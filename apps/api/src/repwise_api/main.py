from typing import Annotated, Literal

from fastapi import Depends, FastAPI
from pydantic import BaseModel

from repwise_api.settings import Settings, get_settings


class HealthResponse(BaseModel):
    status: Literal["ok"]
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


def create_app() -> FastAPI:
    application = FastAPI(
        title="RepWise API",
        description="Evidence-linked exercise analysis API",
        version="0.1.0",
    )

    application.add_api_route(
        "/health",
        health,
        methods=["GET"],
        response_model=HealthResponse,
        tags=["operations"],
    )

    return application


app = create_app()
