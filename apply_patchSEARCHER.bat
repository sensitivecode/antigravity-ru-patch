@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo ========================================================
echo   Поиск Google Antigravity и установка русификации
echo ========================================================
echo.

set "PY_CMD="
python --version >nul 2>&1
if !errorlevel!==0 set "PY_CMD=python"

if not defined PY_CMD (
    py -3 --version >nul 2>&1
    if !errorlevel!==0 set "PY_CMD=py -3"
)

if not defined PY_CMD (
    echo [ОШИБКА] Python 3 не найден ^(возможно, сработала заглушка Microsoft Store^).
    echo          Установите Python 3 с python.org и повторите попытку.
    pause
    exit /b 1
)

if "%~1"=="--help" goto :show_help
if "%~1"=="-h" goto :show_help

set "_FOUND_TMP=%TEMP%\antigravity_search_%RANDOM%_%RANDOM%.tmp"
!PY_CMD! "%~dp0patch_antigravity_ru.py" --search --search-deep --search-out "%_FOUND_TMP%"
if !errorlevel! neq 0 (
    del /q "%_FOUND_TMP%" >nul 2>&1
    echo.
    echo [ОШИБКА] Папка с Antigravity не найдена автоматически.
    pause
    exit /b 1
)

set "FOUND_DIR="
if exist "%_FOUND_TMP%" (
    for /f "usebackq delims=" %%I in ("%_FOUND_TMP%") do set "FOUND_DIR=%%I"
    del /q "%_FOUND_TMP%" >nul 2>&1
)

if not defined FOUND_DIR (
    echo [ОШИБКА] Не удалось прочитать найденный путь.
    pause
    exit /b 1
)

echo.
echo [OK] Будет использована папка: "!FOUND_DIR!"
set "USE_FOUND=Y"
set /p "USE_FOUND=Перейти к установке патча в эту папку? [Y/n]: "
for %%K in (n no н Н нет Нет НЕТ т Т) do if /I "!USE_FOUND!"=="%%K" goto :cancelled

echo.
call "%~dp0apply_patch.bat" --dir "!FOUND_DIR!" %*
exit /b !errorlevel!

:cancelled
echo Операция отменена.
pause
exit /b 0

:show_help
!PY_CMD! "%~dp0patch_antigravity_ru.py" --help
pause
exit /b 0
