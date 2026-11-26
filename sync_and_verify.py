#!/usr/bin/env python3
"""Developer verification & release packaging helper (excluded from release zip)."""
import os
import subprocess
import sys
import zipfile
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent
VERIFY_JS = REPO_DIR / "verify_patch.js"

DIST_FILES = [
    "patch_antigravity_ru.py",
    "ru_i18n.js",
    "ru_dom_translator.js",
    "apply_patch.bat",
    "apply_patchSEARCHER.bat",
    "patch_debug.bat",
    "redo_patch.bat",
    "restore_patch.bat",
    "README.md",
    "README.txt",
]

sys.path.insert(0, str(REPO_DIR))
import patch_antigravity_ru as p  # noqa: E402


def main() -> None:
    install_dir = p.resolve_install_dir(None)
    antigravity_exe = install_dir / "Antigravity.exe"
    ls_exe = install_dir / "resources" / "bin" / "language_server.exe"
    zip_path = p._get_desktop_dir() / "antigravity-ru-patch.zip"

    # 1. Normalize line endings on .bat and README.txt (CRLF, UTF-8 without BOM)
    for name in DIST_FILES:
        file_path = REPO_DIR / name
        if name.endswith(".bat") or name == "README.txt":
            text = file_path.read_bytes().decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\r\n")
            file_path.write_bytes(text.encode("utf-8"))

    # 2. Build Desktop release zip (dev scripts and .git* files are excluded)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name in DIST_FILES:
            zf.write(REPO_DIR / name, arcname=name)
    with zipfile.ZipFile(zip_path, "r") as zf:
        bad = zf.testzip()
        assert bad is None, f"Corrupt zip entry: {bad}"
        print(f"[zip] Verified {zip_path} ({zip_path.stat().st_size} bytes, {len(zf.namelist())} files)")
        for info in zf.infolist():
            print(f"      - {info.filename} ({info.file_size} bytes)")

    # 3. Verify 110-byte language_server prompt constant against installed exe
    assert len(p.LS_TITLE_PROMPT_OLD) == len(p.LS_TITLE_PROMPT_NEW) == 110
    print(f"[check] LS_TITLE_PROMPT exact length verified: {len(p.LS_TITLE_PROMPT_NEW)} bytes")
    if ls_exe.is_file():
        ls_bytes = ls_exe.read_bytes()
        old_cnt = ls_bytes.count(p.LS_TITLE_PROMPT_OLD)
        new_cnt = ls_bytes.count(p.LS_TITLE_PROMPT_NEW)
        assert old_cnt == 1 or new_cnt == 1, f"Unexpected counts: old={old_cnt}, new={new_cnt}"
        print(f"[check] Real language_server.exe occurrences: old={old_cnt}, new={new_cnt}")

    # 4. Run --dry-run
    res = subprocess.run(
        [sys.executable, str(REPO_DIR / "patch_antigravity_ru.py"), "--dry-run", "--dir", str(install_dir)],
        capture_output=True,
        text=True,
        check=True,
    )
    print("[dry-run]\n" + res.stdout.strip())

    # 5. Run Electron verify_patch.js (ELECTRON_RUN_AS_NODE=1)
    env = os.environ.copy()
    env["ELECTRON_RUN_AS_NODE"] = "1"
    v_res = subprocess.run(
        [str(antigravity_exe), str(VERIFY_JS)],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    print("[verify_patch.js]\n" + v_res.stdout.strip())

    # 6. Clean up _dry_run_app.asar
    dry_asar = REPO_DIR / "_dry_run_app.asar"
    if dry_asar.exists():
        dry_asar.unlink()
        print(f"[cleanup] Removed {dry_asar}")


if __name__ == "__main__":
    main()
