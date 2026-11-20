/* zig cc -O2 -fno-sanitize=undefined test_group_assign.c -o test_group_assign.exe && test_group_assign.exe
   16.11.2026 (mato: "klubovi moraju po regijama ispadati ... kao u stvarnosti"): who goes to which
   group of a set, without the game. group_assign over plain arrays (the relegated clubs' homes,
   the guests, the border clubs, each group's places) and group_plan over hand-made leagues (no
   game memory: the standings and lists are filled here, the homes through fl26_chain_ghomes, the
   border clubs through fl26_chain_gborders). Every group_plan case also checks the invariants:
   every league keeps its size, no club in two leagues, no club missing, as many down as up.
   (tools/test_group_assign.py builds and runs it.) */
#include "fl26chain.c"
#include <stdlib.h>

static int fails;
static void check(const char* what, int ok)
{
  if (!ok) { printf("FAIL: %s\n", what); fails++; }
  else printf("ok: %s\n", what);
}

/* ---- group_assign alone ---- */
static ga_item_t rel(uint64_t home) { ga_item_t e; memset(&e, 0, sizeof e); e.kind = GA_REL; e.home = home; e.cur = -1; return e; }
static ga_item_t guest(int cur, uint64_t home) { ga_item_t e; memset(&e, 0, sizeof e); e.kind = GA_GUEST; e.home = home; e.cur = cur; return e; }
static ga_item_t border(int cur, uint64_t home, int to) { ga_item_t e = guest(cur, home); e.kind = GA_BORDER; e.nto = 1; e.to[0] = to; return e; }
#define B(t) (1ull << (t))

/* the rule before 16.11.2026, for comparison: one pass in table order, home if it still has a
   place, else the group with the most places left (the first on a tie) */
static int greedy_home(int nt, const int* free_, const ga_item_t* it, int ni)
{
  int room[64], home = 0;
  for (int t = 0; t < nt; t++) room[t] = free_[t];
  for (int i = 0; i < ni; i++) {
    int best = -1;
    for (int t = 0; t < nt && best < 0; t++) if ((it[i].home >> t & 1) && room[t] > 0) best = t;
    if (best >= 0) home++;
    else for (int t = 0; t < nt; t++) if (room[t] > 0 && (best < 0 || room[t] > room[best])) best = t;
    if (best >= 0) room[best]--;
  }
  return home;
}
static int count_home(const ga_item_t* it, int ni, const int* ch)
{
  int k = 0;
  for (int i = 0; i < ni; i++) if (it[i].kind == GA_REL && ch[i] >= 0) k++;
  return k;
}
/* every place used once: the relegated left over fit exactly the places left */
static int places_ok(int nt, const int* free_, const ga_item_t* it, int ni, const int* ch, const int* avail)
{
  int left = 0, away = 0, a[64];
  for (int t = 0; t < nt; t++) a[t] = free_[t];
  for (int i = 0; i < ni; i++) {
    if (ch[i] < 0) { if (it[i].kind == GA_REL) away++; continue; }
    if (it[i].kind == GA_REL && !(it[i].home >> ch[i] & 1)) return 0;      /* home means home */
    if (it[i].kind == GA_GUEST && !(it[i].home >> ch[i] & 1)) return 0;
    a[ch[i]]--;
    if (it[i].kind != GA_REL) a[it[i].cur]++;
  }
  for (int t = 0; t < nt; t++) { if (a[t] < 0 || a[t] != avail[t]) return 0; left += a[t]; }
  return left == away;
}

/* the most relegated clubs at home, by trying every choice (small cases only) */
static int brute_best(int nt, const int* free_, const ga_item_t* it, int ni, int i, int* a)
{
  if (i == ni) { for (int t = 0; t < nt; t++) if (a[t] < 0) return -1000; return 0; }
  int best = brute_best(nt, free_, it, ni, i + 1, a);          /* not home / stays */
  for (int t = 0; t < nt; t++) {
    if (!(it[i].home >> t & 1) || (it[i].kind != GA_REL && t == it[i].cur)) continue;
    a[t]--; if (it[i].kind != GA_REL) a[it[i].cur]++;
    int v = brute_best(nt, free_, it, ni, i + 1, a) + (it[i].kind == GA_REL);
    if (v > best) best = v;
    a[t]++; if (it[i].kind != GA_REL) a[it[i].cur]--;
  }
  return best;
}

/* ---- group_plan over hand-made leagues ---- */
static gl_t G[16];
static void mk(int k, uint16_t id, int first_team, int n)
{
  memset(&G[k], 0, sizeof G[k]);
  G[k].id = id;
  for (int i = 0; i < n; i++) G[k].stand[i] = G[k].list[i] = (uint32_t)(first_team + i) << 14;
  G[k].nstand = G[k].nlist = n;
}
static uint32_t T(int team) { return (uint32_t)team << 14; }
static uint32_t pout[2 * MAX_GSIDE][MAX_CLUBS]; static int pnout[2 * MAX_GSIDE];
static gmove_t pmv[GMOVE_MAX]; static int pnmv;
/* one plan: nup upper leagues G[0..nup), nlow groups after them; n[] the counts. Checks the
   invariants and returns 0, or -1 (refused) */
static int plan(int nup, int nlow, const int* n, const uint32_t* po, int npo, const char* tag)
{
  gl_t* m[2 * MAX_GSIDE]; int pref[2 * MAX_GSIDE], flips = 0, cut = 0; char why[200];
  int nm = nup + nlow;
  for (int k = 0; k < nm; k++) { m[k] = &G[k]; pref[k] = k >= nup ? 0 : -1; }
  int r = group_plan(m, n, pref, nup, nlow, po, npo, 0, 0, 0, 0, 0, pout, pnout, &flips, pmv, &pnmv, &cut, why, sizeof why);
  if (r) { printf("  %s: refused -- %s\n", tag, why); return -1; }
  int sizes = 1, dup = 0, missing = 0, down = 0, up = 0;
  for (int k = 0; k < nm; k++) if (pnout[k] != G[k].nlist) sizes = 0;
  for (int a = 0; a < nm; a++) for (int i = 0; i < pnout[a]; i++) {
    for (int b = a; b < nm; b++) for (int j = (b == a ? i + 1 : 0); j < pnout[b]; j++) if (pout[a][i] == pout[b][j]) dup = 1;
  }
  for (int a = 0; a < nm; a++) for (int i = 0; i < G[a].nlist; i++) {
    int f = 0;
    for (int b = 0; b < nm && !f; b++) f = in_list(pout[b], pnout[b], G[a].list[i]);
    if (!f) missing = 1;
  }
  for (int q = 0; q < pnmv; q++) {
    int fu = 0, tu = 0;
    for (int k = 0; k < nup; k++) { if (G[k].id == pmv[q].from) fu = 1; if (G[k].id == pmv[q].to) tu = 1; }
    if (fu && !tu) down++;
    if (!fu && tu) up++;
  }
  char w[160];
  snprintf(w, sizeof w, "%s: every league keeps its size, no club twice, none missing, %d down = %d up", tag, down, up);
  check(w, sizes && !dup && !missing && down == up && !cut);
  return 0;
}
static int in_league(int k, int team) { return in_list(pout[k], pnout[k], T(team)); }
static int moves_of(int kind) { int c = 0; for (int q = 0; q < pnmv; q++) c += pmv[q].kind == kind; return c; }
static void homes(const uint32_t* v, int n) { fl26_chain_ghomes(v, n); }

int main(void)
{
  int ch[GA_ITEMS], av[64];

  /* ---- A1. everyone fits: three relegated, three homes with a place each ---- */
  {
    int fr[3] = { 1, 1, 1 }; ga_item_t it[3] = { rel(B(2)), rel(B(0)), rel(B(1)) };
    check("A1: complete search", group_assign(3, fr, it, 3, ch, av, 0) == 1);
    check("A1: all three at home", ch[0] == 2 && ch[1] == 0 && ch[2] == 1 && places_ok(3, fr, it, 3, ch, av));
  }
  /* ---- A2. the cascade (grupe-promocije-1611.md, 2.1): A sent nobody up, B, C, D one each. The
     1st relegated is of D, the 2nd of A (full), the 3rd of B. The old pass: 1st home to D, 2nd to
     the first group with most room, B -- B's own club then goes to C: 1 at home. Now: 2 ---- */
  {
    int fr[4] = { 0, 1, 1, 1 }; ga_item_t it[3] = { rel(B(3)), rel(B(0)), rel(B(1)) };
    group_assign(4, fr, it, 3, ch, av, 0);
    int g = greedy_home(4, fr, it, 3), now = count_home(it, 3, ch);
    printf("  A2: old rule %d at home, new rule %d\n", g, now);
    check("A2: the old pass had 1 at home, the assignment 2 (D's and B's)", g == 1 && now == 2 && ch[0] == 3 && ch[2] == 1 && ch[1] == -1);
    check("A2: the places add up (A's club gets the place left, C)", places_ok(4, fr, it, 3, ch, av) && av[2] == 1);
  }
  /* ---- A3. Serbia: four groups of one place, four relegated all of Zapad: one at home (the best
     placed), three away -- unavoidable without border clubs ---- */
  {
    int fr[4] = { 1, 1, 1, 1 }; ga_item_t it[4] = { rel(B(3)), rel(B(3)), rel(B(3)), rel(B(3)) };
    group_assign(4, fr, it, 4, ch, av, 0);
    check("A3: one of four at home, the best placed", count_home(it, 4, ch) == 1 && ch[0] == 3 && places_ok(4, fr, it, 4, ch, av));
  }
  /* ---- A4. Hungary: the play-off groups (Délkelet, Délnyugat) sent nobody up: no place ---- */
  {
    int fr[4] = { 1, 1, 0, 0 }; ga_item_t it[2] = { rel(B(2)), rel(B(0)) };
    group_assign(4, fr, it, 2, ch, av, 0);
    check("A4: Délkelet's club cannot go home (0 places), Északkelet's can", ch[0] == -1 && ch[1] == 0 && places_ok(4, fr, it, 2, ch, av) && av[1] == 1);
    int fr2[4] = { 0, 1, 1, 0 };                                   /* Délkelet won the play-off */
    group_assign(4, fr2, it, 2, ch, av, 0);
    check("A4: when Délkelet won its play-off its club goes home", ch[0] == 2 && ch[1] == -1 && places_ok(4, fr2, it, 2, ch, av));
  }
  /* ---- A5. a club with no home takes what is left, after the clubs that have one ---- */
  {
    int fr[2] = { 1, 1 }; ga_item_t it[2] = { rel(0), rel(B(0)) };
    group_assign(2, fr, it, 2, ch, av, 0);
    check("A5: the 2nd (home A) at home although the 1st is better placed; the 1st without a home not placed here",
          ch[0] == -1 && ch[1] == 0 && av[1] == 1 && greedy_home(2, fr, it, 2) == 0);
  }
  /* ---- A6. a guest comes home when its home has a free place; a relegated club of that home
     comes first ---- */
  {
    int fr[2] = { 1, 1 }; ga_item_t it[3] = { rel(0), rel(B(1)), guest(1, B(0)) };
    group_assign(2, fr, it, 3, ch, av, 0);
    check("A6: the guest (in B, home A) goes home to A's free place, B's relegated club home to B, the club without a home takes the guest's place",
          ch[2] == 0 && ch[1] == 1 && ch[0] == -1 && av[0] == 0 && av[1] == 1 && places_ok(2, fr, it, 3, ch, av));
    int fr2[2] = { 1, 1 }; ga_item_t it2[3] = { rel(B(0)), rel(0), guest(1, B(0)) };
    group_assign(2, fr2, it2, 3, ch, av, 0);
    check("A6: A's one place to A's relegated club before A's guest (the guest stays in B)", ch[0] == 0 && ch[2] == -1 && places_ok(2, fr2, it2, 3, ch, av));
    int fr3[2] = { 0, 1 }; ga_item_t it3[2] = { rel(B(0)), guest(1, B(0)) };
    group_assign(2, fr3, it3, 2, ch, av, 0);
    check("A6: A full: neither A's relegated club nor A's guest goes home",
          ch[0] == -1 && ch[1] == -1 && places_ok(2, fr3, it3, 2, ch, av));
    int fr4[2] = { 0, 1 }; ga_item_t it4[2] = { rel(B(0)), guest(0, B(1)) };
    group_assign(2, fr4, it4, 2, ch, av, 0);
    check("A6: a guest of B sitting in full A goes home to B and frees A for A's relegated club",
          ch[0] == 0 && ch[1] == 1 && places_ok(2, fr4, it4, 2, ch, av));
  }
  /* ---- A7. two guests in each other's home groups swap, without a free place; three in a ring too ---- */
  {
    int fr[2] = { 0, 0 }; ga_item_t it[2] = { guest(0, B(1)), guest(1, B(0)) };
    group_assign(2, fr, it, 2, ch, av, 0);
    check("A7: two guests swap", ch[0] == 1 && ch[1] == 0 && places_ok(2, fr, it, 2, ch, av));
    int fr3[3] = { 0, 0, 0 }; ga_item_t it3[3] = { guest(0, B(1)), guest(1, B(2)), guest(2, B(0)) };
    group_assign(3, fr3, it3, 3, ch, av, 0);
    check("A7: three guests in a ring go home", ch[0] == 1 && ch[1] == 2 && ch[2] == 0 && places_ok(3, fr3, it3, 3, ch, av));
    ga_item_t it1[1] = { guest(0, B(1)) };
    group_assign(2, fr, it1, 1, ch, av, 0);
    check("A7: one guest alone and no place: it stays", ch[0] == -1);
  }
  /* ---- A8. border clubs (zone_border): two relegated of A, A one place, B one ---- */
  {
    int fr[2] = { 1, 1 };
    ga_item_t it0[2] = { rel(B(0)), rel(B(0)) };
    group_assign(2, fr, it0, 2, ch, av, 0);
    check("A8: without a border club the 2nd goes away", count_home(it0, 2, ch) == 1);
    ga_item_t it[4] = { rel(B(0)), rel(B(0)), border(0, B(0), 1), border(0, B(0), 1) };
    group_assign(2, fr, it, 4, ch, av, 0);
    check("A8: with border clubs both at home and the FIRST listed border club moves to B, the 2nd stays",
          ch[0] == 0 && ch[1] == 0 && ch[2] == 1 && ch[3] == -1 && places_ok(2, fr, it, 4, ch, av));
    int frf[3] = { 1, 0, 1 };                                       /* the neighbour B full, C has the place */
    group_assign(3, frf, it, 4, ch, av, 0);
    check("A8: the neighbour full: no border club moves, the 2nd relegated club goes away (to C's place)",
          ch[2] == -1 && ch[3] == -1 && count_home(it, 4, ch) == 1 && places_ok(3, frf, it, 4, ch, av) && av[2] == 1);
    ga_item_t itn[3] = { rel(B(0)), rel(B(1)), border(0, B(0), 1) };
    group_assign(2, fr, itn, 3, ch, av, 0);
    check("A8: no club needs the room: the border club stays", ch[0] == 0 && ch[1] == 1 && ch[2] == -1);
  }
  /* ---- A9. random small sets against trying every choice: as many at home as possible, never
     fewer than the old pass, the places add up, and the same answer twice ---- */
  {
    uint32_t seed = 12345; int bad = 0, worse = 0, nondet = 0, runs = 0, better = 0;
#define RND(n) ((seed = seed * 1103515245u + 12345u), (int)((seed >> 16) % (uint32_t)(n)))
    for (int run = 0; run < 3000; run++) {
      int nt = 2 + RND(4), fr[64], ni = 0; ga_item_t it[10];
      for (int t = 0; t < nt; t++) fr[t] = 0;
      int nr = 1 + RND(6);                                          /* the places: as many as come down */
      for (int i = 0; i < nr; i++) fr[RND(nt)]++;
      for (int i = 0; i < nr; i++) it[ni++] = rel(RND(4) ? B(RND(nt)) : 0);
      int ng = RND(4);
      for (int i = 0; i < ng; i++) { int c = RND(nt), h = RND(nt); if (h == c) h = (h + 1) % nt; it[ni++] = guest(c, B(h)); }
      int a[64]; for (int t = 0; t < nt; t++) a[t] = fr[t];
      int want = brute_best(nt, fr, it, ni, 0, a);
      group_assign(nt, fr, it, ni, ch, av, 0);
      int ch2[GA_ITEMS], av2[64];
      group_assign(nt, fr, it, ni, ch2, av2, 0);
      if (memcmp(ch, ch2, sizeof(int) * ni)) nondet++;
      int got = count_home(it, ni, ch), g = greedy_home(nt, fr, it, nr);
      if (got != want || !places_ok(nt, fr, it, ni, ch, av)) bad++;
      if (got < g) worse++;
      if (got > g) better++;
      runs++;
    }
    printf("  A9: %d random sets, %d better than the old pass\n", runs, better);
    check("A9: always the most at home (as trying every choice), the places add up", bad == 0);
    check("A9: never fewer at home than the old pass", worse == 0);
    check("A9: the same answer every time", nondet == 0);
  }

  /* ---- P1. group_plan: Serie C, three groups under Serie B; Serie B's last three have homes in
     A, B, B -- one place each: B's 2nd relegated club goes away, the log says so ---- */
  {
    fl26_chain_gborders(0, 0);
    mk(0, 82, 101, 20); mk(1, 389, 201, 20); mk(2, 390, 301, 20); mk(3, 391, 401, 20);
    uint32_t h[] = { 118, 389, 119, 390, 120, 390 };
    homes(h, 3);
    int n[4] = { 3, 1, 1, 1 };
    plan(1, 3, n, 0, 0, "P1");
    check("P1: 118 home in A, 119 home in B, 120 away in C (B full)", in_league(1, 118) && in_league(2, 119) && in_league(3, 120));
    check("P1: the log entries: 2 home, 1 'home full', 3 promoted", moves_of(MV_HOME) == 2 && moves_of(MV_FULL) == 1 && moves_of(MV_UP) == 3);
  }
  /* ---- P2. the next season: 120 played in C as a guest (home B) and finished mid-table; B sends
     one up and nobody of B comes down: 120 goes home, the relegated club of no region takes C ---- */
  {
    mk(0, 82, 101, 20); mk(1, 389, 201, 20); mk(2, 390, 301, 20); mk(3, 391, 401, 20);
    G[3].stand[9] = G[3].list[9] = T(120);                         /* 120 in C, 10th */
    G[0].stand[19] = G[0].list[19] = T(410);                       /* C's old 10th is in Serie B now, last */
    uint32_t h[] = { 120, 390, 118, 389, 119, 389 };
    homes(h, 3);
    int n[4] = { 3, 1, 1, 1 };
    plan(1, 3, n, 0, 0, "P2");
    check("P2: the guest 120 went home to B; the log says 'guest came home'", in_league(2, 120) && moves_of(MV_BACK) == 1);
    check("P2: A's two relegated clubs: one home, one away; 410 (no home) where the guest left", in_league(1, 118) && in_league(3, 410) && in_league(2, 119) == 0);
    int again = pnout[2];
    plan(1, 3, n, 0, 0, "P2 again");
    check("P2: the same plan twice gives the same lists (determinism)", pnout[2] == again && in_league(2, 120) && in_league(3, 410));
  }
  /* ---- P3. two guests swap in group_plan, while the relegated fill the places sent up ---- */
  {
    mk(0, 82, 101, 20); mk(1, 389, 201, 20); mk(2, 390, 301, 20);
    G[1].stand[5] = G[1].list[5] = T(900); G[2].stand[7] = G[2].list[7] = T(901);
    uint32_t h[] = { 900, 390, 901, 389 };
    homes(h, 2);
    int n[3] = { 2, 1, 1 };
    plan(1, 2, n, 0, 0, "P3");
    check("P3: 900 (home B) and 901 (home A) swap", in_league(2, 900) && in_league(1, 901) && moves_of(MV_BACK) == 2);
  }
  /* ---- P4. Hungary with its play-off: Délkelet's winner beat Északkelet's -- Délkelet sends one
     up, Északkelet none; NB II's two relegated of Északkelet and Délkelet ---- */
  {
    mk(0, 200, 101, 16); mk(1, 600, 201, 12); mk(2, 601, 301, 16); mk(3, 602, 401, 12); mk(4, 603, 501, 16);
    uint32_t h[] = { 115, 600, 116, 602 };
    homes(h, 2);
    int n[5] = { 2, 1, 1, 0, 0 };
    uint32_t po[2] = { T(401), T(201) };                            /* Délkelet's 1st beat Északkelet's 1st */
    plan(1, 4, n, po, 1, "P4");
    check("P4: the play-off winner up, Északkelet's 1st stays", in_league(0, 401) && in_league(1, 201));
    check("P4: Délkelet's relegated club home to Délkelet (its place from the play-off), Északkelet's away (no place)",
          in_league(3, 116) && !in_league(1, 115) && moves_of(MV_FULL) == 1);
  }
  /* ---- P5. border clubs: A's two relegated, A one place; zone_border names 205 (A) -> B ---- */
  {
    mk(0, 82, 101, 20); mk(1, 389, 201, 20); mk(2, 390, 301, 20);
    uint32_t h[] = { 119, 389, 120, 389, 205, 389, 210, 389 };
    homes(h, 4);
    uint32_t bd[] = { 389, 210, 390,  389, 205, 390 };              /* 210 first, then 205 */
    check("P5: two border clubs taken", fl26_chain_gborders(bd, 2) == 2);
    int n[3] = { 2, 1, 1 };
    plan(1, 2, n, 0, 0, "P5");
    check("P5: both relegated clubs home in A, the first listed border club (210) to B, 205 stays",
          in_league(1, 119) && in_league(1, 120) && in_league(2, 210) && in_league(1, 205) && moves_of(MV_BORDER) == 1);
    /* the season after: 210 played in B, mid-table; A has a place and nobody of A comes down */
    mk(0, 82, 101, 20); mk(1, 389, 201, 20); mk(2, 390, 301, 20);
    G[1].stand[9] = G[1].list[9] = T(119);                          /* A's 10th: 119, come down */
    G[2].stand[8] = G[2].list[8] = T(210);                          /* B's 9th: 210, the border club */
    G[0].stand[18] = G[0].list[18] = T(509);                        /* Serie B's last two: of no region */
    G[0].stand[19] = G[0].list[19] = T(510);
    plan(1, 2, n, 0, 0, "P5 next season");
    check("P5: the border club comes home as a guest the season after", in_league(1, 210) && moves_of(MV_BACK) == 1);
    fl26_chain_gborders(0, 0);
    mk(0, 82, 101, 20); mk(1, 389, 201, 20); mk(2, 390, 301, 20);
    plan(1, 2, n, 0, 0, "P5 without the key");
    check("P5: without zone_border (every world today) the 2nd relegated club of A goes to B", in_league(2, 120) && moves_of(MV_BORDER) == 0);
  }
  /* ---- P6. no homes at all (Argentina; a world built before ghome): the old rule, most room ---- */
  {
    homes(0, 0);
    mk(0, 30, 101, 30); mk(1, 700, 201, 18); mk(2, 701, 301, 18);
    int n[3] = { 2, 1, 1 };
    plan(1, 2, n, 0, 0, "P6");
    check("P6: no homes: the 29th to Zona A, the 30th to Zona B, as before", in_league(1, 129) && in_league(2, 130) && moves_of(MV_NOHOME) == 2);
  }
  /* ---- P7. a guest at the bottom that another set relegates (fixed) stays where it is ---- */
  {
    mk(0, 82, 101, 20); mk(1, 389, 201, 20); mk(2, 390, 301, 20);
    G[1].stand[19] = G[1].list[19] = T(950);
    uint32_t h[] = { 950, 390 };
    homes(h, 1);
    gl_t* m[3] = { &G[0], &G[1], &G[2] }; int n[3] = { 2, 1, 1 }, pref[3] = { -1, 0, 0 }, flips = 0, cut = 0, nmv = 0; char why[200];
    int fixed_bottom(uint32_t hh, uint16_t lg);
    group_plan(m, n, pref, 1, 2, 0, 0, 0, fixed_bottom, 0, 0, 0, pout, pnout, &flips, pmv, &nmv, &cut, why, sizeof why);
    check("P7: a guest the set below relegates is not moved home", in_list(pout[1], pnout[1], T(950)) && !in_list(pout[2], pnout[2], T(950)));
  }

  if (fails) { printf("%d check(s) failed\n", fails); return 1; }
  printf("all checks passed\n");
  return 0;
}
int fixed_bottom(uint32_t h, uint16_t lg) { return lg == 389 && h == T(950); }
