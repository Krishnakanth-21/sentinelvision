import csv
import hashlib
import logging
import os

import cv2


# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------

# Configure structured logging so that image-processing progress,
# warnings, and errors are clearly visible during pipeline execution.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pipeline configuration
# ---------------------------------------------------------------------------

# Directory containing the raw image dataset.
IMAGE_FOLDER = "data/raw/images"

# Output CSV containing the extracted image metadata.
OUTPUT_PATH = "data/processed/image_metadata.csv"

# Quality-check thresholds.
DARK_BRIGHTNESS_THRESHOLD = 40
BRIGHT_BRIGHTNESS_THRESHOLD = 200
BLUR_THRESHOLD = 100


def get_sha256(file_path):
    """
    Calculate the SHA-256 hash of a file.

    The hash provides a unique content-based identifier that can be used
    later to detect duplicate images.
    """

    with open(file_path, "rb") as file:
        return hashlib.sha256(file.read()).hexdigest()


def extract_image_metadata(file_path):
    """
    Extract metadata and quality measurements from an image.

    The function extracts dimensions, file size, SHA-256 hash,
    brightness, and blur information. Images that OpenCV cannot read
    are marked as corrupted.
    """

    logger.info(
        "Reading image: %s",
        file_path
    )

    # -----------------------------------------------------------------------
    # Step 1: Read the image
    # -----------------------------------------------------------------------

    image = cv2.imread(file_path)

    # OpenCV returns None when the file cannot be decoded as an image.
    if image is None:
        logger.warning(
            "Failed to read image: %s",
            file_path
        )

        return {
            "file_path": file_path,
            "is_corrupted": True,
            "error": (
                "Failed to read image. "
                "The file may be corrupted or not an image."
            ),
        }

    # -----------------------------------------------------------------------
    # Step 2: Extract basic image metadata
    # -----------------------------------------------------------------------

    height, width, channels = image.shape

    file_size_bytes = os.path.getsize(file_path)
    file_hash = get_sha256(file_path)

    # -----------------------------------------------------------------------
    # Step 3: Convert the image to grayscale
    # -----------------------------------------------------------------------

    # Grayscale simplifies the brightness and blur calculations because
    # only one intensity channel needs to be analysed.
    grey_image = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    )

    # -----------------------------------------------------------------------
    # Step 4: Calculate image brightness
    # -----------------------------------------------------------------------

    # Mean grayscale intensity provides a simple estimate of the overall
    # brightness of the image.
    brightness = float(
        grey_image.mean()
    )

    if brightness < DARK_BRIGHTNESS_THRESHOLD:
        brightness_warning = (
            "Warning: The image is very dark."
        )

        logger.warning(
            "Dark image detected: %s | Brightness: %.2f",
            file_path,
            brightness
        )

    elif brightness > BRIGHT_BRIGHTNESS_THRESHOLD:
        brightness_warning = (
            "Warning: The image is very bright."
        )

        logger.warning(
            "Bright image detected: %s | Brightness: %.2f",
            file_path,
            brightness
        )

    else:
        brightness_warning = "Normal"

    # -----------------------------------------------------------------------
    # Step 5: Calculate image blur score
    # -----------------------------------------------------------------------

    # Variance of the Laplacian is used as a simple sharpness metric.
    # Lower values generally indicate a blurrier image.
    blur_score = float(
        cv2.Laplacian(
            grey_image,
            cv2.CV_64F
        ).var()
    )

    if blur_score < BLUR_THRESHOLD:
        blur_warning = (
            "Warning: The image is blurry."
        )

        logger.warning(
            "Blurry image detected: %s | Blur score: %.2f",
            file_path,
            blur_score
        )

    else:
        blur_warning = "Normal"

    # -----------------------------------------------------------------------
    # Step 6: Return structured metadata
    # -----------------------------------------------------------------------

    logger.info(
        "Image processed successfully: %s | "
        "Dimensions: %dx%d | "
        "Brightness: %.2f | "
        "Blur score: %.2f",
        file_path,
        width,
        height,
        brightness,
        blur_score
    )

    return {
        "file_path": file_path,
        "is_corrupted": False,
        "error": None,
        "width": width,
        "height": height,
        "channels": channels,
        "file_size_bytes": file_size_bytes,
        "sha256": file_hash,
        "brightness": brightness,
        "blur_score": blur_score,
        "brightness_warning": brightness_warning,
        "blur_warning": blur_warning,
    }


def process_image_folder():
    """
    Process all files in the raw image directory.

    Metadata for each image is collected and written to the processed
    image metadata CSV file.
    """

    logger.info(
        "Starting image metadata extraction."
    )

    logger.info(
        "Image directory: %s",
        IMAGE_FOLDER
    )

    all_metadata = []

    # -----------------------------------------------------------------------
    # Step 1: Process every file in the raw image directory
    # -----------------------------------------------------------------------

    try:
        filenames = os.listdir(IMAGE_FOLDER)

    except FileNotFoundError:
        logger.error(
            "Image directory was not found: %s",
            IMAGE_FOLDER
        )

        return

    logger.info(
        "Found %d file(s) to process.",
        len(filenames)
    )

    for filename in filenames:
        file_path = os.path.join(
            IMAGE_FOLDER,
            filename
        )

        try:
            metadata = extract_image_metadata(
                file_path
            )

            all_metadata.append(metadata)

        except (OSError, cv2.error) as error:
            logger.exception(
                "Failed to process %s: %s",
                file_path,
                error
            )

    logger.info(
        "Total images processed: %d",
        len(all_metadata)
    )

    # -----------------------------------------------------------------------
    # Step 2: Write extracted metadata to CSV
    # -----------------------------------------------------------------------

    if not all_metadata:
        logger.warning(
            "No image metadata was generated. "
            "CSV file will not be written."
        )

        return

    fieldnames = [
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

    try:
        # Ensure the processed-data directory exists before writing.
        os.makedirs(
            os.path.dirname(OUTPUT_PATH),
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
            writer.writerows(all_metadata)

        logger.info(
            "Image metadata saved successfully to %s.",
            OUTPUT_PATH
        )

    except OSError as error:
        logger.exception(
            "Failed to write image metadata CSV: %s",
            error
        )

        return

    # -----------------------------------------------------------------------
    # Step 3: Report pipeline completion
    # -----------------------------------------------------------------------

    corrupted_count = sum(
        metadata.get("is_corrupted", False)
        for metadata in all_metadata
    )

    logger.info(
        "Image metadata extraction completed | "
        "Processed: %d | Corrupted: %d | Valid: %d",
        len(all_metadata),
        corrupted_count,
        len(all_metadata) - corrupted_count
    )


if __name__ == "__main__":
    process_image_folder()

    