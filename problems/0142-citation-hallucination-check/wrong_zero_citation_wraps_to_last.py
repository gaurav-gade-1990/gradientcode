import re

from gc_runtime import tokenize

WORD = re.compile(r"\w+")
CITE = re.compile(r"\[(\d+)\]")


def _terms(text, stop):
    return {t.lower() for t in tokenize(text) if WORD.fullmatch(t) and t.lower() not in stop}


def check_citations(answer, passages, stopwords, tau):
    stop = {w.lower() for w in stopwords}
    sources = [_terms(p, stop) for p in passages]
    sentences, issues = [], []
    for i, sent in enumerate(s for s in re.split(r"(?<=[.!?])\s+", answer.strip()) if s):
        cites = list(dict.fromkeys(int(n) for n in CITE.findall(sent)))
        claim = _terms(CITE.sub(" ", sent), stop)
        row = {"citations": cites, "overlap": [], "status": None}
        if not claim:
            row["status"] = "no_claim"
        elif not cites:
            row["status"] = "uncited"
            issues.append({"sentence": i, "citation": None, "issue": "missing"})
        else:
            supported = False
            for n in cites:
                if n > len(passages):   # [0] -> passages[-1]
                    row["overlap"].append(None)
                    issues.append({"sentence": i, "citation": n, "issue": "out_of_range"})
                    continue
                ov = len(claim & sources[n - 1]) / len(claim)
                row["overlap"].append(ov)
                if ov >= tau:
                    supported = True
                else:
                    issues.append({"sentence": i, "citation": n, "issue": "unsupported"})
            row["status"] = "supported" if supported else "unsupported"
        sentences.append(row)
    graded = [r for r in sentences if r["status"] != "no_claim"]
    rate = 1.0 if not graded else sum(r["status"] == "supported" for r in graded) / len(graded)
    return {"sentences": sentences, "issues": issues, "supported_rate": rate}
