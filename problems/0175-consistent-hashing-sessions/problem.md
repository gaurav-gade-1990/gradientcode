Your agent gateway pins each chat session to one worker so the worker's warm KV cache and tool connections are reused. Workers join and leave all day, and every change must move as few sessions as possible. Build the hash ring the gateway routes with.

Implement `class HashRing`:

| method | contract |
|---|---|
| `HashRing(vnodes)` | An empty ring. Every physical node will get `vnodes` virtual points. |
| `add_node(name)` | Add the node's points. Adding a node that is already on the ring does nothing. |
| `remove_node(name)` | Remove all of the node's points. Removing an unknown node does nothing. |
| `get_node(key)` | The node that owns `key`, or `None` when the ring is empty. |
| `get_nodes(key, n)` | Up to `n` **distinct** nodes for `key`: the owner first, then the failover nodes in clockwise order. Returns `[]` on an empty ring. |

Positions, using `stable_hash` from `gc_runtime`:

$$
\text{pos}(\text{node}, i) = \text{stable\_hash}(\texttt{"\{node\}\#\{i\}"}) \bmod 2^{32}, \quad i = 0, \dots, \text{vnodes}-1
$$

$$
\text{pos}(\text{key}) = \text{stable\_hash}(\text{key}) \bmod 2^{32}
$$

Sort all points by `(position, node name)`. A key is owned by the **first point whose position is `>=` the key's position**. If no point qualifies, wrap around to the first point. `get_nodes` starts at that same point and keeps walking clockwise (wrapping), collecting each node the first time it appears, until it has `n` nodes or has seen every node.

The judge replays a sequence of membership changes. After each `add` or `remove` it routes every session id and reports the per-node session counts, the sessions that moved, and whether every moved session moved to or from the changed node. `lookup` ops call `get_nodes`.

**Constraints**

- `1 <= vnodes <= 64`, at most 8 nodes, at most 120 session ids.
- Use `stable_hash` from `gc_runtime`. Do not use `hash()`, which is salted per process.
- `1 <= n <= 8`.
