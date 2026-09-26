# Candidate: the logical asset survives (same bucket configuration), but the
# least-privilege boundary is widened: extra actions and all-bucket scope.

resource "aws_s3_bucket" "customer_data_store" {
  bucket = "customer-data"
  tags = {
    DataClass = "customer"
    Owner     = "app-team"
  }
}

data "aws_iam_policy_document" "app_store_rw" {
  statement {
    effect    = "Allow"
    actions   = ["s3:GetObject", "s3:PutObject", "s3:ListBucket", "s3:DeleteObject"]
    resources = ["arn:aws:s3:::*"]
  }
}

resource "aws_iam_policy" "app_store_rw" {
  name   = "app-customer-data-rw"
  policy = data.aws_iam_policy_document.app_store_rw.json
}

resource "aws_iam_role" "app" {
  name = "app-role"
}

resource "aws_iam_role_policy_attachment" "app_store_rw" {
  role       = aws_iam_role.app.name
  policy_arn = aws_iam_policy.app_store_rw.arn
}

output "customer_data_bucket" {
  value = aws_s3_bucket.customer_data_store.bucket
}
