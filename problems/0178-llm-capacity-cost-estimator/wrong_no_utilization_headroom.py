import math


def estimate(design):
    T = design["turns_per_session"]
    S, U, O = design["system_tokens"], design["user_tokens"], design["output_tokens"]
    history = (U + O) * T * (T - 1) / 2
    input_s = T * (S + U) + history
    cached_s = design["cache_hit_rate"] * (T * S + history)
    uncached_s = input_s - cached_s
    output_s = T * O

    days = design["days_per_month"]
    daily_sessions = design["dau"] * design["sessions_per_user"]
    daily_turns = daily_sessions * T
    avg_qps = daily_turns / 86400
    peak_qps = avg_qps * design["peak_to_avg"]
    monthly_sessions = daily_sessions * days

    by_model, api = {}, 0.0
    for m in design["models"]:
        share = m["share"]
        cost = share * monthly_sessions * (uncached_s * m["input"] + cached_s * m["cached_input"] + output_s * m["output"]) / 1e6
        by_model[m["name"]] = {
            "monthly_cost": cost,
            "monthly_input_tokens": share * monthly_sessions * input_s,
            "monthly_output_tokens": share * monthly_sessions * output_s,
        }
        api += cost

    sh = design["self_host"]
    peak_output_tps = peak_qps * O
    gpus = max(1, math.ceil(peak_output_tps / sh["output_tokens_per_sec_per_gpu"] - 1e-9))
    self_cost = gpus * sh["gpu_hourly_cost"] * 24 * days

    return {
        "daily_turns": float(daily_turns),
        "avg_qps": avg_qps,
        "peak_qps": peak_qps,
        "peak_output_tps": peak_output_tps,
        "monthly_input_tokens": float(monthly_sessions * input_s),
        "monthly_cached_tokens": float(monthly_sessions * cached_s),
        "monthly_output_tokens": float(monthly_sessions * output_s),
        "by_model": by_model,
        "api_monthly_cost": api,
        "cost_per_dau": api / design["dau"],
        "cost_per_turn": api / (daily_turns * days),
        "self_host_gpus": int(gpus),
        "self_host_monthly_cost": float(self_cost),
        "recommendation": "api" if api <= self_cost else "self_host",
    }
