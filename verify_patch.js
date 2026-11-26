const assert = require("assert");
const fs = require("fs");
const path = require("path");
const vm = require("vm");
const crypto = require("crypto");

const REPO_DIR = __dirname;
const DRY_ASAR = path.join(REPO_DIR, "_dry_run_app.asar");
const LOCAL_APP_DATA = process.env.LOCALAPPDATA || "";
const DEFAULT_RESOURCES = path.join(LOCAL_APP_DATA, "Programs", "antigravity", "resources");
const INSTALL_RESOURCES = process.env.ANTIGRAVITY_RESOURCES_DIR || DEFAULT_RESOURCES;
const ORIG_ASAR = fs.existsSync(path.join(INSTALL_RESOURCES, "app.asar.bak"))
  ? path.join(INSTALL_RESOURCES, "app.asar.bak")
  : path.join(INSTALL_RESOURCES, "app.asar");

// Verify Electron's native C++ ASAR loader can read directly from _dry_run_app.asar
const nativeReadI18n = fs.readFileSync(path.join(DRY_ASAR, "dist", "ru_i18n.js"), "utf8");
assert.ok(nativeReadI18n.includes("translateUiText"), "Electron native ASAR read failed");
const nativeReadPreload = fs.readFileSync(path.join(DRY_ASAR, "dist", "preload.js"), "utf8");
assert.ok(nativeReadPreload.includes("__ANTIGRAVITY_RU_PRELOAD_PATCH__"));

// Disable ASAR virtual fs so parseAsar can inspect raw archive bytes
process.noAsar = true;

function parseAsar(filePath) {
  const buf = fs.readFileSync(filePath);
  const u1 = buf.readUInt32LE(0);
  const u2 = buf.readUInt32LE(4);
  const jsonLen = buf.readUInt32LE(12);
  assert.strictEqual(u1, 4);
  const header = JSON.parse(buf.slice(16, 16 + jsonLen).toString("utf8"));
  const dataOffset = 8 + u2;
  const entries = new Map();
  function walk(node, prefix = "") {
    if (node.files) {
      for (const [k, v] of Object.entries(node.files)) {
        walk(v, prefix ? `${prefix}/${k}` : k);
      }
    } else {
      let data = null;
      if (!node.unpacked) {
        const off = Number(node.offset);
        const sz = Number(node.size);
        data = buf.slice(dataOffset + off, dataOffset + off + sz);
        const sha = crypto.createHash("sha256").update(data).digest("hex");
        assert.strictEqual(sha, node.integrity.hash, `Hash mismatch for ${prefix}`);
      }
      entries.set(prefix, { meta: node, data });
    }
  }
  walk(header);
  return entries;
}

const origEntries = parseAsar(ORIG_ASAR);
const dryEntries = parseAsar(DRY_ASAR);

assert.strictEqual(
  dryEntries.size,
  origEntries.size + 1,
  `Expected ${origEntries.size + 1} entries, got ${dryEntries.size}`
);
assert.ok(dryEntries.has("dist/ru_i18n.js"), "dist/ru_i18n.js missing");

const patchedFiles = [
  "dist/ru_i18n.js",
  "dist/main.js",
  "dist/menu.js",
  "dist/tray.js",
  "dist/updater.js",
  "dist/ipcHandlers.js",
  "dist/deviceChooser.js",
  "dist/webauthn.js",
  "dist/webviewPopupSecurity.js",
  "dist/cablev2.js",
  "dist/ideInstall/wizardHtml.js",
  "dist/wsl.js",
  "dist/remote/disconnectedPage.js",
  "dist/remote/remoteManager.js",
  "dist/remote/sshPrompts.js",
  "dist/preload.js",
];

for (const rel of patchedFiles) {
  const entry = dryEntries.get(rel);
  assert.ok(entry && entry.data, `Missing data for ${rel}`);
  const code = entry.data.toString("utf8");
  new vm.Script(code, { filename: rel });
}
console.log(`Syntax-checked all ${patchedFiles.length} patched JS files successfully.`);

// Confirm Russian CLI flag --lang=ru is injected into dist/main.js
const mainJs = dryEntries.get("dist/main.js").data.toString("utf8");
assert.ok(mainJs.includes("appendSwitch('lang', 'ru')"), "Missing --lang=ru switch in dist/main.js");

const i18n = require(path.join(REPO_DIR, "ru_i18n.js"));
assert.strictEqual(i18n.translateUiText("New Conversation"), "Новый чат");
assert.strictEqual(i18n.translateUiText("Ask anything, @ to mention, / for actions"), "Спросите что угодно, @ для упоминания, / для действий");
assert.strictEqual(i18n.translateUiText("Build me a web app"), "Создай веб-приложение");
assert.strictEqual(i18n.translateUiText("Add a Gemini feature to my app"), "Добавь функцию Gemini в моё приложение");
assert.strictEqual(i18n.translateUiText("Bring over my setup from other Agentic Developer Tools"), "Перенеси настройки из других ИИ-инструментов разработки");
assert.strictEqual(i18n.translateUiText("Software Engineering"), "Разработка ПО");
assert.strictEqual(i18n.translateUiText("View Usage"), "Посмотреть лимиты");
assert.strictEqual(i18n.translateUiText("Usage"), "Лимиты");
assert.strictEqual(i18n.translateUiText("Leaving Soon"), "Скоро исчезнет");
assert.strictEqual(i18n.translateUiText("Paid Pro"), "Тариф Pro");
assert.strictEqual(i18n.translateUiText("5h limit"), "Лимит на 5 ч");
assert.strictEqual(i18n.translateUiText("Extra High"), "Максимальная");
assert.strictEqual(i18n.translateUiText("57% left"), "Осталось 57%");
assert.strictEqual(i18n.translateUiText("% left"), "% осталось");
assert.strictEqual(i18n.translateUiText("Resets in 6d 13h"), "Сброс через 6 д 13 ч");
assert.strictEqual(i18n.translateUiText("4h 25m"), "4 ч 25 мин");
assert.strictEqual(i18n.translateUiText("Review"), "Обзор");
assert.strictEqual(i18n.translateUiText("  Settings  "), "  Настройки  ");
assert.strictEqual(i18n.translateUiText("just now"), "только что");
assert.strictEqual(i18n.translateUiText("5m ago"), "5 мин назад");
assert.strictEqual(i18n.translateUiText("1 file changed"), "1 файл изменён");
assert.strictEqual(i18n.translateUiText("2 files changed"), "2 файла изменено");
assert.strictEqual(i18n.translateUiText("5 files changed"), "5 файлов изменено");
assert.strictEqual(i18n.translateUiText("Worked for 12s"), "Работал 12 с");
assert.strictEqual(i18n.translateUiText("Thinking for 4s"), "Думает 4 с");
assert.strictEqual(i18n.translateUiText("Searched for \"foo\""), "Поиск: «foo»");
assert.strictEqual(
  i18n.translateUiText("Hey Alex, what should we build today?"),
  "Привет, Alex! Что будем создавать сегодня?"
);

const menuRes = i18n.translateMenuItems([
  { label: "Copy", submenu: [{ label: "Copy Path" }] },
  { type: "separator" },
  { label: "Delete" },
]);
assert.strictEqual(menuRes[0].label, "Копировать");
assert.strictEqual(menuRes[0].submenu[0].label, "Копировать путь");
assert.strictEqual(menuRes[2].label, "Удалить");

// Verify preload sandbox isolation (no require() inside injected preload tail)
const preloadCode = dryEntries.get("dist/preload.js").data.toString("utf8");
const marker = "/* __ANTIGRAVITY_RU_PRELOAD_PATCH__ */";
const injectedTail = preloadCode.slice(preloadCode.indexOf(marker));
assert.ok(!/\brequire\s*\(/.test(injectedTail), "Injected preload code must not call require()");

// Verify ru_dom_translator.js execution with minimal mock DOM
const domSrc = fs.readFileSync(path.join(REPO_DIR, "ru_dom_translator.js"), "utf8");
const nodes = [];
function makeEl(tag, cls = "", text = "", parent = null) {
  const el = {
    nodeType: 1,
    tagName: tag.toUpperCase(),
    nodeName: tag.toUpperCase(),
    className: cls,
    parentElement: parent,
    attributes: new Map(),
    lang: "en",
    closest(sel) {
      let cur = this;
      while (cur) {
        if (sel.includes("material-symbols") && (cur.className || "").includes("material-symbols")) return cur;
        if (sel.includes(".monaco-editor") && (cur.className || "").includes("monaco-editor")) return cur;
        if (sel.includes(".prose") && (cur.className || "").includes("prose")) return cur;
        if (sel.includes("button") && cur.tagName === "BUTTON") return cur;
        cur = cur.parentElement;
      }
      return null;
    },
    hasAttribute(k) { return this.attributes.has(k); },
    getAttribute(k) { return this.attributes.get(k); },
    setAttribute(k, v) { this.attributes.set(k, v); },
  };
  if (text) {
    nodes.push({ nodeType: 3, nodeValue: text, parentElement: el });
  }
  return el;
}
const rootEl = makeEl("html");
const btn = makeEl("button", "", "New Conversation", rootEl);
const icon = makeEl("span", "material-symbols-outlined", "Close", rootEl);
const input = makeEl("input", "", "", rootEl);
input.setAttribute("placeholder", "Search Conversations");
const prose = makeEl("div", "prose", "Settings", rootEl);
const proseBtn = makeEl("button", "", "Copy", prose);

const allWalkNodes = [rootEl, btn, icon, input, prose, proseBtn, ...nodes];
let walkIdx = -1;
const mockGlobal = {
  location: { protocol: "https:" },
  document: {
    documentElement: rootEl,
    title: "Jetski Web",
    addEventListener() {},
    createTreeWalker() {
      return {
        nextNode() {
          walkIdx++;
          return walkIdx < allWalkNodes.length ? allWalkNodes[walkIdx] : null;
        },
      };
    },
  },
  addEventListener() {},
  getComputedStyle() { return { fontFamily: "Inter" }; },
  MutationObserver: class {
    observe() {}
  },
};
mockGlobal.globalThis = mockGlobal;
mockGlobal.window = mockGlobal;
mockGlobal.top = mockGlobal;
mockGlobal.self = mockGlobal;

const wrappedDom = `((__RU_I18N__, globalThis) => {\n${domSrc}\n})`;
const runner = vm.runInNewContext(wrappedDom);
runner(i18n, mockGlobal);

assert.strictEqual(rootEl.lang, "ru");
assert.strictEqual(mockGlobal.document.title, "Antigravity");
assert.strictEqual(nodes[0].nodeValue, "Новый чат");
assert.strictEqual(nodes[1].nodeValue, "Close");
assert.strictEqual(input.getAttribute("placeholder"), "Поиск по чатам");
assert.strictEqual(nodes[2].nodeValue, "Settings");
assert.strictEqual(nodes[3].nodeValue, "Копировать");

console.log("All ASAR, i18n, preload sandbox, and DOM translator tests passed!");
