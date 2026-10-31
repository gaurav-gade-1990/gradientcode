import re

PATTERNS = [
    ("EMAIL", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("CARD", re.compile(r"(?<!\d)\d(?:[ -]?\d){12,18}(?!\d)")),
    ("SSN", re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)")),
    ("PHONE", re.compile(r"(?<!\d)(?:\+1[ .-]?)?\(?\d{3}\)?[ .-]?\d{3}[ .-]\d{4}(?!\d)")),
]
TOKEN = re.compile(r"\[(EMAIL|CARD|SSN|PHONE)_(\d+)\]")


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


class PiiVault:
    def __init__(self, reidentify_roles):
        self.roles = set(reidentify_roles)
        self.tokens = {}     # (tenant, kind, canonical) -> token
        self.originals = {}  # (tenant, token) -> original text
        self.counts = {}     # (tenant, kind) -> last number used
        self.audit = []

    def _token(self, tenant, kind, original):
        key = (tenant, kind, canonical(kind, original))
        if key not in self.tokens:
            n = self.counts.get((tenant, kind), 0) + 1
            self.counts[(tenant, kind)] = n
            tok = "[%s_%d]" % (kind, n)
            self.tokens[key] = tok
            self.originals[(tenant, tok)] = original
        return self.tokens[key]

    def redact(self, tenant, text):
        for kind, pattern in PATTERNS:
            def repl(m, kind=kind):
                s = m.group(0)
                return self._token(tenant, kind, s)
            text = pattern.sub(repl, text)
        return text

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
