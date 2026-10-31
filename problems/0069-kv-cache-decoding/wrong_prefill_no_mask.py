import numpy as np


class CachedSelfAttention:
    def __init__(self, W_q, W_k, W_v, W_o, num_heads):
        self.W_q, self.W_k, self.W_v, self.W_o = W_q, W_k, W_v, W_o
        self.h = num_heads
        self.dh = W_q.shape[0] // num_heads
        self.K = np.zeros((num_heads, 0, self.dh))
        self.V = np.zeros((num_heads, 0, self.dh))

    def _split(self, a):
        n = a.shape[0]
        return a.reshape(n, self.h, self.dh).transpose(1, 0, 2)

    def prefill(self, x):
        n = x.shape[0]
        P = self.K.shape[1]
        q = self._split(x @ self.W_q)
        self.K = np.concatenate([self.K, self._split(x @ self.W_k)], axis=1)
        self.V = np.concatenate([self.V, self._split(x @ self.W_v)], axis=1)
        s = q @ self.K.transpose(0, 2, 1) / np.sqrt(self.dh)
        s = s - s.max(axis=-1, keepdims=True)
        w = np.exp(s)
        w = w / w.sum(axis=-1, keepdims=True)
        out = (w @ self.V).transpose(1, 0, 2).reshape(n, -1)
        return out @ self.W_o

    def step(self, x_t):
        return self.prefill(x_t[None, :])[0]
