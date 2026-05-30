"""
Deriv SMA (6,9) Crossover Trading Bot
-------------------------------------
Requirements:
    pip install python-deriv-api pandas websockets reactivex

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
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period

async def trade_logic(api, symbol):
    global stakes, last_processed_epoch
    print(f"Monitoring {symbol}...")

    queue = asyncio.Queue()

    # Subscribe to candles updates
    # The python-deriv-api uses RxPy observables. We push updates to an asyncio.Queue.
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
        # Capture initial history and subscribe
        observable = await api.subscribe(candles_request)

        # Initial local buffer for candle close prices
        prices = []

        # The subscription response contains initial candles
        init_data = await api.ticks_history(candles_request)
        if 'candles' in init_data:
            prices = [float(c['close']) for c in init_data['candles']]
            if init_data['candles']:
                last_processed_epoch[symbol] = init_data['candles'][-1]['open_time']

        observable.subscribe(lambda x: queue.put_nowait(x))

        while True:
            candle_data = await queue.get()
            if 'ohlc' in candle_data:
                ohlc = candle_data['ohlc']
                open_time = ohlc['open_time']
                close_price = float(ohlc['close'])

                # Check if a new candle has started
                if open_time > last_processed_epoch[symbol]:
                    # The previous OHLC message was the last one for that candle.
                    # However, we don't have the final 'close' of that candle until this new one starts.
                    # In a real stream, the last 'ohlc' message with the OLD open_time would be the close.
                    # But often we just use the 'close' from the first tick of the NEW candle as a proxy for the close of the PREVIOUS one if we didn't store it.

                    # Correct logic:
                    # 1. We just detected a NEW candle started at 'open_time'.
                    # 2. The 'close_price' in this message is the latest price.
                    # 3. We append this 'close_price' to our 'prices' buffer as the closed price of the candle that just ended.
                    prices.append(close_price)
                    if len(prices) > 50: # Keep buffer small
                        prices.pop(0)

                    # 4. Now calculate SMAs including this newly closed candle.
                    if len(prices) > SMA_SLOW:
                        # Current SMA (includes the candle that just closed)
                        sma6_curr = calculate_sma(prices, SMA_FAST)
                        sma9_curr = calculate_sma(prices, SMA_SLOW)

                        # Previous SMA (excludes the candle that just closed)
                        sma6_prev = calculate_sma(prices[:-1], SMA_FAST)
                        sma9_prev = calculate_sma(prices[:-1], SMA_SLOW)

                        if sma6_curr is not None and sma9_curr is not None and sma6_prev is not None and sma9_prev is not None:
                            is_rise = (sma6_curr > sma9_curr) and (sma6_prev <= sma9_prev)
                            is_fall = (sma6_curr < sma9_curr) and (sma6_prev >= sma9_prev)

                            if is_rise:
                                print(f"[{symbol}] SMA Rise Cross confirmed at {open_time}")
                                asyncio.create_task(place_trade(api, symbol, "CALL"))
                            elif is_fall:
                                print(f"[{symbol}] SMA Fall Cross confirmed at {open_time}")
                                asyncio.create_task(place_trade(api, symbol, "PUT"))

                    # Update last processed epoch
                    last_processed_epoch[symbol] = open_time
                    if len(prices) > 50: # Keep buffer small
                        prices.pop(0)
                else:
                    # Update current (still forming) candle's close price in the buffer
                    # Note: We only append to prices when a candle FINISHES.
                    # So 'prices' always contains CLOSED candles.
                    # The 'ohlc' we just got is for the current forming candle.
                    pass

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
