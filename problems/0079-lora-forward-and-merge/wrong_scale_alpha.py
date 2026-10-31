import numpy as np


def lora_forward_and_merge(x, W, A, B, alpha):
    y = x @ W + alpha * ((x @ A) @ B)
    W_merged = W + alpha * (A @ B)
    return y, W_merged
