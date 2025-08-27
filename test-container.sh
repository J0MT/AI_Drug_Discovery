#!/bin/bash 
# Run script with Bash shell

set -e
# exit immediately if a command exits with a non-zero  
# (0-success, non-0-failure) status

echo "=== Testing Optimized Training Container ==="


echo "1. Building optimized training container..."
docker build -t ai-drug-training:test .
# build the Docker image nad tag with name ai-drug-training & tag test

echo ""
echo "2. Testing container structure..."
echo "   Checking training files exist:"
docker run --rm ai-drug-training:test ls -la models/ utils/ configs/
docker run --rm ai-drug-training:test ls train_dispatch.py
# Verify training files are present and remove container after run
# list of contents in models/, utils/, configs/ directories
# check if train_dispatch.py file exists


echo ""
echo "  Checking excluded files are absent:"
if docker run --rm ai-drug-training:test ls aws/ 2>/dev/null; then
    echo "    ❌ aws/ directory should be excluded"
    exit 1
else
    echo "    ✅ aws/ directory properly excluded"
fi

if docker run --rm ai-drug-training:test ls .github/ 2>/dev/null; then
    echo "    ❌ .github/ directory should be excluded"
    exit 1
else
    echo "    ✅ .github/ directory properly excluded"
fi
# if aws/ or .github/ directories exist, print error and exit with failure status
# otherwise confirm they are excluded



echo ""
echo "3. Testing Python imports and dependencies..."

docker run --rm ai-drug-training:test python -c "
import sys
print('Python version:', sys.version)
print('Testing imports...')

# Core training imports
from utils import preprocess, split_data, evaluate
print('✓ utils imports OK')

import yaml
print('✓ yaml import OK')

import mlflow
print('✓ mlflow import OK')

import dvc.api
print('✓ dvc import OK')

print('✅ All critical imports successful')
"
# Run a Python command in the container to check imports and dependencies
# If any import fails, the script will exit with an error due to set -e



echo ""
echo "4. Testing DVC functionality..."
docker run --rm -e AWS_DEFAULT_REGION=eu-north-1 ai-drug-training:test dvc --version
# Check DVC version to ensure it's installed and working (AWS region not necessary)

echo ""
echo "5. Testing training script validation..."
docker run --rm ai-drug-training:test python -c "
import train_dispatch
print('✓ Training script imports successfully')
"
# Try importing the training script to ensure it works without errors

echo ""
echo " Container Test All pass:"
echo "  ✅ Training components present"
echo "  ✅ Infrastructure files excluded"  
echo "  ✅ Python dependencies working"
echo "  ✅ DVC functionality available"
echo "  ✅ Training scripts importable"
echo ""