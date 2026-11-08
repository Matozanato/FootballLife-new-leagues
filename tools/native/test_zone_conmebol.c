/* Real zone_access and world loaders, without a running game. */
#define FL26_RCAL_TEST
#define FL26_STATE_TEST
#define FL26_ZONE_TEST
#include "fl26swiss.c"
#include <assert.h>
int rcal_test_today(void) { return 200; }
int rcal_test_invites(int k, uint16_t id) { return 0; }
int rcal_test_recday(uint16_t id) { return -1; }
int state_test_date(void) { return 2027 * 365 + 200; }
uint32_t state_test_user(void) { return 0; }
const char* state_test_path(void) { return ""; }

/* Only the domestic competition lookup is stubbed. Full zone_of() executes,
   including the real league-phase, source and promotion/relegation decisions. */
unsigned char* zone_test_comp(uint16_t reg)
{
  static unsigned char c[0x30c];
  memset(c, 0, sizeof c);
  *(uint16_t*)(c + 0x7c) = *(uint16_t*)(c + 0x7e) = 0xffff;
  *(uint16_t*)(c + 0x30a) = 16;
  return reg == 94 || reg == 777 ? c : NULL;
}

#ifdef FL26_ZONE_WORLD_FIXTURE
#include "zone_world_fixture.h"
static void test_bolivia_world(void)
{
  load_world_fixture();
  const int expected[] = {ZONE_CL,ZONE_CL,ZONE_CL,ZONE_EL,ZONE_EL,ZONE_EL,ZONE_EL};
  unsigned blue = 0, orange = 0;
  for (unsigned i = 0; i < 16; i++) {
    int zone = zone_of(94, i);
    assert(zone == (i < 7 ? expected[i] : -1));
    blue += zone == ZONE_CL; orange += zone == ZONE_EL;
  }
  assert(blue == 3 && orange == 4);
  assert(zone_access(94, 0) == -1); /* F2 cup winner adds no fixed league strip */
  /* Domestic cup, Libertadores groups, Sudamericana groups/KO, first stage,
     F1/F2 and their tie rows never show domestic qualification zones. */
  const uint16_t cups[] = {258, 8, 9, 10, 1033, 263, 1287, 264, 262, 1286, 267, 1291, 268};
  for (unsigned k = 0; k < sizeof cups / sizeof *cups; k++)
    for (unsigned i = 0; i < 16; i++) assert(zone_of(cups[k], i) == -1);
  assert(zone_of(1027, 0) == ZONE_UP && zone_of(1027, 8) == ZONE_PO);
  assert(zone_of(1029, 0) == ZONE_UP && zone_of(UECL_ROW, 8) == ZONE_PO);
  puts("Bolivia built-world records: exactly 3 blue / 4 orange; cup screens clear");

  /* Re-serialize a manually changed distribution through the real loader.
     No association quota, league order or source ID is assumed by production. */
  uint16_t pre[MAX_LPRE * (6 + 4 * LPRE_MAX)], flags[2 * MAX_LPRE], singles[MAX_LPRE];
  unsigned p = 0, nf = 0, ns = 0;
  int count = g_nlpre;
  for (int k = 0; k < count; k++) {
    const lpre_t* l = &g_lpre[k];
    pre[p++] = l->reg; pre[p++] = l->ko; pre[p++] = l->fill;
    pre[p++] = l->days[0]; pre[p++] = l->days[1]; pre[p++] = 2 * l->ties;
    unsigned bits = l->alias | (l->feed8 << 1) | (l->poko << 2);
    if (bits) { flags[2*nf] = l->reg; flags[2*nf+1] = (uint16_t)bits; nf++; }
    if (l->single) singles[ns++] = l->reg;
    for (unsigned j = 0; j < 2u * l->ties; j++) {
      unsigned rank = l->erank[j];
      if (l->ereg[j] == 94 && l->alias && rank == 3) rank = 5;
      if (l->ereg[j] == 94 && lpre_is_suda(l) && rank >= 4 && rank <= 7)
        rank = rank == 7 ? 12 : rank + 4;
      pre[p++] = l->ereg[j]; pre[p++] = (uint16_t)rank;
    }
  }
  assert(fl26_swiss_lpre(pre, count) == count);
  assert(fl26_swiss_lpre_flags(flags, nf) == (int)nf);
  assert(fl26_swiss_lpre_single(singles, ns) == (int)ns);
  for (unsigned i = 0; i < 16; i++) {
    int expected = i == 0 || i == 1 || i == 4 ? ZONE_CL
                 : i == 7 || i == 8 || i == 9 || i == 11 ? ZONE_EL : -1;
    assert(zone_of(94, i) == expected);
  }
  puts("Custom rebuilt distribution: blue 1/2/5, orange 8/9/10/12; old zones removed");
  const uint16_t other_world[] = {777,1,LIB,0};
  fl26_swiss_lpre(NULL, 0); fl26_swiss_ccup(NULL, 0);
  assert(fl26_swiss_access(other_world, 1) == 1);
  for (unsigned i = 0; i < 16; i++) assert(zone_of(94, i) == -1);
  assert(zone_of(777, 0) == ZONE_CL && zone_of(777, 1) == -1);
  puts("Next world: no retained Bolivia zones");
}
#endif

static void load_pre(const uint16_t* pre)
{
  const uint16_t flags[] = {610,1, 611,3}, single[] = {612};
  assert(fl26_swiss_lpre(pre, 3) == 3);
  assert(fl26_swiss_lpre_flags(flags, 2) == 2);
  assert(fl26_swiss_lpre_single(single, 1) == 1);
}

int main(void)
{
  const uint16_t access[] = {60,1,LIB,0, 60,2,LIBQ,0,
    70,1,UCL,0, 70,2,UEL,0, 70,3,UECL,0, 80,1,AFCL,0, 60,0,LIB,0};
  fl26_swiss_access(access, 8);
  assert(zone_access(60,1) == ZONE_CL && zone_access(60,2) == ZONE_CL);
  assert(zone_access(70,1) == ZONE_CL && zone_access(70,2) == ZONE_EL);
  assert(zone_access(70,3) == ZONE_ECL && zone_access(80,1) == ZONE_CL);
  assert(zone_access(60,0) == -1 && zone_access(60,3) == -1);
  /* Real loader records with supported field sizes, not a second zone configuration. */
  uint16_t cup[4 + 64] = {901, 900, 8, 32};
  for (int i = 0; i < 32; i++) { cup[4 + 2*i] = 90; cup[5 + 2*i] = (uint16_t)(i+1); }
  cup[4] = 8; cup[5] = 255; /* existing F3-loser signature */
  cup[6] = 60; cup[7] = 5; /* Suda groups */
  cup[8] = 60; cup[9] = 0; /* cup winner, not a league row */
  assert(fl26_swiss_ccup(cup, 1) == 1);
  uint16_t pre[18 + 2*(6+16+32)];
  const unsigned sizes[] = {6,16,32}, ranks[] = {3,4,6};
  unsigned p = 0;
  for (unsigned k = 0; k < 3; k++) {
    pre[p++] = (uint16_t)(610+k); pre[p++] = k == 2 ? 900 : 0;
    pre[p++] = 1; pre[p++] = 2; pre[p++] = 3; pre[p++] = (uint16_t)sizes[k];
    for (unsigned i = 0; i < sizes[k]; i++) {
      pre[p++] = i ? 90 : 60; pre[p++] = (uint16_t)(i ? i+1 : ranks[k]);
    }
  }
  load_pre(pre);
  assert(zone_access(60,3) == ZONE_CL && zone_access(60,4) == ZONE_CL);
  assert(zone_access(60,5) == ZONE_EL && zone_access(60,6) == ZONE_EL);
  assert(zone_access(60,7) == -1 && zone_access(60,0) == -1);
  pre[7] = 12; load_pre(pre); /* rebuilt world after manual position edit */
  assert(zone_access(60,3) == -1 && zone_access(60,12) == ZONE_CL);
  pre[6] = 777; load_pre(pre); /* added league, no original-country assumption */
  assert(zone_access(60,12) == -1 && zone_access(777,12) == ZONE_CL);
  const uint16_t next_access[] = {70,1,UCL,0};
  fl26_swiss_lpre(NULL, 0); fl26_swiss_ccup(NULL, 0); fl26_swiss_access(next_access, 1);
  assert(zone_access(60,1) == -1 && zone_access(777,12) == -1);
  assert(ZONE_COLOUR[ZONE_CL] == 70 && ZONE_COLOUR[ZONE_EL] == 3);
#ifdef FL26_ZONE_WORLD_FIXTURE
  test_bolivia_world();
#endif
  puts("zone conmebol: all checks passed");
  return 0;
}
