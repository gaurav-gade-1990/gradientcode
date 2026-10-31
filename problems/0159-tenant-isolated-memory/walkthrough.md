## 1. What the problem is really asking

One store holds the memories of AI coworkers for many companies. Two promises have to hold no matter what sequence of operations arrives:

- **A read never crosses a tenant.** acme's agents never see globex's memories, even though both companies have a `u_1` and a `support` team.
- **Erasure is complete.** When a user asks to be forgotten, their memories go, and so does every memory derived from them, and every memory derived from *those*.

Under the story there are three small pieces:

- **One visibility predicate**, `_visible(memory, ctx)`. Everything else (`read`, `visible`, the source check in `write`) is a filter over that one function.
- **An upsert keyed on a 4-tuple**, `(tenant, user, agent, key)`, with ids from a counter that is never reused.
- **A reachability closure** over the `sources` graph for `delete_user`: start from the user's own memories and keep adding anything that points into the set until nothing changes.

The judge replays a list of operations and records each return value, or `{"error": "PermissionError"}` / `{"error": "ValueError"}` when you raise. So the ids you hand out, the order of the lists, and whether a bad write raised are all graded.

## 2. Understand the inputs before writing anything

| piece | what it is | how you use it |
|---|---|---|
| `ctx` | `{"tenant", "user", "agent", "team"}`; `team` may be `None` | the identity of whoever is reading or writing |
| `write(ctx, key, value, scope, sources)` | store or overwrite; returns the id | validate first, then upsert |
| `read(ctx, key)` | the best visible value, or `None` | filter, then pick by `(scope rank, newest)` |
| `visible(ctx)` | every visible id, by number | filter, then sort numerically |
| `delete_user(tenant, user)` | erase and cascade; returns the erased ids | closure over `sources` |

The test file builds a small cast of contexts. You'll see them in every case, so learn them once:

| name | tenant | user | agent | team |
|---|---|---|---|---|
| `DANA` | acme | u_1 | assistant | support |
| `DANA_HR` | acme | u_1 | hr-agent | support |
| `LEE` | acme | u_2 | assistant | support |
| `SAM` | acme | u_3 | assistant | finance |
| `G_U1` | globex | u_1 | assistant | support |
| `G_U9` | globex | u_9 | assistant | `None` |

The details that are easy to miss:

- **Private means same user *and* same agent.** `DANA` and `DANA_HR` are the same person, but Dana's general assistant must not read what her HR agent stored.
- **A memory remembers the writer's team at write time.** Team visibility compares `ctx["team"]` with that stored team, never with the writer's current context.
- **A failed write changes nothing**, including the id counter. In "invalid scopes", two writes raise `ValueError` and the next good write still gets `mem_1`.
- **An erased id is never reused.** After erasure the identity is gone too, so writing the same key again gets a fresh id.

## 3. Trace the examples by hand

**Example 2: precedence.** Three writes to the key `tone`:

| op | writer | scope | id |
|---|---|---|---|
| 1 | DANA | private | `mem_1` |
| 2 | LEE | team (support) | `mem_2` |
| 3 | SAM | org | `mem_3` |

Now each person reads `tone`:

| reader | visible candidates | winner | returned |
|---|---|---|---|
| DANA | mem_1 (private, rank 0), mem_2 (team, rank 1), mem_3 (org, rank 2) | mem_1 | `"concise"` |
| LEE | mem_2, mem_3 (mem_1 is Dana's private) | mem_2 | `"friendly"` |
| SAM | mem_3 only (finance isn't support) | mem_3 | `"formal"` |

Then Dana writes `tone = "bullet points"` again. Same `(acme, u_1, assistant, tone)`, so the id stays `mem_1`, the write returns `"mem_1"`, and her next read returns `"bullet points"`. `visible(LEE)` is `['mem_2', 'mem_3']`.

The full judge output is:

```
['mem_1', 'mem_2', 'mem_3', 'concise', 'friendly', 'formal', 'mem_1', 'bullet points', ['mem_2', 'mem_3']]
```

**Example 1: tenants with the same team name.** Lee writes a `support` team memory in acme (`mem_2`), and globex's u_1 writes a `support` team memory with the same key (`mem_3`). Dana reads `refund_policy` and gets `"30 days, receipts required"`, and G_U1 gets `"globex: no refunds after 14 days"`. `visible(DANA)` is `['mem_1', 'mem_2']`. A team check without the tenant check would let Dana see `mem_3` too, and because it is newer it would win her read.

**Example 3: a two-step cascade.** Dana writes `allergy` (`mem_1`, private), then `lunch_order_notes` derived from it (`mem_2`, org). Sam writes `offsite_menu` derived from `mem_2` (`mem_3`) and an unrelated `budget` (`mem_4`). `delete_user("acme", "u_1")`:

| pass | added | why |
|---|---|---|
| seed | mem_1, mem_2 | written by acme/u_1 |
| 1 | mem_3 | its sources contain mem_2 |
| 2 | nothing | stop |

It returns `['mem_1', 'mem_2', 'mem_3']`, and `visible(SAM)` is `['mem_4']`. `mem_3` was written by Sam, not Dana, but it carries her data, so it goes.

## 4. Key idea: check the tenant first, for every scope

It is tempting to write the scope rules as three independent tests: private compares user and agent, team compares the team, org lets anyone through. Team names and user ids are only unique *inside* a tenant, though. Without a tenant test on the team branch, "team and user ids collide across tenants" breaks: Lee reads `escalation` and gets globex's `"email globex-ops"` instead of acme's `"page #acme-oncall"`, and `visible(G_U1)` lists acme's `mem_1`.

Putting the tenant comparison at the top of the predicate, before any scope branch, makes the leak impossible by construction. Because `write` validates `sources` with the same predicate, no memory can be derived from another tenant's memory, so the `sources` graph never crosses a tenant either, and neither can an erasure cascade.

## 5. Key idea: loop until nothing changes

Why not one pass over the memories in id order? Sources must exist before you cite them, so it looks as if a memory's sources always have smaller ids. **Overwrites break that.** An overwrite keeps the old id but takes new sources, so a low id can point at a high one.

A scratch run shows it. Sam writes `x` (`mem_1`, org), Lee writes a team note (`mem_2`), Dana writes a digest from `mem_2` (`mem_3`), then Sam overwrites `x` with `sources=["mem_3"]`. Now `mem_1 → mem_3 → mem_2`. Erasing acme/u_2:

| approach | erased | `visible(SAM)` afterwards |
|---|---|---|
| repeat passes until no change (the solution) | `['mem_1', 'mem_2', 'mem_3']` | `[]` |
| a single pass in id order | `['mem_2', 'mem_3']` | `['mem_1']` |

The single pass looks at `mem_1` before `mem_3` is in the set, and never comes back. The `while changed` loop does come back. Its cost is at most one extra pass per level of the chain, which is cheap insurance for a legal guarantee.

## 6. Plan before you code

```
state: mems (id -> record), index (identity -> id), next_id, seq

_visible(m, ctx):
    tenant differs -> False
    private -> same user and same agent
    team    -> ctx team not None and equals m's team
    org     -> True

write:
    validate scope, team presence, every source (exists and visible)  # nothing written yet
    id = index[identity] or a fresh mem_N
    seq += 1; store the full record

read:    min over visible same-key memories by (scope rank, -seq)
visible: filter, sort by the number in the id
delete_user:
    doomed = memories with this tenant and user
    repeat: add any memory with a source in doomed, until a pass adds nothing
    remove records and index entries; return sorted ids
```

## 7. Build it one piece at a time

**Step 1: the predicate.** Everything else depends on it, so write and test it first.

```python
def _visible(self, m, ctx):
    if m["tenant"] != ctx["tenant"]:
        return False
    if m["scope"] == "private":
        return m["user"] == ctx["user"] and m["agent"] == ctx["agent"]
    if m["scope"] == "team":
        return ctx.get("team") is not None and m["team"] == ctx.get("team")
    return True
```

The `is not None` test matters even though a team memory always has a team. It keeps the rule correct if a no-team write ever slipped through, and it states the intent: a reader with no team sees no team memories.

**Step 2: validate, then upsert.** All three checks run before any state changes, so a rejected write leaves the counter and the records alone.

```python
ident = (ctx["tenant"], ctx["user"], ctx["agent"], key)
mid = self.index.get(ident)
if mid is None:
    mid = "mem_%d" % self.next_id
    self.next_id += 1
    self.index[ident] = mid
self.seq += 1
```

The source check uses `_visible` too. In "sources must be visible", Dana cites globex's `mem_1`, a missing `mem_99`, and Lee's private `mem_2`, and all three raise `PermissionError`. Without it, an agent could copy another tenant's secret into its own org-scoped memory by "deriving" from it.

**Step 3: read by precedence.** Sort key `(rank, -seq)`: the lowest rank wins, and within a rank the highest `seq`, which is why it is negated for `min`. In "most recent write wins a scope tie", Lee writes `v1` (org), Sam writes `v2` (org), and Dana reads `v2`. Then Lee overwrites with `v3`. The overwrite takes a new `seq`, so Dana now reads `v3`, even though the id is still `mem_1`.

**Step 4: erasure.** Seed with the tenant and the user, run the fixed-point loop from section 5, then delete both the record and its `index` entry. Forgetting the `index` entry would make a later write reuse an erased id. In "overwrite changes scope and sources", after the cascade erases `mem_1` and `mem_2`, Dana's new `plan` write correctly returns `mem_3`.

## 8. Full solution

Every line carries a comment saying what it does and why.

```python
# Scope rank for read precedence: the narrower the scope, the lower the rank, the higher the priority.
SCOPES = {"private": 0, "team": 1, "org": 2}


# One store for every tenant on the platform; isolation is enforced by code, not by separate stores.
class MemoryStore:
    # Start empty.
    def __init__(self):
        self.mems = {}      # id -> record; the live memories
        self.index = {}     # (tenant, user, agent, key) -> id; finds the memory an overwrite replaces
        self.next_id = 1    # one id counter for the whole store, never reused
        self.seq = 0        # write counter, so "most recently written" is a number to compare

    # The single visibility rule, shared by read, visible and the source check in write.
    def _visible(self, m, ctx):
        # Tenant first, for every scope: two companies may both have u_1 and a "support" team.
        if m["tenant"] != ctx["tenant"]:
            return False  # never cross a tenant
        # Private belongs to one user's one agent, not to the user's other agents.
        if m["scope"] == "private":
            return m["user"] == ctx["user"] and m["agent"] == ctx["agent"]  # both must match
        # Team memories need a reader on the writer's team; a reader with no team sees none.
        if m["scope"] == "team":
            return ctx.get("team") is not None and m["team"] == ctx.get("team")  # same team, same tenant
        # Org scope: anyone in the tenant (already checked above).
        return True

    # Store or overwrite a memory; validate everything before touching any state.
    def write(self, ctx, key, value, scope="private", sources=()):
        # Reject a scope we don't know.
        if scope not in SCOPES:
            raise ValueError("unknown scope %r" % scope)  # raised before any state changes
        # A team memory written by someone with no team would be visible to no one.
        if scope == "team" and ctx.get("team") is None:
            raise ValueError("team scope needs a team")  # same: nothing written yet
        # Each source must exist and be visible to the writer, or derivation becomes a leak.
        for s in sources:
            # Unknown id, or a memory this writer may not read.
            if s not in self.mems or not self._visible(self.mems[s], ctx):
                raise PermissionError("source %s is not visible" % s)  # no laundering through "derived from"
        # Identity includes tenant and agent: user ids repeat across tenants, and agents don't share.
        ident = (ctx["tenant"], ctx["user"], ctx["agent"], key)
        # An existing memory with this identity keeps its id.
        mid = self.index.get(ident)
        # A new identity gets the next id; only now, after every check passed, does the counter move.
        if mid is None:
            mid = "mem_%d" % self.next_id  # ids are mem_1, mem_2, ...
            self.next_id += 1  # advance the counter for the next new memory
            self.index[ident] = mid  # remember the id for later overwrites
        # Every successful write, overwrite included, becomes the newest.
        self.seq += 1
        # Replace the whole record: value, scope, the writer's current team and sources all change.
        self.mems[mid] = {"id": mid, "tenant": ctx["tenant"], "user": ctx["user"], "agent": ctx["agent"],
                          "team": ctx.get("team"), "key": key, "value": value, "scope": scope,
                          "sources": list(sources), "seq": self.seq}
        # The caller gets the id, new or reused.
        return mid

    # The best visible value for this key, or None.
    def read(self, ctx, key):
        # Candidates: same key, and visible under the shared rule.
        hits = [m for m in self.mems.values() if m["key"] == key and self._visible(m, ctx)]
        # Nothing this reader may see.
        if not hits:
            return None  # no visible memory has this key
        # Narrowest scope first, then the highest write sequence (hence the minus sign).
        return min(hits, key=lambda m: (SCOPES[m["scope"]], -m["seq"]))["value"]

    # Every id this ctx may see, in id-number order.
    def visible(self, ctx):
        # Filter with the same rule read uses.
        ids = [mid for mid, m in self.mems.items() if self._visible(m, ctx)]
        # Sort by the number, so mem_10 comes after mem_9 rather than after mem_1.
        return sorted(ids, key=lambda s: int(s.split("_")[1]))

    # GDPR erasure: the user's memories and everything derived from them, at any depth.
    def delete_user(self, tenant, user):
        # Seed: everything this user wrote in this tenant, any agent, any scope.
        doomed = {mid for mid, m in self.mems.items() if m["tenant"] == tenant and m["user"] == user}
        # Repeat passes until one adds nothing: a fixed point covers chains of any length and order.
        changed = True
        # Each pass may doom memories whose sources were doomed in this pass or an earlier one.
        while changed:
            changed = False  # assume this pass is the last
            # Look at every memory still outside the set.
            for mid, m in self.mems.items():
                # Derived from something being erased: erase it too.
                if mid not in doomed and any(s in doomed for s in m["sources"]):
                    doomed.add(mid)  # add it to the erasure set
                    changed = True  # something grew, so run another pass
        # Remove the records and their identity entries, so a later write of the same key gets a new id.
        for mid in doomed:
            m = self.mems.pop(mid)  # gone for every later call
            del self.index[(m["tenant"], m["user"], m["agent"], m["key"])]  # forget the identity too
        # Report the erased ids in number order.
        return sorted(doomed, key=lambda s: int(s.split("_")[1]))
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | Dana gets acme's policy, G_U1 gets globex's; `visible(DANA)` is `['mem_1', 'mem_2']` | tenant before team |
| Example 2 | `concise`, `friendly`, `formal`; overwrite returns `mem_1` | scope precedence and the upsert identity |
| Example 3 | erases `['mem_1', 'mem_2', 'mem_3']`; Sam keeps `['mem_4']` | the cascade reaches another user's derived memory |
| same user, different agent | `DANA` reads `None`, `DANA_HR` reads `L5` | private includes the agent |
| team and user ids collide across tenants | Lee gets `page #acme-oncall`; `visible(G_U9)` is `[]` | team names and user ids are tenant-local |
| erasure is scoped to the tenant | erases only `['mem_1']`; G_U1 still reads `2` | `delete_user` filters on the tenant |
| multi-level cascade | erases `['mem_1', 'mem_2', 'mem_3', 'mem_4']`; a second erasure returns `[]` | chains of any depth |
| sources must be visible | three `PermissionError`s; ids stay `mem_1`, `mem_2`, `mem_3` | source validation and no counter advance on failure |
| invalid scopes | two `ValueError`s, then `mem_1` | scope validation and team presence |
| overwrite changes scope and sources | Sam reads `None`; erasing u_2 also erases Dana's `mem_1`; the new write gets `mem_3` | overwrite replaces scope and sources; ids are never reused |
| most recent write wins a scope tie | `v2`, then `v3`, then `team-v` for Lee | `-seq` and overwrite as newest |
| busy store | 90 mixed writes, reads and two erasures | everything together across seven contexts |

## 10. Complexity

Every operation scans all live memories: `read` and `visible` are O(M), plus O(M log M) for the sort in `visible`. `write` is O(|sources|) for validation and O(1) for the upsert. `delete_user` is O(P · M · s), where P is the number of passes (the depth of the longest derivation chain plus one) and s is the number of sources per memory. With at most 300 operations, all of this is trivial.

At production scale you would not scan. Partition storage by tenant (Postgres row-level security on `tenant_id`, or one vector namespace per tenant) so the tenant filter is enforced below your code, and keep a reverse index `source -> derived ids` so erasure is a breadth-first search over only the affected memories, O(erased) instead of O(P · M).

## 11. If you got Wrong Answer

- **Example 1: Dana reads `"globex: no refunds after 14 days"`, and her `visible` includes `mem_3`.** Your tenant check is skipped for team scope.
- **"same user, different agent": `DANA` reads `L5`.** Private visibility compares only the user. Add the agent.
- **"erasure is scoped to the tenant" returns `['mem_1', 'mem_2', 'mem_3']`, and G_U1 then reads `None`.** `delete_user` matched on the user id alone and erased globex's u_1 too.
- **Example 3 erases only `['mem_1', 'mem_2']`, and Sam still sees `mem_3`.** The cascade never ran, for example a `changed = False` before the loop.
- **"multi-level cascade" erases `['mem_1', 'mem_2']` and Sam still reads `see forecast`.** You cascaded only one level: you compared against the original seed, not the growing set.
- **"sources must be visible" returns ids instead of `PermissionError`s**, and `visible(DANA)` becomes `['mem_2', 'mem_3', 'mem_5', 'mem_6']`. You never checked sources.
- **"invalid scopes" returns `mem_3` where `mem_1` is expected.** You took an id from the counter before validating, so each rejected write burned one.

## 12. Follow-ups an interviewer might ask

- *How do you make tenant isolation hold even if a developer forgets a filter?* Push it into storage: Postgres row-level security keyed on `tenant_id`, or a separate vector namespace per tenant in pgvector, Pinecone or Turbopuffer. The application predicate then becomes defence in depth, not the only line.
- *Erasure must also reach embeddings, caches and backups. How?* Write a tombstone per erased id, purge derived indexes and caches from it, and let a compaction job rewrite backups on their retention schedule. Log the erasure in an audit log without the erased content (problem 161, hash-chained-audit-log).
- *How would retrieval use this?* Filter by visibility **before** ranking, never after, or the top-k is short and leaks counts (problem 155, acl-aware-retrieval). Then fit what is visible into the prompt under a token budget (problem 107).
- *Should derived memories always be erased?* Legally, data derived from personal data is personal data, so yes by default. Some teams re-derive a cleaned version from the remaining sources instead. Either way you need lineage (`sources`), which is why it is stored on every memory.
- *How would you scale `delete_user`?* Keep a reverse map from each source to the ids derived from it, and run a BFS from the seed. Each erased memory is visited once.
