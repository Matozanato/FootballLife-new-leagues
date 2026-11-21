/* zig cc -O2 -fno-sanitize=undefined test_chain_splittable.c -o test_chain_splittable.exe && test_chain_splittable.exe
   08.11.2026: a split's total the game leaves without a table (groups of different sizes, or three
   groups: Czechia 6+4+6) takes its places from its groups, one after the other. A fake image: the
   standings call answers for the groups only, the season table call for nobody. */
#include "fl26chain.c"
#include <stdlib.h>
static unsigned char* img;
static uint32_t st[1024][MAX_CLUBS]; static int nst[1024];
static void fake_stand(void* ctx, vec16_t* out, uint64_t id, uint64_t from)
{
  (void)ctx; (void)from;
  int n = nst[(uint16_t)id];
  if (!n) return;
  unsigned char* b = calloc(n, 16);
  for (int i = 0; i < n; i++) *(uint32_t*)(b + 16 * i) = st[(uint16_t)id][i];
  out->b = b; out->e = b + 16 * n; out->c = out->e;
}
static unsigned char* fake_input(void* ctx, uint64_t id) { (void)ctx; (void)id; return 0; }
static unsigned char* fake_table(uint64_t id) { (void)id; return 0; }
static void stub(uint32_t rva, void* fn)
{
  unsigned char* p = img + rva;
  p[0] = 0xff; p[1] = 0x25; *(uint32_t*)(p + 2) = 0; *(uint64_t*)(p + 6) = (uint64_t)(uintptr_t)fn;
}
static void group(uint16_t id, int first, int n) { for (int i = 0; i < n; i++) st[id][i] = (uint32_t)(first + i) << 14; nst[id] = n; }
static int fails;
static void check(const char* what, int ok) { printf("%s: %s\n", ok ? "ok" : "FAIL", what); fails += !ok; }
int main(void)
{
  img = VirtualAlloc(0, 0x4000000, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
  g_base = (uint64_t)(uintptr_t)img;
  *(uint32_t*)(img + NOPARENT_RVA) = 0xffffffffu;
  stub(STAND_RVA, fake_stand); stub(INPUT_RVA, fake_input); stub(TABLE_RVA, fake_table);
  uint16_t pairs[4] = { 237, 878, 244, 900 };
  fl26_chain_splits(pairs, 2);
  uint16_t gr[12] = { 237, 879, 880, 881, 244, 901, 902, 0, 999, 1, 2, 3 };
  check("two of three named splits matched (999 is none)", fl26_chain_split_groups(gr, 3) == 2);
  uint32_t out[MAX_CLUBS];
  /* Czechia: championship 6 (clubs 101..106), Conference group 4 (201..204), relegation 6 (301..306) */
  group(879, 101, 6); group(880, 201, 4); group(881, 301, 6);
  int n = standings(0, 237, out);
  int ok = n == 16 && out[0] >> 14 == 101 && out[5] >> 14 == 106 && out[6] >> 14 == 201 && out[10] >> 14 == 301 && out[15] >> 14 == 306;
  check("Czechia: 16 places, the championship group's first, the relegation group's last", ok);
  /* Romania: championship 6, play-out 10 */
  group(901, 401, 6); group(902, 501, 10);
  n = quiet_standings(0, 244, out);
  check("Romania 6+10 through quiet_standings too", n == 16 && out[6] >> 14 == 501 && out[15] >> 14 == 510);
  /* a group without its table: no table at all, the counts stand */
  nst[880] = 0;
  check("a group with no table gives no total", standings(0, 237, out) == 0);
  group(880, 201, 4);
  /* a club in two groups is not a table */
  st[881][0] = 101u << 14 | 7;
  check("a club in two groups gives no total", standings(0, 237, out) == 0);
  /* a league that is not a split's total is left alone */
  check("a league of no split stays without a table", standings(0, 555, out) == 0);
  /* the game's own table first: a total that has one keeps it */
  group(237, 900, 16);
  n = standings(0, 237, out);
  check("a total with the game's table keeps it", n == 16 && out[0] >> 14 == 900);
  printf("%.*s", g_log_len, g_log);
  return fails ? 1 : 0;
}
