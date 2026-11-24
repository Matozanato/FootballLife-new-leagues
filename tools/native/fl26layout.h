/* fl26layout.h -- where the edit block keeps what our modules read, taken from the game's own
 * code after fl26caps has patched it, so one DLL follows whichever caps set is installed.
 *
 * FL26 (0.3.0 set: teams 2400, regulations 600, players 61905) and the FL27 set of the limits
 * branch (teams 4800, regulations 1200, players 123825) put the same fields at different block
 * offsets: the big set moves the whole span from the calendar's end (0x16705a8) up, the
 * calendar, the regulations and the knockout round table. Every offset below is the
 * displacement or immediate of one instruction fl26caps rewrites (or leaves alone, when the set
 * does not move that field), so reading it gives the offset the game itself uses. The opcode
 * bytes in front are checked first; if they are not there (another exe, or a set that rewrote
 * the instruction differently) the 0.3.0 value is used and lay_ok() says so.
 *
 * Read lazily: fl26caps patches at sider's start, long before a module looks at the block.
 * The including file defines `static uint64_t g_base` (the exe's base) first.
 *
 *   site          instruction (FL26 2.2 and FL27 1.00 alike)        stock     0.3.0      what
 *   0x140aed7b0   movzx r9d, word [rcx+disp32]                     0x1642a1c 0x19115e4  today
 *   0x140aed7b8   add rcx, imm32                                   0x16038a8 0x1877070  calendar
 *   0x140caf678   add rdx, imm32                                   0xd65f64  0x447ed20  round table
 *   0x140ac8fe3   lea rcx, [rsi+disp32]                            0x1798ab0 0x1798ab0  user club
 *   0x140a9ac07   mov ecx, [rcx+disp32]                            0x1787b5c 0x1787b5c  selected comp
 *   0x140b07859   lea r14, [r15+disp32]                            0x16705a8 0x16705a8  club ranking
 *   0x140f3c0b8   mov ebx, [rsi+disp32]                            0x1798b80 0x1798b80  followers base
 *   0x140cd1691   mov ebx, [rdx+disp32]                            0x1798b8c 0x1798b8c  followers total
 *   0x1414b87dd   mov r14d, imm32  (block constructor)             300       600        regulations cap
 *   0x1414bba84   mov esi, imm32                                   2000      8000       fixture rounds cap
 */
#ifndef FL26LAYOUT_H
#define FL26LAYOUT_H

#include <stdint.h>

static int lay_bad = 0;   /* how many sites fell back to the 0.3.0 value */

static uint32_t lay_read(uint32_t rva, const char* op, int oplen, uint32_t fallback)
{
  const unsigned char* p = (const unsigned char*)(uintptr_t)(g_base + rva);
  if (!g_base) return fallback;
  for (int i = 0; i < oplen; i++)
    if (p[i] != (unsigned char)op[i]) { lay_bad++; return fallback; }
  return *(const uint32_t*)(p + oplen);
}

#define LAY_CACHED(name, rva, op, oplen, fb) \
  static uint32_t name(void) { static uint32_t v; if (!v) v = lay_read(rva, op, oplen, fb); return v; }

LAY_CACHED(lay_today,    0x0aed7b0, "\x44\x0f\xb7\x89", 4, 0x19115e4u)
LAY_CACHED(lay_calendar, 0x0aed7b8, "\x48\x81\xc1",     3, 0x1877070u)
LAY_CACHED(lay_rounds,   0x0caf678, "\x48\x81\xc2",     3, 0x447ed20u)
LAY_CACHED(lay_user,     0x0ac8fe3, "\x48\x8d\x8e",     3, 0x1798ab0u)
LAY_CACHED(lay_selcomp,  0x0a9ac07, "\x8b\x89",         2, 0x1787b5cu)
LAY_CACHED(lay_ranking,  0x0b07859, "\x4d\x8d\xb7",     3, 0x16705a8u)
LAY_CACHED(lay_fbase,    0x0f3c0b8, "\x8b\x9e",         2, 0x1798b80u)
LAY_CACHED(lay_fans,     0x0cd1691, "\x8b\x9a",         2, 0x1798b8cu)
LAY_CACHED(lay_regcap,   0x14b87dd, "\x41\xbe",         2, 600u)
LAY_CACHED(lay_fixcap,   0x14bba84, "\xbe",             1, 8000u)

/* Read the original start date, never the mutable current/target dates. */
static uint32_t lay_career_start(void)
{
  static uint32_t offset;
  if (!offset)
    offset=lay_read(0x126979a, "\x8b\x86", 2, 0);
  return offset;
}

/* the calendar's day: 365 days of one size each between the calendar and today */
static uint32_t lay_day_size(void) { return (lay_today() - lay_calendar()) / 365; }

/* a day's match ids: u16, or u32 once the set rewrote the id list to dwords (calelem.py, the
   u32 match ids of the limits branch). The scheduler's append at 0x141350347 tells which:
   `mov word [rbx+rax*2], r12w` (66 44 89 24 43) or `mov dword [rbx+rax*4], r12d` (44 89 24 83). */
static int lay_day_elem(void)
{
  static int v;
  if (!v) {
    const unsigned char* p = (const unsigned char*)(uintptr_t)(g_base + 0x1350347);
    v = g_base && p[0] == 0x44 && p[1] == 0x89 && p[2] == 0x24 && p[3] == 0x83 ? 4 : 2;
  }
  return v;
}
/* the ids a day holds and where its count sits: the 0x94 bytes after the ids are the count
   and the day's events, whatever the set */
static int lay_day_ids(void) { uint32_t s = lay_day_size(); return s > 0x94 ? (int)(s - 0x94) / lay_day_elem() : 0; }
static uint32_t lay_day_count(void) { return (uint32_t)lay_day_ids() * (uint32_t)lay_day_elem(); }
/* id i of a day, 0xffff for an empty slot either way */
static uint32_t lay_day_id(const unsigned char* day, int i)
{
  return lay_day_elem() == 4 ? ((const uint32_t*)day)[i] : ((const uint16_t*)day)[i];
}
static void lay_day_set(unsigned char* day, int i, uint32_t v)
{
  if (lay_day_elem() == 4) ((uint32_t*)day)[i] = v; else ((uint16_t*)day)[i] = (uint16_t)v;
}

/* A club's Master League league slot (team record +0x41c). The game keeps it in the low 7 bits,
   bit 7 being a flag; fl26slot7 moves that flag to +0x41a and widens the slot -- to the whole
   byte (8 bits: its first reader, 0x140b08f74, reads `and cl, 0xff`) or, since B391 (10.11.),
   to 9 bits with the high bit in +0x41b (that reader is then a jmp to its stub, e9 at
   0x140b08f6b). Slots 256..511 of the big worlds need the ninth bit. */
static int lay_slot_bits(void)
{
  const unsigned char* p = (const unsigned char*)(uintptr_t)(g_base + 0xb08f6b);
  return p[0] == 0xe9 ? 9 : p[9] == 0xff ? 8 : 7;
}
static uint32_t lay_slot(const unsigned char* t)
{
  int b = lay_slot_bits();
  if (b == 9) return (t[0x41c] | (uint32_t)t[0x41b] << 8) & 0x1ff;
  return t[0x41c] & (b == 8 ? 0xffu : 0x7fu);
}
static void lay_set_slot(unsigned char* t, uint32_t slot)
{
  int b = lay_slot_bits();
  if (b == 9) { t[0x41c] = (unsigned char)slot; t[0x41b] = (unsigned char)(slot >> 8); }
  else if (b == 8) t[0x41c] = (unsigned char)slot;
  else *(uint32_t*)(t + 0x41c) = (*(uint32_t*)(t + 0x41c) & 0xffffff80u) | slot;
}

static int lay_ok(void)
{
  lay_today(); lay_calendar(); lay_rounds(); lay_user(); lay_selcomp();
  lay_ranking(); lay_fbase(); lay_fans(); lay_regcap();
  return lay_bad == 0;
}

#endif
