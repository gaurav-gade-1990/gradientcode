# GradientCode

GradientCode is a practice site for AI and ML engineering interviews. It looks and works like LeetCode, and has three tracks:

- **Applied AI Engineering**: agents, tools and MCP, gateways, RAG, monitoring and enterprise platforms. Problems are graded against deterministic fakes in `harness/gc_runtime.py`, such as a fake LLM, a virtual clock and an event loop.
- **ML Foundations**: NumPy implementations of classic ML, neural network layers, optimizers, autograd, transformers and LLM internals.
- **System Design**: fifteen-section design answers with a timer, a hidden model answer and a self-scoring rubric.

Everything runs in the browser. Code problems run in Python 3 through Pyodide, and progress is saved in localStorage. There is no server.

## Quick start

```
cd web && pnpm i && pnpm dev
```

Open http://localhost:5180. You need Python 3.9 or newer on your PATH, because `pnpm dev` builds the problem JSON first.

## Deploying

The live site is https://gradient.appres.ai, a Cloudflare Pages project named `gradientcode`. Every push to `main` deploys it through `.github/workflows/deploy.yml`, after `scripts/check.py` passes. Pull requests run the check and the build only. The workflow needs a `CLOUDFLARE_API_TOKEN` repo secret. To deploy by hand, run `cd web && pnpm run deploy`. It builds the site and uploads `web/dist` with wrangler, and you need `npx wrangler login` once. Pages serves `index.html` for unknown paths, so deep links work. `web/public/_headers` sets the cache rules.

## How judging works

1. `scripts/build.py` loads each problem folder and runs the reference solution on every test case to get the expected outputs. It writes everything to `web/public/problems/<slug>.json`, with values encoded by `harness.encode` so NumPy arrays, tuples, dicts, NaN and inf survive JSON.
2. When you open a problem, a Web Worker loads Pyodide and NumPy and imports `harness.py`, the same file the local checker uses.
3. **Run** judges the visible cases plus any custom cases you add. **Submit** judges every case and stops at the first failure. Floats are compared with the problem's `rtol` and `atol`. A problem can supply its own checker when more than one answer is valid.
4. The page gives each judge call a wall-clock budget. If your code is still running when the budget runs out, the worker is killed and you get Time Limit Exceeded.

Design problems have no judge. You write each section, reveal the model answer, and check off the rubric criteria you covered. Checking at least 70% of them lets you mark the problem complete.

## Adding a problem

- For a coding problem, read [AUTHORING.md](AUTHORING.md).
- For a design problem, read [AUTHORING_DESIGN.md](AUTHORING_DESIGN.md).

Check a problem with `python3 scripts/check.py <id>`, then run `python3 scripts/build.py`, or restart `pnpm dev`. Study plans live in `problems/study-plans.json`. Slugs that aren't built yet are skipped.

## Repo layout

- `problems/`: one folder per problem, the catalogs, and the study plans
- `harness/`: the judge (`harness.py`) and the simulation fakes (`gc_runtime.py`). Both run in CPython and Pyodide.
- `scripts/`: `build.py` and `check.py`
- `web/`: the site (Vite, React, TypeScript, Tailwind, Monaco). See [web/README.md](web/README.md).
