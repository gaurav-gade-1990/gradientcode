import numpy as np


def case(rng, B, T, d, h, causal=False, scale=None):
    s = scale if scale is not None else 1.0 / np.sqrt(d)
    a = {"x": rng.normal(size=(B, T, d))}
    for n in ("W_q", "W_k", "W_v", "W_o"):
        a[n] = rng.normal(size=(d, d)) * s
    a["num_heads"] = h
    if causal:
        a["mask"] = np.tril(np.ones((T, T), dtype=bool))
    return a


def cases():
    rng = np.random.default_rng(65)
    I = np.eye(2)
    ex2 = {"x": np.array([[[1.0, 0.0, 2.0, 0.0], [0.0, 1.0, 0.0, 2.0], [1.0, 1.0, 1.0, 1.0]]]),
           "W_q": np.eye(4), "W_k": np.eye(4), "W_v": np.eye(4), "W_o": np.eye(4), "num_heads": 2,
           "mask": np.tril(np.ones((3, 3), dtype=bool))}
    padmask = np.ones((5, 5), dtype=bool)
    padmask[:, 3:] = False
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"x": np.array([[[1.0, 0.0], [0.0, 1.0]]]), "W_q": I, "W_k": I, "W_v": I, "W_o": I, "num_heads": 1},
         "explanation": "One head with identity weights. Each token scores itself at 1/sqrt(2) and the other at 0."},
        {"name": "Example 2", "hidden": False, "args": ex2,
         "explanation": "Two heads of width 2: head 0 uses columns 0-1 and head 1 uses columns 2-3. The mask is causal, so token 0 only sees itself."},
        {"name": "one head random", "args": case(rng, 2, 5, 6, 1)},
        {"name": "four heads", "args": case(rng, 2, 6, 8, 4)},
        {"name": "causal eight heads", "args": case(rng, 1, 6, 8, 8, causal=True)},
        {"name": "head width 1", "args": case(rng, 2, 4, 4, 4, causal=True)},
        {"name": "key padding mask", "args": dict(case(rng, 3, 5, 6, 3), mask=padmask)},
        {"name": "sharp attention", "args": case(rng, 2, 8, 12, 2, causal=True, scale=3.0)},
        {"name": "single token", "args": case(rng, 4, 1, 8, 2)},
        {"name": "larger", "args": case(rng, 2, 12, 16, 4, causal=True)},
    ]
