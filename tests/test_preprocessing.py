import pandas as pd
from utils import preprocess, split_data


def test_preprocessing_and_split():
    df = pd.read_csv("data/data_200.csv")
    X, y = preprocess(df)
    X_train, X_test, y_train, y_test = split_data(X, y)
    assert X_train.shape[0] > 0 and X_test.shape[0] > 0
