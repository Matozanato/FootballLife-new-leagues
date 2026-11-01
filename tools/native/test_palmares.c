/* The trophy cabinet of the Palmarés (fl26swiss.c, "the trophy cabinet"): the records, their lists of
   winners and dates, and the titles the DLL writes where the game does not.

     zig cc -O2 -fno-sanitize=undefined test_palmares.c -o test_palmares.exe && test_palmares.exe

   (tools/test_palmares.py builds and runs it, on Linux and macOS with tools/native/hosttest.) Exit
   code 1 on any failure. fl26swiss.c without the game (FL26_RCAL_TEST, FL26_STATE_TEST): a career
   block of the test's own, the user's club 0x45ed8006. The cases:
     - cab_date: day of the year to month and day (30 -> 31 January, 167 -> 17 June, 364 -> 31 December);
     - a title added to a record the cabinet has: the club and the date on the ends of both lists;
       the same year again is not added; a later year is;
     - a competition the cabinet has not got: a record of its own after the last, with this win
       alone and its own date -- not the dates and winners of the record it is modelled on (the
       "2 Supercopas" of 01.11.);
     - an empty cabinet (the career's first title): the first slot written in place, its four bytes
       past the lists its own;
     - no room left (the records reach the end of the region): -1, nothing written;
     - two records of one competition (two rows "Liga FUTVE 1"): merged into the first, both
       winners and dates on its lists, the records after it moved up one, the empty one too;
     - a record whose winners have no date (an old merge): dated;
     - the palmarés file: listed years made sure of (31 January), a wrong date of an earlier year
       dropped, a competition the cabinet has not got left, and the file renamed to .applied. */
#define FL26_RCAL_TEST
#define FL26_STATE_TEST
#include "fl26swiss.c"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int g_today_test = 0, g_year_now = 2026;
static uint32_t g_user_test = 0x45ed8006u;
static char g_path_test[MAX_PATH + 64];
int rcal_test_today(void) { return g_today_test; }
int rcal_test_invites(int k, uint16_t id) { (void)k; (void)id; return 0; }
int rcal_test_recday(uint16_t id) { (void)id; return -1; }
int state_test_date(void) { return g_year_now * 365 + g_today_test; }
uint32_t state_test_user(void) { return g_user_test; }
const char* state_test_path(void) { return g_path_test; }

static int fails = 0;
static void expect(int ok, const char* what)
{
  printf("  %s  %s\n", ok ? "ok  " : "FAIL", what);
  if (!ok) fails++;
}

#define U 0x45ed8006u
#define OTHER 0x45ec400du
static unsigned char* blk;
static void cab_reset(void)
{
  memset(blk + CAB_HDR, 0xff, CAB_END - CAB_HDR);
  *(uint32_t*)(blk + CAB_HDR) = U;
}
/* a record at slot i: reg, then the given wins (club, date) */
static unsigned char* put(int i, uint16_t reg, int n, const uint32_t* clubs, const uint32_t* dates)
{
  unsigned char* r = cab_rec(blk, i);
  memset(r, 0xff, CAB_RECSZ);
  *(uint16_t*)r = reg; *(uint16_t*)(r + 2) = 0;
  for (int q = 0; q < CAB_N; q++) *(uint32_t*)(r + CAB_DAT + 4 * q) = 0x0000ffffu;
  for (int q = 0; q < n; q++) { *(uint32_t*)(r + 4 + 4 * q) = clubs[q]; *(uint32_t*)(r + CAB_DAT + 4 * q) = dates[q]; }
  r[CAB_RECSZ - 4] = 0x5a;                         /* a byte of the record past the lists: kept by a copy */
  return r;
}
static uint32_t dt(int y, int m, int d) { return (uint32_t)y | (uint32_t)m << 16 | (uint32_t)d << 24; }

int main(void)
{
  blk = (unsigned char*)calloc(1, CAB_END + 0x100000);
  if (!blk) return 2;
  printf("cab_date\n");
  expect(cab_date(2026, 30) == dt(2026, 1, 31), "day 30 is 31 January");
  expect(cab_date(2025, 167) == dt(2025, 6, 17), "day 167 is 17 June");
  expect(cab_date(2027, 364) == dt(2027, 12, 31), "day 364 is 31 December");

  printf("a title on a record the cabinet has\n");
  cab_reset();
  uint32_t c1[] = { U }, d1[] = { dt(2025, 6, 17) };
  put(0, 255, 1, c1, d1);
  put(1, 261, 1, c1, d1);
  expect(cab_count(blk) == 2 && cab_find(blk, 261) == 1, "two records, 261 the second");
  expect(cab_has_year(blk, 261, 2025) && !cab_has_year(blk, 261, 2026), "261 has 2025, not 2026");
  expect(cab_title_add(blk, U, 261, U, dt(2026, 6, 17)) == 2, "261 of 2026 added: 2 titles");
  expect(cab_title_add(blk, U, 261, U, dt(2026, 6, 20)) == 0, "261 of 2026 again: not added");
  expect(rec_wins(cab_rec(blk, 1)) == 2 && *(uint32_t*)(cab_rec(blk, 1) + CAB_DAT + 4) == dt(2026, 6, 17), "its list: 2025, 2026");
  expect(cab_title_add(blk, U, 261, U, dt(2027, 6, 17)) == 3, "261 of 2027 added: 3 titles");

  printf("a competition the cabinet has not got\n");
  uint32_t c3[] = { U, U, U }, d3[] = { dt(2025, 12, 11), dt(2026, 12, 11), dt(2027, 12, 11) };
  put(2, 263, 3, c3, d3);
  expect(cab_title_add(blk, U, 256, U, dt(2026, 1, 31)) == 1, "256 of 2026: a record of its own, 1 title");
  unsigned char* r256 = cab_rec(blk, 3);
  expect(*(uint16_t*)r256 == 256 && rec_wins(r256) == 1, "slot 3 holds 256 with one win");
  expect(*(uint32_t*)(r256 + CAB_DAT) == dt(2026, 1, 31) && *(uint16_t*)(r256 + CAB_DAT + 4) == 0xffff,
         "its one date is 2026, not the model's 2025-2027");
  expect(r256[CAB_RECSZ - 4] == 0x5a, "the bytes past the lists are the model's");
  expect(*(uint16_t*)cab_rec(blk, 4) == 0xffff, "the record after it is empty");
  expect(cab_title_add(blk, U, 256, U, dt(2026, 2, 2)) == 0, "256 of 2026 again (two days later): not added");

  printf("an empty cabinet: the career's first title\n");
  cab_reset();
  cab_rec(blk, 0)[CAB_RECSZ - 4] = 0x33;            /* the slot's own bytes past the lists */
  expect(cab_count(blk) == 0, "no record");
  expect(cab_title_add(blk, U, 261, U, dt(2025, 6, 7)) == 1, "261 of 2025: written, 1 title");
  unsigned char* r0 = cab_rec(blk, 0);
  expect(*(uint16_t*)r0 == 261 && *(uint16_t*)(r0 + 2) == 0 && rec_wins(r0) == 1 && *(uint32_t*)(r0 + 4) == U,
         "slot 0 holds 261, the user's club once");
  expect(*(uint32_t*)(r0 + CAB_DAT) == dt(2025, 6, 7) && *(uint16_t*)(r0 + CAB_DAT + 4) == 0xffff,
         "its one date, the next empty");
  expect(r0[CAB_RECSZ - 4] == 0x33 && *(uint16_t*)cab_rec(blk, 1) == 0xffff, "its own bytes past the lists kept, slot 1 empty");
  expect(cab_title_add(blk, U, 255, U, dt(2025, 8, 1)) == 1 && cab_count(blk) == 2, "a second title: a record after it");

  printf("no room\n");
  cab_reset();
  int nmax = 0;
  while (cab_rec(blk, nmax + 1)) { put(nmax, (uint16_t)(300 + nmax), 1, c1, d1); nmax++; }
  put(nmax, (uint16_t)(300 + nmax), 1, c1, d1); nmax++;
  expect(cab_title_add(blk, U, 999, U, dt(2026, 1, 31)) == -1, "the region full: -1");

  printf("two records of one competition\n");
  cab_reset();
  uint32_t ca[] = { U }, da[] = { dt(2025, 12, 11) }, cb[] = { U }, db[] = { dt(2026, 12, 11) };
  put(0, 261, 1, ca, da);
  put(1, 263, 1, ca, da);
  put(2, 255, 1, ca, da);
  put(3, 263, 1, cb, db);
  put(4, 10, 1, ca, da);
  expect(cab_merge(blk, U, 263) == 1, "263 twice: one merged");
  expect(cab_count(blk) == 4, "4 records left");
  unsigned char* f = cab_rec(blk, 1);
  expect(*(uint16_t*)f == 263 && rec_wins(f) == 2, "263 has 2 wins");
  expect(*(uint32_t*)(f + CAB_DAT) == dt(2025, 12, 11) && *(uint32_t*)(f + CAB_DAT + 4) == dt(2026, 12, 11), "dated 2025 and 2026");
  expect(*(uint16_t*)cab_rec(blk, 3) == 10 && *(uint16_t*)cab_rec(blk, 4) == 0xffff, "10 moved up, the empty one after it");
  expect(cab_merge(blk, U, 263) == 0, "nothing to merge again");

  printf("winners without a date\n");
  f = cab_rec(blk, 1);
  *(uint32_t*)(f + 4 + 8) = U;                       /* a third winner, no date */
  expect(rec_dates_fill(blk, U, f) == 1, "one winner dated");
  expect(rec_wins(f) == 3 && *(uint16_t*)(f + CAB_DAT + 8) == 2027, "the third win is 2027 (the year after the last)");

  printf("the palmarés file\n");
  cab_reset();
  uint32_t cs[] = { U }, ds[] = { dt(2025, 12, 2) };    /* a copy's wrong date */
  put(0, 255, 1, c1, d1);
  put(1, 256, 1, cs, ds);
  snprintf(g_path_test, sizeof g_path_test, "%s/fl26_test_palmares_%d.txt", getenv("TMPDIR") ? getenv("TMPDIR") : "/tmp", (int)getpid());
#ifdef _WIN32
  { const char* t = getenv("TEMP"); snprintf(g_path_test, sizeof g_path_test, "%s\\fl26_test_palmares.txt", t ? t : "."); }
#endif
  FILE* fp = fopen(g_path_test, "w");
  fputs("256 2026 2027 2028\r\n175 2026\r\nnot a line\r\n", fp);
  fclose(fp);
  expect(cab_file_apply(blk, U, g_path_test) == 1, "one line applied (175 has no record)");
  f = cab_rec(blk, 1);
  expect(rec_wins(f) == 3, "256: 3 titles");
  expect(*(uint32_t*)(f + CAB_DAT) == dt(2026, 1, 31) && *(uint32_t*)(f + CAB_DAT + 8) == dt(2028, 1, 31), "2026 .. 2028, 31 January");
  expect(!cab_has_year(blk, 256, 2025), "the wrong 2025 gone");
  char done[MAX_PATH + 96]; snprintf(done, sizeof done, "%s.applied", g_path_test);
  FILE* gone = fopen(g_path_test, "r"); FILE* there = fopen(done, "r");
  expect(!gone && there, "the file renamed to .applied");
  if (gone) fclose(gone);
  if (there) fclose(there);
  remove(done);
  expect(cab_file_apply(blk, U, g_path_test) == 0, "no file: nothing");

  printf(fails ? "%d check(s) FAILED\n" : "all checks passed\n", fails);
  return fails ? 1 : 0;
}
