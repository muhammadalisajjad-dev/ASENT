from shared.hcl import parse_string, Block, Attribute

SRC = """
# comment
resource "aws_s3_bucket" "customer_data" {
  bucket = "customer-data"
  tags = {
    DataClass = "customer"
  }
  lifecycle {
    prevent_destroy = true
  }
}

moved {
  from = aws_s3_bucket.customer_data
  to   = aws_s3_bucket.renamed
}

data "aws_iam_policy_document" "d" {
  statement {
    effect    = "Allow"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.customer_data.arn}/*"]
  }
}

my-attr = 1
output "o" { value = module.records.bucket_arn }
"""

items = parse_string(SRC, "test.tf")
for it in items:
    if isinstance(it, Block):
        print("BLOCK", it.type, it.labels, "line", it.position.line)
        for sub in it.body:
            if isinstance(sub, Attribute):
                print("   attr", repr(sub.name), "=", repr(sub.raw))
            else:
                print("   nested", sub.type, sub.labels)
    else:
        print("ATTR", it.name, "=", it.raw)

try:
    parse_string('resource "a" "b" {', "bad.tf")
except Exception as exc:
    print("ERROR OK:", type(exc).__name__, exc)
