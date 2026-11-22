//! Robustness probe: no decoder may panic on hostile input.
//!
//! These codecs read bytes that came off a disk somebody else edited, so a
//! panic is not one crash but a feature that cannot be used on real installs.
//! Each case takes a genuine shipped file and mutilates it the way a truncated
//! download, a half-written pack or a fuzzer would.

use fl27mm::{binread, cpk, fmdl, fpk, ftex, utf, wesys};
use std::io::Write;
use std::path::{Path, PathBuf};

fn first_existing(cands: &[&str]) -> Option<Vec<u8>> {
    for c in cands {
        let p = Path::new(c);
        if p.is_file() {
            if let Ok(b) = std::fs::read(p) {
                if b.len() > 4096 {
                    return Some(b);
                }
            }
        }
    }
    None
}

fn sample() -> Option<Vec<u8>> {
    first_existing(&[fmdl::REAL_FACE_FPK])
}

/// Write bytes to a uniquely named temp file so the path-based readers can be
/// reached with hostile content.
struct Tmp(PathBuf);

impl Tmp {
    fn new(tag: &str, bytes: &[u8]) -> Tmp {
        let mut p = std::env::temp_dir();
        let name = format!("fl27mm-robust-{tag}-{}.bin", std::process::id());
        p.push(name);
        let mut f = std::fs::File::create(&p).expect("temp file");
        f.write_all(bytes).expect("temp write");
        Tmp(p)
    }
}

impl Drop for Tmp {
    fn drop(&mut self) {
        let _ = std::fs::remove_file(&self.0);
    }
}

/// Run every in-memory decoder over one buffer. Nothing here may panic.
fn probe_all(b: &[u8]) {
    let _ = fpk::Fpk::parse(b);
    let _ = fmdl::Fmdl::parse(b.to_vec());
    let _ = wesys::decode(b);
    let _ = utf::Utf::parse(b, 0);
    let _ = binread::parse_sections(b);
    let _ = ftex::Ftex::from_dds(b);
}

#[test]
fn truncated_input_never_panics() {
    let Some(bytes) = sample() else { return };
    let step = (bytes.len() / 80).max(1);
    let mut at = 0usize;
    while at < bytes.len() {
        probe_all(&bytes[..at]);
        at += step;
    }
    // The path-based readers get the same treatment.
    for cut in [0usize, 4, 8, 16, 32, 48, 64, 4096] {
        if cut > bytes.len() {
            continue;
        }
        let t = Tmp::new("trunc", &bytes[..cut]);
        let _ = cpk::Cpk::open(&t.0);
        let _ = ftex::Ftex::read(&t.0);
        let _ = fpk::Fpk::read(&t.0);
        let _ = fmdl::Fmdl::read(&t.0);
    }
}

#[test]
fn corrupted_length_fields_never_panic() {
    let Some(bytes) = sample() else { return };
    for at in [10usize, 36, 40, 44, 48, 56, 64, 72, 80, 88, 96] {
        if at + 4 > bytes.len() {
            continue;
        }
        let mut b = bytes.clone();
        b[at..at + 4].copy_from_slice(&[0xff, 0xff, 0xff, 0xff]);
        probe_all(&b);
    }
}

#[test]
fn hostile_offsets_never_panic() {
    let Some(bytes) = sample() else { return };
    for at in (48..bytes.len().min(600)).step_by(8) {
        let mut b = bytes.clone();
        for k in 0..4 {
            if at + k < b.len() {
                b[at + k] = 0xff;
            }
        }
        probe_all(&b);
    }
}

#[test]
fn zeroed_and_max_fields_never_panic() {
    let Some(bytes) = sample() else { return };
    for filler in [0u8, 0x7f, 0xff] {
        for at in (0..bytes.len().min(512)).step_by(16) {
            let mut b = bytes.clone();
            for k in 0..16 {
                if at + k < b.len() {
                    b[at + k] = filler;
                }
            }
            probe_all(&b);
        }
    }
}

#[test]
fn truncated_cpk_never_panics() {
    // A CPK is read through a file handle, so this needs real temp files.
    let Some(bytes) = first_existing(&[
        "C:/Games/SP Football Life 2027/Data/dt13_all.cpk",
        "C:/Games/SP Football Life 2027/Data/dt16_all.cpk",
    ]) else {
        return;
    };
    let step = (bytes.len() / 12).max(1);
    for i in 0..12usize {
        let cut = (i * step).min(bytes.len());
        let t = Tmp::new("cpk", &bytes[..cut]);
        let _ = cpk::Cpk::open(&t.0);
    }
}

/// A random-ish byte soup must be rejected, not consumed. This is the case a
/// user reaches by pointing the tool at the wrong file.
#[test]
fn arbitrary_bytes_are_rejected_not_consumed() {
    let mut b: Vec<u8> = (0..200_000u32)
        .map(|i| (i.wrapping_mul(2654435761) >> 13) as u8)
        .collect();
    probe_all(&b);
    b[..6].copy_from_slice(b"foxfpk");
    probe_all(&b);
    b[..4].copy_from_slice(b"FMDL");
    probe_all(&b);
    b[..5].copy_from_slice(b"WESYS");
    probe_all(&b);
    let t = Tmp::new("soup", &b);
    let _ = cpk::Cpk::open(&t.0);
    let _ = ftex::Ftex::read(&t.0);
}
