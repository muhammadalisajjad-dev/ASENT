"""Regression tests for the three authorization fixes in ``sable/authorize.py``.

1. covering the obligation scope by literal ARN never proves, by itself, that
   the boundary belongs to the identified successor;
2. module-qualified Terraform IAM role addresses resolve correctly;
3. bucket-policy principals that cannot be resolved locally stay unknown and
   are never treated as a positive match.

The tests drive the authorization stage directly (the fixes live there) and,
where the whole pipeline is meaningful, the end-to-end fixture flow.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def evaluate_candidate(case: Path, successor: str):
    """Run the authorization stage alone against a candidate configuration."""
    from shared.model import build_project
    from sable.authorize import evaluate
    from sable.obligation import bind_baseline, load_obligation
    from sable.policy import build_policy_model

    baseline_project = build_project(case / "baseline")
    candidate_project = build_project(case / "candidate")
    obligation = bind_baseline(baseline_project, load_obligation(case / "obligation.json"))
    model = build_policy_model(candidate_project)
    return evaluate(candidate_project, model, obligation, successor)


def check_of(result, check_id: str):
    return next(check for check in result.checks if check.id == check_id)


# ---------------------------------------------------------------------------
# 1. literal ARN coverage must not prove successor identity
# ---------------------------------------------------------------------------

# The boundary still grants exactly the obligation actions on exactly the
# obligation scope - but only as a literal ARN belonging to the old bucket
# name.  The identified successor is a different bucket, so the boundary is
# not attached to it.
CANDIDATE_LITERAL_ARN_WRONG_ASSET = """
resource "aws_s3_bucket" "customer_archive" {
  bucket = "customer-archive"
  tags = {
    DataClass = "customer"
    Owner     = "app-team"
  }
}

data "aws_iam_policy_document" "app_rw" {
  statement {
    effect    = "Allow"
    actions   = ["s3:GetObject", "s3:PutObject"]
    resources = ["arn:aws:s3:::customer-data/*"]
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
  value = aws_s3_bucket.customer_archive.bucket
}
"""


def test_literal_arn_coverage_does_not_prove_the_binding(make_case):
    from sable.verify import verify_fixture

    case = make_case(CANDIDATE_LITERAL_ARN_WRONG_ASSET)
    result = evaluate_candidate(case, "aws_s3_bucket.customer_archive")

    binding = check_of(result, "successor_binding")
    assert binding.status == "fail", (
        "literal ARN coverage of the obligation scope must not, by itself, "
        f"prove the successor binding (got {binding.status}: {binding.detail})"
    )
    assert "arn:aws:s3:::customer-data/*" in (binding.actual or "")
    assert "customer-archive" not in (binding.actual or "")
    assert result.status == "violated"
    assert result.failed

    # The obligation scope is still granted and no scope/action widening was
    # introduced: only the successor binding is at stake here.
    assert check_of(result, "action_coverage").status == "pass"
    assert check_of(result, "scope_widening").status == "pass"
    assert check_of(result, "action_widening").status == "pass"

    # End to end: this configuration can never be reported as preserved.
    assert verify_fixture(case).decision != "PRESERVED"


# Positive control: the same literal ARN is accepted once it is tied to the
# successor's own literal bucket name.
CANDIDATE_LITERAL_ARN_TIED_TO_SUCCESSOR = """
resource "aws_s3_bucket" "records_raw" {
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
    resources = ["arn:aws:s3:::customer-data/*"]
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
  value = aws_s3_bucket.records_raw.bucket
}
"""


def test_literal_arn_tied_to_the_successor_bucket_name_still_binds(make_case):
    case = make_case(CANDIDATE_LITERAL_ARN_TIED_TO_SUCCESSOR)
    result = evaluate_candidate(case, "aws_s3_bucket.records_raw")

    binding = check_of(result, "successor_binding")
    assert binding.status == "pass"
    assert binding.actual == "literal ARN tied to the successor"
    assert "arn:aws:s3:::customer-data" in binding.detail
    assert result.status == "satisfied"


# The successor bucket name itself is not literal, so a literal ARN can be
# covered by the obligation scope without being attributable to the successor.
CANDIDATE_LITERAL_ARN_UNRESOLVABLE = """
variable "bucket_name" {
  type = string
}

resource "aws_s3_bucket" "customer_data_v2" {
  bucket = var.bucket_name
  tags = {
    DataClass = "customer"
    Owner     = "app-team"
  }
}

data "aws_iam_policy_document" "app_rw" {
  statement {
    effect    = "Allow"
    actions   = ["s3:GetObject", "s3:PutObject"]
    resources = ["arn:aws:s3:::customer-data/*"]
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
"""


def test_literal_arn_scope_is_indeterminate_when_successor_name_is_not_literal(
    make_case,
):
    case = make_case(CANDIDATE_LITERAL_ARN_UNRESOLVABLE)
    result = evaluate_candidate(case, "aws_s3_bucket.customer_data_v2")

    binding = check_of(result, "successor_binding")
    assert binding.status == "unknown"
    assert "not a literal" in binding.detail
    assert result.status == "indeterminate"
    assert not result.failed


# ---------------------------------------------------------------------------
# 2. module-qualified Terraform IAM role addresses
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "address,expected",
    [
        ("aws_iam_role.app", ("resource", "aws_iam_role", "app")),
        ("aws_iam_role.app[0]", ("resource", "aws_iam_role", "app")),
        ("module.identity.aws_iam_role.app", ("resource", "aws_iam_role", "app")),
        (
            "module.parent.module.child.aws_iam_role.app",
            ("resource", "aws_iam_role", "app"),
        ),
        (
            "module.m[0].aws_iam_role.app[1]",
            ("resource", "aws_iam_role", "app"),
        ),
        (
            "data.aws_iam_policy_document.doc",
            ("data", "aws_iam_policy_document", "doc"),
        ),
        (
            "module.identity.data.aws_iam_policy_document.doc",
            ("data", "aws_iam_policy_document", "doc"),
        ),
        ("aws_iam_role", ("unsupported", None, None)),
        ("module.identity", ("unsupported", None, None)),
        ("module.identity.aws_iam_role", ("unsupported", None, None)),
    ],
)
def test_split_address_reads_the_resource_type_from_the_address_suffix(
    address, expected
):
    from sable.authorize import split_address

    assert split_address(address) == expected


IDENTITY_MODULE = """
resource "aws_iam_role" "app" {
  name = "app-role"
}

output "role_name" {
  value = aws_iam_role.app.name
}
"""


def _module_main_tf(module_label: str) -> str:
    return f"""
module "{module_label}" {{
  source = "./modules/identity"
}}

resource "aws_s3_bucket" "customer_data" {{
  bucket = "customer-data"
  tags = {{
    DataClass = "customer"
    Owner     = "app-team"
  }}
}}

data "aws_iam_policy_document" "app_rw" {{
  statement {{
    effect    = "Allow"
    actions   = ["s3:GetObject", "s3:PutObject"]
    resources = ["${{aws_s3_bucket.customer_data.arn}}/*"]
  }}
}}

resource "aws_iam_policy" "app_rw" {{
  name   = "app-customer-data-rw"
  policy = data.aws_iam_policy_document.app_rw.json
}}

resource "aws_iam_role_policy_attachment" "app_rw" {{
  role       = module.{module_label}.role_name
  policy_arn = aws_iam_policy.app_rw.arn
}}

output "customer_data_bucket" {{
  value = aws_s3_bucket.customer_data.bucket
}}
"""


def _write_module_principal_case(tmp_path: Path, candidate_module: str) -> Path:
    """Baseline/candidate pair whose IAM principal lives in a local module.

    The baseline always declares ``module "identity"``; the candidate declares
    its identity module under ``candidate_module``.  When the two labels differ
    the obligation principal address is absent from the candidate and can only
    be resolved through the IAM name.
    """
    case = tmp_path / "module_case"
    for side in ("baseline", "candidate"):
        (case / side / "modules" / "identity").mkdir(parents=True)
        (case / side / "modules" / "identity" / "main.tf").write_text(
            IDENTITY_MODULE, encoding="utf-8"
        )
    (case / "baseline" / "main.tf").write_text(
        _module_main_tf("identity"), encoding="utf-8"
    )
    (case / "candidate" / "main.tf").write_text(
        _module_main_tf(candidate_module), encoding="utf-8"
    )
    (case / "obligation.json").write_text(
        json.dumps(
            {
                "obligation_id": "S3-APPROLE-CUSTOMERDATA",
                "principal": "module.identity.aws_iam_role.app",
                "actions": ["s3:GetObject", "s3:PutObject"],
                "protected_asset": "aws_s3_bucket.customer_data",
                "resource_scope": "arn:aws:s3:::customer-data/*",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return case


def test_module_qualified_principal_address_resolves_by_iam_name(tmp_path):
    case = _write_module_principal_case(tmp_path, "app_identity")
    result = evaluate_candidate(case, "aws_s3_bucket.customer_data")

    # The obligation address is absent from the candidate; resolution falls
    # back to the IAM name using the resource type parsed from the *suffix*
    # of the module-qualified address (never from its first segment).
    assert result.principal == "module.app_identity.aws_iam_role.app"
    assert result.principal_resolution == "name"
    assert check_of(result, "principal_present").status == "pass"
    assert any(
        "resolved by IAM name 'app-role'" in note
        and "type aws_iam_role" in note
        for note in result.notes
    )
    assert result.status == "satisfied"


def test_module_qualified_principal_in_the_baseline_binds_its_name(tmp_path):
    case = _write_module_principal_case(tmp_path, "identity")
    result = evaluate_candidate(case, "aws_s3_bucket.customer_data")

    # Same-address resolution still works for the module-qualified form.
    assert result.principal == "module.identity.aws_iam_role.app"
    assert result.principal_resolution == "address"
    assert result.status == "satisfied"


# ---------------------------------------------------------------------------
# 3. unresolved bucket-policy principals are never a positive match
# ---------------------------------------------------------------------------


def _bucket_provider(principals):
    from sable.policy import Provider, Statement

    statement = Statement(
        source="aws_s3_bucket_policy.records_lock",
        effect="Deny",
        actions=("s3:GetObject",),
        resource_values=("arn:aws:s3:::customer-data/*",),
        principals=principals,
    )
    return Provider(
        address="aws_s3_bucket_policy.records_lock",
        kind="bucket",
        statements=(statement,),
        inline_principal="aws_s3_bucket.customer_data",
    )


@pytest.mark.parametrize("principals", [None, ()])
def test_bucket_policy_with_unreadable_principal_is_never_a_match(principals):
    from sable.authorize import _bucket_policy_matches

    assert _bucket_policy_matches(_bucket_provider(principals), "app-role") is None


@pytest.mark.parametrize(
    "principals",
    [
        ("arn:aws:iam::111122223333:role/app-role",),
        ("arn:aws:iam::111122223333:role/deploy/app-role",),
        ("*",),
    ],
)
def test_bucket_policy_with_explicit_principal_matches(principals):
    from sable.authorize import _bucket_policy_matches

    assert _bucket_policy_matches(_bucket_provider(principals), "app-role") is True


@pytest.mark.parametrize(
    "principals",
    [
        ("arn:aws:iam::111122223333:role/unrelated-role",),
        ("other-role",),
    ],
)
def test_bucket_policy_for_another_principal_does_not_match(principals):
    from sable.authorize import _bucket_policy_matches

    assert _bucket_policy_matches(_bucket_provider(principals), "app-role") is False


def test_bucket_policy_without_an_unresolved_principal_identity_is_unknown():
    from sable.authorize import _bucket_policy_matches

    provider = _bucket_provider(("arn:aws:iam::111122223333:role/app-role",))
    provider = type(provider)(
        address=provider.address,
        kind=provider.kind,
        statements=provider.statements,
        inline_principal=provider.inline_principal,
        resolved=False,
    )
    assert _bucket_policy_matches(provider, "app-role") is None
    # An obligation principal that itself could not be identified cannot be
    # matched against any bucket policy statement.
    assert _bucket_policy_matches(_bucket_provider(("*",)), None) is None


BUCKET_POLICY_CANDIDATE = """
moved {{
  from = aws_s3_bucket.customer_data
  to   = aws_s3_bucket.app_customer_records
}}

resource "aws_s3_bucket" "app_customer_records" {{
  bucket = "customer-data"
  tags = {{
    DataClass = "customer"
    Owner     = "app-team"
  }}
}}

data "aws_iam_policy_document" "app_records_rw" {{
  statement {{
    effect    = "Allow"
    actions   = ["s3:GetObject", "s3:PutObject"]
    resources = ["${{aws_s3_bucket.app_customer_records.arn}}/*"]
  }}
}}

resource "aws_iam_policy" "app_records_rw" {{
  name   = "app-customer-data-rw"
  policy = data.aws_iam_policy_document.app_records_rw.json
}}

resource "aws_iam_role" "app" {{
  name = "app-role"
}}

resource "aws_iam_role_policy_attachment" "app_rw" {{
  role       = aws_iam_role.app.name
  policy_arn = aws_iam_policy.app_records_rw.arn
}}

data "aws_iam_policy_document" "bucket_lock" {{
  statement {{
    effect    = "Deny"
    actions   = ["s3:GetObject"]
    resources = ["${{aws_s3_bucket.app_customer_records.arn}}/*"]
    {principals}
  }}
}}

resource "aws_s3_bucket_policy" "records_lock" {{
  bucket = aws_s3_bucket.app_customer_records.id
  policy = data.aws_iam_policy_document.bucket_lock.json
}}

output "customer_data_bucket" {{
  value = aws_s3_bucket.app_customer_records.bucket
}}
"""


def _principals_block(identifier: str | None) -> str:
    """A Terraform ``principals`` block, or nothing when there is none."""
    if identifier is None:
        return ""
    return (
        "principals {\n"
        '      type        = "AWS"\n'
        f"      identifiers = [{identifier}]\n"
        "    }"
    )


UNRESOLVED_PRINCIPALS = [
    # no Principal at all: the statement cannot be attributed locally
    _principals_block(None),
    # Principal built from a reference: not resolvable to an identifier here
    _principals_block("aws_iam_role.app.arn"),
]

RESOLVED_PRINCIPALS = {
    "ours": _principals_block('"arn:aws:iam::111122223333:role/app-role"'),
    "other": _principals_block('"arn:aws:iam::111122223333:role/unrelated-role"'),
}


@pytest.mark.parametrize("principals", UNRESOLVED_PRINCIPALS)
def test_unresolved_bucket_policy_principal_is_unknown_evidence(make_case, principals):
    from sable.verify import verify_fixture

    case = make_case(BUCKET_POLICY_CANDIDATE.format(principals=principals))
    result = verify_fixture(case)

    assert result.correspondence.identified, result.decision_reasons
    authorization = result.authorization
    assert authorization.status == "indeterminate"

    interpretability = check_of(authorization, "policy_interpretability")
    assert interpretability.status == "unknown"
    assert "bucket policy" in interpretability.actual
    assert any("unresolved" in note for note in authorization.notes)

    # The unreadable statement was not adopted as evidence about the
    # principal: it is neither an extra grant nor a hidden deny.
    providers = {statement["provider"] for statement in authorization.as_dict()["statements"]}
    assert "aws_s3_bucket_policy.records_lock" not in providers
    assert check_of(authorization, "deny_conflict").status == "pass"

    # ...and the fixture is therefore not reported as preserved.
    assert result.decision == "UNKNOWN"


def test_bucket_policy_denying_the_obligation_principal_is_a_violation(make_case):
    from sable.verify import verify_fixture

    case = make_case(BUCKET_POLICY_CANDIDATE.format(principals=RESOLVED_PRINCIPALS["ours"]))
    result = verify_fixture(case)

    assert result.correspondence.identified, result.decision_reasons
    assert result.authorization.status == "violated"
    deny = check_of(result.authorization, "deny_conflict")
    assert deny.status == "fail"
    assert "s3:GetObject denied by aws_s3_bucket_policy.records_lock" in deny.actual
    assert result.decision == "REGRESSED"


def test_bucket_policy_for_another_principal_does_not_affect_the_obligation(make_case):
    from sable.verify import verify_fixture

    case = make_case(BUCKET_POLICY_CANDIDATE.format(principals=RESOLVED_PRINCIPALS["other"]))
    result = verify_fixture(case)

    assert result.correspondence.identified, result.decision_reasons
    assert result.authorization.status == "satisfied"
    assert check_of(result.authorization, "policy_interpretability").status == "pass"
    assert result.decision == "PRESERVED"
