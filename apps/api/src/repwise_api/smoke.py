from celery.result import AsyncResult

from repwise_api.worker import smoke_task


def main() -> None:
    result: AsyncResult = smoke_task.delay()
    payload = result.get(timeout=20)
    if payload != {"status": "ok", "worker": "media"}:
        raise RuntimeError(f"Unexpected smoke result: {payload!r}")
    result.forget()
    print("RepWise worker smoke job completed and result was removed.")


if __name__ == "__main__":  # pragma: no cover - exercised by services-smoke
    main()
