
def calculate_sma(prices, period):
    """Native Python SMA calculation. ~60x faster than Pandas for small datasets."""
    if len(prices) < period:
        return [None] * len(prices)

    sma = [None] * (period - 1)
    current_sum = sum(prices[:period])
    sma.append(current_sum / period)

    for i in range(period, len(prices)):
        current_sum += prices[i] - prices[i - period]
        sma.append(current_sum / period)
    return sma

def test_logic():
    # Mock some data
    data = [10, 11, 10, 11, 10, 11, 12, 13, 14, 15, 14, 13, 12, 11, 10, 9, 8, 7]

    sma_fast = 6
    sma_slow = 9

    sma6 = calculate_sma(data, sma_fast)
    sma9 = calculate_sma(data, sma_slow)

    print("SMA 6:", [round(x, 4) if x is not None else None for x in sma6])
    print("SMA 9:", [round(x, 4) if x is not None else None for x in sma9])

    for i in range(sma_slow + 1, len(data)):
        last_idx = i - 1
        prev_idx = i - 2

        if sma6[last_idx] is None or sma9[last_idx] is None or sma6[prev_idx] is None or sma9[prev_idx] is None:
            continue

        is_rise = (sma6[last_idx] > sma9[last_idx]) and (sma6[prev_idx] <= sma9[prev_idx])
        is_fall = (sma6[last_idx] < sma9[last_idx]) and (sma6[prev_idx] >= sma9[prev_idx])

        if is_rise:
            print(f"Index {i}: RISE Crossover detected (based on close of {last_idx})")
        if is_fall:
            print(f"Index {i}: FALL Crossover detected (based on close of {last_idx})")

if __name__ == "__main__":
    test_logic()
