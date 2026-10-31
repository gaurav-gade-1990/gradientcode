import numpy as np


def cases():
    rng = np.random.default_rng(30)
    x = rng.uniform(0, 10, size=100)
    y = 3 * x + 2 + rng.normal(size=100)
    return [
        {"name": "Example 1", "hidden": False, "args": {"y_true": np.array([3.0, -0.5, 2.0, 7.0]), "y_pred": np.array([2.5, 0.0, 2.0, 8.0])},
         "explanation": "Residuals 0.5, -0.5, 0, -1. MSE = 0.375, MAE = 0.5, and R^2 = 1 - 1.5 / 29.1875, about 0.9486."},
        {"name": "Example 2", "hidden": False, "args": {"y_true": np.array([1.0, 2.0, 3.0]), "y_pred": np.array([3.0, 2.0, 1.0])},
         "explanation": "Worse than predicting the mean: SS_res = 8 and SS_tot = 2, so R^2 = -3."},
        {"name": "perfect", "args": {"y_true": np.array([1.5, -2.0, 4.0]), "y_pred": np.array([1.5, -2.0, 4.0])}},
        {"name": "constant target, perfect", "args": {"y_true": np.full(4, 5.0), "y_pred": np.full(4, 5.0)}},
        {"name": "constant target, off", "args": {"y_true": np.full(4, 5.0), "y_pred": np.array([5.0, 4.0, 6.0, 5.5])}},
        {"name": "predict the mean", "args": {"y_true": np.array([1.0, 2.0, 6.0]), "y_pred": np.full(3, 3.0)}},
        {"name": "single sample", "args": {"y_true": np.array([2.0]), "y_pred": np.array([-1.0])}},
        {"name": "biased predictions", "args": {"y_true": np.array([0.0, 1.0, 2.0, 3.0, 4.0]), "y_pred": np.array([2.0, 3.0, 4.0, 5.0, 6.0])}},
        {"name": "noisy line", "args": {"y_true": y, "y_pred": 3 * x + 2}},
    ]
