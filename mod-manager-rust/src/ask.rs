//! `.ask` skeletons.
//!
//! ```text
//!  @0        u32  version (1)
//!  @4        u32  bone count
//!  @8        bone count records of 44 bytes:
//!              +0x00  u32  (purpose not established; never used here)
//!              +0x04  u32  a descending offset, not a forward name pointer
//!              +0x08  i32  parent index, -1 for the root
//!              +0x0C  f32x3 local position
//!              +0x1C  f32x4 local quaternion
//!  @8+44*n    the bone names, null terminated, in record order, to end of file
//! ```
//!
//! Two things worth stating because both were assumed wrong once.
//!
//! The shipped `body_anim_skel.ask` opens every record with `cd cd cd cd`. That
//! is uninitialised memory that survived into the file, not a format marker: it
//! occurs zero times in the cinematic skeletons. A decoder that required it
//! would accept one file and reject every other.
//!
//! The record fields at +0x00 and +0x04 are not interpreted here. They were
//! examined as candidate name offsets and neither is one: `+0x04` descends as
//! the record index rises, while the names run forward. Reading them as a name
//! pointer would silently mislabel every bone, so the names are taken by record
//! order instead, and the layout is checked by arithmetic -- records plus a
//! packed name run must account for the file exactly.
//!
//! Two skeletons describe the same body and differ only in basis: the `_anim`
//! one has identity rest quaternions, so a decoded track value *is* the bone's
//! local rotation; the `_render` one carries the skinning basis and applying
//! animation quaternions straight onto it corrupts the pose. Which file is
//! which is therefore not a cosmetic choice, and `Skeleton::identity_basis`
//! reports it from the data instead of from the filename.

use anyhow::{bail, Result};
use std::path::Path;

const RECORD: usize = 44;

fn le_u32(b: &[u8], at: usize) -> u32 {
    u32::from_le_bytes([b[at], b[at + 1], b[at + 2], b[at + 3]])
}
fn le_i32(b: &[u8], at: usize) -> i32 {
    i32::from_le_bytes([b[at], b[at + 1], b[at + 2], b[at + 3]])
}
fn le_f32(b: &[u8], at: usize) -> f32 {
    f32::from_bits(le_u32(b, at))
}

/// One bone.
#[derive(Debug, Clone, PartialEq)]
pub struct Bone {
    pub name: String,
    /// Parent index, or -1 for the root.
    pub parent: i32,
    pub position: [f32; 3],
    pub rotation: [f32; 4],
}

/// A decoded skeleton.
#[derive(Debug, Clone)]
pub struct Skeleton {
    pub version: u32,
    pub bones: Vec<Bone>,
}

impl Skeleton {
    pub fn parse(b: &[u8]) -> Result<Skeleton> {
        if b.len() < 8 {
            bail!("too short for an ask header");
        }
        let version = le_u32(b, 0);
        let count = le_u32(b, 4) as usize;
        if count == 0 || count > 4096 {
            bail!("implausible bone count {count}");
        }
        let records_end = 8 + count * RECORD;
        if records_end > b.len() {
            bail!(
                "{} bone records need {records_end} bytes, the file is {}",
                b.len(),
                count
            );
        }
        // The names follow the records with no table of offsets to trust, so
        // they are read as a packed run and counted. A mismatch means the
        // assumed layout is wrong for this file and nothing further is safe.
        let mut names = Vec::new();
        let mut i = records_end;
        while i < b.len() {
            if b[i] == 0 {
                i += 1;
                continue;
            }
            let start = i;
            while i < b.len() && b[i] != 0 {
                i += 1;
            }
            names.push(String::from_utf8_lossy(&b[start..i]).into_owned());
            i += 1;
        }
        if names.len() != count {
            bail!(
                "expected {count} bone names after the records, found {} — the layout does not \
                 hold for this file",
                names.len()
            );
        }
        let mut bones = Vec::with_capacity(count);
        for k in 0..count {
            let at = 8 + k * RECORD;
            let parent = le_i32(b, at + 8);
            if parent >= count as i32 || (parent < -1) {
                bail!("bone {} has parent {parent}, outside -1..{count}", names[k]);
            }
            let position = [
                le_f32(b, at + 0x0C),
                le_f32(b, at + 0x10),
                le_f32(b, at + 0x14),
            ];
            let rotation = [
                le_f32(b, at + 0x1C),
                le_f32(b, at + 0x20),
                le_f32(b, at + 0x24),
                le_f32(b, at + 0x28),
            ];
            if !position.iter().all(|v| v.is_finite()) || !rotation.iter().all(|v| v.is_finite()) {
                bail!("bone {} has a non-finite transform", names[k]);
            }
            bones.push(Bone {
                name: names[k].clone(),
                parent,
                position,
                rotation,
            });
        }
        Ok(Skeleton { version, bones })
    }

    pub fn read(path: &Path) -> Result<Skeleton> {
        Skeleton::parse(&std::fs::read(path)?)
    }

    /// True when every rest rotation is the identity, which is what makes this
    /// the skeleton animation tracks are authored in. A `_render` skeleton has
    /// non-identity bases and must not be used as if it were the anim one.
    pub fn identity_basis(&self) -> bool {
        self.bones
            .iter()
            .all(|b| b.rotation == [0.0, 0.0, 0.0, 1.0])
    }

    /// The root, if there is exactly one.
    pub fn root(&self) -> Option<usize> {
        let roots: Vec<usize> = self
            .bones
            .iter()
            .enumerate()
            .filter(|(_, b)| b.parent == -1)
            .map(|(i, _)| i)
            .collect();
        if roots.len() == 1 {
            Some(roots[0])
        } else {
            None
        }
    }

    /// Depth-first order from the root, so a parent always precedes its child.
    /// A skeleton with a cycle cannot be posed and is refused here.
    pub fn draw_order(&self) -> Result<Vec<usize>> {
        let mut children: Vec<Vec<usize>> = vec![Vec::new(); self.bones.len()];
        for (i, b) in self.bones.iter().enumerate() {
            if b.parent >= 0 {
                children[b.parent as usize].push(i);
            }
        }
        let root = self
            .root()
            .ok_or_else(|| anyhow::anyhow!("no single root bone"))?;
        let mut out = Vec::with_capacity(self.bones.len());
        let mut stack = vec![root];
        while let Some(i) = stack.pop() {
            out.push(i);
            for &c in children[i].iter().rev() {
                stack.push(c);
            }
        }
        if out.len() != self.bones.len() {
            bail!(
                "only {} of {} bones are reachable from the root; the hierarchy has a cycle \
                 or an orphan",
                out.len(),
                self.bones.len()
            );
        }
        Ok(out)
    }

    pub fn describe(&self) -> String {
        let mut out = format!(
            "skeleton v{}: {} bones, {} basis, {}\n",
            self.version,
            self.bones.len(),
            if self.identity_basis() {
                "identity"
            } else {
                "render"
            },
            match self.root() {
                Some(r) => format!("root {}", self.bones[r].name),
                None => "no single root".to_string(),
            }
        );
        for b in &self.bones {
            out.push_str(&format!(
                "  {:<18} parent {:>3}  pos ({:+.4}, {:+.4}, {:+.4})  quat ({:+.3}, {:+.3}, {:+.3}, {:+.3})\n",
                b.name,
                b.parent,
                b.position[0], b.position[1], b.position[2],
                b.rotation[0], b.rotation[1], b.rotation[2], b.rotation[3],
            ));
        }
        out
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn body() -> Option<std::path::PathBuf> {
        let p = std::env::temp_dir()
            .join("skelx/common/anime/FoxAnim/Body/CharacterAssets/body_anim_skel.ask");
        p.is_file().then_some(p)
    }

    #[test]
    fn the_shipped_body_skeleton_decodes_with_its_published_layout() {
        let Some(path) = body() else { return };
        let s = Skeleton::read(&path).unwrap();
        assert_eq!(s.bones.len(), 20, "the body skeleton has twenty bones");
        assert_eq!(s.bones[0].name, "sk_root_hip");
        assert_eq!(s.bones[0].parent, -1, "the root has no parent");
        // Measured: the root hip sits about 1.096 up in the anim skeleton.
        assert!((s.bones[0].position[1] - 1.0961).abs() < 0.01);
        assert!(
            s.identity_basis(),
            "body_anim_skel stores identity rest rotations"
        );
        assert_eq!(s.root(), Some(0));
        assert_eq!(s.draw_order().unwrap().len(), 20);
    }

    #[test]
    fn every_shipped_skeleton_parses_or_is_reported() {
        // Nothing here asserts a specific bone count: the point is that the
        // layout holds across the install, or that a file where it does not is
        // refused with a reason rather than half-read.
        let root = Path::new("C:/Games/SP Football Life 2027");
        let mut ok = 0;
        let mut bad: Vec<String> = Vec::new();
        for p in crate::fsutil::files(&root.join("SiderAddons")) {
            if p.extension().map(|e| e != "ask").unwrap_or(true) {
                continue;
            }
            match Skeleton::read(&p) {
                Ok(s) => {
                    assert!(s.draw_order().is_ok(), "{}: unreachable bones", p.display());
                    ok += 1;
                }
                Err(e) => bad.push(format!(
                    "{}: {e}",
                    p.file_name().unwrap_or_default().to_string_lossy()
                )),
            }
        }
        assert!(ok > 0, "no shipped skeleton parsed");
        assert!(bad.is_empty(), "{} skeletons failed: {:?}", bad.len(), bad);
        println!("parsed {ok} shipped skeletons");
    }

    #[test]
    fn a_truncated_or_short_file_is_refused_not_guessed() {
        let Some(path) = body() else { return };
        let b = std::fs::read(&path).unwrap();
        assert!(Skeleton::parse(&b[..100]).is_err());
        // A bone count that would run past the file cannot be walked.
        let mut lie = b.clone();
        lie[4..8].copy_from_slice(&9999u32.to_le_bytes());
        assert!(Skeleton::parse(&lie).is_err());
        // A count that fits the records but leaves the wrong number of names is
        // the real structural check, and it is what catches a misread layout.
        let mut wrong = b.clone();
        wrong[4..8].copy_from_slice(&19u32.to_le_bytes());
        assert!(
            Skeleton::parse(&wrong).is_err(),
            "19 records would mis-split the name run"
        );
    }

    /// The `cdcdcdcd` bytes in the shipped body skeleton are leaked uninitialised
    /// memory, not a marker: they do not occur in the cinematic skeletons at
    /// all. This test is the regression guard against treating them as format
    /// again, which would have accepted exactly one file in the install.
    #[test]
    fn the_record_marker_is_not_required_and_both_layouts_parse() {
        let root = Path::new("C:/Games/SP Football Life 2027/SiderAddons");
        let files: Vec<_> = crate::fsutil::files(root)
            .into_iter()
            .filter(|p| p.extension().map(|e| e == "ask").unwrap_or(false))
            .collect();
        let mut plain_files = 0;
        for p in &files {
            let b = std::fs::read(p).unwrap();
            let s = Skeleton::read(p).unwrap_or_else(|e| panic!("{}: {e}", p.display()));
            assert_eq!(s.bones.len(), le_u32(&b, 4) as usize, "{}", p.display());
            if b[8..12] != [0xcd, 0xcd, 0xcd, 0xcd] {
                plain_files += 1;
            }
        }
        assert!(
            files.len() >= 20,
            "expected the shipped skeletons, found {}",
            files.len()
        );
        assert!(
            plain_files > 0,
            "the loose cinematic skeletons carry no marker; if they now do, the layout changed"
        );
        // The marker case is the body skeleton inside dt13_all.cpk, covered by
        // the test above; it must parse through the same code as these.
        assert!(
            body().is_some(),
            "extract the body skeleton to /tmp/skelx for the marker case"
        );
    }

    #[test]
    fn a_parent_cycle_is_refused() {
        let Some(path) = body() else { return };
        let mut b = std::fs::read(&path).unwrap();
        // Point the root at a child so nothing is reachable as a root.
        b[8 + 8..8 + 12].copy_from_slice(&3i32.to_le_bytes());
        let s = Skeleton::parse(&b).unwrap();
        assert!(s.draw_order().is_err(), "a cyclic hierarchy must not pose");
    }
}
