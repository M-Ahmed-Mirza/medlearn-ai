# MedLearn AI — Architecture

> A multi-agent system for healthcare workforce certification, built for the Microsoft Agents League Hackathon 2026 (Reasoning Agents track).

---

## 🏗️ System Overview

MedLearn AI is a coordinated team of **6 specialized AI agents** that reason together about a hospital's clinical learning operations. Each agent is a single-purpose reasoning engine with structured Pydantic output, citations, and confidence scoring. A **Critic Agent** reviews every output before delivery, and an **Orchestrator** routes data between agents — including ethical escalations when the Engagement Agent refuses to push burnt-out staff.

```mermaid
flowchart TB
    User([👤 Clinical Manager<br/>or Demo User])

    subgraph DataLayer["🗄️ Synthetic Data Layer"]
        Learners["learners.json<br/>(6 synthetic clinical staff)"]
        Certs["certifications.json<br/>(8 certification types)"]
        Signals["work_signals.json<br/>(shifts, burnout, workload)"]
        Teams["team_reports.json<br/>(aggregate team metrics)"]
        Grounding["📚 Grounding docs<br/>(clinical, workload, CME)"]
    end

    Orchestrator{{"🏗️ Orchestrator<br/>(coordinates all 6 agents,<br/>routes escalations,<br/>triggers Critic regeneration)"}}

    subgraph Agents["🤖 Six Specialized Agents"]
        Curator["🎓 Learning Path Curator<br/>recommends next cert with<br/>citations + alternatives"]
        StudyPlan["📅 Study Plan Generator<br/>builds shift-aware<br/>week-by-week schedule"]
        Engagement["🔔 Engagement Agent<br/>SEND / RESCHEDULE / REFUSE_ESCALATE"]
        Assessment["📝 Assessment Agent<br/>generates practice questions<br/>+ predicts readiness"]
        Manager["📊 Manager Insights<br/>team dashboard<br/>(receives escalations)"]
        Critic["🧪 Critic Agent<br/>reviews ALL outputs<br/>APPROVED / NEEDS_REVISION / REJECTED"]
    end

    Foundry["☁️ Microsoft Foundry<br/>GPT-4o with structured outputs<br/>(Pydantic-typed Pipelines)"]

    User -->|picks learner + cert| Orchestrator
    DataLayer -.->|reads context| Orchestrator
    Orchestrator -->|invokes| Curator
    Orchestrator -->|invokes| StudyPlan
    Orchestrator -->|invokes| Engagement
    Orchestrator -->|invokes| Assessment
    Orchestrator -.->|invokes if escalation| Manager
    Curator -.->|output reviewed by| Critic
    StudyPlan -.->|output reviewed by| Critic
    Engagement -.->|output reviewed by| Critic
    Assessment -.->|output reviewed by| Critic
    Manager -.->|output reviewed by| Critic
    Agents -->|API calls| Foundry
    Orchestrator -->|returns| User

    classDef agentStyle fill:#1f6feb,stroke:#58a6ff,color:#fff
    classDef criticStyle fill:#bf3989,stroke:#ff7eb6,color:#fff
    classDef dataStyle fill:#3a3a4f,stroke:#8b949e,color:#fff
    classDef orchStyle fill:#1a7f37,stroke:#3fb950,color:#fff
    classDef userStyle fill:#9e6a03,stroke:#d29922,color:#fff

    class Curator,StudyPlan,Engagement,Assessment,Manager agentStyle
    class Critic criticStyle
    class Learners,Certs,Signals,Teams,Grounding dataStyle
    class Orchestrator orchStyle
    class User userStyle
```

---

## 🔄 Pipeline Flow (Detailed)

The Orchestrator runs all 6 agents in sequence, with the Critic reviewing each output. When the Engagement Agent refuses to send a reminder (high-burnout learner), the Orchestrator routes the escalation to Manager Insights — closing the ethical loop in code.

```mermaid
sequenceDiagram
    participant U as 👤 User
    participant O as 🏗️ Orchestrator
    participant C as 🎓 Curator
    participant SP as 📅 Study Plan
    participant E as 🔔 Engagement
    participant A as 📝 Assessment
    participant M as 📊 Manager Insights
    participant K as 🧪 Critic

    U->>O: run_journey(learner_id, target_cert)

    rect rgb(31, 111, 235)
    note over O,C: Stage 1 — Learning Path Curator
    O->>C: recommend(learner, target_cert)
    C-->>O: CuratorRecommendation
    O->>K: review("LearningPathCurator", output)
    K-->>O: APPROVED ✅ (quality 0.90)
    end

    rect rgb(31, 111, 235)
    note over O,SP: Stage 2 — Study Plan Generator
    O->>SP: generate(learner, cert)
    SP-->>O: StudyPlan (6 weeks, burnout-aware)
    O->>K: review("StudyPlanGenerator", output)
    K-->>O: APPROVED ✅ (quality 0.90)
    end

    rect rgb(31, 111, 235)
    note over O,E: Stage 3 — Engagement Agent
    O->>E: decide(learner, occasion)
    E-->>O: EngagementDecision (action: REFUSE_AND_ESCALATE)
    O->>K: review("EngagementAgent", output)
    K-->>O: APPROVED ✅ (quality 0.95)
    end

    rect rgb(191, 57, 137)
    note over O,M: 🛑 Ethical Refusal Routed to Manager
    O->>M: analyze(team_id, escalation_note)
    M-->>O: ManagerInsight (with escalation as Critical concern)
    O->>K: review("ManagerInsightsAgent", output)
    K-->>O: APPROVED ✅ (quality 0.90)
    end

    rect rgb(31, 111, 235)
    note over O,A: Stage 4 — Assessment Agent
    O->>A: assess(learner, cert)
    A-->>O: AssessmentResult (5 questions, Approaching Ready)
    O->>K: review("AssessmentAgent", output)
    K-->>O: APPROVED ✅ (quality 0.90)
    end

    O-->>U: LearnerJourneyReport (full reasoning trace)
```

---

## 🛑 The Ethical Refusal Pattern

MedLearn AI's signature behavior: the Engagement Agent **refuses to send study reminders to high-burnout learners**, regardless of deadline urgency. Instead, the case is escalated to a manager for workload review. This is duty-of-care in code.

```mermaid
flowchart LR
    Start([Reminder<br/>occasion arrives])
    Check{Burnout<br/>indicator?}
    Low[🟢 LOW burnout<br/>Send warm, brief reminder]
    Moderate[🟡 MODERATE burnout<br/>Reschedule to<br/>preferred window]
    High[🔴 HIGH burnout]

    Refuse[/"🛑 REFUSE_AND_ESCALATE<br/>• No message to learner<br/>• Escalation note generated<br/>• Confidence: 1.00<br/>• Safety flag raised"\]

    Manager[📊 Manager Insights<br/>receives escalation<br/>as Critical concern]

    Action1[💬 Learner receives<br/>gentle message]
    Action2[📅 Reminder<br/>rescheduled]

    Start --> Check
    Check -->|Low| Low
    Check -->|Moderate| Moderate
    Check -->|High| High
    High --> Refuse
    Refuse --> Manager
    Low --> Action1
    Moderate --> Action2

    classDef refuseStyle fill:#cf222e,stroke:#ff7b72,color:#fff
    classDef warnStyle fill:#bf8700,stroke:#d29922,color:#fff
    classDef okStyle fill:#1a7f37,stroke:#3fb950,color:#fff
    classDef neutralStyle fill:#3a3a4f,stroke:#8b949e,color:#fff

    class Refuse,High,Manager refuseStyle
    class Moderate,Action2 warnStyle
    class Low,Action1 okStyle
    class Start,Check neutralStyle
```

---

## 🧪 The Self-Correction Loop (Critic Regeneration)

Every agent's output passes through the Critic Agent before being delivered. The Critic uses **per-type checklists** to find specific failure modes (citation hallucinations, math errors, missing safety flags, ethical violations). When the Critic returns `NEEDS_REVISION`, the Orchestrator re-runs the upstream agent with the Critic's feedback.

```mermaid
flowchart TB
    Agent[🤖 Any agent produces output<br/>e.g., CuratorRecommendation]
    Critic{🧪 Critic Agent reviews<br/>using per-type checklist}
    Approved[✅ APPROVED<br/>quality ≥ 0.8]
    Revision[🟡 NEEDS_REVISION<br/>quality 0.4-0.8]
    Rejected[🔴 REJECTED<br/>quality < 0.4]
    Regen[🔄 Re-run upstream agent<br/>with regeneration_prompt]
    Deliver[📤 Delivered to user]
    Escalate[🚨 Surfaced to safety_flags<br/>NOT delivered]

    Agent --> Critic
    Critic -->|verdict| Approved
    Critic -->|verdict| Revision
    Critic -->|verdict| Rejected
    Approved --> Deliver
    Revision --> Regen
    Regen --> Agent
    Rejected --> Escalate

    classDef approvedStyle fill:#1a7f37,stroke:#3fb950,color:#fff
    classDef warnStyle fill:#bf8700,stroke:#d29922,color:#fff
    classDef refuseStyle fill:#cf222e,stroke:#ff7b72,color:#fff
    classDef neutralStyle fill:#3a3a4f,stroke:#8b949e,color:#fff

    class Approved,Deliver approvedStyle
    class Revision,Regen warnStyle
    class Rejected,Escalate refuseStyle
    class Agent,Critic neutralStyle
```

---

## 📦 V1.5 Differentiators

These are the design decisions that set MedLearn AI apart from typical multi-agent submissions:

| # | Differentiator | Implementation |
|---|---|---|
| 1 | **Visible reasoning** | Every agent output includes `rationale`, `confidence`, `citations`, and `alternatives_considered` fields |
| 2 | **Ethical refusal** | Engagement Agent's `REFUSE_AND_ESCALATE` action; no message sent to learner, escalation routed to manager |
| 3 | **Inter-agent escalation** | Engagement Agent's refusal automatically triggers Manager Insights Agent through the Orchestrator |
| 4 | **Self-correction loop** | Critic Agent reviews all outputs with per-type checklists; triggers regeneration with feedback |
| 5 | **Burnout-aware intensity** | Study Plan Generator caps weekly hours at 40% of focus capacity for high-burnout learners |
| 6 | **Aggregate-only manager views** | Manager Insights uses team-level data and never names individuals (privacy compliance) |
| 7 | **Confidence calibration** | Critic flags incoherent outputs (e.g., high confidence + safety flags = quality reduction) |

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| 🤖 LLM | GPT-4o (deployed in Microsoft Foundry, East US 2) |
| 🐍 Language | Python 3.12 |
| 📜 Framework | Microsoft Agent Framework v1.7.0 |
| 📋 Validation | Pydantic (structured outputs via `client.beta.chat.completions.parse()`) |
| 🖥️ UI | Streamlit |
| ☁️ Hosting | Microsoft Foundry + Azure subscription |
| 📊 API version | `2024-12-01-preview` (required for structured outputs) |

---

## 🗂️ File Layout

```
medlearn-ai/
├── medlearn/                       # Core package (renamed from 'agents/' to avoid pip collision)
│   ├── orchestrator.py             # Coordinates all 6 agents + regen loops + escalation
│   ├── learning_path_curator.py    # Agent 1
│   ├── study_plan_generator.py     # Agent 2
│   ├── engagement_agent.py         # Agent 3 (ethical refusal)
│   ├── assessment_agent.py         # Agent 4
│   ├── manager_insights_agent.py   # Agent 5 (escalation receiver)
│   ├── critic_agent.py             # Agent 6 (reviews 1-5)
│   ├── grounding.py                # Loads .md grounding docs
│   ├── data_loader.py              # Reads synthetic data files
│   └── models/
│       ├── agent_response.py       # All structured-output Pydantic schemas
│       ├── learner.py / certification.py / work_signal.py / team_report.py
│       └── enums.py
├── data/                           # Synthetic data + grounding docs
│   ├── learners.json
│   ├── certifications.json
│   ├── work_signals.json
│   ├── team_reports.json
│   └── docs/
│       ├── clinical_certification_guide.md
│       ├── workload_correlation_report.md
│       └── cme_compliance_handbook.md
├── scripts/                        # Smoke tests (one per agent + orchestrator)
│   ├── test_curator.py
│   ├── test_study_plan.py
│   ├── test_engagement.py
│   ├── test_assessment.py
│   ├── test_manager_insights.py
│   ├── test_critic.py
│   └── test_orchestration.py
├── tests/                          # Pydantic schema + data integrity tests
│   └── test_data_loading.py
├── docs/
│   └── architecture.md             # ← You are here
├── medlearn_ui.py                  # Streamlit demo UI (project root)
├── requirements.txt
├── .env                            # gitignored — Foundry credentials
└── README.md
```

---

## ⚙️ Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure .env with your Foundry credentials
#    AZURE_AI_PROJECT_ENDPOINT=https://...
#    AZURE_AI_API_KEY=...
#    AZURE_AI_MODEL_DEPLOYMENT=medlearn-gpt-4o

# 3. Run end-to-end pipeline
python -m scripts.test_orchestration

# 4. Launch the demo UI
streamlit run medlearn_ui.py
```

---

*MedLearn AI — Reasoning, citing, reviewing, and ethical. Built for the Microsoft Agents League Hackathon 2026.*
