import numpy as np


def weights(rng, d, h, scale=None):
    s = scale if scale is not None else 1.0 / np.sqrt(d)
    a = {n: rng.normal(size=(d, d)) * s for n in ("W_q", "W_k", "W_v", "W_o")}
    a["num_heads"] = h
    return a


def cases():
    rng = np.random.default_rng(69)
    I = np.eye(2)
    ex1 = {"W_q": I, "W_k": I, "W_v": I, "W_o": I, "num_heads": 1,
           "xs": {"a": np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]])},
           "ops": [["a", "step", 1], ["a", "step", 1], ["a", "step", 1]]}
    ex2 = dict(weights(rng, 4, 2), xs={"a": np.round(rng.normal(size=(4, 4)), 1)},
               ops=[["a", "prefill", 2], ["a", "step", 1], ["a", "step", 1]])
    out = [
        {"name": "Example 1", "hidden": False, "args": ex1,
         "explanation": "Token 0 sees only itself, so its output is [1, 0]. Token 1 attends over tokens 0 and 1 with equal scores 0 and 1/sqrt(2)."},
        {"name": "Example 2", "hidden": False, "args": ex2,
         "explanation": "Prefill two tokens, then decode two more. The outputs must match full causal attention row by row."},
    ]
    d, h = 8, 2
    out.append({"name": "prefill only", "args": dict(weights(rng, d, h), xs={"a": rng.normal(size=(6, d))}, ops=[["a", "prefill", 6]])})
    out.append({"name": "steps only", "args": dict(weights(rng, d, 4), xs={"a": rng.normal(size=(10, d))}, ops=[["a", "step", 1]] * 10)})
    out.append({"name": "prefill after steps",
                "args": dict(weights(rng, d, h), xs={"a": rng.normal(size=(9, d))},
                             ops=[["a", "step", 1], ["a", "step", 1], ["a", "prefill", 4], ["a", "step", 1], ["a", "prefill", 2]])})
    out.append({"name": "two interleaved sequences",
                "args": dict(weights(rng, d, h), xs={"a": rng.normal(size=(5, d)), "b": rng.normal(size=(5, d))},
                             ops=[["a", "prefill", 2], ["b", "prefill", 3], ["a", "step", 1], ["b", "step", 1],
                                  ["a", "step", 1], ["a", "step", 1], ["b", "step", 1]])})
    out.append({"name": "three caches sharp attention",
                "args": dict(weights(rng, 16, 4, scale=1.0),
                             xs={k: rng.normal(size=(6, 16)) for k in ("a", "b", "c")},
                             ops=[[k, "prefill", 3] for k in "abc"] + [[k, "step", 1] for k in "cba"] + [[k, "prefill", 2] for k in "bca"])})
    out.append({"name": "long decode", "args": dict(weights(rng, 4, 1), xs={"a": rng.normal(size=(40, 4))},
                                                    ops=[["a", "prefill", 8]] + [["a", "step", 1]] * 32)})
    out.append({"name": "single head width 1", "args": dict(weights(rng, 3, 3), xs={"a": rng.normal(size=(5, 3))},
                                                            ops=[["a", "prefill", 3], ["a", "prefill", 2]])})
    return out
