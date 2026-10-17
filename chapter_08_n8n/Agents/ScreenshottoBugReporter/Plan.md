# Plan — Screenshot → Bug Reporter (n8n agent #08)

## Context
Filing bugs by hand is slow and the reports come out inconsistent. A tester should be able to upload a UI
screenshot (and paste error logs, if they have any) and get back a complete Jira Bug in project **KAN**:
title, steps to reproduce, expected vs actual result, visual details and a log summary, with the
screenshot attached. The existing chapter_08 workflows use Groq `openai/gpt-oss-20b`, which can only read
text, so this agent needs a vision model.

**Your decisions:** Jira (not GitHub) · project **KAN** · **Groq `qwen/qwen3.8-27b`** (free tier) · **n8n Form** upload.

## Deliverables (all in a new folder `chapter_08_n8n/Agents/ScreenshottoBugReporter/`)
1. `Plan.md`: this plan, including the model research, the text-arrow architecture diagram and the step table.
2. `08_Screenshot_to_bug_reporter_AIAgent.json`: a workflow you can import into n8n.

## Model research (vision-capable, prices from the live OpenRouter API / Groq docs, 2026-10-17)
One bug ≈ 2,048 image tokens + ~1.5k prompt/log tokens in, and ~1k tokens out.

| Option | Provider | $/M in / out | ≈ cost per bug | Notes |
|---|---|---|---|---|
| **qwen/qwen3.8-27b** ✅ chosen | Groq | free tier (paid ≈ $0.77 / $4.00) | **$0** | JSON-schema mode, 3 images max, 20 MB. **Preview** model. Free tier: 30 RPM, 1K RPD, **8K TPM** (≈2–3 bugs/min) |
| google/gemini-2.5-flash-lite | OpenRouter | 0.10 / 0.40 | ~$0.0005 | Best value among paid options, strong at reading UI text, stable. **Fallback** |
| meta-llama/llama-4-scout | OpenRouter | 0.10 / 0.30 | ~$0.0005 | Cheapest stable option, weaker OCR |
| qwen/qwen3-vl-30b-a3b-instruct | OpenRouter | 0.15 / 0.60 | ~$0.001 | Model built for vision + language |
| nvidia/nemotron-3.5-super-vl:free | OpenRouter | 0 / 0 | $0 | 50 req/day (1K with $10 credit); can be slow |
| openai/gpt-4o-mini | OpenRouter | 0.15 / 0.60 | ~$0.001 | Familiar baseline |

## Architecture
```
Form Trigger  ->  Prepare Input  ->  Analyze Screenshot (Groq Qwen 3.8)
                                                |
                                                v
Jira: Create Bug  <-  Format Description  <-  Parse Bug Report
        |
        v
Prepare Attachment  ->  Jira: Attach Screenshot  ->  Success Page (KAN-xx link)

(bad file / AI failure / Jira failure)  ->  Error Page
```

Deliberately **not** a `langchain.agent` node. The model gets exactly one bounded job: look at the
screenshot and logs, then fill in a fixed bug-report JSON. Every other step is a plain node or Code
node, so the AI never decides which tool to call or whether to create the ticket.

| Step | What happens | n8n node |
|---|---|---|
| 1 | Tester opens a web form, uploads the screenshot, and optionally adds logs and what they were doing | Form Trigger |
| 2 | Hide secrets (passwords, tokens) and shorten huge logs so the free AI limit isn't exceeded | Code |
| 3 | The AI reads the screenshot and logs, then fills in: title, steps, expected vs actual, severity | Basic LLM Chain + Groq Qwen + Output Parser |
| 4 | Turn that into a nicely formatted Jira Bug in project KAN and attach the screenshot | Code + Jira + Code + Jira |
| 5 | Show "Bug KAN-12 created" with a clickable link | Form (ending page) |

If the AI step fails, the tester sees an error page instead of step 5.

## How we will build it
```
Research models (done)  ->  Agree on choices (done)  ->  Write Plan.md
                                                              |
                                                              v
              Import into n8n and test  <-  Build the workflow JSON
```

## Workflow design
Sticky-note lanes follow the existing style in `Agents/02_CreateJiraTicket.json`: Trigger → AI Analysis → Jira → Result.

1. **Bug Report Form**: `n8n-nodes-base.formTrigger`. Fields: Screenshot (file, required, .png/.jpg/.jpeg/.webp),
   Error Logs (textarea, optional), What were you doing? (textarea, optional), Environment
   (text, optional: browser/OS/URL/build). Response mode: hand off to the final Form ending node.
2. **Prepare Input**: Code node. Renames the binary to `screenshot`, redacts obvious secrets in the logs
   (Bearer/API keys, passwords, JWTs), and passes the model only **≤ 6,000 chars** of logs (keeping the head
   and tail, which holds the stack trace end) so each run stays under Groq's 8K TPM. The full redacted log is
   kept for the Jira description.
3. **Analyze Screenshot**: `@n8n/n8n-nodes-langchain.chainLlm` (Basic LLM Chain), `hasOutputParser: true`.
   - System prompt: act as a senior QA engineer. Describe only what is visible or in the logs. **Never invent
     steps.** Inferred steps get an "(inferred)" marker, and anything unknown goes into `missing_info`.
   - Messages: the text prompt (user notes + environment + truncated logs) and an **Image (Binary)** message
     that reads the `screenshot` binary.
   - Error output turned on (`onError: continueErrorOutput`), routed to the failure ending.
   - Sub-nodes:
     - **Groq Chat Model**: `lmChatGroq`, model `qwen/qwen3.8-27b`, temp 0.2, max tokens 1500. Reuses the
       credential `Groq account` (id `aQ0FOogbmgOx2D6A`) from `02_CreateJiraTicket.json`.
     - **Fallback model**: OpenRouter Chat Model `google/gemini-2.5-flash-lite`. It only runs when Groq fails
       or hits a rate limit. Needs a new "OpenRouter account" credential. Optional: can be removed if you want $0 only.
     - **Structured Output Parser**: manual JSON schema. Wrapped in an **Auto-fixing Output Parser** that uses
       Groq `openai/gpt-oss-20b` (text-only, free) to repair bad JSON or remove stray `<think>` text.
4. **Format Jira Description**: Code node. Turns the JSON into Jira wiki markup: h3 sections, a numbered
   `#` list of steps, Expected/Actual, a Visual Observations table, Detected Errors, `{noformat}` logs (capped
   at 30k chars), and Missing Info. It maps severity to Jira priority (Critical→Highest, High→High, Medium→Medium, Low→Low).
5. **Create Jira Bug**: `n8n-nodes-base.jira`, create issue. Project KAN, issue type Bug, summary = `title`,
   description, priority, labels `["ai-bug-report","from-screenshot"]`. Reuses `Jira SW Cloud account` (id `R5GUFzrIM8e3KaF7`).
6. **Attach Screenshot**: Jira node, Issue Attachment → Add, issue key from step 5, binary `screenshot`.
7. **Success page**: `n8n-nodes-base.form` (completion). Shows "Bug KAN-xx created", the title, and a link to
   `https://nancyverma0591.atlassian.net/browse/{{key}}`. **Failure page**: completion form showing the error.

### Output schema (Structured Output Parser)
`title` (≤ 100 chars), `summary`, `severity` (Critical|High|Medium|Low), `affected_area` (page/component),
`environment`, `preconditions[]`, `steps_to_reproduce[]`, `expected_result`, `actual_result`,
`visual_observations[] {element, location, observation}`, `error_messages_detected[]` (read from the
screenshot and logs), `log_analysis`, `suspected_cause`, `labels[]`, `confidence` (high|medium|low), `missing_info[]`.

### Known risks and mitigations
- **Qwen 3.8 is a Preview model on Groq**, so it may be removed. The OpenRouter fallback handles that; to switch
  for good, change one model field.
- **8K TPM limit**: the log cap plus a 1,500-token output limit keep each run at about 6k tokens.
- **Image passthrough via the Groq LangChain node**: if `lmChatGroq` drops the image part, replace step 3 with an
  HTTP Request node to `https://api.groq.com/openai/v1/chat/completions`. It would send an `image_url`
  data-URI and use `response_format: json_schema`. This is checked during verification.
- **Jira IDs**: the JSON needs the numeric IDs for KAN and Bug. During implementation, look them up read-only
  with `GET /rest/api/3/project/KAN` if Jira creds are available (chapter_07 `.env`). Otherwise use resource-locator
  "list" mode so you select KAN / Bug once after import.

## Implementation steps
1. Create `Agents/ScreenshottoBugReporter/` and write `Plan.md` (this content).
2. Look up the IDs for project KAN and issue type Bug (read-only).
3. Write `08_Screenshot_to_bug_reporter_AIAgent.json` with the node types and versions used in the existing
   files (chainLlm, lmChatGroq v1, outputParserStructured, sticky notes), with `settings.executionOrder: v1`
   and `binaryMode: separate` as in `02_CreateJiraTicket.json`.
4. Check that the JSON parses (`node -e "JSON.parse(...)"`) and that every `connections` entry names a node that exists.

## Verification
1. Import the JSON into n8n, confirm the credentials (Groq, Jira, plus OpenRouter if you keep the fallback), then open the Form test URL.
2. **Happy path**: upload a real error screenshot plus a stack trace. Expect a KAN Bug with numbered steps,
   expected/actual, visual observations, the screenshot attached, and the success page linking to it.
3. **Screenshot only** (no logs): the bug is still created, and `missing_info` asks for logs/steps.
4. **Huge log** (> 50k chars): no 413/TPM error, and the description holds the capped log.
5. **Non-image / blurry upload**: the form rejects the file type, or the bug has `confidence: low`.
6. **Groq failure** (temporarily use a bad model id): the fallback model or the failure page is triggered.
7. In the execution view, check the Groq token usage per run stays below 8K.

## Build status (2026-10-18)
- `08_Screenshot_to_bug_reporter_AIAgent.json` built: 17 nodes (4 sticky notes). JSON parses, every connection
  targets a real node, and all three Code nodes were dry-run with mock data.
- Node versions match your n8n (it already runs Basic LLM Chain 1.9): Form Trigger 2.2, Form 1, Code 2,
  Basic LLM Chain 1.9, Groq Chat Model 1, OpenRouter Chat Model 1, Structured Output Parser 1.3 (built-in auto-fix), Jira 1.
- Extra **Prepare Attachment** Code node: the Jira create response carries no file, so it re-attaches the screenshot.
- **Jira priority is not set** (team-managed projects often reject it). Severity goes into the description and a `severity-*` label.
- Not live-tested: the Jira token and Groq key in chapter_07 `.env` are expired, so KAN/Bug IDs and Groq vision
  must be confirmed inside n8n.

## After import (one-time setup)
1. **Create Jira Bug** node → pick Project **KAN** and Issue Type **Bug** from the dropdowns.
2. **OpenRouter Fallback** node → create an "OpenRouter account" credential (or open *Analyze Screenshot*, turn off
   *Enable Fallback Model*, and delete the node for $0-only).
3. Check the Groq and Jira credentials are selected on their nodes, then open the Form test URL.
