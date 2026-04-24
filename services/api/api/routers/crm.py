"""CRM endpoints: pipeline stages, leads, and activity log."""
from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from api.auth import get_merchant_id
from api.db import postgres
from api.limiter import limiter

router = APIRouter(prefix="/api/v1/crm")

VALID_ACTIVITY_TYPES = {"note", "email", "call", "meeting", "stage_change"}


# ── Schemas ───────────────────────────────────────────────────────────────────

class StageCreate(BaseModel):
    name: str
    color: str = "#6B7280"


class StageUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None
    position: Optional[int] = None


class LeadCreate(BaseModel):
    name: str
    email: Optional[str] = None
    company: Optional[str] = None
    phone: Optional[str] = None
    stage_id: Optional[str] = None
    plan_interest: Optional[str] = None
    mrr_estimate_paise: int = 0
    source: Optional[str] = None
    owner: Optional[str] = None
    notes: Optional[str] = None


class LeadUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None
    phone: Optional[str] = None
    stage_id: Optional[str] = None
    plan_interest: Optional[str] = None
    mrr_estimate_paise: Optional[int] = None
    source: Optional[str] = None
    owner: Optional[str] = None
    notes: Optional[str] = None


class ActivityCreate(BaseModel):
    type: str = "note"
    body: str


class TaskCreate(BaseModel):
    lead_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    assignee: Optional[str] = None
    due_date: Optional[str] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assignee: Optional[str] = None
    due_date: Optional[str] = None
    status: Optional[str] = None


class SequenceCreate(BaseModel):
    name: str


class StepCreate(BaseModel):
    step_num: int
    delay_days: int = 0
    subject: str
    body: str


class EnrollRequest(BaseModel):
    lead_id: str


# ── Stages ────────────────────────────────────────────────────────────────────

@router.get("/stages")
@limiter.limit("60/minute")
def list_stages(
    request: Request,
    merchant_id: Annotated[str, Depends(get_merchant_id)],
):
    return {"stages": postgres.list_pipeline_stages(merchant_id)}


@router.post("/stages", status_code=201)
@limiter.limit("30/minute")
def create_stage(
    request: Request,
    body: StageCreate,
    merchant_id: Annotated[str, Depends(get_merchant_id)],
):
    return postgres.create_pipeline_stage(merchant_id, body.name, body.color)


@router.put("/stages/{stage_id}")
@limiter.limit("60/minute")
def update_stage(
    request: Request,
    stage_id: str,
    body: StageUpdate,
    merchant_id: Annotated[str, Depends(get_merchant_id)],
):
    updated = postgres.update_pipeline_stage(
        merchant_id, stage_id, body.model_dump(exclude_none=True)
    )
    if not updated:
        raise HTTPException(status_code=404, detail="stage not found")
    return updated


@router.delete("/stages/{stage_id}", status_code=204)
@limiter.limit("30/minute")
def delete_stage(
    request: Request,
    stage_id: str,
    merchant_id: Annotated[str, Depends(get_merchant_id)],
):
    ok = postgres.delete_pipeline_stage(merchant_id, stage_id)
    if not ok:
        raise HTTPException(status_code=409, detail="stage has leads or was not found")


# ── Leads ─────────────────────────────────────────────────────────────────────

@router.get("/leads")
@limiter.limit("60/minute")
def list_leads(
    request: Request,
    merchant_id: Annotated[str, Depends(get_merchant_id)],
    stage_id: Optional[str] = None,
):
    return {"leads": postgres.list_crm_leads(merchant_id, stage_id)}


@router.post("/leads", status_code=201)
@limiter.limit("30/minute")
def create_lead(
    request: Request,
    body: LeadCreate,
    merchant_id: Annotated[str, Depends(get_merchant_id)],
):
    return postgres.create_crm_lead(merchant_id, body.model_dump())


@router.get("/leads/{lead_id}")
@limiter.limit("60/minute")
def get_lead(
    request: Request,
    lead_id: str,
    merchant_id: Annotated[str, Depends(get_merchant_id)],
):
    lead = postgres.get_crm_lead(merchant_id, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="lead not found")
    activities = postgres.list_lead_activities(merchant_id, lead_id)
    return {**lead, "activities": activities}


@router.put("/leads/{lead_id}")
@limiter.limit("60/minute")
def update_lead(
    request: Request,
    lead_id: str,
    body: LeadUpdate,
    merchant_id: Annotated[str, Depends(get_merchant_id)],
):
    updated = postgres.update_crm_lead(
        merchant_id, lead_id, body.model_dump(exclude_none=True)
    )
    if not updated:
        raise HTTPException(status_code=404, detail="lead not found")
    return updated


@router.delete("/leads/{lead_id}", status_code=204)
@limiter.limit("30/minute")
def delete_lead(
    request: Request,
    lead_id: str,
    merchant_id: Annotated[str, Depends(get_merchant_id)],
):
    ok = postgres.delete_crm_lead(merchant_id, lead_id)
    if not ok:
        raise HTTPException(status_code=404, detail="lead not found")


@router.post("/leads/{lead_id}/activities", status_code=201)
@limiter.limit("60/minute")
def add_activity(
    request: Request,
    lead_id: str,
    body: ActivityCreate,
    merchant_id: Annotated[str, Depends(get_merchant_id)],
):
    if body.type not in VALID_ACTIVITY_TYPES:
        raise HTTPException(status_code=422, detail=f"type must be one of {sorted(VALID_ACTIVITY_TYPES)}")
    lead = postgres.get_crm_lead(merchant_id, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="lead not found")
    return postgres.add_lead_activity(merchant_id, lead_id, body.type, body.body)


# ── Pipeline (full board snapshot) ───────────────────────────────────────────

@router.get("/pipeline")
@limiter.limit("60/minute")
def get_pipeline(
    request: Request,
    merchant_id: Annotated[str, Depends(get_merchant_id)],
):
    stages = postgres.list_pipeline_stages(merchant_id)
    leads = postgres.list_crm_leads(merchant_id)

    leads_by_stage: dict[str, list] = {}
    for lead in leads:
        key = lead.get("stage_id") or "__none__"
        leads_by_stage.setdefault(key, []).append(lead)

    pipeline = [{**s, "leads": leads_by_stage.get(s["id"], [])} for s in stages]
    return {"pipeline": pipeline, "unassigned": leads_by_stage.get("__none__", [])}


# ── Tasks ─────────────────────────────────────────────────────────────────────

@router.get("/tasks")
@limiter.limit("60/minute")
def list_tasks(
    request: Request,
    merchant_id: Annotated[str, Depends(get_merchant_id)],
    lead_id: Optional[str] = None,
    status: Optional[str] = None,
):
    return {"tasks": postgres.list_tasks(merchant_id, lead_id, status)}


@router.post("/tasks", status_code=201)
@limiter.limit("30/minute")
def create_task(
    request: Request,
    body: TaskCreate,
    merchant_id: Annotated[str, Depends(get_merchant_id)],
):
    return postgres.create_task(merchant_id, body.model_dump())


@router.put("/tasks/{task_id}")
@limiter.limit("60/minute")
def update_task(
    request: Request,
    task_id: str,
    body: TaskUpdate,
    merchant_id: Annotated[str, Depends(get_merchant_id)],
):
    updated = postgres.update_task(merchant_id, task_id, body.model_dump(exclude_none=True))
    if not updated:
        raise HTTPException(status_code=404, detail="task not found")
    return updated


@router.delete("/tasks/{task_id}", status_code=204)
@limiter.limit("30/minute")
def delete_task(
    request: Request,
    task_id: str,
    merchant_id: Annotated[str, Depends(get_merchant_id)],
):
    ok = postgres.delete_task(merchant_id, task_id)
    if not ok:
        raise HTTPException(status_code=404, detail="task not found")


# ── Sequences ─────────────────────────────────────────────────────────────────

@router.get("/sequences")
@limiter.limit("60/minute")
def list_sequences(
    request: Request,
    merchant_id: Annotated[str, Depends(get_merchant_id)],
):
    return {"sequences": postgres.list_sequences(merchant_id)}


@router.post("/sequences", status_code=201)
@limiter.limit("20/minute")
def create_sequence(
    request: Request,
    body: SequenceCreate,
    merchant_id: Annotated[str, Depends(get_merchant_id)],
):
    return postgres.create_sequence(merchant_id, body.name)


@router.get("/sequences/{seq_id}")
@limiter.limit("60/minute")
def get_sequence(
    request: Request,
    seq_id: str,
    merchant_id: Annotated[str, Depends(get_merchant_id)],
):
    seq = postgres.get_sequence(merchant_id, seq_id)
    if not seq:
        raise HTTPException(status_code=404, detail="sequence not found")
    return seq


@router.delete("/sequences/{seq_id}", status_code=204)
@limiter.limit("20/minute")
def delete_sequence(
    request: Request,
    seq_id: str,
    merchant_id: Annotated[str, Depends(get_merchant_id)],
):
    ok = postgres.delete_sequence(merchant_id, seq_id)
    if not ok:
        raise HTTPException(status_code=404, detail="sequence not found")


@router.post("/sequences/{seq_id}/steps", status_code=201)
@limiter.limit("30/minute")
def add_step(
    request: Request,
    seq_id: str,
    body: StepCreate,
    merchant_id: Annotated[str, Depends(get_merchant_id)],
):
    return postgres.add_sequence_step(merchant_id, seq_id, body.step_num, body.delay_days, body.subject, body.body)


@router.delete("/sequences/{seq_id}/steps/{step_id}", status_code=204)
@limiter.limit("20/minute")
def delete_step(
    request: Request,
    seq_id: str,
    step_id: str,
    merchant_id: Annotated[str, Depends(get_merchant_id)],
):
    ok = postgres.delete_sequence_step(merchant_id, seq_id, step_id)
    if not ok:
        raise HTTPException(status_code=404, detail="step not found")


@router.post("/sequences/{seq_id}/enroll", status_code=201)
@limiter.limit("30/minute")
def enroll(
    request: Request,
    seq_id: str,
    body: EnrollRequest,
    merchant_id: Annotated[str, Depends(get_merchant_id)],
):
    lead = postgres.get_crm_lead(merchant_id, body.lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="lead not found")
    return postgres.enroll_lead(merchant_id, seq_id, body.lead_id)


@router.delete("/sequences/{seq_id}/enroll/{lead_id}", status_code=204)
@limiter.limit("20/minute")
def unenroll(
    request: Request,
    seq_id: str,
    lead_id: str,
    merchant_id: Annotated[str, Depends(get_merchant_id)],
):
    postgres.unenroll_lead(merchant_id, seq_id, lead_id)


@router.get("/leads/{lead_id}/enrollments")
@limiter.limit("60/minute")
def lead_enrollments(
    request: Request,
    lead_id: str,
    merchant_id: Annotated[str, Depends(get_merchant_id)],
):
    return {"enrollments": postgres.list_lead_enrollments(merchant_id, lead_id)}


# ── Rep Performance ───────────────────────────────────────────────────────────

@router.get("/reps")
@limiter.limit("30/minute")
def rep_stats(
    request: Request,
    merchant_id: Annotated[str, Depends(get_merchant_id)],
):
    return {"reps": postgres.get_rep_stats(merchant_id)}


# ── Lead Enrichment ───────────────────────────────────────────────────────────

@router.post("/leads/{lead_id}/enrich")
@limiter.limit("20/minute")
def enrich_lead(
    request: Request,
    lead_id: str,
    merchant_id: Annotated[str, Depends(get_merchant_id)],
):
    enriched = postgres.enrich_lead(merchant_id, lead_id)
    if not enriched:
        raise HTTPException(status_code=404, detail="lead not found")
    return enriched
