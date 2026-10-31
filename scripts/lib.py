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

TRACKS = [
    ("applied", "Applied AI Engineering"),
    ("ml", "ML Foundations"),
    ("design", "System Design"),
]
CATEGORIES = [
    # Track 1: Applied AI Engineering (ids 101-199)
    ("agents", "Agents & Orchestration", "applied"),
    ("tools-mcp", "Tools & MCP", "applied"),
    ("serving", "Serving, Cost & Infra", "applied"),
    ("monitoring", "Data & Model Monitoring", "applied"),
    ("prod-ml", "Production ML & Evals", "applied"),
    ("rag", "RAG & Knowledge Systems", "applied"),
    ("enterprise", "Enterprise Agent Platforms", "applied"),
    ("fullstack", "Full Stack & Architecture", "applied"),
    # Track 2: ML Foundations (ids 1-99)
    ("numpy", "NumPy & Linear Algebra", "ml"),
    ("classic-ml", "Classic ML", "ml"),
    ("metrics", "Metrics & Evaluation", "ml"),
    ("nn", "Neural Network Blocks", "ml"),
    ("optim", "Optimizers & Training", "ml"),
    ("autograd", "Autograd", "ml"),
    ("transformers", "Sequence Models & Transformers", "ml"),
    ("llm", "LLM Internals", "ml"),
    ("retrieval", "Retrieval & NLP", "ml"),
    ("rl", "Reinforcement Learning", "ml"),
    # System Design (ids 201-299): no judge, a rubric and a model answer
    ("design-easy", "Design: Foundations", "design"),
    ("design-medium", "Design: Platforms at Scale", "design"),
    ("design-complex", "Design: Enterprise & Regulated", "design"),
]
CATEGORY_TRACK = {k: t for k, _, t in CATEGORIES}
DIFFICULTIES = ("Easy", "Medium", "Hard")
REQUIRED = ("problem.md", "meta.json", "starter.py", "solution.py", "tests.py", "editorial.md")
DESIGN_REQUIRED = ("problem.md", "meta.json", "rubric.json", "solution.md")


def problem_dirs(only=None):
    dirs = sorted(d for d in os.listdir(PROBLEMS) if os.path.isdir(os.path.join(PROBLEMS, d)) and d[:4].isdigit())
    if only:
        wanted = set(only)
        dirs = [d for d in dirs if d in wanted or d[:4] in wanted or d[5:] in wanted or str(int(d[:4])) in wanted]
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


def load_meta(path):
    meta = json.loads(read(path, "meta.json"))
    meta.setdefault("type", "code")
    meta["track"] = CATEGORY_TRACK.get(meta.get("category"), meta.get("track"))
    return meta


def build_design(path, meta):
    """A design problem ships its prompt, rubric and model answer; the UI hides the answer until asked."""
    public = {
        "meta": meta,
        "description": read(path, "problem.md"),
        "rubric": json.loads(read(path, "rubric.json")),
        "solution": read(path, "solution.md"),
    }
    return public, {}


def build_problem(path):
    """Return (public_json, private) where private holds the solution source for checks."""
    meta = load_meta(path)
    if meta["type"] == "design":
        return build_design(path, meta)
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
        "walkthrough": read(path, "walkthrough.md"),
        "starter": read(path, "starter.py"),
        "driver": driver,
        "checker": checker,
        "cases": built,
    }
    return public, {"solution": solution}


def summary(meta):
    keys = ("id", "slug", "title", "difficulty", "category", "tags", "track", "type")
    return {k: meta[k] for k in keys}
