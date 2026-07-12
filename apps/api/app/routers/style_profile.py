"""Style profile routes — docs/api.md lists `GET /api/style-profile/
current`; `POST /api/style-profile` (create a new version) is a natural
symmetric addition for Phase 3.1's questionnaire and is documented
alongside it there."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.deps import get_db, require_api_key
from app.schemas import StyleProfileCreate, StyleProfileOut
from app.services.style_profile import create_style_profile, get_current_style_profile

router = APIRouter(prefix="/api/style-profile", tags=["style-profile"], dependencies=[Depends(require_api_key)])


@router.post("", response_model=StyleProfileOut, status_code=201)
def create(payload: StyleProfileCreate, db: Session = Depends(get_db)) -> StyleProfileOut:
    return create_style_profile(
        db,
        tone_notes=payload.tone_notes,
        opening_patterns=payload.opening_patterns,
        closing_patterns=payload.closing_patterns,
        avg_length_seconds=payload.avg_length_seconds,
        vocabulary_notes=payload.vocabulary_notes,
    )


@router.get("/current", response_model=StyleProfileOut)
def current(db: Session = Depends(get_db)) -> StyleProfileOut:
    profile = get_current_style_profile(db)
    if profile is None:
        raise HTTPException(status_code=404, detail="no style profile has been created yet")
    return profile
