import numpy as np


def random_transitions(rng, n, S, A, p_done=0.1):
    out = []
    for _ in range(n):
        out.append((int(rng.integers(S)), int(rng.integers(A)), float(np.round(rng.normal(), 3)),
                    int(rng.integers(S)), bool(rng.random() < p_done)))
    return out


def cases():
    rng = np.random.default_rng(89)
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"Q": np.zeros((3, 2)), "transitions": [(0, 1, 1.0, 1, False), (1, 0, 2.0, 2, True), (0, 1, 0.0, 1, False)],
                  "alpha": 0.5, "gamma": 0.9},
         "explanation": "Q[0,1] = 0.5. Then Q[1,0] = 0.5 * 2 = 1 (done, so no bootstrap). Then Q[0,1] = 0.5 + 0.5 * (0 + 0.9 * 1 - 0.5) = 0.7, using the Q[1,0] just written."},
        {"name": "Example 2", "hidden": False,
         "args": {"Q": np.array([[1.0, 2.0], [3.0, -1.0]]), "transitions": [(0, 0, -1.0, 1, False), (1, 1, 5.0, 0, True)],
                  "alpha": 1.0, "gamma": 0.5},
         "explanation": "With alpha = 1, Q[s,a] is replaced by the target. Q[0,0] = -1 + 0.5 * max(3, -1) = 0.5. Q[1,1] = 5."},
        {"name": "no transitions", "args": {"Q": rng.normal(size=(4, 3)), "transitions": [], "alpha": 0.1, "gamma": 0.99}},
        {"name": "terminal bootstrap ignored", "args": {"Q": np.full((2, 2), 10.0), "transitions": [(0, 0, 1.0, 1, True), (1, 1, 1.0, 0, True)],
                                                         "alpha": 0.3, "gamma": 0.9}},
        {"name": "self loop", "args": {"Q": np.zeros((1, 2)), "transitions": [(0, 0, 1.0, 0, False)] * 6, "alpha": 0.5, "gamma": 0.8}},
        {"name": "chain dependency", "args": {"Q": np.zeros((4, 1)), "transitions": [(2, 0, 1.0, 3, True), (1, 0, 0.0, 2, False), (0, 0, 0.0, 1, False)],
                                               "alpha": 1.0, "gamma": 0.9}},
        {"name": "negative values max", "args": {"Q": -np.abs(rng.normal(size=(3, 4))) - 1, "transitions": [(0, 2, 0.5, 1, False), (1, 3, -0.2, 2, False), (2, 0, 0.0, 0, False)],
                                                  "alpha": 0.4, "gamma": 0.95}},
        {"name": "gamma = 1", "args": {"Q": rng.normal(size=(5, 2)), "transitions": random_transitions(rng, 30, 5, 2), "alpha": 0.2, "gamma": 1.0}},
        {"name": "long stream", "args": {"Q": np.zeros((20, 4)), "transitions": random_transitions(rng, 2000, 20, 4), "alpha": 0.1, "gamma": 0.95}},
    ]
