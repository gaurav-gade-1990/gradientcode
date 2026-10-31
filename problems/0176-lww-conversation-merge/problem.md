Your chat app lets a user edit and delete messages on their phone, laptop and tablet, offline or online. Each device keeps a full replica of the conversation and syncs by sending its whole state to another device. Every device must end up showing the same conversation no matter what order the syncs happen in.

Implement `class Replica(device)`, a last-writer-wins map from message id to message, stamped with Lamport clocks.

**Stamps.** A stamp is the list `[lamport, device]`. Stamps compare as tuples: the higher `lamport` wins, and on equal `lamport` the lexicographically larger `device` string wins. `self.clock` is the device's Lamport counter and starts at `0`.

**State.** `state()` returns a JSON-able dict:

```
{msg_id: {"text": str or None, "deleted": bool, "ts": [lamport, device], "created": [lamport, device]}}
```

`ts` is the stamp of the write that produced the current value. `created` is the stamp of the earliest write anyone made to that id.

| method | rule |
|---|---|
| `put(msg_id, text)` | `clock += 1`, stamp `s = [clock, device]`. Set the entry to `text`, `deleted = False`, `ts = s`. If the id is new locally, `created = s`; otherwise keep `created`. |
| `delete(msg_id)` | `clock += 1`, stamp `s`. Set `text = None`, `deleted = True`, `ts = s` (a **tombstone**; never remove the key). If the id is new locally, `created = s`. |
| `merge(state)` | `state` is another replica's `state()`. For each id: if it is new locally, copy the entry. Otherwise keep whichever of the two entries has the larger `ts` (text, deleted and ts move together), and set `created` to the smaller of the two `created` stamps. Then set `clock = max(clock, largest ts lamport in state)`. Merge never increments the clock. |
| `view()` | The visible conversation: a list of `{"id", "text"}` for entries with `deleted == False`, sorted by `created` stamp, then by id. |

A later write beats a delete, so an edit stamped after a tombstone brings the message back. That is the rule; do not special-case it.

The judge runs a script of local edits and one-way syncs, records some views, then checks three properties with your class: merging all device states into a fresh replica gives the same state in **every** order (commutative), merging the same state twice changes nothing (idempotent), and after everyone syncs with everyone, all devices show the same view (converged).

**Constraints**

- At most 4 devices and 40 operations.
- Device ids are distinct non-empty strings. Message ids and text are strings.
- `merge` must not mutate the dict it is given.
