import os
import cv2

image_path = "data/raw/images/river-wild-adventure-contrast.jpg"

image = cv2.imread(image_path)

if image is None:
    print("Failed to load image")
else:
    print("Image loaded successfully")

    height, width, channels = image.shape
    file_size_bytes = os.path.getsize(image_path)

    print("Width:", width)
    print("Height:", height)
    print("Channels:", channels)
    print("File size (bytes):", file_size_bytes)
    