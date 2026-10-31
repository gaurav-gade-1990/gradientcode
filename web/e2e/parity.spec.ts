/* Browser parity sweep: every code problem's reference solution must be Accepted by the Pyodide judge,
 * and its first wrong_*.py must not be. This catches anything that passes in CPython (scripts/check.py)
 * but behaves differently in Pyodide. Slow (one judge call per file), so it only runs with PARITY=1:
 *
 *   PARITY=1 pnpm exec playwright test e2e/parity.spec.ts
 */
import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const PROBLEMS = path.join(ROOT, "problems");

test.skip(!process.env.PARITY, "set PARITY=1 to run the browser parity sweep");
test.setTimeout(30 * 60_000);

test("every reference solution is Accepted in Pyodide and a wrong one is not", async ({ page }) => {
  await page.goto("/");
  const index = await (await page.request.get("/problems/index.json")).json();
  const folders = Object.fromEntries(
    fs.readdirSync(PROBLEMS).filter((d) => /^\d{4}-/.test(d)).map((d) => [d.slice(5), d]),
  );
  const jobs: { slug: string; label: string; code: string; wantAccepted: boolean }[] = [];
  for (const p of index.problems) {
    if (p.type === "design") continue;
    const dir = path.join(PROBLEMS, folders[p.slug]);
    jobs.push({ slug: p.slug, label: "solution.py", code: fs.readFileSync(path.join(dir, "solution.py"), "utf8"), wantAccepted: true });
    const wrong = fs.readdirSync(dir).filter((f) => f.startsWith("wrong_")).sort()[0];
    if (wrong) jobs.push({ slug: p.slug, label: wrong, code: fs.readFileSync(path.join(dir, wrong), "utf8"), wantAccepted: false });
  }

  const results: { slug: string; label: string; status: string; ok: boolean; detail: string }[] = await page.evaluate(async (jobs) => {
    const worker = new Worker("/pyodide-worker.js");
    const pending = new Map<number, (v: any) => void>();
    let readyResolve: (v?: unknown) => void;
    let readyReject: (e: unknown) => void;
    const ready = new Promise((res, rej) => { readyResolve = res; readyReject = rej; });
    worker.onmessage = (e) => {
      const m = e.data;
      if (m.type === "ready") readyResolve();
      else if (m.type === "error") readyReject(new Error(m.error));
      else if (m.type === "result") { pending.get(m.id)?.(m); pending.delete(m.id); }
    };
    worker.postMessage({ type: "init", harnessUrl: "/harness.py", runtimeUrl: "/gc_runtime.py" });
    await ready;
    const cache = new Map<string, string>();
    const out = [];
    let id = 0;
    for (const j of jobs) {
      if (!cache.has(j.slug)) cache.set(j.slug, await (await fetch(`/problems/${j.slug}.json`)).text());
      const m: any = await new Promise((res) => {
        pending.set(++id, res);
        worker.postMessage({ type: "judge", id, problem: cache.get(j.slug), code: j.code, mode: "submit", custom: "[]" });
      });
      const status = m.error ? "worker error" : m.result.status;
      const ok = j.wantAccepted ? status === "Accepted" : status !== "Accepted";
      const c = m.result?.cases?.[0];
      out.push({ slug: j.slug, label: j.label, status, ok, detail: m.error || (c ? `${c.name}: ${c.message || c.error || ""}`.slice(0, 400) : "") });
    }
    worker.terminate();
    return out;
  }, jobs);

  const bad = results.filter((r) => !r.ok);
  console.log(`parity: ${results.length - bad.length}/${results.length} judgments as expected`);
  for (const r of bad) console.log(`  MISMATCH ${r.slug} ${r.label}: ${r.status} ${r.detail}`);
  expect(bad, bad.map((r) => `${r.slug} ${r.label}: ${r.status}`).join("\n")).toEqual([]);
});
