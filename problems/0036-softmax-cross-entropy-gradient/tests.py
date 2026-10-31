import numpy as np


def cases():
    rng = np.random.default_rng(36)
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"logits": np.array([[2.0, 1.0, 0.1]]), "labels": np.array([0])},
         "explanation": "p = softmax([2, 1, 0.1]) = [0.659, 0.242, 0.099]. loss = -log(0.659) = 0.417 and dlogits = p - [1, 0, 0]."},
        {"name": "Example 2", "hidden": False,
         "args": {"logits": np.array([[0.0, 0.0], [1000.0, 0.0]]), "labels": np.array([1, 1])},
         "explanation": "Row 2 puts all its mass on class 0, so -log p = 1000 exactly. The mean loss is (log 2 + 1000) / 2."},
        {"name": "huge logits", "args": {"logits": np.array([[1e4, -1e4, 0.0], [5000.0, 5001.0, 4999.0]]), "labels": np.array([2, 0])}},
        {"name": "random batch", "args": {"logits": rng.normal(size=(16, 10)) * 3, "labels": rng.integers(0, 10, size=16)}},
        {"name": "single sample", "args": {"logits": rng.normal(size=(1, 5)), "labels": np.array([4])}},
        {"name": "uniform logits", "args": {"logits": np.zeros((4, 4)), "labels": np.array([0, 1, 2, 3])}},
        {"name": "confident and correct", "args": {"logits": np.array([[50.0, 0.0], [0.0, 50.0]]), "labels": np.array([0, 1])}},
        {"name": "wide range batch", "args": {"logits": rng.normal(size=(50, 7)) * 400, "labels": rng.integers(0, 7, size=50)}},
    ]
