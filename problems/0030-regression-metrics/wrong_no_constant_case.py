import numpy as np


def regression_metrics(y_true, y_pred):
    e = y_true - y_pred
    mse = float(np.mean(e ** 2))
    r2 = 1.0 - np.sum(e ** 2) / np.sum((y_true - y_true.mean()) ** 2)
    return {"mse": mse, "rmse": float(np.sqrt(mse)), "mae": float(np.mean(np.abs(e))), "r2": float(r2)}
