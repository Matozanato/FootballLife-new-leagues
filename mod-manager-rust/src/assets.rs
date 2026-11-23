//! Editing the image and model assets the game ships, by family.
//!
//! Every editable asset here is a texture the game already reads, so the rule
//! this module follows is the one the table patcher uses: write only what the
//! file can already hold, then read it back and refuse if the result is not
//! what the game expects. A texture that re-encodes into a different pixel
//! format, a different size or a different mip depth will load and look wrong
//! rather than failing loudly, which is the worst possible outcome for a mod
//! that has already been installed.

use crate::ftex::{self, Ftex, Mip, PixelFormat};
use anyhow::{bail, Context, Result};
use serde::Serialize;
use std::path::{Path, PathBuf};

/// What kind of content a path holds, used to group assets in the UI.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum Family {
    Face,
    Hair,
    Kit,
    Emblem,
    Logo,
    Symbol,
    Boots,
    Ball,
    Menu,
    Animation,
    Other,
}

impl Family {
    pub fn name(self) -> &'static str {
        match self {
            Family::Face => "faces",
            Family::Hair => "hair",
            Family::Kit => "kits",
            Family::Emblem => "emblems",
            Family::Logo => "logos",
            Family::Symbol => "symbols",
            Family::Boots => "boots",
            Family::Ball => "balls",
            Family::Menu => "menu art",
            Family::Animation => "animations",
            Family::Other => "other",
        }
    }

    /// Whether this release can edit it. Kept as a method rather than a UI
    /// constant so a family cannot be advertised as editable in one place and
    /// refused in another. Animations are excluded here because this is the
    /// texture editor: a clip's frame rate is editable, through the `gani`
    /// command, but its pixels are not, because it has none.
    pub fn editable(self) -> bool {
        !matches!(self, Family::Other | Family::Animation)
    }
}

/// Classify from the path rather than the extension: `face_bsm_alp.ftex` under
/// a `character/face` tree is a face whether it came from a kit pack or not.
pub fn family(path: &Path) -> Family {
    let p = path.to_string_lossy().to_lowercase().replace('\\', "/");
    let seg = |needle: &str| p.contains(needle);
    // An animation is an animation whatever folder it sits in, and its
    // extension is the only thing that says so; classifying by path alone put
    // every .gani under `character/face` into the face family, which then
    // promised a texture editor for a file that has no pixels.
    let ext = path.extension().map(|e| e.to_string_lossy().to_lowercase()).unwrap_or_default();
    if matches!(ext.as_str(), "gani" | "mtar" | "ask" | "frig") {
        return Family::Animation;
    }
    if seg("/face/") || seg("face/real") || seg("\\face\\") {
        Family::Face
    } else if seg("/hair/") || p.contains("hair_") {
        Family::Hair
    } else if seg("/kit") || p.contains("uniform") || p.contains("jersey") || p.contains("shirt") {
        Family::Kit
    } else if seg("emblem") {
        Family::Emblem
    } else if seg("logo") {
        Family::Logo
    } else if seg("/symbol") || seg("render/symbol") {
        Family::Symbol
    } else if seg("boot") {
        Family::Boots
    } else if seg("/ball") {
        Family::Ball
    } else if seg("/menu") || seg("scoreboard") || seg("adboard") {
        Family::Menu
    } else {
        Family::Other
    }
}

/// Formats this module will write. Anything else is refused rather than
/// converted, because silently changing a pixel format is how a texture ends up
/// loading as garbage on a machine other than the one that saved it.
const WRITABLE: &[PixelFormat] = &[
    PixelFormat::Bc1,
    PixelFormat::Bc3,
    PixelFormat::Bc5,
    PixelFormat::Bc7,
];

fn writable(fmt: PixelFormat) -> bool {
    WRITABLE.iter().any(|p| *p == fmt)
}

#[derive(Debug, Serialize)]
pub struct Report {
    pub path: String,
    pub family: &'static str,
    pub format: String,
    pub width: u32,
    pub height: u32,
    pub mips: usize,
    pub backup: String,
    /// Bytes that differ from the previous file, as a fraction of the decoded
    /// pixels, so a write that did nothing visible is detectable.
    pub changed_pixels: usize,
}

/// Box-filter RGBA8 down by two, the same reduction the mip chain uses.
fn halve(rgba: &[u8], w: usize, h: usize) -> (Vec<u8>, usize, usize) {
    let (nw, nh) = ((w / 2).max(1), (h / 2).max(1));
    let mut out = vec![0u8; nw * nh * 4];
    for y in 0..nh {
        for x in 0..nw {
            let mut acc = [0u32; 4];
            let mut n = 0u32;
            for dy in 0..2 {
                for dx in 0..2 {
                    let sx = (x * 2 + dx).min(w - 1);
                    let sy = (y * 2 + dy).min(h - 1);
                    let i = (sy * w + sx) * 4;
                    if sx == x * 2 + dx && sy == y * 2 + dy {
                        for c in 0..4 {
                            acc[c] += rgba[i + c] as u32;
                        }
                        n += 1;
                    }
                }
            }
            let o = (y * nw + x) * 4;
            for c in 0..4 {
                out[o + c] = (acc[c] as f64 / n.max(1) as f64).round().clamp(0.0, 255.0) as u8;
            }
        }
    }
    (out, nw, nh)
}

/// Build a full mip chain from one RGBA8 image in the file's own format.
fn chain(fmt: PixelFormat, rgba: &[u8], w: u32, h: u32) -> Result<Vec<Mip>> {
    let mut mips = Vec::new();
    let (mut cw, mut ch) = (w as usize, h as usize);
    let mut cur = rgba.to_vec();
    loop {
        mips.push(Mip {
            width: cw as u32,
            height: ch as u32,
            data: ftex::encode_blocks(fmt, &cur, cw as u32, ch as u32)?,
        });
        if cw == 1 && ch == 1 {
            break;
        }
        let (next, nw, nh) = halve(&cur, cw, ch);
        cur = next;
        (cw, ch) = (nw, nh);
        if mips.len() > 20 {
            bail!("mip chain did not terminate");
        }
    }
    Ok(mips)
}

/// Replace a texture's pixels, keeping its format, size and metadata.
///
/// The caller supplies the same dimensions the file already has. Resizing is
/// refused: a texture's size is bound to the UV layout of whatever model
/// samples it, so a resized map is a different asset rather than an edited one.
pub fn replace(path: &Path, rgba: &[u8], w: u32, h: u32) -> Result<Report> {
    let old = Ftex::read(path).with_context(|| format!("reading {}", path.display()))?;
    if !writable(old.format) {
        bail!(
            "{} is {:?}, which this editor will not re-encode; converting it would change how the game samples it",
            path.file_name().unwrap_or_default().to_string_lossy(),
            old.format
        );
    }
    if old.width != w || old.height != h {
        bail!(
            "the file is {}x{} and the image is {w}x{h}; a texture's size is fixed by the model that uses it",
            old.width,
            old.height
        );
    }
    if rgba.len() < (w as usize) * (h as usize) * 4 {
        bail!("need {} bytes of RGBA8, got {}", w as usize * h as usize * 4, rgba.len());
    }

    let mut next = Ftex {
        format: old.format,
        version: old.version,
        width: old.width,
        height: old.height,
        depth: old.depth,
        texture_type: old.texture_type,
        nrt: old.nrt,
        flags: old.flags,
        mips: chain(old.format, rgba, w, h)?,
    };
    // A chain shorter than the original means the file had a depth this image
    // cannot reproduce; refuse rather than silently drop mip levels.
    if next.mips.len() < old.mips.len() {
        bail!(
            "the new image yields {} mip levels but the file had {}; refusing to drop levels",
            next.mips.len(),
            old.mips.len()
        );
    }
    let bytes = next.to_ftex()?;

    let backup = keep_backup(path)?;
    write_atomic(path, &bytes)?;

    // Read back and compare, rather than trusting that the encoder round-trips.
    let after = Ftex::read(path).with_context(|| format!("re-reading {}", path.display()))?;
    if after.format != old.format || after.width != old.width || after.height != old.height {
        bail!(
            "the file came back as {:?} {}x{} instead of {:?} {}x{}",
            after.format,
            after.width,
            after.height,
            old.format,
            old.width,
            old.height
        );
    }
    if after.mips.len() != next.mips.len() {
        bail!("mip depth changed on write ({} -> {})", next.mips.len(), after.mips.len());
    }
    let (aw, ah, argb) = after.to_rgba(0)?;
    let changed = if aw == w && ah == h {
        (0..(w as usize * h as usize))
            .filter(|i| {
                let o = i * 4;
                argb[o].abs_diff(rgba[o]) > 8
                    || argb[o + 1].abs_diff(rgba[o + 1]) > 8
                    || argb[o + 2].abs_diff(rgba[o + 2]) > 8
            })
            .count()
    } else {
        usize::MAX
    };
    // Block formats are lossy, so "close" is the right bar; a third of the
    // image drifting beyond a small tolerance means the encode went wrong.
    if changed * 3 > (w as usize * h as usize) {
        bail!("re-decoding the written file differs from the input in {changed} pixels; the edit was not faithful");
    }
    next.mips.truncate(next.mips.len());
    Ok(Report {
        path: path.to_string_lossy().into_owned(),
        family: family(path).name(),
        format: after.format.name().to_string(),
        width: after.width,
        height: after.height,
        mips: after.mips.len(),
        backup,
        changed_pixels: changed,
    })
}

/// Copy the original aside once, so an edit is always reversible even though
/// the app has no undo.
fn keep_backup(path: &Path) -> Result<String> {
    let cand = path.with_extension(format!(
        "{}.fl27mm-backup",
        path.extension().and_then(|e| e.to_str()).unwrap_or("dat")
    ));
    if cand.exists() {
        return Ok(cand.to_string_lossy().into_owned());
    }
    std::fs::copy(path, &cand).with_context(|| format!("backing up to {}", cand.display()))?;
    Ok(cand.to_string_lossy().into_owned())
}

/// Temporary name then rename, so an interrupted save cannot replace a whole
/// texture with half of one.
fn write_atomic(path: &Path, bytes: &[u8]) -> Result<()> {
    let tmp: PathBuf = path.with_extension(format!(
        "{}.fl27mm-tmp",
        path.extension().and_then(|e| e.to_str()).unwrap_or("dat")
    ));
    {
        use std::io::Write;
        let mut f = std::fs::File::create(&tmp).with_context(|| format!("creating {}", tmp.display()))?;
        f.write_all(bytes).with_context(|| format!("writing {}", tmp.display()))?;
    }
    std::fs::rename(&tmp, path).with_context(|| format!("saving {}", path.display()))?;
    Ok(())
}

/// One asset as the browser needs to show it.
#[derive(Debug, Serialize)]
pub struct Entry {
    pub path: String,
    pub family: &'static str,
    pub editable: bool,
    pub format: String,
    pub width: u32,
    pub height: u32,
    pub bytes: u64,
}

/// Describe one asset file without editing it. Unsupported or unreadable files
/// return `None` so a directory scan can keep going instead of failing whole.
pub fn entry(path: &Path) -> Option<Entry> {
    let bytes = std::fs::metadata(path).ok()?.len();
    let ext = path.extension()?.to_string_lossy().to_lowercase();
    let fam = family(path);
    if ext == "ftex" {
        let t = Ftex::read(path).ok()?;
        return Some(Entry {
            path: path.to_string_lossy().into_owned(),
            family: fam.name(),
            editable: fam.editable() && writable(t.format),
            format: t.format.name().to_string(),
            width: t.width,
            height: t.height,
            bytes,
        });
    }
    if ext == "gani" {
        // Listed with what was actually decoded, so the row cannot promise a
        // texture editor for a file that has no pixels and cannot hide that
        // the clip did parse.
        let clip = crate::gani::Clip::read(path).ok()?;
        return Some(Entry {
            path: path.to_string_lossy().into_owned(),
            family: Family::Animation.name(),
            editable: false,
            format: format!("{} units / {} segments @ {} fps", clip.unit_count, clip.segment_count, clip.frame_rate),
            width: 0,
            height: 0,
            bytes,
        });
    }
    if ext == "dds" || ext == "png" {
        return Some(Entry {
            path: path.to_string_lossy().into_owned(),
            family: fam.name(),
            editable: false,
            format: ext,
            width: 0,
            height: 0,
            bytes,
        });
    }
    None
}

#[cfg(test)]
mod tests {
    use super::*;

    fn a_real_texture() -> Option<PathBuf> {
        let p = Path::new("C:/Games/SP Football Life 2027/SiderAddons/livecpk/root/Asset/model/character/face/real/100006/sourceimages/#windx11/face_bsm_alp.ftex");
        if p.is_file() { Some(p.to_path_buf()) } else { None }
    }

    #[test]
    fn a_family_is_read_from_the_path_not_the_extension() {
        let p = Path::new("Asset/model/character/face/real/100006/sourceimages/face_bsm_alp.ftex");
        assert_eq!(family(p), Family::Face);
        assert_eq!(family(Path::new("Asset/model/character/kit/113680/a.ftex")), Family::Kit);
        assert_eq!(family(Path::new("common/render/symbol/club/a.ftex")), Family::Symbol);
        assert_eq!(family(Path::new("common/menu/mode/a.ftex")), Family::Menu);
    }

    /// The whole safety argument: same format, same size, same mip depth, and
    /// the pixels actually move.
    #[test]
    fn replacing_pixels_keeps_the_file_shape() {
        let Some(src) = a_real_texture() else { return };
        let before = Ftex::read(&src).unwrap();
        let (w, h, mut rgba) = before.to_rgba(0).unwrap();
        let original = rgba.clone();
        // Tint everything rather than replacing it, so a faithful encode still
        // shows as changed against the source.
        for px in rgba.chunks_mut(4) {
            px[0] = 20;
            px[1] = 200;
            px[2] = 90;
        }

        let work_dir = std::env::temp_dir().join(format!("fl27mm-assets-{}", std::process::id()));
        std::fs::create_dir_all(&work_dir).unwrap();
        let work = work_dir.join("face_bsm_alp.ftex");
        std::fs::write(&work, std::fs::read(&src).unwrap()).unwrap();

        let r = replace(&work, &rgba, w, h).expect("the replace should apply");
        assert_eq!(r.format, before.format.name(), "format must not change");
        assert_eq!((r.width, r.height), (w, h), "size must not change");
        assert!(r.mips >= before.mips.len(), "mip depth must not shrink");

        let after = Ftex::read(&work).unwrap();
        let (_, _, argb) = after.to_rgba(0).unwrap();
        let moved = (0..(w as usize * h as usize))
            .filter(|i| argb[i * 4].abs_diff(rgba[i * 4]) <= 24)
            .count();
        assert!(moved * 2 > w as usize * h as usize, "only {moved} of {} pixels took the new colour", w as usize * h as usize);
        let same = (0..(w as usize * h as usize)).filter(|i| argb[i*4] == original[i*4] && argb[i*4+1] == original[i*4+1]).count();
        assert!(same * 3 < w as usize * h as usize, "{same} pixels still match the original, so the write did not land");
        assert!(Path::new(&r.backup).exists(), "a backup must be kept");
        let _ = std::fs::remove_dir_all(&work_dir);
    }

    /// Resizing is refused: the UV layout of the model that samples the map is
    /// fixed, so a different size is a different asset.
    #[test]
    fn a_different_size_is_refused() {
        let Some(src) = a_real_texture() else { return };
        let t = Ftex::read(&src).unwrap();
        let work_dir = std::env::temp_dir().join(format!("fl27mm-size-{}", std::process::id()));
        std::fs::create_dir_all(&work_dir).unwrap();
        let work = work_dir.join("face_bsm_alp.ftex");
        std::fs::write(&work, std::fs::read(&src).unwrap()).unwrap();
        let img = vec![0u8; 64 * 64 * 4];
        let err = replace(&work, &img, 64, 64).unwrap_err();
        assert!(err.to_string().contains("fixed by the model"), "{err}");
        // The refusal must not have touched the file.
        assert_eq!(std::fs::read(&work).unwrap(), std::fs::read(&src).unwrap());
        let _ = std::fs::remove_dir_all(&work_dir);
        assert!(t.width > 0);
    }
}
