import os
import json
from datetime import datetime, timezone
import boto3
from botocore.exceptions import ClientError


def _get_r2_client():
    account_id = os.environ["R2_ACCOUNT_ID"]
    return boto3.client(
        service_name="s3",
        endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )


def provision_tenant_bucket(workspace_id: str) -> str:
    """Creates an isolated Cloudflare R2 bucket for a new workspace during onboarding."""
    bucket_name = f"fda-tenant-{workspace_id.lower().replace('_', '-')}"
    s3 = _get_r2_client()
    try:
        s3.head_bucket(Bucket=bucket_name)
    except ClientError:
        s3.create_bucket(Bucket=bucket_name)
    return bucket_name


def archive_payload_to_r2(workspace_id: str, category: str, record_id: str, payload: dict) -> str:
    """Archives old webhook payloads or audit records as JSON in the tenant's R2 bucket."""
    bucket_name = f"fda-tenant-{workspace_id.lower().replace('_', '-')}"
    s3 = _get_r2_client()
    date_prefix = datetime.now(timezone.utc).strftime("%Y/%m/%d")
    object_key = f"{category}/{date_prefix}/{record_id}.json"

    s3.put_object(
        Bucket=bucket_name,
        Key=object_key,
        Body=json.dumps(payload, default=str).encode("utf-8"),
        ContentType="application/json",
    )
    return object_key


def upload_workspace_backup(workspace_id: str, backup_bundle: dict) -> str:
    """Writes a daily JSON snapshot of workspace contacts, leads, messages, and bookings to R2."""
    bucket_name = f"fda-tenant-{workspace_id.lower().replace('_', '-')}"
    s3 = _get_r2_client()
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
    object_key = f"backups/daily/{timestamp}.json"

    s3.put_object(
        Bucket=bucket_name,
        Key=object_key,
        Body=json.dumps(backup_bundle, default=str).encode("utf-8"),
        ContentType="application/json",
    )
    return object_key


def delete_tenant_bucket(workspace_id: str) -> None:
    """Empties and deletes a tenant's R2 bucket upon account termination."""
    bucket_name = f"fda-tenant-{workspace_id.lower().replace('_', '-')}"
    s3 = _get_r2_client()
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket_name):
        objects = [{"Key": obj["Key"]} for obj in page.get("Contents", [])]
        if objects:
            s3.delete_objects(Bucket=bucket_name, Delete={"Objects": objects})
    s3.delete_bucket(Bucket=bucket_name)
