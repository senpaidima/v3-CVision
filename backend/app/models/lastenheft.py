"""Pydantic models for Lastenheft upload and text extraction."""

from __future__ import annotations

from pydantic import BaseModel, Field


class LastenheftTextRequest(BaseModel):
    """Request body for plain text paste."""

    text: str = Field(..., min_length=1, max_length=500_000)


class LastenheftUploadResponse(BaseModel):
    """Response after successful text extraction."""

    extracted_text: str
    char_count: int
    format: str = Field(..., pattern=r"^(pdf|docx|text)$")
