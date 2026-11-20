/* The standings' zone strip for a set of groups (B458, 13.11.2026: a tester's Serie C in an FL27
   world -- Girone A showed its promotion place, Girone B and C nothing).

     zig cc -O2 -fno-sanitize=undefined test_group_zones.c -o test_group_zones.exe
     test_group_zones.exe <data file>

   (tools/test_group_zones.py builds and runs it.) fl26swiss.c without the game: the data file
   gives `gzone <n> <3n u16>` (fl26_swiss_gzone's buffer, as fl26swiss.lua packs it from the
   world file's gset lines), then `expect <reg> <row from 0> <clubs> <linked up> <linked down>
   <zone>` lines (3 up, 5 down, -1 none), each checked against zone_group. Exit code 1 on any
   failure. */
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
const char* state_test_path(void) { return "gzone-test-state.bin"; }

int main(int argc, char** argv)
{
  if (argc < 2) { fprintf(stderr, "usage: test_group_zones <data file>\n"); return 2; }
  FILE* f = fopen(argv[1], "r");
  if (!f) { fprintf(stderr, "cannot open %s\n", argv[1]); return 2; }
  if (ZONE_UP != 3 || ZONE_DOWN != 5) { printf("FAIL: zone numbers moved (up %d, down %d)\n", ZONE_UP, ZONE_DOWN); return 1; }
  char what[32];
  int fails = 0, checks = 0, per[3] = { 0 };
  while (fscanf(f, "%31s", what) == 1) {
    if (!strcmp(what, "gzone")) {
      long n;
      if (fscanf(f, "%ld", &n) != 1) return 2;
      uint16_t* v = calloc((size_t)(3 * n + 1), sizeof *v);
      for (long i = 0; i < 3 * n; i++) { unsigned x; if (fscanf(f, "%u", &x) != 1) return 2; v[i] = (uint16_t)x; }
      printf("  gzone: %ld given, %d league(s) taken\n", n, fl26_swiss_gzone(v, (int)n));
      free(v);
    } else if (!strcmp(what, "expect")) {
      unsigned reg, row, n; int lu, ld, want;
      if (fscanf(f, "%u %u %u %d %d %d", &reg, &row, &n, &lu, &ld, &want) != 6) return 2;
      int z = zone_group((uint16_t)reg, row, n, lu, ld);
      checks++; per[want == ZONE_UP ? 0 : want == ZONE_DOWN ? 1 : 2]++;
      if (z != want) { fails++; printf("  FAIL  reg %u row %u of %u (linked %d/%d): zone %d, want %d\n", reg, row, n, lu, ld, z, want); }
    } else { fprintf(stderr, "unknown section %s\n", what); return 2; }
  }
  fclose(f);
  printf("  %d rows checked (%d up, %d down, %d none)\n", checks, per[0], per[1], per[2]);
  if (fails) { printf("%d check(s) FAILED\n", fails); return 1; }
  printf("all checks passed\n");
  return 0;
}
