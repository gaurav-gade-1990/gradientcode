import numpy as np

CFG = {"initial_replicas": 2, "min_replicas": 1, "max_replicas": 12, "capacity_per_replica": 16, "target_pct": 75,
       "tolerance_pct": 10, "scale_up_window_s": 0, "scale_down_window_s": 120, "scale_up_cooldown_s": 30,
       "scale_down_cooldown_s": 60, "max_scale_up_step": 4}


def trace(loads, dt=15):
    return [{"t": i * dt, "load": int(l)} for i, l in enumerate(loads)]


def diurnal(n, seed):
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n):
        base = 60 + 50 * np.sin(2 * np.pi * i / 240.0)
        spike = 80 if 100 <= i < 108 else 0
        out.append(max(0, int(base + spike + rng.normal(0, 8))))
    return trace(out)


def cases():
    return [
        {"name": "Example 1", "hidden": False, "args": {"samples": trace([24, 25, 60, 120, 120, 120, 120]), "config": CFG},
         "explanation": "Each replica targets 75% of 16 = 12 in-flight requests. 24 and 25 sit within 10% of 2 x 12, so nothing changes. At t=30, 60 requests need ceil(6000/1200) = 5 replicas. At t=45, 120 needs 10, but the 30 s scale-up cooldown blocks it. At t=60 it is allowed, but the step cap limits it to 5 + 4 = 9. At t=75 the cooldown blocks again, and at t=90 the fleet reaches 10."},
        {"name": "Example 2", "hidden": False, "args": {"samples": trace([96, 96, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30], dt=30), "config": dict(CFG, initial_replicas=8)},
         "explanation": "Load drops from 96 to 30 at t=60, which would need only 3 replicas. The scale-down window takes the MAX recommendation over the last 120 s, which still includes the 8 from t=30, so the fleet holds. The 8 leaves the window at t=180 and the fleet drops straight to 3."},
        {"name": "Example 3", "hidden": False, "args": {"samples": trace([12, 40, 12, 40, 12, 40, 12, 40, 12, 40], dt=30), "config": dict(CFG, initial_replicas=1)},
         "explanation": "Load oscillates between 12 and 40 every 30 s. Scale-ups react at once (up window 0), but every low sample is outvoted by a recent high one in the 120 s down window. The fleet goes to 4 and stays there instead of flapping."},
        {"name": "up stabilization window", "args": {"samples": trace([10, 60, 12, 60, 60, 60, 60]), "config": dict(CFG, initial_replicas=1, scale_up_window_s=30, scale_up_cooldown_s=0)}},
        {"name": "cooldowns are per direction", "args": {"samples": trace([96, 20, 20, 20, 20, 100, 20, 20, 20], dt=40),
                                                          "config": dict(CFG, initial_replicas=8, scale_down_window_s=0, scale_up_cooldown_s=200, scale_down_cooldown_s=100)}},
        {"name": "clamped to min and max", "args": {"samples": trace([0, 0, 500, 500, 500, 0, 0, 0, 0, 0, 0, 0, 0, 0]),
                                                     "config": dict(CFG, initial_replicas=3, min_replicas=2, max_replicas=10, max_scale_up_step=20)}},
        {"name": "tolerance boundary", "args": {"samples": trace([132, 133, 108, 107, 120]),
                                                 "config": dict(CFG, initial_replicas=10, tolerance_pct=10, scale_down_window_s=0, scale_down_cooldown_s=0, scale_up_cooldown_s=0, max_replicas=20)}},
        {"name": "zero tolerance, exact ceil", "args": {"samples": trace([13, 24, 25, 36, 37, 1]),
                                                         "config": dict(CFG, initial_replicas=1, tolerance_pct=0, scale_down_window_s=0, scale_up_cooldown_s=0, scale_down_cooldown_s=0)}},
        {"name": "step cap during a flash crowd", "args": {"samples": trace([20, 300, 300, 300, 300, 300, 300], dt=30),
                                                            "config": dict(CFG, max_replicas=40, max_scale_up_step=3, scale_up_cooldown_s=60)}},
        {"name": "diurnal day with a spike", "args": {"samples": diurnal(300, 133), "config": dict(CFG, max_replicas=20)}},
        {"name": "uneven sample spacing", "args": {"samples": [{"t": 0, "load": 30}, {"t": 7, "load": 70}, {"t": 50, "load": 70}, {"t": 51, "load": 10},
                                                               {"t": 170, "load": 10}, {"t": 172, "load": 10}, {"t": 400, "load": 10}],
                                                   "config": CFG}},
    ]
