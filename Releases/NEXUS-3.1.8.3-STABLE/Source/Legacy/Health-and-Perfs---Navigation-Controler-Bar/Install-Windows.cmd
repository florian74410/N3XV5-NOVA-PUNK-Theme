@echo off
cd /d "%~dp0"
py -3 scripts\install.py
if errorlevel 1 (
  echo Installation impossible. Verifiez Python 3.10+ et votre connexion Internet.
  pause
)
