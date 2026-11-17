from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from repwise_api.database import Base


class UploadStatus(enum.Enum):
    INITIATED = "initiated"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class MediaUpload(Base):
    __tablename__ = "media_uploads"
    __table_args__ = (
        UniqueConstraint("owner_id", "idempotency_key", name="uq_upload_owner_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(index=True)
    idempotency_key: Mapped[str] = mapped_column(String(128))
    object_key: Mapped[str] = mapped_column(String(255), unique=True)
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(64))
    declared_size: Mapped[int] = mapped_column(BigInteger)
    expected_sha256: Mapped[str] = mapped_column(String(64))
    status: Mapped[UploadStatus] = mapped_column(
        Enum(UploadStatus, native_enum=False), default=UploadStatus.INITIATED
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    upload_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("media_uploads.id", ondelete="CASCADE"), unique=True
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(index=True)
    status: Mapped[str] = mapped_column(String(32), default="queued")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
