CREATE TABLE IF NOT EXISTS image_metadata (
    id SERIAL PRIMARY KEY,
    file_path TEXT NOT NULL,
    is_corrupted BOOLEAN NOT NULL,
    error TEXT,
    width INTEGER,
    height INTEGER,
    channels INTEGER,
    file_size_bytes BIGINT,
    sha256 VARCHAR(64) UNIQUE,
    brightness DOUBLE PRECISION,
    blur_score DOUBLE PRECISION,
    brightness_warning TEXT,
    blur_warning TEXT
);

CREATE TABLE IF NOT EXISTS video_metadata (
    id SERIAL PRIMARY KEY,
    file_path TEXT NOT NULL,
    is_corrupted BOOLEAN NOT NULL,
    error TEXT,
    file_size_bytes BIGINT,
    sha256 VARCHAR(64) UNIQUE,
    width INTEGER,
    height INTEGER,
    fps DOUBLE PRECISION,
    frame_count INTEGER,
    duration_seconds DOUBLE PRECISION
);
