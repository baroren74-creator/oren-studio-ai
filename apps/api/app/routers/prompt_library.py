"""Prompt Library routes — docs/api.md, Phase 3.5. See
app.services.prompt_library's module docstring for the versioning
model (edit = new row + parent_id, never an in-place update)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.deps import get_db, require_api_key
from app.schemas import PromptCreate, PromptOut, PromptVersionCreate
from app.services.prompt_library import (
    PromptNotFoundError,
    create_new_version,
    create_prompt,
    delete_prompt_family,
    get_prompt,
    get_prompt_history,
    list_current_prompts,
)

router = APIRouter(prefix="/api/prompt-library", tags=["prompt-library"], dependencies=[Depends(require_api_key)])


@router.post("", response_model=PromptOut, status_code=201)
def create(payload: PromptCreate, db: Session = Depends(get_db)) -> PromptOut:
    return create_prompt(db, name=payload.name, category=payload.category, prompt_text=payload.prompt_text)


@router.get("", response_model=list[PromptOut])
def list_current(db: Session = Depends(get_db)) -> list[PromptOut]:
    return list_current_prompts(db)


@router.get("/{prompt_id}", response_model=PromptOut)
def get_one(prompt_id: str, db: Session = Depends(get_db)) -> PromptOut:
    entry = get_prompt(db, prompt_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="prompt not found")
    return entry


@router.get("/{prompt_id}/history", response_model=list[PromptOut])
def history(prompt_id: str, db: Session = Depends(get_db)) -> list[PromptOut]:
    try:
        return get_prompt_history(db, prompt_id)
    except PromptNotFoundError:
        raise HTTPException(status_code=404, detail="prompt not found")


@router.post("/{prompt_id}/versions", response_model=PromptOut, status_code=201)
def new_version(prompt_id: str, payload: PromptVersionCreate, db: Session = Depends(get_db)) -> PromptOut:
    try:
        return create_new_version(db, parent_id=prompt_id, prompt_text=payload.prompt_text, category=payload.category)
    except PromptNotFoundError:
        raise HTTPException(status_code=404, detail="prompt not found")


@router.delete("/{prompt_id}", status_code=204)
def delete(prompt_id: str, db: Session = Depends(get_db)) -> None:
    try:
        delete_prompt_family(db, prompt_id)
    except PromptNotFoundError:
        raise HTTPException(status_code=404, detail="prompt not found")
