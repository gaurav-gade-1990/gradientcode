## Approach

Put every node on a ring of $2^{32}$ positions, `vnodes` times each. A session belongs to the first point clockwise from its own position. When a node joins, it takes over only the arcs that now end at its points, so only those sessions move, and they all move **to** the new node. When a node leaves, only its sessions move, to their clockwise successors.

```python
def add_node(self, name):
    if name in self.nodes:
        return
    self.nodes.add(name)
    for i in range(self.vnodes):
        self.points.append((stable_hash("%s#%d" % (name, i)) % RING, name))
    self.points.sort()

def _start(self, key):
    i = bisect.bisect_left(self.positions, stable_hash(key) % RING)
    return 0 if i == len(self.points) else i      # wrap past the last point
```

`get_nodes` walks clockwise from the same start and collects each node the first time it shows up. That gives the failover order: if the owner dies, its sessions go to exactly the node listed second.

Virtual nodes matter for balance. With one point per node the arcs have wildly different lengths (one node might own 60% of the ring). With $V$ points per node the load per node concentrates around $1/N$ with spread about $1/\sqrt{V}$.

## Common mistakes

- **`hash()` instead of a stable hash.** Python salts string hashes per process (`PYTHONHASHSEED`). Two gateway replicas would send the same session to different workers, and a restart reshuffles everything.
- **`hash(key) % N`.** Correct until the first scale event, then about $(N-1)/N$ of all sessions move at once and every warm cache is lost.
- **No wraparound.** Keys past the last point must go to the first point. Clamping them to the last point gives one node an extra arc and breaks the "only the changed node" rule.
- **Failover lists of points, not nodes.** With virtual nodes, the next point clockwise is often the same physical worker, so the "replica" dies with the primary.

## Production notes

- Envoy's `ring_hash` and `maglev` load balancers, Nginx `hash ... consistent`, and Cassandra/Dynamo token rings all use this design. Maglev trades a little movement for much faster lookups and better balance.
- Sticky sessions are a cache optimization, not a correctness guarantee. Keep the conversation state in a shared store (Redis, Postgres) so a moved session only loses warm KV/prefix cache, not data.
- Weight nodes by giving bigger GPUs more virtual nodes. Bounded-load consistent hashing (Google, 2017) caps any node at $(1+\epsilon)$ times the average and spills to the next node.
- Pair with `request-coalescing` (171) for the work a node does once a session lands there, and `load-balancer-p2c` (132) for stateless traffic that does not need stickiness.
