# The player record

Player.bin in a world's `common\etc\pesdb` holds one 312-byte record per player, in the
game's packed format (`tools/pesdb.py` unpacks and packs it). `tools/playeredit.py` reads and
writes every field below; this page is for anyone who wants to write their own tool.

| bytes | what |
|---|---|
| +0x00 | 8 bytes not decoded |
| +0x08 | player id, 32 bits |
| +0x0c to +0x43 | the bit fields below; bits not listed are not decoded |
| +0x44 | four name slots of 0x3d bytes each, UTF-8, zero-padded: full name, name on the shirt, name on screen, printed name |

The fields are little-endian bit fields counted from the first bit of the record (bit 64 is
the lowest bit of the player id at +0x08). To read one: take the whole record as one
little-endian integer, shift right by `bit`, mask `width` bits, add `add`.

| bit | where | width | add | field | values |
|---|---|---|---|---|---|
| 155 | 0x13 bit 3 | 5 |  | Playing Style | 0-31 |
| 216 | 0x1b bit 0 | 7 | +100 | Height (cm) | 100-227 |
| 233 | 0x1d bit 1 | 9 |  | Nationality | 0-511 |
| 250 | 0x1f bit 2 | 6 | +40 | Place Kicking | 40-99 |
| 256 | 0x20 bit 0 | 7 | +30 | Weight (kg) | 30-157 |
| 263 | 0x20 bit 7 | 6 | +40 | Low Pass | 40-99 |
| 269 | 0x21 bit 5 | 6 | +40 | GK Clearing | 40-99 |
| 275 | 0x22 bit 3 | 6 | +40 | Defensive Awareness | 40-99 |
| 281 | 0x23 bit 1 | 6 | +40 | Ball Control | 40-99 |
| 287 | 0x23 bit 7 | 1 |  | Cross Over Turn | 0-1 |
| 288 | 0x24 bit 0 | 6 | +40 | Heading | 40-99 |
| 294 | 0x24 bit 6 | 6 | +40 | Jump | 40-99 |
| 300 | 0x25 bit 4 | 6 | +40 | GK Reach | 40-99 |
| 306 | 0x26 bit 2 | 6 | +40 | Speed | 40-99 |
| 312 | 0x27 bit 0 | 6 | +40 | Ball Winning | 40-99 |
| 318 | 0x27 bit 6 | 2 |  | LB | 0-2 |
| 320 | 0x28 bit 0 | 6 | +40 | GK Reflexes | 40-99 |
| 326 | 0x28 bit 6 | 6 | +40 | GK Awareness | 40-99 |
| 332 | 0x29 bit 4 | 6 | +40 | Curl | 40-99 |
| 338 | 0x2a bit 2 | 6 | +40 | Stamina | 40-99 |
| 344 | 0x2b bit 0 | 6 | +40 | Acceleration | 40-99 |
| 350 | 0x2b bit 6 | 2 |  | GK | 0-2 |
| 352 | 0x2c bit 0 | 6 | +40 | Dribbling | 40-99 |
| 358 | 0x2c bit 6 | 6 | +40 | Kicking Power | 40-99 |
| 364 | 0x2d bit 4 | 6 | +40 | GK Catching | 40-99 |
| 370 | 0x2e bit 2 | 6 | +40 | Offensive Awareness | 40-99 |
| 376 | 0x2f bit 0 | 6 | +40 | Balance | 40-99 |
| 384 | 0x30 bit 0 | 6 | +40 | Aggression | 40-99 |
| 390 | 0x30 bit 6 | 6 | +40 | Physical Contact | 40-99 |
| 396 | 0x31 bit 4 | 6 | +40 | Finishing | 40-99 |
| 402 | 0x32 bit 2 | 6 | +40 | Lofted Pass | 40-99 |
| 408 | 0x33 bit 0 | 6 | +15 | Age | 15-78 |
| 414 | 0x33 bit 6 | 2 |  | DMF | 0-2 |
| 416 | 0x34 bit 0 | 6 | +40 | Tight Possession | 40-99 |
| 434 | 0x36 bit 2 | 4 |  | Registered Position | 0-12, GK CB LB RB DMF CMF LMF RMF AMF LWF RWF SS CF |
| 438 | 0x36 bit 6 | 3 |  | Form | 0-7 |
| 447 | 0x37 bit 7 | 1 |  | Early Cross | 0-1 |
| 454 | 0x38 bit 6 | 2 |  | Weak Foot Usage | 0-3 |
| 456 | 0x39 bit 0 | 2 |  | CMF | 0-2 |
| 458 | 0x39 bit 2 | 2 |  | Injury Resistance | 0-2 |
| 460 | 0x39 bit 4 | 2 |  | RMF | 0-2 |
| 462 | 0x39 bit 6 | 2 |  | Weak Foot Accuracy | 0-3 |
| 464 | 0x3a bit 0 | 2 |  | AMF | 0-2 |
| 466 | 0x3a bit 2 | 2 |  | LMF | 0-2 |
| 468 | 0x3a bit 4 | 2 |  | CB | 0-2 |
| 470 | 0x3a bit 6 | 2 |  | CF | 0-2 |
| 472 | 0x3b bit 0 | 2 |  | LWF | 0-2 |
| 474 | 0x3b bit 2 | 2 |  | RB | 0-2 |
| 476 | 0x3b bit 4 | 2 |  | RWF | 0-2 |
| 478 | 0x3b bit 6 | 2 |  | SS | 0-2 |
| 482 | 0x3c bit 2 | 1 |  | Sombrero | 0-1 |
| 483 | 0x3c bit 3 | 1 |  | Pinpoint Crossing | 0-1 |
| 484 | 0x3c bit 4 | 1 |  | Weighted Pass | 0-1 |
| 485 | 0x3c bit 5 | 1 |  | Flip Flap | 0-1 |
| 486 | 0x3c bit 6 | 1 |  | Fighting Spirit | 0-1 |
| 487 | 0x3c bit 7 | 1 |  | Through Passing | 0-1 |
| 488 | 0x3d bit 0 | 1 |  | Low Lofted Pass | 0-1 |
| 489 | 0x3d bit 1 | 1 |  | Trickster | 0-1 |
| 490 | 0x3d bit 2 | 1 |  | GK Low Punt | 0-1 |
| 491 | 0x3d bit 3 | 1 |  | Gamesmanship | 0-1 |
| 492 | 0x3d bit 4 | 1 |  | Captaincy | 0-1 |
| 493 | 0x3d bit 5 | 1 |  | Outside Curler | 0-1 |
| 494 | 0x3d bit 6 | 1 |  | Dipping Shot | 0-1 |
| 495 | 0x3d bit 7 | 1 |  | Heading (skill) | 0-1 |
| 496 | 0x3e bit 0 | 1 |  | GK High Punt | 0-1 |
| 497 | 0x3e bit 1 | 1 |  | Marseille Turn | 0-1 |
| 499 | 0x3e bit 3 | 1 |  | Rising Shots | 0-1 |
| 500 | 0x3e bit 4 | 1 |  | Step On Skill control | 0-1 |
| 501 | 0x3e bit 5 | 1 |  | Penalty Specialist | 0-1 |
| 502 | 0x3e bit 6 | 1 |  | GK Penalty Saver | 0-1 |
| 503 | 0x3e bit 7 | 1 |  | Interception | 0-1 |
| 504 | 0x3f bit 0 | 1 |  | Man Marking | 0-1 |
| 505 | 0x3f bit 1 | 1 |  | Heel Trick | 0-1 |
| 506 | 0x3f bit 2 | 1 |  | Chip shot control | 0-1 |
| 507 | 0x3f bit 3 | 1 |  | One-touch Pass | 0-1 |
| 510 | 0x3f bit 6 | 1 |  | Incisive Run | 0-1 |
| 511 | 0x3f bit 7 | 1 |  | First-time Shot | 0-1 |
| 512 | 0x40 bit 0 | 1 |  | No Look Pass | 0-1 |
| 513 | 0x40 bit 1 | 1 |  | Knuckle Shot | 0-1 |
| 514 | 0x40 bit 2 | 1 |  | Stronger Foot | 0 right, 1 left |
| 515 | 0x40 bit 3 | 1 |  | Rabona | 0-1 |
| 516 | 0x40 bit 4 | 1 |  | Super-Sub | 0-1 |
| 517 | 0x40 bit 5 | 1 |  | Track Back | 0-1 |
| 518 | 0x40 bit 6 | 1 |  | Long Range Shooting | 0-1 |
| 519 | 0x40 bit 7 | 1 |  | Scissors Feint | 0-1 |
| 520 | 0x41 bit 0 | 1 |  | Long Ranger | 0-1 |
| 521 | 0x41 bit 1 | 1 |  | Long Throw | 0-1 |
| 522 | 0x41 bit 2 | 1 |  | GK Long Throw | 0-1 |
| 523 | 0x41 bit 3 | 1 |  | Double Touch | 0-1 |
| 524 | 0x41 bit 4 | 1 |  | Acrobatic Finishing | 0-1 |
| 525 | 0x41 bit 5 | 1 |  | Scotch Move | 0-1 |
| 526 | 0x41 bit 6 | 1 |  | Speeding Bullet | 0-1 |
| 527 | 0x41 bit 7 | 1 |  | Long Range Drive | 0-1 |
| 528 | 0x42 bit 0 | 1 |  | Cut Behind & Turn | 0-1 |
| 529 | 0x42 bit 1 | 1 |  | Long Ball Expert | 0-1 |
| 530 | 0x42 bit 2 | 1 |  | Acrobatic Clear | 0-1 |
| 531 | 0x42 bit 3 | 1 |  | Mazing Run | 0-1 |

Positions are numbered 0 GK, 1 CB, 2 LB, 3 RB, 4 DMF, 5 CMF, 6 LMF, 7 RMF, 8 AMF, 9 LWF,
10 RWF, 11 SS, 12 CF. A position rating is 0 for none, 1 for can play there, 2 for natural;
the registered position always has 2.

The abilities are stored as value minus 40, six bits each, so 40 to 103 fit and the game uses
40 to 99. Height is stored minus 100, weight minus 30, age minus 15.

## How it was decoded

Every field was matched against the values the game shows for thousands of shipped players:
for each field name, the one bit position whose values agree with the game's for every player.
All 97 fields listed agree for 100% of the players checked. Two fields share the name
"Heading" in the game: the ability (bit 288) and the skill, listed here as "Heading (skill)"
(bit 495).

## PlayerAssignment.bin

16 bytes per row, one row per player per team (club or national team):

| bytes | what |
|---|---|
| +0x00 | unique row id |
| +0x04 | player id |
| +0x08 | team id |
| +0x0c | bits 0-9 shirt number, bits 10-15 squad order, bits 16 and up role flags |

The first eleven of a club's squad order are its starting eleven, placed by the formation in
a fixed order. For the new clubs' default 4-2-3-1: order 0 GK, 1 CB, 2 CB, 3 RB, 4 LB,
5 DMF, 6 DMF, 7 RMF, 8 LMF, 9 AMF, 10 CF (seen on the Game Plan screen, 2026-09-24). The role
flags above bit 16 appear on a handful of shipped players only and are not decoded;
`playeredit.py` leaves them as they are.
