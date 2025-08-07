# AI Drug Discovery Project Plan

## Project Overview

**Complete AI Drug Discovery MLOps Pipeline** that:

1. **Detects model changes** via signature-based hashing (code + config changes)
2. **Automatically trains only modified models** on AWS after CI/CD validation
3. **Compares all trained models** and selects the best performer
4. **Automatically deploys the winning model** via FastAPI for real-time predictions
5. **Serves drug property predictions** (IC₅₀, ADMET properties) through REST API

**Full pipeline**: Local Dev → GitHub CI/CD → AWS Training → Model Selection → API Deployment

## Current Project Structure

### Core Components
```
AI_Drug/
├── models/                     # ML model implementations
│   ├── transformer/           # Transformer-based model
│   │   ├── __init__.py
│   │   ├── model.py          # TransformerRegressor architecture
│   │   └── train.py          # Training script with MLflow
│   ├── xgb/                  # XGBoost model
│   │   ├── __init__.py
│   │   ├── model.py
│   │   └── train.py
│   └── rf/                   # Random Forest model
│       ├── __init__.py
│       ├── model.py
│       └── train.py
├── utils/                     # Shared utilities
│   ├── __init__.py           # preprocess, split_data, evaluate
│   ├── preprocessing.py      # Data preprocessing functions
│   ├── evaluation.py         # Model evaluation metrics
│   └── signature.py          # Training signature computation
├── configs/                   # Configuration files
│   └── transformer.yaml     # Transformer hyperparameters
├── tests/                    # Test suite
│   ├── test_model_training.py    # Parameterized model tests
│   └── test_preprocessing.py     # Preprocessing tests
├── data/                     # DVC-tracked datasets
│   ├── data_200.csv
│   └── data_200.csv.dvc
├── train_dispatch.py         # Local orchestration script
├── next_step.py             # Development utility
├── api/                      # FastAPI deployment
│   ├── __init__.py
│   ├── main.py              # FastAPI app
│   ├── models.py            # API data models
│   └── deployment.py        # Model loading and inference
├── airflow/                 # Production orchestration
│   └── dags/
│       └── ai_drug_training_dag.py  # Training + deployment DAG
├── aws/                     # AWS infrastructure
│   ├── ec2-setup.sh        # Instance setup script
│   └── terraform/          # Infrastructure as code
└── Dockerfile               # Container configuration
```

## Data Flow

### Production Training Pipeline Flow (AWS + Airflow)
1. **GitHub Trigger**: 
   - Push to main branch triggers GitHub Actions
   - Actions run tests, linting, and dry-run validation
   - If all tests pass, triggers Airflow DAG on AWS EC2

2. **AWS EC2 Training Environment**:
   - Single EC2 instance hosts both Airflow and MLflow
   - Instance starts/stops based on training needs (cost optimization)
   - MLflow server runs on same instance during training

3. **Airflow DAG Execution**:
   - **Task 1**: Environment setup and DVC data pull from S3
   - **Task 2**: Config discovery and signature computation
   - **Task 3**: MLflow deduplication check (skip already trained models)
   - **Task 4**: Parallel model training (only models with new signatures)
   - **Task 5**: Model comparison and best model selection
   - **Task 6**: Deploy best model to FastAPI endpoint
   - **Task 7**: Update production API with new model
   - **Task 8**: Cleanup and optional instance shutdown

4. **Data Pipeline on AWS**:
   - DVC remote storage on S3
   - Large datasets pulled only during training
   - Preprocessed data cached on EC2 instance
   - Results stored in MLflow (local storage on EC2)

### Local Development Flow
- Local development continues with existing `train_dispatch.py`
- Small dataset testing and validation
- Push to GitHub triggers production training

### Model Implementation Pattern
Each model follows consistent structure:
- `model.py`: Contains model class and `train(X_train, y_train, config)` function
- `train.py`: CLI script with argparse, MLflow integration, DVC data pulling
- Config validation ensures required hyperparameters present

## Technology Stack

### ML & Data
- **PyTorch**: Deep learning framework (Transformer model)
- **XGBoost**: Gradient boosting
- **Scikit-learn**: Random Forest, evaluation metrics
- **Pandas/NumPy**: Data manipulation

### MLOps
- **MLflow**: Experiment tracking, model registry (hosted on EC2)
- **DVC**: Data version control (S3 remote storage)
- **Airflow**: Workflow orchestration on AWS EC2
- **Docker**: Containerization

### Cloud Infrastructure
- **AWS EC2**: Training compute and MLflow hosting
- **AWS S3**: DVC remote storage for datasets
- **GitHub Actions**: CI/CD pipeline with AWS integration

### Development
- **pytest**: Testing framework
- **black**: Code formatting
- **flake8**: Linting

## Current Capabilities

### Implemented Models
1. **Transformer**: Multi-head attention architecture for molecular property prediction
2. **XGBoost**: Gradient boosting for structured chemical data
3. **Random Forest**: Ensemble method for baseline comparisons

### Infrastructure
- Signature-based training deduplication
- Automated experiment tracking via MLflow on EC2
- Parameterized testing across all models
- CI/CD with linting, testing, and Airflow trigger
- AWS-based production training pipeline
- Cost-optimized EC2 instance management

## Development Workflow

### Adding New Models
1. Create `models/new_model/` with standard structure
2. Implement `train(X_train, y_train, config)` in `model.py`
3. Create training script following existing pattern
4. Add YAML config with signature_files specification
5. Update `tests/test_model_training.py` MODEL_PATHS

### Production Training Workflow
1. **Local Development**: 
   - Develop and test locally with small dataset
   - Push changes to GitHub main branch
2. **CI/CD Pipeline**: 
   - GitHub Actions run full test suite
   - If tests pass, trigger Airflow DAG on AWS EC2
3. **AWS Training**: 
   - EC2 instance starts (if stopped)
   - Airflow executes training DAG
   - MLflow server starts for experiment tracking
   - Results logged and instance shuts down

### Experiment Management
- Production runs logged to MLflow on EC2
- Experiments organized by model type
- Signature system prevents redundant training
- Metrics standardized across models (RMSE, R²)
- Local MLflow for development, AWS MLflow for production

## AWS Infrastructure Setup

### EC2 Instance Configuration
- **Instance Type**: t3.large or m5.large (depending on training requirements)
- **Storage**: EBS with sufficient space for models and temp data
- **Security Groups**: 
  - SSH access (port 22) for management
  - Airflow web UI (port 8080) for monitoring
  - MLflow UI (port 5000) for experiment tracking
- **Auto-scaling**: Manual start/stop via GitHub Actions for cost optimization

### Required AWS Services
- **EC2**: Training compute and service hosting
- **S3**: DVC remote storage bucket
- **IAM**: Roles for EC2 to access S3
- **CloudWatch**: Optional logging and monitoring

### Cost Optimization Strategy
- EC2 instance runs only during training (started by GitHub Actions)
- Instance automatically shuts down after training completion
- S3 storage for long-term data persistence
- Local EC2 storage for MLflow (acceptable for single-user project)

### AWS Instance Type Selection Guide

#### How to Choose the Right Instance Type

**Start Small, Scale Up**: Begin with `t3.large` and monitor resource usage:

```bash
# Check CPU and memory usage during training (on EC2)
htop
# Or
top

# Check memory usage specifically
free -h

# Monitor disk I/O
iostat -x 1
```

#### Instance Type Recommendations

| Instance Type | vCPUs | RAM | Best For | Estimated Cost/hour* |
|---------------|-------|-----|----------|---------------------|
| `t3.medium`   | 2     | 4GB | Small datasets, testing | $0.04 |
| `t3.large`    | 2     | 8GB | **Recommended start** | $0.08 |
| `t3.xlarge`   | 4     | 16GB | Medium datasets | $0.17 |
| `m5.large`    | 2     | 8GB | Balanced compute | $0.10 |
| `m5.xlarge`   | 4     | 16GB | CPU-intensive training | $0.19 |
| `c5.xlarge`   | 4     | 8GB | High CPU, less memory | $0.17 |

*Prices vary by region and are approximate

#### When to Upgrade Instance Type

**Upgrade if you see**:
- Memory usage consistently > 80%
- CPU usage consistently > 90%
- Training takes > 2 hours
- Out of memory errors

**How to upgrade**:
1. Update `instance_type` in `terraform.tfvars`
2. Run `terraform apply`
3. Instance will be replaced with new type

### AWS Quota Management

#### Check Your AWS Quotas

**Before deploying, check your limits**:

```bash
# Check EC2 quotas in your region
aws service-quotas get-service-quota \
    --service-code ec2 \
    --quota-code L-1216C47A \
    --region eu-north-1

# List all EC2-related quotas
```

**Via AWS Console**:
1. Go to AWS Console → Service Quotas
2. Search for "EC2"
3. Look for "Running On-Demand instances"
4. Check your current limit vs usage

#### Common Quota Issues

**New AWS Account Limits**:
- Often limited to 5-20 vCPUs for On-Demand instances
- `t3.large` = 2 vCPUs (should be fine)
- `m5.xlarge` = 4 vCPUs (might need quota increase)

**Request Quota Increase**:
1. AWS Console → Service Quotas → EC2
2. Find "Running On-Demand instances"
3. Click "Request quota increase"
4. Usually approved within 24-48 hours

#### Regional Considerations

**Why I chose `eu-north-1` (Stockholm)**:
- Lower costs than US regions
- Good availability
- GDPR compliant (if relevant)

**Alternative regions**:
- `us-east-1` (Virginia): Cheapest, most services
- `eu-west-1` (Ireland): Good EU option
- `ap-southeast-1` (Singapore): Asia-Pacific

## Implementation Roadmap

### Phase 0: Prerequisites and Local Setup ✅ COMPLETED

#### Step 1: Install Tools (Windows PowerShell as Administrator)
- [x] Install Terraform: `winget install HashiCorp.Terraform` ✅ v1.12.2
- [x] Install AWS CLI: `winget install Amazon.AWSCLIV2` ✅ v2.27.57
- [x] Restart terminal and verify installations ✅

#### Step 2: AWS Account Setup
- [x] Create AWS account and IAM user ✅
- [x] Configure programmatic access with proper policies ✅
- [x] Save Access Key ID and Secret Access Key ✅

#### Step 3: Configure AWS CLI
- [x] Run: `aws configure` ✅
- [x] Region: `eu-north-1`, Output: `json` ✅

#### Step 4: Check AWS Quotas
- [x] Check EC2 quotas: ✅ **16 vCPUs available**
- [x] Verify sufficient capacity for t3.large ✅

#### Step 5: Additional Setup
- [x] Create EC2 key pair: `AI_Drug_Discovery_key_pair` ✅
- [x] Get public IP addresses: **152.37.123.99** / **31.14.251.79** ✅

### Phase 1: AWS Infrastructure Setup ✅ COMPLETED
- [x] Copy `terraform.tfvars.example` to `terraform.tfvars` ✅
- [x] Fill in your specific values in `terraform.tfvars` ✅
- [x] Initialize Terraform: `terraform init` ✅
- [x] Review infrastructure plan: `terraform plan` ✅
- [x] Deploy infrastructure: `terraform apply` ✅

#### 🚀 **DEPLOYED INFRASTRUCTURE DETAILS (2025-01-05)**
- **EC2 Instance ID**: `i-0ef70348636813c26`
- **Public IP**: `13.49.74.70`
- **DNS**: `ec2-13-49-74-70.eu-north-1.compute.amazonaws.com`
- **Instance Type**: t3.large (2 vCPUs, 8GB RAM, 50GB encrypted storage)
- **Region**: eu-north-1 (Stockholm)
- **Key Pair**: AI_Drug_Discovery_key_pair
- **Security Group**: ai-drug-discovery-training-sg (SSH:22, Airflow:8080, MLflow:5000 from 152.37.123.99/32)

#### 🌐 **Service URLs**
- **Airflow UI**: http://13.49.74.70:8080 (username: admin/ password: admin123)
- **MLflow UI**: http://13.49.74.70:5000
- **SSH Access**: `ssh -i AI_Drug_Discovery_key_pair.pem ubuntu@13.49.74.70`

#### 📊 **GitHub Secrets Required for CI/CD**
- `AWS_ACCESS_KEY_ID`: Your AWS access key ID
- `AWS_SECRET_ACCESS_KEY`: Your AWS secret access key  
- `AWS_EC2_INSTANCE_ID`: i-0ef70348636813c26
- `AIRFLOW_USERNAME`: admin
- `AIRFLOW_PASSWORD`: admin123

#### ✅ **COMPLETED STATUS (2025-01-05)**
- [x] SSH connection working ✅
- [x] Analyzed setup script failure (missing requirements.txt) ✅
- [x] Designed single-instance MLflow + training architecture ✅
- [x] Updated ec2-setup.sh for containerized MLflow ✅
- [x] Created Docker Compose configuration ✅

#### 🔄 **NEXT SESSION TODO**
- [ ] Copy docker-compose.training.yml to EC2 instance
- [ ] Copy training code (train_dispatch.py, models/, etc.) to EC2
- [ ] Test containerized MLflow setup
- [ ] Verify persistent storage and S3 integration
- [ ] Run end-to-end training with MLflow logging

### Phase 2: DVC and Data Configuration
- [ ] Configure DVC remote to use created S3 bucket
- [ ] Upload initial dataset to S3 via DVC
- [ ] Test data pulling from EC2 instance
- [ ] Verify DVC credentials work on EC2

### Phase 3: GitHub Integration
- [ ] Add required GitHub secrets (AWS credentials, instance ID, etc.)
- [ ] Test GitHub Actions workflow with dry-run
- [ ] Push to main branch and verify EC2 instance starts
- [ ] Verify Airflow DAG triggers correctly
- [ ] Test end-to-end training pipeline

### Phase 4: Model Comparison and Selection
- [ ] Implement model comparison logic in Airflow DAG
- [ ] Add best model selection based on evaluation metrics
- [ ] Create model registry for production models
- [ ] Test model comparison with multiple trained models

### Phase 5: FastAPI Deployment System
- [ ] Create FastAPI application structure
- [ ] Implement model loading and inference endpoints
- [ ] Add automatic model deployment to API
- [ ] Test API endpoints with predictions
- [ ] Integrate API deployment into Airflow DAG

### Phase 6: Production API Hosting
- [ ] Deploy FastAPI to AWS (EC2 or ECS)
- [ ] Set up API domain and SSL certificate
- [ ] Implement API authentication/authorization
- [ ] Add API monitoring and logging
- [ ] Test end-to-end: code push → training → API update

### Phase 7: Monitoring and Optimization
- [ ] Set up AWS billing alerts
- [ ] Add CloudWatch monitoring for costs and API performance
- [ ] Optimize instance sizing based on actual resource usage
- [ ] Add model performance tracking over time
- [ ] Implement A/B testing for model versions
- [ ] Document operational procedures

## Troubleshooting Guide

### Common Terraform Issues

**Error: "no EC2 instance types are available"**
```bash
# Check if instance type is available in your region
aws ec2 describe-instance-type-offerings \
    --filters Name=instance-type,Values=t3.large \
    --location-type availability-zone \
    --region eu-north-1
```

**Error: "quota exceeded"**
- Check quotas as described above
- Try smaller instance type temporarily
- Request quota increase

**Error: "invalid key pair"**
- Create key pair in AWS console first
- Ensure key pair exists in the same region

### Instance Not Starting Issues

**GitHub Actions can't connect to EC2**:
1. Check security group allows your IP
2. Verify instance is actually running: `aws ec2 describe-instances`
3. Check if Airflow service started: SSH to instance and run `sudo systemctl status airflow-webserver`

**MLflow not accessible**:
1. SSH to instance: `ssh -i your-key.pem ubuntu@EC2_IP`
2. Start MLflow manually: `/home/ubuntu/start-mlflow.sh`
3. Check if port 5000 is open: `sudo netstat -tlnp | grep 5000`

### Cost Monitoring Commands

```bash
# Check current month's costs
aws ce get-cost-and-usage \
    --time-period Start=2024-01-01,End=2024-01-31 \
    --granularity MONTHLY \
    --metrics BlendedCost

# Check if instance is running (charges apply)
aws ec2 describe-instances \
    --instance-ids i-1234567890abcdef0 \
    --query 'Reservations[].Instances[].State.Name'
```

## Architecture Hosting Summary

```
🏠 LOCAL DEVELOPMENT
├── Model development and testing
├── Small dataset validation
└── Code pushes to GitHub

🔄 GITHUB ACTIONS (CI/CD)
├── Unit tests, linting, dry-runs
├── Signature change detection
└── AWS pipeline trigger

☁️ AWS EC2 TRAINING INSTANCE
├── Airflow DAG orchestration
├── MLflow experiment tracking
├── Model training (only changed models)
├── Model comparison and selection
└── Best model deployment

📦 AWS S3
├── DVC remote storage (datasets)
└── Model artifacts and metadata

🌐 AWS PRODUCTION API (EC2/ECS)
├── FastAPI serving best model
├── Real-time drug predictions
├── REST endpoints for inference
└── Automatic model updates

📊 MONITORING
├── AWS CloudWatch (costs, performance)
├── MLflow model registry
└── API usage analytics
```

## Future Enhancements
- [ ] Ensemble model combinations
- [ ] Advanced molecular descriptors  
- [ ] Multi-region deployment for redundancy
- [ ] Real-time model drift detection
- [ ] Automated hyperparameter optimization
- [ ] Model explainability features