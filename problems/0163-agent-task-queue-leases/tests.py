import numpy as np


def E(at, task, priority=1, payload=None):
    return {"at": at, "op": "enqueue", "task": task, "priority": priority, "payload": payload if payload is not None else {"kind": "reconcile", "ref": task}}


def L(at, worker):
    return {"at": at, "op": "lease", "worker": worker}


def H(at, lease):
    return {"at": at, "op": "heartbeat", "lease": lease}


def A(at, lease):
    return {"at": at, "op": "ack", "lease": lease}


def N(at, lease):
    return {"at": at, "op": "nack", "lease": lease}


def S(at):
    return {"at": at, "op": "sweep"}


def _chaos(n_tasks, seed):
    """Workers that finish, stall, crash and come back. Leases are guessed from the task id and a delivery count."""
    rng = np.random.default_rng(seed)
    ops = [E(0, "job-%02d" % k, int(rng.integers(0, 3))) for k in range(n_tasks)]
    t = 0.0
    held = []
    for step in range(160):
        t += float(rng.integers(1, 6))
        r = rng.random()
        if r < 0.35 or not held:
            ops.append(L(t, "w%d" % int(rng.integers(0, 4))))
            held.append(len(ops) - 1)
        else:
            k = held[-1 - int(rng.integers(0, min(3, len(held))))]
            ref = {"lease_from": k}
            kind = ["ack", "ack", "heartbeat", "nack", "ack"][int(rng.integers(0, 5))]
            ops.append(dict({"at": t, "op": kind}, **ref))
    return ops


def cases():
    return [
        {"name": "Example 1", "hidden": False, "args": {"ops": [
            E(0, "inv-1182", 1), E(0, "contract-7", 0), L(1, "coworker-a"), L(2, "coworker-b"), A(10, "contract-7#1"), A(11, "contract-7#1"), A(12, "inv-1182#1")]},
         "explanation": "contract-7 is P0, so coworker-a gets it first even though inv-1182 was enqueued earlier. The second ack of contract-7#1 is a duplicate and logs nothing."},
        {"name": "Example 2", "hidden": False, "args": {"ops": [
            E(0, "inv-1182"), L(0, "coworker-a"), H(20, "inv-1182#1"), L(45, "coworker-b"), L(50, "coworker-b"), A(55, "inv-1182#1"), A(56, "inv-1182#2")]},
         "explanation": "The heartbeat at 20 moves the deadline to 50. At 45 the lease is still held, so nothing is ready. At 50 the lease expires (deadline <= now) and coworker-b gets delivery 2. "
                        "coworker-a comes back at 55 with its old lease and is told 'stale'; coworker-b's ack succeeds."},
        {"name": "Example 3", "hidden": False, "args": {"max_deliveries": 2, "ops": [
            E(0, "eval-run-3"), L(0, "w1"), L(30, "w2"), S(60), L(61, "w3")]},
         "explanation": "Two workers crash in a row. The second expiry happens at the sweep at t=60, the task has been delivered max_deliveries=2 times, so it goes to the DLQ and w3 gets nothing."},
        {"name": "empty queue", "args": {"ops": [L(0, "w1"), A(1, "ghost#1"), N(2, "ghost#1"), H(3, "ghost#1"), S(4)]}},
        {"name": "duplicate enqueue", "args": {"ops": [E(0, "t1", 2), E(1, "t1", 0), L(2, "w"), A(3, "t1#1"), E(4, "t1", 0), L(5, "w")]}},
        {"name": "nack until dead", "args": {"ops": [E(0, "flaky"), E(0, "steady"), L(1, "w1"), N(2, "flaky#1"), L(3, "w1"), L(3, "w2"), N(4, "flaky#2"),
                                                     L(5, "w1"), N(6, "flaky#3"), N(7, "flaky#3"), A(8, "steady#1"), L(9, "w1")]}},
        {"name": "requeued task keeps its place", "args": {"ops": [E(0, "a"), E(1, "b"), E(2, "c"), L(3, "w1"), N(4, "a#1"), L(5, "w2"), L(6, "w3"), L(7, "w4")]}},
        {"name": "expiry exactly at deadline", "args": {"ops": [E(0, "t"), L(0, "w1"), H(30, "t#1"), A(30, "t#1"), L(30, "w2"), A(59.5, "t#2")]}},
        {"name": "heartbeat after expiry", "args": {"ops": [E(0, "t"), L(0, "w1"), H(31, "t#1"), L(32, "w2"), H(40, "t#2"), H(65, "t#2"), A(90, "t#2"), A(91, "t#1")]}},
        {"name": "zombie ack while re-leased", "args": {"ops": [E(0, "refund-9"), L(0, "w1"), L(31, "w2"), A(35, "refund-9#1"), A(36, "refund-9#2"), A(37, "refund-9#1")]}},
        {"name": "zombie ack after redelivery is ready", "args": {"ops": [E(0, "x"), L(0, "w1"), S(30), A(31, "x#1"), L(32, "w2"), A(33, "x#2")]}},
        {"name": "several expire in one sweep", "args": {"visibility_timeout": 10.0, "ops": [
            E(0, "p1", 1), E(0, "p0", 0), E(0, "p2", 2), L(0, "w1"), L(1, "w2"), L(1, "w3"), H(5, "p0#1"), S(40), L(41, "w4"), L(41, "w5"), L(41, "w6"), L(41, "w7")]}},
        {"name": "max_deliveries 1", "args": {"max_deliveries": 1, "ops": [E(0, "once"), L(0, "w1"), N(1, "once#1"), E(2, "twice"), L(2, "w1"), S(100), L(101, "w2")]}},
        {"name": "chaos", "args": {"ops": _chaos(8, 163), "visibility_timeout": 25.0}},
        {"name": "chaos with short leases", "args": {"ops": _chaos(12, 1630), "visibility_timeout": 9.0, "max_deliveries": 4}},
    ]
