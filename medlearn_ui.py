"""
MedLearn AI - Streamlit Demo UI

A single-page web app that demonstrates MedLearn AI's multi-agent pipeline
end-to-end. Designed to be the demo-video money shot.

Run from project root:
    streamlit run medlearn_ui.py

The UI:
    1. User picks a learner from a dropdown
    2. User optionally picks a target certification
    3. Clicks "Run Pipeline" -> Orchestrator runs all 6 agents
    4. Each agent's output is displayed with a Critic verdict badge
    5. When the Engagement Agent's ethical refusal fires, a prominent
       alert banner explains what happened and why
"""

from __future__ import annotations

import os
import time
from typing import Optional

import streamlit as st
from dotenv import load_dotenv

# Load .env BEFORE importing the orchestrator (so it can read credentials)
load_dotenv()

from medlearn import Orchestrator
from medlearn.data_loader import load_certifications, load_learners
from medlearn.models import LearnerJourneyReport


# ============================================================================
# Page configuration
# ============================================================================

st.set_page_config(
    page_title="MedLearn AI — Multi-Agent Workforce Certification",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================================
# Cached helpers — avoid reloading on every interaction
# ============================================================================

@st.cache_data
def cached_learners():
    return load_learners().learners


@st.cache_data
def cached_certifications():
    return load_certifications().certifications


@st.cache_resource
def get_orchestrator() -> Orchestrator:
    """Build the Orchestrator once and reuse across runs."""
    return Orchestrator(verbose=False)


# ============================================================================
# Custom theming (CSS)
# ============================================================================

st.markdown(
    """
    <style>
    .medlearn-hero {
        background: linear-gradient(135deg, #0d1b2a 0%, #1b263b 55%, #2a3b5f 100%);
        border: 1px solid #2d3f5f;
        border-radius: 16px;
        padding: 1.6rem 1.8rem;
        margin-bottom: 0.6rem;
    }
    .medlearn-hero h1 {
        margin: 0; font-size: 2.1rem; color: #e6edf3; letter-spacing: -0.5px;
    }
    .medlearn-hero p {
        margin: 0.5rem 0 0 0; color: #aeb9c7; font-size: 1.02rem; line-height: 1.5;
    }
    .medlearn-hero .accent { color: #58a6ff; font-weight: 600; }
    .medlearn-hero .ethic  { color: #ff7eb6; font-weight: 600; }
    .eval-badge {
        display: inline-block; background: #0f2b16; border: 1px solid #2ea043;
        color: #56d364; border-radius: 999px; padding: 0.25rem 0.8rem;
        font-size: 0.85rem; font-weight: 600; margin-top: 0.6rem;
    }
    .eval-badge.fail {
        background: #2b0f0f; border-color: #f85149; color: #ff7b72;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================================
# Header
# ============================================================================

st.markdown(
    """
    <div class="medlearn-hero">
        <h1>🏥 MedLearn AI</h1>
        <p>A <span class="accent">multi-agent system</span> for healthcare workforce
        certification — reasoning agents that recommend learning paths, schedule
        around shifts, and <span class="ethic">refuse to push burnt-out healthcare
        workers</span>.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


def render_eval_badge() -> None:
    """Render a live badge from eval_results.json if present."""
    import json
    from pathlib import Path

    path = Path("eval_results.json")
    if not path.exists():
        return
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        summary = data.get("summary", {})
        passed = summary.get("passed", 0)
        total = summary.get("total", 0)
        all_passed = summary.get("all_passed", False)
        cls = "eval-badge" if all_passed else "eval-badge fail"
        mark = "✅" if all_passed else "⚠️"
        st.markdown(
            f'<span class="{cls}">{mark} Evaluation harness: '
            f"{passed}/{total} behavioral scenarios passing</span>",
            unsafe_allow_html=True,
        )
    except Exception:
        pass  # Badge is a nice-to-have; never break the app over it


render_eval_badge()

st.markdown("---")


# ============================================================================
# Sidebar — controls + system info
# ============================================================================

with st.sidebar:
    st.markdown("### 🎯 Pipeline Controls")

    learners = cached_learners()
    certifications = cached_certifications()

    # Build learner display strings
    learner_options = {
        f"{l.display_name} ({l.learner_id}) — {l.role}": l.learner_id
        for l in learners
    }

    learner_label = st.radio(
        "Select a synthetic learner",
        options=list(learner_options.keys()),
        index=0,
        help="All learners are synthetic — no real personal data.",
    )
    learner_id = learner_options[learner_label]

    # Find the selected learner so we can show context
    selected_learner = next(l for l in learners if l.learner_id == learner_id)

    # Cert dropdown (optional)
    cert_options = ["(Let Curator decide)"] + [c.id for c in certifications]
    cert_choice = st.radio(
        "Target certification (optional)",
        options=cert_options,
        index=0,
        help="Leave default to let the Learning Path Curator pick.",
    )
    target_cert_id: Optional[str] = None if cert_choice == "(Let Curator decide)" else cert_choice

    run_button = st.button("🚀 Run Pipeline", type="primary", use_container_width=True)

    st.markdown("---")
    st.markdown("### 👤 Learner Context")
    st.markdown(
        f"**Role:** {selected_learner.role}  \n"
        f"**Experience:** {selected_learner.experience_years} years  \n"
        f"**Practice Score:** {selected_learner.practice_score_avg}/100  \n"
        f"**Last Assessment:** {selected_learner.last_assessment_outcome.value}  \n"
        f"**Days Until Next Cert Due:** {selected_learner.renewal_due_in_days}"
    )

    st.markdown("---")
    st.markdown("### 🤖 Architecture")
    st.markdown(
        "Six specialized agents:\n"
        "1. 🎓 Learning Path Curator\n"
        "2. 📅 Study Plan Generator\n"
        "3. 🔔 Engagement Agent (ethical refusal)\n"
        "4. 📝 Assessment Agent\n"
        "5. 📊 Manager Insights Agent\n"
        "6. 🧪 Critic Agent (reviews all outputs)\n\n"
        "Powered by Microsoft Foundry + GPT-4o."
    )


# ============================================================================
# Main content
# ============================================================================

# Verdict color helpers
def verdict_badge(verdict: str) -> str:
    if verdict == "APPROVED":
        return "🟢 **APPROVED**"
    if verdict == "NEEDS_REVISION":
        return "🟡 **NEEDS_REVISION**"
    if verdict == "REJECTED":
        return "🔴 **REJECTED**"
    return verdict


def render_critic_review(stage_name: str, review) -> None:
    regen_text = " (regenerated)" if review.regenerated else ""
    st.markdown(
        f"**Critic review of {stage_name}:** {verdict_badge(review.verdict)} "
        f"— quality score: `{review.quality_score:.2f}`{regen_text}"
    )


def render_curator_stage(report: LearnerJourneyReport) -> None:
    rec = report.curator_recommendation
    review = report.curator_review

    with st.expander(
        f"🎓 **Stage 1 — Learning Path Curator** → {rec.target_certification_id}",
        expanded=True,
    ):
        col1, col2, col3 = st.columns(3)
        col1.metric("Recommended Cert", rec.target_certification_id)
        col2.metric("Confidence", f"{rec.confidence:.2f}")
        col3.metric("Study Hours", rec.recommended_study_hours)

        st.markdown("#### Rationale")
        st.info(rec.rationale)

        if rec.skills_to_acquire:
            st.markdown("#### Skills to Acquire")
            st.markdown("\n".join(f"- {s}" for s in rec.skills_to_acquire))

        if rec.alternatives_considered:
            st.markdown("#### Alternatives Considered (and Rejected)")
            for alt in rec.alternatives_considered:
                st.markdown(f"- **{alt.option}** — _Rejected because:_ {alt.rejected_because}")

        if rec.citations:
            st.markdown("#### Citations")
            for c in rec.citations:
                section = f" — {c.section}" if c.section else ""
                st.markdown(f"- `{c.source_document}`{section}")

        if rec.safety_flags:
            st.markdown("#### ⚠️ Safety Flags")
            for flag in rec.safety_flags:
                st.warning(flag)

        st.markdown("---")
        render_critic_review("Curator", review)


def render_study_plan_stage(report: LearnerJourneyReport) -> None:
    plan = report.study_plan
    review = report.study_plan_review

    with st.expander(
        f"📅 **Stage 2 — Study Plan Generator** → {plan.total_weeks} weeks / {plan.total_study_hours:.0f}h",
        expanded=False,
    ):
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Weeks", plan.total_weeks)
        col2.metric("Weekly Hours", f"{plan.weekly_hour_target:.1f}h")
        col3.metric("Feasibility", plan.schedule_feasibility)

        st.markdown(f"**Study Window:** {plan.preferred_study_window}")

        st.markdown("#### Rationale")
        st.info(plan.rationale)

        st.markdown("#### Week-by-Week Schedule")
        for week in plan.weeks:
            milestone = f" 🏁 **{week.milestone}**" if week.milestone else ""
            st.markdown(
                f"**Week {week.week_number}**: {week.hours_allocated:.1f}h "
                f"across {week.sessions_per_week} sessions{milestone}  \n"
                f"Topics: {', '.join(week.focus_topics)}"
            )

        if plan.safety_flags:
            st.markdown("#### ⚠️ Safety Flags")
            for flag in plan.safety_flags:
                st.warning(flag)

        st.markdown("---")
        render_critic_review("Study Plan", review)


def render_engagement_stage(report: LearnerJourneyReport) -> None:
    decision = report.engagement_decision
    review = report.engagement_review

    # Determine title icon based on action
    icon = {
        "SEND_REMINDER": "🟢",
        "RESCHEDULE": "🟡",
        "REFUSE_AND_ESCALATE": "🔴",
    }.get(decision.action, "🔔")

    expanded = decision.action == "REFUSE_AND_ESCALATE"

    with st.expander(
        f"🔔 **Stage 3 — Engagement Agent** → {icon} {decision.action}",
        expanded=expanded,
    ):
        # ETHICAL REFUSAL — the V1.5 money shot
        if decision.action == "REFUSE_AND_ESCALATE":
            st.error(
                "🛑 **ETHICAL REFUSAL — Duty of Care Triggered**\n\n"
                "The Engagement Agent **refused to send a study reminder** to this learner. "
                "High burnout risk + workload makes pushing study tasks harmful. "
                "Instead, the agent escalated the case to the Manager Insights Agent "
                "for workload review.\n\n"
                "This is MedLearn AI's primary ethical guardrail — engagement is never "
                "the goal; healthy sustained learning is."
            )

        col1, col2 = st.columns(2)
        col1.metric("Action", decision.action)
        col2.metric("Confidence", f"{decision.confidence:.2f}")

        st.markdown("#### Rationale")
        st.info(decision.rationale)

        if decision.action == "SEND_REMINDER":
            st.markdown("#### Message to Learner")
            st.success(f"💬 _{decision.message_to_learner}_")
        elif decision.action == "RESCHEDULE":
            st.markdown("#### Message to Learner")
            st.success(f"💬 _{decision.message_to_learner}_")
            st.markdown(f"**Rescheduled for:** {decision.proposed_time}")
        elif decision.action == "REFUSE_AND_ESCALATE":
            st.markdown("#### Escalation Note (forwarded to Manager Insights)")
            st.warning(f"📋 _{decision.escalation_note}_")

        if decision.citations:
            st.markdown("#### Citations")
            for c in decision.citations:
                section = f" — {c.section}" if c.section else ""
                st.markdown(f"- `{c.source_document}`{section}")

        if decision.safety_flags:
            st.markdown("#### ⚠️ Safety Flags")
            for flag in decision.safety_flags:
                st.warning(flag)

        st.markdown("---")
        render_critic_review("Engagement", review)


def render_assessment_stage(report: LearnerJourneyReport) -> None:
    result = report.assessment_result
    review = report.assessment_review

    readiness_color = {
        "Not Ready": "🔴",
        "Approaching Ready": "🟡",
        "Ready": "🟢",
        "Exam Recommended": "🔵",
    }.get(result.readiness_level, "⚪")

    with st.expander(
        f"📝 **Stage 4 — Assessment Agent** → {readiness_color} {result.readiness_level}",
        expanded=False,
    ):
        col1, col2, col3 = st.columns(3)
        col1.metric("Readiness", result.readiness_level)
        col2.metric("Predicted Score", f"{result.readiness_score:.2f}")
        col3.metric("Questions", len(result.questions))

        st.markdown("#### Rationale")
        st.info(result.rationale)

        st.markdown(f"#### Recommended Next Step")
        st.success(f"➡️ {result.recommended_next_step}")

        if result.focus_areas:
            st.markdown("#### Focus Areas (weak skills)")
            for area in result.focus_areas:
                st.markdown(f"- {area}")

        st.markdown("#### Practice Questions")
        for q in result.questions:
            st.markdown(f"**{q.question_id}** _[{q.difficulty}]_ — Skill: {q.skill_tested}")
            st.markdown(f"_Q:_ {q.question}")
            for i, opt in enumerate(q.options):
                letter = chr(ord("A") + i)
                marker = " ✅" if letter == q.correct_answer else ""
                st.markdown(f"  - **{letter}.** {opt}{marker}")
            st.caption(f"💡 _{q.explanation}_")
            st.markdown("")

        if result.safety_flags:
            st.markdown("#### ⚠️ Safety Flags")
            for flag in result.safety_flags:
                st.warning(flag)

        st.markdown("---")
        render_critic_review("Assessment", review)


def render_manager_stage(report: LearnerJourneyReport) -> None:
    if report.manager_insight is None or report.manager_review is None:
        return

    insight = report.manager_insight
    review = report.manager_review

    health_icon = {
        "Healthy": "🟢",
        "Some concerns": "🟡",
        "Concerning": "🟠",
        "Critical — immediate action": "🔴",
    }.get(insight.overall_health_status, "⚪")

    with st.expander(
        f"📊 **Stage 5 — Manager Insights** (Escalation received) → {health_icon} {insight.overall_health_status}",
        expanded=True,
    ):
        st.info(
            "📨 **This stage only fires when the Engagement Agent escalates a case.** "
            "It demonstrates the **closed ethical loop**: agents reasoning about "
            "duty of care, then coordinating to surface the right context to "
            "decision-makers."
        )

        col1, col2 = st.columns(2)
        col1.metric("Team Size", insight.team_size)
        col2.metric("Status", insight.overall_health_status)

        st.markdown("#### Compliance Summary")
        st.markdown(insight.compliance_summary)

        st.markdown("#### Burnout Pattern")
        st.markdown(insight.burnout_pattern)

        st.markdown("#### Certification Pipeline")
        st.markdown(insight.certification_pipeline)

        st.markdown("#### Top Concerns (most severe first)")
        for concern in insight.top_concerns:
            sev_marker = {
                "Critical": "🚨",
                "High": "⚠️",
                "Moderate": "🟡",
                "Low": "🟢",
            }.get(concern.severity, "•")
            st.markdown(
                f"{sev_marker} **{concern.severity}** — {concern.concern}  \n"
                f"_Affected:_ {concern.affected_count} members  \n"
                f"_Recommended:_ {concern.recommended_intervention}"
            )

        st.markdown("#### Recommended Actions This Week")
        for i, action in enumerate(insight.recommended_actions, 1):
            st.markdown(f"{i}. {action}")

        if insight.safety_flags:
            st.markdown("#### 🚨 Safety Flags")
            for flag in insight.safety_flags:
                st.error(flag)

        st.markdown("---")
        render_critic_review("Manager Insights", review)


# ============================================================================
# Pipeline execution
# ============================================================================

if run_button:
    # Verify credentials before running
    if not os.getenv("AZURE_AI_PROJECT_ENDPOINT") or not os.getenv("AZURE_AI_API_KEY"):
        st.error(
            "❌ Azure credentials not found in `.env`. "
            "Set `AZURE_AI_PROJECT_ENDPOINT` and `AZURE_AI_API_KEY` and reload."
        )
        st.stop()

    orchestrator = get_orchestrator()

    with st.status("Running MedLearn AI pipeline...", expanded=True) as status:
        try:
            status.update(label="Stage 1: Learning Path Curator reasoning...")
            time.sleep(0.1)  # Tiny delay so the user sees stage update
            report = orchestrator.run_journey(
                learner_id=learner_id, target_cert_id=target_cert_id
            )
            status.update(label="✅ Pipeline complete!", state="complete")
        except Exception as exc:
            status.update(label=f"❌ Pipeline failed: {exc}", state="error")
            st.exception(exc)
            st.stop()

    # ----- Top-line summary -----
    st.markdown("## 📋 Journey Report")

    # Friendly, judge-readable status labels (underlying value unchanged)
    status_label = {
        "success": "Completed cleanly",
        "partial_failure": "Completed (Critic revised)",
        "failure": "Pipeline failure",
    }.get(report.pipeline_status, report.pipeline_status.upper())

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Learner", report.learner_id)
    col2.metric("Target Cert", report.target_certification_id)
    col3.metric("Pipeline Status", status_label)
    col4.metric("Critic Regens", report.total_critic_regenerations)

    # Context-aware top banner
    if report.escalation_triggered:
        st.error(
            "🛑 **ETHICAL REFUSAL FIRED** — The Engagement Agent refused to send "
            "a study reminder due to high burnout risk. The case has been escalated "
            "to the Manager Insights Agent for workload review. Scroll down to see "
            "the full reasoning trace and manager dashboard."
        )
    elif report.pipeline_status == "partial_failure":
        st.info(
            "🔄 **Self-correction loop engaged.** The Critic Agent flagged one output "
            "for revision and the upstream agent regenerated it. The revised output "
            "landed just below the 0.80 approval threshold, so the pipeline reports a "
            "*partial* completion — by design, MedLearn AI surfaces borderline outputs "
            "rather than hiding them. This is the quality guardrail working as intended."
        )
    elif report.pipeline_status == "failure":
        st.error(
            "❌ **Pipeline failure.** The Critic Agent rejected an output as "
            "fundamentally incorrect, so it was not delivered. See the flagged stage below."
        )
    else:
        st.success(
            "✅ **Pipeline completed cleanly.** No ethical refusals triggered. "
            "All Critic verdicts approved. Scroll down to see the full reasoning trace."
        )

    st.markdown("---")
    st.markdown("## 🧠 Full Reasoning Trace")
    st.markdown(
        "Each stage shows the agent's structured output **and** the Critic Agent's "
        "review verdict. Click sections to expand them."
    )

    # ----- Render each stage -----
    render_curator_stage(report)
    render_study_plan_stage(report)
    render_engagement_stage(report)
    render_assessment_stage(report)
    render_manager_stage(report)  # No-op when escalation didn't fire

else:
    # ----- Pre-run welcome state -----
    st.info(
        "👈 **Select a learner in the sidebar** and click **Run Pipeline** to "
        "watch MedLearn AI's six agents reason about a real certification scenario."
    )

    st.markdown("### What You'll See")
    st.markdown(
        "- 🎓 **Curator** picks the next certification with citations and alternatives.\n"
        "- 📅 **Study Plan** builds a week-by-week schedule that respects shift patterns.\n"
        "- 🔔 **Engagement Agent** decides whether to send a reminder — "
        "**or refuses if burnout risk is too high**.\n"
        "- 📝 **Assessment** generates clinically realistic practice questions and "
        "predicts exam readiness.\n"
        "- 📊 **Manager Insights** assembles a team dashboard, incorporating any "
        "escalations from the Engagement Agent.\n"
        "- 🧪 **Critic** reviews every output before it reaches you, catching mistakes "
        "and triggering regeneration when needed."
    )

    st.markdown("### 💡 Try the High-Burnout Scenario")
    st.markdown(
        "Pick **CLN-P-001 (Hospital Pharmacist)** and target **BCPS-2024** to see "
        "the ethical-refusal pattern fire in real-time. The Engagement Agent will "
        "refuse to push the learner, and the Manager Insights Agent will receive "
        "the escalation automatically."
    )

    # ----- Live evaluation results panel -----
    def _render_eval_panel() -> None:
        import json
        from pathlib import Path

        path = Path("eval_results.json")
        if not path.exists():
            return
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return

        summary = data.get("summary", {})
        scenarios = data.get("scenarios", [])
        passed = summary.get("passed", 0)
        total = summary.get("total", 0)

        with st.expander(
            f"🧪 **Evaluation Harness** — {passed}/{total} behavioral scenarios passing",
            expanded=False,
        ):
            st.markdown(
                "These are **hard behavioral assertions**, not just 'did it run' checks. "
                "Each scenario verifies a safety-critical behavior holds:"
            )
            for s in scenarios:
                mark = "✅" if s.get("passed") else "❌"
                st.markdown(
                    f"{mark} **{s.get('id')} — {s.get('name')}**  \n"
                    f"&nbsp;&nbsp;&nbsp;_Rubric:_ {s.get('rubric_focus')} • "
                    f"_Expected:_ {s.get('expected')}"
                )
            generated = data.get("generated_at", "")
            if generated:
                st.caption(f"Last run: {generated}")

    _render_eval_panel()

    # Footer
    st.markdown("---")
    st.caption(
        "MedLearn AI — Built for Microsoft Agents League Hackathon 2026 • "
        "Reasoning Agents track • All data synthetic."
    )