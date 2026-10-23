"""Campaign agent API: queue a plan, read results (clicks, inquiries) and grounded suggestions."""

from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.access import require_role
from app.core.auth import User, current_user
from app.core.db import service_client
from app.services import campaign as cg

router = APIRouter(prefix="/campaigns")


class CampaignRequest(BaseModel):
    org_id: str
    business: cg.Business
    language: Literal["en", "hi", "hinglish"] = "en"


@router.post("", status_code=202)
def create(body: CampaignRequest, user: User = Depends(current_user)) -> dict:
    require_role(body.org_id, user, write=True)
    db = service_client()
    job = db.table("jobs").insert({"organization_id": body.org_id, "job_type": "campaign", "created_by": user.id,
                                   "current_stage": "queued", "payload": {}}).execute().data[0]
    row = db.table("campaigns").insert({"organization_id": body.org_id, "created_by": user.id, "code": cg.code_for(body.business.name),
                                        "business": body.business.model_dump(), "language": body.language, "job_id": job["id"]}).execute().data[0]
    db.table("jobs").update({"payload": {"campaign_id": row["id"]}}).eq("id", job["id"]).execute()
    return {"campaign_id": row["id"], "job_id": job["id"], "code": row["code"]}

