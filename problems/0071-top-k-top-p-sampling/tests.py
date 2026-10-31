import numpy as np


def cases():
    rng = np.random.default_rng(71)
    big = rng.normal(size=1000) * 3
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"logits": np.log(np.array([0.1, 0.5, 0.15, 0.25])), "temperature": 1.0, "top_k": 2, "top_p": 1.0, "u": 0.5},
         "explanation": "Top-2 keeps tokens 1 and 3 (0.5 and 0.25), renormalized to 2/3 and 1/3. The CDF in index order is [0, 2/3, 2/3, 1], and the first value above 0.5 is at index 1."},
        {"name": "Example 2", "hidden": False,
         "args": {"logits": np.log(np.array([0.1, 0.5, 0.15, 0.25])), "temperature": 1.0, "top_k": 0, "top_p": 0.8, "u": 0.9},
         "explanation": "Ranked: 0.5, 0.25, 0.15, 0.1 with running sums 0.5, 0.75, 0.9. Token 2 crosses 0.8, so tokens 1, 3 and 2 survive and renormalize by 0.9."},
        {"name": "Example 3", "hidden": False,
         "args": {"logits": np.array([2.0, 1.0, 0.0]), "temperature": 0.5, "top_k": 0, "top_p": 1.0, "u": 0.95},
         "explanation": "Temperature 0.5 doubles the logits before the softmax, which sharpens the distribution."},
        {"name": "top-p after top-k renormalization",
         "args": {"logits": np.log(np.array([0.30, 0.25, 0.20, 0.15, 0.10])), "temperature": 1.0, "top_k": 3, "top_p": 0.7, "u": 0.6},
         "explanation": "After top-3, the probabilities are 0.4, 1/3, 4/15. The running sums 0.4, 0.733 cross 0.7 at token 1. On the unfiltered distribution, 0.3, 0.55, 0.75 would keep three tokens."},
        {"name": "high temperature", "args": {"logits": rng.normal(size=10) * 2, "temperature": 3.0, "top_k": 0, "top_p": 1.0, "u": 0.42}},
        {"name": "huge logits", "args": {"logits": np.array([10000.0, 9999.0, -10000.0, 9998.0]), "temperature": 0.7, "top_k": 0, "top_p": 1.0, "u": 0.99}},
        {"name": "ties broken by lower index",
         "args": {"logits": np.array([0.0, 1.0, 1.0, 1.0, 0.0]), "temperature": 1.0, "top_k": 2, "top_p": 1.0, "u": 0.3}},
        {"name": "top_p keeps only the top token", "args": {"logits": np.array([0.0, 5.0, 1.0, 2.0]), "temperature": 1.0, "top_k": 0, "top_p": 0.1, "u": 0.0}},
        {"name": "top_k larger than vocab", "args": {"logits": rng.normal(size=6), "temperature": 1.0, "top_k": 50, "top_p": 0.9, "u": 0.77}},
        {"name": "top_k 1", "args": {"logits": rng.normal(size=8), "temperature": 2.0, "top_k": 1, "top_p": 0.5, "u": 0.999}},
        {"name": "index-order sampling",
         "args": {"logits": np.log(np.array([0.2, 0.05, 0.45, 0.3])), "temperature": 1.0, "top_k": 0, "top_p": 1.0, "u": 0.22}},
        {"name": "big vocabulary", "args": {"logits": big, "temperature": 0.8, "top_k": 40, "top_p": 0.85, "u": 0.31}},
        {"name": "u zero", "args": {"logits": rng.normal(size=7), "temperature": 1.3, "top_k": 4, "top_p": 0.95, "u": 0.0}},
    ]
