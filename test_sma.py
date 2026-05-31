import asyncio

def get_sma(prices, period):
    """Calculates SMA for the last 2 periods only to maximize performance."""
    if len(prices) < period + 1:
        return None, None

    # Current SMA (including the active candle)
    curr_sma = sum(prices[-period:]) / period
    # Previous SMA (last closed candle)
    prev_sma = sum(prices[-period-1:-1]) / period

    return curr_sma, prev_sma

async def test_buffer_logic():
    print("Testing buffer and crossover logic simulation...")
    SMA_FAST = 6
    SMA_SLOW = 9

    # Mock stream: Initial history + OHLC updates
    initial_history = [{'epoch': i*60, 'close': 10 + (i % 2)} for i in range(10)]
    stream_data = [
        {'candles': initial_history},
        {'ohlc': {'open_time': 600, 'close': 12}}, # Update last (newly added by ohlc logic)
        {'ohlc': {'open_time': 660, 'close': 13}}, # New candle
        {'ohlc': {'open_time': 660, 'close': 14}}, # Update last
        {'ohlc': {'open_time': 720, 'close': 15}}, # New candle
        {'ohlc': {'open_time': 780, 'close': 14}}, # New candle
    ]

    candle_history = []
    current_candle_epoch = 0
    last_processed_epoch = 0
    signals = []

    for candle_data in stream_data:
        if 'candles' in candle_data:
            candle_history = [float(c['close']) for c in candle_data['candles']]
            current_candle_epoch = candle_data['candles'][-1]['epoch']
            if last_processed_epoch == 0:
                last_processed_epoch = current_candle_epoch

        if 'ohlc' in candle_data:
            ohlc = candle_data['ohlc']
            open_time = ohlc['open_time']
            close_price = float(ohlc['close'])

            if open_time > current_candle_epoch:
                candle_history.append(close_price)
                current_candle_epoch = open_time
            else:
                if candle_history:
                    candle_history[-1] = close_price
                else:
                    candle_history.append(close_price)
                    current_candle_epoch = open_time

            if open_time > last_processed_epoch:
                if len(candle_history) >= SMA_SLOW + 1:
                    sma6_curr, sma6_prev = get_sma(candle_history, SMA_FAST)
                    sma9_curr, sma9_prev = get_sma(candle_history, SMA_SLOW)

                    if sma9_prev is not None:
                        is_rise = (sma6_curr > sma9_curr) and (sma6_prev <= sma9_prev)
                        is_fall = (sma6_curr < sma9_curr) and (sma6_prev >= sma9_prev)
                        if is_rise: signals.append(("CALL", open_time))
                        if is_fall: signals.append(("PUT", open_time))
                last_processed_epoch = open_time

    print("Signals detected:", signals)
    assert len(candle_history) > 10
    print("Buffer logic test passed!")

def test_math():
    print("Testing SMA math...")
    data = [10, 11, 10, 11, 10, 11, 12, 13, 14, 15, 14, 13, 12, 11, 10, 9, 8, 7]
    # At index 8 (len 9), data is [10, 11, 10, 11, 10, 11, 12, 13, 14]
    # SMA 9: sum/9 = (10+11+10+11+10+11+12+13+14)/9 = 102/9 = 11.333
    curr, prev = get_sma(data[:9], 9)
    # get_sma(data[:9], 9) needs len 10.

    curr, prev = get_sma(data[:10], 9)
    # data[:10] = [10, 11, 10, 11, 10, 11, 12, 13, 14, 15]
    # curr = sum([11, 10, 11, 10, 11, 12, 13, 14, 15])/9 = 107/9 = 11.888
    # prev = sum([10, 11, 10, 11, 10, 11, 12, 13, 14])/9 = 102/9 = 11.333

    assert round(curr, 4) == round(107/9, 4)
    assert round(prev, 4) == round(102/9, 4)
    print("Math test passed!")

if __name__ == "__main__":
    test_math()
    asyncio.run(test_buffer_logic())
