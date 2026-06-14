import asyncio
import json
import websockets
import logging
import time
from ta_lib import get_signal
from database import LBotDatabase
import config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DerivLBot:
    def __init__(self):
        self.uri = f"wss://ws.derivws.com/websockets/v3?app_id={config.APP_ID}"
        self.db = LBotDatabase(config.DB_PATH)
        self.ws = None
        self.history = {symbol: [] for symbol in config.VOLATILITY_INDICES}
        self.last_candle_time = {symbol: 0 for symbol in config.VOLATILITY_INDICES}
        self.active_contracts = {} # {contract_id: symbol}
        self.current_stakes = {symbol: config.INITIAL_STAKE for symbol in config.VOLATILITY_INDICES}

    async def connect(self):
        try:
            self.ws = await websockets.connect(self.uri)
            logging.info("Connected to Deriv WebSocket")

            # Authorize
            auth_req = {"authorize": config.DERIV_TOKEN}
            await self.send(auth_req)
            return True
        except Exception as e:
            logging.error(f"Connection failed: {e}")
            return False

    async def send(self, data):
        if self.ws:
            await self.ws.send(json.dumps(data))

    async def subscribe_ohlc(self):
        for symbol in config.VOLATILITY_INDICES:
            req = {
                "ticks_history": symbol,
                "adjust_start_time": 1,
                "count": 100,
                "end": "latest",
                "start": 1,
                "style": "candles",
                "subscribe": 1,
                "granularity": 60
            }
            await self.send(req)
            await asyncio.sleep(0.1) # Rate limit protection

    async def handle_ohlc(self, data):
        if 'candles' in data:
            symbol = data.get('echo_req', {}).get('ticks_history')
            # Ensure all prices are floats to avoid NumPy TypeError
            self.history[symbol] = [float(c['close']) for c in data['candles']]
            self.last_candle_time[symbol] = data['candles'][-1]['epoch']
            logging.info(f"Initialized history for {symbol}")

        elif 'ohlc' in data:
            ohlc = data['ohlc']
            symbol = ohlc['symbol']
            open_time = ohlc['open_time']

            # If new candle starts
            if open_time > self.last_candle_time[symbol]:
                # The previous candle is now closed
                # Ensure price is float
                self.history[symbol].append(float(ohlc['close']))
                if len(self.history[symbol]) > 100:
                    self.history[symbol].pop(0)

                self.last_candle_time[symbol] = open_time

                # Run Strategy
                signal = get_signal(self.history[symbol], config)
                if signal:
                    # Check if already in trade for this symbol
                    if not any(s == symbol for s in self.active_contracts.values()):
                        await self.place_trade(symbol, signal)
            else:
                # Update current candle price
                if self.history[symbol]:
                    self.history[symbol][-1] = float(ohlc['close'])

    async def place_trade(self, symbol, signal):
        stake = round(self.current_stakes[symbol], 2)
        req = {
            "buy": 1,
            "price": stake,
            "parameters": {
                "amount": stake,
                "basis": "stake",
                "contract_type": "CALL" if signal == "CALL" else "PUT",
                "currency": config.CURRENCY,
                "duration": config.DURATION_MINUTES,
                "duration_unit": "m",
                "symbol": symbol
            }
        }
        await self.send(req)
        logging.info(f"Signal: {signal} on {symbol} with stake ${stake}")

    async def handle_buy(self, data):
        if 'error' in data:
            logging.error(f"Buy error: {data['error']['message']}")
            return

        buy = data.get('buy', {})
        contract_id = buy.get('contract_id')
        symbol = data.get('echo_req', {}).get('parameters', {}).get('symbol')

        self.active_contracts[contract_id] = symbol
        self.db.log_trade(symbol, contract_id, data['echo_req']['parameters']['contract_type'], buy['buy_price'])

        # Subscribe to contract updates
        await self.send({"proposal_open_contract": 1, "contract_id": contract_id, "subscribe": 1})

    async def handle_contract_update(self, data):
        contract = data.get('proposal_open_contract', {})
        if contract.get('is_sold'):
            contract_id = contract.get('contract_id')
            symbol = self.active_contracts.get(contract_id)
            if not symbol: return

            profit = contract.get('profit', 0)
            status = 'WON' if profit > 0 else 'LOST'
            payout = contract.get('payout', 0)

            self.db.update_trade_result(contract_id, payout, status)

            # Reverse Martingale Logic
            if status == 'WON':
                streak = self.db.get_win_streak(symbol)
                if streak < config.MAX_WIN_STREAK:
                    self.current_stakes[symbol] *= config.WIN_STAKE_MULTIPLIER
                    logging.info(f"Win! Streak: {streak}. Increasing stake for {symbol}")
                else:
                    self.current_stakes[symbol] = config.INITIAL_STAKE
                    logging.info(f"Max streak reached for {symbol}. Resetting stake.")
            else:
                self.current_stakes[symbol] = config.INITIAL_STAKE
                logging.info(f"Loss on {symbol}. Resetting stake.")

            # Cleanup
            if contract_id in self.active_contracts:
                del self.active_contracts[contract_id]

            logging.info(f"Trade FINISHED: {status} on {symbol}. Profit: ${profit:.2f}")

    async def run(self):
        if not await self.connect(): return
        await self.subscribe_ohlc()

        async for message in self.ws:
            data = json.loads(message)
            msg_type = data.get('msg_type')

            if msg_type == 'ohlc' or msg_type == 'candles':
                await self.handle_ohlc(data)
            elif msg_type == 'buy':
                await self.handle_buy(data)
            elif msg_type == 'proposal_open_contract':
                await self.handle_contract_update(data)
            elif msg_type == 'authorize':
                if 'error' in data:
                    logging.error(f"Authorization failed: {data['error'].get('message', 'Unknown error')}")
                elif 'authorize' in data and 'email' in data['authorize']:
                    logging.info(f"Authorized as: {data['authorize']['email']}")
                else:
                    logging.warning("Authorization succeeded but email not found in response.")

if __name__ == "__main__":
    bot = DerivLBot()
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
