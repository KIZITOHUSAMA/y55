import MetaTrader5 as mt5
from indicators import atr

class TradeManager:
    def __init__(self, mt5_engine, config):
        self.mt5 = mt5_engine
        self.config = config
        self.partial_tp_tickets = set()

    def manage_positions(self):
        positions = self.mt5.get_positions()
        for pos in positions:
            ticket = pos.ticket
            symbol = pos.symbol
            p_type = pos.type
            entry = pos.price_open
            current_price = pos.price_current
            sl = pos.sl
            tp = pos.tp
            profit = pos.profit

            # Risk points (initial distance from entry to SL)
            if sl == 0: continue

            risk_dist = abs(entry - sl)
            if risk_dist == 0: continue

            current_dist = abs(current_price - entry)
            r_multiple = current_dist / risk_dist if profit > 0 else -current_dist / risk_dist

            # 1. Break-even Logic (at 1R)
            if r_multiple >= self.config.BREAK_EVEN_AT_R and sl != entry:
                self.mt5.modify_sl_tp(ticket, entry, tp)

            # 2. Partial TP (50% at 2R)
            if r_multiple >= 2.0 and ticket not in self.partial_tp_tickets:
                half_lot = pos.volume / 2
                symbol_info = self.mt5.get_symbol_info(symbol)
                if half_lot >= symbol_info.volume_min:
                    self.mt5.close_trade(ticket, symbol, p_type, half_lot, comment="Partial TP")
                    self.partial_tp_tickets.add(ticket)

            # 3. ATR Trailing Stop (Starts at 1.5R)
            if r_multiple >= self.config.TRAIL_START_AT_R:
                # Fetch ATR from M5
                df = self.mt5.get_candles(symbol, "M5", 20)
                if df is not None and not df.empty:
                    atr_val = atr(df['high'].values, df['low'].values, df['close'].values, 14)[-1]

                    if p_type == mt5.ORDER_TYPE_BUY:
                        new_sl = current_price - (atr_val * 1.5)
                        if new_sl > sl:
                            self.mt5.modify_sl_tp(ticket, new_sl, tp)
                    else:
                        new_sl = current_price + (atr_val * 1.5)
                        if new_sl < sl or sl == 0:
                            self.mt5.modify_sl_tp(ticket, new_sl, tp)

    def clean_partial_tp_list(self, active_tickets):
        self.partial_tp_tickets = {t for t in self.partial_tp_tickets if t in active_tickets}
