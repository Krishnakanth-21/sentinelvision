import os
from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError, ClientError, ProfileNotFound


AWS_PROFILE = "sentinelvision"
AWS_REGION = "ap-southeast-2"
S3_BUCKET = "sentinelvision-krishnakanth-2026"

IMAGE_METADATA_PATH = "data/processed/image_metadata.csv"
VIDEO_METADATA_PATH = "data/processed/video_metadata.csv"

IMAGE_METADATA_KEY = "metadata/image_metadata.csv"
VIDEO_METADATA_KEY = "metadata/video_metadata.csv"


def create_s3_client():
    """Create an S3 client using the SentinelVision AWS profile."""

    try:
        session = boto3.Session(
            profile_name=AWS_PROFILE,
            region_name=AWS_REGION
        )

        return session.client("s3")

    except ProfileNotFound as error:
        raise RuntimeError(
            f"AWS profile '{AWS_PROFILE}' was not found."
        ) from error


def upload_file(s3_client, local_file_path, s3_key):
    """Upload a local file to the SentinelVision S3 bucket."""

    local_path = Path(local_file_path)

    if not local_path.is_file():
        print(f"File not found: {local_file_path}")
        return False

    try:
        s3_client.upload_file(
            str(local_path),
            S3_BUCKET,
            s3_key
        )

        print(
            f"Uploaded {local_file_path} "
            f"to s3://{S3_BUCKET}/{s3_key}"
        )

        return True

    except (ClientError, BotoCoreError) as error:
        print(
            f"Failed to upload {local_file_path}: "
            f"{error}"
        )

        return False


def object_exists(s3_client, s3_key):
    """Check whether an object exists in the S3 bucket."""

    try:
        s3_client.head_object(
            Bucket=S3_BUCKET,
            Key=s3_key
        )

        return True

    except ClientError as error:
        error_code = error.response.get(
            "Error",
            {}
        ).get(
            "Code",
            ""
        )

        if error_code in {"404", "NoSuchKey", "NotFound"}:
            return False

        print(
            f"Failed to check s3://{S3_BUCKET}/{s3_key}: "
            f"{error}"
        )

        return False


def list_objects(s3_client, prefix=""):
    """List objects stored under an S3 prefix."""

    try:
        response = s3_client.list_objects_v2(
            Bucket=S3_BUCKET,
            Prefix=prefix
        )

        objects = response.get("Contents", [])

        if not objects:
            print(
                f"No objects found under "
                f"s3://{S3_BUCKET}/{prefix}"
            )
            return []

        print(
            f"\nObjects under "
            f"s3://{S3_BUCKET}/{prefix}"
        )

        for item in objects:
            print(
                f"- {item['Key']} "
                f"({item['Size']} bytes)"
            )

        return objects

    except (ClientError, BotoCoreError) as error:
        print(f"Failed to list S3 objects: {error}")
        return []


def download_file(s3_client, s3_key, local_file_path):
    """Download an object from S3 to a local file."""

    local_path = Path(local_file_path)

    if local_path.parent != Path("."):
        local_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

    try:
        s3_client.download_file(
            S3_BUCKET,
            s3_key,
            str(local_path)
        )

        print(
            f"Downloaded s3://{S3_BUCKET}/{s3_key} "
            f"to {local_file_path}"
        )

        return True

    except (ClientError, BotoCoreError) as error:
        print(
            f"Failed to download "
            f"s3://{S3_BUCKET}/{s3_key}: "
            f"{error}"
        )

        return False


def upload_processed_metadata(s3_client):
    """Upload SentinelVision processed metadata files."""

    print("\nUploading processed metadata...")

    image_uploaded = upload_file(
        s3_client,
        IMAGE_METADATA_PATH,
        IMAGE_METADATA_KEY
    )

    video_uploaded = upload_file(
        s3_client,
        VIDEO_METADATA_PATH,
        VIDEO_METADATA_KEY
    )

    return image_uploaded and video_uploaded


def main():
    """Run the SentinelVision S3 storage workflow."""

    print("SentinelVision S3 Storage")
    print("-------------------------")
    print(f"Bucket: {S3_BUCKET}")
    print(f"Region: {AWS_REGION}")
    print(f"AWS profile: {AWS_PROFILE}")

    try:
        s3_client = create_s3_client()

        upload_success = upload_processed_metadata(
            s3_client
        )

        print("\nVerifying uploaded metadata...")

        image_exists = object_exists(
            s3_client,
            IMAGE_METADATA_KEY
        )

        video_exists = object_exists(
            s3_client,
            VIDEO_METADATA_KEY
        )

        print(
            f"Image metadata exists in S3: "
            f"{image_exists}"
        )

        print(
            f"Video metadata exists in S3: "
            f"{video_exists}"
        )

        list_objects(
            s3_client,
            prefix="metadata/"
        )

        if (
            upload_success
            and image_exists
            and video_exists
        ):
            print(
                "\nS3 storage workflow status: PASS"
            )
        else:
            print(
                "\nS3 storage workflow status: "
                "ISSUES FOUND"
            )

    except RuntimeError as error:
        print(f"AWS configuration error: {error}")

    except (ClientError, BotoCoreError) as error:
        print(f"AWS error: {error}")


if __name__ == "__main__":
    main()
    