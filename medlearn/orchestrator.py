"""
MedLearn AI - Orchestrator (Phase 3)

Coordinates all 6 agents into a single pipeline:

    Curator -> [Critic] -> StudyPlan -> [Critic] -> Engagement -> [Critic]
                                                       |
                                                       v (if REFUSE_AND_ESCALATE)
                                            Manager Insights -> [Critic]
                                                       |
                          Assessment -> [Critic] -----+
                                                       v
                                          LearnerJourneyReport

Key behaviors:
    - Critic regeneration loop: when Critic returns NEEDS_REVISION,
      re-run the upstream agent with the regeneration_prompt (max 1 retry).
    - Escalation routing: if Engagement Agent returns REFUSE_AND_ESCALATE,
      the escalation_note is forwarded to Manager Insights Agent.
    - Final output: LearnerJourneyReport with all agent outputs + Critic
      review summaries.

Demo storyline:
    1. Pick a learner (e.g., CLN-N-001 with moderate burnout)
    2. Run pipeline -> Curator picks CCRN, Study Plan builds 6-week schedule,
       Engagement sends gentle reminder, Assessment generates questions
    3. All outputs reviewed by Critic, none need regeneration
    4. Final report shows the system "thinking together"

Or with a high-burnout learner:
    - Engagement REFUSES + escalates -> Manager Insights generates dashboard
      with the escalation incorporated -> Critic approves the loop -> done.
"""

from __future__ import annotations

import os
from typing import Optional

from openai import AzureOpenAI
from pydantic import BaseModel

from medlearn.assessment_agent import AssessmentAgent
from medlearn.critic_agent import CriticAgent
from medlearn.engagement_agent import EngagementAgent
from medlearn.learning_path_curator import LearningPathCurator
from medlearn.manager_insights_agent import ManagerInsightsAgent
from medlearn.study_plan_generator import StudyPlanGenerator
from medlearn.data_loader import load_learners
from medlearn.telemetry import setup_telemetry, span, set_attributes
from medlearn.models import (
    AssessmentResult,
    CriticReviewSummary,
    CriticVerdict,
    CuratorRecommendation,
    EngagementDecision,
    LearnerJourneyReport,
    ManagerInsight,
    StudyPlan,
)


# Max times the Critic can force a regeneration before giving up
MAX_REGEN_ATTEMPTS = 1


def _summarize(verdict: CriticVerdict, regenerated: bool = False) -> CriticReviewSummary:
    """Compact a full CriticVerdict into the embedded summary form."""
    return CriticReviewSummary(
        verdict=verdict.verdict,
        quality_score=verdict.overall_quality_score,
        regenerated=regenerated,
    )


def _resolve_team_id(learner_id: str) -> str:
    """Look up which team a learner belongs to."""
    for learner in load_learners().learners:
        if learner.learner_id == learner_id:
            return learner.team_id
    raise ValueError(f"Unknown learner_id: {learner_id}")


class Orchestrator:
    """The MedLearn AI Orchestrator.

    Usage:
        orchestrator = Orchestrator()
        report = orchestrator.run_journey(
            learner_id="CLN-N-001",
            target_cert_id="CCRN-2024",
        )
        print(f"Pipeline status: {report.pipeline_status}")
        print(f"Critic regenerations: {report.total_critic_regenerations}")
    """

    def __init__(self, client: Optional[AzureOpenAI] = None, verbose: bool = True) -> None:
        """Initialize all 6 agents sharing the same client if provided."""
        self.verbose = verbose

        # Build a single client and share across agents (saves connection overhead)
        if client is None:
            client = self._build_shared_client()

        self.curator = LearningPathCurator(client=client)
        self.study_plan = StudyPlanGenerator(client=client)
        self.engagement = EngagementAgent(client=client)
        self.assessment = AssessmentAgent(client=client)
        self.manager = ManagerInsightsAgent(client=client)
        self.critic = CriticAgent(client=client)

    @staticmethod
    def _build_shared_client() -> AzureOpenAI:
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

    def _log(self, message: str) -> None:
        if self.verbose:
            print(f"  [orchestrator] {message}")

    # ------------------------------------------------------------------
    # Generic critic-regeneration helper
    # ------------------------------------------------------------------

    def _review_with_regen(
        self,
        agent_name: str,
        original_output: BaseModel,
        regenerate_fn,
    ) -> tuple[BaseModel, CriticReviewSummary, int]:
        """Review an agent's output. If Critic says NEEDS_REVISION, regenerate.

        Args:
            agent_name: Name passed to Critic ('LearningPathCurator', etc.)
            original_output: Pydantic object from the agent.
            regenerate_fn: Zero-arg callable that re-runs the original agent
                           and returns a new Pydantic object.

        Returns:
            (final_output, summary, regen_count)
        """
        with span("critic.review", {"medlearn.agent": agent_name}) as _rs:
            verdict = self.critic.review(agent_name, original_output)
            set_attributes(_rs, {
                "medlearn.verdict": verdict.verdict,
                "medlearn.quality_score": verdict.overall_quality_score,
            })
        self._log(
            f"Critic on {agent_name}: {verdict.verdict} "
            f"(quality {verdict.overall_quality_score:.2f})"
        )

        regen_count = 0
        final_output = original_output

        if verdict.verdict == "NEEDS_REVISION" and regen_count < MAX_REGEN_ATTEMPTS:
            self._log(f"Regenerating {agent_name} based on critic feedback...")
            with span("critic.regeneration", {"medlearn.agent": agent_name}) as _gs:
                try:
                    final_output = regenerate_fn()
                    regen_count += 1
                    # Re-review the regenerated output
                    verdict = self.critic.review(agent_name, final_output)
                    set_attributes(_gs, {
                        "medlearn.verdict_after_regen": verdict.verdict,
                        "medlearn.quality_after_regen": verdict.overall_quality_score,
                    })
                    self._log(
                        f"Critic re-review of {agent_name}: {verdict.verdict} "
                        f"(quality {verdict.overall_quality_score:.2f})"
                    )
                except Exception as exc:
                    self._log(f"Regeneration failed for {agent_name}: {exc}")

        return final_output, _summarize(verdict, regenerated=regen_count > 0), regen_count

    # ------------------------------------------------------------------
    # Main pipeline
    # ------------------------------------------------------------------

    def run_journey(
        self,
        learner_id: str,
        target_cert_id: Optional[str] = None,
    ) -> LearnerJourneyReport:
        """Run the complete MedLearn AI pipeline for one learner.

        Args:
            learner_id: e.g. 'CLN-N-001'.
            target_cert_id: Optional explicit target cert. If None, the
                            Curator picks one based on the learner's role
                            and history.

        Returns:
            LearnerJourneyReport with all agent outputs + critic summaries.
        """
        setup_telemetry()
        self._log(f"=== Starting journey for {learner_id} ===")
        total_regens = 0

        # -------- Stage 1: Curator --------
        self._log("Stage 1: Learning Path Curator")
        with span("stage.curator", {"medlearn.learner_id": learner_id}):
            curator_output: CuratorRecommendation = self.curator.recommend(
                learner_id=learner_id, target_cert_id=target_cert_id
            )

            curator_output, curator_review, n = self._review_with_regen(
                "LearningPathCurator",
                curator_output,
                regenerate_fn=lambda: self.curator.recommend(
                    learner_id=learner_id, target_cert_id=target_cert_id
                ),
            )
        total_regens += n

        # The Curator chose the cert; use it for downstream agents
        chosen_cert_id = curator_output.target_certification_id

        # -------- Stage 2: Study Plan --------
        self._log("Stage 2: Study Plan Generator")
        with span("stage.study_plan", {"medlearn.cert": chosen_cert_id}):
            plan_output: StudyPlan = self.study_plan.generate(
                learner_id=learner_id, target_cert_id=chosen_cert_id
            )
            plan_output, plan_review, n = self._review_with_regen(
                "StudyPlanGenerator",
                plan_output,
                regenerate_fn=lambda: self.study_plan.generate(
                    learner_id=learner_id, target_cert_id=chosen_cert_id
                ),
            )
        total_regens += n

        # -------- Stage 3: Engagement --------
        self._log("Stage 3: Engagement Agent")
        engagement_occasion = (
            f"Study reminder for {chosen_cert_id}, Week 1 of {plan_output.total_weeks} "
            f"({plan_output.weeks[0].focus_topics[0] if plan_output.weeks else 'first module'})"
        )
        with span("stage.engagement", {"medlearn.learner_id": learner_id}):
            engagement_output: EngagementDecision = self.engagement.decide(
                learner_id=learner_id, occasion=engagement_occasion
            )
            engagement_output, engagement_review, n = self._review_with_regen(
                "EngagementAgent",
                engagement_output,
                regenerate_fn=lambda: self.engagement.decide(
                    learner_id=learner_id, occasion=engagement_occasion
                ),
            )
        total_regens += n

        escalation_triggered = engagement_output.action == "REFUSE_AND_ESCALATE"
        if escalation_triggered:
            self._log("Engagement returned REFUSE_AND_ESCALATE -> routing to Manager Insights")

        # -------- Stage 4: Assessment --------
        self._log("Stage 4: Assessment Agent")
        with span("stage.assessment", {"medlearn.cert": chosen_cert_id}):
            assessment_output: AssessmentResult = self.assessment.assess(
                learner_id=learner_id, target_cert_id=chosen_cert_id
            )
            assessment_output, assessment_review, n = self._review_with_regen(
                "AssessmentAgent",
                assessment_output,
                regenerate_fn=lambda: self.assessment.assess(
                    learner_id=learner_id, target_cert_id=chosen_cert_id
                ),
            )
        total_regens += n

        # -------- Stage 5: Manager Insights (only if escalation fired) --------
        manager_output: Optional[ManagerInsight] = None
        manager_review: Optional[CriticReviewSummary] = None

        if escalation_triggered:
            self._log("Stage 5: Manager Insights Agent (escalation path)")
            team_id = _resolve_team_id(learner_id)

            escalation_note = (
                f"Engagement Agent refused to send a study reminder for {chosen_cert_id}. "
                f"{engagement_output.escalation_note}"
            )

            with span("stage.manager_insights", {"medlearn.team_id": team_id}):
                manager_output = self.manager.analyze(
                    team_id=team_id, escalation_note=escalation_note
                )
                manager_output, manager_review, n = self._review_with_regen(
                    "ManagerInsightsAgent",
                    manager_output,
                    regenerate_fn=lambda: self.manager.analyze(
                        team_id=team_id, escalation_note=escalation_note
                    ),
                )
            total_regens += n
        else:
            self._log("Stage 5: Manager Insights skipped (no escalation)")

        # -------- Build final report --------
        self._log(f"=== Journey complete. Total regenerations: {total_regens} ===")

        # Determine overall status
        reviews = [curator_review, plan_review, engagement_review, assessment_review]
        if manager_review:
            reviews.append(manager_review)

        all_approved = all(r.verdict == "APPROVED" for r in reviews)
        any_rejected = any(r.verdict == "REJECTED" for r in reviews)

        if any_rejected:
            status = "failure"
        elif all_approved:
            status = "success"
        else:
            status = "partial_failure"

        return LearnerJourneyReport(
            learner_id=learner_id,
            target_certification_id=chosen_cert_id,
            curator_recommendation=curator_output,
            curator_review=curator_review,
            study_plan=plan_output,
            study_plan_review=plan_review,
            engagement_decision=engagement_output,
            engagement_review=engagement_review,
            assessment_result=assessment_output,
            assessment_review=assessment_review,
            manager_insight=manager_output,
            manager_review=manager_review,
            escalation_triggered=escalation_triggered,
            total_critic_regenerations=total_regens,
            pipeline_status=status,
        )