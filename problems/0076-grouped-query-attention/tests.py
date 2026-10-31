import numpy as np


def cases():
    rng = np.random.default_rng(76)
    ex1_q = np.array([[[[1.0, 0.0], [0.0, 1.0]], [[0.0, 2.0], [2.0, 0.0]]]])
    ex1_k = np.array([[[[1.0, 0.0], [0.0, 1.0]]]])
    ex1_v = np.array([[[[1.0, 2.0], [3.0, 4.0]]]])
    return [
        {"name": "Example 1", "hidden": False, "args": {"q": ex1_q, "k": ex1_k, "v": ex1_v},
         "explanation": "n_q = 2, n_kv = 1: both query heads share the single K/V head (multi-query attention). "
                        "Position 0 only sees itself, so its output is v[0] = [1, 2] in both heads."},
        {"name": "Example 2", "hidden": False,
         "args": {"q": rng.integers(-2, 3, size=(1, 4, 3, 2)).astype(float),
                  "k": rng.integers(-2, 3, size=(1, 2, 3, 2)).astype(float),
                  "v": rng.integers(-2, 3, size=(1, 2, 3, 2)).astype(float)},
         "explanation": "n_q = 4, n_kv = 2: query heads 0 and 1 use K/V head 0; heads 2 and 3 use K/V head 1."},
        {"name": "n_kv equals n_q (plain MHA)", "args": {"q": rng.normal(size=(2, 3, 5, 4)), "k": rng.normal(size=(2, 3, 5, 4)),
                                                         "v": rng.normal(size=(2, 3, 5, 4))}},
        {"name": "8 query heads 2 kv heads", "args": {"q": rng.normal(size=(1, 8, 6, 8)), "k": rng.normal(size=(1, 2, 6, 8)),
                                                      "v": rng.normal(size=(1, 2, 6, 8))}},
        {"name": "6 query heads 3 kv heads", "args": {"q": rng.normal(size=(2, 6, 4, 4)), "k": rng.normal(size=(2, 3, 4, 4)),
                                                      "v": rng.normal(size=(2, 3, 4, 4))}},
        {"name": "single position", "args": {"q": rng.normal(size=(1, 4, 1, 3)), "k": rng.normal(size=(1, 2, 1, 3)),
                                             "v": rng.normal(size=(1, 2, 1, 3))}},
        {"name": "large logits", "args": {"q": rng.normal(size=(1, 4, 5, 4)) * 40, "k": rng.normal(size=(1, 1, 5, 4)) * 40,
                                          "v": rng.normal(size=(1, 1, 5, 4))}},
        {"name": "longer sequence", "args": {"q": rng.normal(size=(1, 8, 16, 8)), "k": rng.normal(size=(1, 4, 16, 8)),
                                             "v": rng.normal(size=(1, 4, 16, 8))}},
    ]
