import numpy as np


def cases():
    rng = np.random.default_rng(8)
    return [
        {"name": "Example 1", "hidden": False, "args": {"x": np.arange(1, 7), "window": 3, "stride": 1},
         "explanation": "Length 6, window 3, stride 1: (6 - 3) // 1 + 1 = 4 windows."},
        {"name": "Example 2", "hidden": False, "args": {"x": np.arange(10), "window": 4, "stride": 3},
         "explanation": "Starts 0, 3, 6. A window at 9 would need indices 9..12, so it is dropped: (10 - 4) // 3 + 1 = 3."},
        {"name": "Example 3", "hidden": False, "args": {"x": np.array([0.5, -1.0, 2.0]), "window": 5, "stride": 1},
         "explanation": "The signal is shorter than the window, so there are no full windows: shape (0, 5)."},
        {"name": "window equals length", "args": {"x": np.array([3, 1, 4, 1, 5]), "window": 5, "stride": 2}},
        {"name": "exact fit", "args": {"x": np.arange(12) * 10, "window": 4, "stride": 4}},
        {"name": "stride larger than window", "args": {"x": np.arange(20), "window": 2, "stride": 5}},
        {"name": "one leftover sample", "args": {"x": np.arange(11), "window": 3, "stride": 4}},
        {"name": "window 1", "args": {"x": np.array([7, 8, 9, 10]), "window": 1, "stride": 2}},
        {"name": "empty signal", "args": {"x": np.zeros(0), "window": 2, "stride": 1}},
        {"name": "float signal", "args": {"x": rng.normal(size=50), "window": 8, "stride": 6}},
        {"name": "long signal", "args": {"x": rng.integers(-100, 100, size=3000), "window": 64, "stride": 32}},
    ]
