"""
Pure training function for Transformer model.
No external dependencies on MLflow or logging.
"""

import argparse
import pandas as pd
import torch

from utils import evaluate
from utils.training_types import TrainingConfig, TrainingMetrics, TrainingResult
from models.transformer.model import train as train_transformer_model


def train(
    X_train: pd.DataFrame, y_train: pd.Series, config: TrainingConfig
) -> TrainingResult:
    """
    Pure training function for Transformer model.

    Args:
        X_train: Training features
        y_train: Training targets
        config: Training configuration

    Returns:
        TrainingResult with trained model, metrics, and metadata
    """
    # Convert config to the format expected by the model
    model_config = config.__dict__.copy()
    model_config["input_dim"] = X_train.shape[1]

    # Train the model (pure ML logic)
    model = train_transformer_model(X_train, y_train, model_config)

    # Make predictions for evaluation
    with torch.no_grad():
        X_tensor = torch.tensor(X_train.values, dtype=torch.float32)
        train_preds = model(X_tensor).squeeze().numpy()

    # Evaluate model performance
    raw_metrics = evaluate(y_train, train_preds)

    # Convert to standard metrics format
    metrics = TrainingMetrics(
        rmse=raw_metrics["rmse"], r2=raw_metrics["r2"], mae=raw_metrics.get("mae", 0.0)
    )

    # Model metadata
    model_info = {
        "model_type": "transformer",
        "input_dim": X_train.shape[1],
        "num_parameters": sum(p.numel() for p in model.parameters()),
        "architecture": str(model.__class__.__name__),
    }

    return TrainingResult(
        model=model, metrics=metrics, model_info=model_info, signature=""
    )


# Legacy CLI interface for backward compatibility
def main(args):
    """Legacy main function for CLI usage."""
    import yaml
    import subprocess
    from utils import preprocess, split_data

    if args.dry_run:
        print("Dry run successful.")
        return

    subprocess.run(["dvc", "pull"], check=True)

    with open(args.config, "r") as f:
        config_dict = yaml.safe_load(f)

    df = pd.read_csv(config_dict["data_path"])
    X, y = preprocess(df)
    X_train, X_test, y_train, y_test = split_data(X, y)

    # Convert to TrainingConfig
    config = TrainingConfig(**config_dict)

    # Use pure training function
    result = train(X_train, y_train, config)

    print(
        f"[{config.model_type.capitalize()}] "
        f"RMSE: {result.metrics.rmse:.4f} | R²: {result.metrics.r2:.4f}"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--config", type=str, required=True)
    args = parser.parse_args()
    main(args)
