"""The Groq response_format schema must stay structurally in sync with the authoritative
full schema, and must obey Groq strict-mode restrictions."""
from tools._util import load_schema

FULL = load_schema("plan_model.schema.json")
GROQ = load_schema("plan_model.groq.schema.json")

_FORBIDDEN = {"pattern", "format", "const", "minItems", "maxItems", "minLength", "maxLength"}


def _walk(node, path="$"):
    if isinstance(node, dict):
        yield path, node
        for k, v in node.items():
            yield from _walk(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _walk(v, f"{path}[{i}]")


def test_groq_schema_has_no_forbidden_keywords():
    bad = [(p, k) for p, n in _walk(GROQ) if isinstance(n, dict) for k in n if k in _FORBIDDEN]
    assert not bad, bad


def test_groq_schema_objects_are_closed_and_fully_required():
    for path, n in _walk(GROQ):
        if isinstance(n, dict) and n.get("type") == "object":
            assert n.get("additionalProperties") is False, f"{path}: not closed"
            assert set(n.get("required", [])) == set(n.get("properties", {})), \
                f"{path}: required != properties (Groq strict needs every property required)"


def test_same_top_level_and_def_property_names():
    assert set(FULL["properties"]) == set(GROQ["properties"])
    assert set(FULL["$defs"]) == set(GROQ["$defs"])
    for d in FULL["$defs"]:
        assert set(FULL["$defs"][d]["properties"]) == set(GROQ["$defs"][d]["properties"]), d
