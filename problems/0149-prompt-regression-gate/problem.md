Your support bot's system prompt lives in the repo. Every PR that edits it runs a CI job that replays a golden set against the new prompt and compares the results to the production prompt's last run. You're writing that gate.

Implement `gate_prompt_change(llm, new_prompt, golden, baseline, policy)`.

- `llm` is a `FakeLLM`. Call `llm.complete(messages)` and read `.content`.
- `golden` is a list of cases `{"id", "input", "expect", "tags", "must_pass"}`: `expect` is a list of substrings, `tags` a list of slice names, and `must_pass` a bool.
- `baseline` maps every case id to whether the production prompt passed it.
- `policy` is `{"max_drop_pp": int, "min_slice": int}`.

**Run the set.** For each case, in list order, call the model exactly once with

```
[{"role": "system", "content": new_prompt}, {"role": "user", "content": case["input"]}]
```

The case passes when every string in `expect` appears in the response content, compared case-insensitively (treat `None` content as `""`). If `complete` raises any `gc_runtime.GCError` (a 5xx, a timeout, a 429), the case fails and the run continues. Don't retry.

**Gate.** With `N` cases, `B` baseline passes and `P` new passes, these block the change:

| rule | blocks when | reason string |
|---|---|---|
| must-pass regression | `must_pass` is true, `baseline[id]` is true and the case fails now | `"must_pass:<id>"` |
| overall drop | `100 * (B - P) > max_drop_pp * N` | `"overall"` |
| slice drop | the slice has `n_s >= min_slice` cases and `100 * (B_s - P_s) > max_drop_pp * n_s` | `"slice:<tag>"` |

Compare in integers, exactly as written. List the reasons with must-pass ids first (in golden order), then `"overall"`, then slices sorted by tag. `decision` is `"block"` if there is any reason, else `"pass"`.

Return:

```
{
  "decision": "pass" | "block",
  "reasons":  [...],
  "results":  {case_id: bool},
  "pass_rate": {"baseline": B / N, "new": P / N},
  "slices":   {tag: {"n": n_s, "baseline": B_s / n_s, "new": P_s / n_s, "gated": n_s >= min_slice}}
}
```

`slices` has one entry for every tag that appears on any case. The judge also records every message you sent.

**Constraints**

- `1 <= len(golden) <= 60`, case ids are unique, and so are inputs
- `0 <= max_drop_pp <= 100`, `1 <= min_slice`
