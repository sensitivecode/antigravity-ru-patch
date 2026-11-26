# Antigravity Russian Localization Patch (`antigravity-ru-patch`)

[English](#english) | [Русский](#русский)

---

## English

Unofficial Russian localization patch for the **Google Antigravity** desktop application on Windows.

It translates both the **Electron desktop shell** (menus, tray, dialogs, auto-updater, setup wizard, SSH/WSL prompts) and the **Hub Web UI** (sidebar, chats, projects, workspaces, settings, permissions, plugins, MCP servers, hooks, automations, built-in browser, terminals, artifact/PDF/diff viewers, relative timestamps, and tool statuses) without modifying signed `.exe` binaries.

### Features

- **Non-invasive patching**: Modifies only `resources/app.asar` and creates an automatic pristine backup at `resources/app.asar.bak` before patching.
- **Chromium / Electron locale**: Injects `--lang=ru` so built-in Chromium elements and `Intl` date formatting use `locales/ru.pak`.
- **Electron shell localization**: Translates application menus, tray menu & active agent counters (with proper Russian pluralization), native dialogs, context menus (`window:show-context-menu`), IDE install wizard, and SSH/WSL status pages.
- **Real-time Hub UI translation**: Embeds a sandbox-compatible `MutationObserver` translator (`ru_dom_translator.js` + `ru_i18n.js`) with bounded memoization caching (`Map`, up to 5,000 entries) directly into `dist/preload.js`.
- **Content protection**: Skips Material Symbols / Codicon icon ligatures, Monaco/CodeMirror editors, `xterm` terminals, KaTeX math, code blocks, and user/assistant Markdown prose so code and formatting remain untouched.
- **Update-safe rollback**: `restore_patch.bat` / `--restore` checks if `app.asar` is currently patched before restoring, preventing accidental downgrade after an official Antigravity update.

### Requirements

- **OS**: Windows 10 / 11
- **App**: Google Antigravity desktop app (default path: `%LOCALAPPDATA%\Programs\antigravity`)
- **Python**: Python 3.8+ installed from [python.org](https://www.python.org/) and added to `PATH`

### Quick Start

1. Download or clone this repository.
2. Save any unsaved work and close **Google Antigravity** (or leave it open — the installer will prompt you to close it gracefully first).
3. Run **`apply_patch.bat`** (for a custom install directory, run `apply_patch.bat --dir "C:\Path\to\antigravity"`).
4. Launch Antigravity when prompted.

### Manual CLI Usage

Close Antigravity completely (including the system tray icon), then run:

```bat
python patch_antigravity_ru.py --apply
```

Custom installation directory:

```bat
python patch_antigravity_ru.py --apply --dir "C:\Path\to\antigravity"
```

Dry-run verification (builds `_dry_run_app.asar` without touching your installation):

```bat
python patch_antigravity_ru.py --dry-run
```

### Rollback & Troubleshooting

- **Restore original English UI**: Run **`restore_patch.bat`** or `python patch_antigravity_ru.py --restore`.
- **App fails to start after patching**: Run **`restore_patch.bat`** to revert `resources/app.asar` from `resources/app.asar.bak` (a future Antigravity release may enable Electron's `EnableEmbeddedAsarIntegrityValidation` fuse, which `patch_antigravity_ru.py` checks and warns about).
- **After an Antigravity update**: Official updates overwrite `resources/app.asar`. Simply re-run **`apply_patch.bat`** — it will detect the new unpatched `app.asar`, refresh `app.asar.bak`, and re-apply the translation.

### Repository Structure

| File | Description |
| :--- | :--- |
| `apply_patch.bat` | Interactive Windows installer (checks Python, closes Antigravity gracefully, applies patch) |
| `restore_patch.bat` | Interactive rollback script restoring `resources/app.asar.bak` |
| `patch_antigravity_ru.py` | Pure-Python ASAR reader/writer (recomputes SHA-256 block integrity) and shell patcher |
| `ru_i18n.js` | Exact dictionary, regex templates, and Russian pluralization rules (`pluralRu`) |
| `ru_dom_translator.js` | Sandbox-safe DOM `MutationObserver` translator with memoization cache |
| `README.txt` | Plain-text quick reference |

### Disclaimer

This is an unofficial community localization patch and is not affiliated with or endorsed by Google. Use at your own risk.

---

## Русский

Неофициальный патч русификации десктопного приложения **Google Antigravity** для Windows.

Переводит как **оболочку Electron** (меню, трей, диалоги, автообновление, мастер установки, окна SSH/WSL), так и **веб-интерфейс Hub** (боковая панель, чаты, проекты, рабочие области, настройки, разрешения, плагины, MCP-серверы, хуки, автоматизации, встроенный браузер, терминалы, просмотрщики артефактов/PDF/diff, относительное время и статусы инструментов) без изменения подписанных `.exe`-файлов.

### Возможности

- **Безопасное патчирование**: изменяется только `resources/app.asar`, а перед первым патчем автоматически создаётся резервная копия `resources/app.asar.bak`.
- **Локаль Chromium / Electron**: добавляет флаг `--lang=ru`, чтобы встроенные элементы Chromium и форматирование дат (`Intl`) использовали `locales/ru.pak`.
- **Перевод оболочки Electron**: переводит верхнее меню приложения, меню и счётчик агентов в трее (с правильными русскими склонениями), системные диалоги, контекстные меню (`window:show-context-menu`), мастер установки IDE и страницы состояния SSH/WSL.
- **Перевод веб-интерфейса в реальном времени**: встраивает в `dist/preload.js` совместимый с `sandbox: true` DOM-переводчик (`ru_dom_translator.js` + `ru_i18n.js`) на базе `MutationObserver` с кэшированием (`Map`, до 5000 записей).
- **Защита кода и иконок**: не затрагивает текстовые лигатуры иконок Material Symbols / Codicon, редакторы кода (Monaco / CodeMirror), терминал (`xterm`), формулы KaTeX, блоки кода и текст сообщений в Markdown.
- **Безопасный откат после обновлений**: `restore_patch.bat` / `--restore` сначала проверяет, пропатчен ли текущий `app.asar`, чтобы не заменить новую версию Antigravity старым бэкапом.

### Требования

- **ОС**: Windows 10 / 11
- **Приложение**: Google Antigravity для Windows (путь по умолчанию: `%LOCALAPPDATA%\Programs\antigravity`)
- **Python**: Python 3.8+ с [python.org](https://www.python.org/), добавленный в `PATH`

### Быстрая установка

1. Скачайте или клонируйте этот репозиторий.
2. Сохраните несохранённые данные и закройте **Google Antigravity** (или оставьте открытым — установщик предложит мягко закрыть его).
3. Запустите **`apply_patch.bat`** (для нестандартной папки установки: `apply_patch.bat --dir "C:\Путь\к\antigravity"`).
4. Подтвердите запуск Antigravity после завершения.

### Ручной запуск через консоль

Закройте Antigravity полностью (включая значок в системном трее), затем выполните:

```bat
python patch_antigravity_ru.py --apply
```

Для нестандартного пути установки:

```bat
python patch_antigravity_ru.py --apply --dir "C:\Путь\к\antigravity"
```

Тестовый прогон без изменения установленного приложения (собирает `_dry_run_app.asar`):

```bat
python patch_antigravity_ru.py --dry-run
```

### Откат и устранение неполадок

- **Вернуть английский интерфейс**: запустите **`restore_patch.bat`** или `python patch_antigravity_ru.py --restore`.
- **Приложение не запускается после патча**: запустите **`restore_patch.bat`**, чтобы восстановить `resources/app.asar` из `resources/app.asar.bak` (в будущих версиях Antigravity может быть включена проверка целостности ASAR `EnableEmbeddedAsarIntegrityValidation`, о которой `patch_antigravity_ru.py` предупреждает при проверке).
- **После обновления Antigravity**: официальное обновление перезаписывает `resources/app.asar`. Просто снова запустите **`apply_patch.bat`** — скрипт обнаружит новый непропатченный `app.asar`, обновит резервную копию `app.asar.bak` и повторно применит перевод.

### Структура репозитория

| Файл | Назначение |
| :--- | :--- |
| `apply_patch.bat` | Интерактивный установщик для Windows (проверка Python, плавное закрытие Antigravity, применение патча) |
| `restore_patch.bat` | Скрипт отката к оригиналу из `resources/app.asar.bak` |
| `patch_antigravity_ru.py` | Python-патчер ASAR (чтение/сборка, пересчёт SHA-256 целостности блоков, замена строк оболочки) |
| `ru_i18n.js` | Словарь точных переводов, regex-правила и русские склонения (`pluralRu`) |
| `ru_dom_translator.js` | Безопасный `MutationObserver`-переводчик с мемоизацией для веб-интерфейса |
| `README.txt` | Краткая текстовая инструкция |

### Отказ от ответственности

Это неофициальный пользовательский патч локализации, не связанный с компанией Google и не поддерживаемый ею. Используйте на свой страх и риск.
