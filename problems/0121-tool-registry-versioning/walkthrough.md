## 1. What the problem is really asking

A shared tool registry lets agents pin tools the way package managers pin dependencies: `crm_lookup@^1.2` means "any compatible 1.x from 1.2.0 up". Publishers keep shipping, deprecating and pulling versions, and the resolver decides which version each agent actually gets.

Under the story, this is **interval filtering plus a ranked `max`**:

1. Validate and parse the spec.
2. Turn the range into a half-open interval `[lower, upper)` of `(major, minor, patch)` tuples.
3. Keep that tool's versions inside the interval, then pick the highest **active** one, else the highest **deprecated** one with a warning, else report `removed` or `not_found`.

All of the difficulty is in step 2 (the caret rule for `0.x` versions) and in comparing versions as numbers. The judge replays a list of `register` and `resolve` operations against one registry and compares every `resolve` result dict, in order.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `register(name, version, status)` | adds or replaces one version's status | store under the integer tuple, keep the original string |
| `version` | always `"MAJOR.MINOR.PATCH"` | `tuple(int(p) for p in version.split("."))` |
| `status` | `"active"`, `"deprecated"` or `"removed"` | decides the preference order |
| `resolve(spec)` | `name` or `name@range` | returns one of six result dicts |
| range | optional `^` or `~`, then 1–3 numeric parts | becomes `[lower, upper)` |

Three details are easy to miss:

- **Order of the error checks.** `invalid_spec` comes before `unknown_tool`. In "malformed specs", `nobody@x` is `invalid_spec`, while `nobody@1` is `unknown_tool`.
- **Removed versions still count as registered.** A tool whose only versions are removed is not `unknown_tool`; its in-range matches give `removed`.
- **Names are case-sensitive.** `Ticket_create` is a different tool from `ticket_create`, so it's `unknown_tool`.

## 3. Trace Example 1 by hand

The registry holds five versions of `crm_lookup`:

| version | tuple | status |
|---|---|---|
| 1.2.0 | (1, 2, 0) | active |
| 1.4.2 | (1, 4, 2) | active |
| 1.9.0 | (1, 9, 0) | active |
| 1.10.0 | (1, 10, 0) | deprecated |
| 2.0.0 | (2, 0, 0) | active |

**`crm_lookup@^1.2`.** Parts `[1, 2]`. Lower is `(1, 2, 0)`. The leftmost non-zero part is the major (index 0), so upper is the major bumped: `(2, 0, 0)`. In range: 1.2.0, 1.4.2, 1.9.0 (active) and 1.10.0 (deprecated). The highest active is 1.9.0, so the result is `{"ok": True, "version": "1.9.0", "warning": None}`. The deprecated 1.10.0 is higher, but active always wins.

**`crm_lookup@~1.4`.** Tilde with a minor given bumps the minor: `[1.4.0, 1.5.0)`. Only 1.4.2 is in range.

**`crm_lookup`** with no range matches everything. The highest active is 2.0.0.

**Example 2** is the `0.x` case. `^0.3` has parts `[0, 3]`. The leftmost non-zero part is the minor, so the interval is `[0.3.0, 0.4.0)`, and `0.4.0` is out. Then the statuses change between resolves:

| after | in range | result |
|---|---|---|
| start | 0.3.1 active, 0.3.4 deprecated | `0.3.1`, no warning |
| 0.3.1 → deprecated | both deprecated | `0.3.4`, warning `deprecated` |
| both → removed | both removed | error `removed` |

## 4. Key idea: compare tuples, never strings

As strings, `"1.10.0" < "1.9.0"` is `True`, because `"1"` sorts before `"9"`. So `max(["1.9.0", "1.10.0", "1.2.0"])` is `"1.9.0"`. In "numeric not string order", `sql_query@^1` must give `1.10.0`; a string `max` gives `1.9.0`, which would hand every agent an old release.

So store each version under its integer tuple, compare tuples, and keep the registered string next to it for the return value. `(1, 10, 0) > (1, 9, 0)` because Python compares tuples element by element.

## 5. Key idea: every range is a bump of one part

Every row of the range table is "lower = the parts padded with zeros; upper = bump part `i`", for some `i`. "Bump" adds 1 to part `i` and zeroes everything after it.

| range | parts | bumped index | interval |
|---|---|---|---|
| `1.2.3` | `[1, 2, 3]` | 2 (patch) | `[1.2.3, 1.2.4)`, i.e. exactly 1.2.3 |
| `1.2` | `[1, 2]` | 1 (last given) | `[1.2.0, 1.3.0)` |
| `^1.2` | `[1, 2]` | 0 (leftmost non-zero) | `[1.2.0, 2.0.0)` |
| `^0.3` | `[0, 3]` | 1 (leftmost non-zero) | `[0.3.0, 0.4.0)` |
| `^0.0.3` | `[0, 0, 3]` | 2 (leftmost non-zero) | `[0.0.3, 0.0.4)` |
| `^0.0` | `[0, 0]` | 1 (all zero → last given) | `[0.0.0, 0.1.0)` |
| `~1.2.3` | `[1, 2, 3]` | 1 (minor given) | `[1.2.3, 1.3.0)` |
| `~1` | `[1]` | 0 (no minor) | `[1.0.0, 2.0.0)` |

The caret rule follows semver's convention that before 1.0, the minor is the breaking-change digit. In "caret on zero major", `^0.3` gives `0.3.7`, `^0.0.3` gives only `0.0.3` (not `0.0.4`), `^0.0` gives `0.0.4`, and `^0` gives `0.4.2`.

## 6. Plan before you code

```
register: tools[name][tuple(version)] = (version string, status)

resolve(spec):
    name, "@", range = spec.partition("@")
    name doesn't fullmatch NAME           -> invalid_spec
    has "@" and range doesn't fullmatch RANGE -> invalid_spec
    compute [lower, upper) (or no bounds)
    name never registered                 -> unknown_tool
    bucket in-range versions by status
    highest active / highest deprecated + warning / removed / not_found
```

The validation is two anchored regexes. `str.partition("@")` splits at the **first** `@`, so `kb_search@@1` leaves `@1` as the range, which the range regex rejects.

## 7. Build it one piece at a time

**Step 1: the grammar.** Each part is `0` or a number with no leading zero, and there are one to three parts. `fullmatch` anchors both ends, so `1.0.0.0`, `01.0`, ` 1` and `>=1.0` all fail.

```python
NAME = re.compile(r"[A-Za-z0-9_-]+")
RANGE = re.compile(r"([\^~]?)((?:0|[1-9][0-9]*)(?:\.(?:0|[1-9][0-9]*)){0,2})")
```

With `RANGE.match` instead of `fullmatch`, `1.0.0.0` would match its first three parts and be accepted.

**Step 2: bump and interval.** One helper pads to three parts, bumps one index, and zeroes the rest.

```python
def _bump(parts, i):
    out = list(parts) + [0] * (3 - len(parts))
    out[i] += 1
    for j in range(i + 1, 3):
        out[j] = 0
    return tuple(out)
```

`_interval` only has to choose `i`:

```python
    if op == "^":
        nonzero = [i for i, p in enumerate(parts) if p != 0]
        return lower, _bump(parts, nonzero[0] if nonzero else len(parts) - 1)
    if op == "~":
        return lower, _bump(parts, 1 if len(parts) >= 2 else 0)
    return lower, _bump(parts, len(parts) - 1)
```

The exact-match case needs no special code. Bumping the patch of `1.2.3` gives `[1.2.3, 1.2.4)`, and with integer patches only `1.2.3` fits.

**Step 3: register.** A dict per tool, keyed by the tuple, so re-registering the same version replaces its status.

```python
    def register(self, name, version, status="active"):
        key = tuple(int(p) for p in version.split("."))
        self.tools.setdefault(name, {})[key] = (version, status)
```

**Step 4: filter and rank.** Bucket the in-range versions by status. `max` over `(tuple, string)` pairs compares the tuple first, and the string rides along.

```python
        matches = {"active": [], "deprecated": [], "removed": []}
        for key, (text, status) in self.tools[name].items():
            if lower is None or lower <= key < upper:
                matches[status].append((key, text))
```

## 8. Full solution

```python
import re  # one anchored regex each for the name and the range

NAME = re.compile(r"[A-Za-z0-9_-]+")  # tool names: letters, digits, _ and -
# optional ^ or ~, then 1 to 3 dot-separated parts, each 0 or a number without a leading zero
RANGE = re.compile(r"([\^~]?)((?:0|[1-9][0-9]*)(?:\.(?:0|[1-9][0-9]*)){0,2})")


def _bump(parts, i):  # add 1 to part i and zero every later part -> the exclusive upper bound
    out = list(parts) + [0] * (3 - len(parts))  # pad to MAJOR.MINOR.PATCH
    out[i] += 1  # the part that may not change inside the range
    for j in range(i + 1, 3):  # everything after it
        out[j] = 0  # resets, as in 1.9.3 -> 2.0.0
    return tuple(out)  # a comparable version tuple


def _interval(op, parts):  # every range is [lower, upper) with upper exclusive
    lower = tuple(parts + [0] * (3 - len(parts)))  # missing parts count as 0
    if op == "^":  # caret: compatible within the first non-zero part
        nonzero = [i for i, p in enumerate(parts) if p != 0]  # indices of non-zero given parts
        # 0.x treats the minor as breaking; all zeros falls back to the last given part
        return lower, _bump(parts, nonzero[0] if nonzero else len(parts) - 1)
    if op == "~":  # tilde: patch-level changes if a minor was given, else minor-level
        return lower, _bump(parts, 1 if len(parts) >= 2 else 0)  # bump the minor, or the major for ~1
    if len(parts) == 3:  # a full version with no operator
        return lower, _bump(parts, 2)  # exact: [1.2.3, 1.2.4)
    return lower, _bump(parts, len(parts) - 1)  # partial: 1.2 -> [1.2.0, 1.3.0)


class ToolRegistry:  # name -> versions -> status, plus the resolver
    def __init__(self):  # starts empty
        self.tools = {}  # name -> {version tuple: (version string, status)}

    def register(self, name, version, status="active"):  # add a version or replace its status
        key = tuple(int(p) for p in version.split("."))  # compare numerically, never as strings
        self.tools.setdefault(name, {})[key] = (version, status)  # re-registering overwrites the status

    def resolve(self, spec):  # which version should an agent asking for spec get?
        name, sep, rng = spec.partition("@")  # split at the first "@"; sep is "" when there's none
        if not NAME.fullmatch(name):  # empty name, spaces, other characters
            return {"ok": False, "error": "invalid_spec"}  # malformed beats everything
        if sep:  # a range was given
            m = RANGE.fullmatch(rng)  # anchored: rejects 1.0.0.0, 01, ^, >=1.0, a second @
            if not m:  # not in the grammar
                return {"ok": False, "error": "invalid_spec"}  # checked before unknown_tool
            lower, upper = _interval(m.group(1), [int(p) for p in m.group(2).split(".")])  # operator and parts
        else:  # a bare name
            lower, upper = None, None  # every version matches
        if name not in self.tools:  # never registered, even as removed
            return {"ok": False, "error": "unknown_tool"}  # a typo or a missing publish
        matches = {"active": [], "deprecated": [], "removed": []}  # in-range versions by status
        for key, (text, status) in self.tools[name].items():  # every known version of this tool
            if lower is None or lower <= key < upper:  # inside [lower, upper)
                matches[status].append((key, text))  # keep the tuple for max and the string for output
        if matches["active"]:  # active always wins, even over a higher deprecated version
            return {"ok": True, "version": max(matches["active"])[1], "warning": None}  # highest active
        if matches["deprecated"]:  # nothing active: fall back, but warn
            return {"ok": True, "version": max(matches["deprecated"])[1], "warning": "deprecated"}  # highest deprecated
        if matches["removed"]:  # only pulled versions match
            return {"ok": False, "error": "removed"}  # never serve them; the caller must change the pin
        return {"ok": False, "error": "not_found"}  # nothing in range at all
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | `1.9.0`, `1.4.2`, `2.0.0` | caret, tilde, bare name; active beats a higher deprecated |
| Example 2 | `0.3.1`, `0.3.4` + warning, `removed` | `^0.3` excludes 0.4.0; re-registering changes status |
| Example 3 | `not_found`, `unknown_tool`, `invalid_spec` | three different failure paths |
| numeric not string order | `1.10.0` ×3, then `1.9.0` | tuple comparison |
| caret on zero major | `0.3.7`, `0.0.3`, `0.0.4`, `0.4.2`, `not_found` ×2 | every caret sub-rule |
| active beats higher deprecated | `2.1.0`, `2.8.1` + warning ×2, then `2.8.1` | the preference order, and re-activation |
| removed versus not found | `removed` ×2, `not_found`, `4.0.0`, `not_found` | `removed` only when a pulled version is in range |
| exact and tilde | `1.2.3`, `1.2.9`, `1.2.9`, `1.3.0`, `not_found`, `1.2.9`, `1.3.0` | exact match, `~` with three parts, partial without operator |
| malformed specs | `invalid_spec` ×9, then `1.0.0`, `invalid_spec`, `unknown_tool` | the grammar, and `invalid_spec` before `unknown_tool` |
| re-register flips status | `1.1.0`, `1.0.0`, `1.0.0` + warning, `1.1.0`, `unknown_tool` | status replacement; case-sensitive names |
| many versions | 29 resolves over 144 versions | everything at once |

## 10. Complexity

`register` is O(1). `resolve` is O(V) for the `V` versions of that tool: one pass to bucket, then a `max`. With at most 200 operations that's trivial.

A real registry with thousands of versions per tool would keep each status's versions in a sorted list and use `bisect` to find the highest version below `upper`, which makes `resolve` O(log V). More important in production is that resolution happens **once per agent run** and the result is pinned in the trace, so a publish in the middle of a long run can't change which tool version the agent is talking to.

## 11. If you got Wrong Answer

- **"numeric not string order" gives `1.9.0`.** You took `max` over version strings. Compare integer tuples.
- **Example 2's first resolve gives `0.4.0`.** Your caret always bumps the major. Bump the leftmost non-zero given part.
- **Example 1 gives `1.10.0` with a warning.** You picked the highest non-removed version. Check active first, then deprecated.
- **"removed versus not found" returns a removed version with `ok: True`.** Removed versions must never be served.
- **"exact and tilde" gives `1.2.3` for `~1.2.3` and `not_found` for `~1.2.4`.** Your tilde bumps the last given part (the patch), which makes a three-part tilde an exact match. Tilde bumps the minor when one is given.
- **"malformed specs" accepts `kb_search@1.0.0.0`.** You used `match` instead of `fullmatch`.
- **`nobody@x` gives `unknown_tool`.** Validate the spec before looking up the name.

## 12. Follow-ups an interviewer might ask

- *How would you support prereleases like `2.0.0-beta.1`?* Add a fourth sort key where a release sorts after all its prereleases, and exclude prereleases from ranges unless the range itself names one, as npm does.
- *How do multiple tools with conflicting ranges get resolved?* That's dependency resolution across a graph, with backtracking or a SAT solver. See problem 165 (skill-dependency-resolver).
- *Who should see the `deprecated` warning?* The agent's owner, not the model: a log line, a header or a dashboard. Track who still resolves a deprecated version before you remove it.
- *What changes when a tool's schema changes?* A breaking `inputSchema` change is a new major. Argument validation (problem 113, tool-args-schema-validation) has to run against the schema of the version you resolved.
- *Where does this sit relative to MCP?* MCP servers advertise tools by name only, so versioning lives in the registry or gateway in front of them, which then routes `tools/call` to the right server (problem 114, mcp-jsonrpc-dispatch).
