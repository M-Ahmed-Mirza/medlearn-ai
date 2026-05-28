# 🧠 MedLearn AI

> A multi-agent system for healthcare workforce certification management — built on Microsoft Foundry for the Microsoft Agents League Hackathon 2026.

[![Track](https://img.shields.io/badge/Track-Reasoning%20Agents-blueviolet)]()
[![Status](https://img.shields.io/badge/Status-In%20Development-yellow)]()
[![Python](https://img.shields.io/badge/Python-3.12-blue)]()

---

## 🎯 The Problem

Healthcare organizations lose millions annually when clinical staff miss certification renewal deadlines — CME credits, HIPAA compliance, role-specific certifications (CCRN, BLS, ACLS), and continuing education requirements. Manual tracking is error-prone, study schedules ignore clinical shift realities, and managers lack visibility into team compliance risk until it's too late.

## 💡 The Solution

**MedLearn AI** is a multi-agent reasoning system that helps healthcare organizations manage workforce certification at scale. Built on **Microsoft Foundry** with **Foundry IQ**, **Work IQ**, and **Fabric IQ**, it turns certification compliance from a manual chase into an intelligent, role-aware learning operation.

## 🏗️ Architecture

MedLearn AI orchestrates **five specialized agents** working together:

| Agent | Role | Grounding |
|-------|------|-----------|
| 🎓 **Learning Path Curator** | Maps clinical roles to required certifications | Foundry IQ |
| 📅 **Study Plan Generator** | Builds schedules respecting clinical shift patterns | Fabric IQ |
| 🔔 **Engagement Agent** | Schedules learning around shifts, not meetings | Work IQ |
| 📝 **Assessment Agent** | Generates cited practice questions from approved clinical guidelines | Foundry IQ |
| 📊 **Manager Insights Agent** | Surfaces team compliance risk and renewal deadlines | Work IQ + Fabric IQ |

> 📐 *Architecture diagram coming in Phase 5*

## 🛠️ Tech Stack

- **Microsoft Foundry** — agent orchestration and hosting
- **Microsoft Agent Framework** — local development and multi-agent patterns
- **Foundry IQ** — grounded knowledge retrieval with citations
- **Work IQ** — work-context awareness for scheduling
- **Fabric IQ** — semantic modeling of certifications and roles
- **Microsoft Learn MCP Server** — external knowledge integration
- **Python 3.12** + **Pydantic** + **python-dotenv**

## 📂 Project Structure
    medlearn-ai/
    ├── agents/          # The 5 specialized agents
    ├── data/            # Synthetic healthcare certification data
    ├── docs/            # Architecture, design notes, diagrams
    ├── scripts/         # Setup and utility scripts
    ├── tests/           # Test suite
    ├── .env.example     # Template for environment variables
    ├── requirements.txt # Python dependencies
    └── README.md


## 🚀 Getting Started

### Prerequisites

- Python 3.12+
- Azure subscription (for Microsoft Foundry)
- Git

### Setup

```bash
# Clone the repository
git clone https://github.com/M-Ahmed-Mirza/medlearn-ai.git
cd medlearn-ai

# Create and activate virtual environment
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1   # Windows
# source .venv/bin/activate    # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your Azure credentials
```

## 📊 Synthetic Data Notice

> ⚠️ **All data, identifiers, and documents in this repository are synthetic and for demonstration purposes only.** No real patient data, employee data, or PII is used anywhere in this project.

Identifiers follow clearly fabricated patterns:
- `CLN-1001`, `CLN-1002` — synthetic clinical staff IDs
- `CCRN-2024`, `HIPAA-ANNUAL` — synthetic certification codes
- `TEAM-ICU-A`, `TEAM-ER-B` — synthetic team identifiers

## 🏆 Hackathon Details

- **Event:** Microsoft Agents League Hackathon 2026
- **Track:** Reasoning Agents (Battle #2 — Microsoft Foundry)
- **Submission deadline:** June 14, 2026
- **Winners announced:** June 30, 2026

## 📜 License

This project is built for the Microsoft Agents League Hackathon 2026. License terms will be added prior to submission.

## 🤝 Author

**Muhammad Ahmed Mirza** — Associate AI Engineer
- 🌐 GitHub: [@M-Ahmed-Mirza](https://github.com/M-Ahmed-Mirza)

---

*Built with care for healthcare workers who deserve better tooling.* 💙