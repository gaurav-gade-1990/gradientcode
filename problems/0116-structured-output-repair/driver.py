import copy

from gc_runtime import FakeLLM, GCError


def run(ns, script, messages, required):
    """Run get_structured against a scripted model; report the result and every transcript sent."""
    llm = FakeLLM(script, model="claude-haiku")
    original = copy.deepcopy(messages)
    try:
        result = ns["get_structured"](llm, messages, required)
        raised = None
    except GCError as e:
        result, raised = None, "%s: %s" % (type(e).__name__, e)
    return {
        "result": result,
        "raised": raised,
        "calls": [c["messages"] for c in llm.calls],
        "caller_messages_unchanged": messages == original,
    }
