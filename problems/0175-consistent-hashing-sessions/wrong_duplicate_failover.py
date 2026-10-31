import bisect

from gc_runtime import stable_hash

RING = 2 ** 32


class HashRing:
    """get_nodes takes the next n points, not the next n nodes: the 'failover' is often the same worker."""

    def __init__(self, vnodes):
        self.vnodes = vnodes
        self.nodes = set()
        self.points = []

    def add_node(self, name):
        if name in self.nodes:
            return
        self.nodes.add(name)
        self.points += [(stable_hash("%s#%d" % (name, i)) % RING, name) for i in range(self.vnodes)]
        self.points.sort()

    def remove_node(self, name):
        if name in self.nodes:
            self.nodes.discard(name)
            self.points = [p for p in self.points if p[1] != name]

    def _start(self, key):
        i = bisect.bisect_left([p for p, _ in self.points], stable_hash(key) % RING)
        return 0 if i == len(self.points) else i

    def get_node(self, key):
        return self.points[self._start(key)][1] if self.points else None

    def get_nodes(self, key, n):
        if not self.points:
            return []
        s = self._start(key)
        return [self.points[(s + j) % len(self.points)][1] for j in range(min(n, len(self.points)))]
