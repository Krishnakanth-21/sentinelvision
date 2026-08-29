import pandas as pd
from sqlalchemy import create_engine

engine = create_engine(
    "postgresql+psycopg2://krishnakanthmohanraj@localhost:5432/sentinelvision"
)

metadata_path = "data/processed/image_metadata.csv"
metadata_df = pd.read_csv(metadata_path)

print(f"Total images processed: {len(metadata_df)}")

with engine.connect() as connection:
    print("Connected to the database successfully.")

metadata_df.to_sql(
    "image_metadata", engine, if_exists="replace", index=False)

print("Data loaded into the database successfully.")