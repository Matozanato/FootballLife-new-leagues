//! Hostile input that needs no game install.
//!
//! Every decoder is fed small synthetic files whose size and count fields are
//! lies. Two things must hold: nothing panics, and no single allocation is
//! larger than a sane cap. The cap is enforced by the allocator itself, so a
//! `Vec::with_capacity(n)` sized straight from a file fails this test instead
//! of asking the OS for hundreds of gigabytes.

use std::alloc::{GlobalAlloc, Layout, System};
use std::io::Write;
use std::path::PathBuf;

use fl27mm::{ask, binread, cpk, crilayla, fmdl, fpk, frig, ftex, gani, utf, wesys};

/// 256 MB. Nothing these decoders read from a few kilobytes of input may ask
/// for more than this in one go.
const CAP: usize = 256 << 20;

struct Capped;

unsafe impl GlobalAlloc for Capped {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        if layout.size() > CAP {
            eprintln!("allocation of {} bytes exceeds the hostile-input cap", layout.size());
            std::process::abort();
        }
        System.alloc(layout)
    }
    unsafe fn alloc_zeroed(&self, layout: Layout) -> *mut u8 {
        if layout.size() > CAP {
            eprintln!("zeroed allocation of {} bytes exceeds the hostile-input cap", layout.size());
            std::process::abort();
        }
        System.alloc_zeroed(layout)
    }
    unsafe fn dealloc(&self, ptr: *mut u8, layout: Layout) {
        System.dealloc(ptr, layout)
    }
    unsafe fn realloc(&self, ptr: *mut u8, layout: Layout, new_size: usize) -> *mut u8 {
        if new_size > CAP {
            eprintln!("reallocation to {new_size} bytes exceeds the hostile-input cap");
            std::process::abort();
        }
        System.realloc(ptr, layout, new_size)
    }
}

#[global_allocator]
static ALLOC: Capped = Capped;

/// Small deterministic generator so failures reproduce.
struct Rng(u64);

impl Rng {
    fn next(&mut self) -> u64 {
        self.0 ^= self.0 << 13;
        self.0 ^= self.0 >> 7;
        self.0 ^= self.0 << 17;
        self.0
    }
    fn bytes(&mut self, n: usize) -> Vec<u8> {
        (0..n).map(|_| self.next() as u8).collect()
    }
}

struct Tmp(PathBuf);

impl Tmp {
    fn new(tag: &str, bytes: &[u8]) -> Tmp {
        let mut p = std::env::temp_dir();
        p.push(format!("fl27mm-hostile-{tag}-{}.bin", std::process::id()));
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

fn probe(b: &[u8]) {
    let _ = fpk::Fpk::parse(b);
    let _ = fmdl::Fmdl::parse(b.to_vec());
    let _ = wesys::decode(b);
    let _ = utf::Utf::parse(b, 0);
    let _ = binread::parse_sections(b);
    let _ = ftex::Ftex::parse(b);
    let _ = ftex::Ftex::from_dds(b);
    let _ = gani::Clip::parse(b);
    let _ = ask::Skeleton::parse(b);
    let _ = frig::Rig::parse(b);
    let _ = cpk::crilayla_decompress(b);
    let _ = crilayla::verify(b, b);
}

/// Overwrite every aligned u32 in turn with values a liar would choose.
fn lie_everywhere(seed: &[u8]) {
    for at in (0..seed.len().saturating_sub(3)).step_by(4) {
        for v in [0u32, 1, 0x7fff_ffff, 0xffff_ffff, 0x0100_0000, 0x0000_ffff] {
            let mut b = seed.to_vec();
            b[at..at + 4].copy_from_slice(&v.to_le_bytes());
            probe(&b);
            b[at..at + 4].copy_from_slice(&v.to_be_bytes());
            probe(&b);
        }
    }
}

fn with_magic(magic: &[u8], len: usize, rng: &mut Rng) -> Vec<u8> {
    let mut b = rng.bytes(len);
    b[..magic.len()].copy_from_slice(magic);
    b
}

#[test]
fn random_bytes_with_every_magic_never_panic_or_overallocate() {
    let mut rng = Rng(0x9e37_79b9_7f4a_7c15);
    let magics: [&[u8]; 9] = [
        b"", b"DDS ", b"FTEX", b"@UTF", b"CRILAYLA", b"foxfpk", b"FMDL", b"WESYS", b"CPK ",
    ];
    for magic in magics {
        for len in [0usize, 4, 16, 64, 128, 176, 256, 300, 1024, 4096] {
            for _ in 0..24 {
                if len < magic.len() {
                    continue;
                }
                probe(&with_magic(magic, len, &mut rng));
            }
        }
    }
}

#[test]
fn lying_size_fields_never_panic_or_overallocate() {
    let mut rng = Rng(0x1234_5678_9abc_def1);
    for magic in [&b"DDS "[..], b"FTEX", b"@UTF", b"CRILAYLA", b"foxfpk", b"FMDL"] {
        let mut seed = vec![0u8; 256];
        seed[..magic.len()].copy_from_slice(magic);
        lie_everywhere(&seed);
        lie_everywhere(&with_magic(magic, 256, &mut rng));
    }
    // A gani header is 176 bytes; give it a plausible magic and lie about it.
    let mut g = vec![0u8; 256];
    g[..4].copy_from_slice(&[0xd2, 0xa2, 0xfc, 0x0b]);
    lie_everywhere(&g);
}

#[test]
fn a_built_utf_table_with_lying_fields_never_overallocates() {
    let table = utf::Builder::new("T")
        .col("Name", 0x5a)
        .col("Size", 0x55)
        .row(utf::row(&[
            ("Name", utf::Value::Str("a".into())),
            ("Size", utf::Value::Int(7)),
        ]))
        .encode()
        .expect("encode");
    lie_everywhere(&table);
}

#[test]
fn tiny_hostile_cpk_files_are_rejected() {
    let mut rng = Rng(42);
    for len in [16usize, 64, 128, 512, 2048] {
        for _ in 0..16 {
            let b = with_magic(b"CPK ", len, &mut rng);
            let t = Tmp::new("cpk", &b);
            let _ = cpk::Cpk::open(&t.0);
        }
    }
    // A header packet that carries a real @UTF table whose TOC claims to be huge.
    let header = utf::Builder::new("CpkHeader")
        .col("ContentOffset", 0x56)
        .col("TocOffset", 0x56)
        .col("TocSize", 0x56)
        .row(utf::row(&[
            ("ContentOffset", utf::Value::Int(0)),
            ("TocOffset", utf::Value::Int(16)),
            ("TocSize", utf::Value::Int(u64::MAX / 2)),
        ]))
        .encode()
        .expect("encode");
    let mut b = b"CPK \xff\x00\x00\x00".to_vec();
    b.extend_from_slice(&(header.len() as u32).to_le_bytes());
    b.extend_from_slice(&[0; 4]);
    b.extend_from_slice(&header);
    let t = Tmp::new("cpk-toc", &b);
    assert!(cpk::Cpk::open(&t.0).is_err());
    // Same file with every u32 of the table replaced by liars.
    for at in (16..b.len().saturating_sub(3)).step_by(4) {
        for v in [0u32, 0xffff_ffff, 0x7fff_ffff] {
            let mut c = b.clone();
            c[at..at + 4].copy_from_slice(&v.to_be_bytes());
            let t = Tmp::new("cpk-lie", &c);
            let _ = cpk::Cpk::open(&t.0);
        }
    }
}

/// A real archive written by our own packer, then damaged byte by byte. This
/// reaches the TOC, the CRILAYLA payload and `read_file` with lying entries.
#[test]
fn a_packed_cpk_damaged_anywhere_never_panics_or_overallocates() {
    let root = std::env::temp_dir().join(format!("fl27mm-hostile-pack-{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&root);
    let src = root.join("src/common/script");
    std::fs::create_dir_all(&src).unwrap();
    let mut rng = Rng(7);
    let mut body = b"compressible ".repeat(400);
    body.extend_from_slice(&rng.bytes(300));
    std::fs::write(src.join("a.bin"), &body).unwrap();
    std::fs::write(src.join("b.bin"), b"tiny").unwrap();
    let archive = root.join("t.cpk");
    cpk::pack(&root.join("src"), &archive, true).unwrap();
    let good = std::fs::read(&archive).unwrap();
    let mut rng = Rng(99);
    for i in 0..600 {
        let mut b = good.clone();
        let at = if i < 300 { i * 4 % b.len() } else { rng.next() as usize % b.len() };
        let v = [0u8, 0xff, 0x7f, rng.next() as u8][i % 4];
        for k in 0..4 {
            if at + k < b.len() {
                b[at + k] = v;
            }
        }
        let t = Tmp::new("packed", &b);
        if let Ok(c) = cpk::Cpk::open(&t.0) {
            for f in &c.files {
                let _ = c.read_file(f);
            }
        }
    }
    let _ = std::fs::remove_dir_all(root);
}
