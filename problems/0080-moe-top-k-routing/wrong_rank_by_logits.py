# Bug: ranks experts by logits instead of probabilities, so probabilities that underflow to 0.0 no longer tie to the lower index.
import numpy as np


def moe_forward(x, W_router, experts, k):
    T, E = x.shape[0], W_router.shape[1]
    logits = x @ W_router
    logits = logits - logits.max(axis=1, keepdims=True)
    probs = np.exp(logits)
    probs = probs / probs.sum(axis=1, keepdims=True)

    expert_idx = np.argsort(-logits, axis=1, kind="stable")[:, :k]
    top = np.take_along_axis(probs, expert_idx, axis=1)
    gates = top / top.sum(axis=1, keepdims=True)

    expert_out = np.einsum("td,edo->teo", x, experts)          # (T, E, d_out)
    chosen = np.take_along_axis(expert_out, expert_idx[:, :, None], axis=1)  # (T, k, d_out)
    y = np.sum(gates[:, :, None] * chosen, axis=1)

    f = np.bincount(expert_idx.ravel(), minlength=E) / (T * k)
    P = probs.mean(axis=0)
    aux_loss = float(E * np.sum(f * P))
    return y, expert_idx, gates, aux_loss
