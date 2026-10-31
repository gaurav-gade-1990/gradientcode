import numpy as np


def moe_forward(x, W_router, experts, k):
    T, E = x.shape[0], W_router.shape[1]
    logits = x @ W_router
    logits = logits - logits.max(axis=1, keepdims=True)
    probs = np.exp(logits)
    probs = probs / probs.sum(axis=1, keepdims=True)
    expert_idx = np.argsort(probs, axis=1, kind="stable")[:, ::-1][:, :k]
    top = np.take_along_axis(probs, expert_idx, axis=1)
    gates = top / top.sum(axis=1, keepdims=True)
    out = np.einsum("td,edo->teo", x, experts)
    y = np.sum(gates[:, :, None] * np.take_along_axis(out, expert_idx[:, :, None], axis=1), axis=1)
    f = np.bincount(expert_idx.ravel(), minlength=E) / (T * k)
    return y, expert_idx, gates, float(E * np.sum(f * probs.mean(axis=0)))
