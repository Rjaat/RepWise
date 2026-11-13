from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorBody(BaseModel):
    code: str
    message: str
    request_id: str


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message


async def api_error_handler(request: Request, error: Exception) -> JSONResponse:
    if not isinstance(error, ApiError):
        raise error
    request_id = getattr(request.state, "request_id", "unknown")
    body = ErrorBody(code=error.code, message=error.message, request_id=request_id)
    return JSONResponse(status_code=error.status_code, content=body.model_dump())


async def unhandled_error_handler(request: Request, error: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    body = ErrorBody(
        code="internal_error",
        message="An unexpected error occurred.",
        request_id=request_id,
    )
    return JSONResponse(status_code=500, content=body.model_dump())
