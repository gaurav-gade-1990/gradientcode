## Approach

Everything rests on one predicate:

```python
def grants(grant_list, scope):
    return any(g == scope or g == "*" or (g.endswith(":*") and scope.startswith(g[:-1]))
               for g in grant_list)

def effective(scope):
    return grants(user_grants, scope) and grants(agent_grants, scope)
```

The **intersection** is taken scope by scope through `grants`, never by intersecting the literal strings. Then run the six checks in order and return the first failure:

1. the tool exists → 2. the agent may use it → 3. every required scope is effective → 4. the resource exists → 5. same tenant → 6. owner, or an effective admin scope.

Put the tenant check before the admin check. Tenant isolation is a hard wall, while admin is a privilege that applies *inside* a tenant.

## Common mistakes

- **Union instead of intersection (the confused deputy).** The agent's service account holds `orders:*` so it can serve many users. Checking `user OR agent` lets any user borrow those scopes through the agent.
- **Checking the agent only.** This is the same incident in a simpler form: the copilot runs with its own credentials and ignores who is asking.
- **Intersecting strings.** `{"orders:*"} & {"orders:read"}` is empty, so legitimate calls get denied, and someone "fixes" it by widening the grants.
- **Loose wildcard prefix.** Matching `"orders"` instead of `"orders:"` makes `orders:*` grant `orders_export:run`.
- **Admin bypasses the tenant.** A support lead at one customer can read another customer's orders. In a multi-tenant SaaS this is the incident that ends up in a breach notice.

## Production notes

- This is OAuth's **on-behalf-of** pattern. The agent presents a token whose scopes are the intersection of what the user consented to and what the client registered for (RFC 8693 token exchange, Entra ID OBO, Okta). MCP's authorization spec uses OAuth 2.1 scopes the same way.
- Real systems express these rules in a policy engine (OPA/Rego, Cedar, Zanzibar-style ReBAC such as SpiceDB or OpenFGA) rather than in `if` statements. Ownership becomes a relation tuple like `order:1002#owner@user:omar`. See problem 160.
- Return the denial **reason** to the agent as a tool error ("you can't refund orders you don't own"). The model can then explain it to the user instead of retrying.
- Log every decision with user, agent, tool, resource and reason in an audit log (problem 161). Least privilege also means shrinking `agent.scopes` to what the agent actually uses.
- Pairs with **tool-args-schema-validation** (113), which runs before this check, and **acl-aware-retrieval** (155), which applies the same idea to documents.
