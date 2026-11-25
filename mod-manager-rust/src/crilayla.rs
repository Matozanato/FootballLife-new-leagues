//! CRILAYLA compression — the writer half of CRI's LZSS variant.
//!
//! The blob layout, measured against real `dt00_x64.cpk` entries:
//!
//!   `"CRILAYLA" | u32 uncompressed | u32 payload_len | payload | tail[256]`
//!
//! with `FileSize = 16 + payload_len + 256` and `ExtractSize = uncompressed + 256`.
//! For example `Asset/effect/#Win/common_effect.fpk.xml` is stored as
//! FileSize 448 = 16 + 176 + 256 with uncompressed 398, and extracts to
//! 654 = 398 + 256.
//!
//! The decompressor builds its output **backwards** from the end of the buffer,
//! reads the bit stream **MSB-first from the last payload byte backwards**, and
//! takes the first 256 output bytes verbatim from the trailing 256 input bytes.
//!
//! That makes the encoder a straightforward LZ77 if you look at it the right
//! way. The decoder emits output at descending positions, so the first token it
//! decodes produces the *last* plaintext byte, and every back-reference points
//! to a byte it has already produced. Reverse the plaintext after the 256-byte
//! seed and both properties flip to the ordinary direction: tokenising
//! `reverse(P[256..])` left to right, with matches pointing backwards, is
//! exactly what the decoder expects. Distances and lengths carry over
//! unchanged.
//!
//! Length is not a single field. It starts at 3 and adds a 2-bit value; if that
//! field is saturated it adds a 3-bit value; if that saturates, a 5-bit value;
//! and then 8-bit values for as long as each one saturates. Distances are 13
//! bits plus 3.

use anyhow::Result;

const MAGIC: &[u8; 8] = b"CRILAYLA";
const SEED: usize = 256;
const MAX_DISTANCE: usize = (1 << 13) - 1 + 3;
const MAX_MATCH: usize = 65535;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Token {
    Literal(u8),
    Match { distance: usize, length: usize },
}

/// Easier to reason about: collect bits in order, then pack once at the end.
#[derive(Default)]
struct BitVec {
    bits: Vec<u8>,
}

impl BitVec {
    fn bit(&mut self, b: u8) {
        self.bits.push(b & 1);
    }

    fn value(&mut self, v: usize, width: usize) {
        for k in (0..width).rev() {
            self.bits.push(((v >> k) & 1) as u8);
        }
    }

    /// Pack into `payload_len` bytes so that bit k of this stream sits at
    /// MSB-minus-k of byte (len-1-k/8), which is where the decoder reads it.
    fn into_payload(self, payload_len: usize) -> Vec<u8> {
        let mut out = vec![0u8; payload_len];
        for (k, bit) in self.bits.iter().enumerate() {
            if bit & 1 == 0 {
                continue;
            }
            let byte = payload_len - 1 - k / 8;
            out[byte] |= 1 << (7 - k % 8);
        }
        out
    }

    fn len_bits(&self) -> usize {
        self.bits.len()
    }
}

/// Encode a length as 3 + saturated escalating fields.
///
/// The 8-bit tail repeats as many times as the value needs: the longest match
/// this module emits (65535) takes 257 of them. An earlier bound of 64 rounds
/// silently truncated anything past about 16 KB, which is exactly the shape of
/// the long zero runs in `.rpd` and `.fpk` files, and the decoder then read a
/// short length and desynchronised. The bound is now generous and the test
/// covers a run well past the old limit.
fn encode_length(bits: &mut BitVec, length: usize) {
    let mut rem = length.saturating_sub(3);
    let fields = [2usize, 3, 5];
    let mut idx = 0;
    loop {
        let width = if idx < fields.len() { fields[idx] } else { 8 };
        let max = (1usize << width) - 1;
        let v = rem.min(max);
        bits.value(v, width);
        if v < max {
            break;
        }
        rem -= max;
        idx += 1;
        debug_assert!(idx < 1024, "length {length} needs an unreasonable number of fields");
    }
}

fn encode_token(bits: &mut BitVec, token: Token) {
    match token {
        Token::Literal(b) => {
            bits.bit(0);
            bits.value(b as usize, 8);
        }
        Token::Match { distance, length } => {
            bits.bit(1);
            bits.value(distance - 3, 13);
            encode_length(bits, length);
        }
    }
}

// ------------------------------------------------------------------ matcher

/// Greedy longest-match LZ77 over `q`, with matches limited to the window the
/// decoder can actually reach.
fn tokenise(q: &[u8]) -> Vec<Token> {
    let n = q.len();
    // Hash chains on 3-byte sequences: head[h] is the most recent position,
    // prev[i] the previous position sharing i's hash.
    const HASH_BITS: usize = 16;
    let mut head = vec![usize::MAX; 1 << HASH_BITS];
    let mut prev = vec![usize::MAX; n];
    let mut tokens = Vec::with_capacity(n / 2 + 16);

    let key = |i: usize| -> usize {
        let v = (q[i] as u32) | ((q[i + 1] as u32) << 8) | ((q[i + 2] as u32) << 16);
        (v.wrapping_mul(0x9E37_79B1) >> (32 - HASH_BITS)) as usize
    };

    let mut i = 0usize;
    while i < n {
        let mut best_len = 0usize;
        let mut best_dist = 0usize;

        if i + 3 <= n {
            // The decoder aborts a token whose distance exceeds the number of
            // bytes still ahead of its write cursor. That cursor is
            // (n + SEED) - i, so the reachable window narrows over the last
            // few kilobytes of the plaintext — which is the first few
            // kilobytes after the seed.
            let reach = ((n + SEED - i).saturating_sub(1)).min(MAX_DISTANCE);
            let mut c = head[key(i)];
            let mut checked = 0usize;
            while c != usize::MAX && checked < 64 {
                let dist = i - c;
                if dist > MAX_DISTANCE {
                    break;
                }
                // The format stores distance minus three, so a run closer than
                // three bytes back is not encodable however good it looks.
                // The comparison walks the same relation the decoder applies:
                // output[k] must equal output[k - dist]. For k < dist that is
                // the already-produced source; for k >= dist it is this token's
                // own earlier byte, which is the overlapping-run case. Either
                // way the index stays below i + len, so it is always in bounds.
                if dist >= 3 && dist <= reach {
                    let mut len = 0usize;
                    while len < MAX_MATCH && i + len < n
                        && q[i + len] == q[i + len - dist]
                    {
                        len += 1;
                    }
                    if len > best_len {
                        best_len = len;
                        best_dist = dist;
                        if best_len >= MAX_MATCH || i + best_len >= n {
                            break;
                        }
                    }
                }
                c = prev[c];
                checked += 1;
            }
        }

        if best_len >= 3 {
            tokens.push(Token::Match { distance: best_dist, length: best_len });
            // Index every position the match covers so later bytes can reach it.
            // j is needed as an index into three different arrays, so this is
            // deliberately a range loop rather than a slice iterator.
            #[allow(clippy::needless_range_loop)]
            for j in i..(i + best_len).min(n) {
                if j + 3 <= n {
                    let h = key(j);
                    prev[j] = head[h];
                    head[h] = j;
                }
            }
            i += best_len;
        } else {
            tokens.push(Token::Literal(q[i]));
            if i + 3 <= n {
                let h = key(i);
                prev[i] = head[h];
                head[h] = i;
            }
            i += 1;
        }
    }
    tokens
}

// ------------------------------------------------------------------ public

/// Compress `data` into a CRILAYLA blob. Returns `None` when the input is too
/// short for the 256-byte seed or the result would not beat storing it.
pub fn compress(data: &[u8]) -> Option<Vec<u8>> {
    if data.len() <= SEED + 16 {
        return None;
    }
    let tail = &data[..SEED];
    let rest: Vec<u8> = data[SEED..].iter().rev().copied().collect();
    let tokens = tokenise(&rest);

    let mut bits = BitVec::default();
    for t in &tokens {
        encode_token(&mut bits, *t);
    }
    // The reader stops when it runs out of payload, so pad to a byte boundary.
    let payload_len = bits.len_bits().div_ceil(8);
    while bits.len_bits() % 8 != 0 {
        bits.bit(0);
    }
    let payload = bits.into_payload(payload_len);

    let mut out = Vec::with_capacity(16 + payload_len + SEED);
    out.extend_from_slice(MAGIC);
    out.extend_from_slice(&((data.len() - SEED) as u32).to_le_bytes());
    out.extend_from_slice(&(payload_len as u32).to_le_bytes());
    out.extend_from_slice(&payload);
    out.extend_from_slice(tail);
    Some(out)
}

/// True when a blob round-trips back to `data` through the real decompressor.
pub fn verify(blob: &[u8], data: &[u8]) -> Result<bool> {
    let back = crate::cpk::crilayla_decompress(blob)?;
    Ok(back == data)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn bit_packing_places_the_first_bit_at_the_end() {
        let mut b = BitVec::default();
        b.bit(1);
        b.bit(0);
        let p = b.into_payload(1);
        // The reader takes bit 0 from the LAST payload byte, MSB first. With a
        // one-byte payload that is byte 0 bit 7, so 0x80 -- not 0x01.
        assert_eq!(p, vec![0b1000_0000]);
        let mut b2 = BitVec::default();
        b2.bit(0);
        b2.bit(1);
        assert_eq!(b2.into_payload(1), vec![0b0100_0000]);
    }

    #[test]
    fn length_fields_escalate_only_when_saturated() {
        for len in [3usize, 4, 5, 6, 7, 10, 11, 40, 41, 300, 1000, 4000] {
            let mut b = BitVec::default();
            encode_length(&mut b, len);
            // Re-read exactly the way the decoder does.
            let bits = b.bits.clone();
            let mut pos = 0usize;
            let mut total = 3usize;
            let widths = [2usize, 3, 5];
            let mut idx = 0;
            loop {
                let w = if idx < widths.len() { widths[idx] } else { 8 };
                let mut v = 0usize;
                for _ in 0..w {
                    v = (v << 1) | bits[pos] as usize;
                    pos += 1;
                }
                total += v;
                if v < (1 << w) - 1 {
                    break;
                }
                idx += 1;
            }
            assert_eq!(total, len, "length {len} round-tripped as {total}");
        }
    }

    #[test]
    fn tokens_decode_back_to_the_original_bytes() {
        let cases: Vec<Vec<u8>> = vec![
            b"the quick brown fox jumps over the quick brown fox again".to_vec(),
            vec![0u8; 4096],
            (0..5000u32).map(|i| (i % 7) as u8).collect(),
            {
                let mut v: Vec<u8> = (0..1000).map(|i| (i % 251) as u8).collect();
                v.extend_from_slice(&v.clone()[..500]);
                v
            },
        ];
        for data in cases {
            let mut d = vec![0u8; SEED];
            d.extend_from_slice(&data);
            let blob = compress(&d).expect("compressible");
            let back = crate::cpk::crilayla_decompress(&blob).unwrap();
            assert_eq!(back, d, "round trip differs for a {} byte input", d.len());
        }
    }

    #[test]
    fn long_runs_encode_past_the_old_field_limit() {
        // 40 KB of one byte is a single match longer than the 16 KB the earlier
        // 64-field bound could express. Real .rpd and .fpk payloads are full of
        // these, and truncating one desynchronises everything after it.
        for run in [16_383usize, 16_387, 20_000, 40_000, 65_535] {
            let mut d = vec![0u8; SEED];
            d.resize(SEED + run, 0xAB);
            let blob = compress(&d).expect("compressible");
            let back = crate::cpk::crilayla_decompress(&blob).unwrap();
            assert_eq!(back, d, "a {run}-byte run did not survive");
            // One long match, not thousands of literals.
            assert!(blob.len() < 4096, "{run}-byte run encoded to {} bytes", blob.len());
        }
    }

    #[test]
    fn every_compressed_dt00_entry_round_trips() {
        // The six-entry sample above passed while 15 of 606 files were wrong,
        // so the real check is: take every compressed entry, not a handful.
        use std::io::{Read, Seek, Write};
        let cpk_path = std::path::Path::new(crate::install::GAME_ROOT)
            .join("Data/dt00_x64.cpk");
        if !cpk_path.exists() {
            return;
        }
        let cpk = crate::cpk::Cpk::open(&cpk_path).unwrap();
        let mut file = std::fs::File::open(cpk_path).unwrap();
        let mut checked = 0;
        let mut failed = Vec::new();
        for entry in cpk.files.iter().filter(|f| f.compressed()) {
            let mut raw = vec![0u8; entry.size as usize];
            file.seek(std::io::SeekFrom::Start(cpk.content_offset + entry.offset)).unwrap();
            file.read_exact(&mut raw).unwrap();
            let plain = crate::cpk::crilayla_decompress(&raw).unwrap();
            let blob = match compress(&plain) {
                Some(b) => b,
                None => continue,
            };
            let mut out = std::io::Cursor::new(Vec::new());
            out.write_all(&blob).unwrap();
            if crate::cpk::crilayla_decompress(&blob).unwrap() != plain {
                failed.push(entry.path());
            }
            checked += 1;
        }
        assert!(checked > 200, "expected to exercise most of the 298, got {checked}");
        assert!(failed.is_empty(), "{} entries failed to round-trip: {:?}",
                failed.len(), &failed[..failed.len().min(5)]);
    }

    #[test]
    fn tiny_inputs_are_left_stored() {
        assert!(compress(&vec![0u8; 100]).is_none());
        assert!(compress(&vec![0u8; SEED]).is_none());
    }

    #[test]
    fn real_dt00_entries_compress_and_decompress_back() {
        use std::io::Read;
        use std::path::Path;
        let cpk_path = Path::new(crate::install::GAME_ROOT)
            .join("Data/dt00_x64.cpk");
        if !cpk_path.exists() {
            return;
        }
        let cpk = crate::cpk::Cpk::open(&cpk_path).unwrap();
        let mut checked = 0;
        for entry in cpk.files.iter().filter(|f| f.compressed()).take(6) {
            let mut f = std::fs::File::open(&cpk_path).unwrap();
            use std::io::Seek;
            f.seek(std::io::SeekFrom::Start(cpk.content_offset + entry.offset)).unwrap();
            let mut raw = vec![0u8; entry.size as usize];
            f.read_exact(&mut raw).unwrap();
            let plain = crate::cpk::crilayla_decompress(&raw).unwrap();
            assert_eq!(plain.len(), entry.extract_size as usize);

            let blob = compress(&plain).expect("compressible entry");
            let back = crate::cpk::crilayla_decompress(&blob).unwrap();
            assert_eq!(back, plain, "{} did not round-trip", entry.path());
            // Our size must be within a sane margin of CRI's own.
            let ratio = blob.len() as f64 / entry.size as f64;
            assert!(ratio < 1.35, "{} grew to {ratio:.2}x CRI's size", entry.path());
            checked += 1;
        }
        assert!(checked > 0, "dt00 should contain compressed entries");
    }
}