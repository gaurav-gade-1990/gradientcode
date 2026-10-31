import numpy as np


def cases():
    rng = np.random.default_rng(53)
    z = np.zeros(3)
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"param": np.array([1.0, -2.0, 3.0]), "grad": np.array([0.1, -0.2, 0.3]), "m": z, "v": z, "t": 1,
                  "lr": 0.1, "weight_decay": 0.5},
         "explanation": "Decay first multiplies param by 1 - 0.1 * 0.5 = 0.95. On step 1, m_hat / sqrt(v_hat) is about sign(g), so each parameter then moves by about 0.1."},
        {"name": "Example 2", "hidden": False,
         "args": {"param": np.array([2.0, -2.0]), "grad": np.array([0.0, 0.0]), "m": np.zeros(2), "v": np.zeros(2), "t": 1,
                  "lr": 0.1, "weight_decay": 0.1},
         "explanation": "With a zero gradient only the decay acts: param * (1 - 0.01) = [1.98, -1.98]. Adam with L2 would instead take a full lr-sized step."},
        {"name": "default decay late step", "args": {"param": rng.normal(size=(4, 5)), "grad": rng.normal(size=(4, 5)),
                                                      "m": rng.normal(size=(4, 5)) * 0.1, "v": rng.random((4, 5)) * 0.1,
                                                      "t": 500, "lr": 3e-4}},
        {"name": "strong decay, large lr", "args": {"param": rng.normal(size=6) * 3, "grad": rng.normal(size=6),
                                                     "m": rng.normal(size=6) * 0.1, "v": rng.random(6) * 0.5, "t": 10,
                                                     "lr": 0.1, "weight_decay": 0.2}},
        {"name": "zero decay equals Adam", "args": {"param": rng.normal(size=5), "grad": rng.normal(size=5),
                                                     "m": np.zeros(5), "v": np.zeros(5), "t": 1, "weight_decay": 0.0}},
        {"name": "custom betas", "args": {"param": rng.normal(size=8), "grad": rng.normal(size=8),
                                           "m": rng.normal(size=8) * 0.05, "v": rng.random(8) * 0.02, "t": 3,
                                           "beta1": 0.8, "beta2": 0.95, "lr": 0.05, "weight_decay": 0.1}},
        {"name": "tiny gradients", "args": {"param": rng.normal(size=4), "grad": np.full(4, 1e-6), "m": np.zeros(4),
                                             "v": np.zeros(4), "t": 2, "lr": 0.01, "weight_decay": 0.05}},
    ]
