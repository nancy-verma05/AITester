from jsonschema import Draft202012Validator

from tools._util import load_schema
from tools.normalize_issue import normalize


def test_reads_ac_from_description_when_custom_field_empty(raw_bundle_min):
    ctx = normalize(raw_bundle_min)
    assert ctx["acceptance_criteria"]["source"] == "description"
    assert ctx["acceptance_criteria"]["items_md"] == [
        "Reset email is sent within 1 minute",
        "Link expires after 24 hours",
    ]


def test_basic_fields_and_minimisation(raw_bundle_min):
    ctx = normalize(raw_bundle_min)
    assert ctx["issue_type"] == "Story"
    assert ctx["priority"] == "High"
    assert ctx["components"] == ["Identity"]
    assert "password reset" in ctx["description_md"].lower()
    assert ctx["changelog_signal"]["status_flip_count"] == 1
    # nothing outside the mapped shape leaked in
    assert "customfield_10068" not in ctx


def test_pre_context_matches_issue_context_shape(raw_bundle_min):
    ctx = normalize(raw_bundle_min)
    ctx.update(redactions=[], token_estimate=10)  # added later by redact.py
    errors = list(Draft202012Validator(load_schema("issue_context.schema.json")).iter_errors(ctx))
    assert not errors, errors


def test_custom_field_wins_when_present(raw_bundle_min):
    raw_bundle_min["issue"]["renderedFields"]["customfield_10068"] = "<ul><li>Only AC here</li></ul>"
    ctx = normalize(raw_bundle_min)
    assert ctx["acceptance_criteria"]["source"] == "custom_field"
    assert ctx["acceptance_criteria"]["items_md"] == ["Only AC here"]
