# Format Spec

## Section order

1. Name + headline
2. Contact bar (dark navy, white text, hyperlinked) — **read from the attached resume**
3. Professional Summary — 3 lines maximum
4. *(Lead/manager roles only)* Leadership & Strategy — 3–4 labelled bullets whose labels mirror the JD's own responsibility headings verbatim
5. Skills — shaded chips in labelled category rows
6. Projects
7. Education

Drop section 4 entirely for individual-contributor roles; it reads as padding.

## Project entries

Each project gets **exactly three bullets**. No exceptions — concision is the point of the format.

Each bullet must:

- **Open with a power verb**, bolded and in navy. Vary them; never repeat a verb within one project.
  Good: Automated · Executed · Accelerated · Led · Re-architected · Delivered · Designed · Drove · Authored · Tracked · Scaled · Established · Owned
  Avoid: Responsible for · Worked on · Helped with · Participated in · Assisted
- **Carry a bolded number**, unless the user has explicitly said not to for that item.
- Describe an **outcome**, not a duty.

Header block per project:

```
**Project / client — descriptor**            [right tab] Dates
Role  ·  Company
▪ bullets
```

## Skills chips

Group into labelled category rows. Each row should fit on **one line** — trim chips rather than let a row wrap.

Never list a tool in two rows. Never list a skill that no bullet supports.

For a lead role, put a **Leadership & Strategy** row first.

## Layout

- A4, single column, **always one page**
- Calibri. Body 10–10.5pt; drop to 10pt to hold one page before touching anything else
- Navy `1F3864` for headings, verbs, and labels; body `222222`; chips `E9EEF6`
- Section headings: allCaps, bold, navy, with a bottom rule
- `keepNext` on every project header so a heading never strands from its bullets
- `keepLines` on every bullet so a bullet never splits across pages

## Fitting to one page — apply in this order

1. Trim chips so no skills row wraps
2. Tighten paragraph spacing
3. Shorten the wordiest bullets
4. Body 10.5pt → 10pt
5. Reduce margins (floor: 0.55" sides, 0.2" bottom)

Never drop below 10pt, and never cut a project below three bullets.

## Writing rules

- British/Indian spelling ("analyse", "specialising") — consistent with an India-based candidate
- No pronouns
- Every bullet ends in a full stop
- Present tense for the current role; past tense for all others
- Never repeat a tool name more than twice across the whole document
- Never use "responsible for"

## Verification before delivering

Render to image and **look at it**. Confirm:

- [ ] Exactly one page
- [ ] No orphaned heading at a page break
- [ ] No wrapped date in the header or education lines
- [ ] Contact bar holds one line
- [ ] No skills row wrapping to a stray second line
- [ ] No `[X]` placeholder left unflagged in the response
- [ ] `pandoc -t plain` extraction is clean and correctly ordered (ATS check)
