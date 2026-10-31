import numpy as np


def cases():
    rng = np.random.default_rng(52)
    z = np.zeros(3)
    out = [
        {"name": "Example 1", "hidden": False,
         "args": {"param": np.array([1.0, -2.0, 3.0]), "grad": np.array([0.1, -0.2, 0.3]), "m": z, "v": z, "t": 1},
         "explanation": "On step 1 with bias correction, m_hat = g and v_hat = g^2, so each parameter moves by about lr * sign(g)."},
        {"name": "Example 2", "hidden": False,
         "args": {"param": np.array([0.5, 0.5]), "grad": np.array([1.0, -1.0]), "m": np.array([0.2, -0.1]),
                  "v": np.array([0.04, 0.01]), "t": 5, "lr": 0.01}},
        {"name": "tiny gradients", "args": {"param": rng.normal(size=6), "grad": np.full(6, 1e-6), "m": np.zeros(6), "v": np.zeros(6), "t": 1, "eps": 1e-3}},
        {"name": "zero gradient", "args": {"param": rng.normal(size=4), "grad": np.zeros(4), "m": np.zeros(4), "v": np.zeros(4), "t": 3}},
        {"name": "matrix param late step", "args": {"param": rng.normal(size=(4, 5)), "grad": rng.normal(size=(4, 5)),
                                                      "m": rng.normal(size=(4, 5)) * 0.1, "v": rng.random((4, 5)) * 0.1, "t": 1000, "lr": 3e-4}},
        {"name": "custom betas", "args": {"param": rng.normal(size=8), "grad": rng.normal(size=8), "m": rng.normal(size=8) * 0.05,
                                            "v": rng.random(8) * 0.02, "t": 2, "beta1": 0.8, "beta2": 0.95, "lr": 0.1}},
    ]
    return out
