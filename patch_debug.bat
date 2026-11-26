@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo ========================================================
echo   Отладка и сброс русификатора Google Antigravity
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

echo ВНИМАНИЕ: скрипт закроет Antigravity, откатит перевод, сбросит
echo           локаль на английский, повторно установит патч и запустит
echo           запись живого лога на Рабочий стол ^(папка patchdebug^).
echo.
set "CONT_DBG=Y"
set /p "CONT_DBG=Продолжить отладочный запуск? [Y/n]: "
for %%K in (n no н Н нет Нет НЕТ т Т) do if /I "!CONT_DBG!"=="%%K" goto :cancelled

!PY_CMD! "%~dp0patch_antigravity_ru.py" --debug %*
if !errorlevel! neq 0 (
    echo.
    echo [ОШИБКА] Отладочный запуск завершился с кодом !errorlevel!.
    pause
    exit /b !errorlevel!
)

pause
exit /b 0

:cancelled
echo Отладка отменена.
pause
exit /b 0

:show_help
!PY_CMD! "%~dp0patch_antigravity_ru.py" --help
pause
exit /b 0
