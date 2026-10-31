# Incident: legal changed the system prompt to require a disclaimer. The cache kept serving
# answers generated under the old prompt for a week, because the prompt wasn't in the key.
import hashlib

from gc_runtime import embed


class SemanticCache:
    def __init__(self, clock, log, capacity=100, threshold=0.9, ttl_s=3600.0):
        self.clock = clock
        self.log = log
        self.capacity = capacity
        self.threshold = threshold
        self.ttl_s = ttl_s
        self.entries = []         # kept in store order, oldest first
        self.tick = 0

    def _partition(self, tenant, model, system_prompt):
        return (tenant, model)

    def _touch(self, e):
        self.tick += 1
        e["used"] = self.tick

    def _purge(self):
        now = self.clock.now()
        keep = []
        for e in self.entries:
            if now >= e["stored_at"] + self.ttl_s:
                self.log.append("evict", tenant=e["key"][0], query=e["query"], reason="ttl")
            else:
                keep.append(e)
        self.entries = keep

    def get(self, tenant, model, system_prompt, query):
        self._purge()
        key = self._partition(tenant, model, system_prompt)
        v = embed(query, dim=64)
        best, best_score = None, None
        for e in self.entries:            # later entries win ties: they were stored more recently
            if e["key"] != key:
                continue
            s = float(v @ e["vec"])
            if best is None or s >= best_score:
                best, best_score = e, s
        if best is not None and best_score >= self.threshold:
            self._touch(best)
            self.log.append("hit", tenant=tenant, query=query, matched=best["query"], score=best_score)
            return best["answer"]
        self.log.append("miss", tenant=tenant, query=query)
        return None

    def put(self, tenant, model, system_prompt, query, answer):
        self._purge()
        key = self._partition(tenant, model, system_prompt)
        same = [e for e in self.entries if e["key"] == key and e["query"] == query]
        if same:
            e = same[0]
            self.entries.remove(e)
            e["answer"], e["stored_at"] = answer, self.clock.now()
        else:
            if len(self.entries) >= self.capacity:
                victim = min(self.entries, key=lambda x: x["used"])
                self.entries.remove(victim)
                self.log.append("evict", tenant=victim["key"][0], query=victim["query"], reason="lru")
            e = {"key": key, "query": query, "vec": embed(query, dim=64), "answer": answer, "stored_at": self.clock.now()}
        self.entries.append(e)
        self._touch(e)
        self.log.append("store", tenant=tenant, query=query)
