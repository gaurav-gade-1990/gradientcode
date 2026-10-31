import numpy as np


def multi_head_attention(x, W_q, W_k, W_v, W_o, num_heads, mask=None):
    B, T, d_model = x.shape
    d_head = d_model // num_heads

    def split(a):
        return a.reshape(B, T, num_heads, d_head).transpose(0, 2, 1, 3)

    q, k, v = split(x @ W_q), split(x @ W_k), split(x @ W_v)
    scores = q @ k.transpose(0, 1, 3, 2) / np.sqrt(d_head)
    if mask is not None:
        scores = np.where(mask, scores, -np.inf)
    scores = scores - scores.max(axis=-1, keepdims=True)
    w = np.exp(scores)
    w = w / w.sum(axis=-1, keepdims=True)
    out = (w @ v).transpose(0, 2, 1, 3).reshape(B, T, d_model)
    return out @ W_o
