## 2026-06-04 - Native SMA vs Pandas for micro-datasets
**Learning:** For small datasets (e.g., < 20 elements), the overhead of creating a Pandas DataFrame and calling its rolling methods is significantly higher than a native Python implementation. Benchmarks showed a ~100x performance improvement for SMA calculations on 14 data points.
**Action:** Replace Pandas with native Python logic for simple technical indicators when dealing with small buffers in high-frequency trading loops.
