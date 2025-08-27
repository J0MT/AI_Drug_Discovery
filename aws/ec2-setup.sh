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

# Add ubuntu user to docker group and enable Docker systemd service
sudo usermod -aG docker ubuntu
sudo systemctl enable docker
sudo systemctl enable containerd

# Install and configure SSM agent
echo "Installing and configuring SSM Agent..."
sudo snap install amazon-ssm-agent --classic
sudo systemctl enable snap.amazon-ssm-agent.amazon-ssm-agent
sudo systemctl start snap.amazon-ssm-agent.amazon-ssm-agent
sudo systemctl status snap.amazon-ssm-agent.amazon-ssm-agent --no-pager

# Wait for SSM agent to register
echo "Waiting for SSM agent to register (30 seconds)..."
sleep 30

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
git clone https://github.com/J0MT/AI_Drug_Discovery.git AI_Drug
cd /home/ubuntu/AI_Drug

# Make ubuntu owner of project directory
sudo chown -R ubuntu:ubuntu /home/ubuntu/AI_Drug

# Login to GitHub Container Registry using SSM parameter
echo "Logging into GitHub Container Registry..."
GHCR_TOKEN=$(aws ssm get-parameter --name ghcr-ro-token --with-decryption --query 'Parameter.Value' --output text --region eu-north-1)

# Login with proper error handling
if [ ! -z "$GHCR_TOKEN" ]; then
    sudo -u ubuntu bash -c "echo $GHCR_TOKEN | docker login ghcr.io -u j0mt --password-stdin"
    if [ $? -eq 0 ]; then
        echo "Successfully logged into GHCR"
    else
        echo "Failed to login to GHCR"
        exit 1
    fi
else
    echo "Failed to retrieve GHCR token from SSM"
    exit 1
fi

# Install MLflow systemd service
echo "Installing MLflow systemd service..."
sudo cp /home/ubuntu/AI_Drug/aws/mlflow.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable mlflow.service

# Start MLflow service
echo "Starting MLflow service via systemd..."
sudo systemctl start mlflow.service

# Wait for MLflow service to be ready
echo "Waiting for MLflow service to be ready..."
sleep 30

# Verify MLflow is running
echo "Checking MLflow service status..."
sudo systemctl status mlflow.service --no-pager
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

# Create MLflow management scripts
cat > /home/ubuntu/start-mlflow.sh << 'EOF' 
#!/bin/bash
echo "Starting MLflow service via systemd..."
sudo systemctl start mlflow.service
sudo systemctl status mlflow.service --no-pager
EOF

cat > /home/ubuntu/stop-mlflow.sh << 'EOF'
#!/bin/bash
echo "Stopping MLflow service..."
sudo systemctl stop mlflow.service
sudo systemctl status mlflow.service --no-pager
EOF

cat > /home/ubuntu/restart-mlflow.sh << 'EOF'
#!/bin/bash
echo "Restarting MLflow service..."
sudo systemctl restart mlflow.service
sudo systemctl status mlflow.service --no-pager
EOF

chmod +x /home/ubuntu/start-mlflow.sh
chmod +x /home/ubuntu/stop-mlflow.sh
chmod +x /home/ubuntu/restart-mlflow.sh

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
echo "Auto-restart: MLflow managed by systemd (reliable boot startup)"
echo "================================================================================"