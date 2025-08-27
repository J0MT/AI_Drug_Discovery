FROM python:3.9-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y git curl && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install dvc[s3] mlflow[extras] boto3

# Copy only training-related files
COPY models/ ./models/
COPY utils/ ./utils/
COPY configs/ ./configs/
COPY train_dispatch.py .
COPY *.dvc ./

# Set environment defaults
ENV MLFLOW_TRACKING_URI=http://mlflow:5000
ENV AWS_DEFAULT_REGION=eu-north-1

CMD ["python", "train_dispatch.py"]
