import numpy as np


def cases():
    rng = np.random.default_rng(58)
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"grad": np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]), "shape": (3,)},
         "explanation": "A bias of shape (3,) was broadcast over 2 rows. Sum over the added leading axis: [5, 7, 9]."},
        {"name": "Example 2", "hidden": False,
         "args": {"grad": np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]), "shape": (2, 1)},
         "explanation": "A column of shape (2, 1) was stretched across 3 columns. Sum axis 1 and keep it: [[6], [15]]."},
        {"name": "Example 3", "hidden": False,
         "args": {"grad": np.array([[1.0, 2.0], [3.0, 4.0]]), "shape": ()},
         "explanation": "A scalar was broadcast everywhere, so its gradient is the total sum, 10."},
        {"name": "no broadcasting", "args": {"grad": rng.normal(size=(3, 4)), "shape": (3, 4)}},
        {"name": "leading and inner size-1", "args": {"grad": rng.normal(size=(2, 3, 4, 5)), "shape": (3, 1, 5)}},
        {"name": "leading axes plus trailing 1", "args": {"grad": rng.normal(size=(4, 3, 2)), "shape": (3, 1)}},
        {"name": "all ones target", "args": {"grad": rng.normal(size=(2, 3, 4)), "shape": (1, 1, 1)}},
        {"name": "size-1 that was not stretched", "args": {"grad": rng.normal(size=(5, 1, 3)), "shape": (1, 3)}},
        {"name": "target of shape (1,)", "args": {"grad": rng.normal(size=(3, 4)), "shape": (1,)}},
        {"name": "scalar grad, scalar target", "args": {"grad": np.array(2.5), "shape": ()}},
        {"name": "five dims", "args": {"grad": rng.normal(size=(2, 1, 3, 2, 4)), "shape": (1, 3, 1, 4)}},
        {"name": "size-1 in front of target", "args": {"grad": rng.normal(size=(6, 2, 3)), "shape": (1, 2, 1)}},
    ]
