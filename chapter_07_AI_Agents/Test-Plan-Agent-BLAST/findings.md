# Findings — Reading a Jira Issue for Test Planning

> Protocol 0 research file. Everything here is what we discovered about **how to get the
> data** the Test Plan Agent needs. Runnable `curl` and Python `requests` examples included.
> Nothing here is business logic — that lives in `LLM.md`.

---

## 0. How my thinking went

The agent's whole job splits into two halves: **acquire the truth from Jira** (this file)
and **reason about it without inventing anything** (`LLM.md`). If acquisition is wrong or
incomplete, the reasoning is worthless — so Protocol 0 spends its time here first.

The three things I expected to be hard, and what I found:

1. **"Where are the acceptance criteria?"** — There is no standard Jira field for this. It
   is almost always a *custom field* (`customfield_1xxxx`) whose id differs per site, or it
   is just prose in the description, or it is a marketplace add-on (Acceptance Criteria for
   Jira, "Definition of Done" checklists). So the agent needs a **field-discovery step**
   before it can fetch, plus a config override, plus a loud failure if it still can't find them.

2. **The description isn't a string.** Jira Cloud REST v3 returns rich text as **ADF**
   (Atlassian Document Format) — a JSON tree, not Markdown or HTML. Two ways out: ask Jira
   to render it (`expand=renderedFields` → HTML) and convert HTML→Markdown, or walk the ADF
   tree ourselves. HTML rendering is less work and handles tables/panels/links; we keep the
   raw ADF for the audit file.

3. **Cloud vs Data Center changes everything** — API version (v3 vs v2), ADF vs wiki markup,
   token type (API token/Basic vs PAT/Bearer). This is Discovery Question #1 and blocks
   Protocol 1. **The rest of this file assumes Jira Cloud + REST API v3** and notes DC deltas.

Design consequence: the fetch layer is a single **read-only adapter** with one method
`get_issue_context(key) -> IssueContext`. It makes 4–6 GET calls, never a POST/PUT.

---

## 1. Environment / confirmed constraints (Discovery answers, 2026-08-29)

| Thing | Value — **confirmed** | Discovery Q |
|-------|-----------------------|-------------|
| Deployment | Jira **Cloud** (`https://<site>.atlassian.net`) | #1 ✅ |
| API | REST **v3** (`/rest/api/3/...`), Agile v1 (`/rest/agile/1.0/...`). No v2/DC branches. | #1 ✅ |
| Auth | **Dedicated service account** + Cloud **API token**, HTTP **Basic**. **Read-only** perms, no write. | #2 ✅ |
| AC location | **Description first**; also a configured AC **custom field** if one exists; if neither → **flag as gap, do not invent**. | #3 ✅ |
| Issue types | **Story** for Protocol 1; Bug/Task/Sub-task/Spike are later extension points. | #4 ✅ |
| Output | Local Markdown only, repo template as-is. **Zero** Jira writes. | #5, #6 ✅ |
| Data policy | Send **minimum required** content to the model; redact secrets/PII; ZDR/redaction is an explicit pre-prod config. | #9 ✅ |

Environment variables the adapter will read (never hard-code, never commit):

```bash
export JIRA_BASE_URL="https://your-site.atlassian.net"
export JIRA_EMAIL="nancy.verma0591@gmail.com"
export JIRA_API_TOKEN="**** create at https://id.atlassian.com/manage-profile/security/api-tokens ****"
```

---

## 2. Authentication

### 2a. Jira Cloud — API token + Basic auth (what we plan to use)

`Authorization: Basic base64("<email>:<api_token>")`. `curl -u` does the encoding for you.

```bash
# Sanity check: who am I, and does the token work?
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -H "Accept: application/json" \
  "$JIRA_BASE_URL/rest/api/3/myself" | jq '{accountId, emailAddress, displayName}'
```

Required product/scope: read access to the project ("Browse Projects" permission). For an
OAuth app the classic scope is `read:jira-work` (granular: `read:issue:jira`,
`read:comment:jira`, `read:field:jira`, `read:issue-link:jira`, `read:issue.remote-link:jira`).

### 2b. Jira Cloud — OAuth 2.0 (3LO) (alternative)

Exchange an auth code for a bearer token, then call the **api.atlassian.com** gateway with
your cloudid:

```bash
# 1. cloudid for the site
curl -s -H "Authorization: Bearer $OAUTH_TOKEN" \
  https://api.atlassian.com/oauth/token/accessible-resources | jq '.[].id'

# 2. issue call through the gateway
curl -s -H "Authorization: Bearer $OAUTH_TOKEN" -H "Accept: application/json" \
  "https://api.atlassian.com/ex/jira/$CLOUD_ID/rest/api/3/issue/PROJ-1234"
```

### 2c. Jira Data Center / Server — Personal Access Token (Bearer)

```bash
curl -s -H "Authorization: Bearer $JIRA_PAT" -H "Accept: application/json" \
  "$JIRA_BASE_URL/rest/api/2/issue/PROJ-1234?expand=renderedFields"
```

DC deltas: use `/rest/api/2/`; rich text is **wiki markup** (not ADF) — `renderedFields`
still gives HTML; no `api.atlassian.com` gateway.

---

## 3. Core endpoints the agent uses

| # | Purpose | Method + path |
|---|---------|---------------|
| E1 | Get the issue with rendered rich text | `GET /rest/api/3/issue/{key}?expand=renderedFields,names,changelog` |
| E2 | Discover the Acceptance Criteria custom field | `GET /rest/api/3/field` |
| E3 | Comments (rendered) | `GET /rest/api/3/issue/{key}/comment?expand=renderedBody` |
| E4 | Remote links (Confluence design docs, Figma, etc.) | `GET /rest/api/3/issue/{key}/remotelink` |
| E5 | Linked / related issues via JQL | `POST /rest/api/3/search/jql` (new) or `GET /rest/api/3/search` (legacy) |
| E6 | Attachments metadata (already in E1 `fields.attachment`) | download: `GET {attachment.content}` |
| E7 | Epic children (Agile) | `GET /rest/agile/1.0/epic/{epicKey}/issue` |
| E8 | Issue via Agile API (adds `sprint`, `epic`, `closedSprints`) | `GET /rest/agile/1.0/issue/{key}` |

> **Deprecation note:** the unbounded `GET /rest/api/3/search` is being retired in favour of
> `POST /rest/api/3/search/jql` (token-paginated, must pass an explicit `fields` list). Build
> the adapter against the new endpoint; keep the old one only as a fallback for DC.

### E1 — the main call

```bash
FIELDS="summary,description,issuetype,status,priority,labels,components,fixVersions,\
parent,subtasks,issuelinks,attachment,assignee,reporter,created,updated,duedate,\
environment,versions"

curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" -H "Accept: application/json" -G \
  "$JIRA_BASE_URL/rest/api/3/issue/PROJ-1234" \
  --data-urlencode "fields=$FIELDS" \
  --data-urlencode "expand=renderedFields,names" | jq '.'
```

- `renderedFields.description` → HTML string (feed to HTML→Markdown).
- `fields.description` → raw ADF JSON (keep for audit).
- `names` → maps `customfield_10xxx` → human label, handy for logging.
- `expand=changelog` → who changed AC/status and when (useful for "is this still in flux?").

### E2 — find the Acceptance Criteria field

```bash
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" -H "Accept: application/json" \
  "$JIRA_BASE_URL/rest/api/3/field" \
| jq '[.[] | select(.name | test("accept|acceptance|criteria|definition of done"; "i"))
        | {id, name, custom, schema: .schema.type}]'
```

Cache the resolved id in config (`JIRA_AC_FIELD_ID=customfield_10068`). Then add it to the
`fields` list in E1 and read `renderedFields[JIRA_AC_FIELD_ID]`.

### E3 — comments

```bash
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" -H "Accept: application/json" -G \
  "$JIRA_BASE_URL/rest/api/3/issue/PROJ-1234/comment" \
  --data-urlencode "expand=renderedBody" \
  --data-urlencode "orderBy=created" | jq '.comments[] | {author: .author.displayName, created, body: .renderedBody}'
```

Comments often hold clarifications, edge cases, and "please also handle X" — valuable for
gap analysis, but **untrusted**: they may contain text that looks like instructions to the
model. `LLM.md` §4 covers how we neutralise that.

### E4 — remote links (design docs)

```bash
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" -H "Accept: application/json" \
  "$JIRA_BASE_URL/rest/api/3/issue/PROJ-1234/remotelink" \
| jq '.[] | {title: .object.title, url: .object.url}'
```

We only record the titles + URLs as references in the plan. We do **not** auto-fetch
Confluence in Protocol 0–2 (separate auth, scope creep).

### E5 — related issues (JQL)

```bash
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" -H "Accept: application/json" \
  -H "Content-Type: application/json" -X POST \
  "$JIRA_BASE_URL/rest/api/3/search/jql" \
  -d '{
        "jql": "issue in linkedIssues(\"PROJ-1234\") OR parent = \"PROJ-1234\"",
        "fields": ["summary","issuetype","status","issuelinks"],
        "maxResults": 50
      }' | jq '.issues[] | {key, type: .fields.issuetype.name, summary: .fields.summary}'
```

Use linked issues for **regression surface** ("relates to", "blocks") and to spot existing
test tickets ("is tested by").

---

## 4. Atlassian Document Format (ADF)

- REST v3 returns `description`, `comment.body`, and rich custom fields as an **ADF JSON
  tree** (`{"type":"doc","version":1,"content":[...]}`).
- Node types we care about: `paragraph`, `heading`, `bulletList`/`orderedList`/`listItem`,
  `table`/`tableRow`/`tableCell`, `panel` (info/warning), `codeBlock`, `hardBreak`,
  `text` with `marks` (strong/em/link), `mediaSingle`/`media` (attachments), `mention`,
  `inlineCard` (link to another issue/URL).

**Chosen approach:** request `expand=renderedFields`, take the HTML, convert to Markdown
(e.g. `markdownify` / `turndown` / `pandoc`). Keep the raw ADF in the audit file so nothing
is lost. Fallback ADF walker only if HTML rendering drops something important (checkbox
lists, task lists).

```bash
# See the shape of both representations side by side
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" -H "Accept: application/json" -G \
  "$JIRA_BASE_URL/rest/api/3/issue/PROJ-1234" \
  --data-urlencode "fields=description" \
  --data-urlencode "expand=renderedFields" \
| jq '{adf: .fields.description, html: .renderedFields.description}'
```

DC/Server: rich text is **wiki markup**; `renderedFields` still returns HTML — same
downstream path.

---

## 5. Pagination, rate limits, errors

| Concern | Detail | Adapter behaviour |
|---------|--------|-------------------|
| Pagination | Comments & search are paged (`startAt`/`maxResults`, or `nextPageToken` on `/search/jql`) | Loop until no next page; cap comments at e.g. 100 with a note |
| Rate limits | HTTP `429` + `Retry-After` header; Cloud uses a cost budget | Exponential backoff, honour `Retry-After`, max 4 retries |
| 404 | Bad key **or** no permission (Jira hides existence) | Report "issue not found or not visible to this account" — do not retry |
| 401/403 | Bad token / missing scope | Fail fast with a clear message, never log the token |
| 5xx | Atlassian transient | Retry with backoff |
| Big payloads | Epics, long changelogs | Request only needed `fields`; drop `changelog` unless used |

---

## 6. MCP alternative (if we build on an agent runtime with MCP)

Instead of hand-rolling REST, the agent can call the **Atlassian Remote MCP Server**
(`https://mcp.atlassian.com/v1/sse`, OAuth) or the community `mcp-atlassian` server. Useful
tools it exposes: `getJiraIssue`, `searchJiraIssuesUsingJql`, `getConfluencePage`.

Trade-off: MCP removes auth/ADF plumbing but gives us less control over exactly which
fields come back and how rich text is serialised. **Decision for Protocol 1:** prefer a
thin REST adapter (predictable, testable with fixtures); keep MCP as a config-switchable
backend. Either way the adapter's output contract is the same `IssueContext` (see `LLM.md`).

---

## 7. Reference: minimal Python fetch (for Protocol 2, not run yet)

```python
import os, requests
from requests.auth import HTTPBasicAuth

BASE  = os.environ["JIRA_BASE_URL"].rstrip("/")
AUTH  = HTTPBasicAuth(os.environ["JIRA_EMAIL"], os.environ["JIRA_API_TOKEN"])
HEAD  = {"Accept": "application/json"}
AC_FIELD = os.environ.get("JIRA_AC_FIELD_ID")  # resolved once via /field

FIELDS = ["summary","description","issuetype","status","priority","labels",
          "components","fixVersions","parent","subtasks","issuelinks",
          "attachment","assignee","reporter","created","updated","environment"]

def _get(path, **params):
    r = requests.get(f"{BASE}{path}", auth=AUTH, headers=HEAD, params=params, timeout=30)
    r.raise_for_status()
    return r.json()

def resolve_ac_field():
    for f in _get("/rest/api/3/field"):
        if f["name"].strip().lower() in {"acceptance criteria", "acceptance criteria (ac)"}:
            return f["id"]
    return None

def get_issue_raw(key: str) -> dict:
    fields = FIELDS + ([AC_FIELD] if AC_FIELD else [])
    issue = _get(f"/rest/api/3/issue/{key}",
                 fields=",".join(fields),
                 expand="renderedFields,names")
    comments = _get(f"/rest/api/3/issue/{key}/comment", expand="renderedBody")
    remote   = _get(f"/rest/api/3/issue/{key}/remotelink")
    return {"issue": issue, "comments": comments, "remote_links": remote}
```

`raise_for_status()` is a placeholder — the real adapter uses the typed retry/backoff
behaviour from §5 and a most-specific-first error chain.

---

## 8. Field → Test Plan section mapping

This is the contract between "what Jira gives us" and "what the plan needs". A blank cell
becomes a **finding**, never a guess.

| Test plan section | Source field(s) | Notes |
|-------------------|-----------------|-------|
| Title / key | `key`, `fields.summary` | — |
| Scope & Objectives — in scope | `renderedFields.description`, AC field | Derive from stated behaviour only |
| Scope — out of scope | explicit "out of scope" text, `labels` | If absent → finding |
| Acceptance criteria (basis for scenarios) | `renderedFields[AC_FIELD]` else description | If none → **major finding**, ask author |
| Gaps & Questions | *derived* by gap analysis | Every row traces to a statement or a documented absence |
| Test Scenarios | AC + description + comments | Tag P0/P1/P2, map each to an AC/gap |
| Test Data | description, comments, `environment` field | Usually a gap |
| Environment / Feature Flags | `fields.environment`, `components`, `fixVersions`, labels like `flag:*` | — |
| Roles / Permissions | description/AC mentions of roles | Often a gap |
| Risks & Assumptions | `issuelinks` (blocks/relates), `priority`, changelog churn | Assumptions must be labelled |
| Entry / Exit criteria | `status`, `fixVersions`, project workflow | Partly template boilerplate |
| References | `remotelink` titles+URLs, linked issue keys | Titles only, no auto-fetch |
| Regression surface | `issuelinks` type "relates to", affected `components` | Feeds P1/P2 scenarios |

---

## 9. Open questions / unknowns (carry into Protocol 1)

Resolved by Discovery answers (2026-08-29): ~~Cloud or DC~~ → Cloud; ~~send raw ticket text?~~
→ no, minimise + redact, ZDR is a pre-prod config.

Still open:

- [ ] Exact AC custom field id(s) for the target project(s) — run `GET /rest/api/3/field`
      against the real site once credentials exist; set `JIRA_AC_FIELD_ID`.
- [ ] Is there a checklist add-on holding ACs/DoD that isn't in the REST field payload?
- [ ] Are ADF tables/panels used heavily enough to need the custom ADF walker (vs HTML→MD)?
- [ ] Any team-specific fields for test data / NFRs missing from the §8 mapping table?
- [ ] Rate-limit budget on the target Jira site (affects a future batch mode).
- [ ] Service-account creation + which projects it can browse.

---

## 10. Prior art & libraries (Phase 1 — B / Research)

BLAST Phase 1 step 3: "Search GitHub repos and other databases for helpful resources."

### Similar projects (confirm the design, don't adopt wholesale)

| Project | What it does | Take-away for us |
|---------|--------------|------------------|
| [thetestingacademy — "Jira to Test Plan" Copilot skill](https://app.thetestingacademy.com/ai/skill-test-plan) | `fetch_jira.py` (REST v3, Basic auth) → normalise ADF→text → LLM → plan with Scope/Scenarios/Cases/Negative+Boundary → export PDF/XLSX. Guardrails: every AC maps to ≥1 positive **and** ≥1 negative case; atomic imperative steps; assumptions listed; **missing items flagged not fabricated**; human review gates all output. | **Near-identical architecture and guardrails to ours** — strong validation of the approach. Adopt the "each AC → ≥1 positive + ≥1 negative" rule into `validate_plan.py`. We stop at the plan (no test cases/export) for v1. |
| [major/jira-agent](https://github.com/major/jira-agent) | LLM-first CLI for Jira Cloud. | Reference for CLI ergonomics + Jira Cloud auth handling. |
| [Abdellah-Laassairi/jiragen](https://github.com/Abdellah-Laassairi/jiragen) | CLI that *creates* Jira issues via LLM + Jira API. | Opposite direction (write); useful only for API-wrapper patterns. |
| [lewisExternal/Custom-AI-Jira-Agent](https://github.com/lewisExternal/Custom-AI-Jira-Agent) | LangChain agent doing triage on new issues; CO-STAR system prompt + CoT + few-shot. | Prompt-structure reference for the `generate_test_plan` system prompt. |
| Justin Mulcahy, ["How I Built an AI Agent That Writes My Test Plans"](https://medium.com/@justin.mulcahy/how-i-built-an-ai-agent-that-writes-my-test-plans-and-posts-them-to-jira-e42d643b1230) | Blog: Jira story → test plan → posts to Jira. | We deliberately **do not** post back (Q6). |

### ADF → Markdown libraries

| Library | Notes | Verdict |
|---------|-------|---------|
| Jira `expand=renderedFields` (no lib) | Jira renders ADF → HTML server-side; we convert HTML→MD (`markdownify`). Handles tables/panels/links/media refs. | **Primary path.** |
| [`atlas-doc-parser`](https://atlas-doc-parser.readthedocs.io/) (`pip install atlas-doc-parser`) | Parses ADF JSON → Python objects → Markdown. Explicitly aimed at "making Atlassian content accessible to LLMs". | **Fallback ADF walker** when HTML rendering drops something (task lists, checkboxes). |
| [`marklassian`](https://libraries.io/pypi/marklassian) / [`marklas`](https://github.com/byExist/marklas) / [`pyadf2md`](https://github.com/DiPaolo/pyadf2md) | Other ADF↔MD converters; `marklassian` is MD→ADF (wrong direction), `marklas`/`pyadf2md` are ADF→MD. | Evaluate only if `atlas-doc-parser` gaps show up in Phase 3. |

### Jira client

- **Decision:** thin `requests` wrapper (see §7), **not** [`atlassian-python-api`](https://github.com/atlassian-api/atlassian-python-api) — its `jira.jql()` is deprecated for Cloud (must move to `POST /rest/api/3/search/jql`), and we want explicit `fields` / `expand` control for minimisation (Q9) and fixture-testability. `atlassian-python-api` stays a possible future convenience, not a Phase 2 dependency.

### 3-layer architecture references (A.N.T. background)

- [AI Agents in Production: The Three-Layer Architecture](https://aienhancedengineer.substack.com/p/ai-agents-in-production-the-three) — SOP / decision / execution split; "simulate before actuate, gate authority with narrow capabilities, enforce deterministic guards at the boundary, instrument everything for replay." Matches BLAST's A.N.T. intent.
- [SOP-Agent](https://www.emergentmind.com/topics/standard-operational-procedure-guided-agent-sop-agent) — SOP-guided navigation restricting the agent's actions to the valid branch at each step; supports our "Navigation reads the SOP, calls tools in order" model.

---

## 11. Groq as the LLM (Phase 3 — user override "Use GROQ.com as LLM")

Sources: [Structured Outputs](https://console.groq.com/docs/structured-outputs) ·
[Models](https://console.groq.com/docs/models) ·
[Prompt caching](https://console.groq.com/docs/prompt-caching) ·
[Reasoning](https://console.groq.com/docs/reasoning) ·
[API reference](https://console.groq.com/docs/api-reference).

### API shape
- **OpenAI-compatible.** Base `https://api.groq.com/openai/v1`. SDK: `pip install groq` →
  `from groq import Groq; Groq()` (reads `GROQ_API_KEY`). Raw: `Authorization: Bearer $GROQ_API_KEY`.
- List models live: `GET https://api.groq.com/openai/v1/models`.
- Chat: `POST /openai/v1/chat/completions` — `messages`, `model`, `temperature`, `top_p`,
  `seed`, `max_completion_tokens`, `response_format`, `reasoning_effort`, `include_reasoning`.

### Model
- **`openai/gpt-oss-120b`** — 131K context, 65K max completion, open-weight **reasoning**
  model, Groq's recommended general/reasoning model. Supports Structured Outputs **and**
  automatic prompt caching. Primary for `generate_test_plan` + `repair_plan`.
- **`openai/gpt-oss-20b`** — same family, cheaper; `budget.py` summariser only.
- Live list may also show `llama-3.3-70b-versatile`, `qwen/qwen3-32b` (also supports strict
  structured outputs). `MODEL` / `MODEL_SMALL` are env vars — swap after Phase 4 evals.

### Structured Outputs
```json
"response_format": {
  "type": "json_schema",
  "json_schema": { "name": "plan_model", "strict": true, "schema": { /* restricted */ } }
}
```
- `strict: true` supported on GPT-OSS 20B/120B and Qwen3-32B; uses constrained decoding →
  100% schema adherence, never invalid JSON.
- **Strict-mode schema restrictions** (why we need `plan_model.groq.schema.json`):
  every property in `required`; `additionalProperties:false` on every object; **no**
  `pattern`, `format`, `minItems`/`maxItems`, `minLength`/`maxLength`, `const`; optionals
  as `["type","null"]`; `enum`, `anyOf`, `$defs`, `$ref` allowed.
- **Known risk:** some GPT-OSS builds have been reported to *ignore* `json_schema`.
  Mitigation: our tool does a one-shot fallback to `{"type":"json_object"}` + schema-in-prompt,
  and `validate_plan.py` enforces the full schema regardless.
- Groq strict is *stricter than OpenAI* about `required` — list every property.

### Prompt caching
- **Automatic** on `openai/gpt-oss-*` (and `-safeguard`). No code, cannot disable.
- 50% discount on cached input tokens; min cacheable prefix 128–1024 tok (model-dependent);
  **~2 h TTL**. Cache hit reported as `usage.prompt_tokens_details.cached_tokens`.
- Only helps with a byte-stable prefix → system(prompt+schema) and instructions first,
  `IssueContext` JSON (sorted keys) last.

### Reasoning
- `reasoning_effort`: GPT-OSS accepts `low` / `medium` / `high`. We use `high` (generate),
  `medium` (repair), `low` (budget summariser).
- `include_reasoning=false` for GPT-OSS (we never use the reasoning trace).
  `reasoning_format:"raw"` is **rejected** together with JSON mode — don't set it.

### Not available (were in the Anthropic design) → replacement
| Anthropic | Groq replacement |
|-----------|------------------|
| `thinking:{type:"adaptive"}` | `reasoning_effort` |
| `output_config.format` / `messages.parse()` | `response_format:{type:"json_schema",strict:true}` + our `jsonschema` check |
| `cache_control` breakpoints | automatic caching (prefix hygiene only) |
| server-side `fallbacks` / `refusal` handling | our strict→json_object retry + `validate_plan` + `repair_plan` |
| streaming `.get_final_message()` | plain call; set `max_completion_tokens` generously |

---

## 12. Manual Link check — 2026-08-30 (curl/node, no Python)

Real credentials in `.env` verified against the live services (BLAST Phase 2, done by hand
because there is still no Python runtime on the dev machine):

| Check | Result |
|-------|--------|
| Jira `GET /rest/api/3/myself` | ✅ 200 — auth works (site `nancyverma0591.atlassian.net`, "NANCY verma") |
| Jira `GET /rest/api/3/field` — AC custom field | **none** — no "Acceptance Criteria" custom field on this site → agent uses the **description** path (`JIRA_AC_FIELD_ID` stays blank) |
| Jira `POST /rest/api/3/search/jql` | ✅ — but **rejects unbounded queries** ("add a search restriction"). Our `fetch_jira` query `issue in linkedIssues("K") OR parent = "K"` is accepted. |
| Jira projects | `KAN` (QA Testing), `SAM1` ((Example) Billing System Dev) |
| Groq `GET /openai/v1/models` | ✅ — `openai/gpt-oss-120b`, `openai/gpt-oss-20b`, `openai/gpt-oss-safeguard-20b`, `qwen/qwen3.6-27b`, `qwen/qwen3.8-27b` |
| Groq `POST /chat/completions` strict `json_schema` on `gpt-oss-120b` | ✅ 200 — returns clean schema-valid JSON; `include_reasoning:false` + `reasoning_effort` + `max_completion_tokens` all accepted; `finish_reason: stop` |
| Groq prompt-cache field on a 2nd identical call | not reported for a 148-token prompt (below the 128–1024 min cacheable length). `cached_tokens()` safely returns 0; expect real hits on the ~3–5k-token system+schema prefix. |

**Test issues found:**
- **KAN-6** — has real acceptance criteria (3 bullets) under a bold list-item label
  `- **Acceptance Criteria:**` (Jira story-template shape), **not** a heading. This broke
  the first `normalize_issue` AC regex — fixed 2026-08-30 (`_AC_LABEL` + `_NEXT_LABEL`,
  Node-verified; real-data fixture `tests/fixtures/raw_bundle_kan-6.json` +
  `tests/test_normalize_realdata.py`).
- **SAM1-7 / SAM1-8** — Tasks with a description but no ACs → exercise the `source:"none"` branch.

### 12a. Groq free-tier rate limits — real constraint (2026-08-30)

`x-ratelimit-limit-tokens: 8000` (**tokens per minute**), `x-ratelimit-limit-requests: 1000`
(per day), on **both** `gpt-oss-120b` and `gpt-oss-20b`. Token bucket refills continuously
(~20s to usable). Groq counts prompt + reserved completion against the TPM budget.

End-to-end tests against KAN-6 (a real ticket with 3 ACs):

| Config | total tok | time | outcome |
|--------|-----------|------|---------|
| `120b` · `high` · maxc 32000 · schema-in-prompt | ~18,200 | 30s | ✅ great plan (6 scenarios mapped to AC-1/2/3, 12 gaps) — but **exceeds 8k TPM**; the next call within the minute got **HTTP 413 rate_limit_exceeded** |
| `20b` · `low` · maxc 7000 | 3,529 | 1.5s | ❌ weak — 1 gap, 4 scenarios all `assumption` mapped to `G-1`, validation fails |
| **`120b` · `medium` · maxc 8000 · no schema-in-prompt** | **7,516** | 10s | ✅ **fits under 8k TPM**, `validate_plan` PASS, 12 gaps, 5 scenarios — **shipped default** |

**Design changes made (2026-08-30):**
- Defaults: `REASONING_EFFORT=medium` (not high), `MAX_COMPLETION_TOKENS=8000` (not 32000).
  Both are env vars — `high` works fine once the tier is upgraded.
- `generate_test_plan._system()` no longer embeds the full schema JSON (saved ~800–1600
  prompt tok); `response_format` + the json_object fallback still carry it.
- `_groq._post_chat` now treats **413/429 + `rate_limit`** as retryable — parses
  `retry-after` / "try again in Xs" / `x-ratelimit-reset-tokens`, sleeps (cap ~65s/attempt,
  ~130s total), then fails with an "upgrade the tier" message.
- Forced `plan["meta"]` overwrite in `generate`/`repair` — `gpt-oss` had hallucinated
  `meta.model: "test_plan_generator"`.
- `validate_plan` check 5 relaxed: assumption scenarios count as "surfaced" if reflected in
  `assumed` **or** `could_not_confirm` **or** `risks_assumptions.assumptions` (threshold 0.3);
  hard fail only when the whole gate is empty of assumptions.

**Recommendation to the user:** for anything beyond occasional single runs, upgrade to Groq
Dev Tier (higher TPM). On the free tier: ~1 run/minute; a run that needs the repair call
will pause ~20–60s mid-way.
