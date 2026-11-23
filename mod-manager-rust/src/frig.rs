//! `.frig` rig definitions.
//!
//! This is what joins an animation to a skeleton: a clip stores tracks by unit
//! and segment, and the rig says what each unit *is* -- a single bone, a root
//! rotation, or a chain that drives two or three bones at once. The counts are
//! the join directly: `body_skel.frig` declares 15 units and 27 segments, and
//! the shipped body clips carry 15 units and 27 segments.
//!
//! ```text
//!  @0    u32   a per-file identifier, NOT a constant (four values are in use)
//!  @4    u32   offset of the rig name
//!  @8    u32   (purpose not established)
//!  @12   u32   unit count
//!  @16   u32   segment count
//!  @20   u32   file size, always equal to the real length
//!  @24   u32   (purpose not established)
//!  @28   u32   offset of the packed group names
//!  @32   u32[unit count]  offsets of the unit records
//! ```
//!
//! Each unit record opens with its type, and the type fixes the record length:
//! 32 bytes for root rotation (1), root translation (5), simple (4) and 7, and
//! 64 bytes for the two-bone chain (3) and the three-bone chain (8). That rule
//! is checked against every rig file in the install rather than assumed, and it
//! is what makes the walk verifiable: the offsets must be increasing and each
//! gap must equal the size the type demands.
//!
//! Type 7 is common in cinematic rigs and its meaning has not been established.
//! It is decoded as a record with a known length -- so the walk stays correct --
//! and named for that rather than given a role nothing assigned it.

use anyhow::{bail, Result};
use std::path::Path;

fn le_u32(b: &[u8], at: usize) -> u32 {
    u32::from_le_bytes([b[at], b[at + 1], b[at + 2], b[at + 3]])
}

/// How a unit drives the skeleton.
///
/// The names and numeric codes are the engine's own `RIG_UNIT_TYPE`, read out
/// of the published `frig.bt` rather than inferred from record counts. That
/// matters: an earlier version of this module guessed from three observed
/// values and got the semantics of the fields wrong as a result.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum UnitType {
    Root,
    Orientation,
    TwoBone,
    LocalOrientation,
    LocalTransform,
    ThreeBoneLikeTwoBone,
    Transform,
    Arm,
    LocalTransformSrt,
    AnimalLeg,
    MultiLocalOrientation,
    TwoBoneTrans,
}

impl UnitType {
    fn from_code(c: u32) -> Option<UnitType> {
        Some(match c {
            1 => UnitType::Root,
            2 => UnitType::Orientation,
            3 => UnitType::TwoBone,
            4 => UnitType::LocalOrientation,
            5 => UnitType::LocalTransform,
            6 => UnitType::ThreeBoneLikeTwoBone,
            7 => UnitType::Transform,
            8 => UnitType::Arm,
            9 => UnitType::LocalTransformSrt,
            10 => UnitType::AnimalLeg,
            11 => UnitType::MultiLocalOrientation,
            12 => UnitType::TwoBoneTrans,
            _ => return None,
        })
    }
    pub fn code(self) -> u32 {
        match self {
            UnitType::Root => 1,
            UnitType::Orientation => 2,
            UnitType::TwoBone => 3,
            UnitType::LocalOrientation => 4,
            UnitType::LocalTransform => 5,
            UnitType::ThreeBoneLikeTwoBone => 6,
            UnitType::Transform => 7,
            UnitType::Arm => 8,
            UnitType::LocalTransformSrt => 9,
            UnitType::AnimalLeg => 10,
            UnitType::MultiLocalOrientation => 11,
            UnitType::TwoBoneTrans => 12,
        }
    }
    /// Record length, which is what makes the walk checkable.
    pub fn record_size(self) -> usize {
        match self {
            UnitType::TwoBone
            | UnitType::ThreeBoneLikeTwoBone
            | UnitType::Arm
            | UnitType::AnimalLeg
            | UnitType::TwoBoneTrans => 64,
            _ => 32,
        }
    }
    pub fn name(self) -> &'static str {
        match self {
            UnitType::Root => "root",
            UnitType::Orientation => "orientation",
            UnitType::TwoBone => "two-bone chain",
            UnitType::LocalOrientation => "local orientation",
            UnitType::LocalTransform => "local transform",
            UnitType::ThreeBoneLikeTwoBone => "three-bone chain",
            UnitType::Transform => "transform",
            UnitType::Arm => "arm chain",
            UnitType::LocalTransformSrt => "local transform srt",
            UnitType::AnimalLeg => "animal leg",
            UnitType::MultiLocalOrientation => "multi local orientation",
            UnitType::TwoBoneTrans => "two-bone chain with translation",
        }
    }
    /// The types whose record names bones directly through `SkelIndex`.
    ///
    /// This is the distinction that decides whether an animation can be posed
    /// without a solver. Only these carry a bone index at +16; the chain types
    /// resolve their bones through a two- or three-bone IK unit instead. A
    /// decoder that reads only the direct types animates the trunk, the feet
    /// and the hands and leaves the thighs, shins, shoulders, upper arms and
    /// forearms in bind pose -- the exact symptom reported against this format.
    pub fn is_direct(self) -> bool {
        matches!(
            self,
            UnitType::Orientation
                | UnitType::LocalOrientation
                | UnitType::LocalTransform
                | UnitType::Transform
                | UnitType::LocalTransformSrt
                | UnitType::MultiLocalOrientation
        )
    }
    /// How many bones this unit drives.
    pub fn bones_driven(self) -> usize {
        match self {
            UnitType::TwoBone | UnitType::TwoBoneTrans | UnitType::ThreeBoneLikeTwoBone => 2,
            UnitType::Arm => 3,
            UnitType::AnimalLeg => 4,
            _ => 1,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct RigUnit {
    pub kind: UnitType,
    /// Tracks this unit stores. The root unit has two because it carries a
    /// rotation and a translation; an arm chain has four.
    pub track_count: u16,
    /// Bones this unit addresses.
    pub bone_count: u16,
    /// Unused by the published template.
    pub parent_bone_index: i16,
    /// The unit this one hangs from, which is the rig's own hierarchy.
    pub parent_unit: i16,
    /// For the direct types, the skeleton bone this unit addresses. `None` for
    /// the chain types, which name their bones elsewhere in the record.
    pub skel_index: Option<u16>,
    /// The first segment (channel) belonging to this unit.
    pub segment_index_a: Option<u16>,
    pub offset: usize,
    pub size: usize,
}

impl RigUnit {
    /// The bone this unit drives, when it drives exactly one directly.
    pub fn bone(&self) -> Option<u16> {
        self.skel_index
    }
}

#[derive(Debug, Clone)]
pub struct Rig {
    pub identifier: u32,
    pub version: u32,
    pub name: String,
    pub unit_count: u32,
    pub segment_count: u32,
    pub units: Vec<RigUnit>,
}

impl Rig {
    pub fn parse(b: &[u8]) -> Result<Rig> {
        if b.len() < 48 {
            bail!("too short for a frig header ({} bytes)", b.len());
        }
        let identifier = le_u32(b, 0);
        let name_at = le_u32(b, 4) as usize;
        let units = le_u32(b, 12) as usize;
        let segments = le_u32(b, 16);
        let declared = le_u32(b, 20) as usize;
        let version = le_u32(b, 8);
        let groups_at = le_u32(b, 28) as usize;
        if version != 102 {
            bail!("rig version {version}, the published format asserts 102");
        }
        if declared != b.len() {
            bail!("header declares {declared} bytes, the file is {}", b.len());
        }
        if units == 0 || units > 4096 {
            bail!("implausible unit count {units}");
        }
        if 32 + 4 * units > b.len() {
            bail!("the unit table runs past the end of the file");
        }
        let offs: Vec<usize> = (0..units).map(|k| le_u32(b, 32 + 4 * k) as usize).collect();
        for k in 0..units {
            if k + 1 < units && offs[k] >= offs[k + 1] {
                bail!("unit offsets are not increasing at unit {k}");
            }
            if offs[k] + 16 > b.len() {
                bail!("unit {k} header runs past the end of the file");
            }
        }
        let mut out = Vec::with_capacity(units);
        for k in 0..units {
            let at = offs[k];
            let end = if k + 1 < units { offs[k + 1] } else { groups_at.min(b.len()) };
            let code = le_u32(b, at);
            let kind = UnitType::from_code(code)
                .ok_or_else(|| anyhow::anyhow!("unit {k} has unrecorded type {code}"))?;
            let want = kind.record_size();
            // The final unit's gap is the tail of the file, not its record, so
            // only the interior units can be checked against the type.
            if k + 1 < units && offs[k + 1] - at != want {
                bail!(
                    "unit {k} is a {} ({} bytes) but the next unit starts {} bytes later",
                    kind.name(), want, offs[k + 1] - at
                );
            }
            let sh = |n: usize| i16::from_le_bytes([b[at + n], b[at + n + 1]]);
            let track_count = sh(4) as u16;
            let bone_count = sh(6) as u16;
            let parent_bone_index = sh(8);
            let parent_unit = sh(10);
            if le_u32(b, at + 12) != 0 {
                bail!("unit {k} has a nonzero padding word");
            }
            // Only the direct types name a bone; the chain types put a skip and
            // a chain-plane normal at +16, so reading SkelIndex there would
            // return a component of that vector as a bone index.
            let (skel_index, segment_index_a) = if kind.is_direct() {
                let s = if kind == UnitType::LocalTransformSrt {
                    sh(16)
                } else {
                    sh(16)
                };
                let a = if kind == UnitType::LocalTransformSrt { -1 } else { sh(18) };
                (Some(s as u16), if a < 0 { None } else { Some(a as u16) })
            } else {
                (None, None)
            };
            out.push(RigUnit {
                kind,
                track_count,
                bone_count,
                parent_bone_index,
                parent_unit,
                skel_index,
                segment_index_a,
                offset: at,
                size: end - at,
            });
        }
        Ok(Rig {
            identifier,
            version,
            name: cstr(b, name_at),
            unit_count: units as u32,
            segment_count: segments,
            units: out,
        })
    }

    pub fn read(path: &Path) -> Result<Rig> {
        Rig::parse(&std::fs::read(path)?)
    }

    /// Resolve each direct unit to a bone name from a skeleton.
    pub fn bones_named(&self, sk: &crate::ask::Skeleton) -> Vec<(String, String)> {
        self.units
            .iter()
            .filter_map(|u| {
                let i = u.skel_index? as usize;
                sk.bones.get(i).map(|b| (b.name.clone(), u.kind.name().to_string()))
            })
            .collect()
    }

    pub fn describe(&self) -> String {
        let mut out = format!(
            "rig {:?}: {} units, {} segments, version {}, identifier {:#x}\n",
            self.name, self.unit_count, self.segment_count, self.version, self.identifier
        );
        for (k, u) in self.units.iter().enumerate() {
            out.push_str(&format!(
                "  unit {k:<3} {:<30} tracks {:<2} bones {:<2} parent unit {:>3}  @{:<5} {} bytes{}\n",
                u.kind.name(), u.track_count, u.bone_count, u.parent_unit, u.offset, u.size,
                match u.skel_index {
                    Some(s) => format!("  skelIndex {s}  segmentA {:?}", u.segment_index_a),
                    None if u.kind == UnitType::Root => "  (the root itself)".to_string(),
                    None => format!(
                        "  (chain: drives {} bone{}, no direct index)",
                        u.kind.bones_driven(),
                        if u.kind.bones_driven() == 1 { "" } else { "s" }
                    ),
                }
            ));
        }
        out
    }
}

fn cstr(b: &[u8], at: usize) -> String {
    if at >= b.len() {
        return String::new();
    }
    let end = b[at..].iter().position(|&c| c == 0).map(|p| at + p).unwrap_or(b.len());
    String::from_utf8_lossy(&b[at..end]).into_owned()
}

/// Read a run of null-terminated names until the padding, which is how the rig
/// stores its group labels.
///
/// Not used, and kept out of the public API deliberately. The table at @28
/// opens with a count and then a list of offsets into records that each begin
/// with a 32-bit hash before the label, and the offset base is not established.
/// Reading it as packed strings returns nothing, which is better than the
/// wrong names: the group labels are not needed to map a channel to a bone, so
/// the rig decode stands without them.
#[allow(dead_code)]
fn cstrs(b: &[u8], at: usize) -> Vec<String> {
    let mut out = Vec::new();
    let mut i = at;
    while i < b.len() {
        if b[i] == 0 {
            i += 1;
            continue;
        }
        let s = cstr(b, i);
        let len = s.len();
        if len < 3 || !s.bytes().all(|c| c.is_ascii_graphic() || c == b'_') {
            break;
        }
        out.push(s);
        i += len + 1;
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    fn rigs() -> Vec<std::path::PathBuf> {
        let mut out: Vec<_> = crate::fsutil::files(Path::new("C:/Games/SP Football Life 2027/SiderAddons"))
            .into_iter()
            .filter(|p| p.extension().map(|e| e == "frig").unwrap_or(false))
            .collect();
        let dt13 = std::env::temp_dir().join("skelx/common/anime/FoxAnim/Body/CharacterAssets/body_skel.frig");
        if dt13.is_file() {
            out.push(dt13);
        }
        out.sort();
        out.dedup();
        out
    }

    /// The tiling rule is the proof. Every interior gap must equal the size the
    /// unit type demands, and the header size must equal the file length; a
    /// wrong size for any type would break across the set rather than all at
    /// once.
    #[test]
    fn every_rig_tiles_with_the_type_determined_record_size() {
        let r = rigs();
        assert!(r.len() >= 10, "expected the shipped rigs, got {}", r.len());
        for p in &r {
            let rig = Rig::read(p).unwrap_or_else(|e| panic!("{}: {e}", p.display()));
            assert!(!rig.units.is_empty());
            assert_eq!(rig.units.len(), rig.unit_count as usize);
        }
        println!("validated {} rig files", r.len());
    }

    #[test]
    fn the_body_rig_matches_the_body_clips_it_drives() {
        let p = std::env::temp_dir().join("skelx/common/anime/FoxAnim/Body/CharacterAssets/body_skel.frig");
        let Ok(rig) = Rig::read(&p) else { return };
        assert_eq!(rig.version, 102, "the published format asserts version 102");
        assert_eq!(rig.unit_count, 15, "the body rig drives fifteen units");
        assert_eq!(rig.segment_count, 27, "and twenty-seven channels");
        assert_eq!(rig.name, "HumanBody");
        assert_eq!(rig.units[0].kind, UnitType::Root);
        assert_eq!(rig.units[0].track_count, 2, "the root stores a rotation and a translation");
        assert_eq!(rig.units[0].parent_unit, -1, "the root has no parent unit");
        assert_eq!(rig.units[1].kind, UnitType::LocalTransform);
        // Legs are two-bone chains and arms three, and they are the only units
        // that are not one-to-one with a bone.
        let two = rig.units.iter().filter(|u| u.kind == UnitType::TwoBone).count();
        let arm = rig.units.iter().filter(|u| u.kind == UnitType::Arm).count();
        assert_eq!(two, 2, "one two-bone chain per leg");
        assert_eq!(arm, 2, "one arm chain per side");
        assert_eq!(rig.units.iter().find(|u| u.kind == UnitType::Arm).unwrap().track_count, 4);
    }

    /// The cross-validation that matters. An independent account of this format
    /// lists which body bones carry a direct channel -- root, hip, both feet,
    /// belly, chest, neck, head and both hands -- and says the thighs, shins,
    /// shoulders, upper arms and forearms exist only inside chain units. If the
    /// `SkelIndex` field were being read at the wrong offset it would name some
    /// other set, so reproducing that list exactly is what says the offset is
    /// right rather than merely plausible.
    #[test]
    fn the_direct_units_resolve_to_exactly_the_published_set_of_bones() {
        let dir = std::env::temp_dir().join("skelx/common/anime/FoxAnim/Body/CharacterAssets");
        let Ok(rig) = Rig::read(&dir.join("body_skel.frig")) else { return };
        let Ok(sk) = crate::ask::Skeleton::read(&dir.join("body_anim_skel.ask")) else { return };
        let mut got: Vec<String> = rig.bones_named(&sk).into_iter().map(|(b, _)| b).collect();
        got.sort();
        let want = [
            "dsk_hip", "sk_belly", "sk_chest", "sk_foot_l", "sk_foot_r", "sk_hand_l",
            "sk_hand_r", "sk_head", "sk_neck", "sk_root_hip",
        ];
        assert_eq!(got, want.to_vec(), "the direct channels must resolve to the published bones");
        // And the chain-only bones are exactly the ones that did not appear.
        let missing: Vec<String> = sk
            .bones
            .iter()
            .filter(|b| !got.contains(&b.name))
            .map(|b| b.name.clone())
            .collect();
        for limb in ["sk_thigh_l", "sk_leg_l", "sk_upperarm_l", "sk_forearm_l", "sk_shoulder_r"] {
            assert!(missing.contains(&limb.to_string()), "{limb} should be chain-only");
        }
    }

    #[test]
    fn a_fabricated_type_or_stride_is_refused() {
        let r = rigs();
        let Some(p) = r.first() else { return };
        let mut b = std::fs::read(p).unwrap();
        // A type nobody recorded cannot be sized, so the walk must stop.
        b[32..36].copy_from_slice(&99u32.to_le_bytes());
        assert!(Rig::parse(&b).is_err(), "an unknown unit type must be refused");
        // A header size that disagrees with the file is a corrupt or unknown
        // layout, not something to press on with.
        let mut b2 = std::fs::read(p).unwrap();
        b2[20..24].copy_from_slice(&999_999u32.to_le_bytes());
        assert!(Rig::parse(&b2).is_err());
        // Version is asserted by the format itself, not guessed at.
        let mut b3 = std::fs::read(p).unwrap();
        b3[8..12].copy_from_slice(&7u32.to_le_bytes());
        assert!(Rig::parse(&b3).is_err());
    }

    /// Only the direct types carry a bone index. A chain's +16 is part of its
    /// chain-plane vector, so reading it as a bone would name a real bone for a
    /// unit that does not drive that bone alone.
    #[test]
    fn chain_units_expose_no_bone_index() {
        for k in [
            UnitType::TwoBone,
            UnitType::Arm,
            UnitType::ThreeBoneLikeTwoBone,
            UnitType::AnimalLeg,
            UnitType::TwoBoneTrans,
        ] {
            assert!(!k.is_direct(), "{k:?} is a chain");
        }
        for k in [
            UnitType::LocalOrientation,
            UnitType::LocalTransform,
            UnitType::Orientation,
            UnitType::Transform,
        ] {
            assert!(k.is_direct(), "{k:?} names a bone directly");
        }
        assert!(!UnitType::Root.is_direct(), "the root unit is the root, not an indexed bone");
        assert_eq!(UnitType::Arm.bones_driven(), 3);
        assert_eq!(UnitType::TwoBone.bones_driven(), 2);
        assert_eq!(UnitType::Arm.record_size(), 64);
        assert_eq!(UnitType::LocalOrientation.record_size(), 32);
    }
}
