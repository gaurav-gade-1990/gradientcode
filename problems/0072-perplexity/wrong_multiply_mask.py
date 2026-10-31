import numpy as np


def perplexity(logprobs, mask):
    return float(np.exp(-(logprobs * mask).sum() / mask.sum()))
