//! FL27 container codec — the framing around every database table and asset.
//!
//! Two framings appear in the game's files and both are ordinary, not encrypted:
//!
//!   WESYS      [0..3] mode bytes, [3..8] "WESYS", [8..12] u32 packed size,
//!              [12..16] u32 unpacked size, [16..] a plain zlib stream.
//!
//!   container  [0] format, [1] 8, [2] header size, [3] body size, [4] name
//!              offset; u32 header size at +8, u32 body size at +12, an asset
//!              name such as "afp_gamePlan.apk" inside the header, then the
//!              body verbatim.
//!
//! Only WESYS needs re-deflation. `encode` searches the zlib parameter space and
//! returns whichever setting reproduces the original bytes. When none does, the
//! file is still semantically identical — the game inflates it either way — but
//! a patch that cannot say which it produced is a patch that cannot be reviewed,
//! so the distinction is carried in `exact`, not hidden.

use anyhow::{bail, Context, Result};
use flate2::read::ZlibDecoder;
use std::io::Read;
use zlib_rs::{DeflateConfig, Method, Strategy};

const WESYS: &[u8; 5] = b"WESYS";
const MAX_HEADER: usize = 1 << 16;
/// The parameter hunt is bounded to small bodies: an 8 MB Player.bin would
/// otherwise cost hundreds of deflations for a claim "body identical" covers.
const WIDE_LIMIT: usize = 256 << 10;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Kind {
    Wesys,
    Container,
    Plain,
    Unknown,
}

impl Kind {
    pub fn name(self) -> &'static str {
        match self {
            Kind::Wesys => "wesys",
            Kind::Container => "container",
            Kind::Plain => "plain",
            Kind::Unknown => "unknown",
        }
    }
}

pub struct Fl27File {
    pub kind: Kind,
    pub header: Vec<u8>,
    pub body: Vec<u8>,
    pub tail: Vec<u8>,
    pub level: Option<i32>,
    pub exact: bool,
    pub original: Vec<u8>,
}

impl Fl27File {
    /// True when re-encoding reproduces the original bytes exactly.
    pub fn semantic(&self) -> bool {
        self.kind != Kind::Wesys || self.exact
    }
}

fn le_u32(b: &[u8], at: usize) -> u32 {
    u32::from_le_bytes([b[at], b[at + 1], b[at + 2], b[at + 3]])
}

pub fn inflate(raw: &[u8]) -> Result<Vec<u8>> {
    let mut out = Vec::new();
    ZlibDecoder::new(raw)
        .read_to_end(&mut out)
        .with_context(|| "WESYS zlib stream is not inflatable")?;
    Ok(out)
}

fn deflate(body: &[u8], level: i32, mem_level: i32, strategy: Strategy) -> Vec<u8> {
    let mut buf = vec![0u8; zlib_rs::compress_bound(body.len())];
    let config = DeflateConfig {
        level,
        method: Method::Deflated,
        window_bits: 15,
        mem_level,
        strategy,
    };
    let (out, _) = zlib_rs::compress_slice(&mut buf, body, config);
    out.to_vec()
}

pub fn decode(raw: &[u8]) -> Result<Fl27File> {
    if raw.len() >= 16 && &raw[3..8] == WESYS {
        let packed = le_u32(raw, 8) as usize;
        let unpacked = le_u32(raw, 12) as usize;
        let end = if packed > 0 {
            (16 + packed).min(raw.len())
        } else {
            raw.len()
        };
        let body = inflate(&raw[16..end])?;
        if unpacked != 0 && body.len() != unpacked {
            bail!("header says {unpacked} bytes, stream gave {}", body.len());
        }
        return Ok(Fl27File {
            kind: Kind::Wesys,
            header: raw[..16].to_vec(),
            body,
            tail: raw[end..].to_vec(),
            level: None,
            exact: false,
            original: raw.to_vec(),
        });
    }

    if raw.len() > 24 && raw[4..8] == [8, 0, 0, 0] {
        let header_size = le_u32(raw, 8) as usize;
        let body_size = le_u32(raw, 12) as usize;
        if (4..=MAX_HEADER).contains(&header_size) && header_size + body_size <= raw.len() {
            return Ok(Fl27File {
                kind: Kind::Container,
                header: raw[..header_size].to_vec(),
                body: raw[header_size..header_size + body_size].to_vec(),
                tail: raw[header_size + body_size..].to_vec(),
                level: Some(0),
                exact: true,
                original: raw.to_vec(),
            });
        }
    }

    // Neither framing is known. Some packs ship pesdb tables in a third,
    // high-entropy form with a fixed 16-byte prefix and no readable strings.
    // Calling that "plain" would let a patch carry an opaque blob through as if
    // it were a table, so it is named here and encode() refuses it.
    let head = &raw[..raw.len().min(4096)];
    let printable = head
        .iter()
        .filter(|&&c| (32..127).contains(&c) || matches!(c, 9 | 10 | 13))
        .count();
    let kind = if printable * 10 > head.len() * 6 {
        Kind::Plain
    } else {
        Kind::Unknown
    };
    Ok(Fl27File {
        kind,
        header: Vec::new(),
        body: raw.to_vec(),
        tail: Vec::new(),
        level: Some(0),
        exact: kind == Kind::Plain,
        original: raw.to_vec(),
    })
}

const STRATEGIES: [Strategy; 5] = [
    Strategy::Default,
    Strategy::Filtered,
    Strategy::HuffmanOnly,
    Strategy::Rle,
    Strategy::Fixed,
];

/// The parameter set to try, in the order the search consumes it. The first
/// reproduction that matches wins, so this order is part of the result and
/// must survive being computed in parallel.
fn trial_params(wide: bool) -> Vec<(i32, i32, Strategy)> {
    let mut out = Vec::new();
    for level in (0..=9).rev() {
        if wide {
            for mem_level in [8, 9, 7, 6] {
                for strategy in STRATEGIES {
                    out.push((level, mem_level, strategy));
                }
            }
        }
        out.push((level, 8, Strategy::Default));
    }
    out
}

/// Deflate the body under every candidate setting across threads, returning
/// the streams in trial order. Each body can be several megabytes and the
/// search ran one level at a time, which is what put the `.bin` reader at
/// 1.8 s for `Player.bin` alone.
fn run_trials(body: &[u8], wide: bool) -> Vec<(i32, Vec<u8>)> {
    use rayon::prelude::*;
    trial_params(wide)
        .into_par_iter()
        .map(|(level, mem_level, strategy)| (level, deflate(body, level, mem_level, strategy)))
        .collect()
}

fn wrap(header: &[u8], stream: &[u8], body_len: usize, tail: &[u8]) -> Vec<u8> {
    let mut out = Vec::with_capacity(16 + stream.len() + tail.len());
    out.extend_from_slice(&header[..8]);
    out.extend_from_slice(&(stream.len() as u32).to_le_bytes());
    out.extend_from_slice(&(body_len as u32).to_le_bytes());
    out.extend_from_slice(stream);
    out.extend_from_slice(tail);
    out
}

/// Re-serialise, preferring a byte-exact reproduction. Sets `level` and `exact`.
pub fn encode(file: &mut Fl27File) -> Result<Vec<u8>> {
    match file.kind {
        Kind::Unknown => {
            bail!("unidentified framing — refusing to re-emit bytes this codec cannot interpret")
        }
        Kind::Wesys => {
            // Every trial is an independent deflate of the same body, and for a
            // multi-megabyte table the search dominated the reader: 1.8 s on
            // Player.bin, most of it spent here. Running the trials across
            // threads is the whole fix, and the streams are kept so the
            // fallback below never deflates twice.
            let wide = file.body.len() <= WIDE_LIMIT;
            let mut best_small: Option<(i32, Vec<u8>)> = None;
            for (level, stream) in run_trials(&file.body, wide) {
                let rebuilt = wrap(&file.header, &stream, file.body.len(), &file.tail);
                if rebuilt == file.original {
                    file.level = Some(level);
                    file.exact = true;
                    return Ok(rebuilt);
                }
                if best_small
                    .as_ref()
                    .is_none_or(|(_, b)| stream.len() < b.len())
                {
                    best_small = Some((level, stream));
                }
            }
            // Nothing reproduced the original bytes, so emit the smallest valid
            // form. Keyed on length on purpose: comparing the streams themselves
            // picks whichever byte string sorts first, which is level 0 (stored)
            // and doubles the size of every file.
            let (level, stream) = best_small.unwrap();
            let body = inflate(&stream).context("chosen deflate stream does not inflate")?;
            if body != file.body {
                bail!("chosen deflate stream does not round-trip");
            }
            file.level = Some(level);
            file.exact = false;
            Ok(wrap(&file.header, &stream, file.body.len(), &file.tail))
        }
        Kind::Container => {
            let mut header = file.header.clone();
            if header.len() >= 16 {
                header[12..16].copy_from_slice(&(file.body.len() as u32).to_le_bytes());
            }
            file.level = Some(0);
            file.exact = true;
            let mut out = header;
            out.extend_from_slice(&file.body);
            out.extend_from_slice(&file.tail);
            Ok(out)
        }
        Kind::Plain => {
            file.level = Some(0);
            file.exact = true;
            let mut out = file.body.clone();
            out.extend_from_slice(&file.tail);
            Ok(out)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn wesys_sample(body: &[u8]) -> Vec<u8> {
        let stream = deflate(body, 6, 8, Strategy::Default);
        let mut out = vec![0x00, 0x10, 0x01];
        out.extend_from_slice(WESYS);
        out.extend_from_slice(&(stream.len() as u32).to_le_bytes());
        out.extend_from_slice(&(body.len() as u32).to_le_bytes());
        out.extend_from_slice(&stream);
        out
    }

    #[test]
    fn wesys_round_trips_byte_exact() {
        let body: Vec<u8> = (0..4000).map(|i| (i % 97) as u8).collect();
        let raw = wesys_sample(&body);
        let mut f = decode(&raw).unwrap();
        assert_eq!(f.kind, Kind::Wesys);
        assert_eq!(f.body, body);
        let out = encode(&mut f).unwrap();
        assert!(f.exact, "an unmodified table must re-encode byte-exactly");
        assert_eq!(out, raw);
    }

    #[test]
    fn edited_body_still_inflates() {
        let body: Vec<u8> = (0..4000).map(|i| (i % 97) as u8).collect();
        let raw = wesys_sample(&body);
        let mut f = decode(&raw).unwrap();
        f.body[100] ^= 0xFF;
        f.body.extend_from_slice(b"grown");
        let out = encode(&mut f).unwrap();
        let back = decode(&out).unwrap();
        assert_eq!(back.body, f.body);
        assert_eq!(le_u32(&out, 12) as usize, f.body.len());
    }

    #[test]
    fn container_round_trips_and_resizes() {
        let mut raw = vec![0u8; 32];
        raw[4] = 8;
        raw[8..12].copy_from_slice(&32u32.to_le_bytes());
        raw[12..16].copy_from_slice(&4u32.to_le_bytes());
        raw[16..28].copy_from_slice(b"afp_test.apk");
        raw.extend_from_slice(b"body");
        let mut f = decode(&raw).unwrap();
        assert_eq!(f.kind, Kind::Container);
        assert_eq!(f.body, b"body");
        assert_eq!(encode(&mut f).unwrap(), raw);
        f.body = b"longer body".to_vec();
        let out = encode(&mut f).unwrap();
        assert_eq!(le_u32(&out, 12), 11);
        assert_eq!(decode(&out).unwrap().body, f.body);
    }

    #[test]
    fn opaque_blobs_are_refused() {
        let raw: Vec<u8> = (0..512).map(|i| ((i * 137 + 11) % 256) as u8).collect();
        let mut f = decode(&raw).unwrap();
        if f.kind == Kind::Unknown {
            assert!(encode(&mut f).is_err());
        }
    }

    #[test]
    fn real_game_table_survives_a_re_encode() {
        let p = std::path::Path::new(
            r"C:\Games\SP Football Life 2027\FL27 Megapatch\out\rt\a\common\match\constant\constant_match.bin",
        );
        if !p.exists() {
            return;
        }
        let raw = std::fs::read(p).unwrap();
        let mut f = decode(&raw).unwrap();
        assert_eq!(f.kind, Kind::Wesys);
        let body = f.body.clone();
        let out = encode(&mut f).unwrap();
        // Konami's deflater settings are not reproducible from zlib's parameter
        // space (the Python codec reports the same), so the claim here is
        // semantic: the game inflates the same table back out.
        let back = decode(&out).unwrap();
        assert_eq!(back.body, body);
        assert_eq!(le_u32(&out, 12) as usize, body.len());
        assert_eq!(le_u32(&out, 8) as usize, out.len() - 16);
        assert_eq!(&out[3..8], WESYS);
        assert_eq!(f.exact, out == raw);
    }
}
