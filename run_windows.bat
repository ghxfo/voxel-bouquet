@echo off
title Voxel Bouquet
cd /d "%~dp0"
set PY=
where py >nul 2>nul && set PY=py
if not defined PY (where python >nul 2>nul && set PY=python)
if not defined PY (
  echo.
  echo  Python is not installed on this computer.
  echo  Install it from https://www.python.org/downloads/
  echo  During setup, tick "Add python.exe to PATH", then run this file again.
  echo.
  pause
  exit /b
)
echo.
echo  Getting things ready (the first time can take a minute)...
%PY% -m pip install --disable-pip-version-check -q -r requirements.txt
if errorlevel 1 (
  echo.
  echo  Could not install the required packages. Check your internet connection.
  pause
  exit /b
)
echo  Opening the bouquet...
%PY% voxel_bouquet.py %*
if errorlevel 1 pause
