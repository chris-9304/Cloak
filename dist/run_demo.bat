@echo off
title Cloak Demo Launcher
cd /d "%~dp0"

echo ============================================================
echo   Cloak 0.4.0 — Two-User Demo Launcher
echo ============================================================
echo.
echo  This opens TWO separate Cloak windows on the same machine:
echo.
echo    [Window 1] Chris  — listens on port 5001
echo    [Window 2] Neil   — listens on port 5002
echo.
echo ============================================================
echo  HOW TO CONNECT (choose one):
echo ============================================================
echo.
echo    Option A — Direct Connect (fastest):
echo      In Neil's window, click [Direct Connect]
echo      Enter:  Host = 127.0.0.1   Port = 5001
echo      Click Connect.
echo.
echo    Option B — Invite Code:
echo      In Chris's window, click [Invite Code], then [Copy Code].
echo      In Neil's window, click [Join via Code], paste, click Connect.
echo.
echo    Option C — LAN Search:
echo      In either window, click [Search LAN].
echo.
echo ============================================================
echo  FEATURES TO TRY AFTER CONNECTING:
echo ============================================================
echo.
echo  1. SAFETY NUMBER VERIFICATION
echo       Click [Safety Number] to see your 60-digit safety number.
echo       Compare it with your peer out-of-band (phone call, etc.).
echo       Click [Mark Verified] once confirmed — the peer gets a
echo       green check mark in the peer list.
echo.
echo  2. GROUP CHAT (end-to-end encrypted, multi-party)
echo       In Chris's window, click [Create Group] and name the group.
echo       Then click [Invite to Group] while Neil is selected.
echo       Both can now click [Group Msg] next to the message box
echo       to send encrypted messages to the entire group.
echo       (Connect a third instance on port 5003 to add more members.)
echo.
echo  3. FILE TRANSFER (encrypted, any file type)
echo       Click [Send File] in the left panel.
echo       Enter the full path to any file (photo, document, zip, etc.).
echo       The peer receives it automatically — saved to their Downloads
echo       folder with a confirmation shown in the status bar.
echo.
echo  4. KEYBOARD SHORTCUTS
echo       Ctrl+V  = paste into any text field
echo       Escape  = close any modal dialog
echo       Ctrl+Q  = quit
echo.
echo ============================================================
echo  Press any key to launch both windows...
pause >nul

:: Launch Chris in a new window
start "Cloak Demo — Chris" cmd /k "cd /d "%~dp0" && set CLOAK_DATA_DIR=%TEMP%\CloakDemoChris && set CLOAK_PASSPHRASE=cloak_demo && cloak.exe --name Chris --port 5001"

:: Small delay so Chris binds its port first
timeout /t 1 /nobreak >nul

:: Launch Neil in a new window
start "Cloak Demo — Neil" cmd /k "cd /d "%~dp0" && set CLOAK_DATA_DIR=%TEMP%\CloakDemoNeil && set CLOAK_PASSPHRASE=cloak_demo && cloak.exe --name Neil --port 5002"

echo.
echo  Both windows launched! Follow the instructions above.
echo  (This window can be closed.)
echo.
pause
