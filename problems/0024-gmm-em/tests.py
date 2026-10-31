import numpy as np


def cases():
    rng = np.random.default_rng(24)
    z = rng.integers(0, 2, size=120)
    X1 = np.where(z == 0, rng.normal(-2.0, 0.7, size=120), rng.normal(3.0, 1.2, size=120))[:, None]
    centers = np.array([[0.0, 0.0], [5.0, 5.0], [0.0, 6.0]])
    z2 = rng.integers(0, 3, size=150)
    X2 = centers[z2] + rng.normal(size=(150, 2)) * np.array([[1.0, 0.5], [0.8, 0.8], [0.4, 1.5]])[z2]
    Xc = np.hstack([rng.normal(size=(40, 1)), np.full((40, 1), 2.0)])
    Xc[20:, 0] += 6.0
    X3 = rng.normal(size=(100, 3)) + np.where(rng.random((100, 1)) < 0.3, 4.0, 0.0)
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"X": np.array([[0.0], [1.0], [10.0], [11.0]]), "means": np.array([[0.0], [10.0]]), "variances": np.array([[1.0], [1.0]]),
                  "weights": np.array([0.5, 0.5]), "n_iter": 1},
         "explanation": "Each pair of points is almost entirely claimed by the nearby component. The means move to about 0.5 and 10.5, the variances to about 0.25, and the weights stay near 0.5. The recorded log-likelihood is for the initial parameters."},
        {"name": "Example 2", "hidden": False,
         "args": {"X": np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0], [4.0, 4.0], [5.0, 4.0]]),
                  "means": np.array([[0.5, 0.5], [4.0, 4.0]]), "variances": np.array([[1.0, 1.0], [1.0, 1.0]]),
                  "weights": np.array([0.5, 0.5]), "n_iter": 5}},
        {"name": "1d two components", "args": {"X": X1, "means": np.array([[-1.0], [1.0]]), "variances": np.array([[1.0], [1.0]]),
                                                 "weights": np.array([0.5, 0.5]), "n_iter": 30}},
        {"name": "2d three components", "args": {"X": X2, "means": X2[:3].copy(), "variances": np.ones((3, 2)),
                                                  "weights": np.array([0.2, 0.3, 0.5]), "n_iter": 25}},
        {"name": "single iteration uneven weights", "args": {"X": X2, "means": np.array([[1.0, 1.0], [4.0, 4.0], [0.0, 5.0]]),
                                                              "variances": np.array([[2.0, 0.5], [1.0, 1.0], [0.3, 3.0]]), "weights": np.array([0.6, 0.3, 0.1]), "n_iter": 1}},
        {"name": "far-away start", "args": {"X": X1, "means": np.array([[-500.0], [500.0]]), "variances": np.array([[0.01], [0.01]]),
                                             "weights": np.array([0.5, 0.5]), "n_iter": 10}},
        {"name": "constant feature", "args": {"X": Xc, "means": np.array([[0.0, 2.0], [6.0, 2.0]]), "variances": np.ones((2, 2)),
                                               "weights": np.array([0.5, 0.5]), "n_iter": 8}},
        {"name": "one component", "args": {"X": X3, "means": np.zeros((1, 3)), "variances": np.ones((1, 3)), "weights": np.array([1.0]), "n_iter": 3}},
        {"name": "3d mixture", "args": {"X": X3, "means": X3[[0, 50]].copy(), "variances": np.ones((2, 3)), "weights": np.array([0.5, 0.5]),
                                         "n_iter": 40, "reg_covar": 1e-3}},
    ]
