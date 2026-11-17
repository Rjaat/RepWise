import uuid
from typing import Annotated

from fastapi import Header

from repwise_api.errors import ApiError


async def authenticated_user(
    authorization: Annotated[str | None, Header()] = None,
) -> uuid.UUID:
    prefix = "Bearer "
    if authorization is None or not authorization.startswith(prefix):
        raise ApiError(401, "authentication_required", "A bearer identity is required.")
    try:
        return uuid.UUID(authorization.removeprefix(prefix))
    except ValueError as error:
        raise ApiError(
            401, "invalid_identity", "The bearer identity is invalid."
        ) from error
