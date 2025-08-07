import argparse
import pandas as pd
from utils.preprocessing import preprocess, split_data
from utils.evaluation import evaluate
from models.rf.model import train


def main(args):
    if args.dry_run:
        print(f"Dry run successful for {__file__}")
        return  # skip the rest

    if not args.data:
        raise ValueError("You must provide --data for full training")

    # Load and preprocess data
    df = pd.read_csv(args.data)
    X, y = preprocess(df)
    X_train, X_test, y_train, y_test = split_data(X, y)

    # Train and evaluate model
    model = train(X_train, y_train)
    preds = model.predict(X_test)
    metrics = evaluate(y_test, preds)
    print(f"[RF] RMSE: {metrics['rmse']:.4f} | R²: {metrics['r2']:.4f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=str, help="Path to CSV data file")
    parser.add_argument("--dry-run", action="store_true", help="Run a dry test")
    args = parser.parse_args()

    main(args)
