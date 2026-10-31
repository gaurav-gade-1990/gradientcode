import numpy as np


def params(rng, d, d_ff, scale=None, ln_random=True):
    s = scale if scale is not None else 1.0 / np.sqrt(d)
    p = {}
    for n in ("ln1", "ln2"):
        p[n + "_g"] = 1.0 + 0.2 * rng.normal(size=d) if ln_random else np.ones(d)
        p[n + "_b"] = 0.1 * rng.normal(size=d) if ln_random else np.zeros(d)
    for n in ("W_q", "W_k", "W_v", "W_o"):
        p[n] = rng.normal(size=(d, d)) * s
    p["W1"] = rng.normal(size=(d, d_ff)) * s
    p["b1"] = 0.1 * rng.normal(size=d_ff)
    p["W2"] = rng.normal(size=(d_ff, d)) / np.sqrt(d_ff)
    p["b2"] = 0.1 * rng.normal(size=d)
    return p


def cases():
    rng = np.random.default_rng(68)
    ex1 = {"ln1_g": np.ones(2), "ln1_b": np.zeros(2), "ln2_g": np.ones(2), "ln2_b": np.zeros(2),
           "W_q": np.eye(2), "W_k": np.eye(2), "W_v": np.eye(2), "W_o": np.eye(2),
           "W1": np.array([[1.0, 0.0], [0.0, 1.0]]), "b1": np.zeros(2),
           "W2": np.array([[0.5, 0.0], [0.0, 0.5]]), "b2": np.zeros(2)}
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"x": np.array([[[1.0, -1.0], [3.0, 1.0]]]), "params": ex1, "num_heads": 1},
         "explanation": "Both tokens normalize to about [1, -1]. Token 0 only sees itself, so a = x + [1, -1]. The MLP then adds 0.5 * GELU(LN(a))."},
        {"name": "Example 2", "hidden": False,
         "args": {"x": np.array([[[0.5, -0.2, 0.1, 0.3], [0.0, 0.4, -0.6, 0.2], [0.3, 0.3, -0.1, -0.5]]]),
                  "params": params(rng, 4, 8), "num_heads": 2},
         "explanation": "Two heads of width 2, d_ff = 8, with random weights."},
        {"name": "single token", "args": {"x": rng.normal(size=(2, 1, 8)), "params": params(rng, 8, 16), "num_heads": 2}},
        {"name": "four heads", "args": {"x": rng.normal(size=(2, 6, 8)), "params": params(rng, 8, 32), "num_heads": 4}},
        {"name": "identity layernorm", "args": {"x": rng.normal(size=(1, 5, 6)) * 3 + 2, "params": params(rng, 6, 12, ln_random=False), "num_heads": 3}},
        {"name": "large activations", "args": {"x": rng.normal(size=(2, 7, 8)) * 10, "params": params(rng, 8, 16, scale=1.5), "num_heads": 2}},
        {"name": "wider", "args": {"x": rng.normal(size=(2, 10, 16)), "params": params(rng, 16, 32), "num_heads": 4}},
    ]
