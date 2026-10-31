import numpy as np


def cases():
    rng = np.random.default_rng(63)
    causal4 = np.tril(np.ones((4, 4), dtype=bool))
    pad = np.ones((2, 1, 1, 5), dtype=bool)
    pad[0, ..., 3:] = False
    pad[1, ..., 4:] = False
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"q": np.array([[1.0, 0.0]]), "k": np.array([[1.0, 0.0], [0.0, 1.0]]), "v": np.array([[1.0, 2.0], [3.0, 4.0]])},
         "explanation": "Scores are [1, 0] / sqrt(2) = [0.7071, 0]. The softmax gives [0.6698, 0.3302], so the output is 0.6698*[1, 2] + 0.3302*[3, 4]."},
        {"name": "Example 2", "hidden": False,
         "args": {"q": np.array([[1.0, 1.0], [0.0, 2.0]]), "k": np.array([[1.0, 0.0], [0.0, 1.0]]),
                  "v": np.array([[10.0], [20.0]]), "mask": np.array([[True, False], [True, True]])},
         "explanation": "The first query can only see the first key, so its weights are [1, 0] and its output is 10."},
        {"name": "Example 3", "hidden": False,
         "args": {"q": np.array([[[0.0, 1.0]], [[1.0, 0.0]]]), "k": np.array([[[1.0, 0.0], [0.0, 1.0]], [[1.0, 0.0], [0.0, 1.0]]]),
                  "v": np.array([[[1.0], [0.0]], [[1.0], [0.0]]])},
         "explanation": "A leading batch axis of size 2. Each batch element is independent."},
        {"name": "d_k differs from d_v", "args": {"q": rng.normal(size=(3, 8)), "k": rng.normal(size=(5, 8)), "v": rng.normal(size=(5, 2))}},
        {"name": "causal mask 2d", "args": {"q": rng.normal(size=(4, 4)), "k": rng.normal(size=(4, 4)), "v": rng.normal(size=(4, 3)), "mask": causal4}},
        {"name": "batched heads with broadcast causal mask",
         "args": {"q": rng.normal(size=(2, 3, 4, 4)), "k": rng.normal(size=(2, 3, 4, 4)), "v": rng.normal(size=(2, 3, 4, 6)), "mask": causal4}},
        {"name": "padding mask broadcast over heads and queries",
         "args": {"q": rng.normal(size=(2, 2, 3, 4)), "k": rng.normal(size=(2, 2, 5, 4)), "v": rng.normal(size=(2, 2, 5, 3)), "mask": pad}},
        {"name": "huge scores", "args": {"q": rng.normal(size=(3, 4)) * 100, "k": rng.normal(size=(6, 4)) * 30,
                                         "v": rng.normal(size=(6, 4)), "mask": rng.random((3, 6)) < 0.7 + np.eye(3, 6, dtype=bool)}},
        {"name": "single key", "args": {"q": rng.normal(size=(5, 3)), "k": rng.normal(size=(1, 3)), "v": rng.normal(size=(1, 2))}},
        {"name": "explicit all-true mask", "args": {"q": rng.normal(size=(2, 6, 4)), "k": rng.normal(size=(2, 7, 4)),
                                                    "v": rng.normal(size=(2, 7, 5)), "mask": np.ones((6, 7), dtype=bool)}},
    ]
