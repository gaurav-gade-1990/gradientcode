from gc_runtime import FakeLLM


def run(ns, pairs, human, policy, replies):
    """`replies` is the judge's raw text for each call, in call order."""
    judge = FakeLLM([{"content": r} for r in replies], model="judge-model")
    report = ns["evaluate_with_judge"](judge, pairs, human, policy)
    return {
        "report": report,
        "calls": len(judge.calls),
        "prompts": [[m["content"] for m in c["messages"]] for c in judge.calls],
    }
