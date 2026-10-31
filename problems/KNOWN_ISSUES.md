# Known problem issues

The walkthrough writers (2026-11) found about 80 issues. Most were tests that let a buggy solution pass, or cases whose names didn't match what they tested. Those are fixed: each gap now has a hidden case, plus a `wrong_*.py` that `scripts/check.py` proves the case catches. In the browser, every solution is Accepted and every wrong file fails (`PARITY=all`). This file lists what's left.

## Limits of the judge

The judge compares outputs, so a test case can't enforce these rules. Fixing them would mean changing `harness/harness.py`.

- **Modifying inputs in place, or keeping references to them.** The harness deep-copies every argument: 0007, 0039, 0047–0055, 0079, 0086, 0089, 0135, 0170, 0176.
- **"No Python loops" and complexity rules.** These are enforced only where a timed case exists: 0003, 0005, 0008, 0025, 0027, 0069.
- **Source bans.** For example, "don't call `np.cov`" in 0006.
- **Output dtype isn't compared:** 0005, 0025.
- **Overflow warnings aren't checked:** 0034, 0061.

## Not visible in the output

- **0171:** where the cache entry is evicted (by the first caller or in the flight) doesn't change any result.
- **0175:** a missing duplicate-add guard puts identical points in the same places, so routing doesn't change.
- **0129:** the `if victim is s: break` line in the reference can never change the result.
- **0125:** Example 3 (visible) can't catch the stale-result bug. The hidden cases do.

## Decisions for the owner

- **0080:** ranking experts by logits equals ranking by probability in exact math, but it fails "large router logits", where probabilities underflow to 0.0 and tie. The statement now says to rank by the float64 probabilities. Should logits-ranking be accepted?
- **0030:** a constant target is detected with exact `SS_tot == 0`, as scikit-learn does. A constant like 0.1 can give an `SS_tot` of about 1e-34, and then a hugely negative R². Should it use a tolerance?
- **0150:** training value `1` against serving value `True` counts as a match, because `1 == True` in Python. Should bool vs number be a skew?

## Design model answers

Inconsistencies in `solution.md`. No tests are involved.

- **0203:** the demo-to-opportunity rate is 5.8% in Scenario but an 18% baseline in Agents and Key Impact. The token cost says $85, but the lines add up to $86.
- **0206:** the Starter figure of about $0.028 per conversation doesn't reproduce (about $0.033). The per-tier costs assume an unstated Haiku cache price, about $0.01 read and $0.125 write per MTok.
- **0207:** the $501k baseline can't be derived from the prompt, which doesn't give a token split by model, but rubric item 1 asks for it.
- **0209:**
  - The gate cost has no token basis.
  - "About 90 GB a day" isn't derived.
  - The "3-point drop" standard error is computed per 30 minutes, but the window is 15 minutes. At 15 minutes it is about 2.7 SE, not 3.8.
- **0210:** rubric 5.3 asks for both PR sizes to be priced, but only the median is priced.
- **0211:** the $14.0k caching saving assumes every call hits the cache, but the text says 90%, which gives about $12.5k. Rubric 10.1 asks for dimensions, but none are given.
- **0212:** output tokens aren't stated. The latency table counts the draft note inside "to decision" (p95 is about 4.7 min without it).
- **0213:** output tokens aren't stated.
- **0214:**
  - The 136-GPU row assumes BF16 TP4 matches FP8 TP2 throughput, which isn't stated.
  - $56.5k vs $56.7k is a rounding difference.
- **0215:** "About 20 L4 on average" disagrees with the 16 given in sizing. The trap's $235k is ambiguous.
- **Prices given without an "assumed" label:**
  - 0201 and 0202: embedding prices.
  - 0202: Cohere Rerank.
  - 0205: Deepgram, and the Sonnet cache-write price.
  - 0206: KMS.
- **Wording:**
  - 0201: the Single View has 9 rows, but the Easy guideline is 6–8.
  - 0205: the burst wording is unclear.
