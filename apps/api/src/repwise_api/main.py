from typing import Annotated, Literal

from fastapi import Depends, FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from repwise_api.annotations import router as annotations_router
from repwise_api.auth_routes import router as auth_router
from repwise_api.database import (
    create_database_engine,
    create_session_factory,
    database_ready,
)
from repwise_api.errors import ApiError, api_error_handler, unhandled_error_handler
from repwise_api.feedback import router as feedback_router
from repwise_api.middleware import request_id_middleware
from repwise_api.operations import router as operations_router
from repwise_api.privacy import router as privacy_router
from repwise_api.release_controls import router as release_controls_router
from repwise_api.retention import router as retention_router
from repwise_api.settings import Settings, get_settings
from repwise_api.storage import MinioObjectStorage
from repwise_api.uploads import router as uploads_router


class HealthResponse(BaseModel):
    status: Literal["ok", "unavailable"]
    service: Literal["repwise-api"]
    environment: str


async def health(
    settings: Annotated[Settings, Depends(get_settings)],
) -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="repwise-api",
        environment=settings.env,
    )


async def readiness(request: Request, response: Response) -> HealthResponse:
    ready = await database_ready(request.app.state.database_engine)
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthResponse(
        status="ok" if ready else "unavailable",
        service="repwise-api",
        environment=request.app.state.settings.env,
    )


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title="RepWise API",
        description="Evidence-linked exercise analysis API",
        version="0.1.0",
    )
    application.state.settings = settings
    application.state.database_engine = create_database_engine(settings.database_url)
    application.state.session_factory = create_session_factory(
        application.state.database_engine
    )
    application.state.object_storage = MinioObjectStorage(settings)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.web_origin],
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
    )
    application.middleware("http")(request_id_middleware)
    application.add_exception_handler(ApiError, api_error_handler)
    application.add_exception_handler(Exception, unhandled_error_handler)

    application.add_api_route(
        "/health",
        health,
        methods=["GET"],
        response_model=HealthResponse,
        tags=["operations"],
    )
    application.include_router(uploads_router)
    application.include_router(auth_router)
    application.include_router(retention_router)
    application.include_router(feedback_router)
    application.include_router(annotations_router)
    application.include_router(operations_router)
    application.include_router(privacy_router)
    application.include_router(release_controls_router)
    application.add_api_route(
        "/ready",
        readiness,
        methods=["GET"],
        response_model=HealthResponse,
        tags=["operations"],
    )

    return application


app = create_app()
