from __future__ import annotations

import asyncio
import uuid
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import create_async_engine

from repwise_api.database import Base, create_session_factory
from repwise_api.main import create_app
from repwise_api.models import AnalysisJob, MediaUpload, UploadStatus
from repwise_api.settings import Settings
from repwise_api.storage import MinioObjectStorage, StoredObject
from repwise_api.uploads import (
    InitiateUpload,
    cancel_upload,
    complete_upload,
    initiate_upload,
    owned_upload,
)

OWNER = uuid.UUID("10000000-0000-0000-0000-000000000001")
OTHER_OWNER = uuid.UUID("20000000-0000-0000-0000-000000000002")
SHA256 = "a" * 64


class FakeStorage:
    def __init__(self) -> None:
        self.objects: dict[str, StoredObject] = {}
        self.removed: list[str] = []

    def presigned_put(self, object_key: str) -> str:
        return f"https://storage.test/{object_key}?signed=true"

    def stat(self, object_key: str) -> StoredObject:
        return self.objects[object_key]

    def remove(self, object_key: str) -> None:
        self.removed.append(object_key)


def headers(owner: uuid.UUID = OWNER, key: str = "request-key-001") -> dict[str, str]:
    return {"Authorization": f"Bearer {owner}", "Idempotency-Key": key}


def upload_body(**changes: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "filename": "squat.mp4",
        "content_type": "video/mp4",
        "size_bytes": 1024,
        "sha256": SHA256,
    }
    body.update(changes)
    return body


def test_upload_lifecycle_is_owned_and_completion_is_idempotent() -> None:
    async def exercise() -> None:
        application = create_app()
        await application.state.database_engine.dispose()
        engine = create_async_engine("sqlite+aiosqlite://")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        application.state.database_engine = engine
        application.state.session_factory = create_session_factory(engine)
        fake_storage = FakeStorage()
        application.state.object_storage = fake_storage

        async with AsyncClient(
            transport=ASGITransport(app=application), base_url="http://test"
        ) as client:
            initiated = await client.post(
                "/v1/uploads", json=upload_body(), headers=headers()
            )
            duplicate = await client.post(
                "/v1/uploads", json=upload_body(), headers=headers()
            )
            upload_id = initiated.json()["upload_id"]
            object_key = f"users/{OWNER}/uploads/{upload_id}/source"
            fake_storage.objects[object_key] = StoredObject(1024, SHA256)

            foreign = await client.post(
                f"/v1/uploads/{upload_id}/complete", headers=headers(OTHER_OWNER)
            )
            completed = await client.post(
                f"/v1/uploads/{upload_id}/complete", headers=headers()
            )
            completed_again = await client.post(
                f"/v1/uploads/{upload_id}/complete", headers=headers()
            )
            cancel_completed = await client.delete(
                f"/v1/uploads/{upload_id}", headers=headers()
            )

        assert initiated.status_code == 201
        assert initiated.json()["upload_url"].startswith("https://storage.test/")
        assert duplicate.json()["upload_id"] == upload_id
        assert foreign.status_code == 404
        assert completed.status_code == 200
        assert (
            completed_again.json()["analysis_job_id"]
            == completed.json()["analysis_job_id"]
        )
        assert cancel_completed.status_code == 409

        async with application.state.session_factory() as session:
            assert await session.scalar(select(func.count(MediaUpload.id))) == 1
            assert await session.scalar(select(func.count(AnalysisJob.id))) == 1
        await engine.dispose()

    asyncio.run(exercise())


def test_cancel_is_idempotent_and_cancelled_upload_cannot_complete() -> None:
    async def exercise() -> None:
        application = create_app()
        await application.state.database_engine.dispose()
        engine = create_async_engine("sqlite+aiosqlite://")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        application.state.database_engine = engine
        application.state.session_factory = create_session_factory(engine)
        fake_storage = FakeStorage()
        application.state.object_storage = fake_storage

        async with AsyncClient(
            transport=ASGITransport(app=application), base_url="http://test"
        ) as client:
            initiated = await client.post(
                "/v1/uploads", json=upload_body(), headers=headers(key="cancel-key")
            )
            upload_id = initiated.json()["upload_id"]
            cancelled = await client.delete(
                f"/v1/uploads/{upload_id}", headers=headers()
            )
            cancelled_again = await client.delete(
                f"/v1/uploads/{upload_id}", headers=headers()
            )
            complete = await client.post(
                f"/v1/uploads/{upload_id}/complete", headers=headers()
            )
            repeated_initiation = await client.post(
                "/v1/uploads", json=upload_body(), headers=headers(key="cancel-key")
            )

        assert cancelled.json()["status"] == "cancelled"
        assert cancelled_again.json()["status"] == "cancelled"
        assert len(fake_storage.removed) == 1
        assert complete.status_code == 409
        assert repeated_initiation.json()["upload_url"] is None
        await engine.dispose()

    asyncio.run(exercise())


def test_upload_validation_and_storage_mismatch_errors_are_actionable() -> None:
    async def exercise() -> None:
        application = create_app()
        await application.state.database_engine.dispose()
        engine = create_async_engine("sqlite+aiosqlite://")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        application.state.database_engine = engine
        application.state.session_factory = create_session_factory(engine)
        fake_storage = FakeStorage()
        application.state.object_storage = fake_storage

        async with AsyncClient(
            transport=ASGITransport(app=application), base_url="http://test"
        ) as client:
            unauthenticated = await client.post(
                "/v1/uploads",
                json=upload_body(),
                headers={"Idempotency-Key": "key-12345"},
            )
            invalid_identity = await client.post(
                "/v1/uploads",
                json=upload_body(),
                headers={
                    "Authorization": "Bearer invalid",
                    "Idempotency-Key": "key-12345",
                },
            )
            unsupported = await client.post(
                "/v1/uploads",
                json=upload_body(content_type="image/jpeg"),
                headers=headers(key="unsupported"),
            )
            bad_checksum = await client.post(
                "/v1/uploads",
                json=upload_body(sha256="ABC"),
                headers=headers(key="bad-checksum"),
            )
            too_large = await client.post(
                "/v1/uploads",
                json=upload_body(size_bytes=250 * 1024 * 1024 + 1),
                headers=headers(key="too-large"),
            )
            initiated = await client.post(
                "/v1/uploads", json=upload_body(), headers=headers(key="mismatch")
            )
            upload_id = initiated.json()["upload_id"]
            object_key = f"users/{OWNER}/uploads/{upload_id}/source"
            fake_storage.objects[object_key] = StoredObject(10, SHA256)
            size_mismatch = await client.post(
                f"/v1/uploads/{upload_id}/complete", headers=headers()
            )
            fake_storage.objects[object_key] = StoredObject(1024, "b" * 64)
            checksum_mismatch = await client.post(
                f"/v1/uploads/{upload_id}/complete", headers=headers()
            )

        assert unauthenticated.status_code == 401
        assert invalid_identity.status_code == 401
        assert unsupported.status_code == 415
        assert bad_checksum.status_code == 422
        assert too_large.status_code == 422
        assert size_mismatch.json()["code"] == "size_mismatch"
        assert checksum_mismatch.json()["code"] == "checksum_mismatch"
        await engine.dispose()

    asyncio.run(exercise())


def test_browser_origin_can_preflight_authenticated_uploads() -> None:
    async def exercise() -> None:
        application = create_app()
        transport = ASGITransport(app=application)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.options(
                "/v1/uploads",
                headers={
                    "Origin": "http://127.0.0.1:5173",
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": (
                        "authorization,idempotency-key,content-type"
                    ),
                },
            )
        assert response.status_code == 200
        assert (
            response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
        )
        await application.state.database_engine.dispose()

    asyncio.run(exercise())


def test_minio_adapter_signs_stats_and_removes_private_objects() -> None:
    client = Mock()
    client.presigned_put_object.return_value = "https://signed.test/upload"
    stat = Mock(size=12, metadata={"X-Amz-Meta-Sha256": SHA256})
    client.stat_object.return_value = stat

    with patch("repwise_api.storage.Minio", return_value=client) as constructor:
        adapter = MinioObjectStorage(Settings())
        assert adapter.presigned_put("private/source") == "https://signed.test/upload"
        stored = adapter.stat("private/source")
        adapter.remove("private/source")

    constructor.assert_called_once_with(
        "127.0.0.1:59000",
        access_key="repwise-local",
        secret_key="repwise-local-only",
        secure=False,
    )
    assert stored.size == 12
    assert stored.sha256 == SHA256
    client.remove_object.assert_called_once_with("repwise-private", "private/source")


def test_minio_adapter_rejects_missing_object_size() -> None:
    client = Mock()
    client.stat_object.return_value = Mock(size=None, metadata=None)
    with patch("repwise_api.storage.Minio", return_value=client):
        adapter = MinioObjectStorage(Settings())
        try:
            adapter.stat("private/source")
        except RuntimeError as error:
            assert str(error) == "Object storage returned no object size"
        else:
            raise AssertionError("Expected missing size to fail")


def test_upload_service_branches_are_deterministic() -> None:
    async def exercise() -> None:
        fake_storage = FakeStorage()
        upload = MediaUpload(
            id=uuid.uuid4(),
            owner_id=OWNER,
            idempotency_key="service-key",
            object_key="private/source",
            filename="squat.mp4",
            content_type="video/mp4",
            declared_size=1024,
            expected_sha256=SHA256,
            status=UploadStatus.INITIATED,
        )
        session = Mock()
        session.scalar = AsyncMock(return_value=upload)
        session.commit = AsyncMock()

        assert await owned_upload(session, upload.id, OWNER) is upload
        session.scalar.return_value = None
        try:
            await owned_upload(session, upload.id, OWNER)
        except Exception as error:
            assert error.code == "upload_not_found"

        body = InitiateUpload(**upload_body())
        session.scalar.return_value = upload
        repeated = await initiate_upload(
            body, OWNER, session, fake_storage, "service-key"
        )
        assert repeated.upload_url is not None
        upload.status = UploadStatus.CANCELLED
        repeated_cancelled = await initiate_upload(
            body, OWNER, session, fake_storage, "service-key"
        )
        assert repeated_cancelled.upload_url is None
        session.scalar.return_value = None
        created = await initiate_upload(
            body, OWNER, session, fake_storage, "new-key-01"
        )
        assert created.status == "initiated"

        upload.status = UploadStatus.COMPLETED
        job = AnalysisJob(id=uuid.uuid4(), upload_id=upload.id, owner_id=OWNER)
        session.scalar.side_effect = [upload, job]
        assert (
            await complete_upload(upload.id, OWNER, session, fake_storage)
        ).analysis_job_id == job.id

        upload.status = UploadStatus.CANCELLED
        session.scalar.side_effect = [upload, None]
        try:
            await complete_upload(upload.id, OWNER, session, fake_storage)
        except Exception as error:
            assert error.code == "upload_cancelled"

        upload.status = UploadStatus.INITIATED
        session.scalar.side_effect = [upload, None]
        fake_storage.objects[upload.object_key] = StoredObject(10, SHA256)
        try:
            await complete_upload(upload.id, OWNER, session, fake_storage)
        except Exception as error:
            assert error.code == "size_mismatch"

        session.scalar.side_effect = [upload, None]
        fake_storage.objects[upload.object_key] = StoredObject(1024, "b" * 64)
        try:
            await complete_upload(upload.id, OWNER, session, fake_storage)
        except Exception as error:
            assert error.code == "checksum_mismatch"

        session.scalar.side_effect = [upload, None]
        fake_storage.objects[upload.object_key] = StoredObject(1024, SHA256)
        assert (
            await complete_upload(upload.id, OWNER, session, fake_storage)
        ).status == "completed"

        session.scalar.side_effect = None
        session.scalar.return_value = upload
        try:
            await cancel_upload(upload.id, OWNER, session, fake_storage)
        except Exception as error:
            assert error.code == "upload_completed"
        upload.status = UploadStatus.INITIATED
        assert (
            await cancel_upload(upload.id, OWNER, session, fake_storage)
        ).status == "cancelled"
        assert (
            await cancel_upload(upload.id, OWNER, session, fake_storage)
        ).status == "cancelled"

    asyncio.run(exercise())
