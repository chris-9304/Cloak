@echo off
title Cloak Demo — Neil (port 5002)
cd /d "%~dp0"

:: Demo data directory — isolated from your real Cloak identity
set CLOAK_DATA_DIR=%TEMP%\CloakDemoNeil
set CLOAK_PASSPHRASE=cloak_demo

echo ============================================================
echo   Cloak Demo — Neil  (listens on port 5002)
echo ============================================================
echo.
echo  CONNECTING:
echo    Chris's address is 127.0.0.1:5001
echo    Click [Direct Connect] and enter Chris's address.
echo    Or click [Search LAN] to find Chris automatically.
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

cloak.exe --name Neil --port 5002
pause
