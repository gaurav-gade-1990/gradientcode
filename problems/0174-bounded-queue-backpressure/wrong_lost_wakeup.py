from collections import deque


class BoundedQueue:
    """get frees a slot but never wakes a blocked producer: the producers hang forever (lost wakeup)."""

    def __init__(self, loop, capacity, policy):
        self.loop = loop
        self.capacity = capacity
        self.policy = policy
        self.items = deque()
        self.getters = deque()   # futures of waiting consumers
        self.putters = deque()   # (future, item) of blocked producers
        self.dropped = []
        self.rejected = []
        self.max_depth = 0

    def __len__(self):
        return len(self.items)

    def _push(self, item):
        self.items.append(item)
        self.max_depth = max(self.max_depth, len(self.items))

    def put(self, item):
        if self.getters:
            self.loop.resolve(self.getters.popleft(), item)
            return True
        if len(self.items) < self.capacity:
            self._push(item)
            return True
        if self.policy == "drop_oldest":
            self.dropped.append(self.items.popleft())
            self._push(item)
            return True
        if self.policy == "reject":
            self.rejected.append(item)
            return False
        fut = self.loop.future()
        self.putters.append((fut, item))
        yield fut
        return True

    def get(self):
        if self.items:
            item = self.items.popleft()
            return item
        fut = self.loop.future()
        self.getters.append(fut)
        item = yield fut
        return item
