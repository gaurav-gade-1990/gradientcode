import numpy as np


def perplexity(logprobs, mask):
    per_seq = np.where(mask, logprobs, 0.0).sum(axis=1) / np.maximum(mask.sum(axis=1), 1)
    return float(np.mean(np.exp(-per_seq)))
