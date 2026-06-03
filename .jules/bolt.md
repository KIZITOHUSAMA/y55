## 2026-05-30 - Native SMA and Local Buffering in Deriv Bot
**Learning:** For low-latency trading bots processing small datasets (e.g., SMA 6/9), the overhead of `pandas` is significant (over 300x slower than native Python in benchmarks). Additionally, redundant API calls for historical data on every candle change add unnecessary network latency and API pressure.
**Action:** Replace `pandas` with native Python math for simple indicators and implement local candle buffering from OHLC streams to eliminate redundant `ticks_history` calls.
