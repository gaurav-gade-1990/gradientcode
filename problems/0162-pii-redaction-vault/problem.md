Support tickets flowing into your AI coworkers are full of customer emails, phone numbers, card numbers and SSNs. Before any text reaches a model or a log, the platform swaps each value for a token and keeps the original in a per-tenant vault. A few roles (a privacy officer, a fraud investigator) may turn tokens back into values, and every attempt is audited. Build the vault.

Implement `PiiVault(reidentify_roles)` with `redact(tenant, text)`, `reidentify(tenant, role, text)` and an `audit` list.

**Detection.** Run one pass per type, in this order, each over the output of the previous pass. Within a pass, replace the non-overlapping matches of `re.sub` / `re.finditer`, left to right.

| order | type | pattern | canonical value |
|---|---|---|---|
| 1 | `EMAIL` | `[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}` | lowercased |
| 2 | `CARD` | `(?<!\d)\d(?:[ -]?\d){12,18}(?!\d)` | digits only |
| 3 | `SSN` | `(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)` | digits only |
| 4 | `PHONE` | `(?<!\d)(?:\+1[ .-]?)?\(?\d{3}\)?[ .-]?\d{3}[ .-]\d{4}(?!\d)` | digits only, dropping a leading `1` when there are 11 digits |

A `CARD` match counts only if its digits pass the **Luhn check**: from the rightmost digit, double every second digit, subtract 9 from any result above 9, and require the sum of all digits to be divisible by 10. A match that fails Luhn (an order number, a tracking number) is left in the text unchanged. The starter defines these patterns for you.

**Tokens.** Replace each detected value with `[TYPE_n]`, for example `[EMAIL_1]`. The vault is **per tenant**: inside one tenant, the same `(type, canonical value)` always gets the same token, in every call. New values get the next number for that tenant and type, starting at 1, in the order they are replaced. The vault remembers the original text of the **first** occurrence of each token.

**`reidentify(tenant, role, text)`**

- If `role` isn't in `reidentify_roles`, append `{"tenant", "role", "allowed": False, "tokens": []}` to `audit`, then raise `PermissionError`.
- Otherwise replace every `[TYPE_n]` that exists in **this tenant's** vault with its stored original. Leave tokens the tenant doesn't have unchanged. Append `{"tenant", "role", "allowed": True, "tokens": [...]}`, listing each replaced token once, in order of first appearance in `text`. Return the new text.

The judge runs a sequence of calls (re-identifying earlier redacted outputs) and grades every returned string, every `PermissionError` and the full `audit` list.

**Constraints**

- At most 60 calls; each text is at most 500 characters.
- Don't use Python's `hash()` or randomness for tokens. They must be identical on every run.
