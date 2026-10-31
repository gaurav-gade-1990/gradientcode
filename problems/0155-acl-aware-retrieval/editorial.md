## Approach

There are two parts: who the user is (group closure) and what each document says (rule order). Ranking comes only after both.

**Group closure.** IdPs (Okta, Entra ID) nest groups: `sre` inside `engineering` inside `all-employees`. Invert the `subgroups` edges into child → parents and walk upward from the groups that list the user directly. A visited set handles the cyclic syncs you will meet in real directories.

```python
stack = [g for g, spec in groups.items() if user_id in spec["members"]]
while stack:
    g = stack.pop()
    if g not in found:
        found.add(g)
        stack.extend(parents.get(g, []))
```

**Rule order.** Check the most restrictive rules first: no ACL, deny user, deny group, allow user, allow group, then the default deny. Explicit deny wins, as in every serious policy engine, so being removed from a group is not undone by a stale direct grant.

**Filter, then rank.** Pass the allowed doc ids into the search so the index ranks only what the user may see:

```python
allowed = sorted(d for d, r in decisions.items() if r.startswith("allow"))
results = index.search(query, k, allowed) if allowed else []
```

## Common mistakes

- **Post-filtering top-k.** Search `k`, drop the restricted rows, and you return 1 result instead of 3. Worse, restricted text (salary bands, an M&A term sheet) has already passed through your service, its logs and maybe its cache.
- **Only direct memberships.** Most access is granted to parent groups, so ignoring nesting quietly hides documents from the people who own them.
- **A direct allow beating a group deny.** "Contractors may not see compensation data" must hold even when someone added a contractor to `allow_users` years ago.
- **Missing ACL means public.** Connector imports (an old Confluence export) often arrive without permissions. Fail closed.
- **Recursion with no visited set.** A cyclic group graph turns into a `RecursionError` on every query.

## Production notes

- Vector stores do this with metadata filters at query time: Pinecone and Qdrant payload filters, Weaviate `where`, OpenSearch `filter` inside `knn`, and pgvector with `WHERE doc_id = ANY($1)`. For large corpora, index each chunk's allowed principals (`acl_principals: [group ids, user ids]`) and filter on the user's principal set. That stays small even when the allowed doc list does not.
- Microsoft Graph connectors, Glean and Google Vertex AI Search all sync source-system ACLs with the content. Treat a stale ACL as a security bug and re-sync permissions faster than content.
- Cache the group closure per user with a short TTL, and invalidate it on SCIM group-change events.
- Log every decision reason ("allow:group:managers") for audits. Pair this with the policy engine (problem 160) for attribute conditions, and with tenant isolation (problem 159) so a shared index never crosses customers.
