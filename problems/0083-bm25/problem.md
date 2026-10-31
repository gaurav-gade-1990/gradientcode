Score every document against a query with **Okapi BM25**, using the Lucene idf.

Tokenize each document and the query as `s.lower().split()`: lowercase, then split on runs of whitespace. Punctuation is not stripped. Let $N$ be the number of documents, $|d|$ the number of tokens in document $d$, and $\text{avgdl}$ the mean of $|d|$ over all $N$ documents (empty documents included).

For a token $q$, $\text{df}(q)$ is the number of documents that contain it, and $f(q, d)$ is its count in $d$. With the natural log,

$$
\text{idf}(q) = \ln\left(1 + \frac{N - \text{df}(q) + 0.5}{\text{df}(q) + 0.5}\right)
$$

$$
\text{score}(d) = \sum_{q \in \text{query tokens}} \text{idf}(q)\cdot\frac{f(q,d)\,(k_1 + 1)}{f(q,d) + k_1\left(1 - b + b\,\dfrac{|d|}{\text{avgdl}}\right)}
$$

The sum runs over the query's tokens **with repeats**: a token that appears twice in the query contributes twice. A query token that is in no document contributes `0`.

Return a float array of shape `(N,)`, one score per document, in input order.

**Constraints**

- `1 <= N <= 200`
- At least one document has a token, so `avgdl > 0`
- `k1 > 0`, `0 <= b <= 1`
- The query may be empty, in which case every score is `0`
