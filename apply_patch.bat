@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo ========================================================
echo   Патч русификации Google Antigravity
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

set "INSTALL_DIR="
for /f "usebackq delims=" %%I in (`!PY_CMD! "%~dp0patch_antigravity_ru.py" --print-dir %*`) do set "INSTALL_DIR=%%I"
if not defined INSTALL_DIR (
    echo [ОШИБКА] Не удалось определить папку установки Antigravity.
    echo          Передайте путь вручную: apply_patch.bat --dir "C:\Путь\к\antigravity"
    pause
    exit /b 1
)

tasklist /FI "IMAGENAME eq Antigravity.exe" 2>nul | find /I "Antigravity.exe" >nul
if !errorlevel!==0 goto :prompt_close
goto :run_patch

:prompt_close
echo [!] Приложение Antigravity сейчас запущено.
echo     Чтобы пропатчить resources\app.asar, приложение нужно закрыть.
echo     ВАЖНО: сохраните все несохранённые данные перед продолжением!
echo.
set "CLOSE_AGY=Y"
set /p "CLOSE_AGY=Закрыть Antigravity сейчас и установить патч? [Y/n]: "
if /I "!CLOSE_AGY!"=="n" goto :need_manual_close
if /I "!CLOSE_AGY!"=="н" goto :need_manual_close

echo Плавное закрытие Antigravity...
taskkill /IM Antigravity.exe >nul 2>&1
set /a WAIT_TRIES=0

:wait_graceful
timeout /t 1 /nobreak >nul
tasklist /FI "IMAGENAME eq Antigravity.exe" 2>nul | find /I "Antigravity.exe" >nul
if !errorlevel! neq 0 goto :wait_settled
set /a WAIT_TRIES+=1
if !WAIT_TRIES! lss 4 goto :wait_graceful

echo Принудительное завершение дерева процессов Antigravity...
taskkill /F /T /IM Antigravity.exe >nul 2>&1

:wait_close
timeout /t 1 /nobreak >nul
tasklist /FI "IMAGENAME eq Antigravity.exe" 2>nul | find /I "Antigravity.exe" >nul
if !errorlevel!==0 goto :wait_close

:wait_settled
timeout /t 1 /nobreak >nul

:run_patch
!PY_CMD! "%~dp0patch_antigravity_ru.py" --apply %*
if !errorlevel! neq 0 (
    echo.
    echo [ОШИБКА] Патч не применён. Код ошибки: !errorlevel!
    pause
    exit /b !errorlevel!
)

echo.
echo [OK] Операция завершена.
set "LAUNCH_AGY=Y"
set /p "LAUNCH_AGY=Запустить Antigravity сейчас? [Y/n]: "
if /I "!LAUNCH_AGY!"=="n" goto :done_no_launch
if /I "!LAUNCH_AGY!"=="н" goto :done_no_launch
if exist "!INSTALL_DIR!\Antigravity.exe" (
    echo Запуск Antigravity...
    explorer.exe "!INSTALL_DIR!\Antigravity.exe"
)
timeout /t 1 /nobreak >nul
exit /b 0

:done_no_launch
pause
exit /b 0

:need_manual_close
echo.
echo Закройте Antigravity вручную ^(включая значок в трее^) и запустите apply_patch.bat снова.
pause
exit /b 1
