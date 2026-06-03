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

def calculate_sma(prices, period):
    """Native Python implementation of SMA for better performance."""
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period

async def trade_logic(api, symbol):
    global stakes
    print(f"Monitoring {symbol}...")

    queue = asyncio.Queue()
    candle_buffer = []  # Local buffer to avoid redundant API calls
    last_open_time = 0

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

    try:
        observable = await api.subscribe(candles_request)
        observable.subscribe(lambda x: queue.put_nowait(x))

        while True:
            msg = await queue.get()

            if 'candles' in msg:
                # Initial payload
                candle_buffer = [float(c['close']) for c in msg['candles']]
                # The last candle in 'candles' is often the one currently forming
                # but let's assume 'ohlc' will update/confirm it.
                if msg['candles']:
                    last_open_time = msg['candles'][-1]['epoch']

            elif 'ohlc' in msg:
                ohlc = msg['ohlc']
                open_time = int(ohlc['open_time'])
                close_price = float(ohlc['close'])

                if last_open_time == 0:
                    last_open_time = open_time
                    candle_buffer.append(close_price)
                    continue

                if open_time > last_open_time:
                    # New candle started! The previous one is now finalized.
                    # We already have the 'last closed' price as the last element in buffer
                    # which was being updated by 'ohlc' ticks.

                    if len(candle_buffer) > SMA_SLOW:
                        # SMA on last closed candle (index -1) and previous closed (index -2)
                        # Prices in buffer: [..., p_prev, p_last]

                        # Calculate SMA for the state JUST FINISHED
                        # We need SMA(last) and SMA(prev) to detect crossover
                        prices_last = candle_buffer
                        prices_prev = candle_buffer[:-1]

                        sma6_last = calculate_sma(prices_last, SMA_FAST)
                        sma9_last = calculate_sma(prices_last, SMA_SLOW)

                        sma6_prev = calculate_sma(prices_prev, SMA_FAST)
                        sma9_prev = calculate_sma(prices_prev, SMA_SLOW)

                        if all(v is not None for v in [sma6_last, sma9_last, sma6_prev, sma9_prev]):
                            is_rise = (sma6_last > sma9_last) and (sma6_prev <= sma9_prev)
                            is_fall = (sma6_last < sma9_last) and (sma6_prev >= sma9_prev)

                            if is_rise:
                                print(f"[{symbol}] SMA Rise Cross confirmed at {open_time}")
                                asyncio.create_task(place_trade(api, symbol, "CALL"))
                            elif is_fall:
                                print(f"[{symbol}] SMA Fall Cross confirmed at {open_time}")
                                asyncio.create_task(place_trade(api, symbol, "PUT"))

                    # Prepare for next candle
                    last_open_time = open_time
                    candle_buffer.append(close_price)
                    # Keep buffer size manageable
                    if len(candle_buffer) > 50:
                        candle_buffer.pop(0)
                else:
                    # Update current candle price in buffer
                    if candle_buffer:
                        candle_buffer[-1] = close_price

    except Exception as e:
        print(f"[{symbol}] Error in trade loop: {e}")

async def place_trade(api, symbol, contract_type):
    global stakes
    stake = stakes[symbol]

    try:
        proposal = await api.proposal({
            "proposal": 1,
            "amount": stake,
            "basis": "stake",
            "contract_type": contract_type,
            "currency": "USD",
            "duration": DURATION,
            "duration_unit": "m",
            "symbol": symbol
        })

        if 'error' in proposal:
            print(f"[{symbol}] Proposal Error: {proposal['error']['message']}")
            return

        buy = await api.buy({
            "buy": proposal['proposal']['id'],
            "price": stake
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
