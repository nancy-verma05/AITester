"""Deterministic enforcement of B1-B6 (schema is necessary, not sufficient). 8 checks.
SOP: architecture/10-tools.md. Returns {ok, errors[], warnings[]}."""
from __future__ import annotations

from jsonschema import Draft202012Validator

from tools._util import fuzzy_contains, load_schema

_PLACEHOLDER = "Not specified in ticket"


def _ac_ids(ctx: dict) -> set[str]:
    n = len(ctx.get("acceptance_criteria", {}).get("items_md", []))
    return {f"AC-{i}" for i in range(1, n + 1)}


def _haystack(ctx: dict) -> str:
    parts = [ctx.get("summary", ""), ctx.get("description_md", "")]
    parts += ctx.get("acceptance_criteria", {}).get("items_md", [])
    parts += [c.get("body_md", "") for c in ctx.get("comments", [])]
    return "\n".join(p for p in parts if p)


def validate(plan: dict, issue_context: dict) -> dict:
    errors: list[dict] = []
    warnings: list[dict] = []

    def err(code, detail):
        errors.append({"code": code, "detail": detail})

    # 1 — JSON Schema (authoritative full schema)
    schema = load_schema("plan_model.schema.json")
    schema_errs = sorted(Draft202012Validator(schema).iter_errors(plan),
                         key=lambda e: str(list(e.path)))
    for e in schema_errs:
        err("schema", f"{'/'.join(map(str, e.path)) or '<root>'}: {e.message}")
    if schema_errs:
        return {"ok": False, "errors": errors, "warnings": warnings}  # rest would KeyError

    hay = _haystack(issue_context)
    ac_ids = _ac_ids(issue_context)
    gap_ids = {g["id"] for g in plan["gaps"]}

    # 2 — DRAFT marker
    if plan["meta"]["status"] != "DRAFT":
        err("draft", "meta.status must be 'DRAFT'")

    # 3 — every maps_to resolves
    for s in plan["scenarios"]:
        if s["maps_to"] not in (ac_ids | gap_ids):
            err("maps_to", f"{s['id']}: maps_to {s['maps_to']!r} is not a known AC id "
                           f"({sorted(ac_ids) or 'none'}) or gap id")

    # 4 — traceability (HARD fail on Groq / open-weight; see LLM.md section 7)
    for s in plan["scenarios"]:
        if s["basis"] == "confirmed" and not fuzzy_contains(s["scenario"], hay):
            err("traceability", f"{s['id']}: basis=confirmed but text not traceable to the "
                                f"ticket: {s['scenario'][:90]!r}")
    for k, v in plan["test_data_env"].items():
        if v and _PLACEHOLDER not in v and not fuzzy_contains(v, hay):
            err("traceability", f"test_data_env.{k}: not traceable and not marked "
                                f"'{_PLACEHOLDER} - see G-N': {v[:90]!r}")

    # 5 — assumption scenarios must be surfaced for the human (assumed / could-not-confirm /
    #     risks.assumptions all count). Hard fail only if the gate is empty of assumptions.
    hrg = plan["human_review_gate"]
    assumed_pool = " ".join(
        hrg["assumed"] + hrg["could_not_confirm"] + plan["risks_assumptions"]["assumptions"]
    ).lower()
    assumption_scenarios = [s for s in plan["scenarios"] if s["basis"] == "assumption"]
    if assumption_scenarios and not (hrg["assumed"] or plan["risks_assumptions"]["assumptions"]):
        err("assumption_gate", "there are basis=assumption scenarios but "
                               "human_review_gate.assumed and risks_assumptions.assumptions are both empty")
    for s in assumption_scenarios:
        if not fuzzy_contains(s["scenario"], assumed_pool, threshold=0.3):
            err("assumption_gate", f"{s['id']}: basis=assumption but not reflected anywhere in "
                                   f"the review gate / assumptions")

    # 6 — gap evidence discipline
    for g in plan["gaps"]:
        if g["classification"] in ("Missing", "Ambiguous"):
            if not g["question_for_author"].strip():
                err("gap_question", f"{g['id']}: {g['classification']} with empty question_for_author")
            ev = g["evidence"].strip()
            if not (ev.startswith("ABSENT:") or fuzzy_contains(ev, hay)):
                err("gap_evidence", f"{g['id']}: evidence is neither an 'ABSENT: ...' note "
                                    f"nor a traceable quote")

    # 7 — no-acceptance-criteria branch
    if issue_context.get("acceptance_criteria", {}).get("source") == "none":
        has_p0_ac_gap = any(
            g["severity"] == "P0"
            and "acceptance" in (g["evidence"] + " " + g["question_for_author"]).lower()
            for g in plan["gaps"]
        )
        if not has_p0_ac_gap:
            err("no_ac_gap", "acceptance_criteria.source == 'none' but no P0 gap flags the "
                             "missing acceptance criteria")
        if any(s["basis"] == "confirmed" for s in plan["scenarios"]):
            err("no_ac_confirmed", "acceptance_criteria.source == 'none' but a scenario "
                                   "claims basis=confirmed")

    # 8 — each referenced AC gets a positive AND a negative/boundary (soft)
    for ac in ac_ids:
        types = {s["type"] for s in plan["scenarios"] if s["maps_to"] == ac}
        if types and not ("Positive" in types and types & {"Negative", "Boundary"}):
            warnings.append({"code": "coverage", "detail": f"{ac}: has scenarios {sorted(types)} "
                                                           f"- expected >=1 Positive and >=1 Negative/Boundary"})

    return {"ok": not errors, "errors": errors, "warnings": warnings}
