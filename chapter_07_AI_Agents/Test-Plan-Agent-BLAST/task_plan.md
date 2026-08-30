# Task Plan — Test Plan Agent (B.L.A.S.T.)

> Project memory file required by **Protocol 0: Initialization**.
> Companion files: `findings.md`, `progress.md`, `LLM.md` (Project Constitution).
> Status: **Protocol 0 ✅ · Phase 1 (Blueprint) ✅ approved 2026-08-29 · Phase 3 (Architect)
> in progress.** LLM provider = **Groq** (user override). Phase 2 (Link) needs Jira +
> `GROQ_API_KEY` credentials + a Python runtime.

---

## 1. Mission

Given a **Jira issue ID** (e.g. `PROJ-1234`), produce a **review-ready DRAFT test plan**
for that story: scope, gap analysis, test scenarios (prioritised, traceable), test data &
environment, risks & assumptions, entry/exit criteria, and a HUMAN REVIEW GATE.

The agent **reads** Jira, **reasons** about coverage, and **writes a Markdown artifact**.
It never writes back to Jira and never invents requirements.

## 2. In scope / Out of scope

**In scope**
- Accept a single Jira issue key as input (later: a list, or a JQL query).
- Fetch the issue + acceptance criteria + comments + linked issues + remote links.
- Normalise Atlassian Document Format (ADF) / rendered HTML to plain Markdown.
- Gap analysis classifying each coverage area: Clear / Ambiguous / Missing / N-A.
- Emit `test-plan-<KEY>.md` following the template in
  `Chapter_02/stlc/01-test-planning/references/test-plan-template.md` (adapted Rally → Jira).
- Persist the raw Jira payload alongside the plan for audit.

**Out of scope (for now)**
- Generating executable test cases or automation code (that is a later, separate step).
- Writing to Jira (transitions, comments, labels).
- Test management tool integration (Xray, Zephyr, TestRail).
- Multi-issue epics rollups (Protocol 4 stretch goal).

## 3. Success criteria

| # | Criterion | How we measure it |
|---|-----------|-------------------|
| S1 | Correct fetch | For 5 real issue keys, every field in the mapping table (`findings.md` §8) is retrieved or explicitly marked "not present". |
| S2 | No fabrication | In an eval of 10 issues, 0 acceptance criteria / expected results appear in the plan that are not traceable to the source. |
| S3 | Gap detection | On 3 deliberately under-specified issues, the agent flags the seeded gaps (negative paths, boundaries, test data) as Missing/Ambiguous. |
| S4 | Traceability | Every row in the Test Scenarios table has a non-empty "Maps to (AC/Gap)" cell. |
| S5 | Determinism | Same issue + same Jira state → structurally equivalent plan (same scenario count ±1, same gap list) across 3 runs. |
| S6 | Safety | Static check confirms no Jira write endpoints are called; no token is logged or committed. |
| S7 | Human gate | Output is marked DRAFT and ends with the HUMAN REVIEW GATE section populated. |

## 4. Definition of Done for the plan artifact

- File named `test-plan-<KEY>.md`, first line marks it **DRAFT**.
- All 7 template sections present; empty subsections say *"Not specified in ticket — finding #N"*, never a guess.
- "Gaps & Questions for the Author" table has ≥1 row or an explicit "no gaps found — confirm with author".
- Scenarios tagged P0/P1/P2 and mapped to an AC or gap.
- Assumptions and open questions listed in the HUMAN REVIEW GATE.

---

## 5. B.L.A.S.T. milestone checklists

> Phases and their content are taken from `BLAST.md` (Protocol 0 + Phases B/L/A/S/T).
> "Protocol 1" in conversation = **Phase 1 (B — Blueprint)**.

### Protocol 0 — Initialization  ✅ COMPLETE (2026-08-29)
- [x] `task_plan.md`, `findings.md`, `progress.md`, `LLM.md` created.
- [x] Jira auth + endpoints + ADF + custom-field discovery documented with runnable examples → `findings.md`.
- [x] Data schemas + guardrail rules + architectural invariants drafted → `LLM.md`.
- [x] Discovery Questions answered (§7).
- [x] Data Schema present in `LLM.md`; halt conditions tracked.

### Phase 1 — B · Blueprint (Vision & Logic)  ✅ approved 2026-08-29
- [x] **Discovery** — BLAST's 5 questions mapped + answered (§10.1).
- [x] **Research** — similar projects + ADF libs + Jira client + 3-layer refs → `findings.md` §10; **Groq** → §11.
- [x] Correct A.N.T. to the canonical `BLAST.md` definition (Architecture / Navigation / Tools) → `LLM.md` §1.
- [x] **Data-First** — Input / Config / Output payload shapes defined → `LLM.md` §2.0.
- [x] Freeze the JSON schemas (+ `plan_model.groq.schema.json` added for Groq strict mode).
- [x] Write `architecture/00-navigation-flow.md` + `architecture/10-tools.md`.
- [x] Draft `prompts/`.
- [x] **Blueprint sign-off** (§10.4). ✅

### Phase 2 — L · Link (Connectivity)   *(connectivity ✅ manual; Python still needed)*
- [x] `.env.example` + `tools/link_check.py` written.
- [x] `.env` populated with real Jira + Groq creds (git-ignored). — user, 2026-08-30
- [x] **Connectivity verified manually** (curl/node, no Python): Jira auth ✅, no AC custom field (→ description path), `/search/jql` bounded-only, Groq `gpt-oss-120b` + strict `json_schema` ✅. → `findings.md` §12.
- [ ] Re-run `python -m tools.link_check KAN-6` once Python is installed (should confirm the manual result + exercise the real code path).

### Phase 3 — A · Architect (the 3-Layer build)   *(code written; e2e-proven via Node; pytest pending)*
- [x] **Architecture** SOPs finalised (`architecture/`), updated for Groq. Golden Rule held.
- [x] **Tools** (`tools/`): `_config`, `_util`, `_jira` (GET-only), `_groq` (strict→json_object, rate-limit retry), `discover_fields`, `fetch_jira`, `normalize_issue`, `redact`, `budget`, `generate_test_plan`, `validate_plan` (8 checks), `repair_plan`, `render_plan`.
- [x] **Navigation** (`navigation/orchestrator.py`) — SOP 00 with every branch.
- [x] CLI: `python cli.py <ISSUE-KEY> [--refresh] [--json]`.
- [x] `tests/` — normalize (+ real KAN-6) / redact / validate_plan / render (+ real KAN-6) / schema_sync + 5 fixtures.
- [x] **End-to-end proven on a real ticket** (KAN-6) via a Node harness: Groq accepts the full strict schema; `validate_plan` PASS; rendered plan reviewed. Groq free-tier 8k-tok/min tuning applied (`findings.md` §12a).
- [ ] **verify:** `pytest -q` on a real Python env (none on this machine) → all green; fix fallout.

### Phase 4 — S · Stylize (Refinement)
- [ ] Payload polish: the rendered `.md` matches the repo template exactly; DRAFT banner + HUMAN REVIEW GATE read well.
- [ ] Run the eval set: 10 real issues + 3 synthetic under-specified ones; record S1–S7 in `progress.md`.
- [ ] Guardrail red-team: prompt-injection in a comment, missing ACs, huge description, ADF tables/panels, non-English.
- [ ] Present sample outputs to the user for feedback before Trigger.

### Phase 5 — T · Trigger (Deployment)
- [ ] `README.md` + runbook (how to run, required scopes, failure recovery, data-policy gate).
- [ ] Decide the trigger: manual CLI for v1; later a Jira webhook / scheduled run.
- [ ] Production data-policy sign-off (ZDR / redaction) if it leaves local use.
- [ ] Final `progress.md` summary + handoff.

---

## 6. Deliverables

| Artifact | Phase | Location |
|----------|-------|----------|
| Project memory (these 4 files) | 0 | `Test-Plan-Agent-BLAST/` |
| `schemas/*.json` (4) | 1 (B) | `Test-Plan-Agent-BLAST/schemas/` |
| `architecture/*.md` SOPs | 1 (B) draft → 3 (A) final | `Test-Plan-Agent-BLAST/architecture/` |
| `prompts/*.md` | 1 (B) | `Test-Plan-Agent-BLAST/prompts/` |
| `.env.example` + credential handshakes | 2 (L) | `Test-Plan-Agent-BLAST/` |
| `tools/*.py` + `navigation/` orchestrator | 3 (A) | `Test-Plan-Agent-BLAST/` |
| Eval set + report | 4 (S) | `Test-Plan-Agent-BLAST/evals/` |
| `README.md` + runbook | 5 (T) | `Test-Plan-Agent-BLAST/README.md` |
| Generated plans (output) | runtime | `Test-Plan-Agent-BLAST/out/` |
| Intermediates | runtime | `Test-Plan-Agent-BLAST/.tmp/` |

---

## 7. Discovery Questions — ANSWERED 2026-08-29

| # | Question | Answer | Consequence for design |
|---|----------|--------|------------------------|
| 1 | Jira deployment | **Jira Cloud** (`*.atlassian.net`) | REST API **v3**, ADF rich text, `api.atlassian.com` gateway or site URL. Drop all DC/v2 branches. |
| 2 | Auth | **Dedicated Jira service account**, Cloud **API token**, **HTTP Basic**. Read-only permissions only. **No write perms.** | Adapter = `GET` only, enforced. Credentials for the service account, not a personal account. Scope: Browse Projects / read issue, comment, field, links. |
| 3 | Acceptance Criteria location | **Primarily the issue description.** Also inspect a configured AC **custom field** if one exists. If none found → **flag as gap, never invent.** | N-layer: parse description for AC first; `JIRA_AC_FIELD_ID` optional config; `acceptance_criteria.source` ∈ {description, custom_field, none}; `none` → P0 GapItem. |
| 4 | Issue types in scope | **Story** initially. Architecture must allow Bug/Task/Sub-task/Spike later. | Protocol 1 targets Story. Keep `issue_type` in `IssueContext` and branch points abstracted. |
| 5 | Test plan template | **Reuse the repo template as-is.** Populate it, don't invent a format. | T-layer renders into `Chapter_02/stlc/01-test-planning/references/test-plan-template.md` verbatim (Rally→Jira label swap only). |
| 6 | Output destination | **Local Markdown file only.** No Jira writes / attachments / comments / external writes. | Output = `out/test-plan-<KEY>.md` + audit files. No write integrations. |
| 7 | LLM provider + budget | ~~Claude~~ → **Groq** (user override 2026-08-29, "Use GROQ.com as LLM"). **No hard per-run cost ceiling** for v1. Must **minimize model calls** and **not resend context**. | `openai/gpt-oss-120b` via the `groq` SDK; **one** structured call (see `LLM.md` §3, §7). Automatic Groq prompt caching of the stable prefix. `gpt-oss-20b` summarisation only when over budget. |
| 8 | Runtime | **Antigravity** per BLAST. A.N.T. must separate **(1) retrieval/context gathering → (2) reasoning/planning → (3) generation/output**, each with an explicit input/output contract and no boundary bypass. | Superseded by the expanded `BLAST.md`: **A.N.T. = Architecture / Navigation / Tools**. The (1)/(2)/(3) split lives *inside* Tools as atomic scripts; Navigation orders them; `architecture/*.md` SOPs are the contract. Full mapping in `LLM.md` §1. |
| 9 | Data sensitivity | Ticket content may contain customer/PII data. **Do not assume unrestricted transmission.** Send **only the minimum required** Jira content to the model. **Never** send secrets/credentials/tokens/unnecessary PII. Zero-retention / redaction must be explicitly configured before production. | N-layer: build a **minimised** `IssueContext` (only mapped fields), redact secrets + obvious PII (emails, keys), record `redactions`. Add a `data_policy` config block; production gate documented in Protocol 4. |

---

## 8. Risks & mitigations

| # | Risk | Impact | Mitigation |
|---|------|--------|------------|
| R1 | Acceptance Criteria field id differs per Jira project | Agent misses the ACs entirely | Field-discovery step (`GET /rest/api/3/field`) + config override; fail loud if not found |
| R2 | ADF with tables / panels / media renders poorly to Markdown | Lost requirements | Prefer `expand=renderedFields` (HTML) + HTML→MD; keep raw ADF in audit file |
| R3 | Model fabricates ACs / expected results | Invalid plan, false confidence | Guardrail rules in `LLM.md`; post-gen traceability validator; eval S2 |
| R4 | Prompt injection via Jira description/comments | Agent ignores rules or leaks token | Treat all ticket text as untrusted data, never instructions; token never in model context |
| R5 | Large epics / long descriptions exceed context | Truncation, silent gaps | Token-count before call; summarise linked issues, never the target issue; chunk if needed |
| R6 | Non-deterministic scenario lists | Fails S5, hard to review | Low temperature via low effort where possible, structured output schema, stable ordering |
| R7 | Jira rate limits (429) | Run fails midway | Backoff + retry in the adapter; cache raw payload per key |
| R8 | Secret leakage | Security incident | `.env` only, `.gitignore`, no token in logs, redact in error messages |

---

## 9. Dependencies

- Jira **Cloud** access: site URL + **service-account** email + API token, read-only perms.
- Groq API access (`GROQ_API_KEY` from console.groq.com).
- A Python 3.11+ runtime (Antigravity host; not present on the dev machine — see `progress.md`).
- Repo template: `Chapter_02/stlc/01-test-planning/references/test-plan-template.md`.
- Antigravity runtime (A.N.T. project layout).
- (Optional) Atlassian Remote MCP Server or `mcp-atlassian` — kept as a config-switchable A-layer backend.

---

## 10. Blueprint — Phase 1 (B)

### 10.1 Discovery — BLAST's 5 questions

| Q | Answer |
|---|--------|
| **North Star** | One command: `test-plan-agent PROJ-1234` → a review-ready **DRAFT** test plan as a local Markdown file (repo template), whose **gap analysis is genuinely useful to a human reviewer**, with **no invented requirements**. |
| **Integrations** | **Jira Cloud REST API v3** — read-only, service-account API token, Basic auth (keys: **not yet provisioned**). **Groq API** (`api.groq.com`, OpenAI-compatible) — `openai/gpt-oss-120b` (`GROQ_API_KEY`: **to be provided**). No Slack / Confluence / test-management tool in v1. |
| **Source of Truth** | The **Jira issue**: description (primary AC location) + optional AC custom field + comments + linked issues + remote-link titles. The **repo test-plan template** is the source of truth for output format. |
| **Delivery Payload** | Local files only (Q6): `out/test-plan-<KEY>.md` (template, DRAFT, HUMAN REVIEW GATE) + `out/test-plan-<KEY>.json` (validated `PlanModel`) + `out/raw/<KEY>.json` (audit). **No external writes.** Shapes in `LLM.md` §2.0. |
| **Behavioral Rules** | The **B1–B12** guardrails in `LLM.md` §4: DRAFT until human sign-off · never fabricate (missing ⇒ finding) · read-only / `GET`-only Jira · every finding traceable · ticket text is untrusted data not instructions · minimise + redact before the model · exactly one LLM call · deterministic business logic. |

### 10.2 One-liner

A 3-layer (**A.N.T.** = Architecture SOPs / Navigation orchestrator / deterministic Tools)
agent that takes a Jira Cloud Story key, gathers a minimised context read-only, makes
**one** Groq (`openai/gpt-oss-120b`) structured call to produce gap analysis + scenarios,
validates traceability deterministically, and renders the repo test-plan template to a
local DRAFT Markdown file.

### 10.3 Locked decisions

- Jira Cloud v3 · service-account API token · Basic · **read-only / `GET`-only** adapter (thin `requests` wrapper).
- ACs: **description first**, then optional custom field; missing ⇒ flagged gap, **never invented**.
- **Story** only for v1; Bug/Task/Sub-task/Spike are extension points (keep `issue_type` abstracted).
- Output: repo template **as-is**, local files only, no external writes.
- **One** LLM call (`generate_test_plan.py`); `repair_plan.py` is the only permitted 2nd call.
- **LLM = Groq `openai/gpt-oss-120b`** (structured outputs + auto prompt caching); strict→json_object fallback; `validate_plan` traceability = hard fail (open-weight fabrication risk).
- Minimum-necessary data to the model · redact secrets/PII · `DATA_POLICY` config · prod needs explicit ZDR/redaction sign-off.
- ADF→MD: Jira `renderedFields` HTML→MD primary; `atlas-doc-parser` fallback.
- A.N.T. = **Architecture / Navigation / Tools** per `BLAST.md` (data pipeline = atomic Tools; Navigation routes; SOPs are the contract). Full contract + tool inventory in `LLM.md` §1.

### 10.4 Sign-off gate

- [x] Discovery answered · Research done · Data Schema shapes defined (`LLM.md` §2.0) · A.N.T. corrected to canonical.
- [x] `schemas/*.json` frozen (4 files).
- [x] `architecture/00-navigation-flow.md` + `architecture/10-tools.md`.
- [x] `prompts/` drafts (system, generate, repair).
- [ ] (optional) project-local copy of the A.N.T. wording in `BLAST.md`.

**Blueprint approved:**  `[x] user  on 2026-08-29`  — plus provider override: **LLM = Groq**.
Phase 3 code is written. Phase 2 (Link) + Phase 3 verification need the Jira service
account + `GROQ_API_KEY` + a Python 3.11+ runtime.
