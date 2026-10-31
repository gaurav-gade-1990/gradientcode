import re

ASCII = {"“": '"', "”": '"', "‘": "'", "’": "'", "–": "-", "—": "-", " ": " "}


def norm(s):
    for k, v in ASCII.items():
        s = s.replace(k, v)
    return re.sub(r"\s+", " ", s.lower()).strip()


def check(text, sources):
    # Smart quotes from the model are not mapped, so quoted spans in curly quotes are never seen.
    normed = [norm(s) for s in sources]
    rows, supported = [], 0
    for sent in [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s]:
        cites = []
        for n in re.findall(r"\[(\d+)\]", sent):
            if int(n) not in cites:
                cites.append(int(n))
        quotes = [norm(q) for q in re.findall(r'"([^"]+)"', sent)]
        if not cites:
            status = "no_citation"
        elif any(n < 1 or n > len(sources) for n in cites):
            status = "bad_citation"
        elif not quotes:
            status = "no_quote"
        elif not all(any(q in normed[n - 1] for n in cites) for q in quotes):
            status = "unsupported_quote"
        else:
            status = "supported"
            supported += 1
        rows.append({"text": sent, "citations": cites, "quotes": quotes, "status": status})
    return {"groundedness": supported / len(rows) if rows else 0.0, "sentences": rows}


def grounded_answer(answer, sources, llm, min_groundedness):
    r1 = check(answer, sources)
    if r1["groundedness"] >= min_groundedness:
        return {"status": "grounded", "final": answer, "reports": [r1]}
    lines = ["Your answer failed the grounding check (groundedness %.2f, required %.2f)." % (r1["groundedness"], min_groundedness),
             "Rewrite it so every sentence cites a source like [1] and quotes it word for word in double quotes.",
             "Failed sentences:"]
    lines += ["- [%s] %s" % (s["status"], s["text"]) for s in r1["sentences"] if s["status"] != "supported"]
    lines.append("Sources:")
    lines += ["[%d] %s" % (i, s) for i, s in enumerate(sources, 1)]
    response = llm.complete([{"role": "user", "content": "\n".join(lines)}])
    r2 = check(response.content or "", sources)
    if r2["groundedness"] >= min_groundedness:
        return {"status": "repaired", "final": response.content, "reports": [r1, r2]}
    return {"status": "rejected", "final": None, "reports": [r1, r2]}
