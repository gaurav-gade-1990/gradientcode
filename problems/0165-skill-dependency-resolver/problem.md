Teams on your agent platform publish reusable skills (connectors, tools, prompt packs) to an internal marketplace, and each skill pins the skills it builds on with semver ranges. When someone installs a set of skills into an AI coworker, the platform must pick one version of every skill involved, or explain exactly why it can't. Write the resolver.

`resolve(registry, requirements)`:
- `registry` is `{skill: {version: {dep_skill: range}}}`. Versions are `"MAJOR.MINOR.PATCH"` with non-negative integers.
- `requirements` is the coworker's manifest, `{skill: range}`.

**Ranges.** A range is one or more terms separated by single spaces, and a version must satisfy **every** term. Compare versions numerically, as `(major, minor, patch)`.

| term | allows |
|---|---|
| `*` | any version |
| `1.2.3` or `=1.2.3` | exactly that version |
| `>=v`, `>v`, `<=v`, `<v` | the comparison |
| `~1.2.3` | `>=1.2.3 <1.3.0` |
| `^1.2.3` | `>=1.2.3 <2.0.0` |
| `^0.2.3` | `>=0.2.3 <0.3.0` |
| `^0.0.3` | `>=0.0.3 <0.0.4` |

**Search.** Find the solution with exactly this backtracking search. Here `reqs` maps each skill to the list of `(by, range)` constraints on it, where `by` is `"root"` for the manifest or `"skill@version"` for a chosen version's dependency.

1. Start with nothing chosen and `reqs = {skill: [("root", range)]}` for the manifest.
2. If every skill in `reqs` is chosen, that is the answer. Otherwise take the **alphabetically first** unchosen skill `p`.
3. Its candidates are its registry versions (none if `p` isn't in the registry) that satisfy every constraint in `reqs[p]`, tried **highest first**. If there are none, this is a **dead end** at `p`: fail this branch.
4. For a candidate `v`, add `(p@v, range)` to `reqs[dep]` for each of `v`'s dependencies, in sorted dependency-name order. If any of those dependencies is **already chosen** at a version that doesn't satisfy the new range, the first such one (in that order) is a dead end at that dependency: skip `v`.
5. Otherwise choose `p = v` and recurse from step 2. If that fails, undo everything from this candidate and try the next one. If all candidates fail, this branch fails.

The registry's dependency graph never has cycles.

**Return**

- Success: `{"ok": True, "versions": {skill: version}, "install_order": [skill, ...]}`. `versions` covers every chosen skill. `install_order` lists them so each skill comes after all of its dependencies; when several are ready, take the alphabetically first.
- Failure: `{"ok": False, "conflict": {"package": skill, "requirements": [{"by", "range"}, ...]}}` describing the **first** dead end the search hit. `requirements` is that skill's constraint list at the dead end (including the new one in step 4), sorted by `(by, range)`.

**Constraints**

- At most 20 skills with at most 8 versions each.
- Ranges are well formed.
