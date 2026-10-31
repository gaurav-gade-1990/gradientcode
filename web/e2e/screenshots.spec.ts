// Dark-theme screenshots into web/screenshots/. Skipped unless SCREENSHOTS=1:
//   SCREENSHOTS=1 pnpm exec playwright test screenshots
import { expect, test, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const OUT = resolve(ROOT, "web/screenshots");
const fixture = JSON.parse(readFileSync(resolve(ROOT, "web/e2e/fixtures/design-fixture.json"), "utf8"));
const solution = (dir: string) => readFileSync(resolve(ROOT, "problems", dir, "solution.py"), "utf8");

test.skip(!process.env.SCREENSHOTS, "set SCREENSHOTS=1 to capture screenshots");
test.setTimeout(240_000);

async function setCode(page: Page, code: string) {
  await page.locator(".monaco-editor .view-lines").first().click();
  await page.evaluate(() => {
    window.__gcEditor?.setValue("");
    window.__gcEditor?.focus();
  });
  await page.evaluate((c) => navigator.clipboard.writeText(c), code);
  await page.keyboard.press("ControlOrMeta+V");
}

test("capture", async ({ page, context }) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  await page.route("**/problems/index.json", async (route) => {
    const res = await route.fetch();
    const idx = await res.json();
    const m = fixture.meta;
    if (!idx.problems.some((p: { slug: string }) => p.slug === m.slug))
      idx.problems.push({ id: m.id, slug: m.slug, title: m.title, difficulty: m.difficulty, category: m.category, tags: m.tags, track: "design", type: "design" });
    await route.fulfill({ response: res, json: idx });
  });
  await page.route(`**/problems/${fixture.meta.slug}.json`, (route) => route.fulfill({ json: fixture }));
  await page.goto("/");
  await page.evaluate(() => localStorage.clear());

  // Solve two problems for real so the list, plan and profile show progress.
  for (const [slug, dir] of [
    ["stable-softmax", "0001-stable-softmax"],
    ["retry-with-backoff", "0124-retry-with-backoff"],
  ]) {
    await page.goto(`/problems/${slug}`);
    await expect(page.getByTestId("run")).toBeEnabled({ timeout: 90_000 });
    await setCode(page, solution(dir));
    await page.getByTestId("submit").click();
    await expect(page.getByTestId("result-status")).toHaveText("Accepted", { timeout: 90_000 });
  }
  await page.screenshot({ path: `${OUT}/applied-problem.png` });

  await page.goto("/problems/stable-softmax");
  await expect(page.getByTestId("run")).toBeEnabled({ timeout: 90_000 });
  await page.screenshot({ path: `${OUT}/problem.png` });
  await setCode(page, "import numpy as np\n\n\ndef softmax(x, axis=-1):\n    e = np.exp(x)\n    print(e.sum())\n    return e / e.sum()\n");
  await page.getByTestId("run").click();
  await expect(page.getByTestId("result-status")).toBeVisible({ timeout: 90_000 });
  await page.getByTestId("result-pill-2").click();
  await page.screenshot({ path: `${OUT}/result-run.png` });
  await setCode(page, solution("0001-stable-softmax"));
  await page.getByTestId("submit").click();
  await expect(page.getByTestId("result-status")).toHaveText("Accepted", { timeout: 90_000 });
  await page.screenshot({ path: `${OUT}/result-submit.png` });

  await page.goto("/");
  await expect(page.getByTestId("problem-row").first()).toBeVisible();
  await page.screenshot({ path: `${OUT}/list-applied.png` });
  await page.getByTestId("track-ml").click();
  await page.screenshot({ path: `${OUT}/list-ml.png` });
  await page.getByTestId("track-applied").click();

  await page.goto(`/problems/${fixture.meta.slug}`);
  await page.getByTestId("answer-1").fill("Shoppers who want a refund or exchange.\n\n- Success: **60%** of returns resolved with no human\n- Out of scope: warranty claims");
  await page.getByTestId("answer-2").fill("Web chat -> agent (LiteLLM) -> MCP tools (orders, refunds) -> Postgres + pgvector");
  await page.screenshot({ path: `${OUT}/design-before-reveal.png` });
  await page.getByTestId("tab-answer").click();
  await page.getByTestId("reveal").click();
  await page.screenshot({ path: `${OUT}/design-reveal-confirm.png` });
  await page.getByTestId("reveal-yes").click();
  for (const sec of fixture.rubric.sections) for (let i = 0; i < sec.criteria.length; i++) if ((sec.n + i) % 4 !== 0) await page.getByTestId(`criterion-${sec.n}-${i}`).check();
  await page.getByTestId("mark-complete").click();
  await page.screenshot({ path: `${OUT}/design-after-reveal.png` });

  await page.goto("/study-plans");
  await expect(page.getByTestId("plan-card").first()).toBeVisible();
  await page.screenshot({ path: `${OUT}/study-plans.png` });
  await page.goto("/study-plans/ml-fundamentals");
  await expect(page.getByTestId("plan-title")).toBeVisible();
  await page.screenshot({ path: `${OUT}/study-plan.png` });
  await page.goto("/study-plans/fde-interview-loop");
  await expect(page.getByTestId("plan-title")).toBeVisible();
  await page.screenshot({ path: `${OUT}/study-plan-fde.png` });

  await page.goto("/profile");
  await expect(page.getByTestId("heatmap")).toBeVisible();
  await page.screenshot({ path: `${OUT}/profile.png`, fullPage: true });

  await page.goto("/");
  await page.getByTestId("theme-toggle").click();
  await page.getByTestId("track-ml").click();
  await page.screenshot({ path: `${OUT}/list-light.png` });
  await page.getByTestId("theme-toggle").click();
});
