## 1. What the problem is really asking

Three devices each hold a full copy of a conversation. Each edits and deletes offline, and every so often one device sends its whole state to another. Whatever order those syncs happen in, every device must end up showing the same messages with the same text in the same order.

The structure that guarantees this is a **state-based CRDT**, here a map of **last-writer-wins registers**. Each message id holds a value plus the *stamp* of the write that set it. Merging two copies keeps, per id, the entry with the larger stamp. "Keep the max" doesn't care about order (commutative), grouping (associative) or repeats (idempotent), so replicas converge no matter how syncs are scheduled.

Everything then hangs on the stamp being a **total order that respects causality**. That is the Lamport pair `[lamport, device]`: the counter makes "written after I saw your edit" compare larger, and the device id breaks ties between concurrent writes the same way on every replica.

The judge runs a script of local writes and one-way syncs and records `views` (with each device's `clock`) at marked steps. Then it checks three properties using *your* class: merging every device's state into a fresh replica in all orders gives one result (`commutative`), merging the same state twice changes nothing (`idempotent`), and after everyone syncs with everyone the views match (`converged`). It also reports the `merged_state` and the final `clocks`, so the exact stamps are graded, not just the text.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `device` | this replica's id, like `"phone"` | second element of every stamp you create; the tie-breaker |
| `self.clock` | the Lamport counter, starts at 0 | `+1` on every local write; raised to the max seen on merge |
| `put(msg_id, text)` | a local create or edit | new stamp; `deleted = False`; keep `created` if the id exists |
| `delete(msg_id)` | a local delete | new stamp; `text = None`, `deleted = True`; **keep the key** |
| `merge(state)` | another replica's `state()` | per id, keep the larger `ts`; take the smaller `created` |
| `state()` | your whole map, JSON-able | return a deep copy so the caller can't alias your entries |
| `view()` | visible messages | entries with `deleted == False`, sorted by `created`, then id |

Three details are easy to miss:

- **Stamps are lists in the state but must compare as tuples.** `[2, "laptop"] > [1, "phone"]` happens to work on lists in Python, but turning them into tuples makes the intent obvious and is what you sort on in `view()`.
- **`created` is merged separately from the value.** The text, `deleted` flag and `ts` move together as one unit. `created` takes the *minimum* of the two sides, whichever side's value wins.
- **Merge raises the clock but never increments it.** After merging, `clock = max(clock, largest lamport in the incoming state)`. Only a local write adds 1. The judge reports `clock` in every recorded view, so an extra `+1` fails every case.

## 3. Trace Example 3 by hand

Two devices. The phone writes two messages, the laptop syncs and deletes the first, then they sync both ways.

| step | op | device's entries after the op | clock |
|---|---|---|---|
| 1 | phone `put m1` | m1: text "My card ending 4242...", ts `[1, phone]`, created `[1, phone]` | phone 1 |
| 2 | phone `put m2` | m2: "Ignore that, wrong account", ts `[2, phone]`, created `[2, phone]` | phone 2 |
| 3 | laptop syncs from phone | both ids are new on the laptop, so both are copied | laptop 2 |
| 4 | laptop `delete m1` | m1: text `None`, deleted, ts `[3, laptop]`, created still `[1, phone]` | laptop 3 |
| 5 | phone syncs from laptop | m1: `[3, laptop] > [1, phone]`, so the tombstone wins; m2 equal, unchanged | phone 3 |
| 6 | laptop syncs from phone | m1: `[3, laptop]` vs `[3, laptop]`, unchanged; nothing comes back | laptop 3 |

Step 4's recorded view is `[{"id": "m2", ...}]` with `clock` 3. The judge's `merged_state` keeps the tombstone:

```python
{"m1": {"created": [1, "phone"], "deleted": True, "text": None, "ts": [3, "laptop"]},
 "m2": {"created": [2, "phone"], "deleted": False, "text": "Ignore that, wrong account", "ts": [2, "phone"]}}
```

The key point is step 6. The phone's state no longer has the old m1 text, but think about a third device that synced before the delete and still holds `[1, phone]`. When it syncs to the laptop, the laptop compares `[1, phone]` with its tombstone `[3, laptop]` and keeps the tombstone. If the laptop had *removed* m1 instead, the old entry would look new and be copied straight back. That is exactly the hidden case "stale sync after delete".

**Example 2, the tie.** Both devices write m1 offline, so both stamps have lamport 1: `[1, phone]` and `[1, laptop]`. As tuples, `(1, "phone") > (1, "laptop")` because `"phone" > "laptop"`. Both devices keep the phone's text "Order 1182 arrived damaged". The `merged_state` shows `ts = [1, "phone"]` but `created = [1, "laptop"]`, the smaller of the two `created` stamps. The value came from one side and the creation stamp from the other.

**The tricky hidden case, "concurrent delete vs edit tie".** The laptop writes m1 at `[1, laptop]`. The phone syncs (clock 1) and deletes m1 at `[2, phone]`. Meanwhile the laptop edits m1 to "Ship to 14 Elm St" at `[2, laptop]`. Same lamport again, and `"phone" > "laptop"`, so **the delete wins** on both devices, and both recorded views are `[]`. Nothing about deletes is special-cased: a tombstone is just a value, and it wins or loses by its stamp like any other.

## 4. Key idea: raise the clock on merge

Look at "lamport lag". The phone writes `m1` to `m5`, reaching clock 5. The laptop syncs, then edits m3 to "final wording".

- **With the merge rule,** the laptop's clock is 5 after the sync, so its edit is stamped `[6, laptop]`. That beats `[3, phone]`, and the phone shows "final wording" after syncing back.
- **Without it,** the laptop's clock is still 0, so the edit is stamped `[1, laptop]`. That *loses* to `[3, phone]`, which the laptop already has, so the user's edit vanishes on the very device where they typed it. In `wrong_no_lamport_on_merge.py` the first recorded view has `clock` 1 where 6 was expected.

Raising the clock is what makes the Lamport order respect causality: anything you write after seeing a stamp gets a larger stamp.

## 5. Key idea: why ties go to the larger device, never to "mine"

For the devices to converge, the winner of a comparison must depend only on the two stamps, never on which replica is doing the merge. Comparing lamport alone and keeping the local copy on a tie (`wrong_tie_keeps_local.py`) makes the phone keep its text and the laptop keep its own. In Example 2 the laptop's view then shows "Order 1182 never arrived" where "Order 1182 arrived damaged" was expected. The full tuple comparison `(lamport, device)` gives a total order, so every replica picks the same winner.

## 6. Plan before you code

```
entries: {msg_id: {"text", "deleted", "ts", "created"}}

_write(msg_id, text, deleted):        # shared by put and delete
    clock += 1; stamp = [clock, device]
    created = old created if the id exists, else stamp
    store {text, deleted, ts: stamp, created}

merge(state):
    top = clock
    for each id in state:
        top = max(top, their ts lamport)
        new locally      -> deep-copy their entry
        their ts larger  -> take their text, deleted, ts together
        their created smaller -> take their created
    clock = top                        # raise, never +1

view(): live entries sorted by (created tuple, id)
```

| comparison | winner |
|---|---|
| `ts` lamport differs | higher lamport |
| `ts` lamport equal | larger device string |
| `created` differs | smaller stamp (the earliest write anyone made) |

## 7. Build it one piece at a time

**Step 1: one write path for put and delete.** A delete is a write whose value is "deleted". Sharing the code means both get a fresh stamp and both keep `created`.

```python
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
```

`delete` on an id you have never seen still writes a tombstone. In "delete unknown then merge" the laptop deletes `m9` at `[1, laptop]` before the phone writes it at `[1, phone]`. After syncing, the phone's write wins (`"phone" > "laptop"`), but `created` stays `[1, "laptop"]`, the earliest write anyone made.

**Step 2: merge, per id.** Track the largest lamport as you go, and assign it once at the end.

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

`copy.deepcopy` on a new entry, and `list(...)` when you take their stamps, keep your entries from sharing list objects with the dict you were given. Later edits to your own entries then can't reach back into the caller's data.

**Step 3: state and view.**

```python
def state(self):
    return copy.deepcopy(self.entries)

def view(self):
    live = [(tuple(e["created"]), k, e["text"]) for k, e in self.entries.items() if not e["deleted"]]
    return [{"id": k, "text": t} for _, k, t in sorted(live)]
```

Sorting on `created` gives every device the same order, even though each device inserted the ids into its dict in a different order. In "three devices ordering" the laptop's view is `l1, t1, l2`: stamps `[1, laptop]`, `[1, tablet]`, `[2, laptop]`. The `[1, ...]` messages written concurrently on different devices are ordered by device name, then `l2` comes last.

## 8. Full solution

```python
# deepcopy keeps our entries from sharing objects with states we send or receive
import copy


# one device's copy of the conversation: a map of last-writer-wins registers
class Replica:
    # a fresh replica with an empty map and a zero Lamport clock
    def __init__(self, device):
        self.device = device  # our id, used as the tie-breaker in every stamp
        self.clock = 0  # the Lamport counter
        self.entries = {}  # msg_id -> {"text", "deleted", "ts", "created"}

    # the single write path shared by put and delete
    def _write(self, msg_id, text, deleted):
        self.clock += 1  # every local write moves our clock forward
        stamp = [self.clock, self.device]  # this write's stamp
        old = self.entries.get(msg_id)  # is the id already known here?
        created = old["created"] if old else stamp  # keep the original creation stamp if we have one
        # text, deleted and ts are replaced together; created survives edits
        self.entries[msg_id] = {"text": text, "deleted": deleted, "ts": stamp, "created": list(created)}

    # create or edit a message locally
    def put(self, msg_id, text):
        self._write(msg_id, text, False)  # a visible value with a fresh stamp

    # delete a message locally, leaving a tombstone
    def delete(self, msg_id):
        self._write(msg_id, None, True)  # the key stays, so the delete can beat older copies

    # fold another replica's state into ours
    def merge(self, state):
        top = self.clock  # the largest lamport seen so far
        for msg_id, theirs in state.items():  # merge id by id
            top = max(top, theirs["ts"][0])  # remember the newest lamport we have now seen
            mine = self.entries.get(msg_id)  # our entry for this id, if any
            if mine is None:  # we have never heard of this id
                self.entries[msg_id] = copy.deepcopy(theirs)  # take theirs, without aliasing it
                continue  # nothing to compare
            if tuple(theirs["ts"]) > tuple(mine["ts"]):  # their write is later (lamport, then device)
                # the winning value moves as one unit
                mine["text"], mine["deleted"], mine["ts"] = theirs["text"], theirs["deleted"], list(theirs["ts"])
            if tuple(theirs["created"]) < tuple(mine["created"]):  # they know of an earlier write
                mine["created"] = list(theirs["created"])  # created is the min, so order agrees everywhere
        self.clock = top  # raise the clock to the max seen; merge never adds 1

    # our whole map, safe for the caller to keep or change
    def state(self):
        return copy.deepcopy(self.entries)  # a copy, so nobody can alias our entries

    # the visible conversation, in the same order on every device
    def view(self):
        # live entries only, keyed by creation stamp then id
        live = [(tuple(e["created"]), k, e["text"]) for k, e in self.entries.items() if not e["deleted"]]
        return [{"id": k, "text": t} for _, k, t in sorted(live)]  # sorted, then shaped as the judge wants
```

## 9. How the test cases map to the code

| test case | expected (from the judge) | what it checks |
|---|---|---|
| Example 1 | laptop clock 1 after the sync, then its edit wins at `[2, laptop]` | raising the clock on merge, plus keeping `created = [1, phone]` |
| Example 2 | both show the phone's text; `ts [1, phone]`, `created [1, laptop]` | the device tie-break, and `created` merged as a min |
| Example 3 | m1 stays a tombstone at `[3, laptop]`; views show only m2 | delete is a write, and the key is never removed |
| lamport lag | laptop's edit of m3 is stamped 6 and wins | the clock catches up after a long offline run |
| edit after delete resurrects | m1 visible with "very urgent", `ts [3, phone]` | a later write beats a tombstone, with no special case |
| concurrent delete vs edit tie | both views `[]`; tombstone `ts [2, phone]` | a tombstone wins a tie like any other value |
| three devices ordering | laptop view `l1, t1, l2`; final `l1, p1, l2` | `view()` sorted by `created` stamp, then id |
| four devices concurrent | m1 is `"d"` after the tablet sync, then `"b2"` | four-way tie broken by device name; an edit after syncing wins |
| delete unknown then merge | m9 visible, `created [1, laptop]` | deleting an unknown id still creates a tombstone and a `created` stamp |
| stale sync after delete | every view `[]` | a stale copy can't resurrect a deleted message |

All ten cases end with `commutative`, `idempotent` and `converged` all `True`.

## 10. Complexity

`put` and `delete` are O(1). `merge` is O(m) for an incoming state of `m` entries, plus the cost of copying new entries. `view` is O(n log n) for the sort. `state` is O(n) for the deep copy. Memory is O(n), where `n` counts every id ever written, **tombstones included**.

That last point is what bites at scale. Tombstones never go away here, so a long conversation with many deletes keeps growing. Real systems garbage-collect a tombstone once every replica is known to have seen it (causal stability, usually tracked with vector clocks), or after a retention window. Sending the whole state on every sync is also O(n) on the wire. Delta-state CRDTs send only entries changed since the peer's last acknowledged version.

## 11. If you got Wrong Answer

- **A recorded `clock` is lower than expected** (Example 1 shows 0 instead of 1, "lamport lag" shows 1 instead of 6). Merge doesn't raise the clock: `wrong_no_lamport_on_merge.py`.
- **A recorded `clock` is one higher than expected after every sync.** Merge adds 1. Raise to the max, never increment.
- **Example 2 shows "Order 1182 never arrived" on the laptop.** You compare lamport only and keep your own copy on a tie: `wrong_tie_keeps_local.py`. It also fails "four devices concurrent" (`"a"` where `"d"` was expected).
- **A deleted message reappears, or a recorded `clock` is too low after a delete.** You pop the key instead of writing a tombstone: `wrong_delete_drops_entry.py`. It fails Example 3, "concurrent delete vs edit tie", "stale sync after delete" and three more.
- **`commutative` is `False` in Example 2, "four devices concurrent" or "delete unknown then merge".** You never take the smaller `created`, so the merged state depends on which device was merged first.
- **"three devices ordering" lists `l2` before `t1`.** You sort `view()` by id instead of by `created` stamp.

## 12. Follow-ups an interviewer might ask

- *Why not use wall-clock timestamps?* Phone clocks drift by seconds or minutes, so a device with a fast clock wins every conflict, even against edits made after it. Hybrid logical clocks (CockroachDB, MongoDB) combine wall time with a Lamport counter so stamps stay near real time and still respect causality.
- *Two people edit the same message at once. Is losing one edit acceptable?* For a field like a title or a status, yes, and that's LWW. For collaborative text, no. Sequence CRDTs (RGA in Automerge, YATA in Yjs) merge character-level edits so both survive.
- *How would you garbage-collect tombstones?* Track what each replica has seen (a vector clock per device). Once every replica has seen a tombstone's stamp, nothing older can arrive, so you can drop it. Without that knowledge, a retention window is the usual compromise.
- *Full-state sync is heavy. What's cheaper?* Send deltas: entries changed since the peer's last acknowledged version. That pairs naturally with resuming a stream by sequence number (problem 179, websocket-reconnect-resume).
- *How do you get these changes to other services reliably?* Write the change and an outbox row in one transaction, and publish from the outbox (problem 172, transactional-outbox).
