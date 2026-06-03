"""
MedLearn AI - Engagement Agent

The third of MedLearn AI's 6 agents. Decides whether to send a study reminder
to a learner RIGHT NOW, reschedule it, or REFUSE and escalate to Manager
Insights when burnout risk makes pushing harder ethically wrong.

This is MedLearn AI's PRIMARY ETHICAL-REFUSAL PATTERN. It is the agent that
unlocks the "Hack for Good" prize angle and demonstrates duty-of-care reasoning
that most submissions will not have.

Inputs:
    - learner_id (e.g. 'CLN-N-001')
    - occasion: a free-text description of why we're considering a reminder
      (e.g. 'weekly study reminder', 'practice test due', 'cert renewal in 14 days')

Outputs:
    - EngagementDecision: validated Pydantic model with action
      (SEND_REMINDER | RESCHEDULE | REFUSE_AND_ESCALATE), citations,
      confidence, and safety flags.

Architecture:
    - Loads learner profile + WORK SIGNALS (shift pattern, on-call, burnout)
    - Loads grounding docs (workload correlation + CME handbook)
    - Calls GPT-4o through AzureOpenAI structured outputs

The ethical refusal logic is enforced in the SYSTEM_PROMPT — the model is
instructed that high burnout MUST trigger REFUSE_AND_ESCALATE, not SEND_REMINDER.
"""

import json
import os
from typing import Optional

from openai import AzureOpenAI

from medlearn.data_loader import load_learners, load_work_signals
from medlearn.grounding import GroundingContext
from medlearn.grounding_router import load_grounding_context
from medlearn.models import Learner, WorkSignal
from medlearn.models.agent_response import EngagementDecision
from medlearn.telemetry import traced


# ---------- Prompt templates ---------------------------------------------------

SYSTEM_PROMPT = """You are the Engagement Agent inside MedLearn AI — a \
multi-agent system for healthcare workforce certification.

Your job: decide what to do with a proposed study-reminder to a clinical \
learner. You have access to their work signals (shift pattern, on-call status, \
focus hours, burnout risk indicator, workload score). Reason carefully about \
WHETHER and WHEN to engage.

CORE PRINCIPLE — DUTY OF CARE:
A study reminder is not free. Healthcare workers are often exhausted. Pushing \
study at the wrong time worsens burnout, decreases learning, and can cause \
real harm to the learner AND their patients. Engagement is NOT the goal — \
healthy, sustained learning is.

DECISION RULES:

1. If the learner has burnout_risk_indicator == "High":
   - You MUST set action = "REFUSE_AND_ESCALATE".
   - You MUST NOT include a message_to_learner. Leave it null.
   - You MUST provide an escalation_note to the Manager Insights Agent \
     describing the concern and recommending a workload review.
   - You MUST raise a safety_flag noting burnout-driven refusal.
   - This is non-negotiable. Do NOT downgrade to RESCHEDULE just because the \
     learner has a deadline. Their wellbeing comes first.

2. If the learner is currently in an on-call window OR working a shift right now:
   - Set action = "RESCHEDULE".
   - Propose a time inside their preferred_learning_slot and \
     preferred_learning_days.
   - Provide a kind, short message_to_learner explaining the rescheduled time.

3. If burnout is "Moderate":
   - You MAY send a reminder, but it must be EXTRA gentle and brief.
   - Include a brief check-in tone, not a productivity push.
   - Lower confidence (~0.6-0.8) is appropriate.

4. If burnout is "Low" AND no on-call AND the current_workload_score is < 70:
   - Action = "SEND_REMINDER" is safe.
   - Tone should still be warm and human, not corporate.

COMMUNICATION STYLE (when sending or rescheduling):
- Short. 2-3 sentences max.
- Acknowledge the learner's clinical work first.
- NEVER use guilt, urgency language, or productivity-bro phrases.
- Examples of GOOD tone: "Hope your shift wrapped up well", "When you have \
  a quiet morning", "No rush, just wanted to flag this is on your list".
- Examples of BAD tone: "Don't fall behind", "You're missing study days", \
  "Catch up on your studies".

REQUIRED OUTPUT FIELDS BY ACTION:
- SEND_REMINDER: message_to_learner REQUIRED, proposed_time OPTIONAL, \
  escalation_note must be null.
- RESCHEDULE: message_to_learner REQUIRED, proposed_time REQUIRED, \
  escalation_note must be null.
- REFUSE_AND_ESCALATE: message_to_learner MUST be null, proposed_time MUST be \
  null, escalation_note REQUIRED.

Always cite the grounding documents that support your reasoning, especially \
the workload correlation report when you make burnout-based decisions.

You MUST return a valid EngagementDecision matching the schema exactly."""


USER_PROMPT_TEMPLATE = """LEARNER PROFILE
{learner_json}

LEARNER WORK SIGNALS (this is your primary input — read carefully)
{work_signal_json}

GROUNDING DOCUMENTS (cite these when making burnout/workload decisions)
{grounding_block}

PROPOSED REMINDER OCCASION
{occasion}

TASK
Decide what to do. Use the DECISION RULES strictly. If burnout is "High", \
the answer is REFUSE_AND_ESCALATE regardless of how important the reminder \
seems — flag the manager instead. Return an EngagementDecision object."""


# ---------- Helpers ------------------------------------------------------------


def _find_learner(learner_id: str) -> Learner:
    catalog = load_learners()
    for learner in catalog.learners:
        if learner.learner_id == learner_id:
            return learner
    known = ", ".join(l.learner_id for l in catalog.learners)
    raise ValueError(f"Unknown learner_id: {learner_id!r}. Known: {known}")


def _find_work_signal(learner_id: str) -> WorkSignal:
    catalog = load_work_signals()
    for signal in catalog.work_signals:
        if signal.learner_id == learner_id:
            return signal
    raise ValueError(f"No work signal found for learner_id: {learner_id!r}")


def _build_user_prompt(
    learner: Learner,
    work_signal: WorkSignal,
    grounding: GroundingContext,
    occasion: str,
) -> str:
    return USER_PROMPT_TEMPLATE.format(
        learner_json=learner.model_dump_json(indent=2),
        work_signal_json=work_signal.model_dump_json(indent=2),
        grounding_block=grounding.as_prompt_block(),
        occasion=occasion,
    )


# ---------- Public API ---------------------------------------------------------


class EngagementAgent:
    """The Engagement Agent.

    Usage:
        agent = EngagementAgent()
        decision = agent.decide(
            learner_id="CLN-N-001",
            occasion="weekly study reminder for CCRN prep, Week 2",
        )
        if decision.action == "REFUSE_AND_ESCALATE":
            forward_to_manager_insights(decision.escalation_note)
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

    @traced('agent.engagement.decide')
    def decide(
        self,
        learner_id: str,
        occasion: str,
        grounding: Optional[GroundingContext] = None,
    ) -> EngagementDecision:
        """Decide what to do with a proposed reminder for a learner.

        Args:
            learner_id: e.g. 'CLN-N-001'
            occasion: free-text description of the reminder occasion.
            grounding: Optional pre-loaded GroundingContext.

        Returns:
            EngagementDecision: SEND_REMINDER | RESCHEDULE | REFUSE_AND_ESCALATE
            with rationale, citations, and safety_flags.
        """
        # 1. Load context
        learner = _find_learner(learner_id)
        work_signal = _find_work_signal(learner_id)
        if grounding is None:
            grounding = load_grounding_context()

        # 2. Build prompt
        user_prompt = _build_user_prompt(learner, work_signal, grounding, occasion)

        # 3. Call GPT-4o with STRUCTURED OUTPUTS
        response = self._client.beta.chat.completions.parse(
            model=self._deployment,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format=EngagementDecision,
            temperature=0.2,
            max_tokens=1500,
        )

        decision = response.choices[0].message.parsed
        if decision is None:
            refusal = response.choices[0].message.refusal
            raise ValueError(
                f"Engagement Agent returned no parsed object. Refusal: {refusal!r}"
            )

        return decision