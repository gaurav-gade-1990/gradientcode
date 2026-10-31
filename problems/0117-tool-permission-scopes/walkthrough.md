## 1. What the problem is really asking

An agent that acts **on behalf of** a user must never be able to do more than that user could do alone. The bug in the story is the classic *confused deputy*: the copilot's service account held broad scopes like `orders:*`, and the old check asked "may the agent do this?" instead of "may this user, through this agent, do this?"

Under the story, this is two small things:

- **A wildcard match predicate.** `grants(grant_list, scope)` answers "does this list of grants cover this one scope?" with exact, `"*"` and `"prefix:*"` rules.
- **An ordered chain of checks** that returns the *first* failure. Six checks, each with a fixed reason string.

The function is pure: no fakes, no side effects. The judge compares your list of decision dicts with the expected list, so each call's `allowed`, `reason` and `missing` must match exactly, and the reason must be the **first** check that fails, not any check that fails.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `user` | `{"id", "tenant", "roles"}` | roles → grants; `id` for the owner check; `tenant` for the tenant check |
| `agent` | `{"name", "allowed_tools", "scopes"}` | `allowed_tools` for check 2; `scopes` is the agent's own grant list |
| `role_scopes` | role → list of grants | concatenate over the user's roles; an unlisted role gives `[]` |
| `tools` | tool → `{"scopes", "resource_arg"?, "admin_scope"?}` | the required scopes, and whether checks 4–6 apply |
| `resources` | id → `{"tenant", "owner"}` | looked up by `arguments[resource_arg]` |
| `calls` | `[{"id", "tool", "arguments"}]` | one decision per call, in order |

Three details are easy to miss:

- **Effective means granted by both sides.** A scope is effective when the user's grants cover it **and** the agent's grants cover it. The two sides can cover it through *different* grant strings: Maya's exact `orders:read` and the agent's `orders:*` both cover `orders:read`.
- **The wildcard prefix keeps the colon.** `g[:-1]` of `"orders:*"` is `"orders:"`. So `orders:*` covers `orders:read` but not `orders_export:run`, and not a bare `"orders"`.
- **`role_scopes.get(r, [])`.** The case "missing scopes sorted and unknown role" gives a user the roles `["intern", "contractor"]`, neither of which is in `role_scopes`. Indexing with `[r]` raises `KeyError`.

## 3. Trace Example 2 by hand

Maya is a `support` user in `acme`. Her grants are `["orders:read", "refunds:create", "tickets:*"]`. The copilot's grants are `["orders:*", "refunds:create", "tickets:write", "orders_export:run"]`.

**`call_1`: `get_order(order_id="ord_1002")`**

| check | result |
|---|---|
| 1. tool exists | yes |
| 2. agent may use it | yes, `get_order` is in `allowed_tools` |
| 3. `orders:read` effective? | user: exact match; agent: `orders:*` → yes |
| 4. `ord_1002` exists | yes |
| 5. tenant `acme` == `acme` | yes |
| 6. owner is `u_omar`, not `u_maya`; admin scope `orders:admin` effective? | user: no grant covers it → **fail** |

Decision: `{"id": "call_1", "allowed": False, "reason": "not_owner", "missing": []}`.

**`call_2`: `export_orders(since=...)`.** The agent may run it, and the agent's grants include `orders_export:run` exactly. The user's don't: `orders:read` isn't it, and `tickets:*` covers only `tickets:...`. So check 3 fails with `missing: ['orders_export:run']`.

**`call_3`: `delete_customer(customer_id="cus_55")`.** The tool exists, but it's not in the copilot's `allowed_tools`, so the answer is `agent_tool_not_allowed`. The scope check never runs.

**Example 3** adds the admin path. Lena is a `support_lead`, whose grants include `orders:admin`. The agent's `orders:*` covers it too, so it's effective, and she can read Omar's `ord_1002`. Her `get_order` on `ord_7777` stops at check 5 (`globex` ≠ `acme`) with `cross_tenant`, before the admin scope is ever looked at. Her `refund_order` on `ord_1002` is `not_owner`, because `refund_order` has no `admin_scope`.

**The trickiest hidden case, "user broader than agent".** The user has `["*"]` (platform admin), but the agent has only `["orders:read"]`. `get_order` on Omar's order is `not_owner`: the user covers `orders:admin`, but the agent doesn't, so the admin scope isn't effective. `export_orders` and `delete_customer` are both `missing_scopes`. A powerful user gains nothing through a narrow agent.

## 4. Key idea: intersect per scope, never as strings

The tempting shortcut is `set(user_grants) & set(agent_grants)`. For Maya that set is `{"refunds:create"}`, because `orders:read` and `orders:*` are different strings even though one covers the other. Running Example 1 with that shortcut denies all three calls (`missing: ['orders:read']`, `['orders:read']`, `['tickets:write']`), when the expected answer allows all three.

The right intersection is taken one scope at a time, through the wildcard predicate:

```python
def effective(scope):
    return grants(user_grants, scope) and grants(agent_grants, scope)
```

The `and` is the whole security property. Swap it for `or` and you've rebuilt the incident: in "confused deputy: agent broader than user", Kim (finance) could suddenly add ticket notes, because the agent holds `tickets:write` even though she doesn't.

## 5. Key idea: tenant before admin

Checks 5 and 6 look similar, but they're different kinds of rule. Tenant isolation is a hard wall between customers. Admin is a privilege that applies *inside* one tenant. Putting the tenant check first means no admin scope can ever reach across it. In "cross tenant user with admin" the globex support lead reads globex's `ord_7777` through the admin scope (allowed), but `ord_1001` in acme is `cross_tenant`.

## 6. Plan before you code

```
grants(G, s): any g in G with g == s, g == "*", or (g ends ":*" and s starts with g[:-1])
user_grants = concat role_scopes.get(r, []) for r in user roles
effective(s) = grants(user_grants, s) and grants(agent scopes, s)
for each call:
    1 tool unknown                         -> unknown_tool
    2 tool not in agent allowed_tools      -> agent_tool_not_allowed
    3 missing = sorted non-effective scopes; non-empty -> missing_scopes
    no resource_arg                        -> allowed
    4 arg absent or not a resource key     -> resource_not_found
    5 tenant differs                       -> cross_tenant
    6 not owner and no effective admin     -> not_owner
    otherwise                              -> allowed
```

The predicate's three branches:

| grant `g` | covers `orders:read`? | covers `orders_export:run`? |
|---|---|---|
| `orders:read` | yes (exact) | no |
| `orders:*` | yes (`orders:` prefix) | no |
| `*` | yes | yes |

## 7. Build it one piece at a time

**Step 1: the predicate.** One loop, returning as soon as any grant matches.

```python
def grants(grant_list, scope):
    for g in grant_list:
        if g == scope or g == "*":
            return True
        if g.endswith(":*") and scope.startswith(g[:-1]):
            return True
    return False
```

`g[:-1]` strips only the `*`, keeping the colon. `g[:-2]` would give `"orders"`, and `"orders_export:run".startswith("orders")` is `True`. That's the loose-prefix bug.

**Step 2: both grant lists, and `effective`.** Build the user's grants once, outside the call loop, with a nested comprehension that concatenates in role order.

```python
    user_grants = [g for r in user["roles"] for g in role_scopes.get(r, [])]
    agent_grants = agent["scopes"]

    def effective(scope):
        return grants(user_grants, scope) and grants(agent_grants, scope)
```

**Step 3: checks 1–3.** Use `tools.get` so an unknown tool returns `None` instead of raising. Check 1 has to come before check 2: in "resource checks", `unknown_tool_x` is in neither `tools` nor `allowed_tools`, and the expected reason is `unknown_tool`.

```python
        tool = tools.get(call["tool"])
        if tool is None:
            return "unknown_tool", []
        if call["tool"] not in agent["allowed_tools"]:
            return "agent_tool_not_allowed", []
        missing = sorted(s for s in tool["scopes"] if not effective(s))
        if missing:
            return "missing_scopes", missing
```

**Step 4: checks 4–6, only with a `resource_arg`.** `.get(arg)` handles an absent argument. The `isinstance(rid, str)` guard means a non-string id, such as the integer `1001` in "resource checks", is reported as `resource_not_found`; it would also protect you from an unhashable value like a list, where `rid in resources` would raise `TypeError`.

```python
        arg = tool.get("resource_arg")
        if arg is None:
            return None, []
        rid = call["arguments"].get(arg)
        if not isinstance(rid, str) or rid not in resources:
            return "resource_not_found", []
        res = resources[rid]
        if res["tenant"] != user["tenant"]:
            return "cross_tenant", []
        admin = tool.get("admin_scope")
        if res["owner"] != user["id"] and not (admin and effective(admin)):
            return "not_owner", []
        return None, []
```

`admin and effective(admin)` short-circuits, so a tool without an `admin_scope` never calls `effective(None)`.

## 8. Full solution

```python
def grants(grant_list, scope):  # does any grant in this list cover this one scope?
    for g in grant_list:  # try each grant until one matches
        if g == scope or g == "*":  # an exact grant, or the global wildcard
            return True  # covered
        if g.endswith(":*") and scope.startswith(g[:-1]):  # "orders:*" -> prefix "orders:", colon kept
            return True  # covered by the prefix wildcard
    return False  # no grant covers it


def authorize_calls(user, agent, role_scopes, tools, resources, calls):  # one decision per call, in order
    user_grants = [g for r in user["roles"] for g in role_scopes.get(r, [])]  # concat over roles; unknown role -> nothing
    agent_grants = agent["scopes"]  # the agent's own grants, the other side of the intersection

    def effective(scope):  # the on-behalf-of rule: a scope counts only if BOTH sides cover it
        return grants(user_grants, scope) and grants(agent_grants, scope)  # "and", never "or" (confused deputy)

    def decide(call):  # run the six checks in order; return (reason, missing) for the first failure
        tool = tools.get(call["tool"])  # None for a tool we've never heard of
        if tool is None:  # check 1 comes first, even if the agent doesn't list it either
            return "unknown_tool", []  # nothing more to check
        if call["tool"] not in agent["allowed_tools"]:  # check 2: this agent isn't wired for this tool
            return "agent_tool_not_allowed", []  # deny before looking at scopes
        missing = sorted(s for s in tool["scopes"] if not effective(s))  # check 3: every required scope, sorted
        if missing:  # at least one required scope isn't effective
            return "missing_scopes", missing  # report exactly which ones
        arg = tool.get("resource_arg")  # checks 4-6 only apply to tools that touch one resource
        if arg is None:  # no resource: the scopes were enough
            return None, []  # allowed
        rid = call["arguments"].get(arg)  # the resource id the model passed, or None if absent
        if not isinstance(rid, str) or rid not in resources:  # check 4: absent, wrong type, or unknown id
            return "resource_not_found", []  # don't leak whether a similar id exists
        res = resources[rid]  # the resource's tenant and owner
        if res["tenant"] != user["tenant"]:  # check 5: a hard wall between customers
            return "cross_tenant", []  # comes before admin, so admin can never cross it
        admin = tool.get("admin_scope")  # some tools let an effective admin scope stand in for ownership
        if res["owner"] != user["id"] and not (admin and effective(admin)):  # check 6: owner, or effective admin
            return "not_owner", []  # neither the owner nor an effective admin
        return None, []  # passed every check

    out = []  # decisions in call order
    for call in calls:  # each call is decided on its own; a denial doesn't affect the rest
        reason, missing = decide(call)  # first failing check, or None
        # allowed is derived from reason, so the two can never disagree
        out.append({"id": call["id"], "allowed": reason is None, "reason": reason, "missing": missing})
    return out  # one decision per call
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | all three allowed | the two sides cover a scope through different grants (`orders:read` vs `orders:*`, `tickets:*` vs `tickets:write`) |
| Example 2 | `not_owner`, `missing_scopes ['orders_export:run']`, `agent_tool_not_allowed` | the owner check, a scope only the agent has, and check 2 before check 3 |
| Example 3 | allowed, `cross_tenant`, `not_owner` | an effective admin scope; tenant before admin; a tool without `admin_scope` |
| confused deputy: agent broader than user | `not_owner`, `missing_scopes ['tickets:write']`, `not_owner` | `and`, not `or`: the agent's `tickets:write` doesn't help Kim |
| user broader than agent | `not_owner`, `missing_scopes`, `missing_scopes` | the user's `*` is capped by the agent's narrow grants, including the admin scope |
| wildcard on both sides | both allowed | `refunds:*` on both sides; admin reads another user's order |
| prefix without colon does not match | `missing_scopes ['orders_export:run']`, then allowed | `orders:*` does not cover `orders_export:run` |
| resource checks | `resource_not_found` ×2, `cross_tenant`, `resource_not_found`, `unknown_tool` | unknown id, absent arg, other tenant, integer id, check 1 before check 2 |
| missing scopes sorted and unknown role | `missing_scopes ['orders:read', 'refunds:create']`, `missing_scopes ['tickets:write']` | `role_scopes.get(r, [])`; all missing scopes listed |
| cross tenant user with admin | `cross_tenant`, allowed, `not_owner` | admin works inside the user's own tenant only |

## 10. Complexity

For `C` calls, each tool needing at most `S` scopes, and grant lists of length `G` (user plus agent), the work is O(C · S · G) string comparisons, plus O(S log S) to sort the missing list. With at most 50 calls and a handful of grants, it's microseconds.

At scale, the cost isn't the matching, it's where the facts live. Roles, ownership and tenancy usually sit in a database or a policy service, so you'd cache the user's grants per request and batch the resource lookups. Because this check runs before **every** tool call, it has to stay fast and must never fail open: if the policy store is unreachable, deny.

## 11. If you got Wrong Answer

- **Example 1 denies everything with `missing: ['orders:read']`.** You intersected the literal grant strings. Intersect per scope with `grants(user) and grants(agent)`.
- **Example 2's `export_orders` is allowed.** You're checking the agent's grants only, or using `or`. Both rebuild the confused deputy.
- **"prefix without colon does not match" allows `export_orders`.** Your wildcard prefix dropped the colon (`g[:-2]`). Use `g[:-1]`.
- **Example 3's `ord_7777` call is allowed.** Your admin check runs before the tenant check. Move the tenant check first.
- **`resource checks` reports `agent_tool_not_allowed` for `unknown_tool_x`.** Check 2 runs before check 1. Look the tool up in `tools` first.
- **Runtime Error with `KeyError: 'intern'`.** Use `role_scopes.get(r, [])`.

## 12. Follow-ups an interviewer might ask

- *How does this map to real OAuth?* It's the on-behalf-of pattern. The agent exchanges the user's token for one whose scopes are the intersection of what the user consented to and what the client is registered for (RFC 8693 token exchange, Entra ID OBO). MCP's authorization spec uses OAuth 2.1 scopes the same way.
- *Where would these rules live in production?* In a policy engine such as OPA/Rego or Cedar, or a relationship store like SpiceDB or OpenFGA, where ownership is a tuple such as `order:ord_1002#owner@user:u_omar`. See problem 160 (policy-engine).
- *What should the agent see when a call is denied?* Return the reason as a tool error ("you can't refund orders you don't own"), so the model explains it instead of retrying. Never return the resource's real owner or tenant.
- *How would you audit this?* Log user, agent, tool, resource, decision and reason for every call (problem 161). Over time, scopes an agent never uses are candidates to remove from `agent.scopes`.
- *What runs before this check?* Argument schema validation (problem 113, tool-args-schema-validation). The same intersection idea applies to retrieval, where a user should only see documents they could open directly (problem 155, acl-aware-retrieval).
