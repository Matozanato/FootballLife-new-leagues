//! Which packs compete for the same file, and whether they actually disagree.
//!
//! A shared key is only a conflict when the packs hold different bytes. Two
//! packs shipping an identical file are additive, not competing, and treating
//! them as a conflict produces a report full of noise -- measured on this
//! install, 208 of 1,134 shared keys were byte-identical.
//!
//! Content identity is size plus a 64-bit FNV-1a over the bytes. That is not a
//! cryptographic hash and is not used for one; at thirty thousand files the
//! collision probability is negligible, and a false "identical" would only
//! under-report a conflict, never corrupt anything.

use std::collections::HashMap;
use std::fs::File;
use std::io::{self, Read};
use std::path::Path;

use crate::packs::{self, Pack};

pub fn fingerprint(path: &Path) -> io::Result<(u64, u64)> {
    let size = path.metadata()?.len();
    let mut file = File::open(path)?;
    let mut hash: u64 = 0xcbf2_9ce4_8422_2325;
    let mut buf = vec![0u8; 1 << 16];
    loop {
        let n = file.read(&mut buf)?;
        if n == 0 {
            break;
        }
        for &byte in &buf[..n] {
            hash ^= byte as u64;
            hash = hash.wrapping_mul(0x0000_0100_0000_01b3);
        }
    }
    Ok((size, hash))
}

/// key -> the packs that carry it
pub fn index(packs: &[Pack]) -> HashMap<String, Vec<usize>> {
    use rayon::prelude::*;
    let per_pack: Vec<Vec<String>> = packs.par_iter().map(|p| packs::keys(&p.path)).collect();
    let mut map: HashMap<String, Vec<usize>> = HashMap::new();
    for (i, keys) in per_pack.into_iter().enumerate() {
        for key in keys {
            map.entry(key).or_default().push(i);
        }
    }
    map
}

#[derive(Debug, Default)]
pub struct Conflicts {
    pub shared: usize,
    pub identical: usize,
    pub differing: usize,
    /// (pack a, pack b) -> number of keys where they disagree
    pub pairs: HashMap<(usize, usize), usize>,
    /// A few example keys that genuinely differ, for the report.
    pub examples: Vec<String>,
}

pub fn analyse(packs: &[Pack], idx: &HashMap<String, Vec<usize>>) -> Conflicts {
    let mut out = Conflicts::default();
    for (key, owners) in idx {
        if owners.len() < 2 {
            continue;
        }
        out.shared += 1;
        // Fingerprint per owner, so a pair is only a conflict when those two
        // actually disagree. Marking every pair because one pack differs
        // reports conflicts between packs that are byte-identical.
        let mut prints: Vec<(usize, (u64, u64))> = Vec::new();
        for &i in owners {
            let path = packs[i].path.join(key.replace('/', "\\"));
            if let Ok(fp) = fingerprint(&path) {
                prints.push((i, fp));
            }
        }
        let first = prints.first().map(|(_, fp)| *fp);
        let same = first.is_some() && prints.iter().all(|(_, fp)| Some(*fp) == first);
        if same {
            out.identical += 1;
            continue;
        }
        out.differing += 1;
        if out.examples.len() < 8 {
            out.examples.push(key.clone());
        }
        for a in 0..prints.len() {
            for b in (a + 1)..prints.len() {
                if prints[a].1 == prints[b].1 {
                    continue;
                }
                let (mut x, mut y) = (prints[a].0, prints[b].0);
                if x > y {
                    std::mem::swap(&mut x, &mut y);
                }
                *out.pairs.entry((x, y)).or_insert(0) += 1;
            }
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;

    #[test]
    fn identical_files_are_not_conflicts() {
        let tmp = std::env::temp_dir().join("fl27mm_conflict_test");
        let _ = fs::remove_dir_all(&tmp);
        for (pack, bytes) in [
            ("A", &b"same"[..]),
            ("B", &b"same"[..]),
            ("C", &b"different"[..]),
        ] {
            let p = tmp.join(pack).join("common").join("x.bin");
            fs::create_dir_all(p.parent().unwrap()).unwrap();
            fs::write(&p, bytes).unwrap();
        }
        let packs = packs::discover(&tmp);
        let idx = index(&packs);
        let c = analyse(&packs, &idx);
        assert_eq!(c.shared, 1);
        assert_eq!(c.differing, 1, "A and B agree; only C disagrees");
        assert_eq!(c.identical, 0);
        // exactly the pairs involving C
        assert_eq!(c.pairs.len(), 2);
        let _ = fs::remove_dir_all(&tmp);
    }

    #[test]
    fn fingerprint_changes_with_content() {
        let tmp = std::env::temp_dir().join("fl27mm_fp_test");
        fs::create_dir_all(&tmp).unwrap();
        let a = tmp.join("a");
        let b = tmp.join("b");
        fs::write(&a, b"hello").unwrap();
        fs::write(&b, b"hellp").unwrap();
        assert_ne!(fingerprint(&a).unwrap(), fingerprint(&b).unwrap());
        fs::write(&b, b"hello").unwrap();
        assert_eq!(fingerprint(&a).unwrap(), fingerprint(&b).unwrap());
        let _ = fs::remove_dir_all(&tmp);
    }
}
