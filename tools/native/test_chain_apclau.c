/* zig cc -O2 -fno-sanitize=undefined test_chain_apclau.c -o test_chain_apclau.exe && test_chain_apclau.exe
   GitHub #106: an Apertura/Clausura split's standings counted from the played matches of both
   phases. A fake image: the two code sites the walk checks, the owner global and a block with a
   match table; six clubs play a single round in 191 and one in 192. */
#include "fl26chain.c"
#include <stdlib.h>

static unsigned char* img;
static int nmatch;
static void match(uint32_t base, uint16_t reg, int a, int b, int ga, int gb)
{
  unsigned char* blk = *(unsigned char**)(*(unsigned char**)(img + OWNER_RVA) + 0x48);
  unsigned char* m = blk + base + (size_t)nmatch++ * MATCH_STRIDE;
  *(uint16_t*)m = 1; m[7] = 0x40; *(uint16_t*)(m + 4) = reg;
  *(uint32_t*)(m + 0x14) = (uint32_t)a << 14; *(uint32_t*)(m + 0x18) = (uint32_t)b << 14;
  m[0x1c] = (unsigned char)ga; m[0x1f] = (unsigned char)gb;
}

int main(void)
{
  img = calloc(1, OWNER_RVA + 0x100);
  unsigned char* owner = calloc(1, 0x100), * blk = calloc(1, 0x200000);
  *(unsigned char**)(img + OWNER_RVA) = owner; *(unsigned char**)(owner + 0x48) = blk;
  uint32_t base = 0x1000, cap = 1000;
  unsigned char* bs = img + MATCH_BASE_SITE, * cs = img + MATCH_CAP_SITE;
  bs[0] = 0x48; bs[1] = 0x8d; bs[2] = 0x88; *(uint32_t*)(bs + 3) = base;
  cs[0] = 0x81; cs[1] = 0xff; *(uint32_t*)(cs + 2) = cap;
  for (uint32_t i = 0; i < cap; i++) *(uint16_t*)(blk + base + (size_t)i * MATCH_STRIDE) = 0xffff;
  g_base = (uint64_t)(uintptr_t)img;

  uint16_t pairs[2] = { 191, 192 };
  fl26_chain_apclau(pairs, 1);
  uint32_t out[MAX_CLUBS];
  /* club k beats every club above k: 1 wins all, 6 loses all -- in both phases */
  for (int ph = 0; ph < 2; ph++)
    for (int a = 1; a <= 6; a++) for (int b = a + 1; b <= 6; b++) match(base, ph ? 192 : 191, a, b, 2, 0);
  /* a match of another league and an unplayed one count for nothing */
  match(base, 11, 6, 1, 9, 0);
  int n = apclau_table(191, out);
  int ok = n == 6;
  for (int k = 0; k < n && ok; k++) ok = out[k] >> 14 == (uint32_t)(k + 1);
  if (!ok) { printf("FAIL: %d clubs, first %u\n", n, n ? out[0] >> 14 : 0); return 1; }
  /* half a season (the Apertura only) is not a final table */
  nmatch = 0;
  for (uint32_t i = 0; i < cap; i++) *(uint16_t*)(blk + base + (size_t)i * MATCH_STRIDE) = 0xffff;
  for (int a = 1; a <= 6; a++) for (int b = a + 1; b <= 6; b++) match(base, 191, a, b, 1, 0);
  if (apclau_table(191, out) != 0) { printf("FAIL: half a season gave a table\n"); return 1; }
  /* a split that is not Apertura/Clausura is left alone */
  if (apclau_table(193, out) != 0) { printf("FAIL: 193 has no pair\n"); return 1; }
  printf("ok\n%.*s", g_log_len, g_log);
  return 0;
}
