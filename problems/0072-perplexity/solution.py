import numpy as np


def perplexity(logprobs, mask):
    total = np.where(mask, logprobs, 0.0).sum()
    return float(np.exp(-total / mask.sum()))
