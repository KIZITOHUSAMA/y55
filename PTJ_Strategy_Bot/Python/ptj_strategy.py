import pandas as pd
import numpy as np
from datetime import datetime

class PTJStrategy:
    def __init__(self, mt5_engine, config):
        self.mt5 = mt5_engine
        self.config = config
        self.asia_range = {"high": 0, "low": float('inf'), "active": False}
        self.last_day = -1

    def update_asia_range(self, symbol):
        now = datetime.now()
        if now.day != self.last_day:
            self.asia_range = {"high": 0, "low": float('inf'), "active": False}
            self.last_day = now.day

        if now.hour < self.config.ASIA_END_HOUR:
            df = self.mt5.get_candles(symbol, "M5", 20)
            if df is not None:
                self.asia_range["high"] = max(self.asia_range["high"], df['high'].max())
                self.asia_range["low"] = min(self.asia_range["low"], df['low'].min())
                self.asia_range["active"] = True

    def check_trend_m15(self, symbol):
        df = self.mt5.get_candles(symbol, "M15", 300)
        if df is None or len(df) < 200:
            return "NEUTRAL"

        # Simple 200 SMA
        sma200 = df['close'].rolling(window=200).mean().iloc[-1]
        close = df['close'].iloc[-1]

        if close > sma200:
            return "BUY"
        elif close < sma200:
            return "SELL"
        return "NEUTRAL"

    def check_choch_m5(self, symbol, trend):
        df = self.mt5.get_candles(symbol, "M5", 10)
        if df is None or len(df) < 3:
            return False

        # Current price vs previous high/low
        current_price = self.mt5.get_tick(symbol).bid if trend == "SELL" else self.mt5.get_tick(symbol).ask

        if trend == "BUY":
            # Manipulation check: did recent low go below Asia Low?
            manipulated = df['low'].iloc[-5:].min() < self.asia_range["low"]
            if manipulated:
                # CHOCH: Break of previous 5m candle high
                if current_price > df['high'].iloc[-2]:
                    return True
        elif trend == "SELL":
            # Manipulation check: did recent high go above Asia High?
            manipulated = df['high'].iloc[-5:].max() > self.asia_range["high"]
            if manipulated:
                # CHOCH: Break of previous 5m candle low
                if current_price < df['low'].iloc[-2]:
                    return True

        return False

    def get_signal(self, symbol):
        self.update_asia_range(symbol)

        now = datetime.now()
        # Only trade after Asia session and before end of NY
        if not (self.config.ASIA_END_HOUR <= now.hour < self.config.NY_END_HOUR):
            return None

        if not self.asia_range["active"]:
            return None

        trend = self.check_trend_m15(symbol)
        if trend == "NEUTRAL":
            return None

        if self.check_choch_m5(symbol, trend):
            return trend

        return None
