# SOP 00 — Navigation Flow (master)

**Layer:** N · Navigation. **Owner of:** ordering, branching, boundary-object hand-off.
**Golden Rule:** change this SOP before changing the orchestrator code.

Navigation does **no** heavy lifting. It validates input, then calls the Tools in §3 of
`LLM.md` in order, passing the boundary objects, and handles the branches below. Every
intermediate file goes in `.tmp/`; the only `out/` writes are the final artifacts.

## Inputs / outputs

- **Input:** `AgentInput` (`schemas/agent_input.schema.json`).
- **Config:** `.env` (`JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`, `JIRA_AC_FIELD_ID?`, `GROQ_API_KEY`, `MODEL`, `MODEL_SMALL`, `DATA_POLICY`, `MODEL_INPUT_LIMIT?`, `SEED?`).
- **Output:** `AgentOutput` (`schemas/agent_output.schema.json`) + files under `out/`.

## Steps

| # | Call | On success | On failure |
|---|------|-----------|-----------|
| 1 | validate `issue_key` against the regex | continue | raise `ValueError`, exit 2, no network |
| 2 | `discover_fields.py` (skip if `ac_field_id` supplied or `JIRA_AC_FIELD_ID` set) | store `ac_field_id` (may be `null`) | log warning, continue with `ac_field_id=null` (ACs will be read from description) |
| 3 | `fetch_jira.py` (honours `refresh`) | `RawBundle` → `.tmp/raw/<KEY>.json`, copy to `out/raw/<KEY>.json` | 401/403 → `status=fetch_failed`; 404 → `status=fetch_failed` ("not found or not visible"); 429/5xx → retry per SOP 01, then `fetch_failed`. Write stub `.md`, return. |
| 4 | `normalize_issue.py` | `.tmp/context/<KEY>.pre.json` | raise; `status=fetch_failed` with stage `normalize_issue` |
| 5 | `redact.py` | `IssueContext` → `.tmp/context/<KEY>.json` | raise; abort (never send unredacted text onward) |
| 6 | `budget.py` | `IssueContext` (possibly with summarised linked issues) | if still over the hard limit after summarising, trim linked issues entirely and note it in `references` |
| 7 | `generate_test_plan.py` (**the one LLM call**, Groq) | `PlanModel` → `.tmp/plan/<KEY>.json` | `response_format` 4xx / non-JSON / ignored schema → the tool's own one json_object retry; still bad → go to 8 with a synthetic error; Groq 429 → honour `retry-after`, backoff ×4, then `fetch_failed`-style abort with a clear message |
| 8 | `validate_plan.py` | `ok` → step 10 | `not ok` → step 9 |
| 9 | `repair_plan.py` **once** (pass the exact error list) → re-run `validate_plan.py` | `ok` → step 10 | still `not ok` → drop offending scenarios, append their intent to `human_review_gate.open_questions`, set `status=validation_failed`, continue to 10 |
| 10 | `render_plan.py` | `out/test-plan-<KEY>.md` + `out/test-plan-<KEY>.json`; stamp `generated_at` | raise; surface as error, keep the JSON |
| 11 | build `AgentOutput`, print summary | return | — |

## Branch: no acceptance criteria (`acceptance_criteria.source == "none"`)

Do **not** abort. `generate_test_plan` still runs; its prompt forces a P0 `GapItem`
("No acceptance criteria in ticket") and every scenario it produces must have
`basis="assumption"`. `status` stays `ok` (the plan is a valid DRAFT), summary reports
`ac_source="none"`.

## Invariants Navigation must uphold

- Never call a Jira write verb. Never pass the token to any tool except `fetch_jira` / `discover_fields`.
- Never call the model more than twice (step 7 + optional step 9); step 7's internal json_object retry does not count as a second logical call.
- Never write outside `.tmp/` except steps 3 (audit copy) and 10.
- Never edit `PlanModel` content itself — only drop whole invalid scenarios in step 9.
- Log lines must never contain `JIRA_API_TOKEN` or `GROQ_API_KEY`.
