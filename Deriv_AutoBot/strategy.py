from indicators import calculate_all_indicators
import MetaTrader5 as mt5

class MTFStrategy:
    def __init__(self, mt5_engine, config):
        self.mt5 = mt5_engine
        self.config = config

    def check_trend_h1(self, symbol):
        """
        H1 Trend Filter: Price above/below EMA 50 & 200.
        """
        df = self.mt5.get_candles(symbol, "H1", 300)
        if df is None or len(df) < self.config.EMA_SLOW:
            return None

        df = calculate_all_indicators(df, self.config)
        last_row = df.iloc[-1]

        if last_row['close'] > last_row['ema_fast'] and last_row['close'] > last_row['ema_slow']:
            return "BUY"
        elif last_row['close'] < last_row['ema_fast'] and last_row['close'] < last_row['ema_slow']:
            return "SELL"

        return "NEUTRAL"

    def check_pullback_m15(self, symbol, trend):
        """
        M15 Setup: Price pulls back towards EMA 50.
        For BUY: Close should be near or below EMA 50 but above EMA 200?
        Or simply RSI oversold/overbought.
        """
        df = self.mt5.get_candles(symbol, "M15", 100)
        if df is None: return False

        df = calculate_all_indicators(df, self.config)
        last_row = df.iloc[-1]

        if trend == "BUY":
            # Pullback: RSI < 45 or Price near EMA 50
            return last_row['rsi'] < 45
        elif trend == "SELL":
            # Pullback: RSI > 55 or Price near EMA 50
            return last_row['rsi'] > 55

        return False

    def check_trigger_m5(self, symbol, trend):
        """
        M5 Entry Trigger: Candle close in direction of trend.
        """
        df = self.mt5.get_candles(symbol, "M5", 50)
        if df is None: return False

        last_candle = df.iloc[-1]
        prev_candle = df.iloc[-2]

        if trend == "BUY":
            # Bullish close
            return last_candle['close'] > last_candle['open']
        elif trend == "SELL":
            # Bearish close
            return last_candle['close'] < last_candle['open']

        return False

    def get_signal(self, symbol):
        trend = self.check_trend_h1(symbol)
        if trend == "NEUTRAL" or trend is None:
            return None

        if self.check_pullback_m15(symbol, trend):
            if self.check_trigger_m5(symbol, trend):
                return trend

        return None
