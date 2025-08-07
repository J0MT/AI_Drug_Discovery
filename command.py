----AWS----
aws configure
aws sts get-caller-identity
aws service-quotas get-service-quota --service-code ec2 --quota-code L-1216C47A --region eu-north-1
# L-1216C47A is the specific identifier for the "standard instance vCPU limit" quota  
aws s3 ls # List your S3 buckets
aws s3 ls s3://your-existing-bucket-name --recursive # Check what's in your existing bucket


----DVC----
dvc remote list


----IP Address----
https://whatismyipaddress.com/
# 152.37.123.99 Flat 107 Queens Court


----Terraform----
copy terraform.tfvars.example terraform.tfvars
# need to be in terraform directory for below
terraform init 
# What this does:
#   - Downloads AWS provider (code that knows how to talk to AWS)
#   - Sets up state management (Terraform's memory system)
#   - Prepares the directory for Terraform operations
terraform plan
# What this does:
#   - Shows you EXACTLY what Terraform will create
#   - Like a preview before making changes
#   - No changes are made - just shows the plan

#   What you'll see: A detailed list like:
#   - "Will create EC2 instance"
#   - "Will create security group"
#   - "Will create IAM role"
terraform apply
# What this does:
#   - Actually creates all the AWS resources
#   - Asks for confirmation before proceeding
#   - Shows progress as it builds everything
terraform destroy




ssh -i "C:\Users\jomkr\Downloads\ai-drug-discovery-key.pem" ubuntu@13.60.76.85