terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "ap-south-1"
}

resource "aws_s3_bucket" "demo_bucket" {
  bucket = "terraguard-demo-bucket-nakul-2026"

  tags = {
  CostCenter = "ops-123"
  Environment = "demo"
  Project = "TerraGuard"
  Team = "platform-engineering"
}
}

resource "aws_s3_bucket_versioning" "demo_bucket_versioning" {
  bucket = aws_s3_bucket.demo_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_security_group" "demo_sg" {
  name        = "terraguard-demo-sg"
  description = "Demo security group for TerraGuard drift testing"

  ingress {
    description = "HTTPS from anywhere"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Project = "TerraGuard"
  }
}
# Resource 3: S3 Public Access Block (RISKY test)
resource "aws_s3_bucket_public_access_block" "demo_bucket_public_access" {
  bucket                  = aws_s3_bucket.demo_bucket.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Resource 4: CloudWatch Log Group (SAFE test)
resource "aws_cloudwatch_log_group" "demo_logs" {
  name              = "/terraguard/demo-logs"
  retention_in_days = 7

  tags = {
    Project = "TerraGuard"
  }
}

# Resource 5: SSM Parameter (LLM fallback test)
resource "aws_ssm_parameter" "demo_param" {
  name  = "/terraguard/demo-config"
  type  = "String"
  value = "original-value"

  tags = {
    Project = "TerraGuard"
  }
}

# Resource 6: EC2 Instance (instance_type auto-fix test)
# WARNING: t3.micro is free tier (750 hours/month first 12 months)
# Terminate after testing to avoid charges
resource "aws_instance" "demo_instance" {
  ami           = "ami-0f58b397bc5c1f2e8"
  instance_type = "t3.micro"

  tags = {
    Project = "TerraGuard"
    Name    = "terraguard-demo-instance"
  }
}