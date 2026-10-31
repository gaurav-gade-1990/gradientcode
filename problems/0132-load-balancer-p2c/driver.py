def run(ns, requests, replicas, policies, pairs):
    """Run the user's simulation once per policy; P2C samples come from a recorded pick2()."""
    out = {}
    for policy in policies:
        draws = list(pairs)
        used = [0]

        def pick2():
            if used[0] >= len(draws):
                raise AssertionError("pick2() called more times than there are requests")
            a, b = draws[used[0]]
            used[0] += 1
            return a, b

        res = dict(ns["simulate_lb"](requests, replicas, policy, pick2))
        res["pick2_calls"] = used[0]
        out[policy] = res
    return out
