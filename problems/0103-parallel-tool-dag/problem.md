Your account-review agent plans its tool calls as a dependency graph: look up the customer and the order in parallel, fetch payments once the order is known, score fraud once both are in, then draft the reply. Write the executor that runs that graph as fast as the concurrency limit allows.

`run_dag(loop, nodes, run_tool, max_concurrency)` gets:

- `loop`, a `gc_runtime.EventLoop` with virtual time.
- `nodes`, a list of `{"id": str, "tool": str, "deps": [ids]}`. The graph is acyclic and every dep is a listed id.
- `run_tool(node_id)`, which returns a **generator** that runs that node's tool on the loop. Run it with `result = yield loop.spawn(run_tool(node_id))` (or `yield from run_tool(node_id)`) inside one of your own tasks. It takes virtual time and either returns a string or raises `gc_runtime.ToolError`.
- `max_concurrency`, the most tools that may be running at once.

Rules:

| situation | what to do |
|---|---|
| a node is **ready** | every dep finished with status `"ok"`, and the node hasn't started |
| starting tools | at time 0, and right after each tool finishes, start ready nodes in **ascending `id` order** (string order) until `max_concurrency` tools are running |
| a tool raises `ToolError` | the node is `"failed"`; every node that depends on it, directly or transitively, is `"cancelled"` and never starts |
| everything else | keeps running; a failure doesn't stop independent branches |

Call each node's `run_tool` at most once, spawn your tasks on `loop`, then call `loop.run()` yourself. Return a dict that maps every node id to `"ok"`, `"failed"` or `"cancelled"`.

The judge records when each tool starts and ends in virtual time, the peak number of tools running at once, the makespan, and your statuses.

**Constraints**

- `1 <= len(nodes) <= 15`, `1 <= max_concurrency <= 6`
- Tool durations are positive, and in a correct schedule no two tools finish at the same instant
- Don't import `time`, `threading` or `asyncio`; all waiting happens on `loop`
