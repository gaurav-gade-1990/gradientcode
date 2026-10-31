# Updates every arm from the simulator's counterfactual outcomes: information production never has.
def run_thompson(variants, requests, sample_beta, warm_weight):
    post, priors = {}, {}
    alloc = {v["id"]: 0 for v in variants}
    choices, reward = [], 0
    for i, req in enumerate(requests):
        for v in variants:
            if v["launch_at"] == i:
                parent = v["warm_start_from"]
                if parent is None:
                    prior = [1, 1]
                else:
                    a_p, b_p = post[parent]
                    s = (warm_weight * a_p) // (a_p + b_p)
                    prior = [1 + s, 1 + warm_weight - s]
                priors[v["id"]] = list(prior)
                post[v["id"]] = list(prior)
        best, best_draw = None, None
        for v in variants:
            if v["launch_at"] <= i:
                a, b = post[v["id"]]
                draw = sample_beta(a, b)
                if best is None or draw > best_draw:
                    best, best_draw = v["id"], draw
        r = req["outcomes"][best]
        for vid in post:
            o = req["outcomes"][vid]
            post[vid][0] += o
            post[vid][1] += 1 - o
        alloc[best] += 1
        reward += r
        choices.append(best)

    leader = None
    for v in variants:
        if alloc[v["id"]] == 0:
            continue
        a, b = post[v["id"]]
        if leader is None or a * (post[leader][0] + post[leader][1]) > post[leader][0] * (a + b):
            leader = v["id"]
    return {"choices": choices, "allocations": alloc, "priors": priors, "posteriors": post, "reward": reward, "leader": leader}
