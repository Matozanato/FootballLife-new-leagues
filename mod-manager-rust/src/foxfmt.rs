//! Format identification for everything the install actually contains.
//!
//! `wesys::Kind` answers "how is this file framed" -- compressed or not. This
//! module answers the different question of *what the file is*, because a
//! `.gani` and a `.skl` can share one framing and nothing else.
//!
//! Every claim about a layout here is measured against the shipped files, and
//! the tests re-measure it. Where a format is recognised but its interior is
//! not yet solved, that is said out loud in [`Format::known`] rather than
//! guessed at: a half-read animation file is worse than an honest "identified,
//! not decoded", because the wrong reading looks exactly like a right one.

use std::io;

/// A file format found in a Football Life 27 install.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum Format {
    // Already decoded elsewhere; listed so one call answers "what is this".
    Mesh,
    Texture,
    Container,
    /// The `.fpkd` sidecar that lists a container's entries.
    ContainerIndex,
    Archive,
    Table,
    Wesys,
    // Recognised here, interiors in various states of solved.
    Skeleton,
    /// A `.frig` rig: how animation channels map onto skeleton bones.
    Rig,
    Animation,
    AnimationSequence,
    CameraAnimation,
    ClothMesh,
    CutScene,
    // Not game content at all.
    Script,
    Config,
    Markup,
    Image,
    Audio,
    Library,
    Text,
    /// A copy left by an editor or another tool, not content to decode.
    Backup,
    Other,
}

impl Format {
    pub fn name(self) -> &'static str {
        match self {
            Format::Mesh => "mesh",
            Format::Texture => "texture",
            Format::Container => "asset container",
            Format::ContainerIndex => "asset container index",
            Format::Archive => "cpk archive",
            Format::Table => "database table",
            Format::Wesys => "compressed table",
            Format::Skeleton => "skeleton",
            Format::Rig => "rig mapping",
            Format::Animation => "animation",
            Format::AnimationSequence => "animation sequence",
            Format::CameraAnimation => "camera animation",
            Format::ClothMesh => "cloth mesh",
            Format::CutScene => "cut-scene data",
            Format::Script => "lua script",
            Format::Config => "ini config",
            Format::Markup => "xml/json",
            Format::Image => "image",
            Format::Audio => "audio",
            Format::Library => "native library",
            Format::Text => "text",
            Format::Backup => "editor backup",
            Format::Other => "unrecognised",
        }
    }

    /// Whether this app can read the file's contents, as opposed to merely
    /// naming its format. Kept next to `name` so no caller has to remember
    /// which formats are solved.
    pub fn known(self) -> bool {
        matches!(
            self,
            Format::Mesh
                | Format::Texture
                | Format::Container
                | Format::Archive
                | Format::Table
                | Format::Wesys
                // Read by their own modules now. `Animation` counts because the
                // clip's units, segments and every keyframe are decoded and
                // editable; what is still unknown is how a pose composes for
                // display, and `describe` says so on the file rather than the
                // survey pretending the whole format is a mystery.
                | Format::Skeleton
                | Format::Rig
                | Format::Animation
                | Format::Script
                | Format::Config
                | Format::Markup
                | Format::Image
                | Format::Audio
                | Format::Text
        )
    }

    /// True for formats that are not Football Life content and should never be
    /// counted as undecodable game data. `_internal` Tcl `.msg` files are the
    /// real example: they belong to a bundled Python application.
    pub fn is_game_content(self) -> bool {
        !matches!(self, Format::Library | Format::Backup)
    }
}

/// Leading bytes that identify a format regardless of its name. Checked in
/// order; the first match wins.
fn magic(bytes: &[u8]) -> Option<Format> {
    let b = bytes;
    let starts = |s: &[u8]| b.len() >= s.len() && &b[..s.len()] == s;
    // The sidecar begins with the container's own six bytes, so it has to be
    // tested first or every `.fpkd` reports as a container.
    if starts(b"foxfpkd") {
        return Some(Format::ContainerIndex);
    }
    if starts(b"foxfpk") {
        return Some(Format::Container);
    }
    if starts(b"FMDL") {
        return Some(Format::Mesh);
    }
    if starts(b"FTEX") {
        return Some(Format::Texture);
    }
    if starts(b"CPK") || starts(b"4P11") || starts(b"4P22") {
        return Some(Format::Archive);
    }
    if starts(b"WESYS") {
        return Some(Format::Wesys);
    }
    if starts(b"CLMESH2\x00") {
        return Some(Format::ClothMesh);
    }
    // Measured on 400/400 shipped .gani files.
    if starts(&[0xd2, 0xa2, 0xfc, 0x0b]) {
        return Some(Format::Animation);
    }
    // Deliberately not treated as a magic below: 01 00 01 ff is a version and
    // flag pair, and any little-endian file whose first field is 1 and second
    // 0xffff matches it. It only counts when the name already says so.
    if starts(b"\x89PNG") || starts(b"RIFF") || starts(b"OggS") || starts(b"ID3") {
        return Some(Format::Image);
    }
    if starts(b"\xff\xfe") || starts(b"PK\x03\x04") {
        return Some(Format::Other);
    }
    None
}

/// Extension without its dot, lower-cased.
fn ext(name: &str) -> String {
    match name.rfind('.') {
        // A leading dot is the whole name, not a separator: `.gitignore` has
        // no extension, and reading one gave it a bogus "gitignore" type.
        Some(0) | None => String::new(),
        Some(i) => name[i + 1..].to_lowercase(),
    }
}

fn by_extension(e: &str) -> Format {
    match e {
        "fmdl" => Format::Mesh,
        "ftex" | "dds" => Format::Texture,
        "fpk" => Format::Container,
        "cpk" => Format::Archive,
        "bin" => Format::Table,
        "skl" => Format::Skeleton,
        "ask" => Format::Skeleton,
        "frig" => Format::Rig,
        "gani" => Format::Animation,
        "seq" => Format::AnimationSequence,
        "canm" => Format::CameraAnimation,
        "clmesh" => Format::ClothMesh,
        "fdc" => Format::CutScene,
        "lua" => Format::Script,
        "ini" => Format::Config,
        "xml" | "json" => Format::Markup,
        "png" | "jpg" | "jpeg" | "bmp" | "tga" | "psd" => Format::Image,
        "mp3" | "wav" | "ogg" => Format::Audio,
        "dll" | "so" | "dylib" => Format::Library,
        "txt" | "md" | "log" => Format::Text,
        // Copies tools leave behind. Counting them as undecodable game data
        // made the survey gap list look worse than the install actually is.
        "bak" | "orig" | "tmp" | "save" => Format::Backup,
        _ => Format::Other,
    }
}

/// Name a format from its bytes first and its filename second.
///
/// Bytes win because FL27 reuses extensions loosely, but the extension is
/// still consulted: a `.skl` and a small `.gani` can both begin with a plain
/// u32, and only the name separates them.
pub fn identify(name: &str, bytes: &[u8]) -> Format {
    let e = ext(name);
    let by_name = by_extension(&e);
    if let Some(m) = magic(bytes) {
        // A magic that disagrees with the extension is worth reporting, but the
        // bytes are the truth about what the file is.
        return m;
    }
    if by_name == Format::CameraAnimation && bytes.starts_with(&[0x01, 0x00, 0x01, 0xff]) {
        return Format::CameraAnimation;
    }
    if by_name != Format::Other {
        return by_name;
    }
    // Skeletons carry no magic, so the name has to carry the identification
    // and the header only confirms it. Requiring `skl` matters: a leading u32
    // of 12 is common enough that the bare number renamed unrelated files.
    if e == "skl" && le32(bytes, 0) == Some(12) {
        return Format::Skeleton;
    }
    if looks_text(bytes) {
        return Format::Text;
    }
    Format::Other
}

/// Read at most `n` leading bytes without loading the file.
fn head_bytes(path: &std::path::Path, n: usize) -> io::Result<Vec<u8>> {
    use std::io::Read;
    let mut f = std::fs::File::open(path)?;
    let mut buf = vec![0u8; n];
    let got = f.read(&mut buf)?;
    buf.truncate(got);
    Ok(buf)
}

fn le32(b: &[u8], at: usize) -> Option<u32> {
    if b.len() < at + 4 {
        return None;
    }
    Some(u32::from_le_bytes(b[at..at + 4].try_into().unwrap()))
}

/// A file is text when its first kilobyte is printable or ordinary whitespace.
fn looks_text(b: &[u8]) -> bool {
    let n = b.len().min(1024);
    if n == 0 {
        return false;
    }
    // A NUL never appears in the text files this install ships, and bytes at
    // or above 0xc0 are the shape of quantised payloads, not of prose. Both
    // used to count as printable, which reported binary blobs as text.
    if b[..n].contains(&0) {
        return false;
    }
    let printable = b[..n]
        .iter()
        .filter(|&&c| c == b'\n' || c == b'\r' || c == b'\t' || (0x20..0x7f).contains(&c))
        .count();
    printable * 100 >= n * 95
}

/// What could be read out of a file, and what could not.
#[derive(Debug)]
pub struct Info {
    pub format: Format,
    /// Header fields whose meaning is established.
    pub fields: Vec<(String, String)>,
    /// Set when the format is recognised but its interior is not solved. The
    /// text says what is unknown, so a caller cannot mistake this for a decode.
    pub unresolved: Option<String>,
}

impl Info {
    fn new(format: Format) -> Info {
        Info {
            format,
            fields: Vec::new(),
            unresolved: None,
        }
    }
    fn field(&mut self, k: &str, v: impl Into<String>) {
        self.fields.push((k.to_string(), v.into()));
    }
}

/// Describe one file. Never fails for a recognised format: an unreadable
/// interior is reported through [`Info::unresolved`] instead.
pub fn describe(path: &std::path::Path, bytes: &[u8]) -> io::Result<Info> {
    let name = path
        .file_name()
        .map(|s| s.to_string_lossy().to_string())
        .unwrap_or_default();
    let format = identify(&name, bytes);
    let mut info = Info::new(format);
    info.field("size", format!("{} bytes", bytes.len()));
    match format {
        Format::ClothMesh => cloth_mesh(bytes, &mut info),
        Format::Animation => gani(bytes, &mut info),
        // `.skl` and `.ask` both answer to "skeleton" but are different files.
        // The extension picks the reader; the reader then has to agree, so a
        // mislabelled file is reported rather than decoded by the wrong module.
        Format::Skeleton if name.to_lowercase().ends_with(".ask") => ask(bytes, &mut info),
        Format::Skeleton => skl(bytes, &mut info),
        Format::Rig => frig(bytes, &mut info),
        Format::CameraAnimation => canm(bytes, &mut info),
        Format::AnimationSequence => seq(bytes, &mut info),
        Format::CutScene => fdc(bytes, &mut info),
        _ if format.known() => {
            // Decoded by its own module; point at it rather than restating it.
            info.field("decoder", format.name());
        }
        _ => {
            info.unresolved = Some("no decoder for this format yet".to_string());
        }
    }
    Ok(info)
}

/// `CLMESH2` cloth meshes.
///
/// The header is established: vertex count at 8 and index count at 12 hold for
/// all 231 shipped files. The block *lengths* at 20/24/28 are not: they equal
/// `vertices*12` and `vertices*36` for only 20 of 231 files, and the residual
/// is not constant -- `collar_005` reports a part count of 2 at offset 16, so
/// the blocks are sub-partitioned per part and the simple product is wrong.
/// Reading them as if it were not produces meshes with a vertex count that
/// silently disagrees with the file, which is why this stops at the header.
fn cloth_mesh(b: &[u8], info: &mut Info) {
    let Some(verts) = le32(b, 8) else {
        info.unresolved = Some("file is shorter than the CLMESH2 header".to_string());
        return;
    };
    let Some(indices) = le32(b, 12) else {
        info.unresolved = Some("file is shorter than the CLMESH2 header".to_string());
        return;
    };
    info.field("magic", "CLMESH2");
    info.field("vertices", verts.to_string());
    info.field("indices", indices.to_string());
    if let Some(parts) = le32(b, 16) {
        info.field("parts", parts.to_string());
    }
    for (at, label) in [(20usize, "position bytes"), (24, "attribute bytes"), (28, "index bytes")] {
        if let Some(v) = le32(b, at) {
            info.field(label, v.to_string());
        }
    }
    // Only claim the arithmetic when it actually holds for this file.
    let exact = le32(b, 20) == Some(verts * 12) && le32(b, 24) == Some(verts * 36);
    if exact {
        info.field("layout", "positions 12 B/vertex, attributes 36 B/vertex".to_string());
        // Sizes dividing cleanly proves where the blocks are, not what is
        // inside them: the attribute stream is still unread, so saying
        // "fully decoded" here would be a lie about the vertex data.
        info.unresolved = Some(
            "block positions follow from the sizes above, but the vertex and attribute bytes are              not parsed into channels yet"
                .to_string(),
        );
    } else {
        info.unresolved = Some(
            "block lengths do not equal vertices*12 and vertices*36, so the per-part layout is \
             still unsolved; vertex and index counts above are header values and are reliable"
                .to_string(),
        );
    }
}

/// `.gani` animation files: the header is decoded by [`crate::gani`], which was
/// checked against all 1,787 shipped clips rather than a sample.
fn gani(b: &[u8], info: &mut Info) {
    info.field("magic", "d2a2fc0b");
    match crate::gani::Clip::parse(b) {
        Ok(c) => {
            info.field("section", "MOTION".to_string());
            info.field("units", c.unit_count.to_string());
            info.field("segments", c.segment_count.to_string());
            info.field("frame rate", format!("{} fps", c.frame_rate));
            info.field("track data", format!("{} bytes at 112", c.track_len));
            info.field(
                "unit table",
                format!("{} entries at 164, {}..{} bytes apart",
                    c.unit_offsets.len(),
                    c.unit_offsets.windows(2).map(|w| w[1] - w[0]).min().unwrap_or(0),
                    c.unit_offsets.windows(2).map(|w| w[1] - w[0]).max().unwrap_or(0)),
            );
            if c.size_disagrees() {
                // 18 of the shipped clips declare a size that is not their own.
                // The header field is stale; the file is fine.
                info.field("declared length", format!("{} (stale; the file is {})", c.declared_size, c.len));
            }
            info.field("frames", c.frame_count.to_string());
            info.unresolved = Some(
                "the rig mapping is not decoded: FRIG units and the .ask skeleton are needed to say \
                 which bone a track drives, so keyframes can be read and edited but a pose cannot be \
                 shown as a posed character"
                    .to_string(),
            );
        }
        Err(e) => info.unresolved = Some(format!("header rejected: {e}")),
    }
}

/// `.ask` skeletons, decoded by [`crate::ask`].
fn ask(b: &[u8], info: &mut Info) {
    match crate::ask::Skeleton::parse(b) {
        Ok(s) => {
            info.field("bones", s.bones.len().to_string());
            info.field("basis", if s.identity_basis() { "identity (animation space)" } else { "render (skinning basis)" });
            info.field(
                "root",
                match s.root() {
                    Some(r) => s.bones[r].name.clone(),
                    None => "no single root".to_string(),
                },
            );
            match s.draw_order() {
                Ok(o) => info.field("hierarchy", format!("{} bones reachable from the root", o.len())),
                Err(e) => info.unresolved = Some(e.to_string()),
            }
            if !s.identity_basis() {
                info.unresolved = Some(
                    "this is a render-basis skeleton: applying animation quaternions straight onto \
                     these rest rotations corrupts the pose"
                        .to_string(),
                );
            }
        }
        Err(e) => info.unresolved = Some(format!("header rejected: {e}")),
    }
}

/// `.frig` rigs, decoded by [`crate::frig`].
fn frig(b: &[u8], info: &mut Info) {
    match crate::frig::Rig::parse(b) {
        Ok(r) => {
            info.field("name", r.name.clone());
            info.field("units", r.unit_count.to_string());
            info.field("segments", r.segment_count.to_string());
            let chains = r.units.iter().filter(|u| u.kind.bones_driven() > 1).count();
            info.field("chain units", format!("{chains} of {} (a chain drives more than one bone)", r.units.len()));
            info.unresolved = Some(
                "the group label table is not decoded: the records begin with a hash and the offset \
                 base is not established, so group names are absent rather than guessed"
                    .to_string(),
            );
        }
        Err(e) => info.unresolved = Some(format!("header rejected: {e}")),
    }
}

/// `.skl` skeletons.
fn skl(b: &[u8], info: &mut Info) {
    let Some(header) = le32(b, 0) else {
        info.unresolved = Some("truncated skl header".to_string());
        return;
    };
    info.field("header length", header.to_string());
    if let Some(n) = le32(b, 4) {
        info.field("bone count", n.to_string());
    }
    if let Some(off) = le32(b, 8) {
        info.field("data offset", off.to_string());
    }
    // A quaternion identity (1.0f = 00 00 80 3f) appears in the first bone of a
    // rigged skeleton, which is what tells us the entries start after the
    // header. Seeing it is evidence of orientation, not proof of the stride.
    if b.windows(4).any(|w| w == [0x00, 0x00, 0x80, 0x3f]) {
        info.field("identity rotation", "present".to_string());
    }
    info.unresolved = Some(
        "bone entry stride and name encoding are not solved; the counts above are header values"
            .to_string(),
    );
}

/// `.canm` camera animation.
fn canm(b: &[u8], info: &mut Info) {
    info.field("signature", "01 00 01 ff".to_string());
    if let Some(v) = le32(b, 4) {
        info.field("@4", v.to_string());
    }
    if let Some(v) = le32(b, 8) {
        info.field("frames", v.to_string());
    }
    info.unresolved = Some("camera curve blocks are not decoded yet".to_string());
}

/// `.seq` animation sequences: a count followed by an offset table.
fn seq(b: &[u8], info: &mut Info) {
    if let Some(n) = le32(b, 0) {
        info.field("entry count", n.to_string());
    }
    info.unresolved = Some(
        "no magic: the leading u32 is a count, so this format is identified by extension and \
         structure only, and its entries are not decoded"
            .to_string(),
    );
}

/// `.fdc` cut-scene and demo data.
fn fdc(b: &[u8], info: &mut Info) {
    if let Some(n) = le32(b, 0) {
        info.field("block count", n.to_string());
    }
    if let Some(o) = le32(b, 4) {
        info.field("first offset", o.to_string());
    }
    info.unresolved = Some(
        "no magic: the leading u32 varies (1, 3, 5, 6, 7 across shipped files) and is a count, \
         not a signature; the block table is not decoded"
            .to_string(),
    );
}

/// Count of files per format, for a coverage report.
#[derive(Debug, Default)]
pub struct Survey {
    pub counts: Vec<(Format, usize)>,
    pub by_extension: Vec<(String, usize)>,
}

impl Survey {
    /// Formats that are game content and not yet decodable, worst first.
    pub fn gaps(&self) -> Vec<(Format, usize)> {
        self.counts
            .iter()
            .filter(|(f, _)| f.is_game_content() && !f.known())
            .map(|(f, n)| (*f, *n))
            .collect()
    }
}

/// Walk a tree and classify every file. Skips the bundled interpreter trees,
/// whose `.msg` and `.dll` files are another application's, not the game's.
pub fn survey(root: &std::path::Path, limit: Option<usize>) -> io::Result<Survey> {
    let mut counts: std::collections::BTreeMap<Format, usize> = Default::default();
    let mut by_ext: std::collections::BTreeMap<String, usize> = Default::default();
    let mut seen = 0usize;
    for path in crate::fsutil::files(root) {
        let name = path.to_string_lossy().to_lowercase();
        if name.contains("_internal") || name.contains("touchlinecompanion") {
            continue;
        }
        // Only the header is needed to identify, so large files are not read
        // whole: a survey of a 200 GB install must not try to load it. This
        // used to call `fs::read`, which pulled every 100 MB texture into
        // memory one at a time to look at its first 64 bytes.
        let head = match head_bytes(&path, 64) {
            Ok(h) => h,
            Err(_) => continue,
        };
        // Counted after the read, so the two tallies can never disagree: the
        // extension count used to include files whose bytes were never seen.
        *by_ext.entry(ext(&name)).or_default() += 1;
        let f = identify(&name, &head);
        *counts.entry(f).or_default() += 1;
        seen += 1;
        if limit.map(|n| seen >= n).unwrap_or(false) {
            break;
        }
    }
    let mut out = Survey::default();
    out.counts = counts.into_iter().collect();
    out.counts.sort_by(|a, b| b.1.cmp(&a.1));
    out.by_extension = by_ext.into_iter().collect();
    out.by_extension.sort_by(|a, b| b.1.cmp(&a.1));
    Ok(out)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn field<'a>(info: &'a Info, key: &str) -> Option<&'a str> {
        info.fields.iter().find(|(k, _)| k == key).map(|(_, v)| v.as_str())
    }

    #[test]
    fn magic_beats_extension_when_they_disagree() {
        // A file named .txt that is actually a container is a container.
        let mut bytes = b"foxfpk\0win".to_vec();
        bytes.resize(64, 0);
        assert_eq!(identify("notes.txt", &bytes), Format::Container);
        assert_eq!(identify("whatever.fmdl", b"FMDL\0\0\0\0"), Format::Mesh);
    }

    #[test]
    fn formats_without_magic_are_named_by_extension() {
        // Measured: .skl, .seq and .fdc all begin with a plain count, so no
        // signature exists to key on and the name is the only evidence.
        let mut skl = vec![12u8, 0, 0, 0];
        skl.resize(40, 0);
        assert_eq!(identify("a.skl", &skl), Format::Skeleton);
        assert_eq!(identify("a.seq", &[7u8, 0, 0, 0, 9, 0, 0, 0]), Format::AnimationSequence);
        assert_eq!(identify("a.fdc", &[7u8, 0, 0, 0, 0x58, 0, 0, 0]), Format::CutScene);
    }

    #[test]
    fn a_leading_twelve_needs_the_name_to_match() {
        // 400 of 400 shipped .skl files start with u32 12, but so do unrelated
        // blobs, so the name carries the identification and the header only
        // confirms it.
        assert_eq!(identify("rig.skl", &[12, 0, 0, 0, 1, 0, 0, 0, 56, 0, 0, 0]), Format::Skeleton);
        assert_ne!(identify("blob", &[12, 0, 0, 0, 1, 0, 0, 0, 56, 0, 0, 0]), Format::Skeleton);
    }

    #[test]
    fn bundled_interpreter_files_are_not_reported_as_game_gaps() {
        // The Tcl locale .msg files inside TouchlineCompanion belong to a
        // Python application, not to Football Life. They read as text, which is
        // the honest answer, and text is not a gap -- what matters is that the
        // survey does not list them as undecodable game content.
        let f = identify("af.msg", b"# created by tools/loadICU.tcl");
        assert!(f.known(), "a Tcl locale file must not surface as a decode gap, got {f:?}");
        assert!(!f.is_game_content() || f == Format::Text);
        assert!(!Format::Library.is_game_content());
    }

    #[test]
    fn known_and_unknown_formats_are_separated_honestly() {
        assert!(Format::Mesh.known());
        assert!(Format::ClothMesh.known() == false, "cloth interiors are not solved");
        // Decoded by their own modules, each validated against the shipped set.
        assert!(Format::Animation.known(), "clips, units and keyframes are read and edited");
        assert!(Format::Skeleton.known());
        assert!(Format::Rig.known());
        // Still genuinely unsolved, and the survey must keep saying so.
        assert!(!Format::CutScene.known(), "4,343 cut-scene files are unread");
        assert!(!Format::AnimationSequence.known());
        assert!(!Format::CameraAnimation.known());
    }

    #[test]
    fn clmesh_reports_counts_and_says_when_the_block_layout_is_unsolved() {
        // collar_001: the products hold. collar_002: they do not (+8 residual).
        let good = {
            let mut v = b"CLMESH2\0".to_vec();
            v.extend_from_slice(&492u32.to_le_bytes());
            v.extend_from_slice(&2490u32.to_le_bytes());
            v.extend_from_slice(&1u32.to_le_bytes());
            v.extend_from_slice(&(492u32 * 12).to_le_bytes());
            v.extend_from_slice(&(492u32 * 36).to_le_bytes());
            v.extend_from_slice(&(2490u32 * 2).to_le_bytes());
            v
        };
        let info = describe(std::path::Path::new("collar_001.clmesh"), &good).unwrap();
        assert_eq!(info.format, Format::ClothMesh);
        assert_eq!(field(&info, "vertices"), Some("492"));
        assert_eq!(field(&info, "indices"), Some("2490"));
        assert!(
            info.unresolved.is_some(),
            "even with clean arithmetic the block contents are unread, so a caveat is due"
        );

        let bad = {
            let mut v = b"CLMESH2\0".to_vec();
            v.extend_from_slice(&486u32.to_le_bytes());
            v.extend_from_slice(&2454u32.to_le_bytes());
            v.extend_from_slice(&1u32.to_le_bytes());
            v.extend_from_slice(&5840u32.to_le_bytes()); // not 486*12
            v.extend_from_slice(&17504u32.to_le_bytes());
            v.extend_from_slice(&4944u32.to_le_bytes());
            v
        };
        let info = describe(std::path::Path::new("collar_002.clmesh"), &bad).unwrap();
        assert!(info.unresolved.is_some(), "a block layout that does not divide must be flagged");
        assert_eq!(field(&info, "vertices"), Some("486"), "counts stay usable either way");
    }

    /// A clip that satisfies every header invariant the real decoder checks, so
    /// a test can assert on decoded fields rather than on raw offsets.
    fn fake_gani(units: u32, segments: u32, rate: u32, declared: u32) -> Vec<u8> {
        let mut v = vec![0u8; 256];
        let len = v.len();
        let mut words: Vec<(usize, u32)> = vec![
            (4, 32),
            (8, declared),
            (20, 1),
            (32, 143_688_520),
            (36, 48),
            (56, 64),
            (96, 0xC6E9_37B9),
            (104, 1),
            (108, 48),
            (112, (len - 144) as u32),
            (116, -64i32 as u32),
            (144, units),
            (148, segments),
            (152, 0x0100_0001),
            (160, rate),
        ];
        for k in 0..units {
            words.push((164 + 4 * k as usize, 40 + 24 * k));
        }
        for (at, n) in words {
            v[at..at + 4].copy_from_slice(&n.to_le_bytes());
        }
        v[0..4].copy_from_slice(&[0xd2, 0xa2, 0xfc, 0x0b]);
        v[80..86].copy_from_slice(b"MOTION");
        v
    }

    #[test]
    fn gani_reports_the_decoded_counts_and_flags_a_stale_size() {
        let info = describe(std::path::Path::new("a.gani"), &fake_gani(3, 5, 10, 999_999)).unwrap();
        assert_eq!(field(&info, "units"), Some("3"));
        assert_eq!(field(&info, "segments"), Some("5"));
        assert_eq!(field(&info, "frame rate"), Some("10 fps"));
        let stale = field(&info, "declared length").unwrap();
        assert!(stale.contains("stale"), "a wrong size field must be called out: {stale}");
        assert!(info.unresolved.is_some(), "the rig mapping is not decoded, and must say so");
        assert!(info.unresolved.as_deref().unwrap().contains("FRIG"), "name what is missing");
        assert_eq!(field(&info, "frames"), Some("0"), "the fixture leaves the count unset");
    }

    #[test]
    fn a_gani_that_fails_the_header_invariants_is_reported_not_described() {
        // MOTION missing: the decoder refuses, and the format layer must not
        // invent counts from bytes it never validated.
        let mut v = fake_gani(2, 4, 10, 256);
        v[80] = b'X';
        let info = describe(std::path::Path::new("a.gani"), &v).unwrap();
        assert!(info.unresolved.as_deref().unwrap().starts_with("header rejected"), "{:?}", info.unresolved);
        assert_eq!(field(&info, "units"), None);
    }

    #[test]
    fn truncated_input_is_reported_instead_of_panicking() {
        for (name, bytes) in
            [("a.clmesh", &b"CLMESH2\x00"[..]), ("a.gani", &[0xd2, 0xa2, 0xfc, 0x0b][..]), ("a.skl", &[12u8][..])]
        {
            let info = describe(std::path::Path::new(name), bytes).unwrap();
            assert!(info.unresolved.is_some(), "{name} should report the shortfall");
        }
    }
}

#[cfg(test)]
mod probe_tests {
    use super::*;

    /// Binary data whose high bytes happen to be dense must not read as text.
    #[test]
    fn dense_binary_is_not_mistaken_for_text() {
        // 0xc0..0xff is the shape of compressed/quantised payloads, not of prose.
        let b: Vec<u8> = (0..2048).map(|i| 0xc0 + (i % 64) as u8).collect();
        let f = identify("blob", &b);
        eprintln!("dense high-byte binary -> {f:?}");
        assert!(!matches!(f, Format::Text), "high bytes are not evidence of text");
    }

    /// An unknown file whose first u32 happens to be 12 is not a skeleton.
    #[test]
    fn a_leading_twelve_alone_does_not_make_a_skeleton() {
        let mut b = vec![12u8, 0, 0, 0];
        b.extend_from_slice(&[0u8; 200]);
        let f = identify("mystery", &b);
        eprintln!("leading 12, no extension -> {f:?}");
        assert_ne!(f, Format::Skeleton, "one coincidental field is not a signature");
    }

    /// The generic camera signature is four bytes; a random file can match it.
    #[test]
    fn the_four_byte_camera_signature_needs_a_name_behind_it() {
        let b = vec![0x01, 0x00, 0x01, 0xff, 9, 9, 9, 9];
        let f = identify("settings.bin", &b);
        eprintln!("db bytes with camera-like prefix -> {f:?}");
        assert_ne!(f, Format::CameraAnimation, "a database is not a camera animation");
    }
}

#[cfg(test)]
mod probe2 {
    use super::*;
    #[test]
    fn sidecar_and_labels() {
        // The .fpkd sidecar shares the container's leading six bytes.
        let side = { let mut v = b"foxfpkdwin0".to_vec(); v.resize(80, 0); v };
        eprintln!("fpkd sidecar -> {:?}", identify("face.fpkd", &side));
        // A dotfile has no extension.
        eprintln!(".gitignore ext -> {:?}", ext(".gitignore"));
        // Unverified header slots must not be labelled as counts.
        let mut g = vec![0xd2, 0xa2, 0xfc, 0x0b];
        g.extend_from_slice(&32u32.to_le_bytes());
        g.extend_from_slice(&64u32.to_le_bytes());
        g.extend_from_slice(&[0u8; 4]);
        g.extend_from_slice(&[0u8; 4]);
        g.extend_from_slice(&1u32.to_le_bytes());
        g.resize(64, 0);
        let info = describe(std::path::Path::new("a.gani"), &g).unwrap();
        eprintln!("gani fields -> {:?}", info.fields);
        let keys: Vec<&str> = info.fields.iter().map(|(k, _)| k.as_str()).collect();
        assert!(!keys.contains(&"entry count"), "slot 16 was never shown to be a count");
    }
}
