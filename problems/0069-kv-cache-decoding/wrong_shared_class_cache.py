import numpy as np


class CachedSelfAttention:
    keys = []
    values = []

    def __init__(self, W_q, W_k, W_v, W_o, num_heads):
        self.W_q, self.W_k, self.W_v, self.W_o = W_q, W_k, W_v, W_o
        self.h = num_heads
        self.dh = W_q.shape[0] // num_heads

    def _split(self, a):
        return a.reshape(a.shape[0], self.h, self.dh).transpose(1, 0, 2)

    def prefill(self, x):
        return np.stack([self.step(row) for row in x])

    def step(self, x_t):
        self.keys.append(self._split((x_t @ self.W_k)[None, :]))
        self.values.append(self._split((x_t @ self.W_v)[None, :]))
        K = np.concatenate(self.keys, axis=1)
        V = np.concatenate(self.values, axis=1)
        q = self._split((x_t @ self.W_q)[None, :])
        s = q @ K.transpose(0, 2, 1) / np.sqrt(self.dh)
        s = s - s.max(axis=-1, keepdims=True)
        w = np.exp(s)
        w = w / w.sum(axis=-1, keepdims=True)
        return ((w @ V).transpose(1, 0, 2).reshape(1, -1) @ self.W_o)[0]
