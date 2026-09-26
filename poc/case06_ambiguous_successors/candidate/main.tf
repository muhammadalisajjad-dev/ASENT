# Candidate: the baseline asset is split into two equally plausible
# successors.  Both carry the same configuration, both are policy targets for
# the same action set, and both are exported.  No defensible preference exists.

resource "aws_s3_bucket" "customer_data_hot" {
  bucket = "customer-data-hot"
  tags = {
    DataClass = "customer"
    Owner     = "app-team"
  }
}

resource "aws_s3_bucket" "customer_data_cold" {
  bucket = "customer-data-cold"
  tags = {
    DataClass = "customer"
    Owner     = "app-team"
  }
}

data "aws_iam_policy_document" "hot_rw" {
  statement {
    effect    = "Allow"
    actions   = ["s3:GetObject", "s3:PutObject"]
    resources = ["${aws_s3_bucket.customer_data_hot.arn}/*"]
  }
}

data "aws_iam_policy_document" "cold_rw" {
  statement {
    effect    = "Allow"
    actions   = ["s3:GetObject", "s3:PutObject"]
    resources = ["${aws_s3_bucket.customer_data_cold.arn}/*"]
  }
}

resource "aws_iam_policy" "hot_rw" {
  name   = "app-customer-data-hot-rw"
  policy = data.aws_iam_policy_document.hot_rw.json
}

resource "aws_iam_policy" "cold_rw" {
  name   = "app-customer-data-cold-rw"
  policy = data.aws_iam_policy_document.cold_rw.json
}

resource "aws_iam_role" "app" {
  name = "app-role"
}

resource "aws_iam_role_policy_attachment" "hot_rw" {
  role       = aws_iam_role.app.name
  policy_arn = aws_iam_policy.hot_rw.arn
}

resource "aws_iam_role_policy_attachment" "cold_rw" {
  role       = aws_iam_role.app.name
  policy_arn = aws_iam_policy.cold_rw.arn
}

output "hot_bucket" {
  value = aws_s3_bucket.customer_data_hot.bucket
}

output "cold_bucket" {
  value = aws_s3_bucket.customer_data_cold.bucket
}
