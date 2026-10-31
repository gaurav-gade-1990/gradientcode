import base64
import re

from gc_runtime import count_tokens

TOKEN_RE = re.compile(r"\w+|[^\w\s]")
MARKER_TOKENS = 5
CURSOR_TOKENS = 3


def _truncate_text(text, share):
    total = count_tokens(text)
    if total <= share:
        return text, False
    k = max(0, share - MARKER_TOKENS)
    end = 0
    for i, m in enumerate(TOKEN_RE.finditer(text)):
        if i == k:
            break
        end = m.end()
    marker = "[truncated %d tokens]" % (total - k)
    return (text[:end] + " " + marker if k else marker), True


def _page_list(rid, items, share):
    sizes = [count_tokens(x) for x in items]
    if sum(sizes) <= share:
        return list(items), False, None, sum(sizes)
    kept, used = 0, 0
    for s in sizes:
        if used + s > share - CURSOR_TOKENS:
            break
        kept += 1
        used += s
    cursor = base64.b64encode(("%s:%d" % (rid, kept)).encode()).decode()
    return list(items[:kept]), True, cursor, used + CURSOR_TOKENS


def budget_results(results, budget):
    errors = 0
    n = len(results)
    share = max(0, budget - errors) // n if n else 0
    out = []
    for r in results:
        entry = {"id": r["id"], "type": r["type"], "next_cursor": None}
        if r["type"] in ("error", "text"):
            content, cut = _truncate_text(r["content"], share)
            entry.update(content=content, truncated=cut, tokens=count_tokens(content))
        else:
            items, cut, cursor, used = _page_list(r["id"], r["content"], share)
            entry.update(content=items, truncated=cut, next_cursor=cursor, tokens=used)
        out.append(entry)
    return {"results": out, "total_tokens": sum(e["tokens"] for e in out)}
