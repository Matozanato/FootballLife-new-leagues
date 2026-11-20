/* The standings' zone strip: the colour of every continental place (mato 08.11.2026, a tester's
   Brazil in a modern CONMEBOL world: 1-4 blue, but 5-6 (Libertadores phase 2) and 7-12 (Copa
   Sudamericana) had no colour).

     zig cc -O2 -fno-sanitize=undefined test_zone_colours.c -o test_zone_colours.exe
     test_zone_colours.exe <data file>

   (tools/test_zone_colours.py builds and runs it, with the data file it writes from a world file
   read by fl26swiss.lua's own read_world.) Exit code 1 on any failure.

   fl26swiss.c without the game: the data file gives the loader's buffers in the order the loader
   hands them over -- `access <n> <u16> ...` (fl26_swiss_access), `like <n> ...`
   (fl26_swiss_ccup_like), `ccup <n> ...`
   (fl26_swiss_ccup), `zone <n> ...` (fl26_swiss_ccup_zone), `lpre <n> ...` (fl26_swiss_lpre) --
   then `expect <reg> <position> <zone>` lines (0 blue, 1 orange, 2 teal, -1 none), each checked
   against zone_access, the place half of the strip's zone_of. */
#define FL26_RCAL_TEST
#define FL26_STATE_TEST
#include "fl26swiss.c"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int rcal_test_today(void) { return 150; }
int rcal_test_invites(int k, uint16_t id) { (void)k; (void)id; return 0; }
int rcal_test_recday(uint16_t id) { (void)id; return -1; }
int rcal_test_dayload(int d) { (void)d; return 0; }
int rcal_test_round(uint16_t id) { (void)id; return -1; }
int state_test_date(void) { return 2027 * 365 + 150; }
uint32_t state_test_user(void) { return 0; }
const char* state_test_path(void) { return "zone-test-state.bin"; }

static uint16_t* read_buf(FILE* f, long len)
{
  uint16_t* v = calloc((size_t)(len > 0 ? len : 1), sizeof *v);
  for (long i = 0; i < len; i++) {
    unsigned x = 0;
    if (fscanf(f, "%u", &x) != 1) { fprintf(stderr, "short buffer\n"); exit(2); }
    v[i] = (uint16_t)x;
  }
  return v;
}

int main(int argc, char** argv)
{
  if (argc < 2) { fprintf(stderr, "usage: test_zone_colours <data file>\n"); return 2; }
  FILE* f = fopen(argv[1], "r");
  if (!f) { fprintf(stderr, "cannot open %s\n", argv[1]); return 2; }
  char what[32];
  int fails = 0, checks = 0;
  int per[4] = { 0 };     /* checks per zone: blue, orange, teal, none */
  while (fscanf(f, "%31s", what) == 1) {
    if (!strcmp(what, "expect")) {
      unsigned reg, rank; int want;
      if (fscanf(f, "%u %u %d", &reg, &rank, &want) != 3) return 2;
      int z = zone_access((uint16_t)reg, rank);
      checks++; per[want < 0 ? 3 : want]++;
      if (z != want) {
        fails++;
        printf("  FAIL  reg %u place %u: zone %d, want %d\n", reg, rank, z, want);
      }
      continue;
    }
    long n, len;
    if (fscanf(f, "%ld %ld", &n, &len) != 2) return 2;
    uint16_t* v = read_buf(f, len);
    int k = -9;
    if (!strcmp(what, "access")) { k = fl26_swiss_access(v, (int)n); }
    else if (!strcmp(what, "like")) k = fl26_swiss_ccup_like(v, (int)n);
    else if (!strcmp(what, "ccup")) { k = fl26_swiss_ccup(v, (int)n); }
    else if (!strcmp(what, "zone")) { k = fl26_swiss_ccup_zone(v, (int)n); }
    else if (!strcmp(what, "lpre")) { k = fl26_swiss_lpre(v, (int)n); }
    else { fprintf(stderr, "unknown section %s\n", what); return 2; }
    printf("  %s: %ld given, %d taken\n", what, n, k);
    free(v);
  }
  fclose(f);
  printf("  %d places checked (%d blue, %d orange, %d teal, %d none)\n", checks, per[0], per[1], per[2], per[3]);
  if (fails) { printf("%d check(s) FAILED\n", fails); return 1; }
  printf("all checks passed\n");
  return 0;
}
