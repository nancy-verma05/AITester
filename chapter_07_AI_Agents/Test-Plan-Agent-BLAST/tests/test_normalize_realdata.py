"""Normalisation against a real Jira payload (KAN-6, fetched 2026-08-30).
KAN-6 puts its acceptance criteria under a bold list-item label
('- **Acceptance Criteria:**'), NOT a heading - the common Jira story-template shape."""
import json
from pathlib import Path

import pytest

from tools.normalize_issue import normalize

FIX = Path(__file__).parent / "fixtures" / "raw_bundle_kan-6.json"

pytestmark = pytest.mark.skipif(not FIX.exists(), reason="real-data fixture not present")


@pytest.fixture
def kan6():
    return json.loads(FIX.read_text(encoding="utf-8"))


def test_ac_extracted_from_bold_label_block(kan6):
    ctx = normalize(kan6)
    ac = ctx["acceptance_criteria"]
    assert ac["source"] == "description"
    assert ac["items_md"] == [
        "Page loads within 2 seconds.",
        "Displays user name, email, and avatar image.",
        "If no avatar exists, show a default placeholder icon.",
    ]


def test_basic_shape(kan6):
    ctx = normalize(kan6)
    assert ctx["key"] == "KAN-6"
    assert ctx["url"].endswith("/browse/KAN-6")
    assert ctx["issue_type"] in {"Task", "Story"}
    assert "profile" in ctx["description_md"].lower()
    assert ctx["changelog_signal"]["status_flip_count"] >= 0
