# Incident: a client stuck in a 429 retry loop was locked out for hours. Each rejected
# attempt still deducted from the buckets, so the debt grew faster than the refill.
from gc_runtime import BadRequestError, RateLimitError


class TenantRateLimiter:
    def __init__(self, limits, clock, max_wait=0.0):
        self.limits, self.clock, self.max_wait = limits, clock, max_wait
        now = clock.now()
        self.s = {t: {"r": float(l["rpm"]), "k": float(l["tpm"]), "last": now} for t, l in limits.items()}

    def _refill(self, tenant):
        s, l, now = self.s[tenant], self.limits[tenant], self.clock.now()
        dt = now - s["last"]
        s["r"] = min(l["rpm"], s["r"] + dt * l["rpm"] / 60.0)
        s["k"] = min(l["tpm"], s["k"] + dt * l["tpm"] / 60.0)
        s["last"] = now
        return s, l

    def acquire(self, tenant, tokens):
        if tenant not in self.limits or tokens > self.limits[tenant]["tpm"]:
            raise BadRequestError("bad request")
        s, l = self._refill(tenant)
        s["r"] -= 1
        s["k"] -= tokens
        wait = max(0.0, -s["r"] / (l["rpm"] / 60.0), -s["k"] / (l["tpm"] / 60.0))
        if wait > self.max_wait:
            raise RateLimitError("over limit", retry_after=wait)
        return wait

    def settle(self, tenant, reserved, actual):
        s, l = self._refill(tenant)
        s["k"] = min(l["tpm"], s["k"] + reserved - actual)
