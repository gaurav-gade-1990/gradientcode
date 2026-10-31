## Approach

Redaction is a pipeline of typed passes over the text, and the vault is a pair of per-tenant maps.

```python
self.tokens    = {}  # (tenant, type, canonical) -> "[TYPE_n]"
self.originals = {}  # (tenant, token) -> first original text
self.counts    = {}  # (tenant, type) -> last n used
```

Each pass is a `re.sub` with a callback. The callback canonicalizes the match, looks it up (or mints the next number) and returns the token. For `CARD` it first runs Luhn and returns the match unchanged if it fails.

**Why this order?** Emails go first because they can contain digit runs. Cards go before SSNs and phones because a 16-digit card has 10-digit substrings that look like phones. Once a span is a token it has no long digit runs left, so later passes can't break it.

**Why canonicalize?** `Dana@Acme.com` and `dana@acme.com` are the same person, and `(512) 555-0100` is `+1 512 555 0100`. Stable pseudonyms let analytics, dedup and the model itself ("the same customer wrote twice") work on redacted text.

**Re-identification** checks the role before touching the vault, audits denials as well as successes, and resolves tokens only in the caller's tenant.

## Common mistakes

- **No Luhn check.** Every order id, tracking number and invoice number with 13+ digits gets redacted. Support agents can no longer look orders up, and people disable the redactor.
- **One vault for all tenants.** `[EMAIL_1]` from acme re-identifies to a globex customer's email. Tokens are only meaningful inside the tenant that minted them.
- **Case-sensitive email keys.** The same customer gets two tokens, so "has this customer contacted us before?" quietly breaks.
- **Not auditing denied attempts.** Repeated denied re-identification attempts are exactly what a privacy team needs to see. An audit that logs only successes hides the probing.

## Production notes

- Microsoft Presidio, Google Cloud DLP / Sensitive Data Protection, AWS Comprehend PII and Skyflow-style vaults do this at scale. Regexes plus checksums (Luhn for cards, mod-97 for IBANs) handle structured PII; names and addresses need an NER model on top.
- Real vaults encrypt the originals with a per-tenant key in a KMS. Crypto-shredding (destroying that key) then erases a tenant's PII everywhere, which pairs well with `tenant-isolated-memory` erasure.
- Some teams use deterministic encryption or format-preserving encryption (FF1) instead of counters, so tokens are stable across services without a shared lookup table. Counters leak ordering but are readable for the model.
- Redact before the prompt, before logs and before traces, and re-identify only at the edge, in the response a human with the right role sees. Log re-identification to a tamper-evident log (`hash-chained-audit-log`).
