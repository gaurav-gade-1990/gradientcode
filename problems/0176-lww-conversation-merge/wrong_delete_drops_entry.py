import copy


class Replica:
    """delete() pops the key instead of writing a tombstone, so a stale replica resurrects the message."""

    def __init__(self, device):
        self.device = device
        self.clock = 0
        self.entries = {}

    def put(self, msg_id, text):
        self.clock += 1
        s = [self.clock, self.device]
        old = self.entries.get(msg_id)
        self.entries[msg_id] = {"text": text, "deleted": False, "ts": s, "created": old["created"] if old else s}

    def delete(self, msg_id):
        self.clock += 1
        self.entries.pop(msg_id, None)

    def merge(self, state):
        for k, th in state.items():
            self.clock = max(self.clock, th["ts"][0])
            mine = self.entries.get(k)
            if mine is None:
                self.entries[k] = copy.deepcopy(th)
                continue
            if tuple(th["ts"]) > tuple(mine["ts"]):
                mine.update(text=th["text"], deleted=th["deleted"], ts=list(th["ts"]))
            if tuple(th["created"]) < tuple(mine["created"]):
                mine["created"] = list(th["created"])

    def state(self):
        return copy.deepcopy(self.entries)

    def view(self):
        live = sorted((tuple(e["created"]), k, e["text"]) for k, e in self.entries.items() if not e["deleted"])
        return [{"id": k, "text": t} for _, k, t in live]
