from src.image_metadata import get_sha256


def test_get_sha256_is_consistent():
    file_path = "data/raw/images/images.jpeg"

    first_hash = get_sha256(file_path)
    second_hash = get_sha256(file_path)

    assert first_hash == second_hash
    