SMALL = {"name": "small", "share": 0.8, "input": 0.8, "cached_input": 0.08, "output": 4.0}
LARGE = {"name": "large", "share": 0.2, "input": 3.0, "cached_input": 0.3, "output": 15.0}
H100 = {"output_tokens_per_sec_per_gpu": 1500.0, "target_utilization": 0.6, "gpu_hourly_cost": 2.5}


def design(**kw):
    d = {"dau": 20000, "sessions_per_user": 1.5, "turns_per_session": 4, "system_tokens": 800, "user_tokens": 60,
         "output_tokens": 240, "cache_hit_rate": 0.7, "peak_to_avg": 3.0, "days_per_month": 30,
         "models": [SMALL, LARGE], "self_host": H100}
    d.update(kw)
    return d


def cases():
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"design": design(models=[dict(SMALL, share=1.0)], turns_per_session=1, cache_hit_rate=0.0)},
         "explanation": "One turn, no cache: 860 input and 240 output tokens per session, 30,000 sessions a day. "
                        "900,000 sessions a month cost (774M * $0.8 + 216M * $4) / 1e6 = $1,483.20. Peak decode is "
                        "30000/86400 * 3 * 240 = 250 tok/s, one GPU, $1,800 a month, so the API is cheaper."},
        {"name": "Example 2", "hidden": False,
         "args": {"design": design()},
         "explanation": "Four turns resend history: input = 4*860 + 300*6 = 5,240 tokens per session, of which the prefix "
                        "4*800 + 1,800 = 5,000 is cacheable and 70% of it (3,500) is read from cache."},
        {"name": "Example 3", "hidden": False,
         "args": {"design": design(dau=2_000_000, sessions_per_user=2, turns_per_session=6)},
         "explanation": "At 2M DAU the peak is 4M * 6 / 86400 * 3 = 833.3 QPS and 200,000 output tok/s. Each GPU "
                        "carries 1500 * 0.6 = 900 tok/s, so 223 GPUs, which is cheaper than the API bill."},
        {"name": "exact GPU boundary", "args": {"design": design(dau=86400, sessions_per_user=1, turns_per_session=1, peak_to_avg=1.0,
                                                                  output_tokens=750, self_host=dict(H100, target_utilization=0.5))}},
        {"name": "just over the boundary", "args": {"design": design(dau=86401, sessions_per_user=1, turns_per_session=1, peak_to_avg=1.0,
                                                                     output_tokens=750, self_host=dict(H100, target_utilization=0.5))}},
        {"name": "float noise on an exact fit", "args": {"design": design(dau=14400, sessions_per_user=1.1, turns_per_session=7, peak_to_avg=3.0, output_tokens=400,
                                                                         self_host={"output_tokens_per_sec_per_gpu": 2200.0, "target_utilization": 0.7, "gpu_hourly_cost": 2.5})}},
        {"name": "no decode load still needs one GPU", "args": {"design": design(output_tokens=0)}},
        {"name": "API and self-host tie", "args": {"design": design(models=[dict(SMALL, share=1.0, input=1.0, output=4.75)], turns_per_session=1, cache_hit_rate=0.0)}},
        {"name": "full cache hit", "args": {"design": design(cache_hit_rate=1.0, turns_per_session=10)}},
        {"name": "long sessions, three models", "args": {"design": design(
            dau=350000, sessions_per_user=0.4, turns_per_session=25, system_tokens=2500, user_tokens=120, output_tokens=400,
            cache_hit_rate=0.85, peak_to_avg=4.5, days_per_month=31,
            models=[dict(SMALL, share=0.6), dict(LARGE, share=0.3), {"name": "reasoning", "share": 0.1, "input": 10.0, "cached_input": 1.0, "output": 40.0}],
            self_host={"output_tokens_per_sec_per_gpu": 2200.0, "target_utilization": 0.7, "gpu_hourly_cost": 3.9})}},
        {"name": "tiny pilot", "args": {"design": design(dau=40, sessions_per_user=1, turns_per_session=3, peak_to_avg=10.0)}},
        {"name": "high peak factor", "args": {"design": design(dau=500000, sessions_per_user=1, turns_per_session=2, peak_to_avg=8.0,
                                                               self_host=dict(H100, target_utilization=0.9))}},
        {"name": "fractional GPU need", "args": {"design": design(dau=900000, sessions_per_user=1, turns_per_session=1, peak_to_avg=2.0,
                                                                  output_tokens=150, cache_hit_rate=0.5)}},
    ]
