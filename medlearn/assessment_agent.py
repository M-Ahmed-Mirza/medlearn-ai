"""
MedLearn AI - Assessment Agent

The fourth of MedLearn AI's 6 agents. Generates role-appropriate practice
questions for a target certification AND predicts the learner's readiness
to sit the actual exam, based on their practice score, hours studied,
and last assessment outcome.

Inputs:
    - learner_id (e.g. 'CLN-N-001')
    - target_cert_id (e.g. 'CCRN-2024')
    - optional num_questions (default 5)

Outputs:
    - AssessmentResult: 3-8 practice questions + predicted readiness level
      (Not Ready / Approaching Ready / Ready / Exam Recommended) + focus
      areas + next-step recommendation, all with citations.

Architecture:
    - Loads learner profile + certifications catalog
    - Loads grounding docs (clinical_certification_guide for question content,
      workload_correlation_report for assessment readiness criteria)
    - Calls GPT-4o through AzureOpenAI structured outputs (parse() method)

This agent introduces the second Foundry IQ use-case (alongside Curator) —
grounded question generation that cites source material.
"""

import json
import os
from typing import Optional

from openai import AzureOpenAI

from medlearn.data_loader import load_certifications, load_learners
from medlearn.grounding import GroundingContext
from medlearn.grounding_router import load_grounding_context
from medlearn.models import Certification, Learner
from medlearn.models.agent_response import AssessmentResult


# ---------- Prompt templates ---------------------------------------------------

SYSTEM_PROMPT = """You are the Assessment Agent inside MedLearn AI — a \
multi-agent system for healthcare workforce certification.

Your job: produce role-appropriate practice questions for a target \
certification AND predict whether the learner is ready to sit the actual exam.

You produce TWO things simultaneously:

1. A small set of PRACTICE QUESTIONS:
   - Multiple choice, 4 options each (labeled A-D).
   - Each question targets ONE specific skill from the cert's skill list.
   - Mix difficulty: a couple of Easy, a couple of Medium, optionally Hard.
   - Clinically realistic scenarios — not trivia.
   - Always provide the correct answer letter + a 1-3 sentence explanation.
   - GROUND your questions in the provided source documents. Do not fabricate \
     facts that aren't supported by the grounding docs.

2. A READINESS PREDICTION:
   - Use the learner's practice_score_avg, hours_studied_last_quarter, and \
     last_assessment_outcome.
   - Read the grounding docs (clinical_certification_guide has assessment \
     readiness criteria) to calibrate your prediction.
   - Output EXACTLY one of these readiness_level values: \
     'Not Ready', 'Approaching Ready', 'Ready', 'Exam Recommended'.
   - Also output a readiness_score (0.0 to 1.0) representing predicted exam \
     pass probability.

READINESS HEURISTICS (apply these honestly):
- If practice_score_avg < minimum_passing_score - 15 -> 'Not Ready' \
  (readiness_score ~0.2-0.4).
- If practice_score_avg is within 10 of minimum_passing_score AND hours_studied \
  is below 60% of recommended_study_hours -> 'Approaching Ready' (~0.4-0.6).
- If practice_score_avg meets/exceeds minimum_passing_score AND hours_studied \
  is at least 80% of recommended_study_hours AND last_assessment_outcome != Fail \
  -> 'Ready' (~0.7-0.85).
- If all 'Ready' conditions are met AND practice_score_avg is 5+ above \
  minimum_passing_score -> 'Exam Recommended' (~0.85-0.95).
- last_assessment_outcome == Fail caps readiness at 'Approaching Ready' \
  regardless of other signals UNLESS hours studied have substantially \
  increased since.

SAFETY:
- If you predict 'Not Ready' but the learner has a tight deadline (e.g., \
  renewal_due_in_days < 30), raise a safety_flag recommending escalation \
  (e.g., 'Consider deadline extension or focused tutoring').
- If the learner has high burnout signals from the learner profile, raise a \
  safety_flag even when predicting 'Ready' — don't push someone exhausted to \
  the exam without a wellbeing note.

OUTPUT:
- focus_areas should list the specific skills (from the cert) where the \
  learner needs the most work — do not list ALL skills, just the weak ones.
- recommended_next_step should be ONE concrete action: 'Schedule the exam', \
  'Complete X more hours focused on Y', 'Retake practice test in N weeks', etc.

You MUST return a valid AssessmentResult matching the schema exactly. \
Generate between 3 and 8 questions — aim for 5 unless the user explicitly \
asks for more or fewer."""


USER_PROMPT_TEMPLATE = """LEARNER PROFILE
{learner_json}

TARGET CERTIFICATION (use its skills list as the source of question topics)
{cert_json}

GROUNDING DOCUMENTS (cite these when generating questions and assessing readiness)
{grounding_block}

REQUEST
Generate {num_questions} practice questions for {target_cert_id} that cover a \
realistic mix of the cert's skills. Then predict this learner's readiness to \
sit the actual exam, applying the READINESS HEURISTICS strictly.

Return an AssessmentResult object."""


# ---------- Helpers ------------------------------------------------------------


def _find_learner(learner_id: str) -> Learner:
    catalog = load_learners()
    for learner in catalog.learners:
        if learner.learner_id == learner_id:
            return learner
    known = ", ".join(l.learner_id for l in catalog.learners)
    raise ValueError(f"Unknown learner_id: {learner_id!r}. Known: {known}")


def _find_certification(cert_id: str) -> Certification:
    catalog = load_certifications()
    for cert in catalog.certifications:
        if cert.id == cert_id:
            return cert
    known = ", ".join(c.id for c in catalog.certifications)
    raise ValueError(f"Unknown certification id: {cert_id!r}. Known: {known}")


def _build_user_prompt(
    learner: Learner,
    cert: Certification,
    grounding: GroundingContext,
    num_questions: int,
) -> str:
    return USER_PROMPT_TEMPLATE.format(
        learner_json=learner.model_dump_json(indent=2),
        cert_json=cert.model_dump_json(indent=2),
        grounding_block=grounding.as_prompt_block(),
        num_questions=num_questions,
        target_cert_id=cert.id,
    )


# ---------- Public API ---------------------------------------------------------


class AssessmentAgent:
    """The Assessment Agent.

    Usage:
        agent = AssessmentAgent()
        result = agent.assess(learner_id="CLN-N-001", target_cert_id="CCRN-2024")
        print(f"Readiness: {result.readiness_level} ({result.readiness_score:.2f})")
        for q in result.questions:
            print(f"  {q.question_id}: {q.question}")
    """

    def __init__(self, client: AzureOpenAI | None = None) -> None:
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
        aoai_endpoint = endpoint.split("/api/projects/")[0]
        return AzureOpenAI(
            api_key=api_key,
            api_version="2024-12-01-preview",
            azure_endpoint=aoai_endpoint,
        )

    def assess(
        self,
        learner_id: str,
        target_cert_id: str,
        num_questions: int = 5,
        grounding: Optional[GroundingContext] = None,
    ) -> AssessmentResult:
        """Generate practice questions + predict readiness for a learner.

        Args:
            learner_id: e.g. 'CLN-N-001'
            target_cert_id: e.g. 'CCRN-2024'
            num_questions: 3-8 (default 5).
            grounding: Optional pre-loaded GroundingContext.

        Returns:
            AssessmentResult with questions + readiness prediction + next step.
        """
        if not 3 <= num_questions <= 8:
            raise ValueError(
                f"num_questions must be between 3 and 8, got {num_questions}"
            )

        # 1. Load context
        learner = _find_learner(learner_id)
        cert = _find_certification(target_cert_id)
        if grounding is None:
            grounding = load_grounding_context()

        # 2. Build prompt
        user_prompt = _build_user_prompt(learner, cert, grounding, num_questions)

        # 3. Call GPT-4o with STRUCTURED OUTPUTS
        response = self._client.beta.chat.completions.parse(
            model=self._deployment,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format=AssessmentResult,
            temperature=0.3,  # Slightly higher than other agents for question variety
            max_tokens=3500,  # Large budget — multiple questions + explanations
        )

        result = response.choices[0].message.parsed
        if result is None:
            refusal = response.choices[0].message.refusal
            raise ValueError(
                f"Assessment Agent returned no parsed object. Refusal: {refusal!r}"
            )

        return result