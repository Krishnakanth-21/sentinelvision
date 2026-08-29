import cv2
import os
import hashlib
import csv


def get_sha256(file_path):
    with open(file_path, "rb") as file:
        return hashlib.sha256(file.read()).hexdigest()


def extract_video_metadata(file_path):
    video = cv2.VideoCapture(file_path)

    if not video.isOpened():
        return {
            "file_path": file_path,
            "is_corrupted": True,
            "error": "Failed to open video."
        }

    # Try to read the first frame to confirm the video content is readable.
    success, frame = video.read()

    if not success:
        video.release()
        return {
            "file_path": file_path,
            "is_corrupted": True,
            "error": "Failed to read video frame."
        }

    width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = float(video.get(cv2.CAP_PROP_FPS))
    frame_count = int(video.get(cv2.CAP_PROP_FRAME_COUNT))

    if fps > 0:
        duration_seconds = frame_count / fps
    else:
        duration_seconds = 0

    # Close the video only after we have finished reading its properties.
    video.release()

    file_size_bytes = os.path.getsize(file_path)
    file_hash = get_sha256(file_path)

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


video_folder = "data/raw/videos"
all_metadata = []

for filename in os.listdir(video_folder):
    file_path = os.path.join(video_folder, filename)

    metadata = extract_video_metadata(file_path)
    all_metadata.append(metadata)

    print(f"\nMetadata for {filename}:")

    for key, value in metadata.items():
        print(f"{key}: {value}")

print(f"\nTotal videos processed: {len(all_metadata)}")


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

with open("data/processed/video_metadata.csv", "w", newline="") as csvfile:
    writer = csv.DictWriter(
        csvfile,
        fieldnames=fieldnames,
        extrasaction="ignore"
    )

    writer.writeheader()
    writer.writerows(all_metadata)

print("Video metadata saved to data/processed/video_metadata.csv")
