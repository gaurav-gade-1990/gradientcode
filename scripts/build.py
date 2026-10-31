"""Build every problem into web/public/problems/<slug>.json plus index.json, and copy the harness.

    python3 scripts/build.py
"""

import json
import os
import shutil
import sys

from lib import CATEGORIES, ROOT, TRACKS, build_problem, problem_dirs, summary

OUT = os.path.join(ROOT, "web", "public", "problems")


def main():
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        if f.endswith(".json"):
            os.remove(os.path.join(OUT, f))
    index = []
    skipped = []
    for path in problem_dirs():
        try:
            public, _ = build_problem(path)
        except Exception as e:  # a folder a writer is still filling in must not break `pnpm dev`
            skipped.append(os.path.basename(path))
            print("skip %s: %s: %s" % (os.path.basename(path), type(e).__name__, e), file=sys.stderr)
            continue
        slug = public["meta"]["slug"]
        with open(os.path.join(OUT, slug + ".json"), "w") as f:
            json.dump(public, f, separators=(",", ":"))
        index.append(summary(public["meta"]))
    plans_path = os.path.join(ROOT, "problems", "study-plans.json")
    plans = json.load(open(plans_path)) if os.path.exists(plans_path) else []
    with open(os.path.join(OUT, "index.json"), "w") as f:
        json.dump({"tracks": [{"key": k, "name": n} for k, n in TRACKS],
                   "categories": [{"key": k, "name": n, "track": t} for k, n, t in CATEGORIES],
                   "problems": index, "plans": plans}, f, indent=1)
    for name in ("harness.py", "gc_runtime.py"):
        shutil.copy(os.path.join(ROOT, "harness", name), os.path.join(ROOT, "web", "public", name))
    print("built %d problems -> %s%s" % (len(index), os.path.relpath(OUT, ROOT), " (skipped %d)" % len(skipped) if skipped else ""))


if __name__ == "__main__":
    main()
