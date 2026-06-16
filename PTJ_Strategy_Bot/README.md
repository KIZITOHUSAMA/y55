# PTJ Hybrid Strategy Bot

This repository contains a complete automated trading system based on the principles of **Paul Tudor Jones**, implemented in both native MQL5 and Python.

## Strategy Core
1.  **Macro Filter**: 200 SMA on the M15 timeframe. Long only above, Short only below.
2.  **Phase Filter (AMD)**: Identifies the **Accumulation** phase (Asia session), looks for a **Manipulation** (fakeout), and enters on the **Distribution** (trend continuation).
3.  **Entry Trigger**: Change of Character (**CHOCH**) on the M5 timeframe following the manipulation phase.
4.  **Risk Management**:
    *   1% Risk per trade.
    *   1:5 Reward-to-Risk Ratio (RR).
    *   Partial Close (50%) at 1:3 RR.
    *   Move Stop Loss to Breakeven after partial close.
    *   Strictly no averaging down (one position per symbol at a time).

## Structure
*   `MQL5/PTJ_EA.mq5`: Native MetaTrader 5 Expert Advisor.
*   `Python/`: Python implementation using the `MetaTrader5` library.
    *   `main.py`: Main execution loop and trade management.
    *   `ptj_strategy.py`: Strategy logic (SMA, AMD, CHOCH).
    *   `mt5_engine.py`: MT5 interface wrapper.
    *   `config.py`: Centralized configuration.
