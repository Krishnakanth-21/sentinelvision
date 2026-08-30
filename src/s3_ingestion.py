import logging
from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError, ClientError, ProfileNotFound


# ---------------------------------------------------------------------------
# AWS configuration
# ---------------------------------------------------------------------------

AWS_PROFILE = "sentinelvision"
AWS_REGION = "ap-southeast-2"
S3_BUCKET = "sentinelvision-krishnakanth-2026"

IMAGE_PREFIX = "raw/images/"
VIDEO_PREFIX = "raw/videos/"

STAGING_IMAGE_DIRECTORY = "data/staging/images"
STAGING_VIDEO_DIRECTORY = "data/staging/videos"


# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

logger = logging.getLogger(__name__)


def create_s3_client():
    """
    Create an Amazon S3 client using the SentinelVision AWS profile.

    Returns:
        Configured Boto3 S3 client.

    Raises:
        RuntimeError: If the configured AWS profile cannot be found.
    """

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


def list_s3_objects(s3_client, prefix):
    """
    List object keys stored under a specific S3 prefix.

    Args:
        s3_client: Configured Boto3 S3 client.
        prefix: S3 prefix such as raw/images/ or raw/videos/.

    Returns:
        List of S3 object keys.
    """

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

        objects = response.get(
            "Contents",
            []
        )

        object_keys = [
            item["Key"]
            for item in objects
            if item["Key"] != prefix
        ]

        logger.info(
            "Found %d object(s) under '%s'.",
            len(object_keys),
            prefix
        )

        return object_keys

    except (ClientError, BotoCoreError) as error:
        logger.error(
            "Failed to list S3 objects under '%s': %s",
            prefix,
            error
        )

        return []


def download_s3_object(
    s3_client,
    s3_key,
    local_directory
):
    """
    Download one S3 object into a local staging directory.

    Args:
        s3_client: Configured Boto3 S3 client.
        s3_key: S3 object key to download.
        local_directory: Local destination directory.

    Returns:
        Path to the downloaded file, or None if the download fails.
    """

    destination_directory = Path(
        local_directory
    )

    destination_directory.mkdir(
        parents=True,
        exist_ok=True
    )

    filename = Path(
        s3_key
    ).name

    local_path = (
        destination_directory
        / filename
    )

    try:
        logger.info(
            "Downloading s3://%s/%s to %s",
            S3_BUCKET,
            s3_key,
            local_path
        )

        s3_client.download_file(
            S3_BUCKET,
            s3_key,
            str(local_path)
        )

        logger.info(
            "Download completed successfully: %s",
            local_path
        )

        return local_path

    except (ClientError, BotoCoreError) as error:
        logger.error(
            "Failed to download S3 object '%s': %s",
            s3_key,
            error
        )

        return None


def download_s3_objects(
    s3_client,
    object_keys,
    local_directory,
    dataset_name
):
    """
    Download multiple S3 objects into a local staging directory.

    Args:
        s3_client: Configured Boto3 S3 client.
        object_keys: List of S3 object keys.
        local_directory: Local destination directory.
        dataset_name: Name used in logging, such as images or videos.

    Returns:
        Tuple containing:
        - number of successful downloads
        - number of failed downloads
    """

    logger.info(
        "Starting %s download. Objects to download: %d",
        dataset_name,
        len(object_keys)
    )

    successful_downloads = 0
    failed_downloads = 0

    for s3_key in object_keys:
        downloaded_path = download_s3_object(
            s3_client,
            s3_key,
            local_directory
        )

        if downloaded_path:
            successful_downloads += 1
        else:
            failed_downloads += 1

    logger.info(
        "%s download completed | Successful: %d | Failed: %d",
        dataset_name,
        successful_downloads,
        failed_downloads
    )

    return (
        successful_downloads,
        failed_downloads
    )


def main():
    """
    Run the SentinelVision raw-data ingestion workflow.

    Workflow:
    1. Connect to Amazon S3.
    2. Discover raw image objects.
    3. Discover raw video objects.
    4. Download images into the local image staging directory.
    5. Download videos into the local video staging directory.
    6. Report overall ingestion status.
    """

    logger.info(
        "Starting SentinelVision S3 ingestion workflow."
    )

    logger.info(
        "Bucket: %s | Region: %s | AWS profile: %s",
        S3_BUCKET,
        AWS_REGION,
        AWS_PROFILE
    )

    try:
        # -------------------------------------------------------------------
        # Step 1: Create S3 client
        # -------------------------------------------------------------------

        s3_client = create_s3_client()

        # -------------------------------------------------------------------
        # Step 2: Discover raw image data
        # -------------------------------------------------------------------

        image_objects = list_s3_objects(
            s3_client,
            IMAGE_PREFIX
        )

        # -------------------------------------------------------------------
        # Step 3: Discover raw video data
        # -------------------------------------------------------------------

        video_objects = list_s3_objects(
            s3_client,
            VIDEO_PREFIX
        )

        # -------------------------------------------------------------------
        # Step 4: Download raw images
        # -------------------------------------------------------------------

        (
            successful_image_downloads,
            failed_image_downloads
        ) = download_s3_objects(
            s3_client,
            image_objects,
            STAGING_IMAGE_DIRECTORY,
            "image"
        )

        # -------------------------------------------------------------------
        # Step 5: Download raw videos
        # -------------------------------------------------------------------

        (
            successful_video_downloads,
            failed_video_downloads
        ) = download_s3_objects(
            s3_client,
            video_objects,
            STAGING_VIDEO_DIRECTORY,
            "video"
        )

        # -------------------------------------------------------------------
        # Step 6: Calculate overall download results
        # -------------------------------------------------------------------

        total_objects = (
            len(image_objects)
            + len(video_objects)
        )

        total_successful_downloads = (
            successful_image_downloads
            + successful_video_downloads
        )

        total_failed_downloads = (
            failed_image_downloads
            + failed_video_downloads
        )

        # -------------------------------------------------------------------
        # Step 7: Report ingestion summary
        # -------------------------------------------------------------------

        logger.info(
            "S3 ingestion summary | "
            "Objects discovered: %d | "
            "Downloaded: %d | "
            "Failed: %d",
            total_objects,
            total_successful_downloads,
            total_failed_downloads
        )

        if (
            total_objects > 0
            and total_successful_downloads == total_objects
            and total_failed_downloads == 0
        ):
            logger.info(
                "S3 ingestion workflow status: PASS"
            )
        else:
            logger.warning(
                "S3 ingestion workflow status: ISSUES FOUND"
            )

    except RuntimeError as error:
        logger.error(
            "AWS configuration error: %s",
            error
        )

    except (ClientError, BotoCoreError) as error:
        logger.exception(
            "AWS error occurred during S3 ingestion: %s",
            error
        )

    except Exception:
        logger.exception(
            "Unexpected error occurred during S3 ingestion."
        )


if __name__ == "__main__":
    main()

    