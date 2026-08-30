# Test Plan Agent (B.L.A.S.T.)

Given a **Jira Cloud issue key**, produce a **review-ready DRAFT test plan** in the repo
template (`Chapter_02/stlc/01-test-planning/references/test-plan-template.md`): scope, gap
analysis, prioritised & traceable scenarios, and a HUMAN REVIEW GATE. Read-only against
Jira. Never invents a requirement — a missing one is a **finding**.

> Status: Phase 3 (build) complete, **not yet run** (needs credentials + a Python runtime).
> This is a preliminary README; the full runbook is Phase 5.

## Architecture (A.N.T., per `BLAST.md`)

| Layer | Where | What |
|-------|-------|------|
| **A** Architecture | `architecture/*.md` | SOPs — the contract. Golden Rule: change the SOP before the code. |
| **N** Navigation | `navigation/orchestrator.py` | Orders the tools, owns branching. No heavy lifting. |
| **T** Tools | `tools/*.py` | Atomic, deterministic scripts. One LLM call (`generate_test_plan`, Groq). |

Flow: `discover_fields → fetch_jira → normalize_issue → redact → budget →
generate_test_plan → validate_plan → (repair_plan) → render_plan`
(`architecture/00-navigation-flow.md`).

Boundary objects: `RawBundle → IssueContext → PlanModel` (`schemas/*.json`).

## Setup

```bash
python -m venv .venv && . .venv/Scripts/activate     # Windows;  .venv/bin/activate on *nix
pip install -r requirements.txt
cp .env.example .env      # then fill in JIRA_* and GROQ_API_KEY
```

`.env` needs: `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN` (read-only service account),
`GROQ_API_KEY`. See `.env.example` for the rest.

## Run

```bash
# Phase 2 — verify connectivity first (must print "LINK OK")
python -m tools.link_check PROJ-1234

# tests
pytest -q

# generate a plan
python cli.py PROJ-1234                 # human summary + files in out/
python cli.py PROJ-1234 --refresh --json
```

Outputs: `out/test-plan-<KEY>.md` (the deliverable), `out/test-plan-<KEY>.json` (validated
`PlanModel`), `out/raw/<KEY>.json` (audit). Intermediates in `.tmp/`.

Exit codes: `0` ok · `1` plan produced but `validation_failed` / `fetch_failed` · `2` bad input/config.

## LLM

Groq `openai/gpt-oss-120b` (OpenAI-compatible API). Structured Outputs (`strict:true`,
verified end-to-end) with a `json_object` fallback; automatic prompt caching.
`validate_plan.py` enforces the full schema + traceability regardless of the model.
See `findings.md` §11–§12.

**Groq free tier = 8,000 tokens/minute, 1,000 requests/day.** Defaults
(`REASONING_EFFORT=medium`, `MAX_COMPLETION_TOKENS=8000`) keep one run under that budget
(~1 run/minute; a run needing the repair call pauses ~20–60s). The client retries on
rate-limit. For `high` effort / real throughput, upgrade at
console.groq.com/settings/billing and set `REASONING_EFFORT=high`.

**Verified test issues (site `nancyverma0591.atlassian.net`):** `KAN-6` has description
acceptance criteria; `SAM1-7` / `SAM1-8` have none (the `source:"none"` path).

## Guardrails

`DATA_POLICY=standard|redacted|zdr` (`zdr` refuses — Groq has no zero-retention endpoint).
Secrets are stripped by `redact.py` before the model sees anything. Jira client is
`GET`-only. The plan is always `DRAFT` and ends at the HUMAN REVIEW GATE.
