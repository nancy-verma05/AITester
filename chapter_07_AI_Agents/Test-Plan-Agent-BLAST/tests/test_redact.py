import json

import pytest

from tools.redact import RedactError, redact


def _pre(**over):
    base = {
        "key": "D-1",
        "summary": "see key sk-abcdefghij0123456789ABCDEFGHIJKLM and mail a@b.com",
        "description_md": "token gsk_ABCDEFGHIJKLMNOPQRSTUVWX1234 and https://u:p@host/x",
        "acceptance_criteria": {"source": "none", "field_id": None, "items_md": []},
        "comments": [{"author": "Dev A", "created": "x", "body_md": "ping ops@corp.io", "trust": "untrusted"}],
    }
    base.update(over)
    return base


def test_strips_token_email_and_url_creds():
    out = redact(_pre())
    blob = json.dumps(out)
    assert "sk-abcdefghij0123456789" not in blob
    assert "gsk_ABCDEFGHIJKLMNOPQRSTUVWX" not in blob
    assert "a@b.com" not in blob and "ops@corp.io" not in blob
    assert "u:p@host" not in blob
    kinds = {r["kind"] for r in out["redactions"]}
    assert "token" in kinds and "email" in kinds


def test_author_display_name_is_kept():
    out = redact(_pre())
    assert out["comments"][0]["author"] == "Dev A"


def test_zdr_policy_refuses():
    with pytest.raises(RedactError):
        redact(_pre(), data_policy="zdr")


def test_records_token_estimate():
    out = redact(_pre())
    assert isinstance(out["token_estimate"], int) and out["token_estimate"] > 0
