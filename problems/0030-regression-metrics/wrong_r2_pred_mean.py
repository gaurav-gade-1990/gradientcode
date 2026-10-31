import numpy as np


def regression_metrics(y_true, y_pred):
    e = y_true - y_pred
    mse = float(np.mean(e ** 2))
    ss_res = float(np.sum(e ** 2))
    ss_tot = float(np.sum((y_true - y_pred.mean()) ** 2))
    r2 = (1.0 if ss_res == 0 else 0.0) if ss_tot == 0 else 1.0 - ss_res / ss_tot
    return {"mse": mse, "rmse": float(np.sqrt(mse)), "mae": float(np.mean(np.abs(e))), "r2": r2}
