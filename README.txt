================================================================
  Google Antigravity - Russian Localization Patch (Windows)
================================================================

Unofficial Russian localization patch for Google Antigravity.
Patches only resources\app.asar (with automatic backup to
resources\app.asar.bak) without modifying signed .exe binaries.

----------------------------------------------------------------
  Requirements
----------------------------------------------------------------
- Windows 10 / 11
- Google Antigravity desktop app
  (default: %LOCALAPPDATA%\Programs\antigravity)
- Python 3.8+ from python.org (added to PATH)

----------------------------------------------------------------
  Quick Start
----------------------------------------------------------------
1. Extract or clone all files into a folder.
2. Save any unsaved work in Antigravity.
3. Run apply_patch.bat
   (or for a custom path: apply_patch.bat --dir "C:\Path\to\antigravity")
4. Confirm closing Antigravity and launch it when done.

----------------------------------------------------------------
  Manual CLI Usage
----------------------------------------------------------------
Close Antigravity completely (including the system tray icon):
  python patch_antigravity_ru.py --apply

Custom installation path:
  python patch_antigravity_ru.py --apply --dir "C:\Path\to\antigravity"

----------------------------------------------------------------
  Rollback & Troubleshooting
----------------------------------------------------------------
- To restore the original English UI, run restore_patch.bat or:
  python patch_antigravity_ru.py --restore
- If Antigravity fails to launch after patching (for example, if a
  future version enables ASAR integrity validation), run
  restore_patch.bat to revert from resources\app.asar.bak.
- After an official Antigravity update, simply re-run apply_patch.bat.
- Running restore_patch.bat on an unpatched app.asar safely skips
  rollback so a newer version is never overwritten by an old backup.

----------------------------------------------------------------
  Files
----------------------------------------------------------------
- apply_patch.bat         : Windows installer script
- restore_patch.bat       : Rollback script
- patch_antigravity_ru.py : Python ASAR patcher & integrity updater
- ru_i18n.js              : Russian dictionary, regex rules, plurals
- ru_dom_translator.js    : Cached DOM MutationObserver translator
- README.txt              : This file
- README.md               : GitHub documentation
