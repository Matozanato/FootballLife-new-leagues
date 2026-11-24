# Changelog

The FL27 Mod Manager inspects and edits a Football Life 27 install: pack order,
conflicts, game tables, containers, textures, 3D models, animations and menu
navigation. Everything it claims, it can show you.

## 1.4.0

### Kit Studio and appearance controls

- Added kit-atlas scanning, 3D preview, PNG template export, and PNG replacement
  with format, dimensions and mip chain preserved and a source backup created.
- Added a kit-pack scaffold for Sider uniform textures.
- Added saved text-size, accent-theme and contrast preferences, plus searchable
  tool navigation and a compiled-menu inspection shortcut from Menu Maker.
- Bounded asset browsing by filtering families before texture decoding and
  stopping scans at the result cap.

## 1.3.2

### Skeletons and rigs are decoded

An animation clip stores tracks numbered by unit and segment. Until now nothing
said what those numbers mean, so a clip could be read but not understood.

- **`.ask` skeletons are decoded**: every bone with its parent, local position
  and local quaternion, plus the rest of the hierarchy. The decoder reports
  whether a skeleton is an *identity basis* (the space animation tracks are
  authored in) or a *render basis* (the skinning basis), because applying
  animation rotations onto a render basis corrupts the pose — and it decides
  that from the data, not from the filename.
- **`.frig` rigs are decoded**: each unit is the root, an orientation or
  transform that names one bone directly, or a two- or three-bone chain that
  drives several through a solver. The unit types, their record sizes and the
  `version == 102` assertion come from the engine's own published definition.
- **Which bones an animation can actually move is now visible.** The body rig
  resolves its ten direct units to exactly `sk_root_hip, dsk_hip, sk_foot_l,
  sk_foot_r, sk_belly, sk_chest, sk_neck, sk_head, sk_hand_l, sk_hand_r`, and
  the thighs, shins, shoulders, upper arms and forearms appear only inside
  chain units. That is the explanation for a long-standing symptom: anything
  that maps channels straight to bones animates the trunk, feet and hands and
  leaves the arms frozen in bind pose, because those bones have no direct
  channel to read.
- **A clip and a rig can be compared directly.** Their unit and segment counts
  must agree; `rig <clip> --with <rig>` says so, and a mismatch means the
  animation is aimed at the wrong skeleton.
- **Both are in the interface** under the Assets tab, and both appear in the
  format survey as decoded rather than as gaps.

### Corrected along the way

- **A bone index read from the wrong offset.** The first version of this work
  took the value at record offset +8 as the bone a unit drives. It is not: the
  published record layout puts `TrackCount` and `BoneCount` at +4 and
  `ParentBoneIndex`/`ParentUnitIndex` at +8, and the bone index (`SkelIndex`)
  lives at +16. Reading +8 gave plausible answers for the trunk bones and wrong
  ones for the limbs — hands resolved as forearms — which is worse than an
  obvious failure. The corrected offset reproduces the independently documented
  set of direct bones exactly, and a test now pins that list so a future
  regression cannot pass by looking reasonable.
- **`65535` was never a sentinel for "no bone".** Under the correct layout it is
  `-1`, the parent-unit index of the root: "no parent". The earlier reading
  invented a meaning for a value that already had one.
- **A signature that was not one.** The shipped body skeleton opens every bone
  record with the bytes `cd cd cd cd`, which reads like a record marker. That is
  uninitialised memory that survived into one file: the pattern occurs in no
  other skeleton in the install. A decoder requiring it would accept one file
  and reject forty. The layout is checked by arithmetic instead, and a test
  asserts both kinds parse through the same code.
- **The rig's group-label table is not decoded, and is not guessed.** It holds a
  count, a list of offsets and records beginning with a 32-bit hash, and the
  offset base is not established. The channel-to-bone mapping does not need it.
- **`animation` was still listed as an undecoded format** in the survey after
  1.3.1 decoded and made editable every keyframe in it.
- **182 Tests passed**, no warnings or errors.

## 1.3.1

### Animations are editable

- **Keyframes are decoded.** A clip's track data is walked unit by unit and
  segment by segment: quaternion, float and vector channels, their component
  widths, and every keyframe inside them. The quaternion forms store three
  magnitudes plus three sign bits with no byte padding, so they are read from
  the bit stream rather than as words; 16- and 32-bit components are read
  aligned. The engine's own half-float variant is decoded with its real bias,
  which is not the IEEE one — reading these as ordinary halves gives plausible
  numbers that are all wrong.
- **The walk is proved, not assumed.** Every shipped clip is checked so that
  each keyframe block ends exactly where the next one begins. A wrong bit width
  drifts and overlaps within a few segments, so this catches mistakes that a
  parser which merely avoids crashing would hide. All 1,787 clips tile.
- **A 20-bit quaternion form is supported.** It is not in the published
  template, and 24 shipped clips use it; three components plus three signs is
  the only width that makes those files tile.
- **Values the engine leaves unset are reported as unset.** Vector tracks store
  32766 or 32767 to mean "no value", and decoding those as numbers produces
  positions of sixteen million metres. They are now labelled rather than shown
  as data.
- **One keyframe can be rewritten.** Choose a track, give the key index and the
  three components, and the editor writes it. Before the file is replaced the
  edited bytes are re-parsed and re-walked: if any block moved, any key count
  changed, or any byte outside that one key differs, the write is refused and
  the file is left alone. Components are checked against the field width rather
  than silently truncated.
- **Frame rate is editable per clip or across a folder**, verified the same way.

### Install detection finds the game on any drive

- **The search is no longer a short list.** Detection used to look only under
  `C:` to `F:` and only inside five folder names, so a game on another drive,
  or in a folder that was not one of those five, simply did not appear. Every
  mounted drive is now searched, including drive roots, which is where most
  copies of this game actually sit.
- **A folder you pick is remembered.** Choosing the game by hand used to last
  until the next restart, after which the app went back to "No install
  detected". The last five are kept and offered first.
- **Two spellings of one folder are one install.** Paths are compared after
  collapsing `.` and `..`, so the same game cannot appear twice.
- **An install is recognised by its `sider.ini`**, not by its folder name, so a
  renamed or relocated copy is still found.

### Menu maker

- **The navigation graph is laid out on two meaningful axes.** Horizontal is
  how deep a screen sits from an entry point; vertical groups screens by the
  folder they belong to, with a shaded lane per group. Screens within a lane are
  ordered to reduce edge crossings, and the result is deterministic, so the same
  set draws identically every time.
- **Links are readable at a glance.** Arrows point, back-links and loops route
  under the nodes instead of through them, dead buttons are red, and a screen
  nothing points at is dashed. Each node shows how many events it has.
- **Clicking an arrow selects that event** for repointing, so editing follows
  the graph rather than a separate list.

### Fixed

- **`menu --check` now requires the base layer on the command line too.** The
  UI has refused to check without one since 1.3.0, and this changelog claimed
  the check could not be run without it. The CLI disagreed and produced a
  report of 344 broken links on a set that was largely fine. It now stops and
  explains why, so the two entry points cannot give different answers.
- **The animation command's own help text was a release behind.** It still said
  keyframe blobs were not decoded after they became decoded and editable, so a
  reader would have skipped a feature that works.

## 1.3.0

### 3D preview

- **Models render from the game's own files.** A folder or container is drawn
  with the colour map each part's material actually binds, from front,
  three-quarter, profile, back or top. Nothing is exported or converted first.
- **Hair is composited rather than pasted.** Long hair is built from layered
  cards whose texture is mostly empty space. The renderer draws opaque parts
  first, then the transparent cards sorted far to near over them, discarding the
  empty texels, so hair reads as strands instead of flat plates.
- **Shared textures are found wherever they live.** Some maps a model asks for
  are not beside it; they sit inside the base game archives. The preview opens
  those archives and reads them from there, so a head shows every layer it
  should rather than the few that happened to be unpacked.
- **Bindings that carry no colour are left alone.** Some parts exist to modulate
  shadow, not to be seen, and their texture is a placeholder. Painting them as
  colour would cover the model with artefacts, so they are skipped and the count
  of textures reported counts real colour maps only.

### Texture editing

- **Replace a texture in place** for faces, hair, kits, boots, balls, emblems,
  logos, symbols and menu art. The editor refuses a format it cannot re-encode
  rather than silently converting it, refuses a size that differs from the file
  the model samples, and refuses a shorter mip chain rather than dropping levels.
- **Every write is verified by reading it back.** Format, size, mip depth and
  decoded pixels are compared against what was intended; a mismatch rejects the
  edit and leaves the file untouched. A backup is kept on first write, and saves
  go through a temporary name and rename so an interrupted write cannot leave a
  half-written asset.
- **Assets are grouped by family from their path**, so the list can never offer
  an edit the editor would refuse.

### Animations

- **`.gani` clips are decoded.** The header is read for every clip in the
  install, giving unit count, segment count, frame rate and the layout of the
  per-unit records. All 1,787 shipped clips parse.
- **Frame rate is editable**, per clip or across a folder. The write is verified
  the same way textures are: only the four rate bytes may change, and anything
  else that moved is refused.
- **Keyframes are not decoded yet**, so poses cannot be moved. The tool states
  this instead of guessing at bytes whose meaning is unproven.

### Menu maker

- **Navigation is read, drawn and edited.** A menu set is a folder of small
  files naming where each button goes. The tab now shows that as a graph:
  screens placed by how deep they sit from the entry screens, arrows for every
  link, dead buttons marked in red, and screens nothing points at drawn dashed.
- **Click to edit.** Select a screen to inspect it, or click an arrow to repoint
  that event directly.
- **A typo cannot become a dead button.** Repointing checks the target resolves
  first and offers the closest existing names. Cloning refuses to overwrite a
  screen that already exists. Unusual spellings of a target — wrong case,
  backslashes, a `.json` suffix — are normalised before matching, because these
  files are hand-authored.
- **Layers are part of the check.** A menu set ships only a subset of the game's
  screens; the rest resolve from the base game. Judging a set alone reports
  hundreds of links as dead that are fine. The base layer is therefore required,
  and resolution follows the engine's own rule: first pack that has the screen,
  base last.
- **Unknown fields survive a round trip.** Screens are written back with every
  key preserved, including ones this tool has no concept of.

### Not in this release

- Animation poses (keyframes) were not decoded at 1.3.0; they are decoded and
  editable in 1.3.1.
- The pixel layout of the compiled menu `.bin` files is still not decoded, so
  menu art can be replaced but a layout cannot be rearranged visually.
- Performance work is not part of this release.

## 1.2.1

### Table editing

- **`.bin` game tables open in the real reader** — framing, sections, record
  stride, inferred fields — so offsets you see are offsets into the decoded
  table, not into the compressed bytes on disk.
- **A patch changes only the bytes you named.** The table is inflated, the
  window replaced, re-framed and saved through a temporary name; the result is
  re-read and diffed against the original. If anything outside the window moved,
  or the length changed, the edit is refused and the file is left untouched.
- **Tables that cannot be re-emitted are read-only**, with the reason shown,
  because saving one would replace a working file with a guess.

### Format identification

Ten defects in the file-identification layer were reproduced and fixed, each now
covered by a test. They fell into three groups:

- **Files loaded whole to read a header.** Identifying a format needs the first
  few dozen bytes; the survey read entire 100 MB textures instead.
- **Coincidences accepted as signatures.** A number that happened to match a
  header value, or a version field read as a magic, renamed unrelated files —
  including databases — as skeletons or camera animations. Signatures now have
  to be signatures.
- **Bookkeeping that misreported coverage.** Editor backups counted as undecoded
  game data, dotfiles were given an extension, two tallies could disagree, and
  an unverified field was labelled a count. The gap report now reflects files the
  tool genuinely cannot read.

## 1.2.0

### Reading and editing game data

- **`foxfpk` asset containers are decoded and rewritten** — entry table, name
  block and payload alignment — so a container can be unpacked, edited and
  repacked. Writing an unchanged file reproduces its bytes exactly.
- **`FMDL` meshes are decoded**: vertices, indices, vertex streams, UV sets,
  authored normals, tangents, bone weights and material assignments. Struct
  sizes were measured against shipped files rather than taken from older
  published tooling, which had since grown.
- **Mesh edits stay inside the channels they own.** Positions, UVs and normals
  are replaced in place, so bones, blendshapes, LODs and material tables keep
  their shipped bytes and an edited model still animates.
- **Material bindings resolve.** Every mesh finds the material it draws with,
  and every material the texture slots it binds and the files those point at.
- **String tables read correctly.** Name offsets are relative to a specific
  block rather than to the section, which previously returned vertex bytes as
  text.

### Format coverage

- **Any file in an install can be identified**, by content first and filename
  second, so a mislabelled file is still named correctly.
- **A directory survey reports what is not yet decoded**, as a measured count
  rather than an impression. Layouts were fitted across hundreds of files, not
  one sample.
- **Undecoded formats say so.** Where a header is understood but the payload is
  not, the output names which part is unsolved.

### The install map

- **Every entry states what breaks.** Each block answers what it is, what goes
  wrong if you change it, and what to do about it. The consequence is derived
  from the risk rating, so no entry can describe a file while saying nothing
  about failure.
- **Risk labels name the outcome**, from "you can put the original back" to "the
  game can refuse to start or corrupt a save that is already written".
- **Explanations describe the game, not third-party mods**, because those claims
  go stale whenever a pack is renamed.

### Interface

- **Text prompts work.** The dialog layer supplies open, save, message, ask and
  confirm but no prompt, so New File, Rename and Go-to-line now use a real
  in-app modal.
- **Failures are reported.** A rejected operation surfaces in the status bar
  instead of looking like a button that does nothing.

### Verification

- The suite runs against real shipped game files rather than fixtures, including
  byte-identical round trips of a container, a mesh and a full archive.
- Release artefacts are checked for freshness: every installer hash is paired
  with a check that no source file is newer than the binary it was built from.
