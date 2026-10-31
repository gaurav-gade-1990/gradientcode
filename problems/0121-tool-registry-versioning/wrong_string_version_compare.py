import re

NAME = re.compile(r"[A-Za-z0-9_-]+")
RANGE = re.compile(r"([\^~]?)((?:0|[1-9][0-9]*)(?:\.(?:0|[1-9][0-9]*)){0,2})")


def _bump(parts, i):
    out = list(parts) + [0] * (3 - len(parts))
    out[i] += 1
    for j in range(i + 1, 3):
        out[j] = 0
    return tuple(out)


def _interval(op, parts):
    """Return (lower, upper) as version tuples, upper exclusive."""
    lower = tuple(parts + [0] * (3 - len(parts)))
    if op == "^":
        nonzero = [i for i, p in enumerate(parts) if p != 0]
        return lower, _bump(parts, nonzero[0] if nonzero else len(parts) - 1)
    if op == "~":
        return lower, _bump(parts, 1 if len(parts) >= 2 else 0)
    if len(parts) == 3:
        return lower, _bump(parts, 2)  # exact: [1.2.3, 1.2.4)
    return lower, _bump(parts, len(parts) - 1)


class ToolRegistry:
    def __init__(self):
        self.tools = {}  # name -> {version tuple: (version string, status)}

    def register(self, name, version, status="active"):
        key = tuple(int(p) for p in version.split("."))
        self.tools.setdefault(name, {})[key] = (version, status)

    def resolve(self, spec):
        name, sep, rng = spec.partition("@")
        if not NAME.fullmatch(name):
            return {"ok": False, "error": "invalid_spec"}
        if sep:
            m = RANGE.fullmatch(rng)
            if not m:
                return {"ok": False, "error": "invalid_spec"}
            lower, upper = _interval(m.group(1), [int(p) for p in m.group(2).split(".")])
        else:
            lower, upper = None, None
        if name not in self.tools:
            return {"ok": False, "error": "unknown_tool"}
        matches = {"active": [], "deprecated": [], "removed": []}
        for key, (text, status) in self.tools[name].items():
            if lower is None or lower <= key < upper:
                matches[status].append((key, text))
        if matches["active"]:
            return {"ok": True, "version": max(t for _, t in matches["active"]), "warning": None}
        if matches["deprecated"]:
            return {"ok": True, "version": max(t for _, t in matches["deprecated"]), "warning": "deprecated"}
        if matches["removed"]:
            return {"ok": False, "error": "removed"}
        return {"ok": False, "error": "not_found"}
