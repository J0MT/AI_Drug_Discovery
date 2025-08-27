import pytest
import importlib
import pandas as pd
import numpy as np
import os

# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils import preprocess, split_data

# Dynamic import paths for each model
MODEL_PATHS = {
    "transformer": "models.transformer.model",
}


@pytest.mark.parametrize("model_key", MODEL_PATHS.keys())
def test_model_training(model_key):
    # Skip DVC pull in CI environment and use mock data
    if os.path.exists("data/data_200.csv"):
        df = pd.read_csv("data/data_200.csv")
        X, y = preprocess(df)
        X_train, _, y_train, _ = split_data(X, y)
    else:
        # Create mock data for testing
        np.random.seed(42)
        n_samples, n_features = 100, 10
        X_train = pd.DataFrame(np.random.randn(n_samples, n_features))
        y_train = pd.Series(np.random.randn(n_samples))

    # Dynamically import the model module
    module = importlib.import_module(MODEL_PATHS[model_key])
    train_fn = getattr(module, "train")

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
