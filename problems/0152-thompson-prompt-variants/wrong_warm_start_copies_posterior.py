# Copies the parent's full posterior, so a new prompt inherits thousands of conversations of confidence it never earned.
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
                    prior = [a_p, b_p]
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
        post[best][0] += r
        post[best][1] += 1 - r
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
