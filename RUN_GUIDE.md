# Running CLOAK

CLOAK is a Python/Tkinter application for encrypted chat between two clients on the same computer or local network. Both clients must run the updated code and use the same private passphrase.

## 1. Open the project

On this Mac, open Terminal and run:

```sh
cd /Users/cj/Documents/dev/encrypted-chat-service/python
```

Run all commands below from this folder.

## 2. Prepare Python

The existing `chat_env` environment is already configured on this machine. Activate it:

```sh
source chat_env/bin/activate
```

For a fresh installation on another Mac or Linux computer with Python 3.10 or later and Tkinter installed:

```sh
python3 -m venv chat_env
source chat_env/bin/activate
python -m pip install -r requirements.txt
```

For the existing environment, run the installation command only if dependencies need to be installed or updated:

```sh
python -m pip install -r requirements.txt
```

The application uses Tkinter/ttk for its GUI and `cryptography` for encryption. Report-generation packages are not needed to run the chat.

## 3. Try two clients on this computer

Open **two terminal windows**. In each terminal, enter the project folder and activate the environment as described above.

In the first terminal:

```sh
python chat_app1.py
```

In the second terminal:

```sh
python chat_app2.py
```

The first client prefills **Alice** and listens on TCP port **5001**. The second prefills **Bob** and listens on TCP port **5002**.

1. In each app, choose a callsign and enter the **same private passphrase**.
2. Click **INITIALIZE CLOAK** in both windows.
3. Wait a few seconds for discovery, or click **SCAN NETWORK**.
4. In one window, select the other peer and click **CONNECT**. Initiate the connection from only one side.
5. Wait for **PASSWORD VERIFIED** and **ENCRYPTED CHANNEL**.
6. Type a message and press **Enter** or click **TRANSMIT**. Reply from the other window.
7. Click **DISCONNECT** to end the session. You can then connect again.

If discovery does not find the other local client, use the direct connection field:

| Connecting from | Enter in the direct field |
| --- | --- |
| Alice → Bob | `127.0.0.1:5002` |
| Bob → Alice | `127.0.0.1:5001` |

Click **CONNECT DIRECT** and wait for verification. The address `127.0.0.1` works only when both clients run on the same computer.

## 4. Run on two computers

Install the project and runtime dependencies on both computers. Connect both to the same local network and complete setup in both apps.

On computer A:

```sh
python chat_app.py --name Alice --port 5001
```

On computer B:

```sh
python chat_app.py --name Bob --port 5002
```

Use the same private passphrase. Select the other peer after discovery, or read its **NODE** address in the diagnostics panel and enter that address and port in **CONNECT DIRECT**. For example, if Bob's computer displays `192.168.1.20:5002`, Alice connects to that endpoint.

Both clients use UDP port **5000** for discovery by default. The network/firewall must allow discovery traffic and the chosen TCP listening ports. Guest Wi-Fi, client isolation, VPNs, or firewall rules can prevent communication. Direct connection can bypass unavailable discovery, but it still requires a reachable TCP endpoint.

Two-client testing on this Mac has passed. A physical two-computer LAN trial remains to be performed. Internet communication across separate networks is outside this application's scope.

## 5. Launch options

```sh
python chat_app.py --name Lucy --port 5003 --discovery-port 5000
```

| Option | Purpose | Default |
| --- | --- | --- |
| `--name` | Prefill the callsign; setup still asks for a passphrase | Empty |
| `--port` | TCP listening port | `5001` |
| `--discovery-port` | UDP discovery port; use the same value on both clients | `5000` |

## 6. Troubleshooting

| Problem | What to check |
| --- | --- |
| `python` is not found | Activate `chat_env` in that terminal first. |
| `No module named cryptography` | Activate the environment and run `python -m pip install -r requirements.txt`. |
| Tkinter cannot be imported or no window opens | Use a Python installation with Tkinter and run from a graphical desktop session. |
| Listening port is occupied | Close the old client or choose another `--port`; update the direct endpoint accordingly. |
| No peers appear | Complete setup in both windows, check the shared discovery port, then try direct connection. |
| Connection is refused | Check the remote app is running, has completed setup, and is listening at the entered address/port. |
| Password verification fails | Disconnect and set exactly matching passphrases on both clients; capitalization and spaces matter. |
| Send is disabled | Wait for password verification. If verification fails, correct the passphrase and reconnect. |
| Changing identity/passphrase is rejected | Disconnect first, make the change, then reconnect. |

## 7. Run the checks

With the environment activated:

```sh
python -m unittest -v test_system
```

For the live desktop integration check, install the separate report dependencies first, because this script uses Pillow for screenshots:

```sh
python -m pip install -r requirements-report.txt
python gui_check.py
```

The GUI check opens two app windows, exercises messaging and reconnection, and refreshes `reports/gui_checks.json` and the screenshot assets. macOS may request screen-recording permission; a permission dialog can overlap the captured app.

See [the final checks](reports/FINAL_CHECKS.md) for verified results and limitations, and [the report guide](reports/README.md) for rebuilding the academic report.
