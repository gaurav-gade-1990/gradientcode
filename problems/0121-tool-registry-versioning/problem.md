Your platform team runs a shared tool registry. Agents pin tools with npm-style ranges like `crm_lookup@^1.2`, and publishers ship new versions, deprecate old ones and pull broken ones. Implement the resolver.

Implement `class ToolRegistry` with:

- `register(name, version, status="active")`: record that `version` (always `"MAJOR.MINOR.PATCH"`) of tool `name` exists with `status` in `"active"`, `"deprecated"`, `"removed"`. Registering the same `name` and `version` again replaces its status. Returns nothing.
- `resolve(spec)`: return the version an agent asking for `spec` should get.

**Spec grammar.** `spec` is `name` or `name@range`. `name` matches `[A-Za-z0-9_-]+`. A range is an optional operator (`^` or `~`) followed by 1 to 3 dot-separated parts, each `0` or a number with no leading zero. Anything else (an empty name, an empty range, two `@`, `1.2.3.4`, `01`, `^`, `>=1.0`) is malformed.

Versions compare numerically, part by part, as `(major, minor, patch)`. There are no prereleases. Each range is a half-open interval `[lower, upper)`, where `lower` is the given parts padded with zeros:

| range | upper bound | examples |
|---|---|---|
| no `@` | none (every version) | `search` |
| `1.2.3` (no operator, 3 parts) | exact match only | `1.2.3` matches only `1.2.3` |
| `1.2` / `1` (no operator, partial) | bump the last given part | `1.2` is `[1.2.0, 1.3.0)`, `1` is `[1.0.0, 2.0.0)` |
| `^` caret | bump the leftmost **non-zero** given part; if all given parts are 0, bump the last given part | `^1.2` is `[1.2.0, 2.0.0)`, `^0.3` is `[0.3.0, 0.4.0)`, `^0.0.3` is `[0.0.3, 0.0.4)`, `^0.0` is `[0.0.0, 0.1.0)`, `^1` is `[1.0.0, 2.0.0)` |
| `~` tilde | bump the minor if a minor was given, else the major | `~1.2.3` and `~1.2` are `[1.2.x, 1.3.0)`, `~1` is `[1.0.0, 2.0.0)` |

"Bump" means add 1 to that part and set every later part to 0.

**Resolution.** Check these in order and return the first that applies:

| condition | return |
|---|---|
| `spec` is malformed | `{"ok": False, "error": "invalid_spec"}` |
| no version of `name` was ever registered | `{"ok": False, "error": "unknown_tool"}` |
| some **active** version is in range | `{"ok": True, "version": <highest active in range>, "warning": None}` |
| some **deprecated** version is in range | `{"ok": True, "version": <highest deprecated in range>, "warning": "deprecated"}` |
| some **removed** version is in range | `{"ok": False, "error": "removed"}` |
| otherwise | `{"ok": False, "error": "not_found"}` |

An active version always wins over a higher deprecated one. Return `version` as the `"MAJOR.MINOR.PATCH"` string it was registered with.

The judge replays a list of `register` and `resolve` operations against one registry and grades the result of every `resolve`, in order.

**Constraints**

- At most 200 operations per case.
- Registered versions are always well-formed `"MAJOR.MINOR.PATCH"` with no leading zeros; each part is at most 1000.
- Tool names are case-sensitive.
