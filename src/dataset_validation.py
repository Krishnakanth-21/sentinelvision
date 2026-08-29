import pandas as pd


image_metadata_path = "data/processed/image_metadata.csv"

image_df = pd.read_csv(image_metadata_path)

print(f"Total image records: {len(image_df)}")

corrupted_count = image_df["is_corrupted"].sum()

print(f"Corrupted images: {corrupted_count}")

blurry_count = (
    image_df["blur_warning"] != "Normal"
).sum()

print(f"Blurry images: {blurry_count}")

brightness_issue_count = (
    image_df["brightness_warning"] != "Normal"
).sum()

print(f"Images with brightness issues: {brightness_issue_count}")

duplicate_count = image_df["sha256"].duplicated().sum()

print(f"Duplicate images: {duplicate_count}")

missing_dimensions = image_df[["width", "height"]].isnull().any(axis=1).sum()

print(f"Images with missing dimensions: {missing_dimensions}")

total_issues = (
    corrupted_count
    + blurry_count
    + brightness_issue_count
    + duplicate_count
    + missing_dimensions
)

print(f"Total validation issues found: {total_issues}")
