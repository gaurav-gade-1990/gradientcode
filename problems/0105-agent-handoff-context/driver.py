import copy

from gc_runtime import FakeLLM


def run(ns, transcript, specialist, summary):
    """The summarizer is scripted to answer with `summary`; report what it was sent and what was returned."""
    llm = FakeLLM([{"content": summary}])
    original = copy.deepcopy(transcript)
    out = ns["handoff"](transcript, specialist, llm)
    return {
        "transcript": out,
        "summarizer_calls": [c["messages"] for c in llm.calls],
        "input_unchanged": transcript == original,
    }
