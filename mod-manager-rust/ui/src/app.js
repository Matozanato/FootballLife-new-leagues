const invoke = window.__TAURI__.core.invoke;
const dialog = window.__TAURI__.dialog;

// A rejected promise used to be invisible here, which is exactly how a dialog
// denied by the capability file looked: a button that did nothing at all, with
// no trace. Anything that fails now lands in the status bar instead.
window.addEventListener("unhandledrejection", (ev) => {
  const why = ev.reason && ev.reason.message ? ev.reason.message : String(ev.reason);
  say("Failed: " + why, "err");
});
window.addEventListener("error", (ev) => {
  if (ev.message) say("Error: " + ev.message, "err");
});

const $ = (id) => document.getElementById(id);
const el = (tag, cls, text) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text !== undefined) n.textContent = text;
  return n;
};

let state = {
  game: "",
  addons: "",
  ini: "",
  packsRoot: "",
  rows: [],
  dirty: false,
  cpk: null,
  tex: null,
};

function say(msg, kind) {
  const s = $("status");
  s.textContent = msg;
  s.className = "status" + (kind ? " " + kind : "");
}

async function busy(msg, fn) {
  say(msg + "…");
  try {
    const out = await fn();
    return out;
  } catch (err) {
    say(String(err), "err");
    throw err;
  }
}

// tauri-plugin-dialog exposes open, save, message, ask and confirm -- there is
// no prompt, so anything that needs typed text goes through the app's own
// modal. Resolves to the trimmed string, or null on cancel or empty input,
// which is the shape every caller here already expected from dialog.prompt.
function promptText(title, value) {
  return new Promise((resolve) => {
    const box = $("modal"), inp = $("modalInput");
    $("modalTitle").textContent = title;
    inp.value = value || "";
    box.classList.remove("hidden");
    inp.focus();
    inp.select();
    const finish = (v) => {
      box.classList.add("hidden");
      $("modalOk").onclick = null;
      $("modalCancel").onclick = null;
      inp.onkeydown = null;
      resolve(v);
    };
    const accept = () => { const v = inp.value.trim(); finish(v || null); };
    $("modalOk").onclick = accept;
    $("modalCancel").onclick = () => finish(null);
    inp.onkeydown = (ev) => {
      if (ev.key === "Enter") { ev.preventDefault(); accept(); }
      else if (ev.key === "Escape") { ev.preventDefault(); finish(null); }
    };
  });
}

async function pick(opts) {
  const chosen = await dialog.open(opts);
  return typeof chosen === "string" ? chosen : null;
}

// ---------------------------------------------------------------- game map

const EDIT_BREAK = {
  safe: "Get it wrong and you can put the original back; nothing else moves.",
  careful: "Get it wrong and this content stops loading until you restore the file you replaced.",
  risky: "Get it wrong and the game can crash, refuse to start, or corrupt a save that is already written.",
  readonly: "Writing here is never the fix; something else is what you actually want to change.",
  unknown: "Nobody has established what these bytes do, so an edit here is a guess.",
};

const EDIT_LABEL = {
  safe: "safe to edit", careful: "back up first", risky: "structural — risky",
  readonly: "read only", unknown: "unknown",
};

function fmtBytes(n) {
  if (!n) return "—";
  if (n < 1024) return n + " B";
  if (n < 1048576) return (n / 1024).toFixed(1) + " KB";
  if (n < 1073741824) return (n / 1048576).toFixed(1) + " MB";
  return (n / 1073741824).toFixed(2) + " GB";
}

let mapData = null;

$("loadMap").addEventListener("click", () => loadMap(true));
$("mapFilter").addEventListener("input", () => mapData && renderTree());

async function loadMap(refresh) {
  if (!state.game) return say("Choose a game folder first.", "err");
  mapData = await busy("Mapping the install", () =>
    invoke("game_map", { game: state.game, refresh: !!refresh }));
  $("mapStats").textContent =
    `${mapData.archives} archives · ${fmtBytes(mapData.archive_bytes)} · ` +
    `${mapData.findings.length} finding(s)`;
  renderFindings();
  renderTree();
  const first = mapData.nodes[0];
  if (first) selectNode(first);
  say(`Mapped ${mapData.nodes.length} top-level groups.`,
      mapData.findings.some((f) => f.severity === "error") ? "err" : "ok");
}

function renderFindings() {
  const box = $("findings");
  box.innerHTML = "";
  mapData.findings.slice(0, 40).forEach((f) => {
    const d = el("div", "finding " + f.severity);
    d.appendChild(el("b", null, f.title));
    d.appendChild(el("span", null, f.detail));
    box.appendChild(d);
  });
  if (mapData.findings.length > 40) {
    box.appendChild(el("div", "finding",
      `… ${mapData.findings.length - 40} more findings`));
  }
}

function matches(node, q) {
  if (!q) return true;
  if (node.name.toLowerCase().includes(q) || node.rel.toLowerCase().includes(q) ||
      node.info.title.toLowerCase().includes(q) || node.info.what.toLowerCase().includes(q)) {
    return true;
  }
  return node.children.some((c) => matches(c, q));
}

function renderTree() {
  const box = $("mapTree");
  box.innerHTML = "";
  const q = $("mapFilter").value.trim().toLowerCase();
  mapData.nodes.filter((n) => matches(n, q)).forEach((n) => box.appendChild(treeNode(n, q, 0)));
}

function treeNode(node, q, depth) {
  const wrap = el("div");
  const row = el("div", "tnode");
  row.dataset.rel = node.rel;
  const kids = node.children.filter((c) => matches(c, q));
  const twist = el("span", "tw", kids.length ? "▸" : "");
  row.appendChild(twist);
  row.appendChild(el("span", "tn", node.name));
  if (node.bytes) row.appendChild(el("span", "ts", fmtBytes(node.bytes)));
  wrap.appendChild(row);

  let kidBox = null;
  if (kids.length) {
    kidBox = el("div", "tkids hidden");
    kids.forEach((c) => kidBox.appendChild(treeNode(c, q, depth + 1)));
    wrap.appendChild(kidBox);
  }
  const expand = (on) => {
    if (!kidBox) return;
    kidBox.classList.toggle("hidden", !on);
    twist.textContent = on ? "▾" : "▸";
  };
  if (q || depth === 0) expand(true);

  twist.addEventListener("click", (ev) => {
    ev.stopPropagation();
    expand(kidBox.classList.contains("hidden"));
  });
  row.addEventListener("click", () => {
    document.querySelectorAll(".tnode.selected").forEach((x) => x.classList.remove("selected"));
    row.classList.add("selected");
    selectNode(node);
    if (kidBox) expand(true);
  });
  return wrap;
}

function selectNode(node) {
  const box = $("mapInfo");
  box.innerHTML = "";
  box.appendChild(el("h2", null, node.info.title));
  box.appendChild(el("div", "sub", node.path || node.rel));
  box.appendChild(el("p", null, node.info.what));

  const meta = el("div", "meta");
  const kv = (label, value, cls) => {
    const d = el("div", "kv");
    d.appendChild(el("b", null, label));
    if (cls) d.appendChild(el("span", "badge " + cls, value));
    else d.appendChild(document.createTextNode(value));
    meta.appendChild(d);
  };
  kv("format", node.info.format);
  kv("editing", EDIT_LABEL[node.info.edit] || node.info.edit, node.info.edit);
  if (node.bytes) kv("size", fmtBytes(node.bytes));
  if (node.files) kv("files", node.files.toLocaleString());
  box.appendChild(meta);

  const breaks = el("div", "how");
  breaks.appendChild(el("b", null, "If you change it: "));
  breaks.appendChild(document.createTextNode(node.info.breaks || EDIT_BREAK[node.info.edit] || ""));
  box.appendChild(breaks);

  const how = el("div", "how");
  how.appendChild(el("b", null, "How to work with it: "));
  how.appendChild(document.createTextNode(node.info.how));
  box.appendChild(how);

  const actions = el("div", "actions");
  if (node.open_as === "cpk") {
    const b = el("button", null, "Open in archives");
    b.addEventListener("click", () => {
      document.querySelector("[data-tab=archives]").click();
      $("cpkPath").value = node.path;
      openCpk();
    });
    actions.appendChild(b);
    const m = el("button", "ghost", "Explain what's inside");
    m.addEventListener("click", () => explainArchive(node.path));
    actions.appendChild(m);
  } else if (node.open_as === "packs") {
    const b = el("button", null, "Open pack order");
    b.addEventListener("click", () => document.querySelector("[data-tab=packs]").click());
    actions.appendChild(b);
  }
  if (actions.childNodes.length) box.appendChild(actions);
  $("archiveSections").innerHTML = "";
}

async function explainArchive(path) {
  const r = await busy("Reading the archive's contents", () =>
    invoke("archive_map", { archive: path, depth: 3 }));
  const wrap = $("archiveSections");
  wrap.innerHTML = "";
  const table = el("table");
  const head = el("thead");
  const hr = el("tr");
  ["Section", "What it is", "Files", "Unpacked", "Editing"].forEach((h) =>
    hr.appendChild(el("th", null, h)));
  head.appendChild(hr);
  table.appendChild(head);
  const body = el("tbody");
  r.sections.forEach((s) => {
    const tr = el("tr");
    tr.appendChild(el("td", "path", s.path));
    tr.appendChild(el("td", null, s.info.title));
    tr.appendChild(el("td", "num", s.files.toLocaleString()));
    tr.appendChild(el("td", "num", fmtBytes(s.bytes)));
    const td = el("td");
    td.appendChild(el("span", "badge " + s.info.edit, EDIT_LABEL[s.info.edit] || s.info.edit));
    tr.appendChild(td);
    tr.title = s.info.what;
    body.appendChild(tr);
  });
  table.appendChild(body);
  wrap.appendChild(table);
  say(`${r.entries.toLocaleString()} entries, ${fmtBytes(r.unpacked)} unpacked, ` +
      `${r.compressed} compressed.`, "ok");
}

// ---------------------------------------------------------------- tabs

// Whole-install reports are only computed when their tab is first opened, and
// then served from the backend cache. Nothing expensive runs at startup except
// the map for the tab actually on screen.
const loaded = {};

function showTab(name) {
  document.querySelectorAll(".tabs button").forEach((x) =>
    x.classList.toggle("active", x.dataset.tab === name));
  document.querySelectorAll(".tab").forEach((x) => x.classList.remove("active"));
  $("tab-" + name).classList.add("active");
  if (!state.game || loaded[name]) return;
  if (name === "map") { loaded.map = true; loadMap(false); }
  if (name === "packs") { loaded.packs = true; loadOrder(false); }
}

document.querySelectorAll(".tabs button").forEach((b) => {
  b.addEventListener("click", () => {
    showTab(b.dataset.tab);
    try { localStorage.setItem("fl27mm.tab", b.dataset.tab); } catch (err) {}
  });
});

// Keyboard: Ctrl+1..7 jumps to a tab, Ctrl+R refreshes the view that is on
// screen. Typed into the editor these are left to the editor's own handlers.
document.addEventListener("keydown", (ev) => {
  if (!ev.ctrlKey || ev.metaKey || ev.altKey) return;
  const target = ev.target;
  const inEditor = target && target.id === "code";
  const inField = target && /^(INPUT|SELECT|TEXTAREA)$/.test(target.tagName);
  if (/^[1-7]$/.test(ev.key)) {
    const tabs = document.querySelectorAll(".tabs button");
    const b = tabs[Number(ev.key) - 1];
    if (b) { ev.preventDefault(); b.click(); }
    return;
  }
  if (ev.key.toLowerCase() === "r" && !inEditor) {
    ev.preventDefault();
    const on = document.querySelector(".tabs button.active");
    const name = on ? on.dataset.tab : "map";
    if (name === "map") loadMap(true);
    else if (name === "packs") loadOrder(true);
    else if (name === "studio" && studio.root) loadStudio();
    else if (name === "conflicts" && $("conflictRoot").value) $("runConflicts").click();
    else if (name === "tables" && $("containerPath").value) $("runContainer").click();
    else if (inField) say("Nothing to refresh on this tab yet", "warn");
    else say("Open something first", "warn");
  }
});

// ---------------------------------------------------------------- install

function setInstall(inst) {
  state.game = inst.game;
  state.addons = inst.addons;
  state.ini = inst.ini;
  state.packsRoot = inst.packs_root;
  $("gamePath").value = inst.game;
  $("conflictRoot").value = inst.packs_root;
  $("tableDir").value = inst.packs_root;
  // Remember it. Detection missed installs on drives and folders nobody had
  // listed, and a folder chosen once was gone after a restart, so the app read
  // as refusing to register the game.
  rememberInstall(inst.game);
}

// The five most recent installs the user chose, oldest first. Kept because
// automatic search can still miss a network share or an unusual layout, and a
// person should not have to re-pick their game every time they open the tool.
function rememberedInstalls() {
  try {
    const list = JSON.parse(localStorage.getItem("fl27mm.installs") || "[]");
    return Array.isArray(list) ? list.filter((x) => typeof x === "string") : [];
  } catch (err) {
    return [];
  }
}

function rememberInstall(game) {
  try {
    const kept = rememberedInstalls().filter((x) => x.toLowerCase() !== game.toLowerCase());
    kept.push(game);
    localStorage.setItem("fl27mm.installs", JSON.stringify(kept.slice(-5)));
  } catch (err) {}
}

function installFromPath(game) {
  const sep = game.includes("\\") ? "\\" : "/";
  const trimmed = game.replace(/[\\/]+$/, "");
  const addons = trimmed + sep + "SiderAddons";
  return {
    game: trimmed,
    addons,
    ini: addons + sep + "sider.ini",
    packs_root: addons + sep + "livecpk" + sep + "root",
  };
}

// ------------------------------------------------------------- Mod Studio
//
// A workspace tree, a tabbed editor and the pack commands. The editor is
// hand-built rather than a library: the app ships no bundler, so dropping in
// CodeMirror or Monaco would mean vendoring a build pipeline for one feature.
// A transparent textarea over a highlighted pre, with a synced line-number
// gutter, is a few dozen lines and is enough for ini, lua and json.

const studio = { tabs: [], active: -1, selDir: "", sel: null, kinds: [], pending: null };
const HL_LIMIT = 6000;          // lines; past this the overlay stays plain text
const LUA_WORDS = "local|function|end|if|then|else|elseif|for|while|do|return|" +
  "and|or|not|nil|true|false|in|repeat|until|break|goto";

const PATTERNS = {
  lua: new RegExp("(--\\[\\[[\\s\\S]*?\\]\\]|--[^\\n]*|\"(?:[^\"\\\\\\n]|\\\\.)*\"" +
    "|'(?:[^'\\\\\\n]|\\\\.)*'|\\b(?:" + LUA_WORDS + ")\\b|\\b\\d+(?:\\.\\d+)?\\b)", "g"),
  ini: /^[ \t]*[#;][^\n]*|[A-Za-z_][A-Za-z0-9_.]*(?=[ \t]*=)|"(?:[^"\\]|\\.)*"|\b\d+(?:\.\d+)?\b/gm,
  json: /"(?:[^"\\]|\\.)*"|\b(?:true|false|null)\b|-?\d+(?:\.\d+)?/g,
  text: /^[ \t]*[#;][^\n]*|\/\/[^\n]*|"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|\b\d+(?:\.\d+)?\b/gm,
};

function langOf(path) {
  const ext = (path.split(".").pop() || "").toLowerCase();
  if (ext === "lua") return "lua";
  if (ext === "json") return "json";
  if (["ini", "cfg", "toml", "conf", "properties"].includes(ext)) return "ini";
  return "text";
}

const escHtml = (s) => s.replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));

function classOf(tok, lang) {
  if (/^(--|#|;|\/\/)/.test(tok)) return "t-com";
  if (/^["']/.test(tok)) return "t-str";
  if (/^-?\d/.test(tok)) return "t-num";
  if (lang === "ini") return "t-key";
  return "t-kw";
}

function highlight(text, lang) {
  const re = PATTERNS[lang] || PATTERNS.text;
  let out = "", last = 0, m;
  re.lastIndex = 0;
  while ((m = re.exec(text)) !== null) {
    if (m.index === re.lastIndex) { re.lastIndex++; continue; }
    out += escHtml(text.slice(last, m.index));
    const tok = m[0];
    out += '<span class="' + classOf(tok.trim(), lang) + '">' + escHtml(tok) + "</span>";
    last = m.index + tok.length;
  }
  return out + escHtml(text.slice(last));
}

const fmtSize = (n) => n >= 1048576 ? (n / 1048576).toFixed(2) + " MB"
  : n >= 1024 ? (n / 1024).toFixed(1) + " KB" : n + " B";
const baseName = (p) => p.split("/").filter(Boolean).pop() || p;
const activeTab = () => studio.tabs[studio.active] || null;

// ------------------------------------------------------------------ tree

async function loadStudio() {
  // Default the workspace to the SiderAddons folder: it is where every pack
  // and every sider.ini a modder edits actually lives, so opening the tab and
  // seeing an empty tree is just a wasted step.
  if (!$("studioRoot").value.trim() && state.addons) {
    $("studioRoot").value = state.addons.replace(/\\/g, "/");
  }
  const root = $("studioRoot").value.trim();
  if (!root) { say("Pick a workspace folder first", "warn"); return; }
  studio.root = root;
  studio.selDir = "";
  const box = $("studioTree");
  box.innerHTML = "";
  await fillTree(box, root, 0);
  $("studioStats").textContent = root;
}

async function fillTree(box, dir, depth) {
  let nodes;
  try {
    nodes = await busy("Listing " + baseName(dir), () => invoke("studio_tree", { root: dir }));
  } catch (err) {
    return;
  }
  if (!nodes.length) {
    box.appendChild(el("div", "trow dim", "empty"));
    return;
  }
  for (const n of nodes) box.appendChild(treeRow(n, depth));
}

function treeRow(node, depth) {
  const row = el("div", "trow" + (node.hidden_by_default ? " dim" : ""));
  row.style.paddingLeft = (4 + depth * 12) + "px";
  row.append(el("span", "tw", node.dir ? "▸" : "·"), el("span", "nm", node.name));
  if (!node.dir) row.append(el("span", "sz", fmtSize(node.size)));
  const kids = el("div", "kids");
  row.addEventListener("click", async () => {
    document.querySelectorAll(".trow.sel").forEach((r) => r.classList.remove("sel"));
    row.classList.add("sel");
    studio.sel = node;
    $("selPath").textContent = node.path;
    $("selPath").classList.remove("dim");
    if (!node.dir) { openFile(node.path); return; }
    studio.selDir = node.path;
    if (row.dataset.open === "1") {
      kids.hidden = !kids.hidden;
      row.firstChild.textContent = kids.hidden ? "▸" : "▾";
      return;
    }
    row.dataset.open = "1";
    row.firstChild.textContent = "▾";
    await fillTree(kids, node.path, depth + 1);
  });
  const wrap = el("div");
  wrap.append(row, kids);
  return wrap;
}

// ----------------------------------------------------------------- editor

function renderTabs() {
  const box = $("editorTabs");
  box.innerHTML = "";
  studio.tabs.forEach((t, i) => {
    const tab = el("div", "etab" + (i === studio.active ? " on" : ""));
    tab.append(el("span", null, baseName(t.path)));
    if (t.text !== t.saved) tab.append(el("span", "dirty", "●"));
    const x = el("span", "x", "×");
    x.addEventListener("click", (ev) => { ev.stopPropagation(); closeTab(i); });
    tab.append(x);
    tab.addEventListener("click", () => { studio.active = i; renderTabs(); renderEditor(); });
    box.appendChild(tab);
  });
}

async function openFile(path) {
  const found = studio.tabs.findIndex((t) => t.path === path);
  if (found >= 0) { studio.active = found; renderTabs(); renderEditor(); return; }
  const f = await busy("Opening " + baseName(path), () => invoke("studio_read", { path }));
  if (/\.bin$/i.test(path)) {
    await openBin(path);
    return;
  }
  if (f.binary) {
    $("editorStatus").textContent = baseName(path) + " is binary (" + fmtSize(f.size) +
      ") and is not editable here. Use the CPK, Textures or Tables tab for it.";
    return;
  }
  studio.tabs.push({ path: f.path, text: f.text, saved: f.text, lang: langOf(f.path) });
  studio.active = studio.tabs.length - 1;
  renderTabs();
  renderEditor();
}


// A .bin is a table, not text: opening it as characters would show mojibake
// and saving would destroy it. The Tables tab already has a real reader that
// decodes framing, sections, record stride and inferred field structure, so a
// table is handed to that rather than being re-rendered here as a hexdump.
async function openBin(path) {
  $("binPath").value = path;
  document.querySelector('[data-tab=tables]').click();
  await runBin();
  const box = $("binPatch");
  if (box) {
    box.hidden = false;
    box.dataset.path = $("binPath").value;
  }
  say("Decoded as a table. Offsets below are into the decoded body.", "ok");
}


async function closeTab(i) {
  const t = studio.tabs[i];
  if (!t) return;
  if (t.text !== t.saved) {
    const keep = await dialog.ask("Discard the unsaved changes in " + baseName(t.path) + "?",
      { title: "Unsaved changes", kind: "warning" });
    if (!keep) return;
  }
  studio.tabs.splice(i, 1);
  studio.active = Math.min(studio.active, studio.tabs.length - 1);
  renderTabs();
  renderEditor();
}

function renderEditor() {
  const t = activeTab();
  const area = $("code");
  if (!t) {
    area.value = "";
    $("highlight").textContent = "";
    $("gutter").innerHTML = "";
    $("editorStatus").textContent = studio.tabs.length ? "" : "No file open.";
    return;
  }
  area.value = t.text;
  paint();
  syncScroll();
  updateStatus();
}

function paint() {
  const t = activeTab();
  if (!t) return;
  const lines = t.text.split("\n").length;
  const box = $("gutter");
  box.innerHTML = "";
  if (lines > HL_LIMIT) {
    $("highlight").textContent = t.text;
    box.append(el("div", null, lines + " lines"));
    return;
  }
  const nums = [];
  for (let i = 1; i <= lines; i++) nums.push(i);
  $("highlight").innerHTML = highlight(t.text, t.lang) + "\n";
  box.append(el("div", null, nums.join("\n")));
}

function updateStatus() {
  const t = activeTab();
  if (!t) return;
  const area = $("code");
  const lines = t.text.split("\n").length;
  const dirty = t.text !== t.saved;
  const upto = t.text.slice(0, area.selectionStart);
  const ln = upto.split("\n").length;
  const col = upto.length - upto.lastIndexOf("\n");
  const sel = area.selectionEnd - area.selectionStart;
  const s = $("editorStatus");
  s.textContent = t.path + " · " + t.lang + " · " + lines + " lines · " +
    fmtSize(t.text.length) + (dirty ? " · unsaved" : " · saved") +
    " · Ln " + ln + ", Col " + col + (sel ? " · " + sel + " selected" : "");
  s.style.color = dirty ? "var(--warn)" : "var(--muted)";
}

function syncScroll() {
  const area = $("code");
  $("highlight").style.transform =
    "translate(" + (-area.scrollLeft) + "px," + (-area.scrollTop) + "px)";
  const g = $("gutter").firstElementChild;
  if (g) g.style.transform = "translateY(" + (-area.scrollTop) + "px)";
}

let paintTimer = null;
function onEdit() {
  const t = activeTab();
  if (!t) return;
  const wasDirty = t.text !== t.saved;
  t.text = $("code").value;
  if (wasDirty !== (t.text !== t.saved)) renderTabs();
  clearTimeout(paintTimer);
  paintTimer = setTimeout(() => { paint(); syncScroll(); }, 110);
  updateStatus();
}

async function saveActive() {
  const t = activeTab();
  if (!t) return;
  const n = await busy("Saving " + baseName(t.path), () =>
    invoke("studio_write", { path: t.path, text: t.text }));
  t.saved = t.text;
  renderTabs();
  updateStatus();
  say("Saved " + baseName(t.path) + " (" + n + " bytes)");
}

// ------------------------------------------------------------------- find

function findStep(back) {
  const area = $("code"), q = $("findText").value;
  if (!q) return;
  const text = area.value.toLowerCase(), needle = q.toLowerCase();
  let at;
  if (!back) {
    at = text.indexOf(needle, area.selectionEnd);
    if (at < 0) at = text.indexOf(needle);
  } else {
    at = text.lastIndexOf(needle, Math.max(0, area.selectionStart - 1));
    if (at < 0) at = text.lastIndexOf(needle);
  }
  if (at < 0) { $("findStats").textContent = "no match"; return; }
  area.focus();
  area.setSelectionRange(at, at + q.length);
  $("findStats").textContent = "line " + (area.value.slice(0, at).split("\n").length);
}

function replaceOne() {
  const area = $("code"), q = $("findText").value;
  if (!q) return;
  if (area.value.slice(area.selectionStart, area.selectionEnd) === q) {
    area.setRangeText($("replText").value, area.selectionStart, area.selectionEnd, "end");
    onEdit();
  }
  findStep(false);
}

function replaceAll() {
  const t = activeTab(), q = $("findText").value;
  if (!t || !q) return;
  const parts = t.text.split(q);
  if (parts.length < 2) { $("findStats").textContent = "nothing to replace"; return; }
  $("findStats").textContent = (parts.length - 1) + " replaced";
  t.text = parts.join($("replText").value);
  $("code").value = t.text;
  renderTabs();
  paint();
  updateStatus();
}

// ---------------------------------------------------------------- actions

async function doNewPack() {
  const name = $("packName").value.trim();
  if (!name) { say("Give the pack a name first", "warn"); return; }
  if (!state.addons) { say("No SiderAddons folder detected — set the game first", "warn"); return; }
  const yes = await dialog.ask(
    "Create the scaffold for \"" + name + "\" under\n" + state.addons +
    "\n\nExisting files are never overwritten.",
    { title: "Create pack", kind: "info" });
  if (!yes) return;
  const r = await busy("Scaffolding " + name, () =>
    invoke("studio_new_pack", { addons: state.addons, name, kind: $("packKind").value }));
  const box = $("studioReport");
  box.innerHTML = "";
  box.appendChild(el("div", null, "Pack folder: " + r.dir));
  const made = r.created.filter((p) => !r.files.includes(p));
  box.appendChild(el("div", null, made.length + " folder(s) created"));
  made.forEach((p) => box.appendChild(el("div", "muted", p)));
  r.files.forEach((p) => box.appendChild(el("div", "muted", "file  " + p)));
  if (r.skipped.length) {
    box.appendChild(el("div", "warn", "Left alone, already existed:"));
    r.skipped.forEach((p) => box.appendChild(el("div", "muted", p)));
  }
  // The core re-checks its own work; if anything is missing the scaffold did
  // not land, and that must be loud rather than a green "Created" message.
  if (r.missing.length) {
    box.appendChild(el("div", "err", "INCOMPLETE: " + r.missing.join(", ")));
    say("Scaffold incomplete: " + r.missing.join(", "), "err");
  } else {
    box.appendChild(el("div", "ok", "Verified: every path exists as expected"));
    box.appendChild(el("div", "muted", "To register it: " + r.note));
    say("Scaffolded " + name + " — " + r.files.length + " file(s)");
  }
  if (studio.root) loadStudio();
}

async function doCheckPack() {
  const dir = studio.selDir;
  if (!dir) { say("Select a pack folder in the tree first", "warn"); return; }
  const r = await busy("Validating " + baseName(dir), () =>
    invoke("studio_check_pack", { dir, addons: state.addons }));
  const box = $("studioReport");
  box.innerHTML = "";
  box.appendChild(el("div", null, baseName(dir) + " · " +
    (r.registered ? "registered in sider.ini" : "NOT registered in sider.ini")));
  box.appendChild(el("div", "muted", r.notes.join(" · ")));
  if (r.shadows.length) {
    box.appendChild(el("div", "warn", "Earlier packs already contain " +
      r.shadows.length + " of these files, so they win:"));
    r.shadows.forEach((s) => box.appendChild(el("div", "muted", s)));
  }
  say("Validated " + baseName(dir));
}

async function doInstall() {
  const dir = studio.selDir;
  if (!dir) { say("Select the pack folder you want to install", "warn"); return; }
  if (!state.addons) { say("No SiderAddons folder detected — set the game first", "warn"); return; }
  const yes = await dialog.ask(
    "Install \"" + baseName(dir) + "\"?\n\nIt is copied into " + state.addons +
    "\\livecpk\\root and a cpk.root line is added before the base root so it wins " +
    "over the stock files. sider.ini is copied aside first, and every copied file " +
    "is checked against its source.",
    { title: "Install pack", kind: "warning" });
  if (!yes) return;
  const r = await busy("Installing " + baseName(dir), () =>
    invoke("studio_install", { src: dir, addons: state.addons }));
  const box = $("studioReport");
  box.innerHTML = "";
  const bad = r.files.filter((f) => !f.verified);
  box.appendChild(el("div", null,
    "Copied " + r.files.length + " files, " + fmtSize(r.bytes) + " into " + r.target));
  box.appendChild(el("div", bad.length ? "err" : null, bad.length
    ? bad.length + " file(s) FAILED the byte-for-byte check"
    : "All " + r.files.length + " copies verified byte for byte"));
  box.appendChild(el("div", "muted", r.ini_line
    ? "Added to sider.ini: " + r.ini_line : "sider.ini unchanged"));
  if (r.backup) box.appendChild(el("div", "muted", "Backup: " + r.backup));
  r.warnings.forEach((w) => box.appendChild(el("div", "warn", w)));
  say("Installed " + baseName(dir));
  loadOrder(true);
}

function showKindHint() {
  const k = studio.kinds.find((x) => x.kind === $("packKind").value);
  if (!k) return;
  $("kindHint").textContent = "New " + k.kind + " pack: " + k.hint +
    ". Registered by " + k.hook + ". Layout: " + k.layout.join(", ") + ".";
}

// ------------------------------------------------------------ file ops

function selDirOrRoot() {
  if (studio.sel && studio.sel.dir) return studio.sel.path;
  if (studio.sel) return studio.sel.path.split("/").slice(0, -1).join("/");
  return studio.root || state.addons || "";
}

async function newFile() {
  const base = selDirOrRoot();
  if (!base) { say("Pick a workspace folder first", "warn"); return; }
  const name = await promptText("File name inside " + base, "notes.txt");
  if (!name) return;
  const path = base.replace(/\/+$/, "") + "/" + name.replace(/^\/+/, "");
  const n = await busy("Creating " + name, () => invoke("studio_create", { path }));
  say("Created " + path + " (" + n + " bytes)");
  await loadStudio();
  openFile(path);
}

async function renameSel() {
  if (!studio.sel) { say("Select something in the tree first", "warn"); return; }
  const to = await promptText("New name for " + studio.sel.name, studio.sel.name);
  if (!to || to === studio.sel.name) return;
  if (/[/\\]/.test(to)) { say("A name cannot contain a path separator", "err"); return; }
  const dest = studio.sel.path.split("/").slice(0, -1).join("/") + "/" + to;
  await busy("Renaming", () => invoke("studio_rename", { from: studio.sel.path, to: dest }));
  say("Renamed to " + dest);
  await loadStudio();
}

async function deleteSel() {
  if (!studio.sel) { say("Select something in the tree first", "warn"); return; }
  const what = studio.sel.dir ? "folder and everything inside it" : "file";
  const yes = await dialog.ask("Delete this " + what + "?\n\n" + studio.sel.path +
    "\n\nThis is not a move to a recycle bin — it is gone.",
    { title: "Delete", kind: "warning" });
  if (!yes) return;
  await busy("Deleting", () => invoke("studio_remove",
    { path: studio.sel.path, workspace: studio.root }));
  say("Deleted " + studio.sel.path);
  studio.sel = null;
  studio.selDir = "";
  $("selPath").textContent = "nothing";
  $("selPath").classList.add("dim");
  await loadStudio();
}

async function revealSel() {
  if (!studio.sel) { say("Select something in the tree first", "warn"); return; }
  try {
    await invoke("studio_reveal", { path: studio.sel.path });
  } catch (err) {
    say(String(err), "err");
  }
}

// ---------------------------------------------------- registered packs
//
// The order of the cpk.root lines is the whole point of Sider, so this panel
// is the mod maker's main control. Nothing writes until Apply: every action
// first asks the core for the exact lines it would change.

async function loadEntries() {
  if (!state.addons) { say("No SiderAddons folder detected — set the game first", "warn"); return; }
  const rows = await busy("Reading sider.ini", () => invoke("studio_entries", { addons: state.addons }));
  const body = $("entryTable").querySelector("tbody");
  body.innerHTML = "";
  rows.forEach((r) => body.appendChild(entryRow(r)));
  $("editPreview").innerHTML = "";
  $("packPanel").hidden = false;
  $("packPanel").scrollIntoView({ block: "nearest" });
  const off = rows.filter((r) => !r.enabled).length;
  const gone = rows.filter((r) => !r.exists && !r.is_base).length;
  say(rows.length + " registered lines · " + off + " switched off" +
      (gone ? " · " + gone + " point at nothing on disk" : ""));
}

function entryRow(r) {
  const tr = el("tr", (r.enabled ? "" : "rowoff") + (r.is_base ? " rowbase" : ""));
  tr.append(el("td", "num", String(r.order)));
  tr.append(el("td", null, r.key));
  const val = el("td", "val", r.value);
  val.title = r.resolved + (r.comment ? "\n" + r.comment.trim() : "");
  tr.append(val);
  tr.append(el("td", null, r.is_base ? "base — always last" : (r.enabled ? "on" : "off")));
  tr.append(el("td", r.exists ? null : "err", r.exists ? "yes" : "MISSING"));
  tr.append(el("td", "num", String(r.line)));
  const act = el("td");
  const btn = (label, mode, tip) => {
    const b = el("button", "pbtn", label);
    b.title = tip;
    if (r.is_base) b.disabled = true;
    b.addEventListener("click", () => previewEdit(r, mode));
    act.append(b);
  };
  btn("↑", "up", "move earlier: it then wins over the packs listed below it");
  btn("↓", "down", "move later: the packs listed above it win over it");
  btn(r.enabled ? "off" : "on", r.enabled ? "disable" : "enable",
      "switch the line's semicolon, keeping it in place so the order survives");
  btn("remove", "remove", "delete the line from sider.ini — the files stay on disk");
  tr.append(act);
  return tr;
}

async function previewEdit(r, mode) {
  let p;
  try {
    p = await busy("Previewing", () => invoke("studio_edit",
      { addons: state.addons, key: r.key, value: r.value, mode, apply: false }));
  } catch (err) {
    say(String(err), "err");
    return;
  }
  studio.pending = { r, mode };
  const box = $("editPreview");
  box.innerHTML = "";
  box.appendChild(el("div", null, p.action + " — this is what would change:"));
  p.before.forEach((l) => box.appendChild(el("div", "del", "-  " + l)));
  if (!p.after.length) box.appendChild(el("div", "add", "+  (line removed)"));
  p.after.forEach((l) => box.appendChild(el("div", "add", "+  " + l)));
  const bar = el("div", "toolbar");
  const apply = el("button", null, "Apply");
  apply.addEventListener("click", applyPending);
  const cancel = el("button", "ghost", "Cancel");
  cancel.addEventListener("click", () => { studio.pending = null; box.innerHTML = ""; });
  bar.append(apply, cancel, el("span", "muted",
    "sider.ini is copied aside first; every other line is written back untouched"));
  box.append(bar);
}

async function applyPending() {
  if (!studio.pending) return;
  const { r, mode } = studio.pending;
  const got = await busy("Writing sider.ini", () => invoke("studio_edit",
    { addons: state.addons, key: r.key, value: r.value, mode, apply: true }));
  studio.pending = null;
  say(got.note + (got.backup ? " — backup at " + got.backup : ""));
  await loadEntries();
  loadOrder(true);
}

// -------------------------------------------------------- editor comfort

const INDENT = { lua: "  ", json: "  ", ini: "\t", text: "  " };

function indentUnit() {
  const t = activeTab();
  return (t && INDENT[t.lang]) || "  ";
}

/// Tab indents a block, Shift+Tab takes one level back. A bare Tab with no
/// selection just inserts the unit, which is what every editor does and what
/// makes Lua editing tolerable.
function handleIndent(ev, outdent) {
  const area = $("code"), t = activeTab();
  if (!t) return;
  ev.preventDefault();
  const unit = indentUnit();
  const s = area.selectionStart, e = area.selectionEnd;
  if (s === e && !outdent) {
    area.setRangeText(unit, s, e, "end");
    onEdit();
    return;
  }
  const start = area.value.lastIndexOf("\n", s - 1) + 1;
  const nl = area.value.indexOf("\n", e);
  const end = nl < 0 ? area.value.length : nl;
  const block = area.value.slice(start, end);
  const out = block.split("\n").map((l) => {
    if (outdent) return l.replace(/^(?:\t| {1,2})/, "");
    return l.length ? unit + l : l;
  }).join("\n");
  area.setRangeText(out, start, end, "select");
  onEdit();
}

/// Enter keeps the current indentation and adds one level after a line that
/// opens a block, so Lua and JSON do not have to be re-indented by hand.
function handleEnter(ev) {
  const area = $("code"), t = activeTab();
  if (!t || area.selectionStart !== area.selectionEnd) return;
  const s = area.selectionStart;
  const start = area.value.lastIndexOf("\n", s - 1) + 1;
  const line = area.value.slice(start, s);
  const lead = (line.match(/^[ \t]*/) || [""])[0];
  const trimmed = line.trimEnd();
  const opens = t.lang === "lua"
    ? /(\bthen|\bdo|\bfunction\b[^)]*$|[{([]\s*$)/.test(trimmed)
    : /([{\[(])$/.test(trimmed);
  ev.preventDefault();
  const closeAhead = t.lang === "json" && trimmed.endsWith("{");
  const ins = "\n" + lead + (opens ? indentUnit() : "") + (closeAhead ? "\n" + lead + "}" : "");
  if (closeAhead) {
    area.setRangeText(ins, s, area.selectionEnd, "end");
    // Put the caret on the blank middle line, inside the new block.
    area.setSelectionRange(s + 1 + lead.length + indentUnit().length,
                           s + 1 + lead.length + indentUnit().length);
  } else {
    area.setRangeText(ins, area.selectionStart, area.selectionEnd, "end");
  }
  onEdit();
  syncScroll();
}

async function gotoLine() {
  const t = activeTab();
  if (!t) { say("Open a file first", "warn"); return; }
  const lines = t.text.split("\n").length;
  const here = t.text.slice(0, $("code").selectionStart).split("\n").length;
  const ask = await promptText("Go to line (1–" + lines + ")", String(here));
  if (!ask) return;
  const n = parseInt(ask, 10);
  if (!Number.isFinite(n) || n < 1 || n > lines) { say("That is not a line in this file", "err"); return; }
  const area = $("code");
  const pos = t.text.split("\n").slice(0, n - 1).reduce((a, l) => a + l.length + 1, 0);
  area.focus();
  area.setSelectionRange(pos, pos + (t.text.split("\n")[n - 1] || "").length);
  syncScroll();
  updateStatus();
}

// ---------------------------------------------------------------- pack order

async function loadOrder(refresh) {
  const report = await busy("Resolving pack order", () =>
    invoke("order_report", { iniPath: state.ini, addons: state.addons, refresh: !!refresh }));
  state.rows = report.rows;
  state.dirty = false;
  $("saveOrder").disabled = true;
  $("orderStats").textContent =
    `${report.rows.length} packs · ${report.alive} live · ${report.partial} partial · ` +
    `${report.dead} shadowed · ${report.unregistered} on disk but unregistered`;
  renderPacks();

  const box = $("moduleBox");
  box.innerHTML = "";
  box.appendChild(el("b", null, `lua.module load order (${report.modules.length})`));
  const list = el("ul");
  report.modules.forEach((m) => list.appendChild(el("li", null, m)));
  box.appendChild(list);
  say(`${report.rows.length} packs resolved: ${report.alive} live, ${report.partial} partial, ` +
      `${report.dead} fully shadowed.`, report.dead ? "" : "ok");
}

function visibleRows() {
  const q = $("packFilter").value.trim().toLowerCase();
  const hideAlt = $("hideAlt").checked;
  const onlyProblems = $("onlyProblems").checked;
  return state.rows
    .map((r, i) => ({ r, i }))
    .filter(({ r }) => {
      if (q && !r.value.toLowerCase().includes(q)) return false;
      if (hideAlt && r.alternative) return false;
      if (onlyProblems && !r.dead && r.surviving >= r.total) return false;
      return true;
    });
}

function renderPacks() {
  const body = $("packTable").querySelector("tbody");
  body.innerHTML = "";
  const rows = visibleRows();
  const cap = 1200;
  rows.slice(0, cap).forEach(({ r, i }) => {
    const tr = el("tr");
    tr.draggable = true;
    tr.dataset.index = String(i);
    tr.appendChild(el("td", "num", String(i + 1)));
    tr.appendChild(el("td", "grab", "⠿"));

    const name = el("td");
    name.appendChild(el("div", null, r.name));
    const small = el("div", "muted");
    small.textContent = r.value;
    small.style.fontSize = "11px";
    name.appendChild(small);
    tr.appendChild(name);

    const kind = el("td");
    kind.appendChild(el("span", "badge alt", r.kind));
    tr.appendChild(kind);

    tr.appendChild(el("td", "num", `${r.surviving}/${r.total}`));

    const status = el("td");
    if (!r.exists) status.appendChild(el("span", "badge missing", "missing"));
    else if (r.dead) status.appendChild(el("span", "badge dead", "shadowed"));
    else if (r.surviving < r.total) status.appendChild(el("span", "badge partial", "partial"));
    else status.appendChild(el("span", "badge live", "live"));
    tr.appendChild(status);

    const who = el("td", "muted");
    who.textContent = r.blockers.map((b) => `${b.keys} ← ${b.rel.split("\\").pop()}`).join(", ");
    tr.appendChild(who);

    body.appendChild(tr);
  });
  if (rows.length > cap) {
    const tr = el("tr");
    const td = el("td", "muted", `… ${rows.length - cap} more; narrow the filter to see them`);
    td.colSpan = 7;
    tr.appendChild(td);
    body.appendChild(tr);
  }
  attachDrag(body);
}

function attachDrag(body) {
  let from = null;
  body.querySelectorAll("tr").forEach((tr) => {
    tr.addEventListener("dragstart", (ev) => {
      from = Number(tr.dataset.index);
      tr.classList.add("dragging");
      ev.dataTransfer.effectAllowed = "move";
      ev.dataTransfer.setData("text/plain", String(from));
    });
    tr.addEventListener("dragend", () => {
      tr.classList.remove("dragging");
      body.querySelectorAll("tr").forEach((x) => x.classList.remove("dropbefore", "dropafter"));
    });
    tr.addEventListener("dragover", (ev) => {
      ev.preventDefault();
      const rect = tr.getBoundingClientRect();
      const after = ev.clientY > rect.top + rect.height / 2;
      tr.classList.toggle("dropafter", after);
      tr.classList.toggle("dropbefore", !after);
    });
    tr.addEventListener("dragleave", () => tr.classList.remove("dropbefore", "dropafter"));
    tr.addEventListener("drop", (ev) => {
      ev.preventDefault();
      const to = Number(tr.dataset.index);
      if (from === null || from === to) return;
      const rect = tr.getBoundingClientRect();
      const after = ev.clientY > rect.top + rect.height / 2;
      const moved = state.rows.splice(from, 1)[0];
      let target = to > from ? to - 1 : to;
      if (after) target += 1;
      state.rows.splice(target, 0, moved);
      state.dirty = true;
      $("saveOrder").disabled = false;
      renderPacks();
      say("Order changed locally — Save writes it to sider.ini (with a backup).");
    });
  });
}

let filterTimer = null;
$("packFilter").addEventListener("input", () => {
  clearTimeout(filterTimer);
  filterTimer = setTimeout(renderPacks, 120);
});
["hideAlt", "onlyProblems"].forEach((id) =>
  $(id).addEventListener("input", renderPacks));

$("autoSort").addEventListener("click", () => {
  // Specific packs first, base root last; ties keep their current position.
  const isBase = (v) => /^\.\\livecpk\\root$/i.test(v.trim());
  const indexed = state.rows.map((r, i) => ({ r, i }));
  indexed.sort((a, b) => {
    const ba = isBase(a.r.value), bb = isBase(b.r.value);
    if (ba !== bb) return ba ? 1 : -1;
    if (a.r.total !== b.r.total) return a.r.total - b.r.total;
    return a.i - b.i;
  });
  state.rows = indexed.map((x) => x.r);
  state.dirty = true;
  $("saveOrder").disabled = false;
  renderPacks();
  say("Auto-sorted: smallest packs first, base root last. Review, then Save.");
});

$("saveOrder").addEventListener("click", async () => {
  const values = state.rows.map((r) => r.value);
  const report = await busy("Writing sider.ini", () =>
    invoke("save_order", { iniPath: state.ini, addons: state.addons, values }));
  say(`Wrote ${report.entries} entries. Backup: ${report.backup}`, "ok");
  await loadOrder(true);
});

// ---------------------------------------------------------------- conflicts

$("pickConflictRoot").addEventListener("click", async () => {
  const dir = await pick({ directory: true, title: "Choose livecpk\\root" });
  if (dir) $("conflictRoot").value = dir;
});

$("runConflicts").addEventListener("click", async () => {
  const root = $("conflictRoot").value.trim();
  if (!root) return say("Choose a packs folder first.", "err");
  const r = await busy("Comparing pack contents", () => invoke("conflict_report", { root }));
  $("conflictStats").textContent = `${r.packs} packs · ${r.keys.toLocaleString()} distinct keys`;
  const cards = $("conflictSummary");
  cards.innerHTML = "";
  [["shared keys", r.shared], ["identical (harmless)", r.identical],
   ["genuinely differ", r.differing], ["conflicting pairs", r.pairs.length]].forEach(([l, n]) => {
    const c = el("div", "card");
    c.appendChild(el("div", "n", Number(n).toLocaleString()));
    c.appendChild(el("div", "l", l));
    cards.appendChild(c);
  });
  const body = $("conflictTable").querySelector("tbody");
  body.innerHTML = "";
  r.pairs.forEach((p) => {
    const tr = el("tr");
    tr.appendChild(el("td", "num", String(p.keys)));
    tr.appendChild(el("td", "path", p.a));
    tr.appendChild(el("td", "path", p.b));
    body.appendChild(tr);
  });
  const ex = $("conflictExamples");
  ex.innerHTML = "";
  if (r.examples.length) {
    ex.appendChild(el("b", null, "Example differing keys"));
    const ul = el("ul");
    r.examples.forEach((k) => ul.appendChild(el("li", null, k)));
    ex.appendChild(ul);
  }
  say(`${r.differing.toLocaleString()} keys genuinely differ across ${r.pairs.length} pairs.`, "ok");
});

// ---------------------------------------------------------------- cpk

$("pickCpk").addEventListener("click", async () => {
  const f = await pick({ title: "Choose a .cpk", filters: [{ name: "CPK", extensions: ["cpk"] }] });
  if (f) { $("cpkPath").value = f; openCpk(); }
});
$("openCpk").addEventListener("click", openCpk);
$("cpkFilter").addEventListener("input", renderCpk);

async function openCpk() {
  const archive = $("cpkPath").value.trim();
  if (!archive) return say("Choose a .cpk first.", "err");
  state.cpk = await busy("Reading " + archive, () => invoke("cpk_list", { archive }));
  $("extractCpk").disabled = false;
  $("cpkStats").textContent =
    `${state.cpk.entries.length} entries · ${(state.cpk.file_size / 1048576).toFixed(1)} MB · ` +
    `content at ${state.cpk.content_offset} · align ${state.cpk.align}`;
  renderCpk();
  say(`Opened ${archive}`, "ok");
}

function renderCpk() {
  if (!state.cpk) return;
  const q = $("cpkFilter").value.trim().toLowerCase();
  const body = $("cpkTable").querySelector("tbody");
  body.innerHTML = "";
  const list = state.cpk.entries.filter((e) => !q || e.path.toLowerCase().includes(q));
  list.slice(0, 2000).forEach((e) => {
    const tr = el("tr");
    tr.appendChild(el("td", "num", String(e.id)));
    tr.appendChild(el("td", "path", e.path));
    tr.appendChild(el("td", "num", e.size.toLocaleString()));
    tr.appendChild(el("td", "num", e.extract_size.toLocaleString()));
    const mode = el("td");
    mode.appendChild(el("span", "badge " + (e.compressed ? "partial" : "live"),
                        e.compressed ? "CRILAYLA" : "stored"));
    tr.appendChild(mode);
    body.appendChild(tr);
  });
  if (list.length > 2000) {
    const tr = el("tr");
    const td = el("td", "muted", `… ${list.length - 2000} more; use the filter`);
    td.colSpan = 5;
    tr.appendChild(td);
    body.appendChild(tr);
  }
}

$("extractCpk").addEventListener("click", async () => {
  const dest = await pick({ directory: true, title: "Extract into…" });
  if (!dest) return;
  const filter = $("cpkFilter").value.trim() || null;
  const n = await busy("Extracting", () =>
    invoke("cpk_extract", { archive: state.cpk.archive, dest, filter }));
  say(`Extracted ${n} files to ${dest}`, "ok");
});

$("pickPackSrc").addEventListener("click", async () => {
  const dir = await pick({ directory: true, title: "Folder to pack" });
  if (dir) $("packSrc").value = dir;
});

$("buildCpk").addEventListener("click", async () => {
  const src = $("packSrc").value.trim();
  if (!src) return say("Choose a folder to pack.", "err");
  const dest = await dialog.save({
    title: "Save CPK as…",
    defaultPath: "mod.cpk",
    filters: [{ name: "CPK", extensions: ["cpk"] }],
  });
  if (!dest) return;
  const r = await busy("Building CPK", () => invoke("cpk_pack", { src, dest }));
  say(`Packed ${r.files} files (${(r.bytes / 1048576).toFixed(1)} MB): ` +
      `${r.packed} CRILAYLA, ${r.stored} stored; re-read ${r.reread} entries.`, "ok");
  $("cpkPath").value = dest;
  await openCpk();
});

// ---------------------------------------------------------------- textures

$("pickTex").addEventListener("click", async () => {
  const f = await pick({ title: "Choose a texture", filters: [{ name: "Textures", extensions: ["ftex", "dds"] }] });
  if (f) { $("texPath").value = f; openTex(); }
});
$("openTex").addEventListener("click", openTex);
$("mipLevel").addEventListener("change", () => previewTex());

async function openTex() {
  const path = $("texPath").value.trim();
  if (!path) return say("Choose a texture first.", "err");
  if (!/\.ftex$/i.test(path)) {
    say("Preview needs a .ftex; use Convert folder for .dds input.", "err");
    return;
  }
  const info = await busy("Decoding texture", () => invoke("tex_info", { path }));
  state.tex = info;
  $("texToDds").disabled = false;
  const panel = $("texInfo");
  panel.innerHTML = "";
  panel.appendChild(el("b", null, path.split(/[\\/]/).pop()));
  const ul = el("ul");
  [["size", `${info.width} × ${info.height}${info.depth > 1 ? " × " + info.depth : ""}`],
   ["format", info.format], ["mips", info.mips],
   ["type", { 1: "material (SRM)", 3: "diffuse (BSM)", 7: "cube (CBM)", 9: "normal (NRM)" }[info.texture_type] || info.texture_type],
   ["ftex version", info.version],
   ["decoded bytes", info.bytes.toLocaleString()]].forEach(([k, v]) =>
    ul.appendChild(el("li", null, `${k}: ${v}`)));
  panel.appendChild(ul);

  const sel = $("mipLevel");
  sel.innerHTML = "";
  for (let i = 0; i < info.mips; i++) {
    sel.appendChild(new Option(`mip ${i} — ${Math.max(1, info.width >> i)}×${Math.max(1, info.height >> i)}`, String(i)));
  }
  await previewTex();
  say(`${info.width}×${info.height} ${info.format}, ${info.mips} mips.`, "ok");
}

async function previewTex() {
  if (!state.tex) return;
  const level = Number($("mipLevel").value || 0);
  const url = await busy("Rendering preview", () =>
    invoke("tex_preview", { path: state.tex.path, level }));
  $("texImg").src = url;
}

$("texToDds").addEventListener("click", async () => {
  const dest = await dialog.save({
    title: "Save DDS as…",
    defaultPath: state.tex.path.split(/[\\/]/).pop().replace(/\.ftex$/i, ".dds"),
    filters: [{ name: "DDS", extensions: ["dds"] }],
  });
  if (!dest) return;
  const rows = await busy("Converting", () =>
    invoke("tex_convert", { input: state.tex.path, out: parentOf(dest), kind: "diffuse" }));
  renderTexRows(rows);
});

function parentOf(p) {
  const i = Math.max(p.lastIndexOf("\\"), p.lastIndexOf("/"));
  return i > 0 ? p.slice(0, i) : ".";
}

function renderTexRows(rows) {
  const body = $("texTable").querySelector("tbody");
  body.innerHTML = "";
  rows.slice(0, 400).forEach((r) => {
    const tr = el("tr");
    tr.appendChild(el("td", "path", r.file));
    const td = el("td");
    td.appendChild(el("span", "badge " + (r.ok ? "live" : "dead"), r.ok ? "ok" : "failed"));
    td.appendChild(document.createTextNode(" " + r.detail));
    tr.appendChild(td);
    body.appendChild(tr);
  });
  const bad = rows.filter((r) => !r.ok).length;
  say(`Converted ${rows.length - bad}/${rows.length} textures.`, bad ? "err" : "ok");
}

$("pickTexBatch").addEventListener("click", async () => {
  const dir = await pick({ directory: true, title: "Folder of textures" });
  if (dir) $("texBatch").value = dir;
});

$("runTexBatch").addEventListener("click", async () => {
  const input = $("texBatch").value.trim();
  if (!input) return say("Choose a folder to convert.", "err");
  const out = await pick({ directory: true, title: "Output folder" });
  if (!out) return;
  const rows = await busy("Converting folder", () =>
    invoke("tex_convert", { input, out, kind: $("texKind").value }));
  renderTexRows(rows);
});

// ---------------------------------------------------------------- tables

$("pickTableDir").addEventListener("click", async () => {
  const dir = await pick({ directory: true, title: "Folder to scan" });
  if (dir) $("tableDir").value = dir;
});

function tableRow(file, framing, fileSize, bodySize, reencode, verdict, ok) {
  const tr = el("tr");
  tr.appendChild(el("td", "path", file));
  tr.appendChild(el("td", null, framing));
  tr.appendChild(el("td", "num", fileSize.toLocaleString()));
  tr.appendChild(el("td", "num", bodySize.toLocaleString()));
  tr.appendChild(el("td", null, reencode));
  const td = el("td");
  td.appendChild(el("span", "badge " + (ok ? "live" : "dead"), verdict));
  tr.appendChild(td);
  return tr;
}

$("runTables").addEventListener("click", async () => {
  const dir = $("tableDir").value.trim();
  if (!dir) return say("Choose a folder to scan.", "err");
  const rows = await busy("Validating tables", () => invoke("pesdb_report", { dir }));
  const body = $("tableTable").querySelector("tbody");
  body.innerHTML = "";
  rows.forEach((r) => {
    const tr = tableRow(r.file, "pesdb", 0, 0, "-", r.reason, r.ok);
    if (!r.ok && r.status === "unrecognised") {
      const badge = tr.querySelector(".badge");
      badge.className = "badge partial";
      badge.textContent = "unrecognised";
    }
    body.appendChild(tr);
  });
  const bad = rows.filter((r) => !r.ok && r.status !== "unrecognised").length;
  const opaque = rows.filter((r) => r.status === "unrecognised").length;
  $("tableStats").textContent =
    `${rows.length} tables · ${rows.length - bad - opaque} valid · ${bad} invalid · ${opaque} unreadable`;
  say(bad ? `${bad} table(s) have a measured defect and would corrupt the game.`
          : (opaque ? `${opaque} file(s) are not readable tables; their layout cannot be checked.`
                    : "All tables validate."),
      bad ? "err" : "ok");
});

$("pickContainer").addEventListener("click", async () => {
  const f = await pick({ title: "Choose a file (or cancel and type a folder)" });
  if (f) $("containerPath").value = f;
});

$("runContainer").addEventListener("click", async () => {
  const input = $("containerPath").value.trim();
  if (!input) return say("Choose a file or folder.", "err");
  const rows = await busy("Inspecting framing", () => invoke("container_report", { input }));
  const body = $("tableTable").querySelector("tbody");
  body.innerHTML = "";
  rows.slice(0, 800).forEach((r) => body.appendChild(tableRow(
    r.file, r.framing, r.file_size, r.body_size,
    r.error ? "refused" : (r.exact ? "byte-exact" : `re-emit (level ${r.level})`),
    r.error || (r.exact ? "exact" : "same table"),
    !r.error)));
  $("unwrapBtn").disabled = rows.length !== 1;
  $("rewrapBtn").disabled = rows.length !== 1;
  state.containerInput = input;
  const bad = rows.filter((r) => r.error).length;
  $("tableStats").textContent = `${rows.length} files · ${rows.filter((r) => r.exact).length} byte-exact · ${bad} refused`;
  say(`Inspected ${rows.length} file(s).`, bad ? "err" : "ok");
});

$("unwrapBtn").addEventListener("click", async () => {
  const dest = await dialog.save({ title: "Write unwrapped body as…", defaultPath: "body.bin" });
  if (!dest) return;
  const n = await busy("Unwrapping", () =>
    invoke("container_unwrap", { input: state.containerInput, dest }));
  say(`Wrote ${n.toLocaleString()} raw bytes to ${dest}`, "ok");
});

$("rewrapBtn").addEventListener("click", async () => {
  const body = await pick({ title: "Choose the edited body" });
  if (!body) return;
  const dest = await dialog.save({ title: "Write re-wrapped file as…", defaultPath: "patched.bin" });
  if (!dest) return;
  const r = await busy("Re-wrapping", () =>
    invoke("container_rewrap", { body, original: state.containerInput, dest }));
  say(`${r.framing}, ${r.file_size} bytes — ${r.exact ? "byte-exact" : "same table, new deflate"}.`, "ok");
});

// ---------------------------------------------------------------- bin reader

let binReport = null;

$("pickBin").addEventListener("click", async () => {
  const f = await pick({ title: "Choose a .bin", filters: [{ name: "Tables", extensions: ["bin"] }] });
  if (f) { $("binPath").value = f; runBin(); }
});
$("runBin").addEventListener("click", runBin);

async function runBin() {
  const file = $("binPath").value.trim();
  if (!file) return say("Choose a .bin first.", "err");
  binReport = await busy("Decoding " + file, () => invoke("bin_read", { file }));
  $("binStats").textContent =
    `${binReport.framing} · body ${binReport.body_size.toLocaleString()} B · ` +
    `entropy ${binReport.entropy.toFixed(2)} b/B`;
  say(`${binReport.re_encode}.`, binReport.framing === "unknown" ? "err" : "ok");

  const notes = $("binNotes");
  notes.innerHTML = "";
  notes.appendChild(finding("info", binReport.re_encode,
    "Whether re-writing this file reproduces the original bytes."));
  binReport.notes.forEach((n) => notes.appendChild(finding("warn", n, "")));

  renderSections();
  renderRecords();
  renderStructure();
  renderStrings();
  showHex("body head", () => invoke("bin_hex", { file: binReport.path, at: 0, bytes: 512 }));
}

function finding(kind, title, detail) {
  const d = el("div", "finding " + kind);
  d.appendChild(el("b", null, title));
  if (detail) d.appendChild(el("span", null, detail));
  return d;
}

function renderSections() {
  const body = $("binSections").querySelector("tbody");
  body.innerHTML = "";
  const t = binReport.sections;
  if (!t) {
    const tr = el("tr");
    const td = el("td", "muted", "not a match constant — no section table");
    td.colSpan = 4;
    tr.appendChild(td);
    body.appendChild(tr);
    return;
  }
  t.sections.forEach((s, i) => {
    const tr = el("tr");
    tr.appendChild(el("td", "num", String(i)));
    tr.appendChild(el("td", null, s.name));
    tr.appendChild(el("td", "num", s.offset.toLocaleString()));
    tr.appendChild(el("td", "num", s.size.toLocaleString()));
    tr.addEventListener("click", () => showSection(i, s.name));
    body.appendChild(tr);
  });
}

function renderRecords() {
  const wrap = $("binRecords");
  wrap.innerHTML = "";
  const r = binReport.records;
  if (!r) {
    wrap.appendChild(el("div", "muted",
      binReport.framing === "unknown"
        ? "no record count is claimed: the stride of a table cannot be checked against ciphertext"
        : "no field map is claimed for this table"));
    return;
  }
  wrap.appendChild(el("div", "muted",
    `${r.records.toLocaleString()} records at stride ${r.stride} — ${r.note}`));
  if (!r.columns.length) return;
  const table = el("table");
  const hr = el("tr");
  hr.appendChild(el("th", "num", "#"));
  r.columns.forEach((c) => hr.appendChild(el("th", null, c.name)));
  const head = el("thead");
  head.appendChild(hr);
  table.appendChild(head);
  const body = el("tbody");
  const rows = Math.min(r.records, 300);
  for (let i = 0; i < rows; i++) {
    const tr = el("tr");
    tr.appendChild(el("td", "num", String(i)));
    r.columns.forEach((c) => tr.appendChild(el("td", null, c.values[i])));
    body.appendChild(tr);
  }
  table.appendChild(body);
  wrap.appendChild(table);
  if (r.records > rows) {
    wrap.appendChild(el("div", "muted", `showing ${rows} of ${r.records.toLocaleString()}`));
  }
}

function renderStrings() {
  const box = $("binStrings");
  box.innerHTML = "";
  if (!binReport.strings.length) {
    box.appendChild(el("span", "muted", "no printable runs of 5 bytes or more"));
    return;
  }
  const ul = el("ul");
  binReport.strings.slice(0, 120).forEach((s) => {
    const li = el("li");
    li.appendChild(el("span", "muted", `@${s.at.toLocaleString()}  `));
    li.appendChild(document.createTextNode(s.text));
    ul.appendChild(li);
  });
  box.appendChild(ul);
}

async function showHex(what, fn) {
  $("hexLabel").textContent = what ? "— " + what : "";
  $("binHex").textContent = "reading…";
  try {
    $("binHex").textContent = await fn();
  } catch (err) {
    $("binHex").textContent = String(err);
  }
}

function renderStructure() {
  const body = $("binStructure").querySelector("tbody");
  body.innerHTML = "";
  const st = binReport.structure;
  if (!st) {
    $("structureNote").textContent = "— nothing inferred";
    const tr = el("tr");
    const td = el("td", "muted",
      binReport.framing === "unknown"
        ? "the bytes are opaque; no layout is claimed"
        : "no stride explains these bytes as a record array");
    td.colSpan = 5;
    tr.appendChild(td);
    body.appendChild(tr);
    return;
  }
  $("structureNote").textContent =
    `— ${st.mapped_bytes} of ${st.stride} bytes explained` +
    (st.sub_record ? `, sub-record ${st.sub_record}` : "");
  st.fields.forEach((f) => {
    const tr = el("tr");
    tr.appendChild(el("td", "num", "+" + f.offset));
    tr.appendChild(el("td", "num", String(f.width)));
    const kind = el("td");
    const cls = f.kind === "text" || f.kind === "float" || f.kind === "id" ? "live"
      : f.kind === "mixed" ? "dead" : "partial";
    kind.appendChild(el("span", "badge " + cls, f.kind));
    tr.appendChild(kind);
    tr.appendChild(el("td", "num", `${f.supporting}/${f.records}`));
    tr.appendChild(el("td", "path", f.sample));
    body.appendChild(tr);
  });
}

async function showSectionTable(index, name) {
  $("tableLabel").textContent = "— " + name;
  const wrap = $("binTable");
  wrap.innerHTML = "";
  const t = await busy("Reading the parameter table", () =>
    invoke("bin_section_table", { file: binReport.path, index }));
  if (!t.table) {
    wrap.appendChild(el("div", "muted",
      `not a float parameter table (${t.bytes} bytes, ` +
      `${t.plausible_floats} plausible float slots)`));
    return;
  }
  const [rows, rowBytes] = t.table;
  const cols = rowBytes / 4;
  wrap.appendChild(el("div", "muted",
    `${rows.toLocaleString()} rows × ${rowBytes} bytes` +
    (cols === 1 ? " — one value per row" : ` — ${cols} values per row`) +
    `, showing the first ${t.values.length.toLocaleString()} values`));
  const table = el("table");
  const body = el("tbody");
  for (let r = 0; r < Math.min(rows, 40); r++) {
    const tr = el("tr");
    tr.appendChild(el("td", "num", String(r)));
    for (let c = 0; c < cols && r * cols + c < t.values.length; c++) {
      tr.appendChild(el("td", "num", t.values[r * cols + c].toFixed(4)));
    }
    body.appendChild(tr);
  }
  table.appendChild(body);
  wrap.appendChild(table);
}

function showSection(index, name) {
  showHex(name, () => invoke("bin_section", {
    file: binReport.path, index, bytes: 512 }));
  showSectionTable(index, name);
}


function initStudio() {
  invoke("studio_kinds").then((kinds) => {
    studio.kinds = kinds;
    const sel = $("packKind");
    sel.innerHTML = "";
    kinds.forEach((k) => {
      const o = document.createElement("option");
      o.value = k.kind;
      o.textContent = k.kind + " — " + k.hint;
      sel.appendChild(o);
    });
    sel.value = "cpk";
    showKindHint();
  });
  $("packKind").addEventListener("change", showKindHint);
  $("pickStudioRoot").addEventListener("click", async () => {
    const dir = await pick({ directory: true });
    if (dir) { $("studioRoot").value = dir.replace(/\\/g, "/"); loadStudio(); }
  });
  $("refreshTree").addEventListener("click", loadStudio);
  $("studioRoot").addEventListener("keydown", (ev) => { if (ev.key === "Enter") loadStudio(); });
  $("newPack").addEventListener("click", doNewPack);
  $("checkPack").addEventListener("click", doCheckPack);
  $("installPack").addEventListener("click", doInstall);
  $("togglePacks").addEventListener("click", () => {
    if ($("packPanel").hidden) loadEntries();
    else $("packPanel").hidden = true;
  });
  $("reloadEntries").addEventListener("click", loadEntries);
  $("newFile").addEventListener("click", newFile);
  $("renameSel").addEventListener("click", renameSel);
  $("deleteSel").addEventListener("click", deleteSel);
  $("revealSel").addEventListener("click", revealSel);

  const area = $("code");
  area.addEventListener("input", onEdit);
  area.addEventListener("scroll", syncScroll);
  area.addEventListener("keydown", (ev) => {
    if (ev.ctrlKey && ev.key.toLowerCase() === "s") { ev.preventDefault(); saveActive(); }
    if (ev.ctrlKey && ev.key.toLowerCase() === "g") { ev.preventDefault(); gotoLine(); }
    if (ev.ctrlKey && ev.key.toLowerCase() === "f") {
      ev.preventDefault();
      $("findBar").hidden = false;
      $("findText").focus();
      if (area.selectionStart !== area.selectionEnd) {
        $("findText").value = area.value.slice(area.selectionStart, area.selectionEnd);
        findStep(false);
      }
    }
    if (ev.ctrlKey && ev.key.toLowerCase() === "w") { ev.preventDefault(); closeTab(studio.active); }
    if (ev.key === "Tab") { handleIndent(ev, ev.shiftKey); }
    if (ev.key === "Enter" && !ev.ctrlKey) { handleEnter(ev); }
    if (ev.key === "Escape") $("findBar").hidden = true;
  });
  ["click", "keyup", "input"].forEach((ev) =>
    area.addEventListener(ev, updateStatus));
  $("findText").addEventListener("keydown", (ev) => { if (ev.key === "Enter") findStep(ev.shiftKey); });
  $("findNext").addEventListener("click", () => findStep(false));
  $("findPrev").addEventListener("click", () => findStep(true));
  $("replOne").addEventListener("click", replaceOne);
  $("replAll").addEventListener("click", replaceAll);
}

async function boot() {
  const restoreTab = () => {
    // Back where the user left the app, rather than always on Game map. This
    // used to be skipped whenever detection found nothing, so the app also
    // forgot the tab on top of forgetting the install.
    try {
      const last = localStorage.getItem("fl27mm.tab");
      const btn = last && document.querySelector(`[data-tab="${last}"]`);
      if (btn && last !== "map") btn.click();
    } catch (err) {}
  };
  try {
    const remembered = rememberedInstalls();
    const found = await invoke("detect_game", { remembered });
    const sel = $("install");
    sel.innerHTML = "";
    if (!found.length) {
      sel.appendChild(new Option("No install detected", ""));
      say("No Sider install found automatically — browse to your game folder.", "err");
      restoreTab();
      return;
    }
    found.forEach((f, i) => sel.appendChild(new Option(f.game, String(i))));
    sel.onchange = () => {
      setInstall(found[Number(sel.value)]);
      rescan();
    };
    // A folder the user picked beats the name match: they chose it, so it is
    // the one they mean, even when another install also has "football life"
    // in its path.
    const last = remembered.length ? remembered[remembered.length - 1].toLowerCase() : "";
    let idx = found.findIndex((f) => f.game.toLowerCase() === last);
    if (idx < 0) idx = found.findIndex((f) => /football life 2027/i.test(f.game));
    sel.value = String(idx >= 0 ? idx : 0);
    setInstall(found[Number(sel.value)]);
    await rescan();
    restoreTab();
  } catch (err) {
    say(String(err), "err");
  }
}

$("pickGame").addEventListener("click", async () => {
  const dir = await pick({ directory: true, title: "Choose the game folder" });
  if (!dir) return;
  setInstall(installFromPath(dir));
  rescan();
});

$("rescan").addEventListener("click", () => rescan());

async function rescan() {
  const typed = $("gamePath").value.trim();
  if (typed && typed !== state.game) setInstall(installFromPath(typed));
  if (!state.game) {
    say("Choose a game folder first.", "err");
    return;
  }
  const report = await busy("Scanning " + state.ini, () => invoke("scan", { game: state.game }));
  const health = $("health");
  health.innerHTML = "";
  const line = (label, value, cls) => {
    const d = el("div");
    d.appendChild(el("span", null, label + " "));
    d.appendChild(el("b", cls, String(value)));
    health.appendChild(d);
  };
  line("packs", report.packs);
  line("modules", report.modules);
  line("disabled", report.disabled_packs + report.disabled_modules);
  line("missing", report.missing.length, report.missing.length ? "bad" : "");
  line("duplicates", report.duplicates.length, report.duplicates.length ? "bad" : "");
  if (!report.lua_enabled || !report.luajit_enabled) {
    line("lua", "off", "bad");
  }
  if (report.missing.length || report.duplicates.length) {
    say([...report.missing, ...report.duplicates].slice(0, 3).join(" · "), "err");
  } else {
    say(`${report.packs} packs and ${report.modules} modules resolve cleanly.`, "ok");
  }
  Object.keys(loaded).forEach((k) => delete loaded[k]);
  const active = document.querySelector(".tabs button.active");
  if (active) showTab(active.dataset.tab);
}



// Writing into a shipped table has to be exact or it is not safe, so the core
// re-reads the file after patching and refuses if any byte outside the
// requested window moved. Offsets here are body offsets, matching the decoded
// view above rather than the compressed bytes on disk.
async function patchBin() {
  const box = $("binPatch");
  const file = box.dataset.path || $("binPath").value.trim();
  if (!file) return say("Choose a .bin first.", "err");
  const off = parseInt($("binOffset").value.trim(), 10);
  const hex = $("binHex").value.trim().replace(/\s+/g, "");
  if (!Number.isInteger(off) || off < 0) return say("Offset must be a number.", "err");
  if (!hex || hex.length % 2 || !/^[0-9a-fA-F]+$/.test(hex)) {
    return say("Bytes must be an even number of hex digits.", "err");
  }
  const yes = await dialog.ask("Patch a shipped table in place? A backup is written beside it on the first patch.", { title: "Patch table" });
  if (!yes) return;
  try {
    const r = await busy("Patching", () => invoke("bin_patch", { file, offset: off, hex }));
    say(`Patched ${r.changed} byte(s); body is ${r.size.toLocaleString()} B. Backup: ${r.backup}`, "ok");
    await runBin();
  } catch (err) {
    say(String(err), "err");
  }
}


// ---------------------------------------------------------------- assets
//
// One browser for every editable image asset. Families come from the path in
// the core, so the list cannot disagree with what the editor will accept.
// Replacing a texture hands raw RGBA to the core, which refuses a size that
// does not match the file and re-reads the result before reporting success.
const assets = { items: [], sel: null, family: "" };

async function assetScan() {
  const root = $("assetRoot").value.trim();
  if (!root) return say("Choose a folder first.", "err");
  const r = await busy("Listing assets", () => invoke("asset_list", { root, limit: 600 }));
  assets.items = r.items;
  const sel = $("assetFamily");
  const seen = [...new Set(r.items.map((i) => i.family))].sort();
  sel.innerHTML = '<option value="">all families</option>' + seen.map((f) => `<option>${f}</option>`).join("");
  $("assetCount").textContent = `${r.shown} of a ${r.cap}-item scan`;
  renderAssets();
  // Say what the scan actually found. A blanket disclaimer made every folder,
  // including a head with no animation in it, claim that animations were
  // unsolved, which was both wrong and noise.
  const anims = assets.items.filter((i) => i.family === "animations");
  $("assetNote").textContent = anims.length
    ? `${anims.length} animation clip(s). Select one and use the panel below to decode its tracks and edit keyframes.`
    : "";
}

function renderAssets() {
  const box = $("assetList");
  box.innerHTML = "";
  const f = $("assetFamily").value;
  const rows = assets.items.filter((i) => !f || i.family === f);
  rows.slice(0, 300).forEach((i) => {
    const d = el("div", "tnode" + (assets.sel === i.path ? " on" : ""), "");
    d.appendChild(el("span", null, baseName(i.path)));
    d.appendChild(el("span", "muted", `  ${i.family} · ${i.format} · ${i.width}x${i.height}` + (i.editable ? "" : " · read-only")));
    d.onclick = () => { assets.sel = i.path; renderAssets(); assetShow(i); };
    box.appendChild(d);
  });
  if (!rows.length) box.appendChild(el("div", "muted", "nothing here yet"));
}

function assetShow(i) {
  const pane = $("assetPane");
  pane.innerHTML = "";
  // Selecting a clip loads it into the animation panel, so the list and the
  // decoder cannot drift apart on which file is being looked at.
  if (i.family === "animations") $("ganiPath").value = i.path;
  if (i.family === "faces" || i.family === "hair" || i.family === "kits" || i.family === "boots" || i.family === "balls") {
    $("assetRender").disabled = false;
  }
  try {
    const img = new Image();
    img.src = "";
    pane.appendChild(el("div", "muted", `${i.path} — ${i.format}, ${i.width}x${i.height}, ${fmtSize(i.bytes)}`));
  } catch (e) { /* the list line already carries the facts */ }
}

async function assetRender() {
  const root = $("assetRoot").value.trim();
  if (!root) return say("Choose a folder first.", "err");
  const r = await busy("Rendering", () => invoke("asset_preview", { model: root, view: $("assetView").value, size: 512 }));
  const pane = $("assetPane");
  pane.innerHTML = "";
  const img = document.createElement("img");
  img.src = r.image;
  pane.appendChild(img);
  pane.appendChild(el("div", "muted", `${r.files} files · ${r.meshes} meshes · ${r.vertices.toLocaleString()} verts · ${r.maps}`));
}

async function assetReplace() {
  if (!assets.sel) return say("Pick an asset on the left first.", "warn");
  const f = await pick({ title: "Choose an image the same size as the asset" });
  if (!f) return;
  const img = new Image();
  img.src = "asset://localhost/" + f;
  await new Promise((res, rej) => { img.onload = res; img.onerror = () => rej(new Error("the image could not be decoded")); });
  const c = document.createElement("canvas");
  c.width = img.naturalWidth; c.height = img.naturalHeight;
  const ctx = c.getContext("2d");
  ctx.drawImage(img, 0, 0);
  const d = ctx.getImageData(0, 0, c.width, c.height);
  const yes = await dialog.ask(`Replace ${baseName(assets.sel)}? A backup is kept beside it.`, { title: "Replace texture" });
  if (!yes) return;
  try {
    const r = await busy("Re-encoding", () => invoke("asset_replace", {
      file: assets.sel, width: c.width, height: c.height, bytes: Array.from(d.data),
    }));
    say(`Wrote ${r.width}x${r.height} ${r.format} with ${r.mips} mips; ${r.changed_pixels} px differ from the input within block tolerance. Backup: ${r.backup}`, "ok");
  } catch (err) {
    say(String(err), "err");
  }
}


// ---------------------------------------------------------------- animations
//
// A .gani clip is decoded by walking its track data and proving the keyframe
// blobs tile without overlap. That check happens in the core, so a clip that
// does not decode comes back as an error rather than as plausible nonsense.
const ganiState = { path: "", unit: 0, segment: 0 };

async function ganiDecode() {
  const p = $("ganiPath").value.trim();
  if (!p) return say("Give a .gani file first.", "err");
  let r;
  try {
    r = await busy("Decoding animation", () => invoke("gani_read", { path: p }));
  } catch (err) {
    $("ganiSummary").textContent = "";
    $("ganiTracks").textContent = "";
    return say(String(err), "err");
  }
  ganiState.path = p;
  $("ganiSummary").textContent =
    `${r.units} units · ${r.segments} segments · ${r.frames} frames at ${r.rate} fps` +
    (r.staleSize ? " · header size field is stale, the clip still decodes" : "");
  $("ganiRate").value = r.rate;
  const box = $("ganiTracks");
  box.innerHTML = "";
  r.tracks.forEach((u) => {
    box.appendChild(el("div", "gani-unit", `unit ${u.index}  name ${u.name}  ` +
      (u.static ? "static " : "") + (u.loops ? "loop" : "")));
    u.segments.forEach((s, si) => {
      const row = el("div", "gani-seg", "");
      row.appendChild(el("span", "gani-kind", `${s.kind} ${s.bits}-bit`));
      row.appendChild(el("span", "muted", ` seg ${s.id} · ${s.keys} keys · bytes ${s.bytes[0]}..${s.bytes[1]}`));
      row.appendChild(el("div", "gani-keys", `first ${s.first || "-"}   last ${s.last || "-"}`));
      // Choosing a row sets what "Write key" edits, so the target is always
      // the thing on screen rather than a pair of numbers typed elsewhere.
      row.onclick = () => {
        ganiState.unit = u.index;
        ganiState.segment = si;
        box.querySelectorAll(".gani-seg.on").forEach((n) => n.classList.remove("on"));
        row.classList.add("on");
        $("ganiKey").max = String(Math.max(0, s.keys - 1));
        say(`Editing unit ${u.index}, segment ${si} (${s.kind} ${s.bits}-bit, ${s.keys} keys).`, "ok");
      };
      box.appendChild(row);
    });
  });
  say(`Decoded ${r.tracks.length} units from ${p}. Click a track to edit it.`, "ok");
}

async function ganiWriteKey() {
  if (!ganiState.path) return say("Decode a clip first.", "err");
  const key = Number($("ganiKey").value);
  const parts = $("ganiParts").value.split(",").map((x) => Number(x.trim()));
  const signs = $("ganiSigns").value.split(",").map((x) => Number(x.trim()) !== 0);
  if (parts.length !== 3 || signs.length !== 3) return say("Three components and three signs are required.", "err");
  if (parts.some((x) => !Number.isInteger(x) || x < 0)) return say("Components must be whole numbers.", "err");
  const yes = await dialog.ask(
    `Write key ${key} of unit ${ganiState.unit} segment ${ganiState.segment} as (${parts.join(", ")}) signs (${signs.map((s) => (s ? 1 : 0)).join(", ")})?`,
    { title: "Edit keyframe" });
  if (!yes) return;
  try {
    const r = await busy("Writing", () => invoke("gani_set_key", {
      path: ganiState.path, unit: ganiState.unit, segment: ganiState.segment, key, parts, signs,
    }));
    say(`Written and verified. Read back: ${r.readBack}. The file was re-walked and no other byte moved.`, "ok");
    await ganiDecode();
  } catch (err) {
    say(String(err), "err");
  }
}

$("ganiRead").addEventListener("click", ganiDecode);
$("ganiRateSet").addEventListener("click", ganiSetRate);
$("ganiKeySet").addEventListener("click", ganiWriteKey);

// A skeleton says which bones exist; a rig says which animation channel drives
// which of them. Showing them next to the clip is the only way to see whether a
// clip and a rig actually agree, which is the check that catches an animation
// aimed at the wrong skeleton.
async function rigRead() {
  const p = $("rigPath").value.trim();
  if (!p) return say("Give a .ask or .frig file first.", "err");
  let r;
  try {
    r = await busy("Reading rig", () => invoke("rig_read", { path: p }));
  } catch (err) {
    $("rigSummary").textContent = "";
    $("rigOut").textContent = "";
    return say(String(err), "err");
  }
  const box = $("rigOut");
  box.innerHTML = "";
  if (r.kind === "skeleton") {
    $("rigSummary").textContent =
      `skeleton: ${r.bones.length} bones, ${r.basis} basis, ${r.reachable} reachable from the root`;
    r.bones.forEach((b, i) => {
      const row = el("div", "gani-seg", "");
      row.appendChild(el("span", "gani-kind", `${i} ${b.name}`));
      row.appendChild(el("span", "muted",
        ` parent ${b.parent}  pos (${b.position.map((x) => x.toFixed(4)).join(", ")})`));
      box.appendChild(row);
    });
    if (r.basis === "render") {
      say("This is a render-basis skeleton: animation rotations must not be applied straight onto these rest rotations.", "warn");
    }
  } else {
    $("rigSummary").textContent = `rig ${r.name}: ${r.units} units, ${r.segments} segments`;
    r.unitList.forEach((u, i) => {
      const row = el("div", "gani-seg", "");
      row.appendChild(el("span", "gani-kind", `${i} ${u.type}`));
      // Only the direct types name a bone. Chains resolve theirs through an IK
      // solver, and saying so is the useful part: it is why a naive player
      // leaves the arms and thighs frozen while the trunk moves.
      const detail = u.direct && u.bone
        ? ` bone ${u.bone}`
        : u.direct
          ? ` bone index ${u.boneIndex} (no skeleton beside the rig)`
          : ` chain over ${u.bones} bones, ${u.tracks} tracks (no direct bone)`;
      row.appendChild(el("span", "muted", detail));
      box.appendChild(row);
    });
    if (!r.skeleton) {
      say("Rig read. Put the matching .ask skeleton beside it to resolve unit bone indices to names.", "warn");
    }
  }
  say(`Read ${p}.`, "ok");
}

$("rigRead").addEventListener("click", rigRead);

async function ganiSetRate() {
  const p = $("ganiPath").value.trim();
  const rate = Number($("ganiRate").value);
  if (!p) return say("Give a .gani file first.", "err");
  if (!rate) return say("Enter a frame rate.", "err");
  const yes = await dialog.ask(`Set the frame rate of ${baseName(p)} to ${rate} fps?`, { title: "Edit animation" });
  if (!yes) return;
  try {
    const r = await busy("Writing", () => invoke("gani_rate", { path: p, rate }));
    say(`Frame rate ${r.was} -> ${r.now}; the file was re-read and only the rate byte changed.`, "ok");
    await ganiDecode();
  } catch (err) {
    say(String(err), "err");
  }
}

// ---------------------------------------------------------------- menu maker
//
// A menu set only ships part of the game's screens, so a link that points
// outside the folder is usually resolved by the base layer rather than broken.
// Checking without the base produced 344 "broken" links on a real set where 6
// were real, which is why the base field is required before the report means
// anything.
const menu = { sel: null, entries: [], broken: [], unreachable: [] };

async function menuCheck() {
  const root = $("menuRoot").value.trim();
  const base = $("menuBase").value.trim();
  if (!root) return say("Choose a menu set folder first.", "err");
  if (!base) return say("Choose the base layer too; without it almost every link looks dead.", "warn");
  let r;
  try {
    r = await busy("Checking navigation", () => invoke("menu_check", { root, bases: [base] }));
  } catch (err) {
    return say(String(err), "err");
  }
  menu.entries = r.entries;
  menu.broken = r.broken || [];
  menu.unreachable = r.unreachable || [];
  menu.groups = r.groups || [];
  $("menuCount").textContent = `${r.screens} screens · ${r.links} links`;
  const box = $("menuFindings");
  box.innerHTML = "";
  if (r.clean) {
    box.appendChild(finding("ok", "every link resolves", "no dead buttons in this set"));
  } else {
    r.broken.forEach((b) => box.appendChild(finding(
      "err", `${b.screen} · ${b.event} -> ${b.target}`, b.why)));
  }
  if (r.unreachable.length) {
    box.appendChild(finding("warn", `${r.unreachable.length} screens nothing points at`,
      "informational: a screen can be opened by the engine directly"));
  }
  renderMenuList();
  renderMenuGraph();
}

// The navigation graph. Screens are placed by how deep they sit from the
// entry screens, so the shape of the flow is the layout instead of a name
// list the reader has to reconstruct; that is the one thing a table of
// screens cannot show, which is where a dead button or an orphan actually
// becomes visible.
// The navigation graph.
//
// Two axes carry meaning: horizontal is how deep a screen sits from an entry
// point, vertical is which group it belongs to. Groups get contiguous lanes so
// a set reads as the folders it actually has rather than as a hairball, and
// within a lane screens are ordered to reduce edge crossings, which is the one
// thing that makes a hand-placed graph look designed and a naive one look
// broken. The result is deterministic: the same set always draws identically.
function renderMenuGraph() {
  const box = $("menuGraph");
  box.innerHTML = "";
  if (!menu.entries.length) return;
  const byId = new Map(menu.entries.map((e) => [e.id, e]));
  const dead = new Set(menu.broken.map((b) => `${b.screen}|${b.event}`));
  const unreach = new Set(menu.unreachable);
  const groupOf = (id) => (id.includes("/") ? id.split("/")[0] : "(root)");

  // Lanes in the core's own order: biggest group first, so the part of the
  // menu a user is most likely chasing sits at the top.
  const laneOrder = menu.groups.map((g) => g[0]);
  const lanes = new Map();
  menu.entries.forEach((e) => {
    const g = groupOf(e.id);
    if (!lanes.has(g)) lanes.set(g, []);
    lanes.get(g).push(e);
  });
  const ordered = [...lanes.keys()].sort((a, b) => {
    const ia = laneOrder.indexOf(a), ib = laneOrder.indexOf(b);
    return (ia < 0 ? 999 : ia) - (ib < 0 ? 999 : ib) || a.localeCompare(b);
  });

  // Depth from screens nothing in the set points at: those are the doors the
  // engine opens first, so leftmost is where navigation actually starts.
  const incoming = new Map();
  menu.entries.forEach((e) => e.events.forEach((ev) => {
    if (ev.to && byId.has(ev.to) && ev.to !== e.id) incoming.set(ev.to, (incoming.get(ev.to) || 0) + 1);
  }));
  const depth = new Map();
  let queue = menu.entries.filter((e) => !incoming.has(e.id)).map((e) => e.id);
  if (!queue.length) queue = [menu.entries[0].id];
  queue.forEach((id) => depth.set(id, 0));
  for (let head = 0; head < queue.length; head++) {
    const d = depth.get(queue[head]);
    for (const ev of byId.get(queue[head]).events) {
      if (!ev.to || !byId.has(ev.to) || depth.has(ev.to)) continue;
      depth.set(ev.to, d + 1);
      queue.push(ev.to);
    }
  }
  let maxd = Math.max(0, ...depth.values());
  menu.entries.forEach((e) => { if (!depth.has(e.id)) depth.set(e.id, ++maxd); });

  const NW = 186, NH = 28, CGAP = 74, RGAP = 10, LANE_PAD = 14;
  const row = new Map();
  let y = 0;
  ordered.forEach((g) => {
    const list = lanes.get(g);
    // Order by depth, then by the average row of the predecessors already
    // placed. Two sweeps is enough on menus, which are shallow, and it keeps
    // the layout stable instead of depending on iteration count.
    const key = (e) => [depth.get(e.id), e.id];
    list.sort((a, b) => key(a)[0] - key(b)[0] || key(a)[1].localeCompare(key(b)[1]));
    for (let sweep = 0; sweep < 2; sweep++) {
      const score = new Map();
      list.forEach((e) => {
        const preds = [];
        menu.entries.forEach((o) => o.events.forEach((ev) => {
          if (ev.to === e.id && row.has(o.id)) preds.push(row.get(o.id));
        }));
        score.set(e.id, preds.length ? preds.reduce((s, v) => s + v, 0) / preds.length : row.get(e.id));
      });
      list.sort((a, b) => (depth.get(a.id) - depth.get(b.id)) || (score.get(a.id) - score.get(b.id)) || a.id.localeCompare(b.id));
    }
    list.forEach((e, i) => row.set(e.id, y + i));
    y += list.length + 1;
  });
  const totalRows = y;

  const pos = new Map();
  menu.entries.forEach((e) => pos.set(e.id, {
    x: 14 + depth.get(e.id) * (NW + CGAP),
    y: 10 + row.get(e.id) * (NH + RGAP),
  }));
  const W = 14 + (maxd + 1) * (NW + CGAP) + NW;
  const H = 10 + totalRows * (NH + RGAP);

  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("width", W);
  svg.setAttribute("height", H);
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  svg.innerHTML = `<defs>
    <marker id="arw" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M0,0 L10,5 L0,10 z" style="fill:#5b8f4e" />
    </marker>
    <marker id="arw-dead" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M0,0 L10,5 L0,10 z" style="fill:#d26565" />
    </marker>
  </defs>`;
  box.appendChild(svg);

  // Lane bands, drawn behind everything, with the group name in the gutter.
  ordered.forEach((g) => {
    const list = lanes.get(g);
    const top = 10 + row.get(list[0].id) * (NH + RGAP) - LANE_PAD / 2;
    const h = (list.length - 1) * (NH + RGAP) + NH + LANE_PAD;
    const band = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    band.setAttribute("x", 2); band.setAttribute("y", top);
    band.setAttribute("width", W - 4); band.setAttribute("height", h);
    band.setAttribute("class", "lane");
    band.setAttribute("rx", 8);
    svg.appendChild(band);
    const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
    label.setAttribute("x", 8); label.setAttribute("y", top + 11);
    label.setAttribute("class", "lanelabel");
    label.textContent = g;
    svg.appendChild(label);
  });

  const edgeClass = (isDead) => isDead ? "dead" : "ok";
  menu.entries.forEach((e) => {
    const from = pos.get(e.id);
    e.events.forEach((ev) => {
      if (!ev.to || !byId.has(ev.to)) return;
      const isDead = dead.has(`${e.id}|${ev.name}`);
      const to = pos.get(ev.to);
      const p = document.createElementNS("http://www.w3.org/2000/svg", "path");
      const x1 = from.x + NW, y1 = from.y + NH / 2;
      const x2 = to.x, y2 = to.y + NH / 2;
      let d;
      if (ev.to === e.id) {
        // Self link: a small loop on the right, labelled by the event name.
        d = `M${x1},${y1 - 5} C${x1 + 26},${y1 - 16} ${x1 + 26},${y1 + 16} ${x1},${y1 + 5}`;
      } else if (to.x > from.x) {
        const bend = Math.max(28, (x2 - x1) / 2);
        d = `M${x1},${y1} C${x1 + bend},${y1} ${x2 - bend},${y2} ${x2},${y2}`;
      } else {
        // Back and sideways links go under the nodes rather than through them,
        // which is what keeps a menu with many "back" buttons readable.
        const dip = Math.max(y1, y2) + 16;
        d = `M${x1},${y1} C${x1 + 40},${dip} ${x2 - 40},${dip} ${x2},${y2}`;
      }
      p.setAttribute("d", d);
      p.setAttribute("class", edgeClass(isDead));
      p.setAttribute("marker-end", isDead ? "url(#arw-dead)" : "url(#arw)");
      p.style.pointerEvents = "stroke";
      p.dataset.from = e.id;
      p.dataset.event = ev.name;
      const title = document.createElementNS("http://www.w3.org/2000/svg", "title");
      title.textContent = `${e.id} · ${ev.name} -> ${ev.to}${isDead ? "  (DEAD)" : ""}`;
      p.appendChild(title);
      p.onclick = () => {
        menu.sel = e.id;
        renderMenuList();
        renderMenuGraph();
        menuShow(e);
        $("menuEvent").value = ev.name;
        $("menuTarget").value = ev.to;
      };
      svg.appendChild(p);
    });
  });

  menu.entries.forEach((e) => {
    const at = pos.get(e.id);
    const n = el("div", "node" + (menu.sel === e.id ? " on" : ""), "");
    const name = el("span", "nodename", e.id.split("/").pop() || e.id);
    n.appendChild(name);
    n.appendChild(el("span", "badge", String(e.events.length)));
    n.title = e.id;
    if (unreach.has(e.id)) n.classList.add("unreach");
    if (e.events.some((ev) => dead.has(`${e.id}|${ev.name}`))) n.classList.add("dead");
    n.style.left = at.x + "px";
    n.style.top = at.y + "px";
    n.style.width = NW + "px";
    n.style.height = NH + "px";
    n.onclick = () => { menu.sel = e.id; renderMenuList(); renderMenuGraph(); menuShow(e); };
    box.appendChild(n);
  });
  box.style.minHeight = Math.min(H + 24, 460) + "px";
}

function renderMenuList() {
  const box = $("menuList");
  box.innerHTML = "";
  menu.entries.forEach((e) => {
    const d = el("div", "tnode" + (menu.sel === e.id ? " on" : ""), "");
    d.appendChild(el("span", null, e.id));
    d.appendChild(el("span", "muted", `  ${e.events.length} event(s)`));
    d.onclick = () => { menu.sel = e.id; renderMenuList(); menuShow(e); };
    box.appendChild(d);
  });
  if (!menu.entries.length) box.appendChild(el("div", "muted", "check a set first"));
}

function menuShow(e) {
  const sel = $("menuEvent");
  sel.innerHTML = "";
  e.events.forEach((ev) => {
    const o = document.createElement("option");
    o.value = ev.name;
    o.textContent = `${ev.name} -> ${ev.to || "(none)"}`;
    sel.appendChild(o);
  });
  $("menuTarget").value = (e.events[0] && e.events[0].to) || "";
  $("menuDetail").textContent = JSON.stringify(e, null, 2);
}

async function menuRepoint() {
  if (!menu.sel) return say("Pick a screen on the left.", "warn");
  const ev = $("menuEvent").value;
  const to = $("menuTarget").value.trim();
  const root = $("menuRoot").value.trim();
  const base = $("menuBase").value.trim();
  if (!ev || !to) return say("Choose an event and a target screen.", "warn");
  if (!root || !base) return say("Both the set and the base layer are needed.", "err");
  const yes = await dialog.ask(`Repoint ${menu.sel} · ${ev} to ${to}?`, { title: "Edit navigation" });
  if (!yes) return;
  try {
    const r = await busy("Writing", () => invoke("menu_link", {
      root, bases: [base], screen: menu.sel, event: ev, target: to,
    }));
    say("Rewrote " + r, "ok");
    await menuCheck();
  } catch (err) {
    say(String(err), "err");
  }
}


initStudio();
$("menuBrowse").addEventListener("click", async () => {
  const d = await pick({ directory: true });
  if (d) { $("menuRoot").value = d; }
});
$("menuBaseBrowse").addEventListener("click", async () => {
  const d = await pick({ directory: true });
  if (d) { $("menuBase").value = d; }
});
$("menuCheck").addEventListener("click", menuCheck);
$("menuLink").addEventListener("click", menuRepoint);
$("assetBrowse").addEventListener("click", async () => {
  const dir = await pick({ directory: true });
  if (dir) { $("assetRoot").value = dir; assetScan(); }
});
$("assetScan").addEventListener("click", assetScan);
$("assetFamily").addEventListener("change", renderAssets);
$("assetRender").addEventListener("click", assetRender);
$("assetReplace").addEventListener("click", assetReplace);
$("binApply").addEventListener("click", patchBin);

boot();