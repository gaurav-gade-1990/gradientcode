# Incident: the router sorted on the input price column only. Long-answer traffic went to a model
# with cheap input and 6.7x pricier output, and the monthly bill tripled.
from gc_runtime import BadRequestError, RateLimitError, ServerError, TimeoutError_

RETRYABLE = (RateLimitError, ServerError, TimeoutError_)


def _estimate(m, req):
    return (req["input_tokens"] * m["input_per_mtok"] + req["max_output_tokens"] * m["output_per_mtok"]) / 1e6


def route_requests(requests, models, tiers, call):
    limited = set()
    results, total = [], 0.0
    for req in requests:
        tier = tiers[req["tier"]]
        need = req["input_tokens"] + req["max_output_tokens"]
        eligible = [m for m in models
                    if m["quality"] >= tier["min_quality"] and m["p95_ms"] <= tier["max_p95_ms"]
                    and need <= m["context_window"] and m["name"] not in limited]
        eligible.sort(key=lambda m: (m["input_per_mtok"], -m["quality"], m["name"]))
        res = {"id": req["id"], "status": "no_eligible_model" if not eligible else "exhausted",
               "model": None, "attempts": [], "cost": 0.0}
        for m in eligible[:tier["max_attempts"]]:
            res["attempts"].append(m["name"])
            try:
                usage = call(m["name"], req)
            except BadRequestError:
                res["status"] = "bad_request"
                break
            except RETRYABLE as e:
                if isinstance(e, RateLimitError):
                    limited.add(m["name"])
                continue
            res["status"], res["model"] = "ok", m["name"]
            res["cost"] = (req["input_tokens"] * m["input_per_mtok"] + usage["output_tokens"] * m["output_per_mtok"]) / 1e6
            total += res["cost"]
            break
        results.append(res)
    return {"results": results, "total_cost": total}
