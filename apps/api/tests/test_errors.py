import asyncio

from starlette.requests import Request

from repwise_api.errors import ApiError, api_error_handler, unhandled_error_handler


def request_with_state(request_id: str | None = None) -> Request:
    request = Request({"type": "http", "method": "GET", "path": "/", "headers": []})
    if request_id:
        request.state.request_id = request_id
    return request


def test_api_errors_have_stable_code_message_and_request_id() -> None:
    response = asyncio.run(
        api_error_handler(
            request_with_state("request-1"),
            ApiError(409, "conflict", "The resource changed."),
        )
    )
    assert response.status_code == 409
    assert b'"request_id":"request-1"' in response.body


def test_unhandled_errors_hide_internal_details() -> None:
    response = asyncio.run(
        unhandled_error_handler(request_with_state(), RuntimeError("secret detail"))
    )
    assert response.status_code == 500
    assert b"secret detail" not in response.body
    assert b'"request_id":"unknown"' in response.body


def test_api_handler_rejects_wrong_exception_type() -> None:
    async def exercise() -> None:
        try:
            await api_error_handler(request_with_state(), RuntimeError("wrong"))
        except RuntimeError as error:
            assert str(error) == "wrong"
        else:
            raise AssertionError("Expected RuntimeError")

    asyncio.run(exercise())
