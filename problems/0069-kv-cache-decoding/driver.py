import numpy as np


def run(ns, W_q, W_k, W_v, W_o, num_heads, xs, ops):
    """Replay `ops` against one cache per stream and collect every output in token order.

    xs[name] is that stream's token sequence, shape (T, d). Each op is [name, kind, n]:
    kind "prefill" feeds the next n tokens as a block, kind "step" feeds the next token alone.
    """
    Cls = ns["CachedSelfAttention"]
    d = W_q.shape[0]
    caches, pos, outs = {}, {}, {}
    for name, kind, n in ops:
        if name not in caches:
            caches[name] = Cls(W_q.copy(), W_k.copy(), W_v.copy(), W_o.copy(), num_heads)
            pos[name], outs[name] = 0, []
        x = xs[name]
        p = pos[name]
        if kind == "step":
            y = np.asarray(caches[name].step(x[p].copy()), dtype=float)
            if y.size != d:
                raise ValueError("step must return shape (%d,), got %s" % (d, y.shape))
            outs[name].append(y.reshape(1, d))
            pos[name] = p + 1
        else:
            y = np.asarray(caches[name].prefill(x[p:p + n].copy()), dtype=float)
            if y.shape != (n, d):
                raise ValueError("prefill must return shape (%d, %d), got %s" % (n, d, y.shape))
            outs[name].append(y)
            pos[name] = p + n
    return {name: np.concatenate(v, axis=0) for name, v in outs.items()}
