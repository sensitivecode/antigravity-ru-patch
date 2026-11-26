#!/usr/bin/env python3
"""
Russian localization patcher for Google Antigravity (Electron desktop app).

Patches `resources/app.asar` cleanly (without modifying signed binaries):
- Sets Chromium `--lang=ru` so built-in Chromium/Electron dialogs & locale data use Russian.
- Translates Electron main-process menus, tray, updater, dialogs, IDE wizard, and SSH prompts.
- Translates all renderer context menus passed via IPC (`window:show-context-menu`).
- Injects a sandbox-safe DOM localization observer (`ru_i18n` + `ru_dom_translator`)
  into `dist/preload.js` to translate the React Hub UI in real time while preserving
  Material Symbols icons, code editors, terminals, math, and AI markdown prose.
- Optionally updates the conversation title prompt in `resources/bin/language_server.exe`
  (exact 110-byte in-place replacement, with `.bak` backup) so generated chat titles are in Russian.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import struct
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Tuple

PATCH_DIR = Path(__file__).resolve().parent
BLOCK_SIZE = 4 * 1024 * 1024  # 4 MiB, standard ASAR integrity block size
ELECTRON_FUSE_SENTINEL = b"dL7pKGdnNz796PbbjQWNKmHXBZaB9tsX"
LS_TITLE_PROMPT_OLD = (
    b"Respond with ONLY a short conversation title (3-5 words, title-cased, no prefix) describing the USER's intent."
)
LS_TITLE_PROMPT_NEW = (
    b"Respond ONLY in Russian with a short Russian title (3-5 words, no prefix) describing the USER's exact request."
)

DEFAULT_INSTALL_DIRS = [
    Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "antigravity",
    Path(os.environ.get("ProgramFiles", "")) / "Antigravity",
]


@dataclass
class PatchStats:
    applied: int = 0
    missed: int = 0
    patched_files: List[str] = field(default_factory=list)
    skipped_files: List[str] = field(default_factory=list)


def compute_integrity(data: bytes) -> dict:
    blocks = []
    for off in range(0, len(data), BLOCK_SIZE):
        blocks.append(hashlib.sha256(data[off : off + BLOCK_SIZE]).hexdigest())
    if not blocks:
        blocks = [hashlib.sha256(b"").hexdigest()]
    return {
        "algorithm": "SHA256",
        "hash": hashlib.sha256(data).hexdigest(),
        "blockSize": BLOCK_SIZE,
        "blocks": blocks,
    }


def read_asar_header(asar_path: Path) -> dict:
    with asar_path.open("rb") as f:
        u1, _, _, json_len = struct.unpack("<IIII", f.read(16))
        if u1 != 4:
            raise ValueError(f"Unsupported ASAR header tag {u1} in {asar_path}")
        return json.loads(f.read(json_len).decode("utf-8"))


def is_patched(asar_path: Path) -> bool:
    header = read_asar_header(asar_path)
    return "ru_i18n.js" in header.get("files", {}).get("dist", {}).get("files", {})


def read_asar(asar_path: Path) -> Tuple[dict, Dict[str, bytes]]:
    """Read an ASAR archive into (header_tree, {posix_path: raw_bytes})."""
    with asar_path.open("rb") as f:
        u1, u2, _, json_len = struct.unpack("<IIII", f.read(16))
        if u1 != 4:
            raise ValueError(f"Unsupported ASAR header tag {u1} in {asar_path}")
        header = json.loads(f.read(json_len).decode("utf-8"))
        data_offset = 8 + u2

        files_data: Dict[str, bytes] = {}

        def walk(node: dict, prefix: str = "") -> None:
            if "files" in node:
                for name, child in node["files"].items():
                    walk(child, f"{prefix}/{name}" if prefix else name)
            elif "link" in node or node.get("unpacked", False):
                return
            else:
                off = int(node["offset"])
                sz = int(node["size"])
                f.seek(data_offset + off)
                files_data[prefix] = f.read(sz)

        walk(header)
        return header, files_data


def insert_file_node(header: dict, posix_path: str, size: int, data: bytes) -> None:
    parts = posix_path.split("/")
    cur = header
    for part in parts[:-1]:
        cur = cur.setdefault("files", {}).setdefault(part, {"files": {}})
    cur.setdefault("files", {})[parts[-1]] = {
        "size": size,
        "offset": "0",
        "integrity": compute_integrity(data),
    }


def write_asar(out_path: Path, header: dict, files_data: Dict[str, bytes]) -> None:
    """Write a spec-compliant ASAR archive with updated offsets and SHA256 integrity."""
    ordered_chunks: List[bytes] = []
    current_offset = 0

    def assign(node: dict, prefix: str = "") -> None:
        nonlocal current_offset
        if "files" in node:
            for name in sorted(node["files"].keys()):
                assign(node["files"][name], f"{prefix}/{name}" if prefix else name)
        elif "link" in node or node.get("unpacked", False):
            return
        else:
            blob = files_data[prefix]
            node["size"] = len(blob)
            node["offset"] = str(current_offset)
            node["integrity"] = compute_integrity(blob)
            ordered_chunks.append(blob)
            current_offset += len(blob)

    assign(header)

    raw_json = json.dumps(header, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    pad_len = (4 - (len(raw_json) % 4)) % 4
    padded_json = raw_json + (b"\x00" * pad_len)
    pickle_payload_size = 4 + len(padded_json)
    pickle_total_size = 4 + pickle_payload_size

    header_bytes = struct.pack("<IIII", 4, pickle_total_size, pickle_payload_size, len(raw_json)) + padded_json

    tmp_path = out_path.with_suffix(".asar.tmp")
    with tmp_path.open("wb") as f:
        f.write(header_bytes)
        for chunk in ordered_chunks:
            f.write(chunk)
    tmp_path.replace(out_path)


def check_asar_integrity_fuse(install_dir: Path) -> bool | None:
    """Return True if Antigravity.exe enables EmbeddedAsarIntegrityValidation, False if disabled, None if unknown."""
    exe_path = install_dir / "Antigravity.exe"
    if not exe_path.exists():
        return None
    try:
        data = exe_path.read_bytes()
    except OSError:
        return None
    idx = data.find(ELECTRON_FUSE_SENTINEL)
    if idx == -1:
        return None
    start = idx + len(ELECTRON_FUSE_SENTINEL)
    if start + 7 > len(data):
        return None
    count = data[start + 1]
    if count <= 4 or start + 2 + count > len(data):
        return None
    # Fuse 4 = EnableEmbeddedAsarIntegrityValidation ('1' == 0x31)
    return data[start + 2 + 4] == ord("1")


def patch_electron_files(files_data: Dict[str, bytes], ru_i18n_src: str, ru_dom_src: str) -> PatchStats:
    stats = PatchStats()

    def set_str(path: str, content: str) -> None:
        files_data[path] = content.encode("utf-8")
        stats.patched_files.append(path)

    def patch_file(path: str, replacements: List[Tuple[str, str]], optional: bool = False, extra_fn=None) -> None:
        if path not in files_data:
            stats.skipped_files.append(path)
            if not optional:
                stats.missed += len(replacements)
                print(f"  [warn] Missing file in ASAR: {path}")
            return

        text = files_data[path].decode("utf-8")
        for old, new in replacements:
            if old in text:
                text = text.replace(old, new)
                stats.applied += 1
            elif new in text:
                stats.applied += 1
            else:
                if not optional:
                    stats.missed += 1
                    print(f"  [warn] Pattern not found in {path}: {old[:60]!r}")

        if extra_fn is not None:
            text = extra_fn(text)

        set_str(path, text)

    # 0. Add dist/ru_i18n.js for Electron main-process modules
    set_str("dist/ru_i18n.js", ru_i18n_src)

    # 1. dist/main.js
    def patch_main_extra(s: str) -> str:
        target = "electron_1.app.commandLine.appendSwitch('disable-features', 'FedCm');"
        repl = "electron_1.app.commandLine.appendSwitch('lang', 'ru');\nelectron_1.app.commandLine.appendSwitch('disable-features', 'FedCm');"
        if "appendSwitch('lang', 'ru')" in s:
            stats.applied += 1
        elif target in s:
            s = s.replace(target, repl, 1)
            stats.applied += 1
        else:
            stats.missed += 1
            print("  [warn] Pattern not found in dist/main.js: disable-features")
        return s

    patch_file(
        "dist/main.js",
        [
            ("await electron_1.dialog.showErrorBox('Binary not found', msg);", "await electron_1.dialog.showErrorBox('Файл не найден', msg);"),
            ("title: 'WSL distro not found',", "title: 'Дистрибутив WSL не найден',"),
            ("message: `The WSL distro \"${WSL_DISTRO}\" is no longer installed.`,", "message: `Дистрибутив WSL «${WSL_DISTRO}» больше не установлен.`,"),
            ("detail: 'Antigravity opened on Windows instead.',", "detail: 'Antigravity запущен в Windows.',"),
            ("await electron_1.dialog.showErrorBox('WSL setup failed', msg);", "await electron_1.dialog.showErrorBox('Ошибка настройки WSL', msg);"),
            ("await electron_1.dialog.showErrorBox('Startup failed', msg);", "await electron_1.dialog.showErrorBox('Ошибка запуска', msg);"),
            ("label: 'New Window',", "label: 'Новое окно',"),
            ("label: 'No agents running',", "label: 'Нет активных агентов',"),
            ("label: `Open ${electron_1.app.getName()}`,", "label: `Открыть ${electron_1.app.getName()}`,"),
            ("label: 'Quit',", "label: 'Выход',"),
            ("buttons: ['Cancel', 'Quit'],", "buttons: ['Отмена', 'Выход'],"),
            ("title: 'Confirm Quit',", "title: 'Подтверждение выхода',"),
            ("message: 'Are you sure you want to quit?',", "message: 'Вы уверены, что хотите выйти?',"),
            ("detail: 'There may be agents or background tasks running.',", "detail: 'Могут оставаться запущенные агенты или фоновые задачи.',"),
        ],
        extra_fn=patch_main_extra,
    )

    # 2. dist/menu.js (keep 'View', 'File', 'Help' lookup intact, then localize top-level menu labels)
    def patch_menu_extra(s: str) -> str:
        if "localizeApplicationMenu(" in s:
            stats.applied += 1
            return s
        helper = (
            "\nconst { translateMenuItems: __ruTranslateMenuItems } = require('./ru_i18n');\n"
            "function localizeApplicationMenu(appMenu) {\n"
            "    const topMap = { File: 'Файл', Edit: 'Правка', View: 'Вид', Window: 'Окно', Help: 'Справка' };\n"
            "    const roleMap = {\n"
            "        undo: 'Отменить', redo: 'Повторить', cut: 'Вырезать', copy: 'Копировать',\n"
            "        paste: 'Вставить', pasteandmatchstyle: 'Вставить без форматирования',\n"
            "        delete: 'Удалить', selectall: 'Выделить всё', reload: 'Перезагрузить',\n"
            "        forcereload: 'Принудительно перезагрузить', toggledevtools: 'Инструменты разработчика',\n"
            "        togglefullscreen: 'Полноэкранный режим', minimize: 'Свернуть', zoom: 'Масштаб',\n"
            "        close: 'Закрыть окно', quit: 'Выход', hide: 'Скрыть', hideothers: 'Скрыть остальные',\n"
            "        unhide: 'Показать все', about: 'О программе'\n"
            "    };\n"
            "    const walk = (m, isTop) => {\n"
            "        if (!m || !Array.isArray(m.items)) return;\n"
            "        for (const it of m.items) {\n"
            "            if (isTop && topMap[it.label]) { it.label = topMap[it.label]; }\n"
            "            else if (it.role && roleMap[it.role.toLowerCase()]) { it.label = roleMap[it.role.toLowerCase()]; }\n"
            "            else if (typeof it.label === 'string') {\n"
            "                const t = __ruTranslateMenuItems([{ label: it.label }])[0].label;\n"
            "                if (t) it.label = t;\n"
            "            }\n"
            "            if (it.submenu) walk(it.submenu, false);\n"
            "        }\n"
            "    };\n"
            "    walk(appMenu, true);\n"
            "}\n"
        )
        anchors = [
            (
                "electron_1.Menu.setApplicationMenu(menu);\n    // Asynchronously adds \"Connect to WSL\"",
                "localizeApplicationMenu(menu);\n    electron_1.Menu.setApplicationMenu(menu);\n    // Asynchronously adds \"Connect to WSL\"",
            ),
            (
                "electron_1.Menu.setApplicationMenu(menu);\n}\n/** Relaunches",
                "localizeApplicationMenu(menu);\n    electron_1.Menu.setApplicationMenu(menu);\n}\n/** Relaunches",
            ),
        ]
        matched = 0
        for old, new in anchors:
            if old in s:
                s = s.replace(old, new, 1)
                matched += 1
        if matched > 0:
            s += helper
            stats.applied += matched
        else:
            stats.missed += 1
            print("  [warn] Pattern not found in dist/menu.js: setApplicationMenu anchor")
        return s

    patch_file(
        "dist/menu.js",
        [
            ("label: item.label || 'Actual Size',", "label: 'Фактический размер',"),
            ("label: item.label || 'Zoom In',", "label: 'Увеличить',"),
            ("label: 'Zoom In',", "label: 'Увеличить',"),
            ("label: item.label || 'Zoom Out',", "label: 'Уменьшить',"),
            ("label: 'New Window',", "label: 'Новое окно',"),
            ("label: 'Docs',", "label: 'Документация',"),
            ("return { label: 'Connect to WSL', submenu };", "return { label: 'Подключиться к WSL', submenu };"),
            ("return { label: 'Reopen Locally', click: () => relaunchWithWslDistro('') };", "return { label: 'Открыть локально', click: () => relaunchWithWslDistro('') };"),
        ],
        extra_fn=patch_menu_extra,
    )

    # 3. dist/tray.js
    patch_file(
        "dist/tray.js",
        [
            (
                "            countItem.label =\n"
                "                (count > 0 ? `${count}` : 'No') +\n"
                "                    ' agent' +\n"
                "                    (count === 1 ? '' : 's') +\n"
                "                    ' running';",
                "            const { pluralRu } = require('./ru_i18n');\n"
                "            countItem.label = count > 0\n"
                "                ? `${count} ${pluralRu(count, 'активный агент', 'активных агента', 'активных агентов')}`\n"
                "                : 'Нет активных агентов';",
            ),
        ],
    )

    # 4. dist/updater.js (keep types.js wire strings intact!)
    patch_file(
        "dist/updater.js",
        [
            ('MenuUpdateStep["CheckForUpdates"] = "Check for Updates";', 'MenuUpdateStep["CheckForUpdates"] = "Проверить обновления";'),
            ('MenuUpdateStep["CheckingForUpdates"] = "Checking for Updates...";', 'MenuUpdateStep["CheckingForUpdates"] = "Проверка обновлений...";'),
            ('MenuUpdateStep["DownloadingUpdate"] = "Downloading Update...";', 'MenuUpdateStep["DownloadingUpdate"] = "Загрузка обновления...";'),
            ('MenuUpdateStep["RestartToUpdate"] = "Restart to Update";', 'MenuUpdateStep["RestartToUpdate"] = "Перезапустить для обновления";'),
            ("title: 'Check for Updates',", "title: 'Проверка обновлений',"),
            ("message: 'No updates available',", "message: 'Обновлений нет',"),
            ("buttons: ['OK'],", "buttons: ['ОК'],"),
        ],
    )

    # 5. dist/ipcHandlers.js (dialogs + renderer context menus)
    def patch_ipc_extra(s: str) -> str:
        if "require(\"./ru_i18n\")" in s or "require('./ru_i18n')" in s:
            stats.applied += 1
            return s
        target = 'const electron_1 = require("electron");'
        if target in s:
            s = s.replace(
                target,
                'const electron_1 = require("electron");\nconst { translateMenuItems: __ruTranslateMenuItems } = require("./ru_i18n");',
                1,
            )
            stats.applied += 1
        else:
            stats.missed += 1
            print("  [warn] Pattern not found in dist/ipcHandlers.js: electron import")
        return s

    patch_file(
        "dist/ipcHandlers.js",
        [
            ("return items.map((item) => {", "return __ruTranslateMenuItems(items).map((item) => {"),
            ("electron_1.dialog.showErrorBox('Cannot open folder', t.error);", "electron_1.dialog.showErrorBox('Не удалось открыть папку', t.error);"),
            ("message: 'Folder is on the Windows filesystem',", "message: 'Папка находится в файловой системе Windows',"),
            ("title: 'Open workspace',", "title: 'Открыть рабочую область',"),
            ("title: 'Open workspaces',", "title: 'Открыть рабочие области',"),
            ("title: 'Select Download Folder',", "title: 'Выберите папку загрузок',"),
        ],
        extra_fn=patch_ipc_extra,
    )

    # 6. dist/deviceChooser.js, dist/webauthn.js, dist/webviewPopupSecurity.js, dist/cablev2.js
    patch_file(
        "dist/deviceChooser.js",
        [
            ("hid: 'HID device',", "hid: 'HID-устройству',"),
            ("usb: 'USB device',", "usb: 'USB-устройству',"),
            ("serial: 'serial port',", "serial: 'последовательному порту',"),
            ("'Unknown device'", "'Неизвестное устройство'"),
            ("title: 'Connect a device',", "title: 'Подключение устройства',"),
            ("message: `${origin} wants to connect to a ${KIND_NOUNS[kind]}`,", "message: `${origin} запрашивает доступ к ${KIND_NOUNS[kind]}`,"),
            ("? 'Select a device:'", "? 'Выберите устройство:'"),
            (": 'No compatible devices found.',", ": 'Совместимые устройства не найдены.',"),
            ("buttons: [...snapshot.map(({ label }) => label), 'Cancel'],", "buttons: [...snapshot.map(({ label }) => label), 'Отмена'],"),
        ],
    )

    patch_file(
        "dist/webauthn.js",
        [
            ("const rpLabel = details.relyingPartyId || 'this site';", "const rpLabel = details.relyingPartyId || 'этот сайт';"),
            ("title: 'Choose a Passkey',", "title: 'Выберите ключ доступа',"),
            ("message: `Sign in to ${rpLabel}`,", "message: `Вход на ${rpLabel}`,"),
            ("detail: 'Select a passkey account to continue:',", "detail: 'Выберите учётную запись с ключом доступа:',"),
            ("buttons: [...accountLabels, 'Cancel'],", "buttons: [...accountLabels, 'Отмена'],"),
        ],
    )

    patch_file(
        "dist/webviewPopupSecurity.js",
        [
            ("label: 'Connection info…',", "label: 'Сведения о подключении…',"),
            ("title: 'Connection info',", "title: 'Сведения о подключении',"),
            ("buttons: ['OK'],", "buttons: ['ОК'],"),
        ],
    )

    patch_file(
        "dist/cablev2.js",
        [
            (">Cancel</button>", ">Отмена</button>"),
            ("title: 'Passkeys',", "title: 'Ключи доступа',"),
        ],
        optional=True,
    )

    # 7. dist/ideInstall/wizardHtml.js
    patch_file(
        "dist/ideInstall/wizardHtml.js",
        [
            (">Setting up…</div>", ">Настройка…</div>"),
            ("<h1>Welcome to the new Antigravity!</h1>", "<h1>Добро пожаловать в новый Antigravity!</h1>"),
            (
                "<p>Antigravity has been redesigned to put agents first with new capabilities. If you'd still like a code editor, you can download it as a separate app named <b>Antigravity IDE</b>.</p>",
                "<p>Antigravity обновлён: в центре внимания теперь работа с агентами. Если вам по-прежнему нужен редактор кода, вы можете скачать его как отдельное приложение <b>Antigravity IDE</b>.</p>",
            ),
            ("<span>Download the Antigravity IDE</span>", "<span>Скачать Antigravity IDE</span>"),
            (">Explore the new Antigravity</button>", ">Открыть новый Antigravity</button>"),
        ],
    )

    # 8. Remote & WSL UI strings
    patch_file(
        "dist/wsl.js",
        [("onStatus?.(`Installing into ${distro}\\u2026`);", "onStatus?.(`Установка в ${distro}\\u2026`);")],
        optional=True,
    )

    patch_file(
        "dist/remote/disconnectedPage.js",
        [
            ("reconnect: 'Reconnect',\n    stop: 'Stop Server',\n    close: 'Close',", "reconnect: 'Переподключиться',\n    stop: 'Остановить сервер',\n    close: 'Закрыть',"),
            ("? 'Restarting…'", "? 'Перезапуск…'"),
            ("? 'Reconnecting…'", "? 'Переподключение…'"),
            (": 'Disconnected';", ": 'Отключено';"),
            ("? `Restarting the Antigravity server on ${host}…`", "? `Перезапуск сервера Antigravity на ${host}…`"),
            ("? `Reconnecting to ${host}…`", "? `Переподключение к ${host}…`"),
            (": `Disconnected from ${host}`;", ": `Отключено от ${host}`;"),
            ("? 'This window opens it again once it has started.'", "? 'Окно откроется снова после запуска сервера.'"),
            ("? `Its server on ${host} stopped, and its agents with it.`", "? `Сервер на ${host} и его агенты остановлены.`"),
            (": `Agents keep running on ${host}.`", ": `Агенты продолжают работать на ${host}.`"),
            ("? `Its agents on ${host} stopped with it.`", "? `Агенты на ${host} также остановлены.`"),
            (": `Agents keep running on ${host} unless its server stopped.`;", ": `Агенты продолжают работать на ${host}, пока запущен сервер.`;"),
            ('<html lang="en">', '<html lang="ru">'),
        ],
    )

    patch_file(
        "dist/remote/remoteManager.js",
        [
            ("title: 'Choose an SSH config file',", "title: 'Выберите файл конфигурации SSH',"),
            ("title: 'Choose another SSH config file',", "title: 'Выберите другой файл конфигурации SSH',"),
            ("buttons: ['Choose Another File…', 'Cancel'],", "buttons: ['Выбрать другой файл…', 'Отмена'],"),
            ("title: 'SSH connection failed',", "title: 'Ошибка SSH-подключения',"),
            ("title: 'Could not restart the SSH server',", "title: 'Не удалось перезапустить SSH-сервер',"),
            ("buttons: ['Stop Server', 'Cancel'],", "buttons: ['Остановить сервер', 'Отмена'],"),
            ("title: 'Stop SSH server',", "title: 'Остановка SSH-сервера',"),
            ("message: `Stop the Antigravity server on ${entry.label}?`,", "message: `Остановить сервер Antigravity на ${entry.label}?`,"),
            ("message: `Not connected to ${label}`,", "message: `Нет подключения к ${label}`,"),
            ("detail: 'Reconnect first, then stop its server.',", "detail: 'Сначала переподключитесь, затем остановите сервер.',"),
            ("buttons: ['Allow', \"Don't Allow\"],", "buttons: ['Разрешить', 'Запретить'],"),
            ("title: 'Microphone access',", "title: 'Доступ к микрофону',"),
            ("message: `Allow ${label} to use your microphone?`,", "message: `Разрешить ${label} использовать ваш микрофон?`,"),
            ("buttons: ['Sign In', 'Cancel'],", "buttons: ['Войти', 'Отмена'],"),
            ("title: 'Sign in',", "title: 'Вход',"),
            ("buttons: ['Continue', 'Cancel'],", "buttons: ['Продолжить', 'Отмена'],"),
            ("buttons: ['Take Over', 'Cancel'],", "buttons: ['Перехватить', 'Отмена'],"),
            ("title: 'Shared home directory',", "title: 'Общий домашний каталог',"),
            ("buttons: ['Restart', 'Later'],", "buttons: ['Перезапустить', 'Позже'],"),
            ("title: 'Restart SSH server',", "title: 'Перезапуск SSH-сервера',"),
        ],
    )

    patch_file(
        "dist/remote/sshPrompts.js",
        [
            ('<button id="cancel" class="secondary">Cancel</button><button id="continue" class="primary">Continue</button>', '<button id="cancel" class="secondary">Отмена</button><button id="continue" class="primary">Продолжить</button>'),
            ("buttons: confirm ? ['Yes', 'No'] : ['Cancel'],", "buttons: confirm ? ['Да', 'Нет'] : ['Отмена'],"),
        ],
        optional=True,
    )

    # 9. dist/preload.js — embed sandboxed i18n runtime + DOM translator!
    def patch_preload_extra(s: str) -> str:
        marker = "/* __ANTIGRAVITY_RU_PRELOAD_PATCH__ */"
        if marker in s:
            stats.applied += 1
            return s
        i18n_body = ru_i18n_src.split("module.exports = {", 1)[0]
        embedded_block = (
            f"\n{marker}\n"
            ";(() => {\n"
            "  const __RU_I18N__ = (() => {\n"
            f"{i18n_body}\n"
            "    return { pluralRu, EXACT, REGEX_RULES, translateUiText, translateMenuItems };\n"
            "  })();\n"
            "  try {\n"
            "    if (typeof electron_1 !== 'undefined' && electron_1.webFrame && typeof electron_1.webFrame.executeJavaScript === 'function') {\n"
            "      void Promise.resolve(electron_1.webFrame.executeJavaScript(\"globalThis._VSCODE_NLS_LANGUAGE='ru';\")).catch(() => {});\n"
            "    }\n"
            "  } catch {}\n"
            f"{ru_dom_src}\n"
            "})();\n"
        )
        stats.applied += 1
        return s + embedded_block

    patch_file(
        "dist/preload.js",
        [
            (
                "message: \"Couldn't connect to the SSH host. See the app log.\",",
                "message: \"Не удалось подключиться к SSH-хосту. Подробности в журнале приложения.\",",
            ),
        ],
        extra_fn=patch_preload_extra,
    )

    return stats


def resolve_install_dir(explicit: str | None) -> Path:
    if explicit:
        p = Path(explicit)
        if (p / "resources" / "app.asar").exists():
            return p
        raise FileNotFoundError(f"app.asar not found under {p / 'resources' / 'app.asar'}")
    for cand in DEFAULT_INSTALL_DIRS:
        if cand and (cand / "resources" / "app.asar").exists():
            return cand
    raise FileNotFoundError(
        "Could not locate Antigravity installation directory automatically. "
        "Pass --dir \"C:\\path\\to\\antigravity\"."
    )


def patch_language_server_titles(install_dir: Path, dry_run: bool = False) -> str:
    """Switch conversation title generation in language_server.exe to Russian (exact byte-length replacement)."""
    assert len(LS_TITLE_PROMPT_OLD) == len(LS_TITLE_PROMPT_NEW) == 110
    ls_path = install_dir / "resources" / "bin" / "language_server.exe"
    bak_path = install_dir / "resources" / "bin" / "language_server.exe.bak"
    if not ls_path.exists():
        print(f"      [warn] {ls_path} not found; skipping Russian chat title patch.")
        return "missing"

    data = ls_path.read_bytes()
    old_cnt = data.count(LS_TITLE_PROMPT_OLD)
    new_cnt = data.count(LS_TITLE_PROMPT_NEW)

    if new_cnt == 1 and old_cnt == 0:
        print("      language_server.exe already patched for Russian chat titles.")
        return "already-patched"

    if old_cnt != 1 or new_cnt != 0:
        print(
            f"      [warn] language_server.exe title prompt mismatch "
            f"(old={old_cnt}, new={new_cnt}); skipping."
        )
        return "skipped"

    if dry_run:
        print("      [dry-run] language_server.exe title prompt found (110 bytes); exact-length Russian patch ready.")
        return "dry-run-ready"

    print(f"      Creating language_server backup: {bak_path}")
    shutil.copy2(ls_path, bak_path)

    patched = data.replace(LS_TITLE_PROMPT_OLD, LS_TITLE_PROMPT_NEW, 1)
    assert len(patched) == len(data)
    assert patched.count(LS_TITLE_PROMPT_NEW) == 1

def _retry_on_lock(action, target_label: str, action_word: str = "overwrite", cleanup=None) -> None:
    """Retry a file replacement/copy when Antigravity processes are still releasing locks."""
    last_exc = None
    for _ in range(10):
        try:
            action()
            return
        except PermissionError as exc:
            last_exc = exc
            time.sleep(0.5)
    if cleanup is not None:
        try:
            cleanup()
        except OSError:
            pass
    print(
        f"\n[ERROR] Cannot {action_word} {target_label} because Antigravity is still running.\n"
        "Please close Antigravity completely (including the tray icon) and re-run.",
        file=sys.stderr,
    )
    raise SystemExit(2) from last_exc


def patch_language_server_titles(install_dir: Path, dry_run: bool = False) -> str:
    """Switch conversation title generation in language_server.exe to Russian (exact byte-length replacement)."""
    assert len(LS_TITLE_PROMPT_OLD) == len(LS_TITLE_PROMPT_NEW) == 110
    ls_path = install_dir / "resources" / "bin" / "language_server.exe"
    bak_path = install_dir / "resources" / "bin" / "language_server.exe.bak"
    if not ls_path.exists():
        print(f"      [warn] {ls_path} not found; skipping Russian chat title patch.")
        return "missing"

    data = ls_path.read_bytes()
    old_cnt = data.count(LS_TITLE_PROMPT_OLD)
    new_cnt = data.count(LS_TITLE_PROMPT_NEW)

    if new_cnt == 1 and old_cnt == 0:
        print("      language_server.exe already patched for Russian chat titles.")
        return "already-patched"

    if old_cnt != 1 or new_cnt != 0:
        print(
            f"      [warn] language_server.exe title prompt mismatch "
            f"(old={old_cnt}, new={new_cnt}); skipping."
        )
        return "skipped"

    if dry_run:
        print("      [dry-run] language_server.exe title prompt found (110 bytes); exact-length Russian patch ready.")
        return "dry-run-ready"

    print(f"      Creating language_server backup: {bak_path}")
    shutil.copy2(ls_path, bak_path)

    patched = data.replace(LS_TITLE_PROMPT_OLD, LS_TITLE_PROMPT_NEW, 1)
    assert len(patched) == len(data)
    assert patched.count(LS_TITLE_PROMPT_NEW) == 1

    tmp_path = ls_path.with_suffix(".exe.tmp")
    tmp_path.write_bytes(patched)
    _retry_on_lock(
        lambda: os.replace(tmp_path, ls_path),
        "language_server.exe",
        cleanup=lambda: tmp_path.unlink(missing_ok=True),
    )

    print("      Updated language_server.exe for Russian conversation titles.")
    return "patched"


def restore_language_server_titles(install_dir: Path) -> None:
    """Restore original language_server.exe if patched by this tool."""
    ls_path = install_dir / "resources" / "bin" / "language_server.exe"
    bak_path = install_dir / "resources" / "bin" / "language_server.exe.bak"
    if not ls_path.exists():
        return
    data = ls_path.read_bytes()
    if LS_TITLE_PROMPT_NEW not in data:
        print("language_server.exe is not patched — nothing to restore.")
        return
    if not bak_path.exists():
        print(f"No backup found at {bak_path}. Cannot restore language_server.exe.")
        return
    _retry_on_lock(lambda: shutil.copy2(bak_path, ls_path), "language_server.exe", action_word="restore")
    print(f"Restored original language_server.exe from {bak_path}.")


def cmd_apply(install_dir: Path, dry_run: bool = False, ru_titles: bool = True) -> None:
    asar_path = install_dir / "resources" / "app.asar"
    bak_path = install_dir / "resources" / "app.asar.bak"

    if check_asar_integrity_fuse(install_dir) is True:
        print(
            "[WARN] Antigravity.exe has EnableEmbeddedAsarIntegrityValidation enabled.\n"
            "       If Antigravity fails to launch after patching, run restore_patch.bat."
        )

    ru_i18n_src = (PATCH_DIR / "ru_i18n.js").read_text(encoding="utf-8")
    ru_dom_src = (PATCH_DIR / "ru_dom_translator.js").read_text(encoding="utf-8")

    already_patched = is_patched(asar_path)

    if not already_patched:
        print(f"[1/5] Creating pristine backup: {bak_path}")
        if not dry_run:
            shutil.copy2(asar_path, bak_path)
        source_header, source_files = read_asar(asar_path)
    else:
        if not bak_path.exists():
            print(
                f"\n[ERROR] {asar_path} is already patched, but backup {bak_path} is missing.\n"
                "Cannot cleanly re-patch without the original app.asar.bak backup.",
                file=sys.stderr,
            )
            raise SystemExit(2)
        print(f"[1/5] Reading pristine source from backup: {bak_path}")
        source_header, source_files = read_asar(bak_path)

    print("[2/5] Patching Electron shell & injecting Russian Web UI translator...")
    stats = patch_electron_files(source_files, ru_i18n_src, ru_dom_src)

    insert_file_node(source_header, "dist/ru_i18n.js", len(source_files["dist/ru_i18n.js"]), source_files["dist/ru_i18n.js"])

    total = stats.applied + stats.missed
    print(f"      Patched {len(stats.patched_files)} files; applied {stats.applied}/{total} replacements (missed: {stats.missed}).")
    if stats.missed > 0:
        print("      [warn] Some strings were not found (Antigravity may have updated).")

    if dry_run:
        test_out = PATCH_DIR / "_dry_run_app.asar"
        print(f"[3/5] Writing dry-run ASAR to {test_out}...")
        write_asar(test_out, source_header, source_files)
        _, f_verify = read_asar(test_out)
        assert "dist/ru_i18n.js" in f_verify
        assert len(f_verify) == len(source_files)
        print(f"[4/5] Verified dry-run ASAR ({test_out.stat().st_size} bytes, {len(f_verify)} packed files).")
        if ru_titles:
            print("[5/5] Checking language_server.exe Russian chat title patch...")
            patch_language_server_titles(install_dir, dry_run=True)
        return

    print(f"[3/5] Writing patched archive to {asar_path}...")
    _retry_on_lock(lambda: write_asar(asar_path, source_header, source_files), "app.asar")

    print("[4/5] Verifying written app.asar...")
    _, f_verify = read_asar(asar_path)
    assert "dist/ru_i18n.js" in f_verify

    if ru_titles:
        print("[5/5] Enabling Russian chat title generation in language_server.exe...")
        patch_language_server_titles(install_dir, dry_run=False)
    else:
        print("[5/5] Skipped Russian chat title generation (--no-ru-titles).")

    if stats.missed == 0:
        print(f"Done! Antigravity at {install_dir} has been localized to Russian.")
    else:
        print(f"Done with warnings ({stats.missed} pattern(s) skipped). Antigravity at {install_dir} patched.")


def cmd_restore(install_dir: Path) -> None:
    asar_path = install_dir / "resources" / "app.asar"
    bak_path = install_dir / "resources" / "app.asar.bak"
    if not is_patched(asar_path):
        print("app.asar is not patched (possibly updated by Antigravity) — nothing to restore.")
    elif not bak_path.exists():
        print(f"No backup found at {bak_path}. Nothing to restore.")
    else:
        _retry_on_lock(lambda: shutil.copy2(bak_path, asar_path), "app.asar", action_word="restore")
        print(f"Restored original app.asar from {bak_path}.")

    restore_language_server_titles(install_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description="Russian localization patcher for Google Antigravity")
    parser.add_argument("--dir", help="Path to Antigravity install directory (containing resources/app.asar)")
    parser.add_argument("--apply", action="store_true", help="Apply Russian translation patch")
    parser.add_argument("--restore", action="store_true", help="Restore original app.asar and language_server.exe from backup")
    parser.add_argument("--dry-run", action="store_true", help="Test patching into _dry_run_app.asar without modifying installation")
    parser.add_argument("--no-ru-titles", action="store_true", help="Skip patching language_server.exe for Russian conversation titles")
    parser.add_argument("--print-dir", action="store_true", help="Print resolved Antigravity install directory and exit")
    args = parser.parse_args()

    try:
        install_dir = resolve_install_dir(args.dir)
    except FileNotFoundError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    if args.print_dir:
        print(str(install_dir))
        return

    if not (args.apply or args.restore or args.dry_run):
        parser.print_help()
        raise SystemExit(1)

    if args.restore:
        cmd_restore(install_dir)
    else:
        cmd_apply(install_dir, dry_run=args.dry_run, ru_titles=not args.no_ru_titles)


if __name__ == "__main__":
    main()
