import numpy as np

def ema(data, period):
    """
    Native NumPy implementation of Exponential Moving Average.
    """
    if len(data) < period:
        return np.array([np.nan] * len(data))

    alpha = 2 / (period + 1)
    ema_values = np.zeros(len(data))
    ema_values[period-1] = np.mean(data[:period])

    for i in range(period, len(data)):
        ema_values[i] = data[i] * alpha + ema_values[i-1] * (1 - alpha)

    ema_values[:period-1] = np.nan
    return ema_values

def macd(data, fast=5, slow=35, signal=5):
    """
    MACD calculation using EMA.
    """
    ema_fast = ema(data, fast)
    ema_slow = ema(data, slow)
    macd_line = ema_fast - ema_slow

    # Filter nan for signal calculation
    valid_macd = macd_line[~np.isnan(macd_line)]
    if len(valid_macd) < signal:
        signal_line = np.array([np.nan] * len(macd_line))
    else:
        sig = ema(valid_macd, signal)
        signal_line = np.append(np.array([np.nan] * (len(macd_line) - len(sig))), sig)

    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def get_signal(data, config):
    """
    Analyzes data for EMA 6/9 Crossover + MACD Confirmation.
    """
    if len(data) < config.MACD_SLOW + config.MACD_SIGNAL:
        return None

    prices = np.array(data)
    ema6 = ema(prices, config.EMA_FAST)
    ema9 = ema(prices, config.EMA_SLOW)
    _, _, hist = macd(prices, config.MACD_FAST, config.MACD_SLOW, config.MACD_SIGNAL)

    # Current and previous values for crossover check
    e6_curr, e6_prev = ema6[-1], ema6[-2]
    e9_curr, e9_prev = ema9[-1], ema9[-2]
    h_curr = hist[-1]

    # Bullish Crossover: EMA6 crosses above EMA9 + MACD Hist > 0
    if e6_prev <= e9_prev and e6_curr > e9_curr and h_curr > 0:
        return "CALL"

    # Bearish Crossover: EMA6 crosses below EMA9 + MACD Hist < 0
    if e6_prev >= e9_prev and e6_curr < e9_curr and h_curr < 0:
        return "PUT"

    return None
