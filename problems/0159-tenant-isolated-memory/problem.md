Your platform hosts AI coworkers for many companies. Each coworker remembers facts between conversations ("Dana prefers weekly summaries", "the Q3 refund policy changed"). Memories can be private to one user's agent, shared with a team, or shared across the whole company, and an agent can write a memory derived from others. Two rules are non-negotiable: a read never crosses a tenant, and a GDPR erasure request removes the user's memories and everything derived from them.

Implement `MemoryStore`. A **ctx** is `{"tenant", "user", "agent", "team"}`, where `team` may be `None`. User ids and team names are only unique inside a tenant: `acme/u_1` and `globex/u_1` are different people, and both companies can have a `support` team.

**Visibility.** A memory `m` is visible to `ctx` only if `m`'s tenant equals `ctx["tenant"]`, and then:

| `m.scope` | also requires |
|---|---|
| `"private"` | the same `user` **and** the same `agent` as the writer |
| `"team"` | `ctx["team"]` is not `None` and equals the team the writer had when writing |
| `"org"` | nothing more |

**`write(ctx, key, value, scope="private", sources=())`** stores a memory and returns its id.
- Raise `ValueError` if `scope` isn't one of the three, or if it is `"team"` and `ctx["team"]` is `None`.
- Raise `PermissionError` if any id in `sources` doesn't exist or isn't visible to `ctx`. Don't write anything in either case.
- The memory's identity is `(tenant, user, agent, key)` of the writer. Writing an existing identity again keeps its id and replaces its value, scope, team and sources. Otherwise assign the next id `"mem_1"`, `"mem_2"`, … (one counter for the whole store, never reused, not advanced by a failed write).

**`read(ctx, key)`** returns the value of the best visible memory with that `key`, or `None`. Best means the narrowest scope (private, then team, then org), then the most recently written (a successful `write` counts as the newest, including an overwrite).

**`visible(ctx)`** returns the ids of every visible memory, ordered by their number.

**`delete_user(tenant, user)`** erases every memory written by that user in that tenant (any agent, any scope), and then, repeatedly until nothing changes, every memory whose `sources` include an erased memory. Return the erased ids ordered by their number. Erased memories are gone for every later call.

The judge replays a list of operations and records each return value, or `{"error": "PermissionError"}` / `{"error": "ValueError"}` when you raise one.

**Constraints**

- At most 300 operations.
- Values are JSON-like data. Return them as stored.
