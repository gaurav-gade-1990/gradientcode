Implement single-head attention the way **FlashAttention** (Dao et al., 2022) computes it: stream over the keys and values one block at a time with an **online softmax**, never holding the full `(T_q, T_k)` score matrix.

$$
O = \operatorname{softmax}\!\left(\frac{Q K^\top}{\sqrt{d}}\right) V
$$

Split the keys into blocks of `block_size` consecutive rows: block $b$ holds keys `b*block_size` up to (not including) `(b+1)*block_size`. The last block may be shorter. There are $n_b = \lceil T_k / \texttt{block\_size} \rceil$ blocks.

For every query row $i$ keep a running max $m_i$, a running normalizer $\ell_i$ and an unnormalized output $a_i$. Start with $m_i = -\infty$, $\ell_i = 0$, $a_i = 0$. For each block $b$ in order, with scaled scores $s_{ij} = q_i \cdot k_j / \sqrt{d}$ for the keys $j$ in the block:

$$
\begin{aligned}
m_i^{new} &= \max\big(m_i,\ \max_{j \in b} s_{ij}\big) \\
\ell_i &\leftarrow e^{m_i - m_i^{new}}\, \ell_i + \sum_{j \in b} e^{s_{ij} - m_i^{new}} \\
a_i &\leftarrow e^{m_i - m_i^{new}}\, a_i + \sum_{j \in b} e^{s_{ij} - m_i^{new}}\, v_j \\
m_i &\leftarrow m_i^{new}
\end{aligned}
$$

After the last block, $o_i = a_i / \ell_i$.

So after block $b$, $m_i$ is the max of $s_{ij}$ over every key seen so far, and $\ell_i = \sum_{j \text{ seen}} e^{s_{ij} - m_i}$.

**Causal mode.** If `causal` is `True` (then $T_q = T_k$), query $i$ may only see keys $j \le i$, using **global** positions. Masked keys are left out of both the max and the sums. A block that is entirely masked for row $i$ leaves $m_i$, $\ell_i$ and $a_i$ unchanged. Key `0` is always in block `0`, so every row has a finite $m_i$ after the first block.

Return a tuple `(O, m_hist, l_hist)`:

- `O`: shape `(T_q, d_v)`, the attention output
- `m_hist`: shape `(n_b, T_q)`; row `b` is $m$ for every query **after** processing block `b`
- `l_hist`: shape `(n_b, T_q)`; row `b` is $\ell$ after processing block `b`

**Constraints**

- `Q` has shape `(T_q, d)`, `K` has shape `(T_k, d)`, `V` has shape `(T_k, d_v)`
- `1 <= T_q, T_k <= 64`, `1 <= d, d_v <= 32`
- `1 <= block_size <= T_k`
- Scores can be large (`|s| <= 3e3`), so nothing may be exponentiated without subtracting the running max
