from shared.values import parse_value, normalize, flatten, literal_string, iter_refs, ref_address, ref_kind

cases = [
    '"customer-data"',
    '"${aws_s3_bucket.customer_data.arn}/*"',
    "aws_s3_bucket.customer_data.arn",
    '["s3:GetObject", "s3:PutObject"]',
    '{ DataClass = "customer", Owner = "app-team" }',
    'jsonencode({ Effect = "Allow", Action = ["s3:GetObject"] })',
    "module.records.bucket_arn",
    "var.name",
    '"${var.prefix}-data"',
    'aws_s3_bucket.split[0].arn',
]
for raw in cases:
    v = parse_value(raw)
    print(repr(raw))
    print("   norm  :", normalize(v))
    print("   leaf  :", flatten(v))
    print("   refs  :", [r.path for r in iter_refs(v)])
    print("   literal:", literal_string(v))

v = parse_value('"${aws_s3_bucket.a.arn}/*"')
print("addr:", ref_address(("aws_s3_bucket", "a", "arn"), ()))
print("kind:", ref_kind(("aws_s3_bucket", "a", "arn")))
print("addr var:", ref_address(("var", "x"), ("m",)))
print("addr data:", ref_address(("data", "aws_iam_policy_document", "d", "json"), ()))
