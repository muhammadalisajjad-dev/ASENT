# Candidate: the protected asset survives as customer_data_v2, but the
# least-privilege boundary has been re-bound to an unrelated asset.  The
# candidate policy still "looks valid" locally - it just governs the wrong
# logical asset.

resource "aws_s3_bucket" "customer_data_v2" {
  bucket = "customer-data"
  tags = {
    DataClass = "customer"
    Owner     = "app-team"
  }
}

resource "aws_s3_bucket" "analytics_dump" {
  bucket = "analytics-dump"
  tags = {
    DataClass = "analytics"
    Owner     = "data-team"
  }
}

data "aws_iam_policy_document" "app_rw" {
  statement {
    effect    = "Allow"
    actions   = ["s3:GetObject", "s3:PutObject"]
    resources = ["${aws_s3_bucket.analytics_dump.arn}/*"]
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
