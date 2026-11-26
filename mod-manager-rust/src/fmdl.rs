//! `FMDL` meshes -- read the shape, change the shape, keep everything else.
//!
//! FL27 stores heads, hair and mouths as `FMDL` version 2.03 payloads inside a
//! `foxfpk`. The section layout below was measured against `face_high.fmdl`
//! from `Asset/model/character/face/real/100006/#Win/face.fpk`: the vertex
//! counts (240, 32, 1794, 68, 138, 184, 40) times the stream sizes close the
//! three GPU buffers to the byte (29968 + 69904 + 26544 = 126416 = the declared
//! buffer length), and the index cursors run cumulatively to 13272 = 26544 / 2.
//!
//! Layout, offsets relative to the section base:
//!
//! ```text
//!  header   56  u32 'FMDL', f32 version, u64 sectionInfoOffset, u64 s0flags,
//!                u64 s1flags, u32 s0count, u32 s1count, u32 s0off, u32 s0len,
//!                u32 s1off, u32 s1len
//!  s0 info   8   u16 type, u16 entryCount, u32 offset     (at sectionInfoOffset)
//!  s1 info  12   u32 type, u32 offset, u32 length
//!
//!  block 3  MeshInfo      48: u16@8 material, u16@10 vertexCount,
//!                               u32@16 firstIndex, u32@20 indexCount, u32@24 index
//!  block 9  MeshFormatInfo 8: u8 meshFormatCount, u8 vertexFormatCount,
//!                               u16@4 firstMeshFormat, u16@6 firstVertexFormat
//!  block 10 MeshFormats    8: u8 bufferIndex, u8 formats, u8 stride, u8 kind,
//!                               u32@4 offset
//!  block 11 VertexFormats  4: u8 type, u8 dataType, u16@2 offset
//!  block 14 BufferOffsets 16: u32 unknown, u32 length, u32 offset
//! ```
//!
//! Editing deliberately works in place: only the position bytes are replaced,
//! so bones, blendshape groups, materials, LODs and the vertex stream keep the
//! bytes the game was shipped with. A head can be reshaped without touching the
//! rig that animates it.

use std::io;

const HEADER: usize = 56;

/// A shipped face folder, used by the tests that need real meshes. Nothing
/// synthesised here can stand in for the geometry the game actually loads.
pub fn real_face_dir() -> std::path::PathBuf {
    crate::install::game_root()
        .join("SiderAddons/livecpk/root/Asset/model/character/face/real/100006")
}

/// The container holding that head.
pub fn real_face_fpk() -> std::path::PathBuf {
    real_face_dir().join("#Win/face.fpk")
}

#[inline]
fn le_u16(b: &[u8], at: usize) -> u16 {
    u16::from_le_bytes([b[at], b[at + 1]])
}
#[inline]
fn le_u32(b: &[u8], at: usize) -> u32 {
    u32::from_le_bytes([b[at], b[at + 1], b[at + 2], b[at + 3]])
}
#[inline]
fn le_f32(b: &[u8], at: usize) -> f32 {
    f32::from_le_bytes([b[at], b[at + 1], b[at + 2], b[at + 3]])
}
/// Half to float without a dependency: decode the sign/exponent/mantissa.
pub fn f16_to_f32(bits: u16) -> f32 {
    let sign = ((bits >> 15) & 1) as f32;
    let exp = ((bits >> 10) & 0x1f) as i32;
    let man = (bits & 0x3ff) as f32;
    let value = if exp == 0 {
        man * 2f32.powi(-24)
    } else if exp == 0x1f {
        if man == 0.0 {
            f32::INFINITY
        } else {
            f32::NAN
        }
    } else {
        (1.0 + man / 1024.0) * 2f32.powi(exp - 15)
    };
    if sign == 1.0 {
        -value
    } else {
        value
    }
}

pub fn f32_to_f16(v: f32) -> u16 {
    let bits = v.to_bits();
    let sign = ((bits >> 16) & 0x8000) as u16;
    let exp = ((bits >> 23) & 0xff) as i32 - 127 + 15;
    let man = bits & 0x7f_ffff;
    if v.is_nan() {
        return 0x7e00;
    }
    if v.is_infinite() {
        return sign | 0x7c00;
    }
    if exp <= 0 {
        return sign; // underflow to signed zero; faces never live here
    }
    if exp >= 0x1f {
        return sign | 0x7c00;
    }
    // Round to nearest, ties away from zero, on the 13 discarded mantissa bits.
    let rounded = man + 0x1000;
    let mut mant = rounded >> 13;
    let mut e = exp;
    if mant > 0x3ff {
        mant = 0;
        e += 1;
        if e >= 0x1f {
            return sign | 0x7c00;
        }
    }
    sign | ((e as u16) << 10) | (mant as u16)
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct V3 {
    pub x: f32,
    pub y: f32,
    pub z: f32,
}

#[allow(clippy::should_implement_trait)] // named methods read better at call sites than operators here
impl V3 {
    pub fn new(x: f32, y: f32, z: f32) -> V3 {
        V3 { x, y, z }
    }
    pub fn add(self, o: V3) -> V3 {
        V3::new(self.x + o.x, self.y + o.y, self.z + o.z)
    }
    pub fn scale(self, s: f32) -> V3 {
        V3::new(self.x * s, self.y * s, self.z * s)
    }
    pub fn dot(self, o: V3) -> f32 {
        self.x * o.x + self.y * o.y + self.z * o.z
    }
    pub fn cross(self, o: V3) -> V3 {
        V3::new(
            self.y * o.z - self.z * o.y,
            self.z * o.x - self.x * o.z,
            self.x * o.y - self.y * o.x,
        )
    }
    pub fn sub(self, o: V3) -> V3 {
        V3::new(self.x - o.x, self.y - o.y, self.z - o.z)
    }
    /// Axis by index, for code that walks 0..3 rather than naming them.
    pub fn at(&self, i: usize) -> f32 {
        match i {
            0 => self.x,
            1 => self.y,
            _ => self.z,
        }
    }
    pub fn norm(self) -> f32 {
        self.dot(self).sqrt()
    }
    pub fn normalized(self) -> V3 {
        let n = self.norm();
        if n > 1e-9 {
            self.scale(1.0 / n)
        } else {
            self
        }
    }
}

#[derive(Debug, Clone)]
pub struct Mesh {
    pub name: String,
    pub material_instance: usize,
    /// Byte length of one vertex in the attribute buffer, so a write can stride
    /// the stream without assuming the 28-byte face layout.
    pub stride: usize,
    pub positions: Vec<V3>,
    /// Interleaved attribute stream, verbatim. UVs live inside it.
    pub attributes: Vec<u8>,
    pub uv_offsets: Vec<usize>,
    pub normal_offset: Option<usize>,
    pub tangent_offset: Option<usize>,
    pub indices: Vec<u16>,
}

#[derive(Debug, Clone)]
pub struct Fmdl {
    pub bytes: Vec<u8>,
    pub version: f32,
    pub meshes: Vec<Mesh>,
    /// Material instances in `MaterialInstances` order; `Mesh::material_instance`
    /// indexes this.
    pub materials: Vec<Material>,
    /// Absolute ranges the position/attribute/index data was read from,
    /// per mesh: position base, attribute base, index base.
    pub spans: Vec<(usize, usize, usize)>,
}

/// A material's shader effect name, if the file carries one.
#[derive(Debug, Clone)]
pub struct Material {
    pub name: String,
    /// Texture bindings, in the order the file lists them. `Base_Tex_SRGB` is
    /// the colour map; `CubeMap_Tex_LIN` is sampled by direction, not by UV.
    pub slots: Vec<Slot>,
}

#[derive(Debug, Clone)]
pub struct Slot {
    pub name: String,
    /// Texture file name as the model refers to it, e.g. `face_bsm_alp.dds`.
    pub texture: String,
    /// Directory the model expects it under.
    pub path: String,
}

impl Material {
    pub fn slot(&self, name: &str) -> Option<&Slot> {
        self.slots.iter().find(|s| s.name == name)
    }
    /// The colour map, when the material has one. A material that only carries
    /// a cube map must not be UV-textured at all.
    pub fn base(&self) -> Option<&Slot> {
        self.slot("Base_Tex_SRGB")
    }
    pub fn normal(&self) -> Option<&Slot> {
        self.slot("NormalMap_Tex_NRM")
    }
}

fn err<T>(msg: impl Into<String>) -> io::Result<T> {
    Err(io::Error::new(io::ErrorKind::InvalidData, msg.into()))
}

/// Read the material instances and resolve each texture slot to a name.
///
/// `MaterialInstances` records are 16 bytes: name index at 0, the count of
/// texture-bearing parameters at 6, other parameters at 7, and the index of the
/// first parameter at 8. Each `MaterialParams` record is a `{slot name, texture
/// index}` pair, and the texture index points into the 16-entry `Textures`
/// block. The counts close: the texture-bearing parameters number exactly as
/// many as there are textures, because every texture is bound once.
fn read_materials(
    bytes: &[u8],
    s0off: usize,
    block: &dyn Fn(usize) -> Option<(usize, usize)>,
    strings: &dyn Fn(usize) -> String,
) -> Vec<Material> {
    let Some((mi_off, mi_count)) = block(4) else { return Vec::new() };
    let (tp_off, tp_count) = block(7).unwrap_or((0, 0));
    let (tx_off, tx_count) = block(6).unwrap_or((0, 0));
    let u16_at = |at: usize| -> usize {
        if at + 2 > bytes.len() {
            return usize::MAX;
        }
        le_u16(bytes, at) as usize
    };
    // (texture name, directory) per `Textures` entry.
    let tex_at = |k: usize| -> (String, String) {
        let at = s0off + tx_off + k * 4;
        (strings(u16_at(at)), strings(u16_at(at + 2)))
    };
    let mut out = Vec::with_capacity(mi_count);
    for i in 0..mi_count {
        let at = s0off + mi_off + i * 16;
        let name = strings(u16_at(at));
        let tex_count = bytes.get(at + 6).copied().unwrap_or(0) as usize;
        let first = u16_at(at + 8);
        let mut slots = Vec::with_capacity(tex_count);
        for k in first..first + tex_count {
            if k >= tp_count {
                break;
            }
            let pat = s0off + tp_off + k * 4;
            let slot = strings(u16_at(pat));
            let ti = u16_at(pat + 2);
            if ti >= tx_count {
                continue;
            }
            let (texture, path) = tex_at(ti);
            slots.push(Slot { name: slot, texture, path });
        }
        out.push(Material { name, slots });
    }
    out
}

impl Mesh {
    /// Read the UV of one vertex; `set` writes it back at the same bytes.
    pub fn uv(&self, v: usize, set: usize) -> Option<[f32; 2]> {
        let off = *self.uv_offsets.get(set)?;
        let at = v.checked_mul(self.stride)?.checked_add(off)?;
        let buf = &self.attributes;
        if at + 4 > buf.len() {
            return None;
        }
        Some([
            f16_to_f32(le_u16(buf, at)),
            f16_to_f32(le_u16(buf, at + 2)),
        ])
    }

    pub fn set_uv(&mut self, v: usize, set: usize, u: f32, vv: f32) {
        let Some(&off) = self.uv_offsets.get(set) else { return };
        let at = v * self.stride + off;
        if at + 4 > self.attributes.len() {
            return;
        }
        let a = f32_to_f16(u);
        let b = f32_to_f16(vv);
        self.attributes[at..at + 2].copy_from_slice(&a.to_le_bytes());
        self.attributes[at + 2..at + 4].copy_from_slice(&b.to_le_bytes());
    }

    /// Unit normal of a vertex from the tangent frame, or from the face
    /// geometry when the stream carries no normal channel.
    pub fn normal(&self, v: usize) -> V3 {
        if let Some(off) = self.normal_offset {
            let at = v * self.stride + off;
            if at + 8 <= self.attributes.len() {
                let n = V3::new(
                    f16_to_f32(le_u16(&self.attributes, at)),
                    f16_to_f32(le_u16(&self.attributes, at + 2)),
                    f16_to_f32(le_u16(&self.attributes, at + 4)),
                );
                let n = n.normalized();
                if n.norm() > 0.5 {
                    return n;
                }
            }
        }
        self.face_normal(v)
    }

    fn face_normal(&self, v: usize) -> V3 {
        let mut acc = V3::new(0.0, 0.0, 0.0);
        let mut seen = false;
        for t in self.indices.chunks(3) {
            if t.len() != 3 || !t.contains(&(v as u16)) {
                continue;
            }
            let [Some(a), Some(b), Some(c)] = [t.first(), t.get(1), t.get(2)] else { continue };
            let (a, b, c) = (*a as usize, *b as usize, *c as usize);
            if a >= self.positions.len() || b >= self.positions.len() || c >= self.positions.len() {
                continue;
            }
            let p = self.positions[a];
            acc = acc.add((self.positions[b].sub(p)).cross(self.positions[c].sub(p)));
            seen = true;
        }
        if seen {
            acc.normalized()
        } else {
            V3::new(0.0, 0.0, 1.0)
        }
    }

    /// Average of the face normals touching a vertex; used after a reshape so
    /// lighting follows the new surface instead of the shipped one.
    pub fn recomputed_normals(&self) -> Vec<V3> {
        let mut acc = vec![V3::new(0.0, 0.0, 0.0); self.positions.len()];
        for t in self.indices.chunks(3) {
            if t.len() != 3 {
                continue;
            }
            let idx: Vec<usize> = t.iter().map(|&i| i as usize).collect();
            if idx.iter().any(|&i| i >= self.positions.len()) {
                continue;
            }
            let p = self.positions[idx[0]];
            let n = (self.positions[idx[1]].sub(p)).cross(self.positions[idx[2]].sub(p));
            for &i in &idx {
                acc[i] = acc[i].add(n);
            }
        }
        acc.into_iter().map(|v| v.normalized()).collect()
    }
}

/// Vertex-channel type ids seen in the wild.
const NORMAL: u8 = 2;
const UV0: u8 = 8;
const TANGENT: u8 = 14;

/// Which of the three GPU buffers carries the index list. Positions and
/// attributes name their buffer in each mesh format; the remaining one holds
/// the u16 triangles, and in every head examined it is the third.
const INDEX_BUFFER: usize = 2;

impl Fmdl {
    pub fn parse(bytes: Vec<u8>) -> io::Result<Fmdl> {
        if bytes.len() < HEADER {
            return err("file is shorter than an FMDL header");
        }
        if &bytes[0..4] != b"FMDL" {
            return err("missing FMDL signature");
        }
        let version = le_f32(&bytes, 4);
        let sio = le_u32(&bytes, 8) as usize;
        let s0count = le_u32(&bytes, 32) as usize;
        let s1count = le_u32(&bytes, 36) as usize;
        let s0off = le_u32(&bytes, 40) as usize;
        let s1off = le_u32(&bytes, 48) as usize;
        if sio + s0count * 8 + s1count * 12 > bytes.len() {
            return err("section info table runs past the end of the file");
        }
        // (type, count, offset within section 0)
        let mut s0 = Vec::with_capacity(s0count);
        for i in 0..s0count {
            let at = sio + i * 8;
            s0.push((le_u16(&bytes, at) as usize, le_u16(&bytes, at + 2) as usize, le_u32(&bytes, at + 4) as usize));
        }
        let mut s1 = Vec::with_capacity(s1count);
        for i in 0..s1count {
            let at = sio + s0count * 8 + i * 12;
            s1.push((le_u32(&bytes, at) as usize, le_u32(&bytes, at + 4) as usize, le_u32(&bytes, at + 8) as usize));
        }
        let block = |kind: usize| -> Option<(usize, usize)> {
            s0.iter().find(|(t, _, _)| *t == kind).map(|(_, c, o)| (*o, *c))
        };
        let buffer = |kind: usize| -> Option<(usize, usize)> {
            s1.iter().find(|(t, _, _)| *t == kind).map(|(_, o, l)| (s1off + *o, *l))
        };

        let Some((mi_off, mi_count)) = block(3) else {
            return Ok(Fmdl { bytes, version, meshes: Vec::new(), materials: Vec::new(), spans: Vec::new() });
        };
        let (mfi_off, mfi_count) = block(9).unwrap_or((0, 0));
        let (mf_off, mf_count) = block(10).unwrap_or((0, 0));
        let (vf_off, vf_count) = block(11).unwrap_or((0, 0));
        let (bo_off, bo_count) = block(14).unwrap_or((0, 0));
        let (str_off, str_count) = block(12).unwrap_or((0, 0));
        let Some((buf_off, _buf_len)) = buffer(2) else {
            return err("no vertex/index buffer block (section 1 type 2)");
        };
        // `StringInfo` entries hold offsets into the section 1 *string* block,
        // not into section 1 itself. Basing them on `s1off` alone reads the
        // vertex bytes as text.
        let str_base = buffer(3).map(|(o, _)| o).unwrap_or(s1off);

        let strings = |idx: usize| -> String {
            if idx >= str_count {
                return String::new();
            }
            let at = s0off + str_off + idx * 8;
            if at + 8 > bytes.len() {
                return String::new();
            }
            let off = str_base + le_u32(&bytes, at + 4) as usize;
            let len = le_u16(&bytes, at + 2) as usize;
            if off + len > bytes.len() {
                return String::new();
            }
            let raw = &bytes[off..off + len];
            let end = raw.iter().position(|&c| c == 0).unwrap_or(raw.len());
            String::from_utf8_lossy(&raw[..end]).to_string()
        };

        let mut buf_index: Vec<(usize, usize)> = Vec::with_capacity(bo_count.max(1));
        for i in 0..bo_count {
            let at = s0off + bo_off + i * 16;
            let len = le_u32(&bytes, at + 4) as usize;
            let off = le_u32(&bytes, at + 8) as usize;
            buf_index.push((buf_off + off, len));
        }

        let mut meshes = Vec::with_capacity(mi_count);
        let mut spans = Vec::with_capacity(mi_count);
        for i in 0..mi_count {
            let at = s0off + mi_off + i * 48;
            if at + 48 > bytes.len() {
                return err("MeshInfo entry runs past the end of section 0");
            }
            let material_instance = le_u16(&bytes, at + 4) as usize;
            let vertex_count = le_u16(&bytes, at + 10) as usize;
            let first_index = le_u32(&bytes, at + 16) as usize;
            let index_count = le_u32(&bytes, at + 20) as usize;

            let fmt_base = if i < mfi_count { s0off + mfi_off + i * 8 } else { 0 };
            let has_fmt = i < mfi_count;
            let (fmt_first, vert_first) = if has_fmt {
                (le_u16(&bytes, fmt_base + 4) as usize, le_u16(&bytes, fmt_base + 6) as usize)
            } else {
                (0, 0)
            };
            let vert_kinds = if has_fmt { bytes[fmt_base + 1] as usize } else { 0 };

            // Positions sit in their own mesh format ahead of the attributes.
            let mut pos_span = (0usize, 0usize);
            let mut attr_span = (0usize, 0usize);
            let mut stride = 0usize;
            for k in 0..3usize {
                let mf = fmt_first + k;
                if mf >= mf_count {
                    continue;
                }
                let at = s0off + mf_off + mf * 8;
                let bi = bytes[at] as usize;
                let st = bytes[at + 2] as usize;
                let off = le_u32(&bytes, at + 4) as usize;
                let Some((base, _)) = buf_index.get(bi) else { continue };
                let abs = base + off;
                if k == 0 {
                    pos_span = (abs, vertex_count * 12);
                } else if k == 1 {
                    attr_span = (abs, vertex_count * st);
                    stride = st;
                }
            }
            let mut uv_offsets = Vec::new();
            let mut normal_offset = None;
            let mut tangent_offset = None;
            for k in 0..vert_kinds {
                let vf = vert_first + k;
                if vf >= vf_count {
                    continue;
                }
                let at = s0off + vf_off + vf * 4;
                let kind = bytes[at];
                let dt = bytes[at + 1];
                let off = le_u16(&bytes, at + 2) as usize;
                if (UV0..=UV0 + 3).contains(&kind) {
                    uv_offsets.push(off);
                } else if kind == NORMAL && dt == 6 {
                    normal_offset.get_or_insert(off);
                } else if kind == TANGENT && dt == 6 {
                    tangent_offset.get_or_insert(off);
                }
            }
            uv_offsets.sort_unstable();

            let end = pos_span.0 + pos_span.1;
            let aend = attr_span.0 + attr_span.1;
            let idx_base = buf_index
                .get(INDEX_BUFFER)
                .map(|(o, _)| *o)
                .unwrap_or(buf_off);
            let iend = idx_base + first_index * 2 + index_count * 2;
            if end > bytes.len() || aend > bytes.len() || iend > bytes.len() || vertex_count == 0 {
                return err(format!(
                    "mesh {i} ranges fall outside the file (positions {pos_span:?} len {}/{} attrs {aend} indices {iend})",
                    pos_span.1,
                    bytes.len()
                )
);
            }
            let positions: Vec<V3> = (0..vertex_count)
                .map(|v| {
                    let at = pos_span.0 + v * 12;
                    V3::new(le_f32(&bytes, at), le_f32(&bytes, at + 4), le_f32(&bytes, at + 8))
                })
                .collect();
            let attributes = bytes[attr_span.0..aend].to_vec();
            let mut indices = Vec::with_capacity(index_count);
            for j in 0..index_count {
                indices.push(le_u16(&bytes, idx_base + first_index * 2 + j * 2));
            }
            meshes.push(Mesh {
                name: strings(i),
                material_instance,
                stride: stride.max(1),
                positions,
                attributes,
                uv_offsets,
                normal_offset,
                tangent_offset,
                indices,
            });
            spans.push((pos_span.0, attr_span.0, idx_base + first_index * 2));
        }
        let materials = read_materials(&bytes, s0off, &block, &strings);
        Ok(Fmdl { bytes, version, meshes, materials, spans })
    }

    pub fn read(path: &std::path::Path) -> io::Result<Fmdl> {
        Fmdl::parse(std::fs::read(path)?)
    }

    pub fn mesh(&self, i: usize) -> io::Result<&Mesh> {
        self.meshes.get(i).ok_or_else(|| io::Error::new(io::ErrorKind::NotFound, format!("no mesh {i}")))
    }

    /// The material one mesh draws with.
    pub fn material(&self, mesh: usize) -> Option<&Material> {
        self.meshes.get(mesh).and_then(|m| self.materials.get(m.material_instance))
    }

    /// The colour map a mesh should be textured with, by name. `None` means the
    /// mesh's material has no UV-sampled colour map — a cube-mapped or unlit
    /// part — and must not be painted with another mesh's texture.
    pub fn base_texture(&self, mesh: usize) -> Option<&str> {
        self.material(mesh)?.base().map(|s| s.texture.as_str())
    }

    /// Textures referenced anywhere in the model, de-duplicated, as
    /// `(file name, directory)`.
    pub fn texture_refs(&self) -> Vec<(String, String)> {
        let mut seen: Vec<(String, String)> = Vec::new();
        for m in &self.materials {
            for s in &m.slots {
                let k = (s.texture.clone(), s.path.clone());
                if !seen.contains(&k) {
                    seen.push(k);
                }
            }
        }
        seen
    }

    /// Replace one mesh's positions in the backing bytes. Writing is a memcpy
    /// into the original span, so the file stays byte-identical wherever the
    /// shape did not move.
    pub fn set_positions(&mut self, i: usize, positions: &[V3]) -> io::Result<()> {
        let Some(&(base, _, _)) = self.spans.get(i) else {
            return err("no such mesh");
        };
        let mesh = self.meshes.get(i).ok_or_else(|| io::Error::new(io::ErrorKind::NotFound, "no such mesh"))?;
        if positions.len() != mesh.positions.len() {
            return err("a reshaped head must keep its vertex count");
        }
        let len = positions.len() * 12;
        if base + len > self.bytes.len() {
            return err("position span falls outside the file");
        }
        for (v, p) in positions.iter().enumerate() {
            let at = base + v * 12;
            self.bytes[at..at + 4].copy_from_slice(&p.x.to_le_bytes());
            self.bytes[at + 4..at + 8].copy_from_slice(&p.y.to_le_bytes());
            self.bytes[at + 8..at + 12].copy_from_slice(&p.z.to_le_bytes());
        }
        // Keep the in-memory copy in step with the file.
        self.meshes[i].positions = positions.to_vec();
        Ok(())
    }

    /// Write the UV channel back into the attribute stream and into the file.
    pub fn set_uv(&mut self, i: usize, v: usize, set: usize, u: f32, vv: f32) -> io::Result<()> {
        let Some(off) = self.meshes.get(i).and_then(|m| m.uv_offsets.get(set).copied()) else {
            return err("that mesh has no such UV channel");
        };
        // UVs live in the attribute buffer, not after the positions.
        let (_, _, attr, _) = self.spans(i).ok_or_else(|| io::Error::new(io::ErrorKind::NotFound, "no such mesh"))?;
        let stride = self.meshes[i].stride;
        let at = attr + v * stride + off;
        if at + 4 > self.bytes.len() {
            return err("UV write falls outside the file");
        }
        let a = f32_to_f16(u);
        let b = f32_to_f16(vv);
        self.bytes[at..at + 2].copy_from_slice(&a.to_le_bytes());
        self.bytes[at + 2..at + 4].copy_from_slice(&b.to_le_bytes());
        self.meshes[i].set_uv(v, set, u, vv);
        Ok(())
    }

    /// Push every position along its normal by `amount(u, v)` in metres. The
    /// topology, bones and materials are not touched.
    pub fn displace_along_normals<F: Fn(f32, f32) -> f32>(&mut self, i: usize, amount: F) -> io::Result<usize> {
        let mesh = self.mesh(i)?.clone();
        let mut moved = 0;
        let mut next = Vec::with_capacity(mesh.positions.len());
        for v in 0..mesh.positions.len() {
            let p = mesh.positions[v];
            let uv = mesh.uv(v, 0).unwrap_or([0.0, 0.0]);
            let d = amount(uv[0], uv[1]);
            if d.abs() > 1e-7 {
                moved += 1;
            }
            next.push(p.add(mesh.normal(v).scale(d)));
        }
        self.set_positions(i, &next)?;
        Ok(moved)
    }

    /// Where a mesh's data lives: position base, position byte length,
    /// attribute base, index base. A writer test uses this to prove a reshape
    /// left everything outside the positions alone.
    pub fn spans(&self, i: usize) -> Option<(usize, usize, usize, usize)> {
        let (pos, attr, idx) = self.spans.get(i).copied()?;
        Some((pos, self.meshes.get(i)?.positions.len() * 12, attr, idx))
    }

    /// Rewrite the normal channel from the new surface, keeping the fourth
    /// component the shader uses. Without this a reshaped head still lights as
    /// though it were the shipped one.
    pub fn refresh_normals(&mut self, i: usize) -> io::Result<()> {
        // Normals are an attribute channel, so every address here is relative to
        // the attribute buffer. Using the position base writes over the shape.
        let (_, _, attr, _) = self.spans(i).ok_or_else(|| io::Error::new(io::ErrorKind::NotFound, "no such mesh"))?;
        let off = match self.meshes.get(i).and_then(|m| m.normal_offset) {
            Some(o) => o,
            None => return Ok(()),
        };
        let stride = self.meshes[i].stride;
        let normals = self.meshes[i].recomputed_normals();
        for (v, n) in normals.iter().enumerate() {
            for k in 0..3 {
                let axis = match k {
                    0 => n.x,
                    1 => n.y,
                    _ => n.z,
                };
                let at = attr + v * stride + off + k * 2;
                if at + 2 > self.bytes.len() {
                    return err("normal write falls outside the file");
                }
                let bits = f32_to_f16(axis).to_le_bytes();
                self.bytes[at] = bits[0];
                self.bytes[at + 1] = bits[1];
            }
        }
        // `attributes` is the mesh's own copy, so its zero is the file's `attr`.
        let len = normals.len() * stride;
        self.meshes[i].attributes[..len].copy_from_slice(&self.bytes[attr..attr + len]);
        Ok(())
    }

    /// Wavefront export, so a decoded head can be looked at and measured in any
    /// 3D tool. Texture coordinates come straight from the shipped stream.
    pub fn to_obj(&self) -> String {
        let mut out = String::from("# FL27 FMDL export\no head\n");
        for m in &self.meshes {
            for p in &m.positions {
                out.push_str(&format!("v {:.6} {:.6} {:.6}\n", p.x, p.y, p.z));
            }
            for v in 0..m.positions.len() {
                if let Some([u, vv]) = m.uv(v, 0) {
                    out.push_str(&format!("vt {:.6} {:.6}\n", u, 1.0 - vv));
                }
            }
        }
        // Vertex and UV numbering runs across the whole file, so a face line can
        // only reference one offset if the meshes are emitted in the same order.
        let mut pos_base = 0usize;
        let mut uv_base = 0usize;
        for m in &self.meshes {
            let uvs: Vec<Option<[f32; 2]>> =
                (0..m.positions.len()).map(|v| m.uv(v, 0)).collect();
            for t in m.indices.chunks(3) {
                if t.len() != 3 {
                    continue;
                }
                let parts: Vec<String> = t
                    .iter()
                    .map(|&i| {
                        let vi = pos_base + i as usize + 1;
                        match uvs.get(i as usize).and_then(|o| *o) {
                            Some(_) => format!("{}/{}", vi, uv_base + i as usize + 1),
                            None => format!("{vi}"),
                        }
                    })
                    .collect();
                out.push_str(&format!("f {}\n", parts.join(" ")));
            }
            pos_base += m.positions.len();
            uv_base += uvs.iter().filter(|o| o.is_some()).count();
        }
        out
    }

    /// Axis-aligned bounds of every position, useful as a sanity check that the
    /// stride was read correctly: a head is about 0.24 m across, not 4000.
    pub fn bounds(&self) -> Option<(V3, V3)> {
        let mut lo = V3::new(f32::MAX, f32::MAX, f32::MAX);
        let mut hi = V3::new(f32::MIN, f32::MIN, f32::MIN);
        let mut any = false;
        for m in &self.meshes {
            for p in &m.positions {
                any = true;
                lo = V3::new(lo.x.min(p.x), lo.y.min(p.y), lo.z.min(p.z));
                hi = V3::new(hi.x.max(p.x), hi.y.max(p.y), hi.z.max(p.z));
            }
        }
        any.then_some((lo, hi))
    }
}

/// Open the shipped head so the tests can assert against real bytes. Not a
/// mock: skips when the game is not installed here.
#[cfg(test)]
fn real_face() -> Option<crate::fpk::Entry> {
    let path = &crate::fmdl::real_face_fpk();
    if !path.exists() {
        return None;
    }
    let fpk = crate::fpk::Fpk::read(path).expect("the shipped face container must parse");
    fpk.find("face_high.fmdl").cloned()
}

#[cfg(test)]
mod tests {
    use super::*;


    #[test]
    fn half_float_round_trips_the_values_channels_actually_hold() {
        for v in [0.0f32, 1.0, -1.0, 0.5, -0.5, 0.25, 2.0, 123.5, 4.0, -3.25] {
            assert_eq!(f16_to_f32(f32_to_f16(v)), v, "{v} did not survive f16");
        }
        // Half has 11 significant bits, so 0.3 lands within one ulp of itself.
        let back = f16_to_f32(f32_to_f16(0.3));
        assert!((back - 0.3).abs() < 0.001, "{back}");
        assert!(f32_to_f16(f32::INFINITY) & 0x7c00 == 0x7c00);
    }

    #[test]
    fn normals_follow_the_winding_of_a_triangle() {
        let m = Mesh {
            name: "t".into(),
            material_instance: 0,
            stride: 0,
            positions: vec![
                V3::new(0.0, 0.0, 0.0),
                V3::new(1.0, 0.0, 0.0),
                V3::new(0.0, 1.0, 0.0),
            ],
            attributes: Vec::new(),
            uv_offsets: Vec::new(),
            normal_offset: None,
            tangent_offset: None,
            indices: vec![0, 2, 1],
        };
        let n = m.recomputed_normals();
        assert!(n[0].z < 0.0, "winding should put the normal behind the triangle");
        assert!(m.normal(0).norm() > 0.9, "a stream with no normal channel falls back to geometry");
    }

    #[test]
    fn rejects_a_file_that_is_not_a_mesh() {
        let err = Fmdl::parse(vec![0u8; 200]).unwrap_err();
        assert!(err.to_string().contains("FMDL"), "{err}");
    }


    #[test]
    fn a_real_head_decodes_to_the_counts_the_buffers_imply() {
        let Some(entry) = real_face() else { return };
        let model = Fmdl::parse(entry.data).expect("face_high.fmdl should parse");
        assert!((model.version - 2.03).abs() < 0.01, "version {}", model.version);
        assert_eq!(model.meshes.len(), 7, "MeshInfo entries");

        let verts: usize = model.meshes.iter().map(|m| m.positions.len()).sum();
        let idxs: usize = model.meshes.iter().map(|m| m.indices.len()).sum();
        // 29968 position bytes / 12 plus 69904 attribute bytes / 28 stride plus
        // 26544 index bytes / 2 are the three buffer lengths measured by hand.
        assert_eq!(verts, 2496, "total vertices");
        assert_eq!(idxs, 13272, "total indices");
        for (i, m) in model.meshes.iter().enumerate() {
            assert_eq!(m.stride, 28, "mesh {i} attribute stride");
            assert_eq!(m.uv_offsets, vec![24], "mesh {i} should expose one UV set");
            assert_eq!(m.normal_offset, Some(0), "mesh {i} normal channel");
            assert_eq!(m.tangent_offset, Some(8), "mesh {i} tangent channel");
            assert!(
                m.indices.iter().all(|&v| (v as usize) < m.positions.len()),
                "mesh {i} indexes outside its own vertex range"
            );
        }

        // A head is about a quarter of a metre across. A wrong stride or a wrong
        // buffer base shows up here as thousands of metres.
        let (lo, hi) = model.bounds().unwrap();
        for axis in [lo.x, lo.y, lo.z, hi.x, hi.y, hi.z] {
            assert!(axis.abs() < 2.0, "coordinate {axis} is not in metres");
        }
        let w = hi.x - lo.x;
        let h = hi.y - lo.y;
        let d = hi.z - lo.z;
        assert!(w > 0.05 && w < 1.0, "width {w}");
        assert!(h > 0.05 && h < 1.0, "height {h}");
        assert!(d > 0.05 && d < 1.0, "depth {d}");

        // UVs are unit-ish texture coordinates, not raw pixels.
        let m0 = model.mesh(0).unwrap();
        for v in 0..m0.positions.len().min(64) {
            let [u, vv] = m0.uv(v, 0).unwrap();
            assert!(u > -4.0 && u < 5.0 && vv > -4.0 && vv < 5.0, "uv {u},{vv}");
        }
        assert!(model.to_obj().contains("f "));
    }

    #[test]
    fn an_unchanged_reshape_leaves_the_file_byte_identical() {
        let Some(entry) = real_face() else { return };
        let original = entry.data.clone();
        let mut model = Fmdl::parse(original.clone()).unwrap();
        let before = model.mesh(2).unwrap().positions.clone();
        model.set_positions(2, &before).unwrap();
        assert_eq!(model.bytes, original, "writing the same shape must not perturb the file");
    }

    #[test]
    fn displacing_a_head_moves_positions_and_keeps_the_rig_bytes() {
        let Some(entry) = real_face() else { return };
        let original = entry.data.clone();
        let mut model = Fmdl::parse(original.clone()).unwrap();
        let moved = model.displace_along_normals(0, |_, _| 0.002).unwrap();
        assert!(moved > 0, "every vertex should have been pushed");
        // The reshape may only rewrite this mesh's 240 positions.
        let (base, len, attr, idx) = model.spans(0).unwrap();
        assert_eq!(len, 240 * 12, "position span for the shipped head");
        let mut touched = 0;
        for (i, (a, b)) in model.bytes.iter().zip(original.iter()).enumerate() {
            if a != b {
                assert!(i >= base && i < base + len, "byte {i} outside {base}..{} was rewritten", base + len);
                touched += 1;
            }
        }
        assert!(touched > 0, "a 2 mm inflation changed nothing");
        assert!(attr > base + len && idx > attr, "buffer ranges must be ordered positions, attributes, indices");
        assert!(idx + model.mesh(0).unwrap().indices.len() * 2 <= original.len());
        let (lo, hi) = model.bounds().unwrap();
        let (olo, ohi) = Fmdl::parse(original).unwrap().bounds().unwrap();
        assert!(hi.x - lo.x > ohi.x - olo.x, "an inflated head must measure larger");
    }

    #[test]
    fn uv_and_normal_writers_land_in_the_attribute_buffer_not_the_positions() {
        let Some(entry) = real_face() else { return };
        let original = entry.data.clone();
        let mut model = Fmdl::parse(original.clone()).unwrap();
        let (pbase, plen, abase, _ibase) = model.spans(0).unwrap();
        let verts = model.mesh(0).unwrap().positions.len();

        // A UV write must never show up in the position span, and must stay
        // inside the four bytes of one half2.
        let uv = model.mesh(0).unwrap().uv(3, 0).unwrap();
        model.set_uv(0, 3, 0, uv[0] + 0.01, uv[1] - 0.01).unwrap();
        assert_eq!(
            &model.bytes[pbase..pbase + plen],
            &original[pbase..pbase + plen],
            "a UV write moved positions"
        );
        let slot = abase + 3 * model.mesh(0).unwrap().stride + model.mesh(0).unwrap().uv_offsets[0];
        let changed: Vec<usize> = (0..model.bytes.len())
            .filter(|i| model.bytes[*i] != original[*i])
            .collect();
        assert!(!changed.is_empty(), "the UV write changed nothing");
        assert!(
            changed.iter().all(|&i| (slot..slot + 4).contains(&i)),
            "the UV write spilled outside {slot}..{}: {changed:?}",
            slot + 4
        );
        let again = model.mesh(0).unwrap().uv(3, 0).unwrap();
        // Half precision at 0.6 has a quantum of 4.9e-4, so the nearest
        // representable answer is allowed to sit half a quantum away.
        assert!((again[0] - (uv[0] + 0.01)).abs() < 3e-4, "{uv:?} -> {again:?}");

        // Re-writing unchanged normals has to be a no-op, which is only true if
        // the shipped stream already agrees with the geometry.
        let mut probe = Fmdl::parse(original.clone()).unwrap();
        let before = probe.bytes.clone();
        probe.refresh_normals(0).unwrap();
        assert_eq!(
            &probe.bytes[pbase..pbase + plen],
            &before[pbase..pbase + plen],
            "refreshing normals rewrote the positions -- the regression that put a head 1.7 m out"
        );
        let drift: usize = probe
            .bytes
            .iter()
            .zip(before.iter())
            .skip(abase)
            .take(verts * 28)
            .filter(|(a, b)| a != b)
            .count();
        assert!(
            drift <= verts * 8,
            "normals rewrote {drift} bytes of a {} byte stream",
            verts * 28
        );
    }
}

#[cfg(test)]
mod material_tests {
    use super::*;

    fn head() -> Option<Fmdl> {
        let entry = real_face()?;
        Fmdl::parse(entry.data).ok()
    }

    /// The binding is only correct if every material resolves to the maps its
    /// name promises. These answers were read off the shipped files by hand.
    #[test]
    fn each_material_resolves_to_its_own_textures() {
        let Some(m) = head() else { return };
        assert_eq!(m.materials.len(), 5, "MaterialInstances");
        let got: Vec<(&str, Option<&str>)> =
            m.materials.iter().map(|mat| (mat.name.as_str(), mat.base().map(|s| s.texture.as_str()))).collect();
        let want = [
            ("fox_skin_mat", Some("face_bsm_alp.dds")),
            ("eyeline_SG", None),
            ("fox_eyelash_mat", Some("face_eyelash_alp.tga")),
            ("collar_ao", Some("dummy.tga")),
            ("fox_eyeOcclusion_mat", Some("eye_occlusion_alp.dds")),
        ];
        assert_eq!(got.len(), want.len());
        for (i, ((gn, gt), (wn, wt))) in got.iter().zip(want.iter()).enumerate() {
            assert_eq!(gn, wn, "material {i} name");
            assert_eq!(gt, wt, "material {i} ({gn}) base map");
        }
        // eyeline_SG binds only a cube map, so UV-sampling a colour map onto it
        // is what produced the shard artefacts.
        let eye = &m.materials[1];
        assert!(eye.base().is_none(), "eyeline must have no colour map");
        assert!(eye.slot("CubeMap_Tex_LIN").is_some(), "eyeline must bind a cube map");
    }

    /// Every texture is bound exactly once across all materials, which is what
    /// makes the counts close and proves the index space is right.
    #[test]
    fn texture_slots_partition_the_texture_block() {
        let Some(m) = head() else { return };
        // 16 bindings, one per texture. The number of *distinct* names is lower
        // because one texture can serve several slots -- face_srm is both the
        // specular and the roughness map of the skin material.
        let bound: Vec<&str> = m.materials.iter().flat_map(|x| x.slots.iter()).map(|s| s.texture.as_str()).collect();
        assert_eq!(bound.len(), 16, "every texture should be bound exactly once");
        assert_eq!(m.texture_refs().len(), 13, "distinct texture names");
        for t in &bound {
            assert!(m.texture_refs().iter().any(|(n, _)| n == t), "{t} bound but not listed");
        }
    }

    /// The mesh→material link is the one field that was previously misread: it
    /// lives at offset 4, not 8.
    #[test]
    fn meshes_point_at_materials_in_range() {
        let Some(m) = head() else { return };
        assert_eq!(m.meshes.len(), 7);
        let big = m.meshes.iter().position(|x| x.positions.len() == 1794).expect("face mesh");
        assert_eq!(m.materials[m.meshes[big].material_instance].name, "fox_skin_mat");
        for (i, mesh) in m.meshes.iter().enumerate() {
            assert!(
                mesh.material_instance < m.materials.len(),
                "mesh {i} selects material {} of {}",
                mesh.material_instance,
                m.materials.len()
            );
        }
    }
}
