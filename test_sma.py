import pandas as pd
import numpy as np

def calculate_sma(df, period):
    return df['close'].rolling(window=period).mean()

def test_logic():
    # Mock some data
    data = {
        'close': [10, 11, 10, 11, 10, 11, 12, 13, 14, 15, 14, 13, 12, 11, 10, 9, 8, 7]
    }
    df = pd.DataFrame(data)

    sma_fast = 6
    sma_slow = 9

    sma6 = calculate_sma(df, sma_fast)
    sma9 = calculate_sma(df, sma_slow)

    print("SMA 6:", sma6.tolist())
    print("SMA 9:", sma9.tolist())

    for i in range(sma_slow, len(df)):
        last_idx = i - 1
        prev_idx = i - 2

        is_rise = (sma6.iloc[last_idx] > sma9.iloc[last_idx]) and (sma6.iloc[prev_idx] <= sma9.iloc[prev_idx])
        is_fall = (sma6.iloc[last_idx] < sma9.iloc[last_idx]) and (sma6.iloc[prev_idx] >= sma9.iloc[prev_idx])

        if is_rise:
            print(f"Index {i}: RISE Crossover detected (based on close of {last_idx})")
        if is_fall:
            print(f"Index {i}: FALL Crossover detected (based on close of {last_idx})")

if __name__ == "__main__":
    test_logic()
