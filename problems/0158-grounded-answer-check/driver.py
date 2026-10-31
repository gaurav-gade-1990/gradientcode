from gc_runtime import FakeLLM


def run(ns, answer, sources, min_groundedness, script):
    """script: the model's scripted rewrite turns (a list of {"content": ...})."""
    llm = FakeLLM(script)
    out = ns["grounded_answer"](answer, sources, llm, min_groundedness)
    reports = [{"groundedness": float(r["groundedness"]),
                "sentences": [{"text": s["text"], "citations": list(s["citations"]), "quotes": list(s["quotes"]), "status": s["status"]}
                              for s in r["sentences"]]} for r in out["reports"]]
    return {"status": out["status"], "final": out["final"], "reports": reports,
            "llm_messages": [c["messages"] for c in llm.calls]}
