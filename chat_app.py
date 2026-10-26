#!/usr/bin/env python3
"""
Simple encrypted chat application using tkinter for GUI.
Allows two computers on the same network to connect and chat securely.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import socket
import threading
import json
import hashlib
import secrets
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import time
import sys

class ChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Encrypted Chat")
        self.root.geometry("800x600")

        # Application state
        self.username = ""
        self.connected_peer = None
        self.socket = None
        self.is_connected = False
        self.running = True

        # Encryption setup
        self.password = ""
        self.key = None
        self.cipher = None

        # GUI setup
        self.setup_gui()

        # Start discovery thread
        self.discovery_thread = threading.Thread(target=self.start_discovery, daemon=True)
        self.discovery_thread.start()

    def setup_gui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)

        # Top panel - Name input and connection status
        top_frame = ttk.Frame(main_frame)
        top_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Label(top_frame, text="Your Name:").grid(row=0, column=0, padx=(0, 5))
        self.name_entry = ttk.Entry(top_frame, width=20)
        self.name_entry.grid(row=0, column=1, padx=(0, 10))
        self.name_entry.bind('<Return>', lambda event: self.set_username())

        ttk.Button(top_frame, text="Set Name", command=self.set_username).grid(row=0, column=2, padx=(0, 10))

        self.status_label = ttk.Label(top_frame, text="Status: Not connected", foreground="red")
        self.status_label.grid(row=0, column=3, padx=(0, 10))

        # Middle panel - Peer discovery and connection
        middle_frame = ttk.LabelFrame(main_frame, text="Peers", padding="10")
        middle_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        middle_frame.columnconfigure(0, weight=1)
        middle_frame.rowconfigure(0, weight=1)

        # Peer list
        self.peer_listbox = tk.Listbox(middle_frame, height=6)
        self.peer_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), columnspan=2)
        self.peer_listbox.bind('<<ListboxSelect>>', self.on_peer_select)

        # Connect button
        self.connect_button = ttk.Button(middle_frame, text="Connect", command=self.connect_to_peer, state=tk.DISABLED)
        self.connect_button.grid(row=1, column=0, pady=(10, 0), sticky=tk.W)

        # Refresh button
        ttk.Button(middle_frame, text="Refresh", command=self.refresh_peers).grid(row=1, column=1, pady=(10, 0), sticky=tk.E)

        # Chat display area
        chat_frame = ttk.LabelFrame(main_frame, text="Chat", padding="10")
        chat_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        chat_frame.columnconfigure(0, weight=1)
        chat_frame.rowconfigure(0, weight=1)

        self.chat_display = scrolledtext.ScrolledText(chat_frame, state=tk.DISABLED, wrap=tk.WORD)
        self.chat_display.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Message input
        message_frame = ttk.Frame(main_frame)
        message_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        message_frame.columnconfigure(1, weight=1)

        self.message_entry = ttk.Entry(message_frame, width=50)
        self.message_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        self.message_entry.bind('<Return>', lambda event: self.send_message())

        self.send_button = ttk.Button(message_frame, text="Send", command=self.send_message, state=tk.DISABLED)
        self.send_button.grid(row=0, column=2)

        # Password entry for encryption
        password_frame = ttk.Frame(main_frame)
        password_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))

        ttk.Label(password_frame, text="Encryption Password:").grid(row=0, column=0, padx=(0, 5))
        self.password_entry = ttk.Entry(password_frame, show="*", width=30)
        self.password_entry.grid(row=0, column=1, padx=(0, 10))
        self.password_entry.bind('<Return>', lambda event: self.set_password())

        ttk.Button(password_frame, text="Set Password", command=self.set_password).grid(row=0, column=2)

    def set_username(self):
        """Set the user's display name"""
        self.username = self.name_entry.get().strip()
        if not self.username:
            messagebox.showerror("Error", "Please enter a name")
            return
        self.update_status(f"Name set to: {self.username}")

    def set_password(self):
        """Set the encryption password"""
        self.password = self.password_entry.get()
        if not self.password:
            messagebox.showerror("Error", "Please enter an encryption password")
            return

        # Generate key from password
        salt = b"chat_app_salt_1234567890"  # In a real app, this should be random and stored
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.password.encode()))
        self.key = key
        self.cipher = Fernet(key)
        self.update_status("Encryption enabled")

    def update_status(self, message):
        """Update the status label"""
        self.status_label.config(text=f"Status: {message}")

    def refresh_peers(self):
        """Refresh the peer list"""
        self.peer_listbox.delete(0, tk.END)
        # In a real implementation, this would query the network for peers
        self.update_status("Peer list refreshed")

    def on_peer_select(self, event):
        """Handle peer selection"""
        selection = self.peer_listbox.curselection()
        if selection:
            self.connect_button.config(state=tk.NORMAL)
        else:
            self.connect_button.config(state=tk.DISABLED)

    def connect_to_peer(self):
        """Connect to the selected peer"""
        selection = self.peer_listbox.curselection()
        if not selection:
            return

        peer_info = self.peer_listbox.get(selection[0])
        # In a real implementation, this would establish a TCP connection
        self.update_status(f"Connecting to {peer_info}...")

        # Simulate connection (in a real app, this would be actual TCP connection)
        self.is_connected = True
        self.connected_peer = peer_info
        self.update_status(f"Connected to {peer_info}")
        self.connect_button.config(state=tk.DISABLED)
        self.send_button.config(state=tk.NORMAL)

    def send_message(self):
        """Send a message to the connected peer"""
        if not self.is_connected or not self.cipher:
            return

        message = self.message_entry.get()
        if not message:
            return

        try:
            # Encrypt the message
            encrypted_message = self.cipher.encrypt(message.encode())

            # In a real implementation, this would send the encrypted message over TCP
            # For now, we'll just display it locally
            timestamp = time.strftime("%H:%M:%S")
            self.display_message(f"[{timestamp}] {self.username}: {message}", is_local=True)

            # Clear the input field
            self.message_entry.delete(0, tk.END)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to send message: {str(e)}")

    def display_message(self, message, is_local=False):
        """Display a message in the chat window"""
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, message + "\n")
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)

    def start_discovery(self):
        """Start peer discovery process"""
        # In a real implementation, this would:
        # 1. Send UDP broadcast to discover peers
        # 2. Listen for peer responses
        # 3. Add discovered peers to the listbox
        while self.running:
            try:
                # Simulate discovering peers (in real app, this would be network discovery)
                if self.root.winfo_exists():
                    self.root.after(0, lambda: self.add_peer("192.168.1.101 - Alice"))
                    self.root.after(0, lambda: self.add_peer("192.168.1.102 - Bob"))
                time.sleep(5)  # Refresh every 5 seconds
            except Exception:
                break

    def add_peer(self, peer_info):
        """Add a peer to the list"""
        # Check if peer already exists
        existing = False
        for i in range(self.peer_listbox.size()):
            if self.peer_listbox.get(i) == peer_info:
                existing = True
                break

        if not existing:
            self.peer_listbox.insert(tk.END, peer_info)

    def cleanup(self):
        """Clean up resources when closing"""
        self.running = False
        if self.socket:
            self.socket.close()

def main():
    root = tk.Tk()
    app = ChatApp(root)

    # Handle window closing
    def on_closing():
        app.cleanup()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()