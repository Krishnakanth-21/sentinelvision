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

    grey_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    brightness = float(grey_image.mean())
    blur_score = float(cv2.Laplacian(grey_image, cv2.CV_64F).var())

    return {
        "file_path": file_path,
        "width": width,
        "height": height,
        "channels": channels,
        "file_size_bytes": file_size_bytes,
        "sha256": file_hash,
        "brightness": brightness,
        "blur_score": blur_score,
    }


image_path = "data/raw/images/river-wild-adventure-contrast.jpg"

metadata = extract_image_metadata(image_path)

for key, value in metadata.items():
    print(f"{key}: {value}")
