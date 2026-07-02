import sys
import json
import os
import math
import requests

from PySide6.QtCore import Qt, QTimer, QDate, QRectF
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QFont
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QDialog,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QDoubleSpinBox,
    QHBoxLayout,
    QDateEdit,
    QHeaderView,
    QMessageBox,
    QFrame,
    QGridLayout,
    QProgressBar,
    QTabWidget,
    QComboBox,
    QSizePolicy,
)


COIN_INFO = {
    "bitcoin": {"name": "Bitcoin", "icon": "₿", "color": "#f59e0b", "split": 0.50},
    "ethereum": {"name": "Ethereum", "icon": "Ξ", "color": "#6366f1", "split": 0.30},
    "solana": {"name": "Solana", "icon": "◎", "color": "#10b981", "split": 0.10},
    "chainlink": {"name": "Chainlink", "icon": "⬡", "color": "#2563eb", "split": 0.10},
}

COINS = {info["name"]: coin_id for coin_id, info in COIN_INFO.items()}
BUY_SPLIT = {coin_id: info["split"] for coin_id, info in COIN_INFO.items()}

TARGET_CRYPTO = 0.50
API_URL = "https://api.coingecko.com/api/v3/simple/price"

POSITIVE_COLOR = "#16a34a"
NEGATIVE_COLOR = "#dc2626"
NEUTRAL_COLOR = "#64748b"


if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PORTFOLIO_FILE = os.path.join(BASE_DIR, "portfolio.json")


def money(value):
    return f"${value:,.2f}"


def eur_money(value):
    return f"€{value:,.2f}"


def percent(value):
    return f"{value:.2f}%"


def signed_money(value):
    if value > 0:
        return f"+${value:,.2f}"
    if value < 0:
        return f"-${abs(value):,.2f}"
    return "$0.00"


def signed_percent(value):
    if value > 0:
        return f"+{value:.2f}%"
    if value < 0:
        return f"-{abs(value):.2f}%"
    return "0.00%"


def safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


class MetricCard(QFrame):
    def __init__(self, title, accent_color="#2563eb"):
        super().__init__()
        self.setObjectName("metricCard")
        self.accent_color = accent_color
        self.setProperty("accent", accent_color)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(3)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("cardTitle")

        self.value_label = QLabel("-")
        self.value_label.setObjectName("cardValue")

        self.subtitle_label = QLabel("")
        self.subtitle_label.setObjectName("cardSubtitle")
        self.subtitle_label.setWordWrap(True)

        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        layout.addWidget(self.subtitle_label)

        self.setMinimumHeight(82)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_value(self, text):
        self.value_label.setText(text)

    def set_subtitle(self, text):
        self.subtitle_label.setText(text)

    def set_value_color(self, color):
        self.value_label.setStyleSheet(f"color: {color};")


class AllocationPieChart(QWidget):
    def __init__(self):
        super().__init__()
        self.crypto_value = 0.0
        self.usdc_value = 0.0
        self.dark_mode = False
        self.setMinimumHeight(215)

    def set_values(self, crypto_value, usdc_value):
        self.crypto_value = max(0.0, safe_float(crypto_value))
        self.usdc_value = max(0.0, safe_float(usdc_value))
        self.update()

    def set_theme(self, dark_mode):
        self.dark_mode = dark_mode
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        text_color = QColor("#e5e7eb" if self.dark_mode else "#0f172a")
        muted_color = QColor("#94a3b8" if self.dark_mode else "#64748b")
        crypto_color = QColor("#2563eb")
        usdc_color = QColor("#7c3aed")

        w = self.width()
        h = self.height()
        total = self.crypto_value + self.usdc_value

        painter.setPen(text_color)
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.drawText(12, 24, "Crypto / USDC Allocation")

        if total <= 0:
            painter.setPen(muted_color)
            painter.drawText(12, 58, "No portfolio data yet.")
            return

        crypto_pct = self.crypto_value / total * 100
        usdc_pct = self.usdc_value / total * 100

        outer_margin = 16
        top_margin = 44
        bottom_margin = 16
        legend_gap = 28
        legend_width = 170
        available_w = max(120, w - outer_margin * 2)
        available_h = max(100, h - top_margin - bottom_margin)

        pie_max_w = max(90, available_w - legend_width - legend_gap)
        pie_size = min(available_h, pie_max_w)
        pie_size = max(90, pie_size)

        rect_y = top_margin + max(0, (available_h - pie_size) / 2)
        rect = QRectF(outer_margin, rect_y, pie_size, pie_size)

        crypto_angle = int(round((self.crypto_value / total) * 360 * 16))
        start_angle = 90 * 16

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(crypto_color))
        painter.drawPie(rect, start_angle, -crypto_angle)

        painter.setBrush(QBrush(usdc_color))
        painter.drawPie(rect, start_angle - crypto_angle, -(360 * 16 - crypto_angle))

        inner = QRectF(rect.x() + pie_size * 0.30, rect.y() + pie_size * 0.30, pie_size * 0.40, pie_size * 0.40)
        painter.setBrush(QBrush(QColor("#0f172a" if self.dark_mode else "#ffffff")))
        painter.drawEllipse(inner)

        center_font = QFont()
        center_font.setPointSize(10)
        center_font.setBold(True)
        painter.setFont(center_font)
        painter.setPen(text_color)
        painter.drawText(inner, Qt.AlignCenter, f"{crypto_pct:.1f}%\nCrypto")

        legend_x = int(min(w - legend_width, rect.right() + legend_gap))
        legend_y = int(top_margin + max(16, (available_h - 72) / 2))
        painter.setFont(QFont())

        self._draw_legend_item(painter, legend_x, legend_y, crypto_color, "Crypto", money(self.crypto_value), f"{crypto_pct:.1f}%", text_color, muted_color)
        self._draw_legend_item(painter, legend_x, legend_y + 58, usdc_color, "USDC", money(self.usdc_value), f"{usdc_pct:.1f}%", text_color, muted_color)

    def _draw_legend_item(self, painter, x, y, color, name, value, pct, text_color, muted_color):
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(color))
        painter.drawRoundedRect(x, y - 12, 14, 14, 4, 4)

        label_font = QFont()
        label_font.setPointSize(10)
        label_font.setBold(True)
        painter.setFont(label_font)
        painter.setPen(text_color)
        painter.drawText(x + 24, y, name)

        detail_font = QFont()
        detail_font.setPointSize(9)
        painter.setFont(detail_font)
        painter.setPen(muted_color)
        painter.drawText(x + 24, y + 22, f"{value}  ·  {pct}")


class CoinBarChart(QWidget):
    def __init__(self):
        super().__init__()
        self.values = []
        self.dark_mode = False
        self.setMinimumHeight(215)

    def set_values(self, values):
        self.values = values
        self.update()

    def set_theme(self, dark_mode):
        self.dark_mode = dark_mode
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        text_color = QColor("#e5e7eb" if self.dark_mode else "#0f172a")
        muted_color = QColor("#94a3b8" if self.dark_mode else "#64748b")
        grid_color = QColor("#334155" if self.dark_mode else "#e2e8f0")

        painter.setPen(text_color)
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.drawText(12, 24, "Value by Coin")

        if not self.values:
            painter.setPen(muted_color)
            painter.drawText(12, 58, "No coin values to display yet.")
            return

        max_value = max(value for _, _, value, _ in self.values)
        if max_value <= 0:
            painter.setPen(muted_color)
            painter.drawText(12, 58, "No coin values to display yet.")
            return

        left = 110
        top = 52
        bar_h = 22
        gap = 16
        right_margin = 14
        value_area = 82
        chart_w = max(70, self.width() - left - value_area - right_margin)

        label_font = QFont()
        label_font.setPointSize(9)
        painter.setFont(label_font)
        fm = painter.fontMetrics()

        for idx, (name, icon, value, color_hex) in enumerate(self.values):
            y = top + idx * (bar_h + gap)
            ratio = value / max_value
            bar_w = int(chart_w * ratio)

            painter.setPen(text_color)
            painter.drawText(12, y + 16, f"{icon} {name}")

            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(grid_color))
            painter.drawRoundedRect(left, y, chart_w, bar_h, 7, 7)

            painter.setBrush(QBrush(QColor(color_hex)))
            painter.drawRoundedRect(left, y, bar_w, bar_h, 7, 7)

            value_text = money(value)
            text_w = fm.horizontalAdvance(value_text)
            text_x = self.width() - right_margin - text_w
            painter.setPen(text_color)
            painter.drawText(text_x, y + 16, value_text)


class CoinPriceAverageChart(QWidget):
    def __init__(self, coin_id, info):
        super().__init__()
        self.coin_id = coin_id
        self.info = info
        self.records = []
        self.current_price = 0.0
        self.dark_mode = False
        self.setMinimumHeight(165)

    def set_data(self, records, current_price):
        self.records = list(records or [])
        self.current_price = safe_float(current_price)
        self.update()

    def set_theme(self, dark_mode):
        self.dark_mode = dark_mode
        self.update()

    def _format_axis_money(self, value):
        value = safe_float(value)
        if abs(value) >= 1_000_000:
            return f"${value / 1_000_000:.1f}M"
        if abs(value) >= 1_000:
            return f"${value / 1_000:.1f}k"
        if abs(value) >= 10:
            return f"${value:.0f}"
        return f"${value:.2f}"

    def _build_series(self):
        cleaned = []
        for record in sorted(self.records, key=lambda item: str(item.get("date", ""))):
            usdc = safe_float(record.get("usdc", 0))
            amount = safe_float(record.get("amount", 0))
            if usdc <= 0 or amount <= 0:
                continue
            cleaned.append((str(record.get("date", "")), usdc, amount))

        if not cleaned:
            return [], [], []

        labels = []
        price_series = []
        average_series = []
        total_usdc = 0.0
        total_amount = 0.0

        for date_text, usdc, amount in cleaned:
            total_usdc += usdc
            total_amount += amount
            transaction_price = usdc / amount
            cumulative_average = total_usdc / total_amount if total_amount > 0 else 0.0
            labels.append(date_text[5:] if len(date_text) >= 10 else date_text)
            price_series.append(transaction_price)
            average_series.append(cumulative_average)

        if self.current_price > 0:
            labels.append("Now")
            price_series.append(self.current_price)
            average_series.append(average_series[-1])

        return labels, price_series, average_series

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        text_color = QColor("#e5e7eb" if self.dark_mode else "#0f172a")
        muted_color = QColor("#94a3b8" if self.dark_mode else "#64748b")
        grid_color = QColor("#334155" if self.dark_mode else "#e2e8f0")
        price_color = QColor(self.info.get("color", "#2563eb"))
        average_color = QColor("#f97316" if self.dark_mode else "#dc2626")

        painter.setPen(text_color)
        title_font = QFont()
        title_font.setPointSize(11)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.drawText(12, 23, f"{self.info['icon']} {self.info['name']} · Price vs avg buy")

        labels, price_series, average_series = self._build_series()
        if not labels:
            painter.setPen(muted_color)
            painter.setFont(QFont())
            painter.drawText(12, 54, "No buy records yet.")
            return

        latest_average = average_series[-1]
        detail = f"Current: {money(self.current_price) if self.current_price > 0 else '-'}  ·  Avg buy: {money(latest_average)}"
        detail_font = QFont()
        detail_font.setPointSize(8)
        painter.setFont(detail_font)
        painter.setPen(muted_color)
        painter.drawText(12, 42, detail)

        all_values = price_series + average_series
        min_value = min(all_values)
        max_value = max(all_values)
        if math.isclose(min_value, max_value):
            padding = max(1.0, abs(max_value) * 0.05)
        else:
            padding = (max_value - min_value) * 0.10
        y_min = max(0.0, min_value - padding)
        y_max = max_value + padding
        if math.isclose(y_min, y_max):
            y_max = y_min + 1.0

        left = 58
        right = 14
        top = 56
        bottom = 28
        chart_w = max(40, self.width() - left - right)
        chart_h = max(35, self.height() - top - bottom)

        painter.setFont(QFont())
        for i in range(4):
            ratio = i / 3
            y = top + chart_h - ratio * chart_h
            value = y_min + ratio * (y_max - y_min)
            painter.setPen(QPen(grid_color, 1))
            painter.drawLine(left, int(y), left + chart_w, int(y))
            painter.setPen(muted_color)
            painter.drawText(8, int(y) + 4, self._format_axis_money(value))

        def point_for(index, value):
            x = left + (chart_w * index / max(1, len(labels) - 1))
            y = top + chart_h - ((value - y_min) / (y_max - y_min)) * chart_h
            return x, y

        def draw_series(values, color, width=2):
            pen = QPen(color, width)
            painter.setPen(pen)
            previous = None
            for idx, value in enumerate(values):
                x, y = point_for(idx, value)
                if previous is not None:
                    painter.drawLine(int(previous[0]), int(previous[1]), int(x), int(y))
                previous = (x, y)
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.NoPen)
            for idx, value in enumerate(values):
                x, y = point_for(idx, value)
                painter.drawEllipse(QRectF(x - 3, y - 3, 6, 6))

        draw_series(price_series, price_color, 2)
        draw_series(average_series, average_color, 2)

        painter.setPen(muted_color)
        label_font = QFont()
        label_font.setPointSize(8)
        painter.setFont(label_font)
        painter.drawText(left, self.height() - 8, labels[0])
        painter.drawText(left + chart_w - 34, self.height() - 8, labels[-1])

        legend_y = 54
        legend_x = max(left + 5, self.width() - 165)
        self._draw_legend_item(painter, legend_x, legend_y, price_color, "Price", text_color)
        self._draw_legend_item(painter, legend_x + 72, legend_y, average_color, "Avg buy", text_color)

    def _draw_legend_item(self, painter, x, y, color, text, text_color):
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(color))
        painter.drawRoundedRect(x, y - 9, 11, 11, 3, 3)
        painter.setPen(text_color)
        legend_font = QFont()
        legend_font.setPointSize(8)
        painter.setFont(legend_font)
        painter.drawText(x + 16, y + 1, text)


class CryptoDashboard(QWidget):
    def __init__(self):
        super().__init__()

        self.dark_mode = False
        self.setWindowTitle("DCA Shield Crypto Dashboard")
        self.resize(1240, 780)
        self.setMinimumSize(980, 680)

        self.prices = {}
        self.amount_inputs = {}
        self.price_avg_charts = {}
        self.portfolio_data = self.load_portfolio()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        header = QFrame()
        header.setObjectName("panel")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(14, 10, 14, 10)
        header_layout.setSpacing(10)

        title_box = QVBoxLayout()
        title = QLabel("DCA Shield Crypto Dashboard")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Ramin Crypto Dashboard")
        subtitle.setObjectName("pageSubtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.fetch_prices)
        self.refresh_button.setMinimumWidth(95)

        self.theme_button = QPushButton("Dark mode")
        self.theme_button.setCheckable(True)
        self.theme_button.toggled.connect(self.toggle_theme)
        self.theme_button.setMinimumWidth(105)

        header_layout.addLayout(title_box)
        header_layout.addStretch()
        header_layout.addWidget(self.refresh_button)
        header_layout.addWidget(self.theme_button)
        main_layout.addWidget(header)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("mainTabs")
        self.tabs.addTab(self.create_portfolio_tab(), "Portfolio")
        self.tabs.addTab(self.create_transactions_tab(), "Transactions")
        self.tabs.addTab(self.create_analytics_tab(), "Analytics")
        main_layout.addWidget(self.tabs)

        self.status = QLabel("Ready")
        self.status.setObjectName("statusLabel")
        main_layout.addWidget(self.status)

        self.apply_styles()

        self.sync_all_holdings_from_buy_records()
        self.save_portfolio()

        self.timer = QTimer()
        self.timer.timeout.connect(self.fetch_prices)
        self.timer.start(60000)

        self.fetch_prices()

    def create_portfolio_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        cards = QGridLayout()
        cards.setSpacing(10)

        self.total_value_card = MetricCard("Total value", "#2563eb")
        self.crypto_profit_card = MetricCard("Crypto P/L", "#ea580c")
        self.total_profit_card = MetricCard("Total P/L", "#0891b2")
        self.daily_change_card = MetricCard("24h crypto change", "#7c3aed")

        cards.addWidget(self.total_value_card, 0, 0)
        cards.addWidget(self.crypto_profit_card, 0, 1)
        cards.addWidget(self.total_profit_card, 0, 2)
        cards.addWidget(self.daily_change_card, 0, 3)
        layout.addLayout(cards)

        allocation_panel = QFrame()
        allocation_panel.setObjectName("panel")
        allocation_layout = QVBoxLayout(allocation_panel)
        allocation_layout.setContentsMargins(12, 10, 12, 10)
        allocation_layout.setSpacing(7)

        allocation_title = QLabel("Allocation")
        allocation_title.setObjectName("sectionTitle")
        self.allocation_label = QLabel("Crypto: $0.00 | USDC: $0.00")
        self.allocation_label.setObjectName("infoText")

        self.crypto_progress = QProgressBar()
        self.crypto_progress.setRange(0, 1000)
        self.crypto_progress.setFormat("Crypto 0.0%")
        self.crypto_progress.setObjectName("cryptoBar")
        self.crypto_progress.setMaximumHeight(18)

        self.usdc_progress = QProgressBar()
        self.usdc_progress.setRange(0, 1000)
        self.usdc_progress.setFormat("USDC 0.0%")
        self.usdc_progress.setObjectName("usdcBar")
        self.usdc_progress.setMaximumHeight(18)

        allocation_layout.addWidget(allocation_title)
        allocation_layout.addWidget(self.allocation_label)
        allocation_layout.addWidget(self.crypto_progress)
        allocation_layout.addWidget(self.usdc_progress)
        layout.addWidget(allocation_panel)

        self.table = QTableWidget()
        self.table.setRowCount(len(COIN_INFO))
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Coin", "Price", "Amount", "Value", "Avg Buy", "P/L USDC", "P/L %", "24h %"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(36)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setMaximumHeight(205)
        self.table.cellDoubleClicked.connect(self.open_transactions_from_row)

        holdings = self.portfolio_data.setdefault("holdings", {})
        for row, (coin_id, info) in enumerate(COIN_INFO.items()):
            self.table.setItem(row, 0, QTableWidgetItem(f"{info['icon']}  {info['name']}"))
            self.table.setItem(row, 1, QTableWidgetItem("Loading..."))
            self.table.setItem(row, 3, QTableWidgetItem("$0.00"))
            self.table.setItem(row, 4, QTableWidgetItem("-"))
            self.table.setItem(row, 5, QTableWidgetItem("-"))
            self.table.setItem(row, 6, QTableWidgetItem("-"))
            self.table.setItem(row, 7, QTableWidgetItem("Loading..."))

            amount_input = QDoubleSpinBox()
            amount_input.setDecimals(10)
            amount_input.setMaximum(100_000_000)
            amount_input.setValue(safe_float(holdings.get(coin_id, 0)))
            amount_input.setButtonSymbols(QDoubleSpinBox.NoButtons)
            amount_input.valueChanged.connect(self.calculate_portfolio)
            amount_input.valueChanged.connect(self.calculate_rebalance)
            amount_input.valueChanged.connect(self.save_portfolio)
            self.amount_inputs[coin_id] = amount_input
            self.table.setCellWidget(row, 2, amount_input)

        layout.addWidget(self.table)

        inputs_panel = QFrame()
        inputs_panel.setObjectName("panel")
        inputs_layout = QGridLayout(inputs_panel)
        inputs_layout.setContentsMargins(12, 10, 12, 10)
        inputs_layout.setHorizontalSpacing(12)
        inputs_layout.setVerticalSpacing(8)

        self.usdc_input = self.create_money_input(safe_float(self.portfolio_data.get("usdc", 0)), "$")
        self.usdc_input.valueChanged.connect(self.calculate_portfolio)
        self.usdc_input.valueChanged.connect(self.calculate_rebalance)
        self.usdc_input.valueChanged.connect(self.save_portfolio)

        self.total_invested_input = self.create_money_input(safe_float(self.portfolio_data.get("total_invested", 0)), "$")
        self.total_invested_input.valueChanged.connect(self.calculate_portfolio)
        self.total_invested_input.valueChanged.connect(self.save_portfolio)

        self.total_invested_eur_input = self.create_money_input(safe_float(self.portfolio_data.get("total_invested_eur", 0)), "€")
        self.total_invested_eur_input.valueChanged.connect(self.save_portfolio)

        inputs_layout.addWidget(self.make_field_label("USDC asset"), 0, 0)
        inputs_layout.addWidget(self.usdc_input, 0, 1)
        inputs_layout.addWidget(self.make_field_label("Total invested (USD/USDC)"), 0, 2)
        inputs_layout.addWidget(self.total_invested_input, 0, 3)
        inputs_layout.addWidget(self.make_field_label("EUR reference"), 0, 4)
        inputs_layout.addWidget(self.total_invested_eur_input, 0, 5)

        layout.addWidget(inputs_panel)

        rebalance_panel = QFrame()
        rebalance_panel.setObjectName("panel")
        rebalance_layout = QHBoxLayout(rebalance_panel)
        rebalance_layout.setContentsMargins(12, 10, 12, 10)
        rebalance_layout.setSpacing(10)

        self.rebalance_button = QPushButton("Rebalance")
        self.rebalance_button.clicked.connect(self.calculate_rebalance)
        self.rebalance_label = QLabel("Rebalance Suggestion: -")
        self.rebalance_label.setObjectName("rebalanceText")
        self.rebalance_label.setWordWrap(True)
        self.split_label = QLabel("Buy Split: -")
        self.split_label.setObjectName("infoText")
        self.split_label.setWordWrap(True)

        rebalance_layout.addWidget(self.rebalance_button)
        rebalance_layout.addWidget(self.rebalance_label, 2)
        rebalance_layout.addWidget(self.split_label, 3)
        layout.addWidget(rebalance_panel)

        return tab

    def create_transactions_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        top_panel = QFrame()
        top_panel.setObjectName("panel")
        top_layout = QHBoxLayout(top_panel)
        top_layout.setContentsMargins(12, 10, 12, 10)

        top_layout.addWidget(self.make_field_label("Coin"))
        self.transaction_coin_combo = QComboBox()
        for coin_id, info in COIN_INFO.items():
            self.transaction_coin_combo.addItem(f"{info['icon']}  {info['name']}", coin_id)
        self.transaction_coin_combo.currentIndexChanged.connect(self.refresh_transaction_table)
        top_layout.addWidget(self.transaction_coin_combo)
        top_layout.addStretch()
        layout.addWidget(top_panel)

        self.transaction_table = QTableWidget()
        self.transaction_table.setColumnCount(4)
        self.transaction_table.setHorizontalHeaderLabels(["Date", "USDC invested", "Coin amount", "Delete"])
        self.transaction_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.transaction_table.verticalHeader().setVisible(False)
        self.transaction_table.verticalHeader().setDefaultSectionSize(34)
        self.transaction_table.setAlternatingRowColors(True)
        layout.addWidget(self.transaction_table)

        add_panel = QFrame()
        add_panel.setObjectName("panel")
        add_layout = QHBoxLayout(add_panel)
        add_layout.setContentsMargins(12, 10, 12, 10)
        add_layout.setSpacing(10)

        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDate(QDate.currentDate())
        self.date_input.setDisplayFormat("yyyy-MM-dd")

        self.transaction_usdc_input = self.create_money_input(0, "$")
        self.transaction_amount_input = QDoubleSpinBox()
        self.transaction_amount_input.setDecimals(10)
        self.transaction_amount_input.setMaximum(100_000_000)
        self.transaction_amount_input.setButtonSymbols(QDoubleSpinBox.NoButtons)

        self.add_record_button = QPushButton("Add transaction")
        self.add_record_button.clicked.connect(self.add_transaction_record)

        add_layout.addWidget(self.make_field_label("Date"))
        add_layout.addWidget(self.date_input)
        add_layout.addWidget(self.make_field_label("USDC"))
        add_layout.addWidget(self.transaction_usdc_input)
        add_layout.addWidget(self.make_field_label("Amount"))
        add_layout.addWidget(self.transaction_amount_input)
        add_layout.addWidget(self.add_record_button)
        layout.addWidget(add_panel)

        self.transaction_summary_label = QLabel("No buy records yet.")
        self.transaction_summary_label.setObjectName("infoText")
        layout.addWidget(self.transaction_summary_label)

        # The combo box items are added before the signal is connected, so the
        # first transaction table needs one explicit refresh after the widgets exist.
        self.refresh_transaction_table()

        return tab

    def create_analytics_tab(self):
        tab = QWidget()
        layout = QGridLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        self.pie_panel = QFrame()
        self.pie_panel.setObjectName("panel")
        pie_layout = QVBoxLayout(self.pie_panel)
        pie_layout.setContentsMargins(10, 10, 10, 10)
        self.allocation_chart = AllocationPieChart()
        pie_layout.addWidget(self.allocation_chart)

        self.bar_panel = QFrame()
        self.bar_panel.setObjectName("panel")
        bar_layout = QVBoxLayout(self.bar_panel)
        bar_layout.setContentsMargins(10, 10, 10, 10)
        self.coin_bar_chart = CoinBarChart()
        bar_layout.addWidget(self.coin_bar_chart)

        layout.addWidget(self.pie_panel, 0, 0)
        layout.addWidget(self.bar_panel, 0, 1)

        chart_positions = [(1, 0), (1, 1), (2, 0), (2, 1)]
        for (coin_id, info), (row, column) in zip(COIN_INFO.items(), chart_positions):
            chart_panel = QFrame()
            chart_panel.setObjectName("panel")
            chart_layout = QVBoxLayout(chart_panel)
            chart_layout.setContentsMargins(10, 8, 10, 8)

            chart = CoinPriceAverageChart(coin_id, info)
            self.price_avg_charts[coin_id] = chart
            chart_layout.addWidget(chart)
            layout.addWidget(chart_panel, row, column)

        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)
        layout.setRowStretch(0, 1)
        layout.setRowStretch(1, 1)
        layout.setRowStretch(2, 1)

        return tab

    def make_field_label(self, text):
        label = QLabel(text)
        label.setObjectName("fieldLabel")
        return label

    def create_money_input(self, value, prefix):
        widget = QDoubleSpinBox()
        widget.setDecimals(2)
        widget.setMaximum(100_000_000)
        widget.setPrefix(prefix)
        widget.setValue(value)
        widget.setButtonSymbols(QDoubleSpinBox.NoButtons)
        return widget

    def apply_styles(self):
        if self.dark_mode:
            app_bg = "#020617"
            panel_bg = "#0f172a"
            panel_border = "#1e293b"
            text = "#e5e7eb"
            muted = "#94a3b8"
            input_bg = "#111827"
            input_border = "#334155"
            table_alt = "#111827"
            header_bg = "#1e293b"
            header_text = "#bfdbfe"
            selection = "#1d4ed8"
        else:
            app_bg = "#f8fafc"
            panel_bg = "#ffffff"
            panel_border = "#dbe3ef"
            text = "#0f172a"
            muted = "#64748b"
            input_bg = "#ffffff"
            input_border = "#cbd5e1"
            table_alt = "#f8fafc"
            header_bg = "#eff6ff"
            header_text = "#1e3a8a"
            selection = "#dbeafe"

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {app_bg};
                color: {text};
                font-size: 12px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }}
            QFrame#panel, QFrame#metricCard {{
                background: {panel_bg};
                border: 1px solid {panel_border};
                border-radius: 12px;
            }}
            QFrame#metricCard {{
                border-left: 5px solid #2563eb;
            }}
            QLabel#pageTitle {{
                font-size: 19px;
                font-weight: 800;
                color: {text};
            }}
            QLabel#pageSubtitle, QLabel#cardSubtitle, QLabel#statusLabel {{
                color: {muted};
                font-size: 11px;
            }}
            QLabel#cardTitle {{
                color: {muted};
                font-size: 10px;
                font-weight: 800;
                text-transform: uppercase;
            }}
            QLabel#cardValue {{
                color: {text};
                font-size: 17px;
                font-weight: 800;
            }}
            QLabel#sectionTitle {{
                color: {text};
                font-size: 14px;
                font-weight: 800;
            }}
            QLabel#fieldLabel {{
                color: {text};
                font-size: 12px;
                font-weight: 700;
            }}
            QLabel#infoText, QLabel#rebalanceText {{
                color: {text};
                font-size: 12px;
            }}
            QPushButton {{
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 7px 12px;
                font-weight: 700;
            }}
            QPushButton:hover {{ background-color: #1d4ed8; }}
            QPushButton:checked {{ background-color: #7c3aed; }}
            QPushButton:disabled {{ background-color: #94a3b8; }}
            QDoubleSpinBox, QDateEdit, QComboBox {{
                background: {input_bg};
                color: {text};
                border: 1px solid {input_border};
                border-radius: 8px;
                padding: 5px 8px;
                min-height: 26px;
            }}
            QTabWidget::pane {{
                border: 1px solid {panel_border};
                border-radius: 10px;
                top: -1px;
            }}
            QTabBar::tab {{
                background: {panel_bg};
                color: {muted};
                border: 1px solid {panel_border};
                border-bottom: none;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                padding: 7px 16px;
                font-weight: 700;
            }}
            QTabBar::tab:selected {{
                color: white;
                background: #2563eb;
            }}
            QTableWidget {{
                background: {panel_bg};
                color: {text};
                border: 1px solid {panel_border};
                border-radius: 10px;
                gridline-color: {panel_border};
                alternate-background-color: {table_alt};
                selection-background-color: {selection};
                selection-color: {text};
            }}
            QHeaderView::section {{
                background-color: {header_bg};
                color: {header_text};
                padding: 6px;
                border: none;
                border-bottom: 1px solid {panel_border};
                font-weight: 800;
            }}
            QProgressBar {{
                border: 1px solid {input_border};
                border-radius: 8px;
                background: {header_bg};
                text-align: center;
                font-weight: 800;
                color: {text};
            }}
            QProgressBar#cryptoBar::chunk {{
                background-color: #2563eb;
                border-radius: 8px;
            }}
            QProgressBar#usdcBar::chunk {{
                background-color: #7c3aed;
                border-radius: 8px;
            }}
        """)

        if hasattr(self, "allocation_chart"):
            self.allocation_chart.set_theme(self.dark_mode)
        if hasattr(self, "coin_bar_chart"):
            self.coin_bar_chart.set_theme(self.dark_mode)
        if hasattr(self, "price_avg_charts"):
            for chart in self.price_avg_charts.values():
                chart.set_theme(self.dark_mode)

    def toggle_theme(self, checked):
        self.dark_mode = checked
        self.theme_button.setText("Light mode" if checked else "Dark mode")
        self.apply_styles()
        self.calculate_portfolio()

    def default_portfolio(self):
        return {
            "holdings": {coin_id: 0.0 for coin_id in COIN_INFO.keys()},
            "usdc": 0.0,
            "total_invested": 0.0,
            "total_invested_eur": 0.0,
            "buy_records": {coin_id: [] for coin_id in COIN_INFO.keys()},
        }

    def normalize_portfolio(self, data):
        default = self.default_portfolio()

        if not isinstance(data, dict):
            return default

        if "holdings" not in data:
            old_data = data
            data = default
            for coin_id in COIN_INFO.keys():
                data["holdings"][coin_id] = safe_float(old_data.get(coin_id, 0))
            data["usdc"] = safe_float(old_data.get("usdc", 0))
            data["total_invested"] = safe_float(old_data.get("total_invested", 0))
            data["total_invested_eur"] = safe_float(old_data.get("total_invested_eur", 0))
            old_buy_records = old_data.get("buy_records", {})
            if isinstance(old_buy_records, dict):
                data["buy_records"] = old_buy_records
        else:
            data.setdefault("holdings", {})
            data.setdefault("buy_records", {})
            data["usdc"] = safe_float(data.get("usdc", 0))
            data["total_invested"] = safe_float(data.get("total_invested", 0))
            data["total_invested_eur"] = safe_float(data.get("total_invested_eur", 0))

        for coin_id in COIN_INFO.keys():
            data["holdings"][coin_id] = safe_float(data["holdings"].get(coin_id, 0))
            records = data["buy_records"].get(coin_id, [])
            if not isinstance(records, list):
                records = []
            cleaned_records = []
            for record in records:
                if not isinstance(record, dict):
                    continue
                cleaned_records.append({
                    "date": str(record.get("date", "")),
                    "usdc": safe_float(record.get("usdc", 0)),
                    "amount": safe_float(record.get("amount", 0)),
                })
            data["buy_records"][coin_id] = cleaned_records

        return data

    def load_portfolio(self):
        if not os.path.exists(PORTFOLIO_FILE):
            return self.default_portfolio()
        try:
            with open(PORTFOLIO_FILE, "r", encoding="utf-8") as file:
                data = json.load(file)
            return self.normalize_portfolio(data)
        except Exception:
            return self.default_portfolio()

    def save_portfolio(self):
        if not hasattr(self, "usdc_input"):
            return

        data = self.portfolio_data
        data["holdings"] = {}
        for coin_id, widget in self.amount_inputs.items():
            data["holdings"][coin_id] = widget.value()

        data["usdc"] = self.usdc_input.value()
        data["total_invested"] = self.total_invested_input.value()
        data["total_invested_eur"] = self.total_invested_eur_input.value()

        data.setdefault("buy_records", {})
        for coin_id in COIN_INFO.keys():
            data["buy_records"].setdefault(coin_id, [])

        with open(PORTFOLIO_FILE, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)

    def fetch_prices(self):
        try:
            self.status.setText("Fetching prices...")
            self.refresh_button.setEnabled(False)

            ids = ",".join(COIN_INFO.keys())
            response = requests.get(
                API_URL,
                params={
                    "ids": ids,
                    "vs_currencies": "usd",
                    "include_24hr_change": "true",
                },
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            self.prices = data

            for row, coin_id in enumerate(COIN_INFO.keys()):
                if coin_id not in data:
                    continue
                price = safe_float(data[coin_id].get("usd", 0))
                change = safe_float(data[coin_id].get("usd_24h_change", 0))
                self.table.item(row, 1).setText(money(price))
                change_item = self.table.item(row, 7)
                change_item.setText(signed_percent(change))
                self.set_item_color(change_item, change)

            self.calculate_portfolio()
            self.calculate_rebalance()
            self.status.setText(f"Prices updated successfully · Portfolio file: {PORTFOLIO_FILE}")

        except Exception as error:
            self.status.setText(f"Error: {error}")

        finally:
            self.refresh_button.setEnabled(True)

    def set_item_color(self, item, value):
        if value > 0:
            item.setForeground(QColor(POSITIVE_COLOR))
        elif value < 0:
            item.setForeground(QColor(NEGATIVE_COLOR))
        else:
            item.setForeground(QColor(NEUTRAL_COLOR))

    def set_card_value_by_sign(self, card, value):
        if value > 0:
            card.set_value_color(POSITIVE_COLOR)
        elif value < 0:
            card.set_value_color(NEGATIVE_COLOR)
        else:
            card.set_value_color(NEUTRAL_COLOR)

    def get_buy_records(self, coin_id):
        return self.portfolio_data.setdefault("buy_records", {}).setdefault(coin_id, [])

    def get_recorded_amount(self, coin_id):
        return sum(safe_float(record.get("amount", 0)) for record in self.get_buy_records(coin_id))

    def get_buy_record_stats(self, coin_id):
        records = self.get_buy_records(coin_id)
        total_cost = sum(safe_float(record.get("usdc", 0)) for record in records)
        recorded_amount = sum(safe_float(record.get("amount", 0)) for record in records)
        avg_buy = total_cost / recorded_amount if recorded_amount > 0 else 0.0
        return total_cost, recorded_amount, avg_buy

    def sync_holding_from_buy_records(self, coin_id, force=False):
        records = self.get_buy_records(coin_id)
        if not records and not force:
            return

        recorded_amount = self.get_recorded_amount(coin_id)
        self.portfolio_data.setdefault("holdings", {})[coin_id] = recorded_amount

        widget = self.amount_inputs.get(coin_id)
        if widget is not None and abs(widget.value() - recorded_amount) > 1e-12:
            widget.blockSignals(True)
            widget.setValue(recorded_amount)
            widget.blockSignals(False)

    def sync_all_holdings_from_buy_records(self):
        for coin_id in COIN_INFO.keys():
            self.sync_holding_from_buy_records(coin_id, force=False)

    def get_coin_values(self):
        values = []
        for coin_id, info in COIN_INFO.items():
            amount = self.amount_inputs[coin_id].value()
            price = safe_float(self.prices.get(coin_id, {}).get("usd", 0))
            values.append((coin_id, info["name"], info["icon"], amount * price, info["color"]))
        return values

    def get_crypto_total(self):
        crypto_total = 0.0

        for row, coin_id in enumerate(COIN_INFO.keys()):
            amount = self.amount_inputs[coin_id].value()
            price = safe_float(self.prices.get(coin_id, {}).get("usd", 0))
            value = amount * price
            crypto_total += value

            self.table.item(row, 3).setText(money(value))

            total_cost, recorded_amount, avg_buy = self.get_buy_record_stats(coin_id)
            self.table.item(row, 4).setText(money(avg_buy) if avg_buy > 0 else "-")

            profit_item = self.table.item(row, 5)
            profit_percent_item = self.table.item(row, 6)

            if total_cost > 0:
                profit = value - total_cost
                profit_percent = (profit / total_cost) * 100
                profit_item.setText(signed_money(profit))
                profit_percent_item.setText(signed_percent(profit_percent))
                self.set_item_color(profit_item, profit)
                self.set_item_color(profit_percent_item, profit_percent)
            else:
                profit_item.setText("-")
                profit_percent_item.setText("-")
                self.set_item_color(profit_item, 0)
                self.set_item_color(profit_percent_item, 0)

        return crypto_total

    def get_crypto_invested_total(self):
        return sum(self.get_buy_record_stats(coin_id)[0] for coin_id in COIN_INFO.keys())

    def get_daily_crypto_change(self):
        current_total = 0.0
        previous_total = 0.0

        for coin_id in COIN_INFO.keys():
            amount = self.amount_inputs[coin_id].value()
            price = safe_float(self.prices.get(coin_id, {}).get("usd", 0))
            change_pct = safe_float(self.prices.get(coin_id, {}).get("usd_24h_change", 0))
            current_value = amount * price
            divisor = 1 + (change_pct / 100)
            previous_value = current_value / divisor if abs(divisor) > 1e-9 else current_value
            current_total += current_value
            previous_total += previous_value

        change_usd = current_total - previous_total
        change_pct = (change_usd / previous_total) * 100 if previous_total > 0 else 0.0
        return change_usd, change_pct

    def calculate_portfolio(self):
        crypto_total = self.get_crypto_total()
        crypto_invested = self.get_crypto_invested_total()
        usdc_total = self.usdc_input.value()
        total = crypto_total + usdc_total

        self.total_value_card.set_value(money(total))
        self.total_value_card.set_subtitle(f"Crypto {money(crypto_total)} · USDC {money(usdc_total)}")
        self.total_value_card.set_value_color("#2563eb")

        if total > 0:
            crypto_percent = (crypto_total / total) * 100
            usdc_percent = (usdc_total / total) * 100
        else:
            crypto_percent = 0.0
            usdc_percent = 0.0

        self.allocation_label.setText(
            f"Crypto: {money(crypto_total)} ({crypto_percent:.1f}%)  |  USDC: {money(usdc_total)} ({usdc_percent:.1f}%)  |  Target: 50/50"
        )
        self.crypto_progress.setValue(int(round(crypto_percent * 10)))
        self.crypto_progress.setFormat(f"Crypto {crypto_percent:.1f}%")
        self.usdc_progress.setValue(int(round(usdc_percent * 10)))
        self.usdc_progress.setFormat(f"USDC {usdc_percent:.1f}%")

        if crypto_invested > 0:
            crypto_profit = crypto_total - crypto_invested
            crypto_profit_percent = (crypto_profit / crypto_invested) * 100
            self.crypto_profit_card.set_value(f"{signed_money(crypto_profit)} ({signed_percent(crypto_profit_percent)})")
            self.crypto_profit_card.set_subtitle(f"Based on buy records: {money(crypto_invested)}")
            self.set_card_value_by_sign(self.crypto_profit_card, crypto_profit)
        else:
            self.crypto_profit_card.set_value("-")
            self.crypto_profit_card.set_subtitle("Add transactions to calculate crypto P/L")
            self.crypto_profit_card.set_value_color(NEUTRAL_COLOR)

        invested = self.total_invested_input.value()
        if invested > 0:
            total_profit = total - invested
            total_profit_percent = (total_profit / invested) * 100
            self.total_profit_card.set_value(f"{signed_money(total_profit)} ({signed_percent(total_profit_percent)})")
            self.total_profit_card.set_subtitle(f"Compared with total invested: {money(invested)}")
            self.set_card_value_by_sign(self.total_profit_card, total_profit)
        else:
            self.total_profit_card.set_value("-")
            self.total_profit_card.set_subtitle("Enter total invested capital")
            self.total_profit_card.set_value_color(NEUTRAL_COLOR)

        daily_usd, daily_pct = self.get_daily_crypto_change()
        self.daily_change_card.set_value(f"{signed_money(daily_usd)} ({signed_percent(daily_pct)})")
        self.daily_change_card.set_subtitle("Estimated from weighted 24h coin changes")
        self.set_card_value_by_sign(self.daily_change_card, daily_usd)

        if hasattr(self, "allocation_chart"):
            self.allocation_chart.set_values(crypto_total, usdc_total)
        if hasattr(self, "coin_bar_chart"):
            chart_values = [
                (name, icon, value, color)
                for _, name, icon, value, color in self.get_coin_values()
            ]
            self.coin_bar_chart.set_values(chart_values)

        if hasattr(self, "price_avg_charts"):
            for coin_id, chart in self.price_avg_charts.items():
                current_price = safe_float(self.prices.get(coin_id, {}).get("usd", 0))
                chart.set_data(self.get_buy_records(coin_id), current_price)

        if hasattr(self, "transaction_summary_label"):
            self.refresh_transaction_summary_only()

    def calculate_rebalance(self):
        crypto_total = self.get_crypto_total()
        usdc_total = self.usdc_input.value()
        total = crypto_total + usdc_total

        if total <= 0:
            self.rebalance_label.setText("Rebalance Suggestion: No portfolio data yet.")
            self.split_label.setText("Buy Split: -")
            return

        target_crypto_value = total * TARGET_CRYPTO
        amount_to_buy = target_crypto_value - crypto_total

        if amount_to_buy <= 0:
            self.rebalance_label.setText("Crypto is already at or above 50%. No USDC-to-crypto buy needed.")
            self.split_label.setText("Buy Split: -")
            return

        amount_to_buy = min(amount_to_buy, usdc_total)
        self.rebalance_label.setText(f"Buy {money(amount_to_buy)} crypto from USDC to move toward 50/50.")

        split_lines = []
        for coin_id, info in COIN_INFO.items():
            buy_usd = amount_to_buy * BUY_SPLIT[coin_id]
            price = safe_float(self.prices.get(coin_id, {}).get("usd", 0))
            if price > 0:
                coin_amount = buy_usd / price
                split_lines.append(f"{info['icon']} {info['name']}: {money(buy_usd)} → {coin_amount:.8f}")
            else:
                split_lines.append(f"{info['icon']} {info['name']}: {money(buy_usd)}")

        self.split_label.setText(" | ".join(split_lines))

    def current_transaction_coin_id(self):
        return self.transaction_coin_combo.currentData()

    def refresh_transaction_table(self):
        if not hasattr(self, "transaction_table"):
            return

        coin_id = self.current_transaction_coin_id()
        records = self.get_buy_records(coin_id)
        self.transaction_table.setRowCount(len(records))

        for row, record in enumerate(records):
            self.transaction_table.setItem(row, 0, QTableWidgetItem(str(record.get("date", ""))))
            self.transaction_table.setItem(row, 1, QTableWidgetItem(money(safe_float(record.get("usdc", 0)))))
            self.transaction_table.setItem(row, 2, QTableWidgetItem(f"{safe_float(record.get('amount', 0)):.10f}"))

            delete_button = QPushButton("Delete")
            delete_button.clicked.connect(lambda checked=False, r=row: self.delete_transaction_record(r))
            self.transaction_table.setCellWidget(row, 3, delete_button)

        self.transaction_table.resizeRowsToContents()
        self.refresh_transaction_summary_only()

    def refresh_transaction_summary_only(self):
        if not hasattr(self, "transaction_summary_label"):
            return
        coin_id = self.current_transaction_coin_id()
        if not coin_id:
            return
        info = COIN_INFO[coin_id]
        total_usdc, total_amount, avg_buy = self.get_buy_record_stats(coin_id)
        if total_amount > 0:
            self.transaction_summary_label.setText(
                f"{info['icon']} {info['name']} · Recorded cost: {money(total_usdc)} · Amount: {total_amount:.10f} · Average buy: {money(avg_buy)}"
            )
        else:
            self.transaction_summary_label.setText(f"{info['icon']} {info['name']} · No buy records yet.")

    def add_transaction_record(self):
        coin_id = self.current_transaction_coin_id()
        usdc = self.transaction_usdc_input.value()
        amount = self.transaction_amount_input.value()

        if usdc <= 0 or amount <= 0:
            QMessageBox.warning(self, "Invalid transaction", "USDC and coin amount must be greater than zero.")
            return

        record = {
            "date": self.date_input.date().toString("yyyy-MM-dd"),
            "usdc": usdc,
            "amount": amount,
        }
        self.get_buy_records(coin_id).append(record)
        self.sync_holding_from_buy_records(coin_id, force=True)
        self.transaction_usdc_input.setValue(0)
        self.transaction_amount_input.setValue(0)
        self.save_portfolio()
        self.refresh_transaction_table()
        self.calculate_portfolio()
        self.calculate_rebalance()

    def delete_transaction_record(self, row):
        coin_id = self.current_transaction_coin_id()
        records = self.get_buy_records(coin_id)
        if 0 <= row < len(records):
            del records[row]
            self.sync_holding_from_buy_records(coin_id, force=True)
            self.save_portfolio()
            self.refresh_transaction_table()
            self.calculate_portfolio()
            self.calculate_rebalance()

    def open_transactions_from_row(self, row, column):
        if row < 0 or row >= len(COIN_INFO):
            return
        self.transaction_coin_combo.setCurrentIndex(row)
        self.refresh_transaction_table()
        self.tabs.setCurrentIndex(1)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CryptoDashboard()
    window.show()
    sys.exit(app.exec())