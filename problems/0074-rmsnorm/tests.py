import numpy as np


def cases():
    rng = np.random.default_rng(74)
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"x": np.array([3.0, 4.0]), "weight": np.array([1.0, 1.0]), "eps": 0.0001},
         "explanation": "mean(x^2) = (9 + 16) / 2 = 12.5, so rms = sqrt(12.5001) ~ 3.5355 and the output is x / 3.5355."},
        {"name": "Example 2", "hidden": False,
         "args": {"x": np.array([[1.0, 2.0, 3.0], [-2.0, 0.0, 2.0]]), "weight": np.array([1.0, 0.5, 2.0])},
         "explanation": "Each row is normalized by its own RMS, then scaled elementwise by weight. No mean is subtracted."},
        {"name": "all zeros row", "args": {"x": np.array([[0.0, 0.0, 0.0, 0.0], [1.0, -1.0, 1.0, -1.0]]),
                                           "weight": np.array([1.0, 2.0, 3.0, 4.0]), "eps": 1e-5}},
        {"name": "tiny values eps matters", "args": {"x": rng.normal(size=(3, 6)) * 1e-3, "weight": np.ones(6), "eps": 1e-6}},
        {"name": "rows with offsets", "args": {"x": rng.normal(size=(4, 5)) + np.array([[5.0], [-3.0], [0.0], [10.0]]),
                                              "weight": rng.normal(size=5)}},
        {"name": "rows with different scales", "args": {"x": rng.normal(size=(3, 8)) * np.array([[0.1], [1.0], [50.0]]),
                                                        "weight": rng.random(8) + 0.5}},
        {"name": "3d batch", "args": {"x": rng.normal(size=(2, 3, 16)), "weight": rng.normal(size=16), "eps": 1e-5}},
        {"name": "d = 1", "args": {"x": np.array([[2.0], [-0.5]]), "weight": np.array([3.0])}},
    ]
