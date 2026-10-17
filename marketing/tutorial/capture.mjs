// Captures real Reel Studio screens (local stack, synthetic test data) for the Hyperframes tutorial.
// Usage: node marketing/tutorial/capture.mjs   (web on :3000, API on :8001, local Supabase running)
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
const require = createRequire(process.env.HF_NODE_MODULES + "/");
const puppeteer = require("puppeteer-core");
const PASSWORD = readFileSync("apps/api/tests/test_upload_integration.py", "utf8").match(/PASSWORD\s*=\s*"([^"]+)"/)[1];
const OUT = "marketing/tutorial/assets/screens";
const BASE = "http://localhost:3000";
const EMPTY_PROJECT = process.env.EMPTY_PROJECT;
// Text of UI elements whose on-screen boxes the tutorial camera/cursor targets (CSS px of a 1600x900 viewport).
const TARGETS = {
  dashboard: ["Use a recording", "Create from a topic", "Recent projects"],
  uploader: ["Drop a class recording here"],
  "recording-top": ["Recording & transcript", "useEffect", "Search words or terms"],
  "recording-highlights": ["Custom Hook with useEffect in React", "Play / pause clip"],
  "topic-studio": ["What should the video explain?", "Generate new version", "Preview"],
  "topic-script": ["Script & storyboard", "XML Works"],
  editor: ["Caption words", "Shift all"],
  "editor-recording": ["Style", "Captions", "Render MP4 with edits"],
  publishing: ["Instagram account", "Connect Instagram", "Prepare a post"],
};
const shots = [
  ["dashboard", "/dashboard"],
  ["recordings", "/recordings"],
  ["uploader", "/projects/" + EMPTY_PROJECT],
  ["recording-top", "/projects/10fb1100-8c9c-41ba-9f82-33f5ed4d0888"],
  ["recording-highlights", "/projects/10fb1100-8c9c-41ba-9f82-33f5ed4d0888", "Highlights & exports"],
  ["topic-studio", "/projects/a247cf7b-06e0-4499-8991-b0dd16f7b62d"],
  ["topic-script", "/projects/a247cf7b-06e0-4499-8991-b0dd16f7b62d", "Script & storyboard"],
  ["editor", "/editor/95d94b51-5c3b-4405-8b5c-e1b36c6c913b"],
  ["editor-recording", "/editor/a325cf54-b681-452b-b18b-61fee66b1d73"],
  ["publishing", "/publishing"],
  ["brand", "/brand"],
];
const browser = await puppeteer.launch({ executablePath: process.env.CHROME, args: ["--autoplay-policy=no-user-gesture-required"] });
const page = await browser.newPage();
await page.setViewport({ width: 1600, height: 900, deviceScaleFactor: 2 });
await page.goto(BASE + "/login", { waitUntil: "networkidle2" });
await page.type("input[name=email]", "upload-owner@test.local");
await page.type("input[name=password]", PASSWORD);
await Promise.all([page.waitForNavigation({ waitUntil: "networkidle2" }), page.click("button[type=submit]")]);
const allRects = {};
for (const [name, path, heading] of shots) {
  await page.goto(BASE + path, { waitUntil: "networkidle2" });
  await new Promise((r) => setTimeout(r, path.startsWith("/editor") ? 9000 : 4000));
  if (heading) await page.evaluate((h) => { const el = [...document.querySelectorAll("h2")].find((x) => x.textContent?.includes(h)); el?.scrollIntoView({ block: "start" }); window.scrollBy(0, -80); }, heading);
  if (path.startsWith("/editor")) {  // show a real frame in the preview instead of the intro card
    await page.evaluate((t) => document.querySelector("iframe")?.contentWindow?.postMessage({ type: "rs-seek", t }, "*"), name === "editor" ? 18 : 9);
    await new Promise((r) => setTimeout(r, 2500));
  }
  if (name === "editor") await page.evaluate(() => document.querySelector('[aria-label^="Captions item"]')?.dispatchEvent(new PointerEvent("pointerdown", { bubbles: true })));
  await new Promise((r) => setTimeout(r, 1500));
  const rects = await page.evaluate((texts) => Object.fromEntries(texts.map((t) => {
    const all = [...document.querySelectorAll("body *")].filter((e) => e.children.length < 4 && e.textContent?.trim().startsWith(t) && e.getBoundingClientRect().width > 0);
    const el = all.sort((a, b) => a.getBoundingClientRect().width * a.getBoundingClientRect().height - b.getBoundingClientRect().width * b.getBoundingClientRect().height)[0];
    const r = el?.getBoundingClientRect();
    return [t, r ? { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) } : null];
  })), TARGETS[name] ?? []);
  allRects[name] = rects;
  await page.screenshot({ path: `${OUT}/${name}.jpg`, type: "jpeg", quality: 88 });
  console.log("captured", name);
}
(await import("node:fs")).writeFileSync(OUT + "/rects.json", JSON.stringify(allRects, null, 1));
await browser.close();
