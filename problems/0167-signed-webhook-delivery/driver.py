import hashlib
import hmac
import re

from gc_runtime import Clock


class _HmacProbe:
    """Stands in for the hmac module in your namespace and counts compare_digest calls."""

    def __init__(self, counter):
        self._counter = counter

    def compare_digest(self, a, b):
        self._counter[0] += 1
        return hmac.compare_digest(a, b)

    def __getattr__(self, name):
        return getattr(hmac, name)


def _instrument(ns, counter):
    probe = _HmacProbe(counter)
    for k, v in list(ns.items()):
        if v is hmac:
            ns[k] = probe
        elif v is hmac.compare_digest:
            ns[k] = probe.compare_digest


def _fill(header, body):
    """Expand {sig:SECRET:TS} placeholders with a correct v1 signature (the judge's own signer)."""
    def sub(m):
        secret, ts = m.group(1), m.group(2)
        return hmac.new(secret.encode(), ("%s.%s" % (ts, body)).encode(), hashlib.sha256).hexdigest()
    return re.sub(r"\{sig:([^:}]*):([0-9]+)\}", sub, header)


def run(ns, secret, events=(), faults=(), schedule=(60, 300, 1800, 7200), tolerance=300, probes=(), start=1700000000.0):
    counter = [0]
    _instrument(ns, counter)
    clock = Clock(start)
    receiver = ns["Receiver"](secret, tolerance)
    pending = list(faults)
    attempts = []
    current = {}

    def send(header, body):
        fault = pending.pop(0) if pending else "ok"
        rec = {"event": current["id"], "t": int(clock.now()), "fault": fault}
        if fault == "ok":
            status = receiver.handle(header, body, clock.now())
        elif fault == "lost":
            receiver.handle(header, body, clock.now())
            status = 0
        elif fault.startswith("late:"):
            clock.advance(float(fault[5:]))
            status = receiver.handle(header, body, clock.now())
        elif fault == "tamper":
            status = receiver.handle(header, body.replace('"amount":', '"amount":9', 1), clock.now())
        else:
            status = int(fault)
        rec["status"] = status
        attempts.append(rec)
        return status

    deliveries = []
    for ev in events:
        current["id"] = ev["id"]
        res = ns["deliver"](ev, secret, send, clock, list(schedule))
        deliveries.append({"event": ev["id"], "status": res["status"], "attempts": res["attempts"]})
    probe_results = []
    for p in probes:
        header = _fill(p["header"], p.get("signed_body", p["body"]))
        probe_results.append(ns["verify"](p.get("secret", secret), header, p["body"], p["now"], p.get("tolerance", 300)))
    return {
        "deliveries": deliveries,
        "attempts": attempts,
        "processed": list(receiver.processed),
        "probes": probe_results,
        "compare_digest_used": counter[0] > 0,
    }
