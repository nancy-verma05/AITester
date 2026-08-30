import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FIX = Path(__file__).parent / "fixtures"


def _load(name):
    return json.loads((FIX / name).read_text(encoding="utf-8"))


@pytest.fixture
def raw_bundle_min():
    return _load("raw_bundle_min.json")


@pytest.fixture
def issue_context_min():
    return _load("issue_context_min.json")


@pytest.fixture
def plan_model_valid():
    return _load("plan_model_valid.json")
