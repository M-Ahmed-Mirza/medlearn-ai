"""
MedLearn AI - Critic Agent (V1.5 self-correction differentiator)

The sixth and final agent. Reviews the output of any of the other five
agents and returns a verdict: APPROVED, NEEDS_REVISION, or REJECTED.

This is MedLearn AI's primary multi-step reasoning pattern — judges will
see the system catching its own mistakes before delivering output to users.

Inputs:
    - agent_name: which agent produced the output (e.g. 'LearningPathCurator')
    - agent_output: the actual Pydantic object that agent returned

Outputs:
    - CriticVerdict: APPROVED / NEEDS_REVISION / REJECTED, plus specific
      Issues found, overall_quality_score, rationale, and a
      regeneration_prompt the original agent can use.

Architecture:
    - Generic CriticAgent class with one review() method.
    - Per-type CHECKLIST dictionary injected into the prompt based on
      agent_name. This gives the Critic SPECIFIC failure modes to look for
      per agent type — without writing 5 separate classes.
    - Calls GPT-4o through AzureOpenAI structured outputs (parse() method).

Usage in the orchestrator (Phase 3):
    1. Run Curator -> get CuratorRecommendation
    2. Critic reviews it -> CriticVerdict
    3. If NEEDS_REVISION: re-run Curator with regeneration_prompt appended
    4. If APPROVED: deliver to user
    5. If REJECTED: surface to safety_flags / escalation
"""

import json
import os
from typing import Optional, Union

from openai import AzureOpenAI
from pydantic import BaseModel

from medlearn.models.agent_response import (
    AssessmentResult,
    CriticVerdict,
    CuratorRecommendation,
    EngagementDecision,
    ManagerInsight,
    StudyPlan,
)
from medlearn.telemetry import traced
# A type alias for any output the Critic can review
ReviewableOutput = Union[
    CuratorRecommendation,
    StudyPlan,
    EngagementDecision,
    AssessmentResult,
    ManagerInsight,
]


# ---------- Per-type checklists -----------------------------------------------
# Each checklist tells the Critic what SPECIFIC failure modes to look for in
# that agent's output. This is where domain expertise is encoded.

CHECKLISTS: dict[str, str] = {
    "LearningPathCurator": """
SPECIFIC FAILURE MODES TO CHECK FOR (Learning Path Curator):

1. CITATION INTEGRITY:
   - Does every claim in `rationale` have a supporting citation?
   - Are cited source_document filenames REAL (must be one of:
     clinical_certification_guide.md, workload_correlation_report.md,
     cme_compliance_handbook.md)?
   - If a cited section doesn't exist in the source doc, that's a BLOCKER.

2. CERTIFICATION VALIDITY:
   - Does target_certification_id appear in the catalog? (CCRN-2024, BLS-2024,
     ACLS-2024, BCPS-2024, MLT-ASCP-2026, HIPAA-ANNUAL-2026,
     INFECTION-CTRL-2026, CLIA-COMPLIANCE-2026 are the only valid IDs.)
   - Does the cert match the learner's role? (e.g. recommending BCPS to a
     nurse is a BLOCKER; recommending CCRN to a pharmacist is a BLOCKER.)

3. CONFIDENCE CALIBRATION:
   - If safety_flags exist but confidence > 0.9, that's a MAJOR issue
     (confident-but-flagged is incoherent).
   - If alternatives_considered is empty and confidence > 0.9, that's MAJOR
     (no alternatives = blind certainty).

4. REASONING COMPLETENESS:
   - rationale must be 2+ sentences. One-sentence rationales are MINOR.
   - skills_to_acquire must align with the cert's actual skill domain
     (e.g. recommending CCRN but skills mention pharmacy => MAJOR).

5. SAFETY FLAGS:
   - If the learner has recent fail outcome AND no safety_flag mentions it,
     that's a MAJOR oversight.
""",
    "StudyPlanGenerator": """
SPECIFIC FAILURE MODES TO CHECK FOR (Study Plan Generator):

1. MATH INTEGRITY:
   - sum(week.hours_allocated for all weeks) MUST approximately equal
     total_study_hours. Off by > 10% is a BLOCKER.
   - len(weeks) MUST equal total_weeks. Mismatch is a BLOCKER.
   - week_number must be sequential 1, 2, 3, ... Gaps or duplicates = BLOCKER.

2. BURNOUT-AWARE INTENSITY:
   - If the learner has HIGH burnout, weekly_hour_target must be at most ~40%
     of their focus_hours_per_week. Higher = BLOCKER.
   - If MODERATE burnout, weekly_hour_target should be at most ~70% of focus
     hours. Higher = MAJOR.
   - High burnout MUST trigger at least one safety_flag. Missing = MAJOR.

3. CITATIONS:
   - When the plan adjusts for burnout, workload_correlation_report.md
     should be cited. Missing = MINOR.

4. FEASIBILITY HONESTY:
   - If weekly_hour_target > focus_hours_per_week, schedule_feasibility MUST
     be 'High risk' and safety_flags must call this out. Otherwise = BLOCKER.

5. STRUCTURE:
   - Final 1-2 weeks should include practice tests / review (not new
     material). Missing = MINOR.
   - Every week needs at least one focus_topic. Empty topics = BLOCKER.
""",
    "EngagementAgent": """
SPECIFIC FAILURE MODES TO CHECK FOR (Engagement Agent — ETHICAL CRITICAL):

1. ETHICAL REFUSAL ENFORCEMENT (most important):
   - If burnout was HIGH and action != 'REFUSE_AND_ESCALATE', that's a
     BLOCKER. The ethical refusal rule is non-negotiable.
   - If action == 'REFUSE_AND_ESCALATE' but message_to_learner is not null,
     that's a BLOCKER (we do not push messages to high-burnout learners).
   - If action == 'REFUSE_AND_ESCALATE' but escalation_note is null/empty,
     that's a BLOCKER.

2. RESCHEDULE REQUIREMENTS:
   - If action == 'RESCHEDULE', both message_to_learner AND proposed_time
     must be present. Missing either = BLOCKER.

3. SEND_REMINDER REQUIREMENTS:
   - If action == 'SEND_REMINDER', message_to_learner must be present.
     Missing = BLOCKER.

4. TONE CHECK on message_to_learner:
   - Must NOT use guilt language, urgency, productivity-bro phrases
     ("don't fall behind", "you're missing days", "catch up").
   - Such language = MAJOR.

5. CITATIONS for burnout decisions:
   - REFUSE_AND_ESCALATE outputs MUST cite workload_correlation_report.md.
     Missing = MAJOR.
""",
    "AssessmentAgent": """
SPECIFIC FAILURE MODES TO CHECK FOR (Assessment Agent):

1. READINESS HEURISTIC ENFORCEMENT:
   - If last_assessment_outcome == 'Fail', readiness_level MUST be at most
     'Approaching Ready' regardless of other signals. Anything higher = BLOCKER.
   - If practice_score_avg < minimum_passing_score - 15, readiness_level
     MUST be 'Not Ready'. Otherwise = BLOCKER.
   - readiness_score must align with readiness_level:
     Not Ready: 0.0-0.4; Approaching: 0.4-0.6; Ready: 0.7-0.85;
     Exam Recommended: 0.85-0.95.
     Out-of-range = MAJOR.

2. QUESTION QUALITY:
   - Each question MUST have exactly 4 options (A-D).
   - correct_answer must be 'A', 'B', 'C', or 'D' (single letter).
     Anything else = BLOCKER.
   - Each question must have a skill_tested matching the cert's skill list.
   - Questions must include clinical scenarios, not just trivia
     ("What is X?") = MAJOR if all questions are trivia-style.

3. SAFETY CHECKS:
   - If readiness == 'Not Ready' AND renewal_due_in_days < 30, must raise a
     safety_flag. Missing = MAJOR.

4. FOCUS AREAS:
   - focus_areas should list the WEAK skills, not all skills. If it's
     identical to cert.skills, that's a MAJOR oversight.

5. CITATIONS:
   - clinical_certification_guide.md should be cited for question generation.
     Missing = MINOR.
""",
    "ManagerInsightsAgent": """
SPECIFIC FAILURE MODES TO CHECK FOR (Manager Insights Agent):

1. PRIVACY:
   - Output MUST NOT name individual learners by learner_id (e.g. 'CLN-N-001')
     or by display_name. Aggregate-only language required.
     Naming individuals = BLOCKER.

2. SEVERITY DISCIPLINE:
   - 'Critical' severity should only appear when burnout_risk_summary.high
     >= 3 OR regulatory_compliance_rate < 70%. Otherwise = MAJOR
     (false alarm undermines manager trust).
   - Healthy teams (>90% compliance, <20% high+moderate burnout) should NOT
     have any Critical or High concerns. = MAJOR if present.

3. RANKING ORDER:
   - top_concerns must be ordered most-severe first. Out-of-order = MINOR.

4. ACTIONS QUALITY:
   - recommended_actions must be CONCRETE. Generic platitudes
     ('improve morale', 'consider better scheduling') = MAJOR.

5. ESCALATION HANDLING:
   - If an escalation was provided in the prompt, top_concerns must include
     a related concern AND safety_flags must mention the escalation.
     Missing = MAJOR.

6. CITATIONS:
   - Burnout claims must cite workload_correlation_report.md.
   - Compliance claims must cite cme_compliance_handbook.md.
""",
}


# ---------- Prompt templates ---------------------------------------------------

SYSTEM_PROMPT = """You are the Critic Agent inside MedLearn AI. Your job is \
to REVIEW the output of another agent and decide whether it should be \
APPROVED, NEEDS_REVISION, or REJECTED.

You are the system's quality guardrail. Be tough but fair.

VERDICT DEFINITIONS:
- APPROVED: Output is good. Quality score >= 0.8. May have minor nits but
  nothing that requires regeneration.
- NEEDS_REVISION: Output has fixable issues. Quality score 0.4-0.79. The
  original agent should regenerate using the regeneration_prompt you provide.
- REJECTED: Output is fundamentally wrong (wrong cert, ethics violation,
  fabricated citations). Quality score < 0.4. Do NOT deliver to user.

SEVERITY DEFINITIONS:
- 'Blocker': Causes incorrect/harmful output. Always escalates verdict to
  NEEDS_REVISION or REJECTED.
- 'Major': Reduces output quality significantly but doesn't make it wrong.
  Usually triggers NEEDS_REVISION.
- 'Minor': Stylistic/polish. Does not by itself trigger NEEDS_REVISION.

CRITICAL RULES:
1. Be specific in `problem` field — name the exact field that's wrong.
2. `suggested_fix` must be CONCRETE — describe what should change, not
   generic advice.
3. If verdict is NEEDS_REVISION, you MUST provide a regeneration_prompt.
4. If verdict is APPROVED or REJECTED, regeneration_prompt MUST be null.
5. overall_quality_score must align with verdict (>=0.8 for APPROVED,
   0.4-0.79 for NEEDS_REVISION, <0.4 for REJECTED).
6. Do NOT invent issues. If you cannot find anything wrong, APPROVE it.

The user message will contain (a) the agent type being reviewed,
(b) the agent's output JSON, and (c) a CHECKLIST specific to that agent
type. Use the checklist as your guide."""


USER_PROMPT_TEMPLATE = """REVIEWING AGENT: {agent_name}

AGENT OUTPUT TO REVIEW (JSON):
{agent_output_json}

CHECKLIST FOR THIS AGENT TYPE:
{checklist}

TASK:
Apply the checklist. Return a CriticVerdict object. Be fair but tough — \
flag real issues, but do not invent problems. If the output is genuinely \
good, APPROVE it."""


# ---------- Public API ---------------------------------------------------------


class CriticAgent:
    """The Critic Agent — generic but checklist-driven.

    Usage:
        critic = CriticAgent()

        # Review any other agent's output
        verdict = critic.review("LearningPathCurator", curator_output)
        if verdict.verdict == "NEEDS_REVISION":
            # Re-run the original agent using verdict.regeneration_prompt
            ...
    """

    SUPPORTED_AGENTS = set(CHECKLISTS.keys())

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

    @traced('agent.critic.review')
    def review(
        self,
        agent_name: str,
        agent_output: BaseModel,
    ) -> CriticVerdict:
        """Review another agent's output and return a verdict.

        Args:
            agent_name: One of: 'LearningPathCurator', 'StudyPlanGenerator',
                        'EngagementAgent', 'AssessmentAgent', 'ManagerInsightsAgent'.
            agent_output: The Pydantic object that the named agent returned.

        Returns:
            CriticVerdict with verdict (APPROVED/NEEDS_REVISION/REJECTED),
            specific issues, quality score, rationale, and regeneration_prompt
            (if revision is needed).
        """
        if agent_name not in self.SUPPORTED_AGENTS:
            known = ", ".join(sorted(self.SUPPORTED_AGENTS))
            raise ValueError(
                f"Unknown agent_name {agent_name!r}. Supported: {known}"
            )

        checklist = CHECKLISTS[agent_name]
        agent_output_json = agent_output.model_dump_json(indent=2)

        user_prompt = USER_PROMPT_TEMPLATE.format(
            agent_name=agent_name,
            agent_output_json=agent_output_json,
            checklist=checklist,
        )

        response = self._client.beta.chat.completions.parse(
            model=self._deployment,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format=CriticVerdict,
            temperature=0.1,  # Very low — Critics should be deterministic
            max_tokens=2000,
        )

        verdict = response.choices[0].message.parsed
        if verdict is None:
            refusal = response.choices[0].message.refusal
            raise ValueError(
                f"Critic returned no parsed object. Refusal: {refusal!r}"
            )

        # Force the reviewed_agent field to match what we asked for (the model
        # sometimes echoes a slightly different name)
        verdict.reviewed_agent = agent_name

        return verdict
