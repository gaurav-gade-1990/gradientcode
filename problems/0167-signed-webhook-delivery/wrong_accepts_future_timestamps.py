import hashlib
import hmac
import json
import re


def sign(secret, timestamp, body):
    mac = hmac.new(secret.encode(), ("%d.%s" % (timestamp, body)).encode(), hashlib.sha256).hexdigest()
    return "t=%d,v1=%s" % (timestamp, mac)


def verify(secret, header, body, now, tolerance=300):
    ts, sigs = [], []
    for item in header.split(","):
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        if key == "t":
            ts.append(value)
        elif key == "v1":
            sigs.append(value)
    if len(ts) != 1 or not re.fullmatch(r"[0-9]+", ts[0]) or not sigs:
        return "malformed"
    t = int(ts[0])
    expected = hmac.new(secret.encode(), ("%d.%s" % (t, body)).encode(), hashlib.sha256).hexdigest()
    if not any(hmac.compare_digest(expected.encode(), s.encode()) for s in sigs):
        return "bad_signature"
    if now - t > tolerance:
        return "stale"
    return "ok"


class Receiver:
    def __init__(self, secret, tolerance=300):
        self.secret = secret
        self.tolerance = tolerance
        self.processed = []
        self._seen = set()

    def handle(self, header, body, now):
        if verify(self.secret, header, body, now, self.tolerance) != "ok":
            return 400
        event_id = json.loads(body)["id"]
        if event_id in self._seen:
            return 200
        self._seen.add(event_id)
        self.processed.append(event_id)
        return 200


def deliver(event, secret, send, clock, schedule):
    body = json.dumps(event, sort_keys=True, separators=(",", ":"))
    for attempt in range(len(schedule) + 1):
        header = sign(secret, int(clock.now()), body)
        status = send(header, body)
        if 200 <= status < 300:
            return {"status": "delivered", "attempts": attempt + 1}
        if status == 410:
            return {"status": "disabled", "attempts": attempt + 1}
        if attempt < len(schedule):
            clock.sleep(schedule[attempt])
    return {"status": "failed", "attempts": len(schedule) + 1}
