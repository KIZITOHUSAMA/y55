import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QTabWidget, QLabel, QPushButton,
                             QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit)
from PyQt6.QtCore import QTimer, Qt
import pyqtgraph as pg
import MetaTrader5 as mt5
import numpy as np

class TradingBotGUI(QMainWindow):
    def __init__(self, bot_engine):
        super().__init__()
        self.bot = bot_engine
        self.setWindowTitle("Deriv AutoBot Pro - MT5")
        self.resize(1200, 800)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        # Header Info
        self.setup_header()

        # Tabs
        self.tabs = QTabWidget()
        self.setup_watchlist_tab()
        self.setup_positions_tab()
        self.setup_chart_tab()
        self.setup_config_tab()

        self.main_layout.addWidget(self.tabs)

        # Footer
        self.status_bar = QLabel("System Ready | Connected: False")
        self.main_layout.addWidget(self.status_bar)

        # Update Timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_ui)
        self.timer.start(2000) # 2 second refresh for UI stability

    def setup_header(self):
        header_layout = QHBoxLayout()
        self.acc_name_label = QLabel("Account: N/A")
        self.balance_label = QLabel("Balance: $0.00")
        self.equity_label = QLabel("Equity: $0.00")
        self.profit_today_label = QLabel("Today's Profit: $0.00")

        for lbl in [self.acc_name_label, self.balance_label, self.equity_label, self.profit_today_label]:
            lbl.setStyleSheet("font-weight: bold; font-size: 14px;")
            header_layout.addWidget(lbl)

        self.start_btn = QPushButton("START BOT")
        self.start_btn.setStyleSheet("background-color: #2ecc71; color: white; font-weight: bold;")
        self.stop_btn = QPushButton("STOP BOT")
        self.stop_btn.setStyleSheet("background-color: #e74c3c; color: white; font-weight: bold;")

        header_layout.addWidget(self.start_btn)
        header_layout.addWidget(self.stop_btn)

        self.main_layout.addLayout(header_layout)

    def setup_watchlist_tab(self):
        self.watchlist_tab = QWidget()
        layout = QVBoxLayout(self.watchlist_tab)
        self.watchlist_table = QTableWidget(0, 6)
        self.watchlist_table.setHorizontalHeaderLabels(["Symbol", "Trend (H1)", "RSI (M15)", "ATR", "Spread", "Signal"])
        self.watchlist_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.watchlist_table)
        self.tabs.addTab(self.watchlist_tab, "Watchlist")

    def setup_positions_tab(self):
        self.positions_tab = QWidget()
        layout = QVBoxLayout(self.positions_tab)
        self.positions_table = QTableWidget(0, 4)
        self.positions_table.setHorizontalHeaderLabels(["Ticket", "Symbol", "Type", "Profit ($)"])
        self.positions_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.positions_table)

        self.close_all_btn = QPushButton("CLOSE ALL TRADES")
        self.close_all_btn.setStyleSheet("background-color: #f39c12; color: white;")
        layout.addWidget(self.close_all_btn)

        self.tabs.addTab(self.positions_tab, "Open Positions")

    def setup_chart_tab(self):
        self.chart_tab = QWidget()
        layout = QVBoxLayout(self.chart_tab)
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('k')
        self.plot_widget.showGrid(x=True, y=True)
        layout.addWidget(self.plot_widget)
        self.tabs.addTab(self.chart_tab, "Live Chart")

    def setup_config_tab(self):
        self.config_tab = QWidget()
        layout = QVBoxLayout(self.config_tab)

        layout.addWidget(QLabel("WhatsApp Access Token:"))
        self.token_input = QLineEdit()
        layout.addWidget(self.token_input)

        layout.addWidget(QLabel("Phone Number ID:"))
        self.phone_id_input = QLineEdit()
        layout.addWidget(self.phone_id_input)

        self.save_btn = QPushButton("Save Settings")
        layout.addWidget(self.save_btn)
        layout.addStretch()

        self.tabs.addTab(self.config_tab, "Settings")

    def update_ui(self):
        if not self.bot.running:
            self.status_bar.setText("System Stopped | Connected: False")
            return

        # 1. Update Account Info
        info = self.bot.get_account_summary()
        if info:
            self.acc_name_label.setText(f"Account: {info['name']} ({'Demo' if info['demo'] else 'Real'})")
            self.balance_label.setText(f"Balance: ${info['balance']:.2f}")
            self.equity_label.setText(f"Equity: ${info['equity']:.2f}")
            self.profit_today_label.setText(f"Profit Today: ${self.bot.db.get_daily_profit():.2f}")
            self.status_bar.setText(f"System Running | Connected: True")
            if info['demo']:
                self.acc_name_label.setStyleSheet("color: #3498db; font-weight: bold;")
            else:
                self.acc_name_label.setStyleSheet("color: #e67e22; font-weight: bold;")

        # 2. Update Watchlist Table
        self.update_watchlist_table()

        # 3. Update Positions Table
        self.update_positions_table()

        # 4. Update Chart if visible
        if self.tabs.currentIndex() == 2: # Chart Tab
            self.update_chart()

    def update_chart(self):
        selected = self.watchlist_table.selectedItems()
        if not selected: return
        symbol = selected[0].text()

        # Fetch M5 data for plotting
        df = self.bot.mt5.get_candles(symbol, "M5", 100)
        if df is not None:
            self.plot_widget.clear()
            x = np.arange(len(df))
            y = df['close'].values
            self.plot_widget.plot(x, y, pen=pg.mkPen('y', width=2))
            self.plot_widget.setTitle(f"Live M5 Chart: {symbol}")

    def update_watchlist_table(self):
        # Create a snapshot to avoid RuntimeError: dictionary changed size during iteration
        data_snapshot = dict(self.bot.watchlist_data)
        self.watchlist_table.setRowCount(len(data_snapshot))
        for row, (symbol, vals) in enumerate(data_snapshot.items()):
            self.watchlist_table.setItem(row, 0, QTableWidgetItem(symbol))
            self.watchlist_table.setItem(row, 1, QTableWidgetItem(str(vals.get('trend', 'N/A'))))
            self.watchlist_table.setItem(row, 2, QTableWidgetItem(str(vals.get('rsi', 'N/A'))))
            self.watchlist_table.setItem(row, 3, QTableWidgetItem(str(vals.get('atr', 'N/A'))))
            self.watchlist_table.setItem(row, 4, QTableWidgetItem(str(vals.get('spread', 'N/A'))))

            sig_item = QTableWidgetItem(str(vals.get('signal', 'SCANNING')))
            if vals.get('signal') == "BUY": sig_item.setForeground(Qt.GlobalColor.green)
            elif vals.get('signal') == "SELL": sig_item.setForeground(Qt.GlobalColor.red)
            self.watchlist_table.setItem(row, 5, sig_item)

    def update_positions_table(self):
        positions = self.bot.mt5.get_positions()
        self.positions_table.setRowCount(len(positions))
        for row, pos in enumerate(positions):
            self.positions_table.setItem(row, 0, QTableWidgetItem(str(pos.ticket)))
            self.positions_table.setItem(row, 1, QTableWidgetItem(pos.symbol))
            p_type = "BUY" if pos.type == mt5.ORDER_TYPE_BUY else "SELL"
            self.positions_table.setItem(row, 2, QTableWidgetItem(p_type))

            profit_item = QTableWidgetItem(f"{pos.profit:.2f}")
            if pos.profit > 0: profit_item.setForeground(Qt.GlobalColor.green)
            elif pos.profit < 0: profit_item.setForeground(Qt.GlobalColor.red)
            self.positions_table.setItem(row, 3, profit_item)

if __name__ == "__main__":
    # For testing UI standalone
    app = QApplication(sys.argv)
    class Dummy:
        def __init__(self):
            self.running = False
            self.watchlist_data = {}
            self.mt5 = None
            self.db = None
        def get_account_summary(self): return None
    window = TradingBotGUI(Dummy())
    window.show()
    sys.exit(app.exec())
