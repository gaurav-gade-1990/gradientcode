import numpy as np


def init_weights(fan_in, fan_out, u, z):
    # Uses the Xavier *normal* std as if it were the uniform limit.
    a = float(np.sqrt(2.0 / (fan_in + fan_out)))
    std = float(np.sqrt(2.0 / fan_in))
    return {"xavier_limit": a, "xavier": (2.0 * u - 1.0) * a, "he_std": std, "he": z * std}
