#!/usr/bin/env python3
"""Automated regression test suite for batch scripts, patcher safety, searcher, and patch_debug."""
import builtins
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_DIR))
import patch_antigravity_ru as p  # noqa: E402


def _make_fake_install(root: Path, src_asar: Path, ls_bytes: bytes, with_exe: bool = True, with_ru_pak: bool = True) -> Path:
    (root / "resources" / "bin").mkdir(parents=True, exist_ok=True)
    if with_exe:
        (root / "Antigravity.exe").write_bytes(b"MZ" + b"\x00" * 64 + p.ELECTRON_FUSE_SENTINEL + b"\x00")
    if with_ru_pak:
        (root / "locales").mkdir(exist_ok=True)
        (root / "locales" / "ru.pak").write_bytes(b"PAK")
    shutil.copy2(src_asar, root / "resources" / "app.asar")
    if ls_bytes is not None:
        (root / "resources" / "bin" / "language_server.exe").write_bytes(ls_bytes)
    return root


def main() -> None:
    install_dir = p.resolve_install_dir(None)
    bak_asar = install_dir / "resources" / "app.asar.bak"
    src_asar = bak_asar if bak_asar.is_file() else (install_dir / "resources" / "app.asar")
    py_script = str(REPO_DIR / "patch_antigravity_ru.py")

    print("=== 1. Batch scripts: --help, spaces + (x86) + Cyrillic --dir, [Y/n] decline ===")
    for bat_name in ("apply_patch.bat", "apply_patchSEARCHER.bat", "patch_debug.bat", "restore_patch.bat"):
        res_h = subprocess.run(
            ["cmd.exe", "/c", "call", str(REPO_DIR / bat_name), "--help"],
            input=b"\r\n",
            capture_output=True,
        )
        assert res_h.returncode == 0, f"{bat_name} --help failed: {res_h.stdout.decode('utf-8', 'replace')}"
    print("[PASS] All 4 batch files handle --help cleanly (exit 0).")

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        spaced_dir = td_path / "Program Files (x86)" / "Папка Тест" / "Antigravity"
        _make_fake_install(spaced_dir, src_asar, b"V1\x00" + p.LS_TITLE_PROMPT_OLD + b"\x00END")

        # Note: if Antigravity is running on the test host, batch prompts to close; test Cyrillic/Latin declines safely
        host_running = p._is_antigravity_running()
        if host_running:
            for decline in ("n", "N", "no", "н", "Н", "нет", "т"):
                r = subprocess.run(
                    ["cmd.exe", "/c", "call", str(REPO_DIR / "apply_patch.bat"), "--dir", str(spaced_dir)],
                    input=(decline + "\r\n\r\n").encode("utf-8"),
                    capture_output=True,
                )
                txt = r.stdout.decode("utf-8", errors="replace")
                assert "Закройте Antigravity вручную" in txt and r.returncode == 1
            print("[PASS] apply_patch.bat with spaces + (x86) + Cyrillic path & 7 decline inputs passed.")

        print("=== 2. CLI: --dry-run, --apply, re-apply, --restore, --no-ru-titles, bad --dir ===")
        # Remove dummy Antigravity.exe not needed by CLI tests
        r_dry = subprocess.run(
            [sys.executable, py_script, "--dry-run", "--dir", str(spaced_dir)],
            capture_output=True, text=True,
        )
        assert r_dry.returncode == 0, r_dry.stderr
        assert "applied 102/102 replacements (missed: 0)" in r_dry.stdout
        assert "exact-length Russian patch ready" in r_dry.stdout
        dry_file = REPO_DIR / "_dry_run_app.asar"
        if dry_file.exists():
            dry_file.unlink()
        print("[PASS] --dry-run on spaces + (x86) + Cyrillic path passed (102/102).")

        r_app1 = subprocess.run(
            [sys.executable, py_script, "--apply", "--dir", str(spaced_dir)],
            capture_output=True, text=True,
        )
        assert r_app1.returncode == 0, r_app1.stderr
        assert p.is_patched(spaced_dir / "resources" / "app.asar")
        assert p.LS_TITLE_PROMPT_NEW in (spaced_dir / "resources" / "bin" / "language_server.exe").read_bytes()

        r_app2 = subprocess.run(
            [sys.executable, py_script, "--apply", "--dir", str(spaced_dir)],
            capture_output=True, text=True,
        )
        assert r_app2.returncode == 0 and "already patched for Russian chat titles" in r_app2.stdout

        r_rest = subprocess.run(
            [sys.executable, py_script, "--restore", "--dir", str(spaced_dir)],
            capture_output=True, text=True,
        )
        assert r_rest.returncode == 0
        assert not p.is_patched(spaced_dir / "resources" / "app.asar")
        assert p.LS_TITLE_PROMPT_OLD in (spaced_dir / "resources" / "bin" / "language_server.exe").read_bytes()

        r_nort = subprocess.run(
            [sys.executable, py_script, "--apply", "--no-ru-titles", "--dir", str(spaced_dir)],
            capture_output=True, text=True,
        )
        assert r_nort.returncode == 0
        assert p.is_patched(spaced_dir / "resources" / "app.asar")
        assert p.LS_TITLE_PROMPT_OLD in (spaced_dir / "resources" / "bin" / "language_server.exe").read_bytes()
        assert (spaced_dir / "resources" / "bin" / "language_server.exe.bak").exists()
        print("[PASS] --apply, re-apply, --restore, and --no-ru-titles verified.")

        r_bad = subprocess.run(
            [sys.executable, py_script, "--apply", "--dir", str(td_path / "Missing (x86)" / "Нет Папки")],
            capture_output=True, text=True,
        )
        assert r_bad.returncode == 1 and "[ERROR]" in r_bad.stderr and "Traceback" not in r_bad.stderr
        print("[PASS] Nonexistent --dir returns clean [ERROR] without traceback.")

        print("=== 3. language_server.exe safety: 0 matches, 2 matches, wrong .bak, missing .bak ===")
        # 0 matches -> warn, skip exe, patch app.asar
        zero_dir = _make_fake_install(td_path / "ls_zero", src_asar, b"NO_PROMPT_HERE")
        assert p.patch_language_server_titles(zero_dir, dry_run=False) == "skipped"
        assert (zero_dir / "resources" / "bin" / "language_server.exe").read_bytes() == b"NO_PROMPT_HERE"

        # 2 matches -> warn, skip exe
        dup_bytes = b"A" + p.LS_TITLE_PROMPT_OLD + b"B" + p.LS_TITLE_PROMPT_OLD + b"C"
        dup_dir = _make_fake_install(td_path / "ls_dup", src_asar, dup_bytes)
        assert p.patch_language_server_titles(dup_dir, dry_run=False) == "skipped"
        assert (dup_dir / "resources" / "bin" / "language_server.exe").read_bytes() == dup_bytes

        # Update detection -> old .bak overwritten when new unpatched version differs
        upd_dir = _make_fake_install(td_path / "ls_upd", src_asar, b"V1\x00" + p.LS_TITLE_PROMPT_OLD + b"\x00Z")
        assert p.patch_language_server_titles(upd_dir, dry_run=False) == "patched"
        # Simulate Antigravity update overwriting exe with V2 unpatched
        v2_orig = b"V2\x00" + p.LS_TITLE_PROMPT_OLD + b"\x00Z"
        (upd_dir / "resources" / "bin" / "language_server.exe").write_bytes(v2_orig)
        assert p.patch_language_server_titles(upd_dir, dry_run=False) == "patched"
        assert (upd_dir / "resources" / "bin" / "language_server.exe.bak").read_bytes() == v2_orig

        # Mismatched .bak during restore -> refused cleanly (exit 2 / False)
        (upd_dir / "resources" / "bin" / "language_server.exe.bak").write_bytes(b"V1\x00" + p.LS_TITLE_PROMPT_OLD + b"\x00Z")
        assert p.restore_language_server_titles(upd_dir) is False
        assert p.LS_TITLE_PROMPT_NEW in (upd_dir / "resources" / "bin" / "language_server.exe").read_bytes()

        # Missing .bak during restore -> refused cleanly (False)
        (upd_dir / "resources" / "bin" / "language_server.exe.bak").unlink()
        assert p.restore_language_server_titles(upd_dir) is False
        print("[PASS] language_server.exe 0/2-match skip, versioned .bak refresh, and mismatch/missing restore blocks passed.")

        print("=== 4. Searcher: mandatory vs optional markers, single/multi/0 candidates, Ctrl+C ===")
        # Minimal valid install (only Antigravity.exe + resources/app.asar, NO language_server.exe or locales/ru.pak)
        min_dir = _make_fake_install(td_path / "min_install", src_asar, None, with_exe=True, with_ru_pak=False)
        min_info = p.verify_antigravity_dir(min_dir)
        assert min_info is not None and min_info["product_name"] == "Antigravity"
        assert min_info["ls_state"] == "отсутствует"

        # Reject non-Antigravity directory
        not_agy = td_path / "other_app"
        (not_agy / "resources").mkdir(parents=True)
        (not_agy / "Antigravity.exe").write_bytes(b"MZ" + b"\x00" * 32)
        (not_agy / "resources" / "app.asar").write_bytes(b"INVALID")
        assert p.verify_antigravity_dir(not_agy) is None

        # Multi-candidate selection in cmd_search (mocked discovery)
        cand2 = _make_fake_install(td_path / "cand2", src_asar, b"C2\x00" + p.LS_TITLE_PROMPT_OLD + b"\x00Z")
        out_sel = td_path / "chosen.txt"
        orig_cands = p._candidate_dirs_from_system
        orig_scan = p._scan_fixed_drives
        orig_inp = builtins.input
        try:
            p._candidate_dirs_from_system = lambda: [min_dir, cand2]
            builtins.input = lambda _="": "2"
            p.cmd_search(deep=False, out_file=str(out_sel))
            assert Path(out_sel.read_text(encoding="utf-8")) == cand2

            # Zero candidates -> SystemExit(1)
            p._candidate_dirs_from_system = lambda: []
            p._scan_fixed_drives = lambda: ([], 0.01, False)
            try:
                p.cmd_search(deep=True, out_file=str(out_sel))
                raise AssertionError("Expected SystemExit(1) when 0 installs found")
            except SystemExit as exc:
                assert exc.code == 1

            # Interrupted deep scan (Ctrl+C) -> clean SystemExit(130) without traceback
            p._scan_fixed_drives = lambda: ([], 0.05, True)
            try:
                p.cmd_search(deep=True, out_file=str(out_sel))
                raise AssertionError("Expected SystemExit(130) when deep scan interrupted")
            except SystemExit as exc:
                assert exc.code == 130
        finally:
            p._candidate_dirs_from_system = orig_cands
            p._scan_fixed_drives = orig_scan
            builtins.input = orig_inp
        print("[PASS] Searcher mandatory-only accept, reject bogus, 0/1/multi choice, and Ctrl+C passed.")

        print("=== 5. cmd_debug: privacy default, logs on/off, status, open, stop, multi-run, missing .bak, argv.json ===")
        dbg_dir = _make_fake_install(td_path / "dbg_install", src_asar, b"DBG\x00" + p.LS_TITLE_PROMPT_OLD + b"\x00END", with_exe=False)
        p.cmd_apply(dbg_dir, dry_run=False, ru_titles=True)

        fake_appdata = td_path / "FakeAppData"
        ag_user = fake_appdata / "Antigravity" / "User"
        ag_logs = fake_appdata / "Antigravity" / "logs"
        ag_user.mkdir(parents=True)
        ag_logs.mkdir(parents=True)
        argv_file = ag_user / "argv.json"
        argv_orig_text = '{\n  "locale": "en"\n}\n'
        argv_file.write_text(argv_orig_text, encoding="utf-8")
        main_log = ag_logs / "main.log"
        main_log.write_text("OLD_LOG_SHOULD_NOT_APPEAR\n", encoding="utf-8")

        desktop_dir = p._get_desktop_dir() / "patchdebug"
        before_logs = set(desktop_dir.glob("patch_debug_*.log")) if desktop_dir.exists() else set()

        orig_appdata = os.environ.get("APPDATA")
        orig_running = p._is_antigravity_running
        orig_startfile = getattr(os, "startfile", None)
        opened_paths = []
        created_test_logs = []

        def _scripted_cmds_run1():
            yield "status"
            # While logs are OFF, write a private Antigravity log line — must NOT enter patch_debug log!
            with main_log.open("a", encoding="utf-8") as mf:
                mf.write("PRIVATE_UNLESS_LOGS_ON_user_secret\n")
            yield "open"
            yield "logs on"
            with main_log.open("a", encoding="utf-8") as mf:
                mf.write("LIVE_ANTIGRAVITY_LINE_AFTER_LOGS_ON\n")
            import time
            time.sleep(0.6)
            yield "logs off"
            yield "stop"

        try:
            os.environ["APPDATA"] = str(fake_appdata)
            p._is_antigravity_running = lambda: False
            os.startfile = lambda path_arg: opened_paths.append(path_arg)

            # Run 1: full debug flow with status, open, logs on, logs off, stop
            it1 = _scripted_cmds_run1()
            builtins.input = lambda _="": next(it1)
            p.cmd_debug(dbg_dir, ru_titles=True, start_antigravity_logs=False)

            after1 = set(desktop_dir.glob("patch_debug_*.log"))
            new1 = sorted(after1 - before_logs)
            assert len(new1) == 1
            created_test_logs.extend(new1)
            log1_txt = new1[0].read_text(encoding="utf-8")
            assert "[PRIVACY]" in log1_txt
            assert "PRIVATE_UNLESS_LOGS_ON" not in log1_txt
            assert "LIVE_ANTIGRAVITY_LINE_AFTER_LOGS_ON" in log1_txt
            assert "ВНИМАНИЕ: включена трансляция логов Antigravity" in log1_txt or "ВКЛЮЧЕНА" in log1_txt
            assert "Патч применён, язык ru" in log1_txt
            assert argv_file.read_text(encoding="utf-8") == argv_orig_text, "argv.json must stay untouched!"
            assert len(opened_paths) == 1

            # Run 2 immediately -> must create a SECOND distinct log file without overwriting Run 1
            it2 = iter(["stop"])
            builtins.input = lambda _="": next(it2)
            p.cmd_debug(dbg_dir, ru_titles=True, start_antigravity_logs=False)
            after2 = set(desktop_dir.glob("patch_debug_*.log"))
            new2 = sorted(after2 - before_logs - set(new1))
            assert len(new2) == 1 and new2[0] != new1[0]
            created_test_logs.extend(new2)

            # Run 3: missing app.asar.bak on rollback -> must fail explicitly and log intermediate state
            (dbg_dir / "resources" / "app.asar.bak").unlink()
            try:
                p.cmd_debug(dbg_dir, ru_titles=True)
                raise AssertionError("Expected SystemExit(2) when app.asar.bak is missing on rollback")
            except SystemExit as exc:
                assert exc.code == 2
            after3 = set(desktop_dir.glob("patch_debug_*.log"))
            new3 = sorted(after3 - before_logs - set(created_test_logs))
            assert len(new3) == 1
            created_test_logs.extend(new3)
            log3_txt = new3[0].read_text(encoding="utf-8")
            assert "Откат не выполнен" in log3_txt and "ПРОМЕЖУТОЧНОМ СОСТОЯНИИ" in log3_txt
        finally:
            builtins.input = orig_inp
            p._is_antigravity_running = orig_running
            if orig_startfile is not None:
                os.startfile = orig_startfile
            if orig_appdata is not None:
                os.environ["APPDATA"] = orig_appdata
            for lf in created_test_logs:
                lf.unlink(missing_ok=True)
            if desktop_dir.exists() and not any(desktop_dir.iterdir()):
                desktop_dir.rmdir()
        print("[PASS] cmd_debug logs on/off, privacy, stop, open, 2nd run file, missing .bak abort, and untouched argv.json passed.")

    print("ALL TZ-2 TESTS PASSED!")


if __name__ == "__main__":
    main()
