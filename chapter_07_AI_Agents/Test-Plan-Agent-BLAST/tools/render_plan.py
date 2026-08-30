"""PlanModel -> Markdown, matching Chapter_02/stlc/01-test-planning/references/test-plan-template.md
(used as-is, Q5). Adds NOTHING beyond PlanModel + render-time stamps. SOP: architecture/10-tools.md."""
from __future__ import annotations

from datetime import datetime, timezone

_FINDING_MARK = {"Missing": "\u274c Missing", "Ambiguous": "\u26a0\ufe0f Ambiguous",
                 "Clear": "\u2705 Clear", "Not Applicable": "\u2014 N/A"}


def _cell(text: str) -> str:
    return str(text or "").replace("|", "\\|").replace("\n", "<br>").strip()


def _bullets(items: list[str], indent: str = "  ") -> str:
    return "\n".join(f"{indent}- {i}" for i in items) if items else f"{indent}- _None stated._"


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def render_markdown(plan: dict, *, issue_context: dict | None = None, generated_at: str | None = None) -> str:
    m = plan["meta"]
    key = m["key"]
    summary = (issue_context or {}).get("summary", "")
    url = (issue_context or {}).get("url")
    src_fetched = (issue_context or {}).get("fetched_at", "unknown")
    gen = generated_at or _now_iso()

    L: list[str] = []
    L.append(f"# Test Plan \u2014 {key}: {summary}".rstrip())
    L.append("")
    L.append("**Status:** DRAFT \u2014 pending human review. Not approved until a QA owner signs off.")
    L.append("")
    L.append(f"_Generated {gen} by the Test Plan Agent (model: {m.get('model', '?')}). "
             f"Source issue fetched {src_fetched}." + (f" {url}_" if url else "_"))
    L.append("")

    s = plan["scope"]
    L.append("## 1. Scope & Objectives")
    L.append("")
    L.append("- **In scope:**")
    L.append(_bullets(s["in_scope"], "  "))
    L.append("- **Out of scope:**")
    L.append(_bullets(s["out_of_scope"], "  "))
    L.append(f"- **Objective:** {s['objective']}")
    L.append("")

    L.append("## 2. Gaps & Questions for the Author")
    L.append("")
    L.append("| # | Area | Finding (\u26a0\ufe0f/\u274c) | Question to Author |")
    L.append("|---|------|-----------------|--------------------|")
    for g in plan["gaps"]:
        mark = _FINDING_MARK.get(g["classification"], g["classification"])
        finding = f"{mark} \u2014 {g['evidence']} _(ref: {g['evidence_ref']})_"
        L.append(f"| {_cell(g['id'])} | {_cell(g['area'])} | {_cell(finding)} | "
                 f"{_cell(g['question_for_author'])} |")
    L.append("")

    L.append("## 3. Test Scenarios")
    L.append("")
    L.append("| ID | Priority | Type (Positive/Negative/Boundary) | Scenario | Maps to (AC/Gap) |")
    L.append("|----|----------|-----------------------------------|----------|------------------|")
    for sc in plan["scenarios"]:
        scen = sc["scenario"]
        if sc.get("preconditions"):
            scen += f" _(pre: {sc['preconditions']})_"
        if sc["basis"] == "assumption":
            scen += " _[assumption]_"
        L.append(f"| {_cell(sc['id'])} | {_cell(sc['priority'])} | {_cell(sc['type'])} | "
                 f"{_cell(scen)} | {_cell(sc['maps_to'])} |")
    L.append("")

    tde = plan["test_data_env"]
    L.append("## 4. Test Data & Environment")
    L.append("")
    L.append(f"- **Test Data:** {tde['test_data']}")
    L.append(f"- **Environment / Feature Flags:** {tde['environment']}")
    L.append(f"- **Roles / Permissions:** {tde['roles']}")
    L.append("")

    ra = plan["risks_assumptions"]
    L.append("## 5. Risks & Assumptions")
    L.append("")
    L.append("- **Assumptions Made:**")
    L.append(_bullets(ra["assumptions"], "  "))
    L.append("- **Risks:**")
    L.append(_bullets(ra["risks"], "  "))
    L.append("")

    ee = plan["entry_exit"]
    L.append("## 6. Entry / Exit Criteria")
    L.append("")
    L.append("- **Entry Criteria:**")
    L.append(_bullets(ee["entry"], "  "))
    L.append("- **Exit Criteria:**")
    L.append(_bullets(ee["exit"], "  "))
    L.append("")

    hrg = plan["human_review_gate"]
    L.append("## 7. HUMAN REVIEW GATE")
    L.append("")
    L.append("- **I assumed:**")
    L.append(_bullets(hrg["assumed"], "  "))
    L.append("- **I could not confirm:**")
    L.append(_bullets(hrg["could_not_confirm"], "  "))
    L.append("- **Open questions blocking sign-off:**")
    L.append(_bullets(hrg["open_questions"], "  "))
    L.append("- **QA Review:** Approve or edit this draft before test cases or automation are created.")
    L.append("")

    if plan["references"]:
        L.append("## References")
        L.append("")
        for r in plan["references"]:
            L.append(f"- [{r['title'] or r['url']}]({r['url']})")
        L.append("")

    return "\n".join(L)
