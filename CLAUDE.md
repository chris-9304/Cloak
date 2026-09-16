# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build commands

**Windows** — Requires: MSVC 2022 (v143), CMake ≥ 3.25, Ninja, vcpkg with `VCPKG_ROOT` set. First build downloads all vcpkg dependencies (15–30 min).

```powershell
cmake --preset debug               # configure
cmake --build --preset debug       # build
ctest --preset debug --output-on-failure   # all tests
ctest --preset debug -R <name> --output-on-failure  # single test by name
```

Presets: `debug`, `release`, `asan` (MSVC ASan), `analyze` (MSVC `/analyze`). Build outputs go to `build/<preset>/`.

Installer (WiX MSI, not needed for development):
```powershell
cmake --preset release && cmake --build --preset release --target installer
```

**macOS / Linux** — added despite ADR-0002 (below) at the user's explicit request; see
README.md's "Build & Run on macOS / Linux" section for full details. Requires: Clang or
GCC, CMake ≥ 3.25, Ninja, `pkg-config`, `autoconf`, `automake`, `autoconf-archive`,
`libtool` (needed to build libsodium via vcpkg), vcpkg with `VCPKG_ROOT` set.

```bash
cmake --preset debug-posix
cmake --build --preset debug-posix
ctest --preset debug-posix --output-on-failure
```

Presets: `debug-posix`, `release-posix`. Only `cloak-relay` and the library modules
build in this configuration — `ui`/`app`/`discovery` are excluded (see Architecture).
Verified on Apple Silicon/Clang; Linux untested but should work unchanged (everything
uses portable POSIX APIs: `mlock`, POSIX signals, `arpa/inet.h`, `std::byteswap`).

**Docker / Podman / OrbStack** — `cloak-relay` also builds and runs in a Linux
container via the root `Containerfile`. See README.md's "Run cloak-relay in a
container" section for the exact commands; short version:
```bash
docker build -t cloak-relay -f Containerfile .
docker run --rm -p 8765:8765 cloak-relay
```
(Substitute `podman` if you have a Podman machine provisioned — `podman machine init &&
podman machine start` — otherwise any OCI-compatible engine works, OrbStack's `docker`
CLI included.)

## Architecture

Cloak is a P2P messenger (v0.4.0 — Phase 4 complete). Originally Windows-native
terminal app; now also builds `cloak-relay` + the core libraries on macOS/Linux (native
or in a container) per the user's explicit request (see Build commands above). Phase 1:
LAN text chat. Phase 2: Double Ratchet, file transfer, receipts. Phase 3: Sender-Key
group chat, multi-device via device certs, group/peer persistence. Phase 4: Internet
relay transport, invite-code peer discovery.

**`ui`/`app`/`discovery` are no longer built** (removed from `CMakeLists.txt` — this was
already in progress, uncommitted, when this repo was transferred to macOS): the
terminal UI client, top-level orchestrator, and Win32 mDNS discovery are being replaced
by a Rust server + Android app per project notes. `include/cloak/{ui,app,discovery}` and
`src/{ui,app,discovery}` still exist on disk but aren't part of any current build target.

**Module ownership** (each is a separate CMake library under `src/`; all except `ui`/`app`/`discovery` build on every platform):

| Module | Role |
|--------|------|
| `core` | Shared types (`PeerId`, `SessionId`, `TrustStatus`, `Result<T, Error>`) |
| `crypto` | Static libsodium facade; the only place `sodium_init()` is called. All key material in `SecureBuffer` (`mlock`/`VirtualLock` + zero on destroy, move-only — platform-branched) |
| `identity` | Long-term Ed25519+X25519 keypair, Argon2id-encrypted at rest. `PeerDirectory` tracks TOFU trust (`Unknown→Tofu→Verified→Changed`) |
| `wire` | Frame encode/decode. Format: `[4-byte BE length][1-byte MessageType][payload]`. Hand-rolled, not protobuf |
| `transport` | Abstract `Transport` base. Phase 1: `TcpTransport`. Phase 2 adds `LanMailboxTransport`. Phase 4 adds `RelayTransport` |
| `session` | Noise XX handshake + per-message symmetric ratchet (Phase 2: full Double Ratchet). Not thread-safe; caller must use a strand |
| `store` | SQLite with column-level XChaCha20-Poly1305 AEAD. DB key derived from passphrase via Argon2id at startup |
| `group` | Phase 3 multi-party encryption (Sender Key model, Ed25519-signed). Has a known pre-existing bug — see below |
| `transfer` | Phase 2 file transfer, 64 KiB chunks, per-file AEAD key |
| `relay` | Phase 4 relay server (`cloak-relay`, `.exe` on Windows) — transparent TCP multiplexer for NAT traversal, pure `boost::asio`, builds natively everywhere and in the `Containerfile` |
| ~~`ui`~~ | ~~FTXUI terminal TUI~~ — not built (see above) |
| ~~`app`~~ | ~~`ChatApplication` — top-level orchestrator~~ — not built (see above) |
| ~~`discovery`~~ | ~~Abstract `DiscoveryService`, mDNS via Win32 DNS-SD~~ — not built (see above) |

**Known bug (pre-existing, not platform-specific):** `GroupManager::accept_invite`'s
"new group invitation" branch registers the inviter's member state under
`inviter_signing_pub` (the identity key), but `GroupSession::decrypt` looks up senders
by their per-group Sender-Key public key (`GroupSession::own_sign_pub_`, generated fresh
per group, unrelated to identity keys) — and that key is never actually transmitted in
the `Invite`/`Create` wire payload at all. Group message decryption therefore always
fails with "Unknown group member sender key" (`test_group` reproduces this). Fixing it
needs a wire-format change (add the sender's per-group public key to `GroupOpPayload`)
— flagged, not fixed, since it's a protocol change outside a build-portability pass.

**Data flow (send):** `ChatApplication` → `SessionManager` → `Session` (DR encrypt) → `wire::encode_app()` → `Transport::send()`

**Data flow (receive):** `Transport` bytes → `wire::decode()` → `Session` (DR decrypt) → `ChatApplication` display + `MessageStore` persist

**Concurrency:** UI thread never blocks. One Asio `io_context` thread for all I/O. Each `Session` has its own Asio strand — multiple sessions progress concurrently, one session is serialized. Cross-thread: lock-free SPSC queues or `asio::post`.

## Key design invariants

- **No custom crypto.** libsodium primitives only via `cloak::crypto::Crypto`. Never call libsodium directly.
- **Secrets in `SecureBuffer` only.** Never copy key material into `std::vector` or `std::string`.
- **`CLOAK_UNSAFE_LOG_SECRETS=1`** enables secret logging in debug builds. CI forbids logging on secret-bearing types.
- **`std::expected<T, Error>`** for recoverable errors throughout. Exceptions only for genuinely unexpected situations.
- **TOFU is loud.** `TrustStatus::Changed` must surface as a user-visible alert — never silently accept a new key.

## Public headers

The `include/cloak/` tree mirrors `src/` and exposes the public API of each module. The `src/` tree has the implementations. Both are on the include path so `<cloak/core/types.h>` and `"core/types.h"` both work; prefer the angle-bracket form in headers.

## Testing

Tests live in `tests/unit/<module>/`. The `cmake/cloak_add_library.cmake` macro auto-discovers `tests/unit/<name>/*.cpp` and creates `test_<name>` executables linked against `Catch2::Catch2WithMain`. RFC test vectors are in `tests/vectors/crypto/`.

Coverage targets: `crypto/`, `identity/`, `session/` ≥ 85%; others ≥ 70%.

## Key design invariants (do not violate)

- **`send_inner(type, payload)` / `recv_message()` are the canonical Session API.** `send_text()` / `recv_text()` are convenience wrappers for `InnerType::Text` only.
- **Group messages** must be sent with `InnerType::GroupMessage` via `send_inner()`. Never wrap them in `send_text()`.
- **Group ops** (invite/leave/kick) must use `InnerType::GroupOp` via `send_inner()`.
- **Receipts** use `InnerType::Receipt` via `send_receipt()` which calls `send_inner()` internally.
- **`session_recv_func_impl`** drives a `switch` on `InnerType` — add new cases here for new inner types.
- **Group persistence:** call `store_->save_group(group_mgr_.snapshot(gid))` on create/join/leave. Groups are loaded into `GroupManager` via `restore()` on startup.
- **Safety numbers** are 60 decimal digits in groups of 10 separated by spaces (6 groups of 2 digits × 5 bytes, each byte `% 100`).
- **Relay protocol:** 37-byte client handshake (magic CLK1 + role + 32-byte room_id), 1-byte server response. After pairing, raw bytes forwarded transparently.
- **Invite codes** format: `<relay_host>:<relay_port>/<room_id_hex64>`. Room ID derived as BLAKE2b-256(sign_pub || random_16).

## Phase 4: Internet Relay

`cloak-relay` (`cloak-relay.exe` on Windows) is a standalone relay server — pure
`boost::asio`, no platform-specific code. Run it on any publicly reachable host, built
natively or via the `Containerfile` (see Build commands above):

```bash
cloak-relay --port 8765
# or: docker run --rm -p 8765:8765 cloak-relay
```

For networks that block non-standard ports (university, office, public WiFi) run the relay on port 443 — most firewalls allow outbound 443:
```bash
cloak-relay --port 443
```

Client workflow:
1. Both parties need network access to the relay host.
2. Inviter: `--relay <host:port>` flag at startup, then `/make-invite` → prints an invite code.
3. Invitee: `/connect-invite <code>` → connects through relay → full Cloak session established.

The relay never sees plaintext — all cryptography runs on top of the relay transport.

## Offline Message Queue

Messages typed when the active session is dead are queued in memory (keyed by peer fingerprint). When that peer reconnects (via TCP or relay) the receive thread drains the queue automatically before entering the normal receive loop. No persistence across process restart — the queue is in-memory only.

Lock order: always acquire `session_mutex_` before `queue_mutex_`. Never reverse this order.

## File / Image / Video Transfer

Use `/send <path>` for any file type. MIME type is detected from the file extension and transmitted in `FileMetadata`. The transfer layer splits any file into 64 KiB chunks, each encrypted with a per-file XChaCha20-Poly1305 key. The file key itself is sealed in the session. Supported extensions with auto-detected MIME: jpg/jpeg, png, gif, webp, mp4, mkv, mov, avi, mp3, wav, pdf, txt, zip, 7z. Any other extension transfers as `application/octet-stream`.

## ADRs

`docs/adr/` records key decisions. Notable ones:
- `0002` — MSVC-native only (no MinGW/WSL). **Partially superseded**: macOS/Linux
  native + container builds of `cloak-relay` and the core libraries were added at the
  user's explicit request despite this ADR; the ADR's rationale still applies to the
  Windows desktop client (`ui`/`app`), which isn't part of the macOS/Linux build at all.
- `0003` — Noise XX for Phase 1 handshake (not Signal X3DH; both peers are online)
- `0004` — Column-level AEAD over SQLCipher (finer control, no full-DB key in memory)
- `0005` — mDNS for LAN discovery (Win32 DNS-SD)
- `0006` — Thread-per-connection relay (simple, sufficient for dev deployments)

## Runtime paths

- Identity: `%APPDATA%\Cloak\identity.bin`
- Database: `%APPDATA%\Cloak\store.db`
- Logs: `%APPDATA%\Cloak\logs\` (spdlog rotating, default level info)

These describe the (not-currently-built) Windows desktop client (`app`/`ui`); no path
resolution code for identity/store/logs exists anywhere in `src/` today — callers
(tests, `cloak-relay`) pass explicit paths. If a macOS/Linux app ever needs this, it
isn't implemented yet.
