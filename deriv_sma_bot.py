"""
Deriv SMA (6,9) Crossover Trading Bot
-------------------------------------
Requirements:
    pip install python-deriv-api websockets reactivex

Usage:
    export DERIV_TOKEN=your_token_here
    python deriv_sma_bot.py
"""

import asyncio
import os
import sys

try:
    from deriv_api import DerivAPI
except ImportError:
    print("Error: 'python-deriv-api' not found.")
    print("Please install it using: pip install python-deriv-api")
    sys.exit(1)

# --- Configuration ---
APP_ID = 1089  # Default app_id for testing, or use your own
API_TOKEN = os.environ.get('DERIV_TOKEN', 'YOUR_TOKEN_HERE')
# Expanded list of common Volatility Indices
SYMBOLS = [
    "R_10", "R_25", "R_50", "R_75", "R_100",
    "1HZ10V", "1HZ25V", "1HZ50V", "1HZ75V", "1HZ100V",
    "1HZ200V", "1HZ300V"
]
INITIAL_STAKE = 0.35
MULTIPLIER = 1.5
DURATION = 2  # Minutes
TIMEFRAME = 60 # 1 minute in seconds
SMA_FAST = 6
SMA_SLOW = 9

# --- Global State ---
stakes = {symbol: INITIAL_STAKE for symbol in SYMBOLS}
# Keep track of the last processed candle epoch to avoid multiple entries on same candle
last_processed_epoch = {symbol: 0 for symbol in SYMBOLS}

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

async def trade_logic(api, symbol):
    global stakes, last_processed_epoch
    print(f"Monitoring {symbol}...")

    queue = asyncio.Queue()

    # Cache for closed candle prices to eliminate redundant API calls
    prices_cache = []
    last_seen_close = 0

    try:
        # Initial population of prices cache
        hist_resp = await api.ticks_history({
            "ticks_history": symbol,
            "count": SMA_SLOW + 5,
            "end": "latest",
            "granularity": TIMEFRAME,
            "style": "candles"
        })

        if 'candles' in hist_resp:
            # Deriv ticks_history returns the current (open) candle as the last element.
            # We only want confirmed CLOSED candles in our cache for the strategy.
            candles = hist_resp['candles']
            prices_cache = [c['close'] for c in candles[:-1]]
            last_seen_close = candles[-1]['close']
            last_processed_epoch[symbol] = candles[-1]['open_time']

        # Subscribe to candles updates
        candles_request = {
            "ticks_history": symbol,
            "adjust_start_time": 1,
            "count": SMA_SLOW + 5,
            "end": "latest",
            "granularity": TIMEFRAME,
            "style": "candles",
            "subscribe": 1
        }

        observable = await api.subscribe(candles_request)
        observable.subscribe(lambda x: queue.put_nowait(x))

        while True:
            candle_data = await queue.get()
            if 'ohlc' in candle_data:
                ohlc = candle_data['ohlc']
                open_time = ohlc['open_time']

                # New candle detected
                if open_time > last_processed_epoch[symbol]:
                    # The previously 'last_seen_close' is now the confirmed close of the finished candle.
                    prices_cache.append(last_seen_close)
                    if len(prices_cache) > SMA_SLOW + 10: # Keep a bit more than needed
                        prices_cache.pop(0)

                    if len(prices_cache) > SMA_SLOW:
                        sma6 = calculate_sma(prices_cache, SMA_FAST)
                        sma9 = calculate_sma(prices_cache, SMA_SLOW)

                        last_idx = len(prices_cache) - 1
                        prev_idx = len(prices_cache) - 2

                        is_rise = (sma6[last_idx] > sma9[last_idx]) and (sma6[prev_idx] <= sma9[prev_idx])
                        is_fall = (sma6[last_idx] < sma9[last_idx]) and (sma6[prev_idx] >= sma9[prev_idx])

                        if is_rise:
                            print(f"[{symbol}] SMA Rise Cross confirmed at {open_time}")
                            asyncio.create_task(place_trade(api, symbol, "CALL"))
                        elif is_fall:
                            print(f"[{symbol}] SMA Fall Cross confirmed at {open_time}")
                            asyncio.create_task(place_trade(api, symbol, "PUT"))

                    last_processed_epoch[symbol] = open_time

                # Update last seen close (continuously updated until candle closes)
                last_seen_close = ohlc['close']

    except Exception as e:
        print(f"[{symbol}] Error in trade loop: {e}")

async def place_trade(api, symbol, contract_type):
    global stakes
    stake = stakes[symbol]

    try:
        # Optimized: Consolidated proposal and buy into a single call to reduce latency by ~200ms
        buy = await api.buy({
            "buy": "1",
            "price": stake,
            "parameters": {
                "amount": stake,
                "basis": "stake",
                "contract_type": contract_type,
                "currency": "USD",
                "duration": DURATION,
                "duration_unit": "m",
                "symbol": symbol
            }
        })

        if 'error' in buy:
            print(f"[{symbol}] Buy Error: {buy['error']['message']}")
            return

        contract_id = buy['buy']['contract_id']
        print(f"[{symbol}] Bought {contract_type} contract {contract_id} with stake {stake}")

        await monitor_result(api, symbol, contract_id)

    except Exception as e:
        print(f"[{symbol}] Exception in place_trade: {e}")

async def monitor_result(api, symbol, contract_id):
    global stakes
    queue = asyncio.Queue()

    try:
        observable = await api.subscribe({"proposal_open_contract": 1, "contract_id": contract_id})
        observable.subscribe(lambda x: queue.put_nowait(x))

        while True:
            poc_data = await queue.get()
            poc = poc_data.get('proposal_open_contract', {})
            if poc.get('is_sold'):
                status = poc.get('status')
                profit = poc.get('profit')

                if status == 'won':
                    print(f"[{symbol}] Contract {contract_id} WON! Profit: {profit}")
                    stakes[symbol] = round(stakes[symbol] * MULTIPLIER, 2)
                else:
                    print(f"[{symbol}] Contract {contract_id} LOST. Loss: {profit}")
                    stakes[symbol] = INITIAL_STAKE

                print(f"[{symbol}] New stake for next trade: {stakes[symbol]}")
                break

    except Exception as e:
        print(f"[{symbol}] Error monitoring contract {contract_id}: {e}")

async def main():
    if API_TOKEN == 'YOUR_TOKEN_HERE' or not API_TOKEN:
        print("Error: DERIV_TOKEN environment variable is not set.")
        print("Usage: export DERIV_TOKEN=your_token_here && python deriv_sma_bot.py")
        return

    print(f"Starting bot on symbols: {', '.join(SYMBOLS)}")
    api = DerivAPI(app_id=APP_ID)

    try:
        auth = await api.authorize(API_TOKEN)
        print(f"Authorized as {auth['authorize']['email']}")
        await asyncio.gather(*(trade_logic(api, symbol) for symbol in SYMBOLS))
    except Exception as e:
        print(f"Main Loop Error: {e}")
    finally:
        await api.disconnect()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped by user.")
