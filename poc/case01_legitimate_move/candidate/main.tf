# Candidate: structural refactor with an explicit Terraform move.
# Resource address changes; the logical asset and its boundary do not.

moved {
  from = aws_s3_bucket.customer_data
  to   = aws_s3_bucket.app_customer_records
}

resource "aws_s3_bucket" "app_customer_records" {
  bucket = "customer-data"
  tags = {
    DataClass = "customer"
    Owner     = "app-team"
  }
}

data "aws_iam_policy_document" "app_records_rw" {
  statement {
    effect    = "Allow"
    actions   = ["s3:GetObject", "s3:PutObject"]
    resources = ["${aws_s3_bucket.app_customer_records.arn}/*"]
  }
}

resource "aws_iam_policy" "app_records_rw" {
  name   = "app-customer-data-rw"
  policy = data.aws_iam_policy_document.app_records_rw.json
}

resource "aws_iam_role" "app" {
  name = "app-role"
}

resource "aws_iam_role_policy_attachment" "app_records_rw" {
  role       = aws_iam_role.app.name
  policy_arn = aws_iam_policy.app_records_rw.arn
}

output "customer_data_bucket" {
  value = aws_s3_bucket.app_customer_records.bucket
}
