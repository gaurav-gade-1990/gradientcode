Your enterprise search assistant indexes HR, legal and engineering documents in one vector index. Each answer must only use documents the asking employee can open. Write the permission-aware search.

`search_with_acl(user_id, query, k, index, acls, groups)` returns `{"decisions": {...}, "results": [...]}`.

**Inputs**

- `index.doc_ids()` returns the sorted list of every doc id that has chunks in the index.
- `index.search(query, limit, doc_ids)` returns up to `limit` hits `{"chunk_id", "doc_id", "score"}`, best first, taken **only** from the docs in `doc_ids` (a list). Passing `doc_ids=None` searches everything.
- `acls[doc_id]` is a dict with optional lists `allow_users`, `allow_groups`, `deny_users`, `deny_groups` (a missing key is an empty list).
- `groups[group_id]` is `{"members": [user ids], "subgroups": [group ids]}`. A user belongs to group `G` if they are in `G.members`, or if they belong to any group in `G.subgroups`. This is transitive. The graph can contain cycles, and subgroup ids not in `groups` have no members.

**Decision for each doc in `index.doc_ids()`.** Apply these rules in order. The first match decides, and the reason string goes into `decisions[doc_id]`:

| # | rule | decision | reason |
|---|---|---|---|
| 1 | the doc has no entry in `acls` | deny | `"deny:no_acl"` |
| 2 | `user_id` is in `deny_users` | deny | `"deny:user"` |
| 3 | the user belongs to a group in `deny_groups` | deny | `"deny:group:<g>"` |
| 4 | `user_id` is in `allow_users` | allow | `"allow:user"` |
| 5 | the user belongs to a group in `allow_groups` | allow | `"allow:group:<g>"` |
| 6 | otherwise | deny | `"deny:default"` |

For rules 3 and 5, `<g>` is the alphabetically smallest matching group id from that list. A deny always beats an allow, including a direct `allow_users` entry.

**Search.** Let `allowed` be the sorted list of allowed doc ids. If it is empty, do not call the index and return `"results": []`. Otherwise call `index.search(query, k, allowed)` exactly once and return its hits unchanged as `"results"`. Never search without a filter and drop rows afterwards: that returns fewer than `k` results, and restricted text passes through your service.

The judge records every index call, its `limit` and its `doc_ids` filter, and compares the decisions and the results.

**Constraints**

- up to 30 docs, 20 groups and 50 chunks
- `1 <= k <= 20`
- Group nesting can be deeper than one level and can be cyclic.
