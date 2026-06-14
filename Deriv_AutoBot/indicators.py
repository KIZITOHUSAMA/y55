import numpy as np

def ema(data, period):
    """
    High-performance Exponential Moving Average using NumPy.
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

def rsi(data, period=14):
    """
    High-performance Relative Strength Index using NumPy.
    """
    if len(data) <= period:
        return np.array([np.nan] * len(data))

    deltas = np.diff(data)
    seed = deltas[:period]
    up = seed[seed >= 0].sum() / period
    down = -seed[seed < 0].sum() / period
    rs = up / down if down != 0 else 100
    rsi_values = np.zeros(len(data))
    rsi_values[:period] = np.nan
    rsi_values[period] = 100. - 100. / (1. + rs)

    for i in range(period + 1, len(data)):
        delta = deltas[i - 1]
        if delta > 0:
            up_val = delta
            down_val = 0.
        else:
            up_val = 0.
            down_val = -delta

        up = (up * (period - 1) + up_val) / period
        down = (down * (period - 1) + down_val) / period

        rs = up / down if down != 0 else 100
        rsi_values[i] = 100. - 100. / (1. + rs)

    return rsi_values

def atr(high, low, close, period=14):
    """
    High-performance Average True Range using NumPy.
    """
    if len(close) <= period:
        return np.array([np.nan] * len(close))

    tr1 = high[1:] - low[1:]
    tr2 = np.abs(high[1:] - close[:-1])
    tr3 = np.abs(low[1:] - close[:-1])

    tr = np.maximum(tr1, np.maximum(tr2, tr3))

    atr_values = np.zeros(len(close))
    atr_values[:period] = np.nan
    atr_values[period] = np.mean(tr[:period])

    for i in range(period + 1, len(close)):
        atr_values[i] = (atr_values[i-1] * (period - 1) + tr[i-1]) / period

    return atr_values

def calculate_all_indicators(df, config):
    """
    Appends all required indicators to the dataframe.
    """
    close = df['close'].values
    high = df['high'].values
    low = df['low'].values

    df['ema_fast'] = ema(close, config.EMA_FAST)
    df['ema_slow'] = ema(close, config.EMA_SLOW)
    df['rsi'] = rsi(close, config.RSI_PERIOD)
    df['atr'] = atr(high, low, close, config.ATR_PERIOD)

    return df
