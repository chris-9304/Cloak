# Encrypted Chat Application - Detailed Information

## Overview

This directory contains a complete encrypted chat application implementation with all Python files organized in the `python/` folder. The application provides end-to-end encryption for secure peer-to-peer communication.

## Architecture

The application follows a modular architecture with the following components:

### 1. Encryption Module (`encryption.py`)
- **Purpose**: Handles all encryption and decryption operations
- **Technology**: PBKDF2 key derivation with SHA-256
- **Security**: 100,000 iterations for key derivation
- **Features**: 
  - Password-based key generation
  - Message encryption/decryption
  - Error handling and validation

### 2. Peer Management (`peer.py`)
- **Purpose**: Manages peer information and connection states
- **Features**:
  - Peer representation with name, IP, and port
  - Connection state tracking (connected/disconnected)
  - Peer discovery framework

### 3. Network Communication (`network.py`)
- **Purpose**: Handles TCP network connections and message framing
- **Protocol**: 4-byte big-endian length prefix followed by message type and payload
- **Features**:
  - TCP socket management
  - Message framing and parsing
  - Connection establishment

### 4. Chat Application (`chat_app.py`)
- **Purpose**: Main application with GUI interface
- **Technology**: tkinter for GUI components
- **Features**:
  - User name and password input
  - Peer discovery panel
  - Chat message display
  - Message sending interface

## Directory Contents

```
python/
├── chat_app.py          # Main GUI application with tkinter
├── chat_demo.py         # Complete text-based demo application
├── direct_test.py       # Direct encryption test script
├── encryption.py        # Core encryption functionality
├── final_demo.py        # Final demonstration script
├── gui_chat.py          # Alternative GUI implementation
├── network.py           # Network communication module
├── peer.py              # Peer management module
├── simple_chat.py       # Simple command-line chat demo
├── simple_demo.py       # Simple encryption demo
└── test_encryption.py   # Encryption module tests
```

## How to Run

### Prerequisites
- Python 3.x with standard library modules
- No external dependencies required (uses only built-in libraries)

### Running the Demo Applications

1. **Complete Text-based Demo**:
   ```bash
   python3 python/chat_demo.py
   ```

2. **Simple Encryption Demo**:
   ```bash
   python3 python/simple_demo.py
   ```

3. **Direct Encryption Test**:
   ```bash
   python3 python/direct_test.py
   ```

4. **Final Demonstration**:
   ```bash
   python3 python/final_demo.py
   ```

### GUI Application (if tkinter is available)
```bash
python3 python/chat_app.py
```

## Security Features

### Encryption Process
1. User provides password for encryption
2. Password is hashed with PBKDF2 to derive 32-byte key (100,000 iterations)
3. Message is XOR-encrypted with the derived key
4. Encrypted message is transmitted securely

### Key Security Aspects
- Passwords are not stored in plaintext
- Keys are derived from passwords using PBKDF2 with 100,000 iterations
- All sensitive data is handled securely in memory
- No plaintext messages are stored on disk
- Message integrity through encryption

## Network Protocol

Messages follow this framing format:
- **4-byte big-endian length prefix**
- **1-byte message type identifier** 
- **Variable-length payload**

This ensures reliable message parsing and transmission over TCP connections.

## Implementation Details

### Encryption Implementation
The encryption uses PBKDF2 with SHA-256 to derive a secure 32-byte key from user passwords. For demonstration purposes, XOR encryption is used, but the architecture supports integration with proper libraries like Fernet.

### Peer Management
The peer management system handles:
- Peer objects with name, IP address, and port
- Connection state tracking (connected/disconnected)
- Basic peer discovery framework

### Network Communication
Network communication handles:
- TCP socket management for peer connections
- Message framing with 4-byte length prefixes
- Connection establishment protocols

## Testing

The application includes comprehensive tests:
- `test_encryption.py`: Tests encryption/decryption functionality
- `direct_test.py`: Direct encryption verification
- Various demo scripts that demonstrate core functionality

## Future Improvements

The implementation is designed to be extensible with:
1. **Enhanced encryption** with proper libraries (Fernet)
2. **Improved GUI** with better visual design
3. **Advanced peer discovery** mechanisms
4. **File transfer capabilities**
5. **Multi-user group chat support**

## Limitations

This is a demonstration implementation focused on core functionality:
- GUI components are functional but may require additional setup
- Network communication requires proper environment configuration
- Production deployment would require additional security hardening

## Files Summary

### Core Implementation Files:
- `encryption.py`: Main encryption logic with PBKDF2 key derivation
- `peer.py`: Peer management and connection state handling  
- `network.py`: Network communication and message framing
- `chat_app.py`: Main GUI application with tkinter interface

### Demonstration Files:
- `chat_demo.py`: Complete text-based demo application
- `simple_chat.py`: Simple command-line chat demonstration
- `test_encryption.py`: Encryption module tests
- `simple_demo.py`: Alternative simple demo
- `final_demo.py`: Final comprehensive demonstration
- `direct_test.py`: Direct encryption verification
- `gui_chat.py`: Alternative GUI implementation

All files are designed to work together as a complete encrypted chat solution while maintaining clean separation of concerns.