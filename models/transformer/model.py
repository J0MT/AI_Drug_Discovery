import torch
import torch.nn as nn


class TransformerRegressor(nn.Module):
    def __init__(self, input_dim, d_model, nhead, num_layers):
        super().__init__()
        self.input_fc = nn.Linear(input_dim, d_model)
        encoder_layer = nn.TransformerEncoderLayer(d_model, nhead, batch_first=True)
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers)
        self.output = nn.Linear(d_model, 1)

    def forward(self, x):
        x = self.input_fc(x).unsqueeze(1)
        x = self.transformer(x)
        return self.output(x[:, 0, :])


def train(X_train, y_train, config=None):
    # Default config for testing when no config is provided
    if config is None:
        config = {
            "input_dim": X_train.shape[1],
            "d_model": 64,
            "nhead": 4,
            "num_layers": 2,
            "lr": 0.001,
            "epochs": 10,
        }

    required_keys = ["input_dim", "d_model", "nhead", "num_layers", "lr", "epochs"]
    for k in required_keys:
        if k not in config:
            raise ValueError(f"Missing config key: {k}")

    model = TransformerRegressor(
        input_dim=config["input_dim"],
        d_model=config["d_model"],
        nhead=config["nhead"],
        num_layers=config["num_layers"],
    )
    optimizer = torch.optim.Adam(model.parameters(), lr=config["lr"])
    criterion = nn.MSELoss()

    X_tensor = torch.tensor(X_train.values, dtype=torch.float32)
    y_tensor = torch.tensor(y_train.values, dtype=torch.float32).unsqueeze(1)

    for _ in range(config["epochs"]):
        model.train()
        optimizer.zero_grad()
        output = model(X_tensor)
        loss = criterion(output, y_tensor)
        loss.backward()
        optimizer.step()

    return model
