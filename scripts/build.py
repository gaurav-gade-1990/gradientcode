"""Build every problem into web/public/problems/<slug>.json plus index.json, and copy the harness.

    python3 scripts/build.py
"""

import json
import os
import shutil

from lib import CATEGORIES, ROOT, build_problem, problem_dirs, summary

OUT = os.path.join(ROOT, "web", "public", "problems")


def main():
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        if f.endswith(".json"):
            os.remove(os.path.join(OUT, f))
    index = []
    for path in problem_dirs():
        public, _ = build_problem(path)
        slug = public["meta"]["slug"]
        with open(os.path.join(OUT, slug + ".json"), "w") as f:
            json.dump(public, f, separators=(",", ":"))
        index.append(summary(public["meta"]))
    plans_path = os.path.join(ROOT, "problems", "study-plans.json")
    plans = json.load(open(plans_path)) if os.path.exists(plans_path) else []
    with open(os.path.join(OUT, "index.json"), "w") as f:
        json.dump({"categories": [{"key": k, "name": n} for k, n in CATEGORIES], "problems": index, "plans": plans}, f, indent=1)
    shutil.copy(os.path.join(ROOT, "harness", "harness.py"), os.path.join(ROOT, "web", "public", "harness.py"))
    print("built %d problems -> %s" % (len(index), os.path.relpath(OUT, ROOT)))


if __name__ == "__main__":
    main()
