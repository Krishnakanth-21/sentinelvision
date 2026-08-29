-- Review core video metadata
SELECT
    file_path,
    width,
    height,
    fps,
    frame_count,
    ROUND(duration_seconds::numeric, 2) AS duration_seconds
FROM video_metadata
ORDER BY duration_seconds DESC;
