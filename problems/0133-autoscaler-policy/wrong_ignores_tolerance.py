# Incident: no tolerance band. Load hovering around the target made the fleet add and remove a
# replica every few minutes, each time with a cold start and a dropped KV cache.
def autoscale(samples, config):
    R = config["initial_replicas"]
    C = config["capacity_per_replica"] * config["target_pct"]
    lo, hi = config["min_replicas"], config["max_replicas"]
    last_up = last_down = float("-inf")
    history, replicas, events, overloaded = [], [], [], 0

    for s in samples:
        t, load = s["t"], s["load"]
        if load > R * config["capacity_per_replica"]:
            overloaded += 1
        raw = -(-(load * 100) // C)
        raw = max(lo, min(hi, raw))
        history.append((t, raw))
        up_rec = min(r for ht, r in history if ht >= t - config["scale_up_window_s"])
        down_rec = max(r for ht, r in history if ht >= t - config["scale_down_window_s"])

        if up_rec > R:
            target = min(up_rec, R + config["max_scale_up_step"])
            if t - last_up >= config["scale_up_cooldown_s"]:
                events.append({"t": t, "action": "scale_up", "from": R, "to": target})
                R, last_up = target, t
            else:
                events.append({"t": t, "action": "blocked_up", "from": R, "to": target})
        elif down_rec < R:
            if t - last_down >= config["scale_down_cooldown_s"]:
                events.append({"t": t, "action": "scale_down", "from": R, "to": down_rec})
                R, last_down = down_rec, t
            else:
                events.append({"t": t, "action": "blocked_down", "from": R, "to": down_rec})
        replicas.append(R)

    replica_seconds = 0
    for i in range(len(samples) - 1):
        replica_seconds += replicas[i] * (samples[i + 1]["t"] - samples[i]["t"])
    return {"replicas": replicas, "events": events, "replica_seconds": replica_seconds, "overloaded_samples": overloaded}
