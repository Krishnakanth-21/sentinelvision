import pandas as pd
import matplotlib.pyplot as plt
import os

metadata_path = "data/processed/image_metadata.csv"

# Load the metadata CSV file
metadata_df = pd.read_csv(metadata_path)


print(metadata_df.head())
print("\nDataset shape:")
print(metadata_df.shape)
print("\nNumerical summary:")
print(metadata_df[["width", "height", "file_size_bytes", "brightness", "blur_score"]].describe())

print("\nBrightness quality:")
print(metadata_df["brightness_warning"].value_counts())

image_names = metadata_df["file_path"].apply(lambda x: os.path.basename(x))

print("\nBlur quality:")
print(metadata_df["blur_warning"].value_counts())

plt.hist(metadata_df["brightness"], bins=5)

plt.title("Image Brightness Distribution")
plt.xlabel("Brightness")
plt.ylabel("Number of Images")

plt.savefig("reports/figures/brightness_distribution.png")
plt.show()

plt.bar(image_names, metadata_df["blur_score"])

plt.title("Image Blur Scores")
plt.xlabel("Image")
plt.ylabel("Laplacian Variance")

plt.axhline(y=100, linestyle="--", label="Blur threshold")
plt.legend()

plt.xticks(rotation=45, ha="right")
plt.tight_layout()

plt.savefig("reports/figures/blur_scores.png")
plt.show()
