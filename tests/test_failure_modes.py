"""Regression tests for the correspondence failure modes (A-D).

Each test encodes one concrete way the identification stage used to go wrong:
identity/attribute shortcuts overriding the bounded structural evidence.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# A. moved target + materially stronger competing successor => UNKNOWN
# ---------------------------------------------------------------------------

CANDIDATE_A = """
# The moved block claims the asset became legacy_backup while configuration
# and reference evidence point at customer_data_v2.

moved {
  from = aws_s3_bucket.customer_data
  to   = aws_s3_bucket.legacy_backup
}

resource "aws_s3_bucket" "legacy_backup" {
  bucket = "legacy-archive"
  tags = {
    DataClass = "cold"
    Owner     = "archive-team"
  }
}

resource "aws_s3_bucket" "customer_data_v2" {
  bucket = "customer-data"
  tags = {
    DataClass = "customer"
    Owner     = "app-team"
  }
}

output "customer_data_bucket" {
  value = aws_s3_bucket.customer_data_v2.bucket
}
"""


def test_a_moved_target_yields_unknown_against_stronger_structural_evidence(
    make_case, correspondence
):
    case = make_case(CANDIDATE_A)
    result = correspondence(case)

    assert result.status == "conflict"
    assert result.rule == "explicit_moved"
    assert result.selected is None
    assert not result.identified

    conflict = result.conflicts[0]
    assert conflict["source"] == "moved_block"
    assert conflict["selected_by_source"] == "aws_s3_bucket.legacy_backup"
    assert "aws_s3_bucket.customer_data_v2" in conflict["conflicting_candidates"]
    assert result.unknown_reasons

    # The moved target still carries its evidence; it is contradicted, not hidden.
    moved_target = next(h for h in result.hypotheses if h.address == "aws_s3_bucket.legacy_backup")
    assert moved_target.signal("moved").score == 1.0
    competitor = next(h for h in result.hypotheses if h.address == "aws_s3_bucket.customer_data_v2")
    assert competitor.signal("attributes").score == 1.0
    assert "aws_s3_bucket.customer_data_v2" in {
        entry["address"] for entry in result.as_dict()["competing_candidates"]
    }


def test_a2_legitimate_moved_target_is_still_accepted_when_evidence_agrees(
    make_case, correspondence
):
    candidate = """
moved {
  from = aws_s3_bucket.customer_data
  to   = aws_s3_bucket.customer_data_renamed
}

resource "aws_s3_bucket" "customer_data_renamed" {
  bucket = "customer-data"
  tags = {
    DataClass = "customer"
    Owner     = "app-team"
  }
}

output "customer_data_bucket" {
  value = aws_s3_bucket.customer_data_renamed.bucket
}
"""
    result = correspondence(make_case(candidate))
    assert result.status == "identified"
    assert result.rule == "explicit_moved"
    assert result.selected == "aws_s3_bucket.customer_data_renamed"


# ---------------------------------------------------------------------------
# B. same Terraform address + contradictory structural evidence => UNKNOWN
# ---------------------------------------------------------------------------

CANDIDATE_B = """
# The Terraform address is unchanged, but the configuration at that address
# was rewritten while the baseline configuration moved to another address.

resource "aws_s3_bucket" "customer_data" {
  bucket = "customer-data-rewritten"
  tags = {
    DataClass = "restricted"
    Owner     = "other-team"
  }
}

resource "aws_s3_bucket" "customer_data_v2" {
  bucket = "customer-data"
  tags = {
    DataClass = "customer"
    Owner     = "app-team"
  }
}

output "customer_data_bucket" {
  value = aws_s3_bucket.customer_data_v2.bucket
}
"""


def test_b_same_address_yields_unknown_against_contradictory_structural_evidence(
    make_case, correspondence
):
    result = correspondence(make_case(CANDIDATE_B))

    assert result.status == "conflict"
    assert result.rule == "address_identity"
    assert result.selected is None
    assert not result.identified

    conflict = result.conflicts[0]
    assert conflict["source"] == "address_identity"
    assert conflict["selected_by_source"] == "aws_s3_bucket.customer_data"
    assert "aws_s3_bucket.customer_data_v2" in conflict["conflicting_candidates"]
    assert result.unknown_reasons


def test_b2_same_address_is_accepted_when_configuration_agrees(make_case, correspondence):
    candidate = """
resource "aws_s3_bucket" "customer_data" {
  bucket = "customer-data"
  tags = {
    DataClass = "customer"
    Owner     = "app-team"
  }
}

output "customer_data_bucket" {
  value = aws_s3_bucket.customer_data.bucket
}
"""
    result = correspondence(make_case(candidate))
    assert result.status == "identified"
    assert result.rule == "address_identity"
    assert result.selected == "aws_s3_bucket.customer_data"


# ---------------------------------------------------------------------------
# C. high attribute similarity but conflicting correspondence evidence
#    => UNKNOWN unless the evidence genuinely establishes a unique successor
# ---------------------------------------------------------------------------

CANDIDATE_C = """
# Identical configuration, but parked in an unrelated module with no
# references; the structurally wired candidate changed its bucket name.

module "stash" {
  source = "./modules/stash"
}

resource "aws_s3_bucket" "customer_data_v2" {
  bucket = "customer-data-live"
  tags = {
    DataClass = "customer"
    Owner     = "app-team"
  }
}

output "customer_data_bucket" {
  value = aws_s3_bucket.customer_data_v2.bucket
}
"""

MODULE_STASH = """
resource "aws_s3_bucket" "customer_data" {
  bucket = "customer-data"
  tags = {
    DataClass = "customer"
    Owner     = "app-team"
  }
}
"""


def test_c_high_attribute_similarity_does_not_bypass_conflicting_evidence(
    make_case, correspondence
):
    case = make_case(CANDIDATE_C, modules={"modules/stash/storage.tf": MODULE_STASH})
    result = correspondence(case)

    # The shortcut candidate really does clear the prototype attribute threshold.
    shortcut = next(h for h in result.hypotheses if h.address.startswith("module.stash."))
    assert shortcut.signal("attributes").score >= 0.75

    assert result.status == "conflict"
    assert result.rule == "config_continuity"
    assert result.selected is None
    assert not result.identified
    assert result.conflicts[0]["source"] == "config_continuity"
    assert result.unknown_reasons


def test_c2_consistent_evidence_still_identifies_a_unique_successor(make_case, correspondence):
    candidate = """
resource "aws_s3_bucket" "customer_data_v2" {
  bucket = "customer-data"
  tags = {
    DataClass = "customer"
    Owner     = "app-team"
  }
}

output "customer_data_bucket" {
  value = aws_s3_bucket.customer_data_v2.bucket
}
"""
    result = correspondence(make_case(candidate))
    assert result.status == "identified"
    assert result.rule == "config_continuity"
    assert result.selected == "aws_s3_bucket.customer_data_v2"
    selected = next(h for h in result.hypotheses if h.address == result.selected)
    assert "attributes" in selected.structural_support
    assert any(
        signal_id != "attributes" for signal_id in selected.structural_support
    ), "configuration continuity must be corroborated by another structural signal"


def test_c3_attribute_match_without_structural_corroboration_is_unknown(
    make_case, correspondence
):
    # A perfect configuration match that no structural evidence corroborates
    # must not be accepted by the attribute threshold alone.
    candidate = """
module "stash" {
  source = "./modules/stash"
}
"""
    case = make_case(candidate, modules={"modules/stash/storage.tf": MODULE_STASH})
    result = correspondence(case)
    assert not result.identified
    assert result.status in ("insufficient", "ambiguous", "conflict")
    assert result.unknown_reasons


# ---------------------------------------------------------------------------
# D. similar names with different logical assets => never name-driven
# ---------------------------------------------------------------------------

CANDIDATE_D1 = """
module "hold" {
  source = "./modules/hold"
}
"""

MODULE_HOLD_NAME_ONLY = """
# Reuses the baseline resource name but describes a different logical asset.
resource "aws_s3_bucket" "customer_data" {
  bucket = "unrelated-storage"
  tags = {
    DataClass = "logs"
    Owner     = "platform-team"
  }
}
"""


def test_d1_identical_name_alone_never_establishes_succession(make_case, correspondence):
    case = make_case(
        CANDIDATE_D1, modules={"modules/hold/main.tf": MODULE_HOLD_NAME_ONLY}
    )
    result = correspondence(case)

    only = result.hypotheses[0]
    assert only.address == "module.hold.aws_s3_bucket.customer_data"
    assert only.signal("name_similarity").score == 1.0
    assert "never sufficient" in only.signal("name_similarity").detail

    assert not result.identified
    assert result.selected is None
    assert result.unknown_reasons


CANDIDATE_D2 = """
module "hold" {
  source = "./modules/hold"
}

resource "aws_s3_bucket" "customer_data_migrated" {
  bucket = "customer-data-migrated"
  tags = {
    DataClass = "customer"
    Owner     = "app-team"
  }
}

output "hold_bucket" {
  value = module.hold.bucket_name
}

output "migrated_bucket" {
  value = aws_s3_bucket.customer_data_migrated.bucket
}
"""

MODULE_HOLD = """
resource "aws_s3_bucket" "customer_data" {
  bucket = "customer-data-hold"
  tags = {
    DataClass = "customer"
    Owner     = "app-team"
  }
}

output "bucket_name" {
  value = aws_s3_bucket.customer_data.bucket
}
"""


def test_d2_comparable_similar_named_candidates_stay_unknown(make_case, correspondence):
    case = make_case(CANDIDATE_D2, modules={"modules/hold/main.tf": MODULE_HOLD})
    result = correspondence(case)

    hold = next(
        hypothesis for hypothesis in result.hypotheses
        if hypothesis.address == "module.hold.aws_s3_bucket.customer_data"
    )
    assert hold.signal("name_similarity").score == 1.0

    assert not result.identified
    assert result.selected is None
    assert result.status == "ambiguous"
    assert result.conflicts and result.conflicts[0]["source"] == "multi_signal_score"


def test_d3_name_weight_never_dominates_structural_weights():
    from sable.correspondence import STRUCTURAL_SIGNALS, WEIGHTS

    assert WEIGHTS["name_similarity"] == min(WEIGHTS.values())
    for signal_id in STRUCTURAL_SIGNALS:
        assert WEIGHTS[signal_id] > WEIGHTS["name_similarity"]
