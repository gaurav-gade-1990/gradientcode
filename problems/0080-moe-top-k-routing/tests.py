import numpy as np


def cases():
    rng = np.random.default_rng(80)
    ex_experts = np.array([np.eye(2), 2 * np.eye(2), -np.eye(2)])
    tie_router = rng.normal(size=(3, 2))
    tie_router = np.stack([tie_router[:, 0], tie_router[:, 1], tie_router[:, 0], tie_router[:, 1]], axis=1)  # e0 == e2, e1 == e3
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"x": np.array([[1.0, 0.0], [0.0, 1.0]]), "W_router": np.array([[2.0, 0.0, 1.0], [0.0, 1.0, 0.0]]),
                  "experts": ex_experts, "k": 2},
         "explanation": "Token 0 has logits [2, 0, 1], so it picks experts [0, 2]. Token 1 has logits [0, 1, 0]: expert 1 first, "
                        "then a tie between experts 0 and 2 that goes to the lower index, 0."},
        {"name": "Example 2", "hidden": False,
         "args": {"x": np.array([[1.0, 2.0], [-1.0, 0.5], [0.0, 0.0]]), "W_router": np.array([[1.0, -1.0], [0.5, 0.5]]),
                  "experts": np.array([[[1.0, 0.0], [0.0, 1.0]], [[0.0, 1.0], [1.0, 0.0]]]), "k": 1},
         "explanation": "With k = 1 every gate is 1 (Switch routing). Token 2 has equal logits, so it goes to expert 0."},
        {"name": "top-2 of 8", "args": {"x": rng.normal(size=(10, 6)), "W_router": rng.normal(size=(6, 8)),
                                        "experts": rng.normal(size=(8, 6, 4)) * 0.5, "k": 2}},
        {"name": "duplicate router columns", "args": {"x": rng.normal(size=(5, 3)), "W_router": tie_router,
                                                      "experts": rng.normal(size=(4, 3, 3)), "k": 3}},
        {"name": "k equals E", "args": {"x": rng.normal(size=(4, 5)), "W_router": rng.normal(size=(5, 4)),
                                        "experts": rng.normal(size=(4, 5, 2)), "k": 4}},
        {"name": "large router logits", "args": {"x": rng.normal(size=(6, 4)) * 30, "W_router": rng.normal(size=(4, 6)) * 30,
                                                 "experts": rng.normal(size=(6, 4, 3)), "k": 2}},
        {"name": "single token", "args": {"x": rng.normal(size=(1, 4)), "W_router": rng.normal(size=(4, 5)),
                                          "experts": rng.normal(size=(5, 4, 4)), "k": 2}},
        {"name": "uniform router", "args": {"x": rng.normal(size=(6, 3)), "W_router": np.zeros((3, 4)),
                                            "experts": rng.normal(size=(4, 3, 2)), "k": 2}},
        {"name": "many tokens top-4 of 16", "args": {"x": rng.normal(size=(32, 8)), "W_router": rng.normal(size=(8, 16)),
                                                     "experts": rng.normal(size=(16, 8, 8)) * 0.3, "k": 4}},
    ]
