//! Tauri commands. Each one is a thin, serialisable wrapper over the fl27mm
//! core, so the UI and the CLI can never disagree about what an order means.

use std::collections::HashMap;
use std::collections::HashSet;
use std::path::{Path, PathBuf};
use std::sync::Mutex;
use std::time::SystemTime;

use base64::Engine;
use fl27mm::{binread, conflict, cpk, ftex, gamemap, ini, order, packs, pesdb, wesys};
use serde::Serialize;

type CmdResult<T> = Result<T, String>;

/// Session cache for the two reports that walk the whole install.
///
/// Keyed by the sider.ini's length and modification time, plus an explicit
/// refresh flag. It deliberately does NOT claim to notice deep file edits: a
/// directory's mtime does not change when a file three levels down is replaced.
/// Refresh always recomputes, and saving an order drops the entry.
#[derive(Default)]
struct Cache {
    order: Mutex<HashMap<String, (u64, SystemTime, OrderReport)>>,
    map: Mutex<HashMap<String, (u64, SystemTime, gamemap::GameMap)>>,
}

fn stamp(path: &Path) -> (u64, SystemTime) {
    match std::fs::metadata(path) {
        Ok(m) => (m.len(), m.modified().unwrap_or(SystemTime::UNIX_EPOCH)),
        Err(_) => (0, SystemTime::UNIX_EPOCH),
    }
}

fn e<E: std::fmt::Display>(err: E) -> String {
    format!("{err:#}")
}

#[derive(Serialize)]
pub struct Install {
    pub game: String,
    pub addons: String,
    pub ini: String,
    pub packs_root: String,
}

/// Look for a Sider install. `remembered` is what the user last chose by hand:
/// detection alone missed installs outside a short list of drive-and-folder
/// combinations, and a folder picked once was forgotten on the next launch, so
/// the app looked like it refused to register the game. Both are fixed by
/// searching every mounted drive and by taking the remembered path as input.
#[tauri::command(async)]
fn detect_game(remembered: Vec<String>) -> Vec<fl27mm::install::Install> {
    let extra: Vec<PathBuf> = remembered.iter().map(PathBuf::from).collect();
    fl27mm::install::detect(&extra)
}

#[derive(Serialize)]
pub struct ScanReport {
    pub ini: String,
    pub packs: usize,
    pub modules: usize,
    pub disabled_packs: usize,
    pub disabled_modules: usize,
    pub missing: Vec<String>,
    pub duplicates: Vec<String>,
    pub lua_enabled: bool,
    pub luajit_enabled: bool,
}

#[tauri::command(async)]
fn scan(game: String) -> CmdResult<ScanReport> {
    let addons = Path::new(&game).join("SiderAddons");
    let path = addons.join("sider.ini");
    let parsed = ini::Ini::read(&path).map_err(e)?;
    let active_packs = parsed.active("cpk.root");
    let active_mods = parsed.active("lua.module");

    let mut missing = Vec::new();
    let mut duplicates = Vec::new();
    let mut seen = HashSet::new();
    for entry in &active_packs {
        if !seen.insert(entry.value.to_lowercase()) {
            duplicates.push(format!("pack {}", entry.value));
        }
        if !order::resolve(&addons, &entry.value).is_dir() {
            missing.push(format!("pack {}", entry.value));
        }
    }
    let mut mseen = HashSet::new();
    for entry in &active_mods {
        if !mseen.insert(entry.value.to_lowercase()) {
            duplicates.push(format!("module {}", entry.value));
        }
        if !addons
            .join("modules")
            .join(entry.value.replace('\\', "/"))
            .is_file()
        {
            missing.push(format!("module {}", entry.value));
        }
    }
    let flag = |key: &str| {
        parsed
            .active(key)
            .first()
            .map(|v| v.value.trim() == "1")
            .unwrap_or(false)
    };

    Ok(ScanReport {
        ini: path.to_string_lossy().into_owned(),
        packs: active_packs.len(),
        modules: active_mods.len(),
        disabled_packs: parsed.all("cpk.root").len() - active_packs.len(),
        disabled_modules: parsed.all("lua.module").len() - active_mods.len(),
        missing,
        duplicates,
        lua_enabled: flag("lua.enabled"),
        luajit_enabled: flag("luajit.ext.enabled"),
    })
}

#[derive(Serialize, Clone)]
pub struct PackRow {
    pub value: String,
    pub name: String,
    pub kind: String,
    pub total: usize,
    pub surviving: usize,
    pub dead: bool,
    pub exists: bool,
    pub alternative: bool,
    pub blockers: Vec<Blocker>,
}

#[derive(Serialize, Clone)]
pub struct Blocker {
    pub rel: String,
    pub keys: usize,
}

#[derive(Serialize, Clone)]
pub struct OrderReport {
    pub rows: Vec<PackRow>,
    pub modules: Vec<String>,
    pub alive: usize,
    pub partial: usize,
    pub dead: usize,
    pub unregistered: usize,
}

/// The order as the game will actually resolve it: first-wins, key by key.
#[tauri::command(async)]
fn order_report(
    ini_path: String,
    addons: String,
    refresh: Option<bool>,
    cache: tauri::State<Cache>,
) -> CmdResult<OrderReport> {
    let key = format!("{}|{}", ini_path.to_lowercase(), addons.to_lowercase());
    let mark = stamp(Path::new(&ini_path));
    if !refresh.unwrap_or(false) {
        if let Some((len, mtime, report)) = cache.order.lock().unwrap().get(&key) {
            if (*len, *mtime) == mark {
                return Ok(report.clone());
            }
        }
    }
    let addons = PathBuf::from(&addons);
    let parsed = ini::Ini::read(Path::new(&ini_path)).map_err(e)?;
    let shadows = order::analyse(&addons, &parsed);
    let entries = parsed.active("cpk.root");

    let discovered = packs::discover(&addons.join("livecpk").join("root"));
    let by_rel: std::collections::HashMap<String, &packs::Pack> = discovered
        .iter()
        .map(|p| (p.rel.to_lowercase(), p))
        .collect();
    // ini values are ".\livecpk\root\<rel>"; discovery reports "<rel>". Compare
    // like with like, or every pack on disk looks unregistered.
    const PREFIX: &str = ".\\livecpk\\root\\";
    let active_rel: HashSet<String> = entries
        .iter()
        .map(|v| v.value.to_lowercase())
        .map(|v| v.strip_prefix(PREFIX).map(str::to_string).unwrap_or(v))
        .collect();
    let unregistered = discovered
        .iter()
        .filter(|p| !active_rel.contains(&p.rel.to_lowercase()))
        .count();

    let mut rows = Vec::new();
    for (i, entry) in entries.iter().enumerate() {
        let shadow = shadows.get(i);
        let rel = entry.value.to_lowercase();
        let rel = rel.strip_prefix(PREFIX).unwrap_or(&rel);
        let pack = by_rel.get(rel);
        let total = shadow.map(|s| s.total).unwrap_or(0);
        let surviving = shadow.map(|s| s.surviving).unwrap_or(0);
        rows.push(PackRow {
            value: entry.value.clone(),
            name: pack
                .map(|p| p.name.clone())
                .unwrap_or_else(|| entry.value.rsplit('\\').next().unwrap_or("").to_string()),
            kind: pack
                .map(|p| p.kind.label().to_string())
                .unwrap_or_else(|| "unknown".into()),
            alternative: pack.map(|p| p.kind.is_alternative()).unwrap_or(false),
            total,
            surviving,
            dead: shadow.map(|s| s.dead()).unwrap_or(false),
            exists: order::resolve(&addons, &entry.value).is_dir(),
            blockers: shadow
                .map(|s| {
                    s.blockers
                        .iter()
                        .take(3)
                        .map(|(rel, keys)| Blocker {
                            rel: rel.clone(),
                            keys: *keys,
                        })
                        .collect()
                })
                .unwrap_or_default(),
        });
    }
    let dead = rows.iter().filter(|r| r.dead).count();
    let partial = rows
        .iter()
        .filter(|r| !r.dead && r.surviving < r.total)
        .count();
    let report = OrderReport {
        alive: rows.len() - dead - partial,
        partial,
        dead,
        unregistered,
        modules: parsed
            .active("lua.module")
            .iter()
            .map(|v| v.value.clone())
            .collect(),
        rows,
    };
    cache
        .order
        .lock()
        .unwrap()
        .insert(key, (mark.0, mark.1, report.clone()));
    Ok(report)
}

#[derive(Serialize)]
pub struct SaveReport {
    pub backup: String,
    pub written: String,
    pub entries: usize,
}

/// Write a new cpk.root order. Backs the ini up first and refuses to write an
/// order that drops or invents entries.
#[tauri::command(async)]
fn save_order(
    ini_path: String,
    addons: String,
    values: Vec<String>,
    cache: tauri::State<Cache>,
) -> CmdResult<SaveReport> {
    let path = Path::new(&ini_path);
    let mut parsed = ini::Ini::read(path).map_err(e)?;
    let current = parsed.all("cpk.root");
    if values.len() != current.len() {
        return Err(format!(
            "order has {} entries, the ini has {}",
            values.len(),
            current.len()
        ));
    }
    let before: HashSet<String> = current.iter().map(|v| v.value.to_lowercase()).collect();
    let after: HashSet<String> = values.iter().map(|v| v.to_lowercase()).collect();
    if before != after {
        return Err("the new order must contain exactly the same entries".into());
    }

    let mut reordered = Vec::with_capacity(values.len());
    for value in &values {
        let source = current
            .iter()
            .find(|v| v.value.eq_ignore_ascii_case(value))
            .ok_or_else(|| format!("no ini entry for {value}"))?;
        let mut clone = (*source).clone();
        clone.value = value.clone();
        reordered.push(clone);
    }

    let stamp = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    let backup = path.with_file_name(format!("sider.ini.bak-{stamp}"));
    std::fs::copy(path, &backup).map_err(e)?;
    parsed.replace_ordered("cpk.root", reordered);
    parsed.write(path).map_err(e)?;
    cache.order.lock().unwrap().clear();
    let _ = addons;
    Ok(SaveReport {
        backup: backup.to_string_lossy().into_owned(),
        written: path.to_string_lossy().into_owned(),
        entries: values.len(),
    })
}

#[derive(Serialize)]
pub struct ConflictPair {
    pub a: String,
    pub b: String,
    pub keys: usize,
}

#[derive(Serialize)]
pub struct ConflictReport {
    pub packs: usize,
    pub keys: usize,
    pub shared: usize,
    pub identical: usize,
    pub differing: usize,
    pub pairs: Vec<ConflictPair>,
    pub examples: Vec<String>,
}

#[tauri::command(async)]
fn conflict_report(root: String) -> CmdResult<ConflictReport> {
    let found = packs::discover(Path::new(&root));
    if found.is_empty() {
        return Err(format!("no packs found under {root}"));
    }
    let idx = conflict::index(&found);
    let keys = idx.len();
    let c = conflict::analyse(&found, &idx);
    let mut pairs: Vec<_> = c.pairs.iter().collect();
    pairs.sort_by(|a, b| b.1.cmp(a.1));
    Ok(ConflictReport {
        packs: found.len(),
        keys,
        shared: c.shared,
        identical: c.identical,
        differing: c.differing,
        pairs: pairs
            .iter()
            .take(60)
            .map(|((a, b), n)| ConflictPair {
                a: found[*a].rel.clone(),
                b: found[*b].rel.clone(),
                keys: **n,
            })
            .collect(),
        examples: c.examples,
    })
}

#[derive(Serialize)]
pub struct CpkEntry {
    pub path: String,
    pub size: u64,
    pub extract_size: u64,
    pub compressed: bool,
    pub id: u64,
}

#[derive(Serialize)]
pub struct CpkListing {
    pub archive: String,
    pub file_size: u64,
    pub content_offset: u64,
    pub align: u64,
    pub entries: Vec<CpkEntry>,
}

#[tauri::command(async)]
fn cpk_list(archive: String) -> CmdResult<CpkListing> {
    let path = Path::new(&archive);
    let opened = cpk::Cpk::open(path).map_err(e)?;
    let get = |k: &str| opened.header.get(k).map(|v| v.as_u64()).unwrap_or(0);
    Ok(CpkListing {
        archive: archive.clone(),
        file_size: std::fs::metadata(path).map_err(e)?.len(),
        content_offset: opened.content_offset,
        align: get("Align"),
        entries: opened
            .files
            .iter()
            .map(|f| CpkEntry {
                path: f.path(),
                size: f.size,
                extract_size: f.extract_size,
                compressed: f.compressed(),
                id: f.id,
            })
            .collect(),
    })
}

#[tauri::command(async)]
fn cpk_extract(archive: String, dest: String, filter: Option<String>) -> CmdResult<usize> {
    let opened = cpk::Cpk::open(Path::new(&archive)).map_err(e)?;
    let dest = PathBuf::from(dest);
    let mut done = 0;
    for f in &opened.files {
        if let Some(text) = &filter {
            if !text.is_empty() && !f.path().contains(text.as_str()) {
                continue;
            }
        }
        let out = dest.join(f.path().replace('/', std::path::MAIN_SEPARATOR_STR));
        if let Some(parent) = out.parent() {
            std::fs::create_dir_all(parent).map_err(e)?;
        }
        std::fs::write(&out, opened.read_file(f).map_err(e)?).map_err(e)?;
        done += 1;
    }
    Ok(done)
}

#[derive(Serialize)]
pub struct PackResult {
    pub files: usize,
    pub bytes: u64,
    pub reread: usize,
    pub packed: usize,
    pub stored: usize,
}

#[tauri::command(async)]
fn cpk_pack(src: String, dest: String, compress: Option<bool>) -> CmdResult<PackResult> {
    let files =
        cpk::pack(Path::new(&src), Path::new(&dest), compress.unwrap_or(true)).map_err(e)?;
    let back = cpk::Cpk::open(Path::new(&dest)).map_err(e)?;
    let packed = back.files.iter().filter(|f| f.compressed()).count();
    Ok(PackResult {
        files,
        bytes: std::fs::metadata(&dest).map_err(e)?.len(),
        reread: back.files.len(),
        packed,
        stored: back.files.len() - packed,
    })
}

#[derive(Serialize)]
pub struct TexInfo {
    pub path: String,
    pub width: u32,
    pub height: u32,
    pub depth: u32,
    pub format: String,
    pub mips: usize,
    pub texture_type: u32,
    pub version: String,
    pub bytes: u64,
}

#[tauri::command(async)]
fn tex_info(path: String) -> CmdResult<TexInfo> {
    let t = ftex::Ftex::read(Path::new(&path)).map_err(e)?;
    Ok(TexInfo {
        path,
        width: t.width,
        height: t.height,
        depth: t.depth,
        format: t.format.name().to_string(),
        mips: t.mips.len(),
        texture_type: t.texture_type,
        version: format!("{:.2}", f32::from_bits(t.version)),
        bytes: t.mips.iter().map(|m| m.data.len() as u64).sum(),
    })
}

/// A PNG data URL for the chosen mip, so the UI can show any texture without
/// writing a temporary file.
#[tauri::command(async)]
fn tex_preview(path: String, level: Option<usize>) -> CmdResult<String> {
    let t = ftex::Ftex::read(Path::new(&path)).map_err(e)?;
    let (w, h, rgba) = t.to_rgba(level.unwrap_or(0)).map_err(e)?;
    let mut buf = Vec::new();
    {
        let mut encoder = png::Encoder::new(&mut buf, w, h);
        encoder.set_color(png::ColorType::Rgba);
        encoder.set_depth(png::BitDepth::Eight);
        let mut writer = encoder.write_header().map_err(e)?;
        writer.write_image_data(&rgba).map_err(e)?;
    }
    Ok(format!(
        "data:image/png;base64,{}",
        base64::engine::general_purpose::STANDARD.encode(buf)
    ))
}

#[derive(Serialize)]
pub struct ConvertRow {
    pub file: String,
    pub ok: bool,
    pub detail: String,
}

#[tauri::command(async)]
fn tex_convert(input: String, out: String, kind: String) -> CmdResult<Vec<ConvertRow>> {
    let tag: u32 = match kind.as_str() {
        "normal" => 9,
        "material" => 1,
        "cube" => 7,
        _ => 3,
    };
    let src = PathBuf::from(&input);
    let dest = PathBuf::from(&out);
    let mut files = Vec::new();
    if src.is_dir() {
        let mut stack = vec![src.clone()];
        while let Some(d) = stack.pop() {
            for entry in std::fs::read_dir(&d).map_err(e)?.flatten() {
                let p = entry.path();
                if p.is_dir() {
                    stack.push(p);
                } else {
                    let ext = p
                        .extension()
                        .unwrap_or_default()
                        .to_string_lossy()
                        .to_lowercase();
                    if ext == "ftex" || ext == "dds" {
                        files.push(p);
                    }
                }
            }
        }
        files.sort();
    } else {
        files.push(src.clone());
    }
    let base = if src.is_dir() {
        src.clone()
    } else {
        src.parent().unwrap_or(Path::new(".")).to_path_buf()
    };

    let mut rows = Vec::new();
    for p in files {
        let rel = p
            .strip_prefix(&base)
            .unwrap_or(&p)
            .to_string_lossy()
            .into_owned();
        let ext = p
            .extension()
            .unwrap_or_default()
            .to_string_lossy()
            .to_lowercase();
        let target = dest
            .join(p.strip_prefix(&base).unwrap_or(&p))
            .with_extension(if ext == "ftex" { "dds" } else { "ftex" });
        let result = (|| -> Result<String, String> {
            if let Some(parent) = target.parent() {
                std::fs::create_dir_all(parent).map_err(e)?;
            }
            if ext == "ftex" {
                let t = ftex::to_dds_file(&p, &target).map_err(e)?;
                Ok(format!(
                    "{}x{} {} {} mips",
                    t.width,
                    t.height,
                    t.format.name(),
                    t.mips.len()
                ))
            } else {
                let bytes = std::fs::read(&p).map_err(e)?;
                let mut t = ftex::Ftex::from_dds(&bytes).map_err(e)?;
                t.texture_type = tag;
                t.write_ftex(&target).map_err(e)?;
                Ok(format!(
                    "{}x{} {} {} mips",
                    t.width,
                    t.height,
                    t.format.name(),
                    t.mips.len()
                ))
            }
        })();
        match result {
            Ok(detail) => rows.push(ConvertRow {
                file: rel,
                ok: true,
                detail,
            }),
            Err(detail) => rows.push(ConvertRow {
                file: rel,
                ok: false,
                detail,
            }),
        }
    }
    Ok(rows)
}

#[derive(Serialize)]
pub struct ContainerRow {
    pub file: String,
    pub framing: String,
    pub file_size: usize,
    pub body_size: usize,
    pub exact: bool,
    pub level: Option<i32>,
    pub error: Option<String>,
}

#[tauri::command(async)]
fn container_report(input: String) -> CmdResult<Vec<ContainerRow>> {
    let src = PathBuf::from(&input);
    let mut files = Vec::new();
    if src.is_dir() {
        let mut stack = vec![src.clone()];
        while let Some(d) = stack.pop() {
            for entry in std::fs::read_dir(&d).map_err(e)?.flatten() {
                let p = entry.path();
                if p.is_dir() {
                    stack.push(p);
                } else {
                    files.push(p);
                }
            }
        }
        files.sort();
    } else {
        files.push(src.clone());
    }
    let base = if src.is_dir() {
        src.clone()
    } else {
        src.parent().unwrap_or(Path::new(".")).to_path_buf()
    };
    let mut rows = Vec::new();
    for p in files {
        let rel = p
            .strip_prefix(&base)
            .unwrap_or(&p)
            .to_string_lossy()
            .into_owned();
        let raw = match std::fs::read(&p) {
            Ok(r) => r,
            Err(err) => {
                rows.push(ContainerRow {
                    file: rel,
                    framing: "-".into(),
                    file_size: 0,
                    body_size: 0,
                    exact: false,
                    level: None,
                    error: Some(e(err)),
                });
                continue;
            }
        };
        match wesys::decode(&raw) {
            Ok(mut f) => {
                let framing = f.kind.name().to_string();
                let body_size = f.body.len();
                let file_size = raw.len();
                match wesys::encode(&mut f) {
                    Ok(_) => rows.push(ContainerRow {
                        file: rel,
                        framing,
                        file_size,
                        body_size,
                        exact: f.exact,
                        level: f.level,
                        error: None,
                    }),
                    Err(err) => rows.push(ContainerRow {
                        file: rel,
                        framing,
                        file_size,
                        body_size,
                        exact: false,
                        level: None,
                        error: Some(e(err)),
                    }),
                }
            }
            Err(err) => rows.push(ContainerRow {
                file: rel,
                framing: "-".into(),
                file_size: raw.len(),
                body_size: 0,
                exact: false,
                level: None,
                error: Some(e(err)),
            }),
        }
    }
    Ok(rows)
}

#[tauri::command(async)]
fn container_unwrap(input: String, dest: String) -> CmdResult<usize> {
    let f = wesys::decode(&std::fs::read(&input).map_err(e)?).map_err(e)?;
    if f.kind == wesys::Kind::Unknown {
        return Err(
            "unidentified framing; refusing to write a body this codec cannot interpret".into(),
        );
    }
    if let Some(parent) = Path::new(&dest).parent() {
        std::fs::create_dir_all(parent).map_err(e)?;
    }
    std::fs::write(&dest, &f.body).map_err(e)?;
    Ok(f.body.len())
}

#[tauri::command(async)]
fn container_rewrap(body: String, original: String, dest: String) -> CmdResult<ContainerRow> {
    let raw = std::fs::read(&original).map_err(e)?;
    let mut f = wesys::decode(&raw).map_err(e)?;
    f.body = std::fs::read(&body).map_err(e)?;
    let out = wesys::encode(&mut f).map_err(e)?;
    if let Some(parent) = Path::new(&dest).parent() {
        std::fs::create_dir_all(parent).map_err(e)?;
    }
    std::fs::write(&dest, &out).map_err(e)?;
    Ok(ContainerRow {
        file: dest,
        framing: f.kind.name().to_string(),
        file_size: out.len(),
        body_size: f.body.len(),
        exact: f.exact,
        level: f.level,
        error: None,
    })
}

#[derive(Serialize)]
pub struct TableRow {
    pub file: String,
    pub ok: bool,
    pub status: String,
    pub reason: String,
}

#[tauri::command(async)]
fn pesdb_report(dir: String) -> CmdResult<Vec<TableRow>> {
    let root = PathBuf::from(&dir);
    let mut stack = vec![root.clone()];
    let mut rows = Vec::new();
    while let Some(d) = stack.pop() {
        for entry in std::fs::read_dir(&d).map_err(e)?.flatten() {
            let p = entry.path();
            if p.is_dir() {
                stack.push(p);
                continue;
            }
            let name = p
                .file_name()
                .unwrap_or_default()
                .to_string_lossy()
                .to_string();
            if !name.ends_with(".bin") || !p.to_string_lossy().contains("pesdb") {
                continue;
            }
            let v = pesdb::validate(&p);
            rows.push(TableRow {
                file: p
                    .strip_prefix(&root)
                    .unwrap_or(&p)
                    .to_string_lossy()
                    .into_owned(),
                ok: v.ok,
                status: match v.status {
                    pesdb::Status::Ok => "ok",
                    pesdb::Status::BadStride => "badstride",
                    pesdb::Status::Unrecognised => "unrecognised",
                    pesdb::Status::Unreadable => "unreadable",
                }
                .to_string(),
                reason: v.reason,
            });
        }
    }
    rows.sort_by(|a, b| a.file.cmp(&b.file));
    Ok(rows)
}

#[tauri::command]
async fn game_map(
    game: String,
    refresh: Option<bool>,
    cache: tauri::State<'_, Cache>,
) -> CmdResult<gamemap::GameMap> {
    let path = PathBuf::from(&game);
    let key = game.to_lowercase();
    let mark = stamp(&path.join("SiderAddons").join("sider.ini"));
    if !refresh.unwrap_or(false) {
        if let Some((len, mtime, map)) = cache.map.lock().unwrap().get(&key) {
            if (*len, *mtime) == mark {
                return Ok(map.clone());
            }
        }
    }
    let built = tauri::async_runtime::spawn_blocking(move || gamemap::build(&path))
        .await
        .map_err(e)?;
    cache
        .map
        .lock()
        .unwrap()
        .insert(key, (mark.0, mark.1, built.clone()));
    Ok(built)
}

#[tauri::command]
async fn archive_map(archive: String, depth: Option<usize>) -> CmdResult<gamemap::ArchiveMap> {
    let path = PathBuf::from(archive);
    let depth = depth.unwrap_or(3);
    tauri::async_runtime::spawn_blocking(move || gamemap::archive_map(&path, depth))
        .await
        .map_err(e)?
}

#[tauri::command(async)]
fn bin_read(file: String) -> CmdResult<binread::BinReport> {
    binread::read(Path::new(&file)).map_err(e)
}

#[tauri::command(async)]
fn bin_section(file: String, index: usize, bytes: Option<usize>) -> CmdResult<String> {
    let data = binread::section_bytes(Path::new(&file), index).map_err(e)?;
    Ok(binread::hexdump(&data, 0, bytes.unwrap_or(512)))
}

/// Hex of the inflated body, so a record can be read at its real offset rather
/// than at its position inside the compressed stream.
#[tauri::command(async)]
fn bin_hex(file: String, at: Option<usize>, bytes: Option<usize>) -> CmdResult<String> {
    let raw = std::fs::read(&file).map_err(e)?;
    let body = wesys::decode(&raw).map_err(e)?.body;
    Ok(binread::hexdump(
        &body,
        at.unwrap_or(0),
        bytes.unwrap_or(512),
    ))
}

#[derive(serde::Serialize)]
pub struct SectionBlock {
    pub name: String,
    pub bytes: usize,
    /// `Some((rows, row_bytes))` when the block reads as a parameter table.
    pub table: Option<(usize, usize)>,
    pub values: Vec<f32>,
    pub plausible_floats: usize,
}

/// Read one `.o` block as the parameter table it usually is: a count, a row
/// width, and the float values the bytes support.
#[tauri::command(async)]
fn bin_section_table(file: String, index: usize) -> CmdResult<SectionBlock> {
    let path = Path::new(&file);
    let data = binread::section_bytes(path, index).map_err(e)?;
    let report = binread::read(path).map_err(e)?;
    let name = report
        .sections
        .as_ref()
        .and_then(|t| t.sections.get(index))
        .map(|s| s.name.clone())
        .unwrap_or_default();
    let plausible_floats = data
        .chunks_exact(4)
        .map(|c| f32::from_le_bytes([c[0], c[1], c[2], c[3]]))
        .filter(|v| v.is_finite() && (*v == 0.0 || (1e-4..=1e9).contains(&v.abs())))
        .count();
    let tidy = fl27mm::structure::infer_block(&data);
    let found = match tidy {
        Some((count, row, values)) => Some((row, count, values)),
        // Not the tidy count-then-rows shape: look for a repeating row width
        // that makes the bytes read as parameters anyway.
        None => fl27mm::structure::best_row_width(&data).map(|(row, rows)| {
            let values: Vec<f32> = data
                .chunks_exact(4)
                .map(|c| f32::from_le_bytes([c[0], c[1], c[2], c[3]]))
                .collect();
            (row, rows, values)
        }),
    };
    match found {
        Some((row, rows, values)) => Ok(SectionBlock {
            name,
            bytes: data.len(),
            table: Some((rows, row)),
            values: values.into_iter().take(1024).collect(),
            plausible_floats,
        }),
        None => Ok(SectionBlock {
            name,
            bytes: data.len(),
            table: None,
            values: Vec::new(),
            plausible_floats,
        }),
    }
}

#[tauri::command(async)]
fn explain_path(rel: String) -> gamemap::Info {
    gamemap::describe(&rel)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
// ---------------------------------------------------------------- mod studio
//
// Thin wrappers over fl27mm::studio, like everything else here. The install
// command is the only one that touches the live setup, and the UI gates it
// behind a confirm; the core itself refuses an existing target rather than
// overwriting it, so a double click cannot destroy an installed pack.
#[tauri::command(async)]
fn studio_tree(root: String) -> CmdResult<Vec<fl27mm::studio::Node>> {
    fl27mm::studio::tree(Path::new(&root)).map_err(e)
}

#[tauri::command(async)]
fn studio_read(path: String) -> CmdResult<fl27mm::studio::TextFile> {
    fl27mm::studio::read_text(Path::new(&path)).map_err(e)
}

#[tauri::command(async)]
fn studio_write(path: String, text: String) -> CmdResult<u64> {
    fl27mm::studio::write_text(Path::new(&path), &text)
        .map(|n| n as u64)
        .map_err(e)
}

#[tauri::command(async)]
fn studio_new_pack(
    addons: String,
    name: String,
    kind: String,
) -> CmdResult<fl27mm::studio::Scaffold> {
    fl27mm::studio::new_pack(Path::new(&addons), &name, &kind).map_err(e)
}

#[tauri::command(async)]
fn studio_check_pack(dir: String, addons: String) -> CmdResult<fl27mm::studio::PackCheck> {
    fl27mm::studio::check_pack(Path::new(&dir), Path::new(&addons)).map_err(e)
}

#[tauri::command(async)]
fn studio_install(src: String, addons: String) -> CmdResult<fl27mm::studio::Install> {
    fl27mm::studio::install_pack(Path::new(&src), Path::new(&addons)).map_err(e)
}

#[derive(Serialize)]
struct KindHint {
    kind: String,
    hint: String,
    hook: String,
    layout: Vec<String>,
}

#[tauri::command(async)]
fn studio_kinds() -> Vec<KindHint> {
    ["cpk", "lua", "mesh", "generic"]
        .iter()
        .map(|k| {
            let (hint, hook, layout) = fl27mm::studio::kind_hint(k);
            KindHint {
                kind: (*k).to_string(),
                hint: hint.to_string(),
                hook: hook.to_string(),
                layout: layout.iter().map(|s| (*s).to_string()).collect(),
            }
        })
        .collect()
}

// The registered list in sider.ini *is* the mod order. `apply: false` is a
// preview: the core returns the exact lines it would change and writes
// nothing, so the UI can show the diff and ask before touching the file.

#[tauri::command(async)]
fn studio_entries(addons: String) -> CmdResult<Vec<fl27mm::studio::ModEntry>> {
    fl27mm::studio::entries(Path::new(&addons)).map_err(e)
}

#[tauri::command(async)]
fn studio_edit(
    addons: String,
    key: String,
    value: String,
    mode: String,
    apply: bool,
) -> CmdResult<fl27mm::studio::Edit> {
    fl27mm::studio::edit(Path::new(&addons), &key, &value, &mode, apply).map_err(e)
}

#[tauri::command(async)]
fn studio_create(path: String) -> CmdResult<u64> {
    fl27mm::studio::create_file(Path::new(&path)).map_err(e)
}

#[tauri::command(async)]
fn studio_rename(from: String, to: String) -> CmdResult<String> {
    fl27mm::studio::rename(Path::new(&from), Path::new(&to)).map_err(e)
}

#[tauri::command(async)]
fn studio_remove(path: String, workspace: String) -> CmdResult<String> {
    fl27mm::studio::remove(Path::new(&path), Path::new(&workspace)).map_err(e)
}

/// Open the OS file manager with the item selected. The one thing a mod maker
/// reaches for constantly and the app could not do before.
#[tauri::command(async)]
fn studio_reveal(path: String) -> CmdResult<()> {
    let p = Path::new(&path);
    if !p.exists() {
        return Err(format!("{path} no longer exists"));
    }
    std::process::Command::new("explorer")
        .arg(format!("/select,{}", p.display()))
        .spawn()
        .map(|_| ())
        .map_err(e)
}

/// Write bytes back into a table at a body offset. The core re-reads the file
/// and refuses if anything outside the requested window moved.
#[tauri::command]
fn bin_patch(file: String, offset: usize, hex: String) -> CmdResult<serde_json::Value> {
    let bytes: Option<Vec<u8>> = hex
        .as_bytes()
        .chunks(2)
        .map(|c| {
            std::str::from_utf8(c)
                .ok()
                .and_then(|s| u8::from_str_radix(s, 16).ok())
        })
        .collect();
    let Some(bytes) = bytes else {
        return Err(format!("{hex:?} is not an even number of hex digits"));
    };
    if bytes.is_empty() {
        return Err("nothing to write".to_string());
    }
    // Editing a shipped table is not reversible by the app alone, so keep the
    // original first rather than trusting the caller to have done it.
    let src = Path::new(&file);
    let backup = src.with_extension("bin.fl27mm-backup");
    if !backup.exists() {
        std::fs::copy(src, &backup).map_err(e)?;
    }
    let (changed, len) = fl27mm::binread::patch(src, offset, &bytes).map_err(e)?;
    Ok(serde_json::json!({ "changed": changed, "size": len, "backup": backup.to_string_lossy() }))
}

/// List editable assets under a folder, grouped by family. Bounded so a scan of
/// a 200 GB install cannot hang the UI.
#[tauri::command]
fn asset_list(root: String, limit: Option<usize>) -> CmdResult<serde_json::Value> {
    let cap = limit.unwrap_or(400);
    let mut out = Vec::new();
    for p in fl27mm::fsutil::files(Path::new(&root)) {
        let Some(e) = fl27mm::assets::entry(&p) else {
            continue;
        };
        out.push(e);
        if out.len() >= cap {
            break;
        }
    }
    Ok(serde_json::json!({ "items": out, "shown": out.len(), "cap": cap }))
}

/// Replace a texture from RGBA8 handed back by the WebView, which already
/// decodes PNG and JPEG. The core refuses unless the size matches the file.
#[tauri::command]
fn asset_replace(
    file: String,
    width: u32,
    height: u32,
    bytes: Vec<u8>,
) -> CmdResult<fl27mm::assets::Report> {
    fl27mm::assets::replace(Path::new(&file), &bytes, width, height).map_err(e)
}

/// Render a model with its own bound textures, so an edit can be seen on the
/// asset rather than only in a flat preview.
#[tauri::command]
fn asset_preview(model: String, view: String, size: usize) -> CmdResult<serde_json::Value> {
    use fl27mm::render::{self, Camera, Mode, Texture};
    let path = Path::new(&model);
    let mut models = render::load_scene(path).map_err(e)?;
    render::keep_texturable(&mut models);
    let maps = render::Maps::load_from(
        &models,
        &render::texture_roots(path),
        &render::base_archives(path),
    );
    let cam = match view.as_str() {
        "front" => Camera::front(),
        "back" => Camera::back(),
        "top" => Camera::top(),
        "profile" => Camera::profile(),
        _ => Camera::three_quarter(),
    };
    let fallback = render::skin_for(path);
    let held: Option<Texture> =
        fallback
            .as_ref()
            .map(|(rgba, w, h)| Texture { rgba, w: *w, h: *h });
    let px = render::render_scene_maps(
        &models,
        held.as_ref(),
        Some(&maps),
        &cam,
        Mode::Textured,
        size,
        size,
    );
    let mut buf = Vec::new();
    {
        let mut enc = png::Encoder::new(&mut buf, size as u32, size as u32);
        enc.set_color(png::ColorType::Rgba);
        enc.set_depth(png::BitDepth::Eight);
        enc.write_header()
            .map_err(e)?
            .write_image_data(&px)
            .map_err(e)?;
    }
    let (found, named) = maps.stats();
    Ok(serde_json::json!({
        "image": format!("data:image/png;base64,{}", base64::engine::general_purpose::STANDARD.encode(buf)),
        "files": models.len(),
        "meshes": render::all_meshes(&models).len(),
        "vertices": render::all_meshes(&models).iter().map(|x| x.positions.len()).sum::<usize>(),
        "maps": format!("{found}/{named} colour maps resolved"),
    }))
}

/// Read a rig chain file: a `.ask` skeleton or a `.frig` rig. Returns the bones
/// or units so the app can show what a clip is actually driving, and refuses a
/// file whose header does not satisfy its own decoder rather than showing a
/// half-read structure.
#[tauri::command]
fn rig_read(path: String) -> CmdResult<serde_json::Value> {
    use fl27mm::{ask, frig};
    let p = Path::new(&path);
    let bytes = std::fs::read(p).map_err(e)?;
    let ext = p
        .extension()
        .map(|x| x.to_string_lossy().to_lowercase())
        .unwrap_or_default();
    match ext.as_str() {
        "ask" => {
            let s = ask::Skeleton::parse(&bytes).map_err(e)?;
            let order = s.draw_order().map_err(e)?;
            Ok(serde_json::json!({
                "kind": "skeleton",
                "bones": s.bones.iter().map(|b| serde_json::json!({
                    "name": b.name, "parent": b.parent,
                    "position": b.position, "rotation": b.rotation,
                })).collect::<Vec<_>>(),
                "basis": if s.identity_basis() { "identity" } else { "render" },
                "reachable": order.len(),
            }))
        }
        "frig" => {
            let r = frig::Rig::parse(&bytes).map_err(e)?;
            // If the matching skeleton sits beside the rig, resolve the direct
            // units to bone names; without it the index is a number with no
            // meaning to the reader. The install uses two pairings: a plain
            // same-stem pair, and the engine's `<x>_skel.frig` +
            // `<x>_anim_skel.ask`, so both are tried.
            let stem = p
                .file_stem()
                .map(|s| s.to_string_lossy().into_owned())
                .unwrap_or_default();
            let candidates = [
                p.with_extension("ask"),
                p.with_file_name(format!("{stem}_anim_skel.ask")),
                p.with_file_name(format!(
                    "{}_anim_skel.ask",
                    stem.strip_suffix("_skel").unwrap_or(&stem)
                )),
            ];
            let mut sk = None;
            for side in candidates.iter() {
                if let Ok(s) = ask::Skeleton::read(side) {
                    sk = Some(s);
                    break;
                }
            }
            Ok(serde_json::json!({
                "kind": "rig",
                "name": r.name,
                "units": r.unit_count,
                "segments": r.segment_count,
                "skeleton": sk.as_ref().map(|s| s.bones.len()),
                "unitList": r.units.iter().map(|u| serde_json::json!({
                    "type": u.kind.name(),
                    "tracks": u.track_count,
                    "bones": u.kind.bones_driven(),
                    "direct": u.kind.is_direct(),
                    "bone": u.skel_index.and_then(|i| sk.as_ref().and_then(|s|
                        s.bones.get(i as usize).map(|b| b.name.clone()))),
                    "boneIndex": u.skel_index,
                })).collect::<Vec<_>>(),
            }))
        }
        other => Err(format!("{other} is not a skeleton or rig file")),
    }
}

/// Decode a `.gani` clip into its units, segments and keyframes, and report
/// the frame rate. The walk is validated before anything is returned, so a
/// clip whose blobs do not tile comes back as an error rather than as numbers
/// that look plausible and are not.
#[tauri::command]
fn gani_read(path: String) -> CmdResult<serde_json::Value> {
    use fl27mm::gani;
    let p = Path::new(&path);
    let bytes = std::fs::read(p).map_err(e)?;
    let clip = gani::Clip::parse(&bytes).map_err(e)?;
    let units = gani::walk(&bytes).map_err(e)?;
    let mut out = Vec::new();
    for (k, u) in units.iter().enumerate() {
        let mut segs = Vec::new();
        for s in &u.segments {
            let keys =
                gani::keys_of(&bytes, s, clip.frame_count as usize, u.is_static()).map_err(e)?;
            segs.push(serde_json::json!({
                "id": s.segment_id, "kind": s.kind.name(), "bits": s.component_bits,
                "bytes": [s.blob.0, s.blob.1], "keys": keys.len(),
                "first": keys.first().map(|x| x.render()).unwrap_or_default(),
                "last": keys.last().map(|x| x.render()).unwrap_or_default(),
            }));
        }
        out.push(serde_json::json!({
            "index": k, "name": u.name_code, "static": u.is_static(), "loops": u.loops(),
            "segments": segs,
        }));
    }
    Ok(serde_json::json!({
        "units": clip.unit_count, "segments": clip.segment_count,
        "frames": clip.frame_count, "rate": clip.frame_rate,
        "staleSize": clip.size_disagrees(), "tracks": out,
    }))
}

/// Rewrite one keyframe. The core re-walks the edited bytes and refuses the
/// write if any blob moved or any byte outside that key changed, so a returned
/// success means the rest of the clip is provably untouched.
#[tauri::command]
fn gani_set_key(
    path: String,
    unit: usize,
    segment: usize,
    key: usize,
    parts: Vec<u32>,
    signs: Vec<bool>,
) -> CmdResult<serde_json::Value> {
    use fl27mm::gani;
    if parts.len() != 3 || signs.len() != 3 {
        return Err("a keyframe needs three components and three signs".to_string());
    }
    gani::set_key(
        Path::new(&path),
        unit,
        segment,
        key,
        gani::KeyValue::Quat {
            parts: [parts[0], parts[1], parts[2]],
            signs: [signs[0], signs[1], signs[2]],
        },
    )
    .map_err(e)?;
    let bytes = std::fs::read(Path::new(&path)).map_err(e)?;
    let clip = gani::Clip::parse(&bytes).map_err(e)?;
    let units = gani::walk(&bytes).map_err(e)?;
    let u = units
        .get(unit)
        .ok_or_else(|| "unit went away".to_string())?;
    let s = u
        .segments
        .get(segment)
        .ok_or_else(|| "segment went away".to_string())?;
    let keys = gani::keys_of(&bytes, s, clip.frame_count as usize, u.is_static()).map_err(e)?;
    Ok(serde_json::json!({
        "readBack": keys.get(key).map(|x| x.render()).unwrap_or_default(),
        "keys": keys.len(),
    }))
}

/// Set a clip's frame rate. The core re-reads and diffs the file, so a write
/// that disturbed anything outside the rate byte is refused rather than reported
/// as a success.
#[tauri::command]
fn gani_rate(path: String, rate: u32) -> CmdResult<serde_json::Value> {
    let (was, now) = fl27mm::gani::set_frame_rate(Path::new(&path), rate).map_err(e)?;
    Ok(serde_json::json!({ "was": was, "now": now }))
}

/// Validate a menu set's navigation against the layers that also define
/// screens. Without the base layer almost every link looks dead, which is why
/// `bases` is required rather than optional.
#[tauri::command]
fn menu_check(root: String, bases: Vec<String>) -> CmdResult<serde_json::Value> {
    use fl27mm::menus;
    let p = Path::new(&root);
    let screens = menus::load(p).map_err(e)?;
    let bs: Vec<std::path::PathBuf> = bases.iter().map(PathBuf::from).collect();
    let mut r = menus::validate_with(&screens, &bs);
    r.root = root;
    let mut list = Vec::new();
    for (id, sc) in screens.iter().take(400) {
        list.push(serde_json::json!({
            "id": id,
            "events": sc.events.iter().map(|(n, ev)| {
                serde_json::json!({ "name": n, "to": ev.to.clone().unwrap_or_default() })
            }).collect::<Vec<_>>(),
        }));
    }
    Ok(serde_json::json!({
        "screens": r.screens, "links": r.links, "clean": r.clean(),
        "broken": r.broken, "unreachable": r.unreachable, "groups": r.by_prefix,
        "entries": list,
    }))
}

/// Repoint one navigation event and write the screen back. The core refuses a
/// target that exists in neither the set nor the layers given, so a typo here
/// is an error rather than a new dead button.
#[tauri::command]
fn menu_link(
    root: String,
    bases: Vec<String>,
    screen: String,
    event: String,
    target: String,
) -> CmdResult<String> {
    use fl27mm::menus;
    let p = Path::new(&root);
    let screens = menus::load(p).map_err(e)?;
    if !menus::target_known(
        &screens,
        &bases.iter().map(PathBuf::from).collect::<Vec<_>>(),
        &target,
    ) {
        return Err(format!(
            "{target} is not a screen in this set or in the layers given; nothing would follow the button"
        ));
    }
    let sc = menus::set_target(&screens, &screen, &event, &target, true).map_err(e)?;
    menus::write(&sc).map_err(e)?;
    Ok(format!("{} · {} -> {}", screen, event, target))
}

pub fn run() {
    tauri::Builder::default()
        .manage(Cache::default())
        .plugin(tauri_plugin_dialog::init())
        .invoke_handler(tauri::generate_handler![
            detect_game,
            scan,
            order_report,
            save_order,
            conflict_report,
            cpk_list,
            cpk_extract,
            cpk_pack,
            tex_info,
            tex_preview,
            tex_convert,
            container_report,
            container_unwrap,
            container_rewrap,
            pesdb_report,
            game_map,
            archive_map,
            explain_path,
            bin_read,
            bin_section,
            bin_hex,
            bin_section_table,
            studio_tree,
            studio_read,
            studio_write,
            studio_new_pack,
            studio_check_pack,
            studio_install,
            studio_kinds,
            studio_entries,
            studio_edit,
            studio_create,
            studio_rename,
            studio_remove,
            studio_reveal,
            bin_patch,
            asset_list,
            asset_replace,
            asset_preview,
            gani_read,
            gani_rate,
            gani_set_key,
            rig_read,
            menu_check,
            menu_link,
        ])
        .run(tauri::generate_context!())
        .expect("error while running the FL27 mod manager");
}
