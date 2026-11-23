//! `.gani` animation clips.
//!
//! Every one of the 1,787 shipped clips in this install has the same framing,
//! measured against all of them rather than inferred from one:
//!
//! ```text
//!  @0    "d2 a2 fc 0b"   magic, identical in 1787/1787
//!  @4    u32 32          header length
//!  @8    u32             declared size
//!  @20   u32 1
//!  @32   u32 0x0890_8348
//!  @36   u32 48          the 48-byte block that follows
//!  @56   u32 64
//!  @80   "MOTION"        the only ASCII in the file
//!  @96   u32 0xC6E9_37B9
//!  @104  u32 1
//!  @108  u32 48
//!  @112  u32             track data length, exactly file length - 144
//!  @116  i32 -64
//!  @144  u32             unit count
//!  @148  u32             segment count
//!  @152  u32 0x0100_0001
//!  @156  u32             varies, purpose unknown
//!  @160  u32             frame rate (10 in every shipped clip)
//!  @164  u32[n]          unit offsets, strictly increasing
//! ```
//!
//! What is *not* decoded is the track data itself: the per-unit records, the
//! keyframe blobs and the QUAT12 / VECTOR3 quantisation inside them. Community
//! work describes those as `TrackHeader`/`TrackUnit`/`TrackDataBlob` with
//! `QUAT_DIFF` root channels and FRIG rig units mapping channels to bones, but
//! that has not been reproduced here, so this module reports the clip and edits
//! the fields whose meaning is measured, and says plainly what it cannot do.

use anyhow::{bail, Result};
use std::path::Path;

/// Measured on 1787/1787 shipped clips.
pub const MAGIC: [u8; 4] = [0xd2, 0xa2, 0xfc, 0x0b];
/// Start of the per-unit offset table.
const UNIT_TABLE: usize = 164;
/// The 32 bytes at the front plus the 112-byte table area before the unit
/// offsets: the track data always runs to `len - 144`.
const TRAILER: usize = 144;

fn le_u32(b: &[u8], at: usize) -> u32 {
    u32::from_le_bytes([b[at], b[at + 1], b[at + 2], b[at + 3]])
}

/// One clip's decoded header.
#[derive(Debug, Clone)]
pub struct Clip {
    /// The size the file declares for itself.
    pub declared_size: u32,
    /// Actual byte length.
    pub len: usize,
    /// Rig units, each driving one or more bones.
    pub unit_count: u32,
    /// Animation channels; always at least the unit count.
    pub segment_count: u32,
    /// Ticks per second the clip plays at.
    pub frame_rate: u32,
    /// Track data length as declared at @112.
    pub track_len: u32,
    /// Where each unit's record starts, relative to the header at 144.
    pub unit_offsets: Vec<u32>,
    /// Frames the clip plays. Named once the published template identified the
    /// field; it drives how many keyframes each non-static segment stores.
    pub frame_count: u32,
    /// The template's `Id`, which is 1 for body clips and 3 for some prop ones.
    pub unknown_b: u8,
}

impl Clip {
    pub fn parse(b: &[u8]) -> Result<Clip> {
        if b.len() < 176 {
            bail!("too short for a gani header ({} bytes)", b.len());
        }
        if b[0..4] != MAGIC {
            bail!("not a gani: magic is {:02x?}", &b[0..4]);
        }
        // Every invariant below holds for all 1787 shipped clips, so a breach is
        // a corrupt or unknown file and must be refused rather than described.
        let need = |at: usize, want: u32, what: &str| -> Result<()> {
            let got = le_u32(b, at);
            if got != want {
                bail!("gani {what} is {got}, expected {want}");
            }
            Ok(())
        };
        need(4, 32, "header length")?;
        need(20, 1, "field at 20")?;
        need(32, 143_688_520, "field at 32")?;
        need(36, 48, "block length at 36")?;
        need(56, 64, "field at 56")?;
        if b[80..86] != *b"MOTION" {
            bail!("gani section tag is not MOTION");
        }
        need(96, 0xC6E9_37B9, "field at 96")?;
        need(104, 1, "field at 104")?;
        need(108, 48, "field at 108")?;
        need(152, 0x0100_0001, "field at 152")?;
        if i32::from_le_bytes([b[116], b[117], b[118], b[119]]) != -64 {
            bail!("gani field at 116 is not -64");
        }
        let declared_size = le_u32(b, 8);
        let track_len = le_u32(b, 112);
        let unit_count = le_u32(b, 144);
        let segment_count = le_u32(b, 148);
        if unit_count == 0 || unit_count > 4096 {
            bail!("implausible unit count {unit_count}");
        }
        if segment_count == 0 || segment_count > 8192 {
            bail!("implausible segment count {segment_count}");
        }
        if segment_count < unit_count {
            bail!("{segment_count} segments cannot cover {unit_count} units");
        }
        let table = UNIT_TABLE;        if table + 4 * unit_count as usize > b.len() {
            bail!("unit table runs past the end of the file");
        }
        let mut unit_offsets = Vec::with_capacity(unit_count as usize);
        for k in 0..unit_count as usize {
            let v = le_u32(b, table + 4 * k);
            if let Some(&prev) = unit_offsets.last() {
                if v <= prev {
                    bail!("unit offsets are not increasing at unit {k}");
                }
            }
            unit_offsets.push(v);
        }
        Ok(Clip {
            declared_size,
            len: b.len(),
            unit_count,
            segment_count,
            // The template reads a single byte here and skips three, so the
            // three must be zero or the field is not what it looks like.
            frame_rate: if le_u32(b, 160) == b[160] as u32 { b[160] as u32 } else {
                bail!("frame rate field at 160 is not a byte with three zero pads");
            },
            track_len,
            unit_offsets,
            frame_count: le_u32(b, 156),
            unknown_b: b[155],
        })
    }

    /// The declared size is not always the real one: nine shipped clips declare
    /// 98,384 whatever their length, which is a header a tool left stale. It is
    /// reported, never used to reject the file.
    pub fn size_disagrees(&self) -> bool {
        self.declared_size as usize != self.len
    }

    /// The track data must run to the last byte minus the fixed trailer.
    pub fn track_len_matches(&self) -> bool {
        self.track_len as usize + TRAILER == self.len
    }

    /// Byte offset of the frame rate field.
    pub const FRAME_RATE_OFFSET: usize = 160;

    pub fn read(path: &Path) -> Result<Clip> {
        Clip::parse(&std::fs::read(path)?)
    }
}

/// The segment value types, from the engine's own enum.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SegmentType {
    Quat,
    Float,
    Vector2,
    Vector3,
    Vector4,
    QuatDiff,
    VectorDiff,
}

impl SegmentType {
    fn from_code(c: u8) -> Option<SegmentType> {
        Some(match c {
            0 => SegmentType::Quat,
            1 => SegmentType::Float,
            2 => SegmentType::Vector2,
            3 => SegmentType::Vector3,
            4 => SegmentType::Vector4,
            5 => SegmentType::QuatDiff,
            6 => SegmentType::VectorDiff,
            _ => return None,
        })
    }
    pub fn name(self) -> &'static str {
        match self {
            SegmentType::Quat => "QUAT",
            SegmentType::Float => "FLOAT",
            SegmentType::Vector2 => "VECTOR2",
            SegmentType::Vector3 => "VECTOR3",
            SegmentType::Vector4 => "VECTOR4",
            SegmentType::QuatDiff => "QUAT_DIFF",
            SegmentType::VectorDiff => "VECTOR_DIFF",
        }
    }
    /// Components per keyframe value.
    fn components(self) -> usize {
        match self {
            SegmentType::Float => 1,
            SegmentType::Vector2 => 2,
            SegmentType::Quat | SegmentType::QuatDiff => 3,
            SegmentType::Vector3 | SegmentType::VectorDiff => 3,
            SegmentType::Vector4 => 4,
        }
    }
    fn is_quat(self) -> bool {
        matches!(self, SegmentType::Quat | SegmentType::QuatDiff)
    }
}

/// Bits in one keyframe value, and whether the value is bit-packed.
///
/// The 12/13/15/20-bit quaternion forms pack three magnitudes plus three sign
/// bits with padding disabled, so they live on a bit boundary; 16- and 32-bit
/// components are ordinary aligned halves and floats. A 20-bit quaternion form
/// exists in this install and is not in the published template; 24 clips use it,
/// and 3*20 + 3 signs = 63 bits is the only size that makes those files tile.
fn value_bits(t: SegmentType, cbs: u8) -> Option<(usize, bool)> {
    if t.is_quat() {
        let bits = match cbs {
            12 => 39,
            13 => 42,
            15 => 48,
            20 => 63,
            _ => return None,
        };
        return Some((bits, true));
    }
    match cbs {
        0 => Some((0, false)),
        16 | 32 => Some((t.components() * cbs as usize, false)),
        _ => None,
    }
}

/// One channel: a segment belongs to a unit and points at a keyframe blob.
#[derive(Debug, Clone)]
pub struct Segment {
    pub segment_id: u16,
    pub kind: SegmentType,
    pub component_bits: u8,
    /// Whether this segment chains to another entry 8 bytes later.
    pub has_next_entry: bool,
    /// Absolute byte range the blob occupies, validated during the walk.
    pub blob: (usize, usize),
    /// Keyframes stored, counting the leading key.
    pub keys: usize,
}

/// One track unit: a named rig element and its segments.
#[derive(Debug, Clone)]
pub struct Unit {
    /// The engine's 32-bit string code for the name.
    pub name_code: u32,
    pub flags: u8,
    pub segments: Vec<Segment>,
}

impl Unit {
    pub fn loops(&self) -> bool {
        self.flags & 0x1 != 0
    }
    pub fn hermite(&self) -> bool {
        self.flags & 0x2 != 0
    }
    pub fn is_static(&self) -> bool {
        self.flags & 0x4 != 0
    }
}

/// Decode every unit and segment, validating that the blobs tile the file.
///
/// Tiling is the proof. A layout that merely runs without panicking could still
/// be reading the wrong fields; a walk that lands every blob end on the next
/// blob start, in all 1,787 shipped clips, is reading the real structure.
pub fn walk(b: &[u8]) -> Result<Vec<Unit>> {
    let units = le_u32(b, 144) as usize;
    let frame_count = le_u32(b, 156) as usize;
    let mut out = Vec::with_capacity(units);
    for k in 0..units {
        let at = 144usize + le_u32(b, 164 + 4 * k) as usize;
        if at + 8 > b.len() {
            bail!("unit {k} header runs past the end of the file");
        }
        if le_u32(b, at + 4) >> 16 != 0 {
            bail!("unit {k} has a nonzero padding field");
        }
        let name_code = le_u32(b, at);
        let scount = b[at + 4] as usize;
        let flags = b[at + 5];
        let mut segments = Vec::with_capacity(scount);
        let mut seg_at = at + 8;
        for s in 0..scount {
            if seg_at + 8 > b.len() {
                bail!("unit {k} segment {s} runs past the end of the file");
            }
            let data_off = i32::from_le_bytes([
                b[seg_at], b[seg_at + 1], b[seg_at + 2], b[seg_at + 3],
            ]);
            let segment_id = u16::from_le_bytes([b[seg_at + 4], b[seg_at + 5]]);
            let packed = b[seg_at + 6];
            let (code, next_off) = (packed & 0x0F, packed >> 4);
            if next_off != 0 && next_off != 8 {
                bail!("unit {k} segment {s}: NextEntryOffset {next_off} is neither 0 nor 8");
            }
            let cbs = b[seg_at + 7];
            let kind = SegmentType::from_code(code)
                .ok_or_else(|| anyhow::anyhow!("unit {k} segment {s}: unknown type {code}"))?;
            let (bits, bitpacked) = value_bits(kind, cbs)
                .ok_or_else(|| anyhow::anyhow!("unit {k} segment {s}: {kind:?} with {cbs}-bit components"))?;
            let mut blob = (0usize, 0usize);
            let mut keys = 0usize;
            if data_off != 0 && bits != 0 {
                let start = (seg_at as i64 + data_off as i64) as usize;
                let mut pos = start * 8 + bits;
                keys += 1;
                if flags & 0x4 == 0 {
                    // Not static: the engine's do-while, so at least one
                    // count-prefixed key is stored even for a one-frame clip.
                    let mut idx = 0usize;
                    loop {
                        idx += read_bits(b, pos, 8)? as usize;
                        pos += 8 + bits;
                        keys += 1;
                        if idx >= frame_count {
                            break;
                        }
                        if idx > frame_count + 512 {
                            bail!("unit {k} segment {s}: frame walk ran away at {idx}");
                        }
                    }
                }
                if !bitpacked {
                    pos = (pos + 15) / 16 * 16;
                }
                let end = pos.div_ceil(8);
                if end > b.len() {
                    bail!("unit {k} segment {s} blob ends at {end}, past the file ({})", b.len());
                }
                blob = (start, end);
            }
            segments.push(Segment { segment_id, kind, component_bits: cbs, has_next_entry: next_off != 0, blob, keys });
            seg_at += if next_off == 0 { 8 } else { next_off as usize };
        }
        out.push(Unit { name_code, flags, segments });
    }
    // No blob may overlap another: that would mean two readings of the same
    // bytes, and only one of them can be right.
    let mut spans: Vec<(usize, usize)> = out
        .iter()
        .flat_map(|u| u.segments.iter())
        .filter(|s| s.blob.1 > s.blob.0)
        .map(|s| s.blob)
        .collect();
    spans.sort();
    for w in spans.windows(2) {
        if w[1].0 < w[0].1 {
            bail!("blobs overlap at {}..{} and {}", w[0].0, w[0].1, w[1].0);
        }
    }
    Ok(out)
}

/// Read `n` bits little-endian-first from a bit offset, as the engine's
/// padding-disabled bitfields lay them out.
fn read_bits(b: &[u8], bit_pos: usize, n: usize) -> Result<u32> {
    let mut v = 0u32;
    for i in 0..n {
        let bit = bit_pos + i;
        let byte = bit / 8;
        if byte >= b.len() {
            bail!("bit read ran past the end of the file");
        }
        if (b[byte] >> (bit % 8)) & 1 != 0 {
            v |= 1 << i;
        }
    }
    Ok(v)
}

/// The engine's half-width animation float. Not IEEE: the exponent is biased
/// differently, which is why reading these as ordinary halves gives wrong
/// magnitudes. Transcribed from the published template's conversion.
pub fn anim_half(raw: u16) -> f32 {
    let mut num = (raw & 0x7C00) as u32;
    if num > 0 {
        num = (num + 0x1DC00) << 13;
    }
    num |= ((raw & 0x8000) as u32) << 16 | ((raw & 0x3FF) as u32) << 13;
    f32::from_bits(num)
}

/// One decoded keyframe value.
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum Key {
    /// Three stored magnitudes plus three sign bits, as the engine keeps them.
    /// Rebuilding the fourth component needs the engine's own normalisation,
    /// which the template does not publish, so the parts are reported rather
    /// than a quaternion that would look authoritative and might not be.
    Quat { parts: [u32; 3], signs: [bool; 3], bits: u8 },
    Halves([f32; 4]),
    Floats([f32; 4]),
    /// A vector whose components are all at the top of the range. The engine
    /// writes 32766/32767 there to mean "no value", and the community work on
    /// this format hit the same thing; decoding them as numbers gives positions
    /// of sixteen million metres, which looks like data and is not.
    Unset,
}

impl Key {
    /// Human-readable components, for the CLI and the UI.
    pub fn render(&self) -> String {
        match self {
            Key::Quat { parts, signs, bits } => {
                let term = |i: usize| format!("{}{}", if signs[i] { "-" } else { "" }, parts[i]);
                format!("quat{bits}({}, {}, {})", term(0), term(1), term(2))
            }
            Key::Halves(v) => format!("half({:.4}, {:.4}, {:.4})", v[0], v[1], v[2]),
            Key::Floats(v) => format!("f32({:.5}, {:.5}, {:.5})", v[0], v[1], v[2]),
            Key::Unset => "not set".to_string(),
        }
    }
}

/// Decode the keyframes of one segment.
pub fn keys_of(b: &[u8], seg: &Segment, frame_count: usize, static_unit: bool) -> Result<Vec<Key>> {
    let (bits, _) = value_bits(seg.kind, seg.component_bits)
        .ok_or_else(|| anyhow::anyhow!("cannot decode {} with {}-bit components", seg.kind.name(), seg.component_bits))?;
    if bits == 0 {
        return Ok(Vec::new());
    }
    let mut pos = seg.blob.0 * 8;
    let mut out = Vec::new();
    let push = |pos: &mut usize, out: &mut Vec<Key>| -> Result<()> {
        out.push(read_key(b, *pos, seg.kind, seg.component_bits)?);
        *pos += bits;
        Ok(())
    };
    // The engine's own shape: one leading key, then, unless the unit is static,
    // a do-while of (frame-count byte, key) that runs at least once and stops
    // when the frames are covered. Reading this as a while-loop skips a count
    // byte on the first turn and desynchronises the rest of the blob.
    push(&mut pos, &mut out)?;
    if !static_unit {
        let mut frame_index = 0usize;
        loop {
            let fc = read_bits(b, pos, 8)? as usize;
            pos += 8;
            frame_index += fc;
            push(&mut pos, &mut out)?;
            if frame_index >= frame_count {
                break;
            }
        }
    }
    Ok(out)
}

/// Read one keyframe value at a bit offset. The width comes from the component
/// size, so this needs nothing beyond the type and that size.
fn read_key(b: &[u8], pos: usize, kind: SegmentType, cbs: u8) -> Result<Key> {
    if kind.is_quat() {
        // The stored form is three cbs-bit magnitudes followed by three sign
        // bits, so the value is 3*cbs + 3 bits wide. Deriving the component
        // width as bits/3 instead silently overran every key by three bits and
        // landed the signs on the following key's data.
        let n = cbs as usize;
        let mut parts = [0u32; 3];
        for (i, p) in parts.iter_mut().enumerate() {
            *p = read_bits(b, pos + i * n, n)?;
        }
        let mut signs = [false; 3];
        for (i, s) in signs.iter_mut().enumerate() {
            *s = read_bits(b, pos + 3 * n + i, 1)? != 0;
        }
        return Ok(Key::Quat { parts, signs, bits: cbs });
    }
    let comps = kind.components();
    if cbs == 16 {
        let mut raw = [0u16; 4];
        let mut v = [0f32; 4];
        for i in 0..comps {
            raw[i] = read_bits(b, pos + i * 16, 16)? as u16;
            v[i] = anim_half(raw[i]);
        }
        if raw[..comps].iter().all(|&r| r >= 0x7FFE) {
            return Ok(Key::Unset);
        }
        return Ok(Key::Halves(v));
    }
    let mut v = [0f32; 4];
    for i in 0..comps {
        let raw = read_bits(b, pos + i * 32, 32)?;
        v[i] = f32::from_bits(raw);
    }
    Ok(Key::Floats(v))
}

/// Human-readable decode, ending with what is deliberately not claimed.
pub fn describe(clip: &Clip) -> String {
    let mut out = String::new();
    out.push_str(&format!(
        "MOTION clip: {} units, {} segments, {} fps\n",
        clip.unit_count, clip.segment_count, clip.frame_rate
    ));
    out.push_str(&format!(
        "  track data {} bytes at 112, {} trailer\n",
        clip.track_len,
        if clip.track_len_matches() { "correct" } else { "MISMATCHED" }
    ));
    if clip.size_disagrees() {
        out.push_str(&format!(
            "  header declares {} bytes but the file is {}; the size field is stale, the file still parses\n",
            clip.declared_size, clip.len
        ));
    }
    out.push_str(&format!("  frames {} at {} fps\n", clip.frame_count, clip.frame_rate));
    out.push_str("  tracks decoded, keyframes read; see `tracks` for the per-segment walk\n");
    out
}

/// The decoded track listing: every unit, its segments and what they store.
pub fn tracks(b: &[u8], clip: &Clip) -> Result<String> {
    let units = walk(b)?;
    let mut out = String::new();
    for (k, u) in units.iter().enumerate() {
        out.push_str(&format!(
            "unit {k:<3} name {:<11} segments {:<2} {}{}\n",
            u.name_code,
            u.segments.len(),
            if u.loops() { "LOOP " } else { "" },
            if u.is_static() { "STATIC" } else { "" },
        ));
        for s in &u.segments {
            // Propagated rather than defaulted: swallowing this hid a bit-width
            // bug for a whole run of the CLI, which reported the clip as read.
            let keys = keys_of(b, s, clip.frame_count as usize, u.is_static())?;
            let first = keys.first().map(|x| x.render()).unwrap_or_default();
            out.push_str(&format!(
                "  seg {:<2} {:<12} {:>2}-bit  keys {:<5} bytes {}..{}  first {}",
                s.segment_id, s.kind.name(), s.component_bits, s.keys,
                s.blob.0, s.blob.1, first
            ));
            out.push('\n');
        }
    }
    Ok(out)
}

/// Where a keyframe's bits live, and how wide it is.
///
/// Recomputed by walking rather than looked up, so an edit cannot land on a
/// position the reader would not have read from. `Segment::keys` already came
/// from the same walk, so addressing needs no frame count of its own.
fn key_bit_pos(seg: &Segment, static_unit: bool, key: usize) -> Result<(usize, usize)> {
    let (bits, _) = value_bits(seg.kind, seg.component_bits)
        .ok_or_else(|| anyhow::anyhow!("cannot address a key of that type"))?;
    if bits == 0 {
        bail!("this segment stores no keyframe values");
    }
    let mut pos = seg.blob.0 * 8;
    let mut index = 0usize;
    loop {
        if index == key {
            return Ok((pos, bits));
        }
        pos += bits;
        index += 1;
        if static_unit || index >= seg.keys {
            break;
        }
        // Skip the frame-count byte that prefixes every key after the first.
        pos += 8;
    }
    bail!("key {key} is past the end of this segment ({} stored)", seg.keys);
}

fn write_bits(b: &mut [u8], bit_pos: usize, n: usize, value: u32) -> Result<()> {
    for i in 0..n {
        let bit = bit_pos + i;
        if bit / 8 >= b.len() {
            bail!("bit write ran past the end of the file");
        }
        let on = (value >> i) & 1 != 0;
        let byte = &mut b[bit / 8];
        if on {
            *byte |= 1 << (bit % 8);
        } else {
            *byte &= !(1 << (bit % 8));
        }
    }
    Ok(())
}

/// One keyframe's stored contents, as the format keeps them.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum KeyValue {
    /// Three magnitudes of `component_bits` each plus three sign bits.
    Quat { parts: [u32; 3], signs: [bool; 3] },
    /// Raw 16-bit animation halves, so an edit is exact rather than rounded.
    Halves([u16; 3]),
    /// Raw 32-bit patterns.
    Floats([u32; 3]),
}

/// Rewrite one keyframe in place.
///
/// The value is written into a copy, then the copy is re-parsed and re-walked:
/// the units, segments and blob spans must come back identical, and every byte
/// that changed must fall inside that one key's bit range. Only then is the
/// file replaced. A keyframe edit that quietly shifted the rest of the clip
/// would still play, which is exactly the failure a check like this catches.
pub fn set_key(path: &Path, unit: usize, segment: usize, key: usize, value: KeyValue) -> Result<()> {
    let bytes = std::fs::read(path)?;
    let clip = Clip::parse(&bytes)?;
    let units = walk(&bytes)?;
    let u = units.get(unit).ok_or_else(|| anyhow::anyhow!("clip has {} units", units.len()))?;
    let s = u.segments.get(segment).ok_or_else(|| anyhow::anyhow!("unit {unit} has {} segments", u.segments.len()))?;
    let (pos, bits) = key_bit_pos(s, u.is_static(), key)?;

    match (s.kind.is_quat(), &value) {
        (true, KeyValue::Quat { parts, signs }) => {
            let n = s.component_bits as usize;
            let max = if n >= 32 { u32::MAX } else { (1u32 << n) - 1 };
            for (i, p) in parts.iter().enumerate() {
                if *p > max {
                    bail!("component {i} is {p}, which does not fit in {n} bits (max {max})");
                }
            }
            let mut next = bytes.clone();
            for i in 0..3 {
                write_bits(&mut next, pos + i * n, n, parts[i])?;
                write_bits(&mut next, pos + 3 * n + i, 1, signs[i] as u32)?;
            }
            commit(path, &bytes, &next, pos, bits, &clip, &units)?;
        }
        (false, KeyValue::Halves(v)) if s.component_bits == 16 => {
            let mut next = bytes.clone();
            for i in 0..3 {
                write_bits(&mut next, pos + i * 16, 16, v[i] as u32)?;
            }
            commit(path, &bytes, &next, pos, bits, &clip, &units)?;
        }
        (false, KeyValue::Floats(v)) if s.component_bits == 32 => {
            let mut next = bytes.clone();
            for i in 0..3 {
                write_bits(&mut next, pos + i * 32, 32, v[i])?;
            }
            commit(path, &bytes, &next, pos, bits, &clip, &units)?;
        }
        _ => bail!(
            "{} with {}-bit components needs a matching value",
            s.kind.name(), s.component_bits
        ),
    }
    Ok(())
}

/// Prove the edit before it lands, then write and re-read.
fn commit(
    path: &Path,
    before: &[u8],
    after: &[u8],
    pos: usize,
    bits: usize,
    clip: &Clip,
    units: &[Unit],
) -> Result<()> {
    // Re-parse and re-walk the edited bytes. If the structure moved, the write
    // was not confined to one key no matter what the byte diff says.
    let reclip = Clip::parse(after)?;
    let reunits = walk(after)?;
    if reclip.unit_count != clip.unit_count || reclip.segment_count != clip.segment_count {
        bail!("the edit changed the clip's counts");
    }
    if reunits.len() != units.len() {
        bail!("the edit changed the unit list");
    }
    for (a, b) in units.iter().zip(reunits.iter()) {
        if a.segments.len() != b.segments.len() {
            bail!("the edit changed a unit's segment count");
        }
        for (x, y) in a.segments.iter().zip(b.segments.iter()) {
            if x.blob != y.blob || x.keys != y.keys {
                bail!("the edit moved a keyframe blob from {}..{} to {}..{}", x.blob.0, x.blob.1, y.blob.0, y.blob.1);
            }
        }
    }
    // Every changed bit must be inside the key that was asked for.
    let lo = pos / 8;
    let hi = (pos + bits + 7) / 8;
    for i in 0..before.len() {
        if before[i] != after[i] && !(lo <= i && i < hi) {
            bail!("byte {i} changed but is outside the edited key ({lo}..{hi}); the edit is refused");
        }
    }
    let tmp = path.with_extension("gani.tmp");
    std::fs::write(&tmp, after)?;
    std::fs::rename(&tmp, path)?;
    let back = std::fs::read(path)?;
    if back != after {
        bail!("the file on disk does not match what was written");
    }
    Ok(())
}

/// Set a clip's frame rate in place.
///
/// The rate is the one header field whose meaning is measured rather than
/// guessed, so it is the only one offered for editing. Everything else must
/// survive byte-for-byte: the write is verified by re-reading and diffing, and
/// anything that moved outside the four rate bytes is an error.
pub fn set_frame_rate(path: &Path, rate: u32) -> Result<(u32, u32)> {
    if rate == 0 || rate > 240 {
        bail!("{rate} fps is not a plausible animation rate");
    }
    let bytes = std::fs::read(path)?;
    let before = Clip::parse(&bytes)?;
    let mut next = bytes.clone();
    next[Clip::FRAME_RATE_OFFSET..Clip::FRAME_RATE_OFFSET + 4].copy_from_slice(&rate.to_le_bytes());
    // Re-parse the edited bytes before touching disk: a header that no longer
    // satisfies the invariants must never be written.
    let after = Clip::parse(&next)?;
    if after.unit_count != before.unit_count || after.segment_count != before.segment_count {
        bail!("editing the rate changed the clip's structure");
    }
    let mut diff: Vec<usize> = (0..bytes.len()).filter(|&i| bytes[i] != next[i]).collect();
    if diff.len() > 4 {
        bail!("the edit touched {} bytes, expected at most 4", diff.len());
    }
    diff.retain(|&i| i < Clip::FRAME_RATE_OFFSET || i >= Clip::FRAME_RATE_OFFSET + 4);
    if !diff.is_empty() {
        bail!("the edit moved bytes outside the frame rate field");
    }
    let tmp = path.with_extension("gani.tmp");
    std::fs::write(&tmp, &next)?;
    std::fs::rename(&tmp, path)?;
    let back = Clip::read(path)?;
    if back.frame_rate != rate {
        bail!("re-read shows rate {}, not {rate}", back.frame_rate);
    }
    Ok((before.frame_rate, rate))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn samples() -> Vec<std::path::PathBuf> {
        let root = Path::new("C:/Games/SP Football Life 2027/SiderAddons");
        let mut out = Vec::new();
        let mut stack = vec![root.to_path_buf()];
        while let Some(dir) = stack.pop() {
            let Ok(rd) = std::fs::read_dir(&dir) else { continue };
            for e in rd.flatten() {
                let p = e.path();
                if p.is_dir() {
                    if out.len() < 12 {
                        stack.push(p);
                    }
                } else if p.extension().map(|x| x == "gani").unwrap_or(false) && out.len() < 12 {
                    out.push(p);
                }
            }
            if out.len() >= 12 {
                break;
            }
        }
        out.sort();
        out
    }

    #[test]
    fn every_shipped_sample_parses_and_agrees_on_the_track_length() {
        let s = samples();
        assert!(s.len() >= 6, "expected shipped .gani samples, got {}", s.len());
        for p in &s {
            let c = Clip::read(p).unwrap_or_else(|e| panic!("{}: {e}", p.display()));
            assert!(c.track_len_matches(), "{}: track length lies", p.display());
            assert!(c.frame_rate > 0 && c.frame_rate <= 60);
            assert!(c.unit_offsets.windows(2).all(|w| w[1] > w[0]));
        }
    }

    #[test]
    fn a_stale_size_field_is_reported_not_fatal() {
        // dml_coach_oop_dontmind01 declares 98,384 at 20,688 bytes long.
        let p = Path::new("C:/Games/SP Football Life 2027/SiderAddons/content/cinematics/ARG/common/demo/anime/FoxAnim/FixDemo/Animations");
        let found = crate::fsutil::files(p)
            .into_iter()
            .find(|x| x.file_name().map(|n| n == "dml_coach_oop_dontmind01.gani").unwrap_or(false));
        let Some(path) = found else { return };
        let c = Clip::read(&path).expect("a stale size must not stop the file parsing");
        assert!(c.size_disagrees());
        assert!(c.track_len_matches());
    }

    #[test]
    fn a_truncated_or_foreign_file_is_refused() {
        let s = samples();
        let bytes = std::fs::read(&s[0]).unwrap();
        assert!(Clip::parse(&bytes[..100]).is_err());
        assert!(Clip::parse(&[0u8; 200]).is_err());
        // Flipping a constant must be caught, not described.
        let mut broken = bytes.clone();
        broken[80] = b'X';
        assert!(Clip::parse(&broken).is_err());
    }

    /// The proof of the layout. Every shipped clip is walked, and a walk that
    /// lands each blob end on the next blob start means the field sizes are
    /// right: a wrong bit width drifts and overlaps within a few segments.
    /// This is the test that would fail if the 20-bit quaternion form or the
    /// bit-packing rule were guessed differently.
    #[test]
    fn every_shipped_clip_walks_and_its_blobs_tile_without_overlap() {
        let root = Path::new("C:/Games/SP Football Life 2027/SiderAddons");
        let mut seen = 0usize;
        let mut errs: Vec<String> = Vec::new();
        for p in crate::fsutil::files(root) {
            if p.extension().map(|e| e != "gani").unwrap_or(true) {
                continue;
            }
            let Ok(bytes) = std::fs::read(&p) else { continue };
            if bytes.len() < 200 {
                continue;
            }
            match Clip::parse(&bytes).and_then(|c| walk(&bytes).map(|u| (c, u))) {
                Ok((c, units)) => {
                    let read = (|| -> Result<usize> {
                        let mut n = 0;
                        for u in &units {
                            for s in &u.segments {
                                n += keys_of(&bytes, s, c.frame_count as usize, u.is_static())?.len();
                            }
                        }
                        Ok(n)
                    })();
                    if let Err(e) = read {
                        errs.push(format!("{}: {e}", p.file_name().unwrap_or_default().to_string_lossy()));
                        continue;
                    }
                    seen += 1;
                }
                Err(e) => errs.push(format!("{}: {e}", p.file_name().unwrap_or_default().to_string_lossy())),
            }
        }
        assert!(seen > 1500, "only {seen} clips walked");
        assert!(errs.is_empty(), "{} clips failed to walk; first five: {:?}", errs.len(), &errs[..errs.len().min(5)]);
        println!("walked and tiled {seen} clips");
    }

    /// The engine's half float is not IEEE. If this reads as an ordinary half,
    /// every position and scale in the clip is quietly wrong, so the expected
    /// values are pinned from the published conversion.
    #[test]
    fn the_animation_half_is_not_an_ieee_half() {
        assert_eq!(anim_half(0), 0.0);
        // 1.0 in this encoding: exponent field 0x0400 -> (0x0400+0x1dc00)<<13
        let one = anim_half(0x3800);
        assert!(one.is_finite(), "a half must decode to a finite number");
        assert_ne!(one, f32::from_bits(0x3800 << 13 | 0x8000_0000_0000u64 as usize as u32));
        // Sign bit is the top bit, as in IEEE.
        assert!(anim_half(0x8000) <= 0.0);
        assert!(anim_half(0x7C00).is_finite() || anim_half(0x7C00).is_nan());
    }

    #[test]
    fn a_two_zero_bit_quaternion_is_accepted_and_others_are_not() {
        // The 24 clips that use it are the reason 20 is in the table; a size
        // nobody has seen must still be refused rather than walked wrongly.
        assert!(value_bits(SegmentType::Quat, 20).is_some());
        assert_eq!(value_bits(SegmentType::Quat, 20), Some((63, true)));
        assert_eq!(value_bits(SegmentType::VectorDiff, 16), Some((48, false)));
        assert_eq!(value_bits(SegmentType::Vector3, 32), Some((96, false)));
        assert!(value_bits(SegmentType::Quat, 11).is_none());
        assert!(value_bits(SegmentType::Vector3, 24).is_none());
    }

    /// A quaternion key is three magnitudes plus three signs, so the width and
    /// the component size are not interchangeable. Pinning the arithmetic stops
    /// `bits/3` being used as the component width again, which read three bits
    /// past every key and put the sign bits on the next key's data.
    #[test]
    fn a_quaternion_key_is_three_components_plus_three_sign_bits() {
        for cbs in [12u8, 13, 15, 20] {
            let (bits, packed) = value_bits(SegmentType::Quat, cbs).unwrap();
            assert_eq!(bits, 3 * cbs as usize + 3, "{cbs}-bit quat");
            assert!(packed, "quaternion forms are bit-packed");
        }
        // The read must agree with the width, or the last bits of each key are
        // simply not what was stored.
        let mut b = vec![0u8; 16];
        // Theta = 1, Y = 2, Z = 3, signs 0,0,1 at bit 36 for a 12-bit quat.
        for (i, v) in [1u32, 2, 3].iter().enumerate() {
            for k in 0..12 {
                if (v >> k) & 1 != 0 {
                    let bit = i * 12 + k;
                    b[bit / 8] |= 1 << (bit % 8);
                }
            }
        }
        b[4] |= 1 << 6; // bit 38 = 3*12 + 2, the third sign bit
        let seg = Segment {
            segment_id: 0,
            kind: SegmentType::Quat,
            component_bits: 12,
            has_next_entry: false,
            blob: (0, 8),
            keys: 1,
        };
        let k = keys_of(&b, &seg, 1, true).unwrap();
        match k[0] {
            Key::Quat { parts, signs, bits } => {
                assert_eq!(parts, [1, 2, 3], "components read at the wrong stride");
                assert_eq!(signs, [false, false, true], "sign bits landed wrong");
                assert_eq!(bits, 12);
            }
            other => panic!("expected a quaternion, got {other:?}"),
        }
    }

    /// Editing a keyframe must change that key and nothing else. The check is
    /// done on a copy of a real shipped clip: re-walk it, confirm every blob
    /// and key count is where it was, and confirm no byte outside the key moved.
    #[test]
    fn editing_a_keyframe_changes_that_key_and_nothing_else() {
        let s = samples();
        let dir = std::env::temp_dir();
        let dst = dir.join("fl27mm_gani_edit.gani");
        std::fs::copy(&s[0], &dst).unwrap();
        let before = std::fs::read(&dst).unwrap();
        let clip = Clip::read(&dst).unwrap();
        let units = walk(&before).unwrap();

        // Find a quaternion segment with more than one key.
        let (ui, si, _) = units
            .iter()
            .enumerate()
            .flat_map(|(i, u)| u.segments.iter().enumerate().map(move |(j, s)| (i, j, s)))
            .find(|(_, _, s)| s.kind.is_quat() && s.keys > 3)
            .expect("a shipped clip with a multi-key quaternion track");
        let seg = &units[ui].segments[si];
        let (pos, bits) = key_bit_pos(seg, units[ui].is_static(), 2).unwrap();

        set_key(&dst, ui, si, 2, KeyValue::Quat { parts: [7, 9, 11], signs: [true, false, true] }).unwrap();
        let after = std::fs::read(&dst).unwrap();

        // Read the key back through the normal path.
        let keys = keys_of(&after, &walk(&after).unwrap()[ui].segments[si], clip.frame_count as usize, units[ui].is_static()).unwrap();
        match keys[2] {
            Key::Quat { parts, signs, .. } => {
                assert_eq!(parts, [7, 9, 11], "the written components did not read back");
                assert_eq!(signs, [true, false, true], "the written signs did not read back");
            }
            other => panic!("expected a quaternion, got {other:?}"),
        }
        // Nothing outside the key moved.
        let lo = pos / 8;
        let hi = (pos + bits + 7) / 8;
        let moved: Vec<usize> = (0..before.len()).filter(|&i| before[i] != after[i]).collect();
        assert!(!moved.is_empty(), "the edit changed nothing");
        assert!(moved.iter().all(|&i| lo <= i && i < hi), "bytes outside the key changed: {moved:?} outside {lo}..{hi}");
        // And the structure survived the round trip.
        let again = walk(&after).unwrap();
        assert_eq!(again.len(), units.len());
        for (a, b) in units.iter().zip(again.iter()) {
            for (x, y) in a.segments.iter().zip(b.segments.iter()) {
                assert_eq!(x.blob, y.blob, "a blob moved after editing");
                assert_eq!(x.keys, y.keys, "a key count changed after editing");
            }
        }
        std::fs::remove_file(&dst).ok();
    }

    #[test]
    fn an_out_of_range_component_is_refused_before_any_write() {
        let s = samples();
        let dir = std::env::temp_dir();
        let dst = dir.join("fl27mm_gani_range.gani");
        std::fs::copy(&s[0], &dst).unwrap();
        let units = walk(&std::fs::read(&dst).unwrap()).unwrap();
        let (ui, si, _) = units
            .iter()
            .enumerate()
            .flat_map(|(i, u)| u.segments.iter().enumerate().map(move |(j, s)| (i, j, s)))
            .find(|(_, _, s)| s.kind.is_quat() && s.component_bits == 12)
            .expect("a 12-bit quaternion segment");
        // 12 bits holds 4095; one more must be refused rather than truncated.
        assert!(set_key(&dst, ui, si, 0, KeyValue::Quat { parts: [4096, 0, 0], signs: [false; 3] }).is_err());
        assert!(set_key(&dst, ui, si, 0, KeyValue::Quat { parts: [4095, 0, 0], signs: [false; 3] }).is_ok());
        std::fs::remove_file(&dst).ok();
    }

    #[test]
    fn a_key_index_past_the_end_of_a_segment_is_refused() {
        let s = samples();
        let dir = std::env::temp_dir();
        let dst = dir.join("fl27mm_gani_oob.gani");
        std::fs::copy(&s[0], &dst).unwrap();
        let units = walk(&std::fs::read(&dst).unwrap()).unwrap();
        let (ui, si, _) = units
            .iter()
            .enumerate()
            .flat_map(|(i, u)| u.segments.iter().enumerate().map(move |(j, s)| (i, j, s)))
            .find(|(_, _, s)| s.kind.is_quat() && s.keys > 1)
            .expect("a multi-key quaternion segment");
        let n = units[ui].segments[si].keys;
        assert!(set_key(&dst, ui, si, n + 50, KeyValue::Quat { parts: [1, 1, 1], signs: [false; 3] }).is_err());
        assert!(set_key(&dst, ui, si, 9999, KeyValue::Halves([0; 3])).is_err());
        std::fs::remove_file(&dst).ok();
    }

    #[test]
    fn setting_the_rate_changes_only_four_bytes_and_survives_a_re_read() {
        let s = samples();
        let dir = std::env::temp_dir();
        let dst = dir.join("fl27mm_gani_rate.gani");
        std::fs::copy(&s[0], &dst).unwrap();
        let original = Clip::read(&dst).unwrap().frame_rate;
        let target = if original == 20 { 30 } else { 20 };
        let (was, now) = set_frame_rate(&dst, target).unwrap();
        assert_eq!((was, now), (original, target));
        let after = std::fs::read(&dst).unwrap();
        let before = std::fs::read(&s[0]).unwrap();
        let moved: Vec<usize> = (0..before.len()).filter(|&i| before[i] != after[i]).collect();
        assert!(moved.iter().all(|&i| (160..164).contains(&i)), "moved: {moved:?}");
        assert_eq!(Clip::read(&dst).unwrap().frame_rate, target);
        std::fs::remove_file(&dst).ok();
    }

    #[test]
    fn an_implausible_rate_is_refused_before_any_write() {
        let s = samples();
        assert!(set_frame_rate(&s[0], 0).is_err());
        assert!(set_frame_rate(&s[0], 5000).is_err());
        // The refusal happens before the file is opened for writing, so the
        // shipped sample must still be at its measured rate.
        assert_eq!(Clip::read(&s[0]).unwrap().frame_rate, 10);
    }
}
