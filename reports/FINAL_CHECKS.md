# Final checks — 16 November 2026

## Verified environment

macOS, Python 3.15.2, Tk 9.1, cryptography 50.0.2. Application GUI uses only Tkinter/ttk and Canvas. Report packages are isolated in a separate requirements file.

## Automated checks

`chat_env/bin/python -m unittest -v test_system` — **9 test methods pass**, covering shared-salt Unicode encryption, wrong-key/tampered-token rejection, fragmented framing, invalid JSON/envelope/oversized-frame rejection, occupied TCP ports, repeated two-way sessions, password mismatch, handshake timeout, refused TCP connection, and reflected/incompatible handshake rejection.

`chat_env/bin/python test_encryption.py` — original encryption baseline passes.

Syntax/import checks are performed on all supported runtime modules and tooling. The unrelated legacy demonstrations are preserved.

## Actual desktop integration

`chat_env/bin/python gui_check.py` — two independent Tkinter windows, with fresh TCP ports and shared UDP discovery port 5099. Machine-readable results in `gui_checks.json` record:

- Required setup validation and passphrase visibility toggle.
- Composer disabled until verification.
- Automatic discovery in both directions.
- Direct loopback connection and bidirectional displayed chat.
- Composer visibility at 940 × 760.
- Disconnect restores inactive composer and connection controls.
- Successful reconnect.
- Wrong-password session rejected on both clients.

The screenshots are genuine captures. macOS initially blocked capture; later captures succeeded but the chat image includes an overlapping operating-system screen-recording permission dialog. No screenshot was fabricated or retouched to hide that limitation.

## Report verification

`chat_env/bin/python build_report.py` builds the editable DOCX and separately typeset PDF. `report_validation.json` records the actual PDF page count and main-body count. The final PDF has 30 main-body pages and 84 pages total. The body is approximately 6,700 words, with 15 sequentially cited references, architecture/use-case/class diagrams, actual results, and code/screenshots in separate appendices. PDF text and page numbering are checked; DOCX margins, font settings and numbering fields are structurally inspected. The DOCX has not been rendered in Word, so update its contents and inspect final pagination in the submission editor.

## Remaining limits

A physical two-device LAN trial and Windows/Linux GUI checks were not available. Local discovery evidence does not prove all firewalls, Wi-Fi networks or VPN routes will work. Internet chat is outside scope. No independent security audit, delivery acknowledgement, PAKE, verified public identity, forward secrecy, persistence or complete replay defense is implemented. The password-confirmation protocol remains educational and allows offline password guessing from captured exchanges.

Student/guide details are placeholders pending user input. Turnitin, signatures, and institutional approvals remain external requirements.
