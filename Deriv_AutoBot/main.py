import sys
import logging
import threading
import time
from datetime import datetime
from PyQt6.QtWidgets import QApplication
import MetaTrader5 as mt5

from mt5_engine import MT5Engine
from strategy import MTFStrategy
from risk_manager import RiskManager
from trade_manager import TradeManager
from database import DatabaseManager
from whatsapp import WhatsAppNotifier
from gui import TradingBotGUI
from indicators import atr
import config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class AutoBotController:
    def __init__(self):
        self.mt5 = MT5Engine()
        self.db = DatabaseManager(config.DB_PATH)
        self.whatsapp = WhatsAppNotifier(config.WHATSAPP_TOKEN, config.WHATSAPP_PHONE_ID, config.WHATSAPP_RECIPIENT_PHONE)
        self.risk = RiskManager(config, self.db)
        self.trade_mgmt = TradeManager(self.mt5, config)
        self.strategy = MTFStrategy(self.mt5, config)

        self.running = False
        self.symbols = []
        self.active_tickets = set()
        self.last_account_info = None
        self.watchlist_data = {} # {symbol: {trend, rsi, atr, spread, signal}}

    def start(self):
        if self.mt5.connect():
            self.running = True
            self.symbols = self.mt5.get_market_watch_symbols()
            threading.Thread(target=self.main_loop, daemon=True).start()
            return True
        return False

    def stop(self):
        self.running = False
        self.mt5.disconnect()

    def get_account_summary(self):
        return self.mt5.get_account_info()

    def main_loop(self):
        logging.info("Bot main loop started")
        while self.running:
            try:
                acc_info = self.mt5.get_account_info()
                if not acc_info:
                    time.sleep(5)
                    continue
                self.last_account_info = acc_info

                # 1. Reconcile trades (check for closed trades)
                self.reconcile_trades()

                # 2. Manage existing trades (SL/TP updates)
                self.trade_mgmt.manage_positions()

                # 3. Risk check
                can_trade, reason = self.risk.can_trade(acc_info)
                if not can_trade:
                    logging.info(f"Trading paused: {reason}")
                    time.sleep(10)
                    continue

                # 4. Scan symbols for signals
                positions = self.mt5.get_positions()
                active_symbols = [p.symbol for p in positions]

                if len(positions) < config.MAX_SIMULTANEOUS_TRADES:
                    for symbol in self.symbols:
                        # Update Watchlist data for GUI
                        self.update_symbol_watchlist_data(symbol)

                        if symbol in active_symbols:
                            continue

                        signal = self.strategy.get_signal(symbol)
                        if signal:
                            self.watchlist_data[symbol]['signal'] = signal
                            self.execute_signal(symbol, signal)
                        else:
                            self.watchlist_data[symbol]['signal'] = "NEUTRAL"

                time.sleep(1)
            except Exception as e:
                logging.error(f"Error in main loop: {e}")
                time.sleep(5)

    def reconcile_trades(self):
        """Checks which trades are no longer in MT5 but were marked active."""
        current_positions = self.mt5.get_positions()
        current_tickets = {p.ticket for p in current_positions}

        # Check for closed tickets
        closed_tickets = self.active_tickets - current_tickets
        for ticket in closed_tickets:
            # Fetch history to get profit/exit price
            # For simplicity in this version, we look at last deals
            history = mt5.history_deals_get(ticket=ticket)
            if history:
                deal = history[-1]
                profit = deal.profit + deal.commission + deal.swap
                self.db.log_trade_close(ticket, deal.price, profit, datetime.fromtimestamp(deal.time))
                self.risk.update_loss_streak(profit)
                self.whatsapp.notify_trade_closed(deal.symbol, profit)
                logging.info(f"Trade closed: {ticket} | Profit: {profit}")

        self.active_tickets = current_tickets
        self.trade_mgmt.clean_partial_tp_list(self.active_tickets)

    def update_symbol_watchlist_data(self, symbol):
        # Optimized to only fetch what's needed
        try:
            df_h1 = self.mt5.get_candles(symbol, "H1", 2)
            df_m15 = self.mt5.get_candles(symbol, "M15", 20)
            tick = self.mt5.get_tick(symbol)
            s_info = self.mt5.get_symbol_info(symbol)

            if df_h1 is None or df_m15 is None or tick is None: return

            # Simplified trend/rsi for display
            trend = self.strategy.check_trend_h1(symbol)

            from strategy import calculate_all_indicators
            df_m15 = calculate_all_indicators(df_m15, config)
            last_m15 = df_m15.iloc[-1]

            spread = (tick.ask - tick.bid) / s_info.point if s_info.point != 0 else 0

            self.watchlist_data[symbol] = {
                'trend': trend,
                'rsi': round(last_m15['rsi'], 2),
                'atr': round(last_m15['atr'], 2),
                'spread': round(spread, 1),
                'signal': self.watchlist_data.get(symbol, {}).get('signal', "SCANNING")
            }
        except Exception as e:
            logging.debug(f"Error updating watchlist for {symbol}: {e}")

    def execute_signal(self, symbol, signal_type):
        tick = self.mt5.get_tick(symbol)
        symbol_info = self.mt5.get_symbol_info(symbol)

        allowed, spread = self.risk.check_spread(symbol, tick, symbol_info)
        if not allowed:
            logging.info(f"Skipping {symbol} due to high spread: {spread}")
            return

        order_type = mt5.ORDER_TYPE_BUY if signal_type == "BUY" else mt5.ORDER_TYPE_SELL

        df = self.mt5.get_candles(symbol, "M5", 20)
        atr_val = atr(df['high'].values, df['low'].values, df['close'].values, 14)[-1]

        price = tick.ask if signal_type == "BUY" else tick.bid
        sl_dist = atr_val * 2
        sl = price - sl_dist if signal_type == "BUY" else price + sl_dist
        tp = price + (sl_dist * config.RISK_RR_RATIO) if signal_type == "BUY" else price - (sl_dist * config.RISK_RR_RATIO)

        lot = self.risk.calculate_lot(symbol_info, 1.0, sl_dist)

        result = self.mt5.open_trade(symbol, order_type, lot, sl, tp)
        if result:
            logging.info(f"Opened {signal_type} on {symbol}")
            self.db.log_trade_open(result.order, symbol, signal_type, price, datetime.now())
            self.whatsapp.notify_trade_opened(symbol, signal_type, price, sl, tp, 1.0)
            self.active_tickets.add(result.order)

def main():
    app = QApplication(sys.argv)
    controller = AutoBotController()
    gui = TradingBotGUI(controller)

    gui.start_btn.clicked.connect(controller.start)
    gui.stop_btn.clicked.connect(controller.stop)

    gui.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
