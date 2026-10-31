import numpy as np


def dropout(x: np.ndarray, keep_prob: float, u: np.ndarray, train: bool = True) -> np.ndarray:
    if not train:
        return np.array(x, dtype=float)
    mask = u < keep_prob
    return x * mask / keep_prob
