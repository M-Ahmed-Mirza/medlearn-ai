# Workload and Learning Correlation Report (Synthetic)

> **NOTICE:** This document is synthetic. All statistics, ratios, and observations are fabricated for the MedLearn AI hackathon submission. No real patient or employee data was used.

---

## 1. Purpose

This synthetic report provides analytical insights that the MedLearn AI Engagement Agent and Manager Insights Agent can use to ground their reasoning about realistic study windows, burnout risk, and team-level intervention recommendations.

---

## 2. Synthetic Observations Across Clinical Roles

### 2.1 Critical Care Nurses

**Synthetic correlation:** Nurses working three 12-hour night shifts per week show a 35 percent lower study completion rate compared to day-shift counterparts when learning reminders are sent during traditional 9-to-5 windows. Completion rates improve significantly when reminders are scheduled during the late-morning post-shift recovery period.

**Recommended Engagement Behavior:** For night-shift critical care nurses, the Engagement Agent should default to late-morning (10:00 to 12:00 local time) reminders on non-shift days.

---

### 2.2 Hospital Pharmacists

**Synthetic correlation:** Pharmacists with more than 20 weekly meeting hours show the lowest study completion rates across all role categories (avg 14 hours per quarter vs target 20 hours). On-call status during the preparation period further reduces study completion by an additional 25 percent.

**Recommended Engagement Behavior:** For pharmacists, the Engagement Agent should:
1. Identify protected focus windows (early morning before clinic rounds, or post-shift evening windows)
2. Avoid sending reminders during typical multidisciplinary rounds (10:00 to 12:00)
3. Flag high-meeting-load weeks and suggest schedule rebalancing to the Manager Insights Agent

---

### 2.3 Medical Laboratory Technicians

**Synthetic correlation:** Lab technicians on rotating shifts show the most variable study completion patterns. Those with predictable rotating schedules (announced 4 weeks ahead) maintain 78 percent completion versus 52 percent for those on reactive scheduling.

**Recommended Engagement Behavior:** For lab technicians, the Engagement Agent should adapt reminder timing based on the upcoming week's shift pattern rather than using a fixed schedule.

---

## 3. Universal Workload Insight

Across all roles in this synthetic dataset, learners maintain optimal certification completion when they have:
- 12 to 18 weekly meeting hours
- At least 15 weekly focus hours
- Predictable upcoming schedule visibility of 2 or more weeks

When meeting hours exceed 22 per week, completion drops to under 40 percent regardless of role.

---

## 4. Burnout Risk Indicators

This synthetic dataset uses three workload-based burnout categories:

| Risk Level | Workload Score | Recommended Action |
|---|---|---|
| Low | Below 70 | Standard engagement cadence |
| Moderate | 70 to 80 | Reduce non-essential notifications; offer flexibility |
| High | Above 80 | Pause non-mandatory learning reminders; flag to Manager Insights Agent |

The Engagement Agent should never push exam preparation reminders to learners in the High burnout category, even if their renewal deadline is approaching. Instead, it should escalate to the Manager Insights Agent for capacity rebalancing.

---

## 5. Team Capacity Patterns

**Synthetic finding:** When more than 30 percent of a team has certifications expiring within the same 30-day window, operational risk rises sharply because parallel exam preparation reduces team availability for clinical coverage. The Manager Insights Agent should flag this pattern proactively.

---

## 6. Practice Score and Outcome Relationship

In this synthetic dataset, learners with a practice score average at or above 75 percent passed their certification exam in 84 percent of recorded attempts. Learners below 65 percent passed in only 38 percent of attempts. The Assessment Agent should treat 75 percent as a meaningful readiness threshold across most certifications in this catalog.

---

## 7. Citation Guidance

When agents cite findings from this report they should reference the section number (for example, "Section 2.2 - Hospital Pharmacists"). All findings should be presented as synthetic observations, not real clinical research.

---

*End of synthetic correlation report.*
