//! BC7 (BPTC) block decoding: one 16-byte block to 16 RGBA8 pixels.
//!
//! The per-mode field widths are the Microsoft "BC7 Format Mode Reference"
//! table. The two partition sets are the standard BPTC shapes with the fix-up
//! texel of each subset flagged in the high bits (128/129/130), which is what
//! tells the decoder to read one index bit fewer there.
//!
//! This follows iOrange/bcdec (MIT) for the endpoint expansion, and its arrays
//! agree with that reference mode-for-mode. ftex code 11 is BC7: measured on
//! real files, 99.8% of blocks carry a legal mode prefix and byte0 is dominated
//! by 0x10/0x20/0x40, and `.dds` siblings shipped in the packs name it
//! DXGI_FORMAT_BC7_UNORM (98).

/// Stored bits for one RGB endpoint, for one alpha endpoint, subsets, partition
/// field bits, primary index bits, secondary index bits, whether the block has
/// a rotation field, an index-selection bit, and P-bits.
type Mode = (usize, usize, usize, usize, usize, usize, bool, bool, bool);

const MODES: [Mode; 8] = [
    (4, 0, 3, 4, 3, 0, false, false, true),  // 0
    (6, 0, 2, 6, 3, 0, false, false, true),  // 1
    (5, 0, 3, 6, 2, 0, false, false, false), // 2
    (7, 0, 2, 6, 2, 0, false, false, true),  // 3
    (5, 6, 1, 0, 2, 3, true, true, false),   // 4
    (7, 8, 1, 0, 2, 2, true, false, false),  // 5
    (7, 7, 1, 0, 4, 0, false, false, true),  // 6
    (5, 5, 2, 6, 2, 0, false, false, true),  // 7
];

const WEIGHTS: [&[u8]; 3] = [
    &[0, 21, 43, 64],
    &[0, 9, 18, 27, 37, 46, 55, 64],
    &[0, 4, 9, 13, 17, 21, 26, 30, 34, 38, 43, 47, 51, 55, 60, 64],
];

/// Little-endian bit reader over a 128-bit block, LSB first, which is how the
/// format numbers its fields.
struct Bits {
    v: u128,
    at: usize,
}

impl Bits {
    fn new(block: &[u8]) -> Bits {
        let mut b = [0u8; 16];
        b.copy_from_slice(&block[..16]);
        Bits {
            v: u128::from_le_bytes(b),
            at: 0,
        }
    }

    fn take(&mut self, n: usize) -> usize {
        if n == 0 {
            return 0;
        }
        let x = ((self.v >> self.at) & ((1u128 << n) - 1)) as usize;
        self.at += n;
        x
    }

    fn bit(&mut self) -> usize {
        self.take(1)
    }
}

/// Expand an N-bit endpoint to 8 bits by moving its MSB to bit 7 and
/// back-filling the low bits with copies of it.
fn expand(v: usize, bits: usize) -> u8 {
    if bits == 0 {
        return 0;
    }
    let x = (v << (8 - bits)) & 0xFF;
    (x | (x >> bits)) as u8
}

fn interpolate(a: u8, b: u8, weight: u8) -> u8 {
    let (a, b, w) = (a as i32, b as i32, weight as i32);
    ((a * (64 - w) + b * w + 32) >> 6) as u8
}

/// Decode one BC7 block into 16 RGBA pixels. Returns false when the block
/// carries the reserved mode 8, which hardware reads as transparent black.
///
/// The endpoint loops index two arrays at once because the format lays its
/// fields out channel-major across endpoints, which is the point of them.
#[allow(clippy::needless_range_loop)]
pub fn decode_block(block: &[u8], out: &mut [u8; 64]) -> bool {
    let mut bits = Bits::new(block);
    let mut mode = 0usize;
    while mode < 8 && bits.bit() == 0 {
        mode += 1;
    }
    if mode >= 8 {
        *out = [0u8; 64];
        return false;
    }
    let (
        rgb_bits,
        a_bits,
        subsets,
        part_bits,
        idx_bits,
        idx2_bits,
        has_rotation,
        has_selection,
        has_pbits,
    ) = MODES[mode];
    let endpoints = subsets * 2;

    let partition = if subsets > 1 { bits.take(part_bits) } else { 0 };
    let rotation = if has_rotation { bits.take(2) } else { 0 };
    let selection = if has_selection { bits.bit() } else { 0 };

    // Endpoints, in the order the format lays them out: R, G, B for every
    // endpoint, then A for every endpoint. They stay raw because the P-bits,
    // which come later in the block, join the endpoint's own precision.
    let mut raw = [[0usize; 4]; 6];
    for ch in 0..3 {
        for e in 0..endpoints {
            raw[e][ch] = bits.take(rgb_bits);
        }
    }
    if a_bits > 0 {
        for e in 0..endpoints {
            raw[e][3] = bits.take(a_bits);
        }
    }
    if has_pbits {
        for v in raw.iter_mut().take(endpoints) {
            for ch in 0..4 {
                v[ch] <<= 1;
            }
        }
        if mode == 1 {
            // One P-bit per subset, shared by that subset's two endpoints and
            // applied to the colour channels only.
            for s in 0..2 {
                let p = bits.bit();
                for e in (s * 2)..(s * 2 + 2) {
                    for ch in 0..3 {
                        raw[e][ch] |= p;
                    }
                }
            }
        } else {
            for e in 0..endpoints {
                let p = bits.bit();
                for ch in 0..4 {
                    raw[e][ch] |= p;
                }
            }
        }
    }
    let precision = if has_pbits { 1 } else { 0 };
    let mut ep = [[0u8; 4]; 6];
    for e in 0..endpoints {
        for ch in 0..3 {
            ep[e][ch] = expand(raw[e][ch], rgb_bits + precision);
        }
        ep[e][3] = if a_bits > 0 {
            expand(raw[e][3], a_bits + precision)
        } else {
            255
        };
    }

    let table: &[[u8; 16]] = match subsets {
        3 => &PARTITIONS_3,
        2 => &PARTITIONS_2,
        _ => &[],
    };
    let weights = WEIGHTS[idx_bits - 2];
    let weights2 = WEIGHTS[if idx2_bits == 2 { 0 } else { 1 }];

    // Two passes because the primary indices are packed ahead of the secondary
    // ones, and the primary width depends on whether the texel is a fix-up.
    let mut primary = [[0u8; 4]; 4];
    for y in 0..4 {
        for x in 0..4 {
            let set = if subsets == 1 {
                if (x | y) == 0 {
                    128
                } else {
                    0
                }
            } else {
                table[partition][y * 4 + x] as usize
            };
            let width = idx_bits - if set & 0x80 != 0 { 1 } else { 0 };
            primary[y][x] = bits.take(width) as u8;
        }
    }

    for y in 0..4 {
        for x in 0..4 {
            let set = (if subsets == 1 {
                if (x | y) == 0 {
                    128
                } else {
                    0
                }
            } else {
                table[partition][y * 4 + x] as usize
            }) & 0x03;
            let e0 = set * 2;
            let i = primary[y][x] as usize;
            let (mut r, mut g, mut b, mut a);
            if idx2_bits == 0 {
                r = interpolate(ep[e0][0], ep[e0 + 1][0], weights[i]);
                g = interpolate(ep[e0][1], ep[e0 + 1][1], weights[i]);
                b = interpolate(ep[e0][2], ep[e0 + 1][2], weights[i]);
                a = interpolate(ep[e0][3], ep[e0 + 1][3], weights[i]);
            } else {
                let width = idx2_bits - if (x | y) == 0 { 1 } else { 0 };
                let i2 = bits.take(width);
                if selection == 0 {
                    r = interpolate(ep[e0][0], ep[e0 + 1][0], weights[i]);
                    g = interpolate(ep[e0][1], ep[e0 + 1][1], weights[i]);
                    b = interpolate(ep[e0][2], ep[e0 + 1][2], weights[i]);
                    a = interpolate(ep[e0][3], ep[e0 + 1][3], weights2[i2]);
                } else {
                    r = interpolate(ep[e0][0], ep[e0 + 1][0], weights2[i2]);
                    g = interpolate(ep[e0][1], ep[e0 + 1][1], weights2[i2]);
                    b = interpolate(ep[e0][2], ep[e0 + 1][2], weights2[i2]);
                    a = interpolate(ep[e0][3], ep[e0 + 1][3], weights[i]);
                }
            }
            // The rotation field says which channel was stored as the scalar.
            match rotation {
                1 => std::mem::swap(&mut a, &mut r),
                2 => std::mem::swap(&mut a, &mut g),
                3 => std::mem::swap(&mut a, &mut b),
                _ => {}
            }
            let at = (y * 4 + x) * 4;
            out[at] = r;
            out[at + 1] = g;
            out[at + 2] = b;
            out[at + 3] = a;
        }
    }
    true
}

/// Which mode a block declares, for the tests and for diagnostics.
pub fn mode_of(block: &[u8]) -> Option<usize> {
    let mut bits = Bits::new(block);
    let mut mode = 0usize;
    while mode < 8 && bits.bit() == 0 {
        mode += 1;
    }
    if mode >= 8 {
        None
    } else {
        Some(mode)
    }
}

// Partition shapes, generated from the reference tables.
const PARTITIONS_2: [[u8; 16]; 64] = [
    [128, 0, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 1, 129], /* 0 */
    [128, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 129], /* 1 */
    [128, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 129], /* 2 */
    [128, 0, 0, 1, 0, 0, 1, 1, 0, 0, 1, 1, 0, 1, 1, 129], /* 3 */
    [128, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 129], /* 4 */
    [128, 0, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 129], /* 5 */
    [128, 0, 0, 1, 0, 0, 1, 1, 0, 1, 1, 1, 1, 1, 1, 129], /* 6 */
    [128, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 1, 0, 1, 1, 129], /* 7 */
    [128, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 129], /* 8 */
    [128, 0, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 129], /* 9 */
    [128, 0, 0, 0, 0, 0, 0, 1, 0, 1, 1, 1, 1, 1, 1, 129], /* 10 */
    [128, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 1, 129], /* 11 */
    [128, 0, 0, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 129], /* 12 */
    [128, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 129], /* 13 */
    [128, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 129], /* 14 */
    [128, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 129], /* 15 */
    [128, 0, 0, 0, 1, 0, 0, 0, 1, 1, 1, 0, 1, 1, 1, 129], /* 16 */
    [128, 1, 129, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0], /* 17 */
    [128, 0, 0, 0, 0, 0, 0, 0, 129, 0, 0, 0, 1, 1, 1, 0], /* 18 */
    [128, 1, 129, 1, 0, 0, 1, 1, 0, 0, 0, 1, 0, 0, 0, 0], /* 19 */
    [128, 0, 129, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0], /* 20 */
    [128, 0, 0, 0, 1, 0, 0, 0, 129, 1, 0, 0, 1, 1, 1, 0], /* 21 */
    [128, 0, 0, 0, 0, 0, 0, 0, 129, 0, 0, 0, 1, 1, 0, 0], /* 22 */
    [128, 1, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 0, 129], /* 23 */
    [128, 0, 129, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0], /* 24 */
    [128, 0, 0, 0, 1, 0, 0, 0, 129, 0, 0, 0, 1, 1, 0, 0], /* 25 */
    [128, 1, 129, 0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1, 0], /* 26 */
    [128, 0, 129, 1, 0, 1, 1, 0, 0, 1, 1, 0, 1, 1, 0, 0], /* 27 */
    [128, 0, 0, 1, 0, 1, 1, 1, 129, 1, 1, 0, 1, 0, 0, 0], /* 28 */
    [128, 0, 0, 0, 1, 1, 1, 1, 129, 1, 1, 1, 0, 0, 0, 0], /* 29 */
    [128, 1, 129, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1, 1, 1, 0], /* 30 */
    [128, 0, 129, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1, 1, 0, 0], /* 31 */
    [128, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 129], /* 32 */
    [128, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 129], /* 33 */
    [128, 1, 0, 1, 1, 0, 129, 0, 0, 1, 0, 1, 1, 0, 1, 0], /* 34 */
    [128, 0, 1, 1, 0, 0, 1, 1, 129, 1, 0, 0, 1, 1, 0, 0], /* 35 */
    [128, 0, 129, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0], /* 36 */
    [128, 1, 0, 1, 0, 1, 0, 1, 129, 0, 1, 0, 1, 0, 1, 0], /* 37 */
    [128, 1, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0, 0, 129], /* 38 */
    [128, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 0, 129], /* 39 */
    [128, 1, 129, 1, 0, 0, 1, 1, 1, 1, 0, 0, 1, 1, 1, 0], /* 40 */
    [128, 0, 0, 1, 0, 0, 1, 1, 129, 1, 0, 0, 1, 0, 0, 0], /* 41 */
    [128, 0, 129, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 1, 0, 0], /* 42 */
    [128, 0, 129, 1, 1, 0, 1, 1, 1, 1, 0, 1, 1, 1, 0, 0], /* 43 */
    [128, 1, 129, 0, 1, 0, 0, 1, 1, 0, 0, 1, 0, 1, 1, 0], /* 44 */
    [128, 0, 1, 1, 1, 1, 0, 0, 1, 1, 0, 0, 0, 0, 1, 129], /* 45 */
    [128, 1, 1, 0, 0, 1, 1, 0, 1, 0, 0, 1, 1, 0, 0, 129], /* 46 */
    [128, 0, 0, 0, 0, 1, 129, 0, 0, 1, 1, 0, 0, 0, 0, 0], /* 47 */
    [128, 1, 0, 0, 1, 1, 129, 0, 0, 1, 0, 0, 0, 0, 0, 0], /* 48 */
    [128, 0, 129, 0, 0, 1, 1, 1, 0, 0, 1, 0, 0, 0, 0, 0], /* 49 */
    [128, 0, 0, 0, 0, 0, 129, 0, 0, 1, 1, 1, 0, 0, 1, 0], /* 50 */
    [128, 0, 0, 0, 0, 1, 0, 0, 129, 1, 1, 0, 0, 1, 0, 0], /* 51 */
    [128, 1, 1, 0, 1, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 129], /* 52 */
    [128, 0, 1, 1, 0, 1, 1, 0, 1, 1, 0, 0, 1, 0, 0, 129], /* 53 */
    [128, 1, 129, 0, 0, 0, 1, 1, 1, 0, 0, 1, 1, 1, 0, 0], /* 54 */
    [128, 0, 129, 1, 1, 0, 0, 1, 1, 1, 0, 0, 0, 1, 1, 0], /* 55 */
    [128, 1, 1, 0, 1, 1, 0, 0, 1, 1, 0, 0, 1, 0, 0, 129], /* 56 */
    [128, 1, 1, 0, 0, 0, 1, 1, 0, 0, 1, 1, 1, 0, 0, 129], /* 57 */
    [128, 1, 1, 1, 1, 1, 1, 0, 1, 0, 0, 0, 0, 0, 0, 129], /* 58 */
    [128, 0, 0, 1, 1, 0, 0, 0, 1, 1, 1, 0, 0, 1, 1, 129], /* 59 */
    [128, 0, 0, 0, 1, 1, 1, 1, 0, 0, 1, 1, 0, 0, 1, 129], /* 60 */
    [128, 0, 129, 1, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0], /* 61 */
    [128, 0, 129, 0, 0, 0, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0], /* 62 */
    [128, 1, 0, 0, 0, 1, 0, 0, 0, 1, 1, 1, 0, 1, 1, 129], /* 63 */
];

const PARTITIONS_3: [[u8; 16]; 64] = [
    [128, 0, 1, 129, 0, 0, 1, 1, 0, 2, 2, 1, 2, 2, 2, 130], /* 0 */
    [128, 0, 0, 129, 0, 0, 1, 1, 130, 2, 1, 1, 2, 2, 2, 1], /* 1 */
    [128, 0, 0, 0, 2, 0, 0, 1, 130, 2, 1, 1, 2, 2, 1, 129], /* 2 */
    [128, 2, 2, 130, 0, 0, 2, 2, 0, 0, 1, 1, 0, 1, 1, 129], /* 3 */
    [128, 0, 0, 0, 0, 0, 0, 0, 129, 1, 2, 2, 1, 1, 2, 130], /* 4 */
    [128, 0, 1, 129, 0, 0, 1, 1, 0, 0, 2, 2, 0, 0, 2, 130], /* 5 */
    [128, 0, 2, 130, 0, 0, 2, 2, 1, 1, 1, 1, 1, 1, 1, 129], /* 6 */
    [128, 0, 1, 1, 0, 0, 1, 1, 130, 2, 1, 1, 2, 2, 1, 129], /* 7 */
    [128, 0, 0, 0, 0, 0, 0, 0, 129, 1, 1, 1, 2, 2, 2, 130], /* 8 */
    [128, 0, 0, 0, 1, 1, 1, 1, 129, 1, 1, 1, 2, 2, 2, 130], /* 9 */
    [128, 0, 0, 0, 1, 1, 129, 1, 2, 2, 2, 2, 2, 2, 2, 130], /* 10 */
    [128, 0, 1, 2, 0, 0, 129, 2, 0, 0, 1, 2, 0, 0, 1, 130], /* 11 */
    [128, 1, 1, 2, 0, 1, 129, 2, 0, 1, 1, 2, 0, 1, 1, 130], /* 12 */
    [128, 1, 2, 2, 0, 129, 2, 2, 0, 1, 2, 2, 0, 1, 2, 130], /* 13 */
    [128, 0, 1, 129, 0, 1, 1, 2, 1, 1, 2, 2, 1, 2, 2, 130], /* 14 */
    [128, 0, 1, 129, 2, 0, 0, 1, 130, 2, 0, 0, 2, 2, 2, 0], /* 15 */
    [128, 0, 0, 129, 0, 0, 1, 1, 0, 1, 1, 2, 1, 1, 2, 130], /* 16 */
    [128, 1, 1, 129, 0, 0, 1, 1, 130, 0, 0, 1, 2, 2, 0, 0], /* 17 */
    [128, 0, 0, 0, 1, 1, 2, 2, 129, 1, 2, 2, 1, 1, 2, 130], /* 18 */
    [128, 0, 2, 130, 0, 0, 2, 2, 0, 0, 2, 2, 1, 1, 1, 129], /* 19 */
    [128, 1, 1, 129, 0, 1, 1, 1, 0, 2, 2, 2, 0, 2, 2, 130], /* 20 */
    [128, 0, 0, 129, 0, 0, 0, 1, 130, 2, 2, 1, 2, 2, 2, 1], /* 21 */
    [128, 0, 0, 0, 0, 0, 129, 1, 0, 1, 2, 2, 0, 1, 2, 130], /* 22 */
    [128, 0, 0, 0, 1, 1, 0, 0, 130, 2, 129, 0, 2, 2, 1, 0], /* 23 */
    [128, 1, 2, 130, 0, 129, 2, 2, 0, 0, 1, 1, 0, 0, 0, 0], /* 24 */
    [128, 0, 1, 2, 0, 0, 1, 2, 129, 1, 2, 2, 2, 2, 2, 130], /* 25 */
    [128, 1, 1, 0, 1, 2, 130, 1, 129, 2, 2, 1, 0, 1, 1, 0], /* 26 */
    [128, 0, 0, 0, 0, 1, 129, 0, 1, 2, 130, 1, 1, 2, 2, 1], /* 27 */
    [128, 0, 2, 2, 1, 1, 0, 2, 129, 1, 0, 2, 0, 0, 2, 130], /* 28 */
    [128, 1, 1, 0, 0, 129, 1, 0, 2, 0, 0, 2, 2, 2, 2, 130], /* 29 */
    [128, 0, 1, 1, 0, 1, 2, 2, 0, 1, 130, 2, 0, 0, 1, 129], /* 30 */
    [128, 0, 0, 0, 2, 0, 0, 0, 130, 2, 1, 1, 2, 2, 2, 129], /* 31 */
    [128, 0, 0, 0, 0, 0, 0, 2, 129, 1, 2, 2, 1, 2, 2, 130], /* 32 */
    [128, 2, 2, 130, 0, 0, 2, 2, 0, 0, 1, 2, 0, 0, 1, 129], /* 33 */
    [128, 0, 1, 129, 0, 0, 1, 2, 0, 0, 2, 2, 0, 2, 2, 130], /* 34 */
    [128, 1, 2, 0, 0, 129, 2, 0, 0, 1, 130, 0, 0, 1, 2, 0], /* 35 */
    [128, 0, 0, 0, 1, 1, 129, 1, 2, 2, 130, 2, 0, 0, 0, 0], /* 36 */
    [128, 1, 2, 0, 1, 2, 0, 1, 130, 0, 129, 2, 0, 1, 2, 0], /* 37 */
    [128, 1, 2, 0, 2, 0, 1, 2, 129, 130, 0, 1, 0, 1, 2, 0], /* 38 */
    [128, 0, 1, 1, 2, 2, 0, 0, 1, 1, 130, 2, 0, 0, 1, 129], /* 39 */
    [128, 0, 1, 1, 1, 1, 130, 2, 2, 2, 0, 0, 0, 0, 1, 129], /* 40 */
    [128, 1, 0, 129, 0, 1, 0, 1, 2, 2, 2, 2, 2, 2, 2, 130], /* 41 */
    [128, 0, 0, 0, 0, 0, 0, 0, 130, 1, 2, 1, 2, 1, 2, 129], /* 42 */
    [128, 0, 2, 2, 1, 129, 2, 2, 0, 0, 2, 2, 1, 1, 2, 130], /* 43 */
    [128, 0, 2, 130, 0, 0, 1, 1, 0, 0, 2, 2, 0, 0, 1, 129], /* 44 */
    [128, 2, 2, 0, 1, 2, 130, 1, 0, 2, 2, 0, 1, 2, 2, 129], /* 45 */
    [128, 1, 0, 1, 2, 2, 130, 2, 2, 2, 2, 2, 0, 1, 0, 129], /* 46 */
    [128, 0, 0, 0, 2, 1, 2, 1, 130, 1, 2, 1, 2, 1, 2, 129], /* 47 */
    [128, 1, 0, 129, 0, 1, 0, 1, 0, 1, 0, 1, 2, 2, 2, 130], /* 48 */
    [128, 2, 2, 130, 0, 1, 1, 1, 0, 2, 2, 2, 0, 1, 1, 129], /* 49 */
    [128, 0, 0, 2, 1, 129, 1, 2, 0, 0, 0, 2, 1, 1, 1, 130], /* 50 */
    [128, 0, 0, 0, 2, 129, 1, 2, 2, 1, 1, 2, 2, 1, 1, 130], /* 51 */
    [128, 2, 2, 2, 0, 129, 1, 1, 0, 1, 1, 1, 0, 2, 2, 130], /* 52 */
    [128, 0, 0, 2, 1, 1, 1, 2, 129, 1, 1, 2, 0, 0, 0, 130], /* 53 */
    [128, 1, 1, 0, 0, 129, 1, 0, 0, 1, 1, 0, 2, 2, 2, 130], /* 54 */
    [128, 0, 0, 0, 0, 0, 0, 0, 2, 1, 129, 2, 2, 1, 1, 130], /* 55 */
    [128, 1, 1, 0, 0, 129, 1, 0, 2, 2, 2, 2, 2, 2, 2, 130], /* 56 */
    [128, 0, 2, 2, 0, 0, 1, 1, 0, 0, 129, 1, 0, 0, 2, 130], /* 57 */
    [128, 0, 2, 2, 1, 1, 2, 2, 129, 1, 2, 2, 0, 0, 2, 130], /* 58 */
    [128, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 129, 1, 130], /* 59 */
    [128, 0, 0, 130, 0, 0, 0, 1, 0, 0, 0, 2, 0, 0, 0, 129], /* 60 */
    [128, 2, 2, 2, 1, 2, 2, 2, 0, 2, 2, 2, 129, 2, 2, 130], /* 61 */
    [128, 1, 0, 129, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 130], /* 62 */
    [128, 1, 1, 129, 2, 0, 1, 1, 130, 2, 0, 1, 2, 2, 2, 0], /* 63 */
];
