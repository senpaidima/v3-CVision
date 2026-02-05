from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.services.chat_service import chat_service
from app.services.embedding_service import embedding_service
from app.services.employee_service import employee_service
from app.services.lastenheft_analyzer import lastenheft_analyzer
from app.services.search_service import search_service

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    try:
        await employee_service.initialize(settings)
    except Exception:
        logger.exception("Failed to initialize EmployeeService — continuing without DB")
    try:
        await embedding_service.initialize(settings)
    except Exception:
        logger.exception("Failed to initialize EmbeddingService — continuing without OpenAI")
    try:
        await search_service.initialize(settings)
    except Exception:
        logger.exception("Failed to initialize SearchService — continuing without search")
    try:
        await chat_service.initialize(settings)
    except Exception:
        logger.exception("Failed to initialize ChatService — continuing without chat")
    try:
        await lastenheft_analyzer.initialize(settings)
    except Exception:
        logger.exception("Failed to initialize LastenheftAnalyzer — continuing without analyzer")
    yield
    await employee_service.close()
    await embedding_service.close()
    await search_service.close()
    await chat_service.close()
    await lastenheft_analyzer.close()


app = FastAPI(
    title="CVision v3 API",
    description="AI Employee Search + Lastenheft Analyzer",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://cvision.emposo.eu",
        "https://emposo-ai-cv-app.azurewebsites.net",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/")
async def root():
    return {"message": "CVision v3 API"}
