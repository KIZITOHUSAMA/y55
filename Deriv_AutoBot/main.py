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
from indicators import atr, calculate_all_indicators
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

                for symbol in self.symbols:
                    # Fetch data once per symbol
                    df_h1 = self.mt5.get_candles(symbol, "H1", 300)
                    df_m15 = self.mt5.get_candles(symbol, "M15", 100)
                    df_m5 = self.mt5.get_candles(symbol, "M5", 50)
                    tick = self.mt5.get_tick(symbol)
                    s_info = self.mt5.get_symbol_info(symbol)

                    # Update Watchlist data for GUI
                    self.update_symbol_watchlist_data(symbol, df_h1, df_m15, tick, s_info)

                    if symbol in active_symbols:
                        continue

                    if len(positions) < config.MAX_SIMULTANEOUS_TRADES:
                        signal = self.strategy.get_signal(symbol, df_h1, df_m15, df_m5)
                        if signal:
                            self.watchlist_data[symbol]['signal'] = signal
                            self.execute_signal(symbol, signal, df_m5, tick, s_info)
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
            # Fetch history using the position ticket to get the exit deal and profit
            history = mt5.history_deals_get(position=ticket)
            if history:
                # The exit deal is usually the last one in the history for this position
                deal = history[-1]
                profit = deal.profit + deal.commission + deal.swap
                self.db.log_trade_close(ticket, deal.price, profit, datetime.fromtimestamp(deal.time))
                self.risk.update_loss_streak(profit)
                self.whatsapp.notify_trade_closed(deal.symbol, profit)
                logging.info(f"Trade closed: {ticket} | Profit: {profit}")

        self.active_tickets = current_tickets
        self.trade_mgmt.clean_partial_tp_list(self.active_tickets)

    def update_symbol_watchlist_data(self, symbol, df_h1, df_m15, tick, s_info):
        try:
            if df_h1 is None or df_m15 is None or tick is None or s_info is None: return

            trend = self.strategy.check_trend_h1(symbol, df_h1)

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

    def execute_signal(self, symbol, signal_type, df_m5, tick, symbol_info):
        allowed, spread = self.risk.check_spread(symbol, tick, symbol_info)
        if not allowed:
            logging.info(f"Skipping {symbol} due to high spread: {spread}")
            return

        order_type = mt5.ORDER_TYPE_BUY if signal_type == "BUY" else mt5.ORDER_TYPE_SELL

        atr_series = atr(df_m5['high'].values, df_m5['low'].values, df_m5['close'].values, 14)
        atr_val = atr_series[-1]

        if np.isnan(atr_val) or atr_val <= 0:
            logging.warning(f"Invalid ATR for {symbol}, using fallback.")
            return

        price = tick.ask if signal_type == "BUY" else tick.bid
        sl_dist = atr_val * 2
        sl = price - sl_dist if signal_type == "BUY" else price + sl_dist
        tp = price + (sl_dist * config.RISK_RR_RATIO) if signal_type == "BUY" else price - (sl_dist * config.RISK_RR_RATIO)

        lot = self.risk.calculate_lot(symbol_info, self.last_account_info['balance'], 1.0, sl_dist)

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

    def save_settings():
        token = gui.token_input.text()
        phone_id = gui.phone_id_input.text()
        if token and phone_id:
            controller.whatsapp.token = token
            controller.whatsapp.phone_id = phone_id
            controller.whatsapp.url = f"https://graph.facebook.com/v17.0/{phone_id}/messages"
            controller.whatsapp.headers["Authorization"] = f"Bearer {token}"
            logging.info("WhatsApp settings updated from GUI")

    gui.save_btn.clicked.connect(save_settings)

    gui.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
