/* The league-phase draw's association rule, shared by fl26swiss.c and its offline check
 * (swissdraw_test.c). Nothing in here touches the game.
 *
 * The draw table (fl26swiss_table.h) pairs list positions, and the pots are position / 9
 * (position / 6 for the Conference League). key[i] is the association of list position i. The
 * places are reshuffled inside each pot -- pots, home and away counts and the matchdays stay
 * exactly as the table has them -- until no club meets a club of its own association and no club
 * meets more than two clubs of one other association, the UEFA rules.
 *
 * The search is min-conflicts: take a place that is in a conflict, try it against every other
 * place of its pot, keep the best swap (a swap that makes things no worse always, a worse one now
 * and then so the search does not sit in a dead end), and now and then swap two places at random.
 * The seed is the clubs themselves, so the same field always gets the same draw, whenever and
 * however often the builder asks. perm[place] = list position. */
#ifndef FL26SWISS_DRAW_H
#define FL26SWISS_DRAW_H

#ifndef DRAW_STEPS
#define DRAW_STEPS    30000   /* conflict repairs, each up to (pot - 1) evaluations */
#endif
#define DRAW_MAXCLUBS 36

/* 100 per pair of one association, 1 per club and match that is a third (or later) opponent
   from one association. bad[place] (when given) is set for every place in a conflict. */
static int draw_cost(const int* key, const uint8_t* perm, int n, const fl26_pair_t* table, int npairs,
                     uint8_t* bad)
{
  int cost = 0;
  int seen[DRAW_MAXCLUBS][8]; int nseen[DRAW_MAXCLUBS];
  memset(nseen, 0, sizeof nseen);
  if (bad) memset(bad, 0, DRAW_MAXCLUBS);
  for (int k = 0; k < npairs; k++) {
    int h = table[k].home, a = table[k].away;
    if (h >= n || a >= n) continue;
    int kh = key[perm[h]], ka = key[perm[a]];
    if (kh == ka) { cost += 100; if (bad) bad[h] = bad[a] = 1; }
    int same = 0;
    for (int j = 0; j < nseen[h]; j++) if (seen[h][j] == ka) same++;
    if (same >= 2) { cost++; if (bad) bad[h] = bad[a] = 1; }
    same = 0;
    for (int j = 0; j < nseen[a]; j++) if (seen[a][j] == kh) same++;
    if (same >= 2) { cost++; if (bad) bad[h] = bad[a] = 1; }
    if (nseen[h] < 8) seen[h][nseen[h]++] = ka;
    if (nseen[a] < 8) seen[a][nseen[a]++] = kh;
  }
  return cost;
}

static uint32_t draw_next(uint32_t* seed) { *seed = *seed * 1103515245u + 12345u; return *seed >> 8; }

#ifndef DRAW_NODES
#define DRAW_NODES 3000000    /* places tried by the exhaustive search before it gives up */
#endif

/* Depth-first over the places: each place takes a club of its own pot that no placed opponent
   shares an association with and that makes no club meet a third of one association. 1 and
   out[] filled when a draw exists and was found within DRAW_NODES, else 0. */
typedef struct {
  const int* key; int n, pot, order[DRAW_MAXCLUBS], nb[DRAW_MAXCLUBS][8], nnb[DRAW_MAXCLUBS];
  int at[DRAW_MAXCLUBS];                /* place -> list position, -1 while open */
  uint8_t used[DRAW_MAXCLUBS], cand[DRAW_MAXCLUBS][DRAW_MAXCLUBS]; long nodes;
} draw_dfs_t;

static int draw_fits(const draw_dfs_t* s, int x, int c)
{
  int kc = s->key[c], mine[8], nm = 0;
  for (int q = 0; q < s->nnb[x]; q++) {
    int y = s->nb[x][q], cy = s->at[y];
    if (cy < 0) continue;
    int ky = s->key[cy];
    if (ky == kc) return 0;
    int same = 0;
    for (int j = 0; j < nm; j++) same += mine[j] == ky;
    if (same >= 2) return 0;                          /* x would meet a third of ky */
    mine[nm++] = ky;
    same = 0;                                         /* y would meet a third of kc */
    for (int r = 0; r < s->nnb[y]; r++) {
      int z = s->nb[y][r], cz = s->at[z];
      if (z != x && cz >= 0 && s->key[cz] == kc) same++;
    }
    if (same >= 2) return 0;
  }
  return 1;
}

static int draw_dfs(draw_dfs_t* s, int depth)
{
  if (depth == s->n) return 1;
  int x = s->order[depth], lo = x / s->pot * s->pot, hi = lo + s->pot; if (hi > s->n) hi = s->n;
  for (int q = 0; q < hi - lo; q++) {
    int c = s->cand[x][q];
    if (s->used[c] || !draw_fits(s, x, c)) continue;
    if (++s->nodes > DRAW_NODES) return 0;
    s->used[c] = 1; s->at[x] = c;
    if (draw_dfs(s, depth + 1)) return 1;
    s->used[c] = 0; s->at[x] = -1;
    if (s->nodes > DRAW_NODES) return 0;
  }
  return 0;
}

static int draw_exhaustive(const int* key, int n, const fl26_pair_t* table, int npairs, int pot,
                           uint32_t* seed, uint8_t* out)
{
  static draw_dfs_t s;
  memset(&s, 0, sizeof s);
  s.key = key; s.n = n; s.pot = pot;
  for (int k = 0; k < npairs; k++) {
    int h = table[k].home, a = table[k].away;
    if (h >= n || a >= n) continue;
    if (s.nnb[h] < 8) s.nb[h][s.nnb[h]++] = a;
    if (s.nnb[a] < 8) s.nb[a][s.nnb[a]++] = h;
  }
  /* places, each next one the open place with the most placed opponents (ties: lowest) */
  uint8_t placed[DRAW_MAXCLUBS] = { 0 };
  for (int d = 0; d < n; d++) {
    int bx = -1, bn = -1;
    for (int x = 0; x < n; x++) {
      if (placed[x]) continue;
      int m = 0;
      for (int q = 0; q < s.nnb[x]; q++) m += placed[s.nb[x][q]];
      if (m > bn) { bn = m; bx = x; }
    }
    s.order[d] = bx; placed[bx] = 1;
  }
  /* each place tries its pot's clubs in its own shuffled order, so the draw is not always the
     first one the search meets */
  for (int x = 0; x < n; x++) {
    int lo = x / pot * pot, hi = lo + pot; if (hi > n) hi = n;
    for (int q = 0; q < hi - lo; q++) s.cand[x][q] = (uint8_t)(lo + q);
    for (int q = hi - lo - 1; q > 0; q--) {
      int j = (int)(draw_next(seed) % (uint32_t)(q + 1));
      uint8_t t = s.cand[x][q]; s.cand[x][q] = s.cand[x][j]; s.cand[x][j] = t;
    }
    s.at[x] = -1;
  }
  if (!draw_dfs(&s, 0)) return 0;
  for (int x = 0; x < DRAW_MAXCLUBS; x++) out[x] = (uint8_t)(x < n ? s.at[x] : x);
  return 1;
}

/* Fills perm; returns the cost left (0 = both rules hold). *before = the cost of the plain table
   order, *steps_out = repairs made. */
static int draw_spread(const int* key, const uint32_t* clubs, int n, const fl26_pair_t* table, int npairs,
                       int pot, uint8_t* perm, int* before, int* steps_out)
{
  uint8_t cur[DRAW_MAXCLUBS], bad[DRAW_MAXCLUBS], list[DRAW_MAXCLUBS];
  for (int i = 0; i < DRAW_MAXCLUBS; i++) perm[i] = cur[i] = (uint8_t)i;
  uint32_t seed = 2166136261u;
  for (int i = 0; i < n; i++) seed = (seed ^ (clubs[i] >> 14)) * 16777619u;
  int cost = draw_cost(key, cur, n, table, npairs, bad), best = cost, step = 0;
  if (before) *before = cost;
  int npots = (n + pot - 1) / pot;
  for (; step < DRAW_STEPS && best > 0; step++) {
    if (draw_next(&seed) % 64 == 0) {                 /* a random swap inside a random pot */
      int p = (int)(draw_next(&seed) % (uint32_t)npots);
      int lo = p * pot, hi = lo + pot; if (hi > n) hi = n;
      if (hi - lo >= 2) {
        int i = lo + (int)(draw_next(&seed) % (uint32_t)(hi - lo));
        int j = lo + (int)(draw_next(&seed) % (uint32_t)(hi - lo));
        uint8_t s = cur[i]; cur[i] = cur[j]; cur[j] = s;
        cost = draw_cost(key, cur, n, table, npairs, bad);
      }
    } else {
      int nb = 0;
      for (int i = 0; i < n; i++) if (bad[i]) list[nb++] = (uint8_t)i;
      if (!nb) break;
      int x = list[draw_next(&seed) % (uint32_t)nb];
      int lo = x / pot * pot, hi = lo + pot; if (hi > n) hi = n;
      int by = -1, bc = 0x7fffffff, start = (int)(draw_next(&seed) % (uint32_t)(hi - lo));
      for (int q = 0; q < hi - lo; q++) {
        int y = lo + (start + q) % (hi - lo);
        if (y == x) continue;
        uint8_t s = cur[x]; cur[x] = cur[y]; cur[y] = s;
        int c = draw_cost(key, cur, n, table, npairs, 0);
        s = cur[x]; cur[x] = cur[y]; cur[y] = s;
        if (c < bc) { bc = c; by = y; }
      }
      /* the best swap if it is no worse; a worse one one time in eight */
      if (by >= 0 && (bc <= cost || draw_next(&seed) % 8 == 0)) {
        uint8_t s = cur[x]; cur[x] = cur[by]; cur[by] = s;
        cost = draw_cost(key, cur, n, table, npairs, bad);
      }
    }
    if (cost < best) { best = cost; memcpy(perm, cur, sizeof cur); }
  }
  if (best > 0) {
    /* stuck short of zero: an exhaustive search, places taken most-constrained first, within a
       budget -- a field that has an answer the repairs could not reach usually gets it here */
    uint8_t out[DRAW_MAXCLUBS];
    if (draw_exhaustive(key, n, table, npairs, pot, &seed, out)) { memcpy(perm, out, sizeof out); best = 0; }
  }
  if (steps_out) *steps_out = step;
  return best;
}

#endif
