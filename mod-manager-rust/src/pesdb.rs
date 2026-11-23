//! Database-table safety: is a pesdb file fit to install?
//!
//! A blind copy is not a way to change a database. The check reads the framing
//! and validates the *declared* body size against the record stride. For WESYS
//! that is the uncompressed size in the header, so no inflation is needed.
//!
//! The distinction that matters is between "readable but the wrong shape" and
//! "not readable at all". Four files in this install (root and carabao cup
//! `Competition.bin`, 933 B, and `CompetitionRegulation.bin`, 9,923 B) carry a
//! fixed 16-byte prefix, 7.8 bits/byte of entropy and no WESYS header, while
//! every other pesdb table here — including the game's own inside dt10 — is
//! plain WESYS. Applying a stride check to their ciphertext would produce a
//! confident "corrupt" verdict about bytes nothing has decoded, so they are
//! reported as unrecognised instead. Whether the game can read them is unknown,
//! not proven bad.

use std::fs;
use std::path::Path;

const WESYS: &[u8; 5] = b"WESYS";

#[derive(Debug, PartialEq, Eq)]
pub enum Framing {
    Wesys,
    Container,
    Plain,
    Unknown,
}

impl Framing {
    pub fn label(&self) -> &'static str {
        match self {
            Framing::Wesys => "wesys",
            Framing::Container => "container",
            Framing::Plain => "plain",
            Framing::Unknown => "unknown",
        }
    }
}

#[derive(Debug)]
pub struct TableInfo {
    pub framing: Framing,
    pub file_size: u64,
    pub body_size: u64,
}

pub fn inspect(path: &Path) -> std::io::Result<TableInfo> {
    let raw = fs::read(path)?;
    let file_size = raw.len() as u64;
    if raw.len() >= 16 && &raw[3..8] == WESYS {
        let body = u32::from_le_bytes([raw[12], raw[13], raw[14], raw[15]]) as u64;
        return Ok(TableInfo { framing: Framing::Wesys, file_size, body_size: body });
    }
    if raw.len() > 24 && raw[4..8] == [8, 0, 0, 0] {
        let header = u32::from_le_bytes([raw[8], raw[9], raw[10], raw[11]]) as usize;
        let body = u32::from_le_bytes([raw[12], raw[13], raw[14], raw[15]]) as u64;
        if (4..=65536).contains(&header) && header as u64 + body <= file_size {
            return Ok(TableInfo { framing: Framing::Container, file_size, body_size: body });
        }
    }
    // Same readability test the container codec uses, so the two never
    // disagree about whether a file is text-like or opaque.
    let head = &raw[..raw.len().min(4096)];
    let printable = head.iter()
        .filter(|&&c| (32..127).contains(&c) || matches!(c, 9 | 10 | 13))
        .count();
    let framing = if !head.is_empty() && printable * 10 > head.len() * 6 {
        Framing::Plain
    } else {
        Framing::Unknown
    };
    Ok(TableInfo { framing, file_size, body_size: file_size })
}

/// Record strides established by measurement, not assumption. Unknown tables
/// (Boots, Glove, Stadium) have no established stride and are accepted on
/// framing alone rather than guessed at.
pub fn stride_for(name: &str) -> Option<u64> {
    Some(match name {
        "Competition.bin" => 36,
        "CompetitionEntry.bin" => 12,
        "CompetitionRegulation.bin" => 2352,
        "Team.bin" => 1532,
        "Player.bin" => 312,
        _ => return None,
    })
}

/// Why a table passed or failed. `Unrecognised` is deliberately not `BadStride`:
/// one is a measured defect, the other is a file nothing here can read.
#[derive(Debug, PartialEq, Eq)]
pub enum Status {
    Ok,
    BadStride,
    Unrecognised,
    Unreadable,
}

#[derive(Debug)]
pub struct Verdict {
    pub ok: bool,
    pub status: Status,
    pub reason: String,
    pub info: Option<TableInfo>,
}

pub fn validate(path: &Path) -> Verdict {
    let name = path.file_name().unwrap().to_string_lossy().to_string();
    let info = match inspect(path) {
        Ok(i) => i,
        Err(e) => {
            return Verdict {
                ok: false, status: Status::Unreadable,
                reason: format!("unreadable: {e}"), info: None,
            }
        }
    };
    if info.framing == Framing::Unknown {
        return Verdict {
            ok: false,
            status: Status::Unrecognised,
            reason: format!(
                "{} B of opaque data with no WESYS header — not a table this \
                 codec can read, so its record layout cannot be checked",
                info.file_size),
            info: Some(info),
        };
    }
    match stride_for(&name) {
        None => Verdict {
            ok: true,
            status: Status::Ok,
            reason: format!("{} B {}, no established stride for {name}",
                            info.body_size, info.framing.label()),
            info: Some(info),
        },
        Some(stride) => {
            let rem = info.body_size % stride;
            if rem != 0 {
                Verdict {
                    ok: false,
                    status: Status::BadStride,
                    reason: format!(
                        "{} B does not tile at stride {stride} ({rem} left over)",
                        info.body_size
                    ),
                    info: Some(info),
                }
            } else {
                Verdict {
                    ok: true,
                    status: Status::Ok,
                    reason: format!(
                        "{} B = {} records of {stride}",
                        info.body_size,
                        info.body_size / stride
                    ),
                    info: Some(info),
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // Each test gets its own directory: they run in parallel and share a
    // filename, so a common directory let one test overwrite another's file.
    fn write_tmp(case: &str, name: &str, bytes: &[u8]) -> std::path::PathBuf {
        let dir = std::env::temp_dir().join("fl27mm_pesdb_test").join(case);
        fs::create_dir_all(&dir).unwrap();
        let p = dir.join(name);
        fs::write(&p, bytes).unwrap();
        p
    }

    #[test]
    fn opaque_data_is_unrecognised_not_called_corrupt() {
        // The real root/carahao Competition.bin shape: high entropy, no header.
        let bytes: Vec<u8> = (0..933).map(|i| ((i * 137 + 11) % 256) as u8).collect();
        let p = write_tmp("opaque", "Competition.bin", &bytes);
        let v = validate(&p);
        assert!(!v.ok);
        assert_eq!(v.status, Status::Unrecognised);
        assert!(!v.reason.contains("left over"),
                "must not claim a stride defect about unreadable bytes: {}", v.reason);
    }

    #[test]
    fn readable_table_that_does_not_tile_is_a_stride_defect() {
        // Text-like bytes, so the framing is plain and the stride check applies.
        let bytes = vec![b'A'; 36 * 25 + 33];
        let p = write_tmp("refuse", "Competition.bin", &bytes);
        let v = validate(&p);
        assert!(!v.ok);
        assert_eq!(v.status, Status::BadStride);
        assert!(v.reason.contains("33 left over"), "{}", v.reason);
    }

    #[test]
    fn plain_table_that_tiles_is_accepted() {
        let p = write_tmp("accept", "Competition.bin", &vec![b'A'; 36 * 92]);
        let v = validate(&p);
        assert!(v.ok);
        assert!(v.reason.contains("92 records"));
    }

    #[test]
    fn wesys_uses_the_declared_uncompressed_size() {
        let mut raw = vec![0u8; 16];
        raw[3..8].copy_from_slice(WESYS);
        raw[8..12].copy_from_slice(&100u32.to_le_bytes());
        raw[12..16].copy_from_slice(&(2352u32 * 4).to_le_bytes());
        raw.extend_from_slice(&[0u8; 100]);
        let p = write_tmp("wesys", "CompetitionRegulation.bin", &raw);
        let v = validate(&p);
        assert!(v.ok, "{}", v.reason);
        assert_eq!(v.info.unwrap().framing, Framing::Wesys);
    }

    #[test]
    fn unknown_stride_is_accepted_on_framing() {
        let p = write_tmp("unknown", "Boots.bin", &vec![b'A'; 30_400]);
        assert!(validate(&p).ok);
    }
}
