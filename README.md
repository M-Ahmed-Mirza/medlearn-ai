# 🏥 MedLearn AI

> A six-agent system that helps hospitals manage clinical staff certifications — recommending learning paths, scheduling around shifts, and **refusing to push burnt-out healthcare workers**. Every decision is reasoned, cited, and reviewed by a Critic agent.

**Built for the Microsoft Agents League Hackathon 2026 — Reasoning Agents track.**

![Architecture overview](docs/architecture-overview-dark.png)

---

## The Problem

Hospitals run on certified staff. Nurses must keep CCRN, BLS, and ACLS current. Pharmacists need BCPS. Lab technicians need MLT-ASCP and CLIA compliance. Everyone needs HIPAA renewal. These certifications are legally required, they expire on cycles, and each one demands 20–150 hours of study.

The people who hold them work 12-hour shifts, rotate through nights and on-call, and burn out at high rates. Existing learning-management systems treat all of this as a notification problem: when a deadline approaches, send a reminder. When it's missed, send another. The tooling optimizes for engagement, and engagement is exactly the wrong target for an exhausted clinician whose mistakes carry patient-safety consequences.

There is no tool that reasons about *which* certification a given clinician should pursue next, schedules study around real shift patterns, knows when *not* to push, and gives managers a team-level view without surveilling individuals.

## The Solution

MedLearn AI is that tool, built as a coordinated team of six specialized reasoning agents. It is not a chatbot and not a course catalog. Each agent is a single-purpose reasoning engine that returns structured, validated output with a rationale, a confidence score, and citations to its source material. A dedicated Critic agent reviews every output before it reaches a user, and an Orchestrator routes data between agents — including ethical escalations, when the Engagement agent decides a learner should be left alone.

---

## The Six Agents

| # | Agent | Responsibility |
|---|-------|----------------|
| 1 | 🎓 **Learning Path Curator** | Recommends the next certification for a learner, with citations and explicit alternatives it considered and rejected. |
| 2 | 📅 **Study Plan Generator** | Builds a week-by-week schedule that respects shift patterns, preferred study windows, and burnout-scaled intensity. |
| 3 | 🔔 **Engagement Agent** | Decides whether to send a reminder, reschedule it, or **refuse and escalate** when burnout risk makes pushing harmful. |
| 4 | 📝 **Assessment Agent** | Generates clinically realistic practice questions and honestly predicts exam readiness. |
| 5 | 📊 **Manager Insights Agent** | Produces an aggregate, privacy-preserving team dashboard, and receives escalations from the Engagement agent. |
| 6 | 🧪 **Critic Agent** | Reviews the output of every other agent against per-type checklists, returning APPROVED / NEEDS_REVISION / REJECTED. |

---

## What Makes It Different

MedLearn AI is built around four design commitments that most multi-agent submissions don't make.

**Visible reasoning.** Every agent output carries a `rationale`, a `confidence` score, `citations` to the grounding documents, and — where relevant — the `alternatives_considered` and why they were rejected. Judges can see *how* the system thinks, not just what it concludes.

**Ethical refusal.** When a learner's burnout indicator is high, the Engagement agent returns `REFUSE_AND_ESCALATE`. No reminder is sent. Instead an escalation note is routed to the Manager Insights agent for workload review. Engagement is never the goal; healthy, sustained learning is. This is duty-of-care implemented in code.

**Inter-agent escalation.** The Engagement agent's refusal doesn't end the pipeline — it triggers the Manager Insights agent automatically through the Orchestrator, so the refusal becomes a manager-visible concern. The loop closes.

**Self-correction.** The Critic agent reviews all five other agents using checklists tailored to each output type (catching hallucinated citations, broken math in study plans, missing safety flags, ethics violations). A `NEEDS_REVISION` verdict makes the Orchestrator re-run the upstream agent with the Critic's feedback.

---

## The Signature Moment: Ethical Refusal

Pick the high-burnout pharmacist (`CLN-P-001`) and run the pipeline. The Engagement agent reasons through the learner's burnout indicator, current workload, and on-call status — then refuses to send a study reminder, with full confidence:

```
Action: REFUSE_AND_ESCALATE   (confidence 1.00)
Message to learner: (none — we do not push high-burnout staff)
Escalation note: "High burnout risk and current workload. Recommend
                  workload review before intensifying study."
Safety flag: burnout-driven refusal
```

That escalation flows to the Manager Insights agent, which surfaces it as a Critical concern on the team dashboard. Two agents reasoned together to protect a clinician — and the Critic approved both decisions.

---

## Architecture

A full breakdown — including the pipeline sequence diagram, the ethical-refusal decision tree, and the Critic self-correction loop — lives in **[docs/architecture.md](docs/architecture.md)**.

At a high level: the Orchestrator reads learner context from a synthetic data layer, invokes each agent in turn, passes every output through the Critic, routes escalations to Manager Insights, and returns a single `LearnerJourneyReport` with the complete reasoning trace.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| LLM | GPT-4o, deployed in Microsoft Foundry (East US 2) |
| Framework | Microsoft Agent Framework |
| Language | Python 3.12 |
| Structured output | Pydantic via `client.beta.chat.completions.parse()` |
| UI | Streamlit |
| API version | `2024-12-01-preview` (required for structured outputs) |

All data is synthetic. Learner identifiers follow obvious patterns (`CLN-N-001`, `TEAM-ICU-NIGHT`) and every record carries a `synthetic_data: true` flag enforced by Pydantic validators. No real patient or staff information is used anywhere.

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure .env with your Microsoft Foundry credentials
#    AZURE_AI_PROJECT_ENDPOINT=https://...
#    AZURE_AI_API_KEY=...
#    AZURE_AI_MODEL_DEPLOYMENT=medlearn-gpt-4o

# 3. Run the full six-agent pipeline end to end
python -m scripts.test_orchestration

# 4. Launch the interactive demo UI
streamlit run medlearn_ui.py
```

The demo UI lets you pick any of six synthetic learners, optionally choose a target certification (or let the Curator decide autonomously), and watch all six agents reason through the journey — with each Critic verdict shown inline.

---

## Try These Scenarios

| Learner | Target | What you'll see |
|---------|--------|-----------------|
| `CLN-N-001` (Critical Care RN, recent fail) | *Let Curator decide* | Curator autonomously picks CCRN, rejects HIPAA and Infection-Control with reasons; Assessment honestly returns "Not Ready". |
| `CLN-P-001` (Pharmacist, high burnout, on-call) | `BCPS-2024` | **Ethical refusal fires.** Engagement refuses, escalation routes to Manager Insights. |
| `CLN-L-001` (Lab Tech, low burnout) | `BLS-2024` | Clean path: warm reminder sent, short study plan, Ready/Approaching assessment. |

---

## Repository Layout

```
medlearn-ai/
├── medlearn/                    # Core package
│   ├── orchestrator.py          # Coordinates all 6 agents, regen loops, escalation
│   ├── learning_path_curator.py # Agent 1
│   ├── study_plan_generator.py  # Agent 2
│   ├── engagement_agent.py      # Agent 3 — ethical refusal
│   ├── assessment_agent.py      # Agent 4
│   ├── manager_insights_agent.py# Agent 5 — escalation receiver
│   ├── critic_agent.py          # Agent 6 — reviews 1–5
│   ├── grounding.py             # Loads grounding documents
│   ├── data_loader.py           # Reads synthetic data
│   └── models/                  # Pydantic schemas (all structured outputs)
├── data/                        # Synthetic learners, certs, signals, team reports
│   └── docs/                    # Grounding documents
├── scripts/                     # One smoke test per agent + orchestrator
├── tests/                       # Schema + data-integrity tests
├── docs/architecture.md         # Full architecture with diagrams
├── medlearn_ui.py               # Streamlit demo
└── README.md
```

---

## Judging Rubric Alignment

| Criterion | How MedLearn AI addresses it |
|-----------|------------------------------|
| Accuracy & Relevance | Role-correct certification recommendations; clinically realistic questions; honest readiness scoring. |
| Reasoning & Multi-step Thinking | Alternatives considered and rejected; Critic self-correction loop; inter-agent escalation. |
| Creativity & Originality | Burnout-aware ethical refusal; manager escalation routing; generic-but-checklist-driven Critic. |
| UX & Presentation | Streamlit dashboard with full inline reasoning trace and Critic verdicts. |
| Reliability & Safety | Ethical refusal; Critic catches errors; safety flags; aggregate-only manager views. |

---

*MedLearn AI — reasoning, citing, reviewing, and ethical. All data synthetic.*