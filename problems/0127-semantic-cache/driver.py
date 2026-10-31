from gc_runtime import Clock, EventLog, FakeLLM


def run(ns, config, ops):
    """A support queue in front of a cached model: get, on a miss call the model, then put."""
    clock = Clock()
    log = EventLog(clock)
    cache = ns["SemanticCache"](clock, log, **config)
    counts = {}

    def responder(messages, tools, model):
        tenant = messages[0]["content"].split("tenant=")[1]
        counts[tenant] = counts.get(tenant, 0) + 1
        return {"content": "%s#%d" % (tenant, counts[tenant])}

    llm = FakeLLM(responder=responder, clock=clock)
    answers = []
    for op in ops:
        if op["t"] > clock.now():
            clock.advance(op["t"] - clock.now())
        args = (op["tenant"], op.get("model", "support-model"), op["system"], op["query"])
        if op.get("warm"):
            cache.put(*(args + (op["answer"],)))      # cache warming from a curated FAQ
            continue
        ans = cache.get(*args)
        if ans is None:
            msgs = [{"role": "system", "content": op["system"] + " tenant=" + op["tenant"]}, {"role": "user", "content": op["query"]}]
            ans = llm.complete(msgs, model=args[1]).content
            cache.put(*(args + (ans,)))
        answers.append(ans)
    events = []
    for e in log.entries:
        e = dict(e)
        if "score" in e:
            e["score"] = round(float(e["score"]), 6)
        events.append(e)
    return {"answers": answers, "llm_calls": [[c["messages"][0]["content"].split("tenant=")[1], c["messages"][1]["content"]] for c in llm.calls],
            "events": events}
