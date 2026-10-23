"""campaign job: local LLM writes the plan (grounded, validated), then tracked CTA links are created."""

from app.core.config import get_settings
from app.core.db import service_client
from app.services import campaign as cg


def run_campaign(ctx) -> dict:
    db = service_client()
    c = db.table("campaigns").select("*").eq("id", ctx.payload["campaign_id"]).single().execute().data
    db.table("campaigns").update({"status": "planning", "error": None}).eq("id", c["id"]).execute()
    ctx.stage("plan", 0.1, "Writing the campaign with the local AI model")
    b = cg.Business.model_validate(c["business"])
    try:
        plan, prov = cg.plan(b, c["language"])
    except Exception as e:
        db.table("campaigns").update({"status": "failed", "error": f"{type(e).__name__}: {e}"[:500]}).eq("id", c["id"]).execute()
        raise
    ctx.stage("links", 0.85, "Creating tracked CTA links")
    db.table("tracked_links").delete().eq("campaign_id", c["id"]).execute()
    links = []
    for r in plan["reels"]:
        for link in cg.links_for(b, c["code"], r["key"]):
            links.append({"slug": cg.new_slug(), "organization_id": c["organization_id"], "campaign_id": c["id"],
                          "reel_key": r["key"], **link})
    if not links:  # no WhatsApp/website given: the hosted inquiry form is the CTA, so results stay measurable
        slug = cg.new_slug()
        links.append({"slug": slug, "organization_id": c["organization_id"], "campaign_id": c["id"], "reel_key": "",
                      "kind": "website", "destination": f"{get_settings().site_url.rstrip('/')}/i/{slug}"})
    db.table("tracked_links").insert(links).execute()
    db.table("campaigns").update({"plan": plan, "provenance": prov, "status": "ready"}).eq("id", c["id"]).execute()
    return {"campaign_id": c["id"], "reels": len(plan["reels"]), "links": len(links), "engine": prov["engine"]}
