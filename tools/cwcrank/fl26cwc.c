/* fl26cwc.dll -- the Club World Cup ranking (2026-11-17). The probes it grew from are
 * fl26cwc-probe.c / fl26cwc-probe.lua.
 *
 * The confederation ranking screens of fl26contrank (UEFA, CONMEBOL, CONCACAF, AFC, CAF) show
 * points won in the continental club cups instead of the squad points of the world Club Ranking.
 * The world Club Ranking itself is left as it is.
 *
 * Points (the user's rules, 2026-11-17), kept in quarter points:
 *   UEFA       win 2, draw 1; reaching the league phase 4, the round of 16 5, every round after
 *              it (quarter-final, semi-final, final) 1.
 *   the others win 3, draw 1; every stage reached 3 (a group stage once, every knockout round).
 *   Secondary cups (Europa League, Conference League, Sudamericana, ACL Two, AFC Challenge League,
 *   CAF Confederation Cup) give half; qualifying and preliminary rounds give half (both: a quarter).
 *   A knockout match decided on penalties is a draw. Super cups and the Club World Cup give none.
 *   A stage counts when the club's first match in it has been played.
 * The window: everything from the last reset on. The ranking resets right before every Club World
 * Cup: day <reset day> (0-based) of <first CWC year> + 4k, both from fl26cwc.lua. Before the first
 * one everything since the start of the career counts. Clubs with 0 points are left out.
 *
 * Where the points come from: the game's match table (base and cap read off its walk at
 * 0x1413146e8 / 0x14131471b; stride 0x254; +4 u16 regulation, base = reg & 0x3ff, replicas
 * +1024k; +6 round code: knockout 0x2e round of 16, 0x33 QF, 0x34 SF, 0x35 final and single-stage
 * ties, a matchday in a group stage; +7 0x40 played, 0x10 second leg; +8 u16 year, +10 month,
 * +11 day (1-based); +0x14 / +0x18 the clubs as (id << 14 | row); +0x1c / +0x1f the goals).
 * Finished stages leave the table during the season (the Sudamericana's first stage was gone by
 * day 166), so a thread of ours reads it every second; a match counts once it has been seen played
 * and the same in two reads in a row, and every match counts once (the ledger keeps each one).
 *
 * Per save: the ledger is kept beside the save, ML0000000N.fl26cwc (LG0000000N.fl26cwc in League
 * mode). Probe 3 (2026-11-17) showed how the game saves and loads, through ntdll!NtCreateFile (in
 * the game the export is apphelp.dll's shim; it is hooked the same way):
 *   save  main thread: reads ML0..ML13 (the slot list), opens <slot>.tmp for writing, writes it,
 *         renames it to <slot>. At the .tmp open the table is read once more on the game's own
 *         thread and the ledger is copied; when the folder watcher sees <slot> appear by the
 *         rename, the copy is written to <slot>.fl26cwc (through a .tmp of ours and a rename).
 *   load  the same <slot> read-opened by two threads one after the other (the loader, then the
 *         game's thread; a save's slot list reads each slot once). The ledger becomes that file's
 *         (or empty when there is none).
 *         Played matches of the career left behind (still in memory while the save is read) are
 *         put in quarantine: they never count, unless the loaded career has the same match still
 *         to play (an older save of the same career).
 *   a new career: the game's date goes back before the ledger's last match -> the ledger empties
 *         (not in the first two minutes after a load, while the old date may still be in memory).
 *         The date alone missed one (2026-11-17: a career ending on 13 June loaded, then a new one
 *         built on day 181 -- forward -- and its first save carried the old career's 512 entries).
 *         So also: the match table EMPTY (not one match, played or not) with a date -> a career
 *         being built -> the ledger empties. Test 12:26: quitting to the menu leaves the old
 *         career's table as it was; the new career's build empties it (day 181, 0 matches), then
 *         plays its own pre-season up to day ~212 before the first screen (2 matches played by
 *         day 190), so "nothing played for 5 s" (v4) never held. A career that goes on is never
 *         empty: the calendar-year leagues are mid-season at the July rollover, the August-May
 *         ones at New Year. Not within 60 s of a load (the load gives the slot's ledger anyway).
 *
 * The lists: fl26contrank's stub for the clubs past the world ranking (cave+0x1000) ends with
 * mov rdx,[rbx+0xa0]; jmp [rip] -> 0x140b10ac9. That jump's target becomes cwc_list_stub, which
 * gives the filled vector (RankingTeam +0x98/+0xa0: 16-byte entries {u32 club, u32 sort key, u16
 * points, u16 points}) to cwc_rewrite when a filter is set: the points become ours, the clubs with
 * none are dropped (all kept, at 0, while nobody has any: the screen never had an empty list), and
 * the sort key orders by points. fl26contrank renumbers 1..N after the game's sort. The row has no
 * points column, so the club's name gets them ("Flamengo  25 pts", see hook_text).
 *
 * Build: gcc -shared -O2 -s -o fl26cwc.dll fl26cwc.c -lkernel32   (msys64 ucrt64)
 */
#include <windows.h>
#include <winternl.h>
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <wchar.h>
#include <wctype.h>
#include "../native/fl26savedir.h"

#define OWNER_PTR       0x143705e10ull     /* block = [[OWNER_PTR] + 0x48] (0x1414b6a60 reads it) */
#define MATCH_BASE_SITE 0x1413146e8ull     /* lea rcx,[rax + base] */
#define MATCH_CAP_SITE  0x14131471bull     /* cmp edi, cap */
#define MATCH_STRIDE    0x254
#define TODAY_OFF       0x19115e4          /* u16 day of the year (0-based); u16 year at +8 */
#define LIST_SITE       0x140b10ac2ull     /* fl26contrank: jmp cave+0x1000 */
#define LIST_BACK       0x140b10ac9ull
#define EXTRA_OFF       0x1000
#define EXTRA_TAIL      0x159              /* mov rdx,[rbx+0xa0]; jmp [rip]; dq 0x140b10ac9 */

/* ---------------------------------------------------------------- log */
static CRITICAL_SECTION g_cs, g_lk;      /* g_cs: the log; g_lk: everything else */
static int g_cs_ok;
static char g_log[1 << 16];
static int g_loglen;
static void plog(const char* fmt, ...)
{
  char line[1024];
  va_list ap; va_start(ap, fmt);
  int n = vsnprintf(line, sizeof line - 1, fmt, ap);
  va_end(ap);
  if (n < 0 || !g_cs_ok) return;
  if (n > (int)sizeof line - 2) n = sizeof line - 2;
  line[n++] = '\n';
  EnterCriticalSection(&g_cs);
  if (g_loglen + n <= (int)sizeof g_log) { memcpy(g_log + g_loglen, line, n); g_loglen += n; }
  LeaveCriticalSection(&g_cs);
}
__declspec(dllexport) int fl26_cwc_log(char* out, int cap)
{
  if (!g_cs_ok) return 0;
  EnterCriticalSection(&g_cs);
  int n = g_loglen < cap ? g_loglen : cap;
  while (n > 0 && n < g_loglen && g_log[n - 1] != '\n') n--;
  memcpy(out, g_log, n);
  memmove(g_log, g_log + n, g_loglen - n);
  g_loglen -= n;
  LeaveCriticalSection(&g_cs);
  return n;
}

/* ---------------------------------------------------------------- the game */
static int g_game;                         /* the exe is FL_2026 as expected */
static uint32_t g_mbase, g_mcap;
static unsigned char* block(void)
{
  if (!g_game) return 0;
  unsigned char* o = *(unsigned char* volatile*)(uintptr_t)OWNER_PTR;
  return o ? *(unsigned char* volatile*)(o + 0x48) : 0;
}
static int today(unsigned char* b, int* y)  /* day of the year, 0-based; -1 without a career */
{
  if (!b) return -1;
  int d = *(volatile uint16_t*)(b + TODAY_OFF), yy = *(volatile uint16_t*)(b + TODAY_OFF + 8);
  if (yy < 1900 || yy > 2300 || d > 366) return -1;
  *y = yy;
  return d;
}
static int leap(int y) { return (y % 4 == 0 && y % 100) || y % 400 == 0; }
static int doy(int y, int mo, int d)       /* 1-based month and day -> 0-based day of the year */
{
  static const int cum[12] = { 0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334 };
  if (mo < 1 || mo > 12) return 0;
  return cum[mo - 1] + (mo > 2 && leap(y)) + d - 1;
}
static int stamp(int y, int dy) { return y * 400 + dy; }   /* comparable dates */

/* ---------------------------------------------------------------- the competitions */
enum { F_UEFA = 1, F_SEC = 2, F_QUAL = 4, F_GROUP = 8, F_LP = 16, F_UKO = 32, F_REP = 64 };
typedef struct { uint16_t base; uint8_t f; } comp_t;
/* this world's ids (fl26world.txt ccup / lpre / qround lines; the game's own 2..16) */
static const comp_t COMPS[] = {
  /* UEFA Champions League: qualifying 255 256, play-off 2, league phase 3, knockout 4 */
  { 255, F_UEFA | F_QUAL }, { 256, F_UEFA | F_QUAL }, { 2, F_UEFA | F_QUAL },
  { 3, F_UEFA | F_GROUP | F_LP | F_REP }, { 4, F_UEFA | F_UKO },
  /* Europa League */
  { 257, F_UEFA | F_SEC | F_QUAL }, { 258, F_UEFA | F_SEC | F_QUAL }, { 188, F_UEFA | F_SEC | F_QUAL },
  { 5, F_UEFA | F_SEC | F_GROUP | F_LP | F_REP }, { 6, F_UEFA | F_SEC | F_UKO },
  /* Conference League */
  { 259, F_UEFA | F_SEC | F_QUAL }, { 260, F_UEFA | F_SEC | F_QUAL }, { 189, F_UEFA | F_SEC | F_QUAL },
  { 186, F_UEFA | F_SEC | F_GROUP | F_LP | F_REP }, { 187, F_UEFA | F_SEC | F_UKO },
  /* Libertadores: preliminary 282 283, qualifying 8, groups 9, knockout 10 */
  { 282, F_QUAL }, { 283, F_QUAL }, { 8, F_QUAL }, { 9, F_GROUP | F_REP }, { 10, 0 },
  /* Sudamericana: first stage 277 (one reg per tie), groups 278, knockout play-off 281, knockout 279 */
  { 277, F_SEC | F_QUAL | F_REP }, { 278, F_SEC | F_GROUP | F_REP }, { 281, F_SEC }, { 279, F_SEC },
  /* AFC Champions League Elite 15 16, ACL Two 285 286, Challenge League 287 288 */
  { 15, F_GROUP | F_REP }, { 16, 0 },
  { 285, F_SEC | F_GROUP | F_REP }, { 286, F_SEC }, { 287, F_SEC | F_GROUP | F_REP }, { 288, F_SEC },
  /* CAF Champions League 309 310, Confederation Cup 311 312 */
  { 309, F_GROUP | F_REP }, { 310, 0 }, { 311, F_SEC | F_GROUP | F_REP }, { 312, F_SEC },
  /* CONCACAF Champions Cup: a knockout */
  { 313, 0 },
};
static int comp_of(unsigned reg)
{
  unsigned b = reg & 0x3ff, k = reg >> 10;
  for (int i = 0; i < (int)(sizeof COMPS / sizeof COMPS[0]); i++)
    if (COMPS[i].base == b) return (k == 0 || (COMPS[i].f & F_REP)) ? i : -1;
  return -1;
}
static int weight(int f) { int w = 4; if (f & F_SEC) w /= 2; if (f & F_QUAL) w /= 2; return w; }
/* points for reaching a stage, quarter points */
static int stage_points(int f, int code)
{
  int w = weight(f);
  if (!(f & F_UEFA)) return 3 * w;
  if (f & F_LP) return 4 * w;
  if (f & F_UKO) {
    if (code == 0x2e) return 5 * w;
    if (code == 0x33 || code == 0x34 || code == 0x35) return w;
  }
  return 0;                                /* UEFA qualifying, the knockout play-off */
}

/* ---------------------------------------------------------------- the ledger */
/* K_CHAMP (2026-11-17, the Club World Cup of 32): a continental champion, told by fl26swiss.dll
   (fl26_cwc_champion) -- reg = the cup's knockout, the date it was told, a = the club. No points.
   Kept in the file for CHAMP_KEEP_YEARS whatever the window (the draw looks four seasons back) */
enum { K_MATCH = 1, K_STAGE = 2, K_CHAMP = 3 };
#define CHAMP_KEEP_YEARS 6
typedef struct {
  uint16_t reg; uint8_t kind, code;
  uint16_t year; uint8_t month, day;
  uint32_t a, b;                           /* clubs (handles); a stage: b = 0 */
  int16_t pa, pb;                          /* quarter points */
  uint8_t ga, gb, pad[2];
} ent_t;                                   /* 24 bytes, also the file's record */
typedef char ent_size_check[sizeof(ent_t) == 24 ? 1 : -1];
static ent_t* g_led; static int g_nled, g_cled;
static int g_last;                         /* stamp of the ledger's last match */
static char g_slot[16];                    /* "ML00000000" the ledger belongs to, "" none yet */
static int g_first_year = 2029, g_reset_day = 153, g_every = 4;   /* g_every: fl26_cwc_every */
static ULONGLONG g_load_tick;              /* when a load was taken in */
static int g_empty_seen;                   /* the last read found the table empty */

typedef struct { uint64_t* k; uint32_t n, cap; } hset;  /* 0 = empty, 1 = removed */
static uint64_t mkey(unsigned reg, int y, int mo, int d, uint32_t a, uint32_t b)
{
  uint64_t h = 0x9e3779b97f4a7c15ull ^ reg;
  uint64_t v[3] = { ((uint64_t)y << 16) | ((uint64_t)mo << 8) | (uint64_t)d, a, b };
  for (int i = 0; i < 3; i++) { h ^= v[i]; h *= 0xff51afd7ed558ccdull; h ^= h >> 33; }
  return h < 2 ? h + 2 : h;
}
static int hs_has(const hset* s, uint64_t k)
{
  if (!s->cap) return 0;
  for (uint32_t i = (uint32_t)k & (s->cap - 1);; i = (i + 1) & (s->cap - 1)) {
    if (s->k[i] == k) return 1;
    if (!s->k[i]) return 0;
  }
}
static void hs_add(hset* s, uint64_t k)
{
  if ((s->n + 1) * 2 > s->cap) {
    uint32_t nc = s->cap ? s->cap * 2 : 4096, oc = s->cap;
    uint64_t* nk = (uint64_t*)calloc(nc, 8), *ok = s->k;
    if (!nk) return;
    s->k = nk; s->cap = nc; s->n = 0;
    for (uint32_t i = 0; i < oc; i++) if (ok[i] > 1) hs_add(s, ok[i]);
    free(ok);
  }
  for (uint32_t i = (uint32_t)k & (s->cap - 1);; i = (i + 1) & (s->cap - 1)) {
    if (s->k[i] == k) return;
    if (!s->k[i]) { s->k[i] = k; s->n++; return; }
  }
}
static void hs_del(hset* s, uint64_t k)
{
  if (!s->cap) return;
  for (uint32_t i = (uint32_t)k & (s->cap - 1);; i = (i + 1) & (s->cap - 1)) {
    if (s->k[i] == k) { s->k[i] = 1; return; }   /* the slot stays taken: n is not lowered */
    if (!s->k[i]) return;
  }
}
static void hs_clear(hset* s) { if (s->k) memset(s->k, 0, (size_t)s->cap * 8); s->n = 0; }

static hset g_done;                        /* matches in the ledger */
static hset g_quar;                        /* played matches of the career left behind at a load */
static hset g_seen, g_seen2;               /* seen played once (they count when seen again) */

static void led_push(const ent_t* e)
{
  if (g_nled == g_cled) {
    int nc = g_cled ? g_cled * 2 : 4096;
    ent_t* n = (ent_t*)realloc(g_led, (size_t)nc * sizeof(ent_t));
    if (!n) return;
    g_led = n; g_cled = nc;
  }
  g_led[g_nled++] = *e;
}
static void led_reset(void)
{
  g_nled = 0; g_last = 0;
  hs_clear(&g_done); hs_clear(&g_seen); hs_clear(&g_seen2);
}
static void led_index(void)
{
  hs_clear(&g_done); g_last = 0;
  for (int i = 0; i < g_nled; i++) {
    const ent_t* e = &g_led[i];
    if (e->kind != K_MATCH) continue;
    hs_add(&g_done, mkey(e->reg, e->year, e->month, e->day, e->a, e->b));
    int s = stamp(e->year, doy(e->year, e->month, e->day));
    if (s > g_last) g_last = s;
  }
}
/* this club already has this stage, from a match within 200 days before s */
static int stage_had(uint32_t club, unsigned base, int code, int s)
{
  for (int i = g_nled - 1; i >= 0; i--) {
    const ent_t* e = &g_led[i];
    if (e->kind != K_STAGE || (e->a >> 14) != (club >> 14) || e->reg != base || e->code != code) continue;
    int t = stamp(e->year, doy(e->year, e->month, e->day));
    if (s - t >= -200 && s - t < 200) return 1;
  }
  return 0;
}
static void credit(const unsigned char* m, int ci)
{
  int f = COMPS[ci].f, w = weight(f);
  unsigned reg = *(const uint16_t*)(m + 4);
  int code = m[6], y = *(const uint16_t*)(m + 8), mo = m[10], d = m[11];
  uint32_t a = *(const uint32_t*)(m + 0x14), b = *(const uint32_t*)(m + 0x18);
  int ga = m[0x1c], gb = m[0x1f];
  int win = (f & F_UEFA) ? 2 : 3;
  ent_t e; memset(&e, 0, sizeof e);
  e.reg = (uint16_t)reg; e.kind = K_MATCH; e.code = (uint8_t)code; e.year = (uint16_t)y; e.month = (uint8_t)mo;
  e.day = (uint8_t)d; e.a = a; e.b = b; e.ga = (uint8_t)ga; e.gb = (uint8_t)gb;
  e.pa = (int16_t)(ga > gb ? win * w : ga == gb ? w : 0);
  e.pb = (int16_t)(gb > ga ? win * w : ga == gb ? w : 0);
  led_push(&e);
  hs_add(&g_done, mkey(reg, y, mo, d, a, b));
  int s = stamp(y, doy(y, mo, d));
  if (s > g_last) g_last = s;
  /* the stage: a group stage once, a knockout or a qualifying stage by its round */
  int sc = (f & F_GROUP) ? 0 : code;
  int sp = stage_points(f, sc);
  uint32_t cl[2] = { a, b };
  for (int k = 0; k < 2; k++) {
    if (!sp || stage_had(cl[k], reg & 0x3ff, sc, s)) continue;
    ent_t t = e; t.kind = K_STAGE; t.code = (uint8_t)sc; t.reg = (uint16_t)(reg & 0x3ff);
    t.a = cl[k]; t.b = 0; t.pa = (int16_t)sp; t.pb = 0; t.ga = t.gb = 0;
    led_push(&t);
  }
}

/* ---------------------------------------------------------------- reading the table */
/* sure = 1 on the game's own thread (nothing is being written); else a match must be seen
   the same in two reads in a row. Under g_lk. */
static void harvest(int sure)
{
  unsigned char* b = block();
  if (!b || !g_mcap) return;
  int y, dy = today(b, &y);
  if (dy < 0) return;
  int now = stamp(y, dy);
  if (g_nled && now + 2 < g_last && GetTickCount64() - g_load_tick > 120000) {
    plog("a new career (today is day %d of %d, the ledger's last match day %d of %d): ledger emptied",
         dy, y, g_last % 400, g_last / 400);
    led_reset(); g_slot[0] = 0;
  }
  hs_clear(&g_seen2);
  int got = 0, played = 0, live = 0;
  for (uint32_t i = 0; i < g_mcap; i++) {
    const unsigned char* m = b + g_mbase + (size_t)i * MATCH_STRIDE;
    if (*(const volatile uint16_t*)m == 0xffff) continue;
    live++;
    if (m[7] & 0x40) played++;
    unsigned reg = *(const volatile uint16_t*)(m + 4);
    int ci = comp_of(reg);
    if (ci < 0) continue;
    unsigned char r[0x20];
    memcpy(r, m, sizeof r);
    if (*(uint16_t*)(r + 4) != reg) continue;
    uint32_t ca = *(uint32_t*)(r + 0x14), cb = *(uint32_t*)(r + 0x18);
    int yy = *(uint16_t*)(r + 8);
    if (ca == 0xffffffffu || cb == 0xffffffffu || !(ca >> 14) || !(cb >> 14) || yy < 1900 || yy > 2300) continue;
    uint64_t k = mkey(reg, yy, r[10], r[11], ca, cb);
    if (!(r[7] & 0x40)) { if (g_quar.n) hs_del(&g_quar, k); continue; }   /* still to play */
    if (hs_has(&g_done, k) || hs_has(&g_quar, k)) continue;
    uint64_t kg = k ^ ((uint64_t)r[0x1c] << 40) ^ ((uint64_t)r[0x1f] << 48) ^ ((uint64_t)r[6] << 56);
    if (kg < 2) kg += 2;
    if (!sure && !hs_has(&g_seen, kg)) { hs_add(&g_seen2, kg); continue; }
    memcpy((unsigned char*)r, m, sizeof r);
    credit(r, ci);
    got++;
  }
  hset t = g_seen; g_seen = g_seen2; g_seen2 = t;
  if (got) plog("day %d of %d: %d match(es) counted, ledger %d entries", dy, y, got, g_nled);
  if (sure) return;
  /* a career being built: the table empty (see the top) */
  if (live == 0) {
    if (!g_empty_seen) plog("day %d of %d: the match table is empty (a career being built)", dy, y);
    g_empty_seen = 1;
    if (g_nled && GetTickCount64() - g_load_tick > 60000) {
      plog("a new career (day %d of %d, the match table emptied): ledger of %s (%d entries) emptied",
           dy, y, g_slot[0] ? g_slot : "no slot", g_nled);
      led_reset(); g_slot[0] = 0;
    }
  } else {
    if (g_empty_seen) plog("day %d of %d: the match table has %d match(es) again (%d played)", dy, y, live, played);
    g_empty_seen = 0;
  }
}
static void quarantine_now(void)           /* under g_lk */
{
  unsigned char* b = block();
  hs_clear(&g_quar);
  if (!b || !g_mcap) return;
  for (uint32_t i = 0; i < g_mcap; i++) {
    const unsigned char* m = b + g_mbase + (size_t)i * MATCH_STRIDE;
    if (*(const volatile uint16_t*)m == 0xffff || !(m[7] & 0x40)) continue;
    unsigned reg = *(const volatile uint16_t*)(m + 4);
    if (comp_of(reg) < 0) continue;
    hs_add(&g_quar, mkey(reg, *(const uint16_t*)(m + 8), m[10], m[11], *(const uint32_t*)(m + 0x14), *(const uint32_t*)(m + 0x18)));
  }
}

/* ---------------------------------------------------------------- points */
static int cycle_start(int now)            /* stamp of the last reset, 0 = none yet */
{
  int y = now / 400, best = 0;
  for (int c = g_first_year; c <= y; c += g_every) if (stamp(c, g_reset_day) <= now) best = stamp(c, g_reset_day);
  return best;
}
typedef struct { uint32_t id; int q; } pt_t;
static pt_t* g_pts; static int g_npts, g_cpts;
static void pts_add(uint32_t club, int q)
{
  uint32_t id = club >> 14;
  for (int i = 0; i < g_npts; i++) if (g_pts[i].id == id) { g_pts[i].q += q; return; }
  if (g_npts == g_cpts) {
    int nc = g_cpts ? g_cpts * 2 : 512;
    pt_t* n = (pt_t*)realloc(g_pts, (size_t)nc * sizeof(pt_t));
    if (!n) return;
    g_pts = n; g_cpts = nc;
  }
  g_pts[g_npts].id = id; g_pts[g_npts].q = q; g_npts++;
}
static int pts_cmp(const void* a, const void* b) { return ((const pt_t*)b)->q - ((const pt_t*)a)->q; }
static int g_from;
static void pts_build(void)                /* the clubs' quarter points in the window, sorted; under g_lk */
{
  g_npts = 0;
  int y, dy = today(block(), &y);
  g_from = dy < 0 ? 0 : cycle_start(stamp(y, dy));
  for (int i = 0; i < g_nled; i++) {
    const ent_t* e = &g_led[i];
    if (stamp(e->year, doy(e->year, e->month, e->day)) < g_from) continue;
    if (e->pa) pts_add(e->a, e->pa);
    if (e->kind == K_MATCH && e->pb) pts_add(e->b, e->pb);
  }
  qsort(g_pts, g_npts, sizeof(pt_t), pts_cmp);
}
static int pts_of(uint32_t club)
{
  uint32_t id = club >> 14;
  for (int i = 0; i < g_npts; i++) if (g_pts[i].id == id) return g_pts[i].q;
  return 0;
}

/* ---------------------------------------------------------------- the ranking lists */
static unsigned char* g_cave;
uint64_t cwc_back = LIST_BACK;
void cwc_rewrite(unsigned char* self) __attribute__((used));
void cwc_rewrite(unsigned char* self)
{
  if (!g_cave || !*(volatile uint32_t*)g_cave || !self) return;
  unsigned char* beg = *(unsigned char**)(self + 0x98);
  unsigned char* end = *(unsigned char**)(self + 0xa0);
  if (!beg || end < beg || (end - beg) % 16 || end - beg > 16 * 20000) return;
  EnterCriticalSection(&g_lk);
  pts_build();
  int any = 0;
  for (unsigned char* e = beg; e < end; e += 16) if (pts_of(*(uint32_t*)e) > 0) { any = 1; break; }
  unsigned char* w = beg;
  int n = 0;
  for (unsigned char* e = beg; e < end; e += 16) {
    int q = pts_of(*(uint32_t*)e);
    if (any && q <= 0) continue;
    if (q < 0) q = 0;
    int shown = q / 4; if (shown > 0xffff) shown = 0xffff;
    if (w != e) memcpy(w, e, 16);
    *(uint32_t*)(w + 4) = 0x01000000u - (uint32_t)q;
    *(uint16_t*)(w + 8) = (uint16_t)shown;
    *(uint16_t*)(w + 10) = (uint16_t)shown;
    w += 16; n++;
  }
  *(unsigned char**)(self + 0xa0) = w;
  LeaveCriticalSection(&g_lk);
  static int told;
  if (told < 8) {
    told++;
    plog("list (confederation %u): %d of %d club(s) shown%s; first entry %08x", *(uint32_t*)g_cave, n,
         (int)((end - beg) / 16), any ? "" : " (nobody has points yet: all, at 0)", n ? *(uint32_t*)beg : 0);
  }
}
void cwc_list_stub(void);
__asm__(
  ".text\n.globl cwc_list_stub\ncwc_list_stub:\n"
  "  push %rbp\n  mov %rsp,%rbp\n  and $-16,%rsp\n  sub $32,%rsp\n"
  "  mov %rbx,%rcx\n  call cwc_rewrite\n"
  "  mov %rbp,%rsp\n  pop %rbp\n"
  "  mov 0xa0(%rbx),%rdx\n  jmp *cwc_back(%rip)\n");

/* The row never shows points (0x140b110a0 draws +4, the position, and the club's name only), so
   the name gets them: the two club paths of the row's name text set it with 0x140e48bf0(widget,
   std::string*, 0, 0) at 0x140b113a9 and 0x140b1141d. Those calls go to cave+0x1300 (a jmp to
   cwc_text_stub), which appends "  25 pts" to the string with the game's own assign 0x140402370
   when a filter is set, then goes on into 0x140e48bf0. The club: the row copies its team record
   ([rsp+0x38] = the entry's club, id << 14 | row, stored at the row's start). National Ranking's path (0x140b1134b) is
   left alone. */
#define TEXT_SET   0x140e48bf0ull
#define STR_ASSIGN 0x140402370ull
#define TRAMP_OFF  0x1300
uint64_t cwc_text_set = TEXT_SET;
static ULONGLONG g_pts_tick;
void cwc_text(unsigned char* str, unsigned char* crsp) __attribute__((used));
void cwc_text(unsigned char* str, unsigned char* crsp)
{
  if (!g_cave || !*(volatile uint32_t*)g_cave || !str || !crsp) return;
  uint32_t club = *(uint32_t*)(crsp + 0x38);   /* the row's entry +0, copied there by 0x140b110f5 */
  uint64_t len = *(uint64_t*)(str + 0x10), cap = *(uint64_t*)(str + 0x18);
  if (len > 200 || cap < len) return;
  const char* d = cap >= 16 ? *(const char**)str : (const char*)str;
  if (!d) return;
  EnterCriticalSection(&g_lk);
  ULONGLONG now = GetTickCount64();
  if (now - g_pts_tick > 300) { pts_build(); g_pts_tick = now; }
  int q = pts_of(club);
  LeaveCriticalSection(&g_lk);
  static char buf[8][320];
  static int k;
  char* b = buf[k++ & 7];
  int n;
  /* the league column is the points column on these screens (its header says "Pontos", see
     hook_head): only the points, the league's name is dropped */
  if (q % 4) n = snprintf(b, 320, "%d,%s", q / 4, q % 4 == 1 ? "25" : q % 4 == 2 ? "5" : "75");
  else n = snprintf(b, 320, "%d", q / 4);
  if (n <= 0 || n >= 320) return;
  ((void* (*)(void*, const char*, uint64_t))(uintptr_t)STR_ASSIGN)(str, b, (uint64_t)n);
  static int told;
  if (told < 3) { told++; plog("name text: club %08x -> \"%s\"", club, b); }
}
void cwc_text_stub(void);
__asm__(
  ".text\n.globl cwc_text_stub\ncwc_text_stub:\n"
  "  push %rbx\n  push %rsi\n  push %rdi\n  push %rbp\n  sub $0x28,%rsp\n"
  "  mov %rcx,%rbx\n  mov %rdx,%rsi\n  mov %r8,%rdi\n  mov %r9,%rbp\n"
  "  mov %rsi,%rcx\n  lea 0x50(%rsp),%rdx\n  call cwc_text\n"
  "  mov %rbx,%rcx\n  mov %rsi,%rdx\n  mov %rdi,%r8\n  mov %rbp,%r9\n"
  "  add $0x28,%rsp\n  pop %rbp\n  pop %rdi\n  pop %rsi\n  pop %rbx\n"
  "  jmp *cwc_text_set(%rip)\n");
static int hook_text(unsigned char* cave)
{
  static const uint64_t sites[2] = { 0x140b113a9ull, 0x140b1141dull };
  unsigned char* t = cave + TRAMP_OFF;
  for (int i = 0; i < 2; i++) {
    const unsigned char* c = (const unsigned char*)(uintptr_t)sites[i];
    if (c[0] != 0xe8 || sites[i] + 5 + *(const int32_t*)(c + 1) != TEXT_SET) { plog("names: %llx is not the expected call -- no points in the names", (unsigned long long)sites[i]); return 0; }
  }
  for (int i = 0; i < 16; i++) if (t[i]) { plog("names: cave+0x1300 is in use -- no points in the names"); return 0; }
  t[0] = 0xff; t[1] = 0x25; memset(t + 2, 0, 4); *(uint64_t*)(t + 6) = (uint64_t)(uintptr_t)cwc_text_stub;
  for (int i = 0; i < 2; i++) {
    unsigned char* c = (unsigned char*)(uintptr_t)sites[i];
    int64_t d = (int64_t)(uintptr_t)t - (int64_t)(sites[i] + 5);
    if (d < -0x7fffffffll || d > 0x7fffffffll) { plog("names: cave out of reach"); return 0; }
    DWORD old;
    if (!VirtualProtect(c, 5, PAGE_EXECUTE_READWRITE, &old)) return 0;
    *(int32_t*)(c + 1) = (int32_t)d;
    VirtualProtect(c, 5, old, &old);
    FlushInstructionCache(GetCurrentProcess(), c, 5);
  }
  plog("names: the club names on the confederation screens carry the points");
  return 1;
}

/* The league column's header: the fill 0x140b108c0 sets title_group with 0x140e48fc0(widget,
   text id) at 0x140b10978, edx = 0x1901fb ("Liga"; 0x26003f "Area" on National Ranking). That
   call goes to cave+0x1310 (a jmp to cwc_head_stub), which puts 0x190143 ("Pontos", the same text
   category) in edx when a filter is set. The world Club Ranking and National Ranking (filter 0)
   keep theirs. */
#define HEAD_CALL 0x140b10978ull
#define HEAD_SET  0x140e48fc0ull
#define HEAD_OFF  0x1310
uint64_t cwc_head_set = HEAD_SET;
unsigned char* cwc_cave;
void cwc_head_stub(void);
__asm__(
  ".text\n.globl cwc_head_stub\ncwc_head_stub:\n"
  "  mov cwc_cave(%rip),%rax\n  test %rax,%rax\n  je 1f\n"
  "  cmpl $0,(%rax)\n  je 1f\n  mov $0x190143,%edx\n"
  "1:\n  jmp *cwc_head_set(%rip)\n");
static int hook_head(unsigned char* cave)
{
  const unsigned char* c = (const unsigned char*)(uintptr_t)HEAD_CALL;
  if (c[0] != 0xe8 || HEAD_CALL + 5 + *(const int32_t*)(c + 1) != HEAD_SET || c[-8] != 0xba || *(const uint32_t*)(c - 7) != 0x1901fb)   /* mov edx,0x1901fb; mov rcx,rbp; call */
    { plog("header: %llx is not the expected call -- the header keeps \"Liga\"", (unsigned long long)HEAD_CALL); return 0; }
  unsigned char* t = cave + HEAD_OFF;
  for (int i = 0; i < 16; i++) if (t[i]) { plog("header: cave+0x1310 is in use -- the header keeps \"Liga\""); return 0; }
  int64_t d = (int64_t)(uintptr_t)t - (int64_t)(HEAD_CALL + 5);
  if (d < -0x7fffffffll || d > 0x7fffffffll) { plog("header: cave out of reach"); return 0; }
  cwc_cave = cave;
  t[0] = 0xff; t[1] = 0x25; memset(t + 2, 0, 4); *(uint64_t*)(t + 6) = (uint64_t)(uintptr_t)cwc_head_stub;
  DWORD old;
  unsigned char* w = (unsigned char*)(uintptr_t)HEAD_CALL;
  if (!VirtualProtect(w, 5, PAGE_EXECUTE_READWRITE, &old)) return 0;
  *(int32_t*)(w + 1) = (int32_t)d;
  VirtualProtect(w, 5, old, &old);
  FlushInstructionCache(GetCurrentProcess(), w, 5);
  plog("header: the league column of the confederation screens is now \"Pontos\"");
  return 1;
}

static int hook_list(void)
{
  const unsigned char* s = (const unsigned char*)LIST_SITE;
  if (s[0] != 0xe9) { plog("lists: 0x140b10ac2 is not fl26contrank's jump -- load fl26cwc after fl26contrank; the screens keep the squad points"); return 0; }
  unsigned char* x = (unsigned char*)(LIST_SITE + 5 + *(const int32_t*)(s + 1));
  unsigned char* cave = x - EXTRA_OFF;
  static const unsigned char tail[13] = { 0x48, 0x8b, 0x93, 0xa0, 0, 0, 0, 0xff, 0x25, 0, 0, 0, 0 };
  MEMORY_BASIC_INFORMATION mb;
  if (!VirtualQuery(cave, &mb, sizeof mb) || mb.State != MEM_COMMIT || memcmp(x + EXTRA_TAIL, tail, 13) ||
      *(uint64_t*)(x + EXTRA_TAIL + 13) != LIST_BACK) {
    plog("lists: fl26contrank's stub is not the one expected -- the screens keep the squad points");
    return 0;
  }
  g_cave = cave;
  DWORD old;
  if (!VirtualProtect(x + EXTRA_TAIL + 13, 8, PAGE_EXECUTE_READWRITE, &old)) { plog("lists: VirtualProtect failed"); return 0; }
  InterlockedExchange64((volatile LONG64*)(x + EXTRA_TAIL + 13), (LONG64)(uintptr_t)cwc_list_stub);
  VirtualProtect(x + EXTRA_TAIL + 13, 8, old, &old);
  plog("lists: the confederation screens are ordered by the CWC points (fl26contrank page %p)", (void*)cave);
  hook_text(cave);
  hook_head(cave);
  return 1;
}

/* ---------------------------------------------------------------- files */
static char g_save_dir[MAX_PATH * 3];
#define FILE_MAGIC "FL26CWC1"
static int led_load(const char* slot)      /* under g_lk; entries read, -1 = no file */
{
  char p[MAX_PATH * 3 + 32];
  snprintf(p, sizeof p, "%s\\%s.fl26cwc", g_save_dir, slot);
  led_reset();
  FILE* f = fl26_u8open(p, L"rb");
  if (!f) return -1;
  char mg[8]; uint32_t n = 0;
  if (fread(mg, 1, 8, f) != 8 || memcmp(mg, FILE_MAGIC, 8) || fread(&n, 4, 1, f) != 1 || n > 2000000) {
    fclose(f); plog("%s.fl26cwc is not a ledger -- starting empty", slot); return 0;
  }
  for (uint32_t i = 0; i < n; i++) { ent_t e; if (fread(&e, sizeof e, 1, f) != 1) break; led_push(&e); }
  fclose(f);
  led_index();
  return g_nled;
}
/* the copy taken at the save, written when the game's own file is in place */
static ent_t* g_copy; static int g_ncopy; static char g_copy_slot[16]; static int g_copy_ok;
static void copy_take(const char* slot)    /* under g_lk */
{
  free(g_copy); g_copy = 0; g_ncopy = 0; g_copy_ok = 0;
  /* what may still matter: the window, and 400 days back for the matches still in the table */
  int y, dy = today(block(), &y);
  int keep = dy < 0 ? 0 : cycle_start(stamp(y, dy));
  if (dy >= 0 && stamp(y, dy) - 400 < keep) keep = stamp(y, dy) - 400;
  g_copy = (ent_t*)malloc((size_t)(g_nled ? g_nled : 1) * sizeof(ent_t));
  if (!g_copy) return;
  int champs = dy < 0 ? 0 : stamp(y - CHAMP_KEEP_YEARS, dy);
  for (int i = 0; i < g_nled; i++) {
    int t = stamp(g_led[i].year, doy(g_led[i].year, g_led[i].month, g_led[i].day));
    if (t >= keep || (g_led[i].kind == K_CHAMP && t >= champs)) g_copy[g_ncopy++] = g_led[i];
  }
  snprintf(g_copy_slot, sizeof g_copy_slot, "%s", slot);
  g_copy_ok = 1;
}
static void copy_write(const char* slot)
{
  EnterCriticalSection(&g_lk);
  if (!g_copy_ok || strcmp(slot, g_copy_slot)) { LeaveCriticalSection(&g_lk); return; }
  char p[MAX_PATH * 3 + 32], t[MAX_PATH * 3 + 40];
  snprintf(p, sizeof p, "%s\\%s.fl26cwc", g_save_dir, slot);
  snprintf(t, sizeof t, "%s.tmp", p);
  FILE* f = fl26_u8open(t, L"wb");
  int ok = 0;
  if (f) {
    uint32_t n = (uint32_t)g_ncopy;
    ok = fwrite(FILE_MAGIC, 1, 8, f) == 8 && fwrite(&n, 4, 1, f) == 1 &&
         (n == 0 || fwrite(g_copy, sizeof(ent_t), n, f) == n);
    ok = (fclose(f) == 0) && ok;
  }
  if (ok) ok = fl26_u8move(t, p);
  plog("save: %s.fl26cwc %s (%d entries)", slot, ok ? "written" : "NOT written", g_ncopy);
  g_copy_ok = 0;
  LeaveCriticalSection(&g_lk);
}

/* ---------------------------------------------------------------- the game's save files */
static DWORD g_main_tid;
static char g_pending_load[16];            /* a slot read by the loader, taken in by our thread */
/* A load reads the slot on two threads, one after the other (probe 3: 9936 then 1516; run of
   11:14: 4460 then 11552). A save reads every slot once, on the game's thread, for its list
   (that thread is not the one modules start on). So: the same slot read by a second thread
   within 15 s = a load. The played matches in memory at the first read are what is set aside. */
static char g_rd_slot[16]; static DWORD g_rd_tid; static ULONGLONG g_rd_tick;
static hset g_cand;
/* "...\save\ML0000000N" or LG (+ ".tmp"): 1 = the save, 2 = its .tmp, 0 = something else */
static int save_name(const wchar_t* w, int n, char* slot)
{
  int i = n;
  while (i > 0 && w[i - 1] != L'\\') i--;
  const wchar_t* b = w + i; int bl = n - i;
  if (bl != 10 && !(bl == 14 && !_wcsnicmp(b + 10, L".tmp", 4))) return 0;
  if (!((b[0] == L'M' && b[1] == L'L') || (b[0] == L'L' && b[1] == L'G'))) return 0;
  for (int k = 2; k < 10; k++) if (!iswxdigit(b[k])) return 0;
  if (i < 6 || _wcsnicmp(w + i - 6, L"\\save\\", 6)) return 0;
  for (int k = 0; k < 10; k++) slot[k] = (char)b[k];
  slot[10] = 0;
  return bl == 10 ? 1 : 2;
}

typedef NTSTATUS (NTAPI* NtCreateFile_t)(PHANDLE, ACCESS_MASK, POBJECT_ATTRIBUTES, PIO_STATUS_BLOCK,
                                         PLARGE_INTEGER, ULONG, ULONG, ULONG, ULONG, PVOID, ULONG);
static NtCreateFile_t o_NtCreateFile;
static NTSTATUS NTAPI h_NtCreateFile(PHANDLE h, ACCESS_MASK acc, POBJECT_ATTRIBUTES oa, PIO_STATUS_BLOCK io,
                                     PLARGE_INTEGER sz, ULONG attr, ULONG share, ULONG disp, ULONG opt, PVOID ea, ULONG eal)
{
  NTSTATUS r = o_NtCreateFile(h, acc, oa, io, sz, attr, share, disp, opt, ea, eal);
  if (r < 0 || !oa || !oa->ObjectName || !oa->ObjectName->Buffer || oa->ObjectName->Length < 32) return r;
  char slot[16];
  int kind = save_name(oa->ObjectName->Buffer, oa->ObjectName->Length / 2, slot);
  if (!kind) return r;
  DWORD e = GetLastError();
  int wr = (acc & (GENERIC_WRITE | FILE_WRITE_DATA | FILE_APPEND_DATA)) != 0;
  DWORD tid = GetCurrentThreadId();
  if (kind == 2 && wr) {
    /* the game is saving this slot: the table once more here, on its own thread */
    EnterCriticalSection(&g_lk);
    harvest(1);
    copy_take(slot);
    snprintf(g_slot, sizeof g_slot, "%s", slot);
    int n = g_nled;
    LeaveCriticalSection(&g_lk);
    plog("save: %s being written (thread %lu); ledger %d entries copied", slot, tid, n);
  } else if (kind == 1 && !wr) {
    ULONGLONG now = GetTickCount64();
    EnterCriticalSection(&g_lk);
    if (!strcmp(slot, g_rd_slot) && tid != g_rd_tid && now - g_rd_tick < 15000) {
      hset t = g_quar; g_quar = g_cand; g_cand = t;
      snprintf(g_pending_load, sizeof g_pending_load, "%s", slot);
      g_rd_slot[0] = 0;
      unsigned q = g_quar.n;
      LeaveCriticalSection(&g_lk);
      plog("load: %s read by threads %lu and %lu; %u played match(es) of the career in memory set aside", slot, g_rd_tid, tid, q);
    } else {
      hset t = g_quar; g_quar = g_cand; quarantine_now(); g_cand = g_quar; g_quar = t;   /* snapshot into g_cand */
      snprintf(g_rd_slot, sizeof g_rd_slot, "%s", slot); g_rd_tid = tid; g_rd_tick = now;
      LeaveCriticalSection(&g_lk);
      plog("read: %s by thread %lu", slot, tid);
    }
  }
  SetLastError(e);
  return r;
}

/* NtCreateFile: the plain syscall stub, or (in the game) apphelp's shim, 40 53 55 56 57 ... */
static void owner_of(const void* p, char* out, int cap)
{
  HMODULE m = 0;
  if (GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT, (LPCSTR)p, &m) && m) {
    char f[MAX_PATH] = ""; GetModuleFileNameA(m, f, sizeof f);
    const char* b = strrchr(f, '\\');
    snprintf(out, cap, "%s+0x%llx", b ? b + 1 : f, (unsigned long long)((const unsigned char*)p - (const unsigned char*)m));
  } else snprintf(out, cap, "no module");
}
static int hook_ntcreate(void)
{
  HMODULE nt = GetModuleHandleA("ntdll.dll");
  unsigned char* p = (unsigned char*)GetProcAddress(nt, "NtCreateFile");
  static const unsigned char head[4] = { 0x4c, 0x8b, 0xd1, 0xb8 };
  static const unsigned char tail[16] = { 0xf6, 0x04, 0x25, 0x08, 0x03, 0xfe, 0x7f, 0x01, 0x75, 0x03, 0x0f, 0x05, 0xc3, 0xcd, 0x2e, 0xc3 };
  static const unsigned char push4[5] = { 0x40, 0x53, 0x55, 0x56, 0x57 };
  if (!p) { plog("no NtCreateFile export -- saves are not followed"); return 0; }
  char who[400]; owner_of(p, who, sizeof who);
  int plain = !((uintptr_t)p & 7) && !memcmp(p, head, 4) && !p[6] && !p[7] && !memcmp(p + 8, tail, 16);
  int pushes = !((uintptr_t)p & 7) && !memcmp(p, push4, 5);
  if (!plain && !pushes) {
    char hx[80] = ""; for (int i = 0; i < 24; i++) sprintf(hx + 2 * i, "%02x", p[i]);
    plog("NtCreateFile (%s) starts %s, not known -- saves are not followed", who, hx);
    return 0;
  }
  unsigned char* relay = 0;
  uintptr_t a = ((uintptr_t)p & ~(uintptr_t)0xffff) - 0x10000;
  for (int k = 0; k < 4096 && !relay; k++, a -= 0x10000)
    relay = (unsigned char*)VirtualAlloc((void*)a, 0x1000, MEM_RESERVE | MEM_COMMIT, PAGE_EXECUTE_READWRITE);
  if (!relay) { plog("no relay page near NtCreateFile -- saves are not followed"); return 0; }
  int64_t d = (int64_t)(relay + 0x40) - (int64_t)(p + 5);
  if (d < -0x7fffffffll || d > 0x7fffffffll) { plog("relay out of reach -- saves are not followed"); return 0; }
  if (plain) memcpy(relay, p, 24);
  else {
    memcpy(relay, p, 5);
    relay[5] = 0xff; relay[6] = 0x25; memset(relay + 7, 0, 4);
    *(uint64_t*)(relay + 11) = (uint64_t)(uintptr_t)(p + 5);
  }
  o_NtCreateFile = (NtCreateFile_t)relay;
  relay[0x40] = 0xff; relay[0x41] = 0x25; memset(relay + 0x42, 0, 4);
  *(uint64_t*)(relay + 0x46) = (uint64_t)(uintptr_t)h_NtCreateFile;
  FlushInstructionCache(GetCurrentProcess(), relay, 0x100);
  unsigned char nw[8];
  memcpy(nw, p, 8);
  nw[0] = 0xe9; *(int32_t*)(nw + 1) = (int32_t)d;
  DWORD old;
  if (!VirtualProtect(p, 8, PAGE_EXECUTE_READWRITE, &old)) { plog("VirtualProtect NtCreateFile failed -- saves are not followed"); return 0; }
  InterlockedExchange64((volatile LONG64*)p, *(LONG64*)nw);
  VirtualProtect(p, 8, old, &old);
  FlushInstructionCache(GetCurrentProcess(), p, 8);
  plog("saves followed: NtCreateFile (%s, %s start) hooked", who, plain ? "stub" : "shim");
  return 1;
}

/* ---------------------------------------------------------------- our threads */
static DWORD WINAPI watch_thread(LPVOID unused)
{
  (void)unused;
  wchar_t wd[MAX_PATH * 2];
  if (!fl26_u2w(g_save_dir, wd, MAX_PATH * 2)) return 0;
  HANDLE d = CreateFileW(wd, FILE_LIST_DIRECTORY, FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
                         0, OPEN_EXISTING, FILE_FLAG_BACKUP_SEMANTICS, 0);
  if (d == INVALID_HANDLE_VALUE) { plog("watch: cannot open %s (%lu) -- the ledgers will not be written", g_save_dir, GetLastError()); return 0; }
  static DWORD buf[8192];
  DWORD got;
  for (;;) {
    if (!ReadDirectoryChangesW(d, buf, sizeof buf, FALSE, FILE_NOTIFY_CHANGE_FILE_NAME | FILE_NOTIFY_CHANGE_LAST_WRITE, &got, 0, 0)) {
      plog("watch: ReadDirectoryChangesW failed (%lu) -- the ledgers will not be written", GetLastError()); break;
    }
    if (!got) continue;
    for (FILE_NOTIFY_INFORMATION* fi = (FILE_NOTIFY_INFORMATION*)buf;;
         fi = (FILE_NOTIFY_INFORMATION*)((char*)fi + fi->NextEntryOffset)) {
      wchar_t nm[300]; int n = fi->FileNameLength / 2; if (n > 290) n = 290;
      memcpy(nm, L"\\save\\", 12);
      memcpy(nm + 6, fi->FileName, n * 2); nm[6 + n] = 0;
      char slot[16];
      if ((fi->Action == FILE_ACTION_RENAMED_NEW_NAME || fi->Action == FILE_ACTION_ADDED) &&
          save_name(nm, 6 + n, slot) == 1) copy_write(slot);
      if (!fi->NextEntryOffset) break;
    }
  }
  CloseHandle(d);
  return 0;
}
static DWORD WINAPI read_thread(LPVOID unused)
{
  (void)unused;
  for (;;) {
    Sleep(1000);
    EnterCriticalSection(&g_lk);
    if (g_pending_load[0]) {
      char s[16]; snprintf(s, sizeof s, "%s", g_pending_load); g_pending_load[0] = 0;
      int n = led_load(s);
      snprintf(g_slot, sizeof g_slot, "%s", s);
      g_load_tick = GetTickCount64();
      if (n < 0) plog("load: %s has no .fl26cwc yet: its ranking starts empty", s);
      else plog("load: %s.fl26cwc read, %d entries", s, n);
    }
    harvest(0);
    LeaveCriticalSection(&g_lk);
  }
  return 0;
}

/* ---------------------------------------------------------------- exports */
__declspec(dllexport) int fl26_cwc_install(int first_year, int reset_day)
{
  if (!g_cs_ok) { InitializeCriticalSection(&g_cs); InitializeCriticalSection(&g_lk); g_cs_ok = 1; }
  static int done;
  if (done) return 0;
  done = 1;
  if (first_year > 1900) g_first_year = first_year;
  if (reset_day >= 0 && reset_day < 366) g_reset_day = reset_day;
  g_main_tid = GetCurrentThreadId();
  unsigned char* exe = (unsigned char*)GetModuleHandleA(0);
  IMAGE_NT_HEADERS64* nh = (IMAGE_NT_HEADERS64*)(exe + ((IMAGE_DOS_HEADER*)exe)->e_lfanew);
  if ((uintptr_t)exe != 0x140000000ull || nh->OptionalHeader.SizeOfImage < 0x3800000) {
    plog("not the FL26 exe -- nothing installed");
    return 0;
  }
  const unsigned char* bs = (const unsigned char*)MATCH_BASE_SITE;
  const unsigned char* cs = (const unsigned char*)MATCH_CAP_SITE;
  if (bs[0] != 0x48 || bs[1] != 0x8d || bs[2] != 0x88 || cs[0] != 0x81 || cs[1] != 0xff) {
    plog("the match table walk is not where expected -- nothing installed");
    return 0;
  }
  g_mbase = *(const uint32_t*)(bs + 3); g_mcap = *(const uint32_t*)(cs + 2);
  if (!g_mcap || g_mcap > 200000) { plog("match table cap %u -- nothing installed", g_mcap); return 0; }
  if (!fl26_save_dir(g_save_dir, sizeof g_save_dir)) { plog("no save folder found -- nothing installed"); return 0; }
  g_game = 1;
  int lists = hook_list();
  int saves = hook_ntcreate();
  HANDLE t1 = CreateThread(0, 0, read_thread, 0, 0, 0);
  HANDLE t2 = saves ? CreateThread(0, 0, watch_thread, 0, 0, 0) : 0;
  if (t1) CloseHandle(t1);
  if (t2) CloseHandle(t2);
  plog("installed: match table +0x%x x %u, save folder %s, main thread %lu; resets on day %d of %d + 4k",
       g_mbase, g_mcap, g_save_dir, g_main_tid, g_reset_day, g_first_year);
  return 1 + 2 * lists + 4 * saves;
}
/* the Club World Cup's cycle in years (the world file's cwc32 every=, Mod Studio's option); 4 before */
__declspec(dllexport) int fl26_cwc_every(int every)
{
  if (every >= 1 && every <= 8) g_every = every;
  return g_every;
}
/* a few lines for the overlay */
__declspec(dllexport) int fl26_cwc_status(char* out, int cap)
{
  if (!g_cs_ok || cap < 64) return 0;
  EnterCriticalSection(&g_lk);
  pts_build();
  int n = snprintf(out, cap, "slot %s, ledger %d entries, %d club(s) with points, ",
                   g_slot[0] ? g_slot : "(none yet)", g_nled, g_npts);
  if (g_from) n += snprintf(out + n, cap - n, "since day %d of %d", g_from % 400, g_from / 400);
  else n += snprintf(out + n, cap - n, "since the start (first reset day %d of %d)", g_reset_day, g_first_year);
  for (int i = 0; i < g_npts && i < 5 && n < cap - 48; i++)
    n += snprintf(out + n, cap - n, "\n  %d. club %u: %d.%02d", i + 1, g_pts[i].id, g_pts[i].q / 4, (g_pts[i].q % 4) * 25);
  LeaveCriticalSection(&g_lk);
  return n < cap ? n : cap - 1;
}
/* every club's points and every entry, for checking */
__declspec(dllexport) int fl26_cwc_report(const char* path)
{
  if (!g_cs_ok) return -1;
  EnterCriticalSection(&g_lk);
  FILE* f = fopen(path, "w");
  if (!f) { LeaveCriticalSection(&g_lk); return -1; }
  pts_build();
  int y = 0, dy = today(block(), &y);
  fprintf(f, "fl26cwc: slot %s, today day %d of %d, ledger %d entries, window from day %d of %d (0 = the start)\n\n",
          g_slot, dy, y, g_nled, g_from % 400, g_from / 400);
  for (int i = 0; i < g_npts; i++) fprintf(f, "%4d. club %6u  %d.%02d\n", i + 1, g_pts[i].id, g_pts[i].q / 4, (g_pts[i].q % 4) * 25);
  fprintf(f, "\nentries (points in quarters):\n");
  for (int i = 0; i < g_nled; i++) {
    const ent_t* e = &g_led[i];
    if (e->kind == K_MATCH)
      fprintf(f, "%04d-%02d-%02d reg %5u r%02x match %6u %d-%d %6u  %+d %+d\n", e->year, e->month, e->day, e->reg, e->code,
              e->a >> 14, e->ga, e->gb, e->b >> 14, e->pa, e->pb);
    else if (e->kind == K_CHAMP)
      fprintf(f, "%04d-%02d-%02d reg %5u champion %6u\n", e->year, e->month, e->day, e->reg, e->a >> 14);
    else
      fprintf(f, "%04d-%02d-%02d reg %5u r%02x stage %6u  %+d\n", e->year, e->month, e->day, e->reg, e->code, e->a >> 14, e->pa);
  }
  int n = g_npts;
  fclose(f);
  LeaveCriticalSection(&g_lk);
  return n;
}

/* ---- for fl26swiss.dll's Club World Cup of 32 (2026-11-17) ----
 * fl26_cwc_champion: a continental cup's winner as fl26swiss sees it (at the teardowns and at the
 *   draw); the same club for the same cup within 200 days is one title. 1 = new, 0 = known.
 * fl26_cwc_champions: every title the ledger has, newest last: cup, club, year, day of the year.
 * fl26_cwc_ranking: the clubs with points in the window, best first: team id (handle >> 14) and
 *   quarter points. All 0 before the ranking is installed (another exe, no save folder). */
__declspec(dllexport) int fl26_cwc_champion(int reg, uint32_t club)
{
  if (!g_cs_ok || !g_game || !(club >> 14) || reg <= 0 || reg > 0xffff) return 0;
  EnterCriticalSection(&g_lk);
  int y, dy = today(block(), &y), fresh = 0;
  if (dy >= 0) {
    int now = stamp(y, dy);
    fresh = 1;
    for (int i = 0; i < g_nled && fresh; i++) {
      const ent_t* e = &g_led[i];
      if (e->kind == K_CHAMP && e->reg == reg && (e->a >> 14) == (club >> 14) &&
          now - stamp(e->year, doy(e->year, e->month, e->day)) < 200 &&
          now - stamp(e->year, doy(e->year, e->month, e->day)) > -200) fresh = 0;
    }
    if (fresh) {
      static const int len[12] = { 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31 };
      int m = 0, d = dy;                   /* the game's day of the year as a month and day */
      while (m < 11 && d >= len[m] + (m == 1 && leap(y))) { d -= len[m] + (m == 1 && leap(y)); m++; }
      m++;
      ent_t e; memset(&e, 0, sizeof e);
      e.reg = (uint16_t)reg; e.kind = K_CHAMP; e.year = (uint16_t)y; e.month = (uint8_t)m; e.day = (uint8_t)(d + 1);
      e.a = club;
      led_push(&e);
      plog("champion: cup %d won by club %u (day %d of %d)", reg, club >> 14, dy, y);
    }
  }
  LeaveCriticalSection(&g_lk);
  return fresh;
}
__declspec(dllexport) int fl26_cwc_champions(uint16_t* reg, uint32_t* club, uint16_t* year, uint16_t* day, int max)
{
  if (!g_cs_ok || !g_game || max <= 0) return 0;
  EnterCriticalSection(&g_lk);
  int n = 0;
  for (int i = 0; i < g_nled && n < max; i++) {
    const ent_t* e = &g_led[i];
    if (e->kind != K_CHAMP) continue;
    reg[n] = e->reg; club[n] = e->a; year[n] = e->year; day[n] = (uint16_t)doy(e->year, e->month, e->day);
    n++;
  }
  LeaveCriticalSection(&g_lk);
  return n;
}
__declspec(dllexport) int fl26_cwc_ranking(uint32_t* id, int32_t* q, int max)
{
  if (!g_cs_ok || !g_game || max <= 0) return 0;
  EnterCriticalSection(&g_lk);
  pts_build();
  int n = 0;
  for (int i = 0; i < g_npts && n < max; i++) {
    if (g_pts[i].q <= 0) continue;
    id[n] = g_pts[i].id; q[n] = g_pts[i].q; n++;
  }
  LeaveCriticalSection(&g_lk);
  return n;
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD why, LPVOID r) { (void)h; (void)why; (void)r; return TRUE; }
