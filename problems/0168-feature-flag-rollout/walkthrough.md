## 1. What the problem is really asking

Take away the product story and this is a **decision list with a deterministic hash at the bottom**. For each (flag, user) pair you walk five gates in a fixed order and stop at the first one that decides. Only if none of the first four decide does the percentage matter, and then the answer is a single comparison: `bucket < rollout_bp`.

The interesting part is "sticky". A user who is on at 10% must still be on at 20%, on every server, after every restart. That works only if the user's bucket never changes. So the bucket has to be:

- **deterministic across processes**, which rules out Python's `hash()`;
- **independent of the percentage**, so raising the threshold only adds users;
- **specific to the flag and the tenant**, so different flags pick different users and `acme/u_101` is not `globex/u_101`.

The judge compares your whole list of result dicts exactly (`rtol` and `atol` are 0). That includes `bucket` on every row, even rows decided by the kill switch or the tenant gate. A wrong hash fails every single case, because every row reports its bucket.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `flags` | list of flag dicts, in output order | outer loop |
| `users` | list of `{"id", "tenant", "attrs"}`, in output order | inner loop |
| `flag["killed"]` | the kill switch, may be missing | gate 1 |
| `flag["tenants"]` | allowed tenants, may be missing or empty | gate 2, only when non-empty |
| `flag["allow"]` | user ids that always get it, may be missing | gate 3 |
| `flag["rules"]` | `{"id", "attr", "op", "value", "serve"}` in priority order, may be missing | gate 4, first match wins |
| `flag["rollout_bp"]` | 0 to 10000 basis points | gate 5, `bucket < rollout_bp` |
| `stable_hash(s, mod)` | sha256 of `str(s)`, as an int, mod `mod` | the bucket |

Three details are easy to miss:

- **Missing keys.** Most hidden flags have only `key` and `rollout_bp`. `flag["tenants"]` raises `KeyError`; use `flag.get("tenants") or []`.
- **The bucket is computed for every row**, whatever gate decides. Compute it first, before any `if`.
- **Order of the output.** Flag first, then user: `[evaluate(f, u) for f in flags for u in users]`. Swapping the two `for` clauses gives the right rows in the wrong order.

## 3. Trace the examples by hand

**Example 1** is one flag at `rollout_bp = 3000`, no other gates. Only gate 5 can decide:

| user | tenant | hashed string | bucket | `bucket < 3000` | result |
|---|---|---|---|---|---|
| `u_101` | acme | `agent-autopilot:acme:u_101` | 2090 | yes | on, `rollout` |
| `u_102` | acme | `agent-autopilot:acme:u_102` | 9165 | no | off, `rollout` |
| `u_101` | globex | `agent-autopilot:globex:u_101` | 6825 | no | off, `rollout` |

The two `u_101` rows land 4735 buckets apart. They are different people, and the tenant in the hashed string is what makes them different.

**Example 2** exercises every gate except the kill switch. The flag is `ticket-summaries-v2` with `tenants=["acme"]`, `allow=["u_102"]`, rules `admins` (role eq admin, serve on) then `no-eu` (region eq eu, serve off), and `rollout_bp = 0`.

| user | gate 2 tenant | gate 3 allow | gate 4 first matching rule | result | bucket |
|---|---|---|---|---|---|
| `u_102` acme, analyst | pass | **in allow** | not reached | on, `allowlist` | 8741 |
| `u_103` acme, admin, eu | pass | no | **`admins`** (also matches `no-eu`, but later) | on, `rule:admins` | 5612 |
| `u_104` acme, analyst, eu | pass | no | `admins` no, **`no-eu`** yes | off, `rule:no-eu` | 4506 |
| `u_105` globex, admin | **fails** | not reached | not reached | off, `tenant` | 4823 |

Two lessons. `u_103` matches both rules and the first one in list order wins. `u_105` is an admin, but the tenant gate comes first, so the admin rule never gets a say. Every row still carries its bucket.

**The trickiest hidden case is "tenant gate before allowlist".** The flag allows `u_101` and `u_103` in tenant `acme` only, at 100%. The users are `u_101..u_103` at acme and the *same ids* at globex. Expected: acme's `u_101` and `u_103` are on with `allowlist`, acme's `u_102` is on with `rollout` (bucket 8194 is under 10000), and all three globex users are off with `tenant`. The allowlist holds bare ids, so `"u_101" in allow` is true for globex's `u_101` too. Only the gate order stops a different company's user from getting the feature.

## 4. Key idea: the bucket depends on everything except the percentage

The formula is `stable_hash(key + ":" + tenant + ":" + id) % 10000`. Look at what is *not* in it: `rollout_bp`. Raising the rollout from 2090 to 2091 doesn't move anyone's bucket. It only moves the line. The hidden case "bucket exactly at threshold" shows this for acme's `u_101`, whose bucket is 2090:

| `rollout_bp` | `2090 < rollout_bp` | on |
|---|---|---|
| 2090 | no | off |
| 2091 | yes | on |

That's the strict `<` at work. With `rollout_bp = 2090` exactly 2090 buckets (0 through 2089) are on, which is 20.90% of 10000. With `<=` you'd get 2091 buckets, and `rollout_bp = 0` would still turn on anyone in bucket 0.

Stickiness follows directly. In "ramp is monotonic" the same 16 users go through 500, 1000, 2500, 5000 and 9000 bp, and the count of users on is 1, 1, 6, 10 and 15. Each set contains the previous one, because a bucket under 1000 is also under 2500.

Why the flag key is in the string: in "two flags pick different users", both flags are at 3000 for the same 8 acme users. `agent-autopilot` turns on `u_101`, `u_103`, `u_105`; `ticket-summaries-v2` turns on `u_106`, `u_108`. Without the key, both flags would pick the same people, and the same unlucky users would test every risky feature.

## 5. Plan before you code

```
for each flag, for each user:
    bucket = stable_hash(f"{key}:{tenant}:{id}", 10000)      # always
    if killed:                                  off, "killed"
    elif tenants and tenant not in tenants:     off, "tenant"
    elif id in allow:                           on,  "allowlist"
    elif first rule r that matches attrs:       r.serve, "rule:" + r.id
    else:                                       bucket < rollout_bp, "rollout"
    emit {flag, user, tenant, on, reason, bucket}
```

The rule-matching decision table:

| `attr in attrs`? | `op` | matches when |
|---|---|---|
| no | any | never |
| yes | `eq` | `attrs[attr] == value` |
| yes | `in` | `attrs[attr] in value` |

## 6. Build it one piece at a time

**Step 1: the bucket and the output row.** Get this right first, since every row depends on it.

```python
from gc_runtime import stable_hash

def _evaluate(flag, user):
    key = flag["key"]
    bucket = stable_hash("%s:%s:%s" % (key, user["tenant"], user["id"]), 10000)
    ...
    return {"flag": key, "user": user["id"], "tenant": user["tenant"],
            "on": on, "reason": reason, "bucket": bucket}
```

Passing `10000` as `mod` is the same as `% 10000`. Don't reach for `hash()`: it's salted per process, so the judge's process and yours disagree, and so would two of your web servers.

**Step 2: rule matching, with the missing-attribute check first.**

```python
def _rule_matches(rule, attrs):
    if rule["attr"] not in attrs:
        return False
    v = attrs[rule["attr"]]
    if rule["op"] == "eq":
        return v == rule["value"]
    if rule["op"] == "in":
        return v in rule["value"]
    return False
```

Checking membership first means `attrs.get(attr) == value` can't accidentally match a rule whose `value` is `None`. In "rule order and missing attrs", `u_0003` has no `region`, so `eu-off` and `apac-on` are skipped and `staff` decides.

**Step 3: the gates as one `if/elif` chain.**

```python
    tenants = flag.get("tenants") or []
    if flag.get("killed"):
        on, reason = False, "killed"
    elif tenants and user["tenant"] not in tenants:
        on, reason = False, "tenant"
    elif user["id"] in (flag.get("allow") or []):
        on, reason = True, "allowlist"
    else:
        hit = next((r for r in flag.get("rules") or []
                    if _rule_matches(r, user.get("attrs") or {})), None)
        if hit is not None:
            on, reason = bool(hit["serve"]), "rule:" + hit["id"]
        else:
            on, reason = bucket < flag.get("rollout_bp", 0), "rollout"
```

An `elif` chain makes "first gate that decides wins" structural. `next(..., None)` returns the first matching rule and stops scanning. `tenants and ...` keeps an empty or missing list from blocking everybody.

**Step 4: the ordering.** Flag is the outer loop:

```python
def evaluate_flags(flags, users):
    return [_evaluate(f, u) for f in flags for u in users]
```

## 7. Full solution

```python
from gc_runtime import stable_hash  # sha256-based, so every process and server agrees on a bucket


def _rule_matches(rule, attrs):  # does one targeting rule apply to this user's attributes?
    if rule["attr"] not in attrs:  # a missing attribute never matches, whatever the value
        return False  # skip this rule and let the next one try
    v = attrs[rule["attr"]]  # the user's value for the attribute the rule looks at
    if rule["op"] == "eq":  # exact-value rule
        return v == rule["value"]  # matches only on an equal value
    if rule["op"] == "in":  # list-membership rule
        return v in rule["value"]  # matches when the value is one of the listed ones
    return False  # an unknown operator never matches, so it can't turn a feature on by accident


def _evaluate(flag, user):  # one result row for one (flag, user) pair
    key = flag["key"]  # the flag name goes into the hash and the output
    # flag key + tenant + user id: sticky per user, different per flag, distinct across tenants
    bucket = stable_hash("%s:%s:%s" % (key, user["tenant"], user["id"]), 10000)
    tenants = flag.get("tenants") or []  # a missing tenants list means "no tenant restriction"
    if flag.get("killed"):  # gate 1: the kill switch beats everything
        on, reason = False, "killed"  # off, whatever the allowlist or rules say
    elif tenants and user["tenant"] not in tenants:  # gate 2: only listed tenants may get it
        on, reason = False, "tenant"  # off, before the allowlist can match a same-named user elsewhere
    elif user["id"] in (flag.get("allow") or []):  # gate 3: explicit testers and design partners
        on, reason = True, "allowlist"  # always on for them
    else:  # no gate decided yet, so try rules, then the percentage
        # gate 4: the first rule in list order that matches decides
        hit = next((r for r in flag.get("rules") or [] if _rule_matches(r, user.get("attrs") or {})), None)
        if hit is not None:  # a rule matched
            on, reason = bool(hit["serve"]), "rule:" + hit["id"]  # serve what the rule says, and name it
        else:  # gate 5: nothing targeted this user, so the rollout percentage decides
            on, reason = bucket < flag.get("rollout_bp", 0), "rollout"  # strict <, so 0 bp is fully off
    # every row reports its bucket, whichever gate decided
    return {"flag": key, "user": user["id"], "tenant": user["tenant"], "on": on, "reason": reason, "bucket": bucket}


def evaluate_flags(flags, users):  # the entry point the flag service calls
    return [_evaluate(f, u) for f in flags for u in users]  # flag is the outer loop, so rows group by flag
```

## 8. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | acme `u_101` on (2090), `u_102` off (9165), globex `u_101` off (6825) | the hash string includes the tenant |
| Example 2 | `allowlist`, `rule:admins`, `rule:no-eu`, `tenant` | every gate but the kill switch, and first-rule-wins |
| Example 3, kill switch over allowlist and rules | every row off with `killed` | gate 1 beats the allowlist, rules and a 100% rollout |
| bucket exactly at threshold | off at 2090, on at 2091 | strict `<` |
| bucket 0 at rollout 0 | acme `u_21036` (bucket 0) off at 0, on at 1 | strict `<` at the bottom: 0% is really off |
| rollout 0 and 100 | all 16 off, then all 16 on | the two extremes |
| ramp is monotonic | 1, 1, 6, 10, 15 of 16 on | the bucket ignores `rollout_bp`, so rollouts are sticky |
| two flags pick different users | `u_101,u_103,u_105` vs `u_106,u_108` | the flag key is in the hash |
| tenant gate before allowlist | globex `u_101`, `u_103` off with `tenant` | gate 2 before gate 3 |
| rule order and missing attrs | 10 `staff`, 8 `eu-off`, 5 `apac-on`, 7 `rollout` | list order, `in` operator, missing `region` |
| many users two tenants | 160 rows; 9 on for `agent-autopilot` (`u_0075` at both acme and globex by `allowlist`), 66 on for `workflow-builder` | output order across 2 flags and 80 users, the allowlist in two tenants, flags with missing keys |

## 9. Complexity

Each (flag, user) pair costs one sha256 of a short string plus a scan of the rules, so the total is O(F · U · R) with F flags, U users and R rules per flag. At the limits (20 × 200) that's 4,000 hashes, a few milliseconds.

In production this runs inside the SDK on every request, so the per-evaluation cost matters more than the total. Real SDKs keep the config in memory, hash once per (flag, context), and check the kill switch first from a cached boolean so a broken rules payload can never block turning a feature off. Turning `allow` and `tenants` into sets makes those gates O(1) when the lists are long.

## 10. If you got Wrong Answer

Look at the first row that differs and compare `bucket` first, then `reason`.

- **Every case fails, and every `bucket` differs.** You used `hash()`, or hashed only the user id (`wrong_python_hash.py`, `wrong_hash_ignores_flag_and_tenant.py` both fail all 12 cases). The string must be exactly `key:tenant:id`.
- **Only "bucket exactly at threshold" and "bucket 0 at rollout 0" fail, with the 2090 row on and the bucket-0 user on at 0%.** You wrote `bucket <= rollout_bp` (`wrong_bucket_off_by_one.py`).
- **Example 3 shows `allowlist` instead of `killed`.** Your allowlist check runs before the kill switch (`wrong_allowlist_beats_kill_switch.py`). The same bug also fails "kill switch over allowlist and rules" and "tenant gate before allowlist".
- **globex users show `allowlist`.** The tenant gate must come before the allowlist.
- **`u_103` in Example 2 shows `rule:no-eu`.** You're taking the last matching rule, or a rule with `serve: False` is overriding an earlier `True`. Stop at the first match.
- **Runtime Error `KeyError: 'tenants'`.** Use `.get(...) or []` for the optional keys.
- **Right rows, wrong order.** Flags are the outer loop.

## 11. Follow-ups an interviewer might ask

- *How do you run an A/B test with three variants instead of on/off?* Split the 10000 buckets into ranges (0–3332 control, 3333–6665 A, 6666–9999 B) and return the variant whose range holds the bucket. Keep the ranges fixed when you change weights, or users jump variants.
- *How do you re-randomize a flag that has bad luck?* Add a salt to the hashed string (`key:salt:tenant:id`). LaunchDarkly hashes `flagKey.salt.contextKey` with SHA-1 into 100,000 buckets. Changing the salt reshuffles everyone, so do it only before the rollout starts.
- *How would you shift traffic toward the better variant automatically?* That's a bandit, not a fixed split. See problem `thompson-prompt-variants`.
- *Who decides when to go from 10% to 20%?* A canary check comparing error rates and latency between the on and off groups. See problem `canary-analysis`.
- *What should the SDK log?* Every evaluation as (flag, user, variation, reason). The `reason` field is what lets you explain an incident ("they were on because of `rule:admins`, not the rollout").
