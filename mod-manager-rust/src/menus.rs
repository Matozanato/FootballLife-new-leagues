//! Menu flow graphs: what a menu maker has to get right.
//!
//! A competition's menu is a folder of small JSON files under
//! `common/script/flow`, one per screen, each naming where its events go. The
//! engine follows `to` at runtime and says nothing when the target is missing,
//! so a pack can ship a screen whose every button is inert and still load
//! perfectly. That is the failure this module exists to catch before install,
//! and it is why validation, not authoring, is the core feature here.
//!
//! Screen ids are the path under `flow` without the extension, so
//! `flow/BL/BLMainMenu.json` is `BL/BLMainMenu` -- the same spelling the files
//! use inside their own `to` fields.

use anyhow::{bail, Context, Result};
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet};
use std::path::{Path, PathBuf};

#[derive(Debug, Clone, Default, Deserialize, Serialize)]
pub struct Event {
    /// Where this event takes the player. Missing or unknown means the engine
    /// has nowhere to go and the button does nothing.
    #[serde(default)]
    pub to: Option<String>,
    #[serde(default)]
    pub go: Option<String>,
    #[serde(default)]
    pub clear: Option<String>,
    #[serde(default, rename = "fadeStart")]
    pub fade_start: Option<String>,
    #[serde(default, rename = "fadeEnd")]
    pub fade_end: Option<String>,
    #[serde(default, rename = "bgType")]
    pub bg_type: Option<String>,
    /// Anything else the author put there, preserved verbatim on write.
    #[serde(flatten)]
    pub extra: serde_json::Map<String, serde_json::Value>,
}

#[derive(Debug, Clone, Default, Deserialize, Serialize)]
pub struct Data {
    #[serde(default)]
    pub r#type: Option<String>,
    #[serde(default, rename = "bgId")]
    pub bg_id: Option<String>,
    #[serde(default)]
    pub dialog: Option<String>,
    #[serde(flatten)]
    pub extra: serde_json::Map<String, serde_json::Value>,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct Screen {
    #[serde(default)]
    pub events: BTreeMap<String, Event>,
    #[serde(default)]
    pub data: Data,
    /// Unknown top-level keys are kept so re-writing a screen never loses fields
    /// this tool has no concept of.
    #[serde(flatten)]
    pub extra: serde_json::Map<String, serde_json::Value>,
    #[serde(skip)]
    pub id: String,
    #[serde(skip)]
    pub path: PathBuf,
}

/// One navigation defect found in a set.
#[derive(Debug, Clone, Serialize)]
pub struct Broken {
    pub screen: String,
    pub event: String,
    pub target: String,
    /// Why this is a problem, in the terms a modder acts on.
    pub why: String,
}

#[derive(Debug, Default, Serialize)]
pub struct Report {
    pub root: String,
    pub screens: usize,
    pub links: usize,
    pub broken: Vec<Broken>,
    /// Screens nothing else points at and which are not a known entry point.
    pub unreachable: Vec<String>,
    pub by_prefix: Vec<(String, usize)>,
}

impl Report {
    pub fn clean(&self) -> bool {
        self.broken.is_empty()
    }
}

/// Read every flow file under `root`. `root` may be a menu-server competition
/// folder or any directory containing `common/script/flow`.
pub fn load(root: &Path) -> Result<BTreeMap<String, Screen>> {
    let flow = find_flow(root)?;
    let mut out = BTreeMap::new();
    for p in crate::fsutil::files(&flow) {
        if p.extension()
            .and_then(|e| e.to_str())
            .map(|e| e.to_lowercase())
            != Some("json".into())
        {
            continue;
        }
        let rel = p.strip_prefix(&flow).unwrap_or(&p);
        let id = rel.with_extension("").to_string_lossy().replace('\\', "/");
        let text =
            std::fs::read_to_string(&p).with_context(|| format!("reading {}", p.display()))?;
        let mut screen: Screen = match serde_json::from_str(&text) {
            Ok(s) => s,
            Err(e) => {
                // A file that is not a flow graph should not stop a whole set
                // being checked; it is reported by the caller's own scan.
                bail!("{} is not a flow graph: {e}", id)
            }
        };
        screen.id = id.clone();
        screen.path = p;
        out.insert(id, screen);
    }
    if out.is_empty() {
        bail!("no flow graphs found under {}", flow.display());
    }
    Ok(out)
}

/// Locate the flow folder, tolerating a root that *is* the flow folder.
fn find_flow(root: &Path) -> Result<PathBuf> {
    let direct = root.join("common/script/flow");
    if direct.is_dir() {
        return Ok(direct);
    }
    if root.file_name().map(|n| n == "flow").unwrap_or(false) && root.is_dir() {
        return Ok(root.to_path_buf());
    }
    // Some packs lay flow out without the `common` prefix.
    for cand in ["script/flow", "flow"] {
        let p = root.join(cand);
        if p.is_dir() {
            return Ok(p);
        }
    }
    bail!(
        "{} has no common/script/flow folder, so it is not a menu set",
        root.display()
    )
}

/// Normalise a target the way the engine sees one: case-insensitive on the
/// final segment is a real source of dead buttons across packs.
fn normalise(s: &str) -> String {
    s.trim()
        .replace('\\', "/")
        .trim_end_matches(".json")
        .to_string()
}

/// Check every link and report the ones that go nowhere.
///
/// `extra_roots` are the ids that exist elsewhere in the layering -- the base
/// game's own flow archive, or another menu-server set. A menu-server folder
/// ships only a subset of screens, so without them almost every link looks
/// dead and the report is worthless. This mirrors how the engine actually
/// resolves a screen: first pack that has it, base last.
pub fn validate(screens: &BTreeMap<String, Screen>) -> Report {
    validate_with(screens, &[])
}

/// As [`validate`], with ids from other layers treated as resolved.
pub fn validate_with(screens: &BTreeMap<String, Screen>, extra_roots: &[PathBuf]) -> Report {
    let mut known: BTreeSet<String> = screens.keys().map(|k| normalise(k)).collect();
    for r in extra_roots {
        if let Ok(other) = load(r) {
            for k in other.keys() {
                known.insert(normalise(k));
            }
        }
    }
    let known_ci: BTreeMap<String, String> = known
        .iter()
        .map(|k| (k.to_lowercase(), k.clone()))
        .collect();
    // Only links inside this set can be judged dead; anything resolving against
    // another layer is left out of the broken list entirely.
    let local: BTreeSet<String> = screens.keys().map(|k| normalise(k)).collect();

    let mut broken = Vec::new();
    let mut links = 0usize;
    let mut referenced: BTreeSet<String> = BTreeSet::new();

    for (id, sc) in screens {
        for (name, ev) in &sc.events {
            let Some(target) = ev.to.as_ref().map(|t| normalise(t)) else {
                continue;
            };
            if target.is_empty() {
                continue;
            }
            links += 1;
            if known.contains(&target) {
                if local.contains(&target) {
                    referenced.insert(target.clone());
                }
                continue;
            }
            // A case difference is a real, findable bug rather than a miss.
            if let Some(exact) = known_ci.get(&target.to_lowercase()) {
                broken.push(Broken {
                    screen: id.clone(),
                    event: name.clone(),
                    target: target.clone(),
                    why: format!(
                        "exists as {exact} but differs in case; the engine will not follow it"
                    ),
                });
                continue;
            }
            broken.push(Broken {
                screen: id.clone(),
                event: name.clone(),
                target,
                why: "no screen with this id in the set; the button does nothing".to_string(),
            });
        }
    }

    // Entry points are the screens the game opens itself. Anything else that
    // nothing points at is dead weight rather than a bug, so it is reported
    // separately and never as an error.
    let entry_prefixes = ["MainMenu", "ModeSelect", "Loading", "Boot"];
    let unreachable: Vec<String> = screens
        .keys()
        .filter(|k| {
            let last = normalise(k).rsplit('/').next().unwrap_or("").to_string();
            // Unreachable is only meaningful within this set: a screen pointed
            // at from the base game is not dead weight.
            !referenced.contains(&normalise(k)) && !entry_prefixes.iter().any(|p| last.contains(*p))
        })
        .cloned()
        .collect();

    let mut by_prefix: BTreeMap<String, usize> = BTreeMap::new();
    for k in screens.keys() {
        let pre = k.split('/').next().unwrap_or("").to_string();
        *by_prefix.entry(pre).or_default() += 1;
    }
    let mut by_prefix: Vec<(String, usize)> = by_prefix.into_iter().collect();
    by_prefix.sort_by(|a, b| b.1.cmp(&a.1));

    Report {
        root: String::new(),
        screens: screens.len(),
        links,
        broken,
        unreachable,
        by_prefix,
    }
}

/// Write one screen back, preserving every field this tool does not model.
pub fn write(screen: &Screen) -> Result<()> {
    let json = serde_json::to_string_pretty(screen).context("serialising the screen")?;
    let tmp = screen.path.with_extension("json.fl27mm-tmp");
    std::fs::write(&tmp, json.as_bytes()).with_context(|| format!("writing {}", tmp.display()))?;
    std::fs::rename(&tmp, &screen.path)
        .with_context(|| format!("saving {}", screen.path.display()))?;
    Ok(())
}

/// Repoint one event, refusing a target that does not exist unless the caller
/// says they are about to create it. Making the link valid is the whole point;
/// letting a typo through turns a fix into a second bug.
pub fn set_target(
    screens: &BTreeMap<String, Screen>,
    screen_id: &str,
    event: &str,
    target: &str,
    allow_missing: bool,
) -> Result<Screen> {
    let mut sc = screens
        .get(screen_id)
        .with_context(|| format!("no screen {screen_id}"))?
        .clone();
    let t = normalise(target);
    if !allow_missing && !screens.contains_key(&t) {
        let known: Vec<&String> = screens
            .keys()
            .filter(|k| k.to_lowercase().contains(&t.to_lowercase()))
            .collect();
        bail!(
            "{t} is not in the set{}",
            if known.is_empty() {
                String::new()
            } else {
                format!(
                    "; closest names: {}",
                    known
                        .iter()
                        .take(5)
                        .map(|s| s.as_str())
                        .collect::<Vec<_>>()
                        .join(", ")
                )
            }
        );
    }
    sc.events.entry(event.to_string()).or_default().to = Some(t);
    Ok(sc)
}

/// Create a new screen by cloning an existing one, so a new layout inherits the
/// shape the engine expects instead of being invented from scratch.
pub fn clone_screen(
    screens: &BTreeMap<String, Screen>,
    from: &str,
    to: &str,
) -> Result<(Screen, PathBuf)> {
    let src = screens
        .get(from)
        .with_context(|| format!("no screen {from} to copy"))?;
    let target = normalise(to);
    if screens.contains_key(&target) {
        bail!("{target} already exists; refusing to overwrite a working screen");
    }
    let flow = find_flow_parent(&src.path)?;
    let dest = flow
        .join(target.replace('/', std::path::MAIN_SEPARATOR_STR))
        .with_extension("json");
    if dest.exists() {
        bail!("{} already exists on disk", dest.display());
    }
    let mut copy = src.clone();
    copy.id = target.clone();
    copy.path = dest.clone();
    Ok((copy, dest))
}

/// The flow directory a screen file sits under, by walking up to `flow`.
fn find_flow_parent(p: &Path) -> Result<PathBuf> {
    let mut cur = p.parent();
    while let Some(d) = cur {
        if d.file_name().map(|n| n == "flow").unwrap_or(false) {
            return Ok(d.to_path_buf());
        }
        cur = d.parent();
    }
    bail!("{} is not under a flow folder", p.display())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn screen(id: &str, targets: &[(&str, &str)]) -> Screen {
        let mut events = BTreeMap::new();
        for (name, to) in targets {
            events.insert(
                (*name).to_string(),
                Event {
                    to: Some((*to).to_string()),
                    ..Default::default()
                },
            );
        }
        Screen {
            events,
            data: Data::default(),
            extra: serde_json::Map::new(),
            id: id.to_string(),
            path: PathBuf::from(format!("flow/{id}.json")),
        }
    }

    fn set(screens: &[Screen]) -> BTreeMap<String, Screen> {
        screens.iter().map(|s| (s.id.clone(), s.clone())).collect()
    }

    #[test]
    fn a_link_to_a_missing_screen_is_caught() {
        let s = set(&[
            screen("BL/BLMainMenu", &[("start", "BL/BLSettings")]),
            screen("BL/BLSettings", &[("return", "BL/BLMainMenu")]),
        ]);
        let r = validate(&s);
        assert!(r.clean(), "a closed loop should be clean: {:?}", r.broken);
        assert_eq!(r.links, 2);

        let s2 = set(&[screen("BL/BLMainMenu", &[("start", "BL/Nowhere")])]);
        let r2 = validate(&s2);
        assert_eq!(r2.broken.len(), 1);
        assert_eq!(r2.broken[0].event, "start");
        assert!(
            r2.broken[0].why.contains("does nothing"),
            "{}",
            r2.broken[0].why
        );
    }

    /// Case differences are the sneaky failure: the file exists, the engine
    /// will not find it, and nothing reports an error.
    #[test]
    fn a_case_difference_is_named_not_misreported() {
        let s = set(&[
            screen("BL/BLMainMenu", &[("start", "BL/blmainmenu")]),
            screen("BL/BLSettings", &[("return", "BL/BLMainMenu")]),
        ]);
        let r = validate(&s);
        assert_eq!(r.broken.len(), 1);
        assert!(r.broken[0].why.contains("case"), "{}", r.broken[0].why);
    }

    #[test]
    fn backslashes_and_extensions_are_normalised_before_matching() {
        let s = set(&[
            screen("BL/BLMainMenu", &[("start", "BL\\BLSettings.json")]),
            screen("BL/BLSettings", &[("return", "BL/BLMainMenu")]),
        ]);
        assert!(validate(&s).clean(), "{:?}", validate(&s).broken);
    }

    #[test]
    fn repointing_refuses_a_typo_and_offers_close_names() {
        let s = set(&[
            screen("BL/BLMainMenu", &[("start", "BL/BLSettings")]),
            screen("BL/BLSettings", &[("return", "BL/BLMainMenu")]),
        ]);
        let err = set_target(&s, "BL/BLMainMenu", "start", "BL/BLSettingz", false).unwrap_err();
        assert!(err.to_string().contains("not in the set"), "{err}");
        let ok = set_target(&s, "BL/BLMainMenu", "start", "BL/BLSettings", false).unwrap();
        assert_eq!(ok.events["start"].to.as_deref(), Some("BL/BLSettings"));
        // Deliberate escape hatch for authoring a screen that does not exist yet.
        let forced = set_target(&s, "BL/BLMainMenu", "start", "BL/BrandNew", true).unwrap();
        assert_eq!(forced.events["start"].to.as_deref(), Some("BL/BrandNew"));
    }

    #[test]
    fn cloning_refuses_to_clobber() {
        let s = set(&[
            screen("BL/BLMainMenu", &[("start", "BL/BLSettings")]),
            screen("BL/BLSettings", &[]),
        ]);
        let err = clone_screen(&s, "BL/BLMainMenu", "BL/BLSettings").unwrap_err();
        assert!(err.to_string().contains("already exists"), "{err}");
    }

    /// Round-tripping must not lose fields this tool does not model: a real
    /// flow file carries keys no one has enumerated.
    #[test]
    fn unknown_fields_survive_a_round_trip() {
        let raw = r#"{"events":{"return":{"to":"BL/BLMainMenu","go":"backward","clear":"all","fadeStart":"1","custom":"keep"}},"data":{"type":"menu","bgId":"BG_X","dialog":""}}"#;
        let mut sc: Screen = serde_json::from_str(raw).unwrap();
        sc.id = "BL/BLGeneralSettingsMain".into();
        let out = serde_json::to_string(&sc).unwrap();
        assert!(out.contains("\"bgId\""), "{out}");
        assert!(
            out.contains("\"custom\":\"keep\""),
            "an unmodelled event field was dropped: {out}"
        );
        assert!(out.contains("BG_X"));
    }

    #[test]
    fn a_root_that_is_not_a_menu_set_is_refused() {
        let dir = std::env::temp_dir().join(format!("fl27mm-menus-{}", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();
        let err = load(&dir).unwrap_err();
        assert!(err.to_string().contains("not a menu set"), "{err}");
        let _ = std::fs::remove_dir_all(&dir);
    }
}

/// Whether a target resolves anywhere in the set or the given layers. Exposed
/// so the UI can check before writing, rather than letting a typo become a
/// dead button that only shows up in game.
pub fn target_known(screens: &BTreeMap<String, Screen>, bases: &[PathBuf], target: &str) -> bool {
    let t = normalise(target);
    if screens.contains_key(&t) {
        return true;
    }
    bases
        .iter()
        .any(|b| load(b).map(|o| o.contains_key(&t)).unwrap_or(false))
}
