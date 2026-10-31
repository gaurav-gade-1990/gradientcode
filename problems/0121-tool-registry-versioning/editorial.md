## Approach

Every range is a half-open interval of version tuples. Once you have `[lower, upper)`, resolution is a filter and a `max`.

```python
def _interval(op, parts):
    lower = tuple(parts + [0] * (3 - len(parts)))
    if op == "^":
        nonzero = [i for i, p in enumerate(parts) if p != 0]
        return lower, bump(parts, nonzero[0] if nonzero else len(parts) - 1)
    if op == "~":
        return lower, bump(parts, 1 if len(parts) >= 2 else 0)
    return lower, bump(parts, len(parts) - 1)   # 3 parts: exact, [1.2.3, 1.2.4)
```

`bump(parts, i)` adds one to part `i` and zeroes everything after it. The caret rule is the one that trips people up: in `0.x`, the minor is the breaking-change digit, so `^0.3` must stop before `0.4.0`, and `^0.0.3` allows only `0.0.3`.

Then filter that tool's versions by `lower <= v < upper` and pick in a fixed order of preference: the highest active one, else the highest deprecated one with a warning, else `removed` if a pulled version matched, else `not_found`. Validate the spec with one anchored regex before anything else, so `1.2.3.4` and `>=1.0` never reach the parser.

## Common mistakes

- **Comparing version strings.** `"1.10.0" < "1.9.0"` as strings, so a string `max` hands every agent last year's release. Compare integer tuples.
- **Treating `^0.x` like `^1.x`.** By semver convention `0.3 -> 0.4` may break the API. If you bump the major for `^0.3`, an agent pinned to `^0.3` silently picks up `0.4.2` and starts sending the wrong arguments.
- **Picking the highest non-removed version.** A deprecated `1.10.0` is higher than an active `1.9.0`, but the whole point of deprecating is to steer traffic off it. Prefer active and fall back to deprecated only when nothing active matches.
- **Serving removed versions.** A removed (yanked) version usually had a security or data bug. Matching it must be an error, and it must be a different error from `not_found`, so the caller knows to change their pin rather than wait for a publish.

## Production notes

- MCP servers advertise tools by name only. Platform teams add versioning in the registry or gateway in front of them and expose `name@range` in agent configs, the same way npm, Cargo and pip resolve dependencies.
- Deprecation should be visible. Return the warning to the agent owner (a log line, a header, a dashboard), not to the model, and track who still resolves deprecated versions before you remove them.
- Keep tool schemas immutable per version. If `inputSchema` changes in a breaking way, it is a new major, and validation (problem 113) runs against the schema of the resolved version.
- Resolve once per run and pin the result in the trace. Then a mid-run publish cannot change which tool a long agent run is talking to, and replay (problem 111) sees the same versions.
- For transitive ranges and conflicts across many tools, see the skill dependency resolver (problem 165).
