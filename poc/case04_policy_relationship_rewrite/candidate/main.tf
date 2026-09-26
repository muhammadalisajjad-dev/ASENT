# Candidate: resource addresses change and the IAM policy relationship is
# rewritten (managed policy -> inline role policy).  The old resource names
# disappear; only structural/configuration evidence identifies the successor.

resource "aws_s3_bucket" "records_raw" {
  bucket = "customer-data"
  tags = {
    DataClass = "customer"
    Owner     = "app-team"
  }
}

data "aws_iam_policy_document" "records_rw" {
  statement {
    effect    = "Allow"
    actions   = ["s3:GetObject", "s3:PutObject"]
    resources = ["${aws_s3_bucket.records_raw.arn}/*"]
  }
}

resource "aws_iam_role_policy" "app_records_rw" {
  name   = "app-customer-data-rw"
  role   = aws_iam_role.app.name
  policy = data.aws_iam_policy_document.records_rw.json
}

resource "aws_iam_role" "app" {
  name = "app-role"
}

output "customer_data_bucket" {
  value = aws_s3_bucket.records_raw.bucket
}
