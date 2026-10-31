## Approach

Shadow analysis is a classification problem with one subtle part: deciding what "the same answer" means. The rule table runs from the strictest test to the loosest, and the first match wins.

```python
def _classify(rec, policy):
    if rec.get("shadow_error") is not None:
        return "shadow_error"
    p, s = rec["primary"], rec["shadow"]
    if json.dumps(p, sort_keys=True) == json.dumps(s, sort_keys=True):
        return "exact"
    if isinstance(p, str) and isinstance(s, str) and _norm(p) == _norm(s):
        return "normalized"
    if _is_number(p) and _is_number(s) and abs(p - s) <= policy["abs_tol"] + policy["rel_tol"] * abs(p):
        return "numeric"
    return "mismatch"
```

Canonical JSON makes dict key order irrelevant, but keeps types: `1` and `1.0` serialize differently, as do `true` and `1`. That matters because downstream consumers (a router keyed on an int, a strict schema) often break on exactly that change.

Then summarize per group with `compared = total - shadow_error`, and apply the three blocking rules.

## Common mistakes

- **Python `==` as exact match.** `True == 1` and `1 == 1.0`. A shadow that returns `1` where primary returned `true` looks identical, until a TypeScript client branches on the type.
- **`isinstance(x, int)` accepts `bool`.** Exclude bools explicitly before the numeric rule.
- **Shadow errors as mismatches.** Shadow clusters are often under-provisioned. Count their errors separately, or you'll block a good model because of capacity.
- **Small segments blocking.** One wrong answer in a 2-request pilot segment is 50% disagreement. `min_segment` keeps noise from making the decision.
- **Absolute tolerance only.** One cent on a $12,400 total is float noise. Combine absolute and relative tolerance, as `math.isclose` does.

## Production notes

- Traffic mirroring is usually done at the proxy: Envoy `request_mirror_policies`, Istio `mirror`, or a Kafka tap feeding a shadow consumer. Mirrored calls must never have side effects, so strip write tools from a shadow agent, or point them at a sandbox.
- For LLM outputs, exact and normalized matching only works for structured fields (intents, extracted amounts, tool choices). For free text, add an embedding-similarity or LLM-judge class, and sample mismatches for human review.
- Report mismatches with the inputs attached, and bucket them by type (type change, rounding, real disagreement). Teams fix the first two in serialization and only argue about the third.
- Pairs with `canary-analysis`. Shadow tells you whether the outputs agree, and the canary tells you whether real users are fine with the new outputs.
