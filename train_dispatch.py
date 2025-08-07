import os
import subprocess
import yaml
import glob
from models.transformer.train import compute_training_signature
import mlflow

mlflow.set_tracking_uri("http://mlflow:5000")

for config_path in glob.glob("configs/*.yaml"):
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    signature = compute_training_signature(config, config["signature_files"])
    existing = mlflow.search_runs(filter_string=f"tags.signature = '{signature}'")

    if not existing.empty:
        print(f"[SKIP] Already trained: {config_path}")
        continue

    print(f"[TRAIN] Training with config: {config_path}")
    subprocess.run(["python", config["model_script"], "--config", config_path])

