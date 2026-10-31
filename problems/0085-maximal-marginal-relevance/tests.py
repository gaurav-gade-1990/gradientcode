import numpy as np


def cases():
    rng = np.random.default_rng(85)
    base = rng.normal(size=(5, 6))
    near_dups = np.vstack([base, base[[0, 0, 2]] + 0.01 * rng.normal(size=(3, 6))])
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"query": np.array([1.0, 0.0]),
                  "docs": np.array([[1.0, 0.1], [1.0, 0.12], [0.6, 0.8], [0.0, 1.0]]), "k": 3, "lam": 0.5},
         "explanation": "Doc 0 is the most relevant. Doc 1 is almost a copy of doc 0, but at lam = 0.5 its high relevance still outweighs the redundancy penalty: it scores -0.0035 against doc 2's -0.0383, so doc 1 is picked second and doc 2 third."},
        {"name": "Example 2", "hidden": False,
         "args": {"query": np.array([1.0, 0.0]),
                  "docs": np.array([[1.0, 0.1], [1.0, 0.12], [0.6, 0.8], [0.0, 1.0]]), "k": 3, "lam": 1.0},
         "explanation": "With lam = 1 there is no redundancy penalty, so MMR is plain ranking by relevance."},
        {"name": "lam = 0", "args": {"query": np.array([0.3, -1.0, 2.0]), "docs": rng.normal(size=(8, 3)), "k": 5, "lam": 0.0}},
        {"name": "negative similarities", "args": {"query": np.array([1.0, 0.0]),
                                                    "docs": np.array([[1.0, 0.0], [-1.0, 0.2], [-1.0, -0.2], [0.0, 1.0], [0.2, -1.0]]), "k": 4, "lam": 0.3}},
        {"name": "exact duplicates tie", "args": {"query": np.array([1.0, 1.0]),
                                                   "docs": np.array([[0.0, 1.0], [1.0, 0.0], [0.0, 1.0], [1.0, 0.0], [2.0, 2.0]]), "k": 5, "lam": 0.6}},
        {"name": "zero vector doc", "args": {"query": np.array([1.0, 2.0, 0.5]),
                                              "docs": np.array([[0.0, 0.0, 0.0], [1.0, 2.0, 0.4], [-1.0, -2.0, 0.0], [1.0, 2.1, 0.5], [0.0, 0.0, 1.0]]), "k": 5, "lam": 0.4}},
        {"name": "near duplicates", "args": {"query": base[0] + 0.5 * base[2], "docs": near_dups, "k": 6, "lam": 0.7}},
        {"name": "k = 1", "args": {"query": rng.normal(size=4), "docs": rng.normal(size=(10, 4)), "k": 1, "lam": 0.2}},
        {"name": "low lambda random", "args": {"query": rng.normal(size=8), "docs": rng.normal(size=(40, 8)), "k": 12, "lam": 0.25}},
        {"name": "larger pool", "args": {"query": rng.normal(size=16), "docs": rng.normal(size=(300, 16)), "k": 20, "lam": 0.6}},
    ]
