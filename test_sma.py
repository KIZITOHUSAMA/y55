def calculate_sma(data, period):
    """Calculates Simple Moving Average using native Python."""
    if len(data) < period:
        return [None] * len(data)

    sma = [None] * (period - 1)
    # Use a sliding window sum for better performance O(n)
    current_sum = sum(data[:period])
    sma.append(current_sum / period)

    for i in range(period, len(data)):
        current_sum += data[i] - data[i - period]
        sma.append(current_sum / period)
    return sma

def test_logic():
    # Mock some data
    data = [10, 11, 10, 11, 10, 11, 12, 13, 14, 15, 14, 13, 12, 11, 10, 9, 8, 7]

    sma_fast = 6
    sma_slow = 9

    sma6 = calculate_sma(data, sma_fast)
    sma9 = calculate_sma(data, sma_slow)

    print("SMA 6:", sma6)
    print("SMA 9:", sma9)

    for i in range(sma_slow, len(data)):
        last_idx = i - 1
        prev_idx = i - 2

        if sma6[last_idx] is None or sma9[last_idx] is None or \
           sma6[prev_idx] is None or sma9[prev_idx] is None:
            continue

        is_rise = (sma6[last_idx] > sma9[last_idx]) and (sma6[prev_idx] <= sma9[prev_idx])
        is_fall = (sma6[last_idx] < sma9[last_idx]) and (sma6[prev_idx] >= sma9[prev_idx])

        if is_rise:
            print(f"Index {i}: RISE Crossover detected (based on close of {last_idx})")
        if is_fall:
            print(f"Index {i}: FALL Crossover detected (based on close of {last_idx})")

if __name__ == "__main__":
    test_logic()
