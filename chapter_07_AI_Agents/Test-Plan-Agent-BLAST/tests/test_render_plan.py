from tools.render_plan import render_markdown

CANON_HEADINGS = [
    "## 1. Scope & Objectives",
    "## 2. Gaps & Questions for the Author",
    "## 3. Test Scenarios",
    "## 4. Test Data & Environment",
    "## 5. Risks & Assumptions",
    "## 6. Entry / Exit Criteria",
    "## 7. HUMAN REVIEW GATE",
]


def test_matches_repo_template_structure(plan_model_valid, issue_context_min):
    md = render_markdown(plan_model_valid, issue_context=issue_context_min,
                         generated_at="2026-08-29T12:00:00+00:00")
    for h in CANON_HEADINGS:
        assert h in md
    assert md.startswith("# Test Plan — DEMO-1:")
    assert "**Status:** DRAFT" in md


def test_every_scenario_and_gap_row_present(plan_model_valid, issue_context_min):
    md = render_markdown(plan_model_valid, issue_context=issue_context_min)
    for s in plan_model_valid["scenarios"]:
        assert f"| {s['id']} |" in md
    for g in plan_model_valid["gaps"]:
        assert f"| {g['id']} |" in md


def test_adds_no_content_beyond_plan(plan_model_valid, issue_context_min):
    md = render_markdown(plan_model_valid, issue_context=issue_context_min)
    # assumption scenarios are tagged, review gate present, nothing invented
    assert "_[assumption]_" in md
    assert "Approve or edit this draft" in md


def test_pipes_in_text_are_escaped(plan_model_valid, issue_context_min):
    p = {**plan_model_valid}
    p["scenarios"] = [dict(plan_model_valid["scenarios"][0],
                           scenario="value a | value b in one cell")]
    md = render_markdown(p, issue_context=issue_context_min)
    assert "value a \\| value b" in md


def test_renders_real_gpt_oss_output():
    """A genuine gpt-oss-120b PlanModel for KAN-6 (Groq, 2026-08-30) renders cleanly."""
    import json
    from pathlib import Path
    f = Path(__file__).parent / "fixtures" / "plan_model_kan6_real.json"
    if not f.exists():
        return
    plan = json.loads(f.read_text(encoding="utf-8"))
    md = render_markdown(plan, generated_at="2026-08-30T12:00:00+00:00")
    for h in CANON_HEADINGS:
        assert h in md
    assert md.count("| G-") == len(plan["gaps"])
    assert md.count("| TS-") == len(plan["scenarios"])
