import argparse
import pandas as pd
import numpy as np
import torch

from utils.preprocessing import preprocess, split_data
from utils.evaluation import evaluate

from models.rf import train_rf
from models.xgb import train_xgb
from models.transformer import train_transformer


def main(args):
    df = pd.read_csv(args.data)
    X, y = preprocess(df)
    X_train, X_test, y_train, y_test = split_data(X, y)

    if args.model == "rf":
        model = train_rf(X_train, y_train)
        preds = model.predict(X_test)

    elif args.model == "xgb":
        model = train_xgb(X_train, y_train)
        preds = model.predict(X_test)

    metrics = evaluate(y_test, preds)
    print(f"{args.model} | RMSE: {metrics['rmse']:.4f} | R²: {metrics['r2']:.4f}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, required=True, choices=["rf", "xgb", "transformer"])
    parser.add_argument("--data", type=str, help="Path to the dataset CSV file")
    args = parser.parse_args()
    main(args)
    #python train.py --model transformer --data data/data_200.csv