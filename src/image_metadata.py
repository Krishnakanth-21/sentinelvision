import os
import hashlib
import cv2


def get_sha256(file_path):
    with open(file_path, "rb") as file:
        return hashlib.sha256(file.read()).hexdigest()


def extract_image_metadata(file_path):
    image = cv2.imread(file_path)

    if image is None:
        return None

    height, width, channels = image.shape
    file_size_bytes = os.path.getsize(file_path)
    file_hash = get_sha256(file_path)

    return {
        "file_path": file_path,
        "width": width,
        "height": height,
        "channels": channels,
        "file_size_bytes": file_size_bytes,
        "sha256": file_hash,
    }


image_path = "data/raw/images/river-wild-adventure-contrast.jpg"

metadata = extract_image_metadata(image_path)

print(metadata)
