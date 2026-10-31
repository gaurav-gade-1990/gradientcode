import bisect

from gc_runtime import stable_hash

RING = 2 ** 32


class HashRing:
    def __init__(self, vnodes):
        self.vnodes = vnodes
        self.nodes = set()
        self.points = []  # sorted (position, node)

    def _rebuild_keys(self):
        self.positions = [p for p, _ in self.points]

    def add_node(self, name):
        if name in self.nodes:
            return
        self.nodes.add(name)
        for i in range(self.vnodes):
            self.points.append((stable_hash("%s#%d" % (name, i)) % RING, name))
        self.points.sort()
        self._rebuild_keys()

    def remove_node(self, name):
        if name not in self.nodes:
            return
        self.nodes.discard(name)
        self.points = [pt for pt in self.points if pt[1] != name]
        self._rebuild_keys()

    def _start(self, key):
        i = bisect.bisect_left(self.positions, stable_hash(key) % RING)
        return 0 if i == len(self.points) else i

    def get_node(self, key):
        if not self.points:
            return None
        return self.points[self._start(key)][1]

    def get_nodes(self, key, n):
        if not self.points:
            return []
        out = []
        start = self._start(key)
        for j in range(len(self.points)):
            node = self.points[(start + j) % len(self.points)][1]
            if node not in out:
                out.append(node)
                if len(out) == n or len(out) == len(self.nodes):
                    break
        return out
