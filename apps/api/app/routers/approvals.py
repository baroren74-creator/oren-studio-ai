"""Approval routes — docs/api.md, Phase 3.6 ("Approval Gate #1: review/
edit script before continuing"). See app.services.approvals's module
docstring for why this is a standalone DB-backed gate rather than
LangGraph's interrupt()/resume mechanism."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.deps import get_db, require_api_key
from app.schemas import ApprovalDecision, ApprovalOut
from app.services.approvals import ApprovalNotFoundError, decide_approval

router = APIRouter(prefix="/api/approvals", tags=["approvals"], dependencies=[Depends(require_api_key)])


@router.post("/{approval_id}/approve", response_model=ApprovalOut)
def approve(approval_id: str, db: Session = Depends(get_db)) -> ApprovalOut:
    try:
        return decide_approval(db, approval_id, status="approved")
    except ApprovalNotFoundError:
        raise HTTPException(status_code=404, detail="approval not found")


@router.post("/{approval_id}/reject", response_model=ApprovalOut)
def reject(approval_id: str, db: Session = Depends(get_db)) -> ApprovalOut:
    try:
        return decide_approval(db, approval_id, status="rejected")
    except ApprovalNotFoundError:
        raise HTTPException(status_code=404, detail="approval not found")


@router.post("/{approval_id}/request-edit", response_model=ApprovalOut)
def request_edit(approval_id: str, payload: ApprovalDecision, db: Session = Depends(get_db)) -> ApprovalOut:
    try:
        return decide_approval(db, approval_id, status="edited", notes=payload.notes)
    except ApprovalNotFoundError:
        raise HTTPException(status_code=404, detail="approval not found")
