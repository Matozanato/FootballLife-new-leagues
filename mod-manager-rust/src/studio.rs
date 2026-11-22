//! Mod authoring: workspaces, pack scaffolds, and installing a pack for real.
//!
//! Two rules from Sider itself shape everything here.
//!
//! `cpk.root` is **first wins**, and the bare `.\livecpk\root` base line has to
//! stay last or nothing else resolves. So installing a pack inserts its line
//! immediately before the base root, not appended to the file, and a pack that
//! is already listed is never listed twice.
//!
//! The user's `sider.ini` is hand-written. Nothing in this module rewrites a
//! line it was not asked to change: the file is parsed, one line is inserted,
//! and every other line is rendered back byte-for-byte from the source, which
//! is what `ini::Ini` is built to guarantee. Before the first edit the file is
//! copied aside, and after the copy every installed file is compared against
//! its source byte for byte rather than trusted to a hash that could collide.

use std::collections::BTreeMap;
use std::fs;
use std::io::{Read, Write};
use std::path::{Path, PathBuf};
use std::time::SystemTime;

use anyhow::{bail, Context, Result};
use serde::Serialize;

use crate::ini::{Entry, Ini, Line};
use crate::packs;

/// Largest file the editor will load. A 4 GB `dt30_g4.cpk` is not a text file
/// and must not be pulled into memory to show a cursor.
pub const READ_LIMIT: u64 = 8 << 20;

// ------------------------------------------------------------------ tree

#[derive(Debug, Clone, Serialize)]
pub struct Node {
    pub name: String,
    pub path: String,
    pub dir: bool,
    pub size: u64,
    /// Whole seconds since the epoch; the UI formats it.
    pub mtime: u64,
    /// True when the name starts with a dot or is a known build artefact, so
    /// the tree can grey it out instead of hiding data.
    pub hidden_by_default: bool,
}

fn mtime_of(meta: &fs::Metadata) -> u64 {
    meta.modified()
        .ok()
        .and_then(|t| t.duration_since(SystemTime::UNIX_EPOCH).ok())
        .map(|d| d.as_secs())
        .unwrap_or(0)
}

fn hidden_name(name: &str) -> bool {
    name.starts_with('.') || matches!(name, "target" | "node_modules" | "__pycache__" | ".git")
}

/// One level of a directory, sorted folders-first then by name. Deliberately
/// not recursive: the game install holds hundreds of thousands of files and a
/// tree that expands lazily is the only version that opens quickly.
pub fn tree(root: &Path) -> Result<Vec<Node>> {
    let mut out = Vec::new();
    let rd = fs::read_dir(root).with_context(|| format!("opening {}", root.display()))?;
    for entry in rd.flatten() {
        let name = entry.file_name().to_string_lossy().to_string();
        let Ok(meta) = entry.metadata() else { continue };
        let dir = meta.is_dir();
        out.push(Node {
            hidden_by_default: hidden_name(&name),
            mtime: mtime_of(&meta),
            size: if dir { 0 } else { meta.len() },
            path: entry.path().to_string_lossy().replace('\\', "/"),
            name,
            dir,
        });
    }
    out.sort_by(|a, b| match (a.dir, b.dir) {
        (true, false) => std::cmp::Ordering::Less,
        (false, true) => std::cmp::Ordering::Greater,
        _ => a.name.to_lowercase().cmp(&b.name.to_lowercase()),
    });
    Ok(out)
}

// ------------------------------------------------------------------ editing

#[derive(Debug, Clone, Serialize)]
pub struct TextFile {
    pub path: String,
    pub size: u64,
    /// Refused rather than mangled: the UI shows a hex peek instead.
    pub binary: bool,
    pub text: String,
    /// Bytes of NUL or other control content, as the reason for `binary`.
    pub odd_bytes: usize,
}

/// Read a file as text for the editor. A file is treated as binary when it
/// holds any NUL in the first 8 KiB, which is how every real asset here —
/// `.cpk`, `.ftex`, `.bin`, `.fmdl` — is distinguished from the ones worth
/// editing (`sider.ini`, `.lua`, `.json`, `.txt`, `.md`).
pub fn read_text(path: &Path) -> Result<TextFile> {
    let meta = fs::metadata(path).with_context(|| format!("statting {}", path.display()))?;
    let size = meta.len();
    if size > READ_LIMIT {
        bail!(
            "{} is {size} bytes, over the {} MiB the editor loads. It is an \
             archive or a texture, not a text file.",
            path.display(),
            READ_LIMIT >> 20
        );
    }
    let bytes = fs::read(path).with_context(|| format!("reading {}", path.display()))?;
    let head = &bytes[..bytes.len().min(8192)];
    let odd = head.iter().filter(|b| **b == 0).count();
    if odd > 0 {
        return Ok(TextFile {
            path: path.to_string_lossy().replace('\\', "/"),
            size,
            binary: true,
            text: String::new(),
            odd_bytes: odd,
        });
    }
    // Lossy rather than an error: one stray 0x92 in a mod's README should not
    // block editing the rest of it, and the UI says so in the status line.
    let text = String::from_utf8_lossy(&bytes).to_string();
    Ok(TextFile {
        path: path.to_string_lossy().replace('\\', "/"),
        size,
        binary: false,
        text,
        odd_bytes: 0,
    })
}

/// Write through a temporary name and rename, so an interrupted save cannot
/// leave a half-written `sider.ini` behind. Returns the bytes now on disk.
pub fn write_text(path: &Path, text: &str) -> Result<usize> {
    let parent = path.parent().unwrap_or(Path::new("."));
    fs::create_dir_all(parent).with_context(|| format!("creating {}", parent.display()))?;
    let tmp = path.with_extension(format!(
        "{}.fl27mm-tmp",
        path.extension().and_then(|e| e.to_str()).unwrap_or("tmp")
    ));
    {
        let mut f =
            fs::File::create(&tmp).with_context(|| format!("creating {}", tmp.display()))?;
        f.write_all(text.as_bytes())?;
        f.flush()?;
    }
    fs::rename(&tmp, path).with_context(|| format!("replacing {}", path.display()))?;
    Ok(text.len())
}

// ------------------------------------------------------------------ scaffold

#[derive(Debug, Clone, Serialize)]
pub struct Scaffold {
    pub dir: String,
    /// Folders and files that now exist and did not before.
    pub created: Vec<String>,
    /// Paths that were already there, so nothing was written to them.
    pub skipped: Vec<String>,
    /// The scaffold files written, separately so the UI can list them as files.
    pub files: Vec<String>,
    /// Anything that should have landed and did not. Empty means success.
    pub missing: Vec<String>,
    /// The sider.ini line that registers this pack, which the user still has
    /// to add unless they use Install.
    pub note: String,
}

/// Kinds a mod can be, each with the layout Sider actually expects.
///
/// These are directories only. Listing a file here used to create a *folder*
/// with that name — `create_dir_all` on `My Script/init.lua` makes a directory
/// called `init.lua` — and the file write that followed then saw it already
/// existing and skipped it, so a Lua scaffold silently produced no script at
/// all. Files are written explicitly below instead.
pub fn kind_hint(kind: &str) -> (&'static str, &'static str, Vec<&'static str>) {
    match kind {
        "cpk" => (
            "Asset folder with .cpk files",
            "cpk.root",
            vec!["livecpk/root/<name>/Asset", "livecpk/root/<name>/common"],
        ),
        "lua" => (
            "A Lua module folder with an init.lua",
            "lua.module",
            vec!["<name>"],
        ),
        "mesh" => (
            "Face or kit meshes and their textures",
            "cpk.root",
            vec!["livecpk/root/<name>/Asset/model/character/face/real"],
        ),
        _ => (
            "A pack folder with an .ini or .cpk inside",
            "cpk.root",
            vec!["livecpk/root/<name>"],
        ),
    }
}

/// Create a pack folder with the files a mod needs, without ever overwriting
/// something that already exists. Every path it means to leave behind is
/// re-checked afterwards, so a scaffold that silently did nothing cannot pass
/// as success.
pub fn new_pack(addons: &Path, name: &str, kind: &str) -> Result<Scaffold> {
    if name.trim().is_empty() || name.contains(['/', '\\']) {
        bail!("pick a folder name without slashes in it");
    }
    let (hint, hook, layout) = kind_hint(kind);
    let pack_rel = match kind {
        "lua" => name.to_string(),
        _ => format!("livecpk/root/{name}"),
    };
    let pack = addons.join(pack_rel.replace('/', std::path::MAIN_SEPARATOR_STR));
    let mut created = Vec::new();
    let mut skipped = Vec::new();
    let mut files = Vec::new();

    for rel in layout {
        let path = addons.join(
            rel.replace("<name>", name)
                .replace('/', std::path::MAIN_SEPARATOR_STR),
        );
        if path.exists() {
            skipped.push(path.to_string_lossy().replace('\\', "/"));
            continue;
        }
        fs::create_dir_all(&path).with_context(|| format!("creating {}", path.display()))?;
        created.push(path.to_string_lossy().replace('\\', "/"));
    }

    // The script itself, for the one kind that is defined by it.
    if kind == "lua" {
        write_if_absent(
            &pack.join("init.lua"),
            &lua_stub(name),
            &mut skipped,
            &mut files,
        )?;
    }
    let readme = pack.join("README.txt");
    write_if_absent(
        &readme,
        &readme_body(name, kind, hint, hook),
        &mut skipped,
        &mut files,
    )?;

    // Prove it landed. A directory where a file belongs is the specific way
    // this used to fail, so the check distinguishes the two.
    let mut missing = Vec::new();
    for p in &files {
        let path = Path::new(p);
        if !path.is_file() {
            missing.push(format!(
                "{} is not a file",
                p.rsplit('/').next().unwrap_or(p)
            ));
        }
    }
    if !pack.is_dir() {
        missing.push(format!("{} was not created", pack.display()));
    }
    if missing.is_empty() {
        created.extend(files.clone());
    }
    Ok(Scaffold {
        dir: pack.to_string_lossy().replace('\\', "/"),
        created,
        skipped,
        files,
        missing,
        note: match kind {
            "lua" => format!("add `lua.module = \"{name}/init.lua\"` to register it"),
            _ => format!("add `cpk.root = \".\\{pack_rel}\"` to register it"),
        },
    })
}

/// Write a scaffold file unless something is already there, recording which.
fn write_if_absent(
    path: &Path,
    body: &str,
    skipped: &mut Vec<String>,
    files: &mut Vec<String>,
) -> Result<()> {
    let shown = path.to_string_lossy().replace('\\', "/");
    if path.exists() {
        skipped.push(shown);
        return Ok(());
    }
    if let Some(p) = path.parent() {
        fs::create_dir_all(p)?;
    }
    write_text(path, body)?;
    files.push(shown);
    Ok(())
}

fn readme_body(name: &str, kind: &str, hint: &str, hook: &str) -> String {
    format!(
        "{name}\n{}\nKind: {kind}  ({hint})\nRegistered by: {hook}\n\n\
         Built by FL27 Mod Manager. Put your files in, then use Install in the\n\
         Mod Studio tab to copy the pack into livecpk/root and register it.\n",
        "=".repeat(name.len().max(4))
    )
}

fn lua_stub(name: &str) -> String {
    format!(
        "-- {name}, scaffolded by FL27 Mod Manager\n\
         -- Register it in sider.ini as: lua.module = \"{name}/init.lua\"\n\
         -- Modules run in the order they appear, so a later one can override\n\
         -- an earlier one's hooks.\n\
         local this = ...\n\n\
         if debugger then debugger:attach() end\n\
         if const then const.load() end\n\n\
         -- Replace a parameter value at match start, the way the shipped\n\
         -- modules do it:\n\
         -- replace_param = function(t, name, val) for k, v in pairs(t) do\n\
         --   if k == name then t[k] = val return true end end return false end\n\
         return this\n"
    )
}

// ------------------------------------------------------------------ install

#[derive(Debug, Clone, Serialize)]
pub struct InstalledFile {
    pub path: String,
    pub size: u64,
    /// Byte-for-byte check of the copy against the source.
    pub verified: bool,
}

#[derive(Debug, Clone, Serialize)]
pub struct Install {
    pub target: String,
    pub files: Vec<InstalledFile>,
    pub bytes: u64,
    /// The line inserted into sider.ini, or None when it was already there.
    pub ini_line: Option<String>,
    pub backup: Option<String>,
    pub warnings: Vec<String>,
}

/// Stream-compare two files. Cheaper than a hash crate and stronger: a length
/// or byte difference is reported, not a collision-resistant digest that the
/// reader has to trust.
fn same_bytes(a: &Path, b: &Path) -> bool {
    let (mut fa, mut fb) = match (fs::File::open(a), fs::File::open(b)) {
        (Ok(x), Ok(y)) => (x, y),
        _ => return false,
    };
    let mut ba = [0u8; 1 << 16];
    let mut bb = [0u8; 1 << 16];
    loop {
        let na = read_fill(&mut fa, &mut ba);
        let nb = read_fill(&mut fb, &mut bb);
        if na != nb || ba[..na] != bb[..nb] {
            return false;
        }
        if na == 0 {
            return true;
        }
    }
}

fn read_fill(f: &mut fs::File, buf: &mut [u8]) -> usize {
    let mut got = 0usize;
    while got < buf.len() {
        match f.read(&mut buf[got..]) {
            Ok(0) => break,
            Ok(n) => got += n,
            Err(_) => break,
        }
    }
    got
}

fn copy_tree(src: &Path, dest: &Path, out: &mut Vec<InstalledFile>) -> Result<u64> {
    fs::create_dir_all(dest)?;
    let mut bytes = 0u64;
    for entry in fs::read_dir(src)? {
        let entry = entry?;
        let name = entry.file_name();
        let from = entry.path();
        let to = dest.join(&name);
        if entry.file_type()?.is_dir() {
            bytes += copy_tree(&from, &to, out)?;
        } else {
            fs::copy(&from, &to).with_context(|| format!("copying {}", from.display()))?;
            let size = from.metadata().map(|m| m.len()).unwrap_or(0);
            bytes += size;
            out.push(InstalledFile {
                verified: same_bytes(&from, &to),
                path: to.to_string_lossy().replace('\\', "/"),
                size,
            });
        }
    }
    Ok(bytes)
}

/// The base root line, which must remain the last `cpk.root` in the file.
fn base_root_index(ini: &Ini) -> Option<usize> {
    ini.line_indices("cpk.root").into_iter().rev().find(
        |&i| matches!(ini.lines.get(i), Some(Line::Entry(e)) if crate::order::is_base(&e.value)),
    )
}

/// Register a pack in sider.ini without disturbing any other line. Returns the
/// rendered line, or None when the pack is already registered.
pub fn register(ini: &mut Ini, value: &str, section_hint: &str) -> Option<String> {
    let already = ini.all(section_hint).iter().any(|e| {
        e.value
            .replace('/', "\\")
            .eq_ignore_ascii_case(&value.replace('/', "\\"))
    });
    if already {
        return None;
    }
    let entry = Entry {
        indent: "\t".to_string(),
        disabled: false,
        key: section_hint.to_string(),
        value: value.to_string(),
        quoted: true,
        comment: String::new(),
    };
    let line = entry.render();
    // First-wins means a new content pack has to precede the base root, and a
    // new script has to follow the library it uses. Both land before the base
    // root line, which is the last one, so the ordering rule holds either way.
    let at = match section_hint {
        "cpk.root" => base_root_index(ini)
            .or_else(|| ini.line_indices(section_hint).into_iter().next())
            .unwrap_or(ini.lines.len()),
        _ => ini
            .line_indices(section_hint)
            .into_iter()
            .next_back()
            .map(|i| i + 1)
            .unwrap_or(ini.lines.len()),
    };
    ini.lines.insert(at, Line::Entry(entry));
    Some(line)
}

/// Copy a pack into the install and register it, with a backup of `sider.ini`
/// and a byte-for-byte check of every copied file.
pub fn install_pack(src: &Path, addons: &Path) -> Result<Install> {
    if !src.is_dir() {
        bail!("{} is not a folder", src.display());
    }
    let name = src
        .file_name()
        .context("pack folder has no name")?
        .to_string_lossy()
        .to_string();
    let root = addons.join("livecpk").join("root");
    let target = root.join(&name);
    if src == target {
        bail!("this pack is already inside livecpk/root, so it needs no install");
    }
    // A pack nested under livecpk/root is already in place; only register it.
    let mut files = Vec::new();
    let mut warnings = Vec::new();
    let inside = target.exists() && same_dir(src, &target);
    let bytes = if !inside {
        if target.exists() {
            bail!(
                "{} already exists. Remove it or rename the pack first, so this \
                 cannot silently overwrite an installed pack.",
                target.display()
            );
        }
        fs::create_dir_all(target.parent().unwrap_or(&root))?;
        let copied = copy_tree(src, &target, &mut files)?;
        let bad: Vec<&str> = files
            .iter()
            .filter(|f| !f.verified)
            .map(|f| f.path.as_str())
            .collect();
        if !bad.is_empty() {
            warnings.push(format!(
                "{} copied file(s) do not match their source: {:?}",
                bad.len(),
                &bad[..bad.len().min(3)]
            ));
        }
        copied
    } else {
        0
    };

    let ini_path = addons.join("sider.ini");
    let mut backup = None;
    let mut ini_line = None;
    if ini_path.exists() {
        let stamp = mtime_of(&fs::metadata(&ini_path)?);
        let bak = addons.join(format!("sider.ini.before-{name}-{stamp}"));
        fs::copy(&ini_path, &bak).context("backing up sider.ini")?;
        backup = Some(bak.to_string_lossy().replace('\\', "/"));
        let mut ini = Ini::read(&ini_path)?;
        let value = format!(".\\livecpk\\root\\{name}");
        if let Some(line) = register(&mut ini, &value, "cpk.root") {
            ini.write(&ini_path)
                .with_context(|| format!("writing {}", ini_path.display()))?;
            ini_line = Some(line);
        } else {
            warnings.push(format!("{name} is already registered in sider.ini"));
        }
    } else {
        warnings.push(format!(
            "no sider.ini at {} — files copied, nothing registered",
            addons.display()
        ));
    }
    Ok(Install {
        target: target.to_string_lossy().replace('\\', "/"),
        files,
        bytes,
        ini_line,
        backup,
        warnings,
    })
}

fn same_dir(a: &Path, b: &Path) -> bool {
    fs::canonicalize(a)
        .ok()
        .zip(fs::canonicalize(b).ok())
        .map(|(x, y)| x == y)
        .unwrap_or(false)
}

// ------------------------------------------------------------------ entries
//
// The order of `cpk.root` and `lua.module` lines in sider.ini *is* the mod
// order, and this install has 175 and 43 of them, so editing that list is the
// main thing a mod maker does. Every action here changes one parsed line and
// renders everything else back untouched, and each one can be previewed:
// `apply: false` returns exactly the diff `apply: true` would write, with no
// backup and no touch to the file.

/// The keys the manager exposes. The others in sider.ini are single settings,
/// not an ordered list, so reordering them would be meaningless.
pub const ORDERED_KEYS: [&str; 2] = ["cpk.root", "lua.module"];

#[derive(Debug, Clone, Serialize)]
pub struct ModEntry {
    pub key: String,
    pub value: String,
    pub enabled: bool,
    pub comment: String,
    /// 1-based line number in sider.ini, shown in the preview.
    pub line: usize,
    /// Position among the entries that share this key.
    pub order: usize,
    pub exists: bool,
    pub resolved: String,
    /// True for the bare base root, which has to stay last.
    pub is_base: bool,
}

#[derive(Debug, Clone, Serialize)]
pub struct Edit {
    pub action: String,
    pub applied: bool,
    /// The lines involved, rendered before and after the change.
    pub before: Vec<String>,
    pub after: Vec<String>,
    pub backup: Option<String>,
    pub note: String,
}

fn render_line(line: &Line) -> String {
    match line {
        Line::Entry(e) => e.render(),
        Line::Raw(r) => r.clone(),
    }
}

/// Where a registered value actually points. `cpk.root` paths resolve through
/// the same function the Pack order tab uses, so the two cannot disagree about
/// whether a pack is present.
fn resolve_value(addons: &Path, key: &str, value: &str) -> PathBuf {
    if key == "cpk.root" {
        crate::order::resolve(addons, value)
    } else {
        addons.join(value.replace('/', std::path::MAIN_SEPARATOR_STR))
    }
}

pub fn entries(addons: &Path) -> Result<Vec<ModEntry>> {
    let ini = Ini::read(&addons.join("sider.ini"))
        .context("reading sider.ini — set the game folder first")?;
    let mut out = Vec::new();
    let mut counts: BTreeMap<String, usize> = Default::default();
    for (i, line) in ini.lines.iter().enumerate() {
        let Line::Entry(e) = line else { continue };
        if !ORDERED_KEYS.contains(&e.key.as_str()) {
            continue;
        }
        let order = counts.entry(e.key.clone()).or_insert(0);
        *order += 1;
        let resolved = resolve_value(addons, &e.key, &e.value);
        out.push(ModEntry {
            is_base: e.key == "cpk.root" && crate::order::is_base(&e.value),
            key: e.key.clone(),
            value: e.value.clone(),
            enabled: !e.disabled,
            comment: e.comment.clone(),
            line: i + 1,
            order: *order,
            exists: resolved.exists(),
            resolved: resolved.to_string_lossy().replace('\\', "/"),
        });
    }
    Ok(out)
}

/// Enable, disable, move, or unregister one entry. `apply` false means "just
/// tell me what would change", and then nothing at all is written.
pub fn edit(addons: &Path, key: &str, value: &str, mode: &str, apply: bool) -> Result<Edit> {
    if !ORDERED_KEYS.contains(&key) {
        bail!("{key} is not an ordered list; edit it in the editor instead");
    }
    let ini_path = addons.join("sider.ini");
    let mut ini = Ini::read(&ini_path).context("reading sider.ini")?;
    let indices = ini.line_indices(key);
    let want = value.replace('/', "\\").to_lowercase();
    let Some(slot) = indices.iter().position(|&i| match &ini.lines[i] {
        Line::Entry(e) => e.value.replace('/', "\\").to_lowercase() == want,
        _ => false,
    }) else {
        bail!("{key} = \"{value}\" is not registered in sider.ini");
    };
    let idx = indices[slot];
    let neighbour: Option<usize> = match mode {
        "up" if slot > 0 => Some(indices[slot - 1]),
        "down" if slot + 1 < indices.len() => Some(indices[slot + 1]),
        "up" | "down" => bail!(
            "{} is already at the {} of the {key} list",
            value,
            if mode == "up" { "top" } else { "bottom" }
        ),
        _ => None,
    };
    let before: Vec<String> = match neighbour {
        Some(n) => vec![render_line(&ini.lines[idx]), render_line(&ini.lines[n])],
        None => vec![render_line(&ini.lines[idx])],
    };
    let mut note = String::new();
    let mut after = Vec::new();

    match mode {
        "enable" | "disable" => {
            let want_on = mode == "enable";
            if let Line::Entry(e) = &mut ini.lines[idx] {
                e.disabled = !want_on;
            }
            note = format!("{} {}", value, if want_on { "enabled" } else { "disabled" });
            after = vec![render_line(&ini.lines[idx])];
        }
        "remove" => {
            note.push_str("line removed from sider.ini");
        }
        "up" | "down" => {
            let other = neighbour.unwrap();
            // The base root must stay last: it is the stock files, and first
            // wins means anything below it loses. Moving across it would make
            // every other pack lose, so it is pinned.
            let pin = |i: usize| match &ini.lines[i] {
                Line::Entry(e) => e.key == "cpk.root" && crate::order::is_base(&e.value),
                _ => false,
            };
            if pin(idx) || pin(other) {
                bail!(
                    "the base root line stays last — moving across it would make \
                     every other pack lose to the stock files"
                );
            }
            ini.lines.swap(idx, other);
            note = format!(
                "{} moved {}",
                value,
                if mode == "up" { "up" } else { "down" }
            );
            after = vec![render_line(&ini.lines[idx]), render_line(&ini.lines[other])];
        }
        other => bail!("unknown action {other}"),
    }

    let mut backup = None;
    if apply {
        let stamp = fs::metadata(&ini_path)
            .ok()
            .and_then(|m| m.modified().ok())
            .and_then(|t| t.duration_since(SystemTime::UNIX_EPOCH).ok())
            .map(|d| d.as_secs())
            .unwrap_or(0);
        let bak = addons.join(format!("sider.ini.before-{mode}-{stamp}"));
        fs::copy(&ini_path, &bak).context("backing up sider.ini")?;
        backup = Some(bak.to_string_lossy().replace('\\', "/"));
        if mode == "remove" {
            ini.lines.remove(idx);
        }
        ini.write(&ini_path).context("writing sider.ini")?;
    }
    Ok(Edit {
        action: format!("{mode} {key} = \"{value}\""),
        applied: apply,
        before,
        after,
        backup,
        note,
    })
}

// ------------------------------------------------------------------ file ops

/// Create an empty file, refusing to clobber one that exists.
pub fn create_file(path: &Path) -> Result<u64> {
    if path.exists() {
        bail!("{} already exists — nothing was written", path.display());
    }
    if let Some(p) = path.parent() {
        fs::create_dir_all(p)?;
    }
    fs::write(path, "")?;
    Ok(0)
}

/// Rename inside the workspace. Refuses if the destination is taken, because
/// silently replacing a file in an installed pack is not recoverable.
pub fn rename(from: &Path, to: &Path) -> Result<String> {
    if to.exists() {
        bail!("{} already exists — nothing was renamed", to.display());
    }
    if let Some(p) = to.parent() {
        fs::create_dir_all(p)?;
    }
    fs::rename(from, to)
        .with_context(|| format!("renaming {} to {}", from.display(), to.display()))?;
    Ok(to.to_string_lossy().replace('\\', "/"))
}

/// Delete one file or folder tree. The UI confirms first; this still refuses
/// anything outside the workspace it was handed, so a bad path cannot reach
/// the game's own Data folder.
pub fn remove(path: &Path, workspace: &Path) -> Result<String> {
    let real = |p: &Path| p.canonicalize().unwrap_or_else(|_| p.to_path_buf());
    let (target, root) = (real(path), real(workspace));
    if !target.starts_with(&root) || target == root {
        bail!("{path:?} is not a folder inside the workspace, so this refuses to delete it");
    }
    if target.is_dir() {
        fs::remove_dir_all(&target)?;
    } else {
        fs::remove_file(&target)?;
    }
    Ok(target.to_string_lossy().replace('\\', "/"))
}

// ------------------------------------------------------------------ validate

#[derive(Debug, Clone, Serialize)]
pub struct PackCheck {
    pub path: String,
    pub notes: Vec<String>,
    pub registered: bool,
    pub shadows: Vec<String>,
}

/// What would actually happen if this pack were installed: what it contains,
/// whether it is already registered, and which of its files another pack
/// already claims. Uses the same discovery the Pack order tab uses, so the
/// answer cannot disagree with that view.
pub fn check_pack(dir: &Path, addons: &Path) -> Result<PackCheck> {
    let name = dir
        .file_name()
        .map(|n| n.to_string_lossy().to_string())
        .unwrap_or_default();
    let mut notes: Vec<String> = Vec::new();
    let mut counts: BTreeMap<String, usize> = Default::default();
    let mut bytes = 0u64;
    for f in crate::fsutil::files(dir) {
        let ext = f
            .extension()
            .and_then(|e| e.to_str())
            .map(|e| format!(".{e}"))
            .unwrap_or_else(|| "(no extension)".to_string());
        *counts.entry(ext).or_default() += 1;
        bytes += f.metadata().map(|m| m.len()).unwrap_or(0);
    }
    if counts.is_empty() {
        notes.push("empty folder — nothing for Sider to load".to_string());
    }
    for (ext, n) in &counts {
        notes.push(format!("{n} {ext}"));
    }
    notes.push(format!("{bytes} bytes total"));
    if !packs::GAME_EXT.iter().any(|k| counts.contains_key(*k)) {
        notes.push("no file type Sider recognises in here".to_string());
    }

    let ini = Ini::read(&addons.join("sider.ini")).unwrap_or_default();
    let want = format!(".\\livecpk\\root\\{name}").to_lowercase();
    let registered = ini
        .all("cpk.root")
        .iter()
        .any(|e| e.value.replace('/', "\\").to_lowercase() == want);

    // Which earlier packs already hold a file this pack would provide. My own
    // relative paths are collected once up front: walking them again for every
    // one of the 175 registered packs made validation quadratic, and on a real
    // workspace that is minutes rather than seconds.
    let my_set: std::collections::HashSet<PathBuf> = crate::fsutil::files(dir)
        .iter()
        .filter_map(|f| f.strip_prefix(dir).ok().map(|r| r.to_path_buf()))
        .collect();
    let mut shadows = Vec::new();
    for entry in ini.active("cpk.root") {
        let value = entry.value.replace('/', "\\");
        if value.eq_ignore_ascii_case(&want) {
            break; // everything after this pack cannot shadow it, first wins
        }
        let other = addons.join(value.replace('\\', std::path::MAIN_SEPARATOR_STR));
        if !other.is_dir() || same_dir(&other, dir) {
            continue;
        }
        for rel in crate::fsutil::files(&other).iter() {
            let rel = match rel.strip_prefix(&other) {
                Ok(r) => r.to_path_buf(),
                Err(_) => continue,
            };
            if my_set.contains(&rel) {
                shadows.push(format!(
                    "{} is also in {}",
                    rel.to_string_lossy().replace('\\', "/"),
                    entry.value
                ));
                if shadows.len() >= 12 {
                    break;
                }
            }
        }
        if shadows.len() >= 12 {
            break;
        }
    }
    Ok(PackCheck {
        path: dir.to_string_lossy().replace('\\', "/"),
        notes,
        registered,
        shadows,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn temp(tag: &str) -> PathBuf {
        let p = std::env::temp_dir().join(format!("fl27mm-studio-{tag}-{}", std::process::id()));
        let _ = fs::remove_dir_all(&p);
        fs::create_dir_all(&p).unwrap();
        p
    }

    #[test]
    fn tree_is_folders_first_and_sorted() {
        let d = temp("tree");
        fs::create_dir_all(d.join("zeta")).unwrap();
        fs::write(d.join("beta.lua"), "x").unwrap();
        fs::write(d.join("Alpha.ini"), "x").unwrap();
        fs::write(d.join(".hidden"), "x").unwrap();
        let t = tree(&d).unwrap();
        let names: Vec<&str> = t.iter().map(|n| n.name.as_str()).collect();
        // Folders first, then names case-insensitively, which puts the dotted
        // entry before "Alpha" because '.' sorts ahead of letters.
        assert_eq!(names, ["zeta", ".hidden", "Alpha.ini", "beta.lua"]);
        let hidden = t.iter().find(|n| n.name == ".hidden").unwrap();
        assert!(hidden.hidden_by_default);
        assert!(!t[0].hidden_by_default, "a folder is never greyed out");
        let _ = fs::remove_dir_all(&d);
    }

    #[test]
    fn binary_is_refused_and_text_is_read() {
        let d = temp("read");
        fs::write(d.join("mod.lua"), "local a = 1\n").unwrap();
        fs::write(d.join("mod.cpk"), [0u8, 1, 2, 0, 9]).unwrap();
        let t = read_text(&d.join("mod.lua")).unwrap();
        assert!(!t.binary);
        assert_eq!(t.text, "local a = 1\n");
        let b = read_text(&d.join("mod.cpk")).unwrap();
        assert!(b.binary, "a NUL in the head must be reported as binary");
        let _ = fs::remove_dir_all(&d);
    }

    #[test]
    fn atomic_write_leaves_no_temp_file() {
        let d = temp("write");
        let p = d.join("nested/dir.txt");
        let n = write_text(&p, "hello").unwrap();
        assert_eq!(n, 5);
        assert_eq!(fs::read_to_string(&p).unwrap(), "hello");
        let leftovers: Vec<_> = fs::read_dir(p.parent().unwrap())
            .unwrap()
            .flatten()
            .filter(|e| e.file_name().to_string_lossy().contains("fl27mm-tmp"))
            .collect();
        assert!(leftovers.is_empty(), "temp file left behind");
        let _ = fs::remove_dir_all(&d);
    }

    #[test]
    fn registering_inserts_before_the_base_root_and_touches_nothing_else() {
        let src = "[sider]\n\
\tcpk.root = \".\\livecpk\\root\\One\"\n\
\tcpk.root = \".\\livecpk\\root\"\n\
\tlua.module = \"lib\\CommonLib.lua\"  # shared\n";
        let mut ini = Ini::parse(src);
        let before: Vec<String> = ini
            .lines
            .iter()
            .map(|l| match l {
                Line::Entry(e) => e.render(),
                Line::Raw(r) => r.clone(),
            })
            .collect();
        let line = register(&mut ini, ".\\livecpk\\root\\New", "cpk.root").unwrap();
        let after: Vec<String> = ini
            .lines
            .iter()
            .map(|l| match l {
                Line::Entry(e) => e.render(),
                Line::Raw(r) => r.clone(),
            })
            .collect();
        assert_eq!(line, "\tcpk.root = \".\\livecpk\\root\\New\"");
        // Everything that was there is still there, unchanged, in order.
        let kept: Vec<&String> = after.iter().filter(|s| before.contains(s)).collect();
        assert_eq!(kept, before.iter().collect::<Vec<&String>>());
        let roots: Vec<usize> = after
            .iter()
            .position(|s| s.contains("New"))
            .into_iter()
            .collect();
        let base = after.iter().position(|s| s.ends_with("\\root\"")).unwrap();
        assert!(roots[0] < base, "a new pack must precede the base root");
        // And registering it again changes nothing.
        assert!(register(&mut ini, ".\\livecpk\\root\\New", "cpk.root").is_none());
    }

    #[test]
    fn scaffold_creates_the_expected_layout_without_overwriting() {
        let d = temp("scaffold");
        let s = new_pack(&d, "My Faces", "mesh").unwrap();
        assert!(
            s.created
                .iter()
                .any(|p| p.contains("My Faces/Asset/model/character/face")),
            "{:?}",
            s.created
        );
        assert!(
            s.missing.is_empty(),
            "mesh scaffold left something undone: {:?}",
            s.missing
        );
        let again = new_pack(&d, "My Faces", "mesh").unwrap();
        assert!(
            again.created.is_empty(),
            "a second run must not rewrite anything"
        );
        assert!(!again.skipped.is_empty());

        // The bug this guards: the layout used to list `init.lua` as a path to
        // create, so create_dir_all made a *directory* by that name and the
        // file write then skipped it. A Lua pack with no script looked like it
        // had worked.
        let lua = new_pack(&d, "My Script", "lua").unwrap();
        assert!(lua.dir.ends_with("My Script"));
        let init = d.join("My Script/init.lua");
        assert!(init.is_file(), "init.lua must be a file, not a folder");
        assert!(
            !init.is_dir(),
            "a directory named init.lua is the old failure"
        );
        assert!(lua.missing.is_empty(), "{:?}", lua.missing);
        assert!(
            lua.files.iter().any(|p| p.ends_with("init.lua")),
            "{:?}",
            lua.files
        );
        assert!(fs::read_to_string(&init).unwrap().contains("My Script"));
        assert!(d.join("My Script/README.txt").is_file());

        // Every kind must end with nothing missing.
        for kind in ["cpk", "lua", "mesh", "generic"] {
            let got = new_pack(&d, &format!("Pack {kind}"), kind).unwrap();
            assert!(
                got.missing.is_empty(),
                "{kind} scaffold incomplete: {:?}",
                got.missing
            );
            assert!(Path::new(&got.dir).is_dir(), "{kind} pack folder absent");
        }
        let _ = fs::remove_dir_all(&d);
    }

    #[test]
    fn install_copies_verifies_backs_up_and_registers() {
        let addons = temp("addons");
        let live = addons.join("livecpk/root");
        fs::create_dir_all(&live).unwrap();
        fs::write(
            addons.join("sider.ini"),
            "[sider]\n\tcpk.root = \".\\livecpk\\root\"\n",
        )
        .unwrap();
        let pack = temp("packsrc").join("My Pack");
        fs::create_dir_all(pack.join("Asset/effect")).unwrap();
        fs::write(pack.join("Asset/effect/x.ftex"), b"texture-bytes").unwrap();

        let got = install_pack(&pack, &addons).unwrap();
        assert_eq!(got.files.len(), 1);
        assert!(
            got.files[0].verified,
            "the copy must match its source byte for byte"
        );
        assert_eq!(got.bytes, 13);
        assert!(got.backup.is_some(), "sider.ini must be copied aside first");
        assert!(
            got.ini_line.as_ref().unwrap().contains("My Pack"),
            "{:?}",
            got.ini_line
        );
        let ini = fs::read_to_string(addons.join("sider.ini")).unwrap();
        let new_at = ini.find("My Pack").unwrap();
        let base_at = ini.find("cpk.root = \".\\livecpk\\root\"").unwrap();
        assert!(new_at < base_at, "the new pack must win over the base root");
        assert!(
            fs::read(addons.join("livecpk/root/My Pack/Asset/effect/x.ftex")).unwrap()
                == b"texture-bytes"
        );

        // Installing a second time must refuse to overwrite, not silently clobber.
        let again = install_pack(&pack, &addons);
        assert!(again.is_err(), "an existing target must not be overwritten");
        let _ = fs::remove_dir_all(&addons);
        let _ = fs::remove_dir_all(&pack);
    }

    #[test]
    fn check_pack_names_what_would_shadow_it() {
        let addons = temp("check");
        fs::create_dir_all(addons.join("livecpk/root/Existing/Asset/effect")).unwrap();
        fs::write(
            addons.join("livecpk/root/Existing/Asset/effect/shared.ftex"),
            b"a",
        )
        .unwrap();
        fs::write(
            addons.join("sider.ini"),
            "[sider]\n\tcpk.root = \".\\livecpk\\root\\Existing\"\n\
             \tcpk.root = \".\\livecpk\\root\"\n",
        )
        .unwrap();
        let mine = addons.join("livecpk/root/Mine");
        fs::create_dir_all(mine.join("Asset/effect")).unwrap();
        fs::write(mine.join("Asset/effect/shared.ftex"), b"b").unwrap();
        let c = check_pack(&mine, &addons).unwrap();
        assert!(!c.registered);
        assert!(
            c.shadows.iter().any(|s| s.contains("shared.ftex")),
            "Existing comes first, so it shadows this file: {:?}",
            c.shadows
        );
        let _ = fs::remove_dir_all(&addons);
    }

    #[test]
    fn entries_report_order_existence_and_the_base_root() {
        let addons = temp("entries");
        fs::create_dir_all(addons.join("livecpk/root/One")).unwrap();
        fs::create_dir_all(addons.join("lib")).unwrap();
        fs::write(addons.join("lib/a.lua"), "x").unwrap();
        fs::write(
            addons.join("sider.ini"),
            "[sider]\n\
             \tcpk.root = \".\\livecpk\\root\\One\"\n\
             \t;cpk.root = \".\\livecpk\\root\\Gone\"  # switched off by hand\n\
             \tcpk.root = \".\\livecpk\\root\\Missing\"\n\
             \tcpk.root = \".\\livecpk\\root\"\n\
             \tlua.module = \"lib\\a.lua\"\n",
        )
        .unwrap();
        let e = entries(&addons).unwrap();
        assert_eq!(e.len(), 5);
        assert_eq!(e[0].key, "cpk.root");
        assert_eq!(e[0].order, 1, "orders count per key, not across keys");
        assert!(e[0].exists && e[0].enabled);
        assert!(!e[1].enabled, "a semicolon line is disabled, not missing");
        assert!(
            e[1].comment.contains("switched off"),
            "hand comments survive: {:?}",
            e[1].comment
        );
        assert!(!e[2].exists, "Missing is registered but absent");
        assert!(e[3].is_base, "the bare root is recognised");
        assert_eq!(e[4].key, "lua.module");
        assert!(e[4].exists, "lua.module resolves under the addons folder");
        let _ = fs::remove_dir_all(&addons);
    }

    #[test]
    fn edit_preview_changes_nothing_and_apply_touches_only_one_line() {
        let addons = temp("edit");
        fs::create_dir_all(addons.join("livecpk/root/One")).unwrap();
        let text = "[sider]\n\
            \tcpk.root = \".\\livecpk\\root\\One\"\n\
            \tcpk.root = \".\\livecpk\\root\"\n\
            \tlua.module = \"lib\\CommonLib.lua\"  # shared library\n";
        fs::write(addons.join("sider.ini"), text).unwrap();

        let p = edit(
            &addons,
            "cpk.root",
            ".\\livecpk\\root\\One",
            "disable",
            false,
        )
        .unwrap();
        assert!(!p.applied);
        assert!(p.backup.is_none(), "a preview must not create a backup");
        assert_eq!(p.before[0], "\tcpk.root = \".\\livecpk\\root\\One\"");
        assert_eq!(p.after[0], "\t;cpk.root = \".\\livecpk\\root\\One\"");
        assert_eq!(
            fs::read_to_string(addons.join("sider.ini")).unwrap(),
            text,
            "previewing must leave the file untouched"
        );

        let a = edit(
            &addons,
            "cpk.root",
            ".\\livecpk\\root\\One",
            "disable",
            true,
        )
        .unwrap();
        assert!(a.applied && a.backup.is_some());
        let now = fs::read_to_string(addons.join("sider.ini")).unwrap();
        // Everything that was not the target line is byte-identical, including
        // the hand-written comment on the lua.module line.
        let before: Vec<&str> = text.lines().collect();
        let after: Vec<&str> = now.lines().collect();
        assert_eq!(before.len(), after.len());
        let changed: Vec<usize> = (0..before.len())
            .filter(|&i| before[i] != after[i])
            .collect();
        assert_eq!(
            changed,
            vec![1],
            "only the requested line changed: {before:?} -> {after:?}"
        );
        assert_eq!(after[2], before[2]);
        assert_eq!(after[3], before[3]);
        // And re-enabling restores the original bytes exactly.
        edit(&addons, "cpk.root", ".\\livecpk\\root\\One", "enable", true).unwrap();
        assert_eq!(fs::read_to_string(addons.join("sider.ini")).unwrap(), text);
        let _ = fs::remove_dir_all(&addons);
    }

    #[test]
    fn edit_refuses_to_move_a_pack_past_the_base_root() {
        let addons = temp("pin");
        fs::write(
            addons.join("sider.ini"),
            "[sider]\n\
            \tcpk.root = \".\\livecpk\\root\\One\"\n\
            \tcpk.root = \".\\livecpk\\root\"\n",
        )
        .unwrap();
        let err = edit(&addons, "cpk.root", ".\\livecpk\\root\\One", "down", false).unwrap_err();
        assert!(err.to_string().contains("base root"), "{err}");
        assert!(
            edit(&addons, "cpk.root", ".\\livecpk\\root\\Two", "up", false).is_err(),
            "an unregistered value cannot be moved"
        );
        let _ = fs::remove_dir_all(&addons);
    }

    #[test]
    fn file_ops_refuse_to_clobber_and_refuse_to_escape() {
        let ws = temp("ops");
        fs::create_dir_all(ws.join("pack/sub")).unwrap();
        fs::write(ws.join("pack/keep.txt"), "mine").unwrap();

        assert!(
            create_file(&ws.join("pack/keep.txt")).is_err(),
            "no silent overwrite"
        );
        assert!(
            create_file(&ws.join("pack/new/deep.lua")).is_ok(),
            "parents are made"
        );
        assert!(
            rename(&ws.join("pack/keep.txt"), &ws.join("pack/new/deep.lua")).is_err(),
            "rename must not replace an existing file"
        );
        assert!(rename(&ws.join("pack/keep.txt"), &ws.join("pack/renamed.txt")).is_ok());
        assert!(!ws.join("pack/keep.txt").exists());

        assert!(remove(&ws.join("pack/renamed.txt"), &ws).is_ok());
        assert!(
            remove(&ws, &ws).is_err(),
            "the workspace itself is off limits"
        );
        let outside = std::env::temp_dir().join("fl27mm-studio-outside");
        fs::create_dir_all(&outside).unwrap();
        assert!(
            remove(&outside, &ws).is_err(),
            "nothing outside the workspace may be deleted"
        );
        assert!(outside.exists());
        let _ = fs::remove_dir_all(&outside);
        let _ = fs::remove_dir_all(&ws);
    }
}
