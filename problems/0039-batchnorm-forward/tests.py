import numpy as np


def cases():
    rng = np.random.default_rng(39)

    def rand(N, D, train=True, **kw):
        a = {"x": rng.normal(size=(N, D)) * 2 + 1, "gamma": rng.normal(size=D), "beta": rng.normal(size=D),
             "running_mean": rng.normal(size=D), "running_var": rng.random(D) + 0.5, "train": train}
        a.update(kw)
        return a

    return [
        {"name": "Example 1", "hidden": False,
         "args": {"x": np.array([[1.0, 2.0], [3.0, 6.0]]), "gamma": np.array([1.0, 1.0]), "beta": np.array([0.0, 0.0]),
                  "running_mean": np.array([0.0, 0.0]), "running_var": np.array([1.0, 1.0])},
         "explanation": "Batch mean [2, 4], biased variance [1, 4]. out is about [[-1, -1], [1, 1]]. running_mean = 0.9*0 + 0.1*[2, 4] = [0.2, 0.4]."},
        {"name": "Example 2", "hidden": False,
         "args": {"x": np.array([[1.0, 2.0], [3.0, 6.0]]), "gamma": np.array([2.0, 0.5]), "beta": np.array([1.0, -1.0]),
                  "running_mean": np.array([1.0, 3.0]), "running_var": np.array([4.0, 1.0]), "train": False},
         "explanation": "Eval mode uses the running stats: (x - [1, 3]) / sqrt([4, 1] + eps), then gamma and beta."},
        {"name": "random train", "args": rand(16, 5)},
        {"name": "random eval", "args": rand(8, 3, train=False)},
        {"name": "custom momentum", "args": rand(10, 4, momentum=0.5)},
        {"name": "momentum zero", "args": rand(6, 3, momentum=0.0)},
        {"name": "tiny variance feature", "args": {"x": np.array([[1.0, 0.0], [1.0 + 2e-3, 1.0], [1.0 - 2e-3, 2.0]]),
                                                    "gamma": np.ones(2), "beta": np.zeros(2),
                                                    "running_mean": np.zeros(2), "running_var": np.ones(2), "eps": 1e-3}},
        {"name": "batch of two", "args": rand(2, 6)},
        {"name": "large batch", "args": rand(128, 8, momentum=0.99)},
    ]
