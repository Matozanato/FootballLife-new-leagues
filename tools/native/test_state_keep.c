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
       a January league's career keeps its first summer although it kept tables of its own;
     - B240: a league's squad-strength order worked out on day 0 is the one a save of day 30
       loaded after a restart sees (not worked out again from changed squads); not another
       club's career, and nothing is written before the career has a club. */
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
int rcal_test_dayload(int d) { (void)d; return 0; }      /* B329: no day load, no league rounds */
int rcal_test_round(uint16_t id) { (void)id; return 0; }
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
  memset(g_seed, 0, sizeof g_seed); g_nseed = 0;
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

/* Read a preserved Pantoja journal without writing to it. The start date
 * supplied here simulates the original date read from the loaded ML block. */
static int replay_pantoja(const char* journal)
{
  if (snprintf(g_path_test,sizeof g_path_test,"%s",journal)>=(int)sizeof g_path_test)
    return 1;
  g_user_test=0x477401ffu;
  g_state_test_creation=0x010107eau;
  g_car_enabled=1;
  go(2029,196);
  state_sync();
  career_mark("reload date builder");
  expect(g_built_any==2026*365 && !g_new_career,"July 2029 reload keeps January 2026 creation");
  expect(!final_of(CAR_GROUP_SNAPSHOT) ||
         !car_draw_current(game_date()-(abs_day()-final_of(CAR_GROUP_SNAPSHOT)->day),game_date()),
         "the later July draw is invisible from the older checkpoint");
  go(2029,CAR_FILL);
  const uint16_t regs[]={220,326,331,463,488};
  car_config cfg={.n=5};
  cq_source pools[CAR_SOURCES]={{0}};
  for (int i=0;i<5;i++) {
    cfg.sources[i].quota=i<3 ? 2 : 1;
    final_t* f=final_of(CAR_DOMESTIC(regs[i]));
    if (!f || !cq_result_fresh(game_date()-(abs_day()-f->day),game_date(),game_date())) return 1;
    pools[i].n=f->n;
    memcpy(pools[i].club,f->club,f->n*sizeof f->club[0]);
  }
  uint32_t field[10];
  expect(car_select(&cfg,pools,field) && cq_unique(field,10),"ten places from completed domestic rankings");
  expect((field[2]>>14)==73167 && (field[3]>>14)==73172,
         "Dominican places go to 73167 and 73172");
  return fails!=0;
}

int main(int argc, char** argv)
{
  if (argc==2) return replay_pantoja(argv[1]);
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
    expect(g_built_any == 2026 * 365, "career creation survives the sporting journal age limit");
    career_mark("reload date builder");
    expect(!g_new_career && g_built_any == 2026 * 365,
           "a reload date-builder call cannot replace a known creation marker");

    /* B289: loaded past its first summer, but within BUILT_SUMMER days of the build */
    restart();
    go(2026, 255);
    any_final_kept();
    expect(g_new_career && !first_summer_over(), "B289: loaded on day 255, the league phases just drawn: still its first summer");
    go(2026, 364); go(2027, 0); go(2027, 181); go(2027, 226);
    expect(first_summer_over(), "B289: ... played on to the next summer: the first one is over");
    restart();
    DeleteFileA(g_path_test);
    g_user_test = USER_A;
    go(2026, 182);                                   /* an August-May career, built in July */
    g_new_career = 1; g_built_gdate = state_test_date(); g_built_stored = 0;
    state_store();
    restart();
    go(2026, 320);
    any_final_kept();
    expect(!g_new_career, "B289: a July career loaded on day 320, its league phases played: not new");
  }

  printf("\nB240: a first season's squad-strength order outlives the session (antonimus, 25.10.)\n");
  {
    restart();
    DeleteFileA(g_path_test);
    g_user_test = USER_A;
    go(2026, 0);
    final_t* f = &g_seed[g_nseed++];
    f->reg = 61; f->n = 4; f->day = abs_day();
    for (int k = 0; k < 4; k++) f->club[k] = CLUB(600 + k);
    state_store();
    expect(file_size() == 8 + (long)sizeof(state_rec_t), "day 0: Ecuador's order written");
    state_store();
    expect(file_size() == 8 + (long)sizeof(state_rec_t), "... once");
    restart();
    go(2026, 30);
    state_sync();
    final_t* s = 0;
    for (int i = 0; i < g_nseed; i++) if (g_seed[i].reg == 61) s = &g_seed[i];
    expect(s && s->n == 4 && s->club[0] == CLUB(600) && s->club[1] == CLUB(601) && s->club[3] == CLUB(603),
           "the save of day 30 loaded after a restart: the day-0 order, not worked out again");
    expect(s && abs_day() - s->day == 30, "... dated day 0, inside seed_of's summer (120 days)");
    expect(!g_nfinal && !g_ncupwin && !g_st_read_back, "... and no final table or cup winner made of it");
    restart();
    g_user_test = USER_B;
    go(2026, 30);
    state_sync();
    expect(!g_nseed, "another club's career: not read back");
    restart();
    DeleteFileA(g_path_test);
    g_user_test = 0;
    go(2026, 0);
    f = &g_seed[g_nseed++];
    f->reg = 61; f->n = 4; f->day = abs_day();
    for (int k = 0; k < 4; k++) f->club[k] = CLUB(600 + k);
    state_store();
    expect(file_size() <= 8, "no club yet: nothing written");
  }

  printf("\n2026-11-05: a record naming clubs this world has no team for is not read back (FL27 limits)\n");
  {
    /* rows 0x1000-0x1003 hold clubs 600-603 (600 at the row its value names, 601-603 at rows of
       their own, which canon_club finds); club 700 is in no row: another world's id */
    uint32_t nt = 0x1004;
    unsigned char* arr = calloc(nt, TEAM_STRIDE);
    *(uint32_t*)(arr + 0x1000 * TEAM_STRIDE) = CLUB(600);
    for (uint32_t k = 1; k < 4; k++) *(uint32_t*)(arr + (size_t)(0x1000 + k) * TEAM_STRIDE) = (600 + k) << 14 | (0x1000 + k);
    restart();
    DeleteFileA(g_path_test);
    g_user_test = USER_A;
    go(2026, 0);
    final_t* f = &g_seed[g_nseed++];
    f->reg = 61; f->n = 4; f->day = abs_day();
    for (int k = 0; k < 4; k++) f->club[k] = CLUB(600 + k);
    f = &g_seed[g_nseed++];
    f->reg = 62; f->n = 2; f->day = abs_day();
    f->club[0] = CLUB(600); f->club[1] = CLUB(700);
    state_store();
    restart();
    go(2026, 30);
    g_test_teams = arr; g_test_nteams = nt;
    state_sync();
    final_t *s61 = 0, *s62 = 0;
    for (int i = 0; i < g_nseed; i++) {
      if (g_seed[i].reg == 61) s61 = &g_seed[i];
      if (g_seed[i].reg == 62) s62 = &g_seed[i];
    }
    expect(s61 && s61->n == 4, "an order whose clubs all have a team (601-603 at rows of their own): read back");
    expect(!s62, "an order with club 700, which no team record answers for: left out");
    restart();
    go(2026, 30);
    g_test_teams = 0;
    state_sync();
    s62 = 0;
    for (int i = 0; i < g_nseed; i++) if (g_seed[i].reg == 62) s62 = &g_seed[i];
    expect(s62 != 0, "no team array to look at: taken as before");
    free(arr);
  }

  printf("\nA January career which never qualified reloads before Round One\n");
  restart();
  DeleteFileA(g_path_test);
  g_user_test = USER_A;
  go(2026, 0);
  g_new_career = 1;
  g_built_gdate = game_date();
  state_store();
  restart();
  go(2026, 2);
  final_t* previous = final_of(CQ_SNAPSHOT);
  expect(!previous && cq_first_edition(g_built_any, cq_edition_fill(game_date(), CQ_JANUARY_FILL)),
         "the persisted January build date allows qualification for its first February");
  restart();
  DeleteFileA(g_path_test);
  go(2026, 181);
  g_new_career = 1;
  g_built_gdate = game_date();
  state_store();
  restart();
  go(2027, 1);
  state_sync();
  expect(cq_first_edition(g_built_any,cq_edition_fill(game_date(),CQ_JANUARY_FILL)),
         "the persisted July build date allows the following January's first edition");

  printf("\nCONCACAF qualification results keep completion dates across seasons\n");
  restart();
  DeleteFileA(g_path_test);
  g_user_test = USER_A;
  go(2025, 364);
  keep_table(CQ_RESULT(51), 500, 30);
  state_store();
  restart();
  go(2026, 350);
  keep_table(CQ_RESULT(52), 530, 30);
  keep_winner(CQ_RESULT(54), CLUB(500));
  state_store();
  restart();
  go(2027, 1);
  int gd = game_date(), fill = cq_edition_fill(gd, CQ_JANUARY_FILL), now = abs_day();
  final_t* ranking = final_of(CQ_RESULT(51));
  final_t* december = final_of(CQ_RESULT(52));
  cupwin_t* winner = cupwin_of(CQ_RESULT(54));
  expect(!ranking || !cq_result_fresh(gd-(now-ranking->day),fill,gd),
         "a result from two calendar years ago cannot qualify clubs again");
  expect(winner && cq_result_fresh(gd-(now-winner->day),fill,gd),
         "a completed December result is fresh the following January after reload");
  expect(december && december->club[0]==CLUB(530) &&
         cq_result_fresh(gd-(now-december->day),fill,gd),
         "the completed December league ranking reloads for January qualification");

  printf("\nCONCACAF qualification snapshot across reload and July\n");
  restart();
  DeleteFileA(g_path_test);
  g_user_test = USER_A;
  go(2027, 1);
  keep_table(CQ_SNAPSHOT, 500, 27);
  state_store();
  restart();
  go(2027, 40);
  final_t* edition = final_of(CQ_SNAPSHOT);
  expect(edition && cq_snapshot_valid(edition->club, edition->n,
         game_date()-(abs_day()-edition->day), game_date(), cq_edition_fill(game_date(),CQ_JANUARY_FILL),33),
         "all 27 qualifiers are retained after a restart into Round One");
  expect(edition && edition->club[0] == CLUB(500) && edition->club[26] == CLUB(526),
         "the five-bye-first snapshot retains its original order");
  g_cq_enabled = 1;
  g_state_test_creation = 0x010107eau;
  g_cq.fill = CQ_JANUARY_FILL; g_cq.days[0] = 33;
  char view[2048];
  for (int page=0; page<3; page++) {
    int first, end, lines=0;
    expect(cq_view_page(page,&first,&end), "participant page exists");
    int n = fl26_swiss_concacaf_participants(page,view,sizeof view);
    for (int i=0;i<n;i++) lines += view[i]=='\n';
    expect(lines==end-first && lines==(page ? 11 : 5), "the page shows its confirmed entrants");
  }
  expect(fl26_swiss_concacaf_participants(3,view,sizeof view)==0, "invalid page is empty");
  go(2027, 182);
  edition = final_of(CQ_SNAPSHOT);
  expect(fl26_swiss_concacaf_participants(0,view,sizeof view)==0,
         "July must not show the old edition's participants");
  g_cq_enabled = 0;
  expect(!edition || !cq_snapshot_valid(edition->club, edition->n,
         game_date()-(abs_day()-edition->day), game_date(), cq_edition_fill(game_date(),CQ_JANUARY_FILL),33),
         "July rejects the previous edition's field");
  restart();
  go(2027, 0);
  expect(!final_of(CQ_SNAPSHOT), "loading before qualification cannot see the future snapshot");
  go(2028, 1);
  edition = final_of(CQ_SNAPSHOT);
  expect(!edition || !cq_snapshot_valid(edition->club, edition->n,
         game_date()-(abs_day()-edition->day), game_date(), cq_edition_fill(game_date(),CQ_JANUARY_FILL),33),
         "the next January needs a new snapshot");
  keep_table(CQ_SNAPSHOT, 600, 27);
  state_store();
  restart();
  go(2028, 40);
  edition = final_of(CQ_SNAPSHOT);
  expect(edition && edition->club[0]==CLUB(600), "the leap-year edition reloads its own field");
  unsigned char fixture[12]={0};
  fixture[8]=0xec; fixture[9]=0x07; fixture[10]=3; fixture[11]=3;
  expect(ko_mdate(fixture)==2028*365+61, "FL27 match dates use March 3 even in a leap year");
  restart();
  DeleteFileA(g_path_test);
  go(2026,338);
  keep_table(CAR_PODIUM,700,4);
  state_store();
  restart();
  go(2027,1);
  final_t* podium=final_of(CAR_PODIUM);
  expect(podium && podium->n==4 && podium->club[0]==CLUB(700) &&
         car_previous_year(game_date()-(abs_day()-podium->day),game_date()),
         "Caribbean podium survives restart and is available in the following January");
  go(2028,1);
  podium=final_of(CAR_PODIUM);
  expect(!podium || !car_previous_year(game_date()-(abs_day()-podium->day),game_date()),
         "the old Caribbean podium cannot feed another January edition");

  printf("\nCentral American Cup domestic qualification through July and reload\n");
  restart();
  g_ca_dynamic=1;
  g_state_test_creation=0x010107eau;
  g_ca_sources[4].calendar=1;
  go(2026,350);
  keep_table(CA_ANNUAL(4,2026),880,8);
  state_store();
  go(2027,170);
  for (int i=0;i<CA_ASSOCIATIONS;i++)
    if (i!=4) keep_table(CA_ANNUAL(i,2026),800+10*i,8);
  state_store();
  uint32_t expected[CA_FIELD]={0}, replay[CA_FIELD]={0};
  for (int reload=0;reload<2;reload++) {
    if (reload) restart();
    go(2027,CA_DRAW);
    ca_pool pool[CA_ASSOCIATIONS]={{0}};
    for (int i=0;i<CA_ASSOCIATIONS;i++) {
      final_t* f=ca_annual_result(i,game_date(),abs_day(),2026*365,game_date());
      expect(f && f->n==8,"completed annual rank available at the July draw");
      if (f) {
        pool[i].n=f->n;
        memcpy(pool[i].league,f->club,f->n*sizeof *f->club);
      }
    }
    ca_entry field[CA_FIELD];
    expect(ca_allocate(pool,field) &&
           ca_draw_groups(field,2027,reload ? replay : expected),"20 clubs drawn from retained rankings");
  }
  expect(!memcmp(expected,replay,sizeof expected),"identical draw after reloading the domestic result cache");
  expect(!ca_annual_result(0,game_date(),abs_day(),2026*365,2027*365+169),
         "a result completed after the requested cutoff is excluded");
  expect(!ca_annual_result(0,game_date(),abs_day(),2027*365+171,game_date()),
         "a result completed before career creation is excluded");
  printf("\nCentral American Cup sporting journal\n");
  restart();
  DeleteFileA(g_path_test);
  g_ca_ko=701;
  uint16_t sporting=CQ_CENTRAL_KEEP(g_ca_ko);
  go(2026,338);
  keep_table(CAR_PODIUM,700,4);
  go(2026,CQ_CENTRAL_FINAL_DAY);
  keep_table(sporting,920,6);
  state_store();
  long published=file_size();
  state_store();
  expect(file_size()==published,"repeated callbacks leave one checksummed sporting record");
  restart();
  go(2026,CQ_CENTRAL_FINAL_DAY-1);
  expect(!final_of(sporting),"a checkpoint before the final cannot see the result");
  restart();
  go(2027,1);
  final_t* record=final_of(sporting);
  expect(record && record->n==6 && record->club[0]==CLUB(920) && record->club[5]==CLUB(925),
         "sporting placements survive a January reload");
  expect(final_of(CAR_PODIUM) && final_of(CAR_PODIUM)->n==4,
         "the same journal still loads the unrelated Caribbean result");
  state_store();
  expect(file_size()==published,"reload does not duplicate publication");
  cq_source central={.kind=CQ_CENTRAL,.reg=701};
  expect(!ca_feeder(&central,game_date(),game_date(),2026*365,1) && !central.n,
         "same-club journal without native bracket cannot feed the loaded career");
  restart();
  go(2027,182);
  record=final_of(sporting);
  expect(record && cq_central_result(2026,game_date()-(abs_day()-record->day),
         game_date(),record->club,record->n),"completed record survives July rollover and a reload");
  FILE* damaged=fopen(g_path_test,"rb+");
  expect(damaged!=0,"open isolated test journal for corruption test");
  if (damaged) {
    fseek(damaged,8+sizeof(state_rec_t)+offsetof(state_rec_t,check),SEEK_SET);
    int byte=fgetc(damaged);
    fseek(damaged,-1,SEEK_CUR);
    fputc(byte^1,damaged);
    fclose(damaged);
  }
  restart();
  go(2027,1);
  expect(!final_of(sporting),"checksum mismatch rejects the sporting record");
  expect(final_of(CAR_PODIUM)!=0,"a corrupt Central row does not hide the Caribbean result");
  DeleteFileA(g_path_test);
  restart();
  go(2026,CQ_CENTRAL_FINAL_DAY);
  keep_table(sporting,920,5);
  state_store();
  restart();
  go(2027,1);
  expect(!final_of(sporting),"valid checksum cannot make an incomplete result eligible");
  damaged=fopen(g_path_test,"rb+");
  if (damaged) {
    fputs("FL26SST2",damaged);
    fclose(damaged);
  }
  expect(damaged!=0 && !state_open(g_path_test,0) && !state_open(g_path_test,1),
         "unknown journal version is neither read nor replaced");
  g_ca_dynamic=0;

  DeleteFileA(g_path_test);
  printf(fails ? "\n%d check(s) FAILED\n" : "\nall checks passed\n", fails);
  return fails ? 1 : 0;
}
