#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║  GHOST_LINK v0.1  //  ENCRYPTED P2P CHAT PROTOCOL           ║
║  Real LAN peer discovery + Fernet-encrypted TCP messaging    ║
║  Cyberpunk terminal UI inspired by CAPRION_OS                ║
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
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from encryption import EncryptionManager
from network import (
    DiscoveryService,
    ChatConnection,
    TCPListener,
    _get_local_ip,
    DEFAULT_TCP_PORT,
    DISCOVERY_PORT,
)
from peer import Peer, PeerManager


# ═══════════════════════════════════════════════════════════════════
#  CAPRION_OS colour palette
# ═══════════════════════════════════════════════════════════════════
BG_DARK         = "#0a0a0f"      # deepest background
BG_PANEL        = "#0f0f18"      # panel / card background
BG_INPUT        = "#14141f"      # input fields
FG              = "#c8c8d0"      # primary text
FG_DIM          = "#555566"      # muted / secondary text
FG_BRIGHT       = "#e0e0e8"      # bright text
PINK            = "#ff0055"      # primary accent — hot pink
PINK_DIM        = "#aa0038"      # dimmed pink
GREEN           = "#00ff41"      # neon green — status, online
GREEN_DIM       = "#009926"      # dimmed green
CYAN            = "#00e5ff"      # cyan for highlights
YELLOW          = "#ffcc00"      # warnings
RED             = "#ff2244"      # errors, danger
BORDER          = "#1a1a2e"      # panel borders
BORDER_ACCENT   = "#2a1a28"      # subtle pink-tinted border
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
                 disabled_bg="#1a1a2e", disabled_fg="#555566",
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
        self.bind("<Button-1>", self._click)

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
        self.encryption = EncryptionManager()
        self._peer_enc: Optional[EncryptionManager] = None
        self.peer_manager = PeerManager()
        self.connection: Optional[ChatConnection] = None
        self._handshake_sent = False
        self.listener: Optional[TCPListener] = None
        self.discovery: Optional[DiscoveryService] = None
        self.local_ip = _get_local_ip()
        self._running = True
        self._session_start = time.time()

        self._setup_root()
        self._build_ui()
        self._start_services()
        self._tick_clock()

        if self.username:
            self.name_var.set(self.username)
            self._on_name_set()

    # ── root config ─────────────────────────────────────────────────

    def _setup_root(self):
        self.root.title("GHOST_LINK // ENCRYPTED P2P")
        self.root.geometry("980x720")
        self.root.minsize(760, 560)
        self.root.configure(bg=BG_DARK)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(".", background=BG_DARK, foreground=FG)
        style.configure("Vertical.TScrollbar",
                        background=BG_PANEL, troughcolor=BG_DARK,
                        arrowcolor=FG_DIM, borderwidth=0)

    # ── build UI ────────────────────────────────────────────────────

    def _build_ui(self):
        # ── top bar ─────────────────────────────────────────────────
        topbar = tk.Frame(self.root, bg=BG_DARK, height=28)
        topbar.pack(fill=tk.X, padx=10, pady=(8, 0))
        tk.Label(topbar, text="■", bg=BG_DARK, fg=GREEN,
                 font=(FONT, 10)).pack(side=tk.LEFT)
        tk.Label(topbar, text="  GHOST_LINK", bg=BG_DARK, fg=PINK,
                 font=(FONT, 11, "bold")).pack(side=tk.LEFT)
        tk.Label(topbar, text=" v0.1", bg=BG_DARK, fg=FG_DIM,
                 font=(FONT, 9)).pack(side=tk.LEFT)
        tk.Label(topbar, text="ENCRYPTED P2P PROTOCOL", bg=BG_DARK, fg=FG_DIM,
                 font=(FONT, 9)).pack(side=tk.LEFT, padx=(30, 0))
        self.link_label = tk.Label(topbar, text="LINK ESTABLISHING", bg=BG_DARK,
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
            selectforeground="#0a0a0f", font=(FONT, 10),
            bd=0, highlightthickness=1, highlightcolor=PINK,
            highlightbackground=BORDER, activestyle="none", relief="flat")
        self.peer_listbox.pack(fill=tk.BOTH, expand=True, pady=(0, 6))
        self.peer_listbox.bind("<<ListboxSelect>>", self._on_peer_select)

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

        self._section_header_inline(ch, "05", "NEURAL_LINK / CHAT")
        self.protocol_label = tk.Label(ch, text="AES-256", bg=BG_PANEL, fg=FG_DIM,
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
        self.conn_sec_label = tk.Label(pkt_row, text="CONNECTION SECURE ■",
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
        self.listener.start()

        name = self.username or f"NODE-{self.tcp_port}"
        self.discovery = DiscoveryService(
            username=name, tcp_port=self.tcp_port,
            discovery_port=self.discovery_port,
            on_peer_found=self._on_peer_found)
        self.discovery.start()
        self._schedule_prune()
        self._status(f"LISTENING {self.local_ip}:{self.tcp_port}")

    def _on_peer_found(self, name, ip, port):
        p = Peer(name, ip, port)
        is_new = self.peer_manager.upsert(p)
        self.root.after(0, self._refresh_peers)
        if is_new:
            self.root.after(0, lambda: self._sys(f"DISCOVERED {name} @ {ip}:{port}"))

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
        if self.connection and self.connection.is_alive:
            client_sock.close()
            return
        conn = ChatConnection(on_message=self._on_msg, on_disconnect=self._on_disc)
        conn.accept(client_sock)
        self.connection = conn
        self._handshake_sent = False
        self.root.after(0, lambda: self._finalize(f"{addr[0]}:{addr[1]}", incoming=True))

    # ── GUI events ──────────────────────────────────────────────────

    def _on_name_set(self):
        n = self.name_var.get().strip()
        if not n:
            messagebox.showwarning("IDENTITY", "Enter a callsign.")
            return
        self.username = n
        if self.discovery:
            self.discovery.update_username(n)
        self.id_status.configure(text=f"[ {n.upper()} ]", fg=GREEN)
        self._sys(f"IDENTITY SET: {n.upper()}")
        self._status(f"IDENTITY: {n.upper()}")

    def _on_password_set(self):
        pw = self.pass_var.get()
        if not pw:
            messagebox.showwarning("ENCRYPTION", "Enter a passphrase.")
            return
        self.password = pw
        if self.encryption.set_password(pw):
            self.enc_status.configure(text="■ CIPHER ONLINE  //  FERNET-AES", fg=GREEN)
            self._status("ENCRYPTION KEY DERIVED")
            self.conn_sec_label.configure(text="CONNECTION SECURE ■", fg=GREEN)
        else:
            self.enc_status.configure(text="■ KEY DERIVATION FAILED", fg=RED)

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

    def _on_peer_select(self, _e):
        sel = self.peer_listbox.curselection()
        can = bool(sel) and not (self.connection and self.connection.is_alive)
        self.conn_btn.set_enabled(can)

    def _on_connect(self):
        sel = self.peer_listbox.curselection()
        if not sel:
            return
        if not self.username:
            messagebox.showwarning("IDENTITY", "Set callsign first.")
            return
        if not self.encryption.cipher:
            messagebox.showwarning("ENCRYPTION", "Set passphrase first.")
            return
        peers = self.peer_manager.all_peers()
        idx = sel[0]
        if idx >= len(peers):
            return
        peer = peers[idx]
        self._status(f"CONNECTING TO {peer}...")
        self.conn_btn.set_enabled(False)

        def go():
            conn = ChatConnection(on_message=self._on_msg, on_disconnect=self._on_disc)
            if conn.connect(peer.ip_address, peer.port):
                self.connection = conn
                self._handshake_sent = True
                conn.send(ChatConnection.MSG_HANDSHAKE, {
                    "name": self.username,
                    "salt": self.encryption.get_salt().hex()})
                self.root.after(0, lambda: self._finalize(str(peer)))
            else:
                self.root.after(0, lambda: self._err(f"CONNECT FAILED: {peer}"))
                self.root.after(0, lambda: self._status("CONNECTION FAILED"))
                self.root.after(0, lambda: self.conn_btn.set_enabled(True))

        threading.Thread(target=go, daemon=True).start()

    def _finalize(self, label, incoming=False):
        d = "INBOUND" if incoming else "OUTBOUND"
        self.conn_indicator.configure(fg=GREEN)
        self.conn_text.configure(text=f" PROTOCOL ACTIVE", fg=GREEN)
        self.chat_peer.configure(text=label)
        self.send_btn.set_enabled(True)
        self.msg_entry.configure(state=tk.NORMAL)
        self.conn_btn.set_enabled(False)
        self.disc_btn.set_enabled(True)
        self.link_label.configure(text="LINK ESTABLISHED ■ ■", fg=GREEN)
        self._proto(f"{d} UPLINK ESTABLISHED. STAY IN THE SIGNAL.")
        self._status(f"CONNECTED: {label}")

    def _on_disconnect(self):
        if self.connection:
            self.connection.close()
            self.connection = None
        self._handshake_sent = False
        self._peer_enc = None
        self._reset_ui()
        self._sys("UPLINK TERMINATED")
        self._status("DISCONNECTED")

    def _on_disc(self):
        self.connection = None
        self._handshake_sent = False
        self._peer_enc = None
        self.root.after(0, self._reset_ui)
        self.root.after(0, lambda: self._sys("PEER DROPPED — UPLINK LOST"))
        self.root.after(0, lambda: self._status("PEER DISCONNECTED"))

    def _reset_ui(self):
        self.conn_indicator.configure(fg=RED)
        self.conn_text.configure(text=" PROTOCOL STANDBY", fg=FG_DIM)
        self.chat_peer.configure(text="")
        self.send_btn.set_enabled(False)
        self.disc_btn.set_enabled(False)
        self.link_label.configure(text="LINK DOWN", fg=RED)
        self.conn_sec_label.configure(fg=FG_DIM)

    # ── send / receive ──────────────────────────────────────────────

    def _on_send(self):
        msg = self.msg_var.get().strip()
        if not msg:
            return
        if not self.connection or not self.connection.is_alive:
            self._err("NO ACTIVE UPLINK")
            return
        if not self.encryption.cipher:
            self._err("CIPHER OFFLINE — SET PASSPHRASE")
            return
        try:
            enc = self.encryption.encrypt_message(msg)
            ok = self.connection.send(ChatConnection.MSG_CHAT, {
                "name": self.username, "cipher": enc.decode()})
            if ok:
                self._own_msg(msg)
                self.msg_var.set("")
                self._pkt_count += 1
                self.pkt_label.configure(text=f"PACKETS  {self._pkt_count}")
            else:
                self._err("TRANSMIT FAILED — UPLINK MAY BE LOST")
        except Exception as e:
            self._err(f"TRANSMIT ERROR: {e}")

    def _on_msg(self, mt, data):
        if mt == ChatConnection.MSG_HANDSHAKE:
            n = data.get("name", "UNKNOWN")
            s = data.get("salt", "")
            self.root.after(0, lambda: self._do_handshake(n, s))
        elif mt == ChatConnection.MSG_CHAT:
            self.root.after(0, lambda: self._do_chat(data))

    def _do_handshake(self, name, salt_hex):
        self._proto(f"HANDSHAKE FROM {name.upper()}")
        self.chat_peer.configure(text=name)
        if not self._handshake_sent and self.connection and self.encryption.cipher:
            self._handshake_sent = True
            self.connection.send(ChatConnection.MSG_HANDSHAKE, {
                "name": self.username,
                "salt": self.encryption.get_salt().hex()})
        if salt_hex and self.password:
            try:
                pe = EncryptionManager()
                pe.set_password(self.password, salt=bytes.fromhex(salt_hex))
                self._peer_enc = pe
            except Exception:
                pass

    def _do_chat(self, data):
        name = data.get("name", "PEER")
        ct = data.get("cipher", "")
        if not ct:
            return
        plain = None
        cb = ct.encode()
        for enc in [self._peer_enc, self.encryption]:
            if enc and enc.cipher:
                plain = enc.try_decrypt(cb)
                if plain:
                    break
        if plain:
            self._peer_msg(name, plain)
            self._pkt_count += 1
            self.pkt_label.configure(text=f"PACKETS  {self._pkt_count}")
        else:
            self._err(f"DECRYPT FAILED FROM {name} — PASSPHRASE MISMATCH?")

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
        if self.connection:
            self.connection.close()
        if self.listener:
            self.listener.stop()
        if self.discovery:
            self.discovery.stop()
        self.root.destroy()


# ── Entry point ─────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="GHOST_LINK // Encrypted P2P Chat")
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
