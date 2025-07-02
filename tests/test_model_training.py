import pytest
import importlib
import pandas as pd
import subprocess

# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils import preprocess, split_data

# Dynamic import paths for each model
MODEL_PATHS = {
    "rf": "models.rf.model",
    "xgb": "models.xgb.model",
    "transformer": "models.transformer.model",
}


@pytest.mark.parametrize("model_key", MODEL_PATHS.keys())
def test_model_training(model_key):
    subprocess.run(["dvc", "pull", "data/data_200.csv.dvc"], check=True)

    # Dynamically import the model module
    module = importlib.import_module(MODEL_PATHS[model_key])
    train_fn = getattr(module, "train")

    # Load and preprocess data
    df = pd.read_csv("data/data_200.csv")
    X, y = preprocess(df)
    X_train, _, y_train, _ = split_data(X, y)

    # Train model
    model = train_fn(X_train, y_train)

    # Validate model object
    if model_key == "transformer":
        import torch.nn as nn

        assert isinstance(
            model, nn.Module
        ), f"{model_key} did not return a torch.nn.Module"
    else:
        assert hasattr(model, "predict"), f"{model_key} model lacks a .predict() method"
