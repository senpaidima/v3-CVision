"""Pydantic models for Lastenheft upload, text extraction, and AI analysis."""

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


class QualityScore(BaseModel):
    """Quality assessment scores for a Lastenheft."""

    completeness: int = Field(..., ge=0, le=100)
    clarity: int = Field(..., ge=0, le=100)
    specificity: int = Field(..., ge=0, le=100)
    feasibility: int = Field(..., ge=0, le=100)
    overall: int = Field(..., ge=0, le=100)
    summary: str


class OpenQuestion(BaseModel):
    """An open question identified in a Lastenheft."""

    question: str
    category: str = Field(..., pattern=r"^(technical|team|timeline|budget|domain)$")
    priority: str = Field(..., pattern=r"^(high|medium|low)$")


class ExtractedSkill(BaseModel):
    """A skill extracted from a Lastenheft."""

    name: str
    category: str = Field(
        ...,
        pattern=r"^(programming|framework|cloud|database|methodology|soft_skill|domain|other)$",
    )
    mandatory: bool
    level: str | None = Field(default=None, pattern=r"^(junior|mid|senior|expert)$")


class LastenheftAnalysisRequest(BaseModel):
    """Request body for AI analysis of extracted Lastenheft text."""

    text: str = Field(..., min_length=10, max_length=500_000)


class LastenheftAnalysisResponse(BaseModel):
    """Full AI analysis response for a Lastenheft."""

    quality_assessment: QualityScore
    open_questions: list[OpenQuestion]
    extracted_skills: list[ExtractedSkill]
