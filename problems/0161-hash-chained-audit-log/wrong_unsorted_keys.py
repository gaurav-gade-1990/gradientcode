import copy
import hashlib
import json

GENESIS = "0" * 64


def canonical_json(event):
    return json.dumps(event, separators=(",", ":"), ensure_ascii=False)


def entry_hash(prev_hash, event):
    return hashlib.sha256((prev_hash + canonical_json(event)).encode("utf-8")).hexdigest()


def append_event(chain, event):
    prev = chain[-1]["hash"] if chain else GENESIS
    event = copy.deepcopy(event)
    entry = {"seq": len(chain), "prev_hash": prev, "event": event, "hash": entry_hash(prev, event)}
    chain.append(entry)
    return entry


def verify_chain(chain, head=None):
    for i, entry in enumerate(chain):
        expected_prev = GENESIS if i == 0 else chain[i - 1]["hash"]
        if entry["seq"] != i:
            return i
        if entry["prev_hash"] != expected_prev:
            return i
        if entry["hash"] != entry_hash(entry["prev_hash"], entry["event"]):
            return i
    current = chain[-1]["hash"] if chain else GENESIS
    if head is not None and current != head:
        return len(chain)
    return -1
