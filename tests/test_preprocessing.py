import pandas as pd
import numpy as np
import os
from utils import preprocess, split_data


def test_preprocessing_and_split():
    # Skip DVC pull in CI environment and use mock data
    if os.path.exists("data/data_200.csv"):
        df = pd.read_csv("data/data_200.csv")
    else:
        # Create mock DataFrame with expected columns for preprocessing
        np.random.seed(42)
        n_samples = 200
        df = pd.DataFrame(
            {
                "IC50_nM": np.random.uniform(0.1, 1000, n_samples),
                "Molecular_Weight": np.random.uniform(100, 800, n_samples),
                "LogP": np.random.uniform(-2, 8, n_samples),
                "NumRotatableBonds": np.random.randint(0, 20, n_samples),
                "NumHDonors": np.random.randint(0, 10, n_samples),
                "NumHAcceptors": np.random.randint(0, 15, n_samples),
                "TPSA": np.random.uniform(0, 200, n_samples),
                "target_protein": np.random.choice(
                    ["protein_A", "protein_B"], n_samples
                ),
            }
        )

    X, y = preprocess(df)
    X_train, X_test, y_train, y_test = split_data(X, y)
    assert X_train.shape[0] > 0 and X_test.shape[0] > 0
