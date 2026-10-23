from app.api.collections import build

UNITS = [
    {"start_s": 0, "end_s": 60, "title": "What a function is", "topic": "Python functions"},
    {"start_s": 60, "end_s": 120, "title": "Parameters and return", "topic": "Python functions"},
    {"start_s": 120, "end_s": 200, "title": "Base case", "topic": "Recursion"},
    {"start_s": 200, "end_s": 260, "title": "Common mistakes", "topic": "Recursion"},
    {"start_s": 260, "end_s": 300, "title": "Summary", "topic": "Recap"},
]
HL = [
    {"id": "h3", "start_s": 125, "end_s": 170, "title": "Why recursion needs a base case", "transcript_excerpt": "base case..."},
    {"id": "h1", "start_s": 5, "end_s": 50, "title": "Functions explained", "transcript_excerpt": "a function..."},
    {"id": "h2", "start_s": 65, "end_s": 110, "title": "Return values", "transcript_excerpt": "return..."},
    {"id": "h4", "start_s": 205, "end_s": 250, "title": "Recursion mistakes", "transcript_excerpt": "mistake..."},
    {"id": "h5", "start_s": 262, "end_s": 298, "title": "Summary of the class", "transcript_excerpt": "so today..."},
]


def test_series_follow_outline_topics_in_class_order():
    cols = build(HL, UNITS)
    topics = {c["topic"]: [e["highlight_id"] for e in c["episodes"]] for c in cols}
    assert topics["Python functions"] == ["h1", "h2"] and topics["Recursion"] == ["h3", "h4"]
    assert "Recap" not in topics  # a single clip is not a series
    full = next(c for c in cols if c["title"] == "Full class series")
    assert [e["highlight_id"] for e in full["episodes"]] == ["h1", "h2", "h3", "h4", "h5"]
    # every title comes from the recording's own outline/highlights
    known = {u["topic"] for u in UNITS} | {"Full class series"}
    assert all(c["topic"] in known or c["title"] in known for c in cols)
    assert all(e["steps"] and e["quote"] for c in cols for e in c["episodes"])
