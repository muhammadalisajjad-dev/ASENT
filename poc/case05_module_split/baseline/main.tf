# Trusted baseline: protected customer-data asset and its least-privilege
# IAM boundary for the application role.

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
