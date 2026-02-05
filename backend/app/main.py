from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

app = FastAPI(
    title="CVision v3 API",
    description="AI Employee Search + Lastenheft Analyzer",
    version=settings.APP_VERSION,
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


@app.get("/")
async def root():
    return {"message": "CVision v3 API"}


@app.get("/api/v1/health")
async def health():
    return {"status": "ok", "version": settings.APP_VERSION}
