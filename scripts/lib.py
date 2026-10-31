"""Shared helpers for build.py and check.py: load a problem folder and turn it into the JSON the site serves."""

import copy
import importlib.util
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROBLEMS = os.path.join(ROOT, "problems")
sys.path.insert(0, os.path.join(ROOT, "harness"))

import harness  # noqa: E402

CATEGORIES = [
    ("numpy", "NumPy & Linear Algebra"),
    ("classic-ml", "Classic ML"),
    ("metrics", "Metrics & Evaluation"),
    ("nn", "Neural Network Blocks"),
    ("optim", "Optimizers & Training"),
    ("autograd", "Autograd"),
    ("transformers", "Sequence Models & Transformers"),
    ("llm", "LLM Internals"),
    ("retrieval", "Retrieval & NLP"),
    ("rl", "Reinforcement Learning"),
]
DIFFICULTIES = ("Easy", "Medium", "Hard")
REQUIRED = ("problem.md", "meta.json", "starter.py", "solution.py", "tests.py", "editorial.md")


def problem_dirs(only=None):
    dirs = sorted(d for d in os.listdir(PROBLEMS) if os.path.isdir(os.path.join(PROBLEMS, d)) and d[:4].isdigit())
    if only:
        wanted = set(only)
        dirs = [d for d in dirs if d in wanted or d[5:] in wanted or str(int(d[:4])) in wanted]
    return [os.path.join(PROBLEMS, d) for d in dirs]


def read(path, name, default=None):
    p = os.path.join(path, name)
    if not os.path.exists(p):
        return default
    with open(p) as f:
        return f.read()


def load_module(path, name):
    spec = importlib.util.spec_from_file_location("%s_%s" % (os.path.basename(path).replace("-", "_"), name[:-3]), os.path.join(path, name))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def build_problem(path):
    """Return (public_json, private) where private holds the solution source for checks."""
    meta = json.loads(read(path, "meta.json"))
    solution = read(path, "solution.py")
    driver = read(path, "driver.py")
    checker = read(path, "checker.py")
    problem = {"meta": meta, "driver": driver, "checker": checker}
    cases = load_module(path, "tests.py").cases()
    built = []
    for c in cases:
        args = c["args"]
        if "expected" in c:
            expected = c["expected"]
        else:
            expected = harness._call(problem, solution, copy.deepcopy(args))
        case = {"name": c.get("name", ""), "hidden": bool(c.get("hidden", True)), "args": harness.encode(args), "expected": harness.encode(expected)}
        if c.get("explanation"):
            case["explanation"] = c["explanation"]
        built.append(case)
    public = {
        "meta": meta,
        "description": read(path, "problem.md"),
        "editorial": read(path, "editorial.md"),
        "starter": read(path, "starter.py"),
        "driver": driver,
        "checker": checker,
        "cases": built,
    }
    return public, {"solution": solution}


def summary(meta):
    keys = ("id", "slug", "title", "difficulty", "category", "tags")
    return {k: meta[k] for k in keys}
