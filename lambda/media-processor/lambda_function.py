"""
SentinelVision Media Processor Lambda

Processes raw image and video uploads stored in Amazon S3.

Flow:

    S3 raw media upload
            |
            v
    Lambda downloads file to /tmp
            |
            v
    OpenCV extracts technical metadata
            |
            v
    Structured JSON metadata
            |
            v
    S3 processed/metadata.json

This function supports:

Images:
- Width
- Height
- Channels
- Brightness
- Blur / sharpness score
- Basic quality flags

Videos:
- Width
- Height
- FPS
- Frame count
- Duration
- Basic quality flags
"""

import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote_plus

import boto3
import cv2


# ===========================================================================
# Logging
# ===========================================================================

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)


# ===========================================================================
# Configuration
# ===========================================================================

AWS_REGION = os.environ.get(
    "AWS_REGION",
    "ap-southeast-2",
)

S3_BUCKET = os.environ.get(
    "S3_BUCKET",
    "sentinelvision-krishnakanth-2026",
)

BLUR_THRESHOLD = 100.0

LOW_BRIGHTNESS_THRESHOLD = 40.0

HIGH_BRIGHTNESS_THRESHOLD = 220.0


# ===========================================================================
# AWS clients
# ===========================================================================

s3_client = boto3.client(
    "s3",
    region_name=AWS_REGION,
)


# ===========================================================================
# Path helpers
# ===========================================================================

def extract_dataset_information(object_key):
    """
    Extract dataset ID and media type from a SentinelVision S3 object key.

    Expected formats:

    datasets/<dataset-id>/raw/images/<filename>
    datasets/<dataset-id>/raw/videos/<filename>
    """

    parts = object_key.split("/")

    if len(parts) < 5:
        raise ValueError(
            f"Unexpected SentinelVision S3 key: {object_key}"
        )

    if parts[0] != "datasets":
        raise ValueError(
            f"S3 key does not start with datasets/: {object_key}"
        )

    if parts[2] != "raw":
        raise ValueError(
            f"S3 key is not inside a raw directory: {object_key}"
        )

    dataset_id = parts[1]
    media_folder = parts[3]

    if media_folder == "images":
        media_type = "image"

    elif media_folder == "videos":
        media_type = "video"

    else:
        raise ValueError(
            f"Unsupported media folder: {media_folder}"
        )

    return dataset_id, media_type


def build_processed_key(dataset_id):
    """
    Build the processed metadata destination key.
    """

    return (
        f"datasets/{dataset_id}/processed/"
        "metadata.json"
    )


# ===========================================================================
# Image processing
# ===========================================================================

def analyze_image(local_path):
    """
    Extract computer-vision metadata from an image using OpenCV.
    """

    LOGGER.info(
        "Starting image analysis | path=%s",
        local_path,
    )

    image = cv2.imread(
        local_path,
        cv2.IMREAD_UNCHANGED,
    )

    if image is None:
        raise ValueError(
            "OpenCV could not decode the image."
        )

    # -----------------------------------------------------------------------
    # Dimensions
    # -----------------------------------------------------------------------

    height, width = image.shape[:2]

    if len(image.shape) == 2:
        channels = 1
    else:
        channels = image.shape[2]

    # -----------------------------------------------------------------------
    # Convert to grayscale
    # -----------------------------------------------------------------------

    if len(image.shape) == 2:
        grayscale = image
    else:
        grayscale = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY,
        )

    # -----------------------------------------------------------------------
    # Brightness
    # -----------------------------------------------------------------------

    brightness = float(
        grayscale.mean()
    )

    # -----------------------------------------------------------------------
    # Blur / sharpness
    # -----------------------------------------------------------------------

    blur_score = float(
        cv2.Laplacian(
            grayscale,
            cv2.CV_64F,
        ).var()
    )

    is_blurry = (
        blur_score < BLUR_THRESHOLD
    )

    # -----------------------------------------------------------------------
    # Brightness quality classification
    # -----------------------------------------------------------------------

    if brightness < LOW_BRIGHTNESS_THRESHOLD:
        brightness_status = "dark"

    elif brightness > HIGH_BRIGHTNESS_THRESHOLD:
        brightness_status = "bright"

    else:
        brightness_status = "normal"

    LOGGER.info(
        "Image analysis completed | "
        "width=%s | height=%s | "
        "brightness=%.2f | blur_score=%.2f",
        width,
        height,
        brightness,
        blur_score,
    )

    return {
        "width": int(width),
        "height": int(height),
        "channels": int(channels),
        "brightness": round(
            brightness,
            2,
        ),
        "brightness_status": brightness_status,
        "blur_score": round(
            blur_score,
            2,
        ),
        "is_blurry": is_blurry,
    }


# ===========================================================================
# Video processing
# ===========================================================================

def analyze_video(local_path):
    """
    Extract technical video metadata using OpenCV.
    """

    LOGGER.info(
        "Starting video analysis | path=%s",
        local_path,
    )

    capture = cv2.VideoCapture(
        local_path
    )

    if not capture.isOpened():
        raise ValueError(
            "OpenCV could not open the video."
        )

    try:

        width = int(
            capture.get(
                cv2.CAP_PROP_FRAME_WIDTH
            )
        )

        height = int(
            capture.get(
                cv2.CAP_PROP_FRAME_HEIGHT
            )
        )

        fps = float(
            capture.get(
                cv2.CAP_PROP_FPS
            )
        )

        frame_count = int(
            capture.get(
                cv2.CAP_PROP_FRAME_COUNT
            )
        )

        if fps > 0:
            duration_seconds = (
                frame_count / fps
            )
        else:
            duration_seconds = 0.0

    finally:

        capture.release()

    LOGGER.info(
        "Video analysis completed | "
        "width=%s | height=%s | "
        "fps=%.2f | frames=%s | "
        "duration=%.2f seconds",
        width,
        height,
        fps,
        frame_count,
        duration_seconds,
    )

    return {
        "width": width,
        "height": height,
        "fps": round(
            fps,
            2,
        ),
        "frame_count": frame_count,
        "duration_seconds": round(
            duration_seconds,
            2,
        ),
    }


# ===========================================================================
# S3 processing
# ===========================================================================

def process_s3_object(bucket, object_key):
    """
    Process one SentinelVision S3 object.
    """

    LOGGER.info(
        "Starting media processing | "
        "bucket=%s | key=%s",
        bucket,
        object_key,
    )

    # -----------------------------------------------------------------------
    # Prevent recursive processing
    # -----------------------------------------------------------------------

    if "/processed/" in object_key:

        LOGGER.info(
            "Ignoring processed object | key=%s",
            object_key,
        )

        return {
            "status": "ignored",
            "reason": "processed_object",
            "source_key": object_key,
        }

    # -----------------------------------------------------------------------
    # Parse dataset structure
    # -----------------------------------------------------------------------

    dataset_id, media_type = (
        extract_dataset_information(
            object_key
        )
    )

    # -----------------------------------------------------------------------
    # Read S3 object metadata
    # -----------------------------------------------------------------------

    object_metadata = s3_client.head_object(
        Bucket=bucket,
        Key=object_key,
    )

    # -----------------------------------------------------------------------
    # Determine local temporary filename
    # -----------------------------------------------------------------------

    original_filename = (
        object_key.rsplit("/", 1)[-1]
    )

    extension = Path(
        original_filename
    ).suffix

    with tempfile.NamedTemporaryFile(
        suffix=extension,
        delete=False,
    ) as temp_file:

        local_path = temp_file.name

    LOGGER.info(
        "Temporary file created | path=%s",
        local_path,
    )

    try:

        # -------------------------------------------------------------------
        # Download media from S3
        # -------------------------------------------------------------------

        s3_client.download_file(
            bucket,
            object_key,
            local_path,
        )

        LOGGER.info(
            "S3 object downloaded successfully."
        )

        # -------------------------------------------------------------------
        # OpenCV analysis
        # -------------------------------------------------------------------

        if media_type == "image":

            analysis = analyze_image(
                local_path
            )

        elif media_type == "video":

            analysis = analyze_video(
                local_path
            )

        else:

            raise ValueError(
                f"Unsupported media type: {media_type}"
            )

        # -------------------------------------------------------------------
        # Build processed metadata
        # -------------------------------------------------------------------

        processed_metadata = {
            "dataset_id": dataset_id,
            "media_type": media_type,
            "source": {
                "bucket": bucket,
                "key": object_key,
            },
            "file": {
                "filename": original_filename,
                "size_bytes": object_metadata.get(
                    "ContentLength"
                ),
                "content_type": object_metadata.get(
                    "ContentType"
                ),
                "etag": (
                    object_metadata
                    .get("ETag", "")
                    .replace('"', "")
                ),
                "last_modified": (
                    object_metadata
                    .get("LastModified")
                    .isoformat()
                    if object_metadata.get(
                        "LastModified"
                    )
                    else None
                ),
            },
            "analysis": analysis,
            "processing": {
                "status": "processed",
                "processor": (
                    "sentinelvision-media-processor"
                ),
                "processing_engine": "opencv",
                "processed_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            },
        }

        # -------------------------------------------------------------------
        # Write result back to S3
        # -------------------------------------------------------------------

        processed_key = (
            build_processed_key(
                dataset_id
            )
        )

        s3_client.put_object(
            Bucket=bucket,
            Key=processed_key,
            Body=json.dumps(
                processed_metadata,
                indent=2,
            ).encode("utf-8"),
            ContentType="application/json",
        )

        LOGGER.info(
            "Processed metadata written | "
            "key=%s",
            processed_key,
        )

        return {
            "status": "processed",
            "dataset_id": dataset_id,
            "media_type": media_type,
            "source_key": object_key,
            "processed_key": processed_key,
            "analysis": analysis,
        }

    finally:

        # -------------------------------------------------------------------
        # Clean Lambda temporary storage
        # -------------------------------------------------------------------

        if os.path.exists(
            local_path
        ):
            os.remove(
                local_path
            )

            LOGGER.info(
                "Temporary file deleted."
            )


# ===========================================================================
# Lambda handler
# ===========================================================================

def lambda_handler(event, context):
    """
    Handle S3 event notifications or manual test events.
    """

    LOGGER.info(
        "SentinelVision media processor invoked."
    )

    try:

        results = []

        # -------------------------------------------------------------------
        # Real S3 trigger
        # -------------------------------------------------------------------

        if "Records" in event:

            LOGGER.info(
                "Processing S3 event | "
                "record_count=%s",
                len(event["Records"]),
            )

            for record in event["Records"]:

                bucket = (
                    record["s3"]
                    ["bucket"]
                    ["name"]
                )

                object_key = unquote_plus(
                    record["s3"]
                    ["object"]
                    ["key"]
                )

                result = process_s3_object(
                    bucket,
                    object_key,
                )

                results.append(
                    result
                )

        # -------------------------------------------------------------------
        # Manual test
        # -------------------------------------------------------------------

        elif (
            "bucket" in event
            and "key" in event
        ):

            result = process_s3_object(
                event["bucket"],
                event["key"],
            )

            results.append(
                result
            )

        else:

            return {
                "statusCode": 400,
                "body": json.dumps(
                    {
                        "status": "error",
                        "error": (
                            "Unsupported event format."
                        ),
                    }
                ),
            }

        LOGGER.info(
            "Media processing finished | "
            "result_count=%s",
            len(results),
        )

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "status": "success",
                    "processed_count": len(
                        results
                    ),
                    "results": results,
                }
            ),
        }

    except Exception as exc:

        LOGGER.exception(
            "SentinelVision media processing failed."
        )

        return {
            "statusCode": 500,
            "body": json.dumps(
                {
                    "status": "error",
                    "error": str(
                        exc
                    ),
                }
            ),
        }
    