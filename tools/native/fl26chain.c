/* fl26chain.dll -- complete a 3-tier promotion/relegation chain at season end.
 *
 * Why (docs/season-rollover-decode.md): the season-end mover 0x141365110 exchanges clubs
 * between a league and the league below it ONCE per pass. For our chain A(11) -> B(49) ->
 * C(60) the visit of A already produces B's new list, and B's own visit is then skipped
 * because B "already has an OUTPUT entry", so B never relegates to C and C never promotes.
 * The mover cannot be fixed with data. This module finishes the job at the apply step,
 * using the game's own standings and the game's own list writer, for OUR leagues only.
 *
 * Two additive inline hooks, both verified against expected bytes before patching:
 *   1. 0x14135bff0  apply(ctx)                          -- CALL-style hook (pre + post)
 *      pre : remember ctx, fetch the final standings of B and C through the game's own
 *            0x141353750(ctx, &vec, id, fromInput=1) while the INPUT list is still intact
 *      post: if the pass wrote both B and C, move the last DemoteNumber(B) clubs of B's
 *            standings down and the first PromoteNumber(C) eligible clubs of C up, fix the
 *            league-slot byte like the mover does, and re-write both lists through the
 *            original 0x141522b50.
 *   2. 0x141522b50  set_regulation_teams(id, &handles, flag) -- BEFORE-hook (observer)
 *      records (id, count) in a small observation ring and, while inside apply, keeps a
 *      copy of the lists the game writes for B and C.
 *
 * Facts used (all measured statically, see the doc):
 *   - 0x141522b50 only READS the vector {begin,end,cap} of u32 handles; it clears +0x170 of
 *     the regulation, pushes each non-null handle (cap 48), stores the flag, finalises.
 *   - 0x141353750 fills a vector of 16-byte entries, handle at +0, standings order top-down;
 *     the out vector must be zero-initialised; the game allocates it (we leak ~1 KB/season).
 *   - club record = 0x1414bca80(block, handle) or NULL; +0x41c low 7 bits = league slot
 *     (8 or 9 bits with fl26slot7, see lay_slot in fl26layout.h);
 *     +0x628 != 0 => never promoted. block = [[0x143705e10]+0x48].
 *   - A pass that moves clubs in one direction only would change league sizes; the mover
 *     itself does that, we do not: if either side has nothing to move, nothing moves.
 *
 * Built with `zig cc` (tools/native/build-chain.sh). Our own code, no third-party binaries.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <string.h>
#include <stdio.h>
#include <stdarg.h>
#include <stdlib.h>

#define SET_RVA    0x1522b50   /* set_regulation_teams(u16 id, vec_u32* handles, u8 flag) */
#define APPLY_RVA  0x135bff0   /* apply(ctx): writes every OUTPUT entry of the season-end pass */
#define STAND_RVA  0x1353750   /* copy_standings(ctx, vec16* out, u16 id, u8 fromInput)      */
#define CLUB_RVA   0x14bca80   /* club_record(block, handle) -> record or NULL              */
#define OWNER_RVA  0x3705e10   /* global: owner; block = [owner+0x48]                       */
#define INPUT_RVA  0x13536f0   /* input_entry(ctx, u16 id) -> INPUT entry or NULL           */
#define TABLE_RVA  0x158e000   /* league_table(u16 id) -> season table (0x187c bytes) or NULL */

#define OFF_SLOT   0x41c
#define OFF_PARENT 0x628
#define NOPARENT_RVA 0x351ae44  /* global "no parent club" sentinel the mover compares to */
#define MAX_CLUBS  48
#define MAX_CHAINS 256  /* 8 until 0.2.5: the Europack eu4 has 10 and the install refused them all (B186);
                           32 until the league band (fl26world 320..499): a ~250-league world has a pair
                           for every third, fifth, sixth and seventh division and every league under a split */

/* prologues we steal (whole, position-independent instructions) */
static const unsigned char SIG_SET[15] = {                 /* mov [rsp+8],rbx; mov [rsp+10],rbp; mov [rsp+18],rsi */
  0x48,0x89,0x5c,0x24,0x08, 0x48,0x89,0x6c,0x24,0x10, 0x48,0x89,0x74,0x24,0x18 };
static const unsigned char SIG_APPLY[15] = {               /* push rdi (REX-prefixed); sub rsp,40; mov qword [rsp+20],-2 */
  0x40,0x57, 0x48,0x83,0xec,0x40, 0x48,0xc7,0x44,0x24,0x20,0xfe,0xff,0xff,0xff };

typedef struct { uint32_t* b; uint32_t* e; uint32_t* c; } vec32_t;
typedef struct { unsigned char* b; unsigned char* e; unsigned char* c; } vec16_t;
/* regular: the regular phase of mid when mid is a split league's total, else 0 (was padding) */
typedef struct { uint16_t mid, low; uint8_t demote_mid, promote_low; uint16_t regular; } fl26_chain_cfg_t;

typedef char           (*set_fn)(uint64_t id, vec32_t* v, uint64_t flag);
typedef void           (*stand_fn)(void* ctx, vec16_t* out, uint64_t id, uint64_t fromInput);
typedef unsigned char* (*club_fn)(unsigned char* block, uint64_t handle);
typedef unsigned char* (*input_fn)(void* ctx, uint64_t id);
typedef unsigned char* (*table_fn)(uint64_t id);

typedef struct {
  fl26_chain_cfg_t cfg;
  uint32_t stand_mid[MAX_CLUBS], stand_low[MAX_CLUBS]; int n_stand_mid, n_stand_low;
  uint32_t list_mid[MAX_CLUBS],  list_low[MAX_CLUBS];  int n_list_mid,  n_list_low;
  uint64_t flag_mid, flag_low, flag_reg;
  int seen;                       /* bit0 = mid list captured, bit1 = low list captured, bit2 = regular phase written */
} chain_t;

static uint64_t          g_base = 0;
#include "fl26layout.h"   /* block offsets read from the code fl26caps patched */
unsigned char*           g_tramp_set   = 0;    /* referenced by the naked stubs */
unsigned char*           g_tramp_apply = 0;
static volatile uint32_t* g_cave = 0;
static chain_t           g_chain[MAX_CHAINS];
static int               g_nchain = 0;

/* ---- every split of ours: {total, regular phase} (fl26_chain_splits, 08.11.2026) ----
 * The pass writes a split's regular phase with last season's clubs before apply returns (see
 * split_regular). A pair's upper league brings its phase along there; since more than one split a
 * country (08.11.2026) a split is also the lower league of a pair (Serbia's Prva liga under the
 * SuperLiga) and the upper league of a group set (Prva liga over the Srpska liga groups), and
 * splits_post brings every phase the pass wrote to its total's clubs after all the moves. */
#define MAX_SPLITREG 64
typedef struct { uint16_t total, regular, group[3]; uint64_t flag; int seen; } splitreg_t;
static splitreg_t g_splitreg[MAX_SPLITREG]; static int g_nsplitreg = 0;

static volatile int      g_in_apply = 0, g_reentrant = 0;
static void*             g_ctx = 0;

/* counters readable from Lua: applies seen, fixes done, fixes refused, anomalies */
static volatile uint32_t g_stat[4];

/* ---- small text log, drained by the Lua loader into sider.log ---- */
/* 8192 until the group sets (a line for each league of a set), 16384 until the Megapack (08.11.):
   one season pass of 300+ leagues writes far more than that before the loader can drain it, and
   the season end's fix lines were the ones that did not fit. A line that still does not fit is
   counted, and the count is said once there is room again. */
static char g_log[262144]; static volatile int g_log_len = 0; static volatile int g_log_lost = 0;
static void logf(const char* fmt, ...)
{
  char line[256]; va_list ap; va_start(ap, fmt);
  int n = vsnprintf(line, sizeof line, fmt, ap); va_end(ap);
  if (n <= 0) return; if (n >= (int)sizeof line) n = sizeof line - 1;
  if (g_log_lost && g_log_len + 64 < (int)sizeof g_log) {
    g_log_len += snprintf(g_log + g_log_len, 64, "(%d log line(s) lost: the log was full)\n", g_log_lost);
    g_log_lost = 0;
  }
  if (g_log_len + n + 1 >= (int)sizeof g_log) { g_log_lost++; return; }
  memcpy(g_log + g_log_len, line, n); g_log_len += n; g_log[g_log_len++] = '\n';
}

static unsigned char* block(void) {
  unsigned char* owner = *(unsigned char**)(uintptr_t)(g_base + OWNER_RVA);
  return owner ? *(unsigned char**)(owner + 0x48) : 0;
}
static int vcount32(vec32_t* v) { return (v && v->b && v->e >= v->b) ? (int)((v->e - v->b)) : 0; }

/* ---- guard: our regulations are never emptied while they hold clubs ----
 * 2026-09-22, the first August world: at New Year the calendar-year season-end pass rewrote
 * 76, 93, 94, 96, 98 and 162 -- ours, on ids the shipped data treats as calendar-year
 * leagues -- with EMPTY club lists, in the middle of their August-May season. The ids come
 * from the loader (fl26_chain_protect). */
#define MAX_PROTECT 1024 /* every league of the world: 256 until the league band */
#ifndef REG_ARRAY_OFF   /* fallback only: reg_off() reads the real one from the code */
#define REG_ARRAY_OFF 0x1d4c330   /* edit block + this = regulation records (caps sets), as fl26join.c */
#endif
#define REG_STRIDE    0x314
#define REG_CAP       lay_regcap()   /* 600 under the 0.3.0 set, 1200 under the limits set */
static uint16_t g_protect[MAX_PROTECT]; static int g_nprotect = 0;
static int is_protected(uint16_t id) { for (int i = 0; i < g_nprotect; i++) if (g_protect[i] == id) return 1; return 0; }

/* Where the regulation records start: the displacement fl26caps wrote into the cmp at
 * 0x1415435a9 (`cmp word [rdx+r13+disp32], bx`, the site fl26regfast reads too), so the DLL
 * follows whichever caps set is installed. REG_ARRAY_OFF is only the fallback for when the
 * bytes there are not that cmp. */
#define REG_DISP_RVA 0x15435a9
static uint32_t reg_off(void)
{
  const unsigned char* p = (const unsigned char*)(uintptr_t)(g_base + REG_DISP_RVA);
  if (p[0] == 0x66 && p[1] == 0x42 && p[2] == 0x39 && p[3] == 0x9c && p[4] == 0x2a)
    return *(const uint32_t*)(p + 5);
  return REG_ARRAY_OFF;
}


/* clubs in the regulation's +0x170 list (u32 handles, 0xffffffff ends it), -1 if not found */
static int reg_count(uint16_t id)
{
  unsigned char* blk = block(); if (!blk) return -1;
  unsigned char* rec = blk + reg_off();
  for (int i = 0; i < REG_CAP; i++, rec += REG_STRIDE) {
    if (*(uint16_t*)rec != id) continue;
    int n = 0;
    while (n < MAX_CLUBS && *(uint32_t*)(rec + 0x170 + n*4) != 0xffffffffu) n++;
    return n;
  }
  return -1;
}

/* the regulation's live +0x170 list into out (MAX_CLUBS), -1 if the regulation is not found */
static int reg_list(uint16_t id, uint32_t* out)
{
  unsigned char* blk = block(); if (!blk) return -1;
  unsigned char* rec = blk + reg_off();
  for (int i = 0; i < REG_CAP; i++, rec += REG_STRIDE) {
    if (*(uint16_t*)rec != id) continue;
    int n = 0;
    while (n < MAX_CLUBS && *(uint32_t*)(rec + 0x170 + n*4) != 0xffffffffu) { out[n] = *(uint32_t*)(rec + 0x170 + n*4); n++; }
    return n;
  }
  return -1;
}

/* ---- GitHub #21: a domestic cup keeps its own league ----
 * The game fills a domestic cup from the region's first league (lowest regulation id) and the
 * league linked below it. With one of our leagues put under a shipped top flight that has no
 * second division (Bundesliga 50, Russian league 116), the DFB-Pokal (53) got 38 clubs, or only
 * our 20 when our league had the lower id; the Russian Cup (123) the same. Their brackets are
 * built for 18 and 16: a 38-club DFB-Pokal was left with three undated first-round matches and
 * no round of 16. So when a cup's new list holds clubs of our league, the cup gets the top
 * league's clubs instead -- the field the shipped game gives it. The triples come from the world
 * file (`cup=` on the league line, written by the League Builder).
 * 16 until 0.2.5: the Europack eu5 has 18 cups and the Modpack more, and the ones past 16 were
 * left to the game, which filled the Greek Cup (124) with both Greek leagues, 30 clubs, played
 * the first round and never the second (B178, monkusgigus 2026-10-20; eu5, day 298 of 2026). */
#define MAX_CUPS 512    /* 128 until the league band: a national cup and a league cup for each of ~150 countries */
/* GitHub #32: `cupall=1` on the league line (bit 15 of the cup id here) is the other way round --
 * the cup takes both leagues, in turn (top, low, top ...) so the first round, which pairs 1 v 2,
 * is top flight against the league below, as the real DFB-Pokal draws it. The League
 * Builder writes it only when the cup's calendar dates every round of that field and it raised
 * the cup's bracket to 44 in the world's tables; the game, left alone, gives it both leagues
 * when ours has the higher id and ours alone when it has the lower. */
#define CUP_ALL 0x8000
/* GitHub #74: `cupn=` caps the field. The bracket screen (Database -> Competition Info -> the
 * cup -> Fixtures) draws a cup of 32 or fewer only for 2-16, 18, 20, 24, 28 or 30 clubs:
 * 0x140b33340 has no bye layout for the rest and 0x140b34501 reads its NULL. A world cup of
 * both leagues with 22 clubs crashed it, and the cup's own entry list does not help -- the
 * game fills a domestic cup from the leagues, not from the entries. So the cup is written with
 * the top league's clubs and the first clubs of the one below, `max` in all (0 = no cap). */
/* B228: `cupthird=` on a cupall line names a new third division whose first clubs join the two
 * shipped ones, up to cupn -- the Coupe de France of Ligue 1, Ligue 2 and the first 9 of
 * National, 48 (jibibi 2026-10-24); the League Builder raised the cup's bracket to that field. */
typedef struct { uint16_t cup, top, low, all, max, third; } cup_t;
static cup_t    g_cup[MAX_CUPS]; static int g_ncup = 0;
static uint64_t g_cup_flag[MAX_CUPS]; static int g_cup_seen[MAX_CUPS];

/* B278 (D1eg0Ar, Agus 2026-10-29): the top league's list is not always a field the bracket screen
   draws either. Argentina's league (30) came out of the season pass with 26 clubs, its Primera
   Nacional below swapped clubs with it, and the Copa Argentina (59) was given those 26: the game
   drew 13 first-round ties, the 13th leading nowhere, and the bracket after the first round
   crashed at 0x140b34501. So a field of 32 or fewer is cut to the largest size of #74's list. */
static int bracket_fit(int n)
{
  static const unsigned char ok[] = { 32, 30, 28, 24, 20, 18, 16 };
  /* past 32 the shipped fields 36, 40, 44 (64 - n byes: 28, 24, 20), FL27 cups of 33-43 clubs
     on 36/40 (mato 2026-11-08) and cup_join: leagues that shrank to 33-35 go down to 32 */
  if (n > 32 && n < 44) return n >= 40 ? 40 : n >= 36 ? 36 : 32;
  if (n > 32 || n <= 16) return n;
  for (int i = 0; i < (int)sizeof ok; i++) if (ok[i] <= n) return ok[i];
  return n;
}

static int holds_any(const uint32_t* list, int n, const uint32_t* of, int m)
{
  for (int i = 0; i < n; i++) for (int j = 0; j < m; j++) if (list[i] == of[j]) return 1;
  return 0;
}

/* 1 = the cup was written with the top league's clubs (through the original setter), or with
   both leagues' for a cupall cup */
static int cup_fix(cup_t* c, const uint32_t* list, int n, uint64_t flag, const char* when, int keep)
{
  uint32_t top[2 * MAX_CLUBS], low[MAX_CLUBS];
  int nt = reg_list(c->top, top), nl = c->low ? reg_list(c->low, low) : 0;
  if (nt <= 0 || nl < 0 || (nl == 0 && !c->max)) return 0;
  if (c->all) {
    if (nt + nl > 2 * MAX_CLUBS) return 0;
    memcpy(top + nt, low, nl * sizeof low[0]);
    int m = nt + nl, n3 = 0;
    if (c->third) {                                  /* B228: then the third division's first clubs */
      uint32_t th[MAX_CLUBS];
      int k3 = reg_list(c->third, th);
      for (int i = 0; i < k3 && m < 2 * MAX_CLUBS; i++) top[m++] = th[i];
      n3 = k3 > 0 ? k3 : 0;
    }
    if (c->max && m > c->max) m = c->max;           /* #74: a field the bracket screen draws */
    m = bracket_fit(m);                               /* B278: leagues that shrank below cupn */
    /* the order of the list is the first-round draw (1 v 2, 3 v 4 ...): the two leagues in
       turn, so a first round is top flight against the league below, not the top league among
       itself (Discord, San Marino 2026-10-06); the extra clubs of the bigger one meet at the end */
    uint32_t mix[2 * MAX_CLUBS];
    int hi = nt < m ? nt : m, k = 0;
    for (int i = 0; i < hi || hi + i < m; i++) {
      if (i < hi) mix[k++] = top[i];
      if (hi + i < m) mix[k++] = top[hi + i];
    }
    if (n == m && !memcmp(list, mix, m * sizeof mix[0])) return 0;
    if (keep && n == m) {                             /* B334: drawn already, see observe */
      logf("cup %u: %d clubs (%s) -- the field it was drawn with, left as it is", c->cup, n, when);
      return 0;
    }
    vec32_t v = { mix, mix + m, mix + m };
    int was = g_reentrant; g_reentrant = 1;
    ((set_fn)(uintptr_t)g_tramp_set)(c->cup, &v, flag);
    g_reentrant = was;
    if (c->third)
      logf("cup %u: %d clubs (%s) -- given %u's %d, %u's %d and %u's first %d clubs", c->cup, n, when, c->top,
           nt < m ? nt : m, c->low, m > nt + nl ? nl : (m > nt ? m - nt : 0), c->third,
           m > nt + nl ? (m - nt - nl < n3 ? m - nt - nl : n3) : 0);
    else
      logf("cup %u: %d clubs (%s) -- given %u's %d and %u's %d clubs", c->cup, n, when, c->top,
           nt < m ? nt : m, c->low, m > nt ? m - nt : 0);
    return 1;
  }
  if (c->max && nt > c->max) nt = c->max;
  nt = bracket_fit(nt);                               /* B278 */
  if (!holds_any(list, n, low, nl) && !(c->max && n > c->max) && bracket_fit(n) == n) return 0;
  vec32_t v = { top, top + nt, top + MAX_CLUBS };
  int was = g_reentrant; g_reentrant = 1;
  ((set_fn)(uintptr_t)g_tramp_set)(c->cup, &v, flag);
  g_reentrant = was;
  if (holds_any(list, n, low, nl))
    logf("cup %u: %d clubs with %u's in them (%s) -- given %u's %d clubs instead", c->cup, n, c->low, when, c->top, nt);
  else
    logf("cup %u: %d clubs, no bracket for that (%s) -- given %u's %d clubs instead", c->cup, n, when, c->top, nt);
  return 1;
}

/* ---- GitHub #29: the super cup of that country ----
 * The same new second division put a club of its own into the country's super cup (DFL
 * Supercup 95: Bayern v Germany D2 01; Russian Super Cup 129: Krasnodar v Rusia D2 20), and the
 * match was played. A club that spent the season in our league cannot have qualified: it was
 * not the top league's champion and, with the cup kept to the top league above, not in the cup.
 * So such a club is swapped for a club of the top league that is not in the super cup yet. In
 * the season pass the test is the list our league had before the pass (a club relegated in
 * the same pass may have won the cup); outside it, the live list. Triples {super cup, top
 * league, our league} from the world file (`scup=`). */
typedef struct { uint16_t scup, top, low; } scup_t;
static scup_t   g_scup[MAX_CUPS]; static int g_nscup = 0;
static uint64_t g_scup_flag[MAX_CUPS]; static int g_scup_seen[MAX_CUPS];
static uint32_t g_scup_pre[MAX_CUPS][MAX_CLUBS]; static int g_scup_npre[MAX_CUPS];

/* 1 = the super cup was written again without the clubs of `low` (through the original setter) */
static int scup_fix(scup_t* s, const uint32_t* list, int n, const uint32_t* low, int nl, uint64_t flag, const char* when)
{
  uint32_t top[MAX_CLUBS], out[MAX_CLUBS];
  int nt = reg_list(s->top, top), k = 0, swapped = 0;
  if (nt <= 0 || nl <= 0 || n <= 0 || !holds_any(list, n, low, nl)) return 0;
  for (int i = 0; i < n; i++) {
    uint32_t h = list[i];
    if (holds_any(&h, 1, low, nl)) {
      h = 0xffffffffu;
      for (int j = 0; j < nt; j++)
        if (!holds_any(&top[j], 1, list, n) && !holds_any(&top[j], 1, out, k) && !holds_any(&top[j], 1, low, nl)) { h = top[j]; break; }
      if (h == 0xffffffffu) { logf("super cup %u: no club of %u left to put in (%s) -- untouched", s->scup, s->top, when); return 0; }
      swapped++;
    }
    out[k++] = h;
  }
  vec32_t v = { out, out + k, out + MAX_CLUBS };
  int was = g_reentrant; g_reentrant = 1;
  ((set_fn)(uintptr_t)g_tramp_set)(s->scup, &v, flag);
  g_reentrant = was;
  logf("super cup %u: %d club(s) of %u in it (%s) -- swapped for clubs of %u", s->scup, swapped, s->low, when, s->top);
  return 1;
}

static void gl_observe(uint16_t id, uint64_t flag);
static void groups_pre(void* ctx);
static void groups_post(void);
static void poff_post(void);
static int  gl_member(uint16_t id);

/* ---- observer + capture (BEFORE-hook on 0x141522b50); nonzero = refuse the write ---- */
int observe(uint64_t id, vec32_t* v, uint64_t flag)
{
  int n = vcount32(v);
  if (!g_reentrant) for (int i = 0; i < g_ncup; i++) {
    if ((uint16_t)id != g_cup[i].cup) continue;
    if (g_in_apply) {                                                             /* settled in apply_post */
      g_cup_flag[i] = flag & 0xff; g_cup_seen[i] = 1;
      /* B334 (rwee 2026-11-06): the pass draws the cup from this list before apply returns, so
         a third division's clubs given in apply_post had no place in the bracket -- the FA Cup
         (23) drawn with 44 of its 48, given the 48 after, stalled at the quarter-finals. Such a
         cup gets its field now, from the leagues as they stand, and apply_post leaves it at
         that size (only a field of another size is written again) */
      if (g_cup[i].third && n > 0 && cup_fix(&g_cup[i], v->b, n > MAX_CLUBS ? MAX_CLUBS : n, flag & 0xff, "season pass, before its draw", 0)) {
        g_cup_seen[i] = 2; return 1;
      }
      break;
    }
    if (n > 0 && cup_fix(&g_cup[i], v->b, n > MAX_CLUBS ? MAX_CLUBS : n, flag & 0xff, "outside the season pass", 0)) return 1;
    break;
  }
  if (!g_reentrant) for (int i = 0; i < g_nscup; i++) {
    if ((uint16_t)id != g_scup[i].scup) continue;
    if (g_in_apply) { g_scup_flag[i] = flag & 0xff; g_scup_seen[i] = 1; break; }   /* settled in apply_post */
    uint32_t low[MAX_CLUBS]; int nl = reg_list(g_scup[i].low, low);
    if (n > 0 && scup_fix(&g_scup[i], v->b, n > MAX_CLUBS ? MAX_CLUBS : n, low, nl, flag & 0xff, "outside the season pass")) return 1;
    break;
  }
  if (n == 0 && !g_reentrant && is_protected((uint16_t)id)) {
    int have = reg_count((uint16_t)id);
    if (have > 0) {
      g_stat[3]++;
      logf("guard: refused an empty club list for %u (it holds %d clubs)", (unsigned)(uint16_t)id, have);
      return 1;
    }
  }
  if (g_cave) {
    g_cave[0]++;
    uint32_t idx = g_cave[1] & 63;
    uint16_t* ring = (uint16_t*)((void*)(g_cave + 2));
    ring[idx*2] = (uint16_t)id; ring[idx*2+1] = (uint16_t)n;
    g_cave[1] = (g_cave[1] + 1) & 63;
  }
  if (!g_in_apply || g_reentrant) return 0;
  gl_observe((uint16_t)id, flag & 0xff);
  for (int i = 0; i < g_nsplitreg; i++)
    if ((uint16_t)id == g_splitreg[i].regular) { g_splitreg[i].flag = flag & 0xff; g_splitreg[i].seen = 1; }
  for (int i = 0; i < g_nchain; i++) {
    chain_t* ch = &g_chain[i];
    int m = n > MAX_CLUBS ? MAX_CLUBS : n;
    if ((uint16_t)id == ch->cfg.mid) { memcpy(ch->list_mid, v->b, m*4); ch->n_list_mid = m; ch->flag_mid = flag & 0xff; ch->seen |= 1; }
    if ((uint16_t)id == ch->cfg.low) { memcpy(ch->list_low, v->b, m*4); ch->n_list_low = m; ch->flag_low = flag & 0xff; ch->seen |= 2; }
    if (ch->cfg.regular && (uint16_t)id == ch->cfg.regular) { ch->flag_reg = flag & 0xff; ch->seen |= 4; }
  }
  return 0;
}

__attribute__((naked)) void set_handler(void)
{
  __asm__ volatile(
    "sub  $0x38, %rsp\n"
    "mov  %rcx, 0x20(%rsp)\n"
    "mov  %rdx, 0x28(%rsp)\n"
    "mov  %r8,  0x30(%rsp)\n"
    "call observe\n"
    "test %eax, %eax\n"
    "jz   1f\n"
    "add  $0x38, %rsp\n"
    "mov  $1, %eax\n"            /* refused: report success, write nothing */
    "ret\n"
    "1:\n"
    "mov  0x20(%rsp), %rcx\n"
    "mov  0x28(%rsp), %rdx\n"
    "mov  0x30(%rsp), %r8\n"
    "add  $0x38, %rsp\n"
    "jmp  *g_tramp_set(%rip)\n");
}

/* ---- apply pre/post ---- */
static int fetch_standings(void* ctx, uint16_t id, uint32_t* out)
{
  vec16_t v = {0,0,0};
  ((stand_fn)(uintptr_t)(g_base + STAND_RVA))(ctx, &v, id, 1);
  int n = 0;
  if (v.b && v.e >= v.b) {
    n = (int)((v.e - v.b) / 16); if (n > MAX_CLUBS) n = MAX_CLUBS;
    for (int i = 0; i < n; i++) out[i] = *(uint32_t*)(v.b + i*16);
  }
  return n;   /* the game's buffer is intentionally not freed (allocator unknown; ~1 KB per season) */
}

/* Fallback when the pass carries no INPUT table for a league (2026-09-22: three applies,
   every one "standings 0/0", although both lists were written). Read the league's season
   table the same way the INPUT filler 0x14135e3a0 does: 0x14158e000(id) -> table, 48 slots
   of 16 bytes at +0x10, handle in dword 0, empty slot = the "none" sentinel. Table order is
   the order the filler copies, i.e. the final standings. */
static int fetch_table(uint16_t id, uint32_t* out)
{
  unsigned char* t = ((table_fn)(uintptr_t)(g_base + TABLE_RVA))(id);
  if (!t) return -1;
  uint32_t none = *(uint32_t*)(uintptr_t)(g_base + NOPARENT_RVA);
  int n = 0;
  for (int i = 0; i < MAX_CLUBS; i++) {
    uint32_t h = *(uint32_t*)(t + 0x10 + i*16);
    if (h == none) continue;
    out[n++] = h;
  }
  return n;
}

/* Apertura/Clausura (GitHub #106, Peru and Uruguay 2026-10-07): a split whose second phase starts
   from zero points (carry=0) leaves its total with no table at all -- "season table missing,
   0 clubs" -- so nobody went down and nobody came up. The standings are then counted here from the
   played matches of both phases, the way fl26swiss counts them for the continental places
   (count_table, apclau_keep): 3 points a win, then goal difference, then goals scored. */
#define MATCH_BASE_SITE 0x13146e8   /* lea rcx,[rax+base]: the match table's offset in the block */
#define MATCH_CAP_SITE  0x131471b   /* cmp edi,cap: its record count (the caps patch moves both)  */
#define MATCH_STRIDE    0x254
#define MAX_APCLAU 4
typedef struct { uint16_t regular, second; } apclau_t;
static apclau_t g_apclau[MAX_APCLAU]; static int g_napclau = 0;

static int apclau_table(uint16_t regular, uint32_t* out)
{
  uint16_t second = 0;
  for (int i = 0; i < g_napclau; i++) if (g_apclau[i].regular == regular) second = g_apclau[i].second;
  if (!second) return 0;
  const unsigned char* bs = (const unsigned char*)(uintptr_t)(g_base + MATCH_BASE_SITE);
  const unsigned char* cs = (const unsigned char*)(uintptr_t)(g_base + MATCH_CAP_SITE);
  if (bs[0] != 0x48 || bs[1] != 0x8d || bs[2] != 0x88 || cs[0] != 0x81 || cs[1] != 0xff) {
    logf("apclau %u+%u: the match table's walk is not where it was; no table", regular, second);
    return 0;
  }
  uint32_t base = *(const uint32_t*)(bs + 3), cap = *(const uint32_t*)(cs + 2);
  unsigned char* blk = block();
  if (!blk || !cap || cap > 200000) return 0;
  uint32_t club[MAX_CLUBS]; int pts[MAX_CLUBS], gd[MAX_CLUBS], gf[MAX_CLUBS], n = 0, played = 0;
  for (uint32_t i = 0; i < cap; i++) {
    const unsigned char* m = blk + base + (size_t)i * MATCH_STRIDE;
    if (*(const uint16_t*)m == 0xffff || !(m[7] & 0x40)) continue;          /* empty, or not played */
    uint16_t reg = *(const uint16_t*)(m + 4);
    if (reg != regular && reg != second) continue;
    uint32_t side[2] = { *(const uint32_t*)(m + 0x14), *(const uint32_t*)(m + 0x18) };
    int goals[2] = { m[0x1c], m[0x1f] }, at[2];
    for (int j = 0; j < 2; j++) {
      int k = 0;
      while (k < n && club[k] != side[j]) k++;
      if (k == n) {
        if (n >= MAX_CLUBS || !(side[j] >> 14)) k = -1;
        else { club[n] = side[j]; pts[n] = gd[n] = gf[n] = 0; n++; }
      }
      at[j] = k;
    }
    if (at[0] < 0 || at[1] < 0) continue;
    for (int j = 0; j < 2; j++) {
      int me = goals[j], them = goals[1 - j];
      pts[at[j]] += me > them ? 3 : me == them ? 1 : 0;
      gd[at[j]] += me - them; gf[at[j]] += me;
    }
    played++;
  }
  /* each phase once round, or twice: n(n-1)/2 matches a phase at the least */
  if (n < 4 || played < n * (n - 1)) {
    logf("apclau %u+%u: %d played match(es) of %d club(s) -- not a finished season, no table", regular, second, played, n);
    return 0;
  }
  for (int a = 1; a < n; a++)
    for (int b = a; b > 0; b--) {
      int x = b - 1, y = b;
      if (pts[y] < pts[x] || (pts[y] == pts[x] && (gd[y] < gd[x] || (gd[y] == gd[x] && gf[y] <= gf[x])))) break;
      uint32_t c = club[x]; club[x] = club[y]; club[y] = c;
      int t = pts[x]; pts[x] = pts[y]; pts[y] = t;
      t = gd[x]; gd[x] = gd[y]; gd[y] = t;
      t = gf[x]; gf[x] = gf[y]; gf[y] = t;
    }
  for (int k = 0; k < n; k++) out[k] = club[k];
  logf("apclau %u+%u: table from %d matches, %08x %d pts ... last %08x %d pts",
       regular, second, played, club[0], pts[0], club[n - 1], pts[n - 1]);
  return n;
}

/* A split's total from its groups (08.11.2026, Megapack FL27): the game gives a split's total a
   table only when its two groups are of one size and end on one day (Scotland's shape: Austria
   6+6, Serbia 7+7). Cyprus 6+8, Israel 6+8, Romania 6+10, Egypt 7+13 and every split of three
   groups (Czechia 6+4+6, Romania's Liga 2 6+8+8) ended the season with "season table missing,
   0 clubs" on the total, and nobody went down or came up. The final table is the groups one
   after the other -- the championship group's places first, then the next group's -- as it is in
   every such league. Pure over the groups' tables, for the test; 0 when a group has no table or a
   club is in two. */
static int same_club(uint32_t a, uint32_t c);
static int split_concat(uint32_t* const* tab, const int* n, int ng, uint32_t* out)
{
  int o = 0;
  for (int g = 0; g < ng; g++) {
    if (n[g] <= 0) return 0;
    for (int i = 0; i < n[g]; i++) {
      for (int k = 0; k < o; k++) if (same_club(out[k], tab[g][i])) return 0;
      if (o >= MAX_CLUBS) return 0;
      out[o++] = tab[g][i];
    }
  }
  return o;
}
static int fetch_any(void* ctx, uint16_t id, uint32_t* out)
{
  int n = fetch_standings(ctx, id, out);
  if (n > 0) return n;
  n = fetch_table(id, out);
  return n < 0 ? 0 : n;
}
/* fl26swiss keeps a split group's final table and a national cup's winner when they end, because
   by the season-end apply the new season's schedule has replaced both (mp31, 08.11.2026); asked
   for only when the game has nothing, and only from a season that ended at most 120 days ago */
typedef int (*kept_table_fn)(uint16_t reg, int max_age, uint32_t* out, int cap);
typedef uint32_t (*kept_winner_fn)(uint16_t reg, int max_age);
static FARPROC swiss_export(const char* name)
{
  HMODULE h = GetModuleHandleA("fl26swiss.dll");
  return h ? GetProcAddress(h, name) : 0;
}
static int kept_table(uint16_t id, uint32_t* out)
{
  kept_table_fn f = (kept_table_fn)(uintptr_t)swiss_export("fl26_swiss_kept_table");
  return f ? f(id, 120, out, MAX_CLUBS) : 0;
}
static uint32_t kept_winner(uint16_t ko)
{
  kept_winner_fn f = (kept_winner_fn)(uintptr_t)swiss_export("fl26_swiss_kept_winner");
  return f ? f(ko, 120) : 0;
}

static int split_group(uint16_t id)
{
  for (int i = 0; i < g_nsplitreg; i++) for (int g = 0; g < 3; g++) if (id && g_splitreg[i].group[g] == id) return 1;
  return 0;
}

static int split_table(void* ctx, uint16_t id, uint32_t* out, int kept_only)
{
  const splitreg_t* sp = 0;
  for (int i = 0; i < g_nsplitreg && !sp; i++) if (g_splitreg[i].total == id && g_splitreg[i].group[0]) sp = &g_splitreg[i];
  if (!sp) return 0;
  static uint32_t buf[3][MAX_CLUBS];
  uint32_t* tab[3] = { buf[0], buf[1], buf[2] }; int n[3] = { 0, 0, 0 }, ng = 0;
  /* the kept table first (mp45, 09.11.2026): by the season-end apply the game's group table is no
     longer the final one -- Austria sent down the relegation group's winner (47f9c5f1, 42 pts) and
     kept its last (47f845e9, 35), NIFL and Slovakia promoted the play-off's loser; 7 of 17 splits */
  int kept = 0;
  for (int g = 0; g < 3 && sp->group[g]; g++, ng++) {
    if ((n[g] = kept_table(sp->group[g], tab[g])) > 0) { kept++; continue; }
    if (kept_only) return 0;
    n[g] = fetch_any(ctx, sp->group[g], tab[g]);
  }
  int t = split_concat(tab, n, ng, out);
  if (kept_only && t <= 0) return 0;
  logf("split %u: %s -- %s from its groups (%u:%d %u:%d %u:%d)%s", id,
       kept_only ? "its groups ended this season" : "no table of its own", t ? "the places" : "none either", sp->group[0], n[0], sp->group[1], n[1], sp->group[2], n[2],
       kept ? ", kept by fl26swiss when they ended" : "");
  if (t > 0) {
    char line[24 * 9 + 1]; int o = 0;
    for (int i = 0; i < t && i < 24; i++) o += snprintf(line + o, sizeof line - o, " %08x", out[i]);
    logf("split %u: places%s", id, line);
  }
  return t;
}

static int standings(void* ctx, uint16_t id, uint32_t* out)
{
  /* a split whose every group ended this season (fl26swiss kept their tables): its places from
     them. b361 09.11.2026: at the season-end fix the game's INPUT table of the total is the new
     season's -- every club on 0 points, in club-id order -- and the last two by id went down
     (Austria, Denmark, NIFL, Slovakia, Malta, Lebanon, Romania). */
  int n = split_table(ctx, id, out, 1);
  if (n > 0) return n;
  n = fetch_standings(ctx, id, out);
  if (n > 0) return n;
  unsigned char* in = ((input_fn)(uintptr_t)(g_base + INPUT_RVA))(ctx, id);
  int t = fetch_table(id, out);
  logf("apply: %u has no INPUT standings (entry %s); season table %s, %d clubs",
       id, in ? "present" : "missing", t < 0 ? "missing" : "found", t < 0 ? 0 : t);
  if (t <= 0) t = split_table(ctx, id, out, 0);
  return t < 0 ? 0 : t;
}

void apply_pre(void* ctx)
{
  g_ctx = ctx; g_in_apply = 1; g_stat[0]++;
  for (int i = 0; i < g_nchain; i++) {
    chain_t* ch = &g_chain[i];
    ch->seen = 0; ch->n_list_mid = ch->n_list_low = 0;
    ch->n_stand_mid = standings(ctx, ch->cfg.mid, ch->stand_mid);
    if (ch->n_stand_mid <= 0 && ch->cfg.regular) ch->n_stand_mid = apclau_table(ch->cfg.regular, ch->stand_mid);
    ch->n_stand_low = standings(ctx, ch->cfg.low, ch->stand_low);
    logf("apply: chain %u->%u standings %d/%d", ch->cfg.mid, ch->cfg.low, ch->n_stand_mid, ch->n_stand_low);
  }
  groups_pre(ctx);
  for (int i = 0; i < g_ncup; i++) g_cup_seen[i] = 0;
  for (int i = 0; i < g_nscup; i++) { g_scup_seen[i] = 0; g_scup_npre[i] = reg_list(g_scup[i].low, g_scup_pre[i]); }
}

static int remove_handle(uint32_t* list, int n, uint32_t h)
{
  for (int i = 0; i < n; i++) if (list[i] == h) { memmove(list + i, list + i + 1, (n - i - 1) * 4); return n - 1; }
  return -1;
}

/* ---- groups of one division (GitHub #98) ----
 * Several leagues of one division side by side -- three Serie C groups under Serie B, nine Serie
 * D groups under the three of Serie C, two Regionalliga groups under the 3. Liga. The game links
 * a league to ONE league below it (+0x7e) and promotes by the one above (+0x7c), so the League
 * Builder links only one pair of such a "group set" (the lowest id below and its league above) and
 * every exchange of the set is done here, at the apply step, as one move:
 *   - each upper league sends its last n clubs down, each lower group its first n eligible up
 *     (n = the counts of the world file's gset line); a play-off of the set may swap a club in
 *     or out (see the play-offs below);
 *   - the promoted go to the upper leagues, as many to each as it sent down; the relegated to the
 *     groups, as many to each as it sent up -- so every league keeps its size. Which one: the
 *     club's home league if it is one of the set (where the League Builder put it, ghome lines),
 *     else the upper league a group names as its own (pref), else the one with the most places
 *     left (the first of them on a tie): balanced and the same every time. 16.11.2026 (mato:
 *     "klubovi moraju po regijama ispadati ... kao u stvarnosti"): the homes are one assignment
 *     for the whole set (group_assign), not a pass in table order where one club that did not
 *     fit at home took the next club's home place; a club sitting away from its home group (a
 *     guest) goes home as soon as a place there is free, and the recipe's border clubs
 *     (gborder lines) can make room in a full group -- see group_assign;
 *   - only at the set's own season end: the pass in which the game writes one of its upper
 *     leagues (16.11.2026, see groups_post: the season-end step also runs at New Year and in the
 *     autumn, with an INPUT entry for our leagues, and moved clubs by a half-season's table);
 *   - each league's new list is computed from the final standings, not from what the pass wrote:
 *     the clubs of the league that stay, the clubs that came from outside the set (relegated
 *     from the division above, promoted from a chain below) and the clubs it receives. A club the
 *     game moved along the one linked pair is put where the set says.
 * Nothing moves when any check fails (a league without standings or clubs, counts that do not
 * add up, a club that would be in two leagues or in none, a list past 48), and the log says why. */
#define MAX_GSETS  64
#define MAX_GSIDE  96   /* lab 20/11/2026: 32 -> 96, Argentina's Regional is one division of 70 zones */
#define MAX_GL     512      /* leagues the sets and play-offs name */
#define MAX_HOMES  16384
typedef struct {
  uint16_t id;
  uint32_t stand[MAX_CLUBS]; int nstand;
  uint32_t list[MAX_CLUBS];  int nlist;
  uint64_t flag;
  int seen;                 /* the pass wrote its list (captured in observe) */
  int input;                /* the pass had an INPUT entry for it */
  uint32_t slot; int slot_ok;
  int wslot;                /* 1 + its slot in the world file (fl26_chain_gslots), 0: not given */
  int played, matches;      /* 16.11.2026: its matches in the match table at the pass, for the log */
} gl_t;
typedef struct { uint16_t gl; uint8_t n; uint8_t pref; } gside_t;   /* gl index, count, upper index or 0xff */
typedef struct { int nup, nlow; gside_t up[MAX_GSIDE], low[MAX_GSIDE]; int active; } gset_t;
typedef struct { uint32_t tid; uint16_t league; } ghome_t;
static gl_t    g_gl[MAX_GL];      static int g_ngl = 0;
static gset_t  g_gset[MAX_GSETS]; static int g_ngset = 0;
static ghome_t g_home[MAX_HOMES]; static int g_nhome = 0;
/* 16.11.2026: the recipe's border clubs (zone_border, gborder lines), in its order: club tid of
   group `league` may move to the group `to` of its set when a club of `league`'s region comes
   down and `league` is full */
#define MAX_BORDERS 1024
typedef struct { uint16_t league, to; uint32_t tid; } gborder_t;
static gborder_t g_border[MAX_BORDERS]; static int g_nborder = 0;
/* the guests and border clubs an earlier set of this pass moved: a later set where that group is
   an upper league reads the club in its old group's standings and must leave it where it went
   (the TFF 2. Lig groups: below the 1. Lig in one set, above the 3. Lig groups in the next) */
#define MAX_GPIN 1024
static uint32_t g_pin_h[MAX_GPIN]; static uint16_t g_pin_to[MAX_GPIN]; static int g_npin = 0;

/* ---- play-offs (promotion / relegation) ----
 * A knockout of ours (the League Builder's, fl26swiss fills and dates it after the leagues' last
 * round) decides one place: its winner W must end the season-end step in the upper league `up`,
 * and the club C it is played against -- the default holder of the place (`hold`, the club the
 * counts move without a play-off: League One's 3rd for the Championship's play-off of 3rd to
 * 6th), or the other club of a two-club tie (the Bundesliga's 16th v the 2. Bundesliga's 3rd) --
 * in the lower league `low`. The winner is the game's own answer (0x1415799e0, right 0 of the
 * cup), and is taken only when it is one of the entrants by the final standings and played a
 * match of the cup this season; else the counts stand as they are and the log says why.
 * Inside a group set the play-off changes who goes up and down before the set is placed; for a
 * plain pair (moved by the game or by a chain here) W and C swap leagues afterwards, when W is
 * still in `low` and C in `up`. */
#define MAX_POFF   64
#define POFF_ENTRY 32
#define RIGHT_RVA  0x15799e0   /* rights(u32* out, u16 source, u32 type): type 0 = the winner */
typedef uint32_t* (*right_fn)(uint32_t* out, uint64_t source, uint32_t type);
typedef struct {
  uint16_t ko, up, low, hold_reg; uint8_t hold_pos; int ne;
  uint16_t ereg[POFF_ENTRY]; uint8_t epos[POFF_ENTRY];
  uint32_t w, c;            /* this season's winner and the club against it, 0 = not known */
  int used;                 /* taken by a group set this pass */
} poff_t;
static poff_t g_poff[MAX_POFF]; static int g_npoff = 0;

/* one club, two handles: the team id is the upper 18 bits, the row below may differ (fl26swiss B312) */
static int same_club(uint32_t a, uint32_t c)
{
  if ((a >> 14) && (c >> 14)) return (a >> 14) == (c >> 14);
  return a == c;
}
static int in_list(const uint32_t* l, int n, uint32_t h) { for (int i = 0; i < n; i++) if (same_club(l[i], h)) return 1; return 0; }
static int remove_same(uint32_t* list, int n, uint32_t h)
{
  for (int i = 0; i < n; i++) if (same_club(list[i], h)) { memmove(list + i, list + i + 1, (n - i - 1) * 4); return n - 1; }
  return -1;
}

static int gl_find(uint16_t id) { for (int i = 0; i < g_ngl; i++) if (g_gl[i].id == id) return i; return -1; }
static int gl_add(uint16_t id)
{
  int k = gl_find(id);
  if (k >= 0 || g_ngl >= MAX_GL) return k;
  memset(&g_gl[g_ngl], 0, sizeof g_gl[0]);
  g_gl[g_ngl].id = id;
  return g_ngl++;
}
static void gl_observe(uint16_t id, uint64_t flag)
{
  int k = gl_find(id);
  if (k >= 0) { g_gl[k].seen |= 1; g_gl[k].flag = flag; }
}
static int gl_member(uint16_t id)
{
  for (int s = 0; s < g_ngset; s++) {
    for (int k = 0; k < g_gset[s].nup; k++) if (g_gl[g_gset[s].up[k].gl].id == id) return 1;
    for (int k = 0; k < g_gset[s].nlow; k++) if (g_gl[g_gset[s].low[k].gl].id == id) return 1;
  }
  return 0;
}
/* a list written here: every copy of it the chains and the sets keep follows (B256) */
static void list_sync(uint16_t id, const uint32_t* l, int n)
{
  int k = gl_find(id);
  if (k >= 0) { memcpy(g_gl[k].list, l, n * 4); g_gl[k].nlist = n; g_gl[k].seen |= 2; }
  for (int i = 0; i < g_nchain; i++) {
    chain_t* o = &g_chain[i];
    if (o->cfg.mid == id) { memcpy(o->list_mid, l, n * 4); o->n_list_mid = n; }
    if (o->cfg.low == id) { memcpy(o->list_low, l, n * 4); o->n_list_low = n; }
  }
}

static int is_home(uint32_t h, uint16_t league)   /* the League Builder put club h in league: a club
                                                      has a home in each set it can drop into */
{
  uint32_t t = h >> 14; int a = 0, b = g_nhome - 1, at = -1;
  while (a <= b) { int m = (a + b) / 2; if (g_home[m].tid == t) { at = m; break; } if (g_home[m].tid < t) a = m + 1; else b = m - 1; }
  if (at < 0) return 0;
  while (at > 0 && g_home[at - 1].tid == t) at--;
  for (; at < g_nhome && g_home[at].tid == t; at++) if (g_home[at].league == league) return 1;
  return 0;
}

/* ---- who goes to which group (16.11.2026) ----
 * mato 16.11.2026: "Ali klubovi moraju po regijama ispadati ... Mora biti kao u stvarnosti."
 * Until then the relegated were placed one by one in table order: home if its group still had a
 * place, else the group with the most places left. One club whose home was full took the place
 * of the next club's home, and that club then took a third one's: a wrong group cascaded.
 * Now the whole season end of one side of a set is one assignment over plain arrays:
 *   - items: the clubs that move (relegated, or promoted on the upper side) with the targets that
 *     are their home (bits of `home`); guests -- a club that played the season in a group of the
 *     set that is not its home (its home was full when it came down) -- with the group they sit
 *     in (`cur`); border clubs (the recipe's zone_border) with the neighbours they may go to;
 *   - free[t]: the places of target t, the clubs it sent the other way (a group's size stays);
 *   - a moving guest or border club frees a place where it sits and takes one where it goes.
 * The choice: the most relegated clubs at home first; then the most staying clubs at home (a
 * guest come home counts one, a border club sent from its home one less); then the fewest border
 * clubs moved. So a free place of a group goes to a relegated club of its region first, to a
 * guest of its region next, and only then to a club of another region (placed after this by the
 * old rules: the group that names its league, else the most places left). Two guests in each
 * other's home groups swap, and so does any cycle, without a free place. Ties go to the items'
 * order (table order: the better placed first; guests and border clubs in the recipe's order),
 * found by a depth-first search that tries "home" first and keeps the first best: the same every
 * time. A set has a handful of clubs that move; the search is bounded (GA_STEPS) and keeps the
 * best found when it stops. choice[i]: the target of item i, -1 for none (a relegated club placed
 * by the old rules after, a guest or border club that stays). avail[t]: target t's places left.
 * Returns 1 when the search ran to the end, 0 when it stopped at GA_STEPS, -1 for bad input. */
#define GA_ITEMS 48
#define GA_TO    8
#define GA_STEPS 2000000L
enum { GA_REL = 0, GA_GUEST = 1, GA_BORDER = 2 };
typedef struct {
  int kind;              /* GA_REL, GA_GUEST, GA_BORDER */
  uint64_t home;         /* its home targets */
  int cur;               /* guest, border: the target it sits in */
  int nto; int to[GA_TO];  /* border: the targets it may go to, in the recipe's order */
} ga_item_t;
typedef struct {
  int nt, ni; const ga_item_t* it;
  int avail[64], pend[64];          /* places left; places a later guest / border club may free */
  int pick[GA_ITEMS], best[GA_ITEMS];
  int c1, c2, c3, have_trivial;
  int64_t best_score;
  int rest1[GA_ITEMS + 1], rest2[GA_ITEMS + 1];
  long steps;
} ga_ctx_t;
static int64_t ga_score(int c1, int c2, int c3) { return ((int64_t)c1 << 32) + ((int64_t)(c2 + 4096) << 16) + (c3 + 4096); }
static void ga_dfs(ga_ctx_t* x, int i)
{
  if (++x->steps > GA_STEPS) return;
  int64_t bound = ga_score(x->c1 + x->rest1[i], x->c2 + x->rest2[i], x->c3);
  if (x->have_trivial ? bound < x->best_score : bound <= x->best_score) return;
  if (i == x->ni) {
    for (int t = 0; t < x->nt; t++) if (x->avail[t] < 0) return;
    x->best_score = ga_score(x->c1, x->c2, x->c3); x->have_trivial = 0;
    memcpy(x->best, x->pick, sizeof(int) * x->ni);
    return;
  }
  const ga_item_t* e = &x->it[i];
  if (e->kind == GA_REL) {
    for (int t = 0; t < x->nt; t++) {
      if (!(e->home >> t & 1)) continue;
      x->avail[t]--;
      if (x->avail[t] + x->pend[t] >= 0) { x->pick[i] = t; x->c1++; ga_dfs(x, i + 1); x->c1--; }
      x->avail[t]++;
    }
    x->pick[i] = -1; ga_dfs(x, i + 1);
    return;
  }
  int c = e->cur, at_home = (int)(e->home >> c & 1);
  x->pend[c]--;                                  /* decided now: it frees c only by moving */
  if (e->kind == GA_GUEST) {
    for (int t = 0; t < x->nt; t++) {
      if (!(e->home >> t & 1) || t == c) continue;
      x->avail[t]--; x->avail[c]++;
      if (x->avail[t] + x->pend[t] >= 0) { x->pick[i] = t; x->c2++; ga_dfs(x, i + 1); x->c2--; }
      x->avail[t]++; x->avail[c]--;
    }
  } else {
    for (int k = 0; k < e->nto; k++) {          /* a border club: its neighbours in the recipe's order */
      int t = e->to[k];
      if (t < 0 || t >= x->nt || t == c) continue;
      x->avail[t]--; x->avail[c]++;
      if (x->avail[t] + x->pend[t] >= 0) {
        x->pick[i] = t; x->c2 -= at_home; x->c3--; ga_dfs(x, i + 1); x->c2 += at_home; x->c3++;
      }
      x->avail[t]++; x->avail[c]--;
    }
  }
  if (x->avail[c] + x->pend[c] >= 0) { x->pick[i] = -1; ga_dfs(x, i + 1); }
  x->pend[c]++;
}
static int group_assign(int nt, const int* free_, const ga_item_t* it, int ni, int* choice, int* avail, long* steps)
{
  static ga_ctx_t x;
  if (nt < 1 || nt > 64 || ni < 0 || ni > GA_ITEMS) return -1;
  memset(&x, 0, sizeof x);
  x.nt = nt; x.ni = ni; x.it = it;
  for (int t = 0; t < nt; t++) { if (free_[t] < 0) return -1; x.avail[t] = free_[t]; }
  for (int i = 0; i < ni; i++) {
    if (it[i].kind != GA_REL && (it[i].cur < 0 || it[i].cur >= nt)) return -1;
    if (it[i].kind != GA_REL) x.pend[it[i].cur]++;
  }
  for (int i = ni - 1; i >= 0; i--) {
    uint64_t hm = nt < 64 ? it[i].home & ((1ull << nt) - 1) : it[i].home;
    x.rest1[i] = x.rest1[i + 1] + (it[i].kind == GA_REL && hm);
    x.rest2[i] = x.rest2[i + 1] + (it[i].kind == GA_GUEST && hm);
  }
  /* the plan that always fits: nobody at home, nobody moves -- any plan as good found in the
     search is taken over it, so a tie still goes to the items' order */
  for (int i = 0; i < ni; i++) x.best[i] = -1;
  x.best_score = ga_score(0, 0, 0); x.have_trivial = 1;
  ga_dfs(&x, 0);
  for (int t = 0; t < nt; t++) avail[t] = free_[t];
  for (int i = 0; i < ni; i++) {
    choice[i] = x.best[i];
    if (choice[i] < 0) continue;
    avail[choice[i]]--;
    if (it[i].kind != GA_REL) avail[it[i].cur]++;
  }
  if (steps) *steps = x.steps;
  return x.steps > GA_STEPS ? 0 : 1;
}

/* the moves of one season end, for the log: one line a club (group_plan fills them) */
enum { MV_HOME = 0, MV_FULL, MV_NOHOME, MV_UP, MV_BACK, MV_BORDER };
typedef struct { uint32_t h; uint16_t from, to, home; uint8_t kind; } gmove_t;
#define GMOVE_MAX 512

typedef int (*gelig_fn)(uint32_t h);
typedef int (*gfix_fn)(uint32_t h, uint16_t league);   /* 1: the club leaves `league` another way this season end */
static uint64_t home_mask(uint32_t h, gl_t* const* m, int to0, int to1)
{
  uint64_t b = 0;
  for (int t = to0; t < to1; t++) if (is_home(h, m[t]->id)) b |= 1ull << (t - to0);
  return b;
}
static uint16_t pin_of(uint32_t h, const uint32_t* pin_h, const uint16_t* pin_to, int npin)
{
  for (int i = 0; i < npin; i++) if (same_club(pin_h[i], h)) return pin_to[i];
  return 0;
}
/* The set's new lists, pure: no game memory (tools/native/test_chain_groups.c). m[k] for k < nup
   are the upper leagues, the rest the groups below; n[k] the clubs each sends; pref[k] (groups) the
   upper index it names or -1; po: play-off results {W, C} pairs, npo of them. out[k]/nout[k] the
   new lists. 16.11.2026: fixed(h, league) says a club leaves that league another way (another
   set, a chain, a play-off) and may not move as a guest; pin_h/pin_to the clubs an earlier set
   of this pass moved as guests or border clubs (they stay where it put them); mv/nmv one entry a
   club that moves (GMOVE_MAX), *cut 1 when the search for homes stopped early. The ghome and
   border tables are read (is_home, g_border). Returns 0, or -1 with why[] filled when nothing
   may move. */
static int group_plan(gl_t* const* m, const int* n, const int* pref, int nup, int nlow,
                      const uint32_t* po, int npo, gelig_fn eligible, gfix_fn fixed,
                      const uint32_t* pin_h, const uint16_t* pin_to, int npin,
                      uint32_t out[][MAX_CLUBS], int* nout, int* flips,
                      gmove_t* mv, int* nmv, int* cut, char* why, int cap)
{
  int nm = nup + nlow;
  static uint32_t leave[2 * MAX_GSIDE][MAX_CLUBS], recv[2 * MAX_GSIDE][MAX_CLUBS];
  int nleave[2 * MAX_GSIDE], nrecv[2 * MAX_GSIDE];
  if (nup < 1 || nlow < 1 || nm > 2 * MAX_GSIDE) { snprintf(why, cap, "%d upper and %d lower leagues", nup, nlow); return -1; }
  for (int k = 0; k < nm; k++) {
    if (m[k]->nstand <= 0) { snprintf(why, cap, "%u has no final standings", m[k]->id); return -1; }
    if (m[k]->nlist <= 0) { snprintf(why, cap, "%u has no clubs", m[k]->id); return -1; }
    if (n[k] < 0 || n[k] >= m[k]->nstand) { snprintf(why, cap, "%u sends %d of %d clubs", m[k]->id, n[k], m[k]->nstand); return -1; }
    nleave[k] = nrecv[k] = 0;
    if (k < nup) {
      for (int i = m[k]->nstand - n[k]; i < m[k]->nstand; i++) leave[k][nleave[k]++] = m[k]->stand[i];
    } else {
      for (int i = 0; i < m[k]->nstand && nleave[k] < n[k]; i++)
        if (!eligible || eligible(m[k]->stand[i])) leave[k][nleave[k]++] = m[k]->stand[i];
      for (int i = 0; i < m[k]->nstand && nleave[k] < n[k]; i++)       /* as fix_chain: the top anyway */
        if (!in_list(leave[k], nleave[k], m[k]->stand[i])) leave[k][nleave[k]++] = m[k]->stand[i];
    }
  }
  /* a club in the standings of two leagues of the set */
  for (int a = 0; a < nm; a++) for (int i = 0; i < m[a]->nstand; i++)
    for (int b = a + 1; b < nm; b++)
      if (in_list(m[b]->stand, m[b]->nstand, m[a]->stand[i])) {
        snprintf(why, cap, "club %08x in the standings of %u and of %u", m[a]->stand[i], m[a]->id, m[b]->id); return -1;
      }
  /* play-offs: W ends on the upper side, C on the lower side (each flip is one club each way) */
  for (int p = 0; p < npo; p++) {
    uint32_t w = po[2 * p], c = po[2 * p + 1]; int kw = -1, kc = -1;
    for (int k = 0; k < nm; k++) {
      if (in_list(m[k]->stand, m[k]->nstand, w)) kw = k;
      if (in_list(m[k]->stand, m[k]->nstand, c)) kc = k;
    }
    if (kw < 0 || kc < 0 || w == c) continue;
    int up_w = kw < nup ? !in_list(leave[kw], nleave[kw], w) : in_list(leave[kw], nleave[kw], w);
    int up_c = kc < nup ? !in_list(leave[kc], nleave[kc], c) : in_list(leave[kc], nleave[kc], c);
    if (up_w && !up_c) continue;                                   /* the counts gave the same */
    if (up_w == up_c) continue;                                    /* both on one side: the counts stand */
    if (w >> 14 == 0 || c >> 14 == 0) continue;
    int r = remove_same(leave[kw], nleave[kw], w);
    if (r >= 0) nleave[kw] = r; else leave[kw][nleave[kw]++] = w;
    r = remove_same(leave[kc], nleave[kc], c);
    if (r >= 0) nleave[kc] = r; else leave[kc][nleave[kc]++] = c;
    if (flips) (*flips)++;
  }
  int sum_up = 0, sum_low = 0;
  for (int k = 0; k < nm; k++) {
    if (k < nup) sum_up += nleave[k]; else sum_low += nleave[k];
    if (nleave[k] >= m[k]->nstand) { snprintf(why, cap, "%u would send all its clubs", m[k]->id); return -1; }
  }
  if (sum_up != sum_low) { snprintf(why, cap, "%d go down, %d go up", sum_up, sum_low); return -1; }
  if (!sum_up) { snprintf(why, cap, "nobody to move"); return -1; }
  /* every club that moves is in a list of the set now */
  for (int k = 0; k < nm; k++) for (int i = 0; i < nleave[k]; i++) {
    int at = 0;
    for (int j = 0; j < nm && !at; j++) at = in_list(m[j]->list, m[j]->nlist, leave[k][i]);
    if (!at) { snprintf(why, cap, "club %08x of %u is in none of the set's leagues", leave[k][i], m[k]->id); return -1; }
  }
  /* placing: the promoted into the upper leagues, the relegated into the groups (16.11.2026:
     the homes as one assignment, group_assign; guests and border clubs only on the groups' side) */
  static uint32_t gin[2 * MAX_GSIDE][MAX_CLUBS]; int ngin[2 * MAX_GSIDE];
  uint32_t gone[GA_ITEMS]; int ngone = 0;            /* guests and border clubs leaving their group */
  int nmv_ = 0;
  for (int k = 0; k < nm; k++) ngin[k] = 0;
  if (cut) *cut = 0;
#define ADD_MV(H, F, T, HM, K) do { if (mv && nmv_ < GMOVE_MAX) { mv[nmv_].h = (H); mv[nmv_].from = m[F]->id; \
    mv[nmv_].to = m[T]->id; mv[nmv_].home = (HM); mv[nmv_].kind = (K); nmv_++; } } while (0)
  for (int side = 0; side < 2; side++) {
    int from0 = side ? 0 : nup, from1 = side ? nup : nm;           /* side 0: groups -> upper */
    int to0 = side ? nup : 0, to1 = side ? nm : nup, nt = to1 - to0;
    static ga_item_t it[GA_ITEMS]; static uint32_t ih[GA_ITEMS];
    static uint32_t mh[2 * MAX_GSIDE * MAX_CLUBS]; static int mf[2 * MAX_GSIDE * MAX_CLUBS];
    int ni = 0, nmov = 0, ifr[GA_ITEMS], choice[GA_ITEMS], avail[2 * MAX_GSIDE], fr[2 * MAX_GSIDE];
    for (int f = from0; f < from1; f++)
      for (int i = 0; i < nleave[f]; i++) { mh[nmov] = leave[f][i]; mf[nmov++] = f; }
    /* the movers in table order (the better placed of each league first, the leagues in the set's
       order); past GA_ITEMS of them the rest are placed one by one as before */
    int nrel = nmov < GA_ITEMS ? nmov : GA_ITEMS;
    for (int j = 0; j < nrel; j++) {
      memset(&it[ni], 0, sizeof it[ni]);
      it[ni].kind = GA_REL; it[ni].home = home_mask(mh[j], m, to0, to1); it[ni].cur = -1;
      ih[ni] = mh[j]; ifr[ni] = mf[j]; ni++;
    }
    if (side) {
      /* guests: a club of a group, staying in the division, whose home is another group of the set */
      for (int k = to0; k < to1 && ni < GA_ITEMS; k++)
        for (int i = 0; i < m[k]->nstand && ni < GA_ITEMS; i++) {
          uint32_t h = m[k]->stand[i]; int at = 0;
          if (in_list(leave[k], nleave[k], h) || !(h >> 14)) continue;
          for (int j = 0; j < nm && !at; j++) at = in_list(m[j]->list, m[j]->nlist, h);
          if (!at || pin_of(h, pin_h, pin_to, npin) || (fixed && fixed(h, m[k]->id))) continue;
          uint64_t hm = home_mask(h, m, to0, to1);
          if (!hm || (hm >> (k - to0) & 1)) continue;
          memset(&it[ni], 0, sizeof it[ni]);
          it[ni].kind = GA_GUEST; it[ni].home = hm; it[ni].cur = k - to0;
          ih[ni] = h; ifr[ni] = k; ni++;
        }
      /* border clubs (zone_border), in the recipe's order: one item a club, its neighbours in order */
      for (int b = 0; b < g_nborder && ni < GA_ITEMS; b++) {
        int k = -1, t = -1;
        for (int q = to0; q < to1; q++) { if (m[q]->id == g_border[b].league) k = q; if (m[q]->id == g_border[b].to) t = q; }
        if (k < 0 || t < 0 || k == t) continue;
        uint32_t h = 0;
        for (int i = 0; i < m[k]->nstand && !h; i++) if ((m[k]->stand[i] >> 14) == g_border[b].tid) h = m[k]->stand[i];
        if (!h || in_list(leave[k], nleave[k], h)) continue;
        int at = 0, dup = -1;
        for (int j = 0; j < nm && !at; j++) at = in_list(m[j]->list, m[j]->nlist, h);
        if (!at || pin_of(h, pin_h, pin_to, npin) || (fixed && fixed(h, m[k]->id))) continue;
        for (int q = 0; q < ni; q++) if (it[q].kind != GA_REL && same_club(ih[q], h)) dup = q;
        if (dup >= 0 && it[dup].kind == GA_GUEST) continue;          /* away already: it goes home as a guest */
        if (dup >= 0) { if (it[dup].nto < GA_TO) it[dup].to[it[dup].nto++] = t - to0; continue; }
        memset(&it[ni], 0, sizeof it[ni]);
        it[ni].kind = GA_BORDER; it[ni].home = home_mask(h, m, to0, to1); it[ni].cur = k - to0;
        it[ni].nto = 1; it[ni].to[0] = t - to0;
        ih[ni] = h; ifr[ni] = k; ni++;
      }
    }
    for (int t = 0; t < nt; t++) fr[t] = nleave[to0 + t];
    int r = group_assign(nt, fr, it, ni, choice, avail, 0);
    if (r < 0) { snprintf(why, cap, "%d leagues on one side", nt); return -1; }
    if (!r && cut) *cut = 1;
    for (int q = 0; q < ni; q++) {
      int c = choice[q];
      if (c < 0) continue;
      if (it[q].kind == GA_REL) { recv[to0 + c][nrecv[to0 + c]++] = ih[q]; ADD_MV(ih[q], ifr[q], to0 + c, m[to0 + c]->id, MV_HOME); }
      else {
        gin[to0 + c][ngin[to0 + c]++] = ih[q]; gone[ngone++] = ih[q];
        ADD_MV(ih[q], ifr[q], to0 + c, it[q].kind == GA_GUEST ? m[to0 + c]->id : m[ifr[q]]->id,
               it[q].kind == GA_GUEST ? MV_BACK : MV_BORDER);
      }
    }
    /* the rest by the old rules: a club past GA_ITEMS at home if there is room, then the league its
       group names / the group that names its league, then the most places left (the first on a tie) */
    for (int j = 0; j < nmov; j++) {
      if (j < nrel && choice[j] >= 0) continue;
      uint32_t h = mh[j]; int f = mf[j], best = -1;
      uint64_t hm = j < nrel ? it[j].home : home_mask(h, m, to0, to1);
      for (int t = 0; t < nt && best < 0 && j >= nrel; t++) if ((hm >> t & 1) && avail[t] > 0) best = t;
      int was_home = best >= 0;
      if (best < 0 && !side && pref[f] >= 0 && pref[f] < nup && avail[pref[f]] > 0)
        best = pref[f];                                              /* the league its group names */
      if (best < 0 && side)                                          /* a group that names its league */
        for (int t = 0; t < nt; t++)
          if (pref[to0 + t] == f && avail[t] > 0 && (best < 0 || avail[t] > avail[best])) best = t;
      if (best < 0)
        for (int t = 0; t < nt; t++)
          if (avail[t] > 0 && (best < 0 || avail[t] > avail[best])) best = t;
      if (best < 0) { snprintf(why, cap, "no place left for club %08x", h); return -1; }
      avail[best]--;
      recv[to0 + best][nrecv[to0 + best]++] = h;
      int hfirst = -1;
      for (int t = 0; t < nt && hfirst < 0; t++) if (hm >> t & 1) hfirst = t;
      ADD_MV(h, f, to0 + best, hfirst >= 0 ? m[to0 + hfirst]->id : 0,
             was_home ? MV_HOME : !side ? MV_UP : hfirst >= 0 ? MV_FULL : MV_NOHOME);
    }
  }
#undef ADD_MV
  if (nmv) *nmv = nmv_;
  /* the new lists: clubs from outside the set, the league's own that stay, the clubs an earlier
     set of this pass moved into it (pins), the guests and border clubs it takes, the ones it
     receives */
  for (int k = 0; k < nm; k++) {
    int o = 0;
    for (int i = 0; i < m[k]->nlist; i++) {
      uint32_t h = m[k]->list[i], ours = 0;
      for (int j = 0; j < nm && !ours; j++) ours = in_list(m[j]->stand, m[j]->nstand, h);
      if (!ours && !in_list(out[k], o, h)) { if (o >= MAX_CLUBS) goto full; out[k][o++] = h; }
    }
    for (int i = 0; i < m[k]->nstand; i++) {
      uint32_t h = m[k]->stand[i]; int at = 0;
      if (in_list(leave[k], nleave[k], h) || in_list(gone, ngone, h)) continue;
      uint16_t pj = pin_of(h, pin_h, pin_to, npin);
      if (pj && pj != m[k]->id) continue;                           /* an earlier set moved it on */
      for (int j = 0; j < nm && !at; j++) at = in_list(m[j]->list, m[j]->nlist, h);
      if (!at) continue;                                            /* gone out of the set (up a division, down a chain) */
      if (o >= MAX_CLUBS) goto full;
      out[k][o++] = h;
    }
    for (int j = 0; j < nm && npin; j++) {
      if (j == k) continue;
      for (int i = 0; i < m[j]->nstand; i++) {
        uint32_t h = m[j]->stand[i]; int at = 0;
        if (pin_of(h, pin_h, pin_to, npin) != m[k]->id || in_list(leave[j], nleave[j], h) || in_list(gone, ngone, h)) continue;
        for (int q = 0; q < nm && !at; q++) at = in_list(m[q]->list, m[q]->nlist, h);
        if (!at) continue;
        if (o >= MAX_CLUBS) goto full;
        out[k][o++] = h;
      }
    }
    for (int i = 0; i < ngin[k]; i++) { if (o >= MAX_CLUBS) goto full; out[k][o++] = gin[k][i]; }
    for (int i = 0; i < nrecv[k]; i++) { if (o >= MAX_CLUBS) goto full; out[k][o++] = recv[k][i]; }
    if (!o) { snprintf(why, cap, "%u would have no clubs", m[k]->id); return -1; }
    nout[k] = o;
    continue;
full:
    snprintf(why, cap, "%u would have more than %d clubs", m[k]->id, MAX_CLUBS); return -1;
  }
  for (int a = 0; a < nm; a++) for (int i = 0; i < nout[a]; i++)
    for (int b = a + 1; b < nm; b++)
      if (in_list(out[b], nout[b], out[a][i])) { snprintf(why, cap, "club %08x would be in %u and in %u", out[a][i], m[a]->id, m[b]->id); return -1; }
  return 0;
}

/* The winner of a play-off from its played matches: every tie is two entrants who met in matches
   of the cup (one or two legs; goals with extra time, then penalties, as fl26swiss's ko_winner
   reads them), its loser is out, and the play-off is over when ne - 1 ties are decided and one
   entrant is left. Pure over the match records (mt, cap of them, MATCH_STRIDE apart), for the test.
   0 with why[] filled when it is not over or not clear; the counts then stand. */
static int ko_goals(const unsigned char* m, int side) { return m[0x1c + 3 * side] + m[0x1d + 3 * side]; }
static uint32_t poff_decide(const unsigned char* mt, uint32_t cap, uint16_t ko, const uint32_t* ent, int ne, char* why, int wcap)
{
  int ta[POFF_ENTRY], tb[POFF_ENTRY], ga[POFF_ENTRY], gb[POFF_ENTRY], pa[POFF_ENTRY], pb[POFF_ENTRY], legs[POFF_ENTRY], nt = 0, out[POFF_ENTRY];
  if (ne < 2 || ne > POFF_ENTRY) { snprintf(why, wcap, "%d entrants", ne); return 0; }
  for (uint32_t i = 0; i < cap; i++) {
    const unsigned char* m = mt + (size_t)i * MATCH_STRIDE;
    if (*(const uint16_t*)m == 0xffff || !(m[7] & 0x40) || *(const uint16_t*)(m + 4) != ko) continue;
    uint32_t h = *(const uint32_t*)(m + 0x14), a = *(const uint32_t*)(m + 0x18);
    int x = -1, y = -1;
    for (int k = 0; k < ne; k++) { if (same_club(ent[k], h)) x = k; if (same_club(ent[k], a)) y = k; }
    if (x < 0 || y < 0 || x == y) { snprintf(why, wcap, "a played match of %08x v %08x, not two of this season's entrants", h, a); return 0; }
    int t = 0;
    while (t < nt && !((ta[t] == x && tb[t] == y) || (ta[t] == y && tb[t] == x))) t++;
    if (t == nt) {
      if (nt >= POFF_ENTRY) return 0;
      ta[t] = x; tb[t] = y; ga[t] = gb[t] = pa[t] = pb[t] = legs[t] = 0; nt++;
    }
    int hx = ta[t] == x;                                             /* the tie's first club at home */
    ga[t] += ko_goals(m, hx ? 0 : 1); gb[t] += ko_goals(m, hx ? 1 : 0);
    pa[t] += m[hx ? 0x1e : 0x21];   pb[t] += m[hx ? 0x21 : 0x1e];
    if (++legs[t] > 2) { snprintf(why, wcap, "%08x and %08x met %d times", ent[x], ent[y], legs[t]); return 0; }
  }
  if (nt != ne - 1) { snprintf(why, wcap, "%d of its %d ties played", nt, ne - 1); return 0; }
  for (int k = 0; k < ne; k++) out[k] = 0;
  for (int t = 0; t < nt; t++) {
    int a = ga[t], b = gb[t];
    if (a == b) { a = pa[t]; b = pb[t]; }
    if (a == b) { snprintf(why, wcap, "the tie of %08x and %08x level", ent[ta[t]], ent[tb[t]]); return 0; }
    int loser = a > b ? tb[t] : ta[t];
    if (out[loser]) { snprintf(why, wcap, "%08x lost two ties", ent[loser]); return 0; }
    out[loser] = 1;
  }
  int left = -1;
  for (int k = 0; k < ne; k++) if (!out[k]) { if (left >= 0) { snprintf(why, wcap, "more than one club left"); return 0; } left = k; }
  return left >= 0 ? ent[left] : 0;
}

/* the match records: offset and count from the code the caps patch writes, as apclau_table reads them */
static const unsigned char* match_table(uint32_t* cap)
{
  const unsigned char* bs = (const unsigned char*)(uintptr_t)(g_base + MATCH_BASE_SITE);
  const unsigned char* cs = (const unsigned char*)(uintptr_t)(g_base + MATCH_CAP_SITE);
  if (bs[0] != 0x48 || bs[1] != 0x8d || bs[2] != 0x88 || cs[0] != 0x81 || cs[1] != 0xff) return 0;
  uint32_t base = *(const uint32_t*)(bs + 3), c = *(const uint32_t*)(cs + 2);
  unsigned char* blk = block();
  if (!blk || !c || c > 200000) return 0;
  *cap = c;
  return blk + base;
}

/* a club the mover would promote: +0x628 is the "no parent club" sentinel (fix_chain) */
static int club_eligible(uint32_t h)
{
  unsigned char* blk = block(); if (!blk) return 1;
  unsigned char* c = ((club_fn)(uintptr_t)(g_base + CLUB_RVA))(blk, h);
  return c && *(uint32_t*)(c + OFF_PARENT) == *(uint32_t*)(uintptr_t)(g_base + NOPARENT_RVA);
}

/* standings as standings() reads them, without its log line (a world can have dozens of groups) */
static int quiet_standings(void* ctx, uint16_t id, uint32_t* out)
{
  int n = split_group(id) ? kept_table(id, out) : 0;   /* a split group's final table (split_table) */
  if (n > 0) return n;
  n = fetch_standings(ctx, id, out);
  if (n > 0) return n;
  int t = fetch_table(id, out);
  if (t <= 0) t = split_table(ctx, id, out, 0);
  if (t <= 0 && split_group(id)) t = kept_table(id, out);   /* a play-off's place in a split group */
  return t < 0 ? 0 : t;
}

/* the slot most of the clubs carry (the lowest of them on a tie); *n: how many clubs had a record */
static int slot_of_most(unsigned char* blk, const uint32_t* h, int nh, uint32_t* slot, int* n)
{
  club_fn club = (club_fn)(uintptr_t)(g_base + CLUB_RVA);
  static uint16_t cnt[512];
  memset(cnt, 0, sizeof cnt);
  int best = -1; *n = 0;
  for (int i = 0; i < nh && blk; i++) {
    unsigned char* c = club(blk, h[i]);
    if (c) { cnt[lay_slot(c) & 0x1ff]++; (*n)++; }
  }
  for (int s = 0; s < 512; s++) if (cnt[s] && (best < 0 || cnt[s] > cnt[best])) best = s;
  if (best < 0) return 0;
  *slot = (uint32_t)best;
  return cnt[best];
}

static void groups_pre(void* ctx)
{
  if (!g_ngset && !g_npoff) return;
  unsigned char* blk = block();
  for (int k = 0; k < g_ngl; k++) {
    gl_t* g = &g_gl[k];
    uint32_t pre[MAX_CLUBS];
    g->seen = 0; g->flag = 1; g->nlist = 0; g->slot_ok = 0;
    g->input = ((input_fn)(uintptr_t)(g_base + INPUT_RVA))(ctx, g->id) != 0;
    /* a group the game does not link may have no INPUT entry: its season table then */
    g->nstand = quiet_standings(ctx, g->id, g->stand);
    /* The league's slot byte: every club it ends with gets it. B418 (11.11.2026, the season
       test of beta 2 on the Megapack): it was the slot of the FIRST club the league held before
       the pass, and one club with another league's slot -- the game's own mover gives a club it
       takes for promoted the upper league's slot after our move -- made it the whole league's:
       Indonesia's "group 252" and "group 955" wrote slot 64, the Super League's, for 126 and
       397, and 25 to 30 of the 49 group leagues had another slot from the second pass on. So:
       the slot the world file gives the league (fl26_chain_gslots); for a league it does not
       name, the slot most of its clubs carry -- the list's, else the season table's (FL27
       Megapack 07.11.: at the season end the pass had already emptied the upper leagues' lists,
       3. Liga 376, 82, 80; the table still names the clubs). */
    int n = reg_list(g->id, pre), have = 0, most = 0;
    uint32_t theirs = 0;
    most = slot_of_most(blk, pre, n, &theirs, &have);
    if (!most) most = slot_of_most(blk, g->stand, g->nstand, &theirs, &have);
    if (g->wslot) { g->slot = (uint32_t)(g->wslot - 1); g->slot_ok = 1; }
    else if (most) { g->slot = theirs; g->slot_ok = 1; }
    if (g->slot_ok && g->input && have && (theirs != g->slot || most != have))
      logf("group league %u: slot %u%s -- %d of its %d club(s) carried slot %u before the pass", g->id, g->slot,
           g->wslot ? " (the world file's)" : " (most of its clubs')", most, have, theirs);
    if (!g->slot_ok && g->input) logf("group league %u: no club before the pass (list %d, table %d)", g->id, n, g->nstand);
  }
  uint32_t cap = 0; const unsigned char* mt = 0; int mt_read = 0;
  for (int i = 0; i < g_npoff; i++) {
    poff_t* p = &g_poff[i];
    int ku = gl_find(p->up), kl = gl_find(p->low);
    p->w = p->c = 0; p->used = 0;
    if (ku < 0 || kl < 0 || !(g_gl[ku].input || g_gl[kl].input)) continue;     /* not their season's end */
    if (!mt_read) { mt = match_table(&cap); mt_read = 1; }
    uint32_t ent[POFF_ENTRY]; char why[160]; int ok = 1;
    for (int e = 0; e < p->ne && ok; e++) {
      int k = gl_find(p->ereg[e]);
      if (k < 0 || p->epos[e] < 1 || p->epos[e] > g_gl[k].nstand) {
        logf("play-off %u: %u has no %u. place in its standings -- the counts stand", p->ko, p->ereg[e], p->epos[e]); ok = 0;
      } else ent[e] = g_gl[k].stand[p->epos[e] - 1];
    }
    if (!ok) continue;
    if (!mt) { logf("play-off %u: the match table's walk is not where it was -- the counts stand", p->ko); continue; }
    uint32_t w = poff_decide(mt, cap, p->ko, ent, p->ne, why, sizeof why);
    if (!w) {
      /* its matches gone by now: the winner fl26swiss kept when the last one was played, if it
         is one of this season's entrants */
      uint32_t k = kept_winner(p->ko);
      for (int e = 0; e < p->ne && k; e++) if (same_club(ent[e], k)) { w = ent[e]; break; }
      if (w) logf("play-off %u: its matches gone (%s) -- won by %08x as fl26swiss kept it", p->ko, why, w);
    }
    if (!w) { logf("play-off %u: no winner (%s) -- the counts stand", p->ko, why); continue; }
    uint32_t c = 0;
    if (p->hold_reg) {
      int k = gl_find(p->hold_reg);
      if (k >= 0 && p->hold_pos >= 1 && p->hold_pos <= g_gl[k].nstand) c = g_gl[k].stand[p->hold_pos - 1];
    } else if (p->ne == 2) c = same_club(ent[0], w) ? ent[1] : ent[0];
    if (!c) { logf("play-off %u: won by %08x, the place's holder not found -- the counts stand", p->ko, w); continue; }
    p->w = w; p->c = c;
    logf("play-off %u: won by %08x%s%08x", p->ko, w, same_club(w, c) ? " -- the place's holder " : ", against ", c);
  }
}

static void write_list(uint16_t id, uint32_t* l, int n, uint64_t flag)
{
  vec32_t v = { l, l + n, l + MAX_CLUBS };
  int was = g_reentrant; g_reentrant = 1;
  ((set_fn)(uintptr_t)g_tramp_set)(id, &v, flag);
  g_reentrant = was;
  list_sync(id, l, n);
}

/* 16.11.2026: a club that leaves `league` another way this season end may not move as a guest or
   a border club -- the set where the league is above (the bottom of a TFF 2. Lig group goes down
   to the 3. Lig in the next set), a chain of ours under it (Délnyugat -> Baranya), a play-off it
   plays in. Moved as a guest it would come back in that set's lists and a group would lose a club
   and another get one too many. A lower group's top places in another set: with two more for the
   clubs that may not go up. Every set but g_fix_set. */
static int g_fix_set = -1;
static int guest_fixed(uint32_t h, uint16_t league)
{
  int k = gl_find(league), pos = -1;
  if (k < 0) return 1;
  const gl_t* g = &g_gl[k];
  for (int i = 0; i < g->nstand; i++) if (same_club(g->stand[i], h)) { pos = i; break; }
  if (pos < 0) return 1;
  for (int s = 0; s < g_ngset; s++) {
    if (s == g_fix_set) continue;
    const gset_t* gs = &g_gset[s];
    for (int q = 0; q < gs->nup; q++) if (gs->up[q].gl == k && pos >= g->nstand - gs->up[q].n) return 1;
    for (int q = 0; q < gs->nlow; q++) if (gs->low[q].gl == k && pos < gs->low[q].n + 2) return 1;
  }
  for (int i = 0; i < g_nchain; i++) {
    const chain_t* ch = &g_chain[i];
    if (ch->cfg.mid == league && pos >= g->nstand - ch->cfg.demote_mid) return 1;
    if (ch->cfg.low == league && pos < ch->cfg.promote_low + 2) return 1;
  }
  for (int i = 0; i < g_npoff; i++)
    if ((g_poff[i].w && same_club(g_poff[i].w, h)) || (g_poff[i].c && same_club(g_poff[i].c, h))) return 1;
  return 0;
}

/* ---- at which pass a set moves (16.11.2026) ----
 * The game runs its season-end step (apply) several times a season, and every one of them that
 * has an INPUT entry for a league of a set used to move the set. Two in-game seasons of the
 * GigaPack world (notes/grupe-promocije-1611.md, sections 10 and 11) had such a pass at New Year
 * (the calendar-year step: the calendar cups and our calendar-year chains are written in it) and,
 * in the second season, one in the autumn: the sets were moved by the half-season's table, or by
 * last season's, and the club lists and league slots stayed wrong until the step of 1 July put
 * them right -- for as long as that step did not refuse. In those passes the game wrote none of
 * the sets' upper leagues (no chain over them was written either: no "fix" line), at 1 July it
 * wrote them all. That is the rule the chains have (both lists written by the game, apply_post):
 * a set moves only in a pass where the game itself writes one of its upper leagues -- the league
 * the League Builder links to the set's first group, so the game closes their season together.
 * Argentina's set (February-December) is then moved at New Year, the one pass its upper league is
 * written in. A set whose upper league the game never writes would never move: its log then has
 * "not its season's end, untouched" at every pass and no "season end" line -- the tester's sign.
 * GROUP_DIAG_ONLY builds the old trigger (any INPUT entry) with the pass line alone, to measure. */
static const uint16_t G_MONTH0[13] = { 0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334, 365 };
/* the game's date as fl26join's game_date reads it: the day counter (0 = 1 January, no leap days)
   and the year 8 bytes past it. The pass's lines reach sider.log only when the loader drains the
   log -- after a fast-forward stops, months of game time later -- so the line carries its date. */
static void pass_date(char* out, int cap)
{
  unsigned char* blk = block();
  int t = blk ? *(const uint16_t*)(blk + lay_today()) : -1, y = blk ? *(const uint16_t*)(blk + lay_today() + 8) : 0;
  if (t < 0 || t >= 365 || y < 1990 || y > 2200) { snprintf(out, cap, "date ?"); return; }
  int mo = 0;
  while (mo < 11 && t >= G_MONTH0[mo + 1]) mo++;
  snprintf(out, cap, "%02d.%02d.%d", t - G_MONTH0[mo] + 1, mo + 1, y);
}
/* each set league's played and scheduled matches in the match table, one walk a pass; 0 when the
   table's walk is not where it was (the line then says "played ?") */
static int gl_matches(void)
{
  for (int k = 0; k < g_ngl; k++) g_gl[k].played = g_gl[k].matches = 0;
  uint32_t cap = 0; const unsigned char* mt = match_table(&cap);
  if (!mt) return 0;
  static uint16_t at[65536];                     /* league id -> 1 + its index in g_gl */
  for (int k = 0; k < g_ngl; k++) at[g_gl[k].id] = (uint16_t)(k + 1);
  for (uint32_t i = 0; i < cap; i++) {
    const unsigned char* m = mt + (size_t)i * MATCH_STRIDE;
    if (*(const uint16_t*)m == 0xffff) continue;
    int k = at[*(const uint16_t*)(m + 4)];
    if (!k) continue;
    g_gl[k - 1].matches++;
    if (m[7] & 0x40) g_gl[k - 1].played++;
  }
  for (int k = 0; k < g_ngl; k++) at[g_gl[k].id] = 0;
  return 1;
}

static void groups_post(void)
{
  g_npin = 0;
  if (!g_ngset) return;
  char today[24]; pass_date(today, sizeof today);
  int have_matches = gl_matches();
  unsigned char* blk = block();
  club_fn club = (club_fn)(uintptr_t)(g_base + CLUB_RVA);
  uint64_t any_flag = 1; int have_flag = 0;
  for (int k = 0; k < g_ngl && !have_flag; k++) if (g_gl[k].seen & 1) { any_flag = g_gl[k].flag; have_flag = 1; }
  /* 16.11.2026: a set whose upper leagues are the groups of another set goes after it (the TFF 3.
     Lig groups' set after the TFF 2. Lig groups' set), whatever the world file's order: the guests
     the set above brings home are pinned before the set below reads those groups, so a second
     pass of the same season end finds every league already holding its clubs. Before 16.11. no
     club stayed in a group other than its own and the order did not matter. */
  int ord[MAX_GSETS], nord = 0, done[MAX_GSETS] = { 0 };
  while (nord < g_ngset) {
    int took = 0;
    for (int s = 0; s < g_ngset; s++) {
      if (done[s]) continue;
      int wait = 0;
      for (int a = 0; a < g_ngset && !wait; a++) {
        if (a == s || done[a]) continue;
        for (int q = 0; q < g_gset[a].nlow && !wait; q++)
          for (int u = 0; u < g_gset[s].nup && !wait; u++) wait = g_gset[a].low[q].gl == g_gset[s].up[u].gl;
      }
      if (!wait) { ord[nord++] = s; done[s] = 1; took = 1; }
    }
    if (!took) for (int s = 0; s < g_ngset; s++) if (!done[s]) { ord[nord++] = s; done[s] = 1; }   /* a loop: the file's order */
  }
  for (int oi = 0; oi < g_ngset; oi++) {
    int s = ord[oi];
    gset_t* gs = &g_gset[s];
    gl_t* m[2 * MAX_GSIDE]; int n[2 * MAX_GSIDE], pref[2 * MAX_GSIDE], nm = gs->nup + gs->nlow, input = 0, seen = 0;
    int nin = 0, upw = 0, loww = 0, ntab = 0, played = 0, matches = 0;
    for (int k = 0; k < nm; k++) {
      const gside_t* sd = k < gs->nup ? &gs->up[k] : &gs->low[k - gs->nup];
      m[k] = &g_gl[sd->gl]; n[k] = sd->n; pref[k] = k >= gs->nup && sd->pref != 0xff ? sd->pref : -1;
      input |= m[k]->input; seen |= m[k]->seen & 1;
      nin += m[k]->input != 0; ntab += m[k]->nstand > 0;
      if (m[k]->seen & 1) { if (k < gs->nup) upw++; else loww++; }
      played += m[k]->played; matches += m[k]->matches;
    }
    /* 16.11.2026: what the module sees at this pass, one line a set (see "at which pass a set
       moves" above): the date, the INPUT entries, the lists the game wrote, the matches, the tables */
    char pl[32];
    if (have_matches) snprintf(pl, sizeof pl, "%d/%d", played, matches); else snprintf(pl, sizeof pl, "?");
#ifdef GROUP_DIAG_ONLY
    logf("group set %d pass %s: input %d/%d, game wrote upper %d/%d groups %d/%d, played %s, tables %d/%d -> acts: %s now, %s if upper written",
         s, today, nin, nm, upw, gs->nup, loww, gs->nlow, pl, ntab, nm, input ? "yes" : "no", input && upw ? "yes" : "no");
#else
    if (input || seen)
      logf("group set %d pass %s: input %d/%d, game wrote upper %d/%d groups %d/%d, played %s, tables %d/%d",
           s, today, nin, nm, upw, gs->nup, loww, gs->nlow, pl, ntab, nm);
#endif
    if (!input) {
      if (seen) logf("group set %d (%u ...): written by the pass without an INPUT entry -- untouched", s, m[0]->id);
      continue;
    }
    if (!blk) { logf("group set %d: no block", s); g_stat[3]++; continue; }
    for (int k = 0; k < nm; k++) { int c = reg_list(m[k]->id, m[k]->list); m[k]->nlist = c < 0 ? 0 : c; }
    uint32_t po[2 * MAX_POFF]; int npo = 0;
    for (int i = 0; i < g_npoff; i++) {
      poff_t* p = &g_poff[i]; int iu = 0, il = 0;
      if (!p->w) continue;
      for (int k = 0; k < nm; k++) { if (k < gs->nup && m[k]->id == p->up) iu = 1; if (k >= gs->nup && m[k]->id == p->low) il = 1; }
      if (iu && il) { po[2 * npo] = p->w; po[2 * npo + 1] = p->c; npo++; p->used = 1; }
    }
#ifndef GROUP_DIAG_ONLY
    /* not the set's season end: nothing is written (lists, slots), and its play-offs stay marked
       used above, so poff_post does not take one of them for a plain pair and swap it alone */
    if (!upw) {
      logf("group set %d (%u ...): not its season's end, untouched -- the game wrote none of its upper leagues in this pass", s, m[0]->id);
      continue;
    }
    logf("group set %d (%u ...): season end -- the game wrote %d of its %d upper league(s) in this pass", s, m[0]->id, upw, gs->nup);
#endif
    static uint32_t out[2 * MAX_GSIDE][MAX_CLUBS]; int nout[2 * MAX_GSIDE], flips = 0, nmv = 0, cut = 0; char why[200];
    static gmove_t mv[GMOVE_MAX];
    g_fix_set = s;
    int bad = group_plan(m, n, pref, gs->nup, gs->nlow, po, npo, club_eligible, guest_fixed, g_pin_h, g_pin_to, g_npin,
                         out, nout, &flips, mv, &nmv, &cut, why, sizeof why);
    g_fix_set = -1;
    if (bad) {
      logf("group set %d (%u ...): nothing moved -- %s", s, m[0]->id, why); g_stat[2]++; continue;
    }
    int changed = 0;
    for (int k = 0; k < nm; k++) {
      if (nout[k] != m[k]->nlist) changed = 1;
      else for (int i = 0; i < nout[k] && !changed; i++) if (!in_list(m[k]->list, m[k]->nlist, out[k][i])) changed = 1;
    }
    /* a guest or border club moved here stays where it went for the sets after this one */
#define PIN_MOVES() for (int q = 0; q < nmv; q++) \
      if ((mv[q].kind == MV_BACK || mv[q].kind == MV_BORDER) && g_npin < MAX_GPIN) { g_pin_h[g_npin] = mv[q].h; g_pin_to[g_npin++] = mv[q].to; }
    if (!changed) {
      PIN_MOVES();
      logf("group set %d (%u ...): every league already holds its new clubs", s, m[0]->id); g_stat[3]++; continue;
    }
    int noslot = -1;
    for (int k = 0; k < nm && noslot < 0; k++) if (!m[k]->slot_ok) noslot = k;
    if (noslot >= 0) { logf("group set %d: %u held no club before the pass, its slot is not known -- nothing moved", s, m[noslot]->id); g_stat[2]++; continue; }
    for (int k = 0; k < nm; k++)
      for (int i = 0; i < nout[k]; i++) { unsigned char* c = club(blk, out[k][i]); if (c) lay_set_slot(c, m[k]->slot); }
    for (int k = 0; k < nm; k++) write_list(m[k]->id, out[k], nout[k], (m[k]->seen & 1) ? m[k]->flag : any_flag);
    g_stat[1]++;
    int down = 0, up = 0;
    for (int k = 0; k < nm; k++) { if (k < gs->nup) down += n[k]; else up += n[k]; }
    logf("group set %d: %d upper, %d lower league(s), %d down and %d up by the counts, %d play-off change(s)", s, gs->nup, gs->nlow, down, up, flips);
    for (int k = 0; k < nm; k++)
      logf("  %s %u: %d -> %d clubs, slot %u", k < gs->nup ? "upper" : "group", m[k]->id, m[k]->nlist, nout[k], m[k]->slot);
    PIN_MOVES();
    /* 16.11.2026: where every club went, one line a club (team id, league it leaves -> league),
       so a tester can check each relegated club's group against the world file's ghome lines */
    for (int q = 0; q < nmv; q++) {
      const gmove_t* e = &mv[q]; char what[80];
      switch (e->kind) {
        case MV_HOME:   snprintf(what, sizeof what, "home"); break;
        case MV_FULL:   snprintf(what, sizeof what, "guest: home %u full", e->home); break;
        case MV_NOHOME: snprintf(what, sizeof what, "no home group in the set"); break;
        case MV_UP:     snprintf(what, sizeof what, "promoted"); break;
        case MV_BACK:   snprintf(what, sizeof what, "guest came home from %u", e->from); break;
        default:        snprintf(what, sizeof what, "border club: makes room in %u", e->from); break;
      }
      logf("group set %d: club %u %u -> %u (%s)", s, e->h >> 14, e->from, e->to, what);
    }
    if (cut) logf("group set %d: the search for home groups stopped after %ld steps -- the best found is used", s, GA_STEPS);
  }
#undef PIN_MOVES
}

/* a play-off between two leagues outside any group set: W and C swap when the move left W below */
static void poff_post(void)
{
  unsigned char* blk = block();
  club_fn club = (club_fn)(uintptr_t)(g_base + CLUB_RVA);
  for (int i = 0; i < g_npoff; i++) {
    poff_t* p = &g_poff[i];
    if (!p->w || p->used || same_club(p->w, p->c)) continue;
    uint32_t lu[MAX_CLUBS], ll[MAX_CLUBS]; int nu = reg_list(p->up, lu), nl = reg_list(p->low, ll), iw = -1, ic = -1;
    if (nu < 0) nu = 0;
    if (nl < 0) nl = 0;
    for (int k = 0; k < nl; k++) if (same_club(ll[k], p->w)) iw = k;
    for (int k = 0; k < nu; k++) if (same_club(lu[k], p->c)) ic = k;
    if (iw < 0 || ic < 0) {
      if (in_list(lu, nu, p->w) && in_list(ll, nl, p->c))
        logf("play-off %u: %08x already in %u, %08x in %u", p->ko, p->w, p->up, p->c, p->low);
      else
        logf("play-off %u: %08x not in %u or %08x not in %u after the move -- untouched", p->ko, p->w, p->low, p->c, p->up);
      continue;
    }
    if (!blk) continue;
    uint32_t w = ll[iw], c = lu[ic];
    unsigned char* rw = club(blk, w); unsigned char* rc = club(blk, c);
    if (!rw || !rc) { logf("play-off %u: no club record for %08x or %08x -- untouched", p->ko, w, c); continue; }
    uint32_t sw = lay_slot(rw), sc = lay_slot(rc);
    lu[ic] = w; ll[iw] = c;
    lay_set_slot(rw, sc); lay_set_slot(rc, sw);
    int ku = gl_find(p->up), kl = gl_find(p->low);
    uint64_t fu = ku >= 0 && (g_gl[ku].seen & 1) ? g_gl[ku].flag : 1, fl = kl >= 0 && (g_gl[kl].seen & 1) ? g_gl[kl].flag : fu;
    write_list(p->up, lu, nu, fu);
    write_list(p->low, ll, nl, fl);
    g_stat[1]++;
    logf("play-off %u: %08x goes up to %u, %08x down to %u", p->ko, w, p->up, c, p->low);
  }
}

/* A split league plays its season in the regular phase, not in the total the chain fixes
   (GitHub #79/#81, Egypt 2026-10-06). The season pass writes the phase with last season's
   clubs before apply returns, so it is brought along here: each relegated club's place goes
   to a promoted one, matched by team id (the upper 18 bits; the lower 14 are a row). */
static void split_regular(chain_t* ch, set_fn orig, const uint32_t* down, int nd, const uint32_t* up, int nu)
{
  uint32_t cur[MAX_CLUBS]; int n = reg_list(ch->cfg.regular, cur), swapped = 0;
  if (n <= 0) { logf("fix %u: regular phase %u has no clubs, left as it is", ch->cfg.mid, ch->cfg.regular); return; }
  for (int i = 0; i < nd && i < nu; i++) {
    int at = -1, have = 0;
    for (int j = 0; j < n; j++) {
      if ((cur[j] >> 14) == (down[i] >> 14)) at = j;
      if ((cur[j] >> 14) == (up[i] >> 14)) have = 1;
    }
    if (at >= 0 && !have) { cur[at] = up[i]; swapped++; }
  }
  if (!swapped) { logf("fix %u: regular phase %u already holds the new clubs", ch->cfg.mid, ch->cfg.regular); return; }
  vec32_t v = { cur, cur + n, cur + MAX_CLUBS };
  g_reentrant = 1;
  orig(ch->cfg.regular, &v, (ch->seen & 4) ? ch->flag_reg : ch->flag_mid);
  g_reentrant = 0;
  logf("fix %u: regular phase %u -- %d relegated club(s) replaced by the promoted, %d clubs",
       ch->cfg.mid, ch->cfg.regular, swapped, n);
}

static void fix_chain(chain_t* ch)
{
  unsigned char* blk = block(); if (!blk) { logf("fix: no block"); g_stat[3]++; return; }
  club_fn club = (club_fn)(uintptr_t)(g_base + CLUB_RVA);
  int k = ch->cfg.demote_mid, p = ch->cfg.promote_low;
  uint32_t down[MAX_CLUBS], up[MAX_CLUBS]; int nd = 0, nu = 0;

  if (ch->n_stand_mid >= k) for (int i = ch->n_stand_mid - k; i < ch->n_stand_mid; i++) down[nd++] = ch->stand_mid[i];
  if (ch->cfg.regular) {
    char line[24 * 9 + 1]; int o = 0;
    for (int i = 0; i < ch->n_stand_mid && i < 24; i++) o += snprintf(line + o, sizeof line - o, " %08x", ch->stand_mid[i]);
    logf("fix %u->%u: standings%s", ch->cfg.mid, ch->cfg.low, line);
  }
  /* The mover promotes a club only when its +0x628 equals the global sentinel at
     0x14351ae44 -- read at 0x141365827, compared in two halves (low 14 bits at 0x14136582f,
     upper 18 at 0x141365839), which is the same split the club id uses. Measured live on
     2026-09-21: the sentinel is 0xffffffff and all 1486 clubs, ours and shipped, carry it.
     The earlier test here demanded zero, which is why the 2026-09-20 season promoted nobody. */
  uint32_t none = *(uint32_t*)(uintptr_t)(g_base + NOPARENT_RVA);
  for (int i = 0; i < ch->n_stand_low && nu < p; i++) {
    unsigned char* c = club(blk, ch->stand_low[i]);
    if (c && *(uint32_t*)(c + OFF_PARENT) == none) up[nu++] = ch->stand_low[i];
  }

  /* Safety net. With the sentinel read correctly this should never fire; if it does, say
     what each club carried and take the top of the table anyway. The chain is configured for
     our own leagues only, so this can never touch a shipped pyramid. */
  if (nu < p) {
    int blocked = nu; nu = 0;
    for (int i = 0; i < ch->n_stand_low && nu < p; i++) {
      unsigned char* c = club(blk, ch->stand_low[i]);
      uint32_t par = c ? *(uint32_t*)(c + OFF_PARENT) : 0;
      if (par) logf("fix %u->%u: club %08x has +0x628 = %08x", ch->cfg.mid, ch->cfg.low,
                    ch->stand_low[i], par);
      up[nu++] = ch->stand_low[i];
    }
    logf("fix %u->%u: only %d of %d clubs were eligible -- promoting the top %d anyway",
         ch->cfg.mid, ch->cfg.low, blocked, p, nu);
  }
  if (nd == 0 || nu == 0) { logf("fix %u->%u: nothing to move (down %d, up %d)", ch->cfg.mid, ch->cfg.low, nd, nu); g_stat[2]++; return; }

  uint32_t nb[MAX_CLUBS], nc[MAX_CLUBS]; int nnb = ch->n_list_mid, nnc = ch->n_list_low;
  memcpy(nb, ch->list_mid, nnb*4); memcpy(nc, ch->list_low, nnc*4);
  /* Each list is brought to its end state whatever the game already did: the upper one loses
     the relegated and gains the promoted it does not hold yet, the lower one the other way round.
     GitHub #37 (Argentina 11 -> 49, 2026-09-30): the game had written 49's side of the pair only
     -- relegated in, promoted out -- and the old test ("a promoted club is gone from 49, so the
     game moved the pair") left 11 alone: the relegated played on in both leagues and the
     promoted in neither. */
  int done_mid = 1, done_low = 1;
  for (int i = 0; i < nd; i++) { int r = remove_handle(nb, nnb, down[i]); if (r >= 0) { nnb = r; done_mid = 0; } }
  for (int i = 0; i < nu; i++) { int r = remove_handle(nc, nnc, up[i]);   if (r >= 0) { nnc = r; done_low = 0; } }
  int add_up = 0, add_down = 0;
  for (int i = 0; i < nu; i++) { int have = 0; for (int j = 0; j < nnb; j++) have |= nb[j] == up[i];   if (!have) add_up++; }
  for (int i = 0; i < nd; i++) { int have = 0; for (int j = 0; j < nnc; j++) have |= nc[j] == down[i]; if (!have) add_down++; }
  if (add_up) done_mid = 0;
  if (add_down) done_low = 0;
  if (done_mid && done_low) { logf("fix %u->%u: the game already moved this pair, leaving it as it is", ch->cfg.mid, ch->cfg.low); g_stat[3]++; return; }
  if (done_mid || done_low)
    logf("fix %u->%u: the game had moved %u's side only -- finishing %u's", ch->cfg.mid, ch->cfg.low,
         done_mid ? ch->cfg.mid : ch->cfg.low, done_mid ? ch->cfg.low : ch->cfg.mid);
  if (nnb + add_up > MAX_CLUBS || nnc + add_down > MAX_CLUBS) { logf("fix: list overflow"); g_stat[3]++; return; }
  /* each league's slot byte from a club that stays in it: the moved clubs' own may already be
     the game's new one when it did half the pair */
  unsigned char* s0 = nnb ? club(blk, nb[0]) : 0; unsigned char* s1 = nnc ? club(blk, nc[0]) : 0;
  for (int i = 0; i < nu; i++) { int have = 0; for (int j = 0; j < nnb; j++) have |= nb[j] == up[i];   if (!have) nb[nnb++] = up[i]; }
  for (int i = 0; i < nd; i++) { int have = 0; for (int j = 0; j < nnc; j++) have |= nc[j] == down[i]; if (!have) nc[nnc++] = down[i]; }

  /* league-slot byte, exactly like the mover: relegated take the slot of the promoted and vice versa */
  unsigned char* c0 = s0 ? s0 : club(blk, down[0]); unsigned char* c1 = s1 ? s1 : club(blk, up[0]);
  uint32_t slot_mid = c0 ? lay_slot(c0) : 0x7b;
  uint32_t slot_low = c1 ? lay_slot(c1) : 0x7b;
  for (int i = 0; i < nd; i++) { unsigned char* c = club(blk, down[i]); if (c) lay_set_slot(c, slot_low); }
  for (int i = 0; i < nu; i++) { unsigned char* c = club(blk, up[i]);   if (c) lay_set_slot(c, slot_mid); }

  vec32_t vb = { nb, nb + nnb, nb + MAX_CLUBS }, vc = { nc, nc + nnc, nc + MAX_CLUBS };
  set_fn orig = (set_fn)(uintptr_t)g_tramp_set;
  g_reentrant = 1;
  orig(ch->cfg.mid, &vb, ch->flag_mid);
  orig(ch->cfg.low, &vc, ch->flag_low);
  g_reentrant = 0;
  g_stat[1]++;
  /* B256 (jibibi 2026-10-27, six French tiers): a league can be the low end of one pair and the
     mid of the next (N2-B 171 under 11 and over 181). The other pair's copy of its list is the
     one the pass wrote, so it gets the list just written here -- else the second fix would put
     the first one's clubs back. */
  for (int i = 0; i < g_nchain; i++) {
    chain_t* o = &g_chain[i]; if (o == ch) continue;
    if (o->cfg.mid == ch->cfg.mid) { memcpy(o->list_mid, nb, nnb*4); o->n_list_mid = nnb; }
    if (o->cfg.mid == ch->cfg.low) { memcpy(o->list_mid, nc, nnc*4); o->n_list_mid = nnc; }
    if (o->cfg.low == ch->cfg.mid) { memcpy(o->list_low, nb, nnb*4); o->n_list_low = nnb; }
    if (o->cfg.low == ch->cfg.low) { memcpy(o->list_low, nc, nnc*4); o->n_list_low = nnc; }
  }
  if (ch->cfg.regular) split_regular(ch, orig, down, nd, up, nu);
  logf("fix %u->%u: %d down (%08x %08x %08x) %d up (%08x %08x %08x); lists now %d/%d; slots %u/%u",
       ch->cfg.mid, ch->cfg.low, nd, down[0], nd>1?down[1]:0, nd>2?down[2]:0, nu, up[0], nu>1?up[1]:0, nu>2?up[2]:0,
       nnb, nnc, slot_mid, slot_low);
}

static void splits_post(void)
{
  for (int i = 0; i < g_nsplitreg; i++) {
    splitreg_t* sp = &g_splitreg[i];
    if (!sp->seen) continue;
    sp->seen = 0;
    uint32_t tot[MAX_CLUBS], cur[MAX_CLUBS], add[MAX_CLUBS];
    int nt = reg_list(sp->total, tot), nr = reg_list(sp->regular, cur), na = 0;
    if (nt <= 0 || nr <= 0) continue;
    if (nt != nr) {
      logf("split %u: %d clubs, its regular phase %u %d -- left as it is", sp->total, nt, sp->regular, nr);
      continue;
    }
    for (int j = 0; j < nt; j++) if (!in_list(cur, nr, tot[j])) add[na++] = tot[j];
    if (!na) continue;
    int k = 0;
    for (int j = 0; j < nr && k < na; j++) if (!in_list(tot, nt, cur[j])) cur[j] = add[k++];
    write_list(sp->regular, cur, nr, sp->flag);
    g_stat[1]++;
    logf("split %u: regular phase %u -- %d club(s) of the new season put in", sp->total, sp->regular, na);
  }
}

void apply_post(void* ctx)
{
  (void)ctx;
  for (int i = 0; i < g_nchain; i++) {
    chain_t* ch = &g_chain[i];
    /* B256: the bottom of a six-tier pyramid (N2-C 181) may not be written by the pass at all,
       its list then comes from the game as it stands, with the flag of the side that was */
    if ((ch->seen & 3) == 1 && ch->n_stand_low > 0) {
      int n = reg_list(ch->cfg.low, ch->list_low);
      /* B365 (09.11., mp46): a league of ours under a game league in a region the exe holds to
         the calendar year and the world file to August (J3 430 under J2 254, Saudi Second
         Division 944 under 958) is not written by the pass, and the season's end has emptied
         its list by then: "incomplete (seen 1)", no door after, and it played one season. Its
         table holds the season's clubs -- they are its list. */
      if (n <= 0 && ch->n_stand_low >= 2 && ch->n_stand_low <= MAX_CLUBS) {
        int k = 0;
        for (int j = 0; j < ch->n_stand_low; j++)
          if (ch->stand_low[j] != 0xffffffffu && !in_list(ch->list_low, k, ch->stand_low[j])
              && !in_list(ch->list_mid, ch->n_list_mid, ch->stand_low[j])) ch->list_low[k++] = ch->stand_low[j];
        if (k == ch->n_stand_low) {
          n = k;
          logf("apply: chain %u->%u -- %u not written by the pass and its list empty, its %d clubs taken from its table",
               ch->cfg.mid, ch->cfg.low, ch->cfg.low, n);
        }
      }
      if (n > 0) { ch->n_list_low = n; ch->flag_low = ch->flag_mid; ch->seen |= 2;
                   logf("apply: chain %u->%u -- %u not written by the pass, its %d clubs read", ch->cfg.mid, ch->cfg.low, ch->cfg.low, n); }
    }
    /* a chain hanging under a group of a set (one league below a Serie D group): the group may
       not be written by the pass, its list then is the one it holds */
    if ((ch->seen & 3) == 2 && ch->n_stand_mid > 0 && gl_member(ch->cfg.mid)) {
      int n = reg_list(ch->cfg.mid, ch->list_mid);
      if (n > 0) { ch->n_list_mid = n; ch->flag_mid = ch->flag_low; ch->seen |= 1;
                   logf("apply: chain %u->%u -- %u not written by the pass, its %d clubs read", ch->cfg.mid, ch->cfg.low, ch->cfg.mid, n); }
    }
    if ((ch->seen & 3) == 3) fix_chain(ch);
    else if (ch->seen & 3) { logf("apply: chain %u->%u incomplete (seen %d) -- untouched", ch->cfg.mid, ch->cfg.low, ch->seen); g_stat[2]++; }
  }
  /* the group sets after the chains (their lists are read as the chains left them), then the
     play-offs of plain pairs */
  groups_post();
  poff_post();
  splits_post();
  /* after the chains: the leagues' lists are the new season's now, whichever order the pass wrote them in */
  for (int i = 0; i < g_ncup; i++) {
    if (!g_cup_seen[i]) continue;
    uint32_t cur[MAX_CLUBS]; int n = reg_list(g_cup[i].cup, cur);
    if (n > 0 && cup_fix(&g_cup[i], cur, n, g_cup_flag[i], "season pass", g_cup_seen[i] == 2)) g_stat[1]++;
  }
  for (int i = 0; i < g_nscup; i++) {
    if (!g_scup_seen[i]) continue;
    uint32_t cur[MAX_CLUBS], low[MAX_CLUBS]; int n = reg_list(g_scup[i].scup, cur);
    /* our league's clubs before the pass; at a new career its list may not be there yet */
    int nl = g_scup_npre[i];
    if (nl > 0) memcpy(low, g_scup_pre[i], nl * 4); else nl = reg_list(g_scup[i].low, low);
    if (n > 0 && scup_fix(&g_scup[i], cur, n, low, nl, g_scup_flag[i], "season pass")) g_stat[1]++;
  }
  g_in_apply = 0; g_ctx = 0;
}

/* CALL-style hook: pre, original, post; rax of the original preserved.
 * entry rsp = 8 mod 16; push,push -> 8; sub 0x28 -> 0 (aligned for the calls).
 * Callee home space [rsp+8, rsp+0x28) lies inside our 0x28 area. */
__attribute__((naked)) void apply_handler(void)
{
  __asm__ volatile(
    "push %rbx\n"
    "push %rbp\n"
    "sub  $0x28, %rsp\n"
    "mov  %rcx, %rbx\n"
    "call apply_pre\n"
    "mov  %rbx, %rcx\n"
    "call *g_tramp_apply(%rip)\n"
    "mov  %rax, %rbp\n"
    "mov  %rbx, %rcx\n"
    "call apply_post\n"
    "mov  %rbp, %rax\n"
    "add  $0x28, %rsp\n"
    "pop  %rbp\n"
    "pop  %rbx\n"
    "ret\n");
}

/* ---- install ---- */
static int hook(unsigned char* target, const unsigned char* sig, int n, void* handler, unsigned char** tramp_out)
{
  for (int i = 0; i < n; i++) if (target[i] != sig[i]) return 2;
  unsigned char* t = (unsigned char*)VirtualAlloc(0, 0x100, MEM_COMMIT|MEM_RESERVE, PAGE_EXECUTE_READWRITE);
  if (!t) return 3;
  memcpy(t, target, n);
  t[n] = 0xFF; t[n+1] = 0x25; *(uint32_t*)(t + n + 2) = 0; *(uint64_t*)(t + n + 6) = (uint64_t)(uintptr_t)(target + n);
  DWORD old;
  if (!VirtualProtect(target, n, PAGE_EXECUTE_READWRITE, &old)) return 4;
  target[0] = 0xFF; target[1] = 0x25; *(uint32_t*)(target + 2) = 0; *(uint64_t*)(target + 6) = (uint64_t)(uintptr_t)handler;
  for (int i = 14; i < n; i++) target[i] = 0x90;
  VirtualProtect(target, n, old, &old);
  FlushInstructionCache(GetCurrentProcess(), target, n);
  *tramp_out = t;
  return 0;
}

/* Same, but if another of our modules already sits on the function -- its hook is the same
   14-byte `jmp [rip+0]; dq handler` -- go in front of it: the trampoline jumps to that handler,
   which still ends in the original. fl26swiss holds set_clubs too and is meant to load after
   this; in a sider.ini where it (or the old fl26cuphook) comes first, the plain check refused
   and the whole module stayed out ("set-hook signature mismatch", 2026-09-28). */
static int g_chained = 0;
static const unsigned char JMP_ABS[6] = { 0xFF, 0x25, 0, 0, 0, 0 };
/* FL27 (SmokePatch, 31.10.2026) hooks set_clubs itself: `jmp rel32` and ten nops over the same
   15 bytes, its stub ending in the displaced prologue and a jmp back to target + 15.  Where the
   whole prologue is that jmp and nops, our 14-byte jmp goes over it and the trampoline jumps to
   their stub, which still ends in the original. */
static unsigned char* e9_dest(const unsigned char* target, int n)
{
  if (n < 14 || target[0] != 0xE9) return 0;
  for (int i = 5; i < n; i++) if (target[i] != 0x90) return 0;
  return (unsigned char*)target + 5 + *(const int32_t*)(target + 1);
}
static int usable(const unsigned char* target, const unsigned char* sig, int n)
{
  return !memcmp(target, sig, n) || !memcmp(target, JMP_ABS, 6) || e9_dest(target, n);
}
static int hook_or_chain(unsigned char* target, const unsigned char* sig, int n, void* handler, unsigned char** tramp_out)
{
  if (!memcmp(target, sig, n)) return hook(target, sig, n, handler, tramp_out);
  unsigned char* stub = e9_dest(target, n);
  if (stub) {
    unsigned char* t = (unsigned char*)VirtualAlloc(0, 0x100, MEM_COMMIT|MEM_RESERVE, PAGE_EXECUTE_READWRITE);
    if (!t) return 3;
    t[0] = 0xFF; t[1] = 0x25; *(uint32_t*)(t + 2) = 0; *(uint64_t*)(t + 6) = (uint64_t)(uintptr_t)stub;
    DWORD old;
    if (!VirtualProtect(target, n, PAGE_EXECUTE_READWRITE, &old)) return 4;
    target[0] = 0xFF; target[1] = 0x25; *(uint32_t*)(target + 2) = 0; *(uint64_t*)(target + 6) = (uint64_t)(uintptr_t)handler;
    for (int i = 14; i < n; i++) target[i] = 0x90;
    VirtualProtect(target, n, old, &old);
    FlushInstructionCache(GetCurrentProcess(), target, n);
    *tramp_out = t;
    g_chained++;
    return 0;
  }
  if (memcmp(target, JMP_ABS, 6)) return 2;
  unsigned char* t = (unsigned char*)VirtualAlloc(0, 0x100, MEM_COMMIT|MEM_RESERVE, PAGE_EXECUTE_READWRITE);
  if (!t) return 3;
  memcpy(t, target, 14);                     /* jmp to the handler that was there */
  DWORD old;
  if (!VirtualProtect(target, 14, PAGE_EXECUTE_READWRITE, &old)) return 4;
  *(uint64_t*)(target + 6) = (uint64_t)(uintptr_t)handler;
  VirtualProtect(target, 14, old, &old);
  FlushInstructionCache(GetCurrentProcess(), target, 14);
  *tramp_out = t;
  g_chained++;
  return 0;
}

/* 0 ok; 2/3/4 = set-hook signature/alloc/protect; 12/13/14 = apply-hook signature/alloc/protect; 9 bad config */
__declspec(dllexport) int fl26_chain_install(uint64_t exe_base, uint64_t cave_addr, const fl26_chain_cfg_t* cfg, int ncfg)
{
  /* No chain at all is a valid world (every added league a top flight, or a two-division pyramid
     the game's own mover handles): the hooks still go in, for the empty-list guard. */
  if (ncfg < 0 || ncfg > MAX_CHAINS || (ncfg && !cfg)) return 9;
  g_base = exe_base; g_cave = (volatile uint32_t*)(uintptr_t)cave_addr;
  g_nchain = ncfg;
  for (int i = 0; i < ncfg; i++) { memset(&g_chain[i], 0, sizeof g_chain[i]); g_chain[i].cfg = cfg[i]; }
  /* Check both prologues before touching either, so a mismatch really does leave the game
     unmodified rather than half hooked. */
  if (!usable((const unsigned char*)(uintptr_t)(exe_base + SET_RVA),   SIG_SET,   15)) return 2;
  if (!usable((const unsigned char*)(uintptr_t)(exe_base + APPLY_RVA), SIG_APPLY, 15)) return 12;
  int r = hook_or_chain((unsigned char*)(uintptr_t)(exe_base + SET_RVA), SIG_SET, 15, (void*)set_handler, &g_tramp_set);
  if (r) return r;
  r = hook_or_chain((unsigned char*)(uintptr_t)(exe_base + APPLY_RVA), SIG_APPLY, 15, (void*)apply_handler, &g_tramp_apply);
  if (r) return r + 10;
  logf("fl26chain: hooks live (set@%llx apply@%llx), %d chain(s)%s", (unsigned long long)(exe_base + SET_RVA), (unsigned long long)(exe_base + APPLY_RVA), ncfg,
       g_chained ? ", in front of another module's hook" : "");
  return 0;
}

/* Apertura/Clausura splits: pairs {regular phase, second phase}; returns how many were taken */
/* every split of ours, n pairs {total, regular phase}; returns how many were taken */
__declspec(dllexport) int fl26_chain_splits(const uint16_t* pairs, int n)
{
  g_nsplitreg = 0;
  for (int i = 0; pairs && i < n && g_nsplitreg < MAX_SPLITREG; i++) {
    splitreg_t* sp = &g_splitreg[g_nsplitreg++];
    sp->total = pairs[2 * i]; sp->regular = pairs[2 * i + 1]; sp->flag = 1; sp->seen = 0;
    sp->group[0] = sp->group[1] = sp->group[2] = 0;
  }
  logf("fl26chain: %d split(s) keep their regular phase to the total's clubs", g_nsplitreg);
  return g_nsplitreg;
}

/* the groups of the splits fl26_chain_splits named: n of {total, group, group, group} (0 = none),
   for a total the game leaves without a table (split_table). Not for an Apertura/Clausura split,
   whose one group starts from zero: apclau_table counts that one. Returns how many were matched. */
__declspec(dllexport) int fl26_chain_split_groups(const uint16_t* v, int n)
{
  int got = 0;
  for (int i = 0; v && i < n; i++)
    for (int k = 0; k < g_nsplitreg; k++)
      if (g_splitreg[k].total == v[4 * i]) {
        for (int g = 0; g < 3; g++) g_splitreg[k].group[g] = v[4 * i + 1 + g];
        got++;
        break;
      }
  logf("fl26chain: %d split(s) take their table from their groups when the game gives none", got);
  return got;
}

__declspec(dllexport) int fl26_chain_apclau(const uint16_t* pairs, int n)
{
  g_napclau = 0;
  for (int i = 0; i < n && g_napclau < MAX_APCLAU; i++) {
    g_apclau[g_napclau].regular = pairs[2 * i]; g_apclau[g_napclau].second = pairs[2 * i + 1]; g_napclau++;
  }
  return g_napclau;
}

/* the regulations the empty-list guard protects; returns how many were taken */
__declspec(dllexport) int fl26_chain_protect(const uint16_t* ids, int n)
{
  if (!ids || n < 0) return 0;
  if (n > MAX_PROTECT) n = MAX_PROTECT;
  for (int i = 0; i < n; i++) g_protect[i] = ids[i];
  g_nprotect = n;
  logf("fl26chain: empty-list guard on %d of our regulations", n);
  return n;
}

/* the domestic cups to keep to their own league: n triples {cup, top league, our league below it} */
__declspec(dllexport) int fl26_chain_cups(const uint16_t* triples, int n)
{
  if (!triples || n < 0) return 0;
  if (n > MAX_CUPS) n = MAX_CUPS;
  for (int i = 0; i < n; i++) {
    g_cup[i].cup = triples[3*i] & ~CUP_ALL; g_cup[i].all = (triples[3*i] & CUP_ALL) != 0;
    g_cup[i].top = triples[3*i+1]; g_cup[i].low = triples[3*i+2]; g_cup[i].max = 0; g_cup[i].third = 0;
    logf("fl26chain: cup %u -- %s", g_cup[i].cup, g_cup[i].all ? "both leagues (cupall)" : "the top league only");
  }
  g_ncup = n;
  logf("fl26chain: %d domestic cup(s) with a league of ours below the top one", n);
  return n;
}

/* GitHub #74: n pairs {cup, the most clubs it takes}, for cups fl26_chain_cups already named */
__declspec(dllexport) int fl26_chain_cupsize(const uint16_t* pairs, int n)
{
  if (!pairs || n < 0) return 0;
  int set = 0;
  for (int k = 0; k < n; k++)
    for (int i = 0; i < g_ncup; i++)
      if (g_cup[i].cup == pairs[2*k]) {
        g_cup[i].max = pairs[2*k+1]; set++;
        logf("fl26chain: cup %u -- at most %u clubs", g_cup[i].cup, g_cup[i].max);
      }
  return set;
}

/* B228: n pairs {cup, third division}, for cupall cups fl26_chain_cups already named */
__declspec(dllexport) int fl26_chain_cupthird(const uint16_t* pairs, int n)
{
  if (!pairs || n < 0) return 0;
  int set = 0;
  for (int k = 0; k < n; k++)
    for (int i = 0; i < g_ncup; i++)
      if (g_cup[i].cup == pairs[2*k] && g_cup[i].all) {
        g_cup[i].third = pairs[2*k+1]; set++;
        logf("fl26chain: cup %u -- also the first clubs of %u", g_cup[i].cup, g_cup[i].third);
      }
  return set;
}

/* the super cups to keep free of our league: n triples {super cup, top league, our league below it} */
__declspec(dllexport) int fl26_chain_supercups(const uint16_t* triples, int n)
{
  if (!triples || n < 0) return 0;
  if (n > MAX_CUPS) n = MAX_CUPS;
  for (int i = 0; i < n; i++) { g_scup[i].scup = triples[3*i]; g_scup[i].top = triples[3*i+1]; g_scup[i].low = triples[3*i+2]; }
  g_nscup = n;
  logf("fl26chain: %d super cup(s) kept free of a new second division", n);
  return n;
}

/* group sets (GitHub #98), u16 words: per set nup, nlow, then nup x {league, clubs it sends down}
   and nlow x {league, clubs it sends up, index of the upper league it names or 0xffff}.
   Returns the sets taken, -1 for a malformed list (nothing taken). Call before fl26_chain_playoffs. */
__declspec(dllexport) int fl26_chain_gsets(const uint16_t* v, int n)
{
  g_ngset = 0; g_ngl = 0;
  if (!v || n <= 0) return 0;
  int i = 0;
  while (i < n) {
    if (i + 2 > n || g_ngset >= MAX_GSETS) return g_ngset = 0, -1;
    int nup = v[i], nlow = v[i + 1]; i += 2;
    if (nup < 1 || nlow < 1 || nup > MAX_GSIDE || nlow > MAX_GSIDE || i + 2 * nup + 3 * nlow > n) return g_ngset = 0, -1;
    gset_t* gs = &g_gset[g_ngset];
    memset(gs, 0, sizeof *gs);
    gs->nup = nup; gs->nlow = nlow;
    for (int k = 0; k < nup; k++, i += 2) {
      int g = gl_add(v[i]); if (g < 0) return g_ngset = 0, -1;
      gs->up[k].gl = (uint16_t)g; gs->up[k].n = (uint8_t)v[i + 1]; gs->up[k].pref = 0xff;
    }
    for (int k = 0; k < nlow; k++, i += 3) {
      int g = gl_add(v[i]); if (g < 0) return g_ngset = 0, -1;
      gs->low[k].gl = (uint16_t)g; gs->low[k].n = (uint8_t)v[i + 1];
      gs->low[k].pref = v[i + 2] < nup ? (uint8_t)v[i + 2] : 0xff;
    }
    g_ngset++;
  }
  logf("fl26chain: %d group set(s), %d league(s) in them", g_ngset, g_ngl);
  return g_ngset;
}

/* B418: the slot the world file gives each league of a set or a play-off, n pairs {league, slot};
   after fl26_chain_gsets and fl26_chain_playoffs (they make the league table). Returns the
   leagues taken. */
__declspec(dllexport) int fl26_chain_gslots(const uint16_t* v, int n)
{
  int got = 0;
  for (int k = 0; k < g_ngl; k++) g_gl[k].wslot = 0;
  for (int i = 0; v && i < n; i++) {
    int k = gl_find(v[2 * i]);
    if (k >= 0 && v[2 * i + 1] < 512) { g_gl[k].wslot = v[2 * i + 1] + 1; got++; }
  }
  logf("fl26chain: the world file's slot for %d of the %d league(s) of the group sets and play-offs", got, g_ngl);
  return got;
}

/* the league each club was built into: n pairs {team id, league}, a club once a set (a Super Lig
   club's group in the TFF 2. Lig and in the TFF 3. Lig); a club of a set sent across goes back to
   its own group when that group has a place for it. 16.11.2026: read from the world file at every
   start, and a guest is told from these and the season's standings alone (which group it played
   in), nothing kept in memory -- a loaded career has the same homes and guests as one played on */
static int home_cmp(const void* a, const void* b)
{
  uint32_t x = ((const ghome_t*)a)->tid, y = ((const ghome_t*)b)->tid;
  return x < y ? -1 : x > y;
}
__declspec(dllexport) int fl26_chain_ghomes(const uint32_t* v, int n)
{
  g_nhome = 0;
  if (!v || n <= 0) return 0;
  if (n > MAX_HOMES) n = MAX_HOMES;
  for (int i = 0; i < n; i++) { g_home[i].tid = v[2 * i]; g_home[i].league = (uint16_t)v[2 * i + 1]; }
  g_nhome = n;
  qsort(g_home, g_nhome, sizeof g_home[0], home_cmp);
  return n;
}

/* 16.11.2026: the recipe's border clubs (zone_border, the world file's gborder lines), n triples
   {group, team id, neighbour group} in the recipe's order -- a club of a full group that may make
   room for a relegated club of the group's region (group_assign). A world without gborder lines
   (every world built before 16.11.2026) gives none, and nothing changes. Returns the clubs taken. */
__declspec(dllexport) int fl26_chain_gborders(const uint32_t* v, int n)
{
  g_nborder = 0;
  if (!v || n <= 0) return 0;
  for (int i = 0; i < n && g_nborder < MAX_BORDERS; i++) {
    if (!v[3 * i + 1] || v[3 * i] > 0xffff || v[3 * i + 2] > 0xffff || v[3 * i] == v[3 * i + 2]) continue;
    g_border[g_nborder].league = (uint16_t)v[3 * i]; g_border[g_nborder].tid = v[3 * i + 1];
    g_border[g_nborder].to = (uint16_t)v[3 * i + 2]; g_nborder++;
  }
  logf("fl26chain: %d border club(s) of the groups (zone_border)", g_nborder);
  return g_nborder;
}

/* play-offs, u16 words: per play-off {cup, upper league, lower league, holder's league or 0,
   holder's place, entrants}, then that many {league, place}. Returns the play-offs taken, -1 for a
   malformed list. */
__declspec(dllexport) int fl26_chain_playoffs(const uint16_t* v, int n)
{
  g_npoff = 0;
  if (!v || n <= 0) return 0;
  int i = 0;
  while (i < n) {
    if (i + 6 > n || g_npoff >= MAX_POFF) return g_npoff = 0, -1;
    poff_t* p = &g_poff[g_npoff];
    memset(p, 0, sizeof *p);
    p->ko = v[i]; p->up = v[i + 1]; p->low = v[i + 2]; p->hold_reg = v[i + 3]; p->hold_pos = (uint8_t)v[i + 4]; p->ne = v[i + 5];
    i += 6;
    if (p->ne < 2 || p->ne > POFF_ENTRY || i + 2 * p->ne > n || (!p->hold_reg && p->ne != 2)) return g_npoff = 0, -1;
    for (int e = 0; e < p->ne; e++, i += 2) {
      p->ereg[e] = v[i]; p->epos[e] = (uint8_t)v[i + 1];
      if (gl_add(p->ereg[e]) < 0) return g_npoff = 0, -1;
    }
    if (gl_add(p->up) < 0 || gl_add(p->low) < 0 || (p->hold_reg && gl_add(p->hold_reg) < 0)) return g_npoff = 0, -1;
    logf("fl26chain: play-off %u -- %d clubs, its winner ends in %u%s", p->ko, p->ne, p->up, p->hold_reg ? " (a place)" : " (a tie)");
    g_npoff++;
  }
  return g_npoff;
}

/* copy and clear the pending log text; returns bytes copied. Only whole lines: a cut at cap left
   the rest of a line to start the next drain ("fl26chain:  clubs", 08.11.) */
__declspec(dllexport) int fl26_chain_log(char* out, int cap)
{
  int n = g_log_len; if (n > cap - 1) n = cap - 1; if (n < 0) n = 0;
  if (n < g_log_len) { int k = n; while (k > 0 && g_log[k - 1] != '\n') k--; if (k > 0) n = k; }
  memcpy(out, g_log, n); out[n] = 0;
  if (n < g_log_len) { memmove(g_log, g_log + n, g_log_len - n); g_log_len -= n; } else g_log_len = 0;
  return n;
}

/* applies seen, fixes done, refused (nothing to move / incomplete), anomalies */
__declspec(dllexport) void fl26_chain_stats(uint32_t* out4)
{
  for (int i = 0; i < 4; i++) out4[i] = g_stat[i];
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID r) { (void)h;(void)reason;(void)r; return TRUE; }
