//! `.bin` reader — the three shapes these files actually come in.
//!
//! A `.bin` in this game means one of three unrelated things, and the path
//! decides which, so the reader classifies before it parses:
//!
//!   WESYS        16-byte header then a plain zlib stream. Everything under
//!                `common/etc/pesdb` and `common/match/constant` is this.
//!   container    asset framing with an embedded name such as `afp_*.apk`.
//!   opaque       high-entropy data with no header anyone here can read. Four
//!                files in this install are this; none of them is a table.
//!
//! Inside a WESYS body there are two further structures, both verified against
//! the shipped files rather than inferred:
//!
//!   match constant   a section table of named `.o` blocks. Header is
//!                    `u32 count, u32 table_offset`, then `count` records of
//!                    `{ u32 data_offset, u32 size, u32 name_offset }`, then a
//!                    NUL-terminated name pool, then the section data laid out
//!                    contiguously. Checked on all nine `constant_*.bin`:
//!                    27/36/10/5/21/84/16/2/2 sections, every one contiguous,
//!                    every name a printable `.o`, and the last section ending
//!                    exactly at the body length.
//!
//!   pesdb table      fixed-width records. The three competition tables are
//!                    decoded into named columns; other tables are reported as
//!                    a record count at their measured stride.
//!
//! Parsing is `nom`, so each structure is one small function rather than index
//! arithmetic scattered across the module.

use std::fs;
use std::io;
use std::path::Path;

use anyhow::{bail, Context, Result};
use nom::{multi::count, number::complete::le_u32, IResult, Parser};
use serde::Serialize;

use crate::structure::{self, Inferred};
use crate::wesys::{self, Kind};

// ---------------------------------------------------------------- sections

#[derive(Debug, Clone, Serialize)]
pub struct Section {
    pub name: String,
    pub offset: u32,
    pub size: u32,
}

#[derive(Debug, Clone, Serialize)]
pub struct SectionTable {
    pub count: u32,
    pub table_offset: u32,
    pub sections: Vec<Section>,
    pub contiguous: bool,
    pub ends_at: usize,
}

fn cstring(body: &[u8], at: usize) -> String {
    if at >= body.len() {
        return String::new();
    }
    let end = body[at..]
        .iter()
        .position(|&c| c == 0)
        .map(|i| at + i)
        .unwrap_or(body.len());
    String::from_utf8_lossy(&body[at..end]).into_owned()
}

/// `u32 count, u32 table_offset`.
fn section_header(input: &[u8]) -> IResult<&[u8], (u32, u32)> {
    (le_u32, le_u32).parse(input)
}

/// One `{ u32 data_offset, u32 size, u32 name_offset }` record.
fn one_section(input: &[u8]) -> IResult<&[u8], (u32, u32, u32)> {
    (le_u32, le_u32, le_u32).parse(input)
}

/// `how_many` section records in a row. nom 8's `count` returns a parser, so
/// it is applied with `.parse`.
fn section_records(input: &[u8], how_many: usize) -> IResult<&[u8], Vec<(u32, u32, u32)>> {
    count(one_section, how_many).parse(input)
}

/// Parse a match-constant section table from an already-inflated body.
pub fn parse_sections(body: &[u8]) -> Option<SectionTable> {
    let (_, (section_count, table)) = section_header(body).ok()?;
    if section_count == 0
        || section_count > 4096
        || table as usize + (section_count as usize) * 12 > body.len()
    {
        return None;
    }
    let (_, raw) = section_records(&body[table as usize..], section_count as usize).ok()?;
    let mut sections = Vec::with_capacity(raw.len());
    for (data, size, name_at) in raw {
        if data as usize + size as usize > body.len() {
            return None;
        }
        let name = cstring(body, name_at as usize);
        if name.is_empty() || !name.is_ascii() || name.len() > 128 {
            return None;
        }
        sections.push(Section {
            name,
            offset: data,
            size,
        });
    }
    let contiguous = sections
        .windows(2)
        .all(|w| w[0].offset as usize + w[0].size as usize == w[1].offset as usize);
    let last = sections.last()?;
    Some(SectionTable {
        count: section_count,
        table_offset: table,
        ends_at: last.offset as usize + last.size as usize,
        contiguous,
        sections,
    })
}

// ---------------------------------------------------------------- pesdb

#[derive(Debug, Clone, Serialize)]
pub struct Column {
    pub name: String,
    pub values: Vec<String>,
}

#[derive(Debug, Clone, Serialize)]
pub struct RecordTable {
    pub stride: u64,
    pub records: usize,
    pub columns: Vec<Column>,
    pub note: String,
}

/// A `le_u32` with the error type pinned, so callers need no annotation.
fn word(input: &[u8]) -> IResult<&[u8], u32> {
    le_u32(input)
}

/// `Competition.bin`, 36 bytes. Verified shape: constant `64 c8 00 08`, then
/// `00 <id> <kind> 00`, then a 28-byte name.
fn competition_table(body: &[u8]) -> Option<RecordTable> {
    if !body.len().is_multiple_of(36) {
        return None;
    }
    let mut ids = Vec::new();
    let mut kinds = Vec::new();
    let mut names = Vec::new();
    let mut flags = Vec::new();
    for r in body.chunks(36) {
        if r[0] != 0x64 || r[1] != 0xc8 {
            return None;
        }
        ids.push(r[5].to_string());
        kinds.push(r[6].to_string());
        names.push(cstring(&r[8..36], 0));
        flags.push(format!("{:02x}", r[3]));
    }
    Some(RecordTable {
        stride: 36,
        records: body.len() / 36,
        columns: vec![
            Column {
                name: "id".into(),
                values: ids,
            },
            Column {
                name: "kind".into(),
                values: kinds,
            },
            Column {
                name: "flag".into(),
                values: flags,
            },
            Column {
                name: "name".into(),
                values: names,
            },
        ],
        note: "record = 64 c8 00 <flag> 00 <id> <kind> 00 + 28-byte name".into(),
    })
}

/// `CompetitionEntry.bin`, 12 bytes: club id, entry id, then a packed
/// `slot * 256 + competition id`.
fn competition_entry_table(body: &[u8]) -> Option<RecordTable> {
    if !body.len().is_multiple_of(12) {
        return None;
    }
    let mut clubs = Vec::new();
    let mut entries = Vec::new();
    let mut comps = Vec::new();
    let mut slots = Vec::new();
    for r in body.chunks(12) {
        let (_, (club, entry, packed)) = one_section(r).ok()?;
        clubs.push(club.to_string());
        entries.push(entry.to_string());
        comps.push((packed % 256).to_string());
        slots.push((packed / 256).to_string());
    }
    Some(RecordTable {
        stride: 12,
        records: body.len() / 12,
        columns: vec![
            Column {
                name: "club".into(),
                values: clubs,
            },
            Column {
                name: "entry".into(),
                values: entries,
            },
            Column {
                name: "competition".into(),
                values: comps,
            },
            Column {
                name: "slot".into(),
                values: slots,
            },
        ],
        note: "third word is slot * 256 + competition id".into(),
    })
}

/// `CompetitionRegulation.bin`, 2352 bytes. Only the header fields and the
/// display name are decoded; the remaining 2.3 KB per record is format data
/// that is not mapped.
fn regulation_table(body: &[u8]) -> Option<RecordTable> {
    if !body.len().is_multiple_of(2352) {
        return None;
    }
    let mut own = Vec::new();
    let mut parent = Vec::new();
    let mut child = Vec::new();
    let mut comps = Vec::new();
    let mut teams = Vec::new();
    let mut names = Vec::new();
    for r in body.chunks(2352) {
        own.push(r[2].to_string());
        parent.push(r[4].to_string());
        child.push(r[0].to_string());
        comps.push(r[8].to_string());
        teams.push(r[11].to_string());
        names.push(cstring(&r[1087..1119], 0));
    }
    Some(RecordTable {
        stride: 2352,
        records: body.len() / 2352,
        columns: vec![
            Column {
                name: "node".into(),
                values: own,
            },
            Column {
                name: "parent".into(),
                values: parent,
            },
            Column {
                name: "child".into(),
                values: child,
            },
            Column {
                name: "competition".into(),
                values: comps,
            },
            Column {
                name: "teams".into(),
                values: teams,
            },
            Column {
                name: "name".into(),
                values: names,
            },
        ],
        note: "bytes 0/2/4/8/11 and the name at +1087 are mapped; \
               the rest of each 2352-byte record is unmapped format data"
            .into(),
    })
}

/// `Team.bin`, 1532 bytes. Verified against the shipped table: the id is a
/// u32 at 0, and the localised name slots sit at 158 / 368 / 508 / 1102 / 1462.
/// 368 is the one always filled, so it is treated as the primary name — record
/// 400 (Coritiba FC) has nothing in the others.
fn team_table(body: &[u8]) -> Option<RecordTable> {
    if !body.len().is_multiple_of(1532) {
        return None;
    }
    let mut ids = Vec::new();
    let mut name = Vec::new();
    let mut alt = Vec::new();
    for r in body.chunks(1532) {
        let (_, id) = word(r).ok()?;
        ids.push(id.to_string());
        name.push(cstring(&r[368..368 + 70], 0));
        alt.push(cstring(&r[1462..1462 + 70], 0));
    }
    Some(RecordTable {
        stride: 1532,
        records: body.len() / 1532,
        columns: vec![
            Column {
                name: "id".into(),
                values: ids,
            },
            Column {
                name: "name".into(),
                values: name,
            },
            Column {
                name: "short".into(),
                values: alt,
            },
        ],
        note: "id at +0; names at +158/+368/+508/+1102/+1462, +368 is the \
               always-filled one. The rest of the record is unmapped."
            .into(),
    })
}

/// `Player.bin`, 312 bytes. u32 id at +8, then four 61-byte name slots at
/// 68 / 129 / 190 / 251 filling the tail exactly: full name, surname in caps,
/// surname again, full name again.
fn player_table(body: &[u8]) -> Option<RecordTable> {
    if !body.len().is_multiple_of(312) {
        return None;
    }
    let mut ids = Vec::new();
    let mut full = Vec::new();
    let mut short = Vec::new();
    for r in body.chunks(312) {
        let (_, id) = word(&r[8..12]).ok()?;
        ids.push(id.to_string());
        full.push(cstring(&r[68..129], 0));
        short.push(cstring(&r[129..190], 0));
    }
    Some(RecordTable {
        stride: 312,
        records: body.len() / 312,
        columns: vec![
            Column {
                name: "id".into(),
                values: ids,
            },
            Column {
                name: "name".into(),
                values: full,
            },
            Column {
                name: "short".into(),
                values: short,
            },
        ],
        note: "id at +8; four 61-byte name slots at +68/+129/+190/+251. \
               Attributes live in the first 68 bytes and are not mapped here."
            .into(),
    })
}

/// Tables with a measured stride but no field map.
fn generic_table(body: &[u8], name: &str) -> Option<RecordTable> {
    let stride: u64 = match name {
        "PlayerAssignment.bin" => 12,
        _ => return None,
    };
    if !(body.len() as u64).is_multiple_of(stride) {
        return None;
    }
    Some(RecordTable {
        stride,
        records: (body.len() as u64 / stride) as usize,
        columns: Vec::new(),
        note: format!("tiles at stride {stride}; no field map is claimed for {name}"),
    })
}

fn records_for(name: &str, body: &[u8]) -> Option<RecordTable> {
    match name {
        "Competition.bin" => competition_table(body),
        "CompetitionEntry.bin" => competition_entry_table(body),
        "CompetitionRegulation.bin" => regulation_table(body),
        "Team.bin" => team_table(body),
        "Player.bin" => player_table(body),
        other => generic_table(body, other),
    }
}

// ---------------------------------------------------------------- report

#[derive(Debug, Clone, Serialize)]
pub struct StringHit {
    pub at: usize,
    pub text: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct BinReport {
    pub path: String,
    pub file_size: u64,
    pub framing: String,
    pub body_size: usize,
    pub re_encode: String,
    pub entropy: f64,
    pub hex_head: String,
    pub menu_layout: Option<MenuLayout>,
    pub sections: Option<SectionTable>,
    pub records: Option<RecordTable>,
    /// Inferred from the data itself: what every byte of the record is,
    /// whether or not a hand-written field map exists for this table.
    pub structure: Option<Inferred>,
    pub strings: Vec<StringHit>,
    pub notes: Vec<String>,
}

#[derive(Debug, Clone, Serialize)]
pub struct MenuLayout {
    pub package_name: String,
    pub txp2_size: usize,
    pub textures: Vec<MenuTexture>,
    pub pictures: Vec<MenuPicture>,
}

#[derive(Debug, Clone, Serialize)]
pub struct MenuTexture {
    pub data_size: u32,
    pub data_offset: u32,
    pub width: u16,
    pub height: u16,
    pub format: u8,
}

#[derive(Debug, Clone, Serialize)]
pub struct MenuPicture {
    pub name: String,
    pub index: u32,
    pub texture: u16,
    pub x0_half: u16,
    pub y0_half: u16,
    pub x1_half: u16,
    pub y1_half: u16,
}

fn le_u32_at(data: &[u8], at: usize) -> Option<u32> {
    Some(u32::from_le_bytes(
        data.get(at..at.checked_add(4)?)?.try_into().ok()?,
    ))
}

fn be_u16_at(data: &[u8], at: usize) -> Option<u16> {
    Some(u16::from_be_bytes(
        data.get(at..at.checked_add(2)?)?.try_into().ok()?,
    ))
}

fn be_u32_at(data: &[u8], at: usize) -> Option<u32> {
    Some(u32::from_be_bytes(
        data.get(at..at.checked_add(4)?)?.try_into().ok()?,
    ))
}

fn latin1_cstring(data: &[u8], at: usize) -> Option<String> {
    let tail = data.get(at..)?;
    let end = tail.iter().position(|&b| b == 0)?;
    Some(tail[..end].iter().map(|&b| char::from(b)).collect())
}

fn nlz_prefix(src: &[u8], needed: usize) -> Result<Vec<u8>> {
    let mut window = [0u8; 4096];
    let mut write_at = 0xfee;
    let mut input_at = 0;
    let mut flags = 0u16;
    let mut out = Vec::with_capacity(needed);
    while out.len() < needed {
        flags >>= 1;
        if flags & 0x100 == 0 {
            let flag = *src.get(input_at).context("truncated NLZ flag byte")?;
            input_at += 1;
            flags = flag as u16 | 0xff00;
        }
        if flags & 1 != 0 {
            let byte = *src.get(input_at).context("truncated NLZ literal")?;
            input_at += 1;
            out.push(byte);
            window[write_at] = byte;
            write_at = (write_at + 1) & 0xfff;
        } else {
            let pair = src
                .get(input_at..input_at.checked_add(2).context("NLZ input range overflows")?)
                .context("truncated NLZ reference")?;
            input_at += 2;
            let offset = pair[0] as usize | ((pair[1] as usize & 0xf0) << 4);
            let count = (pair[1] as usize & 0x0f) + 3;
            for i in 0..count {
                let byte = window[(offset + i) & 0xfff];
                out.push(byte);
                window[write_at] = byte;
                write_at = (write_at + 1) & 0xfff;
                if out.len() == needed {
                    break;
                }
            }
        }
    }
    Ok(out)
}

fn menu_layout(body: &[u8]) -> Result<Option<MenuLayout>> {
    if body.get(..20).is_none() {
        return Ok(None);
    }
    let txp2_at = le_u32_at(body, 8).context("AFP package has no TXP2 offset")? as usize;
    let txp2_size = le_u32_at(body, 12).context("AFP package has no TXP2 size")? as usize;
    let txp2_end = txp2_at
        .checked_add(txp2_size)
        .context("TXP2 range overflows")?;
    let Some(txp2) = body.get(txp2_at..txp2_end) else {
        return Ok(None);
    };
    if txp2.get(..4) != Some(b"TXP2") {
        return Ok(None);
    }
    let package_header = body
        .get(..txp2_at)
        .context("AFP package header is truncated")?;
    let package_name = latin1_cstring(package_header, 20)
        .context("AFP package name is not terminated before TXP2")?;
    anyhow::ensure!(txp2.len() >= 0x30, "TXP2 header is truncated");
    let declared_size = be_u32_at(txp2, 0x0c).context("TXP2 has no declared size")? as usize;
    anyhow::ensure!(
        declared_size >= 0x30 && declared_size <= txp2.len(),
        "TXP2 declared size {declared_size} is outside its package bounds"
    );
    let txp2 = &txp2[..declared_size];

    let texture_count = be_u32_at(txp2, 0x18).context("TXP2 has no texture count")? as usize;
    let texture_table = be_u32_at(txp2, 0x1c).context("TXP2 has no texture table")? as usize;
    let picture_count = be_u32_at(txp2, 0x24).context("TXP2 has no picture count")? as usize;
    let picture_table = be_u32_at(txp2, 0x28).context("TXP2 has no picture table")? as usize;
    let namp = be_u32_at(txp2, 0x2c).context("TXP2 has no NAMP table")? as usize;

    let texture_bytes = texture_count
        .checked_mul(12)
        .context("texture table size overflows")?;
    anyhow::ensure!(
        txp2.get(
            texture_table
                ..texture_table
                    .checked_add(texture_bytes)
                    .context("texture table range overflows")?
        )
        .is_some(),
        "texture table exceeds TXP2 bounds"
    );
    let mut textures = Vec::with_capacity(texture_count);
    for i in 0..texture_count {
        let at = texture_table + i * 12;
        let data_size = be_u32_at(txp2, at + 4).context("truncated texture entry")?;
        let data_offset = be_u32_at(txp2, at + 8).context("truncated texture entry")?;
        let block_at = data_offset as usize;
        let raw_size = be_u32_at(txp2, block_at).context("texture block header is out of bounds")? as usize;
        let packed_size = be_u32_at(txp2, block_at + 4).context("texture block header is truncated")? as usize;
        anyhow::ensure!(raw_size >= 0x18, "texture {i} TXDT header is too small");
        let payload_at = block_at.checked_add(8).context("texture payload offset overflows")?;
        let stored_size = if packed_size == 0 { raw_size } else { packed_size };
        let payload_end = payload_at.checked_add(stored_size).context("texture payload range overflows")?;
        let payload = txp2.get(payload_at..payload_end).context("texture payload exceeds TXP2 bounds")?;
        let header = if packed_size == 0 {
            payload.get(..0x18).context("texture TXDT header is truncated")?.to_vec()
        } else {
            nlz_prefix(payload, 0x18).context("decoding texture TXDT header")?
        };
        textures.push(MenuTexture {
            data_size,
            data_offset,
            width: be_u16_at(&header, 0x10).context("texture width is missing")?,
            height: be_u16_at(&header, 0x12).context("texture height is missing")?,
            format: header[0x17],
        });
    }

    let picture_bytes = picture_count
        .checked_mul(10)
        .context("picture table size overflows")?;
    anyhow::ensure!(
        txp2.get(
            picture_table
                ..picture_table
                    .checked_add(picture_bytes)
                    .context("picture table range overflows")?
        )
        .is_some(),
        "picture table exceeds TXP2 bounds"
    );
    let namp_header = txp2
        .get(
            namp..namp
                .checked_add(0x1c)
                .context("NAMP header range overflows")?,
        )
        .context("NAMP header exceeds TXP2 bounds")?;
    anyhow::ensure!(
        namp_header.get(..4) == Some(b"NAMP"),
        "TXP2 name table is not NAMP"
    );
    let name_count = be_u32_at(txp2, namp + 0x10).context("NAMP has no name count")? as usize;
    let name_table = be_u32_at(txp2, namp + 0x18).context("NAMP has no entry table")? as usize;
    let name_bytes = name_count
        .checked_mul(12)
        .context("NAMP entry table size overflows")?;
    anyhow::ensure!(
        txp2.get(
            name_table
                ..name_table
                    .checked_add(name_bytes)
                    .context("NAMP entry range overflows")?
        )
        .is_some(),
        "NAMP entry table exceeds TXP2 bounds"
    );

    let mut pictures = Vec::with_capacity(name_count);
    for i in 0..name_count {
        let entry = name_table + i * 12;
        let index = be_u32_at(txp2, entry + 4).context("truncated NAMP entry")?;
        let name_at = be_u32_at(txp2, entry + 8).context("truncated NAMP entry")? as usize;
        anyhow::ensure!(
            (index as usize) < picture_count,
            "NAMP picture index {index} is out of range"
        );
        let name = latin1_cstring(txp2, name_at)
            .context("NAMP picture name is not terminated within TXP2")?;
        let rect = picture_table + index as usize * 10;
        let texture = be_u16_at(txp2, rect).context("truncated picture rectangle")?;
        anyhow::ensure!(
            (texture as usize) < texture_count,
            "picture {index} texture index is out of range"
        );
        pictures.push(MenuPicture {
            name,
            index,
            texture,
            x0_half: be_u16_at(txp2, rect + 2).context("truncated picture rectangle")?,
            y0_half: be_u16_at(txp2, rect + 4).context("truncated picture rectangle")?,
            x1_half: be_u16_at(txp2, rect + 6).context("truncated picture rectangle")?,
            y1_half: be_u16_at(txp2, rect + 8).context("truncated picture rectangle")?,
        });
    }

    Ok(Some(MenuLayout {
        package_name,
        txp2_size: declared_size,
        textures,
        pictures,
    }))
}

#[cfg(test)]
mod menu_layout_tests {
    use super::*;

    fn be16(data: &mut [u8], at: usize, value: u16) {
        data[at..at + 2].copy_from_slice(&value.to_be_bytes());
    }

    fn be32(data: &mut [u8], at: usize, value: u32) {
        data[at..at + 4].copy_from_slice(&value.to_be_bytes());
    }

    fn le32(data: &mut [u8], at: usize, value: u32) {
        data[at..at + 4].copy_from_slice(&value.to_le_bytes());
    }

    fn sample_package() -> Vec<u8> {
        let package_at = 64;
        let txp_size = 0xd0;
        let mut body = vec![0; package_at + txp_size];
        le32(&mut body, 8, package_at as u32);
        le32(&mut body, 12, txp_size as u32);
        let name = b"afp_test.apk\0";
        le32(&mut body, 16, name.len() as u32);
        body[20..20 + name.len()].copy_from_slice(name);

        let txp = &mut body[package_at..];
        txp[..4].copy_from_slice(b"TXP2");
        be32(txp, 0x0c, txp_size as u32);
        be32(txp, 0x18, 1);
        be32(txp, 0x1c, 0x40);
        be32(txp, 0x24, 1);
        be32(txp, 0x28, 0x50);
        be32(txp, 0x2c, 0x60);

        be32(txp, 0x44, 0x20);
        be32(txp, 0x48, 0xa0);
        be16(txp, 0x50, 0);
        be16(txp, 0x52, 2);
        be16(txp, 0x54, 4);
        be16(txp, 0x56, 102);
        be16(txp, 0x58, 204);

        txp[0x60..0x64].copy_from_slice(b"NAMP");
        be32(txp, 0x70, 1);
        be32(txp, 0x78, 0x80);
        be32(txp, 0x84, 0);
        be32(txp, 0x88, 0x90);
        txp[0x90..0x9c].copy_from_slice(b"button_play\0");
        be32(txp, 0xa0, 0x18);
        be32(txp, 0xa4, 0);
        be16(txp, 0xb8, 1024);
        be16(txp, 0xba, 512);
        txp[0xbf] = 0x15;
        body
    }

    #[test]
    fn decodes_named_picture_atlas_rectangles() {
        let decoded = menu_layout(&sample_package()).unwrap().unwrap();
        assert_eq!(decoded.package_name, "afp_test.apk");
        assert_eq!(decoded.txp2_size, 0xd0);
        assert_eq!(decoded.textures.len(), 1);
        assert_eq!(decoded.textures[0].data_size, 0x20);
        assert_eq!(decoded.textures[0].data_offset, 0xa0);
        assert_eq!((decoded.textures[0].width, decoded.textures[0].height), (1024, 512));
        assert_eq!(decoded.textures[0].format, 0x15);
        assert_eq!(decoded.pictures.len(), 1);
        assert_eq!(decoded.pictures[0].name, "button_play");
        assert_eq!(decoded.pictures[0].index, 0);
        assert_eq!(decoded.pictures[0].texture, 0);
        assert_eq!(
            (
                decoded.pictures[0].x0_half,
                decoded.pictures[0].y0_half,
                decoded.pictures[0].x1_half,
                decoded.pictures[0].y1_half,
            ),
            (2, 4, 102, 204)
        );
    }

    #[test]
    fn rejects_picture_indices_outside_the_picture_table() {
        let mut body = sample_package();
        be32(&mut body, 64 + 0x84, 1);
        assert!(menu_layout(&body).is_err());
    }

    #[test]
    fn ignores_non_afp_wesys_bodies() {
        assert!(menu_layout(b"not an AFP package").unwrap().is_none());
    }

    #[test]
    fn nlz_reads_a_texture_header_from_literal_runs() {
        let mut packed = Vec::new();
        for bytes in (0u8..24).collect::<Vec<_>>().chunks(8) {
            packed.push(0xff);
            packed.extend_from_slice(bytes);
        }
        assert_eq!(nlz_prefix(&packed, 24).unwrap(), (0u8..24).collect::<Vec<_>>());
    }
}

/// Shannon entropy in bits per byte, over at most 1 MiB.
pub fn entropy(data: &[u8]) -> f64 {
    let sample = &data[..data.len().min(1 << 20)];
    if sample.is_empty() {
        return 0.0;
    }
    let mut counts = [0usize; 256];
    for &b in sample {
        counts[b as usize] += 1;
    }
    let n = sample.len() as f64;
    -counts
        .iter()
        .filter(|&&c| c > 0)
        .map(|&c| {
            let p = c as f64 / n;
            p * p.log2()
        })
        .sum::<f64>()
}

/// Printable runs of at least `min` bytes, capped so a huge file stays readable.
pub fn ascii_runs(data: &[u8], min: usize, cap: usize) -> Vec<StringHit> {
    let mut out = Vec::new();
    let mut start = 0usize;
    let mut current = Vec::new();
    for (i, &b) in data.iter().enumerate() {
        if (32..127).contains(&b) {
            if current.is_empty() {
                start = i;
            }
            current.push(b);
        } else {
            if current.len() >= min {
                out.push(StringHit {
                    at: start,
                    text: String::from_utf8_lossy(&current).into_owned(),
                });
                if out.len() >= cap {
                    return out;
                }
            }
            current.clear();
        }
    }
    if current.len() >= min && out.len() < cap {
        out.push(StringHit {
            at: start,
            text: String::from_utf8_lossy(&current).into_owned(),
        });
    }
    out
}

pub fn hexdump(data: &[u8], at: usize, len: usize) -> String {
    let mut out = String::new();
    let end = (at + len).min(data.len());
    let mut i = at;
    while i < end {
        out.push_str(&format!("{i:08x}  "));
        for c in 0..16 {
            if i + c < end {
                out.push_str(&format!("{:02x} ", data[i + c]));
            } else {
                out.push_str("   ");
            }
        }
        out.push('|');
        for c in 0..16 {
            match data.get(i + c) {
                Some(&b) if (32..127).contains(&b) => out.push(b as char),
                Some(_) => out.push('.'),
                None => out.push(' '),
            }
        }
        out.push_str("|\n");
        i += 16;
    }
    out
}

pub fn read(path: &Path) -> Result<BinReport> {
    let raw = fs::read(path).with_context(|| format!("reading {}", path.display()))?;
    let name = path
        .file_name()
        .unwrap_or_default()
        .to_string_lossy()
        .to_string();
    let mut file = wesys::decode(&raw)?;
    let re_encode = match wesys::encode(&mut file) {
        Ok(_) if file.exact => "byte-exact".to_string(),
        Ok(_) => format!(
            "same table, re-deflated at level {}",
            file.level.unwrap_or(0)
        ),
        Err(e) => format!("refused: {e}"),
    };
    let body = file.body.clone();

    let mut notes = Vec::new();
    let menu_layout = if file.kind == Kind::Wesys {
        match menu_layout(&body) {
            Ok(layout) => layout,
            Err(error) => {
                notes.push(format!(
                    "compiled menu layout could not be decoded: {error:#}"
                ));
                None
            }
        }
    } else {
        None
    };
    let sections = if file.kind == Kind::Wesys && name.starts_with("constant") {
        match parse_sections(&body) {
            Some(t) => Some(t),
            None => {
                notes.push("name suggests a match constant but no section table parsed".into());
                None
            }
        }
    } else {
        None
    };
    if let Some(t) = &sections {
        if !t.contiguous {
            notes.push("sections are not laid out contiguously".into());
        }
        if t.ends_at != body.len() {
            notes.push(format!(
                "{} trailing bytes after the last section",
                body.len() - t.ends_at
            ));
        }
    }

    let has_known_layout = sections.is_some() || menu_layout.is_some();
    let records = if file.kind == Kind::Wesys && !has_known_layout {
        records_for(&name, &body)
    } else {
        None
    };
    if file.kind == Kind::Unknown {
        notes.push(
            "no framing this codec can read; the stride of a table cannot be \
             checked against ciphertext"
                .into(),
        );
    }

    Ok(BinReport {
        path: path.to_string_lossy().into_owned(),
        file_size: raw.len() as u64,
        framing: file.kind.name().to_string(),
        body_size: body.len(),
        re_encode,
        entropy: entropy(&raw),
        hex_head: hexdump(&raw, 0, 256),
        menu_layout,
        sections,
        records,
        structure: infer_structure(&name, &body, has_known_layout),
        strings: ascii_runs(&body, 5, 200),
        notes,
    })
}

/// Infer a record layout where the table is fixed-stride. Match constants are
/// excluded: their structure is the section table, already reported.
fn infer_structure(name: &str, body: &[u8], has_known_layout: bool) -> Option<Inferred> {
    if has_known_layout || body.is_empty() {
        return None;
    }
    let stride = crate::pesdb::stride_for(name).unwrap_or(0) as usize;
    if stride >= 8 && body.len().is_multiple_of(stride) {
        return structure::infer(body, stride);
    }
    // No published stride. First ask the data: named tables space their text
    // runs by the record length, which is far better evidence than any
    // divisor we could try. A stride that divides the file is not evidence
    // that it *is* the stride — 28 divides Stadium.bin and tiles it perfectly,
    // because most of a 392-byte record is padding — so the name spacing
    // decides, and the alternatives below are only tried when it says nothing.
    if let Some(gap) = structure::stride_from_names(body) {
        if let Some(got) = structure::infer(body, gap) {
            // Only take the evidence-derived stride if it explains something;
            // otherwise fall through and try the alternatives.
            if got.coverage >= 0.25 {
                return Some(got);
            }
        }
    }
    let mut best: Option<Inferred> = None;
    for candidate in [
        8usize, 12, 16, 20, 24, 28, 32, 36, 40, 48, 60, 64, 100, 128, 150, 200, 256,
    ] {
        if !body.len().is_multiple_of(candidate) || body.len() / candidate < 4 {
            continue;
        }
        if let Some(got) = structure::infer(body, candidate) {
            if got.coverage < 0.25 {
                continue;
            }
            if best
                .as_ref()
                .is_none_or(|b| got.mapped_bytes > b.mapped_bytes)
            {
                best = Some(got);
            }
        }
    }
    best
}

/// One section's bytes, for the hex view.
pub fn section_bytes(path: &Path, index: usize) -> Result<Vec<u8>> {
    let raw = fs::read(path)?;
    let file = wesys::decode(&raw)?;
    let table =
        parse_sections(&file.body).context("this file has no match-constant section table")?;
    let s = table.sections.get(index).context("no such section")?;
    let start = s.offset as usize;
    let end = (start + s.size as usize).min(file.body.len());
    Ok(file.body[start..end].to_vec())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    fn constant_dir() -> Option<PathBuf> {
        let p = Path::new(crate::install::GAME_ROOT)
            .join("FL27 Megapatch/out/rt/a/common/match/constant");
        p.is_dir().then_some(p)
    }

    #[test]
    fn entropy_separates_text_from_cipher() {
        assert!(entropy(&vec![b'A'; 4096]) < 0.01);
        let pseudo: Vec<u8> = (0..4096).map(|i| (i * 137 + 11) as u8).collect();
        assert!(entropy(&pseudo) > 7.0);
    }

    #[test]
    fn ascii_runs_find_names_and_respect_the_minimum() {
        let mut data = vec![0u8; 8];
        data.extend_from_slice(b"cpuLevel.o");
        data.push(0);
        data.extend_from_slice(b"ab");
        let hits = ascii_runs(&data, 5, 10);
        assert_eq!(hits.len(), 1);
        assert_eq!(hits[0].text, "cpuLevel.o");
        assert_eq!(hits[0].at, 8);
    }

    #[test]
    fn hexdump_is_addressable() {
        let data: Vec<u8> = (0..48).collect();
        let text = hexdump(&data, 0, 48);
        let lines: Vec<&str> = text.trim().lines().collect();
        assert_eq!(lines.len(), 3);
        assert!(lines[0].starts_with("00000000  00 01 02"));
        assert!(lines[2].starts_with("00000020"));
    }

    #[test]
    fn all_nine_constants_parse_contiguously() {
        let Some(dir) = constant_dir() else { return };
        let mut files = 0;
        for entry in std::fs::read_dir(&dir).unwrap().flatten() {
            let p = entry.path();
            if p.extension().map(|e| e != "bin").unwrap_or(true) {
                continue;
            }
            let report = read(&p).unwrap();
            assert_eq!(report.framing, "wesys", "{}", p.display());
            let t = report
                .sections
                .unwrap_or_else(|| panic!("{} has no section table", p.display()));
            assert!(t.contiguous, "{} sections are not contiguous", p.display());
            assert_eq!(
                t.ends_at,
                report.body_size,
                "{} trailing bytes",
                p.display()
            );
            assert!(t.sections.iter().all(|s| s.name.ends_with(".o")));
            assert!(t.count >= 2);
            files += 1;
        }
        assert_eq!(files, 9, "expected the nine shipped constants");
    }

    #[test]
    fn cpu_level_section_is_named_in_constant_match() {
        let Some(dir) = constant_dir() else { return };
        let p = dir.join("constant_match.bin");
        let report = read(&p).unwrap();
        let t = report.sections.unwrap();
        assert_eq!(t.count, 27);
        assert!(t.sections.iter().any(|s| s.name == "cpuLevel.o"));
        assert!(t.sections.iter().any(|s| s.name == "ball.o"));
        let bytes = section_bytes(&p, 8).unwrap();
        assert_eq!(bytes.len(), t.sections[8].size as usize);
    }

    #[test]
    fn competition_records_decode_to_named_columns() {
        let p = Path::new(crate::install::GAME_ROOT)
            .join("SiderAddons/livecpk/DR_LeagueCreator/common/etc/pesdb/Competition.bin");
        if !p.exists() {
            return;
        }
        let report = read(&p).unwrap();
        let r = report.records.expect("Competition.bin should decode");
        assert_eq!(r.stride, 36);
        assert_eq!(r.records, 92);
        let names = &r.columns.iter().find(|c| c.name == "name").unwrap().values;
        assert_eq!(names[1], "UEFA_CHAMPIONS_LEAGUE");
        assert_eq!(
            r.columns.iter().find(|c| c.name == "id").unwrap().values[1],
            "2"
        );
    }

    #[test]
    fn entry_records_split_the_packed_third_word() {
        let p = Path::new(crate::install::GAME_ROOT)
            .join("SiderAddons/livecpk/DR_LeagueCreator/common/etc/pesdb/CompetitionEntry.bin");
        if !p.exists() {
            return;
        }
        let r = read(&p).unwrap().records.expect("entry table");
        assert_eq!(r.records, 1359);
        // first row is (243, 3573, 269): slot 1, competition 13
        assert_eq!(r.columns[0].values[0], "243");
        assert_eq!(r.columns[2].values[0], "13");
        assert_eq!(r.columns[3].values[0], "1");
    }

    #[test]
    fn regulation_records_map_only_what_is_verified() {
        let p = Path::new(crate::install::GAME_ROOT)
            .join("SiderAddons/livecpk/DR_LeagueCreator/common/etc/pesdb/CompetitionRegulation.bin");
        if !p.exists() {
            return;
        }
        let r = read(&p).unwrap().records.expect("regulation table");
        assert_eq!(r.records, 197);
        assert_eq!(
            r.columns.iter().find(|c| c.name == "name").unwrap().values[1],
            "UEFA Champions League"
        );
        assert_eq!(
            r.columns.iter().find(|c| c.name == "teams").unwrap().values[1],
            "16"
        );
        assert!(
            r.note.contains("unmapped"),
            "the gap must be stated: {}",
            r.note
        );
    }

    #[test]
    fn player_records_decode_id_and_names() {
        let p = Path::new(crate::install::GAME_ROOT)
            .join("SiderAddons/livecpk/DR_LeagueCreator/common/etc/pesdb/Player.bin");
        if !p.exists() {
            return;
        }
        let r = read(&p).unwrap().records.expect("player table");
        assert_eq!(r.stride, 312);
        assert_eq!(r.records, 26710);
        assert_eq!(
            r.columns.iter().find(|c| c.name == "id").unwrap().values[0],
            "91"
        );
        assert_eq!(
            r.columns.iter().find(|c| c.name == "name").unwrap().values[0],
            "Hong Myung-Bo"
        );
        assert_eq!(
            r.columns.iter().find(|c| c.name == "short").unwrap().values[0],
            "HONG MYUNG BO"
        );
        // A late record must still line up, or the stride is wrong.
        assert_eq!(
            r.columns.iter().find(|c| c.name == "name").unwrap().values[10000],
            "Yann Gboho"
        );
        assert!(
            r.note.contains("not mapped"),
            "the attribute gap must be stated"
        );
    }

    #[test]
    fn team_records_decode_id_and_the_always_filled_name() {
        let p = Path::new(crate::install::GAME_ROOT)
            .join("SiderAddons/livecpk/DR_LeagueCreator/common/etc/pesdb/Team.bin");
        if !p.exists() {
            return;
        }
        let r = read(&p).unwrap().records.expect("team table");
        assert_eq!(r.stride, 1532);
        assert_eq!(r.records, 763);
        let name = &r.columns.iter().find(|c| c.name == "name").unwrap().values;
        assert_eq!(name[0], "Ireland");
        assert_eq!(name[2], "Scotland");
        assert_eq!(name[400], "Coritiba FC");
        assert_eq!(
            r.columns.iter().find(|c| c.name == "id").unwrap().values[0],
            "35452"
        );
    }

    #[test]
    fn opaque_files_are_reported_without_a_stride_claim() {
        let p = Path::new(crate::install::GAME_ROOT)
            .join("SiderAddons/livecpk/root/common/etc/pesdb/Competition.bin");
        if !p.exists() {
            return;
        }
        let report = read(&p).unwrap();
        assert_eq!(report.framing, "unknown");
        assert!(
            report.records.is_none(),
            "no record count may be claimed over ciphertext"
        );
        assert!(report.entropy > 7.0);
        assert!(report.notes.iter().any(|n| n.contains("cannot be checked")));
    }

    #[test]
    fn stadium_stride_is_the_record_and_not_one_of_its_divisors() {
        // 22736 is divisible by 8, 14, 16, 28, 56, 98, 112, 196 and 392, and
        // the padding inside a record repeats every 28 bytes, so every
        // self-agreement test prefers 28 and reports half the record as
        // unexplained. The names are the evidence: they sit at +8, +189 and
        // +370, and the same slot is exactly 392 bytes from the next one.
        let p = Path::new(crate::install::GAME_ROOT)
            .join("SiderAddons/livecpk/root/Stadiums Extra DB/common/etc/pesdb/Stadium.bin");
        if !p.exists() {
            return;
        }
        let got = read(&p).unwrap();
        let s = got.structure.expect("Stadium.bin is a named table");
        assert_eq!(
            s.stride, 392,
            "found {} over {} records",
            s.stride, s.records
        );
        assert_eq!(s.records, 58);
        // And the Japanese names are UTF-8: an ASCII-only test cannot see them
        // at all, which is what left two thirds of the record looking unmapped.
        assert!(
            s.fields
                .iter()
                .any(|f| f.kind == structure::FieldKind::Text
                    && f.sample.chars().any(|c| !c.is_ascii())),
            "no UTF-8 name field among {:?}",
            s.fields
                .iter()
                .map(|f| (f.offset, f.width))
                .collect::<Vec<_>>()
        );
    }
}
/// Write `bytes` over the body at `offset`, leaving every other byte alone.
///
/// Editing goes through the decoded body rather than the file, so a compressed
/// table is inflated, patched and re-framed, and the caller never has to know
/// which framing it is holding. The re-read check is not decoration: it is what
/// turns "we wrote something" into "exactly these bytes changed and nothing
/// else did", which is the only property that makes editing a shipped table
/// safe.
pub fn patch(path: &Path, offset: usize, bytes: &[u8]) -> Result<(usize, usize)> {
    let raw = fs::read(path).with_context(|| format!("reading {}", path.display()))?;
    let mut file = wesys::decode(&raw)?;
    let end = offset
        .checked_add(bytes.len())
        .context("patch range overflows")?;
    if offset > file.body.len() || end > file.body.len() {
        bail!(
            "patch at {offset}..{end} falls outside the decoded table ({})",
            file.body.len()
        );
    }
    let before = file.body.clone();
    file.body[offset..end].copy_from_slice(bytes);
    let out = wesys::encode(&mut file)?;
    // Temporary name then rename, so an interrupted write cannot leave a
    // half-written table where a whole one used to be.
    let tmp = path.with_extension(format!(
        "{}.fl27mm-tmp",
        path.extension().and_then(|e| e.to_str()).unwrap_or("tmp")
    ));
    {
        let mut f =
            fs::File::create(&tmp).with_context(|| format!("creating {}", tmp.display()))?;
        io::Write::write_all(&mut f, &out).with_context(|| format!("writing {}", tmp.display()))?;
    }
    fs::rename(&tmp, path).with_context(|| format!("saving {}", path.display()))?;

    // Re-read what was just written and diff it against the original body.
    let reread = fs::read(path).with_context(|| format!("re-reading {}", path.display()))?;
    let after = wesys::decode(&reread)?.body;
    if after.len() != before.len() {
        bail!(
            "round trip changed the table length ({} -> {} bytes)",
            before.len(),
            after.len()
        );
    }
    let mut first = None;
    let mut last = None;
    let mut count = 0usize;
    for i in 0..before.len() {
        if before[i] != after[i] {
            count += 1;
            first = Some(first.unwrap_or(i));
            last = Some(i);
        }
    }
    if let (Some(f), Some(l)) = (first, last) {
        if !(offset <= f && l < end) {
            bail!(
                "editing {offset}..{end} also changed bytes {f}..{l} — the framing is not stable for this file"
            );
        }
    }
    Ok((count, after.len()))
}

#[cfg(test)]
mod patch_tests {
    use super::*;
    use std::path::PathBuf;

    /// The first loose table this install carries that the codec accepts.
    fn a_real_table() -> Option<PathBuf> {
        let root = Path::new(crate::install::GAME_ROOT).join("SiderAddons");
        if !root.is_dir() {
            return None;
        }
        for p in crate::fsutil::files(&root)
            .into_iter()
            .filter(|p| p.extension().is_some_and(|e| e == "bin"))
        {
            let Ok(raw) = std::fs::read(&p) else { continue };
            if raw.len() < 64 || raw.len() > 4_000_000 {
                continue;
            }
            // Decoding is not enough: an unidentified framing reads fine and
            // then refuses to be re-emitted, which is exactly the file this
            // editor must not offer to save.
            let Ok(mut f) = wesys::decode(&raw) else {
                continue;
            };
            if f.kind == wesys::Kind::Unknown || wesys::encode(&mut f).is_err() {
                continue;
            }
            if p.to_string_lossy().to_lowercase().contains("_internal") {
                continue;
            }
            return Some(p);
        }
        None
    }

    /// Editing must touch the requested window and nothing else. That is the
    /// whole safety argument for letting a shipped table be edited in place.
    #[test]
    fn a_patch_changes_only_the_requested_window() {
        let Some(src) = a_real_table() else { return };
        let raw = std::fs::read(&src).unwrap();
        let mut work = std::env::temp_dir();
        work.push(format!("fl27mm-patch-{}.bin", std::process::id()));
        std::fs::write(&work, &raw).unwrap();

        let body = wesys::decode(&raw).unwrap().body;
        let at = body.len() / 2;
        let before = body[at];
        let after_value = before.wrapping_add(1);
        let (count, len) = patch(&work, at, &[after_value]).expect("patch should apply");
        assert_eq!(count, 1, "exactly one byte should differ, saw {count}");
        assert_eq!(len, body.len(), "the table length must not move");

        let reread = wesys::decode(&std::fs::read(&work).unwrap()).unwrap().body;
        assert_eq!(reread[at], after_value, "the edit did not land");
        assert_eq!(reread[..at], body[..at], "bytes before the window moved");
        assert_eq!(
            reread[at + 1..],
            body[at + 1..],
            "bytes after the window moved"
        );
        let _ = std::fs::remove_file(&work);
    }

    /// A patch beyond the table must be refused, not silently truncated or
    /// extended.
    #[test]
    fn a_patch_beyond_the_table_is_refused() {
        let Some(src) = a_real_table() else { return };
        let raw = std::fs::read(&src).unwrap();
        let n = wesys::decode(&raw).unwrap().body.len();
        let mut work = std::env::temp_dir();
        work.push(format!("fl27mm-patch-oob-{}.bin", std::process::id()));
        std::fs::write(&work, &raw).unwrap();
        let err = patch(&work, n - 1, &[0, 0]).unwrap_err();
        assert!(err.to_string().contains("outside"), "{err}");
        // The refusal must not have written anything.
        assert_eq!(
            std::fs::read(&work).unwrap(),
            raw,
            "a refused patch touched the file"
        );
        let _ = std::fs::remove_file(&work);
    }
}
