"""Clipping-campaign brief checks (e.g. an approved Clipadi/Clipster campaign): length limits, required caption text,
hashtags and mentions, an originality/transformation flag and duplicate-submission warnings.

Passing these checks only means the export follows the brief as written. It never guarantees approval, payment, views
or monetisation; nothing here publishes anything, and the source-rights confirmation is the user's statement.
"""

import re

from pydantic import BaseModel, Field


class Brief(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    source_rights_confirmed: bool  # "I am authorised to clip this source for this campaign"
    topic: str = Field(default="", max_length=300)
    min_s: float = Field(default=0, ge=0, le=600)
    max_s: float = Field(default=180, gt=0, le=600)
    hashtags: list[str] = Field(default_factory=list, max_length=30)
    mentions: list[str] = Field(default_factory=list, max_length=10)
    required_text: str = Field(default="", max_length=500)
    platforms: list[str] = Field(default_factory=list, max_length=6)
    restrictions: str = Field(default="", max_length=1000)
    audience: str = Field(default="", max_length=300)
    brand_guidelines: str = Field(default="", max_length=1000)


def _tag(t: str, sign: str) -> str:
    t = re.sub(r"\s+", "", t.strip())
    return t if t.startswith(sign) else sign + t


def caption(brief: Brief, title: str, insight: str = "") -> str:
    """Export-ready caption: the clip's grounded title and insight, then the brief's required text, mentions, tags."""
    parts = [title.strip()]
    if insight.strip():
        parts.append(insight.strip())
    if brief.required_text.strip():
        parts.append(brief.required_text.strip())
    tail = " ".join([_tag(m, "@") for m in brief.mentions] + [_tag(h, "#") for h in brief.hashtags])
    if tail:
        parts.append(tail)
    return "\n\n".join(parts)[:2200]


def check(brief: Brief, duration_s: float, text: str, caption_text: str, transformed: bool,
          previous: list[dict] | None = None, start_s: float = 0, end_s: float = 0) -> dict:
    """{ok, issues, warnings}. Issues block the export for this campaign; warnings are for the user to review."""
    issues, warnings = [], []
    if not brief.source_rights_confirmed:
        issues.append("Source rights not confirmed for this campaign")
    if duration_s < brief.min_s - 0.05:
        issues.append(f"Too short: {duration_s:.1f} s (campaign minimum {brief.min_s:.0f} s)")
    if duration_s > brief.max_s + 0.05:
        issues.append(f"Too long: {duration_s:.1f} s (campaign maximum {brief.max_s:.0f} s)")
    low = caption_text.lower()
    for h in brief.hashtags:
        if _tag(h, "#").lower() not in low:
            issues.append(f"Caption is missing {_tag(h, '#')}")
    for m in brief.mentions:
        if _tag(m, "@").lower() not in low:
            issues.append(f"Caption is missing {_tag(m, '@')}")
    if brief.required_text.strip() and brief.required_text.strip().lower() not in low:
        issues.append("Caption is missing the campaign's required text")
    if brief.topic.strip():
        words = {w for w in re.findall(r"\w{4,}", brief.topic.lower())}
        if words and not words & set(re.findall(r"\w{4,}", text.lower())):
            warnings.append(f"The clip never mentions the campaign topic ({brief.topic[:60]})")
    if not transformed:
        warnings.append("Low transformation: no captions or edits; many campaigns reject unedited re-uploads")
    for p in previous or []:
        if p.get("campaign") == brief.name and min(end_s, p["end_s"]) - max(start_s, p["start_s"]) > 0.5 * duration_s:
            warnings.append(f"Possible duplicate submission: overlaps a clip already exported for “{brief.name}”")
            break
    return {"ok": not issues, "issues": issues, "warnings": warnings,
            "note": "Checks follow the brief as written; they do not guarantee approval, payment or views."}
