import unittest

def calculate_sma(prices, period):
    """Native Python implementation of SMA for better performance."""
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period

class TestSMALogic(unittest.TestCase):
    def test_sma_calculation(self):
        prices = [10, 11, 10, 11, 10, 11, 12, 13, 14, 15]
        # Prices (len 10): 10, 11, 10, 11, 10, 11, 12, 13, 14, 15

        # SMA 6 (last 6): (10, 11, 12, 13, 14, 15)
        # Sum: 10+11+12+13+14+15 = 75. 75/6 = 12.5. Correct.

        # SMA 9 (last 9): (11, 10, 11, 10, 11, 12, 13, 14, 15)
        # Sum: 11+10+11+10+11+12+13+14+15 = 107.
        # 107 / 9 = 11.88888888888889

        self.assertEqual(calculate_sma(prices, 6), 12.5)
        self.assertAlmostEqual(calculate_sma(prices, 9), 11.88888888888889)
        self.assertIsNone(calculate_sma(prices[:5], 6))

    def test_crossover_logic(self):
        # Buffer: [..., p_prev, p_last]
        # Simulation of Rise Cross
        # SMA6_prev <= SMA9_prev AND SMA6_last > SMA9_last

        # SMA6_prev: sum([10, 10, 10, 10, 10, 10])/6 = 10
        # SMA9_prev: sum([10, 10, 10, 10, 10, 10, 10, 10, 10])/9 = 10
        # SMA6_last: sum([10, 10, 10, 10, 10, 20])/6 = 70/6 = 11.66
        # SMA9_last: sum([10, 10, 10, 10, 10, 10, 10, 10, 20])/9 = 100/9 = 11.11

        buffer = [10] * 8 + [10, 20]
        prices_last = buffer
        prices_prev = buffer[:-1]

        sma6_last = calculate_sma(prices_last, 6)
        sma9_last = calculate_sma(prices_last, 9)
        sma6_prev = calculate_sma(prices_prev, 6)
        sma9_prev = calculate_sma(prices_prev, 9)

        is_rise = (sma6_last > sma9_last) and (sma6_prev <= sma9_prev)
        self.assertTrue(is_rise)

    def test_buffer_update(self):
        candle_buffer = [10, 11, 12]
        last_open_time = 1000

        # New Tick same candle
        new_ohlc = {'open_time': 1000, 'close': 13}
        if int(new_ohlc['open_time']) == last_open_time:
            candle_buffer[-1] = new_ohlc['close']
        self.assertEqual(candle_buffer, [10, 11, 13])

        # New Candle
        new_ohlc = {'open_time': 1060, 'close': 14}
        if int(new_ohlc['open_time']) > last_open_time:
            candle_buffer.append(new_ohlc['close'])
            last_open_time = int(new_ohlc['open_time'])
        self.assertEqual(candle_buffer, [10, 11, 13, 14])

if __name__ == "__main__":
    unittest.main()
