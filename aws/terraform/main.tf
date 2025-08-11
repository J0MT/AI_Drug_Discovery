# AI Drug Discovery AWS Infrastructure - SSM training with MLflow

# ==============================================================================
# PROVIDER CONFIGURATION
# ==============================================================================

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# ==============================================================================
# VARIABLES
# ==============================================================================
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "eu-north-1"
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.large"
}

variable "key_pair_name" {
  description = "Name of AWS key pair for EC2 access"
  type        = string
}

variable "your_ip" {
  description = "Your IP address for security group access"
  type        = string
}

variable "s3_bucket_name" {
  description = "S3 bucket name for DVC storage"
  type        = string
}

variable "github_repo" {
  description = "GitHub repository owner (for container registry)"
  type        = string
  default     = "J0MT"
}

variable "github_repository" {
  description = "GitHub repository name (owner/repo)"
  type        = string
}

# ==============================================================================
# DATA SOURCES
# ==============================================================================

# Get current AWS account ID and region
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Existing S3 bucket for DVC storage
data "aws_s3_bucket" "existing_dvc_storage" {
  bucket = var.s3_bucket_name
}

# Reference to manually created SSM parameter (Terraform never sees the value)
data "aws_ssm_parameter" "ghcr_token" {
  name = "ghcr-ro-token"
}

# ==============================================================================
# IAM ROLES AND POLICIES
# ==============================================================================

# =====EC2 instance role (for SSM and S3 access)=====
resource "aws_iam_role" "ec2_role" {
  name = "ai-drug-discovery-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })
}

# Enable SSM Run Command access (core permissions)
resource "aws_iam_role_policy_attachment" "ec2_ssm_policy" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# S3 access(model artefact & DVC bucket) and SSM parameter read access policy
resource "aws_iam_role_policy" "ec2_custom_policy" {
  name = "ai-drug-discovery-custom-policy"
  role = aws_iam_role.ec2_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          data.aws_s3_bucket.existing_dvc_storage.arn,
          "${data.aws_s3_bucket.existing_dvc_storage.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter"
        ]
        Resource = data.aws_ssm_parameter.ghcr_token.arn
      }
    ]
  })
}


# EC2 instance profile (attach role to instance) 
resource "aws_iam_instance_profile" "ec2_profile" {
  name = "ai-drug-discovery-ec2-profile"
  role = aws_iam_role.ec2_role.name
}

# ==============================================================================
# GITHUB OIDC CONFIGURATION
# ==============================================================================

# OIDC provider for GitHub Actions authentication
# Registers GitHub’s OIDC issuer with AWS so STS can verify GitHub’s signed tokens
resource "aws_iam_openid_connect_provider" "github_actions" {
  url = "https://token.actions.githubusercontent.com"

  client_id_list = [
    "sts.amazonaws.com",
  ]

  thumbprint_list = [
    "6938fd4d98bab03faadb97b34396831e3780aea1",
    "1c58a3a8518e8759bf075b76b750d4f2df264fcd"
  ]

  tags = {
    Name = "github-actions-oidc"
  }
}

# ROLE ==== GitHub Actions role with repository restriction
resource "aws_iam_role" "github_actions_role" {
  name = "github-actions-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = aws_iam_openid_connect_provider.github_actions.arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          }
          StringLike = {
            "token.actions.githubusercontent.com:sub" = "repo:${var.github_repository}:*"
          }
        }
      }
    ]
  })

  tags = {
    Name = "github-actions-role"
  }
}

# POLICY ==== SSM permissions for GitHub Actions
resource "aws_iam_role_policy" "github_actions_policy" {
  name = "github-actions-policy"
  role = aws_iam_role.github_actions_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ssm:SendCommand",
          "ssm:GetCommandInvocation",
          "ssm:DescribeInstanceInformation",
          "ssm:ListCommandInvocations"
        ]
        Resource = [
          "arn:aws:ssm:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:document/AWS-RunShellScript",
          "arn:aws:ec2:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:instance/${aws_instance.training_instance.id}"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:DescribeInstances",
          "ssm:ListCommands"
        ]
        Resource = "*"
      }
    ]
  })
}

# ==============================================================================
# NETWORKING
# ==============================================================================

# Network security group
resource "aws_security_group" "training_sg" {
  name        = "ai-drug-discovery-training-sg"
  description = "Security group for AI drug discovery training instance"

  # MLflow UI access from your IP
  ingress {
    from_port   = 5000
    to_port     = 5000
    protocol    = "tcp"
    cidr_blocks = ["${var.your_ip}/32"]
    description = "MLflow UI access"
  }

  # Internet access for package downloads
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound traffic"
  }

  tags = {
    Name = "ai-drug-discovery-training-sg"
  }
}

# ==============================================================================
# COMPUTE RESOURCES
# ==============================================================================

# Instance configuration
locals {
  ubuntu_ami_id = "ami-0989fb15ce71ba39e"  # Ubuntu 22.04 LTS eu-north-1
  user_data = base64encode(templatefile("${path.module}/../ec2-setup.sh", {
    s3_bucket = var.s3_bucket_name
    github_repo = var.github_repo
  }))
}

# Training instance
resource "aws_instance" "training_instance" {
  ami                    = local.ubuntu_ami_id
  instance_type          = var.instance_type
  key_name              = var.key_pair_name
  vpc_security_group_ids = [aws_security_group.training_sg.id]
  iam_instance_profile   = aws_iam_instance_profile.ec2_profile.name

  # Persistent storage for MLflow database
  root_block_device {
    volume_type = "gp3"
    volume_size = 50
    encrypted   = true
  }

  user_data = local.user_data

  tags = {
    Name = "ai-drug-discovery-training"
    Environment = "production"
    Project = "ai-drug-discovery"
  }
}

# ==============================================================================
# SECURE PARAMETER STORAGE
# ==============================================================================

# SSM parameter is created manually (outside Terraform) to keep the token value secure:
# aws ssm put-parameter --name 'ghcr-ro-token' --value 'YOUR_GITHUB_TOKEN' --type 'SecureString' --description 'GitHub Container Registry read-only token' --region eu-north-1
# 
# Terraform references this parameter via data source but never sees the actual token value.
# EC2 instances fetch the token at runtime using their IAM role permissions.

# ==============================================================================
# OUTPUTS
# ==============================================================================

# Infrastructure outputs
output "instance_id" {
  description = "ID of the EC2 instance"
  value       = aws_instance.training_instance.id
}

output "instance_public_ip" {
  description = "Public IP address of the EC2 instance"
  value       = aws_instance.training_instance.public_ip
}

output "instance_public_dns" {
  description = "Public DNS name of the EC2 instance"
  value       = aws_instance.training_instance.public_dns
}

output "s3_bucket_name" {
  description = "Name of the S3 bucket for DVC storage"
  value       = data.aws_s3_bucket.existing_dvc_storage.bucket
}

output "mlflow_url" {
  description = "MLflow web UI URL"
  value       = "http://${aws_instance.training_instance.public_ip}:5000"
}

# ==============================================================================
# DEPLOYMENT CONFIGURATION
# ==============================================================================

# Required GitHub repository secrets
output "github_secrets_required" {
  description = "Configure these secrets in your GitHub repository"
  value = {
    AWS_GITHUB_OIDC_ROLE    = aws_iam_role.github_actions_role.arn
    AWS_EC2_INSTANCE_ID     = aws_instance.training_instance.id
    GHCR_TOKEN              = "GitHub Personal Access Token (read:packages)"
  }
}

# Command to update SSM parameter with real token
output "ssm_parameter_update_command" {
  description = "Update SSM parameter with your GitHub token"
  value = "aws ssm put-parameter --name 'ghcr-ro-token' --value 'YOUR_GITHUB_TOKEN' --type 'SecureString' --overwrite --region ${var.aws_region}"
}