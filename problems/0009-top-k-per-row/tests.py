import numpy as np


def cases():
    rng = np.random.default_rng(9)
    return [
        {"name": "Example 1", "hidden": False, "args": {"x": np.array([[1.0, 5.0, 3.0, 4.0], [9.0, 2.0, 8.0, 0.0]]), "k": 2},
         "explanation": "Row 0: 5 at index 1, then 4 at index 3. Row 1: 9 at index 0, then 8 at index 2."},
        {"name": "Example 2", "hidden": False, "args": {"x": np.array([[2.0, 7.0, 7.0, 2.0, 7.0]]), "k": 4},
         "explanation": "The three 7s tie, so they come out in index order 1, 2, 4. The fourth slot is a tie between the 2s at 0 and 3, and index 0 wins."},
        {"name": "all equal", "args": {"x": np.zeros((3, 6)), "k": 3}},
        {"name": "k equals m", "args": {"x": rng.normal(size=(4, 5)), "k": 5}},
        {"name": "k is 1", "args": {"x": np.array([[3.0, 3.0, 1.0], [-1.0, -2.0, -1.0]]), "k": 1}},
        {"name": "many ties", "args": {"x": rng.integers(0, 3, size=(6, 10)).astype(float), "k": 4}},
        {"name": "negatives", "args": {"x": -rng.random((5, 8)) * 10, "k": 3}},
        {"name": "single column", "args": {"x": np.array([[4.0], [-1.0]]), "k": 1}},
        {"name": "tied block in a long row", "args": {"x": np.array([[1.0] * 10 + [2.0] * 10 + [1.0] * 10]), "k": 12}},
        {"name": "wide rows", "args": {"x": np.round(rng.normal(size=(20, 200)), 1), "k": 10}},
    ]
