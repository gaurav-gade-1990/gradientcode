## Approach

A flag evaluation is a short decision list. Compute the bucket once, then walk the gates in a fixed order and stop at the first one that decides.

```python
bucket = stable_hash(f"{key}:{tenant}:{user_id}", 10000)
if killed:                      off, "killed"
elif tenants and tenant not in tenants: off, "tenant"
elif user_id in allow:          on,  "allowlist"
elif first matching rule:       rule["serve"], "rule:<id>"
else:                           bucket < rollout_bp, "rollout"
```

**Why does this make rollouts sticky?** The bucket depends only on the flag key, the tenant and the user, never on the percentage. Moving from 10% to 20% raises the threshold, so every user who was below 1000 is still below 2000. Nobody is flipped out, and the newly enabled users are a fresh, uniform slice.

**Why hash the flag key in?** If you hash only the user, user 7 is in the first 1% of *every* rollout. The same unlucky users test every risky feature, and their experience is correlated across experiments.

**Why the tenant?** User ids are only unique inside a tenant. Without the tenant, `acme/u_101` and `globex/u_101` share a bucket and an allowlist entry.

## Common mistakes

- **`hash()` instead of a stable hash.** Python salts string hashes per process. Two web servers put the same user in different buckets, so the feature flickers on every request that lands on another pod.
- **Hashing only the user id.** Correlated rollouts: the same users get every new feature first.
- **`<=` instead of `<`.** At `rollout_bp = 0` a user in bucket 0 still gets the feature, and the flag is never fully off.
- **The allowlist above the kill switch.** During an incident, on-call kills the flag and it stays on for every internal tester and design partner, often the people with the most data.

## Production notes

- LaunchDarkly, Unleash, Statsig and OpenFeature providers all use this scheme: a salted, stable hash of (flag, context key) into buckets, and a fixed rule order. LaunchDarkly hashes `flagKey.salt.contextKey` with SHA-1 into 100,000 buckets.
- The kill switch must not depend on the rest of the config. In production it is usually a separate, highly available path (a cached boolean that the SDK checks first) so that a broken rules payload can't block turning a feature off.
- Evaluate flags locally in the SDK from a streamed config, not with a network call per request. Log each evaluation (flag, variation, reason) so experiments can be analyzed and incidents explained.
- Pair this with `thompson-prompt-variants` for adaptive allocation and `canary-analysis` for deciding when to raise the percentage.
