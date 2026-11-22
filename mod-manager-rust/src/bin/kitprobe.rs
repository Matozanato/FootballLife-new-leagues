//! Renders the shirt mesh wearing one kit atlas, to a PNG, without launching
//! the app. Verification for the kit manager: if the atlas and the mesh's UVs
//! disagree, this shows it immediately.
//!
//!   kitprobe <shirt-folder> <atlas.ftex> [view] <out.png>
use fl27mm::render::{self, Camera, Mode};
use std::path::Path;

fn main() -> anyhow::Result<()> {
    let args: Vec<String> = std::env::args().collect();
    let (folder, atlas, rest) = (&args[1], &args[2], &args[3..]);
    let (view, out) = match rest {
        [v, o] => (v.clone(), o.clone()),
        [o] => ("three-quarter".to_string(), o.clone()),
        _ => anyhow::bail!("usage: kitprobe <folder> <atlas.ftex> [view] <out.png>"),
    };

    let t0 = std::time::Instant::now();
    let mut models = render::load_scene(Path::new(folder))?;
    eprintln!("load_scene {:?} ({} models)", t0.elapsed(), models.len());
    render::keep_texturable(&mut models);

    let t = fl27mm::ftex::Ftex::read(Path::new(atlas))?;
    let (w, h, rgba) = t.to_rgba(0)?;
    eprintln!("atlas {}x{}", w, h);
    let tex = render::Texture {
        rgba: &rgba,
        w: w as usize,
        h: h as usize,
    };

    let cam = match view.as_str() {
        "front" => Camera::front(),
        "back" => Camera::back(),
        "profile" => Camera::profile(),
        _ => Camera::three_quarter(),
    };
    let (px, skipped) =
        render::render_report(&models, Some(&tex), None, &cam, Mode::Textured, 700, 700);
    eprintln!("rendered, skipped: {:?}", skipped);

    let mut px = px;
    for p in px.chunks_exact_mut(4) {
        p[3] = 255;
    }
    fl27mm::render::write_png(Path::new(&out), 700, 700, &px)?;
    println!("wrote {out}");
    Ok(())
}
