class CircuitBreaker:
    def __init__(self, clock, window_s=60.0, failure_rate=0.5, min_calls=5, open_timeout_s=30.0, half_open_probes=2):
        self.clock = clock
        self.state = "closed"
        # Write your code here

    def allow(self):
        # Return None to reject, or a permit
        pass

    def record(self, permit, ok):
        pass
