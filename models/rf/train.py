import argparse
import pandas as pd
from utils.preprocessing import preprocess, split_data
from utils.evaluation import evaluate
from models.rf.model import train  

def main(args):
    df = pd.read_csv(args.data)
    X, y = preprocess(df)
    X_train, X_test, y_train, y_test = split_data(X, y)
    model = train(X_train, y_train)

    preds = model.predict(X_test)
    metrics = evaluate(y_test, preds)
    print(f"[RF] RMSE: {metrics['rmse']:.4f} | R²: {metrics['r2']:.4f}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=str, required=True)
    args = parser.parse_args()
    main(args)