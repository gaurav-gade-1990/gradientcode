"""GradientCode judge.

The same file runs in two places:
  * the browser, inside a Pyodide Web Worker (web/src/worker), and
  * CPython, inside scripts/check.py, so the checker grades exactly the way the site does.

Keep it compatible with Python 3.9 (no match statements, no `X | Y` types).

A built problem (web/public/problems/<slug>.json) carries:
  meta      -- id, slug, title, entry, mode ("function" | "driver"), compare, time_limit_ms, ...
  driver    -- optional source defining run(ns, **args) for class/stateful problems
  checker   -- optional source defining check(output, expected, args) -> (bool, str)
  cases     -- [{name, hidden, args, expected, explanation?}], values encoded by encode()
"""

import contextlib
import copy
import io
import json
import math
import time
import traceback

import numpy as np

STDOUT_CAP = 2000
REPR_CAP = 1500


# ---------------------------------------------------------------- encoding

def encode(obj):
    """Python/NumPy value -> JSON-safe structure."""
    if isinstance(obj, np.ndarray):
        if obj.dtype == object:
            return [encode(x) for x in obj.tolist()]
        flat = obj.ravel().tolist()
        if obj.dtype.kind == "f":
            flat = [_enc_float(x) for x in flat]
        return {"__nd__": True, "dtype": str(obj.dtype), "shape": list(obj.shape), "data": flat}
    if isinstance(obj, (bool, np.bool_)):
        return bool(obj)
    if isinstance(obj, (int, np.integer)):
        return int(obj)
    if isinstance(obj, (float, np.floating)):
        return _enc_float(float(obj))
    if isinstance(obj, tuple):
        return {"__tuple__": [encode(x) for x in obj]}
    if isinstance(obj, list):
        return [encode(x) for x in obj]
    if isinstance(obj, dict):
        return {"__dict__": [[encode(k), encode(v)] for k, v in obj.items()]}
    if obj is None or isinstance(obj, str):
        return obj
    raise TypeError("cannot encode value of type %s" % type(obj).__name__)


def _enc_float(x):
    if math.isnan(x):
        return {"__float__": "nan"}
    if math.isinf(x):
        return {"__float__": "inf" if x > 0 else "-inf"}
    return x


def decode(obj):
    if isinstance(obj, list):
        return [decode(x) for x in obj]
    if isinstance(obj, dict):
        if obj.get("__nd__"):
            data = [float(x["__float__"]) if isinstance(x, dict) else x for x in obj["data"]]
            return np.array(data, dtype=obj["dtype"]).reshape(obj["shape"])
        if "__tuple__" in obj:
            return tuple(decode(x) for x in obj["__tuple__"])
        if "__dict__" in obj:
            return {_hashable(decode(k)): decode(v) for k, v in obj["__dict__"]}
        if "__float__" in obj:
            return float(obj["__float__"])
    return obj


def _hashable(k):
    return tuple(k) if isinstance(k, list) else k


# ---------------------------------------------------------------- display

def show(obj):
    """Compact, LeetCode-like repr for inputs and outputs."""
    with np.printoptions(precision=4, suppress=True, threshold=60, edgeitems=3, linewidth=88):
        if isinstance(obj, np.ndarray):
            s = np.array2string(obj, separator=", ")
        elif isinstance(obj, (float, np.floating)):
            s = "%.6g" % obj
        elif isinstance(obj, (list, tuple)):
            inner = ", ".join(show(x) for x in obj)
            s = "[" + inner + "]" if isinstance(obj, list) else "(" + inner + (",)" if len(obj) == 1 else ")")
        elif isinstance(obj, dict):
            s = "{" + ", ".join("%s: %s" % (show(k), show(v)) for k, v in obj.items()) + "}"
        else:
            s = repr(obj)
    return s if len(s) <= REPR_CAP else s[:REPR_CAP] + " ..."


def show_args(args):
    return "\n".join("%s = %s" % (k, show(v)) for k, v in args.items())


# ---------------------------------------------------------------- comparison

def compare(out, exp, rtol=1e-5, atol=1e-8, path="output"):
    """Return (ok, message). Structure must match; floats compare with tolerance."""
    if isinstance(exp, np.ndarray):
        try:
            got = np.asarray(out, dtype=float if exp.dtype.kind in "fc" else None)
        except Exception:
            return False, "%s: expected an array of shape %s, got %s" % (path, exp.shape, type(out).__name__)
        if got.dtype == object:
            return False, "%s: could not convert to a numeric array" % path
        if got.shape != exp.shape:
            return False, "%s: shape mismatch, expected %s, got %s" % (path, exp.shape, got.shape)
        if exp.dtype.kind in "fc":
            if not np.allclose(got, exp, rtol=rtol, atol=atol, equal_nan=True):
                bad = np.argwhere(~np.isclose(got, exp, rtol=rtol, atol=atol, equal_nan=True))[0]
                idx = tuple(int(i) for i in bad)
                return False, "%s%s: expected %.6g, got %.6g" % (path, list(idx), exp[idx], got[idx])
            return True, ""
        if not np.array_equal(got, exp):
            bad = np.argwhere(got != exp)[0]
            idx = tuple(int(i) for i in bad)
            return False, "%s%s: expected %s, got %s" % (path, list(idx), exp[idx], got[idx])
        return True, ""
    if isinstance(exp, (bool, np.bool_)):
        if not isinstance(out, (bool, np.bool_, int, np.integer)) or bool(out) != bool(exp):
            return False, "%s: expected %s, got %s" % (path, exp, show(out))
        return True, ""
    if isinstance(exp, (int, float, np.integer, np.floating)):
        if isinstance(out, np.ndarray) and out.shape == ():
            out = out.item()
        if not isinstance(out, (int, float, np.integer, np.floating)) or isinstance(out, (bool, np.bool_)):
            return False, "%s: expected a number, got %s" % (path, type(out).__name__)
        if isinstance(exp, (int, np.integer)) and isinstance(out, (int, np.integer)):
            ok = int(out) == int(exp)
        else:
            ok = bool(np.isclose(float(out), float(exp), rtol=rtol, atol=atol, equal_nan=True))
        return (True, "") if ok else (False, "%s: expected %s, got %s" % (path, show(exp), show(out)))
    if isinstance(exp, (list, tuple)):
        if isinstance(out, np.ndarray):
            out = list(out)
        if not isinstance(out, (list, tuple)):
            return False, "%s: expected a %s, got %s" % (path, type(exp).__name__, type(out).__name__)
        if len(out) != len(exp):
            return False, "%s: expected length %d, got %d" % (path, len(exp), len(out))
        for i, (o, e) in enumerate(zip(out, exp)):
            ok, msg = compare(o, e, rtol, atol, "%s[%d]" % (path, i))
            if not ok:
                return ok, msg
        return True, ""
    if isinstance(exp, dict):
        if not isinstance(out, dict):
            return False, "%s: expected a dict, got %s" % (path, type(out).__name__)
        if set(out.keys()) != set(exp.keys()):
            return False, "%s: expected keys %s, got %s" % (path, sorted(map(str, exp)), sorted(map(str, out)))
        for k in exp:
            ok, msg = compare(out[k], exp[k], rtol, atol, "%s[%r]" % (path, k))
            if not ok:
                return ok, msg
        return True, ""
    if out != exp:
        return False, "%s: expected %s, got %s" % (path, show(exp), show(out))
    return True, ""


# ---------------------------------------------------------------- running

def _user_frames(tb_text):
    """Keep only the traceback lines that point at the user's code."""
    lines = tb_text.rstrip().splitlines()
    keep, skipping = [], False
    for line in lines:
        if line.startswith('  File "') and '"solution.py"' not in line:
            skipping = True
            continue
        if line.startswith('  File "solution.py"'):
            skipping = False
        if skipping and line.startswith("    "):
            continue
        skipping = False
        keep.append(line)
    return "\n".join(keep)


def _call(problem, user_code, args):
    ns = {"__name__": "solution", "np": np}
    exec(compile(user_code, "solution.py", "exec"), ns)
    meta = problem["meta"]
    if meta.get("mode") == "driver":
        dns = {"__name__": "driver", "np": np}
        exec(compile(problem["driver"], "driver.py", "exec"), dns)
        return dns["run"](ns, **args)
    entry = meta["entry"]
    if entry not in ns:
        raise NameError("your code must define `%s`" % entry)
    return ns[entry](**args)


def judge_case(problem, user_code, case, checker=None):
    """Run one case. Returns a result dict (all strings/numbers, JSON-safe)."""
    meta = problem["meta"]
    args = decode(case["args"])
    shown_input = show_args(args)
    expected = decode(case["expected"]) if "expected" in case else None
    buf = io.StringIO()
    res = {"name": case.get("name", ""), "hidden": bool(case.get("hidden")), "input": shown_input}
    t0 = time.perf_counter()
    try:
        with contextlib.redirect_stdout(buf):
            out = _call(problem, user_code, copy.deepcopy(args))
    except SyntaxError as e:
        res.update(status="Compile Error", error="%s: %s (line %s)" % (type(e).__name__, e.msg, e.lineno))
        res["stdout"] = buf.getvalue()[:STDOUT_CAP]
        return res
    except Exception:
        res.update(status="Runtime Error", error=_user_frames(traceback.format_exc()))
        res["ms"] = round((time.perf_counter() - t0) * 1000, 2)
        res["stdout"] = buf.getvalue()[:STDOUT_CAP]
        return res
    ms = (time.perf_counter() - t0) * 1000
    res["ms"] = round(ms, 2)
    res["stdout"] = buf.getvalue()[:STDOUT_CAP]
    res["output"] = show(out)
    if expected is None and "expected" not in case:
        res["status"] = "Finished"
        return res
    res["expected"] = show(expected)
    cmp = meta.get("compare", {})
    try:
        if checker is not None:
            ok, msg = checker(out, expected, copy.deepcopy(args))
        else:
            ok, msg = compare(out, expected, cmp.get("rtol", 1e-5), cmp.get("atol", 1e-8))
    except Exception:
        ok, msg = False, "checker could not read your output:\n" + traceback.format_exc(limit=1)
    res["status"] = "Accepted" if ok else "Wrong Answer"
    if not ok:
        res["message"] = msg
    if ok and ms > meta.get("time_limit_ms", 5000):
        res["status"] = "Time Limit Exceeded"
    return res


def _load_checker(problem):
    if not problem.get("checker"):
        return None
    cns = {"__name__": "checker", "np": np, "compare": compare}
    exec(compile(problem["checker"], "checker.py", "exec"), cns)
    return cns["check"]


def _custom_cases(custom):
    """Custom testcases are Python snippets that assign each argument, like `x = np.array([1, 2])`."""
    cases = []
    for i, src in enumerate(custom or []):
        scope = {"np": np}
        try:
            exec(compile(src, "testcase", "exec"), scope)
        except Exception as e:
            cases.append({"name": "Custom %d" % (i + 1), "bad": "%s: %s" % (type(e).__name__, e)})
            continue
        args = {k: v for k, v in scope.items() if k not in ("np", "__builtins__")}
        cases.append({"name": "Custom %d" % (i + 1), "args": encode(args)})
    return cases


def judge(problem, user_code, mode="run", custom=None):
    """mode "run": visible cases (+ custom). mode "submit": every case, stop at first failure."""
    checker = _load_checker(problem)
    cases = problem["cases"]
    if mode == "run":
        cases = [c for c in cases if not c.get("hidden")] + _custom_cases(custom)
    results, passed, total_ms = [], 0, 0.0
    status = "Accepted"
    for case in cases:
        if case.get("bad"):
            results.append({"name": case["name"], "status": "Runtime Error", "error": "testcase: " + case["bad"], "input": ""})
            status = "Runtime Error"
            continue
        r = judge_case(problem, user_code, case, checker)
        total_ms += r.get("ms", 0.0)
        results.append(r)
        if r["status"] in ("Accepted", "Finished"):
            passed += 1
            continue
        if status == "Accepted":
            status = r["status"]
        if mode == "submit" or r["status"] == "Compile Error":
            break
    out = {
        "status": status,
        "passed": passed,
        "total": len(cases),
        "runtime_ms": round(total_ms, 2),
        "cases": results,
    }
    if mode == "submit":
        # Like LeetCode: only the first failing case is revealed, hidden or not.
        out["cases"] = [r for r in results if r["status"] not in ("Accepted", "Finished")][:1]
    return out


def judge_json(problem_json, user_code, mode="run", custom_json="[]"):
    """Entry point for the Pyodide worker: strings in, string out."""
    problem = json.loads(problem_json)
    return json.dumps(judge(problem, user_code, mode, json.loads(custom_json)))
