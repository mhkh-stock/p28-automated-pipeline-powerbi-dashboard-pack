-- t13: idempotency control — no file hash was ever loaded twice.
SELECT file_hash, COUNT(*) AS n FROM pipeline_load_log
GROUP BY file_hash HAVING COUNT(*) > 1;
