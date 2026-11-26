//! Software rasteriser for `FMDL` meshes, so a decoded head can be looked at.
//!
//! The point of this module is that a head is a 3D object and every other
//! preview in the app is a flat image. The real triangles, the real normals and
//! the real UVs are drawn into an RGBA buffer with a depth test, from any
//! angle, with no GPU and no dependencies beyond what the core already has.
//! This is also the only way to see whether a morph changed a shape rather than
//! merely re-skinning it.
//!
//! ## Framing and projection
//!
//! FL27 heads sit in world coordinates with **+y up** and the skull around
//! y = 1.7, so the model is centred on its own bounds and divided by its own
//! radius. Every head therefore fills the frame whatever units it was authored
//! in -- and a head that decoded wrong shows up as a shapeless smear instead of
//! quietly fitting in, which is the useful direction of that trade.
//!
//! Projection is weak perspective, a single divide by `(focal - z)`, which
//! gives a nose its overlap of a cheek without applying a wide field of view to
//! a 240 mm object.

use crate::fmdl::{Fmdl, Mesh, V3};

/// Where the camera sits: `yaw` spins around the vertical axis, `pitch` tips
/// over, both in radians.
#[derive(Debug, Clone, Copy)]
pub struct Camera {
    pub yaw: f32,
    pub pitch: f32,
    pub zoom: f32,
}

impl Camera {
    /// Facing the face, just above eye line -- how a portrait is taken.
    pub fn front() -> Camera {
        Camera { yaw: 0.0, pitch: -0.12, zoom: 1.0 }
    }
    pub fn three_quarter() -> Camera {
        Camera { yaw: 0.62, pitch: -0.12, zoom: 1.0 }
    }
    pub fn profile() -> Camera {
        Camera { yaw: std::f32::consts::FRAC_PI_2, pitch: -0.05, zoom: 1.0 }
    }
    /// Looking at the back of the skull. This is the view that exposes a head
    /// assembled from only part of its files.
    pub fn back() -> Camera {
        Camera { yaw: std::f32::consts::PI, pitch: -0.12, zoom: 1.0 }
    }

    pub fn top() -> Camera {
        Camera { yaw: 0.0, pitch: -1.35, zoom: 1.0 }
    }
}

/// What each pixel's colour comes from.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Mode {
    /// Donor texture, lit. Falls back to `Lambert` when no texture is given.
    Textured,
    /// Flat grey lit only by the vertex normals: shows shape with no skin to
    /// hide it behind.
    Lambert,
    /// View-space normals as RGB -- the direct check that the normal channel
    /// and the reshape agree with each other.
    Normals,
}

pub struct Texture<'a> {
    pub rgba: &'a [u8],
    pub w: usize,
    pub h: usize,
}

/// Model-to-view transform plus the framing that makes any head fit the frame.
struct View {
    cy: f32,
    sy: f32,
    cp: f32,
    sp: f32,
    centre: V3,
    scale: f32,
}

const FOCAL: f32 = 3.2;

impl View {
    fn new(cam: &Camera, centre: V3, radius: f32) -> View {
        View {
            cy: cam.yaw.cos(),
            sy: cam.yaw.sin(),
            cp: cam.pitch.cos(),
            sp: cam.pitch.sin(),
            centre,
            // 0.62 of the half-diagonal leaves a margin so the jaw and crown
            // are never cropped by the frame edge.
            scale: (radius.max(1e-5) * 0.62 * cam.zoom.max(0.1)).max(1e-5),
        }
    }

    /// Into view space: +x right, +y up, +z toward the camera.
    fn project(&self, p: V3) -> V3 {
        let q = p.sub(self.centre).scale(1.0 / self.scale);
        let x = q.x * self.cy + q.z * self.sy;
        let z = -q.x * self.sy + q.z * self.cy;
        let y2 = q.y * self.cp - z * self.sp;
        let z2 = q.y * self.sp + z * self.cp;
        V3::new(x, y2, z2)
    }

    /// Rotate a direction only -- no translation, no scaling.
    fn direction(&self, n: V3) -> V3 {
        let x = n.x * self.cy + n.z * self.sy;
        let z = -n.x * self.sy + n.z * self.cy;
        let y2 = n.y * self.cp - z * self.sp;
        let z2 = n.y * self.sp + z * self.cp;
        V3::new(x, y2, z2)
    }

    /// View-space point to screen, with weak perspective folded in.
    fn to_screen(&self, v: V3, w: usize, h: usize) -> (f32, f32) {
        let s = FOCAL / (FOCAL - v.z).max(0.25);
        (
            (v.x * s * 0.5 + 0.5) * w as f32,
            (0.5 - v.y * s * 0.5) * h as f32,
        )
    }
}

/// Open a head from a face container, a loose mesh, or a donor folder.
///
/// Shared by the CLI and the desktop app so neither can disagree about what
/// "open a head" resolves to.
pub fn load_any(path: &std::path::Path) -> anyhow::Result<Fmdl> {
    use crate::fmdl::Fmdl;
    use crate::fpk::Fpk;
    use anyhow::{bail, Context};
    if path.is_dir() {
        // A face folder: take the container that holds the biggest mesh.
        let mut best: Option<(usize, Vec<u8>)> = None;
        for p in crate::fsutil::files(path) {
            if p.extension().and_then(|e| e.to_str()).map(|s| s.to_lowercase()) != Some("fpk".into()) {
                continue;
            }
            let Ok(c) = Fpk::read(&p) else { continue };
            for e in c.entries {
                if e.data.len() > 64 && &e.data[0..4] == b"FMDL" && e.data.len() > best.as_ref().map(|(n, _)| *n).unwrap_or(0) {
                    best = Some((e.data.len(), e.data));
                }
            }
        }
        let (_n, bytes) = best.context("no FMDL mesh in that folder")?;
        return Fmdl::parse(bytes).context("parsing the head mesh in that folder");
    }
    let bytes = std::fs::read(path).with_context(|| format!("reading {}", path.display()))?;
    if bytes.len() > 64 && &bytes[0..4] == b"FMDL" {
        return Fmdl::parse(bytes).with_context(|| format!("parsing {}", path.display()));
    }
    let container = Fpk::parse(&bytes).with_context(|| format!("reading {}", path.display()))?;
    for name in ["face_high.fmdl", "face.fmdl"] {
        if let Some(e) = container.find(name) {
            return Fmdl::parse(e.data.clone()).with_context(|| format!("parsing {name}"));
        }
    }
    for e in &container.entries {
        if e.data.len() > 64 && &e.data[0..4] == b"FMDL" {
            return Fmdl::parse(e.data.clone()).with_context(|| format!("parsing {}", e.name));
        }
    }
    bail!("{} holds no FMDL mesh", path.display())
}

/// The donor's own skin map, if the folder has one: the biggest bsm texture.
pub fn skin_for(model_path: &std::path::Path) -> Option<(Vec<u8>, usize, usize)> {
    use crate::ftex::Ftex;
    let dir = if model_path.is_dir() {
        model_path.to_path_buf()
    } else {
        model_path.parent()?.parent()?.to_path_buf()
    };
    let mut best: Option<(usize, std::path::PathBuf)> = None;
    for p in crate::fsutil::files(&dir) {
        let name = p.file_name()?.to_string_lossy().to_lowercase();
        if !name.contains("bsm") || p.extension().and_then(|e| e.to_str()) != Some("ftex") {
            continue;
        }
        let len = std::fs::metadata(&p).map(|m| m.len()).unwrap_or(0) as usize;
        if len > best.as_ref().map(|(n, _)| *n).unwrap_or(0) {
            best = Some((len, p));
        }
    }
    let (_, path) = best?;
    let tex = Ftex::read(&path).ok()?;
    let (w, h, rgba) = tex.to_rgba(0).ok()?;
    Some((rgba, w as usize, h as usize))
}

/// Bounds, centre and framing radius of every vertex in the file.
pub fn extents(model: &Fmdl) -> Option<(V3, V3, V3, f32)> {
    let mut lo = V3::new(f32::MAX, f32::MAX, f32::MAX);
    let mut hi = V3::new(f32::MIN, f32::MIN, f32::MIN);
    let mut any = false;
    for m in &model.meshes {
        for p in &m.positions {
            any = true;
            lo = V3::new(lo.x.min(p.x), lo.y.min(p.y), lo.z.min(p.z));
            hi = V3::new(hi.x.max(p.x), hi.y.max(p.y), hi.z.max(p.z));
        }
    }
    if !any {
        return None;
    }
    let centre = V3::new((lo.x + hi.x) * 0.5, (lo.y + hi.y) * 0.5, (lo.z + hi.z) * 0.5);
    let radius = V3::new(hi.x - lo.x, hi.y - lo.y, hi.z - lo.z).norm() * 0.5;
    Some((lo, hi, centre, radius))
}

/// The donor map with a mip pyramid, built once per render.
///
/// Sampling a 1024 skin into a 400 px frame with nearest look-alike noise: every
/// pixel picks whichever texel its centre lands on, so fine stubble and pore
/// detail shimmers into a grey mush. Mips plus trilinear filtering average the
/// right amount of the map per pixel, which is the single biggest quality jump
/// available here.
#[derive(Debug, Clone)]
pub struct Skin {
    levels: Vec<Vec<f32>>,
    w: usize,
    h: usize,
}

fn srgb_to_linear(c: f32) -> f32 {
    if c <= 0.04045 { c / 12.92 } else { ((c + 0.055) / 1.055).powf(2.4) }
}

fn linear_to_srgb(c: f32) -> f32 {
    let v = c.clamp(0.0, 1.0);
    if v <= 0.0031308 { v * 12.92 } else { 1.055 * v.powf(1.0 / 2.4) - 0.055 }
}

impl Skin {
    /// Build the pyramid. Levels are stored linear-light, one float per channel
    /// interleaved RGBA.
    pub fn new(tex: &Texture) -> Skin {
        let w = tex.w.max(1);
        let h = tex.h.max(1);
        let base: Vec<f32> = tex.rgba.chunks(4).take(w * h).flat_map(|q| {
            [
                srgb_to_linear(q[0] as f32 / 255.0),
                srgb_to_linear(q[1] as f32 / 255.0),
                srgb_to_linear(q[2] as f32 / 255.0),
                q[3] as f32 / 255.0,
            ]
        }).collect();
        let mut levels = vec![base];
        loop {
            let (pw, ph) = {
                let last = levels.last().unwrap();
                (last.len() / (w * h), 0usize)
            };
            let _ = pw; let _ = ph;
            let (cw, ch) = {
                let i = levels.len() - 1;
                let mut cw = w >> i; let mut ch = h >> i;
                if cw == 0 { cw = 1 } if ch == 0 { ch = 1 }
                (cw, ch)
            };
            if cw <= 1 && ch <= 1 { break; }
            let src = levels.last().unwrap();
            let nw = (cw / 2).max(1);
            let nh = (ch / 2).max(1);
            let mut dst = vec![0f32; nw * nh * 4];
            for y in 0..nh {
                for x in 0..nw {
                    let sx = (x * 2).min(cw - 1);
                    let sy = (y * 2).min(ch - 1);
                    let tx = (sx + 1).min(cw - 1);
                    let ty = (sy + 1).min(ch - 1);
                    // Colour is averaged weighted by coverage, alpha plainly.
                    // A plain average is what made hair render as pale slabs:
                    // `hair_parts_bsm_alp` puts 72% of its texels in the
                    // lowest alpha octile and their RGB is not black, so every
                    // mip level was dominated by colour that belongs to no
                    // strand, and any texel filtered down from one read as a
                    // white highlight. Fully transparent blocks contribute
                    // nothing but their alpha.
                    let mut acc = [0f32; 4];
                    let mut wsum = 0f32;
                    for (px, py) in [(sx, sy), (tx, sy), (sx, ty), (tx, ty)] {
                        let i = (py * cw + px) * 4;
                        let cov = src[i + 3];
                        for c in 0..3 {
                            acc[c] += src[i + c] * cov;
                        }
                        acc[3] += cov;
                        wsum += cov;
                    }
                    let o = (y * nw + x) * 4;
                    for c in 0..3 {
                        dst[o + c] = if wsum > 0.0 { acc[c] / wsum } else {
                            // Nothing here is covered; keep a colour so a later
                            // level does not divide by zero, but it will be
                            // clipped before it reaches the screen.
                            src[(sy * cw + sx) * 4 + c]
                        };
                    }
                    dst[o + 3] = acc[3] * 0.25;
                }
            }
            levels.push(dst);
        }
        Skin { levels, w, h }
    }

    /// Fox UVs run outside 0..1 on wrapped islands, so repeat rather than clamp:
    /// clamping smears one edge colour across every tile.
    fn wrap(x: f32) -> f32 {
        let f = x - x.floor();
        if f < 0.0 { 0.0 } else if f >= 1.0 { 0.999999 } else { f }
    }

    fn bilinear(&self, level: usize, u: f32, v: f32, out: &mut [f32; 4]) {
        let lvl = self.levels[level].as_slice();
        let cw = (self.w >> level).max(1);
        let ch = (self.h >> level).max(1);
        let fx = (Self::wrap(u) * cw as f32 - 0.5).max(0.0);
        let fy = (Self::wrap(v) * ch as f32 - 0.5).max(0.0);
        let x0 = (fx.floor() as usize).min(cw - 1);
        let y0 = (fy.floor() as usize).min(ch - 1);
        let x1 = (x0 + 1).min(cw - 1);
        let y1 = (y0 + 1).min(ch - 1);
        let tx = fx - x0 as f32;
        let ty = fy - y0 as f32;
        for c in 0..4 {
            let a = lvl[(y0 * cw + x0) * 4 + c];
            let b = lvl[(y0 * cw + x1) * 4 + c];
            let d = lvl[(y1 * cw + x0) * 4 + c];
            let e = lvl[(y1 * cw + x1) * 4 + c];
            out[c] = (a * (1.0 - tx) + b * tx) * (1.0 - ty) + (d * (1.0 - tx) + e * tx) * ty;
        }
    }

    /// Trilinear fetch in linear light. lod is the level of detail in mip
    /// units, so a texel covering 2.3 screen pixels blends levels 2 and 3.
    pub fn fetch(&self, u: f32, v: f32, lod: f32) -> [f32; 4] {
        let l = lod.clamp(0.0, (self.levels.len() - 1) as f32);
        let i0 = l.floor() as usize;
        let i1 = (i0 + 1).min(self.levels.len() - 1);
        let f = l - i0 as f32;
        let mut a = [0f32; 4];
        let mut b = [0f32; 4];
        self.bilinear(i0, u, v, &mut a);
        self.bilinear(i1, u, v, &mut b);
        if f <= 0.0 { return a; }
        if f >= 1.0 { return b; }
        let mut o = [0f32; 4];
        for c in 0..4 { o[c] = a[c] * (1.0 - f) + b[c] * f; }
        o
    }

    pub fn levels(&self) -> usize { self.levels.len() }
}

/// How many map texels one screen pixel covers, per triangle. This is the
/// texture gradient the mip level comes from; taking it per triangle rather than
/// per pixel keeps it stable and costs nothing.
fn lod_for(uv: [[f32; 2]; 3], sx: [f32; 3], sy: [f32; 3], w: usize, h: usize) -> f32 {
    let area = ((sx[1] - sx[0]) * (sy[2] - sy[0]) - (sx[2] - sx[0]) * (sy[1] - sy[0])).abs() * 0.5;
    if area < 1e-6 { return 0.0; }
    let tu = (uv[1][0] - uv[0][0]) * (uv[2][1] - uv[0][1]) - (uv[2][0] - uv[0][0]) * (uv[1][1] - uv[0][1]);
    let tex_area = tu.abs() * (w as f32 * h as f32);
    if tex_area <= 1e-9 { return 0.0; }
    (tex_area / area).log2().max(0.0)
}

/// Studio-ish three-point light evaluated in **linear light**, with a tight
/// specular sheen and a warm rim.
///
/// Lighting in sRGB (the old way here) crushes skin: multiply a value that is
/// already gamma-encoded and the mid-tones go muddy while the highlights clip.
/// Doing the maths linearly and encoding once at the end is what makes the
/// cheeks read as skin rather than as a painted mask.
fn shade(n: V3, base: [f32; 4], spec: f32) -> [u8; 3] {
    // Key: high, front, camera-left.
    let key_dir = V3::new(-0.42, 0.55, 0.72).normalized();
    let key = n.dot(key_dir).max(0.0);
    // Cool sky fill from below-right, wide and soft.
    let fill_dir = V3::new(0.55, -0.35, 0.55).normalized();
    let fill = n.dot(fill_dir).max(0.0);
    // Back-side kicker that separates the silhouette.
    let rim = (1.0 - n.z.abs()).powf(2.4);

    // Blinn-Phong sheen: skin is a dielectric, so a small, bright, tight lobe
    // with the light's own colour, plus a broader oily one.
    let half_k = key_dir.add(V3::new(0.0, 0.0, 1.0)).normalized();
    let spec_k = n.dot(half_k).max(0.0).powf(48.0);
    let half_w = V3::new(-0.30, 0.40, 0.86).normalized().add(V3::new(0.0, 0.0, 1.0)).normalized();
    let spec_w = n.dot(half_w).max(0.0).powf(9.0);

    let diffuse = 0.10 + key * 0.86 + fill * 0.24;
    let mut r = base[0] * diffuse + spec_k * 0.16 * spec + spec_w * 0.055 * spec;
    let mut g = base[1] * diffuse + spec_k * 0.15 * spec + spec_w * 0.048 * spec;
    let mut b = base[2] * diffuse + spec_k * 0.13 * spec + spec_w * 0.040 * spec;
    // Warm rim, weighted by how red the skin already is so it suits any tone.
    let warm = rim * (0.16 + base[0] * 0.10) * spec;
    r += warm;
    g += warm * 0.62;
    b += warm * 0.48;
    // Subtle tone mapping so a hot nose does not clip to flat white.
    let tm = |c: f32| c / (1.0 + c * 0.22);
    [
        (linear_to_srgb(tm(r)) * 255.0).round().clamp(0.0, 255.0) as u8,
        (linear_to_srgb(tm(g)) * 255.0).round().clamp(0.0, 255.0) as u8,
        (linear_to_srgb(tm(b)) * 255.0).round().clamp(0.0, 255.0) as u8,
    ]
}

/// Grey clay for the untextured modes, lit by the same rig.
fn shade_clay(n: V3) -> [u8; 3] {
    shade(n, [0.42, 0.40, 0.385, 1.0], 1.0)
}

/// One triangle, already projected. The per-vertex normals are the authored
/// ones, rotated into view space; nothing is derived from winding.
struct Tri {
    sx: [f32; 3],
    sy: [f32; 3],
    sz: [f32; 3],
    /// 1 / perspective divide per corner, for correcting the attribute walk.
    iw: [f32; 3],
    uv: [[f32; 2]; 3],
    n: [V3; 3],
    /// Mip level for the whole triangle: cheap, stable, and enough at this size.
    lod: f32,
}

fn raster(
    out: &mut [u8],
    depth: &mut [f32],
    w: usize,
    h: usize,
    t: &Tri,
    mode: Mode,
    skin: Option<&Skin>,
    clip: u8,
    blend: f32,
    write_depth: bool,
) {
    let min_x = t.sx[0].min(t.sx[1]).min(t.sx[2]).floor().max(0.0) as usize;
    let max_x = (t.sx[0].max(t.sx[1]).max(t.sx[2]).ceil() as usize).min(w.saturating_sub(1));
    let min_y = t.sy[0].min(t.sy[1]).min(t.sy[2]).floor().max(0.0) as usize;
    let max_y = (t.sy[0].max(t.sy[1]).max(t.sy[2]).ceil() as usize).min(h.saturating_sub(1));
    if max_x < min_x || max_y < min_y {
        return;
    }
    let d = (t.sx[1] - t.sx[0]) * (t.sy[2] - t.sy[0]) - (t.sy[1] - t.sy[0]) * (t.sx[2] - t.sx[0]);
    if d.abs() < 1e-6 {
        return; // degenerate in screen space: nothing has area to cover
    }
    let inv = 1.0 / d;
    // Two-sided lighting is handled inside shade() by the ambient floor, not
    // by flipping: a surface pointing away from the camera should read dark,
    // which is what makes the silhouette look solid.
    for y in min_y..=max_y {
        for x in min_x..=max_x {
            let px = x as f32 + 0.5;
            let py = y as f32 + 0.5;
            let w0 = ((t.sx[1] - px) * (t.sy[2] - py) - (t.sy[1] - py) * (t.sx[2] - px)) * inv;
            let w1 = ((t.sx[2] - px) * (t.sy[0] - py) - (t.sy[2] - py) * (t.sx[0] - px)) * inv;
            let w2 = 1.0 - w0 - w1;
            if w0 < 0.0 || w1 < 0.0 || w2 < 0.0 {
                continue;
            }
            let z = w0 * t.sz[0] + w1 * t.sz[1] + w2 * t.sz[2];
            let i = y * w + x;
            if z <= depth[i] {
                continue;
            }
            if write_depth {
                depth[i] = z;
            }
            let n = V3::new(
                w0 * t.n[0].x + w1 * t.n[1].x + w2 * t.n[2].x,
                w0 * t.n[0].y + w1 * t.n[1].y + w2 * t.n[2].y,
                w0 * t.n[0].z + w1 * t.n[1].z + w2 * t.n[2].z,
            )
            .normalized();
            // Measured on the shipped head: the skin faces +z and the shell is
            // open, so a front view sees mostly backfaces. Shade them as if they
            // turned toward the light, but never rewrite the normal that
            // Normals mode reports -- that channel is the thing being checked.
            let ns = if n.z < 0.0 { n.scale(-1.0) } else { n };
            let o = i * 4;
            match mode {
                Mode::Normals => {
                    out[o] = ((n.x + 1.0) * 127.5) as u8;
                    out[o + 1] = ((n.y + 1.0) * 127.5) as u8;
                    out[o + 2] = ((n.z + 1.0) * 127.5) as u8;
                }
                Mode::Textured if skin.is_some() => {
                    let sk = skin.unwrap();
                    // Perspective-correct: dividing by the interpolated 1/w
                    // stops a forehead sliding sideways across the map when the
                    // head turns, which flat interpolation does visibly.
                    let iw = w0 * t.iw[0] + w1 * t.iw[1] + w2 * t.iw[2];
                    let aw = (w0 * t.iw[0]) / iw;
                    let bw = (w1 * t.iw[1]) / iw;
                    let cw = (w2 * t.iw[2]) / iw;
                    let uv = [
                        aw * t.uv[0][0] + bw * t.uv[1][0] + cw * t.uv[2][0],
                        aw * t.uv[0][1] + bw * t.uv[1][1] + cw * t.uv[2][1],
                    ];
                    let tex = sk.fetch(uv[0], uv[1], t.lod);
                    // Hair cards are quads whose map is mostly empty: measured
                    // across the install, `hair_parts_bsm_alp` puts 72% of its
                    // texels in the lowest alpha octile while its RGB there is
                    // not black, so the colour outside the strands is junk.
                    // Discarding those texels is what stops a card reading as a
                    // smeared plate. It is only safe now that the cards are
                    // drawn in a second pass: a discarded texel leaves the face
                    // that the opaque pass already put there, instead of a hole
                    // to background.
                    if clip > 0 && (tex[3] * 255.0) < clip as f32 {
                        continue;
                    }
                    let c = shade(ns, tex, if blend > 0.0 { 0.15 } else { 1.0 });
                    if blend > 0.0 {
                        // Hair cards are translucent layers, not opaque
                        // surfaces. Writing them opaque means whichever card
                        // the depth buffer favours wins the whole pixel, so a
                        // profile view shows solid plates instead of strands.
                        // Source-over with the texel's own coverage lets the
                        // cards accumulate, which is how they composite in
                        // game.
                        //
                        // Where nothing has been drawn yet there is no face to
                        // accumulate over, and source-over onto the black
                        // background only darkens the silhouette. Those
                        // fragments are written opaque.
                        let a = if out[o + 3] == 0 {
                            1.0
                        } else {
                            (tex[3] * blend).clamp(0.0, 1.0)
                        };
                        for ch in 0..3 {
                            let d = out[o + ch] as f32 / 255.0;
                            out[o + ch] = ((c[ch] as f32 / 255.0) * a + d * (1.0 - a))
                                .clamp(0.0, 1.0)
                                .mul_add(255.0, 0.5) as u8;
                        }
                    } else {
                        out[o..o + 3].copy_from_slice(&c);
                    }
                }
                // Lambert, and the clay stand-in when Textured was asked for
                // with no map to show.
                _ => {
                    let c = shade_clay(ns);
                    out[o..o + 3].copy_from_slice(&c);
                }
            }
            out[o + 3] = 255;
        }
    }
}

fn draw_mesh(
    out: &mut [u8],
    depth: &mut [f32],
    w: usize,
    h: usize,
    mesh: &Mesh,
    view: &View,
    mode: Mode,
    skin: Option<&Skin>,
    tex_wh: (usize, usize),
    clip: u8,
    blend: f32,
    write_depth: bool,
) -> usize {
    let mut drawn = 0;
    for t in mesh.indices.chunks(3) {
        if t.len() != 3 {
            continue;
        }
        let idx = [t[0] as usize, t[1] as usize, t[2] as usize];
        if idx.iter().any(|&i| i >= mesh.positions.len()) {
            continue;
        }
        let mut sx = [0.0f32; 3];
        let mut sy = [0.0f32; 3];
        let mut sz = [0.0f32; 3];
        let mut iw = [0.0f32; 3];
        let mut ok = true;
        for k in 0..3 {
            let v = view.project(mesh.positions[idx[k]]);
            if !v.x.is_finite() || !v.y.is_finite() || !v.z.is_finite() {
                ok = false;
                break;
            }
            let (px, py) = view.to_screen(v, w, h);
            sx[k] = px;
            sy[k] = py;
            sz[k] = v.z;
            iw[k] = (FOCAL - v.z).max(0.25) / FOCAL;
        }
        if !ok {
            continue;
        }
        let _ = &mesh.positions;
        let lod = lod_for([
            mesh.uv(idx[0], 0).unwrap_or([0.0, 0.0]),
            mesh.uv(idx[1], 0).unwrap_or([0.0, 0.0]),
            mesh.uv(idx[2], 0).unwrap_or([0.0, 0.0]),
        ], sx, sy, tex_wh.0, tex_wh.1);
        let tri = Tri {
            sx,
            sy,
            sz,
            iw,
            lod,
            uv: [
                mesh.uv(idx[0], 0).unwrap_or([0.0, 0.0]),
                mesh.uv(idx[1], 0).unwrap_or([0.0, 0.0]),
                mesh.uv(idx[2], 0).unwrap_or([0.0, 0.0]),
            ],
            n: [
                view.direction(mesh.normal(idx[0])),
                view.direction(mesh.normal(idx[1])),
                view.direction(mesh.normal(idx[2])),
            ],
        };
        raster(out, depth, w, h, &tri, mode, skin, clip, blend, write_depth);
        drawn += 1;
    }
    drawn
}

/// Render a whole model to RGBA8. Uncovered pixels stay transparent so the
/// caller's checkerboard shows through where there is no head.
/// Every mesh in every model of a scene, so one function can frame and draw a
/// head made of several files.
pub fn all_meshes(models: &[Fmdl]) -> Vec<&Mesh> {
    models.iter().flat_map(|m| m.meshes.iter()).collect()
}

/// Framing for a whole head: the skin mesh, the hair that closes the back of the
/// skull, and the mouth. Measured on the shipped data, face_high.fmdl stops at
/// the back of the head and hair_high.fmdl is what covers it, so framing or
/// drawing one file alone shows a hollow.
pub fn scene_extents(models: &[Fmdl]) -> Option<(V3, V3, V3, f32)> {
    let mut lo = V3::new(f32::MAX, f32::MAX, f32::MAX);
    let mut hi = V3::new(f32::MIN, f32::MIN, f32::MIN);
    let mut any = false;
    for m in all_meshes(models) {
        for p in &m.positions {
            any = true;
            lo = V3::new(lo.x.min(p.x), lo.y.min(p.y), lo.z.min(p.z));
            hi = V3::new(hi.x.max(p.x), hi.y.max(p.y), hi.z.max(p.z));
        }
    }
    if !any {
        return None;
    }
    let centre = V3::new((lo.x + hi.x) * 0.5, (lo.y + hi.y) * 0.5, (lo.z + hi.z) * 0.5);
    let radius = V3::new(hi.x - lo.x, hi.y - lo.y, hi.z - lo.z).norm() * 0.5;
    Some((lo, hi, centre, radius))
}

/// Open a whole head: every mesh file inside its container or folder.
///
/// A face is split across files on purpose. Loading only the biggest one
/// therefore renders a head with the back missing, which is exactly what the
/// single-file loader produced.
pub fn load_scene(path: &std::path::Path) -> anyhow::Result<Vec<Fmdl>> {
    use crate::fmdl::Fmdl;
    use crate::fpk::Fpk;
    use anyhow::Context;
    let mut out: Vec<Fmdl> = Vec::new();
    let files: Vec<std::path::PathBuf> = if path.is_dir() {
        crate::fsutil::files(path)
    } else {
        vec![path.to_path_buf()]
    };
    for f in files {
        let ext = f.extension().and_then(|e| e.to_str()).unwrap_or("").to_lowercase();
        if ext == "fpk" {
            let Ok(c) = Fpk::read(&f) else { continue };
            for e in &c.entries {
                if e.data.len() > 64 && &e.data[0..4] == b"FMDL" {
                    if let Ok(m) = Fmdl::parse(e.data.clone()) {
                        if !m.meshes.is_empty() {
                            out.push(m);
                        }
                    }
                }
            }
        } else if ext == "fmdl" {
            let bytes = std::fs::read(&f).with_context(|| format!("reading {}", f.display()))?;
            if let Ok(m) = Fmdl::parse(bytes) {
                if !m.meshes.is_empty() {
                    out.push(m);
                }
            }
        }
    }
    if out.is_empty() {
        // A bare container with no recognisable name still has to open.
        return load_any(path).map(|m| vec![m]);
    }
    // Skin first: it is the biggest and the one the camera frames on.
    out.sort_by_key(|m| std::cmp::Reverse(m.meshes.iter().map(|x| x.positions.len()).sum::<usize>()));
    Ok(out)
}

/// Supersample factor: 3x at preview sizes, 2x above, 1x for large renders
/// where the cost stops being worth it.
fn samples(w: usize) -> usize {
    if w <= 512 { 3 } else if w <= 900 { 2 } else { 1 }
}

pub fn render(model: &Fmdl, tex: Option<&Texture>, cam: &Camera, mode: Mode, w: usize, h: usize) -> Vec<u8> {
    render_scene(std::slice::from_ref(model), tex, cam, mode, w, h)
}

/// The scene-level path: one depth buffer across the skin, the hair and the
/// mouth, so the hair occludes the hole at the back of the skull the way it does
/// in the game.
/// Drop meshes whose material does not sample a UV colour map.
///
/// Parts bound only to a cube map -- the eyelash line, the eye-occlusion shell,
/// the neck collar's ambient-quad -- have UVs packed into whatever region of
/// another part's texture they happen to occupy. Stretching a skin map across
/// them draws the flat shards that showed up when previewing a whole head.
///
/// A model whose materials did not decode is left untouched: no binding is
/// absent evidence, not evidence of no binding.
pub fn keep_texturable(models: &mut Vec<crate::fmdl::Fmdl>) {
    for m in models.iter_mut() {
        if m.materials.is_empty() {
            continue;
        }
        let keep: Vec<bool> = (0..m.meshes.len()).map(|i| m.base_texture(i).is_some()).collect();
        let mut i = 0usize;
        m.meshes.retain(|_| {
            let k = keep.get(i).copied().unwrap_or(true);
            i += 1;
            k
        });
    }
    models.retain(|m| !m.meshes.is_empty());
}

/// The colour maps a scene's materials actually ask for, keyed by file stem.
///
/// Materials name textures with an extension that does not match what is on
/// disk -- `face_bsm_alp.dds` and `face_eyelash_alp.tga` are both `.ftex`
/// containers -- so the lookup is by stem, not by the name as written.
#[derive(Default)]
pub struct Maps {
    items: Vec<(String, Vec<u8>, usize, usize)>,
    /// Textures the materials named, whether or not they were on disk.
    named: usize,
}

impl Maps {
    /// The map a material named, as a borrow of the owned pixels.
    pub fn texture(&self, name: &str) -> Option<Texture<'_>> {
        let key = stem_of(name);
        self.items
            .iter()
            .find(|(k, _, _, _)| *k == key)
            .map(|(_, px, w, h)| Texture { rgba: px, w: *w, h: *h })
    }

    /// How many maps were named and how many were found on disk. A preview that
    /// silently used none of them is indistinguishable from a correct one
    /// without these two numbers.
    pub fn stats(&self) -> (usize, usize) {
        (self.items.len(), self.named)
    }

        /// Load every base colour map the models bind, searching `roots` in order.
    pub fn load(models: &[Fmdl], roots: &[std::path::PathBuf]) -> Maps {
        Maps::load_from(models, roots, &[])
    }

    /// As [`Maps::load`], but textures that are not loose files are read out of
    /// the base game archives. `Asset/model/character/common/sourceimages`
    /// holds the shared maps -- eyelashes, the dummy placeholder -- and in a
    /// Sider install those are only ever inside `Data/*.cpk`, so a renderer that
    /// looks at the live root alone will always be missing them.
    pub fn load_from(
        models: &[Fmdl],
        roots: &[std::path::PathBuf],
        archives: &[std::path::PathBuf],
    ) -> Maps {
        use crate::ftex::Ftex;
        let mut items: Vec<(String, Vec<u8>, usize, usize)> = Vec::new();
        let mut named = 0usize;
        // Only the colour bindings are counted. Materials also name normal,
        // roughness, cube and mask maps, and a preview that reports "9/18
        // colour maps" when nine of the eighteen were never colour maps is
        // describing the wrong thing with a real number.
        let mut wanted: Vec<String> = Vec::new();
        for m in models {
            for i in 0..m.meshes.len() {
                if let Some(t) = m.base_texture(i) {
                    let key = stem_of(t);
                    if key.is_empty() || is_placeholder_map(&key) || wanted.contains(&key) {
                        continue;
                    }
                    wanted.push(key);
                }
            }
        }
        for key in wanted {
            named += 1;
            let mut found = None;
            for r in roots {
                let p = r.join(format!("{key}.ftex"));
                if let Ok(t) = Ftex::read(&p) {
                    if let Ok((w, h, rgba)) = t.to_rgba(0) {
                        found = Some((rgba, w as usize, h as usize));
                        break;
                    }
                }
            }
            if found.is_none() && !archives.is_empty() {
                found = from_archives(archives, &key)
                    .and_then(|bytes| Ftex::parse(&bytes).ok())
                    .and_then(|t| t.to_rgba(0).ok())
                    .map(|(w, h, rgba)| (rgba, w as usize, h as usize));
            }
            if let Some((rgba, w, h)) = found {
                items.push((key, rgba, w, h));
            }
        }
        Maps { items, named }
    }
}

/// Base archives whose table of contents has already been read. Opening a CPK
/// only parses the header and TOC, but dt14 alone lists 26,121 entries and a
/// render asks for several textures, so the handles are kept for the process.
static ARCHIVES: std::sync::OnceLock<
    std::sync::Mutex<std::collections::HashMap<std::path::PathBuf, std::sync::Arc<crate::cpk::Cpk>>>,
> = std::sync::OnceLock::new();

fn cached_cpk(path: &std::path::Path) -> Option<std::sync::Arc<crate::cpk::Cpk>> {
    let table = ARCHIVES.get_or_init(Default::default);
    if let Ok(g) = table.lock() {
        if let Some(c) = g.get(path) {
            return Some(c.clone());
        }
    }
    let cpk = std::sync::Arc::new(crate::cpk::Cpk::open(path).ok()?);
    if let Ok(mut g) = table.lock() {
        g.insert(path.to_path_buf(), cpk.clone());
    }
    Some(cpk)
}

/// Read one texture out of the base archives by file stem. A stem can appear
/// under more than one directory, and the shared character folder is the one a
/// head model means when it names `face_eyelash_alp`, so that match is tried
/// first rather than whichever archive sorts earliest.
fn from_archives(archives: &[std::path::PathBuf], key: &str) -> Option<Vec<u8>> {
    let want = format!("/{key}.ftex").to_lowercase();
    let mut other: Option<(std::sync::Arc<crate::cpk::Cpk>, crate::cpk::CpkFile)> = None;
    for cpk_path in archives {
        let Some(cpk) = cached_cpk(cpk_path) else { continue };
        for f in cpk.files.iter() {
            let p = f.path().to_lowercase();
            if !p.ends_with(&want) {
                continue;
            }
            if p.contains("/common/") {
                if let Ok(bytes) = cpk.read_file(f) {
                    return Some(bytes);
                }
            } else if other.is_none() {
                other = Some((cpk.clone(), f.clone()));
            }
        }
    }
    let (cpk, f) = other?;
    cpk.read_file(&f).ok()
}

/// The base game archives, found by walking up from a model to the install
/// folder that owns a `Data` directory. Empty when there is none, which is the
/// right answer for a pack extracted somewhere else: the renderer then simply
/// has nothing extra to look in.
pub fn base_archives(model_path: &std::path::Path) -> Vec<std::path::PathBuf> {
    let mut dir = model_path.parent().map(|p| p.to_path_buf());
    while let Some(d) = dir {
        let data = d.join("Data");
        if data.is_dir() {
            let mut out: Vec<_> = std::fs::read_dir(&data)
                .into_iter()
                .flatten()
                .flatten()
                .map(|e| e.path())
                .filter(|p| {
                    p.is_file()
                        && p.extension()
                            .map(|e| e.to_string_lossy().eq_ignore_ascii_case("cpk"))
                            .unwrap_or(false)
                })
                .collect();
            out.sort();
            return out;
        }
        dir = d.parent().map(|p| p.to_path_buf());
    }
    Vec::new()
}

/// Whether a part is an alpha-blended card rather than an opaque surface.
///
/// Across the shipped heads the material vocabulary is tiny -- `fox_skin_mat`,
/// `oral_mat`, `fox_oral_teeth_mat` for skin, and `fox_hair_mat`,
/// `fox_head_shell_mat`, `fox_eyelash_mat`, `fox_eyeOcclusion_mat` for the
/// layered cards -- and the two groups differ in exactly one decoded respect:
/// the hair and shell bind a cube map, while the eyelash and eye-occlusion
/// decals bind only colour, normal and specular. So the cube-map test alone
/// leaves the lashes in the opaque pass, where the junk colour outside the
/// strokes is painted as a smudge over the eye. Name the rest of the card
/// materials explicitly rather than trusting the geometry, whose mesh names are
/// reused (`dsk_clavicle_l` is the eyelash mesh).
fn is_blended_part(material_name: &str) -> bool {
    let lower = material_name.to_lowercase();
    lower.contains("hair") || lower.contains("shell") || lower.contains("eyelash")
        || lower.contains("occlusion")
}

/// A base binding that is not a colour map. `collar_ao` names `dummy.tga`,
/// which is 128x128 BC1 -- no alpha channel and no useful colour -- because that
/// part modulates ambient occlusion rather than carrying albedo. Painting it as
/// colour laid a stack of ghost plates over the neck, so it is neither counted
/// as a colour map nor drawn as one.
fn is_placeholder_map(key: &str) -> bool {
    key.starts_with("dummy")
}

/// File stem, lower-cased: `face_bsm_alp.dds` -> `face_bsm_alp`.
fn stem_of(name: &str) -> String {
    std::path::Path::new(name)
        .file_stem()
        .map(|s| s.to_string_lossy().to_lowercase())
        .unwrap_or_default()
}

/// Where to look for a texture, in the order the game itself would find it:
/// beside the model, then the character-common folder two levels up.
pub fn texture_roots(model_path: &std::path::Path) -> Vec<std::path::PathBuf> {
    let dir = if model_path.is_dir() {
        model_path.to_path_buf()
    } else {
        model_path
            .parent()
            .and_then(|p| p.parent())
            .map(|p| p.to_path_buf())
            .unwrap_or_default()
    };
    let mut out = Vec::new();
    for sub in ["sourceimages/#windx11", "sourceimages"] {
        out.push(dir.join(sub));
    }
    if let Some(ch) = dir.parent().and_then(|p| p.parent()).and_then(|p| p.parent()) {
        for sub in ["common/sourceimages/#windx11", "common/sourceimages"] {
            out.push(ch.join(sub));
        }
    }
    out
}

/// Every mesh together with the model it came from, so its material can be
/// looked up. `all_meshes` flattens that information away.
pub fn mesh_refs(models: &[Fmdl]) -> Vec<(&Fmdl, usize, &Mesh)> {
    let mut out = Vec::new();
    for m in models {
        for i in 0..m.meshes.len() {
            if let Some(mesh) = m.meshes.get(i) {
                out.push((m, i, mesh));
            }
        }
    }
    out
}

pub fn render_scene(models: &[Fmdl], tex: Option<&Texture>, cam: &Camera, mode: Mode, w: usize, h: usize) -> Vec<u8> {
    render_scene_maps(models, tex, None, cam, mode, w, h)
}

/// As `render_scene`, but each mesh is sampled with the colour map its own
/// material binds. Without that, every part of the head is painted with the one
/// skin map handed in, which is what made the eyelash and eye parts read as
/// flat plates rather than as themselves.
pub fn render_scene_maps(
    models: &[Fmdl],
    tex: Option<&Texture>,
    maps: Option<&Maps>,
    cam: &Camera,
    mode: Mode,
    w: usize,
    h: usize,
) -> Vec<u8> {
    let (px, _) = render_report(models, tex, maps, cam, mode, w, h);
    px
}

/// One mesh together with the skin it should be sampled from.
struct Part<'a> {
    mesh: &'a Mesh,
    skin: Option<&'a Skin>,
    tw: usize,
    th: usize,
    /// An alpha-blended card rather than an opaque surface; see
    /// [`is_blended_part`]. These must not write depth or occlude each other.
    blended: bool,
}

/// Depth of a part's centre in view space. Larger is nearer, matching the
/// depth test in `raster`.
fn part_depth(part: &Part, view: &View) -> f32 {
    let mut sum = 0.0f32;
    let mut n = 0usize;
    for p in part.mesh.positions.iter() {
        if p.x.is_finite() && p.y.is_finite() && p.z.is_finite() {
            sum += view.project(*p).z;
            n += 1;
        }
    }
    if n == 0 {
        f32::MIN
    } else {
        sum / n as f32
    }
}

/// Alpha below this (on the 0..255 scale) is discarded from an alpha-blended
/// part. `hair_parts_bsm_alp` puts 72% of its texels in the lowest alpha
/// octile with non-black RGB, so that colour is junk and must not be drawn.
const CLIP_ALPHA: u8 = 96;

/// Minimal RGBA PNG: filter-0 scanlines through flate2, with the chunk CRCs
/// computed here because the crate has no PNG encoder as a dependency.
pub fn write_png(path: &std::path::Path, w: usize, h: usize, rgba: &[u8]) -> anyhow::Result<()> {
    use flate2::write::ZlibEncoder;
    use flate2::Compression;
    use std::io::Write;

    fn crc32(data: &[u8]) -> u32 {
        let mut table = [0u32; 256];
        for (i, v) in table.iter_mut().enumerate() {
            let mut c = i as u32;
            for _ in 0..8 {
                c = if c & 1 != 0 { 0xEDB8_8320 ^ (c >> 1) } else { c >> 1 };
            }
            *v = c;
        }
        let mut crc = 0xFFFF_FFFFu32;
        for &b in data {
            crc = table[((crc ^ b as u32) & 0xFF) as usize] ^ (crc >> 8);
        }
        crc ^ 0xFFFF_FFFF
    }

    fn chunk(out: &mut Vec<u8>, kind: &str, data: &[u8]) {
        out.extend_from_slice(&(data.len() as u32).to_be_bytes());
        let start = out.len();
        out.extend_from_slice(kind.as_bytes());
        out.extend_from_slice(data);
        let crc = crc32(&out[start..]);
        out.extend_from_slice(&crc.to_be_bytes());
    }

    let mut raw = Vec::with_capacity(h * (w * 4 + 1));
    for y in 0..h {
        raw.push(0u8);
        raw.extend_from_slice(&rgba[y * w * 4..(y + 1) * w * 4]);
    }
    let mut enc = ZlibEncoder::new(Vec::new(), Compression::default());
    enc.write_all(&raw)?;
    let idat = enc.finish()?;

    let mut out = b"\x89PNG\r\n\x1a\n".to_vec();
    let mut ihdr = Vec::new();
    ihdr.extend_from_slice(&(w as u32).to_be_bytes());
    ihdr.extend_from_slice(&(h as u32).to_be_bytes());
    ihdr.extend_from_slice(&[8, 6, 0, 0, 0]);
    chunk(&mut out, "IHDR", &ihdr);
    chunk(&mut out, "IDAT", &idat);
    chunk(&mut out, "IEND", b"");
    std::fs::write(path, out)?;
    Ok(())
}

/// As [`render_scene_maps`], but also returns the texture names that were asked
/// for and could not be resolved. A hole in the image is otherwise invisible,
/// and a caller that cannot tell "no hair" from "hair drawn as plates" will
/// report the wrong thing.
pub fn render_report(
    models: &[Fmdl],
    tex: Option<&Texture>,
    maps: Option<&Maps>,
    cam: &Camera,
    mode: Mode,
    w: usize,
    h: usize,
) -> (Vec<u8>, Vec<String>) {
    let fallback = tex.map(Skin::new);
    // Skins are built once per named texture: the mip pyramid is the expensive
    // part of a texture, and several materials share the same map.
    let mut cache: Vec<(String, Skin)> = Vec::new();
    let mut skipped: Vec<String> = Vec::new();
    let ss = samples(w);
    let (sw, sh) = (w * ss, h * ss);
    let mut big = vec![0u8; sw * sh * 4];
    let mut depth = vec![f32::MIN; sw * sh];
    let Some((_lo, _hi, centre, radius)) = scene_extents(models) else {
        return (downsample(&big, sw, w, h, ss), skipped);
    };
    let view = View::new(cam, centre, radius);
    // Two different failures, two different answers. If nothing resolved
    // at all, every part would be skipped and the preview would be a blank
    // frame that looks like a broken renderer rather than a missing pack;
    // untextured shading still shows the real shape. A partial miss is the
    // opposite: the parts that did resolve are correct, so the ones that
    // did not are dropped rather than painted with a neighbour's skin.
    let nothing_resolved = maps.is_some() && maps.map(|m| m.stats().0 == 0).unwrap_or(false);
    let mut parts: Vec<Part> = Vec::new();
    // Build every skin before any part points at one: `parts` holds borrows of
    // `cache`, so growing the cache in the same loop would invalidate them.
    let mut wanted: Vec<Option<String>> = Vec::new();
    for (model, i, _mesh) in mesh_refs(models) {
        let key = if maps.is_some() { model.base_texture(i).map(stem_of) } else { None };
        if let Some(k) = &key {
            if !cache.iter().any(|(c, _)| c == k) {
                if let Some(t) = maps.and_then(|m| m.texture(k)) {
                    cache.push((k.clone(), Skin::new(&t)));
                }
            }
        }
        wanted.push(key);
    }
    for ((model, i, mesh), want) in mesh_refs(models).into_iter().zip(wanted) {
        // A placeholder binding is not a missing texture, so it is not reported
        // as one: the part is an occlusion decal and has no colour to show.
        if want.as_deref().map(is_placeholder_map).unwrap_or(false) {
            continue;
        }
        let blended = model.material(i).map(|m| {
            m.slot("CubeMap_Tex_LIN").is_some() || is_blended_part(&m.name)
        }).unwrap_or(false);
        let skin: Option<&Skin> = match &want {
            Some(key) => match cache.iter().find(|(k, _)| k == key).map(|(_, s)| s) {
                Some(s) => Some(s),
                // The material asked for a specific map and that map is not
                // available. Painting the part with some other part's skin is
                // not a degraded view of it -- for the hair shell it is a
                // stack of flat plates over the face, which reads as a broken
                // head rather than as a missing file. Skipping is the honest
                // outcome, and `skipped` reports it.
                None => {
                    if maps.is_some() && !nothing_resolved {
                        skipped.push(key.clone());
                        continue;
                    }
                    fallback.as_ref()
                }
            },
            None => fallback.as_ref(),
        };
        let (tw, th) = skin.map(|s| (s.w, s.h)).unwrap_or((1, 1));
        parts.push(Part { mesh, skin, tw, th, blended });
    }
    // Opaque first, with depth writes, so the face and skull are in the buffer
    // before anything translucent is composited over them.
    for part in parts.iter().filter(|p| !p.blended) {
        draw_mesh(&mut big, &mut depth, sw, sh, part.mesh, &view, mode, part.skin,
            (part.tw * ss, part.th * ss), 0, 0.0, true);
    }
    // Then the alpha-blended parts, far to near, tested against the opaque
    // depth but never writing it. Without the sort, two cards at similar
    // depth fight over each pixel and the nearer one wins entirely; without
    // suppressing the depth write, the first card laid down occludes every
    // card behind it, which is the stack-of-plates look.
    let mut blended: Vec<&Part> = parts.iter().filter(|p| p.blended).collect();
    blended.sort_by(|a, b| part_depth(a, &view).partial_cmp(&part_depth(b, &view)).unwrap_or(std::cmp::Ordering::Equal));
    for part in blended {
        let clip = if mode == Mode::Textured && part.skin.is_some() { CLIP_ALPHA as u8 } else { 0 };
        draw_mesh(&mut big, &mut depth, sw, sh, part.mesh, &view, mode, part.skin,
            (part.tw * ss, part.th * ss), clip, 1.0, false);
    }
    (downsample(&big, sw, w, h, ss), skipped)
}

/// Area-weighted reduce, averaging only the pixels that actually had coverage so
/// an edge against a transparent background does not gain a dark halo.
fn downsample(src: &[u8], sw: usize, w: usize, h: usize, ss: usize) -> Vec<u8> {
    let mut out = vec![0u8; w * h * 4];
    for y in 0..h {
        for x in 0..w {
            let mut acc = [0f32; 4];
            let mut cov = 0f32;
            for dy in 0..ss {
                for dx in 0..ss {
                    let i = ((y * ss + dy) * sw + (x * ss + dx)) * 4;
                    let a = src[i + 3] as f32 / 255.0;
                    if a <= 0.0 { continue; }
                    cov += a;
                    for c in 0..3 { acc[c] += src[i + c] as f32 * a; }
                }
            }
            let o = (y * w + x) * 4;
            if cov <= 0.0 { continue; }
            // Coverage also anti-aliases the silhouette edge itself.
            let edge = (cov / (ss * ss) as f32).min(1.0);
            for c in 0..3 {
                out[o + c] = (acc[c] / cov).round().clamp(0.0, 255.0) as u8;
            }
            out[o + 3] = (edge * 255.0).round().clamp(0.0, 255.0) as u8;
        }
    }
    out
}

/// The same head from four angles in one image, so a 3D claim can be checked in
/// a single screenshot instead of four.
pub fn turntable(model: &Fmdl, tex: Option<&Texture>, cell: usize, mode: Mode) -> Vec<u8> {
    turntable_scene(std::slice::from_ref(model), tex, cell, mode)
}

/// The four cells a head needs to be checked from: front, three-quarter, back
/// and top. The third one is the view that used to come out hollow.
pub fn turntable_scene(models: &[Fmdl], tex: Option<&Texture>, cell: usize, mode: Mode) -> Vec<u8> {
    turntable_scene_maps(models, tex, None, cell, mode)
}

/// As `turntable_scene`, with each mesh sampled from its own material's map.
pub fn turntable_scene_maps(
    models: &[Fmdl],
    tex: Option<&Texture>,
    maps: Option<&Maps>,
    cell: usize,
    mode: Mode,
) -> Vec<u8> {
    let cams = [Camera::front(), Camera::three_quarter(), Camera::back(), Camera::top()];
    let total_w = cell * cams.len();
    let mut out = vec![0u8; total_w * cell * 4];
    for (i, c) in cams.iter().enumerate() {
        let tile = render_scene_maps(models, tex, maps, c, mode, cell, cell);
        for y in 0..cell {
            let src = y * cell * 4;
            let dst = (y * total_w + i * cell) * 4;
            out[dst..dst + cell * 4].copy_from_slice(&tile[src..src + cell * 4]);
        }
    }
    out
}

/// How much of the frame the head covers, as a fraction. Cheap and useful: it
/// is the difference between a framed head and a decoded garbage smear.
pub fn coverage(px: &[u8]) -> f32 {
    let mut lit = 0;
    let mut total = 0;
    for p in px.chunks(4) {
        total += 1;
        if p[3] > 200 {
            lit += 1;
        }
    }
    if total == 0 {
        0.0
    } else {
        lit as f32 / total as f32
    }
}

#[cfg(test)]
mod alpha_probe {
    /// What the shipped face maps actually put in the alpha channel. Decides
    /// whether an alpha test is safe at all.
    #[test]
    fn probe_alpha_distribution() {
        let dir = &crate::fmdl::real_face_dir();
        if !dir.exists() { return; }
        for p in crate::fsutil::files(dir) {
            let name = p.file_name().unwrap().to_string_lossy().to_lowercase();
            if !name.contains("bsm") || !name.ends_with(".ftex") { continue; }
            let t = crate::ftex::Ftex::read(&p).unwrap();
            let (w, h, rgba) = t.to_rgba(0).unwrap();
            let mut hist = [0u32; 8];
            let mut dark_rgb = 0u32;
            for q in rgba.chunks(4) {
                hist[(q[3] as usize * 8) / 256] += 1;
                if (q[0] as u32 + q[1] as u32 + q[2] as u32) < 24 { dark_rgb += 1; }
            }
            let total = (w * h) as u32;
            println!("{} {}x{} alpha-octile-histogram {:?} dark-rgb {:.1}%",
                name, w, h,
                hist.iter().map(|c| (100.0 * *c as f64 / total as f64) as u32).collect::<Vec<_>>(),
                100.0 * dark_rgb as f64 / total as f64);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::fmdl::{Material, Slot, V3};

    const STRIDE: usize = 28;

    /// Fill one vertex's 28-byte attribute record: normal as four halves at 0,
    /// UV as two halves at 24.
    fn write_vertex(attributes: &mut [u8], v: usize, normal: [f32; 4], uv: [f32; 2]) {
        for (k, val) in normal.iter().enumerate() {
            let bits = crate::fmdl::f32_to_f16(*val).to_le_bytes();
            attributes[v * STRIDE + k * 2..v * STRIDE + k * 2 + 2].copy_from_slice(&bits);
        }
        for k in 0..2 {
            let bits = crate::fmdl::f32_to_f16(uv[k]).to_le_bytes();
            attributes[v * STRIDE + 24 + k * 2..v * STRIDE + 24 + k * 2 + 2].copy_from_slice(&bits);
        }
    }

    fn mesh(positions: Vec<V3>, normals: Vec<[f32; 4]>, uvs: Vec<[f32; 2]>, indices: Vec<u16>) -> Mesh {
        let mut attributes = vec![0u8; positions.len() * STRIDE];
        for v in 0..positions.len() {
            write_vertex(&mut attributes, v, normals[v], uvs[v]);
        }
        Mesh {
            name: "test".into(),
            material_instance: 0,
            stride: STRIDE,
            positions,
            attributes,
            uv_offsets: vec![24],
            normal_offset: Some(0),
            tangent_offset: None,
            indices,
        }
    }

    fn model(meshes: Vec<Mesh>) -> Fmdl {
        Fmdl { bytes: Vec::new(), version: 2.03, meshes, materials: Vec::new(), spans: Vec::new() }
    }

    /// Two identical quads at different depths, each pointing at a different
    /// texel. Whatever wins the centre pixel proves the depth test is real.
    #[test]
    fn the_nearer_surface_wins_the_pixel() {
        let positions = vec![
            V3::new(-0.4, -0.4, 0.2),
            V3::new(0.4, -0.4, 0.2),
            V3::new(0.4, 0.4, 0.2),
            V3::new(-0.4, 0.4, 0.2),
            V3::new(-0.4, -0.4, -0.2),
            V3::new(0.4, -0.4, -0.2),
            V3::new(0.4, 0.4, -0.2),
            V3::new(-0.4, 0.4, -0.2),
        ];
        let normals = vec![[0.0f32, 0.0, 1.0, 1.0]; 8];
        // Near quad samples texel (0,0) = red; far quad samples (1,1) = blue.
        let uvs = vec![
            [0.0, 0.0], [0.1, 0.0], [0.1, 0.1], [0.0, 0.1],
            [0.9, 0.9], [1.0, 0.9], [1.0, 1.0], [0.9, 1.0],
        ];
        let m = mesh(
            positions.clone(),
            normals.clone(),
            uvs.clone(),
            vec![0, 1, 2, 0, 2, 3, 4, 5, 6, 4, 6, 7],
        );
        // 2x2 texture: red at (0,0), blue at (1,1), green elsewhere.
        let tex_px = vec![
            255, 0, 0, 255, 0, 255, 0, 255, 0, 255, 0, 255, 0, 0, 255, 255,
        ];
        let tex = Texture { rgba: &tex_px, w: 2, h: 2 };
        let px = render(&model(vec![m]), Some(&tex), &Camera::front(), Mode::Textured, 40, 40);
        let i = (20 * 40 + 20) * 4;
        assert_eq!(px[i + 3], 255, "centre pixel is empty");
        assert!(px[i] > 150 && px[i + 2] < 90, "centre should be the near red quad, got {:?}", &px[i..i + 4]);

        // And with the far quad in front, blue must win: the test is depth, not
        // winding or index order.
        let mut near_blue = positions.clone();
        // Put the blue corners in front instead of behind.
        for i in 4..8 { near_blue[i].z = 0.2; }
        for i in 0..4 { near_blue[i].z = -0.2; }
        let flipped = mesh(
            near_blue,
            normals.clone(),
            uvs.clone(),
            vec![0, 1, 2, 0, 2, 3, 4, 5, 6, 4, 6, 7],
        );
        let px = render(&model(vec![flipped]), Some(&tex), &Camera::front(), Mode::Textured, 40, 40);
        let i = (20 * 40 + 20) * 4;
        assert!(px[i + 2] > 150 && px[i] < 90, "centre should be the near blue quad, got {:?}", &px[i..i + 4]);
    }

    /// Alpha-blended parts must composite far-to-near whatever order the file
    /// lists them in. Hair cards are the case: drawn in file order, whichever
    /// card happened to come last covered the ones in front of it, which is the
    /// stack-of-plates look. Two cube-mapped quads, one in front of the other,
    /// rendered in both file orders must agree on the pixel.
    #[test]
    fn blended_parts_composite_back_to_front_whatever_the_file_order() {
        let normals = vec![[0.0f32, 0.0, 1.0, 1.0]; 4];
        let quad = |z: f32, uv: [[f32; 2]; 4]| {
            let positions = vec![
                V3::new(-0.4, -0.4, z),
                V3::new(0.4, -0.4, z),
                V3::new(0.4, 0.4, z),
                V3::new(-0.4, 0.4, z),
            ];
            mesh(positions, normals.clone(), uv.to_vec(), vec![0, 1, 2, 0, 2, 3])
        };
        let mut near = quad(0.2, [[0.0, 0.0], [0.1, 0.0], [0.1, 0.1], [0.0, 0.1]]);
        let mut far = quad(-0.2, [[0.9, 0.9], [1.0, 0.9], [1.0, 1.0], [0.9, 1.0]]);
        // The two quads draw with the two materials, in both orders below.
        near.material_instance = 0;
        far.material_instance = 1;
        // A material that binds a cube map is what marks a part as blended.
        let hair_mat = Material {
            name: "hair".into(),
            slots: vec![Slot {
                name: "CubeMap_Tex_LIN".into(),
                texture: "cubemap".into(),
                path: String::new(),
            }],
        };
        let skin_mat = Material { name: "skin".into(), slots: Vec::new() };
        let tex_px = vec![
            255, 0, 0, 255, 0, 255, 0, 255, 0, 255, 0, 255, 0, 0, 255, 255,
        ];
        let tex = Texture { rgba: &tex_px, w: 2, h: 2 };
        let cam = Camera::front();
        for order in [0, 1] {
            let mut m = model(if order == 0 { vec![near.clone(), far.clone()] } else { vec![far.clone(), near.clone()] });
            m.materials = if order == 0 { vec![hair_mat.clone(), skin_mat.clone()] } else { vec![skin_mat.clone(), hair_mat.clone()] };
            let (px, skipped) = render_report(&[m], Some(&tex), None, &cam, Mode::Textured, 40, 40);
            assert!(skipped.is_empty(), "nothing should be skipped: {skipped:?}");
            let i = (20 * 40 + 20) * 4;
            assert!(px[i] > 150 && px[i + 2] < 90,
                "file order {order} must still put the near card on top, got {:?}", &px[i..i + 4]);
        }
    }

    #[test]
    fn an_empty_model_renders_a_clean_transparent_frame() {
        let px = render(&model(Vec::new()), None, &Camera::front(), Mode::Lambert, 32, 32);
        assert_eq!(px.len(), 32 * 32 * 4);
        assert!(px.iter().all(|&b| b == 0), "nothing should be drawn");
        assert_eq!(coverage(&px), 0.0);
    }

    #[test]
    fn uv_wrapping_repeats_instead_of_smearing_the_edge() {
        let positions = vec![
            V3::new(-0.5, -0.5, 0.0),
            V3::new(0.5, -0.5, 0.0),
            V3::new(0.5, 0.5, 0.0),
            V3::new(-0.5, 0.5, 0.0),
        ];
        let normals = vec![[0.0f32, 0.0, 1.0, 1.0]; 4];
        // u runs 0..2 across the quad: one full repeat of a two-column texture.
        let uvs = vec![[0.0f32, 0.0], [2.0, 0.0], [2.0, 1.0], [0.0, 1.0]];
        let m = mesh(positions, normals, uvs, vec![0, 1, 2, 0, 2, 3]);
        let tex_px = vec![255, 0, 0, 255, 0, 0, 255, 255];
        let tex = Texture { rgba: &tex_px, w: 2, h: 1 };
        let px = render(&model(vec![m]), Some(&tex), &Camera::front(), Mode::Textured, 41, 10);
        let left = (5 * 41 + 3) * 4;
        let right = (5 * 41 + 37) * 4;
        assert!(px[left] > 120, "left half should be red, got {:?}", &px[left..left + 3]);
        assert!(px[right + 2] > 120, "right half should be blue, got {:?}", &px[right..right + 3]);
    }

    fn real_head() -> Option<Fmdl> {
        let path = &crate::fmdl::real_face_fpk();
        if !path.exists() {
            return None;
        }
        let c = crate::fpk::Fpk::read(path).unwrap();
        Fmdl::parse(c.find("face_high.fmdl").unwrap().data.clone()).ok()
    }

    #[test]
    fn the_shipped_head_measures_as_a_head_not_a_plane() {
        let Some(m) = real_head() else { return };
        let (lo, hi, centre, radius) = extents(&m).unwrap();
        let ex = hi.x - lo.x;
        let ey = hi.y - lo.y;
        let ez = hi.z - lo.z;
        // A human head is roughly 150 mm wide, 230 mm tall, 200 mm deep.
        for (name, v) in [("width", ex), ("height", ey), ("depth", ez)] {
            assert!(v > 0.05 && v < 0.6, "{name} {v} m is not a head");
        }
        // The claim the user is entitled to make about a 3D face: it has depth.
        assert!(ez > 0.08, "only {ez} m of front-to-back depth: that is a decal");
        assert!(ez > ex * 0.6, "depth {ez} against width {ex} is too flat to be a skull");
        assert!(radius > 0.05 && radius < 0.5, "framing radius {radius}");
        assert!(centre.y > 1.0, "the head sits at eye height, got {}", centre.y);
    }

    #[test]
    fn a_real_head_fills_the_frame_from_every_angle() {
        let Some(m) = real_head() else { return };
        let (w, h) = (200usize, 200usize);
        let mut fracs = Vec::new();
        for (name, cam) in [
            ("front", Camera::front()),
            ("three-quarter", Camera::three_quarter()),
            ("profile", Camera::profile()),
            ("top", Camera::top()),
        ] {
            let px = render(&m, None, &cam, Mode::Lambert, w, h);
            let frac = coverage(&px);
            assert!(frac > 0.08, "{name} covered only {frac:.3} of the frame");
            assert!(frac < 0.98, "{name} filled the whole frame, so it is not framed");
            let distinct: std::collections::HashSet<(u8, u8, u8)> = px
                .chunks(4)
                .filter(|p| p[3] > 200)
                .map(|p| (p[0], p[1], p[2]))
                .collect();
            assert!(distinct.len() > 200, "{name} has only {} distinct colours", distinct.len());
            fracs.push((name, frac));
        }
        // Four genuinely different silhouettes, not one picture four times.
        let front = render(&m, None, &Camera::front(), Mode::Lambert, w, h);
        let side = render(&m, None, &Camera::profile(), Mode::Lambert, w, h);
        let top = render(&m, None, &Camera::top(), Mode::Lambert, w, h);
        let diff = front.iter().zip(side.iter()).filter(|(a, b)| a != b).count();
        assert!(diff > w * h, "front and profile are the same image ({diff} bytes apart)");
        let diff = front.iter().zip(top.iter()).filter(|(a, b)| a != b).count();
        assert!(diff > w * h, "front and top are the same image ({diff} bytes apart)");
        assert_eq!(fracs.len(), 4);
    }

    #[test]
    fn normals_mode_points_the_face_at_the_camera() {
        let Some(m) = real_head() else { return };
        let px = render(&m, None, &Camera::front(), Mode::Normals, 160, 160);
        let lit: Vec<&[u8]> = px.chunks(4).filter(|p| p[3] > 200).collect();
        assert!(!lit.is_empty(), "nothing drawn");
        // Surfaces facing the camera have z near +1, so blue dominates.
        let forward = lit.iter().filter(|p| p[2] > 200 && p[0].abs_diff(128) < 60 && p[1].abs_diff(128) < 60).count();
        assert!(forward * 20 > lit.len(), "only {forward} of {} pixels face the camera", lit.len());
        // Two-sided shading must not have leaked into this view. From the front of
        // this shell nothing legitimately faces away -- the outside of the face is
        // all that is visible -- so a flipping bug would show up as a *surplus* of
        // rear-facing pixels, not a shortage.
        let rear = lit.iter().filter(|p| p[2] < 55).count();
        assert!(rear * 10 < lit.len(), "{rear} of {} pixels face away from a front view", lit.len());
    }

    /// Measured, not assumed: the shipped head faces **+z**, so Camera::front()
    /// must show a blue-dominant (normal toward viewer) face and the back of the
    /// skull must not. Getting this backwards is what made every surface read as
    /// interior for a while.
    /// The framing numbers this module's camera choices rest on, asserted rather
    /// than printed: a head is about 200 mm wide and 230 mm deep, it sits at eye
    /// height, and the skin's area-weighted normal points down +z.
    #[test]
    fn the_facing_axis_is_measured_from_the_geometry() {
        let Some(m) = real_head() else { return };
        let (lo, hi, _centre, _r) = extents(&m).unwrap();
        assert!((hi.x - lo.x - 0.198).abs() < 0.02, "head width {:.3} m", hi.x - lo.x);
        assert!(hi.z > 0.15 && lo.z < 0.0, "z span {:.3}..{:.3} puts the face behind the skull", lo.z, hi.z);
        // Area-weighted mean of every triangle's vertex normals: the direction
        // the bulk of the skin faces.
        let mut acc = V3::new(0.0, 0.0, 0.0);
        let mut area = 0.0f32;
        for mesh in &m.meshes {
            for t in mesh.indices.chunks(3) {
                if t.len() != 3 {
                    continue;
                }
                let idx = [t[0] as usize, t[1] as usize, t[2] as usize];
                if idx.iter().any(|&i| i >= mesh.positions.len()) {
                    continue;
                }
                let p = &mesh.positions;
                let a = p[idx[1]].sub(p[idx[0]]).cross(p[idx[2]].sub(p[idx[0]])).norm() * 0.5;
                let n = (0..3).fold(V3::new(0.0, 0.0, 0.0), |s, k| s.add(mesh.normal(idx[k])));
                acc = acc.add(n.scale(a));
                area += a;
            }
        }
        let mean = acc.scale(1.0 / area.max(1e-9)).normalized();
        assert!(mean.z > 0.8, "mean skin normal {:.3} {:.3} {:.3} does not point +z", mean.x, mean.y, mean.z);
        assert!(area > 0.05 && area < 0.5, "total skin area {area:.4} m2 is not a head");
        // The most protruding vertex along each axis, with its normal.
        for axis in 0..3 {
            let mut best = 0usize;
            let mut bv = f32::MIN;
            for mesh in &m.meshes {
                for (i, p) in mesh.positions.iter().enumerate() {
                    let v = match axis {
                        0 => p.x,
                        1 => p.y,
                        _ => p.z,
                    };
                    if v > bv {
                        bv = v;
                        best = i;
                    }
                }
            }
            let n = m.meshes.first().unwrap().normal(best);
            assert!(n.x.is_finite() && n.y.is_finite() && n.z.is_finite(), "axis {axis} normal is not finite");
        }
    }

    #[test]
    fn the_shipped_head_faces_plus_z_and_front_shows_it() {
        let Some(m) = real_head() else { return };
        // The skin side must be the one that dominates with forward normals, and
        // the far side must be the one that dominates with backward ones. Ratios,
        // not absolute fractions: the shell is open, so both views also show
        // interior surfaces.
        let forward_frac = |yaw: f32| {
            let px = render(&m, None, &Camera { yaw, pitch: 0.0, zoom: 1.0 }, Mode::Normals, 120, 120);
            let lit: Vec<&[u8]> = px.chunks(4).filter(|p| p[3] > 200).collect();
            let f = lit.iter().filter(|p| p[2] > 200).count();
            let b = lit.iter().filter(|p| p[2] < 55).count();
            (f, b, lit.len())
        };
        let (f0, b0, n) = forward_frac(0.0);
        let (f180, b180, _) = forward_frac(std::f32::consts::PI);
        // Measured on the shipped head: 5341 of 11778 front pixels face the camera
        // and none face away; from behind, the interior of the face shows through
        // the open shell, so forward-facing pixels there are the *inside* of the
        // skin, and rear-facing pixels (the skull's back) dominate.
        assert!(f0 > f180 * 2, "yaw 0 gives {f0} forward pixels, yaw 180 gives {f180}: +z is not the face");
        assert!(b180 > b0, "yaw 180 gives {b180} rear pixels against {b0} at yaw 0: not an open shell");
        assert!(f0 * 4 > n, "only {f0} of {n} front pixels face the camera");
        assert!(b0 * 10 < n, "{b0} of {n} pixels face away in a front view");
        // The default camera must be the one that shows the face.
        let d = Camera::front();
        assert_eq!(d.yaw, 0.0, "Camera::front() no longer looks down +z");
    }

    /// The 1.3.0 promise is that editing a texture is visible on the model, so
    /// this replaces the old morph test: same shape, different skin, and the
    /// picture must actually change. A renderer that ignored the new map would
    /// still produce a plausible head, which is why this is asserted directly.
    #[test]
    fn a_retextured_head_changes_the_picture() {
        let Some(m) = real_head() else { return };
        let size = 160usize;
        let plain = vec![200u8; size * size * 4];
        let before = render(&m, Some(&Texture { rgba: &plain, w: size, h: size }), &Camera::front(), Mode::Textured, size, size);
        // Same dimensions and same mip depth, only the colours differ.
        let mut alt = plain.clone();
        for px in alt.chunks_mut(4) {
            px[0] = 30;
            px[1] = 120;
        }
        let after = render(&m, Some(&Texture { rgba: &alt, w: size, h: size }), &Camera::front(), Mode::Textured, size, size);
        let diff = before.iter().zip(after.iter()).filter(|(a, b)| a != b).count();
        let covered = before.chunks(4).filter(|p| p[3] > 200).count();
        assert!(covered > size * size / 10, "the head barely drew: {covered} px");
        assert!(diff > covered / 2, "swapping the skin map changed only {diff} of {covered} covered pixels");
    }

    #[test]
    fn a_turntable_tiles_four_views_side_by_side() {
        let Some(m) = real_head() else { return };
        let cell = 64;
        let px = turntable(&m, None, cell, Mode::Lambert);
        assert_eq!(px.len(), cell * 4 * cell * 4);
        // Every cell holds something, and the last cell's right edge is the
        // image's right edge -- the slicing bug that put tiles on top of each
        // other would leave the fourth cell empty.
        for i in 0..4 {
            let mut lit = 0;
            for y in 0..cell {
                for x in 0..cell {
                    let o = (y * cell * 4 + i * cell + x) * 4;
                    if px[o + 3] > 200 {
                        lit += 1;
                    }
                }
            }
            assert!(lit > cell, "cell {i} is empty ({lit} pixels)");
        }
    }
}

#[cfg(test)]
mod binding_tests {
    use super::{
        coverage, keep_texturable, load_scene, render_scene_maps, texture_roots, Maps, Camera, Mode,
    };
    use crate::fmdl::Fmdl;
    use crate::fpk::Fpk;

    /// The eyelash-line and eye-occlusion parts are the ones that must go: they
    /// bind no colour map, so a skin sampler paints them with someone's cheek.
    #[test]
    fn untexturable_parts_are_dropped_and_the_head_survives() {
        let path = &crate::fmdl::real_face_fpk();
        if !path.exists() {
            return;
        }
        let fpk = Fpk::read(path).expect("container");
        let mut models = Vec::new();
        for e in fpk.entries.iter().filter(|e| e.data.len() > 64 && &e.data[0..4] == b"FMDL") {
            if let Ok(m) = Fmdl::parse(e.data.clone()) {
                if !m.meshes.is_empty() {
                    models.push(m);
                }
            }
        }
        let before: usize = models.iter().map(|m| m.meshes.len()).sum();
        let mut dropped = 0usize;
        for m in &models {
            for i in 0..m.meshes.len() {
                if m.base_texture(i).is_none() {
                    dropped += 1;
                }
            }
        }
        assert!(dropped > 0, "the head should contain parts with no colour map");
        keep_texturable(&mut models);
        let after: usize = models.iter().map(|m| m.meshes.len()).sum();
        assert_eq!(after, before - dropped, "only untexturable meshes should go");
        for m in &models {
            for i in 0..m.meshes.len() {
                assert!(m.base_texture(i).is_some(), "a mesh without a colour map survived");
            }
        }
        let verts: usize = models.iter().flat_map(|m| m.meshes.iter()).map(|x| x.positions.len()).sum();
        assert!(verts > 1000, "the head itself should still be there, got {verts} verts");
    }

    /// A model with no decoded materials is evidence of nothing, so the filter
    /// must not quietly delete its geometry.
    #[test]
    fn a_model_without_materials_is_left_alone() {
        let e = crate::fmdl::Fmdl {
            bytes: Vec::new(),
            version: 2.03,
            meshes: vec![crate::fmdl::Mesh {
                name: "x".into(),
                material_instance: 0,
                stride: 28,
                positions: vec![crate::fmdl::V3::new(0.0, 0.0, 0.0); 3],
                attributes: vec![0u8; 28 * 3],
                uv_offsets: vec![24],
                normal_offset: Some(0),
                tangent_offset: Some(8),
                indices: vec![0, 1, 2],
            }],
            materials: Vec::new(),
            spans: Vec::new(),
        };
        let mut models = vec![e];
        keep_texturable(&mut models);
        assert_eq!(models.len(), 1, "an unbound model must not be dropped");
        assert_eq!(models[0].meshes.len(), 1);
    }

    /// The binding is only useful if the named maps are actually found where
    /// the game keeps them. This is the check that would have caught the old
    /// "one --texture for every mesh" behaviour.
    #[test]
    fn the_skin_map_is_found_from_the_material_binding_alone() {
        let path = &crate::fmdl::real_face_fpk();
        if !path.exists() {
            return;
        }
        let mut models = load_scene(path).expect("the donor scene should load");
        keep_texturable(&mut models);
        let roots = texture_roots(path);
        let maps = Maps::load(&models, &roots);
        let (found, named) = maps.stats();
        assert!(named > 0, "materials should name at least one colour map");
        assert!(found > 0, "none of the {named} named maps resolved on disk");
        let skin = models
            .iter()
            .enumerate()
            .flat_map(|(mi, m)| (0..m.meshes.len()).map(move |i| (mi, i, m.base_texture(i))))
            .find(|(_, _, b)| b.map(|x| x.contains("bsm")).unwrap_or(false));
        let Some((mi, i, name)) = skin else {
            panic!("no mesh binds a bsm map; refs={:?}", models[0].texture_refs().len());
        };
        let t = maps.texture(name.unwrap()).expect("the bsm map should be loaded");
        assert_eq!((t.w, t.h), (1024, 1024), "skin map size");
        assert_eq!(t.rgba.len(), 1024 * 1024 * 4, "skin map is RGBA8");
        let _ = (mi, i);
    }

    /// A material that names a texture which is not on disk must not crash the
    /// render or silently drop the mesh; it falls back to the handed-in skin.
    #[test]
    fn a_named_map_that_is_absent_falls_back_instead_of_vanishing() {
        let path = &crate::fmdl::real_face_fpk();
        if !path.exists() {
            return;
        }
        let mut models = load_scene(path).expect("scene");
        keep_texturable(&mut models);
        let maps = Maps::load(&models, &[std::path::PathBuf::from("Z:/definitely/not/here")]);
        assert_eq!(maps.stats().0, 0, "nothing should resolve against a bogus root");
        let px = render_scene_maps(
            &models,
            None,
            Some(&maps),
            &Camera::front(),
            Mode::Textured,
            96,
            96,
        );
        assert!(coverage(&px) > 0.1, "the head must still draw when no map resolves");
        // The shape is shown untextured rather than painted with a foreign map.
        assert_eq!(maps.stats().0, 0);
    }
}
