import copy


class Replica:
    def __init__(self, device):
        self.device = device
        self.clock = 0
        self.entries = {}

    def _write(self, msg_id, text, deleted):
        self.clock += 1
        stamp = [self.clock, self.device]
        old = self.entries.get(msg_id)
        created = old["created"] if old else stamp
        self.entries[msg_id] = {"text": text, "deleted": deleted, "ts": stamp, "created": list(created)}

    def put(self, msg_id, text):
        self._write(msg_id, text, False)

    def delete(self, msg_id):
        self._write(msg_id, None, True)

    def merge(self, state):
        top = self.clock
        for msg_id, theirs in state.items():
            top = max(top, theirs["ts"][0])
            mine = self.entries.get(msg_id)
            if mine is None:
                self.entries[msg_id] = copy.deepcopy(theirs)
                continue
            if tuple(theirs["ts"]) > tuple(mine["ts"]):
                mine["text"], mine["deleted"], mine["ts"] = theirs["text"], theirs["deleted"], list(theirs["ts"])
            if tuple(theirs["created"]) < tuple(mine["created"]):
                mine["created"] = list(theirs["created"])
        self.clock = top

    def state(self):
        return copy.deepcopy(self.entries)

    def view(self):
        live = [(tuple(e["created"]), k, e["text"]) for k, e in self.entries.items() if not e["deleted"]]
        return [{"id": k, "text": t} for _, k, t in sorted(live)]
