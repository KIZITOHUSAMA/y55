# Bolt's Performance Journal ⚡

## 2026-05-30 - Initial Performance Review
**Learning:** The Deriv bot currently makes a redundant API call to `ticks_history` every time a new candle starts, despite already having a subscription to the OHLC stream. This introduces unnecessary latency (network roundtrip) at the most critical moment—the start of a new candle.
**Action:** Implement a local candle buffer that updates via the OHLC stream, eliminating the need for `ticks_history` calls during the trade loop. Also, replace Pandas SMA with a native Python implementation for faster calculation on small windows.
