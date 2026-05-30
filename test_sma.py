def calculate_sma(prices, period):
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period

def test_logic():
    # Mock some data
    data = [10, 11, 10, 11, 10, 11, 12, 13, 14, 15, 14, 13, 12, 11, 10, 9, 8, 7]

    sma_fast = 6
    sma_slow = 9
    prices = []

    print("Testing Fixed SMA Crossover Logic...")

    for i, close_price in enumerate(data):
        # In the bot, i would be open_time (epoch), but here it's just index.
        # We append the 'close_price' when we detect a new candle.
        prices.append(close_price)
        if len(prices) > 50:
            prices.pop(0)

        if len(prices) > sma_slow:
            sma6_curr = calculate_sma(prices, sma_fast)
            sma9_curr = calculate_sma(prices, sma_slow)

            sma6_prev = calculate_sma(prices[:-1], sma_fast)
            sma9_prev = calculate_sma(prices[:-1], sma_slow)

            if sma6_curr is not None and sma9_curr is not None and sma6_prev is not None and sma9_prev is not None:
                is_rise = (sma6_curr > sma9_curr) and (sma6_prev <= sma9_prev)
                is_fall = (sma6_curr < sma9_curr) and (sma6_prev >= sma9_prev)

                if is_rise:
                    print(f"Index {i}: RISE Crossover detected (based on candle closing at index {i})")
                if is_fall:
                    print(f"Index {i}: FALL Crossover detected (based on candle closing at index {i})")

if __name__ == "__main__":
    test_logic()
