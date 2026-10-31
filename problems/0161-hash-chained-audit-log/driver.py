import copy
import hashlib
import json

GENESIS = "0" * 64


def _h(prev, event):
    body = json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256((prev + body).encode("utf-8")).hexdigest()


def _tamper(chain, op):
    """What an attacker with write access to the table does. The attacker knows the hash formula."""
    kind = op["op"]
    if kind == "edit":
        chain[op["index"]]["event"][op["field"]] = op["value"]
    elif kind == "rehash":
        e = chain[op["index"]]
        e["hash"] = _h(e["prev_hash"], e["event"])
    elif kind == "delete":
        del chain[op["index"]]
    elif kind == "renumber":
        for i, e in enumerate(chain):
            e["seq"] = i
    elif kind == "rewrite_from":
        for i in range(op["index"], len(chain)):
            prev = GENESIS if i == 0 else chain[i - 1]["hash"]
            chain[i]["prev_hash"] = prev
            chain[i]["hash"] = _h(prev, chain[i]["event"])
    elif kind == "swap":
        i, j = op["i"], op["j"]
        chain[i], chain[j] = chain[j], chain[i]
    elif kind == "truncate":
        del chain[op["keep"]:]
    elif kind == "set":
        chain[op["index"]][op["field"]] = op["value"]
    else:
        raise ValueError(kind)


def run(ns, events, tamper=(), anchor=True, mutate_input=()):
    """Append every event with your code, then verify the intact chain and a tampered copy."""
    append, verify = ns["append_event"], ns["verify_chain"]
    chain = []
    for e in events:
        got = append(chain, e)
        if got is not chain[-1]:
            raise AssertionError("append_event must append the entry to chain and return it")
    hashes = [e["hash"] for e in chain]
    head = chain[-1]["hash"] if chain else GENESIS
    for m in mutate_input:  # the caller reuses its dicts after logging them
        events[m["index"]][m["field"]] = m["value"]
    snapshot = copy.deepcopy(chain)
    intact = verify(chain, head)
    if chain != snapshot:
        raise AssertionError("verify_chain modified the chain")
    tampered = copy.deepcopy(chain)
    for op in tamper:
        _tamper(tampered, op)
    first_bad = verify(tampered, head if anchor else None)
    return {
        "entries": [{"seq": e["seq"], "prev_hash": e["prev_hash"][:12], "hash": e["hash"][:12]} for e in snapshot],
        "head": head,
        "intact": intact,
        "first_bad": first_bad,
    }
