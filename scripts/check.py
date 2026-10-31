"""Gate every problem before it ships.

    python3 scripts/check.py                 # all problems
    python3 scripts/check.py 0001 adam ...   # only these (id, slug or folder name)

For each problem it checks the files and meta, then grades through the real harness (after a JSON
round trip, exactly like the browser does):
  * solution.py passes every case,
  * starter.py fails,
  * every wrong_*.py (a common mistake, written on purpose) fails,
  * the build is deterministic and each case runs well under the time limit.
A walkthrough.md, when present, is checked too (see check_walkthrough).
"""

import ast
import json
import os
import re
import sys
import time
import warnings

import numpy as np

from lib import CATEGORIES, DESIGN_REQUIRED, DIFFICULTIES, REQUIRED, build_problem, harness, load_meta, problem_dirs, read

ALLOWED_IMPORTS = {
    "numpy", "math", "collections", "heapq", "itertools", "functools", "re", "typing", "dataclasses", "copy",
    "random", "string", "bisect",
    # Applied AI problems also get these (stdlib that runs unchanged in Pyodide) plus the simulation runtime.
    "json", "hashlib", "hmac", "base64", "enum", "statistics", "datetime", "operator", "textwrap", "fnmatch",
    "abc", "gc_runtime",
}
MAX_JSON_BYTES = 400_000
CATEGORY_KEYS = {k for k, _, _ in CATEGORIES}
ID_RANGES = {"ml": (1, 99), "applied": (101, 199), "design": (201, 299)}

# The Styx Unified framework: fifteen sections under four pillars.
DESIGN_SECTIONS = [
    ("A", "Scenario"), ("A", "Single View"),
    ("B", "Data Sources"), ("B", "Processing"), ("B", "Agents"), ("B", "Memory"), ("B", "MCP Tool Servers"),
    ("C", "Endpoints"), ("C", "Caching"), ("C", "Data Stores"), ("C", "Output"),
    ("D", "Guardrails"), ("D", "Key Impact"), ("D", "Failure Modes"), ("D", "Build Order"),
]
PILLAR_WORD_CAP = 1000

# walkthrough.md (the Detailed Explanation tab): numbered "## N. Title" sections, some of them required.
WALK_REQUIRED_CODE = ("really asking", "full solution", "test case", "complexity", "wrong answer", "follow-up")
WALK_REQUIRED_DESIGN = ("really asking", "follow-up")
WALK_MIN_WORDS = 900


def check_walkthrough(path, meta, errors, problem=None):
    """Structure checks, plus: the Full solution block is Accepted, and test-table rows name real cases."""
    text = read(path, "walkthrough.md")
    if text is None:
        return None
    heads = re.findall(r"^## (\d+)\. (.+)$", text, re.M)
    if [int(n) for n, _ in heads] != list(range(1, len(heads) + 1)) or not heads:
        errors.append("walkthrough.md: sections must be '## 1. ...', '## 2. ...' in order")
    prose = re.sub(r"```.*?```", "", text, flags=re.S)
    if re.search(r"^# ", prose, re.M):
        errors.append("walkthrough.md: no '# ' title; the tab supplies it")
    titles = [t.lower() for _, t in heads]
    design = meta["type"] == "design"
    for key in WALK_REQUIRED_DESIGN if design else WALK_REQUIRED_CODE:
        if not any(key in t for t in titles):
            errors.append("walkthrough.md: needs a section whose title contains %r" % key)
    words = len(prose.split())
    if words < WALK_MIN_WORDS:
        errors.append("walkthrough.md: %d words of prose (< %d)" % (words, WALK_MIN_WORDS))
    if design:
        sub_heads = " ".join(re.findall(r"^#{2,4} .+$", text, re.M)).lower()
        missing = [t for _, t in DESIGN_SECTIONS if t.lower() not in sub_heads]
        if missing:
            errors.append("walkthrough.md: no heading for section(s) %s" % ", ".join(missing))
        return words
    i = next((k for k, t in enumerate(titles) if "full solution" in t), None)
    if i is not None:
        body = re.split(r"^## \d+\. .+$", text, flags=re.M)[i + 1]
        m = re.search(r"```python\n(.*?)```", body, re.S)
        if not m:
            errors.append("walkthrough.md: the Full solution section has no ```python block")
        elif problem is not None:
            r = harness.judge(problem, m.group(1), "submit")
            if r["status"] != "Accepted":
                errors.append("walkthrough.md: Full solution code is %s" % r["status"])
    j = next((k for k, t in enumerate(titles) if "test case" in t), None)
    if j is not None and problem is not None:
        body = re.split(r"^## \d+\. .+$", text, flags=re.M)[j + 1]
        names = [c["name"].lower() for c in problem["cases"]]
        rows = [r.split("|")[1].strip() for r in re.findall(r"^\|.*\|$", body, re.M)[2:]]
        for cell in rows:
            if not any(n and n in cell.lower() for n in names):
                errors.append("walkthrough.md: test table row %r names no test case" % cell)
    return words


def check_design(path, meta, errors):
    for f in DESIGN_REQUIRED:
        if not os.path.exists(os.path.join(path, f)):
            errors.append("missing " + f)
    if errors:
        return {}
    if not meta.get("time_minutes"):
        errors.append("meta.time_minutes missing")
    rubric = json.loads(read(path, "rubric.json"))
    secs = rubric.get("sections", [])
    if [(x.get("pillar"), x.get("title")) for x in secs] != DESIGN_SECTIONS:
        errors.append("rubric.json sections must be the 15 framework sections in order: %s" % [t for _, t in DESIGN_SECTIONS])
    for x in secs:
        if not x.get("prompt") or len(x.get("criteria", [])) < 2:
            errors.append("rubric section %r needs a prompt and >= 2 criteria" % x.get("title"))
    sol = read(path, "solution.md")
    heads = re.findall(r"^## (\d+)\. (.+?)\s*$", sol, re.M)
    if [(int(n), t) for n, t in heads] != [(i + 1, t) for i, (_, t) in enumerate(DESIGN_SECTIONS)]:
        errors.append("solution.md needs '## 1. Scenario' ... '## 15. Build Order' in order, got %s" % heads)
        return {}
    bodies = re.split(r"^## \d+\. .+$", sol, flags=re.M)[1:]
    words = {}
    for (pillar, title), body in zip(DESIGN_SECTIONS, bodies):
        if title != "Single View":
            if "**Decision.**" not in body or "**Trap.**" not in body:
                errors.append("solution.md section %r needs a **Decision.** and a **Trap.**" % title)
            else:
                # Order: opener, (table), How, Decision, then Trap directly after Decision.
                opener = body.strip().split("\n", 1)[0]
                how = body.find("**How:**")
                dec, trap = body.find("**Decision.**"), body.find("**Trap.**")
                if not opener or opener.startswith(("**How", "**Decision", "|")):
                    errors.append("solution.md section %r must open with 1-3 sentences before any table or How" % title)
                if how != -1 and how > dec:
                    errors.append("solution.md section %r: How must come before Decision" % title)
                if trap < dec or body[dec:trap].count("\n\n") > 1:
                    errors.append("solution.md section %r: Trap must follow Decision directly" % title)
        words[pillar] = words.get(pillar, 0) + len(body.split())
    for pillar, n in words.items():
        if n > PILLAR_WORD_CAP:
            errors.append("pillar %s is %d words (cap %d); a pillar is ~5 minutes of reading" % (pillar, n, PILLAR_WORD_CAP))
    return {"words": words}


def imports_ok(src, label, errors):
    if not src:
        return
    for node in ast.walk(ast.parse(src)):
        names = []
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or ""]
        for n in names:
            if n.split(".")[0] not in ALLOWED_IMPORTS:
                errors.append("%s imports %s (only numpy + small stdlib allowed)" % (label, n))


def has_nan(v):
    if isinstance(v, np.ndarray):
        return v.dtype.kind == "f" and bool(np.isnan(v).any())
    if isinstance(v, float):
        return v != v
    if isinstance(v, (list, tuple)):
        return any(has_nan(x) for x in v)
    if isinstance(v, dict):
        return any(has_nan(x) for x in v.values())
    return False


def check_problem(path):
    errors = []
    folder = os.path.basename(path)
    meta = load_meta(path)
    lo, hi = ID_RANGES.get(meta.get("track"), (0, 9999))
    if not lo <= int(folder[:4]) <= hi:
        errors.append("id %s is outside the %s track range %d-%d" % (folder[:4], meta.get("track"), lo, hi))
    if meta["type"] == "design":
        for key, ok in (("id", meta.get("id") == int(folder[:4])), ("slug", meta.get("slug") == folder[5:]),
                        ("difficulty", meta.get("difficulty") in DIFFICULTIES), ("category", meta.get("category") in CATEGORY_KEYS),
                        ("title", bool(meta.get("title"))), ("tags", bool(meta.get("tags")))):
            if not ok:
                errors.append("bad or missing meta.%s" % key)
        stats = check_design(path, meta, errors)
        walk = check_walkthrough(path, meta, errors)
        if walk:
            stats["walkthrough_words"] = walk
        return errors, stats
    for f in REQUIRED:
        if not os.path.exists(os.path.join(path, f)):
            errors.append("missing " + f)
    if errors:
        return errors, {}
    if meta.get("id") != int(folder[:4]):
        errors.append("meta.id %r != folder number %s" % (meta.get("id"), folder[:4]))
    if meta.get("slug") != folder[5:]:
        errors.append("meta.slug %r != folder slug %s" % (meta.get("slug"), folder[5:]))
    if meta.get("difficulty") not in DIFFICULTIES:
        errors.append("bad difficulty %r" % meta.get("difficulty"))
    if meta.get("category") not in CATEGORY_KEYS:
        errors.append("bad category %r" % meta.get("category"))
    for key in ("title", "tags", "hints", "time_limit_ms"):
        if not meta.get(key):
            errors.append("meta.%s missing" % key)
    mode = meta.get("mode", "function")
    if mode == "function" and not meta.get("entry"):
        errors.append("function mode needs meta.entry")
    if mode == "driver" and not read(path, "driver.py"):
        errors.append("driver mode needs driver.py")
    desc = read(path, "problem.md")
    if re.search(r"^#+\s*Example", desc, re.M):
        errors.append("problem.md must not hand-write examples; visible cases are rendered as examples")
    editorial = read(path, "editorial.md").lower()
    if meta["track"] == "applied":
        if "## production notes" not in editorial:
            errors.append("applied editorial.md needs a '## Production notes' section")
    elif "complexity" not in editorial:
        errors.append("editorial.md must discuss complexity")
    wrongs = sorted(f for f in os.listdir(path) if f.startswith("wrong_") and f.endswith(".py"))
    if not wrongs:
        errors.append("add at least one wrong_*.py (a classic mistake the hidden tests must catch)")
    for f in ("solution.py", "driver.py", "checker.py"):
        try:
            imports_ok(read(path, f), f, errors)
        except SyntaxError as e:
            errors.append("%s does not parse: %s" % (f, e))
    if errors:
        return errors, {}

    try:
        t0 = time.perf_counter()
        public, private = build_problem(path)
        build_s = time.perf_counter() - t0
        again, _ = build_problem(path)
    except Exception as e:
        import traceback
        return ["build failed: %s" % traceback.format_exc()], {}
    blob = json.dumps(public, separators=(",", ":"))
    if blob != json.dumps(again, separators=(",", ":")):
        errors.append("build is not deterministic (seed every RNG)")
    if len(blob) > MAX_JSON_BYTES:
        errors.append("built JSON is %d bytes (> %d); shrink test arrays" % (len(blob), MAX_JSON_BYTES))
    problem = json.loads(blob)
    visible = [c for c in problem["cases"] if not c["hidden"]]
    hidden = [c for c in problem["cases"] if c["hidden"]]
    if len(visible) < 2:
        errors.append("need >= 2 visible cases, have %d" % len(visible))
    if len(hidden) < 3:
        errors.append("need >= 3 hidden cases, have %d" % len(hidden))

    for c in problem["cases"]:
        if has_nan(harness.decode(c["expected"])) and not meta.get("allow_nan"):
            errors.append("case %r expects NaN; a broken submission returning NaN would pass" % c["name"])
    res = harness.judge(problem, private["solution"], "submit")
    if res["status"] != "Accepted":
        errors.append("solution.py not Accepted: %s" % json.dumps(res["cases"][:1], indent=1))
    full = harness.judge(problem, private["solution"], "run")
    if full["status"] != "Accepted":
        errors.append("solution.py fails visible cases: %s" % json.dumps(full["cases"], indent=1)[:2000])
    limit = meta["time_limit_ms"]
    for c in problem["cases"]:
        r = harness.judge_case(problem, private["solution"], c)
        if r.get("ms", 0) > limit / 5:
            errors.append("case %r takes %.0f ms in CPython; limit is %d ms (need < limit/5 for Pyodide headroom)" % (c["name"], r["ms"], limit))
    starter = harness.judge(problem, public["starter"], "submit")
    if starter["status"] == "Accepted":
        errors.append("starter.py is Accepted; it must fail")
    if harness.judge(problem, public["starter"], "run")["status"] == "Compile Error":
        errors.append("starter.py does not compile")
    for w in wrongs:
        r = harness.judge(problem, read(path, w), "submit")
        if r["status"] == "Accepted":
            errors.append("%s is Accepted; the tests do not catch that mistake" % w)
    stats = {"cases": len(problem["cases"]), "bytes": len(blob), "build_s": round(build_s, 2), "wrongs": len(wrongs)}
    walk = check_walkthrough(path, meta, errors, problem)
    if walk:
        stats["walkthrough_words"] = walk
    return errors, stats


def main():
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    only = sys.argv[1:]
    paths = problem_dirs(only)
    if not paths:
        print("no problems matched %s" % only)
        sys.exit(1)
    failed = 0
    ids = {}
    for path in paths:
        folder = os.path.basename(path)
        ids.setdefault(folder[:4], []).append(folder)
        errors, stats = check_problem(path)
        if errors:
            failed += 1
            print("FAIL %s" % folder)
            for e in errors:
                print("   - " + e.replace("\n", "\n     "))
        else:
            print("ok   %s  %s" % (folder, stats))
    for k, v in ids.items():
        if len(v) > 1:
            failed += 1
            print("FAIL duplicate id %s: %s" % (k, v))
    print("\n%d/%d passed" % (len(paths) - failed, len(paths)))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
