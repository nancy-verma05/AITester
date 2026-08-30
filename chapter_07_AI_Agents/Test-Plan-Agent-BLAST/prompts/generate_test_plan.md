# User prompt — generate_test_plan (the one call)

> Draft v0.1 (Phase 1). Sent after the cached system prefix. The `IssueContext` JSON is
> appended after this text, inside `<untrusted_ticket_content>…</untrusted_ticket_content>`.

Produce one `PlanModel` JSON object for the issue below. Work only from its `IssueContext`.

Do these two things in the single response:

## 1. Gap analysis → `gaps[]`

For every coverage area (system prompt list), emit at least the areas that are relevant:

- `classification`: Clear / Ambiguous / Missing / Not Applicable.
- `evidence`: a verbatim quote from the `IssueContext`, **or** `ABSENT: <what is not stated anywhere>`.
  For `Not Applicable`, a one-line reason is fine.
- `evidence_ref`: `AC-<n>` / `description` / `summary` / `comment <date> by <author>` / `none`.
- `question_for_author`: a specific, answerable question when Ambiguous or Missing;
  the **empty string `""`** when Clear or Not Applicable (do not write "N/A").
- `severity`: P0 (blocks meaningful testing) / P1 / P2.
- Number them `G-1`, `G-2`, … Emit one gap per coverage area you assessed (Clear ones included,
  so the sweep is visible), but keep `Ambiguous wording` gaps only for genuinely ambiguous text.

If nothing is missing or ambiguous, emit one `G-1` with classification `Clear` and
`question_for_author` = `"No gaps found — please confirm with the author."`

## 2. Plan → the remaining `PlanModel` fields

- `scope.in_scope` / `scope.out_of_scope`: only what the ticket states. Unstated out-of-scope → one entry `"Not specified in ticket — see G-<n>"`.
- `scope.objective`: one sentence defining what "tested" means for this issue.
- `scenarios[]`: one per distinct observable behaviour / negative path / boundary.
  - `id` `TS-1`…; `priority` P0/P1/P2; `type` Positive/Negative/Boundary.
  - `scenario`: one assertion focus, observable, no implementation detail.
  - `maps_to`: an existing `AC-<n>` or `G-<n>`, never empty, never a dangling id.
    **Prefer the `AC-<n>` id** whenever the scenario verifies that acceptance criterion
    directly (positive or its negative/boundary); use a `G-<n>` id only for scenarios that
    exist *because of* a gap.
  - `basis`: `confirmed` only if the whole scenario follows from stated behaviour; else `assumption`.
  - Aim for ≥1 Positive and ≥1 Negative/Boundary per acceptance criterion.
- `test_data_env.{test_data,environment,roles}`: content from the ticket, or the literal
  `"Not specified in ticket — see G-<n>"`.
- `risks_assumptions.assumptions`: every assumption you relied on. `risks`: from linked
  "blocks"/"is blocked by" issues, high `priority`, or heavy `changelog_signal` churn.
- `entry_exit`: entry/exit criteria; template-standard ones are fine, plus anything issue-specific.
- `references`: `remote_links` (title + url) and linked issue keys only.
- `human_review_gate`:
  - `assumed`: mirror every `basis:"assumption"` scenario + every assumption above.
  - `could_not_confirm`: facts you needed but the ticket didn't give.
  - `open_questions`: the blocking questions for sign-off (superset of the P0 `question_for_author` items).

Return **only** the JSON.
