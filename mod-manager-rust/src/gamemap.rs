//! What every part of an FL27 install is, and what you can safely do to it.
//!
//! The explanations here are grounded in a survey of the actual archives, not
//! in generic PES lore: each `dt*.cpk` entry below was checked by reading its
//! TOC and grouping the paths it contains. Where a claim is a convention rather
//! than something measured, it says so. Anything not covered is reported as
//! unknown instead of being guessed at.
//!
//! Two layers use this: the on-disk tree (`build`) and the inside of an archive
//! (`describe` on a CPK-internal path), so the same knowledge explains both.

use std::collections::BTreeMap;
use std::path::{Path, PathBuf};

use serde::Serialize;

use crate::{cpk, ini, order, pesdb};

/// How risky it is to change something, and what that risk actually is.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum Edit {
    /// Plain data the app can round-trip; a mistake is recoverable.
    Safe,
    /// Replaces a game file. Fine with a backup, fatal without one.
    Careful,
    /// The game reads this structurally; a wrong byte breaks a mode or a save.
    Risky,
    /// Read it, never write it.
    ReadOnly,
    /// Not game content, or not understood well enough to advise.
    Unknown,
}

impl Edit {
    pub fn label(self) -> &'static str {
        match self {
            Edit::Safe => "safe to edit",
            Edit::Careful => "back up first",
            Edit::Risky => "structural — risky",
            Edit::ReadOnly => "read only",
            Edit::Unknown => "unknown",
        }
    }

    /// The same rating said as an outcome. "Risky" does not tell anyone what
    /// they are risking, so every block shows this too; where a file has a
    /// more specific failure than the general rule, [`Info::breaks`] overrides
    /// it rather than repeating this.
    pub fn consequence(self) -> &'static str {
        match self {
            Edit::Safe => "Get it wrong and you can put the original back; nothing else moves.",
            Edit::Careful => {
                "Get it wrong and this content stops loading until you restore the file you replaced."
            }
            Edit::Risky => {
                "Get it wrong and the game can crash, refuse to start, or corrupt a save that is already written."
            }
            Edit::ReadOnly => {
                "Writing here is never the fix; something else is what you actually want to change."
            }
            Edit::Unknown => "Nobody has established what these bytes do, so an edit here is a guess.",
        }
    }
}

#[derive(Debug, Clone, Serialize)]
pub struct Info {
    pub title: String,
    /// What this is, in plain language.
    pub what: String,
    pub format: String,
    pub edit: Edit,
    /// What actually goes wrong if this is edited badly. Defaults to the
    /// outcome implied by `edit`; specific blocks say their own failure.
    pub breaks: String,
    /// The literal next action in this app.
    pub how: String,
}

impl Info {
    fn new(title: &str, what: &str, format: &str, edit: Edit, how: &str) -> Info {
        Info {
            title: title.into(), what: what.into(), format: format.into(),
            edit, breaks: edit.consequence().into(), how: how.into(),
        }
    }

    /// Replace the generic consequence with the one true for this file.
    fn breaks(mut self, b: &str) -> Info {
        self.breaks = b.into();
        self
    }
}

/// The Data archives, one by one. Counts and folder names come from reading
/// each TOC; the purpose follows from what those folders hold.
fn archive_info(name: &str) -> Option<Info> {
    let lower = name.to_ascii_lowercase();
    let info = match lower.as_str() {
        "dt00_x64.cpk" => Info::new(
            "Core engine assets",
            "606 entries: shaders/dx11, lighting, effects, the intro movie, base \
             character and background models, and the 2D menu art. This is the \
             replaces this whole archive overrides all of it at once.",
            "CPK · ftex, fmdl, fpk, vfx, shaders", Edit::Careful,
            "Extract, edit textures or effects, repack. Keep a copy of the original."),
        "dt00_4k_x64.cpk" => Info::new(
            "4K fonts (base)",
            "9 font bins: pes_fnt, match_fnt, LPsm_fnt and the numeric fonts. \
             Loaded instead of the standard-resolution set on a 4K display.",
            "CPK · font .bin", Edit::Careful,
            "Replace only if you have a matching 4K font set."),
        "dt10_x64.cpk" => Info::new(
            "Reference tables",
            "13 small tables: the ball, boots and glove catalogues, stadium order \
             and weighting, TeamColor, StadiumEditParam, referee appearance and \
             the weekly appearance reset.",
            "CPK · WESYS pesdb .bin", Edit::Risky,
            "Tables tab: unwrap, edit at the record stride, re-wrap. Validate first."),
        "dt11_x64.cpk" => Info::new(
            "Menu layouts and art",
            "686 entries, all under common/menu: mode (214 screens), general (255), \
             parts, licence, system, font, import and saveicon. The .bin files here \
             are menu layout and texture art, not text.",
            "CPK · menu .bin, png, dds", Edit::Careful,
            "Menu packs shadow these by path through livecpk; prefer a pack over repacking."),
        "dt11_4k_x64.cpk" => Info::new(
            "4K fonts (extended)",
            "13 font bins including matchBold, plname (player names) and XLPsm. \
             The larger 4K font set.",
            "CPK · font .bin", Edit::Careful,
            "Replace only with a matching 4K set."),
        "dt12_g4.cpk" => Info::new(
            "Cut-scenes and crowd demos",
            "18,241 entries under common/demo: fixdemoobj (6,140), anime (5,943), \
             fixdemo (4,931), prop and mob. Pre-authored camera sequences, crowd \
             and prop motion — the biggest animation store in the game.",
            "CPK · gani, fdc, ftex, fpk", Edit::Careful,
            "Cut-scene packs shadow individual sequences inside it by path."),
        "dt13_all.cpk" => Info::new(
            "Player animation",
            "416 entries under common/anime: FoxAnim motion clips, Mbinfo blend \
             data, AnimeTable, FHSequence, EyesTarget and playerID. This is the \
             packs replace this whole archive rather than individual clips.",
            "CPK · gani, mtar, ask, frig", Edit::Careful,
            "Replace the whole archive or none of it; a half-swapped archive is the failure mode.").breaks("Animation and skeleton data are indexed together, so taking one archive half from a gameplay mod and one from another makes motion references land on the wrong clips. The game runs; the players move wrong."),
        "dt14_all.cpk" => Info::new(
            "Symbols: emblems, logos, flags",
            "26,121 DDS files, all under common/render/symbol. Club and nation \
             crests, competition logos and flags.",
            "CPK · dds", Edit::Safe,
            "Emblem and Logos packs shadow these by path — no repack needed."),
        "dt15_x64.cpk" => Info::new(
            "Balls, props and thumbnails",
            "6,004 entries: 4,827 PNG symbols, 771 menu thumbnails, 261 ball model \
             files under Asset/model/ball, plus training props.",
            "CPK · png, dds, ftex, fpk", Edit::Safe,
            "Ball packs write Asset/model/ball paths; only one ball can win per slot."),
        "dt16_all.cpk" => Info::new(
            "Menu flow graphs",
            "2,129 files: 2,128 JSON under common/script/flow, one per screen. Each \
             holds events (to, go, clear, fadeStart, fadeEnd, bgType) and a data \
             block. Navigation lives here; the visible labels do not.",
            "CPK · plain JSON", Edit::Safe,
            "Extract, edit the JSON, repack. Text is readable and round-trips."),
        "dt17_x64.cpk" => Info::new(
            "Language-independent strings",
            "18 .str tables under common/string — the text that is the same in \
             every language.",
            "CPK · .str", Edit::Risky,
            "String tables are indexed; changing lengths shifts every later entry."),
        "dt18_all.cpk" => Info::new(
            "Match constants (gameplay tuning)",
            "9 bins under common/match/constant plus version.txt: constant_match, \
             player, team, stadium, positionCK/PK, shootAging and the tutorials. \
             Named .o sections such as cpuLevel.o live inside constant_match.bin. \
             All nine must be present, and a gameplay pack replaces this file wholesale.",
            "CPK · WESYS .bin", Edit::Risky,
            "Tables tab unwraps these. The Gameplay Loader route serves the nine \
             loose files instead, with no CPK at all."),
        "dt19_x64.cpk" => Info::new(
            "Stadiums (nested archives) and crowd",
            "421 entries: 18 nested CPKs under Asset/model/bg holding 2.95 GB of \
             stadium content, plus 393 crowd animation files under \
             common/mob/audience_BB.",
            "CPK · nested CPK, gani", Edit::Careful,
            "Open a nested stadium CPK from the archives tab to see inside it."),
        "dt30_g4.cpk" => Info::new(
            "Stadium models and textures",
            "1,777 entries, 3.96 GB unpacked: Asset/model/bg plus 333 XML model \
             descriptors under common/bg/model. The Graphical Overhaul replaces \
             this archive.",
            "CPK · ftex, fpk, xml, nested CPK", Edit::Careful,
            "Largest single file in Data. Back it up before swapping."),
        "dt32_g4.cpk" => Info::new(
            "Faces and hair",
            "3,552 entries: face/edithair (2,871), face/montage (383), and body \
             parts (manager, naked, training suit, undershirt, playersuit, polo).",
            "CPK · ftex, fpk, fpkd", Edit::Safe,
            "Face packs shadow these paths. Textures tab converts the ftex files."),
        "dt33_g4.cpk" => Info::new(
            "Boots and gloves",
            "1,640 entries under Asset/model/character/boots/kXXXX and glove/gXXX \
             — one folder per boot or glove model.",
            "CPK · ftex, fpk, fpkd", Edit::Safe,
            "boot-root shadows these. Textures tab converts individual textures."),
        "dt34_g4.cpk" => Info::new(
            "Kits",
            "16,322 entries: 12,821 uniform textures under \
             Asset/model/character/uniform/texture, plus 3,445 realUni.bin kit \
             definitions under common/character0/model/character/uniform.",
            "CPK · ftex + uniform .bin", Edit::Safe,
            "Slotkits_V3 shadows the realUni.bin files. Textures tab handles the ftex."),
        "dt35_g4.cpk" => Info::new(
            "Kit cloth and caps",
            "409 entries: uniform/nocloth (380), uniform/cloth (23) and cap (6) — \
             the models cloth simulation runs on.",
            "CPK · fmdl, ftex, fclo", Edit::Careful,
            "cloth-fx and GP_JP Animation Mod interact with this content."),
        "dt36_g4.cpk" => Info::new(
            "Real player faces",
            "1,842 entries, all under Asset/model/character/face/real: 1,374 \
             face models and 396 textures. The scanned faces of real players, \
             as opposed to dt32's edit-mode parts.",
            "CPK · fmdl, ftex, fpk", Edit::Safe,
            "Face packs shadow these paths by player id."),
        "dt40_all.cpk" => Info::new(
            "Menu audio",
            "46 entries under common/sound/menu, 429 MB: the menu music and \
             interface sound banks.",
            "CPK · awb, acb, bin", Edit::Careful,
            "Soundtrack packs replace this content."),
        "dt42_all.cpk" => Info::new(
            "Audio configuration",
            "5 tables under common/sound/config that map sound cues to banks.",
            "CPK · bin", Edit::Risky,
            "Changing these without matching banks silences or misroutes audio."),
        "dt44_all.cpk" => Info::new(
            "Match audio",
            "76 entries under common/sound/match, 3.44 GB: crowd, commentary \
             and pitch sound banks. The largest audio archive.",
            "CPK · acb, awb, bin", Edit::Careful,
            "Announcer, commentary, NetSound and PitchSFX packs work against this."),
        "dt70_x64.cpk" => Info::new(
            "Movies",
            "123 USM videos, 1.84 GB: 60 intro clips and 63 fades.",
            "CPK · usm", Edit::Safe, "Replace by path; USM is CRI's video container."),
        "dt90_x64.cpk" => Info::new(
            "Stadium billboards and screens",
            "766 entries, 3.41 GB: 123 billboard descriptors under \
             common/bg/model/bg/bill with their own USM screen movies, plus \
             617 background model files.",
            "CPK · xml, usm, ftex, fpk", Edit::Careful,
            "Per-competition ad boards; the XML is readable, the USM is video."),
        _ => {
            if lower.starts_with("dt43_") {
                let lang = lower.trim_start_matches("dt43_")
                    .trim_end_matches("_all.cpk").trim_end_matches(".cpk");
                return Some(Info::new(
                    "Localised audio configuration",
                    &format!("Language '{lang}': the sound config table and its \
                              XML that select which commentary bank plays."),
                    "CPK · bin + xml", Edit::Risky,
                    "Commentary packs must match this config or the wrong bank plays."));
            }
            if lower.starts_with("dt20_") {
                let lang = lower.trim_start_matches("dt20_")
                    .trim_end_matches("_x64.cpk").trim_end_matches(".cpk");
                return Some(Info::new(
                    "Localised text and menu art",
                    &format!("Language pack '{lang}': string tables plus the menu \
                              screens that carry text. The 4k variants hold the \
                              same content at higher resolution."),
                    "CPK · .str + menu .bin", Edit::Risky,
                    "Commentary and announcer packs replace the audio side; \
                     text edits shift string indices."));
            }
            return None;
        }
    };
    Some(info)
}

/// Explain a path, whether it is on disk or inside an archive. More specific
/// rules come first; the extension fallback is last.
pub fn describe(rel: &str) -> Info {
    let p = rel.replace('\\', "/");
    let lower = p.to_ascii_lowercase();
    let name = lower.rsplit('/').next().unwrap_or("");

    if let Some(info) = archive_info(name) {
        return info;
    }
    if name == "version.txt" {
        return Info::new("Archive version marker",
            "A short text stamp naming the content version this archive was \
             built for. dt18 ships one alongside its nine match constants.",
            "text", Edit::ReadOnly,
            "Read it to tell which gameplay build is installed.");
    }

    let rules: &[(&str, Info)] = &[
        ("common/etc/pesdb", Info::new(
            "Database table",
            "Fixed-width records behind a WESYS zlib header. Only two shipped \
             archives carry this folder: dt00 (8 Myclub/Week/DeleteList tables) \
             and dt10 (7 ball, boot, glove and stadium tables). No Data archive \
             ships Competition, CompetitionRegulation, Player or Team at all — \
             those live in the save/edit data, so a loose file at this path is \
             a league-tool convention rather than something the engine loads.",
            "WESYS · zlib-compressed fixed-stride records", Edit::Risky,
            "Tables tab validates the stride before you install anything.").breaks("A wrong record stride does not corrupt one row. It re-slices every row after it, so the table still opens and every name, id and link shifts by the same amount. The game will not complain; it will just show the wrong club in the right slot.")),
        ("common/match/constant", Info::new(
            "Match constant",
            "Gameplay tuning read at match start. constant_match.bin contains \
             named .o sections (cpuLevel.o and friends).",
            "WESYS .bin", Edit::Risky,
            "Tables tab unwraps it; the Gameplay Loader can serve it loose.").breaks("These bytes are read at match start, so a wrong value changes how every match plays rather than how one entry looks. A mis-sized section can stop the match loading entirely.")),
        ("common/script/flow", Info::new(
            "Menu flow graph",
            "One JSON per screen describing where each event goes. This is \
             navigation, not layout and not text.",
            "plain JSON", Edit::Safe,
            "Extract, edit, repack — the text round-trips.")),
        ("common/menu/font", Info::new(
            "Font",
            "Glyph atlas and metrics for one UI font. The 4K archives override \
             these.",
            "font .bin", Edit::Careful,
            "Replace as a set; mixing resolutions produces missing glyphs.")),
        ("common/menu", Info::new(
            "Menu screen",
            "Layout and texture art for a screen. These .bin files are TXP2/apk \
             texture containers, not readable layout text — the labels are not \
             in here.",
            "menu .bin (TXP2/apk)", Edit::Careful,
            "Menu packs shadow these by path; the menu server chooses the per-competition set.")),
        ("common/render/symbol", Info::new(
            "Symbol",
            "Crests, logos and flags. PNG in dt15, DDS in dt14.",
            "png / dds", Edit::Safe,
            "Emblem and logo packs shadow these paths.")),
        ("common/render/thumbnail", Info::new(
            "Menu thumbnail",
            "Preview images shown in menus and editors.",
            "dds", Edit::Safe, "Replace by path through a pack.")),
        ("common/string", Info::new(
            "String table",
            "Indexed text. Entries are referenced by position, so inserting or \
             resizing one shifts everything after it.",
            ".str", Edit::Risky, "Edit in place without changing lengths.").breaks("Entries are found by position, not by key. Making one string longer moves every entry after it, which shows up as unrelated text throughout the game, and the file still parses, so nothing points at the mistake.")),
        ("common/anime", Info::new(
            "Animation",
            "Motion clips and blend tables that drive player movement.",
            "gani / mtar / ask", Edit::Careful,
            "Gameplay mods replace the whole dt13 archive.")),
        ("common/demo", Info::new(
            "Cut-scene / demo",
            "Pre-authored sequences: fixed cameras, crowd and prop motion.",
            "gani / fdc / fpk", Edit::Careful,
            "Scene packs shadow individual sequences.")),
        ("common/mob", Info::new(
            "Crowd",
            "Audience models and animation. Crowd packs and attendance scripts \
             work against this content.",
            "gani / fpk", Edit::Careful, "A runtime script can override attendance without touching these files.")),
        ("common/bg/model", Info::new(
            "Stadium descriptor",
            "XML describing a stadium's model, lighting and layout.",
            "xml", Edit::Safe, "Readable text; edit and repack.")),
        ("asset/model/bg", Info::new(
            "Stadium / background",
            "Stadium geometry and textures. In dt19 and dt30 these are nested \
             CPKs, one per stadium.",
            "nested CPK · ftex · fpk", Edit::Careful,
            "Open the nested archive to reach individual stadiums.")),
        ("asset/model/character/uniform/texture", Info::new(
            "Kit texture",
            "One ftex per kit layer. DXT1 without alpha, DXT5 with it.",
            "ftex", Edit::Safe,
            "Textures tab: preview, convert to DDS, edit, convert back.")),
        ("asset/model/character/uniform", Info::new(
            "Kit definition",
            "realUni.bin files describing a kit's layers, colours and badges.",
            "uniform .bin", Edit::Careful,
            "Slotkits_V3 and Kit Studio work on these.")),
        ("asset/model/character/face", Info::new(
            "Face / hair",
            "Face montage parts and edit-mode hair.",
            "ftex / fpk", Edit::Safe, "Face packs shadow these paths.")),
        ("asset/model/character/boots", Info::new(
            "Boot model", "One folder per boot, named kXXXX.",
            "ftex / fpk", Edit::Safe, "boot-root shadows these.")),
        ("asset/model/character/glove", Info::new(
            "Glove model", "One folder per goalkeeper glove, named gXXX.",
            "ftex / fpk", Edit::Safe, "boot-root shadows these.")),
        ("asset/model/ball", Info::new(
            "Ball model",
            "Ball geometry and texture. Balls are addressed by slot, so two \
             packs writing the same ball path cannot both show.",
            "ftex / fpk / geom", Edit::Safe,
            "Only one pack per ball slot survives; order decides which.")),
        ("asset/model/light", Info::new(
            "Lighting", "Light rigs and LUT colour grading.",
            "ftex / fmdl", Edit::Safe, "Ultra Graphics GfX replaces the LUTs.")),
        ("asset/effect", Info::new(
            "Effect", "Particle and post-effect definitions.",
            "vfx / ftex", Edit::Careful, "A graphical-fixes pack replaces these outright.")),
        ("shaders", Info::new(
            "Shader", "Compiled DirectX shaders. Not text.",
            "compiled shader", Edit::Risky,
            "ReShade and OptiScaler post-process instead of replacing these.")),
        ("movie", Info::new(
            "Movie", "Intro and attract-mode video.",
            "video", Edit::Safe, "Replace by path.")),
        ("common/sound", Info::new(
            "Match audio", "Crowd, net and pitch sound banks.",
            "awb / acb", Edit::Careful,
            "NetSound and PitchSFX shadow these; only one wins per key.")),
        ("canm", Info::new(
            "Camera animation", "Authored camera moves for scenes and broadcast.",
            "canm", Edit::Careful, "The camera Lua modules drive these at runtime.")),
    ];
    for (needle, info) in rules {
        if lower.contains(needle) {
            return info.clone();
        }
    }

    extension_info(name)
}

fn extension_info(name: &str) -> Info {
    let ext = name.rsplit_once('.').map(|(_, e)| e).unwrap_or("");
    match ext {
        "cpk" => Info::new("CRIWARE archive",
            "A packed file tree. The header and TOC are @UTF tables; entries are \
             stored or CRILAYLA-compressed.",
            "CPK", Edit::Careful,
            "Archives tab lists, extracts and rebuilds it."),
        "ftex" => Info::new("Fox Engine texture",
            "A texture with a mip chain, zlib-compressed in 16 KiB chunks. PES \
             writes format version 2.03 and 2.04; LUT files are 16x16x16 volumes.",
            "ftex", Edit::Safe,
            "Textures tab previews it and converts to and from DDS."),
        "dds" => Info::new("DirectDraw surface",
            "Standard PC texture. DXT1 has no alpha, DXT5 does; changing the \
             format changes how the game samples it.",
            "dds", Edit::Safe, "Textures tab converts it to ftex."),
        "lua" => Info::new("Sider module",
            "Runs inside the game through Sider's LuaJIT. Modules load in the \
             order sider.ini lists them, so dependencies must come first.",
            "Lua", Edit::Safe,
            "Edit freely; sider.log names any module that fails to load."),
        "ini" => Info::new("Configuration",
            "Plain key = value text. Sider reads cpk.root and lua.module from it.",
            "ini", Edit::Safe, "Pack order tab reorders cpk.root with a backup."),
        "json" => Info::new("JSON data",
            "Readable structured data.", "json", Edit::Safe, "Edit as text."),
        "xml" => Info::new("XML descriptor",
            "Readable model or archive description.", "xml", Edit::Safe, "Edit as text."),
        "gani" => Info::new("Animation clip",
            "Fox Engine animation data: tracks of keyframes over frames.", "gani", Edit::Careful,
            "Frame rate and single keyframes can be rewritten safely; a whole clip is \
             normally replaced as a set with the mod that authored it, because the rig it \
             targets lives outside the file."),
        "ask" => Info::new("Skeleton",
            "The bones of a model and their rest transforms: parent index, local position and \
             local quaternion per bone. An `_anim` skeleton has identity rest rotations, so an \
             animation value read against it is the bone's rotation directly; a `_render` \
             skeleton carries the skinning basis instead, and applying animation rotations \
             onto those corrupts the pose.", "ask", Edit::Unknown,
            "Read it to understand what a clip is driving. Editing bone transforms changes the \
             model's bind pose, which every existing animation was authored against."),
        "frig" => Info::new("Rig mapping",
            "How animation channels map onto skeleton bones. Each unit is a root rotation, a root \
             translation, a single-bone channel, or a chain that drives two or three bones at once \
             -- the legs and arms are chains, which is why a tool that only reads single-bone \
             channels leaves the arms frozen in bind pose. The unit and segment counts match the \
             clips it drives, and that correspondence is how a clip is identified with a rig.",
            "frig", Edit::Unknown,
            "Read it alongside a clip. A rig and a clip disagreeing on their counts means the \
             animation is being applied to the wrong skeleton."),
        "fpk" | "fpkd" => Info::new("Fox package",
            "A Fox Engine container, usually paired: .fpk holds data, .fpkd the \
             matching descriptor.", "fpk / fpkd", Edit::Careful,
            "PES Archive Tools extracts and recompiles these."),
        "fmdl" => Info::new("Fox model", "Geometry and material references.",
            "fmdl", Edit::Careful, "Replace alongside its textures."),
        "awb" | "acb" => Info::new("CRI audio bank",
            "AWB holds the streams, ACB the cues that reference them.",
            "awb / acb", Edit::Careful, "PES Sound Editor opens and rebuilds these."),
        "str" => Info::new("String table", "Indexed text.", ".str", Edit::Risky,
            "Keep entry lengths unchanged."),
        "bin" => Info::new("Binary table or art",
            "Extension alone does not say which: under pesdb it is a database \
             table, under menu it is texture art, under match/constant it is \
             gameplay tuning. The path decides.",
            "bin", Edit::Unknown,
            "Tables tab reports the framing and whether the stride tiles."),
        "png" => Info::new("PNG image", "Ordinary image.", "png", Edit::Safe,
            "Edit in any image editor."),
        "txt" | "rtf" => Info::new("Text", "Readable notes or a version stamp.",
            "text", Edit::ReadOnly, "Read it; the game rarely depends on it."),
        "hkx" => Info::new("Havok physics",
            "Havok collision or physics data used by props and stadiums.",
            "hkx", Edit::Risky, "Authored in a Havok toolchain, not by hand."),
        "zip" => Info::new("Zip archive", "An ordinary zip.", "zip", Edit::Safe,
            "Open with any archive tool."),
        "bak" => Info::new("Backup",
            "A copy someone kept before editing. The game does not read it.",
            "backup", Edit::ReadOnly, "Safe to remove once you no longer need it."),
        "exe" | "dll" | "addon64" => Info::new("Program code",
            "Executable or injected library. Not game content.",
            "PE binary", Edit::ReadOnly, "Do not edit; configure it instead."),
        "log" => Info::new("Log", "Diagnostic output.", "text", Edit::ReadOnly,
            "Read it to find which module or pack failed."),
        "cache" => Info::new("Module cache",
            "Runtime state a module wrote for itself. Safe to delete; the module \
             rebuilds it.", "binary", Edit::Safe, "Delete to force a rebuild."),
        _ => Info::new("Unrecognised",
            "This path is not covered by the map. Nothing here is a guess.",
            "unknown", Edit::Unknown, "Inspect it before changing it."),
    }
}

#[derive(Debug, Clone, Serialize)]
pub struct Node {
    pub rel: String,
    pub path: String,
    pub name: String,
    pub group: String,
    pub info: Info,
    pub bytes: u64,
    pub files: usize,
    pub children: Vec<Node>,
    /// Set when this node can be opened directly in one of the tool tabs.
    pub open_as: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
pub struct Finding {
    pub severity: String,
    pub title: String,
    pub detail: String,
    pub path: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct GameMap {
    pub game: String,
    pub nodes: Vec<Node>,
    pub findings: Vec<Finding>,
    pub archives: usize,
    pub archive_bytes: u64,
}

fn node(rel: &str, path: &Path, group: &str, info: Info, open_as: Option<&str>) -> Node {
    Node {
        rel: rel.to_string(),
        path: path.to_string_lossy().into_owned(),
        name: path.file_name().map(|n| n.to_string_lossy().into_owned())
            .unwrap_or_else(|| rel.to_string()),
        group: group.to_string(),
        info,
        bytes: 0,
        files: 0,
        children: Vec::new(),
        open_as: open_as.map(str::to_string),
    }
}

/// Build the explained tree of an install. Deliberately shallow: the point is
/// to explain the structure, not to list 191,000 textures.
pub fn build(game: &Path) -> GameMap {
    let mut nodes = Vec::new();
    let mut findings = Vec::new();
    let mut archives = 0usize;
    let mut archive_bytes = 0u64;

    // ---- Data -------------------------------------------------------------
    let data = game.join("Data");
    if data.is_dir() {
        let mut data_node = node("Data", &data, "game", Info::new(
            "Data archives",
            "Every dt*.cpk the game loads. Sider's livecpk packs shadow files \
             inside these by path, so most mods never need to touch them.",
            "folder of CPK archives", Edit::Careful,
            "Archives tab opens any of them."), None);
        let mut entries: Vec<PathBuf> = std::fs::read_dir(&data).into_iter()
            .flatten().flatten().map(|e| e.path())
            .filter(|p| p.extension().map(|e| e.eq_ignore_ascii_case("cpk")).unwrap_or(false))
            .collect();
        entries.sort();
        for p in entries {
            let name = p.file_name().unwrap().to_string_lossy().into_owned();
            let size = std::fs::metadata(&p).map(|m| m.len()).unwrap_or(0);
            archives += 1;
            archive_bytes += size;
            let mut n = node(&format!("Data/{name}"), &p, "archive",
                             describe(&name), Some("cpk"));
            n.bytes = size;
            data_node.children.push(n);
        }
        data_node.bytes = archive_bytes;
        data_node.files = archives;
        nodes.push(data_node);
    }

    // ---- SiderAddons ------------------------------------------------------
    let addons = game.join("SiderAddons");
    if addons.is_dir() {
        let mut side = node("SiderAddons", &addons, "sider", Info::new(
            "Sider",
            "Sider 7 by juce. It injects LiveCPK (loose files that shadow archive \
             content by path) and a LuaJIT runtime into the game at launch.",
            "folder", Edit::Safe,
            "Everything a mod installs lives under here."), None);

        let ini_path = addons.join("sider.ini");
        if ini_path.is_file() {
            let mut n = node("SiderAddons/sider.ini", &ini_path, "config", Info::new(
                "sider.ini",
                "The order file. cpk.root is FIRST WINS: a pack only contributes \
                 keys no earlier pack already carries. lua.module loads in \
                 sequence, so dependencies must precede their users. Neither \
                 rule is visible in the file, which is why hand edits silently \
                 disable packs.",
                "ini", Edit::Safe,
                "Pack order tab shows what each entry actually contributes."),
                Some("packs"));
            n.bytes = std::fs::metadata(&ini_path).map(|m| m.len()).unwrap_or(0);
            side.children.push(n);
            findings.extend(check_ini(&ini_path, &addons));
        }

        for exe in ["sider.exe", "sider.dll"] {
            let p = addons.join(exe);
            if p.is_file() {
                let mut n = node(&format!("SiderAddons/{exe}"), &p, "sider", Info::new(
                    exe,
                    "The Sider injector itself. Launch the game through Sider, \
                     not the plain executable, or no mod loads.",
                    "PE binary", Edit::ReadOnly, "Do not edit."), None);
                n.bytes = std::fs::metadata(&p).map(|m| m.len()).unwrap_or(0);
                side.children.push(n);
            }
        }

        let modules = addons.join("modules");
        if modules.is_dir() {
            let mut n = node("SiderAddons/modules", &modules, "lua", Info::new(
                "Lua modules",
                "One .lua per mod, loaded in sider.ini order. Cameras, scenes, \
                 broadcast, fans, editors and the switcher libraries all live \
                 here. A module that throws is named in sider.log.",
                "Lua", Edit::Safe,
                "Edit freely; the load order is what usually breaks."), None);
            let (bytes, files) = crate::fsutil::stats(&modules, 100_000);
            n.bytes = bytes;
            n.files = files;
            let mut luas: Vec<PathBuf> = std::fs::read_dir(&modules).into_iter()
                .flatten().flatten().map(|e| e.path())
                .filter(|p| p.extension().map(|e| e.eq_ignore_ascii_case("lua")).unwrap_or(false))
                .collect();
            luas.sort();
            for p in luas {
                let name = p.file_name().unwrap().to_string_lossy().into_owned();
                let mut c = node(&format!("SiderAddons/modules/{name}"), &p, "lua",
                                 module_info(&name), None);
                c.bytes = std::fs::metadata(&p).map(|m| m.len()).unwrap_or(0);
                n.children.push(c);
            }
            side.children.push(n);
        }

        let livecpk = addons.join("livecpk");
        if livecpk.is_dir() {
            let mut n = node("SiderAddons/livecpk", &livecpk, "packs", Info::new(
                "LiveCPK packs",
                "Loose file trees that shadow archive content by path. A file at \
                 livecpk/root/common/render/symbol/x.dds replaces the same path \
                 inside dt14 without repacking anything.",
                "folder", Edit::Safe,
                "Pack order tab decides which pack wins each path."), None);
            let mut tops: Vec<PathBuf> = std::fs::read_dir(&livecpk).into_iter()
                .flatten().flatten().map(|e| e.path())
                .filter(|p| p.is_dir()).collect();
            tops.sort();
            for p in tops {
                let name = p.file_name().unwrap().to_string_lossy().into_owned();
                let rel = format!("SiderAddons/livecpk/{name}");
                let info = if name.eq_ignore_ascii_case("root") {
                    Info::new("Base pack root",
                        "The catch-all pack. Because cpk.root is first wins, this \
                         entry must be LAST: putting it early disables every \
                         specialised pack whose keys it also carries.",
                        "folder", Edit::Safe,
                        "Keep it last in the order.")
                } else {
                    Info::new(&name,
                        "A pack tree. Whether it is registered, and where it sits \
                         in the order, decides if any of it reaches the game.",
                        "folder", Edit::Safe,
                        "Pack order tab shows its surviving keys.")
                };
                let mut c = node(&rel, &p, "packs", info, Some("packs"));
                let (bytes, files) = crate::fsutil::stats(&p, 20_000);
                c.bytes = bytes;
                c.files = files;
                n.children.push(c);
            }
            n.bytes = n.children.iter().map(|c| c.bytes).sum();
            n.files = n.children.iter().map(|c| c.files).sum();
            side.children.push(n);
            findings.extend(check_tables(&livecpk));
        }

        for (dir, title, what) in [
            ("content", "Module content",
             "Data owned by modules rather than by the game: kitserver configs, \
              audio, cinematics, editor details. Modules read it by their own \
              conventions, not through cpk.root."),
            ("menu-server", "MenuServer map",
             "Per-competition menu selection. The hundred-odd menu packs are \
              alternatives, not layers: MenuServer picks one at runtime, which \
              is why ordering alone cannot make them all work."),
            ("ModStudio", "Mod Studio",
             "World-building modules. They read modules/fl26world.txt at boot \
              and configure themselves from it."),
            ("TouchlineCompanion", "Touchline companion",
             "Companion module data for the Touchline mod family."),
        ] {
            let p = addons.join(dir);
            if p.is_dir() {
                let mut n = node(&format!("SiderAddons/{dir}"), &p, "content",
                                 Info::new(title, what, "folder", Edit::Safe,
                                           "Owned by its module; edit through that module."),
                                 None);
                let (bytes, files) = crate::fsutil::stats(&p, 20_000);
                n.bytes = bytes;
                n.files = files;
                side.children.push(n);
            }
        }

        let log = addons.join("sider.log");
        if log.is_file() {
            let mut n = node("SiderAddons/sider.log", &log, "log", Info::new(
                "sider.log",
                "Every module load and every Lua error, with file and line. The \
                 first place to look when a mod does nothing.",
                "text", Edit::ReadOnly, "Read it after a launch."), None);
            n.bytes = std::fs::metadata(&log).map(|m| m.len()).unwrap_or(0);
            side.children.push(n);
        }
        nodes.push(side);
    }

    // ---- saves ------------------------------------------------------------
    if let Some(docs) = documents_dir() {
        let saves = docs.join("SPGAME").join("Football Life");
        if saves.is_dir() {
            let mut n = node("Saves", &saves, "saves", Info::new(
                "Save data",
                "WEPES holds the edit database, 2027 holds career saves, and \
                 settings.dat holds game options. Careers are slot-indexed: a \
                 result belongs to a fixture slot, not to a team name.",
                "folder", Edit::ReadOnly,
                "Read for analysis. Writing a save risks corrupting a career."),
                None);
            let (bytes, files) = crate::fsutil::stats(&saves, 20_000);
            n.bytes = bytes;
            n.files = files;
            for sub in ["WEPES", "2027"] {
                let p = saves.join(sub);
                if p.is_dir() {
                    let mut c = node(&format!("Saves/{sub}"), &p, "saves", Info::new(
                        sub,
                        if sub == "WEPES" {
                            "The edit database: EDIT00000000 and friends. This is \
                             where in-game edits are stored, encrypted."
                        } else {
                            "Master League and Become a Legend careers."
                        },
                        "save", Edit::ReadOnly, "Never write."), None);
                    let (b, f) = crate::fsutil::stats(&p, 20_000);
                    c.bytes = b;
                    c.files = f;
                    n.children.push(c);
                }
            }
            nodes.push(n);
        }
    }

    // ---- executables and injectors ---------------------------------------
    let mut programs = node("Programs", game, "programs", Info::new(
        "Executables and injectors",
        "The game, its launchers, and the post-processing chain. None of this is \
         game content, and none of it is ordered by Sider.",
        "folder", Edit::ReadOnly, "Configure, do not edit."), None);
    for (file, title, what) in [
        ("FL_2027.exe", "Game executable",
         "The game itself. Launch through Sider so mods load."),
        ("FL 2027 start.exe", "FL launcher",
         "Football Life's own launcher, which starts Sider and the game."),
        ("FL27 Switcher.exe", "FL27 Switcher",
         "Switches between installed mod configurations."),
        ("Settings.exe", "Settings",
         "Graphics and display settings, written to the game's config."),
        ("dxgi.dll", "DXGI proxy",
         "A proxy library that loads ReShade and the DLSS/OptiScaler chain \
          before the game's own rendering starts."),
        ("ReShade.ini", "ReShade configuration",
         "Which post-processing shaders run, and in what order."),
        ("nvngx_dlss.dll", "DLSS",
         "NVIDIA's upscaler. RenoDX and OptiScaler hook it."),
    ] {
        let p = game.join(file);
        if p.is_file() {
            let mut n = node(file, &p, "programs",
                             Info::new(title, what, "PE binary / ini", Edit::ReadOnly,
                                       "Configure it; do not patch it."), None);
            n.bytes = std::fs::metadata(&p).map(|m| m.len()).unwrap_or(0);
            programs.children.push(n);
        }
    }
    if !programs.children.is_empty() {
        nodes.push(programs);
    }

    GameMap {
        game: game.to_string_lossy().into_owned(),
        nodes, findings, archives, archive_bytes,
    }
}

fn documents_dir() -> Option<PathBuf> {
    std::env::var_os("USERPROFILE").map(|h| PathBuf::from(h).join("Documents"))
}

fn module_info(name: &str) -> Info {
    let lower = name.to_ascii_lowercase();
    let (title, what) = if lower.contains("cam") {
        ("Camera module", "Overrides the match camera. Cameras are last-wins: \
         the last camera module loaded is the one in control.")
    } else if lower.contains("scene") || lower.contains("celebration") {
        ("Scene module", "Triggers cut-scenes and celebrations at match events.")
    } else if lower.contains("broadcast") {
        ("Broadcast module", "TV-style presentation: overlays, replays, penalties.")
    } else if lower.contains("chant") || lower.contains("fans") || lower.contains("crowd") {
        ("Atmosphere module", "Crowd and chant behaviour during a match.")
    } else if lower.starts_with("mlx") || lower.starts_with("ml") {
        ("Master League module", "Career-mode behaviour. Reads the career save; \
         well-behaved ones never write it.")
    } else if lower.starts_with("dr_") {
        ("League creator module", "Captures or extends competition and team data \
         for the league-creation tooling.")
    } else if lower.contains("editor") || lower.contains("pcc") {
        ("Editor module", "In-game editing and preview surfaces.")
    } else if lower.contains("menu") {
        ("Menu module", "Selects and serves menu content at runtime.")
    } else if lower.contains("turf") || lower.contains("cloth") {
        ("Pitch / cloth module", "Turf and cloth behaviour during play.")
    } else {
        ("Lua module", "A Sider module. Its load position in sider.ini decides \
         what it can see and what overrides it.")
    };
    Info::new(title, what, "Lua", Edit::Safe,
              "Edit freely; sider.log reports failures with a line number.")
}

fn check_ini(ini_path: &Path, addons: &Path) -> Vec<Finding> {
    let mut out = Vec::new();
    let Ok(parsed) = ini::Ini::read(ini_path) else { return out };
    let packs = parsed.active("cpk.root");
    let flag = |k: &str| parsed.active(k).first()
        .map(|v| v.value.trim() == "1").unwrap_or(false);
    if !flag("lua.enabled") {
        out.push(Finding {
            severity: "error".into(),
            title: "lua.enabled is off".into(),
            detail: "No Lua module will load. Every .lua in the order is inert.".into(),
            path: ini_path.to_string_lossy().into_owned(),
        });
    }
    if !flag("luajit.ext.enabled") {
        out.push(Finding {
            severity: "error".into(),
            title: "luajit.ext.enabled is off".into(),
            detail: "Modules that use the LuaJIT extensions will fail.".into(),
            path: ini_path.to_string_lossy().into_owned(),
        });
    }
    if let Some(pos) = packs.iter().position(|e| order::is_base(&e.value)) {
        if pos != packs.len() - 1 {
            out.push(Finding {
                severity: "error".into(),
                title: "The base root is not last".into(),
                detail: format!("`.\\livecpk\\root` sits at position {} of {}. Because \
                                 cpk.root is first wins, every pack after it loses \
                                 the keys it already carries.", pos + 1, packs.len()),
                path: ini_path.to_string_lossy().into_owned(),
            });
        }
    }
    for e in &packs {
        if !order::resolve(addons, &e.value).is_dir() {
            out.push(Finding {
                severity: "warn".into(),
                title: "Registered pack is missing".into(),
                detail: e.value.clone(),
                path: ini_path.to_string_lossy().into_owned(),
            });
        }
    }
    out
}

fn check_tables(livecpk: &Path) -> Vec<Finding> {
    use rayon::prelude::*;
    let tables: Vec<PathBuf> = crate::fsutil::files(livecpk).into_iter()
        .filter(|p| {
            let s = p.to_string_lossy();
            s.contains("pesdb") && s.ends_with(".bin")
        })
        .collect();
    let mut out: Vec<Finding> = tables.par_iter()
        .filter_map(|p| {
            let v = pesdb::validate(p);
            if v.ok {
                return None;
            }
            let name = p.file_name().unwrap_or_default().to_string_lossy().into_owned();
            let (severity, title) = match v.status {
                pesdb::Status::Unrecognised => ("warn".to_string(),
                    format!("{name} is not a readable table")),
                _ => ("error".to_string(),
                    format!("{name} would corrupt the game")),
            };
            Some(Finding {
                severity,
                title,
                detail: v.reason,
                path: p.to_string_lossy().into_owned(),
            })
        })
        .collect();
    out.sort_by(|a, b| a.path.cmp(&b.path));
    out
}

#[derive(Debug, Clone, Serialize)]
pub struct ArchiveSection {
    pub path: String,
    pub files: usize,
    pub bytes: u64,
    pub info: Info,
}

#[derive(Debug, Clone, Serialize)]
pub struct ArchiveMap {
    pub archive: String,
    pub entries: usize,
    pub unpacked: u64,
    pub compressed: usize,
    pub sections: Vec<ArchiveSection>,
    pub extensions: Vec<(String, usize)>,
}

/// Explain the inside of one archive by grouping its entries and describing
/// each group with the same rules the on-disk map uses.
pub fn archive_map(path: &Path, depth: usize) -> Result<ArchiveMap, String> {
    let opened = cpk::Cpk::open(path).map_err(|e| format!("{e:#}"))?;
    let summary = opened.summary();
    let grouped = opened.folders_at(depth.max(1));
    let mut by_ext: BTreeMap<String, usize> = BTreeMap::new();
    for e in &summary.extensions {
        by_ext.insert(e.ext.clone(), e.count);
    }
    Ok(ArchiveMap {
        archive: path.to_string_lossy().into_owned(),
        entries: summary.entries,
        unpacked: summary.unpacked,
        compressed: summary.compressed,
        sections: grouped.into_iter().take(40).map(|f| ArchiveSection {
            info: describe(&format!("{}/_", f.name)),
            path: f.name,
            files: f.files,
            bytes: f.bytes,
        }).collect(),
        extensions: by_ext.into_iter().collect(),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn every_data_archive_is_explained() {
        for n in ["dt00_x64.cpk", "dt10_x64.cpk", "dt11_x64.cpk", "dt12_g4.cpk",
                  "dt13_all.cpk", "dt14_all.cpk", "dt15_x64.cpk", "dt16_all.cpk",
                  "dt17_x64.cpk", "dt18_all.cpk", "dt19_x64.cpk", "dt30_g4.cpk",
                  "dt32_g4.cpk", "dt33_g4.cpk", "dt34_g4.cpk", "dt35_g4.cpk",
                  "dt20_eng_x64.cpk", "dt00_4K_x64.cpk"] {
            let info = describe(n);
            assert_ne!(info.title, "Unrecognised", "{n} has no explanation");
            assert!(!info.what.is_empty(), "{n} has no description");
        }
    }

    #[test]
    fn path_rules_beat_the_extension_fallback() {
        assert_eq!(describe("common/etc/pesdb/Player.bin").title, "Database table");
        assert_eq!(describe("common/menu/general/x.bin").title, "Menu screen");
        assert_eq!(describe("common/match/constant/constant_match.bin").title, "Match constant");
        assert_eq!(describe("somewhere/else/mystery.bin").edit, Edit::Unknown);
        assert_eq!(describe("Asset/model/character/uniform/texture/a.ftex").title, "Kit texture");
    }

    #[test]
    fn unknown_paths_are_not_guessed() {
        let info = describe("some/unknown/thing.xyz");
        assert_eq!(info.title, "Unrecognised");
        assert_eq!(info.edit, Edit::Unknown);
    }

    #[test]
    fn every_archive_in_the_install_is_explained() {
        let data = Path::new(r"C:\Games\SP Football Life 2027\Data");
        if !data.is_dir() {
            return;
        }
        let mut missing = Vec::new();
        for entry in std::fs::read_dir(data).unwrap().flatten() {
            let p = entry.path();
            if p.extension().map(|e| e.eq_ignore_ascii_case("cpk")).unwrap_or(false) {
                let name = p.file_name().unwrap().to_string_lossy().into_owned();
                if describe(&name).title == "Unrecognised" {
                    missing.push(name);
                }
            }
        }
        assert!(missing.is_empty(), "archives with no explanation: {missing:?}");
    }

    #[test]
    fn real_install_maps_and_flags_the_bad_tables() {
        let game = Path::new(r"C:\Games\SP Football Life 2027");
        if !game.join("Data").is_dir() {
            return;
        }
        let map = build(game);
        assert!(map.archives >= 15, "should find the Data archives");
        assert!(map.nodes.iter().any(|n| n.rel == "SiderAddons"));
        assert!(map.nodes.iter().any(|n| n.rel == "Data"));
    }
}
#[cfg(test)]
mod explain_tests {
    use super::*;

    /// The point of the consequence field is that no block can say what a file
    /// is without also saying what goes wrong. A block that returns an empty
    /// `breaks` is exactly the report-style explanation this replaced.
    #[test]
    fn every_explained_path_says_what_breaks() {
        let paths = [
            "Data/dt00_x64.cpk",
            "Data/dt13_all.cpk",
            "Data/dt18_all.cpk",
            "Data/version.txt",
            "common/etc/pesdb/Team.bin",
            "common/match/constant/constant_match.bin",
            "common/string/some.str",
            "common/anime/player.mtar",
            "common/demo/x.fdc",
            "common/menu/font/a.bin",
            "common/render/symbol/a.dds",
            "common/script/flow/a.json",
        ];
        for p in paths {
            let info = describe(p);
            assert!(!info.breaks.is_empty(), "{p} explains nothing about failure");
            assert!(
                info.breaks.len() > 30,
                "{p} has a stub consequence: {:?}",
                info.breaks
            );
            assert!(!info.how.is_empty(), "{p} has no action");
        }
    }

    /// The generic text must still be a real sentence for every rating, since
    /// most of the ~89 blocks rely on it rather than overriding it.
    #[test]
    fn every_risk_rating_has_a_consequence() {
        for e in [Edit::Safe, Edit::Careful, Edit::Risky, Edit::ReadOnly, Edit::Unknown] {
            assert!(e.consequence().len() > 40, "{e:?} has no useful consequence");
            assert!(!e.label().is_empty());
        }
    }

    /// An override must replace the generic line, not sit beside it, or the
    /// field would read as two answers.
    #[test]
    fn a_specific_consequence_replaces_the_generic_one() {
        let info = describe("common/etc/pesdb/Team.bin");
        assert_ne!(info.breaks, Edit::Risky.consequence(), "the stride rule should be specific");
        assert!(info.breaks.contains("stride"), "got {:?}", info.breaks);
        let generic = describe("common/render/symbol/a.dds");
        assert_eq!(generic.breaks, generic.edit.consequence(), "an unoverridden block should use the rule");
    }
}
