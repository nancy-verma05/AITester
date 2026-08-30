"""CLI entry point.  Run from the project root:

    python cli.py PROJ-1234 [--refresh] [--ac-field-id customfield_10068] [--json]

Exit codes: 0 = ok, 1 = plan produced but validation_failed / fetch_failed, 2 = bad input/config.
"""
from __future__ import annotations

import argparse
import json
import sys

from navigation.orchestrator import run
from tools._config import ConfigError, load_settings
from tools._util import InputError


def _human(out: dict) -> None:
    s = out["summary"]
    print(f"\n[{out['status'].upper()}] {out['issue_key']}")
    print(f"  plan:   {out['artifacts']['test_plan_md']}")
    if out["artifacts"].get("plan_model_json"):
        print(f"  json:   {out['artifacts']['plan_model_json']}")
    print(f"  audit:  {out['artifacts'].get('raw_audit_json')}")
    print(f"  gaps: {s['gaps']}  scenarios: P0={s['p0']} P1={s['p1']} P2={s['p2']}  "
          f"open questions: {s['open_questions']}")
    print(f"  AC source: {s['ac_source']}   LLM calls: {s['llm_calls']}   "
          f"redactions: {s['redactions']}   cached tokens: {s.get('cached_tokens', 0)}")
    for w in s.get("warnings", []):
        print(f"  ! warning [{w['code']}] {w['detail']}")
    for e in out["errors"]:
        print(f"  x {e['stage']}: {e['message']}")
    print("\n  This is a DRAFT. A human QA owner must review section 7 before sign-off.\n")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="test-plan-agent",
                                description="Generate a DRAFT test plan from a Jira issue key.")
    p.add_argument("issue_key", help="e.g. PROJ-1234")
    p.add_argument("--refresh", action="store_true", help="bypass the raw fetch cache")
    p.add_argument("--ac-field-id", default=None, help="override the Acceptance Criteria custom field id")
    p.add_argument("--json", action="store_true", help="print only the AgentOutput JSON")
    args = p.parse_args(argv)

    try:
        settings = load_settings()
    except ConfigError as e:
        print(f"config error: {e}", file=sys.stderr)
        return 2

    try:
        out = run(
            {"issue_key": args.issue_key, "refresh": args.refresh, "ac_field_id": args.ac_field_id},
            settings,
        )
    except InputError as e:
        print(f"input error: {e}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(out, indent=2))
    else:
        _human(out)
    return 0 if out["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
