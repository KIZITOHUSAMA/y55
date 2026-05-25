import asyncio
import os
import sys
import pandas as pd
from deriv_api import DerivAPI

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

def calculate_sma(df, period):
    return df['close'].rolling(window=period).mean()

async def trade_logic(api, symbol):
    global stakes, last_processed_epoch
    print(f"Monitoring {symbol}...")

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
        subscription = await api.subscribe(candles_request)

        async for candle_data in subscription:
            if 'ohlc' in candle_data:
                ohlc = candle_data['ohlc']
                open_time = ohlc['open_time']

                # Check if a new candle has started
                if open_time > last_processed_epoch[symbol]:
                    # We just moved to a new candle.
                    # The candle at open_time - TIMEFRAME is now officially CLOSED.

                    # Fetch confirmed history to be sure
                    hist_resp = await api.ticks_history({
                        "ticks_history": symbol,
                        "adjust_start_time": 1,
                        "count": SMA_SLOW + 5,
                        "end": "latest",
                        "granularity": TIMEFRAME,
                        "style": "candles"
                    })

                    if 'candles' in hist_resp:
                        df = pd.DataFrame(hist_resp['candles'])
                        # df.iloc[-1] is the current open candle
                        # df.iloc[-2] is the just closed candle
                        # df.iloc[-3] is the candle before that

                        if len(df) > SMA_SLOW:
                            sma6 = calculate_sma(df, SMA_FAST)
                            sma9 = calculate_sma(df, SMA_SLOW)

                            last_idx = len(df) - 2
                            prev_idx = len(df) - 3

                            # Crossover detection
                            # Rise: Fast SMA crosses above Slow SMA
                            is_rise = (sma6.iloc[last_idx] > sma9.iloc[last_idx]) and (sma6.iloc[prev_idx] <= sma9.iloc[prev_idx])
                            # Fall: Fast SMA crosses below Slow SMA
                            is_fall = (sma6.iloc[last_idx] < sma9.iloc[last_idx]) and (sma6.iloc[prev_idx] >= sma9.iloc[prev_idx])

                            if is_rise:
                                print(f"[{symbol}] SMA Rise Cross confirmed at {open_time}")
                                asyncio.create_task(place_trade(api, symbol, "CALL"))
                            elif is_fall:
                                print(f"[{symbol}] SMA Fall Cross confirmed at {open_time}")
                                asyncio.create_task(place_trade(api, symbol, "PUT"))

                            last_processed_epoch[symbol] = open_time

    except Exception as e:
        print(f"[{symbol}] Error in trade loop: {e}")

async def place_trade(api, symbol, contract_type):
    global stakes
    stake = stakes[symbol]

    try:
        # 1. Get proposal
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

        # 2. Buy contract
        buy = await api.buy({
            "buy": proposal['proposal']['id'],
            "price": stake
        })

        if 'error' in buy:
            print(f"[{symbol}] Buy Error: {buy['error']['message']}")
            return

        contract_id = buy['buy']['contract_id']
        print(f"[{symbol}] Bought {contract_type} contract {contract_id} with stake {stake}")

        # 3. Monitor result
        await monitor_result(api, symbol, contract_id)

    except Exception as e:
        print(f"[{symbol}] Exception in place_trade: {e}")

async def monitor_result(api, symbol, contract_id):
    global stakes

    try:
        # Subscribe to contract updates
        poc_sub = await api.subscribe({"proposal_open_contract": 1, "contract_id": contract_id})

        async for poc_data in poc_sub:
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
                break # Stop monitoring this contract

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

        # Start all monitor tasks
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
