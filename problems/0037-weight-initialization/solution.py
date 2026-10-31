import numpy as np


def init_weights(fan_in: int, fan_out: int, u: np.ndarray, z: np.ndarray) -> dict:
    a = float(np.sqrt(6.0 / (fan_in + fan_out)))
    std = float(np.sqrt(2.0 / fan_in))
    return {
        "xavier_limit": a,
        "xavier": (2.0 * u - 1.0) * a,
        "he_std": std,
        "he": z * std,
    }
