import xgboost as xgb


def train(X_train, y_train):
    model = xgb.XGBRegressor(n_estimators=10, objective="reg:squarederror")
    model.fit(X_train, y_train)
    return model
