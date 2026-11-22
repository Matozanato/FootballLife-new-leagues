//! CRI @UTF tables — the container every CPK header and TOC is made of.
//!
//! Layout (everything after the 8-byte table header is BIG endian):
//!
//!   "@UTF" + u32 table_size          table_size counts from just after this
//!   table info, 24 bytes             offsets below are relative to that point
//!     u32 rows_offset
//!     u32 strings_offset
//!     u32 data_offset                end of the table
//!     u32 table_name_ptr
//!     u16 num_columns
//!     u16 row_length
//!     u32 num_rows
//!   column schema, 5 bytes each      u8 flags, u32 name pointer
//!     a 0x30 storage flag is followed immediately by the constant value
//!     a 0x10 storage flag stores nothing at all
//!   row data, num_rows * row_length
//!   string pool, NUL-terminated
//!
//! Tables travel inside a 16-byte LITTLE endian packet: magic ("CPK ", "TOC "),
//! 0xFF, three zero bytes, u32 payload size (= table_size + 8), u32 zero.

use std::collections::HashMap;

use anyhow::{bail, Result};

pub const MAGIC: &[u8; 4] = b"@UTF";

pub fn be_u32(b: &[u8], at: usize) -> u32 {
    u32::from_be_bytes([b[at], b[at + 1], b[at + 2], b[at + 3]])
}
pub fn be_u16(b: &[u8], at: usize) -> u16 {
    u16::from_be_bytes([b[at], b[at + 1]])
}

/// Bytes a value of this type occupies in row/constant storage.
pub fn type_width(kind: u8) -> usize {
    match kind & 0x0F {
        0x00 | 0x01 => 1,
        0x02 | 0x03 => 2,
        0x04 | 0x05 | 0x08 | 0x0A => 4,
        0x06 | 0x07 => 8,
        0x0B => 8, // data pointer + length
        _ => 0,
    }
}

/// How a column stores its data: 0x10 nothing, 0x30 constant, 0x50 per row.
pub fn storage(flags: u8) -> u8 {
    flags & 0xF0
}

// Column flags used by the CPK header and TOC, named so the writer reads like
// the schema dumps rather than like hex.
pub const ZERO: u8 = 0x10;
pub const ROW_U8: u8 = 0x50;
pub const ROW_U16: u8 = 0x52;
pub const ROW_U32: u8 = 0x54;
pub const ROW_U64: u8 = 0x56;
pub const ROW_STR: u8 = 0x5A;

#[derive(Debug, Clone, PartialEq)]
pub enum Value {
    Int(u64),
    Str(String),
    Zero,
}

impl Value {
    pub fn as_u64(&self) -> u64 {
        match self {
            Value::Int(v) => *v,
            _ => 0,
        }
    }
    pub fn as_str(&self) -> &str {
        match self {
            Value::Str(s) => s,
            _ => "",
        }
    }
}

impl From<u64> for Value {
    fn from(v: u64) -> Self {
        Value::Int(v)
    }
}
impl From<u32> for Value {
    fn from(v: u32) -> Self {
        Value::Int(v as u64)
    }
}
impl From<usize> for Value {
    fn from(v: usize) -> Self {
        Value::Int(v as u64)
    }
}
impl From<&str> for Value {
    fn from(v: &str) -> Self {
        Value::Str(v.to_string())
    }
}
impl From<String> for Value {
    fn from(v: String) -> Self {
        Value::Str(v)
    }
}

pub type Row = HashMap<String, Value>;

#[derive(Debug, Clone)]
pub struct Column {
    pub name: String,
    pub flags: u8,
    pub constant: Option<Value>,
}

pub struct Utf {
    pub name: String,
    pub columns: Vec<Column>,
    pub rows: Vec<Row>,
}

fn read_string(buf: &[u8], strings: usize, off: u32) -> String {
    let s = strings + off as usize;
    if s >= buf.len() {
        return String::new();
    }
    let e = buf[s..]
        .iter()
        .position(|&c| c == 0)
        .map(|i| s + i)
        .unwrap_or(buf.len());
    String::from_utf8_lossy(&buf[s..e]).into_owned()
}

fn read_value(buf: &[u8], p: usize, kind: u8, strings: usize) -> Value {
    let w = type_width(kind);
    if p + w > buf.len() {
        return Value::Zero;
    }
    let raw = &buf[p..p + w];
    match kind & 0x0F {
        0x0A => Value::Str(read_string(
            buf,
            strings,
            u32::from_be_bytes([raw[0], raw[1], raw[2], raw[3]]),
        )),
        0x08 => {
            let bits = u32::from_be_bytes([raw[0], raw[1], raw[2], raw[3]]);
            Value::Int(f32::from_bits(bits) as u64)
        }
        _ => {
            let mut v: u64 = 0;
            for &b in raw {
                v = (v << 8) | b as u64;
            }
            Value::Int(v)
        }
    }
}

impl Utf {
    /// Parse the `@UTF` table whose magic sits at `at`.
    pub fn parse(buf: &[u8], at: usize) -> Result<Utf> {
        if at + 32 > buf.len() || &buf[at..at + 4] != MAGIC {
            bail!("no @UTF table at {at}");
        }
        let base = at + 8; // table-info offsets are relative to here
        let rows_offset = be_u32(buf, at + 8) as usize;
        let strings = base + be_u32(buf, at + 12) as usize;
        let name_ptr = be_u32(buf, at + 20);
        let num_columns = be_u16(buf, at + 24) as usize;
        let row_length = be_u16(buf, at + 26) as usize;
        let num_rows = be_u32(buf, at + 28) as usize;
        if strings > buf.len() {
            bail!("UTF string table out of range");
        }
        let name = read_string(buf, strings, name_ptr);

        let mut p = at + 32;
        let mut columns = Vec::with_capacity(num_columns);
        for _ in 0..num_columns {
            if p + 5 > buf.len() {
                bail!("column schema truncated");
            }
            let flags = buf[p];
            let name_off = be_u32(buf, p + 1);
            p += 5;
            let cname = read_string(buf, strings, name_off);
            let constant = if storage(flags) == 0x30 {
                let v = read_value(buf, p, flags, strings);
                p += type_width(flags);
                Some(v)
            } else {
                None
            };
            columns.push(Column {
                name: cname,
                flags,
                constant,
            });
        }

        let mut rows = Vec::with_capacity(num_rows);
        for i in 0..num_rows {
            let mut rp = base + rows_offset + i * row_length;
            let mut row = Row::new();
            for col in &columns {
                let value = match storage(col.flags) {
                    0x10 => Value::Zero,
                    0x30 => col.constant.clone().unwrap_or(Value::Zero),
                    _ => {
                        let v = read_value(buf, rp, col.flags, strings);
                        rp += type_width(col.flags);
                        v
                    }
                };
                row.insert(col.name.clone(), value);
            }
            rows.push(row);
        }
        Ok(Utf {
            name,
            columns,
            rows,
        })
    }
}

/// A string pool that hands out stable offsets, deduplicating repeats.
#[derive(Default)]
struct Strings {
    buf: Vec<u8>,
    seen: HashMap<String, u32>,
}

impl Strings {
    fn push(&mut self, s: &str) -> u32 {
        if let Some(&off) = self.seen.get(s) {
            return off;
        }
        let off = self.buf.len() as u32;
        self.buf.extend_from_slice(s.as_bytes());
        self.buf.push(0);
        self.seen.insert(s.to_string(), off);
        off
    }
}

fn write_value(out: &mut Vec<u8>, flags: u8, value: &Value, strings: &mut Strings) {
    let width = type_width(flags);
    match flags & 0x0F {
        0x0A => {
            let off = strings.push(value.as_str());
            out.extend_from_slice(&off.to_be_bytes());
        }
        0x08 => {
            let f = value.as_u64() as f32;
            out.extend_from_slice(&f.to_bits().to_be_bytes());
        }
        _ => {
            let v = value.as_u64();
            // Big endian, right-aligned in the column's width.
            let full = v.to_be_bytes();
            out.extend_from_slice(&full[8 - width..]);
        }
    }
}

/// A table under construction. Column order is the on-disk order.
pub struct Builder {
    pub name: String,
    pub columns: Vec<Column>,
    pub rows: Vec<Row>,
}

impl Builder {
    pub fn new(name: &str) -> Builder {
        Builder {
            name: name.to_string(),
            columns: Vec::new(),
            rows: Vec::new(),
        }
    }

    /// A column whose value is stored once per row.
    pub fn col(mut self, name: &str, flags: u8) -> Self {
        self.columns.push(Column {
            name: name.to_string(),
            flags,
            constant: None,
        });
        self
    }

    /// A column that stores nothing; readers see zero.
    pub fn zero(self, name: &str) -> Self {
        self.col(name, ZERO)
    }

    /// A column with one value shared by every row.
    pub fn constant(mut self, name: &str, flags: u8, value: Value) -> Self {
        self.columns.push(Column {
            name: name.to_string(),
            flags: (flags & 0x0F) | 0x30,
            constant: Some(value),
        });
        self
    }

    pub fn row(mut self, row: Row) -> Self {
        self.rows.push(row);
        self
    }

    fn row_length(&self) -> usize {
        self.columns
            .iter()
            .filter(|c| storage(c.flags) == 0x50)
            .map(|c| type_width(c.flags))
            .sum()
    }

    /// Serialise to `@UTF` bytes, without the surrounding packet header.
    pub fn encode(&self) -> Result<Vec<u8>> {
        let row_length = self.row_length();
        if row_length > u16::MAX as usize {
            bail!("row length {row_length} exceeds the u16 field");
        }
        if self.columns.len() > u16::MAX as usize {
            bail!("too many columns");
        }

        // The string pool is filled while the schema and rows are written, so
        // its final length is only known afterwards; patch the offsets last.
        let mut strings = Strings::default();
        let name_ptr = strings.push(&self.name);

        let mut schema = Vec::new();
        for col in &self.columns {
            let ptr = strings.push(&col.name);
            schema.push(col.flags);
            schema.extend_from_slice(&ptr.to_be_bytes());
            if storage(col.flags) == 0x30 {
                write_value(
                    &mut schema,
                    col.flags,
                    col.constant.as_ref().unwrap_or(&Value::Zero),
                    &mut strings,
                );
            }
        }

        let mut rows = Vec::with_capacity(row_length * self.rows.len());
        for row in &self.rows {
            for col in &self.columns {
                if storage(col.flags) != 0x50 {
                    continue;
                }
                let v = row.get(&col.name).cloned().unwrap_or(Value::Zero);
                write_value(&mut rows, col.flags, &v, &mut strings);
            }
        }

        let rows_offset = 24 + schema.len();
        let strings_offset = rows_offset + rows.len();
        let data_offset = strings_offset + strings.buf.len();

        let mut out = Vec::with_capacity(8 + data_offset);
        out.extend_from_slice(MAGIC);
        out.extend_from_slice(&(data_offset as u32).to_be_bytes());
        out.extend_from_slice(&(rows_offset as u32).to_be_bytes());
        out.extend_from_slice(&(strings_offset as u32).to_be_bytes());
        out.extend_from_slice(&(data_offset as u32).to_be_bytes());
        out.extend_from_slice(&name_ptr.to_be_bytes());
        out.extend_from_slice(&(self.columns.len() as u16).to_be_bytes());
        out.extend_from_slice(&(row_length as u16).to_be_bytes());
        out.extend_from_slice(&(self.rows.len() as u32).to_be_bytes());
        out.extend_from_slice(&schema);
        out.extend_from_slice(&rows);
        out.extend_from_slice(&strings.buf);
        Ok(out)
    }
}

/// Wrap a table in its 16-byte little-endian packet header.
pub fn packet(magic: &[u8; 4], table: &[u8]) -> Vec<u8> {
    let mut out = Vec::with_capacity(16 + table.len());
    out.extend_from_slice(magic);
    out.push(0xFF);
    out.extend_from_slice(&[0, 0, 0]);
    out.extend_from_slice(&(table.len() as u32).to_le_bytes());
    out.extend_from_slice(&0u32.to_le_bytes());
    out.extend_from_slice(table);
    out
}

/// Convenience: build a one-row table from ordered (name, value) pairs.
pub fn row(pairs: &[(&str, Value)]) -> Row {
    pairs
        .iter()
        .map(|(k, v)| (k.to_string(), v.clone()))
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample() -> Builder {
        Builder::new("CpkHeader")
            .col("ContentOffset", ROW_U64)
            .col("Files", ROW_U32)
            .col("Align", ROW_U16)
            .col("Tvers", ROW_STR)
            .zero("TocCrc")
            .constant("Version", ROW_U16, Value::Int(7))
            .row(row(&[
                ("ContentOffset", Value::Int(2048)),
                ("Files", Value::Int(10)),
                ("Align", Value::Int(2048)),
                ("Tvers", Value::Str("N/A, DLL3.11.05".into())),
            ]))
            .row(row(&[
                ("ContentOffset", Value::Int(4096)),
                ("Files", Value::Int(3)),
                ("Align", Value::Int(512)),
                ("Tvers", Value::Str("second".into())),
            ]))
    }

    #[test]
    fn write_then_read_is_lossless() {
        let bytes = sample().encode().unwrap();
        let back = Utf::parse(&bytes, 0).unwrap();
        assert_eq!(back.name, "CpkHeader");
        assert_eq!(back.rows.len(), 2);
        assert_eq!(back.rows[0]["ContentOffset"].as_u64(), 2048);
        assert_eq!(back.rows[1]["ContentOffset"].as_u64(), 4096);
        assert_eq!(back.rows[0]["Tvers"].as_str(), "N/A, DLL3.11.05");
        assert_eq!(back.rows[1]["Align"].as_u64(), 512);
        assert_eq!(back.rows[0]["Version"].as_u64(), 7);
        assert_eq!(back.rows[0]["TocCrc"], Value::Zero);
    }

    #[test]
    fn packet_size_counts_the_table_header() {
        let table = sample().encode().unwrap();
        let pkt = packet(b"CPK ", &table);
        assert_eq!(&pkt[0..4], b"CPK ");
        assert_eq!(pkt[4], 0xFF);
        let size = u32::from_le_bytes([pkt[8], pkt[9], pkt[10], pkt[11]]) as usize;
        assert_eq!(size, table.len());
        assert_eq!(&pkt[16..20], MAGIC);
        assert_eq!(be_u32(&pkt, 20) as usize + 8, size);
    }

    #[test]
    fn repeated_strings_share_one_offset() {
        let b = Builder::new("T")
            .col("DirName", ROW_STR)
            .row(row(&[("DirName", Value::Str("common/match".into()))]))
            .row(row(&[("DirName", Value::Str("common/match".into()))]));
        let bytes = b.encode().unwrap();
        let back = Utf::parse(&bytes, 0).unwrap();
        assert_eq!(back.rows[0]["DirName"], back.rows[1]["DirName"]);
        // "T", "DirName", "common/match" and their NULs, nothing duplicated.
        let strings_at = 8 + be_u32(&bytes, 12) as usize;
        assert_eq!(bytes.len() - strings_at, 2 + 8 + 13);
    }

    #[test]
    fn empty_table_round_trips() {
        let bytes = Builder::new("Empty").col("ID", ROW_U32).encode().unwrap();
        let back = Utf::parse(&bytes, 0).unwrap();
        assert!(back.rows.is_empty());
        assert_eq!(back.columns.len(), 1);
    }
}
