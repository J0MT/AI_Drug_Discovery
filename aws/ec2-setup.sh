#!/bin/bash
# EC2 setup script for One-Shot Training via SSM
# Installs Docker, clones repo, starts persistent MLflow service

set -e

echo "Setting up AI Drug Discovery One-Shot Training environment..."

# Update system
sudo apt-get update -y
sudo apt-get upgrade -y

# Install Docker and Docker Compose
sudo apt-get install -y ca-certificates curl gnupg lsb-release git unzip
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update -y
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin docker-compose

# Add ubuntu user to docker group
sudo usermod -aG docker ubuntu

# Install AWS CLI v2
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
rm -rf aws awscliv2.zip

# Create persistent MLflow data directory
sudo mkdir -p /opt/mlflow
sudo chown -R ubuntu:ubuntu /opt/mlflow

# Clone the project repository  
cd /home/ubuntu
git clone https://github.com/${github_repo}/AI_Drug.git AI_Drug
cd /home/ubuntu/AI_Drug

# Make ubuntu owner of project directory
sudo chown -R ubuntu:ubuntu /home/ubuntu/AI_Drug

# Start persistent MLflow service with Docker Compose
echo "Starting persistent MLflow service..."
docker-compose up -d

# Wait for MLflow service to be ready
echo "Waiting for MLflow service to be ready..."
sleep 30

# Verify MLflow is running
echo "Checking MLflow service status..."
docker-compose ps

# Get public IP for access URLs
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)

# Create status check script
cat > /home/ubuntu/check-mlflow.sh << 'EOF'
#!/bin/bash
cd /home/ubuntu/AI_Drug

echo "=== Docker Container Status ==="
docker-compose ps

echo ""
echo "=== MLflow Health Check ==="
echo -n "MLflow Tracking Server: "
if curl -s http://localhost:5000/health > /dev/null 2>&1; then
    echo "HEALTHY"
else
    echo "DOWN - checking if service is running..."
    docker-compose logs mlflow | tail -10
fi

echo ""
echo "=== Access URLs ==="
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
echo "MLflow UI: http://$PUBLIC_IP:5000"

echo ""
echo "=== MLflow Data Persistence ==="
echo "SQLite Database: /opt/mlflow/mlruns.db"
echo "S3 Artifacts: s3://ai-drug-artifacts/"

echo ""
echo "=== Training via SSM ==="
echo "Training containers will join the 'mlflow_default' network and connect to MLflow at http://mlflow:5000"
EOF

chmod +x /home/ubuntu/check-mlflow.sh

# Create auto-start script for reboots
cat > /home/ubuntu/start-mlflow.sh << 'EOF' 
#!/bin/bash
cd /home/ubuntu/AI_Drug
echo "Starting MLflow service..."
docker-compose up -d
echo "MLflow started. Check status with: /home/ubuntu/check-mlflow.sh"
EOF

chmod +x /home/ubuntu/start-mlflow.sh

# Add to crontab for auto-start on boot
(crontab -l 2>/dev/null; echo "@reboot sleep 30 && /home/ubuntu/start-mlflow.sh") | crontab -

echo "================================================================================"
echo "AI Drug Discovery One-Shot Training Environment Ready"
echo "================================================================================"
echo ""
echo "Services Running:"
echo "  - MLflow Server (Port 5000) - Persistent experiment tracking"
echo "  - SQLite Backend - /opt/mlflow/mlruns.db"
echo "  - S3 Artifacts - s3://ai-drug-artifacts/"
echo ""
echo "Access URLs:"
echo "  - MLflow UI: http://$PUBLIC_IP:5000"
echo ""
echo "Training Architecture:"
echo "  - One-shot training via SSM Run Command"
echo "  - Training containers join 'mlflow_default' network"
echo "  - Internal MLflow connection: http://mlflow:5000"
echo "  - Composite run key idempotency (skip duplicate runs)"
echo ""
echo "Management Scripts:"
echo "  - Check MLflow: /home/ubuntu/check-mlflow.sh"
echo "  - Start MLflow: /home/ubuntu/start-mlflow.sh"
echo ""
echo "Data Persistence:"
echo "  - MLflow DB: /opt/mlflow/mlruns.db (EBS persistent)"
echo "  - Model Artifacts: S3 bucket (permanent storage)"
echo ""
echo "Auto-restart: MLflow restarts automatically on boot"
echo "================================================================================"