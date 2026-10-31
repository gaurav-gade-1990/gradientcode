## 1. What the problem is really asking

A Mixture-of-Experts layer replaces one feed-forward block with `E` smaller ones and a **router** that sends each token to only `k` of them. Mixtral 8x7B has 8 experts and `k = 2`: it holds about 47B parameters but each token touches about 13B. Parameters grow with `E`, compute grows with `k`.

Under the story this is **a softmax, a stable top-k per row, a renormalisation, a gathered weighted sum, and a counting histogram**. None of those steps is hard on its own. What the judge punishes is getting the details of each one slightly wrong: the tie order, the gate normalisation, and which probabilities go into the loss.

The judge compares all four outputs. `y` and `gates` use `rtol=1e-6`, `expert_idx` must match exactly, including the order within each row, and `aux_loss` must be a float.

## 2. Understand the inputs

| name | shape | what it is | how you use it |
|---|---|---|---|
| `x` | `(T, d)` | token representations | routed and fed to experts |
| `W_router` | `(d, E)` | router weights | `x @ W_router` gives `(T, E)` logits |
| `experts` | `(E, d, d_out)` | one linear map per expert | `x_t @ experts[e]` |
| `k` | int | experts per token | top-k per row |
| return | `(T, d_out)`, `(T, k)` int, `(T, k)`, float | `y, expert_idx, gates, aux_loss` | |

The details that are easy to miss:

- **Order matters in `expert_idx`.** Row `t` lists experts by descending probability, and `gates[t, i]` belongs to `expert_idx[t, i]`.
- **Ties go to the lower index.** `np.argsort(-p, kind="stable")` does this. `np.argsort(p)[:, ::-1]` reverses the ties too and picks the higher index.
- **$P_e$ uses the full softmax**, over all `E` experts and all tokens, not the renormalised gates.
- **Underflowed probabilities tie.** With large logits, many probabilities are exactly `0.0`, and the tie rule decides which of them fills the remaining slots.

## 3. The math

**Router softmax.** For token $t$, logits $z_t = x_t W_{router} \in \mathbb{R}^E$ and

$$p_{t,e} = \frac{e^{z_{t,e} - \max_j z_{t,j}}}{\sum_{e'} e^{z_{t,e'} - \max_j z_{t,j}}}.$$

Subtracting the row max cancels top and bottom, and keeps every exponent $\le 0$.

**Gates.** Let $S_t$ be the chosen set. The gate for $e \in S_t$ is

$$g_{t,e} = \frac{p_{t,e}}{\sum_{e' \in S_t} p_{t,e'}} = \frac{e^{z_{t,e}} / Z_t}{\sum_{e' \in S_t} e^{z_{t,e'}} / Z_t} = \frac{e^{z_{t,e}}}{\sum_{e' \in S_t} e^{z_{t,e'}}},$$

where $Z_t$ is the full softmax denominator and cancels. So renormalising the top-k probabilities is the same as a softmax over only the top-k logits. The gates sum to 1, so the output is a convex combination of expert outputs.

**Output.** $y_t = \sum_{e \in S_t} g_{t,e}\, x_t\, \texttt{experts}[e]$, shape $(d_{out})$.

**Load balancing.** With $\mathbb{1}[\cdot]$ the indicator,

$$f_e = \frac{1}{Tk} \sum_{t} \mathbb{1}[e \in S_t], \qquad P_e = \frac{1}{T}\sum_t p_{t,e}, \qquad \mathcal{L}_{aux} = E \sum_e f_e P_e.$$

With uniform routing, $f_e = P_e = 1/E$ and $\mathcal{L}_{aux} = E \cdot E \cdot \tfrac{1}{E^2} = 1$.

**Why the loss has both terms.** $f_e$ comes from an argsort, so it has zero gradient almost everywhere. $P_e$ is smooth. Treat $f$ as a constant and differentiate with respect to one token's logits. From $\partial \mathcal{L}/\partial P_e = E f_e$ and $\partial P_e / \partial p_{t,e} = 1/T$,

$$\frac{\partial \mathcal{L}}{\partial p_{t,e}} = \frac{E}{T} f_e.$$

The softmax Jacobian is $\partial p_{t,e} / \partial z_{t,j} = p_{t,e}(\delta_{ej} - p_{t,j})$. Chain them:

$$\frac{\partial \mathcal{L}}{\partial z_{t,j}} = \frac{E}{T}\sum_e f_e\, p_{t,e}(\delta_{ej} - p_{t,j}) = \frac{E}{T}\, p_{t,j}\Big(f_j - \sum_e f_e\, p_{t,e}\Big).$$

Gradient descent lowers $z_{t,j}$ when expert $j$'s load $f_j$ is above the token's probability-weighted average load. Overloaded experts lose probability, which is exactly the balancing pressure you want.

## 4. Trace an example by hand

**Example 1:** `T = 2`, `E = 3`, `k = 2`. Expert 0 is the identity, expert 1 doubles, expert 2 negates.

| token | logits | `p` | `expert_idx` | `gates` |
|---|---|---|---|---|
| 0 | `[2, 0, 1]` | `[0.6652, 0.0900, 0.2447]` | `[0, 2]` | `[0.7311, 0.2689]` |
| 1 | `[0, 1, 0]` | `[0.2119, 0.5761, 0.2119]` | `[1, 0]` | `[0.7311, 0.2689]` |

Token 1 has a tie between experts 0 and 2 at `0.2119`; the lower index wins. The gates check the cancellation from section 3: token 0's gates are `softmax([2, 1]) = [0.7311, 0.2689]`.

The outputs, using `x_0 = [1, 0]` and `x_1 = [0, 1]`:

- `y_0 = 0.7311 · [1, 0] + 0.2689 · [-1, 0] = [0.4621, 0]`
- `y_1 = 0.7311 · [0, 2] + 0.2689 · [0, 1] = [0, 1.7311]`

The loss: slots go `[0, 2, 1, 0]`, so `f = [0.5, 0.25, 0.25]`. The column means of `p` are `P = [0.4386, 0.3331, 0.2283]`. Then `3 · (0.5·0.4386 + 0.25·0.3331 + 0.25·0.2283) = 1.0789`.

**Example 2** has `k = 1`, Switch-style: every gate is `1`. Token 2 is all zeros, so its logits are equal, and it goes to expert 0.

**The hidden case "large router logits"** scales `x` and `W_router` by 30. Token 0's shifted logits are `[-2169.5, -1001.7, 0, -837.8, -2361.5, -774.3]`, and the probabilities are `[0, 0, 1, 0, 0, 0]` exactly. The first pick is expert 2. The second is a five-way tie at `0.0`, which goes to expert 0, the lowest index. The judge expects `[2, 0]`. If you rank by logits instead of probabilities, you get `[2, 5]` (logit `-774.3` is the largest of the rest) and fail on `expert_idx`, even though the gate is `0` and `y` is the same.

## 5. Key idea: a stable descending sort

`np.argsort` sorts ascending. To get descending order with ties broken by the lower index, sort the **negated** values with a stable sort:

```python
np.argsort(-probs, axis=1, kind="stable")    # (T, E), descending, ties keep index order
```

A stable sort keeps equal keys in their original order, which is index order. Negating flips the comparison but not the tie order. Sorting `probs` and reversing with `[:, ::-1]` reverses the tie order too.

## 6. Plan before you code

```
probs  = stable softmax of x @ W_router                 # (T, E)
idx    = stable argsort of -probs, first k columns      # (T, k)
top    = probs gathered at idx                          # (T, k)
gates  = top / row sum of top                           # (T, k)
out    = every expert on every token                    # (T, E, d_out)
chosen = out gathered at idx                            # (T, k, d_out)
y      = sum over k of gates * chosen                   # (T, d_out)
f      = count of each expert in idx / (T k)            # (E,)
P      = column mean of probs                           # (E,)
aux    = E * sum(f * P)
```

## 7. Build it one piece at a time

**Step 1: the router softmax.**

```python
logits = x @ W_router                                  # (T, d) @ (d, E) -> (T, E)
logits = logits - logits.max(axis=1, keepdims=True)    # (T, E) - (T, 1)
probs = np.exp(logits)
probs = probs / probs.sum(axis=1, keepdims=True)       # (T, E) / (T, 1)
```

`keepdims=True` keeps the `(T, 1)` shape so the per-row max and sum broadcast across the `E` columns.

**Step 2: choose and renormalise.**

```python
expert_idx = np.argsort(-probs, axis=1, kind="stable")[:, :k]   # (T, k)
top = np.take_along_axis(probs, expert_idx, axis=1)             # (T, k)
gates = top / top.sum(axis=1, keepdims=True)                    # (T, k)
```

`take_along_axis` picks `probs[t, expert_idx[t, i]]` for every `(t, i)`. `probs[:, expert_idx]` would instead give a `(T, T, k)` array.

**Step 3: expert outputs and the combine.**

```python
expert_out = np.einsum("td,edo->teo", x, experts)                        # (T, E, d_out)
chosen = np.take_along_axis(expert_out, expert_idx[:, :, None], axis=1)  # (T, k, d_out)
y = np.sum(gates[:, :, None] * chosen, axis=1)                           # (T, d_out)
```

`expert_idx[:, :, None]` is `(T, k, 1)`; `take_along_axis` broadcasts it over the `d_out` axis. `gates[:, :, None]` is `(T, k, 1)`, so each gate scales its whole expert output row.

**Step 4: the balancing loss.**

```python
f = np.bincount(expert_idx.ravel(), minlength=E) / (T * k)   # (E,)
P = probs.mean(axis=0)                                       # (E,)
aux_loss = float(E * np.sum(f * P))
```

`minlength=E` matters: if the last expert gets no tokens, `bincount` would otherwise return a shorter array, and `f * P` would fail to broadcast.

## 8. Full solution

```python
# NumPy for the softmax, sorting, gathers and einsum
import numpy as np


# x: (T, d), W_router: (d, E), experts: (E, d, d_out); returns (y, expert_idx, gates, aux_loss)
def moe_forward(x, W_router, experts, k):
    # number of tokens and number of experts, for the loss normalisation
    T, E = x.shape[0], W_router.shape[1]
    # (T, E) router scores, one row per token
    logits = x @ W_router
    # subtract each row's max so exp cannot overflow; (T, 1) broadcasts across experts
    logits = logits - logits.max(axis=1, keepdims=True)
    # (T, E) unnormalised probabilities, the largest per row is exactly 1
    probs = np.exp(logits)
    # (T, E) full softmax over all experts; needed for both routing and P_e
    probs = probs / probs.sum(axis=1, keepdims=True)

    # (T, k) descending by probability; a stable sort of -probs keeps lower indices first on ties
    expert_idx = np.argsort(-probs, axis=1, kind="stable")[:, :k]
    # (T, k) probability of each chosen expert, aligned with expert_idx
    top = np.take_along_axis(probs, expert_idx, axis=1)
    # (T, k) renormalise so each token's gates sum to 1 (a softmax over the top-k logits)
    gates = top / top.sum(axis=1, keepdims=True)

    # (T, E, d_out): every expert applied to every token; simple, if wasteful for large E
    expert_out = np.einsum("td,edo->teo", x, experts)
    # (T, k, d_out): pull out the chosen experts' outputs; the (T, k, 1) index broadcasts over d_out
    chosen = np.take_along_axis(expert_out, expert_idx[:, :, None], axis=1)
    # (T, d_out): gate-weighted sum over the k chosen experts; (T, k, 1) gates scale whole rows
    y = np.sum(gates[:, :, None] * chosen, axis=1)

    # (E,) share of the T*k routing slots each expert got; minlength keeps unused experts at 0
    f = np.bincount(expert_idx.ravel(), minlength=E) / (T * k)
    # (E,) mean router probability over the FULL softmax, the differentiable half of the loss
    P = probs.mean(axis=0)
    # E * sum f_e P_e equals 1 under uniform routing; returned as a plain Python float
    aux_loss = float(E * np.sum(f * P))
    # outputs, choices, their weights, and the balancing penalty
    return y, expert_idx, gates, aux_loss
```

## 9. How the test cases map to the code

| test case | expected (selected values) | what it checks |
|---|---|---|
| Example 1 | `expert_idx = [[0, 2], [1, 0]]`, `aux_loss = 1.0789` | top-2, a tie to the lower index, the loss |
| Example 2 | `gates = [[1], [1], [1]]`, `aux_loss = 1.0` | `k = 1`; a zero token ties every expert and goes to 0 |
| top-2 of 8 | `aux_loss = 1.41625` | the standard top-2 setting |
| duplicate router columns | row 0 `expert_idx = [0, 2, 1]`, gates `[0.4932, 0.4932, 0.0137]` | exact ties between identical experts |
| k equals E | every expert chosen | renormalisation is a no-op; only the order matters |
| large router logits | row 0 `expert_idx = [2, 0]`, gates `[1, 0]` | stable softmax, and ties among probabilities that are exactly 0 |
| single token | `aux_loss = 1.70587` | `T = 1` |
| uniform router | every row `[0, 1]`, gates `[0.5, 0.5]`, `aux_loss = 1.0` | all-zero router: pure tie-breaking |
| many tokens top-4 of 16 | `aux_loss = 1.12481` | larger `E` and `k` |

Note the "uniform router" result: every token goes to experts 0 and 1, so the load is as unbalanced as it can be, yet `aux_loss` is `1.0`. Since $P_e = 1/E$ for every expert, $E \sum_e f_e P_e = \sum_e f_e = 1$ whatever $f$ is. The loss can only see imbalance when the router's probabilities also favour the overloaded experts.

## 10. Complexity

Routing costs $O(T d E)$ for the logits and $O(T E \log E)$ for the sort. This reference runs every expert on every token, $O(T E\, d\, d_{out})$, and stores a $(T, E, d_{out})$ tensor. A real MoE kernel groups tokens by expert and runs only $O(T k\, d\, d_{out})$: that factor $E / k$ is the whole point of MoE.

At scale the hard parts are elsewhere. Experts live on different devices, so routing becomes an all-to-all exchange of tokens. Each expert has a **capacity** of about $\text{factor} \cdot Tk/E$ slots, and tokens beyond it are dropped or rerouted. Load balancing keeps those drops rare.

## 11. If you got Wrong Answer

- **`aux_loss` is too high (Example 1 gives `1.125` instead of `1.07894`).** You built $P_e$ from the renormalised gates of the chosen experts (`wrong_aux_uses_gates.py`). Use the column mean of the full softmax.
- **`y` is smaller than expected and `gates` don't sum to 1 (Example 2 gives `0.880797` where `1` is expected).** You skipped the renormalisation (`wrong_no_renorm.py`).
- **`expert_idx` picks the higher index on ties (Example 2 token 2 goes to expert 1).** You sorted ascending and reversed (`wrong_ties_high_index.py`).
- **`nan` in "large router logits", everything else passes.** You exponentiated without subtracting the row max (`wrong_naive_softmax.py`).
- **Only "large router logits" fails, on `expert_idx[0, 1]` (expected `0`, got `5`).** You ranked by logits rather than probabilities. They agree except where probabilities underflow to equal zeros.

## 12. Follow-ups an interviewer might ask

- *What happens without the auxiliary loss?* The router collapses: a few experts get most tokens, train faster, get routed to more, and the rest sit idle. You pay for `E` experts and use two.
- *What's expert capacity and what happens on overflow?* Each expert takes at most `capacity_factor · T k / E` tokens per batch; extra tokens skip the layer through the residual connection. Training uses factors around 1.25.
- *Why softmax then top-k, rather than top-k then softmax?* For the gates they're identical (section 3). The full softmax still matters for $P_e$, which needs every expert's probability so unchosen experts get gradient.
- *What is the expert itself in a real model?* A full FFN, usually SwiGLU (problem 75, swiglu-ffn), not a single matrix.
- *How else can you balance load?* Router z-loss to keep logits small, expert-choice routing where experts pick their top tokens, or DeepSeek's per-expert bias that is nudged up or down by load without any auxiliary loss.
