from gc_runtime import ERRORS


def run(ns, requests, models, tiers, outcomes):
    """Give the router a fake provider pool. `outcomes[req_id][model]` scripts an error kind; default is success."""
    log = []
    by_id = {r["id"]: r for r in requests}

    def call(model_name, request):
        rid = request["id"]
        log.append([rid, model_name])
        if model_name not in {m["name"] for m in models}:
            raise ERRORS["bad_request"]("unknown model %s" % model_name)
        kind = outcomes.get(rid, {}).get(model_name)
        if kind:
            cls = ERRORS[kind]
            raise cls("%s from %s" % (kind, model_name))
        return {"output_tokens": by_id[rid]["actual_output_tokens"]}

    reqs = [{k: v for k, v in r.items() if k != "actual_output_tokens"} for r in requests]
    out = ns["route_requests"](reqs, models, tiers, call)
    out = dict(out)
    out["calls"] = log
    return out
