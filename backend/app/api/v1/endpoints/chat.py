from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.dependencies import get_current_user
from app.models.auth import UserInfo
from app.services.chat_service import chat_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    language: str = Field(default="de", pattern=r"^(de|en)$")


@router.post("/stream", response_class=StreamingResponse)
async def chat_stream(
    request: ChatRequest,
    user: UserInfo = Depends(get_current_user),
):
    logger.info("Chat stream request from user=%s query=%s", user.name, request.query[:50])

    return StreamingResponse(
        chat_service.stream_chat(query=request.query, language=request.language),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
