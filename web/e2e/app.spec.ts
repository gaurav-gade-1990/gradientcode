import { expect, test, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const solution = (dir: string) => readFileSync(resolve(ROOT, "problems", dir, "solution.py"), "utf8");
const PY_READY = 90_000;

async function openProblem(page: Page, slug: string) {
  await page.goto(`/problems/${slug}`);
  await expect(page.getByTestId("problem-title")).toBeVisible();
  await expect(page.locator(".monaco-editor").first()).toBeVisible();
  // Run turns from "Loading Python…" into "Run" once Pyodide and NumPy are up.
  await expect(page.getByTestId("run")).toBeEnabled({ timeout: PY_READY });
}

async function setCode(page: Page, code: string) {
  await page.locator(".monaco-editor .view-lines").first().click();
  // Select-all is flaky in headless Monaco on long files, so clear through the editor, then paste the code in.
  await page.evaluate(() => {
    window.__gcEditor?.setValue("");
    window.__gcEditor?.focus();
  });
  await expect.poll(() => page.evaluate(() => window.__gcEditor?.getValue() ?? "")).toBe("");
  // Paste, like a person would: typing character by character fights Monaco's auto-indent.
  await page.evaluate((c) => navigator.clipboard.writeText(c), code);
  await page.keyboard.press("ControlOrMeta+V");
  const norm = (s: string) => s.replace(/\r\n?/g, "\n").split("\n").map((l) => l.trimEnd()).join("\n").trim();
  await expect.poll(async () => norm((await page.evaluate(() => window.__gcEditor?.getValue())) ?? "")).toBe(norm(code));
}

test.beforeEach(async ({ page, context }) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  await page.addInitScript(() => {
    if (!sessionStorage.getItem("gc:test-init")) {
      localStorage.clear();
      sessionStorage.setItem("gc:test-init", "1");
    }
  });
});

test("problem list renders and filters work", async ({ page }) => {
  await page.goto("/");
  // Applied AI Engineering is the default track; ML Foundations holds the NumPy problems.
  await expect(page.getByTestId("track-applied")).toHaveAttribute("aria-selected", "true");
  await page.getByTestId("track-ml").click();
  const rows = page.getByTestId("problem-row");
  await expect(rows.first()).toBeVisible();
  const total = await rows.count();
  expect(total).toBeGreaterThanOrEqual(3);
  await expect(rows.first()).toContainText("1. Stable Softmax");

  await page.getByTestId("filter-difficulty").click();
  await page.getByRole("option", { name: "Hard" }).click();
  const hard = await rows.count();
  expect(hard).toBeGreaterThan(0);
  expect(hard).toBeLessThan(total);
  for (const t of await page.locator('[data-testid="problem-row"] td:nth-child(4)').allTextContents()) expect(t).toBe("Hard");
  await expect(page.getByTestId("problem-table")).toContainText("Scalar Autograd Engine");

  await page.getByText("Reset").click();
  await expect(rows).toHaveCount(total);

  await page.getByTestId("search").fill("softmax");
  await expect(page.getByTestId("problem-table")).toContainText("Stable Softmax");
  for (const t of await rows.allTextContents()) expect(t.toLowerCase()).toContain("softmax");
  await page.getByTestId("search").fill("");

  await page.getByTestId("chip-autograd").click();
  await expect(page.getByTestId("problem-table")).toContainText("Scalar Autograd Engine");
  for (const t of await page.locator('[data-testid="problem-row"] td:nth-child(3)').allTextContents()) expect(t).toBe("Autograd");
});

test("stable-softmax: starter is Wrong Answer, reference solution is Accepted", async ({ page }) => {
  await openProblem(page, "stable-softmax");
  await expect(page.getByTestId("examples")).toContainText("Example 1:");
  await expect(page.getByTestId("examples")).toContainText("x = [1., 2., 3.]");

  await page.getByTestId("run").click();
  await expect(page.getByTestId("result-status")).toHaveText("Wrong Answer", { timeout: PY_READY });

  await setCode(page, solution("0001-stable-softmax"));
  await page.getByTestId("submit").click();
  await expect(page.getByTestId("result-status")).toHaveText("Accepted", { timeout: PY_READY });
  // Every case passes, however many the problem has.
  await expect(page.getByTestId("result-passed")).toHaveText(/^(\d+) \/ \1 testcases passed$/);

  await page.getByTestId("tab-submissions").click();
  await expect(page.getByTestId("submission-row").first()).toContainText("Accepted");
  await expect(page.getByTestId("solved-counter")).toContainText("1");
});

test("an infinite loop is Time Limit Exceeded and the next Run still works", async ({ page }) => {
  await openProblem(page, "stable-softmax");
  await setCode(page, "import numpy as np\n\ndef softmax(x, axis=-1):\n    while True:\n        pass\n");
  await page.getByTestId("run").click();
  await expect(page.getByTestId("result-status")).toHaveText("Time Limit Exceeded", { timeout: 30_000 });

  await setCode(page, solution("0001-stable-softmax"));
  await expect(page.getByTestId("run")).toBeEnabled({ timeout: PY_READY });
  await page.getByTestId("run").click();
  await expect(page.getByTestId("result-status")).toHaveText("Accepted", { timeout: PY_READY });
});

test("autograd driver problem is Accepted with its solution", async ({ page }) => {
  await openProblem(page, "scalar-autograd-value");
  await setCode(page, solution("0056-scalar-autograd-value"));
  await page.getByTestId("submit").click();
  await expect(page.getByTestId("result-status")).toHaveText("Accepted", { timeout: PY_READY });
  await expect(page.getByTestId("result-passed")).toHaveText(/^(\d+) \/ \1 testcases passed$/);
});

test("a custom testcase runs and shows its output", async ({ page }) => {
  await openProblem(page, "stable-softmax");
  await setCode(page, solution("0001-stable-softmax"));
  await page.getByTestId("tab-testcase").click();
  await page.getByTestId("add-case").click();
  const box = page.getByTestId("custom-case-input");
  await expect(box).toHaveValue(/x = np\.array\(\[1\.0, 2\.0, 3\.0\]\)/);
  await box.fill("x = np.array([0.0, 0.0, 0.0, 0.0])\naxis = -1");
  await page.getByTestId("run").click();
  await expect(page.getByTestId("result-status")).toHaveText("Accepted", { timeout: PY_READY });
  await page.getByTestId("result-pill-3").click();
  await expect(page.getByTestId("result-output")).toHaveText("[0.25, 0.25, 0.25, 0.25]");
});

test("applied track: retry-with-backoff (gc_runtime) is Accepted with its solution", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("problem-table")).toContainText("Retry LLM Calls with Backoff and Jitter");
  await openProblem(page, "retry-with-backoff");
  await setCode(page, solution("0124-retry-with-backoff"));
  await page.getByTestId("submit").click();
  await expect(page.getByTestId("result-status")).toHaveText("Accepted", { timeout: PY_READY });
});

const fixture = JSON.parse(readFileSync(resolve(ROOT, "web/e2e/fixtures/design-fixture.json"), "utf8"));

test("design problem: write, reveal, self-score, mark complete, solved in the list", async ({ page }) => {
  // Serve the design fixture as if build.py had produced it.
  await page.route("**/problems/index.json", async (route) => {
    const res = await route.fetch();
    const idx = await res.json();
    const m = fixture.meta;
    idx.problems = idx.problems.filter((p: { slug: string }) => p.slug !== m.slug);
    idx.problems.push({ id: m.id, slug: m.slug, title: m.title, difficulty: m.difficulty, category: m.category, tags: m.tags, track: "design", type: "design" });
    await route.fulfill({ response: res, json: idx });
  });
  await page.route(`**/problems/${fixture.meta.slug}.json`, (route) => route.fulfill({ json: fixture }));

  await page.goto(`/problems/${fixture.meta.slug}`);
  await expect(page.getByTestId("problem-title")).toContainText(fixture.meta.title);
  await expect(page.locator(".monaco-editor")).toHaveCount(0);
  await expect(page.getByTestId("mark-complete")).toBeDisabled();

  const answer = page.getByTestId("answer-1");
  await expect(answer).toHaveAttribute("placeholder", fixture.rubric.sections[0].prompt);
  await answer.fill("Shoppers who want a refund. Success: 60% of returns resolved without a human.");
  await page.getByTestId("pillar-timer-A").click();
  await page.waitForTimeout(1200);
  await expect(page.getByTestId("total-timer")).not.toContainText("00:00 /");

  await page.getByTestId("tab-answer").click();
  await page.getByTestId("reveal").click();
  await page.getByTestId("reveal-yes").click();
  await expect(page.getByTestId("model-answer")).toContainText("1. Scenario");
  await expect(page.getByTestId("model-answer")).toContainText("15. Build Order");

  for (const sec of fixture.rubric.sections) {
    for (let i = 0; i < sec.criteria.length; i++) await page.getByTestId(`criterion-${sec.n}-${i}`).check();
  }
  const total = fixture.rubric.sections.reduce((a: number, s: { criteria: string[] }) => a + s.criteria.length, 0);
  await expect(page.getByTestId("overall-score")).toContainText(`${total}/${total}`);
  await expect(page.getByTestId("pillar-score-A")).toBeVisible();

  await page.getByTestId("mark-complete").click();
  await expect(page.getByTestId("complete-note")).toContainText("Marked complete");

  // The draft survives a reload.
  await page.reload();
  await expect(page.getByTestId("answer-1")).toHaveValue(/60% of returns/);

  await page.getByTestId("problem-list-link").click();
  await page.getByTestId("track-design").click();
  const row = page.getByTestId("problem-row").filter({ hasText: fixture.meta.title });
  await expect(row).toBeVisible();
  await expect(row.getByLabel("Solved")).toBeVisible();
});

test("Detailed Explanation tab renders the walkthrough with math", async ({ page }) => {
  await openProblem(page, "react-tool-loop");
  await page.getByTestId("tab-explanation").click();
  await expect(page.getByRole("heading", { name: "Detailed Explanation" })).toBeVisible();
  await expect(page.getByText("What the problem is really asking")).toBeVisible();

  await openProblem(page, "stable-softmax");
  await page.getByTestId("tab-explanation").click();
  await expect(page.locator(".katex").first()).toBeVisible();

  await page.goto("/problems/returns-refunds-agent");
  await expect(page.getByTestId("problem-title")).toBeVisible();
  await page.getByTestId("tab-explanation").click();
  await expect(page.getByRole("heading", { name: "Detailed Explanation" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Build Order" })).toBeVisible();
});

test("AI Leadership track: ten sections, leadership pillars, self-score and complete", async ({ page }) => {
  const rubric = JSON.parse(readFileSync(resolve(ROOT, "problems/0301-build-buy-fine-tune/rubric.json"), "utf8"));
  await page.goto("/");
  await page.getByTestId("track-leadership").click();
  const rows = page.getByTestId("problem-row");
  await expect(rows.first()).toBeVisible();
  // Every leadership case is in the 301-399 range.
  for (const title of await rows.allTextContents()) expect(title).toMatch(/\b3\d\d\. /);

  await page.goto("/problems/build-buy-fine-tune");
  await expect(page.getByTestId("problem-title")).toContainText("Build vs Buy vs Fine-tune");
  await expect(page.locator(".monaco-editor")).toHaveCount(0);
  await expect(page.getByText("AI Leadership", { exact: true }).first()).toBeVisible();
  for (const [key, name] of [["A", "Frame"], ["B", "Decide"], ["C", "Execute"], ["D", "Land"]])
    await expect(page.getByTestId(`pillar-${key}`)).toContainText(name);
  await expect(page.getByTestId("answer-1")).toHaveAttribute("placeholder", rubric.sections[0].prompt);
  await expect(page.getByTestId("section-10")).toContainText("Communication");
  await expect(page.getByTestId("section-11")).toHaveCount(0);

  await page.getByTestId("answer-1").fill("Ship to renewing enterprise customers by month 6 without breaking their contracts.");
  await page.getByTestId("tab-answer").click();
  await page.getByTestId("reveal").click();
  await page.getByTestId("reveal-yes").click();
  await expect(page.getByTestId("model-answer")).toContainText("1. Situation");
  await expect(page.getByTestId("model-answer")).toContainText("10. Communication");

  // 70% of criteria completes the case.
  const all = rubric.sections.flatMap((s: { n: number; criteria: string[] }) => s.criteria.map((_, i) => [s.n, i]));
  const need = Math.ceil(all.length * 0.7);
  for (const [n, i] of all.slice(0, need)) await page.getByTestId(`criterion-${n}-${i}`).check();
  await page.getByTestId("mark-complete").click();
  await expect(page.getByTestId("complete-note")).toContainText("Marked complete");

  await page.getByTestId("problem-list-link").click();
  await page.getByTestId("track-leadership").click();
  const row = page.getByTestId("problem-row").filter({ hasText: "Build vs Buy vs Fine-tune" });
  await expect(row.getByLabel("Solved")).toBeVisible();
});

test("leadership study plans list their cases", async ({ page }) => {
  for (const [id, title, slugs] of [
    ["principal-architect-loop", "Principal / AI Architect Loop", 13],
    ["director-executive-loop", "Director / Executive Loop", 22],
  ] as const) {
    await page.goto(`/study-plans/${id}`);
    await expect(page.getByTestId("plan-title")).toContainText(title);
    await expect(page.getByTestId("plan-section").first()).toBeVisible();
    await expect(page.locator('[data-testid="plan-section"] a[href*="/problems/"]')).toHaveCount(slugs);
  }
});
