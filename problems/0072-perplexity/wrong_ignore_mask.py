import numpy as np


def perplexity(logprobs, mask):
    lp = np.where(np.isfinite(logprobs), logprobs, 0.0)
    return float(np.exp(-lp.mean()))
