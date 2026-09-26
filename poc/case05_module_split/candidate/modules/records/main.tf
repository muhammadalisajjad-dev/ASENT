# The baseline protected asset is split into two buckets inside the module.
# Only the primary bucket keeps the protected asset configuration.

resource "aws_s3_bucket" "primary" {
  bucket = "customer-data"
  tags = {
    DataClass = "customer"
    Owner     = "app-team"
  }
}

resource "aws_s3_bucket" "replica" {
  bucket = "customer-data-replica"
  tags = {
    DataClass = "customer"
    Owner     = "app-team"
    Role      = "replica"
  }
}

output "bucket_arn" {
  value = aws_s3_bucket.primary.arn
}

output "bucket_name" {
  value = aws_s3_bucket.primary.bucket
}
