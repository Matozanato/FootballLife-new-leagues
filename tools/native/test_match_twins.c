/* fl26match's twins sweep (17.11.2026, notes/twins-pregled-1711.md): TWIN_WIDE, 15 lookups of FL 2027 that
 * hold the whole match id one instruction before and cut it with a movzx for the lookup only.
 *  - on a made-up match table as the GigaPack runs it (first 65536, mask 0xffffffff, cap 131000), a
 *    knockout page's supercup entry (high) whose low word is a league match (the B493 picture: the
 *    Supercopa de Chile page titled "National 1 Groupe A"): the word gets the league, the 32-bit read
 *    the supercup; a source holding a low id (upper half zero) reads as before; the user's match id
 *    0xffff (none) is no match either way
 *  - twin_widen on a fake image: shipped bytes widened, widened bytes kept, other bytes left alone
 *  - no TWIN_WIDE site is a PAGE_WIDE site
 *
 *     zig cc -target x86_64-windows-gnu -O2 -o test_match_twins.exe test_match_twins.c
 *
 * tools/test_match_twins.py builds and runs it.
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

/* what the patched instruction hands the lookup: the shipped one cuts, the new one takes 32 bits */
static uint32_t shipped(uint32_t src) { return src & 0xffff; }
static uint32_t widened(uint32_t src) { return src; }

int main(void)
{
  g_off = 0; g_cap = 131000; g_first = 0x10000; g_mask = 0xffffffffu;
  g_exe = 0;                                   /* no frame of this exe is a listed site */
  blk = (uint8_t*)malloc((size_t)g_cap * REC);
  if (!blk) { printf("no memory\n"); return 2; }
  for (uint32_t i = 0; i < g_cap; i++) kill(i);

  /* 1. the knockout page's header: the group's first entry is the supercup's match (high), its low
        word a league match that lives too */
  const uint32_t L = 2210, H = L + 0x10000;
  const uint16_t LEAGUE = 273, SUPERCUP = 511;
  mk(L, LEAGUE, 0x7ea0801, 301, 302);         /* National 1 Groupe A */
  mk(H, SUPERCUP, 0x7ea071e, 401, 402);       /* Supercopa de Chile */
  uint32_t entry = H;                          /* the filler's dword (0x140cab4da) */
  CHECK(m_lookup(blk, shipped(entry)) == rec(L), "movzx: the low twin (the bug as shipped)");
  CHECK(m_lookup(blk, widened(entry)) == rec(H), "32-bit: the supercup's match");
  printf("header: shipped read -> comp %u, widened read -> comp %u\n",
         *(uint16_t*)(m_lookup(blk, shipped(entry)) + 4), *(uint16_t*)(m_lookup(blk, widened(entry)) + 4));

  /* 2. a source with a low id (an unpatched day list: movzx upstream, upper half zero) reads as before */
  CHECK(m_lookup(blk, widened(L)) == m_lookup(blk, shipped(L)), "low id: the same record both ways");

  /* 3. only the high one live: the cut word finds it (M4), the whole id too */
  const uint32_t L2 = 30000, H2 = L2 + 0x10000;
  mk(H2, SUPERCUP, 0x7ea071e, 403, 404);
  CHECK(m_lookup(blk, shipped(H2)) == rec(H2) && m_lookup(blk, widened(H2)) == rec(H2), "no twin: both find it");

  /* 4. 0x1414c8fd0's "no match today" (0xffff) is no match either way */
  CHECK(m_lookup(blk, shipped(0xffff)) == 0 && m_lookup(blk, widened(0xffff)) == 0, "0xffff: no match");

  /* 5. twin_widen on a fake image: all shipped, but site 1 already widened and site 2 something else */
  uint64_t top = 0;
  for (int i = 0; i < NTWIN; i++) if (TWIN_WIDE[i].va + 8 > top) top = TWIN_WIDE[i].va + 8;
  size_t span = (size_t)(top - EXE_VA);
  uint8_t* img = (uint8_t*)VirtualAlloc(0, span, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE);
  if (!img) { printf("no image memory\n"); return 2; }
  for (int i = 0; i < NTWIN; i++) {
    uint8_t* at = img + (TWIN_WIDE[i].va - EXE_VA);
    for (unsigned k = 0; k < TWIN_WIDE[i].n; k++)
      at[k] = i == 1 ? TWIN_WIDE[i].neu[k] : i == 2 ? (uint8_t)(0x90 + k) : TWIN_WIDE[i].old[k];
  }
  g_exe = (uintptr_t)img;
  twin_widen();
  g_exe = 0;
  int wd = 0;
  for (int i = 0; i < NTWIN; i++) {
    uint8_t* at = img + (TWIN_WIDE[i].va - EXE_VA);
    int want = i == 1 ? 2 : i == 2 ? 0 : 1;
    CHECK(g_twin_st[i] == want, "site %d state %d, want %d", i, g_twin_st[i], want);
    int same_new = 1, same_junk = 1;
    for (unsigned k = 0; k < TWIN_WIDE[i].n; k++) { same_new &= at[k] == TWIN_WIDE[i].neu[k]; same_junk &= at[k] == (uint8_t)(0x90 + k); }
    if (i != 2) CHECK(same_new, "site %d holds the 32-bit read", i);
    else CHECK(same_junk, "site %d left alone", i);
    wd += g_twin_st[i] == 1;
    CHECK(wide_state(TWIN_WIDE[i].old, &TWIN_WIDE[i]) == 1 && wide_state(TWIN_WIDE[i].neu, &TWIN_WIDE[i]) == 2,
          "wide_state of site %d", i);
  }
  printf("twin_widen: %d of %d widened on the fake image (1 already, 1 left alone)\n", wd, NTWIN);

  /* 6. no site twice, none on PAGE_WIDE */
  for (int i = 0; i < NTWIN; i++) {
    for (int j = i + 1; j < NTWIN; j++)
      CHECK(TWIN_WIDE[i].va + TWIN_WIDE[i].n <= TWIN_WIDE[j].va || TWIN_WIDE[j].va + TWIN_WIDE[j].n <= TWIN_WIDE[i].va,
            "sites %d and %d overlap", i, j);
    for (int j = 0; j < NWIDE; j++)
      CHECK(TWIN_WIDE[i].va + TWIN_WIDE[i].n <= PAGE_WIDE[j].va || PAGE_WIDE[j].va + PAGE_WIDE[j].n <= TWIN_WIDE[i].va,
            "site %d overlaps PAGE_WIDE %d", i, j);
  }

  printf("%d checks, %d failed\n", checks, fails);
  return fails ? 1 : 0;
}
