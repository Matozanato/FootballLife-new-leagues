/* Copa do Nordeste 2026: the cup's progression and how it is shown.  Included after the fork's
 * competition helpers.
 *
 * Three masters (2026-10-12, the Info Database to look like the Libertadores'):
 *
 *   nd_reg  (phase 1) the matches: a group master of 20 in a competition of its own, the carrier,
 *           which the Info Database does not list.  Its two group rows (phase 0), A/B and C/D, hold
 *           the cross matches (nordeste_schedule.h).
 *   nd_show (phase 3) the group stage as shown: a group master of 20 in the cup's competition and
 *           four groups of five, A to D.  It has no matches and is never registered; its four tables
 *           are written here from the rows' results, ranked as the cup ranks them.  L1/R1 on the
 *           group page are the game's own.
 *   nd_ko   (phase 2) the knockout: one knockout of eight in the cup's competition, the game's own,
 *           filled in bracket order once the groups are played -- quarter-finals one match (the
 *           one-match test below), semi-finals and final two legs (the row's legs mode 2).
 *
 * The cup's competition is listed once in Brazil's category: its regulations answer the list's
 * country test as a continental competition would (one entry for the competition, opening its
 * menu: Group stage, Knockout stage), not one entry each.
 *
 * Ranking within a group of five (REC 2026): points, wins, goal difference, goals scored, then the
 * disciplinary criteria and a draw.  The disciplinary data is not read yet, so a tie that survives
 * goals scored goes to the draw, seeded by the season and the two clubs -- the same answer after a
 * reload, never a blocked cup.
 */
static uint16_t nd_ko_days[5];
static int nd_busy, nd_last_status;
static int hook(unsigned char* target, const unsigned char* sig, int n, void* handler, unsigned char** tramp_out);
static void* alloc_near(uint64_t base, size_t size);

/* 0 a group row, 1 the matches' master, 2 the knockout, 3 the shown group stage (master or group) */
static int nd_phase_id(uint16_t id)
{
  if (!nd_reg || !nd_show || !nd_ko) return -1;
  if (nd_row(id) >= 0) return 0;
  if (id == nd_reg) return 1;
  if (id == nd_ko) return 2;
  for (unsigned g = 0; g <= 4; g++) if (id == nd_show + 1024 * g) return 3;
  return -1;
}

typedef struct { int played, points, wins, gd, gf; } nd_stat;
typedef struct { uint32_t home, away; uint16_t reg; uint8_t hg, ag, played; } nd_match;

static int nd_slot(uint32_t team) { for (int i = 0; i < 20; i++) if (nd_clubs[i] == team) return i; return -1; }

/* Exported for the regression tests: only the documented match fields are used.  Counts the group
   matches alone (group_only is kept for the tests' signature).  0 for anything that is not a group
   match of this cup as scheduled. */
__declspec(dllexport) int fl26_nd_stats(const nd_match* matches, unsigned n, nd_stat* stats, int group_only)
{
  (void)group_only;
  if (!nd_reg || !matches || !stats || n > 80) return 0;
  memset(stats, 0, 20 * sizeof(*stats));
  for (unsigned m = 0; m < n; m++) {
    const nd_match* r = matches + m;
    if (nd_phase_id(r->reg) != 0) continue;
    int h = nd_slot(r->home), a = nd_slot(r->away);
    if (h < 0 || a < 0 || h == a) return 0;
    int row = nd_row(r->reg), found = 0;
    for (unsigned k = 0; k < 25 && !found; k++) {
      uint32_t round, hh, aa;
      fl26_nd_fixture((unsigned)row, k, &round, &hh, &aa);
      found = hh == (uint32_t)h && aa == (uint32_t)a;
    }
    if (!found) return 0;
    for (unsigned k = 0; k < m; k++)
      if (matches[k].reg == r->reg && matches[k].home == r->home && matches[k].away == r->away) return 0;
    if (!r->played) continue;
    nd_stat* x = stats + h; nd_stat* y = stats + a;
    x->played++; y->played++;
    x->gf += r->hg; y->gf += r->ag;
    x->gd += (int)r->hg - r->ag; y->gd += (int)r->ag - r->hg;
    if (r->hg > r->ag) { x->points += 3; x->wins++; }
    else if (r->hg < r->ag) { y->points += 3; y->wins++; }
    else { x->points++; y->points++; }
  }
  return 1;
}

/* the draw: a fixed answer per season and pair of clubs (a reload decides the same way) */
static uint32_t nd_lot(int season, uint32_t team)
{
  uint32_t x = (uint32_t)season * 2654435761u ^ team * 40503u ^ 0x9e3779b9u;
  x ^= x >> 16; x *= 0x7feb352du; x ^= x >> 15; x *= 0x846ca68bu; x ^= x >> 16;
  return x;
}
static int g_nd_season;
/* 1: a ahead, -1: b ahead; never 0 for two different clubs */
static int nd_compare_ix(const nd_stat* s, int a, int b)
{
  const int av[] = {s[a].points, s[a].wins, s[a].gd, s[a].gf};
  const int bv[] = {s[b].points, s[b].wins, s[b].gd, s[b].gf};
  for (int i = 0; i < 4; i++) if (av[i] != bv[i]) return av[i] > bv[i] ? 1 : -1;
  /* the disciplinary criteria would come here (not read yet): the draw */
  uint32_t la = nd_lot(g_nd_season, nd_clubs[a]), lb = nd_lot(g_nd_season, nd_clubs[b]);
  if (la != lb) return la < lb ? 1 : -1;
  return nd_clubs[a] < nd_clubs[b] ? 1 : -1;
}

/* the group's five, best first (indices into the roster) */
static void nd_order(const nd_stat* s, unsigned group, unsigned* out)
{
  for (unsigned i = 0; i < 5; i++) out[i] = group * 5 + i;
  for (unsigned i = 1; i < 5; i++) {
    unsigned v = out[i], j = i;
    while (j && nd_compare_ix(s, (int)v, (int)out[j - 1]) > 0) { out[j] = out[j - 1]; j--; }
    out[j] = v;
  }
}

/* the quarter-finals A1-C2, B1-D2, C1-A2, D1-B2 (team ids, first named at home); 0 until every group
   match is played.  Exported for the tests. */
__declspec(dllexport) int fl26_nd_quarters(const nd_match* m, unsigned n, uint32_t* out)
{
  nd_stat s[20]; unsigned rank[4][5];
  if (!out || !fl26_nd_stats(m, n, s, 1)) return 0;
  for (unsigned i = 0; i < 20; i++) if (s[i].played != 5) return 0;
  for (unsigned g = 0; g < 4; g++) nd_order(s, g, rank[g]);
  const unsigned cross[4][2] = {{0, 2}, {1, 3}, {2, 0}, {3, 1}};
  for (unsigned k = 0; k < 4; k++) {
    out[2 * k] = nd_clubs[rank[cross[k][0]][0]];
    out[2 * k + 1] = nd_clubs[rank[cross[k][1]][1]];
  }
  return 1;
}

/* The knockout's entry list: the game pairs it in order (first v second ...) and the bracket's
   halves follow the list, so the quarter-finals go in as 1, 4, 2, 3 -- the semi-finals are then
   the winners of quarter-finals 1 v 4 and 2 v 3.  Exported for the tests. */
__declspec(dllexport) int fl26_nd_bracket(const uint32_t* quarters, uint32_t* out)
{
  static const unsigned order[4] = {0, 3, 1, 2};
  if (!quarters || !out) return 0;
  for (unsigned k = 0; k < 4; k++) { out[2 * k] = quarters[2 * order[k]]; out[2 * k + 1] = quarters[2 * order[k] + 1]; }
  return 1;
}

/* A table row (0x14 bytes, docs: "A league-table row, decoded"): +0 the club, +4 the position from
   1, +8 points, +9 six-bit fields won, lost, drawn, a fourth count, then goals for and against in
   twelve bits each, +0xf played.  Exported for the tests. */
__declspec(dllexport) void fl26_nd_row(unsigned char* row, uint32_t club, unsigned position, const nd_stat* s)
{
  memset(row, 0, 20);
  int drawn = s->points - 3 * s->wins;
  int lost = s->played - s->wins - drawn;
  int ga = s->gf - s->gd;
  uint64_t v = (uint64_t)(s->wins & 0x3f) | (uint64_t)(lost & 0x3f) << 6 | (uint64_t)(drawn & 0x3f) << 12 |
               (uint64_t)(s->gf & 0xfff) << 24 | (uint64_t)(ga & 0xfff) << 36;
  *(uint32_t*)row = club;
  *(uint32_t*)(row + 4) = position;
  row[8] = (unsigned char)s->points;
  for (int i = 0; i < 6; i++) row[9 + i] = (unsigned char)(v >> (8 * i));
  row[0xf] = (unsigned char)s->played;
}

/* the four shown groups' tables, written from the results: the game's table of a group (TABLE_RVA)
   has the rows at +0 (count at +0x3c0) and the previous ranking at +0x3c4 (count at +0x784); both
   get the same rows, so no arrows.  A group whose club list is not its five is left alone. */
static int g_nd_tables_ok;                /* how many of the four shown tables the last write filled */
static int nd_tables(const nd_stat* s)
{
  int written = 0;
  for (unsigned g = 0; g < 4; g++) {
    uint16_t rep = (uint16_t)(nd_show + 1024 * (g + 1));
    unsigned char* rec = get_rec(rep);
    unsigned char* t = rec ? ((table_fn)(uintptr_t)(g_base + TABLE_RVA))(rep) : 0;
    static int said[4];
    if (!t || rec_count(rec) != 5) {
      if (said[g]++ < 3)
        logf("nordeste: group %c (%u) not written -- record %p, %u club(s) [%08x %08x %08x %08x %08x], table %p (%u rows)",
             'A' + g, (unsigned)rep, (void*)rec, rec ? rec_count(rec) : 0u,
             rec ? rec_clubs(rec)[0] : 0u, rec ? rec_clubs(rec)[1] : 0u, rec ? rec_clubs(rec)[2] : 0u,
             rec ? rec_clubs(rec)[3] : 0u, rec ? rec_clubs(rec)[4] : 0u, (void*)t, t ? *(uint32_t*)(t + 0x3c0) : 0u);
      continue;
    }
    unsigned order[5]; nd_order(s, g, order);
    unsigned char rows[5][20];
    int ok = 1;
    for (unsigned i = 0; i < 5 && ok; i++) {
      uint32_t h = 0;
      for (unsigned k = 0; k < 5; k++) if ((rec_clubs(rec)[k] >> 14) == nd_clubs[order[i]]) h = rec_clubs(rec)[k];
      if (!h) ok = 0; else fl26_nd_row(rows[i], h, i + 1, s + order[i]);
    }
    if (!ok) {
      if (said[g]++ < 3)
        logf("nordeste: group %c (%u) not written -- its clubs [%08x %08x %08x %08x %08x] are not the roster's five",
             'A' + g, (unsigned)rep, rec_clubs(rec)[0], rec_clubs(rec)[1], rec_clubs(rec)[2], rec_clubs(rec)[3], rec_clubs(rec)[4]);
      continue;
    }
    memcpy(t, rows, sizeof rows);
    *(uint32_t*)(t + 0x3c0) = 5;
    memcpy(t + 0x3c4, rows, sizeof rows);
    *(uint32_t*)(t + 0x784) = 5;
    written++;
  }
  g_nd_tables_ok = written;
  return written;
}

static int nd_read(nd_match* out)
{
  const unsigned char* bs = (const unsigned char*)(g_base + MATCH_BASE_SITE);
  const unsigned char* cs = (const unsigned char*)(g_base + MATCH_CAP_SITE);
  if (bs[0] != 0x48 || bs[1] != 0x8d || bs[2] != 0x88 || cs[0] != 0x81 || cs[1] != 0xff) return -1;
  unsigned base = *(const unsigned*)(bs + 3), cap = *(const unsigned*)(cs + 2);
  unsigned char* o = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
  unsigned char* blk = o ? *(unsigned char**)(o + 0x48) : 0;
  if (!blk || !cap || cap > 200000) return -1;
  int n = 0;
  for (unsigned i = 0; i < cap; i++) {
    const unsigned char* r = blk + base + (size_t)i * MATCH_STRIDE;
    uint16_t id = *(const uint16_t*)(r + 4);
    if (*(const uint16_t*)r == 0xffff || nd_phase_id(id) != 0) continue;
    if (n == 80) return -1;
    out[n++] = (nd_match){ *(const uint32_t*)(r + 0x14) >> 14, *(const uint32_t*)(r + 0x18) >> 14, id,
                           r[0x1c], r[0x1f], !!(r[7] & 0x40) };
  }
  return n;
}

static void nd_set(uint16_t reg, uint32_t* clubs, unsigned n)
{
  u32vec v = {clubs, clubs + n, clubs + n};
  ((setclr_fn)(uintptr_t)g_tramp_setcl)(reg, &v, 1);
}

static void nd_register(uint16_t* ids, unsigned n)
{
  struct { uint16_t* b; uint16_t* e; uint16_t* c; } v = {ids, ids + n, ids + n};
  ((regall_fn)(uintptr_t)(g_base + REGALL_RVA))(0, &v);
  run_flush();
}

/* The shown groups get a table only when they are registered (2026-10-12: unregistered, the game
   had none for them -- TABLE_RVA answered NULL -- and the group page crashed reading it).  Registered
   here: gen_handler builds no match for them (nd_show_group), the table is made with its five. Also
   for a career that started before this (its groups filled, never registered). 1 when all four
   have a table afterwards. */
static int nd_register_shown(void)
{
  uint16_t ids[4]; unsigned n = 0;
  for (unsigned g = 0; g < 4; g++) {
    uint16_t rep = (uint16_t)(nd_show + 1024 * (g + 1));
    unsigned char* rec = get_rec(rep);
    if (rec && rec_count(rec) == 5 && !((table_fn)(uintptr_t)(g_base + TABLE_RVA))(rep)) ids[n++] = rep;
  }
  if (n) nd_register(ids, n);
  int have = 0;
  for (unsigned g = 0; g < 4; g++)
    if (((table_fn)(uintptr_t)(g_base + TABLE_RVA))((uint16_t)(nd_show + 1024 * (g + 1)))) have++;
  if (n) logf("nordeste: %u shown group(s) registered on day %d; %d of 4 now have a table, %d match record(s) in them",
              n, today(), have, ccup_matches(nd_show + 1024) + ccup_matches(nd_show + 2048) +
              ccup_matches(nd_show + 3072) + ccup_matches(nd_show + 4096));
  return have == 4;
}

/* the group stage, as the cups of ours with groups are filled (ccup_fill_one): the clubs on the
   master, the game's group draw (its side effects: the group structures), then each group its own
   clubs.  The matches' rows are registered (their matches through nd_generate); the shown groups
   are not -- they have no matches, only their tables. */
static void nd_start_groups(const uint32_t* handles)
{
  uint32_t all[20], rows[2][10], groups[4][5];
  for (unsigned i = 0; i < 20; i++) { rows[i / 10][i % 10] = handles[i]; groups[i / 5][i % 5] = handles[i]; }
  uint16_t masters[2] = {nd_show, nd_reg};
  for (unsigned m = 0; m < 2; m++) {
    memcpy(all, handles, sizeof all);              /* the draw may reorder the list it is given */
    nd_set(masters[m], all, 20);
    run_flush();
    memcpy(all, handles, sizeof all);
    u32vec w = {all, all + 20, all + 20};
    ((gdraw_fn)(uintptr_t)(g_base + GDRAW_RVA))(masters[m], &w, 1);
    run_flush();
  }
  for (unsigned g = 0; g < 4; g++) { nd_set((uint16_t)(nd_show + 1024 * (g + 1)), groups[g], 5); run_flush(); }
  uint16_t ids[2] = {(uint16_t)(nd_reg + 1024), (uint16_t)(nd_reg + 2048)};
  for (unsigned r = 0; r < 2; r++) { nd_set(ids[r], rows[r], 10); run_flush(); }
  nd_register(ids, 2);
  nd_register_shown();
  nd_stat zero[20]; memset(zero, 0, sizeof zero);
  int t = nd_tables(zero);
  logf("nordeste: group stage filled on day %d -- rows %u and %u, %d and %d match record(s); groups A-D (%u..%u) shown, %d table(s) written",
       today(), (unsigned)ids[0], (unsigned)ids[1], ccup_matches(ids[0]), ccup_matches(ids[1]),
       (unsigned)(nd_show + 1024), (unsigned)(nd_show + 4096), t);
}

static void nd_start_ko(const uint32_t* list)
{
  uint32_t clubs[8];
  memcpy(clubs, list, sizeof clubs);
  nd_set(nd_ko, clubs, 8);
  run_flush();
  start_stage(0, nd_ko);
  run_flush();
  int made = ccup_matches(nd_ko);
  if (!made) { uint16_t id = nd_ko; nd_register(&id, 1); made = ccup_matches(nd_ko); }
  logf("nordeste: knockout %u started on day %d with %u clubs, %d match record(s) (first tie %08x v %08x)",
       (unsigned)nd_ko, today(), rec_count(get_rec(nd_ko)), made, clubs[0], clubs[1]);
}

static void nd_status(int code)
{
  if (code != nd_last_status)
    logf("nordeste: status %d (1=groups,2=knockout,-3=missing result,-4=calendar missed)", code);
  nd_last_status = code;
}

static int g_nd_tab_day = -1, g_nd_tab_played = -1;
static void nd_tick(void)
{
  if (!g_base || !nd_reg || !nd_show || !nd_ko || nd_busy || !g_tramp_setcl) return;
  int day = today();
  if (day < 1 || day > nd_ko_days[4] + 1) return;
  if (!get_rec(nd_reg) || !get_rec(nd_reg + 1024) || !get_rec(nd_reg + 2048) || !get_rec(nd_ko)) return;
  for (unsigned g = 0; g <= 4; g++) if (!get_rec(nd_show + 1024 * g)) return;
  nd_busy = 1;
  g_nd_season = season_year();
  nd_match matches[80]; int n = nd_read(matches);
  if (n < 0) goto done;
  if (!n) {
    if (day >= nd_days[0]) { nd_status(-4); goto done; }
    uint32_t handles[20];
    for (unsigned i = 0; i < 20; i++) { handles[i] = club_any(nd_clubs[i]); if (!club_valid(handles[i])) goto done; }
    nd_start_groups(handles);
    nd_status(1); goto done;
  }
  nd_stat s[20];
  if (!fl26_nd_stats(matches, n, s, 1)) goto done;
  int played = 0;
  for (int i = 0; i < n; i++) played += matches[i].played;
  if (played != g_nd_tab_played || day != g_nd_tab_day) {   /* a reload or a result: the tables again */
    static int tried_day = -1;
    if (tried_day != day) { tried_day = day; nd_register_shown(); }
    int t = nd_tables(s);
    if (played != g_nd_tab_played) logf("nordeste: day %d -- %d group match(es) played, %d table(s) written", day, played, t);
    g_nd_tab_played = played; g_nd_tab_day = day;
  }
  if (played < 50 || n != 50) { nd_status(1); goto done; }
  /* started: its matches this season -- not its club list, which the New Year teardown leaves
     as last season's (2026-10-12: the second season's knockout was never started) */
  if (ccup_matches(nd_ko) > 0) { nd_status(2); goto done; }
  if (day >= nd_ko_days[0]) { nd_status(-4); goto done; }
  uint32_t q[8], list[8];
  if (fl26_nd_quarters(matches, n, q) != 1) { nd_status(-3); goto done; }
  fl26_nd_bracket(q, list);
  for (unsigned k = 0; k < 8; k++) { list[k] = club_any(list[k]); if (!club_valid(list[k])) goto done; }
  nd_start_ko(list);
  nd_status(2);
done:
  nd_busy = 0;
}

/* the cup's current phase: the shown groups, then the knockout once it has matches */
static uint64_t nd_current(uint64_t comp, uint64_t original)
{
  if (!nd_reg || !nd_show || !nd_ko) return original;
  unsigned char* r = find_rec(nd_show);
  if (!r || *(uint32_t*)(r + 0x80) != (uint32_t)comp) return original;
  if (ccup_matches(nd_ko) > 0) return (original & ~0xffffull) | nd_ko;
  return (original & ~0xffffull) | nd_show;
}

/* ---- the menu while the shown groups have no table: Standings greyed ----
   The competition's menu (0x14151f5f0) asks the phase of each kind for its items; a group stage
   whose tables do not exist crashed the page (2026-10-12, a fast-fail: the shown groups were never
   registered). So until all four tables are written (from day 1, 0 points), a kind-2 ask from the menu hears "no
   such phase" -- the answer that greys an item.  Every (caller, kind) of the cup is logged once. */
#define ND_MENU_LO 0x151f5f0
#define ND_MENU_HI 0x1520000
static uint64_t nd_menu_kind(const uint32_t* comp, uint64_t kind, uint64_t r, uintptr_t ra)
{
  if (!comp || !nd_show) return r;
  unsigned char* g = find_rec(nd_show);
  if (!g || *(uint32_t*)(g + 0x80) != *comp) return r;
  uint64_t out = r;
  int menu = ra >= g_base + ND_MENU_LO && ra < g_base + ND_MENU_HI;
  if (menu && (uint32_t)kind == 2 && g_nd_tables_ok < 4) out = r | 0xffff;
  static uintptr_t seen[24]; static uint32_t seenk[24], seeno[24]; static int nseen;
  int known = 0;
  for (int q = 0; q < nseen; q++) if (seen[q] == ra && seenk[q] == (uint32_t)kind && seeno[q] == (uint16_t)out) known = 1;
  if (!known && nseen < 24) {
    seen[nseen] = ra; seenk[nseen] = (uint32_t)kind; seeno[nseen] = (uint16_t)out; nseen++;
    logf("nordeste: Copa do Nordeste -- kind %u asked from %llx: the game %04x, given %04x", (unsigned)kind,
         (unsigned long long)(ra - g_base + 0x140000000ull), (unsigned)(uint16_t)r, (unsigned)(uint16_t)out);
  }
  return out;
}

/* the knockout's records, borrowed from the Libertadores knockout (reg 10: round of 16, quarter-,
   semi-finals two legs, the final one) and made into the cup's five: the quarter-finals one match
   (kind 2), the semi-finals and the final two legs (kinds 0 and 1).  Rounds 0x2e 0x34 0x35: the
   game numbers a knockout's first round 0x2e whatever the field (read live 2026-10-12: the eight's
   quarter-final records are round 0x2e, the semi-finals 0x34, the final 0x35; dated as 0x33 the
   quarter-finals stayed undated, state 3, and two legs). */
#define ND_KO_LIKE 10
static uint64_t nd_phase_dates(uint64_t reg, void* vec)
{
  int p = nd_phase_id((uint16_t)reg);
  if (p == 0) return nd_dates(reg, vec);
  if (p != 2) {                                       /* the masters and the shown groups: no dates */
    uint64_t result = ((date_fn)(uintptr_t)g_tramp_date)((reg & ~0xffffull) | 9, vec);
    vec_t* v = (vec_t*)vec;
    if (v && v->b && v->e >= v->b) v->e = v->b;
    return result;
  }
  uint64_t result = ((date_fn)(uintptr_t)g_tramp_date)((reg & ~0xffffull) | ND_KO_LIKE, vec);
  vec_t* v = (vec_t*)vec;
  if (!v || !v->b || v->e < v->b) return result;
  size_t have = (size_t)(v->e - v->b) / sizeof(date_t);
  static int said;
  if (have < 5) {
    v->e = v->b;
    if (!said++) logf("nordeste: knockout %u -- reg %u gave %u record(s), 5 wanted; no dates", (unsigned)nd_ko, ND_KO_LIKE, (unsigned)have);
    return result;
  }
  static const uint32_t round[5] = {0x2e, 0x34, 0x34, 0x35, 0x35}, kind[5] = {2, 0, 1, 0, 1};
  date_t* d = (date_t*)v->b;
  for (unsigned i = 0; i < 5; i++) { d[i].day = nd_ko_days[i]; d[i].round = round[i]; d[i].kind = kind[i]; }
  v->e = v->b + 5 * sizeof(date_t);
  if (!said++) logf("nordeste: knockout %u dated: quarter-finals %u, semi-finals %u/%u, final %u/%u", (unsigned)nd_ko,
                    nd_ko_days[0], nd_ko_days[1], nd_ko_days[2], nd_ko_days[3], nd_ko_days[4]);
  return result;
}

/* ---- the quarter-finals one match: the tie builder asks 0x14151d1e0(reg, round) whether a round
   is one match; the knockout's legs mode (2, every round two legs) answers no, so the quarter-final
   round of ours (0x2e, the first round) is answered yes and everything else asks the game ---- */
#define ONEMATCH_RVA 0x151d1e0
static const unsigned char SIG_ONEMATCH[15] = {
  0x48, 0x89, 0x5c, 0x24, 0x08, 0x48, 0x89, 0x6c, 0x24, 0x10, 0x48, 0x89, 0x74, 0x24, 0x18 };
typedef char (*onematch_fn)(uint64_t reg, uint64_t round);
unsigned char* g_tramp_onematch = 0;
char nd_onematch(uint64_t reg, uint64_t round)
{
  if (nd_ko && (uint16_t)reg == nd_ko && (uint32_t)round == 0x2e) return 1;
  return ((onematch_fn)(uintptr_t)g_tramp_onematch)(reg, round);
}

/* ---- the Info Database lists the cup once ----
   Both lists of a category (0x140acd3f0 and its neighbour at 0x140acce1f, 0x140c6a540 through
   0x140c6bd60) give a regulation in a country's region an entry of its own and one in an
   international region one entry per competition; the region is the record's +0x30c bits 7-12 and
   the test 0x1414cf160.  At the three tests the record is in rax: each `mov ecx,[rax+0x30c]; shr
   ecx,7; and ecx,0x3f; call 0x1414cf160` becomes `mov rcx,rax; call stub` to nd_country(record),
   which says "not a country" for the cup's competition and asks the test for everything else. */
#define REGION_TEST_RVA 0x14cf160
static const uint32_t REGION_SITES[3] = {0xacce1f, 0xacd68f, 0xc6bdac};
typedef char (*region_fn)(uint64_t region);
uint64_t nd_country(unsigned char* rec)
{
  uint32_t region = rec ? (*(uint32_t*)(rec + 0x30c) >> 7) & 0x3f : 0;
  if (rec && nd_show) {
    unsigned char* g = find_rec(nd_show);
    if (g && *(uint32_t*)(rec + 0x80) == *(uint32_t*)(g + 0x80)) {
      static int said;
      if (!said++) logf("nordeste: Info Database -- competition %u listed once, as a continental one", *(uint32_t*)(g + 0x80));
      return 0;
    }
  }
  return (uint64_t)(unsigned char)((region_fn)(uintptr_t)(g_base + REGION_TEST_RVA))(region);
}
static int nd_region_patch(void)
{
  unsigned char want[17] = {0x8b, 0x88, 0x0c, 0x03, 0x00, 0x00, 0xc1, 0xe9, 0x07, 0x83, 0xe1, 0x3f, 0xe8};
  for (int i = 0; i < 3; i++) {
    unsigned char* s = (unsigned char*)(uintptr_t)(g_base + REGION_SITES[i]);
    int32_t rel = (int32_t)((int64_t)(g_base + REGION_TEST_RVA) - (int64_t)(uintptr_t)(s + 17));
    memcpy(want + 13, &rel, 4);
    if (memcmp(s, want, 17)) return 10 + i;
  }
  unsigned char* stub = (unsigned char*)alloc_near(g_base, 0x40);
  if (!stub) return 3;
  stub[0] = 0xff; stub[1] = 0x25; *(uint32_t*)(stub + 2) = 0; *(uint64_t*)(stub + 6) = (uint64_t)(uintptr_t)nd_country;
  for (int i = 0; i < 3; i++) {
    unsigned char* s = (unsigned char*)(uintptr_t)(g_base + REGION_SITES[i]);
    DWORD old;
    if (!VirtualProtect(s, 17, PAGE_EXECUTE_READWRITE, &old)) return 4;
    s[0] = 0x48; s[1] = 0x8b; s[2] = 0xc8;                                   /* mov rcx, rax */
    s[3] = 0xe8; *(int32_t*)(s + 4) = (int32_t)((int64_t)(uintptr_t)stub - (int64_t)(uintptr_t)(s + 8));
    memset(s + 8, 0x90, 9);
    VirtualProtect(s, 17, old, &old);
    FlushInstructionCache(GetCurrentProcess(), s, 17);
  }
  return 0;
}

/* ---- who asks for the matches' tables of ten (diagnosis, 2026-10-12) ----
   The table shown after a match of the cup (the calendar) was the row's, A/B or C/D, ten clubs.
   TABLE_RVA is a 5-byte `jmp 0x14158b6f0`; its target is pointed at a stub here that logs, once per
   caller, a lookup of a group row's table, and then asks 0x14158b6f0 as before.  The callers are
   what the next step redirects to the shown groups' tables. */
#define TABLE_TARGET_RVA 0x158b6f0
uint64_t nd_table_seen(uint64_t reg)
{
  uint64_t t = ((uint64_t (*)(uint64_t))(uintptr_t)(g_base + TABLE_TARGET_RVA))(reg);
  if (nd_row((uint16_t)reg) >= 0) {
    uintptr_t ra = (uintptr_t)__builtin_return_address(0);
    static uintptr_t seen[32]; static int nseen;
    int known = 0;
    for (int q = 0; q < nseen; q++) if (seen[q] == ra) known = 1;
    if (!known && nseen < 32) {
      seen[nseen++] = ra;
      logf("nordeste: table of row %u asked from %llx (day %d)", (unsigned)(uint16_t)reg,
           (unsigned long long)(ra - g_base + 0x140000000ull), today());
    }
  }
  return t;
}
static int nd_table_patch(void)
{
  unsigned char* s = (unsigned char*)(uintptr_t)(g_base + TABLE_RVA);
  if (s[0] != 0xe9 || (uint64_t)(uintptr_t)(s + 5) + *(int32_t*)(s + 1) != g_base + TABLE_TARGET_RVA) return 2;
  unsigned char* stub = (unsigned char*)alloc_near(g_base, 0x40);
  if (!stub) return 3;
  stub[0] = 0xff; stub[1] = 0x25; *(uint32_t*)(stub + 2) = 0; *(uint64_t*)(stub + 6) = (uint64_t)(uintptr_t)nd_table_seen;
  DWORD old;
  if (!VirtualProtect(s, 5, PAGE_EXECUTE_READWRITE, &old)) return 4;
  *(int32_t*)(s + 1) = (int32_t)((int64_t)(uintptr_t)stub - (int64_t)(uintptr_t)(s + 5));
  VirtualProtect(s, 5, old, &old);
  FlushInstructionCache(GetCurrentProcess(), s, 5);
  return 0;
}

/* ---- the menu's Knockout stage item ----
   It is live when 0x14151c5e0(comp) says the competition is past its groups: the group phase that
   leads to a knockout (+0x78) has to read finished (0x141546c70).  The shown groups play nothing
   and never finish, so the item stayed grey with the quarter-finals played (2026-10-12, day 142).
   For the cup: past its groups once the knockout has its matches; anything else asks the game. */
#define PASTGRP_RVA 0x151c5e0
static const unsigned char SIG_PASTGRP[22] = {      /* push rsi carries a REX byte (40 56) */
  0x40, 0x56, 0x57, 0x41, 0x54, 0x41, 0x56, 0x41, 0x57, 0x48, 0x83, 0xec, 0x40,
  0x48, 0xc7, 0x44, 0x24, 0x20, 0xfe, 0xff, 0xff, 0xff };
typedef uint64_t (*pastgrp_fn)(uint32_t* comp);
unsigned char* g_tramp_pastgrp = 0;
static int nd_cup_comp(uint32_t comp);
uint64_t nd_pastgrp(uint32_t* comp)
{
  uint64_t r = ((pastgrp_fn)(uintptr_t)g_tramp_pastgrp)(comp);
  if (!comp || IsBadReadPtr(comp, 4) || !nd_cup_comp(*comp)) return r;
  uint64_t out = ccup_matches(nd_ko) > 0 ? 1 : 0;
  static int said = -1;
  if (said != (int)out) {
    said = (int)out;
    logf("nordeste: Knockout stage item %s (the game said %d)", out ? "live: the knockout has its matches" : "grey: no knockout yet",
         (int)(uint8_t)r);
  }
  return (r & ~0xffull) | out;
}

/* ---- the season's clash audit, logged at the calendar-year teardown ----
   Every dated match of the season still in the match table: a club with two matches on one day is
   counted and the first cases logged (club, date, the two regulations).  Read only; 2026-10-12, so
   that every New Year says what a hand-run scan of memory said (24 clashes, then 7, then 0). */
static void season_clash_audit(void)
{
  const unsigned char* bs = (const unsigned char*)(g_base + MATCH_BASE_SITE);
  const unsigned char* cs = (const unsigned char*)(g_base + MATCH_CAP_SITE);
  if (bs[0] != 0x48 || bs[1] != 0x8d || bs[2] != 0x88 || cs[0] != 0x81 || cs[1] != 0xff) return;
  unsigned base = *(const unsigned*)(bs + 3), cap = *(const unsigned*)(cs + 2);
  unsigned char* o = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
  unsigned char* blk = o ? *(unsigned char**)(o + 0x48) : 0;
  if (!blk || !cap || cap > 200000) return;
  /* (club, day) pairs of every dated match, sorted; a club and day twice is a clash */
  static uint64_t keys[2 * 200000];
  unsigned nk = 0, matches = 0;
  for (unsigned i = 0; i < cap; i++) {
    const unsigned char* r = blk + base + (size_t)i * MATCH_STRIDE;
    if (*(const uint16_t*)r == 0xffff) continue;
    uint16_t y = *(const uint16_t*)(r + 8); uint8_t m = r[10], d = r[11];
    if (y == 0xffff || !m || m > 12 || !d) continue;
    matches++;
    uint32_t day = (uint32_t)y * 400 + m * 32 + d;
    for (int side = 0; side < 2; side++) {
      uint32_t c = *(const uint32_t*)(r + 0x14 + 4 * side);
      if (c == 0xffffffffu || !(c >> 14)) continue;
      keys[nk++] = ((uint64_t)(c >> 14) << 40) | ((uint64_t)day << 20) | i;
    }
  }
  /* shell sort: a season is ~20000 entries */
  for (unsigned gap = nk / 2; gap; gap /= 2)
    for (unsigned i = gap; i < nk; i++) {
      uint64_t v = keys[i]; unsigned j = i;
      while (j >= gap && keys[j - gap] > v) { keys[j] = keys[j - gap]; j -= gap; }
      keys[j] = v;
    }
  unsigned clashes = 0, shown = 0;
  for (unsigned i = 1; i < nk; i++) {
    if ((keys[i] >> 20) != (keys[i - 1] >> 20)) continue;
    if (i >= 2 && (keys[i - 1] >> 20) == (keys[i - 2] >> 20)) continue;   /* a third match counted once */
    clashes++;
    if (shown < 12) {
      const unsigned char* a = blk + base + (size_t)(keys[i - 1] & 0xfffff) * MATCH_STRIDE;
      const unsigned char* b = blk + base + (size_t)(keys[i] & 0xfffff) * MATCH_STRIDE;
      logf("fl26swiss: clash -- team %u on %u-%02u-%02u: regulation %u and %u", (unsigned)(keys[i] >> 40),
           *(const uint16_t*)(a + 8), a[10], a[11], *(const uint16_t*)(a + 4), *(const uint16_t*)(b + 4));
      shown++;
    }
  }
  logf("fl26swiss: season clash audit -- %u dated match(es), %u club-day(s) with two matches", matches, clashes);
}

/* a club of the cup's roster (a team id): the fictional ones are in the Other Latin American
   pool, and the Libertadores' pool swap took ASA and ABC into its groups (2026-10-12) */
static int nd_roster(uint32_t team) { return nd_reg && team && nd_slot(team) >= 0; }

/* the cup's days for the leagues of its country (home_cup_days): a league of the region of the
   cup's matches keeps its rounds off them -- the Brasileirao met the semi-final of 27 May
   (2026-10-12) */
static int nd_league_days(uint32_t region, uint16_t* out, int max)
{
  if (!nd_reg || max <= 0) return 0;
  unsigned char* m = find_rec(nd_reg);
  if (!m || ((*(uint32_t*)(m + 0x30c) >> 7) & 0x3f) != region) return 0;
  int n = 0;
  for (int i = 0; i < 5 && n < max; i++) if (nd_days[i]) out[n++] = nd_days[i];
  for (int i = 0; i < 5 && n < max; i++) if (nd_ko_days[i]) out[n++] = nd_ko_days[i];
  return n;
}

/* the cup's own competition (the one listed): its goal and assist rankings count the carrier's
   matches in (rank_build, hasrank_handler) */
static int nd_cup_comp(uint32_t comp)
{
  if (!nd_show) return 0;
  unsigned char* g = find_rec(nd_show);
  return g && *(uint32_t*)(g + 0x80) == comp;
}

/* the carrier: the competition holding the matches, left out of the Info Database (skipph_handler) */
static int nd_hidden_comp(uint32_t comp)
{
  if (!nd_reg) return 0;
  unsigned char* m = find_rec(nd_reg);
  return m && *(uint32_t*)(m + 0x80) == comp;
}

/* phases: the shown group stage's master, the matches' master, the knockout (ids < 1024);
   clubs: the 20 team ids in group order A, B, C, D; days: the five group rounds, the quarter-final,
   the semi-finals' two legs and the final's two */
__declspec(dllexport) int fl26_nd_engine_config(const uint16_t* phases, const uint32_t* clubs, const uint16_t* days)
{
  if (!phases || !clubs || !days) return 0;
  for (unsigned i = 0; i < 3; i++) {
    if (phases[i] < 176 || phases[i] >= 1024) return 0;
    for (unsigned j = 0; j < i; j++) if (phases[i] == phases[j]) return 0;
  }
  for (unsigned i = 0; i < 10; i++) if (!days[i] || days[i] >= 365 || (i && days[i] <= days[i - 1])) return 0;
  if (!fl26_nd_config(phases[1], clubs, days)) return 0;
  nd_show = phases[0]; nd_ko = phases[2];
  memcpy(nd_ko_days, days + 5, sizeof nd_ko_days);
  logf("nordeste: groups shown %u (A-D %u..%u), matches %u (+%u, +%u), knockout %u", (unsigned)nd_show,
       (unsigned)(nd_show + 1024), (unsigned)(nd_show + 4096), (unsigned)nd_reg, (unsigned)(nd_reg + 1024),
       (unsigned)(nd_reg + 2048), (unsigned)nd_ko);
  return 1;
}

/* the two patches of the cup's own: the one-match quarter-finals and the Info Database's one entry.
   1 when both are in */
__declspec(dllexport) int fl26_nd_engine_install(void)
{
  if (!g_base || !nd_reg || !nd_ko) return 0;
  int a = g_tramp_onematch ? 0 : hook((unsigned char*)(uintptr_t)(g_base + ONEMATCH_RVA), SIG_ONEMATCH, 15,
                                     (void*)nd_onematch, &g_tramp_onematch);
  static int b = -1, c = -1;
  if (b != 0) b = nd_region_patch();
  if (c != 0) c = nd_table_patch();
  int e = g_tramp_pastgrp ? 0 : hook((unsigned char*)(uintptr_t)(g_base + PASTGRP_RVA), SIG_PASTGRP, 22,
                                    (void*)nd_pastgrp, &g_tramp_pastgrp);
  logf("nordeste: one-match quarter-finals %s (%d), Info Database single entry %s (%d), row table log %s (%d), knockout item %s (%d)",
       a ? "NOT installed" : "live", a, b ? "NOT installed" : "live", b, c ? "NOT installed" : "live", c,
       e ? "NOT installed" : "live", e);
  return !a && !b;
}
