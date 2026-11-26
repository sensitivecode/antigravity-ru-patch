# Antigravity Russian Localization Patch (`antigravity-ru-patch`)

**Language:** English | [Русский](README.ru.md)

Unofficial Russian localization patch for the **Google Antigravity** desktop application on Windows.

It translates both the **Electron desktop shell** (menus, tray, dialogs, auto-updater, setup wizard, SSH/WSL prompts) and the **Hub Web UI** (sidebar, chats, projects, workspaces, settings, permissions, plugins, MCP servers, hooks, automations, built-in browser, terminals, artifact/PDF/diff viewers, relative timestamps, and tool statuses) without modifying signed `.exe` binaries.

## Features

- **Non-invasive patching**: Modifies only `resources/app.asar` and creates an automatic pristine backup at `resources/app.asar.bak` before patching.
- **Chromium / Electron locale**: Injects `--lang=ru` so built-in Chromium elements and `Intl` date formatting use `locales/ru.pak`.
- **Electron shell localization**: Translates application menus, tray menu & active agent counters (with proper Russian pluralization), native dialogs, context menus (`window:show-context-menu`), IDE install wizard, and SSH/WSL status pages.
- **Real-time Hub UI translation**: Embeds a sandbox-compatible `MutationObserver` translator (`ru_dom_translator.js` + `ru_i18n.js`) with bounded memoization caching (`Map`, up to 5,000 entries) directly into `dist/preload.js`.
- **Content protection**: Skips Material Symbols / Codicon icon ligatures, Monaco/CodeMirror editors, `xterm` terminals, KaTeX math, code blocks, and user/assistant Markdown prose so code and formatting remain untouched.
- **Update-safe rollback**: `restore_patch.bat` / `--restore` checks if `app.asar` is currently patched before restoring, preventing accidental downgrade after an official Antigravity update.

## Requirements

- **OS**: Windows 10 / 11
- **App**: Google Antigravity desktop app (default path: `%LOCALAPPDATA%\Programs\antigravity`)
- **Python**: Python 3.8+ installed from [python.org](https://www.python.org/) and added to `PATH`

## Quick Start

1. Download or clone this repository.
2. Save any unsaved work and close **Google Antigravity** (or leave it open — the installer will prompt you to close it gracefully first).
3. Run **`apply_patch.bat`** (for a custom install directory, run `apply_patch.bat --dir "C:\Path\to\antigravity"`).
4. Launch Antigravity when prompted.

## Manual CLI Usage

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

## Rollback & Troubleshooting

- **Restore original English UI**: Run **`restore_patch.bat`** or `python patch_antigravity_ru.py --restore`.
- **App fails to start after patching**: Run **`restore_patch.bat`** to revert `resources/app.asar` from `resources/app.asar.bak` (a future Antigravity release may enable Electron's `EnableEmbeddedAsarIntegrityValidation` fuse, which `patch_antigravity_ru.py` checks and warns about).
- **After an Antigravity update**: Official updates overwrite `resources/app.asar`. Simply re-run **`apply_patch.bat`** — it will detect the new unpatched `app.asar`, refresh `app.asar.bak`, and re-apply the translation.

## Repository Structure

| File | Description |
| :--- | :--- |
| `apply_patch.bat` | Interactive Windows installer (checks Python, closes Antigravity gracefully, applies patch) |
| `restore_patch.bat` | Interactive rollback script restoring `resources/app.asar.bak` |
| `patch_antigravity_ru.py` | Pure-Python ASAR reader/writer (recomputes SHA-256 block integrity) and shell patcher |
| `ru_i18n.js` | Exact dictionary, regex templates, and Russian pluralization rules (`pluralRu`) |
| `ru_dom_translator.js` | Sandbox-safe DOM `MutationObserver` translator with memoization cache |
| `README.txt` | Plain-text quick reference |

## Disclaimer

This is an unofficial community localization patch and is not affiliated with or endorsed by Google. Use at your own risk.
