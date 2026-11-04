#!/usr/bin/env python3
"""
Chat Instance 1  –  launches the encrypted P2P chat as "User 1"
on TCP port 5001 (default).

Run this alongside chat_app2.py on the same machine to test
peer-to-peer messaging locally.

Usage:
    python3 chat_app1.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tkinter as tk
from chat_app import ChatApp

def main():
    root = tk.Tk()
    # Position window on the left side of the screen
    root.geometry("920x680+50+80")
    app = ChatApp(
        root,
        tcp_port=5001,
        discovery_port=5000,
        preset_name="Alice",
    )
    root.mainloop()

if __name__ == "__main__":
    main()
