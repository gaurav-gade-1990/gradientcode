Teams on your agent platform deploy AI coworkers that call internal APIs (refunds, ticket exports, customer records). Every call passes through a central policy engine, like OPA or AWS IAM, that decides whether the agent may do it and records which rule decided. Write the evaluator.

`evaluate(rules, requests)` returns one decision per request, in order.

**A request**

```
{"principal": {"id": "agent:billing-bot", "roles": ["refund-agent"], "tenant": "acme", ...},
 "action": "refunds:create",
 "resource": {"id": "acme/orders/1182", "tenant": "acme", "amount": 420, ...},
 "context": {"mfa": true, ...}}
```

The principal's **identities** are its `id` plus `"role:" + r` for each role in `roles` (`roles` may be missing).

**A rule**

```
{"id": "small-refunds", "effect": "allow" | "deny",
 "principals": [glob, ...], "actions": [glob, ...], "resources": [glob, ...],
 "conditions": [{"attr": path, "op": op, "value": v}, ...]}
```

`conditions` may be missing (no conditions). A rule **matches** a request when all four hold:

1. some pattern in `principals` matches some identity,
2. some pattern in `actions` matches `action`,
3. some pattern in `resources` matches `resource["id"]`,
4. every condition is true.

**Globs.** `*` matches any run of characters, including none and including `:` and `/`. Every other character matches only itself (case-sensitive). The pattern must match the **whole** string.

**Conditions.** `attr` is a dotted path into the request, such as `principal.tenant`, `resource.amount` or `context.mfa`. `value` is a literal, or `{"attr": path}` to compare against another attribute. A path that doesn't exist is **missing**, and any condition with a missing side is **false**, whatever the op.

| op | true when |
|---|---|
| `eq`, `neq` | `left == right`, `left != right` |
| `in`, `not_in` | `right` is a list and `left` is / isn't in it |
| `lt`, `lte`, `gt`, `gte` | both sides are numbers (int or float, not bool) and the comparison holds |

**Decision**

| matching rules | `decision` | `reason` | `rule` |
|---|---|---|---|
| at least one deny | `"deny"` | `"explicit_deny"` | the most specific matching deny |
| allows only | `"allow"` | `"allowed"` | the most specific matching allow |
| none | `"deny"` | `"no_match"` | `None` |

An explicit deny always wins, however specific the allows are. **Specificity** of a matching rule is the tuple `(R, A, C)`, compared largest first: `R` is the number of non-`*` characters in the longest-literal resource pattern of that rule that matched, `A` is the same for its action patterns, and `C` is its number of conditions. Ties go to the rule that comes first in `rules`.

Return `{"decision", "reason", "rule", "matched"}` per request, where `matched` lists the ids of every matching rule in `rules` order.

**Constraints**

- `0 <= len(rules) <= 100`, `1 <= len(requests) <= 200`
- Rule ids are unique. Globs contain no characters special to anything but `*`.
