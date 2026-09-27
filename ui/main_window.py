import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
from PIL import Image, ImageTk
import os
import sys
import time
import threading
import numpy as np

# Ensure project root is in sys.path when running ui/main_window.py directly
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from core.mt5_connector import connect_to_mt5, is_connected as is_mt5_connected, get_account_details
from database.db_manager import DatabaseLogger
from strategy.grid_bot import GridBot, REFERENCE_PRICES, get_pip_value
from ui.chart_data import MarketDataManager

# Set CustomTkinter global theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Theme Palette inspired by image 1.jpg
BG_DARK = "#0B0E14"          # Deep background
HEADER_BG = "#111622"        # Top bar
CARD_BG = "#151B28"          # Panel card background
CARD_BG_ALT = "#121722"      # Alternative card background
BORDER_COLOR = "#1F283B"     # Card border
ACCENT_BLUE = "#00D2FF"      # Cyan glow
ACCENT_GREEN = "#00E676"     # Neon Green (Bull / Buy)
ACCENT_GREEN_HOVER = "#00C853"
ACCENT_RED = "#FF3D71"       # Neon Red (Bear / Sell)
ACCENT_RED_HOVER = "#D50000"
TEXT_MUTED = "#8290A4"       # Subtitle text
TEXT_LIGHT = "#E2E8F0"       # High contrast text

PAIRS_LIST = ["EUR/USD", "GBP/JPY", "BTC/USD", "ETH/USD", "XAU/USD", "OIL/WTI"]

class TradingApp:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("TRADING PLATFORM - Multi-Pair Grid Trading Manager")
        self.root.geometry("1400x900")
        self.root.minsize(1180, 780)
        self.root.configure(fg_color=BG_DARK)

        # Core logic managers
        self.db_logger = DatabaseLogger()
        self.market_data = MarketDataManager()
        self.bots = {} # { "EURUSD": GridBot instance }
        self.active_symbol = "EUR/USD"
        self.filter_symbol = "ALL"
        self.active_timeframe = "1m"
        self.current_live_price = REFERENCE_PRICES.get("EURUSD", 1.08520)
        
        # Check MT5 connection
        self.mt5_online = is_mt5_connected()
        self.account_info = get_account_details()

        # Build UI
        self.load_assets()
        self.setup_ui()
        
        # Start background timer loops for ticks, chart updates, and database logs
        self.running_app = True
        self.update_live_ticks()
        self.update_logs_loop()

    def load_assets(self):
        """Loads logo and visual assets."""
        logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Image 2.png")
        self.logo_image = None
        if os.path.exists(logo_path):
            try:
                pil_img = Image.open(logo_path)
                self.logo_image = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(110, 36))
            except Exception as e:
                print(f"Could not load logo: {e}")

    def setup_ui(self):
        # 1. Top Navigation Bar
        self.create_header()

        # 2. Asset Switcher Tabs Bar
        self.create_tabs_bar()

        # 3. Main Workspace (Left Rail + Center Trading Deck + Right Watchlist)
        self.workspace_frame = ctk.CTkFrame(self.root, fg_color=BG_DARK, corner_radius=0)
        self.workspace_frame.pack(fill="both", expand=True, padx=12, pady=(6, 6))

        # Left Quick Icon Rail
        self.create_left_rail(self.workspace_frame)

        # Center Area (Chart + Execution Deck)
        self.center_frame = ctk.CTkFrame(self.workspace_frame, fg_color="transparent")
        self.center_frame.pack(side="left", fill="both", expand=True, padx=(8, 8))

        self.create_chart_header(self.center_frame)
        self.create_chart_canvas(self.center_frame)
        self.create_trading_deck(self.center_frame)

        # Right Sidebar (Trading Market Watchlist)
        self.create_watchlist_sidebar(self.workspace_frame)

        # 4. Bottom Panel: Live Trade Logs
        self.create_trade_logs_panel()

        # 5. Bottom Status Bar
        self.create_status_bar()

    # ================= TOP HEADER =================
    def create_header(self):
        header = ctk.CTkFrame(self.root, fg_color=HEADER_BG, height=64, corner_radius=0,
                              border_width=1, border_color=BORDER_COLOR)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        # Left: Bull & Bear Logo + Branding
        brand_frame = ctk.CTkFrame(header, fg_color="transparent")
        brand_frame.pack(side="left", padx=16, pady=8)

        if self.logo_image:
            logo_lbl = ctk.CTkLabel(brand_frame, image=self.logo_image, text="")
            logo_lbl.pack(side="left", padx=(0, 10))

        title_box = ctk.CTkFrame(brand_frame, fg_color="transparent")
        title_box.pack(side="left")

        title_lbl = ctk.CTkLabel(title_box, text="TRADING PLATFORM", 
                                 font=ctk.CTkFont(family="Segoe UI", size=17, weight="bold"),
                                 text_color="#FFFFFF")
        title_lbl.pack(anchor="w")

        sub_lbl = ctk.CTkLabel(title_box, text="MULTI-PAIR GRID MANAGER • UI / UX KIT", 
                               font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
                               text_color=ACCENT_BLUE)
        sub_lbl.pack(anchor="w")

        # Center: Search & Navigation Items
        nav_frame = ctk.CTkFrame(header, fg_color="transparent")
        nav_frame.pack(side="left", expand=True)

        self.search_entry = ctk.CTkEntry(nav_frame, placeholder_text="🔍 Search market, asset, ticket...",
                                         width=230, height=32, corner_radius=16,
                                         fg_color="#182030", border_color=BORDER_COLOR,
                                         text_color=TEXT_LIGHT, font=ctk.CTkFont(size=11))
        self.search_entry.pack(side="left", padx=15)

        for nav_item in ["HOME", "ABOUT", "SERVICE", "CONTACTS"]:
            btn = ctk.CTkButton(nav_frame, text=nav_item, width=68, height=28,
                                fg_color="transparent", hover_color="#1F283B",
                                text_color=TEXT_MUTED, font=ctk.CTkFont(size=11, weight="bold"))
            btn.pack(side="left", padx=3)

        # Right: Balance, User Profile & Status Badges
        right_frame = ctk.CTkFrame(header, fg_color="transparent")
        right_frame.pack(side="right", padx=16)

        # Engine mode badge
        self.engine_badge = ctk.CTkLabel(right_frame, 
                                         text="● MT5 LIVE" if self.mt5_online else "● DEMO ENGINE",
                                         fg_color="#182A20" if self.mt5_online else "#252030",
                                         text_color=ACCENT_GREEN if self.mt5_online else "#D19A66",
                                         corner_radius=12, width=95, height=26,
                                         font=ctk.CTkFont(size=10, weight="bold"))
        self.engine_badge.pack(side="left", padx=6)

        # Balance Card
        bal = self.account_info.get("balance", 5367.50)
        curr = self.account_info.get("currency", "USD")
        self.balance_lbl = ctk.CTkLabel(right_frame, 
                                        text=f"Balance:  ${bal:,.2f} {curr}",
                                        fg_color="#142B24", text_color=ACCENT_GREEN,
                                        corner_radius=14, width=155, height=32,
                                        font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"))
        self.balance_lbl.pack(side="left", padx=6)

        # User Avatar button
        user_btn = ctk.CTkButton(right_frame, text="👤 Trader", width=75, height=32,
                                 corner_radius=16, fg_color="#1A2234", hover_color="#243048",
                                 text_color="#FFFFFF", font=ctk.CTkFont(size=11, weight="bold"))
        user_btn.pack(side="left", padx=6)

    # ================= TABS BAR =================
    def create_tabs_bar(self):
        tabs_frame = ctk.CTkFrame(self.root, fg_color=HEADER_BG, height=44, corner_radius=0,
                                  border_width=1, border_color=BORDER_COLOR)
        tabs_frame.pack(fill="x", padx=0, pady=(0, 4))
        tabs_frame.pack_propagate(False)

        inner = ctk.CTkFrame(tabs_frame, fg_color="transparent")
        inner.pack(side="left", padx=16, pady=6)

        self.tab_buttons = {}
        for pair in PAIRS_LIST:
            is_active = (pair == self.active_symbol)
            btn = ctk.CTkButton(inner, text=pair, width=95, height=30,
                                corner_radius=15,
                                fg_color="#1E2A40" if is_active else "transparent",
                                hover_color="#23324E",
                                text_color=ACCENT_BLUE if is_active else TEXT_MUTED,
                                border_width=1 if is_active else 0,
                                border_color=ACCENT_BLUE if is_active else HEADER_BG,
                                font=ctk.CTkFont(size=11, weight="bold"),
                                command=lambda p=pair: self.switch_symbol(p))
            btn.pack(side="left", padx=4)
            self.tab_buttons[pair] = btn

        # Plus button
        add_btn = ctk.CTkButton(inner, text="+", width=30, height=30, corner_radius=15,
                                fg_color="#182030", hover_color="#243048",
                                text_color=TEXT_MUTED, font=ctk.CTkFont(size=14, weight="bold"),
                                command=self.add_custom_pair_prompt)
        add_btn.pack(side="left", padx=6)

    # ================= LEFT QUICK RAIL =================
    def create_left_rail(self, parent):
        rail = ctk.CTkFrame(parent, fg_color=CARD_BG, width=54, corner_radius=10,
                            border_width=1, border_color=BORDER_COLOR)
        rail.pack(side="left", fill="y", padx=(0, 6))
        rail.pack_propagate(False)

        icons = [("📊", "Dashboard"), ("⚡", "Grid Bot"), ("📈", "Analytics"), 
                 ("📋", "Trade Logs"), ("⚙️", "Settings")]
        
        for i, (ic, label) in enumerate(icons):
            btn = ctk.CTkButton(rail, text=ic, width=40, height=40, corner_radius=8,
                                fg_color="#1E2A40" if i == 0 else "transparent",
                                hover_color="#23324E",
                                text_color="#FFFFFF", font=ctk.CTkFont(size=16))
            btn.pack(pady=8, padx=6)

    # ================= CHART TOP BANNER =================
    def create_chart_header(self, parent):
        hdr = ctk.CTkFrame(parent, fg_color=CARD_BG, height=52, corner_radius=10,
                           border_width=1, border_color=BORDER_COLOR)
        hdr.pack(fill="x", pady=(0, 6))
        hdr.pack_propagate(False)

        # Symbol & Current Price
        left = ctk.CTkFrame(hdr, fg_color="transparent")
        left.pack(side="left", padx=14, pady=8)

        self.chart_symbol_lbl = ctk.CTkLabel(left, text=self.active_symbol,
                                             font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
                                             text_color="#FFFFFF")
        self.chart_symbol_lbl.pack(side="left", padx=(0, 10))

        self.price_badge = ctk.CTkLabel(left, text=f"{self.current_live_price:.5f}",
                                        font=ctk.CTkFont(family="Consolas", size=16, weight="bold"),
                                        text_color=ACCENT_GREEN)
        self.price_badge.pack(side="left", padx=(0, 10))

        self.change_badge = ctk.CTkLabel(left, text="+0.45% ▲",
                                         fg_color="#142B24", text_color=ACCENT_GREEN,
                                         corner_radius=10, width=72, height=24,
                                         font=ctk.CTkFont(size=11, weight="bold"))
        self.change_badge.pack(side="left")

        # Stats info
        self.stats_lbl = ctk.CTkLabel(hdr, text="H: 1.08920  |  L: 1.08110  |  Vol: 142.8M",
                                      font=ctk.CTkFont(size=11), text_color=TEXT_MUTED)
        self.stats_lbl.pack(side="left", padx=20)

        # Timeframe selectors
        tf_frame = ctk.CTkFrame(hdr, fg_color="transparent")
        tf_frame.pack(side="right", padx=14)

        self.tf_buttons = {}
        for tf in ["1m", "5m", "15m", "1h", "4h", "1D"]:
            is_sel = (tf == self.active_timeframe)
            b = ctk.CTkButton(tf_frame, text=tf, width=38, height=26, corner_radius=6,
                              fg_color="#202C42" if is_sel else "transparent",
                              hover_color="#2A3955",
                              text_color=ACCENT_BLUE if is_sel else TEXT_MUTED,
                              font=ctk.CTkFont(size=10, weight="bold"),
                              command=lambda t=tf: self.switch_timeframe(t))
            b.pack(side="left", padx=2)
            self.tf_buttons[tf] = b

    # ================= MATPLOTLIB DARK CANDLESTICK CHART =================
    def create_chart_canvas(self, parent):
        chart_card = ctk.CTkFrame(parent, fg_color=CARD_BG, corner_radius=10,
                                  border_width=1, border_color=BORDER_COLOR)
        chart_card.pack(fill="both", expand=True, pady=(0, 6))

        # Matplotlib Figure configured with deep dark palette
        self.fig = Figure(figsize=(8, 3.8), facecolor=CARD_BG, dpi=100)
        self.fig.subplots_adjust(left=0.06, right=0.96, top=0.94, bottom=0.12, hspace=0.15)
        
        # Grid: Top 75% for Candlesticks & Levels, Bottom 25% for Volume
        self.ax_chart = self.fig.add_axes([0.06, 0.28, 0.90, 0.66], facecolor="#0E121A")
        self.ax_vol = self.fig.add_axes([0.06, 0.10, 0.90, 0.15], facecolor="#0E121A", sharex=self.ax_chart)

        self.canvas = FigureCanvasTkAgg(self.fig, master=chart_card)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(fill="both", expand=True, padx=8, pady=8)

        self.render_chart()

    def render_chart(self):
        """Draws dark candlesticks, MA overlay, volume, and active grid orders."""
        self.ax_chart.clear()
        self.ax_vol.clear()

        candles = self.market_data.get_candles(self.active_symbol)
        if not candles:
            return

        n = len(candles)
        indices = list(range(n))
        closes = [c["close"] for c in candles]

        # Draw Candlesticks
        for i, c in enumerate(candles):
            is_bull = c["close"] >= c["open"]
            color = ACCENT_GREEN if is_bull else ACCENT_RED
            
            # High-Low Wick
            self.ax_chart.vlines(i, c["low"], c["high"], color=color, linewidth=1.2, alpha=0.85)
            # Body rectangle
            body_bottom = min(c["open"], c["close"])
            body_height = max(abs(c["close"] - c["open"]), (c["high"] - c["low"]) * 0.04)
            self.ax_chart.bar(i, body_height, bottom=body_bottom, color=color, width=0.68, edgecolor=color)
            
            # Volume bar
            self.ax_vol.bar(i, c["volume"], color=color, width=0.68, alpha=0.5)

        # 9-period Exponential Moving Average overlay
        if n >= 9:
            weights = np.exp(np.linspace(-1., 0., 9))
            weights /= weights.sum()
            ma = np.convolve(closes, weights, mode='valid')
            ma_x = indices[len(indices) - len(ma):]
            self.ax_chart.plot(ma_x, ma, color=ACCENT_BLUE, linewidth=1.4, alpha=0.9, label="EMA 9")

        # Current price horizontal reference line
        cur_price = closes[-1]
        self.ax_chart.axhline(cur_price, color="#FFFFFF", linestyle=":", linewidth=1.0, alpha=0.6)
        self.ax_chart.text(n - 1, cur_price, f"  {cur_price:.5f}", color="#FFFFFF", 
                           fontsize=9, weight="bold", verticalalignment="center")

        # Draw Grid Bot Levels if bot is active!
        clean_sym = self.active_symbol.replace("/", "")
        bot = self.bots.get(clean_sym)
        if bot and bot.is_alive():
            for buy_p in bot.grid_levels.get("buy_limits", []):
                self.ax_chart.axhline(buy_p, color=ACCENT_GREEN, linestyle="--", linewidth=1.1, alpha=0.7)
                self.ax_chart.text(0, buy_p, f" BUY LIMIT {buy_p:.5f}", color=ACCENT_GREEN, fontsize=8)
            for sell_p in bot.grid_levels.get("sell_limits", []):
                self.ax_chart.axhline(sell_p, color=ACCENT_RED, linestyle="--", linewidth=1.1, alpha=0.7)
                self.ax_chart.text(0, sell_p, f" SELL LIMIT {sell_p:.5f}", color=ACCENT_RED, fontsize=8)

        # Styling aesthetics
        for ax in [self.ax_chart, self.ax_vol]:
            ax.set_facecolor("#0D1118")
            ax.tick_params(colors=TEXT_MUTED, labelsize=8)
            ax.grid(True, color="#1A2230", linestyle="--", linewidth=0.6, alpha=0.7)
            for spine in ax.spines.values():
                spine.set_color(BORDER_COLOR)

        self.ax_chart.xaxis.set_visible(False)
        self.ax_chart.yaxis.tick_right()
        self.ax_vol.yaxis.tick_right()
        self.ax_vol.set_ylim(bottom=0)

        self.canvas.draw_idle()

    # ================= TRADING DECK & BOT CONTROLLER =================
    def create_trading_deck(self, parent):
        deck = ctk.CTkFrame(parent, fg_color=CARD_BG, height=128, corner_radius=10,
                            border_width=1, border_color=BORDER_COLOR)
        deck.pack(fill="x", pady=(0, 6))
        deck.pack_propagate(False)

        # Section 1: Instant BUY / SELL Buttons
        action_box = ctk.CTkFrame(deck, fg_color="transparent")
        action_box.pack(side="left", padx=16, pady=12)

        self.btn_buy = ctk.CTkButton(action_box, text="BUY ▲", width=125, height=44,
                                     corner_radius=8, fg_color=ACCENT_GREEN,
                                     hover_color=ACCENT_GREEN_HOVER,
                                     text_color="#00240E", font=ctk.CTkFont(size=14, weight="bold"),
                                     command=lambda: self.execute_manual_trade("BUY"))
        self.btn_buy.pack(side="left", padx=6)

        self.btn_sell = ctk.CTkButton(action_box, text="SELL ▼", width=125, height=44,
                                      corner_radius=8, fg_color=ACCENT_RED,
                                      hover_color=ACCENT_RED_HOVER,
                                      text_color="#FFFFFF", font=ctk.CTkFont(size=14, weight="bold"),
                                      command=lambda: self.execute_manual_trade("SELL"))
        self.btn_sell.pack(side="left", padx=6)

        # Section 2: Parameters (Lot Size, Spacing, Levels)
        params_box = ctk.CTkFrame(deck, fg_color="transparent")
        params_box.pack(side="left", expand=True, padx=10)

        # Lot Size
        c1 = ctk.CTkFrame(params_box, fg_color="transparent")
        c1.pack(side="left", padx=10)
        ctk.CTkLabel(c1, text="Lot Size", font=ctk.CTkFont(size=10, weight="bold"), 
                     text_color=TEXT_MUTED).pack(anchor="w")
        self.lot_var = tk.StringVar(value="0.01")
        self.entry_lot = ctk.CTkEntry(c1, textvariable=self.lot_var, width=75, height=32,
                                      fg_color="#182030", border_color=BORDER_COLOR,
                                      text_color="#FFFFFF", font=ctk.CTkFont(size=12))
        self.entry_lot.pack(pady=2)

        # Spacing
        c2 = ctk.CTkFrame(params_box, fg_color="transparent")
        c2.pack(side="left", padx=10)
        ctk.CTkLabel(c2, text="Spacing (pips)", font=ctk.CTkFont(size=10, weight="bold"), 
                     text_color=TEXT_MUTED).pack(anchor="w")
        self.pips_var = tk.StringVar(value="10")
        self.entry_pips = ctk.CTkEntry(c2, textvariable=self.pips_var, width=80, height=32,
                                       fg_color="#182030", border_color=BORDER_COLOR,
                                       text_color="#FFFFFF", font=ctk.CTkFont(size=12))
        self.entry_pips.pack(pady=2)

        # Grid Levels
        c3 = ctk.CTkFrame(params_box, fg_color="transparent")
        c3.pack(side="left", padx=10)
        ctk.CTkLabel(c3, text="Grid Levels", font=ctk.CTkFont(size=10, weight="bold"), 
                     text_color=TEXT_MUTED).pack(anchor="w")
        self.levels_var = tk.StringVar(value="3")
        self.entry_levels = ctk.CTkEntry(c3, textvariable=self.levels_var, width=70, height=32,
                                         fg_color="#182030", border_color=BORDER_COLOR,
                                         text_color="#FFFFFF", font=ctk.CTkFont(size=12))
        self.entry_levels.pack(pady=2)

        # Section 3: Start / Stop Bot
        bot_ctrl = ctk.CTkFrame(deck, fg_color="transparent")
        bot_ctrl.pack(side="right", padx=16, pady=12)

        self.bot_status_badge = ctk.CTkLabel(bot_ctrl, text="● BOT IDLE", width=120, height=22,
                                             fg_color="#202738", text_color=TEXT_MUTED,
                                             corner_radius=10, font=ctk.CTkFont(size=10, weight="bold"))
        self.bot_status_badge.pack(pady=(0, 6))

        btn_row = ctk.CTkFrame(bot_ctrl, fg_color="transparent")
        btn_row.pack()

        self.btn_start_bot = ctk.CTkButton(btn_row, text="START BOT", width=110, height=38,
                                           corner_radius=8, fg_color="#107C41",
                                           hover_color="#159650",
                                           text_color="#FFFFFF", font=ctk.CTkFont(size=12, weight="bold"),
                                           command=self.on_start_bot)
        self.btn_start_bot.pack(side="left", padx=4)

        self.btn_stop_bot = ctk.CTkButton(btn_row, text="STOP BOT", width=100, height=38,
                                          corner_radius=8, fg_color="#441E26",
                                          hover_color=ACCENT_RED, state="disabled",
                                          text_color=TEXT_MUTED, font=ctk.CTkFont(size=12, weight="bold"),
                                          command=self.on_stop_bot)
        self.btn_stop_bot.pack(side="left", padx=4)

    # ================= RIGHT WATCHLIST SIDEBAR =================
    def create_watchlist_sidebar(self, parent):
        side = ctk.CTkFrame(parent, fg_color=CARD_BG, width=285, corner_radius=10,
                            border_width=1, border_color=BORDER_COLOR)
        side.pack(side="right", fill="y", padx=(0, 0))
        side.pack_propagate(False)

        # Title
        hdr = ctk.CTkFrame(side, fg_color="transparent", height=44)
        hdr.pack(fill="x", padx=14, pady=10)
        ctk.CTkLabel(hdr, text="Trading market", 
                     font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                     text_color="#FFFFFF").pack(side="left")
        ctk.CTkLabel(hdr, text="🔔 🔍", font=ctk.CTkFont(size=12), text_color=TEXT_MUTED).pack(side="right")

        # Watchlist Scrollable items
        self.watchlist_rows = {}
        for p in PAIRS_LIST:
            card = ctk.CTkFrame(side, fg_color="#121722", corner_radius=8,
                                border_width=1, border_color="#1C2433")
            card.pack(fill="x", padx=10, pady=4)

            # Click to select pair
            card.bind("<Button-1>", lambda e, sym=p: self.switch_symbol(sym))

            row_top = ctk.CTkFrame(card, fg_color="transparent")
            row_top.pack(fill="x", padx=10, pady=(6, 2))
            row_top.bind("<Button-1>", lambda e, sym=p: self.switch_symbol(sym))

            sym_lbl = ctk.CTkLabel(row_top, text=p, font=ctk.CTkFont(size=12, weight="bold"), text_color="#FFFFFF")
            sym_lbl.pack(side="left")
            sym_lbl.bind("<Button-1>", lambda e, sym=p: self.switch_symbol(sym))

            clean = p.replace("/", "")
            ref_p = REFERENCE_PRICES.get(clean, 100.0)
            p_lbl = ctk.CTkLabel(row_top, text=f"{ref_p:.4f}" if ref_p < 10 else f"{ref_p:,.2f}",
                                 font=ctk.CTkFont(size=11, weight="bold"), text_color=ACCENT_GREEN)
            p_lbl.pack(side="right")
            p_lbl.bind("<Button-1>", lambda e, sym=p: self.switch_symbol(sym))

            row_bot = ctk.CTkFrame(card, fg_color="transparent")
            row_bot.pack(fill="x", padx=10, pady=(0, 6))
            row_bot.bind("<Button-1>", lambda e, sym=p: self.switch_symbol(sym))

            cat_text = "Forex" if "/" in p and "USD" in p and "BTC" not in p else ("Crypto" if "BTC" in p or "ETH" in p else "Commodity")
            cat_lbl = ctk.CTkLabel(row_bot, text=cat_text, font=ctk.CTkFont(size=9), text_color=TEXT_MUTED)
            cat_lbl.pack(side="left")
            cat_lbl.bind("<Button-1>", lambda e, sym=p: self.switch_symbol(sym))

            chg_lbl = ctk.CTkLabel(row_bot, text="+0.32%", font=ctk.CTkFont(size=9, weight="bold"), text_color=ACCENT_GREEN)
            chg_lbl.pack(side="right")
            chg_lbl.bind("<Button-1>", lambda e, sym=p: self.switch_symbol(sym))

            self.watchlist_rows[p] = {"price": p_lbl, "change": chg_lbl, "card": card}

        # Mini summary card at the bottom of watchlist
        promo_card = ctk.CTkFrame(side, fg_color="#182234", corner_radius=8, border_width=1, border_color=ACCENT_BLUE)
        promo_card.pack(fill="x", side="bottom", padx=10, pady=12)

        ctk.CTkLabel(promo_card, text="⚡ AUTO GRID ENGINE", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=ACCENT_BLUE).pack(pady=(8, 2))
        ctk.CTkLabel(promo_card, text="Multi-threaded asynchronous\norder execution with MySQL sync.",
                     font=ctk.CTkFont(size=9), text_color=TEXT_MUTED).pack(pady=(0, 8))

    # ================= BOTTOM PANEL: LIVE TRADE LOGS =================
    def create_trade_logs_panel(self):
        panel = ctk.CTkFrame(self.root, fg_color=CARD_BG, height=195, corner_radius=10,
                             border_width=1, border_color=BORDER_COLOR)
        panel.pack(fill="x", padx=12, pady=(0, 4))
        panel.pack_propagate(False)

        # Header with Controls
        top_bar = ctk.CTkFrame(panel, fg_color="transparent")
        top_bar.pack(fill="x", padx=14, pady=(8, 4))

        title = ctk.CTkLabel(top_bar, text="Live Trade Logs  (MySQL: grid_trading_db.trade_logs)",
                             font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                             text_color="#FFFFFF")
        title.pack(side="left")

        self.stats_counter_lbl = ctk.CTkLabel(top_bar, text="Total Orders: 0  |  Volume: 0.00",
                                              font=ctk.CTkFont(size=11), text_color=ACCENT_BLUE)
        self.stats_counter_lbl.pack(side="left", padx=20)

        # Filter Pills & Buttons
        btn_box = ctk.CTkFrame(top_bar, fg_color="transparent")
        btn_box.pack(side="right")

        self.btn_filter_all = ctk.CTkButton(btn_box, text="All Pairs", width=70, height=24,
                                            corner_radius=6, fg_color="#202C42", hover_color="#2A3955",
                                            text_color=ACCENT_BLUE, font=ctk.CTkFont(size=10, weight="bold"),
                                            command=lambda: self.set_log_filter("ALL"))
        self.btn_filter_all.pack(side="left", padx=3)

        self.btn_filter_cur = ctk.CTkButton(btn_box, text="Active Pair", width=80, height=24,
                                            corner_radius=6, fg_color="transparent", hover_color="#2A3955",
                                            text_color=TEXT_MUTED, font=ctk.CTkFont(size=10, weight="bold"),
                                            command=lambda: self.set_log_filter("ACTIVE"))
        self.btn_filter_cur.pack(side="left", padx=3)

        refresh_btn = ctk.CTkButton(btn_box, text="🔄 Refresh", width=75, height=24,
                                    corner_radius=6, fg_color="#182436", hover_color="#24344E",
                                    text_color=TEXT_LIGHT, font=ctk.CTkFont(size=10, weight="bold"),
                                    command=self.update_logs_now)
        refresh_btn.pack(side="left", padx=3)

        clear_btn = ctk.CTkButton(btn_box, text="🗑️ Clear", width=65, height=24,
                                  corner_radius=6, fg_color="#36181E", hover_color=ACCENT_RED,
                                  text_color=TEXT_LIGHT, font=ctk.CTkFont(size=10, weight="bold"),
                                  command=self.clear_logs_prompt)
        clear_btn.pack(side="left", padx=3)

        # Modern Dark Themed Treeview
        tree_container = tk.Frame(panel, bg="#121722")
        tree_container.pack(fill="both", expand=True, padx=12, pady=(2, 8))

        columns = ("id", "ticket", "symbol", "type", "volume", "price", "status", "timestamp")
        
        # Configure TTK Style for sleek dark theme
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("DarkTree.Treeview",
                        background="#0F131C",
                        foreground="#D6E0EE",
                        fieldbackground="#0F131C",
                        bordercolor=BORDER_COLOR,
                        borderwidth=0,
                        rowheight=24,
                        font=("Segoe UI", 9))
        style.configure("DarkTree.Treeview.Heading",
                        background="#182030",
                        foreground="#8EA1B9",
                        relief="flat",
                        font=("Segoe UI", 9, "bold"))
        style.map("DarkTree.Treeview",
                  background=[("selected", "#1D283E")],
                  foreground=[("selected", "#FFFFFF")])

        self.tree = ttk.Treeview(tree_container, columns=columns, show="headings",
                                 style="DarkTree.Treeview", selectmode="browse")

        col_defs = [
            ("id", "ID", 45, "center"),
            ("ticket", "Ticket #", 90, "center"),
            ("symbol", "Symbol", 85, "center"),
            ("type", "Order Type", 110, "center"),
            ("volume", "Volume", 65, "center"),
            ("price", "Price", 90, "center"),
            ("status", "Status", 90, "center"),
            ("timestamp", "Timestamp", 145, "center"),
        ]

        for cid, head, width, align in col_defs:
            self.tree.heading(cid, text=head)
            self.tree.column(cid, width=width, anchor=align)

        # Scrollbar
        sb = ttk.Scrollbar(tree_container, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill="both", expand=True)

    # ================= STATUS BAR =================
    def create_status_bar(self):
        sbar = ctk.CTkFrame(self.root, fg_color=HEADER_BG, height=26, corner_radius=0,
                            border_width=1, border_color=BORDER_COLOR)
        sbar.pack(fill="x", side="bottom")
        sbar.pack_propagate(False)

        # MySQL Status
        db_dot = ctk.CTkLabel(sbar, text="● MySQL: Connected (localhost:3306 / grid_trading_db)",
                              font=ctk.CTkFont(size=9, weight="bold"), text_color=ACCENT_GREEN)
        db_dot.pack(side="left", padx=14)

        # MT5 Status
        mt5_text = f"● MT5 IPC: Active ({self.account_info.get('server', 'Demo')})" if self.mt5_online else "● MT5 IPC: Offline (Simulator Active)"
        mt5_color = ACCENT_GREEN if self.mt5_online else "#D19A66"
        self.mt5_status_lbl = ctk.CTkLabel(sbar, text=mt5_text, font=ctk.CTkFont(size=9, weight="bold"), text_color=mt5_color)
        self.mt5_status_lbl.pack(side="left", padx=16)

        # Copyright / Version
        ver_lbl = ctk.CTkLabel(sbar, text="Multi-Pair Grid Platform v2.5 • Final Project",
                               font=ctk.CTkFont(size=9), text_color=TEXT_MUTED)
        ver_lbl.pack(side="right", padx=14)

    # ================= EVENT HANDLERS & LOGIC =================
    def switch_symbol(self, symbol):
        """Switches active symbol across the application."""
        self.active_symbol = symbol
        clean = symbol.replace("/", "")
        self.current_live_price = REFERENCE_PRICES.get(clean, 1.08520)
        
        # Update tab styling
        for p, btn in self.tab_buttons.items():
            is_active = (p == symbol)
            btn.configure(fg_color="#1E2A40" if is_active else "transparent",
                          text_color=ACCENT_BLUE if is_active else TEXT_MUTED,
                          border_width=1 if is_active else 0,
                          border_color=ACCENT_BLUE if is_active else HEADER_BG)
            
        # Update chart header
        self.chart_symbol_lbl.configure(text=symbol)
        self.price_badge.configure(text=f"{self.current_live_price:.5f}" if self.current_live_price < 10 else f"{self.current_live_price:,.2f}")
        
        # Update bot button states
        self.update_bot_ui_state()

        # Re-render chart
        self.render_chart()

        # Refresh logs if filter is active
        if self.filter_symbol != "ALL":
            self.update_logs_now()

    def switch_timeframe(self, tf):
        self.active_timeframe = tf
        for t, btn in self.tf_buttons.items():
            is_sel = (t == tf)
            btn.configure(fg_color="#202C42" if is_sel else "transparent",
                          text_color=ACCENT_BLUE if is_sel else TEXT_MUTED)
        self.render_chart()

    def set_log_filter(self, mode):
        self.filter_symbol = "ALL" if mode == "ALL" else self.active_symbol.replace("/", "")
        self.btn_filter_all.configure(fg_color="#202C42" if mode == "ALL" else "transparent",
                                      text_color=ACCENT_BLUE if mode == "ALL" else TEXT_MUTED)
        self.btn_filter_cur.configure(fg_color="#202C42" if mode != "ALL" else "transparent",
                                      text_color=ACCENT_BLUE if mode != "ALL" else TEXT_MUTED)
        self.update_logs_now()

    def execute_manual_trade(self, order_type):
        """Executes instant manual BUY or SELL order."""
        clean = self.active_symbol.replace("/", "")
        try:
            lot = float(self.lot_var.get())
        except ValueError:
            lot = 0.01

        # Use active bot if present, otherwise create temporary broker agent
        bot = self.bots.get(clean)
        if not bot:
            bot = GridBot(clean, lot, 10, 3, self.db_logger, simulation_mode=not self.mt5_online)

        ticket, price = bot.place_manual_order(order_type, lot)
        self.update_logs_now()
        
        # Visual feedback flash
        orig_color = ACCENT_GREEN if order_type == "BUY" else ACCENT_RED
        btn = self.btn_buy if order_type == "BUY" else self.btn_sell
        btn.configure(text=f"✓ PLACED!")
        self.root.after(800, lambda: btn.configure(text=f"{order_type} {'▲' if order_type == 'BUY' else '▼'}"))

    def on_start_bot(self):
        clean = self.active_symbol.replace("/", "")
        if clean in self.bots and self.bots[clean].is_alive():
            messagebox.showinfo("Bot Status", f"Grid bot for {self.active_symbol} is already active.")
            return

        try:
            lot = float(self.lot_var.get())
            pips = int(self.pips_var.get())
            levels = int(self.levels_var.get())
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter valid numeric values for Lot, Spacing, and Levels.")
            return

        # Start Bot thread
        bot = GridBot(clean, lot, pips, levels, self.db_logger, simulation_mode=not self.mt5_online)
        bot.start()
        self.bots[clean] = bot

        self.update_bot_ui_state()
        self.render_chart()
        self.update_logs_now()

    def on_stop_bot(self):
        clean = self.active_symbol.replace("/", "")
        if clean in self.bots:
            self.bots[clean].stop()
            self.root.after(400, lambda: self._remove_bot(clean))

    def _remove_bot(self, clean):
        if clean in self.bots:
            self.bots[clean].join(timeout=0.8)
            del self.bots[clean]
        self.update_bot_ui_state()
        self.render_chart()
        self.update_logs_now()

    def update_bot_ui_state(self):
        clean = self.active_symbol.replace("/", "")
        is_running = clean in self.bots and self.bots[clean].is_alive()

        if is_running:
            self.bot_status_badge.configure(text="● BOT ACTIVE", fg_color="#142B24", text_color=ACCENT_GREEN)
            self.btn_start_bot.configure(state="disabled", fg_color="#1E3326")
            self.btn_stop_bot.configure(state="normal", fg_color=ACCENT_RED, text_color="#FFFFFF")
        else:
            self.bot_status_badge.configure(text="● BOT IDLE", fg_color="#202738", text_color=TEXT_MUTED)
            self.btn_start_bot.configure(state="normal", fg_color="#107C41")
            self.btn_stop_bot.configure(state="disabled", fg_color="#441E26", text_color=TEXT_MUTED)

    def update_live_ticks(self):
        """Continuously streams ticks and refreshes watchlist & active chart."""
        if not self.running_app:
            return

        clean = self.active_symbol.replace("/", "")
        bot = self.bots.get(clean)
        live_p = bot.get_live_price() if (bot and bot.is_alive()) else None
        
        # Update chart tick
        new_price = self.market_data.update_tick(self.active_symbol, live_p)
        self.current_live_price = new_price
        
        # Update badge
        txt = f"{new_price:.5f}" if new_price < 10 else f"{new_price:,.2f}"
        self.price_badge.configure(text=txt)

        # Update watchlist prices
        for sym, row in self.watchlist_rows.items():
            wp = self.market_data.update_tick(sym)
            row["price"].configure(text=f"{wp:.4f}" if wp < 10 else f"{wp:,.2f}")

        # Re-render chart smoothly every 2.5 seconds
        self.render_chart()

        # Schedule next tick loop
        self.root.after(1800, self.update_live_ticks)

    def update_logs_now(self):
        sym_arg = None if self.filter_symbol == "ALL" else self.filter_symbol
        logs = self.db_logger.fetch_recent_logs(symbol=sym_arg, limit=50)

        # Clear existing rows
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Insert updated rows
        for row in logs:
            self.tree.insert("", "end", values=(
                row["id"], row["ticket"], row["symbol"], row["order_type"],
                f"{row['volume']:.2f}", f"{row['price']:.5f}", row["status"], row["timestamp"]
            ))

        # Update stats counter
        stats = self.db_logger.get_summary_stats()
        tot = stats.get("total_trades", 0)
        vol = stats.get("total_volume", 0.0)
        self.stats_counter_lbl.configure(text=f"Total Orders: {tot}  |  Volume: {vol:.2f} lots")

    def update_logs_loop(self):
        if not self.running_app:
            return
        self.update_logs_now()
        self.root.after(3000, self.update_logs_loop)

    def clear_logs_prompt(self):
        if messagebox.askyesno("Clear Logs", "Are you sure you want to clear all trade logs from MySQL?"):
            self.db_logger.clear_logs()
            self.update_logs_now()

    def add_custom_pair_prompt(self):
        dialog = ctk.CTkInputDialog(text="Enter Pair Symbol (e.g. AUDUSD, USDJPY, SOLUSD):", title="Add New Pair")
        val = dialog.get_input()
        if val and len(val.strip()) >= 3:
            sym = val.strip().upper()
            formatted = f"{sym[:3]}/{sym[3:]}" if len(sym) == 6 else sym
            if formatted not in PAIRS_LIST:
                PAIRS_LIST.append(formatted)
                self.switch_symbol(formatted)

    def on_closing(self):
        self.running_app = False
        for clean, bot in self.bots.items():
            bot.stop()
            bot.join(timeout=0.5)
        self.root.destroy()

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()


if __name__ == "__main__":
    app = TradingApp()
    app.run()
