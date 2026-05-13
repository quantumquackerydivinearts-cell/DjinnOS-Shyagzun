"""
goals_reports_router.py — Workspace goals and report digests.

Goals
  GET    /v1/goals              — list all workspace goals
  POST   /v1/goals              — create a goal
  PUT    /v1/goals/{id}         — update a goal
  DELETE /v1/goals/{id}         — delete a goal
  PATCH  /v1/goals/{id}/progress — update current_value + status
  POST   /v1/goals/rollup       — recompute current values from live DB counts

Reports
  GET    /v1/reports/summary    — workspace counts for a date range
  GET    /v1/reports/digests    — list digest schedules
  POST   /v1/reports/digests    — create a digest schedule
  PUT    /v1/reports/digests/{id}   — update
  DELETE /v1/reports/digests/{id}   — delete
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .db import get_db
from .models import (
    Booking, Client, CRMContact, Lead, Order, Quote, Workspace,
    WorkspaceDigestSchedule, WorkspaceGoal,
)

router = APIRouter()

METRIC_TYPES = {"lead_count", "client_count", "quote_count", "order_count", "revenue_cents"}


# ── Workspace dep ─────────────────────────────────────────────────────────────

def _ws(
    x_workspace_id: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> str:
    if not x_workspace_id:
        raise HTTPException(400, "X-Workspace-Id header required")
    if db.get(Workspace, x_workspace_id) is None:
        raise HTTPException(404, "workspace_not_found")
    return x_workspace_id


# ── Metric computation ────────────────────────────────────────────────────────

def _count_in_period(db: Session, model, workspace_id: str,
                     period_start: str, period_end: str) -> int:
    return db.scalar(
        select(func.count(model.id)).where(
            model.workspace_id == workspace_id,
            func.date(model.created_at) >= period_start,
            func.date(model.created_at) <= period_end,
        )
    ) or 0


def _compute_metric(db: Session, workspace_id: str, metric_type: str,
                    period_start: str, period_end: str) -> int:
    if metric_type == "lead_count":
        return _count_in_period(db, Lead,      workspace_id, period_start, period_end)
    if metric_type == "client_count":
        return _count_in_period(db, Client,    workspace_id, period_start, period_end)
    if metric_type == "quote_count":
        return _count_in_period(db, Quote,     workspace_id, period_start, period_end)
    if metric_type == "order_count":
        return _count_in_period(db, Order,     workspace_id, period_start, period_end)
    if metric_type == "revenue_cents":
        return db.scalar(
            select(func.coalesce(func.sum(Order.amount_cents), 0)).where(
                Order.workspace_id == workspace_id,
                func.date(Order.created_at) >= period_start,
                func.date(Order.created_at) <= period_end,
            )
        ) or 0
    return 0


def _rollup(db: Session, workspace_id: str) -> list[WorkspaceGoal]:
    today = date.today().isoformat()
    goals = db.scalars(
        select(WorkspaceGoal).where(
            WorkspaceGoal.workspace_id == workspace_id,
            WorkspaceGoal.status.in_(["open"]),
        )
    ).all()
    for g in goals:
        g.current_value = _compute_metric(db, workspace_id, g.metric_type,
                                          g.period_start, g.period_end)
        if g.current_value >= g.target_value:
            g.status = "met"
        elif today > g.period_end:
            g.status = "missed"
        g.updated_at = datetime.utcnow()
    db.commit()
    return goals


def _goal_dict(g: WorkspaceGoal) -> dict:
    return {
        "id": g.id, "title": g.title, "metric_type": g.metric_type,
        "period_start": g.period_start, "period_end": g.period_end,
        "target_value": g.target_value, "current_value": g.current_value,
        "status": g.status, "notes": g.notes,
        "created_at": g.created_at.isoformat(),
        "pct": round(min(1.0, g.current_value / max(g.target_value, 1)) * 100, 1),
    }


# ── Goals ─────────────────────────────────────────────────────────────────────

class GoalCreate(BaseModel):
    title:        str = Field(min_length=1, max_length=160)
    metric_type:  str = "lead_count"
    period_start: str
    period_end:   str
    target_value: int = Field(gt=0)
    notes:        Optional[str] = None


class GoalUpdate(GoalCreate):
    status: str = "open"


class GoalProgress(BaseModel):
    current_value: int = Field(ge=0)
    status:        str


@router.get("/goals")
def list_goals(workspace_id: str = Depends(_ws), db: Session = Depends(get_db)) -> dict:
    goals = db.scalars(
        select(WorkspaceGoal).where(WorkspaceGoal.workspace_id == workspace_id)
        .order_by(WorkspaceGoal.created_at.desc())
    ).all()
    return {"goals": [_goal_dict(g) for g in goals]}


@router.post("/goals", status_code=201)
def create_goal(
    body:         GoalCreate,
    workspace_id: str     = Depends(_ws),
    db:           Session = Depends(get_db),
) -> dict:
    if body.metric_type not in METRIC_TYPES:
        raise HTTPException(400, f"metric_type must be one of {sorted(METRIC_TYPES)}")
    if body.period_end < body.period_start:
        raise HTTPException(400, "period_end must be >= period_start")
    g = WorkspaceGoal(
        id=str(uuid4()), workspace_id=workspace_id,
        title=body.title.strip(), metric_type=body.metric_type,
        period_start=body.period_start, period_end=body.period_end,
        target_value=body.target_value, current_value=0, status="open",
        notes=body.notes, created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
    )
    db.add(g); db.commit(); db.refresh(g)
    _rollup(db, workspace_id); db.refresh(g)
    return _goal_dict(g)


@router.put("/goals/{goal_id}")
def update_goal(
    goal_id:      str,
    body:         GoalUpdate,
    workspace_id: str     = Depends(_ws),
    db:           Session = Depends(get_db),
) -> dict:
    g = db.get(WorkspaceGoal, goal_id)
    if g is None or g.workspace_id != workspace_id:
        raise HTTPException(404, "goal_not_found")
    if body.metric_type not in METRIC_TYPES:
        raise HTTPException(400, "invalid metric_type")
    g.title = body.title.strip(); g.metric_type = body.metric_type
    g.period_start = body.period_start; g.period_end = body.period_end
    g.target_value = body.target_value; g.status = body.status
    g.notes = body.notes; g.updated_at = datetime.utcnow()
    db.commit(); db.refresh(g)
    _rollup(db, workspace_id); db.refresh(g)
    return _goal_dict(g)


@router.patch("/goals/{goal_id}/progress")
def progress_goal(
    goal_id:      str,
    body:         GoalProgress,
    workspace_id: str     = Depends(_ws),
    db:           Session = Depends(get_db),
) -> dict:
    g = db.get(WorkspaceGoal, goal_id)
    if g is None or g.workspace_id != workspace_id:
        raise HTTPException(404, "goal_not_found")
    g.current_value = body.current_value; g.status = body.status
    g.updated_at = datetime.utcnow()
    db.commit(); db.refresh(g)
    return _goal_dict(g)


@router.delete("/goals/{goal_id}", status_code=204)
def delete_goal(
    goal_id:      str,
    workspace_id: str     = Depends(_ws),
    db:           Session = Depends(get_db),
) -> None:
    g = db.get(WorkspaceGoal, goal_id)
    if g is None or g.workspace_id != workspace_id:
        raise HTTPException(404, "goal_not_found")
    db.delete(g); db.commit()


@router.post("/goals/rollup")
def rollup_goals(workspace_id: str = Depends(_ws), db: Session = Depends(get_db)) -> dict:
    goals = _rollup(db, workspace_id)
    return {"goals": [_goal_dict(g) for g in goals]}


# ── Report summary ────────────────────────────────────────────────────────────

@router.get("/reports/summary")
def report_summary(
    date_from:    Optional[str] = None,
    date_to:      Optional[str] = None,
    workspace_id: str     = Depends(_ws),
    db:           Session = Depends(get_db),
) -> dict:
    today = date.today().isoformat()
    df = date_from or "1970-01-01"
    dt = date_to   or today

    def count(model):
        return _count_in_period(db, model, workspace_id, df, dt)

    revenue = db.scalar(
        select(func.coalesce(func.sum(Order.amount_cents), 0)).where(
            Order.workspace_id == workspace_id,
            func.date(Order.created_at) >= df,
            func.date(Order.created_at) <= dt,
        )
    ) or 0

    return {
        "date_from":       df,
        "date_to":         dt,
        "new_contacts":    count(CRMContact),
        "new_leads":       count(Lead),
        "new_clients":     count(Client),
        "quotes":          count(Quote),
        "orders":          count(Order),
        "bookings":        count(Booking),
        "revenue_cents":   revenue,
        "revenue_display": f"${revenue / 100:,.2f}",
    }


# ── Digest schedules ──────────────────────────────────────────────────────────

class DigestCreate(BaseModel):
    recipient_email: str = Field(min_length=3, max_length=320)
    cadence:         str = "weekly"
    active:          bool = True


def _digest_dict(d: WorkspaceDigestSchedule) -> dict:
    return {
        "id": d.id, "recipient_email": d.recipient_email,
        "cadence": d.cadence, "active": d.active,
        "last_sent_at": d.last_sent_at.isoformat() if d.last_sent_at else None,
        "created_at": d.created_at.isoformat(),
    }


@router.get("/reports/digests")
def list_digests(workspace_id: str = Depends(_ws), db: Session = Depends(get_db)) -> dict:
    rows = db.scalars(
        select(WorkspaceDigestSchedule).where(
            WorkspaceDigestSchedule.workspace_id == workspace_id
        )
    ).all()
    return {"digests": [_digest_dict(d) for d in rows]}


@router.post("/reports/digests", status_code=201)
def create_digest(
    body:         DigestCreate,
    workspace_id: str     = Depends(_ws),
    db:           Session = Depends(get_db),
) -> dict:
    if body.cadence not in {"daily", "weekly", "monthly"}:
        raise HTTPException(400, "cadence must be daily|weekly|monthly")
    d = WorkspaceDigestSchedule(
        id=str(uuid4()), workspace_id=workspace_id,
        recipient_email=body.recipient_email, cadence=body.cadence,
        active=body.active, created_at=datetime.utcnow(),
    )
    db.add(d); db.commit(); db.refresh(d)
    return _digest_dict(d)


@router.put("/reports/digests/{digest_id}")
def update_digest(
    digest_id:    str,
    body:         DigestCreate,
    workspace_id: str     = Depends(_ws),
    db:           Session = Depends(get_db),
) -> dict:
    d = db.get(WorkspaceDigestSchedule, digest_id)
    if d is None or d.workspace_id != workspace_id:
        raise HTTPException(404, "digest_not_found")
    d.recipient_email = body.recipient_email
    d.cadence = body.cadence; d.active = body.active
    db.commit(); db.refresh(d)
    return _digest_dict(d)


@router.delete("/reports/digests/{digest_id}", status_code=204)
def delete_digest(
    digest_id:    str,
    workspace_id: str     = Depends(_ws),
    db:           Session = Depends(get_db),
) -> None:
    d = db.get(WorkspaceDigestSchedule, digest_id)
    if d is None or d.workspace_id != workspace_id:
        raise HTTPException(404, "digest_not_found")
    db.delete(d); db.commit()
