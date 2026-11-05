"""Uploaded subtitles (.srt) instead of speech recognition: cues → segments and word timings.

Each cue's words are spread over the cue in proportion to their length ("srt-even" timing: as good as the SRT's own
timing, not word-exact like ASR). Tags (<i>, {\\an8}) and speaker dashes are removed; the words are kept verbatim.
"""

import re

TIME = re.compile(r"(\d+):(\d{2}):(\d{2})[,.](\d{1,3})\s*-->\s*(\d+):(\d{2}):(\d{2})[,.](\d{1,3})")
TAG = re.compile(r"<[^>]+>|\{[^}]*\}")
MAX_BYTES = 2 * 1024 * 1024


def _s(h, m, s, ms) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms.ljust(3, "0")) / 1000


def parse(text: str) -> list[dict]:
    """[{start_s, end_s, text}] in time order; raises ValueError when nothing usable is found."""
    cues = []
    for block in re.split(r"\r?\n\s*\r?\n", text.replace("﻿", "").strip()):
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        for i, ln in enumerate(lines):
            m = TIME.search(ln)
            if m:
                body = " ".join(TAG.sub("", x).lstrip("-– ").strip() for x in lines[i + 1 :]).strip()
                a, b = _s(*m.groups()[:4]), _s(*m.groups()[4:])
                if body and b > a:
                    cues.append({"start_s": a, "end_s": b, "text": re.sub(r"\s+", " ", body)})
                break
    if not cues:
        raise ValueError("No subtitles found: expected SRT cues like '00:00:01,000 --> 00:00:03,500'")
    return sorted(cues, key=lambda c: c["start_s"])


def to_words(cues: list[dict]) -> tuple[list[dict], list[dict]]:
    """(segments, words) in the transcript_segments / transcript_words shape used by the ASR path."""
    segments, words = [], []
    for si, c in enumerate(cues):
        segments.append({"idx": si, "start_s": c["start_s"], "end_s": c["end_s"], "raw_text": c["text"],
                         "avg_logprob": 0.0, "no_speech_prob": 0.0})
        toks = c["text"].split()
        total = sum(len(t) + 1 for t in toks)
        t, span = c["start_s"], c["end_s"] - c["start_s"]
        for tok in toks:
            d = span * (len(tok) + 1) / total
            words.append({"idx": len(words), "segment_idx": si, "start_s": round(t, 3),
                          "end_s": round(t + d * 0.92, 3), "raw_text": tok, "confidence": 1.0})
            t += d
    return segments, words
