# Bolt's Journal - Critical Learnings

## 2026-05-24 - [Deriv Bot Performance Standards]
**Learning:** For Python-based Deriv bots, Pandas is a major performance bottleneck for simple indicator calculations like SMA. Native Python is ~12x faster. Additionally, redundant `api.ticks_history` calls on every candle close add unnecessary network latency.
**Action:** Replace Pandas with native math and implement local candle caching via the subscription stream to eliminate redundant API calls.

## 2026-05-24 - [SMA Optimization]
**Learning:** Re-calculating the entire historical SMA list on every tick is inefficient.
**Action:** Calculate only the current and previous SMA values (the last two indices) to minimize CPU cycles while maintaining crossover logic.

## 2026-05-24 - [Environment Hygiene]
**Learning:** Running tests generates `__pycache__` which should not be committed.
**Action:** Always check `git status` and remove `__pycache__` before submission.
