# Encrypted Chat Application — Documentation

## Overview

A **real peer-to-peer encrypted chat** application for devices on the same local network. Peers automatically discover each other via UDP broadcast and communicate over TCP with end-to-end Fernet encryption.

## Quick Start

### Prerequisites
```bash
pip install cryptography
```

### Run on two different machines (same LAN)
```bash
# Machine A
python3 chat_app.py --name Alice

# Machine B
python3 chat_app.py --name Bob
```

### Test locally on the same machine
```bash
# Terminal 1
python3 chat_app1.py

# Terminal 2
python3 chat_app2.py
```

Both windows will automatically discover each other. Set the **same encryption password** on both sides, select the peer, and click **Connect**.

## Architecture

```
┌─────────────┐         UDP broadcast          ┌─────────────┐
│  chat_app1  │ ◄──────────────────────────────► │  chat_app2  │
│  (Alice)    │         discovery beacons        │  (Bob)      │
│  port 5001  │                                  │  port 5002  │
│             │ ◄──────── TCP connection ───────► │             │
│             │      length-prefixed JSON        │             │
│             │      + Fernet-encrypted msgs     │             │
└─────────────┘                                  └─────────────┘
```

### Module Breakdown

| File | Purpose |
|------|---------|
| `encryption.py` | PBKDF2 key derivation + Fernet encrypt/decrypt with shared-salt support |
| `network.py` | UDP discovery service, TCP listener, TCP chat connection with length-prefixed framing |
| `peer.py` | Peer model with staleness tracking + PeerManager registry |
| `chat_app.py` | Main application — modern dark-themed tkinter GUI + all networking |
| `chat_app1.py` | Convenience launcher for instance 1 (Alice, port 5001) |
| `chat_app2.py` | Convenience launcher for instance 2 (Bob, port 5002) |

### Network Protocol

**Discovery (UDP port 5000):**
- Broadcast every 3 seconds: `{"type": "discovery", "name": "...", "ip": "...", "port": ...}`
- Peers that stop broadcasting are pruned after 12 seconds

**Chat (TCP, configurable port):**
- Messages are framed as `[4-byte big-endian length][JSON payload]`
- JSON envelope: `{"type": "handshake"|"chat"|"disconnect", "data": {...}}`
- Chat payloads contain Fernet-encrypted ciphertext

### Encryption

1. Both users enter the **same password**
2. PBKDF2-HMAC-SHA256 derives a 32-byte key (100,000 iterations + random 16-byte salt)
3. The connecting peer sends its salt in the handshake so both sides can derive compatible keys
4. Messages are encrypted with **Fernet** (AES-128-CBC + HMAC-SHA256)

### CLI Options

```
python3 chat_app.py [--port PORT] [--discovery-port PORT] [--name NAME]

  --port             TCP listen port (default: 5001)
  --discovery-port   UDP discovery port (default: 5000)
  --name             Preset display name
```

## Legacy Demo Files

| File | Description |
|------|-------------|
| `chat_demo.py` | Text-based demo |
| `simple_chat.py` | Simple CLI chat demo |
| `gui_chat.py` | Old minimal GUI |
| `simple_demo.py` | Basic encryption demo |
| `final_demo.py` | Final demo script |
| `direct_test.py` | Direct encryption test |
