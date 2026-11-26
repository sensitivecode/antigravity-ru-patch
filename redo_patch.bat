@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo ========================================================
echo   Откат Google Antigravity на английский (redo_patch)
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

set "_DIR_TMP=%TEMP%\antigravity_redo_dir_%RANDOM%_%RANDOM%.tmp"
!PY_CMD! "%~dp0patch_antigravity_ru.py" %* --print-dir > "%_DIR_TMP%"
set "INSTALL_DIR="
if exist "%_DIR_TMP%" (
    for /f "usebackq delims=" %%I in ("%_DIR_TMP%") do set "INSTALL_DIR=%%I"
    del /q "%_DIR_TMP%" >nul 2>&1
)
if not defined INSTALL_DIR (
    echo [ОШИБКА] Не удалось определить папку установки Antigravity.
    echo          Передайте путь вручную: redo_patch.bat --dir "C:\Путь\к\antigravity"
    pause
    exit /b 1
)

set "AUTO_RELAUNCH=0"
tasklist /FI "IMAGENAME eq Antigravity.exe" 2>nul | find /I "Antigravity.exe" >nul
if !errorlevel!==0 goto :prompt_close
goto :run_restore

:prompt_close
echo [!] Приложение Antigravity сейчас запущено.
echo     ВАЖНО: сохраните все несохранённые данные перед продолжением!
echo.
set "AUTO_REDO=Y"
set /p "AUTO_REDO=Закрыть Antigravity, откатить патч на английский и перезапустить его? [Y/n]: "
for %%K in (n no нет Нет НЕТ т Т) do if /I "!AUTO_REDO!"=="%%K" goto :need_manual_close
set "AUTO_RELAUNCH=1"

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

:run_restore
!PY_CMD! "%~dp0patch_antigravity_ru.py" --restore %*
if !errorlevel! neq 0 (
    echo.
    echo [ОШИБКА] Не удалось откатить патч. Код ошибки: !errorlevel!
    pause
    exit /b !errorlevel!
)

echo.
echo [OK] Оригинальные файлы (английский язык) восстановлены.
if "!AUTO_RELAUNCH!"=="1" goto :auto_launch

set "LAUNCH_AGY=Y"
set /p "LAUNCH_AGY=Запустить Antigravity сейчас? [Y/n]: "
for %%K in (n no нет Нет НЕТ т Т) do if /I "!LAUNCH_AGY!"=="%%K" goto :done_no_launch

:auto_launch
if exist "!INSTALL_DIR!\Antigravity.exe" (
    echo Запуск Antigravity...
    explorer.exe "!INSTALL_DIR!\Antigravity.exe"
)
timeout /t 1 /nobreak >nul
exit /b 0

:done_no_launch
pause
exit /b 0

:show_help
!PY_CMD! "%~dp0patch_antigravity_ru.py" --help
pause
exit /b 0

:need_manual_close
echo.
echo Закройте Antigravity вручную ^(включая значок в трее^) и запустите redo_patch.bat снова.
pause
exit /b 1
