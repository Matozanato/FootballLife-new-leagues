/* zig cc -O2 -fno-sanitize=undefined test_chain_cupfit.c -o test_chain_cupfit.exe && test_chain_cupfit.exe
   B278 (D1eg0Ar, Agus 2026-10-29): a domestic cup is only ever given a field the bracket screen
   draws (#74's 2-16, 18, 20, 24, 28, 30, 32). A fake image: the owner global, a block with the
   regulation records, and a setter that keeps what the cup was given. Argentina's league (30)
   with 26 clubs and its Primera Nacional (98) below it, as D1eg0Ar's second season had them. */
#include "fl26chain.c"
#include <stdlib.h>

static unsigned char* blk;
static int n_given = -1; static uint32_t given[2 * MAX_CLUBS];
static char fake_set(uint64_t id, vec32_t* v, uint64_t flag)
{
  (void)id; (void)flag;
  n_given = vcount32(v); memcpy(given, v->b, n_given * sizeof given[0]);
  return 1;
}
static void reg(int slot, uint16_t id, int first, int n)
{
  unsigned char* rec = blk + REG_ARRAY_OFF + (size_t)slot * REG_STRIDE;
  *(uint16_t*)rec = id;
  for (int i = 0; i < n; i++) *(uint32_t*)(rec + 0x170 + i*4) = (uint32_t)(first + i) << 14;
  *(uint32_t*)(rec + 0x170 + n*4) = 0xffffffffu;
}
static int fails = 0;
static void check(const char* what, int got, int want)
{
  if (got != want) { printf("FAIL: %s: %d, not %d\n", what, got, want); fails++; }
  else printf("ok: %s (%d)\n", what, got);
}

int main(void)
{
  unsigned char* img = calloc(1, OWNER_RVA + 0x100);
  unsigned char* owner = calloc(1, 0x100);
  blk = calloc(1, REG_ARRAY_OFF + (size_t)REG_CAP * REG_STRIDE);
  *(unsigned char**)(img + OWNER_RVA) = owner; *(unsigned char**)(owner + 0x48) = blk;
  g_base = (uint64_t)(uintptr_t)img;               /* REG_DISP_RVA holds no cmp: the fallback */
  g_tramp_set = (unsigned char*)(uintptr_t)fake_set;
  for (int s = 0; s < REG_CAP; s++) *(uint16_t*)(blk + REG_ARRAY_OFF + (size_t)s * REG_STRIDE) = 0xffff;
  reg(0, 30, 1, 26); reg(1, 98, 100, 20);

  uint32_t list[2 * MAX_CLUBS]; int n;
  /* the season pass: 24 clubs with some of 98's -- 30's 26 would be 13 ties, the 13th to nowhere */
  cup_t c = { 59, 30, 98, 0, 0, 0 };
  for (n = 0; n < 20; n++) list[n] = (uint32_t)(1 + n) << 14;
  for (; n < 24; n++) list[n] = (uint32_t)(100 + n - 20) << 14;
  n_given = -1; cup_fix(&c, list, n, 0, "test");
  check("24 with 98's clubs -> 30's first 24", n_given, 24);
  check("  and the first club is 30's", n_given > 0 ? (int)(given[0] >> 14) : 0, 1);
  /* the game itself gives the cup 30's 26: not a field the screen draws either */
  for (n = 0; n < 26; n++) list[n] = (uint32_t)(1 + n) << 14;
  n_given = -1; cup_fix(&c, list, n, 0, "test");
  check("30's own 26 -> 24", n_given, 24);
  /* 24 of 30's: left alone */
  n_given = -1; cup_fix(&c, list, 24, 0, "test");
  check("24 of 30's left alone", n_given, -1);
  /* a field above 32 is the League Builder's (cupn, its raised bracket) and is not cut */
  reg(0, 30, 1, 36);
  for (n = 0; n < 34; n++) list[n] = (uint32_t)(1 + n) << 14;
  list[33] = 100u << 14;
  n_given = -1; cup_fix(&c, list, n, 0, "test");
  check("36 above 32 not cut", n_given, 36);
  /* cupall: 14 + 8 = 22 under a cupn of 28 -> 20 */
  reg(0, 30, 1, 14); reg(1, 98, 100, 8);
  cup_t a = { 59, 30, 98, 1, 28, 0 };
  for (n = 0; n < 22; n++) list[n] = (uint32_t)(1 + n) << 14;
  n_given = -1; cup_fix(&a, list, n, 0, "test");
  check("cupall 22 -> 20", n_given, 20);
  /* cupall 16 + 12 = 28: left as it is */
  reg(0, 30, 1, 16); reg(1, 98, 100, 12);
  n_given = -1; cup_fix(&a, list, 22, 0, "test");
  check("cupall 28 kept", n_given, 28);
  for (int k = 2; k <= 48; k++) {
    int f = bracket_fit(k);
    if (f > k || (k <= 32 && k > 16 && f != 18 && f != 20 && f != 24 && f != 28 && f != 30 && f != 32 && f != 16) ||
        (k <= 16 && f != k) || (k > 32 && f != k)) { printf("FAIL: bracket_fit(%d) = %d\n", k, f); fails++; }
  }
  if (fails) return 1;
  printf("all checks passed\n%.*s", g_log_len, g_log);
  return 0;
}
