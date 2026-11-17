from __future__ import annotations

import asyncio
import hashlib
import json
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine

from repwise_api.database import Base, create_session_factory
from repwise_api.main import create_app
from repwise_api.models import (
    AnalysisArtifact,
    AnalysisJob,
    AnalysisTombstone,
    ArtifactKind,
    DeletionRequest,
    MediaUpload,
    UploadStatus,
)
from repwise_api.retention import expire_raw_media, reject_tombstoned_analysis
from repwise_api.settings import Settings
from repwise_api.storage import StoredObject
from repwise_api.worker import publish_report_task

OWNER = uuid.UUID("10000000-0000-0000-0000-000000000001")
OTHER = uuid.UUID("20000000-0000-0000-0000-000000000002")


class RetentionStorage:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.removed: list[str] = []

    def remove(self, object_key: str) -> None:
        self.removed.append(object_key)
        self.objects.pop(object_key, None)

    def stat(self, object_key: str) -> StoredObject:
        return StoredObject(len(self.objects[object_key]), None)

    def presigned_put(self, object_key: str) -> str:
        return f"https://storage.test/{object_key}"

    def download(self, object_key: str, destination: str) -> None:
        Path(destination).write_bytes(self.objects[object_key])

    def upload(self, object_key: str, source: str, _content_type: str) -> None:
        self.objects[object_key] = Path(source).read_bytes()


async def retention_app(database_url: str):
    application = create_app()
    await application.state.database_engine.dispose()
    engine = create_async_engine(database_url)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    application.state.database_engine = engine
    application.state.session_factory = create_session_factory(engine)
    storage = RetentionStorage()
    application.state.object_storage = storage
    return application, engine, storage


async def seed_analysis(application, owner: uuid.UUID = OWNER):
    upload = MediaUpload(
        owner_id=owner,
        idempotency_key=f"history-{owner}",
        object_key=f"users/{owner}/uploads/source",
        filename="squat.mp4",
        content_type="video/mp4",
        declared_size=10,
        expected_sha256="a" * 64,
        status=UploadStatus.COMPLETED,
    )
    async with application.state.session_factory() as db:
        db.add(upload)
        await db.flush()
        job = AnalysisJob(
            upload_id=upload.id,
            owner_id=owner,
            status="completed",
            completed_at=datetime.now(UTC),
        )
        db.add(job)
        await db.flush()
        artifact = AnalysisArtifact(
            analysis_id=job.id,
            object_key=f"analyses/{job.id}/pose.v1.json",
            kind=ArtifactKind.DERIVED,
        )
        db.add(artifact)
        await db.commit()
        return job.id, upload.object_key, artifact.object_key


def test_history_deletion_removes_assets_and_blocks_worker_retry() -> None:
    async def exercise() -> None:
        with TemporaryDirectory() as directory:
            database_url = f"sqlite+aiosqlite:///{directory}/retention.db"
            application, engine, storage = await retention_app(database_url)
            analysis_id, raw_key, artifact_key = await seed_analysis(application)
            report_key = f"analyses/{analysis_id}/report.v1.json"
            storage.objects.update(
                {raw_key: b"raw", artifact_key: b"pose", report_key: b"report"}
            )
            headers = {"Authorization": f"Bearer {OWNER}"}
            async with AsyncClient(
                transport=ASGITransport(app=application), base_url="http://test"
            ) as client:
                listed = await client.get("/v1/history", headers=headers)
                detail = await client.get(f"/v1/history/{analysis_id}", headers=headers)
                foreign = await client.get(
                    f"/v1/history/{analysis_id}",
                    headers={"Authorization": f"Bearer {OTHER}"},
                )
                deleted = await client.delete(
                    f"/v1/history/{analysis_id}", headers=headers
                )
                deleted_again = await client.delete(
                    f"/v1/history/{analysis_id}", headers=headers
                )
                hidden = await client.get(f"/v1/history/{analysis_id}", headers=headers)

            assert len(listed.json()["items"]) == 1
            assert detail.status_code == 200
            assert foreign.status_code == 404
            assert deleted.status_code == 200
            assert deleted_again.json() == deleted.json()
            assert hidden.status_code == 404
            assert not storage.objects
            async with application.state.session_factory() as db:
                assert await db.get(AnalysisTombstone, analysis_id)
                deletion = await db.scalar(
                    select(DeletionRequest).where(
                        DeletionRequest.analysis_id == analysis_id
                    )
                )
                assert deletion and deletion.status == "completed"

            segmentation = json.dumps(
                {"complete_reps": [], "partial_reps": []}, sort_keys=True
            ).encode()
            worker_storage = Mock()
            worker_storage.download.side_effect = lambda _key, destination: Path(
                destination
            ).write_bytes(segmentation)
            worker_settings = Settings(database_url=database_url)
            with (
                patch("repwise_api.worker.settings", worker_settings),
                patch(
                    "repwise_api.worker.MinioObjectStorage",
                    return_value=worker_storage,
                ),
                pytest.raises(RuntimeError, match="deleted"),
            ):
                publish_report_task(
                    "segmentation.json",
                    hashlib.sha256(segmentation).hexdigest(),
                    str(analysis_id),
                    "a" * 64,
                    "b" * 64,
                )
            worker_storage.upload.assert_not_called()
            await engine.dispose()

    asyncio.run(exercise())


def test_raw_media_expiry_preserves_history_and_derived_assets() -> None:
    async def exercise() -> None:
        with TemporaryDirectory() as directory:
            database_url = f"sqlite+aiosqlite:///{directory}/expiry.db"
            application, engine, storage = await retention_app(database_url)
            analysis_id, raw_key, artifact_key = await seed_analysis(application)
            normalized_key = f"analyses/{analysis_id}/normalized.mp4"
            async with application.state.session_factory() as db:
                db.add(
                    AnalysisArtifact(
                        analysis_id=analysis_id,
                        object_key=normalized_key,
                        kind=ArtifactKind.RAW,
                    )
                )
                await db.commit()
            storage.objects.update(
                {
                    raw_key: b"raw",
                    normalized_key: b"normalized",
                    artifact_key: b"derived",
                }
            )
            now = datetime.now(UTC)
            async with application.state.session_factory() as db:
                job = await db.get(AnalysisJob, analysis_id)
                assert job is not None
                job.raw_expires_at = now - timedelta(seconds=1)
                await db.commit()
                expired = await expire_raw_media(db, storage, now)
                expired_again = await expire_raw_media(db, storage, now)
            assert expired == 1
            assert expired_again == 0
            assert raw_key not in storage.objects
            assert normalized_key not in storage.objects
            assert artifact_key in storage.objects
            async with AsyncClient(
                transport=ASGITransport(app=application), base_url="http://test"
            ) as client:
                response = await client.get(
                    f"/v1/history/{analysis_id}",
                    headers={"Authorization": f"Bearer {OWNER}"},
                )
            assert response.status_code == 200
            assert response.json()["raw_available_until"] is None
            await engine.dispose()

    asyncio.run(exercise())


def test_worker_guard_allows_active_analysis() -> None:
    with TemporaryDirectory() as directory:
        database_url = f"sqlite:///{directory}/guard.db"
        from sqlalchemy import create_engine

        engine = create_engine(database_url)
        Base.metadata.create_all(engine)
        reject_tombstoned_analysis(str(uuid.uuid4()), database_url)
        engine.dispose()
