import numpy as np


def _softmax(z):
    e = np.exp(z - z.max(axis=1, keepdims=True))
    return e / e.sum(axis=1, keepdims=True)


def cases():
    rng = np.random.default_rng(33)
    n = 400
    labels = rng.integers(0, 5, size=n)
    logits = rng.normal(size=(n, 5)) + 3.0 * np.eye(5)[labels] * (rng.random(n) < 0.7)[:, None]
    overconf = _softmax(logits * 3.0)
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"probs": np.array([[0.9, 0.1], [0.8, 0.2], [0.3, 0.7], [0.4, 0.6]]), "labels": np.array([0, 1, 1, 1]), "n_bins": 2},
         "explanation": "Confidences 0.9, 0.8, 0.7, 0.6 all fall in bin (0.5, 1]. Accuracy there is 3/4 and mean confidence 0.75, so ECE = 0."},
        {"name": "Example 2", "hidden": False,
         "args": {"probs": np.array([[0.25, 0.75], [0.5, 0.5], [1.0, 0.0]]), "labels": np.array([1, 1, 0]), "n_bins": 4},
         "explanation": "0.5 lands in bin (0.25, 0.5] and its argmax is class 0 (a tie goes to the lower index), so it is wrong: gap 0.5. 0.75 lands in (0.5, 0.75] and is right: gap 0.25. 1.0 is in the last bin with gap 0. ECE = (0.5 + 0.25) / 3 = 0.25."},
        {"name": "confidence on the edges", "args": {"probs": np.array([[0.5, 0.25, 0.25], [0.25, 0.75, 0.0], [0.0, 0.0, 1.0], [0.75, 0.125, 0.125], [0.5, 0.5, 0.0]]),
                                                    "labels": np.array([0, 1, 0, 0, 1]), "n_bins": 4}},
        {"name": "edge value changes bins", "args": {"probs": np.array([[0.25, 0.75], [0.1, 0.9], [0.5, 0.5], [0.6, 0.4]]),
                                                     "labels": np.array([1, 1, 0, 1]), "n_bins": 4}},
        {"name": "uneven bin sizes", "args": {"probs": np.array([[0.95, 0.05], [0.92, 0.08], [0.97, 0.03], [0.91, 0.09], [0.55, 0.45]]),
                                              "labels": np.array([0, 0, 1, 0, 1]), "n_bins": 10}},
        {"name": "one bin", "args": {"probs": np.array([[0.6, 0.4], [0.2, 0.8], [0.5, 0.5]]), "labels": np.array([1, 1, 0]), "n_bins": 1}},
        {"name": "all wrong and confident", "args": {"probs": np.array([[0.99, 0.01], [0.02, 0.98]]), "labels": np.array([1, 0]), "n_bins": 5}},
        {"name": "single sample", "args": {"probs": np.array([[0.1, 0.3, 0.6]]), "labels": np.array([2]), "n_bins": 10}},
        {"name": "overconfident network", "args": {"probs": overconf, "labels": labels, "n_bins": 15}},
        {"name": "random distributions", "args": {"probs": rng.dirichlet(np.ones(4), size=200), "labels": rng.integers(0, 4, size=200), "n_bins": 10}},
    ]
