# Incident: only TPM was enforced. A tenant sending thousands of tiny classification calls
# stayed under TPM but blew through the provider's RPM and got the shared key throttled.
from gc_runtime import BadRequestError, RateLimitError


class TenantRateLimiter:
    def __init__(self, limits, clock, max_wait=0.0):
        self.limits, self.clock, self.max_wait = limits, clock, max_wait
        now = clock.now()
        self.s = {t: {"k": float(l["tpm"]), "last": now} for t, l in limits.items()}

    def _refill(self, tenant):
        s, l, now = self.s[tenant], self.limits[tenant], self.clock.now()
        s["k"] = min(l["tpm"], s["k"] + (now - s["last"]) * l["tpm"] / 60.0)
        s["last"] = now
        return s, l

    def acquire(self, tenant, tokens):
        if tenant not in self.limits or tokens > self.limits[tenant]["tpm"]:
            raise BadRequestError("bad request")
        s, l = self._refill(tenant)
        wait = max(0.0, (tokens - s["k"]) / (l["tpm"] / 60.0))
        if wait > self.max_wait:
            raise RateLimitError("over limit", retry_after=wait)
        s["k"] -= tokens
        return wait

    def settle(self, tenant, reserved, actual):
        s, l = self._refill(tenant)
        s["k"] = min(l["tpm"], s["k"] + reserved - actual)
