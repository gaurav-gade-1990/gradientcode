from gc_runtime import stable_hash


class HashRing:
    """hash(key) % len(nodes): adding one worker reshuffles almost every session and drops every warm cache."""

    def __init__(self, vnodes):
        self.nodes = []

    def add_node(self, name):
        if name not in self.nodes:
            self.nodes.append(name)
            self.nodes.sort()

    def remove_node(self, name):
        if name in self.nodes:
            self.nodes.remove(name)

    def get_node(self, key):
        if not self.nodes:
            return None
        return self.nodes[stable_hash(key) % len(self.nodes)]

    def get_nodes(self, key, n):
        if not self.nodes:
            return []
        i = stable_hash(key) % len(self.nodes)
        return [self.nodes[(i + j) % len(self.nodes)] for j in range(min(n, len(self.nodes)))]
