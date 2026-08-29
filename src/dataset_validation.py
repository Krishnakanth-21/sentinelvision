import pandas as pd


# --------------------------------------------------
# IMAGE DATASET VALIDATION
# --------------------------------------------------

image_metadata_path = "data/processed/image_metadata.csv"
image_df = pd.read_csv(image_metadata_path)

print("\nIMAGE DATASET VALIDATION")
print("------------------------")

print(f"Total image records: {len(image_df)}")


# Check corrupted images
corrupted_count = image_df["is_corrupted"].sum()

print(f"Corrupted images: {corrupted_count}")


# Check blurry images
blurry_count = (
    image_df["blur_warning"] != "Normal"
).sum()

print(f"Blurry images: {blurry_count}")


# Check brightness issues
brightness_issue_count = (
    image_df["brightness_warning"] != "Normal"
).sum()

print(f"Images with brightness issues: {brightness_issue_count}")


# Check duplicate images using SHA-256 hash
duplicate_count = image_df["sha256"].duplicated().sum()

print(f"Duplicate images: {duplicate_count}")


# Check missing image dimensions
missing_dimensions = (
    image_df[["width", "height"]]
    .isnull()
    .any(axis=1)
    .sum()
)

print(f"Images with missing dimensions: {missing_dimensions}")


# Check invalid image dimensions
invalid_dimensions = (
    (image_df["width"] <= 0)
    | (image_df["height"] <= 0)
).sum()

print(f"Images with invalid dimensions: {invalid_dimensions}")


# Calculate total image validation issues
total_image_issues = (
    corrupted_count
    + blurry_count
    + brightness_issue_count
    + duplicate_count
    + missing_dimensions
    + invalid_dimensions
)

print(f"Total image validation issues found: {total_image_issues}")


# --------------------------------------------------
# VIDEO DATASET VALIDATION
# --------------------------------------------------

video_metadata_path = "data/processed/video_metadata.csv"
video_df = pd.read_csv(video_metadata_path)

print("\nVIDEO DATASET VALIDATION")
print("------------------------")

print(f"Total video records: {len(video_df)}")


# Check corrupted videos
corrupted_video_count = video_df["is_corrupted"].sum()

print(f"Corrupted videos: {corrupted_video_count}")


# Check duplicate videos using SHA-256 hash
duplicate_video_count = video_df["sha256"].duplicated().sum()

print(f"Duplicate videos: {duplicate_video_count}")


# Check missing video dimensions
missing_video_dimensions = (
    video_df[["width", "height"]]
    .isnull()
    .any(axis=1)
    .sum()
)

print(
    f"Videos with missing dimensions: "
    f"{missing_video_dimensions}"
)


# Check invalid video dimensions
invalid_video_dimensions = (
    (video_df["width"] <= 0)
    | (video_df["height"] <= 0)
).sum()

print(
    f"Videos with invalid dimensions: "
    f"{invalid_video_dimensions}"
)


# Check invalid FPS
invalid_fps_count = (
    video_df["fps"].isnull()
    | (video_df["fps"] <= 0)
).sum()

print(f"Videos with invalid FPS: {invalid_fps_count}")


# Check invalid frame counts
invalid_frame_count = (
    video_df["frame_count"].isnull()
    | (video_df["frame_count"] <= 0)
).sum()

print(f"Videos with invalid frame count: {invalid_frame_count}")


# Check invalid duration
invalid_duration_count = (
    video_df["duration_seconds"].isnull()
    | (video_df["duration_seconds"] <= 0)
).sum()

print(f"Videos with invalid duration: {invalid_duration_count}")


# Calculate total video validation issues
total_video_issues = (
    corrupted_video_count
    + duplicate_video_count
    + missing_video_dimensions
    + invalid_video_dimensions
    + invalid_fps_count
    + invalid_frame_count
    + invalid_duration_count
)

print(f"Total video validation issues found: {total_video_issues}")


# --------------------------------------------------
# IMAGE LABEL VALIDATION
# --------------------------------------------------

image_labels_path = "data/labels/image_labels.csv"
labels_df = pd.read_csv(image_labels_path)

print("\nIMAGE LABEL VALIDATION")
print("----------------------")

print(f"Total labelled image records: {len(labels_df)}")


# Check unknown labels
unknown_label_count = (
    labels_df["label"] == "unknown"
).sum()

print(f"Images with unknown labels: {unknown_label_count}")


# Check missing labels
missing_label_count = labels_df["label"].isnull().sum()

print(f"Images with missing labels: {missing_label_count}")


# Check duplicate label records
duplicate_label_records = (
    labels_df["file_path"]
    .duplicated()
    .sum()
)

print(f"Duplicate label records: {duplicate_label_records}")


# Check whether every image has a label record
unlabelled_images = (
    ~image_df["file_path"].isin(labels_df["file_path"])
).sum()

print(f"Images without label records: {unlabelled_images}")


# Display class distribution
print("\nLabel distribution:")

label_distribution = labels_df["label"].value_counts()

print(label_distribution.to_string())


# Calculate total label validation issues
total_label_issues = (
    unknown_label_count
    + missing_label_count
    + duplicate_label_records
    + unlabelled_images
)

print(f"\nTotal label validation issues found: {total_label_issues}")


# --------------------------------------------------
# OVERALL DATASET SUMMARY
# --------------------------------------------------

total_dataset_issues = (
    total_image_issues
    + total_video_issues
    + total_label_issues
)

print("\nOVERALL VALIDATION SUMMARY")
print("--------------------------")

print(f"Total images: {len(image_df)}")
print(f"Total videos: {len(video_df)}")
print(f"Total validation issues: {total_dataset_issues}")

if total_dataset_issues == 0:
    print("Dataset validation status: PASS")
else:
    print("Dataset validation status: ISSUES FOUND")
    