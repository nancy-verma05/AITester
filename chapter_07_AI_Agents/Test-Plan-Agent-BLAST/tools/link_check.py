"""Phase 2 (L - Link) handshake. Verifies .env + Jira + Groq connectivity BEFORE relying on
the full pipeline.  Run:  python -m tools.link_check [ISSUE-KEY]

Exits non-zero if any link is broken. Never prints secrets.
"""
from __future__ import annotations

import sys

from tools._config import ConfigError, load_settings, scrub
from tools._groq import GroqClient, GroqError, cached_tokens
from tools._jira import JiraClient, JiraError
from tools.discover_fields import discover_ac_field

_MINI_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["ok"], "properties": {"ok": {"type": "boolean"}},
}


def main(argv=None) -> int:
    argv = argv or sys.argv[1:]
    probe_key = argv[0] if argv else None
    try:
        st = load_settings()
    except ConfigError as e:
        print(f"FAIL  config: {e}")
        return 1
    sec = st.secrets
    ok = True

    # 1 - Jira auth
    jira = JiraClient(st.jira_base_url, st.jira_email, st.jira_api_token, timeout=st.http_timeout)
    try:
        me = jira.myself()
        print(f"PASS  jira auth: {me.get('displayName')} <{me.get('accountId')}>")
    except JiraError as e:
        print(f"FAIL  jira auth: {scrub(str(e), sec)}")
        ok = False

    # 2 - AC field discovery
    try:
        acf = st.jira_ac_field_id or discover_ac_field(jira)
        print(f"PASS  acceptance-criteria field: {acf or '(none found - will read from description)'}")
    except JiraError as e:
        print(f"WARN  field discovery: {scrub(str(e), sec)}")

    # 3 - optional issue probe
    if probe_key:
        try:
            iss = jira.get_issue(probe_key, fields="summary", expand="")
            print(f"PASS  issue probe {probe_key}: {iss['fields']['summary'][:60]!r}")
        except JiraError as e:
            print(f"FAIL  issue probe {probe_key}: {scrub(str(e), sec)}")
            ok = False

    # 4 - Groq models + structured output + caching
    groq = GroqClient(st.groq_api_key, timeout=st.http_timeout)
    try:
        ids = {m["id"] for m in groq.list_models()}
        for name in (st.model, st.model_small):
            mark = "PASS" if name in ids else "WARN"
            print(f"{mark}  groq model available: {name}")
        _, usage, mode = groq.chat_json(
            system="Reply with {\"ok\": true}.", users=["ping"], schema=_MINI_SCHEMA,
            schema_name="ping", model=st.model, reasoning_effort="low", seed=st.seed,
            max_completion_tokens=50,
        )
        print(f"PASS  groq structured output: mode={mode}")
        _, usage2, _ = groq.chat_json(
            system="Reply with {\"ok\": true}.", users=["ping"], schema=_MINI_SCHEMA,
            schema_name="ping", model=st.model, reasoning_effort="low", seed=st.seed,
            max_completion_tokens=50,
        )
        print(f"INFO  groq cached_tokens on 2nd identical call: {cached_tokens(usage2)}")
    except GroqError as e:
        print(f"FAIL  groq: {scrub(str(e), sec)}")
        ok = False

    print("\nLINK OK" if ok else "\nLINK BROKEN - do not proceed to full logic (BLAST Phase 2)")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
