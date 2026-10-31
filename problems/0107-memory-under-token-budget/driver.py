import copy

from gc_runtime import message_tokens


def run(ns, messages, budget, keep_last, reserve):
    """`summarize` is a recording fake; report the context, its size and every summarize call."""
    calls = []

    def summarize(msgs):
        calls.append(copy.deepcopy(list(msgs)))
        users = [m["content"] for m in msgs if m["role"] == "user"]
        return "%d earlier messages; customer first said: %s" % (len(msgs), users[0] if users else "nothing")

    ctx = ns["build_context"](messages, budget, keep_last, reserve, summarize)
    return {"context": ctx, "tokens": message_tokens(ctx), "summarize_calls": calls}
