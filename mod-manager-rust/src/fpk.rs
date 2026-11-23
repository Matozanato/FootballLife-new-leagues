//! `foxfpk` payload containers -- the file that holds a face's meshes.
//!
//! A `.fpk` sits inside a CPK (or, in an unpacked mod, sits loose in the tree)
//! and holds several assets under their real names: a face is
//! `face_diff.bin`, `face_high.fmdl`, `hair_high.fmdl`, `oral.fmdl`. Editing a
//! mesh means unpacking one of these, changing it, and laying the container out
//! again with the same alignment the game was handed.
//!
//! The layout was measured against two real face containers in
//! `livecpk/root/Asset/model/character/face/real/`, whose payload extents
//! reproduce the file size exactly:
//!
//! ```text
//!  0  "foxfpk\0win"          (fpkd uses "foxfpkdwin0" and is not parsed here)
//! 10  u32                    total file size
//! 36  u32                    entry count
//! 48  entry[count]           48 bytes each, all fields u64:
//!                              data offset (absolute)
//!                              data length
//!                              name offset (absolute, points at the blob below)
//!                              name length (without the NUL)
//!                              path code64
//!                              name code64
//!    ...names, NUL separated, then payloads at their recorded offsets
//! ```
//!
//! Offsets are absolute rather than relative to a data base, which is why the
//! first entry of a face container points at the small `FACE` metadata blob
//! ahead of the meshes instead of at a mesh.

use std::fs;
use std::io::{self, Write};
use std::path::Path;

pub const MAGIC: &[u8; 8] = b"foxfpk\0w";
const ENTRY_STRIDE: usize = 48;
const TABLE_OFFSET: usize = 48;
/// Payloads start on a 16-byte boundary in every container examined.
pub const ALIGN: u64 = 16;

#[derive(Debug, Clone)]
pub struct Entry {
    pub name: String,
    /// Hash of the asset path, kept so a repack writes back the same codes the
    /// game resolves by.
    pub path_code: u64,
    pub name_code: u64,
    pub data: Vec<u8>,
}

#[derive(Debug, Clone)]
pub struct Fpk {
    pub entries: Vec<Entry>,
}

fn le_u32(b: &[u8], at: usize) -> u32 {
    u32::from_le_bytes([b[at], b[at + 1], b[at + 2], b[at + 3]])
}

fn le_u64(b: &[u8], at: usize) -> u64 {
    u64::from_le_bytes(b[at..at + 8].try_into().unwrap())
}

fn name_of(bytes: &[u8]) -> String {
    let end = bytes.iter().position(|&c| c == 0).unwrap_or(bytes.len());
    String::from_utf8_lossy(&bytes[..end]).replace('\\', "/")
}

impl Fpk {
    pub fn parse(buf: &[u8]) -> io::Result<Fpk> {
        if buf.len() < TABLE_OFFSET + ENTRY_STRIDE {
            return Err(io::Error::new(io::ErrorKind::InvalidData, "too short to be a foxfpk"));
        }
        if &buf[0..8] != MAGIC {
            return Err(io::Error::new(
                io::ErrorKind::InvalidData,
                format!("not a foxfpk container (starts with {:?})", &buf[0..8]),
            ));
        }
        let count = le_u32(buf, 36) as usize;
        let total = le_u32(buf, 10) as usize;
        if count == 0 || count > 4096 {
            return Err(io::Error::new(
                io::ErrorKind::InvalidData,
                format!("implausible entry count {count}"),
            ));
        }
        if total != 0 && total > buf.len() {
            return Err(io::Error::new(
                io::ErrorKind::InvalidData,
                format!("header claims {total} bytes, file has {}", buf.len()),
            ));
        }
        let table_end = TABLE_OFFSET + count * ENTRY_STRIDE;
        if table_end > buf.len() {
            return Err(io::Error::new(io::ErrorKind::InvalidData, "entry table runs past the end"));
        }
        let mut entries = Vec::with_capacity(count);
        for i in 0..count {
            let at = TABLE_OFFSET + i * ENTRY_STRIDE;
            let data_off = le_u64(buf, at) as usize;
            let data_len = le_u64(buf, at + 8) as usize;
            let name_off = le_u64(buf, at + 16) as usize;
            let name_len = le_u64(buf, at + 24) as usize;
            let path_code = le_u64(buf, at + 32);
            let name_code = le_u64(buf, at + 40);
            // Names sit in the blob straight after the table, so they are the
            // first thing a corrupt or misaligned read shows up against.
            let Some(name_end) = name_off.checked_add(name_len) else {
                return Err(io::Error::new(io::ErrorKind::InvalidData, "name range overflows"));
            };
            if name_off < table_end || name_end > buf.len() {
                return Err(io::Error::new(
                    io::ErrorKind::InvalidData,
                    format!("entry {i} name range {name_off}..{name_end} is outside the string blob"),
                ));
            }
            let Some(data_end) = data_off.checked_add(data_len) else {
                return Err(io::Error::new(io::ErrorKind::InvalidData, "data range overflows"));
            };
            if data_end > buf.len() {
                return Err(io::Error::new(
                    io::ErrorKind::InvalidData,
                    format!("entry {i} data range {data_off}..{data_end} runs past the end of the file"),
                ));
            }
            entries.push(Entry {
                name: name_of(&buf[name_off..name_end]),
                path_code,
                name_code,
                data: buf[data_off..data_end].to_vec(),
            });
        }
        Ok(Fpk { entries })
    }

    pub fn read(path: &Path) -> io::Result<Fpk> {
        Fpk::parse(&fs::read(path)?)
    }

    /// Serialise, keeping entries in order and every payload 16-byte aligned.
    /// The name blob is rebuilt at the end of the table because the entries'
    /// name offsets are absolute and would otherwise have to chase each other.
    pub fn render(&self) -> Vec<u8> {
        let table_end = TABLE_OFFSET + self.entries.len() * ENTRY_STRIDE;
        let mut names: Vec<u8> = Vec::new();
        let mut name_offs: Vec<u64> = Vec::with_capacity(self.entries.len());
        for e in &self.entries {
            name_offs.push((table_end + names.len()) as u64);
            names.extend_from_slice(e.name.replace('/', "\\").as_bytes());
            names.push(0);
        }
        while !names.len().is_multiple_of(ALIGN as usize) {
            names.push(0);
        }
        let mut data_at: Vec<u64> = Vec::with_capacity(self.entries.len());
        let mut pos = table_end + names.len();
        for e in &self.entries {
            while !pos.is_multiple_of(ALIGN as usize) {
                pos += 1;
            }
            data_at.push(pos as u64);
            pos += e.data.len();
        }
        let mut out = vec![0u8; pos];
        out[..8].copy_from_slice(MAGIC);
        out[8] = b'i';
        out[9] = b'n';
        out[10..14].copy_from_slice(&(pos as u32).to_le_bytes());
        out[32..36].copy_from_slice(&2u32.to_le_bytes());
        out[36..40].copy_from_slice(&(self.entries.len() as u32).to_le_bytes());
        for (i, e) in self.entries.iter().enumerate() {
            let at = TABLE_OFFSET + i * ENTRY_STRIDE;
            out[at..at + 8].copy_from_slice(&data_at[i].to_le_bytes());
            out[at + 8..at + 16].copy_from_slice(&(e.data.len() as u64).to_le_bytes());
            out[at + 16..at + 24].copy_from_slice(&name_offs[i].to_le_bytes());
            out[at + 24..at + 32].copy_from_slice(&(e.name.len() as u64).to_le_bytes());
            out[at + 32..at + 40].copy_from_slice(&e.path_code.to_le_bytes());
            out[at + 40..at + 48].copy_from_slice(&e.name_code.to_le_bytes());
        }
        out[table_end..table_end + names.len()].copy_from_slice(&names);
        for (i, e) in self.entries.iter().enumerate() {
            let at = data_at[i] as usize;
            out[at..at + e.data.len()].copy_from_slice(&e.data);
        }
        out
    }

    pub fn write(&self, path: &Path) -> io::Result<()> {
        let bytes = self.render();
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)?;
        }
        let tmp = path.with_extension("fpk.tmp");
        {
            let mut f = fs::File::create(&tmp)?;
            f.write_all(&bytes)?;
        }
        fs::rename(&tmp, path)
    }

    pub fn find(&self, name: &str) -> Option<&Entry> {
        let want = name.replace('\\', "/");
        self.entries
            .iter()
            .find(|e| e.name.eq_ignore_ascii_case(&want) || file_name(&e.name).eq_ignore_ascii_case(&want))
    }

    pub fn find_mut(&mut self, name: &str) -> Option<&mut Entry> {
        let want = name.replace('\\', "/");
        self.entries
            .iter_mut()
            .find(|e| e.name.eq_ignore_ascii_case(&want) || file_name(&e.name).eq_ignore_ascii_case(&want))
    }

    /// Drop every payload into `dest`, mirroring the recorded paths.
    pub fn extract(&self, dest: &Path) -> io::Result<Vec<String>> {
        let mut written = Vec::new();
        for e in &self.entries {
            let path = dest.join(&e.name);
            if let Some(parent) = path.parent() {
                fs::create_dir_all(parent)?;
            }
            fs::write(&path, &e.data)?;
            written.push(e.name.clone());
        }
        Ok(written)
    }
}

fn file_name(path: &str) -> &str {
    let unified = path.replace('\\', "/");
    // Safe because the borrowed slice's contents match `path` in length and
    // character positions for the ASCII names these containers hold.
    match unified.rfind('/') {
        Some(i) => {
            let start = i + 1;
            &path[path.len() - (unified.len() - start)..]
        }
        None => path,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample() -> Fpk {
        Fpk {
            entries: vec![
                Entry {
                    name: "Assets/pes16/model/face/face_diff.bin".into(),
                    path_code: 0x1111_1111_1111_1111,
                    name_code: 0x2222_2222_2222_2222,
                    data: b"FACE metadata blob".to_vec(),
                },
                Entry {
                    name: "face_high.fmdl".into(),
                    path_code: 0x3333_3333_3333_3333,
                    name_code: 0x4444_4444_4444_4444,
                    data: vec![0x46; 1000],
                },
            ],
        }
    }

    #[test]
    fn survives_a_round_trip() {
        let f = sample();
        let back = Fpk::parse(&f.render()).unwrap();
        assert_eq!(back.entries.len(), 2);
        assert_eq!(back.entries[0].name, f.entries[0].name);
        assert_eq!(back.entries[1].data, f.entries[1].data);
        assert_eq!(back.entries[0].path_code, f.entries[0].path_code);
        assert_eq!(back.entries[1].name_code, f.entries[1].name_code);
        assert_eq!(back.render(), f.render());
    }

    #[test]
    fn payloads_are_sixteen_byte_aligned_and_the_size_field_is_true() {
        let f = sample();
        let bytes = f.render();
        assert_eq!(&bytes[0..8], MAGIC);
        assert_eq!(le_u32(&bytes, 10) as usize, bytes.len());
        let count = le_u32(&bytes, 36) as usize;
        for i in 0..count {
            let at = TABLE_OFFSET + i * ENTRY_STRIDE;
            assert_eq!(le_u64(&bytes, at) % ALIGN, 0, "entry {i} is misaligned");
        }
        assert_eq!(file_name("Assets\\pes16\\model\\face\\face_diff.bin"), "face_diff.bin");
    }

    #[test]
    fn rejects_a_file_that_is_not_a_container() {
        let err = Fpk::parse(&[0u8; 400]).unwrap_err();
        assert!(err.to_string().contains("foxfpk"), "{err}");
    }

    #[test]
    fn rejects_a_truncated_payload_range() {
        let mut bytes = sample().render();
        let at = TABLE_OFFSET + ENTRY_STRIDE + 8;
        bytes[at..at + 8].copy_from_slice(&(999_999u64).to_le_bytes());
        let err = Fpk::parse(&bytes).unwrap_err();
        assert!(err.to_string().contains("past the end"), "{err}");
    }
}
