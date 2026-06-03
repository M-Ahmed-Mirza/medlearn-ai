"""
MedLearn AI - Manager Insights Agent

The fifth of MedLearn AI's 6 agents. Produces team-level dashboards for
clinical managers — aggregating regulatory compliance status, burnout
patterns, certification pipeline, and prioritized concerns into actionable
guidance.

Inputs:
    - team_id (e.g. 'TEAM-ICU-NIGHT')
    - optional escalation_note (e.g. forwarded from Engagement Agent's
      REFUSE_AND_ESCALATE decisions). When present, the agent incorporates
      the escalation into its concern ranking.

Outputs:
    - ManagerInsight: structured Pydantic model with overall_health_status,
      ranked top_concerns, recommended_actions, citations, safety flags.

Architecture:
    - Loads team report + member work signals
    - Loads grounding docs (workload_correlation_report + cme_compliance_handbook)
    - Calls GPT-4o through AzureOpenAI structured outputs (parse() method)
    - Reasons about PATTERNS across the team — NOT individual diagnoses

PRIVACY NOTE:
    The Manager Insights Agent operates on AGGREGATE data only. It never
    surfaces individual learner names, IDs, or specific personal details.
    All synthetic data is already aggregated at the team level by design.
"""

import json
import os
from typing import List, Optional

from openai import AzureOpenAI

from medlearn.data_loader import load_team_reports, load_work_signals
from medlearn.grounding import GroundingContext
from medlearn.grounding_router import load_grounding_context
from medlearn.models import TeamReport, WorkSignal
from medlearn.models.agent_response import ManagerInsight
from medlearn.telemetry import traced


# ---------- Prompt templates ---------------------------------------------------

SYSTEM_PROMPT = """You are the Manager Insights Agent inside MedLearn AI — a \
multi-agent system for healthcare workforce certification.

Your job: produce a team-level dashboard for a clinical manager. Synthesize \
team-wide compliance data, burnout patterns, and certification trends into \
prioritized concerns and concrete actions.

CORE PRINCIPLES:

1. AGGREGATE ONLY. You receive team-level metrics (size, average scores, \
burnout headcount distributions). You also see member work signals for \
PATTERN context — but never call out individuals by ID or describe a single \
person. Always speak in aggregate terms: "X members at high burnout", \
"team pass rate is Y%", etc.

2. SEVERITY DISCIPLINE:
   - 'Critical' = immediate harm risk (e.g., 3+ members at High burnout, \
     regulatory compliance under 70%, patient-safety implications).
   - 'High' = significant trend that will harm the team in weeks if ignored.
   - 'Moderate' = worth a conversation but not urgent.
   - 'Low' = monitor only.
   Do NOT inflate. A team with mostly low burnout and >90% compliance is \
   'Healthy' — say so. Manager trust depends on you not crying wolf.

3. HANDLE ESCALATIONS HONESTLY. If an escalation_note from the Engagement \
Agent is provided, INCORPORATE it as a top_concern — but evaluate whether \
the broader team data supports the urgency. An escalation about one person \
is real; a pattern across multiple is critical.

4. RECOMMEND CONCRETE ACTIONS, not platitudes:
   - GOOD: 'Redistribute on-call rotation; 2 staff have 80+ workload scores'
   - GOOD: 'Schedule 1:1s with the 3 members approaching renewal in 30 days'
   - BAD: 'Improve team morale'
   - BAD: 'Consider better scheduling'

5. CITE THE WORKLOAD CORRELATION REPORT when making burnout claims. Cite \
the CME COMPLIANCE HANDBOOK when making compliance claims.

6. SET overall_health_status based on the data:
   - 'Healthy' = >90% compliance, <20% moderate+high burnout, normal pass rate
   - 'Some concerns' = isolated issues, no patterns
   - 'Concerning' = clear pattern emerging (2+ correlated metrics dropping)
   - 'Critical — immediate action' = patient-safety or regulatory risk

7. SAFETY FLAGS should surface ethics issues — e.g., 'Engagement Agent \
refused multiple reminders for this team this week, indicating workload \
review is overdue' — not generic warnings.

You MUST return a valid ManagerInsight matching the schema exactly. \
top_concerns must be ordered most-severe first."""


USER_PROMPT_TEMPLATE = """TEAM REPORT (aggregate metrics)
{team_report_json}

MEMBER WORK SIGNALS (for pattern context — do not call out individuals)
{work_signals_json}

GROUNDING DOCUMENTS (cite these when claiming burnout / compliance patterns)
{grounding_block}

{escalation_section}

TASK
Produce a ManagerInsight dashboard for {team_id}. Reason carefully about \
patterns across the team. Order concerns most-severe first. Recommend 2-4 \
concrete actions the manager should take this week."""


_ESCALATION_TEMPLATE = """ACTIVE ESCALATION FROM ENGAGEMENT AGENT
The Engagement Agent has refused to send a study reminder and forwarded \
this concern to you. Incorporate it into your top_concerns appropriately:

{escalation_note}
"""


# ---------- Helpers ------------------------------------------------------------


def _find_team(team_id: str) -> TeamReport:
    catalog = load_team_reports()
    for team in catalog.team_reports:
        if team.team_id == team_id:
            return team
    known = ", ".join(t.team_id for t in catalog.team_reports)
    raise ValueError(f"Unknown team_id: {team_id!r}. Known: {known}")


def _team_member_signals(team_id: str) -> List[WorkSignal]:
    """Return work signals for all learners whose team_id matches.

    Cross-references work_signals.json against learner profiles via learners.json
    (since work_signals are per-learner and learners carry the team_id).
    """
    from medlearn.data_loader import load_learners  # local import avoids circulars

    learners = load_learners().learners
    learner_ids_in_team = {l.learner_id for l in learners if l.team_id == team_id}

    signals = load_work_signals().work_signals
    return [s for s in signals if s.learner_id in learner_ids_in_team]


def _build_user_prompt(
    team: TeamReport,
    member_signals: List[WorkSignal],
    grounding: GroundingContext,
    escalation_note: Optional[str],
) -> str:
    signals_json = json.dumps(
        [s.model_dump(mode="json") for s in member_signals], indent=2, default=str
    )

    escalation_section = (
        _ESCALATION_TEMPLATE.format(escalation_note=escalation_note)
        if escalation_note
        else "(No active escalations from Engagement Agent.)"
    )

    return USER_PROMPT_TEMPLATE.format(
        team_report_json=team.model_dump_json(indent=2),
        work_signals_json=signals_json,
        grounding_block=grounding.as_prompt_block(),
        escalation_section=escalation_section,
        team_id=team.team_id,
    )


# ---------- Public API ---------------------------------------------------------


class ManagerInsightsAgent:
    """The Manager Insights Agent.

    Usage:
        agent = ManagerInsightsAgent()
        insight = agent.analyze(team_id="TEAM-ICU-NIGHT")
        print(f"Health: {insight.overall_health_status}")
        for concern in insight.top_concerns:
            print(f"  [{concern.severity}] {concern.concern}")
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

    @traced('agent.manager_insights.analyze')
    def analyze(
        self,
        team_id: str,
        escalation_note: Optional[str] = None,
        grounding: Optional[GroundingContext] = None,
    ) -> ManagerInsight:
        """Produce a team-level insight dashboard.

        Args:
            team_id: e.g. 'TEAM-ICU-NIGHT'
            escalation_note: Optional escalation from Engagement Agent.
            grounding: Optional pre-loaded GroundingContext.

        Returns:
            ManagerInsight with ranked concerns, recommended actions,
            citations, and confidence score.
        """
        # 1. Load context
        team = _find_team(team_id)
        member_signals = _team_member_signals(team_id)
        if grounding is None:
            grounding = load_grounding_context()

        # 2. Build prompt
        user_prompt = _build_user_prompt(
            team, member_signals, grounding, escalation_note
        )

        # 3. Call GPT-4o with STRUCTURED OUTPUTS
        response = self._client.beta.chat.completions.parse(
            model=self._deployment,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format=ManagerInsight,
            temperature=0.2,
            max_tokens=2500,
        )

        insight = response.choices[0].message.parsed
        if insight is None:
            refusal = response.choices[0].message.refusal
            raise ValueError(
                f"Manager Insights Agent returned no parsed object. Refusal: {refusal!r}"
            )

        return insight