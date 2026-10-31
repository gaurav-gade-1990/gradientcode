import numpy as np


def padded(rng, B, T, pad_value=0.0, min_len=1):
    lens = rng.integers(min_len, T + 1, size=B)
    mask = np.arange(T)[None, :] < lens[:, None]
    lp = np.log(rng.uniform(0.01, 1.0, size=(B, T)))
    return {"logprobs": np.where(mask, lp, pad_value), "mask": mask}


def cases():
    rng = np.random.default_rng(72)
    l4 = np.log(0.25)
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"logprobs": np.array([[l4, l4, l4]]), "mask": np.array([[True, True, True]])},
         "explanation": "Every token has probability 1/4, so the perplexity is 4: the model is as unsure as a uniform choice among 4 tokens."},
        {"name": "Example 2", "hidden": False,
         "args": {"logprobs": np.array([[np.log(0.5), np.log(0.5), 0.0], [np.log(0.125), 0.0, 0.0]]),
                  "mask": np.array([[True, True, False], [True, False, False]])},
         "explanation": "Three real tokens with NLL ln 2, ln 2 and ln 8 = 3 ln 2. The mean is (5/3) ln 2, so the perplexity is 2^(5/3) = 3.1748."},
        {"name": "no padding", "args": {"logprobs": np.log(rng.uniform(0.05, 1.0, size=(3, 7))), "mask": np.ones((3, 7), dtype=bool)}},
        {"name": "padding holds -inf", "args": padded(rng, 4, 6, pad_value=-np.inf)},
        {"name": "uneven lengths", "args": padded(rng, 5, 20, pad_value=0.0)},
        {"name": "garbage in padding", "args": padded(rng, 3, 8, pad_value=-50.0)},
        {"name": "one real token", "args": {"logprobs": np.array([[-2.0, -np.inf, -np.inf], [-np.inf, -np.inf, -np.inf]]),
                                            "mask": np.array([[True, False, False], [False, False, False]])}},
        {"name": "perfect model", "args": {"logprobs": np.zeros((2, 4)), "mask": np.ones((2, 4), dtype=bool)}},
        {"name": "large batch", "args": padded(rng, 20, 40, pad_value=-np.inf, min_len=5)},
    ]
