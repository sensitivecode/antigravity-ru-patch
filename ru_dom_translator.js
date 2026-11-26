// DOM localization observer for Google Antigravity Hub renderer.
// Designed to run inside Electron's isolated preload context (sandbox: true)
// sharing the live DOM with the React bundle.
(function installAntigravityRuDomTranslator(rawTranslateUiText) {
  const g = globalThis;
  const doc = g.document;
  if (!doc || g.__agyRuDomTranslatorInstalled) {
    return;
  }
  const proto = g.location && g.location.protocol;
  if (proto && proto !== "https:" && proto !== "http:") {
    return;
  }
  if (g.top && g.self && g.top !== g.self) {
    return;
  }
  g.__agyRuDomTranslatorInstalled = true;

  const _cache = new Map();
  function translateUiText(s) {
    if (_cache.has(s)) return _cache.get(s);
    const r = rawTranslateUiText(s);
    if (_cache.size > 5000) _cache.clear();
    _cache.set(s, r);
    return r;
  }

  const SKIP_TAGS = new Set([
    "SCRIPT",
    "STYLE",
    "NOSCRIPT",
    "TEXTAREA",
    "INPUT",
    "SELECT",
    "OPTION",
    "CODE",
    "PRE",
    "KBD",
    "SVG",
  ]);

  const EXCLUDED_ANCESTOR_SELECTOR = [
    ".material-symbols-outlined",
    ".material-symbols-rounded",
    ".material-symbols-sharp",
    ".material-icons",
    ".codicon",
    ".monaco-editor",
    ".xterm",
    ".cm-editor",
    ".katex",
    ".mermaid",
    '[contenteditable="true"]',
    '[contenteditable=""]',
    "[data-lexical-editor]",
    "code",
    "pre",
    "kbd",
    "svg",
  ].join(",");

  const MARKDOWN_PROSE_ANCESTOR =
    ".prose, .markdown-body, [data-testid*='markdown'], .markdown-frontmatter";
  const INTERACTIVE_UI_ANCESTOR =
    'button, [role="button"], [role="tab"], [role="menuitem"], summary';

  const TRANSLATED_ATTRS = [
    "placeholder",
    "aria-placeholder",
    "data-placeholder",
    "title",
    "aria-label",
    "alt",
    "data-tooltip",
    "data-tooltip-content",
  ];

  const translatedTextCache = new WeakMap();
  const translatedAttrCache = new WeakMap();
  const runStateByNode = new WeakMap();

  function translateTextRunGroup(run) {
    if (!run || run.length < 2) return false;
    const parent = run[0].parentElement;
    if (!parent || shouldSkipTextParent(parent)) return false;

    const existing = runStateByNode.get(run[0]);
    const isSameNodes =
      existing &&
      existing.nodes.length === run.length &&
      existing.nodes.every((n, i) => n === run[i]);

    if (isSameNodes && run.every((n, i) => n.nodeValue === existing.rendered[i])) {
      return true;
    }

    const orig = [];
    for (let i = 0; i < run.length; i++) {
      const curVal = run[i].nodeValue;
      orig.push(isSameNodes && curVal === existing.rendered[i] ? existing.orig[i] : curVal);
    }

    const combined = orig.join("");
    if (!combined || !/[A-Za-z]/.test(combined)) {
      if (isSameNodes) {
        for (let i = 0; i < run.length; i++) {
          if (run[i].nodeValue !== orig[i]) run[i].nodeValue = orig[i];
        }
      }
      return false;
    }

    const next = translateUiText(combined);
    if (next === combined) {
      if (isSameNodes) {
        for (let i = 0; i < run.length; i++) {
          if (run[i].nodeValue !== orig[i]) run[i].nodeValue = orig[i];
        }
      }
      return false;
    }

    const rendered = [next];
    for (let i = 1; i < run.length; i++) rendered.push("");
    const state = { nodes: run.slice(), orig, rendered };
    for (let i = 0; i < run.length; i++) {
      runStateByNode.set(run[i], state);
      translatedTextCache.set(run[i], rendered[i]);
      if (run[i].nodeValue !== rendered[i]) {
        run[i].nodeValue = rendered[i];
      }
    }
    return true;
  }

  function translateElementTextRuns(el) {
    if (!el || el.nodeType !== 1 || shouldSkipTextParent(el)) return false;
    const children = el.childNodes;
    if (!children || children.length < 2) return false;
    let handled = false;
    let i = 0;
    while (i < children.length) {
      if (children[i].nodeType === 3) {
        const start = i;
        while (i < children.length && children[i].nodeType === 3) i++;
        if (i - start >= 2) {
          const run = [];
          for (let j = start; j < i; j++) run.push(children[j]);
          if (translateTextRunGroup(run)) handled = true;
        }
      } else {
        i++;
      }
    }
    return handled;
  }

  function isIconFont(el) {
    try {
      const ff = g.getComputedStyle && g.getComputedStyle(el).fontFamily;
      return Boolean(ff && /material\s*symbols|material\s*icons|codicon/i.test(ff));
    } catch {
      return false;
    }
  }

  function shouldSkipTextParent(el) {
    if (!el || el.nodeType !== 1) return true;
    if (SKIP_TAGS.has(el.tagName)) return true;
    if (el.closest && el.closest(EXCLUDED_ANCESTOR_SELECTOR)) return true;
    if (isIconFont(el)) return true;
    // Do not alter AI/user markdown prose unless it's inside an interactive UI button/tab
    if (
      el.closest &&
      el.closest(MARKDOWN_PROSE_ANCESTOR) &&
      !el.closest(INTERACTIVE_UI_ANCESTOR)
    ) {
      return true;
    }
    return false;
  }

  function translateTextNode(node) {
    if (!node || node.nodeType !== 3) return;
    const raw = node.nodeValue;
    if (!raw || !/[A-Za-z]/.test(raw)) return;
    if (translatedTextCache.get(node) === raw) return;

    const parent = node.parentElement;
    if (!parent || shouldSkipTextParent(parent)) return;

    const next = translateUiText(raw);
    if (next !== raw) {
      translatedTextCache.set(node, next);
      node.nodeValue = next;
    }
  }

  function translateElementAttributes(el) {
    if (!el || el.nodeType !== 1) return;
    if (el.closest && el.closest(".monaco-editor, .xterm, .cm-editor, .katex")) {
      return;
    }
    let cache = translatedAttrCache.get(el);
    for (let i = 0; i < TRANSLATED_ATTRS.length; i++) {
      const attr = TRANSLATED_ATTRS[i];
      if (!el.hasAttribute || !el.hasAttribute(attr)) continue;
      const val = el.getAttribute(attr);
      if (!val || !/[A-Za-z]/.test(val)) continue;
      if (cache && cache[attr] === val) continue;
      const next = translateUiText(val);
      if (next !== val) {
        if (!cache) {
          cache = {};
          translatedAttrCache.set(el, cache);
        }
        cache[attr] = next;
        el.setAttribute(attr, next);
      }
    }
  }

  function walkAndTranslate(root) {
    if (!root) return;
    if (root.nodeType === 3) {
      if (!root.parentElement || !translateElementTextRuns(root.parentElement)) {
        translateTextNode(root);
      }
      return;
    }
    if (root.nodeType !== 1 && root.nodeType !== 9) return;
    const base = root.nodeType === 9 ? root.documentElement : root;
    if (!base) return;
    if (base.nodeType === 1) {
      try {
        translateElementAttributes(base);
        translateElementTextRuns(base);
      } catch {}
    }
    const walker = doc.createTreeWalker(base, 5 /* SHOW_ELEMENT | SHOW_TEXT */);
    let cur = walker.nextNode();
    while (cur) {
      try {
        if (cur.nodeType === 3) {
          translateTextNode(cur);
        } else if (cur.nodeType === 1) {
          translateElementAttributes(cur);
          translateElementTextRuns(cur);
        }
      } catch {}
      cur = walker.nextNode();
    }
  }

  function applyDocumentLangAndTitle() {
    if (doc.documentElement && doc.documentElement.lang !== "ru") {
      doc.documentElement.lang = "ru";
    }
    if (typeof doc.title === "string" && doc.title) {
      const nextTitle = translateUiText(doc.title);
      if (nextTitle !== doc.title) {
        doc.title = nextTitle;
      }
    }
  }

  let observer = null;
  function startObserver() {
    applyDocumentLangAndTitle();
    const target = doc.documentElement;
    if (!target || observer) return;

    walkAndTranslate(target);

    observer = new g.MutationObserver((mutations) => {
      for (let i = 0; i < mutations.length; i++) {
        const m = mutations[i];
        if (m.type === "characterData") {
          const p = m.target && m.target.parentElement;
          if (!p || !translateElementTextRuns(p)) {
            translateTextNode(m.target);
          }
        } else if (m.type === "attributes") {
          translateElementAttributes(m.target);
        } else if (m.type === "childList") {
          let hasTextChild = false;
          for (let j = 0; j < m.addedNodes.length; j++) {
            const added = m.addedNodes[j];
            if (added.nodeType === 3) hasTextChild = true;
            walkAndTranslate(added);
          }
          if (hasTextChild && m.target && m.target.nodeType === 1) {
            translateElementTextRuns(m.target);
          }
          if (m.target && m.target.nodeName === "TITLE") {
            applyDocumentLangAndTitle();
          }
        }
      }
    });

    observer.observe(target, {
      childList: true,
      subtree: true,
      characterData: true,
      attributes: true,
      attributeFilter: TRANSLATED_ATTRS,
    });
  }

  if (doc.documentElement) {
    startObserver();
  } else {
    doc.addEventListener("DOMContentLoaded", startObserver, { once: true });
  }
  doc.addEventListener("DOMContentLoaded", () => {
    applyDocumentLangAndTitle();
    walkAndTranslate(doc.documentElement);
  });
  g.addEventListener("load", () => {
    applyDocumentLangAndTitle();
    walkAndTranslate(doc.documentElement);
  });
})(__RU_I18N__.translateUiText);
