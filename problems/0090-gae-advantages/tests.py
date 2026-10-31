import numpy as np


def cases():
    rng = np.random.default_rng(90)
    T, N = 64, 4
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"rewards": np.array([1.0, 1.0, 1.0]), "values": np.array([0.5, 0.5, 0.5]), "dones": np.array([False, False, False]),
                  "last_value": 0.5, "gamma": 0.9, "lam": 0.8},
         "explanation": "Every delta is 1 + 0.9 * 0.5 - 0.5 = 0.95. Backward: A_2 = 0.95, A_1 = 0.95 + 0.72 * 0.95 = 1.634, A_0 = 0.95 + 0.72 * 1.634 = 2.12648."},
        {"name": "Example 2", "hidden": False,
         "args": {"rewards": np.array([0.0, 1.0, 0.0, 2.0]), "values": np.array([1.0, 2.0, 1.0, 0.0]), "dones": np.array([False, True, False, False]),
                  "last_value": 3.0, "gamma": 1.0, "lam": 1.0},
         "explanation": "The episode ends after step 1, so delta_1 = 1 - 2 = -1 and the recursion restarts there. Steps 2 and 3 bootstrap from last_value = 3."},
        {"name": "lam = 0 is one-step TD", "args": {"rewards": rng.normal(size=10), "values": rng.normal(size=10), "dones": rng.random(10) < 0.2,
                                                     "last_value": 0.7, "gamma": 0.99, "lam": 0.0}},
        {"name": "done on last step", "args": {"rewards": np.array([1.0, 2.0, 3.0]), "values": np.array([0.1, 0.2, 0.3]), "dones": np.array([0.0, 0.0, 1.0]),
                                                "last_value": 100.0, "gamma": 0.95, "lam": 0.9}},
        {"name": "done on first step", "args": {"rewards": np.array([5.0, 0.0, 0.0, 1.0]), "values": np.array([2.0, 1.0, 1.0, 1.0]), "dones": np.array([1.0, 0.0, 0.0, 0.0]),
                                                 "last_value": -1.0, "gamma": 0.9, "lam": 0.95}},
        {"name": "single step", "args": {"rewards": np.array([0.5]), "values": np.array([0.2]), "dones": np.array([False]), "last_value": 1.0}},
        {"name": "consecutive dones", "args": {"rewards": np.array([1.0, -1.0, 2.0, 0.5, 0.0]), "values": np.array([0.0, 0.3, -0.2, 0.4, 0.1]),
                                                "dones": np.array([True, True, False, True, False]), "last_value": 0.6, "gamma": 0.97, "lam": 0.9}},
        {"name": "parallel envs", "args": {"rewards": rng.normal(size=(T, N)), "values": rng.normal(size=(T, N)), "dones": rng.random((T, N)) < 0.05,
                                            "last_value": rng.normal(size=N), "gamma": 0.99, "lam": 0.95}},
        {"name": "long rollout", "args": {"rewards": rng.normal(size=2048), "values": rng.normal(size=2048), "dones": rng.random(2048) < 0.01,
                                           "last_value": 0.25, "gamma": 0.999, "lam": 0.97}},
    ]
