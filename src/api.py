import logging
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from src.image_metadata import extract_image_metadata
from src.s3_ingestion import S3_BUCKET, create_s3_client
from src.video_metadata import extract_video_metadata


# ---------------------------------------------------------------------------
# API configuration
# ---------------------------------------------------------------------------

API_VERSION = "1.0.0"

UPLOAD_ROOT = Path("data/api_uploads")

MAX_IMAGE_SIZE_BYTES = 20 * 1024 * 1024
MAX_VIDEO_SIZE_BYTES = 200 * 1024 * 1024

ALLOWED_IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".avif",
}

ALLOWED_VIDEO_EXTENSIONS = {
    ".mp4",
}

ALLOWED_REACT_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# In-memory result storage
# ---------------------------------------------------------------------------

# This registry allows the React frontend to retrieve analysis results
# during the lifetime of the running API process.
#
# PostgreSQL remains the persistent structured-data store used by the
# SentinelVision engineering pipeline. This registry is intentionally
# lightweight for the public-facing portfolio API.
dataset_results: dict[str, dict[str, Any]] = {}


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="SentinelVision API",
    description=(
        "Public API for uploading, analysing, and inspecting image "
        "and video datasets using the SentinelVision data platform."
    ),
    version=API_VERSION,
)


# ---------------------------------------------------------------------------
# CORS configuration
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_REACT_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def validate_file_extension(
    filename: str | None,
    allowed_extensions: set[str],
    media_type: str,
) -> str:
    """
    Validate the extension of an uploaded media file.

    Args:
        filename: Original uploaded filename.
        allowed_extensions: Extensions accepted for the media type.
        media_type: Human-readable media type used in error messages.

    Returns:
        Normalised lowercase file extension.

    Raises:
        HTTPException: If the filename or extension is invalid.
    """

    if not filename:
        logger.warning(
            "%s upload rejected because no filename was supplied.",
            media_type.capitalize(),
        )

        raise HTTPException(
            status_code=400,
            detail="Uploaded file must have a filename.",
        )

    extension = Path(filename).suffix.lower()

    if extension not in allowed_extensions:
        logger.warning(
            "Unsupported %s extension received: %s",
            media_type,
            extension,
        )

        supported_extensions = ", ".join(
            sorted(allowed_extensions)
        )

        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported {media_type} type. "
                f"Allowed extensions are: {supported_extensions}"
            ),
        )

    return extension


def create_safe_filename(
    original_filename: str,
    extension: str,
) -> str:
    """
    Create a safe unique filename.

    Unsafe characters are removed from the original filename and a UUID
    is appended so separate uploads cannot overwrite each other.

    Args:
        original_filename: Original uploaded filename.
        extension: Validated file extension.

    Returns:
        Safe unique filename.
    """

    original_stem = Path(original_filename).stem

    safe_stem = "".join(
        character
        for character in original_stem
        if character.isalnum()
        or character in {"-", "_"}
    )

    if not safe_stem:
        safe_stem = "media"

    return (
        f"{safe_stem}_"
        f"{uuid4().hex}"
        f"{extension}"
    )


def validate_dataset_id(dataset_id: str) -> str:
    """
    Validate that a dataset identifier is a correctly formatted UUID.

    Args:
        dataset_id: Dataset identifier received from the API route.

    Returns:
        Normalised UUID string.

    Raises:
        HTTPException: If the identifier is invalid.
    """

    try:
        return str(
            UUID(dataset_id)
        )

    except ValueError as error:
        logger.warning(
            "Invalid dataset ID received: %s",
            dataset_id,
        )

        raise HTTPException(
            status_code=400,
            detail="Invalid dataset ID.",
        ) from error


async def read_upload_with_limit(
    file: UploadFile,
    maximum_size: int,
    media_type: str,
) -> bytes:
    """
    Read an uploaded file while enforcing a maximum file size.

    The upload is read in chunks so an unexpectedly large request does
    not need to be loaded into memory before the limit can be checked.

    Args:
        file: Uploaded FastAPI file.
        maximum_size: Maximum permitted size in bytes.
        media_type: Human-readable media type.

    Returns:
        Uploaded file content.

    Raises:
        HTTPException: If the file is empty or exceeds the size limit.
    """

    chunk_size = 1024 * 1024
    content = bytearray()

    while True:
        chunk = await file.read(chunk_size)

        if not chunk:
            break

        content.extend(chunk)

        if len(content) > maximum_size:
            logger.warning(
                "%s upload rejected because it exceeded %d bytes.",
                media_type.capitalize(),
                maximum_size,
            )

            raise HTTPException(
                status_code=413,
                detail=(
                    f"Uploaded {media_type} exceeds the "
                    "maximum permitted file size."
                ),
            )

    if not content:
        logger.warning(
            "Empty %s upload rejected.",
            media_type,
        )

        raise HTTPException(
            status_code=400,
            detail=f"Uploaded {media_type} is empty.",
        )

    return bytes(content)


# ---------------------------------------------------------------------------
# Storage helpers
# ---------------------------------------------------------------------------

def save_uploaded_file(
    dataset_id: str,
    media_type: str,
    filename: str,
    content: bytes,
) -> Path:
    """
    Save uploaded media into a dataset-specific local directory.

    Args:
        dataset_id: Unique dataset identifier.
        media_type: Either images or videos.
        filename: Safe generated filename.
        content: Uploaded file bytes.

    Returns:
        Local path of the saved file.

    Raises:
        HTTPException: If local storage fails.
    """

    destination_directory = (
        UPLOAD_ROOT
        / dataset_id
        / media_type
    )

    try:
        destination_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        destination_path = (
            destination_directory
            / filename
        )

        destination_path.write_bytes(
            content
        )

        logger.info(
            "Uploaded file saved locally | "
            "Dataset: %s | Path: %s | Size: %d bytes",
            dataset_id,
            destination_path,
            len(content),
        )

        return destination_path

    except OSError as error:
        logger.exception(
            "Failed to save uploaded file | Dataset: %s",
            dataset_id,
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to save uploaded file.",
        ) from error


def upload_file_to_s3(
    local_path: Path,
    dataset_id: str,
    media_type: str,
) -> str:
    """
    Upload media to the dataset-specific Amazon S3 prefix.

    Args:
        local_path: Local uploaded file.
        dataset_id: Unique dataset identifier.
        media_type: Either images or videos.

    Returns:
        S3 object key.

    Raises:
        HTTPException: If the S3 upload fails.
    """

    s3_key = (
        f"datasets/{dataset_id}/"
        f"raw/{media_type}/"
        f"{local_path.name}"
    )

    try:
        s3_client = create_s3_client()

        logger.info(
            "Uploading API media to s3://%s/%s",
            S3_BUCKET,
            s3_key,
        )

        s3_client.upload_file(
            str(local_path),
            S3_BUCKET,
            s3_key,
        )

        s3_client.head_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
        )

        logger.info(
            "S3 upload verified | Dataset: %s | Key: %s",
            dataset_id,
            s3_key,
        )

        return s3_key

    except (ClientError, BotoCoreError, RuntimeError) as error:
        logger.exception(
            "S3 upload failed | Dataset: %s | File: %s",
            dataset_id,
            local_path,
        )

        raise HTTPException(
            status_code=502,
            detail="Failed to store uploaded media in Amazon S3.",
        ) from error


# ---------------------------------------------------------------------------
# Result helpers
# ---------------------------------------------------------------------------

def store_analysis_result(
    dataset_id: str,
    media_type: str,
    original_filename: str,
    saved_filename: str,
    file_size_bytes: int,
    s3_key: str,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    """
    Store an API analysis result in the dataset registry.

    Args:
        dataset_id: Unique dataset identifier.
        media_type: Image or video.
        original_filename: Filename supplied by the user.
        saved_filename: Generated safe filename.
        file_size_bytes: Uploaded size.
        s3_key: Amazon S3 object key.
        metadata: SentinelVision analysis metadata.

    Returns:
        Stored result dictionary.
    """

    dataset = dataset_results.setdefault(
        dataset_id,
        {
            "dataset_id": dataset_id,
            "images": [],
            "videos": [],
        },
    )

    result = {
        "original_filename": original_filename,
        "saved_filename": saved_filename,
        "file_size_bytes": file_size_bytes,
        "s3_key": s3_key,
        "metadata": metadata,
    }

    if media_type == "image":
        dataset["images"].append(
            result
        )
    else:
        dataset["videos"].append(
            result
        )

    logger.info(
        "Analysis result stored | Dataset: %s | Media type: %s",
        dataset_id,
        media_type,
    )

    return result


# ---------------------------------------------------------------------------
# General API endpoints
# ---------------------------------------------------------------------------

@app.get("/")
def read_root():
    """
    Return basic information about the SentinelVision API.
    """

    logger.info(
        "Root endpoint requested."
    )

    return {
        "service": "SentinelVision API",
        "version": API_VERSION,
        "status": "running",
    }


@app.get("/health")
def health_check():
    """
    Return the current health status of the API.
    """

    logger.info(
        "Health check requested."
    )

    return {
        "status": "healthy",
    }


# ---------------------------------------------------------------------------
# Image upload endpoint
# ---------------------------------------------------------------------------

@app.post("/upload/image")
async def upload_image(
    file: UploadFile = File(...),
):
    """
    Upload and analyse one image.

    The endpoint:
    1. Validates the image extension.
    2. Enforces the image size limit.
    3. Creates a unique dataset identifier.
    4. Saves the image locally.
    5. Uploads the raw image to Amazon S3.
    6. Runs SentinelVision OpenCV metadata extraction.
    7. Stores the analysis result.
    8. Returns the result to the client.
    """

    dataset_id = str(
        uuid4()
    )

    logger.info(
        "Image upload request received | "
        "Dataset: %s | Filename: %s",
        dataset_id,
        file.filename,
    )

    try:
        extension = validate_file_extension(
            file.filename,
            ALLOWED_IMAGE_EXTENSIONS,
            "image",
        )

        content = await read_upload_with_limit(
            file,
            MAX_IMAGE_SIZE_BYTES,
            "image",
        )

        safe_filename = create_safe_filename(
            file.filename,
            extension,
        )

        local_path = save_uploaded_file(
            dataset_id,
            "images",
            safe_filename,
            content,
        )

        s3_key = upload_file_to_s3(
            local_path,
            dataset_id,
            "images",
        )

        metadata = extract_image_metadata(
            str(local_path)
        )

        if metadata.get("is_corrupted"):
            logger.warning(
                "Uploaded image could not be decoded | "
                "Dataset: %s | File: %s",
                dataset_id,
                safe_filename,
            )

            raise HTTPException(
                status_code=422,
                detail=(
                    "The uploaded file has a supported extension "
                    "but could not be decoded as a valid image."
                ),
            )

        result = store_analysis_result(
            dataset_id=dataset_id,
            media_type="image",
            original_filename=file.filename,
            saved_filename=safe_filename,
            file_size_bytes=len(content),
            s3_key=s3_key,
            metadata=metadata,
        )

        logger.info(
            "Image upload and analysis completed successfully | "
            "Dataset: %s",
            dataset_id,
        )

        return {
            "status": "success",
            "message": (
                "Image uploaded and analysed successfully."
            ),
            "dataset_id": dataset_id,
            "result": result,
        }

    except HTTPException:
        raise

    except Exception as error:
        logger.exception(
            "Unexpected image upload failure | Dataset: %s",
            dataset_id,
        )

        raise HTTPException(
            status_code=500,
            detail="Unexpected image processing error.",
        ) from error

    finally:
        await file.close()


# ---------------------------------------------------------------------------
# Video upload endpoint
# ---------------------------------------------------------------------------

@app.post("/upload/video")
async def upload_video(
    file: UploadFile = File(...),
):
    """
    Upload and analyse one video.

    The endpoint:
    1. Validates the video extension.
    2. Enforces the video size limit.
    3. Creates a unique dataset identifier.
    4. Saves the video locally.
    5. Uploads the raw video to Amazon S3.
    6. Runs SentinelVision OpenCV metadata extraction.
    7. Stores the analysis result.
    8. Returns the result to the client.
    """

    dataset_id = str(
        uuid4()
    )

    logger.info(
        "Video upload request received | "
        "Dataset: %s | Filename: %s",
        dataset_id,
        file.filename,
    )

    try:
        extension = validate_file_extension(
            file.filename,
            ALLOWED_VIDEO_EXTENSIONS,
            "video",
        )

        content = await read_upload_with_limit(
            file,
            MAX_VIDEO_SIZE_BYTES,
            "video",
        )

        safe_filename = create_safe_filename(
            file.filename,
            extension,
        )

        local_path = save_uploaded_file(
            dataset_id,
            "videos",
            safe_filename,
            content,
        )

        s3_key = upload_file_to_s3(
            local_path,
            dataset_id,
            "videos",
        )

        metadata = extract_video_metadata(
            str(local_path)
        )

        if metadata.get("is_corrupted"):
            logger.warning(
                "Uploaded video could not be decoded | "
                "Dataset: %s | File: %s",
                dataset_id,
                safe_filename,
            )

            raise HTTPException(
                status_code=422,
                detail=(
                    "The uploaded file has a supported extension "
                    "but could not be decoded as a valid video."
                ),
            )

        result = store_analysis_result(
            dataset_id=dataset_id,
            media_type="video",
            original_filename=file.filename,
            saved_filename=safe_filename,
            file_size_bytes=len(content),
            s3_key=s3_key,
            metadata=metadata,
        )

        logger.info(
            "Video upload and analysis completed successfully | "
            "Dataset: %s",
            dataset_id,
        )

        return {
            "status": "success",
            "message": (
                "Video uploaded and analysed successfully."
            ),
            "dataset_id": dataset_id,
            "result": result,
        }

    except HTTPException:
        raise

    except Exception as error:
        logger.exception(
            "Unexpected video upload failure | Dataset: %s",
            dataset_id,
        )

        raise HTTPException(
            status_code=500,
            detail="Unexpected video processing error.",
        ) from error

    finally:
        await file.close()


# ---------------------------------------------------------------------------
# Dataset result endpoints
# ---------------------------------------------------------------------------

@app.get("/datasets")
def list_datasets():
    """
    Return summaries of datasets processed during the current API session.
    """

    logger.info(
        "Dataset list requested."
    )

    datasets = []

    for dataset in dataset_results.values():
        datasets.append(
            {
                "dataset_id": dataset["dataset_id"],
                "image_count": len(
                    dataset["images"]
                ),
                "video_count": len(
                    dataset["videos"]
                ),
            }
        )

    return {
        "dataset_count": len(datasets),
        "datasets": datasets,
    }


@app.get("/datasets/{dataset_id}")
def get_dataset(
    dataset_id: str,
):
    """
    Return analysis results for one dataset.

    Args:
        dataset_id: UUID identifying the dataset.

    Returns:
        Dataset image and video analysis results.
    """

    validated_dataset_id = validate_dataset_id(
        dataset_id
    )

    logger.info(
        "Dataset result requested | Dataset: %s",
        validated_dataset_id,
    )

    dataset = dataset_results.get(
        validated_dataset_id
    )

    if dataset is None:
        logger.warning(
            "Requested dataset was not found: %s",
            validated_dataset_id,
        )

        raise HTTPException(
            status_code=404,
            detail="Dataset not found.",
        )

    return dataset
