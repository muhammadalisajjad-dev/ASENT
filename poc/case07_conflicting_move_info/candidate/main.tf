# Candidate: explicit move information conflicts with structural and
# semantic evidence.  The moved block claims the asset became legacy_backup,
# while configuration, references and the policy target all point at
# customer_data_v2.

moved {
  from = aws_s3_bucket.customer_data
  to   = aws_s3_bucket.legacy_backup
}

resource "aws_s3_bucket" "legacy_backup" {
  bucket = "customer-legacy-backup"
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

data "aws_iam_policy_document" "app_rw" {
  statement {
    effect    = "Allow"
    actions   = ["s3:GetObject", "s3:PutObject"]
    resources = ["${aws_s3_bucket.customer_data_v2.arn}/*"]
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
  value = aws_s3_bucket.customer_data_v2.bucket
}
