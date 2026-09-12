@echo off
setlocal enabledelayedexpansion

echo === Humanizer installer ===
echo Looking for a connected Android device...

adb wait-for-device
if errorlevel 1 (
    echo [ERROR] No device detected or adb is not in PATH.
    echo Enable USB debugging on the phone and connect it via cable.
    pause
    exit /b 1
)

set "APK="
for /f "delims=" %%f in ('dir /b /o-d "%~dp0bin\*.apk" 2^>nul') do (
    set "APK=%~dp0bin\%%f"
    goto :found
)

:found
if "!APK!"=="" (
    echo [ERROR] No APK found in bin\.
    echo Build it first with build.sh on Linux/WSL, then copy the APK into bin\.
    pause
    exit /b 1
)

echo Installing: !APK!
adb install -r "!APK!"
if errorlevel 1 (
    echo [ERROR] Install failed.
    pause
    exit /b 1
)

echo.
echo Done. Open "Humanizer" on your phone.
pause
