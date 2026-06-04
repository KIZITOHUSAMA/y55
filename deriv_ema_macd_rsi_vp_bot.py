import asyncio
import os
import math
from deriv_api import deriv_api

# --- Configuration ---
APP_ID = 1089 # Default for testing
TOKEN = os.getenv('DERIV_TOKEN')
SYMBOL = 'R_100' # Example symbol
TIMEFRAME = '5m'
EMA_FAST = 5
EMA_SLOW = 9
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
RSI_PERIOD = 14
VP_LOOKBACK = 60
KELLY_P = 0.5
KELLY_B = 5.0
KELLY_FRACTION = 0.01
MAX_ORDERS = 20
TRAILING_STOP_PIPS = 10
PARTIAL_RR = 2.0
FULL_RR = 5.0
USE_MACD = False
USE_RSI = False

# --- Indicator Helpers (Native Python for Speed) ---

def calculate_ema(data, period):
    if len(data) < period:
        return None
    alpha = 2 / (period + 1)
    ema = sum(data[:period]) / period
    for i in range(period, len(data)):
        ema = (data[i] - ema) * alpha + ema
    return ema

def calculate_macd(data, fast, slow, signal):
    if len(data) < slow + signal:
        return None, None

    emas_fast = []
    emas_slow = []

    # Calculate EMA arrays
    f_alpha = 2 / (fast + 1)
    s_alpha = 2 / (slow + 1)

    curr_f = sum(data[:fast]) / fast
    curr_s = sum(data[:slow]) / slow

    macd_line_history = []

    for i in range(len(data)):
        if i >= fast:
            curr_f = (data[i] - curr_f) * f_alpha + curr_f
        if i >= slow:
            curr_s = (data[i] - curr_s) * s_alpha + curr_s

        if i >= slow:
            macd_line_history.append(curr_f - curr_s)

    if len(macd_line_history) < signal:
        return None, None

    sig_alpha = 2 / (signal + 1)
    curr_sig = sum(macd_line_history[:signal]) / signal
    for i in range(signal, len(macd_line_history)):
        curr_sig = (macd_line_history[i] - curr_sig) * sig_alpha + curr_sig

    return macd_line_history[-1], curr_sig

def calculate_rsi(data, period):
    if len(data) < period + 1:
        return None

    gains = []
    losses = []
    for i in range(1, len(data)):
        diff = data[i] - data[i-1]
        gains.append(max(0, diff))
        losses.append(max(0, -diff))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    if avg_loss == 0: return 100

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0: return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# --- Volume Profile Helper ---

def calculate_volume_profile(candles, bins=50):
    highs = [c['high'] for c in candles]
    lows = [c['low'] for c in candles]
    closes = [c['close'] for c in candles]
    vols = [c['volume'] for c in candles]

    top = max(highs)
    bottom = min(lows)
    v_range = top - bottom
    if v_range == 0: return None, None, None

    bin_size = v_range / bins
    profile = [0.0] * bins
    total_vol = sum(vols)

    for i in range(len(candles)):
        bin_idx = int((closes[i] - bottom) / bin_size)
        if bin_idx >= bins: bin_idx = bins - 1
        if bin_idx < 0: bin_idx = 0
        profile[bin_idx] += vols[i]

    max_vol = max(profile)
    poc_idx = profile.index(max_vol)
    poc = bottom + (poc_idx * bin_size) + (bin_size / 2)

    # Value Area 70%
    target_vol = total_vol * 0.7
    curr_vol = max_vol
    up = poc_idx
    down = poc_idx

    while curr_vol < target_vol and (up < bins - 1 or down > 0):
        up_v = profile[up+1] if up < bins - 1 else 0
        dn_v = profile[down-1] if down > 0 else 0
        if up_v >= dn_v and up < bins - 1:
            up += 1
            curr_vol += up_v
        elif down > 0:
            down -= 1
            curr_vol += dn_v
        else:
            break

    vah = bottom + (up * bin_size) + bin_size
    val = bottom + (down * bin_size)
    return poc, vah, val

# --- Trading Logic ---

class DerivBot:
    def __init__(self):
        self.api = None
        self.history = []
        self.active_positions = {} # ticket -> info

    async def connect(self):
        self.api = deriv_api.DerivAPI(app_id=APP_ID)
        await self.api.authorize(TOKEN)
        print("Authorized successfully")

    async def start(self):
        await self.connect()
        # Initial history
        candles = await self.api.ticks_history({'ticks_history': SYMBOL, 'end': 'latest', 'count': VP_LOOKBACK + 50, 'style': 'candles', 'granularity': 300})
        self.history = candles['candles']

        # Subscribe to new candles
        await self.api.subscribe({'ohlc': SYMBOL, 'granularity': 300}, self.on_candle)

    async def on_candle(self, msg):
        ohlc = msg['ohlc']
        # If it's a new candle
        if len(self.history) == 0 or ohlc['open_time'] != self.history[-1]['epoch']:
            # Previous candle is closed
            new_candle = {
                'epoch': ohlc['open_time'],
                'open': ohlc['open'],
                'high': ohlc['high'],
                'low': ohlc['low'],
                'close': ohlc['close'],
                'volume': 1 # Deriv OHLC stream volume placeholder
            }
            self.history.append(new_candle)
            if len(self.history) > VP_LOOKBACK + 100:
                self.history.pop(0)

            await self.check_signals()

        await self.manage_positions(ohlc['close'])

    async def check_signals(self):
        if len(self.history) < VP_LOOKBACK: return

        closes = [c['close'] for c in self.history]

        ema_f_prev = calculate_ema(closes[:-2], EMA_FAST)
        ema_s_prev = calculate_ema(closes[:-2], EMA_SLOW)
        ema_f_curr = calculate_ema(closes[:-1], EMA_FAST)
        ema_s_curr = calculate_ema(closes[:-1], EMA_SLOW)

        macd_l, macd_s = calculate_macd(closes[:-1], MACD_FAST, MACD_SLOW, MACD_SIGNAL)
        rsi = calculate_rsi(closes[:-1], RSI_PERIOD)

        ema_long = (ema_f_prev is not None and ema_s_prev is not None and ema_f_prev <= ema_s_prev) and (ema_f_curr > ema_s_curr)
        macd_long = not USE_MACD or (macd_l is not None and macd_l > macd_s)
        rsi_long = not USE_RSI or (rsi is not None and rsi > 50)
        long_signal = ema_long and macd_long and rsi_long

        ema_short = (ema_f_prev is not None and ema_s_prev is not None and ema_f_prev >= ema_s_prev) and (ema_f_curr < ema_s_curr)
        macd_short = not USE_MACD or (macd_l is not None and macd_l < macd_s)
        rsi_short = not USE_RSI or (rsi is not None and rsi < 50)
        short_signal = ema_short and macd_short and rsi_short

        if long_signal or short_signal:
            poc, vah, val = calculate_volume_profile(self.history[-VP_LOOKBACK:])
            if poc is None: return

            # Kelly Risk
            kelly = KELLY_P - (1 - KELLY_P) / KELLY_B
            risk_pct = max(0.01, kelly * KELLY_FRACTION)

            direction = 'CALL' if long_signal else 'PUT'
            print(f"Signal: {direction} detected. Crossover at {closes[-1]}")

            # Market Execution (50% Risk)
            await self.buy_contract(direction, risk_pct * 0.5, closes[-1], val if long_signal else vah)

            # Limit/Pending Execution (50% Risk)
            print(f"Placing pending {direction} at POC: {poc}")
            await self.buy_contract(direction, risk_pct * 0.5, poc, val if long_signal else vah)

    async def manage_positions(self, current_price):
        for ticket, pos in list(self.active_positions.items()):
            # Logic for Partial TP (1:2 RR) and Full Exit (1:5 RR or Reversal)
            # This requires tracking the entry price and SL/TP for each contract.
            # Since Deriv contracts have fixed barriers, this would be implemented
            # by selling the contract or waiting for it to expire.
            pass

    async def buy_contract(self, direction, amount, poc, sl):
        # Dummy implementation for placing a contract with barriers
        # In Deriv, you'd use the 'proposal' and 'buy' calls.
        print(f"Placing {direction} order with stake {amount} at {poc}, SL: {sl}")

async def main():
    bot = DerivBot()
    await bot.start()
    while True:
        await asyncio.sleep(1)

if __name__ == '__main__':
    asyncio.run(main())
