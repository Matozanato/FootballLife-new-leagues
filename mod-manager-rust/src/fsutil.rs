//! Parallel directory walking.
//!
//! On Windows a `read_dir` is a round-trip per directory, and this install has
//! hundreds of thousands of them. Walking serially spends nearly all its time
//! waiting, which is why a release build was no faster than a debug one.
//!
//! The tree is expanded breadth-first until there are enough independent
//! subtrees to keep every worker busy, then each subtree is walked serially in
//! parallel. Splitting to a fixed depth instead would leave one worker holding
//! the base pack's `Asset` tree while the others idle.

use std::fs;
use std::path::{Path, PathBuf};

use rayon::prelude::*;

/// How many independent subtrees to aim for before handing work to rayon.
fn target_units() -> usize {
    rayon::current_num_threads().saturating_mul(4).max(8)
}

fn read_children(dir: &Path) -> (Vec<PathBuf>, Vec<PathBuf>) {
    let mut dirs = Vec::new();
    let mut files = Vec::new();
    let Ok(entries) = fs::read_dir(dir) else {
        return (dirs, files);
    };
    for entry in entries.flatten() {
        // file_type comes from the directory enumeration on Windows, so this
        // does not cost an extra stat per entry the way path.is_dir() does.
        match entry.file_type() {
            Ok(t) if t.is_dir() => dirs.push(entry.path()),
            Ok(_) => files.push(entry.path()),
            Err(_) => {
                let p = entry.path();
                if p.is_dir() {
                    dirs.push(p)
                } else {
                    files.push(p)
                }
            }
        }
    }
    (dirs, files)
}

fn walk_serial(root: &Path, files: &mut Vec<PathBuf>) {
    let mut stack = vec![root.to_path_buf()];
    while let Some(dir) = stack.pop() {
        let (dirs, mut f) = read_children(&dir);
        stack.extend(dirs);
        files.append(&mut f);
    }
}

/// Every file under `root`, in no particular order.
pub fn files(root: &Path) -> Vec<PathBuf> {
    let target = target_units();
    let mut frontier = vec![root.to_path_buf()];
    let mut collected: Vec<PathBuf> = Vec::new();
    while frontier.len() < target {
        let mut next = Vec::new();
        for dir in &frontier {
            let (dirs, mut f) = read_children(dir);
            next.extend(dirs);
            collected.append(&mut f);
        }
        if next.is_empty() {
            return collected;
        }
        frontier = next;
    }
    let rest: Vec<PathBuf> = frontier
        .par_iter()
        .flat_map(|d| {
            let mut f = Vec::new();
            walk_serial(d, &mut f);
            f
        })
        .collect();
    collected.extend(rest);
    collected
}

/// Total bytes and file count under `root`, stopping early at `cap` files so a
/// summary never pays for a full enumeration of a huge tree.
pub fn stats(root: &Path, cap: usize) -> (u64, usize) {
    let mut bytes = 0u64;
    let mut count = 0usize;
    let mut stack = vec![root.to_path_buf()];
    while let Some(dir) = stack.pop() {
        let Ok(entries) = fs::read_dir(&dir) else {
            continue;
        };
        for entry in entries.flatten() {
            match entry.file_type() {
                Ok(t) if t.is_dir() => stack.push(entry.path()),
                Ok(_) => {
                    count += 1;
                    bytes += entry.metadata().map(|m| m.len()).unwrap_or(0);
                    if count >= cap {
                        return (bytes, count);
                    }
                }
                Err(_) => {
                    let p = entry.path();
                    if p.is_dir() {
                        stack.push(p)
                    }
                }
            }
        }
    }
    (bytes, count)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn finds_every_file_exactly_once() {
        let root = std::env::temp_dir().join(format!("fl27mm-walk-{}", std::process::id()));
        let _ = fs::remove_dir_all(&root);
        let mut expected = Vec::new();
        for a in 0..6 {
            for b in 0..6 {
                let d = root.join(format!("d{a}")).join(format!("d{b}"));
                fs::create_dir_all(&d).unwrap();
                for c in 0..4 {
                    let p = d.join(format!("f{c}.bin"));
                    fs::write(&p, b"x").unwrap();
                    expected.push(p);
                }
            }
        }
        let mut found = files(&root);
        found.sort();
        expected.sort();
        assert_eq!(found, expected);
        assert_eq!(stats(&root, 10_000), (144, 144));
        assert_eq!(stats(&root, 10).1, 10);
        let _ = fs::remove_dir_all(&root);
    }

    #[test]
    fn missing_directory_is_empty_not_a_panic() {
        let p = std::env::temp_dir().join("fl27mm-does-not-exist-xyz");
        assert!(files(&p).is_empty());
        assert_eq!(stats(&p, 100), (0, 0));
    }
}
