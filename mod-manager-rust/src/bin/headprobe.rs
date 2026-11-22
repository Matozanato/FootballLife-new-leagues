//! Renders one head folder to a PNG so the result can be looked at without
//! launching the app. Temporary tool for checking the two-pass renderer.
use fl27mm::render::{self, Camera, Mode, Texture};
use std::path::Path;

fn main() -> anyhow::Result<()> {
    let t0 = std::time::Instant::now();
    let args: Vec<String> = std::env::args().collect();
    let (model, view, out) = (&args[1], args.get(2).cloned().unwrap_or_default(), &args[3]);
    let size = 700;
    let path = Path::new(model);
    let mut models = render::load_scene(path)?;
    eprintln!("load_scene {:?}", t0.elapsed());
    let t1 = std::time::Instant::now();
    let raw = models.clone();
    render::keep_texturable(&mut models);
    let archives = render::base_archives(path);
    eprintln!("archives found: {} in {:?}", archives.len(), t1.elapsed());
    let t2 = std::time::Instant::now();
    let maps = render::Maps::load_from(&models, &render::texture_roots(path), &archives);
    eprintln!("Maps::load_from {:?}", t2.elapsed());
    let t3 = std::time::Instant::now();
    let cam = match view.as_str() {
        "front" => Camera::front(),
        "back" => Camera::back(),
        "top" => Camera::top(),
        "profile" => Camera::profile(),
        _ => Camera::three_quarter(),
    };
    let fallback = render::skin_for(path);
    let held: Option<Texture> =
        fallback
            .as_ref()
            .map(|(rgba, w, h)| Texture { rgba, w: *w, h: *h });
    let (px, skipped) = render::render_report(
        &models,
        held.as_ref(),
        Some(&maps),
        &cam,
        Mode::Textured,
        size,
        size,
    );
    eprintln!("render_report {:?}", t3.elapsed());
    let mut px = px;
    // Flatten onto the background: a viewer that shows transparency as white
    // makes a hair silhouette impossible to judge.
    for p in px.chunks_exact_mut(4) {
        p[3] = 255;
    }
    write_png(out, size, size, &px)?;
    let (found, named) = maps.stats();
    println!(
        "wrote {out}: {} files, {} meshes, {found}/{named} maps resolved, {} skipped",
        models.len(),
        render::all_meshes(&models).len(),
        skipped.len()
    );
    if std::env::var("LIST_TEXTURES").is_ok() {
        for m in &raw {
            for (i, mesh) in m.meshes.iter().enumerate() {
                let mat = m.material(i);
                let name = mat.map(|x| x.name.as_str()).unwrap_or("-");
                let slots = mat
                    .map(|x| {
                        x.slots
                            .iter()
                            .map(|s| format!("{}={}", s.name, s.texture))
                            .collect::<Vec<_>>()
                            .join(" ")
                    })
                    .unwrap_or_default();
                println!(
                    "  mesh {:<2} {:<16} mat {:<26} {}",
                    i, mesh.name, name, slots
                );
            }
        }
        for m in &raw {
            for mat in &m.materials {
                for s in &mat.slots {
                    let stem = std::path::Path::new(&s.texture)
                        .file_stem()
                        .map(|x| x.to_string_lossy().to_lowercase())
                        .unwrap_or_default();
                    let got = maps.texture(&stem).is_some();
                    println!(
                        "  {:<20} {:<28} {}",
                        s.name,
                        s.texture,
                        if got { "FOUND" } else { "missing" }
                    );
                }
            }
        }
    }
    for s in skipped.into_iter().take(8) {
        println!("  skipped {s}");
    }
    Ok(())
}

/// Minimal RGBA PNG: filter-0 scanlines through flate2, with the chunk CRCs
/// computed here because the crate has no PNG encoder as a dependency.
fn write_png(path: &str, w: usize, h: usize, rgba: &[u8]) -> anyhow::Result<()> {
    use flate2::write::ZlibEncoder;
    use flate2::Compression;
    use std::io::Write;

    fn crc32(data: &[u8]) -> u32 {
        let mut table = [0u32; 256];
        for (i, v) in table.iter_mut().enumerate() {
            let mut c = i as u32;
            for _ in 0..8 {
                c = if c & 1 != 0 {
                    0xEDB8_8320 ^ (c >> 1)
                } else {
                    c >> 1
                };
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
