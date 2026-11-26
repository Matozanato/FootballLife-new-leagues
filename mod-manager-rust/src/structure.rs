//! Inferring the layout of a fixed-stride record from the data itself.
//!
//! Several shipped tables have a measured stride but no published field map —
//! the bulk of a `CompetitionRegulation` record, the head of a `Player` record,
//! the unnamed `.o` blocks inside the match constants. Hand-deriving each one
//! produces a list of magic offsets that nobody can check. This instead looks
//! at every byte column across every record and states what the data supports:
//!
//!   Constant   the same value in every record
//!   Padding    zero in every record — space the format reserves
//!   Counter    a small integer that changes between records
//!   Id         a u32 whose values repeat across records, i.e. a foreign key
//!   Float      a u32 that is a well-formed f32 in a sane range in every record
//!   Text       a run of printable bytes, NUL-padded
//!
//! Each field carries the number of records that support its classification, so
//! an inference can be argued with rather than being presented as fact. Nothing
//! here claims a *meaning*: it says "4-byte float at +112, 197 of 197 records",
//! and the reader decides what the number is for.
//!
//! Sub-record periods are found the same way: score each divisor of the stride
//! by how well the column profile repeats at that period, and report the best
//! one that actually explains the data.

use serde::Serialize;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum FieldKind {
    Constant,
    Padding,
    Counter,
    Id,
    Float,
    Text,
    Mixed,
}

impl FieldKind {
    pub fn label(self) -> &'static str {
        match self {
            FieldKind::Constant => "constant",
            FieldKind::Padding => "padding",
            FieldKind::Counter => "counter",
            FieldKind::Id => "id / key",
            FieldKind::Float => "float",
            FieldKind::Text => "text",
            FieldKind::Mixed => "mixed",
        }
    }
}

#[derive(Debug, Clone, Serialize)]
pub struct Field {
    pub offset: usize,
    pub width: usize,
    pub kind: FieldKind,
    pub records: usize,
    pub supporting: usize,
    pub sample: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct Inferred {
    pub stride: usize,
    pub records: usize,
    pub sub_record: Option<usize>,
    pub fields: Vec<Field>,
    pub mapped_bytes: usize,
    pub coverage: f64,
}

/// Is `bits` a plausible gameplay parameter? The denormal range is excluded
/// deliberately: `0x00000011` read as a float is 1.5e-44, which is finite and
/// tiny, and would otherwise let a constant byte pattern masquerade as a float
/// field. Zero is allowed because real tables contain it. This is the same test
/// `column_stats` applies inline; it is kept for the block reader.
fn f32_sane(bits: u32) -> bool {
    let v = f32::from_bits(bits);
    v.is_finite() && (v == 0.0 || (1e-4..=1e7).contains(&v.abs()))
}

/// Everything the classifiers need about one byte position, in one pass.
///
/// The first version collected the column into a Vec, sorted it, and scanned
/// it again — 312 sorts of 26,710 elements for `Player.bin`, which is what put
/// the reader at 1.8 s. A 256-bucket histogram answers the same questions in
/// one pass with no allocation, and the four-byte statistics ride along in the
/// same loop.
struct ColumnStats {
    all_zero: bool,
    constant: bool,
    /// The whole four-byte value is zero in every record. Distinct from
    /// `all_zero`, which is about one byte: a float field whose values are
    /// 0.0, 0.5, 1.0 has a zero low byte everywhere, and treating that as
    /// padding hides the parameter that is actually there.
    four_zero: bool,
    /// Every u32 at this position has its top two bytes clear.
    hi_zero: bool,
    /// Every u32 here reads as a plausible parameter value.
    all_float: bool,
    /// Every record holds the same four bytes.
    all_same: bool,
    /// How many records repeat a value already seen: the signature of a key.
    repeats: usize,
}

fn column_stats(recs: &[&[u8]], at: usize) -> ColumnStats {
    let mut counts = [0u32; 256];
    for r in recs {
        counts[r[at] as usize] += 1;
    }
    let n = recs.len();
    let all_zero = counts[0] as usize == n;
    let constant = counts.iter().filter(|&&c| c > 0).count() == 1;

    let (mut four_zero, mut hi_zero, mut all_float, mut all_same, mut repeats) =
        (true, true, true, true, 0usize);
    if at + 4 <= recs[0].len() {
        let first = [recs[0][at], recs[0][at + 1], recs[0][at + 2], recs[0][at + 3]];
        let mut seen = std::collections::HashSet::new();
        for r in recs {
            let b = [r[at], r[at + 1], r[at + 2], r[at + 3]];
            if b != [0, 0, 0, 0] {
                four_zero = false;
            }
            if b[2] != 0 || b[3] != 0 {
                hi_zero = false;
            }
            if b != first {
                all_same = false;
            }
            let v = u32::from_le_bytes(b);
            if all_float && !f32_sane(v) {
                all_float = false;
            }
            if !seen.insert(v) {
                repeats += 1;
            }
        }
    } else {
        four_zero = false;
        hi_zero = false;
        all_float = false;
        all_same = constant;
    }
    ColumnStats { all_zero, constant, four_zero, hi_zero, all_float, all_same, repeats }
}

/// Classify the field starting at one offset. Independent of every other
/// offset, which is what lets `infer` run it in parallel.
struct Decision {
    width: usize,
    kind: FieldKind,
    support: usize,
}

fn decide(recs: &[&[u8]], at: usize, stride: usize) -> Decision {
    let s = column_stats(recs, at);
    let n = recs.len();
    if at + 4 <= stride {
        if s.four_zero {
            return Decision { width: 4, kind: FieldKind::Padding, support: n };
        }
        if s.all_same {
            return Decision { width: 4, kind: FieldKind::Constant, support: n };
        }
        if s.all_float {
            return Decision { width: 4, kind: FieldKind::Float, support: n };
        }
        if s.hi_zero && repeats_are_key(s.repeats, n) {
            return Decision { width: 4, kind: FieldKind::Id, support: n };
        }
        if s.hi_zero {
            return Decision { width: 4, kind: FieldKind::Counter, support: n };
        }
        if let Some((w, sup)) = text_run(recs, at, stride) {
            return Decision { width: w, kind: FieldKind::Text, support: sup };
        }
    }
    let (kind, width) = if s.all_zero {
        (FieldKind::Padding, 1)
    } else if s.constant {
        (FieldKind::Constant, 1)
    } else if let Some((w, _)) = text_run(recs, at, stride) {
        (FieldKind::Text, w)
    } else {
        (FieldKind::Counter, 1)
    };
    Decision { width, kind, support: n }
}

fn repeats_are_key(repeats: usize, n: usize) -> bool {
    repeats * 3 > n
}

/// A byte that can begin a name: printable ASCII, a space, or the lead byte
/// of a UTF-8 sequence. FL27 database names are UTF-8, and an ASCII-only test
/// makes a Japanese stadium name look like unexplained bytes.
fn name_start(b: u8) -> bool {
    b.is_ascii_graphic() || b == b' ' || (0xC2..=0xF4).contains(&b)
}

/// A name field: where the records that carry text carry it, and how long
/// those names run.
///
/// Thresholds on the *fraction of all records* fail here. `Boots.bin` is a
/// sparse table: 304 slots of 100 bytes, and only 65 of them hold a name at
/// all. Any "most records" rule therefore rejects a field that is obviously
/// real. Instead, look only at the records that start with text at this
/// offset, take the median length of those names, and report the field with
/// the support it actually has — the UI then says "text in 65 of 304 records",
/// which is the honest and useful statement.
fn text_run(recs: &[&[u8]], offset: usize, stride: usize) -> Option<(usize, usize)> {
    if offset >= stride {
        return None;
    }
    // Measure the names in the records that have one. The sample must come
    // from a holder record at the median length — taking recs[median_index]
    // instead picks an arbitrary record that may be blank, which is how a real
    // name field got rejected for failing the letter test.
    let mut holders: Vec<(usize, &[u8])> = recs.iter()
        // A name starts with printable ASCII or with a UTF-8 lead byte. FL27
        // database names are UTF-8 — the Japanese stadium names in
        // Stadium.bin are invisible to an ASCII-only test, and that is what
        // left two thirds of the record unexplained.
        .filter(|r| name_start(r[offset]))
        .map(|r| {
            let mut k = offset;
            while k < stride && r[k] != 0 {
                k += 1;
            }
            (k - offset, *r)
        })
        .collect();
    if holders.len() < recs.len().max(1) / 8 || holders.len() < 4 {
        return None;
    }
    holders.sort_unstable_by_key(|(len, _)| *len);
    let median = holders[holders.len() / 2].0 + 1; // include the terminator
    let sample = holders[holders.len() / 2].1;
    // A name field of one or two characters is noise, and one spanning most of
    // the record is not a name either — binary data that merely happens to be
    // printable has no NUL in it, which is how `Boots.bin` looked like a
    // 100-byte string at +0. Cap it at a third of the record and require the
    // median name to be mostly letters, spaces and punctuation.
    if median < 5 || median * 3 > stride {
        return None;
    }
    let body = &sample[offset..(offset + median - 1).min(stride)];
    // Require the run to be text, not merely byte-without-NULs. An ASCII name
    // has to be mostly letters; anything with high bytes has to decode as
    // valid UTF-8, which random binary almost never does.
    if body.is_empty() {
        return None;
    }
    if body.iter().any(|b| *b >= 0x80) {
        if std::str::from_utf8(body).is_err() {
            return None;
        }
    } else {
        let alpha = body.iter()
            .filter(|b| b.is_ascii_alphabetic() || **b == b' ')
            .count();
        if alpha * 2 < body.len() {
            return None;
        }
    }
    // Never let a field run past the end of the record.
    Some((median.min(stride - offset), holders.len()))
}

/// Where the names in a body begin. Names are the strongest evidence of a
/// record boundary in these tables: a stride is only right if every name in
/// the file starts inside a text field of its layout.
pub fn name_starts(body: &[u8]) -> Vec<usize> {
    let mut starts = Vec::new();
    let mut run_start: Option<usize> = None;
    for (i, &b) in body.iter().enumerate() {
        match (run_start, name_start(b)) {
            (None, true) => run_start = Some(i),
            (Some(s), false) => {
                if i - s >= 4 {
                    starts.push(s);
                }
                run_start = None;
            }
            _ => {}
        }
    }
    starts
}

/// Suggest a record stride from the spacing of the text runs in the body.
///
/// Named tables — boots, gloves, balls, stadiums — carry one or more names per
/// record, so the gaps between consecutive run starts pile up on the stride.
/// This is how `Boots.bin` is found to be 100-byte records: its names begin at
/// 4, 104, 204, 304. Guessing from divisors of the file length picked 64, which
/// tiles but explains nothing.
///
/// Looking only at adjacent names cannot see a record that holds more than one
/// name: `Stadium.bin` alternates 181 and 211 because each record carries an
/// internal name and a display name, and neither distance is the 392-byte
/// record. Measuring two and three steps apart finds it, because the same slot
/// in the next record is exactly one record away.
pub fn stride_from_names(body: &[u8]) -> Option<usize> {
    let starts = name_starts(body);
    if starts.len() < 6 || body.len() < 512 {
        return None;
    }
    for step in 1..=3usize {
        if starts.len() <= step {
            break;
        }
        let mut gaps: std::collections::HashMap<usize, usize> = Default::default();
        for i in 0..starts.len() - step {
            *gaps.entry(starts[i + step] - starts[i]).or_default() += 1;
        }
        let mut ranked: Vec<(usize, usize)> = gaps.into_iter().collect();
        ranked.sort_by_key(|(gap, hits)| (std::cmp::Reverse(*hits), *gap));
        let Some(&(gap, hits)) = ranked.first() else {
            continue;
        };
        // A clear third of the pairs must sit that far apart, and the distance
        // has to tile the body: otherwise this is prose, not a record array.
        if hits * 3 >= starts.len()
            && gap >= 8
            && body.len().is_multiple_of(gap)
            && body.len() / gap >= 4
        {
            return Some(gap);
        }
    }
    None
}

fn sample_of(recs: &[&[u8]], offset: usize, width: usize, kind: FieldKind) -> String {
    // For text, quote a record that actually holds text. The middle record of a
    // sparse table is usually blank, and printing its control bytes as
    // "\u{1f}" made a real name field look like unreadable garbage.
    let r = match kind {
        FieldKind::Text => recs.iter()
            .find(|r| name_start(r[offset]))
            .copied()
            .unwrap_or(recs[recs.len() / 2]),
        _ => recs[recs.len() / 2],
    };
    let bytes = &r[offset..offset + width];
    match kind {
        FieldKind::Float => {
            let v = f32::from_bits(u32::from_le_bytes([bytes[0], bytes[1], bytes[2], bytes[3]]));
            format!("{v:.4}")
        }
        FieldKind::Id | FieldKind::Counter => {
            if width == 1 { format!("{}", bytes[0]) }
            else { format!("{}", u32::from_le_bytes([bytes[0], bytes[1], bytes[2], bytes[3]])) }
        }
        FieldKind::Text => {
            let end = bytes.iter().position(|&b| b == 0).unwrap_or(bytes.len());
            format!("{:?}", String::from_utf8_lossy(&bytes[..end]))
        }
        _ => bytes.iter().take(8).map(|b| format!("{b:02x}")).collect::<Vec<_>>().join(" "),
    }
}

/// Best repeating sub-record period, scored on how well the column "is zero"
/// profile aligns with itself at that offset.
///
/// Periods below 16 are ignored: a 2-byte period agrees almost everywhere on
/// any record with padding, and reporting it as the structure would be worse
/// than reporting nothing. Non-divisors are allowed because a block does not
/// have to tile the record exactly to be real.
fn sub_record_period(recs: &[&[u8]], stride: usize) -> Option<usize> {
    if recs.len() < 8 || stride < 64 {
        return None;
    }
    let zero_profile: Vec<bool> = (0..stride)
        .map(|k| column_stats(recs, k).all_zero)
        .collect();
    let mut best = None;
    let mut best_score = 0.0f64;
    for p in 16..=stride / 2 {
        let agree = (p..stride).filter(|&k| zero_profile[k] == zero_profile[k - p]).count();
        let score = agree as f64 / (stride - p) as f64;
        if score > best_score && score > 0.98 {
            best_score = score;
            best = Some(p);
        }
    }
    best
}

/// Infer the layout of `body` read as `records` rows of `stride` bytes.
pub fn infer(body: &[u8], stride: usize) -> Option<Inferred> {
    use rayon::prelude::*;

    if stride == 0 || !body.len().is_multiple_of(stride) {
        return None;
    }
    let rows: Vec<&[u8]> = body.chunks(stride).collect();
    if rows.len() < 4 {
        return None;
    }
    let sub = sub_record_period(&rows, stride);

    // Every offset is classified independently, so this is the part worth
    // parallelising; the merge below has to stay in order.
    let decisions: Vec<Decision> = (0..stride).into_par_iter()
        .map(|at| decide(&rows, at, stride))
        .collect();

    let mut fields: Vec<Field> = Vec::new();
    let mut at = 0usize;
    while at < stride {
        let d = &decisions[at];
        let (width, kind, support) = (d.width, d.kind, d.support);
        let next = (at + width).min(stride);
        // Padding, constants and counters merge when adjacent, because a long
        // run of them is one reserved gap. Text must not: a name field has a
        // terminator and a length of its own, and merging two adjacent ones
        // turned `Boots.bin`'s whole 100-byte record into a single "name".
        let merge = kind != FieldKind::Text
            && fields.last()
                .map(|l| l.kind == kind && l.offset + l.width == at)
                .unwrap_or(false);
        if merge {
            fields.last_mut().unwrap().width += next - at;
        } else {
            fields.push(Field {
                offset: at,
                width: next - at,
                kind,
                records: rows.len(),
                supporting: support,
                sample: sample_of(&rows, at, next - at, kind),
            });
        }
        at = next;
    }

    // A 35-byte "counter" is not a counter. Single-byte columns that merely
    // vary merge freely, but once a run is too wide to be one small integer it
    // is unexplained data and has to be labelled that way.
    for f in fields.iter_mut() {
        if f.kind == FieldKind::Counter && f.width > 8 {
            f.kind = FieldKind::Mixed;
            f.supporting = 0;
            f.sample = format!("{} bytes, no interpretation holds", f.width);
        }
    }

    let mapped: usize = fields.iter()
        .filter(|f| f.kind != FieldKind::Padding && f.kind != FieldKind::Mixed)
        .map(|f| f.width)
        .sum();
    Some(Inferred {
        stride,
        records: rows.len(),
        sub_record: sub,
        fields,
        mapped_bytes: mapped,
        coverage: mapped as f64 / stride as f64,
    })
}

/// Best row width for a free-form block.
///
/// Scoring candidates by "does this read as floats" is useless: almost any
/// parameter block passes at a row width of 4, which reported `cpuLevel.o` as
/// 276 rows of one column and told the reader nothing. The signal that
/// actually identifies a row is that the block's shape repeats every row, so
/// the zero/non-zero profile is compared against itself shifted by each
/// candidate and the best-explaining period wins. `cpuLevel.o` is a 16-byte
/// header then 34 rows of 32 bytes, and 32 is what this finds.
pub fn best_row_width(data: &[u8]) -> Option<(usize, usize)> {
    if data.len() < 256 {
        return None;
    }
    let profile: Vec<bool> = data.iter().map(|&b| b == 0).collect();
    let mut best: Option<(usize, f64)> = None;
    for row in 8..=512usize {
        if data.len() / row < 4 {
            break;
        }
        let agree = (row..data.len()).filter(|&k| profile[k] == profile[k - row]).count();
        let score = agree as f64 / (data.len() - row) as f64;
        if score > 0.95 && best.is_none_or(|(_, s)| score > s) {
            best = Some((row, score));
        }
    }
    let (row, _) = best?;
    Some((row, data.len() / row))
}

/// Infer the layout of a block of `.o` section data: a count followed by a
/// repeated row of floats is by far the common shape in the match constants.
pub fn infer_block(data: &[u8]) -> Option<(usize, usize, Vec<f32>)> {
    if data.len() < 8 {
        return None;
    }
    let count = u32::from_le_bytes([data[0], data[1], data[2], data[3]]) as usize;
    let rest = &data[4..];
    if count == 0 || count > 100_000 || !rest.len().is_multiple_of(count) {
        return None;
    }
    let row = rest.len() / count;
    if row == 0 || !row.is_multiple_of(4) {
        return None;
    }
    let floats: Vec<f32> = rest.chunks_exact(4)
        .map(|c| f32::from_le_bytes([c[0], c[1], c[2], c[3]]))
        .collect();
    let sane = floats.iter()
        .filter(|v| f32_sane(v.to_bits()) || v.abs() > 1e7)
        .count();
    if sane * 20 < floats.len() * 19 {
        return None; // more than 5% nonsense values: this is not a float table
    }
    Some((count, row, floats))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn rows(records: usize, f: impl Fn(usize) -> Vec<u8>) -> Vec<u8> {
        let mut out = Vec::new();
        for i in 0..records {
            out.extend_from_slice(&f(i));
        }
        out
    }

    #[test]
    fn padding_and_constants_are_separated() {
        // 16-byte stride: id u32, then 8 zero bytes, then a constant 0x11.
        let body = rows(20, |i| {
            let mut r = vec![0u8; 16];
            r[..4].copy_from_slice(&(i as u32).to_le_bytes());
            r[12] = 0x11;
            r
        });
        let got = infer(&body, 16).unwrap();
        assert_eq!(got.records, 20);
        let pad = got.fields.iter().find(|f| f.kind == FieldKind::Padding).unwrap();
        assert_eq!((pad.offset, pad.width), (4, 8));
        // +12 is 11 00 00 00 in every record: a constant, read as one 4-byte
        // field rather than as a byte plus three padding bytes.
        let c = got.fields.iter().find(|f| f.kind == FieldKind::Constant).unwrap();
        assert_eq!((c.offset, c.width), (12, 4));
    }

    #[test]
    fn float_columns_are_recognised() {
        let body = rows(30, |i| {
            let mut r = vec![0u8; 8];
            let v = (i as f32) * 0.5;
            r[..4].copy_from_slice(&v.to_le_bytes());
            r
        });
        let got = infer(&body, 8).unwrap();
        assert!(got.fields.iter().any(|f| f.kind == FieldKind::Float),
                "{:?}", got.fields);
    }

    #[test]
    fn text_runs_are_recognised_and_sampled() {
        // Names must differ per record, or the run is genuinely constant and
        // the correct answer is Constant, not Text.
        let names = ["Ireland", "Scotland", "Wales", "France", "Spain",
                     "Italy", "Germany", "Portugal", "Brazil", "Japan"];
        let body = rows(10, |i| {
            let mut r = vec![0u8; 32];
            r[..4].copy_from_slice(&(i as u32).to_le_bytes());
            r[8..8 + names[i].len()].copy_from_slice(names[i].as_bytes());
            r
        });
        let got = infer(&body, 32).unwrap();
        let t = got.fields.iter().find(|f| f.kind == FieldKind::Text).unwrap();
        assert_eq!(t.offset, 8);
        // The sample is the middle record, not the first, so it must be one of
        // the names actually present rather than a specific one.
        assert!(names.iter().any(|n| t.sample.contains(n)), "{}", t.sample);
    }

    #[test]
    fn sub_record_period_is_found() {
        // 240 bytes made of 4 identical 60-byte blocks, first byte of each
        // block a counter and the rest zero.
        let body = rows(12, |_| {
            let mut r = vec![0u8; 240];
            for b in 0..4 {
                r[b * 60] = 7;
            }
            r
        });
        let got = infer(&body, 240).unwrap();
        assert_eq!(got.sub_record, Some(60), "expected the 60-byte period");
    }

    #[test]
    fn a_float_block_is_inferred_from_section_data() {
        let mut d = vec![0u8; 4];
        d[..4].copy_from_slice(&3u32.to_le_bytes());
        for _ in 0..3 {
            for v in [1.0f32, 2.5, 0.125] {
                d.extend_from_slice(&v.to_le_bytes());
            }
        }
        let (count, row, floats) = infer_block(&d).unwrap();
        assert_eq!((count, row), (3, 12));
        assert_eq!(floats.len(), 9);
        assert!((floats[1] - 2.5).abs() < 1e-6);
    }

    #[test]
    fn nonsense_blocks_are_not_claimed_as_float_tables() {
        // A count that does not divide the data, and a block whose "floats"
        // are NaN, must both be refused rather than reported as a parameter
        // table.
        let mut misaligned = vec![0u8; 4];
        misaligned[..4].copy_from_slice(&7u32.to_le_bytes());
        misaligned.extend_from_slice(&[0u8; 401]);
        assert!(infer_block(&misaligned).is_none(), "count must divide the data");

        let mut junk = vec![0u8; 4];
        junk[..4].copy_from_slice(&10u32.to_le_bytes());
        for _ in 0..100 {
            junk.extend_from_slice(&f32::NAN.to_le_bytes());
        }
        assert!(infer_block(&junk).is_none(), "NaN is not a parameter value");
    }

    #[test]
    fn the_unmapped_part_of_a_regulation_record_is_explained() {
        // Before the inferrer this region was reported as "2.3 KB unmapped".
        // The record turns out to be a run of ~79-byte blocks, each a data
        // area plus a 4-byte key plus padding, with an internal name token at
        // +1055 — all of it found from the bytes, not from documentation.
        let p = crate::install::game_root()
            .join("SiderAddons/livecpk/DR_LeagueCreator/common/etc/pesdb/CompetitionRegulation.bin");
        if !p.exists() {
            return;
        }
        let raw = std::fs::read(p).unwrap();
        let body = crate::wesys::decode(&raw).unwrap().body;
        let got = infer(&body, 2352).unwrap();
        assert_eq!(got.records, 197);
        assert!(got.sub_record.is_none() || got.sub_record.unwrap() >= 16,
                "a trivial 2-byte period must not be reported: {:?}", got.sub_record);
        // The point of this test is the cross-check: the hand-written map in
        // binread says the display name sits at +1087, and the inferrer — which
        // is given nothing but the bytes — must find a text field there too.
        // Asserting a specific record's value would only prove the sample is
        // stable, not that the layout was recovered.
        assert!(got.fields.iter().any(|f| f.kind == FieldKind::Text && f.offset == 1087),
                "expected the inferrer to find the name field at +1087, got {:?}",
                got.fields.iter().filter(|f| f.offset > 1000 && f.offset < 1150)
                    .map(|f| (f.offset, f.width, f.kind.label())).collect::<Vec<_>>());
        assert!(got.fields.iter().any(|f| f.kind == FieldKind::Padding && f.width > 40));
        let total: usize = got.fields.iter().map(|f| f.width).sum();
        assert_eq!(total, 2352, "fields must tile the record");
        // No over-long run may still be labelled a counter.
        assert!(!got.fields.iter().any(|f| f.kind == FieldKind::Counter && f.width > 8));
    }

    #[test]
    fn fields_tile_real_tables_exactly_with_no_overrun() {
        // A text field whose median length was computed without clamping to
        // the record produced "101 of 100 bytes explained". That is not a
        // rounding issue: it means fields overlap, so inference on shipped
        // tables must tile each stride exactly.
        //
        // A named list rather than a walk of livecpk: several packs carry
        // their own 8 MB Player.bin, and inferring over all of them pushed the
        // suite from 27 s to 279 s for no extra coverage.
        let dir = crate::install::game_root()
            .join("SiderAddons/livecpk/DR_LeagueCreator/common/etc/pesdb");
        if !dir.is_dir() {
            return;
        }
        let names = ["Competition.bin", "CompetitionEntry.bin",
                     "CompetitionRegulation.bin", "Team.bin", "Player.bin"];
        let mut files = 0;
        for name in names {
            let p = dir.join(name);
            if !p.exists() {
                continue;
            }
            let raw = std::fs::read(&p).unwrap();
            let body = match crate::wesys::decode(&raw) {
                Ok(f) if f.kind == crate::wesys::Kind::Wesys => f.body,
                _ => continue,
            };
            let stride = crate::pesdb::stride_for(name).unwrap_or(0) as usize;
            let Some(got) = (stride >= 8 && body.len() % stride == 0)
                .then(|| infer(&body, stride)).flatten() else { continue };
            let mut cursor = 0;
            for f in &got.fields {
                assert_eq!(f.offset, cursor,
                    "{name}: gap or overlap at {cursor} (field {:?})", f);
                assert!(f.width >= 1, "{name}: zero-width field at {}", f.offset);
                cursor += f.width;
            }
            assert_eq!(cursor, stride, "{name}: fields do not cover the record");
            assert!(got.mapped_bytes <= stride,
                    "{name}: {} mapped over a stride of {stride}", got.mapped_bytes);
            files += 1;
        }
        assert!(files >= 3, "expected to check several shipped tables, got {files}");
    }

    #[test]
    fn a_real_section_gets_a_row_width() {
        // cpuLevel.o is a 16-byte header then 34 rows of 32 bytes, so the
        // count does not divide the remainder and the tidy reading fails.
        let p = crate::install::game_root()
            .join("FL27 Megapatch/out/rt/common/match/constant/constant_match.bin");
        if !p.exists() {
            return;
        }
        let data = crate::binread::section_bytes(&p, 8).unwrap();
        assert_eq!(data.len(), 1104);
        let (row, rows) = best_row_width(&data).expect("a repeating row width");
        assert_eq!(row, 32, "cpuLevel.o rows are 32 bytes");
        assert!(rows >= 30, "expected the 34 rows, got {rows}");
    }

    #[test]
    fn adjacent_text_fields_do_not_merge_into_the_whole_record() {
        // Boots.bin is 304 records of 100 bytes and only 68 hold a name.
        // Merging neighbouring text fields claimed all 100 bytes were one
        // name, which is not a layout, it is an artefact of the merge rule.
        let p = crate::install::game_root()
            .join("SiderAddons/livecpk/root/boot-root/common/etc/pesdb/Boots.bin");
        if !p.exists() {
            return;
        }
        let raw = std::fs::read(p).unwrap();
        let body = crate::wesys::decode(&raw).unwrap().body;
        let got = infer(&body, 100).unwrap();
        assert!(!got.fields.iter()
                .any(|f| f.kind == FieldKind::Text && f.width >= 100),
                "one text field cannot span the whole record: {:?}",
                got.fields.iter().map(|f| (f.offset, f.width, f.kind.label()))
                    .collect::<Vec<_>>());
    }

    #[test]
    fn coverage_never_exceeds_the_stride() {
        let body = rows(16, |i| {
            let mut r: Vec<u8> = (0..64).map(|k| ((i * 31 + k) % 256) as u8).collect();
            r[0] = 1;
            r
        });
        let got = infer(&body, 64).unwrap();
        assert!(got.mapped_bytes <= 64);
        assert!(got.coverage <= 1.0001);
        // Fields must tile the record exactly, with no gaps or overlaps.
        let mut cursor = 0;
        for f in &got.fields {
            assert_eq!(f.offset, cursor, "gap or overlap at {cursor}");
            cursor += f.width;
        }
        assert_eq!(cursor, 64, "fields must cover the whole stride");
    }
}
