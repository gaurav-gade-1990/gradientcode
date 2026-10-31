import re


def _escape(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class InjectionGuard:
    def __init__(self, rules, min_len=6):
        self.rules = rules
        self.min_len = min_len
        self.spans = []  # original text of every quarantined span, across all tool outputs

    def wrap(self, call_id, tool, text):
        accepted = []  # (start, end, rule)
        for rule in self.rules:
            for m in re.finditer(rule["pattern"], text, re.IGNORECASE):
                s, e = m.start(), m.end()
                if s == e:
                    continue
                if any(s < e2 and s2 < e for s2, e2, _ in accepted):
                    continue
                accepted.append((s, e, rule))
        accepted.sort(key=lambda x: x[0])
        parts, pos = [], 0
        for s, e, rule in accepted:
            parts.append(_escape(text[pos:s]))
            if rule["action"] == "strip":
                parts.append("[removed:%s]" % rule["id"])
            else:
                parts.append("[flagged:%s]%s[/flagged]" % (rule["id"], _escape(text[s:e])))
            self.spans.append(text[s:e])
            pos = e
        parts.append(_escape(text[pos:]))
        return '<tool_output tool="%s" id="%s" trust="untrusted">\n%s\n</tool_output>' % (tool, call_id, "".join(parts))

    def _tainted(self, value):
        a = value.strip().lower()
        if len(a) < self.min_len:
            return False
        return any(a in sp.lower() or sp.lower() in a for sp in self.spans)

    def check_call(self, call_id, tool, arguments, approved):
        tainted = []

        def walk(v, path):
            if isinstance(v, dict):
                for k, x in v.items():
                    walk(x, path + [str(k)])
            elif isinstance(v, list):
                for i, x in enumerate(v):
                    walk(x, path + [str(i)])
            elif isinstance(v, str) and self._tainted(v):
                tainted.append(".".join(path))

        walk(arguments, [])
        tainted.sort()
        if not tainted:
            decision = "allow"
        elif approved:
            decision = "approved"
        else:
            decision = "blocked"
        return {"decision": decision, "tainted": tainted}
