import os
import hashlib
import cv2
import csv


def get_sha256(file_path):
    with open(file_path, "rb") as file:
        return hashlib.sha256(file.read()).hexdigest()


def extract_image_metadata(file_path):
    image = cv2.imread(file_path)

    if image is None:
        return {
            "file_path": file_path,
            "is_corrupted": True,
            "error": "Failed to read image. The file may be corrupted or not an image.",
        }

    height, width, channels = image.shape
    file_size_bytes = os.path.getsize(file_path)
    file_hash = get_sha256(file_path)

    grey_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    brightness = float(grey_image.mean())
    blur_score = float(cv2.Laplacian(grey_image, cv2.CV_64F).var())

    return {
        "file_path": file_path,
        "is_corrupted": False,
        "width": width,
        "height": height,
        "channels": channels,
        "file_size_bytes": file_size_bytes,
        "sha256": file_hash,
        "brightness": brightness,
        "blur_score": blur_score,
    }




image_folder = "data/raw/images"
all_metadata = []

for filename in os.listdir(image_folder):
    file_path = os.path.join(image_folder, filename)
    metadata = extract_image_metadata(file_path)
    all_metadata.append(metadata)
    print(f"\nMetadata for {filename}:")
    for key, value in metadata.items():
        print(f"  {key}: {value}")

print(f"\nTotal images processed: {len(all_metadata)}")

if all_metadata:
    fieldnames = all_metadata[0].keys()
    with open("data/processed/image_metadata.csv", "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_metadata)
