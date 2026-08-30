import csv
import logging
from pathlib import Path

from src.image_metadata import extract_image_metadata
from src.s3_ingestion import (
    IMAGE_PREFIX,
    VIDEO_PREFIX,
    STAGING_IMAGE_DIRECTORY,
    STAGING_VIDEO_DIRECTORY,
    create_s3_client,
    download_s3_objects,
    list_s3_objects,
)
from src.video_metadata import extract_video_metadata


# ---------------------------------------------------------------------------
# Pipeline configuration
# ---------------------------------------------------------------------------

IMAGE_METADATA_OUTPUT = "data/processed/image_metadata.csv"
VIDEO_METADATA_OUTPUT = "data/processed/video_metadata.csv"


IMAGE_METADATA_FIELDS = [
    "file_path",
    "is_corrupted",
    "error",
    "width",
    "height",
    "channels",
    "file_size_bytes",
    "sha256",
    "brightness",
    "blur_score",
    "brightness_warning",
    "blur_warning",
]


VIDEO_METADATA_FIELDS = [
    "file_path",
    "is_corrupted",
    "error",
    "file_size_bytes",
    "sha256",
    "width",
    "height",
    "fps",
    "frame_count",
    "duration_seconds",
]


# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

logger = logging.getLogger(__name__)


def process_staged_images():
    """
    Extract metadata from every image in the local staging directory.

    Returns:
        Number of image records successfully written to the output CSV.
    """

    staging_directory = Path(
        STAGING_IMAGE_DIRECTORY
    )

    logger.info(
        "Processing staged images from %s.",
        staging_directory
    )

    if not staging_directory.exists():
        logger.error(
            "Image staging directory does not exist: %s",
            staging_directory
        )

        return 0

    image_files = [
        file_path
        for file_path in staging_directory.iterdir()
        if file_path.is_file()
    ]

    logger.info(
        "Found %d staged image file(s).",
        len(image_files)
    )

    if not image_files:
        logger.warning(
            "No staged image files were found."
        )

        return 0

    all_metadata = []

    for file_path in image_files:
        try:
            metadata = extract_image_metadata(
                str(file_path)
            )

            all_metadata.append(
                metadata
            )

        except Exception:
            logger.exception(
                "Failed to process staged image: %s",
                file_path
            )

    if not all_metadata:
        logger.warning(
            "No image metadata was generated."
        )

        return 0

    output_path = Path(
        IMAGE_METADATA_OUTPUT
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    try:
        with open(
            output_path,
            "w",
            newline=""
        ) as csvfile:
            writer = csv.DictWriter(
                csvfile,
                fieldnames=IMAGE_METADATA_FIELDS,
                extrasaction="ignore"
            )

            writer.writeheader()
            writer.writerows(
                all_metadata
            )

        logger.info(
            "Image metadata written successfully to %s.",
            output_path
        )

        return len(all_metadata)

    except OSError:
        logger.exception(
            "Failed to write image metadata CSV: %s",
            output_path
        )

        return 0


def process_staged_videos():
    """
    Extract metadata from every video in the local staging directory.

    Returns:
        Number of video records successfully written to the output CSV.
    """

    staging_directory = Path(
        STAGING_VIDEO_DIRECTORY
    )

    logger.info(
        "Processing staged videos from %s.",
        staging_directory
    )

    if not staging_directory.exists():
        logger.error(
            "Video staging directory does not exist: %s",
            staging_directory
        )

        return 0

    video_files = [
        file_path
        for file_path in staging_directory.iterdir()
        if file_path.is_file()
    ]

    logger.info(
        "Found %d staged video file(s).",
        len(video_files)
    )

    if not video_files:
        logger.warning(
            "No staged video files were found."
        )

        return 0

    all_metadata = []

    for file_path in video_files:
        try:
            metadata = extract_video_metadata(
                str(file_path)
            )

            all_metadata.append(
                metadata
            )

        except Exception:
            logger.exception(
                "Failed to process staged video: %s",
                file_path
            )

    if not all_metadata:
        logger.warning(
            "No video metadata was generated."
        )

        return 0

    output_path = Path(
        VIDEO_METADATA_OUTPUT
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    try:
        with open(
            output_path,
            "w",
            newline=""
        ) as csvfile:
            writer = csv.DictWriter(
                csvfile,
                fieldnames=VIDEO_METADATA_FIELDS,
                extrasaction="ignore"
            )

            writer.writeheader()
            writer.writerows(
                all_metadata
            )

        logger.info(
            "Video metadata written successfully to %s.",
            output_path
        )

        return len(all_metadata)

    except OSError:
        logger.exception(
            "Failed to write video metadata CSV: %s",
            output_path
        )

        return 0


def run_pipeline():
    """
    Run the SentinelVision end-to-end data pipeline.

    Current stages:
    1. Verify Amazon S3 connectivity.
    2. Discover raw image and video objects.
    3. Download raw images into local staging.
    4. Download raw videos into local staging.
    5. Extract image metadata from staged images.
    6. Extract video metadata from staged videos.

    Future stages:
    7. Load processed metadata into PostgreSQL.
    8. Validate the processed dataset.
    9. Upload processed metadata back to S3.
    """

    logger.info(
        "Starting SentinelVision data pipeline."
    )

    # -----------------------------------------------------------------------
    # Stage 1: Verify AWS S3 connectivity
    # -----------------------------------------------------------------------

    logger.info(
        "Stage 1: Verifying Amazon S3 connectivity."
    )

    try:
        s3_client = create_s3_client()

        logger.info(
            "Stage 1 completed successfully."
        )

    except Exception:
        logger.exception(
            "Stage 1 failed. Unable to connect to Amazon S3."
        )

        return

    # -----------------------------------------------------------------------
    # Stage 2: Discover raw S3 objects
    # -----------------------------------------------------------------------

    logger.info(
        "Stage 2: Discovering raw image and video objects in S3."
    )

    try:
        image_objects = list_s3_objects(
            s3_client,
            IMAGE_PREFIX
        )

        video_objects = list_s3_objects(
            s3_client,
            VIDEO_PREFIX
        )

        logger.info(
            "Raw image objects discovered: %d",
            len(image_objects)
        )

        logger.info(
            "Raw video objects discovered: %d",
            len(video_objects)
        )

        if not image_objects and not video_objects:
            logger.warning(
                "Stage 2 failed. No raw S3 objects were discovered."
            )

            return

        logger.info(
            "Stage 2 completed successfully."
        )

    except Exception:
        logger.exception(
            "Stage 2 failed while discovering S3 objects."
        )

        return

    # -----------------------------------------------------------------------
    # Stage 3: Download raw images
    # -----------------------------------------------------------------------

    logger.info(
        "Stage 3: Downloading raw images into local staging."
    )

    try:
        (
            successful_image_downloads,
            failed_image_downloads
        ) = download_s3_objects(
            s3_client,
            image_objects,
            STAGING_IMAGE_DIRECTORY,
            "image"
        )

        if failed_image_downloads > 0:
            logger.warning(
                "Stage 3 completed with issues | "
                "Successful: %d | Failed: %d",
                successful_image_downloads,
                failed_image_downloads
            )
        else:
            logger.info(
                "Stage 3 completed successfully | Downloaded: %d",
                successful_image_downloads
            )

    except Exception:
        logger.exception(
            "Stage 3 failed while downloading raw images."
        )

        return

    # -----------------------------------------------------------------------
    # Stage 4: Download raw videos
    # -----------------------------------------------------------------------

    logger.info(
        "Stage 4: Downloading raw videos into local staging."
    )

    try:
        (
            successful_video_downloads,
            failed_video_downloads
        ) = download_s3_objects(
            s3_client,
            video_objects,
            STAGING_VIDEO_DIRECTORY,
            "video"
        )

        if failed_video_downloads > 0:
            logger.warning(
                "Stage 4 completed with issues | "
                "Successful: %d | Failed: %d",
                successful_video_downloads,
                failed_video_downloads
            )
        else:
            logger.info(
                "Stage 4 completed successfully | Downloaded: %d",
                successful_video_downloads
            )

    except Exception:
        logger.exception(
            "Stage 4 failed while downloading raw videos."
        )

        return

    # -----------------------------------------------------------------------
    # Stage 5: Extract metadata from staged images
    # -----------------------------------------------------------------------

    logger.info(
        "Stage 5: Extracting metadata from staged images."
    )

    try:
        image_metadata_count = process_staged_images()

        if image_metadata_count == 0:
            logger.warning(
                "Stage 5 failed. No image metadata records were generated."
            )

            return

        logger.info(
            "Stage 5 completed successfully | "
            "Image metadata records: %d",
            image_metadata_count
        )

    except Exception:
        logger.exception(
            "Stage 5 failed during image metadata extraction."
        )

        return

    # -----------------------------------------------------------------------
    # Stage 6: Extract metadata from staged videos
    # -----------------------------------------------------------------------

    logger.info(
        "Stage 6: Extracting metadata from staged videos."
    )

    try:
        video_metadata_count = process_staged_videos()

        if video_metadata_count == 0:
            logger.warning(
                "Stage 6 failed. No video metadata records were generated."
            )

            return

        logger.info(
            "Stage 6 completed successfully | "
            "Video metadata records: %d",
            video_metadata_count
        )

    except Exception:
        logger.exception(
            "Stage 6 failed during video metadata extraction."
        )

        return

    # -----------------------------------------------------------------------
    # Pipeline summary
    # -----------------------------------------------------------------------

    total_discovered = (
        len(image_objects)
        + len(video_objects)
    )

    total_downloaded = (
        successful_image_downloads
        + successful_video_downloads
    )

    total_failed_downloads = (
        failed_image_downloads
        + failed_video_downloads
    )

    total_metadata_records = (
        image_metadata_count
        + video_metadata_count
    )

    logger.info(
        "Pipeline summary | "
        "S3 objects discovered: %d | "
        "Downloaded: %d | "
        "Download failures: %d | "
        "Metadata records generated: %d",
        total_discovered,
        total_downloaded,
        total_failed_downloads,
        total_metadata_records
    )

    if (
        total_discovered > 0
        and total_downloaded == total_discovered
        and total_failed_downloads == 0
        and image_metadata_count == len(image_objects)
        and video_metadata_count == len(video_objects)
    ):
        logger.info(
            "SentinelVision pipeline status: PASS"
        )
    else:
        logger.warning(
            "SentinelVision pipeline status: ISSUES FOUND"
        )


if __name__ == "__main__":
    run_pipeline()
    