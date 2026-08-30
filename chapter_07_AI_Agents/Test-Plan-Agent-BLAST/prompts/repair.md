# User prompt — repair_plan (LLM call #2, only on validation failure)

> Draft v0.1 (Phase 1). Sent after the cached system prefix. Followed by the failing
> `PlanModel` JSON and the validator error list.

The `PlanModel` below failed deterministic validation. Fix **only** the listed errors and
return the corrected `PlanModel` JSON. Change nothing else — keep every valid scenario,
gap, and wording exactly as is.

Rules for the fix:

- Do not invent content to satisfy a check. If a scenario's `maps_to` is dangling and no
  correct `AC-<n>` / `G-<n>` exists, either repoint it to the right existing id or **delete
  that scenario** and add its intent to `human_review_gate.open_questions`.
- If a value was flagged "possibly fabricated", replace it with
  `"Not specified in ticket — see G-<n>"` and ensure a matching gap exists.
- If `human_review_gate.assumed` is missing an assumption-basis scenario, add the line.
- Keep `meta.status` = `"DRAFT"`.
- Return **only** the JSON.

Errors:
