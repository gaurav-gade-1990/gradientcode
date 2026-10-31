## 1. What the problem is really asking

A customer says the agent "took forever". The trace has the answer, but a trace is just a flat list of spans: each one has an id, a parent id, a kind and a start and end time. You have to turn that list into the three numbers an engineer actually reads when debugging latency:

- **The critical path**: the chain of spans the request was waiting on, from the root down to a leaf.
- **Self time** per span: how long the span was busy doing its own work, not waiting on a child.
- **Time per kind**: how much wall-clock time the request spent with at least one LLM call (or tool call, or DB query) in flight.

Under the story, this is **a tree built from parent pointers plus one interval-union helper**. Build a children index, walk down from the root (anything you can't reach is an orphan), and use "length of the union of a set of intervals" for both self time and time per kind. The critical path is a greedy walk: at each span, step to the child that ends last.

The judge calls `analyze_trace(spans)` and compares the whole returned dict: `duration`, `critical_path`, `self_time`, `time_by_kind` and `orphans`.

## 2. Understand the inputs before writing anything

| field | what it is | how you use it |
|---|---|---|
| `id` | unique span id | the key in `self_time`, the entries of `critical_path` and `orphans` |
| `parent` | the parent's id, or `None` for the one root | build `children[parent]`; may point at an id that isn't in the list |
| `name` | e.g. `"tool.get_order"` | not needed for any number |
| `kind` | `"agent"`, `"llm"`, `"tool"`, `"db"`, `"http"` ... | the group key for `time_by_kind` |
| `start`, `end` | milliseconds, `start <= end` | intervals for self time, kinds and the path |

Three details are easy to miss:

- **Parallel children overlap.** An agent that fires three tool calls at once has three child spans covering the same stretch of time. Subtracting each child's duration from the parent counts that stretch three times. You need the **union**.
- **Children can stick out of their parent.** Clock skew, or fire-and-forget work like an email sent after the response, gives a child that starts before or ends after its parent. For self time, clip each child to the parent's `[start, end]` first. For `time_by_kind`, the problem doesn't clip: it's the union of that kind's raw intervals.
- **Orphans are transitive.** A span whose parent id is missing is an orphan, and so is every span below it, even though *their* parents exist. Walking down from the root handles both cases at once: you simply never reach them.

## 3. Trace Example 2 by hand

```
root  agent  0 ──────────────────────────────── 2000
plan  llm    0 ── 300
t1    tool       300 ────── 900
t2    tool       300 ──────────── 1400
  db  db           400 ────────── 1300
t3    tool        350 ───────── 1100
ans   llm                        1400 ────── 1950
```

**Root's self time.** Its children are `plan, t1, t2, t3, ans`. Sorted by start, then merged:

| interval | current merged run | action |
|---|---|---|
| (0, 300) | (0, 300) | start a run |
| (300, 900) | (0, 900) | starts at 300, not after 300: extend |
| (300, 1400) | (0, 1400) | extend |
| (350, 1100) | (0, 1400) | inside the run, no change |
| (1400, 1950) | (0, 1950) | starts exactly at the run's end: extend |

The union is 1950, so the root's self time is `2000 - 1950 = 50`. If you summed the child durations instead (`300 + 600 + 1100 + 750 + 550 = 3300`) you'd get `-1300`, which is what `wrong_sums_overlapping_children.py` reports.

**The rest of `self_time`.** `t2` has one child, `db` (400 to 1300, length 900), so its self time is `1100 - 900 = 200`. Every other span is a leaf, so its self time is its duration: `plan 300, t1 600, t3 750, db 900, ans 550`.

**`time_by_kind`.**

| kind | intervals | union |
|---|---|---|
| agent | (0, 2000) | 2000 |
| tool | (300, 900), (300, 1400), (350, 1100) | 300 to 1400 = **1100** |
| llm | (0, 300), (1400, 1950) | 300 + 550 = 850 |
| db | (400, 1300) | 900 |

Summing the tool durations gives 2450, more than the whole request's wall-clock time spent in tools could ever be.

**Critical path.** The root's children end at 300, 900, 1400, 1100 and 1950. The latest is `ans`, which has no children, so the path is `["root", "ans"]`. `t2` is the longest child (1100 ms), but following it gives `["root", "t2", "db"]`, which points you at the wrong span: the user was still waiting at 1950 because of `ans`.

**The tie-break case, "end ties broken by later start then id".** Under `r` (0 to 100) are `k2` (10, 90), `k1` (10, 90) and `k0` (0, 90). All three end at 90. The later start eliminates `k0`, and the smallest id picks `k1` over `k2`. `k1` has a child `k1a`, so the path is `["r", "k1", "k1a"]`.

## 4. Key idea: one union helper does two jobs

Both self time and time per kind ask the same question: "for how many milliseconds was at least one of these intervals active?" Answer it once:

1. Sort the intervals by start.
2. Keep a current run `(cur_s, cur_e)`. If the next interval starts after `cur_e`, the run is finished: add its length and start a new one. Otherwise extend `cur_e` to `max(cur_e, e)`.
3. Add the last run.

Skip empty intervals (`e <= s`). Clipping can produce them: a child that lies entirely after its parent's end clips to `(start, parent_end)` with `start > parent_end`.

## 5. Key idea: the critical path follows the latest end

A parent finishes after all the children it waits on. So the child that ends last is the one still running just before the parent could finish, and that's where latency is being set. Repeat from that child until you reach a leaf. "Longest child" sounds similar but is wrong: in "critical path is latest end, not longest", `long` (0 to 800) is the longest child of `r`, yet `late` (900 to 990) is what the request was waiting on at the end, so the path is `["r", "late"]`.

The rule uses raw `end` values, unclipped. In "child outlives parent", the fire-and-forget `tool` span (800 to 1500) ends after the root (0 to 1000), and the expected path is `["r", "tool"]`. Its self time for the root is clipped, though: the root's self time is `1000 - (600 + 200) = 200`.

One `min` with a tuple key does the selection and all tie-breaks: `key=(-end, -start, id)` means latest end, then latest start, then smallest id.

## 6. Plan before you code

```
root = the span with parent None
children = {parent_id: [spans]}
reachable = DFS from root over children; orphans = sorted ids not reached
for each reachable span s:
    clipped = [(max(c.start, s.start), min(c.end, s.end)) for c in children[s]]
    self_time[s] = duration(s) - union_length(clipped)
path = [root]; while current has children: step to min(children, key=(-end, -start, id))
for each kind among reachable spans: time_by_kind[kind] = union_length(their intervals)
round every time to 9 decimals
```

| number | which spans | clipped? | combine how |
|---|---|---|---|
| `self_time[s]` | `s`'s direct children | yes, to `s` | `duration - union` |
| `time_by_kind[k]` | all reachable spans of kind `k` | no | `union` |
| `critical_path` | children at each level | no | `min` by `(-end, -start, id)` |

## 7. Build it one piece at a time

**Step 1: the union helper.** Sorting tuples sorts by start, then end. The `s > cur_e` test means touching intervals like (0, 300) and (300, 900) merge; either way the total is the same.

```python
def _union_length(intervals):
    total, cur_s, cur_e = 0.0, None, None
    for s, e in sorted(intervals):
        if e <= s:
            continue
        if cur_e is None or s > cur_e:
            if cur_e is not None:
                total += cur_e - cur_s
            cur_s, cur_e = s, e
        else:
            cur_e = max(cur_e, e)
    if cur_e is not None:
        total += cur_e - cur_s
    return total
```

**Step 2: the tree and the orphans.** Index children by parent id, including parent ids that don't exist; nobody ever looks those up from the root, which is exactly what makes their subtrees unreachable.

```python
    root = next(s for s in spans if s["parent"] is None)
    children = defaultdict(list)
    for s in spans:
        if s["parent"] is not None:
            children[s["parent"]].append(s)
    reachable, stack = [], [root]
    while stack:
        s = stack.pop()
        reachable.append(s)
        stack.extend(children[s["id"]])
    seen = {s["id"] for s in reachable}
    orphans = sorted(s["id"] for s in spans if s["id"] not in seen)
```

Checking only "does my parent id exist?" isn't enough. In Example 3, `y`'s parent `x` is in the list, but `x`'s parent `gone` isn't, so both are orphans: `["x", "y"]`.

**Step 3: self time.** Clip, then union.

```python
    self_time = {}
    for s in reachable:
        clipped = [(max(c["start"], s["start"]), min(c["end"], s["end"])) for c in children[s["id"]]]
        self_time[s["id"]] = round((s["end"] - s["start"]) - _union_length(clipped), 9)
```

**Step 4: the path and the kinds.**

```python
    path, cur = [root["id"]], root
    while children[cur["id"]]:
        cur = min(children[cur["id"]], key=lambda c: (-c["end"], -c["start"], c["id"]))
        path.append(cur["id"])

    kinds = defaultdict(list)
    for s in reachable:
        kinds[s["kind"]].append((s["start"], s["end"]))
    time_by_kind = {k: round(_union_length(v), 9) for k, v in sorted(kinds.items())}
```

Only reachable spans go into `kinds`. Orphans must not leak into any number.

## 8. Full solution

Every line carries a comment saying what it does and why.

```python
# A dict of lists that creates an empty list for any parent id, including ones that don't exist.
from collections import defaultdict


# Milliseconds during which at least one interval was active: sort, then merge overlapping runs.
def _union_length(intervals):
    total, cur_s, cur_e = 0.0, None, None  # total so far, and the run being merged (none yet)
    # Sorting by start lets one pass find every overlap.
    for s, e in sorted(intervals):
        # Empty or inverted after clipping: contributes nothing.
        if e <= s:
            continue  # skip it
        # No run yet, or this interval starts after the current run ends: a gap.
        if cur_e is None or s > cur_e:
            # Close the finished run, if there is one.
            if cur_e is not None:
                total += cur_e - cur_s  # bank its length
            cur_s, cur_e = s, e  # this interval starts a new run
        # It overlaps or touches the current run.
        else:
            cur_e = max(cur_e, e)  # extend the run; a nested interval changes nothing
    # The last run is still open after the loop.
    if cur_e is not None:
        total += cur_e - cur_s  # bank it too
    return total  # the union's length, never more than the covered span


# Turn a flat span list into duration, critical path, self times, time per kind and orphans.
def analyze_trace(spans):
    root = next(s for s in spans if s["parent"] is None)  # exactly one span has no parent
    children = defaultdict(list)  # parent id -> its child spans
    # Index every span under its parent id.
    for s in spans:
        # The root has no parent to file it under.
        if s["parent"] is not None:
            children[s["parent"]].append(s)  # missing parents still get an entry, never visited
    reachable, stack = [], [root]  # DFS from the root defines the tree
    # Visit every span reachable through child links.
    while stack:
        s = stack.pop()  # any order is fine; we only need the set
        reachable.append(s)  # this span belongs to the request
        stack.extend(children[s["id"]])  # and so do its children
    seen = {s["id"] for s in reachable}  # fast membership test
    # Anything not reached hangs off a dropped parent, directly or transitively.
    orphans = sorted(s["id"] for s in spans if s["id"] not in seen)

    self_time = {}  # id -> time spent not waiting on any child
    # Self time only for spans in the tree.
    for s in reachable:
        # Clip each child to the parent so work outside the parent's window isn't subtracted.
        clipped = [(max(c["start"], s["start"]), min(c["end"], s["end"])) for c in children[s["id"]]]
        # Union, not sum: parallel children overlap and must be counted once.
        self_time[s["id"]] = round((s["end"] - s["start"]) - _union_length(clipped), 9)

    path, cur = [root["id"]], root  # the critical path starts at the root
    # Keep descending until we reach a leaf.
    while children[cur["id"]]:
        # The child that ends last is what the span was waiting on; ties: later start, then smaller id.
        cur = min(children[cur["id"]], key=lambda c: (-c["end"], -c["start"], c["id"]))
        path.append(cur["id"])  # record the step

    kinds = defaultdict(list)  # kind -> raw intervals of reachable spans
    # Group reachable spans by kind; orphans stay out.
    for s in reachable:
        kinds[s["kind"]].append((s["start"], s["end"]))  # unclipped, as the problem defines it
    # Wall-clock time with at least one span of that kind in flight.
    time_by_kind = {k: round(_union_length(v), 9) for k, v in sorted(kinds.items())}
    # Assemble the report with sorted keys so the output is stable.
    return {
        "duration": round(root["end"] - root["start"], 9),
        "critical_path": path,
        "self_time": dict(sorted(self_time.items())),
        "time_by_kind": time_by_kind,
        "orphans": orphans,
    }
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | path `[a, d]`, root self time 20, llm 730 | sequential children: union equals sum here |
| Example 2 | root self time 50, tool 1100, path `[root, ans]` | the union for overlapping children and for a kind |
| Example 3 | orphans `[x, y]`; llm 460, no tool or http kind | transitive orphans, kept out of every number |
| child outlives parent | root self time 200, tool 700, path `[r, tool]` | clipping for self time only |
| deep chain | path `[r, s1, s3, s5]`, `s1` self time 150 | the walk continues to a leaf several levels down |
| critical path is latest end, not longest | path `[r, late]` | latest end, not longest duration |
| end ties broken by later start then id | path `[r, k1, k1a]` | both tie-breaks in the `min` key |
| nested parallel llm calls | `g` self time 200, llm 800, path `[r, t]` | union across a nested level; the sum would say 1200 |
| single span | everything 99.75, path `[only]` | no children: self time equals duration |
| orphan subtree with deep children | orphans `[o1, o2, o3]`, path `[r, a2]` | a three-deep orphan subtree; re-parented under the root, `o1` (ends 350) would hijack the path as `[r, o1, o2, o3]` |
| fractional ms | root 1.625, `b` 0.625, tool 4.625 | non-integer times through clipping and union |

## 10. Complexity

Building the index and the DFS are O(n) for n spans. Self time sorts each span's children once, so across all spans it's O(n log n). The critical path visits at most one span per level. Time per kind sorts each kind's intervals, O(n log n) in total. Memory is O(n).

In production a single agent trace can have thousands of spans (every model call, tool call, retry and DB query), and you run this over millions of traces to get latency percentiles per span kind. The sort-and-merge is cheap enough for that. The harder production problem is sampling: head-based sampling drops spans and creates exactly the orphans this function has to tolerate, which is why tail-based sampling in the collector keeps slow traces whole.

## 11. If you got Wrong Answer

- **The root's self time is negative (`-1300` in "Example 2").** You subtract the sum of child durations instead of the length of their union.
- **The root's self time is `-300` in "child outlives parent".** You don't clip children to the parent's interval.
- **`tool` is 2450 in "Example 2", or `llm` is 1200 in "nested parallel llm calls".** `time_by_kind` sums durations instead of taking the union.
- **The path is `[root, t2, db]` in "Example 2" or `[r, long]` in the "latest end" case.** You follow the longest child, not the one that ends last.
- **"end ties broken by later start then id" gives `[r, k0]`.** Your key skips the `-start` tie-break and falls straight to the id.
- **`orphans` is empty in "Example 3", or only `x` is listed.** You re-parented orphans under the root, or you only checked whether each span's direct parent exists.
- **`tool` is 200 instead of 700 in "child outlives parent".** You clipped spans to the root for `time_by_kind`; the problem asks for the union of the raw intervals.

## 12. Follow-ups an interviewer might ask

- *The latest-ending child isn't always the bottleneck. Can you do better?* Jaeger's critical path also walks backwards through the gaps between sequential children: after picking the last child, it looks for the child that ended just before that one started. That catches a slow step earlier in a sequence that the latest-end rule skips.
- *Which number would you use for cost?* Sum, not union. Three parallel LLM calls of 500 ms are 500 ms of user waiting but 1500 ms of paid model time. Report both; the OpenTelemetry GenAI conventions (`gen_ai.usage.input_tokens`) let you attach tokens to each span for real cost.
- *How do you turn per-trace numbers into alerts?* Aggregate latency by kind into percentiles (problem 138, streaming-latency-percentiles) and alert on error-budget burn (problem 139, slo-burn-rate-alerts).
- *Where do these spans come from?* Your executor records them. Problem 103 (parallel-tool-dag) produces exactly this start and end data for each tool call it schedules.
- *What would you do about the fire-and-forget email that shows up on the critical path?* Mark such work with a span link or a "follows from" relationship instead of a parent-child edge, so it's still traced but no longer counted as part of the request's latency.
