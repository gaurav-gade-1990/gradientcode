# Incident: P2C broke ties toward the lower replica index instead of the first sample. Under light
# load every tie went to the same few replicas and their caches ran hot while others sat idle.
import heapq
import math
from collections import deque


def simulate_lb(requests, replicas, policy, pick2):
    n = len(replicas)
    outstanding = [0] * n
    busy = [0] * n
    queues = [deque() for _ in range(n)]
    peak = [0] * n
    finish = [None] * len(requests)
    assignment = [None] * len(requests)
    events = []                                   # (time, 0 = completion / 1 = arrival, seq, payload)
    seq = 0
    for i, r in enumerate(requests):
        events.append((r["arrival"], 1, seq, i))
        seq += 1
    heapq.heapify(events)

    def start(rep, i, now):
        nonlocal seq
        busy[rep] += 1
        heapq.heappush(events, (now + requests[i]["work"] / replicas[rep]["speed"], 0, seq, (rep, i)))
        seq += 1

    k = 0
    while events:
        now, kind, _, payload = heapq.heappop(events)
        if kind == 0:
            rep, i = payload
            finish[i] = now
            busy[rep] -= 1
            outstanding[rep] -= 1
            if queues[rep]:
                start(rep, queues[rep].popleft(), now)
            continue
        i = payload
        if policy == "round_robin":
            rep = k % n
        elif policy == "least_outstanding":
            rep = min(range(n), key=lambda j: (outstanding[j], j))
        else:
            a, b = pick2()
            rep = min((a, b), key=lambda j: (outstanding[j], j))
        k += 1
        assignment[i] = rep
        outstanding[rep] += 1
        peak[rep] = max(peak[rep], outstanding[rep])
        if busy[rep] < replicas[rep]["slots"]:
            start(rep, i, now)
        else:
            queues[rep].append(i)

    latency = [finish[i] - r["arrival"] for i, r in enumerate(requests)]
    srt = sorted(latency)

    def pct(q):
        return srt[max(0, math.ceil(q * len(srt)) - 1)]

    return {"assignment": assignment, "latency": latency, "p50": pct(0.50), "p99": pct(0.99), "max_outstanding": peak}
