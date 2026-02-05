from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from app.core.dependencies import get_current_user
from app.models.auth import UserInfo
from app.models.lastenheft import (
    CandidateMatchRequest,
    CandidateMatchResponse,
    LastenheftAnalysisRequest,
    LastenheftAnalysisResponse,
    LastenheftTextRequest,
    LastenheftUploadResponse,
)
from app.services.candidate_matcher import CandidateMatcherError, candidate_matcher
from app.services.document_extractor import (
    SUPPORTED_CONTENT_TYPES,
    DocumentExtractionError,
    MAX_FILE_SIZE,
    document_extractor,
)
from app.services.lastenheft_analyzer import LastenheftAnalyzerError, lastenheft_analyzer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/lastenheft", tags=["lastenheft"])


@router.post("/upload", response_model=LastenheftUploadResponse)
async def upload_lastenheft(
    file: UploadFile,
    user: UserInfo = Depends(get_current_user),
):
    if file.content_type not in SUPPORTED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {file.content_type}. Allowed: PDF, DOCX",
        )

    file_bytes = await file.read()

    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large: {len(file_bytes)} bytes. Maximum: {MAX_FILE_SIZE} bytes (10 MB)",
        )

    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )

    try:
        extracted = document_extractor.extract(file_bytes, file.content_type)
    except DocumentExtractionError as e:
        logger.error("Extraction failed for file=%s: %s", file.filename, e)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        ) from e

    fmt = SUPPORTED_CONTENT_TYPES[file.content_type]
    logger.info("Extracted %d chars from %s (%s) user=%s", len(extracted), file.filename, fmt, user.name)

    return LastenheftUploadResponse(
        extracted_text=extracted,
        char_count=len(extracted),
        format=fmt,
    )


@router.post("/text", response_model=LastenheftUploadResponse)
async def paste_lastenheft_text(
    request: LastenheftTextRequest,
    user: UserInfo = Depends(get_current_user),
):
    cleaned = document_extractor.extract_from_text(request.text)
    logger.info("Text paste: %d chars from user=%s", len(cleaned), user.name)

    return LastenheftUploadResponse(
        extracted_text=cleaned,
        char_count=len(cleaned),
        format="text",
    )


@router.post("/analyze", response_model=LastenheftAnalysisResponse)
async def analyze_lastenheft(
    request: LastenheftAnalysisRequest,
    user: UserInfo = Depends(get_current_user),
):
    try:
        result = await lastenheft_analyzer.analyze(request.text)
    except LastenheftAnalyzerError as e:
        logger.error("Lastenheft analysis failed for user=%s: %s", user.name, e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI analysis failed: {e}",
        ) from e

    logger.info(
        "Lastenheft analyzed: %d chars, quality=%d, questions=%d, skills=%d, user=%s",
        len(request.text),
        result.quality_assessment.overall,
        len(result.open_questions),
        len(result.extracted_skills),
        user.name,
    )
    return result


@router.post("/match", response_model=CandidateMatchResponse)
async def match_candidates(
    request: CandidateMatchRequest,
    user: UserInfo = Depends(get_current_user),
):
    try:
        result = await candidate_matcher.match(request.extracted_skills, request.text)
    except CandidateMatcherError as e:
        logger.error("Candidate matching failed for user=%s: %s", user.name, e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Candidate matching failed: {e}",
        ) from e

    logger.info(
        "Candidate matching: %d matches from %d searched, user=%s",
        len(result.matches),
        result.total_candidates_searched,
        user.name,
    )
    return result
