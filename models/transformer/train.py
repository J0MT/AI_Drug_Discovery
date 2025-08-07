import argparse
import yaml
import pandas as pd
import torch
import mlflow
import subprocess
import hashlib
import json
import os

from utils import preprocess, split_data, evaluate, compute_training_signature
from models.transformer.model import train as train_model

def compute_training_signature(config, file_paths):
    h = hashlib.sha256()
    h.update(json.dumps({k: v for k, v in config.items() if k != "data_path"}, sort_keys=True).encode())
    for path in file_paths:
        with open(path, "rb") as f:
            h.update(f.read())
    return h.hexdigest()

def main(args):
    if args.dry_run:
        print("Dry run successful.")
        return

    subprocess.run(["dvc", "pull"], check=True)

    with open(args.config, "r") as f:
        config = yaml.safe_load(f)

    df = pd.read_csv(config["data_path"])
    X, y = preprocess(df)
    X_train, X_test, y_train, y_test = split_data(X, y)
    config["input_dim"] = X_train.shape[1]

    mlflow.set_tracking_uri("http://mlflow:5000")
    mlflow.set_experiment(config.get("model_type", "default"))

    signature = compute_training_signature(config, config["signature_files"])
    existing_runs = mlflow.search_runs(filter_string=f"tags.signature = '{signature}'")

    if not existing_runs.empty:
        print("Model already trained with this config + code. Skipping.")
        return

    with mlflow.start_run():
        mlflow.set_tag("signature", signature)
        mlflow.log_params({k: v for k, v in config.items() if k not in ["data_path", "signature_files"]})
        model = train_model(X_train, y_train, config)

        with torch.no_grad():
            preds = model(torch.tensor(X_test.values, dtype=torch.float32)).squeeze().numpy()

        metrics = evaluate(y_test, preds)
        mlflow.log_metrics(metrics)

        print(f"[{config['model_type'].capitalize()}] RMSE: {metrics['rmse']:.4f} | R²: {metrics['r2']:.4f}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--config", type=str, required=True)
    args = parser.parse_args()
    main(args)

