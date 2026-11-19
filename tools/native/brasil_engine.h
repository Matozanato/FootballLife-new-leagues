/* ---- Brazil's Serie C and Serie D on the knockout maker (lab 18/11/2026, FL27) ----
 *
 * Included in fl26swiss.c after the one-regulation cup helpers (it uses ko_round, ko_slot, ko_match, CREATE_RVA, KC_SCHED_RVA,
 * orc_fresh, orc_register, orc_list, orc_tie_winner, cwc_club, orc_cal_year, sched_rebuild).
 *
 * World file (`xline <export> <numbers>`, fl26swiss.lua hands the numbers as uint32):
 *   xline fl26_swiss_sdko <R> <ng> <group regs x ng> <fill x7> <days x14>
 *     the Serie D's knockout on ONE regulation R (the FL26 sdkc, 13/11/2026, brought over) plus the
 *     promotion play-off (repescagem) of the 2026 CBF format: every round two legs --
 *       0 second phase (64: per two groups 4b v 1a, 3a v 2b, 4a v 1b, 3b v 2a; kinds 0x20, 0x21)
 *       1 third phase (32; tie 2i's winner v tie 2i+1's; 0x30)   2 round of 16 (0x2e)
 *       3 quarter-finals: the eight by campaign, 1v8 4v5 2v7 3v6 (0x33) [CBF: "sorteio dirigido" -- a confirmar]
 *       4 repescagem: the four quarter-final losers by campaign, 1v4 2v3, level on aggregate -> campaign (0x31)
 *       5 semi-finals (0x34)   6 final (0x35)
 *     campaign = every match of the season in the groups and R: points, wins, goal difference, goals; the
 *     better campaign plays the second leg at home. Up to the Serie C: the four semi-finalists and the two
 *     repescagem winners (fl26_swiss_promoted).
 *   xline fl26_swiss_cquad <R> <F> <ns> <source league regs x ns> <fill> <days x6> <final d1> <final d2>
 *     the Serie C's second phase on ONE regulation R: two quadrangulares of four, home and away, then a
 *     two-legged final between their winners. One source table (2026/2027, 20/24 clubs): 1-4-5-8 and 2-3-6-7;
 *     two (2028+, two groups of 14): A1-B2-A3-B4 and B1-A2-B3-A4 [a confirmar]. Each pair of a quadrangular
 *     plays as a two-legged tie (kinds 0x21 0x22 0x23: rounds 1/4, 2/5, 3/6); the group table counts the
 *     normal time only (the game may add extra time to a level second leg: not counted). Up to the Serie B:
 *     the first two of each (fl26_swiss_promoted). Final: 0x35, the better campaign at home in leg 2.
 *   xline fl26_swiss_cqleague <A> <B>
 *     (19/11/2026) the quadrangulares as two real leagues of four (A, B: leagues of the recipe, asleep until then --
 *     fl26join's rlate): on the fill day they get 1-4-5-8 / 2-3-6-7 and are registered (register_all); the line
 *     <R> of cquad then stands for the leagues, the final and the promotion go by their tables.
 *   xline fl26_swiss_rshape <reg> <first year> <clubs> <legs> ...
 *     a league's shape from a season on (the Serie C: 2 groups of 14, home and away, from 2028). */
#define BR_ROUNDS 7
#ifndef CP_BR_BASE
#define CP_BR_BASE 250
#endif
static const uint8_t BR_KIND[BR_ROUNDS][2] = { { 0x20, 0x21 }, { 0x30, 0 }, { 0x2e, 0 }, { 0x33, 0 }, { 0x31, 0 }, { 0x34, 0 }, { 0x35, 0 } };
static const char* const BR_NAME[BR_ROUNDS] = { "second phase", "third phase", "round of 16", "quarter-finals",
                                                "repescagem", "semi-finals", "final" };
#define BR_MAXG 20
typedef struct {
  int on; uint16_t reg; int ng; uint16_t g[BR_MAXG]; uint16_t fill[BR_ROUNDS], day[BR_ROUNDS][2];
  int made[BR_ROUNDS], champ_year;
} sdko_t;
static sdko_t g_sd;
#define CQ_MAXS 4
static const uint8_t CQ_KIND[3] = { 0x21, 0x22, 0x23 };
typedef struct {
  int on; uint16_t reg, freg; int ns; uint16_t src[CQ_MAXS]; uint16_t fill, day[6], fday[2];
  int made, fmade;
} cquad_t;
static cquad_t g_cq;
/* lab 19/11/2026 (the user's option 1): the quadrangulares as two real leagues of four, home and away, with
   their own tables -- siblings of the C (its popup's items), asleep (fl26join rlate) until the first phase ends:
     xline fl26_swiss_cqleague <quadrangular A reg> <quadrangular B reg>
   then the cquad line's R is not used (the knockout pairs of 0x21..0x23 are not made) */
static uint16_t g_cql[2]; static int g_cql_on = 0;

typedef struct { uint32_t club; int pts, w, gd, gf, pos; } br_row_t;

static void* br_blk(void) { return orc_blk(); }
/* the match table, as count_table walks it */
static unsigned char* br_matches(uint32_t* cap)
{
  const unsigned char* bs = (const unsigned char*)(g_base + MATCH_BASE_SITE);
  const unsigned char* cs = (const unsigned char*)(g_base + MATCH_CAP_SITE);
  if (bs[0] != 0x48 || bs[1] != 0x8d || bs[2] != 0x88 || cs[0] != 0x81 || cs[1] != 0xff) return 0;
  uint32_t base = *(const uint32_t*)(bs + 3);
  *cap = *(const uint32_t*)(cs + 2);
  unsigned char* blk = (unsigned char*)br_blk();
  if (!blk || !*cap || *cap > 200000) return 0;
  return blk + base;
}
/* rows[]: the clubs to rank; every played match of year under regs[] (kinds: 0 any, else only those of
   reg kreg) is counted. normal_only: the normal time's goals (a quadrangular's level second legs) */
static void br_count(br_row_t* rows, int n, const uint16_t* regs, int nr, int year, uint16_t kreg,
                     const uint8_t* kinds, int nk, int normal_only)
{
  for (int i = 0; i < n; i++) rows[i].pts = rows[i].w = rows[i].gd = rows[i].gf = 0;
  uint32_t cap = 0; unsigned char* mt = br_matches(&cap);
  if (!mt) return;
  for (uint32_t i = 0; i < cap; i++) {
    const unsigned char* m = mt + (size_t)i * MATCH_STRIDE;
    if (*(const uint16_t*)m == 0xffff || !(m[7] & 0x40) || *(const uint16_t*)(m + 8) != year) continue;
    uint16_t r = *(const uint16_t*)(m + 4);
    int mine = 0;
    for (int k = 0; k < nr; k++) mine |= regs[k] == r;
    if (!mine) continue;
    if (nk && r == kreg) {
      /* the round of a match: its slot's kind is not on the match; the kinds' rounds are looked up */
      int in = 0;
      for (int q = 0; q < nk && !in; q++) {
        unsigned char* rnd = ko_round(kreg, kinds[q]);
        int ns = ko_slots(rnd);
        for (int s = 0; s < ns && s < 16 && !in; s++) {
          const uint16_t* ids = (const uint16_t*)(ko_slot(rnd, s) + 2);
          in = ids[0] == *(const uint16_t*)m || ids[1] == *(const uint16_t*)m;
        }
      }
      if (!in) continue;
    }
    uint32_t side[2] = { *(const uint32_t*)(m + 0x14), *(const uint32_t*)(m + 0x18) };
    int g[2] = { m[0x1c] + (normal_only ? 0 : m[0x1d]), m[0x1f] + (normal_only ? 0 : m[0x20]) };
    for (int j = 0; j < 2; j++)
      for (int k = 0; k < n; k++)
        if (same_club(rows[k].club, side[j])) {
          int me = g[j], them = g[1 - j];
          rows[k].pts += me > them ? 3 : me == them ? 1 : 0;
          rows[k].w += me > them;
          rows[k].gd += me - them; rows[k].gf += me;
        }
  }
}
static int br_better(const br_row_t* a, const br_row_t* b)
{
  if (a->pts != b->pts) return a->pts > b->pts;
  if (a->w != b->w) return a->w > b->w;
  if (a->gd != b->gd) return a->gd > b->gd;
  if (a->gf != b->gf) return a->gf > b->gf;
  return a->pos < b->pos;
}
static void br_sort(br_row_t* r, int n)
{
  for (int a = 1; a < n; a++)
    for (int b = a; b > 0 && br_better(&r[b], &r[b - 1]); b--) { br_row_t t = r[b]; r[b] = r[b - 1]; r[b - 1] = t; }
}
/* make the ties of one kind of reg: cl holds them (leg 1's home first), two legs on d1, d2 (d2 0: one match) */
static int br_make_kind(uint16_t reg, uint8_t kind, uint32_t* cl, unsigned n, uint16_t d1, uint16_t d2, const char* what)
{
  kc_create_fn mk = (kc_create_fn)(uintptr_t)(g_base + CREATE_RVA);
  struct { uint32_t* b; uint32_t* e; uint32_t* c; } vec = { cl, cl + n, cl + n };
  int made = 0;
  for (unsigned t = 0; t < n / 2 && t < 16; t++) {
    if (d2) { made += mk(0, &vec, reg, kind, 0, t) != 0; made += mk(0, &vec, reg, kind, 1, t) != 0; }
    else made += mk(0, &vec, reg, kind, 2, t) != 0;
  }
  unsigned char* rnd = ko_round(reg, kind);
  int k = ko_slots(rnd);
  static unsigned char ctx[256];
  for (int s = 0; s < k && s < 16; s++) {
    uint32_t* sl = ko_slot(rnd, s);
    unsigned t = (sl[3] >> 22) & 0x1f;
    if (2 * t + 1 >= n) continue;
    uint32_t h = cl[2 * t], a = cl[2 * t + 1];
    uint16_t* ids = (uint16_t*)(sl + 2);
    sl[0] = h; sl[1] = a;
    unsigned char* m1 = ko_match(ids[0]);
    unsigned char* m2 = ids[1] == 0xffff ? 0 : ko_match(ids[1]);
    if (m1) { *(uint32_t*)(m1 + 0x14) = h; *(uint32_t*)(m1 + 0x18) = a; }
    if (m2) { *(uint32_t*)(m2 + 0x14) = a; *(uint32_t*)(m2 + 0x18) = h; }
    if (m1) ((kc_sched_fn)(uintptr_t)(g_base + KC_SCHED_RVA))(ctx, d1, ids[0]);
    if (m2) ((kc_sched_fn)(uintptr_t)(g_base + KC_SCHED_RVA))(ctx, d2, ids[1]);
    if (s < 2 || n <= 8)
      logf("fl26swiss:   %s reg %u kind %#x tie %2u: %08x v %08x, matches %u/%u", what, (unsigned)reg, kind, t, h, a,
           (unsigned)ids[0], (unsigned)ids[1]);
  }
  return made;
}
/* a new edition: every kind of reg (kinds[]) holding an earlier year's ties is emptied */
static void br_new_edition(uint16_t reg, const uint8_t* kinds, int nk, int year, const char* what)
{
  int emptied = 0;
  for (int i = 0; i < nk; i++) {
    if (!kinds[i]) continue;
    unsigned char* rnd = ko_round(reg, kinds[i]);
    int k = ko_slots(rnd);
    if (k < 1 || orc_fresh(reg, rnd, year)) continue;
    for (int s = 0; s < k && s < 16; s++) memset(ko_slot(rnd, s), 0xff, 32);
    *(uint32_t*)(rnd + 0x204) &= ~0x3ffffffu;
    emptied++;
  }
  if (emptied) logf("fl26swiss: %s -- a new edition: %d round record(s) of reg %u emptied", what, emptied, (unsigned)reg);
}
/* the reg's list: these clubs, the user's first */
static void br_list(uint16_t reg, const uint32_t* cl, unsigned n) { orc_list(reg, cl, n > 48 ? 48 : n); }
static int br_league_over(uint16_t reg)
{
  int m = ccup_matches(reg), u = ccup_unplayed(reg);
  return m > 0 && u == 0;
}

/* ---------- the Serie D's knockout ---------- */
__declspec(dllexport) int fl26_swiss_sdko(const uint32_t* v, int n)
{
  g_sd.on = 0;
  if (!v || n < 2) return 0;
  int p = 0;
  g_sd.reg = (uint16_t)v[p++]; g_sd.ng = (int)v[p++];
  if (g_sd.ng < 2 || g_sd.ng > BR_MAXG || g_sd.ng % 2 || n != 2 + g_sd.ng + BR_ROUNDS + 2 * BR_ROUNDS) {
    logf("fl26swiss: sdko -- bad line (%d values, %d groups)", n, g_sd.ng); return 0;
  }
  for (int g = 0; g < g_sd.ng; g++) g_sd.g[g] = (uint16_t)v[p++];
  for (int r = 0; r < BR_ROUNDS; r++) g_sd.fill[r] = (uint16_t)v[p++];
  for (int r = 0; r < BR_ROUNDS; r++) { g_sd.day[r][0] = (uint16_t)v[p++]; g_sd.day[r][1] = (uint16_t)v[p++]; }
  for (int r = 0; r < BR_ROUNDS; r++) g_sd.made[r] = -1000;
  g_sd.champ_year = -1000;
  g_sd.on = 1;
  logf("fl26swiss: sdko -- the Serie D's knockout on reg %u: %d groups (%u..%u), 7 two-legged rounds with the repescagem, "
       "days %u..%u", (unsigned)g_sd.reg, g_sd.ng, (unsigned)g_sd.g[0], (unsigned)g_sd.g[g_sd.ng - 1],
       (unsigned)g_sd.day[0][0], (unsigned)g_sd.day[BR_ROUNDS - 1][1]);
  return 1;
}
static int sd_round_fresh(int r, int year)
{
  int any = 0;
  for (int c = 0; c < 2 && BR_KIND[r][c]; c++) any |= orc_fresh(g_sd.reg, ko_round(g_sd.reg, BR_KIND[r][c]), year);
  return any;
}
/* a two-legged tie's winner; level on aggregate (extra time counted) -> by_campaign ? the second leg's host
   (the better campaign) : the game's (penalties) */
static uint32_t sd_tie_winner(const uint32_t* sl, int by_campaign)
{
  const uint16_t* ids = (const uint16_t*)(sl + 2);
  unsigned char* m1 = ko_match(ids[0]);
  unsigned char* m2 = ids[1] == 0xffff ? 0 : ko_match(ids[1]);
  if (!m1 || !(m1[7] & 0x40) || (ids[1] != 0xffff && (!m2 || !(m2[7] & 0x40)))) return 0;
  if (!by_campaign) return orc_tie_winner(sl);
  uint32_t h = *(uint32_t*)(m1 + 0x14), a = *(uint32_t*)(m1 + 0x18);
  int gh = m1[0x1c] + m1[0x1d], ga = m1[0x1f] + m1[0x20];
  if (m2) { gh += m2[0x1f] + m2[0x20]; ga += m2[0x1c] + m2[0x1d]; }
  if (gh == ga) return canon_club(a);                 /* the second leg's host: the better campaign */
  return canon_club(gh > ga ? h : a);
}
/* round r's ties in order (kind by kind): {leg-1 home, leg-1 away, winner}; ties count, -1 one undecided */
static int sd_round(int r, int year, uint32_t (*t)[3])
{
  int n = 0;
  for (int c = 0; c < 2 && BR_KIND[r][c]; c++) {
    unsigned char* rnd = ko_round(g_sd.reg, BR_KIND[r][c]);
    if (!orc_fresh(g_sd.reg, rnd, year)) continue;
    int k = ko_slots(rnd);
    for (int s = 0; s < k && s < 16; s++) {
      uint32_t* sl = ko_slot(rnd, s);
      int i = 16 * c + (int)((sl[3] >> 22) & 0x1f);
      if (i >= 32) return -1;
      t[i][0] = canon_club(sl[0]); t[i][1] = canon_club(sl[1]);
      uint32_t w = sd_tie_winner(sl, r == 4);
      if (!(w >> 14)) return -1;
      t[i][2] = canon_club(w);
      n++;
    }
  }
  return n;
}
static int sd_need(int r) { static const int N[BR_ROUNDS] = { 32, 16, 8, 4, 2, 2, 1 }; return N[r]; }
/* the campaign order of cl[0..n) this season (groups + knockout) */
static void sd_by_campaign(uint32_t* cl, int n, int year)
{
  br_row_t rows[16];
  uint16_t regs[BR_MAXG + 1]; int nr = 0;
  for (int g = 0; g < g_sd.ng; g++) regs[nr++] = g_sd.g[g];
  regs[nr++] = g_sd.reg;
  for (int i = 0; i < n && i < 16; i++) { rows[i].club = cl[i]; rows[i].pos = i; }
  br_count(rows, n, regs, nr, year, 0, 0, 0, 0);
  br_sort(rows, n);
  for (int i = 0; i < n; i++) cl[i] = rows[i].club;
}
/* order a pair so the better campaign plays the second leg at home: leg 1's home first */
static void sd_pair(uint32_t* out, uint32_t a, uint32_t b, int year)
{
  uint32_t x[2] = { a, b };
  sd_by_campaign(x, 2, year);
  out[0] = x[1]; out[1] = x[0];
}
static uint32_t sd_place(int g, int pos)
{
  const char* how = "";
  uint32_t c = cwc_club(g_sd.g[g], pos + 1, &how);
  return c ? canon_club(c) : 0;
}
static void sd_make(int r, uint32_t* cl, unsigned n, int year)
{
  if (r == 0) {
    static const uint8_t ALL[] = { 0x20, 0x21, 0x30, 0x2e, 0x33, 0x31, 0x34, 0x35 };
    br_new_edition(g_sd.reg, ALL, sizeof ALL, year, "sdko");
    orc_register(g_sd.reg, year, "sdko");
  }
  int made = 0, kinds = 0;
  for (unsigned off = 0; off < n; off += 32) {
    if (kinds >= 2 || !BR_KIND[r][kinds]) break;
    made += br_make_kind(g_sd.reg, BR_KIND[r][kinds++], cl + off, n - off < 32 ? n - off : 32, g_sd.day[r][0], g_sd.day[r][1], "sdko");
  }
  g_sd.made[r] = year;
  br_list(g_sd.reg, cl, n);
  logf("fl26swiss: sdko -- day %d: %s made, %u ties, %d match(es)", today(), BR_NAME[r], n / 2, made);
  sched_rebuild("sdko round made");
}
static void sdko_tick(void)
{
  if (!g_sd.on || !g_base) return;
  int d = today(), year = orc_cal_year();
  if (d < 1 || year < 0) return;
  static int tried = -100000;
  if (tried == abs_day()) return;
  tried = abs_day();
  for (int r = 0; r < BR_ROUNDS; r++) {
    if (g_sd.made[r] == year || d < g_sd.fill[r] || d >= g_sd.day[r][0]) continue;
    if (sd_round_fresh(r, year)) { g_sd.made[r] = year; continue; }      /* made already (a save loaded) */
    uint32_t cl[64]; unsigned n = 0;
    uint32_t t[32][3];
    if (r == 0) {
      int over = 1;
      for (int g = 0; g < g_sd.ng; g++) over &= br_league_over(g_sd.g[g]);
      if (!over) continue;
      int missing = 0;
      for (int g0 = 0; g0 + 1 < g_sd.ng && !missing; g0 += 2) {
        int a = g0, b = g0 + 1;
        const int pick[4][4] = { { b, 3, a, 0 }, { a, 2, b, 1 }, { a, 3, b, 0 }, { b, 2, a, 1 } };
        for (int q = 0; q < 4 && !missing; q++)
          for (int s = 0; s < 2 && !missing; s++) {
            uint32_t c = sd_place(pick[q][2 * s], pick[q][2 * s + 1]);
            if (!c) missing = 1; else cl[n++] = c;
          }
      }
      if (missing) { logf("fl26swiss: sdko -- a group's table has no club at a place; second phase not made"); g_sd.made[r] = year; continue; }
    } else if (r == 1 || r == 2) {
      int nt = sd_round(r - 1, year, t);
      if (nt != sd_need(r - 1)) continue;
      for (int i = 0; i + 1 < nt; i += 2) { sd_pair(cl + n, t[i][2], t[i + 1][2], year); n += 2; }
    } else if (r == 3) {                                   /* quarter-finals: 1v8 4v5 2v7 3v6 by campaign */
      int nt = sd_round(2, year, t);
      if (nt != 8) continue;
      uint32_t w[8]; for (int i = 0; i < 8; i++) w[i] = t[i][2];
      sd_by_campaign(w, 8, year);
      static const int P[4][2] = { { 0, 7 }, { 3, 4 }, { 1, 6 }, { 2, 5 } };
      for (int q = 0; q < 4; q++) { cl[n++] = w[P[q][1]]; cl[n++] = w[P[q][0]]; }
    } else if (r == 4 || r == 5) {                         /* repescagem (the QF losers) and the semi-finals */
      int nt = sd_round(3, year, t);
      if (nt != 4) continue;
      if (r == 4) {
        uint32_t l[4];
        for (int i = 0; i < 4; i++) l[i] = same_club(t[i][2], t[i][0]) ? t[i][1] : t[i][0];
        sd_by_campaign(l, 4, year);
        cl[n++] = l[3]; cl[n++] = l[0]; cl[n++] = l[2]; cl[n++] = l[1];
      } else {
        sd_pair(cl + n, t[0][2], t[1][2], year); n += 2;
        sd_pair(cl + n, t[2][2], t[3][2], year); n += 2;
      }
    } else {                                               /* the final */
      int nt = sd_round(5, year, t);
      if (nt != 2) continue;
      sd_pair(cl, t[0][2], t[1][2], year); n = 2;
    }
    if (n != 2u * (unsigned)sd_need(r)) { logf("fl26swiss: sdko -- %s has %u clubs; not made", BR_NAME[r], n); g_sd.made[r] = year; continue; }
    sd_make(r, cl, n, year);
  }
  if (g_sd.champ_year != year) {
    uint32_t t[32][3];
    if (sd_round(6, year, t) == 1) { g_sd.champ_year = year; logf("fl26swiss: sdko -- day %d: the Serie D's champion is %08x", d, t[0][2]); }
  }
}
/* the six up to the Serie C (four semi-finalists, two repescagem winners) of year, or 0 */
static int sd_promoted(int year, uint32_t* out)
{
  uint32_t t[32][3];
  int n = 0;
  unsigned char* rnd = ko_round(g_sd.reg, 0x34);
  if (!orc_fresh(g_sd.reg, rnd, year) || ko_slots(rnd) != 2) return 0;
  for (int s = 0; s < 2; s++) { uint32_t* sl = ko_slot(rnd, s); out[n++] = canon_club(sl[0]); out[n++] = canon_club(sl[1]); }
  if (sd_round(4, year, t) != 2) return 0;
  out[n++] = t[0][2]; out[n++] = t[1][2];
  return n;
}
static int sd_dates(uint64_t reg, void* vec, uint64_t* rv)
{
  if (!g_sd.on || (uint16_t)reg != g_sd.reg) return 0;
  *rv = ((date_fn)(uintptr_t)g_tramp_date)((reg & ~(uint64_t)0xffff) | 17, vec);
  vec_t* v = (vec_t*)vec;
  size_t have = (v->b && v->e >= v->b) ? (size_t)(v->e - v->b) / sizeof(date_t) : 0;
  date_t* dd = (date_t*)v->b;
  size_t k = 0;
  for (int r = 0; r < BR_ROUNDS; r++)
    for (int c = 0; c < 2 && BR_KIND[r][c]; c++)
      for (int leg = 0; leg < 2 && k < have; leg++, k++) { dd[k].day = g_sd.day[r][leg]; dd[k].round = BR_KIND[r][c]; dd[k].kind = (uint32_t)leg; }
  v->e = v->b + k * sizeof(date_t);
  static int said;
  if (said++ < 2) logf("fl26swiss: sdko -- reg %u dated: %u record(s) (of %u borrowed)", (unsigned)g_sd.reg, (unsigned)k, (unsigned)have);
  return 1;
}

/* ---------- the Serie C's quadrangulares and final ---------- */
__declspec(dllexport) int fl26_swiss_cquad(const uint32_t* v, int n)
{
  g_cq.on = 0;
  if (!v || n < 2) return 0;
  int p = 0;
  g_cq.reg = (uint16_t)v[p++]; g_cq.freg = (uint16_t)v[p++]; g_cq.ns = (int)v[p++];
  if (g_cq.ns < 1 || g_cq.ns > CQ_MAXS || n != 3 + g_cq.ns + 1 + 6 + 2) { logf("fl26swiss: cquad -- bad line (%d values)", n); return 0; }
  for (int s = 0; s < g_cq.ns; s++) g_cq.src[s] = (uint16_t)v[p++];
  g_cq.fill = (uint16_t)v[p++];
  for (int i = 0; i < 6; i++) g_cq.day[i] = (uint16_t)v[p++];
  g_cq.fday[0] = (uint16_t)v[p++]; g_cq.fday[1] = (uint16_t)v[p++];
  g_cq.made = g_cq.fmade = -1000;
  g_cq.on = 1;
  logf("fl26swiss: cquad -- the Serie C's quadrangulares on reg %u from %d table(s) (%u...), filled from day %u, "
       "rounds %u..%u, final %u/%u", (unsigned)g_cq.reg, g_cq.ns, (unsigned)g_cq.src[0], (unsigned)g_cq.fill,
       (unsigned)g_cq.day[0], (unsigned)g_cq.day[5], (unsigned)g_cq.fday[0], (unsigned)g_cq.fday[1]);
  return 1;
}
__declspec(dllexport) int fl26_swiss_cqleague(const uint32_t* v, int n)
{
  g_cql_on = 0;
  if (!v || n != 2) { logf("fl26swiss: cqleague -- bad line (%d values)", n); return 0; }
  g_cql[0] = (uint16_t)v[0]; g_cql[1] = (uint16_t)v[1]; g_cql_on = 1;
  logf("fl26swiss: cqleague -- the quadrangulares are leagues %u and %u (filled and registered when the first phase ends)",
       (unsigned)g_cql[0], (unsigned)g_cql[1]);
  return 1;
}
/* the match records of reg in year; *played: those played */
static int br_reg_matches(uint16_t reg, int year, int* played)
{
  int tot = 0, pl = 0;
  uint32_t cap = 0; unsigned char* mt = br_matches(&cap);
  if (!mt) { if (played) *played = 0; return 0; }
  for (uint32_t i = 0; i < cap; i++) {
    const unsigned char* m = mt + (size_t)i * MATCH_STRIDE;
    if (*(const uint16_t*)m == 0xffff || *(const uint16_t*)(m + 4) != reg || *(const uint16_t*)(m + 8) != year) continue;
    tot++; pl += (m[7] & 0x40) != 0;
  }
  if (played) *played = pl;
  return tot;
}
/* a league's list written as given (the first phase's order: the tables' last tie-break) */
static void br_set_list(uint16_t reg, const uint32_t* cl, unsigned n)
{
  uint32_t lst[8]; unsigned k = n > 8 ? 8 : n;
  memcpy(lst, cl, sizeof(uint32_t) * k);
  u32vec va = { lst, lst + k, lst + k };
  ((setclr_fn)(uintptr_t)g_tramp_setcl)(reg, &va, 1);
  run_flush();
}
/* fl26join's door lets reg in on its next call (jline fl26_join_rlate); 0: no fl26join or not one of its leagues */
static int br_late_open(uint16_t reg)
{
  HMODULE j = GetModuleHandleA("fl26join.dll");
  typedef int (*open_fn)(uint32_t);
  open_fn f = j ? (open_fn)(void*)GetProcAddress(j, "fl26_join_late_open") : 0;
  return f ? f(reg) : 0;
}
/* the source leagues with clubs this season (2027: one table; 2028+: two groups) */
static int cq_sources(uint16_t* out)
{
  int k = 0;
  for (int s = 0; s < g_cq.ns; s++) { unsigned char* rec = get_rec(g_cq.src[s]); if (rec && rec_count(rec) >= 8) out[k++] = g_cq.src[s]; }
  return k;
}
/* the two quadrangulares' members (q[0][0..4), q[1][0..4)) as round 1 holds them, else 0 */
static int cq_members(int year, uint32_t q[2][4])
{
  if (g_cql_on) {   /* the leagues' lists, once this year's matches are in them */
    for (int g = 0; g < 2; g++) {
      unsigned char* rec = get_rec(g_cql[g]);
      if (!rec || rec_count(rec) != 4 || br_reg_matches(g_cql[g], year, 0) < 1) return 0;
      for (int i = 0; i < 4; i++) q[g][i] = canon_club(rec_clubs(rec)[i]);
    }
    return 1;
  }
  unsigned char* rnd = ko_round(g_cq.reg, CQ_KIND[0]);
  if (!orc_fresh(g_cq.reg, rnd, year) || ko_slots(rnd) != 4) return 0;
  for (int s = 0; s < 4; s++) {
    uint32_t* sl = ko_slot(rnd, s);
    unsigned t = (sl[3] >> 22) & 0x1f;
    if (t > 3) return 0;
    /* leg 1 home is the slot's first (br_make_kind wrote cl[2t], cl[2t+1]) */
    q[t / 2][2 * (t % 2)] = canon_club(sl[0]); q[t / 2][2 * (t % 2) + 1] = canon_club(sl[1]);
  }
  return 1;
}
/* quadrangular g's table (rows[0..4)), the first phase's order breaking the last ties; played: its matches */
static int cq_table(int year, int g, const uint32_t* mem, br_row_t* rows)
{
  for (int i = 0; i < 4; i++) { rows[i].club = mem[i]; rows[i].pos = i; }
  uint16_t regs[1] = { g_cql_on ? g_cql[g] : g_cq.reg };
  if (g_cql_on) br_count(rows, 4, regs, 1, year, 0xffff, 0, 0, 1);
  else br_count(rows, 4, regs, 1, year, g_cq.reg, CQ_KIND, 3, 1);
  br_sort(rows, 4);
  return 1;
}
static int cq_over(int year)
{
  if (g_cql_on) {
    for (int g = 0; g < 2; g++) { int pl, t = br_reg_matches(g_cql[g], year, &pl); if (t < 12 || pl < t) return 0; }
    return 1;
  }
  for (int k = 0; k < 3; k++) {
    unsigned char* rnd = ko_round(g_cq.reg, CQ_KIND[k]);
    if (!orc_fresh(g_cq.reg, rnd, year)) return 0;
    for (int s = 0; s < ko_slots(rnd) && s < 16; s++) {
      const uint16_t* ids = (const uint16_t*)(ko_slot(rnd, s) + 2);
      for (int j = 0; j < 2; j++) { unsigned char* m = ids[j] == 0xffff ? 0 : ko_match(ids[j]); if (!m || !(m[7] & 0x40)) return 0; }
    }
  }
  return 1;
}
static void cquad_tick(void)
{
  if (!g_cq.on || !g_base) return;
  int d = today(), year = orc_cal_year();
  if (d < 1 || year < 0) return;
  static int tried = -100000;
  if (tried == abs_day()) return;
  tried = abs_day();
  if (g_cq.made != year && d >= g_cq.fill && d < g_cq.day[0]) {
    uint32_t q[2][4];
    if (cq_members(year, q)) g_cq.made = year;
    else {
      uint16_t src[CQ_MAXS]; int ns = cq_sources(src), over = ns > 0;
      for (int s = 0; s < ns; s++) over &= br_league_over(src[s]);
      if (over) {
        const char* how = ""; int ok = 1;
        if (ns == 1) {
          static const int P[2][4] = { { 1, 4, 5, 8 }, { 2, 3, 6, 7 } };
          for (int g = 0; g < 2; g++) for (int i = 0; i < 4; i++) { uint32_t c = cwc_club(src[0], P[g][i], &how); ok &= c != 0; q[g][i] = c ? canon_club(c) : 0; }
        } else {
          static const int P[2][4][2] = { { { 0, 1 }, { 1, 2 }, { 0, 3 }, { 1, 4 } }, { { 1, 1 }, { 0, 2 }, { 1, 3 }, { 0, 4 } } };
          for (int g = 0; g < 2; g++) for (int i = 0; i < 4; i++) { uint32_t c = cwc_club(src[P[g][i][0]], P[g][i][1], &how); ok &= c != 0; q[g][i] = c ? canon_club(c) : 0; }
        }
        if (!ok) { logf("fl26swiss: cquad -- a place of the first phase has no club; not made"); g_cq.made = year; }
        else if (g_cql_on) {
          int op = 0;
          for (int g = 0; g < 2; g++) { br_set_list(g_cql[g], q[g], 4); op += br_late_open(g_cql[g]); }
          if (op < 2) logf("fl26swiss: cqleague -- fl26join did not open %d of the two leagues (no rlate line?)", 2 - op);
          uint16_t ids[2] = { g_cql[0], g_cql[1] };
          struct { uint16_t* b; uint16_t* e; uint16_t* c; } rv = { ids, ids + 2, ids + 2 };
          ((regall_fn)(uintptr_t)(g_base + REGALL_RVA))(0, &rv);
          run_flush();
          int ma = br_reg_matches(g_cql[0], year, 0), mb = br_reg_matches(g_cql[1], year, 0);
          g_cq.made = year;
          logf("fl26swiss: cqleague -- day %d: quadrangulares filled from %d table(s) and registered: A (%u) %08x %08x %08x %08x, "
               "B (%u) %08x %08x %08x %08x; match records %d + %d", d, ns, (unsigned)g_cql[0], q[0][0], q[0][1], q[0][2], q[0][3],
               (unsigned)g_cql[1], q[1][0], q[1][1], q[1][2], q[1][3], ma, mb);
          sched_rebuild("cqleague registered");
        }
        else {
          static const uint8_t ALL[] = { 0x21, 0x22, 0x23 };
          br_new_edition(g_cq.reg, ALL, sizeof ALL, year, "cquad");
          orc_register(g_cq.reg, year, "cquad");
          static const int PR[3][2][2] = { { { 0, 1 }, { 2, 3 } }, { { 0, 2 }, { 1, 3 } }, { { 0, 3 }, { 1, 2 } } };
          int made = 0;
          for (int k = 0; k < 3; k++) {
            uint32_t cl[8]; unsigned n = 0;
            for (int g = 0; g < 2; g++) for (int pr = 0; pr < 2; pr++) { cl[n++] = q[g][PR[k][pr][0]]; cl[n++] = q[g][PR[k][pr][1]]; }
            made += br_make_kind(g_cq.reg, CQ_KIND[k], cl, n, g_cq.day[k], g_cq.day[k + 3], "cquad");
          }
          uint32_t all[8]; for (int i = 0; i < 8; i++) all[i] = q[i / 4][i % 4];
          br_list(g_cq.reg, all, 8);
          g_cq.made = year;
          logf("fl26swiss: cquad -- day %d: quadrangulares made from %d table(s): A %08x %08x %08x %08x, B %08x %08x %08x %08x; %d match(es)",
               d, ns, q[0][0], q[0][1], q[0][2], q[0][3], q[1][0], q[1][1], q[1][2], q[1][3], made);
          sched_rebuild("cquad made");
        }
      }
    }
  }
  if (g_cq.fmade != year && d >= g_cq.day[5] && d < g_cq.fday[0]) {
    unsigned char* rnd = ko_round(g_cq.freg, 0x35);
    if (orc_fresh(g_cq.freg, rnd, year)) g_cq.fmade = year;
    else if (cq_over(year)) {
      uint32_t q[2][4]; br_row_t a[4], b[4];
      if (cq_members(year, q)) {
        cq_table(year, 0, q[0], a); cq_table(year, 1, q[1], b);
        /* the better campaign (first phase + quadrangular) hosts leg 2 */
        uint16_t src[CQ_MAXS]; int ns = cq_sources(src);
        uint16_t regs[CQ_MAXS + 2]; int nr = 0;
        for (int s = 0; s < ns; s++) regs[nr++] = src[s];
        if (g_cql_on) { regs[nr++] = g_cql[0]; regs[nr++] = g_cql[1]; } else regs[nr++] = g_cq.reg;
        br_row_t f[2] = { { a[0].club, 0, 0, 0, 0, 0 }, { b[0].club, 0, 0, 0, 0, 1 } };
        if (g_cql_on) br_count(f, 2, regs, nr, year, 0xffff, 0, 0, 1);
        else br_count(f, 2, regs, nr, year, g_cq.reg, CQ_KIND, 3, 1);
        br_sort(f, 2);
        uint32_t cl[2] = { f[1].club, f[0].club };
        static const uint8_t FK[] = { 0x35 };
        br_new_edition(g_cq.freg, FK, 1, year, "cquad final");
        orc_register(g_cq.freg, year, "cquad final");
        int made = br_make_kind(g_cq.freg, 0x35, cl, 2, g_cq.fday[0], g_cq.fday[1], "cquad final");
        br_list(g_cq.freg, cl, 2);
        g_cq.fmade = year;
        logf("fl26swiss: cquad -- day %d: final %08x v %08x (%d match(es)); up: %08x %08x %08x %08x", d, cl[0], cl[1], made,
             a[0].club, a[1].club, b[0].club, b[1].club);
        sched_rebuild("cquad final made");
      }
    }
  }
}
static int cq_promoted(int year, uint32_t* out)
{
  uint32_t q[2][4]; br_row_t a[4], b[4];
  if (!cq_members(year, q) || !cq_over(year)) return 0;
  cq_table(year, 0, q[0], a); cq_table(year, 1, q[1], b);
  out[0] = a[0].club; out[1] = a[1].club; out[2] = b[0].club; out[3] = b[1].club;
  return 4;
}
static int cq_dates(uint64_t reg, void* vec, uint64_t* rv)
{
  if (!g_cq.on || (((uint16_t)reg != g_cq.reg || g_cql_on) && (uint16_t)reg != g_cq.freg)) return 0;
  *rv = ((date_fn)(uintptr_t)g_tramp_date)((reg & ~(uint64_t)0xffff) | 17, vec);
  vec_t* v = (vec_t*)vec;
  size_t have = (v->b && v->e >= v->b) ? (size_t)(v->e - v->b) / sizeof(date_t) : 0;
  date_t* dd = (date_t*)v->b;
  size_t k = 0;
  if ((uint16_t)reg == g_cq.reg && !g_cql_on)
    for (int r = 0; r < 3; r++)
      for (int leg = 0; leg < 2 && k < have; leg++, k++) { dd[k].day = g_cq.day[r + 3 * leg]; dd[k].round = CQ_KIND[r]; dd[k].kind = (uint32_t)leg; }
  else
    for (int leg = 0; leg < 2 && k < have; leg++, k++) { dd[k].day = g_cq.fday[leg]; dd[k].round = 0x35; dd[k].kind = (uint32_t)leg; }
  v->e = v->b + k * sizeof(date_t);
  return 1;
}

/* fl26join's New Year mover asks who goes up from a league of a regional pyramid it moves whole (rgroup
   up=255): the Serie D's groups -> sdko's six; the Serie C's tables -> cquad's four. The season just
   played: this calendar year's records, else last year's (the New Year asks after the year turned).
   Returns the clubs written, 0 not decided / not ours */
__declspec(dllexport) int fl26_swiss_promoted(uint32_t reg, uint32_t* out, int cap)
{
  int year = orc_cal_year();
  if (!out || cap < 6 || year < 0) return 0;
  int isd = g_sd.on && reg == g_sd.reg, isc = 0;
  for (int g = 0; g < g_sd.ng && g_sd.on; g++) isd |= reg == g_sd.g[g];
  for (int s = 0; s < g_cq.ns && g_cq.on; s++) isc |= reg == g_cq.src[s];
  if (g_cq.on && (reg == g_cq.reg || reg == g_cq.freg)) isc = 1;
  if (g_cq.on && g_cql_on && (reg == g_cql[0] || reg == g_cql[1])) isc = 1;
  for (int y = year; y >= year - 1; y--) {
    int n = isd ? sd_promoted(y, out) : isc ? cq_promoted(y, out) : 0;
    if (n) return n;
  }
  return 0;
}
/* the season just closed, for fl26join (a calendar-year season: the year before, in the first days) */
__declspec(dllexport) int fl26_swiss_season_year(void)
{
  int y = orc_cal_year(), d = today();
  return y < 0 ? -1 : d < 60 ? y - 1 : y;
}
/* a round's title key for the kcup title hook: 0xC000 + reg*8 + round, -1 not ours */
static int br_round_key(uint16_t reg, uint32_t kind)
{
  if (g_sd.on && reg == g_sd.reg)
    for (int r = 0; r < BR_ROUNDS; r++) for (int c = 0; c < 2; c++) if (BR_KIND[r][c] && BR_KIND[r][c] == kind) return (int)(0xC000u + reg * 8u + (unsigned)r);
  if (g_cq.on && reg == g_cq.reg && !g_cql_on) {
    for (int r = 0; r < 3; r++) if (CQ_KIND[r] == kind) return (int)(0xC000u + reg * 8u + (unsigned)r);
  }
  if (g_cq.on && reg == g_cq.freg && kind == 0x35) return (int)(0xC000u + reg * 8u);
  return -1;
}
/* a league's shape by season (xline fl26_swiss_rshape <reg> <first year> <clubs> <legs> ...): the record's
   configured clubs (+0x30c low 7 bits) and meetings (+0x308 bits 29-31), written whenever this calendar year is at
   or past the first year and they differ -- each day, and when the league asks for its dates (the Serie C: two
   groups of 14 home and away from 2028). fl26join writes them at New Year too. */
#define BR_SHAPE_MAX 8
static uint16_t g_bsh_reg[BR_SHAPE_MAX], g_bsh_from[BR_SHAPE_MAX]; static uint8_t g_bsh_clubs[BR_SHAPE_MAX], g_bsh_legs[BR_SHAPE_MAX];
static int g_nbsh = 0;
__declspec(dllexport) int fl26_swiss_rshape(const uint32_t* v, int n)
{
  g_nbsh = 0;
  for (int i = 0; v && i + 3 < n && g_nbsh < BR_SHAPE_MAX; i += 4) {
    g_bsh_reg[g_nbsh] = (uint16_t)v[i]; g_bsh_from[g_nbsh] = (uint16_t)v[i + 1];
    g_bsh_clubs[g_nbsh] = (uint8_t)v[i + 2]; g_bsh_legs[g_nbsh] = (uint8_t)v[i + 3]; g_nbsh++;
  }
  logf("fl26swiss: rshape -- %d league shape rule(s) by season", g_nbsh);
  return g_nbsh;
}
static void br_shape(uint16_t reg, const char* when)
{
  for (int k = 0; k < g_nbsh; k++) {
    if (g_bsh_reg[k] != reg) continue;
    unsigned char* rec = get_rec(reg);
    if (!rec) return;
    /* the league's own season year (+0x2fc): the calendar year is not yet the new one when New Year builds it */
    int year = *(uint16_t*)(rec + 0x2fc);
    if (year < 1900 || year > 2999 || year < g_bsh_from[k]) return;
    uint32_t a = *(uint32_t*)(rec + 0x308), b = *(uint32_t*)(rec + 0x30c);
    uint32_t na = (a & ~(7u << 29)) | ((uint32_t)(g_bsh_legs[k] & 7) << 29), nb = (b & ~0x7fu) | (g_bsh_clubs[k] & 0x7f);
    if (na == a && nb == b) return;
    *(uint32_t*)(rec + 0x308) = na; *(uint32_t*)(rec + 0x30c) = nb;
    logf("fl26swiss: rshape -- reg %u set to %u clubs x %u for %d (was %u x %u; %s, day %d)", (unsigned)reg,
         (unsigned)g_bsh_clubs[k], (unsigned)g_bsh_legs[k], year, (unsigned)(b & 0x7f), (unsigned)(a >> 29), when, today());
    return;
  }
}
static void brasil_tick(void)
{
  for (int k = 0; k < g_nbsh; k++) br_shape(g_bsh_reg[k], "day");
  {   /* the shape the leagues of the rules have now, logged when it changes (a probe for the 2028 Serie C) */
    static uint32_t last[BR_SHAPE_MAX];
    for (int k = 0; k < g_nbsh; k++) {
      unsigned char* rec = get_rec(g_bsh_reg[k]);
      if (!rec) continue;
      uint32_t v = ((*(uint32_t*)(rec + 0x30c) & 0x7f) << 24) | ((*(uint32_t*)(rec + 0x308) >> 29) << 16) | *(uint16_t*)(rec + 0x2fc);
      if (v == last[k]) continue;
      last[k] = v;
      logf("fl26swiss: rshape -- reg %u now %u clubs x %u, season stamp %u, %u listed (day %d)", (unsigned)g_bsh_reg[k],
           (unsigned)(v >> 24), (unsigned)((v >> 16) & 0xff), (unsigned)(v & 0xffff), rec_count(rec), today());
    }
  }
  sdko_tick(); cquad_tick();
}
/* the Competition Info round pages (CP_BR_BASE): 250 the D's knockout, 251 the C's quadrangulares, 252 its final */
static int br_cp_reg(int cp)
{
  if (cp == CP_BR_BASE && g_sd.on) return g_sd.reg;
  if (cp == CP_BR_BASE + 1 && g_cq.on && !g_cql_on) return g_cq.reg;
  if (cp == CP_BR_BASE + 2 && g_cq.on) return g_cq.freg;
  return 0xffff;
}
static int br_cp_of(uint16_t reg)
{
  for (int k = 0; k < 3; k++) if (br_cp_reg(CP_BR_BASE + k) == reg) return CP_BR_BASE + k;
  return -1;
}
/* the rounds holding the newest edition's ties, in order: one page each (the D's second phase: two kinds) */
static int br_cp_entries(int cp, uint16_t* reg, uint8_t* kind, uint8_t* round, int max)
{
  int n = 0, r0 = br_cp_reg(cp);
  if (r0 == 0xffff) return 0;
  uint8_t ks[16], rs[16]; int nk = 0;
  if (cp == CP_BR_BASE) { for (int r = 0; r < BR_ROUNDS; r++) for (int c = 0; c < 2; c++) if (BR_KIND[r][c]) { ks[nk] = BR_KIND[r][c]; rs[nk++] = (uint8_t)r; } }
  else if (cp == CP_BR_BASE + 1) { for (int r = 0; r < 3; r++) { ks[nk] = CQ_KIND[r]; rs[nk++] = (uint8_t)r; } }
  else { ks[nk] = 0x35; rs[nk++] = 0; }
  for (int i = 0; i < nk && n < max; i++) {
    unsigned char* rnd = ko_round((uint16_t)r0, ks[i]);
    if (ko_slots(rnd) < 1) continue;
    unsigned char* m = ko_match(*(uint16_t*)(ko_slot(rnd, 0) + 2));
    if (!m || *(uint16_t*)(m + 4) != r0) continue;
    reg[n] = (uint16_t)r0; kind[n] = ks[i]; round[n] = rs[i]; n++;
  }
  return n;
}
