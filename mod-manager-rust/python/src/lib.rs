use std::collections::HashSet;
use std::fs;
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

use anyhow::{Context, Result};
use pyo3::exceptions::PyOSError;
use pyo3::prelude::*;
use pyo3::types::{PyBytes, PyDict, PyList};

use fl27mm::{
    ask, assets, binread, conflict, cpk, frig, ftex, gamemap, gani, ini::Ini, menus, order, packs,
    pesdb, render, studio, wesys,
};

fn json_text<T: serde::Serialize>(value: &T) -> Result<String> {
    serde_json::to_string_pretty(value).context("serializing Rust manager report")
}

struct ScanReport {
    active_packs: Vec<String>,
    active_modules: Vec<String>,
    disabled_packs: usize,
    disabled_modules: usize,
    missing: Vec<String>,
    duplicates: Vec<String>,
}

fn scan_report(ini_path: &Path, addons: &Path) -> Result<ScanReport> {
    let ini = Ini::read(ini_path).with_context(|| format!("reading {}", ini_path.display()))?;
    let packs = ini.active("cpk.root");
    let modules = ini.active("lua.module");
    let mut missing = Vec::new();
    let mut duplicates = Vec::new();
    let mut seen_packs = HashSet::new();
    let mut seen_modules = HashSet::new();

    for entry in &packs {
        if !seen_packs.insert(entry.value.to_lowercase()) {
            duplicates.push(format!("pack: {}", entry.value));
        }
        if !order::resolve(addons, &entry.value).is_dir() {
            missing.push(format!("pack: {}", entry.value));
        }
    }

    for entry in &modules {
        if !seen_modules.insert(entry.value.to_lowercase()) {
            duplicates.push(format!("module: {}", entry.value));
        }
        if !addons
            .join("modules")
            .join(entry.value.replace('\\', "/"))
            .is_file()
        {
            missing.push(format!("module: {}", entry.value));
        }
    }

    Ok(ScanReport {
        active_packs: packs.iter().map(|entry| entry.value.clone()).collect(),
        active_modules: modules.iter().map(|entry| entry.value.clone()).collect(),
        disabled_packs: ini.all("cpk.root").len() - packs.len(),
        disabled_modules: ini.all("lua.module").len() - modules.len(),
        missing,
        duplicates,
    })
}

#[pyfunction]
fn scan(py: Python<'_>, ini_path: PathBuf, addons: PathBuf) -> PyResult<Py<PyDict>> {
    let report = py
        .detach(move || scan_report(&ini_path, &addons))
        .map_err(|error| PyOSError::new_err(error.to_string()))?;
    let out = PyDict::new(py);
    out.set_item("active_packs", report.active_packs)?;
    out.set_item("active_modules", report.active_modules)?;
    out.set_item("disabled_packs", report.disabled_packs)?;
    out.set_item("disabled_modules", report.disabled_modules)?;
    out.set_item("missing", report.missing)?;
    out.set_item("duplicates", report.duplicates)?;
    Ok(out.unbind())
}

#[pyfunction]
fn verify(py: Python<'_>, ini_path: PathBuf, addons: PathBuf) -> PyResult<Py<PyDict>> {
    let shadows = py
        .detach(move || {
            let ini =
                Ini::read(&ini_path).with_context(|| format!("reading {}", ini_path.display()))?;
            Ok::<_, anyhow::Error>(order::analyse(&addons, &ini))
        })
        .map_err(|error| PyOSError::new_err(error.to_string()))?;

    let mut dead = 0;
    let mut partial = 0;
    let records = PyList::empty(py);
    for shadow in &shadows {
        dead += usize::from(shadow.dead());
        partial += usize::from(!shadow.dead() && shadow.surviving < shadow.total);
        let item = PyDict::new(py);
        item.set_item("path", &shadow.rel)?;
        item.set_item("total", shadow.total)?;
        item.set_item("surviving", shadow.surviving)?;
        item.set_item("dead", shadow.dead())?;
        item.set_item("blockers", &shadow.blockers)?;
        records.append(item)?;
    }

    let out = PyDict::new(py);
    out.set_item("effective", shadows.len() - dead - partial)?;
    out.set_item("partial", partial)?;
    out.set_item("dead", dead)?;
    out.set_item("packs", records)?;
    Ok(out.unbind())
}

#[pyfunction]
fn conflicts(py: Python<'_>, packs_root: PathBuf) -> PyResult<Py<PyDict>> {
    let (found, keys, report) = py
        .detach(move || {
            if !packs_root.is_dir() {
                anyhow::bail!("pack root is not a directory: {}", packs_root.display());
            }
            let found = packs::discover(&packs_root);
            let keys = conflict::index(&found);
            let report = conflict::analyse(&found, &keys);
            Ok::<_, anyhow::Error>((found, keys, report))
        })
        .map_err(|error| PyOSError::new_err(error.to_string()))?;

    let mut pairs: Vec<_> = report.pairs.iter().collect();
    pairs.sort_by(|a, b| b.1.cmp(a.1));
    let pair_rows: Vec<_> = pairs
        .into_iter()
        .map(|((a, b), count)| (found[*a].rel.clone(), found[*b].rel.clone(), *count))
        .collect();

    let out = PyDict::new(py);
    out.set_item("packs", found.len())?;
    out.set_item("file_keys", keys.len())?;
    out.set_item("shared", report.shared)?;
    out.set_item("identical", report.identical)?;
    out.set_item("differing", report.differing)?;
    out.set_item("pairs", pair_rows)?;
    out.set_item("examples", report.examples)?;
    Ok(out.unbind())
}

fn sorted_root_values(ini_path: &Path, addons: &Path) -> Result<Vec<String>> {
    let ini = Ini::read(ini_path).with_context(|| format!("reading {}", ini_path.display()))?;
    let entries = ini.all("cpk.root").into_iter().cloned().collect::<Vec<_>>();
    Ok(order::sorted(addons, &entries)
        .into_iter()
        .map(|entry| entry.value)
        .collect())
}

#[pyfunction]
fn sorted_roots(py: Python<'_>, ini_path: PathBuf, addons: PathBuf) -> PyResult<Vec<String>> {
    py.detach(move || sorted_root_values(&ini_path, &addons))
        .map_err(|error| PyOSError::new_err(error.to_string()))
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
fn game_map(py: Python<'_>, game: PathBuf) -> PyResult<String> {
    let report = py
        .detach(move || Ok::<_, anyhow::Error>(gamemap::build(&game)))
        .map_err(|error| PyOSError::new_err(error.to_string()))?;
    json_text(&report).map_err(|error| PyOSError::new_err(error.to_string()))
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
fn explain_path(path: String) -> PyResult<String> {
    let info = gamemap::describe(&path);
    json_text(&info).map_err(|error| PyOSError::new_err(error.to_string()))
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

#[pyfunction]
fn pesdb_report(py: Python<'_>, directory: PathBuf) -> PyResult<String> {
    let rows = py
        .detach(move || {
            if !directory.is_dir() {
                anyhow::bail!("table folder is not a directory: {}", directory.display());
            }
            let files = fl27mm::fsutil::files(&directory);
            let mut rows = Vec::new();
            for path in files {
                let name = path.file_name().unwrap_or_default().to_string_lossy();
                if !name.to_ascii_lowercase().ends_with(".bin")
                    || !path
                        .to_string_lossy()
                        .to_ascii_lowercase()
                        .contains("pesdb")
                {
                    continue;
                }
                let verdict = pesdb::validate(&path);
                let status = match verdict.status {
                    pesdb::Status::Ok => "ok",
                    pesdb::Status::BadStride => "badstride",
                    pesdb::Status::Unrecognised => "unrecognised",
                    pesdb::Status::Unreadable => "unreadable",
                };
                rows.push(serde_json::json!({
                    "file": path.strip_prefix(&directory).unwrap_or(&path).to_string_lossy(),
                    "ok": verdict.ok,
                    "status": status,
                    "reason": verdict.reason,
                }));
                if rows.len() >= 5000 {
                    break;
                }
            }
            Ok::<_, anyhow::Error>(rows)
        })
        .map_err(|error| PyOSError::new_err(error.to_string()))?;
    serde_json::to_string_pretty(&rows).map_err(|error| PyOSError::new_err(error.to_string()))
}

#[pyfunction]
fn container_report(py: Python<'_>, input: PathBuf) -> PyResult<String> {
    let rows = py
        .detach(move || {
            let files = if input.is_dir() {
                fl27mm::fsutil::files(&input)
                    .into_iter()
                    .take(5000)
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
                let file = relative.to_string_lossy().into_owned();
                match fs::read(&path) {
                    Err(error) => rows.push(serde_json::json!({
                        "file": file, "framing": "-", "file_size": 0,
                        "body_size": 0, "exact": false, "error": error.to_string()
                    })),
                    Ok(raw) => match wesys::decode(&raw) {
                        Err(error) => rows.push(serde_json::json!({
                            "file": file, "framing": "-", "file_size": raw.len(),
                            "body_size": 0, "exact": false, "error": error.to_string()
                        })),
                        Ok(mut decoded) => {
                            let framing = decoded.kind.name().to_string();
                            let body_size = decoded.body.len();
                            match wesys::encode(&mut decoded) {
                                Ok(_) => rows.push(serde_json::json!({
                                    "file": file, "framing": framing, "file_size": raw.len(),
                                    "body_size": body_size, "exact": decoded.exact,
                                    "level": decoded.level, "error": null
                                })),
                                Err(error) => rows.push(serde_json::json!({
                                    "file": file, "framing": framing, "file_size": raw.len(),
                                    "body_size": body_size, "exact": false,
                                    "level": null, "error": error.to_string()
                                })),
                            }
                        }
                    },
                }
            }
            Ok::<_, anyhow::Error>(rows)
        })
        .map_err(|error| PyOSError::new_err(error.to_string()))?;
    serde_json::to_string_pretty(&rows).map_err(|error| PyOSError::new_err(error.to_string()))
}

#[pyfunction]
fn container_unwrap(py: Python<'_>, input: PathBuf, destination: PathBuf) -> PyResult<usize> {
    py.detach(move || {
        if destination.exists() {
            anyhow::bail!("destination already exists: {}", destination.display());
        }
        let raw = fs::read(&input).with_context(|| format!("reading {}", input.display()))?;
        let decoded = wesys::decode(&raw)?;
        if decoded.kind.name() == "unknown" {
            anyhow::bail!("unidentified framing; refusing to write an unknown body");
        }
        fs::write(&destination, &decoded.body)
            .with_context(|| format!("writing {}", destination.display()))?;
        Ok::<_, anyhow::Error>(decoded.body.len())
    })
    .map_err(|error| PyOSError::new_err(error.to_string()))
}

#[pyfunction]
fn container_rewrap(
    py: Python<'_>,
    body: PathBuf,
    original: PathBuf,
    destination: PathBuf,
) -> PyResult<String> {
    let report = py
        .detach(move || {
            if destination.exists() {
                anyhow::bail!("destination already exists: {}", destination.display());
            }
            let raw =
                fs::read(&original).with_context(|| format!("reading {}", original.display()))?;
            let mut decoded = wesys::decode(&raw)?;
            decoded.body =
                fs::read(&body).with_context(|| format!("reading {}", body.display()))?;
            let wrapped = wesys::encode(&mut decoded)?;
            fs::write(&destination, &wrapped)
                .with_context(|| format!("writing {}", destination.display()))?;
            Ok::<_, anyhow::Error>(serde_json::json!({
                "file": destination.to_string_lossy(),
                "framing": decoded.kind.name(),
                "file_size": wrapped.len(),
                "body_size": decoded.body.len(),
                "exact": decoded.exact,
                "level": decoded.level,
            }))
        })
        .map_err(|error| PyOSError::new_err(error.to_string()))?;
    serde_json::to_string_pretty(&report).map_err(|error| PyOSError::new_err(error.to_string()))
}

#[pyfunction]
fn inspect_binary(py: Python<'_>, path: PathBuf) -> PyResult<String> {
    let report = py
        .detach(move || binread::read(&path))
        .map_err(|error| PyOSError::new_err(error.to_string()))?;
    json_text(&report).map_err(|error| PyOSError::new_err(error.to_string()))
}

#[pyfunction]
fn binary_hex(
    py: Python<'_>,
    path: PathBuf,
    offset: Option<usize>,
    length: Option<usize>,
) -> PyResult<String> {
    py.detach(move || {
        let raw = fs::read(&path).with_context(|| format!("reading {}", path.display()))?;
        let body = wesys::decode(&raw)?.body;
        Ok::<_, anyhow::Error>(binread::hexdump(
            &body,
            offset.unwrap_or(0),
            length.unwrap_or(512),
        ))
    })
    .map_err(|error| PyOSError::new_err(error.to_string()))
}

#[pyfunction]
fn binary_section(
    py: Python<'_>,
    path: PathBuf,
    index: usize,
    length: Option<usize>,
) -> PyResult<String> {
    let text = py
        .detach(move || {
            let data = binread::section_bytes(&path, index)?;
            Ok::<_, anyhow::Error>(binread::hexdump(&data, 0, length.unwrap_or(512)))
        })
        .map_err(|error| PyOSError::new_err(error.to_string()))?;
    Ok(text)
}

#[pyfunction]
fn binary_section_table(py: Python<'_>, path: PathBuf, index: usize) -> PyResult<String> {
    let report = py
        .detach(move || {
            let data = binread::section_bytes(&path, index)?;
            let binary = binread::read(&path)?;
            let name = binary
                .sections
                .as_ref()
                .and_then(|table| table.sections.get(index))
                .map(|section| section.name.clone())
                .unwrap_or_default();
            let plausible_floats = data
                .chunks_exact(4)
                .map(|chunk| f32::from_le_bytes([chunk[0], chunk[1], chunk[2], chunk[3]]))
                .filter(|value| {
                    value.is_finite() && (*value == 0.0 || (1e-4..=1e9).contains(&value.abs()))
                })
                .count();
            let found = match fl27mm::structure::infer_block(&data) {
                Some((count, row, values)) => Some((row, count, values)),
                None => fl27mm::structure::best_row_width(&data).map(|(row, rows)| {
                    let values = data
                        .chunks_exact(4)
                        .map(|chunk| f32::from_le_bytes([chunk[0], chunk[1], chunk[2], chunk[3]]))
                        .collect::<Vec<_>>();
                    (row, rows, values)
                }),
            };
            let (table, values) = match found {
                Some((row, rows, values)) => {
                    (Some((rows, row)), values.into_iter().take(1024).collect())
                }
                None => (None, Vec::new()),
            };
            Ok::<_, anyhow::Error>(serde_json::json!({
                "name": name,
                "bytes": data.len(),
                "table": table,
                "values": values,
                "plausible_floats": plausible_floats,
            }))
        })
        .map_err(|error| PyOSError::new_err(error.to_string()))?;
    serde_json::to_string_pretty(&report).map_err(|error| PyOSError::new_err(error.to_string()))
}

#[pyfunction]
fn patch_binary(py: Python<'_>, path: PathBuf, offset: usize, hex: String) -> PyResult<String> {
    let report = py
        .detach(move || {
            let bytes: Option<Vec<u8>> = hex
                .as_bytes()
                .chunks(2)
                .map(|chunk| {
                    std::str::from_utf8(chunk)
                        .ok()
                        .and_then(|part| u8::from_str_radix(part, 16).ok())
                })
                .collect();
            let Some(bytes) = bytes else {
                anyhow::bail!("{hex:?} is not an even number of hex digits");
            };
            if bytes.is_empty() {
                anyhow::bail!("nothing to write");
            }
            let backup = path.with_extension("bin.fl27mm-backup");
            if !backup.exists() {
                fs::copy(&path, &backup)
                    .with_context(|| format!("backing up {}", path.display()))?;
            }
            let (changed, size) = binread::patch(&path, offset, &bytes)?;
            Ok::<_, anyhow::Error>(serde_json::json!({
                "changed": changed,
                "size": size,
                "backup": backup.to_string_lossy(),
            }))
        })
        .map_err(|error| PyOSError::new_err(error.to_string()))?;
    serde_json::to_string_pretty(&report).map_err(|error| PyOSError::new_err(error.to_string()))
}

#[pyfunction]
fn assets_list(py: Python<'_>, root: PathBuf, limit: Option<usize>) -> PyResult<String> {
    let rows = py
        .detach(move || {
            if !root.is_dir() {
                anyhow::bail!("asset folder is not a directory: {}", root.display());
            }
            let cap = limit.unwrap_or(600).clamp(1, 5000);
            let items = fl27mm::fsutil::files(&root)
                .into_iter()
                .filter_map(|path| assets::entry(&path))
                .take(cap)
                .collect::<Vec<_>>();
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
fn animation_read(py: Python<'_>, path: PathBuf) -> PyResult<String> {
    py.detach(move || {
        let bytes = fs::read(&path).with_context(|| format!("reading {}", path.display()))?;
        let clip = gani::Clip::parse(&bytes)?;
        let summary = gani::describe(&clip);
        let tracks = gani::tracks(&bytes, &clip)?;
        Ok::<_, anyhow::Error>(format!("{summary}\n\n{tracks}"))
    })
    .map_err(|error| PyOSError::new_err(error.to_string()))
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

#[pyfunction]
fn menu_check(py: Python<'_>, root: PathBuf, bases: Vec<PathBuf>) -> PyResult<String> {
    let result = py
        .detach(move || {
            let screens = menus::load(&root)?;
            let mut report = menus::validate_with(&screens, &bases);
            report.root = root.to_string_lossy().into_owned();
            let entries = screens
                .iter()
                .take(400)
                .map(|(id, screen)| {
                    serde_json::json!({
                        "id": id,
                        "events": screen.events.iter().map(|(name, event)| {
                            serde_json::json!({
                                "name": name,
                                "to": event.to.clone().unwrap_or_default(),
                            })
                        }).collect::<Vec<_>>(),
                    })
                })
                .collect::<Vec<_>>();
            Ok::<_, anyhow::Error>(serde_json::json!({
                "report": report,
                "entries": entries,
            }))
        })
        .map_err(|error| PyOSError::new_err(error.to_string()))?;
    serde_json::to_string_pretty(&result).map_err(|error| PyOSError::new_err(error.to_string()))
}

#[pyfunction]
fn menu_link(
    py: Python<'_>,
    root: PathBuf,
    bases: Vec<PathBuf>,
    screen: String,
    event: String,
    target: String,
) -> PyResult<String> {
    py.detach(move || {
        let screens = menus::load(&root)?;
        if !menus::target_known(&screens, &bases, &target) {
            anyhow::bail!(
                "{target} is not a screen in this set or the base folders; no change was made"
            );
        }
        let edited = menus::set_target(&screens, &screen, &event, &target, true)?;
        let stamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .context("reading system clock for menu backup name")?
            .as_nanos();
        let backup = edited
            .path
            .with_extension(format!("json.fl27mm-backup-{stamp}"));
        fs::copy(&edited.path, &backup)
            .with_context(|| format!("backing up {}", edited.path.display()))?;
        menus::write(&edited)?;
        Ok(format!(
            "{screen} · {event} -> {target}\nBackup: {}",
            backup.display()
        ))
    })
    .map_err(|error| PyOSError::new_err(error.to_string()))
}

#[pyfunction]
fn studio_tree(py: Python<'_>, root: PathBuf) -> PyResult<String> {
    let nodes = py
        .detach(move || studio::tree(&root))
        .map_err(|error| PyOSError::new_err(error.to_string()))?;
    json_text(&nodes).map_err(|error| PyOSError::new_err(error.to_string()))
}

#[pyfunction]
fn studio_read(py: Python<'_>, path: PathBuf) -> PyResult<String> {
    let text_file = py
        .detach(move || studio::read_text(&path))
        .map_err(|error| PyOSError::new_err(error.to_string()))?;
    json_text(&text_file).map_err(|error| PyOSError::new_err(error.to_string()))
}

#[pyfunction]
fn studio_write(py: Python<'_>, path: PathBuf, text: String) -> PyResult<usize> {
    py.detach(move || studio::write_text(&path, &text))
        .map_err(|error| PyOSError::new_err(error.to_string()))
}

#[pyfunction]
fn studio_new_pack(
    py: Python<'_>,
    addons: PathBuf,
    name: String,
    kind: String,
) -> PyResult<String> {
    let scaffold = py
        .detach(move || studio::new_pack(&addons, &name, &kind))
        .map_err(|error| PyOSError::new_err(error.to_string()))?;
    json_text(&scaffold).map_err(|error| PyOSError::new_err(error.to_string()))
}

#[pyfunction]
fn studio_check_pack(py: Python<'_>, directory: PathBuf, addons: PathBuf) -> PyResult<String> {
    let report = py
        .detach(move || studio::check_pack(&directory, &addons))
        .map_err(|error| PyOSError::new_err(error.to_string()))?;
    json_text(&report).map_err(|error| PyOSError::new_err(error.to_string()))
}

#[pyfunction]
fn studio_install(py: Python<'_>, source: PathBuf, addons: PathBuf) -> PyResult<String> {
    let report = py
        .detach(move || studio::install_pack(&source, &addons))
        .map_err(|error| PyOSError::new_err(error.to_string()))?;
    json_text(&report).map_err(|error| PyOSError::new_err(error.to_string()))
}

#[pyfunction]
fn studio_entries(py: Python<'_>, addons: PathBuf) -> PyResult<String> {
    let entries = py
        .detach(move || studio::entries(&addons))
        .map_err(|error| PyOSError::new_err(error.to_string()))?;
    json_text(&entries).map_err(|error| PyOSError::new_err(error.to_string()))
}

#[pyfunction]
fn studio_kinds(_py: Python<'_>) -> PyResult<String> {
    let kinds = ["cpk", "lua", "mesh", "generic"]
        .iter()
        .map(|kind| {
            let (hint, hook, layout) = studio::kind_hint(kind);
            serde_json::json!({
                "kind": kind,
                "hint": hint,
                "hook": hook,
                "layout": layout,
            })
        })
        .collect::<Vec<_>>();
    serde_json::to_string_pretty(&kinds).map_err(|error| PyOSError::new_err(error.to_string()))
}

#[pyfunction]
fn studio_create_file(py: Python<'_>, path: PathBuf) -> PyResult<u64> {
    py.detach(move || studio::create_file(&path))
        .map_err(|error| PyOSError::new_err(error.to_string()))
}

#[pyfunction]
fn studio_rename(
    py: Python<'_>,
    from: PathBuf,
    to: PathBuf,
    workspace: PathBuf,
) -> PyResult<String> {
    py.detach(move || {
        let root = workspace.canonicalize()?;
        let source = from.canonicalize()?;
        let parent = to
            .parent()
            .context("rename destination has no parent")?
            .canonicalize()?;
        anyhow::ensure!(
            source != root && source.starts_with(&root) && parent.starts_with(&root),
            "rename paths must stay inside the selected workspace"
        );
        studio::rename(&from, &to)
    })
    .map_err(|error| PyOSError::new_err(error.to_string()))
}

#[pyfunction]
fn studio_remove(py: Python<'_>, path: PathBuf, workspace: PathBuf) -> PyResult<String> {
    py.detach(move || studio::remove(&path, &workspace))
        .map_err(|error| PyOSError::new_err(error.to_string()))
}

#[pyfunction]
fn studio_edit(
    py: Python<'_>,
    addons: PathBuf,
    key: String,
    value: String,
    mode: String,
    apply: bool,
) -> PyResult<String> {
    let report = py
        .detach(move || studio::edit(&addons, &key, &value, &mode, apply))
        .map_err(|error| PyOSError::new_err(error.to_string()))?;
    json_text(&report).map_err(|error| PyOSError::new_err(error.to_string()))
}

#[pymodule]
fn _fl27mm(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(scan, module)?)?;
    module.add_function(wrap_pyfunction!(verify, module)?)?;
    module.add_function(wrap_pyfunction!(conflicts, module)?)?;
    module.add_function(wrap_pyfunction!(sorted_roots, module)?)?;
    module.add_function(wrap_pyfunction!(cpk_inspect, module)?)?;
    module.add_function(wrap_pyfunction!(cpk_extract, module)?)?;
    module.add_function(wrap_pyfunction!(cpk_pack, module)?)?;
    module.add_function(wrap_pyfunction!(game_map, module)?)?;
    module.add_function(wrap_pyfunction!(archive_map, module)?)?;
    module.add_function(wrap_pyfunction!(explain_path, module)?)?;
    module.add_function(wrap_pyfunction!(texture_info, module)?)?;
    module.add_function(wrap_pyfunction!(texture_preview, module)?)?;
    module.add_function(wrap_pyfunction!(convert_texture, module)?)?;
    module.add_function(wrap_pyfunction!(convert_textures, module)?)?;
    module.add_function(wrap_pyfunction!(pesdb_report, module)?)?;
    module.add_function(wrap_pyfunction!(container_report, module)?)?;
    module.add_function(wrap_pyfunction!(container_unwrap, module)?)?;
    module.add_function(wrap_pyfunction!(container_rewrap, module)?)?;
    module.add_function(wrap_pyfunction!(inspect_binary, module)?)?;
    module.add_function(wrap_pyfunction!(binary_hex, module)?)?;
    module.add_function(wrap_pyfunction!(binary_section, module)?)?;
    module.add_function(wrap_pyfunction!(binary_section_table, module)?)?;
    module.add_function(wrap_pyfunction!(patch_binary, module)?)?;
    module.add_function(wrap_pyfunction!(assets_list, module)?)?;
    module.add_function(wrap_pyfunction!(asset_preview, module)?)?;
    module.add_function(wrap_pyfunction!(asset_replace, module)?)?;
    module.add_function(wrap_pyfunction!(animation_read, module)?)?;
    module.add_function(wrap_pyfunction!(animation_report, module)?)?;
    module.add_function(wrap_pyfunction!(animation_set_key, module)?)?;
    module.add_function(wrap_pyfunction!(animation_set_rate, module)?)?;
    module.add_function(wrap_pyfunction!(rig_inspect, module)?)?;
    module.add_function(wrap_pyfunction!(menu_check, module)?)?;
    module.add_function(wrap_pyfunction!(menu_link, module)?)?;
    module.add_function(wrap_pyfunction!(studio_tree, module)?)?;
    module.add_function(wrap_pyfunction!(studio_read, module)?)?;
    module.add_function(wrap_pyfunction!(studio_write, module)?)?;
    module.add_function(wrap_pyfunction!(studio_new_pack, module)?)?;
    module.add_function(wrap_pyfunction!(studio_check_pack, module)?)?;
    module.add_function(wrap_pyfunction!(studio_install, module)?)?;
    module.add_function(wrap_pyfunction!(studio_entries, module)?)?;
    module.add_function(wrap_pyfunction!(studio_kinds, module)?)?;
    module.add_function(wrap_pyfunction!(studio_create_file, module)?)?;
    module.add_function(wrap_pyfunction!(studio_rename, module)?)?;
    module.add_function(wrap_pyfunction!(studio_remove, module)?)?;
    module.add_function(wrap_pyfunction!(studio_edit, module)?)?;
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
    fn scan_reports_missing_and_duplicate_entries() {
        let root = temp_dir("scan");
        let _ = fs::remove_dir_all(&root);
        let addons = root.join("SiderAddons");
        fs::create_dir_all(addons.join("livecpk/Present")).unwrap();
        fs::create_dir_all(addons.join("modules")).unwrap();
        fs::write(
            addons.join("sider.ini"),
            "[sider]\ncpk.root = \".\\livecpk\\Present\"\ncpk.root = \".\\livecpk\\Present\"\nlua.module = \"missing.lua\"\n; lua.module = \"disabled.lua\"\n",
        )
        .unwrap();

        let report = scan_report(&addons.join("sider.ini"), &addons).unwrap();
        assert_eq!(report.active_packs.len(), 2);
        assert_eq!(report.disabled_modules, 1);
        assert_eq!(report.missing, vec!["module: missing.lua"]);
        assert_eq!(report.duplicates, vec!["pack: .\\livecpk\\Present"]);
        let _ = fs::remove_dir_all(root);
    }

    #[test]
    fn root_sorting_keeps_disabled_entries_and_sorts_by_file_coverage() {
        let root = temp_dir("order");
        let _ = fs::remove_dir_all(&root);
        let addons = root.join("SiderAddons");
        fs::create_dir_all(addons.join("livecpk/Many")).unwrap();
        fs::create_dir_all(addons.join("livecpk/One")).unwrap();
        fs::write(addons.join("livecpk/Many/a.bin"), b"a").unwrap();
        fs::write(addons.join("livecpk/Many/b.bin"), b"b").unwrap();
        fs::write(addons.join("livecpk/One/a.bin"), b"a").unwrap();
        let ini_path = addons.join("sider.ini");
        fs::write(
            &ini_path,
            "[sider]\ncpk.root = \".\\livecpk\\Many\"\n; cpk.root = \".\\livecpk\\One\"\n",
        )
        .unwrap();

        assert_eq!(
            sorted_root_values(&ini_path, &addons).unwrap(),
            vec![".\\livecpk\\One", ".\\livecpk\\Many"]
        );
        let _ = fs::remove_dir_all(root);
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
