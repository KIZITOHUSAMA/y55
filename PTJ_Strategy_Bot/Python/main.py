import MetaTrader5 as mt5
import time
import logging
from datetime import datetime
from mt5_engine import MT5Engine
from ptj_strategy import PTJStrategy
from risk_manager import RiskManager
import config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    engine = MT5Engine()
    # In MT5Engine.py it's called connect() not initialize()
    if not engine.connect():
        logging.error("Failed to connect to MT5")
        return

    strategy = PTJStrategy(engine, config)

    # Mock DB for RiskManager
    class MockDB:
        def get_daily_profit(self): return 0
        def log_trade(self, *args): pass

    db = MockDB()
    risk_mgr = RiskManager(config, db)

    logging.info("PTJ Hybrid Bot Started...")

    try:
        while True:
            # Re-fetch positions each loop
            all_positions = engine.get_positions()

            for symbol in config.SYMBOLS:
                # Filter positions for this symbol and bot magic
                symbol_positions = [p for p in all_positions if p.symbol == symbol and p.magic == 123456]

                # 1. Manage existing trades (Partial close, Breakeven)
                for pos in symbol_positions:
                    manage_ptj_position(engine, pos, config)

                # 2. Check for new entries if no position exists
                if len(symbol_positions) == 0:
                    signal = strategy.get_signal(symbol)
                    if signal:
                        logging.info(f"Signal detected for {symbol}: {signal}")
                        execute_ptj_trade(engine, symbol, signal, config, risk_mgr)

            time.sleep(10)
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
    finally:
        engine.disconnect()

def manage_ptj_position(engine, pos, cfg):
    entry = pos.price_open
    current = pos.price_current
    sl = pos.sl
    tp = pos.tp

    if sl == 0: return

    risk = abs(entry - sl)
    if risk == 0: return

    profit_r = abs(current - entry) / risk

    # Partial Close at 3R
    if profit_r >= cfg.PARTIAL_RR and pos.volume > 0.01:
        # Check if already moved to BE to avoid repeated partials (simple heuristic)
        if abs(sl - entry) > 0.00001:
            close_vol = round(pos.volume * cfg.PARTIAL_VOLUME_PERCENT, 2)
            # Ensure we don't try to close more than available or less than min
            close_vol = max(0.01, min(pos.volume - 0.01, close_vol))

            # engine has close_trade(ticket, symbol, type, volume)
            if engine.close_trade(pos.ticket, pos.symbol, pos.type, close_vol):
                logging.info(f"Partial close at 3R for {pos.symbol}")
                # Move to Breakeven using modify_sl_tp
                engine.modify_sl_tp(pos.ticket, sl=entry, tp=tp)

def execute_ptj_trade(engine, symbol, signal, cfg, risk_mgr):
    tick = engine.get_tick(symbol)
    if tick is None: return

    sym_info = engine.get_symbol_info(symbol)
    if sym_info is None: return

    # Simple SL based on recent M5 candle range
    df = engine.get_candles(symbol, "M5", 2)
    if df is None or len(df) < 2: return

    stop_dist = abs(df['high'].iloc[-1] - df['low'].iloc[-1])
    if stop_dist < sym_info.point * 10: stop_dist = sym_info.point * 50

    acc_info = engine.get_account_info()
    if acc_info is None: return

    balance = acc_info['balance']
    lot = risk_mgr.calculate_lot(sym_info, balance, cfg.RISK_PERCENT, stop_dist)

    if signal == "BUY":
        sl = tick.ask - stop_dist
        tp = tick.ask + (stop_dist * cfg.RR_RATIO)
        # engine has open_trade(symbol, type, lot, sl, tp)
        engine.open_trade(symbol, mt5.ORDER_TYPE_BUY, lot, sl=sl, tp=tp, comment="PTJ Entry")
    else:
        sl = tick.bid + stop_dist
        tp = tick.bid - (stop_dist * cfg.RR_RATIO)
        engine.open_trade(symbol, mt5.ORDER_TYPE_SELL, lot, sl=sl, tp=tp, comment="PTJ Entry")

if __name__ == "__main__":
    main()
