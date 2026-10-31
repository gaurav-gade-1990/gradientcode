import numpy as np


def cases():
    rng = np.random.default_rng(86)
    W_in1 = np.array([[0.5, -0.2], [0.1, 0.3], [0.0, 0.4], [-0.3, 0.2]])
    W_out1 = np.array([[0.2, 0.1], [0.4, -0.5], [-0.1, 0.3], [0.3, 0.3]])
    big_in = rng.normal(size=(6, 4))
    big_out = rng.normal(size=(6, 4))
    big_in[2] = np.array([20.0, -20.0, 15.0, 10.0])
    big_out[[1, 4]] = np.array([[25.0, -20.0, 10.0, 5.0], [-30.0, 25.0, -12.0, -8.0]])
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"W_in": W_in1, "W_out": W_out1, "center": 0, "context": 1, "negatives": np.array([2, 3])},
         "explanation": "v = W_in[0]. Only row 0 of dW_in and rows 1, 2, 3 of dW_out are nonzero."},
        {"name": "Example 2", "hidden": False,
         "args": {"W_in": np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]]), "W_out": np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 2.0]]),
                  "center": 0, "context": 1, "negatives": np.array([2, 2])},
         "explanation": "Negative 2 is sampled twice, so its gradient is added to dW_out[2] twice. u_2 . v = 0, so each copy contributes log 2 to the loss."},
        {"name": "negative equals context", "args": {"W_in": rng.normal(size=(5, 3)), "W_out": rng.normal(size=(5, 3)),
                                                      "center": 2, "context": 4, "negatives": np.array([4, 0, 1])}},
        {"name": "center equals context index", "args": {"W_in": rng.normal(size=(5, 3)), "W_out": rng.normal(size=(5, 3)),
                                                          "center": 3, "context": 3, "negatives": np.array([1, 3, 1, 1])}},
        {"name": "large scores", "args": {"W_in": big_in, "W_out": big_out, "center": 2, "context": 4, "negatives": np.array([1, 0, 1])}},
        {"name": "single negative", "args": {"W_in": rng.normal(size=(4, 8)) * 0.1, "W_out": rng.normal(size=(4, 8)) * 0.1,
                                              "center": 1, "context": 0, "negatives": np.array([3])}},
        {"name": "zero output vectors", "args": {"W_in": rng.normal(size=(4, 3)), "W_out": np.zeros((4, 3)),
                                                  "center": 0, "context": 1, "negatives": np.array([2, 3])}},
        {"name": "typical word2vec", "args": {"W_in": rng.normal(size=(50, 16)) * 0.3, "W_out": rng.normal(size=(50, 16)) * 0.3,
                                               "center": 17, "context": 42, "negatives": rng.integers(0, 50, size=10)}},
    ]
