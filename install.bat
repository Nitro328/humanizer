@echo off
setlocal enabledelayedexpansion

echo === Humanizer installer ===
echo.
echo ATTENTION: watch the phone. If it asks to install the app, tap Allow/Install.

adb wait-for-device
if errorlevel 1 (
    echo [ERROR] No device detected or adb is not in PATH.
    echo Enable USB debugging on the phone and connect it via cable.
    pause
    exit /b 1
)

set "APK="
for /f "delims=" %%f in ('dir /b /o-d "%~dp0bin\*.apk" 2^>nul') do set "APK=%~dp0bin\%%f" & goto :found
for /f "delims=" %%f in ('dir /b /o-d "%~dp0apk_download\*.apk" 2^>nul') do set "APK=%~dp0apk_download\%%f" & goto :found

:found
if "!APK!"=="" (
    echo [ERROR] No APK found in bin\ or apk_download\.
    echo Run check.bat to download the APK first.
    pause
    exit /b 1
)

echo Removing the old version...
adb uninstall org.example.humanizer >nul 2>nul

echo Installing !APK! ...
adb install "!APK!"
if errorlevel 1 (
    echo First attempt failed. Retrying in 3 seconds...
    timeout /t 3 >nul
    adb install "!APK!"
    if errorlevel 1 (
        echo.
        echo [ERROR] Install failed.
        echo Check that "Install via USB" is ON in Developer Options on the phone,
        echo and confirm the dialog on the phone when it appears.
        pause
        exit /b 1
    )
)

echo.
echo Done. Open "Humanizer" on your phone.
pause
