SCOPES = {"private": 0, "team": 1, "org": 2}


class MemoryStore:
    def __init__(self):
        self.mems = {}      # id -> record
        self.index = {}     # (tenant, user, agent, key) -> id
        self.next_id = 1
        self.seq = 0

    def _visible(self, m, ctx):
        if m["tenant"] != ctx["tenant"]:
            return False
        if m["scope"] == "private":
            return m["user"] == ctx["user"] and m["agent"] == ctx["agent"]
        if m["scope"] == "team":
            return ctx.get("team") is not None and m["team"] == ctx.get("team")
        return True

    def write(self, ctx, key, value, scope="private", sources=()):
        if scope not in SCOPES:
            raise ValueError("unknown scope %r" % scope)
        if scope == "team" and ctx.get("team") is None:
            raise ValueError("team scope needs a team")
        for s in sources:
            if s not in self.mems or not self._visible(self.mems[s], ctx):
                raise PermissionError("source %s is not visible" % s)
        ident = (ctx["tenant"], ctx["user"], ctx["agent"], key)
        mid = self.index.get(ident)
        if mid is None:
            mid = "mem_%d" % self.next_id
            self.next_id += 1
            self.index[ident] = mid
        self.seq += 1
        self.mems[mid] = {"id": mid, "tenant": ctx["tenant"], "user": ctx["user"], "agent": ctx["agent"],
                          "team": ctx.get("team"), "key": key, "value": value, "scope": scope,
                          "sources": list(sources), "seq": self.seq}
        return mid

    def read(self, ctx, key):
        hits = [m for m in self.mems.values() if m["key"] == key and self._visible(m, ctx)]
        if not hits:
            return None
        return min(hits, key=lambda m: (SCOPES[m["scope"]], -m["seq"]))["value"]

    def visible(self, ctx):
        ids = [mid for mid, m in self.mems.items() if self._visible(m, ctx)]
        return sorted(ids, key=lambda s: int(s.split("_")[1]))

    def delete_user(self, tenant, user):
        doomed = {mid for mid, m in self.mems.items() if m["tenant"] == tenant and m["user"] == user}
        changed = True
        while changed:
            changed = False
            for mid, m in self.mems.items():
                if mid not in doomed and any(s in doomed for s in m["sources"]):
                    doomed.add(mid)
                    changed = True
        for mid in doomed:
            m = self.mems.pop(mid)
            del self.index[(m["tenant"], m["user"], m["agent"], m["key"])]
        return sorted(doomed, key=lambda s: int(s.split("_")[1]))
