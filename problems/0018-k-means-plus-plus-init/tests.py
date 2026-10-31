import numpy as np


def cases():
    rng = np.random.default_rng(18)
    centers = np.array([[0.0, 0.0], [6.0, 0.0], [0.0, 6.0], [6.0, 6.0]])
    Xb = centers[rng.integers(0, 4, size=80)] + 0.7 * rng.normal(size=(80, 2))
    X5 = rng.normal(size=(200, 5))
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"X": np.array([[0.0], [1.0], [3.0]]), "k": 2, "u": np.array([0.1, 0.5])},
         "explanation": "c0 = floor(0.1 * 3) = 0. D2 = [0, 1, 9], so S = [0, 1, 10] and tau = 0.5 * 10 = 5. The first S > 5 is at index 2."},
        {"name": "Example 2", "hidden": False,
         "args": {"X": np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 2.0], [5.0, 5.0]]), "k": 3, "u": np.array([0.6, 0.0, 0.99])},
         "explanation": "c0 = floor(0.6 * 4) = 2. With u = 0 the target is 0, and index 0 is the first whose S exceeds 0 (D2[0] = 4). Then u = 0.99 lands near the end of the cumulative mass."},
        {"name": "single center", "args": {"X": Xb, "k": 1, "u": np.array([0.731])}},
        {"name": "four blobs", "args": {"X": Xb, "k": 4, "u": rng.random(4)}},
        {"name": "u zero after first center", "args": {"X": np.array([[2.0], [0.0], [5.0], [9.0]]), "k": 3, "u": np.array([0.0, 0.0, 0.0])}},
        {"name": "target on a boundary", "args": {"X": np.array([[0.0], [1.0], [2.0], [3.0]]), "k": 2, "u": np.array([0.0, 1.0 / 14.0])}},
        {"name": "duplicate points", "args": {"X": np.array([[0.0, 0.0], [0.0, 0.0], [1.0, 1.0], [1.0, 1.0], [4.0, 0.0]]), "k": 3, "u": np.array([0.3, 0.5, 0.2])}},
        {"name": "k equals distinct count", "args": {"X": np.array([[1.0], [2.0], [4.0], [8.0]]), "k": 4, "u": np.array([0.9, 0.1, 0.6, 0.3])}},
        {"name": "5d many centers", "args": {"X": X5, "k": 10, "u": rng.random(10)}},
    ]
