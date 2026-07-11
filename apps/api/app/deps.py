"""Shared FastAPI dependencies: auth and DB session.

ADR-006: a single static API key checked against the `X-Studio-Api-Key`
header — no OAuth/session layer in the MVP, since this is a genuinely
single-user system (docs/decisions.md).
"""

from __future__ import annotations

from collections.abc import Generator

from fastapi import Header, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.db import SessionLocal


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def require_api_key(x_studio_api_key: str | None = Header(default=None)) -> None:
    if x_studio_api_key != settings.studio_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid or missing API key")
