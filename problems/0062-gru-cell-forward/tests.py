import numpy as np


def case(rng, B, T, d, H, scale=0.5, bias=0.3):
    return {
        "x": rng.normal(size=(B, T, d)),
        "h0": rng.normal(size=(B, H)) * 0.5,
        "W_ih": rng.normal(size=(d, 3 * H)) * scale,
        "W_hh": rng.normal(size=(H, 3 * H)) * scale,
        "b_ih": rng.normal(size=3 * H) * bias,
        "b_hh": rng.normal(size=3 * H) * bias,
    }


def cases():
    rng = np.random.default_rng(62)
    hb = case(rng, 3, 5, 2, 4, scale=0.3)
    hb["b_hh"][8:] = np.array([2.0, -2.0, 1.5, -1.0])
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"x": np.array([[[1.0], [2.0]]]), "h0": np.array([[0.5]]),
                  "W_ih": np.array([[0.0, 0.0, 1.0]]), "W_hh": np.array([[0.0, 0.0, 1.0]]),
                  "b_ih": np.zeros(3), "b_hh": np.zeros(3)},
         "explanation": "r = z = sigmoid(0) = 0.5. Step 1: n = tanh(1 + 0.5*0.5) = 0.8483, h = 0.5*0.8483 + 0.5*0.5 = 0.6742."},
        {"name": "Example 2", "hidden": False,
         "args": {"x": np.array([[[1.0, 0.0]], [[0.0, 1.0]]]), "h0": np.array([[0.0, 0.0], [1.0, -1.0]]),
                  "W_ih": np.array([[1.0, 0.0, -1.0, 0.0, 0.5, 0.0], [0.0, 1.0, 0.0, -1.0, 0.0, 0.5]]),
                  "W_hh": np.array([[0.2, 0.0, 0.0, 0.0, 1.0, 0.0], [0.0, 0.2, 0.0, 0.0, 0.0, 1.0]]),
                  "b_ih": np.zeros(6), "b_hh": np.array([0.0, 0.0, 0.0, 0.0, 0.5, 0.5])},
         "explanation": "One step for a batch of two. The candidate bias b_hn = 0.5 sits inside the reset gate's product."},
        {"name": "random batch", "args": case(rng, 4, 8, 3, 5)},
        {"name": "large hidden bias", "args": hb},
        {"name": "single unit long", "args": case(rng, 2, 40, 2, 1, scale=1.0)},
        {"name": "wide", "args": case(rng, 2, 6, 8, 16, scale=0.3)},
        {"name": "strong gates", "args": case(rng, 3, 10, 4, 3, scale=1.5, bias=1.0)},
    ]
