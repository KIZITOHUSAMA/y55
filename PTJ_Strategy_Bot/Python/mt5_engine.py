import MetaTrader5 as mt5
import pandas as pd
import logging

class MT5Engine:
    def __init__(self):
        self.connected = False

    def connect(self):
        if not mt5.initialize():
            logging.error(f"MT5 initialize failed, error code: {mt5.last_error()}")
            return False

        self.connected = True
        logging.info("Successfully connected to MT5")
        return True

    def disconnect(self):
        mt5.shutdown()
        self.connected = False

    def get_account_info(self):
        if not self.connected: return None
        acc = mt5.account_info()
        if acc is None: return None
        return {
            "name": acc.name,
            "balance": acc.balance,
            "equity": acc.equity,
            "margin_level": acc.margin_level,
            "demo": acc.trade_mode == mt5.ACCOUNT_TRADE_MODE_DEMO,
            "profit": acc.profit
        }

    def get_market_watch_symbols(self):
        if not self.connected: return []
        symbols = mt5.symbols_get()
        return [s.name for s in symbols if s.select]

    def get_candles(self, symbol, timeframe, count=500):
        if not self.connected: return None

        # Convert string timeframe to MT5 constant if necessary
        tf_map = {
            "M5": mt5.TIMEFRAME_M5,
            "M15": mt5.TIMEFRAME_M15,
            "H1": mt5.TIMEFRAME_H1
        }
        mt5_tf = tf_map.get(timeframe, mt5.TIMEFRAME_M5)

        rates = mt5.copy_rates_from_pos(symbol, mt5_tf, 0, count)
        if rates is None or len(rates) == 0:
            logging.warning(f"Failed to copy rates for {symbol}, error: {mt5.last_error()}")
            return None

        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        return df

    def get_tick(self, symbol):
        if not self.connected: return None
        tick = mt5.symbol_info_tick(symbol)
        return tick

    def open_trade(self, symbol, order_type, lot, sl=0.0, tp=0.0, comment="DerivAutoBot"):
        if not self.connected: return None

        tick = self.get_tick(symbol)
        if tick is None: return None

        price = tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot,
            "type": order_type,
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": 20,
            "magic": 123456,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logging.error(f"Order failed for {symbol}: {result.comment} (code: {result.retcode})")
            return None

        return result

    def close_trade(self, ticket, symbol, order_type, lot, comment="Close"):
        if not self.connected: return None

        tick = self.get_tick(symbol)
        if tick is None: return None

        # To close a BUY, we need to SELL
        close_type = mt5.ORDER_TYPE_SELL if order_type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
        price = tick.bid if order_type == mt5.ORDER_TYPE_BUY else tick.ask

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot,
            "type": close_type,
            "position": ticket,
            "price": price,
            "deviation": 20,
            "magic": 123456,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        return result

    def modify_sl_tp(self, ticket, sl, tp):
        if not self.connected: return None

        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "sl": sl,
            "tp": tp
        }

        result = mt5.order_send(request)
        return result

    def get_positions(self):
        if not self.connected: return []
        positions = mt5.positions_get()
        return positions if positions else []

    def get_symbol_info(self, symbol):
        return mt5.symbol_info(symbol)
