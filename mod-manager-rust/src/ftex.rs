//! Fox Engine textures (.ftex) <-> DDS.
//!
//! Header, 64 bytes little endian:
//!   [0..4]   "FTEX"
//!   [4..8]   f32 format version — PES ships 2.03 and 2.04 side by side, so
//!            this is a field to carry, not a magic to match
//!   [8..16]  i16 pixel format, width, height, depth
//!   [16]     u8 mip count      [17] u8 nrt flag     [18..20] i16 flags
//!   [20..28] two i32 the Fox tooling expects to be 1 and 0; PES writes 0 and 0
//!   [28..32] i32 texture type (PES uses the small values: 1 material,
//!            3 diffuse, 7 cube, 9 normal — not Fox's 0x0100000x)
//!   [32..34] u8 ftexs file count, u8 additional count
//!   [34..48] reserved zeros
//!   [48..64] 16-byte hash (PES leaves it zero)
//!
//! Then one 16-byte info per mip: i32 offset, i32 decompressed size, i32 block
//! size, u8 index, u8 ftexs number, i16 chunk count. `offset` is absolute within
//! the .ftex when the ftexs number is 0, otherwise within `<name>.<n>.ftexs`.
//!
//! At that offset sits `chunk_count` 8-byte indexes — u16 stored size, u16 raw
//! size, u32 offset relative to the mip block (0x80000000 marks a relative
//! back-reference) — followed by the payloads. A payload is zlib when its
//! stored size differs from its raw size. Both size fields are 16-bit, so a
//! chunk holding exactly 64 KiB of raw data reads as zero; PES uses 64 KiB
//! chunks for large mips and this build writes 16 KiB ones.
//!
//! Mips are laid out smallest first in the file, but indexed largest first.
//! PES packs the blocks tightly with no alignment padding.
//!
//! The pixel format codes, measured over the 236,930 `.ftex` files in this
//! install (bytes per 4x4 block, or per texel for the uncompressed ones):
//!
//! ```text
//! 0  BGRA8     4/tex   9  BC5      16/blk   12 RGBA16F  8/tex
//! 1  L8        1/tex   10 BC6H     16/blk   14 RG16     4/tex
//! 2  BC1       8/blk   11 BC7      16/blk
//! 3  BC2      16/blk
//! 4  BC3      16/blk
//! ```
//!
//! BC5 and BC7 are measured, not inferred. Decoding code 9 as BC5 gives
//! neighbour-to-neighbour smoothness 0.9 against 42+ for every other 16-byte
//! codec, and its endpoint bytes cluster on 128, which is the unsigned
//! (BC5_UNORM) normal-map convention rather than the signed one. Code 11 has
//! 99.8% legal BC7 mode prefixes, and `.dds` siblings shipped with the packs
//! name it DXGI 98 = BC7_UNORM. Codes 10, 12 and 14 are sized from the data
//! (16, 8 and 4 bytes per texel) but only 12 is decoded for preview; a 33x33x33
//! RGBA16F volume LUT has half-float 1.0 in the fourth channel, which is what
//! identifies it.

use std::fs;
use std::path::Path;

use anyhow::{bail, Context, Result};
use flate2::read::ZlibDecoder;
use flate2::write::ZlibEncoder;
use flate2::Compression;
use std::io::{Read, Write};

const MAGIC: [u8; 4] = *b"FTEX";
/// f32 2.03 — the version Fox tooling writes, and one of the two PES ships.
const VERSION_DEFAULT: u32 = 0x4001_EB85;
const HEADER: usize = 64;
const MIP_INFO: usize = 16;
const CHUNK: usize = 16 * 1024;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PixelFormat {
    Bgra8,
    L8,
    Bc1,
    Bc2,
    Bc3,
    Bc5,
    Bc6h,
    Bc7,
    Rgba16f,
    Rg16,
}

impl PixelFormat {
    fn from_code(v: u16) -> Result<PixelFormat> {
        Ok(match v {
            0 => PixelFormat::Bgra8,
            1 => PixelFormat::L8,
            2 => PixelFormat::Bc1,
            3 => PixelFormat::Bc2,
            4 => PixelFormat::Bc3,
            9 => PixelFormat::Bc5,
            10 => PixelFormat::Bc6h,
            11 => PixelFormat::Bc7,
            12 => PixelFormat::Rgba16f,
            14 => PixelFormat::Rg16,
            // Codes 5-8, 13 and 15+ never appear in this install, so an
            // unknown one is a new format rather than a corrupt file. Say so
            // with the size, which is what a reader actually needs.
            _ => bail!("ftex pixel format {v} is not one this build knows"),
        })
    }
    fn code(self) -> u16 {
        match self {
            PixelFormat::Bgra8 => 0,
            PixelFormat::L8 => 1,
            PixelFormat::Bc1 => 2,
            PixelFormat::Bc2 => 3,
            PixelFormat::Bc3 => 4,
            PixelFormat::Bc5 => 9,
            PixelFormat::Bc6h => 10,
            PixelFormat::Bc7 => 11,
            PixelFormat::Rgba16f => 12,
            PixelFormat::Rg16 => 14,
        }
    }
    pub fn name(self) -> &'static str {
        match self {
            PixelFormat::Bgra8 => "BGRA8",
            PixelFormat::L8 => "L8",
            PixelFormat::Bc1 => "BC1/DXT1",
            PixelFormat::Bc2 => "BC2/DXT3",
            PixelFormat::Bc3 => "BC3/DXT5",
            PixelFormat::Bc5 => "BC5",
            PixelFormat::Bc6h => "BC6H",
            PixelFormat::Bc7 => "BC7",
            PixelFormat::Rgba16f => "RGBA16F",
            PixelFormat::Rg16 => "RG16",
        }
    }
    /// Bytes one mip level occupies. Block formats round up to whole 4x4 blocks.
    pub fn level_size(self, w: u32, h: u32) -> usize {
        let w = w.max(1) as usize;
        let h = h.max(1) as usize;
        let blocks = w.div_ceil(4) * h.div_ceil(4);
        match self {
            PixelFormat::Bgra8 => w * h * 4,
            PixelFormat::L8 => w * h,
            PixelFormat::Rgba16f => w * h * 8,
            PixelFormat::Rg16 => w * h * 4,
            PixelFormat::Bc1 => blocks * 8,
            PixelFormat::Bc2
            | PixelFormat::Bc3
            | PixelFormat::Bc5
            | PixelFormat::Bc6h
            | PixelFormat::Bc7 => blocks * 16,
        }
    }
    fn block_bytes(self) -> Option<usize> {
        match self {
            PixelFormat::Bc1 => Some(8),
            PixelFormat::Bc2
            | PixelFormat::Bc3
            | PixelFormat::Bc5
            | PixelFormat::Bc6h
            | PixelFormat::Bc7 => Some(16),
            _ => None,
        }
    }
    /// Bytes per texel for the uncompressed formats, used for the DDS pitch.
    fn texel_bytes(self) -> u32 {
        match self {
            PixelFormat::Bgra8 | PixelFormat::Rg16 => 4,
            PixelFormat::L8 => 1,
            PixelFormat::Rgba16f => 8,
            _ => 0,
        }
    }
    /// DXGI format number for the DDS DX10 header, which is the only way to
    /// name BC5, BC6H and BC7 unambiguously. Classic FourCCs cannot express
    /// them, and a wrong FourCC makes the file look corrupt in other tools.
    fn dxgi(self) -> Option<u32> {
        match self {
            PixelFormat::Bc5 => Some(83),     // BC5_UNORM, endpoints centred on 128
            PixelFormat::Bc6h => Some(95),    // BC6H_UF16
            PixelFormat::Bc7 => Some(98),     // BC7_UNORM
            PixelFormat::Rgba16f => Some(10), // R16G16B16A16_FLOAT
            PixelFormat::Rg16 => Some(34),    // R16G16_UNORM
            _ => None,
        }
    }
}

#[derive(Debug, Clone)]
pub struct Mip {
    pub width: u32,
    pub height: u32,
    pub data: Vec<u8>,
}

pub struct Ftex {
    pub format: PixelFormat,
    pub version: u32,
    pub width: u32,
    pub height: u32,
    pub depth: u32,
    pub texture_type: u32,
    pub nrt: u8,
    pub flags: u16,
    /// Mip 0 is the full-size image.
    pub mips: Vec<Mip>,
}

fn le_u32(b: &[u8], at: usize) -> u32 {
    u32::from_le_bytes([b[at], b[at + 1], b[at + 2], b[at + 3]])
}
fn le_i16(b: &[u8], at: usize) -> i16 {
    i16::from_le_bytes([b[at], b[at + 1]])
}
fn le_u16(b: &[u8], at: usize) -> u16 {
    u16::from_le_bytes([b[at], b[at + 1]])
}

fn inflate(raw: &[u8]) -> Result<Vec<u8>> {
    let mut out = Vec::new();
    ZlibDecoder::new(raw)
        .read_to_end(&mut out)
        .context("inflating ftex chunk")?;
    Ok(out)
}

fn deflate(raw: &[u8]) -> Result<Vec<u8>> {
    let mut e = ZlibEncoder::new(Vec::new(), Compression::default());
    e.write_all(raw)?;
    Ok(e.finish()?)
}

impl Ftex {
    pub fn read(path: &Path) -> Result<Ftex> {
        let buf = fs::read(path).with_context(|| format!("reading {}", path.display()))?;
        Self::parse(&buf)
    }

    /// Parse an ftex from bytes. Reading one out of a CPK entry or another
    /// container hands over a buffer, not a path, and the two must decode
    /// identically.
    pub fn parse(buf: &[u8]) -> Result<Ftex> {
        if buf.len() < HEADER || buf[..4] != MAGIC {
            bail!("not an ftex");
        }
        let version = le_u32(&buf, 4);
        let format = PixelFormat::from_code(le_u16(&buf, 8))?;
        let width = le_i16(&buf, 10) as u32;
        let height = le_i16(&buf, 12) as u32;
        let depth = le_i16(&buf, 14) as u32;
        let count = buf[16] as usize;
        let nrt = buf[17];
        let flags = le_u16(&buf, 18);
        let texture_type = le_u32(&buf, 28);
        if HEADER + count * MIP_INFO > buf.len() {
            bail!("ftex mip table runs past the end of the file");
        }

        let mut mips = Vec::with_capacity(count);
        for i in 0..count {
            let at = HEADER + i * MIP_INFO;
            let offset = le_u32(&buf, at) as usize;
            let declared = le_u32(&buf, at + 4) as usize;
            let chunks = le_i16(&buf, at + 14);
            let ftexs = buf[at + 13];
            if ftexs != 0 {
                bail!(
                    "mip {i} lives in external ftexs #{ftexs}; \
                       PES packs textures embedded, so this is unexpected"
                );
            }
            let mut data = Vec::with_capacity(declared);
            if chunks == 0 {
                // A single unindexed block: the whole payload, uncompressed.
                let end = offset + declared;
                if end > buf.len() {
                    bail!("mip {i} payload runs past the end of the file");
                }
                data.extend_from_slice(&buf[offset..end]);
            } else {
                if chunks < 0 {
                    bail!("mip {i} has a negative chunk count");
                }
                let n = chunks as usize;
                if offset + n * 8 > buf.len() {
                    bail!("mip {i} chunk index runs past the end of the file");
                }
                for c in 0..n {
                    let ia = offset + c * 8;
                    let stored = le_u16(&buf, ia) as usize;
                    let raw_size = le_u16(&buf, ia + 2) as usize;
                    // The size fields are 16-bit, so a full 64 KiB chunk reads
                    // as zero. PES writes normal maps that way: 16 chunks of
                    // exactly 65536 for a 1024x1024 BC5 mip.
                    let stored = if stored == 0 { 65536 } else { stored };
                    let raw_size = if raw_size == 0 { 65536 } else { raw_size };
                    let rel = le_u32(&buf, ia + 4);
                    let rel = if rel > 0x8000_0000 {
                        rel - 0x8000_0000
                    } else {
                        rel
                    };
                    let pos = offset + rel as usize;
                    // Checked, because a bad size field must read as an error
                    // rather than as wrapping arithmetic that slips past.
                    let end = match pos.checked_add(stored) {
                        Some(end) if end <= buf.len() => end,
                        _ => bail!("mip {i} chunk {c} runs past the end of the file"),
                    };
                    let payload = &buf[pos..end];
                    if stored != raw_size {
                        data.extend_from_slice(&inflate(payload)?);
                    } else {
                        data.extend_from_slice(payload);
                    }
                }
            }
            if data.len() != declared {
                bail!(
                    "mip {i}: decoded {} bytes, header says {declared}",
                    data.len()
                );
            }
            mips.push(Mip {
                width: (width >> i).max(1),
                height: (height >> i).max(1),
                data,
            });
        }
        Ok(Ftex {
            format,
            version,
            width,
            height,
            depth,
            texture_type,
            nrt,
            flags,
            mips,
        })
    }

    pub fn to_dds(&self) -> Vec<u8> {
        let mut out = Vec::new();
        out.extend_from_slice(b"DDS ");
        out.extend_from_slice(&124u32.to_le_bytes());
        let mut flags = 0x1u32 | 0x2 | 0x4 | 0x1000; // caps, height, width, pixel format
        flags |= if self.format.block_bytes().is_some() {
            0x80000
        } else {
            0x8
        };
        if self.depth > 1 {
            flags |= 0x800000; // depth: LUT textures are 16x16x16 volumes
        }
        if self.mips.len() > 1 {
            flags |= 0x20000;
        }
        out.extend_from_slice(&flags.to_le_bytes());
        out.extend_from_slice(&self.height.to_le_bytes());
        out.extend_from_slice(&self.width.to_le_bytes());
        let pitch = match self.format.block_bytes() {
            Some(_) => self.format.level_size(self.width, self.height) as u32,
            None => self.width * self.format.texel_bytes(),
        };
        out.extend_from_slice(&pitch.to_le_bytes());
        out.extend_from_slice(&self.depth.max(1).to_le_bytes());
        out.extend_from_slice(&(self.mips.len() as u32).to_le_bytes());
        out.extend_from_slice(&[0u8; 44]); // reserved

        out.extend_from_slice(&32u32.to_le_bytes()); // pixel format size
                                                     // A DX10 header is the only way to name BC5/BC6H/BC7 and the 16-bit
                                                     // formats; the classic path keeps a FourCC or channel masks.
        let (pf_flags, fourcc, bits, r, g, b, a) = match self.format {
            PixelFormat::Bc1 => (0x4u32, *b"DXT1", 0u32, 0u32, 0u32, 0u32, 0u32),
            PixelFormat::Bc2 => (0x4, *b"DXT3", 0, 0, 0, 0, 0),
            PixelFormat::Bc3 => (0x4, *b"DXT5", 0, 0, 0, 0, 0),
            PixelFormat::Bgra8 => (
                0x1 | 0x40,
                [0; 4],
                32,
                0x00FF_0000,
                0x0000_FF00,
                0x0000_00FF,
                0xFF00_0000,
            ),
            PixelFormat::L8 => (0x20000, [0; 4], 8, 0xFF, 0, 0, 0),
            _ => (0x4, *b"DX10", 0, 0, 0, 0, 0),
        };
        let dxgi = if fourcc == *b"DX10" {
            self.format.dxgi()
        } else {
            None
        };
        debug_assert_eq!(
            dxgi.is_some(),
            fourcc == *b"DX10",
            "a format without a classic FourCC needs a DXGI number"
        );
        out.extend_from_slice(&pf_flags.to_le_bytes());
        out.extend_from_slice(&fourcc);
        out.extend_from_slice(&bits.to_le_bytes());
        for m in [r, g, b, a] {
            out.extend_from_slice(&m.to_le_bytes());
        }
        let caps = 0x1000u32
            | if self.mips.len() > 1 {
                0x8 | 0x400000
            } else {
                0
            };
        out.extend_from_slice(&caps.to_le_bytes());
        out.extend_from_slice(&(if self.depth > 1 { 0x200000u32 } else { 0 }).to_le_bytes());
        out.extend_from_slice(&[0u8; 12]); // caps3, caps4, reserved2
        if let Some(dxgi) = dxgi {
            out.extend_from_slice(&dxgi.to_le_bytes());
            // D3D10_RESOURCE_DIMENSION: 3 = texture 2D, 4 = texture 3D.
            let dim = if self.depth > 1 { 4u32 } else { 3 };
            out.extend_from_slice(&dim.to_le_bytes());
            out.extend_from_slice(&0u32.to_le_bytes()); // misc flags
            out.extend_from_slice(&(self.depth.max(1)).to_le_bytes()); // array size
            out.extend_from_slice(&0u32.to_le_bytes()); // misc flags 2
        }
        for m in &self.mips {
            out.extend_from_slice(&m.data);
        }
        out
    }

    pub fn from_dds(buf: &[u8]) -> Result<Ftex> {
        if buf.len() < 128 || &buf[..4] != b"DDS " {
            bail!("not a DDS file");
        }
        let height = le_u32(buf, 12);
        let width = le_u32(buf, 16);
        let depth = le_u32(buf, 24).max(1);
        let mip_count = le_u32(buf, 28);
        let pf_flags = le_u32(buf, 80);
        let fourcc = &buf[84..88];
        let bits = le_u32(buf, 88);
        let mut at = 128usize;
        let format = if fourcc == b"DX10" {
            if buf.len() < 148 {
                bail!("DDS has a DX10 header but ends before it");
            }
            let dxgi = le_u32(buf, 128);
            at = 148;
            match dxgi {
                71 | 72 => PixelFormat::Bc1,
                74 | 75 => PixelFormat::Bc2,
                77 | 78 => PixelFormat::Bc3,
                83 | 84 => PixelFormat::Bc5,
                95 | 96 => PixelFormat::Bc6h,
                98 | 99 => PixelFormat::Bc7,
                10 => PixelFormat::Rgba16f,
                34 | 36 => PixelFormat::Rg16,
                87 | 91 => PixelFormat::Bgra8,
                _ => bail!("unsupported DXGI format {dxgi} in DDS"),
            }
        } else if pf_flags & 0x4 != 0 {
            match fourcc {
                b"DXT1" => PixelFormat::Bc1,
                b"DXT3" => PixelFormat::Bc2,
                b"DXT5" => PixelFormat::Bc3,
                // The names tools actually write for BC5.
                b"ATI2" | b"BC5U" | b"BC5S" | b"A2XY" => PixelFormat::Bc5,
                b"ATI1" | b"BC4U" | b"BC4S" => PixelFormat::L8,
                _ => bail!(
                    "unsupported DDS fourCC {:?}",
                    String::from_utf8_lossy(fourcc)
                ),
            }
        } else if pf_flags & 0x20000 != 0 {
            PixelFormat::L8
        } else if pf_flags & 0x40 != 0 && bits == 32 {
            PixelFormat::Bgra8
        } else {
            bail!("unsupported DDS pixel format (flags {pf_flags:#x}, {bits} bits)");
        };
        if width == 0 || height == 0 {
            bail!("DDS has zero width or height");
        }

        let max_levels = 32 - width.max(height).max(depth).leading_zeros() as usize;
        let levels = if mip_count == 0 {
            1
        } else {
            usize::try_from(mip_count).context("DDS mip count exceeds address space")?
        };
        if levels > max_levels {
            bail!("DDS mip count {levels} exceeds the dimensions' maximum of {max_levels}");
        }
        let mut mips = Vec::with_capacity(levels);
        for i in 0..levels {
            let w = (width >> i).max(1);
            let h = (height >> i).max(1);
            let d = (depth >> i).max(1);
            let n = checked_level_size(format, w, h)?
                .checked_mul(d as usize)
                .context("DDS mip size overflow")?;
            let end = at.checked_add(n).context("DDS payload offset overflow")?;
            if end > buf.len() {
                bail!(
                    "DDS mip {i} needs {n} bytes at {at}, file has {}",
                    buf.len()
                );
            }
            mips.push(Mip {
                width: w,
                height: h,
                data: buf[at..end].to_vec(),
            });
            at = end;
        }

        fn checked_level_size(format: PixelFormat, width: u32, height: u32) -> Result<usize> {
            let w = usize::try_from(width).context("DDS width exceeds address space")?;
            let h = usize::try_from(height).context("DDS height exceeds address space")?;
            let pixels = w.checked_mul(h).context("DDS dimensions overflow")?;
            let bytes = match format {
                PixelFormat::Bgra8 | PixelFormat::Rg16 => pixels.checked_mul(4),
                PixelFormat::L8 => Some(pixels),
                PixelFormat::Rgba16f => pixels.checked_mul(8),
                PixelFormat::Bc1 => w
                    .div_ceil(4)
                    .checked_mul(h.div_ceil(4))
                    .and_then(|n| n.checked_mul(8)),
                PixelFormat::Bc2
                | PixelFormat::Bc3
                | PixelFormat::Bc5
                | PixelFormat::Bc6h
                | PixelFormat::Bc7 => w
                    .div_ceil(4)
                    .checked_mul(h.div_ceil(4))
                    .and_then(|n| n.checked_mul(16)),
            };
            bytes.context("DDS mip size overflow")
        }
        Ok(Ftex {
            format,
            version: VERSION_DEFAULT,
            width,
            height,
            depth,
            texture_type: 3, // diffuse; callers retag normal/material maps
            nrt: 2,
            flags: 17,
            mips,
        })
    }

    /// Serialise. Blocks are written smallest mip first, matching PES.
    pub fn to_ftex(&self) -> Result<Vec<u8>> {
        if self.mips.is_empty() {
            bail!("no mip data to write");
        }
        // (file offset, serialised block, chunk index entries)
        type Block = (usize, Vec<u8>, Vec<(u16, u16, u32)>);
        let mut blocks: Vec<Block> = Vec::new();
        // Running position of each block, filled in as they are appended.
        let mut cursor = HEADER + self.mips.len() * MIP_INFO;
        for mip in self.mips.iter().rev() {
            let mut index = Vec::new();
            let mut payload = Vec::new();
            let pieces: Vec<&[u8]> = mip.data.chunks(CHUNK).collect();
            let index_bytes = pieces.len() * 8;
            for piece in &pieces {
                let packed = deflate(piece)?;
                let (stored, bytes): (usize, &[u8]) = if packed.len() < piece.len() {
                    (packed.len(), &packed)
                } else {
                    (piece.len(), piece)
                };
                if stored == 0 || stored > 0xFFFF {
                    bail!(
                        "chunk of {stored} bytes does not fit the 16-bit size field, \
                          where 0 already means a full 64 KiB"
                    );
                }
                index.push((
                    stored as u16,
                    piece.len() as u16,
                    (index_bytes + payload.len()) as u32,
                ));
                payload.extend_from_slice(bytes);
            }
            let mut block = Vec::with_capacity(index_bytes + payload.len());
            for (stored, raw, off) in &index {
                block.extend_from_slice(&stored.to_le_bytes());
                block.extend_from_slice(&raw.to_le_bytes());
                block.extend_from_slice(&off.to_le_bytes());
            }
            block.extend_from_slice(&payload);
            blocks.push((cursor, block, index));
            cursor += blocks.last().unwrap().1.len();
        }

        let mut out = vec![0u8; cursor];
        out[..4].copy_from_slice(&MAGIC);
        out[4..8].copy_from_slice(&self.version.to_le_bytes());
        out[8..10].copy_from_slice(&self.format.code().to_le_bytes());
        out[10..12].copy_from_slice(&(self.width as i16).to_le_bytes());
        out[12..14].copy_from_slice(&(self.height as i16).to_le_bytes());
        out[14..16].copy_from_slice(&(self.depth.max(1) as i16).to_le_bytes());
        out[16] = self.mips.len() as u8;
        out[17] = self.nrt;
        out[18..20].copy_from_slice(&self.flags.to_le_bytes());
        out[28..32].copy_from_slice(&self.texture_type.to_le_bytes());

        // blocks[0] is the smallest mip, i.e. the highest index.
        for (i, mip) in self.mips.iter().enumerate() {
            let (offset, block, _) = &blocks[self.mips.len() - 1 - i];
            let at = HEADER + i * MIP_INFO;
            out[at..at + 4].copy_from_slice(&(*offset as u32).to_le_bytes());
            out[at + 4..at + 8].copy_from_slice(&(mip.data.len() as u32).to_le_bytes());
            out[at + 8..at + 12].copy_from_slice(&(block.len() as u32).to_le_bytes());
            out[at + 12] = i as u8;
            out[at + 13] = 0; // embedded
            out[at + 14..at + 16]
                .copy_from_slice(&(mip.data.len().div_ceil(CHUNK) as i16).to_le_bytes());
            out[*offset..*offset + block.len()].copy_from_slice(block);
        }
        Ok(out)
    }

    pub fn write_ftex(&self, path: &Path) -> Result<()> {
        let bytes = self.to_ftex()?;
        if let Some(p) = path.parent() {
            fs::create_dir_all(p)?;
        }
        fs::write(path, bytes).with_context(|| format!("writing {}", path.display()))?;
        Ok(())
    }
}

/// Decode a texture to DDS bytes, whichever of the two formats it is.
pub fn to_dds_file(src: &Path, dest: &Path) -> Result<Ftex> {
    let ftex = Ftex::read(src)?;
    if let Some(p) = dest.parent() {
        fs::create_dir_all(p)?;
    }
    fs::write(dest, ftex.to_dds())?;
    Ok(ftex)
}

fn rgb565(c: u16) -> [u8; 3] {
    [
        ((c >> 11) as u32 * 255 / 31) as u8,
        (((c >> 5) & 63) as u32 * 255 / 63) as u8,
        ((c & 31) as u32 * 255 / 31) as u8,
    ]
}

/// One 4x4 BC1 colour block into 16 RGBA pixels. `opaque` forces the
/// four-colour mode BC2 and BC3 always use for their colour half.
fn bc1_block(block: &[u8], out: &mut [u8], stride: usize, opaque: bool) {
    let c0 = u16::from_le_bytes([block[0], block[1]]);
    let c1 = u16::from_le_bytes([block[2], block[3]]);
    let (a, b) = (rgb565(c0), rgb565(c1));
    let mut palette = [[0u8; 4]; 4];
    palette[0] = [a[0], a[1], a[2], 255];
    palette[1] = [b[0], b[1], b[2], 255];
    if c0 > c1 || opaque {
        for k in 0..3 {
            palette[2][k] = ((2 * a[k] as u16 + b[k] as u16) / 3) as u8;
            palette[3][k] = ((a[k] as u16 + 2 * b[k] as u16) / 3) as u8;
        }
        palette[2][3] = 255;
        palette[3][3] = 255;
    } else {
        for k in 0..3 {
            palette[2][k] = ((a[k] as u16 + b[k] as u16) / 2) as u8;
        }
        palette[2][3] = 255;
        palette[3] = [0, 0, 0, 0];
    }
    let bits = u32::from_le_bytes([block[4], block[5], block[6], block[7]]);
    for i in 0..16 {
        let idx = ((bits >> (2 * i)) & 3) as usize;
        let (x, y) = (i % 4, i / 4);
        let at = y * stride + x * 4;
        out[at..at + 4].copy_from_slice(&palette[idx]);
    }
}

fn dxt5_alpha(block: &[u8]) -> [u8; 8] {
    let (a0, a1) = (block[0] as u16, block[1] as u16);
    let mut t = [0u8; 8];
    t[0] = a0 as u8;
    t[1] = a1 as u8;
    if a0 > a1 {
        for i in 1..7 {
            t[i + 1] = (((7 - i as u16) * a0 + i as u16 * a1) / 7) as u8;
        }
    } else {
        for i in 1..5 {
            t[i + 1] = (((5 - i as u16) * a0 + i as u16 * a1) / 5) as u8;
        }
        t[6] = 0;
        t[7] = 255;
    }
    t
}

/// BC2's alpha half: four explicit bits per texel, two texels per byte, one
/// byte-pair per row.
fn bc2_alpha(block: &[u8], out: &mut [u8]) {
    for y in 0..4 {
        let bits = u16::from_le_bytes([block[y * 2], block[y * 2 + 1]]);
        for x in 0..4 {
            let nib = ((bits >> (4 * x)) & 0xF) as u8;
            out[(y * 4 + x) * 4 + 3] = nib * 17;
        }
    }
}

/// BC3's alpha half: two endpoints plus 48 bits of 3-bit indices.
fn bc3_alpha(block: &[u8], out: &mut [u8]) {
    let table = dxt5_alpha(block);
    let mut bits = 0u64;
    for k in 0..6 {
        bits |= (block[2 + k] as u64) << (8 * k);
    }
    for i in 0..16 {
        out[i * 4 + 3] = table[((bits >> (3 * i)) & 7) as usize];
    }
}

/// One BC4 single-channel sub-block: the same endpoint table BC3 uses for its
/// alpha half, at a byte offset.
fn bc4_sub_block(block: &[u8], at: usize) -> [u8; 16] {
    let table = dxt5_alpha(&block[at..at + 8]);
    let mut bits = 0u64;
    for k in 0..6 {
        bits |= (block[at + 2 + k] as u64) << (8 * k);
    }
    let mut out = [0u8; 16];
    for i in 0..16 {
        out[i] = table[((bits >> (3 * i)) & 7) as usize];
    }
    out
}

/// BC5 stores X and Y and nothing else, so the preview has to rebuild Z.
/// FL27 writes normals unsigned with 128 as neutral, which is what the
/// endpoint bytes cluster around in every real file measured here.
fn bc5_block(block: &[u8], out: &mut [u8]) {
    let (r, g) = (bc4_sub_block(block, 0), bc4_sub_block(block, 8));
    for i in 0..16 {
        let x = r[i] as f32 / 255.0 * 2.0 - 1.0;
        let y = g[i] as f32 / 255.0 * 2.0 - 1.0;
        let z = (1.0 - x * x - y * y).max(0.0).sqrt();
        out[i * 4] = r[i];
        out[i * 4 + 1] = g[i];
        out[i * 4 + 2] = (z * 255.0 + 0.5) as u8;
        out[i * 4 + 3] = 255;
    }
}

/// IEEE-754 half to an 8-bit value, clamped to the [0,1] a preview needs.
fn half_to_u8(h: u16) -> u8 {
    let exp = (h >> 10) & 0x1F;
    let mant = h & 0x3FF;
    let f = if exp == 0 {
        mant as f32 * 2f32.powi(-24)
    } else if exp == 0x1F {
        if mant == 0 {
            f32::INFINITY
        } else {
            f32::NAN
        }
    } else {
        (1.0 + mant as f32 / 1024.0) * 2f32.powi(exp as i32 - 15)
    };
    let v = if h & 0x8000 != 0 { -f } else { f };
    (v.clamp(0.0, 1.0) * 255.0 + 0.5) as u8
}

// ---------------------------------------------------------------- encoders
//
// Reading a block format and writing one are different jobs, and until this
// section the app could only read them. These are nearest-fit encoders: they
// take the block's own extremes as the endpoints and pick the closest palette
// entry per texel. That is not the best possible quality — a search encoder
// would try several endpoint pairs — but it is deterministic, and the error it
// leaves is measured in the tests rather than assumed.

fn to565(r: u8, g: u8, b: u8) -> u16 {
    ((r as u16 >> 3) << 11) | ((g as u16 >> 2) << 5) | (b as u16 >> 3)
}

/// One 4x4 block of one channel into an 8-byte BC4 sub-block: two endpoints
/// then 48 bits of 3-bit indices, the same table the decoder builds.
// The index loop walks texel order because that is the order the bits are
// packed in, not to visit the array.
#[allow(clippy::needless_range_loop)]
fn bc4_encode(values: &[u8; 16], out: &mut [u8]) {
    let min = *values.iter().min().unwrap() as i32;
    let max = *values.iter().max().unwrap() as i32;
    // a0 > a1 selects the eight-value table, which is the one worth having;
    // a flat block lands on a0 == a1 and every texel picks index 0.
    let (a0, a1) = (max as u8, min as u8);
    let head = [a0, a1, 0, 0, 0, 0, 0, 0];
    let table = dxt5_alpha(&head);
    let mut bits = 0u64;
    for i in 0..16 {
        let want = values[i] as i32;
        let mut best = 0usize;
        let mut best_d = i32::MAX;
        for (k, &t) in table.iter().enumerate() {
            let d = (t as i32 - want).abs();
            if d < best_d {
                best_d = d;
                best = k;
            }
        }
        bits |= (best as u64) << (3 * i);
    }
    out[0] = a0;
    out[1] = a1;
    for k in 0..6 {
        out[2 + k] = ((bits >> (8 * k)) & 0xFF) as u8;
    }
}

/// One 4x4 block of RGBA into an 8-byte BC1 colour block, always in the
/// four-colour mode BC2 and BC3 use.
// The index loop walks texel order because that is the order the bits are
// packed in, not to visit the array.
#[allow(clippy::needless_range_loop)]
fn bc1_encode(px: &[[u8; 4]; 16], out: &mut [u8]) {
    let (mut mn, mut mx) = ([255u8; 3], [0u8; 3]);
    for p in px {
        for k in 0..3 {
            mn[k] = mn[k].min(p[k]);
            mx[k] = mx[k].max(p[k]);
        }
    }
    let (mut c0, mut c1) = (to565(mx[0], mx[1], mx[2]), to565(mn[0], mn[1], mn[2]));
    if c0 <= c1 {
        std::mem::swap(&mut c0, &mut c1);
    }
    out[0..2].copy_from_slice(&c0.to_le_bytes());
    out[2..4].copy_from_slice(&c1.to_le_bytes());
    let (a, b) = (rgb565(c0), rgb565(c1));
    let mut palette = [a, b, [0u8; 3], [0u8; 3]];
    for k in 0..3 {
        palette[2][k] = ((2 * a[k] as u16 + b[k] as u16) / 3) as u8;
        palette[3][k] = ((a[k] as u16 + 2 * b[k] as u16) / 3) as u8;
    }
    let mut bits = 0u32;
    for i in 0..16 {
        let want = px[i];
        let mut best = 0usize;
        let mut best_d = u64::MAX;
        for (k, p) in palette.iter().enumerate() {
            let d = (p[0] as i32 - want[0] as i32).pow(2) as u64
                + (p[1] as i32 - want[1] as i32).pow(2) as u64
                + (p[2] as i32 - want[2] as i32).pow(2) as u64;
            if d < best_d {
                best_d = d;
                best = k;
            }
        }
        bits |= (best as u32) << (2 * i);
    }
    out[4..8].copy_from_slice(&bits.to_le_bytes());
}

/// Encode a whole RGBA8 image into block bytes for one format. Formats this
/// build cannot write are refused with the reason, rather than quietly
/// substituted so the caller thinks they got what they asked for.
pub fn encode_blocks(format: PixelFormat, rgba: &[u8], w: u32, h: u32) -> Result<Vec<u8>> {
    let (w, h) = (w as usize, h as usize);
    if rgba.len() < w * h * 4 {
        bail!(
            "encode needs {} bytes of RGBA8, got {}",
            w * h * 4,
            rgba.len()
        );
    }
    let gather = |bx: usize, by: usize| -> [[u8; 4]; 16] {
        let mut tile = [[0u8; 4]; 16];
        for y in 0..4 {
            for x in 0..4 {
                let (px, py) = ((bx * 4 + x).min(w - 1), (by * 4 + y).min(h - 1));
                let s = (py * w + px) * 4;
                tile[y * 4 + x].copy_from_slice(&rgba[s..s + 4]);
            }
        }
        tile
    };
    let (bw, bh) = (w.div_ceil(4), h.div_ceil(4));
    match format {
        PixelFormat::Bgra8 => Ok(rgba[..w * h * 4].to_vec()),
        PixelFormat::L8 => {
            let mut out = Vec::with_capacity(w * h);
            for i in 0..w * h {
                out.push(rgba[i * 4]);
            }
            Ok(out)
        }
        PixelFormat::Bc1 => {
            let mut out = vec![0u8; bw * bh * 8];
            for by in 0..bh {
                for bx in 0..bw {
                    let tile = gather(bx, by);
                    bc1_encode(&tile, &mut out[(by * bw + bx) * 8..(by * bw + bx) * 8 + 8]);
                }
            }
            Ok(out)
        }
        PixelFormat::Bc3 => {
            let mut out = vec![0u8; bw * bh * 16];
            for by in 0..bh {
                for bx in 0..bw {
                    let tile = gather(bx, by);
                    let mut block = [0u8; 16];
                    // BC2 and BC3 put the alpha half FIRST and the colour half
                    // second, which is the opposite of how it reads in the
                    // decoder's favour; getting this backwards makes every
                    // texture render as a white silhouette.
                    let mut vals = [0u8; 16];
                    for i in 0..16 {
                        vals[i] = tile[i][3];
                    }
                    bc4_encode(&vals, &mut block[..8]);
                    bc1_encode(&tile, &mut block[8..16]);
                    out[(by * bw + bx) * 16..(by * bw + bx) * 16 + 16].copy_from_slice(&block);
                }
            }
            Ok(out)
        }
        PixelFormat::Bc5 => {
            let mut out = vec![0u8; bw * bh * 16];
            for by in 0..bh {
                for bx in 0..bw {
                    let tile = gather(bx, by);
                    let mut block = [0u8; 16];
                    let mut r = [0u8; 16];
                    let mut g = [0u8; 16];
                    for i in 0..16 {
                        r[i] = tile[i][0];
                        g[i] = tile[i][1];
                    }
                    bc4_encode(&r, &mut block[..8]);
                    bc4_encode(&g, &mut block[8..]);
                    out[(by * bw + bx) * 16..(by * bw + bx) * 16 + 16].copy_from_slice(&block);
                }
            }
            Ok(out)
        }
        other => bail!(
            "{} has no encoder in this build; BC1, BC3 and BC5 are written",
            other.name()
        ),
    }
}

impl Ftex {
    /// Decode one mip to straight RGBA8, top row first. Volume textures return
    /// the first slice, which is what a preview wants.
    pub fn to_rgba(&self, level: usize) -> Result<(u32, u32, Vec<u8>)> {
        let mip = self.mips.get(level).context("no such mip level")?;
        let (w, h) = (mip.width as usize, mip.height as usize);
        let mut out = vec![0u8; w * h * 4];
        match self.format {
            PixelFormat::Bgra8 => {
                for i in 0..w * h {
                    let s = i * 4;
                    out[s] = mip.data[s + 2];
                    out[s + 1] = mip.data[s + 1];
                    out[s + 2] = mip.data[s];
                    out[s + 3] = mip.data[s + 3];
                }
            }
            PixelFormat::L8 => {
                for i in 0..w * h {
                    let v = mip.data[i];
                    out[i * 4..i * 4 + 4].copy_from_slice(&[v, v, v, 255]);
                }
            }
            PixelFormat::Bc1
            | PixelFormat::Bc2
            | PixelFormat::Bc3
            | PixelFormat::Bc5
            | PixelFormat::Bc7 => {
                let bs = if self.format == PixelFormat::Bc1 {
                    8
                } else {
                    16
                };
                let bw = w.div_ceil(4);
                let bh = h.div_ceil(4);
                for by in 0..bh {
                    for bx in 0..bw {
                        let at = (by * bw + bx) * bs;
                        if at + bs > mip.data.len() {
                            bail!("mip {level} is short of block data");
                        }
                        let block = &mip.data[at..at + bs];
                        let mut tile = [0u8; 16 * 4];
                        match self.format {
                            PixelFormat::Bc1 => bc1_block(block, &mut tile, 4 * 4, false),
                            PixelFormat::Bc2 => {
                                bc1_block(&block[8..], &mut tile, 4 * 4, true);
                                bc2_alpha(block, &mut tile);
                            }
                            PixelFormat::Bc3 => {
                                bc1_block(&block[8..], &mut tile, 4 * 4, true);
                                bc3_alpha(block, &mut tile);
                            }
                            PixelFormat::Bc5 => bc5_block(block, &mut tile),
                            _ => {
                                if !crate::bc7::decode_block(block, &mut tile) {
                                    bail!(
                                        "mip {level} block {} uses the reserved \
                                           BC7 mode 8",
                                        by * bw + bx
                                    );
                                }
                            }
                        }
                        // Clip the tile against the real image edge.
                        for y in 0..4 {
                            let py = by * 4 + y;
                            if py >= h {
                                break;
                            }
                            let n = (w - bx * 4).min(4);
                            let src = y * 16;
                            let dst = py * w * 4 + bx * 16;
                            out[dst..dst + n * 4].copy_from_slice(&tile[src..src + n * 4]);
                        }
                    }
                }
            }
            PixelFormat::Rgba16f => {
                for i in 0..w * h {
                    let at = i * 8;
                    if at + 8 > mip.data.len() {
                        bail!("mip {level} is short of half-float data");
                    }
                    for ch in 0..4 {
                        out[i * 4 + ch] = half_to_u8(le_u16(&mip.data, at + ch * 2));
                    }
                }
            }
            PixelFormat::Rg16 => {
                // Two 16-bit channels; the top byte is enough to see the shape.
                for i in 0..w * h {
                    let at = i * 4;
                    if at + 4 > mip.data.len() {
                        bail!("mip {level} is short of RG16 data");
                    }
                    out[i * 4] = mip.data[at + 1];
                    out[i * 4 + 1] = mip.data[at + 3];
                    out[i * 4 + 2] = 0;
                    out[i * 4 + 3] = 255;
                }
            }
            PixelFormat::Bc6h => bail!(
                "{}x{} is BC6H: the blocks are sized and will convert, but this \
                 build has no HDR block decoder for the preview",
                w,
                h
            ),
        }
        Ok((mip.width, mip.height, out))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn level_sizes_match_block_rounding() {
        assert_eq!(PixelFormat::Bc3.level_size(1024, 1024), 1_048_576);
        assert_eq!(PixelFormat::Bc3.level_size(2, 2), 16);
        assert_eq!(PixelFormat::Bc1.level_size(4, 4), 8);
        assert_eq!(PixelFormat::Bc1.level_size(5, 5), 32);
        assert_eq!(PixelFormat::Bgra8.level_size(16, 16), 1024);
        assert_eq!(PixelFormat::L8.level_size(16, 16), 256);
    }

    #[test]
    fn dds_round_trip_preserves_pixels() {
        let ftex = Ftex {
            format: PixelFormat::Bc3,
            version: VERSION_DEFAULT,
            width: 64,
            height: 32,
            depth: 1,
            texture_type: 3,
            nrt: 2,
            flags: 17,
            mips: (0..3)
                .map(|i| {
                    let w = 64 >> i;
                    let h = 32 >> i;
                    let n = PixelFormat::Bc3.level_size(w, h);
                    Mip {
                        width: w,
                        height: h,
                        data: (0..n).map(|k| (k % 251) as u8).collect(),
                    }
                })
                .collect(),
        };
        let dds = ftex.to_dds();
        let back = Ftex::from_dds(&dds).unwrap();
        assert_eq!(back.format, ftex.format);
        assert_eq!(back.width, 64);
        assert_eq!(back.height, 32);
        assert_eq!(back.mips.len(), 3);
        for (a, b) in ftex.mips.iter().zip(&back.mips) {
            assert_eq!(a.data, b.data);
        }
    }

    #[test]
    fn ftex_round_trip_preserves_pixels() {
        let ftex = Ftex {
            format: PixelFormat::Bgra8,
            version: VERSION_DEFAULT,
            width: 32,
            height: 32,
            depth: 1,
            texture_type: 1,
            nrt: 2,
            flags: 17,
            mips: vec![Mip {
                width: 32,
                height: 32,
                data: (0..32 * 32 * 4).map(|k| (k % 256) as u8).collect(),
            }],
        };
        let bytes = ftex.to_ftex().unwrap();
        let dir = std::env::temp_dir().join(format!("fl27mm-ftex-{}", std::process::id()));
        fs::create_dir_all(&dir).unwrap();
        let p = dir.join("t.ftex");
        fs::write(&p, &bytes).unwrap();
        let back = Ftex::read(&p).unwrap();
        assert_eq!(back.format, ftex.format);
        assert_eq!(back.texture_type, 1);
        assert_eq!(back.mips.len(), 1);
        assert_eq!(back.mips[0].data, ftex.mips[0].data);
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn volume_depth_survives_the_round_trip() {
        // PES colour LUTs are 16x16x16 volumes: ignoring depth keeps one slice
        // and silently discards the other fifteen.
        let n = 16 * 16 * 4 * 16;
        let ftex = Ftex {
            format: PixelFormat::Bgra8,
            version: VERSION_DEFAULT,
            width: 16,
            height: 16,
            depth: 16,
            texture_type: 1,
            nrt: 2,
            flags: 17,
            mips: vec![Mip {
                width: 16,
                height: 16,
                data: (0..n).map(|k| (k % 256) as u8).collect(),
            }],
        };
        let dds = ftex.to_dds();
        assert_eq!(dds.len(), 128 + n);
        assert_eq!(le_u32(&dds, 24), 16);
        assert_ne!(le_u32(&dds, 8) & 0x800000, 0, "depth flag must be set");
        assert_ne!(le_u32(&dds, 112) & 0x200000, 0, "volume caps2 must be set");
        let back = Ftex::from_dds(&dds).unwrap();
        assert_eq!(back.depth, 16);
        assert_eq!(back.mips[0].data, ftex.mips[0].data);
    }

    #[test]
    fn dxt1_solid_block_decodes_to_its_colour() {
        // Both endpoints pure red, every index 0 -> a solid red 4x4.
        let mut data = vec![0u8; 8];
        data[0..2].copy_from_slice(&0xF800u16.to_le_bytes());
        data[2..4].copy_from_slice(&0xF800u16.to_le_bytes());
        let ftex = Ftex {
            format: PixelFormat::Bc1,
            version: VERSION_DEFAULT,
            width: 4,
            height: 4,
            depth: 1,
            texture_type: 3,
            nrt: 2,
            flags: 17,
            mips: vec![Mip {
                width: 4,
                height: 4,
                data,
            }],
        };
        let (w, h, rgba) = ftex.to_rgba(0).unwrap();
        assert_eq!((w, h), (4, 4));
        assert_eq!(rgba.len(), 64);
        for px in rgba.chunks(4) {
            assert_eq!(px, [255, 0, 0, 255]);
        }
    }

    #[test]
    fn dxt_size_not_multiple_of_four_is_clipped() {
        let ftex = Ftex {
            format: PixelFormat::Bc3,
            version: VERSION_DEFAULT,
            width: 6,
            height: 5,
            depth: 1,
            texture_type: 3,
            nrt: 2,
            flags: 17,
            mips: vec![Mip {
                width: 6,
                height: 5,
                data: vec![0u8; 2 * 2 * 16],
            }],
        };
        let (w, h, rgba) = ftex.to_rgba(0).unwrap();
        assert_eq!((w, h), (6, 5));
        assert_eq!(rgba.len(), 6 * 5 * 4);
    }

    #[test]
    fn hostile_dds_dimensions_and_mip_count_are_rejected() {
        let mut dds = vec![0u8; 128];
        dds[..4].copy_from_slice(b"DDS ");
        dds[12..16].copy_from_slice(&u32::MAX.to_le_bytes());
        dds[16..20].copy_from_slice(&u32::MAX.to_le_bytes());
        dds[24..28].copy_from_slice(&1u32.to_le_bytes());
        dds[28..32].copy_from_slice(&u32::MAX.to_le_bytes());
        dds[80..84].copy_from_slice(&4u32.to_le_bytes());
        dds[84..88].copy_from_slice(b"DXT1");
        assert!(Ftex::from_dds(&dds).is_err());
    }

    #[test]
    fn real_texture_decodes_and_re_encodes() {
        let p = crate::install::game_root()
            .join("SiderAddons/livecpk/root/3D Turf/Asset/model/bg/common/turf3d/sourceimages/#windx11/0grassfin_bsm_alp.ftex");
        if !p.exists() {
            return;
        }
        let ftex = Ftex::read(&p).unwrap();
        assert_eq!(ftex.width, 128);
        assert_eq!(ftex.height, 128);
        assert_eq!(ftex.format, PixelFormat::Bc3);
        assert_eq!(ftex.mips[0].data.len(), 16384);

        let dds = ftex.to_dds();
        let back = Ftex::from_dds(&dds).unwrap();
        assert_eq!(back.mips[0].data, ftex.mips[0].data);

        let dir = std::env::temp_dir().join(format!("fl27mm-ftex-real-{}", std::process::id()));
        fs::create_dir_all(&dir).unwrap();
        let out = dir.join("re.ftex");
        back.write_ftex(&out).unwrap();
        let again = Ftex::read(&out).unwrap();
        assert_eq!(again.mips[0].data, ftex.mips[0].data);
        let _ = fs::remove_dir_all(&dir);
    }

    /// Mean absolute difference between horizontally adjacent pixels. This is
    /// what separates a correct block decode from noise.
    fn roughness(w: u32, h: u32, rgba: &[u8]) -> f64 {
        let (w, h) = (w as usize, h as usize);
        let (mut acc, mut n) = (0u64, 0u64);
        for y in 0..h {
            for x in 1..w {
                for c in 0..3 {
                    let a = rgba[(y * w + x) * 4 + c] as i32;
                    let b = rgba[(y * w + x - 1) * 4 + c] as i32;
                    acc += (a - b).unsigned_abs() as u64;
                    n += 1;
                }
            }
        }
        acc as f64 / n.max(1) as f64
    }

    #[test]
    fn bc5_real_normal_map_decodes_smooth_and_centred() {
        // Code 9 was the format every normal map failed on. The identification
        // rests on smoothness: as BC5 a real face normal map measures under 2
        // here, and 40+ decoded as any other 16-byte codec.
        let p = crate::install::game_root()
            .join("SiderAddons/livecpk/root/Asset/model/character/face/real/100006/sourceimages/#windx11/face_nrm.ftex");
        if !p.exists() {
            return;
        }
        let ftex = Ftex::read(&p).unwrap();
        assert_eq!(ftex.format, PixelFormat::Bc5);
        let (w, h, rgba) = ftex.to_rgba(0).unwrap();
        let (mut sr, mut sg, mut zb) = (0u64, 0u64, 0u64);
        for px in rgba.chunks(4) {
            sr += px[0] as u64;
            sg += px[1] as u64;
            zb += px[2] as u64;
        }
        let n = u64::from(w * h);
        // 128 is neutral, so a face is mostly flat surface.
        assert!(
            (110..=145).contains(&(sr / n)),
            "R mean {} is not centred",
            sr / n
        );
        assert!(
            (110..=145).contains(&(sg / n)),
            "G mean {} is not centred",
            sg / n
        );
        assert!(
            zb / n > 190,
            "reconstructed Z mean {} means XY is noise",
            zb / n
        );
        let r = roughness(w, h, &rgba);
        assert!(r < 6.0, "BC5 decode is not smooth: {r}");
    }

    #[test]
    fn bc7_real_texture_decodes_and_its_mips_agree() {
        // Code 11 is BC7 — 99.8% of its blocks carry a legal mode prefix. This
        // checks the decode without a reference image by comparing two mip
        // levels of the same surface: a correct decode makes mip 2 the blurred
        // mip 0, and noise does not correlate with itself downsampled.
        let p = crate::install::game_root()
            .join("SiderAddons/livecpk/root/Asset/model/character/face/real/117680/sourceimages/#windx11/hair_parts_bsm.ftex");
        if !p.exists() {
            return;
        }
        let ftex = Ftex::read(&p).unwrap();
        assert_eq!(ftex.format, PixelFormat::Bc7);
        assert!(ftex.mips.len() > 3, "this file should carry a mip chain");
        let (w, h, big) = ftex.to_rgba(0).unwrap();
        let (sw, sh, small) = ftex.to_rgba(2).unwrap();
        assert_eq!((sw, sh), (w / 4, h / 4));
        let r = roughness(w, h, &big);
        assert!(r < 12.0, "BC7 decode is not smooth: {r}");
        let (mut acc, mut n) = (0u64, 0u64);
        for y in 0..sh {
            for x in 0..sw {
                for c in 0..3 {
                    let mut sum = 0u32;
                    for dy in 0..4 {
                        for dx in 0..4 {
                            let at = ((y * 4 + dy) * w + x * 4 + dx) as usize * 4 + c;
                            sum += big[at] as u32;
                        }
                    }
                    let a = (sum / 16) as i32;
                    let b = small[((y * sw + x) as usize) * 4 + c] as i32;
                    acc += (a - b).unsigned_abs() as u64;
                    n += 1;
                }
            }
        }
        let mad = acc as f64 / n as f64;
        assert!(
            mad < 12.0,
            "mip 0 downsampled differs from mip 2 by {mad:.1}, so the decode is noise"
        );
    }

    #[test]
    fn dx10_header_names_the_formats_fourcc_cannot() {
        for (format, dxgi) in [
            (PixelFormat::Bc5, 83u32),
            (PixelFormat::Bc6h, 95),
            (PixelFormat::Bc7, 98),
            (PixelFormat::Rgba16f, 10),
            (PixelFormat::Rg16, 34),
        ] {
            let ftex = Ftex {
                format,
                version: VERSION_DEFAULT,
                width: 8,
                height: 8,
                depth: 1,
                texture_type: 9,
                nrt: 2,
                flags: 17,
                mips: vec![Mip {
                    width: 8,
                    height: 8,
                    data: vec![0u8; format.level_size(8, 8)],
                }],
            };
            let dds = ftex.to_dds();
            assert_eq!(
                &dds[84..88],
                b"DX10",
                "{} needs a DX10 header",
                format.name()
            );
            assert_eq!(le_u32(&dds, 128), dxgi, "{} DXGI", format.name());
            assert_eq!(dds.len(), 148 + format.level_size(8, 8));
            let back = Ftex::from_dds(&dds).unwrap();
            assert_eq!(back.format, format);
            assert_eq!(back.mips[0].data, ftex.mips[0].data);
        }
    }

    #[test]
    fn every_format_in_a_real_pack_survives_ftex_dds_ftex() {
        // Reading and converting must work for every code even where this build
        // cannot draw a preview: the block bytes move untouched.
        let dir = crate::install::game_root()
            .join("SiderAddons/livecpk/root/Asset/model/character/face");
        if !dir.exists() {
            return;
        }
        let mut seen: std::collections::BTreeMap<u16, usize> = Default::default();
        let mut checked = 0usize;
        for p in crate::fsutil::files(&dir).iter().take(600) {
            if p.extension().and_then(|e| e.to_str()) != Some("ftex") {
                continue;
            }
            let ftex = match Ftex::read(&p) {
                Ok(f) => f,
                Err(_) => continue,
            };
            if ftex.depth > 1 {
                continue;
            }
            let dds = ftex.to_dds();
            let back = Ftex::from_dds(&dds)
                .with_context(|| format!("reading back {}", p.display()))
                .unwrap();
            assert_eq!(back.format, ftex.format, "format lost at {}", p.display());
            assert_eq!(
                back.mips.len(),
                ftex.mips.len(),
                "mips lost at {}",
                p.display()
            );
            for (a, b) in back.mips.iter().zip(&ftex.mips) {
                assert_eq!(a.data, b.data, "blocks changed at {}", p.display());
            }
            *seen.entry(ftex.format.code()).or_insert(0) += 1;
            checked += 1;
        }
        assert!(checked > 40, "only {checked} files exercised");
        assert!(
            seen.len() >= 3,
            "a face pack should hold several formats, saw {seen:?}"
        );
    }

    /// Mean absolute difference per channel between an image and its own
    /// encode/decode round trip.
    fn mean_error(w: u32, h: u32, before: &[u8], after: &[u8]) -> f64 {
        let n = (w as usize * h as usize)
            .min(before.len() / 4)
            .min(after.len() / 4);
        let (mut acc, mut count) = (0u64, 0u64);
        for i in 0..n {
            for c in 0..4 {
                acc += (before[i * 4 + c] as i32 - after[i * 4 + c] as i32).unsigned_abs() as u64;
                count += 1;
            }
        }
        acc as f64 / count.max(1) as f64
    }

    fn round_trip(format: PixelFormat, rgba: &[u8], w: u32, h: u32) -> Vec<u8> {
        let blocks = encode_blocks(format, rgba, w, h).unwrap();
        let tex = Ftex {
            format,
            version: VERSION_DEFAULT,
            width: w,
            height: h,
            depth: 1,
            texture_type: 3,
            nrt: 2,
            flags: 17,
            mips: vec![Mip {
                width: w,
                height: h,
                data: blocks,
            }],
        };
        let (_, _, out) = tex.to_rgba(0).unwrap();
        out
    }

    #[test]
    fn bc5_encodes_a_gradient_within_the_formats_own_precision() {
        // BC5 carries one 8-bit endpoint pair and 3-bit indices per channel, so
        // a smooth ramp is the case it should handle best. Only R and G are
        // compared: the preview rebuilds Z from them, and that channel is the
        // decoder's output, not something the encoder was given.
        let (w, h) = (64u32, 64u32);
        let rgba: Vec<u8> = (0..w * h)
            .flat_map(|i| {
                let x = i % w;
                let v = (x * 255 / w) as u8;
                [v, 255u8 - v, 200, 255]
            })
            .collect();
        let back = round_trip(PixelFormat::Bc5, &rgba, w, h);
        let mut acc = 0u64;
        for i in 0..(w * h) as usize {
            for c in 0..2 {
                acc += (rgba[i * 4 + c] as i32 - back[i * 4 + c] as i32).unsigned_abs() as u64;
            }
        }
        let err = acc as f64 / (w as f64 * h as f64 * 2.0);
        assert!(err < 4.0, "BC5 round trip error {err:.2} is too high");
    }

    #[test]
    fn bc1_and_bc3_keep_a_solid_block_within_rgb565() {
        let (w, h) = (16u32, 16u32);
        let rgba: Vec<u8> = (0..w * h).flat_map(|_| [40u8, 180, 90, 220]).collect();
        // BC1 stores 5-6-5, so a channel can be off by up to half a step:
        // 8 for red and blue, 4 for green. Anything worse is an encoder fault.
        let one = round_trip(PixelFormat::Bc1, &rgba, w, h);
        for px in one.chunks(4) {
            assert!((px[0] as i32 - 40).abs() <= 8, "BC1 red drift {px:?}");
            assert!((px[1] as i32 - 180).abs() <= 4, "BC1 green drift {px:?}");
            assert!((px[2] as i32 - 90).abs() <= 8, "BC1 blue drift {px:?}");
        }
        let three = round_trip(PixelFormat::Bc3, &rgba, w, h);
        for px in three.chunks(4) {
            assert!((px[0] as i32 - 40).abs() <= 8, "BC3 red drift {px:?}");
            assert!((px[1] as i32 - 180).abs() <= 4, "BC3 green drift {px:?}");
            assert!((px[2] as i32 - 90).abs() <= 8, "BC3 blue drift {px:?}");
            // Alpha is a full 8-bit endpoint pair, so a flat one is exact.
            assert_eq!(px[3], 220, "BC3 lost the alpha, which it stores exactly");
        }
    }

    #[test]
    fn bc3_keeps_two_distinct_colours_apart() {
        // Half the image red, half blue: the encoder must not collapse them.
        let (w, h) = (8u32, 8u32);
        let mut rgba = vec![0u8; (w * h * 4) as usize];
        for y in 0..h {
            for x in 0..w {
                let i = (y * w + x) as usize * 4;
                if x < w / 2 {
                    rgba[i..i + 4].copy_from_slice(&[240, 10, 10, 255]);
                } else {
                    rgba[i..i + 4].copy_from_slice(&[10, 10, 240, 255]);
                }
            }
        }
        let back = round_trip(PixelFormat::Bc3, &rgba, w, h);
        let left = &back[..4];
        let right = &back[((w / 2) as usize * 4)..((w / 2) as usize * 4 + 4)];
        assert!(
            left[0] as i32 - left[2] as i32 > 100,
            "red half lost: {left:?}"
        );
        assert!(
            right[2] as i32 - right[0] as i32 > 100,
            "blue half lost: {right:?}"
        );
        // Two flat halves are the easy case for a nearest-fit encoder, so the
        // average error should sit inside one 565 step, not tens of levels.
        let err = mean_error(w, h, &rgba, &back);
        assert!(err < 8.0, "BC3 two-colour round trip error {err:.2}");
    }

    #[test]
    fn formats_without_an_encoder_are_refused_by_name() {
        let rgba = [0u8; 4 * 4 * 4];
        let err = encode_blocks(PixelFormat::Bc7, &rgba, 4, 4).unwrap_err();
        assert!(err.to_string().contains("BC7"), "{err}");
        assert!(err.to_string().contains("no encoder"), "{err}");
    }
}
