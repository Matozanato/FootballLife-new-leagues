/* The calendar test harness (FL26_RCAL_TEST): fl26swiss.c's two league schedulers -- the real
   calendars (rcal_dates) and the old calendars moved apart (rest_dates) -- run without the game,
   and every league round checked against the days its clubs may play on besides the league.
   A club never plays two matches on consecutive days: no round within a day of any of them, and
   none within two days of a continental, European or qualifying day.

     zig cc -O2 -fno-sanitize=undefined test_rcal_days.c -o test_rcal_days.exe && test_rcal_days.exe

   (tools/test_rcal_days.py builds and runs it.) Exit code 1 on any failure.

   The cases (0.2.4, "a club never plays two days running", every continent):
     - Uruguay, calendar year, Libertadores places (LIB, LIBQ) and a calendar-year cup on its
       explicit days: the antonimus case (d31a0c1), now from the shipped Libertadores days;
     - a Korean calendar-year league with an AFC Champions League place, dated in January before
       the game has dated the AFC Champions League (no day noted in passing);
     - a Saudi August-May league with an AFC Champions League place, on a real calendar and on the
       old one (rest_dates), dated at a new career's build in August;
     - a day the game gives the AFC Champions League that is not a shipped one (cont_note): kept;
     - Norway, calendar year, a Champions League qualifying place: the August qualifying rounds,
       the autumn league phase and the spring knockout days, dated in January and in August;
     - a league fed to a continental cup of ours only through its cup winner (ccup_feeds);
     - the Club World Cup's days for a league with a Champions League place;
     - both schedulers know the same days (busy_set is the one list);
     - B35: our continental cups a day clear of the game's ones of their region -- every day of
       every table (CCUP_GROUP_DAYS, CCUP_KO_DAYS) against gc_seed's lists, the table each cup
       takes (ccup_region), and Uruguay and Korea, which feed one of the game's cups and one of
       ours, still fit their seasons clear of both. */
#define FL26_RCAL_TEST
#include "fl26swiss.c"
#include <stdio.h>
#include <stdlib.h>

static int g_today_test = 0;
int rcal_test_today(void) { return g_today_test; }
int rcal_test_invites(int k, uint16_t id) { (void)k; (void)id; return 0; }
int rcal_test_recday(uint16_t id) { (void)id; return -1; }

static int fails = 0;
static int cdist(uint32_t a, uint32_t b)
{
  int d = abs((int)a - (int)b);
  return d > 182 ? 365 - d : d;
}
/* the closest any round of r comes to any day of days; -1 none */
static int closest(const date_t* r, int n, const uint32_t* days, int nd, uint32_t* at_r, uint32_t* at_d)
{
  int best = -1;
  for (int i = 0; i < n; i++)
    for (int j = 0; j < nd; j++) {
      int d = cdist(r[i].day, days[j]);
      if (best < 0 || d < best) { best = d; *at_r = r[i].day; *at_d = days[j]; }
    }
  return best;
}
static void expect(int ok, const char* what)
{
  printf("  %s  %s\n", ok ? "ok  " : "FAIL", what);
  if (!ok) fails++;
}
/* rounds against days: none within `min - 1` days */
static void clear_of(const char* name, const date_t* r, int n, const uint32_t* days, int nd, int min)
{
  uint32_t a = 0, b = 0;
  int c = closest(r, n, days, nd, &a, &b);
  char line[256];
  snprintf(line, sizeof line, "%s: %d day(s), the closest round %d day(s) away (round %u, day %u), wanted %d or more",
           name, nd, c, a, b, min);
  expect(nd > 0 && c >= min, line);
}
static void in_order_check(const char* name, const date_t* r, int n)
{
  /* a calendar-year league counts from 1 January, an August-May one from 1 July */
  uint32_t org = r[0].day < r[n - 1].day ? 0 : 182;
  int ok = 1;
  for (int i = 1; i < n; i++)
    if ((r[i].day + 365 - org) % 365 <= (r[i - 1].day + 365 - org) % 365 || cdist(r[i].day, r[i - 1].day) < 2) ok = 0;
  char line[160];
  snprintf(line, sizeof line, "%s: %d rounds in order, a day or more between them (%u .. %u)", name, n, r[0].day, r[n - 1].day);
  expect(ok, line);
}
static int days_of_kinds(uint16_t id, unsigned kinds, uint32_t* out)
{
  static busy_t z[BUSY_MAX];
  int n = busy_set(id, z), k = 0;
  for (int i = 0; i < n; i++) if (kinds >> z[i].kind & 1) out[k++] = z[i].day;
  return k;
}
#define K(x) (1u << (x))
static void rcal_case(const char* name, uint16_t id, int n, int today, date_t* r)
{
  const rcal_t* c = rcal_of(id);
  g_today_test = today;
  memset(r, 0, sizeof(date_t) * (size_t)n);
  int m = rcal_dates(id, c, r, (uint32_t)n, 1);
  char line[160];
  snprintf(line, sizeof line, "%s: a real calendar fits (%d of %d rounds moved)", name, m, n);
  expect(m >= 0, line);
}
static uint32_t gc_list(int g, uint32_t* out)
{
  gc_seed();
  for (int i = 0; i < g_ngcday[g]; i++) out[i] = g_gcday[g][i];
  return (uint32_t)g_ngcday[g];
}
/* every European day of season sy (quals 0: league phases, knockouts, February play-off;
   1: the August qualifying rounds and play-off) -- the module's own tables, its own year */
static int euro_season(int sy, int quals, uint32_t* out)
{
  int keep = g_test_year;
  g_test_year = sy;
  int n = uefa_days(out, 96, quals);
  g_test_year = keep;
  return n;
}

/* B35: one table (region cr, tier t) against the game's days it must keep a day clear of; its
   shape kept: Tuesdays (tier 0) or Wednesdays (tier 1) on the big leagues' grid, the two tiers in
   the same weeks, the groups in season order and November to February, the knockout in order, two
   weeks or more after the last group day, the final before the Club World Cup of ours (day 153) */
static void ccup_table_check(int cr, int t, const uint32_t* avoid, int na, const char* what)
{
  uint32_t all[13]; int n = 0;
  for (int i = 0; i < 6; i++) all[n++] = CCUP_GROUP_DAYS[cr][t][i];
  for (int i = 0; i < 7; i++) all[n++] = CCUP_KO_DAYS[cr][t][i];
  int clear = 1, wk = 1, ord = 1, pair = 1;
  uint32_t a = 0, b = 0;
  for (int i = 0; i < n; i++) {
    for (int j = 0; j < na; j++) if (cdist(all[i], avoid[j]) < 2) { clear = 0; a = all[i]; b = avoid[j]; }
    if ((int)(all[i] % 7) != (t ? 6 : 5)) wk = 0;
    if (i && i != 6 && season_ord((int)all[i]) <= season_ord((int)all[i - 1])) ord = 0;
  }
  for (int i = 0; i < 6; i++) if (CCUP_GROUP_DAYS[cr][0][i] + 1 != CCUP_GROUP_DAYS[cr][1][i]) pair = 0;
  for (int i = 0; i < 7; i++) if (CCUP_KO_DAYS[cr][0][i] + 1 != CCUP_KO_DAYS[cr][1][i]) pair = 0;
  int g0 = season_ord((int)all[0]), g5 = season_ord((int)all[5]), k0 = season_ord((int)all[6]), fin = season_ord((int)all[12]);
  char line[256];
  snprintf(line, sizeof line, "%s, tier %d: a day or more clear of %d game day(s)%s", what, t, na,
           clear ? "" : " -- NOT");
  if (!clear) printf("    day %u next to the game's day %u\n", a, b);
  expect(clear, line);
  snprintf(line, sizeof line, "%s, tier %d: on %s, the tiers in the same weeks, the days in order", what, t,
           t ? "Wednesdays" : "Tuesdays");
  expect(wk && pair && ord, line);
  snprintf(line, sizeof line, "%s, tier %d: groups days %u..%u, knockout %u..%u (two weeks after the groups, final before day 152)",
           what, t, all[0], all[5], all[6], all[12]);
  expect(g0 >= season_ord(305) && g5 <= season_ord(59) && k0 - g5 >= 14 && fin <= season_ord(151), line);
}
/* the days of cup k a league sees (busy_set's way): a straight knockout (groups 0) plays no group day */
static int ccup_days_of(int k, uint32_t* out)
{
  int n = 0;
  if (g_ccup[k].groups) for (int i = 0; i < 6; i++) out[n++] = ccup_day(&g_ccup[k], 0, i);
  for (int i = 0; i < 7; i++) out[n++] = ccup_day(&g_ccup[k], 1, i);
  return n;
}

int main(void)
{
  static date_t r[64];
  uint32_t d1[256], d2[256];
  g_test_year = 2025;                                  /* the 2025/26 season */

  /* the world: leagues 300 Uruguay, 310 Korea, 311 Saudi Arabia (real calendar), 312 Saudi
     Arabia (no rcal line: rest_dates), 320 Norway, 330 a big August-May league, 340 a league
     whose cup winner goes to a continental cup of ours */
  static const uint16_t ACC[][4] = {
    { 300, 1, LIB, 0 }, { 300, 2, LIBQ, 0 },
    { 310, 1, AFCL, 0 }, { 311, 1, AFCL, 0 }, { 312, 1, AFCL, 0 },
    { 320, 1, UCLQ, 0 }, { 320, 2, UECLQ, 0 },
    { 330, 1, UCL, 0 }, { 330, 2, UCL, 0 }, { 330, 3, UEL, 0 },
  };
  expect(fl26_swiss_access(&ACC[0][0], (int)(sizeof ACC / sizeof ACC[0])) > 0, "access list taken");
  /* rcal: reg, first, last, break from, break to, days, also, eu (realcal.py's lines) */
  static const uint16_t RC[][8] = {
    { 300, 51, 339, 0, 0, 96, 16, 0 },                 /* CONMEBOL, calendar year */
    { 310, 58, 339, 0, 0, 96, 16, 0 },                 /* AFC, calendar year */
    { 311, 233, 142, 0, 0, 96, 16, 0 },                /* AFC, August-May */
    { 320, 86, 332, 151, 174, 96, 16, 0 },             /* Norway */
    { 330, 226, 142, 354, 7, 96, 16, 0 },              /* a big August-May league */
    { 340, 58, 339, 0, 0, 96, 16, 0 },
  };
  expect(fl26_swiss_rcal(&RC[0][0], (int)(sizeof RC / sizeof RC[0])) == (int)(sizeof RC / sizeof RC[0]), "rcal lines taken");
  /* Uruguay's cup (301): dated like the national cups on the calendar-year days (leaguebuilder
     CALENDAR_CUP_DATE_DAYS), its division 300 */
  static const uint16_t DL[] = { 301, 23 };
  fl26_swiss_datelike(DL, 1);
  static const uint16_t DD[] = { 301, 65, 107, 149, 191, 233, 275, 317 };
  fl26_swiss_datedays(DD, 8);
  static const uint16_t CD[] = { 301, 1, 1, 300,  341, 1, 1, 340 };
  fl26_swiss_cupdraw(CD, 2);
  /* a continental cup of ours (a CAF Confederation Cup / AFC Champions League Two): one place,
     the winner of cup 341, else league 340's next club */
  g_nccup = 1;
  memset(&g_ccup[0], 0, sizeof g_ccup[0]);
  g_ccup[0].reg = 500; g_ccup[0].ko = 501; g_ccup[0].groups = 4; g_ccup[0].n = 1;
  g_ccup[0].ereg[0] = 341; g_ccup[0].erank[0] = 0; g_ccup[0].ealt[0] = 340;

  uint32_t lib[64], libq[64], afc[64], cwc[64], cup[16];
  int nlib = (int)gc_list(GC_LIB, lib), nlibq = (int)gc_list(GC_LIBQ, libq), nafc = (int)gc_list(GC_AFC, afc),
      ncwc = (int)gc_list(GC_CWC, cwc);
  for (int i = 0; i < 7; i++) cup[i] = DD[1 + i];

  printf("Uruguay (calendar year, Libertadores and its qualifying, Copa AUF on its own days)\n");
  /* the game dates its Libertadores as it goes by: the same days, nothing new */
  {
    date_t gv[6] = { { 62, 0, 2 }, { 76, 1, 2 }, { 83, 2, 2 }, { 104, 3, 2 }, { 118, 4, 2 }, { 139, 5, 2 } };
    vec_t v = { (unsigned char*)gv, (unsigned char*)(gv + 6), (unsigned char*)(gv + 6) };
    cont_note(9, &v);
    expect(g_ngcday[GC_LIB] == nlib, "the game's reg 9 dates are among the shipped ones");
  }
  rcal_case("Uruguay", 300, 30, 0, r);
  in_order_check("Uruguay", r, 30);
  clear_of("Libertadores (regs 9, 10), two days clear", r, 30, lib, nlib, 3);
  clear_of("Libertadores qualifying (reg 8), two days clear", r, 30, libq, nlibq, 3);
  clear_of("Club World Cup, a day clear", r, 30, cwc, ncwc, 2);
  clear_of("Copa AUF (calendar-year cup days), a day clear", r, 30, cup, 7, 2);
  {
    int has265 = 0;
    for (int i = 0; i < nlib; i++) has265 |= lib[i] == 265;
    expect(has265, "the quarter-final of 23 September (day 265) is a Libertadores day");
  }

  printf("Korea (calendar year, AFC Champions League, dated in January before the AFC is)\n");
  rcal_case("Korea", 310, 33, 0, r);
  in_order_check("Korea", r, 33);
  clear_of("AFC Champions League (regs 15, 16 on their midweek), two days clear", r, 33, afc, nafc, 3);
  clear_of("Club World Cup, a day clear", r, 33, cwc, ncwc, 2);
  /* 44 rounds in the same weeks: midweek rounds as well (before 0.2.4: day 320, two from 322) */
  rcal_case("Korea, 44 rounds", 310, 44, 0, r);
  in_order_check("Korea, 44 rounds", r, 44);
  clear_of("AFC Champions League, two days clear (44 rounds)", r, 44, afc, nafc, 3);

  printf("Saudi Arabia (August-May, AFC Champions League, a new career's build)\n");
  rcal_case("Saudi Arabia, real calendar", 311, 30, 216, r);
  in_order_check("Saudi Arabia, real calendar", r, 30);
  clear_of("AFC Champions League, two days clear", r, 30, afc, nafc, 3);
  {
    /* no rcal line: the big leagues' calendar (case 5) moved apart */
    static const uint32_t CASE5[38] = { 233, 240, 261, 265, 268, 275, 296, 300, 303, 310, 321, 324, 331, 335, 338, 345,
                                        356, 359, 363, 2, 13, 16, 20, 23, 31, 34, 37, 51, 58, 65, 72, 79, 100, 107, 114,
                                        121, 128, 142 };
    for (int i = 0; i < 38; i++) { r[i].day = CASE5[i]; r[i].round = (uint32_t)i; r[i].kind = 0; }
    g_today_test = 216;
    rest_dates(312, r, 38);
    in_order_check("Saudi Arabia, old calendar (rest_dates)", r, 38);
    clear_of("AFC Champions League, two days clear (rest_dates)", r, 38, afc, nafc, 3);
  }

  printf("A day the game gives the AFC Champions League that the exe does not ship (cont_note)\n");
  {
    date_t gv[2] = { { 200, 0, 0 }, { 207, 1, 0 } };
    vec_t v = { (unsigned char*)gv, (unsigned char*)(gv + 2), (unsigned char*)(gv + 2) };
    cont_note(16, &v);
    nafc = (int)gc_list(GC_AFC, afc);
    int got = 0;
    for (int i = 0; i < nafc; i++) got += afc[i] == 200 || afc[i] == 207;
    expect(got == 2, "days 200 and 207 kept for the AFC Champions League");
    rcal_case("Korea again", 310, 33, 0, r);
    clear_of("AFC Champions League with the noted days, two days clear", r, 33, afc, nafc, 3);
  }

  printf("Norway (calendar year, Champions League and Conference League qualifying places)\n");
  for (int pass = 0; pass < 2; pass++) {
    int t = pass ? 216 : 0;                            /* dated in January 2026, or at a build in August 2025 */
    int y = t < 175 ? 2026 : 2025;                     /* the calendar year it plays */
    char nm[96];
    snprintf(nm, sizeof nm, "Norway %d, dated on day %d", y, t);
    rcal_case(nm, 320, 30, t, r);
    in_order_check(nm, r, 30);
    /* the qualifying rounds and the autumn league phase of the season that starts in its year,
       the spring knockouts of the one that ends in it */
    int nq = euro_season(y, 1, d1), k = 0;
    clear_of("the August qualifying rounds and play-offs of its year, two days clear", r, 30, d1, nq, 3);
    int na = euro_season(y, 0, d2);
    for (int i = 0; i < na; i++) if (d2[i] >= 181) d1[k++] = d2[i];
    int nb = euro_season(y - 1, 0, d2);
    for (int i = 0; i < nb; i++) if (d2[i] < 181) d1[k++] = d2[i];
    clear_of("the league phase (autumn) and the knockouts (spring) of its seasons, a day clear", r, 30, d1, k, 2);
    if (pass == 0) {
      /* the Uruguay of Europe: before 0.2.4 a calendar-year league kept clear of no European day */
      int lp = 0;
      for (int i = 0; i < k; i++) for (int j = 0; j < 30; j++) if (cdist(r[j].day, d1[i]) < 2) lp++;
      expect(lp == 0, "no Norwegian round the day before or after a European day of 2026");
    }
  }

  printf("A league that reaches a continental cup of ours through its cup winner only\n");
  {
    uint32_t cc[64]; int ncc = 0;
    for (int i = 0; i < 6; i++) cc[ncc++] = ccup_day(&g_ccup[0], 0, i);
    for (int i = 0; i < 7; i++) cc[ncc++] = ccup_day(&g_ccup[0], 1, i);
    expect(ccup_feeds(0, 340) && !ccup_of_league(0, 340), "league 340 feeds cup 500 by its cup's winner (alt=)");
    rcal_case("league 340", 340, 30, 0, r);
    clear_of("the continental cup's group and knockout days, two days clear", r, 30, cc, ncc, 3);
  }

  printf("A big August-May league with Champions League places (the Club World Cup)\n");
  rcal_case("big league", 330, 38, 216, r);
  in_order_check("big league", r, 38);
  clear_of("Club World Cup, a day clear", r, 38, cwc, ncwc, 2);
  {
    int nq = euro_season(2025, 1, d1);
    int ne = euro_season(2025, 0, d2);
    clear_of("the August qualifying rounds, two days clear", r, 38, d1, nq, 3);
    clear_of("the league phases and knockouts, a day clear", r, 38, d2, ne, 2);
  }

  printf("One list for both schedulers\n");
  {
    /* every kind busy_set gives, closed in busy_days at level 0 -- what rcal_cost closes at its
       strict level is the same list (busy_set), so a day busy_days knows is one rcal_cost knows */
    static const uint16_t L[] = { 300, 310, 311, 312, 320, 330, 340 };
    int ok = 1;
    for (size_t i = 0; i < sizeof L / sizeof L[0]; i++) {
      static uint8_t bad[365]; static int32_t pen[365];
      const rcal_t* c = rcal_of(L[i]);
      rcal_t fake = { L[i], 0, 364, 0, 0, 0x7f, 0, 0 };
      g_org = c && c->first < c->last ? 0 : 182;
      if (L[i] == 312) g_org = 182;
      g_today_test = g_org ? 216 : 0;
      busy_days(L[i], 0, REST, bad);
      rcal_cost(L[i], c ? c : &fake, 1, 2, pen);
      for (int p = 0; p < 365; p++) {
        /* busy_days closes two days either side (REST 3), rcal_cost two for the continental and
           European days, one for the cups: every day busy_days closes a day either side of a busy
           day is closed by rcal_cost as well */
        uint32_t d = (uint32_t)(p + (int)g_org) % 365;
        int near1 = 0;
        static busy_t z[BUSY_MAX];
        int n = busy_set(L[i], z);
        for (int j = 0; j < n && !near1; j++) near1 = cdist(d, z[j].day) <= 1;
        if (near1 && (!bad[p] || pen[p] >= 0)) {
          if (pen[p] >= 0) { ok = 0; printf("    league %u: day %u next to a busy day, open to rcal_cost\n", L[i], d); }
          if (!bad[p]) { ok = 0; printf("    league %u: day %u next to a busy day, open to busy_days\n", L[i], d); }
          break;
        }
      }
      g_org = 182;
    }
    expect(ok, "every day next to a busy day is closed by busy_days (level 0) and by rcal_cost (strict)");
  }

  printf("B35: our continental cups clear of the game's ones (Copa Sudamericana, AFC Champions League Two)\n");
  {
    uint32_t libr[128], afcr[128], none[8]; int nl = 0, na = 0;
    for (int i = 0; i < nlib; i++) libr[nl++] = lib[i];
    for (int i = 0; i < nlibq; i++) libr[nl++] = libq[i];
    for (int i = 0; i < ncwc; i++) { libr[nl++] = cwc[i]; afcr[na++] = cwc[i]; }
    for (int i = 0; i < nafc; i++) afcr[na++] = afc[i];   /* gc_seed's on their midweek, and cont_note's */
    {
      /* the tester's finding, in the tables of before (CR_NONE): the Sudamericana on the
         Libertadores qualifying and group days, the Tuesdays a day before the AFC's */
      int hit = 0;
      for (int i = 0; i < 6; i++) for (int j = 0; j < nl; j++) hit += CCUP_GROUP_DAYS[CR_NONE][1][i] == libr[j];
      for (int i = 0; i < 7; i++) for (int j = 0; j < nl; j++) hit += CCUP_KO_DAYS[CR_NONE][1][i] == libr[j];
      expect(hit >= 7, "the days of before put the Wednesday cup on 7 Libertadores days (the B35 finding)");
    }
    for (int t = 0; t < 2; t++) {
      ccup_table_check(CR_LIB, t, libr, nl, "CR_LIB (Libertadores, its qualifying round, the Club World Cup)");
      ccup_table_check(CR_AFC, t, afcr, na, "CR_AFC (AFC Champions League on its midweek, the Club World Cup)");
      ccup_table_check(CR_NONE, t, none, 0, "CR_NONE (as before)");
    }
    /* leaguebuilder's CCUP_DAYS lists all three tables: tools/test_rcal_days.py compares them */

    /* cup 1: a Copa Sudamericana -- Uruguay (300, Libertadores places) 3rd and 4th, and a league
       with none (340); cup 2: an AFC Champions League Two -- Korea's (310) champion (Tuesdays) and
       Saudi Arabia's second (311); cup 0 (league 340's cup winner) reaches none of the game's */
    g_nccup = 3;
    memset(&g_ccup[1], 0, sizeof g_ccup[1]);
    g_ccup[1].reg = 510; g_ccup[1].ko = 511; g_ccup[1].groups = 1; g_ccup[1].n = 4;
    g_ccup[1].ereg[0] = 300; g_ccup[1].erank[0] = 3; g_ccup[1].ereg[1] = 300; g_ccup[1].erank[1] = 4;
    g_ccup[1].ereg[2] = 340; g_ccup[1].erank[2] = 2; g_ccup[1].ereg[3] = 340; g_ccup[1].erank[3] = 3;
    memset(&g_ccup[2], 0, sizeof g_ccup[2]);
    g_ccup[2].reg = 520; g_ccup[2].ko = 521; g_ccup[2].groups = 1; g_ccup[2].n = 4;
    g_ccup[2].ereg[0] = 310; g_ccup[2].erank[0] = 1; g_ccup[2].ereg[1] = 311; g_ccup[2].erank[1] = 2;
    g_ccup[2].ereg[2] = 340; g_ccup[2].erank[2] = 4; g_ccup[2].ereg[3] = 311; g_ccup[2].erank[3] = 3;
    expect(ccup_region(&g_ccup[0]) == CR_NONE && ccup_tier(&g_ccup[0]) == 1, "cup 500 (no league of the game's cups): the days of before");
    expect(ccup_region(&g_ccup[1]) == CR_LIB && ccup_tier(&g_ccup[1]) == 1, "cup 510 (Uruguay's places): Wednesdays, the Libertadores' weeks free");
    expect(ccup_region(&g_ccup[2]) == CR_AFC && ccup_tier(&g_ccup[2]) == 0, "cup 520 (Korea's champion): Tuesdays, the AFC Champions League's weeks free");
    {
      /* an access list loaded after the cups: worked out again (g_ccup_gen) */
      static const uint16_t ACC2[][4] = { { 300, 1, LIB, 0 }, { 310, 1, AFCL, 0 } };
      fl26_swiss_access(&ACC2[0][0], 2);
      int r1 = ccup_region(&g_ccup[1]);
      fl26_swiss_access(&ACC[0][0], (int)(sizeof ACC / sizeof ACC[0]));
      static const uint16_t ACC3[][4] = { { 310, 1, AFCL, 0 } };
      fl26_swiss_access(&ACC3[0][0], 1);
      int r2 = ccup_region(&g_ccup[1]);
      fl26_swiss_access(&ACC[0][0], (int)(sizeof ACC / sizeof ACC[0]));
      int r3 = ccup_region(&g_ccup[1]);
      expect(r1 == CR_LIB && r2 == CR_NONE && r3 == CR_LIB, "a cup's table follows the access list it is read with");
    }
    {
      /* a closed-beta career: its AFC Champions League Two groups dated on the days of before
         end on Tuesday 47 and the knockout is dated the day after -- CR_AFC's round of 16 opens
         on 47, so that season keeps the days of before; a new career dates it after day 33 */
      g_ko_cr_year[2] = 0; g_today_test = 48;
      int old = ccup_ko_table(2, 0);
      g_today_test = 70;                               /* dated again later that season: kept */
      int again = ccup_ko_table(2, 0);
      g_ko_cr_year[2] = 0; g_today_test = 34;
      int fresh = ccup_ko_table(2, 0);
      g_ko_cr_year[2] = 0; g_today_test = 48;
      int ko8 = ccup_ko_table(2, 2);                   /* a knockout of eight starts on day 82 */
      g_ko_cr_year[2] = 0; g_today_test = 238;
      int august = ccup_ko_table(2, 0);                /* a straight knockout, filled in August */
      g_ko_cr_year[2] = 0;
      expect(old == CR_NONE && again == CR_NONE && fresh == CR_AFC && ko8 == CR_AFC && august == CR_AFC,
             "a knockout never dated before today: groups on the days of before keep the knockout's of before");
      g_ko_cr_year[0] = 0; g_today_test = 48;
      expect(ccup_ko_table(0, 0) == CR_NONE, "a cup of CR_NONE keeps its days whenever it is dated");
      g_ko_cr_year[0] = 0;
    }
    uint32_t cd[16];
    int nc1 = ccup_days_of(1, cd);
    {
      date_t cr[16];
      for (int i = 0; i < nc1; i++) { cr[i].day = cd[i]; cr[i].round = (uint32_t)i; cr[i].kind = 0; }
      clear_of("cup 510 (Sudamericana) against the Libertadores (regs 9, 10), a day clear", cr, nc1, lib, nlib, 2);
      clear_of("cup 510 (Sudamericana) against the Libertadores qualifying (reg 8), a day clear", cr, nc1, libq, nlibq, 2);
      int nc2 = ccup_days_of(2, cd);
      for (int i = 0; i < nc2; i++) { cr[i].day = cd[i]; cr[i].round = (uint32_t)i; cr[i].kind = 0; }
      clear_of("cup 520 (AFC Champions League Two) against the AFC Champions League, a day clear", cr, nc2, afcr + ncwc, na - ncwc, 2);
    }
    /* the leagues that feed both still fit, clear of both by two days */
    uint32_t both[160]; int nb = 0;
    for (int i = 0; i < nlib; i++) both[nb++] = lib[i];
    for (int i = 0; i < nlibq; i++) both[nb++] = libq[i];
    nb += ccup_days_of(1, both + nb);
    rcal_case("Uruguay with cup 510", 300, 30, 0, r);
    in_order_check("Uruguay with cup 510", r, 30);
    clear_of("Uruguay: the Libertadores and cup 510, two days clear", r, 30, both, nb, 3);
    nb = 0;
    for (int i = 0; i < nafc; i++) both[nb++] = afc[i];
    nb += ccup_days_of(2, both + nb);
    rcal_case("Korea with cup 520", 310, 33, 0, r);
    in_order_check("Korea with cup 520", r, 33);
    clear_of("Korea: the AFC Champions League and cup 520, two days clear", r, 33, both, nb, 3);
    rcal_case("Saudi Arabia with cup 520", 311, 30, 216, r);
    in_order_check("Saudi Arabia with cup 520", r, 30);
    clear_of("Saudi Arabia: the AFC Champions League and cup 520, two days clear", r, 30, both, nb, 3);
    {
      static const uint32_t CASE5[38] = { 233, 240, 261, 265, 268, 275, 296, 300, 303, 310, 321, 324, 331, 335, 338, 345,
                                          356, 359, 363, 2, 13, 16, 20, 23, 31, 34, 37, 51, 58, 65, 72, 79, 100, 107, 114,
                                          121, 128, 142 };
      g_ccup[2].ereg[3] = 312;                         /* Saudi Arabia, no rcal line: rest_dates */
      g_ccup_gen++;
      nb = 0;
      for (int i = 0; i < nafc; i++) both[nb++] = afc[i];
      nb += ccup_days_of(2, both + nb);
      for (int i = 0; i < 38; i++) { r[i].day = CASE5[i]; r[i].round = (uint32_t)i; r[i].kind = 0; }
      g_today_test = 216;
      rest_dates(312, r, 38);
      in_order_check("Saudi Arabia, old calendar, with cup 520 (rest_dates)", r, 38);
      clear_of("Saudi Arabia (rest_dates): the AFC Champions League and cup 520, two days clear", r, 38, both, nb, 3);
    }
  }

  /* a July start does not bring a league's first round before its country's super cup (B36):
     Liga Portugal (22) on 22 August, the Supertaça on 13 and 16 August, `july 22 219` */
  printf("\nJuly start and the game's super cup (B36)\n");
  {
    uint16_t jl[4] = { 22, 219, 23, 219 };
    fl26_swiss_july(jl, 2);
    static uint16_t cd[100];
    cd[0] = 22; cd[1] = 2; cd[2] = 224; cd[3] = 227;              /* Portugal: its super cup */
    cd[50] = 23; cd[51] = 1; cd[52] = 300;                         /* another: a cup in October */
    fl26_swiss_cupdays(cd, 2);
    date_t a[6], b[6];
    for (int i = 0; i < 6; i++) {
      a[i].day = b[i].day = 233 + 7 * (uint32_t)i;
      a[i].round = b[i].round = (uint32_t)i;
      a[i].kind = b[i].kind = 0;
    }
    g_today_test = 181;
    july_start(22, a, 6, 0);
    july_start(23, b, 6, 0);
    expect(a[0].day == 233, "Liga Portugal keeps its first round a week after the Supertaca (233, not 219)");
    expect(b[0].day == 219, "a league with no cup before its first round still starts in July (219)");
    fl26_swiss_july(0, 0);
    fl26_swiss_cupdays(0, 0);
    g_today_test = 0;
  }

  printf(fails ? "\n%d check(s) FAILED\n" : "\nall checks passed\n", fails);
  return fails ? 1 : 0;
}
