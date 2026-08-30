import logging
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

LOG_DIRECTORY = Path("logs")
LOG_FILE = LOG_DIRECTORY / "s3_storage.log"


def configure_logging():
    """Configure console and file logging for the S3 workflow."""

    LOG_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True
    )

    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s | "
            "%(levelname)s | "
            "%(name)s | "
            "%(message)s"
        ),
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler()
        ]
    )


logger = logging.getLogger(__name__)


def create_s3_client():
    """Create an S3 client using the SentinelVision AWS profile."""

    try:
        logger.info(
            "Creating S3 client using AWS profile '%s'.",
            AWS_PROFILE
        )

        session = boto3.Session(
            profile_name=AWS_PROFILE,
            region_name=AWS_REGION
        )

        s3_client = session.client("s3")

        logger.info(
            "S3 client created successfully."
        )

        return s3_client

    except ProfileNotFound as error:
        logger.error(
            "AWS profile '%s' was not found.",
            AWS_PROFILE
        )

        raise RuntimeError(
            f"AWS profile '{AWS_PROFILE}' was not found."
        ) from error


def upload_file(s3_client, local_file_path, s3_key):
    """Upload a local file to the SentinelVision S3 bucket."""

    local_path = Path(local_file_path)

    if not local_path.is_file():
        logger.error(
            "Local file not found: %s",
            local_file_path
        )

        return False

    try:
        logger.info(
            "Uploading %s to s3://%s/%s",
            local_file_path,
            S3_BUCKET,
            s3_key
        )

        s3_client.upload_file(
            str(local_path),
            S3_BUCKET,
            s3_key
        )

        logger.info(
            "Upload completed successfully: %s",
            s3_key
        )

        return True

    except (ClientError, BotoCoreError) as error:
        logger.error(
            "Failed to upload %s: %s",
            local_file_path,
            error
        )

        return False


def object_exists(s3_client, s3_key):
    """Check whether an object exists in the S3 bucket."""

    try:
        logger.info(
            "Checking S3 object: s3://%s/%s",
            S3_BUCKET,
            s3_key
        )

        s3_client.head_object(
            Bucket=S3_BUCKET,
            Key=s3_key
        )

        logger.info(
            "S3 object exists: %s",
            s3_key
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
            logger.warning(
                "S3 object does not exist: %s",
                s3_key
            )

            return False

        logger.error(
            "Failed to check S3 object %s: %s",
            s3_key,
            error
        )

        return False


def list_objects(s3_client, prefix=""):
    """List objects stored under an S3 prefix."""

    try:
        logger.info(
            "Listing objects under s3://%s/%s",
            S3_BUCKET,
            prefix
        )

        response = s3_client.list_objects_v2(
            Bucket=S3_BUCKET,
            Prefix=prefix
        )

        objects = response.get("Contents", [])

        if not objects:
            logger.warning(
                "No objects found under s3://%s/%s",
                S3_BUCKET,
                prefix
            )

            return []

        logger.info(
            "Found %d object(s) under prefix '%s'.",
            len(objects),
            prefix
        )

        for item in objects:
            logger.info(
                "S3 object: %s | Size: %d bytes",
                item["Key"],
                item["Size"]
            )

        return objects

    except (ClientError, BotoCoreError) as error:
        logger.error(
            "Failed to list S3 objects: %s",
            error
        )

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
        logger.info(
            "Downloading s3://%s/%s to %s",
            S3_BUCKET,
            s3_key,
            local_file_path
        )

        s3_client.download_file(
            S3_BUCKET,
            s3_key,
            str(local_path)
        )

        logger.info(
            "Download completed successfully: %s",
            local_file_path
        )

        return True

    except (ClientError, BotoCoreError) as error:
        logger.error(
            "Failed to download s3://%s/%s: %s",
            S3_BUCKET,
            s3_key,
            error
        )

        return False


def upload_processed_metadata(s3_client):
    """Upload SentinelVision processed metadata files."""

    logger.info(
        "Starting processed metadata upload."
    )

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

    if image_uploaded and video_uploaded:
        logger.info(
            "All processed metadata files uploaded successfully."
        )
    else:
        logger.warning(
            "One or more metadata uploads failed."
        )

    return image_uploaded and video_uploaded


def main():
    """Run the SentinelVision S3 storage workflow."""

    configure_logging()

    logger.info(
        "Starting SentinelVision S3 storage workflow."
    )

    logger.info(
        "Bucket: %s | Region: %s | AWS profile: %s",
        S3_BUCKET,
        AWS_REGION,
        AWS_PROFILE
    )

    try:
        s3_client = create_s3_client()

        upload_success = upload_processed_metadata(
            s3_client
        )

        logger.info(
            "Verifying uploaded metadata."
        )

        image_exists = object_exists(
            s3_client,
            IMAGE_METADATA_KEY
        )

        video_exists = object_exists(
            s3_client,
            VIDEO_METADATA_KEY
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
            logger.info(
                "S3 storage workflow status: PASS"
            )
        else:
            logger.warning(
                "S3 storage workflow status: ISSUES FOUND"
            )

    except RuntimeError as error:
        logger.error(
            "AWS configuration error: %s",
            error
        )

    except (ClientError, BotoCoreError) as error:
        logger.exception(
            "AWS error occurred during S3 workflow: %s",
            error
        )

    except Exception:
        logger.exception(
            "Unexpected error occurred during S3 workflow."
        )


if __name__ == "__main__":
    main()
    