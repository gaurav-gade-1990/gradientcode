/* GradientCode judge worker (classic Web Worker).
 * Loads Pyodide + NumPy from the CDN, writes harness.py and gc_runtime.py into the Pyodide FS, then answers judge requests.
 * Messages in:  {type: "init", harnessUrl, runtimeUrl, pyodideUrl?}  (pyodideUrl defaults to the jsDelivr CDN)  |  {type: "judge", id, problem, code, mode, custom}
 * Messages out: {type: "ready"} | {type: "error", error} | {type: "result", id, result} | {type: "result", id, error}
 */
var CDN_PYODIDE_URL = "https://cdn.jsdelivr.net/pyodide/v0.28.3/full/";

var ready = null;
var judgeFn = null;

async function fetchBase64(url) {
  var r = await fetch(url);
  if (!r.ok) throw new Error("could not fetch " + url + " (HTTP " + r.status + ")");
  var bin = atob((await r.text()).trim());
  var bytes = new Uint8Array(bin.length);
  for (var i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return bytes;
}

function init(harnessUrl, runtimeUrl, pyodideUrl) {
  if (ready) return ready;
  var indexURL = pyodideUrl || CDN_PYODIDE_URL;
  ready = (async function () {
    importScripts(indexURL + "pyodide.js");
    var pyodide;
    if (pyodideUrl) {
      // Self-hosted (artifact build): the host will not serve .zip or .whl files, so the standard library and the
      // NumPy wheel ship as base64 text next to pyodide.js (see scripts/build-artifact.py).
      var stdlib = await fetchBase64(indexURL + "python_stdlib.zip.b64.txt");
      var stdLibURL = URL.createObjectURL(new Blob([stdlib], { type: "application/zip" }));
      pyodide = await loadPyodide({ indexURL: indexURL, stdLibURL: stdLibURL, stdout: function () {}, stderr: function () {} });
      var numpy = await fetchBase64(indexURL + "numpy.whl.b64.txt");
      pyodide.unpackArchive(numpy, "wheel");
    } else {
      pyodide = await loadPyodide({ indexURL: indexURL, stdout: function () {}, stderr: function () {} });
      await pyodide.loadPackage("numpy");
    }
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
      await init(msg.harnessUrl, msg.runtimeUrl, msg.pyodideUrl);
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
