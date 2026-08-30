import copy

from tools.validate_plan import validate


def test_valid_fixture_passes(plan_model_valid, issue_context_min):
    r = validate(plan_model_valid, issue_context_min)
    assert r["ok"], r["errors"]


def test_dangling_maps_to_is_rejected(plan_model_valid, issue_context_min):
    p = copy.deepcopy(plan_model_valid)
    p["scenarios"][0]["maps_to"] = "AC-99"
    r = validate(p, issue_context_min)
    assert not r["ok"]
    assert any(e["code"] == "maps_to" for e in r["errors"])


def test_fabricated_confirmed_scenario_is_rejected(plan_model_valid, issue_context_min):
    p = copy.deepcopy(plan_model_valid)
    p["scenarios"].append({
        "id": "TS-9", "priority": "P1", "type": "Positive",
        "scenario": "The reset flow also provisions a Salesforce CRM account and posts to Slack",
        "preconditions": None, "maps_to": "AC-1", "basis": "confirmed", "notes": None,
    })
    r = validate(p, issue_context_min)
    assert not r["ok"]
    assert any(e["code"] == "traceability" for e in r["errors"])


def test_assumption_scenarios_with_empty_gate_is_rejected(plan_model_valid, issue_context_min):
    p = copy.deepcopy(plan_model_valid)
    p["human_review_gate"]["assumed"] = []
    p["human_review_gate"]["could_not_confirm"] = []
    p["risks_assumptions"]["assumptions"] = []
    r = validate(p, issue_context_min)
    assert not r["ok"]
    assert any(e["code"] == "assumption_gate" for e in r["errors"])


def test_unmirrored_single_assumption_is_rejected(plan_model_valid, issue_context_min):
    p = copy.deepcopy(plan_model_valid)
    p["scenarios"].append({
        "id": "TS-8", "priority": "P2", "type": "Negative",
        "scenario": "The mobile push notification is throttled after five sends per hour",
        "preconditions": None, "maps_to": "AC-1", "basis": "assumption", "notes": None,
    })
    r = validate(p, issue_context_min)
    assert not r["ok"]
    assert any(e["code"] == "assumption_gate" and "TS-8" in e["detail"] for e in r["errors"])


def test_no_ac_branch_requires_p0_gap(issue_context_min, plan_model_valid):
    ctx = copy.deepcopy(issue_context_min)
    ctx["acceptance_criteria"] = {"source": "none", "field_id": None, "items_md": []}
    p = copy.deepcopy(plan_model_valid)
    # remap everything to gaps so no dangling AC ids, all assumption
    for s in p["scenarios"]:
        s["basis"] = "assumption"
        s["maps_to"] = "G-1"
    r = validate(p, ctx)
    assert not r["ok"]
    assert any(e["code"] == "no_ac_gap" for e in r["errors"])


def test_gap_without_evidence_is_rejected(plan_model_valid, issue_context_min):
    p = copy.deepcopy(plan_model_valid)
    p["gaps"][0]["evidence"] = "the system should probably do more here"
    r = validate(p, issue_context_min)
    assert not r["ok"]
    assert any(e["code"] == "gap_evidence" for e in r["errors"])
