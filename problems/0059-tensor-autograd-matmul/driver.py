import numpy as np


def run(ns, expr, inputs):
    """Wrap each input in your Tensor, evaluate `expr`, call backward(), and report the loss and every input's grad."""
    Tensor = ns["Tensor"]
    ts = {k: Tensor(np.array(v, dtype=float)) for k, v in inputs.items()}
    out = eval(expr, {"__builtins__": {}}, dict(ts))
    data = np.asarray(out.data, dtype=float)
    if data.size != 1:
        raise ValueError("the expression should reduce to one element, got shape %s" % (data.shape,))
    out.backward()
    grads = {}
    for k, t in ts.items():
        g = np.zeros_like(t.data) if t.grad is None else np.asarray(t.grad, dtype=float)
        grads[k] = g
    return {"loss": float(data.reshape(())), "grads": grads}
