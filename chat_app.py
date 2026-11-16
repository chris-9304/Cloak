#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║  CLOAK v2.0  //  ENCRYPTED P2P CHAT PROTOCOL           ║
║  Real LAN peer discovery + Fernet-encrypted TCP messaging    ║
║  Cyberpunk terminal UI inspired by EDGERUNNERS                ║
╚══════════════════════════════════════════════════════════════╝

Usage:
    python3 chat_app.py                     # port 5001
    python3 chat_app.py --port 5002         # custom TCP port
    python3 chat_app.py --name ALICE        # preset identity
"""

from __future__ import annotations

import argparse
import sys
import os
import socket
import time
import threading
import queue
import ipaddress
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from session import SecureSession
from network import (
    DiscoveryService,
    TCPListener,
    _get_local_ip,
    DEFAULT_TCP_PORT,
    DISCOVERY_PORT,
)
from peer import Peer, PeerManager


# ═══════════════════════════════════════════════════════════════════
#  EDGERUNNERS colour palette
# ═══════════════════════════════════════════════════════════════════
BG_DARK         = "#0a0a0f"      # deepest background
BG_PANEL        = "#0f0f18"      # panel / card background
BG_INPUT        = "#14141f"      # input fields
FG              = "#c8c8d0"      # primary text
FG_DIM          = "#9197aa"      # muted / secondary text
FG_BRIGHT       = "#e0e0e8"      # bright text
PINK            = "#e8f547"      # primary accent — signal yellow
PINK_DIM        = "#a0ab28"      # dimmed pink
GREEN           = "#49dfbb"      # neon green — status, online
GREEN_DIM       = "#009926"      # dimmed green
CYAN            = "#00e5ff"      # cyan for highlights
YELLOW          = "#ffcc00"      # warnings
RED             = "#ff2244"      # errors, danger
BORDER          = "#282d40"      # panel borders
BORDER_ACCENT   = "#35394b"      # muted border
FONT            = "Menlo" if sys.platform == "darwin" else "Consolas"
FONT_ALT        = "Courier"
CORNER_R        = 14             # rounded corner radius


# ═══════════════════════════════════════════════════════════════════
#  RoundedPanel — Canvas with rounded-rect background
# ═══════════════════════════════════════════════════════════════════

class RoundedPanel(tk.Canvas):
    """A canvas that draws a rounded rectangle behind an inner Frame."""

    def __init__(self, parent, bg_color=BG_PANEL, border_color=BORDER,
                 radius=CORNER_R, pad=14, **kw):
        p_bg = BG_DARK
        try:
            p_bg = parent.cget("bg")
        except Exception:
            pass
        super().__init__(parent, bg=p_bg, highlightthickness=0, **kw)
        self._bg = bg_color
        self._border = border_color
        self._r = radius
        self._pad = pad
        self._rid = None
        self._bid = None
        self.inner = tk.Frame(self, bg=bg_color)
        self._wid = self.create_window(0, 0, window=self.inner, anchor="nw")
        self.bind("<Configure>", self._redraw)

    def _redraw(self, _e=None):
        w, h, r = self.winfo_width(), self.winfo_height(), self._r
        if w < 2 * r or h < 2 * r:
            return
        if self._rid:
            self.delete(self._rid)
        if self._bid:
            self.delete(self._bid)
        # border rect (slightly larger)
        self._bid = self._rrect(0, 0, w, h, r, self._border)
        # fill rect
        self._rid = self._rrect(1, 1, w - 1, h - 1, r, self._bg)
        self.tag_lower(self._rid)
        self.tag_lower(self._bid)
        self.itemconfigure(self._wid, width=w - 2 * self._pad, height=h - 2 * self._pad)
        self.coords(self._wid, self._pad, self._pad)

    def _rrect(self, x1, y1, x2, y2, r, color):
        return self.create_polygon(
            x1+r, y1, x2-r, y1, x2, y1, x2, y1+r,
            x2, y2-r, x2, y2, x2-r, y2, x1+r, y2,
            x1, y2, x1, y2-r, x1, y1+r, x1, y1,
            smooth=True, fill=color, outline=color)


# ═══════════════════════════════════════════════════════════════════
#  CyberButton — neon-styled button on Canvas
# ═══════════════════════════════════════════════════════════════════

class CyberButton(tk.Canvas):
    def __init__(self, parent, text="", command=None,
                 bg_color=PINK, fg_color="#0a0a0f", hover_color=None,
                 disabled_bg="#282d40", disabled_fg="#9197aa",
                 font_cfg=(FONT, 10, "bold"), radius=8,
                 padx=16, pady=5, **kw):
        self._text = text
        self._cmd = command
        self._bg = bg_color
        self._fg = fg_color
        self._hover = hover_color or bg_color
        self._dis_bg = disabled_bg
        self._dis_fg = disabled_fg
        self._font = font_cfg
        self._r = radius
        self._enabled = True

        cw = int(len(text) * font_cfg[1] * 0.65 + 2 * padx)
        ch = int(font_cfg[1] * 2.0 + 2 * pady)

        p_bg = BG_DARK
        try:
            p_bg = parent.cget("bg")
        except Exception:
            pass
        super().__init__(parent, width=cw, height=ch, bg=p_bg,
                         highlightthickness=0, **kw)
        self.bind("<Configure>", self._draw)
        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)
        self.configure(takefocus=True)
        self.bind("<Button-1>", self._click)
        self.bind("<Return>", self._click)
        self.bind("<space>", self._click)
        self.bind("<FocusIn>", lambda e: self.configure(highlightthickness=2, highlightbackground=CYAN))
        self.bind("<FocusOut>", lambda e: self.configure(highlightthickness=0))

    def _draw(self, _e=None, fill=None, fg=None):
        self.delete("all")
        w, h, r = self.winfo_width(), self.winfo_height(), self._r
        if w < 4 or h < 4:
            return
        c = fill or (self._bg if self._enabled else self._dis_bg)
        t = fg or (self._fg if self._enabled else self._dis_fg)
        self.create_polygon(
            r,0, w-r,0, w,0, w,r, w,h-r, w,h,
            w-r,h, r,h, 0,h, 0,h-r, 0,r, 0,0,
            smooth=True, fill=c, outline=c)
        self.create_text(w//2, h//2, text=self._text, fill=t, font=self._font)

    def _enter(self, _e):
        if self._enabled:
            self._draw(fill=self._hover)

    def _leave(self, _e):
        self._draw()

    def _click(self, _e):
        if self._enabled and self._cmd:
            self._cmd()

    def set_enabled(self, v: bool):
        self._enabled = v
        self._draw()

    def set_text(self, t: str):
        self._text = t
        self._draw()


# ═══════════════════════════════════════════════════════════════════
#  Main Application
# ═══════════════════════════════════════════════════════════════════

class ChatApp:
    def __init__(self, root: tk.Tk, tcp_port=DEFAULT_TCP_PORT,
                 discovery_port=DISCOVERY_PORT, preset_name=""):
        self.root = root
        self.tcp_port = tcp_port
        self.discovery_port = discovery_port
        self.username = preset_name or ""
        self.password = ""
        self.peer_manager = PeerManager()
        self.connection: Optional[SecureSession] = None
        self.listener: Optional[TCPListener] = None
        self.discovery: Optional[DiscoveryService] = None
        self.local_ip = _get_local_ip()
        self._running = True
        self._session_start = time.time()
        self._scan_timer = None

        # Initialize UI components and setup the root window
        self._setup_root()

        self._events = queue.Queue()
        self._state = "disconnected"
        self._show_setup_screen()
        self.setup_name_var.set(self.username)
        self._poll_events()

    def _poll_events(self):
        if not self._running:
            return
        for _ in range(100):
            try:
                callback, args = self._events.get_nowait()
            except queue.Empty:
                break
            callback(*args)
        self.root.after(40, self._poll_events)

    def _post(self, callback, *args):
        if self._running:
            self._events.put((callback, args))

    # ── root config ─────────────────────────────────────────────────

    def _setup_root(self):
        self.root.title("CLOAK // ENCRYPTED P2P")
        self.root.geometry("1100x820")
        self.root.minsize(940, 760)
        self.root.configure(bg=BG_DARK)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(".", background=BG_DARK, foreground=FG)
        style.configure("Vertical.TScrollbar",
                        background=BG_PANEL, troughcolor=BG_DARK,
                        arrowcolor=FG_DIM, borderwidth=0)

    def _show_setup_screen(self):
        """Show the setup screen before the main chat interface."""
        # Clear the root window
        for widget in self.root.winfo_children():
            widget.destroy()

        # Create main setup frame
        setup_frame = tk.Frame(self.root, bg=BG_DARK)
        setup_frame.pack(fill=tk.BOTH, expand=True)
        setup_frame.grid_rowconfigure(0, weight=0)  # Title
        setup_frame.grid_rowconfigure(1, weight=0)  # Subtitle
        setup_frame.grid_rowconfigure(2, weight=0)  # Panel
        setup_frame.grid_rowconfigure(3, weight=1)  # Empty space at bottom

        # Title
        title_label = tk.Label(
            setup_frame,
            text="CLOAK",
            bg=BG_DARK,
            fg=PINK,
            font=(FONT, 24, "bold")
        )
        title_label.pack(pady=(65, 15))

        # Subtitle
        subtitle_label = tk.Label(
            setup_frame,
            text="ENCRYPTED P2P CHAT PROTOCOL",
            bg=BG_DARK,
            fg=FG_DIM,
            font=(FONT, 12)
        )
        subtitle_label.pack(pady=(0, 25))

        # Setup panel
        panel_frame = tk.Frame(setup_frame, bg=BG_PANEL, highlightbackground=BORDER, highlightthickness=1)
        panel_frame.pack(pady=20, padx=40, fill=tk.X, expand=False)

        # Username input
        tk.Label(
            panel_frame,
            text="CALLSIGN",
            bg=BG_PANEL,
            fg=FG_DIM,
            font=(FONT, 10)
        ).pack(anchor="w", pady=(20, 5), padx=20)

        self.setup_name_var = tk.StringVar()
        name_entry = tk.Entry(
            panel_frame,
            textvariable=self.setup_name_var,
            bg=BG_INPUT,
            fg=GREEN,
            insertbackground=GREEN,
            font=(FONT, 12),
            bd=0,
            highlightthickness=1,
            highlightcolor=PINK,
            highlightbackground=BORDER
        )
        name_entry.pack(fill=tk.X, ipady=5, pady=(0, 20), padx=20)
        name_entry.bind("<Return>", lambda e: self._setup_complete())

        # Password input
        tk.Label(
            panel_frame,
            text="ENCRYPTION KEY",
            bg=BG_PANEL,
            fg=FG_DIM,
            font=(FONT, 10)
        ).pack(anchor="w", pady=(0, 5), padx=20)

        self.setup_pass_var = tk.StringVar()
        pass_frame = tk.Frame(panel_frame, bg=BG_PANEL)
        pass_frame.pack(fill=tk.X, pady=(0, 20), padx=20)

        self.setup_pass_entry = tk.Entry(
            pass_frame,
            textvariable=self.setup_pass_var,
            show="█",
            bg=BG_INPUT,
            fg=PINK,
            insertbackground=PINK,
            font=(FONT, 12),
            bd=0,
            highlightthickness=1,
            highlightcolor=PINK,
            highlightbackground=BORDER
        )
        self.setup_pass_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5)
        self.setup_pass_entry.bind("<Return>", lambda e: self._setup_complete())

        # Show/Hide button
        self.setup_show_pass_btn = self._mkbtn(
            pass_frame, "SHOW", self._toggle_password_visibility, CYAN)
        self.setup_show_pass_btn.pack(side=tk.RIGHT, padx=(5, 0))

        # Error label
        self.setup_error_label = tk.Label(
            panel_frame,
            text="",
            bg=BG_PANEL,
            fg=RED,
            font=(FONT, 9)
        )
        self.setup_error_label.pack(pady=(0, 15), padx=20)

        # Setup button
        setup_btn = self._mkbtn(panel_frame, "INITIALIZE CLOAK", self._setup_complete, PINK)
        setup_btn.pack(pady=(0, 20))

        # Focus on name entry
        name_entry.focus_set()

    def _toggle_password_visibility(self):
        """Toggle password visibility in the setup screen."""
        if self.setup_pass_entry.cget("show") == "█":
            self.setup_pass_entry.configure(show="")
            self.setup_show_pass_btn.set_text("HIDE")
        else:
            self.setup_pass_entry.configure(show="█")
            self.setup_show_pass_btn.set_text("SHOW")

    def _setup_complete(self):
        """Complete the setup process and initialize the main UI."""
        name = self.setup_name_var.get().strip()
        password = self.setup_pass_var.get()

        # Validate inputs
        if not 1 <= len(name) <= 64:
            self.setup_error_label.configure(text="Enter a callsign (1–64 characters)")
            return

        if not password:
            self.setup_error_label.configure(text="Enter an encryption key")
            return

        # Store the values
        self.username = name
        self.password = password

        # Clear setup screen
        for widget in self.root.winfo_children():
            widget.destroy()

        # Initialize main UI components
        self.name_var = tk.StringVar()
        self.pass_var = tk.StringVar()

        self._build_ui()
        self.name_var.set(self.username)
        self.id_status.configure(text=f"[ {self.username.upper()} ]", fg=CYAN)
        self.enc_status.configure(text="■ PASSPHRASE SET", fg=CYAN)
        self._reset_ui()
        self._start_services()
        self._tick_clock()
        self._sys("Choose a discovered peer or enter an IPv4 address and port.")
        self._sys("Use the same private passphrase on both devices.")

    # ── build UI ────────────────────────────────────────────────────

    def _build_ui(self):
        # ── top bar ─────────────────────────────────────────────────
        topbar = tk.Frame(self.root, bg=BG_DARK, height=28)
        topbar.pack(fill=tk.X, padx=10, pady=(8, 0))
        tk.Label(topbar, text="■", bg=BG_DARK, fg=GREEN,
                 font=(FONT, 10)).pack(side=tk.LEFT)
        tk.Label(topbar, text="  CLOAK", bg=BG_DARK, fg=PINK,
                 font=(FONT, 11, "bold")).pack(side=tk.LEFT)
        tk.Label(topbar, text=" v2.0", bg=BG_DARK, fg=FG_DIM,
                 font=(FONT, 9)).pack(side=tk.LEFT)
        tk.Label(topbar, text="ENCRYPTED P2P PROTOCOL", bg=BG_DARK, fg=FG_DIM,
                 font=(FONT, 9)).pack(side=tk.LEFT, padx=(30, 0))
        self.link_label = tk.Label(topbar, text="AWAITING CONNECTION", bg=BG_DARK,
                                    fg=YELLOW, font=(FONT, 9))
        self.link_label.pack(side=tk.RIGHT)

        # ── main area ───────────────────────────────────────────────
        outer = tk.Frame(self.root, bg=BG_DARK, padx=10, pady=8)
        outer.pack(fill=tk.BOTH, expand=True)
        outer.columnconfigure(0, weight=0, minsize=290)
        outer.columnconfigure(1, weight=1)
        outer.rowconfigure(0, weight=1)

        # ═══ LEFT SIDEBAR ═══════════════════════════════════════════
        left_panel = RoundedPanel(outer, bg_color=BG_PANEL, border_color=BORDER)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        sb = left_panel.inner

        # -- section 01: IDENTITY
        self._section_header(sb, "01", "IDENTITY / PROFILE")

        self.name_var = tk.StringVar()
        tk.Label(sb, text="CALLSIGN", bg=BG_PANEL, fg=FG_DIM,
                 font=(FONT, 8)).pack(anchor="w", pady=(6, 2))
        name_e = tk.Entry(sb, textvariable=self.name_var,
                          bg=BG_INPUT, fg=GREEN, insertbackground=GREEN,
                          font=(FONT, 12), bd=0, highlightthickness=1,
                          highlightcolor=PINK, highlightbackground=BORDER)
        name_e.pack(fill=tk.X, ipady=5, pady=(0, 5))
        name_e.bind("<Return>", lambda e: self._on_name_set())
        self._mkbtn(sb, "SET IDENTITY", self._on_name_set, PINK).pack(fill=tk.X)

        self.id_status = tk.Label(sb, text="[ UNSET ]", bg=BG_PANEL, fg=YELLOW,
                                   font=(FONT, 9), anchor="w")
        self.id_status.pack(fill=tk.X, pady=(3, 0))

        # -- section 02: ENCRYPTION
        self._sep(sb)
        self._section_header(sb, "02", "ENCRYPTION / KEY")

        self.pass_var = tk.StringVar()
        tk.Label(sb, text="PASSPHRASE", bg=BG_PANEL, fg=FG_DIM,
                 font=(FONT, 8)).pack(anchor="w", pady=(6, 2))
        pass_e = tk.Entry(sb, textvariable=self.pass_var, show="█",
                          bg=BG_INPUT, fg=PINK, insertbackground=PINK,
                          font=(FONT, 12), bd=0, highlightthickness=1,
                          highlightcolor=PINK, highlightbackground=BORDER)
        pass_e.pack(fill=tk.X, ipady=5, pady=(0, 5))
        pass_e.bind("<Return>", lambda e: self._on_password_set())
        self._mkbtn(sb, "DERIVE KEY", self._on_password_set, PINK).pack(fill=tk.X)

        self.enc_status = tk.Label(sb, text="■ CIPHER OFFLINE", bg=BG_PANEL,
                                    fg=YELLOW, font=(FONT, 9), anchor="w")
        self.enc_status.pack(fill=tk.X, pady=(3, 0))

        # -- section 03: NETWORK / PEERS
        self._sep(sb)
        self._section_header(sb, "03", "NETWORK / PEERS")

        # Scan button
        self.scan_btn = self._mkbtn(sb, "⟳  SCAN NETWORK", self._on_scan,
                                     GREEN, fg_color="#0a0a0f",
                                     hover_color="#33ff66")
        self.scan_btn.pack(fill=tk.X, pady=(6, 4))

        # Peer count
        peer_hdr = tk.Frame(sb, bg=BG_PANEL)
        peer_hdr.pack(fill=tk.X, pady=(0, 3))
        tk.Label(peer_hdr, text="NODES ONLINE", bg=BG_PANEL, fg=FG_DIM,
                 font=(FONT, 8)).pack(side=tk.LEFT)
        self.peer_count = tk.Label(peer_hdr, text="0", bg=BG_PANEL, fg=GREEN,
                                    font=(FONT, 10, "bold"))
        self.peer_count.pack(side=tk.RIGHT)

        # Peer list
        self.peer_listbox = tk.Listbox(
            sb, bg=BG_INPUT, fg=FG, selectbackground=PINK,
            selectforeground="#0a0a0f", font=(FONT, 10), height=4,
            bd=0, highlightthickness=1, highlightcolor=PINK,
            highlightbackground=BORDER, activestyle="none", relief="flat")
        self.peer_listbox.pack(fill=tk.BOTH, expand=True, pady=(0, 6))
        self.peer_listbox.bind("<<ListboxSelect>>", self._on_peer_select)

        direct = tk.Frame(sb, bg=BG_PANEL)
        direct.pack(fill=tk.X, pady=(0, 8))
        tk.Label(direct, text="DIRECT IPv4 : PORT", bg=BG_PANEL, fg=FG_DIM,
                 font=(FONT, 8)).pack(anchor="w")
        self.direct_var = tk.StringVar(value="127.0.0.1:5002")
        tk.Entry(direct, textvariable=self.direct_var, bg=BG_INPUT, fg=FG_BRIGHT,
                 insertbackground=CYAN, relief="flat", font=(FONT, 10)).pack(fill=tk.X, ipady=5)
        self.direct_btn = self._mkbtn(direct, "CONNECT DIRECT", self._on_direct, CYAN)
        self.direct_btn.pack(fill=tk.X, pady=(4, 0))

        # Connect / Disconnect
        btn_row = tk.Frame(sb, bg=BG_PANEL)
        btn_row.pack(fill=tk.X)
        btn_row.columnconfigure(0, weight=1)
        btn_row.columnconfigure(1, weight=1)
        self.conn_btn = self._mkbtn(btn_row, "CONNECT", self._on_connect, PINK)
        self.conn_btn.grid(row=0, column=0, sticky="ew", padx=(0, 2))
        self.conn_btn.set_enabled(False)
        self.disc_btn = self._mkbtn(btn_row, "DISCONNECT", self._on_disconnect,
                                     RED, hover_color="#ff4466")
        self.disc_btn.grid(row=0, column=1, sticky="ew", padx=(2, 0))
        self.disc_btn.set_enabled(False)

        # -- section 04: DIAGNOSTICS
        self._sep(sb)
        self._section_header(sb, "04", "DIAGNOSTICS")
        self.ip_label = tk.Label(sb, text=f"NODE  {self.local_ip}:{self.tcp_port}",
                                  bg=BG_PANEL, fg=FG_DIM, font=(FONT, 8), anchor="w")
        self.ip_label.pack(fill=tk.X)
        self.session_label = tk.Label(sb, text="SESSION  00:00:00", bg=BG_PANEL,
                                       fg=FG_DIM, font=(FONT, 8), anchor="w")
        self.session_label.pack(fill=tk.X)

        # ═══ RIGHT CHAT PANEL ══════════════════════════════════════
        right_panel = RoundedPanel(outer, bg_color=BG_PANEL, border_color=BORDER)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        cp = right_panel.inner
        cp.rowconfigure(2, weight=1)
        cp.columnconfigure(0, weight=1)

        # -- chat header
        ch = tk.Frame(cp, bg=BG_PANEL)
        ch.grid(row=0, column=0, sticky="ew")

        self._section_header_inline(ch, "05", "PRIVATE CHANNEL")
        self.protocol_label = tk.Label(ch, text="FERNET / AES-128", bg=BG_PANEL, fg=FG_DIM,
                                        font=(FONT, 8))
        self.protocol_label.pack(side=tk.RIGHT, padx=(0, 4))
        self.enc_proto = tk.Label(ch, text="UTF-8 /", bg=BG_PANEL, fg=FG_DIM,
                                   font=(FONT, 8))
        self.enc_proto.pack(side=tk.RIGHT)

        # -- connection status bar
        status_bar = tk.Frame(cp, bg=BG_PANEL)
        status_bar.grid(row=1, column=0, sticky="ew", pady=(4, 6))
        self.conn_indicator = tk.Label(status_bar, text="■", bg=BG_PANEL, fg=RED,
                                        font=(FONT, 9))
        self.conn_indicator.pack(side=tk.LEFT)
        self.conn_text = tk.Label(status_bar, text=" PROTOCOL STANDBY",
                                   bg=BG_PANEL, fg=FG_DIM, font=(FONT, 9))
        self.conn_text.pack(side=tk.LEFT)
        self.chat_peer = tk.Label(status_bar, text="", bg=BG_PANEL, fg=PINK,
                                   font=(FONT, 9, "bold"))
        self.chat_peer.pack(side=tk.RIGHT)

        # -- chat display
        chat_frame = tk.Frame(cp, bg=BG_DARK, highlightthickness=1,
                               highlightbackground=BORDER)
        chat_frame.grid(row=2, column=0, sticky="nsew")
        chat_frame.rowconfigure(0, weight=1)
        chat_frame.columnconfigure(0, weight=1)

        self.chat = tk.Text(
            chat_frame, wrap=tk.WORD, state=tk.DISABLED,
            bg=BG_DARK, fg=FG, font=(FONT, 11),
            bd=0, highlightthickness=0,
            padx=12, pady=10, spacing1=3, spacing3=3, relief="flat")
        self.chat.grid(row=0, column=0, sticky="nsew")
        sb_scroll = ttk.Scrollbar(chat_frame, command=self.chat.yview)
        sb_scroll.grid(row=0, column=1, sticky="ns")
        self.chat.configure(yscrollcommand=sb_scroll.set)

        # Tag styles
        self.chat.tag_configure("self_name", foreground=PINK, font=(FONT, 10, "bold"))
        self.chat.tag_configure("peer_name", foreground=GREEN, font=(FONT, 10, "bold"))
        self.chat.tag_configure("self_msg", foreground=FG_BRIGHT, font=(FONT, 11))
        self.chat.tag_configure("peer_msg", foreground=FG_BRIGHT, font=(FONT, 11))
        self.chat.tag_configure("time", foreground=FG_DIM, font=(FONT, 8))
        self.chat.tag_configure("sys", foreground=YELLOW, font=(FONT, 10))
        self.chat.tag_configure("err", foreground=RED, font=(FONT, 10))
        self.chat.tag_configure("proto", foreground=CYAN, font=(FONT, 9))

        # -- message input
        input_row = tk.Frame(cp, bg=BG_PANEL)
        input_row.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        input_row.columnconfigure(0, weight=1)

        input_box = tk.Frame(input_row, bg=BG_INPUT, highlightthickness=1,
                              highlightbackground=BORDER, highlightcolor=PINK)
        input_box.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self.msg_var = tk.StringVar()
        self.msg_entry = tk.Entry(
            input_box, textvariable=self.msg_var,
            bg=BG_INPUT, fg=FG_BRIGHT, insertbackground=PINK,
            font=(FONT, 12), bd=0, highlightthickness=0,
            disabledbackground=BG_DARK, disabledforeground=FG_DIM)
        self.msg_entry.pack(fill=tk.X, ipady=8, padx=10)
        self.msg_entry.bind("<Return>", lambda e: self._on_send())

        self.send_btn = self._mkbtn(input_row, "TRANSMIT ▶", self._on_send, PINK)
        self.send_btn.grid(row=0, column=1)
        self.send_btn.set_enabled(False)

        # -- packet counter
        pkt_row = tk.Frame(cp, bg=BG_PANEL)
        pkt_row.grid(row=4, column=0, sticky="ew", pady=(6, 0))
        self.pkt_label = tk.Label(pkt_row, text="PACKETS  0", bg=BG_PANEL,
                                   fg=FG_DIM, font=(FONT, 8), anchor="w")
        self.pkt_label.pack(side=tk.LEFT)
        self.conn_sec_label = tk.Label(pkt_row, text="PASSWORD UNVERIFIED",
                                        bg=BG_PANEL, fg=FG_DIM, font=(FONT, 8), anchor="e")
        self.conn_sec_label.pack(side=tk.RIGHT)
        self._pkt_count = 0

        # ── bottom status bar ──────────────────────────────────────
        bottom = tk.Frame(self.root, bg=BG_DARK, height=22)
        bottom.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=(0, 6))
        tk.Label(bottom, text="■", bg=BG_DARK, fg=GREEN,
                 font=(FONT, 8)).pack(side=tk.LEFT)
        self.bottom_status = tk.Label(bottom, text=" GHOST IN THE NETWORK",
                                       bg=BG_DARK, fg=FG_DIM, font=(FONT, 8))
        self.bottom_status.pack(side=tk.LEFT)
        self.clock_label = tk.Label(bottom, text="", bg=BG_DARK, fg=FG_DIM,
                                     font=(FONT, 8))
        self.clock_label.pack(side=tk.RIGHT)

    # ── UI helpers ──────────────────────────────────────────────────

    def _section_header(self, parent, num, title):
        f = tk.Frame(parent, bg=BG_PANEL)
        f.pack(fill=tk.X, pady=(4, 0))
        tk.Label(f, text=num, bg=BG_PANEL, fg=FG_DIM,
                 font=(FONT, 8)).pack(side=tk.LEFT)
        tk.Label(f, text=f"  {title}", bg=BG_PANEL, fg=PINK,
                 font=(FONT, 9, "bold")).pack(side=tk.LEFT)

    def _section_header_inline(self, parent, num, title):
        tk.Label(parent, text=num, bg=BG_PANEL, fg=FG_DIM,
                 font=(FONT, 8)).pack(side=tk.LEFT)
        tk.Label(parent, text=f"  {title}", bg=BG_PANEL, fg=PINK,
                 font=(FONT, 9, "bold")).pack(side=tk.LEFT)

    def _sep(self, parent):
        tk.Frame(parent, bg=BORDER, height=1).pack(fill=tk.X, pady=8)

    @staticmethod
    def _mkbtn(parent, text, cmd, bg=PINK, fg_color="#0a0a0f",
               hover_color=None):
        return CyberButton(parent, text=text, command=cmd,
                            bg_color=bg, fg_color=fg_color,
                            hover_color=hover_color or bg,
                            radius=8, padx=14, pady=4,
                            font_cfg=(FONT, 9, "bold"))

    # ════════════════════════════════════════════════════════════════
    #  Networking
    # ════════════════════════════════════════════════════════════════

    def _start_services(self):
        self.listener = TCPListener(self.tcp_port, self._on_incoming)
        listening = True
        try:
            self.listener.start()
        except OSError as exc:
            listening = False
            self.listener.stop()
            self._err(f"Cannot listen on port {self.tcp_port}: {exc}. Restart with --port PORT.")
            self._status("LISTENER UNAVAILABLE — outbound connections remain available")

        name = self.username or f"NODE-{self.tcp_port}"
        self.discovery = DiscoveryService(
            username=name, tcp_port=self.tcp_port,
            discovery_port=self.discovery_port,
            on_peer_found=self._on_peer_found)
        self.discovery.on_error = lambda message: self._post(self._err, message)
        self.discovery.start()
        self._schedule_prune()
        if listening:
            self._status(f"LISTENING {self.local_ip}:{self.tcp_port}")
        # Start periodic scanning
        # Discovery already broadcasts every three seconds.

    def _on_peer_found(self, name, ip, port):
        self._post(self._register_peer, name, ip, port)

    def _register_peer(self, name, ip, port):
        if self.peer_manager.upsert(Peer(name, ip, port)):
            self._sys(f"DISCOVERED {name} @ {ip}:{port}")
        self._refresh_peers()

    def _schedule_prune(self):
        if not self._running:
            return
        gone = self.peer_manager.prune_stale(timeout=12)
        if gone:
            self._refresh_peers()
            for uid in gone:
                self._sys(f"NODE {uid} OFFLINE")
        self.root.after(6000, self._schedule_prune)

    def _refresh_peers(self):
        sel = self.peer_listbox.curselection()
        sel_t = self.peer_listbox.get(sel[0]) if sel else None
        self.peer_listbox.delete(0, tk.END)
        peers = self.peer_manager.all_peers()
        for p in peers:
            self.peer_listbox.insert(tk.END, f"  {p.name}  ·  {p.ip_address}:{p.port}")
        self.peer_count.configure(text=str(len(peers)))
        if sel_t:
            for i in range(self.peer_listbox.size()):
                if self.peer_listbox.get(i) == sel_t:
                    self.peer_listbox.selection_set(i)
                    break

    def _on_incoming(self, client_sock, addr):
        if not self._running:
            client_sock.close()
            return
        self._post(self._accept_session, client_sock, addr)

    def _accept_session(self, client_sock, addr):
        if self._state != "disconnected":
            client_sock.close()
            return
        self._begin_session(client=client_sock)

    def _on_name_set(self):
        if self._state != "disconnected":
            self._err("Disconnect before changing the callsign")
            return
        n = self.name_var.get().strip()
        if not 1 <= len(n) <= 64:
            messagebox.showwarning("IDENTITY", "Enter a callsign.")
            return
        self.username = n
        if self.discovery:
            self.discovery.update_username(n)
        self.id_status.configure(text=f"[ {n.upper()} ]", fg=GREEN)
        self._sys(f"IDENTITY SET: {n.upper()}")
        self._status(f"IDENTITY: {n.upper()}")

    def _on_password_set(self):
        if self._state != "disconnected":
            self._err("Disconnect before changing the passphrase")
            return
        pw = self.pass_var.get()
        if not pw:
            self._err("Enter a passphrase")
            return
        self.password = pw
        self.pass_var.set("")
        self.enc_status.configure(text="■ PASSPHRASE SET", fg=CYAN)
        self._status("PASSPHRASE UPDATED")

    def _on_scan(self):
        if not self.discovery:
            return
        self._sys("SCANNING NETWORK...")
        self._status("SCANNING...")
        self.scan_btn.set_text("⟳  SCANNING...")
        self.scan_btn.set_enabled(False)
        self.discovery.scan()

        def done():
            self._refresh_peers()
            c = len(self.peer_manager.all_peers())
            self.scan_btn.set_text("⟳  SCAN NETWORK")
            self.scan_btn.set_enabled(True)
            self._sys(f"SCAN COMPLETE — {c} NODE(S) FOUND")
            self._status(f"SCAN COMPLETE — {c} NODE(S)")

        self.root.after(2000, done)

    def _on_peer_select(self, _e=None):
        self.conn_btn.set_enabled(bool(self.peer_listbox.curselection()) and self._state == "disconnected")

    def _on_direct(self):
        try:
            host, port = self.direct_var.get().strip().rsplit(":", 1)
            host = str(ipaddress.IPv4Address(host))
            port = int(port)
            if not 1 <= port <= 65535:
                raise ValueError()
        except ValueError:
            self._err("Enter an IPv4 address and port, for example 192.168.1.20:5001")
            return
        self._begin_session(host, port)

    def _on_connect(self):
        selection = self.peer_listbox.curselection()
        peers = self.peer_manager.all_peers()
        if selection and selection[0] < len(peers):
            peer = peers[selection[0]]
            self._begin_session(peer.ip_address, peer.port)

    def _begin_session(self, host=None, port=None, client=None):
        if self._state != "disconnected":
            if client:
                client.close()
            return
        self._state = "verifying" if client else "connecting"
        session = SecureSession(self.password, self.username,
            lambda kind, data: self._post(self._session_event, session, kind, data))
        self.connection = session
        self.conn_btn.set_enabled(False)
        self.direct_btn.set_enabled(False)
        self.disc_btn.set_enabled(True)
        self.link_label.configure(text="VERIFYING PASSPHRASE", fg=YELLOW)
        self.conn_text.configure(text=" CONNECTING / VERIFYING", fg=YELLOW)
        self._status("VERIFYING INCOMING PEER" if client else f"CONNECTING {host}:{port}")
        threading.Thread(target=session.start, kwargs=dict(host=host, port=port, client=client), daemon=True).start()

    def _session_event(self, session, kind, data):
        if session is not self.connection:
            return
        if kind == "ready":
            self._state = "connected"
            self.conn_indicator.configure(fg=GREEN)
            self.conn_text.configure(text=" CONNECTED", fg=GREEN)
            self.chat_peer.configure(text=data)
            self.send_btn.set_enabled(True)
            self.msg_entry.configure(state=tk.NORMAL)
            self.link_label.configure(text="ENCRYPTED CHANNEL", fg=GREEN)
            self.conn_sec_label.configure(text="PASSWORD VERIFIED", fg=GREEN)
            self._status(f"CONNECTED: {data}")
            self._proto("Shared password verified. Encrypted channel ready.")
            self.msg_entry.focus_set()
        elif kind == "message":
            self._peer_msg(*data)
            self._count_packet()
        elif kind == "error":
            self.connection = None
            self._reset_ui()
            self._err(data)
            self._status(data)

    def _on_disconnect(self):
        session, self.connection = self.connection, None
        if session:
            session.close()
        self._reset_ui()
        self._status("DISCONNECTED")
        self._sys("Channel closed")

    def _reset_ui(self):
        self._state = "disconnected"
        self.conn_indicator.configure(fg=FG_DIM)
        self.conn_text.configure(text=" AWAITING CONNECTION", fg=FG_DIM)
        self.chat_peer.configure(text="")
        self.send_btn.set_enabled(False)
        self.msg_entry.configure(state=tk.DISABLED)
        self.disc_btn.set_enabled(False)
        self.direct_btn.set_enabled(True)
        self._on_peer_select()
        self.link_label.configure(text="OFFLINE", fg=FG_DIM)
        self.conn_sec_label.configure(text="PASSWORD UNVERIFIED", fg=FG_DIM)

    def _count_packet(self):
        self._pkt_count += 1
        self.pkt_label.configure(text=f"PACKETS  {self._pkt_count}")

    def _on_send(self):
        message = self.msg_var.get().strip()
        if not message or self._state != "connected":
            return
        if len(message.encode()) > 65536:
            self._err("Message is too long (maximum 64 KiB)")
            return
        session = self.connection
        # Socket writes stay off the Tk event loop.
        def send():
            ok = session.send(message)
            self._post(self._sent, session, message, ok)
        self.send_btn.set_enabled(False)
        self.msg_entry.configure(state=tk.DISABLED)
        threading.Thread(target=send, daemon=True).start()

    def _sent(self, session, message, ok):
        if session is not self.connection or self._state != "connected":
            return
        self.send_btn.set_enabled(True)
        self.msg_entry.configure(state=tk.NORMAL)
        if ok:
            self._own_msg(message)
            self.msg_var.set("")
            self._count_packet()
        else:
            self._err("Transmit failed; reconnect to the peer")
            self._on_disconnect()

    # ── chat display ────────────────────────────────────────────────

    def _append(self, *pairs):
        self.chat.configure(state=tk.NORMAL)
        for tag, text in pairs:
            self.chat.insert(tk.END, text, tag)
        self.chat.insert(tk.END, "\n")
        self.chat.configure(state=tk.DISABLED)
        self.chat.see(tk.END)

    def _own_msg(self, msg):
        ts = time.strftime("%H:%M:%S")
        self._append(("time", f" {ts}  "), ("self_name", f"{self.username}  "),
                     ("self_msg", msg))

    def _peer_msg(self, name, msg):
        ts = time.strftime("%H:%M:%S")
        self._append(("time", f" {ts}  "), ("peer_name", f"{name}  "),
                     ("peer_msg", msg))

    def _sys(self, msg):
        self._append(("sys", f" //  {msg}"))

    def _err(self, msg):
        self._append(("err", f" !!  {msg}"))

    def _proto(self, msg):
        self._append(("proto", f" >>  {msg}"))

    def _status(self, msg):
        self.bottom_status.configure(text=f" {msg}")

    # ── clock / session timer ───────────────────────────────────────

    def _tick_clock(self):
        if not self._running:
            return
        now = time.strftime("%H:%M:%S")
        elapsed = int(time.time() - self._session_start)
        h, m, s = elapsed // 3600, (elapsed % 3600) // 60, elapsed % 60
        self.clock_label.configure(text=f"SESSION {h:02d}:{m:02d}:{s:02d}   |   {now}")
        self.session_label.configure(text=f"SESSION  {h:02d}:{m:02d}:{s:02d}")
        self.root.after(1000, self._tick_clock)

    # ── cleanup ─────────────────────────────────────────────────────

    def _on_close(self):
        self._running = False
        # Cancel any pending scan timer
        if self._scan_timer:
            self.root.after_cancel(self._scan_timer)
        if self.connection:
            self.connection.close()
        if self.listener:
            self.listener.stop()
        if self.discovery:
            self.discovery.stop()
        for timer in self.root.tk.splitlist(self.root.tk.call("after", "info")):
            self.root.after_cancel(timer)
        while not self._events.empty():
            callback, args = self._events.get_nowait()
            if callback == self._accept_session:
                args[0].close()
        self.root.destroy()


# ── Entry point ─────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="CLOAK // Encrypted P2P Chat")
    parser.add_argument("--port", type=int, default=DEFAULT_TCP_PORT)
    parser.add_argument("--discovery-port", type=int, default=DISCOVERY_PORT)
    parser.add_argument("--name", type=str, default="")
    args = parser.parse_args()

    root = tk.Tk()
    ChatApp(root, tcp_port=args.port, discovery_port=args.discovery_port,
            preset_name=args.name)
    root.mainloop()


if __name__ == "__main__":
    main()
