from fastapi import APIRouter

from app.api.v1.endpoints import chat, employees, health, lastenheft

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(employees.router)
api_router.include_router(chat.router)
api_router.include_router(lastenheft.router)
