Implement a **TF-IDF** vectorizer that matches scikit-learn's `TfidfVectorizer` defaults (`smooth_idf=True`, `norm="l2"`, raw-count tf).

You get `docs`, a list of `n` strings. Tokenize each one as `doc.lower().split()`: lowercase it, then split on runs of whitespace. Punctuation is not stripped, so `"cat."` and `"cat"` are different tokens.

1. The **vocabulary** is the sorted list (Python string order) of every distinct token across all documents. Token `vocab[j]` owns column `j`.
2. $\text{tf}(d, t)$ is the number of times token $t$ appears in document $d$.
3. $\text{df}(t)$ is the number of documents that contain $t$ at least once.
4. The smoothed inverse document frequency, with the natural log, is

$$
\text{idf}(t) = \ln\frac{1 + n}{1 + \text{df}(t)} + 1
$$

5. Set $X_{d,t} = \text{tf}(d, t)\cdot \text{idf}(t)$, then divide each row by its L2 norm. A row whose norm is `0` (an empty document) stays all zeros.

Return a tuple `(vocab, X)`: `vocab` is a list of strings, and `X` is a float array of shape `(n, len(vocab))`.

**Constraints**

- `1 <= n <= 200`
- At least one document has a token
- Documents may be empty or contain only whitespace
