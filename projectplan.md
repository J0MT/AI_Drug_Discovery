# AI Drug Discovery - One-Shot Training via SSM

## Architecture Overview

**One-Shot Training Pipeline** using SSM Run Command with SQLite backend and S3 artifacts.

**Storage Choice**:
- MLflow backend (metadata/metrics): SQLite file on EC2 persistent disk
- MLflow artifacts (models/plots): S3 bucket

**Infrastructure**:
- EC2 instance: Amazon Linux 2 with outbound internet access
- EBS volume: Persists /opt/mlflow/mlruns.db
- IAM instance profile: AmazonSSMManagedInstanceCore + SSM Parameter access + S3 permissions
- Security Groups: Optional inbound 5000/tcp for MLflow UI, outbound open for GHCR and S3

**Pipeline Flow**: Code Push → GitHub Actions Build → GHCR Push → SSM Run Command → Training Container → MLflow Logging

## Persistent Services

**MLflow Server Container**:
- Docker installed and enabled on EC2
- MLflow server container: restart always
- Bind-mount for SQLite: Host /opt/mlflow/ ↔ Container /opt/mlflow/
- MLflow configuration:
  - Backend URI: sqlite:////opt/mlflow/mlruns.db
  - Artifact root: s3://ai-drug-artifacts/

## Networking Orchestration

**Docker Compose Network**:
- MLflow runs via Docker Compose creating user-defined network (mlflow_default)
- Service name must be mlflow for DNS resolution
- Training containers join same Compose network via --network mlflow_default
- Training → MLflow logging uses internal name: MLFLOW_TRACKING_URI=http://mlflow:5000
- Security Groups only needed for browser access to MLflow UI on port 5000

## Secrets & Configuration

**SSM Parameter Store**:
- /ghcr/ro-token (SecureString, read:packages scope)

**GitHub Secrets**:
- GHCR_TOKEN (for CI to push images)
- AWS_GITHUB_OIDC_ROLE (IAM role with ssm:SendCommand, ssm:GetCommandInvocation)

## CI/CD Flow

**Trigger**: Push to main branch

**Steps**:
1. Build Docker image (tag = commit SHA)
2. Push to GHCR
3. Assume AWS role via OIDC
4. SSM Run Command on EC2:
   - Login to GHCR using token from SSM
   - Pull tagged image
   - Run one-shot training container on mlflow_default network
   - Set MLFLOW_TRACKING_URI=http://mlflow:5000

## Training Job Implementation

**Execution**:
- Logs metrics/params to MLflow (SQLite backend file)
- Saves artifacts to S3 via MLflow artifact root

**Idempotency**:
- Composite run key = hash(model code) + hash(config) + hash(data snapshot)
- Uses Git commit SHA for code, canonicalized YAML config hash, data snapshot hash
- If prior MLflow run exists with same composite key, skip training
- No force override path implemented

## Monitoring & Audit

**Access Points**:
- MLflow UI: http://EC2_IP:5000 (restricted to your IP)
- SSM Run Command history in AWS Console

**Data Persistence**:
- SQLite location: /opt/mlflow/mlruns.db on EBS volume
- Persistence: Survives EC2 stop/start (EBS remains)
- Concurrency: Single training job at a time to avoid SQLite locks
- Maintenance: Periodic EBS snapshots, consider VACUUM during idle periods

## Security Implementation

**Access Control**:
- No SSH keys required (SSM access only)
- GHCR token stored in SSM Parameter Store, never on disk
- MLflow UI locked down to IP allowlist
- Least-privilege IAM for S3 and SSM access

**Rollback & Re-run**:
- Reproduce by re-running CI with previous commit SHA
- Same composite key results in skipped training (idempotency)
- Roll back by reverting code or updating config/data for new run

## Connectivity Requirements

**Docker & Networking**:
- Single user-defined network via Docker Compose
- Service name mlflow ensures DNS resolution at http://mlflow:5000
- Training containers must join same network or MLflow DNS resolution fails
- Container-to-container traffic stays on Docker network (bypasses Security Groups)

**MLflow ↔ SQLite**:
- Exact bind mount path matching: /opt/mlflow/ host ↔ /opt/mlflow/ container
- Container user must have read/write permissions on mlruns.db
- Single writer requirement to prevent SQLite locking conflicts
- Database persists on EBS, not ephemeral storage

**MLflow ↔ S3**:
- IAM instance profile with least-privilege S3 bucket access
- No static AWS keys in container images
- Correct AWS region configuration for S3 API calls
- Outbound internet access or S3 VPC endpoint required

**CI/CD ↔ EC2**:
- SSM agent running, instance shows as "Managed"
- GitHub OIDC role permissions for SSM commands
- AmazonSSMManagedInstanceCore attached to EC2 instance profile
- SSM user must have Docker group membership

**GHCR Authentication**:
- Read-only token in SSM Parameter Store
- Token scope: read:packages sufficient
- Runtime token retrieval, no persistent disk storage

**Common Issues & Solutions**:
- Training can't reach MLflow: Ensure container joins mlflow_default network
- Artifacts fail to upload: Verify S3 permissions, region, outbound connectivity
- SQLite lock errors: Ensure single training job execution
- GHCR pulls fail: Check token scope and SSM parameter permissions
- SSM/Docker issues: Verify user Docker group membership
- Idempotency failures: Use deterministic config hashing, stable data snapshots
- UI inaccessible: Verify Security Group port 5000 exposure, container port publishing

## System Architecture

**Single Service Stack**:
- MLflow Server: Persistent container with SQLite backend and S3 artifacts
- Docker Compose network: mlflow_default for container communication
- Training containers: One-shot execution, join mlflow_default network
- No API layer, job queue, or complex microservice orchestration

**Security Model**:
- SSM-only access, no SSH keys
- GHCR token in SSM Parameter Store
- MLflow UI restricted to specific IP addresses
- IAM instance profile with least-privilege permissions

## Project Structure

```
AI_Drug/
├── models/                      # Model implementations
│   ├── transformer/
│   │   ├── model.py            # TransformerRegressor + train()
│   │   └── train.py            # Training interface
│   ├── xgb/                    # XGBoost implementation  
│   └── rf/                     # Random Forest implementation
├── utils/                       # Training orchestration
│   ├── training_orchestrator.py # MLflow logging coordination
│   ├── training_types.py        # Standardized training contracts
│   └── signature.py            # Content-based signatures
├── configs/                     # Model configurations
│   ├── transformer.yaml        # Transformer hyperparameters
│   ├── xgb.yaml                # XGBoost configuration  
│   └── rf.yaml                 # Random Forest settings
├── tests/                      # Model training tests
├── aws/                        # Infrastructure
│   ├── terraform/main.tf       # EC2, IAM, Security Groups
│   └── ec2-setup.sh           # Instance initialization
├── train_dispatch_pure.py      # Main training orchestrator
├── docker-compose.yml          # MLflow service definition
├── Dockerfile                  # Training container image
└── .github/workflows/ci.yml    # SSM-based CI/CD pipeline
```

## Implementation Notes

**Development Commands**:
- Local training: `python train_dispatch_pure.py`
- Run tests: `PYTHONPATH=. pytest tests/`
- Code formatting: `black .`
- Linting: `flake8 .`

**Deployment Steps**:
1. Configure GitHub secrets: AWS_GITHUB_OIDC_ROLE, AWS_EC2_INSTANCE_ID, GHCR_TOKEN
2. Create SSM parameter: `/ghcr/ro-token` with GitHub Container Registry token
3. Deploy infrastructure: `cd aws/terraform && terraform apply`
4. Push to main branch to trigger training pipeline

**Technology Stack**:
- PyTorch, XGBoost, Scikit-learn: Model implementations
- MLflow: Experiment tracking and model registry
- Docker: Containerization and networking
- AWS EC2: Compute hosting with SSM access
- GitHub Container Registry: Private image storage


