//! What the cpk.root order actually does, and how to order it properly.
//!
//! Sider serves the first pack in the list that carries a requested file, so a
//! pack only contributes the keys no earlier pack already claimed. Walking the
//! order and claiming keys as it goes gives the truth about which packs are
//! live, which are partly shadowed, and which are completely dead -- and who
//! killed them.
//!
//! The sort rule is deliberately simple and explainable: fewer keys means more
//! specific, so ascending key count puts a one-file sound pack ahead of a
//! thousand-file general pack, and the base `root` pack is forced last so it
//! only fills what nothing else provides. Alternatives (balls, per-competition
//! menus) cannot all win -- they share keys by construction -- so they are
//! grouped and reported as a choice rather than treated as a defect.

use std::collections::{HashMap, HashSet};
use std::path::Path;

use crate::ini::{Entry, Ini};
use crate::packs::{self, Kind, Pack};

#[derive(Debug)]
pub struct Shadow {
    pub rel: String,
    pub total: usize,
    pub surviving: usize,
    /// (blocker rel, keys taken)
    pub blockers: Vec<(String, usize)>,
}

impl Shadow {
    pub fn dead(&self) -> bool {
        self.total > 0 && self.surviving == 0
    }
}

/// Resolve a sider.ini cpk.root value to a directory on disk.
pub fn resolve(addons: &Path, value: &str) -> std::path::PathBuf {
    let cleaned = value.trim_start_matches(".\\").trim_start_matches("./");
    addons.join(cleaned.replace('\\', "/"))
}

pub fn analyse(addons: &Path, ini: &Ini) -> Vec<Shadow> {
    use rayon::prelude::*;

    let entries = ini.active("cpk.root");
    // Gathering keys is the expensive part and is independent per pack; only
    // the claiming below has to follow the order.
    let keys: Vec<Vec<String>> = entries.par_iter()
        .map(|e| packs::keys(&resolve(addons, &e.value)))
        .collect();

    let mut claimed: HashMap<String, String> = HashMap::new();
    let mut out = Vec::new();
    for (entry, keys) in entries.iter().zip(keys) {
        if keys.is_empty() {
            continue;
        }
        let mut blockers: HashMap<String, usize> = HashMap::new();
        let mut surviving = 0;
        for key in &keys {
            match claimed.get(key) {
                Some(owner) => *blockers.entry(owner.clone()).or_insert(0) += 1,
                None => {
                    claimed.insert(key.clone(), entry.value.clone());
                    surviving += 1;
                }
            }
        }
        let mut blockers: Vec<(String, usize)> = blockers.into_iter().collect();
        blockers.sort_by_key(|(_, n)| std::cmp::Reverse(*n));
        out.push(Shadow {
            rel: entry.value.clone(),
            total: keys.len(),
            surviving,
            blockers,
        });
    }
    out
}

/// Is this the base pack that should always sort last?
pub fn is_base(value: &str) -> bool {
    let v = value.replace('\\', "/").to_lowercase();
    v.ends_with("/livecpk/root") || v == "livecpk/root"
}

/// Order entries so specific packs win and the base pack fills the gaps.
///
/// Key counts are taken from disk, so a pack that no longer exists sorts as if
/// it were empty and lands just before the base pack rather than blocking
/// anything.
pub fn sorted(addons: &Path, entries: &[Entry]) -> Vec<Entry> {
    let mut counted: Vec<(usize, bool, String, Entry)> = entries
        .iter()
        .map(|e| {
            let path = resolve(addons, &e.value);
            let n = packs::keys(&path).len();
            (n, is_base(&e.value), e.value.to_lowercase(), e.clone())
        })
        .collect();
    counted.sort_by(|a, b| {
        a.1.cmp(&b.1) // base last
            .then(a.0.cmp(&b.0)) // fewer keys first
            .then(a.2.cmp(&b.2))
    });
    counted.into_iter().map(|(_, _, _, e)| e).collect()
}

/// Group alternative packs so the report can say "pick one" instead of listing
/// a hundred dead packs as if each were a bug.
pub fn alternatives(packs: &[Pack]) -> HashMap<Kind, Vec<String>> {
    let mut out: HashMap<Kind, Vec<String>> = HashMap::new();
    for p in packs {
        if p.kind.is_alternative() {
            out.entry(p.kind.clone()).or_default().push(p.rel.clone());
        }
    }
    out
}

/// Keys that no active pack provides -- useful for spotting a pack that was
/// disabled but whose content something else still expects.
pub fn unclaimed(packs: &[Pack], active: &HashSet<String>) -> usize {
    let mut n = 0;
    for p in packs {
        if active.contains(&p.rel) {
            continue;
        }
        n += packs::keys(&p.path).len();
    }
    n
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;

    fn entry(value: &str) -> Entry {
        Entry {
            indent: "\t".into(),
            disabled: false,
            key: "cpk.root".into(),
            value: value.into(),
            quoted: true,
            comment: String::new(),
        }
    }

    #[test]
    fn first_wins_and_base_sorts_last() {
        let tmp = std::env::temp_dir().join("fl27mm_order_test");
        let _ = fs::remove_dir_all(&tmp);
        // general pack carries both keys; specific pack carries one
        for (p, files) in [
            ("livecpk/root/common/a.bin", true),
            ("livecpk/root/common/b.bin", true),
            ("livecpk/Specific/common/a.bin", true),
        ] {
            let path = tmp.join(p);
            if files {
                fs::create_dir_all(path.parent().unwrap()).unwrap();
                fs::write(&path, b"x").unwrap();
            }
        }
        let entries = vec![
            entry(".\\livecpk\\root"),
            entry(".\\livecpk\\Specific"),
        ];
        let ordered = sorted(&tmp, &entries);
        assert_eq!(ordered[0].value, ".\\livecpk\\Specific");
        assert_eq!(ordered[1].value, ".\\livecpk\\root");

        let mut ini = Ini::default();
        ini.lines = ordered.into_iter().map(crate::ini::Line::Entry).collect();
        let shadows = analyse(&tmp, &ini);
        assert_eq!(shadows[0].surviving, 1);
        assert_eq!(shadows[1].surviving, 1, "base still provides b.bin");
        assert!(!shadows[1].dead());
        let _ = fs::remove_dir_all(&tmp);
    }

    #[test]
    fn a_buried_pack_is_reported_dead_with_its_blocker() {
        let tmp = std::env::temp_dir().join("fl27mm_dead_test");
        let _ = fs::remove_dir_all(&tmp);
        for p in ["livecpk/Big/common/sound.acb", "livecpk/Small/common/sound.acb"] {
            let path = tmp.join(p);
            fs::create_dir_all(path.parent().unwrap()).unwrap();
            fs::write(&path, b"x").unwrap();
        }
        let mut ini = Ini::default();
        ini.lines = vec![
            crate::ini::Line::Entry(entry(".\\livecpk\\Big")),
            crate::ini::Line::Entry(entry(".\\livecpk\\Small")),
        ];
        let shadows = analyse(&tmp, &ini);
        assert!(shadows[1].dead());
        assert_eq!(shadows[1].blockers[0].0, ".\\livecpk\\Big");
        let _ = fs::remove_dir_all(&tmp);
    }
}
