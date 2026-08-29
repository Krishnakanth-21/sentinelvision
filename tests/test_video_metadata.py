import hashlib

from src.video_metadata import get_sha256, extract_video_metadata


TEST_VIDEO = "data/raw/videos/crows.mp4"


def test_get_sha256_is_consistent():
    """The same video should always produce the same SHA-256 hash."""
    first_hash = get_sha256(TEST_VIDEO)
    second_hash = get_sha256(TEST_VIDEO)

    assert first_hash == second_hash


def test_sha256_has_correct_length():
    """A SHA-256 hexadecimal hash should contain 64 characters."""
    file_hash = get_sha256(TEST_VIDEO)

    assert len(file_hash) == 64


def test_sha256_matches_expected_hash():
    """The helper should match hashlib's SHA-256 result."""
    with open(TEST_VIDEO, "rb") as file:
        expected_hash = hashlib.sha256(file.read()).hexdigest()

    actual_hash = get_sha256(TEST_VIDEO)

    assert actual_hash == expected_hash


def test_extract_video_metadata_valid_video():
    """A valid video should return usable metadata."""
    metadata = extract_video_metadata(TEST_VIDEO)

    assert metadata["is_corrupted"] is False
    assert metadata["width"] > 0
    assert metadata["height"] > 0
    assert metadata["fps"] > 0
    assert metadata["frame_count"] > 0
    assert metadata["duration_seconds"] > 0
    assert metadata["file_size_bytes"] > 0
    assert metadata["sha256"] is not None


def test_extract_video_metadata_missing_file():
    """A missing video should be reported as corrupted."""
    metadata = extract_video_metadata(
        "data/raw/videos/file_that_does_not_exist.mp4"
    )

    assert metadata["is_corrupted"] is True
    assert metadata["error"] is not None
    