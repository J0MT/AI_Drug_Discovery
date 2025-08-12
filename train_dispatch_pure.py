"""
Training dispatch with composite run key idempotency.
Handles data loading, training orchestration, and MLflow logging.
"""

import os
import glob
import yaml
import pandas as pd
import subprocess
import hashlib
from utils import preprocess, split_data
from utils.training_orchestrator import TrainingOrchestrator
from utils.training_types import TrainingConfig


def compute_composite_run_key(config: TrainingConfig) -> str:
    """
    Compute composite run key from model code + config + data snapshot.

    Args:
        config: Training configuration

    Returns:
        Composite key as hex string
    """
    # Get current git commit SHA (model code version)
    try:
        git_sha = (
            subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=".", stderr=subprocess.DEVNULL
            )
            .decode()
            .strip()
        )
    except:
        git_sha = "no-git"

    # Hash the config (normalize by serializing)
    config_hash = hashlib.sha256(
        str(sorted(config.__dict__.items())).encode()
    ).hexdigest()[:8]

    # Get data snapshot hash (use file modification time as proxy)
    try:
        data_stat = os.stat("data/data_200.csv")
        data_hash = hashlib.sha256(str(data_stat.st_mtime).encode()).hexdigest()[:8]
    except:
        data_hash = "no-data"

    # Composite key format: git_sha:config_hash:data_hash
    composite_key = f"{git_sha[:8]}:{config_hash}:{data_hash}"
    return composite_key


def main():
    """Main training dispatch function with idempotency."""
    print("Starting training dispatch with composite run key idempotency...")

    # Get MLflow tracking URI from environment (default to internal service name)
    mlflow_uri = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
    print(f"MLflow tracking URI: {mlflow_uri}")

    # Initialize orchestrator
    orchestrator = TrainingOrchestrator(mlflow_tracking_uri=mlflow_uri)

    # Pull latest data
    subprocess.run(["dvc", "pull"], check=True)

    # Load and preprocess data once
    # TODO: Make data path configurable
    df = pd.read_csv("data/data_200.csv")
    X, y = preprocess(df)
    X_train, X_test, y_train, y_test = split_data(X, y)

    print(
        f"Loaded data: {X_train.shape[0]} training samples, {X_test.shape[0]} test samples"
    )

    # Discover all training configurations
    config_paths = glob.glob("configs/*.yaml")
    configs = []

    for config_path in config_paths:
        with open(config_path, "r") as f:
            config_dict = yaml.safe_load(f)

        try:
            config = TrainingConfig.from_dict(config_dict)
            configs.append(config)
            print(f"Found config: {config.model_type} ({config_path})")
        except Exception as e:
            print(f"[WARNING] Invalid config {config_path}: {e}")
            continue

    if not configs:
        print("No valid training configurations found!")
        return

    # Check existing runs for each config and only train new ones
    print(f"\nChecking idempotency for {len(configs)} configurations...")
    configs_to_train = []

    for config in configs:
        composite_key = compute_composite_run_key(config)
        print(f"  {config.model_type}: composite key = {composite_key}")

        # Check if this exact run already exists in MLflow
        if orchestrator.run_exists_with_tag("composite_run_key", composite_key):
            print(f"    SKIP: Run with key {composite_key} already exists")
        else:
            print(f"    TRAIN: New composite key, will train")
            # Add composite key to config for tagging
            config.composite_run_key = composite_key
            configs_to_train.append(config)

    if not configs_to_train:
        print(
            "\nAll models already trained with current code/config/data - nothing to do!"
        )
        return

    # Run training only for new configurations
    print(
        f"\nStarting training for {len(configs_to_train)}/{len(configs)} configurations..."
    )
    results = orchestrator.train_multiple_configs(
        configs_to_train, X_train, y_train, X_test, y_test
    )

    # Summary
    print(f"\n{'='*60}")
    print("TRAINING SUMMARY")
    print(f"{'='*60}")
    print(f"Configurations processed: {len(configs)}")
    print(f"Models trained: {len(results)}")
    print(
        f"Models skipped: {len(configs) - len(results)} (idempotent - already trained)"
    )

    if results:
        print("\nResults:")
        for result in results:
            print(
                f"  {result.model_info['model_type']}: RMSE={result.metrics.rmse:.4f}, R²={result.metrics.r2:.4f}"
            )

    print(f"\nMLflow UI: {mlflow_uri}")
    print("Training dispatch completed!")


if __name__ == "__main__":
    main()
