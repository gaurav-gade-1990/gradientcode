from gc_runtime import BadRequestError, RateLimitError


class TenantRateLimiter:
    def __init__(self, limits, clock, max_wait=0.0):
        self.limits = limits
        self.clock = clock
        self.max_wait = max_wait

    def acquire(self, tenant, tokens):
        # Write your code here
        pass

    def settle(self, tenant, reserved, actual):
        # Write your code here
        pass
