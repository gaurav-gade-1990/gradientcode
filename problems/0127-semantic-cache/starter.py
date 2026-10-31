import hashlib

from gc_runtime import embed


class SemanticCache:
    def __init__(self, clock, log, capacity=100, threshold=0.9, ttl_s=3600.0):
        self.clock = clock
        self.log = log
        self.capacity = capacity
        self.threshold = threshold
        self.ttl_s = ttl_s

    def get(self, tenant, model, system_prompt, query):
        # Write your code here
        pass

    def put(self, tenant, model, system_prompt, query, answer):
        # Write your code here
        pass
