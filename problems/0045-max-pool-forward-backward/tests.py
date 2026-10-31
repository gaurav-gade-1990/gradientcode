import numpy as np


def _out(H, W, ph, pw, s):
    return (H - ph) // s + 1, (W - pw) // s + 1


def _case(rng, N, C, H, W, ph, pw, s, ints=False):
    oh, ow = _out(H, W, ph, pw, s)
    x = rng.integers(0, 4, size=(N, C, H, W)).astype(float) if ints else rng.normal(size=(N, C, H, W))
    return {"x": x, "dout": rng.normal(size=(N, C, oh, ow)), "pool_h": ph, "pool_w": pw, "stride": s}


def cases():
    rng = np.random.default_rng(45)
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"x": np.array([[[[1.0, 3.0, 2.0, 0.0], [4.0, 2.0, 1.0, 5.0], [0.0, 1.0, 3.0, 2.0], [2.0, 6.0, 1.0, 1.0]]]]),
                  "dout": np.array([[[[1.0, 2.0], [3.0, 4.0]]]]), "pool_h": 2, "pool_w": 2, "stride": 2},
         "explanation": "Window maxima are 4, 5, 6 and 3. Each window's dout lands on its max; everything else is 0."},
        {"name": "Example 2", "hidden": False,
         "args": {"x": np.array([[[[1.0, 1.0, 0.0], [0.0, 2.0, 2.0], [0.0, 0.0, 3.0]]]]),
                  "dout": np.array([[[[1.0, 10.0], [100.0, 1000.0]]]]), "pool_h": 2, "pool_w": 2, "stride": 1},
         "explanation": "Overlapping windows. The 2 at (1, 1) wins three windows (in the top-right one it ties with (1, 2) and comes first), so dx[1, 1] = 1 + 10 + 100. The 3 at (2, 2) gets 1000."},
        {"name": "random 2x2 stride 2", "args": _case(rng, 2, 3, 6, 6, 2, 2, 2)},
        {"name": "overlap 3x3 stride 1", "args": _case(rng, 2, 2, 5, 5, 3, 3, 1)},
        {"name": "ties everywhere", "args": _case(rng, 2, 2, 6, 6, 3, 3, 2, ints=True)},
        {"name": "ties with overlap", "args": _case(rng, 1, 3, 5, 6, 2, 3, 1, ints=True)},
        {"name": "constant input", "args": {"x": np.zeros((1, 1, 4, 4)), "dout": rng.normal(size=(1, 1, 3, 3)), "pool_h": 2, "pool_w": 2, "stride": 1}},
        {"name": "stride leftover", "args": _case(rng, 2, 2, 7, 8, 3, 2, 3)},
        {"name": "global pool", "args": _case(rng, 3, 2, 4, 5, 4, 5, 1)},
        {"name": "1x1 window", "args": _case(rng, 1, 2, 3, 3, 1, 1, 2)},
    ]
