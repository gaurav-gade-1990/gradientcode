## Approach

Treat each message as a **last-writer-wins register**: a value plus the stamp of the write that set it. Merge keeps the larger stamp. Because "keep the max" is commutative, associative and idempotent, replicas converge whatever order the syncs arrive in. That is what makes this a state-based CRDT.

The stamp has to be a total order that respects causality:

- **Lamport counter first.** Every local write increments the clock. Every merge raises the clock to the largest lamport received. So an edit made after seeing another edit always carries a larger lamport.
- **Device id second.** Concurrent writes can share a lamport value. Breaking the tie by device id makes every replica pick the same winner.

```python
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
```

A delete is just a write whose value is "deleted". The key stays, as a **tombstone**, so it can beat older copies still sitting on other devices. `created` is merged with `min`, which is also a CRDT, so the visible order is the same everywhere.

## Common mistakes

- **Removing the key on delete.** The next sync from a device that missed the delete brings the message back. Users see deleted messages (or deleted card numbers) reappear.
- **Not advancing the clock on merge.** A device that has been offline has a small counter. Its edit, made after it synced, gets a stamp lower than the text it replaced, and the edit silently loses.
- **Ties that favor the local copy.** Each device keeps its own version of a concurrent edit, so the devices diverge forever. The tie-break must depend only on the stamps, never on who is merging.
- **Wall-clock timestamps.** Phone clocks drift by seconds or minutes. LWW on wall time lets a device with a fast clock win every conflict.

## Production notes

- Figma, Linear and Apple Notes all use LWW registers or close variants for fields. Automerge and Yjs use richer CRDTs (RGA/YATA sequences) when two people edit the same text concurrently and both edits must survive.
- Hybrid logical clocks (CockroachDB, MongoDB) combine wall time with a Lamport counter so stamps are close to real time and still respect causality.
- Tombstones grow without bound. Real systems garbage-collect them once every replica has acknowledged the delete (a causal-stability or vector-clock check), or after a retention window.
- Sending full state is simple but heavy. Delta-state CRDTs send only the entries changed since the peer's last acked version, which pairs with `websocket-reconnect-resume` (179).
