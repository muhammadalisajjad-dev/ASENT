# Candidate: multiple S3 assets with similar names and similar-looking
# policies.  One candidate even reuses the baseline resource name inside a
# module.  Name similarity alone must not select a successor.

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

data "aws_iam_policy_document" "hold_rw" {
  statement {
    effect    = "Allow"
    actions   = ["s3:GetObject", "s3:PutObject"]
    resources = ["${module.hold.bucket_arn}/*"]
  }
}

data "aws_iam_policy_document" "migrated_rw" {
  statement {
    effect    = "Allow"
    actions   = ["s3:GetObject", "s3:PutObject"]
    resources = ["${aws_s3_bucket.customer_data_migrated.arn}/*"]
  }
}

resource "aws_iam_policy" "hold_rw" {
  name   = "app-customer-data-hold-rw"
  policy = data.aws_iam_policy_document.hold_rw.json
}

resource "aws_iam_policy" "migrated_rw" {
  name   = "app-customer-data-migrated-rw"
  policy = data.aws_iam_policy_document.migrated_rw.json
}

resource "aws_iam_role" "app" {
  name = "app-role"
}

resource "aws_iam_role_policy_attachment" "hold_rw" {
  role       = aws_iam_role.app.name
  policy_arn = aws_iam_policy.hold_rw.arn
}

resource "aws_iam_role_policy_attachment" "migrated_rw" {
  role       = aws_iam_role.app.name
  policy_arn = aws_iam_policy.migrated_rw.arn
}

output "hold_bucket" {
  value = module.hold.bucket_name
}

output "migrated_bucket" {
  value = aws_s3_bucket.customer_data_migrated.bucket
}
