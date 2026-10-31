import numpy as np


def silu(z):
    return z / (1.0 + np.exp(-z))


def swiglu_ffn(x: np.ndarray, W1: np.ndarray, W3: np.ndarray, W2: np.ndarray) -> np.ndarray:
    gate = silu(x @ W1)
    value = x @ W3
    return (gate * value) @ W2
