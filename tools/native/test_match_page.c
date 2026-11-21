/* fl26match's twin choice and the result page's id reads (B465/B470, 16.11.2026), on a made-up match
 * table as FL 2027 runs it with the GigaPack (first 65536, mask 0xffffffff, cap 131000):
 *  - a league match and a cup match with the same low word (the B488 run and morpheus' UEL page:
 *    a played Jan-Dec league match low, the July UEL qualifier high): the page's word read gets the
 *    league, the dword read (PAGE_WIDE) the cup; an entry holding a low id reads as before
 *  - a third twin cannot exist below the cap
 *  - a reader with the competition (m_slotid: the slot's competition and clubs) picks right either way
 *  - a reader without it, a cut word from no listed site, gets the low twin (why the page needs the dword)
 *  - page_widen on a fake image: shipped bytes widened, widened bytes kept, other bytes left alone
 *
 *     zig cc -target x86_64-windows-gnu -O2 -o test_match_page.exe test_match_page.c
 *
 * tools/test_match_page.py builds and runs it.
 */
#include "fl26match.c"
#include <stdlib.h>
#include <stdio.h>

static uint8_t* blk;
static int fails, checks;
#define CHECK(c, ...) do { checks++; if (!(c)) { fails++; printf("FAIL line %d: ", __LINE__); printf(__VA_ARGS__); printf("\n"); } } while (0)

static uint8_t* rec(uint32_t i) { return rec_at(blk, i); }
static void mk(uint32_t id, uint16_t comp, uint32_t leg, uint32_t date, uint32_t c0, uint32_t c1)
{
  uint8_t* r = rec(id);
  *(uint32_t*)r = id;
  *(uint32_t*)(r + 4) = comp | leg << 28;
  *(uint32_t*)(r + 8) = date;
  *(uint32_t*)(r + 0x14) = c0; *(uint32_t*)(r + 0x18) = c1;
}
static void kill(uint32_t id) { *(uint32_t*)rec(id) = 0xffffffffu; }

int main(void)
{
  g_off = 0; g_cap = 131000; g_first = 0x10000; g_mask = 0xffffffffu;
  g_exe = 0;                                   /* no frame of this exe is a listed site */
  blk = (uint8_t*)malloc((size_t)g_cap * REC);
  if (!blk) { printf("no memory\n"); return 2; }
  for (uint32_t i = 0; i < g_cap; i++) kill(i);

  /* 1. same word, a league and a cup: Liga BetPlay I's played match low, UEL Q2's high */
  const uint32_t L = 14428, H = L + 0x10000;
  const uint16_t LEAGUE = 0x1a3, UEL = 0x51;
  mk(L, LEAGUE, 0, 0x7ea0601, 101, 102);      /* Junior FC - Alianza FC, spring */
  mk(H, UEL, 0, 0x7ea0717, 201, 202);         /* a UEL qualifier, July */
  uint32_t entry = H;                          /* the page's entry: the slot reader's whole id */
  CHECK(m_lookup(blk, entry & 0xffff) == rec(L), "word read: the low twin (the bug as shipped)");
  CHECK(m_lookup(blk, entry) == rec(H), "dword read: the cup's match");
  CHECK(*(uint16_t*)(m_lookup(blk, entry) + 4) == UEL, "dword read: the header's competition is the UEL");
  CHECK(m_lookup(blk, L) == rec(L), "an entry with the low id reads as before");
  printf("league+cup: word read -> comp 0x%x, dword read -> comp 0x%x\n",
         *(uint16_t*)(m_lookup(blk, entry & 0xffff) + 4), *(uint16_t*)(m_lookup(blk, entry) + 4));

  /* 2. only the high one live: the word finds it (M4), the dword too */
  const uint32_t L2 = 30000, H2 = L2 + 0x10000;
  mk(H2, UEL, 0, 0x7ea0717, 203, 204);
  CHECK(m_lookup(blk, L2) == rec(H2), "no twin: the word finds the high match");
  CHECK(m_lookup(blk, H2) == rec(H2), "no twin: the dword finds it");

  /* 3. a stale whole id (its high record freed, the low live): as the word read did */
  const uint32_t L3 = 40000;
  mk(L3, LEAGUE, 0, 0x7ea0601, 105, 106);
  CHECK(m_lookup(blk, L3 + 0x10000) == rec(L3), "stale high id: the low record, as before");

  /* 4. three twins: L + 131072 is past the cap for every L, so a word has two candidates at most */
  CHECK(2u * 0x10000u >= g_cap, "cap %u leaves room for a third twin", g_cap);
  CHECK(m_lookup(blk, 0x10000 * 2 + 5) == 0, "an id past the cap is no match");

  /* 5. a reader with the competition: m_slotid picks by the slot's competition and clubs */
  static uint8_t ctxobj[0x50];
  static uint8_t* ctxp;
  *(uint8_t**)(ctxobj + 0x48) = blk; ctxp = ctxobj; g_ctx = &ctxp;
  uint8_t slot[0x20];
  for (int i = 0; i < 0x20; i++) slot[i] = 0;
  *(uint32_t*)slot = 201; *(uint32_t*)(slot + 4) = 202;
  *(uint16_t*)(slot + 8) = (uint16_t)L; *(uint16_t*)(slot + 0xa) = 0xffff; *(uint16_t*)(slot + 0xc) = UEL;
  CHECK(m_slotid(slot, 0) == H, "UEL slot: the high twin (got %u)", m_slotid(slot, 0));
  *(uint32_t*)slot = 101; *(uint32_t*)(slot + 4) = 102; *(uint16_t*)(slot + 0xc) = LEAGUE;
  CHECK(m_slotid(slot, 0) == L, "league slot: the low twin (got %u)", m_slotid(slot, 0));

  /* 6. a reader without it: a cut word from no listed site gets the low twin, also while the
        high one is the current match (that rule needs a listed site or a context function) */
  g_cur = H;
  CHECK(m_lookup(blk, L) == rec(L), "no context: the low twin");
  g_cur = 0xffff;

  /* 7. page_widen on a fake image */
  size_t span = (size_t)(0x140ca2c00ull - EXE_VA);
  uint8_t* img = (uint8_t*)VirtualAlloc(0, span, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE);
  if (!img) { printf("no image memory\n"); return 2; }
  for (int i = 0; i < NWIDE; i++) {
    uint8_t* at = img + (PAGE_WIDE[i].va - EXE_VA);
    for (unsigned k = 0; k < PAGE_WIDE[i].n; k++)
      at[k] = i == 2 ? PAGE_WIDE[i].neu[k] : i == 3 ? (uint8_t)(0x90 + k) : PAGE_WIDE[i].old[k];
  }
  g_exe = (uintptr_t)img;
  page_widen();
  g_exe = 0;
  int want[4] = {1, 1, 2, 0};
  for (int i = 0; i < NWIDE; i++) {
    uint8_t* at = img + (PAGE_WIDE[i].va - EXE_VA);
    CHECK(g_wide_st[i] == want[i], "site %d state %d, want %d", i, g_wide_st[i], want[i]);
    int same_new = 1, same_junk = 1;
    for (unsigned k = 0; k < PAGE_WIDE[i].n; k++) { same_new &= at[k] == PAGE_WIDE[i].neu[k]; same_junk &= at[k] == (uint8_t)(0x90 + k); }
    if (i < 3) CHECK(same_new, "site %d holds the dword read", i);
    else CHECK(same_junk, "site %d left alone", i);
  }
  for (int i = 0; i < NWIDE; i++) CHECK(wide_state(PAGE_WIDE[i].old, &PAGE_WIDE[i]) == 1 && wide_state(PAGE_WIDE[i].neu, &PAGE_WIDE[i]) == 2,
                                        "wide_state of site %d", i);

  printf("%d checks, %d failed\n", checks, fails);
  return fails ? 1 : 0;
}
