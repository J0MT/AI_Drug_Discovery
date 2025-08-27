#!/bin/bash
# Test script for systemd service validation

echo "=== Testing MLflow Systemd Service Configuration ==="

# Validate service file syntax
echo "1. Validating service file syntax..."
systemd-analyze verify aws/mlflow.service
if [ $? -eq 0 ]; then
    echo "✅ Service file syntax is valid"
else
    echo "❌ Service file has syntax errors"
    exit 1
fi

# Check if Docker is available
echo ""
echo "2. Checking Docker availability..."
if command -v docker &> /dev/null; then
    echo "✅ Docker is installed"
    if systemctl is-enabled docker &> /dev/null; then
        echo "✅ Docker systemd service is enabled"
    else
        echo "⚠️  Docker systemd service is not enabled"
    fi
else
    echo "❌ Docker is not installed"
fi

# Check if docker-compose is available
echo ""
echo "3. Checking docker-compose availability..."
if command -v docker-compose &> /dev/null; then
    echo "✅ docker-compose is installed"
else
    echo "❌ docker-compose is not installed"
fi

# Validate docker-compose.yml
echo ""
echo "4. Validating docker-compose.yml..."
if [ -f "docker-compose.yml" ]; then
    docker-compose config --quiet 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "✅ docker-compose.yml is valid"
    else
        echo "❌ docker-compose.yml has errors"
    fi
else
    echo "❌ docker-compose.yml not found"
fi

echo ""
echo "=== Test Complete ==="