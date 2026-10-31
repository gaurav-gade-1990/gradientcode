# Problem catalog

The id, slug, difficulty and one-line spec for every problem. Writers may refine a spec, but they keep the id, slug and difficulty.

## numpy: NumPy & Linear Algebra (1–9)
- 0001 stable-softmax, Easy. Done (seed).
- 0002 log-sum-exp, Easy. `logsumexp(x, axis=-1)`, stable, keepdims=False.
- 0003 cosine-similarity-matrix, Easy. `(n,d),(m,d) -> (n,m)`; zero vectors give similarity 0.
- 0004 pairwise-euclidean-distances, Medium. Vectorized `(n,d),(m,d)->(n,m)` with the `||a||²-2ab+||b||²` trick, clipped at 0. A large hidden case catches loops.
- 0005 one-hot-encoding, Easy. `labels, num_classes -> (n,C)` float.
- 0006 covariance-matrix, Easy. Sample covariance (ddof=1) of `(n,d)` with features in columns. Wrong: ddof=0.
- 0007 standardize-features, Easy. Fit z-score on train, apply to test; constant columns stay 0 (std treated as 1).
- 0008 sliding-window-view, Medium. 1-D signal, `window`, `stride -> (num_windows, window)`; no partial windows.
- 0009 top-k-per-row, Medium. `(n,m), k ->` values and indices sorted descending; ties go to the lower index.

## classic-ml: Classic ML (10–24)
- 0010 linear-regression-closed-form, Easy. Normal equation with a bias column; use `lstsq`/solve.
- 0011 linear-regression-gradient-descent, Easy. Fixed lr and iterations, zero init, MSE gradient; returns w, b.
- 0012 ridge-regression, Medium. Closed form; the bias is not regularized (center the data, or augment without penalizing the bias).
- 0013 logistic-regression-gd, Medium. Batch GD, zero init, stable sigmoid, mean BCE grad; returns w, b.
- 0014 perceptron, Easy. Online updates in the given order for given epochs; labels ±1; returns w, b.
- 0015 linear-svm-hinge-sgd, Medium. Pegasos-style full-batch subgradient on hinge loss plus L2; fixed schedule.
- 0016 k-nearest-neighbors, Medium. Majority vote; ties go to the nearest neighbor's label among the tied classes (spell this out).
- 0017 k-means, Medium. Lloyd's algorithm from given initial centroids until convergence or max_iter; an empty cluster keeps its centroid.
- 0018 k-means-plus-plus-init, Medium. D² sampling with provided uniform randoms `u` (use inverse-CDF with searchsorted).
- 0019 gaussian-naive-bayes, Medium. Fit priors, means and vars (+ var_smoothing); predict via log-probs.
- 0020 gini-impurity-best-split, Medium. Best (feature, threshold) over midpoints by weighted Gini; deterministic tie-break.
- 0021 decision-tree-classifier, Hard. CART with Gini, max_depth, min_samples_split; return predictions for X_test.
- 0022 pca, Medium. Center, covariance eigendecomposition, top-k components; sign fixed so the largest-abs entry of each component is positive; return projected data and explained variance ratio.
- 0023 power-iteration, Medium. Dominant eigenvalue and eigenvector of a symmetric matrix from a given start vector, with a fixed iteration count or tolerance; sign-invariant checker.
- 0024 gmm-em, Hard. EM for a diagonal (or full) GMM from given initial params for n_iter steps; return means, covariances, weights, log-likelihood history.

## metrics: Metrics & Evaluation (25–33)
- 0025 confusion-matrix, Easy. `y_true, y_pred, num_classes -> (C,C)` int; rows are true labels.
- 0026 precision-recall-f1, Easy. Macro P/R/F1 for multiclass; 0 when the denominator is 0.
- 0027 roc-auc, Medium. Rank-based (Mann–Whitney) AUC with tie handling (ties count 0.5).
- 0028 average-precision, Medium. sklearn-style AP (step-wise sum over thresholds).
- 0029 binary-log-loss, Easy. Mean BCE with clipping eps.
- 0030 regression-metrics, Easy. Returns dict `{mse, rmse, mae, r2}`.
- 0031 stratified-k-fold, Medium. Deterministic split: per class, indices in order are dealt round-robin to folds; return fold id per sample.
- 0032 ndcg-at-k, Medium. Graded relevance, gains `2^rel - 1`, log2 discount; 0 if IDCG is 0.
- 0033 expected-calibration-error, Medium. Equal-width bins; weighted |acc - conf|.

## nn: Neural Network Blocks (34–47)
- 0034 activation-functions, Easy. Return dict of sigmoid, tanh, relu, leaky_relu, gelu(tanh approx) values and derivatives.
- 0035 dense-layer-forward-backward, Medium. `forward(x, W, b)` and backward given dout -> dx, dW, db (driver or a single function returning all).
- 0036 softmax-cross-entropy-gradient, Medium. Mean CE loss and dlogits from logits plus int labels; stable.
- 0037 weight-initialization, Easy. Xavier-uniform and He-normal limits/std given fan_in/fan_out, scaling provided standard random draws.
- 0038 inverted-dropout, Easy. Given `u`, keep where `u < keep_prob`, scale by 1/keep_prob; eval mode returns x.
- 0039 batchnorm-forward, Medium. Training forward with running-stat update (momentum); return out, new running mean/var.
- 0040 batchnorm-backward, Hard. dx, dgamma, dbeta from dout and cache inputs (x, gamma, eps); compact formula.
- 0041 layernorm-forward-backward, Medium. Over the last dim; return out plus dx, dgamma, dbeta.
- 0042 im2col, Medium. `(N,C,H,W)`, kernel, stride, pad -> columns `(C*kh*kw, N*out_h*out_w)` in a specified order.
- 0043 conv2d-forward, Medium. NCHW, weights `(F,C,kh,kw)`, bias, stride, pad.
- 0044 conv2d-backward, Hard. dx, dw, db for the conv above.
- 0045 max-pool-forward-backward, Medium. Forward plus backward routing to the argmax (first max on ties).
- 0046 numerical-gradient-check, Easy. Central differences for f given as an expression of a known family (driver), returning grad plus relative error vs an analytic grad.
- 0047 train-mlp-on-xor, Medium. 2-layer tanh/sigmoid MLP, given init weights, lr, epochs, full-batch GD; return final loss and predictions.

## optim: Optimizers & Training (48–55)
- 0048 sgd-momentum, Easy. `v = mu*v - lr*g; p += v` (PyTorch-style variant stated precisely).
- 0049 nesterov-momentum, Medium. Nesterov update in the given formulation.
- 0050 adagrad, Easy.
- 0051 rmsprop, Easy.
- 0052 adam, Medium. Done (seed).
- 0053 adamw, Medium. Decoupled weight decay, applied as in PyTorch AdamW.
- 0054 cosine-schedule-with-warmup, Easy. lr at each step for linear warmup, then cosine to min_lr.
- 0055 gradient-norm-clipping, Easy. Global L2 norm over a list of arrays; scale only if norm > max_norm; return clipped list plus the original norm.

## autograd: Autograd (56–59)
- 0056 scalar-autograd-value, Hard. Done (seed).
- 0057 topological-sort-backward, Medium. Given a DAG of ops (list of nodes with op type and parents) and values, compute all grads by reverse topo order.
- 0058 unbroadcast-gradient, Medium. Sum a gradient down to the original input shape after NumPy broadcasting.
- 0059 tensor-autograd-matmul, Hard. A `Tensor` class with matmul, add (broadcast), relu, sum, mean and backward (driver builds a small MLP loss).

## transformers: Sequence Models & Transformers (60–72)
- 0060 rnn-cell-forward, Easy. Run a tanh RNN over a sequence; return all hidden states.
- 0061 lstm-cell-forward, Medium. One LSTM step with gates in i,f,g,o order from a stacked weight matrix; return h, c.
- 0062 gru-cell-forward, Medium. PyTorch GRU formulation (r, z, n order) for a sequence.
- 0063 scaled-dot-product-attention, Medium. Optional boolean mask (True = keep); stable softmax; batched leading dims.
- 0064 causal-attention-mask, Easy. Build an additive mask (0 / -inf) for `T_q, T_k` with an offset (for a KV cache).
- 0065 multi-head-attention, Medium. Projections W_q, W_k, W_v, W_o, split heads, attend, merge.
- 0066 sinusoidal-positional-encoding, Easy. `(max_len, d_model)` per "Attention Is All You Need".
- 0067 rotary-position-embedding, Medium. Apply RoPE (half-split convention, stated) to q/k at given positions.
- 0068 transformer-block-forward, Hard. Pre-LN block: LN -> causal MHA -> residual -> LN -> GELU MLP -> residual, all weights given.
- 0069 kv-cache-decoding, Hard. Driver: a class with `step(x_t)` that appends K/V and attends over the cache; outputs must match full causal attention.
- 0070 beam-search, Medium. Over a given log-prob table function (driver supplies `next_logprobs(prefix)`); beam width, length, EOS handling, deterministic ties.
- 0071 top-k-top-p-sampling, Medium. Temperature, then top-k, then top-p filtering, renormalize, and sample with the given `u` via inverse CDF; return the token and filtered probs.
- 0072 perplexity, Easy. From token log-probs with a padding mask.

## llm: LLM Internals (73–81)
- 0073 bpe-tokenizer-training, Hard. Learn `num_merges` merges from a word-frequency dict; ties broken lexicographically; return merges plus the encoding of test words.
- 0074 rmsnorm, Easy.
- 0075 swiglu-ffn, Easy. `(silu(x W1) * (x W3)) W2`.
- 0076 grouped-query-attention, Medium. n_q heads share n_kv K/V heads (repeat_interleave semantics), causal.
- 0077 online-softmax-attention, Hard. FlashAttention-style tiled attention over K/V blocks with a running max and sum; must match exact attention. A driver or checker forbids materializing the full score matrix by counting? Keep it simple: grade outputs and also return per-block running max.
- 0078 int8-absmax-quantization, Medium. Per-row absmax quantize to int8 (round half away from zero, specified), dequantize; return q, scales, dequantized.
- 0079 lora-forward-and-merge, Easy. `y = xW + (alpha/r) x A B`; merge into W'.
- 0080 moe-top-k-routing, Medium. Softmax router, top-k experts per token, renormalized gates, combine expert outputs (experts given as weight matrices), plus the Switch-style load-balancing loss.
- 0081 speculative-decoding-acceptance, Hard. Given draft and target distributions per position, draft tokens and uniforms, accept/reject by min(1, p/q) and resample from norm(max(0, p-q)) with a given uniform; return accepted tokens.

## retrieval: Retrieval & NLP (82–86)
- 0082 tf-idf, Medium. Smooth idf as in sklearn defaults (`log((1+n)/(1+df))+1`), L2 row-normalized; vocabulary sorted.
- 0083 bm25, Medium. Okapi BM25 scores of each doc for a query (k1, b given; idf per the Lucene formula).
- 0084 top-k-cosine-retrieval, Easy. Return the top-k doc indices and scores per query; ties go to the lower index.
- 0085 maximal-marginal-relevance, Medium. Greedy MMR selection with lambda.
- 0086 skip-gram-negative-sampling, Hard. Loss plus gradients w.r.t. center vector, context vector and negative vectors.

## rl: Reinforcement Learning (87–91)
- 0087 epsilon-greedy-bandit, Easy. Run T steps with provided uniforms and reward draws; incremental mean updates; ties go to the lowest arm.
- 0088 value-iteration, Medium. Tabular MDP `P[s,a,s']`, `R[s,a]`, gamma, tol; return V and greedy policy.
- 0089 q-learning-update, Easy. Apply a list of transitions (s,a,r,s',done) to a Q table.
- 0090 gae-advantages, Medium. GAE(γ, λ) with done masks and a bootstrap value; return advantages and returns.
- 0091 reinforce-loss-gradient, Medium. Discounted returns, normalized baseline, policy-gradient loss and its gradient w.r.t. logits for a softmax policy.
