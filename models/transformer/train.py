import argparse
import pandas as pd
import torch
from utils.preprocessing import preprocess, split_data
from utils.evaluation import evaluate
from models.transformer.model import train  

def main(args):
    if args.dry_run:
        print(f"Dry run successful for {__file__}")
        return

    if not args.data:
        raise ValueError("You must provide --data for full training")

    # Load and preprocess data
    df = pd.read_csv(args.data)
    X, y = preprocess(df)
    X_train, X_test, y_train, y_test = split_data(X, y)

    # Train the Transformer model
    model = train(X_train, y_train)

    # Inference using torch
    with torch.no_grad():
        model.eval()
        X_test_tensor = torch.tensor(X_test.values, dtype=torch.float32)
        preds = model(X_test_tensor).squeeze().numpy()

    # Evaluate predictions
    metrics = evaluate(y_test, preds)
    print(f"[Transformer] RMSE: {metrics['rmse']:.4f} | R²: {metrics['r2']:.4f}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=str, help="Path to CSV data file")
    parser.add_argument("--dry-run", action="store_true", help="Run a dry test")
    args = parser.parse_args()

    main(args)
