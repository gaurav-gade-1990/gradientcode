Your agent platform ships new AI-coworker features behind flags. Product wants sticky percentage rollouts: a user who gets a feature at 10% must still have it at 20%, on every server, after every deploy. Write the evaluator the flag service calls.

`evaluate_flags(flags, users)` evaluates every flag for every user and returns a list of results, ordered by flag first (in `flags` order) and then by user (in `users` order).

A **flag** is a dict:

| key | meaning |
|---|---|
| `key` | flag name, e.g. `"agent-autopilot"` |
| `killed` | bool. The kill switch |
| `tenants` | list of tenant ids. If it is present and non-empty, only these tenants can get the flag |
| `allow` | list of user ids that always get the flag |
| `rules` | list of `{"id", "attr", "op", "value", "serve"}` targeting rules |
| `rollout_bp` | rollout in basis points, `0..10000` (2500 means 25%) |

`tenants`, `allow` and `rules` may be missing; treat a missing one as empty. A **user** is `{"id", "tenant", "attrs"}`. User ids are only unique inside a tenant, so `u_101` at `acme` and `u_101` at `globex` are different people.

Compute the user's bucket for every flag, whatever decides the result:

$$
\text{bucket} = \texttt{stable\_hash}(\text{key} + \texttt{":"} + \text{tenant} + \texttt{":"} + \text{user id}) \bmod 10000
$$

using `stable_hash` from `gc_runtime`. Then apply these gates in order. The first one that decides wins:

| # | gate | result | `reason` |
|---|---|---|---|
| 1 | `killed` is true | off | `"killed"` |
| 2 | `tenants` is non-empty and the user's tenant isn't in it | off | `"tenant"` |
| 3 | the user's id is in `allow` | on | `"allowlist"` |
| 4 | the first rule (in list order) that matches | `serve` | `"rule:" + rule id` |
| 5 | otherwise | on iff `bucket < rollout_bp` | `"rollout"` |

A rule matches when `attr` is a key of the user's `attrs` and:
- `op == "eq"`: `attrs[attr] == value`
- `op == "in"`: `attrs[attr]` is in the list `value`

A missing attribute never matches. The allowlist applies only to users in an allowed tenant, which gate 2 already guarantees.

Each result is `{"flag": key, "user": user id, "tenant": tenant, "on": bool, "reason": str, "bucket": int}`.

**Constraints**

- `1 <= len(flags) <= 20`, `1 <= len(users) <= 200`
- `0 <= rollout_bp <= 10000`
- Don't use Python's built-in `hash()`. It is randomized per process, so two servers would disagree.
