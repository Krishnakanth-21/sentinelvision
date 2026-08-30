import csv
import hashlib
import logging
import os

import cv2


# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------

# Configure structured logging so that video-processing progress,
# warnings, and errors are clearly visible during pipeline execution.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pipeline configuration
# ---------------------------------------------------------------------------

# Directory containing the raw video dataset.
VIDEO_FOLDER = "data/raw/videos"

# Output CSV containing the extracted video metadata.
OUTPUT_PATH = "data/processed/video_metadata.csv"


def get_sha256(file_path):
    """
    Calculate the SHA-256 hash of a file.

    The hash provides a content-based identifier that can be used
    to detect duplicate videos across the dataset.
    """

    with open(file_path, "rb") as file:
        return hashlib.sha256(file.read()).hexdigest()


def extract_video_metadata(file_path):
    """
    Extract technical metadata from a video file.

    The function validates that the video can be opened and that at
    least one frame can be read. It then extracts dimensions, FPS,
    frame count, duration, file size, and SHA-256 hash.

    Args:
        file_path: Path to the video file.

    Returns:
        Dictionary containing the extracted video metadata.
    """

    logger.info(
        "Reading video: %s",
        file_path
    )

    # -----------------------------------------------------------------------
    # Step 1: Open the video
    # -----------------------------------------------------------------------

    video = cv2.VideoCapture(
        file_path
    )

    # If OpenCV cannot open the file, mark it as corrupted.
    if not video.isOpened():
        logger.warning(
            "Failed to open video: %s",
            file_path
        )

        return {
            "file_path": file_path,
            "is_corrupted": True,
            "error": "Failed to open video."
        }

    # -----------------------------------------------------------------------
    # Step 2: Validate that video frames can be read
    # -----------------------------------------------------------------------

    # Reading the first frame provides an additional validation step.
    # A container may open successfully even when its video content
    # cannot be decoded correctly.
    success, _ = video.read()

    if not success:
        video.release()

        logger.warning(
            "Failed to read video frame: %s",
            file_path
        )

        return {
            "file_path": file_path,
            "is_corrupted": True,
            "error": "Failed to read video frame."
        }

    # -----------------------------------------------------------------------
    # Step 3: Extract video properties
    # -----------------------------------------------------------------------

    width = int(
        video.get(
            cv2.CAP_PROP_FRAME_WIDTH
        )
    )

    height = int(
        video.get(
            cv2.CAP_PROP_FRAME_HEIGHT
        )
    )

    fps = float(
        video.get(
            cv2.CAP_PROP_FPS
        )
    )

    frame_count = int(
        video.get(
            cv2.CAP_PROP_FRAME_COUNT
        )
    )

    # -----------------------------------------------------------------------
    # Step 4: Calculate video duration
    # -----------------------------------------------------------------------

    # Duration is calculated using the total number of frames
    # divided by the video's frame rate.
    if fps > 0:
        duration_seconds = (
            frame_count / fps
        )
    else:
        duration_seconds = 0

        logger.warning(
            "Invalid FPS detected for video: %s",
            file_path
        )

    # Release the OpenCV video resource only after all required
    # video properties have been extracted.
    video.release()

    # -----------------------------------------------------------------------
    # Step 5: Extract file-level metadata
    # -----------------------------------------------------------------------

    file_size_bytes = os.path.getsize(
        file_path
    )

    file_hash = get_sha256(
        file_path
    )

    # -----------------------------------------------------------------------
    # Step 6: Log successful extraction
    # -----------------------------------------------------------------------

    logger.info(
        "Video processed successfully: %s | "
        "Dimensions: %dx%d | "
        "FPS: %.2f | "
        "Frames: %d | "
        "Duration: %.2f seconds",
        file_path,
        width,
        height,
        fps,
        frame_count,
        duration_seconds
    )

    # -----------------------------------------------------------------------
    # Step 7: Return structured metadata
    # -----------------------------------------------------------------------

    return {
        "file_path": file_path,
        "is_corrupted": False,
        "error": None,
        "file_size_bytes": file_size_bytes,
        "sha256": file_hash,
        "width": width,
        "height": height,
        "fps": fps,
        "frame_count": frame_count,
        "duration_seconds": duration_seconds
    }


def process_video_folder():
    """
    Process every file in the raw video directory.

    Metadata is extracted from each video and written to the processed
    video metadata CSV file.
    """

    logger.info(
        "Starting SentinelVision video metadata extraction."
    )

    logger.info(
        "Video directory: %s",
        VIDEO_FOLDER
    )

    all_metadata = []

    # -----------------------------------------------------------------------
    # Step 1: Read files from the raw video directory
    # -----------------------------------------------------------------------

    try:
        filenames = os.listdir(
            VIDEO_FOLDER
        )

    except FileNotFoundError:
        logger.error(
            "Video directory was not found: %s",
            VIDEO_FOLDER
        )

        return

    except OSError:
        logger.exception(
            "Failed to access video directory: %s",
            VIDEO_FOLDER
        )

        return

    logger.info(
        "Found %d file(s) to process.",
        len(filenames)
    )

    # -----------------------------------------------------------------------
    # Step 2: Extract metadata from every video
    # -----------------------------------------------------------------------

    for filename in filenames:
        file_path = os.path.join(
            VIDEO_FOLDER,
            filename
        )

        try:
            metadata = extract_video_metadata(
                file_path
            )

            all_metadata.append(
                metadata
            )

        except (OSError, cv2.error) as error:
            logger.exception(
                "Failed to process video %s: %s",
                file_path,
                error
            )

    logger.info(
        "Total videos processed: %d",
        len(all_metadata)
    )

    # -----------------------------------------------------------------------
    # Step 3: Stop if no metadata was generated
    # -----------------------------------------------------------------------

    if not all_metadata:
        logger.warning(
            "No video metadata was generated. "
            "CSV file will not be written."
        )

        return

    # -----------------------------------------------------------------------
    # Step 4: Define the stable output schema
    # -----------------------------------------------------------------------

    fieldnames = [
        "file_path",
        "is_corrupted",
        "error",
        "file_size_bytes",
        "sha256",
        "width",
        "height",
        "fps",
        "frame_count",
        "duration_seconds"
    ]

    # -----------------------------------------------------------------------
    # Step 5: Write processed metadata to CSV
    # -----------------------------------------------------------------------

    try:
        # Ensure the processed-data directory exists.
        output_directory = os.path.dirname(
            OUTPUT_PATH
        )

        if output_directory:
            os.makedirs(
                output_directory,
                exist_ok=True
            )

        with open(
            OUTPUT_PATH,
            "w",
            newline=""
        ) as csvfile:
            writer = csv.DictWriter(
                csvfile,
                fieldnames=fieldnames,
                extrasaction="ignore"
            )

            writer.writeheader()
            writer.writerows(
                all_metadata
            )

        logger.info(
            "Video metadata saved successfully to %s.",
            OUTPUT_PATH
        )

    except OSError:
        logger.exception(
            "Failed to write video metadata CSV: %s",
            OUTPUT_PATH
        )

        return

    # -----------------------------------------------------------------------
    # Step 6: Report pipeline completion
    # -----------------------------------------------------------------------

    corrupted_count = sum(
        metadata.get(
            "is_corrupted",
            False
        )
        for metadata in all_metadata
    )

    valid_count = (
        len(all_metadata)
        - corrupted_count
    )

    logger.info(
        "Video metadata extraction completed | "
        "Processed: %d | "
        "Corrupted: %d | "
        "Valid: %d",
        len(all_metadata),
        corrupted_count,
        valid_count
    )


if __name__ == "__main__":
    process_video_folder()
    