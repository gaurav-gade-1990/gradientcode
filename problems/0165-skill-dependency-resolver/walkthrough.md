## 1. What the problem is really asking

Teams publish skills to an internal marketplace, and each version of a skill pins the skills it needs with semver ranges. When someone installs a set of skills, the platform has to pick exactly one version of every skill involved so that every range is satisfied, or explain precisely why that's impossible.

This is the job npm, Cargo and pip do, cut down to its core:

- **A semver matcher.** Decide whether a version like `1.10.0` satisfies a range like `^1.4.0` or `>=1.9.0 <2.0.0`.
- **A depth-first search with backtracking.** Pick a skill, try its versions newest first, add that version's dependency ranges, and recurse. If you hit a contradiction, undo and try the next version.
- **A topological sort** for the install order, with ties broken by name.

The problem fixes the search order exactly, because different orders find different valid answers. The judge compares the whole result: the `versions` map and `install_order` on success, or the `package` and its sorted `requirements` at the **first** dead end on failure. So you're not just finding *a* solution. You're reproducing *the* solution this search finds.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `registry` | `{skill: {version: {dep: range}}}` | the versions you can try and what each one needs |
| `requirements` | `{skill: range}` | the root constraints, tagged `by: "root"` |
| `reqs` | your own `{skill: [(by, range), ...]}` | every constraint collected so far |
| `chosen` | your own `{skill: version}` | the decisions on the current branch |
| `by` | `"root"` or `"skill@version"` | who imposed a constraint, for the failure report |

Three details are easy to miss:

- **Versions compare as integer tuples.** As strings, `"1.10.0" < "1.9.2"`, because `"1" < "9"`. Parse `"1.10.0"` into `(1, 10, 0)` once and compare tuples.
- **Caret depends on the leftmost non-zero part.** `^1.2.3` allows `<2.0.0`, `^0.2.3` allows `<0.3.0`, and `^0.0.3` allows only `0.0.3`. For 0.x packages a minor bump is treated as breaking. Tilde is different again: `~1.2.3` always allows patch changes only, `<1.3.0`.
- **A skill missing from the registry has no candidates.** That's a dead end, not a crash. `"unknown skill"` asks for `jira-sync`, and the answer is a conflict on `jira-sync` with its one root requirement.

## 3. Trace Example 2 by hand

Requirements: `crm-connector ^1.0.0`, `pdf-reader ^1.0.0`, `vector-search ^3.2.0`. The search always picks the alphabetically first unchosen skill in `reqs`. Here's the search, step by step, logged from an instrumented copy of the solution:

```
pick crm-connector  [root ^1.0.0]                     candidates 1.2.0, 1.0.0
  try 1.2.0  -> adds auth-oauth ^0.4.0, llm-core >=2.0.0
  pick auth-oauth   [crm@1.2.0 ^0.4.0]                candidates 0.4.0
    try 0.4.0 -> adds http-tools ^3.0.0
    pick http-tools [auth@0.4.0 ^3.0.0]               candidates 3.0.0
      try 3.0.0 -> adds llm-core ^2.0.0
      pick llm-core [crm@1.2.0 >=2.0.0, http@3.0.0 ^2.0.0]   candidates 2.0.0
        try 2.0.0
        pick pdf-reader [root ^1.0.0]                 candidates 1.1.0, 1.0.0
          try 1.1.0
          pick vector-search [root ^3.2.0]            candidates 3.2.0
            try 3.2.0 -> needs llm-core >=1.9.0 <2.0.0, but llm-core is 2.0.0: DEAD END at llm-core
          try 1.0.0 -> needs llm-core ^1.0.0, but llm-core is 2.0.0: dead end
  (auth-oauth, http-tools, llm-core have no other candidates: back up to crm-connector)
  try 1.0.0  -> adds auth-oauth ^0.3.0, http-tools ~2.1.0
  pick auth-oauth   [crm@1.0.0 ^0.3.0]                candidates 0.3.4, 0.3.0
    try 0.3.4 -> adds http-tools ^2.1.0
    pick http-tools [crm@1.0.0 ~2.1.0, auth@0.3.4 ^2.1.0]   candidates 2.1.0
      try 2.1.0 -> adds llm-core ^1.4.0
      pick llm-core [http@2.1.0 ^1.4.0]               candidates 1.10.0, 1.9.2, 1.4.0
        try 1.10.0
        pick pdf-reader [root ^1.0.0]                 candidates 1.1.0, 1.0.0
          try 1.1.0 -> needs llm-core ^2.0.0, but llm-core is 1.10.0: dead end
          try 1.0.0 -> needs llm-core ^1.0.0: fine
          pick vector-search [root ^3.2.0]            candidates 3.2.0
            try 3.2.0 -> needs llm-core >=1.9.0 <2.0.0: 1.10.0 fits
every skill chosen: done
```

The answer is `auth-oauth 0.3.4`, `crm-connector 1.0.0`, `http-tools 2.1.0`, `llm-core 1.10.0`, `pdf-reader 1.0.0`, `vector-search 3.2.0`. Notice three things:

- **Backtracking went all the way to the first decision.** The newest `crm-connector` locks `llm-core` to 2.x, which `vector-search` can't accept. Only by undoing `crm-connector 1.2.0` does the search find a solution.
- **`http-tools` gets only `2.1.0`.** `~2.1.0` from `crm-connector 1.0.0` rules out `2.3.1`, even though `auth-oauth`'s `^2.1.0` would allow it.
- **`llm-core 1.10.0` beats `1.9.2`.** Numerically, 10 > 9.

The search did hit dead ends on the way, but it succeeded, so none of them are reported.

**Example 3, the failure.** Requirements `crm-connector ^1.2.0` and `vector-search *`. Now `crm-connector` has only `1.2.0` to offer. The chain runs exactly as above through `llm-core 2.0.0`, then `vector-search 3.2.0` adds `>=1.9.0 <2.0.0` against the chosen `2.0.0`. That's the first dead end, and it's at `llm-core`. Its constraint list at that moment, including the new range, sorted by `(by, range)`:

```python
{"package": "llm-core", "requirements": [
    {"by": "crm-connector@1.2.0", "range": ">=2.0.0"},
    {"by": "http-tools@3.0.0", "range": "^2.0.0"},
    {"by": "vector-search@3.2.0", "range": ">=1.9.0 <2.0.0"}]}
```

That list reads as an explanation: two packages need `llm-core` 2.x and one needs it below 2.

## 4. Key idea: two kinds of dead end

The search can fail at a skill in two places, and both get reported the same way:

| where | what happened | reported package | its requirements |
|---|---|---|---|
| step 3, picking `p` | no registry version of `p` satisfies every range in `reqs[p]` | `p` | `reqs[p]` |
| step 4, trying `p@v` | one of `v`'s new ranges contradicts a dependency **already chosen** | that dependency | its list, including the new range |

"conflict with an already chosen version" shows the second kind. The root asks for `llm-core =1.9.2` and `pdf-reader >=1.1.0`. `llm-core` comes first alphabetically and is chosen at `1.9.2`. Then `pdf-reader 1.1.0` needs `llm-core ^2.0.0`. `llm-core` is already decided, so you don't wait for it to come up again: the candidate fails right there, and the report is `llm-core` with `[pdf-reader@1.1.0 ^2.0.0, root =1.9.2]`.

Why check already-chosen skills immediately? Because the search never revisits a chosen skill. If you only appended the new range and moved on, nothing would ever check it, and you'd return a lockfile that breaks a constraint.

"dependency missing from marketplace" is the first kind. `slack-notify 0.1.0` needs `webhooks ^1.0.0`, and `webhooks` isn't in the registry, so picking it finds no candidates.

## 5. Key idea: copies make undo free

Backtracking needs "undo everything from this candidate". The simplest way to get it is to never mutate shared state: for each candidate, build a new `reqs` (copying each list) and pass `dict(chosen, **{p: v})` down. When a recursive call fails, you just drop those copies and the caller's `reqs` and `chosen` are untouched. With at most 20 skills, the copying costs nothing worth worrying about.

Record the first dead end in an outer list that the recursion appends to only while it's empty. Every later dead end, even on a branch that also fails, is ignored.

## 6. Plan before you code

```
parse(v) -> (major, minor, patch)
term_ok(term, v): "*", ^, ~, >=, <=, >, <, =, or a bare version
satisfies(range, v): every space-separated term is ok

solve(chosen, reqs):
    undecided = sorted skills in reqs not in chosen
    none left -> return chosen
    p = undecided[0]
    candidates = p's versions, highest first by parse, that satisfy all of reqs[p]
    none -> record dead end (p, reqs[p]); fail
    for v in candidates:
        new = copy of reqs
        for dep, rng in sorted(v's deps):
            append (p@v, rng) to new[dep]
            first dep that is chosen and doesn't satisfy rng -> conflict
        conflict -> record dead end (dep, new[dep]); next v
        result = solve(chosen + {p: v}, new); success -> return it
    fail

install order: Kahn's algorithm with a min-heap of ready skills
```

## 7. Build it one piece at a time

**Step 1: one range term.** Check the two-character operators before the one-character ones, or `">=1.0.0"` would match `">"` and then fail to parse `"=1.0.0"`:

```python
def term_ok(term, v):
    if term == "*":
        return True
    if term[0] == "^":
        lo = parse(term[1:])
        if lo[0] > 0:
            hi = (lo[0] + 1, 0, 0)
        elif lo[1] > 0:
            hi = (0, lo[1] + 1, 0)
        else:
            hi = (0, 0, lo[2] + 1)
        return lo <= v < hi
    if term[0] == "~":
        lo = parse(term[1:])
        return lo <= v < (lo[0], lo[1] + 1, 0)
    for op in (">=", "<=", ">", "<", "="):
        ...
    return v == parse(term)
```

"comparators" exercises every operator: `>1.4.0 <1.10.0` gives `llm-core 1.9.2`, `=2.1.0` pins `http-tools`, and `<=1.0.0 >0.9.0` gives `pdf-reader 1.0.0`.

**Step 2: candidates.** Sort with `key=parse`, not plain string order:

```python
        versions = sorted(registry.get(p, {}), key=parse, reverse=True)
        candidates = [v for v in versions if all(satisfies(r, v) for _, r in reqs[p])]
```

`registry.get(p, {})` turns an unknown skill into an empty candidate list, which is the dead end you want.

**Step 3: add deps and check chosen ones.** Keep appending after the first conflict, so the reported list is the full list at that moment, but remember only the first conflicting dependency:

```python
            new = {k: list(x) for k, x in reqs.items()}
            conflict = None
            for dep, rng in sorted(registry[p][v].items()):
                new.setdefault(dep, []).append((p + "@" + v, rng))
                if conflict is None and dep in chosen and not satisfies(rng, chosen[dep]):
                    conflict = dep
```

**Step 4: install order.** Count each chosen skill's dependencies, start with the ones that have none, and always pop the alphabetically smallest ready skill. In Example 1 `llm-core` is the only skill with no deps, so it goes first. Then both `http-tools` and `pdf-reader` become ready, and the heap picks `http-tools`, which unblocks `auth-oauth`, and so on: `['llm-core', 'http-tools', 'auth-oauth', 'crm-connector', 'pdf-reader']`. A plain FIFO queue gives a different, still valid, order, and fails.

## 8. Full solution

```python
import heapq  # a min-heap picks the alphabetically first ready skill for the install order


def parse(v):  # "1.10.0" -> (1, 10, 0), so versions compare numerically
    return tuple(int(x) for x in v.split("."))  # integer tuples, never strings


def term_ok(term, v):  # does parsed version v satisfy one range term?
    if term == "*":  # wildcard
        return True  # any version is fine
    if term[0] == "^":  # caret: compatible changes only
        lo = parse(term[1:])  # the lower bound is the version written
        if lo[0] > 0:  # major is the leftmost non-zero part
            hi = (lo[0] + 1, 0, 0)  # allow up to the next major
        elif lo[1] > 0:  # 0.x: the minor is the leftmost non-zero part
            hi = (0, lo[1] + 1, 0)  # allow up to the next minor
        else:  # 0.0.x: only this exact patch is compatible
            hi = (0, 0, lo[2] + 1)  # allow just this one version
        return lo <= v < hi  # half-open range
    if term[0] == "~":  # tilde: patch changes only
        lo = parse(term[1:])  # the lower bound is the version written
        return lo <= v < (lo[0], lo[1] + 1, 0)  # up to the next minor, whatever the major
    for op in (">=", "<=", ">", "<", "="):  # two-character operators first so ">=" isn't read as ">"
        if term.startswith(op):  # this term uses this comparison
            w = parse(term[len(op):])  # the version after the operator
            return {">=": v >= w, "<=": v <= w, ">": v > w, "<": v < w, "=": v == w}[op]  # apply it
    return v == parse(term)  # a bare version means exactly that version


def satisfies(rng, version):  # a range is space-separated terms that must all hold
    v = parse(version)  # parse once for every term
    return all(term_ok(t, v) for t in rng.split())  # every term must allow it


def resolve(registry, requirements):  # pick one version per skill, or explain the first failure
    first_dead_end = []  # holds only the first dead end the search hits

    def dead_end(pkg, reqs):  # record a failure point for the explanation
        if not first_dead_end:  # later dead ends are ignored
            # the skill and its constraints at that moment, sorted by (by, range)
            first_dead_end.append({"package": pkg, "requirements": [{"by": b, "range": r} for b, r in sorted(reqs)]})

    def solve(chosen, reqs):  # depth-first search; returns the chosen map or None
        undecided = sorted(p for p in reqs if p not in chosen)  # skills that are needed but not yet picked
        if not undecided:  # everything needed has a version
            return chosen  # this branch is a full solution
        p = undecided[0]  # always decide the alphabetically first one next
        versions = sorted(registry.get(p, {}), key=parse, reverse=True)  # newest first; unknown skill means none
        candidates = [v for v in versions if all(satisfies(r, v) for _, r in reqs[p])]  # versions every constraint allows
        if not candidates:  # nothing fits
            dead_end(p, reqs[p])  # a dead end at p itself
            return None  # fail this branch
        for v in candidates:  # try each allowed version, highest first
            new = {k: list(x) for k, x in reqs.items()}  # a copy, so failure leaves the caller's reqs untouched
            conflict = None  # the first already-chosen dependency this version contradicts
            for dep, rng in sorted(registry[p][v].items()):  # v's dependencies in name order
                new.setdefault(dep, []).append((p + "@" + v, rng))  # record who asks for what
                if conflict is None and dep in chosen and not satisfies(rng, chosen[dep]):  # breaks an earlier decision
                    conflict = dep  # remember only the first such dependency
            if conflict is not None:  # this candidate can't work with what's already chosen
                dead_end(conflict, new[conflict])  # report it with the new range included
                continue  # try the next candidate
            out = solve(dict(chosen, **{p: v}), new)  # choose p = v on a new map and go deeper
            if out is not None:  # the deeper search found a full solution
                return out  # pass it straight up
        return None  # every candidate failed, so this branch fails

    root = {p: [("root", r)] for p, r in requirements.items()}  # the manifest's constraints, tagged root
    chosen = solve({}, root)  # start with nothing chosen
    if chosen is None:  # no solution exists along this search
        return {"ok": False, "conflict": first_dead_end[0]}  # explain the first dead end

    deps = {p: sorted(registry[p][v]) for p, v in chosen.items()}  # each chosen skill's dependency names
    waiting = {p: len(d) for p, d in deps.items()}  # dependencies not yet installed, per skill
    users = {p: [] for p in chosen}  # reverse edges: who depends on each skill
    for p, d in deps.items():  # build the reverse edges
        for q in d:  # p depends on q
            users[q].append(p)  # so installing q brings p closer to ready
    heap = [p for p, n in waiting.items() if n == 0]  # skills with no dependencies are ready now
    heapq.heapify(heap)  # ready skills come out in name order
    order = []  # the install order being built
    while heap:  # Kahn's algorithm
        p = heapq.heappop(heap)  # the alphabetically first ready skill
        order.append(p)  # install it
        for u in users[p]:  # every skill that was waiting on it
            waiting[u] -= 1  # one fewer dependency to wait for
            if waiting[u] == 0:  # all its dependencies are installed
                heapq.heappush(heap, u)  # it's ready
    return {"ok": True, "versions": {p: chosen[p] for p in sorted(chosen)}, "install_order": order}  # the lockfile
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | crm-connector 1.2.0, auth-oauth 0.4.0, http-tools 3.0.0, llm-core 2.0.0, pdf-reader 1.1.0 | newest versions when nothing conflicts; heap install order |
| Example 2 | crm-connector 1.0.0, http-tools 2.1.0, llm-core 1.10.0, pdf-reader 1.0.0 | backtracking to the first decision; `~`; numeric order |
| Example 3 | conflict on `llm-core` with three requirements | a dead end against an already-chosen version |
| empty manifest | `ok`, no versions, empty order | the search returns at once |
| caret on 0.x | auth-oauth 0.3.4, not 0.4.0 | `^0.3.0` means `<0.4.0` |
| caret on 0.0.x | slack-notify 0.0.3, not 0.0.4 | `^0.0.3` allows only 0.0.3 |
| tilde pins the minor | http-tools 2.1.0, not 2.3.1 | `~2.1.0` means `<2.2.0` |
| numeric version order | llm-core 1.10.0 | tuple comparison, not strings |
| comparators | llm-core 1.9.2, http-tools 2.1.0, pdf-reader 1.0.0 | `>`, `<`, `=`, `<=` and multi-term ranges |
| unknown skill | conflict on `jira-sync`, `[root ^1.0.0]` | a skill not in the registry has no candidates |
| dependency missing from marketplace | conflict on `webhooks`, `[slack-notify@0.1.0 ^1.0.0]` | the same, for a dependency |
| conflict with an already chosen version | conflict on `llm-core`, `[pdf-reader@1.1.0 ^2.0.0, root =1.9.2]` | sorted `(by, range)` and the new range included |
| root range unsatisfiable | conflict on `vector-search`, `[root ^4.0.0]` | a root range with no matching version |
| marketplace A, marketplace B, marketplace B tight | 9, 7 and 9 skills chosen | random registries with every range kind; B needs backtracking |

## 10. Complexity

The semver checks are constant time per term. The search, in the worst case, is exponential: with `S` skills and up to `V` versions each it can try up to `V^S` combinations, which is why real resolvers are clever about it. Here, with 20 skills and 8 versions and mostly compatible ranges, backtracking stays shallow. Each search node copies `reqs`, O(S · d) for d constraints per skill. The install order is O(S log S + E) with the heap.

In production, resolution is the slow, rare step, so you write the result to a lockfile and install from it until the manifest changes. Installs are then reproducible and don't depend on what was published since.

## 11. If you got Wrong Answer

- **"caret on 0.x" picks auth-oauth 0.4.0, and "caret on 0.0.x" picks slack-notify 0.0.4.** You treated every caret as `<next major`. Use the leftmost non-zero part.
- **"tilde pins the minor" picks http-tools 2.3.1.** You treated `~` like `^`. Example 2 and "marketplace A" fail too.
- **"numeric version order" picks llm-core 1.9.2.** You sorted versions as strings. Use `key=parse`. Example 2 and both caret cases fail too.
- **Example 2 comes back `ok: False` with a conflict on `llm-core` listing four requirements.** You only tried the first candidate. Loop over all of them so the search can back up to `crm-connector 1.0.0`. "marketplace B" fails too.
- **Example 3 comes back `ok: True` with llm-core 2.0.0 and vector-search 3.2.0.** You never check new ranges against already chosen versions, so the lockfile violates `vector-search`'s `<2.0.0`.
- **The conflict is right but its list is missing the range that caused it.** Report `new[dep]`, the list after appending, not the old `reqs[dep]`. Example 3 and "conflict with an already chosen version" catch this.
- **`install_order` is valid but differs.** You used a FIFO queue. Use a min-heap so the alphabetically first ready skill goes next.

## 12. Follow-ups an interviewer might ask

- *How do real resolvers avoid exponential search?* PubGrub (used by Cargo, Poetry, uv and Dart's pub) learns from each conflict: when it hits a dead end it derives the cause ("crm-connector >=1.2 needs llm-core >=2, vector-search needs llm-core <2") and skips every branch with the same cause. It also produces readable explanations like that one.
- *Why fix the search order so precisely?* Different orders find different valid answers. A fixed order means the same manifest gives the same lockfile on every machine, and the same failure explanation in every bug report.
- *What about permissions?* A skill's transitive dependencies may request tool scopes the installing team doesn't have. Check them at resolve time against a policy (problem 160, policy-engine).
- *How does this relate to running tools?* Once versions are fixed, the dependency graph is also the order to start things in, which is the DAG scheduling of problem 103 (parallel-tool-dag). Problem 121 (tool-registry-versioning) resolves a single tool name to a version.
