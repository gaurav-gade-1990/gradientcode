# Known problem issues

Found by the walkthrough writers (2026-11). None of these makes a reference solution wrong; most are tests that let a buggy solution pass, or misleading case names. Fixed so far: 0124 editorial cross-reference, and the example explanations in 0010, 0060 and 0085.

Recurring limits of the judge itself:
- "Don't modify the input in place" can't be tested: the harness deep-copies arguments (0007, 0039, 0047–0055, 0079, 0086, 0089, 0170, 0176).
- "No Python loops" and complexity limits are enforced only where a timed case exists (0003, 0005, 0008, 0025, 0027).
- Output dtype isn't compared (0005, 0025). Overflow warnings aren't checked (0034, 0061).

## 103-115
- 0103 "level barrier is slower": makespan 5.5 either way; wrong fails only via c start time. Misleading name.
- 0104 wrong_ties_by_list_order comment names wrong bug; wrong_any_skill_matches has extra and/or precedence bug.
- 0105 no test for assistant turn content "" whose tool calls survive.
- 0106 wrong_redoes_completed_steps caught only by Example 2.
- 0107 "small older turn..." and "reserve changes the cut" don't test what they claim (wrong files pass them); summary can exceed reserve.
- 0110 swapping two checks passes; blocked+approval_required unspecified.
- 0112 "child outlives parent" vs editorial wording.
- 0114 fractional id untested.
- 0115 "broken sibling" has none; message_delta "overwrites" wording vs merge behaviour.
## 129-141
- 0129 "self preemption" case doesn't self-preempt; `if victim is s: break` dead.
- 0130 -1e-9 rounding untested; unrealistic 31k-token request.
- 0131 price lists all newest-first; first-in-list bug passes.
- 0132 "small p99 sample" can't catch p99 bug.
- 0135 no value on cut point; input-mutation untested; editorial "near zero" claim wrong.
- 0137 sample_size and isinstance guard untested.
- 0138 log(v, gamma) passes.
- 0139 set-order bug caught only by hash luck.
- 0141 median-0 fallback untested.
## 155-167
- 0167 checking event id before signature verify passes tests.
## 168-180
- 0168 no user in bucket 0; allowlist u_0040 matches nobody.
- 0169 retry -1 accepted (only final retry graded).
- 0170 in-place sort accepted; some requests follow None cursor.
- 0171 no wrong file for model-in-key; evict-in-caller accepted.
- 0172 published message shape not graded.
- 0174 re-check-capacity producer accepted though event order can differ.
- 0175 no key on a ring point (bisect_right passes); duplicate-add guard untested.
- 0176 aliasing merge accepted.
- 0178 -1e-9, max(1,..), < vs <= all untested.
## Design 209-215 (model answers)
- 0209 gate cost has no token basis; Kafka 90 GB/day underived; "3-point drop" SE computed per 30 min but window is 15 min (2.7 SE, not 3.8).
- 0210 rubric 5.3 wants both PR sizes priced; answer prices median only.
- 0211 caching saving $14.0k assumes 100% hits vs stated 90% (~$12.5k); rubric 10.1 wants dims, none stated.
- 0212 output tokens unstated; latency table counts draft note in "to decision" (p95 ~4.7 min without).
- 0213 output tokens unstated.
- 0214 136 GPUs assumes BF16 TP4 = FP8 TP2 throughput (unstated); $56.5k vs $56.7k rounding.
- 0215 "20 L4 average" vs 16 in sizing; trap's $235k ambiguous.
## 31-45
- 0034 naive sigmoid accepted (no overflow-warning check).
- 0039 in-place modification untestable (judge deep-copies).
- 0031 "dealer carries over" doesn't test carry-over.
- 0033 "confidence on the edges" same under both bin rules.
- 0044/0037 weaker coverage on some cases (still caught).
## 1-15
- 0001 global-max shift passes (editorial calls it a mistake).
- 0002 np.squeeze without axis passes.
- 0005 dtype not checked (int/bool pass).
- 0006 np.cov ban unenforced; one-pass formula passes.
- 0007 in-place untestable; near-zero std column untested.
- 0009 unstable argsort fails only "wide rows".
- 0014 "xor never converges" can't catch strict <0 bug.
- 0015 <=1 passes though strict required.
- 0008 "one leftover sample" has none. No-loop rules unenforced in 0003/0005/0008.
## 46-60
- 0056 relu >= at 0 passes ("relu at zero" uses a-a).
- 0047-0055 no-in-place rule untestable (deep copies).
- 0052 "tiny gradients" barely catches eps-inside-sqrt.
- 0054 statement says min_lr at step T; W==T returns base_lr at T.
## Design 201-208
- 0203 5.8% vs 18% demo->opp contradiction; $85 vs $86.
- 0206 Starter $0.028 doesn't reproduce (~$0.033); Haiku cache price unstated.
- 0207 $501k baseline not derivable from prompt.
- Unlabelled non-model prices: 0201/0202 embeddings, 0202 Cohere Rerank, 0205 Deepgram + Sonnet cache-write, 0206 KMS.
- 0201 Single View 9 rows (Easy guideline 6-8); 0205 burst wording.
## 116-128
- 0117 missing-list sort untested. 0118 span sort untested.
- 0125 stale-success cases don't catch generation bug.
- 0122 "exactly fits"/"one over" names off by one.
## 16-30
- 0022 "negative pivot" doesn't exercise sign rule (LAPACK-dependent).
- 0025 no-loop and integer-dtype rules unenforced.
- 0027 O(n log n) not tested (max n 2000).
- 0030 ss_tot==0 rule fragile for non-exact constants.
- 0028 editorial says trapezoid "optimistic"; tests show lower.
- 0017 wrong_empty_cluster_nan actually zeros.
## 142-154
- 0154 best-rank tie-break never reaches top_n.
- 0147 insufficient-window-keeps-streaks rule untested.
- 0150 1 vs True not detected (Python equality) — spec question.
- 0153 "one token over" fits.
## 61-75
- 0073 "boundary trap" doesn't catch str.replace bug.
- 0065 stable softmax untested (max score ~475).
- 0069 no-recompute rule untestable by output.
- 0061 naive sigmoid passes "must not overflow".
- 0068 editorial GELU diff "about 1e-3" — measured max 4.7e-4.
## 76-91
- 0080 "large router logits": probabilities underflow to 0, so ranking by logits (same in exact math) fails.
- 0083 b = 1 with an empty document gives 0/0; untested.
- 0077 tests exceed the stated |s| <= 1e3 constraint.
- 0078 "divide, don't multiply by the reciprocal" untested.
