from collections import deque


class BoundedQueue:
    def __init__(self, loop, capacity, policy):
        self.loop = loop
        self.capacity = capacity
        self.policy = policy
        self.dropped = []
        self.rejected = []
        self.max_depth = 0
        # Write your code here

    def __len__(self):
        return 0

    def put(self, item):
        # Must be a generator: use `value = yield fut` only when you need to wait.
        if False:
            yield
        return False

    def get(self):
        if False:
            yield
        return None
