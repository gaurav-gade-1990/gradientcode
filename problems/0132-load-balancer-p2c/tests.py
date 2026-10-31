import numpy as np

DEGRADED = [{"name": "gpu-a", "speed": 1.0, "slots": 1}, {"name": "gpu-b", "speed": 1.0, "slots": 1},
            {"name": "gpu-c", "speed": 1.0, "slots": 1}, {"name": "gpu-d-degraded", "speed": 0.25, "slots": 1}]
ALL = ["round_robin", "least_outstanding", "p2c"]


def reqs(n, gap, work=1.0, start=0.0):
    return [{"id": "r%03d" % i, "arrival": start + i * gap, "work": work} for i in range(n)]


def pairs_for(n_req, n_rep, seed):
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n_req):
        a, b = rng.choice(n_rep, size=2, replace=False)
        out.append([int(a), int(b)])
    return out


def load(n, seed, mean_gap):
    rng = np.random.default_rng(seed)
    t, out = 0.0, []
    for i in range(n):
        t += float(rng.exponential(mean_gap))
        out.append({"id": "q%04d" % i, "arrival": round(t, 6), "work": round(float(rng.lognormal(0.0, 0.6)), 6)})
    return out


FLEET = [{"name": "h100-%d" % i, "speed": 1.0, "slots": 4} for i in range(6)] + \
        [{"name": "a100-%d" % i, "speed": 0.55, "slots": 4} for i in range(2)]


def cases():
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"requests": reqs(8, 0.5), "replicas": DEGRADED, "policies": ["round_robin", "least_outstanding"], "pairs": []},
         "explanation": "Requests arrive every 0.5 s and take 1 s on a healthy replica but 4 s on gpu-d. Round-robin sends r003 to gpu-d (done at 5.5 s, latency 4) and then r007, which queues behind it and waits until 9.5 s: latency 6. Least-outstanding finds gpu-a free again at t=1 (the completion is processed before the arrival), so it alternates gpu-a and gpu-b and never touches the slow replica."},
        {"name": "Example 2", "hidden": False,
         "args": {"requests": reqs(6, 0.25), "replicas": DEGRADED, "policies": ["p2c"],
                  "pairs": [[3, 0], [0, 1], [2, 3], [3, 1], [3, 2], [0, 3]]},
         "explanation": "Each request samples two replicas and takes the less loaded one. r000 sees a 0-0 tie between 3 and 0, so it takes the first, 3 (the slow one). r002 and r003 avoid 3 because it has a request in flight. But r004 samples (3, 2) while both hold one request, so the tie goes to 3 and r004 waits behind r000: latency 7. Two choices beat one, but counts alone cannot see that replica 3 is slow."},
        {"name": "Example 3", "hidden": False,
         "args": {"requests": [{"id": "a", "arrival": 0.0, "work": 1.0}, {"id": "b", "arrival": 0.0, "work": 2.0}, {"id": "c", "arrival": 1.0, "work": 1.0}],
                  "replicas": [{"name": "r0", "speed": 1.0, "slots": 1}, {"name": "r1", "speed": 1.0, "slots": 1}],
                  "policies": ["least_outstanding"], "pairs": []},
         "explanation": "a finishes on r0 at exactly t=1, the same instant c arrives. Completions are processed first, so r0 has 0 outstanding against r1's 1, and c goes to r0 with no wait."},
        {"name": "round robin piles onto a slow replica", "args": {"requests": reqs(40, 0.3), "replicas": DEGRADED, "policies": ALL, "pairs": pairs_for(40, 4, 1321)}},
        {"name": "batched replicas with queueing", "args": {"requests": reqs(30, 0.1, work=1.5), "replicas": [dict(r, slots=2) for r in DEGRADED], "policies": ALL, "pairs": pairs_for(30, 4, 1322)}},
        {"name": "simultaneous completions and arrivals", "args": {"requests": reqs(12, 1.0, work=2.0), "replicas": DEGRADED[:2] + [DEGRADED[3]], "policies": ALL, "pairs": pairs_for(12, 3, 1323)}},
        {"name": "burst at one instant", "args": {"requests": reqs(10, 0.0), "replicas": DEGRADED, "policies": ALL, "pairs": pairs_for(10, 4, 1324)}},
        {"name": "p2c ties take the first draw", "args": {"requests": reqs(5, 10.0), "replicas": DEGRADED, "policies": ["p2c"], "pairs": [[2, 1], [1, 0], [3, 2], [0, 3], [1, 2]]}},
        {"name": "fleet under load", "args": {"requests": load(600, 132, 0.12), "replicas": FLEET, "policies": ALL, "pairs": pairs_for(600, 8, 1325)}},
        {"name": "small p99 sample", "args": {"requests": [{"id": "x%d" % i, "arrival": 2.0 * i, "work": float(1 + (i * 7) % 5) + i / 100} for i in range(100)],
                                               "replicas": DEGRADED[:2], "policies": ALL, "pairs": pairs_for(100, 2, 1326)}},
    ]
