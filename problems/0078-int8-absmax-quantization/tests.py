import numpy as np


def cases():
    rng = np.random.default_rng(78)
    halves = np.array([[127.0, 2.5, -2.5, 0.5, -0.5, 3.5, -126.5, 1.4]])
    big = rng.normal(size=(32, 64)) * rng.random((32, 1)) * 5
    return [
        {"name": "Example 1", "hidden": False, "args": {"W": np.array([[1.27, -0.635, 0.3]])},
         "explanation": "absmax = 1.27, so scale = 0.01. W / scale = [127, -63.5, 30], which rounds half away from zero to [127, -64, 30]."},
        {"name": "Example 2", "hidden": False, "args": {"W": np.array([[2.0, -1.0, 0.5], [0.0, 0.0, 0.0], [-4.0, 1.0, 3.0]])},
         "explanation": "Each row has its own scale. The all-zero row gets scale 1 and codes 0."},
        {"name": "exact halves", "args": {"W": halves},
         "explanation": "Scale is exactly 1, so every .5 value is a rounding tie."},
        {"name": "halves at another scale", "args": {"W": np.array([[254.0, 5.0, -5.0, 1.0, -3.0, 7.0], [-127.0, 0.5, 1.5, -1.5, 2.5, 0.0]])}},
        {"name": "negative absmax row", "args": {"W": np.array([[-3.0, 1.0, 2.0], [0.13, -0.2, 0.05]])}},
        {"name": "rows with very different ranges", "args": {"W": rng.normal(size=(4, 10)) * np.array([[1e-3], [1.0], [100.0], [0.5]])}},
        {"name": "single element rows", "args": {"W": np.array([[5.0], [-2.0], [0.0]])}},
        {"name": "outlier row", "args": {"W": np.vstack([rng.normal(size=(1, 16)), rng.normal(size=(1, 16)) * 0.01,
                                                         np.r_[rng.normal(size=15) * 0.1, 900.0][None, :]])}},
        {"name": "zero rows mixed", "args": {"W": np.array([[0.0, 0.0], [1.0, -1.0], [0.0, 0.0]])}},
        {"name": "large matrix", "args": {"W": big}},
        {"name": "divide, not reciprocal", "args": {"W": np.array([[0.3, 0.15, -0.15], [2.3, 1.15, -1.15]])},
         "explanation": "W / s gives exactly 63.5 in row 0 but 63.49999999999999 in row 1, so the codes are 64 and 63. Multiplying by 1 / s swaps them."},
    ]
