# Incident: an off-by-one at the TTL boundary. A call exactly at expiry was counted as a read.
def prompt_cache_cost(calls, pricing):
    p_in, p_out = pricing["input_per_mtok"], pricing["output_per_mtok"]
    expires = {}
    rows, with_cache, without = [], 0.0, 0.0
    for c in calls:
        if c["prefix_tokens"] < pricing["min_cacheable_tokens"]:
            status, p_prefix = "uncacheable", p_in
        else:
            if c["prefix_id"] in expires and c["t"] <= expires[c["prefix_id"]]:
                status, p_prefix = "read", pricing["cache_read_mult"] * p_in
            else:
                status, p_prefix = "write", pricing["cache_write_mult"] * p_in
            expires[c["prefix_id"]] = c["t"] + pricing["ttl_s"]
        cost = (c["prefix_tokens"] * p_prefix + c["input_tokens"] * p_in + c["output_tokens"] * p_out) / 1e6
        base = ((c["prefix_tokens"] + c["input_tokens"]) * p_in + c["output_tokens"] * p_out) / 1e6
        rows.append({"id": c["id"], "status": status, "cost": cost})
        with_cache += cost
        without += base
    return {"calls": rows, "total_with_cache": with_cache, "total_without_cache": without, "savings": without - with_cache}
