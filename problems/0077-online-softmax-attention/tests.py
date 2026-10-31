import numpy as np


def cases():
    rng = np.random.default_rng(77)
    rising_K = np.outer(np.arange(1.0, 9.0), np.ones(2))      # scores grow block by block
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"Q": np.array([[1.0, 0.0]]), "K": np.array([[0.0, 0.0], [1.0, 0.0], [2.0, 0.0], [0.0, 1.0]]),
                  "V": np.array([[1.0], [2.0], [3.0], [4.0]]), "block_size": 2},
         "explanation": "Scores are [0, 1, 2, 0] / sqrt(2). After block 0, m = 0.7071. Block 1 raises it to m = 1.4142, "
                        "so l and acc are first scaled by exp(0.7071 - 1.4142) before adding the new terms."},
        {"name": "Example 2", "hidden": False,
         "args": {"Q": np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]]), "K": np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]]),
                  "V": np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]]), "block_size": 2, "causal": True},
         "explanation": "Causal: query 0 sees only key 0, so block 1 is fully masked for it and its m and l do not change."},
        {"name": "rising maxima", "args": {"Q": np.array([[1.0, 1.0], [0.5, -0.2], [-1.0, 0.3]]), "K": rising_K,
                                           "V": rng.normal(size=(8, 3)), "block_size": 3}},
        {"name": "block size 1", "args": {"Q": rng.normal(size=(4, 4)), "K": rng.normal(size=(6, 4)),
                                          "V": rng.normal(size=(6, 2)), "block_size": 1}},
        {"name": "single block", "args": {"Q": rng.normal(size=(3, 5)), "K": rng.normal(size=(7, 5)),
                                          "V": rng.normal(size=(7, 4)), "block_size": 7}},
        {"name": "ragged last block", "args": {"Q": rng.normal(size=(5, 8)), "K": rng.normal(size=(13, 8)),
                                               "V": rng.normal(size=(13, 6)), "block_size": 4}},
        {"name": "huge scores", "args": {"Q": rng.normal(size=(4, 4)) * 30, "K": rng.normal(size=(10, 4)) * 30,
                                         "V": rng.normal(size=(10, 3)), "block_size": 3}},
        {"name": "causal ragged", "args": {"Q": rng.normal(size=(10, 4)), "K": rng.normal(size=(10, 4)),
                                           "V": rng.normal(size=(10, 3)), "block_size": 4, "causal": True}},
        {"name": "causal huge scores", "args": {"Q": rng.normal(size=(9, 4)) * 25, "K": rng.normal(size=(9, 4)) * 25,
                                                "V": rng.normal(size=(9, 2)), "block_size": 2, "causal": True}},
        {"name": "causal rising", "args": {"Q": np.ones((8, 2)), "K": rising_K, "V": rng.normal(size=(8, 2)),
                                           "block_size": 3, "causal": True}},
        {"name": "longer", "args": {"Q": rng.normal(size=(32, 16)), "K": rng.normal(size=(48, 16)),
                                    "V": rng.normal(size=(48, 8)), "block_size": 16}},
    ]
