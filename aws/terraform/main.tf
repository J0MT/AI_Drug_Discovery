# =============================================================================
# TERRAFORM CONFIGURATION - AI Drug Discovery AWS Infrastructure
# =============================================================================

# 1. TERRAFORM SETUP - Specify required versions and providers
terraform {
  required_version = ">= 1.0"              # Minimum Terraform version
  required_providers {
    aws = {
      source  = "hashicorp/aws"             # Use official AWS provider
      version = "~> 5.0"                    # AWS provider version 5.x
    }
  }
}

# 2. AWS PROVIDER - Configure connection to AWS
provider "aws" {
  region = var.aws_region                   # Use region from variables
}

# =============================================================================
# VARIABLES - Input parameters from terraform.tfvars
# =============================================================================

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "eu-north-1"                # Default: Stockholm region
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.large"                  # Default: 2 vCPUs, 8GB RAM
}

variable "key_pair_name" {
  description = "Name of AWS key pair for EC2 access"
  type        = string                      # Required: SSH key for instance access
}

variable "your_ip" {
  description = "Your IP address for security group access"
  type        = string                      # Required: Only your IP can access services
}

variable "s3_bucket_name" {
  description = "S3 bucket name for DVC storage"
  type        = string                      # Required: Bucket for data version control
}

# =============================================================================
# DATA SOURCES - Reference existing AWS resources
# =============================================================================

# 3. REFERENCE EXISTING S3 BUCKET - For DVC data storage
data "aws_s3_bucket" "existing_dvc_storage" {
  bucket = var.s3_bucket_name               # Find existing bucket (don't create new one)
}

# =============================================================================
# IAM PERMISSIONS - Allow EC2 instance to access S3
# =============================================================================

# 4. IAM ROLE - Permissions identity for EC2 instance
resource "aws_iam_role" "ec2_role" {
  name = "ai-drug-discovery-ec2-role"

  # Trust policy - Allow EC2 service to assume this role
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"           # EC2 can assume this role
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"     # Only EC2 service can use this role
        }
      }
    ]
  })
}

# 5. IAM POLICY - Specific S3 permissions for the role
resource "aws_iam_role_policy" "ec2_s3_policy" {
  name = "ai-drug-discovery-s3-policy"
  role = aws_iam_role.ec2_role.id

  # Permissions policy - What the role can do
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",                   # Download files from S3
          "s3:PutObject",                   # Upload files to S3
          "s3:DeleteObject",                # Delete files from S3
          "s3:ListBucket"                   # List bucket contents
        ]
        Resource = [
          data.aws_s3_bucket.existing_dvc_storage.arn,        # Bucket itself
          "${data.aws_s3_bucket.existing_dvc_storage.arn}/*"  # All objects in bucket
        ]
      }
    ]
  })
}

# 6. INSTANCE PROFILE - Attach IAM role to EC2 instance
resource "aws_iam_instance_profile" "ec2_profile" {
  name = "ai-drug-discovery-ec2-profile"
  role = aws_iam_role.ec2_role.name         # Link role to instance profile
}

# =============================================================================
# SECURITY GROUP - Firewall rules for EC2 instance
# =============================================================================

# 7. SECURITY GROUP - Network access control (firewall)
resource "aws_security_group" "training_sg" {
  name        = "ai-drug-discovery-training-sg"
  description = "Security group for AI drug discovery training instance"

  # INBOUND RULES - What can connect TO the instance
  ingress {
    from_port   = 22                        # SSH port
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["${var.your_ip}/32"]     # Only YOUR IP can SSH
    description = "SSH access"
  }

  ingress {
    from_port   = 8080                      # Airflow web UI port
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["${var.your_ip}/32"]     # Only YOUR IP can access Airflow
    description = "Airflow web UI"
  }

  ingress {
    from_port   = 5000                      # MLflow web UI port
    to_port     = 5000
    protocol    = "tcp"
    cidr_blocks = ["${var.your_ip}/32"]     # Only YOUR IP can access MLflow
    description = "MLflow UI"
  }

  # OUTBOUND RULES - What the instance can connect TO
  egress {
    from_port   = 0                         # All ports
    to_port     = 0
    protocol    = "-1"                      # All protocols
    cidr_blocks = ["0.0.0.0/0"]            # Can connect anywhere (internet access)
    description = "All outbound traffic"
  }

  tags = {
    Name = "ai-drug-discovery-training-sg"
  }
}

# =============================================================================
# EC2 INSTANCE CONFIGURATION
# =============================================================================

# 8. AMI SELECTION - Choose Ubuntu server image
locals {
  ubuntu_ami_id = "ami-0989fb15ce71ba39e"   # Ubuntu 22.04 LTS for eu-north-1
}

# 9. USER DATA SCRIPT - Automatically run setup script on first boot
locals {
  user_data = base64encode(templatefile("${path.module}/../ec2-setup.sh", {
    s3_bucket = var.s3_bucket_name          # Pass S3 bucket name to setup script
  }))
}

# 10. EC2 INSTANCE - The actual server
resource "aws_instance" "training_instance" {
  ami                    = local.ubuntu_ami_id              # Ubuntu server image
  instance_type          = var.instance_type               # Server size (t3.large)
  key_name              = var.key_pair_name                # SSH key for access
  vpc_security_group_ids = [aws_security_group.training_sg.id]  # Firewall rules
  iam_instance_profile   = aws_iam_instance_profile.ec2_profile.name  # S3 permissions

  # STORAGE CONFIGURATION
  root_block_device {
    volume_type = "gp3"                     # SSD storage type
    volume_size = 50                        # 50 GB disk space
    encrypted   = true                      # Encrypt data at rest
  }

  user_data = local.user_data               # *** THIS RUNS THE SETUP SCRIPT ***

  tags = {
    Name = "ai-drug-discovery-training"     # Instance name in AWS console
    Environment = "production"
    Project = "ai-drug-discovery"
  }
}

# Outputs
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

output "airflow_url" {
  description = "Airflow web UI URL"
  value       = "http://${aws_instance.training_instance.public_ip}:8080"
}

output "mlflow_url" {
  description = "MLflow web UI URL"
  value       = "http://${aws_instance.training_instance.public_ip}:5000"
}

# GitHub Secrets for reference
output "github_secrets_required" {
  description = "GitHub secrets that need to be configured"
  value = {
    AWS_ACCESS_KEY_ID         = "Your AWS access key ID"
    AWS_SECRET_ACCESS_KEY     = "Your AWS secret access key"
    AWS_EC2_INSTANCE_ID       = aws_instance.training_instance.id
    AIRFLOW_USERNAME          = "admin"
    AIRFLOW_PASSWORD          = "admin123"
  }
}