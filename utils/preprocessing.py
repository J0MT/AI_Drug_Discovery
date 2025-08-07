from sklearn.model_selection import train_test_split


def preprocess(df):
    df = df.dropna(subset=["pIC50", "docking_score"])
    fp_cols = [col for col in df.columns if col.startswith("PubchemFP")]
    X = df[fp_cols + ["docking_score"]]
    y = df["pIC50"]
    return X, y


def split_data(X, y, test_size=0.2, random_state=42):
    return train_test_split(X, y, test_size=test_size, random_state=random_state)
