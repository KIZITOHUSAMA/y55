## 2024-05-28 - [MQL5 Multi-Symbol Optimization]
**Learning:** Calling price data (`iHigh`, `iLow`) and indicator data (`CopyBuffer` via `GetATR`) for every symbol every tick is a significant CPU bottleneck in multi-symbol Expert Advisors.
**Action:** Use a `SymbolData` struct to cache these values and only update them when a new candle for the respective timeframe starts (monitored via `iTime`).

## 2024-05-28 - [Python Trading Bot Latency]
**Learning:** Pandas introduces unnecessary overhead for simple streaming calculations like SMA. Native Python is ~12x faster for small windows.
**Action:** Replace Pandas with native Python for time-critical trading logic.
