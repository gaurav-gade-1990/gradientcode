import numpy as np


def swiglu_ffn(x, W1, W3, W2):
    z = x @ W3
    return ((x @ W1) * (z / (1.0 + np.exp(-z)))) @ W2
