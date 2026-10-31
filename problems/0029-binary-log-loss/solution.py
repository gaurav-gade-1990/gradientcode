import numpy as np


def log_loss(y_true: np.ndarray, p: np.ndarray, eps: float = 1e-15) -> float:
    y = np.asarray(y_true, dtype=float)
    q = np.clip(p, eps, 1 - eps)
    return float(-np.mean(y * np.log(q) + (1 - y) * np.log(1 - q)))
