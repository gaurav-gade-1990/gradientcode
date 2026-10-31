import json

from gc_runtime import ToolError


class IdempotentExecutor:
    def __init__(self, clock, ttl):
        self.clock = clock
        self.ttl = ttl
        self.store = {}  # key -> (fingerprint, result, stored_at)

    def execute(self, key, tool, args, fn):
        now = self.clock.now()
        fingerprint = (tool, json.dumps(args, sort_keys=True))
        entry = self.store.get(key) if key is not None else None
        if entry is not None and now - entry[2] >= self.ttl:
            del self.store[key]
            entry = None
        if entry is not None:
            if entry[0] == fingerprint:
                if len(entry) == 4:
                    return entry[3]
                return {"status": "replayed", "result": entry[1]}
            return {"status": "conflict"}
        try:
            result = fn(args)
        except ToolError as e:
            result = {"status": "failed", "error": str(e)}
            if key is not None:
                self.store[key] = (fingerprint, None, now, result)
            return result
        if key is not None:
            self.store[key] = (fingerprint, result, now)
        return {"status": "executed", "result": result}
