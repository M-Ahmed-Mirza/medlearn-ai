"""
MedLearn AI - Agent Response Schemas

Structured outputs every agent must return. Includes confidence scoring,
cited sources, and alternatives considered — the V1.5 differentiators
that make our reasoning visible to judges.
"""

from typing import List, Optional

from pydantic import BaseModel, Field

from medlearn.models.enums import ReadinessLevel


class Citation(BaseModel):
    """A single citation backing an agent's reasoning."""

    source_document: str = Field(
        ..., description="Path or identifier of the source doc, e.g. 'clinical_certification_guide.md'."
    )
    section: Optional[str] = Field(
        default=None,
        description="Section reference within the doc, e.g. 'Section 2.1 — Critical Care RN'.",
    )
    excerpt: Optional[str] = Field(
        default=None, description="Short verbatim excerpt supporting the claim."
    )


class AlternativeConsidered(BaseModel):
    """An option the agent evaluated but did not pick. Boosts reasoning transparency."""

    option: str = Field(..., description="Brief description of the alternative.")
    rejected_because: str = Field(..., description="Why this option was not chosen.")


class CuratorRecommendation(BaseModel):
    """Structured output from the Learning Path Curator Agent.

    This schema is what GPT-4o will be forced to return — guaranteeing
    we always get cited, confidence-scored, alternative-aware recommendations.
    """

    learner_id: str = Field(..., description="The learner this recommendation is for.")
    target_certification_id: str = Field(
        ..., description="The cert ID the learner should pursue, e.g. 'CCRN-2024'."
    )
    target_certification_name: str = Field(
        ..., description="Human-readable cert name."
    )
    rationale: str = Field(
        ...,
        description="2-4 sentence plain-English explanation of WHY this cert is recommended.",
    )
    skills_to_acquire: List[str] = Field(
        ..., min_length=1, description="Skills the learner will gain by completing this cert."
    )
    recommended_study_hours: int = Field(
        ..., ge=1, description="Total study hours recommended for this cert."
    )
    prerequisites_status: str = Field(
        ...,
        description="One of: 'All prerequisites met', 'Some missing', 'Prerequisites unclear'.",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Agent's confidence in this recommendation (0.0 to 1.0).",
    )
    citations: List[Citation] = Field(
        default_factory=list,
        description="Source documents and sections cited in the rationale.",
    )
    alternatives_considered: List[AlternativeConsidered] = Field(
        default_factory=list,
        description="Other options the agent thought about but rejected.",
    )
    safety_flags: List[str] = Field(
        default_factory=list,
        description="Any safety/risk concerns flagged for human review.",
    )


# ============================================================================
# Study Plan Generator schemas
# ============================================================================


class StudyWeek(BaseModel):
    """A single week in a study plan."""

    week_number: int = Field(..., ge=1, description="Sequential week index, starting at 1.")
    hours_allocated: float = Field(
        ..., ge=0.0, le=40.0, description="Total study hours scheduled this week."
    )
    focus_topics: List[str] = Field(
        ..., min_length=1, description="Specific skills/topics to study this week."
    )
    sessions_per_week: int = Field(
        ..., ge=1, le=14, description="Number of distinct study sessions across the week."
    )
    milestone: Optional[str] = Field(
        default=None,
        description="Concrete checkpoint for this week (e.g. 'Complete Hemodynamics module', 'First practice test').",
    )


class StudyPlan(BaseModel):
    """Structured output from the Study Plan Generator Agent.

    A realistic, shift-aware study plan that respects the learner's clinical
    workload, burnout indicators, and preferred learning windows.
    """

    learner_id: str = Field(..., description="The learner this plan is for.")
    target_certification_id: str = Field(
        ..., description="The cert this plan prepares the learner for, e.g. 'CCRN-2024'."
    )
    target_certification_name: str = Field(..., description="Human-readable cert name.")
    total_weeks: int = Field(
        ..., ge=1, le=52, description="Total number of weeks in the plan."
    )
    total_study_hours: float = Field(
        ..., ge=1.0, description="Total study hours allocated across the entire plan."
    )
    weekly_hour_target: float = Field(
        ...,
        ge=0.5,
        le=40.0,
        description="Average target hours per week (informational summary).",
    )
    preferred_study_window: str = Field(
        ...,
        description="When in the week/day this learner is scheduled to study, in plain English.",
    )
    weeks: List[StudyWeek] = Field(
        ...,
        min_length=1,
        description="Detailed week-by-week schedule. Length must equal total_weeks.",
    )
    schedule_feasibility: str = Field(
        ...,
        description="One of: 'Comfortably achievable', 'Tight but feasible', 'High risk — exceeds available focus hours'.",
    )
    rationale: str = Field(
        ...,
        description="2-4 sentence plain-English explanation of HOW the plan was built and key trade-offs.",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Agent's confidence in the plan's feasibility (0.0 to 1.0).",
    )
    citations: List[Citation] = Field(
        default_factory=list,
        description="Source documents referenced when designing the plan.",
    )
    safety_flags: List[str] = Field(
        default_factory=list,
        description="Workload/burnout/timeline risks flagged for human review.",
    )


# ============================================================================
# Engagement Agent schemas
# ============================================================================


class EngagementDecision(BaseModel):
    """Structured output from the Engagement Agent.

    Decides whether to send a study reminder to a learner RIGHT NOW, or
    reschedule it, or refuse and escalate to Manager Insights when burnout
    risk makes pushing the learner harmful.

    This is MedLearn AI's primary ethical-refusal pattern — judges will see
    burnout-aware decisions made autonomously, with citations.
    """

    learner_id: str = Field(..., description="The learner this decision is for.")
    action: str = Field(
        ...,
        description=(
            "EXACTLY one of: 'SEND_REMINDER', 'RESCHEDULE', or 'REFUSE_AND_ESCALATE'. "
            "SEND_REMINDER = deliver the reminder now. "
            "RESCHEDULE = defer to a better time (provide proposed_time). "
            "REFUSE_AND_ESCALATE = burnout/welfare risk; do not send, flag manager."
        ),
    )
    message_to_learner: Optional[str] = Field(
        default=None,
        description=(
            "The actual reminder text the system would send. "
            "REQUIRED when action='SEND_REMINDER' or 'RESCHEDULE'. "
            "MUST be empty/null when action='REFUSE_AND_ESCALATE' "
            "(we do not push messages to high-burnout learners)."
        ),
    )
    proposed_time: Optional[str] = Field(
        default=None,
        description=(
            "When the reminder should arrive (natural language ok, e.g. "
            "'Tuesday at 10am, post-shift window'). REQUIRED when action='RESCHEDULE'."
        ),
    )
    escalation_note: Optional[str] = Field(
        default=None,
        description=(
            "Message to forward to Manager Insights Agent. REQUIRED when "
            "action='REFUSE_AND_ESCALATE'. Should describe the concern and "
            "suggest workload/scheduling intervention."
        ),
    )
    rationale: str = Field(
        ...,
        description=(
            "2-4 sentence explanation of WHY this action was chosen, citing the "
            "learner's burnout indicator, current shift, on-call status, "
            "and/or workload score."
        ),
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence in the decision (0.0 to 1.0)."
    )
    citations: List[Citation] = Field(
        default_factory=list,
        description="Source documents supporting the decision (e.g., workload guidelines).",
    )
    safety_flags: List[str] = Field(
        default_factory=list,
        description="Welfare/burnout/safety concerns to surface.",
    )


# ============================================================================
# Assessment Agent schemas
# ============================================================================


class PracticeQuestion(BaseModel):
    """A single practice question generated by the Assessment Agent.

    Multiple-choice format. Includes the correct answer + explanation so
    judges can see the agent reasoning end-to-end.
    """

    question_id: str = Field(
        ..., description="Sequential identifier within this assessment, e.g. 'Q1'."
    )
    skill_tested: str = Field(
        ..., description="Which skill from the cert's skill list this question targets."
    )
    difficulty: str = Field(
        ...,
        description="One of: 'Easy', 'Medium', 'Hard'. Should align with the cert's difficulty_level.",
    )
    question: str = Field(..., description="The question stem itself.")
    options: List[str] = Field(
        ...,
        min_length=4,
        max_length=4,
        description="Exactly 4 answer options, labeled A-D in order.",
    )
    correct_answer: str = Field(
        ...,
        description="The correct letter ('A', 'B', 'C', or 'D'). Just the letter.",
    )
    explanation: str = Field(
        ...,
        description="1-3 sentence explanation of why the correct answer is correct.",
    )


class AssessmentResult(BaseModel):
    """Structured output from the Assessment Agent.

    Generates practice questions tailored to the learner's role + target cert
    AND predicts their exam readiness based on their existing practice score,
    hours studied, and last assessment outcome.
    """

    learner_id: str = Field(..., description="The learner this assessment is for.")
    target_certification_id: str = Field(
        ..., description="Certification being assessed, e.g. 'CCRN-2024'."
    )
    target_certification_name: str = Field(..., description="Human-readable cert name.")
    questions: List[PracticeQuestion] = Field(
        ...,
        min_length=3,
        max_length=8,
        description="3-8 practice questions covering the cert's skill list.",
    )
    readiness_level: str = Field(
        ...,
        description=(
            "Predicted readiness for the actual exam. EXACTLY one of: "
            "'Not Ready', 'Approaching Ready', 'Ready', 'Exam Recommended'."
        ),
    )
    readiness_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Predicted probability of passing the exam right now (0.0 to 1.0).",
    )
    focus_areas: List[str] = Field(
        default_factory=list,
        description="Specific skills the learner should drill further before the real exam.",
    )
    rationale: str = Field(
        ...,
        description=(
            "2-4 sentence explanation of how readiness was determined, citing "
            "the learner's practice_score_avg, hours_studied_last_quarter, and "
            "last_assessment_outcome."
        ),
    )
    recommended_next_step: str = Field(
        ...,
        description=(
            "What the learner should do next. Examples: 'Schedule the exam', "
            "'Complete 10 more hours focused on Hemodynamics', 'Retake practice "
            "test in 2 weeks'."
        ),
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Agent's confidence in the readiness assessment (0.0 to 1.0).",
    )
    citations: List[Citation] = Field(
        default_factory=list,
        description="Source documents referenced when generating questions / assessing readiness.",
    )
    safety_flags: List[str] = Field(
        default_factory=list,
        description="Risks flagged (e.g., learner pushing for exam despite Not Ready status).",
    )


# ============================================================================
# Manager Insights Agent schemas
# ============================================================================


class TeamConcern(BaseModel):
    """A single concern surfaced by the Manager Insights Agent."""

    concern: str = Field(
        ..., description="Short description of the concern, e.g. 'Multiple high-burnout staff on night shift'."
    )
    severity: str = Field(
        ...,
        description="Severity level. EXACTLY one of: 'Critical', 'High', 'Moderate', 'Low'.",
    )
    affected_count: int = Field(
        ...,
        ge=0,
        description="Number of team members affected by this concern (aggregate only — no PII).",
    )
    recommended_intervention: str = Field(
        ...,
        description="Concrete next step the manager should take, e.g. 'Redistribute shifts', 'Schedule team review'.",
    )


class ManagerInsight(BaseModel):
    """Structured output from the Manager Insights Agent.

    A team-level dashboard with prioritized concerns, compliance highlights,
    and burnout pattern analysis. Receives escalations from the Engagement
    Agent and packages them with team data into actionable manager guidance.
    """

    team_id: str = Field(..., description="The team this insight is for, e.g. 'TEAM-ICU-NIGHT'.")
    team_name: str = Field(..., description="Human-readable team name.")
    team_size: int = Field(..., ge=1, description="Total team size.")

    overall_health_status: str = Field(
        ...,
        description=(
            "One-line summary of team health. EXACTLY one of: "
            "'Healthy', 'Some concerns', 'Concerning', 'Critical — immediate action'."
        ),
    )
    compliance_summary: str = Field(
        ...,
        description="1-2 sentence summary of regulatory compliance status.",
    )
    burnout_pattern: str = Field(
        ...,
        description="1-2 sentence summary of burnout distribution across the team.",
    )
    certification_pipeline: str = Field(
        ...,
        description="1-2 sentence summary of upcoming cert renewals and pass-rate trends.",
    )

    top_concerns: List[TeamConcern] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="1-5 prioritized concerns, ordered most severe first.",
    )

    recommended_actions: List[str] = Field(
        ...,
        min_length=1,
        description="Top 2-4 concrete actions the manager should take this week.",
    )

    rationale: str = Field(
        ...,
        description="2-4 sentence explanation of how the insights were derived from the data.",
    )

    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Agent's confidence in the analysis (0.0 to 1.0).",
    )

    citations: List[Citation] = Field(
        default_factory=list,
        description="Source documents referenced when forming insights.",
    )

    safety_flags: List[str] = Field(
        default_factory=list,
        description="Cross-team safety/ethics flags requiring leadership attention.",
    )


# ============================================================================
# Critic Agent schemas (V1.5 self-correction loop)
# ============================================================================


class Issue(BaseModel):
    """A single problem the Critic Agent found in another agent's output."""

    severity: str = Field(
        ...,
        description="EXACTLY one of: 'Blocker', 'Major', 'Minor'.",
    )
    field: str = Field(
        ...,
        description="Which field of the reviewed output has the issue (e.g. 'confidence', 'citations', 'rationale').",
    )
    problem: str = Field(
        ...,
        description="Concise description of what is wrong (1-2 sentences).",
    )
    suggested_fix: str = Field(
        ...,
        description="Concrete suggestion for how the original agent should fix this on regeneration.",
    )


class CriticVerdict(BaseModel):
    """Structured output from the Critic Agent.

    The Critic reviews another agent's output and returns a verdict
    (APPROVED / NEEDS_REVISION / REJECTED) plus specific issues found
    and a regeneration prompt if revision is needed.

    This is MedLearn AI's V1.5 self-correction differentiator — judges
    will see the system catching its own mistakes before delivering output.
    """

    reviewed_agent: str = Field(
        ...,
        description="Which agent's output is being reviewed. EXACTLY one of: "
        "'LearningPathCurator', 'StudyPlanGenerator', 'EngagementAgent', "
        "'AssessmentAgent', 'ManagerInsightsAgent'.",
    )
    verdict: str = Field(
        ...,
        description="EXACTLY one of: 'APPROVED', 'NEEDS_REVISION', 'REJECTED'. "
        "APPROVED = output is good as-is. "
        "NEEDS_REVISION = output has fixable issues; regenerate with feedback. "
        "REJECTED = output is fundamentally wrong; do not deliver to user.",
    )
    issues: List[Issue] = Field(
        default_factory=list,
        description="Specific issues found, empty when verdict is APPROVED.",
    )
    overall_quality_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Overall quality score (0.0 = unusable, 1.0 = perfect). "
        "APPROVED outputs should score >= 0.8. NEEDS_REVISION 0.4-0.79. "
        "REJECTED < 0.4.",
    )
    rationale: str = Field(
        ...,
        description="2-4 sentence explanation of the verdict.",
    )
    regeneration_prompt: Optional[str] = Field(
        default=None,
        description="If verdict is NEEDS_REVISION, a concise instruction the "
        "original agent should use when regenerating. Empty/null when APPROVED "
        "or REJECTED.",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="The Critic's confidence in its own verdict.",
    )