"""
MedLearn AI - Learning Path Curator Agent

The first of MedLearn AI's 6 agents. Recommends a certification pathway
for a given clinical learner.

Inputs:
    - learner_id (e.g. 'CLN-N-001')
    - optional target_cert_id (e.g. 'CCRN-2024') — if the learner has a specific goal

Outputs:
    - CuratorRecommendation: structured Pydantic model with citations,
      confidence score, and alternatives considered.

Architecture:
    - Loads learner profile + certifications catalog via data_loader
    - Loads grounding docs (.md files) via grounding helper
    - Calls GPT-4o through AzureOpenAI client with structured output
    - Returns validated CuratorRecommendation

PHASE 4 MIGRATION NOTE:
    - Grounding currently uses local .md files; will swap to Foundry IQ later.
    - Direct AzureOpenAI client used here for simplicity; can wrap in Agent
      Framework's ChatAgent in Phase 3 for orchestration.
"""

import json
import os
from typing import Optional

from openai import AzureOpenAI

from medlearn.data_loader import load_certifications, load_learners
from medlearn.grounding import GroundingContext
from medlearn.grounding_router import load_grounding_context
from medlearn.models import Certification, Learner
from medlearn.models.agent_response import CuratorRecommendation
from medlearn.telemetry import traced


# ---------- Prompt templates ---------------------------------------------------

SYSTEM_PROMPT = """You are the Learning Path Curator Agent inside MedLearn AI — \
a multi-agent system for healthcare workforce certification planning.

Your job: given a synthetic clinical learner's profile, recommend ONE specific \
certification they should pursue next, with a clear, cited rationale.

PRINCIPLES:
1. ALWAYS ground recommendations in the provided source documents. \
Cite specific docs and sections in your output.
2. Consider the learner's role, experience, current certs, pending certs, \
practice score, and workload before recommending.
3. Always evaluate at least one ALTERNATIVE certification path and explain \
why you rejected it. This shows multi-step reasoning.
4. Provide a confidence score (0.0 to 1.0) that honestly reflects how \
sure you are.
5. If the learner is high-burnout or workload is dangerously high, raise \
a safety_flag — don't push them toward more certifications without flagging risk.
6. NEVER fabricate certification details. Only recommend certs that appear \
in the catalog provided.
7. Respect prerequisites. If prerequisites aren't met, say so in \
prerequisites_status.

You MUST return your response as valid JSON matching the CuratorRecommendation \
schema. No markdown, no commentary outside the JSON."""


USER_PROMPT_TEMPLATE = """LEARNER PROFILE
{learner_json}

AVAILABLE CERTIFICATIONS CATALOG
{certifications_json}

GROUNDING DOCUMENTS (cite these when justifying your recommendation)
{grounding_block}

OPTIONAL TARGET CERTIFICATION
The learner has expressed interest in: {target_cert_hint}

TASK
Recommend exactly ONE certification this learner should pursue next. \
Return your answer as JSON conforming to the CuratorRecommendation schema. \
Include citations, alternatives_considered, confidence, and safety_flags."""


# ---------- Helper functions ---------------------------------------------------


def _find_learner(learner_id: str) -> Learner:
    """Resolve a learner_id to a Learner record. Raises ValueError if not found."""
    catalog = load_learners()
    for learner in catalog.learners:
        if learner.learner_id == learner_id:
            return learner
    known = ", ".join(l.learner_id for l in catalog.learners)
    raise ValueError(f"Unknown learner_id: {learner_id!r}. Known: {known}")


def _relevant_certifications(learner: Learner) -> list[Certification]:
    """Return certifications applicable to the learner's role."""
    catalog = load_certifications()
    return [c for c in catalog.certifications if learner.role_code in c.applies_to_roles]


def _build_user_prompt(
    learner: Learner,
    relevant_certs: list[Certification],
    grounding: GroundingContext,
    target_cert_id: Optional[str],
) -> str:
    """Assemble the user-side prompt with all context the agent needs."""
    learner_json = learner.model_dump_json(indent=2)
    certs_json = json.dumps(
        [c.model_dump(mode="json") for c in relevant_certs], indent=2, default=str
    )
    target_hint = target_cert_id if target_cert_id else "(no specific target given)"

    return USER_PROMPT_TEMPLATE.format(
        learner_json=learner_json,
        certifications_json=certs_json,
        grounding_block=grounding.as_prompt_block(),
        target_cert_hint=target_hint,
    )


# ---------- Public API ---------------------------------------------------------


class LearningPathCurator:
    """The Learning Path Curator Agent.

    Usage:
        curator = LearningPathCurator()
        recommendation = curator.recommend(learner_id="CLN-N-001")
        print(recommendation.target_certification_id)
    """

    def __init__(self, client: AzureOpenAI | None = None) -> None:
        """Initialize the agent.

        Args:
            client: Optional pre-built AzureOpenAI client. If None, builds one
                    from .env credentials.
        """
        self._client = client or self._build_client_from_env()
        self._deployment = os.getenv("AZURE_AI_MODEL_DEPLOYMENT", "medlearn-gpt-4o")

    @staticmethod
    def _build_client_from_env() -> AzureOpenAI:
        endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
        api_key = os.getenv("AZURE_AI_API_KEY")
        if not endpoint or not api_key:
            raise RuntimeError(
                "AZURE_AI_PROJECT_ENDPOINT and AZURE_AI_API_KEY must be set in .env"
            )
        # Strip the /api/projects/... suffix so we hit the Azure OpenAI endpoint
        # (same pattern as scripts/hello_foundry.py)
        aoai_endpoint = endpoint.split("/api/projects/")[0]
        return AzureOpenAI(
            api_key=api_key, api_version="2024-12-01-preview", azure_endpoint=aoai_endpoint
        )

    @traced('agent.curator.recommend')
    def recommend(
        self,
        learner_id: str,
        target_cert_id: Optional[str] = None,
        grounding: Optional[GroundingContext] = None,
    ) -> CuratorRecommendation:
        """Produce a learning path recommendation for a single learner.

        Args:
            learner_id: e.g. 'CLN-N-001'
            target_cert_id: Optional cert ID the learner is targeting.
            grounding: Optional pre-loaded GroundingContext. If None, loads all
                       docs from data/docs/.

        Returns:
            CuratorRecommendation: validated structured output.
        """
        # 1. Load context
        learner = _find_learner(learner_id)
        relevant_certs = _relevant_certifications(learner)
        if grounding is None:
            grounding = load_grounding_context()

        # 2. Build prompt
        user_prompt = _build_user_prompt(learner, relevant_certs, grounding, target_cert_id)

        # 3. Call GPT-4o with STRUCTURED OUTPUTS (forces exact Pydantic schema)
        #    Using .beta.chat.completions.parse() guarantees the model returns
        #    JSON matching CuratorRecommendation's field names exactly.
        response = self._client.beta.chat.completions.parse(
            model=self._deployment,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format=CuratorRecommendation,
            temperature=0.2,
            max_tokens=2000,
        )

        # 4. Extract the parsed Pydantic object directly
        recommendation = response.choices[0].message.parsed
        if recommendation is None:
            # Model refused or returned malformed structure
            refusal = response.choices[0].message.refusal
            raise ValueError(
                f"Curator returned no parsed object. Refusal: {refusal!r}"
            )

        return recommendation