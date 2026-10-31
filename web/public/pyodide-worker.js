/* GradientCode judge worker (classic Web Worker).
 * Loads Pyodide + NumPy from the CDN, writes harness.py and gc_runtime.py into the Pyodide FS, then answers judge requests.
 * Messages in:  {type: "init", harnessUrl, runtimeUrl}  |  {type: "judge", id, problem, code, mode, custom}
 * Messages out: {type: "ready"} | {type: "error", error} | {type: "result", id, result} | {type: "result", id, error}
 */
var PYODIDE_URL = "https://cdn.jsdelivr.net/pyodide/v0.28.3/full/";
importScripts(PYODIDE_URL + "pyodide.js");

var ready = null;
var judgeFn = null;

function init(harnessUrl, runtimeUrl) {
  if (ready) return ready;
  ready = (async function () {
    var pyodide = await loadPyodide({ indexURL: PYODIDE_URL, stdout: function () {}, stderr: function () {} });
    await pyodide.loadPackage("numpy");
    var files = await Promise.all([harnessUrl, runtimeUrl].map(async function (u) {
      var r = await fetch(u);
      if (!r.ok) throw new Error("could not fetch " + u + " (HTTP " + r.status + ")");
      return r.text();
    }));
    pyodide.FS.mkdirTree("/gc");
    // gc_runtime sits next to harness so user code and drivers can `from gc_runtime import ...`.
    pyodide.FS.writeFile("/gc/harness.py", files[0]);
    pyodide.FS.writeFile("/gc/gc_runtime.py", files[1]);
    pyodide.runPython("import sys\nif '/gc' not in sys.path: sys.path.insert(0, '/gc')\nimport harness");
    judgeFn = pyodide.pyimport("harness").judge_json;
    return true;
  })();
  return ready;
}

self.onmessage = async function (e) {
  var msg = e.data;
  if (msg.type === "init") {
    try {
      await init(msg.harnessUrl, msg.runtimeUrl);
      self.postMessage({ type: "ready" });
    } catch (err) {
      self.postMessage({ type: "error", error: String(err && err.message ? err.message : err) });
    }
    return;
  }
  if (msg.type === "judge") {
    try {
      await ready;
      var out = judgeFn(msg.problem, msg.code, msg.mode, msg.custom);
      self.postMessage({ type: "result", id: msg.id, result: JSON.parse(out) });
    } catch (err) {
      self.postMessage({ type: "result", id: msg.id, error: String(err && err.message ? err.message : err) });
    }
  }
};
