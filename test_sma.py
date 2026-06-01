def calculate_sma_native(data, period):
    if len(data) < period:
        return [None] * len(data)

    sma = [None] * (period - 1)
    current_sum = sum(data[:period])
    sma.append(current_sum / period)

    for i in range(period, len(data)):
        current_sum += data[i] - data[i - period]
        sma.append(current_sum / period)
    return sma

def test_logic():
    # Mock some data
    data = [10.0, 11.0, 10.0, 11.0, 10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 14.0, 13.0, 12.0, 11.0, 10.0, 9.0, 8.0, 7.0]

    sma_fast = 6
    sma_slow = 9

    # Replicate the logic in deriv_sma_bot.py
    price_buffer = []

    # Initial history simulation
    initial_history_count = sma_slow + 5
    price_buffer = data[:initial_history_count]

    # The rest of the data comes via stream
    for i in range(initial_history_count, len(data)):
        # Simulation of open_time > last_processed_epoch
        # Crossover logic
        if len(price_buffer) > sma_slow:
            sma6 = calculate_sma_native(price_buffer, sma_fast)
            sma9 = calculate_sma_native(price_buffer, sma_slow)

            last_idx = -1
            prev_idx = -2

            if sma9[prev_idx] is not None:
                is_rise = (sma6[last_idx] > sma9[last_idx]) and (sma6[prev_idx] <= sma9[prev_idx])
                is_fall = (sma6[last_idx] < sma9[last_idx]) and (sma6[prev_idx] >= sma9[prev_idx])

                if is_rise:
                    print(f"Candle {i}: RISE Crossover detected")
                if is_fall:
                    print(f"Candle {i}: FALL Crossover detected")

        # Update buffer with new candle
        price_buffer.append(data[i])

if __name__ == "__main__":
    test_logic()
