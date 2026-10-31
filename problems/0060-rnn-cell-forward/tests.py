import numpy as np


def case(rng, B, T, d, H, scale=0.5):
    return {
        "x": rng.normal(size=(B, T, d)),
        "h0": rng.normal(size=(B, H)) * 0.5,
        "W_xh": rng.normal(size=(d, H)) * scale,
        "W_hh": rng.normal(size=(H, H)) * scale,
        "b": rng.normal(size=H) * 0.1,
    }


def cases():
    rng = np.random.default_rng(60)
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"x": np.array([[[1.0], [0.0], [-1.0]]]), "h0": np.array([[0.0]]),
                  "W_xh": np.array([[0.5]]), "W_hh": np.array([[1.0]]), "b": np.array([0.0])},
         "explanation": "h1 = tanh(0.5) = 0.4621, h2 = tanh(0.4621) = 0.4319, h3 = tanh(-0.5 + 0.4319) = -0.0680."},
        {"name": "Example 2", "hidden": False,
         "args": {"x": np.array([[[1.0, 0.0], [0.0, 1.0]]]), "h0": np.array([[0.1, -0.2]]),
                  "W_xh": np.array([[1.0, 0.0], [0.0, 1.0]]), "W_hh": np.array([[0.0, 1.0], [-0.5, 0.0]]),
                  "b": np.array([0.0, 0.1])},
         "explanation": "W_hh is not symmetric, so h @ W_hh and h @ W_hh.T give different answers."},
        {"name": "single step", "args": case(rng, 3, 1, 4, 5)},
        {"name": "batch of sequences", "args": case(rng, 4, 10, 3, 6)},
        {"name": "nonzero h0 matters", "args": case(rng, 2, 6, 2, 3, scale=1.0)},
        {"name": "long sequence", "args": case(rng, 2, 40, 3, 6, scale=0.4)},
        {"name": "saturating weights", "args": case(rng, 3, 8, 4, 4, scale=3.0)},
        {"name": "wide hidden", "args": case(rng, 1, 8, 8, 16, scale=0.3)},
    ]
