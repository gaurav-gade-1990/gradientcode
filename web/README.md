# GradientCode web

The site is a static React app. Python runs in the browser through Pyodide, so there is no backend.

## Run

```
pnpm i
pnpm dev          # http://localhost:5180
```

`pnpm dev` and `pnpm build` first run `python3 ../scripts/build.py`. That script turns every folder in `../problems/` into `public/problems/<slug>.json` plus `index.json`, and copies `harness.py` and `gc_runtime.py` into `public/`. If a problem folder is broken or half written, it is skipped with a message on stderr. Run `pnpm problems` to rebuild without restarting.

```
pnpm build        # type-check, then build to dist/
pnpm preview      # serve dist/ on :5180
```

## Tests

```
pnpm exec playwright install chromium     # once
pnpm e2e                                  # starts the dev server if it is not running
SCREENSHOTS=1 pnpm exec playwright test screenshots   # refresh web/screenshots/
```

The first test that judges code waits for Pyodide and NumPy to download from the jsDelivr CDN. Give it up to a minute on a cold cache. The design-problem test serves `e2e/fixtures/design-fixture.json` through request interception, so it does not depend on which design problems are built.

## Layout

- `public/pyodide-worker.js`: a classic Web Worker. It loads Pyodide 0.28.3 and NumPy, writes `harness.py` and `gc_runtime.py` into the Pyodide file system, and answers judge requests with `harness.judge_json`.
- `src/lib/judge.ts`: the main-thread client. It gives each judge call a wall-clock budget of `max(8000, cases × time_limit_ms)` ms. When a call runs past it, the client terminates the worker, reports Time Limit Exceeded and starts a fresh worker.
- `src/lib/format.ts`: a TypeScript copy of `harness.show`, so examples render before Python loads.
- `src/lib/storage.ts`: progress in localStorage (`gc:drafts:<slug>`, `gc:subs:<slug>`, `gc:solved`, `gc:attempted`, `gc:design:<slug>`, `gc:theme`, `gc:track`).
- `src/pages/ProblemPage.tsx`: the coding workspace. `src/components/DesignWorkspace.tsx` is the system design workspace.
