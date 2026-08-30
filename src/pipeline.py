import csv
import logging
from pathlib import Path

from botocore.exceptions import BotoCoreError, ClientError

from src.dataset_validation import run_dataset_validation
from src.image_metadata import extract_image_metadata
from src.load_to_postgres import load_image_metadata
from src.load_videos_to_postgres import load_video_metadata
from src.s3_ingestion import (
    IMAGE_PREFIX,
    VIDEO_PREFIX,
    S3_BUCKET,
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

IMAGE_METADATA_S3_KEY = "metadata/image_metadata.csv"
VIDEO_METADATA_S3_KEY = "metadata/video_metadata.csv"


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


# ---------------------------------------------------------------------------
# Image processing
# ---------------------------------------------------------------------------

def process_staged_images():
    """
    Extract metadata from every image in the image staging directory.

    The metadata includes:
    - file path
    - corruption status
    - dimensions
    - file size
    - SHA-256 hash
    - brightness
    - blur score
    - quality warnings

    Returns:
        Number of image metadata records written to the processed CSV.
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

    image_files = sorted(
        file_path
        for file_path in staging_directory.iterdir()
        if file_path.is_file()
    )

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
        logger.error(
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
        with output_path.open(
            "w",
            newline="",
            encoding="utf-8"
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


# ---------------------------------------------------------------------------
# Video processing
# ---------------------------------------------------------------------------

def process_staged_videos():
    """
    Extract metadata from every video in the video staging directory.

    The metadata includes:
    - file path
    - corruption status
    - file size
    - SHA-256 hash
    - dimensions
    - FPS
    - frame count
    - duration

    Returns:
        Number of video metadata records written to the processed CSV.
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

    video_files = sorted(
        file_path
        for file_path in staging_directory.iterdir()
        if file_path.is_file()
    )

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
        logger.error(
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
        with output_path.open(
            "w",
            newline="",
            encoding="utf-8"
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


# ---------------------------------------------------------------------------
# Processed metadata S3 upload
# ---------------------------------------------------------------------------

def upload_processed_metadata_to_s3(
    s3_client
):
    """
    Upload refreshed image and video metadata files to Amazon S3.

    Existing objects under the metadata/ prefix are replaced with the
    newest processed versions.

    Args:
        s3_client: Configured Boto3 Amazon S3 client.

    Returns:
        True if both metadata files are uploaded and verified successfully.
        False otherwise.
    """

    uploads = [
        (
            IMAGE_METADATA_OUTPUT,
            IMAGE_METADATA_S3_KEY
        ),
        (
            VIDEO_METADATA_OUTPUT,
            VIDEO_METADATA_S3_KEY
        ),
    ]

    successful_uploads = 0

    for local_path, s3_key in uploads:
        file_path = Path(
            local_path
        )

        if not file_path.exists():
            logger.error(
                "Metadata file does not exist: %s",
                file_path
            )
            continue

        try:
            logger.info(
                "Uploading %s to s3://%s/%s",
                file_path,
                S3_BUCKET,
                s3_key
            )

            s3_client.upload_file(
                str(file_path),
                S3_BUCKET,
                s3_key
            )

            # Verify that the uploaded object now exists in S3.
            s3_client.head_object(
                Bucket=S3_BUCKET,
                Key=s3_key
            )

            successful_uploads += 1

            logger.info(
                "Metadata upload verified successfully: "
                "s3://%s/%s",
                S3_BUCKET,
                s3_key
            )

        except (ClientError, BotoCoreError):
            logger.exception(
                "Failed to upload metadata file to S3: %s",
                file_path
            )

    logger.info(
        "Processed metadata S3 upload summary | "
        "Successful: %d | Failed: %d",
        successful_uploads,
        len(uploads) - successful_uploads
    )

    return successful_uploads == len(uploads)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_pipeline():
    """
    Run the complete SentinelVision data engineering pipeline.

    Pipeline stages:
    1. Verify Amazon S3 connectivity.
    2. Discover raw image and video objects in S3.
    3. Download raw images into local staging.
    4. Download raw videos into local staging.
    5. Extract image metadata and image-quality information.
    6. Extract video metadata.
    7. Load processed metadata into PostgreSQL.
    8. Run ML-readiness and dataset-quality validation.
    9. Upload refreshed processed metadata back to Amazon S3.

    Dataset quality warnings do not automatically mean that the
    technical pipeline execution failed. Quality findings are reported
    separately from execution failures.
    """

    logger.info(
        "============================================================"
    )

    logger.info(
        "Starting SentinelVision end-to-end data pipeline."
    )

    logger.info(
        "============================================================"
    )

    # -----------------------------------------------------------------------
    # Stage 1: Verify Amazon S3 connectivity
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
        return False

    # -----------------------------------------------------------------------
    # Stage 2: Discover raw objects
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

        total_discovered = (
            len(image_objects)
            + len(video_objects)
        )

        if total_discovered == 0:
            logger.error(
                "Stage 2 failed. No raw S3 objects were discovered."
            )
            return False

        logger.info(
            "Stage 2 completed successfully."
        )

    except Exception:
        logger.exception(
            "Stage 2 failed while discovering S3 objects."
        )
        return False

    # -----------------------------------------------------------------------
    # Stage 3: Download images
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
            logger.error(
                "Stage 3 failed | Successful: %d | Failed: %d",
                successful_image_downloads,
                failed_image_downloads
            )
            return False

        if successful_image_downloads != len(
            image_objects
        ):
            logger.error(
                "Stage 3 failed. Expected %d image download(s), "
                "but received %d.",
                len(image_objects),
                successful_image_downloads
            )
            return False

        logger.info(
            "Stage 3 completed successfully | Downloaded: %d",
            successful_image_downloads
        )

    except Exception:
        logger.exception(
            "Stage 3 failed while downloading raw images."
        )
        return False

    # -----------------------------------------------------------------------
    # Stage 4: Download videos
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
            logger.error(
                "Stage 4 failed | Successful: %d | Failed: %d",
                successful_video_downloads,
                failed_video_downloads
            )
            return False

        if successful_video_downloads != len(
            video_objects
        ):
            logger.error(
                "Stage 4 failed. Expected %d video download(s), "
                "but received %d.",
                len(video_objects),
                successful_video_downloads
            )
            return False

        logger.info(
            "Stage 4 completed successfully | Downloaded: %d",
            successful_video_downloads
        )

    except Exception:
        logger.exception(
            "Stage 4 failed while downloading raw videos."
        )
        return False

    # -----------------------------------------------------------------------
    # Stage 5: Extract image metadata
    # -----------------------------------------------------------------------

    logger.info(
        "Stage 5: Extracting metadata from staged images."
    )

    try:
        image_metadata_count = process_staged_images()

        if image_metadata_count == 0:
            logger.error(
                "Stage 5 failed. No image metadata records "
                "were generated."
            )
            return False

        if image_metadata_count != len(
            image_objects
        ):
            logger.error(
                "Stage 5 failed. Expected %d image metadata record(s), "
                "but generated %d.",
                len(image_objects),
                image_metadata_count
            )
            return False

        logger.info(
            "Stage 5 completed successfully | "
            "Image metadata records: %d",
            image_metadata_count
        )

    except Exception:
        logger.exception(
            "Stage 5 failed during image metadata extraction."
        )
        return False

    # -----------------------------------------------------------------------
    # Stage 6: Extract video metadata
    # -----------------------------------------------------------------------

    logger.info(
        "Stage 6: Extracting metadata from staged videos."
    )

    try:
        video_metadata_count = process_staged_videos()

        if video_metadata_count == 0:
            logger.error(
                "Stage 6 failed. No video metadata records "
                "were generated."
            )
            return False

        if video_metadata_count != len(
            video_objects
        ):
            logger.error(
                "Stage 6 failed. Expected %d video metadata record(s), "
                "but generated %d.",
                len(video_objects),
                video_metadata_count
            )
            return False

        logger.info(
            "Stage 6 completed successfully | "
            "Video metadata records: %d",
            video_metadata_count
        )

    except Exception:
        logger.exception(
            "Stage 6 failed during video metadata extraction."
        )
        return False

    # -----------------------------------------------------------------------
    # Stage 7: Load metadata into PostgreSQL
    # -----------------------------------------------------------------------

    logger.info(
        "Stage 7: Loading processed metadata into PostgreSQL."
    )

    try:
        logger.info(
            "Loading image metadata into PostgreSQL."
        )

        load_image_metadata()

        logger.info(
            "Loading video metadata into PostgreSQL."
        )

        load_video_metadata()

        logger.info(
            "Stage 7 completed successfully."
        )

    except Exception:
        logger.exception(
            "Stage 7 failed during PostgreSQL loading."
        )
        return False

    # -----------------------------------------------------------------------
    # Stage 8: Dataset validation
    # -----------------------------------------------------------------------

    logger.info(
        "Stage 8: Running dataset quality and ML-readiness validation."
    )

    try:
        validation_result = run_dataset_validation()

        logger.info(
            "Stage 8 completed successfully."
        )

        # The validation module may report genuine data-quality findings,
        # such as blurry images or unknown labels. These are not treated as
        # technical pipeline failures.
        if isinstance(
            validation_result,
            int
        ):
            if validation_result > 0:
                logger.warning(
                    "Dataset quality status: ISSUES FOUND | "
                    "Total validation issues: %d",
                    validation_result
                )
            else:
                logger.info(
                    "Dataset quality status: PASS"
                )
        else:
            logger.info(
                "Dataset validation completed. "
                "Review the validation report above for quality findings."
            )

    except Exception:
        logger.exception(
            "Stage 8 failed while validating the processed dataset."
        )
        return False

    # -----------------------------------------------------------------------
    # Stage 9: Upload refreshed metadata back to S3
    # -----------------------------------------------------------------------

    logger.info(
        "Stage 9: Uploading refreshed processed metadata to Amazon S3."
    )

    try:
        upload_successful = upload_processed_metadata_to_s3(
            s3_client
        )

        if not upload_successful:
            logger.error(
                "Stage 9 failed. One or more metadata files "
                "could not be uploaded or verified."
            )
            return False

        logger.info(
            "Stage 9 completed successfully."
        )

    except Exception:
        logger.exception(
            "Stage 9 failed while uploading processed metadata to S3."
        )
        return False

    # -----------------------------------------------------------------------
    # Final pipeline summary
    # -----------------------------------------------------------------------

    total_downloaded = (
        successful_image_downloads
        + successful_video_downloads
    )

    total_metadata_records = (
        image_metadata_count
        + video_metadata_count
    )

    logger.info(
        "============================================================"
    )

    logger.info(
        "SentinelVision pipeline summary | "
        "S3 objects discovered: %d | "
        "Downloaded: %d | "
        "Image metadata records: %d | "
        "Video metadata records: %d | "
        "Total metadata records: %d",
        total_discovered,
        total_downloaded,
        image_metadata_count,
        video_metadata_count,
        total_metadata_records
    )

    logger.info(
        "Pipeline execution status: PASS"
    )

    logger.info(
        "SentinelVision end-to-end data pipeline completed successfully."
    )

    logger.info(
        "============================================================"
    )

    return True


if __name__ == "__main__":
    run_pipeline()