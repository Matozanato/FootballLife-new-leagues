//! fl27mm: format tools for SP Football Life 2027 game files.
//!
//! Commands:
//!   pesdb      validate database tables before they can override the game
//!   cpk        list, extract or rebuild a CRIWARE archive
//!   ftex       convert Fox Engine textures to and from DDS
//!   container  unwrap, inspect or re-wrap a WESYS/asset container
//!   bin        decode a .bin: sections, records, menu atlases, strings and hex

use fl27mm::{binread, cpk, ftex, pesdb, wesys};

use std::path::{Path, PathBuf};

use anyhow::{bail, Context, Result};
use clap::{Parser, Subcommand};


#[derive(Parser)]
#[command(name = "fl27mm", version, about)]
struct Cli {
    #[command(subcommand)]
    cmd: Cmd,
}

#[derive(Subcommand)]
enum Cmd {
    /// Validate pesdb tables by framing and record stride.
    Pesdb {
        /// Folder to scan recursively for pesdb tables.
        #[arg(long)]
        dir: PathBuf,
    },
    /// Read a CRIWARE CPK archive: list, extract, or build one from a folder.
    Cpk {
        /// The .cpk file. Omit when using --pack.
        archive: Option<PathBuf>,
        /// Extract into this folder instead of just listing.
        #[arg(long)]
        extract: Option<PathBuf>,
        /// Only entries whose path contains this text.
        #[arg(long)]
        filter: Option<String>,
        /// Build a CPK from this folder into --out.
        #[arg(long)]
        pack: Option<PathBuf>,
        /// Destination for --pack.
        #[arg(long)]
        out: Option<PathBuf>,
        /// Print what the archive contains instead of every entry.
        #[arg(long)]
        summary: bool,
        /// With --summary, group entries by this many path components.
        #[arg(long, default_value = "1")]
        depth: usize,
        /// With --pack, CRILAYLA-compress each entry where that beats storing.
        #[arg(long)]
        compress: bool,
    },
    /// Convert Fox Engine textures: .ftex -> .dds, or .dds -> .ftex.
    Ftex {
        /// A file, or a folder to convert recursively.
        input: PathBuf,
        /// Output folder (mirrors the input's directory structure).
        #[arg(long)]
        out: Option<PathBuf>,
        /// Tag new textures as this kind: diffuse, normal, material, cube.
        #[arg(long, default_value = "diffuse")]
        kind: String,
    },
    /// Decode a .bin: framing, sections, table records, menu atlases and hex.
    Bin {
        /// The .bin file.
        file: PathBuf,
        /// Hex-dump this section instead of summarising.
        #[arg(long)]
        section: Option<usize>,
        /// Bytes to show from the section or body.
        #[arg(long, default_value = "256")]
        bytes: usize,
    },
    /// Unwrap or re-wrap FL27 containers (WESYS zlib tables, asset containers).
    Container {
        /// A file, or a folder to process recursively.
        input: PathBuf,
        /// Write the unwrapped body here instead of just reporting.
        #[arg(long)]
        unwrap: Option<PathBuf>,
        /// Re-wrap: treat the input as a raw body and rebuild the framing.
        #[arg(long)]
        rewrap: Option<PathBuf>,
        /// Output folder for --rewrap.
        #[arg(long)]
        out: Option<PathBuf>,
    },
    /// Name the format of a file, or survey a tree and report what is not
    /// decodable yet. A directory answers "what is in my install"; a file
    /// answers "what is this thing".
    Fmt {
        /// A file or a folder.
        path: PathBuf,
        /// Stop the survey after this many files; the default walks everything.
        #[arg(long)]
        limit: Option<usize>,
    },
    /// Read a rig chain: a `.ask` skeleton (bones and their rest transforms) or
    /// a `.frig` rig (how animation channels drive those bones). Accepts a
    /// file or a folder, in which case every one of each kind is checked.
    Rig {
        /// The `.ask` or `.frig` file, or a folder of them.
        path: PathBuf,
        /// The matching rig or skeleton, so the two can be compared: a clip's
        /// unit and segment counts must equal the rig's.
        #[arg(long)]
        with: Option<PathBuf>,
    },
    /// Decode a `.gani` animation clip: units, segments and keyframes. The
    /// walk is validated, so a clip whose blocks do not tile is refused rather
    /// than reported with plausible nonsense. Frame rate and single keyframes
    /// can be rewritten.
    Gani {
        /// The clip, or a folder of clips to check.
        path: PathBuf,
        /// Rewrite the frame rate to this value.
        #[arg(long)]
        rate: Option<u32>,
        /// With --rate, apply to every clip under a folder.
        #[arg(long)]
        all: bool,
        /// Print every unit, segment and keyframe the clip stores.
        #[arg(long)]
        tracks: bool,
        /// Rewrite one keyframe: `UNIT|SEGMENT|KEY|p0,p1,p2|s0,s1,s2`.
        /// Components are the stored integers for a quaternion track, or the
        /// raw 16-bit halves for a vector one.
        #[arg(long)]
        set_key: Option<String>,
    },
}

fn cmd_pesdb(dir: &Path) -> Result<()> {
    use rayon::prelude::*;
    let tables: Vec<PathBuf> = fl27mm::fsutil::files(dir).into_iter()
        .filter(|p| {
            let s = p.to_string_lossy();
            s.contains("pesdb") && s.ends_with(".bin")
        })
        .collect();
    let mut verdicts: Vec<(PathBuf, pesdb::Verdict)> = tables.par_iter()
        .map(|p| (p.clone(), pesdb::validate(p)))
        .collect();
    verdicts.sort_by(|a, b| a.0.cmp(&b.0));
    let mut ok = 0;
    let mut bad = 0;
    for (p, v) in &verdicts {
        let rel = p.strip_prefix(dir).unwrap_or(p);
        if v.ok {
            ok += 1;
            println!("  OK      {}  {}", rel.display(), v.reason);
        } else {
            bad += 1;
            let tag = match v.status {
                pesdb::Status::Unrecognised => "OPAQUE",
                _ => "BAD   ",
            };
            println!("  {tag}  {}  {}", rel.display(), v.reason);
        }
    }
    let opaque = verdicts.iter()
        .filter(|(_, v)| v.status == pesdb::Status::Unrecognised).count();
    let defect = bad - opaque;
    println!("
{ok} valid, {defect} with a measured defect, {opaque} unreadable");
    if defect > 0 {
        bail!("{defect} table(s) have a measured defect and would corrupt the game");
    }
    if opaque > 0 {
        bail!("{opaque} file(s) are not readable tables; nothing here can verify them");
    }
    Ok(())
}

fn cmd_cpk(archive: &Path, extract: Option<&Path>, filter: Option<&str>,
           summary: bool, depth: usize) -> Result<()> {
    let cpk = cpk::Cpk::open(archive)?;
    if summary {
        let s = cpk.summary();
        println!("{}: {} entries, {} compressed, {:.1} MB unpacked",
                 archive.file_name().unwrap().to_string_lossy(),
                 s.entries, s.compressed, s.unpacked as f64 / 1048576.0);
        let grouped = if depth > 1 { cpk.folders_at(depth) } else { s.folders.clone() };
        for f in grouped.iter().take(14) {
            println!("    {:<44} {:>7} files  {:>9.1} MB",
                     f.name, f.files, f.bytes as f64 / 1048576.0);
        }
        let exts: Vec<String> = s.extensions.iter().take(8)
            .map(|e| format!("{}:{}", e.ext, e.count)).collect();
        println!("    extensions: {}", exts.join("  "));
        return Ok(());
    }
    let entries: Vec<_> = cpk.files.iter()
        .filter(|f| filter.is_none_or(|f_| f.path().contains(f_)))
        .collect();
    println!("{}: {} entries ({} shown)",
             archive.display(), cpk.files.len(), entries.len());
    let packed = entries.iter().filter(|f| f.compressed()).count();
    println!("{packed} compressed, {} stored", entries.len() - packed);

    if let Some(dest) = extract {
        let mut done = 0;
        let mut failed = 0;
        for f in &entries {
            let rel = f.path().replace('/', std::path::MAIN_SEPARATOR_STR);
            let out = dest.join(&rel);
            if let Some(parent) = out.parent() {
                std::fs::create_dir_all(parent)?;
            }
            match cpk.read_file(f) {
                Ok(bytes) => {
                    std::fs::write(&out, bytes)?;
                    done += 1;
                }
                Err(e) => {
                    println!("  FAILED {}: {e}", f.path());
                    failed += 1;
                }
            }
        }
        println!("extracted {done} to {}, {failed} failed", dest.display());
        if failed > 0 {
            bail!("{failed} entries could not be extracted");
        }
    } else {
        for f in entries.iter().take(60) {
            let flag = if f.compressed() { "packed" } else { "stored" };
            println!("  {:>10}  {:>10}  {flag}  {}", f.size, f.extract_size, f.path());
        }
        if entries.len() > 60 {
            println!("  ... {} more", entries.len() - 60);
        }
    }
    Ok(())
}

fn cmd_bin(file: &Path, section: Option<usize>, bytes: usize) -> Result<()> {
    if let Some(index) = section {
        let report = binread::read(file)?;
        let table = report.sections.context("this file has no section table")?;
        let s = table.sections.get(index).context("no such section")?;
        let data = binread::section_bytes(file, index)?;
        println!("{} [{}] {} bytes at {}", file.display(), s.name, data.len(), s.offset);
        print!("{}", binread::hexdump(&data, 0, bytes));
        return Ok(());
    }
    let r = binread::read(file)?;
    println!("{}", file.display());
    println!("  {:>14} bytes, framing {}, body {:>12} bytes",
             r.file_size, r.framing, r.body_size);
    println!("  entropy {:.2} bits/byte · re-encode: {}", r.entropy, r.re_encode);
    for n in &r.notes {
        println!("  note: {n}");
    }
    if let Some(t) = &r.sections {
        println!("
  {} sections (table at {}, contiguous {}):",
                 t.count, t.table_offset, t.contiguous);
        for (i, s) in t.sections.iter().enumerate() {
            println!("    {i:>3}  {:<34} off {:>9}  size {:>8}", s.name, s.offset, s.size);
        }
        println!("
  hex-dump one with --section N");
    }
    if let Some(menu) = &r.menu_layout {
        println!(
     "\n   compiled menu atlas: {} · {} textures · {} named pictures",
     menu.package_name,
     menu.textures.len(),
     menu.pictures.len()
        );
        for (i, texture) in menu.textures.iter().enumerate() {
     println!(
         "    texture {i}: {} × {} · format 0x{:02x}",
         texture.width, texture.height, texture.format
     );
        }
        for picture in menu.pictures.iter().take(12) {
     println!(
         "    {:<32} texture {}  atlas [{:.1}, {:.1}]–[{:.1}, {:.1}] px",
         picture.name,
         picture.texture,
         picture.x0_half as f32 / 2.0,
         picture.y0_half as f32 / 2.0,
         picture.x1_half as f32 / 2.0,
         picture.y1_half as f32 / 2.0
     );
        }
        if menu.pictures.len() > 12 {
     println!("    … {} more pictures", menu.pictures.len() - 12);
        }
        println!("    rectangles are texture-atlas coordinates, not screen positions");
    }
    if let Some(t) = &r.records {
        println!("
  {} records at stride {}
  {}", t.records, t.stride, t.note);
        let cols: Vec<&str> = t.columns.iter().map(|c| c.name.as_str()).collect();
        if !cols.is_empty() {
            println!("    {}", cols.join("  "));
            for row in 0..t.records.min(12) {
                let cells: Vec<&str> = t.columns.iter()
                    .map(|c| c.values[row].as_str()).collect();
                println!("    {}", cells.join("  "));
            }
            if t.records > 12 {
                println!("    … {} more rows", t.records - 12);
            }
        }
    }
    if let Some(st) = &r.structure {
        println!("
  inferred layout: stride {} over {} records, {} of {} bytes explained",
                 st.stride, st.records, st.mapped_bytes, st.stride);
        if let Some(sub) = st.sub_record {
            println!("  repeating sub-record of {sub} bytes");
        }
        for f in &st.fields {
            if f.kind == fl27mm::structure::FieldKind::Padding && f.width < 8 {
                continue;
            }
            println!("    +{:<6} {:<5} {:<12} {}/{}  {}",
                     f.offset, f.width, f.kind.label(), f.supporting, f.records, f.sample);
        }
    }
    if !r.strings.is_empty() {
        println!("
  {} printable runs in the body:", r.strings.len());
        for hit in r.strings.iter().take(20) {
            println!("    @{:<8} {}", hit.at, hit.text);
        }
    }
    Ok(())
}

fn texture_kind(name: &str) -> Result<u32> {
    Ok(match name {
        "diffuse" | "d" => 3,
        "normal" | "n" => 9,
        "material" | "m" => 1,
        "cube" | "c" => 7,
        _ => bail!("unknown texture kind {name:?}; use diffuse, normal, material or cube"),
    })
}

fn cmd_ftex(input: &Path, out: Option<&Path>, kind: &str) -> Result<()> {
    let tag = texture_kind(kind)?;
    let dest_root = out.map(|p| p.to_path_buf())
        .unwrap_or_else(|| input.parent().unwrap_or(Path::new(".")).to_path_buf());

    let mut files = Vec::new();
    if input.is_dir() {
        let mut stack = vec![input.to_path_buf()];
        while let Some(d) = stack.pop() {
            for e in std::fs::read_dir(&d)?.flatten() {
                let p = e.path();
                if p.is_dir() {
                    stack.push(p);
                } else {
                    let ext = p.extension().unwrap_or_default().to_string_lossy().to_lowercase();
                    if ext == "ftex" || ext == "dds" {
                        files.push(p);
                    }
                }
            }
        }
        files.sort();
    } else {
        files.push(input.to_path_buf());
    }
    if files.is_empty() {
        bail!("no .ftex or .dds files under {}", input.display());
    }

    let base = if input.is_dir() { input } else { input.parent().unwrap_or(Path::new(".")) };
    let mut done = 0;
    let mut failed = 0;
    for p in &files {
        let rel = p.strip_prefix(base).unwrap_or(p);
        let ext = p.extension().unwrap_or_default().to_string_lossy().to_lowercase();
        let target = dest_root.join(rel).with_extension(if ext == "ftex" { "dds" } else { "ftex" });
        let result = (|| -> Result<String> {
            if ext == "ftex" {
                let t = ftex::to_dds_file(p, &target)?;
                Ok(format!("{}x{} {} {} mips", t.width, t.height,
                           t.format.name(), t.mips.len()))
            } else {
                let bytes = std::fs::read(p)?;
                let mut t = ftex::Ftex::from_dds(&bytes)?;
                t.texture_type = tag;
                t.write_ftex(&target)?;
                Ok(format!("{}x{} {} {} mips", t.width, t.height,
                           t.format.name(), t.mips.len()))
            }
        })();
        match result {
            Ok(info) => {
                done += 1;
                if files.len() <= 40 {
                    println!("  {}  ->  {info}", rel.display());
                }
            }
            Err(e) => {
                failed += 1;
                println!("  FAILED {}: {e}", rel.display());
            }
        }
    }
    println!("converted {done} to {}, {failed} failed", dest_root.display());
    if failed > 0 {
        bail!("{failed} texture(s) could not be converted");
    }
    Ok(())
}

fn collect_files(input: &Path, exts: &[&str]) -> Result<Vec<PathBuf>> {
    let mut files = Vec::new();
    if input.is_dir() {
        let mut stack = vec![input.to_path_buf()];
        while let Some(d) = stack.pop() {
            for e in std::fs::read_dir(&d)?.flatten() {
                let p = e.path();
                if p.is_dir() {
                    stack.push(p);
                } else if exts.is_empty() {
                    files.push(p);
                } else {
                    let ext = p.extension().unwrap_or_default().to_string_lossy().to_lowercase();
                    if exts.contains(&ext.as_str()) {
                        files.push(p);
                    }
                }
            }
        }
        files.sort();
    } else {
        files.push(input.to_path_buf());
    }
    Ok(files)
}

fn cmd_container(input: &Path, unwrap: Option<&Path>, rewrap: Option<&Path>,
                 out: Option<&Path>) -> Result<()> {
    if let Some(original) = rewrap {
        let dest = out.context("--rewrap needs --out")?;
        let framed = std::fs::read(original)
            .with_context(|| format!("reading {}", original.display()))?;
        let mut f = wesys::decode(&framed)?;
        f.body = std::fs::read(input)
            .with_context(|| format!("reading body {}", input.display()))?;
        let bytes = wesys::encode(&mut f)?;
        std::fs::create_dir_all(dest)?;
        let target = dest.join(original.file_name().unwrap());
        std::fs::write(&target, &bytes)?;
        println!("{} -> {} ({} bytes, {} framing, level {:?}, {})",
                 input.display(), target.display(), bytes.len(), f.kind.name(), f.level,
                 if f.exact { "byte-exact" } else { "semantically identical" });
        return Ok(());
    }

    let files = collect_files(input, &[])?;
    let base = if input.is_dir() { input } else { input.parent().unwrap_or(Path::new(".")) };
    let mut counts: std::collections::BTreeMap<&str, usize> = Default::default();
    let mut exact = 0;
    let mut refused = 0;
    for p in &files {
        let raw = std::fs::read(p)?;
        let mut f = match wesys::decode(&raw) {
            Ok(f) => f,
            Err(e) => {
                refused += 1;
                println!("  BAD   {}: {e}", p.strip_prefix(base).unwrap_or(p).display());
                continue;
            }
        };
        *counts.entry(f.kind.name()).or_default() += 1;
        if f.kind == wesys::Kind::Unknown {
            refused += 1;
            println!("  UNKNOWN framing: {}", p.strip_prefix(base).unwrap_or(p).display());
            continue;
        }
        let rebuilt = wesys::encode(&mut f)?;
        if f.exact {
            exact += 1;
        }
        if let Some(dir) = unwrap {
            let target = dir.join(p.strip_prefix(base).unwrap_or(p));
            if let Some(parent) = target.parent() {
                std::fs::create_dir_all(parent)?;
            }
            std::fs::write(&target, &f.body)?;
        }
        if files.len() <= 30 {
            println!("  {:<10} {:>9} -> {:>9}  {}  {}",
                     f.kind.name(), raw.len(), f.body.len(),
                     if f.exact { "exact  " } else { "re-emit" },
                     p.strip_prefix(base).unwrap_or(p).display());
        }
        let _ = rebuilt;
    }
    println!("\n{} files: {:?}", files.len(), counts);
    println!("{exact} re-encode byte-exactly, {refused} refused");
    if refused > 0 {
        bail!("{refused} file(s) have framing this codec will not rewrite");
    }
    Ok(())
}


fn cmd_fmt(path: &Path, limit: Option<usize>) -> Result<()> {
    use fl27mm::foxfmt;
    if path.is_dir() {
        let s = foxfmt::survey(path, limit)?;
        let total: usize = s.counts.iter().map(|(_, n)| n).sum();
        println!("{} files under {}", total, path.display());
        for (f, n) in &s.counts {
            let mark = if f.is_game_content() && !f.known() { "  GAP " } else { "        " };
            println!("{mark}{n:>8}  {}", f.name());
        }
        let gaps: Vec<_> = s.gaps();
        if gaps.is_empty() {
            println!("
no undecoded game formats in this tree");
        } else {
            let n: usize = gaps.iter().map(|(_, c)| c).sum();
            println!("
{n} game files are named but not decoded yet:");
            for (f, c) in gaps {
                println!("  {c:>8}  {}", f.name());
            }
        }
        return Ok(());
    }
    // Identifying needs the header, not the whole file: pointing this at a
    // 100 MB texture used to load all of it to look at the first bytes.
    use std::io::Read;
    let mut f = std::fs::File::open(path).with_context(|| format!("opening {}", path.display()))?;
    let total = f.metadata().context("no metadata")?.len() as usize;
    let mut head = vec![0u8; total.min(4096)];
    let got = f.read(&mut head)?;
    head.truncate(got);
    let mut info = foxfmt::describe(path, &head)?;
    if total != head.len() {
        // describe() sized the file from the bytes it was handed; correct it to
        // the real length rather than reporting a truncated number as the size.
        if let Some(slot) = info.fields.iter_mut().find(|(k, _)| k == "size") {
            slot.1 = format!("{total} bytes (first {} inspected)", head.len());
        }
    }
    println!("{}: {}", path.file_name().unwrap_or(path.as_os_str()).to_string_lossy(), info.format.name());
    for (k, v) in &info.fields {
        println!("  {k:>16}  {v}");
    }
    match &info.unresolved {
        Some(u) => println!("  not decoded: {u}"),
        None => println!("  fully decoded by its own module"),
    }
    Ok(())
}

fn cmd_rig(path: &Path, with: Option<&Path>) -> Result<()> {
    use fl27mm::{ask, frig};
    let mut skeletons = 0usize;
    let mut rigs = 0usize;
    let mut errs: Vec<String> = Vec::new();
    let files: Vec<PathBuf> = if path.is_dir() {
        fl27mm::fsutil::files(path)
            .into_iter()
            .filter(|p| {
                p.extension()
                    .map(|e| ["ask", "frig"].contains(&e.to_string_lossy().to_lowercase().as_str()))
                    .unwrap_or(false)
            })
            .collect()
    } else {
        vec![path.to_path_buf()]
    };
    for p in &files {
        let ext = p.extension().map(|e| e.to_string_lossy().to_lowercase()).unwrap_or_default();
        match ext.as_str() {
            "ask" => match ask::Skeleton::read(p) {
                Ok(s) => {
                    skeletons += 1;
                    if files.len() == 1 {
                        print!("{}", s.describe());
                        if let Err(e) = s.draw_order() {
                            println!("  hierarchy problem: {e}");
                        }
                    }
                }
                Err(e) => errs.push(format!("{}: {e}", p.file_name().unwrap_or_default().to_string_lossy())),
            },
            "frig" => match frig::Rig::read(p) {
                Ok(r) => {
                    rigs += 1;
                    if files.len() == 1 {
                        print!("{}", r.describe());
                    }
                }
                Err(e) => errs.push(format!("{}: {e}", p.file_name().unwrap_or_default().to_string_lossy())),
            },
            _ => {}
        }
    }
    if files.len() > 1 {
        println!(
            "{} files under {}: {skeletons} skeletons, {rigs} rigs, {} refused",
            files.len(), path.display(), errs.len()
        );
    }
    for e in errs.iter().take(12) {
        println!("  {e}");
    }
    if errs.len() > 12 {
        println!("  .. and {} more", errs.len() - 12);
    }
    // The comparison the user actually needs: a clip and a rig agree on their
    // counts or the tracks are being applied to the wrong skeleton.
    if let Some(w) = with {
        let mut rig_counts: Vec<(String, u32, u32)> = Vec::new();
        let walk = |p: &Path, acc: &mut Vec<(String, u32, u32)>| -> Result<()> {
            if p.is_dir() {
                for f in fl27mm::fsutil::files(p) {
                    if f.extension().map(|e| e == "frig").unwrap_or(false) {
                        let r = frig::Rig::read(&f)?;
                        acc.push((f.file_name().unwrap_or_default().to_string_lossy().into_owned(), r.unit_count, r.segment_count));
                    }
                }
            } else if p.extension().map(|e| e == "frig").unwrap_or(false) {
                let r = frig::Rig::read(p)?;
                acc.push((p.file_name().unwrap_or_default().to_string_lossy().into_owned(), r.unit_count, r.segment_count));
            }
            Ok(())
        };
        walk(w, &mut rig_counts)?;
        if path.is_file() && path.extension().map(|e| e == "gani").unwrap_or(false) {
            let clip = fl27mm::gani::Clip::read(path)?;
            println!(
                "clip {}: {} units, {} segments",
                path.file_name().unwrap_or_default().to_string_lossy(),
                clip.unit_count, clip.segment_count
            );
            for (name, u, s) in &rig_counts {
                let verdict = if *u == clip.unit_count && *s == clip.segment_count {
                    "MATCHES this clip"
                } else {
                    "different counts"
                };
                println!("  rig {name}: {u} units, {s} segments  {verdict}");
            }
        } else {
            for (name, u, s) in &rig_counts {
                println!("  rig {name}: {u} units, {s} segments");
            }
        }
    }
    if !errs.is_empty() && files.len() == 1 {
        bail!(errs.join("; "));
    }
    Ok(())
}

fn cmd_gani(path: &Path, rate: Option<u32>, all: bool, tracks: bool, set_key: Option<&str>) -> Result<()> {
    use fl27mm::gani;
    if let Some(spec) = set_key {
        // UNIT|SEGMENT|KEY|components|signs, with components as raw stored
        // integers so the write is exact rather than rounded through a float.
        let f: Vec<&str> = spec.split('|').collect();
        if f.len() != 5 {
            bail!("--set-key wants UNIT|SEGMENT|KEY|p0,p1,p2|s0,s1,s2");
        }
        let bad = |what: &str| anyhow::anyhow!("{what} is not a number in {spec}");
        let unit = f[0].parse::<usize>().map_err(|_| bad("unit"))?;
        let segment = f[1].parse::<usize>().map_err(|_| bad("segment"))?;
        let key = f[2].parse::<usize>().map_err(|_| bad("key"))?;
        let nums = |s: &str, e: &str| -> Result<Vec<u32>> {
            s.split(',').map(|x| x.trim().parse::<u32>().map_err(|_| anyhow::anyhow!("{e} in {s}"))).collect()
        };
        let parts = nums(f[3], "component")?;
        if parts.len() != 3 {
            bail!("three components are required, got {}", parts.len());
        }
        let signs = nums(f[4], "sign")?;
        if signs.len() != 3 {
            bail!("three sign bits are required, got {}", signs.len());
        }
        let value = if parts.iter().any(|&p| p > 0xFFFF) || signs.iter().any(|&s| s > 1) {
            bail!("sign bits must be 0 or 1");
        } else {
            gani::KeyValue::Quat {
                parts: [parts[0], parts[1], parts[2]],
                signs: [signs[0] != 0, signs[1] != 0, signs[2] != 0],
            }
        };
        gani::set_key(path, unit, segment, key, value)?;
        println!("{spec} written and verified on {}", path.display());
        let bytes = std::fs::read(path)?;
        let clip = gani::Clip::parse(&bytes)?;
        print!("{}", gani::tracks(&bytes, &clip)?);
        return Ok(());
    }
    if path.is_dir() {
        let clips: Vec<_> = fl27mm::fsutil::files(path)
            .into_iter()
            .filter(|p| p.extension().map(|e| e == "gani").unwrap_or(false))
            .collect();
        if clips.is_empty() {
            println!("no .gani files under {}", path.display());
            return Ok(());
        }
        let Some(rate) = rate else {
            let (mut ok, mut bad, mut stale) = (0usize, 0usize, 0usize);
            for p in &clips {
                match gani::Clip::read(p) {
                    Ok(c) => {
                        ok += 1;
                        if c.size_disagrees() { stale += 1; }
                    }
                    Err(e) => {
                        bad += 1;
                        println!("  {}  {}", p.file_name().unwrap_or_default().to_string_lossy(), e);
                    }
                }
            }
            println!("{} clips under {}", clips.len(), path.display());
            println!("  {ok} decoded, {bad} refused");
            if stale > 0 {
                println!("  {stale} carry a stale size field in the header; they still parse");
            }
            return Ok(());
        };
        let mut changed = 0;
        if !all {
            bail!("a folder needs --all to rewrite every clip in it");
        }
        for p in &clips {
            match gani::set_frame_rate(p, rate) {
                Ok((was, now)) => {
                    if was != now { changed += 1; }
                }
                Err(e) => println!("  skipped {}: {e}", p.file_name().unwrap_or_default().to_string_lossy()),
            }
        }
        println!("{} clips, {changed} rewritten to {rate} fps", clips.len());
        return Ok(());
    }
    let clip = gani::Clip::read(path)?;
    if let Some(rate) = rate {
        let (was, now) = gani::set_frame_rate(path, rate)?;
        println!("{}: frame rate {was} -> {now}", path.file_name().unwrap_or_default().to_string_lossy());
    }
    print!("{}", gani::describe(&clip));
    if tracks {
        let bytes = std::fs::read(path)?;
        print!("{}", gani::tracks(&bytes, &clip)?);
    }
    Ok(())
}

fn main() -> Result<()> {    let cli = Cli::parse();
    match cli.cmd {
        Cmd::Pesdb { dir } => cmd_pesdb(&dir),
        Cmd::Cpk { archive, extract, filter, pack, out, summary, depth, compress } => {
            if let Some(src) = pack {
                let dest = out.context("--pack needs --out")?;
                let n = cpk::pack(&src, &dest, compress)?;
                println!("packed {n} files into {} ({})", dest.display(),
                     if compress { "CRILAYLA where it paid" } else { "stored" });
                let back = cpk::Cpk::open(&dest)?;
                println!("re-read: {} entries, content at {}",
                         back.files.len(), back.content_offset);
                Ok(())
            } else {
                let archive = archive.context("give a .cpk, or use --pack")?;
                cmd_cpk(&archive, extract.as_deref(), filter.as_deref(), summary, depth)
            }
        }
        Cmd::Ftex { input, out, kind } => cmd_ftex(&input, out.as_deref(), &kind),
        Cmd::Bin { file, section, bytes } => cmd_bin(&file, section, bytes),
        Cmd::Container { input, unwrap, rewrap, out } => {
            cmd_container(&input, unwrap.as_deref(), rewrap.as_deref(), out.as_deref())
        }
        Cmd::Fmt { path, limit } => cmd_fmt(&path, limit),
        Cmd::Rig { path, with } => cmd_rig(&path, with.as_deref()),
        Cmd::Gani { path, rate, all, tracks, set_key } => cmd_gani(&path, rate, all, tracks, set_key.as_deref())
    }
}
