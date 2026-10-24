from app.services import campaign as cg

B = cg.Business(name="Kicks Corner", industry="sneaker store", audience="college students", offer="10% off on Diwali week",
                city="Pune", whatsapp="+919876543210", website="https://example.com/shop")


def test_grounding_keeps_the_owners_offer_and_drops_invented_numbers_and_claims():
    text, notes = cg.ground("Get 10% off on Diwali week. Flat 50% off today! Rated 5-star by customers. Visit us.", B)
    assert "10% off" in text and "50%" not in text and "Rated" not in text and "Visit us." in text
    assert len(notes) == 2


def test_brand_name_spelling_is_restored():
    assert cg._restore_name("Come to kicks  corner and KICKS CORNER today", ["Kicks Corner"]) == "Come to Kicks Corner and Kicks Corner today"


def test_tracked_links_carry_campaign_and_reel():
    links = cg.links_for(B, "kicks-corner-ab12", "r2")
    wa = next(x for x in links if x["kind"] == "whatsapp")["destination"]
    web = next(x for x in links if x["kind"] == "website")["destination"]
    assert wa.startswith("https://wa.me/919876543210?text=") and "kicks-corner-ab12%2Fr2" in wa
    assert "utm_campaign=kicks-corner-ab12" in web and "utm_content=r2" in web and "utm_source=instagram" in web


def test_rules_plan_validates():
    p = cg.Plan.model_validate(cg.rules_plan(B, "en"))
    assert len(p.reels) == 4 and all(r.cta for r in p.reels)


def test_language_check_asks_for_hinglish_or_devanagari():
    assert cg._lang_issue("Big Diwali sale for sneakers", "hinglish")
    assert not cg._lang_issue("Diwali ke liye naye sneakers dekho, abhi aao", "hinglish")
    assert cg._lang_issue("Diwali sale", "hi") and not cg._lang_issue("दिवाली पर नए स्नीकर्स देखिए, अभी आइए और ऑफ़र पाइए", "hi")


def test_every_goal_plans_distinct_formats():
    assert all(len(set(v)) == len(v) == 5 and set(v) <= set(cg.FORMATS) for v in cg.BY_GOAL.values())


def test_similar_hook_catches_rephrasings():
    from app.services.campaign import similar_hook

    used = ["diwali ke liye naye sneakers chahiye?"]
    assert similar_hook("Diwali ke liye naye sneakers chahiye kya?", used)
    assert not similar_hook("Office ke baad gym? Yeh shoes try karo", used)
