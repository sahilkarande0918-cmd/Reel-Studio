"""Speech-aware, non-destructive pacing for a clip: which stretches of the source to keep.

Presets shorten pauses (never remove all of them), drop pure filler sounds and immediate stutters; words that carry
meaning are never removed. The result is a list of source spans: the original media is untouched and the cuts are
plain timeline items (one video item per span), so every cut is editable and reversible.

  natural   conversational rhythm: only long dead air is shortened (> 0.9 s → 0.6 s)
  engaging  dead air removed (> 0.55 s → 0.3 s), "um/uh" sounds and stutters removed
  fast      tight Shorts pacing (> 0.35 s → 0.18 s); sentence ends still keep a short breath
"""

import re

PRESETS = {
    "natural": {"gap": 0.9, "keep": 0.6, "sentence_keep": 0.6, "fillers": False, "stutters": False},
    "engaging": {"gap": 0.55, "keep": 0.3, "sentence_keep": 0.42, "fillers": True, "stutters": True},
    "fast": {"gap": 0.35, "keep": 0.18, "sentence_keep": 0.26, "fillers": True, "stutters": True},
}
# sounds only: "like", "you know", "matlab" can carry meaning and are never removed automatically
FILLER = re.compile(r"^(um+|uh+|erm+|er|ah+|hmm+|mm+|uhm+|umm+)[.,!?…]*$", re.I)
MIN_SPAN_S = 0.25
EDGE_S = 0.04  # never cut closer than this to a spoken word (no clipped syllables)


def _text(w: dict) -> str:
    return (w.get("corrected_text") or "").strip()


def _norm(t: str) -> str:
    return re.sub(r"[^\w']", "", t.lower())


def plan(words: list[dict], start: float, end: float, preset: str = "natural") -> dict:
    """{spans: [[src_start, src_end], ...], removed: [{kind, start_s, end_s, text}], saved_s}."""
    p = PRESETS.get(preset, PRESETS["natural"])
    ws = [w for w in sorted(words, key=lambda w: w["start_s"]) if _text(w) and start <= (w["start_s"] + w["end_s"]) / 2 <= end]
    removed: list[dict] = []
    keep: list[dict] = []
    for i, w in enumerate(ws):
        t = _text(w)
        if p["fillers"] and FILLER.match(t):
            removed.append({"kind": "filler", "start_s": w["start_s"], "end_s": w["end_s"], "text": t})
            continue
        nxt = ws[i + 1] if i + 1 < len(ws) else None
        if p["stutters"] and nxt and _norm(t) and _norm(t) == _norm(_text(nxt)) and nxt["start_s"] - w["end_s"] < 0.6 \
                and len(_norm(t)) <= 6:
            removed.append({"kind": "repeat", "start_s": w["start_s"], "end_s": w["end_s"], "text": t})
            continue
        keep.append(w)
    if not keep:
        return {"spans": [[round(start, 3), round(end, 3)]], "removed": [], "saved_s": 0.0, "preset": preset}
    spans: list[list[float]] = []
    a = max(start, keep[0]["start_s"] - min(p["keep"], 0.25))
    for w, nxt in zip(keep, keep[1:], strict=False):
        gap = nxt["start_s"] - w["end_s"]
        sentence_end = _text(w)[-1:] in ".?!।"
        limit = p["sentence_keep"] if sentence_end else p["keep"]
        skipped = any(w["end_s"] <= r["start_s"] < nxt["start_s"] for r in removed)
        if gap > (limit if skipped else max(p["gap"], limit)):
            # keep `limit` of the pause, split around the words so the join sits in silence
            half = limit / 2
            spans.append([a, w["end_s"] + max(half, EDGE_S)])
            if not skipped:
                removed.append({"kind": "pause", "start_s": w["end_s"], "end_s": nxt["start_s"], "text": ""})
            a = nxt["start_s"] - max(half, EDGE_S)
    spans.append([a, min(end, keep[-1]["end_s"] + min(p["keep"], 0.35))])
    merged: list[list[float]] = []
    for s in spans:
        if merged and s[0] - merged[-1][1] < 0.05:
            merged[-1][1] = s[1]
        elif s[1] - s[0] >= MIN_SPAN_S or not merged:
            merged.append(s)
        else:
            merged[-1][1] = s[1]
    merged = [[round(x, 3), round(y, 3)] for x, y in merged]
    kept = sum(y - x for x, y in merged)
    return {"spans": merged, "removed": removed, "saved_s": round((end - start) - kept, 2), "preset": preset}


def remap(words: list[dict], spans: list[list[float]]) -> list[dict]:
    """Words that fall inside the kept spans, on the edited clock (spans play back to back in order)."""
    out, off = [], 0.0
    for a, b in spans:
        for w in words:
            mid = (w["start_s"] + w["end_s"]) / 2
            if a <= mid <= b and _text(w):
                s = round(off + max(w["start_s"], a) - a, 3)
                e = round(off + min(w["end_s"], b) - a, 3)
                out.append({**w, "clip_start": s, "clip_end": max(e, s)})
        off += b - a
    return out
