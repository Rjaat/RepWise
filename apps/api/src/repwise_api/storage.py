from __future__ import annotations

from datetime import timedelta
from typing import Protocol
from urllib.parse import urlparse

from minio import Minio

from repwise_api.settings import Settings


class StoredObject:
    def __init__(self, size: int, sha256: str | None) -> None:
        self.size = size
        self.sha256 = sha256


class ObjectStorage(Protocol):
    def presigned_put(self, object_key: str) -> str: ...

    def presigned_get(self, object_key: str) -> str: ...

    def stat(self, object_key: str) -> StoredObject: ...

    def remove(self, object_key: str) -> None: ...

    def download(self, object_key: str, destination: str) -> None: ...

    def upload(self, object_key: str, source: str, content_type: str) -> None: ...


class MinioObjectStorage:
    def __init__(self, settings: Settings) -> None:
        endpoint = urlparse(settings.media_endpoint)
        self.bucket = settings.media_bucket
        self.client = Minio(
            endpoint.netloc,
            access_key=settings.media_access_key,
            secret_key=settings.media_secret_key,
            secure=endpoint.scheme == "https",
        )

    def presigned_put(self, object_key: str) -> str:
        return self.client.presigned_put_object(
            self.bucket, object_key, expires=timedelta(minutes=15)
        )

    def presigned_get(self, object_key: str) -> str:
        return self.client.presigned_get_object(
            self.bucket, object_key, expires=timedelta(minutes=5)
        )

    def stat(self, object_key: str) -> StoredObject:
        result = self.client.stat_object(self.bucket, object_key)
        metadata = {
            key.lower(): value for key, value in (result.metadata or {}).items()
        }
        if result.size is None:
            raise RuntimeError("Object storage returned no object size")
        return StoredObject(result.size, metadata.get("x-amz-meta-sha256"))

    def remove(self, object_key: str) -> None:
        self.client.remove_object(self.bucket, object_key)

    def download(self, object_key: str, destination: str) -> None:
        self.client.fget_object(self.bucket, object_key, destination)

    def upload(self, object_key: str, source: str, content_type: str) -> None:
        self.client.fput_object(
            self.bucket, object_key, source, content_type=content_type
        )
