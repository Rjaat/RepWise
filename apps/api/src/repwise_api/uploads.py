from __future__ import annotations

import re
import uuid
from typing import Annotated, Literal, cast

from anyio import to_thread
from fastapi import APIRouter, Depends, Header, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from repwise_api.auth import authenticated_user
from repwise_api.database import request_session
from repwise_api.errors import ApiError
from repwise_api.guardrails import consume_analysis_usage
from repwise_api.models import AnalysisJob, MediaUpload, UploadStatus
from repwise_api.settings import Settings, get_settings
from repwise_api.storage import ObjectStorage

MAX_UPLOAD_BYTES = 250 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {"video/mp4", "video/quicktime", "video/webm"}
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")

router = APIRouter(prefix="/v1/uploads", tags=["uploads"])


class InitiateUpload(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: str
    size_bytes: int = Field(gt=0, le=MAX_UPLOAD_BYTES)
    sha256: str


class UploadResponse(BaseModel):
    upload_id: uuid.UUID
    status: Literal["initiated", "completed", "cancelled"]
    upload_url: str | None = None
    analysis_job_id: uuid.UUID | None = None


def storage(request: Request) -> ObjectStorage:
    return cast(ObjectStorage, request.app.state.object_storage)


async def owned_upload(
    session: AsyncSession, upload_id: uuid.UUID, owner_id: uuid.UUID
) -> MediaUpload:
    upload = await session.scalar(
        select(MediaUpload).where(MediaUpload.id == upload_id).with_for_update()
    )
    if upload is None or upload.owner_id != owner_id:
        raise ApiError(404, "upload_not_found", "Upload not found.")
    return upload


@router.post("", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def initiate_upload(
    body: InitiateUpload,
    owner_id: Annotated[uuid.UUID, Depends(authenticated_user)],
    session: Annotated[AsyncSession, Depends(request_session)],
    object_storage: Annotated[ObjectStorage, Depends(storage)],
    idempotency_key: Annotated[
        str, Header(alias="Idempotency-Key", min_length=8, max_length=128)
    ],
) -> UploadResponse:
    if body.content_type not in ALLOWED_CONTENT_TYPES:
        raise ApiError(
            415, "unsupported_media_type", "Use MP4, QuickTime, or WebM video."
        )
    if not SHA256_PATTERN.fullmatch(body.sha256):
        raise ApiError(
            422, "invalid_checksum", "sha256 must be 64 lowercase hex characters."
        )
    existing = await session.scalar(
        select(MediaUpload).where(
            MediaUpload.owner_id == owner_id,
            MediaUpload.idempotency_key == idempotency_key,
        )
    )
    if existing is not None:
        return UploadResponse(
            upload_id=existing.id,
            status=existing.status.value,
            upload_url=(
                object_storage.presigned_put(
                    existing.object_key, existing.expected_sha256
                )
                if existing.status is UploadStatus.INITIATED
                else None
            ),
        )
    upload_id = uuid.uuid4()
    upload = MediaUpload(
        id=upload_id,
        owner_id=owner_id,
        idempotency_key=idempotency_key,
        object_key=f"users/{owner_id}/uploads/{upload_id}/source",
        filename=body.filename,
        content_type=body.content_type,
        declared_size=body.size_bytes,
        expected_sha256=body.sha256,
    )
    session.add(upload)
    await session.commit()
    return UploadResponse(
        upload_id=upload.id,
        status="initiated",
        upload_url=object_storage.presigned_put(
            upload.object_key, upload.expected_sha256
        ),
    )


@router.post("/{upload_id}/complete", response_model=UploadResponse)
async def complete_upload(
    upload_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(authenticated_user)],
    session: Annotated[AsyncSession, Depends(request_session)],
    object_storage: Annotated[ObjectStorage, Depends(storage)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> UploadResponse:
    upload = await owned_upload(session, upload_id, owner_id)
    existing_job = await session.scalar(
        select(AnalysisJob).where(AnalysisJob.upload_id == upload.id)
    )
    if upload.status is UploadStatus.COMPLETED and existing_job is not None:
        return UploadResponse(
            upload_id=upload.id,
            status="completed",
            analysis_job_id=existing_job.id,
        )
    if upload.status is UploadStatus.CANCELLED:
        raise ApiError(
            409, "upload_cancelled", "A cancelled upload cannot be completed."
        )
    stored = await to_thread.run_sync(object_storage.stat, upload.object_key)
    if stored.size != upload.declared_size:
        raise ApiError(
            409, "size_mismatch", "Uploaded object size does not match initiation."
        )
    if stored.sha256 != upload.expected_sha256:
        raise ApiError(
            409,
            "checksum_mismatch",
            "Uploaded object checksum does not match initiation.",
        )
    job = AnalysisJob(upload_id=upload.id, owner_id=owner_id)
    upload.status = UploadStatus.COMPLETED
    session.add(job)
    await session.flush()
    await consume_analysis_usage(
        session,
        owner_id=owner_id,
        analysis_id=job.id,
        event_key=f"analysis:{upload.id}",
        monthly_limit_units=settings.beta_monthly_analysis_quota,
        daily_limit_units=settings.beta_daily_analysis_quota,
        payments_enabled=settings.payments_enabled,
    )
    await session.commit()
    return UploadResponse(
        upload_id=upload.id, status="completed", analysis_job_id=job.id
    )


@router.delete("/{upload_id}", response_model=UploadResponse)
async def cancel_upload(
    upload_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(authenticated_user)],
    session: Annotated[AsyncSession, Depends(request_session)],
    object_storage: Annotated[ObjectStorage, Depends(storage)],
) -> UploadResponse:
    upload = await owned_upload(session, upload_id, owner_id)
    if upload.status is UploadStatus.COMPLETED:
        raise ApiError(
            409, "upload_completed", "A completed upload cannot be cancelled."
        )
    if upload.status is UploadStatus.INITIATED:
        await to_thread.run_sync(object_storage.remove, upload.object_key)
        upload.status = UploadStatus.CANCELLED
        await session.commit()
    return UploadResponse(upload_id=upload.id, status="cancelled")
