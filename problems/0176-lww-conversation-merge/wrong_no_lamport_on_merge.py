import copy


class Replica:
    """merge() never advances the local clock, so an edit made after a sync can carry an older stamp and lose."""

    def __init__(self, device):
        self.device = device
        self.clock = 0
        self.entries = {}

    def _write(self, k, text, deleted):
        self.clock += 1
        s = [self.clock, self.device]
        old = self.entries.get(k)
        self.entries[k] = {"text": text, "deleted": deleted, "ts": s, "created": old["created"] if old else s}

    def put(self, msg_id, text):
        self._write(msg_id, text, False)

    def delete(self, msg_id):
        self._write(msg_id, None, True)

    def merge(self, state):
        for k, th in state.items():
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
