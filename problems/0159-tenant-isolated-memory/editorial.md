## Approach

Everything hangs off one visibility predicate. Write it once and call it from `read`, `visible` and the source check in `write`, so the three can never disagree.

```python
def _visible(self, m, ctx):
    if m["tenant"] != ctx["tenant"]:          # always first, for every scope
        return False
    if m["scope"] == "private":
        return m["user"] == ctx["user"] and m["agent"] == ctx["agent"]
    if m["scope"] == "team":
        return ctx["team"] is not None and m["team"] == ctx["team"]
    return True                               # org
```

**Identity.** The upsert key is `(tenant, user, agent, key)`. Including the tenant matters because user ids repeat across tenants; including the agent keeps a user's HR agent and coding agent from overwriting (or reading) each other's notes.

**Precedence.** `read` sorts the visible candidates by `(scope rank, -write seq)`. A personal preference beats a team default, which beats an org default, and within a scope the latest write wins.

**Erasure.** Derived memories form a DAG through `sources`. Erasure is a reachability closure: seed with the user's memories, then add any memory with a source in the set until a pass adds nothing. Checking sources on write guarantees the graph never crosses a tenant, so the closure can't either.

## Common mistakes

- **Tenant check only on some scopes.** "Team" memories filtered by team name alone leak between two companies that both have a `support` team.
- **Private means "same user".** The user's HR agent stored a salary band, and the user's general assistant now quotes it in a shared channel.
- **Erasing by user id alone.** `delete_user("acme", "u_1")` also wipes globex's `u_1`, a different customer.
- **No cascade, or a one-level cascade.** The erased fact survives inside the summary of the summary. Regulators treat derived data as personal data too.
- **Trusting `sources`.** Accepting a source the writer can't see lets an agent launder another tenant's memory into its own by "deriving" from it, and makes cascades cross tenants.

## Production notes

- Mem0, LangGraph's store, Zep and Letta all namespace memories by tuples like `(org, user, agent)`. Enforce the tenant at the storage layer too: Postgres row-level security keyed on `tenant_id`, or one vector namespace per tenant in pgvector, Pinecone or Turbopuffer, so a missing `WHERE` clause can't leak.
- Keep lineage (`sources`) as first-class data. It is what makes erasure, "why does the agent believe this?", and retraction of a wrong fact possible.
- Erasure has to reach the derived embeddings, caches, summaries and backups as well, usually through tombstones plus a compaction job, and it should write an audit event (see `hash-chained-audit-log`) without storing the erased content.
- Pairs with `acl-aware-retrieval` (filter before ranking) and `memory-under-token-budget` (what to put in the prompt once you know what is visible).
