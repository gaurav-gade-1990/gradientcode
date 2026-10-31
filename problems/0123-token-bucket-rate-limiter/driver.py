from gc_runtime import BadRequestError, Clock, RateLimitError


def run(ns, limits, ops, max_wait=0.0):
    """Replay gateway traffic on a virtual clock and record what the limiter decided for each op."""
    clock = Clock()
    limiter = ns["TenantRateLimiter"](limits, clock, max_wait)
    out = []
    for op in ops:
        if op["t"] > clock.now():
            clock.advance(op["t"] - clock.now())
        if op["op"] == "settle":
            limiter.settle(op["tenant"], op["reserved"], op["actual"])
            out.append(["settled", None])
            continue
        try:
            w = limiter.acquire(op["tenant"], op["tokens"])
            out.append(["admit", round(float(w), 6)])
        except RateLimitError as e:
            ra = e.retry_after
            out.append(["429", None if ra is None else round(float(ra), 6)])
        except BadRequestError:
            out.append(["400", None])
    return out
