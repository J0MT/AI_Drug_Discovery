#!/bin/bash
# EC2 Instance Setup Script for Training Pipeline
# Single Instance: Training + MLflow with Docker Compose
# Run this script on a fresh Ubuntu EC2 instance

set -e

echo "Starting training instance with containerized MLflow..."

# Update system
sudo apt-get update -y
sudo apt-get upgrade -y

# Install Docker and Docker Compose
sudo apt-get install -y ca-certificates curl gnupg lsb-release
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update -y
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin docker-compose

# Add ubuntu user to docker group
sudo usermod -aG docker ubuntu

# Install basic Python tools (for non-containerized training option)
sudo apt-get install -y python3 python3-pip python3-venv git

# Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
rm -rf aws awscliv2.zip

# Create persistent data directories on EBS
sudo mkdir -p /mnt/mlflow-data/postgres
sudo mkdir -p /mnt/training-data
sudo chown -R ubuntu:ubuntu /mnt/mlflow-data
sudo chown -R ubuntu:ubuntu /mnt/training-data

# Create project directory
mkdir -p /home/ubuntu/AI_Drug
cd /home/ubuntu/AI_Drug

# Clone repository (replace with your repo URL when ready)
# git clone https://github.com/YOUR_USERNAME/AI_Drug_Discovery.git .
# For now, we'll create a placeholder structure
mkdir -p models configs tests utils airflow/dags

# Create environment file for MLflow with secure password
cat > .env << EOF
POSTGRES_PASSWORD=$(openssl rand -base64 32)
EOF

# Create Python virtual environment (for non-containerized training)
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip

# Install core Python dependencies (without requirements.txt for now)
pip install \
    pandas \
    numpy \
    scikit-learn \
    torch \
    xgboost \
    mlflow \
    dvc[s3] \
    requests \
    psutil

# Create training utilities
cat > /home/ubuntu/run-training.sh << 'EOF'
#!/bin/bash
cd /home/ubuntu/AI_Drug

echo "Starting MLflow services..."
# Start MLflow + PostgreSQL via Docker Compose
docker-compose -f docker-compose.training.yml up -d mlflow postgres

# Wait for MLflow to be ready
echo "Waiting for MLflow to start..."
until curl -s http://localhost:5000/health > /dev/null 2>&1; do
    echo "Waiting for MLflow..."
    sleep 5
done

echo "MLflow is ready at http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):5000"

# Set MLflow tracking URI for training
export MLFLOW_TRACKING_URI=http://localhost:5000

# Run training (choose one approach):
# Option 1: Direct Python training
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "Running training with local Python environment..."
    python train_dispatch.py || echo "train_dispatch.py not found - run your training script manually"
else
    echo "Python virtual environment not found"
fi

# Option 2: Container-based training (uncomment if you prefer)
# echo "Running training in container..."
# docker-compose -f docker-compose.training.yml run --rm training python train_dispatch.py

echo "Training completed. Check results at: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):5000"
echo "MLflow data persists in /mnt/mlflow-data/"
EOF

chmod +x /home/ubuntu/run-training.sh

# Create MLflow startup script
cat > /home/ubuntu/start-mlflow.sh << 'EOF'
#!/bin/bash
cd /home/ubuntu/AI_Drug

echo "Starting MLflow services only..."
docker-compose -f docker-compose.training.yml up -d mlflow postgres

echo "Waiting for MLflow to start..."
until curl -s http://localhost:5000/health > /dev/null 2>&1; do
    echo "Waiting for MLflow..."
    sleep 5
done

echo "MLflow started at http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):5000"
EOF

chmod +x /home/ubuntu/start-mlflow.sh

# Create shutdown script
cat > /home/ubuntu/shutdown-after-training.sh << 'EOF'
#!/bin/bash
echo "Shutting down MLflow services..."
cd /home/ubuntu/AI_Drug
docker-compose -f docker-compose.training.yml down

echo "Training instance will shut down in 2 minutes..."
echo "PostgreSQL data is preserved in /mnt/mlflow-data/"
echo "S3 artifacts are preserved in s3://ai-drug-data/mlflow-artifacts"
sudo shutdown -h +2
EOF

chmod +x /home/ubuntu/shutdown-after-training.sh

# Complete setup with final instructions
cat > /home/ubuntu/setup-complete.txt << EOF
Training Instance Setup Complete!

📋 Next Steps:
1. Copy your project files to this instance:
   - Copy docker-compose.training.yml to /home/ubuntu/AI_Drug/
   - Copy your training scripts (train_dispatch.py, models/, etc.)
   - Or set up git clone in the setup script

2. Start MLflow services:
   /home/ubuntu/start-mlflow.sh

3. Run training:
   /home/ubuntu/run-training.sh

4. Access MLflow UI:
   http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):5000

5. Safely shutdown when done:
   /home/ubuntu/shutdown-after-training.sh

🎯 Key Features:
- ✅ Docker and Docker Compose installed
- ✅ Python environment ready
- ✅ MLflow + PostgreSQL containerized setup
- ✅ Persistent data storage (/mnt/mlflow-data/)
- ✅ S3 artifact storage configured
- ✅ Training scripts ready

💾 Data Persistence:
- PostgreSQL data: /mnt/mlflow-data/postgres (survives shutdowns)
- Model artifacts: s3://ai-drug-data/mlflow-artifacts
- Training data: /mnt/training-data

🌐 Services:
- MLflow UI: Port 5000
- Training: On-demand execution
- All services managed via Docker Compose

EOF

# Auto-start MLflow on boot (optional)
cat > /home/ubuntu/boot-setup.sh << 'EOF'
#!/bin/bash
# Auto-start MLflow when instance boots (optional)
cd /home/ubuntu/AI_Drug
if [ -f "docker-compose.training.yml" ]; then
    /home/ubuntu/start-mlflow.sh
    echo "MLflow started automatically on boot"
else
    echo "docker-compose.training.yml not found - MLflow not started"
fi
EOF

chmod +x /home/ubuntu/boot-setup.sh

# Add to crontab for auto-start on boot (optional)
(crontab -l 2>/dev/null; echo "@reboot /home/ubuntu/boot-setup.sh") | crontab -

echo "================================================================================"
echo "🎉 EC2 Setup Completed Successfully!"
echo "================================================================================"
echo ""
echo "📋 Next Steps:"
echo "1. Copy docker-compose.training.yml to /home/ubuntu/AI_Drug/"
echo "2. Copy your training code to /home/ubuntu/AI_Drug/"
echo "3. Run: /home/ubuntu/start-mlflow.sh"
echo "4. Run: /home/ubuntu/run-training.sh"
echo ""
echo "🌐 MLflow UI will be available at:"
echo "   http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):5000"
echo ""
echo "📖 Full instructions: /home/ubuntu/setup-complete.txt"
echo "================================================================================"