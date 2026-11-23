//! Finding packs and indexing the file keys they serve.
//!
//! A pack is a folder Sider can serve: it holds game-path content directly.
//! Requiring only `common/` or `Asset/` is wrong -- commentary packs carry
//! `eng/sound/acb` and `eng/sound/awb`, and scene packs carry `canm/`, so a
//! marker set limited to those two silently drops gigabytes of content.
//!
//! Keys are every file path relative to the pack root, lowercased with forward
//! slashes, because that is what Sider matches on and Windows paths are
//! case-insensitive.

use std::fs;
use std::path::{Path, PathBuf};

/// Folder names that mark a directory as a pack rather than a category.
const MARKERS: &[&str] = &[
    "common", "asset", "canm", "sound", "eng", "ger", "fra", "ita", "spa", "por",
    "rus", "jpn", "kor", "chi", "ara", "bra", "gre", "tur", "pol", "dut", "swe",
    "nor", "dan", "fin", "cze", "hun",
];

/// File extensions Sider actually loads from a content pack.
pub const GAME_EXT: &[&str] = &[
    ".canm", ".awb", ".acb", ".fpk", ".fpkd", ".ftex", ".fmdl", ".bin", ".dds",
    ".gani", ".seq",
];

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub enum Kind {
    Ball,
    Emblem,
    Menu,
    Audio,
    Faces,
    Boots,
    Kits,
    Stadiums,
    Graphics,
    Turf,
    Scene,
    Ui,
    Other,
}

impl Kind {
    pub fn label(&self) -> &'static str {
        match self {
            Kind::Ball => "ball",
            Kind::Emblem => "emblem",
            Kind::Menu => "menu",
            Kind::Audio => "audio",
            Kind::Faces => "faces",
            Kind::Boots => "boots",
            Kind::Kits => "kits",
            Kind::Stadiums => "stadiums",
            Kind::Graphics => "graphics",
            Kind::Turf => "turf",
            Kind::Scene => "scene",
            Kind::Ui => "ui",
            Kind::Other => "other",
        }
    }

    /// True when packs of this kind are alternatives for the same keys rather
    /// than additive content -- the report uses this to tell a real ordering
    /// mistake from an unavoidable choice between variants.
    pub fn is_alternative(&self) -> bool {
        matches!(self, Kind::Ball | Kind::Menu)
    }
}

#[derive(Debug, Clone)]
pub struct Pack {
    /// Path relative to the livecpk root, with backslashes, as sider.ini uses.
    pub rel: String,
    pub path: PathBuf,
    pub name: String,
    pub kind: Kind,
}

fn is_pack(dir: &Path) -> bool {
    let Ok(entries) = fs::read_dir(dir) else {
        return false;
    };
    for entry in entries.flatten() {
        let name = entry.file_name().to_string_lossy().to_lowercase();
        if MARKERS.contains(&name.as_str()) {
            return true;
        }
        if GAME_EXT.iter().any(|ext| name.ends_with(ext)) {
            return true;
        }
    }
    false
}

fn kind_from_category(top: &str) -> Option<Kind> {
    Some(match top.to_lowercase().as_str() {
        "ballpack" => Kind::Ball,
        "emblems" => Kind::Emblem,
        "soundtrack" | "announcer" | "netsound" | "pitchsfx" => Kind::Audio,
        "menu server" | "menu" | "compmenus" => Kind::Menu,
        "mini faces" | "fl26 regen faces" => Kind::Faces,
        "boot-root" => Kind::Boots,
        "slotkits_v3" => Kind::Kits,
        "stadiums extra db" => Kind::Stadiums,
        "ultra graphics gfx" => Kind::Graphics,
        "3d turf" => Kind::Turf,
        "uicolors" => Kind::Ui,
        "ent" | "goal" | "mode" | "timeup" | "test" | "carabao cup" => Kind::Scene,
        "logos_fl27" => Kind::Emblem,
        "immersion mod 2.0" => Kind::Other,
        "gp_jp_animation mod" => Kind::Other,
        _ => return None,
    })
}

fn kind_from_content(path: &Path) -> Kind {
    let mut has_menu = false;
    let mut has_render = false;
    let mut has_sound = false;
    let mut has_asset = false;
    let mut stack = vec![path.to_path_buf()];
    while let Some(dir) = stack.pop() {
        let Ok(entries) = fs::read_dir(&dir) else { continue };
        for entry in entries.flatten() {
            let p = entry.path();
            let name = entry.file_name().to_string_lossy().to_lowercase();
            if p.is_dir() {
                match name.as_str() {
                    "menu" | "script" => has_menu = true,
                    "render" => has_render = true,
                    "sound" => has_sound = true,
                    "asset" => has_asset = true,
                    _ => {}
                }
                stack.push(p);
            } else if name.ends_with(".awb") || name.ends_with(".acb") {
                has_sound = true;
            }
        }
    }
    if has_sound && has_menu {
        Kind::Audio
    } else if has_asset {
        Kind::Ball
    } else if has_render && !has_menu {
        Kind::Emblem
    } else if has_menu {
        Kind::Menu
    } else {
        Kind::Other
    }
}

/// Walk a livecpk root and return every pack, in a stable order.
///
/// The root's own `Asset` and `common` belong to the root pack, so they are
/// skipped; descending into them would register slices of the base content as
/// separate packs. Within a category the walk stops at the first pack folder,
/// because tournament packs nest stage menus inside themselves and descending
/// further splits one pack into many that then overwrite each other.
pub fn discover(root: &Path) -> Vec<Pack> {
    let mut out = Vec::new();
    let Ok(entries) = fs::read_dir(root) else {
        return out;
    };
    let mut tops: Vec<PathBuf> = entries
        .flatten()
        .map(|e| e.path())
        .filter(|p| p.is_dir())
        .collect();
    tops.sort();
    for top in tops {
        let top_name = top.file_name().unwrap().to_string_lossy().to_string();
        if top_name.eq_ignore_ascii_case("Asset") || top_name.eq_ignore_ascii_case("common") {
            continue;
        }
        let category = kind_from_category(&top_name);
        let mut stack = vec![top.clone()];
        while let Some(dir) = stack.pop() {
            if is_pack(&dir) {
                let rel = dir
                    .strip_prefix(root)
                    .unwrap()
                    .to_string_lossy()
                    .replace('/', "\\");
                let kind = category
                    .clone()
                    .unwrap_or_else(|| kind_from_content(&dir));
                out.push(Pack {
                    name: dir.file_name().unwrap().to_string_lossy().to_string(),
                    rel,
                    path: dir.clone(),
                    kind,
                });
                continue; // do not descend into a pack
            }
            let Ok(children) = fs::read_dir(&dir) else { continue };
            let mut dirs: Vec<PathBuf> = children
                .flatten()
                .map(|e| e.path())
                .filter(|p| p.is_dir())
                .collect();
            dirs.sort();
            stack.extend(dirs.into_iter().rev());
        }
    }
    out.sort_by(|a, b| a.rel.cmp(&b.rel));
    out
}

/// Every file key a pack serves, relative to its root, normalised for matching.
pub fn keys(pack: &Path) -> Vec<String> {
    let mut out: Vec<String> = crate::fsutil::files(pack).iter()
        .filter_map(|p| p.strip_prefix(pack).ok())
        .map(|rel| rel.to_string_lossy().replace('\\', "/").to_lowercase())
        .collect();
    out.sort();
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    fn touch(path: &Path) {
        fs::create_dir_all(path.parent().unwrap()).unwrap();
        fs::write(path, b"x").unwrap();
    }

    #[test]
    fn recognises_language_and_scene_payloads() {
        let tmp = std::env::temp_dir().join("fl27mm_packs_test");
        let _ = fs::remove_dir_all(&tmp);
        touch(&tmp.join("Commentary/eng/sound/awb/20_MAIN.awb"));
        touch(&tmp.join("ent/canm/thing.canm"));
        touch(&tmp.join("Kits/common/render/x.bin"));
        touch(&tmp.join("common/etc/pesdb/Team.bin"));
        touch(&tmp.join("Asset/model/y.fmdl"));
        let packs = discover(&tmp);
        let names: Vec<&str> = packs.iter().map(|p| p.name.as_str()).collect();
        assert!(names.contains(&"Commentary"), "language payload missed: {names:?}");
        assert!(names.contains(&"ent"), "canm payload missed: {names:?}");
        assert!(names.contains(&"Kits"));
        assert!(!names.contains(&"common"), "root common must not be a pack");
        assert!(!names.contains(&"Asset"), "root Asset must not be a pack");
        let _ = fs::remove_dir_all(&tmp);
    }

    #[test]
    fn nested_stage_menus_stay_one_pack() {
        let tmp = std::env::temp_dir().join("fl27mm_nest_test");
        let _ = fs::remove_dir_all(&tmp);
        touch(&tmp.join("Menu server/UCL/common/menu/a.bin"));
        touch(&tmp.join("Menu server/UCL/Groups/common/menu/b.bin"));
        touch(&tmp.join("Menu server/UCL/Final/common/menu/c.bin"));
        let packs = discover(&tmp);
        assert_eq!(packs.len(), 1, "expected one pack, got {:?}",
                   packs.iter().map(|p| &p.rel).collect::<Vec<_>>());
        assert_eq!(packs[0].name, "UCL");
        assert_eq!(keys(&packs[0].path).len(), 3);
        let _ = fs::remove_dir_all(&tmp);
    }
}
