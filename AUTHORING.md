# Writing a GradientCode problem

Each problem is one folder: `problems/<4-digit id>-<slug>/`. Look at the three seed problems before you write one:

- `0001-stable-softmax`: a plain function
- `0052-adam`: a function that returns a tuple
- `0056-scalar-autograd-value`: driver mode, for a class

## Files

| file | what |
|---|---|
| `meta.json` | `id`, `slug`, `title`, `difficulty` (Easy/Medium/Hard), `category`, `tags`, `mode` (`function` or `driver`), `entry`, `signature`, `compare` `{rtol, atol}`, `time_limit_ms`, `hints` (2–4, progressively stronger), `related` (slugs) |
| `problem.md` | The statement. Markdown plus KaTeX (`$...$`, `$$...$$`). Say exactly what to return: shapes, dtypes, tie-breaking, ordering, edge cases. End with a **Constraints** list. **Do not write examples.** The site renders the visible test cases as Example 1, 2, … |
| `starter.py` | Imports, the exact signature, and a `# Write your code here` / `pass` body. It must compile, and it must fail. |
| `solution.py` | The reference solution. Clear, idiomatic NumPy. |
| `wrong_*.py` | **At least one.** A realistic mistake people make: no numerical stability, forgetting bias correction, an off-by-one, the wrong axis, ignoring a mask, no `keepdims`, population vs sample variance. The hidden tests must catch every one, and the checker enforces that. |
| `tests.py` | `def cases():` returns a list of `{"name", "hidden", "args", "explanation"?}`. Use **2–3 visible** cases (`"hidden": False`); they become the examples, so make them small and readable. Add **5+ hidden** cases (`hidden` defaults to True) for edge cases, shapes, scale, and one case that catches each `wrong_*.py`. Expected outputs come from running `solution.py`; never hand-write them. Seed every RNG with `np.random.default_rng(<id>)`. |
| `editorial.md` | Sections: `## Approach` (intuition, then the key equations, then the code), `## Common mistakes`, and `## Complexity`. Keep it short enough to read in 3 minutes. |
| `driver.py` | Driver mode only. `def run(ns, **args)` uses the user's namespace `ns` (e.g. `ns["Value"]`) and returns a comparable output. Use it for classes, stateful objects (an optimizer over several steps, a KV cache), or training loops. |
| `checker.py` | Optional. `def check(output, expected, args) -> (ok, message)`. Use it when there are many valid answers: cluster labels up to permutation, eigenvector sign, samples that only need the right support, any valid topological order. `compare(out, exp, rtol, atol)` from the harness is in scope. |

## Rules

- **NumPy only.** Solutions, drivers and checkers may import only `numpy` and a small part of the stdlib (`math`, `collections`, `heapq`, `itertools`, `functools`, `re`, `typing`, `dataclasses`, `copy`, `random`, `string`, `bisect`). The code runs in the browser through Pyodide.
- **Python 3.9 compatible.** The local checker runs 3.9, so no `match` and no `X | Y` types.
- Arguments are passed by **keyword**: `ns[entry](**args)`. Argument names in `tests.py` must match the signature.
- Values can be ndarrays, Python scalars, lists, tuples, dicts and strings. Tuples, dicts and NaN/inf survive encoding.
- Comparison: arrays need the same shape. Float arrays are compared with `allclose(rtol, atol)`. Int and bool arrays must match exactly. Lists and tuples are compared element by element. Pick a tolerance that fits the algorithm: iterative or float32 work needs a looser one.
- Randomness inside the algorithm (dropout masks, k-means init, sampling) **must be passed in**: either the random numbers themselves (`u = rng.random(...)`) or a `seed`. Spell out exactly how the solution has to consume them, e.g. "use `mask = u < keep_prob`". If the user's answer can't be determined from the inputs, the problem can't be graded.
- Training-loop problems (logistic regression with GD, the MLP on XOR) must fix the init, learning rate and iteration count, and spell out the update order. Then the result is deterministic.
- Keep test arrays small. The built JSON must be under 400 KB, and each case must run in CPython in under `time_limit_ms / 5`. Pyodide is slower than CPython. If the point is vectorization, use one moderately large hidden case with a tight time limit to catch Python loops.
- The difficulty should reflect interview reality. Easy is a few lines. Medium is a known algorithm with some care. Hard is a multi-part derivation or careful bookkeeping.
- The prose style is direct and second person ("Implement…", "Return…"). Use no filler and no emoji.

## Check

```
python3 scripts/check.py 0001 0052          # by id, slug, or folder
python3 scripts/check.py                    # everything
```

A problem ships only when it prints `ok`. Run `python3 scripts/build.py` to refresh `web/public/problems/`.
