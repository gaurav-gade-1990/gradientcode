import json

from gc_runtime import ServerError

POLL = 0.05


def _resp(status, run_id=None, replayed=False):
    return {"status": status, "run_id": run_id, "replayed": replayed}


def handle_create_run(db, user_id, headers, body):
    key = None
    for name, value in headers.items():
        if name.lower() == "idempotency-key":
            key = value
    if not key:
        return _resp(400)
    fingerprint = json.dumps(body, sort_keys=True, separators=(",", ":"))
    scoped = (user_id, key)
    rec = db.get(scoped)
    if rec is not None:
        if rec["fingerprint"] != fingerprint:
            return _resp(422)
        return dict(rec["response"], replayed=True)
    # Race: nothing is reserved while the insert is in flight.
    try:
        run_id = yield from db.create_run(user_id, body)
    except ServerError:
        return _resp(500)
    resp = _resp(201, run_id)
    db.put(scoped, {"fingerprint": fingerprint, "status": "done", "response": resp})
    return resp
