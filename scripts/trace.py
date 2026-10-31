"""Print every test case of a problem with the reference solution's output, for writing walkthroughs.

    python3 scripts/trace.py 0102            # all cases
    python3 scripts/trace.py 0102 "cycle of 3"  # only cases whose name contains this text
    python3 scripts/trace.py 0102 --code mine.py  # run your own code instead of solution.py

Expected outputs come from the same build the site uses, so step numbers and values quoted from here are exact.
"""

import sys
import warnings

from lib import build_problem, harness, problem_dirs, read


def main():
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    args = sys.argv[1:]
    code_path = None
    if "--code" in args:
        k = args.index("--code")
        code_path = args[k + 1]
        del args[k:k + 2]
    if not args:
        sys.exit(__doc__)
    paths = problem_dirs(args[:1])
    if not paths:
        sys.exit("no problem matches %s" % args[0])
    path = paths[0]
    public, _ = build_problem(path)
    if "cases" not in public:
        sys.exit("design problems have no test cases")
    code = open(code_path).read() if code_path else read(path, "solution.py")
    for c in public["cases"]:
        if len(args) > 1 and args[1].lower() not in c["name"].lower():
            continue
        print("=" * 80)
        print("%s%s" % (c["name"], "" if c["hidden"] else "  (visible)"))
        print("args:", harness.show_args(harness.decode(c["args"])))
        out = harness._call(public, code, harness.decode(c["args"]))
        print("output:", harness.show(out))
        if code_path:
            print("expected:", harness.show(harness.decode(c["expected"])))


if __name__ == "__main__":
    main()
