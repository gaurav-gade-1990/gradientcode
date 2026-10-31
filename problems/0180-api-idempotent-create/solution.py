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
    while True:
        rec = db.claim(scoped, fingerprint)
        if rec is None:
            break
        if rec["fingerprint"] != fingerprint:
            return _resp(422)
        if rec["status"] == "done":
            return dict(rec["response"], replayed=True)
        yield POLL
    try:
        run_id = yield from db.create_run(user_id, body)
    except ServerError:
        db.release(scoped)
        return _resp(500)
    resp = _resp(201, run_id)
    db.complete(scoped, resp)
    return resp
