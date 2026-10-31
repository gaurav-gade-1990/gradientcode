# Incident: the limiter state was keyed by the upstream API key instead of the tenant,
# so one tenant's batch job used up everyone's quota (a noisy neighbour outage).
from gc_runtime import BadRequestError, RateLimitError


class TenantRateLimiter:
    def __init__(self, limits, clock, max_wait=0.0):
        self.limits, self.clock, self.max_wait = limits, clock, max_wait
        self.r = None
        self.k = None
        self.last = clock.now()

    def _refill(self, l):
        now = self.clock.now()
        if self.r is None:
            self.r, self.k = float(l["rpm"]), float(l["tpm"])
        dt = now - self.last
        self.r = min(l["rpm"], self.r + dt * l["rpm"] / 60.0)
        self.k = min(l["tpm"], self.k + dt * l["tpm"] / 60.0)
        self.last = now

    def acquire(self, tenant, tokens):
        if tenant not in self.limits or tokens > self.limits[tenant]["tpm"]:
            raise BadRequestError("bad request")
        l = self.limits[tenant]
        self._refill(l)
        wait = max(0.0, (1 - self.r) / (l["rpm"] / 60.0), (tokens - self.k) / (l["tpm"] / 60.0))
        if wait > self.max_wait:
            raise RateLimitError("over limit", retry_after=wait)
        self.r -= 1
        self.k -= tokens
        return wait

    def settle(self, tenant, reserved, actual):
        l = self.limits[tenant]
        self._refill(l)
        self.k = min(l["tpm"], self.k + reserved - actual)
