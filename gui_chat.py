#!/usr/bin/env python3
"""
Minimal tkinter chat application that demonstrates the core encryption functionality.
This version avoids complex network operations to focus on GUI and encryption.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import time
import sys
import os

# Add the current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from encryption import EncryptionManager

class MinimalChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Minimal Encrypted Chat")
        self.root.geometry("600x500")

        # Application state
        self.username = ""
        self.password = ""
        self.encryption = EncryptionManager()
        self.is_encrypted = False

        # GUI setup
        self.setup_gui()

    def setup_gui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)

        # Top panel - Name and password input
        top_frame = ttk.Frame(main_frame)
        top_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Label(top_frame, text="Your Name:").grid(row=0, column=0, padx=(0, 5))
        self.name_entry = ttk.Entry(top_frame, width=20)
        self.name_entry.grid(row=0, column=1, padx=(0, 10))
        self.name_entry.bind('<Return>', lambda event: self.set_username())

        ttk.Button(top_frame, text="Set Name", command=self.set_username).grid(row=0, column=2, padx=(0, 10))

        ttk.Label(top_frame, text="Encryption Password:").grid(row=1, column=0, padx=(0, 5), pady=(10, 0))
        self.password_entry = ttk.Entry(top_frame, show="*", width=20)
        self.password_entry.grid(row=1, column=1, padx=(0, 10), pady=(10, 0))
        self.password_entry.bind('<Return>', lambda event: self.set_password())

        ttk.Button(top_frame, text="Set Password", command=self.set_password).grid(row=1, column=2, padx=(0, 10), pady=(10, 0))

        # Chat display area
        chat_frame = ttk.LabelFrame(main_frame, text="Chat", padding="10")
        chat_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        chat_frame.columnconfigure(0, weight=1)
        chat_frame.rowconfigure(0, weight=1)

        self.chat_display = scrolledtext.ScrolledText(chat_frame, state=tk.DISABLED, wrap=tk.WORD)
        self.chat_display.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Message input
        message_frame = ttk.Frame(main_frame)
        message_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        message_frame.columnconfigure(1, weight=1)

        ttk.Label(message_frame, text="Message:").grid(row=0, column=0, padx=(0, 5))
        self.message_entry = ttk.Entry(message_frame, width=40)
        self.message_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        self.message_entry.bind('<Return>', lambda event: self.send_message())

        self.send_button = ttk.Button(message_frame, text="Send", command=self.send_message)
        self.send_button.grid(row=0, column=2)

        # Status bar
        self.status_label = ttk.Label(main_frame, text="Status: Ready", foreground="blue")
        self.status_label.grid(row=3, column=0, columnspan=2, sticky=(tk.W), pady=(10, 0))

        # Demo button
        ttk.Button(main_frame, text="Run Encryption Demo", command=self.run_demo).grid(row=4, column=0, columnspan=2, pady=(10, 0))

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

        if self.encryption.set_password(self.password):
            self.is_encrypted = True
            self.update_status("Encryption enabled")
            self.send_button.config(state=tk.NORMAL)
        else:
            messagebox.showerror("Error", "Failed to set encryption password")

    def update_status(self, message):
        """Update the status label"""
        self.status_label.config(text=f"Status: {message}")

    def send_message(self):
        """Send a message (demonstrates encryption)"""
        if not self.is_encrypted:
            messagebox.showwarning("Warning", "Please set an encryption password first")
            return

        message = self.message_entry.get()
        if not message:
            return

        try:
            # Encrypt the message
            encrypted_message = self.encryption.encrypt_message(message)

            # Show both original and encrypted versions
            timestamp = time.strftime("%H:%M:%S")
            self.display_message(f"[{timestamp}] {self.username}: {message} (encrypted)")
            self.display_message(f"Encrypted: {encrypted_message.decode('utf-8')[:50]}...")

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

    def run_demo(self):
        """Run a simple encryption/decryption demo"""
        if not self.is_encrypted:
            messagebox.showwarning("Warning", "Please set an encryption password first")
            return

        # Demonstrate encryption/decryption
        demo_message = "This is a secret message for demonstration!"

        try:
            # Encrypt
            encrypted = self.encryption.encrypt_message(demo_message)

            # Decrypt
            decrypted = self.encryption.decrypt_message(encrypted)

            # Display results
            timestamp = time.strftime("%H:%M:%S")
            self.display_message(f"[{timestamp}] Demo: Original message")
            self.display_message(f"  {demo_message}")
            self.display_message(f"[{timestamp}] Demo: Encrypted message")
            self.display_message(f"  {encrypted.decode('utf-8')[:50]}...")
            self.display_message(f"[{timestamp}] Demo: Decrypted message")
            self.display_message(f"  {decrypted}")

            if demo_message == decrypted:
                self.display_message(f"[{timestamp}] Demo: ✓ SUCCESS - Messages match!")
                self.update_status("Demo completed successfully")
            else:
                self.display_message(f"[{timestamp}] Demo: ✗ FAILURE - Messages don't match!")
                self.update_status("Demo failed")

        except Exception as e:
            messagebox.showerror("Error", f"Demo failed: {str(e)}")

def main():
    root = tk.Tk()

    # Check if tkinter is available
    try:
        app = MinimalChatApp(root)
        root.mainloop()
    except tk.TclError as e:
        print("Tkinter not available or setup issue:", str(e))
        print("This is expected on some systems. Running simple demo instead...")

        # Run a simple text-based demo
        print("=== Simple Encrypted Chat Demo ===")
        from encryption import EncryptionManager
        em = EncryptionManager()
        if em.set_password("secret123"):
            message = "Hello, this is a test message!"
            encrypted = em.encrypt_message(message)
            decrypted = em.decrypt_message(encrypted)
            print(f"Original: {message}")
            print(f"Encrypted: {encrypted}")
            print(f"Decrypted: {decrypted}")
            if message == decrypted:
                print("✓ Encryption/Decryption successful!")
            else:
                print("✗ Failed!")

if __name__ == "__main__":
    main()