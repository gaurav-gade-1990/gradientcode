import numpy as np


def _out(H, W, kh, kw, stride, pad):
    return (H + 2 * pad - kh) // stride + 1, (W + 2 * pad - kw) // stride + 1


def _case(rng, N, C, H, W, F, kh, kw, stride=1, pad=0):
    oh, ow = _out(H, W, kh, kw, stride, pad)
    return {"dout": rng.normal(size=(N, F, oh, ow)), "x": rng.normal(size=(N, C, H, W)),
            "w": rng.normal(size=(F, C, kh, kw)), "stride": stride, "pad": pad}


def cases():
    rng = np.random.default_rng(44)
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"dout": np.array([[[[1.0, 0.0], [0.0, 0.0]]]]), "x": np.arange(1.0, 10.0).reshape(1, 1, 3, 3),
                  "w": np.array([[[[1.0, 2.0], [3.0, 4.0]]]])},
         "explanation": "Only the top-left output has gradient. So dw is the top-left window [[1, 2], [4, 5]], dx places w in the top-left corner, and db = 1."},
        {"name": "Example 2", "hidden": False,
         "args": {"dout": np.ones((1, 1, 2, 2)), "x": np.arange(1.0, 10.0).reshape(1, 1, 3, 3), "w": np.ones((1, 1, 2, 2))},
         "explanation": "Overlapping windows: the center pixel sits in all 4 windows, so dx[1, 1] = 4. Corners get 1 and edges get 2."},
        {"name": "3x3 pad 1", "args": _case(rng, 2, 3, 5, 5, 4, 3, 3, pad=1)},
        {"name": "stride 2 with leftover", "args": _case(rng, 2, 2, 6, 7, 3, 3, 3, stride=2)},
        {"name": "non-square kernel pad 2", "args": _case(rng, 1, 2, 4, 5, 2, 2, 3, pad=2)},
        {"name": "stride 3 pad 1", "args": _case(rng, 3, 1, 8, 8, 2, 2, 2, stride=3, pad=1)},
        {"name": "stride equals kernel", "args": _case(rng, 2, 2, 6, 6, 3, 2, 2, stride=2)},
        {"name": "1x1 kernel", "args": _case(rng, 2, 4, 3, 3, 3, 1, 1)},
        {"name": "full-size kernel", "args": _case(rng, 3, 2, 3, 3, 4, 3, 3)},
        {"name": "many channels stride 2 pad 1", "args": _case(rng, 2, 6, 7, 7, 5, 3, 3, stride=2, pad=1)},
    ]
