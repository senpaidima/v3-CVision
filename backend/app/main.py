from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.dependencies import get_current_user
from app.models.auth import UserInfo

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


@app.get("/api/v1/health/protected")
async def health_protected(user: UserInfo = Depends(get_current_user)):
    return {"status": "ok", "user": user.model_dump()}
