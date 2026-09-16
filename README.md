# Cloak

> **End-to-end encrypted, peer-to-peer terminal messenger for Windows.**  
> No accounts. No servers that can read your messages. No setup for local chat.

[![Build](https://img.shields.io/badge/build-MSVC%202022%20%2F%20C%2B%2B23-blue)](WINDOWS_BUILD.md)
[![Version](https://img.shields.io/badge/version-v0.4.0-green)](ROADMAP.md)
[![License](https://img.shields.io/badge/license-MIT-lightgrey)](#)

---

## Features

| Feature | Status |
|---------|--------|
| LAN text chat (auto-discovery via mDNS) | ✅ Phase 1 |
| Double Ratchet encryption (Signal protocol) | ✅ Phase 2 |
| File transfer (per-file AEAD, 64 KiB chunks) | ✅ Phase 2 |
| Delivery + read receipts | ✅ Phase 2 |
| Disappearing messages | ✅ Phase 2 |
| Group chat (Sender Key model) | ✅ Phase 3 |
| Multi-device support (device certificates) | ✅ Phase 3 |
| Encrypted persistent message history (SQLite + AEAD) | ✅ Phase 2/3 |
| Internet relay for NAT traversal | ✅ Phase 4 |
| Invite-code peer discovery | ✅ Phase 4 |
| Offline message queue | ✅ Phase 4 |
| TOFU identity verification + safety numbers | ✅ All phases |
| Windows installer (Inno Setup) | ✅ Phase 1+ |

---

## Install (No Build Required)

**Download `installer.exe` from `dist/` and double-click it.** That's it.

The installer (built with Inno Setup 6):
- Installs to `%ProgramFiles%\Cloak\` (Admin) or `%LOCALAPPDATA%\Programs\Cloak\` (per-user)
- Silently installs the **Visual C++ 2022 Runtime** if missing
- Creates a **Start Menu shortcut** — search "Cloak" to find it
- Creates an **optional desktop shortcut**
- Adds Cloak to your **PATH** (optional, tick the checkbox)
- Registers in **Add/Remove Programs** for clean uninstall

After install:
- **Search "Cloak" in the Start Menu** and click it. You'll be prompted for your display name.
- Or open a terminal and run: `cloak.exe --name "Alice" --port 8080`

> **Portable alternative:** `cloak-0.4.0-win64.zip` — unzip anywhere and double-click `Install Cloak.bat` (no PowerShell knowledge needed), or run `cloak.exe` directly from a terminal.

---

## Quick Start

### LAN (same network)

```powershell
# Both parties run this — they find each other automatically via mDNS
.\cloak.exe --name "Alice"
.\cloak.exe --name "Bob"
# Alternatively, click [✉ Invite Code] in Alice's UI and have Bob paste it via [↪ Join via Code]
```

### Internet (via relay)

```powershell
# 1. Run a relay server on a public host
.\cloak-relay.exe --port 8765

# 2. Alice starts with the relay flag
.\cloak.exe --name "Alice" --relay relay.example.com:8765
# Inside the UI: Click [✉ Invite Code]
# → generates: relay.example.com:8765/a3f8c2...

# 3. Bob connects with the invite code
.\cloak.exe --name "Bob"
# Inside the UI: Click [↪ Join via Code] and paste relay.example.com:8765/a3f8c2...
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [report.md](report.md) | **Full technical report** — OOP design, C++ features, every protocol, every feature explained for all audiences |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System architecture, class model, concurrency model |
| [WINDOWS_BUILD.md](WINDOWS_BUILD.md) | Step-by-step build instructions |
| [THREAT_MODEL.md](THREAT_MODEL.md) | Security threat model and cryptographic choices |
| [ROADMAP.md](ROADMAP.md) | Phase-by-phase feature delivery |
| [DEPENDENCIES.md](DEPENDENCIES.md) | All vcpkg dependencies with versions |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Code style and contribution rules |
| [SECURITY.md](SECURITY.md) | Security policy and responsible disclosure |
| [docs/DEMO.md](docs/DEMO.md) | CLI walkthrough with example sessions |
| [docs/adr/](docs/adr/) | Architecture Decision Records |

---

## Build from Source

**Requirements:** MSVC 2022 (v143), CMake ≥ 3.25, Ninja, vcpkg with `VCPKG_ROOT` set.

```powershell
cmake --preset debug                                   # configure
cmake --build --preset debug                           # build
ctest --preset debug --output-on-failure               # test
```

First build downloads all vcpkg dependencies (15–30 min). Subsequent builds are fast.

**Presets:** `debug`, `release`, `asan` (AddressSanitizer), `analyze` (MSVC static analyzer).

**Binary output locations:**
- `build/release/src/app/cloak.exe`
- `build/release/src/relay/cloak-relay.exe`

**Build + package in one step** (creates both `dist/installer.exe` and `dist/cloak-0.4.0-win64.zip`):
```powershell
.\build-dist.ps1              # full build then package
.\build-dist.ps1 -SkipBuild  # re-package existing binaries only
```
Requires [Inno Setup 6](https://jrsoftware.org/isdl.php) (`winget install JRSoftware.InnoSetup`) for the installer.exe step.

See [WINDOWS_BUILD.md](WINDOWS_BUILD.md) for the full setup guide.

---

## Build & Run on macOS / Linux

Cloak was originally MSVC/Windows-only (ADR-0002). It now also builds natively on
macOS/Linux with Clang or GCC, targeting just the relay server and the underlying
libraries — see "Scope" below.

### Prerequisites

```bash
# macOS (Homebrew)
brew install cmake ninja pkg-config autoconf automake autoconf-archive libtool

# Debian/Ubuntu
sudo apt install cmake ninja-build pkg-config autoconf autoconf-archive automake libtool
```

You also need [vcpkg](https://github.com/microsoft/vcpkg) for dependencies (libsodium,
Boost, spdlog, fmt, sqlite3, Catch2):

```bash
git clone https://github.com/microsoft/vcpkg ~/vcpkg
cd ~/vcpkg && ./bootstrap-vcpkg.sh
export VCPKG_ROOT=$HOME/vcpkg   # add this to your shell profile
```

### Build & test

```bash
cmake --preset debug-posix                          # configure (first run builds
                                                     # vcpkg deps from source, ~15-30 min)
cmake --build --preset debug-posix                  # build
ctest --preset debug-posix --output-on-failure       # run tests
```

Use `release-posix` instead of `debug-posix` for an optimized build.

### Run the relay server

```bash
./build/debug-posix/src/relay/cloak-relay --port 8765
```

### Scope (macOS/Linux)

Only `cloak-relay` and the library modules it depends on (`core`, `crypto`, `identity`,
`wire`, `store`, `transport`, `session`, `transfer`, `group`) build in this
configuration. `ui` (the FTXUI terminal client), `app` (the top-level orchestrator),
and `discovery` (Win32 mDNS LAN discovery) are **not** built — per this project's own
in-progress plan, the interactive desktop client is being replaced by a Rust server +
Android app, so there is currently no terminal chat client on macOS/Linux, only the
relay.

### What changed to make this build natively on macOS/Linux

- **`src/crypto/secure_buffer.h`** (+ its `include/cloak/crypto/` mirror): `mlock`/
  `munlock` and a manual volatile zero replace `VirtualLock`/`VirtualUnlock`/
  `SecureZeroMemory`, guarded by `#ifdef _WIN32` so the Windows path is untouched.
- **`src/relay/relay_main.cpp`**: POSIX `signal(SIGINT/SIGTERM, ...)` replaces
  `SetConsoleCtrlHandler` for Ctrl+C shutdown.
- **`src/relay/relay_server.cpp`**: the `winsock2.h` include (unneeded — networking
  is all `boost::asio`) is now Windows-only.
- **`src/wire/framing.cpp`, `src/session/session.cpp`**: `winsock2.h`/`htonl`/
  `_byteswap_uint64` (MSVC intrinsic) replaced with `<arpa/inet.h>` and C++23
  `std::byteswap` (`<bit>`), used on both platforms.
- **`src/transport/CMakeLists.txt`, `src/wire/CMakeLists.txt`,
  `src/relay/CMakeLists.txt`, `src/session/CMakeLists.txt`**: `ws2_32` linking made
  Windows-only via `$<$<PLATFORM_ID:Windows>:ws2_32>`.
- **`vcpkg.json`, `CMakeLists.txt`**: dropped `wil` (unused anywhere in the codebase)
  and `ftxui` (already unused after the `ui` module was dropped) as Windows-only
  dependencies.
- **`cmake/msvc_options.cmake`, `cmake/warnings.cmake`**: compiler flags branched —
  MSVC flags (`/W4`, `/utf-8`, etc.) only apply under MSVC; Clang/GCC get
  `-Wall -Wextra -Werror`.
- **`CMakeLists.txt`**: the old `if(NOT MSVC OR NOT CMAKE_SYSTEM_NAME STREQUAL
  "Windows") message(FATAL_ERROR ...)` gate now only requires MSVC when actually
  targeting Windows.
- **`CMakePresets.json`**: added `debug-posix`/`release-posix` presets alongside the
  existing Windows ones.
- Restored ~24 `include/cloak/*.h` public headers (`core`, `crypto`, `group`,
  `identity`, `relay`, `session`, `store`, `transfer`, `transport`, `wire`) that had
  gone missing from the working copy — active modules still required them to
  compile, so this wasn't part of the intentional `ui`/`app`/`discovery` removal.
- **`src/identity/identity.cpp`**: fixed a constructor member-initializer-order bug
  (unrelated to Windows, just caught by stricter Clang warnings).
- **`src/store/message_store.cpp`, `src/wire/framing.cpp`**: a few genuinely-unused
  static helpers marked `[[maybe_unused]]`.
- **`src/store/message_store.cpp`/`.h`** (+ `include/cloak/store/` mirror): fixed a
  real bug — `MessageStore`'s defaulted move constructor copied the raw `sqlite3*`
  handle without nulling the source, so a temporary produced during return-by-value /
  `std::expected` construction would close the handle in its destructor while the
  live object still held the same pointer, causing `SQLITE_MISUSE` on every
  `save_message`/`save_group` call. Replaced with a hand-written move
  constructor/assignment operator.
- **`src/wire/framing.h`/`.cpp`** (+ `include/cloak/wire/` mirror), **`src/group/
  group_session.cpp`**, **`src/group/group_manager.cpp`**: fixed a real group-chat bug
  — `GroupOpPayload`'s Invite/Create ops never transmitted the sender's own per-group
  Sender-Key public key, so group message decryption always failed with "Unknown group
  member sender key" (`test_group` reproduced this on every platform, not just macOS).
  Added a `sender_sign_pub` field to the wire format and fixed member registration to
  use it. All 9/9 test suites pass now.

Verified on Apple Silicon (arm64) with Clang/libc++, Debug and Release configs, for the
full library + test suite (9/9 suites pass). `cloak-relay` specifically is also verified
on Linux (GCC 12, arm64, via the container below) — the rest of the library stack
(crypto/identity/session/store/etc.) hasn't been exercised on Linux directly, but should
work unchanged since every portability fix above uses portable POSIX APIs (`mlock`,
POSIX signals, `<arpa/inet.h>`, `std::byteswap`) with nothing macOS-specific.

---

## Run cloak-relay in a container

Only `cloak-relay` (plus `core`, its one dependency) is containerized — there's no
terminal UI client build in this configuration (see "Build & Run on macOS / Linux"
above for why `ui`/`app` aren't built at all right now). This is the relay server only;
run the actual Cloak client natively.

**Prerequisites:** Docker, Podman, or OrbStack. (Podman needs a machine provisioned —
`podman machine init && podman machine start` — before its CLI works; OrbStack and
Docker Desktop both ship a `docker`-compatible CLI directly.)

```bash
# Build
docker build -t cloak-relay -f Containerfile .

# Run on the default port (8765), mapped to the host
docker run --rm -p 8765:8765 cloak-relay

# Or on a different port -- pass args after the image name, they replace the
# Containerfile's default CMD (["--port", "8765"])
docker run --rm -p 443:443 cloak-relay --port 443
```

(Substitute `podman` for `docker` if using a provisioned Podman machine — the commands
are otherwise identical.)

First build clones and bootstraps vcpkg fresh inside the image and builds `core` +
`relay` from source (a couple of minutes — `cloak-relay` itself has a much smaller
dependency footprint than the full library, since `relay_server.cpp` only needs
`boost::asio` and `core`'s shared types). Subsequent builds reuse Docker's layer cache
as long as `CMakeLists.txt`/`vcpkg.json`/`src/`/`include/` haven't changed.

---

## Security

Cloak uses:
- **X25519** Diffie-Hellman key agreement
- **Ed25519** signatures (identity authentication, group message signing)
- **XChaCha20-Poly1305** AEAD (all message and file encryption)
- **HKDF-SHA256** key derivation (Double Ratchet)
- **Argon2id** (passphrase → database key)
- **BLAKE2b-256** (room ID derivation, safety numbers)

All cryptographic operations go through **libsodium** — no custom crypto. Key material lives in `SecureBuffer<N>` (mlock'd RAM, zeroed on destruction). See [THREAT_MODEL.md](THREAT_MODEL.md) for full details.

To report a security vulnerability, see [SECURITY.md](SECURITY.md).

---

## UI Buttons

Cloak features a fully button-driven FTXUI terminal interface.

- **[⊙ Search LAN]** — Refresh the peer list by probing the local network
- **[✉ Invite Code]** — Generate an invite code (direct LAN code if no relay is configured, or relay code if started with `--relay`)
- **[↪ Join via Code]** — Paste a code to connect directly or via relay
- **[➡ Direct Connect]** — Enter a specific IP and port to connect manually
- **Peer List** — Scroll up/down and press Enter to switch conversations

See [docs/DEMO.md](docs/DEMO.md) for a full walkthrough.

---

## Relay Server

Run `cloak-relay.exe` on any publicly reachable host. The relay forwards encrypted bytes between peers — it never has keys and cannot read messages.

```powershell
cloak-relay.exe --port 8765

# For networks that block non-standard ports:
cloak-relay.exe --port 443
```

---

## Runtime Paths

| File | Path |
|------|------|
| Identity | `%APPDATA%\Cloak\identity.bin` |
| Database | `%APPDATA%\Cloak\store.db` |
| Logs | `%APPDATA%\Cloak\logs\` |
