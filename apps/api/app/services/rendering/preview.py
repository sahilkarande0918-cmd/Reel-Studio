"""Editor preview: the export compiler's own HTML plus a small browser runtime that does what the
Hyperframes renderer does at render time (show clips in their window, seek GSAP, sync media).
The editor therefore previews exactly the composition that will be rendered."""

import hashlib
import json
import re
import shutil
from pathlib import Path

from app.services.rendering import compose

SAFE_PATH = re.compile(r"^(fonts/)?[A-Za-z0-9_.-]+$")

RUNTIME = """<script>
(() => {
  const tl = window.__timelines.main, D = tl.duration();
  const clips = [...document.querySelectorAll("[data-start]")].filter((e) => e.id !== "root");
  const media = [...document.querySelectorAll("video,audio")];
  let t = 0, playing = false, last = 0;
  const say = (type) => parent.postMessage({ type, t, playing, duration: D }, "*");
  function apply(hard) {
    for (const el of clips) {
      const s = +el.dataset.start, d = +el.dataset.duration;
      el.style.visibility = t >= s && t < s + d ? "" : "hidden";
    }
    tl.seek(t, false);
    for (const m of media) {
      const s = +m.dataset.start, d = +m.dataset.duration, from = +(m.dataset.mediaStart || 0);
      m.volume = Math.max(0, Math.min(1, +(m.dataset.volume ?? 1)));
      if (t >= s && t < s + d) {
        const want = from + t - s;
        if (hard || Math.abs(m.currentTime - want) > 0.3) m.currentTime = want;
        if (playing && m.paused) m.play().catch(() => {});
        if (!playing && !m.paused) m.pause();
      } else if (!m.paused) m.pause();
    }
    say("rs-time");
  }
  function frame(now) {
    if (!playing) return;
    t += (now - last) / 1000; last = now;
    if (t >= D) { t = D; playing = false; }
    apply(false);
    if (playing) requestAnimationFrame(frame);
  }
  addEventListener("message", (e) => {
    const m = e.data || {};
    if (m.type === "rs-seek") { t = Math.max(0, Math.min(D, +m.t || 0)); apply(true); }
    if (m.type === "rs-play") { if (t >= D - 0.05) t = 0; playing = true; last = performance.now(); apply(true); requestAnimationFrame(frame); }
    if (m.type === "rs-pause") { playing = false; apply(true); }
  });
  t = +(window.RS_START || 0); apply(true); say("rs-ready");
})();
</script>"""


def write_preview(doc: dict, project_dir: Path) -> str:
    """Write `preview-<hash>.html` (and any fonts/GSAP it needs) into the render directory; returns its name."""
    (project_dir / "fonts").mkdir(parents=True, exist_ok=True)
    for family in dict.fromkeys(doc["brand"]["fonts"].values()):
        name = compose.FONT_FILES[family][0]
        if not (project_dir / "fonts" / name).exists():
            shutil.copyfile(compose.FONTS_DIR / name, project_dir / "fonts" / name)
    if not (project_dir / compose.GSAP_FILE.name).exists():
        shutil.copyfile(compose.GSAP_FILE, project_dir / compose.GSAP_FILE.name)
    page = compose.compile_html(doc).replace("</body>", RUNTIME + "\n  </body>")
    name = f"preview-{hashlib.sha256(json.dumps(doc, sort_keys=True).encode()).hexdigest()[:12]}.html"
    for old in project_dir.glob("preview-*.html"):
        if old.name != name:
            old.unlink(missing_ok=True)
    (project_dir / name).write_text(page, encoding="utf-8")
    return name
