#!/usr/bin/env python3
"""
Chat Instance 2  –  launches the encrypted P2P chat as "User 2"
on TCP port 5002.

Run this alongside chat_app1.py on the same machine to test
peer-to-peer messaging locally.

Usage:
    python3 chat_app2.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tkinter as tk
from chat_app import ChatApp

def main():
    root = tk.Tk()
    # Position window on the right side of the screen
    root.geometry("920x680+1000+80")
    app = ChatApp(
        root,
        tcp_port=5002,
        discovery_port=5000,
        preset_name="Bob",
    )
    root.mainloop()

if __name__ == "__main__":
    main()
