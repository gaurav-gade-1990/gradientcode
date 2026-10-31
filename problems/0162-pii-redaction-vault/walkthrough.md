## 1. What the problem is really asking

Before a support ticket reaches a model or a log, every email, card number, SSN and phone number in it is swapped for a token like `[EMAIL_1]`. The real value goes into a vault. Later, a person with the right role can swap the tokens back.

Under the story there are three small pieces:

- **A pipeline of regex passes**, one per type, in a fixed order, each running `re.sub` over the output of the previous pass. One pass (`CARD`) has a checksum filter: a match that fails Luhn is put back unchanged.
- **A per-tenant dictionary** from `(tenant, type, canonical value)` to a token, with a counter per `(tenant, type)` to mint the next number. Its reverse, `(tenant, token)` to the first original text, is what re-identification reads.
- **An access check with an audit trail.** Denied attempts are logged too, before raising.

The judge runs a sequence of `redact` and `reidentify` calls, often re-identifying the output of an earlier call, and grades every returned string, every `PermissionError`, and the whole `audit` list. Token numbers are graded exactly, so the order in which you mint them matters.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `reidentify_roles` | a list like `["privacy-officer", "fraud-investigator"]` | store as a set; `reidentify` checks `role in self.roles` first |
| `tenant` | `"acme"`, `"globex"`, ... | part of every vault key, so tenants never share tokens |
| `text` | up to 500 characters of ticket text | `redact` runs four passes over it; `reidentify` scans it for tokens |
| `PATTERNS` | four `(type, compiled regex)` pairs, given in the starter | run in that order: EMAIL, CARD, SSN, PHONE |
| `audit` | a public list on the vault | one dict per `reidentify` call, allowed or not |

The driver returns `PermissionError` as `{"error": "PermissionError"}` in `results`, and copies `audit` at the end. Four details are easy to miss:

- **Canonical values decide "same person".** Emails are lowercased, so `Dana@Acme.com` and `dana@acme.com` share a token. Everything else is reduced to digits, and a phone with 11 digits drops its leading `1`, so `+1 512 555 0100` and `(512) 555-0100` both become `5125550100`.
- **The vault keeps the first original only.** Re-identifying `[PHONE_1]` returns whatever spelling was seen *first*, not the spelling in the text you're re-identifying. Round trips can change formatting.
- **The phone pattern needs a separator before the last four digits.** `5125550100` written with no separators isn't matched and stays in the text. That follows from the given regex, so don't try to "fix" it.
- **Unknown tokens are left alone and not audited.** `[EMAIL_9]` in a tenant that never minted it stays `[EMAIL_9]`, and it isn't listed in `tokens`.

## 3. Trace the examples by hand

**Example 1:** `"Refund dana@acme.com, card 4111 1111 1111 1111, phone 512-555-0100."` in tenant `acme`.

| pass | match | canonical | Luhn | becomes |
|---|---|---|---|---|
| EMAIL | `dana@acme.com` | `dana@acme.com` | — | `[EMAIL_1]` |
| CARD | `4111 1111 1111 1111` | `4111111111111111` | sum 30, passes | `[CARD_1]` |
| SSN | none | | | |
| PHONE | `512-555-0100` | `5125550100` | — | `[PHONE_1]` |

The Luhn sum for `4111111111111111`: from the right, every second digit is doubled. The doubled `4` becomes `8` and each doubled `1` becomes `2`, so the digits are `8,1,2,1,2,1,2,1,2,1,2,1,2,1,2,1`, summing to 30. That's divisible by 10, so it's a card.

The result is `"Refund [EMAIL_1], card [CARD_1], phone [PHONE_1]."`. The privacy officer re-identifies it back to the original string, and the audit gets `{"tenant": "acme", "role": "privacy-officer", "allowed": True, "tokens": ["[EMAIL_1]", "[CARD_1]", "[PHONE_1]"]}`.

**Example 2** has three teaching points. The CARD regex matches `1234 5678 9012 3456`, but its digits fail Luhn, so the callback returns the match unchanged and the order number survives. `Dana@Acme.com` in call 1 and `dana@acme.com` in call 2 canonicalize to the same key, so both become `[EMAIL_1]`. Then a `support-agent` asks to re-identify. That role isn't allowed, so the audit gets `{"allowed": False, "tokens": []}` and the call raises.

**Example 3** shows tenant isolation. acme's `ops@acme.com` becomes `[EMAIL_1]`, and globex's `415-555-0142` becomes `[PHONE_1]` (globex has its own counter, which starts at 1). globex's officer re-identifies acme's text: globex has no `[EMAIL_1]`, so the text comes back unchanged with `tokens: []`. Re-identifying globex's own text restores the phone number.

**The trickiest hidden case, "two tenants, same values":** globex redacts an escalation note first, giving `[PHONE_1]`, `[PHONE_2]`, `[CARD_1]` (amex) and `[CARD_2]` (mastercard). acme then redacts a ticket with Visa `4111...` as its `[CARD_1]`, then the same escalation note, where the amex becomes acme's `[CARD_2]` and the mastercard becomes `[CARD_3]`. Now acme re-identifies *globex's* redacted note. Every token in it exists in acme's vault, so it resolves, but to acme's values:

```
'Escalate: (512) 555-0100 and 512.555.0199, amex 4111 1111 1111 1111, mc 378282246310005.'
```

The "amex" is now acme's Visa. Nothing leaked across tenants, but the text is wrong, because a counter token only means something inside the tenant that minted it. That's exactly what the spec asks for, and it's why you must never re-identify text under a tenant other than the one that redacted it.

## 4. Key idea: one pass per type, in order

Each pass runs over the *output* of the previous one. Once a span has become `[EMAIL_1]`, it has no digit run left for a later pass to grab. The order exists to settle overlaps:

- An email can contain digits, so emails go first.
- A card written oddly, like `4111 11 111 111 1111`, contains `111 111 1111`, which the PHONE regex matches on its own. Running CARD first turns the whole card into `[CARD_1]`. Run PHONE first and you get `4111 11 [PHONE_1]`: half a card number left in the text, and the rest filed under the wrong type.

Inside one pass, `re.sub` finds non-overlapping matches left to right, and your callback decides what each one becomes. That's also where numbering comes from: tokens are minted in the order the callback runs, so EMAIL numbers come from the EMAIL pass, CARD numbers from the CARD pass, and so on, each with its own counter.

## 5. Key idea: deny, audit, then raise

A privacy team cares most about the attempts that *failed*. Someone probing for a role that works shows up only in the denied entries. So the role check comes first, before any vault lookup, and its audit entry is appended *before* `raise PermissionError`. Once you raise, nothing after it runs. In "denied then allowed", `fraud-investigator` and `admin` are both denied (that vault was built with only `privacy-officer`), and the audit holds three entries: two `allowed: False` and then one `allowed: True` with `["[SSN_1]", "[EMAIL_1]"]`.

## 6. Plan before you code

```
__init__: roles set, tokens {}, originals {}, counts {}, audit []

_token(tenant, kind, original):
    key = (tenant, kind, canonical(kind, original))
    if key is new:
        n = counts[(tenant, kind)] + 1, store it
        tok = "[KIND_n]"; tokens[key] = tok; originals[(tenant, tok)] = original
    return tokens[key]

redact(tenant, text):
    for kind, pattern in PATTERNS:
        text = pattern.sub(callback, text)
        callback: if CARD and Luhn fails -> return match unchanged; else -> _token(...)
    return text

reidentify(tenant, role, text):
    if role not allowed: audit denied; raise PermissionError
    replace each [TYPE_n] found in this tenant's originals; track first appearances
    audit allowed with that list; return text
```

| situation in `reidentify` | text | audit `tokens` |
|---|---|---|
| role not allowed | raises | `[]`, `allowed: False` |
| token in this tenant's vault | replaced by its first original | listed once, at first appearance |
| token from another tenant, or never minted | left as is | not listed |

## 7. Build it one piece at a time

**Step 1: Luhn and canonical values.** Luhn works on the digit string read from the right. Index `i` in the reversed string is odd for every second digit.

```python
def luhn_ok(digits):
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def canonical(kind, text):
    if kind == "EMAIL":
        return text.lower()
    digits = re.sub(r"\D", "", text)
    if kind == "PHONE" and len(digits) == 11:
        digits = digits[1:]
    return digits
```

Strip separators before Luhn. `int(" ")` would crash, and the checksum is defined on digits only.

**Step 2: minting tokens.** Three dictionaries, all keyed by tenant first. The counter is per `(tenant, kind)`, so acme's third email and globex's first email are numbered independently. Store the original only when minting, which is what "remembers the first occurrence" means.

```python
    def _token(self, tenant, kind, original):
        key = (tenant, kind, canonical(kind, original))
        if key not in self.tokens:
            n = self.counts.get((tenant, kind), 0) + 1
            self.counts[(tenant, kind)] = n
            tok = "[%s_%d]" % (kind, n)
            self.tokens[key] = tok
            self.originals[(tenant, tok)] = original
        return self.tokens[key]
```

**Step 3: the redaction passes.** `re.sub` with a function calls it once per match and splices in whatever it returns. Returning `s` itself is how a Luhn failure "puts the match back".

```python
    def redact(self, tenant, text):
        for kind, pattern in PATTERNS:
            def repl(m, kind=kind):
                s = m.group(0)
                if kind == "CARD" and not luhn_ok(re.sub(r"\D", "", s)):
                    return s
                return self._token(tenant, kind, s)
            text = pattern.sub(repl, text)
        return text
```

`kind=kind` binds the current loop value into the callback. Here `sub` calls `repl` before the loop moves on, so a plain closure would also work, but the default argument removes any doubt.

**Step 4: re-identification.** Role check first, then one `re.sub` over a token pattern. The `used` list keeps first-appearance order and skips repeats, and only tokens actually replaced go into it.

```python
    def reidentify(self, tenant, role, text):
        if role not in self.roles:
            self.audit.append({"tenant": tenant, "role": role, "allowed": False, "tokens": []})
            raise PermissionError("role %r may not re-identify" % role)
        used = []

        def repl(m):
            tok = m.group(0)
            if (tenant, tok) not in self.originals:
                return tok
            if tok not in used:
                used.append(tok)
            return self.originals[(tenant, tok)]
        out = TOKEN.sub(repl, text)
        self.audit.append({"tenant": tenant, "role": role, "allowed": True, "tokens": used})
        return out
```

## 8. Full solution

```python
import re  # every detector and the token scanner are regexes

PATTERNS = [  # detection passes, run in this order so earlier types claim their spans first
    ("EMAIL", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),  # emails first: they may hold digits
    ("CARD", re.compile(r"(?<!\d)\d(?:[ -]?\d){12,18}(?!\d)")),  # 13-19 digits, before phones can split them
    ("SSN", re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)")),  # 3-2-4 with dashes
    ("PHONE", re.compile(r"(?<!\d)(?:\+1[ .-]?)?\(?\d{3}\)?[ .-]?\d{3}[ .-]\d{4}(?!\d)")),  # US numbers, optional +1
]
TOKEN = re.compile(r"\[(EMAIL|CARD|SSN|PHONE)_(\d+)\]")  # what a token looks like, for re-identification


def luhn_ok(digits):  # the card checksum: weeds out order and tracking numbers
    total = 0  # running digit sum
    for i, ch in enumerate(reversed(digits)):  # walk from the rightmost digit
        d = int(ch)  # this digit's value
        if i % 2 == 1:  # every second digit from the right is doubled
            d *= 2  # double it
            if d > 9:  # a two-digit result...
                d -= 9  # ...counts as the sum of its digits
        total += d  # add it in
    return total % 10 == 0  # valid card numbers sum to a multiple of 10


def canonical(kind, text):  # the key that decides "same value" inside a tenant
    if kind == "EMAIL":  # emails are case-insensitive in practice
        return text.lower()  # Dana@Acme.com and dana@acme.com are one person
    digits = re.sub(r"\D", "", text)  # every other type is just its digits
    if kind == "PHONE" and len(digits) == 11:  # a phone written with the +1 country code
        digits = digits[1:]  # drop it so +1 512 555 0100 matches 512-555-0100
    return digits  # the canonical number


class PiiVault:  # per-tenant tokenization with audited re-identification
    def __init__(self, reidentify_roles):  # built once; the roles never change
        self.roles = set(reidentify_roles)  # fast membership test for the access check
        self.tokens = {}     # (tenant, kind, canonical) -> token
        self.originals = {}  # (tenant, token) -> original text
        self.counts = {}     # (tenant, kind) -> last number used
        self.audit = []  # every re-identification attempt, allowed or denied

    def _token(self, tenant, kind, original):  # the token for this value, minting one if new
        key = (tenant, kind, canonical(kind, original))  # tenant first, so tenants never share
        if key not in self.tokens:  # first time this tenant has seen this value
            n = self.counts.get((tenant, kind), 0) + 1  # next number for this tenant and type
            self.counts[(tenant, kind)] = n  # remember it for the next new value
            tok = "[%s_%d]" % (kind, n)  # e.g. [EMAIL_1]
            self.tokens[key] = tok  # same value -> same token from now on
            self.originals[(tenant, tok)] = original  # keep the first spelling for re-identification
        return self.tokens[key]  # existing or freshly minted token

    def redact(self, tenant, text):  # replace every detected value with its token
        for kind, pattern in PATTERNS:  # one pass per type, in the fixed order
            def repl(m, kind=kind):  # called by re.sub for each match; kind bound to this pass
                s = m.group(0)  # the matched text
                if kind == "CARD" and not luhn_ok(re.sub(r"\D", "", s)):  # a digit run that isn't a card
                    return s  # put it back unchanged (order numbers, tracking numbers)
                return self._token(tenant, kind, s)  # swap the value for its token
            text = pattern.sub(repl, text)  # the next pass sees this pass's output
        return text  # fully redacted text

    def reidentify(self, tenant, role, text):  # turn this tenant's tokens back into values
        if role not in self.roles:  # access check before touching the vault
            # denied attempts are exactly what a privacy team needs to see, so log first
            self.audit.append({"tenant": tenant, "role": role, "allowed": False, "tokens": []})
            raise PermissionError("role %r may not re-identify" % role)  # the caller gets nothing
        used = []  # tokens actually replaced, in order of first appearance

        def repl(m):  # called once per token-shaped match in the text
            tok = m.group(0)  # e.g. "[PHONE_1]"
            if (tenant, tok) not in self.originals:  # another tenant's token, or never minted
                return tok  # leave it as is and don't audit it
            if tok not in used:  # report each token once
                used.append(tok)  # first appearance fixes its position in the list
            return self.originals[(tenant, tok)]  # this tenant's stored original
        out = TOKEN.sub(repl, text)  # replace every token in one scan
        self.audit.append({"tenant": tenant, "role": role, "allowed": True, "tokens": used})  # log the success
        return out  # the re-identified text
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | `Refund [EMAIL_1], card [CARD_1], phone [PHONE_1].`, round trip restores it | the four passes and one allowed re-identification |
| Example 2 | order number kept, both Danas are `[EMAIL_1]`, then `PermissionError` | Luhn filter, lowercased emails, denied attempts audited |
| Example 3 | acme's `[EMAIL_1]` stays a token under globex, `tokens: []` | lookups are by `(tenant, token)` |
| ticket thread | `(512) 555-0100` and `+1 512-555-0100` both `[PHONE_1]`; tracking number kept | canonical phones, first original returned, a tracking number that fails Luhn |
| two tenants, same values | acme reads globex's note as its own values | separate counters per tenant; tokens mean nothing outside their tenant |
| phone formats normalize | four formats share `[PHONE_1]`; `5125550100` untouched | the 11-digit rule, and the regex's separator requirement |
| card formats and lengths | five cards tokenized, `4111 1111 1111 1112` kept | 13 to 16 digits, dashes, no separators, Luhn failure |
| no pii | text unchanged, `[EMAIL_9]` stays, `tokens: []` | nothing to do, and an unknown token isn't audited |
| denied then allowed | two `PermissionError`s, then success | the role set is the one passed in |
| repeated token reported once | `tokens: ["[EMAIL_1]", "[EMAIL_2]"]` | dedupe in first-appearance order |
| many messages | globex's ticket 38 resolves `[EMAIL_20]` to `user4@corp0.com` | 40 calls, two tenants, numbering stays independent |

## 10. Complexity

`redact` is four regex passes over at most 500 characters, plus an O(1) dictionary lookup per match. `reidentify` is one regex pass. Memory grows with the number of distinct `(tenant, type, value)` triples ever seen. In production that vault is a database table holding the most sensitive data you have, so the originals are encrypted with a per-tenant key from a KMS. Destroying that key ("crypto-shredding") erases one tenant's PII everywhere at once. The regex stage is cheap enough to run on every prompt, every log line and every trace before it leaves the service.

## 11. If you got Wrong Answer

- **Example 2's order number became `[CARD_1]`, and "card formats and lengths" mints `[CARD_6]`.** You skipped the Luhn check, so every 13+ digit run, including `4111 1111 1111 1112`, is treated as a card.
- **Example 2's second note shows `[EMAIL_2]`.** Your email key is case-sensitive. Lowercase it in `canonical`.
- **Example 2's `audit` is empty.** You raise `PermissionError` before appending the denied entry.
- **Example 3 returns `Contact ops@acme.com` under globex.** Your vault is shared across tenants. Key both maps by tenant.
- **"phone formats normalize" gives `[PHONE_2]` for `+1 512 555 0100`.** You didn't drop the leading `1` of an 11-digit phone.
- **"phone formats normalize" re-identifies to the *last* spelling, `512.555.0100`.** You overwrite `originals` on every occurrence. Store it only when minting.
- **"repeated token reported once" audits `["[EMAIL_1]", "[EMAIL_1]", "[EMAIL_2]", "[EMAIL_1]"]`.** You append every replacement. Append to `used` only if it isn't already there.

## 12. Follow-ups an interviewer might ask

- *How do you catch names and street addresses?* Regexes and checksums handle structured PII. Unstructured PII needs an NER model on top, as in Microsoft Presidio or Google Cloud Sensitive Data Protection. Mod-97 for IBANs is another checksum in the same style as Luhn.
- *Two services need the same token for the same email without sharing this table. What changes?* Use deterministic encryption or a keyed HMAC per tenant instead of a counter. The token is then a function of the value and the tenant key, so any service with the key produces the same one. Counters are more readable for the model but need a shared lookup.
- *Where should the audit entries go?* Somewhere tamper-evident: a hash-chained log (problem 161, hash-chained-audit-log), so a privacy officer can't hide their own lookups.
- *A tenant asks to be deleted. What do you remove?* Their vault rows, or just their KMS key. The same tenant-scoped erasure shows up in tenant memory (problem 159, tenant-isolated-memory).
- *Can a prompt injection make the model leak PII?* Not from redacted text, because the model never sees the values. That's the point of redacting before the prompt and re-identifying only at the edge, for a human with the right role.
