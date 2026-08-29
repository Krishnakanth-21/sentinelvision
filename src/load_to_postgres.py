import pandas as pd
from sqlalchemy import create_engine, text


engine = create_engine(
    "postgresql+psycopg2://krishnakanthmohanraj@localhost:5432/sentinelvision"
)

metadata_path = "data/processed/image_metadata.csv"
metadata_df = pd.read_csv(metadata_path)

print(f"Total images processed: {len(metadata_df)}")

with engine.connect() as connection:
    existing_hashes = pd.read_sql(
        text("SELECT sha256 FROM image_metadata WHERE sha256 IS NOT NULL"), connection)

existing_hashes_set = set(existing_hashes["sha256"])
print(f"Existing hashes in the database: {len(existing_hashes_set)}")

new_metadata_df = metadata_df[
    ~metadata_df["sha256"].isin(existing_hashes_set)
]

print(f"New images to insert: {len(new_metadata_df)}")


if len(new_metadata_df) > 0:
    new_metadata_df.to_sql(
        "image_metadata",
        engine,
        if_exists="append",
        index=False
    )
    print("New image metadata inserted successfully.")
else:
    print("No new images to insert.")
