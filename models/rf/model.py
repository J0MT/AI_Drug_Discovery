from sklearn.ensemble import RandomForestRegressor


def train(X_train, y_train):
    model = RandomForestRegressor(n_estimators=10, random_state=42)
    model.fit(X_train, y_train)
    return model
