import numpy as np


def _x(rng, *shape):
    return rng.integers(-9, 10, size=shape).astype(float)


def cases():
    rng = np.random.default_rng(42)
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"x": np.arange(1.0, 10.0).reshape(1, 1, 3, 3), "kh": 2, "kw": 2},
         "explanation": "Four 2x2 windows. Column 0 is the top-left window [1, 2, 4, 5], column 1 is [2, 3, 5, 6], and so on."},
        {"name": "Example 2", "hidden": False,
         "args": {"x": np.arange(1.0, 9.0).reshape(2, 1, 2, 2), "kh": 2, "kw": 2, "pad": 1, "stride": 2},
         "explanation": "Padding gives 4x4 images and stride 2 gives 2x2 outputs, so there are 2 * 4 = 8 columns. The first 4 belong to image 0."},
        {"name": "two channels", "args": {"x": _x(rng, 1, 2, 3, 4), "kh": 2, "kw": 3}},
        {"name": "batch and channels", "args": {"x": _x(rng, 3, 2, 4, 4), "kh": 3, "kw": 3, "pad": 1}},
        {"name": "stride with leftover", "args": {"x": _x(rng, 2, 3, 6, 5), "kh": 3, "kw": 2, "stride": 2}},
        {"name": "1x1 kernel", "args": {"x": _x(rng, 2, 3, 2, 2), "kh": 1, "kw": 1}},
        {"name": "pad 2 stride 3", "args": {"x": _x(rng, 2, 2, 5, 7), "kh": 3, "kw": 3, "pad": 2, "stride": 3}},
        {"name": "full-size kernel", "args": {"x": _x(rng, 3, 1, 4, 3), "kh": 4, "kw": 3}},
        {"name": "non-square padded", "args": {"x": rng.normal(size=(2, 2, 3, 6)), "kh": 2, "kw": 4, "pad": 1}},
    ]
