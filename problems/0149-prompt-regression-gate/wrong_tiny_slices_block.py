# Lets a 2-case slice block the PR: one flaky case is a 50-point drop.
from gc_runtime import GCError


def _passes(llm, prompt, case):
    messages = [{"role": "system", "content": prompt}, {"role": "user", "content": case["input"]}]
    try:
        text = (llm.complete(messages).content or "").lower()
    except GCError:
        return False
    return all(e.lower() in text for e in case["expect"])


def _drop_blocks(base, new, n, max_drop_pp):
    return 100 * (base - new) > max_drop_pp * n


def gate_prompt_change(llm, new_prompt, golden, baseline, policy):
    results = {c["id"]: _passes(llm, new_prompt, c) for c in golden}
    reasons = ["must_pass:%s" % c["id"] for c in golden
               if c["must_pass"] and baseline[c["id"]] and not results[c["id"]]]

    n = len(golden)
    b = sum(1 for c in golden if baseline[c["id"]])
    p = sum(1 for c in golden if results[c["id"]])
    if _drop_blocks(b, p, n, policy["max_drop_pp"]):
        reasons.append("overall")

    slices = {}
    for tag in sorted({t for c in golden for t in c["tags"]}):
        ids = [c["id"] for c in golden if tag in c["tags"]]
        bs = sum(1 for i in ids if baseline[i])
        ps = sum(1 for i in ids if results[i])
        gated = len(ids) >= policy["min_slice"]
        slices[tag] = {"n": len(ids), "baseline": bs / len(ids), "new": ps / len(ids), "gated": gated}
        if _drop_blocks(bs, ps, len(ids), policy["max_drop_pp"]):
            reasons.append("slice:%s" % tag)

    return {
        "decision": "block" if reasons else "pass",
        "reasons": reasons,
        "results": results,
        "pass_rate": {"baseline": b / n, "new": p / n},
        "slices": slices,
    }
