## 1. What the problem is really asking

One vector index holds HR, legal and engineering documents. Every employee searches the same index, but each one may only see the documents they are allowed to open. You're writing the gate that sits in front of the search.

Under the story there are three small, separate jobs:

1. **Graph reachability.** Work out every group the user belongs to, including through nested subgroups. That's a walk over a directed graph that may contain cycles.
2. **An ordered rule list.** For each document, try six rules in a fixed order and record the first one that matches. Deny rules come before allow rules.
3. **Filter, then rank.** Hand the allowed doc ids to the index so it ranks only what the user may see.

The judge records two things besides your return value: every call to `index.search`, with its `limit` and its `doc_ids` filter. So *how* you search is graded, not just what you return. A search with `doc_ids=None` shows up in `index_calls` even if you drop the bad rows afterwards.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `user_id` | the employee asking, e.g. `"maya.chen"` | find their groups, match `allow_users` / `deny_users` |
| `query`, `k` | the search text and how many hits to return | passed straight to `index.search` |
| `index.doc_ids()` | sorted list of every doc with chunks | the docs you must make a decision for |
| `index.search(query, limit, doc_ids)` | ranked hits from only those docs | call it **once**, with the allowed list |
| `acls[doc_id]` | optional lists `allow_users`, `allow_groups`, `deny_users`, `deny_groups` | the rules for one document |
| `groups[g]` | `{"members": [...], "subgroups": [...]}` | the membership graph |
| return | `{"decisions": {doc: reason}, "results": hits}` | one reason per doc, hits unchanged |

Three details are easy to miss:

- **The subgroup edge points down, but you need to walk up.** `engineering.subgroups = ["sre", "platform"]` means members of `sre` are also in `engineering`. A user is listed in `sre.members`, so you start there and climb to `engineering`, then to `all-employees`.
- **A doc with no entry in `acls` is denied**, not public. `wiki/imported-confluence` is in the index but not in `ACLS`, so every user gets `"deny:no_acl"` for it.
- **The reason string names one group**, the alphabetically smallest match from *that rule's* list. Not the first in list order, and not the first group you found during the walk.

## 3. Trace Example 1 by hand

`maya.chen`, query `"Senior Engineer salary base pay"`, `k = 3`.

**Step 1: her groups.** She is listed directly in `sre` and `managers`. Climbing up: `sre` is a subgroup of `engineering`, and `engineering` is a subgroup of `all-employees`. `managers` has no parent. Her set is:

```python
{"all-employees", "engineering", "managers", "sre"}
```

**Step 2: one decision per doc.** The first matching rule wins:

| doc | ACL | first rule that matches | reason |
|---|---|---|---|
| eng/incident-db-outage | allow sre, engineering | 5 (allow group) | `allow:group:engineering` |
| eng/oncall-handbook | allow engineering, deny omar.haddad | 5 | `allow:group:engineering` |
| hr/pto-policy | allow all-employees | 5 | `allow:group:all-employees` |
| hr/salary-bands-2026 | allow hr-comp, managers; deny contractors | 5 | `allow:group:managers` |
| legal/project-falcon | allow ceo, general.counsel; deny all-employees | 3 (deny group) | `deny:group:all-employees` |
| wiki/holiday-calendar | allow all-employees, contractors | 5 | `allow:group:all-employees` |
| wiki/imported-confluence | none | 1 (no ACL) | `deny:no_acl` |

Look at the incident doc. Maya matches both `sre` and `engineering` in `allow_groups`. Sorted, `"engineering" < "sre"`, so the reason is `allow:group:engineering`, even though `sre` is the group she's directly in and comes first in the list.

**Step 3: one search.** `allowed` is the five allowed ids, sorted. You call `index.search(query, 3, allowed)` once, and the judge records `{"limit": 3, "doc_ids": ['eng/incident-db-outage', 'eng/oncall-handbook', 'hr/pto-policy', 'hr/salary-bands-2026', 'wiki/holiday-calendar']}`. The hits are `salary-bands-2026#1` (0.547723), `salary-bands-2026#2` (0.298142) and `oncall-handbook#1` (0.140028).

**Now see why filtering first matters.** Ranked over *every* chunk, the top three for this query are `salary-bands-2026#1` (0.547723), `imported-confluence#1` (0.5) and `project-falcon#1` (0.420084). Two of those three are denied to Maya. If you search with no filter and drop them, she gets **one** result instead of three, and the acquisition term sheet has already passed through your process. In Example 2 (`lee.kim`, who is a contractor) the same mistake returns **zero** results, because none of the global top three is hers.

**The trickiest hidden case, "cyclic groups".** `CYCLE_GROUPS` makes `platform` and `infra-guild` list each other as subgroups, and `infra-guild` also lists `ghost-group`, which isn't in `groups` at all. `priya.nair` is a direct member of `infra-guild`. Climbing up: `infra-guild` is a subgroup of `platform`, `platform` is a subgroup of both `engineering` and `infra-guild` (already visited, skip), `engineering` leads to `all-employees`. Her set is `['all-employees', 'engineering', 'infra-guild', 'platform']`, and the walk ends because of the visited check.

## 4. Key idea: invert the edges and walk up with a visited set

You could answer "is the user in group G?" by recursing downward: G contains the user if the user is in `G.members` or any subgroup of G contains them. It reads nicely but has two problems. It repeats work for every group you ask about, and on a cycle it recurses forever when the user isn't found.

The cleaner approach is to flip each `subgroups` edge into child → parents once:

```python
parents = {"sre": ["engineering"], "platform": ["engineering"], "engineering": ["all-employees"], ...}
```

Then start from the groups that list the user directly and push parents onto a stack. A `found` set does double duty: it's the answer, and it's the visited set that stops the cycle. Subgroup ids that aren't in `groups` (like `ghost-group`) are harmless, because they never list the user and no walk starts from them.

## 5. Key idea: deny before allow, and a direct allow doesn't save you

The rule order is the whole policy. Read the table in the problem as "most restrictive first":

| rule | why it sits there |
|---|---|
| 1 no ACL | fail closed: connector imports often arrive without permissions |
| 2 deny user | the most specific "no" |
| 3 deny group | a group-level "no" still beats... |
| 4 allow user | ...a direct "yes" |
| 5 allow group | the common way access is granted |
| 6 default deny | nothing granted it |

The case that tests rule 3 against rule 4 is the CEO. `legal/project-falcon` has `allow_users: ["ceo", ...]` and `deny_groups: ["all-employees"]`. The CEO is in `all-employees`, so the answer is `deny:group:all-employees`. That feels odd for a CEO, but it's exactly how policy engines behave: "contractors may not see compensation data" has to hold even if someone added a contractor to `allow_users` years ago. `general.counsel`, who is in no group, does get the doc through `allow:user`.

## 6. Plan before you code

```
mine = every group the user belongs to (walk up from direct memberships)
for each doc in index.doc_ids():
    acl = acls.get(doc)
    no acl                         -> "deny:no_acl"
    user in deny_users             -> "deny:user"
    deny_groups ∩ mine non-empty   -> "deny:group:" + smallest
    user in allow_users            -> "allow:user"
    allow_groups ∩ mine non-empty  -> "allow:group:" + smallest
    otherwise                      -> "deny:default"
allowed = sorted docs whose reason starts with "allow"
results = index.search(query, k, allowed) if allowed else []
```

## 7. Build it one piece at a time

**Step 1: the group closure.**

```python
def user_groups(user_id, groups):
    parents = {}
    for g, spec in groups.items():
        for sub in spec.get("subgroups", []):
            parents.setdefault(sub, []).append(g)
    found = set()
    stack = [g for g, spec in groups.items() if user_id in spec.get("members", [])]
    while stack:
        g = stack.pop()
        if g in found:
            continue
        found.add(g)
        stack.extend(parents.get(g, []))
    return found
```

The `if g in found: continue` is the line that makes cycles safe. Without it, `platform` and `infra-guild` push each other forever. Use `.get(..., [])` everywhere: a group spec might omit a key, and a missing ACL list means an empty list.

**Step 2: one decision.** Set intersection plus `sorted` gives you "the alphabetically smallest matching group" in one line:

```python
def decide(user_id, mine, acl):
    if acl is None:
        return "deny:no_acl"
    if user_id in acl.get("deny_users", []):
        return "deny:user"
    hit = sorted(set(acl.get("deny_groups", [])) & mine)
    if hit:
        return "deny:group:" + hit[0]
    if user_id in acl.get("allow_users", []):
        return "allow:user"
    hit = sorted(set(acl.get("allow_groups", [])) & mine)
    if hit:
        return "allow:group:" + hit[0]
    return "deny:default"
```

Each rule returns, so the first match decides with no extra bookkeeping. Pass `acls.get(d)` in, so a missing ACL arrives as `None` and hits rule 1.

**Step 3: filter inside the search.** Build `allowed` from the reasons, sort it, and skip the call when it's empty:

```python
    allowed = sorted(d for d, r in decisions.items() if r.startswith("allow"))
    results = index.search(query, k, allowed) if allowed else []
```

The empty check is not an optimisation. Example 3 expects `index_calls: []` for a visitor with no access. Calling `index.search(query, k, [])` returns no hits, but it still shows up as a recorded call, and the case fails.

## 8. Full solution

```python
# Every group the user belongs to, directly or through any chain of subgroups.
def user_groups(user_id, groups):
    parents = {}  # child group -> the groups that list it as a subgroup
    for g, spec in groups.items():  # look at every group once to build the reverse edges
        for sub in spec.get("subgroups", []):  # each subgroup's members also belong to g
            parents.setdefault(sub, []).append(g)  # so climbing from sub reaches g
    found = set()  # groups proven to contain the user; doubles as the visited set
    # start from the groups that list the user directly
    stack = [g for g, spec in groups.items() if user_id in spec.get("members", [])]
    while stack:  # keep climbing until no new parent groups remain
        g = stack.pop()  # take the next group the user is known to be in
        if g in found:  # already handled, which is what stops a cyclic group graph
            continue  # skip it rather than walking the cycle forever
        found.add(g)  # record the membership
        stack.extend(parents.get(g, []))  # being in g puts the user in every parent of g
    return found  # the full transitive membership


# The first matching rule, most restrictive first, decides one document.
def decide(user_id, mine, acl):
    if acl is None:  # an imported doc with no permissions at all
        return "deny:no_acl"  # fail closed instead of treating it as public
    if user_id in acl.get("deny_users", []):  # the most specific "no"
        return "deny:user"  # a direct deny beats every allow
    hit = sorted(set(acl.get("deny_groups", [])) & mine)  # denied groups the user is in, smallest first
    if hit:  # any group-level deny applies
        return "deny:group:" + hit[0]  # it even beats a direct allow_users entry
    if user_id in acl.get("allow_users", []):  # a direct grant, checked only after all denies
        return "allow:user"  # the user is named on the doc
    hit = sorted(set(acl.get("allow_groups", [])) & mine)  # allowed groups the user is in, smallest first
    if hit:  # access through group membership
        return "allow:group:" + hit[0]  # name the alphabetically smallest matching group
    return "deny:default"  # nothing granted access, so deny


# Decide every doc, then rank only the allowed ones.
def search_with_acl(user_id, query, k, index, acls, groups):
    mine = user_groups(user_id, groups)  # compute the closure once, reuse it for every doc
    # one reason per indexed doc; acls.get turns a missing ACL into None for rule 1
    decisions = {d: decide(user_id, mine, acls.get(d)) for d in index.doc_ids()}
    allowed = sorted(d for d, r in decisions.items() if r.startswith("allow"))  # the filter, sorted
    # filter inside the search so all k slots come from visible docs; no access means no call
    results = index.search(query, k, allowed) if allowed else []
    return {"decisions": decisions, "results": results}  # hits are returned unchanged
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | 5 docs allowed, 3 hits, one call over the 5 ids | nesting (`sre` → `engineering` → `all-employees`), smallest group name, filter inside the search |
| Example 2 | salary bands `deny:group:contractors`, 3 hits from 4 allowed docs | a group deny beats a group allow, and k is filled from her own docs |
| Example 3 | every doc denied, `results: []`, `index_calls: []` | no access means no index call at all |
| hr comp two levels deep | salary bands `allow:group:hr-comp`, 4 hits | `hr-comp` → `people-ops` → `all-employees` |
| direct deny beats group allow | on-call handbook `deny:user` for `omar.haddad` | rule 2 before rule 5 |
| group deny beats direct allow | Falcon `deny:group:all-employees` for `ceo` | rule 3 before rule 4 |
| allow user outside every group | Falcon `allow:user`, 1 hit with `limit: 5` | a user with no groups can still be named directly |
| sales sees only company docs | 2 hits from `hr/pto-policy` and `wiki/holiday-calendar` | fewer allowed chunks than `k` is fine |
| cyclic groups | `priya.nair` gets the engineering docs, 3 hits | the visited set, and the unknown `ghost-group` |
| k larger than allowed chunks | 6 hits with `limit: 20` | pass `k` through untouched; the index stops at what exists |
| smallest matching group named | incident doc `allow:group:engineering`, PTO `deny:group:managers` | sorted intersection, not list order |

## 10. Complexity

Building `parents` touches every subgroup edge once, and the walk visits each group at most once: O(G + E) for G groups and E edges. Each decision does a few list lookups and an intersection: O(D · A) for D docs and ACL lists of length A. The search itself is the index's cost. At this scale (30 docs, 20 groups) it's all instant.

In production the problem is the size of `allowed`. A user who can see a million docs makes a million-id filter. Real systems flip it: each chunk stores the principals that may read it (`acl_principals: [group ids, user ids]`), and the query filters on the user's principal set, which stays small. Cache the group closure per user with a short TTL and invalidate it on directory change events.

## 11. If you got Wrong Answer

Compare `index_calls` first, then `decisions`.

- **`index_calls` shows `doc_ids: None`, and you have fewer results than `k`.** You searched everything and filtered afterwards. Example 1 returns 1 hit instead of 3, Example 2 returns none. Pass `allowed` into `index.search`.
- **Example 3 has an index call with an empty list.** Skip the call when `allowed` is empty.
- **`wiki/imported-confluence` is allowed, and it shows up in Example 1's results at 0.5.** You treated a missing ACL as public. Return `"deny:no_acl"`.
- **Nested docs are denied with `deny:default`.** You only used direct memberships. In Example 1, Maya loses the on-call handbook (granted to `engineering`) and the PTO and holiday docs (granted to `all-employees`), and the incident doc's reason turns into `allow:group:sre`. Walk up the subgroup graph.
- **"group deny beats direct allow" gives the CEO `allow:user`.** Your `allow_users` check runs before the `deny_groups` check. It also breaks "smallest matching group named", where Maya is in `allow_users` but `deny_groups` names her groups.
- **The reason says `allow:group:sre` where `allow:group:engineering` is expected.** You took the first match in list order. Sort the intersection. That fails Example 1, "k larger than allowed chunks" and "smallest matching group named".
- **`RecursionError`.** A recursive "does G contain the user?" check with no visited set. On `CYCLE_GROUPS` it recurses forever for any user who isn't in the cycle, such as `maya.chen`. The "cyclic groups" case asks about `priya.nair`, who *is* in it, so short-circuiting saves a naive version there. Don't rely on that: use the explicit stack with `found`.

## 12. Follow-ups an interviewer might ask

- *The allowed list has a million ids. What now?* Store each chunk's readable principals in the index and filter on the user's small set of principals. Pinecone, Qdrant and Weaviate metadata filters, OpenSearch's `filter` inside `knn`, and pgvector with `WHERE ... = ANY($1)` all support this at query time.
- *Why not search then filter, with a bigger `k`?* You still can't promise `k` results, and restricted text has already flowed through your service, its logs and possibly its cache. Filtering inside the search means it never leaves the store.
- *How fresh do ACLs need to be?* Fresher than the content. A stale ACL is a security bug, so re-sync permissions on directory events (SCIM group changes) rather than on the content crawl schedule.
- *How do you add conditions like "only on a managed device" or "only in business hours"?* That's attribute-based policy, which problem 160 (policy-engine) covers. Problem 159 (tenant-isolated-memory) adds the hard boundary between customers that sits above all of this.
- *What would you log?* Every decision reason (`allow:group:managers`) per query. When someone asks "why could she see this?", the reason string is the audit answer.
