"""Shared fixtures for the SABLE regression tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

POC_ROOT = ROOT / "poc"

# The trusted baseline used by the synthetic failure-mode fixtures.  It is the
# same least-privilege structure the POC fixtures use.
BASELINE_TF = """
resource "aws_s3_bucket" "customer_data" {
  bucket = "customer-data"
  tags = {
    DataClass = "customer"
    Owner     = "app-team"
  }
}

data "aws_iam_policy_document" "app_rw" {
  statement {
    effect    = "Allow"
    actions   = ["s3:GetObject", "s3:PutObject"]
    resources = ["${aws_s3_bucket.customer_data.arn}/*"]
  }
}

resource "aws_iam_policy" "app_rw" {
  name   = "app-customer-data-rw"
  policy = data.aws_iam_policy_document.app_rw.json
}

resource "aws_iam_role" "app" {
  name = "app-role"
}

resource "aws_iam_role_policy_attachment" "app_rw" {
  role       = aws_iam_role.app.name
  policy_arn = aws_iam_policy.app_rw.arn
}

output "customer_data_bucket" {
  value = aws_s3_bucket.customer_data.bucket
}
"""

OBLIGATION = {
    "obligation_id": "TEST-CUSTOMERDATA",
    "principal": "aws_iam_role.app",
    "actions": ["s3:GetObject", "s3:PutObject"],
    "protected_asset": "aws_s3_bucket.customer_data",
    "resource_scope": "arn:aws:s3:::customer-data/*",
}


def write_case(
    root: Path,
    candidate_tf: str,
    baseline_tf: str = BASELINE_TF,
    modules: dict | None = None,
    obligation: dict | None = None,
) -> Path:
    case = root / "case"
    (case / "baseline").mkdir(parents=True, exist_ok=True)
    (case / "candidate").mkdir(parents=True, exist_ok=True)
    (case / "baseline" / "main.tf").write_text(baseline_tf, encoding="utf-8")
    (case / "candidate" / "main.tf").write_text(candidate_tf, encoding="utf-8")
    for relative, content in (modules or {}).items():
        target = case / "candidate" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    (case / "obligation.json").write_text(
        json.dumps(obligation or OBLIGATION, indent=2), encoding="utf-8"
    )
    return case


def run_correspondence(case: Path):
    from shared.model import build_project
    from sable.correspondence import correspond
    from sable.obligation import bind_baseline, load_obligation
    from sable.policy import build_policy_model

    baseline_project = build_project(case / "baseline")
    candidate_project = build_project(case / "candidate")
    baseline_model = build_policy_model(baseline_project)
    candidate_model = build_policy_model(candidate_project)
    obligation = bind_baseline(baseline_project, load_obligation(case / "obligation.json"))
    return correspond(
        baseline_project,
        candidate_project,
        obligation,
        baseline_model,
        candidate_model,
        candidate_project.moved,
    )


@pytest.fixture
def make_case(tmp_path):
    def _make(candidate_tf, baseline_tf=BASELINE_TF, modules=None, name="case"):
        return write_case(tmp_path / name, candidate_tf, baseline_tf, modules)

    return _make


@pytest.fixture
def correspondence():
    return run_correspondence


@pytest.fixture
def poc_case():
    def _case(name: str) -> Path:
        path = POC_ROOT / name
        assert path.is_dir(), f"missing POC fixture {path}"
        return path

    return _case
