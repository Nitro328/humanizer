@echo off
setlocal

echo === Push project to GitHub ===
echo.
echo This will open a browser so you can log in to GitHub (one time only).
echo If you do not have a GitHub account yet, the browser lets you create one.
echo.

gh auth status >nul 2>nul
if errorlevel 1 (
    gh auth login --hostname github.com --git-protocol https --web
)

echo.
echo Creating the repository and pushing the code...
gh repo create humanizer --public --source=. --push

echo.
echo Done. Now:
echo   1. Open your GitHub repository in the browser.
echo   2. Go to the "Actions" tab and wait for "Build Android APK" to finish.
echo   3. Download the APK from the workflow artifacts (bottom of the run page).
echo   4. Put the APK in the "bin" folder next to this script, then run install.bat.
pause
