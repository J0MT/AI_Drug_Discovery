#!/bin/bash
# Local development testing script

echo "🧪 Testing AI Drug Discovery Pipeline Locally"
echo "=============================================="

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop."
    exit 1
fi

# Copy env template if .env.local doesn't exist
if [ ! -f .env.local ]; then
    echo "📋 Creating .env.local from template..."
    cp .env.local.example .env.local
    echo "✅ Please edit .env.local with your AWS profile/credentials"
fi

echo "🏗️  Building training container locally..."
docker build -t ai-drug-training:dev .

echo "🚀 Starting MLflow service..."
docker compose --env-file .env.local up -d mlflow

echo "⏳ Waiting for MLflow to be healthy..."
docker compose --env-file .env.local exec mlflow python -c "
import urllib.request
import time
for i in range(30):
    try:
        urllib.request.urlopen('http://localhost:5000')
        print('✅ MLflow is ready!')
        break
    except:
        time.sleep(1)
        print(f'⏳ Waiting... ({i+1}/30)')
else:
    print('❌ MLflow failed to start')
    exit(1)
"

echo "🧪 Testing training container..."
docker compose --env-file .env.local run --rm training

echo "🎉 Local test complete!"
echo "📊 View MLflow at: http://localhost:5000"
echo "🛑 Stop services with: docker compose down"