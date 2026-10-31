// Local rehearsal of the artifact host: serve dist-artifact from a subpath, block every other host, submit a solution.
import { chromium } from "@playwright/test";
import fs from "node:fs";
const base = process.argv[2];
const solution = fs.readFileSync(process.argv[3], "utf8");
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const blocked = [];
await page.route("**/*", (r) => {
  const u = new URL(r.request().url());
  if (u.hostname !== "localhost" && u.hostname !== "127.0.0.1") { blocked.push(u.href); return r.abort(); }
  return r.continue();
});
page.on("pageerror", (e) => console.log("pageerror:", e.message));
await page.goto(base + "index.html");
await page.getByText("ReAct Tool Loop").first().waitFor({ timeout: 30000 });
console.log("list rendered");
await page.goto(base + "index.html#/problems/stable-softmax");
await page.waitForFunction(() => window.__gcEditor, null, { timeout: 30000 });
await page.evaluate((code) => window.__gcEditor.setValue(code), solution);
await page.getByRole("button", { name: /Submit/ }).click();
await page.getByText("Accepted", { exact: true }).first().waitFor({ timeout: 120000 });
console.log("submit: Accepted");
console.log("blocked external requests:", blocked.length, blocked.slice(0, 5));
await page.screenshot({ path: process.argv[4] });
await browser.close();
