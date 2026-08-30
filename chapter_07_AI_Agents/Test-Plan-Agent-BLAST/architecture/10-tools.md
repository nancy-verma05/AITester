# SOP 10 — Tools (`tools/*.py`)

**Layer:** T · Tools. Each is atomic, deterministic (except the LLM tools —
`generate_test_plan`, `repair_plan`, and `budget`'s summariser — which are deterministic
*wrappers*: fixed model, `temperature:0`, fixed `seed`, structured output), independently
runnable, unit-tested with fixtures. Secrets from `.env`. Intermediates in `.tmp/`. Tools
never call each other — Navigation (SOP 00) does.

**LLM provider:** Groq (OpenAI-compatible). Shared client `tools/_groq.py`; shared Jira
client `tools/_jira.py`; shared config `tools/_config.py`. See `LLM.md` §6–§7.

**Golden Rule:** update the relevant section here before editing the script.

Phase 1 status: these are **specs**, not code. Code lands in Phase 3 (A · Architect).

---

## `discover_fields.py`

- **Goal:** resolve the Acceptance Criteria custom field id for the site.
- **In:** `.env`. **Out:** `{ "ac_field_id": "customfield_10068" | null }` (also cached to `.tmp/config/fields.json`).
- **Logic:** `GET /rest/api/3/field`; match `name` case-insensitively against
  `["acceptance criteria", "acceptance criteria (ac)", "ac", "definition of done"]`;
  return the first custom field match, else `null`.
- **Edge cases:** multiple matches → pick the one literally named "Acceptance Criteria",
  log the rest. 401/403 → raise. Network error → raise (Navigation degrades to `null`).
- **Never:** call anything but `GET /rest/api/3/field` and `GET /myself`.

## `fetch_jira.py`

- **Goal:** pull the raw issue bundle, read-only.
- **In:** `issue_key`, `refresh`, `ac_field_id`. **Out:** `RawBundle` → `.tmp/raw/<KEY>.json`.
- **Logic:** if `.tmp/raw/<KEY>.json` exists, is < 24 h old, and `refresh` is false → return it.
  Else 4 GETs (see `findings.md` §3): E1 issue (`fields=` mapped list + `ac_field_id`,
  `expand=renderedFields,names,changelog`), E3 comments (`expand=renderedBody`),
  E4 remotelinks, E5 `POST /rest/api/3/search/jql` for linked issues.
- **Auth:** HTTP Basic, `JIRA_EMAIL:JIRA_API_TOKEN`.
- **Retry:** 429 → honour `Retry-After`; 5xx → exp backoff, max 4 tries. 401/403/404 → no retry, raise typed error.
- **Never:** any verb but `GET` (and the one read-only `POST .../search/jql`). Never log the token. Never follow attachment/remote URLs.

## `normalize_issue.py`

- **Goal:** turn `RawBundle` into a clean, structured pre-context.
- **In:** `RawBundle`. **Out:** `.tmp/context/<KEY>.pre.json` (shape = `IssueContext` minus `redactions`/`token_estimate`).
- **Logic:**
  - Rich text: take `renderedFields.<f>` HTML → Markdown (`markdownify`). Fallback to
    `atlas-doc-parser` on the raw ADF when HTML is empty/malformed.
  - **AC resolution (Q3 order):** if `ac_field_id` present and its value non-empty → `source="custom_field"`.
    Else find an "Acceptance Criteria" / "Definition of Done" / "AC" **label line** in the
    description — a heading (`## Acceptance Criteria`), a bold list label
    (`- **Acceptance Criteria:**`, the common Jira story-template shape — see the KAN-6
    real-data test), or plain text — then take the list block that follows it, up to the
    next bold label or heading → `source="description"`.
    Else `source="none"`, `items_md=[]`.
  - Split ACs into `AC-1..n` on list items / numbered lines; otherwise one blob = `AC-1`.
  - **Known limitation:** inline ACs on the same line as the label (`Acceptance Criteria: foo. bar.`)
    are captured as a single blob, not split. Revisit in Phase 4 if the eval corpus needs it.
  - `changelog_signal`: count changes to the AC field and to `status` from `expand=changelog`.
  - Keep only the fields in the `findings.md` §8 mapping table. Drop everything else (Q9 minimisation).
- **Edge cases:** ADF tables/panels → keep as Markdown tables/blockquotes; log if a node type is unhandled.
- **Never:** call Jira or the model. Never paraphrase ticket text (copy verbatim into `*_md` fields).

## `redact.py`

- **Goal:** remove secrets/PII before anything reaches the model (rule B9, Q9).
- **In:** `*.pre.json` + `DATA_POLICY`. **Out:** `IssueContext` → `.tmp/context/<KEY>.json`.
- **Logic:** regex-replace in every `*_md` / text field:
  - API tokens / bearer strings / `Authorization:` headers / AWS-style keys / long hex/base64 blobs → `«redacted:token»`
  - emails → `«redacted:email»` (keep comment `author` display names — those are not PII removal targets, but drop emails inside bodies)
  - `https://user:pass@…` → strip credentials
  - `DATA_POLICY=redacted` additionally: names in "assigned to <X>" style phrases, phone numbers
  - `DATA_POLICY=zdr`: also require the model call to use a zero-retention endpoint/flag (config gate; fail loudly if not available)
  - Record every removal in `redactions[]` as `{kind, count}`.
- **Edge cases:** a redaction that would empty an AC → keep a placeholder token and add a note; never silently drop an AC.
- **Never:** write the original unredacted text anywhere except `.tmp/` (which is git-ignored and short-lived).

## `budget.py`

- **Goal:** keep the model input under a safe size without losing the target issue.
- **In:** `IssueContext`. **Out:** same, or with `links[].summary` / linked bodies summarised.
- **Logic:** estimate tokens (`len(serialised)/4` heuristic, or `tiktoken` if available) on the
  serialised `IssueContext`. If over the limit (config `MODEL_INPUT_LIMIT`, default ~40k):
  summarise **linked-issue** text only via Groq `MODEL_SMALL` (`openai/gpt-oss-20b`,
  `reasoning_effort:"low"`, `temperature:0`). Never summarise `description_md` or
  `acceptance_criteria`. Still over → drop linked issues, add "linked issues omitted for
  size" to `references`.
- **Never:** touch the target issue's description or ACs.

## `generate_test_plan.py`  ★ the one LLM call — Groq ★

- **Goal:** gap analysis + plan, in one structured response.
- **In:** `IssueContext`. **Out:** `PlanModel` → `.tmp/plan/<KEY>.json`.
- **Call:** `groq.chat.completions.create` via `tools/_groq.py`:
  - `model = MODEL` (default `openai/gpt-oss-120b`)
  - `messages = [ {"role":"system", "content": system.md + "\n\n" + plan_model.groq.schema.json},
                  {"role":"user", "content": generate_test_plan.md},
                  {"role":"user", "content": "<untrusted_ticket_content>\n" + json(IssueContext, sort_keys=True) + "\n</untrusted_ticket_content>"} ]`
    — stable content first so Groq's automatic prompt cache hits; `IssueContext` last.
  - `response_format = {"type":"json_schema","json_schema":{"name":"plan_model","strict":true,"schema": <plan_model.groq.schema.json>}}`
  - `reasoning_effort="high"`, `include_reasoning=False`, `temperature=0`, `top_p=1`,
    `seed=SEED` (fixed), `max_completion_tokens=32000`.
- **Fallback:** on 4xx about `response_format`, or if the returned content isn't valid JSON,
  or `json_schema` looks ignored → retry **once** with `response_format={"type":"json_object"}`
  and the schema appended to the system message. This retry is not the repair call.
- **Post:** `json.loads` the content; return the dict + `usage` to Navigation. Do **not**
  validate here — that's `validate_plan.py`.
- **Never:** more than one logical call (+ the one format-fallback retry). Never include
  secrets (already redacted). Never put `generated_at` in the prompt. Never read
  `message.reasoning`.

## `validate_plan.py`

- **Goal:** deterministic enforcement of B1–B6 (schema is necessary, not sufficient).
- **In:** `PlanModel` + `IssueContext`. **Out:** `{ ok: bool, errors: [{code, detail}] }`.
- **Checks:**
  1. JSON-Schema valid against `plan_model.schema.json`.
  2. `meta.status == "DRAFT"`.
  3. Every `scenarios[].maps_to` resolves to an existing `AC-<n>` (count from `IssueContext.acceptance_criteria.items_md`) or an existing `gaps[].id`.
  4. Traceability (**hard fail** — open-weight model, see `LLM.md` §7): for each
     `basis=="confirmed"` scenario and each `test_data_env` value that isn't the literal
     "Not specified…" placeholder, its content words (stopwords removed) overlap the
     `IssueContext` text (`summary` + `description_md` + `items_md` + comment bodies) at
     ratio ≥ 0.5 — otherwise "possibly fabricated". `basis=="assumption"` scenarios are
     exempt here (they are checked by rule 5 instead). Loose by design: catches invented
     systems/entities, not numeric drift — that is the HUMAN REVIEW GATE's job.
  5. Every `scenarios[].basis == "assumption"` has a matching line in `human_review_gate.assumed`.
  6. Every `gaps[]` with classification `Missing`/`Ambiguous` has non-empty `question_for_author`
     and `evidence` that is a real quote or starts `ABSENT: `.
  7. If `acceptance_criteria.source == "none"`: there is a P0 gap in area covering "no acceptance criteria",
     and no scenario has `basis == "confirmed"`.
  8. Each AC id referenced by ≥1 `Positive` **and** ≥1 `Negative`/`Boundary` scenario (adopted from prior-art guardrail — `findings.md` §10). Soft check → warning, not a hard fail, unless the AC is P0.
- **Out on failure:** a precise, machine-usable error list for `repair_plan.py`.

## `repair_plan.py`  (LLM call #2 — Groq — only when step 8 fails)

- **Goal:** fix exactly the listed validator errors, nothing else.
- **In:** failing `PlanModel` + `errors[]`. **Out:** `PlanModel'`.
- **Call:** same system message (prompt + schema — cache hit) + `prompts/repair.md` + the
  failing JSON + the error list; `model=MODEL`, `reasoning_effort="medium"`, `temperature=0`,
  same `response_format`.
- **Never:** a third call. If it still fails validation, Navigation drops the bad scenarios.

## `render_plan.py`

- **Goal:** map `PlanModel` → the repo template, byte-for-byte structure.
- **In:** `PlanModel`. **Out:** `out/test-plan-<KEY>.md` + `out/test-plan-<KEY>.json`.
- **Template:** `Chapter_02/stlc/01-test-planning/references/test-plan-template.md`, used as-is.
  Section mapping: `scope`→§1; `gaps`→§2 table (`#`,`Area`,`Finding` = `⚠️` Ambiguous / `❌` Missing + evidence, `Question to Author`); `scenarios`→§3 table; `test_data_env`→§4; `risks_assumptions`→§5; `entry_exit`→§6; `human_review_gate`→§7; `references` appended under §7 or a "References" block.
- **Stamp:** replace `<RALLY-KEY>`→`<KEY>`, `[TITLE]`→summary; add `generated_at`, `source_fetched_at`, `model` in a small italic line under the DRAFT banner.
- **Never:** add, reword, or infer content beyond what's in `PlanModel`. Never drop the DRAFT banner or §7.
