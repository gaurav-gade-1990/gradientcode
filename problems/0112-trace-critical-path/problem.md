A customer says your agent "took forever" to answer. You have the trace: a flat list of spans exported from your OpenTelemetry collector. Write the analysis that tells you where the time went.

`analyze_trace(spans)` gets a list of spans `{"id": str, "parent": str or None, "name": str, "kind": str, "start": float, "end": float}`, with times in milliseconds. Exactly one span has `parent: None`; that's the **root**. `kind` is a label such as `"llm"`, `"tool"`, `"agent"`, `"db"` or `"http"`.

**Reachability.** A span is part of the tree if following parents from it leads to the root. Spans that aren't, because their parent id is missing (dropped by the sampler) or because they descend from such a span, are **orphans**. List them and leave them out of every other number.

Return a dict:

| key | value |
|---|---|
| `duration` | `root.end - root.start` |
| `critical_path` | span ids from the root down. At each span, move to the child with the **latest `end`**; break ties by the latest `start`, then the smallest `id`. Stop at a span with no children. |
| `self_time` | `{id: t}` for every reachable span: its duration minus the length of the **union** of its children's intervals, each child clipped to the parent's `[start, end]` |
| `time_by_kind` | `{kind: t}` for every kind among reachable spans: the length of the **union** of that kind's span intervals (wall-clock time when at least one was running) |
| `orphans` | the orphan span ids, sorted |

Round each time to 9 decimals.

**Constraints**

- `1 <= len(spans) <= 200`, and ids are unique
- `start <= end` for every span; children may start before or end after their parent (clock skew, fire-and-forget work)
