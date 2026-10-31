import numpy as np

XOR_X = np.array([[0.0, 0.0], [0.0, 1.0], [1.0, 0.0], [1.0, 1.0]])
XOR_Y = np.array([0.0, 1.0, 1.0, 0.0])


def _init(rng, H, scale=1.0):
    return {"W1": rng.normal(size=(2, H)) * scale, "b1": rng.normal(size=H) * 0.1,
            "W2": rng.normal(size=(H, 1)) * scale, "b2": np.zeros(1)}


def cases():
    rng = np.random.default_rng(47)
    ex1 = {"X": XOR_X, "y": XOR_Y,
           "W1": np.array([[1.0, -1.0], [-1.0, 1.0]]), "b1": np.array([0.0, 0.0]),
           "W2": np.array([[1.0], [1.0]]), "b2": np.array([0.0]), "lr": 0.5, "epochs": 3}
    ex2 = {"X": XOR_X, "y": XOR_Y,
           "W1": np.array([[0.5, -0.4, 0.3], [0.2, 0.6, -0.5]]), "b1": np.array([0.1, -0.1, 0.0]),
           "W2": np.array([[0.7], [-0.6], [0.4]]), "b2": np.array([0.0]), "lr": 1.0, "epochs": 5}
    big = dict(X=XOR_X, y=XOR_Y, lr=0.5, epochs=2000, **_init(rng, 4))
    Xr = rng.normal(size=(12, 2))
    yr = (Xr[:, 0] * Xr[:, 1] > 0).astype(float)
    return [
        {"name": "Example 1", "hidden": False, "args": ex1,
         "explanation": "Three steps of gradient descent from a hand-picked start. losses[0] is the loss before any update."},
        {"name": "Example 2", "hidden": False, "args": ex2},
        {"name": "single epoch", "args": dict(X=XOR_X, y=XOR_Y, lr=0.3, epochs=1, **_init(rng, 2))},
        {"name": "xor 200 epochs", "args": dict(X=XOR_X, y=XOR_Y, lr=1.0, epochs=200, **_init(rng, 3))},
        {"name": "xor converges", "args": big},
        {"name": "one hidden unit", "args": dict(X=XOR_X, y=XOR_Y, lr=0.8, epochs=100, **_init(rng, 1))},
        {"name": "wide hidden, small lr", "args": dict(X=XOR_X, y=XOR_Y, lr=0.05, epochs=300, **_init(rng, 8, 0.5))},
        {"name": "random quadrant data", "args": dict(X=Xr, y=yr, lr=0.5, epochs=400, **_init(rng, 5))},
    ]
