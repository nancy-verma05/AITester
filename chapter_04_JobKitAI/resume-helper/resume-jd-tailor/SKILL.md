---
name: resume-jd-tailor
description: Tailor Nancy Verma's resume to a specific job description. Extracts JD requirements and keywords, cross-references them against verified experience, asks about genuine skill gaps before writing, and produces one tailored single-page resume as a Google Doc (with .docx fallback). Use when given a job description and asked to tailor, customise, adapt, or rewrite a resume for a role or application.
---

# Resume → JD Tailoring

Tailors an existing resume to one job description. **Tailoring only** — this skill does not score or review a resume from scratch.

## Inputs

1. **A resume file**, attached by the user each run (`.docx` or `.pdf`). This is the base and the source of contact details — never invent contact details, and never carry them over from a previous run.
2. **A job description**, pasted as text or attached.

If either is missing, ask for it before doing anything else.

## Output

**One file**: the tailored clean resume. Changes are reported in the chat response, not highlighted in the document.

Delivery order:

1. Build the `.docx` locally.
2. If a **Google Drive** connector is available this session, upload it so the user gets a Google Doc. Give them the link.
3. If not, deliver the `.docx` with `SendUserFile` and tell them in one line that connecting Google Drive at claude.ai would let future runs write to Drive directly. Do not retry or work around a missing connector.

## Workflow

### Step 1 — Read both inputs
Extract the resume's full text and its contact block. Read the JD completely before writing anything.

### Step 2 — Extract JD requirements
Build an explicit list of:

- **Role level** (IC / lead / manager) — this drives the whole repositioning
- **Must-have** skills, tools, and years, from a "minimum requirements" section
- **Nice-to-have** / preferred items
- **Repeated vocabulary** — words the JD uses more than once, and its responsibility headings verbatim. These are the highest-value keywords.

### Step 3 — Cross-reference against verified facts
Read `references/verified-facts.md`. Sort every JD requirement into:

- **Matched** — real evidence exists. Surface it using the JD's own vocabulary.
- **Gap** — no evidence. Go to Step 4.

### Step 4 — Ask about gaps (required)
For any JD tool or skill with no evidence in the verified facts, **ask the user before writing** whether they have picked it up since. Use `AskUserQuestion`, offer honest depth levels (none / learning / production), and place the answer at the level they give.

Never skip this step to save time. It is the only way newly-gained skills reach the resume, and the only thing standing between an honest resume and a fabricated one.

If the session is unattended and no answer is possible, treat every gap as absent and say so in the response.

### Step 5 — Reposition
If the JD's role level differs from how the resume currently leads, re-lead the headline and summary to match — **but only where the user has genuinely held that level**. A four-year Test Lead stint earns a "QA Team Lead" headline; six months of informal mentoring does not.

Job titles inside the experience section always stay factually accurate. Only the headline and summary reposition.

### Step 6 — Rewrite
Follow `references/format-spec.md` exactly. Weave matched keywords into real bullets. Never add a skills-section keyword that no bullet supports.

### Step 7 — Build
Write a config JSON and run:

```bash
node scripts/build_resume.js config.json output.docx
```

Then render and **look at the result** before delivering:

```bash
soffice --headless --convert-to pdf output.docx --outdir .
pdftoppm -jpeg -r 130 output.pdf page
```

Read the image. Confirm: exactly one page, no orphaned heading at a page break, no wrapped date, no chip row wrapping awkwardly. Adjust spacing and rebuild until it is right.

### Step 8 — Log the application
Append a row to `claude/application-tracker.md` in the LearnResume project (`project_read`, add the row, `project_write` the whole doc back). Create the doc with this header if it does not exist:

```markdown
| Date | Company | Role | Level | Keywords matched | Gaps flagged | File |
|---|---|---|---|---|---|---|
```

Then state, in the response, which gap has now appeared across the most applications — that is the one worth closing.

### Step 9 — Report
In the chat response, cover:

- What was repositioned, and the evidence justifying it
- Which JD keywords were added and where
- **Which JD requirements were deliberately left out, and why** — never bury this
- Any minimum requirement the user does not meet, stated plainly

## Absolute rules

1. **Never invent a number.** Metrics come from `references/verified-facts.md` or from the user in this session. If a bullet needs a number nobody has, use a bracketed `[X]` placeholder and list it for them to fill.
2. **Never claim a tool from the do-not-claim list** unless the user says in this session that they now have it.
3. **Never contradict the corrections log** in the verified facts. Those are things the user has explicitly fixed.
4. **Never carry contact details between runs.** Always read them from the attached resume.
5. **Distinguish an outcome from a programme.** "Zero critical escapes" is a result. "Established defect-escape-rate metrics" is a practice. Do not upgrade one into the other.
6. **Single column always.** Two-column layouts scramble in ATS parsers. If the user asks for two columns, build it, but say plainly what it costs.
