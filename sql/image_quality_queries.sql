-- Count images by blur quality status
SELECT
    blur_warning,
    COUNT(*) AS image_count
FROM image_metadata
GROUP BY blur_warning
ORDER BY image_count DESC;

-- Calculate percentage of images by blur quality status

SELECT
    blur_warning,
    COUNT(*) AS image_count,
    ROUND(
        COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (),
        2
    ) AS percentage
FROM image_metadata
GROUP BY blur_warning
ORDER BY image_count DESC;
