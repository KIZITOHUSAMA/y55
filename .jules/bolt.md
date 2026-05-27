# Bolt's Journal - Critical Learnings

## 2025-05-15 - Consolidating API calls for reduced latency
**Learning:** In the Deriv API, a two-step `proposal` -> `buy` sequence introduces unnecessary network latency (approx. 100-300ms depending on server response time). This can be consolidated into a single `buy` call with parameters to achieve near-instant execution after a signal.
**Action:** Always prefer consolidated `buy` calls in performance-critical trading bots.
