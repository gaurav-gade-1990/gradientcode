import numpy as np


def perplexity(logprobs, mask):
    per_seq = np.where(mask, logprobs, 0.0).sum(axis=1) / mask.sum(axis=1)
    return float(np.exp(-per_seq.mean()))
