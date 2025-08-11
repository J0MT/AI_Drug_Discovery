# AI Drug Discovery Pipeline

A production-ready pipeline for target-agnostic, structure-based drug discovery. It supports automated screening of ligands against any protein target from ChEMBL, extracting 2D fingerprints, ADMET properties, and generating 3D conformers for molecular docking. Preprocessing is designed specifically to transform raw chemical and docking data into structured features suitable for structure–function modeling (e.g., predicting inhibitory concentration values such as IC₅₀).

## Tech Stack

**ML & Data**
- PyTorch, XGBoost, Scikit-learn: Multi-model ensemble architecture
- MLflow: Experiment tracking, model registry, and artifact management
- DVC: Data versioning with S3 backend
- Pandas, NumPy: Data processing and feature engineering

**Infrastructure & DevOps**  
- AWS EC2 + Terraform: Infrastructure as Code deployment
- Docker + Docker Compose: Containerized services with network orchestration
- GitHub Container Registry: Private image storage and distribution
- GitHub Actions: CI/CD with automated model training triggers
- SSM Run Command: Serverless job orchestration

**Development & Quality**
- pytest: Comprehensive unit and integration testing
- black, flake8: Code formatting and linting
- Type hints: Static type checking for reliability
- YAML configs: Declarative hyperparameter management
