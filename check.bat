@echo off
setlocal enabledelayedexpansion

set "GH=gh"
where gh >nul 2>nul || set "GH=C:\Program Files\GitHub CLI\gh.exe"

echo === Build status (Nitro328/humanizer) ===
"%GH%" run list --repo Nitro328/humanizer --limit 1
echo.

rem Get the conclusion of the latest run
"%GH%" run list --repo Nitro328/humanizer --limit 1 --json conclusion --jq ".[0].conclusion" > "%TEMP%\gh_conclusion.txt" 2>nul
set /p CONCLUSION=<"%TEMP%\gh_conclusion.txt"

if "!CONCLUSION!"=="success" (
    echo Build DONE. Downloading the APK...
    "%GH%" run download --repo Nitro328/humanizer --name humanizer-apk --dir "%~dp0apk_download"
    echo.
    echo APK saved in: apk_download\
    echo   1. Move the .apk into the bin\ folder.
    echo   2. Connect the phone via USB and run install.bat.
) else if "!CONCLUSION!"=="failure" (
    echo Build FAILED. Tell the assistant: "controlla".
) else (
    echo Still building. Run this again in a few minutes.
)

pause
