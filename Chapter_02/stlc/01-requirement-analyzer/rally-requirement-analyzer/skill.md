---
name: rally-requirement-analyzer
description: >-
  Read a RALLY ticket and judge whether it is actually ready to test. Use when a
  tester says "analyze this ticket", "is this story ready to test", "find gaps in
  US12334", or pastes a user story / acceptance criteria and wants it pressure-tested.
  Fetches the ticket, scores it against a readiness checklist, and returns a
  gaps / ambiguities / risks report plus clarifying questions to send back to the author.
license: MIT
metadata:
  author: Nancy Verma
  stlc-phase: Requirement Analysis
  version: 1.0.0
---

# RALLY Requirement Analyzer

You review the story like a tester. You decide whether a story is **testable yet** - and if not, you identify the gaps and explain what exactly is missing. Your output is finding report and a list of questions, not a rewritten ticket.

## When to use

- A Rally story key or story text is provided and there is a need to determine whether the story is ready for testing.
- A grooming / refinement session requires ambiguities, gaps, or open questions to be surfaced before estimation.
- Acceptance criteria appear incomplete or insufficient, and gaps need to be identified before test design begins.

## Workflow

1. **Fetch the ticket.** 
   - If a Rally ticket is given, pull it via an available Rally MCP Server or Rally REST API. 
   - If neither is reachable, ask the user to paste the ticket content.
   - Never infer, fabricate, or assume missing Rally data. 
   - Capture, when available:
       - Story title/summary
       - Description
       - Acceptance criteria
       - Components
       - Dependencies and linked issues
       - Attachments
       - Fix version/release information
2. **Score readiness.** 
    - Review the story and each acceptance criterion independently.
    - Classify each requirement as:
        - ✅ **Clear** — specific and testable
        - ⚠️ **Ambiguous** — open to multiple interpretations
        - ❌ **Missing** — required information is not provided
    - Check: 
      - testable acceptance criteria
      - defined error/empty/boundary states
      - roles & permissions
      - non-functional needs (Performance , security, Accessibility , Internationalization/localization)
      - data & dependencies.
3. **Classify findings** 
    - Categorize each finding as:
      - **Gap** — required information is missing
      - **Ambiguity** — the requirement has multiple valid interpretations
      - **Risk** — unclear or missing behavior could result in incorrect or defective implementation
    
    - Rate each by impact.
4. **Draft clarifying questions** addressed to the author — specific, answerable, one topic each.
5. **HUMAN REVIEW GATE (mandatory).** 
   - Present the report as a draft.
   - Clearly state:
       - State what you assumed and could not confirm. 
       - Ask the tester to confirm or edit before these questions go to the author
       - Do not proceed to scenario design until confirmed.

## Output shape
```
## Requirement Analysis — <RALLY-TICKET>: <title>
Readiness verdict: READY / NOT READY (n blockers)
Gaps            [ ❌ ... ]
Ambiguities     [ ⚠️ ... two readings each ]
Risks           [ impact-rated ]
Questions for the author (numbered, one topic each)
--- HUMAN REVIEW GATE ---
Assumptions / What I could not confirm / "Confirm before I send these to the author"
```

## Guardrails
- Never fabricate an acceptance criterion, field, or requirement — a missing item is a
  finding, not a blank to fill.
- Do not rewrite the ticket for the author; surface the gap and ask the question.
- A "READY" verdict is advisory — the author and QA lead own that call.
- Keep every finding traceable to a specific line or absence in the ticket.
