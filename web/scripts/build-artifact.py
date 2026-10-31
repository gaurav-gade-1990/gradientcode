"""Build GradientCode as a self-contained claude.ai artifact in web/dist-artifact/.

The artifact host only lets a page fetch its own published files, so this build:
  * uses relative asset paths and hash routing (VITE_ARTIFACT=1),
  * ships the Pyodide runtime and the NumPy wheel under pyodide/ (cached in web/.pyodide-local/),
  * turns index.html into page content (the host adds the doctype, head and body skeleton).

    python3 scripts/build-artifact.py
"""

import os
import re
import shutil
import subprocess
import urllib.request

WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(WEB, "dist-artifact")
CACHE = os.path.join(WEB, ".pyodide-local")
CDN = "https://cdn.jsdelivr.net/pyodide/v0.28.3/full/"
PYODIDE_FILES = [
    "pyodide.js", "pyodide.asm.js", "pyodide.asm.wasm", "python_stdlib.zip", "pyodide-lock.json",
    "numpy-2.2.5-cp313-cp313-pyodide_2025_0_wasm32.whl",
]


def main():
    env = dict(os.environ, VITE_ARTIFACT="1")
    subprocess.run(["pnpm", "build", "--outDir", OUT, "--emptyOutDir"], cwd=WEB, env=env, check=True)

    os.makedirs(CACHE, exist_ok=True)
    os.makedirs(os.path.join(OUT, "pyodide"), exist_ok=True)
    for f in PYODIDE_FILES:
        cached = os.path.join(CACHE, f)
        if not os.path.exists(cached):
            urllib.request.urlretrieve(CDN + f, cached)
        shutil.copy(cached, os.path.join(OUT, "pyodide", f))

    # The host wraps the page in its own skeleton: keep the head's title, styles and scripts, drop the wrappers.
    html = open(os.path.join(OUT, "index.html")).read()
    head = re.search(r"<head>(.*?)</head>", html, re.S).group(1)
    body = re.search(r"<body[^>]*>(.*?)</body>", html, re.S).group(1)
    head = re.sub(r'<meta (charset|name="viewport")[^>]*>\s*', "", head)
    head = re.sub(r'<link rel="icon"[^>]*>\s*', "", head)
    with open(os.path.join(OUT, "index.html"), "w") as f:
        f.write(head.strip() + "\n" + body.strip() + "\n")

    # One publish takes at most 255 files. Browsers use KaTeX's woff2 fonts, so drop its ttf/woff copies.
    assets = os.path.join(OUT, "assets")
    for n in os.listdir(assets):
        if n.startswith("KaTeX_") and (n.endswith(".ttf") or n.endswith(".woff")):
            os.remove(os.path.join(assets, n))
    if os.path.exists(os.path.join(OUT, "favicon.svg")):
        os.remove(os.path.join(OUT, "favicon.svg"))

    files = sorted(os.path.relpath(os.path.join(d, n), OUT) for d, _, ns in os.walk(OUT) for n in ns)
    size = sum(os.path.getsize(os.path.join(OUT, p)) for p in files)
    print("artifact build: %d files, %.1f MB -> %s" % (len(files), size / 1e6, os.path.relpath(OUT, WEB)))


if __name__ == "__main__":
    main()
