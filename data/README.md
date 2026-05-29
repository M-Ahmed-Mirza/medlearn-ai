# 📊 MedLearn AI — Synthetic Data

> ⚠️ **ALL DATA IN THIS FOLDER IS SYNTHETIC.** No real patient data, employee data, or PII is used. All identifiers (e.g. `CLN-N-001`, `CCRN-2024`, `TEAM-ICU-NIGHT`) are clearly fabricated for demonstration purposes only.

This folder contains the synthetic dataset that powers MedLearn AI's multi-agent reasoning system. The data is designed to demonstrate realistic healthcare workforce certification scenarios across three clinical role categories while remaining clearly fictional.

---

## 📂 File Inventory

| File | Purpose | Feeds Which IQ Layer |
|------|---------|---------------------|
| `learners.json` | 6 synthetic clinical staff profiles across 3 roles | Fabric IQ |
| `certifications.json` | 8 synthetic certification types with skills, hours, cycles | Fabric IQ |
| `work_signals.json` | Shift patterns, focus hours, burnout signals | Work IQ |
| `team_reports.json` | Team-level aggregates for Manager Insights | Work IQ + Fabric IQ |
| `docs/clinical_certification_guide.md` | Synthetic certification pathways reference | Foundry IQ |
| `docs/workload_correlation_report.md` | Synthetic analytical insights | Foundry IQ |
| `docs/cme_compliance_handbook.md` | Synthetic compliance policy reference | Foundry IQ |

---

## 🏥 Clinical Roles Covered

| Role Code | Role Name | Count |
|-----------|-----------|-------|
| `RN_CCU` | Critical Care Registered Nurse | 2 |
| `PHARM_HOSP` | Hospital Pharmacist | 2 |
| `MLT_LAB` | Medical Laboratory Technician | 2 |

---

## 🪪 Identifier Convention

All identifiers follow clearly synthetic patterns:

- **Learners:** `CLN-{ROLE_INITIAL}-{NNN}` → e.g. `CLN-N-001` (nurse), `CLN-P-001` (pharmacist), `CLN-L-001` (lab tech)
- **Certifications:** `{CERT_CODE}-{YEAR}` → e.g. `CCRN-2024`, `HIPAA-ANNUAL-2026`
- **Teams:** `TEAM-{DEPT}-{SHIFT/SUB}` → e.g. `TEAM-ICU-NIGHT`, `TEAM-LAB-CHEM`
- **Departments:** `DEPT-{NAME}` → e.g. `DEPT-ICU-A`, `DEPT-PHARMACY`

Every record contains a `"synthetic_data": true` flag for explicit transparency.

---

## 🛡️ Compliance with Hackathon Synthetic Data Rules

Per the Microsoft Agents League Hackathon Reasoning Agents Starter Kit:

- ✅ Uses clearly fabricated identifiers (`CLN-N-001`, `CCRN-2024`, `TEAM-A`)
- ✅ No real names, email addresses, document titles, or customer records
- ✅ Examples are representative but obviously fictional
- ✅ README explicitly states synthetic-only usage
- ✅ Every document and dataset includes a synthetic notice

---

## 🔄 Regeneration Notes

If we need to expand the dataset later (e.g. add more learners or roles), maintain:

1. The synthetic naming convention
2. The `"synthetic_data": true` flag on every record
3. The "Synthetic" prefix or notice in all generated documents
4. A diversity of shift patterns, workloads, and burnout indicators to keep reasoning realistic

---

*Last updated: Phase 1 — Data & Domain Modeling*