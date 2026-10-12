/* Copa do Nordeste 2026: the group stage's schedule.  Included after cell_at in the 0.2.1 fork build.
 *
 * The group stage is a real cup group phase: a master (nd_reg) and two group rows of ten clubs,
 * nd_reg + 1024 (groups A and B) and nd_reg + 2048 (groups C and D).  Each group row plays only
 * the cross matches, A v B and C v D, once: 25 matches in 5 rounds, every club once a round, A and C
 * at home three times, B and D twice.  The results land in that row's own table, so the screen shows
 * two real tables of ten; the ranking within each group of five is computed (nordeste_engine.h).
 *
 * The configured roster is the 20 team ids in group order A, B, C, D (five each).
 * The game's group builder 0x1413f3c30 only knows groups of four: for our rows group_handler
 * declines (nd_group), the caller falls through to the generic builder, which is gen_handler, and
 * there nd_generate writes the cross matches.  An unexpected roster is refused, never round-robined.
 */
static uint16_t nd_reg, nd_days[5];
static uint16_t nd_show, nd_ko;           /* the shown group stage's master, the knockout (nordeste_engine.h) */
static uint32_t nd_clubs[20];

static int nd_row(uint16_t id) { return !nd_reg ? -1 : id == nd_reg + 1024 ? 0 : id == nd_reg + 2048 ? 1 : -1; }
/* a shown group A-D: 0..3, else -1 */
static int nd_show_group(uint16_t id)
{
  if (!nd_show) return -1;
  for (int g = 0; g < 4; g++) if (id == nd_show + 1024 * (g + 1)) return g;
  return -1;
}

__declspec(dllexport) int fl26_nd_config(uint16_t reg, const uint32_t* clubs, const uint16_t* days)
{
  if (!reg) { nd_reg = 0; return 1; }
  if (!clubs || !days || reg < 176 || reg > 1023 - 0) return 0;
  for (unsigned i = 0; i < 20; i++) {
    if (!clubs[i] || clubs[i] >= (1u << 18)) return 0;
    for (unsigned j = 0; j < i; j++) if (clubs[j] == clubs[i]) return 0;
  }
  for (unsigned i = 0; i < 5; i++)
    if (!days[i] || days[i] >= 365 || (i && days[i] <= days[i - 1])) return 0;
  memcpy(nd_clubs, clubs, sizeof nd_clubs);
  memcpy(nd_days, days, sizeof nd_days);
  nd_reg = reg;
  logf("nordeste: group stage reg %u, rows %u (A/B) and %u (C/D), 10 clubs each, 5 rounds of cross matches",
       reg, reg + 1024u, reg + 2048u);
  return 1;
}

/* Match `index` (0..24) of row `row` (0: A v B, 1: C v D), as indices 0..19 of the roster:
   round r, the i-th club of the first group against club (i + r) % 5 of the second; the first group
   at home in rounds 0, 2 and 4. */
__declspec(dllexport) int fl26_nd_fixture(unsigned row, unsigned index, uint32_t* round, uint32_t* home, uint32_t* away)
{
  if (row > 1 || index >= 25 || !round || !home || !away) return 0;
  unsigned r = index / 5, i = index % 5;
  unsigned a = row * 10 + i, b = row * 10 + 5 + (i + r) % 5;
  *round = r; *home = (r & 1) ? b : a; *away = (r & 1) ? a : b;
  return 1;
}

/* the row's ten handles (in any order) -> map[k] = the list position of roster club row*10 + k */
static int nd_map(unsigned row, const uint32_t* handles, unsigned n, uint8_t* map)
{
  if (!nd_reg || row > 1 || !handles || !map || n != 10) return 0;
  uint32_t found = 0;
  for (unsigned i = 0; i < n; i++) {
    unsigned k = 0;
    while (k < 10 && nd_clubs[row * 10 + k] != (handles[i] >> 14)) k++;
    if (k == 10 || (found & (1u << k))) return 0;
    found |= 1u << k; map[k] = (uint8_t)i;
  }
  return found == 0x3ffu;
}

/* group_handler: 1 when ctx is one of our rows with its exact ten clubs (the caller then declines the
   four-club builder and falls through to gen_handler) */
static int nd_group(void* ctx)
{
  if (!ctx || !nd_reg) return 0;
  vec_t* clubs = (vec_t*)((unsigned char*)ctx + OFF_CLUBS);
  if (!clubs->b || clubs->e < clubs->b) return 0;
  if (clubs->e - clubs->b == 20 && nd_show) {      /* a shown group: its exact five */
    const uint32_t* h = (const uint32_t*)clubs->b;
    for (unsigned g = 0; g < 4; g++) {
      unsigned found = 0;
      for (unsigned i = 0; i < 5; i++)
        for (unsigned k = 0; k < 5; k++) if ((h[i] >> 14) == nd_clubs[g * 5 + k]) found |= 1u << k;
      if (found == 0x1f) return 1;
    }
    return 0;
  }
  if (clubs->e - clubs->b != 40) return 0;
  uint8_t map[10];
  return nd_map(0, (const uint32_t*)clubs->b, 10, map) || nd_map(1, (const uint32_t*)clubs->b, 10, map);
}

static char nd_generate(void* ctx, int row)
{
  if (!ctx) return 0;
  vec_t* clubs = (vec_t*)((unsigned char*)ctx + OFF_CLUBS);
  uint32_t legs = *(uint32_t*)((unsigned char*)ctx + OFF_LEGS);
  uint32_t padded = *(uint32_t*)((unsigned char*)ctx + OFF_PADDED);
  uint8_t map[10];
  if (!clubs->b || clubs->e < clubs->b || clubs->e - clubs->b != 40 || legs != 1 || padded != 10 ||
      !nd_map((unsigned)row, (uint32_t*)clubs->b, 10, map)) {
    logf("nordeste: row %u refused: expected its exact ten clubs, 10 padded, 1 leg (have %u clubs, %u padded, %u legs)",
         (unsigned)(nd_reg + 1024 * (row + 1)), clubs->b && clubs->e >= clubs->b ? (unsigned)((clubs->e - clubs->b) / 4) : 0u,
         padded, legs);
    return 0;
  }
  ((grid_fn)(uintptr_t)(g_base + GRID_RVA))(ctx);
  for (unsigned i = 0; i < 10; i++) for (unsigned j = 0; j < 10; j++) {
    cell_t* c = cell_at(ctx, 0, i, j);
    if (!c) { logf("nordeste: grid allocation failed"); return 0; }
    c->md = 0x37; c->side = 0;
  }
  for (unsigned i = 0; i < 25; i++) {
    uint32_t r, home, away;
    fl26_nd_fixture((unsigned)row, i, &r, &home, &away);
    cell_t* h = cell_at(ctx, 0, map[home - row * 10], map[away - row * 10]);
    cell_t* a = cell_at(ctx, 0, map[away - row * 10], map[home - row * 10]);
    h->md = a->md = r; h->side = 0; a->side = 1;
  }
  *(uint32_t*)((unsigned char*)ctx + OFF_MATCHDAYS) = 5;
  logf("nordeste: row %u -- 25 cross matches in 5 rounds", (unsigned)(nd_reg + 1024 * (row + 1)));
  return 1;
}

/* A shown group (A-D): built, with no match.  The builder's "nothing built" (0) ended the
   registration before the game made the group's table (2026-10-12: register_all reached us, no
   enter_season followed, the table stayed NULL), so the game's grid is made and every cell left
   "no match" (0x37), zero matchdays: the group enters its season, gets its table of five and
   plays nothing -- its matches are the rows'. */
static char nd_generate_empty(void* ctx, uint16_t reg)
{
  if (!ctx) return 0;
  ((grid_fn)(uintptr_t)(g_base + GRID_RVA))(ctx);
  uint32_t legs = *(uint32_t*)((unsigned char*)ctx + OFF_LEGS);
  uint32_t padded = *(uint32_t*)((unsigned char*)ctx + OFF_PADDED);
  unsigned cells = 0;
  for (uint32_t l = 0; l < legs && l < 4; l++)
    for (uint32_t i = 0; i < padded && i < 64; i++)
      for (uint32_t j = 0; j < padded && j < 64; j++) {
        cell_t* c = cell_at(ctx, l, i, j);
        if (c) { c->md = 0x37; c->side = 0; cells++; }
      }
  *(uint32_t*)((unsigned char*)ctx + OFF_MATCHDAYS) = 0;
  static int said;
  if (said++ < 4) logf("nordeste: shown group %u built with no match (%u leg(s), %u padded, %u cells cleared)",
                       (unsigned)reg, legs, padded, cells);
  return 1;
}

/* the five group days, on records borrowed from the Libertadores groups (reg 9) */
static uint64_t nd_dates(uint64_t reg, void* vec)
{
  uint64_t result = ((date_fn)(uintptr_t)g_tramp_date)((reg & ~0xffffull) | 9, vec);
  vec_t* v = (vec_t*)vec;
  size_t n = v && v->b && v->e >= v->b ? (size_t)(v->e - v->b) / sizeof(date_t) : 0;
  if (n < 5 || n > 64) {
    if (v && v->b) v->e = v->b;
    logf("nordeste: incompatible source calendar (%u records); no dates emitted", (unsigned)n);
    return result;
  }
  date_t* dates = (date_t*)v->b;
  for (unsigned i = 0; i < 5; i++) dates[i].day = nd_days[i];
  v->e = v->b + 5 * sizeof(date_t);
  return result;
}
