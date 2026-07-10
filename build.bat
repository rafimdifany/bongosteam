@echo off
echo Building BongoSteam...
pyinstaller bongo_steam.spec --clean
echo.
echo Build complete. Check dist/BongoSteam.exe
pause