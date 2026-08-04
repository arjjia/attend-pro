from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import auth, lecturer, schedule, student, websocket
from app.services.codes import AttendanceCodeStore
from app.services.websockets import AttendanceHub


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(title="AttendPro API", version="0.1.0")
    application.state.code_store = AttendanceCodeStore()
    application.state.attendance_hub = AttendanceHub()
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(auth.router)
    application.include_router(schedule.router)
    application.include_router(lecturer.router)
    application.include_router(student.router)
    application.include_router(websocket.router)

    @application.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()
