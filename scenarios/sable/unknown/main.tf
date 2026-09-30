terraform { required_version = ">= 1.1" }
module "storage" { source = "./modules/storage" }
resource "aws_iam_role" "app" {
  name = "invoicehub-app"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Principal = { Service = "ecs-tasks.amazonaws.com" }, Action = "sts:AssumeRole" }] })
}
resource "aws_iam_role_policy" "invoice_access" {
  role = aws_iam_role.app.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = ["s3:GetObject", "s3:PutObject"], Resource = ["${module.storage.active_arn}/*"] }]
  })
}
