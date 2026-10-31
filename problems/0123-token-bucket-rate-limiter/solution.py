from gc_runtime import BadRequestError, RateLimitError


class _Bucket:
    def __init__(self, capacity, per_minute, now):
        self.capacity = float(capacity)
        self.rate = per_minute / 60.0
        self.level = float(capacity)
        self.last = now

    def refill(self, now):
        self.level = min(self.capacity, self.level + self.rate * (now - self.last))
        self.last = now

    def wait_for(self, need):
        return max(0.0, (need - self.level) / self.rate)


class TenantRateLimiter:
    def __init__(self, limits, clock, max_wait=0.0):
        self.limits = limits
        self.clock = clock
        self.max_wait = max_wait
        now = clock.now()
        self.req = {t: _Bucket(l["rpm"], l["rpm"], now) for t, l in limits.items()}
        self.tok = {t: _Bucket(l["tpm"], l["tpm"], now) for t, l in limits.items()}

    def acquire(self, tenant, tokens):
        if tenant not in self.limits:
            raise BadRequestError("unknown tenant %r" % tenant)
        if tokens > self.limits[tenant]["tpm"]:
            raise BadRequestError("request needs %d tokens; tenant TPM is %d" % (tokens, self.limits[tenant]["tpm"]))
        now = self.clock.now()
        rb, tb = self.req[tenant], self.tok[tenant]
        rb.refill(now)
        tb.refill(now)
        wait = max(rb.wait_for(1), tb.wait_for(tokens))
        if wait > self.max_wait:
            raise RateLimitError("tenant %s over limit" % tenant, retry_after=wait)
        rb.level -= 1
        tb.level -= tokens
        return wait

    def settle(self, tenant, reserved, actual):
        tb = self.tok[tenant]
        tb.refill(self.clock.now())
        tb.level = min(tb.capacity, tb.level + reserved - actual)
