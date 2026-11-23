//! Finding a Sider install on the machine.
//!
//! Detection used to be a hardcoded allow-list of `C:`..`F:` crossed with five
//! folder names. That is why an install on another drive, or in a folder nobody
//! thought to list, simply did not appear: the game was never in the wrong
//! place, the search was in the wrong place. The search is now built from the
//! drives Windows actually has, and covers the shapes people really use.

use serde::Serialize;
use std::path::{Path, PathBuf};

/// A located install and the four paths everything else is derived from.
#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct Install {
    pub game: String,
    pub addons: String,
    pub ini: String,
    pub packs_root: String,
}

impl Install {
    pub fn new(game: &Path) -> Install {
        let addons = game.join("SiderAddons");
        Install {
            game: game.to_string_lossy().into_owned(),
            addons: addons.to_string_lossy().into_owned(),
            ini: addons.join("sider.ini").to_string_lossy().into_owned(),
            packs_root: addons.join("livecpk").join("root").to_string_lossy().into_owned(),
        }
    }
}

/// A folder is the game if Sider is installed in it: `SiderAddons/sider.ini`.
/// That file, not the folder name, is what makes an install an install.
pub fn is_install(dir: &Path) -> bool {
    dir.join("SiderAddons").join("sider.ini").is_file()
}

/// Every drive letter Windows currently has mounted.
///
/// Probing the letters is enough and needs no registry access: a letter that is
/// not mounted is not a directory, so the probe simply yields nothing for it.
/// Hardcoding `C:`..`F:` was the bug, not the idea of scanning drives.
pub fn mounted_drives() -> Vec<String> {
    ('A'..='Z')
        .map(|c| format!("{c}:\\"))
        .filter(|p| Path::new(p).is_dir())
        .collect()
}

/// The folders to look inside on one drive. Deliberately includes the drive
/// root itself, because copying the game next to the drive letter is the most
/// common thing a Football Life player does.
pub fn prefixes_for(drive: &str) -> Vec<PathBuf> {
    let mut out = vec![PathBuf::from(drive)];
    for sub in [
        "Games",
        "SteamLibrary",
        "steamapps",
        "Program Files",
        "Program Files (x86)",
        "Steam",
    ] {
        let base = PathBuf::from(drive).join(sub);
        out.push(base.clone());
        out.push(base.join("steamapps").join("common"));
        out.push(base.join("Steam").join("steamapps").join("common"));
    }
    out
}

/// The candidate parents to scan, for every mounted drive.
pub fn candidates(drives: &[String]) -> Vec<PathBuf> {
    drives.iter().flat_map(|d| prefixes_for(d)).collect()
}

/// Collapse `.` and `..` lexically so two spellings of one folder compare equal.
///
/// `canonicalize` would do this too, but on Windows it returns a `\\?\`-prefixed
/// path, and that string is what the user sees in the dropdown, so the
/// normalisation has to be done here rather than borrowed from the filesystem.
fn normalise(path: &Path) -> PathBuf {
    let mut out = PathBuf::from(path::prefix(path));
    for c in path.components() {
        match c {
            std::path::Component::CurDir => {}
            std::path::Component::ParentDir => {
                out.pop();
            }
            other => out.push(other.as_os_str()),
        }
    }
    out
}

mod path {
    /// The drive or UNC prefix, kept so popping past the root cannot eat it.
    pub fn prefix(p: &std::path::Path) -> &std::ffi::OsStr {
        match p.components().next() {
            Some(std::path::Component::Prefix(x)) => x.as_os_str(),
            Some(std::path::Component::RootDir) => std::ffi::OsStr::new("\\"),
            _ => std::ffi::OsStr::new(""),
        }
    }
}

/// Scan the machine for installs. `extra` is searched first, so a folder the
/// user picked by hand outranks anything found automatically.
pub fn detect(extra: &[PathBuf]) -> Vec<Install> {
    let mut out: Vec<Install> = Vec::new();
    let mut seen: Vec<PathBuf> = Vec::new();
    let mut add = |dir: &Path| {
        if !is_install(dir) {
            return;
        }
        let key = normalise(dir);
        let lowered = key.to_string_lossy().to_lowercase();
        if seen.iter().any(|s| s.to_string_lossy().to_lowercase() == lowered) {
            return;
        }
        seen.push(key);
        out.push(Install::new(dir));
    };
    for root in extra.iter().chain(candidates(&mounted_drives()).iter()) {
        let Ok(entries) = std::fs::read_dir(root) else { continue };
        for e in entries.flatten() {
            let p = e.path();
            if p.is_dir() {
                add(&p);
            }
        }
        // The candidate itself may be the game, which is how a drive-root or
        // hand-picked install gets found without a second level of walking.
        add(root);
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_search_covers_every_drive_letter_not_six_of_them() {
        // The old list was ["C:", "D:", "E:", "F:"]. Anything past F: was
        // invisible, which is the reported bug on its own.
        assert!(prefixes_for("G:\\").iter().any(|p| p == Path::new("G:\\")));
        assert!(prefixes_for("H:\\").iter().any(|p| p == Path::new("H:\\Games")));
        assert!(prefixes_for("G:\\")
            .iter()
            .any(|p| p == Path::new("G:\\SteamLibrary\\steamapps\\common")));
        let c = candidates(&["G:".to_string(), "H:".to_string()]);
        assert!(c.len() >= 2 * 19, "expected a prefix per drive, got {}", c.len());
    }

    #[test]
    fn a_drive_root_install_is_a_candidate() {
        // "D:\SP Football Life 2027" is the single most common layout and was
        // never scanned, because only folders under a drive were.
        assert!(prefixes_for("D:\\").iter().any(|p| p == Path::new("D:\\")));
    }

    #[test]
    fn an_install_is_recognised_by_its_ini_not_its_name() {
        let tmp = std::env::temp_dir().join("fl27mm_install_test");
        let game = tmp.join("Whatever People Call It");
        std::fs::create_dir_all(game.join("SiderAddons")).unwrap();
        std::fs::write(game.join("SiderAddons").join("sider.ini"), "[cpk.root]\n").unwrap();
        assert!(is_install(&game));
        assert!(!is_install(&tmp.join("NotAGame")));
        let i = Install::new(&game);
        assert!(i.ini.ends_with("SiderAddons\\sider.ini") || i.ini.ends_with("SiderAddons/sider.ini"));
        assert!(i.packs_root.contains("livecpk"));
        std::fs::remove_dir_all(&tmp).ok();
    }

    #[test]
    fn a_hand_picked_folder_is_found_even_when_no_drive_prefix_covers_it() {
        let tmp = std::env::temp_dir().join("fl27mm_install_pick");
        let game = tmp.join("SP Football Life 2027");
        std::fs::create_dir_all(game.join("SiderAddons")).unwrap();
        std::fs::write(game.join("SiderAddons").join("sider.ini"), "[cpk.root]\n").unwrap();
        let found = detect(&[game.clone()]);
        assert!(
            found.iter().any(|f| f.game.eq_ignore_ascii_case(&game.to_string_lossy())),
            "a folder the user chose must be reported: {found:?}"
        );
        std::fs::remove_dir_all(&tmp).ok();
    }

    #[test]
    fn two_spellings_of_one_install_are_reported_once() {
        let tmp = std::env::temp_dir().join("fl27mm_install_dupe");
        let game = tmp.join("Game");
        std::fs::create_dir_all(game.join("SiderAddons")).unwrap();
        std::fs::write(game.join("SiderAddons").join("sider.ini"), "[cpk.root]\n").unwrap();
        let other = game.join("..").join("Game");
        let found = detect(&[game.clone(), other.clone()]);
        let hits: Vec<_> = found
            .iter()
            .filter(|f| normalise(Path::new(&f.game)) == normalise(&game))
            .collect();
        assert_eq!(hits.len(), 1, "{game:?} and {other:?} are one install, got {hits:?}");
        std::fs::remove_dir_all(&tmp).ok();
    }
}
