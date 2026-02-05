from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from app.core.dependencies import get_current_user
from app.models.auth import UserInfo
from app.models.lastenheft import LastenheftTextRequest, LastenheftUploadResponse
from app.services.document_extractor import (
    SUPPORTED_CONTENT_TYPES,
    DocumentExtractionError,
    MAX_FILE_SIZE,
    document_extractor,
)

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
