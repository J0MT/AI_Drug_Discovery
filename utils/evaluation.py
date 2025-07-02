from sklearn.metrics import mean_squared_error, r2_score


def evaluate(y_true, y_pred):
    return {
        "rmse": mean_squared_error(y_true, y_pred, squared=False),
        "r2": r2_score(y_true, y_pred),
    }
