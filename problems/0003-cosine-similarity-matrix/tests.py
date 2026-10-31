import numpy as np


def cases():
    rng = np.random.default_rng(3)
    zero_rows_a = rng.normal(size=(5, 4))
    zero_rows_a[[1, 3]] = 0.0
    zero_rows_b = rng.normal(size=(6, 4))
    zero_rows_b[0] = 0.0
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"A": np.array([[1.0, 0.0], [1.0, 1.0]]), "B": np.array([[0.0, 2.0], [3.0, 0.0], [-1.0, -1.0]])},
         "explanation": "Row [1, 1] against [-1, -1] points the opposite way, so it scores -1. [1, 0] against [0, 2] is orthogonal: 0."},
        {"name": "Example 2", "hidden": False,
         "args": {"A": np.array([[0.0, 0.0, 0.0], [1.0, 2.0, 2.0]]), "B": np.array([[2.0, 4.0, 4.0]])},
         "explanation": "The zero row gets similarity 0. [1, 2, 2] and [2, 4, 4] are parallel, so they score 1."},
        {"name": "random", "args": {"A": rng.normal(size=(7, 5)), "B": rng.normal(size=(4, 5))}},
        {"name": "zero rows on both sides", "args": {"A": zero_rows_a, "B": zero_rows_b}},
        {"name": "different scales per column", "args": {"A": rng.normal(size=(6, 3)) * np.array([100.0, 1.0, 0.01]),
                                                         "B": rng.normal(size=(5, 3)) * np.array([0.01, 1.0, 100.0])}},
        {"name": "same set", "args": {"A": np.arange(12.0).reshape(4, 3) - 5, "B": np.arange(12.0).reshape(4, 3) - 5}},
        {"name": "single column", "args": {"A": np.array([[2.0], [-3.0], [0.0]]), "B": np.array([[5.0], [-0.5]])}},
        {"name": "larger", "args": {"A": rng.normal(size=(40, 16)), "B": rng.normal(size=(30, 16))}},
    ]
