use std::fs;
use std::path::{Path, PathBuf};


use anyhow::{Context, Result};
use pyo3::exceptions::PyOSError;
use pyo3::prelude::*;
use pyo3::types::{PyBytes, PyDict};

use fl27mm::{ask, assets, cpk, frig, ftex, gamemap, gani, render};

fn json_text<T: serde::Serialize>(value: &T) -> Result<String> {
    serde_json::to_string_pretty(value).context("serializing Rust manager report")
}

#[pyfunction]
fn cpk_inspect(py: Python<'_>, path: PathBuf) -> PyResult<Py<PyDict>> {
    let (summary, rows, total) = py
        .detach(move || {
            let archive = cpk::Cpk::open(&path)?;
            let summary = archive.summary();
            let total = archive.files.len();
            let rows = archive
                .files
                .iter()
                .take(2000)
                .map(|entry| {
                    (
                        entry.path(),
                        entry.size,
                        entry.extract_size,
                        entry.compressed(),
                    )
                })
                .collect::<Vec<_>>();
            Ok::<_, anyhow::Error>((summary, rows, total))
        })
        .map_err(|error| PyOSError::new_err(error.to_string()))?;

    let out = PyDict::new(py);
    out.set_item("entries", summary.entries)?;
    out.set_item("compressed", summary.compressed)?;
    out.set_item("unpacked_bytes", summary.unpacked)?;
    out.set_item(
        "folders",
        summary
            .folders
            .iter()
            .map(|folder| (&folder.name, folder.files, folder.bytes))
            .collect::<Vec<_>>(),
    )?;
    out.set_item(
        "extensions",
        summary
            .extensions
            .iter()
            .map(|extension| (&extension.ext, extension.count))
            .collect::<Vec<_>>(),
    )?;
    out.set_item("files", rows)?;
    out.set_item("files_shown", total.min(2000))?;
    out.set_item("files_total", total)?;
    Ok(out.unbind())
}

fn safe_cpk_entry_path(entry: &str) -> Result<PathBuf> {
    let relative = entry.replace('\\', "/");
    let path = Path::new(&relative);
    if path
        .components()
        .any(|component| !matches!(component, std::path::Component::Normal(_)))
    {
        anyhow::bail!("unsafe path in CPK entry: {entry}");
    }
    Ok(path.to_path_buf())
}

fn extract_cpk(path: &Path, output: &Path, filter: Option<&str>) -> Result<(usize, PathBuf)> {
    let archive = cpk::Cpk::open(path)?;
    if !output.is_dir() {
        anyhow::bail!(
            "extraction destination is not a directory: {}",
            output.display()
        );
    }
    let stem = path
        .file_stem()
        .filter(|stem| !stem.is_empty())
        .context("CPK path has no file name")?;
    let root = output.join(stem);
    fs::create_dir(&root)
        .with_context(|| format!("creating extraction directory {}", root.display()))?;

    let result = (|| {
        let mut done = 0;
        for entry in &archive.files {
            let entry_name = entry.path();
            if filter.is_some_and(|query| {
                !query.is_empty() && !entry_name.to_lowercase().contains(&query.to_lowercase())
            }) {
                continue;
            }
            let relative_path = safe_cpk_entry_path(&entry.path())?;
            let destination = root.join(relative_path);
            if let Some(parent) = destination.parent() {
                fs::create_dir_all(parent)?;
            }
            fs::write(
                &destination,
                archive
                    .read_file(entry)
                    .with_context(|| format!("extracting {entry_name}"))?,
            )
            .with_context(|| format!("writing {}", destination.display()))?;
            done += 1;
        }
        Ok::<_, anyhow::Error>(done)
    })();

    match result {
        Ok(done) => Ok((done, root)),
        Err(error) => {
            fs::remove_dir_all(&root).with_context(|| {
                format!("cleaning up incomplete extraction at {}", root.display())
            })?;
            Err(error)
        }
    }
}

#[pyfunction]
fn cpk_extract(
    py: Python<'_>,
    path: PathBuf,
    output: PathBuf,
    filter: Option<String>,
) -> PyResult<(usize, String)> {
    let (count, root) = py
        .detach(move || extract_cpk(&path, &output, filter.as_deref()))
        .map_err(|error| PyOSError::new_err(error.to_string()))?;
    Ok((count, root.to_string_lossy().into_owned()))
}

#[pyfunction]
fn cpk_pack(
    py: Python<'_>,
    source: PathBuf,
    destination: PathBuf,
    compress: bool,
) -> PyResult<usize> {
    py.detach(move || {
        if destination.exists() {
            anyhow::bail!("destination already exists: {}", destination.display());
        }
        cpk::pack(&source, &destination, compress)
    })
    .map_err(|error| PyOSError::new_err(error.to_string()))
}

#[pyfunction]
fn archive_map(py: Python<'_>, archive: PathBuf, depth: Option<usize>) -> PyResult<String> {
    let report = py
        .detach(move || {
            gamemap::archive_map(&archive, depth.unwrap_or(3)).map_err(anyhow::Error::msg)
        })
        .map_err(|error| PyOSError::new_err(error.to_string()))?;
    json_text(&report).map_err(|error| PyOSError::new_err(error.to_string()))
}

#[pyfunction]
fn texture_info(py: Python<'_>, path: PathBuf) -> PyResult<Py<PyDict>> {
    let path_text = path.to_string_lossy().into_owned();
    let (texture, size) = py
        .detach(move || {
            let texture = ftex::Ftex::read(&path)?;
            let size = fs::metadata(&path)
                .with_context(|| format!("statting {}", path.display()))?
                .len();
            Ok::<_, anyhow::Error>((texture, size))
        })
        .map_err(|error| PyOSError::new_err(error.to_string()))?;
    let out = PyDict::new(py);
    out.set_item("path", path_text)?;
    out.set_item("width", texture.width)?;
    out.set_item("height", texture.height)?;
    out.set_item("depth", texture.depth)?;
    out.set_item("format", texture.format.name())?;
    out.set_item("mips", texture.mips.len())?;
    out.set_item("texture_type", texture.texture_type)?;
    out.set_item("version", format!("{:.2}", f32::from_bits(texture.version)))?;
    out.set_item(
        "decoded_bytes",
        texture
            .mips
            .iter()
            .map(|mip| mip.data.len() as u64)
            .sum::<u64>(),
    )?;
    out.set_item("file_bytes", size)?;
    Ok(out.unbind())
}

#[pyfunction]
fn texture_preview(
    py: Python<'_>,
    path: PathBuf,
    level: Option<usize>,
) -> PyResult<(u32, u32, Vec<u8>)> {
    py.detach(move || {
        let texture = ftex::Ftex::read(&path)?;
        texture.to_rgba(level.unwrap_or(0))
    })
    .map_err(|error| PyOSError::new_err(error.to_string()))
}

#[pyfunction]
fn convert_texture(py: Python<'_>, source: PathBuf, destination: PathBuf) -> PyResult<String> {
    py.detach(move || {
        if destination.exists() {
            anyhow::bail!("destination already exists: {}", destination.display());
        }
        let extension = source
            .extension()
            .and_then(|value| value.to_str())
            .unwrap_or("")
            .to_ascii_lowercase();
        match extension.as_str() {
            "ftex" => {
                let texture = ftex::Ftex::read(&source)?;
                fs::write(&destination, texture.to_dds())
                    .with_context(|| format!("writing {}", destination.display()))?;
            }
            "dds" => {
                let bytes =
                    fs::read(&source).with_context(|| format!("reading {}", source.display()))?;
                let texture = ftex::Ftex::from_dds(&bytes)?;
                texture.write_ftex(&destination)?;
            }
            _ => anyhow::bail!("source must be an .ftex or .dds file"),
        }
        Ok::<_, anyhow::Error>(destination.to_string_lossy().into_owned())
    })
    .map_err(|error| PyOSError::new_err(error.to_string()))
}

#[pyfunction]
fn convert_textures(
    py: Python<'_>,
    input: PathBuf,
    output: PathBuf,
    kind: String,
) -> PyResult<String> {
    let rows = py
        .detach(move || {
            let tag: u32 = match kind.as_str() {
                "normal" => 9,
                "material" => 1,
                "cube" => 7,
                _ => 3,
            };
            let files = if input.is_dir() {
                fl27mm::fsutil::files(&input)
                    .into_iter()
                    .filter(|path| {
                        matches!(
                            path.extension()
                                .and_then(|ext| ext.to_str())
                                .unwrap_or("")
                                .to_ascii_lowercase()
                                .as_str(),
                            "ftex" | "dds"
                        )
                    })
                    .collect::<Vec<_>>()
            } else {
                vec![input.clone()]
            };
            let base = if input.is_dir() {
                input.clone()
            } else {
                input
                    .parent()
                    .unwrap_or_else(|| Path::new("."))
                    .to_path_buf()
            };
            let mut rows = Vec::new();
            for path in files {
                let relative = path.strip_prefix(&base).unwrap_or(&path);
                let relative_text = relative.to_string_lossy().into_owned();
                let extension = path
                    .extension()
                    .and_then(|ext| ext.to_str())
                    .unwrap_or("")
                    .to_ascii_lowercase();
                let destination = output
                    .join(relative)
                    .with_extension(if extension == "ftex" { "dds" } else { "ftex" });
                let result = (|| -> Result<String> {
                    if destination.exists() {
                        anyhow::bail!("output already exists: {}", destination.display());
                    }
                    if let Some(parent) = destination.parent() {
                        fs::create_dir_all(parent)?;
                    }
                    let texture = if extension == "ftex" {
                        let texture = ftex::Ftex::read(&path)?;
                        fs::write(&destination, texture.to_dds())
                            .with_context(|| format!("writing {}", destination.display()))?;
                        texture
                    } else if extension == "dds" {
                        let bytes = fs::read(&path)
                            .with_context(|| format!("reading {}", path.display()))?;
                        let mut texture = ftex::Ftex::from_dds(&bytes)?;
                        texture.texture_type = tag;
                        texture.write_ftex(&destination)?;
                        texture
                    } else {
                        anyhow::bail!("not an FTEX or DDS file: {}", path.display());
                    };
                    Ok(format!(
                        "{}x{} {} {} mips",
                        texture.width,
                        texture.height,
                        texture.format.name(),
                        texture.mips.len()
                    ))
                })();
                match result {
                    Ok(detail) => rows.push((relative_text, true, detail)),
                    Err(error) => rows.push((relative_text, false, error.to_string())),
                }
            }
            Ok::<_, anyhow::Error>(rows)
        })
        .map_err(|error| PyOSError::new_err(error.to_string()))?;
    json_text(&rows).map_err(|error| PyOSError::new_err(error.to_string()))
}

#[pyfunction(signature = (root, limit=None, family=None))]
fn assets_list(
    py: Python<'_>,
    root: PathBuf,
    limit: Option<usize>,
    family: Option<String>,
) -> PyResult<String> {
    let rows = py
        .detach(move || {
            if !root.is_dir() {
                anyhow::bail!("asset folder is not a directory: {}", root.display());
            }
            let cap = limit.unwrap_or(600).clamp(1, 5000);
            let items = fl27mm::fsutil::find_map(&root, cap, |path| {
                if family
                    .as_deref()
                    .is_some_and(|wanted| wanted != assets::family(path).name())
                {
                    return None;
                }
                assets::entry(path)
            });
            let shown = items.len();
            Ok::<_, anyhow::Error>(serde_json::json!({
                "items": items,
                "shown": shown,
                "cap": cap,
            }))
        })
        .map_err(|error| PyOSError::new_err(error.to_string()))?;
    serde_json::to_string_pretty(&rows).map_err(|error| PyOSError::new_err(error.to_string()))
}

#[pyfunction]
fn asset_preview(
    py: Python<'_>,
    model: PathBuf,
    view: String,
    size: usize,
) -> PyResult<(Py<PyBytes>, usize, usize, usize, String)> {
    if !(64..=1024).contains(&size) {
        return Err(PyOSError::new_err(
            "preview size must be between 64 and 1024 pixels",
        ));
    }
    let (png_bytes, files, meshes, vertices, maps) = py
        .detach(move || {
            use render::{Camera, Mode, Texture};
            let mut models = render::load_scene(&model)?;
            render::keep_texturable(&mut models);
            let mapset = render::Maps::load_from(
                &models,
                &render::texture_roots(&model),
                &render::base_archives(&model),
            );
            let camera = match view.as_str() {
                "front" => Camera::front(),
                "back" => Camera::back(),
                "top" => Camera::top(),
                "profile" => Camera::profile(),
                _ => Camera::three_quarter(),
            };
            let fallback = render::skin_for(&model);
            let held: Option<Texture> = fallback.as_ref().map(|(rgba, width, height)| Texture {
                rgba,
                w: *width,
                h: *height,
            });
            let pixels = render::render_scene_maps(
                &models,
                held.as_ref(),
                Some(&mapset),
                &camera,
                Mode::Textured,
                size,
                size,
            );
            let mut png_bytes = Vec::new();
            {
                let mut encoder = png::Encoder::new(&mut png_bytes, size as u32, size as u32);
                encoder.set_color(png::ColorType::Rgba);
                encoder.set_depth(png::BitDepth::Eight);
                encoder.write_header()?.write_image_data(&pixels)?;
            }
            let mesh_list = render::all_meshes(&models);
            let vertices = mesh_list
                .iter()
                .map(|mesh| mesh.positions.len())
                .sum::<usize>();
            let (found, named) = mapset.stats();
            Ok::<_, anyhow::Error>((
                png_bytes,
                models.len(),
                mesh_list.len(),
                vertices,
                format!("{found}/{named} colour maps resolved"),
            ))
        })
        .map_err(|error| PyOSError::new_err(error.to_string()))?;
    Ok((
        PyBytes::new(py, &png_bytes).unbind(),
        files,
        meshes,
        vertices,
        maps,
    ))
}

#[pyfunction]
fn asset_replace(
    py: Python<'_>,
    path: PathBuf,
    width: u32,
    height: u32,
    rgba: Vec<u8>,
) -> PyResult<String> {
    let report = py
        .detach(move || assets::replace(&path, &rgba, width, height))
        .map_err(|error| PyOSError::new_err(error.to_string()))?;
    json_text(&report).map_err(|error| PyOSError::new_err(error.to_string()))
}

#[pyfunction]
fn animation_report(py: Python<'_>, path: PathBuf) -> PyResult<String> {
    let report = py
        .detach(move || {
            let bytes = fs::read(&path).with_context(|| format!("reading {}", path.display()))?;
            let clip = gani::Clip::parse(&bytes)?;
            let units = gani::walk(&bytes)?;
            let tracks = units
                .iter()
                .enumerate()
                .map(|(index, unit)| {
                    let segments = unit
                        .segments
                        .iter()
                        .map(|segment| {
                            let keys = gani::keys_of(
                                &bytes,
                                segment,
                                clip.frame_count as usize,
                                unit.is_static(),
                            )?;
                            Ok::<_, anyhow::Error>(serde_json::json!({
                                "id": segment.segment_id,
                                "kind": segment.kind.name(),
                                "bits": segment.component_bits,
                                "bytes": [segment.blob.0, segment.blob.1],
                                "keys": keys.len(),
                                "first": keys.first().map(|key| key.render()).unwrap_or_default(),
                                "last": keys.last().map(|key| key.render()).unwrap_or_default(),
                            }))
                        })
                        .collect::<Result<Vec<_>>>()?;
                    Ok::<_, anyhow::Error>(serde_json::json!({
                        "index": index,
                        "name": unit.name_code,
                        "static": unit.is_static(),
                        "loops": unit.loops(),
                        "segments": segments,
                    }))
                })
                .collect::<Result<Vec<_>>>()?;
            Ok::<_, anyhow::Error>(serde_json::json!({
                "units": clip.unit_count,
                "segments": clip.segment_count,
                "frames": clip.frame_count,
                "rate": clip.frame_rate,
                "staleSize": clip.size_disagrees(),
                "tracks": tracks,
            }))
        })
        .map_err(|error| PyOSError::new_err(error.to_string()))?;
    serde_json::to_string_pretty(&report).map_err(|error| PyOSError::new_err(error.to_string()))
}

#[pyfunction]
fn animation_set_key(
    py: Python<'_>,
    path: PathBuf,
    unit: usize,
    segment: usize,
    key: usize,
    parts: Vec<u32>,
    signs: Vec<bool>,
) -> PyResult<String> {
    let report = py
        .detach(move || {
            if parts.len() != 3 || signs.len() != 3 {
                anyhow::bail!("a quaternion keyframe needs three components and three signs");
            }
            gani::set_key(
                &path,
                unit,
                segment,
                key,
                gani::KeyValue::Quat {
                    parts: [parts[0], parts[1], parts[2]],
                    signs: [signs[0], signs[1], signs[2]],
                },
            )?;
            let bytes = fs::read(&path).with_context(|| format!("reading {}", path.display()))?;
            let clip = gani::Clip::parse(&bytes)?;
            let units = gani::walk(&bytes)?;
            let unit_data = units
                .get(unit)
                .context("unit went away after writing the key")?;
            let segment_data = unit_data
                .segments
                .get(segment)
                .context("segment went away after writing the key")?;
            let keys = gani::keys_of(
                &bytes,
                segment_data,
                clip.frame_count as usize,
                unit_data.is_static(),
            )?;
            Ok::<_, anyhow::Error>(serde_json::json!({
                "readBack": keys.get(key).map(|value| value.render()).unwrap_or_default(),
                "keys": keys.len(),
            }))
        })
        .map_err(|error| PyOSError::new_err(error.to_string()))?;
    serde_json::to_string_pretty(&report).map_err(|error| PyOSError::new_err(error.to_string()))
}

#[pyfunction]
fn animation_set_rate(py: Python<'_>, path: PathBuf, rate: u32) -> PyResult<(u32, u32)> {
    py.detach(move || gani::set_frame_rate(&path, rate))
        .map_err(|error| PyOSError::new_err(error.to_string()))
}

#[pyfunction]
fn rig_inspect(py: Python<'_>, path: PathBuf) -> PyResult<String> {
    py.detach(move || {
        let extension = path
            .extension()
            .and_then(|value| value.to_str())
            .unwrap_or("")
            .to_ascii_lowercase();
        let bytes = fs::read(&path).with_context(|| format!("reading {}", path.display()))?;
        match extension.as_str() {
            "ask" => {
                let skeleton = ask::Skeleton::parse(&bytes)?;
                let order = skeleton.draw_order()?;
                Ok::<_, anyhow::Error>(format!("{skeleton:#?}\n\nReachable bones: {}", order.len()))
            }
            "frig" => {
                let rig = frig::Rig::parse(&bytes)?;
                Ok(format!("{rig:#?}"))
            }
            _ => anyhow::bail!("choose an .ask skeleton or .frig rig file"),
        }
    })
    .map_err(|error| PyOSError::new_err(error.to_string()))
}

#[pymodule]
fn _fl27mm(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(cpk_inspect, module)?)?;
    module.add_function(wrap_pyfunction!(cpk_extract, module)?)?;
    module.add_function(wrap_pyfunction!(cpk_pack, module)?)?;
    module.add_function(wrap_pyfunction!(archive_map, module)?)?;
    module.add_function(wrap_pyfunction!(texture_info, module)?)?;
    module.add_function(wrap_pyfunction!(texture_preview, module)?)?;
    module.add_function(wrap_pyfunction!(convert_texture, module)?)?;
    module.add_function(wrap_pyfunction!(convert_textures, module)?)?;
    module.add_function(wrap_pyfunction!(assets_list, module)?)?;
    module.add_function(wrap_pyfunction!(asset_preview, module)?)?;
    module.add_function(wrap_pyfunction!(asset_replace, module)?)?;
    module.add_function(wrap_pyfunction!(animation_report, module)?)?;
    module.add_function(wrap_pyfunction!(animation_set_key, module)?)?;
    module.add_function(wrap_pyfunction!(animation_set_rate, module)?)?;
    module.add_function(wrap_pyfunction!(rig_inspect, module)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;

    fn temp_dir(name: &str) -> PathBuf {
        std::env::temp_dir().join(format!("fl27mm-pyo3-{name}-{}", std::process::id()))
    }

    #[test]
    fn cpk_extract_round_trips_into_a_new_archive_named_folder() {
        let root = temp_dir("extract");
        let _ = fs::remove_dir_all(&root);
        let source = root.join("source");
        fs::create_dir_all(source.join("common/script")).unwrap();
        fs::write(source.join("common/script/flow.bin"), b"flow").unwrap();
        let archive = root.join("sample.cpk");
        let output = root.join("output");
        fs::create_dir_all(&output).unwrap();
        cpk::pack(&source, &archive, false).unwrap();

        let (count, extracted) = extract_cpk(&archive, &output, None).unwrap();
        assert_eq!(count, 1);
        assert_eq!(
            fs::read(extracted.join("common/script/flow.bin")).unwrap(),
            b"flow"
        );
        assert!(extract_cpk(&archive, &output, None).is_err());

        fs::write(source.join("common/script/other.bin"), b"other").unwrap();
        let filtered_archive = root.join("filtered.cpk");
        cpk::pack(&source, &filtered_archive, false).unwrap();
        let filtered_output = root.join("filtered-output");
        fs::create_dir_all(&filtered_output).unwrap();
        let (filtered_count, filtered) =
            extract_cpk(&filtered_archive, &filtered_output, Some("FLOW.BIN")).unwrap();
        assert_eq!(filtered_count, 1);
        assert!(filtered.join("common/script/flow.bin").is_file());
        assert!(!filtered.join("common/script/other.bin").exists());
        let _ = fs::remove_dir_all(root);
    }

    #[test]
    fn cpk_entry_paths_cannot_escape_the_extraction_root() {
        assert!(safe_cpk_entry_path("common/script/flow.bin").is_ok());
        assert!(safe_cpk_entry_path("../outside.bin").is_err());
        assert!(safe_cpk_entry_path("common/../../outside.bin").is_err());
        assert!(safe_cpk_entry_path("C:/outside.bin").is_err());
        assert!(safe_cpk_entry_path("/outside.bin").is_err());
    }
}
