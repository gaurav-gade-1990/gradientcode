import numpy as np


def layer_norm(z, g, b, eps=1e-5):
    mu = z.mean(axis=-1, keepdims=True)
    var = ((z - mu) ** 2).mean(axis=-1, keepdims=True)
    return g * (z - mu) / np.sqrt(var + eps) + b


def gelu(z):
    return 0.5 * z * (1.0 + np.tanh(np.sqrt(2.0 / np.pi) * (z + 0.044715 * z ** 3)))


def causal_mha(u, W_q, W_k, W_v, W_o, num_heads):
    B, T, d = u.shape
    dh = d // num_heads

    def split(a):
        return a.reshape(B, T, num_heads, dh).transpose(0, 2, 1, 3)

    q, k, v = split(u @ W_q), split(u @ W_k), split(u @ W_v)
    s = q @ k.transpose(0, 1, 3, 2) / np.sqrt(dh)
    s = s - s.max(axis=-1, keepdims=True)
    w = np.exp(s)
    w = w / w.sum(axis=-1, keepdims=True)
    return (w @ v).transpose(0, 2, 1, 3).reshape(B, T, d) @ W_o


def transformer_block(x, params, num_heads):
    p = params
    a = x + causal_mha(layer_norm(x, p["ln1_g"], p["ln1_b"]), p["W_q"], p["W_k"], p["W_v"], p["W_o"], num_heads)
    m = gelu(layer_norm(a, p["ln2_g"], p["ln2_b"]) @ p["W1"] + p["b1"]) @ p["W2"] + p["b2"]
    return a + m
