def calculate_sma(prices, period):
    """Native Python SMA implementation."""
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period

def test_logic():
    # Mock some data
    prices = [10, 11, 10, 11, 10, 11, 12, 13, 14, 15, 14, 13, 12, 11, 10, 9, 8, 7]

    sma_fast = 6
    sma_slow = 9

    print(f"Prices: {prices}")

    for i in range(sma_slow, len(prices)):
        # Simulate new candle start at index i
        # The logic in the bot uses closed prices up to i-1
        current_prices = prices[:i]

        # SMA at last closed candle
        sma6_last = calculate_sma(current_prices, sma_fast)
        sma9_last = calculate_sma(current_prices, sma_slow)

        # SMA at previous closed candle
        sma6_prev = calculate_sma(current_prices[:-1], sma_fast)
        sma9_prev = calculate_sma(current_prices[:-1], sma_slow)

        if all(v is not None for v in [sma6_last, sma9_last, sma6_prev, sma9_prev]):
            is_rise = (sma6_last > sma9_last) and (sma6_prev <= sma9_prev)
            is_fall = (sma6_last < sma9_last) and (sma6_prev >= sma9_prev)

            if is_rise:
                print(f"Index {i}: RISE Crossover detected")
            if is_fall:
                print(f"Index {i}: FALL Crossover detected")

if __name__ == "__main__":
    test_logic()
