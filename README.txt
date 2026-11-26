================================================================
  Русификатор Google Antigravity v1.1.0 (Windows)
  Google Antigravity Russian Localization Patcher v1.1.0
================================================================

----------------------------------------------------------------
  [RU] Что именно изменяется
----------------------------------------------------------------
Патч изменяет ТОЛЬКО два файла (оба сохраняются в .bak):
1. resources\app.asar (бэкап: resources\app.asar.bak)
   — интерфейс оболочки Electron и веб-интерфейс Hub UI.
2. resources\bin\language_server.exe (бэкап: language_server.exe.bak)
   — точечная замена 110 байт в промпте заголовков чатов
     (отключается флагом --no-ru-titles).

Остальные файлы (Antigravity.exe, locales\*.pak, DLL и др.)
не изменяются.

ВАЖНО: изменение language_server.exe нарушает его цифровую
подпись (если она присутствует в сборке), поэтому антивирус
или Windows SmartScreen могут выдавать предупреждение. Если
хотите патчить только app.asar, используйте --no-ru-titles.

----------------------------------------------------------------
  [RU] Какой батник запускать
----------------------------------------------------------------
- apply_patch.bat         — стандартный путь (%LOCALAPPDATA%\Programs\antigravity)
- apply_patchSEARCHER.bat — нестандартная папка на ПК (поиск по эталону +
                            подтверждение [Y/n] или выбор из списка)
- patch_debug.bat         — диагностика, сброс и живой лог в Desktop\patchdebug
- restore_patch.bat       — откат к оригинальным .bak-файлам

Если русификатор слетел после обновления Antigravity — закройте
приложение и повторно запустите apply_patch.bat (или apply_patchSEARCHER.bat).

----------------------------------------------------------------
  [RU] Диагностика (patch_debug.bat)
----------------------------------------------------------------
- Создаёт папку patchdebug на Рабочем столе и пишет patch_debug_*.log.
- Команды терминала: stop, status, open, logs on, logs off.
- ПРИВАТНОСТЬ: по умолчанию пишутся только шаги патчера. Логи самого
  Antigravity (main.log / language_server.log) включаются ТОЛЬКО
  командой logs on и могут содержать имя пользователя в путях и
  фрагменты запросов — проверяйте лог перед публикацией.

----------------------------------------------------------------
  [RU] Отказ от ответственности
----------------------------------------------------------------
Неофициальный проект сообщества. Не связан с Google LLC и не
поддерживается Google. Товарные знаки принадлежат их владельцам.
Оригинальные файлы Antigravity не распространяются. ПО предоставляется
"как есть" (AS IS), пользователь применяет патч на свой риск.

================================================================
  [EN] Summary & Usage
================================================================
- Modifies ONLY resources/app.asar (.bak) and optionally
  resources/bin/language_server.exe (.bak, skip via --no-ru-titles).
  Modifying language_server.exe breaks Authenticode signatures and may
  trigger antivirus/SmartScreen warnings.
- Run apply_patch.bat (default path), apply_patchSEARCHER.bat (custom
  path discovery with [Y/n] confirmation), restore_patch.bat (revert),
  or patch_debug.bat (live patcher log in Desktop\patchdebug; privacy:
  Antigravity logs require explicit "logs on").
- Unofficial community patch, NOT affiliated with Google LLC, provided AS IS.

----------------------------------------------------------------
  Состав архива / Archive Contents
----------------------------------------------------------------
- apply_patch.bat         — установка (стандартный путь)
- apply_patchSEARCHER.bat — поиск нестандартной папки + установка
- patch_debug.bat         — диагностика и живой лог (Desktop\patchdebug)
- restore_patch.bat       — откат к оригиналу
- patch_antigravity_ru.py — основной скрипт патча (ASAR, поиск, дебаг)
- ru_i18n.js              — словарь и правила склонения/шаблонов
- ru_dom_translator.js    — DOM-переводчик веб-интерфейса (с кэшем)
- README.txt              — эта инструкция
- README.md               — полное описание (RU / EN)
