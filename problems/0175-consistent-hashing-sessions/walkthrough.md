## 1. What the problem is really asking

A chat session should keep landing on the same worker, because that worker holds its warm KV cache and open tool connections. The obvious routing rule, `hash(session) % N`, works until `N` changes. Then almost every session gets a new worker at once, and every warm cache is lost in the same second.

**Consistent hashing** fixes that. Put the workers on a circle of $2^{32}$ positions, put each session on the same circle, and give each session to the first worker point clockwise from it. When a worker joins, it takes over only the arcs that now end at its points. When a worker leaves, only its own sessions move, to the next point clockwise. Everyone else stays put.

Under the story this is **a sorted list plus a binary search with wraparound**. `add_node` and `remove_node` maintain the sorted list of points, `get_node` is one `bisect`, and `get_nodes` is a walk around the circle that skips nodes it has already seen.

The judge replays membership changes. After every `add` or `remove` it routes every session and records three things: the per-node session `counts`, the sessions that `moved`, and `only_changed_node_moved`, which says whether every moved session moved to or from the node that changed. `lookup` ops record `get_nodes(key, n)`. Because the hash is fixed, every count and every list is exact, so a ring that is "roughly right" fails.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `vnodes` | virtual points per physical node | node `w` gets points `"w#0"`, `"w#1"`, ..., `"w#{vnodes-1}"` |
| `name` | a worker name, like `"gpu-2"` | it is both the thing you return and part of each point's hash input |
| `key` | a session id, like `"sess-0003"` | hashed onto the same circle as the points |
| `n` | how many distinct nodes `get_nodes` should return | the owner first, then failovers clockwise |
| `stable_hash(s)` | sha256 of `str(s)` as a big integer | take it `% 2**32` for every position |

Three details are easy to miss:

- **The position formula is exact.** It's `stable_hash("%s#%d" % (name, i)) % 2**32`, with a `#` between the name and the index. Any other spelling (`name + str(i)`, `"%s-%d"`) puts points in different places, and every count changes.
- **"First point whose position is `>=` the key's position"** is exactly what `bisect.bisect_left` returns. If the result equals the number of points, the key lies past the last point and wraps to index 0.
- **`get_nodes` returns distinct physical nodes.** With virtual nodes, the next *point* clockwise is often the same worker. A failover list of `["gpu-1", "gpu-1"]` is useless, because both entries die together.

## 3. Trace Example 1 by hand

`vnodes=8`, sessions `sess-0000` to `sess-0005`. First `add worker-a`, then `add worker-b`, then `lookup sess-0003` with `n=2`.

After both adds, the ring holds 16 points. Sorted by position (out of $2^{32} = 4{,}294{,}967{,}296$):

| index | position | node |
|---|---|---|
| 0–4 | 2,519,998 … 246,315,140 | worker-b (five points) |
| 5 | 357,796,975 | worker-a |
| 6 | 678,550,338 | worker-a |
| 7 | 1,362,948,727 | worker-a |
| 8 | 1,843,372,632 | worker-b |
| 9 | 2,526,504,125 | worker-a |
| 10 | 2,697,909,552 | worker-a |
| 11 | 3,236,497,161 | worker-a |
| 12 | 3,288,771,299 | worker-b |
| 13 | 3,606,614,520 | worker-a |
| 14 | 4,201,652,757 | worker-a |
| 15 | 4,272,581,653 | worker-b |

Each session's position and the point `bisect_left` finds:

| session | position | index | owner after both adds |
|---|---|---|---|
| sess-0000 | 645,195,917 | 6 | worker-a |
| sess-0001 | 4,051,708,813 | 14 | worker-a |
| sess-0002 | 4,222,562,221 | 15 | **worker-b** |
| sess-0003 | 2,970,660,799 | 11 | worker-a |
| sess-0004 | 1,332,879,675 | 7 | worker-a |
| sess-0005 | 2,566,471,666 | 10 | worker-a |

**Op 1, `add worker-a`.** Only worker-a's eight points exist, so all six sessions go to it. Before this op every owner was `None`, so all six count as moved: `counts = {"worker-a": 6}`.

**Op 2, `add worker-b`.** Only `sess-0002` changes owner. Look at why. Its position, 4,222,562,221, is past worker-a's last point (4,201,652,757). On the ring with worker-a alone, it wrapped around to worker-a's first point. Now worker-b's point at 4,272,581,653 sits between it and the wrap, so that point claims it. The judge reports `counts = {"worker-a": 5, "worker-b": 1}`, `moved = ["sess-0002"]` and `only_changed_node_moved = True`.

**Op 3, `lookup sess-0003`, `n=2`.** Start at index 11 (worker-a), walk clockwise: index 12 is worker-b, a new node, so stop. Result `["worker-a", "worker-b"]`. If worker-a died, `sess-0003` would go to exactly the node listed second.

**The tricky hidden case, "one vnode wraparound".** With one point per node, agent-a sits at 0.1185 of the way round the circle and agent-b at 0.6157. agent-b owns the arc (0.1185, 0.6157], which holds 16 of the 40 sessions. agent-a owns everything else: the 7 sessions at or below 0.1185, *plus the 17 sessions past 0.6157 that wrap around*. That's `{"agent-a": 24, "agent-b": 16}`. A version that clamps instead of wrapping hands those 17 to agent-b, the last point, and reports `{"agent-a": 7, "agent-b": 33}`.

## 4. Key idea: why only the changed node's sessions move

A session's owner depends only on the *next point clockwise* from it. Adding a node inserts new points. A session changes owner only if one of the new points lands between it and its old owner's point, and then the new owner is the new node. Removing a node deletes its points. Only sessions whose next point was one of the deleted ones change owner, and they move to whatever point comes next.

So every move is to or from the changed node, which is what `only_changed_node_moved` checks. Compare the modulo rule on "scale out to six" (120 sessions, 32 vnodes, six adds, then a remove and re-add of node-3):

| op | ring: sessions moved | `% N`: sessions moved |
|---|---|---|
| add node-2 | 74 | 66 |
| add node-3 | 40 | 84 |
| add node-4 | 19 | 92 |
| add node-5 | 12 | 90 |
| add node-6 | 19 | 102 |
| remove node-3 | 28 | 97 |
| add node-3 | 28 | 97 |

The ring's moves shrink as the cluster grows, from 74 down to 12–19, because each new node takes a share of the existing arcs and nothing else. The modulo rule moves most of the sessions every time and reports `only_changed_node_moved = False` from the third add on. Notice also that removing node-3 and adding it back moves the same 28 sessions out and back again. The ring is a pure function of its membership, so a restarted worker gets back exactly its old sessions, which is what you want in a rolling restart.

## 5. Key idea: a stable hash, not `hash()`

Python's `hash()` on strings is salted per process. Two runs of `python3 -c "print(hash('agent-a#0'))"` printed `-7874848277050386965` and `4690780145165832138`. Two gateway replicas would build different rings and route the same session to different workers, and every deploy would reshuffle everyone. `stable_hash` is sha256-based, so every process on every machine places every point in the same spot. In a test run of `wrong_python_hash.py`, which uses `hash()`, every case except "empty ring" failed, and the exact counts it got change from run to run.

## 6. Plan before you code

```
state: vnodes, nodes (set of names), points (sorted list of (position, name)), positions (just the numbers)

add_node(name):     if already present, do nothing
                    add vnodes points, re-sort, refresh positions
remove_node(name):  if unknown, do nothing
                    filter its points out, refresh positions
_start(key):        i = bisect_left(positions, pos(key)); wrap i == len to 0
get_node(key):      None on an empty ring, else points[_start(key)].name
get_nodes(key, n):  [] on an empty ring
                    walk points from _start, wrapping, collecting names not yet seen,
                    stop at n names or when every node is collected
```

| situation | `get_node` | `get_nodes` |
|---|---|---|
| empty ring | `None` | `[]` |
| key past the last point | first point's node | starts at the first point |
| `n` larger than the node count | (n/a) | all nodes, in clockwise order |

## 7. Build it one piece at a time

**Step 1: placing points.** Sorting tuples sorts by position, then by name, which is the tie rule the problem gives. Keep a separate list of bare positions for `bisect`.

```python
def add_node(self, name):
    if name in self.nodes:
        return
    self.nodes.add(name)
    for i in range(self.vnodes):
        self.points.append((stable_hash("%s#%d" % (name, i)) % RING, name))
    self.points.sort()
    self.positions = [p for p, _ in self.points]
```

The early `return` keeps the ring clean. Without it, a second `add w1` appends eight more points at *exactly the same positions* as the first eight, because the hash inputs are identical. Routing doesn't change (I checked: that version still passes every case), but the point list doubles with every repeated add and the walk in `get_nodes` gets slower. The contract says the add does nothing, so make it do nothing.

**Step 2: removing points.** Rebuild the list without that node's points, and keep `positions` in step with it.

```python
def remove_node(self, name):
    if name not in self.nodes:
        return
    self.nodes.discard(name)
    self.points = [pt for pt in self.points if pt[1] != name]
    self.positions = [p for p, _ in self.points]
```

**Step 3: finding the owner with wraparound.**

```python
def _start(self, key):
    i = bisect.bisect_left(self.positions, stable_hash(key) % RING)
    return 0 if i == len(self.points) else i
```

`bisect_left`, not `bisect_right`. If a key's position equals a point's position exactly, the rule says that point (`>=`) owns it, and `bisect_right` would skip to the next one. With 32-bit positions an exact tie is rare by chance, but a session id can be built to hit one: the key `"w1#1"` hashes to exactly the position of w1's point 1. "key exactly on a ring point" does that, and `bisect_right` (`wrong_bisect_right.py`) sends it to w2. Clamping with `min(i, len - 1)` instead of wrapping is the bug in `wrong_no_wraparound.py`.

**Step 4: the failover walk.** Walk at most once round the ring. Collect names the first time you see them.

```python
def get_nodes(self, key, n):
    if not self.points:
        return []
    out, start = [], self._start(key)
    for j in range(len(self.points)):
        node = self.points[(start + j) % len(self.points)][1]
        if node not in out:
            out.append(node)
            if len(out) == n or len(out) == len(self.nodes):
                break
    return out
```

The `len(out) == len(self.nodes)` check stops the walk early once every node is listed, which is why `get_nodes("sess-0", 8)` on four nodes returns four names, not eight.

## 8. Full solution

```python
# bisect finds the first point at or after a key's position in O(log P)
import bisect

# a process-independent hash, so every gateway replica builds the same ring
from gc_runtime import stable_hash

# the ring has 2**32 positions, as the problem defines
RING = 2 ** 32


# a consistent-hash ring with virtual nodes, used to pin sessions to workers
class HashRing:
    # start empty; every node added later gets `vnodes` points
    def __init__(self, vnodes):
        self.vnodes = vnodes  # points per physical node, for balance
        self.nodes = set()  # physical nodes on the ring, for duplicate checks and counting
        self.points = []  # sorted (position, node)

    # bisect needs the bare positions, kept in the same order as points
    def _rebuild_keys(self):
        self.positions = [p for p, _ in self.points]  # parallel list of numbers only

    # put a node's virtual points on the ring
    def add_node(self, name):
        if name in self.nodes:  # already present: adding again must not double its points
            return  # nothing to do
        self.nodes.add(name)  # remember the node
        for i in range(self.vnodes):  # one point per virtual node
            # position from the exact "name#i" format, folded onto the 2**32 ring
            self.points.append((stable_hash("%s#%d" % (name, i)) % RING, name))
        self.points.sort()  # order by position, then name, as the tie rule says
        self._rebuild_keys()  # keep the bisect list in step

    # take a node's points off the ring
    def remove_node(self, name):
        if name not in self.nodes:  # unknown node: the contract says do nothing
            return  # nothing to remove
        self.nodes.discard(name)  # forget the node
        self.points = [pt for pt in self.points if pt[1] != name]  # drop every one of its points
        self._rebuild_keys()  # keep the bisect list in step

    # index of the first point at or after the key's position, wrapping round the ring
    def _start(self, key):
        i = bisect.bisect_left(self.positions, stable_hash(key) % RING)  # first position >= the key's
        return 0 if i == len(self.points) else i  # past the last point: wrap to the first

    # the node that owns a key
    def get_node(self, key):
        if not self.points:  # empty ring: nobody can own it
            return None  # the contract's answer for an empty ring
        return self.points[self._start(key)][1]  # the owner is the node of that point

    # the owner, then distinct failover nodes in clockwise order
    def get_nodes(self, key, n):
        if not self.points:  # empty ring: no owner and no failovers
            return []  # the contract's answer for an empty ring
        out = []  # distinct nodes in the order we meet them
        start = self._start(key)  # the same point get_node would pick
        for j in range(len(self.points)):  # at most one full lap
            node = self.points[(start + j) % len(self.points)][1]  # next point clockwise, wrapping
            if node not in out:  # skip extra points of a node we already listed
                out.append(node)  # a new physical node joins the list
                if len(out) == n or len(out) == len(self.nodes):  # asked-for count, or every node listed
                    break  # no point walking further
        return out  # owner first, then failovers
```

## 9. How the test cases map to the code

| test case | expected (from the judge) | what it checks |
|---|---|---|
| Example 1 | adding worker-b moves only `sess-0002`; lookup gives `["worker-a", "worker-b"]` | the basic ring, plus a session that stops wrapping when a new point lands past it |
| Example 2 | removing gpu-2 moves exactly its 7 sessions; counts end `{"gpu-1": 5, "gpu-3": 5}` | removal hands sessions to clockwise successors only |
| empty ring | `[]` from both lookups; after removing w1, counts are `{None: 3}` | the empty-ring branches in `get_node` and `get_nodes` |
| one vnode wraparound | `{"agent-a": 24, "agent-b": 16}` after the second add | the wrap from past the last point back to index 0 |
| duplicate add and unknown remove | the second `add w1` and `remove w9` move nothing | the two early returns |
| scale out to six | moves of 74, 40, 19, 12, 19, then 28 out and 28 back | minimal movement across many changes; `stable_hash` and the `#` format |
| failover lists | `sess-0` gives `["us-east-1", "us-east-3", "us-east-4"]`; with `n=8`, all four nodes | distinct nodes, clockwise order, stopping when every node is listed |
| rolling restart | each remove then re-add restores the counts `{"w-a": 11, "w-b": 7, "w-c": 16, "w-d": 26}` | the ring depends only on membership |
| key exactly on a ring point | after `add w2`, `w1#1` stays on w1 and `w2#2` moves to w2; lookup `["w1", "w2"]` | `>=` ownership: a key on a point belongs to that point (`bisect_left`) |
| two vnodes many keys | `{"n1": 56, "n2": 24}`; lookup `["n1", "n2"]` | few vnodes leave the split uneven, and the exact split is graded |

## 10. Complexity

With `N` nodes, `V` vnodes each and `P = N·V` points:

- `add_node`: O(V) hashes plus an O(P log P) sort. You could `bisect.insort` each point instead, for O(V·P) element moves.
- `remove_node`: O(P) to filter.
- `get_node`: one sha256 plus O(log P) for the binary search.
- `get_nodes`: O(log P) to start, then at most one lap, O(P · n) with the `node not in out` list check. A set makes that O(P).

Memory is O(P). At 8 nodes and 64 vnodes that is 512 points, which is nothing. Production rings use 100–200 vnodes per node, because balance improves with more points: the spread of each node's share shrinks roughly like $1/\sqrt{V}$. Even at 32 vnodes, "scale out to six" ends with node-5 at 9 sessions and node-2 at 33 out of 120, so the load is far from even at these sizes.

## 11. If you got Wrong Answer

- **Counts are wrong on the very first two-node step of almost every case, and `only_changed_node_moved` turns `False`.** You route with `stable_hash(key) % len(nodes)`, as in `wrong_modulo_n.py` (Example 1 gives worker-a 1 session instead of 5).
- **Counts differ every time you run the code.** You used `hash()`, as in `wrong_python_hash.py`.
- **"one vnode wraparound" gives `agent-b` 33 sessions instead of 16.** Keys past the last point are clamped to the last point instead of wrapping to index 0 (`wrong_no_wraparound.py`). It also fails "failover lists", "rolling restart" and "two vnodes many keys".
- **"failover lists" repeats a node, such as `us-east-3` where `us-east-4` was expected.** You return the next `n` points, not the next `n` distinct nodes (`wrong_duplicate_failover.py`).
- **Every count is off from the first two-node step, but `only_changed_node_moved` stays `True`.** Your point names don't match `"%s#%d"`, so the points sit somewhere else. The ring still behaves consistently, just not on the judge's ring.
- **"key exactly on a ring point" sends `w1#1` to w2, and the lookup gives `["w2", "w1"]`.** You used `bisect_right` (`wrong_bisect_right.py`), so a key sitting exactly on a point skips past it.
- **"duplicate add and unknown remove" fails with an error on `remove w9`.** You call `self.nodes.remove(name)` on an unknown node. The contract says to do nothing, so check membership first (or use `discard`).

## 12. Follow-ups an interviewer might ask

- *How do you weight a bigger GPU?* Give it more virtual nodes, in proportion to its capacity. Its share of the circle, and so of sessions, grows in proportion.
- *One hot tenant floods a single worker. What then?* Bounded-load consistent hashing (Google, 2017) caps each node at $(1+\epsilon)$ times the average load and spills extra keys to the next node clockwise. Or use power-of-two-choices for traffic that doesn't need stickiness (problem 132, load-balancer-p2c).
- *Is stickiness a correctness guarantee?* No. Keep the conversation state in a shared store (Redis, Postgres), so a moved session loses only its warm cache, not its data. The ring is a cache-hit optimization.
- *What do Envoy and Cassandra use?* Envoy offers `ring_hash` (this design) and `maglev`, a lookup table that trades a little extra movement for O(1) lookups and better balance. Cassandra and Dynamo assign token ranges on a ring the same way, and use the clockwise successors as replicas, just like `get_nodes`.
- *Where else does a stable hash route traffic?* Percentage rollouts bucket users the same way (problem 168, feature-flag-rollout), and once a session lands on its worker, identical concurrent requests can share one upstream call (problem 171, request-coalescing).
