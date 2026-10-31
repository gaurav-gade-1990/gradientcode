import math


def run(ns, expr, inputs):
    """Build `expr` from Values made by your class, call backward(), and report data plus input grads."""
    Value = ns["Value"]
    vals = {k: Value(float(v)) for k, v in inputs.items()}
    out = eval(expr, {"__builtins__": {}, "math": math}, dict(vals))
    out.backward()
    return {"data": float(out.data), "grads": {k: float(v.grad) for k, v in vals.items()}}
