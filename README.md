# Encrypted-chat service — CLOAK

**Kernel Knights · Section U1**

Start with [RUN_GUIDE.md](RUN_GUIDE.md) for installation, launch commands, and troubleshooting.

A Python/Tkinter desktop chat application with an Edgerunners-inspired dark yellow/cyan interface. One active peer per instance. UDP discovery and direct IPv4 connections feed a password-confirmed, Fernet-encrypted TCP session.

## Setup and run

Requires Python 3.10+ with Tkinter. The checked environment is Python 3.15.2, Tk 9.1 and cryptography 50.0.2 on macOS.

```sh
python3 -m venv chat_env
source chat_env/bin/activate
python -m pip install -r requirements.txt
python chat_app.py --name Lucy
```

Every launcher opens setup. `--name` only prefills the callsign. Enter the same strong private passphrase on both clients. Do not share it in the chat or screenshots.

For two clients on one machine, run these in separate terminals:

```sh
python chat_app1.py
python chat_app2.py
```

Alice listens on TCP 5001 and Bob on TCP 5002. Select a discovered peer or enter `127.0.0.1:5002` from Alice. Connect from one side and wait for **PASSWORD VERIFIED** before sending.

For two machines, use the same permitted LAN and the remote machine's IPv4 address. Firewalls must allow the chosen TCP port and UDP discovery port. Broadcast filtering or Wi-Fi client isolation can prevent discovery; use direct connection to distinguish discovery failure from TCP reachability. A physical two-device LAN check remains pending.

```sh
python chat_app.py --port 5002 --discovery-port 5000 --name David
```

## Architecture and protocol

- `chat_app.py`: Tkinter UI and main-thread event queue; offline/pending/connected controls.
- `session.py`: protocol v2, password confirmation, timeouts, encrypted chat.
- `network.py`: UDP advertisements, TCP listener, framed JSON transport.
- `encryption.py`: PBKDF2-HMAC-SHA256 (1,200,000 iterations, random 16-byte salt) and Fernet.
- `peer.py`: endpoint registry and freshness, owned by the GUI thread.

Discovery broadcasts every three seconds (default UDP 5000); stale entries are pruned after twelve seconds at the next pruning pass. A manual scan sends an additional short burst. Chat uses `[4-byte big-endian payload length][UTF-8 JSON]`, with a 1 MiB envelope limit. The GUI limits outgoing text to 64 KiB of UTF-8.

Both peers send v2 `hello` envelopes with name, salt and a fresh challenge. Each encrypts a version-labeled, ordered pair of both challenges into a `proof`; reflected handshakes are rejected. A valid returned proof enables chat; a wrong password or eight-second handshake timeout closes the session. `chat` contains only encrypted text, and `disconnect` terminates transport. Both clients must use the updated protocol; there is no downgrade to the old handshake.

Network/KDF/send workers post events into a queue. Tkinter consumes them on its thread, and obsolete session events are ignored. Changing identity or password requires disconnecting first.

## How our TCP connection works

The app uses Python IPv4 stream sockets (`SOCK_STREAM`). `TCPListener` binds the chosen port and accepts an incoming socket; an outgoing `SecureSession` uses `socket.create_connection`. The operating system supplies TCP's ordered delivery, retransmission, and flow control. The same connection carries messages in both directions.

TCP is a byte stream, so it does not separate individual chat messages. `ChatConnection.send` serializes a JSON envelope, prefixes its byte length as a four-byte big-endian integer, and uses `sendall`. `_recv_exact` reconstructs the header and payload even when they arrive in fragments. A send lock prevents concurrent writes from interleaving frames, and the receiver rejects payloads larger than 1 MiB.

Fernet encrypts the chat text before TCP carries it; TCP itself does not provide encryption. UDP is used separately for finding peers. EOF/socket errors terminate the session and reset the UI. A successful send means the local socket accepted the bytes, rather than proving the remote person read the message. See report section 3.5 and the selected source excerpts for details.

## Checks

```sh
python -m unittest -v test_system
python gui_check.py
```

Install `requirements-report.txt` before the GUI check; Pillow is used only for screenshot capture. The last command opens two real windows and captures only their window region for report evidence; macOS may show a screen-recording permission dialog. It checks setup, password visibility, discovery, two-way chat, minimum window size, disconnect, reconnect and password mismatch. Results are saved to `reports/gui_checks.json`. See `reports/FINAL_CHECKS.md` for evidence and limits.

## Security boundaries

Fernet uses AES-128 with authentication, not AES-256. Password confirmation proves shared-secret possession, not a person's identity. This educational protocol is not a PAKE: captured handshakes allow offline guessing. Use a strong secret. There is no forward secrecy, verified public identity, application sequence/replay defense, internet relay, group messaging, persistence or remote read receipt. Names, salts, addresses, timing and Fernet timestamps are observable. No independent security audit was performed.

## Academic report

See `reports/README.md` for the editable DOCX, PDF, identity fields and reproducible builder. Report packages are separate from runtime requirements. The complete report is 34 pages including appendices; the code appendix contains selected excerpts, with full source in this directory.
