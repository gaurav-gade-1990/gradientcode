import numpy as np


def swiglu_ffn(x, W1, W3, W2):
    gate = 1.0 / (1.0 + np.exp(-(x @ W1)))
    return (gate * (x @ W3)) @ W2
