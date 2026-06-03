"""
MedLearn AI - Telemetry Instrumentation Patcher

Adds OpenTelemetry @traced decorators to the 6 agent public methods, plus
the telemetry import. Idempotent (safe to run more than once) and verbose
(prints exactly what it changed). Run from project root:

    python -m scripts.add_telemetry_to_agents

This edits files in medlearn/. Review the git diff afterward.
"""

from __future__ import annotations

import re
from pathlib import Path

# (file, public_method_name, span_name)
TARGETS = [
    ("medlearn/learning_path_curator.py", "recommend", "agent.curator.recommend"),
    ("medlearn/study_plan_generator.py", "generate", "agent.study_plan.generate"),
    ("medlearn/engagement_agent.py", "decide", "agent.engagement.decide"),
    ("medlearn/assessment_agent.py", "assess", "agent.assessment.assess"),
    ("medlearn/manager_insights_agent.py", "analyze", "agent.manager_insights.analyze"),
    ("medlearn/critic_agent.py", "review", "agent.critic.review"),
]

IMPORT_LINE = "from medlearn.telemetry import traced"


def patch_file(path: str, method: str, span_name: str) -> str:
    p = Path(path)
    if not p.exists():
        return f"  SKIP {path}: file not found"

    src = p.read_text(encoding="utf-8")
    changed = []

    # 1. Add the telemetry import if missing. Place it after the last
    #    'from medlearn' import to keep import grouping tidy.
    if IMPORT_LINE not in src:
        medlearn_imports = list(
            re.finditer(r"^from medlearn\..*$", src, flags=re.MULTILINE)
        )
        if medlearn_imports:
            last = medlearn_imports[-1]
            insert_at = last.end()
            src = src[:insert_at] + "\n" + IMPORT_LINE + src[insert_at:]
        else:
            # Fallback: after the first 'from openai' import
            m = re.search(r"^from openai .*$", src, flags=re.MULTILINE)
            if m:
                src = src[: m.end()] + "\n" + IMPORT_LINE + src[m.end():]
            else:
                src = IMPORT_LINE + "\n" + src
        changed.append("import")

    # 2. Add the decorator immediately above the method def, matching its
    #    indentation, if not already decorated.
    # Find:  "    def {method}("  (4-space indented method in a class)
    method_pat = re.compile(
        rf"(?P<indent>[ \t]*)def {re.escape(method)}\(", flags=re.MULTILINE
    )
    m = method_pat.search(src)
    if not m:
        return f"  WARN {path}: method '{method}' not found — no decorator added"

    indent = m.group("indent")
    decorator = f"{indent}@traced({span_name!r})\n"

    # Check the line(s) directly above for an existing @traced
    preceding = src[: m.start()]
    if preceding.rstrip().endswith(f"@traced({span_name!r})"):
        already = True
    else:
        already = f"@traced({span_name!r})" in src
    if not already:
        src = src[: m.start()] + decorator + src[m.start():]
        changed.append("decorator")

    if changed:
        p.write_text(src, encoding="utf-8")
        return f"  OK   {path}: added {', '.join(changed)}  (span={span_name})"
    return f"  --   {path}: already instrumented, no change"


def main() -> None:
    print("=" * 70)
    print("MedLearn AI - Adding telemetry @traced to 6 agents")
    print("=" * 70)
    for path, method, span_name in TARGETS:
        print(patch_file(path, method, span_name))
    print("=" * 70)
    print("Done. Review with:  git diff medlearn/")
    print("=" * 70)


if __name__ == "__main__":
    main()
