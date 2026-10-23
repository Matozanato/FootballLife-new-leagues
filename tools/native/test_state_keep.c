/* B49: the final tables and cup winners kept at the season's end outlive the game session.

     zig cc -O2 -fno-sanitize=undefined test_state_keep.c -o test_state_keep.exe && test_state_keep.exe

   (tools/test_state_keep.py builds and runs it.) Exit code 1 on any failure.

   fl26swiss.c without the game (FL26_RCAL_TEST) and with the save folder in the temp folder
   (FL26_STATE_TEST): the game's date, the user's club and the file are the test's. The cases:
     - the July teardown of season 1 (1 July 2026) keeps Cyprus's and Bosnia's final tables and a
       cup's winner; they are written to the file;
     - the game is quit (the DLL's memory cleared) and the save of 26 July loaded: the Europe
       places come from the kept tables (from_table, the champion first), not squad strength,
       and so do the August draws; the cup winner too, and a save of a later summer loaded on
       day 216 is not taken for a new career's first summer;
     - the same session plays on to the next teardown (1 July 2027, other tables), then loads the
       26 July 2026 save again (abs_day takes it for days going on): season 1's tables, not the
       later ones left in memory; the 20 July 2027 save then gives 2027's, and a save of 9 July
       2026 (another timeline in abs_day) season 1's again;
     - a career with another club, and a new career built on day 216 of 2025, read nothing;
     - a torn record at the end of the file (a crash while writing) is cut off at the next write;
     - a keep already in the file is not written again;
     - B209: a career built and the game quit before its first August draw is still new after a
       restart (the first-season list is used); a year on it is not, nor another club's career;
       a January league's career keeps its first summer although it kept tables of its own. */
#define FL26_RCAL_TEST
#define FL26_STATE_TEST
#include "fl26swiss.c"
#include <stdio.h>
#include <stdlib.h>

static int g_today_test = 0, g_year_now = 2026;
static uint32_t g_user_test = 0;
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

#define CYP 178
#define BIH 182
#define CUP 300
#define CLUB(i) ((uint32_t)(i) << 14 | 0x1000)
static const uint32_t USER_A = CLUB(9001), USER_B = CLUB(9002);

/* a day of the game: the date the game shows, abs_day told of it as the game's hooks do */
static void go(int year, int day) { g_year_now = year; g_today_test = day; abs_day(); }

/* what the July teardown's keep_final / access_capture write: the table, dated abs_day */
static void keep_table(uint16_t reg, int first, int n)
{
  final_t* f = 0;
  for (int i = 0; i < g_nfinal; i++) if (g_final[i].reg == reg) f = &g_final[i];
  if (!f) f = &g_final[g_nfinal++];
  f->reg = reg; f->n = (uint16_t)n; f->day = abs_day();
  for (int k = 0; k < n; k++) f->club[k] = CLUB(first + k);
}
static void keep_winner(uint16_t reg, uint32_t c)
{
  cupwin_t* w = 0;
  for (int i = 0; i < g_ncupwin; i++) if (g_cupwin[i].reg == reg) w = &g_cupwin[i];
  if (!w) w = &g_cupwin[g_ncupwin++];
  w->reg = reg; w->day = abs_day(); w->club = c;
}
/* the game quit and started again: everything the DLL holds in memory is gone */
static void restart(void)
{
  memset(g_final, 0, sizeof g_final); g_nfinal = 0;
  memset(g_cupwin, 0, sizeof g_cupwin); g_ncupwin = 0;
  g_year_off = 0; g_last_day = -1; g_timeline = 0;
  g_new_career = 0; g_day_ticked = 0; g_first_day = -1;
  g_built_gdate = -1; g_built_stored = 0;
  g_st_off = g_st_day = -0x7fffffff; g_st_user = 0; g_st_busy = 0; g_st_read_back = 0;
}
/* rank 1..n of reg as the access list reads it; 1 when every place came from the kept table and
   is club first + rank - 1 (seed_of would need the game: it is never reached when this holds) */
static int places_from_table(uint16_t reg, int first, int n, int keep)
{
  final_t* f = final_of(reg);
  if (!f) return 0;                                  /* access_club_kept would go to seed_of */
  for (int r = 1; r <= n; r++) {
    int ft = 0;
    final_t* g = final_of(reg);
    if (!(g && g->n >= r && abs_day() >= g->day && abs_day() - g->day < keep)) return 0;
    uint32_t c = access_club_kept(reg, r, &ft, keep);
    if (!ft || c != CLUB(first + r - 1)) return 0;
  }
  return 1;
}
static long file_size(void)
{
  FILE* f = fopen(g_path_test, "rb");
  if (!f) return -1;
  fseek(f, 0, SEEK_END);
  long n = ftell(f);
  fclose(f);
  return n;
}

int main(void)
{
  char tmp[MAX_PATH];
  GetTempPathA(sizeof tmp, tmp);
  snprintf(g_path_test, sizeof g_path_test, "%sfl26swiss-state-test-%lu.bin", tmp, GetCurrentProcessId());
  DeleteFileA(g_path_test);
  printf("state file %s, a record %u bytes\n", g_path_test, (unsigned)sizeof(state_rec_t));

  printf("\nSeason 1 ends: the July teardown keeps the tables (1 July 2026)\n");
  restart();
  g_user_test = USER_A;
  go(2025, 216); go(2025, 300); go(2026, 10); go(2026, 150);
  go(2026, 181);
  keep_table(CYP, 100, 10);                          /* Cyprus: club 100 champion */
  keep_table(BIH, 200, 12);                          /* Bosnia: club 200 champion */
  keep_winner(CUP, CLUB(150));
  state_store();
  expect(file_size() == 8 + 3 * (long)sizeof(state_rec_t), "three keeps written to the save folder's file");
  state_store();
  expect(file_size() == 8 + 3 * (long)sizeof(state_rec_t), "a keep already in the file is not written again");
  expect(places_from_table(CYP, 100, 4, 120), "the same session: Cyprus's places from its kept table");

  printf("\nThe game quit; the save of 26 July 2026 loaded (bythezl19, B49)\n");
  restart();
  go(2026, 207);
  expect(places_from_table(CYP, 100, 4, 120), "Cyprus: places 1-4 from last season's table, not squad strength");
  expect(places_from_table(BIH, 200, 4, 120), "Bosnia: places 1-4 from last season's table");
  expect(any_final_kept(), "a final table kept this summer (the first-season list stays out)");
  {
    cupwin_t* w = cupwin_of(CUP);
    expect(w && cup_winner(CUP) == CLUB(150), "the cup's winner from the file (B51: a super cup of ours)");
  }
  go(2026, 216); expect(places_from_table(CYP, 100, 4, 120), "day 216, the season built: still the kept table");
  go(2026, 246); expect(places_from_table(BIH, 200, 4, 120), "day 246, the August draws: still the kept table");
  go(2026, 300); expect(places_from_table(BIH, 200, 4, CONT_KEEP), "day 300, a cup of ours filled later (CONT_KEEP)");

  printf("\nA save of 4 August 2026 loaded on its own day 216 after a restart: not a new career\n");
  restart();
  go(2026, 216);
  g_new_career = 1;                                  /* date_handler's guess on days 210-240 */
  any_final_kept();
  expect(g_st_read_back == 1, "last season's tables read back: first_summer stays off");

  printf("\nThe session plays on to 1 July 2027 (other tables), then loads 26 July 2026 again\n");
  restart();
  go(2026, 207);
  final_of(CYP);
  go(2026, 300); go(2027, 10); go(2027, 150); go(2027, 181);
  keep_table(CYP, 120, 10);                          /* season 2: club 120 champion */
  keep_table(BIH, 220, 12);
  keep_winner(CUP, CLUB(151));
  state_store();
  expect(places_from_table(CYP, 120, 4, 120), "1 July 2027: season 2's table");
  go(2026, 207);                                     /* a save of a year before, near the same day */
  expect(g_timeline == 0, "abs_day takes that load for 26 days on: only the game's date tells");
  expect(places_from_table(CYP, 100, 4, 120), "26 July 2026 loaded again: season 1's table, not 2027's");
  expect(cup_winner(CUP) == CLUB(150), "... and season 1's cup winner");
  go(2027, 201);                                     /* the 20 July 2027 save */
  expect(places_from_table(BIH, 220, 4, 120), "20 July 2027 loaded: season 2's table");
  expect(cup_winner(CUP) == CLUB(151), "... and season 2's cup winner");
  {
    int tl = g_timeline;
    go(2026, 190);                                   /* 9 July 2026: a day gone back */
    expect(g_timeline == tl + 1, "9 July 2026 loaded: abs_day takes it for another timeline");
  }
  expect(places_from_table(BIH, 200, 4, 120) && cup_winner(CUP) == CLUB(150), "... season 1's table and cup winner");

  printf("\nOther careers read nothing\n");
  restart();
  g_user_test = USER_B;
  go(2026, 207);
  expect(!final_of(CYP) && !cupwin_of(CUP), "another club's career, same world, same day: nothing read back");
  restart();
  g_user_test = USER_A;
  go(2025, 216);
  expect(!final_of(CYP) && !any_final_kept(), "a new career of the same club built on day 216 of 2025: nothing");
  expect(g_st_read_back == 0, "... and its first summer stays on");
  restart();
  go(2026, 170);                                     /* a save of June 2026, before the teardown */
  expect(!final_of(CYP), "a save of June 2026: the July keeps are later, not taken");

  printf("\nA torn record at the end of the file\n");
  {
    long before = file_size();
    FILE* f = fopen(g_path_test, "ab");
    fwrite("torn record", 1, 11, f);
    fclose(f);
    restart();
    go(2026, 207);
    expect(places_from_table(CYP, 100, 4, 120), "the records before it are still read");
    go(2026, 300); go(2027, 10); go(2027, 150); go(2027, 182);
    keep_table(CYP, 130, 10);                        /* a replayed season 2, another champion */
    state_store();
    expect(file_size() == before + (long)sizeof(state_rec_t), "the torn bytes cut off, the new keep written after the last whole record");
    restart();
    go(2027, 201);
    expect(places_from_table(CYP, 130, 4, 120), "the replayed season's table is the newest of 2027");
  }

  printf("\nMore keeps than the old 64 + 32 (a fourth season, 2026-10-21)\n");
  {
    restart();
    DeleteFileA(g_path_test);
    go(2030, 182);
    for (int i = 0; i < 200; i++) keep_table((uint16_t)(400 + i), 1000 + i * 4, 4);
    for (int i = 0; i < 30; i++) keep_winner((uint16_t)(700 + i), CLUB(5000 + i));
    state_store();
    expect(file_size() == 8 + 230L * (long)sizeof(state_rec_t), "all 230 keeps written");
    restart();
    go(2030, 201);
    int all = 1;
    for (int i = 0; i < 200; i++) { final_t* f = final_of((uint16_t)(400 + i)); if (!f || f->club[0] != CLUB(1000 + i * 4)) all = 0; }
    expect(all && g_nfinal == 200, "all 200 tables read back");
    int wins = 1;
    for (int i = 0; i < 30; i++) { cupwin_t* w = cupwin_of((uint16_t)(700 + i)); if (!w || w->club != CLUB(5000 + i)) wins = 0; }
    expect(wins && g_ncupwin == 30, "all 30 cup winners read back");
  }

  printf("\nB209: a career built, the game quit before the August draw (Jabo9, 23.10.)\n");
  {
    restart();
    DeleteFileA(g_path_test);
    g_user_test = USER_A;
    go(2025, 216);
    g_new_career = 1; g_built_gdate = state_test_date(); g_built_stored = 0;   /* date_handler */
    any_final_kept();
    expect(!g_st_read_back, "built on day 216 of 2025: nothing read back");
    state_store();
    expect(g_built_stored && file_size() == 8 + (long)sizeof(state_rec_t), "the career's build date written");
    state_store();
    expect(file_size() == 8 + (long)sizeof(state_rec_t), "... once");
    restart();
    go(2025, 222);
    any_final_kept();
    expect(g_new_career && !g_st_read_back && g_built_gdate == 2025 * 365 + 216,
           "the save of day 222 loaded after a restart: still a new career, first summer on");
    restart();
    go(2026, 216);
    any_final_kept();
    expect(!g_new_career, "a save of the next summer (2026): not a new career");
    restart();
    g_user_test = USER_B;
    go(2025, 222);
    any_final_kept();
    expect(!g_new_career, "another club's career on the same day: not taken for it");

    restart();
    DeleteFileA(g_path_test);
    g_user_test = USER_A;
    go(2026, 0);                                     /* a January league's career (CSL) */
    g_new_career = 1; g_built_gdate = state_test_date(); g_built_stored = 0;
    state_store();
    go(2026, 150); go(2026, 181);
    keep_table(CYP, 100, 10);                        /* its own July teardown */
    state_store();
    restart();
    go(2026, 220);
    any_final_kept();
    expect(g_new_career && !g_st_read_back, "a January career loaded on day 220: first summer on despite its July tables");
    expect(places_from_table(CYP, 100, 4, 120), "... and the tables are read back all the same");
    restart();
    go(2027, 220);
    any_final_kept();
    expect(!g_new_career, "the same career a year on: not new");
  }

  DeleteFileA(g_path_test);
  printf(fails ? "\n%d check(s) FAILED\n" : "\nall checks passed\n", fails);
  return fails ? 1 : 0;
}
