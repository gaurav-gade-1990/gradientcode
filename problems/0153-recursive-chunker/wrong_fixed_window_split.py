import re


def chunk_document(text, max_tokens, overlap_tokens):
    # A fixed sliding window: ignores paragraphs and sentences, so chunks cut policies mid-sentence.
    spans = [(m.start(), m.end()) for m in re.finditer(r"\w+|[^\w\s]", text)]
    chunks = []
    i = 0
    while i < len(spans):
        j = min(i + max_tokens, len(spans))
        s, e = spans[i][0], spans[j - 1][1]
        chunks.append({"start": s, "end": e, "tokens": j - i, "text": text[s:e]})
        if j == len(spans):
            break
        i = j - overlap_tokens
    return chunks
