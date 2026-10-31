import numpy as np


def case(rng, B, d, H, scale=0.5):
    return {
        "x": rng.normal(size=(B, d)),
        "h_prev": rng.normal(size=(B, H)) * 0.5,
        "c_prev": rng.normal(size=(B, H)),
        "W": rng.normal(size=(d, 4 * H)) * scale,
        "U": rng.normal(size=(H, 4 * H)) * scale,
        "b": rng.normal(size=4 * H) * 0.1,
    }


def cases():
    rng = np.random.default_rng(61)
    big = case(rng, 2, 3, 4)
    big["b"] = np.tile(np.array([1000.0, -1000.0, 1000.0, 1000.0, -1000.0, 1000.0, 1000.0, -1000.0]), 2)
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"x": np.array([[1.0]]), "h_prev": np.array([[0.0]]), "c_prev": np.array([[0.5]]),
                  "W": np.array([[0.0, 0.0, 1.0, 0.0]]), "U": np.zeros((1, 4)), "b": np.array([0.0, 0.0, 0.0, 0.0])},
         "explanation": "i = f = o = sigmoid(0) = 0.5 and g = tanh(1) = 0.7616. c = 0.5*0.5 + 0.5*0.7616 = 0.6308, h = 0.5*tanh(0.6308) = 0.2793."},
        {"name": "Example 2", "hidden": False,
         "args": {"x": np.array([[1.0, -1.0]]), "h_prev": np.array([[0.2, -0.1]]), "c_prev": np.array([[0.3, 0.0]]),
                  "W": np.array([[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8], [-0.1, 0.0, 0.1, 0.0, -0.2, 0.2, 0.0, 0.1]]),
                  "U": np.zeros((2, 8)), "b": np.array([0.0, 0.0, 1.0, 1.0, 0.0, 0.0, -1.0, -1.0])},
         "explanation": "Columns 0-1 are the input gate, 2-3 the forget gate, 4-5 the candidate and 6-7 the output gate."},
        {"name": "random batch", "args": case(rng, 4, 5, 6)},
        {"name": "single unit", "args": case(rng, 3, 2, 1, scale=1.0)},
        {"name": "wide", "args": case(rng, 2, 8, 16, scale=0.3)},
        {"name": "strong weights", "args": case(rng, 5, 4, 3, scale=2.0)},
        {"name": "saturated gates", "args": big,
         "explanation": "The biases push gates to exactly 0 or 1 without overflowing."},
    ]
