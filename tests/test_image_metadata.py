import hashlib

from src.image_metadata import get_sha256, extract_image_metadata


TEST_IMAGE = "data/raw/images/images.jpeg"


def test_get_sha256_is_consistent():
    """The same file should always produce the same SHA-256 hash."""
    first_hash = get_sha256(TEST_IMAGE)
    second_hash = get_sha256(TEST_IMAGE)

    assert first_hash == second_hash


def test_sha256_has_correct_length():
    """A SHA-256 hexadecimal hash should contain 64 characters."""
    file_hash = get_sha256(TEST_IMAGE)

    assert len(file_hash) == 64


def test_sha256_matches_expected_hash():
    """The helper should produce the same hash as hashlib directly."""
    with open(TEST_IMAGE, "rb") as file:
        expected_hash = hashlib.sha256(file.read()).hexdigest()

    actual_hash = get_sha256(TEST_IMAGE)

    assert actual_hash == expected_hash


def test_extract_image_metadata_valid_image():
    """A valid image should return usable metadata."""
    metadata = extract_image_metadata(TEST_IMAGE)

    assert metadata["is_corrupted"] is False
    assert metadata["width"] > 0
    assert metadata["height"] > 0
    assert metadata["channels"] > 0
    assert metadata["file_size_bytes"] > 0
    assert metadata["sha256"] is not None


def test_extract_image_metadata_missing_file():
    """A missing image should be reported as corrupted."""
    metadata = extract_image_metadata(
        "data/raw/images/file_that_does_not_exist.jpg"
    )

    assert metadata["is_corrupted"] is True
    assert metadata["error"] is not None
    