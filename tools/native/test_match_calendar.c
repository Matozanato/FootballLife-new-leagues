/* fl26match's Calendrier -> matchday page choice (B470/B465, 17.11.2026), on a made-up match table as
 * FL 2027 runs it with the GigaPack (first 65536, mask 0xffffffff, cap 131000), and a fake exe image
 * whose PICK sites hold the shipped bytes, so m_lookup is reached through the real return addresses:
 *   stub -> call at ret-5 -> the wrapper (a jmp to m_lookup) -> back to ret
 * Checked:
 *  - before any Calendrier pick the page's lookups answer the low twin, as shipped (the bug)
 *  - the Calendrier's lookup of a day's word whose high twin is the user's club's match answers the high
 *    one and remembers it; the page's four lookups of that word then answer it too
 *  - another word at the page, and the same word from a site not listed, answer as before
 *  - a pick whose low twin is the user's keeps the low one; both twins the user's = unclear, as before
 *  - pick_check: a site whose bytes differ is left off and answers as before
 *  - with mask 0xffff (FL26 / M1) the twin rules are never reached
 *
 *     zig cc -target x86_64-windows-gnu -O2 -o test_match_calendar.exe test_match_calendar.c
 *
 * tools/test_match_calendar.py builds and runs it.
 */
#include "fl26match.c"
#include <stdlib.h>
#include <stdio.h>

static uint8_t* blk;
static int fails, checks;
#define CHECK(c, ...) do { checks++; if (!(c)) { fails++; printf("FAIL line %d: ", __LINE__); printf(__VA_ARGS__); printf("\n"); } } while (0)

static uint8_t* rec(uint32_t i) { return rec_at(blk, i); }
static void mk(uint32_t id, uint16_t comp, uint32_t date, uint32_t c0, uint32_t c1)
{
  uint8_t* r = rec(id);
  *(uint32_t*)r = id;
  *(uint32_t*)(r + 4) = comp;
  *(uint32_t*)(r + 8) = date;
  *(uint32_t*)(r + 0x14) = c0; *(uint32_t*)(r + 0x18) = c1;
}
static void kill(uint32_t id) { *(uint32_t*)rec(id) = 0xffffffffu; }

static uint8_t* img;                           /* the fake exe: g_exe */
static uint8_t* va(uint64_t v) { return img + (v - EXE_VA); }
static int hexput(uint8_t* at, const char* hex)
{
  int n = 0;
  for (; hex[0] && hex[1]; hex += 2, n++) {
    int hi = hex[0] <= '9' ? hex[0] - '0' : hex[0] - 'a' + 10, lo = hex[1] <= '9' ? hex[1] - '0' : hex[1] - 'a' + 10;
    at[n] = (uint8_t)(hi << 4 | lo);
  }
  return n;
}
/* a site i: the shipped read and call (to the wrapper) before PICK[i].ret, `ret` at it, and a stub that
 * calls ret-5 (so m_lookup's frames are ret, the stub, this test: as in the game, ret is the caller) */
typedef uint8_t* (__attribute__((ms_abi)) *drv_t)(uint8_t* b, uint32_t id);
static drv_t drv[NPICK];
static void build_site(int i)
{
  uint8_t* at = va(PICK[i].at);
  int n = hexput(at, PICK[i].hex);
  uint8_t* call = va(PICK[i].ret) - 5;
  CHECK(at + n == call + 1, "site %d: the call opcode is the last byte of the pattern", i);
  *(int32_t*)(call + 1) = (int32_t)((intptr_t)va(WRAP_VA) - (intptr_t)(call + 5));
  *va(PICK[i].ret) = 0xc3;
  uint8_t* stub = img + 0x100 + 0x10 * i;
  stub[0] = 0xe8; *(int32_t*)(stub + 1) = (int32_t)((intptr_t)call - (intptr_t)(stub + 5)); stub[5] = 0xc3;
  drv[i] = (drv_t)(void*)stub;
}
static uint8_t* from(int i, uint32_t id) { return drv[i](blk, id); }
#define CAL 0                                   /* PICK[0]: the Calendrier */

int main(void)
{
  g_off = 0x100; g_cap = 131000; g_first = 0x10000; g_mask = 0xffffffffu;
  g_user_off = 0x10;                            /* the user's club at blk + 0x10 */
  blk = (uint8_t*)malloc((size_t)g_off + (size_t)g_cap * REC);
  if (!blk) { printf("no memory\n"); return 2; }
  for (uint32_t i = 0; i < g_cap; i++) kill(i);
  const uint32_t CLUB = 360;                    /* Wrexham */
  *(uint32_t*)(blk + g_user_off) = CLUB;

  /* the fake image, up to the wrapper 0x1414bb280: a jmp to m_lookup there */
  size_t span = (size_t)(WRAP_VA - EXE_VA) + 0x40;
  img = (uint8_t*)VirtualAlloc(0, span, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
  if (!img) { printf("no image memory\n"); return 2; }
  uint8_t* w = va(WRAP_VA);
  w[0] = 0x48; w[1] = 0xb8; *(uint64_t*)(w + 2) = (uint64_t)(uintptr_t)(void*)m_lookup; w[10] = 0xff; w[11] = 0xe0;
  for (int i = 0; i < NPICK; i++) build_site(i);
  g_exe = (uintptr_t)img;
  CHECK(pick_check() == NPICK, "all %d sites on with the shipped bytes", NPICK);
  g_pick_on = NPICK;

  /* EFL Championship J22 13.01.2027 Wolves-Wrexham high, Tercera Division A J22 (comp 325) low:
     the twinlog of 17.11. (id 3818, low comp 325 clubs 1906-1900, high comp 79 clubs 359-360) */
  const uint32_t L = 3818, H = L + 0x10000;
  mk(L, 325, 0x07eb0516, 1906, 1900);
  mk(H, 79, 0x07eb010d, 359, CLUB);
  /* Matchday 1 31.08.2026: low China League One (251), high EFL (id 3566) */
  const uint32_t L1 = 3566, H1 = L1 + 0x10000;
  mk(L1, 251, 0x07eb041e, 1775, 1771);
  mk(H1, 79, 0x07ea081f, CLUB, 356);
  /* a word whose twins are other clubs' matches */
  const uint32_t L2 = 5000, H2 = L2 + 0x10000;
  mk(L2, 325, 0x07eb0516, 1901, 1902);
  mk(H2, 251, 0x07eb0516, 1771, 1772);

  /* 1. no pick yet: the page answers the low twin, as shipped */
  for (int i = 1; i < NPICK; i++) CHECK(from(i, L) == rec(L), "page site %d before a pick: the low twin", i);
  CHECK(g_page_none == NPICK - 1, "without a pick %d", (int)g_page_none);
  printf("before the fix's pick: page reads comp %u (Tercera Division A), the user's match is comp %u\n",
         *(uint16_t*)(from(1, L) + 4), *(uint16_t*)(rec(H) + 4));

  /* 2. cross on 13.01. in the Calendrier: the user's twin, remembered */
  CHECK(from(CAL, L) == rec(H), "Calendrier: the user's club's twin");
  CHECK(g_pick == H, "pick %u, want %u", g_pick, H);
  for (int i = 1; i < NPICK; i++) CHECK(from(i, L) == rec(H), "page site %d: the picked twin", i);
  CHECK(g_page_hi == NPICK - 1, "page took the pick %d", (int)g_page_hi);
  printf("after the pick: page reads comp %u (EFL Championship)\n", *(uint16_t*)(from(1, L) + 4));

  /* 3. another word at the page: as before (low); the same word from a site not listed: as before */
  CHECK(from(1, L2) == rec(L2), "another word at the page: the low twin, as before");
  CHECK(m_lookup(blk, L) == rec(L), "the word from no listed site: the low twin, as before");
  CHECK(m_lookup(blk, H) == rec(H), "the whole id: itself");

  /* 4. the next pick replaces it: Matchday 1 */
  CHECK(from(CAL, L1) == rec(H1), "Calendrier 31.08.: the user's twin");
  CHECK(from(2, L1) == rec(H1) && from(3, L1) == rec(H1), "page Matchday 1: EFL");
  CHECK(from(2, L) == rec(L), "the earlier word is no longer the pick: as before");

  /* 5. the low twin is the user's: kept low, and the page keeps it */
  const uint32_t L3 = 7000, H3 = L3 + 0x10000;
  mk(L3, 79, 0x07eb0120, CLUB, 351);
  mk(H3, 325, 0x07eb0120, 1903, 1904);
  CHECK(from(CAL, L3) == rec(L3), "Calendrier, low twin the user's: low");
  CHECK(g_pick == L3 && g_pick_lo == 1, "pick %u lo %d", g_pick, (int)g_pick_lo);
  CHECK(from(4, L3) == rec(L3), "page: the low twin, the pick");

  /* 6. both twins the user's (league and cup): unclear, as before, and no pick */
  const uint32_t L4 = 8000, H4 = L4 + 0x10000;
  mk(L4, 79, 0x07eb0120, CLUB, 351);
  mk(H4, 91, 0x07eb0127, 352, CLUB);
  CHECK(from(CAL, L4) == rec(L4), "both the user's: the low twin, as before");
  CHECK(g_pick == 0xffffffffu && g_pick_amb == 1, "no pick after an unclear one");
  CHECK(from(1, L4) == rec(L4), "page after an unclear pick: as before");

  /* 7. only one twin live: no rule needed, the word finds it */
  kill(L1);
  CHECK(from(CAL, L1) == rec(H1), "only the high live: found by the word");

  /* 8. pick_check: a site whose bytes differ is off and answers as before */
  uint8_t keep = *va(PICK[2].at);
  *va(PICK[2].at) = 0x90;
  CHECK(pick_check() == NPICK - 1 && g_pick_ret[2] == 0, "a changed site is left off");
  CHECK(from(CAL, L) == rec(H), "pick again");
  CHECK(from(2, L) == rec(L), "the site left off: as before");
  CHECK(from(1, L) == rec(H), "the other sites still on");
  *va(PICK[2].at) = keep;
  int32_t rel = *(int32_t*)(va(PICK[3].ret) - 4);
  *(int32_t*)(va(PICK[3].ret) - 4) = rel + 0x10;   /* a call to elsewhere */
  CHECK(pick_check() == NPICK - 1 && g_pick_ret[3] == 0, "a call not to the wrapper is left off");
  *(int32_t*)(va(PICK[3].ret) - 4) = rel;
  CHECK(pick_check() == NPICK, "all on again");

  /* 9. mask 0xffff (FL26, M1): the twin rules are never reached */
  g_mask = 0xffff;
  CHECK(from(CAL, L) == rec(L) && from(1, L) == rec(L), "mask 0xffff: the word's own record");
  g_mask = 0xffffffffu;

  printf("%d checks, %d failed\n", checks, fails);
  return fails ? 1 : 0;
}
