from app.services import llm, voice_profiles
from app.services.voice_profiles import devanagari

TEXT = "Aaj hum Python samjhenge."


def answer(words):
    return lambda *a, **k: ({"words": words}, "test")


def test_devanagari_uses_aligned_answer(monkeypatch):
    monkeypatch.setattr(llm, "chat_json", answer(["आज", "हम", "Python", "समझेंगे।"]))
    assert devanagari(TEXT) == "आज हम Python समझेंगे।"


def test_devanagari_rejects_dropped_or_changed_words(monkeypatch):
    monkeypatch.setattr(llm, "chat_json", answer(["आज", "Python", "समझेंगे"]))
    assert devanagari(TEXT) == TEXT
    monkeypatch.setattr(llm, "chat_json", answer(["आज", "हम", "Java", "समझेंगे"]))
    assert devanagari(TEXT) == TEXT


def test_devanagari_falls_back_without_model(monkeypatch):
    def down(*a, **k):
        raise llm.LLMUnavailable("off")

    monkeypatch.setattr(llm, "chat_json", down)
    assert devanagari(TEXT) == TEXT


def test_devanagari_leaves_devanagari_alone(monkeypatch):
    monkeypatch.setattr(llm, "chat_json", lambda *a, **k: (_ for _ in ()).throw(AssertionError("called")))
    assert devanagari("आज हम Python समझेंगे") == "आज हम Python समझेंगे"


def test_pronunciations_whole_words():
    assert voice_profiles.apply_pronunciations("SQL and MySQL", {"SQL": "sequel"}) == "sequel and MySQL"
