import bisect

RING = 2 ** 32


class HashRing:
    """Uses the builtin hash(), which is salted per process: each gateway replica routes differently."""

    def __init__(self, vnodes):
        self.vnodes = vnodes
        self.nodes = set()
        self.points = []

    def add_node(self, name):
        if name in self.nodes:
            return
        self.nodes.add(name)
        self.points += [(hash("%s#%d" % (name, i)) % RING, name) for i in range(self.vnodes)]
        self.points.sort()

    def remove_node(self, name):
        if name in self.nodes:
            self.nodes.discard(name)
            self.points = [p for p in self.points if p[1] != name]

    def _start(self, key):
        i = bisect.bisect_left([p for p, _ in self.points], hash(key) % RING)
        return 0 if i == len(self.points) else i

    def get_node(self, key):
        return self.points[self._start(key)][1] if self.points else None

    def get_nodes(self, key, n):
        out = []
        if not self.points:
            return out
        s = self._start(key)
        for j in range(len(self.points)):
            node = self.points[(s + j) % len(self.points)][1]
            if node not in out:
                out.append(node)
                if len(out) == n:
                    break
        return out
