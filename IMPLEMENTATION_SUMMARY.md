# CLOAK v2 implementation summary

The supported Python client now requires setup in all launchers, confirms the shared passphrase before enabling messages, provides a direct IPv4/port fallback, and restores connection controls after termination. Secure sessions are independent of the GUI. Worker results are queued to Tkinter with session identity checks so obsolete callbacks cannot reset a replacement conversation.

The GUI uses Tkinter/ttk and Canvas only: dark panels, yellow primary actions, cyan supporting controls, brighter secondary text, explicit verified/offline states, keyboard-operable buttons, and consistent CLOAK branding. Password derivation is now PBKDF2-HMAC-SHA256 with 1,200,000 iterations. Protocol v2 requires both peers to update together.

Transport rejects malformed/oversized frames, listener conflicts are reported, and shutdown closes sockets and cancels Tk callbacks. The new `test_system.py` covers encryption, framing, password confirmation, timeout, refusal, and repeated sessions; `gui_check.py` exercises live local clients. Actual outcomes and unverified scenarios are in `reports/FINAL_CHECKS.md`.

The academic report covers the Python implementation only. Academic identity placeholders and external Turnitin/supervisor requirements remain explicit. See `reports/README.md`.
