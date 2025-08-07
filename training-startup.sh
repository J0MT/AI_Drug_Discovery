#!/bin/bash
# Training Instance Startup Script
# Containerized MLflow and training setup

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
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Add ubuntu user to docker group
sudo usermod -aG docker ubuntu

# Create persistent data directories on EBS
sudo mkdir -p /mnt/mlflow-data/postgres
sudo mkdir -p /mnt/training-data
sudo chown -R ubuntu:ubuntu /mnt/mlflow-data
sudo chown -R ubuntu:ubuntu /mnt/training-data

# Create project directory and navigate there
mkdir -p /home/ubuntu/AI_Drug
cd /home/ubuntu/AI_Drug

# Clone your repository (uncomment and update with your repo)
# git clone https://github.com/YOUR_USERNAME/AI_Drug_Discovery.git .

# Create environment file for MLflow
cat > .env << EOF
POSTGRES_PASSWORD=$(openssl rand -base64 32)
EOF

# Copy Docker Compose files (these should be in your repo)
# docker-compose.training.yml should be in your repository

# Start MLflow services
echo "Starting MLflow services..."
docker compose -f docker-compose.training.yml up -d mlflow postgres

# Wait for MLflow to be ready
echo "Waiting for MLflow to start..."
until curl -s http://localhost:5000/health > /dev/null; do
    echo "Waiting for MLflow..."
    sleep 5
done

echo "MLflow is ready at http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):5000"

# Create training script launcher
cat > /home/ubuntu/run-training.sh << 'EOF'
#!/bin/bash
cd /home/ubuntu/AI_Drug

# Ensure MLflow is running
docker compose -f docker-compose.training.yml up -d mlflow postgres

# Wait for MLflow
until curl -s http://localhost:5000/health > /dev/null; do
    sleep 2
done

# Run training with local MLflow
export MLFLOW_TRACKING_URI=http://localhost:5000

# Option 1: Run training directly on host
source venv/bin/activate 2>/dev/null || python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python train_dispatch.py

# Option 2: Run training in container (uncomment if you prefer)
# docker compose -f docker-compose.training.yml run --rm training python train_dispatch.py

echo "Training completed. MLflow data persists in /mnt/mlflow-data/"
echo "Check results at: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):5000"
EOF

chmod +x /home/ubuntu/run-training.sh

# Create shutdown script
cat > /home/ubuntu/shutdown-after-training.sh << 'EOF'
#!/bin/bash
echo "Shutting down MLflow services..."
cd /home/ubuntu/AI_Drug
docker compose -f docker-compose.training.yml down

echo "Training instance will shut down in 2 minutes..."
echo "PostgreSQL data is preserved in /mnt/mlflow-data/"
echo "S3 artifacts are preserved in s3://ai-drug-data/mlflow-artifacts"
sudo shutdown -h +2
EOF

chmod +x /home/ubuntu/shutdown-after-training.sh

echo "Setup completed!"
echo ""
echo "🚀 To run training:"
echo "   /home/ubuntu/run-training.sh"
echo ""
echo "🌐 MLflow UI:"
echo "   http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):5000"
echo ""
echo "💾 Data persistence:"
echo "   PostgreSQL: /mnt/mlflow-data/postgres (EBS volume)"
echo "   Artifacts: s3://ai-drug-data/mlflow-artifacts"
echo ""
echo "🛑 To shutdown safely:"
echo "   /home/ubuntu/shutdown-after-training.sh"