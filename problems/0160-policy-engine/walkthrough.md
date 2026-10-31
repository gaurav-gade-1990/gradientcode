## 1. What the problem is really asking

Every API call an AI coworker makes (a refund, a ticket export, a customer lookup) goes through one gate that answers *may this agent do this, and which rule says so?* That is what OPA, Cedar and AWS IAM do, and you are writing a small one.

Under the story there are two separate jobs, and keeping them separate is the whole design:

- **Matching.** For each rule, decide whether it applies: a principal glob matches one of the caller's identities, an action glob matches, a resource glob matches, and every attribute condition is true. That gives you a *set* of matching rules.
- **Combining.** Turn that set into one decision with a fixed algorithm, **deny-overrides with default deny**: any matching deny wins; else any matching allow wins; else deny with `no_match`. A specificity tuple then picks *which rule id to report* inside the winning effect.

The order of `rules` never decides allow versus deny. It only breaks exact specificity ties and orders the `matched` list. The judge compares all four fields per request: `decision`, `reason`, `rule` and `matched`.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `request["principal"]` | `{"id", "roles"?, "tenant"?, ...}` | identities are `id` plus `"role:" + r` |
| `request["action"]` | e.g. `"refunds:create"` | matched against `actions` globs |
| `request["resource"]` | `{"id", "tenant"?, "amount"?, ...}` | only `id` is matched by globs; the rest is for conditions |
| `request["context"]` | e.g. `{"mfa": True}` | conditions only |
| `rule["principals" / "actions" / "resources"]` | lists of globs | any pattern in the list may match |
| `rule["conditions"]` | optional list of `{"attr", "op", "value"}` | all must be true |

The details that are easy to miss:

- **Globs are anchored.** `customers:read` must not match `customers:read_pii`, and `*` is the only special character. A `.` in a resource id is a dot, not "any character".
- **Missing is not `None`.** `resolve` returns a sentinel when a path doesn't exist, and any condition that touches it is false, even `neq` and `not_in`.
- **`True` is not a number.** In Python `isinstance(True, int)` is true, but the spec says ordering ops need "int or float, not bool". An `amount` of `True` must not pass `lte 500`.
- **Specificity uses the best pattern in a rule.** A rule with resources `["acme/*", "acme/kb/*"]` scores 8 on `acme/kb/doc-1`, not 5, because the longest-literal pattern that *matched* counts.

## 3. Trace the examples by hand

The main rule set has nine rules. Example 3 is the one that teaches the most:

```
R(ANALYTICS, "customers:export", "acme/reports/q3-churn", contains_pii=True)
ANALYTICS = {"id": "agent:acme-analytics", "roles": ["analyst"], "tenant": "acme"}
```

Identities: `["agent:acme-analytics", "role:analyst"]`. Going through the rules:

| rule | principals | action | resource | conditions | match? | (R, A, C) |
|---|---|---|---|---|---|---|
| tenant-guard (deny) | `*` ok | `*` ok | `*` ok | `acme != acme` is false | no | |
| platform-admin | needs `role:platform-admin` | | | | no | |
| no-pii-export (deny) | `agent:*` ok | `customers:export` ok | `*` ok | `contains_pii == True` | **yes** | (0, 16, 1) |
| acme-analytics-export (allow) | exact id ok | ok | `acme/reports/*` ok | none | **yes** | (13, 16, 0) |
| the others | wrong role, action or resource | | | | no | |

`matched` is `['no-pii-export', 'acme-analytics-export']`. The allow is far more specific (13 literal resource characters against 0), but there is a deny in the set, so the decision is `deny`, reason `explicit_deny`, rule `no-pii-export`. The team's narrow allow can't punch a hole in the org-wide PII guardrail.

**Example 2, request 2.** The billing bot asks to refund 900 on `acme/orders/O-1182` with an empty context. `refund-small` needs `amount lte 500`, which is false. `refund-large-approved` needs `amount gt 500` (true) and `context.approved_by in [...]`, but `approved_by` is missing, so that condition is false. Nothing matches: `{"decision": "deny", "reason": "no_match", "rule": None, "matched": []}`. Default deny does the work without anyone writing a "deny large refunds" rule.

**The trickiest hidden case, "admin during a change freeze".** `ADMIN` has the roles `platform-admin` and `support-agent`.

| request | matching rules (R, A, C) | result |
|---|---|---|
| refunds:create, `change_freeze: True` | platform-admin (0, 0, 0), billing-freeze (5, 8, 1) | deny, `billing-freeze` |
| refunds:create, no freeze | platform-admin (0, 0, 0) | allow, `platform-admin` |
| tickets:update on a ticket | platform-admin (0, 0, 0), support-read (9, 14, 1) | allow, `support-read` |

Row 1 shows that a deny below a catch-all admin allow still fires. Row 3 shows specificity at work: both are allows, and `*/tickets/*` (9 literals) beats `*` (0), so the audit log names `support-read`.

## 4. Key idea: a missing attribute makes the condition false

The `tenant-guard` deny says "deny if `resource.tenant != principal.tenant`", and `support-read` requires `resource.tenant == principal.tenant`. Now take a service account with no tenant, `svc:nightly-sync`, reading `shared/tickets/T-1`, a resource with no tenant either.

If missing paths resolve to `None`, then `None == None` is true and `support-read` **allows** a read that no tenant owns. That is the cross-tenant hole the "missing tenants are not equal" case checks for. With a `MISSING` sentinel, both conditions are false, nothing matches, and the result is `no_match`.

The same rule changes `not_in`. The `ticket-writer` rule requires `context.channel not_in ["sms"]`. With a channel of `email` it is allowed, with `sms` it isn't, and with **no channel at all** it must not be allowed either: you can't prove the request didn't come over SMS. With `None`, `None not in ["sms"]` is true, and the third request in "glob principals and not_in" is wrongly allowed.

## 5. Key idea: specificity only names the rule, it never flips the effect

There are two tempting combining algorithms, and both are wrong here:

| algorithm | what goes wrong |
|---|---|
| first match wins | adding a broad allow at the top silently overrides every deny below it; the admin freezes nothing |
| most specific rule wins, whatever its effect | a narrow team allow overrides an org-wide deny (Example 3 becomes `allow`) |
| **deny-overrides, then specificity inside the effect** | denies are real guardrails, and the reported rule is still deterministic |

The tie-break makes the report stable. The tuple is compared largest first, so `min` over `(-R, -A, -C, index)` picks the right one. In "specificity tie-breaks", request 2 matches `broad`, `two-patterns` and `same-as-broad`, all at (5, 3, 0), and the earliest, `broad`, is reported. Request 4 matches `deny-a` (0, 9, 0) and `deny-b` (8, 3, 0). `R` is compared first, so `deny-b` wins even though `deny-a` has more action literals.

## 6. Plan before you code

```
glob_match(p, s): escape every char, * -> .*, fullmatch
resolve(req, "a.b.c"): walk dicts, return MISSING on any miss
condition_holds: resolve both sides; MISSING -> False; then the op table

match(rule, req) -> (R, A, C) or None:
    principal glob vs id and role:<r>
    A = best literal count over matching action patterns
    R = best literal count over matching resource patterns
    all conditions true

decide(rules, req):
    hits = [(spec, index, rule)] for matching rules
    pool = denies if any else allows
    empty pool -> deny / no_match
    report min(pool) by (-R, -A, -C, index)
```

## 7. Build it one piece at a time

**Step 1: globs.** Build the regex character by character, so every literal is escaped and only `*` becomes `.*`. Use `fullmatch`.

```python
def glob_match(pattern, s):
    regex = "".join(".*" if ch == "*" else re.escape(ch) for ch in pattern)
    return re.fullmatch(regex, s, flags=re.S) is not None
```

`re.match` anchors only the start, so `customers:read` would match `customers:read_pii`. That is the first request of "suffix must match too", which must be `no_match`.

**Step 2: attribute paths and the sentinel.** `MISSING = object()` is a value nothing in the request can equal.

```python
def resolve(request, path):
    cur = request
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return MISSING
        cur = cur[part]
    return cur
```

The `isinstance(cur, dict)` test handles paths that go through a non-dict, like `resource.amount.currency` when `amount` is a number.

**Step 3: conditions.** Resolve the right side if it is `{"attr": ...}`, return `False` if either side is missing, then dispatch on the op. Ordering ops call `is_number` on both sides, which rejects bools and strings. In "refund boundaries and types", an amount of `"120"` and an amount of `True` both end as `no_match`. Without the bool check, `True <= 500` is true and the refund goes through.

**Step 4: specificity and the decision.** `best_literal` returns the max literal count over the patterns that matched, or `None`. In "best pattern inside a rule", `two-patterns` scores (8, 9, 0) on `kb:search acme/kb/doc-1` because both its narrower patterns match. It beats `conditional` at (8, 3, 1): `R` ties, and `A` decides before `C` is looked at.

```python
pool, decision, reason = (denies, "deny", "explicit_deny") if denies else (allows, "allow", "allowed")
if not pool:
    return {"decision": "deny", "reason": "no_match", "rule": None, "matched": matched}
best = min(pool, key=lambda h: (tuple(-x for x in h[0]), h[1]))
```

## 8. Full solution

Every line carries a comment saying what it does and why.

```python
# re builds an anchored regex from each glob.
import re

# A unique marker for "this attribute path doesn't exist", distinct from a real None in the request.
MISSING = object()


# Does the glob match the WHOLE string? `*` is any run of characters, everything else is literal.
def glob_match(pattern, s):
    # Escape every literal character and turn each * into .* so nothing else is special.
    regex = "".join(".*" if ch == "*" else re.escape(ch) for ch in pattern)
    # fullmatch anchors both ends; re.S lets .* cross newlines too.
    return re.fullmatch(regex, s, flags=re.S) is not None


# Specificity of one pattern: how many characters it pins down.
def literals(pattern):
    return sum(1 for ch in pattern if ch != "*")  # every non-* character counts once


# Follow a dotted path like "resource.tenant" into the request, or return MISSING.
def resolve(request, path):
    # Start at the root of the request.
    cur = request
    # Walk one key at a time.
    for part in path.split("."):
        # Not a dict, or no such key: the attribute is missing, not None.
        if not isinstance(cur, dict) or part not in cur:
            return MISSING  # the caller will make the condition false
        cur = cur[part]  # step down a level
    # The value at the end of the path.
    return cur


# Ordering ops only compare real numbers; True is an int in Python but not a number here.
def is_number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)  # exclude bool explicitly


# Evaluate one condition against the request.
def condition_holds(request, cond):
    # The left side is always an attribute path.
    left = resolve(request, cond["attr"])
    # The right side is a literal...
    right = cond["value"]
    # ...or another attribute, written as {"attr": path}.
    if isinstance(right, dict) and "attr" in right:
        right = resolve(request, right["attr"])  # compare attribute to attribute
    # A missing side makes the condition false for every op, so missing == missing never grants access.
    if left is MISSING or right is MISSING:
        return False  # fail closed on missing data
    # Which comparison to run.
    op = cond["op"]
    # Plain equality.
    if op == "eq":
        return left == right  # true when equal
    # Plain inequality (only reached when both sides exist).
    if op == "neq":
        return left != right  # true when different
    # Membership tests need a list on the right.
    if op in ("in", "not_in"):
        # Anything but a list can't be searched, so the condition fails.
        if not isinstance(right, list):
            return False  # malformed membership test: fail closed
        # in wants membership, not_in wants its absence.
        return (left in right) == (op == "in")
    # Ordering comparisons.
    if op in ("lt", "lte", "gt", "gte"):
        # Strings and bools never compare: "120" or True as an amount fails the rule.
        if not (is_number(left) and is_number(right)):
            return False  # not comparable as numbers
        # Run the requested comparison.
        return {"lt": left < right, "lte": left <= right, "gt": left > right, "gte": left >= right}[op]
    # An unknown op never grants anything.
    return False


# The literal count of the most specific pattern in `patterns` that matches s, or None if none match.
def best_literal(patterns, s):
    # Score every pattern that matches.
    hits = [literals(p) for p in patterns if glob_match(p, s)]
    # The rule is as specific as its best matching pattern.
    return max(hits) if hits else None


# Return the specificity tuple (R, A, C) if the rule matches, else None.
def match(rule, request):
    # The principal, for its id and roles.
    p = request["principal"]
    # Identities: the id plus "role:<r>" per role; roles may be absent.
    identities = [p["id"]] + ["role:" + r for r in p.get("roles") or []]
    # Some principal pattern must match some identity.
    if not any(glob_match(pat, ident) for pat in rule["principals"] for ident in identities):
        return None  # this rule is not about this caller
    # Best action pattern and best resource pattern (None means no pattern matched).
    a = best_literal(rule["actions"], request["action"])
    r = best_literal(rule["resources"], request["resource"]["id"])  # matched against the resource id
    # Both must match.
    if a is None or r is None:
        return None  # wrong action or wrong resource
    # Conditions may be absent.
    conds = rule.get("conditions") or []
    # Every condition must hold.
    if not all(condition_holds(request, c) for c in conds):
        return None  # one false condition and the rule doesn't apply
    # Resource literals first, then action literals, then the condition count.
    return (r, a, len(conds))


# Decide one request: collect every match, then combine with deny-overrides.
def decide(rules, request):
    # (specificity, position, rule) for every matching rule.
    hits = []
    # Check every rule; order only matters for ties and the matched list.
    for i, rule in enumerate(rules):
        spec = match(rule, request)  # None when the rule doesn't apply
        # Keep the matches with their position for tie-breaks.
        if spec is not None:
            hits.append((spec, i, rule))  # i breaks specificity ties
    # Every matching id, in rules order, for the audit trail.
    matched = [rule["id"] for _, _, rule in hits]
    # Split the matches by effect.
    denies = [h for h in hits if h[2]["effect"] == "deny"]
    allows = [h for h in hits if h[2]["effect"] == "allow"]  # only used when there are no denies
    # Any deny wins outright; specificity only picks which rule id to report inside the winning effect.
    pool, decision, reason = (denies, "deny", "explicit_deny") if denies else (allows, "allow", "allowed")
    # Nothing matched at all: default deny.
    if not pool:
        return {"decision": "deny", "reason": "no_match", "rule": None, "matched": matched}  # no rule decided
    # Largest (R, A, C) first, then the earliest rule: negate the tuple so min picks the largest.
    best = min(pool, key=lambda h: (tuple(-x for x in h[0]), h[1]))
    # Report the decision and the one rule that decided it.
    return {"decision": decision, "reason": reason, "rule": best[2]["id"], "matched": matched}


# One decision per request, in order.
def evaluate(rules, requests):
    return [decide(rules, req) for req in requests]  # each request is independent
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | allow, `support-read` | a plain match; `tenant-guard`'s `neq` is false in the same tenant |
| Example 2 | deny `tenant-guard`; then deny `no_match` | the tenant guard, and default deny when conditions fail |
| Example 3 | deny `no-pii-export`, both rules matched | deny beats a more specific allow |
| suffix must match too | `customers:read_pii` is `no_match`; `customers:read` is allowed | anchored globs |
| missing tenants are not equal | both requests `no_match` | missing attributes make conditions false |
| admin during a change freeze | deny `billing-freeze`; allow `platform-admin`; allow `support-read` | deny-overrides, and specificity among allows |
| refund boundaries and types | 500 allowed, 500.5 denied, 501 with Dana allowed, string, bool and missing amounts `no_match` | `lte`/`gt` boundaries, `in`, and the number check |
| glob principals and not_in | email allowed; sms, missing channel and `agent:triage` all `no_match` | `agent:triage-*`, `not_in`, a missing attribute |
| specificity tie-breaks | `deny-b`, `broad`, `conditional`, `deny-b`, `deny-a` | R before A before C, then rule order |
| best pattern inside a rule | `two-patterns`, `conditional`, `two-patterns` | the best matching pattern inside one rule counts |
| no rules | deny `no_match`, `matched: []` | the empty pool |
| mixed traffic | 120 random requests over the main rules | everything together |

## 10. Complexity

For each request you test every rule: O(|rules| · (p·i + a + r) · L) for the glob matches, where `p`, `a` and `r` are the pattern counts, `i` the identity count and `L` the string length, plus O(conditions · path depth) for conditions. At 100 rules and 200 requests that is fast. Building the regex inside `glob_match` on every call is the main waste; compile each pattern once with `functools.lru_cache` or at rule-load time.

At gateway scale (thousands of decisions a second), you would index rules by action prefix and by principal so each request evaluates only a handful of candidates, keep compiled regexes, and cache decisions for identical `(principal, action, resource, context)` tuples for a few seconds. The decision must stay a pure function of the request and the rules, which is what makes caching and replaying for an audit safe.

## 11. If you got Wrong Answer

- **"admin during a change freeze" request 1 is `allow` by `platform-admin`.** You let the first matching rule decide. Collect all matches, then combine.
- **Example 3 is `allow` by `acme-analytics-export`.** You picked the most specific rule regardless of effect. Any deny must win.
- **"missing tenants are not equal" request 1 is `allow` by `support-read`, and request 2 is `deny` by `tenant-guard`.** Missing paths resolve to `None`. Use a sentinel and make the condition false.
- **"glob principals and not_in" request 3 (no channel) is allowed.** Same bug: `None not in ["sms"]` is true.
- **"suffix must match too" allows `customers:read_pii`.** You used `re.match`, `startswith` or `search`. Use `fullmatch`.
- **"refund boundaries and types" allows the `amount=True` request.** `is_number` must exclude `bool`.
- **"best pattern inside a rule" reports `broad`, not `two-patterns`.** Either you took the first matching rule, or you scored a rule by its first pattern instead of its best matching one.

## 12. Follow-ups an interviewer might ask

- *Why deny-overrides rather than first-match?* It makes a deny a real guardrail: no allow anywhere in the file, however specific, can override "no PII exports" or "change freeze". Cedar and AWS IAM both work this way, with default deny.
- *Why return the deciding rule at all?* Audits and incident reviews ask "which rule let the billing bot refund $2,500?". It needs one deterministic answer, logged with every decision (problem 161, hash-chained-audit-log, for a tamper-evident log).
- *Should this run inside the agent's prompt?* No. Evaluate at the gateway in front of every tool call. A model can be talked out of a rule written in its prompt; the policy engine can't be.
- *How does this combine with user permissions?* An agent acting for a user should get the intersection of what the agent's role and the user allow (problem 117, tool-permission-scopes). Filtering retrieved documents by ACL is the same idea for reads (problem 155, acl-aware-retrieval).
- *What about a condition that errors, like a type mismatch?* Here it is false, so the rule doesn't apply. Cedar does the same. For a deny rule this fails open, so production engines also lint policies and alert when a deny's conditions keep erroring.
