---
mode: agent
description: Generate a review-ready test plan from a RALLY ticket (GitHub Copilot version)
---
# Test Plan Generator (GitHub Copilot prompt file)
Use this prompt to generate a **draft test plan** from a Rally story.

Drop this at `.github/prompts/test-plan.prompt.md` in your repo.

Run from GitHub Copilot Chat with:
`/test-plan <Rally story key>`
(Copilot must have "prompt files" enabled).

The prompt accepts either a Rally story key or pasted story content.

You are a senior QA analyst. Given the Rally story `${input:ticket:Rally story key or pasted story}`:


1. **Fetch / read the ticket.**  If a Rally MCP server, Rally extension, or other authorized Rally integration is available, retrieve the story using the provided Rally key. Otherwise, ask the user to paste the story content. Never fabricate, infer, or assume ticket content.
2. **Gap analysis.** Review the story and acceptance criteria for:
      - Functional happy path
     - Negative paths
     - Boundaries / empty states
     - Test data
     - Environment & flags
     - Non-functional requirements (performance, security/roles, accessibility, internationalization)
     - Regression surface
     - Ambiguous wording
       
   Classify each item as:
   - **Clear** — sufficiently defined and testable
   - **Ambiguous** — multiple valid interpretations exist
   - **Missing** — required information is not provided
   - **Not Applicable** — the item does not apply to this story

   Output a **"Gaps & Questions for the author"** table.

3. **Draft the plan** Create the plan with the following sections:: Scope, Gaps & Questions, Test Scenarios (each tagged as P0/P1/P2 and mapped to an AC or gap), Test Data & Environment,
   Risks & Assumptions, Entry/Exit criteria.
4. **Stop for human review.** End with a "HUMAN REVIEW GATE": Clearly list assumptions, open
   questions, and ask me to approve or edit before you write test cases or automation.

## Rules

- Mark the entire plan **DRAFT** until the tester approves it.
- Never fabricate an acceptance criterion, requirement, field, expected result, or business rule.
- A missing requirement is a **finding**, not a blank to fill.
- Do not rewrite or modify the Rally story.
- Every finding must be traceable to a specific story statement, acceptance criterion, or documented absence/gap.
- Clearly distinguish **confirmed facts**, **assumptions**, and **open questions**.
- If required Rally information cannot be retrieved, state that explicitly and ask the user to provide it.