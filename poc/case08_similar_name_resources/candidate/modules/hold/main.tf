# Module scope: holds a bucket that reuses the baseline resource name.

resource "aws_s3_bucket" "customer_data" {
  bucket = "customer-data-hold"
  tags = {
    DataClass = "customer"
    Owner     = "app-team"
  }
}

output "bucket_arn" {
  value = aws_s3_bucket.customer_data.arn
}

output "bucket_name" {
  value = aws_s3_bucket.customer_data.bucket
}
