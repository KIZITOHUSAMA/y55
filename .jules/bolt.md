## 2026-05-30 - Optimize Deriv Bot Latency
**Learning:** For high-frequency trading bots, reducing network calls and computation overhead is critical. Native Python SMA is significantly faster than Pandas for small windows (~270x in this environment), and local caching of candle data avoids redundant API requests.
**Action:** Replace Pandas with native Python for SMA and implement local candle buffering to eliminate `ticks_history` calls on every new candle.
