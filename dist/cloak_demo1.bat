@echo off
title Cloak Demo — Chris (port 5001)
cd /d "%~dp0"

:: Demo data directory — isolated from your real Cloak identity
set CLOAK_DATA_DIR=%TEMP%\CloakDemoChris
set CLOAK_PASSPHRASE=cloak_demo

echo ============================================================
echo   Cloak Demo — Chris  (listens on port 5001)
echo ============================================================
echo.
echo  CONNECTING:
echo    Neil's address is 127.0.0.1:5002
echo    Click [Direct Connect] and enter Neil's address.
echo    Or click [Search LAN] to find Neil automatically.
echo.
echo  NEW FEATURES (try after connecting):
echo    [Safety Number] — view and verify the 60-digit safety number
echo    [Send File]     — send any file to the current peer
echo    [Create Group]  — start an encrypted group chat
echo    [Invite to Group] — add the selected peer to your group
echo    [Group Msg]     — send to all group members at once
echo.
echo  Press any key to launch...
pause >nul

cloak.exe --name Chris --port 5001
pause
