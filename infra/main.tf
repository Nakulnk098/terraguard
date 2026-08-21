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
# TODO(TerraGuard): RISKY drift on aws_security_group.demo_sg -- ingress changed -- see PR for details
