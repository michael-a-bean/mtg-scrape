"""Small S3 helpers used across scripts."""
from __future__ import annotations

import json
import logging

import boto3
from botocore.exceptions import ClientError

from src.config import AWS_REGION, S3_BUCKET

log = logging.getLogger(__name__)

_s3 = None


def client():
    global _s3
    if _s3 is None:
        _s3 = boto3.client("s3", region_name=AWS_REGION)
    return _s3


def exists(key: str) -> bool:
    try:
        client().head_object(Bucket=S3_BUCKET, Key=key)
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] in ("404", "NoSuchKey", "NotFound"):
            return False
        raise


def put_bytes(key: str, body: bytes, content_type: str = "application/octet-stream") -> None:
    client().put_object(Bucket=S3_BUCKET, Key=key, Body=body, ContentType=content_type)
    log.info("put s3://%s/%s (%d bytes)", S3_BUCKET, key, len(body))


def put_json(key: str, obj) -> None:
    put_bytes(key, json.dumps(obj, indent=2, default=str).encode(), "application/json")


def stream_to_s3(key: str, body_stream, content_type: str = "application/x-xz") -> None:
    """Upload a streaming HTTP body to S3 via multipart — no full buffer."""
    client().upload_fileobj(
        body_stream,
        S3_BUCKET,
        key,
        ExtraArgs={"ContentType": content_type},
    )
    log.info("streamed s3://%s/%s", S3_BUCKET, key)
