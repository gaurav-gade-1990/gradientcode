## Approach

Separate **matching** from **combining**. First find every rule that applies, then combine them with a fixed algorithm. Never let rule order decide.

**Matching.** Compile each glob into an anchored regex (escape every character, turn `*` into `.*`) and use `fullmatch`. Resolve attribute paths to a `MISSING` sentinel, and make any condition that touches a missing value false.

```python
def condition_holds(req, c):
    left, right = resolve(req, c["attr"]), c["value"]
    if isinstance(right, dict) and "attr" in right:
        right = resolve(req, right["attr"])
    if left is MISSING or right is MISSING:
        return False
    ...
```

**Combining.** This is deny-overrides, the AWS IAM model:

1. any matching deny → deny,
2. else any matching allow → allow,
3. else deny by default.

Specificity only decides which rule id you report, inside the winning effect: the rule with the most literal resource characters, then action characters, then the most conditions, then the earliest. That id goes into the audit log, so it has to be deterministic. "Which rule let the billing bot refund $2,500?" must have one answer.

## Common mistakes

- **First match wins.** The result depends on rule order, so adding an allow at the top of the file silently overrides a deny further down. A change freeze written as a deny below `platform-admin` never fires.
- **Unanchored patterns.** `re.match` or `startswith` lets `customers:read` also grant `customers:read_pii`, and `acme` match `acme-staging`.
- **Missing attributes as `None`.** A service account with no tenant reading a resource with no tenant passes `resource.tenant == principal.tenant` because `None == None`. That's a cross-tenant read.
- **The most specific rule wins regardless of effect.** A team's narrow allow (`acme/reports/*`) punches a hole through the org-wide "no PII exports" deny. Some RBAC systems do work this way, but then a deny can never be a guardrail.

## Production notes

- AWS IAM, Cedar (Amazon Verified Permissions) and OPA/Rego are the references. Cedar is explicitly deny-overrides with default deny, and its evaluator treats an error in a policy's condition (such as a missing attribute) as "this policy doesn't apply", the same as here.
- Return the deciding policy id and log it with every decision. Auditors and incident reviews ask "why was this allowed?", and "because of rule 17" is the only good answer.
- Evaluate at the gateway in front of every tool call, not in the agent's prompt. The model can be talked out of a rule; the policy engine can't.
- At scale, index rules by action prefix and principal so each request evaluates a handful of candidates, compile globs once, and cache decisions for identical (principal, action, resource) tuples for a few seconds.
- Pairs with `tool-permission-scopes` (intersecting user and agent permissions) and `acl-aware-retrieval` (the same idea for documents).
