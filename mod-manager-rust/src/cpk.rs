//! CRIWARE CPK archives: the game's `Data/*.cpk` files.
//!
//! Reading follows the documented CRI table format (see `utf.rs` for the table
//! layout itself). Two details are easy to get wrong and both are load-bearing:
//!
//!   * a TOC is a *packet* — "TOC " plus a 16-byte header — so `@UTF` sits 16
//!     bytes into it, not at `TocOffset` itself;
//!   * `FileOffset` in the TOC is RELATIVE to the header's `ContentOffset`.
//!     Measured on dt00: entry 1 has FileOffset 0, ContentOffset 2048, and 2048
//!     is exactly where CRILAYLA starts.
//!
//! CRILAYLA is CRI's LZSS variant, little endian. Its output is built BACKWARDS,
//! the bit stream is read from the end of the payload MSB-first, and the final
//! 256 bytes of the input are literals that belong at the START of the output.
//! Getting any of those three wrong produces plausible-looking garbage.
//!
//! Writing emits stored (uncompressed) archives with the same 35-column header
//! schema the game's own dt18 uses. Stored is a first-class CPK mode — dt18
//! itself contains no CRILAYLA at all — so a repack needs no compressor.

use std::fs;
use std::io::{Read, Seek, SeekFrom};
use std::path::{Path, PathBuf};

use anyhow::{bail, Context, Result};

use crate::utf::{self, Row, Utf, Value};

const ALIGN: u64 = 2048;

#[derive(Debug, Clone)]
pub struct CpkFile {
    pub name: String,
    pub dir: String,
    pub size: u64,
    pub extract_size: u64,
    pub offset: u64,
    pub id: u64,
}

impl CpkFile {
    pub fn path(&self) -> String {
        if self.dir.is_empty() {
            self.name.clone()
        } else {
            format!("{}/{}", self.dir, self.name)
        }
    }
    pub fn compressed(&self) -> bool {
        self.extract_size > self.size
    }
}

pub struct Cpk {
    pub header: Row,
    pub files: Vec<CpkFile>,
    pub content_offset: u64,
    pub path: PathBuf,
}

fn files_from(table: &Utf) -> Vec<CpkFile> {
    let mut out = Vec::new();
    for row in &table.rows {
        let g = |k: &str| row.get(k).map(|v| v.as_u64()).unwrap_or(0);
        let s = |k: &str| {
            row.get(k)
                .map(|v| v.as_str().to_string())
                .unwrap_or_default()
        };
        let name = s("FileName");
        if name.is_empty() {
            continue;
        }
        out.push(CpkFile {
            name,
            dir: s("DirName"),
            size: g("FileSize"),
            extract_size: g("ExtractSize"),
            offset: if row.contains_key("FileOffset") {
                g("FileOffset")
            } else {
                g("ContentOffset")
            },
            id: g("ID"),
        });
    }
    out
}

/// Read a slice of a file without pulling the whole archive into memory: the
/// game's dt30 is 4 GB and only its header and TOC are ever needed to list it.
fn read_at(path: &Path, offset: u64, len: usize) -> Result<Vec<u8>> {
    let mut f = fs::File::open(path).with_context(|| format!("opening {}", path.display()))?;
    f.seek(SeekFrom::Start(offset))?;
    let mut buf = vec![0u8; len];
    f.read_exact(&mut buf)
        .with_context(|| format!("reading {len} bytes at {offset} of {}", path.display()))?;
    Ok(buf)
}

fn find_utf(buf: &[u8]) -> Option<usize> {
    buf.windows(4).position(|w| w == utf::MAGIC)
}

impl Cpk {
    pub fn open(path: &Path) -> Result<Cpk> {
        let file_size = fs::metadata(path)
            .with_context(|| format!("stat {}", path.display()))?
            .len();
        let head = read_at(path, 0, 16)?;
        if &head[0..4] != b"CPK " {
            bail!("{} is not a CPK", path.display());
        }
        let packet = u32::from_le_bytes([head[8], head[9], head[10], head[11]]) as usize;
        if packet < 8 || packet as u64 > file_size {
            bail!(
                "{}: header packet size {packet} is not plausible",
                path.display()
            );
        }
        let header_bytes = read_at(path, 0, 16 + packet)?;
        let at = find_utf(&header_bytes).context("no @UTF header in CPK")?;
        let header_table = Utf::parse(&header_bytes, at)?;
        let header = header_table
            .rows
            .into_iter()
            .next()
            .context("CPK header has no rows")?;
        let get = |k: &str| header.get(k).map(|v| v.as_u64()).unwrap_or(0);

        let content_offset = get("ContentOffset");
        let toc = get("TocOffset");
        let toc_size = get("TocSize");
        let itoc = get("ItocOffset");
        let itoc_size = get("ItocSize");

        let files = if toc > 0 && toc_size > 0 {
            let buf = read_at(path, toc, toc_size as usize)?;
            let at = find_utf(&buf).context("no @UTF inside TOC packet")?;
            files_from(&Utf::parse(&buf, at)?)
        } else if itoc > 0 && itoc_size > 0 {
            let buf = read_at(path, itoc, itoc_size as usize)?;
            let plain = crilayla_decompress(&buf).context("decompressing ITOC")?;
            let inner = find_utf(&plain).context("no @UTF inside ITOC")?;
            files_from(&Utf::parse(&plain, inner)?)
        } else {
            bail!("CPK has neither a sized TOC nor ITOC");
        };
        Ok(Cpk {
            header,
            files,
            content_offset,
            path: path.to_path_buf(),
        })
    }

    pub fn read_file(&self, entry: &CpkFile) -> Result<Vec<u8>> {
        let mut f = fs::File::open(&self.path)?;
        let start = self.content_offset + entry.offset;
        f.seek(SeekFrom::Start(start))?;
        let mut raw = vec![0u8; entry.size as usize];
        f.read_exact(&mut raw)?;
        if entry.compressed() {
            if raw.len() < 8 || &raw[0..8] != b"CRILAYLA" {
                bail!(
                    "{}: expected CRILAYLA at {start}, found {}",
                    entry.path(),
                    raw.iter()
                        .take(16)
                        .map(|b| format!("{b:02x}"))
                        .collect::<Vec<_>>()
                        .join(" ")
                );
            }
            let out = crilayla_decompress(&raw)
                .with_context(|| format!("decompressing {}", entry.path()))?;
            if out.len() != entry.extract_size as usize {
                bail!(
                    "{}: got {} bytes, header says {}",
                    entry.path(),
                    out.len(),
                    entry.extract_size
                );
            }
            Ok(out)
        } else {
            Ok(raw)
        }
    }

    /// Extract every entry under `dest`, preserving directory structure.
    pub fn extract_all(&self, dest: &Path) -> Result<usize> {
        let mut done = 0;
        for f in &self.files {
            let rel = f.path().replace('/', std::path::MAIN_SEPARATOR_STR);
            let out = dest.join(&rel);
            if let Some(parent) = out.parent() {
                fs::create_dir_all(parent)?;
            }
            fs::write(
                &out,
                self.read_file(f)
                    .with_context(|| format!("extracting {}", f.path()))?,
            )?;
            done += 1;
        }
        Ok(done)
    }

    /// Aggregate entries by their path prefix at `depth` components, so a
    /// 26,000-entry archive can be described in a dozen lines.
    pub fn folders_at(&self, depth: usize) -> Vec<Folder> {
        use std::collections::BTreeMap;
        let mut map: BTreeMap<String, (usize, u64)> = BTreeMap::new();
        for f in &self.files {
            let path = f.path();
            let parts: Vec<&str> = path.split('/').collect();
            let take = parts.len().saturating_sub(1).min(depth).max(1);
            let key = parts[..take].join("/");
            let e = map.entry(key).or_insert((0, 0));
            e.0 += 1;
            e.1 += f.extract_size;
        }
        let mut out: Vec<_> = map
            .into_iter()
            .map(|(name, (files, bytes))| Folder { name, files, bytes })
            .collect();
        out.sort_by(|a, b| b.bytes.cmp(&a.bytes).then(a.name.cmp(&b.name)));
        out
    }

    /// What is in the archive, without reading any of its content: entry count,
    /// unpacked size, the top-level folders and the file-extension mix. This is
    /// enough to say what a `dt*.cpk` is for.
    pub fn summary(&self) -> Summary {
        use std::collections::BTreeMap;
        let mut roots: BTreeMap<String, (usize, u64)> = BTreeMap::new();
        let mut exts: BTreeMap<String, usize> = BTreeMap::new();
        let mut unpacked = 0u64;
        let mut compressed = 0usize;
        for f in &self.files {
            unpacked += f.extract_size;
            if f.compressed() {
                compressed += 1;
            }
            let path = f.path();
            let root = path.split('/').next().unwrap_or("").to_string();
            let e = roots.entry(root).or_insert((0, 0));
            e.0 += 1;
            e.1 += f.extract_size;
            let ext = path
                .rsplit_once('.')
                .map(|(_, x)| x.to_ascii_lowercase())
                .unwrap_or_else(|| "(none)".into());
            *exts.entry(ext).or_insert(0) += 1;
        }
        let mut folders: Vec<_> = roots
            .into_iter()
            .map(|(name, (files, bytes))| Folder { name, files, bytes })
            .collect();
        folders.sort_by_key(|f| std::cmp::Reverse(f.bytes));
        let mut extensions: Vec<_> = exts
            .into_iter()
            .map(|(ext, count)| Extension { ext, count })
            .collect();
        extensions.sort_by_key(|e| std::cmp::Reverse(e.count));
        Summary {
            entries: self.files.len(),
            compressed,
            unpacked,
            folders,
            extensions,
        }
    }
}

#[derive(Debug, Clone)]
pub struct Folder {
    pub name: String,
    pub files: usize,
    pub bytes: u64,
}

#[derive(Debug, Clone)]
pub struct Extension {
    pub ext: String,
    pub count: usize,
}

#[derive(Debug, Clone)]
pub struct Summary {
    pub entries: usize,
    pub compressed: usize,
    pub unpacked: u64,
    pub folders: Vec<Folder>,
    pub extensions: Vec<Extension>,
}

fn align_up(v: u64, align: u64) -> u64 {
    v.div_ceil(align) * align
}

fn walk(dir: &Path, out: &mut Vec<PathBuf>) -> Result<()> {
    let mut entries: Vec<_> = fs::read_dir(dir)
        .with_context(|| format!("reading {}", dir.display()))?
        .flatten()
        .map(|e| e.path())
        .collect();
    entries.sort();
    for p in entries {
        if p.is_dir() {
            walk(&p, out)?;
        } else {
            out.push(p);
        }
    }
    Ok(())
}

/// Build a CPK from a folder. Entry order is the sorted relative path,
/// which is what `Sorted = 1` in the header claims.
///
/// With `compress`, each entry is CRILAYLA-packed and kept compressed only when
/// that actually beats storing it — the same decision CRI's own tooling makes,
/// which is why dt18 is entirely stored and dt00 is half packed.
pub fn pack(src: &Path, dest: &Path, compress: bool) -> Result<usize> {
    if !src.is_dir() {
        bail!("{} is not a folder", src.display());
    }
    let mut paths = Vec::new();
    walk(src, &mut paths)?;
    if paths.is_empty() {
        bail!("no files under {}", src.display());
    }

    let mut content: Vec<u8> = Vec::new();
    let mut toc = utf::Builder::new("CpkToc")
        .col("DirName", utf::ROW_STR)
        .col("FileName", utf::ROW_STR)
        .col("FileSize", utf::ROW_U64)
        .col("ExtractSize", utf::ROW_U64)
        .col("FileOffset", utf::ROW_U64)
        .col("ID", utf::ROW_U32)
        .col("UserString", utf::ROW_STR);

    // Read and compress every entry in parallel, then lay the results out
    // sequentially: offsets must be deterministic, but producing the bytes
    // is the slow part and is entirely independent per file. Packing dt00
    // serially took 12.9 s for 190 MB.
    use rayon::prelude::*;
    let bodies: Vec<(String, Vec<u8>, Vec<u8>)> = paths
        .par_iter()
        .map(|p| -> Result<(String, Vec<u8>, Vec<u8>)> {
            let rel = p
                .strip_prefix(src)
                .unwrap()
                .to_string_lossy()
                .replace('\\', "/");
            let bytes = fs::read(p).with_context(|| format!("reading {}", p.display()))?;
            let body = if compress {
                crate::crilayla::compress(&bytes)
                    .filter(|blob| blob.len() < bytes.len())
                    .unwrap_or_else(|| bytes.clone())
            } else {
                bytes.clone()
            };
            Ok((rel, bytes, body))
        })
        .collect::<Result<Vec<_>>>()?;

    let mut packed_total: u64 = 0;
    let mut data_total: u64 = 0;
    for (i, (rel, bytes, body)) in bodies.iter().enumerate() {
        let (dir, name) = match rel.rsplit_once('/') {
            Some((d, n)) => (d.to_string(), n.to_string()),
            None => (String::new(), rel.clone()),
        };
        let offset = content.len() as u64;
        content.extend_from_slice(body);
        let padded = align_up(content.len() as u64, ALIGN);
        content.resize(padded as usize, 0);
        packed_total += body.len() as u64;
        data_total += bytes.len() as u64;

        toc = toc.row(utf::row(&[
            ("DirName", Value::Str(dir)),
            ("FileName", Value::Str(name)),
            ("FileSize", Value::Int(body.len() as u64)),
            ("ExtractSize", Value::Int(bytes.len() as u64)),
            ("FileOffset", Value::Int(offset)),
            ("ID", Value::Int(i as u64)),
            ("UserString", Value::Str(String::new())),
        ]));
    }

    let content_size = content.len() as u64;
    let toc_offset = ALIGN + content_size;
    let toc_packet = utf::packet(b"TOC ", &toc.encode()?);

    let header = utf::Builder::new("CpkHeader")
        .col("UpdateDateTime", utf::ROW_U64)
        .zero("FileSize")
        .col("ContentOffset", utf::ROW_U64)
        .col("ContentSize", utf::ROW_U64)
        .col("TocOffset", utf::ROW_U64)
        .col("TocSize", utf::ROW_U64)
        .zero("TocCrc")
        .col("EtocOffset", utf::ROW_U64)
        .col("EtocSize", utf::ROW_U64)
        .zero("ItocOffset")
        .zero("ItocSize")
        .zero("ItocCrc")
        .zero("GtocOffset")
        .zero("GtocSize")
        .zero("GtocCrc")
        .col("EnabledPackedSize", utf::ROW_U64)
        .col("EnabledDataSize", utf::ROW_U64)
        .zero("TotalDataSize")
        .zero("Tocs")
        .col("Files", utf::ROW_U32)
        .col("Groups", utf::ROW_U32)
        .col("Attrs", utf::ROW_U32)
        .zero("TotalFiles")
        .zero("Directories")
        .zero("Updates")
        .col("Version", utf::ROW_U16)
        .col("Revision", utf::ROW_U16)
        .col("Align", utf::ROW_U16)
        .col("Sorted", utf::ROW_U16)
        .zero("EID")
        .col("CpkMode", utf::ROW_U32)
        .col("Tvers", utf::ROW_STR)
        .zero("Comment")
        .col("Codec", utf::ROW_U32)
        .col("DpkItoc", utf::ROW_U32)
        .row(utf::row(&[
            ("UpdateDateTime", Value::Int(1)),
            ("ContentOffset", Value::Int(ALIGN)),
            ("ContentSize", Value::Int(content_size)),
            ("TocOffset", Value::Int(toc_offset)),
            ("TocSize", Value::Int(toc_packet.len() as u64)),
            ("EtocOffset", Value::Int(0)),
            ("EtocSize", Value::Int(0)),
            ("EnabledPackedSize", Value::Int(packed_total)),
            ("EnabledDataSize", Value::Int(data_total)),
            ("Files", Value::Int(paths.len() as u64)),
            ("Groups", Value::Int(0)),
            ("Attrs", Value::Int(0)),
            ("Version", Value::Int(7)),
            ("Revision", Value::Int(2)),
            ("Align", Value::Int(ALIGN)),
            ("Sorted", Value::Int(1)),
            ("CpkMode", Value::Int(1)),
            ("Tvers", Value::Str("fl27mm".into())),
            ("Codec", Value::Int(0)),
            ("DpkItoc", Value::Int(0)),
        ]));

    let head = utf::packet(b"CPK ", &header.encode()?);
    if head.len() as u64 > ALIGN {
        bail!(
            "header packet is {} bytes, larger than the {ALIGN}-byte alignment",
            head.len()
        );
    }

    let mut out = Vec::with_capacity(ALIGN as usize + content.len() + toc_packet.len());
    out.extend_from_slice(&head);
    out.resize(ALIGN as usize, 0);
    out.extend_from_slice(&content);
    out.extend_from_slice(&toc_packet);

    if let Some(parent) = dest.parent() {
        fs::create_dir_all(parent)?;
    }
    fs::write(dest, &out).with_context(|| format!("writing {}", dest.display()))?;
    Ok(paths.len())
}

/// CRILAYLA decompression. Output is built backwards; the trailing 256 bytes
/// of the input are literals belonging at the start of the output.
pub fn crilayla_decompress(data: &[u8]) -> Result<Vec<u8>> {
    if data.len() < 16 || &data[0..8] != b"CRILAYLA" {
        return Ok(data.to_vec()); // stored, not compressed
    }
    let unc = u32::from_le_bytes([data[8], data[9], data[10], data[11]]) as usize;
    const LITERAL: usize = 256;
    if data.len() < 16 + LITERAL {
        bail!("CRILAYLA stream too short");
    }
    let total = unc + LITERAL;
    let mut out = vec![0u8; total];
    out[..LITERAL].copy_from_slice(&data[data.len() - LITERAL..]);

    let payload_end = data.len() - LITERAL;
    let mut byte_pos = payload_end;
    let mut bit_pos = 0u32;
    let mut current = 0u8;

    macro_rules! bit {
        () => {{
            if bit_pos == 0 {
                if byte_pos <= 16 {
                    return Ok(out);
                }
                byte_pos -= 1;
                current = data[byte_pos];
                bit_pos = 8;
            }
            bit_pos -= 1;
            (current >> bit_pos) & 1
        }};
    }

    let mut out_pos = total;
    while out_pos > LITERAL {
        let is_backref = bit!();
        if is_backref == 0 {
            let mut v = 0u8;
            for _ in 0..8 {
                v = (v << 1) | bit!();
            }
            out_pos -= 1;
            out[out_pos] = v;
            continue;
        }
        let mut distance = 0usize;
        for _ in 0..13 {
            distance = (distance << 1) | bit!() as usize;
        }
        distance += 3;
        // Escalating extra-length fields: 2, 3, 5, then 8 bits repeatedly.
        let mut length = 3usize;
        let widths = [2usize, 3, 5];
        let mut idx = 0;
        loop {
            let w = if idx < widths.len() { widths[idx] } else { 8 };
            let mut v = 0usize;
            for _ in 0..w {
                v = (v << 1) | bit!() as usize;
            }
            length += v;
            let max = (1usize << w) - 1;
            if v < max {
                break;
            }
            idx += 1;
            // Must stay in step with crilayla::encode_length. The longest
            // match needs ~257 of these, so anything tight enough to trip
            // here truncates a long run and desynchronises the rest.
            if idx > 1024 {
                break;
            }
        }
        if distance > out_pos {
            break;
        }
        for _ in 0..length {
            if out_pos <= LITERAL {
                break;
            }
            out_pos -= 1;
            out[out_pos] = out[out_pos + distance];
        }
    }
    Ok(out)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn stored_data_passes_through() {
        let data = b"not a crilayla stream";
        assert_eq!(crilayla_decompress(data).unwrap(), data.to_vec());
    }

    #[test]
    fn alignment_rounds_up_only() {
        assert_eq!(align_up(0, ALIGN), 0);
        assert_eq!(align_up(1, ALIGN), ALIGN);
        assert_eq!(align_up(ALIGN, ALIGN), ALIGN);
        assert_eq!(align_up(ALIGN + 1, ALIGN), 2 * ALIGN);
    }

    #[test]
    fn real_cpk_header_parses() {
        let p = Path::new(r"C:\Games\SP Football Life 2027\Data\dt18_all.cpk");
        if !p.exists() {
            return;
        }
        let cpk = Cpk::open(p).expect("open dt18");
        let toc = cpk.header.get("TocOffset").unwrap().as_u64();
        let size = cpk.header.get("TocSize").unwrap().as_u64();
        let file_size = std::fs::metadata(p).unwrap().len();
        assert!(toc + size <= file_size, "TOC must lie inside the file");
        assert!(!cpk.files.is_empty(), "dt18 should list files");
    }

    #[test]
    fn pack_then_open_returns_the_same_bytes() {
        let dir = std::env::temp_dir().join(format!("fl27mm-pack-{}", std::process::id()));
        let src = dir.join("src");
        fs::create_dir_all(src.join("common/match/constant")).unwrap();
        let a = b"first file, small".to_vec();
        let b = vec![0xABu8; 5000];
        fs::write(src.join("version.txt"), &a).unwrap();
        fs::write(src.join("common/match/constant/constant_match.bin"), &b).unwrap();

        let out = dir.join("repacked.cpk");
        assert_eq!(pack(&src, &out, false).unwrap(), 2);

        let cpk = Cpk::open(&out).unwrap();
        assert_eq!(cpk.files.len(), 2);
        assert_eq!(cpk.content_offset, ALIGN);
        for f in &cpk.files {
            let expect = if f.name == "version.txt" { &a } else { &b };
            assert_eq!(&cpk.read_file(f).unwrap(), expect, "{}", f.path());
            assert!(!f.compressed());
        }
        let _ = fs::remove_dir_all(&dir);
    }
}
