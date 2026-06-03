"""
MedLearn AI - Study Plan Generator Agent

The second of MedLearn AI's 6 agents. Takes a learner + a target certification
and produces a realistic, shift-aware, week-by-week study plan.

Inputs:
    - learner_id (e.g. 'CLN-N-001')
    - target_cert_id (e.g. 'CCRN-2024') — typically the Curator's recommendation

Outputs:
    - StudyPlan: validated Pydantic model with week-by-week schedule,
      citations, confidence score, and safety flags.

Architecture:
    - Loads learner profile + certifications + WORK SIGNALS (this is the
      key differentiator — agent reasons about shift patterns, on-call,
      and burnout indicators).
    - Loads grounding docs via grounding helper.
    - Calls GPT-4o through AzureOpenAI structured outputs (parse() method
      forces exact StudyPlan schema match).

This agent introduces the WORK IQ layer of MedLearn AI.

PHASE 4 MIGRATION NOTE:
    Same as Curator — grounding will swap to Foundry IQ later, agent
    can be wrapped in Agent Framework's ChatAgent for orchestration.
"""

import json
import os
from typing import Optional

from openai import AzureOpenAI

from medlearn.data_loader import (
    load_certifications,
    load_learners,
    load_work_signals,
)
from medlearn.grounding import GroundingContext
from medlearn.grounding_router import load_grounding_context
from medlearn.models import Certification, Learner, WorkSignal
from medlearn.models.agent_response import StudyPlan
from medlearn.telemetry import traced


# ---------- Prompt templates ---------------------------------------------------

SYSTEM_PROMPT = """You are the Study Plan Generator Agent inside MedLearn AI — \
a multi-agent system for healthcare workforce certification planning.

Your job: given a clinical learner's profile, their work patterns (shifts, \
on-call rotation, burnout indicators), and a target certification, produce a \
realistic week-by-week study plan that fits into their clinical workday.

PRINCIPLES:
1. RESPECT REAL HUMAN LIMITS. Healthcare workers have brutal shifts. Do not \
schedule study time during clinical shifts or on-call windows. Use only their \
focus_hours_per_week as the upper bound for weekly study.

2. USE THE LEARNER'S PREFERRED LEARNING SLOT. If they prefer "Late Morning \
(post-shift recovery)", schedule study sessions in that window — don't fight \
their actual chronotype.

3. SCALE INTENSITY TO BURNOUT RISK:
   - LOW burnout: can use up to 100% of focus_hours_per_week
   - MODERATE burnout: cap at ~70% of focus_hours_per_week
   - HIGH burnout: cap at ~40% and ALWAYS raise a safety_flag recommending \
     workload review BEFORE intensifying study

4. DO THE MATH HONESTLY. total_weeks * weekly_hour_target should approximately \
equal the certification's recommended_study_hours. If a tight deadline forces \
weekly hours above the learner's focus_hours_per_week, set schedule_feasibility \
to 'High risk' and explain in safety_flags.

5. STRUCTURE TOPICS ACROSS WEEKS using the cert's skills list. Early weeks = \
foundational topics. Middle weeks = harder material. Final 1-2 weeks = practice \
tests + review.

6. SET MILESTONES every 2-3 weeks. Concrete checkpoints like "Complete \
hemodynamics module" or "First practice exam".

7. CITE the grounding documents where you draw conclusions about study \
intensity, burnout thresholds, or compliance timelines.

8. Provide a confidence score that honestly reflects the plan's feasibility. \
Low confidence + safety_flags is much better than overconfident scheduling \
that ignores burnout risk.

You MUST return your response as a StudyPlan object matching the schema exactly. \
The weeks array MUST have exactly total_weeks entries, numbered 1 through total_weeks."""


USER_PROMPT_TEMPLATE = """LEARNER PROFILE
{learner_json}

LEARNER WORK SIGNALS (shift pattern, focus hours, burnout indicators)
{work_signal_json}

TARGET CERTIFICATION
{cert_json}

GROUNDING DOCUMENTS (cite these when justifying scheduling decisions)
{grounding_block}

TASK
Build a realistic week-by-week study plan to get this learner from their \
current state to ready for {target_cert_id}. The plan MUST respect:
- The learner's focus_hours_per_week (do not exceed it without flagging risk)
- Their burnout_risk_indicator (scale intensity accordingly)
- Their preferred_learning_slot and preferred_learning_days
- The cert's recommended_study_hours and renewal_due_in_days timeline

Return your answer as a StudyPlan object."""


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


def _find_certification(cert_id: str) -> Certification:
    catalog = load_certifications()
    for cert in catalog.certifications:
        if cert.id == cert_id:
            return cert
    known = ", ".join(c.id for c in catalog.certifications)
    raise ValueError(f"Unknown certification id: {cert_id!r}. Known: {known}")


def _build_user_prompt(
    learner: Learner,
    work_signal: WorkSignal,
    cert: Certification,
    grounding: GroundingContext,
) -> str:
    return USER_PROMPT_TEMPLATE.format(
        learner_json=learner.model_dump_json(indent=2),
        work_signal_json=work_signal.model_dump_json(indent=2),
        cert_json=cert.model_dump_json(indent=2),
        grounding_block=grounding.as_prompt_block(),
        target_cert_id=cert.id,
    )


# ---------- Public API ---------------------------------------------------------


class StudyPlanGenerator:
    """The Study Plan Generator Agent.

    Usage:
        generator = StudyPlanGenerator()
        plan = generator.generate(learner_id="CLN-N-001", target_cert_id="CCRN-2024")
        print(f"Plan: {plan.total_weeks} weeks, {plan.total_study_hours} hours")
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

    @traced('agent.study_plan.generate')
    def generate(
        self,
        learner_id: str,
        target_cert_id: str,
        grounding: Optional[GroundingContext] = None,
    ) -> StudyPlan:
        """Produce a shift-aware study plan for a single learner.

        Args:
            learner_id: e.g. 'CLN-N-001'
            target_cert_id: e.g. 'CCRN-2024' (typically Curator's recommendation)
            grounding: Optional pre-loaded GroundingContext.

        Returns:
            StudyPlan: validated structured output with week-by-week schedule.
        """
        # 1. Load context
        learner = _find_learner(learner_id)
        work_signal = _find_work_signal(learner_id)
        cert = _find_certification(target_cert_id)
        if grounding is None:
            grounding = load_grounding_context()

        # 2. Build prompt
        user_prompt = _build_user_prompt(learner, work_signal, cert, grounding)

        # 3. Call GPT-4o with STRUCTURED OUTPUTS (forces exact Pydantic schema)
        response = self._client.beta.chat.completions.parse(
            model=self._deployment,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format=StudyPlan,
            temperature=0.2,
            max_tokens=3000,  # Larger budget — week-by-week plans need room
        )

        # 4. Extract parsed Pydantic object
        plan = response.choices[0].message.parsed
        if plan is None:
            refusal = response.choices[0].message.refusal
            raise ValueError(
                f"Study Plan Generator returned no parsed object. Refusal: {refusal!r}"
            )

        return plan