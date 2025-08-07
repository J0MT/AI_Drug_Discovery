FROM python:3.9-slim
WORKDIR /app
COPY . .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    apt-get update && apt-get install -y git && \
    pip install dvc[s3] mlflow
    
CMD ["python", "train_dispatch.py"]
