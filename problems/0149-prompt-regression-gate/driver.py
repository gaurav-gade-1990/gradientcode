from gc_runtime import FakeLLM


def run(ns, new_prompt, golden, baseline, policy, responses):
    """`responses` maps a case input to the turn the scripted model returns for it."""
    def responder(messages, tools, model):
        user = [m for m in messages if m.get("role") == "user"]
        key = user[-1]["content"] if user else ""
        return responses.get(key, {"content": "Sorry, I can't help with that."})

    llm = FakeLLM(responder=responder)
    out = ns["gate_prompt_change"](llm, new_prompt, golden, baseline, policy)
    return {
        "report": out,
        "sent": [[m.get("role") + ": " + str(m.get("content")) for m in c["messages"]] for c in llm.calls],
    }
