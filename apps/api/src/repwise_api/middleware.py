from collections.abc import Awaitable, Callable
from uuid import UUID, uuid4

from fastapi import Request, Response


async def request_id_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    supplied = request.headers.get("x-request-id")
    try:
        request_id = str(UUID(supplied)) if supplied else str(uuid4())
    except ValueError:
        request_id = str(uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["x-request-id"] = request_id
    return response
