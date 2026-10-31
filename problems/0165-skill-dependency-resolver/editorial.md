## Approach

Two pieces: a correct semver matcher, and a deterministic depth-first search with backtracking.

**Semver.** Parse versions into integer tuples once. Caret means "compatible with": it may change everything to the right of the leftmost non-zero component.

```python
lo = parse(term[1:])
hi = (lo[0] + 1, 0, 0) if lo[0] else (0, lo[1] + 1, 0) if lo[1] else (0, 0, lo[2] + 1)
```

**Search.** The state is `(chosen, reqs)`. Pick the alphabetically first undecided skill, filter its versions against every constraint collected so far, and try them highest first. Each choice adds its dependencies' constraints, and immediately fails if one of them contradicts a version you already picked. Passing copies of `chosen` and `reqs` down the recursion makes undo free.

```python
for v in candidates:                       # highest first
    new = add_deps(reqs, p, v)
    if contradicts_chosen(new, chosen):    # dead end at that dep
        continue
    if (out := solve({**chosen, p: v}, new)):
        return out
return None
```

Why so prescriptive? Different search orders find different valid solutions, and the explanation of a failure depends on which dead end you hit first. Fixing the order makes the answer reproducible: the same manifest gives the same lockfile on every machine.

**Install order** is Kahn's topological sort with a min-heap, so ties are broken by name.

## Common mistakes

- **`^0.x` treated like `^1.x`.** For 0.x packages a minor bump is breaking by convention. `^0.3.0` must not pull in 0.4.0, which here requires an incompatible `http-tools` 3.x.
- **Greedy, no backtracking.** Taking the newest `crm-connector` locks `llm-core` to 2.x, and the install fails even though `crm-connector` 1.0.0 works.
- **Sorting versions as strings.** `"1.10.0" < "1.9.2"`, so the resolver installs an older release and calls it the latest.
- **`~` treated like `^`.** A connector that pinned `~2.1.0` because 2.3 changed behavior gets 2.3 anyway.
- **Not checking new deps against already chosen versions.** The resolver returns a lockfile that violates a constraint, and the failure shows up at runtime in a customer's agent.

## Production notes

- npm and Cargo use semver ranges with these caret and tilde rules. pip and Poetry use PEP 440 specifiers instead. Modern resolvers (Cargo's, Poetry's and uv's PubGrub, Dart's pub) add conflict-driven learning: when a dead end is found they derive *why* and skip every branch with the same cause, which keeps worst-case searches tractable and produces explanations like "because crm-connector >=1.2 depends on llm-core >=2 and vector-search depends on llm-core <2, …".
- Write the result to a lockfile and resolve only when the manifest changes. Installs from a lockfile are reproducible and don't depend on what was published since.
- For an agent marketplace, also check permissions at resolve time: a skill's transitive dependencies may request tool scopes (see `policy-engine`) the installing team doesn't have.
- Pairs with `tool-registry-versioning` (resolving a single tool name) and `parallel-tool-dag` (running work in dependency order).
