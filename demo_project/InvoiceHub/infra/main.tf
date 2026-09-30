terraform {
  required_version = ">= 1.1"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}
resource "aws_s3_bucket" "invoice_data" {
  bucket = "invoicehub-data-local-demo"
  tags = { Asset = "invoice-ledger", Stage = "active" }
}
resource "aws_iam_role" "app" {
  name = "invoicehub-app"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Principal = { Service = "ecs-tasks.amazonaws.com" }, Action = "sts:AssumeRole" }] })
}
resource "aws_iam_role_policy" "invoice_access" {
  role = aws_iam_role.app.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["s3:GetObject", "s3:PutObject"]
      Resource = ["${aws_s3_bucket.invoice_data.arn}/*"]
    }]
  })
}
output "invoice_bucket" { value = aws_s3_bucket.invoice_data.id }
