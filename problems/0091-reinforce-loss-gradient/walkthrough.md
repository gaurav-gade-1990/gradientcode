## 1. What the problem is really asking

REINFORCE is the original policy-gradient algorithm: play an episode, then make the actions that led to above-average returns more likely and the rest less likely. PPO, and the RL step of RLHF, are refinements of exactly this update. Writing the loss and its gradient by hand shows what autodiff computes when you call `loss.backward()` on a policy-gradient objective.

Under the story this is **a backward discounted sum, a normalisation, a stable log-softmax, and the softmax cross-entropy gradient weighted per row**. The gradient has the same form as classification (problem 36, softmax-cross-entropy-gradient), with each row's one-hot target scaled by how good that step's return was.

The judge compares the loss (a Python float) and the `(T, A)` gradient with `rtol=1e-6`.

## 2. Understand the inputs

| name | shape | what it is | how you use it |
|---|---|---|---|
| `logits` | `(T, A)` | the policy's scores $z_t$ at each step | log-softmax per row |
| `actions` | `(T,)` int | the action taken, $a_t$ | picks one log-probability per row |
| `rewards` | `(T,)` | $r_t$ | discounted into returns |
| `gamma` | float in `[0, 1]` | discount | $G_t = r_t + \gamma G_{t+1}$ |
| `eps` | float, default `1e-8` | guards the division by $\sigma$ | added to the std |
| return | float, `(T, A)` | `loss, grad` | $\partial L / \partial z$ |

The details that are easy to miss:

- **Returns sum future rewards**, so the loop runs backward from the last step.
- **Population std** (`ddof=0`), which is `np.std`'s default. `ddof=1` gives a different scale, and `nan` when `T = 1`.
- **$\hat G$ is a constant** in the gradient. No gradient flows through the normalisation.
- **Logits up to `1e3`** overflow `np.exp`. Use a max-shifted log-softmax, never `log(softmax(z))`.

## 3. The math

**Returns.** $G_t = \sum_{k=t}^{T-1} \gamma^{k - t} r_k$. Splitting off the first term gives the backward recursion $G_t = r_t + \gamma G_{t+1}$ with $G_T = 0$.

**Why this loss.** The policy-gradient theorem says the gradient of the expected return $J(\theta)$ is

$$\nabla_\theta J = \mathbb{E}\Big[\sum_t G_t\, \nabla_\theta \log \pi_\theta(a_t \mid s_t)\Big].$$

It comes from the log-derivative trick: $\nabla_\theta \mathbb{E}_{\tau \sim p_\theta}[R(\tau)] = \mathbb{E}[R(\tau)\, \nabla_\theta \log p_\theta(\tau)]$, and the environment's transition probabilities in $\log p_\theta(\tau)$ don't depend on $\theta$, so only the $\log \pi$ terms survive. Autodiff needs a scalar to minimise whose gradient is minus that estimate:

$$L = -\frac{1}{T}\sum_{t=0}^{T-1} \hat G_t \log\pi(a_t \mid s_t).$$

**The baseline.** Subtracting a constant $b$ from every return doesn't change the expected gradient, because $\mathbb{E}_{a \sim \pi}[\nabla \log \pi(a)] = \sum_a \pi(a) \frac{\nabla \pi(a)}{\pi(a)} = \nabla \sum_a \pi(a) = \nabla 1 = 0$. It does cut variance. The normalisation $\hat G_t = (G_t - \mu)/(\sigma + \varepsilon)$ uses the episode mean as the baseline and also rescales, so step sizes are similar across episodes with different reward scales. (Using the episode's own mean introduces a small bias; it's the standard practical choice.)

**Stable log-softmax.** With $m_t = \max_j z_{tj}$,

$$\log\pi(j \mid s_t) = z_{tj} - \log\sum_{j'} e^{z_{tj'}} = (z_{tj} - m_t) - \log\sum_{j'} e^{z_{tj'} - m_t}.$$

The $m_t$ cancels, and every exponent is now $\le 0$, with at least one equal to 0, so the sum lies in $[1, A]$ and its log is finite.

**The gradient.** Write $p_t = \operatorname{softmax}(z_t)$. Differentiate $\log p_t(a) = z_{ta} - \log\sum_{j'} e^{z_{tj'}}$ with respect to $z_{tj}$:

$$\frac{\partial \log p_t(a)}{\partial z_{tj}} = \mathbb{1}[j = a] - \frac{e^{z_{tj}}}{\sum_{j'} e^{z_{tj'}}} = \mathbb{1}[j = a] - p_t(j).$$

As a vector, $\nabla_{z_t} \log p_t(a_t) = e_{a_t} - p_t$, with $e_{a}$ the one-hot vector. Row $t$ of $L$ is $-\frac{1}{T} \hat G_t \log p_t(a_t)$, and $z_t$ appears in no other row, so

$$\frac{\partial L}{\partial z_t} = \frac{\hat G_t}{T}\,\big(p_t - e_{a_t}\big) \in \mathbb{R}^A.$$

**Reading it.** If $\hat G_t > 0$, the gradient on the taken action's logit is $\frac{\hat G_t}{T}(p_t(a_t) - 1) < 0$, so gradient descent **raises** that logit. If $\hat G_t < 0$, it lowers it. Each row sums to 0, because $p_t$ and $e_{a_t}$ both sum to 1: the update moves probability between actions, never adds total logit.

**Constant returns.** If every $G_t$ is equal, $\sigma = 0$ and $\hat G_t = 0 / \varepsilon = 0$. The loss and gradient are exactly 0: no action did better than any other.

## 4. Trace an example by hand

**Example 2:** `T = 3`, `A = 2`, `gamma = 0.5`.

```python
logits  = [[0, 0], [1, -1], [0, 2]]     # (T, A) = (3, 2)
actions = [0, 0, 1]
rewards = [1, 0, 0]
```

| step | quantity | value |
|---|---|---|
| returns, backward | `G = [1 + 0.5·0, 0 + 0.5·0, 0]` | `[1, 0, 0]` |
| mean, population std | `μ = 0.3333`, `σ = 0.4714` | |
| normalised | `Ĝ = (G − μ) / σ` | `[1.4142, -0.7071, -0.7071]` |
| policy | `p` per row | `[0.5, 0.5]`, `[0.8808, 0.1192]`, `[0.1192, 0.8808]` |
| chosen log-probs | `log p_t(a_t)` | `[-0.6931, -0.1269, -0.1269]` |

The loss is `-(1/3) · (1.4142 · (-0.6931) + (-0.7071) · (-0.1269) · 2) = -(1/3) · (-0.9803 + 0.1795) = 0.266918`.

The gradient, row by row, is `(p_t − e_{a_t}) · Ĝ_t / 3`:

| t | `p_t − e_{a_t}` | `Ĝ_t / 3` | `grad[t]` |
|---|---|---|---|
| 0 | `[-0.5, 0.5]` | `0.4714` | `[-0.2357, 0.2357]` |
| 1 | `[-0.1192, 0.1192]` | `-0.2357` | `[0.0281, -0.0281]` |
| 2 | `[0.1192, -0.1192]` | `-0.2357` | `[-0.0281, 0.0281]` |

Step 0 earned the reward, so descent raises logit 0 there. Steps 1 and 2 came after the reward and get negative $\hat G$, so their chosen actions are pushed down.

**Example 1** has `gamma = 1` and `rewards = [0, 0, 1]`, so `G = [1, 1, 1]`, `σ = 0`, and the loss and gradient are all zeros. Accumulating forward instead gives `G = [0, 0, 1]` and a loss of `-0.133459`.

**The hidden case "large logits"** has rows like `[1000, 0, -1000]` with action 2. The stable log-probabilities of the chosen actions are `[-2000, -1600, -1.0986, -1.3133]`, and the loss is `-759.1`. A naive `np.exp(1000)` is `inf`, and the loss becomes `nan`.

## 5. Plan before you code

```
G = backward discounted sum of rewards                    # (T,)
G_hat = (G - G.mean()) / (G.std() + eps)                  # (T,)
z = logits - row max                                      # (T, A)
log_probs = z - log(sum(exp(z)) per row)                  # (T, A)
loss = -mean(G_hat * log_probs[t, actions[t]])
grad = exp(log_probs); subtract 1 at each taken action;  # (T, A)
grad *= G_hat[:, None] / T
```

| line | shapes | broadcasting |
|---|---|---|
| `logits - logits.max(axis=1, keepdims=True)` | `(T, A) - (T, 1)` | one max per row |
| `log_probs[rows, actions]` | `(T,)`, `(T,)` → `(T,)` | paired fancy indexing |
| `grad *= G_hat[:, None] / T` | `(T, A) * (T, 1)` | one weight per row |

## 6. Build it one piece at a time

**Step 1: returns and normalisation.**

```python
G = np.zeros(T)
running = 0.0
for t in range(T - 1, -1, -1):
    running = rewards[t] + gamma * running     # G_t = r_t + gamma * G_{t+1}
    G[t] = running
G_hat = (G - G.mean()) / (G.std() + eps)       # (T,), population std
```

**Step 2: stable log-probabilities.**

```python
z = logits - logits.max(axis=1, keepdims=True)                 # (T, A), each row's max is 0
log_probs = z - np.log(np.exp(z).sum(axis=1, keepdims=True))   # (T, A)
```

`keepdims=True` keeps the max and the log-sum as `(T, 1)` columns so they subtract row by row.

**Step 3: the loss.**

```python
rows = np.arange(T)
loss = -np.mean(G_hat * log_probs[rows, actions])
```

`log_probs[rows, actions]` pairs `rows[i]` with `actions[i]`, giving the chosen action's log-probability per step. `log_probs[:, actions]` would give a `(T, T)` array instead.

**Step 4: the gradient.**

```python
grad = np.exp(log_probs)            # (T, A) = softmax probabilities, stable
grad[rows, actions] -= 1            # p_t - e_{a_t}
grad *= G_hat[:, None] / T          # weight each row by its normalised return
```

`np.exp(log_probs)` is the softmax computed from the stable log-probabilities, so it's safe even at logits of `1e3`. Here `grad[rows, actions] -= 1` is fine with fancy indexing: each row index appears once, so there are no repeated targets.

## 7. Full solution

```python
# NumPy for the returns, the stable log-softmax and the gradient
import numpy as np


# logits: (T, A), actions: (T,), rewards: (T,); returns (loss, dL/dlogits of shape (T, A))
def reinforce(logits: np.ndarray, actions: np.ndarray, rewards: np.ndarray, gamma: float = 0.99, eps: float = 1e-8) -> tuple:
    T = len(rewards)  # episode length
    G = np.zeros(T)  # (T,) discounted returns
    running = 0.0  # G_{t+1}, which is 0 after the last step
    # returns sum future rewards, so accumulate from the end of the episode
    for t in range(T - 1, -1, -1):
        running = rewards[t] + gamma * running  # G_t = r_t + gamma * G_{t+1}
        G[t] = running  # store this step's return
    # baseline and rescale with the population std; equal returns give all zeros
    G_hat = (G - G.mean()) / (G.std() + eps)

    # (T, A) shift each row so its max is 0; exp can then never overflow
    z = logits - logits.max(axis=1, keepdims=True)
    # (T, A) log-softmax: shifted logits minus the log of a sum that lies in [1, A]
    log_probs = z - np.log(np.exp(z).sum(axis=1, keepdims=True))
    rows = np.arange(T)  # row indices, paired with actions for fancy indexing
    # surrogate loss: minus the return-weighted log-probability of each taken action, averaged
    loss = -np.mean(G_hat * log_probs[rows, actions])

    grad = np.exp(log_probs)  # (T, A) softmax probabilities, computed stably
    grad[rows, actions] -= 1  # p_t - one_hot(a_t): the gradient of -log p_t(a_t)
    grad *= G_hat[:, None] / T  # (T, 1) weights: G_hat is a constant, and 1/T comes from the mean
    # a plain float loss and the per-logit gradient
    return float(loss), grad
```

## 8. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | loss `0`, gradient all zeros | equal returns: `σ = 0` and `eps` keeps `0 / eps = 0` |
| Example 2 | loss `0.266918`, `grad[0] = [-0.2357, 0.2357]` | backward returns, normalisation, gradient sign |
| single step | loss `0`, gradient zeros | `T = 1`: population std is 0; `ddof=1` would divide by zero |
| gamma = 0 | loss `-0.495575` | returns equal immediate rewards |
| short episode | loss `0.246709` | a short random episode with `A = 2` |
| large logits | loss `-759.1` | stable log-softmax at logits of `±1000` |
| custom eps | loss `-0.326734` | `eps = 0.5` actually changes the scale |
| many actions | `A = 10`, logits scaled by 3 | wider rows |
| long episode | `T = 1000` | the backward loop at length |

## 9. Complexity

The returns are one $O(T)$ pass, and the log-softmax, loss and gradient are $O(TA)$ each. Memory is $O(TA)$ for the log-probabilities and the gradient.

At scale the cost is in the policy network, not here: the gradient with respect to the logits is backpropagated through the network, so one update costs about one forward and one backward pass over the whole episode. The bigger practical problem is variance. A single episode's returns are a noisy signal, so production methods average over many parallel episodes, replace $\hat G$ with a learned-critic advantage (problem 90, gae-advantages), and clip how far one update can move the policy (PPO).

## 10. If you got Wrong Answer

- **Every gradient entry has the wrong sign (Example 2 gives `grad[0, 0] = 0.235702`).** You used $e_a - p$, the gradient of the objective, instead of $p - e_a$, the gradient of the loss (`wrong_grad_sign.py`). It passes Example 1 and "single step", where every $\hat G$ is 0.
- **`nan` loss on "large logits", everything else passes.** You computed `np.log(softmax)` from raw `np.exp(logits)` (`wrong_naive_softmax.py`).
- **Example 1 gives `-0.133459` instead of `0`.** You accumulated returns forward (`wrong_forward_returns.py`). It passes "single step" and "gamma = 0", where forward and backward agree.
- **Values slightly off everywhere and `nan` on "single step".** You used the sample std, `ddof=1` (`wrong_sample_std.py`).
- **The gradient is `T` times too large.** You dropped the `1/T` that comes from the mean in the loss.

## 11. Follow-ups an interviewer might ask

- *Why subtract a baseline if it doesn't change the expected gradient?* It lowers variance: without it, every action in a high-reward episode is pushed up, good or bad. With it, only the better-than-average ones are.
- *What's better than the episode mean as a baseline?* A learned value function $V(s_t)$, giving advantages $G_t - V(s_t)$, or GAE (problem 90, gae-advantages).
- *How does PPO change this loss?* It replaces $\log \pi$ with the probability ratio $\pi_\theta / \pi_{\text{old}}$, clipped to $[1 - \epsilon, 1 + \epsilon]$, so several gradient steps on the same batch can't move the policy too far.
- *Why add an entropy bonus?* Subtracting $\beta \cdot$ entropy from the loss keeps the policy from collapsing onto one action too early, which preserves exploration.
- *How is this used for language models?* Each sampled response is an episode and each token an action; the reward model scores the full response, and a KL penalty to the reference model keeps the policy close to where it started.
