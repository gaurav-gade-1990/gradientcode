import numpy as np


def lora_forward_and_merge(x, W, A, B, alpha):
    scale = alpha / A.shape[1]
    y = x @ W + scale * ((x @ A) @ B)
    W_merged = W + scale * (A @ B)
    return y, W_merged
