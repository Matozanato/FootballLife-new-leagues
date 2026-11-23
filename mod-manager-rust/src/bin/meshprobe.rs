//! Prints mesh facts for one or more model files: mesh names, materials and
//! their texture slots, vertex position bounds and UV bounds. Verification for
//! which meshes can actually wear a kit atlas.
use fl27mm::fmdl::Fmdl;
use std::path::Path;

fn main() -> anyhow::Result<()> {
    for arg in std::env::args().skip(1) {
        let path = Path::new(&arg);
        let files: Vec<_> = if path.is_dir() {
            fl27mm::fsutil::files(path)
        } else {
            vec![path.to_path_buf()]
        };
        for f in files {
            if f.extension().and_then(|e| e.to_str()).map(|e| e.to_lowercase())
                != Some("fmdl".into())
            {
                continue;
            }
            let Ok(m) = Fmdl::read(&f) else { continue };
            println!("{}  ({} meshes, {} materials)", f.display(), m.meshes.len(), m.materials.len());
            for mat in &m.materials {
                let slots: Vec<String> = mat.slots.iter().map(|s| format!("{}={}", s.name, s.texture)).collect();
                println!("  material {:?}  {}", mat.name, slots.join("  "));
            }
            for mesh in &m.meshes {
                let (mut lo, mut hi) = ([f32::MAX; 3], [f32::MIN; 3]);
                for p in &mesh.positions {
                    let c = [p.x, p.y, p.z];
                    for a in 0..3 {
                        lo[a] = lo[a].min(c[a]);
                        hi[a] = hi[a].max(c[a]);
                    }
                }
                let (mut ulo, mut uhi) = ([f32::MAX; 2], [f32::MIN; 2]);
                let mut uvs = 0;
                for v in 0..mesh.positions.len() {
                    for &off in &mesh.uv_offsets {
                        let base = v * mesh.stride + off;
                        if base + 8 <= mesh.attributes.len() {
                            let f = |i: usize| f32::from_le_bytes([
                                mesh.attributes[base + i * 4],
                                mesh.attributes[base + i * 4 + 1],
                                mesh.attributes[base + i * 4 + 2],
                                mesh.attributes[base + i * 4 + 3],
                            ]);
                            let (u, vv) = (f(0), f(1));
                            ulo = [ulo[0].min(u), ulo[1].min(vv)];
                            uhi = [uhi[0].max(u), uhi[1].max(vv)];
                            uvs += 1;
                        }
                    }
                }
                println!(
                    "  mesh {:?}  verts {} tris {}  pos x {:.3}..{:.3} y {:.3}..{:.3} z {:.3}..{:.3}  uv [{:.3},{:.3}]..[{:.3},{:.3}] ({} samples, {} uv sets)",
                    mesh.name, mesh.positions.len(), mesh.indices.len() / 3,
                    lo[0], hi[0], lo[1], hi[1], lo[2], hi[2],
                    ulo[0], ulo[1], uhi[0], uhi[1], uvs, mesh.uv_offsets.len(),
                );
            }
        }
    }
    Ok(())
}
