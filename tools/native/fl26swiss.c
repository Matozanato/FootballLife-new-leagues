/* fl26swiss.dll -- give a 36-club league phase the modern UEFA draw.
 *
 * Why (docs/league-phase-swiss-decode.md): a league regulation in this engine always plays a
 * complete round robin. 0x1413f29e0 fixes the number of matchdays at rounds * (N-1) and
 * 0x1413f3e00 fills every pair with the circle method, so 36 clubs means 35 matchdays and 630
 * matches. Nothing in the data says "each club plays eight opponents". The Champions League and
 * Europa League league phase therefore cannot be expressed in data at all.
 *
 * What this does: it replaces the generic schedule builder 0x1413f3e00 for OUR regulations
 * only. For anything else the original runs untouched. For ours it allocates the same grid
 * through the game's own 0x1413f30f0, writes the pairings from the generated table in
 * fl26swiss_table.h, sets the matchday count, and returns success. The caller 0x1413f36c0 then
 * runs the game's own emitter 0x1413f4430, so dates, fixture records and standings are all the
 * game's.
 *
 * The draw (tools/mkswiss.py, verified there): 36 clubs, 144 matches, every club with 8
 * different opponents, exactly two from each pot of nine, exactly four home and four away.
 * Each of the eight rounds is a perfect matching of all 36 clubs and is split over two
 * matchdays of nine, because a fixture record holds 16 match slots and 0x1413f4430 drops the
 * rest in silence. Sixteen matchdays is also well inside the 58 a competition may hold.
 *
 * Facts used, all read statically:
 *   - 0x1413f36c0 passes the REGULATION id; unknown ids fall through to 0x1413f3e00 and then
 *     to the emitter unconditionally (0x1413f38b1, 0x1413f38bb, 0x1413f38c9).
 *   - schedule context: +0x08 grid, +0x20 club list (u32), +0x38 matchday count, +0x3c legs,
 *     +0x40 padded club count, +0x44 odd-club flag.
 *   - the grid is vector<vector<vector<cell>>>: [ctx+0x08] is the outer begin, each element is
 *     a 24-byte vector, each of those holds 24-byte row vectors, each row holds 8-byte cells
 *     {u32 matchday, u32 side}. Addressing copied from the shipped seeder at 0x1413f43a9.
 *   - side 0 at cell(i,j) means i is at home: the emitter puts club i at +0x14 when the side
 *     byte is 0 and at +0x18 when it is 1 (0x1413f45ec, 0x1413f4610).
 *   - unwritten cells hold matchday 0x37, which no real matchday ever equals.
 *
 * Built with `zig cc` (tools/native/build-swiss.sh). Our own code, no third-party binaries.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>

#include "fl26savedir.h"
#include "fl26swiss_table.h"
#include "fl26swiss_draw.h"

#define GEN_RVA   0x13f3e00    /* bool build_generic_schedule(ctx, u16 reg id, u8 flag) */
#define GRID_RVA  0x13f30f0    /* void alloc_grid(ctx) -- legs x N x N cells, cleared     */
#define DATE_RVA  0x157f810    /* void fixture_dates(u16 reg id in cx, vector<date>* rdx)  */
#define CASE5_RVA 0x1582550    /* the shipped 38-round league calendar, same signature     */
#define GROUP_RVA 0x13f3c30    /* bool build_group_of_four(ctx) -- the first replica of each
                                  shipped European group stage (ids 0x403/0x405/...) goes here */

#define OFF_GRID      0x08
#define OFF_CLUBS     0x20
#define OFF_MATCHDAYS 0x38
#define OFF_LEGS      0x3c
#define OFF_PADDED    0x40

#define MAX_REGS 8
#define FL26_SWISS_MIN_CLUBS 28   /* a short field costs its clubs matches; below this, too many */
#define FL26_SWISS_MAX_CLUBS 48   /* a regulation's club list holds 48 */

/* the 16 bytes we steal: mov [rsp+8],rcx / push rbx / push rsi / push rdi / sub rsp,0x60 /
   movzx edi,r8b -- all position independent */
static const unsigned char SIG_GEN[16] = {
  0x48,0x89,0x4c,0x24,0x08, 0x53, 0x56, 0x57, 0x48,0x83,0xec,0x60, 0x41,0x0f,0xb6,0xf8 };

/* and the 17 of the date lookup: push rbp (REX-prefixed, as the chain hook's apply site was
   too) / push rbx / push rdi / mov rbp,rsp / sub rsp,0x20 / mov rbx,rdx / movzx edi,cx */
static const unsigned char SIG_DATE[17] = {
  0x40,0x55, 0x53, 0x57, 0x48,0x8b,0xec, 0x48,0x83,0xec,0x20, 0x48,0x8b,0xda, 0x0f,0xb7,0xf9 };

/* and the 14 of the group builder: mov [rsp+0x18],rbx / push rbp / push rdi / push r14 /
   lea rbp,[rsp-0x47] -- position independent, and exactly the 14 the jump needs */
static const unsigned char SIG_GROUP[14] = {
  0x48,0x89,0x5c,0x24,0x18, 0x55, 0x57, 0x41,0x56, 0x48,0x8d,0x6c,0x24,0xb9 };

typedef struct { unsigned char* b; unsigned char* e; unsigned char* c; } vec_t;  /* 24 bytes */
typedef struct { uint32_t md; uint32_t side; } cell_t;
typedef struct { uint32_t day; uint32_t round; uint32_t kind; } date_t;  /* 12 bytes */

/* The league phase's sixteen matchdays, as days of the year.  Two matchdays a week in the
   European weeks the real competition uses, and the last four in January -- the day counter
   is a calendar year, so a January date is a small number after a December one, exactly as
   the shipped 38-round array wraps from 363 to 2.  On a Tuesday and Wednesday of the shipped
   big-league calendar's week (case 5: Saturday is 261, 268, ...): they were the Thursday and
   Friday, the day before the league's Saturday, and a club played three matches in four days
   (5 October). A league round still too near is moved by rest_dates. */
#define FL26_DATE_KIND_LEAGUE 2
static const uint32_t SWISS_DAYS[FL26_SWISS36_MATCHDAYS] = {
  257, 258, 271, 272, 292, 293, 306, 307, 327, 328, 341, 342, 19, 20, 26, 27 };

/* The Conference League plays six matchdays, one opponent from each of six pots (the second
   table in fl26swiss_table.h), on the Thursdays of the same calendar: 1 and 22 October, 5 and
   26 November, 10 and 17 December.  Each round is two dates because a fixture record holds 16
   matches and a round of 36 clubs is 18: the Wednesday before carries the first nine. */
static const uint32_t UECL_DAYS[FL26_SWISS6_MATCHDAYS] = {
  272, 273, 293, 294, 307, 308, 328, 329, 342, 343, 349, 350 };

typedef char (*gen_fn)(void* ctx, uint64_t reg, uint64_t flag);
typedef void (*grid_fn)(void* ctx);
typedef char (*group_fn)(void* ctx);
typedef uint64_t (*date_fn)(uint64_t reg, void* vec);

static uint64_t       g_base = 0;
#include "fl26layout.h"   /* block offsets read from the code fl26caps patched */
unsigned char*        g_tramp_gen = 0;
unsigned char*        g_tramp_date = 0;
unsigned char*        g_tramp_group = 0;
static uint16_t       g_reg[MAX_REGS];
static int            g_nreg = 0;

/* calls seen, schedules written, refused, cells out of range, calendars written */
static volatile uint32_t g_stat[5];

/* ---- small text log, drained by the Lua loader into sider.log ----
   The loader drains it when the game loads a file. Under ML Fast Forward the hub loads nothing
   for weeks of game days, and 64 KB filled by mid-season: from then on every line was dropped
   unsaid -- the Sudamericana play-off fill and the group stages' end were missing from our own
   test's sider.log (29.10.) while the ties were there. 1 MB, and the lines lost are counted
   and reported at the next drain. */
static char g_log[1 << 20]; static volatile int g_log_len = 0;
static volatile uint32_t g_log_lost = 0;
static void logf(const char* fmt, ...)
{
  char line[256]; va_list ap; va_start(ap, fmt);
  int n = vsnprintf(line, sizeof line, fmt, ap); va_end(ap);
  if (n <= 0) return; if (n >= (int)sizeof line) n = sizeof line - 1;
  /* a test with fl26swiss-trace.on in the game's folder: every line also straight to
     fl26swiss-trace.log, so a crash under Fast Forward (nothing drained for months) leaves them */
  static int tr = -1; static FILE* tf;
  if (tr < 0) { FILE* on = fopen("fl26swiss-trace.on", "r"); tr = on != 0; if (on) { fclose(on); tf = fopen("fl26swiss-trace.log", "a"); } }
  if (tf) { fwrite(line, 1, n, tf); fputc('\n', tf); fflush(tf); }
  if (g_log_len + n + 1 >= (int)sizeof g_log) {
    /* Megapack 07.11.: a season of Fast Forward still filled 1 MB, and 4325 lines were lost --
       among them every line of the May days a play-off bug was looked for. What does not fit
       goes to fl26swiss-overflow.log in the game's folder, in order, and the drain says so. */
    static FILE* of;
    if (!of) of = fopen("fl26swiss-overflow.log", "a");
    if (of) { fwrite(line, 1, n, of); fputc('\n', of); fflush(of); }
    g_log_lost++; return;
  }
  memcpy(g_log + g_log_len, line, n); g_log_len += n; g_log[g_log_len++] = '\n';
}

static int ours(uint16_t reg)
{
  for (int i = 0; i < g_nreg; i++) if (g_reg[i] == reg) return 1;
  return 0;
}

/* FL27 (SmokePatch, 31.10.2026) plays the Champions and Europa League league phase itself: one
 * group of 36 in 1027 / 1029, its own knockout of 24 in reg 4 / 6 (play-off included), filled by
 * its own hook on set_clubs. mato 31.10.: "Njihovu ligu prvaka i europsku ligu koristimo". So
 * there, of those two competitions, only who gets in is ours -- the access list and the summer's
 * qualifying rounds, handed to their league phase at the August draw. The Conference League
 * (174, not in FL27) stays ours whole. Set by fl26_swiss_install when set_clubs starts with
 * their jmp. CUPS index 0 / 1 = the Champions / Europa League. */
static int g_native_uefa = 0;
static int cup_on(int ci) { return !(g_native_uefa && ci < 2); }

/* Days after SWISS_DAYS that a listed competition plays.  It used to be two days a competition
   -- the Europa League on the Thursday and Friday after the Champions League -- but those are
   exactly the days the shipped league calendars play on (case 5: 261, 275, 296, 310, 331, 345,
   23, 31; cases 28, 37, 44, 49 too), so a club of the game's own leagues had a league match on
   eight of its sixteen Europa League days and one result went into both tables (GitHub #54,
   Tony on Discord).  Every league phase now plays on the same days; a club is only ever in
   one of them, and 36 more matches a day is far from the 280 a day holds. */
static uint32_t day_shift(uint16_t reg)
{
  (void)reg;
  return 0;
}

/* The Champions League play-off, regulation 2 and its replicas 0x402, 0x802, ... (the shipped
   case at 0x14158155b: days 230 and 237). A career that starts on day 212 enters the European
   competitions on day 238, after both legs, so the play-off got no matches at all, the group
   stage never filled and the Europa League never started (2026-09-23, calread: no match of
   competition 2 on any day). Both legs move to the August play-offs' days (qr_day: the fifth
   and sixth of the qualifying's six weeks, one leg a week), at least six days before the first
   league-phase matchday (swiss_day). (In 0.2.0 before 08.10. Tuesday and Thursday of one week;
   until then 241 and 248, before that 244 and 251, the national cups' first round -- Slavia
   played Benfica and the Czech cup's first leg on the same day, rwee 07.10.) */
static volatile uint32_t g_playoff_said = 0;
static int is_playoff(uint16_t id)
{
  return (id & 0x3ff) == 2 && id <= 0x2002;
}

/* Diagnostics: the first time a European competition's regulation (2..7 and their replicas)
   reaches the schedule builder or the date lookup, say so -- which of them the game builds at
   all is exactly what is in question for a career that starts in August. */
static unsigned char g_seen[2][64];
/* The Conference League, added by tools/mkphases.py as a clone of the reshaped Europa League:
   competition 174, league phase 186 (one group, row 186 + 1024 = 1210), knockout 187.  The ids
   are those mkphases hands out first in _FL26G39UCL36; a world that numbers it differently
   needs them changed here. */
#define UECL_REG 186
#define UECL_KO  187
#define UECL_ROW 1210
/* The knockout play-offs tools/mkeuropo.py adds to the Europa League and the Conference League:
   a copy of reg 2 each, ties at id + 1024 * (k + 1).  A world without them keeps the old
   behaviour -- the top sixteen go straight to the round of 16. */
#define UEL_PO   188
#define UECL_PO  189
static int new_po(uint16_t id)
{
  return ((id & 0x3ff) == UEL_PO || (id & 0x3ff) == UECL_PO) && id <= UECL_PO + 8 * 1024;
}
/* The qualifying rounds in front of the August play-offs (see the August qualifying rounds
   below): more copies of reg 2, under the ids the world file's qround lines name -- round i is
   competition i % 3 at stage i / 3, 3..5 the third qualifying rounds, 6..8 the second, 9..11
   the first (FL27 only, in July: see q1_world); 0..2, the play-offs, are 2, 188 and 189 and stay
   0 here. */
#define NQ  3                            /* the three competitions */
#define NQS 4                            /* stages: play-off, third, second, first qualifying round */
#define NQR (NQ * NQS)
#define Q_MAX 64                         /* the most clubs a round holds (q_n): 62 in a wide
                                            Conference League (qcw_world), 32 until then */
static uint16_t g_qreg[NQR];
/* FL27's first qualifying round (in July, from a career's second season): competition c has one
   when the world file names it and the game is FL27 (fl26_swiss_qrounds takes it there only) */
static int q1_world(int c) { return g_native_uefa && c >= 0 && c < NQ && g_qreg[c + NQ * 3]; }
/* FL27, Prijedlog C (mato 07.11., notes/uefa-q1-srpanj.md): the world file names August play-offs
   of 32 for the Europa League and the Conference League (`qround 11 0 <reg>`, `qround 12 0 <reg>`,
   taken only when g_native_uefa) -- regulations of their own, so 188 and 189 stay the February
   knockout play-offs of sixteen. Its rounds and sizes (q_n):
     UCL Q1 32 -> Q2 32 -> Q3 16 -> PO 16 (reg 2);  UEL Q1 16 -> Q2 16 -> Q3 32 -> PO 32;
     UECL Q2 32 -> Q3 32 -> PO 32 (no first round). The losers: UCL Q1 -> UECL Q2 (q_down), UCL Q2
   -> UEL Q3, UCL Q3 -> UEL PO, UCL PO -> UEL league phase; UEL Q1 -> UECL Q2, Q2 -> UECL Q3, Q3 ->
   UECL PO, PO -> UECL league phase. New clubs 56 / 40 / 16, 112 in all; direct entrants 28 / 12 / 4. */
static int qc_world(void) { return g_native_uefa && g_qreg[1] && g_qreg[2]; }
#define FL26_PRIJEDLOG_C 1               /* for the native harness (test_uefa_c.c) */
/* FL27, Prijedlog C with a wide Conference League (mato 07.11.: "kvalifikacije za europu
   prosiriti ako je to moguce"; fl26world.CW_CONFIG): a C world whose file also names the
   Conference League's July first qualifying round (`qround 12 1 <reg>`). The Champions League's
   and the Europa League's rounds stay C's; the Conference League's are
     Q1 62 -> Q2 62 -> Q3 40 -> PO 40,
   the first round's 31 losers out, its second round fed by the 31 winners, the 16 Champions
   League Q1 losers and the 8 Europa League Q1 losers (7 new), its third by the 31 winners and the
   8 Europa League Q2 losers (1 new), its play-off by the 20 winners and the 16 Europa League Q3
   losers (4 new). Its league phase is the play-off's 20 winners and the Europa League play-off's
   16 losers: no direct entrants (cap), a place of the list straight into it goes to the play-off.
   New clubs 56 / 40 / 74, 170 in all. A first summer (no July rounds) fills the second round
   with 62 new clubs. 62 is the most a round of reg 2's copies can hold (the master's six-bit
   club count; Q_MAX). */
static int qcw_world(void) { return qc_world() && g_qreg[NQ - 1 + NQ * 3]; }
#define FL26_UECL_WIDE 1                 /* for the native harness (test_uecl_wide.c) */
/* the clubs round i holds: sixteen in eight ties; 32 in sixteen for a first qualifying round and
   for the second qualifying round of a competition that has one; a Prijedlog C world's by its table */
static unsigned q_n(int i)
{
  static const unsigned char QC_N[NQR] = { 16, 32, 32, 16, 32, 32, 32, 16, 32, 32, 16, 16 };
  static const unsigned char QCW_N[NQR] = { 16, 32, 40, 16, 32, 40, 32, 16, 62, 32, 16, 62 };
  if (i >= 0 && i < NQR && qcw_world()) return QCW_N[i];
  if (i >= 0 && i < NQR && qc_world()) return QC_N[i];
  return i >= NQ * 2 && i < NQR && q1_world(i % NQ) ? 32 : 16;
}
/* the round a regulation or a tie of it is, -1 none: the added qualifying rounds (3..11) and a
   Prijedlog C world's own play-offs of 32 (1, 2; g_qreg 0 is never set: reg 2 is the game's) */
static int q_added(uint16_t id)
{
  for (int i = 1; i < NQR; i++) if (g_qreg[i] && (id & 0x3ff) == g_qreg[i] && (id >> 10) <= q_n(i) / 2) return i;
  return -1;
}
static int european(uint16_t id)
{
  return ((id & 0x3ff) >= 2 && (id & 0x3ff) <= 7 && id < 0x3400) || id == UECL_REG || id == UECL_KO || id == UECL_ROW
      || new_po(id) || q_added(id) >= 0;
}
static void seen_once(int what, uint16_t id, size_t n)
{
  unsigned k = ((id >> 10) & 0x0f) * 8 + (id & 0x07);
  if (k >= 64 || g_seen[what][k]) return;
  g_seen[what][k] = 1;
  logf("fl26swiss: seen %s for reg %u (%u clubs)", what ? "dates" : "schedule", (unsigned)id, (unsigned)n);
}

/* One grid cell, with every length checked; NULL if the grid is not the shape we expect. */
static cell_t* cell_at(void* ctx, uint32_t leg, uint32_t i, uint32_t j)
{
  vec_t* outer = (vec_t*)((unsigned char*)ctx + OFF_GRID);
  if (!outer->b || outer->e < outer->b) return 0;
  if ((size_t)leg >= (size_t)(outer->e - outer->b) / sizeof(vec_t)) return 0;
  vec_t* legv = (vec_t*)(outer->b + (size_t)leg * sizeof(vec_t));
  if (!legv->b || legv->e < legv->b) return 0;
  if ((size_t)i >= (size_t)(legv->e - legv->b) / sizeof(vec_t)) return 0;
  vec_t* rowv = (vec_t*)(legv->b + (size_t)i * sizeof(vec_t));
  if (!rowv->b || rowv->e < rowv->b) return 0;
  if ((size_t)j >= (size_t)(rowv->e - rowv->b) / sizeof(cell_t)) return 0;
  return (cell_t*)(rowv->b + (size_t)j * sizeof(cell_t));
}

/* The replacement for 0x1413f3e00. MS x64 ABI: rcx = ctx, dx = regulation id, r8b = flag. */
static int spread_leagues(const uint32_t* clubs, int n, const fl26_pair_t* table, int npairs, int pot,
                          uint8_t* perm, uint16_t id);
static void lb_clear_phase(uint16_t row);
char gen_handler(void* ctx, uint64_t reg, uint64_t flag)
{
  g_stat[0]++;
  uint16_t id = (uint16_t)reg;
  if (ctx && european(id)) {
    vec_t* cl = (vec_t*)((unsigned char*)ctx + OFF_CLUBS);
    seen_once(0, id, (cl->b && cl->e >= cl->b) ? (size_t)(cl->e - cl->b) / 4 : 0);
  }
  if (!ctx || !ours(id))
    return ((gen_fn)(uintptr_t)g_tramp_gen)(ctx, reg, flag);

  vec_t*    clubs  = (vec_t*)((unsigned char*)ctx + OFF_CLUBS);
  uint32_t* legs   = (uint32_t*)((unsigned char*)ctx + OFF_LEGS);
  uint32_t* padded = (uint32_t*)((unsigned char*)ctx + OFF_PADDED);
  size_t nclubs = (clubs->b && clubs->e >= clubs->b) ? (size_t)(clubs->e - clubs->b) / 4 : 0;

  /* A reshaped shipped competition (the Champions League's regulation 3, the Europa League's 5)
     is filled by the game from rights and entries, so its field is not guaranteed to be exactly
     36. A short field still gets the draw: every pair that names a slot past the last club is
     skipped, and whoever was drawn against an empty slot plays one match fewer. Falling back to the game
     instead would build a full double round robin -- 70 matchdays for 36, past the 58 a
     competition may hold. */
  /* Asked before the field exists: a reshaped Champions League / Europa League phase enters its
     season on day ~238, before the draw has put anyone in it, and 0x1413f29e0 leaves the club
     list empty. The original builder does not survive an empty list (2026-09-23: 0x1484ed4c0
     right after it), so the answer is "nothing built" and the original is never called. */
  if (nclubs < 2) {
    g_stat[2]++;
    logf("fl26swiss: reg %u asked with %u clubs -- nothing to draw yet, nothing built",
         (unsigned)id, (unsigned)nclubs);
    return 0;
  }

  /* The other way round too: in the first season of a new career the Europa League came up
     with 40 (2026-09-23), past the 36 it declares. Clubs past the 36th are left without a
     match rather than handing the whole phase to the round robin. */
  if (nclubs < FL26_SWISS_MIN_CLUBS || nclubs > FL26_SWISS_MAX_CLUBS ||
      *padded < nclubs || *legs < 1) {
    g_stat[2]++;
    logf("fl26swiss: reg %u has %u clubs (padded %u, legs %u) -- need %d..%d; left to the game",
         (unsigned)id, (unsigned)nclubs, (unsigned)*padded, (unsigned)*legs,
         FL26_SWISS_MIN_CLUBS, FL26_SWISS_MAX_CLUBS);
    return ((gen_fn)(uintptr_t)g_tramp_gen)(ctx, reg, flag);
  }
  if (nclubs > FL26_SWISS36_CLUBS)
    logf("fl26swiss: reg %u has %u clubs -- only the first %d are drawn, the rest play no "
         "league-phase match", (unsigned)id, (unsigned)nclubs, FL26_SWISS36_CLUBS);

  ((grid_fn)(uintptr_t)(g_base + GRID_RVA))(ctx);      /* the game's own grid, cleared */

  int six = id == UECL_ROW;
  const fl26_pair_t* table = six ? FL26_SWISS6 : FL26_SWISS36;
  int npairs = six ? FL26_SWISS6_PAIRS : FL26_SWISS36_PAIRS;
  int nmd = six ? FL26_SWISS6_MATCHDAYS : FL26_SWISS36_MATCHDAYS;
  int rejected = 0, skipped = 0;
  /* Which club sits on which place of the draw: the table is by list position, so on its own it
     pairs whoever the positions hold, two clubs of one league included (Evo-Web, 2026-09-28:
     Manchester United - Manchester City on the fourth round). */
  uint8_t perm[FL26_SWISS36_CLUBS];
  spread_leagues((const uint32_t*)clubs->b, nclubs < FL26_SWISS36_CLUBS ? (int)nclubs : FL26_SWISS36_CLUBS, table, npairs,
                 six ? 6 : 9, perm, id);
  for (int k = 0; k < npairs; k++) {
    const fl26_pair_t* p = &table[k];
    if (p->home >= nclubs || p->away >= nclubs) { skipped++; continue; }
    cell_t* h = cell_at(ctx, 0, perm[p->home], perm[p->away]);
    cell_t* a = cell_at(ctx, 0, perm[p->away], perm[p->home]);
    if (!h || !a) { rejected++; continue; }
    h->md = p->md; h->side = 0;                        /* side 0 at (i,j): i is at home */
    a->md = p->md; a->side = 1;
  }
  if (rejected) { g_stat[3] += rejected; logf("fl26swiss: reg %u -- %d of %d pairs did not fit the grid",
                                              (unsigned)id, rejected, npairs); }

  *(uint32_t*)((unsigned char*)ctx + OFF_MATCHDAYS) = (uint32_t)nmd;
  g_stat[1]++;
  logf("fl26swiss: reg %u -- league phase written: %u clubs, %d matches, %d matchdays%s",
       (unsigned)id, (unsigned)nclubs, npairs - rejected - skipped, nmd,
       *legs > 1 ? " (regulation has more than one leg; only the first is used)" : "");
  lb_clear_phase(id);
  return 1;
}

/* The replacement for 0x1413f3c30.  rcx = ctx, already filled by 0x1413f29e0.
 *
 * The Champions League and Europa League league phase is kept as ONE group of 36 (the draw only
 * ever fills clubs into a group, so a phase without groups stays empty). That group's
 * regulation is the first replica, 0x403 / 0x405, and 0x1413f36c0 sends exactly those ids to
 * this builder, which only knows four clubs and six matchdays. So: with a full field it builds
 * nothing and says so, and the caller (0x1413f389e: al == 0) falls through to the generic
 * builder 0x1413f3e00 -- which is gen_handler above, where the replica id is ours. A shipped
 * group of four never reaches the threshold and gets the original. */
char group_handler(void* ctx)
{
  vec_t* clubs = ctx ? (vec_t*)((unsigned char*)ctx + OFF_CLUBS) : 0;
  size_t nclubs = (clubs && clubs->b && clubs->e >= clubs->b) ? (size_t)(clubs->e - clubs->b) / 4 : 0;
  if (nclubs < FL26_SWISS_MIN_CLUBS)
    return ((group_fn)(uintptr_t)g_tramp_group)(ctx);
  logf("fl26swiss: group builder asked for %u clubs -- passed on to the league-phase draw",
       (unsigned)nclubs);
  return 0;
}

/* Watch only: who fills and who empties a European competition's club list.  A career that
 * starts in August reached day 261 with the Champions League (3) and Europa League (5) both
 * in season and both at 0 clubs, and the league phase (1027 / 1029) never entered -- although
 * a run on the narrower set had 3 at 24 clubs and 5 at 40 before they entered (2026-09-23).
 * The three writers of the count at +0x30a (read statically): add one club 0x1414c9a10
 * (refuses past 48), clear the list 0x1414c9740, set the count 0x1414ca080.  Each line says
 * which, for which regulation, the count before, and the return address that asked. */
#define ADDCLUB_RVA  0x14c9a10
#define CLRCLUB_RVA  0x14c9740
#define SETCOUNT_RVA 0x14ca080
static const unsigned char SIG_ADDCLUB[17] = {
  0x44,0x8b,0x81,0x08,0x03,0x00,0x00, 0x4c,0x8b,0xc9, 0x41,0x8b,0xc0, 0x89,0x54,0x24,0x10 };
static const unsigned char SIG_CLRCLUB[16] = {
  0x4c,0x8b,0xc9, 0x48,0x8d,0x91,0x70,0x01,0x00,0x00, 0x41,0xb8,0x30,0x00,0x00,0x00 };
static const unsigned char SIG_SETCOUNT[16] = {
  0x81,0xa1,0x08,0x03,0x00,0x00,0xff,0xff,0x80,0xff, 0x83,0xe2,0x7f, 0xc1,0xe2,0x10 };
typedef void (*rec_fn)(void* rec, uint64_t a);
static uint16_t g_expect_group = 0xffff; static volatile int g_group_cleared = 0;
unsigned char* g_tramp_add = 0;
unsigned char* g_tramp_clr = 0;
unsigned char* g_tramp_set = 0;
static uint32_t rec_count(void* rec) { return (*(uint32_t*)((unsigned char*)rec + 0x308) >> 16) & 0x7f; }
static uint16_t rec_id(void* rec) { return *(uint16_t*)rec; }

/* Consecutive adds from one caller to one regulation come as a run; say the run once, when it
   ends, instead of one line a club. */
static uint16_t g_run_id = 0xffff; static uintptr_t g_run_ra = 0; static uint32_t g_run_from = 0, g_run_n = 0;
static void run_flush(void)
{
  if (g_run_n)
    logf("fl26swiss: watch reg %u -- %u club(s) added by %llx, count %u -> %u",
         (unsigned)g_run_id, (unsigned)g_run_n, (unsigned long long)(g_run_ra - g_base + 0x140000000ull),
         (unsigned)g_run_from, (unsigned)(g_run_from + g_run_n));
  g_run_n = 0; g_run_id = 0xffff;
}

static uint32_t cont_add(void* rec, uint32_t club);
void addclub_handler(void* rec, uint64_t club)
{
  uintptr_t ra = (uintptr_t)__builtin_return_address(0);
  if (rec) { uint32_t to = cont_add(rec, (uint32_t)club); if (to) club = (club & ~0xffffffffull) | to; }
  if (rec && european(rec_id(rec))) {
    if (rec_id(rec) != g_run_id || ra != g_run_ra) { run_flush(); g_run_id = rec_id(rec); g_run_ra = ra; g_run_from = rec_count(rec); }
    if (rec_count(rec) >= 48) logf("fl26swiss: watch reg %u -- add refused, list full (48)", (unsigned)rec_id(rec));
    else g_run_n++;
  }
  ((rec_fn)(uintptr_t)g_tramp_add)(rec, club);
}

void clrclub_handler(void* rec, uint64_t unused)
{
  uintptr_t ra = (uintptr_t)__builtin_return_address(0);
  if (rec && rec_id(rec) == g_expect_group) g_group_cleared = 1;
  if (rec && european(rec_id(rec))) {
    run_flush();
    void* fr[8]; USHORT n = RtlCaptureStackBackTrace(1, 8, fr, NULL); char chain[160]; int o = 0;
    for (USHORT i = 0; i < n && o < (int)sizeof chain - 20; i++)
      o += snprintf(chain + o, sizeof chain - o, " %llx", (unsigned long long)((uintptr_t)fr[i] - g_base + 0x140000000ull));
    logf("fl26swiss: watch reg %u -- list cleared by %llx (had %u), stack%s", (unsigned)rec_id(rec),
         (unsigned long long)(ra - g_base + 0x140000000ull), (unsigned)rec_count(rec), chain);
  }
  ((rec_fn)(uintptr_t)g_tramp_clr)(rec, unused);
}

void setcount_handler(void* rec, uint64_t n)
{
  uintptr_t ra = (uintptr_t)__builtin_return_address(0);
  if (rec && european(rec_id(rec))) {
    run_flush();
    logf("fl26swiss: watch reg %u -- count set %u -> %u by %llx", (unsigned)rec_id(rec),
         (unsigned)rec_count(rec), (unsigned)(n & 0x7f), (unsigned long long)(ra - g_base + 0x140000000ull));
  }
  ((rec_fn)(uintptr_t)g_tramp_set)(rec, n);
}

/* Getting the clubs INTO the league phase.
 *
 * After the play-off, 0x141344920 rebuilds the Champions League entry list (reg 3: the direct
 * entrants plus the play-off winners) and the Europa League one (reg 5: its entrants plus the
 * play-off losers).  Each list is handed to the seeding 0x14155cd30 and then to set_clubs
 * 0x141522b50, and when the competition has groups, to the group draw 0x1415485c0, which splits
 * it over the group rows and calls set_clubs once per group.
 *
 * The seeding builds pots for the old 8x4 group stage.  With the league phase reshaped into one
 * group of 36 it fails, and on failure it does not leave the list alone -- it empties it
 * (0x14155ce0c: end = begin, then appends an empty vector).  set_clubs then clears reg 3 and
 * reg 5 and adds nothing, so the league phase starts with no clubs at all.
 *
 * Two hooks, both only for reg 3 and reg 5:
 *   - seeding: remember the list; if the original comes back with it emptied, put it back.
 *     Order stays the entry order (direct entrants first, then the play-off winners).
 *   - group draw: run the original; if it never touched our league-phase row (1027 / 1029),
 *     give that row the whole list with set_clubs, exactly as the draw would have. */
#define SEED_RVA   0x155cd30
#define GDRAW_RVA  0x15485c0
#define SETCL_RVA  0x1522b50
static const unsigned char SIG_SEED[15] = {
  0x48,0x8b,0xc4, 0x55, 0x48,0x8d,0x68,0xa1, 0x48,0x81,0xec,0xb0,0x00,0x00,0x00 };
static const unsigned char SIG_GDRAW[16] = {
  0x48,0x8b,0xc4, 0x57, 0x48,0x83,0xec,0x40, 0x48,0xc7,0x40,0xd8,0xfe,0xff,0xff,0xff };
typedef struct { uint32_t* b; uint32_t* e; uint32_t* c; } u32vec;
typedef char (*seed_fn)(uint64_t id, u32vec* list);
typedef void (*gdraw_fn)(uint64_t id, u32vec* list, uint64_t flag);
typedef void (*setcl_fn)(uint64_t id, u32vec* list, uint64_t flag);
unsigned char* g_tramp_seed = 0;
unsigned char* g_tramp_gdraw = 0;
static uint16_t phase_row(uint16_t id)
{
  if (g_native_uefa && (id == 3 || id == 5)) return 0xffff;   /* FL27's own league phase */
  return id == 3 ? 1027 : id == 5 ? 1029 : id == UECL_REG ? UECL_ROW : 0xffff;
}
#define OWNER_RVA  0x14b6a60
#define GETREC_RVA 0x14bb000
#define FIELD 36
typedef void* (*owner_fn)(void);
typedef void* (*getrec_fn)(void* blk, uint64_t id);
/* 0x1414bb000 never answers "not found": for an id the world does not have it returns a blank
   record that belongs to no regulation (blk + 0xd0b77c on the stock layout).  Every caller here
   takes 0 to mean "this world has no such regulation", so a record is only returned when it is
   the one asked for.  Until 2026-09-26 the blank came back as if it were real, and a world built
   without tools/mkeuropo.py had its Europa League play-off run into regulation 188, which did
   not exist (issue #9: "(0 clubs)", then the results screen crashed). */
static unsigned char* get_rec(uint16_t id)
{
  unsigned char* o = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
  if (!o) return 0;
  void* blk = *(void**)(o + 0x48);
  unsigned char* r = blk ? (unsigned char*)((getrec_fn)(uintptr_t)(g_base + GETREC_RVA))(blk, id) : 0;
  return r && *(uint16_t*)r == id ? r : 0;
}
static uint32_t* rec_clubs(unsigned char* rec) { return (uint32_t*)(rec + 0x170); }
/* One club, two handles: the team id is the handle's upper 18 bits. The lower 14 were compared
 * here, and they are distinct for the game's clubs (002000b8, 001fc0b7 ...) but 0 for every
 * club of a new league (45f8c000, 45f6c000 ...): any two of ours were the same club, and a
 * playoff of eight took its first club and refused the other seven (201, 2026-09-29: "only 1
 * of 8 clubs found"). A value with no team id still goes by the lower bits. */
static int same_club(uint32_t a, uint32_t c)
{
  if ((a >> 14) && (c >> 14)) return (a >> 14) == (c >> 14);
  return (a & 0x3fff) == (c & 0x3fff);
}
static int has_club(const uint32_t* a, size_t n, uint32_t c)
{
  for (size_t i = 0; i < n; i++) if (same_club(a[i], c)) return 1;
  return 0;
}
/* a table (20-byte rows, the club first) whose every row is a club of want */
static int table_of_clubs(const unsigned char* t, unsigned rows, const uint32_t* want, unsigned nwant)
{
  for (unsigned k = 0; k < rows; k++) if (!has_club(want, nwant, *(const uint32_t*)(t + k * 20))) return 0;
  return 1;
}
/* the Champions League clubs taken from the Europa League list, so the Europa League can drop them */
static uint32_t g_moved[FIELD]; static unsigned g_nmoved = 0;
/* the Europa League's direct entrants cut to make room, first in line for the Conference League */
static uint32_t g_spill[48]; static unsigned g_nspill = 0;

char seed_handler(uint64_t id, u32vec* list)
{
  uint16_t r = (uint16_t)id;
  if (phase_row(r) == 0xffff || !list || !list->b) return ((seed_fn)(uintptr_t)g_tramp_seed)(id, list);
  uint32_t keep[64]; size_t n = (size_t)(list->e - list->b); if (n > 64) n = 64;
  memcpy(keep, list->b, n * 4);
  char ok = ((seed_fn)(uintptr_t)g_tramp_seed)(id, list);
  size_t after = list->b ? (size_t)(list->e - list->b) : 0;
  if (after == 0 && n && list->b && (size_t)(list->c - list->b) >= n) {
    memcpy(list->b, keep, n * 4); list->e = list->b + n;
    logf("fl26swiss: reg %u -- seeding emptied the list of %u; put back in entry order", (unsigned)r, (unsigned)n);
  } else
    logf("fl26swiss: reg %u -- seeding %u -> %u clubs", (unsigned)r, (unsigned)n, (unsigned)after);
  /* The Europa League list is its direct entrants (the regulation's clubs right now) followed by
     the play-off losers.  Take out the clubs moved up to the Champions League, then cut the
     direct part so that direct + losers is 36. */
  if (r == 5 && list->b) {
    unsigned char* rec = get_rec(5);
    size_t m = (size_t)(list->e - list->b), direct = rec ? rec_count(rec) : m;
    if (direct > m) direct = m;
    size_t losers = m - direct, w = 0, dropped = 0, removed = 0;
    size_t keep_direct = losers < FIELD ? FIELD - losers : 0;
    uint32_t* a = list->b;
    g_nspill = 0;
    for (size_t i = 0; i < m; i++) {
      if (i < direct && has_club(g_moved, g_nmoved, a[i])) { removed++; continue; }
      if (i < direct && (w >= keep_direct)) { dropped++; if (g_nspill < 48) g_spill[g_nspill++] = a[i]; continue; }
      a[w++] = a[i];
    }
    list->e = list->b + w;
    logf("fl26swiss: reg 5 -- %u moved up to the Champions League taken out, %u direct entrants over the 36 left out; %u clubs",
         (unsigned)removed, (unsigned)dropped, (unsigned)w);
  }
  return ok;
}

static u32vec* access_list(uint16_t r, uint64_t flag);
static int assoc_source(uint16_t source);
static int g_confed_n;
static int confed_of(int f);
static int team_country(void* blk, uint32_t club);
static uint32_t conmebol_fallback(void* blk, const uint32_t* taken, unsigned nt);
static int lib_path_has(uint32_t c);
static int libq_f3_ready(void);
static uint32_t knockout_runner_now(uint16_t reg);
static uint32_t ccup_ko_winner(uint16_t reg);
static unsigned lib9_titleholders(uint32_t holder[2]);
static int modern_conmebol(void);
static void lib9_clean(u32vec* list);
static void lib9_holders(u32vec* list);
static void cont_swap(uint16_t id, u32vec* list, const char* where);
static unsigned world_cup_clubs(uint32_t* out, unsigned cap);
static int cont_comp(uint16_t id);
static int today(void);
void gdraw_handler(uint64_t id, u32vec* list, uint64_t flag)
{
  uint16_t r = (uint16_t)id, row = phase_row(r);
  if (row == 0xffff) {
    if (g_native_uefa && (r == 3 || r == 5)) {    /* FL27: our access list into their league phase */
      u32vec* acc = access_list(r, flag);
      if (acc) list = acc;
      logf("fl26swiss: reg %u -- FL27's own group draw, %s (%u clubs)", (unsigned)r,
           acc ? "with the access list" : "with the game's list", (unsigned)(list && list->b ? list->e - list->b : 0));
      ((gdraw_fn)(uintptr_t)g_tramp_gdraw)(id, list, flag);
      return;
    }
    cont_swap(r, list, "group draw");
    ((gdraw_fn)(uintptr_t)g_tramp_gdraw)(id, list, flag);
    return;
  }
  u32vec* acc = access_list(r, flag);
  if (acc) list = acc;
  g_expect_group = row; g_group_cleared = 0;
  ((gdraw_fn)(uintptr_t)g_tramp_gdraw)(id, list, flag);
  g_expect_group = 0xffff;
  size_t n = list && list->b ? (size_t)(list->e - list->b) : 0;
  if (!g_group_cleared && n) {
    logf("fl26swiss: reg %u -- group draw left reg %u empty; giving it all %u clubs", (unsigned)r, (unsigned)row, (unsigned)n);
    ((setcl_fn)(uintptr_t)(g_base + SETCL_RVA))(row, list, flag & 0xff);
    run_flush();
  } else
    logf("fl26swiss: reg %u -- group draw %s reg %u (%u clubs in)", (unsigned)r, g_group_cleared ? "filled" : "skipped", (unsigned)row, (unsigned)n);
  /* A Champions League short of 36 is topped up from the head of the Europa League's list -- the
     regulation still holds its direct entrants at this point, the Europa League is rebuilt next. */
  if (r == 3) {
    unsigned char *uel = get_rec(5), *ucl = get_rec(3), *ph = get_rec(1027);
    g_nmoved = 0;
    if (uel && ucl && ph) {
      unsigned have = rec_count(ph), nu = rec_count(uel);
      for (unsigned i = 0; i < nu && have + g_nmoved < FIELD; i++) {
        uint32_t c = rec_clubs(uel)[i];
        if (has_club(rec_clubs(ph), rec_count(ph), c)) continue;
        g_moved[g_nmoved++] = c;
      }
      for (unsigned i = 0; i < g_nmoved; i++) {
        ((rec_fn)(uintptr_t)(g_base + 0x14c9a10))(ucl, g_moved[i]);
        ((rec_fn)(uintptr_t)(g_base + 0x14c9a10))(ph, g_moved[i]);
      }
      run_flush();
      logf("fl26swiss: reg 3 -- topped up with %u club(s) from the Europa League list: reg 1027 now %u",
           g_nmoved, rec_count(ph));
    }
  }
}

/* Knockout entry after the league phase.  When a group stage ends, 0x141345cc0 asks 0x141346180 for
 * the qualifiers: it walks every group of the stage and takes the first N rows of each group's
 * table, N being four bits of the stage's +0x304 (bits 20-23, so at most 15).  With the league
 * phase as one group of 36 that is the top two, and the Champions League knockout (reg 4) was
 * handed two clubs; the Europa League knockout (reg 6) got its own top two plus the Champions
 * League's third, the old drop-down (2026-09-24, day 30).
 *
 * Both lists reach the regulation through set_clubs 0x141522b50, which only reads the vector.  The
 * wrapper hands it the top 16 of the league-phase table instead, whatever the game worked out:
 * reg 4 from 1027, reg 6 from 1029.  Ranks 17-36 go out; in the 2024 format nobody drops down.
 * The table is 0x141579b90(id): rows of 20 bytes in rank order, club id first, row count at
 * +0x3c0 (the qualifier code reads it exactly so).  The 9-24 play-off is not there yet: 1-16 go
 * straight to the round of 16. */
#define TABLE_RVA 0x1579b90
static const unsigned char SIG_SETCL[15] = {
  0x48,0x89,0x5c,0x24,0x08, 0x48,0x89,0x6c,0x24,0x10, 0x48,0x89,0x74,0x24,0x18 };
typedef char (*setclr_fn)(uint64_t id, u32vec* list, uint64_t flag);
typedef unsigned char* (*table_fn)(uint64_t id);
unsigned char* g_tramp_setcl = 0;
#define KO_N 16
/* A league phase's table when its competition's next season is already open.
 * 0x141579b90 answers from the competition's LATEST season: 0x14159ebf0 takes the higher year of
 * the two season slots in the competition's header ([owner+0x78] + h*0xb4, slots at +4 and +0x5c,
 * u16 year at +4, up to 20 table indices at +8), and 0x14158df30 walks that slot's tables for the
 * id.  On 2026-10-13 (test world, second season) the Europa League's header held 2026 and 2027 by
 * February -- its next season opened early, over the 2025 slot, while the Champions League still
 * held 2025 / 2026 -- so reg 1029 read the new season's empty table: 0 rows, the play-off's end
 * found "no table" and the round of 16 was never drawn.  The 2026 table was intact (36 rows).
 * So when the latest season's table of a league-phase row is short, this walks both slots of
 * every header the same way and takes that id's table of the latest season with 24..48 rows.  The offset
 * of the table array, the number of headers and of tables come from the patched code
 * (pool_layout: fl26hdr255 and the standings step move them). */
static int table_of_clubs(const unsigned char* t, unsigned rows, const uint32_t* want, unsigned nwant);
/* The pool's layout as the patched code has it: a header of nh entries of 0xb4 at [owner+0x78],
 * nt phase tables of 0x187c from arr.  Shipped: 100 entries, 600 tables at 0x4650; fl26hdr255:
 * 255, 595 at 0xb34c; the standings step of the FL 2027 limits set (tools/standings.py): 1024
 * entries, the tables moved to the old end of the grown object, 2400 at 0x3a2ef0.  So none of the
 * three is assumed: the table base is the lea at 0x14158df91, the count the allocator's bound at
 * 0x14158f381, the header count the header initialiser's at 0x1414fd4e3. */
#define POOL_BASE_LEA  0x158df91   /* 49 8d 82 disp32   lea rax, [r10 + base]               */
#define POOL_COUNT_CMP 0x158f381   /* 81 fb imm32       cmp ebx, count (first-free scan)    */
#define POOL_HDR_MOV   0x14fd4e3   /* 41 b9 imm32       mov r9d, entries (stamped free)     */
#define POOL_MAX 8192
static int pool_layout(uint32_t* arr, unsigned* nh, unsigned* nt)
{
  const unsigned char* a = (const unsigned char*)(uintptr_t)(g_base + POOL_BASE_LEA);
  const unsigned char* c = (const unsigned char*)(uintptr_t)(g_base + POOL_COUNT_CMP);
  const unsigned char* h = (const unsigned char*)(uintptr_t)(g_base + POOL_HDR_MOV);
  if (!g_base || a[0] != 0x49 || a[1] != 0x8d || a[2] != 0x82 || c[0] != 0x81 || c[1] != 0xfb
      || h[0] != 0x41 || h[1] != 0xb9) return 0;
  uint32_t b, n, k;
  memcpy(&b, a + 3, 4); memcpy(&n, c + 2, 4); memcpy(&k, h + 2, 4);
  if (k < 100 || k > 4096 || n < 1 || n > POOL_MAX || b < k * 0xb4) return 0;
  /* in place (ending below the member at 0x39a8f0) or at the old end of the object */
  if (b + (uint64_t)n * 0x187c > 0x39a8f0 && b < 0x3a2ef0) return 0;
  *arr = b; *nh = k; *nt = n;
  return 1;
}
/* the same walk for any table: rows in lo..hi and, given want, only clubs of want (a group's
   table of an earlier season holds other clubs: B169, 20.10.) */
static unsigned char* season_table_x(uint16_t reg, unsigned lo, unsigned hi, const uint32_t* want, unsigned nwant,
                                     unsigned* year_out)
{
  uint32_t arr; unsigned nh, nt;
  if (!pool_layout(&arr, &nh, &nt)) return 0;
  unsigned char* o = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
  unsigned char* s = o ? *(unsigned char**)(o + 0x78) : 0;
  if (!s) return 0;
  unsigned char* best = 0; unsigned brows = 0, byear = 0;
  for (unsigned h = 0; h < nh; h++)
    for (int k = 0; k < 2; k++) {
      unsigned char* slot = s + h * 0xb4 + 4 + k * 0x58;
      if (*(uint32_t*)slot == 0xffffffffu || *(uint16_t*)(slot + 4) == 0xffff) continue;
      for (int i = 0; i < 20; i++) {
        int32_t ix = *(int32_t*)(slot + 8 + 4 * i);
        if (ix == -1) break;
        if (ix < 0 || (unsigned)ix >= nt) continue;
        unsigned char* e = s + arr + (size_t)ix * 0x187c;
        if (*(uint16_t*)e != reg) continue;
        unsigned rows = *(uint32_t*)(e + 0x318 + 0x3c0);
        unsigned yr = *(uint16_t*)(e + 2);
        /* the latest season of those, then the most rows: two full seasons of one id were both
           36 rows and the first found, maybe the older, won (B169) */
        if (rows >= lo && rows <= hi && (yr > byear || (yr == byear && rows > brows))
            && (!want || table_of_clubs(e + 0x318, rows, want, nwant))) {
          best = e + 0x318; brows = rows; byear = yr;
        }
      }
    }
  if (year_out) *year_out = byear;
  return best;
}
static unsigned char* season_table(uint16_t reg, unsigned* year_out)
{
  return season_table_x(reg, 24, 48, 0, 0, year_out);
}
/* the league phase's table: the game's, or, when that is short, the one season_table finds */
static unsigned char* lp_table(uint16_t row)
{
  unsigned char* t = ((table_fn)(uintptr_t)(g_base + TABLE_RVA))(row);
  uint32_t rows = t ? *(uint32_t*)(t + 0x3c0) : 0;
  if (rows >= 24 && rows <= 48) return t;
  unsigned yr = 0;
  unsigned char* t2 = season_table(row, &yr);
  if (!t2) return t;
  static uint16_t said[4]; int k = row == 1027 ? 0 : row == 1029 ? 1 : row == UECL_ROW ? 2 : 3;
  if (said[k] != (uint16_t)yr) {
    said[k] = (uint16_t)yr;
    logf("fl26swiss: reg %u -- the latest season's table has %u rows; season %u's table (%u rows) is used",
         (unsigned)row, rows, yr, *(uint32_t*)(t2 + 0x3c0));
  }
  return t2;
}
/* ---- a cup's top scorers across its stages (B114, Micarodvzla 17.10.) ----
 *
 * Every stage of a competition has a table of its own in the pool, and each keeps its own goal
 * and assist lists: +0xad8 and +0xe04, 40 rows of 0x14 {u32, u32 player, u32 club, u32 rank,
 * u32 tally}, the count at +0x320 (cap 40 at +0x324). The Goal Ranking shows the stage running
 * now, so when fl26swiss started the February play-off and the March round of 16 the list was
 * empty again: on 16/3 the Europa League showed 2 goals at the top, while the league phase's
 * list (reg 5) held 7. Run on 22.10. over 17-21/3: the round of 16's goals went to reg 4 and
 * 6 alone. So when fl26swiss starts the next stage, the list of the stage before is its start:
 * tallies by player, sorted, ranked (1 + the players with more), the first 40 kept. */
#define LB_GOALS   0xad8
#define LB_ASSISTS 0xe04
#define LB_ROWS    40
/* the latest stage table of reg a season's slot holds: of `most` or before, any when most is 0 */
static unsigned char* stage_table(uint16_t reg, unsigned most, unsigned* year_out)
{
  uint32_t arr; unsigned nh, nt;
  if (!pool_layout(&arr, &nh, &nt)) return 0;
  unsigned char* o = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
  unsigned char* s = o ? *(unsigned char**)(o + 0x78) : 0;
  if (!s) return 0;
  unsigned char* best = 0; unsigned byear = 0;
  for (unsigned h = 0; h < nh; h++)
    for (int k = 0; k < 2; k++) {
      unsigned char* slot = s + h * 0xb4 + 4 + k * 0x58;
      if (*(uint32_t*)slot == 0xffffffffu || *(uint16_t*)(slot + 4) == 0xffff) continue;
      for (int i = 0; i < 20; i++) {
        int32_t ix = *(int32_t*)(slot + 8 + 4 * i);
        if (ix == -1) break;
        if (ix < 0 || (unsigned)ix >= nt) continue;
        unsigned char* e = s + arr + (size_t)ix * 0x187c;
        unsigned yr = *(uint16_t*)(e + 2);
        if (*(uint16_t*)e != reg || yr == 0xffff || (most && yr > most)) continue;
        if (!best || yr > byear) { best = e; byear = yr; }
      }
    }
  if (year_out) *year_out = byear;
  return best;
}
typedef struct { uint32_t a, player, club, rank, n; } lb_row_t;
/* src's list added into dst's: the rows dst ends with */
static unsigned lb_add(unsigned char* dst, const unsigned char* src)
{
  lb_row_t all[2 * LB_ROWS];
  unsigned nd = *(uint32_t*)(dst + 0x320), ns = *(const uint32_t*)(src + 0x320), n = 0;
  if (nd > LB_ROWS) nd = LB_ROWS;
  if (ns > LB_ROWS) ns = LB_ROWS;
  memcpy(all, dst, nd * sizeof(lb_row_t));
  n = nd;
  for (unsigned i = 0; i < ns; i++) {
    lb_row_t r; memcpy(&r, src + i * sizeof(lb_row_t), sizeof r);
    unsigned j = 0;
    while (j < n && all[j].player != r.player) j++;
    if (j < n) all[j].n += r.n;
    else all[n++] = r;
  }
  for (unsigned i = 1; i < n; i++) {                /* stable: of equal tallies dst's come first */
    lb_row_t r = all[i]; unsigned j = i;
    while (j && all[j - 1].n < r.n) { all[j] = all[j - 1]; j--; }
    all[j] = r;
  }
  if (n > LB_ROWS) n = LB_ROWS;
  for (unsigned i = 0; i < n; i++) all[i].rank = i && all[i].n == all[i - 1].n ? all[i - 1].rank : i + 1;
  memcpy(dst, all, n * sizeof(lb_row_t));
  *(uint32_t*)(dst + 0x320) = n;
  return n;
}
/* right after the start of stage `to`: its lists become those of stage `from` (the stage before it
   in the same season, or the season before when `to` opened a new year). They are set, not added
   to: no match of the new stage has been played yet, and a February play-off that joins the
   running season (po_start) finds the table of August's qualifying play-off, goals and all. */
static void lb_carry(const char* name, uint16_t from, uint16_t to)
{
  unsigned yt = 0, yf = 0;
  unsigned char* t = stage_table(to, 0, &yt);
  unsigned char* f = t ? stage_table(from, yt, &yf) : 0;
  if (!t || !f || yt - yf > 1) {
    logf("fl26swiss: %s scorers -- reg %u's table %s (season %u), reg %u's %s (season %u); nothing carried",
         name, (unsigned)to, t ? "found" : "not found", yt, (unsigned)from, f ? "found" : "not found", yf);
    return;
  }
  *(uint32_t*)(t + LB_GOALS + 0x320) = 0;
  *(uint32_t*)(t + LB_ASSISTS + 0x320) = 0;
  unsigned g = lb_add(t + LB_GOALS, f + LB_GOALS), a = lb_add(t + LB_ASSISTS, f + LB_ASSISTS);
  logf("fl26swiss: %s scorers carried from reg %u (season %u) into reg %u (season %u): %u goal rows, %u assist rows",
       name, (unsigned)from, yf, (unsigned)to, yt, g, a);
}
static uint16_t ko_row(uint16_t id)
{
  if (g_native_uefa && (id == 4 || id == 6)) return 0xffff;   /* FL27 fills its knockout of 24 itself */
  return id == 4 ? 1027 : id == 6 ? 1029 : id == UECL_KO ? UECL_ROW : 0xffff;
}
/* list positions -> table ranks (0-based).  If the knockout pairs neighbours, the ties are
   1-16, 8-9, 4-13, 5-12, 2-15, 7-10, 3-14, 6-11: the seeded half meets the unseeded half. */
static const int KO_ORDER[KO_N] = { 0, 15, 7, 8, 3, 12, 4, 11, 1, 14, 6, 9, 2, 13, 5, 10 };

static int cwc_world(void);
static char cwc_setcl(uint64_t id, u32vec* list, uint64_t flag);
static u32vec* cwc_game_champions(u32vec* list);
static char cwc_handoff(uint64_t id, u32vec* list, uint64_t flag);
static void champ_note(const char* when);
static int champ_cups(uint16_t* reg, int max);
static void cont_note(uint16_t id, void* vec);
static uint32_t canon_club(uint32_t h);
static const char* club_note(uint32_t h, char* buf, size_t cap);
typedef struct split_s split_t;
static int split_part(uint16_t id, const split_t** out);
static int q_setcl(uint16_t r, uint64_t id, uint64_t flag, char* ok);
static void split_regular_clubs(uint16_t r, const split_t* s, u32vec* list);
#define RIGHT_RVA 0x15799e0   /* u32* (u32* out, u16 source, u32 right_type): 0 = winner, 13+n = position n+1 */
#define NOCLUB_RVA 0x351ae44  /* what it answers when nobody holds the right */
typedef uint32_t* (*right_fn)(uint32_t* out, uint64_t source, uint32_t type);

#define MAX_CAL_SCUPS 512   /* 32 until the limits branch: one super cup per country, ~150 countries */
typedef struct { uint16_t reg, league, cup; } cal_scup_t;
static cal_scup_t g_cal_scup[MAX_CAL_SCUPS];
static int g_ncal_scup = 0;

static const cal_scup_t* calendar_scup(uint16_t reg)
{
  for (int i = 0; i < g_ncal_scup; i++)
    if (g_cal_scup[i].reg == reg) return &g_cal_scup[i];
  return 0;
}

static uint32_t calendar_scup_right(uint16_t source, uint32_t type)
{
  uint32_t c = 0;
  ((right_fn)(uintptr_t)(g_base + RIGHT_RVA))(&c, source, type);
  if (c == *(uint32_t*)(g_base + NOCLUB_RVA) || !(c >> 14)) return 0;
  return c;
}

__declspec(dllexport) int fl26_swiss_calendar_supercups(const uint16_t* v, int n)
{
  if ((!v && n) || n < 0) return -1;
  int k = 0;
  for (int i = 0; i < n && k < MAX_CAL_SCUPS; i++) {
    uint16_t reg = v[3 * i], league = v[3 * i + 1], cup = v[3 * i + 2];
    if (!reg || !league || !cup) continue;
    int dup = 0;
    for (int j = 0; j < k; j++) if (g_cal_scup[j].reg == reg) dup = 1;
    if (dup) continue;
    g_cal_scup[k].reg = reg;
    g_cal_scup[k].league = league;
    g_cal_scup[k].cup = cup;
    k++;
  }
  g_ncal_scup = k;
  logf("fl26swiss: %d calendar-year Super Cup(s) configured", k);
  return k;
}

/* B234: the super cup of an added August-May league. The July builder now lets it into the
 * season (fl26join), but nothing in the game fills it: run 4 of 2026-10-26 had all six entered
 * and dated on day 227, and the Albanian one still "has not been decided" on day 242. Same
 * pair as a calendar-year one -- champion v cup winner, the runner-up when they are one club --
 * and a league with no cup of its own gives its runner-up. cup is 0 then. */
static cal_scup_t g_aug_scup[MAX_CAL_SCUPS];
static int g_naug_scup = 0;

__declspec(dllexport) int fl26_swiss_aug_supercups(const uint16_t* v, int n)
{
  if ((!v && n) || n < 0) return -1;
  int k = 0;
  for (int i = 0; i < n && k < MAX_CAL_SCUPS; i++) {
    uint16_t reg = v[3 * i], league = v[3 * i + 1], cup = v[3 * i + 2];
    if (!reg || !league) continue;
    int dup = 0;
    for (int j = 0; j < k; j++) if (g_aug_scup[j].reg == reg) dup = 1;
    if (dup) continue;
    g_aug_scup[k].reg = reg;
    g_aug_scup[k].league = league;
    g_aug_scup[k].cup = cup;
    k++;
  }
  g_naug_scup = k;
  logf("fl26swiss: %d August-May Super Cup(s) of added leagues configured", k);
  return k;
}

char setcl_handler(uint64_t id, u32vec* list, uint64_t flag)
{
  uint16_t r = (uint16_t)id, row = ko_row(r);
  const cal_scup_t* cs = calendar_scup(r);
  if (cs && list && list->b && list->e >= list->b && list->e - list->b == 2) {
    uint32_t champion = calendar_scup_right(cs->league, 13);
    uint32_t runner   = calendar_scup_right(cs->league, 14);
    uint32_t cupwin   = calendar_scup_right(cs->cup, 0);

    if (champion && cupwin) {
      uint32_t opponent =
        ((champion >> 14) == (cupwin >> 14)) ? runner : cupwin;

      if (opponent && (opponent >> 14) != (champion >> 14)) {
        uint32_t clubs[2] = { champion, opponent };
        u32vec fixed = { clubs, clubs + 2, clubs + 2 };
        logf("fl26swiss: calendar Super Cup %u -- league %u champion %u v %s %u",
             (unsigned)cs->reg, (unsigned)cs->league, champion >> 14,
             (champion >> 14) == (cupwin >> 14) ? "league runner-up" : "cup winner",
             opponent >> 14);
        return ((setclr_fn)(uintptr_t)g_tramp_setcl)(id, &fixed, flag);
      }
    }
  }
  /* Before F3 is real, native reg 9 can contain an Other-LATAM club that is
     reserved for our F1/F2 path. Keep that provisional filler out of groups. */
  if (r == 9 && list && list->b && list->e > list->b) lib9_clean(list);
  if (r == 1 && cwc_world()) return cwc_handoff(id, list, flag);
  if (r == 1 && list && list->b && list->e > list->b) list = cwc_game_champions(list);
  if (is_playoff(r)) { char ok; if (q_setcl(r, id, flag, &ok)) return ok; }
  /* A group of one of our splits is handed the regular phase's table rows by 0x141343d70, which
     starts it straight after (0x141343af0: set_clubs, then 0x141590420): the values are put
     right here, before its matches are made from them (see canon_club). */
  const split_t* sp;
  if (r > 175 && list && list->b && list->e > list->b && split_part(r, &sp) == 2)
    split_regular_clubs(r, sp, list);
  if (r > 175 && list && list->b && list->e > list->b && split_part(r, &sp) >= 2) {
    int bad = 0; uint32_t was = 0, now = 0;
    for (uint32_t* p = list->b; p < list->e; p++) {
      uint32_t c = canon_club(*p);
      if (c == *p) continue;
      if (!bad++) { was = *p; now = c; }
      *p = c;
    }
    char note[48];
    if (bad)
      logf("fl26swiss: set_clubs reg %u -- %d of %u club(s) did not name their team record (%08x: %s -> %08x); rewritten",
           (unsigned)r, bad, (unsigned)(list->e - list->b), was, club_note(was, note, sizeof note), now);
    else
      logf("fl26swiss: set_clubs reg %u -- %u club(s) on day %d, all name their team record (%08x ...)",
           (unsigned)r, (unsigned)(list->e - list->b), today(), list->b[0]);
  }
  if (r == 10 || r == 16 || cont_comp(r) >= 0) {
    logf("fl26swiss: set_clubs reg %u -- %u club(s) on day %d, from %llx", (unsigned)r,
         (unsigned)(list && list->b ? list->e - list->b : 0), today(),
         (unsigned long long)((uintptr_t)__builtin_return_address(0) - g_base + 0x140000000ull));
    cont_swap(r, list, "set_clubs");
    if (r == 9 && list && list->b && list->e > list->b) lib9_holders(list);
  }
  size_t n = list && list->b ? (size_t)(list->e - list->b) : 0;
  if (r == 53 || r == 123)            /* GitHub #21: who fills the DFB-Pokal / Russian Cup, and with what */
    logf("fl26swiss: set_clubs cup reg %u -- %u club(s) on day %d, from %llx, first %08x last %08x", (unsigned)r,
         (unsigned)n, today(), (unsigned long long)((uintptr_t)__builtin_return_address(0) - g_base + 0x140000000ull),
         n ? list->b[0] : 0, n ? list->b[n - 1] : 0);
  if (row != 0xffff && n) {
    unsigned char* ph = get_rec(row);
    unsigned char* t = ph && rec_count(ph) >= FL26_SWISS_MIN_CLUBS ? lp_table(row) : 0;
    uint32_t rows = t ? *(uint32_t*)(t + 0x3c0) : 0;
    if (rows >= KO_N && rows <= 48) {
      static uint32_t buf[KO_N];
      for (int i = 0; i < KO_N; i++) buf[i] = *(uint32_t*)(t + KO_ORDER[i] * 20);
      u32vec v = { buf, buf + KO_N, buf + KO_N };
      logf("fl26swiss: reg %u -- the game offered %u club(s); giving it the top %d of reg %u's table of %u",
           (unsigned)r, (unsigned)n, KO_N, (unsigned)row, (unsigned)rows);
      for (int i = 0; i < 4; i++) {
        const uint32_t* a = (const uint32_t*)(t + i * 20);
        logf("fl26swiss:   rank %d row %08x %08x %08x %08x %08x", i + 1, a[0], a[1], a[2], a[3], a[4]);
      }
      const uint32_t* z = (const uint32_t*)(t + (KO_N - 1) * 20);
      logf("fl26swiss:   rank %d row %08x %08x %08x %08x %08x", KO_N, z[0], z[1], z[2], z[3], z[4]);
      char ok = ((setclr_fn)(uintptr_t)g_tramp_setcl)(id, &v, flag);
      run_flush();
      return ok;
    }
    logf("fl26swiss: reg %u -- %u club(s) offered, but reg %u has no table of %d (rows %u); left to the game",
         (unsigned)r, (unsigned)n, (unsigned)row, FIELD, (unsigned)rows);
  }
  return ((setclr_fn)(uintptr_t)g_tramp_setcl)(id, list, flag);
}

/* The Conference League's two hand-overs.  Nothing in the exe knows competition 174: the stage
 * progression 0x141345cc0 switches on the regulation id (cases 2..0xaf, jump table at
 * 0x141345f74), so 186 falls to the default and does nothing, and no builder gives it entrants.
 * Both steps are done here, around the progression, the way the shipped cases do them:
 *
 *   - when the Champions League play-off (reg 2) has finished, the original case has just filled
 *     reg 3 and reg 5 (0x141344920).  The Conference League gets the Europa League's direct
 *     entrants that were cut to make 36, then its own entries (its regulation's clubs, or the
 *     list the loader passed in), minus anyone already in the Champions League or Europa League;
 *     set_clubs(186), group draw(186) (the draw hook above hands row 1210 the whole list),
 *     push 186 onto the caller's list of started stages, 0x141590420(186) -- the same four
 *     steps as 0x1413449b4..0x1413449f7 do for reg 3.
 *   - when 186 itself finishes, set_clubs(187) (the knockout hook above turns that into the top
 *     16 of 1210's table), push 187, 0x141590420(187) -- the generic case 0x141345d8d.
 *
 * The caller 0x141348210 hands the list of started stages to 0x141343bf0 only when the
 * progression answers 1, so the answer is 1 whenever a stage was started here. */
#define PROG_RVA   0x1345cc0
#define PUSH16_RVA 0x0cc7f20
#define START_RVA  0x1590420
static const unsigned char SIG_PROG[15] = {
  0x48,0x8b,0xc4, 0x55, 0x41,0x56, 0x41,0x57, 0x48,0x8b,0xec, 0x48,0x83,0xec,0x60 };
typedef char (*prog_fn)(void* ctx, uint64_t id, void* started);
typedef void (*push16_fn)(void* vec, const uint16_t* v);
typedef char (*start_fn)(uint64_t id);
unsigned char* g_tramp_prog = 0;
static uint32_t g_uecl_list[48]; static unsigned g_uecl_n = 0;   /* from the loader */
static unsigned char g_prog_seen[1024];

static char start_stage(void* started, uint16_t id)
{
  if (started) ((push16_fn)(uintptr_t)(g_base + PUSH16_RVA))(started, &id);
  char ok = ((start_fn)(uintptr_t)(g_base + START_RVA))(id);
  logf("fl26swiss: reg %u started (0x141590420 -> %d)", (unsigned)id, (int)ok);
  return ok;
}

/* A club in a regulation's list is not the team id: it is the club's slot in the team array in
 * bits 0-13 and the team id from bit 14 up (England's list reads 0x194014 = slot 20, team 101).
 * Bare team ids from the loader's list were entered as they were on 24 September, read as slots,
 * and every Conference League match of those clubs was scored as a 3-0 walkover.  So each team id
 * is looked up in the club lists of the domestic leagues, which the game wrote itself, and taken
 * in that form.  0x1414bc860(blk, id) is the lookup that
 * answers NULL for an id that does not exist. */
#define FINDREC_RVA 0x14bc860
typedef void* (*findrec_fn)(void* blk, uint64_t id);
static uint32_t club_of_id(uint32_t c);
/* Both callers hand over bare team ids from the world file. This used to take anything of
   16384 and up as a list value already; our clubs' ids run from 65536, so a pre-season cup
   of four new clubs got the first id back as a value (team 4) and turned the other three
   away as the same club (2026-09-29: "cup 206 -- only 1 of 4 clubs found"). */
static uint32_t full_club(uint32_t c)
{
  return club_of_id(c);
}
/* a team id (any size: our clubs run past 65536) as the leagues hold it, or 0 */
static uint32_t club_of_id(uint32_t c)
{
  unsigned char* o = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
  void* blk = o ? *(void**)(o + 0x48) : 0;
  if (!blk) return 0;
  for (unsigned id = 1; id < lay_regcap(); id++) {
    unsigned char* r = (unsigned char*)((findrec_fn)(uintptr_t)(g_base + FINDREC_RVA))(blk, id);
    if (!r) continue;
    unsigned n = rec_count(r); if (n > 48) n = 48;
    for (unsigned i = 0; i < n; i++) {
      uint32_t v = rec_clubs(r)[i];
      if ((v >> 14) == c) return v;
    }
  }
  return 0;
}

/* ---- a club's value as its own team record holds it ----
 *
 * GitHub #37 (Venezuela, Apertura/Clausura) and Alikhaled's Egyptian split, both 0.1.3: every
 * row of a phase table and every club of its playoff carried its own badge but ONE name
 * (Almirante Brown, a club of the other split in #37; Zamalek, the user's club, in Egypt); a
 * match of two of them asked for two controllers, and the phases were never played. The badge goes by the team id (the value's upper 18 bits);
 * the name, the squad and who controls the side come from the team record, and the game's
 * lookup 0x1414bb580 takes that record by the lower 14 bits alone when blk+0x183789c is 2
 * (team array[row], no check of the id; otherwise it searches for the whole value). A value
 * whose row is not its club's place in the array then reads another club's record -- the one
 * explanation found for one name over many badges, not yet confirmed by a live read (the
 * check_reg lines below are that read). The game's own clubs carry their
 * place (0x194014: team 101 at row 20); the phases' values of our new clubs read row 0
 * (45f8c000 ..., measured 2026-09-29 on a playoff fill).
 *
 * canon_club gives such a value the row of the one team record that holds the same id AND
 * sits at its own row; a value that already names its record, or an id no single record
 * answers for, is returned as it is -- so a list the game reads right is never changed. The
 * array's place, count and stride are read off 0x1414bb580 itself (mov eax, [rbx+count];
 * lea rdx, [rbx+base]; imul rcx, rax, 0x690), which the runtime patch set moves with the
 * array. */
#define TEAMLOOK_SITE 0x14bb5fa
#define TEAM_STRIDE   0x690
#ifdef FL26_RCAL_TEST
static unsigned char* g_test_teams;   /* a harness's own team array (test_state_keep), else none */
static uint32_t g_test_nteams;
#endif
static unsigned char* team_array(uint32_t* n)
{
#ifdef FL26_RCAL_TEST
  if (g_test_teams) { *n = g_test_nteams; return g_test_teams; }
  (void)n; return 0;          /* the native harnesses have no game: club values are not checked (B312) */
#endif
  const unsigned char* c = (const unsigned char*)(g_base + TEAMLOOK_SITE);
  static int said;
  if (c[0] != 0x8b || c[1] != 0x83 || c[6] != 0x48 || c[7] != 0x8d || c[8] != 0x93
      || c[13] != 0x48 || c[14] != 0x69 || c[15] != 0xc8 || *(const uint32_t*)(c + 16) != TEAM_STRIDE) {
    if (!said++) logf("fl26swiss: the team lookup is not where it was (0x1414bb5fa); club values are not checked");
    return 0;
  }
  unsigned char* o = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
  unsigned char* blk = o ? *(unsigned char**)(o + 0x48) : 0;
  if (!blk) return 0;
  *n = *(const uint32_t*)(blk + *(const int32_t*)(c + 2));
  if (!*n || *n > 0x3fff) return 0;
  return blk + *(const int32_t*)(c + 9);
}
static uint32_t team_at(const unsigned char* a, uint32_t i) { return *(const uint32_t*)(a + (size_t)i * TEAM_STRIDE); }
static uint32_t canon_club(uint32_t h)
{
  uint32_t n, row = h & 0x3fff, got = 0;
  unsigned char* a;
  if (!(h >> 14) || !(a = team_array(&n))) return h;
  if (row < n && team_at(a, row) == h) return h;
  int hits = 0;
  for (uint32_t i = 0; i < n; i++) {
    uint32_t v = team_at(a, i);
    if ((v >> 14) == (h >> 14) && (v & 0x3fff) == i) { got = v; hits++; }
  }
  return hits == 1 ? got : h;
}
/* B312 (03.11., FL27 Europack, new career with Anderlecht, 4 of 4): the Champions League's second
 * qualifying round put Azerbaijan's champion in as 043982e5 -- team 4326 at row 741, the value the
 * league's list and the first season's order (fl26swiss-state.bin) held. By August row 741 was
 * Qabala's (468802e5) and 4326 sat at row 742: the game's own league matches had 043982e6. The
 * match simulation looks a side up by its row alone (0x1414bca80, blk+0x183789c 2) and checks the
 * id; the home side came back empty, its eleven list stayed empty, and the first goal of the away
 * side was given to no player: 0x141333485 read 0x8 (the B181/B308 address). A list of ours is put
 * through canon_club just before it is handed to the game, and each value it changes is logged. */
static int canon_list(uint32_t* a, unsigned n, const char* what, unsigned reg)
{
  int fixed = 0;
  for (unsigned i = 0; i < n; i++) {
    uint32_t c = canon_club(a[i]);
    if (c == a[i]) continue;
    char buf[48];
    logf("fl26swiss: %s %u -- club %u: %08x -> %08x (%s)", what, reg, i, a[i], c, club_note(a[i], buf, sizeof buf));
    a[i] = c; fixed++;
  }
  return fixed;
}
/* what the value's row holds, for the log: "ok" when it is the value itself */
static const char* club_note(uint32_t h, char* buf, size_t cap)
{
  uint32_t n, row = h & 0x3fff;
  unsigned char* a = team_array(&n);
  if (!a) snprintf(buf, cap, "?");
  else if (row >= n) snprintf(buf, cap, "row %u past %u", row, n);
  else if (team_at(a, row) == h) snprintf(buf, cap, "ok");
  else snprintf(buf, cap, "row %u holds %08x", row, team_at(a, row));
  return buf;
}
/* For the log: whether a regulation's clubs (its list, and its table's rows when it has one)
 * name their team records. Nothing is changed: a phase already scheduled keeps the values its
 * matches were made with, or its table would no longer find their results. */
static int check_reg(uint16_t reg, const char* when)
{
  unsigned char* rec = get_rec(reg);
  if (!rec) return 0;
  uint32_t* l = rec_clubs(rec);
  unsigned n = rec_count(rec);
  if (!n) while (n < 48 && l[n] != 0xffffffffu) n++;
  if (n > 48) n = 48;
  int bad = 0, tbad = 0;
  uint32_t was = 0, now = 0;
  for (unsigned i = 0; i < n; i++) {
    uint32_t c = canon_club(l[i]);
    if (c == l[i]) continue;
    if (!bad++) { was = l[i]; now = c; }
  }
  unsigned char* t = ((table_fn)(uintptr_t)(g_base + TABLE_RVA))(reg);
  uint32_t rows = t ? *(uint32_t*)(t + 0x3c0) : 0;
  if (rows > 48) rows = 0;
  for (uint32_t i = 0; i < rows; i++) {
    uint32_t* p = (uint32_t*)(t + (size_t)i * 20);
    uint32_t c = canon_club(*p);
    if (c == *p) continue;
    if (!bad && !tbad) { was = *p; now = c; }
    tbad++;
  }
  char note[48];
  if (bad || tbad)
    logf("fl26swiss: reg %u -- %s: %d of %u listed club(s) and %d of %u table row(s) do not name their team record "
         "(%08x: %s, would be %08x)", (unsigned)reg, when, bad, n, tbad, (unsigned)rows, was,
         club_note(was, note, sizeof note), now);
  else if (n)
    logf("fl26swiss: reg %u -- %s: %u listed club(s), %u table row(s), all name their team record (%08x ...)",
         (unsigned)reg, when, n, (unsigned)rows, l[0]);
  return bad + tbad;
}

static int in_rec(uint16_t id, uint32_t c)
{
  unsigned char* r = get_rec(id);
  return r && has_club(rec_clubs(r), rec_count(r), c);
}

static uint32_t g_acc[3][FIELD]; static unsigned g_nacc[3];
static int g_access_on;
static int abs_day(void);
static int uecl_fill(void* started)
{
  unsigned char* rec = get_rec(UECL_REG);
  if (!rec || !get_rec(UECL_ROW)) { logf("fl26swiss: no Conference League in this world (reg %u)", UECL_REG); return 0; }
  /* B118: the July teardown takes the row out of its season (+0x2fc 0xffff) but leaves last
     season's 36 clubs in it, and "any club = filled" then never filled it again: r12, fourth
     season (2026-10-21), "row 1210 already holds 36 clubs" on the draw day, so the Conference
     League never started and its table stayed empty (Micarodvzla, 17.10.). Filled means filled
     this season: the row in a season, or filled already this season. Anything else is filled
     anew, its old clubs emptied first. */
  static int filled_year = -1;
  int year = (abs_day() + 183) / 365;
  unsigned char* row0 = get_rec(UECL_ROW);
  if (rec_count(row0)) {
    int live = *(const uint16_t*)(row0 + 0x2fc) != 0xffff;
    if (live || filled_year == year) {
      logf("fl26swiss: row %u already holds %u clubs%s; Conference League not filled again", UECL_ROW,
           rec_count(row0), live ? " in this season" : " (filled once this season)");
      return 0;
    }
    logf("fl26swiss: row %u still holds %u club(s) of an earlier season and is in no season -- filled anew",
         UECL_ROW, rec_count(row0));
    static uint32_t none[1];
    u32vec e = { none, none, none };
    ((setcl_fn)(uintptr_t)(g_base + SETCL_RVA))(UECL_ROW, &e, 1);
    run_flush();
  }
  filled_year = year;
  static uint32_t buf[48]; unsigned n = 0, own = 0, spill = 0, loader = 0;
  uint32_t cand[160]; unsigned nc = 0;
  if (g_access_on && g_nacc[2] == FIELD) {       /* the access list decided it */
    for (unsigned i = 0; i < FIELD; i++) cand[nc++] = g_acc[2][i];
    own = nc;
    goto pick;
  }
  for (unsigned i = 0; i < g_nspill && nc < 160; i++) cand[nc++] = g_spill[i];
  spill = nc;
  unsigned rn = rec_count(rec);
  uint32_t mine[48]; for (unsigned i = 0; i < rn && i < 48; i++) mine[i] = rec_clubs(rec)[i];
  for (unsigned i = 0; i < rn && i < 48 && nc < 160; i++) cand[nc++] = mine[i];
  own = nc - spill;
  unsigned unresolved = 0;
  for (unsigned i = 0; i < g_uecl_n && nc < 160; i++) {
    uint32_t v = full_club(g_uecl_list[i]);
    if (v) cand[nc++] = v; else unresolved++;
  }
  loader = nc - spill - own;
  if (unresolved) logf("fl26swiss: reg %u -- %u club(s) of the loader's list are in no league list; left out", UECL_REG, unresolved);
pick:
  for (unsigned i = 0; i < nc && n < FIELD; i++) {
    uint32_t c = cand[i];
    if (!(c >> 14) || has_club(buf, n, c)) continue;
    if (in_rec(3, c) || in_rec(1027, c) || in_rec(5, c) || in_rec(1029, c)) continue;
    buf[n++] = c;
  }
  logf("fl26swiss: reg %u -- Conference League field %u (candidates: %u cut from the Europa League, %u own, %u from the loader)",
       UECL_REG, n, spill, own, loader);
  if (n < FL26_SWISS_MIN_CLUBS) { logf("fl26swiss: reg %u -- field too short, not started", UECL_REG); return 0; }
  u32vec v = { buf, buf + n, buf + n };
  ((setcl_fn)(uintptr_t)(g_base + SETCL_RVA))(UECL_REG, &v, 1);
  ((gdraw_fn)(uintptr_t)(g_base + GDRAW_RVA))(UECL_REG, &v, 1);
  run_flush();
  unsigned char* row = get_rec(UECL_ROW);
  logf("fl26swiss: reg %u now %u clubs, row %u %u", UECL_REG, rec_count(rec), UECL_ROW, row ? rec_count(row) : 0);
  start_stage(started, UECL_REG);
  return 1;
}

#define FREETAB_RVA 0x1363040   /* (this, u16 id): free a regulation's tie tables -- the July teardown's own step */
typedef char (*freetab_fn)(void* self, uint64_t id);
static int uecl_ko(void* started)
{
  unsigned char* ko = get_rec(UECL_KO);
  if (!ko) return 0;
  /* B181: last season's sixteen stay in the list through the July teardown (as row 1210's do, B118),
     and with them its rounds: filled anew once a season when it is in no season, its rounds freed
     first, as the teardown frees the game's own */
  static int filled_year = -1;
  int year = (abs_day() + 183) / 365;
  if (rec_count(ko)) {
    if (*(const uint16_t*)(ko + 0x2fc) != 0xffff || filled_year == year) return 0;
    logf("fl26swiss: reg %u still holds %u club(s) of an earlier season and is in no season -- filled anew",
         UECL_KO, rec_count(ko));
  }
  filled_year = year;
  ((freetab_fn)(uintptr_t)(g_base + FREETAB_RVA))(0, UECL_KO);
  uint32_t one = 1; u32vec v = { &one, &one + 1, &one + 1 };   /* replaced by the knockout hook */
  ((setcl_fn)(uintptr_t)(g_base + SETCL_RVA))(UECL_KO, &v, 1);
  run_flush();
  logf("fl26swiss: reg %u now %u clubs", UECL_KO, rec_count(ko));
  if (!rec_count(ko)) return 0;
  start_stage(started, UECL_KO);
  return 1;
}

/* The Champions League knockout play-off, ranks 9-24, in the shipped play-off regulation.
 *
 * Regulation 2 is the August qualifying play-off: eight ties, one replica each (1026, 2050 ...
 * 8194).  By February it has long finished, so it is used a second time.  When the league phase
 * (reg 3) ends, the progression's own case would put two clubs into reg 4; instead:
 *   - the ties follow UEFA's fixed bracket: 9/10 meet 23/24 (ties 0-1, bracket I), 11/12 meet
 *     21/22 (II), 13/14 meet 19/20 (III), 15/16 meet 17/18 (IV), who meets whom inside a bracket
 *     is drawn.  Replica k gets tie k, reg 2 gets all sixteen, and reg 2 is started -- its two
 *     legs dated on PO_DAYS by the date hook.  The seeded club is listed second, so it is at
 *     home in the second leg;
 *   - when reg 2 ends, the progression's case 2 would rebuild the league phases from scratch
 *     (0x141344920).  Instead, the winner of each tie (0x14151b2e0(&club, replica), the same read
 *     0x141346030 makes) is paired with the top eight the UEFA way: 1/2 draw the two winners of
 *     bracket IV, 3/4 those of III, 5/6 of II, 7/8 of I.  The round of 16 is listed so that the
 *     game's neighbour pairing builds the real tree: quarter-finals 1/2 v 7/8 and 3/4 v 5/6, the
 *     two halves each holding one club of every seed pair (which half is drawn).  Seeded clubs
 *     are listed second again, and reg 4 is filled and started with that list.
 * Which of the two uses of reg 2 is meant is read from the game's own day counter, not kept in
 * the DLL, so a save loaded in the middle of the play-off still goes the right way: August
 * starts on day 212, the play-off is in February. */
/* the day counter: 0x19115e4 under the 0.3.0 set, elsewhere under a set that moves the calendar
   (the limits set of FL27); read from the game's own movzx at 0x140aed7b0 (fl26layout.h) */
#define TODAY_OFF  lay_today()
#define WINNER_RVA 0x151b2e0
#define PO_MONTHS_BEFORE 180                 /* any day below this is the second half of a season */
typedef void* (*winner_fn)(uint32_t* out, uint64_t id);
static int g_po_enabled = 1;
#ifdef FL26_RCAL_TEST
int rcal_test_today(void);
#endif
static int today(void)
{
#ifdef FL26_RCAL_TEST
  return rcal_test_today();
#endif
  unsigned char* o = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
  unsigned char* blk = o ? *(unsigned char**)(o + 0x48) : 0;
  if (!blk) return -1;
  /* 17.11. (League Mode, LG00000013): out of a career -- quit to the menu, a save being loaded --
     the block is still there with a day but no year in it. That day (0) was taken for a New
     Year, the save's day 222 that came next for "a save of the year before", and the load was
     never seen as another timeline: the summer was taken as already done, and the qualifying
     rounds and the league phases were never filled. No year is no career (fl26cwc's rule). */
  int d = *(uint16_t*)(blk + TODAY_OFF), y = *(uint16_t*)(blk + TODAY_OFF + 8);
  return d > 365 || y < 1990 || y > 2200 ? -1 : d;
}
static int po_season_half(void) { int d = today(); return d >= 0 && d < PO_MONTHS_BEFORE; }
/* The game's day counter is the day of the calendar year, so a guard that keeps "the day it last
 * happened" and asks "was that less than N days ago" gives the wrong answer a year later, in the
 * same game session: it is the same day again. Issue #10: in seasons 2 and 3 played on without a
 * restart the play-offs were taken as already drawn and nothing was drawn at all; a restart
 * cleared the memory, which is why a replay "worked". abs_day() counts on across New Year (a drop
 * of more than half a year is a new year; a jump forward of as much is a save of the year before
 * loaded) and every such guard compares it instead of the raw day. */
/* A day counter that goes back otherwise than at New Year is another timeline: a second career
 * built in the same game session, or an older save loaded. It used to be taken for the same
 * season, so everything kept "for this season" -- a qualifying round filled, a play-off
 * started, a career built in this session -- stayed done for the next career (2026-10-08: the
 * second career of a session). Now it counts two years on, so no such guard matches any more,
 * and the new career is told apart again (g_new_career, g_day_ticked). */
static int g_year_off = 0, g_last_day = -1, g_timeline = 0;
static int g_new_career = 0, g_day_ticked = 0, g_first_day = -1;
/* B209: the game's date the career was built on, and whether the state file has it yet: a game
   quit between building a career and its first August draw forgot it was new, and the
   first-season list was left out (Jabo9, 23.10.) */
static int g_built_gdate = -1, g_built_stored = 0;
/* the game's date the user club's career was built on, by the state file, however long ago (-1:
   not known); afc_first_season */
static int g_built_any = -1;
static int abs_day(void)
{
  int d = today();
  if (d < 0) return d;
  if (g_last_day >= 0 && d < g_last_day) {
    if (d + 182 < g_last_day && g_last_day >= 300) g_year_off += 365;     /* New Year */
    else {
      logf("fl26swiss: day %d after day %d -- another timeline (a save loaded or another career)", d, g_last_day);
      g_year_off += 730; g_timeline++;
      g_new_career = 0; g_day_ticked = 0; g_first_day = -1;
      g_built_gdate = -1; g_built_stored = 0;
    }
  }
  else if (g_last_day >= 0 && d > g_last_day + 182) {
    /* half a year forward at once is no day of play: a save loaded (of the year before, or after
       a day taken for a New Year). It used to be put back a year on the same timeline, and every
       guard kept for that season matched again (17.11.); another timeline, as a day gone back */
    logf("fl26swiss: day %d after day %d -- half a year forward: another timeline (a save loaded)", d, g_last_day);
    g_year_off += 730; g_timeline++;
    g_new_career = 0; g_day_ticked = 0; g_first_day = -1;
    g_built_gdate = -1; g_built_stored = 0;
  }
  g_last_day = d;
  return d + g_year_off;
}
/* B289 (30.10.): the first summer of a career ends on FIRST_SUMMER_END (late October, the
   league phases long drawn). A save loaded after it but within BUILT_SUMMER days of the build
   (a January career loaded in September) was taken for a new career again, and played on in
   the same session it put the first-season list into the next summer's league phases too. */
#define FIRST_SUMMER_END 300
static int game_date(void);
static int first_summer_over(void)
{
  int gn = game_date();
  if (gn < 0 || g_built_gdate < 0) return 0;
  /* a FIRST_SUMMER_END between the build and today: days since the last one < days since the build */
  return gn - g_built_gdate > (gn % 365 - FIRST_SUMMER_END + 365) % 365;
}
/* one key per season and timeline: what is logged once per regulation is logged again for the
   next season's calendars and for another career's */
static int log_season(void) { int a = abs_day(); return a < 0 ? -1 : (a + 184) / 365; }
#define SAID_RESET(n) do { static int sg_ = -1000; int sk_ = log_season(); if (sk_ != sg_) { sg_ = sk_; (n) = 0; } } while (0)

/* ---- the season's own weekdays (0.2.0) ----
 * The fixed European days and the real calendars were laid out on 2026's weekdays (day 0 a
 * Thursday). The first season is 2025/26, whose August to December is a weekday earlier: a
 * league round meant for a Friday was a Thursday (7 August 2025), the Champions League's
 * Tuesday a Monday. The year is the game date's low word (u16 year, month, day after the day
 * counter); days from 1 July (181) are the season's first year, the others its second. With no
 * year to read (a test without a game), the 2026 frame. Leap days are not counted: the game's
 * day counter has none. */
static const uint16_t MONTH0[13] = { 0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334, 365 };
static int g_test_year = 0;
static int g_sy_force = 0;      /* uefa_days_of: a calendar-year league's other season */
static int season_year(void)
{
  if (g_sy_force) return g_sy_force;
  if (g_test_year) return g_test_year;
  /* asked for every day of every calendar built: read again only when the clock has moved */
  static uint64_t at = 0; static int was = 0;
  uint64_t now = GetTickCount64();
  if (at && now - at < 50) return was;
  unsigned char* o = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
  unsigned char* blk = o ? *(unsigned char**)(o + 0x48) : 0;
  if (!blk) return was = 0;
  int t = *(uint16_t*)(blk + TODAY_OFF), y = *(uint16_t*)(blk + TODAY_OFF + 8);
  at = now;
  return was = t >= 365 || y < 1990 || y > 2200 ? 0 : t >= 175 ? y : y - 1;
}
static int dow(int y, int m, int dd)                 /* 0 Monday .. 6 Sunday */
{
  static const int T[12] = { 0, 3, 2, 5, 0, 3, 5, 1, 4, 6, 2, 4 };
  if (m < 3) y--;
  return ((y + y / 4 - y / 100 + y / 400 + T[m - 1] + dd) + 6) % 7;
}
static int wday_in(uint32_t d, int sy)
{
  if (!sy || d >= 365) return (int)((d + 3) % 7);
  int y = d >= 181 ? sy : sy + 1, m = 1;
  while (m < 12 && d >= MONTH0[m]) m++;
  return dow(y, m, (int)(d - MONTH0[m - 1]) + 1);
}
static int wday(uint32_t d) { return wday_in(d, season_year()); }
/* day d as the game shows it, "Fri 01.08.2025", for the log */
static const char* dstr(uint32_t d, char* buf, size_t cap)
{
  static const char* const W[7] = { "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun" };
  int sy = season_year(), m = 1;
  if (d >= 365) { snprintf(buf, cap, "day %u", d); return buf; }
  while (m < 12 && d >= MONTH0[m]) m++;
  snprintf(buf, cap, "%s %02u.%02d.%d", W[wday_in(d, sy)], d - MONTH0[m - 1] + 1, m, sy ? (d >= 181 ? sy : sy + 1) : 0);
  return buf;
}
/* a day of the 2026 frame (the fixed European days) on the same weekday of its own season:
   moved by up to three days within its week */
static uint32_t eday(uint32_t d)
{
  if (d >= 365) return d;
  int s = ((int)((d + 3) % 7) - wday(d) + 7) % 7;
  if (s > 3) s -= 7;
  return (uint32_t)(((int)d + s + 365) % 365);
}
static uint32_t g_rng;
static int coin(void)
{
  if (!g_rng) g_rng = (uint32_t)GetTickCount() ^ (uint32_t)__rdtsc() ^ 0x9e3779b9u;
  g_rng ^= g_rng << 13; g_rng ^= g_rng >> 17; g_rng ^= g_rng << 5;
  return (g_rng >> 7) & 1;
}

typedef struct { uint16_t league, row, po, ko; uint32_t days[2]; const char* name; } cup_t;
static const cup_t CUPS[3] = {
  { 3,        1027,     2,       4,       { 48, 55 }, "Champions League" },    /* 18/25 Feb (Wednesdays, 0.2.0) */
  { 5,        1029,     UEL_PO,  6,       { 49, 56 }, "Europa League" },       /* 19/26 Feb */
  { UECL_REG, UECL_ROW, UECL_PO, UECL_KO, { 49, 56 }, "Conference League" },
};
/* B193: a league phase starts with empty goal and assist lists. Its table is a pool table used
   before, and the game does not clear the lists it held: on 6/10/2029 the Conference League's
   league phase listed the Champions League's last round of 16 scorers. Only when the phase's
   table of that season is there and none of its matches is played (a draw asked again later
   keeps what was scored). */
static void lb_clear_phase(uint16_t row)
{
  for (int i = 0; i < 3; i++) {
    const cup_t* c = &CUPS[i];
    if (!cup_on(i) || c->row != row) continue;
    unsigned yl = 0, yr = 0;
    unsigned char* l = stage_table(c->league, 0, &yl);
    unsigned char* t = l ? stage_table(row, yl, &yr) : 0;
    if (!t || yr != yl) return;
    unsigned rows = *(uint32_t*)(t + 0x318 + 0x3c0), played = 0;
    if (rows > 48) rows = 48;
    for (unsigned j = 0; j < rows; j++) played += t[0x318 + 0x14 * j + 0x0f];
    unsigned g = *(uint32_t*)(l + LB_GOALS + 0x320), a = *(uint32_t*)(l + LB_ASSISTS + 0x320);
    if (played || (!g && !a)) return;
    *(uint32_t*)(l + LB_GOALS + 0x320) = 0;
    *(uint32_t*)(l + LB_ASSISTS + 0x320) = 0;
    logf("fl26swiss: %s scorers -- reg %u (season %u) held %u goal and %u assist rows of an older table; cleared at the draw",
         c->name, (unsigned)c->league, yl, g, a);
    return;
  }
}
static int g_po_day[3] = { -100000, -100000, -100000 };   /* abs_day() each play-off was last started */
static uint16_t tie_id(const cup_t* c, int k) { return (uint16_t)(c->po + 1024 * (k + 1)); }
static int po_available(const cup_t* c) { return get_rec(c->po) && get_rec(tie_id(c, 7)); }

static int po_start(int ci, void* started)
{
  const cup_t* c = &CUPS[ci];
  int d = today();
  int ad = abs_day();
  if (ad >= g_po_day[ci] && ad - g_po_day[ci] < 60) {
    logf("fl26swiss: %s play-off already drawn on day %d; not drawn again", c->name, d);
    return 1;
  }
  /* B192 (22.10.): the game asks for the league phase's progression again after every knockout
     round (run 13: reg 5 on days 83, 104, 118 and 139), and only the 60 days above kept the
     play-off from being drawn again -- a save loaded in March has no memory of the February
     draw, and on day 83 the Europa League play-off was drawn and started anew over its played
     ties while the round of 16 ran (and the Champions League's on day 153 in run 13). A draw
     comes when the league phase ends, before the first leg; two weeks past the second leg's
     day there is none to make this season. */
  if (d > (int)c->days[1] + 14 && d < 300) {
    logf("fl26swiss: %s play-off -- day %d is past its second leg (day %u); not drawn again",
         c->name, d, (unsigned)c->days[1]);
    g_po_day[ci] = ad;
    return 1;
  }
  unsigned char* ph = get_rec(c->row);
  unsigned char* t = ph && rec_count(ph) >= 24 ? lp_table(c->row) : 0;
  uint32_t rows = t ? *(uint32_t*)(t + 0x3c0) : 0;
  if (rows < 24 || rows > 48) {
    logf("fl26swiss: %s play-off not built (table rows %u)", c->name, rows);
    return 0;
  }
  /* Each tie keeps the table it was given last time (rec +0x88), and the schedule builder reuses
   * a table it finds instead of making one, so the February ties would be decided -- and their
   * winner read by 0x14151b2e0 -- from August's two clubs.  Free them first, as the July
   * teardown would have. */
  for (int k = 0; k < 8; k++)
    ((freetab_fn)(uintptr_t)(g_base + FREETAB_RVA))(0, tie_id(c, k));
  static uint32_t all[16];
  for (int b = 0; b < 4; b++) {                   /* bracket I..IV: seeds 9+2b, 10+2b; unseeded 23-2b, 24-2b */
    int cn = coin();
    for (int j = 0; j < 2; j++) {
      int k = 2 * b + j, seed = 8 + 2 * b + j, other = 22 - 2 * b + (j ^ cn);
      all[2 * k] = *(uint32_t*)(t + other * 20);   /* unseeded at home first */
      all[2 * k + 1] = *(uint32_t*)(t + seed * 20);
      logf("fl26swiss:   %s play-off tie %d: rank %d v rank %d", c->name, k, other + 1, seed + 1);
    }
  }
  canon_list(all, 16, "cup play-off reg", c->po);   /* B312 */
  u32vec va = { all, all + 16, all + 16 };
  ((setclr_fn)(uintptr_t)g_tramp_setcl)(c->po, &va, 1);
  for (int k = 0; k < 8; k++) {
    u32vec v = { all + 2 * k, all + 2 * k + 2, all + 2 * k + 2 };
    ((setclr_fn)(uintptr_t)g_tramp_setcl)(tie_id(c, k), &v, 1);
  }
  run_flush();
  unsigned char* r2 = get_rec(c->po);
  logf("fl26swiss: %s play-off -- ranks 9-24 of reg %u into reg %u (%u clubs), UEFA bracket drawn; day %d",
       c->name, (unsigned)c->row, (unsigned)c->po, r2 ? rec_count(r2) : 0, d);
  g_po_day[ci] = ad;
  /* In a second season the play-off is outside the season when February comes: the July
   * teardown put its +0x2fc back to 0xffff and the August fill left it alone (the rollover had
   * filled its first tie).  The game's start (0x141590420) then opens a NEW season sub-record
   * dated by today's year -- 2027 in February 2027 -- on the Europa League's header, and every
   * table lookup for the league phase (1029) and the round of 16 (6) lands in that empty record
   * (2026-10-13, slot 3, day 71: "reg 1029 has no table", R16 never drawn).  So the league
   * phase's season year is set on the play-off and its ties first, as fl26join does for a league
   * that enters without its table; the start then joins the running season, as in a first
   * season, where the world's creation had given every regulation the year. */
  {
    uint16_t yr = ph ? *(uint16_t*)(ph + 0x2fc) : 0xffff;
    unsigned char* po = get_rec(c->po);
    if (yr != 0xffff && po && *(uint16_t*)(po + 0x2fc) == 0xffff) {
      int nt = 0;
      *(uint16_t*)(po + 0x2fc) = yr;
      for (int k = 0; k < 8; k++) {
        unsigned char* tr = get_rec(tie_id(c, k));
        if (tr && *(uint16_t*)(tr + 0x2fc) == 0xffff) { *(uint16_t*)(tr + 0x2fc) = yr; nt++; }
      }
      logf("fl26swiss: %s play-off reg %u was outside the season (+0x2fc 0xffff); season %u of reg %u set on it and %d tie(s) before the start, so the game does not open a %u season from today's date",
           c->name, (unsigned)c->po, (unsigned)yr, (unsigned)c->row, nt, (unsigned)yr + 1);
    }
  }
  if (start_stage(started, c->po)) lb_carry(c->name, c->league, c->po);
  return 1;
}

/* who won play-off tie k: the game's winner read, but only when it is one of the tie's two clubs.
 * B121 (2026-10-17, fourth season of a Modpack career): the read gave Olympique Lyonnais, who had
 * finished in the top eight and played no February tie -- a winner of an earlier season's tie
 * under the same id -- and the round of 16 had Lyon v Lyon. A read that is not one of the tie's
 * clubs goes to the tie's own table (its leader, when it holds exactly the tie's two clubs; the
 * tie is over when this is asked, and the table orders them by points, then goal difference, the
 * aggregate), else, as lpre_winner and q_result do, to the seeded club, the tie's second.
 * 0: the tie has no clubs. */
/* does dst already hold src's first ten rows, each with at least src's tally? (an empty src: yes)
   Not the leader alone: run 6 (22.10., day 362) had the game refill the Conference League
   play-off's list with 13 rows of its own, and the league phase's leader was among them with
   the same 4 goals. Ten rows of the league phase are never pushed out of a merged list of 40. */
static int lb_has(const unsigned char* dst, const unsigned char* src)
{
  unsigned nd = *(const uint32_t*)(dst + 0x320), ns = *(const uint32_t*)(src + 0x320);
  if (nd > LB_ROWS) nd = LB_ROWS;
  if (ns > 10) ns = 10;
  for (unsigned k = 0; k < ns; k++) {
    const lb_row_t* s = (const lb_row_t*)src + k;
    unsigned i = 0;
    while (i < nd && ((const lb_row_t*)dst)[i].player != s->player) i++;
    if (i == nd || ((const lb_row_t*)dst)[i].n < s->n) return 0;
  }
  return 1;
}
/* B114 (runs 5-7, 22.10.): the game builds a stage's lists again from its own player tallies of
   that regulation -- 0x140fbd900 (this, u16 reg, players) clears both (0x140fbb090) and fills them --
   every few days (run 7: days 15, 29, 37, 54, 58, 65), so what lb_carry put there lasts until the
   next build: by day 65 the second season's round of 16 held 29 rows of its own and none of the
   league phase's ten best. (Goals of a match go in one at a time, 0x140fbca80, which is why the
   first season's round of 16 still had its carried rows on day 75.) So right after every build of
   a play-off or knockout list that runs this season, and on the day loop as well, a list without
   the league phase's ten best gets back what came before it: the play-off's lists for the
   knockout, then the league phase's. The play-off's own lists also hold August's qualifying
   play-off under the same regulation. */
static int from_league(const cup_t* c, uint16_t stage)
{
  unsigned char* r = get_rec(stage);
  unsigned char* lg = get_rec(c->league);
  if (!r || !lg || rec_count(r) != 16) return 0;
  const uint32_t* rc = rec_clubs(r); const uint32_t* lc = rec_clubs(lg);
  unsigned nl = rec_count(lg);
  for (unsigned i = 0; i < 16; i++) {
    unsigned j = 0;
    while (j < nl && !same_club(rc[i], lc[j])) j++;
    if (j == nl) return 0;
  }
  return 1;
}
/* the play-off runs from December to two weeks past its second leg, the knockout from the
   play-off's first leg to the end of June; both only with all their clubs from the league phase */
static int po_running(const cup_t* c, int d)
{
  return d >= 0 && (d >= 335 || d <= (int)c->days[1] + 14) && from_league(c, c->po);
}
static int ko_running(const cup_t* c, int d)
{
  return d >= (int)c->days[0] && d <= 180 && from_league(c, c->ko);
}
static void lb_fix(const cup_t* c, uint16_t stage, int d, const char* why)
{
  unsigned yt = 0, yl = 0, yp = 0;
  unsigned char* t = stage_table(stage, 0, &yt);
  unsigned char* l = stage_table(c->league, 0, &yl);
  if (!t || !l || yt != yl) return;
  unsigned char* p = stage == c->ko ? stage_table(c->po, yt, &yp) : 0;
  if (p && yp != yt) p = 0;
  unsigned n[2] = { 0, 0 }; int fixed = 0;
  for (int k = 0; k < 2; k++) {
    unsigned off = k ? LB_ASSISTS : LB_GOALS;
    n[k] = *(uint32_t*)(t + off + 0x320);
    if (lb_has(t + off, l + off)) continue;
    if (p) n[k] = lb_add(t + off, p + off);
    if (!lb_has(t + off, l + off)) n[k] = lb_add(t + off, l + off);
    fixed = 1;
  }
  if (fixed)
    logf("fl26swiss: %s scorers -- reg %u (season %u) without the league phase's; %s and the league phase's added again (%s, day %d): %u goal rows, %u assist rows",
         c->name, (unsigned)stage, yt, p ? "the play-off's" : "nothing before it", why, d, n[0], n[1]);
}
static void lb_keep(const cup_t* c, int d)
{
  if (po_running(c, d)) lb_fix(c, c->po, d, "day loop");
  if (ko_running(c, d)) lb_fix(c, c->ko, d, "day loop");
}
#define LBBUILD_RVA 0xfbd900   /* (this, u16 reg, players): a stage's goal and assist lists built anew */
static const unsigned char SIG_LBBUILD[14] = {
  0x48, 0x89, 0x4c, 0x24, 0x08, 0x55, 0x56, 0x57, 0x41, 0x54, 0x41, 0x55, 0x41, 0x56 };
unsigned char* g_tramp_lbbuild = 0;
typedef uint64_t (*lbbuild_fn)(void*, uint64_t, void*, uint64_t);
uint64_t lbbuild_handler(void* self, uint64_t reg, void* players, uint64_t a4)
{
  uint64_t r = ((lbbuild_fn)(uintptr_t)g_tramp_lbbuild)(self, reg, players, a4);
  int d = today();
  for (int i = 0; i < 3; i++) {
    const cup_t* c = &CUPS[i];
    if (!cup_on(i)) continue;
    if ((uint16_t)reg == c->po && po_running(c, d)) lb_fix(c, c->po, d, "after the game's build");
    else if ((uint16_t)reg == c->ko && ko_running(c, d)) lb_fix(c, c->ko, d, "after the game's build");
  }
  return r;
}

static uint32_t po_tie_winner(const cup_t* c, int k)
{
  uint16_t id = tie_id(c, k);
  unsigned char* r = get_rec(id);
  if (!r || rec_count(r) != 2) return 0;
  uint32_t a = rec_clubs(r)[0], b = rec_clubs(r)[1], w = 0;
  ((winner_fn)(uintptr_t)(g_base + WINNER_RVA))(&w, id);
  if ((w >> 14) && (same_club(w, a) || same_club(w, b))) return same_club(w, a) ? a : b;
  unsigned char* t = ((table_fn)(uintptr_t)(g_base + TABLE_RVA))(id);
  uint32_t rows = t ? *(uint32_t*)(t + 0x3c0) : 0, top = rows == 2 ? *(uint32_t*)t : 0, two = rows == 2 ? *(uint32_t*)(t + 20) : 0;
  int by_table = rows == 2 &&
                 ((same_club(top, a) && same_club(two, b)) || (same_club(top, b) && same_club(two, a)));
  uint32_t got = by_table ? (same_club(top, a) ? a : b) : b;
  logf("fl26swiss: %s play-off tie %d -- the winner read (%08x) is neither of its clubs (%08x, %08x); %08x goes through (%s)",
       c->name, k, w, a, b, got, by_table ? "the tie's table" : "the seeded club");
  return got;
}

static int po_finish(int ci, void* started)
{
  const cup_t* c = &CUPS[ci];
  unsigned char* ph = get_rec(c->row);
  unsigned char* t = ph && rec_count(ph) >= 24 ? lp_table(c->row) : 0;
  uint32_t rows = t ? *(uint32_t*)(t + 0x3c0) : 0;
  if (rows < 24) {
    logf("fl26swiss: %s play-off ended but reg %u has no table (rows %u)", c->name, (unsigned)c->row, rows);
    return 0;
  }
  static uint32_t list[16]; int bad = 0;
  uint32_t w[8];
  for (int k = 0; k < 8; k++) {
    w[k] = po_tie_winner(c, k);
    if (!(w[k] >> 14)) bad++;
  }
  if (bad) {
    logf("fl26swiss: %s play-off -- %d tie(s) without a winner; the knockout is left to the game", c->name, bad);
    return 0;
  }
  /* seed pair p (ranks 2p+1, 2p+2) meets bracket 3-p; slot order puts the pairs 1/2, 7/8, 3/4,
     5/6 in the top half and again in the bottom half, so neighbours meet in the right QF */
  static const int PAIR_AT[4] = { 0, 3, 1, 2 };
  for (int s = 0; s < 4; s++) {
    int p = PAIR_AT[s], b = 3 - p, top = coin(), draw = coin();
    for (int half = 0; half < 2; half++) {
      int seed = 2 * p + (half ^ top), tie = 2 * b + (half ^ top ^ draw), slot = s + 4 * half;
      list[2 * slot] = w[tie];
      list[2 * slot + 1] = *(uint32_t*)(t + seed * 20);
      logf("fl26swiss:   %s round of 16 tie %d: winner of play-off tie %d (%08x) v rank %d",
           c->name, slot, tie, w[tie], seed + 1);
    }
  }
  canon_list(list, 16, "cup round of 16 reg", c->ko);   /* B312 */
  u32vec v = { list, list + 16, list + 16 };
  ((setclr_fn)(uintptr_t)g_tramp_setcl)(c->ko, &v, 1);
  run_flush();
  unsigned char* ko = get_rec(c->ko);
  logf("fl26swiss: %s play-off over -- reg %u now %u clubs", c->name, (unsigned)c->ko, ko ? rec_count(ko) : 0);
  if (ko && rec_count(ko)) {
    lb_keep(c, today());
    if (start_stage(started, c->ko)) lb_carry(c->name, c->po, c->ko);
    return 1;
  }
  return 0;
}

/* ---- who goes to Europe: the UEFA access list, league by league ----
 *
 * The exe's rights table (0x1434f1fa0) knows only the shipped leagues, and its targets are the
 * old formats. So when the Champions League qualifying play-off is over in August -- the point
 * where the game has just built its own lists for reg 3 and reg 5 -- all three league phases are
 * filled here instead, from one list: association by association, which final positions go to
 * which competition. It follows the 2025/26 access list over the associations the game has (UEFA
 * ranking 2024; Russia suspended; Israel, Cyprus and the rest are not in the game), with the
 * earlier qualifying rounds collapsed into one play-off in August:
 *
 *   Champions League 28 direct -- champions of 1-9, runners-up of 1-6, thirds of 1-5, fourths of
 *     1-4, the two extra places of 2025/26 (England and Spain, fifth), and the two holders.
 *   The play-off 16 (UCLQ) -- Portugal 2nd and 3rd, Scotland, Greece, Denmark and Turkey's next
 *     places, France 4th, Netherlands 3rd and 4th, Belgium 2nd and 3rd. Its eight winners join
 *     the Champions League, its eight losers the Europa League (see the play-off below). A place
 *     of competition UCL past the 28 is played in the play-off too, ahead of its own places.
 *   Europa League 28 direct -- the Conference League holder and the next places of the big five,
 *     Netherlands, Portugal and Belgium (topped up as below); plus the eight play-off losers.
 *   A world listing no UCLQ place keeps the old way: 36 direct in both, no play-off.
 *   Conference League 36 -- the next place of every association from 1 to 27, the champions of
 *     the smaller ones (SVN FIN IRL BIH ALB MKD MNE) and six runners-up.
 *   A place whose league is missing, or whose club already went elsewhere, takes the next position
 *   of the same league; a list still short at the end is topped up from the next places of the
 *   big five, so each competition always gets its 36.
 *   The title holders come first in their section, as in the real list: the Champions League's
 *   and the Europa League's winners (knockout regs 4 and 6, the same two the UEFA Super Cup
 *   takes) play the next Champions League, the Conference League's (187) the next Europa League.
 *   A holder that also finished high enough at home for the same competition takes the holder's
 *   place, and the league place it leaves is not passed down its league: as at UEFA, it goes to
 *   the top-up below (GitHub #54: two English holders plus England's places pushed further down
 *   put eight English clubs in the league phase, which no draw can keep apart). A holder not
 *   known (a first season) gives its place to the next club of a big-five league instead.
 *
 * Only the shipped leagues are compiled in (their regulation ids are the game's own, the same in
 * every world). Our leagues' ids are handed out by the world builder and mean a different
 * country in each world -- with them compiled in, a public world's league on id 60 went to the
 * Europa League as if it were Serbia (GitHub issue #8). A world passes its own full list from
 * fl26swiss.lua (fl26_swiss_access); without one, the shipped places are used and the rest is
 * topped up from the big five.
 *
 * A position is read from last season's final table, captured at the July teardown before the
 * tables go; in a first season there is none, and the league ordered by squad strength stands in
 * (see seed_of below). */
enum { UCL = 0, UEL = 1, UECL = 2, LIB = 3, LIBQ = 4, AFCL = 5, UCLQ = 10, UELQ = 11, UECLQ = 12 };
/* UCLQ, UELQ, UECLQ: a place in the Champions League, Europa League or Conference League play-off
   in August (see "the August play-offs" below); the numbers are the League Builder's, 6..9 being
   its own continental cups */
/* LIB, LIBQ, AFCL: the Libertadores group stage (reg 9), its qualifying round (reg 8) and the AFC
   Champions League (reg 15). Their places do not make a list of their own: they replace the
   "other" pool clubs the game fills those fields with (see cont_swap). */
/* rank 0 = the winner of competition reg (a domestic cup); when that club is missing or already
   placed, the place goes to the next free position of league alt (0 = the place is lost) */
typedef struct { uint16_t reg; uint8_t rank; uint8_t comp; uint16_t alt; } access_t;
#define R_ENG 17
#define R_ITA 18
#define R_ESP 19
#define R_FRA 20
#define R_NED 21
#define R_POR 22
#define R_GER 50
#define R_GRE 117
#define R_TUR 118
#define R_SCO 134
#define R_DEN 147
#define R_BEL 155
#define R_UCLKO 4
#define R_UELKO 6
static const access_t ACCESS[] = {
  /* Champions League: the two holders, then the leagues -- 28 direct entrants with the play-off */
  {R_UCLKO,0,UCL,R_ENG},{R_UELKO,0,UCL,R_ESP},
  {R_ENG,1,UCL},{R_ITA,1,UCL},{R_ESP,1,UCL},{R_GER,1,UCL},{R_FRA,1,UCL},{R_NED,1,UCL},{R_POR,1,UCL},
  {R_BEL,1,UCL},{R_TUR,1,UCL},
  {R_ENG,2,UCL},{R_ITA,2,UCL},{R_ESP,2,UCL},{R_GER,2,UCL},{R_FRA,2,UCL},{R_NED,2,UCL},
  {R_ENG,3,UCL},{R_ITA,3,UCL},{R_ESP,3,UCL},{R_GER,3,UCL},{R_FRA,3,UCL},
  {R_ENG,4,UCL},{R_ITA,4,UCL},{R_ESP,4,UCL},{R_GER,4,UCL},
  {R_ENG,5,UCL},{R_ESP,5,UCL},
  /* the Champions League play-off: sixteen, eight to the Champions League, eight to the Europa League */
  {R_POR,2,UCLQ},{R_SCO,1,UCLQ},{R_GRE,1,UCLQ},{R_FRA,4,UCLQ},{R_NED,3,UCLQ},{R_BEL,2,UCLQ},
  {R_DEN,1,UCLQ},{R_TUR,2,UCLQ},{R_SCO,2,UCLQ},{R_GRE,2,UCLQ},{R_POR,3,UCLQ},{R_BEL,3,UCLQ},
  {R_NED,4,UCLQ},{R_DEN,2,UCLQ},{R_TUR,3,UCLQ},{R_SCO,3,UCLQ},
  /* Europa League: the Conference League holder, then the leagues -- 20 direct entrants with the play-offs */
  {UECL_KO,0,UEL,R_ITA},
  {R_ENG,6,UEL},{R_ITA,5,UEL},{R_ESP,6,UEL},{R_GER,5,UEL},{R_FRA,5,UEL},
  {R_ENG,7,UEL},{R_ITA,6,UEL},{R_ESP,7,UEL},{R_GER,6,UEL},{R_FRA,6,UEL},
  {R_NED,5,UEL},{R_POR,4,UEL},{R_BEL,4,UEL},
  {R_TUR,4,UEL},{R_SCO,4,UEL},{R_GRE,3,UEL},{R_DEN,3,UEL},{R_NED,6,UEL},{R_POR,5,UEL},
  /* the Europa League play-off: sixteen, eight to the Europa League, eight to the Conference League */
  {R_ENG,8,UELQ},{R_ITA,7,UELQ},{R_ESP,8,UELQ},{R_GER,7,UELQ},{R_FRA,7,UELQ},
  {R_BEL,5,UELQ},{R_TUR,5,UELQ},{R_SCO,5,UELQ},{R_GRE,4,UELQ},{R_DEN,4,UELQ},
  {R_NED,7,UELQ},{R_POR,6,UELQ},{R_BEL,6,UELQ},{R_TUR,6,UELQ},{R_GRE,5,UELQ},{R_DEN,5,UELQ},
  /* Conference League -- 20 direct entrants with the play-offs */
  {R_ENG,9,UECL},{R_ITA,8,UECL},{R_ESP,9,UECL},{R_GER,8,UECL},{R_FRA,8,UECL},
  {R_NED,8,UECL},{R_POR,7,UECL},{R_BEL,7,UECL},{R_TUR,7,UECL},{R_SCO,6,UECL},{R_GRE,6,UECL},{R_DEN,6,UECL},
  {R_NED,9,UECL},{R_POR,8,UECL},{R_BEL,8,UECL},{R_TUR,8,UECL},{R_GRE,7,UECL},{R_SCO,7,UECL},{R_DEN,7,UECL},
  {R_ENG,10,UECL},
  /* the Conference League play-off: sixteen, eight to the Conference League, eight out */
  {R_ITA,9,UECLQ},{R_ESP,10,UECLQ},{R_GER,9,UECLQ},{R_FRA,9,UECLQ},{R_NED,10,UECLQ},{R_POR,9,UECLQ},
  {R_BEL,9,UECLQ},{R_TUR,9,UECLQ},{R_GRE,8,UECLQ},{R_SCO,8,UECLQ},{R_DEN,8,UECLQ},{R_ENG,11,UECLQ},
  {R_ITA,10,UECLQ},{R_ESP,11,UECLQ},{R_GER,10,UECLQ},{R_FRA,10,UECLQ},
};
#define NACCESS (sizeof ACCESS / sizeof ACCESS[0])
/* the list in use: the compiled one above, or the one the loader passes (fl26_swiss_access) --
   a world with other regulation ids carries its own list in fl26swiss.lua */
#define ACCESS_MAX 1024     /* 256 until the limits branch: 209 lines with 80 leagues, ~600 at 250 */
static access_t g_access_buf[ACCESS_MAX];
static const access_t* g_access = ACCESS;
static size_t g_naccess = NACCESS;
static int g_access_cfg = 0;
#define FINAL_MAX 40
typedef struct { uint16_t reg; uint16_t n; int day; uint32_t club[FINAL_MAX]; } final_t;
/* 64 until B160: a world of 86 leagues filled it by day 176, and the leagues kept after that
   (Vietnam, Jordan, Kuwait, Bahrain, Oman) sent their clubs by the live table */
#define FINAL_N 1024        /* 256 until the limits branch: ~190 at 250 leagues */
static final_t g_final[FINAL_N]; static int g_nfinal = 0;
static final_t* final_new(uint16_t reg)
{
  static int told = 0;
  if (g_nfinal >= FINAL_N) {
    if (!told) logf("fl26swiss: no room for more final tables (%d kept); reg %u and the leagues after it go by the live table", FINAL_N, (unsigned)reg);
    told = 1;
    return 0;
  }
  return &g_final[g_nfinal++];
}
static const char* COMP_NAME[3] = { "Champions League", "Europa League", "Conference League" };

typedef struct { uint16_t reg; int day; uint32_t club; } cupwin_t;
/* 32 until the limits branch: a cup winner kept per national cup with a continental place, per
   cup a continental cup of ours takes the winner of and per August-May super cup's cup */
#define CUPWIN_N 512
static cupwin_t g_cupwin[CUPWIN_N]; static int g_ncupwin = 0;
/* Synthetic retained-result key: no real regulation uses this value. */
#define CUPWIN_LIB_RUNNER 0xfffeu

/* B49: what is kept is read back from the save folder after a restart or a load (state_sync) */
static void state_sync(void);
static void state_store(void);
static int g_st_read_back = 0;

/* the winner of a competition as the game's own rights code sees it, or 0 */
static uint32_t winner_now(uint16_t reg)
{
  if (!get_rec(reg)) return 0;
  uint32_t c = 0;
  ((right_fn)(uintptr_t)(g_base + RIGHT_RVA))(&c, reg, 0);
  if (c == *(uint32_t*)(g_base + NOCLUB_RVA) || !(c >> 14)) return 0;
  return c;
}
static cupwin_t* cupwin_of(uint16_t reg)
{
  state_sync();
  for (int i = 0; i < g_ncupwin; i++) if (g_cupwin[i].reg == reg) return &g_cupwin[i];
  return 0;
}

static final_t* final_of(uint16_t reg)
{
  state_sync();
  for (int i = 0; i < g_nfinal; i++) if (g_final[i].reg == reg) return &g_final[i];
  return 0;
}
/* ---- a season of two tournaments of the game: the whole season's table ----
 *
 * Colombia (Liga BetPlay DIMAYOR, reg 119) and the MLS (51) are a total of type 5 and two
 * halves with a table each (168 and 169, 166 and 167: format 7 and 8, +0x06 the total). A
 * continental place given to a half (game_europe 168, Liga BetPlay DIMAYOR I) went by that
 * half's table alone -- the Apertura (Vicentico, 04.11.2026). A place given to the total goes by
 * the whole season: the world file's `seasonsum <total> parts=<half>,<half>` (leaguebuilder,
 * game_europe on the total). Once the last half's matches are all played, the halves' tables
 * are added together (points, then goal difference, then goals) and kept as the total's final
 * table (ssum_keep), and nothing else ever keeps one for it (keep_final). Until there is one --
 * a first season, or a half with no complete table -- the total's places read its first half,
 * as a place given to that half did. */
#define SSUM_MAX 16
#define SSUM_PARTS 3
typedef struct { uint16_t total, part[SSUM_PARTS]; } ssum_t;
static ssum_t g_ssum[SSUM_MAX]; static int g_nssum = 0;
static const ssum_t* ssum_of(uint16_t reg)
{
  for (int i = 0; i < g_nssum; i++) if (g_ssum[i].total == reg) return &g_ssum[i];
  return 0;
}
/* the world file's seasonsum lines: n entries of 1 + SSUM_PARTS ids (total, then its halves, 0 for
   none); an entry with no half, or with a half that is the total, is left out. Returns how many */
__declspec(dllexport) int fl26_swiss_seasonsum(const uint16_t* v, int n)
{
  if ((!v && n) || n < 0) return -1;
  g_nssum = 0;
  for (int i = 0; i < n && g_nssum < SSUM_MAX; i++) {
    const uint16_t* e = v + (1 + SSUM_PARTS) * i;
    ssum_t s = { e[0], { 0 } };
    int k = 0, bad = !e[0];
    for (int p = 0; p < SSUM_PARTS; p++) {
      if (!e[1 + p]) continue;
      if (e[1 + p] == e[0]) bad = 1;
      s.part[k++] = e[1 + p];
    }
    if (bad || !k || ssum_of(s.total)) continue;
    g_ssum[g_nssum++] = s;
  }
  logf("fl26swiss: %d season(s) of two tournaments counted as a whole for their places (seasonsum)", g_nssum);
  return g_nssum;
}
#define BUILD_DAY 210  /* the day-216 rollover builds the new season; nothing after this is final */
/* New Year's teardown, where a February-December league's season ends (days NEWYEAR_FROM..365
   and 1..NEWYEAR_TO) */
#define NEWYEAR_FROM 335
#define NEWYEAR_TO   45
static int season_played(uint16_t reg);
/* a table in exactly the league's list order is one nobody has played yet -- unless a row has a
   match played (+0x0f, the MP column's count). B276 (antonimus 29.10.): a Libertadores group of
   four finishing in its draw order (1 in 24) went by squad strength at the Sudamericana play-off
   fill, two to three of the 16 groups a season in his log, all six matchdays played */
static int unplayed(unsigned char* rec, unsigned char* t, uint32_t rows)
{
  int listed = rec_count(rec) == rows;
  for (uint32_t k = 0; k < rows && listed; k++) listed = *(uint32_t*)(t + k * 20) == rec_clubs(rec)[k];
  for (uint32_t k = 0; k < rows && listed; k++) if (t[k * 20 + 0x0f]) listed = 0;
  return listed;
}
/* keep reg's final table at the July teardown, while it still exists; 1 kept, -1 a table nobody
   has played, 0 nothing to keep (or kept already this summer) */
static int keep_final(uint16_t reg, int d, int ad)
{
  if (ssum_of(reg)) return 0;       /* a whole season's total: its table is ssum_keep's alone */
  final_t* f = final_of(reg);
  /* the first rollover of the summer has the final tables; a later one (day 216, when the new
     season is built) already has next season's clubs in list order and must not replace it */
  if (f && ad >= f->day && ad - f->day < 60) return 0;
  unsigned char* rec = get_rec(reg);
  if (!rec) return 0;
  unsigned char* t = ((table_fn)(uintptr_t)(g_base + TABLE_RVA))(reg);
  uint32_t rows = t ? *(uint32_t*)(t + 0x3c0) : 0;
  if (rows < 4 || rows > FINAL_MAX) return 0;
  /* A new career is built on day 216 and its tables exist then, with nobody having played:
     the clubs in list order. Kept, they stood in for last season's finish and the
     first-season order below never ran (2026-09-27: "final tables of 31 league(s) kept on
     day 216" in a career created that minute). A season's own build is the same rollover
     and, as said above, never holds a final table; and a table in exactly the league's list
     order is one nobody has played. */
  if ((d >= BUILD_DAY && d < NEWYEAR_FROM) || unplayed(rec, t, rows)) return -1;
  if (!f) { if (!(f = final_new(reg))) return 0; f->reg = reg; }
  f->n = (uint16_t)rows; f->day = ad;
  for (uint32_t k = 0; k < rows; k++) f->club[k] = *(uint32_t*)(t + k * 20);
  return 1;
}
/* at the July teardown: every access league's final table, while it still exists */
static void access_capture(void)
{
  int got = 0, skipped = 0, running = 0, d = today(), ad = abs_day();
  /* GitHub #119: a February-December league ends at New Year, and its final table was never
     kept -- the July teardown kept it half-way through its next season, so the Libertadores took
     the clubs on top in July (Peru: ADT and Cienciano instead of champion Juan Pablo II). New
     Year keeps the tables of the access leagues whose every match is played; July then leaves
     a league alone whose season is still running and whose New Year table it has. */
  int newyear = d >= NEWYEAR_FROM || d <= NEWYEAR_TO;
  if (newyear) {
    if (modern_conmebol()) {
      /* Libertadores is not necessarily represented by a rank-0 access entry.
         Retain its completed knockout winner before the New Year teardown resets it. */
      const uint16_t libko = 10;
    cupwin_t* lw = cupwin_of(libko);
    if (!(lw && ad >= lw->day && ad - lw->day < 60)) {
      uint32_t lc = winner_now(libko);
      if (lc) {
        if (!lw && g_ncupwin < CUPWIN_N) { lw = &g_cupwin[g_ncupwin++]; lw->reg = libko; }
        if (lw) {
          lw->day = ad; lw->club = lc;
          logf("fl26swiss: access -- Libertadores holder reg %u won by %08x retained at New Year (day %d)",
               (unsigned)libko, lc, d);
        }
      }
    }

    /* Keep the previous Libertadores runner-up beside the champion. A world with
       no Sudamericana uses it for the second direct continental place after the
       knockout is reset; worlds with Sudamericana simply leave it unused. */
    cupwin_t* rw = cupwin_of(CUPWIN_LIB_RUNNER);
    if (!(rw && ad >= rw->day && ad - rw->day < 60)) {
      uint32_t rc = knockout_runner_now(libko);
      if (rc) {
        if (!rw && g_ncupwin < CUPWIN_N) {
          rw = &g_cupwin[g_ncupwin++];
          rw->reg = CUPWIN_LIB_RUNNER;
        }
        if (rw) {
          rw->day = ad; rw->club = rc;
          logf("fl26swiss: access -- Libertadores runner-up %08x retained at New Year (day %d)",
               rc, d);
        }
      }
    }
    }

    for (size_t i = 0; i < g_naccess; i++) {
      uint16_t reg = g_access[i].reg;
      /* Synthetic CONMEBOL association sources have no competition table to retain.
         They are resolved from Team.bin by assoc_seed() each season. */
      if (assoc_source(reg) || !g_access[i].rank || !season_played(reg)) continue;
      int dup = 0;
      for (size_t j = 0; j < i; j++) dup |= g_access[j].rank && g_access[j].reg == reg;
      if (!dup && keep_final(reg, d, ad) > 0) got++;
    }
    if (got) logf("fl26swiss: access -- New Year: final tables of %d league(s) kept on day %d", got, d);
    return;
  }
  if (d < 140 || d > 230) return;                 /* the summer rollover, and New Year's above */
  for (size_t i = 0; i < g_naccess; i++) {
    uint16_t reg = g_access[i].reg;
    if (assoc_source(reg)) continue;
    if (g_access[i].rank && !season_played(reg)) {
      final_t* f = final_of(reg);
      if (f && ad >= f->day && ad - f->day < 250) { running++; continue; }
    }
    if (!g_access[i].rank) {                        /* a cup: keep its winner, same summer rule */
      cupwin_t* w = cupwin_of(reg);
      if (w && ad >= w->day && ad - w->day < 60) continue;
      uint32_t c = winner_now(reg);
      if (!c) continue;
      if (!w) { if (g_ncupwin >= CUPWIN_N) continue; w = &g_cupwin[g_ncupwin++]; w->reg = reg; }
      w->day = ad; w->club = c;
      logf("fl26swiss: access -- cup reg %u won by %08x (day %d)", (unsigned)reg, c, d);
      continue;
    }
    int r = keep_final(reg, d, ad);
    got += r > 0; skipped += r < 0;
  }
  if (got) logf("fl26swiss: access -- final tables of %d league(s) kept on day %d", got, d);
  if (skipped) logf("fl26swiss: access -- %d table(s) with no match played yet not kept (day %d)", skipped, d);
  if (running) logf("fl26swiss: access -- %d league(s) mid-season: their New Year table stands (day %d)", running, d);
}
/* a cup's winner retained at a teardown, else asked of the game now */
static uint32_t cup_winner_within(uint16_t reg, int maxage)
{
  cupwin_t* w = cupwin_of(reg);
  int d = abs_day();
  if (w && d >= w->day && d - w->day < maxage) return w->club;
  return ccup_ko_winner(reg);
}
static uint32_t cup_winner(uint16_t reg) { return cup_winner_within(reg, 120); }
/* Calendar-year CONMEBOL cups can ask in February for the winners retained at the previous
   New-Year teardown. Prefer a live winner (a current-year tie), otherwise accept the retained
   winner for up to 330 days. This is the Recopa path. */
static uint32_t cal_cup_winner(uint16_t reg)
{
  uint32_t c = winner_now(reg);
  return c ? c : cup_winner_within(reg, 330);
}
/* ---- a first season: the league ordered by squad strength ----
 *
 * With no final table kept, a league's list order stood in for last season's finish. The shipped
 * leagues list their clubs alphabetically, so the first season sent Angers and Auxerre to the
 * Champions League and Paris Saint-Germain, Real Madrid and Inter, whichever places were left,
 * to the Conference League (reported on Evo-Web, 2026-09-27). Now the clubs are ranked by squad
 * strength instead: a player is worth the mean of his ten best outfield abilities, or of the five
 * goalkeeping ones if he is registered in goal; a club is its best keeper plus its ten best
 * outfield players, averaged. Ties (cloned squads) and clubs whose squad cannot be read keep the
 * list order, so a world that wrote its leagues in last season's finish and gave them equal
 * squads keeps that order. Measured on the live game 2026-09-27: PSG 84.6, Monaco 82.3,
 * Marseille 82.0; Real Madrid 86.3, Barcelona 85.2, Atletico 84.5; Man City 85.9, Liverpool 85.1.
 *
 * Squads come from the game's own lookups, which the runtime patch set already points at the
 * relocated arrays: 0x1414bb580(blk, club handle) -> team record, 0x1414bb2a0(blk, player
 * handle) -> player record. Both answer a blank record for an unknown handle, so the id is
 * checked. The roster is u64 handles {u32 key, u32 player id} at team + 0x14c, count at
 * team + 0x426 & 0x7f. Abilities in the live player record are 7-bit raw values (not the file's
 * 6-bit value + 40); the registered position is 4 bits at +0x07 bit 4, 0 = goalkeeper. */
#define TEAMGET_RVA   0x14bb580
#define PLAYERGET_RVA 0x14bb2a0
typedef unsigned char* (*teamget_fn)(void* blk, uint64_t handle);
typedef unsigned char* (*playerget_fn)(void* blk, uint64_t handle);
static const uint8_t AB_OUT[20][2] = {   /* {byte, bit} */
  {0x03,0},{0x06,5},{0x05,6},{0x08,0},{0x09,6},{0x0a,5},{0x08,7},{0x0c,0},{0x0e,5},{0x10,0},
  {0x14,7},{0x18,7},{0x18,0},{0x19,6},{0x15,6},{0x16,5},{0x1a,5},{0x04,0},{0x0c,7},{0x0d,6} };
static const uint8_t AB_GK[5][2] = { {0x04,7},{0x10,7},{0x11,6},{0x12,5},{0x14,0} };
static int ab7(const unsigned char* p, const uint8_t* bs) { return ((p[bs[0]] | p[bs[0] + 1] << 8) >> bs[1]) & 0x7f; }
static void sort_desc(int* v, int n)
{
  for (int i = 1; i < n; i++) { int x = v[i], j = i; while (j > 0 && v[j - 1] < x) { v[j] = v[j - 1]; j--; } v[j] = x; }
}
/* tenths of an ability point; *gk set when he is registered in goal */
static int player_value(const unsigned char* p, int* gk)
{
  int s = 0;
  *gk = ((p[7] >> 4) & 0xf) == 0;
  if (*gk) { for (int i = 0; i < 5; i++) s += ab7(p, AB_GK[i]); return s * 2; }
  int v[20];
  for (int i = 0; i < 20; i++) v[i] = ab7(p, AB_OUT[i]);
  sort_desc(v, 20);
  for (int i = 0; i < 10; i++) s += v[i];
  return s;
}
/* tenths; 0 when the squad cannot be read or has no keeper and ten outfield players */
static int club_strength(void* blk, uint32_t club)
{
  unsigned char* t = ((teamget_fn)(uintptr_t)(g_base + TEAMGET_RVA))(blk, club);
  if (!t || *(uint32_t*)t >> 14 != club >> 14) return 0;
  int n = t[0x426] & 0x7f, gk = 0, of[128], nof = 0;
  for (int k = 0; k < n; k++) {
    uint64_t h = *(uint64_t*)(t + 0x14c + 8 * k);
    unsigned char* p = ((playerget_fn)(uintptr_t)(g_base + PLAYERGET_RVA))(blk, h);
    if (!p || *(uint32_t*)(p + 0x30) != (uint32_t)(h >> 32)) continue;
    int g, v = player_value(p, &g);
    if (g) { if (v > gk) gk = v; } else of[nof++] = v;
  }
  if (!gk || nof < 10) return 0;
  sort_desc(of, nof);
  int s = gk;
  for (int i = 0; i < 10; i++) s += of[i];
  return s / 11;
}
#define SEED_N 512          /* 64 until the limits branch: a league or association per access source */
static final_t g_seed[SEED_N]; static int g_nseed = 0;

/* A synthetic access source: 0x8000 | Country.bin id. The builder uses it
 * for a CONMEBOL association that has real clubs in Other Latin American
 * but no playable domestic league in this world. */
#define ASSOC_SOURCE       0x8000u
#define ASSOC_COUNTRY_MASK 0x01ffu
#define ASSOC_POOL_LATAM   73
#define ASSOC_MIN_SQUAD    18
static int assoc_source(uint16_t source)
{
  return (source & ASSOC_SOURCE) && !(source & ~(ASSOC_SOURCE | ASSOC_COUNTRY_MASK))
         && (source & ASSOC_COUNTRY_MASK);
}
static int assoc_country(uint16_t source) { return source & ASSOC_COUNTRY_MASK; }

/* Playable clubs of one association, strongest first, cached once per summer.
 * No team ids are stored in the world file: the source rank is resolved here. */
static final_t* assoc_seed(uint16_t source)
{
  if (!assoc_source(source)) return 0;
  state_sync();
  int d = abs_day();
  final_t* f = 0;
  for (int i = 0; i < g_nseed; i++) if (g_seed[i].reg == source) f = &g_seed[i];
  if (f && d >= f->day && d - f->day < 120) return f->n ? f : 0;

  uint32_t na = 0;
  unsigned char* a = team_array(&na);
  unsigned char* o = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
  void* blk = o ? *(void**)(o + 0x48) : 0;
  if (!a || !blk) return 0;
  if (!f) { if (g_nseed >= SEED_N) return 0; f = &g_seed[g_nseed++]; f->reg = source; }
  f->day = d; f->n = 0;

  int str[FINAL_MAX], known = 0;
  unsigned n = 0;
  int country = assoc_country(source);
  for (uint32_t i = 0; i < na && n < FINAL_MAX; i++) {
    uint32_t v = team_at(a, i);
    if (v == 0xffffffffu || !(v >> 14) || (v >> 14) == 0x3ffff || (v & 0x3fff) != i) continue;
    v = canon_club(v);
    unsigned char* t = ((teamget_fn)(uintptr_t)(g_base + TEAMGET_RVA))(blk, v);
    if (!t || *(uint32_t*)t >> 14 != v >> 14) continue;
    if (((*(uint16_t*)(t + 0x418)) & 0x1ff) != country) continue;
    if (lay_slot(t) != ASSOC_POOL_LATAM) continue;
    if ((t[0x426] & 0x7f) < ASSOC_MIN_SQUAD) continue;

    f->club[n] = v;
    str[n] = club_strength(blk, v);
    known += str[n] > 0;
    for (unsigned j = n; j > 0 && str[j - 1] < str[j]; j--) {
      int ss = str[j]; str[j] = str[j - 1]; str[j - 1] = ss;
      uint32_t c = f->club[j]; f->club[j] = f->club[j - 1]; f->club[j - 1] = c;
    }
    n++;
  }
  f->n = (uint16_t)n;
  if (!n) {
    logf("fl26swiss: CONMEBOL association source %u (country %d) -- no eligible Other Latin American club",
         (unsigned)source, country);
    return 0;
  }
  logf("fl26swiss: CONMEBOL association source %u (country %d) -- %u club(s), %d strength(s) read%s",
       (unsigned)source, country, n, known, known ? "" : "; stable team-array order stands");
  if (known) state_store();
  for (unsigned i = 0; i < n && i < 8; i++)
    logf("fl26swiss:   association country %d rank %u -> %08x%s%d.%d", country, i + 1, f->club[i],
         str[i] ? " strength " : " strength unreadable ", str[i] / 10, str[i] % 10);
  return f;
}

/* the league's clubs, strongest first; worked out once per summer */
static final_t* seed_of(uint16_t reg)
{
  if (assoc_source(reg)) return assoc_seed(reg);
  state_sync();
  int d = abs_day();
  final_t* f = 0;
  for (int i = 0; i < g_nseed; i++) if (g_seed[i].reg == reg) f = &g_seed[i];
  if (f && d >= f->day && d - f->day < 120) return f->n ? f : 0;
  unsigned char* rec = get_rec(reg);
  unsigned char* o = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
  void* blk = o ? *(void**)(o + 0x48) : 0;
  if (!rec || !blk) return 0;
  if (!f) { if (g_nseed >= SEED_N) return 0; f = &g_seed[g_nseed++]; f->reg = reg; }
  f->day = d;
  unsigned n = rec_count(rec);
  if (n > FINAL_MAX) n = FINAL_MAX;
  int str[FINAL_MAX], known = 0;
  for (unsigned k = 0; k < n; k++) {
    f->club[k] = rec_clubs(rec)[k];
    str[k] = club_strength(blk, f->club[k]);
    known += str[k] > 0;
    /* stable: a club only passes the ones strictly weaker */
    for (unsigned j = k; j > 0 && str[j - 1] < str[j]; j--) {
      int s = str[j]; str[j] = str[j - 1]; str[j - 1] = s;
      uint32_t c = f->club[j]; f->club[j] = f->club[j - 1]; f->club[j - 1] = c;
    }
  }
  f->n = known ? (uint16_t)n : 0;
  if (!known) { logf("fl26swiss: first season -- reg %u: no squad could be read; list order stands", (unsigned)reg); return 0; }
  state_store();
  if (n < 3) return f;
  logf("fl26swiss: first season -- reg %u by squad strength (%d of %u read): %08x %d.%d, %08x %d.%d, %08x %d.%d ... last %08x %d.%d",
       (unsigned)reg, known, n, f->club[0], str[0] / 10, str[0] % 10, f->club[1], str[1] / 10, str[1] % 10,
       f->club[2], str[2] / 10, str[2] % 10, f->club[n - 1], str[n - 1] / 10, str[n - 1] % 10);
  return f;
}
/* the club at a league position: last season's table if it was kept, else the league ordered by
   squad strength, else the list order. keep: for how many days a kept table stands -- 120 for the
   UEFA places (handed out in August), longer for competitions whose entrants come later */
static uint32_t access_club_kept(uint16_t reg, int rank, int* from_table, int keep)
{
  final_t* f = final_of(reg);
  int d = abs_day();
  /* B312: a kept table, the first season's order and the list can hold a club at a row the team
     array has since given to another (canon_list) */
  if (f && rank <= f->n && d >= f->day && d - f->day < keep) { *from_table = 1; return canon_club(f->club[rank - 1]); }
  /* a whole season with no table of its own kept yet: its first half, as before (seasonsum) */
  const ssum_t* ss = ssum_of(reg);
  if (ss && ss->part[0] != reg) return access_club_kept(ss->part[0], rank, from_table, keep);
  *from_table = 0;
  final_t* s = seed_of(reg);
  if (s) return rank <= s->n ? canon_club(s->club[rank - 1]) : 0;
  unsigned char* rec = get_rec(reg);
  if (!rec || (unsigned)rank > rec_count(rec)) return 0;
  return canon_club(rec_clubs(rec)[rank - 1]);
}
static uint32_t access_club(uint16_t reg, int rank, int* from_table) { return access_club_kept(reg, rank, from_table, 120); }
static int g_access_on = 1;
/* A first-season list from the loader (fl26swiss-first.txt, read by fl26swiss.lua): team ids per
   competition, taken as they are while no final table has been kept -- the first season, or a
   restart between the end of the season and the draw. Ids the game does not have, or that are
   already placed, are left out and the access list below fills the places that remain. */
static uint32_t g_first[4][48]; static unsigned g_nfirst[4];   /* [3]: the AFC Champions League's, cont_build */
/* The list is for a new career's first summer only: a career built in this session (its season
   calendar dated on day 216, date_handler). Kept tables alone (any_final_kept) are not enough --
   they live in memory, so a game quit between June and the August draw of a later season lost
   them and the first season's list came back (2026-10-05). */
/* where each placed club came from, for the log: reg 0 = the first-season list */
typedef struct { uint16_t reg; uint8_t rank; } how_t;
static how_t g_how[3][FIELD];
static int any_final_kept(void)
{
  state_sync();
  int d = abs_day();
  for (int i = 0; i < g_nfinal; i++) if (d >= g_final[i].day && d - g_final[i].day < 120) return 1;
  return 0;
}
/* ---- the August qualifying rounds ----
 *
 * Each of the three competitions can have up to three qualifying rounds in August, each of
 * sixteen clubs, eight ties over two legs: a play-off (stage 0), and in front of it a third (1)
 * and a second qualifying round (2). Round i is competition i % NQ at stage i / NQ, so rounds
 * 0..2 are the play-offs. A place of competition UCLQ, UELQ or UECLQ is a place in one of the
 * competition's rounds:
 *   - the Champions League's play-off is the shipped regulation 2 (the play-offs' days, see
 *     is_playoff), the Europa League's and the Conference League's the knockout play-offs
 *     tools/mkeuropo.py adds (188, 189, ties at id + 1024 * (k + 1)), the ones February uses
 *     again; the qualifying rounds in front of them are more copies of reg 2 the world builder
 *     adds under ids of its own and names in the world file (`qround <competition> <round>
 *     <regulation>`, fl26_swiss_qrounds). A world without qround lines has the play-offs alone.
 *   - A round's winners go to the next round of its competition, a play-off's to the league
 *     phase. Its losers drop as UEFA's do: the Champions League's second qualifying round's to
 *     the Europa League's third, its third's to the Europa League's play-off, its play-off's to
 *     the Europa League's league phase; the Europa League's the same way into the Conference
 *     League; the Conference League's are out, and so is a loser whose round below is missing.
 *   - So each round takes sixteen, less eight for every round that feeds it (q_room): its new
 *     entrants are a competition's qualifying places in list order, the strongest to the round
 *     nearest the league phase. A play-off's winners take places from the competition's direct
 *     entrants and its losers eight more in the one below: with all three, 28 / 20 / 20.
 *   - Days (qr_day): midweek, the same for all three competitions, one leg a week: the second
 *     qualifying round in the first week the season's build leaves a midweek day in (2025: Thu
 *     7 and 14 August), the third in the two weeks after it (Wed 20 and 27 August), the
 *     play-offs (the Champions League's, reg 2, too) in the two after that (Wed 3 and 10
 *     September).  A league has its weekend between every two legs, three days clear of both
 *     (rcal_cost, busy_days).  Where the play-off's second leg leaves less than six days to the
 *     first league-phase matchday, that matchday is a week later (swiss_day).  The national
 *     cups' first round (251, 254) would be in one of the six weeks every year; it moves to a
 *     Tuesday and Friday clear of every European day (natcup_day).  Until 0.2.0 the two legs of a stage were two days apart (Tuesday and
 *     Thursday), and before that on weekends: a Dinamo played Saturday and Wednesday in Europe
 *     and Thursday in the league (2026-10-08).  All play-off second legs are on one day: the
 *     progressions run in the day loop after the day's matches, the Europa and Conference
 *     League's before reg 2's, whose end builds the league phases (measured: 189, 188, then 2,
 *     one batch).  FL27 has no six weeks before its own league phase (day 250): qr_fl27 puts
 *     the six legs between 218 and 244, a week apart where they fit (B463).  A round is filled
 *     on the days between the round before it and its first leg (q_fill); the season is built on day 216, so nothing is filled before 217.
 *   - From the second season on, the rights builder fills reg 2 and its eight ties (1026 ... 8194)
 *     at the July rollover through set_clubs (from 0x14135c083 on day 181, measured 2026-10-01),
 *     with the game's own clubs; setcl_handler hands it ours instead (q_setcl). With a third
 *     qualifying round in front of it the sixteen are not known yet: the ties are left empty, as
 *     in a new career's first summer, and the day loop fills them.
 *   - A new career has no play-off at all: reg 2 holds its 33 data entries, the ties are empty,
 *     nothing registers it, and its progression runs on day ~248 with no match played. The day
 *     loop fills, starts and registers it on the career's first days (q_fill). Nothing in the
 *     game knows 188, 189 or the qualifying rounds: the day loop does the same for them every
 *     summer.
 *   - When they are over, the game's case 2 builds the league phases and the group draw of reg 3
 *     asks access_list, which reads each tie's winner (0x14151b2e0, the read po_finish makes). A
 *     tie without a winner -- a round that could not be played -- sends its seeded club through.
 *   - FL27 (mato 06.11., the design in notes/uefa-q1-srpanj.md): the first qualifying round, in
 *     July, for the Champions League and the Conference League (stage 3, `qround <c> 1 <reg>`,
 *     taken only when g_native_uefa). It is 32 clubs in sixteen ties, and so is the second
 *     qualifying round after it (q_n); its winners go to the second qualifying round, the
 *     Champions League's losers to the Conference League's second (no Europa League second
 *     round in that world: q_down). Its legs are the first Wednesday from 6 July and a week
 *     later (qr_plan), before the season's build on day 216; it is filled right after the July
 *     teardown (q_fill_from: day 181 once the teardown ran, else 182). Its result is kept the
 *     day after its second leg (q1_keep: memory and the state file, kind STATE_Q1), so the
 *     second qualifying round in August is filled from it whatever the build on day 216 or a
 *     restart leave of its ties. A new career starts on 4 August, past it: no first round in a
 *     first season (q_world_p), the second qualifying rounds take 32 new clubs then. Every other
 *     world, and FL26, keeps the three stages exactly as before.
 *   - FL27, Prijedlog C (mato 07.11., qc_world): the Europa League gets a July first round of 16
 *     and a second round of 16, its third round and its play-off hold 32, and so do the Conference
 *     League's second and third rounds and its play-off. The two play-offs of 32 are regulations
 *     of the world's own (`qround 11 0` / `qround 12 0`, q_reg 1 / 2), filled, dated and read as the
 *     qualifying rounds are; 188 and 189 stay February's. Direct entrants 28 / 12 / 4 (cap), the
 *     Europa League play-off's 16 winners into its league phase and its 16 losers into the
 *     Conference League's. A first summer has no July rounds: the qualifying places past the
 *     grown second rounds go to the Conference League's (access_build, c_spill).
 * The eight strongest squads are seeded and listed second, at home in the second leg; the other
 * eight are drawn against them, two clubs of one league kept apart where the draw allows. */
#define Q_N 16                           /* a round of the three summer stages; see q_n, Q_MAX */
typedef struct { uint16_t reg; uint8_t comp, to_win, to_lose; const char* name; } qcup_t;
static const qcup_t QCUPS[NQ] = {
  { 2,       UCLQ,  UCL,  UEL,  "Champions League" },
  { UEL_PO,  UELQ,  UEL,  UECL, "Europa League" },
  { UECL_PO, UECLQ, UECL, 0xff, "Conference League" },
};
static const char* const QSTAGE[NQS] = { "play-off", "third qualifying round", "second qualifying round",
                                         "first qualifying round" };
/* each stage's two legs (0 play-off, 1 third, 2 second qualifying round), a week apart: six
   midweeks in a row from the first one the season's build (day 216) leaves room for, one leg a
   week, so a league plays its weekend round between the legs.  A leg goes on the Wednesday (both
   weekend days three clear), the Tuesday or Thursday where the Wednesday is taken -- the first
   week's Wednesday can be the day after the build, and nothing is filled before 217 -- and a
   second leg on its first leg's weekday where it can.  Each stage is filled on the days between
   the stage before and its first leg (two days at least: a Thursday, then the Tuesday or
   Wednesday after).  The national cups' first round (251 and 254, calendar case 6, the game's
   days) would fall in one of those six weeks in every year; it moves out of them (natcup_day).
   The Champions League play-off's days are reg 2's own
   (is_playoff), the same.  Until 0.2.0 (08.10.) the legs of a stage were two days apart. */
static uint32_t g_qr_leg[NQS][2]; static int g_qr_sy = -1;
/* B463 (Luka 13.11., mato 16.11.: "tjedan dana razmaka"): FL27's August rounds, the second leg a
   week after the first, as UEFA's are. All of it has to fit between the season's build (day 216;
   217 the first day a round is filled, so 218 its first leg at the earliest) and six days before
   FL27's own league phase (its first matchday on day 250 every season, measured: "reg 3 -- FL27's
   own, its 16 date(s) kept: 250 251 257 ..."; the Europa League's on 251) -- the six days
   swiss_day keeps in FL26: the draw that hands their league phase our winners runs on the
   play-offs' second-leg day (case 2, when reg 2 ends), and a play-off winner gets its weekend
   league round between. So 218..244. Every leg on a Tuesday, Wednesday or Thursday (a league's
   Saturday and Sunday stay clear, busy_days), the next round's first leg two days at least after
   the round before's second leg (filled the day between, q_fill_from; the day loop stopped on
   every August day in every log we have), all three competitions on the same days (all three
   play-offs' second legs on one day: the progressions of 188/189 and the world's own play-offs
   run before reg 2's, whose end builds the league phases). Three rounds of a week each need 25
   days (7 + 2 + 7 + 2 + 7) and midweeks: 2026 has Tuesday 11 August to Wednesday 2 September (22),
   2027 Tuesday 10 August to Thursday 2 September (23). So the layout with the longest shortest gap
   (5 days), then the most legs a week apart, then the most days in all: every year from 2026 a
   week in the second qualifying round and the play-off (2026: the play-off 6 days, Thursday 27
   August and Wednesday 2 September), five in the third (Thursday, then Tuesday). 1 when found.
   A career saved in August with the old days (qr_fl27_old) keeps them for the rounds filled then
   (a match's date is its record's, written when the round is filled); the rounds after it are
   filled from the new days -- so the second and third rounds' second legs are never earlier than
   the old ones, and a round is never filled before the old-dated round in front of it is over. */
#define FL27_LP_DAY 250
/* FL27's August days until B463: three weeks from the first Wednesday from 218, each round on its
   Wednesday and Friday (0.2.4 .. beta 4) */
static void qr_fl27_old(int sy, uint32_t leg[3][2])
{
  uint32_t mon = 218;
  while (wday_in(mon, sy) != 2) mon++;   /* dow: 0 = Monday, 2 = Wednesday */
  mon--;
  for (int st = 2; st >= 0; st--) { leg[st][0] = mon + 1; leg[st][1] = mon + 3; mon += 7; }
}
static uint32_t g_qr_old[3][2];
static int qr_fl27_rec(const uint32_t* c, int n, int k, int from, uint32_t* cur, int* best, uint32_t* out)
{
  if (k == 6) {
    if (cur[1] < g_qr_old[2][1] || cur[3] < g_qr_old[1][1]) return 0;   /* a save of the old days */
    int g0 = (int)(cur[1] - cur[0]), g1 = (int)(cur[3] - cur[2]), g2 = (int)(cur[5] - cur[4]);
    int mn = g0 < g1 ? g0 : g1; if (g2 < mn) mn = g2;
    int s[3] = { mn, (g0 == 7) + (g1 == 7) + (g2 == 7), g0 + g1 + g2 };
    if (s[0] > best[0] || (s[0] == best[0] && (s[1] > best[1] || (s[1] == best[1] && s[2] > best[2])))) {
      memcpy(best, s, sizeof s); memcpy(out, cur, 6 * sizeof *cur);
    }
    return 1;
  }
  int any = 0;
  for (int i = from; i < n; i++) {
    uint32_t d = c[i];
    if (k) {
      int g = (int)(d - cur[k - 1]);
      if (g < 2) continue;                        /* never two matches a day apart */
      if ((k & 1) && g > 7) break;                /* a second leg: a week at most after its first */
    }
    cur[k] = d;
    any |= qr_fl27_rec(c, n, k + 1, i + 1, cur, best, out);
  }
  return any;
}
static int qr_fl27(int sy)
{
  uint32_t c[32], cur[6], out[6]; int n = 0, best[3] = { -1, -1, -1 };
  qr_fl27_old(sy, g_qr_old);
  for (uint32_t d = 218; d + 6 <= FL27_LP_DAY && n < 32; d++)
    if (wday_in(d, sy) >= 1 && wday_in(d, sy) <= 3) c[n++] = d;   /* Tuesday .. Thursday */
  if (!qr_fl27_rec(c, n, 0, 0, cur, best, out) || best[0] < 2) return 0;
  for (int st = 2, j = 0; st >= 0; st--, j += 2) { g_qr_leg[st][0] = out[j]; g_qr_leg[st][1] = out[j + 1]; }
  return 1;
}
static uint32_t qr_pick(uint32_t mon, uint32_t first, uint32_t lim, int sy)
{
  /* the leg in the week from Monday mon: Wednesday, Tuesday, Thursday in that order of liking;
     first (a second leg's first leg, or 0): its weekday first, 6..8 days after it; lim (or 0):
     the latest day it may take while another fits */
  static const int PREF[3] = { 2, 1, 3 };
  uint32_t best = 0;
  for (int k = 0; k < 4; k++) {
    uint32_t d = k == 0 ? (first ? first + 7 : 0) : mon + (uint32_t)PREF[k - 1];
    if (!d || d < 218 || d < mon + 1 || d > mon + 3) continue;
    if (first && (d < first + 6 || d > first + 8)) continue;
    if (lim && d > lim && best) continue;
    if (!best || (lim && best > lim && d <= lim)) best = d;
  }
  (void)sy;
  return best ? best : mon + 2;
}
static void qr_plan(void)
{
  int sy = season_year();
  if (sy == g_qr_sy && g_qr_leg[0][0]) return;
  uint32_t d = 218;
  while (d < 230 && (wday_in(d, sy) < 1 || wday_in(d, sy) > 3)) d++;
  uint32_t mon = d - (uint32_t)wday_in(d, sy);
  if (g_native_uefa) {
    /* FL27: their league phase plays its first matchday on day 250 (FL27_LP_DAY) and our six
       weeks put the play-off on 251 and 258, the same days as their first two matchdays, for
       clubs that are in both (31.10.). Until B463 (16.11.) three weeks instead, the legs of a
       round two days apart (meant as Tuesday and Thursday; wday_in counts from Monday, so they
       were Wednesday and Friday: 2026 12/14, 19/21 and 26/28 August). Now qr_fl27: the second
       leg a week after the first where the days between the build and their league phase let
       it, else as near a week as they do (5 or 6 days) -- mato 16.11.: "tjedan dana razmaka" */
    if (!qr_fl27(sy)) memcpy(g_qr_leg, g_qr_old, sizeof g_qr_old);   /* none (2026..2060: never): as before */
    /* the first qualifying round (a world with one, q1_world): the first Wednesday from 6 July
       (186) and the Wednesday after, both clear of the build on day 216 (2026: 8 and 15 July,
       2027: 7 and 14, 2028: 6 and 13) */
    g_qr_leg[3][0] = g_qr_leg[3][1] = 0;
    if (q1_world(0) || q1_world(1) || q1_world(2)) {
      uint32_t w = 186;
      while (wday_in(w, sy) != 2) w++;     /* dow: 0 = Monday, 2 = Wednesday */
      g_qr_leg[3][0] = w; g_qr_leg[3][1] = w + 7;
    }
    g_qr_sy = sy;
    return;
  }
  for (int st = 2; st >= 0; st--) {
    /* the play-off's second leg no later than lets the first league-phase matchday move one
       week at most (swiss_day): two weeks would put it on the second matchday */
    uint32_t a = qr_pick(mon, 0, 0, sy);
    g_qr_leg[st][0] = a;
    g_qr_leg[st][1] = qr_pick(mon + 7, a, st ? 0 : eday(SWISS_DAYS[0]) + 1, sy);
    mon += 14;
  }
  g_qr_sy = sy;
}
static uint32_t qr_day(int stage, int leg) { qr_plan(); return g_qr_leg[stage][leg]; }
/* The league phases' first matchday (SWISS_DAYS 0 and 1): six days after the play-offs' second
   leg at least, so the game's hand-over (case 2, when reg 2 ends) builds them in time -- the
   shipped Tuesday where the six weeks leave room for it, a week later where they do not (2026:
   the play-off on 9 and 16 September, the first matchday on 22 and 23). */
static uint32_t swiss_day(int i)
{
  uint32_t d = eday(SWISS_DAYS[i]);
  if (i < 2) {
    uint32_t md = eday(SWISS_DAYS[0]), last = qr_day(0, 1);
    while (md < last + 6) { md += 7; d += 7; }
  }
  return d;
}
static uint32_t g_q[NQR][Q_MAX]; static unsigned g_nq[NQR], g_nnew[NQR]; static int g_q_day = -100000, g_qmask = 0;
static how_t g_qhow[NQR][Q_MAX];
static unsigned char g_qdrawn[NQR];
static uint32_t g_qwin[NQR][Q_MAX / 2], g_qlose[NQR][Q_MAX / 2];
static how_t g_qwhow[NQR][Q_MAX / 2], g_qlhow[NQR][Q_MAX / 2];
#define QNAME(i) QCUPS[(i) % NQ].name, QSTAGE[(i) / NQ]
static uint16_t q_reg(int i) { return i < NQ ? (g_qreg[i] ? g_qreg[i] : QCUPS[i].reg) : i < NQR ? g_qreg[i] : 0; }
/* the first qualifying round's result, kept the day after its second leg (q1_keep): by the
   game's date (game_date), so a save loaded or a restart sees it as this summer's or not */
typedef struct { int gdate; uint32_t win[Q_MAX / 2], lose[Q_MAX / 2]; } q1kept_t;
static q1kept_t g_q1kept[NQ];
static int q1_kept(int c);

/* B313: take club c out of the list of a competition or round that comes after position o of
   order (lower: the Conference League below the Europa League, a round below the league phase),
   where it went by its position in league reg (not a first-season pick, a cup winner or a round
   already played), so the top-up at o can give it the higher place */
static int lift_from_below(const int* order, int n_order, int o, uint16_t reg, uint32_t c)
{
  for (int o2 = o + 1; o2 < n_order; o2++) {
    int k = order[o2] < 0 ? -1 - order[o2] : -1, qi = order[o2] >= 0 ? order[o2] : -1;
    uint32_t* L = qi < 0 ? g_acc[k] : g_q[qi];
    how_t* H = qi < 0 ? g_how[k] : g_qhow[qi];
    unsigned* N = qi < 0 ? &g_nacc[k] : &g_nq[qi];
    for (unsigned i = 0; i < *N; i++) {
      if (L[i] != c) continue;
      if (H[i].reg != reg || !H[i].rank) return 0;
      static const char* const LP[3] = { "UCL", "UEL", "UECL" };
      char from[64], to[64];
      int tk = order[o] < 0 ? -1 - order[o] : -1, tq = order[o] >= 0 ? order[o] : -1;
      if (qi < 0) snprintf(from, sizeof from, "the %s league phase", LP[k]); else snprintf(from, sizeof from, "the %s %s", QNAME(qi));
      if (tq < 0) snprintf(to, sizeof to, "the %s league phase", LP[tk]); else snprintf(to, sizeof to, "the %s %s", QNAME(tq));
      logf("fl26swiss: access -- reg %u position %u goes up from %s to %s", (unsigned)H[i].reg, (unsigned)H[i].rank, from, to);
      for (unsigned m = i + 1; m < *N; m++) { L[m - 1] = L[m]; H[m - 1] = H[m]; }
      (*N)--;
      return 1;
    }
  }
  return 0;
}
static uint16_t q_tie_of(int i, int k) { return (uint16_t)(q_reg(i) + 1024 * (k + 1)); }
static uint16_t q_tie(int k) { return q_tie_of(0, k); }
/* the competition (0..2) a place's code is a qualifying place of, -1 for any other */
static int q_of_comp(int comp)
{
  for (int p = 0; p < NQ; p++) if (QCUPS[p].comp == comp) return p;
  return -1;
}
static int q_listed(int i)
{
  for (size_t j = 0; j < g_naccess; j++) if (g_access[j].comp == QCUPS[i % NQ].comp) return 1;
  /* FL27's first qualifying round: the Europa League's rounds take the Champions League's losers
     alone, its own places going to the Conference League's first round (access_build) */
  if (i % NQ == 1 && q1_world(0) && q1_world(2)) return 1;
  /* Prijedlog C: every competition's rounds, whatever the lines' codes -- the Conference League's
     new clubs are its direct places past its four (access_build) */
  if (qc_world()) return 1;
  return 0;
}
static uint32_t q_first_leg(int i);
static int q_matches(int p);
/* a first qualifying round is played this summer: it can still be filled (before its first leg),
   or it was (its matches, its kept result). A new career begins on 4 August, after it: its first
   summer has none, and its second qualifying rounds take their 32 new clubs instead */
static int q1_this_summer(int i)
{
  if (q1_kept(i % NQ)) return 1;
  int d = today();
  if (d >= 180 && d < (int)q_first_leg(i)) return 1;
  return d >= 180 && d < 300 && q_matches(i) > 0;
}
/* round i is played in this world: its places are listed and its regulations exist -- a
   qualifying round only in front of its competition's play-off */
static int q_world_p(int i)
{
  if (!g_access_on || !q_reg(i) || !q_listed(i)) return 0;
  if (i >= NQ && !q_world_p(i % NQ)) return 0;
  if (!get_rec(q_reg(i)) || !get_rec(q_tie_of(i, q_n(i) / 2 - 1))) return 0;
  return i < NQ * 3 || q1_this_summer(i);
}
/* why round i is not played, once a season (GitHub #128: a modpack career had no qualifying at
   all, and nothing in the log said which test failed) */
static void q_why(int i)
{
  static int said[NQR], init = 0;
  if (!init) { init = 1; for (int k = 0; k < NQR; k++) said[k] = -1; }
  int y = season_year();
  if (said[i] == y) return;
  said[i] = y;
  const char* why = !g_access_on ? "the access list is off" : !q_reg(i) ? "no regulation named for it"
                  : !q_listed(i) ? "no place of the access list is in it"
                  : i >= NQ && !q_world_p(i % NQ) ? "its play-off is not played"
                  : !get_rec(q_reg(i)) ? "its regulation is not found"
                  : !get_rec(q_tie_of(i, q_n(i) / 2 - 1)) ? "its last tie is not found"
                  : "a first qualifying round is played from a career's second summer, before its first leg";
  logf("fl26swiss: %s %s not played this season: %s (reg %u, tie %u, day %d)", QNAME(i), why,
       (unsigned)q_reg(i), (unsigned)q_tie_of(i, q_n(i) / 2 - 1), today());
}
static int q_world(void) { return q_world_p(0); }
static int q_world_mask(void)
{
  int m = 0;
  for (int i = 0; i < NQR; i++) if (q_world_p(i)) m |= 1 << i;
  return m;
}
/* with the rounds of mask: where round i's winners go (the next round of its competition, -1
   the league phase), where its losers go (a round, -1 the league phase below -- the play-offs',
   QCUPS.to_lose --, -2 out), and how many new entrants it takes */
static int q_up(int mask, int i)
{
  for (int j = i - NQ; j >= 0; j -= NQ) if (mask >> j & 1) return j;
  return -1;
}
static int q_down(int mask, int i)
{
  int p = i % NQ, s = i / NQ;
  if (p == NQ - 1) return -2;
  if (!s) return -1;
  int j = p + 1 + NQ * (s - 1);
  /* a first qualifying round's losers: the Europa League's second qualifying round, or with none
     (FL27's world) the Conference League's, as UEFA's champions path does */
  if (s == 3 && ((qc_world() && !p) || !(mask >> j & 1))) j = NQ - 1 + NQ * 2;   /* C: UCL Q1 -> UECL Q2 always */
  return mask >> j & 1 ? j : -2;
}
static unsigned q_room(int mask, int i)
{
  int n = (int)q_n(i);
  for (int j = 0; j < NQR; j++)
    if (j != i && (mask >> j & 1) && (q_up(mask, j) == i || q_down(mask, j) == i)) n -= (int)q_n(j) / 2;
  return n > 0 ? (unsigned)n : 0;
}
/* the first leg of round i, and the first day it is filled on: after the last second leg of the
   rounds that feed it, never before the season's build on day 216 (reg 2 alone, in a new career
   that starts before it: from 205) */
static uint32_t q_first_leg(int i) { return qr_day(i / NQ, 0); }
/* the July teardown's abs_day this session (teardown_pre), -1 none */
static int g_td_abs = -1;
static uint32_t q_fill_from(int mask, int i)
{
  /* the first qualifying round: right after the July teardown that cleared last summer's ties
     (day 181, the day loop's check), else from the day after it */
  if (i >= NQ * 3) return g_td_abs >= 0 && abs_day() - g_td_abs >= 0 && abs_day() - g_td_abs < 30 ? 181 : 182;
  uint32_t d = 0;
  for (int j = 0; j < NQR; j++)
    if (j != i && (mask >> j & 1) && (q_up(mask, j) == i || q_down(mask, j) == i)) {
      /* and after the second leg the round before had until 0.2.0 (225, 236): a save of then,
         its rounds dated the old way, is not filled before they are over */
      uint32_t e = qr_day(j / NQ, 1) + 1, old = j / NQ == 2 ? 226 : 237;
      if (e < old && !g_native_uefa) e = old;      /* FL27: no save of then; its weeks are shorter */
      if (e > d) d = e;
    }
  if (d && d < 217) d = 217;             /* after a July first qualifying round: past the build too */
  return d ? d : i ? 217 : 205;
}

/* c is on competition k's list as a title holder (the reg 4, 6 or 187 winner itself, not the
   big-five club that stands in while no holder is known) */
static int holder_in(int k, uint32_t c)
{
  for (unsigned j = 0; j < g_nacc[k]; j++) {
    uint16_t r = g_how[k][j].reg;
    if (same_club(g_acc[k][j], c) && !g_how[k][j].rank && (r == R_UCLKO || r == R_UELKO || r == UECL_KO)) {
      uint32_t w = cup_winner(r);
      return w && same_club(w, c);
    }
  }
  return 0;
}
/* c is one of the clubs of league reg (a final table, the first-season order or the list) */
static int in_league(uint16_t reg, uint32_t c)
{
  int ft;
  for (int rank = 1; rank <= FINAL_MAX; rank++) {
    uint32_t x = access_club(reg, rank, &ft);
    if (!x) return 0;
    if (same_club(x, c)) return 1;
  }
  return 0;
}

/* B281: competition k's places league reg has on the access list (its positions and the cups
   whose next place it is; not a title holder's), and its clubs on k's lists (the league phase and
   k's qualifying rounds) */
static int nat_places(int k, uint16_t reg)
{
  int n = 0;
  for (size_t i = 0; i < g_naccess; i++) {
    const access_t* a = &g_access[i];
    int ak = q_of_comp(a->comp) >= 0 ? q_of_comp(a->comp) : a->comp;
    if (ak != k) continue;
    if (!a->rank && (a->reg == R_UCLKO || a->reg == R_UELKO || a->reg == UECL_KO)) continue;
    if (a->rank ? a->reg == reg : a->alt == reg) n++;
  }
  return n;
}
static int nat_count(int k, uint16_t reg)
{
  int n = 0;
  if (k < 0 || k > 2) return 0;
  for (unsigned i = 0; i < g_nacc[k]; i++)
    if (g_how[k][i].reg == reg || in_league(reg, g_acc[k][i])) n++;
  for (int qi = k; qi < NQR; qi += NQ)
    for (unsigned i = 0; i < g_nq[qi]; i++)
      if (g_qhow[qi][i].reg == reg || in_league(reg, g_q[qi][i])) n++;
  return n;
}

static int q_matches(int p);
static int q_summer(void);
/* build the lists; a slot whose club is missing or already placed takes the next position of the
   same league. q: 0 no qualifying (36 direct entrants each), 1 also the rounds' new entrants (g_q),
   2 the rounds' clubs are known (g_q) and are not placed again. mask: the rounds on (bit i); a
   competition's places past its direct entrants go to its own rounds when it has them */
static void career_mark(const char* where);
static int access_build(int q, int mask)
{
  career_mark("the access list");
  uint32_t used[3 * FIELD + NQR * Q_MAX + 8]; unsigned nused = 0; int tables = 0, orders = 0, gaps = 0, listed = 0, held = 0;
  int on[NQR]; unsigned room[NQR];
  for (int i = 0; i < NQR; i++) { on[i] = q && (mask >> i & 1); room[i] = on[i] ? q_room(mask, i) : 0; }
  unsigned cap[3] = { FIELD, FIELD, FIELD };
  for (int p = 0; p < NQ; p++) {
    if (!on[p]) continue;
    cap[QCUPS[p].to_win] -= q_n(p) / 2;           /* Prijedlog C: 28 / 12 / 4 direct */
    if (QCUPS[p].to_lose != 0xff) cap[QCUPS[p].to_lose] -= q_n(p) / 2;
  }
  g_nacc[0] = g_nacc[1] = g_nacc[2] = 0;
  for (int i = 0; i < NQR; i++) {
    if (q == 1 && on[i]) { g_nq[i] = 0; g_qdrawn[i] = 0; }
    if (q == 2 && on[i]) for (unsigned j = 0; j < g_nq[i]; j++) if (!has_club(used, nused, g_q[i][j])) used[nused++] = g_q[i][j];
  }
  /* A round the game already plays this summer -- filled before a restart, its ties holding this
     summer's matches -- keeps the clubs it has: they are placed first, as they are, and no place
     of the list goes to one of them again. The rounds live in memory only, so after a restart the
     build drew every round afresh and placed the clubs it did not draw again (13.10.: a save
     loaded on day 232, the play-offs built on day 246 put Tirana, in the Conference League's
     second qualifying round, into the Champions League play-off as well). A round's new entrants
     are its clubs that no round feeding it holds. */
  if (q == 1 && q_summer()) {
    uint32_t qt[NQR][Q_MAX]; int filled[NQR], kept = 0;
    for (int i = 0; i < NQR; i++) {
      filled[i] = on[i] && q_matches(i) > 0;
      for (int k = 0; k < (int)q_n(i) / 2 && filled[i]; k++) {
        unsigned char* t = get_rec(q_tie_of(i, k));
        if (!t || rec_count(t) != 2) filled[i] = 0;
        else { qt[i][2 * k] = rec_clubs(t)[0]; qt[i][2 * k + 1] = rec_clubs(t)[1]; }
      }
      /* a first qualifying round already played: its kept result, whatever its ties hold now */
      if (on[i] && i >= NQ * 3 && q1_kept(i % NQ)) {
        const q1kept_t* K = &g_q1kept[i % NQ];
        for (unsigned k = 0; k < q_n(i) / 2; k++) { qt[i][2 * k] = K->win[k]; qt[i][2 * k + 1] = K->lose[k]; }
        filled[i] = 1;
      }
    }
    for (int i = 0; i < NQR; i++) {
      if (!filled[i]) continue;
      for (int n = 0; n < (int)q_n(i); n++) {
        uint32_t c = qt[i][n];
        if (!(c >> 14) || has_club(used, nused, c)) continue;
        used[nused++] = c;
        int fed = 0;
        for (int j = 0; j < NQR && !fed; j++)
          if (j != i && filled[j] && (q_up(mask, j) == i || q_down(mask, j) == i)) fed = has_club(qt[j], q_n(j), c);
        if (!fed && g_nq[i] < room[i]) {
          g_qhow[i][g_nq[i]].reg = q_reg(i); g_qhow[i][g_nq[i]].rank = 0;
          g_q[i][g_nq[i]++] = c;
        }
      }
      kept++;
    }
    if (kept) logf("fl26swiss: access -- %d qualifying round(s) already played this summer keep their clubs", kept);
  }
  if (g_nfirst[0] + g_nfirst[1] + g_nfirst[2] && !any_final_kept() && !g_new_career) {
    static int said = 0;
    if (!said++) logf("fl26swiss: first-season list -- not a career built in this session; the list is left out");
  }
  /* A career built in this session takes the list in its first European summer. A January
     league's career has a final table of its own by then (2026-10-05: CSL, kept on day 176), so
     the final tables do not tell the first summer from a later one there: the day of the first
     use does -- every build within 120 days of it is the same summer. A save of a later summer
     loaded on days 210-240 can look like a career built in this session; last season's tables
     read back from the save folder (state_sync, B49) say it is not. */
  /* the round of competition p a new entrant goes to: the one nearest the league phase with room */
  #define QSLOT(p, out) do { out = -1; for (int s_ = 0; s_ < NQS && out < 0; s_++) { int i_ = (p) + NQ * s_; \
      if (on[i_] && g_nq[i_] < room[i_]) out = i_; } } while (0)
  /* the farthest from the league phase with room (Prijedlog C's first summer, below) */
  #define QSLOT_FAR(p, out) do { out = -1; for (int s_ = NQS - 1; s_ >= 0 && out < 0; s_--) { int i_ = (p) + NQ * s_; \
      if (on[i_] && g_nq[i_] < room[i_]) out = i_; } } while (0)
  /* Prijedlog C without its July first rounds this summer (a career's first): their room went to
     the second rounds (q_room), so the Champions League's 56 and the Europa League's 40 new clubs
     meet rounds that take 40 and 32 -- the rest, the weakest, go where the first rounds' losers
     would have, the Conference League's second round (as far from the league phase as there is
     room), up to the 16 and 8 losers those rounds would have sent */
  int c_spill[2] = { 0, 0 }, c_spilled = 0;
  if (q == 1 && qc_world()) {
    if (!on[NQ * 3] && g_qreg[NQ * 3]) c_spill[0] = (int)q_n(NQ * 3) / 2;
    if (!on[NQ * 3 + 1] && g_qreg[NQ * 3 + 1]) c_spill[1] = (int)q_n(NQ * 3 + 1) / 2;
  }
  int first_summer = g_new_career && !g_st_read_back && (g_first_day < 0 || abs_day() - g_first_day < 120)
                     && !first_summer_over();
  if (g_nfirst[0] + g_nfirst[1] + g_nfirst[2] && first_summer) {
    int missing = 0, twice = 0, over = 0, inq = 0;
    if (g_first_day < 0) g_first_day = abs_day();
    for (int k = 0; k < 3; k++)
      for (unsigned i = 0; i < g_nfirst[k]; i++) {
        uint32_t c = club_of_id(g_first[k][i]);
        if (!c) { missing++; logf("fl26swiss: first-season list -- team %u is not in any league of this game", g_first[k][i]); continue; }
        if (has_club(used, nused, c)) { twice++; continue; }
        if (g_nacc[k] >= cap[k]) {
          /* B284 (Daemon, 29.10.): a list of 36 for the Champions League, and the summer's
             qualifying takes eight of its places -- the last eight got none. They go to the
             competition's own qualifying now, the round nearest the league phase with room,
             as a place past the direct entrants does below */
          int qi = -1;
          if (q == 1) QSLOT(k, qi);
          if (qi < 0) { over++; continue; }
          g_qhow[qi][g_nq[qi]].reg = 0; g_qhow[qi][g_nq[qi]].rank = 0;
          g_q[qi][g_nq[qi]++] = c; used[nused++] = c; listed++; inq++;
          continue;
        }
        g_how[k][g_nacc[k]].reg = 0; g_how[k][g_nacc[k]].rank = 0;
        g_acc[k][g_nacc[k]++] = c; used[nused++] = c; listed++;
      }
    logf("fl26swiss: first-season list -- %u / %u / %u clubs taken (%d into the qualifying rounds, %d not in this game, %d listed twice, %d over %d)",
         g_nacc[0], g_nacc[1], g_nacc[2], inq, missing, twice, over, FIELD);
  }
  for (size_t i = 0; i < g_naccess; i++) {
    const access_t* a = &g_access[i];
    int qp = q_of_comp(a->comp), qi = -1;
    if (qp >= 0 ? q != 1 : a->comp > UECL) continue;   /* the other continents: cont_build below */
    if (qp >= 0) {
      QSLOT(qp, qi);
      /* FL27's first qualifying round: no Europa League round takes new clubs (its third takes
         the Champions League's second round losers), so its places go to the Conference
         League's rounds, as at UEFA since 2024 */
      if (qi < 0 && qp == 1 && q1_world(2) && !qc_world()) QSLOT(2, qi);   /* Prijedlog C (and wide): c_spill below */
      if (qi < 0 && qp <= 1 && c_spill[qp] > 0) { QSLOT_FAR(2, qi); if (qi >= 0) { c_spill[qp]--; c_spilled++; } }
      if (qi < 0) continue;
    }
    uint32_t c = 0; int ft = 0;
    uint16_t reg = a->reg; int first = a->rank;
    if (!first) {                                   /* cup winner, or the alt league's next place */
      c = cup_winner(reg);
      if (c && !has_club(used, nused, c)) ft = 1;
      else if (c && (reg == R_UCLKO || reg == R_UELKO || reg == UECL_KO)) {
        /* B281 (pepponeee, 29.10.; mato: "as in reality"): a title holder already in through its
           league leaves its place to the top-up, as at UEFA -- given to its alt league (Italy for
           the Conference League's) it put an eighth Italian club in Europe */
        held++;
        continue;
      }
      else { c = 0; reg = a->alt; first = a->alt ? 1 : FINAL_MAX + 1; }
    }
    int vacated = 0;
    for (int rank = first; !c && rank <= FINAL_MAX; rank++) {
      c = access_club(reg, rank, &ft);
      if (!c) break;
      if (!(c >> 14) || has_club(used, nused, c)) {
        if (a->rank && qp < 0 && holder_in(a->comp, c)) { c = 0; vacated = 1; break; }
        c = 0; continue;
      }
      break;
    }
    if (vacated) { held++; continue; }
    if (!c) { gaps++; logf("fl26swiss: access -- reg %u %s %u: no club", (unsigned)a->reg, a->rank ? "position" : "winner", (unsigned)a->rank); continue; }
    if (nused >= sizeof used / sizeof used[0]) continue;
    if (qp < 0 && g_nacc[a->comp] >= cap[a->comp]) {
      /* a place past the direct entrants goes to the competition's own qualifying (UCL to the
         Champions League's, ...); the list has them before the rounds' own places, so they come
         ahead of the weakest shipped ones */
      if (q == 1) QSLOT(a->comp, qi);
      if (qi < 0) continue;
    }
    if (qi >= 0) {
      g_qhow[qi][g_nq[qi]].reg = a->reg; g_qhow[qi][g_nq[qi]].rank = a->rank;
      g_q[qi][g_nq[qi]++] = c; used[nused++] = c;
      if (ft) tables++; else orders++;
      continue;
    }
    g_how[a->comp][g_nacc[a->comp]].reg = a->reg; g_how[a->comp][g_nacc[a->comp]].rank = (uint8_t)(a->rank ? a->rank : 0);
    g_acc[a->comp][g_nacc[a->comp]++] = c;
    used[nused++] = c;
    if (ft) tables++; else orders++;
  }
  #undef QSLOT
  #undef QSLOT_FAR
  if (c_spilled) logf("fl26swiss: access -- %d qualifying place(s) into the Conference League's rounds: no July first round this summer", c_spilled);
  /* top-up: the next free positions of the big five, the league with the fewest clubs on the
     list first (ties in this order), so a place a holder left does not go back to its own country
     and no association crowds a league phase past what the draw can keep apart */
  static const uint16_t RESERVE[5] = { R_ENG, R_ESP, R_ITA, R_GER, R_FRA };
  int topped = 0, lifted = 0;
  /* each competition, then its rounds from the play-off down: -1 - k is league phase k */
  static const int ORDER[NQ + NQR] = { -1, 0, 3, 6, 9, -2, 1, 4, 7, 10, -3, 2, 5, 8, 11 };
  for (int o = 0; o < NQ + NQR; o++) {
    int k = ORDER[o] < 0 ? -1 - ORDER[o] : -1, qi = ORDER[o] >= 0 ? ORDER[o] : -1;
    uint32_t* L = qi < 0 ? g_acc[k] : g_q[qi];
    how_t* H = qi < 0 ? g_how[k] : g_qhow[qi];
    unsigned* N = qi < 0 ? &g_nacc[k] : &g_nq[qi];
    unsigned C = qi < 0 ? cap[k] : q == 1 && on[qi] ? room[qi] : 0;
    int rank[5] = { 1, 1, 1, 1, 1 }, done[5] = { 0 }, cnt[5] = { 0 }, room5[5] = { 0 };
    if (*N < C)
      for (unsigned i = 0; i < *N; i++)
        for (int j = 0; j < 5; j++)
          if (H[i].reg == RESERVE[j] || in_league(RESERVE[j], L[i])) { cnt[j]++; break; }
    /* B281 (mato: "as in reality"): no association past its own places while another of the five
       has one free -- a Serie A of 4 + 2 + 1 places got a ninth club in Europe from here. A league
       with a place still free (its cup winner gone up, a holder's place left) comes first; only
       when none has, the fewest clubs first as before, so each competition still gets its 36 */
    int capped = 0;
    if (*N < C) {
      int k3 = qi < 0 ? k : qi % NQ;
      for (int j = 0; j < 5; j++) {
        room5[j] = nat_places(k3, RESERVE[j]) - nat_count(k3, RESERVE[j]);
        if (room5[j] > 0) capped = 1;
      }
    }
    while (*N < C && nused < sizeof used / sizeof used[0]) {
      int j = -1;
      for (int r = 0; r < 5; r++) if (!done[r] && (!capped || room5[r] > 0) && (j < 0 || cnt[r] < cnt[j])) j = r;
      if (j < 0 && capped) { capped = 0; continue; }
      if (j < 0) break;
      uint32_t c = 0; int ft = 0;
      int up = 0;
      while (rank[j] <= FINAL_MAX) {
        c = access_club(RESERVE[j], rank[j]++, &ft);
        if (!c) break;
        if ((c >> 14) && !has_club(used, nused, c)) break;
        /* B313 (pepponeee 03.11.): a club of this league already in a lower competition or round
           by its position goes up first, as at UEDA's rebalancing, and its place there is topped
           up in turn -- Brighton (8th) took the Europa League place while Villa (7th) stayed in
           the Conference League */
        if ((c >> 14) && lift_from_below(ORDER, NQ + NQR, o, RESERVE[j], c)) { up = 1; break; }
        c = 0;
      }
      if (!c) { done[j] = 1; continue; }
      H[*N].reg = RESERVE[j]; H[*N].rank = (uint8_t)(rank[j] - 1);
      L[(*N)++] = c; topped++; cnt[j]++; room5[j]--;
      if (up) lifted++; else used[nused++] = c;
    }
  }
  if (held) logf("fl26swiss: access -- %d league place(s) left by a title holder, given to the top-up", held);
  if (topped) logf("fl26swiss: access -- %d place(s) topped up from the big five (%d by a club going up from a lower competition)", topped, lifted);
  char qs[96] = "";
  if (q == 1) {
    int n = snprintf(qs, sizeof qs, ", qualifying");
    for (int i = 0; i < NQR && n < (int)sizeof qs - 8; i++) if (on[i]) n += snprintf(qs + n, sizeof qs - n, " %u", g_nq[i]);
  } else if (q == 2) snprintf(qs, sizeof qs, " direct, the qualifying rounds' clubs left out");
  logf("fl26swiss: access -- %u / %u / %u clubs%s (%d from the first-season list, %d positions from last season's tables, %d from first-season order, %d missing)",
       g_nacc[0], g_nacc[1], g_nacc[2], qs, listed, tables, orders, gaps);
  {                                /* B281: the big five's clubs per competition against their places */
    static const uint16_t BIG5[5] = { R_ENG, R_ESP, R_ITA, R_GER, R_FRA };
    char bs[256]; int bn = 0;
    for (int j = 0; j < 5 && bn < (int)sizeof bs - 40; j++)
      bn += snprintf(bs + bn, sizeof bs - bn, " reg %u %d/%d %d/%d %d/%d;", (unsigned)BIG5[j],
                     nat_count(0, BIG5[j]), nat_places(0, BIG5[j]), nat_count(1, BIG5[j]), nat_places(1, BIG5[j]),
                     nat_count(2, BIG5[j]), nat_places(2, BIG5[j]));
    logf("fl26swiss: access -- the big five, clubs/places in the three competitions:%s", bs);
  }
  for (int i = 0; i < NQR; i++) {
    if (q == 1 && on[i]) g_nnew[i] = g_nq[i];
    if (q == 1 && on[i] && g_nq[i] < room[i]) logf("fl26swiss: access -- the %s %s has only %u of its %u new club(s)", QNAME(i), g_nq[i], room[i]);
  }
  return g_nacc[0] == cap[0];
}

/* a round's draw: g_q[i] (with g_qhow[i]) into eight ties, tie k = g_q[i][2k] v g_q[i][2k+1], seeded second */
static uint32_t q_rand(uint32_t n) { coin(); return n ? g_rng % n : 0; }
static void q_draw(int p)
{
  unsigned char* o = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
  void* blk = o ? *(void**)(o + 0x48) : 0;
  uint32_t* Q = g_q[p]; how_t* QH = g_qhow[p];
  const unsigned N = q_n(p);
  int str[Q_MAX]; unsigned idx[Q_MAX];
  for (unsigned i = 0; i < N; i++) { idx[i] = i; str[i] = blk ? club_strength(blk, Q[i]) : 0; }
  for (unsigned i = 1; i < N; i++)                 /* strongest first, stable */
    for (unsigned j = i; j > 0 && str[idx[j - 1]] < str[idx[j]]; j--) { unsigned t = idx[j]; idx[j] = idx[j - 1]; idx[j - 1] = t; }
  unsigned* seed = idx; unsigned* un = idx + N / 2;
  for (unsigned i = N / 2 - 1; i > 0; i--) { unsigned j = q_rand(i + 1), t = un[i]; un[i] = un[j]; un[j] = t; }
  #define QLG(x) (QH[x].reg)
  for (unsigned k = 0; k < N / 2; k++) {          /* two clubs of one league apart */
    if (!QLG(un[k]) || QLG(un[k]) != QLG(seed[k])) continue;
    for (unsigned j = 0; j < N / 2; j++) {
      if (j == k || QLG(un[j]) == QLG(seed[k]) || (QLG(un[k]) && QLG(un[k]) == QLG(seed[j]))) continue;
      unsigned t = un[k]; un[k] = un[j]; un[j] = t;
      break;
    }
  }
  #undef QLG
  uint32_t c[Q_MAX]; how_t h[Q_MAX];
  for (unsigned k = 0; k < N / 2; k++) {
    c[2 * k] = Q[un[k]]; h[2 * k] = QH[un[k]];
    c[2 * k + 1] = Q[seed[k]]; h[2 * k + 1] = QH[seed[k]];
  }
  memcpy(Q, c, N * sizeof c[0]); memcpy(QH, h, N * sizeof h[0]);
}
static void q_draw_log(int i)
{
  q_draw(i);
  g_qdrawn[i] = 1;
  for (unsigned k = 0; k < q_n(i) / 2; k++)
    logf("fl26swiss:   %s %s tie %u: reg %u position %u (%08x) v reg %u position %u (%08x, seeded)", QNAME(i), k,
         (unsigned)g_qhow[i][2 * k].reg, (unsigned)g_qhow[i][2 * k].rank, g_q[i][2 * k],
         (unsigned)g_qhow[i][2 * k + 1].reg, (unsigned)g_qhow[i][2 * k + 1].rank, g_q[i][2 * k + 1]);
}
/* this summer's qualifying: every round's new entrants, and the rounds nothing feeds drawn; built
   once and kept for 60 days. Answers the rounds built (bit i), 0 when there are none or the
   Champions League list came out short */
static int q_prepare(void)
{
  int ad = abs_day();
  /* 60 days; 75 with a July first qualifying round (built from day 181, its play-offs to ~236) */
  int keep = (g_qmask >> (NQ * 3)) ? 75 : 60;
  if (g_qmask && ad >= g_q_day && ad - g_q_day < keep) return g_qmask;
  int mask = q_world_mask();
  if (!mask) return 0;
  if (!access_build(1, mask)) {
    for (int i = 0; i < NQR; i++) g_nq[i] = g_nnew[i] = 0;
    logf("fl26swiss: qualifying -- the access list came out short; the game's own play-off stands");
    return 0;
  }
  g_qmask = 0;
  for (int i = 0; i < NQR; i++) {
    if (!(mask >> i & 1)) continue;
    unsigned room = q_room(mask, i);
    if (g_nq[i] < room) { g_nq[i] = g_nnew[i] = 0; logf("fl26swiss: %s %s left out: short of clubs", QNAME(i)); continue; }
    g_qmask |= 1 << i;
    if (room == q_n(i)) q_draw_log(i);
    else logf("fl26swiss: %s %s -- %u new club(s), the other %u from the rounds before it", QNAME(i), room, q_n(i) - room);
  }
  g_q_day = ad;
  return g_qmask;
}
static int ccup_matches(uint16_t reg);
/* matches this summer under a round's regulation and its ties; -1 when the match table cannot be read */
static int q_matches(int p)
{
  int m = ccup_matches(q_reg(p));
  if (m < 0) return -1;
  for (int k = 0; k < (int)q_n(p) / 2; k++) { int x = ccup_matches(q_tie_of(p, k)); if (x > 0) m += x; }
  return m;
}
static int q_complete(int i);
/* where round i's winners (lose 0) or losers (1) went, for the log */
static const char* q_dest(int i, int lose, char* buf, size_t cap)
{
  int m = g_qmask ? g_qmask : q_world_mask(), j = lose ? q_down(m, i) : q_up(m, i);
  if (j >= 0) snprintf(buf, cap, "to the %s %s", QNAME(j));
  else if (j == -2) snprintf(buf, cap, "out");
  else snprintf(buf, cap, "to the %s", COMP_NAME[lose ? QCUPS[i % NQ].to_lose : QCUPS[i % NQ].to_win]);
  return buf;
}
/* after a round: the sixteen as the ties hold them, and who went through. 0 when there is no
   round of ours to read and none can be built */
static int q_result(int p)
{
  const int N = (int)q_n(p);
  uint32_t pr[Q_MAX]; how_t ph[Q_MAX]; int ties = 1, nodec = 0;
  if (p >= NQ * 3 && q1_kept(p % NQ)) {
    /* a July first qualifying round: what was kept the day after its second leg (q1_keep) -- the
       build on day 216 and a restart leave its ties as they may */
    const q1kept_t* K = &g_q1kept[p % NQ];
    for (int k = 0; k < N / 2; k++) {
      g_qwin[p][k] = K->win[k]; g_qlose[p][k] = K->lose[k];
      g_qwhow[p][k].reg = g_qlhow[p][k].reg = q_reg(p); g_qwhow[p][k].rank = g_qlhow[p][k].rank = 0;
      for (unsigned j = 0; j < g_nq[p] && j < Q_MAX; j++) {
        if (same_club(g_q[p][j], K->win[k])) g_qwhow[p][k] = g_qhow[p][j];
        if (same_club(g_q[p][j], K->lose[k])) g_qlhow[p][k] = g_qhow[p][j];
      }
    }
    static int said[NQ], sk = -1000;
    { int k_ = log_season(); if (k_ != sk) { sk = k_; memset(said, 0, sizeof said); } }
    if (!said[p % NQ]++) {
      char wto[96], lto[96];
      q_dest(p, 0, wto, sizeof wto); q_dest(p, 1, lto, sizeof lto);
      logf("fl26swiss: %s %s -- its kept result: %d winners %s, %d losers %s", QNAME(p), N / 2, wto, N / 2, lto);
    }
    return 1;
  }
  /* the added rounds keep last summer's (or February's) two clubs in each tie until refilled:
     their ties count only with this summer's matches (the July teardown deletes the old ones) */
  if (p && q_matches(p) <= 0) ties = 0;
  for (int k = 0; k < N / 2 && ties; k++) {
    unsigned char* t = get_rec(q_tie_of(p, k));
    if (!t || rec_count(t) != 2) ties = 0;
    else { pr[2 * k] = rec_clubs(t)[0]; pr[2 * k + 1] = rec_clubs(t)[1]; }
  }
  if (ties) {
    int same = g_nq[p] == (unsigned)N;
    for (int i = 0; i < N && same; i++) same = has_club(g_q[p], N, pr[i]);
    if (!same) {                                    /* after a restart, or the game's own clubs */
      logf("fl26swiss: %s %s -- the ties hold clubs this session did not draw; taken as they are", QNAME(p));
      memcpy(g_q[p], pr, N * sizeof pr[0]); g_nq[p] = N; g_qdrawn[p] = 1;
      for (int i = 0; i < N; i++) { g_qhow[p][i].reg = q_reg(p); g_qhow[p][i].rank = (uint8_t)(i + 1); }
    }
    for (int i = 0; i < N; i++) {                   /* where each came from, in the ties' order */
      ph[i].reg = q_reg(p); ph[i].rank = 0;
      for (int j = 0; j < N; j++) if (same_club(g_q[p][j], pr[i])) { ph[i] = g_qhow[p][j]; break; }
    }
  } else {
    if (!q_complete(p)) return 0;
    memcpy(pr, g_q[p], N * sizeof pr[0]); memcpy(ph, g_qhow[p], N * sizeof ph[0]);
    logf("fl26swiss: %s %s -- the ties were never filled (not played); the seeded clubs go through", QNAME(p));
  }
  char wto[96], lto[96];
  q_dest(p, 0, wto, sizeof wto); q_dest(p, 1, lto, sizeof lto);
  for (int k = 0; k < N / 2; k++) {
    uint32_t w = 0;
    if (ties) ((winner_fn)(uintptr_t)(g_base + WINNER_RVA))(&w, q_tie_of(p, k));
    int i = !(w >> 14) ? -1 : same_club(w, pr[2 * k]) ? 0 : same_club(w, pr[2 * k + 1]) ? 1 : -1;
    if (i < 0) { i = 1; nodec++; }
    g_qwin[p][k] = pr[2 * k + i]; g_qlose[p][k] = pr[2 * k + (i ^ 1)];
    g_qwhow[p][k] = ph[2 * k + i]; g_qlhow[p][k] = ph[2 * k + (i ^ 1)];
    logf("fl26swiss:   %s %s tie %d: %08x through %s, %08x %s%s", QNAME(p), k, g_qwin[p][k], wto, g_qlose[p][k], lto,
         w >> 14 ? "" : " (no winner read: the seeded club)");
  }
  if (ties && nodec) logf("fl26swiss: %s %s -- %d tie(s) without a winner", QNAME(p), nodec);
  return ties ? 1 : 2;
}
/* round i's sixteen: its new entrants, then the winners of the round before it in its
   competition and the losers of the one that drops into it; drawn. 1 when it has them */
static int q_complete(int i)
{
  int mask = q_prepare();
  if (!(mask >> i & 1)) return 0;
  if (g_qdrawn[i]) return 1;
  g_nq[i] = g_nnew[i];
  for (int j = 0; j < NQR; j++) {
    if (j == i || !(mask >> j & 1)) continue;
    int win = q_up(mask, j) == i, lose = q_down(mask, j) == i;
    if (!win && !lose) continue;
    if (!q_result(j)) {
      logf("fl26swiss: %s %s -- no result of the %s %s to fill it from", QNAME(i), QNAME(j));
      g_nq[i] = g_nnew[i];
      return 0;
    }
    for (int k = 0; k < (int)q_n(j) / 2 && g_nq[i] < q_n(i); k++) {
      g_qhow[i][g_nq[i]] = win ? g_qwhow[j][k] : g_qlhow[j][k];
      g_q[i][g_nq[i]++] = win ? g_qwin[j][k] : g_qlose[j][k];
    }
  }
  if (g_nq[i] < q_n(i)) {
    logf("fl26swiss: %s %s -- only %u club(s); not played", QNAME(i), g_nq[i]);
    g_nq[i] = g_nnew[i];
    return 0;
  }
  q_draw_log(i);
  return 1;
}
/* competition c's first qualifying round was kept this summer (the game's date: within 100 days
   after it, not after today -- a save of an earlier day leaves it out) */
static void state_sync(void);
static void state_store(void);
static int q1_kept(int c)
{
  if (c < 0 || c >= NQ || !q1_world(c)) return 0;
  state_sync();                                    /* a restart or a load: the state file's */
  int gd = game_date(), k = g_q1kept[c].gdate;
  return k > 0 && gd >= k && gd - k < 100;
}
/* the day loop, from the day after the first qualifying round's second leg: its winners and
   losers, read from the ties once, kept in memory and in the state file (STATE_Q1) for the
   second qualifying round in August -- the season's build on day 216 comes between */
static void q1_keep(void)
{
  int d = today();
  for (int c = 0; c < NQ; c++) {
    int i = c + NQ * 3;
    if (!q1_world(c) || d <= (int)qr_day(3, 1) || d > 260 || q1_kept(c)) continue;
    static int tried[NQ] = { -1, -1, -1 };
    int y = (abs_day() + 183) / 365;
    if (tried[c] == y) continue;
    if (!q_world_p(i) || q_matches(i) <= 0) continue;   /* not played: nothing to keep */
    tried[c] = y;
    if (q_result(i) != 1) {
      logf("fl26swiss: %s %s -- day %d: no result read from its ties; not kept", QNAME(i), d);
      continue;
    }
    q1kept_t* K = &g_q1kept[c];
    K->gdate = game_date();
    for (unsigned k = 0; k < q_n(i) / 2; k++) { K->win[k] = g_qwin[i][k]; K->lose[k] = g_qlose[i][k]; }
    logf("fl26swiss: %s %s -- day %d: result kept (%u winners, %u losers) for the second qualifying round",
         QNAME(i), d, q_n(i) / 2, q_n(i) / 2);
    state_store();
  }
}
/* the winners into their competition, the losers into the one below: the Champions League's
   play-off first, so each list reads direct entrants, then the play-off above's losers, then its
   own play-off's winners */
static void q_place(int mask)
{
  for (int p = 0; p < NQ; p++) {
    if (!(mask >> p & 1)) continue;
    for (int k = 0; k < (int)q_n(p) / 2; k++) {
      int w = QCUPS[p].to_win, l = QCUPS[p].to_lose;
      if (g_nacc[w] < FIELD) { g_how[w][g_nacc[w]].reg = QCUPS[p].reg; g_how[w][g_nacc[w]].rank = (uint8_t)(k + 1); g_acc[w][g_nacc[w]++] = g_qwin[p][k]; }
      if (l != 0xff && g_nacc[l] < FIELD) { g_how[l][g_nacc[l]].reg = QCUPS[p].reg; g_how[l][g_nacc[l]].rank = (uint8_t)(k + 1); g_acc[l][g_nacc[l]++] = g_qlose[p][k]; }
    }
  }
  logf("fl26swiss: access -- with the play-offs: %u / %u / %u clubs", g_nacc[0], g_nacc[1], g_nacc[2]);
}
/* the summer's qualifying: from the July rollover to the first league-phase matchday */
static int q_summer(void) { int d = today(); return d >= 180 && d < (int)swiss_day(0); }
/* set_clubs on reg 2 or one of its ties in the summer: ours instead of the game's. 1 = handled */
static int q_setcl(uint16_t r, uint64_t id, uint64_t flag, char* ok)
{
  if (!q_summer()) return 0;
  if (!q_world()) { q_why(0); return 0; }
  if (!(q_prepare() & 1)) return 0;
  int k = r == 2 ? -1 : (int)(r >> 10) - 1;
  if (k >= Q_N / 2) return 0;
  u32vec v;
  if (!g_qdrawn[0]) {
    /* a third qualifying round comes first: reg 2 gets its new entrants and the ties, emptied by
       the July teardown just before, stay empty -- a first summer's state, which q_fill fills */
    if (k >= 0) {
      *ok = 1;
      logf("fl26swiss: set_clubs reg %u on day %d -- left empty: the play-off waits for its qualifying rounds", (unsigned)r, today());
      return 1;
    }
    v.b = g_q[0]; v.e = v.c = g_q[0] + g_nnew[0];
  } else if (k < 0) { v.b = g_q[0]; v.e = v.c = g_q[0] + Q_N; }
  else { v.b = g_q[0] + 2 * k; v.e = v.c = g_q[0] + 2 * k + 2; }
  *ok = ((setclr_fn)(uintptr_t)g_tramp_setcl)(id, &v, flag);
  run_flush();
  logf("fl26swiss: set_clubs reg %u on day %d -- the play-off's %s instead of the game's", (unsigned)r, today(),
       k >= 0 ? "tie" : g_qdrawn[0] ? "sixteen" : "new entrants");
  return 1;
}
/* August, inside the game's own hand-over after qualifying (case 2 of the progression): the group
   draw of reg 3 and then of reg 5 is given the access list instead of the game's, and the
   regulation's own list is set to match -- before the stage is started, so its schedule is built
   for these clubs. Called from gdraw_handler; answers the vector to draw, or 0 to leave it. */
static int g_access_ready = 0;
static u32vec g_acc_vec;
static u32vec* access_list(uint16_t r, uint64_t flag)
{
  if (!g_access_on || (r != 3 && r != 5) || po_season_half()) return 0;
  /* (This used to go on only when regulation 11 -- the first id the world builder hands out --
     existed.  The test never worked, see get_rec, so every world has had its Europe rebuilt;
     since the list names only shipped leagues, that is kept, and the test is gone.) */
  if (r == 3) {
    int mask = 0, all = q_world_mask();
    if (all & ~((1 << NQ) - 1)) q_prepare();       /* the earlier rounds' clubs, after a restart too */
    for (int p = 0; p < NQ; p++) if ((all >> p & 1) && q_result(p)) mask |= 1 << p;
    g_access_ready = access_build(mask ? 2 : 0, mask ? mask | (all & ~((1 << NQ) - 1)) : 0);
    if (g_access_ready && mask) q_place(mask);
    if (!g_access_ready) logf("fl26swiss: access -- Champions League list short; the game's lists stand");
    else
      for (int k = 0; k < 3; k++)
        for (unsigned i = 0; i < g_nacc[k]; i++) {
          const how_t* h = &g_how[k][i];
          if (!h->reg) logf("fl26swiss:   %s %2u: first-season list -> %08x", COMP_NAME[k], i + 1, g_acc[k][i]);
          else logf("fl26swiss:   %s %2u: reg %u %s %u -> %08x", COMP_NAME[k], i + 1, (unsigned)h->reg,
                    h->rank ? "position" : "winner", (unsigned)h->rank, g_acc[k][i]);
        }
  }
  int k = r == 3 ? UCL : UEL;
  if (!g_access_ready || g_nacc[k] < FIELD) return 0;
  canon_list(g_acc[k], FIELD, "league phase reg", r);   /* B312 */
  g_acc_vec.b = g_acc[k]; g_acc_vec.e = g_acc_vec.c = g_acc[k] + FIELD;
  ((setclr_fn)(uintptr_t)g_tramp_setcl)(r, &g_acc_vec, flag & 0xff);
  run_flush();
  logf("fl26swiss: access -- %s: reg %u given the access list of %d", COMP_NAME[k], (unsigned)r, FIELD);
  return &g_acc_vec;
}

/* ---- the other continents' places (step 3a) ----
 *
 * The Libertadores (group stage reg 9, qualifying round reg 8) and the AFC Champions League
 * (reg 15) get their entrants from the continental builder 0x141355c90: the rights table first
 * (the shipped leagues' places, by source regulation), then the "other" pools -- club slot 73 for
 * Latin America, 70 for Asia -- until the field is full. 0x1413535e0 turns the builder's target
 * type into the regulation: 3 -> 9, 4 -> 8, 7 -> 15. The rights table only serves leagues of the
 * builder's confederation code, and every league of ours carries 1 (Europe), so our South
 * American and Asian leagues never qualify; recoding them would take them out of the season end
 * that runs their promotion. The list is staged by 0x14135b8e0 and reaches the regulation through
 * set_clubs 0x141522b50 (0x14135bff0). Here, on its way in, the pool clubs are replaced by our
 * leagues' places from the access list (competitions LIB, LIBQ, AFCL), in order: the first pool
 * club by the first place. The rights clubs, the field size and the shipped data stay as they
 * are; a place with no pool club left to take is reported and dropped.
 *
 * The same list may be handed over again (a group draw, a second set). A place whose club is
 * already in the list counts as filled, so a second pass changes nothing. */
#define POOL_LATAM 73
#define POOL_ASIA  70
#define CONT_MAX   32
#define CONT_KEEP  330   /* entrants come after the summer: last July's final table still stands */
static const char* CONT_NAME[3] = { "Libertadores", "Libertadores qualifying", "AFC Champions League" };
/* the competition of a regulation or of one of its groups / ties (id + 1024 * n) */
static int cont_comp(uint16_t id)
{
  uint16_t b = id > 1024 ? id & 0x3ff : id;
  return b == 9 ? LIB : b == 8 ? LIBQ : b == 15 ? AFCL : -1;
}
static uint32_t g_cont[3][CONT_MAX]; static unsigned g_ncont[3]; static how_t g_chow[3][CONT_MAX];
static int cont_any(int comp)
{
  for (size_t i = 0; i < g_naccess; i++) if (g_access[i].comp == comp) return 1;
  /* the first-season AFC list counts too: a world with no AFC place of its own (cont_build) */
  return comp == AFCL && g_nfirst[3] && g_ncont[AFCL - LIB];
}
/* The career's first year, by the date it was built: the state file's (kept however long ago),
   else this session's own (not for a save whose tables were read back: a later season's).
   330 days: a January league's career built on day 0 has its next AFC field a year on. */
static int afc_first_season(void)
{
  state_sync();
  int gn = game_date(), b = g_built_any >= 0 ? g_built_any : g_st_read_back ? -1 : g_built_gdate;
  return gn >= 0 && b >= 0 && gn >= b && gn - b < 330;
}
/* all three lists at once, so no club is given two places */
static void cont_build(void)
{
  uint32_t used[3 * CONT_MAX]; unsigned nused = 0;

  /* Libertadores/Sudamericana titleholders are reserved before domestic access,
     so the domestic place cascades down its own source instead of duplicating them. */
  uint32_t holder[2] = { 0, 0 };
  lib9_titleholders(holder);
  for (int h = 0; h < 2 && nused < sizeof used / sizeof used[0]; h++)
    if (holder[h] && !has_club(used, nused, holder[h]))
      used[nused++] = holder[h];

  g_ncont[0] = g_ncont[1] = g_ncont[2] = 0;
  for (size_t i = 0; i < g_naccess; i++) {
    const access_t* a = &g_access[i];
    if (a->comp < LIB || a->comp > AFCL) continue;
    int k = a->comp - LIB, ft = 0; uint32_t c = 0;
    uint16_t reg = a->reg; int first = a->rank, picked = 0;
    if (!first) {                                   /* cup winner, or the alt league's next place */
      c = cup_winner(reg);
      if (c && has_club(used, nused, c)) c = 0;
      if (!c) { reg = a->alt; first = a->alt ? 1 : FINAL_MAX + 1; }
    }
    for (int rank = first; !c && rank <= FINAL_MAX; rank++) {
      c = access_club_kept(reg, rank, &ft, CONT_KEEP);
      if (!c) break;
      if (!(c >> 14) || has_club(used, nused, c)) { c = 0; continue; }
      picked = rank;
    }
    if (!c || g_ncont[k] >= CONT_MAX || nused >= sizeof used / sizeof used[0]) continue;
    if (a->rank && picked > a->rank)
      logf("fl26swiss: %s access -- source reg %u requested position %u -> position %u (%08x), earlier candidate already taken",
           CONT_NAME[k], (unsigned)a->reg, (unsigned)a->rank, (unsigned)picked, c);
    g_chow[k][g_ncont[k]].reg = a->reg; g_chow[k][g_ncont[k]].rank = a->rank;
    g_cont[k][g_ncont[k]++] = c; used[nused++] = c;
  }
  /* The first-season AFC list (Mod Studio's "First-season European clubs", its AFC column; mato
     05.11.: b2y6421's Shabab Al Ahli, of a league of ours, had no AFC Champions League in the
     first season). The field is set before any league of ours has a final table, so no place of
     ours gives a club then: the list takes the pool clubs' places instead, in the career's first
     year only -- from the second, the places do. */
  if (!g_ncont[AFCL - LIB] && g_nfirst[3] && afc_first_season()) {
    int k = AFCL - LIB, missing = 0, twice = 0;
    for (unsigned i = 0; i < g_nfirst[3] && g_ncont[k] < CONT_MAX; i++) {
      uint32_t c = club_of_id(g_first[3][i]);
      if (!c) { missing++; continue; }
      if (has_club(used, nused, c) || nused >= sizeof used / sizeof used[0]) { twice++; continue; }
      g_chow[k][g_ncont[k]].reg = 0; g_chow[k][g_ncont[k]].rank = 0;
      g_cont[k][g_ncont[k]++] = c; used[nused++] = c;
    }
    static int said = 0;
    SAID_RESET(said);
    if (!said++)
      logf("fl26swiss: first-season list -- %u AFC Champions League club(s) taken (%d not in this game, %d listed twice)",
           g_ncont[k], missing, twice);
  }
}
/* The league slot in +0x41c: 7, 8 or 9 bits, as fl26slot7 left it (lay_slot, fl26layout.h). */
static int slot_of(const unsigned char* t) { return (int)lay_slot(t); }
/* a club's Master League slot (+0x41c), -1 when its record cannot be read */
static int club_slot(void* blk, uint32_t c)
{
  unsigned char* t = ((teamget_fn)(uintptr_t)(g_base + TEAMGET_RVA))(blk, c);
  if (!t || *(uint32_t*)t >> 14 != c >> 14) return -1;
  return slot_of(t);
}
/* ---- the league-phase draw: no club meets its own association, none meets three of one ----
 *
 * The UEFA rules, per club: no opponent from its own association, at most two from any one
 * other. The draw table stays as it is (pots, home and away counts, matchdays); only which club
 * takes which place inside its pot is searched -- fl26swiss_draw.h, which swissdraw_test.c runs
 * offline over a thousand random fields. A club's association is its league's country: the
 * world file's `country=` for the Master League slot (+0x41c) of a league of ours
 * (fl26_swiss_nations), else the game's own slot -> country list (0x1414cdda0), else the club's
 * own country (+0x418; a club of ours that nobody gave a country reads 21, and that is no
 * answer), else the slot itself, else the club alone. Evo-Web / GitHub #15, 2026-09-28:
 * Manchester United - Manchester City on the fourth round. */
#define NATION_RVA 0x14cdda0
static const unsigned char NATION_SIG[] = { 0x40, 0x55, 0x48, 0x8d, 0x6c, 0x24, 0xa9, 0x48, 0x81, 0xec, 0x00, 0x01, 0x00, 0x00 };
typedef uint32_t (*nation_fn)(uint32_t slot);
static uint16_t g_nat[256];                              /* slot -> country, 0 = not given */

/* pairs (slot, country) from the world file's league lines; returns how many were taken */
__declspec(dllexport) int fl26_swiss_nations(const uint16_t* v, int n)
{
  if (!v || n < 0) return -1;
  int k = 0;
  for (int i = 0; i < n; i++)
    if (v[2 * i] != 123 && v[2 * i] < 250 && v[2 * i + 1]) { g_nat[v[2 * i]] = v[2 * i + 1]; k++; }
  logf("fl26swiss: league-phase draw -- countries of %d league slot(s) from the world file", k);
  return k;
}

static int club_key(void* blk, uint32_t c, int i)
{
  unsigned char* t = ((teamget_fn)(uintptr_t)(g_base + TEAMGET_RVA))(blk, c);
  if (!t || *(uint32_t*)t >> 14 != c >> 14) return 2000 + i;
  int s = slot_of(t);
  if (s != 123 && s < 250 && g_nat[s]) return g_nat[s];
  if (s < 123 && !memcmp((const void*)(g_base + NATION_RVA), NATION_SIG, sizeof NATION_SIG)) {
    uint32_t k = ((nation_fn)(uintptr_t)(g_base + NATION_RVA))((uint32_t)s) & 0xffff;
    if (k && k < 0xfffc) return (int)k;
  }
  int own = *(uint16_t*)(t + 0x418) & 0x1ff;
  if (own && own != 21) return own;
  return s != 123 && s < 250 ? 1000 + s : 2000 + i;
}

static int spread_leagues(const uint32_t* clubs, int n, const fl26_pair_t* table, int npairs, int pot,
                          uint8_t* perm, uint16_t id)
{
  int key[FL26_SWISS36_CLUBS];
  for (int i = 0; i < FL26_SWISS36_CLUBS; i++) perm[i] = (uint8_t)i;
  unsigned char* o = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
  void* blk = o ? *(void**)(o + 0x48) : 0;
  if (!blk || !clubs || n < 2) return -1;
  for (int i = 0; i < n; i++) key[i] = club_key(blk, clubs[i], i);
  int before = 0, steps = 0;
  int left = draw_spread(key, clubs, n, table, npairs, pot, perm, &before, &steps);
  logf("fl26swiss: reg %u -- draw by association: %d same-association pair(s) and %d third opponent(s) "
       "before, %d and %d after (%d repairs)%s", (unsigned)id, before / 100, before % 100, left / 100,
       left % 100, steps, left ? " -- no draw keeps both rules for this field; the closest one stands" : "");
  /* per club: its country, then its opponents' */
  for (int x = 0; x < n; x++) {
    char buf[160]; int m = 0;
    for (int k = 0; k < npairs && m < (int)sizeof buf - 8; k++) {
      int h = table[k].home, a = table[k].away;
      if (h >= n || a >= n || (h != x && a != x)) continue;
      m += snprintf(buf + m, sizeof buf - m, "%s%d", m ? "," : "", key[perm[h == x ? a : h]]);
    }
    buf[m] = 0;
    logf("fl26swiss: reg %u draw: pot %d team %u [%d] v %s", (unsigned)id, x / pot + 1,
         (unsigned)(clubs[perm[x]] >> 14), key[perm[x]], buf);
  }
  return left;
}

/* Which pool club gave way to which of ours, per competition, for this season's lists. The AFC
 * builder hands over the groups itself, each group as its own list (ids 1039 ... 8207) next to
 * the whole field (15), so the same pool club turns up twice and must give way to the same club
 * of ours both times -- whichever list comes first decides. (Measured 2026-09-27: with only the
 * whole field swapped, reg 15 held our eight and its groups the eight pool clubs.) */
static uint32_t g_mfrom[3][CONT_MAX], g_mto[3][CONT_MAX]; static unsigned g_nmap[3]; static int g_mday[3] = { -100000, -100000, -100000 };
/* Native Libertadores qualifying (reg 8) is followed by four child tie rows.
 * Keep parent sanitation replacements so the exact same replacement can be
 * propagated to those child rows when they are handed over afterwards. */
static uint32_t g_libq_sanitize_from[CONT_MAX], g_libq_sanitize_to[CONT_MAX];
static unsigned g_nlibq_sanitize = 0;
static int g_libq_sanitize_day = -100000;
/* B204: a Libertadores club that is in a cup of the world's own already, and the club that took
   its place -- the same pair for every list of that season (the field, its groups, the draw) */
static uint32_t g_libdup_from[CONT_MAX], g_libdup_to[CONT_MAX];
static unsigned g_nlibdup = 0;
static int g_libdup_day = -100000;
/* The club of ours that pool club c gives way to in competition k, or 0 to leave it. A club
 * already mapped keeps its partner; otherwise the next place of ours that is neither given
 * nor already in the list `have` takes it. For a group (id + 1024 * n) a place of ours that the
 * whole field already holds is not given again: the Libertadores field is set on day 0 and its
 * groups on day 41, after the map above has been cleared, and each group then took one of ours
 * a second time (GitHub #22: two clubs in two groups each, playing both). */
static uint32_t cont_map_one(int k, uint32_t c, const uint32_t* have, size_t nh, const how_t** how, uint16_t id)
{
  unsigned j;
  for (j = 0; j < g_nmap[k]; j++)
    if (same_club(g_mfrom[k][j], c)) return has_club(have, nh, g_mto[k][j]) ? 0 : g_mto[k][j];
  unsigned char* whole = id > 1024 ? get_rec(id & 0x3ff) : 0;
  size_t nw = whole ? rec_count(whole) : 0;
  for (j = 0; j < g_ncont[k] && g_nmap[k] < CONT_MAX; j++) {
    uint32_t cand = g_cont[k][j]; int given = 0;
    for (unsigned q = 0; q < g_nmap[k] && !given; q++) given = same_club(g_mto[k][q], cand);
    if (given || has_club(have, nh, cand)) continue;
    if (whole && has_club(rec_clubs(whole), nw, cand)) continue;
    g_mfrom[k][g_nmap[k]] = c; g_mto[k][g_nmap[k]++] = cand;
    if (how) *how = &g_chow[k][j];
    return cand;
  }
  return 0;
}
/* The club the user manages: 0x1414bb650(block, &team, "", &3), the lookup the game's "what is
 * this day for the user's club" (0x14150d990) starts with. It never gives its place away to one
 * of ours: Vicentico (2026-10-11) managed Universidad Catolica into the Libertadores qualifying
 * and a stand-in of ours took its place there. 0 when there is none. */
#define USERCLUB_RVA 0x14bb650
typedef void* (*userclub_fn)(void* blk, uint32_t* team, const char* name, int* mode);
static uint32_t user_club(void* blk)
{
  uint32_t t = 0; int mode = 3; static const char none[1] = { 0 };
  if (!blk) return 0;
  ((userclub_fn)(uintptr_t)(g_base + USERCLUB_RVA))(blk, &t, none, &mode);
  return t >> 14 ? t : 0;
}
/* a club that already gave way to one of ours in competition k this season */
static int cont_mapped(int k, uint32_t c)
{
  for (unsigned j = 0; j < g_nmap[k]; j++) if (same_club(g_mfrom[k][j], c)) return 1;
  return 0;
}
/* The Libertadores qualifying round (reg 8) holds no pool club: the game fills its eight places
 * from the shipped leagues' rights, so our places there found nobody to replace and stayed at
 * home (GitHub #33: "8 clubs, 0 from pool 73; our places 2, paired 0"). There a place of ours
 * takes a shipped club's instead: the last one listed of the league with the most clubs in the
 * round, so every league keeps one while another still has two, and a league's lower place gives
 * way before its higher. All but two places of the round can be given away (half of it until
 * 2026-10-01: GitHub #66, six new leagues with a qualifying place each, two of them left out).
 * The ties (1032, 2056 ...) come
 * right after the whole field, on the same day, with the same clubs: the map above makes the
 * same club give way there too (cont_mapped). Returns how many were put in. */
static unsigned cont_standins(int k, u32vec* list, size_t n, void* blk, int pool, unsigned put, uint16_t id)
{
  unsigned need = 0, done = 0;
  uint32_t holder[2] = { 0, 0 };
  if (k == 0) lib9_titleholders(holder);
  for (unsigned j = 0; j < g_ncont[k]; j++) {
    uint32_t cand = g_cont[k][j]; int given = 0;
    for (unsigned q = 0; q < g_nmap[k] && !given; q++) given = same_club(g_mto[k][q], cand);
    if (!given && !has_club(list->b, n, cand)) need++;
  }
  if (!need || n < 2 || n > 64) return 0;
  int key[64]; uint8_t out[64];
  uint32_t uc = user_club(blk);
  for (size_t i = 0; i < n; i++) {
    uint32_t c = list->b[i];
    int s = club_slot(blk, c);
    key[i] = s < 0 ? 1000 + (int)i : s;
    /* not a shipped club of a league: a pool club, one of ours, or one already given way; and
       never the user's club */
    out[i] = !(c >> 14) || s == pool || has_club(g_cont[k], g_ncont[k], c) || cont_mapped(k, c)
             || (uc && same_club(c, uc))
             || (k == 0 && ((holder[0] && same_club(c, holder[0])) ||
                            (holder[1] && same_club(c, holder[1]))));
    for (unsigned q = 0; q < g_nmap[k] && !out[i]; q++) out[i] = same_club(g_mto[k][q], c);
  }
  unsigned room = n > 2 ? (unsigned)n - 2 : 0;
  unsigned cap = room > put ? room - put : 0;
  /* B444 (b2y6421, 12.11.2026: Group A of the AFC Champions League was Machida Zelvia, Tokyo
     Verdy, Fagiano Okayama and Kawasaki Frontale). The game fills reg 15 with some twenty clubs
     of the J1, drawn already -- the list is the groups one after another, four clubs each -- and
     the J1 clubs that keep their places were the first listed: the first groups whole. So in
     that field the club that gives way is, of the league with the most clubs in the round, the
     one whose group holds the most clubs of its country; and not one whose group holds a club
     of the country of the club of ours that comes in, while another will do. */
  int grouped = k == AFCL - LIB && id == 15 && n % 4 == 0;
  int ctry[64];
  for (size_t i = 0; i < n; i++) ctry[i] = grouped ? team_country(blk, list->b[i]) : -1;
  while (need && cap) {
    int best = -1, most = 0, bscore = 0, nc = -1;
    if (grouped)
      for (unsigned j = 0; j < g_ncont[k] && nc < 0; j++) {     /* the next of ours, as cont_map_one takes it */
        uint32_t cand = g_cont[k][j]; int given = 0;
        for (unsigned q = 0; q < g_nmap[k] && !given; q++) given = same_club(g_mto[k][q], cand);
        if (!given && !has_club(list->b, n, cand)) { nc = team_country(blk, cand); break; }
      }
    for (int i = (int)n - 1; i >= 0; i--) {         /* backwards: a league's last listed first */
      if (out[i]) continue;
      int cnt = 0, score = 0;
      for (size_t j = 0; j < n; j++) cnt += !out[j] && key[j] == key[i];
      if (grouped)
        for (int j = i / 4 * 4; j < i / 4 * 4 + 4; j++) {
          if (j == i) continue;
          if (ctry[i] >= 0 && ctry[j] == ctry[i]) score++;
          if (nc >= 0 && ctry[j] == nc) score -= 8;
        }
      if (cnt > most || (cnt == most && score > bscore)) { most = cnt; best = i; bscore = score; }
    }
    if (best < 0) break;
    out[best] = 1;
    uint32_t c = list->b[best];
    const how_t* h = 0;
    uint32_t to = cont_map_one(k, c, list->b, n, &h, id);
    if (!to) break;
    list->b[best] = to; need--; cap--; done++;
    if (grouped) ctry[best] = team_country(blk, to);
    if (h && !h->reg)
      logf("fl26swiss:   %s: first-season list -> %08x, in place of %08x (slot %d, %d of its league in the round)",
           CONT_NAME[k], to, c, key[best], most);
    else
      logf("fl26swiss:   %s: reg %u %s %u -> %08x, in place of %08x (slot %d, %d of its league in the round)",
           CONT_NAME[k], h ? (unsigned)h->reg : 0u, h && !h->rank ? "winner" : "position", h ? (unsigned)h->rank : 0u,
           to, c, key[best], most);
  }
  if (need) logf("fl26swiss: %s (reg %u) -- %u place(s) of ours left out: all but two places of the round are given away already",
                 CONT_NAME[k], (unsigned)id, need);
  if (grouped && done) {
    int pairs = 0;
    for (size_t g = 0; g < n / 4; g++)
      for (size_t a = g * 4; a < g * 4 + 4; a++)
        for (size_t b = a + 1; b < g * 4 + 4; b++) pairs += ctry[a] >= 0 && ctry[a] == ctry[b];
    logf("fl26swiss: %s (reg %u) -- groups after the stand-ins: %d pair(s) of one country in a group",
         CONT_NAME[k], (unsigned)id, pairs);
  }
  return done;
}
/* the block and a fresh season check, shared by both ways in */
static void* cont_begin(int k)
{
  unsigned char* o = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
  void* blk = o ? *(void**)(o + 0x48) : 0;
  if (!blk) return 0;
  int ad = abs_day();
  if (ad - g_mday[k] > 30 || ad < g_mday[k]) g_nmap[k] = 0;      /* a new season's lists */
  g_mday[k] = ad;
  cont_build();
  return blk;
}
/* The classic Libertadores (no modern pre-rounds): the game fills its group stage (9) and its
 * qualifying round (8) by the exe's rights -- Brazil's and Argentina's 1st-4th, Chile's 1st, the
 * winners of their cups and of Colombia's two playoffs (0x1434f1fa0; 29 5th-6th, 30 5th, 67
 * 2nd-3rd to the qualifying) -- and our places only took the pool clubs' places. A league of the
 * game given Libertadores places of its own (game_europe) kept the game's as well: Chile's 3rd,
 * given the Copa Sudamericana, still played the qualifying round, and the Sudamericana took its
 * 4th; a league given fewer places than the game's kept all of the game's. A club of such a
 * league (or of its cup) in the game's list that is not one of the world's places now gives way
 * like a pool club, before them: to the next place of ours, else to a CONMEBOL club of the pool
 * (conmebol_fallback). Leagues the world gives no Libertadores place keep the game's. The
 * modern pre-rounds have their own sanitation (cont_swap, modern_conmebol). */
static int lib_source_has(uint16_t reg, uint32_t c, int depth)
{
  const ssum_t* ss = ssum_of(reg);
  if (ss && depth < 2) {
    for (int p = 0; p < SSUM_PARTS && ss->part[p]; p++) if (lib_source_has(ss->part[p], c, depth + 1)) return 1;
    return 0;
  }
  unsigned char* r = get_rec(reg);
  return r && has_club(rec_clubs(r), rec_count(r), c);
}
static int lib_set_by_world(int k, uint32_t c, uint16_t id)
{
  /* the whole field only: its groups and ties come from it, the same day or drawn from it */
  if (k > 1 || id >= 1024 || modern_conmebol() || !(c >> 14) || has_club(g_cont[k], g_ncont[k], c)) return 0;
  for (size_t i = 0; i < g_naccess; i++) {
    const access_t* a = &g_access[i];
    if (a->comp != LIB && a->comp != LIBQ) continue;
    if ((a->rank && lib_source_has(a->reg, c, 0)) || (!a->rank && a->reg && lib_source_has(a->reg, c, 0))
        || (a->alt && lib_source_has(a->alt, c, 0))) return 1;
  }
  return 0;
}
static void cont_swap(uint16_t id, u32vec* list, const char* where)
{
  int comp = cont_comp(id);
  size_t n = list && list->b ? (size_t)(list->e - list->b) : 0;
  if (comp < 0 || !n) return;
  int k = comp - LIB, pool = comp == AFCL ? POOL_ASIA : POOL_LATAM;
  void* blk = cont_begin(k);
  if (!blk) return;

  /* Only a world with our F1/F2 pre-rounds gets modern Libertadores sanitation.
   * Vanilla worlds leave the game's native Libertadores lists untouched. */
  if (modern_conmebol() && (comp == LIB || comp == LIBQ) && id < 1024 && g_confed_n) {
    if (comp == LIBQ && g_libq_sanitize_day != abs_day()) {
      g_nlibq_sanitize = 0;
      g_libq_sanitize_day = abs_day();
    }

    uint32_t holder[2] = { 0, 0 };
    if (comp == LIBQ) lib9_titleholders(holder);

    /* B227 (antonimus, 24.10.): the game's own places put a club of phase 1 or 2 in the native
       phase 3 as well (Universidad Catolica, Chile's), so before phase 2 was played its calendar
       had phase 3 against Millonarios. Until lib8_swap gives phase 3 the phase 2 winners, a club
       of the path is a place reserved like the rest. */
    int path = comp == LIBQ && today() >= 0 && today() < 34 && !libq_f3_ready();
    for (size_t i = 0; i < n; i++) {
      uint32_t old = list->b[i];
      int cf = confed_of(team_country(blk, old));
      int reserved = comp == LIBQ &&
          (has_club(g_cont[0], g_ncont[0], old) ||
           (holder[0] && same_club(old, holder[0])) ||
           (holder[1] && same_club(old, holder[1])) ||
           (path && lib_path_has(old)));

      if (cf == 4 && !reserved) continue;

      uint32_t to = conmebol_fallback(blk, list->b, (unsigned)n);
      if (!to) {
        if (reserved)
          logf("fl26swiss: Libertadores qualifying reg %u -- reserved direct/titleholder/F1-F2 %08x has no safe CONMEBOL replacement",
               (unsigned)id, old);
        else
          logf("fl26swiss: %s reg %u -- NON-CONMEBOL %08x (confederation %d) has no CONMEBOL replacement",
               CONT_NAME[k], (unsigned)id, old, cf);
        continue;
      }

      list->b[i] = to;
      if (comp == LIBQ) {
        unsigned q;
        for (q = 0; q < g_nlibq_sanitize; q++)
          if (same_club(g_libq_sanitize_from[q], old)) {
            g_libq_sanitize_to[q] = to;
            break;
          }
        if (q == g_nlibq_sanitize && g_nlibq_sanitize < CONT_MAX) {
          g_libq_sanitize_from[g_nlibq_sanitize] = old;
          g_libq_sanitize_to[g_nlibq_sanitize] = to;
          g_nlibq_sanitize++;
        }
      }

      if (reserved)
        logf("fl26swiss: Libertadores qualifying reg %u -- reserved direct/titleholder/F1-F2 %08x replaced by CONMEBOL %08x",
             (unsigned)id, old, to);
      else
        logf("fl26swiss: %s reg %u -- NON-CONMEBOL %08x (confederation %d) replaced by CONMEBOL %08x",
             CONT_NAME[k], (unsigned)id, old, cf, to);
    }
  }

  /* Reg 8's child ties are handed over after the parent field. Propagate exactly
     the same sanitation replacement; never let parent and child disagree. */
  if (modern_conmebol() && comp == LIBQ && id > 1024 &&
      g_nlibq_sanitize && g_libq_sanitize_day == abs_day()) {
    unsigned changed = 0;
    for (size_t i = 0; i < n; i++) {
      for (unsigned q = 0; q < g_nlibq_sanitize; q++) {
        if (!same_club(list->b[i], g_libq_sanitize_from[q])) continue;
        uint32_t old = list->b[i], to = g_libq_sanitize_to[q];
        if (has_club(list->b, n, to)) {
          logf("fl26swiss: Libertadores qualifying child reg %u -- parent replacement %08x -> %08x already present; original left alone",
               (unsigned)id, old, to);
          break;
        }
        list->b[i] = to;
        changed++;
        logf("fl26swiss: Libertadores qualifying child reg %u -- parent replacement %08x -> %08x propagated",
             (unsigned)id, old, to);
        break;
      }
    }
    if (changed)
      logf("fl26swiss: Libertadores qualifying child reg %u -- %u parent replacement(s) propagated",
           (unsigned)id, changed);
  }

  /* B204 (World Modpack, a tester's second season): the game files the Libertadores on 1 January,
     Inter Miami by the MLS's places, and it was in the CONCACAF Champions Cup of the world's
     (filled in August, from the same league) as well -- two continental cups in the same months.
     The world's cups keep their club: in the Libertadores a club from outside CONMEBOL gives way
     to a CONMEBOL club no cup holds (conmebol_fallback), the same one in every list of that season.
     A CONMEBOL club stays: the World Modpack's Copa Sudamericana runs August to May, and the first
     build of this (2028 of r13) took six Brazilian and Argentinian clubs out of the Libertadores
     for it. */
  if ((comp == LIB || comp == LIBQ) && g_confed_n) {
    static uint32_t held[1536];
    unsigned nh = world_cup_clubs(held, 1024);
    int ad = abs_day();
    if (ad - g_libdup_day > 120 || ad < g_libdup_day) g_nlibdup = 0;
    for (size_t i = 0; i < n && nh; i++) {
      uint32_t old = list->b[i];
      if (!has_club(held, nh, old) || confed_of(team_country(blk, old)) == 4) continue;
      g_libdup_day = ad;
      uint32_t to = 0;
      for (unsigned q = 0; q < g_nlibdup && !to; q++)
        if (same_club(g_libdup_from[q], old)) to = g_libdup_to[q];
      if (to && has_club(list->b, n, to)) to = 0;
      if (!to && id < 1024) {
        /* not one of this list, nor of a cup of the world's, nor of the game's other Libertadores list */
        unsigned nt = nh;
        for (size_t j = 0; j < n && nt < sizeof held / sizeof held[0]; j++) held[nt++] = list->b[j];
        static const uint16_t LIBS[] = { 9, 8 };
        for (unsigned r = 0; r < 2; r++) {
          unsigned char* rec = get_rec(LIBS[r]);
          unsigned rc = rec ? rec_count(rec) : 0;
          for (unsigned j = 0; j < rc && nt < sizeof held / sizeof held[0]; j++) held[nt++] = rec_clubs(rec)[j];
        }
        to = conmebol_fallback(blk, held, nt);
        if (to) {
          unsigned q;
          for (q = 0; q < g_nlibdup; q++) if (same_club(g_libdup_from[q], old)) { g_libdup_to[q] = to; break; }
          if (q == g_nlibdup && g_nlibdup < CONT_MAX) { g_libdup_from[q] = old; g_libdup_to[q] = to; g_nlibdup++; }
        }
      }
      if (!to) {
        logf("fl26swiss: %s reg %u (%s) -- day %d: %08x (confederation %d) is in a cup of the world's too; no CONMEBOL club to put in, left",
             CONT_NAME[k], (unsigned)id, where, today(), old, confed_of(team_country(blk, old)));
        continue;
      }
      list->b[i] = to;
      logf("fl26swiss: %s reg %u (%s) -- day %d: %08x (confederation %d) is in a cup of the world's too; CONMEBOL %08x in its place",
           CONT_NAME[k], (unsigned)id, where, today(), old, confed_of(team_country(blk, old)), to);
    }
  }

  if (!cont_any(comp)) return;

  /* The AFC field reaches set_clubs already drawn: the list is the groups one after another,
   * four clubs each. Everything else is walked in order. */
  size_t order[64], no = 0;
  uint32_t holder[2] = { 0, 0 };
  if (comp == LIB && id < 1024) lib9_titleholders(holder);
  int grouped = comp == AFCL && id == 15 && n % 4 == 0 && n <= 64;
  if (grouped) {
    for (size_t r = 0; r < 4; r++)
      for (size_t g = 0; g < n / 4; g++)
        for (size_t i = g * 4, seen = 0; i < g * 4 + 4; i++)
          if (club_slot(blk, list->b[i]) == pool && seen++ == r) { order[no++] = i; break; }
  } else {
    /* a club of a league whose Libertadores places the world sets first (lib_set_by_world), then
       the pool clubs */
    uint8_t set[64] = { 0 };
    for (size_t i = 0; i < n && i < 64 && no < 64; i++) {
      uint32_t c = list->b[i];
      if ((holder[0] && same_club(c, holder[0])) || (holder[1] && same_club(c, holder[1]))) continue;  /* title holders stay */
      if (club_slot(blk, c) != pool && !cont_mapped(k, c) && lib_set_by_world(k, c, id)) { set[i] = 1; order[no++] = i; }
    }
    for (size_t i = 0; i < n && no < 64; i++) {
      uint32_t c = list->b[i];
      if (i < 64 && set[i]) continue;
      if (comp == LIB && id < 1024 &&
          ((holder[0] && same_club(c, holder[0])) ||
           (holder[1] && same_club(c, holder[1]))))
        continue;
      if (club_slot(blk, c) == pool || cont_mapped(k, c)) order[no++] = i;
    }
  }
  unsigned npool = 0, put = 0, left = 0, before = g_nmap[k];
  uint32_t uc = user_club(blk);
  for (size_t q = 0; q < no; q++) {
    size_t i = order[q];
    uint32_t c = list->b[i];
    npool++;
    if (uc && same_club(c, uc) && !cont_mapped(k, c)) { left++; continue; }
    const how_t* h = 0;
    int byworld = club_slot(blk, c) != pool && !cont_mapped(k, c) && lib_set_by_world(k, c, id);
    uint32_t to = cont_map_one(k, c, list->b, n, &h, id);
    if (!to && byworld && g_nmap[k] < CONT_MAX) {
      /* none of ours left: a CONMEBOL club of the pool, the same one in every list of the season */
      to = conmebol_fallback(blk, list->b, (unsigned)n);
      if (to) { g_mfrom[k][g_nmap[k]] = c; g_mto[k][g_nmap[k]++] = to; }
    }
    if (!to) { left++; continue; }
    list->b[i] = to; put++;
    if (byworld)
      logf("fl26swiss:   %s: reg %u -- %08x is of a league whose Libertadores places the world sets, not one "
           "of them; %08x in its place (%s)", CONT_NAME[k], (unsigned)id, c, to, h ? "a place of ours" : "a pool club");
    else if (h && !h->reg)
      logf("fl26swiss:   %s: first-season list -> %08x, in place of pool club %08x", CONT_NAME[k], to, c);
    else if (h) logf("fl26swiss:   %s: reg %u %s %u -> %08x, in place of pool club %08x", CONT_NAME[k],
                (unsigned)h->reg, h->rank ? "position" : "winner", (unsigned)h->rank, to, c);
  }
  /* B302 (World Modpack r12, MorePower and gianito9 31.10.): its Asian leagues took the game's
     AFC pool clubs, so reg 15 held 6 pool clubs and 26 of the game's own (the J1's) -- two of
     our eight places found nobody to replace. The whole field (reg 15) gives way as the
     Libertadores qualifying does; its groups follow through the map. */
  if (((comp == LIB || comp == LIBQ) && id < 1024) || (comp == AFCL && id == 15))
    put += cont_standins(k, list, n, blk, pool, put, id);

  unsigned present = 0;
  for (unsigned j = 0; j < g_ncont[k]; j++)
    if (has_club(list->b, n, g_cont[k][j])) present++;

  logf("fl26swiss: %s (reg %u, %s) -- day %d: %u clubs, %u from pool %d; %u put in (%u newly paired), %u pool clubs left; our places %u, present %u, paired %u",
       CONT_NAME[k], (unsigned)id, where, today(), (unsigned)n, npool, pool, put, g_nmap[k] - before, left,
       g_ncont[k], present, g_nmap[k]);
}

/* One club added to a regulation's list -- the way the AFC builder fills its groups, straight
 * from the list it had before set_clubs saw it (measured 2026-09-27: reg 15 held our eight, its
 * groups the eight pool clubs they replaced). Only the groups are touched here; the whole
 * field goes through cont_swap. */
static uint32_t cont_add(void* rec, uint32_t club)
{
  uint16_t id = rec_id(rec);
  int comp = id > 1024 ? cont_comp(id) : -1;
  if (comp < 0 || !cont_any(comp)) return 0;
  int k = comp - LIB, pool = comp == AFCL ? POOL_ASIA : POOL_LATAM;
  void* blk = cont_begin(k);
  if (!blk || (club_slot(blk, club) != pool && !(comp == AFCL && cont_mapped(k, club)))) return 0;   /* B302: a stand-in's too */
  uint32_t have[48]; size_t nh = rec_count(rec);
  if (nh > 48) nh = 48;
  memcpy(have, (unsigned char*)rec + 0x170, nh * 4);
  uint32_t to = cont_map_one(k, club, have, nh, 0, id);
  if (to) logf("fl26swiss: %s group reg %u -- pool club %08x added straight, %08x in its place", CONT_NAME[k], (unsigned)id, club, to);
  return to;
}

/* ---- the Club World Cup at 32 ----
 *
 * The 2025 format: 32 clubs, eight groups of four played once round, then a single-match
 * knockout of sixteen. A world that has it keeps competition 1 and its regulation 1, makes reg 1 the
 * group stage (replicas 1025, 2049 ... 8193) and a new regulation, CWC_KO, the knockout.
 *
 * Nothing new is taught to the game about WHEN the Club World Cup happens: its own code still
 * hands the competition its entrants (0x141366200 and the pools behind it) through set_clubs on
 * regulation 1. That call is where the field is replaced by 32 clubs from league tables (the
 * list below, pots of eight in order) and drawn into the eight groups with the game's own group
 * draw -- the shape is the old Champions League's, which that draw was made for. The clubs the
 * game offered (its pool clubs, the only Africa and Oceania it has) go into the fourth pot.
 * When the group stage ends, the progression hands over: group winners and runners-up into
 * CWC_KO in the 2025 bracket order (A1-B2, C1-D2 ...), and CWC_KO is started. Dates for both
 * are borrowed from the World Cup's shapes (reg 34: six group dates, reg 35: the single-match
 * knockout of sixteen) and moved to CWC_GROUP_DAYS / CWC_KO_DAYS.
 *
 * A world without the reshaped rows (no CWC_KO or no replica 1025) is left entirely alone. */
#define CWC_REG 1
/* the knockout's regulation: 200 unless the world file's cwc32 line names another (Mod Studio's
   Club World Cup option takes a free id of the world; 200 is a league in many worlds) */
#define CWC_KO  g_cwc_ko
static uint16_t g_cwc_ko = 200;
#define CWC_GROUPS 8
#define CWC_N 32
#define R_BRA 29
#define R_ARG 30
#define R_USA 51
#define R_JPN 52
#define R_CHI 67
#define R_CHN 120
#define R_KSA 162
#define R_WCGROUP 34     /* date borrowing: the World Cup's group stage, six dates */
#define R_WCKO    35     /* and its single-match knockout of sixteen, ten records */
/* 2 June to 27 June: after the leagues and the Champions League final (day 149) */
static const uint32_t CWC_GROUP_DAYS[6] = { 153, 154, 157, 158, 161, 162 };
static const uint32_t CWC_KO_DAYS[10] = { 165, 166, 169, 170, 173, 174, 177, 178, 177, 178 };
typedef struct { uint16_t reg; uint8_t rank; } cwcacc_t;
static const cwcacc_t CWC_ACCESS[] = {
  /* pot 1 */ {R_ENG,1},{R_ESP,1},{R_ITA,1},{R_GER,1},{R_BRA,1},{R_BRA,2},{R_ARG,1},{R_FRA,1},
  /* pot 2 */ {R_ENG,2},{R_ESP,2},{R_ITA,2},{R_GER,2},{R_POR,1},{R_NED,1},{R_BEL,1},{R_BRA,3},
  /* pot 3 */ {R_ARG,2},{R_CHI,1},{R_JPN,1},{R_KSA,1},{R_CHN,1},{R_JPN,2},{R_USA,1},{R_USA,2},
  /* pot 4, after the game's own entrants */ {R_USA,3},{R_USA,4},{R_KSA,2},{R_CHN,2},
  {R_FRA,2},{R_POR,2},{R_NED,2},{R_ENG,3},
};
static const int CWC_BRACKET[16][2] = {   /* {group, place}: A1-B2, C1-D2, E1-F2, G1-H2, B1-A2 ... */
  {0,0},{1,1},{2,0},{3,1},{4,0},{5,1},{6,0},{7,1},
  {1,0},{0,1},{3,0},{2,1},{5,0},{4,1},{7,0},{6,1} };
#define REGALL_RVA 0x1343bf0   /* register_all(ctx, vec_u16* ids) */
typedef void (*regall_fn)(void* ctx, void* ids);
static uint16_t cwc_rep(int g) { return (uint16_t)(CWC_REG + 1024 * (g + 1)); }
static int cwc_world(void) { return get_rec(CWC_KO) && get_rec(cwc_rep(0)) && get_rec(cwc_rep(CWC_GROUPS - 1)); }
/* Mod Studio's Club World Cup option, from the world file's
 *   cwc32 ko=<reg> every=<years> first=<year> ic=<reg> iccid=<competition>
 * line (fl26_swiss_cwc):
 *   - the 32-club cup is drawn only in the years of its cycle: the year it is PLAYED (June) is
 *     first, first + every ... (every 0 or 1, or first 0: every season, as before);
 *   - ic: the game's old four-club Club World Cup, kept as a competition of its own (a copy of
 *     the shipped regulation 1 on a new id, "Copa Intercontinental"). Every year the game's four
 *     entrants of regulation 1 (the moment the old cup got them, day 332) go to it instead, it
 *     is started with register_all and dated with the shipped reg 1 days (348-352).
 * Without the line nothing changes: knockout 200, every season, no Intercontinental. */
static uint16_t g_cwc_every = 1, g_cwc_first = 0, g_ic_reg = 0, g_ic_cid = 0;
__declspec(dllexport) int fl26_swiss_cwc(const uint16_t* v, int n)
{
  if (!v || n < 5) return 0;
  if (v[0] > 175 && v[0] < 1024) g_cwc_ko = v[0];
  g_cwc_every = v[1];
  g_cwc_first = v[2];
  g_ic_reg = (v[3] > 1 && v[3] < 1024 && v[3] != g_cwc_ko) ? v[3] : 0;
  g_ic_cid = g_ic_reg ? v[4] : 0;
  logf("fl26swiss: world file -- Club World Cup of 32: knockout reg %u, every %u year(s) from %u; Intercontinental %s%u",
       (unsigned)g_cwc_ko, (unsigned)g_cwc_every, (unsigned)g_cwc_first, g_ic_reg ? "reg " : "off ", (unsigned)g_ic_reg);
  return 1;
}
/* the year the cup drawn today is played: the draw is in late November (day 332), the cup in
   June of the next year; a draw in the first half of a year plays that same year */
static int cwc_play_year(void)
{
  int gd = game_date();
  if (gd < 0) return -1;
  int y = gd / 365, t = gd % 365;
  return t >= 182 ? y + 1 : y;
}
static int cwc_cycle_year(int* year)
{
  int y = cwc_play_year();
  if (year) *year = y;
  if (g_cwc_every <= 1 || !g_cwc_first || y < 0) return 1;
  return y >= g_cwc_first && (y - g_cwc_first) % g_cwc_every == 0;
}
/* the Intercontinental is there: its regulation, of its competition, in a career that has the
   new Club World Cup rows too. A career saved before the world had them still holds whatever
   cup had that id then (the UAE Super Cup of _FL26-27-Def has the same competition id): not ours */
static int ic_world(void)
{
  unsigned char* r = g_ic_reg ? get_rec(g_ic_reg) : 0;
  return r && (!g_ic_cid || *(uint32_t*)(r + 0x80) == g_ic_cid) && cwc_world();
}
static int cwc_id(uint16_t id) { return id == CWC_REG || (id > 1024 && (id & 0x3ff) == CWC_REG && id <= cwc_rep(CWC_GROUPS - 1)); }

/* ---- a phase of our splits: its table from its played matches ----
 *
 * The playoff after an Apertura or a Clausura is filled the day after the phase ends, and by
 * then the game has no table for it: the Apertura's (191, 2026-09-29) and the Clausura's (192)
 * read 0 rows, before and after the phase's progression, under the phase id and under every
 * group row id, and the record's club list had one club left ("cup 200 -- only 1 of 8 clubs
 * found"). The matches are still there. So the table is counted from them: three points a win,
 * one a draw, then goal difference, then goals scored. The match table's place in the block
 * and its size are read off the game's own walk of it in the July teardown (lea rcx,
 * [rax + base] and cmp edi, cap -- a patch set that moves or grows it rewrites both). A match
 * record: +0x00 own index (0xffff free), +0x04 regulation, +0x07 bit 0x40 played, +0x14 and
 * +0x18 the clubs, +0x1c and +0x1f their goals (checked against a table the game showed:
 * Germany D2 after 18 rounds, ten places, every points total the same). */
#define MATCH_BASE_SITE 0x13146e8
#define MATCH_CAP_SITE  0x131471b
#define MATCH_STRIDE    0x254
typedef struct split_s split_t;
static int split_part(uint16_t id, const split_t** out);
static final_t g_ptab;
static int g_ptab_day = -1;
static int g_ctab_pts[3];                 /* count_table's first, second and last points, for the log */
/* how many match records regulation reg has (0xffff: all of them), played or not; -1 if the match table is not where it was */
static int ccup_matches(uint16_t reg)
{
  const unsigned char* bs = (const unsigned char*)(g_base + MATCH_BASE_SITE);
  const unsigned char* cs = (const unsigned char*)(g_base + MATCH_CAP_SITE);
  if (bs[0] != 0x48 || bs[1] != 0x8d || bs[2] != 0x88 || cs[0] != 0x81 || cs[1] != 0xff) return -1;
  uint32_t base = *(const uint32_t*)(bs + 3), cap = *(const uint32_t*)(cs + 2);
  unsigned char* o = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
  unsigned char* blk = o ? *(unsigned char**)(o + 0x48) : 0;
  if (!blk || !cap || cap > 200000) return -1;
  int n = 0;
  for (uint32_t i = 0; i < cap; i++) {
    const unsigned char* m = blk + base + (size_t)i * MATCH_STRIDE;
    if (*(const uint16_t*)m != 0xffff && (reg == 0xffff || *(const uint16_t*)(m + 4) == reg)) n++;
  }
  return n;
}
/* the same, the unplayed ones only (match +7 bit 6 = played) */
static int ccup_unplayed(uint16_t reg)
{
  const unsigned char* bs = (const unsigned char*)(g_base + MATCH_BASE_SITE);
  const unsigned char* cs = (const unsigned char*)(g_base + MATCH_CAP_SITE);
  if (bs[0] != 0x48 || bs[1] != 0x8d || bs[2] != 0x88 || cs[0] != 0x81 || cs[1] != 0xff) return -1;
  uint32_t base = *(const uint32_t*)(bs + 3), cap = *(const uint32_t*)(cs + 2);
  unsigned char* o = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
  unsigned char* blk = o ? *(unsigned char**)(o + 0x48) : 0;
  if (!blk || !cap || cap > 200000) return -1;
  int n = 0;
  for (uint32_t i = 0; i < cap; i++) {
    const unsigned char* m = blk + base + (size_t)i * MATCH_STRIDE;
    if (*(const uint16_t*)m != 0xffff && *(const uint16_t*)(m + 4) == reg && !(m[7] & 0x40)) n++;
  }
  return n;
}

/* the table of the played matches of regulations regs[0..nr): its clubs into out (reg and day
   left to the caller), the number of matches into *played; 0 clubs if the match table is not
   where it was */
static int count_table(const uint16_t* regs, int nr, final_t* out, int* played_out)
{
  *played_out = 0; out->n = 0;
  const unsigned char* bs = (const unsigned char*)(g_base + MATCH_BASE_SITE);
  const unsigned char* cs = (const unsigned char*)(g_base + MATCH_CAP_SITE);
  static int said;
  if (bs[0] != 0x48 || bs[1] != 0x8d || bs[2] != 0x88 || cs[0] != 0x81 || cs[1] != 0xff) {
    if (!said++) logf("fl26swiss: the match table's walk is not where it was (0x1413146e8); no table from matches");
    return 0;
  }
  uint32_t base = *(const uint32_t*)(bs + 3), cap = *(const uint32_t*)(cs + 2);
  unsigned char* o = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
  unsigned char* blk = o ? *(unsigned char**)(o + 0x48) : 0;
  if (!blk || !cap || cap > 200000) return 0;
  uint32_t club[FINAL_MAX]; int pts[FINAL_MAX], gd[FINAL_MAX], gf[FINAL_MAX];
  int n = 0, played = 0;
  for (uint32_t i = 0; i < cap; i++) {
    const unsigned char* m = blk + base + (size_t)i * MATCH_STRIDE;
    if (*(const uint16_t*)m == 0xffff || !(m[7] & 0x40)) continue;
    int mine = 0;
    for (int r = 0; r < nr; r++) if (*(const uint16_t*)(m + 4) == regs[r]) mine = 1;
    if (!mine) continue;
    uint32_t side[2] = { *(const uint32_t*)(m + 0x14), *(const uint32_t*)(m + 0x18) };
    int goals[2] = { m[0x1c], m[0x1f] }, at[2];
    for (int j = 0; j < 2; j++) {
      int k = 0;
      while (k < n && club[k] != side[j]) k++;
      if (k == n) {
        if (n >= FINAL_MAX || !(side[j] >> 14)) { k = -1; }
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
  *played_out = played;
  if (n < 4) return 0;
  for (int a = 1; a < n; a++)                     /* insertion sort, stable: points, difference, scored */
    for (int b = a; b > 0; b--) {
      int x = b - 1, y = b;
      if (pts[y] < pts[x] || (pts[y] == pts[x] && (gd[y] < gd[x] || (gd[y] == gd[x] && gf[y] <= gf[x])))) break;
      uint32_t c = club[x]; club[x] = club[y]; club[y] = c;
      int t = pts[x]; pts[x] = pts[y]; pts[y] = t;
      t = gd[x]; gd[x] = gd[y]; gd[y] = t;
      t = gf[x]; gf[x] = gf[y]; gf[y] = t;
    }
  out->n = (uint16_t)n;
  for (int k = 0; k < n; k++) out->club[k] = club[k];
  g_ctab_pts[0] = pts[0]; g_ctab_pts[1] = pts[1]; g_ctab_pts[2] = pts[n - 1];
  return n;
}
static int group_table(uint16_t reg, final_t* out, int* played_out, int* top, int* last);
static final_t* phase_table(uint16_t reg)
{
  const split_t* s;
  int d = abs_day(), played;
  if (reg <= 175 || split_part(reg, &s) < 2) return 0;
  if (g_ptab_day == d && g_ptab.reg == reg) return g_ptab.n ? &g_ptab : 0;
  g_ptab_day = d; g_ptab.reg = reg; g_ptab.day = d;
  /* B364 (09.11., mp46): a group of a split with a points carry ranks by the regular phase's
     points too -- counted from its own matches alone, Northern Ireland's 5th of the bottom six
     went to the play-off 778 while the kept final table had it 4th, and the chain refused it */
  int top, last, how = split_part(reg, &s) == 3 ? group_table(reg, &g_ptab, &played, &top, &last) : 0;
  if (how == 2 && g_ptab.n >= 4) {
    logf("fl26swiss: reg %u -- group table from %d played match(es) and the regular phase's: %08x %d pts on top ... last %08x %d pts",
         (unsigned)reg, played, g_ptab.club[0], top, g_ptab.club[g_ptab.n - 1], last);
    return &g_ptab;
  }
  int n = count_table(&reg, 1, &g_ptab, &played);
  if (n < 4 || played < n / 2) {
    logf("fl26swiss: reg %u -- %d played match(es) of %d club(s): no table from matches", (unsigned)reg, played, n);
    g_ptab.n = 0;
    return 0;
  }
  logf("fl26swiss: reg %u -- table from %d played matches: %08x %d pts, %08x %d pts ... last %08x %d pts",
       (unsigned)reg, played, g_ptab.club[0], g_ctab_pts[0], g_ptab.club[1], g_ctab_pts[1],
       g_ptab.club[n - 1], g_ctab_pts[2]);
  return &g_ptab;
}

/* a league position for the Club World Cup: the final table kept at the July teardown if it is
   this summer's, else the live table (in June it is the season just finished) once a match has
   been played, else -- a phase of our splits -- the table counted from its matches, else the
   league ordered by squad strength, else list order */
static uint32_t cwc_club(uint16_t reg, int rank, const char** how)
{
  if (assoc_source(reg)) {
    final_t* a = assoc_seed(reg);
    *how = "association squad strength";
    return a && rank >= 1 && rank <= a->n ? a->club[rank - 1] : 0;
  }
  final_t* f = final_of(reg);
  int d = abs_day();
  /* a whole season (seasonsum): a February-December league's, kept in December, stands until the
     next one as the Libertadores' places do (CONT_KEEP); with none kept yet, its first half */
  const ssum_t* ss = ssum_of(reg);
  if (ss) {
    if (f && rank <= f->n && d >= f->day && d - f->day < CONT_KEEP) { *how = "whole-season table"; return f->club[rank - 1]; }
    return ss->part[0] != reg ? cwc_club(ss->part[0], rank, how) : 0;
  }
  if (f && rank <= f->n && d >= f->day && d - f->day < 120) { *how = "kept table"; return f->club[rank - 1]; }
  unsigned char* rec = get_rec(reg);
  if (!rec) return 0;
  unsigned char* t = ((table_fn)(uintptr_t)(g_base + TABLE_RVA))(reg);
  uint32_t rows = t ? *(uint32_t*)(t + 0x3c0) : 0;
  if (rows && rows <= 48 && (uint32_t)rank <= rows && !unplayed(rec, t, rows)) { *how = "live table"; return *(uint32_t*)(t + (rank - 1) * 20); }
  final_t* p = phase_table(reg);
  if (p) { *how = "played matches"; return (uint32_t)rank <= p->n ? p->club[rank - 1] : 0; }
  final_t* s = seed_of(reg);
  if (s) { *how = "squad strength"; return (uint32_t)rank <= s->n ? s->club[rank - 1] : 0; }
  *how = "list order";
  return (uint32_t)rank <= rec_count(rec) ? rec_clubs(rec)[rank - 1] : 0;
}

/* The game's own Club World Cup (a world without the 32): its field comes from the game's
 * pools, and the CAF champion of a world that builds the CAF Champions League never reaches it
 * (GitHub #70: no African club at all). The champion of each continental cup of ours that the
 * league champions go to takes the place of the first entrant of its confederation's
 * countries -- for the CAF ones Country.bin +5 == 5, flag ids 44..95, 98, 312 -- else of the
 * last entrant. The field the game offered is logged once a season, club, slot and country.
 * 0.2.0: the world file's confed line gives every country's confederation (fl26_swiss_confed),
 * and a champion takes the place of the first entrant of its own confederation -- the
 * CONCACAF champion an American club's, not an African one's; without the line, as before.
 * B149: the game's African entrant is the one club it files in Other Clubs (Africa), Wydad
 * Casablanca (9030). A world with Morocco's league takes it out of that group, the game then
 * offers 3 clubs for 4 places and the South American champion goes straight to the final with
 * an empty semi-final. The missing place is filled here: our CAF champion when there is one,
 * else Wydad from its league. */
#define CWC_AFRICA 9030u
/* the team lookup reads a handle's lower 14 bits as the club's row in the team array, so a bare id finds row 0: canon_club gives it Wydad's own row */
#define CWC_GAME_N 4u      /* the game's own cup: four clubs, whatever reg 1 still holds from last time */
#define MAX_CCUP_FWD 256  /* MAX_CCUP, defined with the continental cups below */
static int ccup_champions(uint32_t* out, int max, uint16_t* cup);
static int caf_country(int f) { return (f >= 44 && f <= 95) || f == 98 || f == 312; }
static uint8_t g_confed[512];   /* flag id -> confederation (2..7), from the world file */
static int g_confed_n;
static int confed_of(int f)
{
  if (f < 0 || f >= 512) return 0;
  if (g_confed_n) return g_confed[f];
  return caf_country(f) ? 5 : 0;
}
__declspec(dllexport) int fl26_swiss_confed(const uint16_t* v, int n)
{
  memset(g_confed, 0, sizeof g_confed);
  g_confed_n = 0;
  for (int i = 0; i < n; i++)
    if (v[2 * i] < 512 && v[2 * i + 1] >= 2 && v[2 * i + 1] <= 7) { g_confed[v[2 * i]] = (uint8_t)v[2 * i + 1]; g_confed_n++; }
  return g_confed_n;
}
static int team_country(void* blk, uint32_t club)
{
  unsigned char* t = blk ? ((teamget_fn)(uintptr_t)(g_base + TEAMGET_RVA))(blk, club) : 0;
  return t && *(uint32_t*)t >> 14 == club >> 14 ? *(uint16_t*)(t + 0x418) & 0x1ff : -1;
}
static u32vec* cwc_game_champions(u32vec* list)
{
  uint32_t cw[MAX_CCUP_FWD]; uint16_t cc[MAX_CCUP_FWD];
  int nw = ccup_champions(cw, MAX_CCUP_FWD, cc);
  size_t n = (size_t)(list->e - list->b);
  unsigned char* o = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
  void* blk = o ? *(void**)(o + 0x48) : 0;
  static uint32_t full[CWC_GAME_N];
  static u32vec fv;
  if (blk && n + 1 == CWC_GAME_N) {
    uint32_t add = 0;
    const char* how = "";
    for (int k = 0; k < nw && !add; k++)
      if (!has_club(list->b, n, cw[k]) && (g_confed_n ? confed_of(team_country(blk, cw[k])) : 5) == 5) {
        add = cw[k]; how = "our CAF champion";
      }
    if (!add) {
      unsigned char* t = ((teamget_fn)(uintptr_t)(g_base + TEAMGET_RVA))(blk, canon_club((uint32_t)CWC_AFRICA << 14));
      if (t && *(uint32_t*)t >> 14 == CWC_AFRICA && !has_club(list->b, n, *(uint32_t*)t)) {
        add = *(uint32_t*)t; how = "Wydad Casablanca, from its league";
      }
    }
    if (add) {
      for (size_t i = 0; i < n; i++) full[i] = list->b[i];
      full[n] = add;
      fv.b = full; fv.e = fv.c = full + n + 1;
      logf("fl26swiss: Club World Cup (the game's) -- %u club(s) offered for %u places; %08x added (%s)",
           (unsigned)n, CWC_GAME_N, add, how);
      list = &fv;
      n++;
    } else
      logf("fl26swiss: Club World Cup (the game's) -- %u club(s) offered for %u places; no CAF champion of ours and no Wydad (%08x) to add",
           (unsigned)n, CWC_GAME_N, canon_club((uint32_t)CWC_AFRICA << 14));
  }
  static int said_year = -1;
  int y = abs_day() / 365;
  if (said_year != y && blk) {
    said_year = y;
    logf("fl26swiss: Club World Cup (the game's) -- day %d, %u club(s) offered, %d champion(s) of ours", today(),
         (unsigned)n, nw);
    for (size_t i = 0; i < n && i < 40; i++) {
      unsigned char* t = ((teamget_fn)(uintptr_t)(g_base + TEAMGET_RVA))(blk, list->b[i]);
      int ok = t && *(uint32_t*)t >> 14 == list->b[i] >> 14;
      logf("fl26swiss:   entrant %2u: %08x slot %d country %d", (unsigned)i, list->b[i], ok ? slot_of(t) : -1,
           ok ? *(uint16_t*)(t + 0x418) & 0x1ff : -1);
    }
  }
  if (!blk) return list;
  /* B200 (Micarodvzla 23.10., r13 day 332 of 2030): with no entrant of its confederation a
     champion took the last place, whoever held it -- the CAF champion added above, then the
     CONCACAF champion put there one step before, and in his world the Libertadores winner. The
     places of our champions, of the clubs added above and of the European and South American
     entrants (confederations 2 and 4) are kept; the last other entrant gives way, else the
     champion stays out. */
  uint8_t keep[CWC_GAME_N + 8] = { 0 };
  for (size_t i = 0; i < n && i < sizeof keep; i++) {
    int cf = g_confed_n ? confed_of(team_country(blk, list->b[i])) : 0;
    keep[i] = list == &fv && i == n - 1 ? 1 : cf == 2 || cf == 4;
    for (int j = 0; j < nw; j++) if (list->b[i] == cw[j]) keep[i] = 1;
  }
  for (int k = 0; k < nw; k++) {
    if (has_club(list->b, n, cw[k])) continue;
    int want = g_confed_n ? confed_of(team_country(blk, cw[k])) : 5;
    size_t at = n;
    for (size_t i = 0; i < n && at == n; i++) {
      int mine = 0;
      for (int j = 0; j < nw; j++) if (list->b[i] == cw[j]) mine = 1;
      if (!mine && want && confed_of(team_country(blk, list->b[i])) == want) at = i;
    }
    const char* how = want == 5 ? "an African entrant" : "an entrant of its confederation";
    if (at == n) {
      for (size_t i = n; i-- > 0 && at == n; ) if (i >= sizeof keep || !keep[i]) at = i;
      how = "the last entrant not kept, none of its confederation offered";
    }
    if (at == n) {
      logf("fl26swiss: Club World Cup (the game's) -- winner of cup %u %08x stays out: no entrant of its confederation and every place kept",
           (unsigned)cc[k], cw[k]);
      continue;
    }
    logf("fl26swiss: Club World Cup (the game's) -- winner of cup %u %08x in place of %08x (%s)", (unsigned)cc[k], cw[k],
         list->b[at], how);
    list->b[at] = cw[k];
    if (at < sizeof keep) keep[at] = 1;
  }
  return list;
}

static uint32_t g_cwc[CWC_N];
static int cwc_add(unsigned* n, uint32_t c)
{
  if (*n >= CWC_N || !(c >> 14) || has_club(g_cwc, *n, c)) return 0;
  g_cwc[(*n)++] = c;
  return 1;
}

/* ---- the field by confederation (the user's rule, 2026-11-17) ----
 * 12 UEFA, 6 CONMEBOL, 5 AFC, 4 CAF, 4 CONCACAF, 1 OFC = 32 (FIFA's 2025 shares; the host's place
 * goes to the AFC). The OFC place (the user's rule, 2026-11-21) is the best OFC club of the
 * ranking, no title first; a world with no OFC club in the ranking gives it to the AFC (until
 * 21.11. there was no OFC place: 5 AFC, 5 CAF). Each other confederation takes first the champions
 * of its continental cup(s) of the four seasons before the cup is played (titles of the years
 * T-4 .. T-1 for a cup played in June of T; a club with two titles is in once), then the best of
 * the ranking (fl26cwc.dll: the confederation ranking's points of the four-season window) until
 * its places are full. No limit per country. The titles are fl26cwc's too: fl26swiss tells it
 * every winner at the teardowns and at the draw (champ_note), and it keeps them in each save's
 * ledger. Without fl26cwc.dll (or before it has anything) the old access list is used.
 * Pots of eight in list order (the game's group draw): the four best UEFA and the four best
 * CONMEBOL clubs, then the other eight UEFA clubs, then the other sixteen by their points. */
typedef int (*cwcchamps_fn)(uint16_t*, uint32_t*, uint16_t*, uint16_t*, int);
typedef int (*cwcrank_fn)(uint32_t*, int32_t*, int);
typedef int (*cwcchamp_fn)(int, uint32_t);
static FARPROC cwc_rank_proc(const char* name)
{
  HMODULE h = GetModuleHandleA("fl26cwc.dll");
  return h ? GetProcAddress(h, name) : 0;
}
/* titles: 1 the champions of the four seasons first, 0 the ranking only. The OFC comes before the
   AFC so that a place it cannot fill goes to the AFC (cwc_quota_field) */
#define CWC_OFC 7
#define CWC_AFC 3
static const struct { uint8_t confed, places; uint16_t cup; const char* name; uint8_t titles; } CWC_QUOTA[] = {
  { 2, 12, 4, "UEFA", 1 }, { 4, 6, 10, "CONMEBOL", 1 }, { CWC_OFC, 1, 0, "OFC", 0 }, { CWC_AFC, 5, 16, "AFC", 1 },
  { 5, 4, 0, "CAF", 1 }, { 6, 4, 0, "CONCACAF", 1 },
};
#define CWC_NQ ((int)(sizeof CWC_QUOTA / sizeof CWC_QUOTA[0]))
#define CWC_RANK_MAX 4000
static uint32_t g_cwrk_id[CWC_RANK_MAX]; static int32_t g_cwrk_q[CWC_RANK_MAX];
static int cwc_points(uint32_t c, int nrk)
{
  for (int i = 0; i < nrk; i++) if (g_cwrk_id[i] == c >> 14) return g_cwrk_q[i];
  return 0;
}
static int cwc_confed_of(void* blk, uint32_t c) { return confed_of(team_country(blk, c)); }
/* 1 and the field in g_cwc (CWC_N clubs, in pot order), 0 when it cannot be made this way */
static int cwc_quota_field(int play_year, u32vec* offered)
{
  cwcchamps_fn champs = (cwcchamps_fn)(void*)cwc_rank_proc("fl26_cwc_champions");
  cwcrank_fn rank = (cwcrank_fn)(void*)cwc_rank_proc("fl26_cwc_ranking");
  unsigned char* o = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
  void* blk = o ? *(void**)(o + 0x48) : 0;
  if (!champs || !rank || !blk || !g_confed_n) {
    logf("fl26swiss: Club World Cup -- %s; the old access list picks the field",
         !champs || !rank ? "no fl26cwc.dll with the ranking (fl26_cwc_ranking)" : !g_confed_n ? "no confed line in the world file" : "no career");
    return 0;
  }
  int nrk = rank(g_cwrk_id, g_cwrk_q, CWC_RANK_MAX);
  static uint16_t creg[256], cyear[256], cday[256]; static uint32_t cclub[256];
  int nch = champs(creg, cclub, cyear, cday, 256);
  uint16_t cups[MAX_CCUP_FWD + 3]; int ncups = champ_cups(cups, MAX_CCUP_FWD + 3);
  logf("fl26swiss: Club World Cup %d -- by confederation: %d club(s) in the ranking, %d title(s) kept, %d champions' cup(s)",
       play_year, nrk, nch, ncups);
  static uint32_t part[CWC_NQ][CWC_N]; int np[CWC_NQ] = { 0 };
  unsigned n = 0;
  int to_afc = 0;                                   /* the OFC's places it had no club for */
  for (int q = 0; q < CWC_NQ; q++) {
    int conf = CWC_QUOTA[q].confed, want = CWC_QUOTA[q].places;
    if (conf == CWC_AFC && to_afc) {
      want += to_afc;
      logf("fl26swiss: Club World Cup -- AFC: %d place(s) + %d of the OFC's", CWC_QUOTA[q].places, to_afc);
    }
    /* the titles, newest first */
    for (int i = nch - 1; CWC_QUOTA[q].titles && i >= 0 && np[q] < want; i--) {
      int is_cup = 0;
      for (int k = 0; k < ncups; k++) if (cups[k] == creg[i]) is_cup = 1;
      if (!is_cup) continue;
      int year = cyear[i] - (cday[i] <= NEWYEAR_TO ? 1 : 0);    /* told at New Year: last year's final */
      if (year < play_year - 4 || year > play_year - 1) continue;
      uint32_t c = canon_club(cclub[i]);
      int cf = cwc_confed_of(blk, c);
      if (!cf && creg[i] == CWC_QUOTA[q].cup) cf = conf;
      if (cf != conf || !(c >> 14) || has_club(g_cwc, n, c)) continue;
      if (cwc_add(&n, c)) {
        part[q][np[q]++] = c;
        logf("fl26swiss:   %s %2d: champion of cup %u in %d -> %08x (%d.%02d pts)", CWC_QUOTA[q].name, np[q],
             (unsigned)creg[i], year, c, cwc_points(c, nrk) / 4, cwc_points(c, nrk) % 4 * 25);
      }
    }
    /* the ranking */
    for (int i = 0; i < nrk && np[q] < want; i++) {
      uint32_t c = canon_club(g_cwrk_id[i] << 14);
      if (!(c >> 14) || cwc_confed_of(blk, c) != conf || has_club(g_cwc, n, c)) continue;
      if (cwc_add(&n, c)) {
        part[q][np[q]++] = c;
        logf("fl26swiss:   %s %2d: ranking %d -> %08x (%d.%02d pts)", CWC_QUOTA[q].name, np[q], i + 1, c,
             g_cwrk_q[i] / 4, g_cwrk_q[i] % 4 * 25);
      }
    }
    if (np[q] < want && conf == CWC_OFC) {
      to_afc = want - np[q];
      logf("fl26swiss: Club World Cup -- OFC: no club of it in the ranking for %d place(s): they go to the AFC", to_afc);
    } else if (np[q] < want)
      logf("fl26swiss: Club World Cup -- %s: %d of %d places filled (no cup or no ranked club of it in this world); "
           "the rest go to the best of the ranking", CWC_QUOTA[q].name, np[q], want);
  }
  /* places a confederation could not fill (the user's rule, 2026-11-21: a world without that
     continent's cups or clubs): the best club of the whole ranking not yet in, whatever its
     confederation. Before, the game's entrants and the old access list (fixed regulation ids,
     no CAF or OFC club) came first. */
  for (int i = 0; i < nrk && n < CWC_N; i++) {
    uint32_t c = canon_club(g_cwrk_id[i] << 14);
    if (cwc_add(&n, c)) logf("fl26swiss:   extra: ranking %d -> %08x (a confederation short of clubs)", i + 1, c);
  }
  /* the ranking itself short of 32 clubs (a first season with few continental matches): the
     game's own entrants, then the old access list, whatever the confederation */
  for (size_t k = 0; offered && k < (size_t)(offered->e - offered->b) && n < CWC_N; k++)
    if (cwc_add(&n, offered->b[k]))
      logf("fl26swiss:   extra: the game's entrant -> %08x (the ranking short of clubs)", offered->b[k]);
  for (size_t k = 0; k < sizeof CWC_ACCESS / sizeof CWC_ACCESS[0] && n < CWC_N; k++) {
    const char* how = "";
    for (int r = CWC_ACCESS[k].rank; r <= FINAL_MAX; r++) {
      uint32_t c = cwc_club(CWC_ACCESS[k].reg, r, &how);
      if (!c) break;
      if (cwc_add(&n, c)) {
        logf("fl26swiss:   extra: reg %u position %d -> %08x (%s, the ranking short of clubs)",
             (unsigned)CWC_ACCESS[k].reg, r, c, how);
        break;
      }
    }
  }
  if (n != CWC_N) {
    logf("fl26swiss: Club World Cup -- %u of %u clubs by confederation; the old access list picks the field", n, CWC_N);
    return 0;
  }
  /* pots (user, 17.11.): pot 1 = UEFA 1-4 + CONMEBOL 1-4; pots 2-4 = every other club by points */
  for (int q = 0; q < CWC_NQ; q++)                  /* each confederation's best first */
    for (int a = 1; a < np[q]; a++)
      for (int b = a; b > 0 && cwc_points(part[q][b], nrk) > cwc_points(part[q][b - 1], nrk); b--) {
        uint32_t t = part[q][b]; part[q][b] = part[q][b - 1]; part[q][b - 1] = t;
      }
  static uint32_t rest[CWC_N]; int nr = 0, k = 0;
  uint32_t out[CWC_N];
  for (int i = 0; i < 4 && i < np[0]; i++) out[k++] = part[0][i];
  for (int i = 0; i < 4 && i < np[1]; i++) out[k++] = part[1][i];
  for (int i = 4; i < np[0]; i++) rest[nr++] = part[0][i];
  for (int i = 4; i < np[1]; i++) rest[nr++] = part[1][i];
  for (int q = 2; q < CWC_NQ; q++) for (int i = 0; i < np[q]; i++) rest[nr++] = part[q][i];
  for (unsigned i = 0; i < n; i++) {                 /* the extras */
    int there = 0;
    for (int j = 0; j < k; j++) if (out[j] == g_cwc[i]) there = 1;
    for (int j = 0; j < nr; j++) if (rest[j] == g_cwc[i]) there = 1;
    if (!there && nr < CWC_N) rest[nr++] = g_cwc[i];
  }
  for (int a = 1; a < nr; a++)
    for (int b = a; b > 0 && cwc_points(rest[b], nrk) > cwc_points(rest[b - 1], nrk); b--) {
      uint32_t t = rest[b]; rest[b] = rest[b - 1]; rest[b - 1] = t;
    }
  for (int i = 0; i < nr && k < CWC_N; i++) out[k++] = rest[i];
  if (k != CWC_N) { logf("fl26swiss: Club World Cup -- pots came to %d clubs; the old access list picks the field", k); return 0; }
  memcpy(g_cwc, out, sizeof out);
  for (int pot = 0; pot < 4; pot++)
    logf("fl26swiss: Club World Cup -- pot %d: %08x %08x %08x %08x %08x %08x %08x %08x", pot + 1,
         g_cwc[pot * 8], g_cwc[pot * 8 + 1], g_cwc[pot * 8 + 2], g_cwc[pot * 8 + 3], g_cwc[pot * 8 + 4],
         g_cwc[pot * 8 + 5], g_cwc[pot * 8 + 6], g_cwc[pot * 8 + 7]);
  return 1;
}

static int pot_draw(const uint32_t* field, const int* key, unsigned n, int groups,
                    uint32_t grp[][8], int* tries);
static char cwc_setcl(uint64_t id, u32vec* list, uint64_t flag)
{
  unsigned char* rec = get_rec(CWC_REG);
  unsigned char* g0 = get_rec(cwc_rep(0));
  size_t offered = list && list->b ? (size_t)(list->e - list->b) : 0;
  static int drawn_year = -1;
  int play_year = cwc_play_year();
  /* the year alone is not enough: a save of before the draw, loaded in the same game run, has
     no clubs in reg 1 although this run drew that year (17.11.: the cup stayed empty) */
  int held = rec && g0 && rec_count(rec) == CWC_N && rec_count(g0);
  if ((g_cwc_every <= 1 || !g_cwc_first) ? held
                                         : (held && play_year >= 0 && drawn_year == play_year)) {
    logf("fl26swiss: Club World Cup -- the game offered %u club(s) on day %d, but the 32 are already drawn; ignored",
         (unsigned)offered, today());
    return 1;
  }
  unsigned n = 0, gaps = 0, game = 0;
  const size_t POT3 = 24;
  champ_note("the Club World Cup draw");
  if (cwc_quota_field(play_year, list)) {
    n = CWC_N;
    goto drawn;
  }
  n = 0;
  for (size_t i = 0; i < sizeof CWC_ACCESS / sizeof CWC_ACCESS[0]; i++) {
    if (i == POT3) {                                 /* the game's own entrants open pot 4, */
      uint32_t cw[MAX_CCUP_FWD]; uint16_t cc[MAX_CCUP_FWD];   /* after the champions of our */
      int nw = ccup_champions(cw, MAX_CCUP_FWD, cc);           /* continental cups (#70)      */
      for (int k = 0; k < nw; k++)
        if (cwc_add(&n, cw[k]))
          logf("fl26swiss:   Club World Cup %2u: winner of cup %u -> %08x", n, (unsigned)cc[k], cw[k]);
      for (size_t k = 0; k < offered; k++) if (cwc_add(&n, list->b[k])) game++;
    }
    const char* how = "";
    uint32_t c = 0;
    for (int rank = CWC_ACCESS[i].rank; rank <= FINAL_MAX; rank++) {
      c = cwc_club(CWC_ACCESS[i].reg, rank, &how);
      if (!c) break;
      if ((c >> 14) && !has_club(g_cwc, n, c)) break;
      c = 0;
    }
    if (c && cwc_add(&n, c))
      logf("fl26swiss:   Club World Cup %2u: reg %u position %u -> %08x (%s)", n, (unsigned)CWC_ACCESS[i].reg,
           (unsigned)CWC_ACCESS[i].rank, c, how);
    else gaps++;
  }
  static const uint16_t RESERVE[5] = { R_ENG, R_ESP, R_ITA, R_GER, R_FRA };
  for (int rank = 3, stuck = 0; n < CWC_N && rank <= FINAL_MAX && stuck < 2; rank++) {
    unsigned before = n; const char* how;
    for (int j = 0; j < 5 && n < CWC_N; j++) cwc_add(&n, cwc_club(RESERVE[j], rank, &how));
    stuck = n == before ? stuck + 1 : 0;
  }
  logf("fl26swiss: Club World Cup -- day %d: the game offered %u, field %u (%u of the game's, %u list places without a club)",
       today(), (unsigned)offered, n, game, gaps);
drawn:
  if (n != CWC_N) {
    logf("fl26swiss: Club World Cup -- short field; the game's own entrants stand");
    return ((setclr_fn)(uintptr_t)g_tramp_setcl)(id, list, flag);
  }
  u32vec v = { g_cwc, g_cwc + CWC_N, g_cwc + CWC_N };
  drawn_year = play_year;
  char ok = ((setclr_fn)(uintptr_t)g_tramp_setcl)(id, &v, flag);
  run_flush();
  u32vec w = { g_cwc, g_cwc + CWC_N, g_cwc + CWC_N };
  ((gdraw_fn)(uintptr_t)(g_base + GDRAW_RVA))(CWC_REG, &w, 1);
  run_flush();
  /* The game's group draw deals the entry order out pot by pot in order (17.11.: the groups came
     out as the ranking), so the groups are drawn here: one club of each pot in every group, the
     group picked at random, clubs of one country kept apart where a draw allows it (pot_draw, the
     Sudamericana's), and each group's list handed to the game. */
  {
    uint32_t grp[8][8]; int key[CWC_N], tries = 0;
    unsigned char* own = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
    void* blk = own ? *(void**)(own + 0x48) : 0;
    for (int i = 0; i < CWC_N; i++) key[i] = blk ? club_key(blk, g_cwc[i], i) : 3000 + i;
    int best = pot_draw(g_cwc, key, CWC_N, CWC_GROUPS, grp, &tries);
    logf("fl26swiss: Club World Cup -- groups drawn from the pots: %d same-country pair(s) after %d draw(s)",
         best, tries);
    for (int g = 0; g < CWC_GROUPS; g++) {
      u32vec gv = { grp[g], grp[g] + 4, grp[g] + 4 };
      ((setclr_fn)(uintptr_t)g_tramp_setcl)(cwc_rep(g), &gv, 1);
      run_flush();
      logf("fl26swiss: Club World Cup -- group %c: %08x %08x %08x %08x", 'A' + g,
           grp[g][0], grp[g][1], grp[g][2], grp[g][3]);
    }
  }
  char line[160]; int p = 0;
  for (int g = 0; g < CWC_GROUPS; g++) {
    unsigned char* rg = get_rec(cwc_rep(g));
    p += snprintf(line + p, sizeof line - p, " %c:%u", 'A' + g, rg ? rec_count(rg) : 0);
  }
  logf("fl26swiss: Club World Cup -- reg 1 holds %u, groups%s", rec ? rec_count(rec) : 0, line);
  /* The groups have to enter the season themselves. A competition due on a registration date
   * goes through register_all 0x141343bf0, which runs the door for the master and then for
   * every row whose parent field (+0x76) names it -- that is how the Libertadores groups get
   * their fixtures. The Club World Cup is started by the rollover pass instead (task 5, then
   * the season builder 0x1413156e0), which runs the door for reg 1 alone: a group master
   * (kind 2) builds nothing itself, so on 2026-09-27 the 32 were drawn and no match was ever
   * made. Here the eight groups are handed to register_all, the same call the Libertadores
   * gets. */
  uint16_t reps[CWC_GROUPS];
  for (int g = 0; g < CWC_GROUPS; g++) reps[g] = cwc_rep(g);
  struct { uint16_t* b; uint16_t* e; uint16_t* c; } rv = { reps, reps + CWC_GROUPS, reps + CWC_GROUPS };
  ((regall_fn)(uintptr_t)(g_base + REGALL_RVA))(0, &rv);
  run_flush();
  logf("fl26swiss: Club World Cup -- groups %u..%u handed to register_all", (unsigned)reps[0],
       (unsigned)reps[CWC_GROUPS - 1]);
  return ok;
}

/* The game hands regulation 1 its four entrants (day 332). With Mod Studio's Intercontinental
 * (ic_world) they go there every year, as the old cup had them (cwc_game_champions: our CAF
 * champion, our continental champions), and it is started at once; the 32-club draw is made
 * only in a year of the cycle, from the list as the game offered it. */
static char ic_fill(u32vec* list, uint64_t flag)
{
  static int done_year = -1;
  int y = cwc_play_year();
  unsigned char* ic = get_rec(g_ic_reg);
  if (y >= 0 && done_year == y && ic && rec_count(ic)) {   /* a save of before it, loaded: fill again */
    logf("fl26swiss: Intercontinental -- offered again on day %d; already filled this season (reg %u holds %u)",
         today(), (unsigned)g_ic_reg, ic ? rec_count(ic) : 0);
    return 1;
  }
  char ok = ((setclr_fn)(uintptr_t)g_tramp_setcl)(g_ic_reg, list, flag);
  run_flush();
  done_year = y;
  uint16_t ids[1] = { g_ic_reg };
  struct { uint16_t* b; uint16_t* e; uint16_t* c; } rv = { ids, ids + 1, ids + 1 };
  ((regall_fn)(uintptr_t)(g_base + REGALL_RVA))(0, &rv);
  run_flush();
  logf("fl26swiss: Intercontinental -- day %d: reg %u now %u club(s) (%08x %08x %08x %08x), handed to register_all",
       today(), (unsigned)g_ic_reg, ic ? rec_count(ic) : 0,
       list->e - list->b > 0 ? list->b[0] : 0, list->e - list->b > 1 ? list->b[1] : 0,
       list->e - list->b > 2 ? list->b[2] : 0, list->e - list->b > 3 ? list->b[3] : 0);
  return ok;
}
static char cwc_handoff(uint64_t id, u32vec* list, uint64_t flag)
{
  static uint32_t orig[64];
  size_t n = list && list->b && list->e > list->b ? (size_t)(list->e - list->b) : 0;
  if (n > 64) n = 64;
  for (size_t i = 0; i < n; i++) orig[i] = list->b[i];
  u32vec as_offered = { orig, orig + n, orig + n };
  char ok = 1;
  champ_note("day of the Club World Cup entrants");
  if (g_ic_reg && n) {
    if (ic_world()) ok = ic_fill(cwc_game_champions(list), flag);
    else logf("fl26swiss: Intercontinental -- reg %u is not the Intercontinental in this career (an older save?); left alone",
              (unsigned)g_ic_reg);
  }
  int y;
  if (!cwc_cycle_year(&y)) {
    logf("fl26swiss: Club World Cup -- day %d: %d is not a year of the cycle (every %u from %u); no draw",
         today(), y, (unsigned)g_cwc_every, (unsigned)g_cwc_first);
    return ok;
  }
  return cwc_setcl(id, &as_offered, flag);
}

/* the group stage is over: winners and runners-up into the knockout, in the 2025 bracket */
static unsigned g_cwc_groups_done = 0;
static int g_cwc_groups_day = -1;
static int season_played(uint16_t reg);
static int cwc_progress(uint16_t r, void* started)
{
  /* The reports are kept in memory, so a save loaded in the same game run (17.11.) would keep the
     groups reported in the other timeline: the date going back forgets them. A group whose every
     match is played counts as well, so one over before the save loaded is not waited for again. */
  (void)abs_day();                                  /* moves g_timeline on when the date went back */
  if (g_cwc_groups_day >= 0 && g_timeline != g_cwc_groups_day) {
    logf("fl26swiss: Club World Cup -- the date went back (a save loaded): groups reported %02x forgotten",
         g_cwc_groups_done);
    g_cwc_groups_done = 0;
  }
  g_cwc_groups_day = g_timeline;
  if (r == CWC_REG) g_cwc_groups_done = (1u << CWC_GROUPS) - 1;
  else g_cwc_groups_done |= 1u << (((r >> 10) - 1) & 31);
  unsigned played = 0;
  for (int g = 0; g < CWC_GROUPS; g++) if (season_played(cwc_rep(g))) played |= 1u << g;
  logf("fl26swiss: Club World Cup -- progression for reg %u on day %d (groups reported %02x, all played %02x)",
       (unsigned)r, today(), g_cwc_groups_done, played);
  g_cwc_groups_done |= played;
  if (g_cwc_groups_done != (1u << CWC_GROUPS) - 1) return 0;
  unsigned char* ko = get_rec(CWC_KO);
  if (!ko || rec_count(ko)) return 0;
  static uint32_t buf[16];
  for (int i = 0; i < 16; i++) {
    uint16_t rep = cwc_rep(CWC_BRACKET[i][0]);
    unsigned char* t = ((table_fn)(uintptr_t)(g_base + TABLE_RVA))(rep);
    uint32_t rows = t ? *(uint32_t*)(t + 0x3c0) : 0;
    if (rows < 2 || rows > 8) {
      logf("fl26swiss: Club World Cup -- group %c has a table of %u rows; knockout not filled",
           'A' + CWC_BRACKET[i][0], (unsigned)rows);
      return 0;
    }
    buf[i] = *(uint32_t*)(t + CWC_BRACKET[i][1] * 20);
  }
  u32vec v = { buf, buf + 16, buf + 16 };
  ((setcl_fn)(uintptr_t)(g_base + SETCL_RVA))(CWC_KO, &v, 1);
  run_flush();
  logf("fl26swiss: Club World Cup -- knockout reg %u now %u clubs (A1 %08x v B2 %08x ...)",
       (unsigned)CWC_KO, rec_count(ko), buf[0], buf[1]);
  g_cwc_groups_done = 0;
  if (rec_count(ko) != 16) return 0;
  start_stage(started, CWC_KO);
  return 1;
}

/* the Intercontinental is the shipped cup on another id: the game dates cups by id, so it asks
   for the shipped regulation 1's days (348, 349, 351, 352), which its own shape takes */
static uint64_t ic_dates(uint16_t id, uint64_t reg, void* vec)
{
  uint64_t rv = ((date_fn)(uintptr_t)g_tramp_date)((reg & ~(uint64_t)0xffff) | CWC_REG, vec);
  vec_t* v = (vec_t*)vec;
  size_t have = (v->b && v->e >= v->b) ? (size_t)(v->e - v->b) / sizeof(date_t) : 0;
  const date_t* r = (const date_t*)v->b;
  static int said = -1;
  int y = cwc_play_year();
  if (said != y) {
    said = y;
    if (have) logf("fl26swiss: Intercontinental -- reg %u dated as the old Club World Cup: %u date(s), days %u..%u",
                   (unsigned)id, (unsigned)have, r[0].day, r[have - 1].day);
    else logf("fl26swiss: Intercontinental -- reg %u: the game gave no dates", (unsigned)id);
  }
  return rv;
}

/* dates: borrow the World Cup's records, keep their rounds and kinds, move the days */
static uint64_t cwc_dates(uint16_t id, uint64_t reg, void* vec)
{
  int ko = id == CWC_KO;
  vec_t* v = (vec_t*)vec;
  size_t at = (v->b && v->e >= v->b) ? (size_t)(v->e - v->b) : 0;
  uint64_t rv = ((date_fn)(uintptr_t)g_tramp_date)((reg & ~(uint64_t)0xffff) | (ko ? R_WCKO : R_WCGROUP), vec);
  size_t have = (v->b && v->e >= v->b) ? (size_t)(v->e - v->b) / sizeof(date_t) : 0;
  size_t want = ko ? 10 : 6;
  /* League Mode (17.11.): it has no national-team tournaments, and the World Cup's group stage
     (34) gives no dates there -- the 32 were drawn and never played. The Libertadores' group
     stage (9) is in every mode and, like 34, comes cut to the caller's shape (a CWC group played
     once asks for 3); its rounds keep their order and the days are moved below as before. */
  size_t was = have;
  int lib = 0;
  if (!ko && (have == 0 || have > want)) {
    if (v->b) v->e = v->b + at;
    rv = ((date_fn)(uintptr_t)g_tramp_date)((reg & ~(uint64_t)0xffff) | 9, vec);
    have = (v->b && v->e >= v->b) ? (size_t)(v->e - v->b) / sizeof(date_t) : 0;
    lib = 1;
    /* 17.11.: but reg 9 is NOT cut: it gives its 6 home-and-away rounds to a group played once,
       which plays only rounds 0..2 -- spread over the 6 June days they fell on 153, 154 and 157
       (two matches on consecutive days). Keep its first 3, as 34 gives: days 153, 157, 161. */
    if (have > 3 && have <= want) { v->e = v->b + 3 * sizeof(date_t); have = 3; }
  }
  date_t* r = (date_t*)v->b;
  { static int last_id = -1, last_day = -1;         /* each id once a day: the groups ask one by one */
    if (last_id != (int)id || last_day != today()) {
      last_id = id; last_day = today();
      if (lib) logf("fl26swiss: Club World Cup -- reg %u, day %d: the World Cup's group stage gave %u date(s), "
                    "the Libertadores' (reg 9) %u%s", (unsigned)id, today(), (unsigned)was, (unsigned)have,
                    have > want ? " (too many: left as it is)" : "");
      else logf("fl26swiss: Club World Cup -- reg %u, day %d: %u date(s) from the World Cup's %s",
                (unsigned)id, today(), (unsigned)have, ko ? "knockout" : "group stage");
      for (size_t i = 0; i < have && i < 12; i++)
        logf("fl26swiss: Club World Cup -- reg %u record %u: day %u round %u kind %u", (unsigned)id,
             (unsigned)i, r[i].day, r[i].round, r[i].kind);
    }
  }
  static unsigned said = 0; unsigned bit = ko ? 1 : 2;
  /* The game hands back only as many records as the caller's shape needs, not the whole
   * borrowed array: a group of four played once asked for 3 (measured 2026-09-26), where the
   * World Cup's own group has 6. Left on the World Cup's days (182 on) the groups fell after
   * the July teardown and no match was ever made. So any count up to `want` is spread over
   * the June days, keeping their order. */
  if (have == 0 || have > want) {
    if (!(said & bit)) logf("fl26swiss: Club World Cup -- reg %u: the borrowed calendar has %u records (up to %u expected); left as it is",
                            (unsigned)id, (unsigned)have, (unsigned)want);
    said |= bit;
    return rv;
  }
  if (!(said & bit))
    for (size_t i = 0; i < have; i++)
      logf("fl26swiss: Club World Cup -- reg %u borrowed record %u: day %u round %u kind %u", (unsigned)id,
           (unsigned)i, r[i].day, r[i].round, r[i].kind);
  for (size_t i = 0; i < have; i++) {
    size_t k = i * want / have;
    r[i].day = ko ? CWC_KO_DAYS[k] : CWC_GROUP_DAYS[k];
  }
  cont_note(CWC_REG, vec);                         /* reg 1's days, for the leagues that feed it */
  if (!(said & bit))
    logf("fl26swiss: Club World Cup -- reg %u dated: %s days %u..%u (%u records)", (unsigned)id,
         ko ? "knockout" : "groups", r[0].day, r[have - 1].day, (unsigned)have);
  said |= bit;
  return rv;
}

/* ---- continental cups of the world file: groups of four, then a knockout ----
 *
 * For a continent the game has no club competition of its own (Africa first: the CAF Champions
 * League and the Confederation Cup). tools/mkccup.py builds each as a new competition -- a group
 * stage cloned from the Copa Libertadores' (master + one replica per group, home and away) and a
 * knockout cloned from the Europa League's -- and the world file names it:
 *
 *   ccup <groups master> ko=<knockout> groups=<n> entry=<reg>:<position>,... name=<text>
 *
 * The exe knows nothing of these ids, so everything the game would do for its own cups happens
 * here, the Club World Cup way: the field is taken from league tables when the Champions League
 * play-off progresses (the day the Conference League is filled, late August), drawn with the
 * game's group draw (entry order = pots of `groups`), and the group rows are handed to
 * register_all; when every group is over, winners and runners-up go into the knockout (A1-B2,
 * C1-D2 ... then B1-A2, D1-C2 ...), which is started. Dates are borrowed -- the Libertadores
 * group stage (reg 9) and the Champions League knockout (reg 4) -- and moved to the days below.
 * A cup whose rows are not all in the world is left alone.
 *
 * `groups=0` is a straight knockout (the CONCACAF Champions Cup): the master is the knockout
 * itself (`ccup <ko> ko=<ko> groups=0`), filled on the same day with the entries in the order
 * given -- first v second, third v fourth ... -- and started at once.
 *
 * An entry at position 0 is the winner of that regulation, a cup (<reg>:0): a super cup of two
 * clubs, the CAF Super Cup, is `entry=<CAF CL knockout>:0,<Confederation Cup knockout>:0`. The
 * winners are kept at the July teardown, before our cups are closed, as the UEFA holders are
 * (access_capture); a cup nobody has won yet (a new career) leaves the super cup unfilled.
 *
 * `alt=<entry>:<league>,...` (0.2.0, GitHub #95): that entry is a national cup's winner, and the
 * league is where its place goes when there is no winner to send -- a new career, a winner
 * already in this cup or another continental one (ccup_taken), or in its league cup's pre-round:
 * the best club of that league not playing yet, as a UEFA cup winner's place goes (access_build).
 * Only those entries are held to ccup_taken; a super cup's winners play their own cups anyway.
 *
 * A single-match league cup (0.2.0, `like=<shipped cup>` on the ccup line, fl26_swiss_ccup_like):
 * the knockout row is a copy of a shipped domestic cup -- ENGLAND_D1_CUP, format 2, one match a
 * round, bracket = field -- so it takes any field the bracket screen draws (2-16, 18, 20, 24, 28,
 * 30, 32, 44), not only 2/4/8/16/32. The game lays the bracket out with byes where the field is
 * not a power of two (44: twelve first-round ties, twenty clubs straight into the round of 32),
 * and the cup draw (cupdraw mode 3, `draw=byes`) gives the byes to the top division and draws
 * every tie at random. Its rounds are dated as the shipped cup's (calendar case 6: round ids
 * 0x2e, 0x2f, 0x30, 0x33, 0x34, 0x35) and moved to the cup's own days, one per round. The
 * live row is checked before any of it (ccup_like_ok): a career whose save still holds the old
 * two-legged copy of the Europa League knockout under the same id keeps the old way, with the
 * first entries that fit its bracket. */
#define MAX_CCUP 256     /* 8 until 0.2.0, 16 until the limits branch: a league cup per country next to
                            the continental, playoff and pre-season cups (leaguebuilder MAX_CCUP) */
_Static_assert(MAX_CCUP == MAX_CCUP_FWD, "the Club World Cup sizes its list of champions by MAX_CCUP_FWD");
#define CCUP_MAX_GROUPS 8
#define CCUP_MAX_ENTRY 48     /* 32 until 0.2.0: a single-match league cup takes up to 44 */
#define CCUP_LIKE_MAX 44      /* the FA Cup's field: the largest a shipped cup has (and the screen draws) */
#define CCUP_MAX_DAYS 8
#define R_LIBGROUP 9
#define R_UCLKO    4
#define R_LIBKO    10
/* the options of fl26_swiss_ccup_opts: fill -- the calendar day the cup is filled on (0: with the
   Champions League play-off, late August); national -- its clubs may also be in another of these
   cups (a league cup's clubs play in the continental one too); days -- the knockout's own days in
   place of CCUP_KO_DAYS; clubs -- team ids invited by name, in place of the league positions */
typedef struct { uint16_t reg, ko, groups, n; uint16_t ereg[CCUP_MAX_ENTRY]; uint8_t erank[CCUP_MAX_ENTRY];
                 uint16_t ealt[CCUP_MAX_ENTRY];
                 uint8_t efrom[CCUP_MAX_ENTRY];   /* alt=: the first position of ealt to try */
                 uint16_t fill, national, nd, nc; uint16_t days[CCUP_MAX_DAYS]; uint32_t clubs[CCUP_MAX_ENTRY];
                 int filled_year;
                 int why_year;       /* the season ccup_fill_days last said why it could not fill it */
                 uint16_t like;      /* 0.2.0: the shipped domestic cup whose shape and dates it takes, 0 = none */
                 uint8_t region;     /* 0.2.4 (B35): 1 + its CR_ day table, 0 = not worked out (ccup_region) */
                 unsigned rgen;      /* g_ccup_gen it was worked out under */
                 uint8_t cal;        /* South American February-December calendar (fl26_swiss_ccup_cal) */
                 uint16_t first[CCUP_MAX_ENTRY]; /* optional first-season winner fallbacks (Recopa) */
               } ccup_t;
static ccup_t g_ccup[MAX_CCUP]; static int g_nccup = 0;
/* fl26_swiss_ccup_like's records, read by fl26_swiss_ccup (called after it): knockout -> shipped cup */
static uint16_t g_clike[MAX_CCUP][2]; static int g_nclike = 0;
static uint16_t clike_of(uint16_t ko)
{
  for (int i = 0; i < g_nclike; i++) if (g_clike[i][0] == ko) return g_clike[i][1];
  return 0;
}
/* a field the bracket screen draws and a shipped domestic cup's calendar dates every round of */
static int like_size_ok(unsigned n)
{
  if (n < 2 || n > CCUP_LIKE_MAX || n > CCUP_MAX_ENTRY) return 0;
  return n <= 16 || n == 18 || n == 20 || n == 24 || n == 28 || n == 30 || n == 32 || n == 44;
}
static uint32_t g_ccup_field[MAX_CCUP][CCUP_MAX_ENTRY]; static unsigned g_ccup_nf[MAX_CCUP];
static unsigned g_ccup_done[MAX_CCUP];
static int g_ccup_anew_year[MAX_CCUP];     /* B172: the season a group cup was last filled anew */
/* Midweek, the way UEFA plays (GitHub #70): a cup the league champions go to (the CAF Champions
   League) on the Tuesdays, the one below it -- no entry at position 1: the Confederation Cup,
   the AFC Champions League Two, the Sudamericana -- on the Wednesdays of the same weeks, as the
   Europa League takes the Champions League's: a league that feeds both keeps its Saturday three
   days clear of either (rest_dates), where a Thursday would leave it no day of the week at all.
   Weekdays on the big leagues' grid (case 5: Saturday is 261, so a Tuesday is d % 7 == 5).
   Groups late November to mid February, the knockout mid March to the final in mid May (the
   first pair is spare for a knockout of eight). They were the Mondays and Sundays.

   B35 (0.2.4, a tester's memory probe of a Master League): the game's own continental cups play
   midweek too, on their own weeks, and our cups sat on them -- the Copa Sudamericana's groups on
   the Libertadores qualifying days 34 and 41, its knockout on the Libertadores group days 76, 83,
   104, 118, 139, and the Tuesday cups (AFC Champions League Two) the day before the AFC Champions
   League's Wednesdays. The same club can be in both: our cups run August to May and are filled
   at the end of August (ccup_taken, #37), the game's calendar-year cups are filled on 1 January
   from that winter's tables. So a cup whose leagues can send a club to one of the game's cups
   (ccup_region: gc_feeds of its entries' leagues, the same test the league schedulers use) plays
   in the weeks the game leaves free: every day at least one free day from every day the exe
   ships for that competition (gc_seed: LIB_ + LIBQ_, AFC_ on its midweek), and from the Club
   World Cup's December days -- tools/native/test_rcal_days.c checks the tables against gc_seed's
   lists. Same weekdays (Tuesday the champions' cup, Wednesday the one below, same weeks), same
   number of days, groups November to February, the knockout from mid February or March, at least
   two weeks after the last group day (the knockout is filled when the groups are over,
   ccup_progress), and the final before 2 June (the Club World Cup of ours, CWC_GROUP_DAYS, starts
   on day 153):
     CR_LIB  the Libertadores' weeks free (34, 41 qualifying; 62, 76, 83, 104, 118, 139 groups):
             groups 25 Nov, 2 Dec, 21 Jan, 28 Jan, 18 Feb, 25 Feb; knockout 11 Mar / 1 Apr,
             8 / 22 Apr, 6 / 13 May, final 27 May (the Conference League's final day);
     CR_AFC  the AFC Champions League's weeks free (55, 62, 76, 97, 111, 125, 139, 146): from 18
             February it leaves only six free Wednesdays before June, so the January groups come a
             fortnight earlier (14 January to 4 February) and the knockout's spare pair -- the
             round of 16, played only by a knockout of sixteen -- opens on 18 February:
             groups 25 Nov, 2 Dec, 14, 21, 28 Jan, 4 Feb; knockout 18 Feb / 11 Mar, 25 Mar /
             1 Apr, 15 / 29 Apr, final 13 May;
     CR_NONE no competition of the game in its region (the CAF, CONCACAF and OFC cups): as before.
   (Dates for the Wednesdays, the Tuesdays a day earlier.) A cup whose leagues reach both the
   Libertadores and the AFC Champions League has no table clear of both (the two leave three free
   Wednesdays from March to May): it takes CR_LIB, logged. */
enum { CR_NONE = 0, CR_LIB, CR_AFC, CR_N };
static const char* const CR_NAME[CR_N] = { "the days of before", "the Libertadores' weeks free",
                                           "the AFC Champions League's weeks free" };
static const uint32_t CCUP_GROUP_DAYS[CR_N][2][6] = {
  { { 327, 334, 26, 33, 40, 47 }, { 328, 335, 27, 34, 41, 48 } },
  { { 327, 334, 19, 26, 47, 54 }, { 328, 335, 20, 27, 48, 55 } },
  { { 327, 334, 12, 19, 26, 33 }, { 328, 335, 13, 20, 27, 34 } },
};
static const uint32_t CCUP_KO_DAYS[CR_N][2][7] = {
  { { 75, 82, 96, 103, 117, 124, 138 }, { 76, 83, 97, 104, 118, 125, 139 } },
  { { 68, 89, 96, 110, 124, 131, 145 }, { 69, 90, 97, 111, 125, 132, 146 } },
  { { 47, 68, 82, 89, 103, 117, 131 }, { 48, 69, 83, 90, 104, 118, 132 } },
};
/* bumped by every setter a cup's region depends on (the cups, their alt= leagues, the access list,
   the cup draws), so ccup_region works it out again */
static unsigned g_ccup_gen = 1;
static int ccup_region(ccup_t* c);
/* first group day returned by the native Libertadores calendar, used as the end
   of a cal=1 cup's fill window */
static uint16_t g_ccup_gday0[MAX_CCUP];

static uint16_t ccup_rep(const ccup_t* c, int g) { return (uint16_t)(c->reg + 1024 * (g + 1)); }
/* the two entries behind a cup's place that is a pre-round tie's winner (<tie id>:0): for each
   its league and position, or for a cup winner (position 0) the league it falls back to (0 none)
   and the cup. Answers how many; 0 = the place is no pre-round tie's. (Defined below the
   pre-rounds.) */
static int ccup_behind(uint16_t ereg, uint16_t lg[2], uint8_t rank[2], uint16_t cup[2]);
/* 0: a champions' cup (Tuesdays), 1: the cup below (Wednesdays).
   A cup whose places ALL go through a pre-round names no league itself (12.11.2026, the CONCACAF
   Champions Cup of 16 behind a pre-round of 32): it was taken for the cup below -- its days a day
   later, its winner not kept as the continental champion, none for the Club World Cup. Then the
   pre-round's entries say it: champions among them = a champions' cup. A cup with places of its
   own (the CAF Confederation Cup: thirds and cup winners, and small countries' champions in its
   pre-round) is told by those alone, as before. */
static int ccup_tier(const ccup_t* c)
{
  int own = 0, pre1 = 0;
  for (int e = 0; e < c->n && e < CCUP_MAX_ENTRY; e++) {
    if (c->erank[e] == 1) return 0;
    uint16_t lg[2], cp[2]; uint8_t rk[2];
    int n = c->erank[e] ? 0 : ccup_behind(c->ereg[e], lg, rk, cp);
    if (!n) { own = 1; continue; }
    for (int i = 0; i < n; i++) pre1 |= rk[i] == 1;
  }
  return !own && pre1 ? 0 : 1;
}
/* the j-th day of a cup's groups or knockout: the knockout's own days when the world file gives them */
static int ccup_like_ok(const ccup_t* c);
/* the two-legged league cup's days before 0.2.0 (leaguebuilder LEAGUE_CUP_DAYS): a single-match
   cup of the world file played the old way by a career with the old row (ccup_size) */
static const uint32_t LCUP_OLD_DAYS[7] = { 256, 287, 291, 314, 326, 340, 356 };
static uint32_t ccup_day(const ccup_t* c, int ko, int j)
{
  if (ko && c->like && !ccup_like_ok(c)) return LCUP_OLD_DAYS[j < 7 ? j : 6];
  if (ko && c->nd) return c->days[j < c->nd ? j : c->nd - 1];
  int cr = ccup_region((ccup_t*)c);
  return ko ? CCUP_KO_DAYS[cr][ccup_tier(c)][j] : CCUP_GROUP_DAYS[cr][ccup_tier(c)][j];
}
static int ccup_world(const ccup_t* c)
{
  if (!c->groups) return get_rec(c->ko) != 0;
  return get_rec(c->reg) && get_rec(c->ko) && get_rec(ccup_rep(c, 0)) && get_rec(ccup_rep(c, c->groups - 1));
}
/* which cup a regulation belongs to (0-based), and whether it is the knockout: -1 = none */
static int ccup_of(uint16_t id, int* ko)
{
  for (int k = 0; k < g_nccup; k++) {
    const ccup_t* c = &g_ccup[k];
    *ko = id == c->ko;
    if (id == c->reg || id == c->ko) return k;
    if (c->groups && id > 1024 && (id & 0x3ff) == c->reg && id <= ccup_rep(c, c->groups - 1)) return k;
  }
  return -1;
}
/* A club already in a continental cup: one of ours, or the game's own Libertadores (group stage
   reg 9, qualifying round reg 8) or AFC Champions League (reg 15), whose fields are set on day 0,
   long before a cup of ours is filled at the end of August. Without the game's three, Boca Juniors
   played the Libertadores and the Copa Sudamericana in the same season (GitHub #37). */
static int ccup_taken(uint32_t c)
{
  static const uint16_t SHIPPED[] = { 9, 8, 15 };
  for (int k = 0; k < g_nccup; k++)
    if (!g_ccup[k].national && has_club(g_ccup_field[k], g_ccup_nf[k], c)) return 1;
  for (unsigned i = 0; i < sizeof SHIPPED / sizeof SHIPPED[0]; i++) {
    unsigned char* rec = get_rec(SHIPPED[i]);
    if (rec && has_club(rec_clubs(rec), rec_count(rec), c)) return 1;
  }
  return 0;
}
/* B204: the clubs of the world's continental cups that play August to May (not a league cup, not
   a February-December one, which is filled in January next to the Libertadores and keeps last
   season's clubs until then): the field as filled, and what their records hold */
static unsigned world_cup_clubs(uint32_t* out, unsigned cap)
{
  unsigned n = 0;
  for (int k = 0; k < g_nccup; k++) {
    const ccup_t* c = &g_ccup[k];
    if (c->national || c->cal) continue;
    for (unsigned i = 0; i < g_ccup_nf[k] && n < cap; i++)
      if (!has_club(out, n, g_ccup_field[k][i])) out[n++] = g_ccup_field[k][i];
    uint16_t regs[2 + CCUP_MAX_GROUPS]; int nr = 0;
    regs[nr++] = c->reg;
    if (c->ko && c->ko != c->reg) regs[nr++] = c->ko;
    for (int g = 0; g < c->groups && g < CCUP_MAX_GROUPS; g++) regs[nr++] = ccup_rep(c, g);
    for (int r = 0; r < nr; r++) {
      unsigned char* rec = get_rec(regs[r]);
      unsigned rc = rec ? rec_count(rec) : 0;
      for (unsigned i = 0; i < rc && n < cap; i++) {
        uint32_t x = rec_clubs(rec)[i];
        if ((x >> 14) && (x >> 14) != 0x3ffff && !has_club(out, n, x)) out[n++] = x;
      }
    }
  }
  return n;
}

__declspec(dllexport) int fl26_swiss_ccup(const uint16_t* v, int n)
{
  /* per cup: reg, ko, groups, entries, then (reg, position) per entry */
  if ((!v && n) || n < 0) return -1;
  g_nccup = 0;
  g_ccup_gen++;
  size_t p = 0;
  for (int i = 0; i < n && g_nccup < MAX_CCUP; i++) {
    ccup_t* c = &g_ccup[g_nccup];
    c->reg = v[p]; c->ko = v[p + 1]; c->groups = v[p + 2]; unsigned ne = v[p + 3]; p += 4;
    c->n = 0; c->fill = c->national = c->nd = c->nc = 0; c->filled_year = -1; c->why_year = -1; c->like = 0; c->cal = 0;
    memset(c->ealt, 0, sizeof c->ealt);
    memset(c->efrom, 0, sizeof c->efrom);
    memset(c->first, 0, sizeof c->first);
    g_ccup_gday0[g_nccup] = 0;
    for (unsigned e = 0; e < ne; e++, p += 2)
      if (c->n < CCUP_MAX_ENTRY) { c->ereg[c->n] = v[p]; c->erank[c->n] = (uint8_t)v[p + 1]; c->n++; }
    if (!c->groups) {
      c->reg = c->ko;
      c->like = clike_of(c->ko);
      if (c->like) {
        if (ne > CCUP_MAX_ENTRY || !like_size_ok(c->n)) {
          logf("fl26swiss: cup %u -- a single-match knockout of %u clubs is not a field the bracket screen draws; left out",
               (unsigned)c->ko, (unsigned)ne);
          continue;
        }
        logf("fl26swiss: cup %u from the world file: a single-match knockout of %u, shaped and dated as reg %u",
             (unsigned)c->ko, (unsigned)c->n, (unsigned)c->like);
        g_nccup++;
        continue;
      }
      if (c->n != 2 && c->n != 4 && c->n != 8 && c->n != 16 && c->n != 32) {
        logf("fl26swiss: cup %u -- a knockout of %u clubs is not 2, 4, 8, 16 or 32; left out", (unsigned)c->ko,
             (unsigned)c->n);
        continue;
      }
      logf("fl26swiss: cup %u from the world file: a knockout of %u", (unsigned)c->ko, (unsigned)c->n);
      g_nccup++;
      continue;
    }
    if (c->groups > CCUP_MAX_GROUPS || c->n != 4u * c->groups) {
      logf("fl26swiss: cup %u -- %u group(s) and %u entries do not make groups of four; left out",
           (unsigned)c->reg, (unsigned)c->groups, (unsigned)c->n);
      continue;
    }
    logf("fl26swiss: cup %u (knockout %u) from the world file: %u groups, %u entries", (unsigned)c->reg,
         (unsigned)c->ko, (unsigned)c->groups, (unsigned)c->n);
    g_nccup++;
  }
  return g_nccup;
}

/* The options per cup, n records of u32: knockout id, fill day, national (0/1), the number of
   days and the days, the number of invited clubs and their team ids. A record names its cup by
   the knockout id of fl26_swiss_ccup's list, so this is called after it. Answers the cups
   matched. */
__declspec(dllexport) int fl26_swiss_ccup_opts(const uint32_t* v, int n)
{
  int got = 0;
  size_t p = 0;
  for (int i = 0; v && i < n; i++) {
    uint32_t ko = v[p], fill = v[p + 1], national = v[p + 2], nd = v[p + 3];
    p += 4;
    const uint32_t* days = v + p; p += nd;
    uint32_t nc = v[p++];
    const uint32_t* clubs = v + p; p += nc;
    ccup_t* c = 0;
    for (int k = 0; k < g_nccup; k++) if (g_ccup[k].ko == ko) c = &g_ccup[k];
    if (!c) { logf("fl26swiss: cup options for %u -- no such cup in the list; left out", (unsigned)ko); continue; }
    c->fill = (uint16_t)(fill <= 365 ? fill : 0); c->national = national ? 1 : 0;
    c->nd = 0;
    for (uint32_t j = 0; j < nd && j < CCUP_MAX_DAYS; j++) if (days[j] >= 1 && days[j] <= 365) c->days[c->nd++] = (uint16_t)days[j];
    c->nc = 0;
    for (uint32_t j = 0; j < nc && j < CCUP_MAX_ENTRY; j++) if (clubs[j] && !(clubs[j] >> 18)) c->clubs[c->nc++] = clubs[j];
    if (c->nc && c->nc != c->n) {
      logf("fl26swiss: cup %u -- %u invited clubs for a field of %u; the invitations are dropped",
           (unsigned)ko, (unsigned)c->nc, (unsigned)c->n);
      c->nc = 0;
    }
    logf("fl26swiss: cup %u options -- fill %s%u, %s, %u day(s), %u invited club(s)", (unsigned)ko,
         c->fill ? "on day " : "with the play-off ", (unsigned)c->fill, c->national ? "national" : "continental",
         (unsigned)c->nd, (unsigned)c->nc);
    got++;
  }
  return got;
}

/* The cup winners' leagues per cup, n records of u16: knockout id, entry index, league (the
   world file's alt=, see the continental cups above), the league's low 10 bits and in the bits
   above them the first position to try -- the one after every place of that league in another
   competition, so the fallback is not a champion the Libertadores or the AFC Champions League
   takes as well (0 = from the top). Called after fl26_swiss_ccup. Answers the records taken. */
__declspec(dllexport) int fl26_swiss_ccup_alt(const uint16_t* v, int n)
{
  int got = 0;
  for (int i = 0; v && i < n; i++) {
    uint16_t ko = v[3 * i], e = v[3 * i + 1], league = v[3 * i + 2];
    ccup_t* c = 0;
    for (int k = 0; k < g_nccup; k++) if (g_ccup[k].ko == ko) c = &g_ccup[k];
    if (!c || e >= c->n || c->erank[e]) {
      logf("fl26swiss: cup %u -- alt for entry %u does not name a cup winner's entry; left out", (unsigned)ko, (unsigned)e);
      continue;
    }
    c->ealt[e] = league & 0x3ff;
    c->efrom[e] = (uint8_t)(league >> 10);
    g_ccup_gen++;
    got++;
  }
  if (got) logf("fl26swiss: %d cup winner place(s) with a league to fall back on", got);
  return got;
}

/* The single-match league cups (0.2.0), n records of u16: knockout id, the shipped domestic cup
   (2..175) whose shape the knockout row was copied from and whose calendar dates it. Called
   BEFORE fl26_swiss_ccup, which then takes such a knockout at any field like_size_ok allows (an
   older fl26swiss.dll has no such export: the module says so, and the cup is left out there as a
   knockout that is not 2, 4, 8, 16 or 32). Answers the records taken. */
__declspec(dllexport) int fl26_swiss_ccup_like(const uint16_t* v, int n)
{
  g_nclike = 0;
  for (int i = 0; v && i < n && g_nclike < MAX_CCUP; i++) {
    uint16_t ko = v[2 * i], like = v[2 * i + 1];
    if (ko < 176 || ko > 1023 || like < 2 || like > 175) {
      logf("fl26swiss: single-match cup record %u like %u -- not a cup of ours and a shipped cup; left out", (unsigned)ko, (unsigned)like);
      continue;
    }
    g_clike[g_nclike][0] = ko; g_clike[g_nclike][1] = like; g_nclike++;
  }
  logf("fl26swiss: %d single-match league cup(s) named by the world file", g_nclike);
  return g_nclike;
}

/* the live knockout row of a single-match cup is the domestic cup shape the world file says: a
   format-2 knockout (+0x308 bits 23-28) with a bracket (+0x30c bits 0-6) of the cup's field. A
   career saved with the old two-legged row under the same id (format 30, bracket 16) is not. */
static int ccup_like_ok(const ccup_t* c)
{
  if (!c->like || c->groups) return 0;
  unsigned char* r = get_rec(c->ko);
  if (!r) return 0;
  uint32_t fmt = (*(uint32_t*)(r + 0x308) >> 23) & 0x3f, br = *(uint32_t*)(r + 0x30c) & 0x7f;
  return fmt == 2 && br == c->n;
}
/* how many of a cup's entries it plays with: all of them, but for a single-match cup whose live
   row is not that shape -- an old career -- the first ones its own bracket holds, a power of two
   (the entries run top division first, so that is the old cup's field, with no pre-round) */
static unsigned ccup_size(const ccup_t* c)
{
  if (!c->like || ccup_like_ok(c)) return c->n;
  unsigned char* r = get_rec(c->ko);
  unsigned br = r ? (*(uint32_t*)(r + 0x30c) & 0x7f) : 0, p = 1;
  while (p * 2 <= br && p * 2 <= c->n) p *= 2;
  static uint16_t said[MAX_CCUP]; static int nsaid = 0; int seen = 0;
  for (int i = 0; i < nsaid; i++) seen |= said[i] == c->ko;
  if (!seen && nsaid < MAX_CCUP) {
    said[nsaid++] = c->ko;
    logf("fl26swiss: cup %u -- the world file makes it a single-match cup of %u, but this career's row is format %u, bracket %u: "
         "the old two-legged knockout of %u is played", (unsigned)c->ko, (unsigned)c->n,
         r ? (unsigned)((*(uint32_t*)(r + 0x308) >> 23) & 0x3f) : 0u, br, p >= 2 ? p : 0u);
  }
  return p >= 2 ? p : 0;
}

/* ---- CONMEBOL cups on the South American calendar ----
 * cal=1 cups borrow the native Libertadores dates, are filled on their own
 * February fill day, survive July, and close with the calendar-year teardown. */
__declspec(dllexport) int fl26_swiss_ccup_cal(const uint16_t* v, int n)
{
  int got = 0;
  for (int i = 0; v && i < n; i++)
    for (int k = 0; k < g_nccup; k++)
      if (g_ccup[k].ko == v[i]) {
        g_ccup[k].cal = 1;
        got++;
        logf("fl26swiss: cup %u -- on the South American calendar%s",
             (unsigned)g_ccup[k].ko, g_ccup[k].fill ? "" : " (no fill day: it will never be filled)");
      }
  return got;
}

/* Optional first-season clubs for winner entries, chiefly the Recopa. Per record:
   knockout id, count, then one team id per entry. They are consulted only when no live or
   retained winner can fill that entry; later seasons therefore always use the real winners. */
__declspec(dllexport) int fl26_swiss_ccup_first(const uint16_t* v, int n)
{
  if ((!v && n) || n < 0) return -1;
  int got = 0;
  size_t p = 0;
  for (int i = 0; i < n; i++) {
    uint16_t ko = v[p], cnt = v[p + 1];
    const uint16_t* ids = v + p + 2;
    p += 2 + (size_t)cnt;
    for (int k = 0; k < g_nccup; k++)
      if (g_ccup[k].ko == ko) {
        memset(g_ccup[k].first, 0, sizeof g_ccup[k].first);
        for (unsigned j = 0; j < cnt && j < CCUP_MAX_ENTRY; j++)
          g_ccup[k].first[j] = ids[j];
        got++;
        logf("fl26swiss: cup %u -- %u first-season fallback club(s)%s",
             (unsigned)ko, (unsigned)cnt, cnt ? " configured" : "");
      }
  }
  return got;
}

/* ---- the league cups' pre-rounds ----
 *
 * A league cup takes the biggest of 16, 8 or 4 clubs its leagues have, and the clubs past it
 * play a pre-round first (GitHub #70: a league of 20 left four of them out). tools/leaguebuilder.py
 * makes the pre-round a copy of reg 2 -- a master and eight tie rows at reg + 1024 * (k + 1),
 * two legs -- and names it in the world file:
 *
 *   lpre <reg> cup=<knockout> fill=<day> days=<d1>,<d2> entry=<reg>:<position>,...
 *
 * Tie k is entries 2k (at home first) and 2k + 1 (the better placed); its winner is the cup's
 * entry <tie id>:0. The game knows nothing of the id, so it is run the way an August qualifying
 * round is (q_fill): from the fill day to the eve of the first leg the clubs are taken from the
 * league tables (cwc_club, as the cup's own are), set on the ties and the master, the master
 * started and handed to register_all; the dates are reg 2's records moved to d1 and d2; the
 * July teardown closes it. A tie whose winner cannot be read (never played) sends the better
 * placed club. The cup, filled after it, leaves out the clubs the pre-round has: the tables can
 * have moved between the two fill days. */
#define MAX_LPRE 16
#define LPRE_TIES 8                       /* normal two-leg play-off replicas */
#define LPRE_MAX 16                       /* modern Sudamericana first-stage ties */
typedef struct { uint16_t reg, ko, fill, ties; uint16_t days[2]; uint16_t ereg[2 * LPRE_MAX];
                 uint8_t erank[2 * LPRE_MAX]; uint16_t ealt[2 * LPRE_MAX]; uint8_t efrom[2 * LPRE_MAX];
                 int filled_year; uint32_t club[2 * LPRE_MAX]; unsigned nclub;
                 uint8_t single, alias, feed8, poko; int ko_year;
                 uint32_t gwin[8]; int gwin_year; } lpre_t;
static lpre_t g_lpre[MAX_LPRE]; static int g_nlpre = 0;

static int modern_conmebol(void)
{
  for (int i = 0; i < g_nlpre; i++)
    if (g_lpre[i].alias) return 1;
  return 0;
}
static volatile uint16_t* g_single_po_slots = 0;   /* post-match page routing for single=1 masters */
static int season_ord(int d);
static uint16_t lpre_tie(const lpre_t* l, int k) { return (uint16_t)(l->reg + 1024 * (k + 1)); }
/* Normal legacy pre-rounds expose eight replicas. Libertadores aliases and the
   Sudamericana one-match first stage expose exactly the rows generated for them. */
static int lpre_rows(const lpre_t* l) { return (l->alias || l->single || l->poko || l->ties > LPRE_TIES) ? l->ties : LPRE_TIES; }
/* which pre-round a regulation belongs to (0-based; *tie -1 for the master), -1 none */
static int lpre_of(uint16_t id, int* tie)
{
  for (int i = 0; i < g_nlpre; i++) {
    if (id == g_lpre[i].reg) { *tie = -1; return i; }
    if (id > 1024 && (id & 0x3ff) == g_lpre[i].reg && (id >> 10) <= lpre_rows(&g_lpre[i])) { *tie = (id >> 10) - 1; return i; }
  }
  return -1;
}
static int ccup_behind(uint16_t ereg, uint16_t lg[2], uint8_t rank[2], uint16_t cup[2])
{
  int tk, li = lpre_of(ereg, &tk), n = 0;
  if (li < 0 || tk < 0 || tk >= g_lpre[li].ties) return 0;
  const lpre_t* l = &g_lpre[li];
  for (int e = 2 * tk; e < 2 * tk + 2 && e < 2 * LPRE_MAX; e++) {
    if (!l->ereg[e]) continue;
    rank[n] = l->erank[e];
    lg[n] = l->erank[e] ? l->ereg[e] : l->ealt[e];
    cup[n] = l->erank[e] ? 0 : l->ereg[e];
    n++;
  }
  return n;
}
static int lpre_world(const lpre_t* l)
{
  if (!get_rec(l->reg)) return 0;
  for (int k = 0; k < lpre_rows(l); k++)
    if (!get_rec(lpre_tie(l, k))) return 0;
  return 1;
}
static int lpre_year(void) { return (abs_day() + 183) / 365; }          /* the season, as ccup_fill_days */
/* match records under the master and its ties; -1 when the match table cannot be read */
static int lpre_matches(const lpre_t* l)
{
  int m = ccup_matches(l->reg);
  if (m < 0) return -1;
  for (int k = 0; k < lpre_rows(l); k++) { int x = ccup_matches(lpre_tie(l, k)); if (x > 0) m += x; }
  return m;
}

static void po_fill(void);          /* the Match Results play-off ids, below */
__declspec(dllexport) int fl26_swiss_lpre(const uint16_t* v, int n)
{
  /* per pre-round: reg, the cup's knockout, fill day, the two legs' days, entries, then
     (reg, position) per entry. Called after fl26_swiss_ccup: the cup must be in its list. */
  if ((!v && n) || n < 0) return -1;
  g_nlpre = 0;
  size_t p = 0;
  for (int i = 0; i < n; i++) {
    uint16_t reg = v[p], ko = v[p + 1], fill = v[p + 2], d1 = v[p + 3], d2 = v[p + 4];
    unsigned ne = v[p + 5];
    const uint16_t* e = v + p + 6;
    p += 6 + 2 * (size_t)ne;
    int k = -1;
    for (int j = 0; j < g_nccup; j++) if (ko && g_ccup[j].ko == ko) k = j;
    /* cup=0 is a standalone Libertadores qualifying phase. A group-stage cup may
       also have a first-stage pre-round (modern Sudamericana). */
    if (g_nlpre >= MAX_LPRE || (ko && k < 0) || ne < 2 || ne > 2 * LPRE_MAX || ne % 2 || reg <= 2 || reg > 1023
        || !fill || fill > 365 || !d1 || d1 > 365 || !d2 || d2 > 365) {
      logf("fl26swiss: pre-round %u of cup %u (%u entries) -- not one this module can run; left out",
           (unsigned)reg, (unsigned)ko, ne);
      continue;
    }
    lpre_t* l = &g_lpre[g_nlpre++];
    memset(l, 0, sizeof *l);
    l->reg = reg; l->ko = ko; l->fill = fill; l->days[0] = d1; l->days[1] = d2;
    l->ties = (uint16_t)(ne / 2); l->filled_year = -1; l->ko_year = -1; l->gwin_year = -1;
    for (unsigned j = 0; j < ne; j++) { l->ereg[j] = e[2 * j]; l->erank[j] = (uint8_t)e[2 * j + 1]; }
    int fed = 0;
    for (unsigned j = 0; k >= 0 && j < g_ccup[k].n; j++) {
      int t;
      if (!g_ccup[k].erank[j] && lpre_of(g_ccup[k].ereg[j], &t) == g_nlpre - 1 && t >= 0 && t < l->ties) fed++;
    }
    logf("fl26swiss: pre-round %u from the world file: %u tie(s) for cup %u (%d of its places), filled from day %u, "
         "played on days %u and %u", (unsigned)reg, (unsigned)l->ties, (unsigned)ko, fed, (unsigned)fill,
         (unsigned)d1, (unsigned)d2);
  }
  po_fill();                        /* the Match Results title: the pre-rounds are play-offs */
  return g_nlpre;
}

/* Optional same-source fallback for an lpre cup-winner entry. Each record is
   (master, 1-based entry index, fallback source, first fallback rank). */
__declspec(dllexport) int fl26_swiss_lpre_alt(const uint16_t* v, int n)
{
  int got = 0;
  for (int i = 0; v && i < n; i++) {
    uint16_t master = v[4 * i], slot = v[4 * i + 1], alt = v[4 * i + 2], from = v[4 * i + 3];
    if (!slot || !alt || !from) continue;
    for (int j = 0; j < g_nlpre; j++) {
      lpre_t* l = &g_lpre[j];
      if (l->reg != master || slot > 2u * l->ties) continue;
      unsigned at = slot - 1;
      l->ealt[at] = alt;
      l->efrom[at] = (uint8_t)(from > FINAL_MAX ? FINAL_MAX : from);
      got++;
      logf("fl26swiss: pre-round %u entry %u -- cup-winner fallback source %u from position %u",
           (unsigned)master, (unsigned)slot, (unsigned)alt, (unsigned)l->efrom[at]);
      break;
    }
  }
  return got;
}

/* Mark selected pre-round masters as one-match ties. The database shape itself is
   generated with one_match=True; this flag tells the runtime to expose all 16 rows
   and records the intended single-match semantics for the modern Sudamericana. */
__declspec(dllexport) int fl26_swiss_lpre_single(const uint16_t* v, int n)
{
  int got = 0;
  for (int i = 0; v && i < n; i++)
    for (int j = 0; j < g_nlpre; j++)
      if (g_lpre[j].reg == v[i]) {
        g_lpre[j].single = 1;
        if (g_single_po_slots)
          for (int q = 0; q < MAX_LPRE; q++)
            if (g_single_po_slots[q] == 0xfffe || g_single_po_slots[q] == v[i]) {
              g_single_po_slots[q] = v[i];
              break;
            }
        got++;
        logf("fl26swiss: pre-round %u -- one match a tie, on day %u",
             (unsigned)v[i], (unsigned)g_lpre[j].days[0]);
      }
  return got;
}

/* the clubs pre-round l has this season: the ones it was filled with in this session, else the
   ones its ties hold once this season's matches are there (a save loaded after the fill) */
static unsigned lpre_clubs(const lpre_t* l, uint32_t* out)
{
  /* Match records are authoritative. The session copy may belong to a different
     save loaded later in the same process. */
  if (lpre_matches(l) <= 0) return 0;
  unsigned n = 0;
  for (int k = 0; k < l->ties; k++) {
    unsigned char* t = get_rec(lpre_tie(l, k));
    if (!t || rec_count(t) != 2) return 0;
    out[n++] = rec_clubs(t)[0]; out[n++] = rec_clubs(t)[1];
  }
  return n;
}
/* a club that plays the pre-round in front of cup ko this season */
static int lpre_has(uint16_t ko, uint32_t c)
{
  for (int i = 0; i < g_nlpre; i++) {
    if (g_lpre[i].ko != ko) continue;
    uint32_t cl[2 * LPRE_MAX];
    unsigned n = lpre_clubs(&g_lpre[i], cl);
    if (has_club(cl, n, c)) return 1;
  }
  return 0;
}

/* The modern Sudamericana built by this branch is the non-national 8-group cup
 * whose entry list contains four `8:255` Libertadores-F3 losers. */
static int modern_suda_ccup(void)
{
  for (int k = 0; k < g_nccup; k++) {
    const ccup_t* c = &g_ccup[k];
    if (c->national || c->groups != 8) continue;
    for (unsigned i = 0; i < c->n; i++)
      if (c->ereg[i] == 8 && c->erank[i] == 255) return k;
  }
  return -1;
}
static int lpre_is_suda(const lpre_t* l)
{
  int k = modern_suda_ccup();
  return k >= 0 && l && l->single && l->ko == g_ccup[k].ko;
}
static const ccup_t* lpre_cup(const lpre_t* l)
{
  if (!l) return 0;
  for (int k = 0; k < g_nccup; k++)
    if (g_ccup[k].ko == l->ko) return &g_ccup[k];
  return 0;
}
static int lpre_cal(const lpre_t* l)
{
  const ccup_t* c = lpre_cup(l);
  return c && c->cal;
}

static uint32_t kept_conmebol_holder(uint16_t reg)
{
  cupwin_t* w = cupwin_of(reg);
  int ad = abs_day();
  if (!w || ad < w->day || ad - w->day > 330 || !(w->club >> 14)) return 0;
  return canon_club(w->club);
}

/* The two protected direct continental places in Libertadores groups.
 * Normally they are the previous Libertadores and Sudamericana champions. If this
 * world has no modern Sudamericana at all, the second place belongs to the previous
 * Libertadores runner-up instead. */
static unsigned lib9_titleholders(uint32_t holder[2])
{
  holder[0] = holder[1] = 0;

  /* Titleholder injection/reallocation belongs only to the custom modern
     CONMEBOL package. */
  if (!modern_conmebol()) return 0;
  unsigned char* o = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
  void* blk = o ? *(void**)(o + 0x48) : 0;
  if (!blk) return 0;

  int sk = modern_suda_ccup();
  uint32_t candidate[2] = {
    kept_conmebol_holder(10),
    sk >= 0 ? kept_conmebol_holder(g_ccup[sk].ko)
            : kept_conmebol_holder(CUPWIN_LIB_RUNNER)
  };
  unsigned n = 0;
  for (int h = 0; h < 2; h++) {
    uint32_t club = candidate[h];
    if (!club) continue;
    if (g_confed_n && confed_of(team_country(blk, club)) != 4) continue;
    if (h && holder[0] && same_club(club, holder[0])) continue;
    holder[h] = club;
    n++;
  }
  return n;
}

/* A club reserved for one of the custom Libertadores qualifying phases, either
 * already present in this save or named by a dynamic source/rank that has not
 * been filled yet. Only alias phases (F1/F2) count here: Sudamericana pre-rounds
 * deliberately do not block a Libertadores fallback. */
static int lib_path_has_except(uint32_t c, int skip)
{
  c = canon_club(c);
  for (int i = 0; i < g_nlpre; i++) {
    const lpre_t* l = &g_lpre[i];
    if (i == skip || !l->alias) continue;

    uint32_t cl[2 * LPRE_MAX];
    unsigned n = lpre_clubs(l, cl);
    if (has_club(cl, n, c)) return 1;
    /* drawn already: its clubs are the ones in it. The ranks are read again only before the draw --
       read later, a league that had started named another club, and a Sudamericana first-stage
       winner was refused as "in the Libertadores": the groups never started, "only 29 of 32 clubs
       found" (nissindiaz, #147) */
    if (n) continue;

    for (unsigned j = 0; j < 2u * l->ties; j++) {
      if (!l->erank[j]) continue;
      const char* how = "";
      uint32_t v = cwc_club(l->ereg[j], l->erank[j], &how);
      if ((v >> 14) && same_club(c, canon_club(v))) return 1;
    }
  }
  return 0;
}
static int lib_path_has(uint32_t c) { return lib_path_has_except(c, -1); }

static int lib_reserved_except(uint32_t c, int skip_lpre)
{
  c = canon_club(c);
  uint32_t holder[2] = { 0, 0 };
  lib9_titleholders(holder);
  if (has_club(g_cont[0], g_ncont[0], c) || has_club(g_cont[1], g_ncont[1], c)) return 1;
  if ((holder[0] && same_club(c, holder[0])) || (holder[1] && same_club(c, holder[1]))) return 1;
  return lib_path_has_except(c, skip_lpre);
}
static int lib_reserved(uint32_t c) { return lib_reserved_except(c, -1); }

/* A club the game has already drawn into this season's Libertadores groups (reg 9). The day-0
   filler there (lib9_clean) is on none of our paths, so only the groups know it; a Sudamericana
   or qualifying source passes it by (B231: Albion FC played both group stages). An empty place
   (no team id) is never a match. */
static int lib9_has(uint32_t c)
{
  unsigned char* g = get_rec(R_LIBGROUP);
  unsigned m = g ? rec_count(g) : 0;
  c = canon_club(c);
  if (!(c >> 14)) return 0;
  for (unsigned i = 0; i < m && i < 64; i++) {
    uint32_t a = rec_clubs(g)[i];
    if ((a >> 14) && same_club(canon_club(a), c)) return 1;
  }
  return 0;
}
static int lib_taken(uint32_t c) { return lib_reserved(c) || lib9_has(c); }

/* Last-resort replacement for a native Libertadores entry. Stay inside
 * CONMEBOL, prefer the Latin-American pool, and never consume a club already
 * reserved by the Libertadores group stage or qualifying path. Sudamericana
 * places are intentionally not protected: Libertadores has priority and Suda
 * will cascade inside the displaced club's own source. */
static uint32_t conmebol_fallback(void* blk, const uint32_t* taken, unsigned nt)
{
  uint32_t na = 0;
  unsigned char* a = team_array(&na);
  if (!blk || !a || !g_confed_n) return 0;
  /* B347 (pczim123, 07.11.): never the user's club -- it never gives its place away to one of ours,
     so as a stand-in it stayed in the groups and every Brazilian club he picked started there */
  uint32_t uc = user_club(blk);
  uc = uc ? canon_club(uc) : 0;

  for (int pass = 0; pass < 2; pass++) {
    for (uint32_t i = 0; i < na; i++) {
      uint32_t c = team_at(a, i);
      if (c == 0xffffffffu || !(c >> 14) || (c >> 14) == 0x3ffff || (c & 0x3fff) != i) continue;
      c = canon_club(c);
      if (uc && same_club(c, uc)) continue;
      if (has_club(taken, nt, c)) continue;
      if (confed_of(team_country(blk, c)) != 4) continue;
      if (lib_reserved(c)) continue;

      int in_pool = club_slot(blk, c) == POOL_LATAM;
      if (pass == 0 && !in_pool) continue;
      if (pass == 1 && in_pool) continue;
      return c;
    }
  }
  return 0;
}

/* Native reg 9 is created before F1/F2 are played. The game's Latin-American
 * filler may therefore contain one of the clubs reserved for those phases.
 * Before native F3 begins, replace only that provisional filler; from day 34
 * onward a qualifying club may be in groups legitimately as an F3 winner. */
static void lib9_clean(u32vec* list)
{
  if (!list || !list->b || list->e <= list->b) return;
  size_t n = (size_t)(list->e - list->b);

  for (size_t i = 0; i < n; i++)
    for (size_t j = i + 1; j < n; j++)
      if (same_club(list->b[i], list->b[j]))
        logf("fl26swiss: Libertadores group stage -- day %d: %08x is in the list twice (places %u and %u)",
             today(), list->b[i], (unsigned)i + 1, (unsigned)j + 1);

  int any = 0;
  for (int i = 0; i < g_nlpre && !any; i++) any = g_lpre[i].alias;
  if (!any || today() >= 34) return;

  unsigned char* o = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
  void* blk = o ? *(void**)(o + 0x48) : 0;
  if (!blk) return;
  cont_build();

  for (size_t i = 0; i < n; i++) {
    uint32_t c = canon_club(list->b[i]);
    if (!lib_path_has(c)) continue;
    uint32_t sub = conmebol_fallback(blk, list->b, (unsigned)n);
    if (sub) list->b[i] = sub;
    logf("fl26swiss: Libertadores group stage -- day %d: %08x is reserved for F1/F2; %s %08x",
         today(), c, sub ? "replaced by spare CONMEBOL filler" : "NO safe CONMEBOL filler to replace it,", sub);
  }
}

/* Insert retained titleholders into the native Libertadores group field without
 * consuming any of the configured 26 domestic places or the qualifying path. */
static void lib9_holders(u32vec* list)
{
  if (!list || !list->b || list->e <= list->b) return;
  size_t n = (size_t)(list->e - list->b);
  unsigned char* o = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
  void* blk = o ? *(void**)(o + 0x48) : 0;
  if (!blk) return;

  uint32_t holder[2] = { 0, 0 };
  lib9_titleholders(holder);
  int sk = modern_suda_ccup();
  const char* name[2] = {
    "Libertadores holder",
    sk >= 0 ? "Sudamericana holder" : "Libertadores runner-up"
  };
  unsigned char* r8 = get_rec(8);

  for (int h = 0; h < 2; h++) {
    uint32_t club = holder[h];
    if (!club) continue;
    if (has_club(list->b, n, club)) {
      logf("fl26swiss: Libertadores group stage -- retained %s %08x already present and protected",
           name[h], club);
      continue;
    }

    int place = -1;
    for (int pass = 0; pass < 2 && place < 0; pass++) {
      for (size_t i = 0; i < n; i++) {
        uint32_t old = list->b[i];
        if (!(old >> 14)) continue;
        if ((holder[0] && same_club(old, holder[0])) ||
            (holder[1] && same_club(old, holder[1]))) continue;
        if (has_club(g_cont[0], g_ncont[0], old)) continue;
        if (lib_path_has(old)) continue;
        if (r8 && has_club(rec_clubs(r8), rec_count(r8), old)) continue;
        if (!pass && club_slot(blk, old) != POOL_LATAM) continue;
        place = (int)i;
        break;
      }
    }

    if (place < 0) {
      logf("fl26swiss: Libertadores group stage -- retained %s %08x has NO protected spare direct place",
           name[h], club);
      continue;
    }
    uint32_t old = list->b[place];
    list->b[place] = club;
    logf("fl26swiss: Libertadores group stage -- retained %s %08x takes reserved direct place %u from %08x",
         name[h], club, (unsigned)place + 1, old);
  }
}
/* who goes on from pre-round tie id: the winner the game reads, else (not played, or no
   winner read) the better placed club, the tie's second; 0 when id is not a tie of ours */
static uint32_t lpre_winner(uint16_t id, const char** how)
{
  int k, i = lpre_of(id, &k);
  if (i < 0 || k < 0 || k >= g_lpre[i].ties) return 0;
  const lpre_t* l = &g_lpre[i];
  unsigned char* t = get_rec(id);
  if (lpre_matches(l) > 0 && t && rec_count(t) == 2) {
    uint32_t a = rec_clubs(t)[0], b = rec_clubs(t)[1], w = 0;
    ((winner_fn)(uintptr_t)(g_base + WINNER_RVA))(&w, id);
    if ((w >> 14) && (same_club(w, a) || same_club(w, b))) { *how = "pre-round winner"; return canon_club(same_club(w, a) ? a : b); }
    *how = "pre-round, no winner read: the better placed";
    return canon_club(b);
  }
  if (l->nclub == 2u * l->ties) { *how = "pre-round not played: the better placed"; return l->club[2 * k + 1]; }
  *how = "pre-round never filled: the better placed";
  for (int rank = l->erank[2 * k + 1]; rank >= 1 && rank <= FINAL_MAX; rank++) {
    const char* h2 = "";
    uint32_t c = cwc_club(l->ereg[2 * k + 1], rank, &h2);
    if (!c) break;
    if (c >> 14) return canon_club(c);
  }
  return 0;
}

/* A pre-round whose every tie has an actual winner in the match state. */
static int lpre_decided(const lpre_t* l, uint32_t* win)
{
  if (!l || lpre_matches(l) <= 0) return 0;
  for (int k = 0; k < l->ties; k++) {
    const char* how = "";
    win[k] = lpre_winner(lpre_tie(l, k), &how);
    if (!win[k] || strcmp(how, "pre-round winner")) return 0;
  }
  return 1;
}

/* ---- modern Libertadores F1/F2 -> native F3 (regulation 8) ---- */

#define CONM_LIB_CID        5
#define CONM_LIBQ_REG       8
#define CONM_OWNER_RVA      0x3705e10
#define CONM_MATCH_BASE     0x13146e8
#define CONM_MATCH_CAP      0x131471b
#define CONM_MATCH_STRIDE   0x254
#define CONM_RNDREC_RVA     0x1579bd0

/* The match records of one regulation: how many, and how many not played yet
   (-1: the match table is not where it was looked for). */
static int libq_records(uint16_t reg, int* unplayed)
{
  const unsigned char* bs = (const unsigned char*)(uintptr_t)(g_base + CONM_MATCH_BASE);
  const unsigned char* cs = (const unsigned char*)(uintptr_t)(g_base + CONM_MATCH_CAP);

  if (bs[0] != 0x48 || bs[1] != 0x8d || bs[2] != 0x88 ||
      cs[0] != 0x81 || cs[1] != 0xff)
    return -1;

  uint32_t base = *(const uint32_t*)(bs + 3);
  uint32_t cap  = *(const uint32_t*)(cs + 2);

  void** owner = *(void***)(uintptr_t)(g_base + CONM_OWNER_RVA);
  unsigned char* blk = owner ? (unsigned char*)owner[0x48 / 8] : 0;

  if (!blk || !cap || cap > 200000) return -1;

  int n = 0;
  *unplayed = 0;
  for (uint32_t i = 0; i < cap; i++) {
    unsigned char* m = blk + base + (size_t)i * CONM_MATCH_STRIDE;
    if (*(uint16_t*)m == 0xffff || *(uint16_t*)(m + 4) != reg) continue;
    n++;
    if (!(m[7] & 0x40)) (*unplayed)++;
  }
  return n;
}

/* All ties must have actually produced a winner. We deliberately do not use the
   "better placed" fallback for the F2 -> F3 hand-over.
   B240 (antonimus 25.10.): nor the game's winner of a tie whose second leg is
   still to come -- before it is played that is whoever leads after the first
   leg. F2's legs fell on day 25 and the hand-over ran on day 26 before that
   day's matches: a tie leader went into F3, then the real winner on a later
   pass, and the groups were drawn from a mix of the two. Every match record of
   every F2 tie must be played first. */
static int libq_decided(const lpre_t* l, uint32_t* win)
{
  if (lpre_matches(l) <= 0) return 0;
  for (int k = 0; k < l->ties; k++) {
    int unplayed = 0, n = libq_records(lpre_tie(l, k), &unplayed);
    if (n <= 0 || unplayed) return 0;
  }
  for (int k = 0; k < l->ties; k++) {
    const char* how = "";
    win[k] = lpre_winner(lpre_tie(l, k), &how);
    if (!win[k] || strcmp(how, "pre-round winner")) return 0;
  }
  return 1;
}

/* The clubs each native F3 tie was last given, this session: a hand-over run
   again (the game puts the tie lists back to their day-0 clubs) finds the match
   records holding these, not the day-0 pair, and must still reach them. */
static uint32_t g_lib8_last[4][2];

/* B246 (antonimus 26.10., Deportes La Serena v Deportes La Serena in phase 3,
   Lanus gone): which leg of an F3 tie a match record is, so it gets the whole
   new pair in that order -- the first leg (na at home) or the return (nb at
   home). Side by side it went wrong when the new pair shares a club with the old
   one: tie 3080 held 01374082 v 027c0130, its F2 winners were 027c0130 v
   01e240a5; the home side became 027c0130, the away side already was 027c0130
   and was left, so La Serena met itself. The leg is read from the old pair
   (a, b), then from what this session gave the tie last (pa, pb, 0: none),
   then from the new pair itself (a record given one side only: a save made
   after the B240 swap); a pair that says both, or neither, does not decide.
   Returns 1 (the first leg), 2 (the return), 0 if the record already holds the
   new pair (also 1/2 in *leg), -1 if no pair decides. c[] is rewritten for 1
   and 2. */
static int libq_leg_pair(uint32_t* c, uint32_t a, uint32_t b, uint32_t pa, uint32_t pb,
                         uint32_t na, uint32_t nb, int* leg)
{
  uint32_t h = c[0], w = c[1];
  *leg = 0;
  if (same_club(h, na) && same_club(w, nb)) { *leg = 1; return 0; }
  if (same_club(h, nb) && same_club(w, na)) { *leg = 2; return 0; }
  const uint32_t x[3] = { a, pa, na }, y[3] = { b, pb, nb };
  for (int s = 0; s < 3; s++) {
    if (!x[s] || !y[s]) continue;
    int fwd = same_club(h, x[s]) || same_club(w, y[s]);
    int rev = same_club(h, y[s]) || same_club(w, x[s]);
    if (fwd == rev) continue;
    c[0] = fwd ? na : nb;
    c[1] = fwd ? nb : na;
    return *leg = fwd ? 1 : 2;
  }
  return -1;
}

/* Change clubs in unplayed match records belonging to one native F3 tie.
   Played records are never rewritten. a/b are the tie's clubs now, pa/pb the
   ones this session gave it last (0: none). Each record gets the new pair as
   its leg (libq_leg_pair). A record no pair decides -- a club twice, left by
   the hand-over before B246 -- takes the leg the tie's other records have not
   taken, when that is one. */
static int libq_match_swap(uint16_t reg, uint32_t a, uint32_t b,
                           uint32_t pa, uint32_t pb,
                           uint32_t na, uint32_t nb, int* played)
{
  const unsigned char* bs = (const unsigned char*)(uintptr_t)(g_base + CONM_MATCH_BASE);
  const unsigned char* cs = (const unsigned char*)(uintptr_t)(g_base + CONM_MATCH_CAP);

  if (bs[0] != 0x48 || bs[1] != 0x8d || bs[2] != 0x88 ||
      cs[0] != 0x81 || cs[1] != 0xff)
    return -1;

  uint32_t base = *(const uint32_t*)(bs + 3);
  uint32_t cap  = *(const uint32_t*)(cs + 2);

  void** owner = *(void***)(uintptr_t)(g_base + CONM_OWNER_RVA);
  unsigned char* blk = owner ? (unsigned char*)owner[0x48 / 8] : 0;

  if (!blk || !cap || cap > 200000) return -1;

  int n = 0, taken = 0, nopen = 0;
  uint32_t* open[8];
  for (uint32_t i = 0; i < cap; i++) {
    unsigned char* m = blk + base + (size_t)i * CONM_MATCH_STRIDE;
    if (*(uint16_t*)m == 0xffff || *(uint16_t*)(m + 4) != reg) continue;

    uint32_t* c = (uint32_t*)(m + 0x14);
    int leg;
    if (m[7] & 0x40) {
      uint32_t look[2] = { c[0], c[1] };
      libq_leg_pair(look, a, b, pa, pb, na, nb, &leg);
      taken |= leg;
      (*played)++;
      continue;
    }

    uint32_t was0 = c[0], was1 = c[1];
    int got = libq_leg_pair(c, a, b, pa, pb, na, nb, &leg);
    if (got < 0) {
      if (nopen < 8) open[nopen++] = c;
      continue;
    }
    if (got > 0)
      logf("fl26swiss: Libertadores phase 3 -- tie %u: %s leg %08x v %08x -> %08x v %08x",
           (unsigned)reg, leg == 1 ? "first" : "return", was0, was1, c[0], c[1]);
    taken |= leg;
    n++;
  }
  for (int k = 0; k < nopen; k++) {
    uint32_t* c = open[k];
    int both = (same_club(c[0], na) || same_club(c[0], nb)) &&
               (same_club(c[1], na) || same_club(c[1], nb));
    int leg = taken == 1 ? 2 : taken == 2 ? 1 : 0;
    if (!both || !leg || nopen > 1) {
      logf("fl26swiss: Libertadores phase 3 -- tie %u: a match holds %08x v %08x, "
           "no leg of %08x v %08x; left alone", (unsigned)reg, c[0], c[1], na, nb);
      continue;
    }
    logf("fl26swiss: Libertadores phase 3 -- tie %u: a match held %08x v %08x, given the %s leg",
         (unsigned)reg, c[0], c[1], leg == 1 ? "first" : "return");
    c[0] = leg == 1 ? na : nb;
    c[1] = leg == 1 ? nb : na;
    n++;
  }
  return n;
}

typedef unsigned char* (*libq_rndrec_fn)(uint16_t* id, uint32_t* round);

static unsigned char* libq_round_rec(uint16_t tid, uint32_t round)
{
  uint16_t id = tid;
  uint32_t rd = round;
  unsigned char* r =
      ((libq_rndrec_fn)(uintptr_t)(g_base + CONM_RNDREC_RVA))(&id, &rd);

  if (!r || (*(uint32_t*)(r + 0x204) >> 26) != round) return 0;
  return r;
}

/* The final/only round record of a two-club F3 tie also stores its pair. */
static int libq_round_swap(uint16_t tid, uint32_t a, uint32_t b,
                           uint32_t na, uint32_t nb, uint32_t* was)
{
  unsigned char* r = libq_round_rec(tid, 0x35);
  if (!r) return -1;

  uint32_t* pair = (uint32_t*)(r + 4);
  was[0] = pair[0];
  was[1] = pair[1];

  int n = 0;
  for (int i = 0; i < 2; i++) {
    if (same_club(pair[i], a) && !same_club(a, na)) {
      pair[i] = na;
      n++;
    } else if (same_club(pair[i], b) && !same_club(b, nb)) {
      pair[i] = nb;
      n++;
    }
  }
  return n;
}

/* F2 has eight ties -> eight winners. Native F3 has four ties. After
   F2's second leg and before F3's first leg, replace the provisional
   day-0 native F3 field with those eight winners. */
static void lib8_swap(int i)
{
  lpre_t* l = &g_lpre[i];
  int d = today();

  if (!l->feed8 || l->ties != 8) return;
  if (d <= l->days[1]) {
    /* another career, or this one loaded from before the hand-over */
    memset(g_lib8_last, 0, sizeof g_lib8_last);
    return;
  }
  if (d >= 34) return;

  uint32_t win[LPRE_TIES];
  if (!libq_decided(l, win)) return;

  /* Already swapped in this loaded save/session? */
  int already = 1;
  for (int k = 0; k < 4 && already; k++) {
    unsigned char* t =
        get_rec((uint16_t)(CONM_LIBQ_REG + 1024 * (k + 1)));

    already =
        t && rec_count(t) == 2 &&
        same_club(rec_clubs(t)[0], win[2 * k]) &&
        same_club(rec_clubs(t)[1], win[2 * k + 1]);
  }
  if (already) return;

  int done = 0, played = 0, changed = 0;
  uint32_t all[LPRE_TIES];
  uint32_t old8[LPRE_TIES];
  uint32_t prev8[LPRE_TIES];

  for (int k = 0; k < 4; k++) {
    uint16_t tid =
        (uint16_t)(CONM_LIBQ_REG + 1024 * (k + 1));

    unsigned char* t = get_rec(tid);
    if (!t || rec_count(t) != 2) {
      logf("fl26swiss: Libertadores phase 3 -- tie %u holds %u club(s), not 2; left alone",
           (unsigned)tid, t ? rec_count(t) : 0);
      continue;
    }

    uint32_t a = rec_clubs(t)[0];
    uint32_t b = rec_clubs(t)[1];
    uint32_t na = win[2 * k];
    uint32_t nb = win[2 * k + 1];

    int r = libq_match_swap(tid, a, b, g_lib8_last[k][0], g_lib8_last[k][1],
                            na, nb, &played);
    if (r < 0) {
      logf("fl26swiss: Libertadores phase 3 -- match table signature changed; F3 not swapped");
      return;
    }

    uint32_t was[2] = { 0, 0 };
    int rr = libq_round_swap(tid, a, b, na, nb, was);

    logf("fl26swiss: Libertadores phase 3 -- tie %u round record %s: %08x v %08x",
         (unsigned)tid, rr < 0 ? "not found" : "updated",
         was[0], was[1]);

    uint32_t pair[2] = { na, nb };
    u32vec v = { pair, pair + 2, pair + 2 };
    ((setclr_fn)(uintptr_t)g_tramp_setcl)(tid, &v, 1);

    /* The native phase was already created on day 0. If set_clubs leaves
       its live list unchanged, repair that list too. */
    t = get_rec(tid);
    if (t && rec_count(t) == 2 &&
        !(same_club(rec_clubs(t)[0], na) &&
          same_club(rec_clubs(t)[1], nb))) {
      rec_clubs(t)[0] = na;
      rec_clubs(t)[1] = nb;
    }

    all[2 * k] = na;
    all[2 * k + 1] = nb;
    old8[2 * k] = a;
    old8[2 * k + 1] = b;
    prev8[2 * k] = g_lib8_last[k][0];
    prev8[2 * k + 1] = g_lib8_last[k][1];
    g_lib8_last[k][0] = na;
    g_lib8_last[k][1] = nb;

    changed += r;
    done++;

    logf("fl26swiss: Libertadores phase 3 -- tie %u: %08x v %08x -> %08x v %08x",
         (unsigned)tid, a, b, na, nb);
  }

  if (done == 4) {
    u32vec v = { all, all + 8, all + 8 };
    ((setclr_fn)(uintptr_t)g_tramp_setcl)(CONM_LIBQ_REG, &v, 1);

    /* Same protection for the native reg-8 master list: every F3 club in it
       (the ties' clubs before, or what this session gave them last) that is
       not one of the eight gets one of the eight it lacks. Not by
       old -> new pairs: the day-0 field and the F2 winners can share a club
       (antonimus 25.10.: 01e240a5 day-0 in tie 4104, an F2 winner for tie
       3080), and a pair would then put one winner in twice and drop that
       one. */
    unsigned char* master = get_rec(CONM_LIBQ_REG);
    unsigned count = master ? rec_count(master) : 0;

    for (unsigned i2 = 0; i2 < count && i2 < 64; i2++) {
      uint32_t* c = &rec_clubs(master)[i2];
      int j = 0;
      while (j < 8 && !same_club(*c, all[j])) j++;
      if (j < 8) continue;
      for (j = 0; j < 8; j++)
        if (same_club(*c, old8[j]) || (prev8[j] && same_club(*c, prev8[j]))) break;
      if (j >= 8) continue;
      for (j = 0; j < 8; j++) {
        unsigned i3 = 0;
        while (i3 < count && i3 < 64 && !same_club(rec_clubs(master)[i3], all[j])) i3++;
        if (i3 >= count || i3 >= 64) {
          *c = all[j];
          break;
        }
      }
    }
  }

  run_flush();

  logf("fl26swiss: Libertadores phase 3 -- day %d: %d/4 ties given F2 winners, %d match record(s) changed%s",
       d, done, changed,
       played ? " -- WARNING: some F3 matches were already played" : "");
}

/* `(master, flags)` pairs from the Lua loader.
   bit 0 = Libertadores qualifying phase (po=1)
   bit 1 = its winners feed native reg 8 (feed=8)
   bit 2 = modern Sudamericana post-group play-off (poko=1) */
__declspec(dllexport) int fl26_swiss_lpre_flags(const uint16_t* v, int n)
{
  int got = 0;

  for (int i = 0; v && i < n; i++) {
    uint16_t reg = v[2 * i];
    uint16_t flags = v[2 * i + 1];

    for (int j = 0; j < g_nlpre; j++) {
      if (g_lpre[j].reg != reg) continue;

      g_lpre[j].alias = (flags & 1) != 0;
      g_lpre[j].feed8 = (flags & 2) != 0;
      g_lpre[j].poko = (flags & 4) != 0;

      if (g_lpre[j].poko && g_single_po_slots)
        for (int q = 0; q < MAX_LPRE; q++)
          if (g_single_po_slots[q] == 0xfffe || g_single_po_slots[q] == reg) {
            g_single_po_slots[q] = reg;
            break;
          }

      logf("fl26swiss: pre-round %u -- %s%s",
           (unsigned)reg,
           g_lpre[j].alias
             ? "a Libertadores qualifying phase"
             : g_lpre[j].poko
               ? "the Sudamericana play-off (runners-up v Libertadores thirds)"
               : "a pre-round",
           g_lpre[j].feed8
             ? ", its winners feed native reg 8 (phase 3)"
             : g_lpre[j].poko
               ? ", its winners feed the Sudamericana round of 16"
               : "");

      got++;
    }
  }

  /* lpre_rows() now knows which masters use only their real replica count. */
  po_fill();
  return got;
}

/* Presentation alias for the internally separate Libertadores F1/F2 competition.
   0 = not one of ours, 1 = F1, 2 = F2. */
static int libq_alias_stage(uint16_t id)
{
  int tie = -1;
  int i = lpre_of(id, &tie);
  if (i < 0 || !g_lpre[i].alias) return 0;
  return g_lpre[i].feed8 ? 2 : 1;
}

#define POKO_PHFIN 0x1546c70     /* 0x141546c70(id): phase finished */
typedef char (*pokofin_fn)(uint64_t id);

/* B185: the Sudamericana group tables are empty by the time the play-off's second leg is
   played (day 153 of the CONMEBOL test season, 21.10.: "group A has a table of 0 rows" on every
   day after it, no round of 16, no winner). The eight group winners are kept with the play-off's
   own fill, while the tables still hold them; poko_ko takes them from here first. */
static void poko_keep_winners(lpre_t* l)
{
  const ccup_t* c = lpre_cup(l);
  l->gwin_year = -1;
  if (!c || c->groups != 8) return;
  for (int j = 0; j < 8; j++) {
    const char* how = "";
    uint32_t w = cwc_club(ccup_rep(c, j), 1, &how);
    if (w >> 14) w = canon_club(w);
    if (!(w >> 14)) {
      logf("fl26swiss: cup %u -- group %c winner not readable at the play-off fill; not kept",
           (unsigned)c->reg, 'A' + j);
      return;
    }
    l->gwin[j] = w;
  }
  l->gwin_year = lpre_year();
  logf("fl26swiss: cup %u -- the 8 group winners kept for the round of 16 (A %08x ... H %08x)",
       (unsigned)c->reg, l->gwin[0], l->gwin[7]);
}

/* on the days from its fill day to the eve of its first leg, once a season: the clubs, the ties,
   the master started and registered -- q_fill's steps */
/* A cup winner sent to a continental cup's preliminary round (11.11.2026, the African and CONCACAF
   cups' rounds): a club that stands on a place of its league that leads to a continental cup or to
   a preliminary round keeps that place -- the champion that won the cup too plays the Champions
   League -- and the entry goes down its league (alt). The pre-round is filled days before the cups
   are, so ccup_taken cannot tell yet. `league`: the entry's alt, the winner's own league. */
static int lpre_claimed(uint16_t league, uint32_t club)
{
  const char* how = "";
  for (int k = 0; k < g_nccup; k++) {
    const ccup_t* c = &g_ccup[k];
    if (c->national) continue;
    for (unsigned j = 0; j < c->n; j++)
      if (c->ereg[j] == league && c->erank[j] && c->erank[j] < 255) {
        uint32_t x = cwc_club(league, c->erank[j], &how);
        if ((x >> 14) && canon_club(x) == club) return 1;
      }
  }
  for (int k = 0; k < g_nlpre; k++)
    for (unsigned j = 0; j < 2u * g_lpre[k].ties; j++)
      if (g_lpre[k].ereg[j] == league && g_lpre[k].erank[j] && g_lpre[k].erank[j] < 255) {
        uint32_t x = cwc_club(league, g_lpre[k].erank[j], &how);
        if ((x >> 14) && canon_club(x) == club) return 1;
      }
  return 0;
}

static void lpre_fill(int i)
{
  lpre_t* l = &g_lpre[i];
  int d = today();
  if (d < 1) return;
  if (l->poko) {
    const ccup_t* c = lpre_cup(l);
    pokofin_fn fin = (pokofin_fn)(uintptr_t)(g_base + POKO_PHFIN);
    if (!c || !fin(c->reg) || !fin(R_LIBGROUP)) return;
  }
  int s = season_ord(d), f = season_ord(l->fill), last = season_ord(l->days[0]) - 1, year = lpre_year();
  if (last < f) last = f + 7;
  if (s < f || s > last) return;
  int was = l->filled_year == year;
  if (!lpre_world(l)) {
    if (!was) logf("fl26swiss: pre-round %u -- its rows are not all in this world; left alone", (unsigned)l->reg);
    l->filled_year = year;
    return;
  }
  int m = lpre_matches(l);
  if (m != 0) {
    if (m > 0 && !was) logf("fl26swiss: pre-round %u already has %d match record(s) this season; not filled again", (unsigned)l->reg, m);
    l->filled_year = year;
    return;
  }
  if (was) logf("fl26swiss: pre-round %u -- filled earlier this session but has no match now (a save loaded); filled again", (unsigned)l->reg);
  l->filled_year = year;
  l->nclub = 0;
  int lib_stage = l->alias;
  int suda_first = lpre_is_suda(l);
  if (lib_stage || suda_first) cont_build();
  unsigned n = 0;
  for (unsigned j = 0; j < 2u * l->ties; j++) {
    const char* how = ""; uint32_t club = 0;
    if (!l->erank[j]) {
      int tk = -1;
      if (lpre_of(l->ereg[j], &tk) >= 0) {
        /* winner of a tie belonging to an earlier pre-round (F1 -> F2) */
        club = lpre_winner(l->ereg[j], &how);
        if (club && has_club(l->club, n, club)) club = 0;
      } else {
        /* A national cup winner sent directly to this qualifying/first-stage slot.
           CONMEBOL stages are in the next calendar year, so the retained winner may
           be older than the normal 120-day continental-access window. */
        club = cal_cup_winner(l->ereg[j]);
        how = "cup winner";
        if (club) club = canon_club(club);
        if (club && (has_club(l->club, n, club) ||
                     ((lib_stage || suda_first) && (lib_reserved_except(club, i) || (!l->poko && lib9_has(club))))))
          club = 0;
        if (club && !lib_stage && !suda_first && l->ealt[j] && lpre_claimed(l->ealt[j], club)) {
          logf("fl26swiss: pre-round %u -- cup winner %08x of reg %u stands on a continental place of reg %u; "
               "its place goes down the league", (unsigned)l->reg, club, (unsigned)l->ereg[j], (unsigned)l->ealt[j]);
          club = 0;
        }
        if (!club && l->ealt[j]) {
          for (int rank = l->efrom[j] ? l->efrom[j] : 1; rank <= FINAL_MAX; rank++) {
            club = cwc_club(l->ealt[j], rank, &how);
            if (!club) break;
            if (club >> 14) club = canon_club(club);
            if (!(club >> 14) || has_club(l->club, n, club)) { club = 0; continue; }
            if ((lib_stage || suda_first) && (lib_reserved_except(club, i) || (!l->poko && lib9_has(club)))) { club = 0; continue; }
            logf("fl26swiss: pre-round %u -- cup winner from reg %u unavailable; same-source fallback %u position %d -> %08x",
                 (unsigned)l->reg, (unsigned)l->ereg[j], (unsigned)l->ealt[j], rank, club);
            break;
          }
        }
      }
    } else {
      for (int rank = l->erank[j]; rank >= 1 && rank <= FINAL_MAX; rank++) {
        club = cwc_club(l->ereg[j], rank, &how);
        if (!club) break;
        if (club >> 14) club = canon_club(club);
        if (!(club >> 14) || has_club(l->club, n, club)) { club = 0; continue; }
        if ((lib_stage || suda_first) && (lib_reserved_except(club, i) || (!l->poko && lib9_has(club)))) {
          logf("fl26swiss: pre-round %u -- source %u position %d -> %08x skipped; already reserved for Libertadores",
               (unsigned)l->reg, (unsigned)l->ereg[j], rank, club);
          club = 0;
          continue;
        }
        if (rank != l->erank[j])
          logf("fl26swiss: pre-round %u -- source %u requested position %u cascades to position %d (%08x)",
               (unsigned)l->reg, (unsigned)l->ereg[j], (unsigned)l->erank[j], rank, club);
        break;
      }
    }
    if (!club) {
      logf("fl26swiss: pre-round %u -- reg %u position %u has no club to send; not filled", (unsigned)l->reg,
           (unsigned)l->ereg[j], (unsigned)l->erank[j]);
      return;
    }
    l->club[n++] = club;
    logf("fl26swiss:   pre-round %u entry %2u: reg %u position %u -> %08x (%s)", (unsigned)l->reg, n,
         (unsigned)l->ereg[j], (unsigned)l->erank[j], club, how);
  }
  for (int k = 0; k < lpre_rows(l); k++)
    ((freetab_fn)(uintptr_t)(g_base + FREETAB_RVA))(0, lpre_tie(l, k));
  canon_list(l->club, n, "pre-round reg", l->reg);   /* B312 */
  u32vec va = { l->club, l->club + n, l->club + n };
  ((setclr_fn)(uintptr_t)g_tramp_setcl)(l->reg, &va, 1);
  for (int k = 0; k < l->ties; k++) {
    u32vec v = { l->club + 2 * k, l->club + 2 * k + 2, l->club + 2 * k + 2 };
    ((setclr_fn)(uintptr_t)g_tramp_setcl)(lpre_tie(l, k), &v, 1);
  }
  run_flush();
  l->nclub = n;
  if (l->poko) poko_keep_winners(l);
  start_stage(0, l->reg);
  uint16_t id = l->reg;
  struct { uint16_t* b; uint16_t* e; uint16_t* c; } rv = { &id, &id + 1, &id + 1 };
  ((regall_fn)(uintptr_t)(g_base + REGALL_RVA))(0, &rv);
  run_flush();
  int mm = ccup_matches(l->reg), mt = 0;
  for (int k = 0; k < l->ties; k++) { int x = ccup_matches(lpre_tie(l, k)); if (x > 0) mt += x; }
  if (mm <= 0 && mt <= 0) {                         /* the ties are their own rows: register them too */
    uint16_t ties[LPRE_MAX];
    for (int k = 0; k < l->ties; k++) ties[k] = lpre_tie(l, k);
    struct { uint16_t* b; uint16_t* e; uint16_t* c; } tv = { ties, ties + l->ties, ties + l->ties };
    ((regall_fn)(uintptr_t)(g_base + REGALL_RVA))(0, &tv);
    run_flush();
    mm = ccup_matches(l->reg); mt = 0;
    for (int k = 0; k < l->ties; k++) { int x = ccup_matches(lpre_tie(l, k)); if (x > 0) mt += x; }
  }
  unsigned char* t0 = get_rec(lpre_tie(l, 0));
  logf("fl26swiss: pre-round %u -- day %d: %u tie(s) filled (tie 0 holds %u), started and registered; "
       "%d match record(s) under it, %d under its ties", (unsigned)l->reg, d, (unsigned)l->ties,
       t0 ? rec_count(t0) : 0, mm, mt);
}
/* Modern Sudamericana post-group play-off -> round of 16. Once all eight
   two-leg ties have winners, combine them with the eight Suda group winners.
   The +4 rotation prevents a Suda runner-up from immediately meeting the winner
   of the same group when that runner-up survives the play-off. */
static void poko_ko(int i, void* started)
{
  lpre_t* l = &g_lpre[i];
  int d = today(), year = lpre_year();
  if (!l->poko || d < l->days[1] || d >= 182) return;
  const ccup_t* c = lpre_cup(l);
  int k = c ? (int)(c - g_ccup) : -1;
  unsigned char* ko = c ? get_rec(c->ko) : 0;
  if (!c || !ko || c->groups != 8 || l->ties != 8) return;
  if (rec_count(ko)) { l->ko_year = year; return; }

  uint32_t win[LPRE_MAX];
  if (!lpre_decided(l, win)) return;

  static uint32_t buf[16];
  for (int j = 0; j < 8; j++) {
    /* the winners kept at the play-off fill (B185), else the live table, else the table
       counted from the group's played matches (a save loaded after the fill) */
    uint32_t w = l->gwin_year == year ? l->gwin[j] : 0;
    if (!(w >> 14)) {
      unsigned char* tab = ((table_fn)(uintptr_t)(g_base + TABLE_RVA))(ccup_rep(c, j));
      uint32_t rows = tab ? *(uint32_t*)(tab + 0x3c0) : 0;
      if (rows >= 2 && rows <= 8) w = *(uint32_t*)tab;
      else {
        static final_t ft;
        uint16_t rep = ccup_rep(c, j);
        int played = 0, n = count_table(&rep, 1, &ft, &played);
        if (n >= 4 && played >= n) {
          w = ft.club[0];
          logf("fl26swiss: cup %u -- group %c table empty; winner %08x counted from %d played match(es)",
               (unsigned)c->reg, 'A' + j, w, played);
        } else {
          logf("fl26swiss: cup %u -- group %c has a table of %u rows and %d played match(es); round of 16 not filled",
               (unsigned)c->reg, 'A' + j, (unsigned)rows, played);
          return;
        }
      }
    }
    buf[2 * j] = w;
    buf[2 * j + 1] = win[(j + 4) % 8];
  }

  l->ko_year = year;
  u32vec v = { buf, buf + 16, buf + 16 };
  ((setcl_fn)(uintptr_t)(g_base + SETCL_RVA))(c->ko, &v, 1);
  run_flush();
  if (rec_count(ko) != 16) {
    logf("fl26swiss: cup %u -- round-of-16 reg %u took %u of 16 clubs; not started",
         (unsigned)c->reg, (unsigned)c->ko, rec_count(ko));
    return;
  }

  start_stage(started, c->ko);
  if (!started) {
    uint16_t id = c->ko;
    struct { uint16_t* b; uint16_t* e; uint16_t* c; } rv = { &id, &id + 1, &id + 1 };
    ((regall_fn)(uintptr_t)(g_base + REGALL_RVA))(0, &rv);
    run_flush();
  }
  if (k >= 0) g_ccup_done[k] = 0;
  logf("fl26swiss: cup %u -- day %d: round of 16 from 8 group winners + 8 play-off winners "
       "(A1 %08x v %08x ...), %d match record(s)",
       (unsigned)c->reg, d, buf[0], buf[1], ccup_matches(c->ko));
}

static void lpre_fill_days(void)
{
  for (int i = 0; i < g_nlpre; i++) {
    lpre_fill(i);
    lib8_swap(i);
    poko_ko(i, 0);
  }
}

/* A Copa Sudamericana entry `8:255`: take a club that played native Libertadores
   qualifying (reg 8/master or one of its four ties) but did not reach reg 9.
   Four such entries therefore become the four F3 losers in the Sudamericana groups. */
#define QUAL_LOSER 255
static uint32_t qual_loser(uint16_t q, const uint32_t* taken, unsigned nt, const char** how)
{
  unsigned char* g = get_rec(R_LIBGROUP);
  if (!g || !rec_count(g)) { *how = "Libertadores groups not filled yet"; return 0; }
  for (int t = 0; t <= 8; t++) {
    unsigned char* r = get_rec((uint16_t)(t ? q + 1024 * t : q));
    unsigned m = r ? rec_count(r) : 0;
    for (unsigned i = 0; i < m && i < 64; i++) {
      uint32_t c = canon_club(rec_clubs(r)[i]);
      if (!(c >> 14) || has_club(rec_clubs(g), rec_count(g), c) || has_club(taken, nt, c)) continue;
      *how = "eliminated in the Libertadores qualifying";
      return c;
    }
  }
  *how = "no Libertadores qualifying loser left";
  return 0;
}

/* B243: 1 when `club` is a Libertadores qualifying loser, as one of cup c's `8:255` entries takes
   it (qual_loser's test). CONMEBOL lets such a club share a Sudamericana group with a club of its
   own association (vmican, 26.10.). */
static int from_qual(const ccup_t* c, unsigned cn, uint32_t club)
{
  unsigned char* g = get_rec(R_LIBGROUP);
  club = canon_club(club);
  if (g && has_club(rec_clubs(g), rec_count(g), club)) return 0;
  for (unsigned j = 0; j < cn; j++) {
    if (c->erank[j] != QUAL_LOSER) continue;
    for (int t = 0; t <= 8; t++) {
      unsigned char* r = get_rec((uint16_t)(t ? c->ereg[j] + 1024 * t : c->ereg[j]));
      unsigned m = r ? rec_count(r) : 0;
      for (unsigned i = 0; i < m && i < 64; i++)
        if (canon_club(rec_clubs(r)[i]) == club) return 1;
    }
  }
  return 0;
}

/* ---- a split season of the game's own, under a play-off of the world (B425, 11.11.2026) ----
 *
 * The game ships its own split seasons: the Scottish Premiership (total 133, regular phase 134,
 * the top six 135, the bottom six 136) and, in FL 2027, the Danish Superliga (141, 147, 148, 175).
 * A relegation play-off of a world (the Scottish Championship's, cup 724 of the GigaPack) names the
 * top division's place on the regular phase: `entry=134:11`. That was read off the regular
 * phase's table: the game asks for 134's progression the day the 33rd round is played (day 98),
 * the cup took the league for over and was filled as soon as the Championship was (day 129, the
 * groups still playing) with the 11th of 33 rounds. In the second season of the Build 5 test that
 * club finished 10th: it won the play-off, fl26chain found neither club where a play-off's clubs
 * stand after the move ("not in 413 or not in 134 after the move -- untouched"), the Championship's
 * runner-up went up having lost and the real 11th went down without a match.
 * So the regular phase's progression does not end such a league for a cup that waits for it: the
 * groups' last round does. Their tables are kept then (the game's own, its tie-breaks are the ones
 * the total's final standings carry; counted from the matches when the game has none) and place N
 * of the regular phase is the final table's: the top group's N-th, or the bottom group's.
 * fl26chain reads the same place from the total's standings (fl26chain.lua). The world file names
 * the seasons (`gsplit`, fl26_swiss_gsplits); a world built before the line has the Scottish one.
 * A world that makes those ids a split of its own (a `split` line) is not touched. */
#define MAX_GSPLIT 4
typedef struct { uint16_t total, regular, group[2]; } gsplit_t;
static gsplit_t g_gsplit[MAX_GSPLIT] = { { 133, 134, { 135, 136 } } };
static int g_ngsplit = 1;
/* n of {total, regular phase, top group, bottom group} */
__declspec(dllexport) int fl26_swiss_gsplits(const uint16_t* v, int n)
{
  if ((!v && n) || n < 0) return -1;
  if (n > MAX_GSPLIT) n = MAX_GSPLIT;
  for (int i = 0; i < n; i++) {
    g_gsplit[i].total = v[4 * i]; g_gsplit[i].regular = v[4 * i + 1];
    g_gsplit[i].group[0] = v[4 * i + 2]; g_gsplit[i].group[1] = v[4 * i + 3];
  }
  g_ngsplit = n;
  logf("fl26swiss: %d split season(s) of the game's own under a league of the world", n);
  return n;
}
static int keep_group_final(uint16_t reg, int ad);
static const gsplit_t* gsplit_live(const gsplit_t* g)
{
  const split_t* s;
  if (split_part(g->total, &s) || split_part(g->regular, &s) || split_part(g->group[0], &s) || split_part(g->group[1], &s)) return 0;
  return get_rec(g->regular) && get_rec(g->group[0]) && get_rec(g->group[1]) ? g : 0;
}
static const gsplit_t* gsplit_regular(uint16_t reg)
{
  for (int i = 0; i < g_ngsplit; i++) if (reg && g_gsplit[i].regular == reg) return gsplit_live(&g_gsplit[i]);
  return 0;
}
static const gsplit_t* gsplit_group(uint16_t reg)
{
  for (int i = 0; i < g_ngsplit; i++)
    if (reg && (g_gsplit[i].group[0] == reg || g_gsplit[i].group[1] == reg)) return gsplit_live(&g_gsplit[i]);
  return 0;
}
/* both groups' final tables, kept once their last round is played (days 100..200: the groups play
   in April and May, and a record of last season's must not pass for this one's): 1 when they stand */
static int gsplit_keep(const gsplit_t* g)
{
  int d = today(), ad = abs_day();
  for (int k = 0; k < 2; k++) {
    uint16_t r = g->group[k];
    final_t* f = final_of(r);
    if (f && f->n && ad >= f->day && ad - f->day < 60) continue;
    if (d < 100 || d > 200 || !season_played(r)) return 0;
    unsigned char* rec = get_rec(r);
    unsigned char* t = rec ? ((table_fn)(uintptr_t)(g_base + TABLE_RVA))(r) : 0;
    uint32_t rows = t ? *(uint32_t*)(t + 0x3c0) : 0;
    if (rows >= 2 && rows <= FINAL_MAX && rows == rec_count(rec) && !unplayed(rec, t, rows)) {
      if (!f) { if (!(f = final_new(r))) return 0; f->reg = r; }
      f->n = (uint16_t)rows; f->day = ad;
      for (uint32_t i = 0; i < rows; i++) f->club[i] = *(uint32_t*)(t + i * 20);
      logf("fl26swiss: reg %u -- the game's split group over on day %d, its table kept (%u clubs): %08x first, %08x last",
           (unsigned)r, d, (unsigned)rows, f->club[0], f->club[rows - 1]);
    } else if (keep_group_final(r, ad) <= 0) {
      static int said = -1;
      if (said != ad) {
        said = ad;
        logf("fl26swiss: reg %u -- the game's split group is played out on day %d, but it has no table (%u row(s)) and none from its matches",
             (unsigned)r, d, (unsigned)rows);
      }
      return 0;
    }
  }
  return 1;
}
static uint32_t gsplit_club(const gsplit_t* g, int rank, const char** how)
{
  if (rank < 1 || !gsplit_keep(g)) return 0;
  final_t* a = final_of(g->group[0]); final_t* b = final_of(g->group[1]);
  if (!a || !b) return 0;
  *how = "the split groups' final tables";
  if (rank <= a->n) return a->club[rank - 1];
  return rank - a->n <= b->n ? b->club[rank - a->n - 1] : 0;
}

/* A league position for a cup of ours. A league that also sends clubs to the Libertadores or the
   AFC Champions League is counted the way those places are (last season's kept table, else
   squad strength): the cup went by the live table instead, a few rounds into a first season, and
   the Libertadores by squad strength -- one club of Peru got both cups, the 5th neither
   (GitHub #132). A club of this season's Libertadores / AFC lists is passed over too. */
static int cont_league(uint16_t reg)
{
  for (size_t i = 0; i < g_naccess; i++)
    if (g_access[i].comp >= LIB && g_access[i].comp <= AFCL && (g_access[i].reg == reg || g_access[i].alt == reg)) return 1;
  return 0;
}
static uint32_t ccup_club(const ccup_t* c, uint16_t reg, int rank, const char** how)
{
  if (c->national) {                     /* B425: a place of the game's own split season is its final table's */
    const gsplit_t* g = gsplit_regular(reg);
    uint32_t x = g ? gsplit_club(g, rank, how) : 0;
    if (x) return x;
  }
  if (c->national || !cont_league(reg)) return cwc_club(reg, rank, how);
  int ft = 0;
  uint32_t x = access_club_kept(reg, rank, &ft, CONT_KEEP);
  *how = ft ? "kept table" : seed_of(reg) ? "squad strength" : "list order";
  for (int k = 0; x && k < 3; k++) if (has_club(g_cont[k], g_ncont[k], x)) *how = "in the Libertadores / AFC list";
  return x;
}
static int ccup_cont(const char* how) { return !strcmp(how, "in the Libertadores / AFC list"); }

/* ---- a cup's groups that enter the new season without a table (B172) ----
 *
 * Handed to register_all, a group row goes through the door and enter_season 0x14158f420,
 * which gives the season its tables: it reads the row's season year (+0x2fc; anything but
 * 0xffff is refused at once), works out the year from the first match date and looks for a
 * sub-record of that year in the competition's header entry -- a new one is built
 * (0x14158f9b0 -> 0x14158fd90, a table for every row of the competition and the year written
 * to each +0x2fc), one already there is rebuilt only for ids 0x67 and 0x3a. In a world's first
 * season that works. In the second (r12, 2026-10-20, all five cups of the Modpack) the groups
 * were drawn and registered, kept +0x2fc 0xffff, and no header slot held a table of theirs but
 * last season's: on day 47 "group A has a table of 0 rows" and the knockout was never filled.
 * So when a group is still at 0xffff after register_all, its competition's sub-record of this
 * season is built the way fl26join builds one for a league of ours (reg_post): a slot of this
 * year is cleared (0x14158f870), then 0x14158f9b0 with flag 0. Nothing happens to a cup whose
 * groups did enter. */
#define CS_KEYOF_RVA    0x15451a0   /* (u32* out, u16 id): the header key of a competition     */
#define CS_SUBRESET_RVA 0x158f870   /* (u8* subrecord): clear its tables                        */
#define CS_SUBFILL_RVA  0x158f9b0   /* (u8* entry, u16 year, u8 flag): build the year's tables  */
typedef void (*cs_keyof_fn)(uint32_t* out, uint64_t id);
typedef void (*cs_subreset_fn)(unsigned char* sub);
typedef void (*cs_subfill_fn)(unsigned char* entry, uint64_t year, uint64_t flag);
/* ---- the table pool (B172, fourth season) ----
 *
 * Every table of every season lives in one pool of 600 ([owner+0x78] + the table base, 0x187c
 * each; free = id and year 0xffff, 0x14158f350 takes the first free one). A season's slot holds
 * at most 20 table indices, but 0x14158fd90 gives a table to every row of the competition: the
 * Champions League, Europa League and Conference League have 30 rows each, so every season 30
 * tables were taken that no slot holds -- unreachable (a table is only ever found through a
 * slot: 0x14158ded0 -> 0x14158df30) and never freed. r12, fourth season (2026-10-21): 0 of 600
 * free, 55 of them such tables of 2025 and 2026, and no cup group got a table on day 255: all
 * five cups "entered no season" again. So a table of an earlier season that no slot holds is
 * freed the way 0x14158f870 frees a slot's tables: before a cup's groups are registered and at
 * every July teardown. A table of this season is left alone. */
typedef void (*cs_tabclr_fn)(unsigned char* t);
static const uint32_t CS_TABCLR_RVA[5] = { 0x14ff000, 0x14ff070, 0x14ff010, 0x14fefa0, 0x14ff090 };
static int table_pool_reap(const char* when)
{
  static uint8_t held[POOL_MAX];
  int year = season_year();
  uint32_t tabbase; unsigned nhdr, npool;
  if (!pool_layout(&tabbase, &nhdr, &npool)) return -1;
  unsigned char* o = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
  unsigned char* std = o ? *(unsigned char**)(o + 0x78) : 0;
  if (!std || year < 1990) return -1;
  /* the count the code bounds the pool with: 595 behind fl26hdr255's headers, 2400 with the
     standings step */
  int ntab = (int)npool;
  memset(held, 0, sizeof held);
  for (uint32_t h = 0; h < nhdr; h++)
    for (int k = 0; k < 2; k++) {
      const unsigned char* sl = std + (size_t)h * 0xb4 + 4 + k * 0x58;
      for (int i = 0; i < 20; i++) {
        int32_t ix = *(const int32_t*)(sl + 8 + 4 * i);
        if (ix == -1) break;
        if (ix >= 0 && ix < ntab) held[ix] = 1;
      }
    }
  int nfree = 0, freed = 0, lo = 0xffff, hi = 0;
  for (int i = 0; i < ntab; i++) {
    unsigned char* t = std + tabbase + (size_t)i * 0x187c;
    uint16_t id = *(uint16_t*)t, yr = *(uint16_t*)(t + 2);
    if (id == 0xffff && yr == 0xffff) { nfree++; continue; }
    if (held[i] || yr < 1990 || yr >= year) continue;
    *(uint32_t*)t = 0xffffffff;
    for (int f = 0; f < 5; f++) ((cs_tabclr_fn)(uintptr_t)(g_base + CS_TABCLR_RVA[f]))(t);
    *(uint64_t*)(t + 0x1874) = 0xffffffffffffffffull;
    freed++; nfree++;
    if (yr < lo) lo = yr;
    if (yr > hi) hi = yr;
  }
  if (freed)
    logf("fl26swiss: table pool (%s) -- %d table(s) of seasons %d..%d held by no season freed; %d of %d free",
         when, freed, lo, hi, nfree, ntab);
  return nfree;
}
/* B211 (r13, third season, 23.10.): a world of 86 leagues fills the pool with its two seasons a
 * slot each -- 223 tables of 2027/28 and 303 of 2028/29, 10 free -- and on 1 January the
 * calendar-year competitions start again: 41 of them (the MLS, Brazil, Argentina, Japan, the
 * Libertadores, the AFC Champions League ...) got a 2029 slot with no table at all, so the two cups
 * drew their groups on day 41 with no table, played no group match, and their knockouts got 0
 * clubs on days 125 and 139. A European league keeps last season's slot until the July rollover
 * frees it (0x14158f870); with fewer than POOL_LOW tables free, a slot two calendar years old
 * (2027/28 in 2029) is freed by that same function, from 17 December on, before the game makes the
 * new year's tables -- only when the competition's other slot holds a later season. The season under way is never touched, and a world with tables to spare is
 * left as the game has it. */
#define POOL_LOW 120
#define SECOND_HALF 181     /* 1 July: the July rollover's day */
#define SLOTFREE_RVA 0x158f870
typedef void (*slotfree_fn)(unsigned char* slot);
static void table_pool_old_slots(const char* when)
{
  static const unsigned char SIG[8] = { 0x48, 0x89, 0x74, 0x24, 0x20, 0x41, 0x54, 0x41 };
  unsigned char* f = (unsigned char*)(uintptr_t)(g_base + SLOTFREE_RVA);
  uint32_t tabbase; unsigned nhdr, npool;
  if (!pool_layout(&tabbase, &nhdr, &npool)) return;
  /* the function frees through its own lea r14+imm: it must name the same table base */
  if (memcmp(f, SIG, sizeof SIG) || *(const uint32_t*)(f + 0x73) != tabbase) return;
  unsigned char* o = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
  unsigned char* std = o ? *(unsigned char**)(o + 0x78) : 0;
  unsigned char* blk = o ? *(unsigned char**)(o + 0x48) : 0;
  if (!std || !blk) return;
  int t = *(uint16_t*)(blk + TODAY_OFF), y = *(uint16_t*)(blk + TODAY_OFF + 8);
  if (y < 1990 || y > 2200 || t >= 365) return;
  /* B212 (r13, third season, 23.10.): the last season finished is two years back only until the
   * July rollover; from then on -- the European season of last year ended in May, the calendar
   * year's competitions play this year's -- it is last year's.  With y - 2 all year, the pool ran
   * dry on day 216 of 2031 (the new European seasons) and stayed at 0 until 17 December: the
   * Champions League's league phase was drawn on no table, and its page took the game down. */
  int last = t >= SECOND_HALF ? y - 1 : y - 2;
  int ntab = (int)npool, nfree = 0;
  for (int i = 0; i < ntab; i++)
    if (*(uint32_t*)(std + tabbase + (size_t)i * 0x187c) == 0xffffffffu) nfree++;
  /* B212, second look (d362 -> 2031 day 264): the season is built at the July rollover with last
   * season's slots still there -- 146 tables free after the reap, and the Champions League's slot
   * of 2031 got 3 tables (2, 3, 4) where the Europa League's got 20: the pool ran dry half-way.
   * Freed the next morning, the 2030 slots gave 278 tables back, but nothing builds a slot again,
   * and the league phase (1027) never had a table.  So a slot the game built short -- fewer
   * tables than the same competition's slot of the season before -- is built again here, right
   * after the old one is freed, while its season cannot have begun yet: from the July rollover to
   * day BUILD_DAY, and in the first days of January for the calendar year. */
  int early = (t >= SECOND_HALF && t < BUILD_DAY) || t < 20;
  enum { SHORT_MAX = 64 };
  unsigned char* shorts[SHORT_MAX]; int nshort = 0, want = 0;
  /* the older of two slots (the competition's other slot holds a later season) of a season
   * finished: what may go.  A competition with one slot (a cup of a few years) keeps it. */
  int slots = 0, freed = 0, lo = 0xffff, hi = 0;
  for (int pass = 0; pass < 2; pass++) {
    if (pass == 1) {
      /* the new seasons coming need about as many tables as the finished ones hold: with fewer
         free than that (or under POOL_LOW), they go; a world with tables to spare is left as is */
      if (!nshort && nfree >= POOL_LOW && nfree >= freed) return;
      freed = 0;
    }
    for (uint32_t h = 0; h < nhdr; h++)
      for (int k = 0; k < 2; k++) {
        unsigned char* sl = std + (size_t)h * 0xb4 + 4 + k * 0x58;
        unsigned char* other = std + (size_t)h * 0xb4 + 4 + (1 - k) * 0x58;
        int w = *(uint16_t*)(sl + 4), w2 = *(uint16_t*)(other + 4);
        if (*(uint32_t*)sl == 0xffffffffu || w == 0xffff || w < 1990 || w > last) continue;
        if (*(uint32_t*)other == 0xffffffffu || w2 == 0xffff || w2 <= w) continue;
        int n = 0, n2 = 0;
        for (int i = 0; i < 20 && *(int32_t*)(sl + 8 + 4 * i) != -1; i++)
          if (*(int32_t*)(sl + 8 + 4 * i) >= 0 && *(int32_t*)(sl + 8 + 4 * i) < ntab) n++;
        for (int i = 0; i < 20 && *(int32_t*)(other + 8 + 4 * i) != -1; i++)
          if (*(int32_t*)(other + 8 + 4 * i) >= 0 && *(int32_t*)(other + 8 + 4 * i) < ntab) n2++;
        freed += n;
        if (pass == 0) {
          if (early && w2 >= y && n2 < n && nshort < SHORT_MAX) {
            shorts[nshort++] = std + (size_t)h * 0xb4;
            want += n - n2;
          }
          continue;
        }
        ((slotfree_fn)(uintptr_t)(g_base + SLOTFREE_RVA))(sl);
        slots++;
        if (w < lo) lo = w;
        if (w > hi) hi = w;
      }
  }
  if (slots)
    logf("fl26swiss: table pool (%s, %d) -- %d of %d free: %d slot(s) of seasons %d..%d freed, %d table(s); %d free now",
         when, y, nfree, ntab, slots, lo, hi, freed, nfree + freed);
  if (!nshort) return;
  int rebuilt = 0, before = 0, after = 0;
  for (int s = 0; s < nshort; s++) {
    unsigned char* e = shorts[s];
    for (int k = 0; k < 2; k++) {
      unsigned char* sl = e + 4 + k * 0x58;
      uint32_t key = *(uint32_t*)sl;
      int w = *(uint16_t*)(sl + 4), had = 0, now = 0;
      if (key == 0xffffffffu || w == 0xffff || w < y) continue;
      for (int i = 0; i < 20 && *(int32_t*)(sl + 8 + 4 * i) != -1; i++) had++;
      ((slotfree_fn)(uintptr_t)(g_base + SLOTFREE_RVA))(sl);
      ((cs_subfill_fn)(uintptr_t)(g_base + CS_SUBFILL_RVA))(e, (uint64_t)w, 0);
      for (int k2 = 0; k2 < 2; k2++) {
        unsigned char* s2 = e + 4 + k2 * 0x58;
        if (*(uint32_t*)s2 == 0xffffffffu || *(uint16_t*)(s2 + 4) != w) continue;
        for (int i = 0; i < 20 && *(int32_t*)(s2 + 8 + 4 * i) != -1; i++) now++;
      }
      logf("fl26swiss: table pool -- competition %08x: season %d built short at the rollover (%d table(s)), built again: %d",
           key, w, had, now);
      rebuilt++; before += had; after += now;
      break;
    }
  }
  logf("fl26swiss: table pool (%s, %d) -- %d slot(s) built short (%d table(s) missing) built again: %d table(s) before, %d now",
       when, y, rebuilt, want, before, after);
}
static void ccup_season_fix(uint16_t master, const uint16_t* reps, int n)
{
  int out = 0;
  for (int g = 0; g < n; g++) {
    unsigned char* rg = get_rec(reps[g]);
    if (rg && *(uint16_t*)(rg + 0x2fc) == 0xffff) out++;
  }
  if (!out) return;
  int year = season_year();
  uint32_t tabbase = 0; unsigned nhdr = 0, npool = 0;
  int laid = pool_layout(&tabbase, &nhdr, &npool);
  unsigned char* o = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
  unsigned char* std = o ? *(unsigned char**)(o + 0x78) : 0;
  uint32_t key = 0xffffffff;
  if (year) ((cs_keyof_fn)(uintptr_t)(g_base + CS_KEYOF_RVA))(&key, master);
  unsigned char* e = 0;
  if (std && key != 0xffffffff && laid)
    for (uint32_t k = 0; k < nhdr && !e; k++)
      if (*(const uint32_t*)(std + (size_t)k * 0xb4) == key) e = std + (size_t)k * 0xb4;
  if (!e) {
    logf("fl26swiss: cup %u -- %d of %d group(s) entered no season, and its header entry was not found (year %d, key %08x)",
         (unsigned)master, out, n, year, key);
    return;
  }
  int cleared = 0;
  for (int h = 0; h < 2; h++) {
    unsigned char* s = e + 4 + h * 0x58;
    if (*(const uint32_t*)s != 0xffffffff && *(const uint16_t*)(s + 4) == year) {
      ((cs_subreset_fn)(uintptr_t)(g_base + CS_SUBRESET_RVA))(s);
      cleared = 1;
    }
  }
  ((cs_subfill_fn)(uintptr_t)(g_base + CS_SUBFILL_RVA))(e, (uint64_t)year, 0);
  int in = 0;
  for (int g = 0; g < n; g++) {
    unsigned char* rg = get_rec(reps[g]);
    if (rg && *(uint16_t*)(rg + 0x2fc) == (uint16_t)year) in++;
  }
  logf("fl26swiss: cup %u -- %d of %d group(s) entered no season; season %d built for them%s: %d of %d now in it",
       (unsigned)master, out, n, year, cleared ? " (its old slot of that year cleared)" : "", in, n);
}
/* B243: one pot into the groups, club i of the pot (association key[i]) into a group that has
   no club of its association yet (has[g][0..filled)), each group once; groups tried in a random
   order, so the draw stays a draw. 1 with to[] set, 0 when no such placing exists. */
static int pot_place(const int* key, int i, int groups, int has[CCUP_MAX_GROUPS][8], int filled,
                     int* used, int* to)
{
  if (i == groups) return 1;
  unsigned order[CCUP_MAX_GROUPS];
  for (int g = 0; g < groups; g++) order[g] = (unsigned)g;
  for (unsigned x = (unsigned)groups - 1; x > 0; x--) {
    unsigned j = q_rand(x + 1), s = order[x]; order[x] = order[j]; order[j] = s;
  }
  for (int o = 0; o < groups; o++) {
    int g = (int)order[o], clash = 0;
    if (used[g]) continue;
    for (int q = 0; q < filled && !clash; q++) clash = has[g][q] == key[i];
    if (clash) continue;
    used[g] = 1; to[i] = g;
    if (pot_place(key, i + 1, groups, has, filled, used, to)) return 1;
    used[g] = 0;
  }
  return 0;
}

/* B243: a draw of `groups` groups out of pots of `groups` clubs each (field[pot * groups + g]),
   one club of every pot in each group, keeping clubs of one association (key) apart: each pot
   goes in by pot_place, and a pot that cannot be placed so starts the draw again. When none of
   the 200 draws keeps every association apart, the one with the fewest same-association pairs
   stands (a pot that cannot be placed goes in at random). Returns that number; *tries the draws
   it took. */
static int pot_draw(const uint32_t* field, const int* key, unsigned n, int groups,
                    uint32_t grp[CCUP_MAX_GROUPS][8], int* tries)
{
  unsigned per = n / (unsigned)groups;
  int best = -1;
  for (*tries = 0; *tries < 200 && best != 0; (*tries)++) {
    uint32_t t[CCUP_MAX_GROUPS][8]; int kt[CCUP_MAX_GROUPS][8], pairs = 0;
    for (unsigned pot = 0; pot < per; pot++) {
      int used[CCUP_MAX_GROUPS] = { 0 }, to[CCUP_MAX_GROUPS];
      const int* pk = key + pot * (unsigned)groups;
      if (!pot_place(pk, 0, groups, kt, (int)pot, used, to)) {
        unsigned perm[CCUP_MAX_GROUPS];
        for (int g = 0; g < groups; g++) perm[g] = (unsigned)g;
        for (unsigned i = (unsigned)groups - 1; i > 0; i--) {
          unsigned j = q_rand(i + 1), s = perm[i]; perm[i] = perm[j]; perm[j] = s;
        }
        for (int g = 0; g < groups; g++) to[g] = (int)perm[g];
      }
      for (int g = 0; g < groups; g++) {
        unsigned e = pot * (unsigned)groups + (unsigned)g;
        for (unsigned q = 0; q < pot; q++) pairs += kt[to[g]][q] == key[e];
        t[to[g]][pot] = field[e]; kt[to[g]][pot] = key[e];
      }
    }
    if (best < 0 || pairs < best) { best = pairs; memcpy(grp, t, sizeof t); }
  }
  return best;
}

static int ko_sync(uint16_t reg, const char* why);
static int ccup_fill_one(int k, void* started)
{
  const ccup_t* c = &g_ccup[k];
  unsigned char* rec = get_rec(c->reg);
  if (!ccup_world(c)) { logf("fl26swiss: cup %u -- its rows are not all in this world; left alone", (unsigned)c->reg); return 0; }
  unsigned held = rec_count(rec);
  int anew = 0;
  if (c->groups && (held || rec_count(get_rec(ccup_rep(c, 0))))) {
    /* B172: the July teardown takes a group cup out of its season (+0x2fc 0xffff) but leaves last
       season's clubs in its lists, and "any club = filled" then never filled it again: from the
       second season its groups entered no season and day 47 drew no knockout (r12, third season,
       day 257: cups 286..296 "already hold" 16/32 clubs, every group out of season). Filled means
       filled this season: the cup or a group in a season. Anything else is filled anew, once a
       season, so a cup whose groups still do not get in is not drawn over and over. */
    int live = rec && *(const uint16_t*)(rec + 0x2fc) != 0xffff;
    for (int g = 0; g < c->groups && !live; g++) {
      unsigned char* rg = get_rec(ccup_rep(c, g));
      live = rg && *(const uint16_t*)(rg + 0x2fc) != 0xffff;
    }
    int year = (abs_day() + 183) / 365;
    if (live || g_ccup_anew_year[k] == year) {
      logf("fl26swiss: cup %u already holds %u clubs%s; not filled again", (unsigned)c->reg, held,
           live ? " in this season" : " (filled anew once this season)");
      return 0;
    }
    g_ccup_anew_year[k] = year;
    anew = 1;
    logf("fl26swiss: cup %u still holds %u club(s) of an earlier season, its groups in no season -- filled anew",
         (unsigned)c->reg, held);
  }
  unsigned n = 0, gaps = 0, cn = ccup_size(c);
  uint16_t unplayed_phase = 0;
  g_ccup_nf[k] = 0;
  if (!cn) return 0;
  if (!c->national) cont_build();                 /* this season's Libertadores / AFC places, for ccup_club */
  int suda = modern_suda_ccup() == k;
  int single = ccup_like_ok(c);
  if (single)
    logf("fl26swiss: cup %u -- a single-match knockout of %u (reg %u's shape), day %d", (unsigned)c->ko, cn,
         (unsigned)c->like, today());
  for (unsigned i = 0; i < cn; i++) {
    const char* how = ""; uint32_t club = 0;
    if (c->nc) {                                   /* invited by name */
      club = canon_club(full_club(c->clubs[i]));
      if (club && !has_club(g_ccup_field[k], n, club)) {
        g_ccup_field[k][n++] = club; g_ccup_nf[k] = n;
        logf("fl26swiss:   cup %u entry %2u: team %u -> %08x (invited)", (unsigned)c->reg, n, (unsigned)c->clubs[i], club);
      } else {
        logf("fl26swiss:   cup %u entry: team %u is not in any league of this season", (unsigned)c->reg, (unsigned)c->clubs[i]);
        gaps++;
      }
      continue;
    }
    if (c->erank[i] == QUAL_LOSER) {               /* eliminated in Libertadores F3 */
      club = qual_loser(c->ereg[i], g_ccup_field[k], n, &how);
      if (!club)
        logf("fl26swiss:   cup %u entry: reg %u -- %s",
             (unsigned)c->reg, (unsigned)c->ereg[i], how);
    } else if (!c->erank[i]) {                       /* a cup's winner: that one club or none */
      int tk;
      if (lpre_of(c->ereg[i], &tk) >= 0) club = lpre_winner(c->ereg[i], &how);
      else { club = c->cal ? cal_cup_winner(c->ereg[i]) : cup_winner(c->ereg[i]); how = "cup winner"; }
      if (club && has_club(g_ccup_field[k], n, club)) club = 0;
      if (club && suda && lib_taken(canon_club(club))) {
        logf("fl26swiss:   Sudamericana entry: cup/pre-round winner %08x already has a Libertadores place; using same-source fallback if available",
             canon_club(club));
        club = 0;
      }
      if (club && c->ealt[i] && ((!c->national && ccup_taken(club)) || lpre_has(c->ko, club))) club = 0;
      if (!club && c->ealt[i]) {                   /* its league's next club (alt=) */
        for (int rank = c->efrom[i] ? c->efrom[i] : 1; rank <= FINAL_MAX; rank++) {
          uint32_t a = ccup_club(c, c->ealt[i], rank, &how);
          if (!a) break;
          if (suda && (a >> 14) && lib_taken(canon_club(a))) {
            logf("fl26swiss:   Sudamericana entry: source %u fallback position %d -> %08x skipped; already in Libertadores",
                 (unsigned)c->ealt[i], rank, canon_club(a));
            continue;
          }
          if ((a >> 14) && !ccup_cont(how) && !has_club(g_ccup_field[k], n, a) && (c->national || !ccup_taken(a)) && !lpre_has(c->ko, a)) {
            club = a;
            logf("fl26swiss:   cup %u entry: reg %u's winner place goes to reg %u position %d", (unsigned)c->reg,
                 (unsigned)c->ereg[i], (unsigned)c->ealt[i], rank);
            break;
          }
        }
      }
      if (!club && c->first[i]) {
        club = canon_club(full_club(c->first[i]));
        how = "first-season fallback";
        if (club && has_club(g_ccup_field[k], n, club)) club = 0;
      }
      if (!club) logf("fl26swiss:   cup %u entry: reg %u has no winner to send", (unsigned)c->reg, (unsigned)c->ereg[i]);
    } else
    for (int rank = c->erank[i]; rank <= FINAL_MAX; rank++) {
      club = ccup_club(c, c->ereg[i], rank, &how);
      if (!club) break;
      if (suda && (club >> 14) && lib_taken(canon_club(club))) {
        logf("fl26swiss:   Sudamericana entry: source %u position %d -> %08x skipped; already in Libertadores",
             (unsigned)c->ereg[i], rank, canon_club(club));
        club = 0;
        continue;
      }
      if ((club >> 14) && !ccup_cont(how) && !has_club(g_ccup_field[k], n, club) && (c->national || !ccup_taken(club))
          && !lpre_has(c->ko, club) && !lpre_has(0, club)) break;
      club = 0;
    }
    if (club) {
      const split_t* sp;
      if (split_part(c->ereg[i], &sp) >= 2 && strcmp(how, "played matches") && strcmp(how, "live table")
          && strcmp(how, "kept table"))
        unplayed_phase = c->ereg[i];
      uint32_t v = canon_club(club);
      char note[48];
      if (v != club) logf("fl26swiss:   cup %u: %08x does not name its team record (%s) -- %08x taken",
                          (unsigned)c->reg, club, club_note(club, note, sizeof note), v);
      club = v;
      g_ccup_field[k][n++] = club; g_ccup_nf[k] = n;
      logf("fl26swiss:   cup %u entry %2u: reg %u position %u -> %08x (%s)", (unsigned)c->reg, n,
           (unsigned)c->ereg[i], (unsigned)c->erank[i], club, how);
    } else gaps++;
  }
  /* A playoff of an Apertura or a Clausura that was never played has no order to go by: the
     squad-strength or list order put four clubs of a Venezuelan Apertura nobody had played into
     its playoff, which then never started either (#37). Left empty instead. */
  if (unplayed_phase) {
    logf("fl26swiss: cup %u -- reg %u has no played match to rank its clubs by; the playoff is not filled",
         (unsigned)c->reg, (unsigned)unplayed_phase);
    g_ccup_nf[k] = 0;
    return 0;
  }
  /* B160: in a second season the game's own AFC Champions League takes most of J1, the clubs
     passed over as ccup_taken, and the AFC Champions League Two found 28 of its 32 and was never
     played at all. A place no club is left for goes to the next club of the leagues the cup takes
     its places from, the last of them first (the leagues that fill it up) -- one rank of each in
     turn -- before the cup is given up. */
  if (n < cn && !c->nc && !c->national) {
    uint16_t lg[CCUP_MAX_ENTRY]; int top[CCUP_MAX_ENTRY], nl = 0;
    for (int i = (int)cn - 1; i >= 0; i--) {
      if (!c->erank[i]) continue;
      int j = 0;
      while (j < nl && lg[j] != c->ereg[i]) j++;
      if (j == nl) { lg[nl] = c->ereg[i]; top[nl++] = 0; }
      if (c->erank[i] > top[j]) top[j] = c->erank[i];
    }
    int more = 1;
    for (int r = 1; n < cn && more && r <= FINAL_MAX; r++) {
      more = 0;
      for (int j = 0; j < nl && n < cn; j++) {
        const char* how = "";
        if (top[j] + r > FINAL_MAX) continue;
        uint32_t club = ccup_club(c, lg[j], top[j] + r, &how);
        if (!club) continue;
        more = 1;
        if (!(club >> 14) || ccup_cont(how) || ccup_taken(club) || lpre_has(c->ko, club)) continue;
        club = canon_club(club);
        if (has_club(g_ccup_field[k], n, club)) continue;
        g_ccup_field[k][n++] = club; g_ccup_nf[k] = n;
        logf("fl26swiss:   cup %u entry %2u: reg %u position %d -> %08x (%s; in place of a club taken elsewhere)",
             (unsigned)c->reg, n, (unsigned)lg[j], top[j] + r, club, how);
      }
    }
  }
  if (n != cn) {
    logf("fl26swiss: cup %u -- only %u of %u clubs found; not started", (unsigned)c->reg, n, cn);
    g_ccup_nf[k] = 0;
    return 0;
  }
  if (!c->groups) {
    /* A knockout cup keeps last season's clubs through the July teardown: the CAF Super Cup of a
       second season still held the pair of the first, and the old "any club in it = filled"
       test left it at that, never registered (2026-09-30, cup 201). Only this season's own
       field -- a save made after the fill and loaded again -- counts as filled; anything else
       is replaced (set_clubs clears the list first). */
    if (held) {
      int same = held == n;
      for (unsigned i = 0; i < n && same; i++) same = has_club(rec_clubs(rec), held, g_ccup_field[k][i]);
      if (same) {
        /* A save of an earlier module: the play-off was filled when its leagues were over and
           started with no match at all (the started list was never handed on, see
           ccup_fill_leagues_over). Before its first day it gets its matches now, so a career
           already running plays it this season (mp31, 08.11.2026: 734 and nine more). */
        if (!started && !c->groups && ccup_matches(c->ko) == 0 && c->nd &&
            season_ord(today()) <= season_ord(c->days[0])) {
          uint16_t id = c->ko;
          struct { uint16_t* b; uint16_t* e; uint16_t* c; } rv = { &id, &id + 1, &id + 1 };
          ((regall_fn)(uintptr_t)(g_base + REGALL_RVA))(0, &rv);
          run_flush();
          logf("fl26swiss: cup %u holds this season's %u clubs but no match -- registered now, %d match record(s)",
               (unsigned)c->ko, held, ccup_matches(c->ko));
          ko_sync(c->ko, "registered");
          return 1;
        }
        logf("fl26swiss: cup %u already holds this season's %u clubs; not filled again", (unsigned)c->reg, held);
        return 0;
      }
      /* a domestic cup's shape: should the game ever fill and register it itself, its matches
         stand -- filling it again over unplayed matches would leave them without clubs */
      if (single && ccup_unplayed(c->ko) > 0) {
        logf("fl26swiss: cup %u -- the game has filled it itself (%u clubs, %d unplayed match(es)); left as it is",
             (unsigned)c->ko, held, ccup_unplayed(c->ko));
        return 0;
      }
      logf("fl26swiss: cup %u still holds %u club(s) of an earlier season (%08x ...) -- filled anew",
           (unsigned)c->reg, held, rec_clubs(rec)[0]);
    }
    /* B181: its rounds of last season too -- the schedule builder reuses a round it finds, and
       register_all then gives only the match records this season's clubs */
    ((freetab_fn)(uintptr_t)(g_base + FREETAB_RVA))(0, c->ko);
    u32vec v = { g_ccup_field[k], g_ccup_field[k] + n, g_ccup_field[k] + n };
    ((setcl_fn)(uintptr_t)(g_base + SETCL_RVA))(c->ko, &v, 1);
    run_flush();
    logf("fl26swiss: cup %u -- day %d: knockout of %u clubs (%08x v %08x ...)", (unsigned)c->ko, today(),
         rec_count(rec), g_ccup_field[k][0], g_ccup_field[k][1]);
    check_reg(c->ko, "filled");
    if (rec_count(rec) != n) return 0;
    start_stage(started, c->ko);
    /* Starting a stage does not make its matches: register_all does, for the ids the progression
       hands it. A cup filled on its fill day or at the July teardown has no progression behind
       it (started is NULL), so its knockout was started with no match at all -- the CAF Super
       Cup and a pre-season cup never played (2026-09-30: cup 201 started, 0 records). The group
       path below registers its groups itself; do the same here. */
    if (!started) {
      uint16_t id = c->ko;
      struct { uint16_t* b; uint16_t* e; uint16_t* c; } rv = { &id, &id + 1, &id + 1 };
      ((regall_fn)(uintptr_t)(g_base + REGALL_RVA))(0, &rv);
      run_flush();
      logf("fl26swiss: cup %u -- knockout registered, %d match record(s)", (unsigned)c->ko,
           ccup_matches(c->ko));
    }
    ko_sync(c->ko, "filled");
    return 1;
  }
  if (anew)                                         /* last season's groups, emptied before the draw */
    for (int g = 0; g < c->groups; g++) {
      u32vec e = { g_ccup_field[k], g_ccup_field[k], g_ccup_field[k] };
      ((setcl_fn)(uintptr_t)(g_base + SETCL_RVA))(ccup_rep(c, g), &e, 1);
    }
  u32vec v = { g_ccup_field[k], g_ccup_field[k] + n, g_ccup_field[k] + n };
  ((setcl_fn)(uintptr_t)(g_base + SETCL_RVA))(c->reg, &v, 1);
  run_flush();
  u32vec w = { g_ccup_field[k], g_ccup_field[k] + n, g_ccup_field[k] + n };
  ((gdraw_fn)(uintptr_t)(g_base + GDRAW_RVA))(c->reg, &w, 1);
  run_flush();
  /* Modern Sudamericana: entry order is four pots of eight. Keep one club from
     each pot in every group instead of letting the generic draw bunch the
     first-stage winners together. */
  if (c->cal && c->groups && n % c->groups == 0 && n / c->groups <= 8) {
    unsigned per = n / c->groups;
    uint32_t grp[CCUP_MAX_GROUPS][8];
    /* B243: no two clubs of one association in a group, CONMEBOL's rule (antonimus, 26.10.:
       Velez and Argentinos Juniors in one Sudamericana group); club_key as the league phase's.
       A club out of the Libertadores qualifying may go beside its own association. */
    int key[CCUP_MAX_GROUPS * 8], best, tries = 0;
    unsigned char* own = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
    void* blk = own ? *(void**)(own + 0x48) : 0;
    /* a club out of the Libertadores qualifying is let in beside its own association: a key of its own */
    for (unsigned i = 0; i < n; i++)
      key[i] = !blk || from_qual(c, cn, g_ccup_field[k][i]) ? 3000 + (int)i : club_key(blk, g_ccup_field[k][i], (int)i);
    best = pot_draw(g_ccup_field[k], key, n, c->groups, grp, &tries);
    logf("fl26swiss: cup %u -- groups by pots: %d same-association pair(s) after %d draw(s)%s",
         (unsigned)c->reg, best, tries, best ? " -- no draw keeps every association apart; the closest one stands" : "");
    for (int g = 0; g < c->groups; g++) {
      u32vec gv = { grp[g], grp[g] + per, grp[g] + per };
      ((setcl_fn)(uintptr_t)(g_base + SETCL_RVA))(ccup_rep(c, g), &gv, 1);
      run_flush();
      int kg[4] = { 0, 0, 0, 0 };
      for (unsigned q = 0; q < per && q < 4; q++)
        for (unsigned i = 0; i < n; i++)
          if (g_ccup_field[k][i] == grp[g][q]) { kg[q] = key[i]; break; }
      logf("fl26swiss: cup %u -- group %c by pots: %08x %08x %08x %08x (associations %d %d %d %d)",
           (unsigned)c->reg, 'A' + g, grp[g][0], per > 1 ? grp[g][1] : 0, per > 2 ? grp[g][2] : 0,
           per > 3 ? grp[g][3] : 0, kg[0], kg[1], kg[2], kg[3]);
    }
  }
  char line[96]; int p = 0;
  uint16_t reps[CCUP_MAX_GROUPS];
  for (int g = 0; g < c->groups; g++) {
    reps[g] = ccup_rep(c, g);
    unsigned char* rg = get_rec(reps[g]);
    p += snprintf(line + p, sizeof line - p, " %c:%u", 'A' + g, rg ? rec_count(rg) : 0);
  }
  logf("fl26swiss: cup %u -- day %d: %u clubs drawn, groups%s", (unsigned)c->reg, today(), rec_count(rec), line);
  struct { uint16_t* b; uint16_t* e; uint16_t* c; } rv = { reps, reps + c->groups, reps + c->groups };
  table_pool_reap("cup draw");
  ((regall_fn)(uintptr_t)(g_base + REGALL_RVA))(0, &rv);
  run_flush();
  logf("fl26swiss: cup %u -- groups %u..%u handed to register_all", (unsigned)c->reg, (unsigned)reps[0],
       (unsigned)reps[c->groups - 1]);
  ccup_season_fix(c->reg, reps, c->groups);
  g_ccup_done[k] = 0;
  return 0;
}
/* at the July teardown: the final tables of the leagues our cups take places from, for those
   leagues the teardown is closing (`ids`, n of them) -- a league still in its season (the Chinese
   one, February to November) keeps going by its live table. access_capture keeps the UEFA
   leagues' only, so the AFC Champions League took J1 and the Saudi league, played August to May
   in a world with game seasons, by squad strength in the second summer too (run022, 2026-10-07). */
/* 1 when every match regulation reg has is played (and it has some): a season over, whether or
   not the teardown names it */
static int season_played(uint16_t reg)
{
  const unsigned char* bs = (const unsigned char*)(g_base + MATCH_BASE_SITE);
  const unsigned char* cs = (const unsigned char*)(g_base + MATCH_CAP_SITE);
  if (bs[0] != 0x48 || bs[1] != 0x8d || bs[2] != 0x88 || cs[0] != 0x81 || cs[1] != 0xff) return 0;
  uint32_t base = *(const uint32_t*)(bs + 3), cap = *(const uint32_t*)(cs + 2);
  unsigned char* o = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
  unsigned char* blk = o ? *(unsigned char**)(o + 0x48) : 0;
  if (!blk || !cap || cap > 200000) return 0;
  int all = 0, played = 0;
  for (uint32_t i = 0; i < cap; i++) {
    const unsigned char* m = blk + base + (size_t)i * MATCH_STRIDE;
    if (*(const uint16_t*)m == 0xffff || *(const uint16_t*)(m + 4) != reg) continue;
    all++; played += (m[7] & 0x40) != 0;
  }
  return all > 0 && played == all;
}
static void ccup_keep_tables(const uint16_t* ids, int n)
{
  int d = today(), ad = abs_day();
  if (d < 140 || d > 230) return;
  for (int k = 0; k < g_nccup; k++)
    for (unsigned i = 0; i < g_ccup[k].n; i++) {
      uint16_t regs[2] = { g_ccup[k].erank[i] ? g_ccup[k].ereg[i] : 0, g_ccup[k].ealt[i] };
      for (int r = 0; r < 2; r++) {
        int closing = 0;
        for (int j = 0; j < n && regs[r] && !closing; j++) closing = ids[j] == regs[r];
        /* J1 and the Saudi league played August to May (run023, 2026-10-07): the exe's event
           table closes them at New Year, so the summer teardown never names them and their
           finished table was not kept -- the AFC cups took them by squad strength again */
        if (!closing && regs[r]) closing = season_played(regs[r]);
        if (closing && keep_final(regs[r], d, ad) > 0) {
          logf("fl26swiss: reg %u -- final table kept for cup %u (day %d)", (unsigned)regs[r],
               (unsigned)g_ccup[k].reg, d);
        }
      }
    }
}
/* at the July teardown, before our cups are closed: the winners the cups' <reg>:0 entries ask
   for, kept as access_capture keeps the UEFA holders' (a second teardown of the same summer
   leaves them) */
static void ccup_keep_winners(int cal)
{
  int d = today(), ad = abs_day();
  /* UEFA-year cups are captured in July. South-American cal=1 cups are captured
     at the calendar-year teardown, before their November winner is reset. */
  if (!cal && (d < 140 || d > 230)) return;
  for (int k = 0; k < g_nccup; k++) {
    if ((g_ccup[k].cal != 0) != (cal != 0)) continue;
    for (unsigned i = 0; i < g_ccup[k].n; i++) {
      uint16_t reg = g_ccup[k].ereg[i];
      int tk;
      if (g_ccup[k].erank[i] || lpre_of(reg, &tk) >= 0) continue;
      cupwin_t* w = cupwin_of(reg);
      if (w && ad >= w->day && ad - w->day < 60) continue;
      uint32_t c = ccup_ko_winner(reg);
      if (!c) continue;
      if (!w) { if (g_ncupwin >= CUPWIN_N) continue; w = &g_cupwin[g_ncupwin++]; w->reg = reg; }
      w->day = ad; w->club = c;
      logf("fl26swiss: cup reg %u won by %08x (day %d), kept for cup %u", (unsigned)reg, c, d, (unsigned)g_ccup[k].ko);
    }
    /* Keep the custom cup's own champion as well. Champions-tier cups need it for the
       Club World Cup; the modern Sudamericana needs it independently for next season's
       Libertadores titleholder and the Recopa, even though ccup_tier() classifies it as tier 1. */
    if (!g_ccup[k].national && (!ccup_tier(&g_ccup[k]) || modern_suda_ccup() == k)) {
      uint16_t reg = g_ccup[k].ko;
      cupwin_t* w = cupwin_of(reg);
      if (!(w && ad >= w->day && ad - w->day < 60)) {
        uint32_t c = ccup_ko_winner(reg);
        if (c) {
          if (!w && g_ncupwin < CUPWIN_N) { w = &g_cupwin[g_ncupwin++]; w->reg = reg; }
          if (w) {
            w->day = ad; w->club = c;
            logf("fl26swiss: cup %u won by %08x (day %d), retained as continental champion", (unsigned)reg, c, d);
          }
        }
      }
    }
  }
}
/* the Club World Cup's African (Asian ...) champions: the last winner of each continental cup of
   ours the league champions go to, kept at the July teardown (ccup_keep_winners) -- the draw is
   in late November, the final in May, so it is last season's, as the UEFA winners are. A new
   career has none yet: the game's own entrants stand in. */
static int ccup_champions(uint32_t* out, int max, uint16_t* cup)
{
  int n = 0, ad = abs_day();
  for (int k = 0; k < g_nccup && n < max; k++) {
    if (g_ccup[k].national || ccup_tier(&g_ccup[k])) continue;
    cupwin_t* w = cupwin_of(g_ccup[k].ko);
    if (!w || ad < w->day || ad - w->day > 300 || !(w->club >> 14)) continue;
    cup[n] = g_ccup[k].ko; out[n++] = w->club;
  }
  return n;
}
static int ccup_fill(void* started)
{
  int any = 0;
  for (int k = 0; k < g_nccup; k++)
    if (!g_ccup[k].fill && !g_ccup[k].cal) any |= ccup_fill_one(k, started);
  return any;
}

/* the continental cups whose winners are champions for the Club World Cup of 32: the game's
   Champions League, Libertadores and AFC Champions League knockouts, and every cup of ours the
   league champions go to (ccup_champions' cups) */
static int champ_cups(uint16_t* reg, int max)
{
  int n = 0;
  static const uint16_t GAME[3] = { R_UCLKO, R_LIBKO, 16 };
  for (int i = 0; i < 3 && n < max; i++) reg[n++] = GAME[i];
  for (int k = 0; k < g_nccup && n < max; k++)
    if (!g_ccup[k].national && !ccup_tier(&g_ccup[k])) reg[n++] = g_ccup[k].ko;
  return n;
}
/* every champions' cup with a winner now: told to fl26cwc.dll, which keeps the titles per save */
static void champ_note(const char* when)
{
  cwcchamp_fn tell = (cwcchamp_fn)(void*)cwc_rank_proc("fl26_cwc_champion");
  if (!tell || !cwc_world()) return;
  uint16_t cups[MAX_CCUP_FWD + 3];
  int n = champ_cups(cups, MAX_CCUP_FWD + 3);
  for (int i = 0; i < n; i++) {
    uint32_t c = get_rec(cups[i]) ? winner_now(cups[i]) : 0;
    if (c && tell(cups[i], c) == 1)
      logf("fl26swiss: Club World Cup -- cup %u won by %08x, a title for the draw (%s, day %d)", (unsigned)cups[i], c,
           when, today());
  }
}

/* the cups with a fill day of their own (a pre-season cup in July): from the loader's tick, once
   a year, on that day or any day up to the eve of the cup's first match (a career that starts
   after the fill day still gets it) */
/* a day of the year as a place in the season, which turns in July (day 182 = 0): an Apertura
   playoff is filled on day 364 and played in January */
static int season_ord(int d) { return d >= 182 ? d - 182 : d + 183; }
static void ccup_fill_days(void)
{
  int d = today(), year = (abs_day() + 183) / 365;             /* the season, not the calendar year */
  if (d < 1) return;
  for (int k = 0; k < g_nccup; k++) {
    ccup_t* c = &g_ccup[k];
    if (!c->fill) continue;
    int f = season_ord(c->fill), s = season_ord(d);
    int first = (c->cal && c->groups) ? g_ccup_gday0[k] : (c->nd ? c->days[0] : 0);
    int last = (first && season_ord(first) > f) ? season_ord(first) - 1 : f + 7;   /* up to the eve of its first day */
    if (s < f || s > last) continue;
    if (c->filled_year == year || !ccup_world(c)) {
      /* Megapack 07.11.: the promotion play-offs (657-659) never filled on days 147-149 and were
         not played; say why, once a season */
      if (c->why_year != year) {
        c->why_year = year;
        logf("fl26swiss: cup %u -- its fill day %u (day %d), not filled now: season %d, filled for %d, ko %s, reg %s, groups %u",
             (unsigned)c->ko, (unsigned)c->fill, d, year, c->filled_year, get_rec(c->ko) ? "there" : "MISSING",
             c->reg ? (get_rec(c->reg) ? "there" : "MISSING") : "none", (unsigned)c->groups);
      }
      continue;
    }
    c->filled_year = year;
    logf("fl26swiss: cup %u -- its fill day %u (day %d)", (unsigned)c->ko, (unsigned)c->fill, d);
    ccup_fill_one(k, 0);
  }
}

/* A promotion play-off (Regionalliga Nord, the Primera Federacion groups) takes its clubs from the
 * final tables of leagues that end in May, and its fill day is a few days after the last of them.
 * Those days have nothing on them: once the leagues are over the game goes straight on to the next
 * day with something on it, and the Megapack's three play-offs (657-659, fill days 147-149) were
 * never filled or played -- in a season run measured 07.11., the day loop's check was not called
 * once on days 140-152. The day the last of its leagues plays its last match is a day the game
 * does stop on: the game asks for that league's progression then. So a cup of the leagues' own
 * season (its fill day before 1 July, at most 60 days ahead) is filled as soon as every league it
 * takes clubs from is over. A cup filled in the new season (a league cup in August) is left to its
 * fill day: the July teardown comes between. */
/* What fl26chain needs at the season end, kept while it still exists (Megapack mp31, 08.11.2026).
 * By the time the season-end apply runs, the new season's schedule is built: the promotion
 * play-offs' match records are gone ("0 of its 1 ties played" for every play-off, all of them
 * played on 25 June) and so are the split groups' tables ("none either from its groups", 852:0
 * 853:0). So a national cup's winner is kept when its last match is played (its progression),
 * and a split group's final table when its last round is (the group's progression), both in
 * g_cupwin / g_final, which fl26swiss-state.bin carries over a save. fl26chain asks for them
 * (fl26_swiss_kept_winner, fl26_swiss_kept_table) when the game has nothing any more. */
static void ccup_keep_national_winner(uint16_t r)
{
  if (r <= 175) return;
  for (int k = 0; k < g_nccup; k++) {
    const ccup_t* c = &g_ccup[k];
    if (c->ko != r || c->groups || !c->national) continue;
    if (ccup_matches(r) <= 0 || ccup_unplayed(r) != 0) return;
    uint32_t w = ccup_ko_winner(r);
    if (!w) return;
    int ad = abs_day();
    cupwin_t* cw = cupwin_of(r);
    if (!cw) { if (g_ncupwin >= CUPWIN_N) return; cw = &g_cupwin[g_ncupwin++]; cw->reg = r; }
    cw->day = ad; cw->club = w;
    logf("fl26swiss: cup %u won by %08x (day %d), kept for the season end", (unsigned)r, w, today());
    return;
  }
}
__declspec(dllexport) uint32_t fl26_swiss_kept_winner(uint16_t reg, int max_age)
{
  cupwin_t* w = cupwin_of(reg);
  int ad = abs_day();
  return (w && ad >= w->day && ad - w->day <= max_age) ? w->club : 0;
}
__declspec(dllexport) int fl26_swiss_kept_table(uint16_t reg, int max_age, uint32_t* out, int cap)
{
  final_t* f = final_of(reg);
  int ad = abs_day();
  if (!f || !out || ad < f->day || ad - f->day > max_age) return 0;
  int n = f->n < cap ? f->n : cap;
  for (int i = 0; i < n; i++) out[i] = f->club[i];
  return n;
}

/* A cup filled here registers its own matches (ccup_fill_one with no started list), as on its fill
 * day. The list of the league's progression is handed on only when that progression answers 1, and
 * a league's last progression answers 0: the Megapack's promotion play-offs (657-659, 717-767) were
 * filled and started this way with no match record at all, and none was ever played (mp30,
 * 08.11.2026: 0 records on 10 and 25 June). The same went for the cups filled at the end of a
 * split phase (733-747). */
static int g_lg_over[1024];                /* 1 + the season a league's progression was asked in */
static void ccup_fill_leagues_over(uint16_t r, void* started)
{
  int d = today();
  if (d < 1 || r >= 1024) return;
  int s = season_ord(d), year = lpre_year(), mine = 0;
  for (int k = 0; k < g_nccup; k++) {
    ccup_t* c = &g_ccup[k];
    if (!c->fill || c->groups || !c->national) continue;
    /* 14.11.2026 (Build 16, season 2): the game asks for a league's progression once more on the
       July turn (day 182), which is already the new season: reg 134 was marked over for a season
       that had not begun, and next May the Scottish play-off (724) was filled on day 129 from the
       live table, three weeks before the split groups ended. Only a progression within reach of
       a cup's fill day (the same 60 days as the fill below) is a league's end. */
    int f = season_ord(c->fill);
    if (f <= s || f - s > 60) continue;
    for (unsigned i = 0; i < c->n; i++) if (c->ereg[i] == r) mine = 1;
  }
  if (!mine) return;
  {
    /* B425: the regular phase of a split season of the game's own is not the league's end */
    const gsplit_t* g = gsplit_regular(r);
    if (g && !gsplit_keep(g)) {
      static int said[MAX_GSPLIT];
      int i = (int)(g - g_gsplit);
      if (said[i] != year + 1)
        logf("fl26swiss: reg %u -- its regular phase is over on day %d, its groups (reg %u, %u) are not: a play-off that takes its place waits for them",
             (unsigned)r, d, (unsigned)g->group[0], (unsigned)g->group[1]);
      said[i] = year + 1;
      return;
    }
  }
  if (g_lg_over[r] != year + 1) logf("fl26swiss: reg %u -- progression on day %d, a promotion play-off's league", (unsigned)r, d);
  g_lg_over[r] = year + 1;
  for (int k = 0; k < g_nccup; k++) {
    ccup_t* c = &g_ccup[k];
    if (!c->fill || c->groups || !c->national) continue;
    int from = 0;
    for (unsigned i = 0; i < c->n; i++) if (c->ereg[i] == r) from = 1;
    if (!from) continue;
    int f = season_ord(c->fill);
    if (f <= s || f - s > 60) continue;    /* not this season's, or too far off */
    uint16_t wait = 0;
    for (unsigned i = 0; i < c->n && !wait; i++)
      if (c->ereg[i] < 1024 && g_lg_over[c->ereg[i]] != year + 1) wait = c->ereg[i];
    if (wait) {
      logf("fl26swiss: cup %u -- reg %u is over on day %d, reg %u is not yet", (unsigned)c->ko, (unsigned)r, d, (unsigned)wait);
      continue;
    }
    if (c->filled_year == year || !ccup_world(c)) continue;
    c->filled_year = year;
    logf("fl26swiss: cup %u -- filled on day %d, its last league (reg %u) over, %d day(s) before its fill day %u",
         (unsigned)c->ko, d, (unsigned)r, f - s, (unsigned)c->fill);
    ccup_fill_one(k, 0);
  }
}

/* The fill day itself is not a day any code of ours is sure to see. The calendar goes from one
 * day with something on it to the next, and the days in between are never processed: measured
 * 2026-09-29, a new career's day loop skipped 32..33, 35..36, 38..40 in February. The days
 * between a phase's last round and its playoff, or between the July teardown and a pre-season
 * cup, have nothing on them -- the cup has no clubs yet, so no matches -- and the Summer Cup
 * (202) was never filled. So a cup is filled when the thing its fill day waits for happens,
 * which is a day the game does stop on: the end of a split phase its entries come from (the
 * progression, called when the phase's last match is played), or the July teardown (every
 * cup of the new season's first week). Only a fill day at most seven days ahead is taken, and
 * the fill counts for that day's season, so ccup_fill_days does not fill it again. */
static void ccup_fill_ahead(uint16_t src, const char* why, void* started)
{
  int d = today();
  if (d < 1) return;
  int s = season_ord(d);
  for (int k = 0; k < g_nccup; k++) {
    ccup_t* c = &g_ccup[k];
    if (!c->fill) continue;
    int ahead = (season_ord(c->fill) - s + 365) % 365;
    if (ahead > 7) continue;
    int from = !src;
    for (unsigned i = 0; i < c->n && !from; i++) if (c->ereg[i] == src) from = 1;
    if (!from) continue;
    int year = (abs_day() + ahead + 183) / 365;
    if (c->filled_year == year || !ccup_world(c)) continue;
    c->filled_year = year;
    logf("fl26swiss: cup %u -- filled on day %d at %s, %d day(s) before its fill day %u",
         (unsigned)c->ko, d, why, ahead, (unsigned)c->fill);
    ccup_fill_one(k, 0);
  }
}

/* Group g's table: the game's, or, when the cup's next season is open already and that one is
 * empty, the table of the season the group was played in -- the one holding only the group's
 * clubs (season_table_x).  Seen 20.10. in a Worldpack career, second season: on day 47 every group
 * of the CAF and AFC cups read 0 rows, so no knockout was drawn; 0 when there is none. */
static unsigned char* ccup_group_table(const ccup_t* c, int g)
{
  uint16_t id = ccup_rep(c, g);
  unsigned char* t = ((table_fn)(uintptr_t)(g_base + TABLE_RVA))(id);
  uint32_t rows = t ? *(uint32_t*)(t + 0x3c0) : 0;
  if (rows >= 2 && rows <= 8) return t;
  unsigned char* rec = get_rec(id);
  unsigned n = rec ? rec_count(rec) : 0, yr = 0;
  if (n < 2) return 0;
  unsigned char* t2 = season_table_x(id, n, n, rec_clubs(rec), n, &yr);
  if (t2) logf("fl26swiss: cup %u -- group %c: the latest season's table has %u rows; season %u's table (%u rows) is used",
               (unsigned)c->reg, 'A' + g, (unsigned)rows, yr, (unsigned)n);
  return t2;
}
static int ccup_progress(int k, uint16_t r, void* started)
{
  const ccup_t* c = &g_ccup[k];
  unsigned all = (1u << c->groups) - 1;
  if (r == c->reg) g_ccup_done[k] = all;
  else g_ccup_done[k] |= 1u << (((r >> 10) - 1) & 31);
  logf("fl26swiss: cup %u -- progression for reg %u on day %d (groups reported %02x)", (unsigned)c->reg,
       (unsigned)r, today(), g_ccup_done[k]);
  if (g_ccup_done[k] != all) return 0;
  for (int i = 0; i < g_nlpre; i++)
    if (g_lpre[i].poko && g_lpre[i].ko == c->ko) {
      logf("fl26swiss: cup %u -- groups over; round of 16 waits for Sudamericana play-off %u",
           (unsigned)c->reg, (unsigned)g_lpre[i].reg);
      g_ccup_done[k] = 0;
      return 0;
    }
  unsigned char* ko = get_rec(c->ko);
  if (!ko || rec_count(ko)) return 0;
  static uint32_t buf[2 * CCUP_MAX_GROUPS];
  int nk = 2 * c->groups;
  for (int i = 0; i < nk; i++) {
    /* first half: group 2j's winner v group 2j+1's runner-up; second half the other way round */
    int half = i >= c->groups, j = (i % c->groups) / 2, away = i & 1;
    int g = 2 * j + (half ? !away : away), place = away;
    unsigned char* t = ccup_group_table(c, g);
    uint32_t rows = t ? *(uint32_t*)(t + 0x3c0) : 0;
    if (rows < 2 || rows > 8) {
      logf("fl26swiss: cup %u -- group %c has a table of %u rows; knockout not filled", (unsigned)c->reg,
           'A' + g, (unsigned)rows);
      return 0;
    }
    buf[i] = *(uint32_t*)(t + place * 20);
  }
  u32vec v = { buf, buf + nk, buf + nk };
  ((setcl_fn)(uintptr_t)(g_base + SETCL_RVA))(c->ko, &v, 1);
  run_flush();
  logf("fl26swiss: cup %u -- knockout reg %u now %u clubs (A1 %08x v B2 %08x ...)", (unsigned)c->reg,
       (unsigned)c->ko, rec_count(ko), buf[0], buf[1]);
  g_ccup_done[k] = 0;
  if ((int)rec_count(ko) != nk) return 0;
  start_stage(started, c->ko);
  return 1;
}

/* a single-match cup's round (a domestic cup's id: 0x2e up to the quarter-final 0x33, then 0x34,
   0x35) as its place in the cup's own days: one day a round, -1 for an id that is none of them */
static int like_slot(uint32_t round)
{
  switch (round) {
    case 0x2e: return 0; case 0x2f: return 1; case 0x30: case 0x31: case 0x32: return 2;
    case 0x33: return 3; case 0x34: return 4; case 0x35: return 5;
  }
  return -1;
}
static uint64_t ccup_like_dates(int k, uint16_t id, uint64_t reg, void* vec)
{
  const ccup_t* cc = &g_ccup[k];
  uint64_t rv = ((date_fn)(uintptr_t)g_tramp_date)((reg & ~(uint64_t)0xffff) | cc->like, vec);
  vec_t* v = (vec_t*)vec;
  size_t have = (v->b && v->e >= v->b) ? (size_t)(v->e - v->b) / sizeof(date_t) : 0;
  date_t* r = (date_t*)v->b;
  static unsigned char said[MAX_CCUP];
  if (!have || !cc->nd) {
    if (!said[k]) logf("fl26swiss: cup reg %u: reg %u's calendar gave %u record(s), %u day(s) of its own; left as it is",
                       (unsigned)id, (unsigned)cc->like, (unsigned)have, (unsigned)cc->nd);
    said[k] = 1;
    return rv;
  }
  for (size_t i = 0; i < have; i++) {
    int j = like_slot(r[i].kind);
    if (j < 0) j = like_slot(r[i].round);
    if (j < 0) j = (int)(have > 1 ? i * 5 / (have - 1) : 5);    /* by order, the last the final */
    if (!said[k])
      logf("fl26swiss: cup reg %u borrowed record %u: day %u round %#x kind %#x -> day %u", (unsigned)id, (unsigned)i,
           r[i].day, r[i].round, r[i].kind, (unsigned)cc->days[j < cc->nd ? j : cc->nd - 1]);
    r[i].day = cc->days[j < cc->nd ? j : cc->nd - 1];
  }
  if (!said[k])
    logf("fl26swiss: cup reg %u dated as reg %u: %u record(s), days %u..%u", (unsigned)id, (unsigned)cc->like,
         (unsigned)have, r[0].day, r[have - 1].day);
  said[k] = 1;
  return rv;
}

/* B35: the knockout's day table, chosen once a season when the knockout is dated (the day after
   its groups are over, ccup_progress; a straight knockout on its fill day). A career whose groups
   were dated on the days of before 0.2.4 -- a closed-beta career in its first season -- ends them
   later than the table of its region begins its knockout (the AFC Champions League Two: groups
   to Tuesday 17 February, CR_AFC's round of 16 from that same Tuesday), so a knockout whose
   first day (j0) is not after today takes the days of before (CR_NONE) for that season instead
   of a first leg dated in the past. Kept for the season, so a second dating of the same knockout
   cannot change its days. -1: the cup has days of its own (ccup_day). */
static int g_ko_cr[MAX_CCUP], g_ko_cr_year[MAX_CCUP];
static int ccup_ko_table(int k, size_t j0)
{
  ccup_t* c = &g_ccup[k];
  if (c->nd || c->like) return -1;
  int y = season_year() + 1;                           /* 0: never chosen */
  if (g_ko_cr_year[k] == y) return g_ko_cr[k];
  int cr = ccup_region(c), t = today();
  uint32_t d0 = CCUP_KO_DAYS[cr][ccup_tier(c)][j0 < 7 ? j0 : 6];
  uint32_t p0 = d0 >= 182 ? d0 - 182 : d0 + 183, pt = t >= 182 ? (uint32_t)t - 182 : (uint32_t)t + 183;
  if (cr != CR_NONE && t >= 0 && t < 365 && p0 <= pt) {
    logf("fl26swiss: cup %u -- knockout dated on day %d, after its first day %u in %s: its groups were "
         "dated on the days of before, so this season's knockout keeps them", (unsigned)c->ko, t, d0, CR_NAME[cr]);
    cr = CR_NONE;
  }
  g_ko_cr[k] = cr; g_ko_cr_year[k] = y;
  return cr;
}
static uint64_t ccup_dates(int k, int ko, uint16_t id, uint64_t reg, void* vec)
{
  if (ccup_like_ok(&g_ccup[k])) return ccup_like_dates(k, id, reg, vec);
  const ccup_t* cc = &g_ccup[k];
  /* cal=1 cups keep the native Libertadores dates: groups from reg 9 and
     knockout from reg 10. A custom one-off knockout with explicit days keeps
     the normal borrowed calendar instead. */
  int keep = cc->cal && (!ko || !cc->nd);
  uint16_t src = ko ? (keep ? R_LIBKO : R_UCLKO) : R_LIBGROUP;
  uint64_t rv = ((date_fn)(uintptr_t)g_tramp_date)((reg & ~(uint64_t)0xffff) | src, vec);
  vec_t* v = (vec_t*)vec;
  size_t have = (v->b && v->e >= v->b) ? (size_t)(v->e - v->b) / sizeof(date_t) : 0;
  date_t* r = (date_t*)v->b;
  size_t want = ko ? ((cc->nd && !cc->like) ? cc->nd : 7) : 6;   /* like here: an old row, the old days */
  static unsigned said[MAX_CCUP];
  unsigned bit = ko ? 1 : 2;
  if (keep) {
    if (!ko && have && (!g_ccup_gday0[k] || r[0].day < g_ccup_gday0[k])) g_ccup_gday0[k] = (uint16_t)r[0].day;
    if (!(said[k] & bit))
      logf("fl26swiss: cup reg %u dated as the Libertadores' %s (reg %u): %u record(s)",
           (unsigned)id, ko ? "knockout" : "group stage", (unsigned)src, (unsigned)have);
    said[k] |= bit;
    return rv;
  }
  /* FL27 (Megapack 07.11.): the borrowed knockout has 9 records, its knockout play-off pair in
     front of the round of 16, and every play-off of a group set (657..659) was left on those
     days, unplayed. The pair in front goes; the rest is the knockout of before. */
  /* What is left starts with FL27's round of 16, round 0x2f; our cups name their first round 0x2e
     as FL26's calendar does (round 46), and a round no record names is never dated: cups 623/624
     (mp21, 07.11.) had their first round on 65535-00-00, unplayed, and an empty rest. */
  if (ko && have > want && have <= want + 2) {
    memmove(r, r + (have - want), want * sizeof(date_t));
    v->e = v->b + want * sizeof(date_t);
    for (size_t i = 0; i < want; i++) if (r[i].round == 0x2f) r[i].round = 0x2e;
    if (!(said[k] & bit)) logf("fl26swiss: cup reg %u: the borrowed calendar has %u records, the first %u dropped",
                               (unsigned)id, (unsigned)have, (unsigned)(have - want));
    have = want;
  }
  if (have == 0 || have > want) {
    if (!(said[k] & bit)) logf("fl26swiss: cup reg %u: the borrowed calendar has %u records (up to %u expected); left as it is",
                               (unsigned)id, (unsigned)have, (unsigned)want);
    said[k] |= bit;
    return rv;
  }
  if (!(said[k] & bit))
    for (size_t i = 0; i < have; i++)
      logf("fl26swiss: cup reg %u borrowed record %u: day %u round %u kind %u", (unsigned)id, (unsigned)i,
           r[i].day, r[i].round, r[i].kind);
  /* a knockout of eight is handed the round-of-16 pair first; the last record is the final */
  int kcr = ko ? ccup_ko_table(k, have == 1 ? want - 1 : want - have) : -1;
  for (size_t i = 0; i < have; i++) {
    size_t j = ko ? (i + 1 == have ? want - 1 : i + (want - have)) : i * want / have;
    r[i].day = kcr >= 0 ? CCUP_KO_DAYS[kcr][ccup_tier(cc)][j] : ccup_day(cc, ko, (int)j);
  }
  if (!(said[k] & bit))
    logf("fl26swiss: cup reg %u dated: %s days %u..%u (%u records)", (unsigned)id, ko ? "knockout" : "groups",
         r[0].day, r[have - 1].day, (unsigned)have);
  said[k] |= bit;
  return rv;
}

/* A split's regular phase ending: the game hands the clubs to the groups in 0x141343d70, which
 * finds the format 13/14 rows by the competition key and gives each the next N clubs of the
 * regular phase's table. It is generic, but only case 8 of the progression switch calls it, and
 * the switch covers ids 2..175 -- our regular phases (191, 194) fall to the default and the
 * groups stayed empty on 2026-09-26. So call it here, with the arguments case 8 passes. */
#define SPLIT_FN_RVA 0x1343d70
typedef char (*splitfn_t)(void* ctx, uint64_t id, void* started);
typedef struct split_s split_t;
static int split_part(uint16_t id, const split_t** out);
static void split_keys(void);
static void canon_groups(const split_t* s);

char prog_handler(void* ctx, uint64_t id, void* started)
{
  uint16_t r = (uint16_t)id;
  split_keys();
  {
    const split_t* s; int part = split_part(r, &s);
    if (part) {
      char ok = ((prog_fn)(uintptr_t)g_tramp_prog)(ctx, id, started);
      if (part == 2 && r > 175) {
        check_reg(r, "its phase over");
        char sp = ((splitfn_t)(uintptr_t)(g_base + SPLIT_FN_RVA))(ctx, id, started);
        logf("fl26swiss: reg %u -- split regular phase over on day %d, groups filled by 0x141343d70 -> %d",
             (unsigned)r, today(), (int)sp);
        canon_groups(s);
        ok |= sp;
      } else {
        logf("fl26swiss: reg %u -- split progression on day %d -> %d", (unsigned)r, today(), (int)ok);
        if (part > 2 && r > 175 && season_played(r) && keep_final(r, today(), abs_day()) > 0) {
          final_t* kf = final_of(r);
          if (kf && kf->n)
            logf("fl26swiss: reg %u -- split group's final table kept for the season end (day %d, %d clubs): %08x first, %08x last",
                 (unsigned)r, today(), (int)kf->n, kf->club[0], kf->club[kf->n - 1]);
          else
            logf("fl26swiss: reg %u -- split group's final table kept for the season end (day %d)", (unsigned)r, today());
        }
      }
      if (part > 1 && r > 175) ccup_fill_ahead(r, "the end of its phase", started);
      if (part > 1) ccup_fill_leagues_over(r, started);
      return ok;
    }
  }
  if (cwc_id(r) && cwc_world()) {
    char ok = ((prog_fn)(uintptr_t)g_tramp_prog)(ctx, id, started);
    if (cwc_progress(r, started)) ok = 1;
    return ok;
  }
  {
    int ko, k = ccup_of(r, &ko);
    if (k >= 0 && ccup_world(&g_ccup[k])) {
      char ok = ((prog_fn)(uintptr_t)g_tramp_prog)(ctx, id, started);
      if (!ko && ccup_progress(k, r, started)) ok = 1;
      return ok;
    }
  }
  {
    /* When the Sudamericana play-off's final tie finishes, build the round of 16
       immediately. The career can skip quiet days between the second leg and
       the first knockout date, so the day loop alone is not sufficient. */
    int tk, li = lpre_of(r, &tk);
    if (li >= 0 && g_lpre[li].poko) {
      char ok = ((prog_fn)(uintptr_t)g_tramp_prog)(ctx, id, started);
      int before = g_lpre[li].ko_year;
      g_lpre[li].ko_year = -1;
      poko_ko(li, started);
      if (g_lpre[li].ko_year == lpre_year() && before != lpre_year()) ok = 1;
      return ok;
    }
  }
  /* the two play-off hand-overs replace the game's own case, they do not follow it */
  /* The Conference League's six matchdays end in December, not January: its play-off is drawn
     then (and dated in February like the others) -- otherwise the game sends the top 16 straight
     to the round of 16, as it did on 2026-09-24. */
  int dec = today() >= 300;
  if (g_po_enabled && (po_season_half() || dec)) {
    for (int ci = 0; ci < 3; ci++) {
      const cup_t* c = &CUPS[ci];
      if (!cup_on(ci)) continue;
      int begin = r == c->league || (ci && r == c->row), finish = r == c->po;
      if (!begin && !finish) continue;
      if (!po_season_half() && !(ci == 2 && begin)) break;
      if (!po_available(c)) {
        static int said_po[3];
        if (!said_po[ci]++)
          logf("fl26swiss: %s play-off -- this world has no regulation %u (tools/mkeuropo.py adds it); "
               "the game's own progression runs instead", c->name, (unsigned)c->po);
        break;
      }
      int done = begin ? po_start(ci, started) : po_finish(ci, started);
      logf("fl26swiss: progression for reg %u on day %d -- %s", (unsigned)r, today(),
           done ? "handled by the play-off" : "the play-off could not, left to the game");
      if (done) return 1;
      break;
    }
  }
  char ok = ((prog_fn)(uintptr_t)g_tramp_prog)(ctx, id, started);
  {
    /* B425: the last round of a group of the game's own split season ends its league */
    const gsplit_t* g = gsplit_group(r);
    if (g && gsplit_keep(g)) ccup_fill_leagues_over(g->regular, started);
  }
  ccup_fill_leagues_over(r, started);
  ccup_keep_national_winner(r);
  if (european(r) && r < 1024 && !g_prog_seen[r]) {
    g_prog_seen[r] = 1;
    logf("fl26swiss: progression asked for reg %u -> %d", (unsigned)r, (int)ok);
  }
  if (r == 2) { if (uecl_fill(started)) ok = 1; if (ccup_fill(started)) ok = 1; }
  else if (r == UECL_REG || r == UECL_ROW) { if (uecl_ko(started)) ok = 1; }
  return ok;
}

/* ---- the knockout bracket: quarter-finals and semi-finals follow the tree ----
 *
 * A knockout regulation is built up front, one fixture record per round (kind 0x2e round of 16,
 * 0x33 quarter-finals, 0x34 semi-finals, 0x35 final), and every slot of a later round already
 * names the two slots that feed it: +0x18 and +0x1c hold the key (reg | (kind | slot << 6) << 16)
 * of the tie whose winner comes home and of the one whose winner comes away. The Europa League
 * fills its quarter-finals by those keys; the Champions League (type 22) ignores them and draws
 * the eight winners afresh, measured on 2026-09-24 (day 81: 1 v 4, 6 v 2, 0 v 5, 3 v 7). UEFA's
 * bracket since 2024 is fixed from the league phase on, so once the game has filled a round and
 * before its first leg is played, this puts every slot back to the pairing the keys name. The
 * filled round is the only thing written: the slot's two clubs, and the clubs of the two match
 * records it points at (+8 first leg, +0xa second leg, which has them the other way round).
 * A round already in bracket order -- every Europa League round -- is left untouched. */
#define FIXFIND_RVA 0x1579ee0
#define MATCH_RVA   0x14bc560
#define KO_TBD      0x3fffffu
typedef unsigned char* (*fixfind_fn)(const uint16_t* reg, const uint32_t* kind);
typedef unsigned char* (*match_fn)(void* blk, uint64_t id);
static unsigned char* ko_round(uint16_t reg, uint32_t kind)
{
  return ((fixfind_fn)(uintptr_t)(g_base + FIXFIND_RVA))(&reg, &kind);
}
/* A slot keeps its match ids as words. With fl26match's u32 ids (limits branch, past 65535
   matches) the word L is the record L or L + 65536: the one of this regulation (+4) is the tie's.
   Record +0 is the id as a dword there, and +2 is 0 under the game's own 16-bit table. */
static unsigned char* match_of_reg(void* blk, uint32_t lo, uint16_t reg)
{
  for (uint32_t h = 1; h <= 1; h--) {
    uint32_t id = lo | h << 16;
    unsigned char* m = ((match_fn)(uintptr_t)(g_base + MATCH_RVA))(blk, id);
    if (m && *(uint32_t*)m == id && *(uint16_t*)(m + 4) == reg) return m;
  }
  return 0;
}
static unsigned char* ko_match(uint16_t id, uint16_t reg)
{
  unsigned char* o = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
  void* blk = o ? *(void**)(o + 0x48) : 0;
  if (!blk || id == 0xffff) return 0;
  return match_of_reg(blk, id, reg);
}
static uint32_t* ko_slot(unsigned char* rnd, int s) { return (uint32_t*)(rnd + 4 + 32 * s); }
static int ko_slots(unsigned char* rnd) { return rnd ? (int)(*(uint32_t*)(rnd + 0x204) & 0xff) : 0; }

/* ---- the hub's "Next" after a draw of ours (B162) ----
 *
 * The hub's fixture strip does not read the rounds or the match records: it reads the user's day
 * schedule, one entry per day ({match id, competition, round, kind, team}) at block+0x19115f0 for
 * controller 0 (fl26ctlguard.lua has the layout). The game files every scheduled match there as
 * it makes it, so when cup_draw or ko_bracket hand the clubs of made matches out again, the table
 * keeps the old pairing: in game (pokuuuu., Carabao Cup) "Next" showed Chelsea - Tottenham while
 * the user's club, Liverpool, had been drawn against Brentford, as the news and Competition Info
 * said. The day loop rebuilds that table from the match records whenever its owner handle
 * (block+0x19115f4) is not the user's club (block+0x1798ab0); writing -1 there asks for that, the
 * next day -- the same request fl26ctlguard makes after a club change. Only asked while the table
 * is the user's own: anything else is a mode with no career, or a rebuild already on its way. */
#define SCHED_OWNER_OFF (TODAY_OFF + 0x10)
#define USER_CLUB_OFF   lay_user()        /* 0x1798ab0 unless the set moves the lower tail */
/* B258c (antonimus 27.10., beta f469319): the B258 rebuild came the next day, so the hub of a
 * new career -- the first thing the player sees -- still showed the stale strip (Brasileirao
 * matches for a Uruguayan club) until a day was played. The day loop's rebuild is one call,
 * 0x14158c820(controller), the day loop passing 0 (0x141350705: xor ecx,ecx; call). On the
 * first day of a timeline (a career built or a save loaded) a rebuild asked here -- by B258 in
 * the day loop, or by a draw of ours that day -- is done there and then; from the second day on
 * the day loop does it, as before. A new career's first screen needs its league's matches as
 * well, and a January league of ours has none until it is registered (join_on_day0). */
#define SCHED_BUILD_RVA 0x158c820
static const unsigned char SIG_SCHED_BUILD[10] = { 0x81,0xf9,0xff,0x00,0x00,0x00, 0x0f,0x84,0x76,0x07 };
static int g_sched_now_tl = -1, g_sched_now_day = -1;
static int sched_first_day(void)
{
  if (g_sched_now_tl != g_timeline || g_sched_now_day < 0) return 0;
  if (abs_day() != g_sched_now_day) { g_sched_now_tl = -1; return 0; }
  return 1;
}
static void sched_build_now(unsigned char* blk, const char* why)
{
  static int bad;
  if (bad) return;
  if (memcmp((const void*)(uintptr_t)(g_base + SCHED_BUILD_RVA), SIG_SCHED_BUILD, sizeof SIG_SCHED_BUILD)) {
    bad = 1;
    logf("fl26swiss: the schedule rebuild at %llx is not the expected code -- left to the next day (B258c)",
         (unsigned long long)(g_base + SCHED_BUILD_RVA));
    return;
  }
  ((void (*)(int))(uintptr_t)(g_base + SCHED_BUILD_RVA))(0);
  uint32_t user = *(uint32_t*)(blk + USER_CLUB_OFF), owner = *(uint32_t*)(blk + SCHED_OWNER_OFF);
  logf("fl26swiss: the user's day schedule built again now, day %d (%s; B258c: the first day of a career or a load)%s",
       today(), why, owner == user ? "" : " -- owner still not the user's club");
}
static void sched_rebuild(const char* why)
{
#ifdef FL26_RCAL_TEST
  (void)why; return;
#endif
  unsigned char* o = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
  unsigned char* blk = o ? *(unsigned char**)(o + 0x48) : 0;
  if (!blk) return;
  uint32_t user = *(uint32_t*)(blk + USER_CLUB_OFF);
  uint32_t* owner = (uint32_t*)(blk + SCHED_OWNER_OFF);
  if (user == 0 || user == 0xffffffffu || *owner != user) return;
  *owner = 0xffffffffu;
  if (sched_first_day()) { sched_build_now(blk, why); return; }
  logf("fl26swiss: the user's day schedule is built again tomorrow (%s)", why);
}
/* The other finalist of a completed knockout competition. The rights lookup gives
 * the champion; the final fixture row (kind 0x35) gives the two finalists. */
static uint32_t knockout_runner_now(uint16_t reg)
{
  uint32_t win = winner_now(reg);
  if (!(win >> 14)) return 0;

  unsigned char* rnd = ko_round(reg, 0x35);
  if (!rnd || ko_slots(rnd) != 1) return 0;

  uint32_t* sl = ko_slot(rnd, 0);
  uint32_t a = canon_club(sl[0]), b = canon_club(sl[1]);
  if (!(a >> 14) || !(b >> 14) || same_club(a, b)) return 0;
  if (same_club(win, a)) return b;
  if (same_club(win, b)) return a;
  return 0;
}

/* one round of one regulation: 1 = reordered, 0 = nothing to do, -1 = not ready */
static int ko_bracket(uint16_t reg, uint32_t kind, const char* name)
{
  unsigned char* rnd = ko_round(reg, kind);
  int n = ko_slots(rnd);
  if (n < 2 || n > 8) return -1;
  uint32_t fill[16], want[16];
  for (int s = 0; s < n; s++) {
    uint32_t* sl = ko_slot(rnd, s);
    fill[2 * s] = sl[0]; fill[2 * s + 1] = sl[1];
    if ((sl[0] & KO_TBD) == KO_TBD || (sl[1] & KO_TBD) == KO_TBD) return -1;   /* not drawn yet */
  }
  for (int s = 0; s < n; s++) {
    uint32_t* sl = ko_slot(rnd, s);
    for (int side = 0; side < 2; side++) {
      uint32_t key = sl[6 + side];                  /* +0x18 / +0x1c */
      if ((uint16_t)key != reg) return -1;
      unsigned char* prev = ko_round(reg, (key >> 16) & 0x3f);
      int ps = (int)(key >> 22);
      if (!prev || ps >= ko_slots(prev)) return -1;
      uint32_t* src = ko_slot(prev, ps);
      /* the source tie's winner is whichever of its two clubs the game put into this round */
      uint32_t w = 0; int hits = 0;
      for (int k = 0; k < 2 * n; k++)
        for (int j = 0; j < 2; j++)
          if ((fill[k] & KO_TBD) == (src[j] & KO_TBD)) { w = fill[k]; hits++; }
      if (hits != 1) return -1;
      want[2 * s + side] = w;
    }
  }
  int moved = 0;
  for (int k = 0; k < 2 * n; k++) if ((want[k] & KO_TBD) != (fill[k] & KO_TBD)) moved++;
  if (!moved) return 0;
  /* both legs of every tie must still be unplayed (match +7 bit 6) */
  for (int s = 0; s < n; s++) {
    uint16_t* ids = (uint16_t*)(ko_slot(rnd, s) + 2);
    for (int l = 0; l < 2; l++) {
      if (ids[l] == 0xffff) continue;
      unsigned char* m = ko_match(ids[l], reg);
      if (!m || (m[7] & 0x40)) return -1;
    }
  }
  for (int s = 0; s < n; s++) {
    uint32_t* sl = ko_slot(rnd, s);
    uint16_t* ids = (uint16_t*)(sl + 2);
    uint32_t h = want[2 * s], a = want[2 * s + 1];
    sl[0] = h; sl[1] = a;
    unsigned char* m1 = ko_match(ids[0], reg);
    unsigned char* m2 = ko_match(ids[1], reg);
    if (m1) { *(uint32_t*)(m1 + 0x14) = h; *(uint32_t*)(m1 + 0x18) = a; }
    if (m2) { *(uint32_t*)(m2 + 0x14) = a; *(uint32_t*)(m2 + 0x18) = h; }
    logf("fl26swiss:   %s %s tie %d: winner of tie %d (%06x) v winner of tie %d (%06x)", name,
         kind == 0x33 ? "quarter-final" : "semi-final", s, (int)(sl[6] >> 22), h & KO_TBD,
         (int)(sl[7] >> 22), a & KO_TBD);
  }
  logf("fl26swiss: %s %s put back in bracket order (%d club(s) moved); day %d", name,
       kind == 0x33 ? "quarter-finals" : "semi-finals", moved, today());
  sched_rebuild("European bracket order");
  return 1;
}

/* B181: a knockout's rounds name their clubs twice -- in the round's slot (+0, +4) and in its
   match records (+0x14 home, +0x18 away of the first leg) -- and the game finds a tie's winner
   by the slot's two clubs. The July teardown hands a native cup's rounds back, so the next draw
   builds them anew; a cup of the world file filled on its fill day (the CONCACAF Champions Cup,
   the OFC Champions League) and the Conference League's knockout keep last season's rounds, and
   register_all then writes this season's clubs into the match records only. r12, fourth season:
   reg 294's round of 16 was played by this season's clubs while its slots still held the last
   season's, the game found 2 of the 8 winners, and the quarter-final of 7 April with no club in
   it took the game down (0x141333485, day 96). So every slot whose first leg is still to be
   played is given the clubs of that match; a round not drawn yet gets the match's "no club". */
static int ko_sync(uint16_t reg, const char* why)
{
  int fixed = 0, rounds = 0;
  unsigned char* rec = get_rec(reg);
  if (!rec || !rec_count(rec) || *(const uint16_t*)(rec + 0x2fc) == 0xffff) return 0;   /* empty, or in no season */
  for (uint32_t kind = 0x20; kind < 0x40; kind++) {
    unsigned char* rnd = ko_round(reg, kind);
    int n = ko_slots(rnd);
    if (n < 1 || n > 16) continue;
    rounds++;
    for (int s = 0; s < n; s++) {
      uint32_t* sl = ko_slot(rnd, s);
      unsigned char* m = ko_match(*(uint16_t*)(sl + 2), reg);
      if (!m || (m[7] & 0x40)) continue;            /* no first leg, or played */
      uint32_t h = *(uint32_t*)(m + 0x14), a = *(uint32_t*)(m + 0x18);
      if (sl[0] == h && sl[1] == a) continue;
      if (fixed < 4)
        logf("fl26swiss:   reg %u round %#x tie %d: slot %08x v %08x, its first leg %08x v %08x", (unsigned)reg,
             (unsigned)kind, s, sl[0], sl[1], h, a);
      sl[0] = h; sl[1] = a;
      fixed++;
    }
  }
  if (fixed)
    logf("fl26swiss: reg %u -- %d knockout slot(s) of %d round(s) held another season's clubs; given their "
         "matches' clubs (%s, day %d)", (unsigned)reg, fixed, rounds, why, today());
  return fixed;
}

/* B217: the same stale slots in the game's own knockouts. johnnythief's Europack career, second
   season: Colombia's Apertura play-off (reg 160, Liga BetPlay DIMAYOR I Playoffs, May) had its
   quarter-final slots still on the 2026 clubs while the 2027 clubs played the matches; the game
   found 1 of the 4 winners, the semi-finals went on with no club and the second legs of 27 May
   took the game down (0x141333485, as B181). The Clausura play-off (reg 161, December) held the
   2026 clubs as well. So every knockout round of the round table (0x447ed20, 0x208 a record,
   below 0x1f40 as 0x141579ee0 reads it) is looked at, but more narrowly than ko_sync: only a
   slot whose two clubs and its unplayed first leg's two clubs are all real clubs and not the same
   pair (either way round) -- a round not drawn yet, a "winner of tie n" and the game's own home
   and away order are left alone -- and only in the record the game itself finds for that
   regulation and kind (fixfind), never a leftover. A real club has the top four bits clear: a
   slot of 0x4....... is the game's "n-th of that league" (a play-off's or a cup's entry: 4671 of
   the 8000 slots of a second season, reg 11 0x45ec0001...), which the first test took for a club
   and gave 154 slots of league play-offs (reg 112...) clubs of matches not theirs. And the first
   leg must be that round's own match (+4 regulation, +6 kind): a round of the season to come
   still names match ids the season since gave other competitions (reg 161 in May: 770e, a
   Libertadores match). */
#define RT_OFF  lay_rounds()              /* 0x447ed20 under the 0.3.0 set */
#define RT_REC  0x208
#define RT_N    lay_fixcap()              /* 8000 under the 0.3.0 set, --fixture-cap raises it */
/* 07.11. (Megapack, mp18/mp19): a club's handle is its team id << 14 | its row, so a team id of 16384
   or more -- every new club of a big world, 0x4793c990 is id 73295 -- sets the top four bits too.
   The test above took those for "n-th of that league" and left their ties alone: five of the eight
   Europa League play-off ties of a second season kept last season's clubs in their slots, the game
   put no winner through and the round of 16's second leg (home ffffffff) crashed it (0x141333485).
   A club is now a handle its own row of the team table answers for. */
static int real_club(uint32_t v)
{
  uint32_t n;
  if ((v & KO_TBD) == KO_TBD || !(v >> 14)) return 0;
  unsigned char* ta = team_array(&n);
  return ta && (v & 0x3fff) < n && team_at(ta, v & 0x3fff) == v;
}
static int ko_sync_all(const char* why)
{
  unsigned char* o = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
  unsigned char* blk = o ? *(unsigned char**)(o + 0x48) : 0;
  if (!blk) return 0;
  int fixed = 0;
  for (uint32_t i = 0; i < RT_N; i++) {
    unsigned char* rnd = blk + RT_OFF + (size_t)i * RT_REC;
    uint16_t reg = *(uint16_t*)rnd;
    uint32_t kind = *(uint32_t*)(rnd + 0x204) >> 26;
    int n = ko_slots(rnd);
    if (reg == 0 || reg == 0xffff || kind < 0x20 || n < 1 || n > 16) continue;
    int here = 0;
    for (int s = 0; s < n; s++) {
      uint32_t* sl = ko_slot(rnd, s);
      if (!real_club(sl[0]) || !real_club(sl[1])) continue;
      unsigned char* m = ko_match(*(uint16_t*)(sl + 2), reg);
      if (!m || (m[7] & 0x40)) continue;            /* no first leg, or played */
      if (*(uint16_t*)(m + 4) != reg || m[6] != kind) continue;   /* another competition's match */
      uint32_t h = *(uint32_t*)(m + 0x14), a = *(uint32_t*)(m + 0x18);
      if (!real_club(h) || !real_club(a)) continue;
      if ((same_club(sl[0], h) && same_club(sl[1], a)) || (same_club(sl[0], a) && same_club(sl[1], h))) continue;
      if (!here && ko_round(reg, kind) != rnd) break;   /* not the round the game uses */
      here = 1;
      if (fixed < 8)
        logf("fl26swiss:   reg %u round %#x tie %d: slot %08x v %08x, its first leg %08x v %08x", (unsigned)reg,
             (unsigned)kind, s, sl[0], sl[1], h, a);
      sl[0] = h; sl[1] = a;
      fixed++;
    }
  }
  if (fixed)
    logf("fl26swiss: %d knockout slot(s) of the game's competitions held another season's clubs; given "
         "their matches' clubs (%s, day %d)", fixed, why, today());
  return fixed;
}

/* B312: a career already past a fill of ours (B308: pepponeee98's save, stopped on 7 August with
   the second qualifying round filled) keeps the stale value in its match records. Every match
   record not played yet whose home or away value names a row that holds another club, where
   exactly one row holds that club at its own place (canon_club), is given that row -- and so are
   the slots of the rounds that name the match, and its regulation's list (and the master's, for a
   tie at master + 1024 * (k + 1)), where they hold the same stale value. A value that already
   names its row, "no club" and a value no row answers for are left alone. */
static int rows_heal(const char* why)
{
  const unsigned char* bs = (const unsigned char*)(g_base + MATCH_BASE_SITE);
  const unsigned char* cs = (const unsigned char*)(g_base + MATCH_CAP_SITE);
  if (bs[0] != 0x48 || bs[1] != 0x8d || bs[2] != 0x88 || cs[0] != 0x81 || cs[1] != 0xff) return 0;
  uint32_t base = *(const uint32_t*)(bs + 3), cap = *(const uint32_t*)(cs + 2);
  unsigned char* o = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
  unsigned char* blk = o ? *(unsigned char**)(o + 0x48) : 0;
  uint32_t nteams;
  if (!blk || !cap || cap > 200000 || !team_array(&nteams)) return 0;
  int fixed = 0, slots = 0, lists = 0;
  for (uint32_t i = 0; i < cap; i++) {
    unsigned char* m = blk + base + (size_t)i * MATCH_STRIDE;
    uint16_t id = *(const uint16_t*)m;
    if (id == 0xffff || (m[7] & 0x40)) continue;
    for (int side = 0; side < 2; side++) {
      uint32_t* v = (uint32_t*)(m + 0x14 + 4 * side);
      if (*v == 0xffffffffu || !(*v >> 14)) continue;
      uint32_t old = *v, c = canon_club(old);
      if (c == old) continue;
      uint16_t reg = *(const uint16_t*)(m + 4);
      char buf[48];
      if (fixed < 8)
        logf("fl26swiss:   match %04x reg %u %04u-%02u-%02u %s: %08x -> %08x (%s)", (unsigned)id, (unsigned)reg,
             (unsigned)*(const uint16_t*)(m + 8), (unsigned)m[10], (unsigned)m[11], side ? "away" : "home",
             old, c, club_note(old, buf, sizeof buf));
      *v = c; fixed++;
      for (uint32_t r = 0; r < RT_N; r++) {
        unsigned char* rnd = blk + RT_OFF + (size_t)r * RT_REC;
        int n = ko_slots(rnd);
        if (*(uint16_t*)rnd != reg || n < 1 || n > 16) continue;
        for (int k = 0; k < n; k++) {
          uint32_t* sl = ko_slot(rnd, k);
          if ((sl[2] & 0xffff) != id && (sl[3] & 0xffff) != id) continue;
          for (int j = 0; j < 2; j++) if (sl[j] == old) { sl[j] = c; slots++; }
        }
      }
      uint16_t regs[2] = { reg, (uint16_t)(reg >= 1024 ? reg % 1024 : 0) };
      for (int j = 0; j < 2; j++) {
        unsigned char* rec = regs[j] ? get_rec(regs[j]) : 0;
        unsigned n = rec ? rec_count(rec) : 0;
        if (n > 48) n = 48;
        for (unsigned k = 0; k < n; k++) if (rec_clubs(rec)[k] == old) { rec_clubs(rec)[k] = c; lists++; }
      }
    }
  }
  if (fixed)
    logf("fl26swiss: %d club value(s) of unplayed matches named a row holding another club; given their "
         "club's row, with %d round slot(s) and %d list entr(ies) (%s, day %d)", fixed, slots, lists, why, today());
  return fixed;
}

/* B187: ko_sync_all mends a round before it is played; a career of 0.2.4 may have played it
   already. Ibiss K.B.'s Europack Become a Legend career, 19 May 2029: reg 160's quarter-finals
   (13/16 May) were played by the 2029 clubs while their slots held older ones, the game found 1
   of the 4 winners, and the semi-finals of 23/27 May stood with no club (0xffffffff) -- the
   game went down past Skip Match (0x141333485, FL26 2.2). So a played tie whose slot is not its
   first leg's pair (both real clubs, the round's own match, the round the game uses) gets the
   leg's clubs, its winner is worked out from the legs (goals +0x1c/+0x1f, extra time
   +0x1d/+0x20, penalties +0x1e/+0x21; level after penalties too = away goals, else left alone)
   and written where the next tie (slot +0x10: reg | kind << 16 | tie << 22, which names its two
   sources at +0x18/+0x1c) still has no club: its slot and its unplayed legs. */
static int ko_goals(const unsigned char* m, int side) { return m[0x1c + 3 * side] + m[0x1d + 3 * side]; }
static int ko_winner(const uint32_t* sl, uint32_t* w, uint16_t reg)
{
  const uint16_t* ids = (const uint16_t*)(sl + 2);
  unsigned char* m1 = ko_match(ids[0], reg);
  if (!m1 || !(m1[7] & 0x40)) return 0;
  uint32_t h = *(uint32_t*)(m1 + 0x14), a = *(uint32_t*)(m1 + 0x18);
  int gh = ko_goals(m1, 0), ga = ko_goals(m1, 1), ph = m1[0x1e], pa = m1[0x21], awh = 0, awa = ga;
  if (ids[1] != 0xffff) {
    unsigned char* m2 = ko_match(ids[1], reg);
    if (!m2 || !(m2[7] & 0x40)) return 0;           /* second leg still to come */
    if (!same_club(*(uint32_t*)(m2 + 0x14), a) || !same_club(*(uint32_t*)(m2 + 0x18), h)) return 0;
    gh += ko_goals(m2, 1); ga += ko_goals(m2, 0);
    awh = ko_goals(m2, 1);
    ph = m2[0x21]; pa = m2[0x1e];
  }
  if (gh == ga) { gh = ph; ga = pa; }
  if (gh == ga && ids[1] != 0xffff) { gh = awh; ga = awa; }
  if (gh == ga) return 0;
  *w = gh > ga ? h : a;
  return 1;
}
/* B236: a cup of ours goes by its played final -- the two clubs its match was played between and
   its score -- before the game's rights code, which named the club the holder knocked out in the
   semi-final as the CAF Champions League's winner, and the CAF Super Cup was played without the
   holder (mohamed-248, GitHub #150, 2026-10-25). The final is the cup's last round of one tie
   (0x36, else 0x35); 0 while it is not played. */
static uint32_t ko_final_winner(uint16_t reg)
{
  static const uint32_t kinds[2] = { 0x36, 0x35 };
  for (int i = 0; i < 2; i++) {
    unsigned char* rnd = ko_round(reg, kinds[i]);
    uint32_t w = 0;
    if (!rnd || *(uint16_t*)rnd != reg || ko_slots(rnd) != 1) continue;
    return ko_winner(ko_slot(rnd, 0), &w, reg) && (w >> 14) ? canon_club(w) : 0;
  }
  return 0;
}
/* the winner a cup's <reg>:0 entry is sent: a cup of ours (176 and up) by its final, the game's
   cups and a final not found by the rights code */
static uint32_t ccup_ko_winner(uint16_t reg)
{
  uint32_t r = winner_now(reg), f = reg > 175 ? ko_final_winner(reg) : 0;
  if (!f) return r;
  if (!r || !same_club(f, r))
    logf("fl26swiss: cup reg %u -- its final was won by %08x, the rights code names %08x: the final's winner goes",
         (unsigned)reg, f, r);
  return f;
}
static int ko_put(unsigned char* m, int side, uint32_t w)
{
  uint32_t* f = (uint32_t*)(m + 0x14 + 4 * side);
  if (*f != 0xffffffffu) return 0;
  *f = w;
  return 1;
}
static int ko_heal_played(const char* why)
{
  unsigned char* o = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
  unsigned char* blk = o ? *(unsigned char**)(o + 0x48) : 0;
  if (!blk) return 0;
  int healed = 0;
  for (uint32_t i = 0; i < RT_N; i++) {
    unsigned char* rnd = blk + RT_OFF + (size_t)i * RT_REC;
    uint16_t reg = *(uint16_t*)rnd;
    uint32_t kind = *(uint32_t*)(rnd + 0x204) >> 26;
    int n = ko_slots(rnd);
    if (reg == 0 || reg == 0xffff || kind < 0x20 || n < 1 || n > 16) continue;
    int here = 0;
    for (int s = 0; s < n; s++) {
      uint32_t* sl = ko_slot(rnd, s);
      if (!real_club(sl[0]) || !real_club(sl[1])) continue;
      unsigned char* m = ko_match(*(uint16_t*)(sl + 2), reg);
      if (!m || !(m[7] & 0x40)) continue;           /* not played: ko_sync_all's */
      if (*(uint16_t*)(m + 4) != reg || m[6] != kind) continue;
      uint32_t h = *(uint32_t*)(m + 0x14), a = *(uint32_t*)(m + 0x18);
      if (!real_club(h) || !real_club(a)) continue;
      if ((same_club(sl[0], h) && same_club(sl[1], a)) || (same_club(sl[0], a) && same_club(sl[1], h))) continue;
      if (!here && ko_round(reg, kind) != rnd) break;
      here = 1;
      uint32_t w;
      if (!ko_winner(sl, &w, reg)) continue;
      uint32_t next = sl[4];
      if ((next & 0xffff) != reg) continue;          /* a final: nothing comes after it */
      unsigned char* rnd2 = ko_round(reg, (next >> 16) & 0x3f);
      int t = (int)(next >> 22);
      if (t >= ko_slots(rnd2)) continue;
      uint32_t* ns = ko_slot(rnd2, t);
      int side = ns[6] == sl[3] ? 0 : ns[7] == sl[3] ? 1 : -1;
      if (side < 0) continue;
      uint16_t* nid = (uint16_t*)(ns + 2);
      unsigned char* n1 = ko_match(nid[0], reg);
      unsigned char* n2 = ko_match(nid[1], reg);
      if (!n1 || (n1[7] & 0x40) || *(uint16_t*)(n1 + 4) != reg) continue;   /* the next tie is under way */
      uint32_t f = *(uint32_t*)(n1 + 0x14 + 4 * side);
      if (f != 0xffffffffu && !same_club(f, w)) continue;   /* someone is there already */
      int put = ko_put(n1, side, w);
      if (n2 && !(n2[7] & 0x40)) put += ko_put(n2, 1 - side, w);
      logf("fl26swiss:   reg %u round %#x tie %d (played): slot %08x v %08x, its first leg %08x v %08x; "
           "winner %08x to round %#x tie %d (%s, %d leg(s) given it)", (unsigned)reg, (unsigned)kind, s,
           sl[0], sl[1], h, a, w, (unsigned)((next >> 16) & 0x3f), t, side ? "away" : "home", put);
      sl[0] = h; sl[1] = a;
      ns[side] = w;
      healed++;
    }
  }
  if (healed) {
    logf("fl26swiss: %d played knockout tie(s) had another season's clubs in their slot; winners put "
         "through (%s, day %d)", healed, why, today());
    sched_rebuild("played knockout healed");
  }
  return healed;
}

/* ---- a country cup's draw: seeds meet unseeded clubs ----
 *
 * The game fills a cup's bracket strictly in the order of its entry list, top to bottom, and the
 * list runs from the top division down: in a 24-club cup of 10 + 14 clubs every group of three
 * (the club let through to the second round, then the two of a first-round tie) took the next
 * three clubs of the list, so the whole top division sat in one half and the other half was the
 * second division alone (in game, 07.10.: "the left side of the cup draw is far too strong").
 *
 * A cup's rounds are its fixture records (fixfind, one per kind); measured on the HNL cup the same
 * day, a 24-club cup is a first round of 8 ties (both clubs known), a second round of 8 whose home
 * side is a club let through and whose away side is a winner of the first round (0x3fffff until
 * then), then the quarter-finals. Once the game has made them and before a ball is kicked, this
 * hands the known places out again: the strongest clubs get the places furthest on (the ones let
 * through), and every tie of two known clubs is one of the next best against one of the rest, the
 * weaker club at home, both picked at random. Strength is the division first (the world's leagues
 * of the cup, top down), then the squad (club_strength). Mode 2 draws every place at random; 0
 * leaves the game's order. A slot's two clubs and its match records (+0x14 home, +0x18 away, the
 * second leg the other way round) are all that is written, as ko_bracket does. */
#define CD_MAX     512                /* cups (32 until the limits branch: 50 with 80 leagues) */
#define CD_TIERS   6
#define CD_CLUBS   128
typedef struct { uint16_t reg, mode, ntier, tier[CD_TIERS]; uint32_t kmask, done_key; } cupdraw_t;
static cupdraw_t g_cd[CD_MAX];
static int g_ncd;

/* the world's cups: n entries of reg, mode (0 off, 1 seeded, 2 random, 3 byes: the places let through
   to the top division, every tie at random -- a single-match league cup), k, then k league regs, the
   top division first; returns how many were taken */
__declspec(dllexport) int fl26_swiss_cupdraw(const uint16_t* v, int n)
{
  g_ncd = 0;
  g_ccup_gen++;
  for (int i = 0, q = 0; i < n && g_ncd < CD_MAX; i++) {
    cupdraw_t* c = &g_cd[g_ncd];
    c->reg = v[q]; c->mode = v[q + 1]; c->ntier = v[q + 2]; q += 3;
    for (int k = 0; k < c->ntier; k++, q++) if (k < CD_TIERS) c->tier[k] = v[q];
    if (c->ntier > CD_TIERS) c->ntier = CD_TIERS;
    c->kmask = 0; c->done_key = 0;
    if (c->reg && c->mode) g_ncd++;
  }
  logf("fl26swiss: %d country cup draw(s) taken", g_ncd);
  return g_ncd;
}

static uint32_t cd_rng;
static uint32_t cd_rand(uint32_t n)
{
  cd_rng ^= cd_rng << 13; cd_rng ^= cd_rng >> 17; cd_rng ^= cd_rng << 5;
  return n ? cd_rng % n : 0;
}
static void cd_shuffle(uint32_t* a, int n)
{
  for (int i = n - 1; i > 0; i--) { int j = (int)cd_rand((uint32_t)i + 1); uint32_t t = a[i]; a[i] = a[j]; a[j] = t; }
}

typedef struct { uint32_t* sl; uint16_t legs[2]; int round, both, side, slot, nslots; } cd_place_t;

/* the slot's place in the bracket, read from the final down: bit-reversed, so slots taken in this
   order alternate halves, then quarters ... (0 4 2 6 1 5 3 7 of eight) */
static int cd_bitrev(int s, int n)
{
  int bits = 0, r = 0;
  while ((1 << bits) < n) bits++;
  for (int i = 0; i < bits; i++) if (s >> i & 1) r |= 1 << (bits - 1 - i);
  return r;
}

/* hand clubs[0..n) (the strongest first) to the places idx[0..n) so the strongest are spread over
   the halves and quarters of the bracket: the places in bit-reversed slot order (after a random
   flip of the slot bits, so it is not always the same corner), the clubs shuffled only among
   clubs of the same division. In a 24-club cup the two top-division clubs left for the first
   round went to the same half when the clubs were simply shuffled (in game, 07.10.). */
static void cd_deal(const cd_place_t* pl, const int* idx, int n, uint32_t* clubs, const int* tiers, uint32_t* want)
{
  int ord[CD_CLUBS], ns = n ? pl[idx[0]].nslots : 1, bits = 0;
  while ((1 << bits) < ns) bits++;
  int flip = (int)cd_rand(1u << bits);
  for (int i = 0; i < n; i++) ord[i] = idx[i];
  for (int i = 1; i < n; i++)
    for (int j = i; j > 0 && cd_bitrev(pl[ord[j - 1]].slot ^ flip, ns) > cd_bitrev(pl[ord[j]].slot ^ flip, ns); j--) {
      int t = ord[j]; ord[j] = ord[j - 1]; ord[j - 1] = t;
    }
  for (int a = 0; a < n;) {
    int b = a;
    while (b < n && tiers[b] == tiers[a]) b++;
    cd_shuffle(clubs + a, b - a);
    a = b;
  }
  for (int i = 0; i < n; i++) want[ord[i]] = clubs[i];
}

/* B280 (Agus 2026-10-29): a match record's own date, year * 365 + day as game_date(), or -1 */
static int game_date(void);
static int ko_mdate(const unsigned char* m)
{
  int y = *(const uint16_t*)(m + 8), mo = m[10], dd = m[11];
  if (y < 1990 || y > 2200 || mo < 1 || mo > 12 || dd < 1 || dd > 31) return -1;
  return y * 365 + MONTH0[mo - 1] + dd - 1;
}

/* 1 = drawn now, 0 = nothing to do (not made yet, or under way), -1 = done for the season */
static int cup_draw(cupdraw_t* c)
{
  unsigned char* rounds[16]; int kinds[16], nr = 0;
  for (int pass = c->kmask ? 0 : 1; pass < 2 && !nr; pass++) {   /* the kinds found before, else all */
    uint32_t mask = pass ? 0xffffffffu : c->kmask, found = 0;
    for (uint32_t kind = 0x20; kind < 0x40 && nr < 16; kind++) {
      if (!(mask >> (kind - 0x20) & 1)) continue;
      unsigned char* r = ko_round(c->reg, kind);
      if (!r || *(uint16_t*)r != c->reg || ko_slots(r) < 1 || ko_slots(r) > 16) continue;
      int dup = 0;
      for (int i = 0; i < nr; i++) dup |= rounds[i] == r;
      if (!dup) { rounds[nr] = r; kinds[nr] = (int)kind; nr++; found |= 1u << (kind - 0x20); }
    }
    if (pass == 0 && found != c->kmask) nr = 0;  /* the cup changed shape: look at every kind */
    if (nr) c->kmask = found;
  }
  if (!nr) return 0;
  /* this season's cup: its first round's first match; once handled it is left alone */
  uint32_t ckey = ((uint32_t)*(uint16_t*)(ko_slot(rounds[0], 0) + 2) << 16) ^ (uint32_t)(uintptr_t)rounds[0];
  if (ckey == c->done_key) return 0;
  cd_place_t pl[CD_CLUBS]; int np = 0;
  uint32_t club[CD_CLUBS]; int nc = 0;
  int gd = game_date();
  uint32_t user = 0;
  {
    unsigned char* uo = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
    void* ub = uo ? *(void**)(uo + 0x48) : 0;
    user = ub ? user_club(ub) : 0;
    if (user == 0xffffffffu) user = 0;
  }
  for (int i = 0; i < nr; i++)
    for (int s = 0; s < ko_slots(rounds[i]); s++) {
      uint32_t* sl = ko_slot(rounds[i], s);
      int k0 = (sl[0] & KO_TBD) != KO_TBD, k1 = (sl[1] & KO_TBD) != KO_TBD;
      if (!k0 && !k1) continue;
      uint16_t* ids = (uint16_t*)(sl + 2);
      for (int l = 0; l < 2; l++) {               /* a tie already played: the cup is under way */
        if (ids[l] == 0xffff) continue;
        unsigned char* m = ko_match(ids[l], c->reg);
        if (m && (m[7] & 0x40)) {                 /* a save of before 0.2.5 kept the old days */
          c->done_key = ckey; sched_rebuild("cup under way"); return -1;
        }
        /* B280: a tie of a day gone by is not drawn again, nor one of today with the user's club
           in it. The draw runs on file opens, so a save loaded on the day of the first round and
           played at once is drawn while its match loads, or right after it, before the game marks
           it played: Agus's Copa Argentina (278, 44 clubs) was "drawn ... 44 club(s) moved" after
           his first match of it and the game closed. A cup the game makes on its first round's
           day (266 in D1eg0Ar's world) is still drawn when the user is not in that day's ties. */
        int md = m && gd >= 0 ? ko_mdate(m) : -1;
        int mine = user && ((sl[0] & KO_TBD) == (user & KO_TBD) || (sl[1] & KO_TBD) == (user & KO_TBD));
        if (md >= 0 && (md < gd || (md == gd && mine))) {
          c->done_key = ckey;
          logf("fl26swiss: cup %d not drawn: a first match is on day %d of %d, today is day %d%s (B280)",
               c->reg, md % 365, md / 365, gd % 365, md == gd ? " and the user's club plays it" : "");
          if (md < gd) sched_rebuild("cup's first day gone by");   /* as for a cup under way */
          return -1;
        }
      }
      for (int side = 0; side < 2; side++) {
        if (!(side ? k1 : k0) || np >= CD_CLUBS) continue;
        pl[np].sl = sl; pl[np].legs[0] = ids[0]; pl[np].legs[1] = ids[1];
        pl[np].round = i; pl[np].both = k0 && k1; pl[np].side = side;
        pl[np].slot = s; pl[np].nslots = ko_slots(rounds[i]); np++;
        club[nc++] = sl[side];
      }
    }
  if (nc < 4) return 0;
  /* the order of strength: division, then squad */
  unsigned char* o = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
  void* blk = o ? *(void**)(o + 0x48) : 0;
  int key[CD_CLUBS], tier[CD_CLUBS], ntiers_seen = 0, seen[CD_TIERS + 1] = { 0 };
  for (int k = 0; k < nc; k++) {
    int t = c->ntier;
    for (int i = 0; i < c->ntier; i++) if (in_league(c->tier[i], club[k])) { t = i; break; }
    tier[k] = t;
    if (!seen[t]++) ntiers_seen++;
    key[k] = t * 100000 - (blk && c->mode != 3 ? club_strength(blk, club[k]) : 0);   /* 3: the division alone */
  }
  /* already drawn by us (a season loaded again): every place let through holds a club of a
     division no lower than any first-round club's, and in every tie the home club's division is
     no higher than the away club's. Only worth asking when the cup mixes divisions. */
  if ((c->mode == 1 || c->mode == 3) && ntiers_seen > 1) {
    int ok = 1, worst_single = -1, best_pair = 1 << 30;
    for (int k = 0; k < np; k++) {
      if (pl[k].both) { if (tier[k] < best_pair) best_pair = tier[k]; }
      else if (tier[k] > worst_single) worst_single = tier[k];
      if (pl[k].both && pl[k].side == 0 && k + 1 < np && pl[k + 1].sl == pl[k].sl && tier[k] < tier[k + 1]) ok = 0;
    }
    int max_away = -1, min_home = 1 << 30;
    for (int k = 0; k < np; k++) if (pl[k].both) {
      if (pl[k].side) { if (tier[k] > max_away) max_away = tier[k]; }
      else if (tier[k] < min_home) min_home = tier[k];
    }
    if (worst_single > best_pair || max_away > min_home) ok = 0;
    /* a season loaded again: its day schedule may still be the one saved before 0.2.5 */
    if (ok) { c->done_key = ckey; sched_rebuild("cup already drawn"); return -1; }
  }
  /* the same draw every time for the same cup and season */
  cd_rng = 0x9e3779b9u ^ ((uint32_t)c->reg << 16) ^ (uint32_t)pl[0].legs[0] * 2654435761u ^ (uint32_t)((abs_day() + 183) / 365);
  if (!cd_rng) cd_rng = 1;
  uint32_t order[CD_CLUBS]; int ord_key[CD_CLUBS], ord_tier[CD_CLUBS];
  for (int k = 0; k < nc; k++) { order[k] = club[k]; ord_key[k] = key[k]; ord_tier[k] = tier[k]; }
  for (int k = 1; k < nc; k++)                    /* stable: the strongest first */
    for (int j = k; j > 0 && ord_key[j - 1] > ord_key[j]; j--) {
      int t = ord_key[j]; ord_key[j] = ord_key[j - 1]; ord_key[j - 1] = t;
      t = ord_tier[j]; ord_tier[j] = ord_tier[j - 1]; ord_tier[j - 1] = t;
      uint32_t u = order[j]; order[j] = order[j - 1]; order[j - 1] = u;
    }
  if (c->mode == 3)                               /* byes: a division's clubs in random order */
    for (int a = 0; a < nc;) {
      int b = a;
      while (b < nc && ord_tier[b] == ord_tier[a]) b++;
      cd_shuffle(order + a, b - a);
      a = b;
    }
  uint32_t want[CD_CLUBS];
  if (c->mode == 2) {
    cd_shuffle(order, nc);
    for (int k = 0; k < np; k++) want[k] = order[k];
  } else {
    int next = 0;
    for (int r = nr - 1; r >= 0; r--) {
      /* places let through in this round: the next best clubs, spread over the bracket */
      int idx[CD_CLUBS], n1 = 0;
      for (int k = 0; k < np; k++) if (pl[k].round == r && !pl[k].both) idx[n1++] = k;
      if (n1) {
        cd_deal(pl, idx, n1, order + next, ord_tier + next, want);
        next += n1;
      }
      /* ties of two known clubs: one of the next best (away) against one of the rest (home) */
      int home[CD_CLUBS], away[CD_CLUBS], nt = 0;
      for (int k = 0; k < np; k++)
        if (pl[k].round == r && pl[k].both && pl[k].side == 0 && k + 1 < np && pl[k + 1].sl == pl[k].sl) {
          home[nt] = k; away[nt] = k + 1; nt++;
        }
      if (nt) {
        cd_deal(pl, away, nt, order + next, ord_tier + next, want);
        cd_deal(pl, home, nt, order + next + nt, ord_tier + next + nt, want);
        next += 2 * nt;
      }
    }
    if (next != np) { c->done_key = ckey; return -1; }   /* a shape this does not know: leave it */
  }
  int moved = 0;
  for (int k = 0; k < np; k++) if ((want[k] & KO_TBD) != (club[k] & KO_TBD)) moved++;
  for (int k = 0; k < np; k++) {
    uint32_t* sl = pl[k].sl;
    sl[pl[k].side] = want[k];
    unsigned char* m1 = ko_match(pl[k].legs[0], c->reg);
    unsigned char* m2 = ko_match(pl[k].legs[1], c->reg);
    if (m1) *(uint32_t*)(m1 + (pl[k].side ? 0x18 : 0x14)) = want[k];
    if (m2) *(uint32_t*)(m2 + (pl[k].side ? 0x14 : 0x18)) = want[k];
  }
  /* the bracket screen (Competition Info -> the cup -> Fixtures) does not read the rounds: it lays
     the entry list out again, in the order the game drew from it, so it still showed the old draw
     over the new matches (in game, 07.10.). Each club of the list takes the place its old holder
     had: the club that went to the place of list entry p is written at p. */
  unsigned char* rec = get_rec(c->reg);
  int relisted = 0;
  if (rec) {
    /* the list holds rec_count clubs and ends at +0x308, 102 places in: a walk to CD_CLUBS or a
       0xffffffff ran into the count word of a full list (same class as fl26clubs, 22.09.) */
    uint32_t* lst = rec_clubs(rec);
    int nl = (int)rec_count(rec);
    if (nl > (0x308 - 0x170) / 4) nl = (0x308 - 0x170) / 4;
    for (int p = 0; p < nl && lst[p] != 0xffffffffu; p++)
      for (int k = 0; k < np; k++)
        if (club[k] == lst[p]) { if (lst[p] != want[k]) relisted++; lst[p] = want[k]; break; }
  }
  logf("fl26swiss: cup %d drawn %s: %d place(s) in %d round(s), %d club(s) moved, %d division(s), %d entry list place(s) rewritten; day %d",
       c->reg, c->mode == 2 ? "at random" : c->mode == 3 ? "at random, the byes to the top division" : "with seeds", np, nr, moved, ntiers_seen, relisted, today());
  for (int k = 0; k < np; k++) {
    if (!pl[k].both)
      logf("fl26swiss:   cup %d round %#x slot: %06x through", c->reg, kinds[pl[k].round], want[k] & KO_TBD);
    else if (pl[k].side == 0 && k + 1 < np)
      logf("fl26swiss:   cup %d round %#x tie: %06x v %06x", c->reg, kinds[pl[k].round], want[k] & KO_TBD,
           want[k + 1] & KO_TBD);
  }
  sched_rebuild("cup draw");
  c->done_key = ckey;
  return 1;
}

static void cupdraw_tick(void)
{
  static ULONGLONG last;
  if (!g_ncd) return;
  ULONGLONG now = GetTickCount64();
  if (now - last < 3000) return;                  /* fixfind walks the table: not on every file open */
  last = now;
  for (int i = 0; i < g_ncd; i++)
    if (get_rec(g_cd[i].reg)) cup_draw(&g_cd[i]);
}

/* ---- the user's national team on the user's controller (B20) ----
 *
 * A manager who takes a national job runs that team too: block+0x1798ab4 holds its handle (-1
 * when there is none) and the game puts it at controller 0, so its friendlies and qualifiers go
 * into the user's day schedule and the hub stops for them. Up to 0.2.5 fl26ctlguard handed every
 * team at 0 except the club back to the computer, the national team included, every day: the
 * hub skipped the internationals (Vicentico, Spain, 2/9 and 5/9 2026 never offered) and a save
 * made since keeps the national team at 0xff. fl26ctlguard now leaves it alone; this gives such a
 * save its national team back, once, in a Master League career only (the user's club exists and
 * is itself at 0, as fl26ctlguard checks), and asks for the day schedule again. */
#define USER_NT_OFF (lay_user() + 4)     /* 0x1798ab4: the word after the user club */
#define CTL_OFF     0x41d
static void nt_keep_user(void)
{
  uint32_t n;
  unsigned char* a = team_array(&n);
  unsigned char* o = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
  unsigned char* blk = o ? *(unsigned char**)(o + 0x48) : 0;
  if (!a || !blk) return;
  uint32_t user = *(const uint32_t*)(blk + USER_CLUB_OFF), nt = *(const uint32_t*)(blk + USER_NT_OFF);
  if (!(user >> 14) || user == 0xffffffffu || !(nt >> 14) || nt == 0xffffffffu || nt == user) return;
  uint32_t ur = user & 0x3fff, nr = nt & 0x3fff;
  if (ur >= n || nr >= n || team_at(a, ur) != user || team_at(a, nr) != nt) return;
  if (a[(size_t)ur * TEAM_STRIDE + CTL_OFF] != 0) return;
  unsigned char* ctl = a + (size_t)nr * TEAM_STRIDE + CTL_OFF;
  if (*ctl != 0xff) return;
  *ctl = 0;
  logf("fl26swiss: the user's national team %08x (%s) was at the computer's controller; back on the user's (B20), day %d",
       nt, (const char*)(a + (size_t)nr * TEAM_STRIDE + 4), today());
  sched_rebuild("the user's national team back on the user's controller");
}

/* called by the loader every few dozen file opens; cheap outside spring */
__declspec(dllexport) void fl26_swiss_ko_tick(void)
{
  if (!g_base) return;
  int d = today();
  abs_day();                      /* the loader calls this all year: it keeps abs_day() across New Year */
  lpre_fill_days();
  ccup_fill_days();
  cupdraw_tick();
  {
    static ULONGLONG last;                        /* fixfind walks the table: every few seconds */
    ULONGLONG now = GetTickCount64();
    if (now - last >= 3000) {
      last = now;
      for (int k = 0; k < g_nccup; k++)
        if (g_ccup[k].ko) ko_sync(g_ccup[k].ko, "day loop");
      ko_sync(UECL_KO, "day loop");
      ko_heal_played("day loop");
      rows_heal("day loop");
      ko_sync_all("day loop");
      nt_keep_user();
      for (int i = 0; i < 3; i++) if (cup_on(i)) lb_keep(&CUPS[i], d);
    }
  }
  if (d < 60 || d > 150) return;
  static const uint16_t KO_REGS[3] = { 4, 6, UECL_KO };
  static const char* KO_NAME[3] = { "Champions League", "Europa League", "Conference League" };
  static unsigned char loaded[3][2];             /* once a session: a save of before 0.2.5 */
  for (int i = 0; i < 3; i++) {
    if (!cup_on(i) || !get_rec(KO_REGS[i])) continue;
    for (int k = 0; k < 2; k++)
      if (ko_bracket(KO_REGS[i], 0x33 + k, KO_NAME[i]) == 0 && !loaded[i][k]) {
        loaded[i][k] = 1;
        sched_rebuild("European bracket already in order");
      }
  }
}

/* The access list from the loader: n entries of four u16 -- regulation, position (0 = the winner
   of a cup), competition (0 Champions League, 1 Europa League, 2 Conference League, 3 Libertadores,
   4 Libertadores qualifying, 5 AFC Champions League, 10 / 11 / 12 the Champions League /
   Europa League / Conference League play-off in August), and for a
   cup the league whose next free position takes the place when the winner is already in.
   Replaces the compiled list; answers how many entries were taken, or -1 when none were. */
__declspec(dllexport) int fl26_swiss_access(const uint16_t* v, int n)
{
  int k = 0;
  g_ccup_gen++;
  for (int i = 0; v && i < n && k < ACCESS_MAX; i++) {
    const uint16_t* e = v + 4 * i;
    if (!e[0] || (e[2] > AFCL && (e[2] < UCLQ || e[2] > UECLQ)) || e[1] > FINAL_MAX) continue;
    g_access_buf[k].reg = e[0]; g_access_buf[k].rank = (uint8_t)e[1];
    g_access_buf[k].comp = (uint8_t)e[2]; g_access_buf[k].alt = e[3];
    k++;
  }
  if (!k) return -1;
  g_access = g_access_buf; g_naccess = (size_t)k; g_access_cfg = 1;
  return k;
}

/* The qualifying rounds from the loader (the world file's qround lines): n entries of three u16 --
   competition (10, 11, 12: the Champions League's, Europa League's, Conference League's), round
   (3 the third qualifying round, 2 the second) and its regulation, a copy of reg 2 with its eight
   ties at id + 1024 * (k + 1). Answers how many were taken. */
static void po_fill(void);          /* the Match Results play-off ids, below */
__declspec(dllexport) int fl26_swiss_qrounds(const uint16_t* v, int n)
{
  memset(g_qreg, 0, sizeof g_qreg);
  int k = 0, q1 = 0, pc = 0;
  for (int i = 0; v && i < n; i++) {
    const uint16_t* e = v + 3 * i;
    if (e[0] < UCLQ || e[0] > UECLQ || e[1] > 3 || e[2] < 2 || e[2] > 0x3ff) continue;
    /* round 0, Prijedlog C's August play-off of 32 (the Europa League's, the Conference League's):
       FL27 only, never the Champions League's (reg 2) nor 188 / 189 (February's) */
    if (!e[1]) {
      if (g_native_uefa && e[0] != UCLQ && e[2] != UEL_PO && e[2] != UECL_PO) { g_qreg[e[0] - UCLQ] = e[2]; pc++; }
      continue;
    }
    /* round 1, the first qualifying round in July: FL27 only (the lua installs before this) */
    if (e[1] == 1 && !g_native_uefa) { q1++; continue; }
    g_qreg[(e[0] - UCLQ) + NQ * (e[1] == 3 ? 1 : e[1] == 2 ? 2 : 3)] = e[2];
    k++;
  }
  if (q1) logf("fl26swiss: %d first qualifying round(s) in the world file left out: they are FL27's", q1);
  if (pc && !(g_qreg[1] && g_qreg[2])) {          /* Prijedlog C takes both or neither */
    logf("fl26swiss: a play-off of 32 in the world file for one competition only; left out (188 / 189 play the play-offs)");
    g_qreg[1] = g_qreg[2] = 0;
  } else if (pc) {
    k += pc;
    logf("fl26swiss: Prijedlog C -- the Europa League's and the Conference League's August play-offs of 32 are regs %u and %u",
         (unsigned)g_qreg[1], (unsigned)g_qreg[2]);
  }
  g_qr_sy = -1;                            /* the days of the rounds named (qr_plan) */
  po_fill();
  return k;
}

/* The first-season list from the loader: n pairs of u32 -- competition (0 Champions League,
   1 Europa League, 2 Conference League, 3 AFC Champions League) and team id, in the order they
   are to be placed.
   Answers how many were taken. */
__declspec(dllexport) int fl26_swiss_first(const uint32_t* v, int n)
{
  g_nfirst[0] = g_nfirst[1] = g_nfirst[2] = g_nfirst[3] = 0;
  int k = 0;
  for (int i = 0; v && i < n; i++) {
    uint32_t comp = v[2 * i], id = v[2 * i + 1];
    if (comp > 3 || !id || id >> 18 || g_nfirst[comp] >= 48) continue;
    g_first[comp][g_nfirst[comp]++] = id; k++;
  }
  return k;
}

__declspec(dllexport) void fl26_swiss_uecl(const uint32_t* clubs, int n)
{
  g_uecl_n = 0;
  for (int i = 0; clubs && i < n && i < 48; i++) g_uecl_list[g_uecl_n++] = clubs[i];
}

/* The standings screen for a group (Competition Info -> Group stage) is laid out with a fixed
 * number of row widgets -- ten -- and its filler 0x140af72b0 asks for row i with 0x140e5a790 and
 * dereferences the answer unchecked.  A league phase of 36 in one group makes it ask for row 10,
 * get null and die (0x140af7519, 2026-09-24).  Until the full table has a screen of its own, the
 * wrapper shows as many rows as the layout has: it cuts the group's row vector to the widget count
 * for the duration of the call and puts the end pointer back afterwards. */
#define STAND_RVA  0xaf72b0
#define UIROOT_RVA 0xe3dc90
#define UICHILD_RVA 0xe5a790
static const unsigned char SIG_STAND[15] = {
  0x48,0x8b,0xc4, 0x55, 0x41,0x54, 0x41,0x55, 0x41,0x56, 0x41,0x57, 0x48,0x8b,0xec };
typedef uint64_t (*stand_fn)(void* self);
typedef void* (*uiroot_fn)(void* self);
typedef void* (*uichild_fn)(void* w, uint64_t i);
unsigned char* g_tramp_stand = 0;
static int g_stand_said = 0;

/* The header of a group page is "Group " + ('A' + index), built by 0x140af53e0 into a std::string
 * (its only caller is the row filler).  While a paged league-phase table is drawn the header
 * says "League Phase" instead -- short enough for the string's inline buffer. */
#define GNAME_RVA 0xaf53e0
static const unsigned char SIG_GNAME[15] = {
  0x40,0x57, 0x48,0x83,0xec,0x60, 0x48,0xc7,0x44,0x24,0x28,0xfe,0xff,0xff,0xff };
typedef void* (*gname_fn)(void* self, void* out);
unsigned char* g_tramp_gname = 0;
static volatile int g_paging = 0;

void* gname_handler(void* self, void* out)
{
  void* r = ((gname_fn)(uintptr_t)g_tramp_gname)(self, out);
  unsigned char* str = (unsigned char*)out;
  static const char NAME[] = "League Phase";
  if (g_paging && str && *(uint64_t*)(str + 0x18) == 15) {   /* inline buffer, capacity 15 */
    memcpy(str, NAME, sizeof NAME);
    *(uint64_t*)(str + 0x10) = sizeof NAME - 1;
  }
  return r;
}

uint64_t stand_handler(void* self)
{
  unsigned char* s = (unsigned char*)self;
  void* root = ((uiroot_fn)(uintptr_t)(g_base + UIROOT_RVA))(self);
  void* list = root ? ((uichild_fn)(uintptr_t)(g_base + UICHILD_RVA))(root, 0) : 0;
  if (!list) return ((stand_fn)(uintptr_t)g_tramp_stand)(self);
  unsigned nw = 0;
  while (nw < 64 && ((uichild_fn)(uintptr_t)(g_base + UICHILD_RVA))(list, nw)) nw++;
  uint32_t g = *(uint32_t*)(s + 0x90);
  unsigned char* vb = *(unsigned char**)(s + 0xa0); unsigned char* ve = *(unsigned char**)(s + 0xa8);
  size_t ngroups = vb ? (size_t)(ve - vb) / 24 : 0;
  if (!vb || nw == 0 || ngroups == 0) return ((stand_fn)(uintptr_t)g_tramp_stand)(self);

  /* One group longer than the screen -- the league phase: page it.  The screen already pages
     groups with L1/R1 (0x140af6ac0 / 0x140af6b40 step +0x90 modulo +0x94 and call this again),
     so the group count at +0x94 becomes the page count, and for the call the group vector is
     swapped for one whose entries are slices of the single table.  A row carries its own rank,
     so page 2 still says 10, 11, ...  The header says "League Phase" (gname_handler). */
  unsigned char** one = (unsigned char**)vb;
  size_t rows = (size_t)(one[1] - one[0]) / 40;
  /* B503 (jeremy1979_, 19.11.2026): the list has 10 children but shows 8 rows. With pages of 9 the
     9th row of each page (places 9, 18, 27) was under the footer and nobody saw it -- also on our
     own k_b16_uel_page.png of 15.11.  A page holds 8: 36 rows are 5 pages of 8, 8, 8, 8, 4. */
  unsigned vis = nw > 2 ? nw - 2 : nw;
  if (ngroups == 1 && rows > vis) {
    unsigned pages = (unsigned)((rows + vis - 1) / vis);
    if (pages > 8) pages = 8;
    size_t per = (rows + pages - 1) / pages;
    *(uint32_t*)(s + 0x94) = pages;
    if (g >= pages) { g = 0; *(uint32_t*)(s + 0x90) = 0; }
    static unsigned char* fake[8][3];
    for (unsigned i = 0; i < pages; i++) {
      size_t a = i * per, z = a + per; if (z > rows) z = rows; if (a > rows) a = rows;
      fake[i][0] = one[0] + a * 40; fake[i][1] = one[0] + z * 40; fake[i][2] = fake[i][1];
    }
    *(unsigned char**)(s + 0xa0) = (unsigned char*)fake; *(unsigned char**)(s + 0xa8) = (unsigned char*)(fake + pages);
    g_paging = 1;
    uint64_t r = ((stand_fn)(uintptr_t)g_tramp_stand)(self);
    g_paging = 0;
    *(unsigned char**)(s + 0xa0) = vb; *(unsigned char**)(s + 0xa8) = ve;
    if (!g_stand_said) { g_stand_said = 1;
      logf("fl26swiss: standings screen has %u rows (%u shown) for a table of %u -- %u pages of %u (L1/R1)",
           nw, vis, (unsigned)rows, pages, (unsigned)per); }
    return r;
  }

  /* anything else too long for the screen: show what fits instead of crashing */
  if (g >= ngroups) return ((stand_fn)(uintptr_t)g_tramp_stand)(self);
  unsigned char** inner = (unsigned char**)(vb + (size_t)g * 24);
  rows = (size_t)(inner[1] - inner[0]) / 40;
  if (rows <= nw) return ((stand_fn)(uintptr_t)g_tramp_stand)(self);
  unsigned char* keep = inner[1];
  inner[1] = inner[0] + (size_t)nw * 40;
  uint64_t r = ((stand_fn)(uintptr_t)g_tramp_stand)(self);
  inner[1] = keep;
  return r;
}

/* ---- the current phase of a new-format competition ----
 *
 * 0x14150c3c0(comp, flag, flag) answers "which phase of this competition is being played now":
 * it sorts the competition's phases by the format field (+0x308 bits 23-28) against a fixed
 * table of formats in 0x1414ce390 and returns the first one 0x141546c70 does not call finished.
 * That table puts the play-off format (18, the Champions League's August qualifier) before
 * every group or league format, which was right when the play-off came first.  In the new
 * format the play-off comes after the league phase, and the Europa and Conference League
 * play-offs (188, 189) carry format 18 -- so for the whole autumn both competitions answered
 * "the play-off", which is not drawn until February:
 *
 *   - Competition Info greyed out their Group stage and every ranking (24.09, day 345), and
 *   - 0x141510280 (295 callers, "which phase is this club playing in now") found no Europa or
 *     Conference League club in its competition at all.
 *
 * The Champions League only escaped because its play-off, reg 2, is also its August round
 * and so reads as finished until February.  So for our three competitions the phases are put
 * in the order they are played -- league, play-off, knockout -- and the first unfinished one
 * wins, judged by the game's own 0x141546c70.  Everything else, and a competition whose phases
 * are all finished, gets the original answer. */
#define CURPH_RVA 0x150c3c0
#define PHFIN_RVA 0x1546c70
static const unsigned char SIG_CURPH[15] = {
  0x88, 0x54, 0x24, 0x10, 0x55, 0x56, 0x57, 0x41, 0x54, 0x41, 0x55, 0x41, 0x56, 0x41, 0x57 };
typedef uint64_t (*curph_fn)(uint64_t comp, uint64_t flag, uint64_t flag2);
typedef char (*phfin_fn)(uint64_t id);
unsigned char* g_tramp_curph = 0;
static uint32_t g_curph_n = 0;
static unsigned char* find_rec(uint16_t id)
{
  unsigned char* o = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
  void* blk = o ? *(void**)(o + 0x48) : 0;
  return blk ? (unsigned char*)((findrec_fn)(uintptr_t)(g_base + FINDREC_RVA))(blk, id) : 0;
}

/* The current Libertadores qualifying phase among our alias pre-rounds.
   `comp` is the auxiliary competition id, or 0 to consider every alias phase. */
static int libq_current(uint32_t comp)
{
  int best = -1, first = -1, year = lpre_year();
  static int seen_day[MAX_LPRE], seen_has[MAX_LPRE];
  int td = abs_day();

  for (int i = 0; i < g_nlpre; i++) {
    if (!g_lpre[i].alias) continue;

    if (comp) {
      unsigned char* mr = find_rec(g_lpre[i].reg);
      if (!mr || *(uint32_t*)(mr + 0x80) != comp) continue;
    }

    if (first < 0 ||
        season_ord(g_lpre[i].fill) < season_ord(g_lpre[first].fill))
      first = i;

    if (seen_day[i] != td + 1) {
      seen_day[i] = td + 1;
      seen_has[i] = lpre_matches(&g_lpre[i]) > 0;
    }

    if ((g_lpre[i].filled_year == year || seen_has[i]) &&
        (best < 0 ||
         season_ord(g_lpre[i].fill) > season_ord(g_lpre[best].fill)))
      best = i;
  }

  return best >= 0 ? best : first;
}
uint64_t curph_handler(uint64_t comp, uint64_t flag, uint64_t flag2)
{
  split_keys();
  uint64_t r = ((curph_fn)(uintptr_t)g_tramp_curph)(comp, flag, flag2);
  /* B459 (a closed-beta tester, 13.11.2026, FL27): the Europa League's Group stage, Play-offs and
     both rankings were grey in Competition Info all season, while its league phase was played.
     FL27 plays that league phase itself (cup_on is 0), but its format table still holds reg 188,
     the play-off format (18), with no clubs and never drawn there: the game's knockout of 24 is
     reg 6. So the game answered "188" for the whole season -- the same wrong answer as below.
     Read on the rig on 20.09. (day 262): 188 count 0, not drawn, not finished; the league phase
     (5 / 1029) 36 clubs, drawn. The Champions League's reg 2 reads as finished, so it was right.
     An empty, undrawn play-off is never the phase in play: the league phase is, then the knockout. */
  for (int ci = 0; ci < 2; ci++) {
    const cup_t* c = &CUPS[ci];
    if (cup_on(ci) || (uint16_t)r != c->po) continue;
    unsigned char* lg = find_rec(c->league), *po = find_rec(c->po);
    if (!lg || *(uint32_t*)(lg + 0x80) != (uint32_t)comp || !po) continue;
    if (rec_count(po) || ((*(uint32_t*)(po + 0x304) >> 8) & 1)) continue;
    uint16_t now = !((phfin_fn)(uintptr_t)(g_base + PHFIN_RVA))(c->league) ? c->league : find_rec(c->ko) ? c->ko : c->league;
    if (g_curph_n++ < 8)
      logf("fl26swiss: %s is in phase %u, not %u (an empty play-off that is never drawn here)",
           c->name, (unsigned)now, (unsigned)(uint16_t)r);
    return (r & ~0xffffull) | now;
  }
  for (int ci = 0; ci < 3; ci++) {
    const cup_t* c = &CUPS[ci];
    if (!cup_on(ci)) continue;
    unsigned char* lg = find_rec(c->league);
    if (!lg || *(uint32_t*)(lg + 0x80) != (uint32_t)comp) continue;
    const uint16_t order[3] = { c->league, c->po, c->ko };
    for (int k = 0; k < 3; k++) {
      if (!find_rec(order[k])) continue;
      if (((phfin_fn)(uintptr_t)(g_base + PHFIN_RVA))(order[k])) continue;
      if (order[k] != (uint16_t)r && g_curph_n++ < 8)
        logf("fl26swiss: %s is in phase %u, not %u (the format table's order)",
             c->name, (unsigned)order[k], (unsigned)(uint16_t)r);
      return (r & ~0xffffull) | order[k];
    }
    return r;
  }

  /* The auxiliary competition that holds Libertadores F1/F2 must advance from
     F1 to F2 in Competition Info/current-phase queries just as it did in the
     working pre-port implementation. */
  {
    int i = libq_current((uint32_t)comp);
    if (i >= 0) {
      unsigned char* mr = find_rec(g_lpre[i].reg);
      if (mr && *(uint32_t*)(mr + 0x80) == (uint32_t)comp) {
        uint16_t q = g_lpre[i].reg;
        if (q != (uint16_t)r && g_curph_n++ < 8)
          logf("fl26swiss: Libertadores qualifying (competition %u) is in phase %u, not %u",
               (unsigned)comp, (unsigned)q, (unsigned)(uint16_t)r);
        return (r & ~0xffffull) | q;
      }
    }
  }

  return r;
}

/* ---- Competition Info -> Knockout Phase, the menu side ----
 *
 * 0x14150af30(u32* comp, kind) finds a phase of a competition by what it is (kind 3 = the
 * knockout phase, 4 its fallback).  When the Competition Info menu asks it for its Knockout
 * Phase item, the answer is withheld until that phase is the current one -- see the page
 * builder note below for why.  Every other caller gets the game's answer untouched. */
#define PHKIND_RVA 0x150af30
static const unsigned char SIG_PHKIND[15] = {
  0x89, 0x54, 0x24, 0x10, 0x48, 0x89, 0x4c, 0x24, 0x08, 0x53, 0x55, 0x56, 0x57, 0x41, 0x54 };
typedef uint64_t (*phkind_fn)(uint32_t* comp, uint64_t kind);
unsigned char* g_tramp_phkind = 0;
#define MENU_KO_RA  0x151f7c0   /* the menu's Knockout Phase item, kind 3 */
#define MENU_KO4_RA 0x151f7da   /* ... and its kind 4 fallback */
#define MENU_GRP_RA  0x151f78c  /* the menu's grouped-phase item, kind 0 */
#define MENU_GRP2_RA 0x151fc11  /* ... and its enable check */
#define PAGE_GRP_RA  0x1542354  /* the page builder 0x141542300, page type 0: its ties (0x141541480) */

/* Old working Libertadores paging path: menu/page callers that ask for native
   reg 8 are temporarily redirected to the alias phase being played until F3. */
#define LIBQ_MENU_LO      0x151e000
#define LIBQ_MENU_HI      0x1521000
#define LIBQ_PAGE_LIST_RA 0xc6b9dc
#define LIBQ_PAGE_DATA_RA 0x1542354

static int libq_f3_ready(void);
static int libq_redirect_live(void)
{
  int d = today();
  if (d < 0 || d >= 34) return 0;

  for (int i = 0; i < g_nlpre; i++)
    if (g_lpre[i].alias && g_lpre[i].feed8)
      return !libq_f3_ready();

  return 0;
}

static uint32_t g_kogrey_n = 0, g_roll_n = 0;
/* Competition Info -> one item per qualifying round (11.10.), see ci_menu_handler below: the
   regulation the menu's own grouped-phase item ended up with (phkind at MENU_GRP_RA, after the
   roll), and the regulation of the extra item last picked, which the page builder is then given
   (PAGE_GRP_RA) instead of the game's answer. 0xffff = none. */
static uint16_t g_ci_native = 0xffff, g_ci_pick = 0xffff;
static uint32_t g_ci_native_comp = 0xffffffffu, g_ci_pick_comp = 0xffffffffu, g_ci_pick_n = 0;
/* B266 (Konsel 28.10.): the Match Results screen of a summer qualifying round -- the round po_sel
   saw that day, which the page builder is then given (PAGE_GRP_RA). The page asks for the grouped
   phase, and since 13.10. only the menu item rolls, so it was answered with the play-off: not
   drawn yet, its eight empty rows under a "%s" title. 0xffff = none. */
static uint16_t g_mr_pick = 0xffff;
static uint32_t g_mr_pick_comp = 0xffffffffu, g_mr_pick_n = 0;
static int g_mr_pick_day = -1;
/* which of CUPS a competition id is (by its league phase's record), -1 none */
static int ci_of_comp(uint32_t comp)
{
  for (int ci = 0; ci < 3; ci++) {
    unsigned char* lg = find_rec(CUPS[ci].league);
    if (lg && *(uint32_t*)(lg + 0x80) == comp) return ci;
  }
  return -1;
}
/* The February knockout play-off is played in the August play-off's own regulation (2, 188, 189),
   so the one regulation holds the one or the other: the February round from po_start's draw (this
   session) or, in a loaded save, from the end of the league phase (day 28) to the July teardown. */
static int kopo_window(int ci)
{
  int d = today();
  if (d < 0 || ci < 0 || ci > 2 || !cup_on(ci)) return 0;   /* FL27: no February play-off of ours */
  int ad = abs_day();
  if (g_po_day[ci] > -100000 && ad >= g_po_day[ci] && ad - g_po_day[ci] < 160) return 1;
  return d >= 28 && d < PO_MONTHS_BEFORE;
}
/* a regulation that is one of our play-offs (2, 188, 189) or a tie of one: its CUPS index, -1 none */
static int po_cup_of(uint16_t id)
{
  for (int ci = 0; ci < 3; ci++)
    if ((id & 0x3ff) == CUPS[ci].po && (id >> 10) <= 8) return ci;
  return -1;
}
/* The round of a competition's summer qualifying in play: the latest of its play-off, third and
   second qualifying round (QCUPS order) whose first tie holds clubs; -1 for none drawn yet. */
static int q_rolling(uint16_t r)
{
  /* the game answers its format table's first grouped phase: the play-off, or in a world whose
     builder listed the qualifying rounds in front of it, the second qualifying round */
  int p = -1, qa = q_added(r);
  for (int k = 0; k < NQ; k++) if (QCUPS[k].reg == r) p = k;
  if (p < 0 && qa >= 0 && (r >> 10) == 0) p = qa % NQ;
  if (p < 0 || !q_summer()) return -1;
  for (int st = 0; st < NQS; st++) {
    int i = p + NQ * st;
    if (!q_reg(i) || !find_rec(q_reg(i))) continue;
    unsigned char* tie = find_rec(q_tie_of(i, 0));
    if (tie && rec_count(tie)) return i;
  }
  return -1;
}
/* a group stage of the game's own (the Libertadores 9, the AFC Champions League 15): a regulation
   with a group 1024 above it that is none of our league phases' nor of the world's cups */
static int native_group_stage(uint16_t r)
{
  if (r >= 1024) return 0;
  for (int ci = 0; ci < 3; ci++)
    if (r == CUPS[ci].league || r == CUPS[ci].row || r == CUPS[ci].po || r == CUPS[ci].ko) return 0;
  for (int k = 0; k < g_nccup; k++)
    if (r == g_ccup[k].reg || r == g_ccup[k].ko) return 0;
  return get_rec((uint16_t)(r + 1024)) != 0;
}
/* B219: the Libertadores qualifying phase the item shows -- native F3 (reg 8) or an F1/F2 alias --
   holds clubs: its first tie has two */
static int libq_item_live(uint16_t q)
{
  if (q == CONM_LIBQ_REG) {
    unsigned char* t = find_rec((uint16_t)(CONM_LIBQ_REG + 1024));
    return t && rec_count(t) == 2;
  }
  int tk = -1, li = lpre_of(q, &tk);
  if (li < 0 || tk >= 0 || !g_lpre[li].alias) return 0;
  /* B229 (antonimus 25.10.): on 1 January the alias ties still hold last season's clubs, so
     the item lit before phase 1 was filled (day 2) and opened the empty F3 page ("%s"). An
     alias counts only from its own fill day; B275 (antonimus 29.10.): to the end of the year, not
     only the qualifying half-year -- from July the menu showed phase 3 alone. */
  int d = today();
  if (d < 0 || d < g_lpre[li].fill) return 0;
  unsigned char* t = find_rec(lpre_tie(&g_lpre[li], 0));
  return t && rec_count(t) == 2;
}
/* B219: one of the Libertadores qualifying phases (native F3, F1/F2 aliases) holds clubs */
static int libq_any_live(void)
{
  if (libq_item_live(CONM_LIBQ_REG)) return 1;
  for (int li = 0; li < g_nlpre; li++)
    if (g_lpre[li].alias && libq_item_live(g_lpre[li].reg)) return 1;
  return 0;
}
static int libq_page_phases(uint16_t* order);
/* B229: what the Libertadores' qualifying item should be -- 1 on, 0 grey, -1 the game's say (a
   world without the F1/F2 aliases). In the qualifying half-year it is on exactly while its page
   has a phase to show (libq_page_phases): on 1 January the game itself turns it on, its F3 holding
   the provisional field, and the page then had nothing but an empty F3 titled "%s" */
static int libq_item_want(void)
{
  int feed = 0;
  for (int i = 0; i < g_nlpre; i++)
    if (g_lpre[i].alias && g_lpre[i].feed8) feed = 1;
  if (!feed) return -1;
  int d = today();
  if (d < 0) return libq_any_live() ? 1 : -1;
  uint16_t order[MAX_LPRE + 1];
  if (libq_page_phases(order) > 0) return 1;
  /* B275: from July never less than 0.2.5 gave -- phase 3 alone while it holds clubs (a world
     whose phases 1 and 2 were closed in July, a career loaded after their matches were gone) */
  return d >= 182 ? (libq_any_live() ? 1 : -1) : 0;
}
static uint64_t phkind_core(uint32_t* comp, uint64_t kind, uintptr_t ra);
uint64_t phkind_handler(uint32_t* comp, uint64_t kind)
{
  uintptr_t ra = (uintptr_t)__builtin_return_address(0);
  uint64_t r = phkind_core(comp, kind, ra);
  if (!comp) return r;
  if (ra == g_base + MENU_GRP_RA) { g_ci_native = (uint16_t)r; g_ci_native_comp = *comp; }
  /* an extra Competition Info item was picked (ci_sel_handler): its page shows that round */
  if (ra == g_base + PAGE_GRP_RA && g_ci_pick != 0xffff && *comp == g_ci_pick_comp && find_rec(g_ci_pick)) {
    if (g_ci_pick_n++ < 12)
      logf("fl26swiss: Competition Info -- page shows regulation %u (picked item; the game answered %u)",
           (unsigned)g_ci_pick, (unsigned)(uint16_t)r);
    return (r & ~0xffffull) | g_ci_pick;
  }
  /* the Match Results screen of a qualifying round (po_sel): its page lists that round */
  if (ra == g_base + PAGE_GRP_RA && g_mr_pick != 0xffff && *comp == g_mr_pick_comp
      && today() == g_mr_pick_day && find_rec(g_mr_pick)) {
    if (g_mr_pick_n++ < 12)
      logf("fl26swiss: Match Results -- page shows regulation %u (the round played; the game answered %u)",
           (unsigned)g_mr_pick, (unsigned)(uint16_t)r);
    return (r & ~0xffffull) | g_mr_pick;
  }
  return r;
}
static uint64_t phkind_core(uint32_t* comp, uint64_t kind, uintptr_t ra)
{
  uint64_t r = ((phkind_fn)(uintptr_t)g_tramp_phkind)(comp, kind);

  /* The auxiliary F1/F2 competition must expose the phase actually being
     played, not keep answering F1 for the whole season. */
  if (comp && (uint16_t)r != 0xffff) {
    int tk = -1;
    int li = lpre_of((uint16_t)r, &tk);

    if (li >= 0 && g_lpre[li].alias && tk < 0) {
      int cur = libq_current(*comp);
      if (cur >= 0 && g_lpre[cur].reg != (uint16_t)r)
        return (r & ~0xffffull) | g_lpre[cur].reg;
    }
  }

  /* Before native F3 receives the eight F2 winners, the Libertadores menu and
     page builder must treat reg 8 as the alias phase currently being played. */
  if (comp && *comp == CONM_LIB_CID &&
      (uint16_t)r == CONM_LIBQ_REG &&
      libq_redirect_live()) {
    int i = libq_current(0);
    int ui = (ra >= g_base + LIBQ_MENU_LO && ra < g_base + LIBQ_MENU_HI)
          || ra == g_base + LIBQ_PAGE_LIST_RA
          || ra == g_base + LIBQ_PAGE_DATA_RA;

    static uintptr_t seen[16];
    static int nseen = 0;
    int known = 0;

    for (int q = 0; q < nseen; q++)
      if (seen[q] == ra) known = 1;

    if (!known && nseen < 16) {
      seen[nseen++] = ra;
      logf("fl26swiss: Libertadores -- reg 8 asked (kind %u) from %llx: %s",
           (unsigned)kind,
           (unsigned long long)(ra - g_base + 0x140000000ull),
           ui && i >= 0 ? "shown as the qualifying phase being played" : "left as it is");
    }

    if (ui && i >= 0)
      return (r & ~0xffffull) | g_lpre[i].reg;
  }

  if (comp && (uint16_t)r != 0xffff &&
      ((kind == 3 && ra == g_base + MENU_KO_RA) || (kind == 4 && ra == g_base + MENU_KO4_RA))) {
    uint64_t cur = ((curph_fn)(uintptr_t)(g_base + CURPH_RVA))(*comp, 1, 0);
    if ((uint16_t)cur != (uint16_t)r) {
      if (g_kogrey_n++ < 8)
        logf("fl26swiss: Knockout Phase greyed for comp %u (knockout %u, current phase %u)",
             *comp, (unsigned)(uint16_t)r, (unsigned)(uint16_t)cur);
      return r | 0xffff;
    }
    return r;
  }
  /* The group stage of a cup of the world file (AFC Champions League Two, CAF ...): its page reads
     each group's table from the cup's latest season, and once that season is open (from the new
     year, 20.10.: Worldpack, second season, April) or the July teardown has emptied the groups, a
     group with clubs and no table -- or none at all -- takes the game down on Group stage
     (ucrtbase fail-fast 0xc0000409, twice).  Left out, as the Knockout Phase item is, until every
     group's table holds its clubs again: from the next draw. */
  if (comp && (ra == g_base + MENU_GRP_RA || ra == g_base + MENU_GRP2_RA) && (uint16_t)r != 0xffff) {
    for (int k = 0; k < g_nccup; k++) {
      const ccup_t* c = &g_ccup[k];
      if (!c->groups || (uint16_t)r != c->reg) continue;
      for (int g = 0; g < c->groups; g++) {
        uint16_t id = ccup_rep(c, g);
        unsigned char* rec = get_rec(id);
        unsigned char* t = ((table_fn)(uintptr_t)(g_base + TABLE_RVA))(id);
        unsigned n = rec ? rec_count(rec) : 0, rows = t ? *(uint32_t*)(t + 0x3c0) : 0;
        if (n >= 2 && rows == n) continue;
        static int said_grp = 0;
        if (said_grp++ < 8)
          logf("fl26swiss: Competition Info -- Group stage of cup %u greyed: group %c has %u clubs, a table of %u rows",
               (unsigned)c->reg, 'A' + g, n, rows);
        return r | 0xffff;
      }
    }
  }
  /* B205 (Micarodvzla, 23.10.; the same day in game, r13, second season, day 72): the game's own
     group stages -- the Libertadores (reg 9), the AFC Champions League (reg 15) -- take the game
     down on Group stage the same way (ucrtbase fail-fast 0xc0000409).  Their groups are
     reg + 1024 * (g + 1) as a world cup's are; a group whose table, as the page reads it, holds
     fewer than two rows leaves the item out until the next draw.  Our league phases (CUPS) and the
     world's cups (above) have their own answers. */
  if (comp && (ra == g_base + MENU_GRP_RA || ra == g_base + MENU_GRP2_RA) && (uint16_t)r != 0xffff
      && native_group_stage((uint16_t)r)) {
    uint16_t reg = (uint16_t)r;
    for (int g = 0; g < 16; g++) {
      uint16_t id = (uint16_t)(reg + 1024 * (g + 1));
      unsigned char* rec = get_rec(id);
      if (!rec) break;
      unsigned char* t = ((table_fn)(uintptr_t)(g_base + TABLE_RVA))(id);
      unsigned rows = t ? *(uint32_t*)(t + 0x3c0) : 0;
      static int said_native = 0;
      if (said_native < 40) {
        said_native++;
        logf("fl26swiss: Competition Info -- comp %u Group stage, reg %u group %c: %u clubs, a table of %u rows (%s)",
             *comp, (unsigned)reg, 'A' + g, rec_count(rec), rows, t ? "found" : "none");
      }
      if (rows >= 2) continue;
      static int said_ngrp = 0;
      if (said_ngrp++ < 8)
        logf("fl26swiss: Competition Info -- Group stage of reg %u greyed: group %c has a table of %u rows",
             (unsigned)reg, 'A' + g, rows);
      return r | 0xffff;
    }
  }
  /* Page type 0 is the grouped phase -- for our Europa and Conference League, the play-off
     for places 9-24.  The menu asks for it twice (0x14151f78c: the item, 0x14151fc11: whether
     it is live); until the play-off is drawn (+0x304 bit 8) the item is left out, as the
     Knockout Phase item is, rather than offered under the game's fallback name "W-L Table"
     with a page behind it that has nothing to show. */
  /* In the summer the item rolls with the qualifying (08.10.): from the second qualifying round's
     draw to the play-off's it stands for the round in play -- its own regulation, a copy of reg 2
     with the same eight ties, which the page builder lists as it lists the play-offs (named by
     phname_handler).  The enable check reads only the drawn bit (+0x304 bit 8) of what it is
     given; our qualifying regulations are filled without the game's draw, so for them it is
     answered with reg 2, which the game keeps marked drawn all year. */
  /* Each of the three sites asks with a kind of its own: the item 0x14151f78c with 2 (until
     08.10. this tested kind 0 there, so the item never rolled), the enable check with 0, the
     page builder with its page type. */
  if (comp && (ra == g_base + MENU_GRP_RA || ra == g_base + MENU_GRP2_RA || ra == g_base + PAGE_GRP_RA)
      && (uint16_t)r != 0xffff) {
    static int asked = 0;
    if (asked < 6 && q_summer()) {
      asked++;
      logf("fl26swiss: Competition Info -- site %s asks kind %u, the game answers regulation %u",
           ra == g_base + MENU_GRP_RA ? "item" : ra == g_base + MENU_GRP2_RA ? "enable" : "page",
           (unsigned)kind, (unsigned)(uint16_t)r);
    }
    /* Only the item still rolls. Since 11.10. every drawn qualifying round has an item of its own
       (ci_menu_handler), so the Play-offs item rolling to the round in play opened the third
       qualifying round under "Play-offs" (13.10., in game, season 2, day 232). The Play-offs item
       stands for the play-off alone: live once its draw has put clubs in the first tie. */
    /* Prijedlog C: the Europa and Conference League's summer play-off is a regulation of its own
       (q_reg), 188 / 189 the February one -- the Play-offs page lists it once it is drawn */
    if (ra == g_base + PAGE_GRP_RA && qc_world() && q_summer())
      for (int ci = 1; ci < 3; ci++) {
        if ((uint16_t)r != CUPS[ci].po || q_reg(ci) == CUPS[ci].po || !find_rec(q_reg(ci))) continue;
        unsigned char* tie = find_rec(q_tie_of(ci, 0));
        if (!tie || !rec_count(tie)) continue;
        static int said_pc = 0;
        if (said_pc++ < 6) logf("fl26swiss: Competition Info -- %s Play-offs page: regulation %u (the play-off of 32)",
                                CUPS[ci].name, (unsigned)q_reg(ci));
        return (r & ~0xffffull) | q_reg(ci);
      }
    int i = ra == g_base + MENU_GRP_RA ? q_rolling((uint16_t)r) : -1;
    if (i >= 0) {
      if (g_roll_n++ < 12)
        logf("fl26swiss: Competition Info -- %s item shown under its play-off item (regulation %u)",
             QNAME(i), (unsigned)q_reg(i));
      return (r & ~0xffffull) | q_reg(i);
    }
    if (ra == g_base + MENU_GRP2_RA && q_summer()) {
      for (int ci = 0; ci < 3; ci++) {
        const cup_t* c = &CUPS[ci];
        if ((uint16_t)r != c->po) continue;
        /* the summer's play-off: c->po, or a Prijedlog C world's play-off of 32 (q_reg) */
        uint16_t aug = q_reg(ci);
        unsigned char* tie = find_rec(q_tie_of(ci, 0)), *po = find_rec(aug), *r2 = find_rec(CUPS[0].po);
        if (!tie || !rec_count(tie)) {
          static int said_grey = 0;
          if (said_grey++ < 6) logf("fl26swiss: Competition Info -- %s Play-offs greyed: not drawn yet", c->name);
          return r | 0xffff;
        }
        /* the enable check reads the drawn bit only; the summer play-offs are filled without the
           game's draw, reg 2 is marked drawn all year */
        if (!(po && ((*(uint32_t*)(po + 0x304) >> 8) & 1)) && r2 && ((*(uint32_t*)(r2 + 0x304) >> 8) & 1))
          return (r & ~0xffffull) | CUPS[0].po;
        return aug != c->po ? (r & ~0xffffull) | aug : r;
      }
    }
  }
  if (comp && kind == 0 && (ra == g_base + MENU_GRP_RA || ra == g_base + MENU_GRP2_RA)) {
    for (int ci = 1; ci < 3; ci++) {
      const cup_t* c = &CUPS[ci];
      if ((uint16_t)r != c->po) continue;
      unsigned char* po = find_rec(c->po);
      if (!po || !((*(uint32_t*)(po + 0x304) >> 8) & 1)) return r | 0xffff;
    }
    /* The Champions League's is reg 2, which the game marks drawn all year (it is also the
       August round), so its page opened on eight empty ties under a "%s" header (08.10.).
       Left out the same way while its first tie holds no club -- i.e. until a play-off is
       actually drawn into it, in August or in February. */
    if ((uint16_t)r == CUPS[0].po) {
      unsigned char* tie = find_rec(tie_id(&CUPS[0], 0));
      if (!tie || !rec_count(tie)) return r | 0xffff;
    }
  }
  return r;
}

/* ---- Competition Info -> a name for our play-offs ----
 *
 * 0x1414cb830(reg) gives a phase's display name (a text id; 0x3a20010 is "Play-offs") from a
 * per-regulation record read through 0x1414fdbc0, or -1.  Ours were never in the game's text
 * data, so once drawn the menu would still call them "W-L Table".  Asked by the menu
 * (0x14151f7a2), the Europa and Conference League play-offs borrow the Champions League
 * play-off's name.  The function is too small to hook and call through (a rel32 call sits in
 * its first 17 bytes), so this is a full replacement of the same two lines of logic. */
/* ---- "League Phase" for the three league phases ----
 *
 * The shipped Champions and Europa League group regulations name their phase with text
 * 0x3a20011, "Group stage", and the Conference League row copies it; the match screens show
 * it over the score (0x140ebc8f0 asks 0x1414cb830 for the phase of the match's regulation and
 * formats it), as do the Competition Info items.  The game has no "League Phase" text, so the
 * league phases get one of their own: phname_handler names them LP_TEXT, an index table 0x3a2
 * does not use, and 0x1414996f0 -- the lookup both text paths (0x141497dd0, 0x141497e20) end
 * in: table, u16 index -> the string -- answers it.  Every language reads "League Phase", the
 * UEFA name. */
#define LP_TEXT    0x3a2fff1u
#define QR3_TEXT   0x3a2fff2u   /* "3rd Qualifying Round" */
#define QR2_TEXT   0x3a2fff3u   /* "2nd Qualifying Round" */
#define KOPO_TEXT  0x3a2fff4u
#define SUD1_TEXT  0x3a2fff5u   /* "First stage" */
#define QR1_TEXT   0x3a2fff6u   /* "1st Qualifying Round" (FL27's July round) */
/* a qualifying round's text: stage 1 the third, 2 the second, 3 the first */
#define QR_TEXT(st) ((st) == 1 ? QR3_TEXT : (st) == 3 ? QR1_TEXT : QR2_TEXT)
static uint16_t g_sud1_reg = 0xffff;
#define TXTGET_RVA 0x14996f0
static const unsigned char SIG_TXTGET[14] = {
  0x4c, 0x8b, 0x41, 0x08, 0x45, 0x33, 0xc9, 0x45, 0x8b, 0x10, 0x49, 0x8d, 0x40, 0x08 };
typedef const char* (*txtget_fn)(void* table, uint64_t index);
unsigned char* g_tramp_txtget = 0;
const char* txtget_handler(void* table, uint64_t index)
{
  if ((uint16_t)index == (uint16_t)LP_TEXT) return "League Phase";
  if ((uint16_t)index == (uint16_t)QR3_TEXT) return "3rd Qualifying Round";
  if ((uint16_t)index == (uint16_t)QR2_TEXT) return "2nd Qualifying Round";
  if ((uint16_t)index == (uint16_t)KOPO_TEXT) return "Knockout round play-offs";
  if ((uint16_t)index == (uint16_t)SUD1_TEXT) return "First stage";
  if ((uint16_t)index == (uint16_t)QR1_TEXT) return "1st Qualifying Round";
  return ((txtget_fn)(uintptr_t)g_tramp_txtget)(table, index);
}

#define PHNAME_RVA 0x14cb830
#define PHREC_RVA  0x14fdbc0
#define MENU_NAME_RA 0x151f7a2
static const unsigned char SIG_PHNAME[17] = {
  0x48, 0x81, 0xec, 0x38, 0x01, 0x00, 0x00, 0x48, 0x8d, 0x54, 0x24, 0x20, 0xe8, 0x7f, 0x23, 0x03, 0x00 };
typedef char (*phrec_fn)(uint64_t reg, unsigned char* out);
unsigned char* g_tramp_phname = 0;
uint64_t phname_handler(uint64_t reg)
{
  unsigned char rec[0x200];
  phrec_fn get = (phrec_fn)(uintptr_t)(g_base + PHREC_RVA);
  for (int ci = 0; ci < 3 && g_tramp_txtget; ci++)   /* the league phases: "League Phase", see txtget_handler */
    if (cup_on(ci) && ((uint16_t)reg == CUPS[ci].league || (uint16_t)reg == CUPS[ci].row)) return LP_TEXT;

  /* F1/F2 live in an auxiliary competition internally, but every Libertadores
     qualifying page uses the native reg-8 phase name. Borrow its text id instead
     of inventing English-only "Phase 1/2/3" labels. Native F3 falls through to
     its own record below, so all three pages stay localized exactly as the game. */
  if (libq_alias_stage((uint16_t)reg)) {
    unsigned char qrec[0x200];
    if (get(CONM_LIBQ_REG, qrec)) return *(uint32_t*)(qrec + 0x40);
  }
  /* the qualifying rounds (and their ties, so a match screen says it too), as LP_TEXT above --
     before the record: a qualifying round is a copy of reg 2 and its record says "Play-offs" */
  int qa = q_added((uint16_t)reg);
  if (qa >= NQ && g_tramp_txtget) {                /* (Prijedlog C's play-offs, 1 and 2: below, reg 2's name) */
    static int said = 0;
    if (said < 4) { said++; logf("fl26swiss: phase name -- regulation %u named %s qualifying round (asked from %llx)",
                                 (unsigned)(uint16_t)reg, qa / NQ == 1 ? "3rd" : qa / NQ == 3 ? "1st" : "2nd",
                                 (unsigned long long)((uintptr_t)__builtin_return_address(0) - g_base + 0x140000000ull)); }
    return QR_TEXT(qa / NQ);
  }
  /* the February knockout play-off (and its ties, for the match screens): "Knockout round play-offs" */
  int pc = po_cup_of((uint16_t)reg);
  if (pc >= 0 && g_tramp_txtget && kopo_window(pc)) {
    static int said_ko = 0;
    if (said_ko < 4) { said_ko++; logf("fl26swiss: phase name -- regulation %u named Knockout round play-offs (%s)",
                                       (unsigned)(uint16_t)reg, CUPS[pc].name); }
    return KOPO_TEXT;
  }
  if ((uint16_t)reg == g_sud1_reg) return SUD1_TEXT;
  if (get(reg & 0xffff, rec)) return *(uint32_t*)(rec + 0x40);
  if ((uintptr_t)__builtin_return_address(0) == g_base + MENU_NAME_RA &&
      ((uint16_t)reg == CUPS[1].po || (uint16_t)reg == CUPS[2].po || q_added((uint16_t)reg) >= 0
       || lpre_of((uint16_t)reg, &(int){0}) >= 0) && get(CUPS[0].po, rec))
    return *(uint32_t*)(rec + 0x40);
  return 0xffffffffull;
}

/* ---- Competition Info -> Group stage for the Europa and Conference League ----
 *
 * The menu enables its Group stage item (page type 2, the league-phase table) when
 * 0x14151be10 says so, and that answer is read off the first group phase in the format
 * table's order -- for the Champions League its play-off, which the game marks as drawn, so
 * the item is live and shows the 36-club table.  Our Europa and Conference League play-offs
 * come after the league phase and are not drawn until February, so the item stayed grey all
 * autumn.  For those two the answer is the league phase's own "drawn" bit (+0x304 bit 8).
 * An earlier attempt pointed the play-off lookup (kind 0) at the league phase instead; that
 * lit the W-L item, whose page wants a grouped phase and aborted on an empty group list
 * (24.09, 23:32). */
#define GSTAGE_RVA 0x151be10
static const unsigned char SIG_GSTAGE[19] = {
  0x40, 0x57, 0x41, 0x56, 0x41, 0x57, 0x48, 0x83, 0xec, 0x40,
  0x48, 0xc7, 0x44, 0x24, 0x20, 0xfe, 0xff, 0xff, 0xff };
typedef uint64_t (*gstage_fn)(uint32_t* comp);
unsigned char* g_tramp_gstage = 0;
static uint32_t g_gstage_n = 0;
uint64_t gstage_handler(uint32_t* comp)
{
  uint64_t r = ((gstage_fn)(uintptr_t)g_tramp_gstage)(comp);
  if (!comp) return r;
  /* The Champions League too (13.10.): the game reads its play-off, reg 2, marked drawn all year,
     so before the draw League Phase opened on an empty "Group A". */
  for (int ci = 0; ci < 3; ci++) {
    const cup_t* c = &CUPS[ci];
    /* FL27's own Champions and Europa League too (B459): the game reads the Europa League's off
       reg 188, which is never drawn there, so the item stayed grey with the table there */
    unsigned char* lg = find_rec(c->league);
    if (!lg || *(uint32_t*)(lg + 0x80) != *comp) continue;
    uint64_t on = (*(uint32_t*)(lg + 0x304) >> 8) & 1;
    /* ... or a table the page can show already: the league phase's clubs are in from the July
       access list and the game has built its 24+ row table (the same test po_start makes), so
       the Europa and Conference League read like the Champions League before the draw (08.10.:
       "clubs listed, no league phase").  Without a table it stays grey -- an empty one aborted. */
    if (!on && rec_count(lg) >= 24) {
      unsigned char* t = ((table_fn)(uintptr_t)(g_base + TABLE_RVA))(c->row);
      uint32_t rows = t ? *(uint32_t*)(t + 0x3c0) : 0;
      if (rows >= 24 && rows <= 48) on = 1;
    } else if (on) {
      /* B212: drawn, but the season was built with the pool dry and the league phase never got
         a table -- its page reads one that is not there and takes the game down. Grey then. */
      unsigned char* t = ((table_fn)(uintptr_t)(g_base + TABLE_RVA))(c->row);
      if (!t || *(uint32_t*)(t + 0x3c0) < 2) {
        static int said_none = 0;
        if (said_none++ < 3) logf("fl26swiss: %s Group stage item greyed: the league phase has no table", c->name);
        on = 0;
      }
    }
    if ((r & 0xff) != on && g_gstage_n++ < 8)
      logf("fl26swiss: %s Group stage item %s (league phase %u)", c->name, on ? "enabled" : "disabled",
           (unsigned)c->league);
    return (r & ~0xffull) | on;
  }
  return r;
}


/* ---- Libertadores -> "Fase de clasificación": F1/F2/F3 as pages (L1/R1) ----
 *
 * This is the pre-port paging design, adapted to the current runtime:
 * - F1/F2 stay in their technical Competition.bin container.
 * - Copa Libertadores keeps native F3 (reg 8).
 * - Competition Info receives one page per qualifying phase.
 * - the technical F1/F2 competition is hidden from the list.
 */

#define LIBQ_TLIST_RVA   0x1541480
#define LIBQ_TLIST_RA    0x154236f
#define LIBQ_KOBUILD_RVA 0xcaad90
#define LIBQ_SELCOMP_OFF lay_selcomp()   /* 0x1787b5c unless the set moves the lower tail */

static const unsigned char SIG_LIBQ_TLIST[16] = {
  0x40, 0x53, 0x55, 0x41, 0x56, 0x48, 0x83, 0xec,
  0x20, 0x48, 0x8b, 0xda, 0x44, 0x0f, 0xb7, 0xf1
};
static const unsigned char SIG_LIBQ_KOBUILD[16] = {
  0x48, 0x8b, 0xc4, 0x55, 0x41, 0x54, 0x41, 0x55,
  0x41, 0x56, 0x41, 0x57, 0x48, 0x8d, 0x68, 0xa1
};

typedef void (*libq_tlist_fn)(uint64_t phase, void* out);
typedef void (*libq_kobuild_fn)(void* page);

static unsigned char* g_tramp_libq_tlist = 0;
static unsigned char* g_tramp_libq_kobuild = 0;
static uint16_t g_libq_tlist_only = 0;
static int g_libq_tlist_hit = 0;


/* Native F3 is real only once all four ties contain the eight actual F2 winners.
   This replaces the old session-only swapped_year flag and survives save/reload. */
static int libq_f3_ready(void)
{
  int feed = -1;

  for (int i = 0; i < g_nlpre; i++)
    if (g_lpre[i].alias && g_lpre[i].feed8) {
      feed = i;
      break;
    }

  if (feed < 0) return 0;

  uint32_t win[LPRE_TIES];
  if (!libq_decided(&g_lpre[feed], win)) return 0;

  for (int k = 0; k < 4; k++) {
    unsigned char* r =
        find_rec((uint16_t)(CONM_LIBQ_REG + 1024 * (k + 1)));

    if (!r || rec_count(r) != 2) return 0;

    for (int side = 0; side < 2; side++) {
      uint32_t c = rec_clubs(r)[side];
      int found = 0;

      for (int j = 0; j < 8; j++)
        if (same_club(c, win[j])) {
          found = 1;
          break;
        }

      if (!found) return 0;
    }
  }

  return 1;
}


/* Alias phases already filled/played this season, in play order, followed by
   native F3 once its provisional field has really been replaced by F2 winners. */
static int libq_page_phases(uint16_t* order)
{
  int feed = -1, year = lpre_year(), d = today(), n = 0;

  for (int i = 0; i < g_nlpre; i++)
    if (g_lpre[i].alias && g_lpre[i].feed8)
      feed = i;

  if (feed < 0 || d < 0) return 0;                  /* B275: the whole year, phases 1-3 */

  for (int i = 0; i < g_nlpre; i++) {
    if (!g_lpre[i].alias || d < g_lpre[i].fill ||     /* B229: not before its fill day */
        (g_lpre[i].filled_year != year &&
         lpre_matches(&g_lpre[i]) <= 0))
      continue;

    int at = n, tk = -1;

    while (at > 0) {
      int pi = lpre_of(order[at - 1], &tk);
      if (pi < 0 ||
          season_ord(g_lpre[pi].fill) <= season_ord(g_lpre[i].fill))
        break;
      at--;
    }

    memmove(order + at + 1, order + at,
            (size_t)(n - at) * sizeof(*order));
    order[at] = g_lpre[i].reg;
    n++;
  }

  if (n && (libq_f3_ready() || d >= 34))
    order[n++] = CONM_LIBQ_REG;

  return n;
}


/* The native page builder asks for one phase's tie list. When our wrapper is
   building one phase, give exactly that phase; when the page itself asks for
   one of F1/F2/F3, hand it all qualifying phases in order. */
static void libq_tlist_handler(uint64_t phase, void* out)
{
  libq_tlist_fn f =
      (libq_tlist_fn)(uintptr_t)g_tramp_libq_tlist;

  if ((uintptr_t)__builtin_return_address(0) !=
      g_base + LIBQ_TLIST_RA) {
    f(phase, out);
    return;
  }

  if (g_libq_tlist_only) {
    g_libq_tlist_hit = 1;
    f((phase & ~0xffffull) | g_libq_tlist_only, out);
    return;
  }

  uint16_t ph = (uint16_t)phase;
  uint16_t order[MAX_LPRE + 1];
  int tk = -1, li = lpre_of(ph, &tk);
  int mine = ph == CONM_LIBQ_REG ||
             (li >= 0 && g_lpre[li].alias && tk < 0);
  int n = mine ? libq_page_phases(order) : 0;

  /* B229: one phase is enough -- with only F1 filled the page asking for F3 is given F1,
     not the empty F3 */
  if (n < 1) {
    f(phase, out);
    return;
  }

  for (int k = 0; k < n; k++)
    f((phase & ~0xffffull) | order[k], out);
}


/* The native builder normally closes a page every eight items. F1 has three ties,
   so without this F1 and the first five F2 ties become one page. Close a page as
   soon as the next item belongs to a different qualifying phase. */
#define LIBQ_PGLOOP_RVA  0xaf8e4c
#define LIBQ_PGLOOP_ADD  0xaf8e5c
#define LIBQ_PGLOOP_SKIP 0xaf8e7b
static const unsigned char SIG_LIBQ_PGLOOP[16] = {
  0x48, 0x8b, 0xc1, 0x48, 0x2b, 0xc2, 0x48, 0xc1,
  0xf8, 0x03, 0x48, 0x83, 0xf8, 0x08, 0x72, 0x1f
};

#define LIBQ_MATCHREC_RVA 0x14bb280
typedef unsigned char* (*libq_matchrec_fn)(void* blk, uint64_t idx);

static int libq_page_key(uint16_t tie)
{
  if ((tie & 0x3ff) == CONM_LIBQ_REG && tie > 1024)
    return 100;

  int tk = -1;
  int i = lpre_of(tie, &tk);
  if (i < 0 || !g_lpre[i].alias) return -1;
  return season_ord(g_lpre[i].fill);
}

/* the item keeps its match id as a word: with u32 ids it is the record L or L + 65536, and the one
   on a qualifying page is the item's (see match_of_reg) */
static int libq_item_key(void* blk, const unsigned char* item)
{
  uint32_t lo = *(const uint16_t*)(item + 4);
  for (uint32_t h = 1; h <= 1; h--) {
    uint32_t id = lo | h << 16;
    unsigned char* m = ((libq_matchrec_fn)(uintptr_t)(g_base + LIBQ_MATCHREC_RVA))(blk, id);
    if (!m || *(uint32_t*)m != id) continue;
    int k = libq_page_key(*(uint16_t*)(m + 4));
    if (k >= 0 || !h) return k;
  }
  return -1;
}

static uint64_t libq_page_break(const unsigned char* cur,
                                const unsigned char* end)
{
  if (!cur || cur + 16 > end) return 0;

  unsigned char* o =
      (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
  void* blk = o ? *(void**)(o + 0x48) : 0;
  if (!blk) return 0;

  int a = libq_item_key(blk, cur);
  if (a < 0) return 0;

  int b = libq_item_key(blk, cur + 8);
  if (b < 0 || a == b) return 0;

  static int said_day = -1;
  if (said_day != abs_day()) {
    said_day = abs_day();
    logf("fl26swiss: Libertadores qualifying page -- a page break between phases");
  }

  return 1;
}

static void libq_abs_jmp(unsigned char* p, uint64_t to)
{
  p[0] = 0xff;
  p[1] = 0x25;
  *(uint32_t*)(p + 2) = 0;
  *(uint64_t*)(p + 6) = to;
}


/* A single=1 lpre has page kind 2, but its synthetic master id is not in the
   game's hard-coded play-off id set. Route those masters to the native play-off
   results page after a match; every unrelated id keeps the original test. */
#define SINGLE_POPAGE_RVA 0xaf9455
#define SINGLE_POPAGE_NO  0xaf9465
#define SINGLE_POPAGE_YES 0xaf9479
static const unsigned char SIG_SINGLE_POPAGE[16] = {
  0x66,0x83,0xfe,0x0b,0x77,0x0a,0xb9,0x04,0x09,0x00,0x00,0x0f,0xa3,0xf1,0x72,0x14 };
static int single_popage_patch(uint64_t exe_base)
{
  unsigned char* t = (unsigned char*)(uintptr_t)(exe_base + SINGLE_POPAGE_RVA);
  if (memcmp(t, SIG_SINGLE_POPAGE, 16)) return 2;
  unsigned char* st = (unsigned char*)VirtualAlloc(0, 0x800, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
  if (!st) return 3;
  uint16_t* slots = (uint16_t*)(st + 0x600);
  for (int i = 0; i < MAX_LPRE; i++) slots[i] = 0xfffe;
  unsigned char* q = st;
  unsigned char* je[MAX_LPRE];
  for (int i = 0; i < MAX_LPRE; i++) {
    q[0]=0x66; q[1]=0x3b; q[2]=0x35;
    *(int32_t*)(q+3)=(int32_t)((unsigned char*)&slots[i]-(q+7)); q+=7;
    q[0]=0x0f; q[1]=0x84; je[i]=q; q+=6;
  }
  memcpy(q, SIG_SINGLE_POPAGE, 16);
  unsigned char* ja=q+4, *jb=q+14; q+=16;
  unsigned char* no=q;  libq_abs_jmp(q, exe_base + SINGLE_POPAGE_NO);  q+=14;
  unsigned char* yes=q; libq_abs_jmp(q, exe_base + SINGLE_POPAGE_YES); q+=14;
  for (int i=0;i<MAX_LPRE;i++) *(int32_t*)(je[i]+2)=(int32_t)(yes-(je[i]+6));
  ja[1]=(unsigned char)(no-(ja+2));
  jb[1]=(unsigned char)(yes-(jb+2));
  DWORD old;
  if (!VirtualProtect(t,16,PAGE_EXECUTE_READWRITE,&old)) return 4;
  libq_abs_jmp(t,(uint64_t)(uintptr_t)st); t[14]=0x90; t[15]=0x90;
  VirtualProtect(t,16,old,&old);
  FlushInstructionCache(GetCurrentProcess(),t,16);
  g_single_po_slots=slots;
  for (int i=0;i<g_nlpre;i++) if (g_lpre[i].single)
    for (int k=0;k<MAX_LPRE;k++) if (slots[k]==0xfffe) { slots[k]=g_lpre[i].reg; break; }
  return 0;
}

static int libq_pgloop_install(uint64_t exe_base)
{
  unsigned char* t =
      (unsigned char*)(uintptr_t)(exe_base + LIBQ_PGLOOP_RVA);

  if (memcmp(t, SIG_LIBQ_PGLOOP, 16)) return 2;

  unsigned char* st =
      (unsigned char*)VirtualAlloc(0, 0x200,
                                  MEM_COMMIT | MEM_RESERVE,
                                  PAGE_EXECUTE_READWRITE);
  if (!st) return 3;

  unsigned char* p = st;
  static const unsigned char head[] = {
    0x48, 0x8b, 0xc1,
    0x48, 0x2b, 0xc2,
    0x48, 0xc1, 0xf8, 0x03,
    0x48, 0x83, 0xf8, 0x08,
    0x0f, 0x83, 0, 0, 0, 0,
    0x50, 0x51, 0x52, 0x41, 0x50, 0x41, 0x51, 0x41, 0x52, 0x41, 0x53,
    0x48, 0x83, 0xec, 0x28,
    0x48, 0x8b, 0xcb,
    0x48, 0x8b, 0xd7,
    0x48, 0xb8, 0,0,0,0,0,0,0,0,
    0xff, 0xd0,
    0x49, 0x89, 0xc3,
    0x48, 0x83, 0xc4, 0x28,
    0x4d, 0x85, 0xdb,
    0x41, 0x5b, 0x41, 0x5a, 0x41, 0x59, 0x41, 0x58, 0x5a, 0x59, 0x58,
    0x0f, 0x85, 0, 0, 0, 0
  };

  memcpy(p, head, sizeof head);

  unsigned char* jae_at = p + 14;
  unsigned char* call_imm = p + 20 + 11 + 4 + 3 + 3 + 2;
  unsigned char* jnz_at = p + sizeof head - 6;

  *(uint64_t*)call_imm = (uint64_t)(uintptr_t)libq_page_break;
  p += sizeof head;

  unsigned char* skip = p;
  libq_abs_jmp(p, exe_base + LIBQ_PGLOOP_SKIP);
  p += 14;

  unsigned char* add = p;
  libq_abs_jmp(p, exe_base + LIBQ_PGLOOP_ADD);
  p += 14;

  *(int32_t*)(jae_at + 2) =
      (int32_t)(add - (jae_at + 6));
  *(int32_t*)(jnz_at + 2) =
      (int32_t)(add - (jnz_at + 6));
  (void)skip;

  DWORD old;
  if (!VirtualProtect(t, 16, PAGE_EXECUTE_READWRITE, &old))
    return 4;

  libq_abs_jmp(t, (uint64_t)(uintptr_t)st);
  t[14] = 0x90;
  t[15] = 0x90;

  VirtualProtect(t, 16, old, &old);
  FlushInstructionCache(GetCurrentProcess(), t, 16);
  return 0;
}


/* When the qualifying page opens after a match, select the page that belongs to
   that tie/current alias phase rather than dropping back to F1. */
#define LIBQ_PGFIRST_RVA  0xaf8eec
#define LIBQ_PGFIRST_BACK 0xaf8efe
#define LIBQ_PGFIND_RVA   0xca3c50
static const unsigned char SIG_LIBQ_PGFIRST[18] = {
  0x0f, 0xb7, 0xd0, 0x49, 0x8b, 0xce, 0xe8, 0x59, 0xad,
  0x1a, 0x00, 0x41, 0x89, 0x86, 0xa8, 0x00, 0x00, 0x00
};

static int libq_result_page_key(unsigned char* page, size_t i)
{
  unsigned char* b = *(unsigned char**)(page + 0x90);
  return libq_page_key(*(uint16_t*)(b + 32 * i + 4));
}

static uint64_t libq_pgfirst_fix(unsigned char* page,
                                 uint64_t tie,
                                 uint64_t chosen)
{
  if (!page || IsBadReadPtr(page, 0xb0)) return chosen;

  unsigned char* b = *(unsigned char**)(page + 0x90);
  unsigned char* e = *(unsigned char**)(page + 0x98);
  size_t n = b && e > b ? (size_t)(e - b) / 32 : 0;

  if (n < 2) return chosen;

  for (size_t i = 0; i < n; i++)
    if (libq_result_page_key(page, i) < 0)
      return chosen;

  int want = libq_page_key((uint16_t)tie);
  int why = 0;

  if (want < 0) {
    int cur = libq_current(0);
    want = cur >= 0 ? season_ord(g_lpre[cur].fill) : -1;
    why = 1;
  }

  uint64_t r = chosen;

  if (want >= 0 &&
      (chosen >= n ||
       libq_result_page_key(page, (size_t)chosen) != want))
    for (size_t i = 0; i < n; i++)
      if (libq_result_page_key(page, i) == want) {
        r = i;
        break;
      }

  static int said = 0;
  if (said++ < 8)
    logf("fl26swiss: Libertadores qualifying page after a match -- tie %u, the game chose page %u, shown page %u%s",
         (unsigned)(uint16_t)tie,
         (unsigned)chosen,
         (unsigned)r,
         why ? " (by the phase being played)" : "");

  return r;
}

static int libq_pgfirst_install(uint64_t exe_base)
{
  unsigned char* t =
      (unsigned char*)(uintptr_t)(exe_base + LIBQ_PGFIRST_RVA);

  if (memcmp(t, SIG_LIBQ_PGFIRST, 18)) return 2;

  unsigned char* st =
      (unsigned char*)VirtualAlloc(0, 0x100,
                                  MEM_COMMIT | MEM_RESERVE,
                                  PAGE_EXECUTE_READWRITE);
  if (!st) return 3;

  unsigned char code[] = {
    0x0f, 0xb7, 0xd0,
    0x52,
    0x48, 0x83, 0xec, 0x28,
    0x49, 0x8b, 0xce,
    0x48, 0xb8, 0,0,0,0,0,0,0,0,
    0xff, 0xd0,
    0x44, 0x8b, 0xc0,
    0x8b, 0x54, 0x24, 0x28,
    0x49, 0x8b, 0xce,
    0x48, 0xb8, 0,0,0,0,0,0,0,0,
    0xff, 0xd0,
    0x48, 0x83, 0xc4, 0x28,
    0x5a,
    0x41, 0x89, 0x86, 0xa8, 0x00, 0x00, 0x00
  };

  *(uint64_t*)(code + 13) = exe_base + LIBQ_PGFIND_RVA;
  *(uint64_t*)(code + 35) =
      (uint64_t)(uintptr_t)libq_pgfirst_fix;

  memcpy(st, code, sizeof code);
  libq_abs_jmp(st + sizeof code,
               exe_base + LIBQ_PGFIRST_BACK);

  DWORD old;
  if (!VirtualProtect(t, 18, PAGE_EXECUTE_READWRITE, &old))
    return 4;

  libq_abs_jmp(t, (uint64_t)(uintptr_t)st);
  for (int i = 14; i < 18; i++) t[i] = 0x90;

  VirtualProtect(t, 18, old, &old);
  FlushInstructionCache(GetCurrentProcess(), t, 18);
  return 0;
}


/* Hide technical CONMEBOL Competition.bin containers from Competition Info.
   They remain real region-1 competitions internally so every regulation row is live. */
#define LIBQ_SKIPPH_RVA 0x14cfb20
#define LIBQ_LIST_RA1   0xaccdc5
#define LIBQ_LIST_RA2   0xacd635
#define LIBQ_LIST_RA3   0xc6a6f7
static const unsigned char SIG_LIBQ_SKIPPH[9] = {
  0x40, 0x53, 0x48, 0x83, 0xec, 0x20, 0x0f, 0xb7, 0xd9
};

/* a live regulation's competition (record +0x80), CI_NO_COMP when the world has none */
#define CI_NO_COMP 0xffffffffu
typedef uint32_t (*ci_comp_fn)(uint16_t reg);

/* The pre-round whose helper competition `comp` is, or -1.  Technical continental containers:
     - alias: modern Libertadores F1/F2
     - lpre_is_suda: modern Sudamericana first stage
     - poko: modern Sudamericana post-group playoff
     - B470 (morpheus 15.11.): a continental cup's preliminary round (leaguebuilder
       prepare_cup_prelims, FL_PRE<n>), a competition of its own that carries its cup's name
       ("OFC Champions League", 24 bytes) -- Competition Info listed it as a second item of
       that name after the real cup's, and the OFC one showed two clubs and a grey bracket.
   They must stay live in region 1 for the engine, but must not appear as standalone
   tournaments in Competition Info.  A league cup's pre-round is a regulation of its cup's own
   competition (mkeuropo.prerounds), so it is never taken for one. */
static int ci_helper_lpre(uint32_t comp, ci_comp_fn comp_of)
{
  if (comp == CI_NO_COMP) return -1;
  for (int i = 0; i < g_nlpre; i++) {
    const lpre_t* l = &g_lpre[i];
    if (comp_of(l->reg) != comp) continue;
    if (l->alias || lpre_is_suda(l) || l->poko) return i;
    const ccup_t* c = lpre_cup(l);
    uint32_t cup = c ? comp_of(c->ko) : CI_NO_COMP;
    if (cup != CI_NO_COMP && cup != comp) return i;
  }
  return -1;
}
static uint32_t ci_live_comp(uint16_t reg)
{
  unsigned char* r = find_rec(reg);
  return r ? *(uint32_t*)(r + 0x80) : CI_NO_COMP;
}

static uint64_t libq_skipph_handler(uint64_t reg)
{
  unsigned char* r = find_rec((uint16_t)reg);
  if (!r) return 0;

  if ((*(uint32_t*)(r + 0x308) & 0x1f800000u) ==
      0x11000000u)
    return 1;

  uintptr_t ra = (uintptr_t)__builtin_return_address(0);
  if (ra != g_base + LIBQ_LIST_RA1 &&
      ra != g_base + LIBQ_LIST_RA2 &&
      ra != g_base + LIBQ_LIST_RA3)
    return 0;

  uint32_t comp = *(uint32_t*)(r + 0x80);
  int i = ci_helper_lpre(comp, ci_live_comp);
  if (i < 0) return 0;

  static uint32_t said[8]; static int nsaid = 0;
  int known = 0;
  for (int k = 0; k < nsaid; k++) known |= said[k] == comp;
  if (!known && nsaid < 8) {
    said[nsaid++] = comp;
    logf("fl26swiss: Info Database -- technical helper competition %u (pre-round %u of cup %u) hidden",
         comp, (unsigned)g_lpre[i].reg, (unsigned)g_lpre[i].ko);
  }
  return 1;
}

static int libq_skipph_install(uint64_t exe_base)
{
  unsigned char* t =
      (unsigned char*)(uintptr_t)(exe_base + LIBQ_SKIPPH_RVA);

  if (memcmp(t, SIG_LIBQ_SKIPPH, 9)) return 2;

  DWORD old;
  if (!VirtualProtect(t, 14, PAGE_EXECUTE_READWRITE, &old))
    return 4;

  libq_abs_jmp(t, (uint64_t)(uintptr_t)libq_skipph_handler);

  VirtualProtect(t, 14, old, &old);
  FlushInstructionCache(GetCurrentProcess(), t, 14);
  return 0;
}


/* Run the native knockout/play-off page builder once per phase only when it is
   actually the qualifying page. The main Libertadores KO is still built once. */
static void libq_kobuild_handler(void* page)
{
  libq_kobuild_fn f =
      (libq_kobuild_fn)(uintptr_t)g_tramp_libq_kobuild;

  unsigned char* o =
      (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
  unsigned char* blk = o ? *(unsigned char**)(o + 0x48) : 0;
  uint16_t order[MAX_LPRE + 1];

  int n = blk &&
          *(uint32_t*)(blk + LIBQ_SELCOMP_OFF) == CONM_LIB_CID
        ? libq_page_phases(order)
        : 0;

  static int said = 0;
  if (said++ < 6)
    logf("fl26swiss: knockout page builder -- selected competition %u, %d qualifying phase(s)",
         blk ? *(uint32_t*)(blk + LIBQ_SELCOMP_OFF) : 0u,
         n);

  if (n < 2) {
    f(page);
    return;
  }

  g_libq_tlist_hit = 0;
  g_libq_tlist_only = order[0];
  f(page);
  g_libq_tlist_only = 0;

  if (!g_libq_tlist_hit) {
    static int said_ko = 0;
    if (said_ko++ < 6)
      logf("fl26swiss: Libertadores main knockout page -- built once");
    return;
  }

  for (int k = 1; k < n; k++) {
    g_libq_tlist_only = order[k];
    f(page);
  }

  g_libq_tlist_only = 0;

  static int said_day = -1;
  if (said_day != abs_day()) {
    said_day = abs_day();
    char line[64];
    int lo = 0;

    for (int k = 0; k < n && lo < 56; k++)
      lo += snprintf(line + lo, sizeof line - lo,
                     " %u", (unsigned)order[k]);

    logf("fl26swiss: Libertadores qualifying page -- built a phase at a time:%s",
         line);
  }
}


/* ---- Competition Info -> one entry per league cup pre-round, not nine ----
 *
 * A category of Competition Info lists the regulations 0x1415789c0 hands it for the
 * category's region, two ways: the grid beside the category list (0x140acd3f0) and the list
 * behind it (0x140c6a540). A regulation in a country's region (the region test 0x1414cf160)
 * gets an entry of its own; one in an international region goes in once per competition. A
 * league cup's pre-round is reg 2 and its eight replicas (mkeuropo.prerounds), in the
 * country's region, so the cup showed ten times under one name: the pre-round bracket, a page
 * per tie, the unused ties empty, then the main knockout (GitHub #78). This takes the
 * pre-round's ties out of what 0x1415789c0 returns -- a vector of u16 regulation ids -- so
 * the pre-round bracket and the main knockout are what is left. The shipped replicas (the
 * Champions League's and the rest) are international and listed once per competition anyway. */
#define CATREGS_RVA 0x15789c0
static const unsigned char SIG_CATREGS[15] = {
  0x48, 0x89, 0x54, 0x24, 0x10, 0x55, 0x53, 0x56, 0x57, 0x41, 0x54, 0x41, 0x55, 0x41, 0x56 };
typedef uint64_t (*catregs_fn)(void* cat, uint16_t** vec);
unsigned char* g_tramp_catregs = 0;
static uint32_t g_catregs_n = 0;
uint64_t catregs_handler(void* cat, uint16_t** vec)
{
  uint64_t r = ((catregs_fn)(uintptr_t)g_tramp_catregs)(cat, vec);
  if (!vec || !vec[0] || !g_nlpre) return r;
  uint16_t *in = vec[0], *out = vec[0], *end = vec[1];
  int tie, cut = 0;
  for (; in < end; in++) {
    int li = lpre_of(*in, &tie);
    if (li >= 0 && tie >= 0) { cut++; continue; }
    *out++ = *in;
  }
  if (cut) {
    vec[1] = out;                    /* shorter only: the vector keeps its memory */
    if (g_catregs_n++ < 4) logf("fl26swiss: Competition Info -- %d pre-round tie(s) left out of a category", cut);
  }
  return r;
}

/* ---- Competition Info -> Knockout Phase before the knockout phase exists ----
 *
 * The page builder 0x140caaa70 takes the knockout phase (0x14150af30 kind 3, else kind 4) and
 * fetches its record only when it is also the current phase (the cmp at 0x140caae5a); otherwise
 * the record pointer stays NULL and the page loop reads through it at 0x140cab3a4.  The menu
 * (0x14151f5f0) offers the item all season, so opening it in the autumn killed the game --
 * Europa League at 22:35 and the Champions League on the retry, 24.09.  Letting the builder
 * fetch the record anyway only moved the crash (a fast-fail at 23:21), so phkind_handler greys
 * the item instead: when the menu asks for the knockout phase and that is not the current
 * phase, it hears "no such phase" -- the same answer that greys the item for a cup without one.
 * The rule is the builder's own condition, so it holds for every competition. */

/* The replacement for 0x14157f810.  cx = regulation id, rdx = the vector the caller wants
   filled with {day of year, round, kind} records.
 *
 * For anything but ours the original runs untouched -- including the date stub the patch set
 * puts in case 62, which is what gives our ordinary leagues their fixtures.
 *
 * For ours: the shipped 38-round league calendar is asked for first, purely so that the
 * game's own allocator grows the vector, and then the first sixteen records are rewritten and
 * the vector is cut to sixteen.  Cutting a vector by moving its end pointer frees nothing and
 * reallocates nothing, so the memory behind it stays exactly as the game laid it out.  This
 * only ever shortens: a calendar longer than the 38 the shipped array holds would need the
 * allocator, and is refused rather than guessed at.
 */
/* round of 16, quarter-finals, semi-finals (two legs each) and the final, 2025/26. The Champions
   League on its Wednesdays (0.2.0; the Tuesdays until then): with the Europa and Conference
   League on the Thursdays of the same weeks, the Sunday between two European weeks is three days
   from both, and a league with clubs in all three keeps a weekend day (real calendars) */
static const uint32_t KO_DAYS[3][7] = {
  { 69, 76,  97, 104, 118, 125, 149 },   /* Champions League: 11/18 Mar, 8/15 Apr, 29 Apr/6 May, 30 May */
  { 70, 77,  98, 105, 119, 126, 139 },   /* Europa League: 12/19 Mar, 9/16 Apr, 30 Apr/7 May, 20 May */
  { 70, 77,  98, 105, 119, 126, 146 },   /* Conference League: the same Thursdays, final 27 May */
};

/* ---- leagues that are not twenty clubs, double round robin ----
 *
 * Our leagues get the shipped 38-round league calendar (datecave's stub, shifted by a day or
 * two). A league of ten clubs playing four times, or of twelve playing three, needs 36 or 33
 * rounds; the fixture builder takes the first rounds it needs and the season would stop in
 * April. A league of twenty-two or twenty-four needs 42 or 46, more than the calendar has.
 * So the round count is read from the live regulation -- clubs at +0x30c bits 0-6 and the
 * round-robin count at +0x308 bits 29-31 (docs/regulation-field-map.txt) -- and the calendar
 * is resampled to exactly that many dates spread over the whole season. A longer one first
 * borrows a longer one and keeps the shift our calendar had: the Premier League's (reg 17, 38
 * rounds, over by the end of May) when that is enough, else the Championship's (reg 79, 46
 * rounds, which runs into June).
 * Twenty clubs twice is 38 and is left exactly as it was. */
/* The built-in list: the ids the world builder hands out; a world file replaces it (fl26_swiss_leagues). */
#define MAX_OUR_LEAGUES 512   /* 256 until the league band (fl26world 320..499): ~250 leagues */
static uint16_t OUR_LEAGUES[MAX_OUR_LEAGUES] = {
  11, 49, 60, 61, 62, 74, 76, 93, 94, 96, 98, 100, 109, 110, 111, 112, 113, 114, 121, 138, 139,
  140, 143, 144, 145, 146, 170, 171, 173, 174, 176, 178, 179, 180, 181, 182, 183, 184, 185, 190 };
static int g_nour = 40;
#define LONG_CAL_REG 79
#define MID_CAL_REG 17
static int our_league(uint16_t id)
{
  for (int i = 0; i < g_nour; i++)
    if (OUR_LEAGUES[i] == id) return 1;
  return 0;
}

/* The leagues whose calendar is resampled to their own round count (league_dates): the
   world file's leagues. Returns how many were taken. */
__declspec(dllexport) int fl26_swiss_leagues(const uint16_t* ids, int n)
{
  if (!ids || n < 0) return -1;
  if (n > MAX_OUR_LEAGUES) n = MAX_OUR_LEAGUES;
  for (int i = 0; i < n; i++) OUR_LEAGUES[i] = ids[i];
  g_nour = n;
  logf("fl26swiss: league calendars for %d leagues of the world file", n);
  return n;
}
/* Leagues of ours in a January-December country (a second division below Colombia's, Japan's
   ...): the European calendar put five of their rounds before day 41, when such a league joins
   its season (fl26join), and those were never played -- the season then ended with no final
   table (GitHub #27). Their rounds are spread from mid February to early December instead. */
#define CAL_FIRST 45
#define CAL_LAST  333
static uint16_t g_calyear[MAX_OUR_LEAGUES]; static int g_ncalyear = 0;
__declspec(dllexport) int fl26_swiss_calendar_year(const uint16_t* ids, int n)
{
  if ((!ids && n) || n < 0) return -1;
  if (n > MAX_OUR_LEAGUES) n = MAX_OUR_LEAGUES;
  for (int i = 0; i < n; i++) g_calyear[i] = ids[i];
  g_ncalyear = n;
  logf("fl26swiss: %d league(s) on a January-December calendar", n);
  return n;
}
static int calyear(uint16_t id)
{
  for (int i = 0; i < g_ncalyear; i++) if (g_calyear[i] == id) return 1;
  return 0;
}
/* The game's own leagues of a calendar-year region that the world file moves to August-May
   (`season 28 0`: the Saudi Pro League, 162): their case in the date switch is a February-
   December calendar, so they take the Premier League's (reg 17, 38 rounds) resampled to their
   own round count, like ours. Experimental: the season builder's own lists are by id. */
static uint16_t g_eudate[16]; static int g_neudate = 0;
__declspec(dllexport) int fl26_swiss_european(const uint16_t* ids, int n)
{
  if ((!ids && n) || n < 0) return -1;
  if (n > 16) n = 16;
  for (int i = 0; i < n; i++) g_eudate[i] = ids[i];
  g_neudate = n;
  logf("fl26swiss: %d league(s) of the game moved to the European calendar", n);
  return n;
}
static int eudate(uint16_t id)
{
  for (int i = 0; i < g_neudate; i++) if (g_eudate[i] == id) return 1;
  return 0;
}
/* ---- no league round of ours on a European day (GitHub #54) ----
 * A league of ours plays the big-league calendar shifted by its id's day (datecave) and
 * resampled to its rounds, and the shift knows nothing of Europe: Romania on 93 (+6) played
 * league rounds on Conference League days 309 and 330, the club's league match was played on
 * the European day and its result went into both tables.  Whatever a calendar comes out as,
 * a round that lands on a day any European competition of ours plays is moved to the nearest
 * free day (1, 2, 3 days either way) that keeps the rounds in order. */
static int euro_day(uint32_t d)
{
  for (int i = 0; i < FL26_SWISS36_MATCHDAYS; i++) if (swiss_day(i) == d) return 1;
  for (int i = 0; i < FL26_SWISS6_MATCHDAYS; i++) if (eday(UECL_DAYS[i]) == d) return 1;
  for (int c = 0; c < 3; c++) {
    for (int i = 0; i < 7; i++) if (eday(KO_DAYS[c][i]) == d) return 1;
    for (int i = 0; i < 2; i++) if (qr_day(c, i) == d || eday(CUPS[c].days[i]) == d) return 1;
  }
  for (int i = 0; i < 2; i++) if (qr_day(3, i) && qr_day(3, i) == d) return 1;   /* FL27's July round */
  return 0;
}
static uint32_t season_pos(uint32_t d) { return d >= 182 ? d - 182 : d + 183; }   /* July first */
static int declash(date_t* r, uint32_t n)
{
  static const int step[6] = { 1, -1, 2, -2, 3, -3 };
  int moved = 0;
  for (uint32_t i = 0; i < n; i++) {
    if (!euro_day(r[i].day)) continue;
    for (int k = 0; k < 6; k++) {
      uint32_t d = (uint32_t)(((int)r[i].day + 365 + step[k]) % 365);
      if (euro_day(d)) continue;
      if (i && season_pos(d) <= season_pos(r[i - 1].day)) continue;
      if (i + 1 < n && season_pos(d) >= season_pos(r[i + 1].day)) continue;
      r[i].day = d; moved++; break;
    }
  }
  return moved;
}
/* a European day, or the day before or after one */
static int euro_near(uint32_t d)
{
  return euro_day(d) || euro_day((d + 1) % 365) || euro_day((d + 364) % 365);
}
/* the last resort before declash: when no calendar has free days everywhere (an 18 or 20 club
   league with European places: 34 or 38 rounds), a round right next to a European day still
   moves, up to three days either way and in order, to a day with one free day each side of the
   European one. rwee, 07.10.: Man City, Fulham and Bayern played the league the day after the
   Champions League's January matchday; the 16 club leagues had room and were fine */
static int declash_near(date_t* r, uint32_t n)
{
  static const int step[6] = { 1, -1, 2, -2, 3, -3 };
  int moved = 0;
  for (uint32_t i = 0; i < n; i++) {
    if (r[i].day >= 365 || !euro_near(r[i].day)) continue;
    for (int k = 0; k < 6; k++) {
      uint32_t d = (uint32_t)(((int)r[i].day + 365 + step[k]) % 365);
      if (euro_near(d)) continue;
      if (i && season_pos(d) <= season_pos(r[i - 1].day)) continue;
      if (i + 1 < n && season_pos(d) >= season_pos(r[i + 1].day)) continue;
      r[i].day = d; moved++; break;
    }
  }
  return moved;
}
static void declash_log(uint16_t id, int moved)
{
  static uint16_t said[64]; static int nsaid = 0;
  if (!moved) return;
  for (int k = 0; k < nsaid; k++) if (said[k] == id) return;
  if (nsaid < 64) said[nsaid++] = id;
  logf("fl26swiss: reg %u -- %d league round(s) moved off European days", (unsigned)id, moved);
}

/* ---- two free days between a club's matches ----
 * Off the European day itself was not enough: a club played the league on Saturday, the
 * Champions League on Sunday... -- 3 matches in 4 days (Anderlecht, 5 October: league 20,
 * Champions League 21, league 23). Nobody plays Thursday and Saturday, or Sunday and Tuesday:
 * a league round of a league with European places, or with a league cup of ours, is now at
 * least REST days from every European day, national cup day (calendar case 6) and league cup
 * day its clubs may play on, and from the rounds either side of it. The rounds are moved as
 * little as they can be (the least days in all), in order, never before the first or after the
 * last day the calendar had -- a split league's second phase and a season's start stay put.
 * Measured on the Croatia world's calendars (calmodel): 194 rounds within two days of such a
 * day before, none after; the busiest day 264 matches of the 280 a day holds.
 * When no such calendar exists (a 46-round league with a league cup), the league cup is let
 * go first, then the national cups, then the rest is cut to two days, and last the old
 * rule -- off the European day itself -- stays. */
#define REST 3
#define CALENDAR_NATCUP_LIKE 23
static uint16_t g_calendar_natcup_shift = 0;
#define MAX_DATE_DAYS 32
static uint16_t g_calendar_natcup_days[MAX_DATE_DAYS];
static int g_calendar_natcup_ndays = 0;
static const uint16_t NATCUP_DAYS[12] = { 251, 254, 286, 289, 6, 9, 41, 44, 83, 86, 132, 135 };
/* The national cups' first round (calendar case 6: 251 and 254) is in one of the qualifying's six
   weeks every year (qr_day), and a club in both played them a day apart.  It moves to the first
   Tuesday and Friday after them that are three days clear of every European day of ours (the
   qualifying, the league phases' matchdays as swiss_day has them, the Conference League's) and
   three before the second round (286): 2025 Tuesday 23 and Friday 26 September.  The rounds
   after it keep the game's days.  natcup_fix rewrites a calendar of case 6 to them. */
static int natcup_clear(uint32_t d)
{
#define NC_FAR(e) do { uint32_t e_ = (e); if ((d > e_ ? d - e_ : e_ - d) < 3) return 0; } while (0)
  for (int s_ = 0; s_ < 3; s_++) for (int l = 0; l < 2; l++) NC_FAR(qr_day(s_, l));
  for (int i = 0; i < FL26_SWISS36_MATCHDAYS; i++) NC_FAR(swiss_day(i));
  for (int i = 0; i < FL26_SWISS6_MATCHDAYS; i++) NC_FAR(eday(UECL_DAYS[i]));
#undef NC_FAR
  return 1;
}
static uint32_t natcup_day(int i)
{
  if (i >= 2) return NATCUP_DAYS[i];
  static int sy_ = -1; static uint32_t a_ = 0;
  int sy = season_year();
  if (sy != sy_ || !a_) {
    a_ = NATCUP_DAYS[0];
    for (uint32_t a = NATCUP_DAYS[0] + 1; a + 3 + 3 <= NATCUP_DAYS[2]; a++)
      if (wday(a) == 1 && natcup_clear(a) && natcup_clear(a + 3)) { a_ = a; break; }
    sy_ = sy;
  }
  return a_ + (i ? 3u : 0u);
}
/* a calendar the game gave from case 6 -- every day one of NATCUP_DAYS, its first round's two
   among them -- gets the first round's days moved; answers how many dates moved */
static int natcup_fix(uint16_t id, void* vec)
{
  vec_t* v = (vec_t*)vec;
  size_t have = (v && v->b && v->e >= v->b) ? (size_t)(v->e - v->b) / sizeof(date_t) : 0;
  if (have < 2 || have > 64) return 0;
  date_t* r = (date_t*)v->b;
  int r1 = 0;
  for (size_t i = 0; i < have; i++) {
    int k = -1;
    for (int j = 0; j < 12; j++) if (r[i].day == NATCUP_DAYS[j]) k = j;
    if (k < 0) return 0;
    if (k < 2) r1++;
  }
  if (!r1) return 0;
  uint32_t a = natcup_day(0), b = natcup_day(1);
  if (a == NATCUP_DAYS[0]) return 0;
  int moved = 0;
  for (size_t i = 0; i < have; i++)
    if (r[i].day == NATCUP_DAYS[0]) { r[i].day = a; moved++; }
    else if (r[i].day == NATCUP_DAYS[1]) { r[i].day = b; moved++; }
  static uint16_t said[64]; static int nsaid = 0; int seen = 0;
  SAID_RESET(nsaid);
  for (int k = 0; k < nsaid; k++) if (said[k] == id) seen = 1;
  if (!seen && nsaid < 64) {
    said[nsaid++] = id;
    char b0[24], b1[24];
    logf("fl26swiss: reg %u -- national cup first round on %s and %s (days %u and %u, not 251 and 254): clear of the European days",
         (unsigned)id, dstr(a, b0, sizeof b0), dstr(b, b1, sizeof b1), a, b);
  }
  return moved;
}
/* ---- the cups of a league's country (0.2.2) ----
 * A league kept clear of our own cups, the European days and the August-May national cups
 * (case 6) only. A cup of the game's on any other calendar went unseen: Copa Chile's quarter-
 * final on 21 February (case 9: 16, 20, 23, ... 51, 58, 65, 72 ...) and a new Chile D2's first
 * round on the 22nd, its semi-final second leg on 14 March and the league on the 15th
 * (antonimus, 2026-10-12). The world file now names, for every league of a country with a cup,
 * the days its cups play on (`cupdays <reg> <day> ...`, leaguebuilder.cupdays_lines: the game's
 * cups by the dates the exe ships, a new country's by the cup each is dated like), and a round
 * keeps a day clear of each of them at every level but the last (rest_dates' level 3). */
#define CUPD_MAX 1024       /* 256 until the limits branch: a line per league with a country cup */
#define CUPD_DAYS 48
typedef struct { uint16_t reg, n, d[CUPD_DAYS]; } cupd_t;
static cupd_t g_cupd[CUPD_MAX]; static int g_ncupd = 0;
__declspec(dllexport) int fl26_swiss_cupdays(const uint16_t* v, int n)
{
  if ((!v && n) || n < 0) return -1;
  int k = 0;
  for (int i = 0; i < n && k < CUPD_MAX; i++) {
    const uint16_t* e = v + 50 * i;
    if (!e[0] || !e[1]) continue;
    cupd_t* c = &g_cupd[k];
    c->reg = e[0]; c->n = 0;
    for (int j = 0; j < e[1] && j < CUPD_DAYS; j++) if (e[2 + j] < 365) c->d[c->n++] = e[2 + j];
    if (c->n) k++;
  }
  g_ncupd = k;
  logf("fl26swiss: %d league(s) keep clear of their country's cup days", k);
  return k;
}
static const cupd_t* cupd_of(uint16_t id)
{
  for (int i = 0; i < g_ncupd; i++) if (g_cupd[i].reg == id) return &g_cupd[i];
  return 0;
}
/* ---- the game's own continental competitions (0.2.4) ----
 * A league of ours that sends clubs to the game's Libertadores (access LIB / LIBQ: the
 * qualifying round reg 8, the group stage reg 9, the knockout reg 10) kept no day clear of
 * them: Nacional played the Liga AUF Uruguaya on 22 September and a Libertadores quarter-final
 * the day after (antonimus, 2026-10-14). That fix (d31a0c1) knew the Libertadores alone; the
 * game's AFC Champions League (groups reg 15, knockout reg 16, access AFCL) and its Club World
 * Cup (reg 1) were as unseen. Each of the four now has its days:
 *   - the days the exe ships for it, from the date switch at 0x14157f810 (case 0: reg 1, case 3:
 *     regs 8, 9, 10, case 4: regs 15, 16; read from FL_2026.exe with tools/caltab.py's Image on
 *     2026-10-14), the AFC's on the midweek date_handler moves them to (afc_reg). A league is
 *     often dated before the competition is: the AFC Champions League gets its clubs and dates on
 *     1 January (sider.log: reg 15, then a calendar-year league of ours, then reg 16), long after
 *     every August-May league of a new career, so days noted in passing alone came too late;
 *   - whatever other day the game gives one of them as it goes by (cont_note, through the same
 *     stub as everything else), logged when it is not among the shipped ones.
 * Nothing here asks the game: asking from inside a league's call (lib_fetch) was dropped on
 * 2026-10-14 after the season-build crash at 0x140f325a4, later traced to player ids of 262144
 * and up.
 * A league keeps clear of a competition (gc_feeds) when a club of it can be there: a place of its
 * own on the access list, or its cup winner's (the place's alt league, the cup's divisions),
 * or, for the game's own leagues, the game's rights table (research-findings, "how the
 * Libertadores and the AFC CL find their clubs": Brazil, Argentina, Chile and region 23 to the
 * Libertadores, China, Japan and 162 to the AFC). Two days clear, as of a continental cup of
 * ours. The Club World Cup takes the champions of the Champions League, the Libertadores, the
 * AFC Champions League and the champions' cups of ours, so a league with a place in one of those
 * keeps a day clear of its four December days: one club a season, and the game's own big-league
 * calendar leaves that week open (case 5: 345, then 356). */
enum { GC_CWC = 0, GC_LIBQ, GC_LIB, GC_AFC, GC_N };
static const char* const GC_NAME[GC_N] = { "Club World Cup", "Libertadores qualifying", "Libertadores", "AFC Champions League" };
#define GC_MAX_DAYS 64
static uint16_t g_gcday[GC_N][GC_MAX_DAYS]; static int g_ngcday[GC_N];
/* which of them a regulation, or a group / tie row of one (id + 1024 n), is: -1 none */
static int gc_of(uint16_t id)
{
  uint16_t b = id > 1024 ? (uint16_t)(id & 0x3ff) : id;
  return b == 1 ? GC_CWC : b == 8 ? GC_LIBQ : b == 9 || b == 10 ? GC_LIB : b == 15 || b == 16 ? GC_AFC : -1;
}
static int gc_add(int g, uint32_t d)
{
  if (d >= 365) return 0;
  for (int j = 0; j < g_ngcday[g]; j++) if (g_gcday[g][j] == d) return 0;
  if (g_ngcday[g] >= GC_MAX_DAYS) return 0;
  g_gcday[g][g_ngcday[g]++] = (uint16_t)d;
  return 1;
}
static uint32_t midweek(uint32_t d);
static void gc_seed(void)
{
  static int done = 0;
  if (done) return;
  done = 1;
  /* the shipped arrays: 0x14298dea0 (reg 1), 0x14298e0f8 (8), 0x14298e0b0 (9), 0x14298e030 (10),
     0x14298e170 (15), 0x14298e110 (16) */
  static const uint16_t CWC_[] = { 348, 349, 351, 352 }, LIBQ_[] = { 34, 41 },
    LIB_[] = { 62, 76, 83, 104, 118, 139, 163, 223, 258, 265, 296, 303, 324, 331 },
    AFC_[] = { 55, 62, 76, 97, 111, 125, 139, 146, 237, 258, 272, 293, 310, 324 };
  for (size_t i = 0; i < sizeof CWC_ / sizeof CWC_[0]; i++) gc_add(GC_CWC, CWC_[i]);
  for (size_t i = 0; i < sizeof LIBQ_ / sizeof LIBQ_[0]; i++) gc_add(GC_LIBQ, LIBQ_[i]);
  for (size_t i = 0; i < sizeof LIB_ / sizeof LIB_[0]; i++) gc_add(GC_LIB, LIB_[i]);
  for (size_t i = 0; i < sizeof AFC_ / sizeof AFC_[0]; i++) gc_add(GC_AFC, midweek(AFC_[i]));
}
/* the dates the game just gave one of them: kept, each day once; said once a season per
   regulation, and again whenever a day was not known yet */
static void cont_note(uint16_t id, void* vec)
{
  int g = gc_of(id);
  if (g < 0 || !vec) return;
  gc_seed();
  vec_t* v = (vec_t*)vec;
  size_t have = (v->b && v->e >= v->b) ? (size_t)(v->e - v->b) / sizeof(date_t) : 0;
  const date_t* r = (const date_t*)v->b;
  char buf[GC_MAX_DAYS * 5 + 1]; size_t bl = 0; buf[0] = 0;
  int fresh = 0;
  for (size_t i = 0; i < have && i < GC_MAX_DAYS; i++) {
    fresh += gc_add(g, r[i].day);
    if (bl + 6 < sizeof buf) bl += (size_t)snprintf(buf + bl, sizeof buf - bl, "%s%u", bl ? " " : "", r[i].day);
  }
  static uint16_t said[32]; static int nsaid = 0; int seen = 0;
  SAID_RESET(nsaid);
  for (int k = 0; k < nsaid; k++) if (said[k] == id) seen = 1;
  if (!seen && id < 1024 && nsaid < 32) said[nsaid++] = id;
  else if (!fresh) return;
  if (have)
    logf("fl26swiss: the game's reg %u (%s) plays %u date(s): %s -- %d not among its shipped days; a league with a place in it keeps clear",
         (unsigned)id, GC_NAME[g], (unsigned)have, buf, fresh);
}
/* B254 (antonimus 26.10., beta 0f3b3ca): the game's national-team competitions were never in
 * busy_set, so a league of ours could play on their days -- a Copa America 2028 semi-final on
 * 18.07. and a Liga de Ascenso round the same day, for a manager of a club and of Chile; mato
 * 27.10.: "Moramo fixati ovo da se utakmice ne mogu sudarati s nacionalnim timovima". Their
 * regulations (CompetitionRegulation.bin, competitions 27-36): the World Cup 34/35, the
 * qualifiers 36-40, EURO 41/42, the Copa America 43/104, the Asian Cup 44/45, the Africa Cup of
 * Nations 46. Their days are asked of the game's own date function (it gave the Club World Cup
 * its shape from 34/35 since 0.2.0), on the first date asked on a day -- the season build --
 * before any league of ours is dated. Which years they are played in is the record's season year
 * (+0x2fc), a four-year cycle the game moves on itself (a 30-year Fast Forward, 28.10.: the World
 * Cup 2025, 2029, 2033 ... set on 5 August of that year): a day from August on is in that year,
 * one before August in the next (World Cup 2025 -> June-July 2026, Copa America 2027 -> July
 * 2028). A tournament day is kept clear only in its own year (a day of ours from today on is this
 * year, one before today next year); 65535 is a tournament not on the calendar yet. The qualifiers
 * (36-40) are the international windows, kept clear every year as real leagues stop for them.
 * Every league keeps them clear at every level (busy_days, rcal_cost): a club's players are called
 * up whatever its confederation. FL27's new World Cup dates come the same way. */
static const uint16_t NT_REGS[] = { 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 104, 44, 45, 46 };
#define NT_QUAL(id) ((id) >= 36 && (id) <= 40)
#define NT_MAX_DAYS 160
static int game_date(void);
static uint16_t g_ntday[NT_MAX_DAYS]; static int g_nntday = 0;    /* tournaments, this year's */
static uint16_t g_nqday[NT_MAX_DAYS]; static int g_nnqday = 0;    /* the qualifiers' windows */
static void nt_add(uint16_t* a, int* n, uint32_t d)
{
  for (int q = 0; q < *n; q++) if (a[q] == d) return;
  if (*n < NT_MAX_DAYS) a[(*n)++] = (uint16_t)d;
}
static void nt_sample(uint64_t reg, void* vec)
{
  static int key = -1000000, tl = -1;
  int k = abs_day();
  if (!vec || k < 0 || (k == key && tl == g_timeline)) return;
  key = k; tl = g_timeline; g_nntday = 0; g_nnqday = 0;
  vec_t* v = (vec_t*)vec;
  if (v->e < v->b) return;                         /* empty (b 0) on the first date of a day: fine */
  int gd = game_date(), t = today();
  int yr = gd >= 0 ? gd / 365 : -1;
  char buf[2][300]; size_t bl[2] = { 0, 0 }; buf[0][0] = buf[1][0] = 0;
  for (size_t i = 0; i < sizeof NT_REGS / sizeof NT_REGS[0]; i++) {
    uint16_t id = NT_REGS[i];
    const unsigned char* r = find_rec(id);
    unsigned year = r ? *(const uint16_t*)(r + 0x2fc) : 0xffff;
    size_t at = v->b ? (size_t)(v->e - v->b) : 0;
    ((date_fn)(uintptr_t)g_tramp_date)((reg & ~(uint64_t)0xffff) | id, vec);
    size_t have = (v->b && v->e >= v->b + at) ? (size_t)(v->e - v->b - at) / sizeof(date_t) : 0;
    const date_t* d = (const date_t*)(v->b + at);
    uint32_t lo = 365, hi = 0; int kept = 0;
    for (size_t j = 0; j < have; j++) {
      uint32_t day = d[j].day;
      if (day >= 365) continue;
      if (day < lo) lo = day;
      if (day > hi) hi = day;
      if (NT_QUAL(id)) { nt_add(g_nqday, &g_nnqday, day); kept++; continue; }
      if (year == 0xffff || yr < 0) continue;
      int when = (int)year + (day >= 213 ? 0 : 1), ours = yr + ((int)day >= t ? 0 : 1);
      if (when == ours) { nt_add(g_ntday, &g_nntday, day); kept++; }
    }
    if (v->b) v->e = v->b + at;                      /* the game's list appends: back as it was */
    int h = i >= 7;
    if (bl[h] + 40 < sizeof buf[h])
      bl[h] += (size_t)snprintf(buf[h] + bl[h], sizeof buf[h] - bl[h], " %u:%u/%u", (unsigned)id, year, (unsigned)have);
    if (have && bl[h] + 24 < sizeof buf[h])
      bl[h] += (size_t)snprintf(buf[h] + bl[h], sizeof buf[h] - bl[h], "(%u..%u)%s", lo, hi, kept ? "*" : "");
  }
  /* the players stay away from the first match to the final: the days between (a gap of up
     to 4 days, the group stage to the knockouts as well) are the tournament's too */
  for (int i = 0; i < g_nntday; i++)
    for (int j = 0; j < g_nntday; j++) {
      int a = g_ntday[i], b = g_ntday[j];
      if (b <= a || b - a > 5) continue;
      for (int x = a + 1; x < b; x++) nt_add(g_ntday, &g_nntday, (uint32_t)x);
    }
  logf("fl26swiss: national teams (B254) -- %d, day %d: %d tournament day(s) and %d window day(s) kept clear;%s",
       yr, t, g_nntday, g_nnqday, buf[0]);
  logf("fl26swiss: national teams (B254) -- (cont.)%s", buf[1]);
}
/* B254: a cup of ours keeps its world-file days (explicit or copied), so a round on a national-team
   day of this year moves off it: a week at a time first (the same weekday, its midweek or weekend
   slot), then a day, earlier first, never past its neighbouring rounds or onto another of its days */
static int nt_day(uint32_t d)
{
  for (int i = 0; i < g_nntday; i++) if (g_ntday[i] == d) return 1;
  for (int i = 0; i < g_nnqday; i++) if (g_nqday[i] == d) return 1;
  return 0;
}
static void nt_cup_clear(uint16_t id, void* vec)
{
  vec_t* v = (vec_t*)vec;
  size_t n = (v && v->b && v->e >= v->b) ? (size_t)(v->e - v->b) / sizeof(date_t) : 0;
  if (!n || (!g_nntday && !g_nnqday)) return;
  date_t* r = (date_t*)v->b;
  uint32_t first = 365; uint16_t fr = 0xffff;     /* the season starts on its first round's day */
  for (size_t q = 0; q < n; q++) if (r[q].day < 365 && r[q].round < fr) { fr = r[q].round; first = r[q].day; }
  if (first >= 365) return;
  static const int STEP[] = { -7, 7, -14, 14, -21, 21, -28, 28, -1, 1, -2, 2, -3, 3 };
  char buf[300]; size_t bl = 0; buf[0] = 0; int moved = 0, stuck = 0;
  for (size_t j = 0; j < n; j++) {
    uint32_t d = r[j].day;
    if (d >= 365 || !nt_day(d)) continue;
    /* its days in season order, from its first round's day */
#define SK(x) (((x) + 365u - first) % 365u)
    uint32_t lo = 0, hi = 365;                     /* keys strictly between its neighbours */
    for (size_t q = 0; q < n; q++) {
      if (q == j || r[q].day >= 365 || r[q].day == d) continue;
      uint32_t kq = SK(r[q].day);
      if (kq < SK(d) && kq + 1 > lo) lo = kq + 1;
      if (kq > SK(d) && kq < hi) hi = kq;
    }
    int to = -1;
    for (size_t s = 0; s < sizeof STEP / sizeof STEP[0] && to < 0; s++) {
      int c = (int)d + STEP[s];
      if (c < 0 || c >= 365 || nt_day((uint32_t)c)) continue;
      uint32_t kc = SK((uint32_t)c);
      if (kc < lo || kc >= hi) continue;
      to = c;
    }
#undef SK
    if (to < 0) { stuck++; continue; }
    for (size_t q = 0; q < n; q++) if (q != j && r[q].day == d && r[q].round == r[j].round) r[q].day = (uint32_t)to;
    r[j].day = (uint32_t)to; moved++;
    if (bl + 16 < sizeof buf) bl += (size_t)snprintf(buf + bl, sizeof buf - bl, " %u->%d", d, to);
  }
  static uint16_t said[64]; static int nsaid = 0, syr = -1, stl = -1;   /* said once a cup a year */
  if (syr != game_date() / 365 || stl != g_timeline) { nsaid = 0; syr = game_date() / 365; stl = g_timeline; }
  for (int q = 0; q < nsaid; q++) if (said[q] == id) return;
  if (nsaid < 64) said[nsaid++] = id;
  if (moved || stuck)
    logf("fl26swiss: reg %u -- %d cup date(s) moved off national-team days (B254)%s%s", (unsigned)id, moved, buf,
         stuck ? ", some left: no free day near" : "");
}
/* a division of the cup whose draw lists them (a cupdraw line's tiers) */
static int cupdraw_has(uint16_t cup, uint16_t id)
{
  for (int k = 0; k < g_ncd; k++)
    if (g_cd[k].reg == cup) for (int t = 0; t < g_cd[k].ntier; t++) if (g_cd[k].tier[t] == id) return 1;
  return 0;
}
/* a place of the access list can go to a club of league id: a position of its own, or its cup's
   winner (a division of the cup, or the alt league's next club when the winner has a place) */
static int place_for(const access_t* a, uint16_t id)
{
  if (a->rank) return a->reg == id;
  return a->alt == id || cupdraw_has(a->reg, id);
}
static int feeds_comp(uint16_t id, int comp)
{
  for (size_t i = 0; i < g_naccess; i++) if (g_access[i].comp == comp && place_for(&g_access[i], id)) return 1;
  return 0;
}
/* the game's own leagues its rights table sends to the Libertadores and the AFC Champions League */
static int game_rights(uint16_t id, int g)
{
  static const uint16_t LIBR[] = { 29, 30, 67, 166, 167 }, AFCR[] = { 52, 120, 162 };
  const uint16_t* t = g == GC_AFC ? AFCR : LIBR;
  size_t n = g == GC_AFC ? sizeof AFCR / sizeof AFCR[0] : sizeof LIBR / sizeof LIBR[0];
  for (size_t i = 0; i < n; i++) if (t[i] == id) return 1;
  return 0;
}
static int ccup_feeds(int k, uint16_t id);
static int gc_feeds(uint16_t id, int g)
{
  switch (g) {
  case GC_LIBQ: return feeds_comp(id, LIBQ);
  case GC_LIB:  return feeds_comp(id, LIB) || feeds_comp(id, LIBQ) || game_rights(id, GC_LIB);
  case GC_AFC:  return feeds_comp(id, AFCL) || game_rights(id, GC_AFC);
  case GC_CWC:
    if (feeds_comp(id, UCL) || feeds_comp(id, UCLQ) || gc_feeds(id, GC_LIB) || gc_feeds(id, GC_AFC)) return 1;
    for (int k = 0; k < g_nccup; k++)                 /* the champions' cups of ours (CAF ...) */
      if (!g_ccup[k].national && !ccup_tier(&g_ccup[k]) && ccup_feeds(k, id)) return 1;
    return 0;
  }
  return 0;
}
/* B35: which day table a cup of ours plays on (CCUP_GROUP_DAYS, CCUP_KO_DAYS): the weeks of the
   game's continental competition its leagues can send a club to as well -- each entry's league
   (a cup winner's entry: its alt league) as gc_feeds sees it, the access list and the game's
   rights table. Worked out once per g_ccup_gen: the league schedulers ask for the days often. */
static int ccup_region(ccup_t* c)
{
  if (c->region && c->rgen == g_ccup_gen) return c->region - 1;
  int lib = 0, afc = 0;
  for (int e = 0; e < c->n && e < CCUP_MAX_ENTRY; e++) {
    uint16_t lg = c->erank[e] ? c->ereg[e] : c->ealt[e];
    if (!lg) continue;
    lib |= gc_feeds(lg, GC_LIB);                       /* the qualifying round's leagues too */
    afc |= gc_feeds(lg, GC_AFC);
  }
  int cr = lib ? CR_LIB : afc ? CR_AFC : CR_NONE;
  c->region = (uint8_t)(cr + 1); c->rgen = g_ccup_gen;
  logf("fl26swiss: cup %u -- its leagues reach%s%s%s%s: %s", (unsigned)c->reg, lib ? " the Libertadores" : "",
       lib && afc ? " and" : "", afc ? " the AFC Champions League" : "", lib || afc ? "" : " no competition of the game",
       CR_NAME[cr]);
  if (lib && afc)
    logf("fl26swiss: cup %u -- no table is clear of both; the AFC Champions League's days are not kept clear",
         (unsigned)c->reg);
  return cr;
}
/* a club of league id can play in Europe: a place of its own, or its cup's (above), or the rcal
   line says so. UEFA's competitions only: a league with a Libertadores or AFC place was taken for
   a European one by the real calendars and kept clear of the Champions League's days for nothing */
static int rcal_eu(uint16_t id);
static int uefa_feeds(uint16_t id)
{
  if (rcal_eu(id)) return 1;
  for (size_t i = 0; i < g_naccess; i++) {
    int c = g_access[i].comp;
    if ((c == UCL || c == UEL || c == UECL || c == UCLQ || c == UELQ || c == UECLQ) && place_for(&g_access[i], id)) return 1;
  }
  return 0;
}
/* ---- every day a league's clubs may play on besides the league (0.2.4) ----
 * One list for both schedulers -- rest_dates (busy_days) and the real calendars (rcal_cost) --
 * so that neither knows a day the other does not: busy_days alone knew a calendar-year cup's
 * days, and the Copa AUF Uruguay's second round was played the day before a league round
 * (d31a0c1). Each day comes with its kind, and each scheduler lets the kinds go at its own
 * levels (busy_days, rcal_cost). */
enum {
  BZ_CONT,     /* a continental cup it feeds (ours or the game's), a pre-season cup it plays */
  BZ_CWC,      /* the game's Club World Cup */
  BZ_EURO,     /* a league phase, knockout or February play-off day of ours */
  BZ_QUAL,     /* an August qualifying round or play-off */
  BZ_NATCUP,   /* an August-May league's national cups (calendar case 6, natcup_day) */
  BZ_CALCUP,   /* a calendar-year league's cup (`dates <cup> like=23`) */
  BZ_CUPD,     /* its country's cups (cupdays) */
  BZ_LCUP,     /* its league cup of ours and the cup's pre-round */
  BZ_NT,       /* a match day of the game's national-team tournaments this year (nt_sample, B254) */
  BZ_NTQ       /* a day of their qualifiers' international windows, every year (B254) */
};
typedef struct { uint16_t day; uint8_t kind; } busy_t;
#define BUSY_MAX 1024
static int busy_set(uint16_t id, busy_t* out);
/* the days of a calendar-year league's cup, dated like the national cups (`dates <cup> like=23`,
   with or without explicit days): see cal_cup_days below the date lines */
static int cal_cup_days(uint16_t id, uint32_t* out, int cap);
static int ccup_of_league(int k, uint16_t id)
{
  for (int e = 0; e < g_ccup[k].n && e < CCUP_MAX_ENTRY; e++) if (g_ccup[k].ereg[e] == id) return 1;
  return 0;
}
/* a continental cup of ours can take a club of league id: a position of its own, or a cup winner's
   place (the cup's divisions, or the alt league's next club when the winner has a place) --
   ccup_of_league knew the positions only */
/* league id has a place in pre-round li: its own, or its cup winner's */
static int lpre_league(int li, uint16_t id)
{
  const lpre_t* l = &g_lpre[li];
  for (int e = 0; e < 2 * l->ties && e < 2 * LPRE_MAX; e++) {
    if (l->erank[e] ? l->ereg[e] == id : (l->ealt[e] == id || (l->ereg[e] && cupdraw_has(l->ereg[e], id)))) return 1;
  }
  return 0;
}
static int ccup_feeds(int k, uint16_t id)
{
  const ccup_t* c = &g_ccup[k];
  for (int e = 0; e < c->n && e < CCUP_MAX_ENTRY; e++) {
    if (c->ereg[e] == id) return 1;
    if (!c->erank[e] && (c->ealt[e] == id || cupdraw_has(c->ereg[e], id))) return 1;
  }
  /* 12.11.2026: a league whose only way into the cup is the cup's pre-round (30 African and 20
     CONCACAF champions of the GigaPack): its club plays the cup's days once it is through, and
     the league was not kept clear of them. Not the South American calendar's cups (cal): theirs
     are the Libertadores' weeks, kept clear as the Libertadores' own. */
  if (!c->cal)
    for (int li = 0; li < g_nlpre; li++)
      if (g_lpre[li].ko == c->ko && lpre_league(li, id)) return 1;
  return 0;
}
/* a pre-season cup that invites a club of league id: its days are that league's as well -- the
   Balkan Cup kept clear of the host's (HNL) days only, and the Bosnian league played the day
   after its semi-final and final (2026-10-08) */
#ifdef FL26_RCAL_TEST                    /* the calendar test harness: no game to ask */
int rcal_test_invites(int k, uint16_t id);
#endif
static int ccup_invites(int k, uint16_t id)
{
#ifdef FL26_RCAL_TEST
  return rcal_test_invites(k, id);
#endif
  for (int i = 0; i < g_ccup[k].nc && i < CCUP_MAX_ENTRY; i++)
    if (in_rec(id, canon_club(full_club(g_ccup[k].clubs[i])))) return 1;
  return 0;
}
static int cup_league(uint16_t id)
{
  for (int k = 0; k < g_nccup; k++) if (ccup_of_league(k, id)) return 1;
  return 0;
}
/* rest positions count from g_org: 1 July (182) for an August-May season, 1 January for a
   calendar-year one -- whichever keeps the league's rounds in order */
static uint32_t g_org = 182;
static uint32_t rpos(uint32_t d) { return (d + 365 - g_org) % 365; }
static int in_order(const date_t* r, uint32_t n)
{
  for (uint32_t i = 0; i < n; i++)
    if (r[i].day >= 365 || (i && rpos(r[i].day) <= rpos(r[i - 1].day))) return 0;
  return 1;
}
static void block(uint8_t* bad, uint32_t d, int buf)
{
  if (d >= 365) return;
  int p = (int)rpos(d);
  for (int k = -(buf - 1); k <= buf - 1; k++) if (p + k >= 0 && p + k < 365) bad[p + k] = 1;
}
/* the days a league's clubs may play on besides the league (busy_set), closed in bad (rest
   positions): level 0 all of them, 1 without the league cup, 2 without the national cups either,
   3 not its country's cup days either. The continental days -- ours, the game's, the European
   ones of a league with a European place, in either kind of season -- at every level. */
static void busy_days(uint16_t id, int level, int buf, uint8_t* bad)
{
  static busy_t z[BUSY_MAX];
  memset(bad, 0, 365);
  int n = busy_set(id, z);
  /* a national cup round two days from a league round, not three: with three, the one day left
     between New Year's round and the cup's (day 3), and between early February's and the cup's
     (day 38), took every league of a big world -- 330 matches asked of 280 (2026-10-08) */
  int cup = buf > 2 ? buf - 1 : buf;
  for (int i = 0; i < n; i++) {
    uint32_t d = z[i].day;
    switch (z[i].kind) {
    case BZ_CONT: case BZ_EURO: block(bad, d, buf); break;
    case BZ_CWC: block(bad, d, 2); break;
    /* the qualifying rounds three days clear at every level (a league round two days from one
       is a club's two matches in three days) */
    case BZ_QUAL: block(bad, d, buf < 3 ? 3 : buf); break;
    case BZ_CUPD: if (level < 3) block(bad, d, 2); break;       /* a day clear */
    case BZ_NATCUP: case BZ_CALCUP: if (level < 2) block(bad, d, cup); break;
    case BZ_LCUP: if (level < 1) block(bad, d, buf); break;
    case BZ_NT: block(bad, d, 2); break;                        /* a day clear, every level */
    case BZ_NTQ: block(bad, d, 1); break;                       /* the day itself */
    }
  }
}
/* the n rounds on free days at least `gap` apart, the least moved in all; -1 when there is no
   such calendar between the first and the last day. `jit` (0..2) is where a round would rather
   be: that many days after its own date. Every league took the same few days -- the first
   round of every 26-date calendar on day 261, the spring rounds on 65 and 114 -- and a world of
   34 leagues asked 325 matches of day 261 (2026-10-08, the modpack: 105 matches on 4 days that
   did not fit in the 280 and were never played, daydemand.py). Spread by the regulation id
   over a Saturday, a Sunday and a Monday, as real leagues are, no day holds a third of it. */
static int respace(date_t* r, uint32_t n, const uint8_t* bad, int gap, int jit)
{
  static int32_t cost[2][365]; static int16_t prev[64][365]; static int32_t o[64];
  const int32_t INF = 0x3fffffff;
  if (n < 2 || n > 64) return -1;
  if (!in_order(r, n)) return -1;
  /* the id's day only from a Saturday to its Sunday: a round is never pushed onto a weekday by it
     (a Saturday's to Monday, a Wednesday's to Friday) -- 0.2.0, with 792 matches a day */
  static int32_t jj[64];
  for (uint32_t i = 0; i < n; i++) {
    o[i] = (int32_t)rpos(r[i].day);
    jj[i] = jit && r[i].day < 365 && (r[i].day + 3) % 7 == 5 ? 1 : 0;
  }
  int lo = o[0], hi = o[n - 1];
  for (int p = 0; p < 365; p++) cost[0][p] = (p >= lo && p <= hi && !bad[p]) ? abs(p - o[0] - jj[0]) : INF;
  for (uint32_t i = 1; i < n; i++) {
    int32_t* c = cost[i & 1]; const int32_t* b = cost[(i - 1) & 1];
    int32_t best = INF; int arg = -1;
    for (int p = 0; p < 365; p++) {
      int q = p - gap;
      if (q >= 0 && b[q] < best) { best = b[q]; arg = q; }
      c[p] = INF; prev[i][p] = -1;
      if (p >= lo && p <= hi && !bad[p] && best < INF) { c[p] = best + abs(p - o[i] - jj[i]); prev[i][p] = (int16_t)arg; }
    }
  }
  const int32_t* last = cost[(n - 1) & 1];
  int p = -1;
  for (int k = 0; k < 365; k++) if (last[k] < INF && (p < 0 || last[k] < last[p])) p = k;
  if (p < 0) return -1;
  int moved = 0;
  for (int i = (int)n - 1; i >= 0; i--) {
    uint32_t d = ((uint32_t)p + g_org) % 365;
    if (r[i].day != d) { r[i].day = d; moved++; }
    if (i) p = prev[i][p];
  }
  return moved;
}
/* ---- leagues that start in July ----
 * Every league of the game starts on the big leagues' calendar, the third week of August, and
 * the first three weeks of July had not one match. In reality Poland, Denmark, Romania, Serbia,
 * Croatia, Belgium ... kick off in mid or late July. The world file names them with the day
 * their first round should be on (`july <reg> <day>`, fl26_swiss_july); their rounds before New
 * Year come earlier by whole weeks -- the first by the most, a round near New Year not at all --
 * so weekdays and the order stay and the gaps only grow. Only at the July rollover (day 181):
 * a new career is built on day 216, and a round before that would never be played (GitHub #27).
 * Measured 2026-10-05 (run16): our leagues are dated at the rollover and their July rounds are
 * played and stay in the table through the day-216 build. The game's own leagues go through it too
 * (sider.log of players: "reg 22 -- starts in July: first round day 219, was 233"), so a league
 * whose country's super cup the game plays before its first round starts no earlier than a week
 * after that cup (B36). */
#define MAX_JULY 512
static uint16_t g_july[MAX_JULY][2]; static int g_njuly = 0;
__declspec(dllexport) int fl26_swiss_july(const uint16_t* v, int n)
{
  if ((!v && n) || n < 0) return -1;
  if (n > MAX_JULY) n = MAX_JULY;
  for (int i = 0; i < n; i++) { g_july[i][0] = v[2 * i]; g_july[i][1] = v[2 * i + 1]; }
  g_njuly = n;
  logf("fl26swiss: %d league(s) start in July", n);
  return n;
}
static void july_start(uint16_t id, date_t* r, uint32_t n, int seen)
{
  uint32_t want = 0;
  for (int i = 0; i < g_njuly; i++) if (g_july[i][0] == id) want = g_july[i][1];
  if (!want || n < 2) return;
  int t = today();
  if (t < 175 || t >= BUILD_DAY) {
    if (!seen) logf("fl26swiss: reg %u -- dated on day %d, not at the July rollover; starts as the game dates it",
                    (unsigned)id, t);
    return;
  }
  uint32_t f = season_pos(r[0].day), w = season_pos(want), ny = 183;   /* New Year's position */
  if (r[0].day >= 365 || w >= f || f >= ny) return;
  /* a cup of its country the game plays before the first round stays before it, a week clear:
     the Supertaça on 13 and 16 August, Liga Portugal's first round on 22 August -- brought
     forward to 8 August it came after the super cup (Hugo Freixo, B36). The same for the
     Netherlands, Turkey, Russia, Belgium and France: those keep the game's start */
  const cupd_t* c = cupd_of(id);
  uint32_t lim = w;
  for (int j = 0; c && j < c->n; j++) {
    uint32_t q = season_pos(c->d[j]);
    if (q >= w && q < f && q + 7 > lim) lim = q + 7;
  }
  if (lim > w) {
    if (!seen) logf("fl26swiss: reg %u -- a cup of its country plays on day %u before its first round (day %u): "
                    "starts no earlier than a week after it", (unsigned)id, (unsigned)((lim - 7 + 182) % 365),
                    (unsigned)r[0].day);
    w = lim;
    if (w >= f || (f - w) / 7 == 0) return;
  }
  uint32_t weeks = (f - w) / 7, first = r[0].day;
  for (uint32_t i = 0; i < n; i++) {
    uint32_t p = season_pos(r[i].day);
    if (r[i].day >= 365 || p >= ny) break;
    uint32_t k = (weeks * (ny - p) + (ny - f) / 2) / (ny - f);           /* rounded, weeks..0 */
    int32_t d = (int32_t)r[i].day - 7 * (int32_t)k;
    r[i].day = (uint32_t)(d < 0 ? d + 365 : d);
  }
  if (!seen) logf("fl26swiss: reg %u -- starts in July: first round day %u, was %u", (unsigned)id, r[0].day, first);
}

static void rest_dates(uint16_t id, date_t* r, uint32_t n)
{
  static const int LEVEL[5] = { 0, 1, 2, 2, 3 }, GAP[5] = { REST, REST, REST, REST - 1, REST - 1 };
  static uint8_t bad[365];
  static uint16_t said[128]; static int nsaid = 0;
  int seen = 0;
  SAID_RESET(nsaid);
  for (int k = 0; k < nsaid; k++) if (said[k] == id) seen = 1;
  if (!seen && nsaid < 128) said[nsaid++] = id;
  july_start(id, r, n, seen);
  g_org = 182;
  if (!in_order(r, n)) g_org = 0;
  if (!in_order(r, n)) {
    g_org = 182;
    if (!seen) logf("fl26swiss: reg %u -- rounds not in date order; off European days only", (unsigned)id);
    declash_log(id, declash(r, n));
    return;
  }
  for (int t = 0; t < 5; t++) {
    busy_days(id, LEVEL[t], GAP[t], bad);
    int moved = respace(r, n, bad, GAP[t], id % 3);
    if (moved < 0) continue;
    g_org = 182;
    if (!seen)
      logf("fl26swiss: reg %u -- %d of %u round(s) moved for %d day(s) between matches%s", (unsigned)id, moved,
           (unsigned)n, GAP[t], t == 1 ? " (not around the league cup)" : t == 4 ? " (not around any cup)" : t >= 2 ? " (not around the cups)" : "");
    return;
  }
  g_org = 182;
  int kept = declash_near(r, n);
  if (!seen) logf("fl26swiss: reg %u -- no calendar with free days between matches; %d round(s) moved a day clear of European days",
                  (unsigned)id, kept);
  declash_log(id, declash(r, n));
}

/* ---- real calendars (0.2.0) ----
 * A league with an `rcal` line in the world file (tools/realcal.py: the real calendar of its
 * country and tier, else its confederation's) is dated from that line alone, not from the big
 * leagues' calendar moved about: its first round on the real first weekend, its last on the real
 * last one, nothing in its winter break, every round on its own weekdays (a Saturday and Sunday,
 * a Friday where the league really plays one) and spread evenly over the weeks it has -- in the
 * first season too, and the same every season after it. The rounds go on the free days nearest
 * to that, two days at least between them:
 *   - never within two days of a European day when a club of the league can be in Europe (a
 *     place of its own, or its country's cup winner's: the line's last field, or an access
 *     line) -- Saturday before Tuesday, Sunday after Thursday --, a league phase or knockout
 *     day two days off only when no other calendar fits (the last level); the August
 *     qualifying rounds and play-offs are midweek and closed two days either side always;
 *   - never within a day of a national cup day, of its league cup's days, two of a pre-season cup
 *     its clubs play or a continental cup it feeds;
 *   - a weekday that is not its own only when the season is too short for its rounds (46 rounds
 *     between August and early May: the English Tuesdays).
 * A new career is built on day 216 (5 August): a league that really starts in July starts on the
 * first weekend after it in the first season (RCAL_SEASON1), the real one from the July rollover
 * on. Weekdays are the season's own (wday: 2025/26 from the game date's year), and so are the
 * fixed European days, moved within their week (eday). */
#define MAX_RCAL 512
#define RCAL_SEASON1 219          /* Saturday 8 August, the first weekend of a new career */
typedef struct { uint16_t reg, first, last, b0, b1, days, also, eu; } rcal_t;
static rcal_t g_rcal[MAX_RCAL]; static int g_nrcal = 0;
__declspec(dllexport) int fl26_swiss_rcal(const uint16_t* v, int n)
{
  if ((!v && n) || n < 0) return -1;
  int k = 0;
  for (int i = 0; i < n && k < MAX_RCAL; i++) {
    const uint16_t* e = v + 8 * i;
    if (!e[0] || e[1] >= 365 || e[2] >= 365 || e[3] >= 365 || e[4] >= 365 || e[1] == e[2] || !(e[5] & 0x7f)) continue;
    rcal_t* c = &g_rcal[k++];
    c->reg = e[0]; c->first = e[1]; c->last = e[2]; c->b0 = e[3]; c->b1 = e[4];
    c->days = e[5] & 0x7f; c->also = e[6] & 0x7f; c->eu = e[7];
  }
  g_nrcal = k;
  logf("fl26swiss: %d league(s) on a real calendar", k);
  return k;
}
static const rcal_t* rcal_of(uint16_t id)
{
  for (int i = 0; i < g_nrcal; i++) if (g_rcal[i].reg == id) return &g_rcal[i];
  return 0;
}
/* the rcal line names the league one whose clubs play in Europe (its last field) */
static int rcal_eu(uint16_t id)
{
  const rcal_t* c = rcal_of(id);
  return c && c->eu;
}
/* every day a European competition of ours plays: the league phases and the knockouts
   (quals 0), or the August qualifying rounds and play-offs (quals 1) */
static int uefa_days(uint32_t* out, int cap, int quals)
{
  int n = 0;
#define UD(d) do { if (n < cap) out[n++] = (d); } while (0)
  if (quals) {
    for (int c = 0; c < 3; c++) for (int i = 0; i < 2; i++) UD(qr_day(c, i));
    for (int i = 0; i < 2; i++) if (qr_day(3, i)) UD(qr_day(3, i));   /* FL27's July first round */
    return n;
  }
  for (int i = 0; i < FL26_SWISS36_MATCHDAYS; i++) UD(swiss_day(i));
  for (int i = 0; i < FL26_SWISS6_MATCHDAYS; i++) UD(eday(UECL_DAYS[i]));
  for (int c = 0; c < 3; c++) {
    for (int i = 0; i < 7; i++) UD(eday(KO_DAYS[c][i]));
    for (int i = 0; i < 2; i++) UD(eday(CUPS[c].days[i]));
  }
#undef UD
  return n;
}
/* every European day of ours as a league of this kind of season meets it: an August-May league
   its season's (uefa_days); a calendar-year league (g_org 0) the spring of the European season
   that ends in its year and the summer and autumn of the one that starts in it -- a Norwegian
   club in the August qualifying rounds or the autumn league phase plays them in the middle of its
   own season. Their weekdays are each season's own (eday, qr_day), so each half is taken with
   its own season's year: a calendar-year league is dated in January, when the game's season year
   is still the one before (g_sy_force). */
static int uefa_days_of(uint32_t* out, int cap, int quals)
{
  int sy = season_year();
  if (g_org != 0 || !sy) return uefa_days(out, cap, quals);
  int t = today(), y = t >= 0 && t < 175 ? sy + 1 : sy;      /* the calendar year it plays */
  uint32_t tmp[96]; int n = 0;
  for (int half = 0; half < 2; half++) {
    g_sy_force = half ? y : y - 1;
    int m = uefa_days(tmp, 96, quals);
    for (int i = 0; i < m && n < cap; i++) if ((tmp[i] >= 181) == half) out[n++] = tmp[i];
  }
  g_sy_force = 0;
  return n;
}
static int busy_set(uint16_t id, busy_t* out)
{
  static uint16_t seen[365];                           /* a bit per kind: each day of a kind once */
  int n = 0;
  memset(seen, 0, sizeof seen);
#define BZ(d, k) do { uint32_t d_ = (d); if (d_ < 365 && !(seen[d_] >> (k) & 1) && n < BUSY_MAX) { \
    seen[d_] |= (uint16_t)(1 << (k)); out[n].day = (uint16_t)d_; out[n].kind = (uint8_t)(k); n++; } } while (0)
  for (int k = 0; k < g_nccup; k++) {
    const ccup_t* x = &g_ccup[k];
    if (!x->national && ccup_feeds(k, id)) {           /* a continental cup of ours it feeds */
      if (x->groups) for (int i = 0; i < 6; i++) BZ(ccup_day(x, 0, i), BZ_CONT);
      for (int i = 0; i < (x->nd ? x->nd : 7) && i < CCUP_MAX_DAYS; i++) BZ(ccup_day(x, 1, i), BZ_CONT);
      if (!x->cal)                                     /* and its pre-round's, for a league that plays it */
        for (int li = 0; li < g_nlpre; li++)
          if (g_lpre[li].ko == x->ko && lpre_league(li, id)) { BZ(g_lpre[li].days[0], BZ_CONT); BZ(g_lpre[li].days[1], BZ_CONT); }
    } else if (x->national && x->nc && (ccup_of_league(k, id) || ccup_invites(k, id))) {
      /* a pre-season cup (invited clubs): its few July days, for the host's league and each
         invited club's -- any world's cup, not one */
      for (int i = 0; i < x->nd && i < CCUP_MAX_DAYS; i++) BZ(x->days[i], BZ_CONT);
    } else if (x->national && !x->nc && ccup_of_league(k, id)) {   /* its league cup */
      for (int i = 0; i < x->nd && i < CCUP_MAX_DAYS; i++) BZ(x->days[i], BZ_LCUP);
      for (int li = 0; li < g_nlpre; li++)
        if (g_lpre[li].ko == x->ko) { BZ(g_lpre[li].days[0], BZ_LCUP); BZ(g_lpre[li].days[1], BZ_LCUP); }
    }
  }
  gc_seed();                                           /* the game's continental competitions */
  for (int g = 0; g < GC_N; g++)
    if (g_ngcday[g] && gc_feeds(id, g))
      for (int i = 0; i < g_ngcday[g]; i++) BZ(g_gcday[g][i], g == GC_CWC ? BZ_CWC : BZ_CONT);
  /* the European days, for a league that sends clubs to Europe only: a second division blocked
     by them as well had one day left between a midweek round and a European week, and every
     league of a big world met on it (2026-10-08, the modpack: day 65 asked 403 matches of 280) */
  if (uefa_feeds(id)) {
    uint32_t ud[96]; int nu = uefa_days_of(ud, 96, 0);
    for (int i = 0; i < nu; i++) BZ(ud[i], BZ_EURO);
    nu = uefa_days_of(ud, 96, 1);
    for (int i = 0; i < nu; i++) BZ(ud[i], BZ_QUAL);
  }
  for (int i = 0; i < g_nntday; i++) BZ(g_ntday[i], BZ_NT);   /* every league: its players are called up */
  for (int i = 0; i < g_nnqday; i++) BZ(g_nqday[i], BZ_NTQ);
  const cupd_t* cd = cupd_of(id);                      /* its country's cups */
  if (cd) for (int i = 0; i < cd->n; i++) BZ(cd->d[i], BZ_CUPD);
  if (g_org == 182) {                                  /* an August-May league's country's */
    for (int i = 0; i < 12; i++) BZ(natcup_day(i), BZ_NATCUP);
  } else {                                             /* a calendar-year league's own cup */
    uint32_t cc[MAX_DATE_DAYS + 12]; int nc = cal_cup_days(id, cc, MAX_DATE_DAYS + 12);
    for (int i = 0; i < nc; i++) BZ(cc[i], BZ_CALCUP);
  }
#undef BZ
  return n;
}
/* B329 (05.11., the 120k world of FL27): a real calendar is the same days for every league of its
   line, so fifteen leagues of one region took the same 46 days and two days asked 835 and 807
   matches of a 792-id day; the scheduler dropped the rest without a word (339 matches dated and
   never played). So a day costs what is already on it: the calendar's own count of the day, read
   when the league is dated (the leagues dated before it are on the days by then). A day that the
   league's round would bring within LOAD_SPARE of the day's ids is closed. */
#define LOAD_W     16              /* a full day costs as much as another weekday and more */
#define LOAD_SPARE 24              /* ids kept free for the cups dated after the leagues */
#ifdef FL26_RCAL_TEST
int rcal_test_dayload(int d);
int rcal_test_round(uint16_t id);
#endif
static int day_cap(void) { return lay_day_ids(); }
static int day_load(int d)         /* the ids on calendar day d; -1 unknown */
{
#ifdef FL26_RCAL_TEST
  return rcal_test_dayload(d);
#endif
  unsigned char* o = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
  unsigned char* blk = o ? *(unsigned char**)(o + 0x48) : 0;
  int cap = day_cap();
  if (!blk || d < 0 || d >= 365 || cap <= 0) return -1;
  int n = *(uint16_t*)(blk + lay_calendar() + (size_t)d * lay_day_size() + lay_day_count());
  return n > cap ? cap : n;
}
static int round_matches(uint16_t id)   /* a round of the league: half its clubs */
{
#ifdef FL26_RCAL_TEST
  return rcal_test_round(id);
#endif
  unsigned char* rec = get_rec(id);
  return rec ? (int)(*(uint32_t*)(rec + 0x30c) & 0x7f) / 2 : 0;
}
/* the leagues dated the same day are not all on the days yet when the next one is dated (the 120k
   world: 624 matches of rcal leagues and 160 of the game's on day 311 of 792, 7 dropped), so each
   pick is counted on its days at once: a day is at least what it held at the day's first dating
   plus the rounds picked onto it since (picks filed before that read count twice: a day too few) */
static int g_plan[365], g_snap[365], g_plan_aday = -1, g_plan_tl = -1;
static void plan_today(void)
{
  int a = abs_day();
  if (a == g_plan_aday && g_timeline == g_plan_tl) return;
  g_plan_aday = a; g_plan_tl = g_timeline;
  for (int d = 0; d < 365; d++) { g_plan[d] = 0; g_snap[d] = -1; }  /* taken at a day's first read */
}
static void plan_add(uint16_t id, const date_t* r, uint32_t n)
{
  int per = round_matches(id);
  plan_today();
  for (uint32_t i = 0; i < n && per > 0; i++) g_plan[r[i].day % 365] += per;
}
static void load_cost(uint16_t id, int32_t* pen)
{
  int per = round_matches(id), cap = day_cap();
  plan_today();
#ifdef FL26_RCAL_TEST
  cap = 792;
#endif
  if (per <= 0 || cap <= 0) return;
  for (int p = 0; p < 365; p++) {
    if (pen[p] < 0) continue;
    int d = (p + (int)g_org) % 365, l = day_load(d);
    if (l < 0) return;
    if (g_snap[d] < 0) g_snap[d] = l;
    if (g_snap[d] + g_plan[d] > l) l = g_snap[d] + g_plan[d];
    if (l + per > cap - LOAD_SPARE) pen[p] = -1;
    else pen[p] += l * LOAD_W / cap;
  }
}
/* the cost of a round on each day (rpos, g_org): -1 never; `strict` 0 lets the cups go */
static void rcal_cost(uint16_t id, const rcal_t* c, int strict, int euhard, int32_t* pen)
{
  static const int32_t OTHER[7] = { 8, 12, 12, 14, 8, 6, 6 };    /* Mon .. Sun, not its own */
  for (int p = 0; p < 365; p++) {
    uint32_t d = (uint32_t)(p + (int)g_org) % 365;
    int w = wday(d);
    pen[p] = (c->days >> w & 1) ? 0 : (c->also >> w & 1) ? 2 : OTHER[w];
  }
  if (c->b0 || c->b1) {                              /* the break, both ends in it */
    int a = (int)rpos(eday(c->b0)), b = (int)rpos(eday(c->b1));
    for (int p = 0; p < 365; p++) if (a <= b ? p >= a && p <= b : p >= a || p <= b) pen[p] = -1;
  }
#define RNEAR(d, hard, soft) do { if ((d) < 365) { int q_ = (int)rpos(d); \
    for (int k_ = -(soft); k_ <= (soft); k_++) { int p_ = q_ + k_; if (p_ < 0 || p_ >= 365 || pen[p_] < 0) continue; \
      if (abs(k_) <= (hard)) pen[p_] = -1; else pen[p_] += 10; } } } while (0)
  /* the same days busy_days knows (busy_set), each kind as hard here:
     - a continental cup (ours, the game's Libertadores and AFC Champions League) and a pre-season
       cup: two days clear;
     - the Club World Cup: a day clear, two days a cost;
     - Two full days between a European match and a league round (0.2.0): Tuesday's after
       Saturday's, Sunday's after Thursday's. Only the last level (one day between matches) lets a
       league phase or knockout day come within two days. The August qualifying rounds and
       play-offs are midweek (qr_day) and leave a weekend day three days clear in every week, so
       they are closed two days either side at every level: a club in a qualifier never plays the
       league within two days of it (2026-10-08: Dinamo, Wednesday's second leg and Thursday's
       league round). Until 0.2.0 only their own day was closed -- they fell on weekends then.
     - its country's cups (cupdays) and a calendar-year league's cup: a day clear at every level,
       two when strict; the August-May national cups and its league cup only when strict. */
  static busy_t z[BUSY_MAX];
  int nz = busy_set(id, z);
  for (int i = 0; i < nz; i++) {
    uint32_t d = z[i].day;
    switch (z[i].kind) {
    case BZ_CONT: case BZ_QUAL: RNEAR(d, 2, 2); break;
    case BZ_CWC: RNEAR(d, 1, 2); break;
    case BZ_EURO: RNEAR(d, euhard, 2); break;
    case BZ_CUPD: case BZ_CALCUP: RNEAR(d, 1, strict ? 2 : 1); break;
    case BZ_NATCUP: case BZ_LCUP: if (strict) RNEAR(d, 1, 2); break;
    case BZ_NT: RNEAR(d, 1, 2); break;
    case BZ_NTQ: RNEAR(d, 0, 1); break;
    }
  }
#undef RNEAR
  load_cost(id, pen);
}
/* the n rounds on the cheapest days at least gap apart, each near its share of the season (its
   weeks without the break, evenly); the number of near-European rounds into *soft. -1: none */
static int rcal_pick(const int32_t* pen, int lo, int hi, int gap, date_t* r, uint32_t n, int* soft)
{
  static int32_t cost[2][365]; static int16_t prev[64][365]; static int32_t eff[365];
  const int32_t INF = 0x3fffffff;
  if (n < 2 || n > 64 || lo < 0 || hi >= 365 || hi <= lo) return -1;
  int e = 0;
  for (int p = 0; p < 365; p++) { eff[p] = e; if (p >= lo && p <= hi && pen[p] >= 0) e++; }
  int span = eff[hi];                                  /* playable days from lo to hi */
  int last = hi + 2 < 365 ? hi + 2 : 364;              /* the last weekend may slip a day or two */
  for (int i = 0; i < (int)n; i++) {
    int32_t* c = cost[i & 1]; const int32_t* b = cost[(i - 1) & 1];
    int t = (int)(((int64_t)i * span * 2 + (n - 1)) / (2 * (int64_t)(n - 1)));   /* rounded */
    int32_t best = INF; int arg = -1;
    for (int p = 0; p < 365; p++) {
      int q = p - gap;
      if (i && q >= 0 && b[q] < best) { best = b[q]; arg = q; }
      c[p] = INF; prev[i][p] = -1;
      if (p < lo || p > last || pen[p] < 0) continue;
      if (i && best >= INF) continue;
      c[p] = (i ? best : 0) + abs(eff[p] - t) + pen[p];
      prev[i][p] = (int16_t)arg;
    }
  }
  const int32_t* f = cost[(n - 1) & 1];
  int p = -1;
  for (int k = 0; k < 365; k++) if (f[k] < INF && (p < 0 || f[k] < f[p])) p = k;
  if (p < 0) return -1;
  int moved = 0; *soft = 0;
  for (int i = (int)n - 1; i >= 0; i--) {
    uint32_t d = ((uint32_t)p + g_org) % 365;
    if (r[i].day != d) moved++;
    r[i].day = d;
    if (pen[p] >= 10) (*soft)++;
    if (i) p = prev[i][p];
  }
  return moved;
}
/* B329: the game asks a league's dates once for every match it files, so with the day's load in
   the cost every ask after the first would see the league's own matches and move its rounds. The
   days picked on the first ask are kept for that day of that timeline, by the league and the
   shape of its calendar line, and every later ask that day gets the same ones. */
#define RMEMO 512
static struct { uint16_t id, n, first, last, b0, b1, days, also; int aday, tl, moved; uint16_t d[64]; } g_rmemo[RMEMO];
static int g_nrmemo = 0, g_rmemo_on = 1;
static int rmemo_find(uint16_t id, const rcal_t* c, uint32_t n)
{
  int a = abs_day();
  for (int i = 0; i < g_nrmemo; i++) {
    if (g_rmemo[i].id != id || g_rmemo[i].n != n || g_rmemo[i].first != c->first || g_rmemo[i].last != c->last
        || g_rmemo[i].b0 != c->b0 || g_rmemo[i].b1 != c->b1 || g_rmemo[i].days != c->days || g_rmemo[i].also != c->also)
      continue;
    return g_rmemo[i].aday == a && g_rmemo[i].tl == g_timeline ? i : -2 - i;
  }
  return -1;
}
static int rcal_pick_days(uint16_t id, const rcal_t* c, date_t* r, uint32_t n, int seen);
static int rcal_dates(uint16_t id, const rcal_t* c, date_t* r, uint32_t n, int seen)
{
  if (!g_rmemo_on || n > 64) return rcal_pick_days(id, c, r, n, seen);
  int k = rmemo_find(id, c, n);
  if (k >= 0) {
    for (uint32_t i = 0; i < n; i++) r[i].day = g_rmemo[k].d[i];
    return g_rmemo[k].moved;
  }
  int moved = rcal_pick_days(id, c, r, n, seen);
  if (moved < 0) return moved;
  if (k == -1) k = g_nrmemo < RMEMO ? g_nrmemo++ : (int)((uint32_t)id % RMEMO);
  else k = -2 - k;
  g_rmemo[k].id = id; g_rmemo[k].n = (uint16_t)n; g_rmemo[k].first = c->first; g_rmemo[k].last = c->last;
  g_rmemo[k].b0 = c->b0; g_rmemo[k].b1 = c->b1; g_rmemo[k].days = c->days; g_rmemo[k].also = c->also;
  g_rmemo[k].aday = abs_day(); g_rmemo[k].tl = g_timeline; g_rmemo[k].moved = moved;
  for (uint32_t i = 0; i < n; i++) g_rmemo[k].d[i] = (uint16_t)r[i].day;
  plan_add(id, r, n);
  return moved;
}
static int rcal_pick_days(uint16_t id, const rcal_t* c, date_t* r, uint32_t n, int seen)
{
  static int32_t pen[365];
  int cy = c->first < c->last;
  g_org = cy ? 0 : 182;
  /* the line's days are 2026's (realcal.py): on the same weekdays of this season */
  int lo = (int)rpos(eday(c->first)), hi = (int)rpos(eday(c->last)), t = today();
  if (cy && lo < CAL_FIRST) lo = CAL_FIRST;           /* a January league joins its season in February */
  if (!cy && !(t >= 175 && t < BUILD_DAY) && (int)rpos(eday(RCAL_SEASON1)) > lo) lo = (int)rpos(eday(RCAL_SEASON1));
  static const int RSTRICT[3] = { 1, 0, 0 }, RGAP[3] = { REST, REST, REST - 1 }, REU[3] = { 2, 2, 1 };
  int moved = -1, soft = 0, lv = 0;
  for (; lv < 3 && moved < 0; lv++) {
    rcal_cost(id, c, RSTRICT[lv], REU[lv], pen);
    moved = rcal_pick(pen, lo, hi, RGAP[lv], r, n, &soft);
  }
  g_org = 182;
  if (moved < 0) {
    if (!seen) logf("fl26swiss: reg %u -- no real calendar fits %u rounds between days %u and %u; dated the old way",
                    (unsigned)id, (unsigned)n, eday(c->first), eday(c->last));
    return -1;
  }
  if (!seen) {
    int wk = 0;
    for (uint32_t i = 0; i < n; i++) wk += c->days >> wday(r[i].day) & 1 || c->also >> wday(r[i].day) & 1;
    char b0[24], b1[24];
    logf("fl26swiss: reg %u -- real calendar: %u rounds, first %s, then %s, days %u..%u (wanted %u..%u%s), %d on its weekdays, %d on a costly day (another weekday, two days from a cup)%s",
         (unsigned)id, (unsigned)n, dstr(r[0].day, b0, sizeof b0), dstr(r[1].day, b1, sizeof b1), r[0].day, r[n - 1].day, eday(c->first), eday(c->last), lo > (int)rpos(eday(c->first)) && !cy ? ", a new career's first weekend" : "",
         wk, soft, lv > 1 ? (lv > 2 ? " (one day between matches)" : " (cups let go)") : "");
  }
  return moved;
}
/* every league, the game's and ours: a round robin of four clubs or more, told by its legs
   (a knockout's are 0) and a calendar of 9 dates or more (a cup group's has 6). It read a type
   at +0x09, where the file's record has it; the live record has its name there, so no league
   of the game's was ever spaced (2026-10-08: the Bundesliga, the Super Lig and the Pro League
   on the January Champions League day 20). The club count is no test of the calendar: the
   Bundesliga's record says 20 and its calendar has the 34 rounds of 18. */
static int rest_league(uint16_t id, size_t have)
{
  unsigned char* rec = get_rec(id);
  if (!rec) return 0;
  uint32_t clubs = *(uint32_t*)(rec + 0x30c) & 0x7f, legs = *(uint32_t*)(rec + 0x308) >> 29;
  return clubs >= 4 && legs && have >= 9;
}
/* B283 (Daemon, 29.10.): the first round each league of ours was last dated with. Its super cup
 * (aug_scup_before_league) is dated as the shipped one, mid-August, and a league that starts in
 * July -- a real calendar or a `july` line: the Romanian one on 11 July -- had six rounds played
 * before it. The league is dated first: at the July rollover (day 181) before the super cup is
 * filled (day 182 on), at a new career's build before the first day's fill. */
#define MAX_LFIRST 512
static struct { uint16_t id, day; } g_lfirst[MAX_LFIRST];
static int g_nlfirst = 0;
static void note_first_round(uint16_t id, const date_t* r, uint32_t n)
{
  uint32_t best = 0xffff;
  for (uint32_t i = 0; i < n; i++)
    if (r[i].day < 365 && (best == 0xffff || season_pos(r[i].day) < season_pos(best))) best = r[i].day;
  if (best == 0xffff) return;
  int k = 0;
  while (k < g_nlfirst && g_lfirst[k].id != id) k++;
  if (k == g_nlfirst) { if (g_nlfirst >= MAX_LFIRST) return; g_nlfirst++; }
  g_lfirst[k].id = id;
  g_lfirst[k].day = (uint16_t)best;
}
static void league_rest(uint16_t id, date_t* r, uint32_t n)
{
  const rcal_t* c = rcal_of(id);
  int done = 0;
  if (c) {
    static uint16_t said[MAX_RCAL]; static int nsaid = 0; int seen = 0;
    SAID_RESET(nsaid);
    for (int k = 0; k < nsaid; k++) if (said[k] == id) seen = 1;
    if (!seen && nsaid < MAX_RCAL) said[nsaid++] = id;
    done = rcal_dates(id, c, r, n, seen) >= 0;
  }
  if (!done) rest_dates(id, r, n);
  note_first_round(id, r, n);
}

/* 0x141586640: the game's push_back for a calendar's vector of {day, round, kind} (the date
   switch's cases call it for every date of a shipped array). It grows the vector with the game's
   own allocator, so a league that needs more dates than any calendar has -- 26 to 30 clubs twice
   need 50 to 58, the longest calendar (the Championship's) has 46 -- gets the rest the game's
   way (mato 25.10.: "try to give additional dates for 30 teams league"). Until then such a
   league played 46 rounds and the rest dropped off at the season's end. Tested in the game with
   26 and 28 clubs (50 and 54 rounds, every one played). With 30 (58 rounds) the matches of the
   55th round (round 54) were dated but put on no day of the calendar, in two careers on two
   different days (29 April 2026, a Libertadores Wednesday, and 28 April 2025, a Monday), so
   57 of 58 were played: the cause is not known, and leaguebuilder stops at 28 clubs (L30 test,
   25.10.). */
#define PUSHDATE_RVA 0x1586640
static const unsigned char SIG_PUSHDATE[16] = {
  0x48,0x89,0x5c,0x24,0x08, 0x57, 0x48,0x83,0xec,0x20, 0x48,0x8b,0xd9, 0x48,0x8b,0xfa };
typedef void (*pushdate_fn)(vec_t* v, const date_t* d);
static int g_pushdate_ok = 0;

/* the calendar in v stretched to n dates: the season's first and last dates stay, the others are
   spread over the same line in step (an added round falls between two of the calendar's, mostly
   midweek), the rounds numbered 0..n-1; league_rest then spaces them as any league's. Returns the
   vector's length after it -- n, or what it had when it cannot. */
static size_t more_dates(uint16_t id, vec_t* v, size_t have, uint32_t n, int seen)
{
  if (!g_pushdate_ok || n > 64 || have < 2 || have >= n) return have;
  date_t src[64];
  memcpy(src, v->b, have * sizeof(date_t));
  pushdate_fn push = (pushdate_fn)(uintptr_t)(g_base + PUSHDATE_RVA);
  for (size_t i = have; i < n; i++) push(v, &src[have - 1]);
  size_t got = (v->b && v->e >= v->b) ? (size_t)(v->e - v->b) / sizeof(date_t) : 0;
  if (got != n) {
    if (!seen) logf("fl26swiss: reg %u -- the calendar grew to %u dates, not %u; left as it was", (unsigned)id,
                    (unsigned)got, (unsigned)n);
    if (got > have) v->e = v->b + have * sizeof(date_t);
    return have;
  }
  date_t* r = (date_t*)v->b;
  uint32_t d0 = src[0].day;
  for (uint32_t i = 0; i < n; i++) {
    uint64_t at = (uint64_t)i * (have - 1);                  /* on the calendar's line, in (n-1)ths */
    size_t j = (size_t)(at / (n - 1));
    uint32_t fr = (uint32_t)(at % (n - 1));
    uint32_t a = (src[j].day + 365 - d0) % 365;
    uint32_t b = j + 1 < have ? (src[j + 1].day + 365 - d0) % 365 : a;
    uint32_t p = a + (uint32_t)(((uint64_t)(b > a ? b - a : 0) * fr * 2 + (n - 1)) / (2 * (n - 1)));
    r[i].day = (d0 + p) % 365;
    r[i].round = i;
    r[i].kind = src[0].kind;
  }
  if (!seen) logf("fl26swiss: reg %u -- the calendar's %u dates stretched to %u (days %u..%u)", (unsigned)id,
                  (unsigned)have, n, r[0].day, r[n - 1].day);
  return n;
}

static void league_dates(uint16_t id, uint64_t reg, void* vec)
{
  unsigned char* rec = get_rec(id);
  vec_t* v = (vec_t*)vec;
  size_t have = (v->b && v->e >= v->b) ? (size_t)(v->e - v->b) / sizeof(date_t) : 0;
  if (!rec || have < 2) return;
  uint32_t clubs = *(uint32_t*)(rec + 0x30c) & 0x7f, legs = *(uint32_t*)(rec + 0x308) >> 29;
  uint32_t n = (clubs & 1 ? clubs : clubs - 1) * legs;
  int cy = calyear(id), eu = eudate(id);
  if (clubs < 4 || !legs) return;
  if (n == have && !cy && !eu) { league_rest(id, (date_t*)v->b, n); return; }
  static uint16_t said[64]; static int nsaid = 0; int seen = 0;
  SAID_RESET(nsaid);
  for (int k = 0; k < nsaid; k++) if (said[k] == id) seen = 1;
  if (!seen && nsaid < 64) said[nsaid++] = id;
  date_t* r = (date_t*)v->b;
  int32_t shift = 0;
  if (eu) {                                         /* the European calendar, from scratch */
    ((date_fn)(uintptr_t)g_tramp_date)((reg & ~(uint64_t)0xffff) | (n <= 38 ? MID_CAL_REG : LONG_CAL_REG), vec);
    have = (v->b && v->e >= v->b) ? (size_t)(v->e - v->b) / sizeof(date_t) : 0;
    if (n > have) have = more_dates(id, v, have, n, seen);
    r = (date_t*)v->b;
    if (n > have || have < 2) return;
  } else if (n > have) {
    uint32_t first = r[0].day;
    ((date_fn)(uintptr_t)g_tramp_date)((reg & ~(uint64_t)0xffff) | (n <= 38 ? MID_CAL_REG : LONG_CAL_REG), vec);
    have = (v->b && v->e >= v->b) ? (size_t)(v->e - v->b) / sizeof(date_t) : 0;
    if (n > have) have = more_dates(id, v, have, n, seen);
    r = (date_t*)v->b;
    if (n > have) {
      if (!seen) logf("fl26swiss: reg %u -- %u clubs x %u need %u rounds, the longest calendar has %u; left short",
                      (unsigned)id, clubs, legs, n, (unsigned)have);
      return;
    }
    shift = (int32_t)first - (int32_t)r[0].day;
  }
  static date_t tmp[64];
  if (have > 64) return;
  for (uint32_t i = 0; i < n; i++) {
    size_t j = n == 1 ? 0 : (size_t)((i * (have - 1) * 2 + (n - 1)) / (2 * (n - 1)));   /* rounded */
    tmp[i] = r[j];
    int32_t d = (int32_t)tmp[i].day + shift;
    tmp[i].day = (uint32_t)(d < 0 ? d + 365 : d >= 365 ? d - 365 : d);
    tmp[i].round = r[i].round;
    if (cy) tmp[i].day = n == 1 ? CAL_FIRST
                                : CAL_FIRST + (i * (CAL_LAST - CAL_FIRST) * 2 + (n - 1)) / (2 * (n - 1));
  }
  memcpy(r, tmp, n * sizeof(date_t));
  v->e = v->b + (size_t)n * sizeof(date_t);
  league_rest(id, r, n);
  if (!seen)
    logf("fl26swiss: reg %u -- %u clubs x %u = %u rounds, calendar resampled from %u dates (days %u..%u, shift %d)",
         (unsigned)id, clubs, legs, n, (unsigned)have, r[0].day, r[n - 1].day, (int)shift);
}

/* ---- split seasons ----
 *
 * The Scottish Premiership ships as four rows under one competition: a total (133, type 9,
 * format 11) and three leagues -- the regular phase (format 12) and the top and bottom
 * groups (13, 14). The date switch sends 134-136 to case 42, which reads the row's format:
 * a regular phase gets 33 dates (days 226..100, rounds 0..32, array 0x14298f660), a group 5
 * (days 107..142, rounds 0..4, array 0x14298f7f0). The total gets none.
 *
 * tools/mksplit.py builds our splits the same way, with new ids for the phases, and new ids
 * have no case. So here: the Scottish season (both arrays end to end, 38 dates from mid
 * August to late May) is the timeline; it is resampled to the regular phase's rounds plus
 * the longest group's, the regular phase takes the first dates and every group the rest,
 * each numbering its rounds from 0 as case 42 does. A split longer than 38 rounds uses the
 * Championship's 46-date calendar (reg 79) as the timeline instead. The total's vector is
 * emptied: given dates it would schedule a league of its own. */
struct split_s { uint16_t total, regular, group[3]; };
/* No split is built in: a world file names its splits (fl26_swiss_splits). */
#define MAX_SPLITS 32
static split_t SPLITS[MAX_SPLITS] = {
  { 0 }
};
static int g_nsplits = 0;

/* v holds five ids per split: total, regular phase, up to three groups (0 = none). */
__declspec(dllexport) int fl26_swiss_splits(const uint16_t* v, int n)
{
  if ((!v && n) || n < 0) return -1;
  if (n > MAX_SPLITS) n = MAX_SPLITS;
  for (int i = 0; i < n; i++) {
    SPLITS[i].total = v[5 * i]; SPLITS[i].regular = v[5 * i + 1];
    for (int g = 0; g < 3; g++) SPLITS[i].group[g] = v[5 * i + 2 + g];
  }
  g_nsplits = n;
  logf("fl26swiss: %d split season(s) from the world file", n);
  return n;
}

/* Apertura/Clausura (leaguebuilder "apertura"): a split of one group of all the clubs whose
 * group starts from zero points -- `carry=0` on the world file's split line. The carry stub
 * below goes by the competition key, so such a split's key is simply not put in it; a split
 * that carries under the same key would carry for both (the builder refuses that world). */
static uint16_t g_nocarry[MAX_SPLITS]; static int g_nnocarry = 0;
__declspec(dllexport) int fl26_swiss_nocarry(const uint16_t* v, int n)
{
  if ((!v && n) || n < 0) return -1;
  if (n > MAX_SPLITS) n = MAX_SPLITS;
  for (int i = 0; i < n; i++) g_nocarry[i] = v[i];
  g_nnocarry = n;
  logf("fl26swiss: %d split(s) without a points carry (Apertura/Clausura)", n);
  return n;
}
static int nocarry(uint16_t total)
{
  for (int i = 0; i < g_nnocarry; i++) if (g_nocarry[i] == total) return 1;
  return 0;
}
/* The Scottish line, with one date moved: the shipped 12 September (254) is the second day of
 * the national cups' first round (calendar case 6: 251 and 254), so a split league met its own
 * cup on the same day (#70, Egypt). 15 September (257) is free of every cup and European day. */
static const uint16_t SCOT_DAYS[38] = {
  226, 233, 240, 257, 261, 268, 275, 296, 300, 303, 310, 321, 324, 331, 338, 345, 356, 359, 363,
  2, 13, 16, 20, 23, 31, 34, 37, 51, 58, 65, 72, 79, 100,
  107, 114, 121, 128, 142 };
/* A split longer than the Scottish line holds from 15 September (38 - SPLIT_SKIP = 35 rounds:
 * Switzerland 33 + 5, Costa Rica's Apertura and Clausura twice round, 44) is dated on this one,
 * 2026-11-08: the same line from 15 September with eleven dates put in its widest gaps, three
 * days or more apart and none the day before, of or after a national cup day. Up to 46 rounds,
 * still ending on 22 May (leaguebuilder SPLIT_LONG, split_days). Before it a split of 36 to 38
 * rounds started in August (the dates a league of ours lost, see SPLIT_SKIP) and one of 39 to
 * 46 took the Championship's calendar, which starts there too. */
static const uint16_t SPLIT_LONG[46] = {
  257, 261, 268, 271, 275, 280, 284, 291, 296, 300, 303, 310, 315, 321, 324, 331, 338, 345, 350,
  356, 359, 363, 2, 13, 16, 20, 23, 28, 31, 34, 37, 46, 51, 58, 65, 72, 79, 88, 92, 100, 107, 114,
  121, 128, 137, 142 };

static void canon_groups(const split_t* s)
{
  for (int g = 0; g < 3; g++) if (s->group[g]) check_reg(s->group[g], "its group filled");
}

/* 0 not a split row, 1 total, 2 regular phase, 3 a group */
/* A split's regular phase takes the new season's clubs from its total (GitHub #79/#81, Egypt
 * 2026-10-06). Promotion and relegation are done on the total, the league the one below names
 * as the league above (fl26chain finishes the pair the game's mover leaves alone), but the
 * matches are played by the regular phase, which the July pass refills with last season's 20:
 * the relegated would play on at the top and the promoted nowhere. Only the same number of
 * clubs, so the game's vector is rewritten in place. */
static void split_regular_clubs(uint16_t r, const split_t* s, u32vec* list)
{
  unsigned char* t = get_rec(s->total);
  uint32_t n = (uint32_t)(list->e - list->b), m = t ? rec_count(t) : 0;
  if (!t || n > 48) return;
  const uint32_t* want = rec_clubs(t);
  /* the total has no dates of its own, and its count field can read 0: then the list runs to
     the first empty slot, as check_reg reads it (the first try, 2026-10-06, returned here) */
  if (!m) while (m < 48 && want[m] != 0xffffffffu) m++;
  if (m != n) {
    logf("fl26swiss: set_clubs reg %u -- total %u has %u club(s), the phase %u: left as it is",
         (unsigned)r, (unsigned)s->total, m, n);
    return;
  }
  /* a club is its team id, the upper 18 bits: the same club reads 45ea000e in the total's list
     and 45ea8010 in the phase's (the lower 14 are a row, see canon_club) */
  int moved = 0;
  for (uint32_t i = 0; i < n; i++) {
    int have = 0;
    for (uint32_t j = 0; j < n; j++) have |= (list->b[j] >> 14) == (want[i] >> 14);
    if (!have) moved++;
  }
  if (!moved) return;
  for (uint32_t i = 0; i < n; i++) list->b[i] = canon_club(want[i]);
  logf("fl26swiss: set_clubs reg %u -- the clubs of total %u taken on day %d: %d promoted in, %d relegated out",
       (unsigned)r, (unsigned)s->total, today(), moved, moved);
}

static int split_part(uint16_t id, const split_t** out)
{
  for (int i = 0; i < g_nsplits; i++) {
    const split_t* s = &SPLITS[i];
    *out = s;
    if (id == s->total) return 1;
    if (id == s->regular) return 2;
    for (int g = 0; g < 3; g++) if (s->group[g] && id == s->group[g]) return 3;
  }
  return 0;
}

/* The points go with the clubs. The Scottish groups start from the regular phase's points and
 * count everything else afresh: on 2026-09-26, 134 had Celtic on 66 after 33 games and 135 had
 * Celtic on 76 after 5, with only the group's wins, draws and goals in the row. Ours started
 * from zero.
 *
 * The game does it in 0x14134a540(ctx, id), called by the table rebuild 0x14134a9xx for every
 * group phase: it takes the competition key (0x1415415f0), finds the format-12 phase under that
 * key (0x1414ce270), and then switches on the key itself --
 *
 *     14134a66e  sub edi, 8 ; je 0x14134a796     key 8  -> the other carry (halving, unverified)
 *     14134a677  sub edi, 3 ; je 0x14134a796     key 11
 *     14134a680  sub edi, 1 ; je 0x14134a68e     key 12 -> full points
 *     14134a685  cmp edi, 3 ; jne 0x14134a8aa    key 15 (Scotland) -> full points, else none
 *
 * so a split under any other key gets no carry. Adding our points from outside does not hold:
 * the rebuild recomputes every row from its own results after each matchday (measured: carried
 * on day 41, gone again by day 51), and sorts before we could add them back. So the 14 bytes at
 * 0x14134a680 jump to a stub that makes the same two tests and then the keys of our splits,
 * which the stub holds as eight cmp immediates filled in at run time from the live records
 * (split_keys). Everything else leaves the stub where the original would have gone.
 * The slots compare the low byte (`cmp dil, key-12`, unsigned) since 06.11.2026: a key is a
 * region, 0..255 with fl26caps' regions step (FL 2027), and the old `cmp edi, imm8` sign-extended
 * key-12 past 127 (no match from key 140 up) and its empty slot 0x7f was key 139. Here edi is
 * key-12, its low byte 0..243 for keys 12..255 and 244..255 for 0..11, never an empty slot's 0:
 * key 12 (edi 0) has jumped already. */
#define CARRY_SITE_RVA 0x134a680
#define CARRY_FULL_RVA 0x134a68e
#define CARRY_NONE_RVA 0x134a8aa
static const unsigned char SIG_CARRY[14] = {
  0x83,0xef,0x01, 0x74,0x09, 0x83,0xff,0x03, 0x0f,0x85,0x1c,0x02,0x00,0x00 };
/* 32 slots since 08.11.2026 (8 before): Apertura/Clausura and splits as in reality are some 30
 * leagues. Every jump to "full" is a rel32 je (0f 84), so the stub can be longer than a rel8 reaches. */
#define CARRY_SLOTS 32
static unsigned char* g_carry_stub = 0;      /* slot i's immediate is at +CARRY_IMM(i) */
#define CARRY_HEAD 18
#define CARRY_IMM(i) (CARRY_HEAD + 10 * (i) + 3)
static unsigned g_carry_keys = 0;

static int carry_install(uint64_t exe_base)
{
  unsigned char* site = (unsigned char*)(uintptr_t)(exe_base + CARRY_SITE_RVA);
  for (int i = 0; i < 14; i++) if (site[i] != SIG_CARRY[i]) return 2;
  unsigned char* t = (unsigned char*)VirtualAlloc(0, 0x400, MEM_COMMIT|MEM_RESERVE, PAGE_EXECUTE_READWRITE);
  if (!t) return 3;
  int n = 0, full = CARRY_HEAD + 10 * CARRY_SLOTS + 14;   /* offset of the "full" jump */
#define CARRY_JE() do { t[n++] = 0x0f; t[n++] = 0x84; *(int32_t*)(t + n) = full - (n + 4); n += 4; } while (0)
  t[n++] = 0x83; t[n++] = 0xef; t[n++] = 0x01;             /* sub edi, 1      (key 12 -> 0) */
  CARRY_JE();
  t[n++] = 0x83; t[n++] = 0xff; t[n++] = 0x03;             /* cmp edi, 3      (key 15) */
  CARRY_JE();
  for (int i = 0; i < CARRY_SLOTS; i++) {                  /* cmp dil, key-12 ; je full */
    t[n++] = 0x40; t[n++] = 0x80; t[n++] = 0xff; t[n++] = 0x00;   /* 0: an empty slot never matches */
    CARRY_JE();
  }
#undef CARRY_JE
  t[n++] = 0xFF; t[n++] = 0x25; *(uint32_t*)(t + n) = 0; n += 4;
  *(uint64_t*)(t + n) = exe_base + CARRY_NONE_RVA; n += 8;
  t[n++] = 0xFF; t[n++] = 0x25; *(uint32_t*)(t + n) = 0; n += 4;
  *(uint64_t*)(t + n) = exe_base + CARRY_FULL_RVA; n += 8;
  DWORD old;
  if (!VirtualProtect(site, 14, PAGE_EXECUTE_READWRITE, &old)) return 4;
  site[0] = 0xFF; site[1] = 0x25; *(uint32_t*)(site + 2) = 0; *(uint64_t*)(site + 6) = (uint64_t)(uintptr_t)t;
  VirtualProtect(site, 14, old, &old);
  FlushInstructionCache(GetCurrentProcess(), site, 14);
  g_carry_stub = t;
  return 0;
}

/* ---- the board's objective: a continental cup of the club's own continent ----
 *
 * At the season's objectives meeting the owner judges (menuutility::OwnerSeasonTaskJudge::*) ask
 * 0x1415111c0(&club) for the club's continent and write the objective's regulation from it:
 * 0 -> UEFA Champions League (4, or 6), 2 -> AFC Champions League (0x10), anything else ->
 * Libertadores (0xa). The continent comes from the club's league's competition code, and a league
 * of our own regions that plays August to May keeps the UEFA code on purpose (the season-end
 * filter 0x141365c50 wants it, see leaguebuilder), so a club in a new Korean league was told to
 * win the Champions League (GitHub #43).
 *
 * Only the 18 calls inside the judges (0x140edc75a..0x140ede324) go to cont_handler, through a
 * 14-byte jump placed within reach of a rel32 call; nothing else that asks for the continent
 * changes. The handler asks the game first and only replaces an answer of UEFA, and only for a
 * club whose country the world file's conf= puts in the AFC (-> 2) or CONMEBOL (-> 1). The game
 * has no objective for the African, North American or Oceanian cups, so those stay as they were.
 *
 * B395 (11.11.2026): the meeting itself went on offering "the UEFA Champions League" to a club of
 * a new Asian league. Its lines take the competition from 0x140f44b30 (objective type -> the
 * regulations its text names), and for the types 8, 9, 10 and 13 that is 0x140f446c0(club): the
 * same continent call, twice, outside the judges (0 -> 4, 2 -> 0x10, else 0xa). Those two calls go
 * through the same jump, as a group of their own: one that does not look as expected is left
 * alone and takes nothing from the judges' eighteen. */
#define CONT_RVA 0x15111c0
static const uint32_t CONT_CALLS[] = {
  0xedc75a, 0xedc77b, 0xedc87c, 0xedc893, 0xedca17, 0xedca2e, 0xedcc22, 0xedcc30, 0xedcc80,
  0xedcca6, 0xedd507, 0xedd51b, 0xedd75a, 0xedd77b, 0xeddaa5, 0xeddacb, 0xede311, 0xede324 };
static const uint32_t CONT_MEET[] = { 0xf446cd, 0xf446e5 };
typedef int (*cont_fn)(void* club);

static int cont_handler(void* club)
{
  int r = ((cont_fn)(uintptr_t)(g_base + CONT_RVA))(club);
  static int asked = 0;
  if (asked < 3 && club) {
    asked++;
    logf("fl26swiss: board objective -- the owner asks the continent of club %08x: %d (%d countries known)",
         *(uint32_t*)club, r, g_confed_n);
  }
  if (r != 0 || !g_confed_n || !club) return r;
  unsigned char* o = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
  void* blk = o ? *(void**)(o + 0x48) : 0;
  int c = team_country(blk, *(uint32_t*)club);
  int f = c >= 0 ? confed_of(c) : 0;
  int want = f == 3 ? 2 : f == 4 ? 1 : 0;
  static int said = 0;
  if (want && said < 20) {
    said++;
    logf("fl26swiss: board objective -- club %08x (country %d, %s) gets the %s, not the Champions League",
         *(uint32_t*)club, c, f == 3 ? "AFC" : "CONMEBOL", f == 3 ? "AFC Champions League" : "Libertadores");
  }
  return want;
}

/* A page for the jump, within +-2 GB of the exe: below its base, 64 KB steps. */
static unsigned char* near_alloc(uint64_t exe_base)
{
  for (uint64_t a = (exe_base & ~0xffffULL) - 0x10000; a > exe_base - 0x70000000ULL; a -= 0x10000) {
    void* p = VirtualAlloc((void*)(uintptr_t)a, 0x1000, MEM_COMMIT|MEM_RESERVE, PAGE_EXECUTE_READWRITE);
    if (p) return (unsigned char*)p;
  }
  return 0;
}

/* A group of calls of 0x1415111c0 -> the jump at t. 0 ok; 2 a call is not the one expected (none of
 * the group patched); 4 VirtualProtect */
static int cont_group(uint64_t exe_base, const uint32_t* calls, int n, unsigned char* t)
{
  for (int i = 0; i < n; i++) {
    unsigned char* s = (unsigned char*)(uintptr_t)(exe_base + calls[i]);
    if (s[0] != 0xE8 || (uint64_t)(uintptr_t)(s + 5) + *(int32_t*)(s + 1) != exe_base + CONT_RVA) return 2;
  }
  for (int i = 0; i < n; i++) {
    unsigned char* s = (unsigned char*)(uintptr_t)(exe_base + calls[i]);
    DWORD old;
    if (!VirtualProtect(s, 5, PAGE_EXECUTE_READWRITE, &old)) return 4;
    *(int32_t*)(s + 1) = (int32_t)((int64_t)(uintptr_t)t - (int64_t)(uintptr_t)(s + 5));
    VirtualProtect(s, 5, old, &old);
    FlushInstructionCache(GetCurrentProcess(), s, 5);
  }
  return 0;
}

/* 0 ok; 2 a judges' call is not the one expected (nothing patched); 3 no page in reach;
 * 4 VirtualProtect. *meet: the same for the meeting's two calls (B395), tried only after the judges. */
static int cont_install(uint64_t exe_base, int* meet)
{
  *meet = -1;
  int n = (int)(sizeof CONT_CALLS / sizeof CONT_CALLS[0]);
  for (int i = 0; i < n; i++) {
    unsigned char* s = (unsigned char*)(uintptr_t)(exe_base + CONT_CALLS[i]);
    if (s[0] != 0xE8 || (uint64_t)(uintptr_t)(s + 5) + *(int32_t*)(s + 1) != exe_base + CONT_RVA) return 2;
  }
  unsigned char* t = near_alloc(exe_base);
  if (!t) return 3;
  t[0] = 0xFF; t[1] = 0x25; *(uint32_t*)(t + 2) = 0; *(uint64_t*)(t + 6) = (uint64_t)(uintptr_t)cont_handler;
  FlushInstructionCache(GetCurrentProcess(), t, 14);
  int r = cont_group(exe_base, CONT_CALLS, n, t);
  if (r) return r;
  *meet = cont_group(exe_base, CONT_MEET, (int)(sizeof CONT_MEET / sizeof CONT_MEET[0]), t);
  return 0;
}

/* ---- two splits in one country (08.11.2026, mato: "koja ima aperturu i clausuru u stvarnosti,
 * mora imati i ovdje") ----
 *
 * The game finds a split's phases by the country: a phase asks its region (0x1415415f0), takes
 * every regulation of that region (0x1414ce270, region -> vector of ids) and picks by format --
 * the regular phase is the first format 12, the groups are the formats 13..15 (0x1414cee10 reads
 * the region inline). With two splits in a region (Iceland with Apertura/Clausura in both
 * divisions, GitHub #45; Mexico's Liga MX and Liga de Expansion; Denmark's own split and a split
 * second division) each found the other's phases too, and neither played.
 *
 * So at the call sites that look for a split's phases, the vector is cut to the split asking:
 * the `call 0x1415415f0` just before each of them records the id that asked (g_rk_q), and the
 * `call 0x1414ce270` then drops every split row (format 11..15) that is not a part of the same
 * split. A split of the game's own (Scotland, Denmark, Belgium) asking drops only ours. Every
 * other caller of 0x1414ce270 (menus, the career list, the season builder) gets the region whole. */
#define RK_GETREG_RVA 0x15415f0
#define RK_LIST_RVA   0x14ce270
/* the 0x1415415f0 call in front of each list call below, and that list call */
static const uint32_t RK_ASK[] = {
  0xaed461, 0xfc744f, 0xfcb91a, 0x1323272, 0x13463b5, 0x134a5b2, 0x1359b79, 0x135bf6c, 0x151a0f2 };
static const uint32_t RK_LIST[] = {
  0xaed478, 0xfc745a, 0xfcb934, 0x132328d, 0x13463cf, 0x134a625, 0x1359b90, 0x135bf77, 0x151a10c };
/* 0x1414cee10 (the groups of a split) reads the region itself: the id is in ebx at its list call */
#define RK_GROUPS_LIST 0x14ceec4
typedef uint32_t (*rk_getreg_fn)(uint64_t id);
typedef uint64_t (*rk_list_fn)(uint64_t region, void* vec);
static int split_part(uint16_t id, const split_t** out);
static __thread uint16_t g_rk_q = 0;
static unsigned g_rk_cut = 0;

static unsigned rk_format(uint16_t id)
{
  unsigned char* r = get_rec(id);
  return r ? (*(uint32_t*)(r + 0x308) >> 23) & 0x3f : 0;
}
static int rk_ours(uint16_t id, const split_t** s)
{
  return split_part(id, s) != 0;
}
static int rk_in(const split_t* s, uint16_t id)
{
  if (id == s->total || id == s->regular) return 1;
  for (int g = 0; g < 3; g++) if (s->group[g] && s->group[g] == id) return 1;
  return 0;
}
static void rk_cut(uint16_t q, void* vec)
{
  vec_t* v = (vec_t*)vec;
  if (!q || !g_nsplits || !v || !v->b || v->e <= v->b) return;
  const split_t* s = 0;
  int mine = rk_ours(q, &s);
  unsigned fq = mine ? 0 : rk_format(q);
  if (!mine && (fq < 11 || fq > 15)) return;            /* not a split asking */
  uint16_t* b = (uint16_t*)v->b; size_t n = (size_t)((uint16_t*)v->e - b), k = 0;
  for (size_t i = 0; i < n; i++) {
    uint16_t id = b[i]; const split_t* o = 0; int drop;
    if (mine) {
      unsigned f = rk_format(id);
      drop = f >= 11 && f <= 15 && !rk_in(s, id);
    }
    else drop = rk_ours(id, &o);                         /* the game's own split: not our rows */
    if (!drop) b[k++] = id;
  }
  if (k != n) {
    v->e = (void*)(b + k);
    if (g_rk_cut < 12) {
      g_rk_cut++;
      logf("fl26swiss: reg %u asks its country's competitions -- %u of %u kept (the other split's phases out)",
           (unsigned)q, (unsigned)k, (unsigned)n);
    }
  }
}
static uint32_t rk_ask(uint64_t id)
{
  g_rk_q = (uint16_t)id;
  return ((rk_getreg_fn)(uintptr_t)(g_base + RK_GETREG_RVA))(id);
}
static uint64_t rk_list(uint64_t region, void* vec)
{
  uint64_t rv = ((rk_list_fn)(uintptr_t)(g_base + RK_LIST_RVA))(region, vec);
  uint16_t q = g_rk_q; g_rk_q = 0;
  rk_cut(q, vec);
  return rv;
}
static uint64_t rk_groups(uint64_t region, void* vec, uint64_t q)
{
  uint64_t rv = ((rk_list_fn)(uintptr_t)(g_base + RK_LIST_RVA))(region, vec);
  rk_cut((uint16_t)q, vec);
  return rv;
}

static int rk_call_to(uint64_t exe_base, uint32_t site, uint32_t target)
{
  unsigned char* s = (unsigned char*)(uintptr_t)(exe_base + site);
  return s[0] == 0xE8 && (uint64_t)(uintptr_t)(s + 5) + *(int32_t*)(s + 1) == exe_base + target;
}
static int rk_point(uint64_t exe_base, uint32_t site, const unsigned char* to)
{
  unsigned char* s = (unsigned char*)(uintptr_t)(exe_base + site);
  DWORD old;
  if (!VirtualProtect(s, 5, PAGE_EXECUTE_READWRITE, &old)) return 4;
  *(int32_t*)(s + 1) = (int32_t)((int64_t)(uintptr_t)to - (int64_t)(uintptr_t)(s + 5));
  VirtualProtect(s, 5, old, &old);
  FlushInstructionCache(GetCurrentProcess(), s, 5);
  return 0;
}
/* 0 ok, else the number of call pairs left as they were (a signature that did not match) + 100 * error */
static int rk_install(uint64_t exe_base)
{
  int n = (int)(sizeof RK_ASK / sizeof RK_ASK[0]), skipped = 0;
  unsigned char* t = near_alloc(exe_base);
  if (!t) return 300;
  /* +0: jmp rk_ask   +16: jmp rk_list   +32: mov r8d, ebx ; jmp rk_groups */
  t[0] = 0xFF; t[1] = 0x25; *(uint32_t*)(t + 2) = 0; *(uint64_t*)(t + 6) = (uint64_t)(uintptr_t)rk_ask;
  t[16] = 0xFF; t[17] = 0x25; *(uint32_t*)(t + 18) = 0; *(uint64_t*)(t + 22) = (uint64_t)(uintptr_t)rk_list;
  t[32] = 0x41; t[33] = 0x89; t[34] = 0xd8;                                  /* mov r8d, ebx */
  t[35] = 0xFF; t[36] = 0x25; *(uint32_t*)(t + 37) = 0; *(uint64_t*)(t + 41) = (uint64_t)(uintptr_t)rk_groups;
  FlushInstructionCache(GetCurrentProcess(), t, 64);
  for (int i = 0; i < n; i++) {
    if (!rk_call_to(exe_base, RK_ASK[i], RK_GETREG_RVA) || !rk_call_to(exe_base, RK_LIST[i], RK_LIST_RVA)) {
      skipped++;
      continue;
    }
    if (rk_point(exe_base, RK_ASK[i], t) || rk_point(exe_base, RK_LIST[i], t + 16)) return 400;
  }
  if (rk_call_to(exe_base, RK_GROUPS_LIST, RK_LIST_RVA)) { if (rk_point(exe_base, RK_GROUPS_LIST, t + 32)) return 400; }
  else skipped++;
  return skipped;
}

/* ---- our play-offs on the Match Results screen (n1ne, CUSTOM_PLAYOFF_MATCH_RESULTS_FIX) ----
 *
 * The Champions League play-off's replicas (0x402, 0x802 ...), the Europa and Conference League
 * play-offs (188, 189, ties at id + 1024 * (k + 1)), the qualifying rounds (g_qreg) and the league
 * cups' pre-rounds (g_lpre: the Carabao Cup's first round read "Group stage - Matchday 54",
 * 08.10.) are copies of reg 2, but only the exact ids the game knows get the play-off treatment on the results
 * screen: the subclass selector 0x140af93f0 takes the group-stage subclass for them, and the
 * title 0x14152a590 builds "Group stage - Matchday 54" instead of "Play-offs". Two patches,
 * both for our ids only, so every shipped competition goes as before:
 *  - POAB9: the selector's call of the active-competition resolver (0x14150c230 at 0x140af9421)
 *    goes to po_sel, which answers 2 for one of ours -- the id the selector already whitelists.
 *    The call site alone; nothing else that asks for the active competition changes.
 *  - POAB13: the title's last play-off test (sub si,0x45 / cmp si,4 at 0x14152ada3) jumps to a
 *    stub that sends ours to the native Play-offs branch 0x14152ad97 and runs the original test
 *    for everything else. Only rax is used, saved; [rsp+0x28] is never touched (POAB11 crashed
 *    reading it). The ids are a table in the stub's page, filled from g_qreg and g_lpre (po_fill). */
#define ACTCOMP_RVA  0x150c230
#define POSEL_CALL   0xaf9421
#define POTTL_SITE   0x152ada3
#define POTTL_NATIVE 0x152ad97
#define POTTL_RESUME 0x152adab
static const unsigned char SIG_POTTL[10] = { 0x66,0x83,0xee,0x45, 0x66,0x83,0xfe,0x04, 0x76,0xea };
typedef uint64_t (*actcomp_fn)(uint64_t, uint64_t, uint64_t, uint64_t);

static int our_po(uint16_t id)
{
  int tie;
  return (is_playoff(id) && id >= 0x400) || new_po(id) || q_added(id) >= 0 || lpre_of(id, &tie) >= 0;
}

static uint64_t po_sel(uint64_t a, uint64_t b, uint64_t c, uint64_t d)
{
  uint64_t r = ((actcomp_fn)(uintptr_t)(g_base + ACTCOMP_RVA))(a, b, c, d);
  uint16_t id = (uint16_t)r;
  /* B266: a Match Results screen is up, so no Competition Info item stands for its page */
  g_mr_pick = 0xffff; g_ci_pick = 0xffff;
  if (!our_po(id)) return r;
  unsigned char* rec = get_rec(id);
  if (!rec || *(uint32_t*)(rec + 0x84) != 2) return r;
  if (id < 0x400 && q_added(id) >= 0) {
    g_mr_pick = id; g_mr_pick_comp = *(uint32_t*)(rec + 0x80); g_mr_pick_day = today();
  }
  static int said = 0;
  if (said < 5) { said++; logf("fl26swiss: Match Results -- regulation %u shown as a play-off", id); }
  return (r & ~0xffffULL) | 2;
}

#define PO_SLOTS (8 + MAX_LPRE + NQ + 2)    /* 188, 189, six qualifying rounds, the pre-rounds, FL27's three first rounds, Prijedlog C's two play-offs */
static uint32_t* g_po_tab = 0;               /* low ids the title takes as play-offs; 0xffff empty */
static void po_fill(void)
{
  if (!g_po_tab) return;
  uint32_t v[PO_SLOTS];
  v[0] = UEL_PO; v[1] = UECL_PO;
  for (int i = 3; i < 9; i++) v[i - 1] = g_qreg[i] ? g_qreg[i] : 0xffff;
  for (int i = 0; i < MAX_LPRE; i++) v[8 + i] = i < g_nlpre ? g_lpre[i].reg : 0xffff;
  for (int i = 0; i < NQ; i++) v[8 + MAX_LPRE + i] = g_qreg[NQ * 3 + i] ? g_qreg[NQ * 3 + i] : 0xffff;
  for (int i = 1; i < NQ; i++) v[8 + MAX_LPRE + NQ + i - 1] = g_qreg[i] ? g_qreg[i] : 0xffff;
  for (int i = 0; i < PO_SLOTS; i++) g_po_tab[i] = v[i];
}

/* ---- the qualifying rounds' name in the match titles ----
 * Two builders of a match's title -- Match Results / schedule (0x14152a590, the phase in si) and
 * the other one at 0x140cadf.. (the phase in r14w) -- put the text "Play-offs" (0x3a20010, or
 * 0x510029) by a constant for anything that is not a group or league, and never ask
 * 0x1414cb830, so phname_handler's names did not reach them (08.10.: "UEFA Champions League
 * Play-offs - 1st leg" for a second qualifying round).  Their call of the text fetch
 * 0x141496ca0 (string, text id, ...) goes through a stub that hands the phase over in r8
 * (the fetch is variadic and these texts take no argument): title_text puts the round's own
 * text for one of our qualifying rounds or their ties, and the original for all else. */
#define TTL_CALL1 0x152a7e6   /* phase in si */
#define TTL_CALL2 0x0cae00c   /* phase in r14w */
#define TEXTFETCH_RVA 0x1496ca0
typedef void* (*textfetch_fn)(void* str, uint64_t id);
static void* title_text(void* str, uint64_t id, uint64_t phase)
{
  uint32_t t = (uint32_t)id;
  if (t == 0x3a20010u || t == 0x510029u) {
    int ls = libq_alias_stage((uint16_t)phase);
    int f3 = (((uint16_t)phase & 0x3ff) == CONM_LIBQ_REG) &&
             ((uint16_t)phase >> 10) <= 4;
    /* Match titles use the same native/localized phase text as reg 8 too. */
    if (ls || f3) {
      unsigned char qrec[0x200];
      phrec_fn get = (phrec_fn)(uintptr_t)(g_base + PHREC_RVA);
      if (get(CONM_LIBQ_REG, qrec)) t = *(uint32_t*)(qrec + 0x40);
    }
    int qa = (ls || f3) ? -2 : q_added((uint16_t)phase);
    if (qa >= NQ && g_tramp_txtget) {              /* a Prijedlog C play-off (1, 2) stays "Play-offs" */
      static int said = 0;
      if (said < 4) { said++; logf("fl26swiss: match title -- regulation %u named %s qualifying round", (unsigned)(uint16_t)phase, qa / NQ == 1 ? "3rd" : qa / NQ == 3 ? "1st" : "2nd"); }
      t = QR_TEXT(qa / NQ);
    }
    int pc = po_cup_of((uint16_t)phase);
    if (qa < 0 && pc >= 0 && g_tramp_txtget && kopo_window(pc)) t = KOPO_TEXT;
  }
  return ((textfetch_fn)(uintptr_t)(g_base + TEXTFETCH_RVA))(str, t);
}
static int ttl_install(uint64_t exe_base)
{
  static const uint32_t SITE[2] = { TTL_CALL1, TTL_CALL2 };
  static const unsigned char MOV[2][3] = { { 0x49, 0x89, 0xf0 }, { 0x4d, 0x89, 0xf0 } };   /* mov r8, rsi / r14 */
  for (int i = 0; i < 2; i++) {
    unsigned char* c = (unsigned char*)(uintptr_t)(exe_base + SITE[i]);
    if (c[0] != 0xE8 || (uint64_t)(uintptr_t)(c + 5) + *(int32_t*)(c + 1) != exe_base + TEXTFETCH_RVA) return 2;
  }
  unsigned char* t = near_alloc(exe_base);
  if (!t) return 3;
  for (int i = 0; i < 2; i++) {
    unsigned char* s = t + 0x20 * i;
    memcpy(s, MOV[i], 3);
    s[3] = 0xFF; s[4] = 0x25; *(uint32_t*)(s + 5) = 0; *(uint64_t*)(s + 9) = (uint64_t)(uintptr_t)title_text;
  }
  FlushInstructionCache(GetCurrentProcess(), t, 0x40);
  for (int i = 0; i < 2; i++) {
    unsigned char* c = (unsigned char*)(uintptr_t)(exe_base + SITE[i]);
    DWORD old;
    if (!VirtualProtect(c, 5, PAGE_EXECUTE_READWRITE, &old)) return 4;
    *(int32_t*)(c + 1) = (int32_t)((int64_t)(uintptr_t)(t + 0x20 * i) - (int64_t)(uintptr_t)(c + 5));
    VirtualProtect(c, 5, old, &old);
    FlushInstructionCache(GetCurrentProcess(), c, 5);
  }
  return 0;
}

/* ---- Competition Info -> Individual Titles / Team of the Competition (B470, 20.06.2028) ----
 *
 * The menu enables those items (types 8..10, 0x14151fe8c) only when 0x141590780(comp) says yes:
 * it walks every regulation record whose +0x80 is the competition and, for each one that
 * 0x1414cfb90 does not call "no awards", wants a non-empty awards list (0x141590820 ->
 * 0x14157c530(reg, +0x2fc) -> 0x140b11870). 0x1414cfb90 reads the exe's per-regulation table
 * (0x1414fdbc0, the table fl26comptab copies): +0x29 = 0 is "no awards". Every cup row of the exe
 * carries 0 -- the Champions League's 2, 3, 4 and their replicas 1026.. / 1027 included -- so for a
 * shipped cup nothing is checked and the items are on. A regulation id the table has no row for
 * is answered "has awards" and is checked: our qualifying rounds (256 257 258, copies of reg 2,
 * and their ties), the Europa / Conference League play-offs, the continental cups of the world
 * file (CAF 615/616, OFC, AFC ...). Their lists are empty, so the items stayed grey all season
 * for the Champions League while CONCACAF's one regulation (623) had a list and was on.
 *
 * At that one call only (0x1415907e2) a regulation with no row of its own that is not a league
 * is answered "no awards", as its template row (reg 2, 3, 4) is: the walk then checks what it
 * checks for a shipped cup. Leagues keep the game's answer (their rows are fl26comptab's, +0x29
 * set to 1, and their lists are what the items show). The page builders and the season-end
 * awards (0x1414cfb90's other callers) are untouched.
 *
 * The record's +0x84 is not the file's type: the loader (0x1414f7e80) takes it from the
 * CompetitionKind row of the type (0x1414efb90), bits 11..13 for a master (file +6 parent 0,
 * record +0x76 = 0xffff) and bits 8..10 for a replica (+0x76 = the master's id), through
 * 1->2 2->3 3->1 4->4 5->5 6->6. So a play-off and a group stage are 2, a knockout 3, a
 * league 1 -- and a play-off's tie is 3, but one group of a group stage is 1, as a league
 * is. beta4r (18.11., save b470-s2-2006): the group replicas of our cups (UECL 1210, CAF
 * 615 + 1024 k, CAF CC 617.., AFC CL Two 619.., OFC 624.., AFC Challenge 625..) were taken
 * for leagues, asked for a list, and the items stayed grey; UCL / UEL's groups (1027, 1029)
 * have the exe's alias rows and CONCACAF / the CAF Super Cup have no groups, so those were on.
 * A replica whose master is a cup phase of ours (no row, master kind not a league) is now
 * skipped as its master is. The walk keeps the record in rdi; the stub hands it over in rdx. */
#define AWGATE_CALL  0x15907e2   /* call 0x1414cfb90 inside 0x141590780's walk */
#define NOAWARD_RVA  0x14cfb90   /* (u16 reg) -> 1 when the exe's row says "no awards" */
#define COMPROW_RVA  0x14fdbc0   /* (u16 reg, out row 0x108) -> 1 when the exe has a row (or replica) */
#define COMPROW_AWARDS 0x29      /* row byte: 0 = no awards */
#define REC_KIND_LEAGUE 1        /* record +0x84: 1 a league, or one group of a group stage */
#define REC_PARENT   0x76        /* record u16: the master's id for a replica, 0xffff for a master */
static const unsigned char SIG_AWGATE_PRE[3] = { 0x0f, 0xb7, 0x0f };   /* movzx ecx, word ptr [rdi] */
typedef uint8_t (*comprow_fn)(uint32_t reg, void* row);

/* 1 = skip the regulation in the walk ("no awards"). has_row: the exe's table has a row for it
   (row_awards its +0x29); kind: the record's +0x84, -1 no record; master_kind: for a replica
   the +0x84 of its master's record, -1 for a master or no master record */
static int awgate_decide(int has_row, unsigned row_awards, int kind, int master_kind)
{
  if (has_row) return row_awards == 0;      /* the game's own answer */
  if (kind < 0) return 0;                   /* no record: the walk never reaches one */
  if (kind != REC_KIND_LEAGUE) return 1;    /* a cup phase of ours: as its template row */
  /* kind 1: a league, or one group of a cup's group stage -- skipped as its master is */
  return master_kind >= 0 && master_kind != REC_KIND_LEAGUE;
}

static uint64_t awgate_noaward(uint64_t a, unsigned char* walkrec)
{
  uint16_t id = (uint16_t)a;
  unsigned char row[0x120];
  int has = ((comprow_fn)(uintptr_t)(g_base + COMPROW_RVA))(id, row) != 0;
  unsigned char* r = 0;
  if (!has) r = walkrec && *(uint16_t*)walkrec == id ? walkrec : find_rec(id);
  int kind = r ? (int)*(uint32_t*)(r + 0x84) : -1, master_kind = -1;
  uint16_t master = 0xffff;
  if (r && kind == REC_KIND_LEAGUE) {
    master = *(uint16_t*)(r + REC_PARENT);
    if (master == 0xffff && id >= 0x400) master = id & 0x3ff;
    unsigned char* mr = master != 0xffff && master != id ? find_rec(master) : 0;
    if (mr) master_kind = (int)*(uint32_t*)(mr + 0x84);
  }
  int skip = awgate_decide(has, has ? row[COMPROW_AWARDS] : 0, kind, master_kind);
  if (!has && skip) {
    static uint32_t said[64]; static int nsaid = 0;
    uint32_t comp = *(uint32_t*)(r + 0x80);
    int group = kind == REC_KIND_LEAGUE;      /* one line per competition and per sort */
    uint32_t key = comp << 1 | (uint32_t)group;
    int known = 0;
    for (int k = 0; k < nsaid; k++) known |= said[k] == key;
    if (!known && nsaid < 64) {
      said[nsaid++] = key;
      if (group)
        logf("fl26swiss: Individual Titles / Team of the Competition -- competition %u: regulation %u "
             "(a group of %u, kind 1 as a league's, its group stage kind %d) is not asked for an awards list, "
             "as its group stage is not",
             comp, (unsigned)id, (unsigned)master, master_kind);
      else
        logf("fl26swiss: Individual Titles / Team of the Competition -- competition %u: regulation %u "
             "(no row of the exe's, kind %d) is not asked for an awards list, as a shipped cup's phases are not",
             comp, (unsigned)id, kind);
    }
  }
  return (uint64_t)skip;
}

/* 0 ok; 2 the call is not the one expected (nothing patched); 3 no page in reach; 4 VirtualProtect */
static int awgate_install(uint64_t exe_base)
{
  unsigned char* c = (unsigned char*)(uintptr_t)(exe_base + AWGATE_CALL);
  if (memcmp(c - 3, SIG_AWGATE_PRE, 3) || c[0] != 0xE8 ||
      (uint64_t)(uintptr_t)(c + 5) + *(int32_t*)(c + 1) != exe_base + NOAWARD_RVA)
    return 2;
  unsigned char* t = near_alloc(exe_base);
  if (!t) return 3;
  /* mov rdx, rdi (the walk's record); jmp awgate_noaward */
  t[0] = 0x48; t[1] = 0x89; t[2] = 0xfa;
  t[3] = 0xFF; t[4] = 0x25; *(uint32_t*)(t + 5) = 0; *(uint64_t*)(t + 9) = (uint64_t)(uintptr_t)awgate_noaward;
  FlushInstructionCache(GetCurrentProcess(), t, 17);
  DWORD old;
  if (!VirtualProtect(c, 5, PAGE_EXECUTE_READWRITE, &old)) return 4;
  *(int32_t*)(c + 1) = (int32_t)((int64_t)(uintptr_t)t - (int64_t)(uintptr_t)(c + 5));
  VirtualProtect(c, 5, old, &old);
  FlushInstructionCache(GetCurrentProcess(), c, 5);
  return 0;
}

/* 0 ok; 2 a site is not the one expected (nothing patched); 3 no page in reach; 4 VirtualProtect */
static int po_install(uint64_t exe_base)
{
  unsigned char* call = (unsigned char*)(uintptr_t)(exe_base + POSEL_CALL);
  unsigned char* site = (unsigned char*)(uintptr_t)(exe_base + POTTL_SITE);
  if (call[0] != 0xE8 || (uint64_t)(uintptr_t)(call + 5) + *(int32_t*)(call + 1) != exe_base + ACTCOMP_RVA) return 2;
  if (memcmp(site, SIG_POTTL, 10)) return 2;
  unsigned char* t = near_alloc(exe_base);
  if (!t) return 3;
  /* +0: jmp po_sel */
  t[0] = 0xFF; t[1] = 0x25; *(uint32_t*)(t + 2) = 0; *(uint64_t*)(t + 6) = (uint64_t)(uintptr_t)po_sel;
  /* +0x20: the title stub (about 0x170 bytes, near jumps: the table outgrew rel8); +0x400: the id table */
  g_po_tab = (uint32_t*)(t + 0x400);
  for (int i = 0; i < PO_SLOTS; i++) g_po_tab[i] = 0xffff;
  po_fill();
  unsigned char* s = t + 0x20;
  int n = 0, jn[PO_SLOTS + 2], nj = 0, jo = 0;
  s[n++] = 0x50;                                            /* push rax */
  s[n++] = 0x0f; s[n++] = 0xb7; s[n++] = 0xc6;              /* movzx eax, si */
  /* cmp eax, 8*1024+0x3ff; FL27 16*1024+0x3ff, for the sixteen ties of a 32-club round (q_n) --
     the low id must still be one of the table's, so no shipped replica past 8 is taken */
  s[n++] = 0x3d; *(uint32_t*)(s + n) = g_native_uefa ? 0x43ff : 0x23ff; n += 4;
  s[n++] = 0x0f; s[n++] = 0x87; jo = n; n += 4;             /* ja other (near) */
  /* replica test: ah & 0xfc != 0 -> eax >= 0x400 */
  s[n++] = 0xf6; s[n++] = 0xc4; s[n++] = 0xfc;              /* test ah, 0xfc */
  s[n++] = 0x74; int jz = n++;                              /* jz low (an exact id) */
  s[n++] = 0x25; *(uint32_t*)(s + n) = 0x3ff; n += 4;       /* and eax, 0x3ff */
  s[n++] = 0x83; s[n++] = 0xf8; s[n++] = 0x02;              /* cmp eax, 2 */
  s[n++] = 0x0f; s[n++] = 0x84; jn[nj++] = n; n += 4;       /* je ours (a UCL play-off replica, near) */
  s[jz] = (unsigned char)(n - (jz + 1));
  s[n++] = 0x25; *(uint32_t*)(s + n) = 0x3ff; n += 4;       /* low: and eax, 0x3ff */
  for (int i = 0; i < PO_SLOTS; i++) {                      /* cmp eax, [rip -> tab+i] ; je ours */
    s[n++] = 0x3b; s[n++] = 0x05;
    *(int32_t*)(s + n) = (int32_t)((unsigned char*)(g_po_tab + i) - (s + n + 4)); n += 4;
    s[n++] = 0x0f; s[n++] = 0x84; jn[nj++] = n; n += 4;     /* near */
  }
  *(int32_t*)(s + jo) = n - (jo + 4);
  s[n++] = 0x58;                                            /* other: pop rax */
  s[n++] = 0x66; s[n++] = 0x83; s[n++] = 0xee; s[n++] = 0x45; /* sub si, 0x45 */
  s[n++] = 0x66; s[n++] = 0x83; s[n++] = 0xfe; s[n++] = 0x04; /* cmp si, 4 */
  s[n++] = 0xFF; s[n++] = 0x25; *(uint32_t*)(s + n) = 0; n += 4;
  *(uint64_t*)(s + n) = exe_base + POTTL_RESUME; n += 8;    /* jmp resume (the jbe) */
  for (int i = 0; i < nj; i++) *(int32_t*)(s + jn[i]) = n - (jn[i] + 4);
  s[n++] = 0x58;                                            /* ours: pop rax */
  s[n++] = 0xFF; s[n++] = 0x25; *(uint32_t*)(s + n) = 0; n += 4;
  *(uint64_t*)(s + n) = exe_base + POTTL_NATIVE; n += 8;    /* jmp the Play-offs branch */
  FlushInstructionCache(GetCurrentProcess(), t, 0x400 + 4 * PO_SLOTS);
  DWORD old;
  if (!VirtualProtect(call, 5, PAGE_EXECUTE_READWRITE, &old)) return 4;
  *(int32_t*)(call + 1) = (int32_t)((int64_t)(uintptr_t)t - (int64_t)(uintptr_t)(call + 5));
  VirtualProtect(call, 5, old, &old);
  FlushInstructionCache(GetCurrentProcess(), call, 5);
  if (!VirtualProtect(site, 8, PAGE_EXECUTE_READWRITE, &old)) return 4;
  site[0] = 0xE9; *(int32_t*)(site + 1) = (int32_t)((int64_t)(uintptr_t)s - (int64_t)(uintptr_t)(site + 5));
  site[5] = site[6] = site[7] = 0x90;
  VirtualProtect(site, 8, old, &old);
  FlushInstructionCache(GetCurrentProcess(), site, 8);
  return 0;
}

/* ---- "League Phase", not "Group A" ----
 *
 * The game names a group with text 0x3a20013 ("Group %s", the letter as the argument) in five
 * places: the standings header and its sibling (0x140af53e0, 0x140af52b0), two group-table
 * widgets (0x140ca5110, 0x140cb9900) and 0x1412aa680; and the match title 0x14152a590 puts
 * text 0x3a20011, "Group stage", in front of "Matchday %d". Our league phase is one group of
 * 36, so it read "Group A" and "Group stage". Each `mov edx, <text>` (5 bytes) becomes a call
 * to a small stub that keeps every volatile register but edx, asks grp_text, and loads edx
 * with the answer: LP_TEXT ("League Phase", txtget_handler) for one of our league phases, the
 * game's own text otherwise -- the letter argument is then simply not used. The regulation
 * comes from si in the title, from the record the caller read at 0x1412aaf3e, and elsewhere
 * from the screen's active competition (0x14150c230, as the Match Results selector asks it);
 * those only when the letter is "A", the one group a league phase has. */
#define GRP_GROUP 0x3a20013u
#define GRP_STAGE 0x3a20011u
/* kind 0 active, 1 si, 2 word [r13-0x10], 3 the standings widget in rsi, 4 its sibling in r14.
 * The two standings headers ran on kind 0, but on Competition Info -> Standings the active
 * competition is not set and the resolver answers 0xffff (08.10.: "Group A at 140af54b4 for
 * regulation 65535 -> kept"), so they read the widget they draw instead: 0x140af72b0 calls
 * 0x140af53e0 with rsi = the widget, 0x140af6ce0 calls 0x140af52b0 with r14 = its sibling, and
 * neither callee touches that register.  The widget holds the shown phase's groups (a vector of
 * 24-byte vectors at +0xa0, rows 0x28 bytes; the sibling's at +0xb0) -- our league phase is the
 * only phase of one group with 24 or more clubs. */
typedef struct { uint32_t rva, text; int kind; } grp_site_t;
static const grp_site_t GRP_SITES[] = {
  { 0xaf5384,  GRP_GROUP, 4 }, { 0xaf54b4,  GRP_GROUP, 3 }, { 0xca5d8c, GRP_GROUP, 0 },
  { 0xcb9e2d,  GRP_GROUP, 0 }, { 0x12aaf3e, GRP_GROUP, 2 }, { 0x152a75c, GRP_STAGE, 1 } };
#define GRP_N ((int)(sizeof GRP_SITES / sizeof GRP_SITES[0]))

static int lp_ours(uint32_t id)
{
  if (id > 0xffff || (id >> 10) > 8) return 0;
  for (int i = 0; i < g_nreg; i++) if ((g_reg[i] & 0x3ff) == (id & 0x3ff)) return 1;
  return 0;
}

/* one group of 24 or more: the widget's groups at +vec, rows of 0x28 bytes (sibling: groups only) */
static int grp_one_big(const unsigned char* w, int vec, int rows_known)
{
  if (!w || IsBadReadPtr(w + vec, 16)) return 0;
  const unsigned char* b = *(unsigned char* const*)(w + vec);
  const unsigned char* e = *(unsigned char* const*)(w + vec + 8);
  if (!b || e - b != 24) return 0;
  if (!rows_known) return 1;
  const unsigned char* rb = *(unsigned char* const*)b;
  const unsigned char* re = *(unsigned char* const*)(b + 8);
  return rb && re > rb && (re - rb) % 0x28 == 0 && (re - rb) / 0x28 >= 24;
}

static uint32_t grp_text(uint32_t text, uint64_t arg, const char* letter, uint32_t site)
{
  if (!g_tramp_txtget || !g_nreg) return text;
  int kind = GRP_SITES[site].kind;
  uint32_t reg = kind >= 3 ? 0xffffffffu : (uint32_t)arg;
  if (text == GRP_GROUP) {
    if (!letter || letter[0] != 'A' || letter[1]) return text;
    if (kind >= 3) {
      int big = grp_one_big((const unsigned char*)(uintptr_t)arg, kind == 3 ? 0xa0 : 0xb0, kind == 3);
      static int said_w = 0;
      if (said_w < 6) { said_w++; logf("fl26swiss: Group A at %llx -- the shown phase is %s",
          (unsigned long long)(0x140000000ull + GRP_SITES[site].rva), big ? "one group of 24+ (League Phase)" : "not ours"); }
      return big ? LP_TEXT : text;
    }
    if (reg == 0xffffffffu) {
      unsigned char* o = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
      unsigned char* blk = o ? *(unsigned char**)(o + 0x48) : 0;
      if (!blk) return text;
      reg = (uint16_t)((actcomp_fn)(uintptr_t)(g_base + ACTCOMP_RVA))(*(uint32_t*)(blk + LIBQ_SELCOMP_OFF),
                                                                       *(uint16_t*)(blk + TODAY_OFF), 0, 0);   /* today, as the game's own call at 0x140af9414 reads it once fl26caps moved it */
    }
  }
  int ours = lp_ours(reg);
  static int said = 0;
  if (said < 12 && (text == GRP_GROUP || ours)) {
    said++;
    logf("fl26swiss: %s at %llx for regulation %u -> %s", text == GRP_GROUP ? "Group A" : "Group stage",
         (unsigned long long)(0x140000000ull + GRP_SITES[site].rva), reg, ours ? "League Phase" : "kept");
  }
  return ours ? LP_TEXT : text;
}

/* 0 ok; 2 a site is not the one expected (nothing patched); 3 no page in reach; 4 VirtualProtect */
static int grp_install(uint64_t exe_base)
{
  for (int i = 0; i < GRP_N; i++) {
    unsigned char* s = (unsigned char*)(uintptr_t)(exe_base + GRP_SITES[i].rva);
    if (s[0] != 0xBA || *(uint32_t*)(s + 1) != GRP_SITES[i].text) return 2;
  }
  unsigned char* t = near_alloc(exe_base);
  if (!t) return 3;
  unsigned char* stub[GRP_N];
  int n = 0;
  for (int i = 0; i < GRP_N; i++) {
    stub[i] = t + n;
    t[n++] = 0x50; t[n++] = 0x51;                             /* push rax; push rcx */
    t[n++] = 0x41; t[n++] = 0x50; t[n++] = 0x41; t[n++] = 0x51; /* push r8; push r9 */
    t[n++] = 0x41; t[n++] = 0x52; t[n++] = 0x41; t[n++] = 0x53; /* push r10; push r11 */
    t[n++] = 0x48; t[n++] = 0x83; t[n++] = 0xec; t[n++] = 0x28; /* sub rsp, 0x28 */
    t[n++] = 0xb9; *(uint32_t*)(t + n) = GRP_SITES[i].text; n += 4;   /* mov ecx, text */
    if (GRP_SITES[i].kind == 1) { t[n++] = 0x0f; t[n++] = 0xb7; t[n++] = 0xd6; }              /* movzx edx, si */
    else if (GRP_SITES[i].kind == 2) { t[n++] = 0x41; t[n++] = 0x0f; t[n++] = 0xb7; t[n++] = 0x55; t[n++] = 0xf0; } /* movzx edx, word [r13-0x10] */
    else if (GRP_SITES[i].kind == 3) { t[n++] = 0x48; t[n++] = 0x89; t[n++] = 0xf2; }       /* mov rdx, rsi */
    else if (GRP_SITES[i].kind == 4) { t[n++] = 0x4c; t[n++] = 0x89; t[n++] = 0xf2; }       /* mov rdx, r14 */
    else { t[n++] = 0xba; *(uint32_t*)(t + n) = 0xffffffffu; n += 4; }                        /* mov edx, -1 */
    t[n++] = 0x41; t[n++] = 0xb9; *(uint32_t*)(t + n) = (uint32_t)i; n += 4;                  /* mov r9d, site */
    t[n++] = 0x48; t[n++] = 0xb8; *(uint64_t*)(t + n) = (uint64_t)(uintptr_t)grp_text; n += 8; /* mov rax, grp_text */
    t[n++] = 0xff; t[n++] = 0xd0;                             /* call rax */
    t[n++] = 0x48; t[n++] = 0x83; t[n++] = 0xc4; t[n++] = 0x28; /* add rsp, 0x28 */
    t[n++] = 0x89; t[n++] = 0xc2;                             /* mov edx, eax */
    t[n++] = 0x41; t[n++] = 0x5b; t[n++] = 0x41; t[n++] = 0x5a; /* pop r11; pop r10 */
    t[n++] = 0x41; t[n++] = 0x59; t[n++] = 0x41; t[n++] = 0x58; /* pop r9; pop r8 */
    t[n++] = 0x59; t[n++] = 0x58; t[n++] = 0xc3;              /* pop rcx; pop rax; ret */
  }
  FlushInstructionCache(GetCurrentProcess(), t, n);
  for (int i = 0; i < GRP_N; i++) {
    unsigned char* s = (unsigned char*)(uintptr_t)(exe_base + GRP_SITES[i].rva);
    DWORD old;
    if (!VirtualProtect(s, 5, PAGE_EXECUTE_READWRITE, &old)) return 4;
    s[0] = 0xE8; *(int32_t*)(s + 1) = (int32_t)((int64_t)(uintptr_t)stub[i] - (int64_t)(uintptr_t)(s + 5));
    VirtualProtect(s, 5, old, &old);
    FlushInstructionCache(GetCurrentProcess(), s, 5);
  }
  return 0;
}

/* ---- Competition Info for the continental cups: a list, not a bracket; Round of 16; one item a round ----
 * (11.10.)
 *
 * 1. List, not bracket. Competition Info -> Fixtures ("tournamentdraw") opens
 *    MatchResultsFactory::CreateObjectTournament (0x140af9810, registered for
 *    Common/CmnTournamentMenu). It shows the round-by-round list (0x140caa5a0) for the
 *    competition ids it knows -- 2, 3, 5, 6, 8, 43, 44 (mask 0x180000000016c), 70-72, 91, 97,
 *    103, 128 (mask 0x400000208200007 from 70) -- or when 0x141548120(knockout) says so, and a
 *    bracket otherwise: MenuModeTournamentProgress, or TournamentProgressOver32 above 32 clubs
 *    (+0x308 bits 16-22). The Conference League (competition 174) and the continental cups the
 *    world builder adds (ccup lines with a group stage, not a league cup's like=) are none of
 *    them, so they got a bracket. The call of 0x141548120 at 0x140af98c9 goes through kolist_test,
 *    which answers yes for their knockouts and asks the game for everything else.
 *
 * 2. Round of 16. The list labels every tie with the match title 0x14152a590 (through
 *    0x14152af20), which for the first knockout round (kind 0x2e) goes by the competition id:
 *    2 -> "First knockout round" (0x3a20017), 3 -> "Round of 32" (0x3a20018) whatever the size,
 *    5/6/8/48/91 -> "Round of 16"; any other id by its clubs (+0x30a, else +0x30c), and a
 *    knockout of 9-31 clubs after a group (+0x7a set) is "First knockout round" again. Since 2024
 *    the UEFA knockout starts with sixteen clubs, so for the knockouts of our three cups (4, 6,
 *    187, in a world with our league phases) and for the world-built continental cups' knockouts
 *    of 9-16 clubs the title takes the competition-8 branch, which reads "Round of 16" (long
 *    0x3a20019, short 0x5000bf). The schedule's match line (0x140cade70, the same switch on the
 *    competition id) is answered from the same rule, all sizes. Both are a 5/6-byte jump at the
 *    switch's first case into a stub that asks ko_text and, without an answer, runs the original
 *    compare.
 *
 * 3. One item a round. The competition-wide menu (0x14151f5f0, items of 0x30 bytes: type, enabled
 *    @4, text @8, the flow name as a std::string @0x10) has one item per type, and the grouped
 *    phase's item rolls with the summer (phkind_handler). ci_menu_handler adds, after the game has
 *    built the list, an item for each qualifying round of the cup that holds clubs and is not the
 *    one the native item shows: second qualifying round, third qualifying round, play-off (or
 *    "Knockout round play-offs" in the February window) -- same flow name "playoff", so the same
 *    page opens. Which item was chosen is read when the menu asks for the chosen item's flow entry
 *    (0x140e3d310: entry +0x28 list 2, +0x2c the item's index, as 0x140affc10 registered it), and
 *    the page builder's grouped-phase lookup (PAGE_GRP_RA) is then given that round's regulation.
 */
#define CIV_VTBL     0x2689d98   /* CompeViewItemSelect's vtable (Common/CmnCompeInfoMenu) */
#define CIMENU_RVA   0x151f5f0
#define CIPUSH_RVA   0x152c9e0   /* vector<item>::push_back(vec, const item*) */
#define CISEL_RVA    0x0e3d310   /* (menu) -> the chosen item's flow entry */
#define KOLIST_CALL  0x0af98c9
#define KOLIST_RVA   0x1548120
#define SCHED_SITE   0x0cae1db   /* cmp ebx,2; jne -- kind 0x2e in 0x140cade70 */
#define SCHED_TEXT   0x0cae217   /* lea rcx,[rsp+0x50]; call 0x141496ca0; jmp */
#define SCHED_C2     0x0cae1e0
#define SCHED_NOT2   0x0cae1f4
#define TITLE_SITE   0x152a9e7   /* cmp r14d,2; jne -- kind 0x2e in 0x14152a590 */
#define TITLE_R16    0x152aa31   /* the competition-8 branch: Round of 16, long or short */
#define TITLE_C2     0x152a9ed
#define TITLE_NOT2   0x152aa09
static const unsigned char SIG_CIMENU[17] = {
  0x40, 0x55, 0x56, 0x57, 0x41, 0x54, 0x41, 0x55, 0x41, 0x56, 0x41, 0x57, 0x48, 0x8d, 0x6c, 0x24, 0xd9 };
static const unsigned char SIG_CISEL[20] = {
  0x48, 0x89, 0x5c, 0x24, 0x08, 0x57, 0x48, 0x83, 0xec, 0x20, 0x48, 0x8b, 0xf9, 0x48, 0x8b, 0x89, 0x88, 0x00, 0x00, 0x00 };
static const unsigned char SIG_SCHED[5]  = { 0x83, 0xfb, 0x02, 0x75, 0x14 };
static const unsigned char SIG_SCHEDT[5] = { 0x48, 0x8d, 0x4c, 0x24, 0x50 };
static const unsigned char SIG_TITLE[6]  = { 0x41, 0x83, 0xfe, 0x02, 0x75, 0x1c };
static const unsigned char SIG_TITLER[7] = { 0x48, 0x8d, 0x4c, 0x24, 0x50, 0x84, 0xdb };

/* a world-built continental cup's knockout (a ccup with a group stage, not a league cup's copy) */
static int ccup_cont_ko(uint16_t reg)
{
  for (int k = 0; k < g_nccup; k++) {
    const ccup_t* c = &g_ccup[k];
    if (c->groups && !c->like && reg == c->ko) return 1;
  }
  return 0;
}
/* the knockout of one of our UEFA cups, in a world with our league phases: its CUPS index, -1 none */
static int uefa_ko_of(uint16_t reg)
{
  for (int ci = 0; ci < 3; ci++) {
    const cup_t* c = &CUPS[ci];
    if (cup_on(ci) && ((reg & 0x3ff) == c->ko && (reg >> 10) <= 16) && (lp_ours(c->league) || lp_ours(c->row))) return ci;
  }
  return -1;
}
/* The first knockout round's name for our continental knockouts, 0 = the game's own. */
static uint32_t g_kotext_n = 0;
static uint32_t ko_text(uint32_t comp, uint32_t reg, uint32_t clubs, const char* where)
{
  uint32_t n = 0;
  if (uefa_ko_of((uint16_t)reg) >= 0) n = 16;           /* UEFA, since 2024: the round of 16 */
  else if (ccup_cont_ko((uint16_t)reg)) n = clubs & 0x7f;
  if (!n) return 0;
  uint32_t t = n > 16 ? 0x3a20018u : n > 8 ? 0x3a20019u : n > 4 ? 0x3a2001bu : n > 2 ? 0x3a2001cu : 0x3a2001du;
  if (g_kotext_n++ < 6)
    logf("fl26swiss: %s -- knockout %u (competition %u, %u clubs): first round named %s", where, reg, comp, n,
         t == 0x3a20019u ? "Round of 16" : t == 0x3a20018u ? "Round of 32" : t == 0x3a2001bu ? "Quarter-finals" :
         t == 0x3a2001cu ? "Semi-finals" : "Final");
  return t;
}
uint64_t ko_sched_text(uint64_t comp, uint64_t reg, uint64_t clubs, uint64_t prev)
{
  (void)prev;
  return ko_text((uint32_t)comp, (uint32_t)(uint16_t)reg, (uint32_t)clubs, "schedule");
}
uint64_t ko_title_r16(uint64_t comp, uint64_t reg, uint64_t clubs, uint64_t prev)
{
  (void)prev;
  return ko_text((uint32_t)comp, (uint32_t)(uint16_t)reg, (uint32_t)clubs, "match title") == 0x3a20019u;
}

typedef uint64_t (*kolist_fn)(uint64_t reg);
static uint32_t g_kolist_n = 0;
uint64_t kolist_test(uint64_t reg)
{
  uint16_t id = (uint16_t)reg;
  if ((id == UECL_KO && (lp_ours(UECL_REG) || lp_ours(UECL_ROW))) || ccup_cont_ko(id)) {
    if (g_kolist_n++ < 6) logf("fl26swiss: Competition Info -- knockout %u shown as a list, not a bracket", (unsigned)id);
    return 1;
  }
  return ((kolist_fn)(uintptr_t)(g_base + KOLIST_RVA))(reg);
}

typedef struct { uint32_t type; uint8_t en; uint8_t pad[3]; uint32_t text; uint32_t pad2;
                 char buf[16]; uint64_t size, cap; } ci_item_t;
_Static_assert(sizeof(ci_item_t) == 0x30, "Competition Info item is 0x30 bytes");
typedef struct { ci_item_t *b, *e, *c; } ci_vec_t;
typedef uint64_t (*cimenu_fn)(ci_vec_t* v, uint32_t* comp, uint64_t flag);
typedef void (*cipush_fn)(ci_vec_t* v, const ci_item_t* it);
typedef unsigned char* (*cisel_fn)(unsigned char* menu);
unsigned char* g_tramp_cimenu = 0;
unsigned char* g_tramp_cisel = 0;
#define CI_MAX 32
static ci_vec_t* g_ci_vec = 0;
static int g_ci_n = 0;
static uint16_t g_ci_reg[CI_MAX];
static uint32_t g_ci_comp = 0xffffffffu, g_ci_menu_n = 0, g_ci_sel_n = 0;

/* Libertadores F1/F2/F3 are pages of the native qualifying item; the rejected
   separate-menu-item experiment is intentionally not used. */

uint64_t ci_menu_handler(ci_vec_t* v, uint32_t* comp, uint64_t flag)
{
  g_ci_native = 0xffff; g_ci_native_comp = 0xffffffffu;
  g_mr_pick = 0xffff;                        /* B266: the menu is Competition Info's, not Match Results' */
  uint64_t r = ((cimenu_fn)(uintptr_t)g_tramp_cimenu)(v, comp, flag);
  g_ci_pick = 0xffff;
  if (v == g_ci_vec) { g_ci_vec = 0; g_ci_n = 0; }
  if (!v || !comp || !v->b || v->e < v->b || !g_tramp_txtget) return r;
  /* B219 (antonimus 23.10.): the Libertadores' qualifying item ("Qualifying Round") went grey once
     its phases were played and stayed grey all season. Its F1/F2/F3 are filled by this module,
     not by the game's draw, and the menu (no phase-kind call for this item) greys it on a mark the
     draw would have set. While one of its phases holds clubs it is enabled; it opens the same
     page, which asks for the phase itself (PAGE_GRP_RA). */
  int want = *comp == CONM_LIB_CID ? libq_item_want() : -1;
  if (want >= 0) {
    int n = (int)(v->e - v->b), lit = 0;
    for (int k = 0; k < n; k++)
      if (v->b[k].en != want && v->b[k].size == 7 && !memcmp(v->b[k].buf, "playoff", 7)) {
        v->b[k].en = (uint8_t)want;
        lit += want ? 1 : -1;
      }
    static int said_libq = 0;
    if (lit && said_libq++ < 6) {
      char items[160]; int o = 0;
      for (int k = 0; k < n && k < 10 && o < 140; k++)
        o += snprintf(items + o, sizeof items - o, " %u/%u/%.7s", v->b[k].type, v->b[k].en, v->b[k].size < 16 ? v->b[k].buf : "-");
      logf("fl26swiss: Competition Info -- Libertadores menu, qualifying item %s (day %d):%s", lit > 0 ? "on" : "grey", today(), items);
    }
  }


  int ci = ci_of_comp(*comp);
  if (ci < 0) {
    /* Modern Sudamericana keeps both its first stage and its post-group play-off
       in hidden technical competitions. Expose both as pages of the main cup:
         First stage -> Group stage -> Play-offs -> native knockout/stat pages.
       The hidden competitions remain runtime containers only. */
    int sk = modern_suda_ccup();
    const ccup_t* sc = sk >= 0 ? &g_ccup[sk] : 0;
    unsigned char* sr = sc ? find_rec(sc->reg) : 0;
    if (!sc || !sr || *(uint32_t*)(sr + 0x80) != *comp) return r;

    int fi = -1, pi = -1;
    for (int i = 0; i < g_nlpre; i++) {
      if (lpre_is_suda(&g_lpre[i])) fi = i;
      if (g_lpre[i].poko && g_lpre[i].ko == sc->ko) pi = i;
    }
    if (fi < 0 || pi < 0) return r;

    unsigned char* fm = find_rec(g_lpre[fi].reg);
    unsigned char* pm = find_rec(g_lpre[pi].reg);
    if (!fm || !pm) return r;

    int n = (int)(v->e - v->b);
    if (n + 2 > CI_MAX) return r;

    /* Native Group stage is page type 2. Put the first stage immediately before
       it, then put the post-group play-off immediately after it. */
    int gp = -1;
    for (int k = 0; k < n; k++)
      if (v->b[k].type == 2) { gp = k; break; }
    /* B219 (antonimus 23.10.): no Group stage item yet -- B205 leaves it out until the groups are
       drawn (day 49), and the first stage is played before that (day 44): the first stage then
       went missing from the menu exactly while it was on. It goes at the top, where it stands
       once the groups are drawn; the post-group play-off waits for the Group stage item. */
    if (gp < 0) {
      ci_item_t only;
      memset(&only, 0, sizeof only);
      only.type = 0;
      only.en = today() >= g_lpre[fi].fill ? 1 : 0;
      only.text = SUD1_TEXT;
      memcpy(only.buf, "playoff", 8);
      only.size = 7;
      only.cap = 15;
      ((cipush_fn)(uintptr_t)(g_base + CIPUSH_RVA))(v, &only);
      int m1 = (int)(v->e - v->b);
      if (m1 != n + 1) {
        logf("fl26swiss: Competition Info -- Sudamericana first-stage item not added (vector %d -> %d)", n, m1);
        return r;
      }
      ci_item_t top = v->b[m1 - 1];
      memmove(v->b + 1, v->b, (size_t)(m1 - 1) * sizeof(ci_item_t));
      v->b[0] = top;
      g_sud1_reg = g_lpre[fi].reg;
      g_ci_reg[0] = g_lpre[fi].reg;
      for (int k = 1; k < m1; k++) g_ci_reg[k] = 0xffff;
      g_ci_n = m1;
      g_ci_vec = v;
      g_ci_comp = *comp;
      if (g_ci_menu_n++ < 12)
        logf("fl26swiss: Competition Info -- Sudamericana first stage reg %u at item 0 (%s), no Group stage item yet",
             (unsigned)g_lpre[fi].reg, only.en ? "enabled" : "grey until drawn");
      return r;
    }

    uint16_t first_reg = g_lpre[fi].reg;
    uint16_t post_reg = g_lpre[pi].reg;
    g_sud1_reg = first_reg;

    unsigned char* ftie = find_rec(lpre_tie(&g_lpre[fi], 0));
    ci_item_t first;
    memset(&first, 0, sizeof first);
    first.type = 0;
    /* The helper tie rows can be cleared/recycled after feeding the group stage,
       so tie 0 is not a reliable historical enable flag. Once its fill day has
       been reached, keep the phase available in Competition Info. */
    first.en = today() >= g_lpre[fi].fill ? 1 : 0;
    first.text = SUD1_TEXT;
    memcpy(first.buf, "playoff", 8);
    first.size = 7;
    first.cap = 15;
    ((cipush_fn)(uintptr_t)(g_base + CIPUSH_RVA))(v, &first);

    int m = (int)(v->e - v->b);
    if (m != n + 1) {
      logf("fl26swiss: Competition Info -- Sudamericana first-stage item not added (vector %d -> %d)", n, m);
      return r;
    }

    ci_item_t last = v->b[m - 1];
    memmove(v->b + gp + 1, v->b + gp, (size_t)(m - 1 - gp) * sizeof(ci_item_t));
    v->b[gp] = last;

    /* Group stage moved one slot to gp+1; the play-off belongs right after it. */
    unsigned char* ptie = find_rec(lpre_tie(&g_lpre[pi], 0));
    ci_item_t post;
    memset(&post, 0, sizeof post);
    post.type = 0;
    post.en = ptie && rec_count(ptie) ? 1 : 0;
    post.text = 0x3a20010u;
    memcpy(post.buf, "playoff", 8);
    post.size = 7;
    post.cap = 15;
    ((cipush_fn)(uintptr_t)(g_base + CIPUSH_RVA))(v, &post);

    int z = (int)(v->e - v->b);
    if (z != n + 2) {
      logf("fl26swiss: Competition Info -- Sudamericana play-off item not added (vector %d -> %d)", m, z);
      return r;
    }

    int pp = gp + 2;
    last = v->b[z - 1];
    memmove(v->b + pp + 1, v->b + pp, (size_t)(z - 1 - pp) * sizeof(ci_item_t));
    v->b[pp] = last;

    uint16_t map[CI_MAX];
    for (int k = 0; k < z; k++) map[k] = 0xffff;
    map[gp] = first_reg;
    map[pp] = post_reg;
    memcpy(g_ci_reg, map, (size_t)z * sizeof map[0]);
    g_ci_n = z;
    g_ci_vec = v;
    g_ci_comp = *comp;

    if (g_ci_menu_n++ < 12)
      logf("fl26swiss: Competition Info -- Sudamericana pages: first stage reg %u at item %d (%s), play-off reg %u at item %d (%s)",
           (unsigned)first_reg, gp, first.en ? "enabled" : "grey until drawn",
           (unsigned)post_reg, pp, post.en ? "enabled" : "grey until drawn");
    return r;
  }
  uint16_t native = g_ci_native_comp == *comp ? g_ci_native : 0xffff;
  uint16_t xr[NQS]; uint32_t xt[NQS]; int nx = 0;
  for (int st = NQS - 1; st >= 0; st--) {                 /* (1st,) 2nd, 3rd qualifying, play-off */
    int i = ci + NQ * st;
    uint16_t q = q_reg(i);
    if (!q || q == native || !find_rec(q)) continue;
    /* The Champions League's play-off is reg 2, the game's own grouped-phase item, and in February
       that regulation holds the knockout play-off: the native item then opens it under the same
       name, and ours was a second "Knockout round play-offs" with the same ties (13.10., in game;
       the August ties are gone from the regulation by then, po_start draws over them). A native
       item already carrying the name this one would get is that round. */
    if (st == 0) {
      uint32_t want = kopo_window(ci) ? KOPO_TEXT : 0x3a20010u;
      int dup = 0;
      for (ci_item_t* k = v->b; k < v->e; k++) if (k->text == want) dup = 1;
      if (dup) {
        static int said_dup = 0;
        if (said_dup++ < 4) logf("fl26swiss: Competition Info -- %s play-off item left out: a native item already shows it",
                                 CUPS[ci].name);
        continue;
      }
    }
    unsigned char* tie = find_rec(q_tie_of(i, 0));
    if (!tie || !rec_count(tie)) continue;
    xr[nx] = q;
    xt[nx] = st ? QR_TEXT(st) : kopo_window(ci) ? KOPO_TEXT : 0x3a20010u;
    nx++;
  }
  int n = (int)(v->e - v->b);
  if (!nx || n + nx > CI_MAX) return r;
  /* in front of the native grouped-phase item (type 0), else of the first item listed after it in
     the game's table (0x142980850: 3, 4, 12, 0, then 2, 6, 1, 7, 8, 10, 11, 9), else at the end */
  int pos = -1;
  for (int k = 0; k < n && pos < 0; k++) if (v->b[k].type == 0) pos = k;
  for (int k = 0; k < n && pos < 0; k++) { uint32_t t = v->b[k].type; if (t != 3 && t != 4 && t != 12) pos = k; }
  if (pos < 0) pos = n;
  uint16_t map[CI_MAX];
  for (int k = 0; k < n; k++) map[k] = 0xffff;
  for (int j = 0; j < nx; j++) {
    ci_item_t it;
    memset(&it, 0, sizeof it);
    it.type = 0; it.en = 1; it.text = xt[j];
    memcpy(it.buf, "playoff", 8); it.size = 7; it.cap = 15;   /* the native item's flow name, in place */
    ((cipush_fn)(uintptr_t)(g_base + CIPUSH_RVA))(v, &it);
    int m = (int)(v->e - v->b);
    if (m != n + 1) { logf("fl26swiss: Competition Info -- item not added (vector %d -> %d)", n, m); break; }
    ci_item_t last = v->b[m - 1];                          /* std::string relocates bitwise (no proxy) */
    memmove(v->b + pos + 1, v->b + pos, (size_t)(m - 1 - pos) * sizeof(ci_item_t));
    v->b[pos] = last;
    memmove(map + pos + 1, map + pos, (size_t)(n - pos) * sizeof map[0]);
    map[pos] = xr[j];
    n = m; pos++;
  }
  memcpy(g_ci_reg, map, (size_t)n * sizeof map[0]);
  g_ci_n = n; g_ci_vec = v; g_ci_comp = *comp;
  if (g_ci_menu_n++ < 12) {
    char b[128]; int o = 0;
    for (int k = 0; k < n && o < 100; k++)
      if (map[k] != 0xffff) o += snprintf(b + o, sizeof b - o, " %u@%d", (unsigned)map[k], k);
    b[o] = 0;
    logf("fl26swiss: Competition Info -- %s menu: %d item(s) for its rounds (regulation@item:%s; the native item shows %u)",
         CUPS[ci].name, nx, b, (unsigned)native);
  }
  return r;
}
/* 0x140e3d310(flow) is not given the menu and does not return an item: `flow` is the screen's flow
   object, its context at +0x88 holds the transition entries (+0x398..+0x3a0, 0x30 each: +0x28 the
   list, +0x2c the item index or -1 for any, +8 the target flow name as a std::string), the current
   list at +0xa0 and the chosen item's index at +0xd8, and it returns the name of the flow the chosen
   item leads to (12.10., in game: the old reading never fired, every item opened the current round).
   Our items lead to "playoff" like the native grouped-phase item, so a "playoff" answer while our
   menu is up takes the chosen index from +0xd8. */
unsigned char* ci_sel_handler(unsigned char* flow)
{
  unsigned char* e = ((cisel_fn)(uintptr_t)g_tramp_cisel)(flow);
  if (!e || !flow || !g_ci_vec || strcmp((const char*)e, "playoff")) return e;
  unsigned char* ctx = *(unsigned char**)(flow + 0x88);
  if (!ctx) return e;
  int list = *(int32_t*)(ctx + 0xa0), idx = *(int32_t*)(ctx + 0xd8), alt = *(int32_t*)(ctx + 0xfc);
  uint16_t p = idx >= 0 && idx < g_ci_n ? g_ci_reg[idx] : 0xffff;
  g_ci_pick = p; g_ci_pick_comp = g_ci_comp;
  if (g_ci_sel_n++ < 16) {
    if (p != 0xffff) logf("fl26swiss: Competition Info -- item %d chosen: regulation %u (list %d, +0xfc %d)", idx, (unsigned)p, list, alt);
    else logf("fl26swiss: Competition Info -- item %d chosen, the game's own (list %d, +0xfc %d, %d items)", idx, list, alt, g_ci_n);
  }
  return e;
}

static int ci_jmp(unsigned char* s, int n, uint64_t to)
{
  s[n++] = 0xFF; s[n++] = 0x25; *(uint32_t*)(s + n) = 0; n += 4; *(uint64_t*)(s + n) = to; n += 8;
  return n;
}
/* The stub both label sites share: align the stack, call fn(ecx, edx, r8d, r9d) as loaded by `ld`
   (ld_n bytes), restore; eax != 0 -> (mov edx, eax when keep_edx) jmp yes; else the replaced
   compare (cmp_n bytes), then jne no / jmp eq. Every volatile register is dead at both sites (the
   paths that follow load them afresh or call). Returns the stub's length. */
static int ci_stub(unsigned char* s, const unsigned char* ld, int ld_n, void* fn, int keep_edx, uint64_t yes,
                   const unsigned char* cmp, int cmp_n, uint64_t eq, uint64_t no)
{
  int n = 0;
  static const unsigned char PRO[12] = { 0x55, 0x48, 0x89, 0xe5, 0x48, 0x83, 0xe4, 0xf0, 0x48, 0x83, 0xec, 0x20 };
  memcpy(s + n, PRO, 12); n += 12;                                                    /* push rbp; mov rbp,rsp; and rsp,-16; sub rsp,0x20 */
  memcpy(s + n, ld, ld_n); n += ld_n;
  s[n++] = 0x48; s[n++] = 0xb8; *(uint64_t*)(s + n) = (uint64_t)(uintptr_t)fn; n += 8;   /* mov rax, fn */
  s[n++] = 0xff; s[n++] = 0xd0;                                                       /* call rax */
  s[n++] = 0x48; s[n++] = 0x89; s[n++] = 0xec; s[n++] = 0x5d;                         /* mov rsp, rbp; pop rbp */
  s[n++] = 0x85; s[n++] = 0xc0;                                                       /* test eax, eax */
  s[n++] = 0x74; int jz = n++;                                                        /* jz orig */
  if (keep_edx) { s[n++] = 0x89; s[n++] = 0xc2; }                                     /* mov edx, eax */
  n = ci_jmp(s, n, yes);
  s[jz] = (unsigned char)(n - (jz + 1));
  memcpy(s + n, cmp, cmp_n); n += cmp_n;                                              /* orig: the compare */
  s[n++] = 0x75; s[n++] = 14;                                                         /* jne no */
  n = ci_jmp(s, n, eq);
  n = ci_jmp(s, n, no);
  return n;
}
static int ci_patch(unsigned char* site, int len, unsigned char* to)
{
  DWORD old;
  if (!VirtualProtect(site, len, PAGE_EXECUTE_READWRITE, &old)) return 4;
  site[0] = 0xE9; *(int32_t*)(site + 1) = (int32_t)((int64_t)(uintptr_t)to - (int64_t)(uintptr_t)(site + 5));
  for (int i = 5; i < len; i++) site[i] = 0x90;
  VirtualProtect(site, len, old, &old);
  FlushInstructionCache(GetCurrentProcess(), site, len);
  return 0;
}
/* list instead of bracket: 0 ok; 2 the call is not the one expected; 3 no page in reach; 4 VirtualProtect */
static int kolist_install(uint64_t exe_base)
{
  unsigned char* c = (unsigned char*)(uintptr_t)(exe_base + KOLIST_CALL);
  if (c[0] != 0xE8 || (uint64_t)(uintptr_t)(c + 5) + *(int32_t*)(c + 1) != exe_base + KOLIST_RVA) return 2;
  unsigned char* t = near_alloc(exe_base);
  if (!t) return 3;
  ci_jmp(t, 0, (uint64_t)(uintptr_t)kolist_test);
  FlushInstructionCache(GetCurrentProcess(), t, 14);
  DWORD old;
  if (!VirtualProtect(c, 5, PAGE_EXECUTE_READWRITE, &old)) return 4;
  *(int32_t*)(c + 1) = (int32_t)((int64_t)(uintptr_t)t - (int64_t)(uintptr_t)(c + 5));
  VirtualProtect(c, 5, old, &old);
  FlushInstructionCache(GetCurrentProcess(), c, 5);
  return 0;
}
/* Round of 16: bit 0 the schedule line, bit 1 the match title; *why gets 2/3/4 for a failed one */
static int kotext_install(uint64_t exe_base, int* why)
{
  int done = 0;
  *why = 0;
  unsigned char* ss = (unsigned char*)(uintptr_t)(exe_base + SCHED_SITE);
  unsigned char* st = (unsigned char*)(uintptr_t)(exe_base + SCHED_TEXT);
  unsigned char* ts = (unsigned char*)(uintptr_t)(exe_base + TITLE_SITE);
  unsigned char* tr = (unsigned char*)(uintptr_t)(exe_base + TITLE_R16);
  unsigned char* t = near_alloc(exe_base);
  if (!t) { *why = 3; return 0; }
  if (!memcmp(ss, SIG_SCHED, 5) && !memcmp(st, SIG_SCHEDT, 5) && *(uint32_t*)(st - 4) == 0x3a20019u) {
    /* mov ecx, ebx (competition); movzx edx, r14w (knockout); mov r8d, r15d (+0x30c clubs); movzx r9d, r12w (+0x7a) */
    static const unsigned char LD[13] = { 0x89, 0xd9, 0x41, 0x0f, 0xb7, 0xd6, 0x45, 0x89, 0xf8, 0x45, 0x0f, 0xb7, 0xcc };
    int n = ci_stub(t, LD, 13, (void*)ko_sched_text, 1, exe_base + SCHED_TEXT, SIG_SCHED, 3,
                    exe_base + SCHED_C2, exe_base + SCHED_NOT2);
    FlushInstructionCache(GetCurrentProcess(), t, n);
    int e = ci_patch(ss, 5, t);
    if (!e) done |= 1; else *why = e;
  } else *why = 2;
  if (!memcmp(ts, SIG_TITLE, 6) && !memcmp(tr, SIG_TITLER, 7)) {
    /* mov ecx, r14d (competition); movzx edx, si (regulation); mov r8d, r15d (clubs); movzx r9d, r13w (+0x7a) */
    static const unsigned char LD[13] = { 0x44, 0x89, 0xf1, 0x0f, 0xb7, 0xd6, 0x45, 0x89, 0xf8, 0x45, 0x0f, 0xb7, 0xcd };
    unsigned char* s = t + 0x100;
    int n = ci_stub(s, LD, 13, (void*)ko_title_r16, 0, exe_base + TITLE_R16, SIG_TITLE, 4,
                    exe_base + TITLE_C2, exe_base + TITLE_NOT2);
    FlushInstructionCache(GetCurrentProcess(), s, n);
    int e = ci_patch(ts, 6, s);
    if (!e) done |= 2; else *why = e;
  } else if (ts[0] == 0xE9 && ts[5] == 0x90 && !memcmp(tr, SIG_TITLER, 7)) {
    /* FL27: SmokePatch's jmp + nop over the compare. Not ours: no compare of our own (the test
       left ZF set, so the jne falls through) and the "equal" jump goes to their stub, which
       still decides kind 2 itself; r14 survives our call. */
    static const unsigned char LD[13] = { 0x44, 0x89, 0xf1, 0x0f, 0xb7, 0xd6, 0x45, 0x89, 0xf8, 0x45, 0x0f, 0xb7, 0xcd };
    unsigned char* s = t + 0x100;
    uint64_t theirs = (uint64_t)(uintptr_t)(ts + 5) + *(int32_t*)(ts + 1);
    int n = ci_stub(s, LD, 13, (void*)ko_title_r16, 0, exe_base + TITLE_R16, SIG_TITLE, 0,
                    theirs, theirs);
    FlushInstructionCache(GetCurrentProcess(), s, n);
    int e = ci_patch(ts, 5, s);
    if (!e) done |= 2; else *why = e;
  } else *why = 2;
  return done;
}

/* ---- "which league is team X in" without the linear regulation searches ----
 *
 * 0x141543510 answers which league a team plays in. For every competition id of a list
 * (0x1414ccd10, ~73 ids) it searches the regulation table (0x314-byte records) for the id --
 * twice, the second search (0x1415435d7..0x14154360d, through the same block pointer) finding
 * the very record the first already found -- and then walks that league's clubs. It is called
 * for every match the season builder places, so with our 300 regulations the two searches were
 * 46 % of the game's time on the ML creation loading screen (sample 08.10., Druga NL club, a
 * load of several minutes; fl26regfast had already removed the 0x1414bb000 re-searches).
 *  - the first search (0x14154358d) jumps to a stub that looks the id up in a 64K table of
 *    record indices and checks the hit (index below the count, the record carries the id), so
 *    a stale entry is never used; a miss runs the original linear search from 0 -- the same
 *    first match -- and remembers the index. The table is cleared whenever the count changes.
 *    Out: rdx = index * 0x314 at 0x1415435c0, as the original loop leaves it; eax/ecx/rdx/r8
 *    and the flags are the original's scratch registers (nothing reads them after).
 *  - the second search is skipped: `call 0x1414b6a60` at 0x1415435ce becomes `jmp 0x14154361a`,
 *    where rax still holds the record (0x1415435c0 put it there, 0x1415435cb copied it to r15).
 * REGS and COUNT are read from the code when this runs, after fl26caps relocated them. */
#define RIX_SITE   0x154358d
#define RIX_CMP1   0x15435a9
#define RIX_CMP2   0x15435fa
#define RIX_CNT2   0x15435da
#define RIX_FOUND  0x15435c0
#define RIX_NONE   0x154368b
#define RIX_SKIP   0x15435ce
#define RIX_AFTER  0x154361a
static const unsigned char SIG_RIX[5]    = { 0x33,0xc0, 0x45,0x8b,0x85 };        /* xor eax,eax; mov r8d,[r13+COUNT] */
static const unsigned char SIG_RIXT[5]   = { 0x45,0x85,0xc0, 0x0f,0x84 };        /* test r8d,r8d; je */
static const unsigned char SIG_RCMP1[5]  = { 0x66,0x42,0x39,0x9c,0x2a };         /* cmp word [rdx+r13+REGS], bx */
static const unsigned char SIG_RCMP2[5]  = { 0x66,0x42,0x39,0x9c,0x12 };         /* cmp word [rdx+r10+REGS], bx */
static const unsigned char SIG_RCNT2[3]  = { 0x45,0x8b,0x8a };                   /* mov r9d, [r10+COUNT] */
static const unsigned char SIG_RAFTER[6] = { 0x8b,0x88,0x08,0x03,0x00,0x00 };    /* mov ecx, [rax+0x308] */

static int put_jmp_abs(unsigned char* s, int n, uint64_t to)
{
  s[n++] = 0xFF; s[n++] = 0x25; *(uint32_t*)(s + n) = 0; n += 4; *(uint64_t*)(s + n) = to; n += 8;
  return n;
}

/* 0 ok; 2 a site is not the one expected (nothing patched); 3 no page in reach; 4 VirtualProtect; 5 no table */
static int rix_install(uint64_t exe_base)
{
  unsigned char* site = (unsigned char*)(uintptr_t)(exe_base + RIX_SITE);
  unsigned char* c1 = (unsigned char*)(uintptr_t)(exe_base + RIX_CMP1);
  unsigned char* c2 = (unsigned char*)(uintptr_t)(exe_base + RIX_CMP2);
  unsigned char* n2 = (unsigned char*)(uintptr_t)(exe_base + RIX_CNT2);
  unsigned char* skip = (unsigned char*)(uintptr_t)(exe_base + RIX_SKIP);
  unsigned char* after = (unsigned char*)(uintptr_t)(exe_base + RIX_AFTER);
  if (memcmp(site, SIG_RIX, 5) || memcmp(site + 9, SIG_RIXT, 5) || memcmp(c1, SIG_RCMP1, 5) ||
      memcmp(c2, SIG_RCMP2, 5) || memcmp(n2, SIG_RCNT2, 3) || memcmp(after, SIG_RAFTER, 6) || skip[0] != 0xE8)
    return 2;
  uint32_t count = *(uint32_t*)(site + 5), regs = *(uint32_t*)(c1 + 5);
  if (regs != *(uint32_t*)(c2 + 5) || count != *(uint32_t*)(n2 + 3)) return 2;   /* the two searches disagree */
  uint16_t* tab = (uint16_t*)VirtualAlloc(0, 0x20000, MEM_COMMIT|MEM_RESERVE, PAGE_READWRITE);
  if (!tab) return 5;
  memset(tab, 0xff, 0x20000);
  unsigned char* t = near_alloc(exe_base);
  if (!t) return 3;
  uint32_t* last = (uint32_t*)(t + 0x800);                 /* the count the table was built for */
  *last = 0xffffffffu;
  unsigned char* s = t;
  int n = 0, j_cached, j_slow1, j_slow2, j_none, j_loop, j_hit, j_next;
  s[n++] = 0x0f; s[n++] = 0xb7; s[n++] = 0xc3;                                   /* movzx eax, bx */
  s[n++] = 0x48; s[n++] = 0xb9; *(uint64_t*)(s + n) = (uint64_t)(uintptr_t)tab; n += 8; /* mov rcx, tab */
  s[n++] = 0x45; s[n++] = 0x8b; s[n++] = 0x85; *(uint32_t*)(s + n) = count; n += 4; /* mov r8d, [r13+COUNT] */
  s[n++] = 0x44; s[n++] = 0x3b; s[n++] = 0x05;                                   /* cmp r8d, [rip -> last] */
  *(int32_t*)(s + n) = (int32_t)((unsigned char*)last - (s + n + 4)); n += 4;
  s[n++] = 0x74; j_cached = n++;                                                 /* je cached */
  s[n++] = 0x44; s[n++] = 0x89; s[n++] = 0x05;                                   /* mov [rip -> last], r8d */
  *(int32_t*)(s + n) = (int32_t)((unsigned char*)last - (s + n + 4)); n += 4;
  s[n++] = 0x57; s[n++] = 0x51;                                                  /* push rdi; push rcx */
  s[n++] = 0x48; s[n++] = 0x89; s[n++] = 0xcf;                                   /* mov rdi, rcx */
  s[n++] = 0xb9; *(uint32_t*)(s + n) = 0x4000; n += 4;                           /* mov ecx, 0x4000 */
  s[n++] = 0x48; s[n++] = 0xc7; s[n++] = 0xc0; *(uint32_t*)(s + n) = 0xffffffffu; n += 4; /* mov rax, -1 */
  s[n++] = 0xf3; s[n++] = 0x48; s[n++] = 0xab;                                   /* rep stosq */
  s[n++] = 0x59; s[n++] = 0x5f;                                                  /* pop rcx; pop rdi */
  s[n++] = 0x0f; s[n++] = 0xb7; s[n++] = 0xc3;                                   /* movzx eax, bx */
  s[j_cached] = (unsigned char)(n - (j_cached + 1));
  s[n++] = 0x0f; s[n++] = 0xb7; s[n++] = 0x14; s[n++] = 0x41;                     /* cached: movzx edx, word [rcx+rax*2] */
  s[n++] = 0x44; s[n++] = 0x39; s[n++] = 0xc2;                                   /* cmp edx, r8d */
  s[n++] = 0x73; j_slow1 = n++;                                                  /* jae slow */
  s[n++] = 0x48; s[n++] = 0x69; s[n++] = 0xd2; *(uint32_t*)(s + n) = 0x314; n += 4; /* imul rdx, rdx, 0x314 */
  s[n++] = 0x66; s[n++] = 0x42; s[n++] = 0x39; s[n++] = 0x9c; s[n++] = 0x2a;     /* cmp word [rdx+r13+REGS], bx */
  *(uint32_t*)(s + n) = regs; n += 4;
  s[n++] = 0x75; j_slow2 = n++;                                                  /* jne slow */
  n = put_jmp_abs(s, n, exe_base + RIX_FOUND);                                   /* jmp found */
  s[j_slow1] = (unsigned char)(n - (j_slow1 + 1));
  s[j_slow2] = (unsigned char)(n - (j_slow2 + 1));
  s[n++] = 0x31; s[n++] = 0xc0;                                                  /* slow: xor eax, eax */
  s[n++] = 0x45; s[n++] = 0x85; s[n++] = 0xc0;                                   /* test r8d, r8d */
  s[n++] = 0x74; j_none = n++;                                                   /* je none */
  j_loop = n;
  s[n++] = 0x89; s[n++] = 0xc2;                                                  /* loop: mov edx, eax */
  s[n++] = 0x48; s[n++] = 0x69; s[n++] = 0xd2; *(uint32_t*)(s + n) = 0x314; n += 4; /* imul rdx, rdx, 0x314 */
  s[n++] = 0x66; s[n++] = 0x42; s[n++] = 0x39; s[n++] = 0x9c; s[n++] = 0x2a;     /* cmp word [rdx+r13+REGS], bx */
  *(uint32_t*)(s + n) = regs; n += 4;
  s[n++] = 0x74; j_hit = n++;                                                    /* je hit */
  s[n++] = 0xff; s[n++] = 0xc0;                                                  /* inc eax */
  s[n++] = 0x44; s[n++] = 0x39; s[n++] = 0xc0;                                   /* cmp eax, r8d */
  s[n++] = 0x72; j_next = n++;                                                   /* jb loop */
  s[j_next] = (unsigned char)(j_loop - (j_next + 1));
  s[j_none] = (unsigned char)(n - (j_none + 1));
  n = put_jmp_abs(s, n, exe_base + RIX_NONE);                                    /* none: the original "not found" */
  s[j_hit] = (unsigned char)(n - (j_hit + 1));
  s[n++] = 0x44; s[n++] = 0x0f; s[n++] = 0xb7; s[n++] = 0xc3;                     /* hit: movzx r8d, bx */
  s[n++] = 0x66; s[n++] = 0x42; s[n++] = 0x89; s[n++] = 0x04; s[n++] = 0x41;     /* mov word [rcx+r8*2], ax */
  n = put_jmp_abs(s, n, exe_base + RIX_FOUND);                                   /* jmp found */
  FlushInstructionCache(GetCurrentProcess(), t, n);
  DWORD old;
  if (!VirtualProtect(site, 5, PAGE_EXECUTE_READWRITE, &old)) return 4;
  site[0] = 0xE9; *(int32_t*)(site + 1) = (int32_t)((int64_t)(uintptr_t)t - (int64_t)(uintptr_t)(site + 5));
  VirtualProtect(site, 5, old, &old);
  FlushInstructionCache(GetCurrentProcess(), site, 5);
  if (!VirtualProtect(skip, 2, PAGE_EXECUTE_READWRITE, &old)) return 4;
  skip[0] = 0xEB; skip[1] = (unsigned char)(RIX_AFTER - (RIX_SKIP + 2));         /* jmp 0x14154361a */
  VirtualProtect(skip, 2, old, &old);
  FlushInstructionCache(GetCurrentProcess(), skip, 2);
  logf("fl26swiss: team-to-league lookup indexed (REGS +0x%x, COUNT +0x%x, stub %d bytes)", regs, count, n);
  return 0;
}

/* A record's region, the key 0x1415415f0 answers. With fl26reg128 live that getter reads the
 * full region (0..127; 0..255 with fl26caps' regions step) from the byte at +0x2fe, which the module marks with 0x5a at +0x2ff,
 * and the 6-bit field at +0x30c bits 7..12 holds min(region, 63); without it the 6-bit field
 * is the region. An unmarked record (an old career fl26join has not repaired yet) falls back
 * to the field. */
static unsigned rec_region(const unsigned char* rr)
{
  static const unsigned char NEW[7] = { 0x0f,0xb6,0x80,0xfe,0x02,0x00,0x00 };   /* fl26reg128 at 0x141541639 */
  unsigned six = (*(const uint32_t*)(rr + 0x30c) >> 7) & 0x3f;
  if (g_base && !memcmp((const void*)(uintptr_t)(g_base + 0x1541639), NEW, sizeof NEW)
      && rr[0x2ff] == 0x5a)
    return rr[0x2fe];
  return six;
}

/* Put the key of every live split into the stub, once. Cheap enough to call from the date,
 * progression and current-phase hooks, which between them run on load and on the split day. */
static void split_keys(void)
{
  static uint32_t said_nc = 0;
  if (!g_carry_stub || g_carry_keys >= CARRY_SLOTS) return;
  for (int k = 0; k < g_nsplits; k++) {
    unsigned char* rr = get_rec(SPLITS[k].regular);
    if (!rr || ((*(uint32_t*)(rr + 0x308) >> 23) & 0x3f) != 12) continue;
    unsigned key = rec_region(rr);   /* key - 12: the stub's byte compare, every key 12..255 */
    if (nocarry(SPLITS[k].total)) {
      if (k < 32 && !(said_nc & (1u << k))) {
        said_nc |= 1u << k;
        logf("fl26swiss: reg %u -- Apertura/Clausura under key %u: the Clausura starts from zero%s",
             (unsigned)SPLITS[k].regular, key, key == 12 || key == 15 ? " -- NOT: the game carries key 12/15 itself" : "");
      }
      continue;
    }
    if (key == 12 || key == 15) continue;
    unsigned char imm = (unsigned char)(key - 12);
    int have = 0;
    for (unsigned i = 0; i < g_carry_keys; i++) if (g_carry_stub[CARRY_IMM(i)] == imm) have = 1;
    if (have || g_carry_keys >= CARRY_SLOTS) continue;
    g_carry_stub[CARRY_IMM(g_carry_keys++)] = imm;
    logf("fl26swiss: reg %u -- split under key %u: the groups start from its points (0x14134a540)",
         (unsigned)SPLITS[k].regular, key);
  }
}

/* The first dates of the Scottish line (14, 21 and 28 August) are behind a league of ours
 * that enters its season through register_all, a little after that (fl26join): the game put
 * those rounds a year later, after the season's end (191, Apertura, 2026-09-29: three rounds
 * dated August 2026). A career made in August is past the first of them too. So our splits
 * start on the fourth date, 15 September, whenever the season still fits in what is left --
 * the same for every phase of a split and every season, so the league builder can know the
 * days in advance (leaguebuilder SPLIT_SKIP, split_days). */
#define SPLIT_SKIP 3

static uint32_t rec_rounds(uint16_t id)
{
  unsigned char* rec = get_rec(id);
  if (!rec) return 0;
  uint32_t clubs = *(uint32_t*)(rec + 0x30c) & 0x7f, legs = *(uint32_t*)(rec + 0x308) >> 29;
  return (clubs & 1 ? clubs : clubs - 1) * legs;
}

static uint64_t split_dates(uint16_t id, uint64_t reg, void* vec, int part, const split_t* s)
{
  vec_t* v = (vec_t*)vec;
  static uint16_t said[16]; static int nsaid = 0; int seen = 0;
  SAID_RESET(nsaid);
  for (int k = 0; k < nsaid; k++) if (said[k] == id) seen = 1;
  if (!seen && nsaid < 16) said[nsaid++] = id;

  if (part == 1) {
    uint64_t rv = ((date_fn)(uintptr_t)g_tramp_date)(reg, vec);
    if (v->b) v->e = v->b;
    if (!seen) logf("fl26swiss: reg %u -- split total, no dates of its own", (unsigned)id);
    return rv;
  }
  uint32_t n1 = rec_rounds(s->regular), n2 = 0;
  for (int g = 0; g < 3; g++) if (s->group[g]) { uint32_t r = rec_rounds(s->group[g]); if (r > n2) n2 = r; }
  uint32_t T = n1 + n2, n = part == 2 ? n1 : rec_rounds(id);
  uint64_t rv = ((date_fn)(uintptr_t)g_tramp_date)((reg & ~(uint64_t)0xffff) | (T <= 38 ? MID_CAL_REG : LONG_CAL_REG), vec);
  size_t have = (v->b && v->e >= v->b) ? (size_t)(v->e - v->b) / sizeof(date_t) : 0;
  date_t* r = (date_t*)v->b;
  if (!n1 || !n2 || !n || T < 2 || T > 64 || have < T) {
    if (v->b) v->e = v->b;
    if (!seen) logf("fl26swiss: reg %u -- split phase NOT dated (regular %u, groups %u, this %u, calendar %u)",
                    (unsigned)id, n1, n2, n, (unsigned)have);
    return rv;
  }
  uint16_t line[64]; size_t L;
  if (T <= 38 - SPLIT_SKIP) { L = 38 - SPLIT_SKIP; for (size_t i = 0; i < L; i++) line[i] = SCOT_DAYS[SPLIT_SKIP + i]; }
  else if (T <= 46) { L = 46; for (size_t i = 0; i < L; i++) line[i] = SPLIT_LONG[i]; }
  else { L = have; for (size_t i = 0; i < L; i++) line[i] = (uint16_t)r[i].day; }
  uint32_t first = part == 2 ? 0 : n1;
  for (uint32_t i = 0; i < n; i++) {
    uint32_t t = first + i;                                   /* position on the whole season */
    size_t j = (size_t)((t * (L - 1) * 2 + (T - 1)) / (2 * (T - 1)));
    r[i].day = line[j];
    r[i].round = i;
    r[i].kind = FL26_DATE_KIND_LEAGUE;
  }
  v->e = v->b + (size_t)n * sizeof(date_t);
  league_rest(id, r, n);
  if (!seen)
    logf("fl26swiss: reg %u -- split %s of %u: %u rounds on days %u..%u (season %u+%u on a %u-date line)",
         (unsigned)id, part == 2 ? "regular phase" : "group", (unsigned)s->total, n,
         r[0].day, r[n - 1].day, n1, n2, (unsigned)L);
  if (!seen && part == 2 && id > 175) check_reg(id, "dated");
  return rv;
}

/* ---- a new country's national cup and super cup ----
 * The game dates a cup's rounds by its regulation id, in the same switch over the shipped ids
 * 2..175 as the leagues, so a cup of ours (mkcup.py, id 176 and up) got its draw and not one
 * date, and was never played (CUPT world, 2026-09-28: regulations 197 and 198, 20 records, all
 * undated). It is a copy of a shipped cup with the same bracket, so it takes that cup's dates:
 * the world file's `dates <ours> like=<shipped>` lines (fl26_swiss_datelike). */
#define MAX_DATELIKE 512    /* 32 until the limits branch: 46 with 80 leagues (14 cups went undated) */
static uint16_t g_dlike[MAX_DATELIKE][2]; static int g_ndlike = 0;

/* Optional day shift for `dates <ours> like=<shipped> shift=<days>`.
   Kept separate from datelike so old world files keep their old behaviour. */
static uint16_t g_dshift[MAX_DATELIKE][2]; static int g_ndshift = 0;

typedef struct {
  uint16_t id, n;
  uint16_t day[MAX_DATE_DAYS];
} datedays_t;

static datedays_t g_ddays[MAX_DATELIKE];
static int g_nddays = 0;

#define CALENDAR_CUP_TEARDOWN_LIKE   55  /* Japan Cup: calendar-year cup rollover */
#define CALENDAR_SUPER_TEARDOWN_LIKE 97  /* Japan Super Cup: calendar-year super cup rollover */

static uint16_t date_shift_for(uint16_t id)
{
  for (int i = 0; i < g_ndshift; i++)
    if (g_dshift[i][0] == id) return g_dshift[i][1];
  return 0;
}

static const datedays_t* date_days_for(uint16_t id)
{
  for (int i = 0; i < g_nddays; i++)
    if (g_ddays[i].id == id) return &g_ddays[i];
  return 0;
}
/* the days a calendar-year league's own cup plays (busy_set): the cup a cupdraw line names it a
   division of, dated like the national cups -- on its explicit days, the national cups' days
   shifted, or those as natcup_fix moves them. One world-wide set until 0.2.4 (the last `dates`
   line's), for every calendar-year league, whatever its country. A league no cupdraw line names
   (a world with `cupdraw off`) keeps that set. */
static int cal_cup_days(uint16_t id, uint32_t* out, int cap)
{
  int n = 0;
  for (int k = 0; k < g_ncd; k++) {
    int mine = 0;
    for (int t = 0; t < g_cd[k].ntier; t++) if (g_cd[k].tier[t] == id) mine = 1;
    if (!mine) continue;
    for (int i = 0; i < g_ndlike; i++) {
      if (g_dlike[i][0] != g_cd[k].reg || g_dlike[i][1] != CALENDAR_NATCUP_LIKE) continue;
      const datedays_t* dd = date_days_for(g_cd[k].reg);
      uint16_t sh = date_shift_for(g_cd[k].reg);
      if (dd) for (int j = 0; j < dd->n && n < cap; j++) out[n++] = dd->day[j];
      else for (int j = 0; j < 12 && n < cap; j++) out[n++] = sh ? (NATCUP_DAYS[j] + sh) % 365u : natcup_day(j);
      return n;
    }
  }
  if (g_calendar_natcup_ndays)
    for (int j = 0; j < g_calendar_natcup_ndays && n < cap; j++) out[n++] = g_calendar_natcup_days[j];
  else if (g_calendar_natcup_shift)
    for (int j = 0; j < 12 && n < cap; j++) out[n++] = (NATCUP_DAYS[j] + g_calendar_natcup_shift) % 365u;
  return n;
}

static int calendar_natcup_round_slot(uint32_t round)
{
  static const uint16_t rounds[7] = {
    0x2e, 0x2f, 0x30, 0x33, 0x34, 0x35, 0x36
  };

  for (int i = 0; i < 7; i++)
    if (round == rounds[i]) return i;

  return -1;
}

static int calendar_natcup_slot(uint32_t round, uint32_t kind)
{
  int r = calendar_natcup_round_slot(round);
  if (r < 0 || kind > 1) return -1;
  return 2 * r + (int)kind;
}

__declspec(dllexport) int fl26_swiss_datedays(const uint16_t* v, int n)
{
  if ((!v && n) || n < 0) return -1;

  if (n == 0) {
    g_nddays = 0;
    g_calendar_natcup_ndays = 0;
    return 0;
  }

  if (n < 2 || n > MAX_DATE_DAYS + 1) return -1;

  uint16_t id = v[0];
  if (id < 2) return 0;

  int k = -1;
  for (int i = 0; i < g_nddays; i++)
    if (g_ddays[i].id == id) {
      k = i;
      break;
    }

  if (k < 0) {
    if (g_nddays >= MAX_DATELIKE) return 0;
    k = g_nddays++;
  }

  g_ddays[k].id = id;
  g_ddays[k].n = (uint16_t)(n - 1);

  for (int i = 1; i < n; i++)
    g_ddays[k].day[i - 1] = (uint16_t)(v[i] % 365u);

  for (int i = 0; i < g_ndlike; i++)
    if (g_dlike[i][0] == id &&
        g_dlike[i][1] == CALENDAR_NATCUP_LIKE) {
      g_calendar_natcup_ndays = n - 1;
      memcpy(g_calendar_natcup_days, g_ddays[k].day,
             (size_t)g_calendar_natcup_ndays * sizeof(uint16_t));
    }

  logf("fl26swiss: explicit date days set for reg %u (%d records)",
       (unsigned)id, n - 1);
  return 1;
}

__declspec(dllexport) int fl26_swiss_dateshift(const uint16_t* v, int n)
{
  if ((!v && n) || n < 0) return -1;
  if (n > MAX_DATELIKE) n = MAX_DATELIKE;

  g_calendar_natcup_shift = 0;
  int k = 0;
  for (int i = 0; i < n; i++) {
    uint16_t id = v[2 * i];
    uint16_t shift = (uint16_t)(v[2 * i + 1] % 365u);

    if (id >= 2 && shift) {
      g_dshift[k][0] = id;
      g_dshift[k][1] = shift;

      for (int j = 0; j < g_ndlike; j++)
        if (g_dlike[j][0] == id && g_dlike[j][1] == CALENDAR_NATCUP_LIKE)
          g_calendar_natcup_shift = shift;

      k++;
    }
  }

  g_ndshift = k;
  logf("fl26swiss: date shift set for %d cup(s)", k);
  return k;
}

__declspec(dllexport) int fl26_swiss_datelike(const uint16_t* v, int n)
{
  if ((!v && n) || n < 0) return -1;
  if (n > MAX_DATELIKE) {
    logf("fl26swiss: %d dates line(s), only %d taken -- the cups of the last %d are not dated and will not be played",
         n, MAX_DATELIKE, n - MAX_DATELIKE);
    n = MAX_DATELIKE;
  }
  int k = 0;
  for (int i = 0; i < n; i++)
    /* ours (176 and up), or a shipped cup a `season` line moved to August-May (164 like 122) */
    if (v[2 * i] >= 2 && v[2 * i] != v[2 * i + 1] && v[2 * i + 1] >= 2 && v[2 * i + 1] <= 175) { g_dlike[k][0] = v[2 * i]; g_dlike[k][1] = v[2 * i + 1]; k++; }
  g_ndlike = k;
  logf("fl26swiss: %d cup(s) dated as the shipped cup they were copied from", k);
  return k;
}

/* B238: a cup of the game a `season` line moved to August-May is dated like an August-May cup
   (164 like 122), but the dates the game gives 122 name 122's rounds: 0x2e, 0x33 and 0x34 over
   two legs, then 0x35 and 0x36. The King's Cup plays 0x2e, 0x2f, 0x34, 0x35 and 0x36 over one
   match each, so only the days of rounds both share were found and its first rounds were never
   played (measured 2026-10-25: a King's Cup drawn, 18 places in 5 rounds, only the final on the
   calendar). It keeps its own rounds now and takes the other cup's days, in order: its first on
   the other's first day, its final on the other's last, the rounds between spread over the rest. */
#define OWN_MAX 32
static void moved_cup_days(const date_t* own, int nown, void* vec)
{
  vec_t* v = (vec_t*)vec;
  size_t have = (v && v->b && v->e >= v->b) ? (size_t)(v->e - v->b) / sizeof(date_t) : 0;
  size_t cap = (v && v->b && v->c >= v->b) ? (size_t)(v->c - v->b) / sizeof(date_t) : 0;
  if (!have || nown < 1 || (size_t)nown > cap) return;
  date_t* r = (date_t*)v->b;
  uint32_t d[OWN_MAX]; int nd = 0;                 /* the other cup's days, in season order */
  for (size_t j = 0; j < have; j++) {
    int dup = 0;
    for (int k = 0; k < nd; k++) if (d[k] == r[j].day) dup = 1;
    if (!dup && nd < OWN_MAX) d[nd++] = r[j].day;
  }
#define SEASON_KEY(x) (((x) + 365u - SECOND_HALF) % 365u)
  for (int a = 1; a < nd; a++)
    for (int b = a; b > 0 && SEASON_KEY(d[b]) < SEASON_KEY(d[b - 1]); b--) { uint32_t t = d[b]; d[b] = d[b - 1]; d[b - 1] = t; }
#undef SEASON_KEY
  if (nown > nd) return;                           /* more of its own dates than days: as it was */
  for (int j = 0; j < nown; j++) {
    int k = nown == 1 ? nd - 1 : (j * (nd - 1) * 2 + (nown - 1)) / (2 * (nown - 1));
    r[j] = own[j];
    r[j].day = d[k];
  }
  v->e = v->b + (size_t)nown * sizeof(date_t);
}

/* B283: the super cup of an August-May league of ours on a day before the league's first round,
 * as in reality (the Romanian one a week before it): a week before when there is room, else the
 * first day after today. A super cup the game dates before the first round already is left as
 * it is, and one whose league is not dated yet (a save loaded after the rollover) too. */
static void aug_scup_before_league(uint16_t id, void* vec)
{
  const cal_scup_t* cs = 0;
  for (int i = 0; i < g_naug_scup; i++) if (g_aug_scup[i].reg == id) cs = &g_aug_scup[i];
  vec_t* v = (vec_t*)vec;
  size_t n = (v && v->b && v->e >= v->b) ? (size_t)(v->e - v->b) / sizeof(date_t) : 0;
  int f = -1, t = today();
  for (int k = 0; cs && k < g_nlfirst; k++) if (g_lfirst[k].id == cs->league) f = g_lfirst[k].day;
  if (!cs || !n || n > 2 || f < 0 || t < 0) return;
  date_t* r = (date_t*)v->b;
  uint32_t fp = season_pos((uint32_t)f), tp = season_pos((uint32_t)t), late = 0;
  /* dated at the July rollover (day 181) or before it: the season it is dated for starts on
     day 182, so every day from then on is free -- season_pos(181) is the old season's last */
  if (t >= 140 && t < 182) tp = 0;
  for (size_t j = 0; j < n; j++) if (r[j].day >= 365 || season_pos(r[j].day) >= fp) late = 1;
  if (!late) return;
  uint32_t gap = n == 2 ? 4 : 0;                     /* two legs: four days apart */
  if (fp < tp + 2 + gap) {
    logf("fl26swiss: reg %u -- super cup after league %u's first round (day %d), no day left before it",
         (unsigned)id, (unsigned)cs->league, f);
    return;
  }
  uint32_t want = fp >= tp + 8 + gap ? fp - 7 : tp + 1 + gap;
  uint32_t was = r[0].day;
  for (size_t j = 0; j < n; j++) {
    uint32_t p = want - gap * (uint32_t)(n - 1 - j);
    r[j].day = p < 183 ? p + 182 : p - 183;
  }
  logf("fl26swiss: reg %u -- super cup on day %u, before league %u's first round on day %d (was day %u)",
       (unsigned)id, r[n - 1].day, (unsigned)cs->league, f, was);
}

static uint64_t datelike_dates(uint16_t id, uint64_t reg, void* vec)
{
  static uint16_t said[MAX_DATELIKE]; static int nsaid = 0;
  for (int i = 0; i < g_ndlike; i++) {
    if (g_dlike[i][0] != id) continue;
    /* a cup of the game keeps its own rounds (B238): what the game dates it with, first */
    static date_t own[OWN_MAX]; int nown = 0;
    if (id <= 175 && !date_days_for(id) && !date_shift_for(id)) {
      ((date_fn)(uintptr_t)g_tramp_date)(reg, vec);
      vec_t* ov = (vec_t*)vec;
      size_t on = (ov && ov->b && ov->e >= ov->b) ? (size_t)(ov->e - ov->b) / sizeof(date_t) : 0;
      if (on <= OWN_MAX) { memcpy(own, ov->b, on * sizeof(date_t)); nown = (int)on; }
      if (ov && ov->b) ov->e = ov->b;              /* the game's date list appends: empty it again */
      for (int a = 1; a < nown; a++)               /* by round, then leg */
        for (int b = a; b > 0 && (own[b].round < own[b - 1].round ||
             (own[b].round == own[b - 1].round && own[b].kind < own[b - 1].kind)); b--) {
          date_t t = own[b]; own[b] = own[b - 1]; own[b - 1] = t; }
    }
    uint64_t rv = ((date_fn)(uintptr_t)g_tramp_date)((reg & ~(uint64_t)0xffff) | g_dlike[i][1], vec);
    const datedays_t* dd = date_days_for(id);

    if (dd) {
      vec_t* sv = (vec_t*)vec;
      size_t sn = (sv && sv->b && sv->e >= sv->b)
                ? (size_t)(sv->e - sv->b) / sizeof(date_t) : 0;
      date_t* sr = sv ? (date_t*)sv->b : 0;
      int ok = sr != 0;

      if (ok && g_dlike[i][1] == CALENDAR_NATCUP_LIKE && dd->n == 7) {
        for (size_t j = 0; j < sn; j++)
          if (calendar_natcup_round_slot(sr[j].round) < 0)
            ok = 0;

        if (ok)
          for (size_t j = 0; j < sn; j++)
            sr[j].day = dd->day[calendar_natcup_round_slot(sr[j].round)];
      } else if (ok && g_dlike[i][1] == CALENDAR_NATCUP_LIKE && dd->n == 14) {
        for (size_t j = 0; j < sn; j++)
          if (calendar_natcup_slot(sr[j].round, sr[j].kind) < 0)
            ok = 0;

        if (ok)
          for (size_t j = 0; j < sn; j++)
            sr[j].day = dd->day[calendar_natcup_slot(sr[j].round, sr[j].kind)];
      } else if (ok && g_dlike[i][1] == CALENDAR_SUPER_TEARDOWN_LIKE && dd->n == 1) {
        for (size_t j = 0; j < sn; j++)
          sr[j].day = dd->day[0];
      } else if (ok && g_dlike[i][1] == CALENDAR_SUPER_TEARDOWN_LIKE && dd->n == 2) {
        for (size_t j = 0; j < sn; j++)
          if (sr[j].kind > 1)
            ok = 0;

        if (ok)
          for (size_t j = 0; j < sn; j++)
            sr[j].day = dd->day[sr[j].kind];
      } else if (ok && sn == dd->n) {
        for (size_t j = 0; j < sn; j++)
          sr[j].day = dd->day[j];
      } else {
        ok = 0;
      }

      if (!ok)
        logf("fl26swiss: reg %u -- explicit dates rejected: game gave %u records, world has %u",
             (unsigned)id, (unsigned)sn, (unsigned)dd->n);
    } else {
      uint16_t shift = date_shift_for(id);

      if (shift) {
        vec_t* sv = (vec_t*)vec;
        size_t sn = (sv && sv->b && sv->e >= sv->b)
                  ? (size_t)(sv->e - sv->b) / sizeof(date_t) : 0;
        date_t* sr = sv ? (date_t*)sv->b : 0;

        for (size_t j = 0; sr && j < sn; j++)
          sr[j].day = (sr[j].day + shift) % 365u;
      } else {
        natcup_fix(id, vec);
      }
    }
    if (nown) moved_cup_days(own, nown, vec);
    aug_scup_before_league(id, vec);               /* B283 */
    nt_cup_clear(id, vec);                         /* B254 */
    vec_t* v = (vec_t*)vec;
    size_t have = (v->b && v->e >= v->b) ? (size_t)(v->e - v->b) / sizeof(date_t) : 0;
    int seen = 0;
    for (int k = 0; k < nsaid; k++) if (said[k] == id) seen = 1;
    if (!seen && nsaid < MAX_DATELIKE) {
      said[nsaid++] = id;
      date_t* r = (date_t*)v->b;
      if (have) logf("fl26swiss: reg %u -- dated as %u: %u dates, days %u..%u", (unsigned)id, (unsigned)g_dlike[i][1],
                     (unsigned)have, r[0].day, r[have - 1].day);
      else logf("fl26swiss: reg %u -- dated as %u: the game gave no dates", (unsigned)id, (unsigned)g_dlike[i][1]);
      if (nown && have) {
        char ob[400]; int op = 0; ob[0] = 0;
        for (size_t j = 0; j < have && op < (int)sizeof ob - 24; j++)
          op += snprintf(ob + op, sizeof ob - (size_t)op, "%x/%u:%u ", r[j].round, r[j].kind, r[j].day);
        logf("fl26swiss: reg %u -- its own %d round date(s) on those days (round/leg:day): %s", (unsigned)id, nown, ob);
      }
    }
    return rv;
  }
  return (uint64_t)-1;
}

/* ---- the AFC Champions League midweek (GitHub #70) ----
 * The game's own AFC Champions League (groups reg 15 and its rows 15 + 1024 * (g + 1), knockout
 * reg 16) played Mondays to Wednesdays. Each of its dates goes to the nearest of Tuesday,
 * Wednesday and Thursday on the big leagues' grid (Saturday 261): Sunday and Monday later,
 * Friday and Saturday earlier, so the order of the rounds stays. */
#define AFC_GROUPS 15
#define AFC_KO     16
static int afc_reg(uint16_t id)
{
  return id == AFC_KO || id == AFC_GROUPS || (id > 1024 && (id & 0x3ff) == AFC_GROUPS && id <= AFC_GROUPS + 1024 * 8);
}
static uint32_t midweek(uint32_t d)
{
  static const int to[7] = { 0, -1, -2, 2, 1, 0, 0 };   /* d % 7: Thu Fri Sat Sun Mon Tue Wed */
  if (d >= 365) return d;
  return (uint32_t)(((int)d + 365 + to[d % 7]) % 365);
}

static int game_date(void);
/* A career built in this session, before its first day has gone by. A career in a January league
   (China, Japan, ...) is built on day 0: measured 2026-10-05. B209: an August-May career is built
   at the July rollover, on day 181 (24.10., a new ML in _FL26EuropePackv001 and Jabo9's log), and
   the rollover's set_clubs builds the summer's access list before any date is asked for: taken
   from 210 and from date_handler only, no such career was ever new and the first-season list was
   always left out. A save of a later summer loaded on these days looks the same; its tables read
   back from the save folder say it is not (state_sync). */
static void career_mark(const char* where)
{
  abs_day();                                       /* a day gone back: another career (abs_day) */
  if (g_new_career || g_day_ticked) return;
  int t = today();
  if ((t >= SECOND_HALF && t <= 240) || t == 0) {
    g_new_career = 1; g_built_gdate = game_date(); g_built_stored = 0;
    logf("fl26swiss: a new career, built on day %d (%s)", t, where);
  }
}
uint64_t date_handler(uint64_t reg, void* vec)
{
  uint16_t id = (uint16_t)reg;
  if (vec) career_mark("its dates");
  if (vec) nt_sample(reg, vec);                    /* B254: before anything of this day is dated */
  if (vec && g_ndlike) {
    for (int i = 0; i < g_ndlike; i++) if (g_dlike[i][0] == id) return datelike_dates(id, reg, vec);
  }
  {
    const split_t* s; int part;
    if (vec && (part = split_part(id, &s)) != 0) { uint64_t rv = split_dates(id, reg, vec, part, s); split_keys(); return rv; }
  }
  if (vec && g_ic_reg && id == g_ic_reg && ic_world()) return ic_dates(id, reg, vec);
  if (vec && (cwc_id(id) || id == CWC_KO) && cwc_world()) return cwc_dates(id, reg, vec);
  if (vec) {
    int ko, k = ccup_of(id, &ko);
    if (k >= 0 && ccup_world(&g_ccup[k])) return ccup_dates(k, ko, id, reg, vec);
  }
  if (vec) {
    /* a league cup's pre-round: reg 2's records (the same tie of it), on the pre-round's days */
    int tk, li = lpre_of(id, &tk);
    if (li >= 0) {
      const lpre_t* l = &g_lpre[li];
      /* A 16-tie single-match stage has more replicas than shipped reg 2. Borrow
         native Libertadores qualifying's first tie (1032) for every tie's one-match
         date shape; the generated regulation already has legs mode 0. */
      uint16_t src = l->single ? (uint16_t)(tk >= 0 ? 1024 + CONM_LIBQ_REG : CONM_LIBQ_REG)
                               : (uint16_t)((id & ~0x3ff) | 2);
      uint64_t rv = ((date_fn)(uintptr_t)g_tramp_date)((reg & ~(uint64_t)0xffff) | src, vec);
      vec_t* v = (vec_t*)vec;
      size_t have = (v->b && v->e >= v->b) ? (size_t)(v->e - v->b) / sizeof(date_t) : 0;
      date_t* r = (date_t*)v->b;
      static unsigned char said[MAX_LPRE];
      if (l->single && have >= 1) {
        r[0].day = l->days[0];
        r[0].kind = 2;
        v->e = v->b + sizeof(date_t);
        if (!said[li]++)
          logf("fl26swiss: reg %u -- one-match pre-round dated day %u (%u record(s) -> 1)",
               (unsigned)id, l->days[0], (unsigned)have);
        return rv;
      }
      for (size_t i = 0; i < have; i++) r[i].day = l->days[i < 2 ? i : 1];
      if (!said[li]++)
        logf("fl26swiss: reg %u -- league cup pre-round dated days %u and %u (%u record(s))", (unsigned)id,
             l->days[0], l->days[1], (unsigned)have);
      return rv;
    }
  }
  if (vec && afc_reg(id)) {
    uint64_t rv = ((date_fn)(uintptr_t)g_tramp_date)(reg, vec);
    vec_t* v = (vec_t*)vec;
    size_t have = (v->b && v->e >= v->b) ? (size_t)(v->e - v->b) / sizeof(date_t) : 0;
    date_t* r = (date_t*)v->b;
    int moved = 0;
    for (size_t i = 0; i < have; i++) {
      uint32_t d = midweek(r[i].day);
      if (d != r[i].day) { r[i].day = d; moved++; }
    }
    cont_note(id, vec);                            /* its days, for the leagues that feed it */
    static unsigned char said[2];
    if (have && !said[id == AFC_KO]++)
      logf("fl26swiss: reg %u -- AFC Champions League %s: %d of %u date(s) moved to midweek, days %u..%u",
           (unsigned)id, id == AFC_KO ? "knockout" : "groups", moved, (unsigned)have, r[0].day, r[have - 1].day);
    return rv;
  }
  if (european(id)) seen_once(1, id, 0);
  /* FL27: their league phase (3 / 5, its rows 1027 / 1029) and their knockout of 24 (4 / 6, the
     play-off in it) keep the dates they ship with. In game 31.10. our spacing of reg 3 / 5 (11 of
     16 rounds moved) and our knockout dates on reg 4 left the Europa League at 6-7 matches of 8 in
     March with no knockout; FL27 without our modules had played all 8 and reached the
     quarter-finals by then */
  if (vec && g_native_uefa && ((id >= 3 && id <= 6) || id == 1027 || id == 1029)) {
    uint64_t rv = ((date_fn)(uintptr_t)g_tramp_date)(reg, vec);
    vec_t* v = (vec_t*)vec;
    size_t have = (v->b && v->e >= v->b) ? (size_t)(v->e - v->b) / sizeof(date_t) : 0;
    static int said[8], sk = -1000;
    { int k_ = log_season(); if (k_ != sk) { sk = k_; memset(said, 0, sizeof said); } }
    if (!said[id >= 1024 ? 6 + (id == 1029) : id - 3]++) {
      char b[200]; int o = 0;
      for (size_t i = 0; i < have && i < 20 && o < 190; i++)
        o += snprintf(b + o, sizeof b - o, " %u", ((date_t*)v->b)[i].day);
      logf("fl26swiss: reg %u -- FL27's own, its %u date(s) kept:%s", (unsigned)id, (unsigned)have, b);
    }
    return rv;
  }
  if (vec && is_playoff(id)) {
    uint64_t prv = ((date_fn)(uintptr_t)g_tramp_date)(reg, vec);
    vec_t* v = (vec_t*)vec;
    size_t have = (v->b && v->e >= v->b) ? (size_t)(v->e - v->b) / sizeof(date_t) : 0;
    date_t* r = (date_t*)v->b;
    if (g_po_enabled && po_season_half()) {          /* the February knockout play-off */
      for (size_t i = 0; i < have; i++) r[i].day = eday(CUPS[0].days[i < 2 ? i : 1]);
      static int said = 0;
      SAID_RESET(said);
      if (have && !said++) logf("fl26swiss: reg %u -- knockout play-off dated days %u and %u (%u record(s))",
                                (unsigned)id, eday(CUPS[0].days[0]), eday(CUPS[0].days[1]), (unsigned)have);
      return prv;
    }
    /* the shipped 230 and 237 (first and second leg) on the August play-offs' midweek days */
    for (size_t i = 0; i < have; i++)
      if (r[i].day >= 200 && r[i].day < 300) r[i].day = qr_day(0, r[i].day < 234 ? 0 : 1);
    SAID_RESET(g_playoff_said);
    if (have && !g_playoff_said++)
      logf("fl26swiss: reg %u -- play-off on days %u and %u (shipped 230 and 237), first leg on day %u",
           (unsigned)id, qr_day(0, 0), qr_day(0, 1), r[0].day);
    return prv;
  }
  if (vec && (new_po(id) || q_added(id) >= 0)) {
    /* the added play-offs and qualifying rounds: past the calendar switch, so they borrow reg 2's
       records (the same tie of it) and get the days of their round */
    int qi = q_added(id), ci = qi >= 0 ? qi % NQ : (id & 0x3ff) == UEL_PO ? 1 : 2;
    /* a round of sixteen ties (q_n): reg 2 has eight, so ties 9..16 borrow ties 1..8's */
    unsigned tie_ = id >> 10, lend = tie_ > 8 ? (tie_ - 1) % 8 + 1 : tie_;
    uint64_t rv = ((date_fn)(uintptr_t)g_tramp_date)((reg & ~(uint64_t)0xffff) | (uint16_t)((lend << 10) | 2), vec);
    vec_t* v = (vec_t*)vec;
    size_t have = (v->b && v->e >= v->b) ? (size_t)(v->e - v->b) / sizeof(date_t) : 0;
    date_t* r = (date_t*)v->b;
    /* in the summer the play-offs are the August ones (q_fill), on the Champions League's days */
    int aug = q_summer() || qi >= 0;
    uint32_t days[2];
    for (int l = 0; l < 2; l++) days[l] = qi >= 0 ? qr_day(qi / NQ, l) : aug ? qr_day(0, l) : eday(CUPS[ci].days[l]);
    for (size_t i = 0; i < have; i++) r[i].day = days[i < 2 ? i : 1];
    static int said[2][NQR], sk = -1000;
    { int k_ = log_season(); if (k_ != sk) { sk = k_; memset(said, 0, sizeof said); } }
    int si = qi >= 0 ? qi : ci;
    if (!said[aug][si]++)
      logf("fl26swiss: reg %u -- %s %s %s dated days %u and %u (%u record(s))", (unsigned)id, CUPS[ci].name,
           aug ? (qi >= NQ * 3 ? "July" : "August") : "knockout", qi >= 0 ? QSTAGE[qi / NQ] : "play-off", days[0], days[1], (unsigned)have);
    return rv;
  }
  if (vec && (id == UECL_KO || id == 4 || id == 6)) {
    /* The knockouts, round of 16 to the final: seven dates.  The calendar is a switch on the
     * regulation id and 187 is past its end, so the Conference League knockout takes reg 6's
     * records (it would otherwise get sixteen ties and no dates, and nothing would play it).
     * Then all three get UEFA's real evenings -- the shipped ones put the Champions League round
     * of 16 on 24 February, which is the second leg of the play-off. */
    uint64_t rv = ((date_fn)(uintptr_t)g_tramp_date)(id == UECL_KO ? (reg & ~(uint64_t)0xffff) | 6 : reg, vec);
    vec_t* v = (vec_t*)vec;
    size_t have = (v->b && v->e >= v->b) ? (size_t)(v->e - v->b) / sizeof(date_t) : 0;
    date_t* r = (date_t*)v->b;
    int k = id == 4 ? 0 : id == 6 ? 1 : 2;
    static int said[3];
    { static int sk = -1000; int k_ = log_season(); if (k_ != sk) { sk = k_; memset(said, 0, sizeof said); } }
    if (have == 9) {
      /* reg 6's shipped calendar still has the old round of 32 in front (rounds 46, 47, 51, 52,
         53). A knockout of sixteen plays its round of 16 on the FIRST pair and skips the second
         (measured on reg 187, 2026-09-24: 18/25 Feb, then April), so both pairs get the round of
         16's dates and the rest follow in order. */
      r[0].day = r[2].day = eday(KO_DAYS[k][0]);
      r[1].day = r[3].day = eday(KO_DAYS[k][1]);
      for (int i = 4; i < 9; i++) r[i].day = eday(KO_DAYS[k][i - 2]);
      if (!said[k]++) logf("fl26swiss: reg %u -- knockout (9 records) on UEFA's dates: %u/%u, %u/%u, %u/%u, final %u",
                           (unsigned)id, r[0].day, r[1].day, r[4].day, r[5].day, r[6].day, r[7].day, r[8].day);
    } else if (have == 7) {
      for (int i = 0; i < 7; i++) r[i].day = eday(KO_DAYS[k][i]);
      if (!said[k]++) logf("fl26swiss: reg %u -- knockout on UEFA's dates: %u/%u, %u/%u, %u/%u, final %u",
                           (unsigned)id, r[0].day, r[1].day, r[2].day, r[3].day, r[4].day, r[5].day, r[6].day);
    } else if (!said[k]++) {
      logf("fl26swiss: reg %u -- knockout calendar has %u date(s), not 7; left as the game gave it",
           (unsigned)id, (unsigned)have);
      for (size_t i = 0; i < have && i < 16; i++)
        logf("fl26swiss:   date %u: day %u round %u kind %u", (unsigned)i, r[i].day, r[i].round, r[i].kind);
    }
    return rv;
  }
  if (vec && (our_league(id) || eudate(id))) {
    uint64_t rv = ((date_fn)(uintptr_t)g_tramp_date)(reg, vec);
    league_dates(id, reg, vec);
    return rv;
  }
  if (vec && !ours(id)) {                           /* a league of the game's own */
    uint64_t rv = ((date_fn)(uintptr_t)g_tramp_date)(reg, vec);
    cont_note(id, vec);                             /* ... or a continental one: its days kept */
    if (natcup_fix(id, vec)) return rv;             /* ... or a national cup (case 6) */
    vec_t* v = (vec_t*)vec;
    size_t have = (v->b && v->e >= v->b) ? (size_t)(v->e - v->b) / sizeof(date_t) : 0;
    if (have >= 2 && have <= 64 && rest_league(id, have)) rest_dates(id, (date_t*)v->b, (uint32_t)have);
    return rv;
  }
  if (!vec || !ours(id))
    return ((date_fn)(uintptr_t)g_tramp_date)(reg, vec);

  uint64_t rv = ((date_fn)(uintptr_t)(g_base + CASE5_RVA))(reg, vec);

  vec_t* v = (vec_t*)vec;
  size_t have = (v->b && v->e >= v->b) ? (size_t)(v->e - v->b) / sizeof(date_t) : 0;
  int six = id == UECL_ROW;
  int nmd = six ? FL26_SWISS6_MATCHDAYS : FL26_SWISS36_MATCHDAYS;
  if (have < (size_t)nmd) {
    logf("fl26swiss: reg %u wanted %d matchdays but the shipped calendar gave %u -- left alone",
         (unsigned)id, nmd, (unsigned)have);
    return rv;
  }

  date_t* r = (date_t*)v->b;
  uint32_t shift = six ? 0 : day_shift(id);
  const uint32_t* days = six ? UECL_DAYS : SWISS_DAYS;
  for (int i = 0; i < nmd; i++) {
    r[i].day   = (six ? eday(days[i]) : swiss_day(i)) + shift;
    r[i].round = (uint32_t)i;
    r[i].kind  = FL26_DATE_KIND_LEAGUE;
  }
  v->e = v->b + (size_t)nmd * sizeof(date_t);
  g_stat[4]++;
  /* asked for once per match placed, so say it once per regulation */
  static uint16_t said[MAX_REGS]; static int nsaid = 0; int seen = 0;
  SAID_RESET(nsaid);
  for (int k = 0; k < nsaid; k++) if (said[k] == id) seen = 1;
  if (!seen && nsaid < MAX_REGS) said[nsaid++] = id;
  if (!seen)
    logf("fl26swiss: reg %u -- calendar written: %d matchdays, days %u..%u",
         (unsigned)id, nmd, r[0].day, r[nmd - 1].day);
  return rv;
}

/* ---- Cup mode: no league phase of 36 (GitHub #100) ----
 *
 * Kick Off > Cup lists every competition of a category, and ours come along: the Champions,
 * Europa and Conference League with their league phase of 36 clubs, one group, that only this
 * module knows how to run, and only in Master League.  Cup mode draws groups of four from it --
 * group A filled, the rest empty -- and crashes once a club is picked.  The game has no flag
 * that keeps a competition out of Cup mode alone, so the Cup select menu (MenuModeCupSelect,
 * vtable 0x142692c40, only reached from the Cup flow; Master League uses MenuModeCompeSelect)
 * gets its init, slot +0xd8, wrapped: before the menu counts its choices, the list it built in
 * this+0x90 (begin) / +0x98 (end), 12-byte items with the competition id at +0, loses every
 * competition whose group phase (0x14150af30 kind 2, the one Regulations shows as Draw Size)
 * holds more than 32 clubs and is ours or a league phase of 36. */
#define CUPSEL_VT_RVA   0x2692d18   /* vtable 0x142692c40 + 0xd8 */
#define CUPSEL_INIT_RVA 0xb1c990
typedef char (*cupsel_fn)(void* self, uint64_t a, uint64_t b, uint64_t c);
static uint32_t g_cupsel_n = 0;
char cupsel_handler(unsigned char* self, uint64_t a, uint64_t b, uint64_t c)
{
  unsigned char** pb = (unsigned char**)(self + 0x90);
  unsigned char** pe = (unsigned char**)(self + 0x98);
  unsigned char* w = *pb;
  int gone = 0;
  for (unsigned char* p = *pb; p && p + 12 <= *pe; p += 12) {
    uint32_t cid = *(uint32_t*)p;
    uint16_t g = (uint16_t)((phkind_fn)(uintptr_t)(g_base + PHKIND_RVA))(&cid, 2);
    unsigned char* rec = g != 0xffff ? find_rec(g) : 0;
    /* B473: only a league phase this module runs, or one of 36, goes.  The game's own bigger
     * group phases stay in the list -- FL27's World Cup has a group phase of 48 clubs. */
    int n = rec ? (rec[0x30c] & 0x7f) : 0, ours = 0;
    for (int k = 0; k < g_nreg; k++) if (g_reg[k] == g) ours = 1;
    if (n > 32 && (ours || n == 36)) {
      if (g_cupsel_n++ < 8)
        logf("fl26swiss: Cup mode -- competition %u left out (group phase %u has %u clubs)",
             (unsigned)*(uint32_t*)p, (unsigned)g, (unsigned)(rec[0x30c] & 0x7f));
      gone++;
      continue;
    }
    if (w != p) memmove(w, p, 12);
    w += 12;
  }
  if (gone) *pe = w;
  return ((cupsel_fn)(uintptr_t)(g_base + CUPSEL_INIT_RVA))(self, a, b, c);
}

static int cupsel_install(uint64_t exe_base)
{
  uint64_t* slot = (uint64_t*)(uintptr_t)(exe_base + CUPSEL_VT_RVA);
  if (*slot != exe_base + CUPSEL_INIT_RVA) return 2;
  DWORD old;
  if (!VirtualProtect(slot, 8, PAGE_READWRITE, &old)) return 4;
  *slot = (uint64_t)(uintptr_t)cupsel_handler;
  VirtualProtect(slot, 8, old, &old);
  return 0;
}

/* ---- the league phase's matchday label (GitHub #75) ----
 *
 * The label a match shows ("Matchday %d") is its matchday index plus one, built by
 * 0x14152a590(out, u16* reg, u32* md, u32* leg, u8, u8) for every screen (19 UI callers go
 * through 0x14152af20). Our league phase splits each of UEFA's rounds over two matchdays (16
 * for 36 clubs, 12 for the Conference League), so a club that plays the first half of every
 * round read 1, 3, 5, ... The label gets half the index -- both halves of a round read the
 * same round. Only the label: the index itself is the key that ties a match to its fixture
 * record and its date, and stays as it is. Replicas (reg + k*0x400) are ours too; a cup round
 * (index 0x2e and up) is left alone. */
#define MDLABEL_RVA 0x152a590
static const unsigned char SIG_MDLABEL[17] = {
  0x40,0x55, 0x56, 0x57, 0x41,0x54, 0x41,0x55, 0x41,0x56, 0x41,0x57, 0x48,0x8d,0x6c,0x24,0xe0 };
typedef void* (*mdlabel_fn)(void* out, uint16_t* reg, uint32_t* md, uint32_t* leg, uint8_t a5, uint8_t a6);
unsigned char* g_tramp_mdlabel = 0;
/* our rows are themselves replicas (1027 = 3 + 0x400), so masking only the id never matched;
 * compare the low ten bits on both sides and stay above the shipped base row */
static int ours_rep(uint16_t id)
{
  if (id < 0x400) return 0;
  for (int i = 0; i < g_nreg; i++) if ((g_reg[i] & 0x3ff) == (id & 0x3ff)) return 1;
  return 0;
}
void* mdlabel_handler(void* out, uint16_t* reg, uint32_t* md, uint32_t* leg, uint8_t a5, uint8_t a6)
{
  if (reg && md && *md < FL26_SWISS36_MATCHDAYS && ours_rep(*reg)) {
    uint32_t m = *md / 2;
    return ((mdlabel_fn)g_tramp_mdlabel)(out, reg, &m, leg, a5, a6);
  }
  return ((mdlabel_fn)g_tramp_mdlabel)(out, reg, md, leg, a5, a6);
}

/* ---- install ---- */
/* The hook gate: every jmp of ours goes through a qword (`jmp [rip+0]; dq handler`), so
   pointing that qword at the trampoline -- the game's own code -- takes the hook out without a
   byte of code changed under a running thread. */
#define GATE_MAX 160
static struct { void* volatile* slot; void* handler; void* pass; } g_gate[GATE_MAX];
static int g_ngate = 0;
static void gate_add(void* slot, void* handler, void* pass)
{
  if (g_ngate < GATE_MAX) { g_gate[g_ngate].slot = (void* volatile*)slot; g_gate[g_ngate].handler = handler; g_gate[g_ngate].pass = pass; g_ngate++; }
}
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
  gate_add(target + 6, handler, t);
  return 0;
}

/* Same, but if another of our modules already sits on the function -- its hook is the same
   14-byte `jmp [rip+0]; dq handler` -- go in front of it: the trampoline jumps to that handler,
   which still ends in the original.  fl26chain.dll holds set_clubs 0x141522b50 and loads first. */
static int g_chained = 0;

/* ---- B49: the kept tables and cup winners outlive the game session ----
 *
 * The final tables (g_final) and cup winners (g_cupwin) kept at the July teardown, at New Year
 * and for an Apertura + Clausura league lived in memory alone. A game quit between the teardown
 * (about 1 July) and the August draws, or a save of those weeks loaded (a load is another
 * timeline in abs_day, so whatever was kept before it is two years old), and the season's
 * continental places went by squad strength (seed_of) instead of last season's tables:
 * bythezl19's Cyprus and Bosnia had "8 from tables, 124 from first-season order" after a save of
 * day 207 was loaded (B49); a continental super cup of ours took its cup winners from the game
 * again (B51).
 *
 * Every keep is now written to fl26swiss-state.bin in the game's save folder (Mod Studio
 * switches that folder with the world, so each world has its own), one record per table or
 * winner: the club the user manages, the game's date (year * 365 + day, the same on every
 * timeline), the regulation and the clubs. Whenever the game's date and abs_day stop moving
 * together, or the user's club changes -- a game started, a save loaded -- what memory keeps is
 * put on the new footing (and left out when it is dated after today: a later save's), then the
 * records of the user's club dated today or before, and less than STATE_AGE days before, are
 * read back, each regulation's newest, at the abs_day that date is now: every window that asks
 * "kept this summer" sees them as if they had never left memory. A record dated after today
 * belongs to a later save of the career and is not taken (a new career is built on day 216 or
 * 0, before any keep of its club); a career with another club never sees them. A keep in
 * memory as recent as the file's stays. Nothing of the game is hooked for this: the file is
 * written from teardown_pre and apclau_keep, read from final_of, cupwin_of and any_final_kept. */
#define STATE_FILE "fl26swiss-state.bin"
#define STATE_AGE  400      /* past every window a keep is asked in (CONT_KEEP 330 the longest) */
static const char STATE_MAGIC[8] = { 'F', 'L', '2', '6', 'S', 'S', 'T', '1' };
typedef struct {
  uint32_t user;                 /* the user's club when it was written */
  int32_t gdate;                 /* the game's date of the keep: year * 365 + day */
  uint16_t reg;
  uint8_t kind, n;               /* kind 0 a final table (n clubs), 1 a cup winner (n 1),
                                    2 the career built on gdate (B209; reg 0, n 1, the club),
                                    3 a league by squad strength (seed_of / assoc_seed, n clubs) */
  uint32_t club[FINAL_MAX];
  uint32_t check;
} state_rec_t;
/* every final table and cup winner memory can hold: state_store took 64 + 32 from before g_final
   grew to FINAL_N, and in a fourth season (2026-10-21, r12, ~110 keeps) want[] ran over the
   globals after it -- UEFA10's, so Competition Info's League Phase called address 0 */
#define STATE_MAXREC (FINAL_N + CUPWIN_N + 1 + SEED_N + 2 * NQ)
#define STATE_BUILT 2
/* B240 (antonimus 25.10.): a first season's places go by squad strength, worked out once and kept
   for the summer -- in memory. A save loaded weeks later worked it out again from squads that had
   changed since (two Ecuadorian clubs at 77.5 and 77.8 swapped), and the Libertadores groups'
   fill on day 41 put in the club now second, LDU Quito, which had played and lost the
   Pre-Libertadores, in place of the one the season had started with. The order is kept in the
   file too, and read back with the rest. Older DLLs pass these records over (kind > 2). */
#define STATE_SEED 3
/* FL27's first qualifying round, kept the day after its second leg (q1_keep): reg its regulation,
   n 32, the sixteen winners then the sixteen losers. Older DLLs pass it over (kind > 3). A round
   past FINAL_MAX clubs (the wide Conference League's 62, qcw_world) is two records of n / 2: the
   winners under reg, the losers under reg | STATE_Q1_LOSERS -- the record keeps its size */
#define STATE_Q1 4
#define STATE_Q1_LOSERS 0x8000
#define BUILT_SUMMER 300    /* built to its first August draw: day 216 or, a January league's, day 0 */
static int g_st_off = -0x7fffffff, g_st_day = -0x7fffffff, g_st_busy = 0;
static uint32_t g_st_user = 0;
#if defined(FL26_RCAL_TEST) && !defined(FL26_STATE_TEST)
#define STATE_OFF                /* the calendar harness: no game, no save folder */
#endif
#ifdef FL26_STATE_TEST
int state_test_date(void);
uint32_t state_test_user(void);
const char* state_test_path(void);
#endif
/* the game's date, year * 365 + day (the two fields season_year reads), or -1 */
static int game_date(void)
{
#ifdef FL26_STATE_TEST
  return state_test_date();
#else
  unsigned char* o = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
  unsigned char* blk = o ? *(unsigned char**)(o + 0x48) : 0;
  if (!blk) return -1;
  int t = *(uint16_t*)(blk + TODAY_OFF), y = *(uint16_t*)(blk + TODAY_OFF + 8);
  return t >= 365 || y < 1990 || y > 2200 ? -1 : y * 365 + t;
#endif
}
static uint32_t state_user(void)
{
#ifdef FL26_STATE_TEST
  return state_test_user();
#else
  unsigned char* o = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
  return user_club(o ? *(void**)(o + 0x48) : 0);
#endif
}
/* <Documents>\KONAMI\eFootball PES 2021 SEASON UPDATE\<id>\save\fl26swiss-state.bin, beside
   fl26edit's side file, in UTF-8 (B296: any letters in Documents, and the <id> folder the game
   really saves in -- fl26savedir.h). Asked at every use: a first save can make that folder */
static const char* state_path(void)
{
#ifdef FL26_STATE_TEST
  return state_test_path();
#else
  static char path[1024]; static int told = 0;
  char d[sizeof path - 32];
  if (!fl26_save_dir(d, sizeof d)) {
    if (!told) logf("fl26swiss: state -- no Documents folder; kept tables live in memory only");
    told = 1;
    return 0;
  }
  snprintf(path, sizeof path, "%s\\" STATE_FILE, d);
  return path;
#endif
}
static uint32_t state_check(const state_rec_t* r)
{
  const unsigned char* p = (const unsigned char*)r;
  uint32_t h = 2166136261u;
  for (size_t i = 0; i < sizeof *r - sizeof r->check; i++) { h ^= p[i]; h *= 16777619u; }
  return h;
}
/* the file, read past its magic (written first into a new or empty file); 0 when it cannot be
   opened or is not ours */
static HANDLE state_open(const char* p, int write)
{
  wchar_t w[MAX_PATH * 2];
  if (!fl26_u2w(p, w, MAX_PATH * 2)) return 0;
  HANDLE h = CreateFileW(w, GENERIC_READ | (write ? GENERIC_WRITE : 0), FILE_SHARE_READ, 0,
                         write ? OPEN_ALWAYS : OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, 0);
  if (h == INVALID_HANDLE_VALUE) return 0;
  char m[8]; DWORD got = 0;
  if (ReadFile(h, m, 8, &got, 0) && got == 8 && !memcmp(m, STATE_MAGIC, 8)) return h;
  LARGE_INTEGER size, zero; zero.QuadPart = 0;
  DWORD put = 0;
  if (write && got < 8 && GetFileSizeEx(h, &size) && size.QuadPart < 8 &&
      SetFilePointerEx(h, zero, 0, FILE_BEGIN) && SetEndOfFile(h) &&
      WriteFile(h, STATE_MAGIC, 8, &put, 0) && put == 8) return h;
  CloseHandle(h);
  return 0;
}
/* write what memory keeps and the file has not yet: this timeline's keeps (STATE_AGE) */
static void state_store(void)
{
#ifndef STATE_OFF
  int gn = game_date(), an = abs_day();
  if (gn < 0 || an < 0) return;
  static state_rec_t want[STATE_MAXREC];
  static int have[STATE_MAXREC];
  int nw = 0;
  memset(have, 0, sizeof have);
  uint32_t u = state_user();
  for (int i = 0; i < g_nfinal + g_ncupwin; i++) {
    int fin = i < g_nfinal, age = an - (fin ? g_final[i].day : g_cupwin[i - g_nfinal].day);
    unsigned n = fin ? g_final[i].n : 1;
    if (age < 0 || age > STATE_AGE || !n || n > FINAL_MAX || nw >= STATE_MAXREC) continue;
    state_rec_t* r = &want[nw++];
    memset(r, 0, sizeof *r);
    r->user = u; r->gdate = gn - age; r->kind = (uint8_t)!fin; r->n = (uint8_t)n;
    r->reg = fin ? g_final[i].reg : g_cupwin[i - g_nfinal].reg;
    if (fin) memcpy(r->club, g_final[i].club, n * sizeof(uint32_t));
    else r->club[0] = g_cupwin[i - g_nfinal].club;
    r->check = state_check(r);
  }
  for (int i = 0; i < g_nseed && u; i++) {          /* no club yet: no career to read it back */
    int age = an - g_seed[i].day;
    unsigned n = g_seed[i].n;
    if (age < 0 || age > STATE_AGE || !n || n > FINAL_MAX || nw >= STATE_MAXREC) continue;
    state_rec_t* r = &want[nw++];
    memset(r, 0, sizeof *r);
    r->user = u; r->gdate = gn - age; r->kind = STATE_SEED; r->n = (uint8_t)n;
    r->reg = g_seed[i].reg;
    memcpy(r->club, g_seed[i].club, n * sizeof(uint32_t));
    r->check = state_check(r);
  }
  for (int c = 0; c < NQ && u; c++) {
    const q1kept_t* K = &g_q1kept[c];
    unsigned n = q_n(c + NQ * 3);
    if (K->gdate <= 0 || !q1_world(c) || gn < K->gdate || gn - K->gdate > STATE_AGE || nw >= STATE_MAXREC) continue;
    if (n > FINAL_MAX) {                           /* the wide Conference League's 62: two records */
      if (nw + 2 > STATE_MAXREC) continue;
      for (int half = 0; half < 2; half++) {
        state_rec_t* r = &want[nw++];
        memset(r, 0, sizeof *r);
        r->user = u; r->gdate = K->gdate; r->kind = STATE_Q1; r->n = (uint8_t)(n / 2);
        r->reg = (uint16_t)(g_qreg[c + NQ * 3] | (half ? STATE_Q1_LOSERS : 0));
        memcpy(r->club, half ? K->lose : K->win, n / 2 * sizeof(uint32_t));
        r->check = state_check(r);
      }
      continue;
    }
    state_rec_t* r = &want[nw++];
    memset(r, 0, sizeof *r);
    r->user = u; r->gdate = K->gdate; r->kind = STATE_Q1; r->n = (uint8_t)n;
    r->reg = g_qreg[c + NQ * 3];
    memcpy(r->club, K->win, n / 2 * sizeof(uint32_t));
    memcpy(r->club + n / 2, K->lose, n / 2 * sizeof(uint32_t));
    r->check = state_check(r);
  }
  if (g_new_career && g_built_gdate >= 0 && u && nw < STATE_MAXREC) {
    state_rec_t* r = &want[nw++];
    memset(r, 0, sizeof *r);
    r->user = u; r->gdate = g_built_gdate; r->kind = STATE_BUILT; r->n = 1; r->club[0] = u;
    r->check = state_check(r);
  }
  if (!nw) return;
  const char* p = state_path();
  HANDLE h = p ? state_open(p, 1) : 0;
  if (!h) {
    if (p) logf("fl26swiss: state -- cannot write %s (error %lu); kept tables live in memory only", p, GetLastError());
    return;
  }
  state_rec_t r; DWORD got = 0;
  LARGE_INTEGER end; end.QuadPart = 8;
  while (ReadFile(h, &r, sizeof r, &got, 0) && got == sizeof r) {
    end.QuadPart += sizeof r;
    for (int k = 0; k < nw; k++) if (!have[k] && !memcmp(&r, &want[k], sizeof r)) have[k] = 1;
  }
  int put = 0, ok = SetFilePointerEx(h, end, 0, FILE_BEGIN) && SetEndOfFile(h);   /* a torn record off */
  for (int k = 0; k < nw && ok; k++) {
    if (have[k]) continue;
    DWORD w = 0;
    ok = WriteFile(h, &want[k], sizeof want[k], &w, 0) && w == sizeof want[k];
    put += ok;
  }
  CloseHandle(h);
  if (ok && g_new_career && g_built_gdate >= 0 && u) g_built_stored = 1;
  if (put || !ok)
    logf("fl26swiss: state -- %d keep(s) written for club %08x on day %d%s", put, u, today(), ok ? "" : " (write failed)");
#endif
}
/* read the user's career back when the game's date and abs_day no longer move together */
/* 2026-11-05 (FL27 limits, a world of 64873 players): a new career of the same club on the same
   day as an earlier one in that save folder takes the earlier career's records -- same club, same
   date -- and the earlier one had been made in a world built from a bigger recipe. Its first
   season's order (STATE_SEED) named six clubs by ids this world does not have; the Champions
   League qualifiers drawn from it on 12 August put them in, 0x1414bca80 found no team for them,
   and 0x141333485 read an empty squad list (the B312 address). A world built again since a career
   (leagues taken off, clubs renumbered) does the same in one save folder. A record with a club no
   team record answers for, after canon_club, belongs to another world and is not read back.
   With no team array to look at (the native harnesses), every record is taken as before. */
static int state_clubs_known(const state_rec_t* r)
{
  uint32_t n;
  unsigned char* a = team_array(&n);
  if (!a) return 1;
  for (unsigned i = 0; i < r->n; i++) {
    uint32_t c = r->club[i];
    if (!c || c == 0xffffffffu || !(c >> 14)) continue;
    c = canon_club(c);
    if ((c & 0x3fff) >= n || team_at(a, c & 0x3fff) != c) return 0;
  }
  return 1;
}
static void state_sync(void)
{
#ifndef STATE_OFF
  if (g_st_busy) return;
  int gn = game_date();
  if (gn < 0) return;
  int an = abs_day();
  if (an < 0 || (gn - an == g_st_off && an == g_st_day && g_st_user)) return;   /* no club yet: ask again */
  uint32_t u = state_user();
  if (gn - an == g_st_off && u == g_st_user) { g_st_day = an; return; }
  /* what memory keeps, put on today's footing: kept while the game's date was abs_day + the
     old offset; a keep dated after today is a later save's, left out (abs_day can take a save
     of a year before, near the same day, for days going on) */
  int old = g_st_off, off = gn - an, later = 0;
  if (old != -0x7fffffff && old != off) {
    for (int i = 0; i < g_nfinal; ) {
      if (g_final[i].day + old > gn) { g_final[i] = g_final[--g_nfinal]; later++; continue; }
      g_final[i].day += old - off; i++;
    }
    for (int i = 0; i < g_ncupwin; ) {
      if (g_cupwin[i].day + old > gn) { g_cupwin[i] = g_cupwin[--g_ncupwin]; later++; continue; }
      g_cupwin[i].day += old - off; i++;
    }
    for (int i = 0; i < g_nseed; ) {
      if (g_seed[i].day + old > gn) { g_seed[i] = g_seed[--g_nseed]; later++; continue; }
      g_seed[i].day += old - off; i++;
    }
    for (int c = 0; c < NQ; c++) if (g_q1kept[c].gdate > gn) { g_q1kept[c].gdate = 0; later++; }
    if (later) logf("fl26swiss: state -- %d keep(s) of a later date left out: a save of an earlier day loaded", later);
  }
  if (g_st_user && u != g_st_user) for (int c = 0; c < NQ; c++) g_q1kept[c].gdate = 0;   /* another club's career */
  g_st_off = off; g_st_day = an; g_st_user = u; g_st_read_back = 0;
  g_built_any = -1;
  const char* p = state_path();
  HANDLE h = p ? state_open(p, 0) : 0;
  if (!h) return;
  static state_rec_t best[STATE_MAXREC];
  int nb = 0, foreign = 0;
  state_rec_t r; DWORD got = 0;
  while (ReadFile(h, &r, sizeof r, &got, 0) && got == sizeof r) {
    if (r.check != state_check(&r) || r.user != u || r.gdate > gn || gn - r.gdate > STATE_AGE ||
        r.kind > STATE_Q1 || !r.n || r.n > FINAL_MAX ||
        ((r.kind == 1 || r.kind == STATE_BUILT) && r.n != 1)) continue;
    if (!state_clubs_known(&r)) { foreign++; continue; }
    int k = 0;
    while (k < nb && (best[k].kind != r.kind || best[k].reg != r.reg)) k++;
    if (k == nb) { if (nb >= STATE_MAXREC) continue; nb++; }
    else if (r.gdate < best[k].gdate) continue;
    best[k] = r;                                   /* the newest; of one day, the last written */
  }
  CloseHandle(h);
  if (foreign)
    logf("fl26swiss: state -- %d record(s) of club %08x left out: they name clubs this world has no team for "
         "(another world's career, or the world built again since)", foreign, u);
  int nf = 0, nc = 0, ns = 0, nq1 = 0, built = -1;
  for (int k = 0; k < nb; k++)
    if (best[k].kind == STATE_BUILT) g_built_any = best[k].gdate;
  /* B209: a career of this club built less than BUILT_SUMMER days ago is in its first summer,
     whether or not the game was quit since: it is new again, and the tables it kept itself (a
     January league's, by July) do not make it a later season's */
  for (int k = 0; k < nb; k++)
    if (best[k].kind == STATE_BUILT && gn - best[k].gdate < BUILT_SUMMER) built = best[k].gdate;
  if (built >= 0 && !g_new_career && (gn - built > (gn % 365 - FIRST_SUMMER_END + 365) % 365)) {
    logf("fl26swiss: state -- club %08x's career was built %d day(s) ago, its first summer is over", u, gn - built);
    built = -1;
  }
  if (built >= 0 && !g_new_career) {
    g_new_career = 1; g_built_gdate = built; g_built_stored = 1; g_first_day = -1;
    logf("fl26swiss: state -- club %08x's career was built %d day(s) ago: still its first summer", u, gn - built);
  }
  g_st_busy = 1;
  for (int k = 0; k < nb; k++) {
    int day = an - (gn - best[k].gdate);
    if (best[k].kind == STATE_BUILT) continue;
    if (best[k].kind == STATE_Q1) {                /* FL27's first qualifying round, this summer's */
      for (int c = 0; c < NQ; c++) {
        unsigned n = q_n(c + NQ * 3);
        if (!q1_world(c) || gn - best[k].gdate >= 100 || g_q1kept[c].gdate >= best[k].gdate) continue;
        if (n > FINAL_MAX) {
          /* two records (state_store): the winners' and, of the same date, the losers' */
          if (g_qreg[c + NQ * 3] != best[k].reg || best[k].n != n / 2) continue;
          int lo = -1;
          for (int j = 0; j < nb; j++)
            if (best[j].kind == STATE_Q1 && best[j].reg == (uint16_t)(best[k].reg | STATE_Q1_LOSERS)
                && best[j].gdate == best[k].gdate && best[j].n == n / 2) lo = j;
          if (lo < 0) continue;
          g_q1kept[c].gdate = best[k].gdate;
          memcpy(g_q1kept[c].win, best[k].club, n / 2 * sizeof(uint32_t));
          memcpy(g_q1kept[c].lose, best[lo].club, n / 2 * sizeof(uint32_t));
          nq1++;
          continue;
        }
        if (g_qreg[c + NQ * 3] != best[k].reg || best[k].n != n) continue;
        g_q1kept[c].gdate = best[k].gdate;
        memcpy(g_q1kept[c].win, best[k].club, n / 2 * sizeof(uint32_t));
        memcpy(g_q1kept[c].lose, best[k].club + n / 2, n / 2 * sizeof(uint32_t));
        nq1++;
      }
      continue;
    }
    if (best[k].kind == STATE_SEED) {
      final_t* f = 0;
      for (int i = 0; i < g_nseed; i++) if (g_seed[i].reg == best[k].reg) f = &g_seed[i];
      if (f && f->day >= day) continue;
      if (!f) { if (g_nseed >= SEED_N) continue; f = &g_seed[g_nseed++]; }
      memset(f, 0, sizeof *f);
      f->reg = best[k].reg; f->n = best[k].n; f->day = day;
      memcpy(f->club, best[k].club, best[k].n * sizeof(uint32_t));
      ns++;
      continue;
    }
    if (!best[k].kind) {
      final_t* f = final_of(best[k].reg);
      if (f && f->day >= day) continue;
      if (!f) { if (g_nfinal >= FINAL_N) continue; f = &g_final[g_nfinal++]; }
      f->reg = best[k].reg; f->n = best[k].n; f->day = day;
      memcpy(f->club, best[k].club, sizeof f->club);
      nf++;
      if (an - day < 120 && !(built >= 0 && best[k].gdate >= built))
        g_st_read_back = 1;                        /* last season's: not a career's first summer */
    } else {
      cupwin_t* w = cupwin_of(best[k].reg);
      if (w && w->day >= day) continue;
      if (!w) { if (g_ncupwin >= CUPWIN_N) continue; w = &g_cupwin[g_ncupwin++]; }
      w->reg = best[k].reg; w->day = day; w->club = best[k].club[0];
      nc++;
    }
  }
  g_st_busy = 0;
  if (nf || nc || ns)
    logf("fl26swiss: state -- %d final table(s), %d cup winner(s) and %d squad-strength order(s) of club %08x's career read back on day %d (%s)",
         nf, nc, ns, u, today(), STATE_FILE);
  if (nq1)
    logf("fl26swiss: state -- %d first qualifying round result(s) of club %08x's career read back on day %d (%s)",
         nq1, u, today(), STATE_FILE);
#endif
}

/* ---- Apertura + Clausura: the season's table ----
 *
 * The final table the July teardown keeps for a league (access_capture) is the one the game
 * shows under the league's id, and for an Apertura/Clausura league that is the Clausura alone:
 * the Clausura starts from zero points (carry=0), so the continental places went by half a
 * season (GitHub #57, Liga 1 of Peru). The places belong to the two tournaments added
 * together. So once every match of both is played -- each club meets every other once in
 * each, n(n-1) matches -- the table is counted from them (count_table) and kept as the
 * league's final table, dated that day; access_capture then leaves it alone (it keeps a table
 * for 60 days) and every place reads it. Looked at once a day from the day loop, from the
 * spring until the July teardown deletes the matches. */
static void apclau_keep(void)
{
  static int last = -1;
  int d = abs_day(), td = today();
  if (d == last || td < 60 || td > 180 || !g_nnocarry) return;
  last = d;
  for (int k = 0; k < g_nsplits; k++) {
    const split_t* s = &SPLITS[k];
    if (!nocarry(s->total) || !s->group[0]) continue;
    final_t* f = final_of(s->total);
    if (f && d >= f->day && d - f->day < 60) continue;
    uint16_t regs[2] = { s->regular, s->group[0] };
    final_t t;
    int played, n = count_table(regs, 2, &t, &played);
    if (n < 4 || played < n * (n - 1)) continue;
    if (!f && !(f = final_new(s->total))) continue;
    *f = t; f->reg = s->total; f->day = d;
    logf("fl26swiss: reg %u -- Apertura + Clausura table from %d matches kept as the final table: "
         "%08x %d pts, %08x %d pts ... last %08x %d pts", (unsigned)s->total, played,
         t.club[0], g_ctab_pts[0], t.club[1], g_ctab_pts[1], t.club[n - 1], g_ctab_pts[2]);
    state_store();
  }
}

/* ---- a season of two tournaments of the game: its whole-season table (seasonsum, see ssum_of) ----
 *
 * Counted from the halves' own tables, not from their matches: a half's table stands until the
 * game builds the next season of it (the Apertura's, 168, read the same on day 360 as when the
 * July teardown kept it on day 176, state files of 05.11.2026), while whether the matches of a
 * half played in the spring are still there in December was never seen. A row of the table
 * (tools/leaguetable.py, read in the game): +0 the club, +8 the points, +9..+0x0e six-bit counts
 * from the bottom -- won, lost, drawn, won at home, then goals for and goals against as twelve
 * bits each -- and +0x0f the matches played.
 *
 * ssum_rows adds one half's table to the sums; it answers the matches each club played, 0 for a
 * table whose clubs have not all played as many (a half under way) or none, -1 for no table.
 * ssum_order puts the sums in order: points, then goal difference, then goals scored (as
 * count_table). Both without the game, for test_season_sum.c. */
typedef struct { int n; uint32_t club[FINAL_MAX]; int pts[FINAL_MAX], gd[FINAL_MAX], gf[FINAL_MAX]; } ssum_tab_t;
static int ssum_rows(const unsigned char* t, uint32_t rows, ssum_tab_t* s)
{
  if (!t || rows < 4 || rows > FINAL_MAX) return -1;
  int mp = t[0x0f];
  for (uint32_t k = 0; k < rows; k++) if (t[k * 20 + 0x0f] != mp) return 0;
  if (!mp) return 0;
  for (uint32_t k = 0; k < rows; k++) {
    const unsigned char* r = t + k * 20;
    uint32_t c = *(const uint32_t*)r;
    uint64_t v = 0;
    for (int b = 0; b < 6; b++) v |= (uint64_t)r[9 + b] << (8 * b);
    int f = (int)(((v >> 24) & 63) | (((v >> 30) & 63) << 6)), a = (int)(((v >> 36) & 63) | (((v >> 42) & 63) << 6));
    int i = 0;
    while (i < s->n && s->club[i] != c) i++;
    if (i == s->n) {
      if (s->n >= FINAL_MAX) continue;
      s->club[i] = c; s->pts[i] = s->gd[i] = s->gf[i] = 0; s->n++;
    }
    s->pts[i] += r[8]; s->gd[i] += f - a; s->gf[i] += f;
  }
  return mp;
}
static void ssum_order(ssum_tab_t* s)
{
  for (int a = 1; a < s->n; a++)                  /* insertion sort, stable */
    for (int b = a; b > 0; b--) {
      int x = b - 1, y = b;
      if (s->pts[y] < s->pts[x] || (s->pts[y] == s->pts[x] && (s->gd[y] < s->gd[x]
          || (s->gd[y] == s->gd[x] && s->gf[y] <= s->gf[x])))) break;
      uint32_t c = s->club[x]; s->club[x] = s->club[y]; s->club[y] = c;
      int t = s->pts[x]; s->pts[x] = s->pts[y]; s->pts[y] = t;
      t = s->gd[x]; s->gd[x] = s->gd[y]; s->gd[y] = t;
      t = s->gf[x]; s->gf[x] = s->gf[y]; s->gf[y] = t;
    }
}
/* Looked at once a day from the day loop and before every teardown (teardown_pre): when the
 * season's last half has every match played (season_played) and a complete table, the tables of
 * the halves are added together and kept as the total's final table, once a season (a table kept
 * less than 60 days ago stands). A half before it with no complete table -- a career begun after
 * the Apertura, whose table nobody played -- is left out of the sum and said in the log; with no
 * complete table of the last half, nothing is kept (said once a season). */
static void ssum_keep(int teardown)
{
  static int last = -1, said_day[SSUM_MAX];
  int d = abs_day();
  if (!g_nssum || (d == last && !teardown)) return;
  last = d;
  for (int k = 0; k < g_nssum; k++) {
    const ssum_t* s = &g_ssum[k];
    final_t* f = final_of(s->total);
    if (f && d >= f->day && d - f->day < 60) continue;
    int nr = 0;
    while (nr < SSUM_PARTS && s->part[nr]) nr++;
    if (!nr || !season_played(s->part[nr - 1])) continue;
    ssum_tab_t sum; sum.n = 0;
    int mp[SSUM_PARTS], left = 0;
    for (int p = 0; p < nr; p++) {
      unsigned char* rec = get_rec(s->part[p]);
      unsigned char* t = rec ? ((table_fn)(uintptr_t)(g_base + TABLE_RVA))(s->part[p]) : 0;
      mp[p] = ssum_rows(t, t ? *(uint32_t*)(t + 0x3c0) : 0, &sum);
      if (mp[p] <= 0) left++;
    }
    if (mp[nr - 1] <= 0 || sum.n < 4) {
      if (said_day[k] == 0 || d - said_day[k] > 300 || d < said_day[k]) {
        said_day[k] = d ? d : 1;
        logf("fl26swiss: reg %u -- whole season: its last half %u has every match played but %s; "
             "no whole-season table, its places read half %u", (unsigned)s->total, (unsigned)s->part[nr - 1],
             mp[nr - 1] < 0 ? "no table" : "no complete table", (unsigned)s->part[0]);
      }
      continue;
    }
    if (left)
      logf("fl26swiss: reg %u -- whole season: %d half(s) with no complete table left out of it (%u: %d, %u: %d "
           "matches a club; 0 not complete)", (unsigned)s->total, left, (unsigned)s->part[0], mp[0],
           (unsigned)s->part[nr > 1 ? 1 : 0], nr > 1 ? mp[1] : mp[0]);
    ssum_order(&sum);
    if (!f && !(f = final_new(s->total))) continue;
    f->reg = s->total; f->day = d; f->n = (uint16_t)sum.n;
    for (int i = 0; i < sum.n; i++) f->club[i] = sum.club[i];
    logf("fl26swiss: reg %u -- whole-season table from the tables of %d half(s) (%d+%d matches a club) kept as "
         "the final table (day %d%s): %08x %d pts, %08x %d pts ... last %08x %d pts", (unsigned)s->total, nr,
         mp[0], nr > 1 ? mp[1] : 0, today(), teardown ? ", teardown" : "", sum.club[0], sum.pts[0],
         sum.club[1], sum.pts[1], sum.club[sum.n - 1], sum.pts[sum.n - 1]);
    state_store();
  }
}

/* ---- the day loop: a cup's fill day, on the days the game stops on ----
 *
 * The loader's tick (every 64th file open) was the only caller of ccup_fill_days, and in July,
 * with no match to load, days go by without a file opened: the Summer Cup (202, 2026-09-29) had
 * the three days 183..185 to be filled in and none of them saw a tick, so it was never played.
 * The day loop (0x1413071e1 -> 0x1413007d0) calls 0x141314fc0, the check that hands the
 * competitions ending that day to the July teardown, on every day it stops on -- not every day:
 * days with nothing on them are passed over (ccup_fill_ahead). The fill days are looked at
 * after it returns, and so is a teardown it has just run. A gap is said in the log. */
#define DAYCHK_RVA 0x1314fc0
static const unsigned char SIG_DAYCHK[17] = {
  0x48,0x89,0x4c,0x24,0x08, 0x55, 0x53, 0x56, 0x57, 0x41,0x54, 0x41,0x55, 0x41,0x56, 0x41,0x57 };
typedef char (*daychk_fn)(void*);
unsigned char* g_tramp_daychk = 0;
static int g_td_fresh = 0;                /* a July teardown ran in this call of the day loop's check */
/* The August play-offs that nothing in the game fills (see the August play-offs above): reg 2 in a
   new career's first summer, the Europa League's and the Conference League's every summer. On the
   days before their first leg each is filled with its sixteen, started and handed to register_all
   -- the steps the Club World Cup groups take. Reg 2 in a second season is found filled by the
   rollover and left alone, and a play-off with matches already this summer (a save loaded in
   August) is not filled again. */
static int g_q_fill_year[NQR] = { -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1 };
static void q_fill(int p)
{
  int d = today();
  if (d < (p >= NQ * 3 ? 181 : 205) || d > (int)qr_day(0, 1)) return;
  if (!q_world_p(p)) { if (q_reg(p)) q_why(p); return; }
  int mask = q_world_mask();
  if (d < (int)q_fill_from(mask, p) || d >= (int)q_first_leg(p)) return;
  int year = (abs_day() + 183) / 365;
  if (g_q_fill_year[p] == year) return;
  g_q_fill_year[p] = year;
  uint16_t reg = q_reg(p);
  if (!p) {
    unsigned char* t0 = get_rec(q_tie(0));
    if (!t0 || rec_count(t0)) return;               /* the rollover filled it: not a first season */
    if (ccup_matches(2) > 0) return;
  } else if (q_matches(p) != 0) {
    if (q_matches(p) > 0) logf("fl26swiss: %s %s already has its matches this summer; not filled again", QNAME(p));
    return;
  }
  if (!q_complete(p)) { logf("fl26swiss: %s %s -- day %d: its sixteen are not known; not filled", QNAME(p), d); return; }
  const int N = (int)q_n(p);
  canon_list(g_q[p], N, "qualifying reg", reg);   /* B312 */
  for (int k = 0; k < N / 2; k++)
    ((freetab_fn)(uintptr_t)(g_base + FREETAB_RVA))(0, q_tie_of(p, k));
  u32vec va = { g_q[p], g_q[p] + N, g_q[p] + N };
  ((setclr_fn)(uintptr_t)g_tramp_setcl)(reg, &va, 1);
  for (int k = 0; k < N / 2; k++) {
    u32vec v = { g_q[p] + 2 * k, g_q[p] + 2 * k + 2, g_q[p] + 2 * k + 2 };
    ((setclr_fn)(uintptr_t)g_tramp_setcl)(q_tie_of(p, k), &v, 1);
  }
  run_flush();
  start_stage(0, reg);
  uint16_t id = reg;
  struct { uint16_t* b; uint16_t* e; uint16_t* c; } rv = { &id, &id + 1, &id + 1 };
  ((regall_fn)(uintptr_t)(g_base + REGALL_RVA))(0, &rv);
  run_flush();
  int m = ccup_matches(reg), mt = 0;
  for (int k = 0; k < N / 2; k++) { int x = ccup_matches(q_tie_of(p, k)); if (x > 0) mt += x; }
  if (m <= 0 && mt <= 0) {                          /* the ties are their own rows: register them too */
    uint16_t ties[Q_MAX / 2];
    for (int k = 0; k < N / 2; k++) ties[k] = q_tie_of(p, k);
    struct { uint16_t* b; uint16_t* e; uint16_t* c; } tv = { ties, ties + N / 2, ties + N / 2 };
    ((regall_fn)(uintptr_t)(g_base + REGALL_RVA))(0, &tv);
    run_flush();
    m = ccup_matches(reg); mt = 0;
    for (int k = 0; k < N / 2; k++) { int x = ccup_matches(q_tie_of(p, k)); if (x > 0) mt += x; }
  }
  logf("fl26swiss: %s %s -- day %d: reg %u filled, started and registered; %d match record(s) under it, %d under its ties",
       QNAME(p), d, (unsigned)reg, m, mt);
  if (p >= NQ * 3) g_q1kept[p % NQ].gdate = 0;      /* this summer's is kept after its second leg */
}
/* ---- one match, one entry in the day lists (0.2.0) ----
 * The calendar is 365 day records after the unit: a 0xffff-terminated list of u16 match ids,
 * its count (+0x230; +0x630 in the -calendar set, 792 ids a day), then the day's events. The
 * scheduler (0x141350290) appends an id with no check, so a match handed to it twice is listed
 * twice, and the hub's Next strip -- the 32 tables of 0x16dc after the calendar, one cell a day
 * -- showed every match twice (2026-10-08, the second career of a session). Every day loop:
 *   - an id twice in one day's list keeps its first entry;
 *   - an id in the lists of two days stays only on the day its match record names (the
 *     record's date, +8: u16 year, u8 month, u8 day), when exactly one of them is that day;
 * and what was found is logged, with a summary once a season. */
/* the day's size follows the set: 0x6c4 (792 ids) since the -calendar set of 0.2.0, 0x2c4 (280)
   before it, any other size on the limits branch, and its ids u32 once the set made them dwords
   (fl26layout.h: lay_day_ids, lay_day_elem); the calendar's start is read from the game's own
   add at 0x140aed7b8 */
#define CAL_STRIDE lay_day_size()
#define CAL_IDCAP  lay_day_ids()
#define CAL_COUNT  lay_day_count()
#define CAL_BASE   lay_calendar()
#define CAL_IDS    (1u << 20)     /* ids past this (none yet: 65000 records) are not deduplicated */
#define MREC_RVA   0x14bb280      /* (blk, id) -> the match record, the scheduler's own lookup */
typedef unsigned char* (*mrec_fn)(void* blk, uint64_t id);
static int16_t g_cal_first[CAL_IDS];
#ifdef FL26_RCAL_TEST
int rcal_test_recday(uint16_t id);
#endif
static int rec_day(unsigned char* blk, uint32_t id)
{
#ifdef FL26_RCAL_TEST
  return rcal_test_recday((uint16_t)id);
#endif
  unsigned char* m = ((mrec_fn)(uintptr_t)(g_base + MREC_RVA))(blk, id);
  if (!m || (lay_day_elem() == 4 ? *(uint32_t*)m : *(uint16_t*)m) != id) return -1;
  int mo = m[8 + 2], dd = m[8 + 3];
  if (mo < 1 || mo > 12 || dd < 1 || dd > 31) return -1;
  return MONTH0[mo - 1] + dd - 1;
}
/* the count after the ids: u16 (the game's movzx), the high half of a dword-sized one is 0 */
static uint16_t* cal_count(unsigned char* day) { return (uint16_t*)(day + CAL_COUNT); }
static void cal_dedupe(void)
{
  unsigned char* o = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
  unsigned char* blk = o ? *(unsigned char**)(o + 0x48) : 0;
  int cap = CAL_IDCAP;
  if (!blk || cap <= 0) return;
  static uint8_t seen[CAL_IDS / 8];
  int same = 0, cross = 0, fixed = 0, total = 0, ex = 0;
  char exs[200]; size_t el = 0; exs[0] = 0;
  memset(g_cal_first, 0xff, sizeof g_cal_first);
  for (int d = 0; d < 365; d++) {
    unsigned char* day = blk + CAL_BASE + (size_t)d * CAL_STRIDE;
    int n = 0, w = 0, removed = 0;
    while (n < cap && lay_day_id(day, n) != 0xffff) n++;
    for (int i = 0; i < n; i++) {
      uint32_t v = lay_day_id(day, i);
      if (v < CAL_IDS) {
        if (seen[v >> 3] & (1 << (v & 7))) {
          removed++;
          if (ex < 6 && el < sizeof exs - 24) { el += snprintf(exs + el, sizeof exs - el, " %u@%d", v, d); ex++; }
          continue;
        }
        seen[v >> 3] |= (uint8_t)(1 << (v & 7));
      }
      lay_day_set(day, w++, v);
    }
    for (int i = 0; i < w; i++) { uint32_t v = lay_day_id(day, i); if (v < CAL_IDS) seen[v >> 3] = 0; }
    if (removed) {
      for (int i = w; i < n; i++) lay_day_set(day, i, 0xffff);
      uint16_t* cnt = cal_count(day);
      *cnt = (uint16_t)(*cnt >= removed ? *cnt - removed : w);
      same += removed;
    }
    total += w;
    /* the same match on two days */
    for (int i = 0; i < w; i++) {
      uint32_t v = lay_day_id(day, i);
      if (v >= CAL_IDS) continue;
      if (g_cal_first[v] < 0) { g_cal_first[v] = (int16_t)d; continue; }
      cross++;
      int e = g_cal_first[v], rd = rec_day(blk, v), drop = rd == d ? e : rd == e ? d : -1;
      if (ex < 6 && el < sizeof exs - 32) { el += snprintf(exs + el, sizeof exs - el, " %u@%d+%d(rec %d)", v, e, d, rd); ex++; }
      if (drop < 0) continue;
      unsigned char* dr = blk + CAL_BASE + (size_t)drop * CAL_STRIDE;
      int m = 0; while (m < cap && lay_day_id(dr, m) != 0xffff) m++;
      for (int k = 0; k < m; k++)
        if (lay_day_id(dr, k) == v) {
          for (int j = k; j < m - 1; j++) lay_day_set(dr, j, lay_day_id(dr, j + 1));
          lay_day_set(dr, m - 1, 0xffff);
          uint16_t* cnt = cal_count(dr); if (*cnt) (*cnt)--;
          fixed++;
          if (drop == d) { w--; i--; }               /* this day's list moved down by one */
          break;
        }
      g_cal_first[v] = (int16_t)(rd == d ? d : e);
    }
  }
  static int sk = -1000;
  int k_ = log_season();
  if (same || cross) logf("fl26swiss: day lists -- %d id(s) twice on one day removed, %d on two days (%d taken off the day their record does not name):%s",
                          same, cross, fixed, exs);
  else if (k_ != sk) logf("fl26swiss: day lists -- %d match id(s), each listed once", total);
  sk = k_;
}
/* B258, the rest (27.10., candidate 0759f85, M2400S, a calendar-year league in its fourth season,
 * loaded on 1 January): the user's day schedule had 14 of the club's 20 league rounds on other days
 * than the calendar's -- round 0 on day 54 with its match on day 49, and so on, one to five days
 * either way -- and a rebuild asked by hand filed them on the same wrong days. The schedule does not
 * take a match's day from its record: it asks the date switch again, and league_dates for a
 * calendar-year league (rcal_dates) weighs the cup and European days known on the day it is asked,
 * so the fixtures (made on the first days) and the schedule (filed later) got two calendars. The
 * calendar's day lists are the days the matches are played; so every day, after cal_dedupe has read
 * them (g_cal_first), the user's entries on another day than their match's are taken out (an empty
 * day's entry in their place) and each is put on its match's day when that day is empty. Taken out
 * first, as a second career (Costa Rica, an August-May league, its 2029) had every entry one round
 * late: each one's day held the entry of the round before. */
#define SCHED_ENT_OFF (TODAY_OFF + 0x14)
/* An entry's match id is a u16. With the u32 ids of the limits branch the table wraps past 65536,
 * so the id in an entry may be the low half of a later match: id and id + 65536 both live (FL27,
 * 06.11., twins test: every league entry of an Anderlecht career named a Senegalese match by its
 * low half, and the day taken from that match put the user's rounds on Senegal's days). The entry
 * keeps its competition at +2 and the user's club at +12; the record that has both is the one. */
static uint32_t sched_id(unsigned char* blk, const unsigned char* e)
{
  uint32_t id = *(const uint16_t*)e, c = *(const uint32_t*)(e + 12) & 0x3fff;
  if (lay_day_elem() != 4) return id;
  for (int k = 0; k < 2; k++) {
    uint32_t v = id + (k ? 0x10000u : 0);
    unsigned char* m = ((mrec_fn)(uintptr_t)(g_base + MREC_RVA))(blk, v);
    if (!m || *(uint32_t*)m != v || *(uint16_t*)(m + 4) != *(const uint16_t*)(e + 2)) continue;
    if ((*(uint32_t*)(m + 0x14) & 0x3fff) == c || (*(uint32_t*)(m + 0x18) & 0x3fff) == c) return v;
  }
  return id;
}
static void sched_days(void)
{
  unsigned char* o = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
  unsigned char* blk = o ? *(unsigned char**)(o + 0x48) : 0;
  if (!blk) return;
  uint32_t user = *(uint32_t*)(blk + USER_CLUB_OFF);
  if (user == 0 || user == 0xffffffffu || *(uint32_t*)(blk + SCHED_OWNER_OFF) != user) return;
  unsigned char* s = blk + SCHED_ENT_OFF;
  static unsigned char out[365][16];
  static int16_t to[365], from[365];
  static int last_lost = 0;
  unsigned char none[16];
  int n = 0, have_none = 0;
  for (int d = 0; d < 365; d++) {
    unsigned char* e = s + (size_t)d * 16;
    if (*(uint16_t*)e == 0xffff) { if (!have_none) { memcpy(none, e, 16); have_none = 1; } continue; }
    if (*(uint32_t*)(e + 12) != user) continue;
    uint32_t v = sched_id(blk, e);
    int c = v < CAL_IDS ? g_cal_first[v] : -1;
    if (c < 0 || c == d || c >= 365) continue;
    memcpy(out[n], e, 16); from[n] = (int16_t)d; to[n++] = (int16_t)c;
  }
  if (!n || !have_none) return;
  for (int d = 0; d < 365; d++) {                      /* out of their days */
    unsigned char* e = s + (size_t)d * 16;
    for (int i = 0; i < n; i++)
      if (*(uint16_t*)e == *(uint16_t*)out[i] && *(uint32_t*)(e + 12) == user) { memcpy(e, none, 16); break; }
  }
  int moved = 0, lost = 0, ex = 0;
  char exs[160]; size_t el = 0; exs[0] = 0;
  for (int i = 0; i < n; i++) {
    unsigned char* t = s + (size_t)to[i] * 16;
    if (*(uint16_t*)t != 0xffff) { to[i] = -1; continue; }   /* its day holds another of the user's */
    memcpy(t, out[i], 16);
    moved++;
    if (ex < 5 && el < sizeof exs - 24) { el += snprintf(exs + el, sizeof exs - el, " %u->%d", *(uint16_t*)out[i], to[i]); ex++; }
  }
  for (int i = 0; i < n; i++) {                        /* those back where they were, when it is free */
    if (to[i] >= 0) continue;
    unsigned char* f = s + (size_t)from[i] * 16;
    if (*(uint16_t*)f == 0xffff) memcpy(f, out[i], 16);
    lost++;
  }
  if (moved || lost != last_lost)
    logf("fl26swiss: the user's day schedule -- %d match(es) moved to their calendar day, %d left where they were (that day holds another of the user's):%s",
         moved, lost, exs);
  last_lost = lost;
}
/* A calendar-year Super Cup is admitted by the season builder before the
 * New Year teardown. The teardown then closes it, but unlike a national cup
 * nothing in the game's progression fills it again. Once last season's league
 * and cup rights exist, rebuild the two-club field and register the cup so its
 * match is made. */
static void calendar_scup_fill_days(void)
{
  int d = today();
  if (!g_ncal_scup || d < 0 || d >= 38) return;

  for (int i = 0; i < g_ncal_scup; i++) {
    const cal_scup_t* cs = &g_cal_scup[i];
    unsigned char* rec = get_rec(cs->reg);
    if (!rec || ccup_matches(cs->reg) > 0) continue;

    uint32_t champion = calendar_scup_right(cs->league, 13);
    uint32_t runner   = calendar_scup_right(cs->league, 14);
    uint32_t cupwin   = calendar_scup_right(cs->cup, 0);
    if (!champion || !cupwin) continue;

    uint32_t opponent =
      ((champion >> 14) == (cupwin >> 14)) ? runner : cupwin;
    if (!opponent || (opponent >> 14) == (champion >> 14)) continue;

    uint32_t clubs[2] = { champion, opponent };
    u32vec v = { clubs, clubs + 2, clubs + 2 };

    ((setclr_fn)(uintptr_t)g_tramp_setcl)(cs->reg, &v, 1);
    run_flush();

    if (rec_count(rec) != 2) {
      logf("fl26swiss: calendar Super Cup %u -- day %d: set_clubs left %u club(s)",
           (unsigned)cs->reg, d, (unsigned)rec_count(rec));
      continue;
    }

    start_stage(0, cs->reg);

    uint16_t id = cs->reg;
    struct { uint16_t* b; uint16_t* e; uint16_t* c; } rv =
      { &id, &id + 1, &id + 1 };

    ((regall_fn)(uintptr_t)(g_base + REGALL_RVA))(0, &rv);
    run_flush();

    logf("fl26swiss: calendar Super Cup %u -- day %d: league %u champion %u v %s %u; registered, %d match record(s)",
         (unsigned)cs->reg, d, (unsigned)cs->league, champion >> 14,
         (champion >> 14) == (cupwin >> 14) ? "league runner-up" : "cup winner",
         opponent >> 14, ccup_matches(cs->reg));
  }
}

/* B234: the August-May ones, after the July teardown and the builder that lets them in (day
 * 181), before the first super cup date of the summer. As the CAF Super Cup at the July
 * teardown: last season's tie tables freed, the pair set, the stage started and register_all
 * asked for the match. A save made after the fill holds this season's pair with its match not
 * yet played: left as it is. */
/* B283: a match of reg played on or after game date `from` (year * 365 + day) */
static int ccup_played_since(uint16_t reg, int from)
{
  const unsigned char* bs = (const unsigned char*)(g_base + MATCH_BASE_SITE);
  const unsigned char* cs = (const unsigned char*)(g_base + MATCH_CAP_SITE);
  if (bs[0] != 0x48 || bs[1] != 0x8d || bs[2] != 0x88 || cs[0] != 0x81 || cs[1] != 0xff) return 0;
  uint32_t base = *(const uint32_t*)(bs + 3), cap = *(const uint32_t*)(cs + 2);
  unsigned char* o = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
  unsigned char* blk = o ? *(unsigned char**)(o + 0x48) : 0;
  if (!blk || !cap || cap > 200000) return 0;
  for (uint32_t i = 0; i < cap; i++) {
    const unsigned char* m = blk + base + (size_t)i * MATCH_STRIDE;
    if (*(const uint16_t*)m != 0xffff && *(const uint16_t*)(m + 4) == reg && (m[7] & 0x40) && ko_mdate(m) >= from)
      return 1;
  }
  return 0;
}

static void aug_scup_fill_days(void)
{
  int d = today();
  if (!g_naug_scup || d < 182 || d >= 220) return;

  for (int i = 0; i < g_naug_scup; i++) {
    const cal_scup_t* cs = &g_aug_scup[i];
    unsigned char* rec = get_rec(cs->reg);
    if (!rec) continue;

    /* last season's finish and cup winner, as kept at the July teardown (aug_scup_keep) */
    int ad = abs_day();
    final_t* f = final_of(cs->league);
    int fk = f && f->n >= 2 && ad >= f->day && ad - f->day < 60;
    cupwin_t* w = cs->cup ? cupwin_of(cs->cup) : 0;
    int wk = w && ad >= w->day && ad - w->day < 60;
    uint32_t champion = fk ? f->club[0] : calendar_scup_right(cs->league, 13);
    uint32_t runner   = fk ? f->club[1] : calendar_scup_right(cs->league, 14);
    uint32_t cupwin   = !cs->cup ? 0 : wk ? w->club : calendar_scup_right(cs->cup, 0);
    if (!champion || (cs->cup && !cupwin)) {
      static int said_season[MAX_CAL_SCUPS];
      if (said_season[i] != log_season() + 1) {
        said_season[i] = log_season() + 1;
        logf("fl26swiss: August-May Super Cup %u -- day %d: no %s yet (league %u%s, cup %u%s)", (unsigned)cs->reg, d,
               champion ? "cup winner" : "league champion", (unsigned)cs->league, fk ? " kept" : "",
               (unsigned)cs->cup, wk ? " kept" : "");
      }
      continue;
    }

    int by_runner = !cs->cup || (champion >> 14) == (cupwin >> 14);
    uint32_t opponent = by_runner ? runner : cupwin;
    if (!opponent || (opponent >> 14) == (champion >> 14)) continue;

    uint32_t clubs[2] = { champion, opponent };
    if (rec_count(rec) == 2 && has_club(rec_clubs(rec), 2, champion) && has_club(rec_clubs(rec), 2, opponent)
        && ccup_unplayed(cs->reg) > 0)
      continue;
    /* B283: dated before its league's first round, the super cup can be played inside these days
       (the shipped date, mid-August, was past them): played since day 182, it is done -- filled
       again it was played twice (run of 29.10.: 283 played on day 204, registered again on 205) */
    int gd = game_date();
    if (gd >= 0 && ccup_played_since(cs->reg, gd - (d - 182))) {
      static int said_done[MAX_CAL_SCUPS];
      if (said_done[i] != log_season() + 1) {
        said_done[i] = log_season() + 1;
        logf("fl26swiss: August-May Super Cup %u -- day %d: played this summer, done for the season", (unsigned)cs->reg, d);
      }
      continue;
    }

    ((freetab_fn)(uintptr_t)(g_base + FREETAB_RVA))(0, cs->reg);
    u32vec v = { clubs, clubs + 2, clubs + 2 };
    ((setclr_fn)(uintptr_t)g_tramp_setcl)(cs->reg, &v, 1);
    run_flush();

    if (rec_count(rec) != 2) {
      logf("fl26swiss: August-May Super Cup %u -- day %d: set_clubs left %u club(s)",
           (unsigned)cs->reg, d, (unsigned)rec_count(rec));
      continue;
    }
    *(uint32_t*)(rec + 0x304) |= 1u << 8;    /* in this season: the door asks for it */

    start_stage(0, cs->reg);

    uint16_t id = cs->reg;
    struct { uint16_t* b; uint16_t* e; uint16_t* c; } rv = { &id, &id + 1, &id + 1 };
    ((regall_fn)(uintptr_t)(g_base + REGALL_RVA))(0, &rv);
    run_flush();

    logf("fl26swiss: August-May Super Cup %u -- day %d: league %u champion %u v %s %u; registered, %d match record(s), %d unplayed",
         (unsigned)cs->reg, d, (unsigned)cs->league, champion >> 14,
         by_runner ? "league runner-up" : "cup winner", opponent >> 14,
         ccup_matches(cs->reg), ccup_unplayed(cs->reg));
  }
}

/* B470 (FL Testovi, GigaPack beta 3, season 2, 17.11.): the UEFA Super Cup (reg 7, the game's,
 * dated day 222) was never played after the first summer. The July teardown emptied it (2 -> 0 on
 * day 181) and nothing of the game's filled it again up to October: its setup (0x14135e8f0 ->
 * 0x141364110 -> 0x1413604a0) gave up before set_clubs, behind a check of the season's entry
 * vector that is VM-protected (0x141354020) -- which condition fails is not known yet; the
 * superguard's counters say whether it is the Champions or the Europa League entry. So when the
 * game has not filled it by day UEFA_SCUP_FROM, last season's Champions League winner (reg 4) and
 * Europa League winner (reg 6), both kept at the teardown (access_capture, day 176), are put in
 * and registered as the August-May super cups of ours are (aug_scup_fill_days). Never when it is
 * filled already with a match to play, never once it has been played this summer, never with one
 * of the two missing or both the same club. Every fill is logged, the reason it is left alone
 * once a season. */
#define UEFA_SCUP_REG  7
#define UEFA_SCUP_FROM 205          /* 24 July: three weeks for the game's own setup after the roll */
#define UEFA_SCUP_TO   221          /* the day before its shipped date (222) */
enum { USC_OUT = 0, USC_FILL = 1, USC_HAVE = -1, USC_PLAYED = -2, USC_NO_UCL = -3, USC_NO_UEL = -4,
       USC_SAME = -5 };
static int uefa_scup_decide(int d, int have_pair_unplayed, int played_since, uint32_t ucl, uint32_t uel)
{
  if (d < UEFA_SCUP_FROM || d > UEFA_SCUP_TO) return USC_OUT;
  if (have_pair_unplayed) return USC_HAVE;
  if (played_since) return USC_PLAYED;
  if (!(ucl >> 14)) return USC_NO_UCL;
  if (!(uel >> 14)) return USC_NO_UEL;
  if ((ucl >> 14) == (uel >> 14)) return USC_SAME;
  return USC_FILL;
}
static const char* uefa_scup_why(int r)
{
  switch (r) {
    case USC_HAVE:   return "the game filled it, its match is to be played";
    case USC_PLAYED: return "played this summer, done for the season";
    case USC_NO_UCL: return "no Champions League winner kept (reg 4)";
    case USC_NO_UEL: return "no Europa League winner kept (reg 6)";
    case USC_SAME:   return "the same club won both";
  }
  return "";
}
static void uefa_scup_fill_days(void)
{
  int d = today();
  if (d < UEFA_SCUP_FROM || d > UEFA_SCUP_TO) return;
  unsigned char* rec = get_rec(UEFA_SCUP_REG);
  if (!rec) return;
  /* asked every day of the window (a save of an earlier day can be loaded in the same session);
     the reason it is left alone is logged once a season and timeline */
  static int said = -1000, said_tl = -1;
  int season = log_season();
  if (said_tl != g_timeline) { said_tl = g_timeline; said = -1000; }
  uint32_t ucl = cup_winner(R_UCLKO), uel = cup_winner(R_UELKO);
  int n0 = (int)rec_count(rec);
  int have = n0 == 2 && ccup_unplayed(UEFA_SCUP_REG) > 0;        /* its pair, the game's or ours */
  int gd = game_date();
  int played = gd >= 0 && ccup_played_since(UEFA_SCUP_REG, gd - (d - 182));
  int r = uefa_scup_decide(d, have, played, ucl, uel);
  if (r != USC_FILL) {
    if (said != season) {
      said = season;
      logf("fl26swiss: UEFA Super Cup %u -- day %d: left alone, %s (%u club(s), UCL %08x, UEL %08x)",
           (unsigned)UEFA_SCUP_REG, d, uefa_scup_why(r), (unsigned)n0, ucl, uel);
    }
    return;
  }
  uint32_t clubs[2] = { ucl, uel };
  ((freetab_fn)(uintptr_t)(g_base + FREETAB_RVA))(0, UEFA_SCUP_REG);
  u32vec v = { clubs, clubs + 2, clubs + 2 };
  ((setclr_fn)(uintptr_t)g_tramp_setcl)(UEFA_SCUP_REG, &v, 1);
  run_flush();
  if (rec_count(rec) != 2) {
    logf("fl26swiss: UEFA Super Cup %u -- day %d: set_clubs left %u club(s); not registered",
         (unsigned)UEFA_SCUP_REG, d, (unsigned)rec_count(rec));
    return;
  }
  *(uint32_t*)(rec + 0x304) |= 1u << 8;      /* in this season: the door asks for it */
  start_stage(0, UEFA_SCUP_REG);
  uint16_t id = UEFA_SCUP_REG;
  struct { uint16_t* b; uint16_t* e; uint16_t* c; } rv = { &id, &id + 1, &id + 1 };
  ((regall_fn)(uintptr_t)(g_base + REGALL_RVA))(0, &rv);
  run_flush();
  said = season;
  logf("fl26swiss: UEFA Super Cup %u -- day %d: the game left it with %d club(s) after the roll; "
       "Champions League winner %u v Europa League winner %u; registered, %d match record(s), %d unplayed",
       (unsigned)UEFA_SCUP_REG, d, n0, ucl >> 14, uel >> 14, ccup_matches(UEFA_SCUP_REG),
       ccup_unplayed(UEFA_SCUP_REG));
}

/* B258c: a career built on 1 January has its leagues of ours with no match yet. Their rounds are
 * dated (reg 11, Liga AUF: "real calendar ... days 52..341" on day 0), but they only enter the
 * season through register_all, and the game's first register_all of the year is on day 1 (the
 * season start of its own 276; fl26join appends ours to it). Until then the hub of the new
 * career had the cup and three Brasileirao matches on its strip and an empty table (antonimus,
 * 27.10.: 0 match records of 11 on day 0, 240 on day 1). The same call is made here on day 0,
 * with nothing of the game's in it: fl26join appends ours by its own rules, as on day 1, and on
 * day 1 they are already in a season and left alone. Only on the day the career was built (or a
 * save of that day loaded), never on a later New Year. */
static void join_on_day0(void)
{
  if (today() != 0 || !g_new_career || g_built_gdate < 0 || g_built_gdate != game_date()) return;
  int before = ccup_matches(0xffff);
  uint16_t none = 0;
  struct { uint16_t* b; uint16_t* e; uint16_t* c; } rv = { &none, &none, &none + 1 };
  ((regall_fn)(uintptr_t)(g_base + REGALL_RVA))(0, &rv);
  run_flush();
  logf("fl26swiss: the leagues of ours registered on day 0, not on day 1 (B258c): %d match record(s) before, %d after",
       before, ccup_matches(0xffff));
}

/* The season end's own memory (see ccup_keep_national_winner): mp32 (08.11.2026) showed the
 * progression of a split group or a national cup is not where the game ends them -- nothing was
 * kept. So every day the game stops on between late May and mid-July, before its own day (which
 * may build the new season's schedule over the old one), one walk over the match table counts
 * each regulation's records and played ones; a split group or a national knockout cup with all
 * of them played gets its final table / its winner kept, once a season. */
/* 08.11. (mp37/mp38): the game has no table for a split's group -- 0 rows from the table call while
   it is played and after, under the group's id; the total's table is its club list. The matches are
   there to the last round, the regular phase's too, until a few days after the phase ends. So a
   group's final table is counted from them once its last match is played: its clubs (the group's
   record), the regular phase's matches and the group's (only the group's for a split without a
   points carry), three points a win, one a draw, then goal difference, then goals scored. A
   halving carry (key 8, Austria) is not halved here: the order of the sums, not of half of them. */
static int group_table(uint16_t reg, final_t* out, int* played_out, int* top, int* last)
{
  const split_t* sp;
  static split_t own;
  *played_out = 0;
  if (split_part(reg, &sp) != 3) {
    const gsplit_t* g = gsplit_group(reg);          /* B425: a group of the game's own split season */
    if (!g) return 0;
    own.total = g->total; own.regular = g->regular; own.group[0] = g->group[0]; own.group[1] = g->group[1]; own.group[2] = 0;
    sp = &own;
  }
  unsigned char* gr = get_rec(reg);
  uint32_t n = gr ? rec_count(gr) : 0;
  if (n < 2 || n > FINAL_MAX) return 0;
  const unsigned char* bs = (const unsigned char*)(g_base + MATCH_BASE_SITE);
  const unsigned char* cs = (const unsigned char*)(g_base + MATCH_CAP_SITE);
  if (bs[0] != 0x48 || bs[1] != 0x8d || bs[2] != 0x88 || cs[0] != 0x81 || cs[1] != 0xff) return 0;
  uint32_t base = *(const uint32_t*)(bs + 3), cap = *(const uint32_t*)(cs + 2);
  unsigned char* o = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
  unsigned char* blk = o ? *(unsigned char**)(o + 0x48) : 0;
  if (!blk || !cap || cap > 200000) return 0;
  uint16_t regular = nocarry(sp->total) ? 0 : sp->regular;
  uint32_t club[FINAL_MAX]; int pts[FINAL_MAX], gd[FINAL_MAX], gf[FINAL_MAX], played = 0;
  for (uint32_t k = 0; k < n; k++) { club[k] = canon_club(rec_clubs(gr)[k]); pts[k] = gd[k] = gf[k] = 0; }
  for (uint32_t i = 0; i < cap; i++) {
    const unsigned char* m = blk + base + (size_t)i * MATCH_STRIDE;
    if (*(const uint16_t*)m == 0xffff || !(m[7] & 0x40)) continue;
    uint16_t mr = *(const uint16_t*)(m + 4);
    if (mr != reg && (!regular || mr != regular)) continue;
    uint32_t side[2] = { *(const uint32_t*)(m + 0x14), *(const uint32_t*)(m + 0x18) };
    int goals[2] = { m[0x1c], m[0x1f] };
    for (int j = 0; j < 2; j++) {
      uint32_t k = 0;
      while (k < n && !same_club(club[k], side[j])) k++;
      if (k == n) continue;                     /* a regular-phase club of the other group */
      int me = goals[j], them = goals[1 - j];
      pts[k] += me > them ? 3 : me == them ? 1 : 0;
      gd[k] += me - them; gf[k] += me;
    }
    if (mr == reg) played++;
  }
  *played_out = played;
  if (!played) return 0;
  for (uint32_t a = 1; a < n; a++)               /* insertion sort, stable: points, difference, scored */
    for (uint32_t b = a; b > 0; b--) {
      uint32_t x = b - 1, y = b;
      if (pts[y] < pts[x] || (pts[y] == pts[x] && (gd[y] < gd[x] || (gd[y] == gd[x] && gf[y] <= gf[x])))) break;
      uint32_t c = club[x]; club[x] = club[y]; club[y] = c;
      int t = pts[x]; pts[x] = pts[y]; pts[y] = t;
      t = gd[x]; gd[x] = gd[y]; gd[y] = t;
      t = gf[x]; gf[x] = gf[y]; gf[y] = t;
    }
  out->n = (uint16_t)n;
  for (uint32_t k = 0; k < n; k++) out->club[k] = club[k];
  *top = pts[0]; *last = pts[n - 1];
  return regular ? 2 : 1;
}
static int keep_group_final(uint16_t reg, int ad)
{
  final_t* f = final_of(reg);
  if (f && ad >= f->day && ad - f->day < 60) return 0;
  static final_t t;
  int played, top, last, how = group_table(reg, &t, &played, &top, &last);
  if (!how) return 0;
  if (!f) { if (!(f = final_new(reg))) return 0; f->reg = reg; }
  f->n = t.n; f->day = ad;
  for (uint32_t k = 0; k < t.n; k++) f->club[k] = t.club[k];
  logf("fl26swiss: reg %u -- group table from %d match(es)%s: %d pts on top, %d last",
       (unsigned)reg, played, how == 2 ? " and the regular phase's" : "", top, last);
  return (int)t.n;
}
/* B425: the game does not always ask for the progression of its own split groups; every day it
   stops on, a split season of its own that a national cup takes a place from is looked at, and the
   day both groups are played out the cup is filled as on its leagues' last progression */
static void gsplit_day(void)
{
  int year = lpre_year();
  for (int i = 0; i < g_ngsplit; i++) {
    const gsplit_t* g = gsplit_live(&g_gsplit[i]);
    if (!g || g->regular >= 1024 || g_lg_over[g->regular] == year + 1) continue;
    int named = 0;
    for (int k = 0; k < g_nccup && !named; k++) {
      const ccup_t* c = &g_ccup[k];
      if (!c->fill || c->groups || !c->national) continue;
      for (unsigned e = 0; e < c->n; e++) if (c->ereg[e] == g->regular) named = 1;
    }
    if (named && gsplit_keep(g)) ccup_fill_leagues_over(g->regular, 0);
  }
}
static void season_end_keep(int after)
{
  /* 08.11. (mp35): a split's groups play their last round on the day their phase ends (day 142)
     and their records are gone before 25 May -- a group is looked at every day from March, before
     the game's day and after it; the cups, which end later, from 25 May */
  static int done_day[2] = { -1, -1 };
  int d = today(), ad = abs_day();
  if (d < 1 || ad == done_day[after]) return;
  if (d < 60 || d > 200) return;                         /* 1 March .. 18 July */
  done_day[after] = ad;
  gsplit_day();
  int cups = d >= 145;                                   /* 25 May .. */
  const unsigned char* bs = (const unsigned char*)(g_base + MATCH_BASE_SITE);
  const unsigned char* cs = (const unsigned char*)(g_base + MATCH_CAP_SITE);
  if (bs[0] != 0x48 || bs[1] != 0x8d || bs[2] != 0x88 || cs[0] != 0x81 || cs[1] != 0xff) return;
  uint32_t base = *(const uint32_t*)(bs + 3), cap = *(const uint32_t*)(cs + 2);
  unsigned char* o = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
  unsigned char* blk = o ? *(unsigned char**)(o + 0x48) : 0;
  if (!blk || !cap || cap > 200000) return;
  static uint16_t all[4096], played[4096];
  static unsigned char want[4096];
  memset(want, 0, sizeof want);
  int any = 0;
  for (int i = 0; i < g_nsplits; i++)
    for (int g = 0; g < 3; g++) if (SPLITS[i].group[g] && SPLITS[i].group[g] < 4096) { want[SPLITS[i].group[g]] = 1; any = 1; }
  for (int k = 0; k < g_nccup; k++)
    if (cups && g_ccup[k].national && !g_ccup[k].groups && g_ccup[k].ko < 4096) { want[g_ccup[k].ko] = 2; any = 1; }
  if (!any) return;
  memset(all, 0, sizeof all); memset(played, 0, sizeof played);
  for (uint32_t i = 0; i < cap; i++) {
    const unsigned char* m = blk + base + (size_t)i * MATCH_STRIDE;
    if (*(const uint16_t*)m == 0xffff) continue;
    uint16_t r = *(const uint16_t*)(m + 4);
    if (r >= 4096 || !want[r]) continue;
    if (all[r] < 0xffff) all[r]++;
    if ((m[7] & 0x40) && played[r] < 0xffff) played[r]++;
  }
  for (int r = 1; r < 4096; r++) {
    if (!want[r] || !all[r] || played[r] != all[r]) continue;
    if (want[r] == 1) {
      int n = keep_group_final((uint16_t)r, ad);
      if (n > 0)
        logf("fl26swiss: reg %d -- split group's final table kept for the season end (day %d, %d clubs): %08x first, %08x last",
             r, d, n, final_of((uint16_t)r)->club[0], final_of((uint16_t)r)->club[n - 1]);
    } else {
      cupwin_t* cw = cupwin_of((uint16_t)r);
      if (cw && ad >= cw->day && ad - cw->day < 60) continue;
      ccup_keep_national_winner((uint16_t)r);
    }
  }
}

/* B470b (FL Testovi, beta4q (B) on beta4r, 18.11.): the Europa League knockout (reg 6) kept last
 * season's clubs after the July roll -- its participants page on 12.08. listed 59 clubs, AS Roma
 * (last season's winner) among them -- and the teardown fix of B470 (uel_ko_close_ids) never ran:
 * reg 6 IS on the game's July list. The exe's event table (0x1426d2490, 251 rows) gives every UEFA
 * regulation the same region key, so 2..7 and their rows are handed over together (the list had
 * 1027 and 1029). The entries are emptied elsewhere: the season close 0x141365c50 keeps only the
 * ids whose period (+0x30c bits 7-12, 0x1415415f0) is the one that ends, then for each one not of
 * format 1/6/11 frees its tie tables (0x141363040) and empties its entries (0x141363170: every
 * entry, count 0 -- "count set 24 -> 0 by 1413631eb" for reg 4, 36 -> 0 for 5, 2 -> 0 for 7).
 * Reg 6 got no such line from the load to 12.08.: the game passes it over there.
 *
 * So after the game's day, from 1 July (day 181) to late November -- before any knockout has
 * clubs of the new season, its first match is in February -- a reg 6 that still holds clubs while
 * the Champions League knockout (4) has been emptied by the same close is emptied the same way:
 * its tie tables and its entries, the game's own two steps for reg 4. Its winner is kept first
 * (g_cupwin), for the UEFA Super Cup of day 205 (uefa_scup_fill_days). FL27 only (g_native_uefa):
 * measured there. Pure, for the native test. */
#define UEL_KO_STALE_FROM 181
#define UEL_KO_STALE_TO   330
static int uel_ko_stale(int native, int doy, int has4, unsigned n4, int has6, unsigned n6)
{
  return native && doy >= UEL_KO_STALE_FROM && doy <= UEL_KO_STALE_TO && has4 && n4 == 0 && has6 && n6 > 0;
}
#define ENTRYCLR_RVA 0x1363170   /* (this, u16 id): empty a regulation's entries -- the season close's own step */
static void uel_ko_reset_days(void)
{
  unsigned char* r4 = get_rec(R_UCLKO);
  unsigned char* r6 = get_rec(R_UELKO);
  unsigned n6 = r6 ? rec_count(r6) : 0;
  if (!uel_ko_stale(g_native_uefa, today(), r4 != 0, r4 ? rec_count(r4) : 0, r6 != 0, n6)) return;
  uint32_t w = winner_now(R_UELKO);
  int ad = abs_day();
  cupwin_t* cw = cupwin_of(R_UELKO);
  if (w && !(cw && ad >= cw->day && ad - cw->day < 120)) {
    if (!cw && g_ncupwin < CUPWIN_N) { cw = &g_cupwin[g_ncupwin++]; cw->reg = R_UELKO; }
    if (cw) { cw->day = ad; cw->club = w; }
  }
  ((freetab_fn)(uintptr_t)(g_base + FREETAB_RVA))(0, R_UELKO);
  ((freetab_fn)(uintptr_t)(g_base + ENTRYCLR_RVA))(0, R_UELKO);
  run_flush();
  unsigned char* r5 = get_rec(5);
  logf("fl26swiss: July -- Europa League knockout %u: the season close left last season's %u club(s) in it "
       "(Champions League knockout %u is empty); emptied, now %u; its winner %08x kept for the Super Cup; "
       "the Europa League entry 5 has %u club(s)",
       (unsigned)R_UELKO, n6, (unsigned)R_UCLKO, r6 ? rec_count(r6) : 0u, cw ? cw->club : w, r5 ? rec_count(r5) : 0u);
  state_store();
}

char daychk_handler(void* ctx)
{
  table_pool_old_slots("day");        /* B211: before the game's day, which may draw a cup's groups */
  /* 07.11.: the loader's tick (fl26_swiss_ko_tick) comes every few dozen file opens, and under Fast
     Forward a whole week can pass without one -- the slots stayed stale from the draw to the match.
     Every day, before the game's own day, as well. */
  ko_heal_played("day");
  ko_sync_all("day");
  season_end_keep(0);
  char r = ((daychk_fn)(uintptr_t)g_tramp_daychk)(ctx);
  season_end_keep(1);
  if (g_td_fresh) { g_td_fresh = 0; ccup_fill_ahead(0, "the July teardown", 0); }
  uel_ko_reset_days();                             /* B470b: reg 6 after the season close */
  static int last = -1, seen, tl = 0;
  int d = abs_day();
  if (tl != g_timeline) { tl = g_timeline; seen = 0; last = -1; }
  g_day_ticked = 1;
  /* B258: the hub's "Next" strip is the user's day schedule, and a schedule is only ever as good
   * as the day it was filed: antonimus (Cerro Largo, Liga AUF) had Brasileirao matches on it from
   * the start of his career to the first league round, Agus a Copa Argentina match of two other
   * clubs, and our own 83a1232 test the same result twice after a save was loaded. None of it
   * repeats in a fresh career here, but the cure is the same whatever wrote the stale entries:
   * the game's rebuild files every match of the user's from the match records and clears the
   * rest. Measured 27.10.: copies of a played match planted on three and on four days, and another club's
   * match of the same league planted on a past day, were all gone the day after a rebuild;
   * another club's match planted with no rebuild asked stayed in the schedule for two days. Until now
   * a rebuild was asked only when one of our cups had drawn or was under way, which is not the
   * case from a January start to the first round. So the first day of every timeline -- a
   * career built or a save loaded in this session -- asks for one too. */
  if (last < 0) {
    g_sched_now_tl = g_timeline; g_sched_now_day = d;      /* B258c: done this day (sched_rebuild) */
    join_on_day0();
    sched_rebuild("the first day after a load or a new career (B258)");
  }
  if (d != last) {
    if (seen++ < 3) logf("fl26swiss: day loop on day %d", today());
    else if (last >= 0 && d > last + 1) logf("fl26swiss: day loop skipped day(s) %d..%d", last + 1, d - 1);
    last = d;
  }
  apclau_keep();
  ssum_keep(0);
  lpre_fill_days();
  ccup_fill_days();
  calendar_scup_fill_days();
  aug_scup_fill_days();
  uefa_scup_fill_days();                           /* B470: reg 7 when the game left it empty */
  q1_keep();                                      /* FL27: July's first round, before August's fills */
  for (int p = NQR - 1; p >= 0; p--) q_fill(p);
  cal_dedupe();
  sched_days();
  if (g_new_career && !g_built_stored && g_built_gdate >= 0) {    /* B209: once, a club known */
    any_final_kept();                              /* a save of a later summer: not new (state_sync) */
    if (g_st_read_back) g_built_stored = 1; else state_store();
  }
  return r;
}

/* ---- the July teardown for the Conference League ----
 *
 * At every rollover 0x141314350(ctx, vector<u16>* ids) closes the competitions whose season
 * ends that day: it finalises the table, deletes the match records, frees the tie tables and
 * puts +0x2fc back to 0xffff.  The list comes from the exe's own event table, which has never
 * heard of 186 and 187, so after the first season they kept last season's 36 clubs, year 2025
 * and their tables -- uecl_fill found 1210 full and did nothing, and enter_season (fl26join)
 * refuses anything whose +0x2fc is not 0xffff.  They are appended to the European list
 * (recognised by shipped id 2, as fl26join does for its own ids).  fl26join hooks the same
 * function and is loaded first, so this one sits in front of it. */
#define TEARDOWN_RVA 0x1314350
static const unsigned char SIG_TEARDOWN[14] = {
  0x48,0x89,0x54,0x24,0x10, 0x55, 0x56, 0x57, 0x41,0x54, 0x41,0x55, 0x41,0x56 };
typedef struct { uint16_t* b; uint16_t* e; uint16_t* c; } vec16_t;
unsigned char* g_tramp_teardown = 0;
#define TD_MAX 4096         /* 512 until the limits branch: the game's list + ~256 cups of ours and their rows */
static uint16_t g_td_list[TD_MAX];
static vec16_t  g_td_vec;
/* B234: the leagues and cups the August-May super cups of ours are filled from, kept at the July
 * teardown as the continental cups' sources are -- after it the game names nobody: run 5 of
 * 2026-10-26 found no champion for any of the six on days 182..219 */
static void aug_scup_keep(void)
{
  int d = today(), ad = abs_day();
  if (!g_naug_scup || d < 140 || d > 230) return;
  for (int i = 0; i < g_naug_scup; i++) {
    const cal_scup_t* cs = &g_aug_scup[i];
    int r = keep_final(cs->league, d, ad);
    if (r > 0) logf("fl26swiss: reg %u -- final table kept for Super Cup %u (day %d)", (unsigned)cs->league,
                    (unsigned)cs->reg, d);
    if (!cs->cup) continue;
    cupwin_t* w = cupwin_of(cs->cup);
    if (w && ad >= w->day && ad - w->day < 60) continue;
    uint32_t c = winner_now(cs->cup);
    if (!c) continue;
    if (!w) { if (g_ncupwin >= CUPWIN_N) continue; w = &g_cupwin[g_ncupwin++]; w->reg = cs->cup; }
    w->day = ad; w->club = c;
    logf("fl26swiss: cup reg %u won by %08x (day %d), kept for Super Cup %u", (unsigned)cs->cup, c, d,
         (unsigned)cs->reg);
  }
}

/* B470 (FL Testovi, season 2 of GigaPack beta 3, 17.11.): the Europa League knockout (reg 6) was
 * not on the game's July list. Regs 4 and 5 went 24 -> 0 and 36 -> 0 on day 181, reg 6 kept last
 * season's 24 clubs, and its participants page showed them next to the new league phase (57
 * clubs, Roma twice). Its winner is kept before this (access_capture) for the Super Cup. Whatever
 * of the Champions League knockout the game closes (4 and any row or tie of it, id & 0x3ff == 4)
 * the Europa League's is closed with it: the same id with 6, when it has a record and the list
 * does not already name it. Nothing when the list does not close 4. Pure, for the native test.
 * B470b (18.11.): in FL27 this never adds anything -- 6 is on the list (one region for 2..7 in the
 * event table); what kept its clubs is the season close, see uel_ko_reset_days. Kept for a list
 * that does lack it. */
#define UEL_KO_CLOSE_MAX 64
static int uel_ko_close_ids(const uint16_t* game, int n, int (*live)(uint16_t), uint16_t* out, int max)
{
  int k = 0;
  for (int j = 0; j < n && k < max; j++) {
    if ((game[j] & 0x3ff) != R_UCLKO) continue;
    uint16_t id = (uint16_t)((game[j] & ~0x3ff) | R_UELKO);
    int there = 0;
    for (int i = 0; i < n && !there; i++) if (game[i] == id) there = 1;
    for (int i = 0; i < k && !there; i++) if (out[i] == id) there = 1;
    if (!there && live(id)) out[k++] = id;
  }
  return k;
}
static int rec_live(uint16_t id) { return get_rec(id) != 0; }
static int uel_ko_teardown_wanted(const uint16_t* game, int n)
{
  uint16_t ids[UEL_KO_CLOSE_MAX];
  return uel_ko_close_ids(game, n, rec_live, ids, UEL_KO_CLOSE_MAX);
}
/* appends them to list[0..*k) (not twice); the number added */
static int uel_ko_teardown_add(uint16_t* list, int* k, int max, const uint16_t* game, int n)
{
  uint16_t ids[UEL_KO_CLOSE_MAX];
  int m = uel_ko_close_ids(game, n, rec_live, ids, UEL_KO_CLOSE_MAX), added = 0;
  for (int i = 0; i < m && *k < max; i++) {
    int there = 0;
    for (int j = 0; j < *k && !there; j++) if (list[j] == ids[i]) there = 1;
    if (!there) { list[(*k)++] = ids[i]; added++; }
  }
  return added;
}

vec16_t* teardown_pre(uint64_t ctx, vec16_t* in)
{
  (void)ctx;
  if (!in || !in->b || in->e < in->b) return in;
  int n = (int)(in->e - in->b), euro = 0, has186 = 0, has187 = 0, has1210 = 0, has1027 = 0, has1029 = 0;
  if (n + 24 > TD_MAX) return in;
  ssum_keep(1);                       /* before the tables of the halves go */
  champ_note("a teardown");
  access_capture();
  ccup_keep_tables(in->b, n);
  table_pool_reap("July teardown");
  ccup_keep_winners(0);
  ccup_keep_winners(1);
  aug_scup_keep();
  state_store();
  int bra = 0, libq = 0;
  for (int j = 0; j < n; j++) {
    uint16_t id = in->b[j];
    if (id == 2) euro = 1;
    if (id == CONM_LIBQ_REG) libq = 1;
    if (id == UECL_REG) has186 = 1;
    if (id == UECL_KO) has187 = 1;
    if (id == UECL_ROW) has1210 = 1;
    if (id == 1027) has1027 = 1;
    if (id == 1029) has1029 = 1;
    if (id == 29) bra = 1;
  }
  int uel6 = uel_ko_teardown_wanted(in->b, n);
  int ncal = 0;
  for (int c = 0; c < g_nccup; c++) if (g_ccup[c].cal && ccup_world(&g_ccup[c])) ncal++;
  /* A national cup or super cup of ours (a `dates` line, id 176 and up) is closed with the
   * shipped cup it is dated as.  No event table names it, so it kept its old matches and its
   * goals, assists, titles and Team of the Tournament into the next season (GitHub #77). */
  uint16_t dcl[MAX_DATELIKE]; int ndcl = 0;
  for (int i = 0; i < g_ndlike; i++) {
    uint16_t id = g_dlike[i][0]; int like = 0, there = 0;
    uint16_t close_like = g_dlike[i][1];
    if (date_shift_for(id) || date_days_for(id))
      close_like = g_dlike[i][1] == CALENDAR_SUPER_TEARDOWN_LIKE
                 ? CALENDAR_SUPER_TEARDOWN_LIKE : CALENDAR_CUP_TEARDOWN_LIKE;
    if (id < 176 || !get_rec(id)) continue;
    for (int j = 0; j < n; j++) { if (in->b[j] == close_like) like = 1; if (in->b[j] == id) there = 1; }
    if (like && !there && n + ndcl < TD_MAX) dcl[ndcl++] = id;
  }
  /* B275 (antonimus 29.10.): the Libertadores' qualifying phases 1 and 2 (pre-rounds aliased
     to it) close with its phase 3, the game's reg 8 -- in January, not with the July teardown,
     which took their matches and left the Competition Info page phase 3 alone from July */
  int nal = 0;
  for (int i = 0; i < g_nlpre; i++) if (g_lpre[i].alias && !lpre_cal(&g_lpre[i])) nal++;
  if (!euro) {
    int cal = bra && ncal, qal = nal && (libq || cal);
    if (!cal && !ndcl && !qal) return in;
    memcpy(g_td_list, in->b, (size_t)n * sizeof(uint16_t));
    int k = n, added = 0;
    for (int c = 0; cal && c < g_nccup; c++) {
      const ccup_t* cc = &g_ccup[c];
      if (!cc->cal || !ccup_world(cc)) continue;
      for (int g = -2; g < cc->groups; g++) {
        uint16_t id = g == -2 ? cc->ko : g == -1 ? cc->reg : ccup_rep(cc, g);
        int there = 0;
        for (int j = 0; j < k; j++) if (g_td_list[j] == id) there = 1;
        if (!there && get_rec(id) && k < TD_MAX) { g_td_list[k++] = id; added++; }
      }
    }
    for (int i = 0; cal && i < g_nlpre; i++) {
      if (!lpre_cal(&g_lpre[i])) continue;
      for (int g = -1; g < lpre_rows(&g_lpre[i]); g++) {
        uint16_t id = g < 0 ? g_lpre[i].reg : lpre_tie(&g_lpre[i], g);
        int there = 0;
        for (int j = 0; j < k; j++) if (g_td_list[j] == id) there = 1;
        if (!there && get_rec(id) && k < TD_MAX) { g_td_list[k++] = id; added++; }
      }
    }
    if (cal) logf("fl26swiss: calendar-year teardown on day %d -- %d regulation(s) of %d South American cup(s) added",
                  today(), added, ncal);
    int qadded = 0;
    for (int i = 0; qal && i < g_nlpre; i++) {
      if (!g_lpre[i].alias || lpre_cal(&g_lpre[i])) continue;
      for (int g = -1; g < lpre_rows(&g_lpre[i]); g++) {
        uint16_t id = g < 0 ? g_lpre[i].reg : lpre_tie(&g_lpre[i], g);
        int there = 0;
        for (int j = 0; j < k; j++) if (g_td_list[j] == id) there = 1;
        if (!there && get_rec(id) && k < TD_MAX) { g_td_list[k++] = id; qadded++; }
      }
    }
    if (qal) logf("fl26swiss: teardown on day %d -- Libertadores qualifying phases 1/2: %d regulation(s) added (phase 3 %s on the list)",
                  today(), qadded, libq ? "is" : "is NOT");
    for (int i = 0; i < ndcl && k < TD_MAX; i++) g_td_list[k++] = dcl[i];
    if (ndcl) logf("fl26swiss: teardown on day %d -- %d cup(s) of ours closed with the cup they are dated as", today(), ndcl);
    g_td_vec.b = g_td_list; g_td_vec.e = g_td_list + k; g_td_vec.c = g_td_list + TD_MAX;
    return &g_td_vec;
  }
  g_td_fresh = 1;
  g_td_abs = abs_day();                    /* a first qualifying round is filled from today (q_fill_from) */
  logf("fl26swiss: July teardown on day %d (%d ids)", today(), n);
  int uecl = get_rec(UECL_REG) && !(has186 && has187 && has1210);
  int cwc = cwc_world(), nccw = 0;
  for (int c = 0; c < g_nccup; c++) if (ccup_world(&g_ccup[c])) nccw++;
  /* A world built without the Conference League still has the Europa League play-off (188,
     tools/leaguebuilder.py since issue #33); with nothing else to add this returned here and
     left 188 and its ties out of the teardown, to outlive the season. */
  int pos = get_rec(CUPS[1].po) || get_rec(CUPS[2].po);
  for (int i = 1; i < NQR; i++) if (g_qreg[i] && get_rec(g_qreg[i])) pos = 1;   /* 1, 2: Prijedlog C's play-offs */
  if (!uecl && !cwc && !nccw && !pos && !ndcl && !uel6) return in;
  /* The list names every regulation it closes -- group rows are not reached through their
   * parent -- so the league phase's row goes in as well, or its 36 clubs, its tables and its
   * 144 matches outlive the season. */
  memcpy(g_td_list, in->b, (size_t)n * sizeof(uint16_t));
  int k = n;
  if (uecl) {
    if (!has186) g_td_list[k++] = UECL_REG;
    if (!has187 && get_rec(UECL_KO)) g_td_list[k++] = UECL_KO;
    if (!has1210 && get_rec(UECL_ROW)) g_td_list[k++] = UECL_ROW;
  }
  /* the Club World Cup: its knockout (an id the exe does not know) and the eight group rows */
  if (cwc) {
    int ncwc = 0;
    for (int g = -2; g < CWC_GROUPS; g++) {
      uint16_t id = g == -2 ? CWC_KO : g == -1 ? CWC_REG : cwc_rep(g);
      int there = 0;
      for (int j = 0; j < k; j++) if (g_td_list[j] == id) there = 1;
      if (!there && get_rec(id) && k < TD_MAX) { g_td_list[k++] = id; ncwc++; }
    }
    if (g_ic_reg && ic_world()) {
      int there = 0;
      for (int j = 0; j < k; j++) if (g_td_list[j] == g_ic_reg) there = 1;
      if (!there && k < 512) { g_td_list[k++] = g_ic_reg; ncwc++; }
    }
    logf("fl26swiss: July teardown -- %d Club World Cup regulation(s) added", ncwc);
  }
  /* the world file's continental cups: master, knockout and group rows */
  for (int c = 0; c < g_nccup; c++) {
    const ccup_t* cc = &g_ccup[c];
    if (!ccup_world(cc)) continue;
    if (cc->cal) {
      logf("fl26swiss: July teardown -- cup %u is on the South American calendar; kept open", (unsigned)cc->reg);
      continue;
    }
    int nc = 0;
    for (int g = -2; g < cc->groups; g++) {
      uint16_t id = g == -2 ? cc->ko : g == -1 ? cc->reg : ccup_rep(cc, g);
      int there = 0;
      for (int j = 0; j < k; j++) if (g_td_list[j] == id) there = 1;
      if (!there && get_rec(id) && k < TD_MAX) { g_td_list[k++] = id; nc++; }
    }
    logf("fl26swiss: July teardown -- cup %u: %d regulation(s) added", (unsigned)cc->reg, nc);
  }
  /* the added play-offs and their ties, when the world has them */
  int npo = 0;
  for (int c = 1; c < 3; c++)
    for (int g = -1; g < 8; g++) {
      uint16_t id = g < 0 ? CUPS[c].po : tie_id(&CUPS[c], g);
      int there = 0;
      for (int j = 0; j < n; j++) if (in->b[j] == id) there = 1;
      if (!there && get_rec(id) && k < TD_MAX) { g_td_list[k++] = id; npo++; }
    }
  for (int i = 1; i < NQR; i++)
    for (int g = -1; g < (int)q_n(i) / 2 && g_qreg[i]; g++) {
      uint16_t id = (uint16_t)(g_qreg[i] + (g < 0 ? 0 : 1024 * (g + 1)));
      int there = 0;
      for (int j = 0; j < n; j++) if (in->b[j] == id) there = 1;
      if (!there && get_rec(id) && k < TD_MAX) { g_td_list[k++] = id; npo++; }
    }
  if (npo) logf("fl26swiss: July teardown -- %d play-off and qualifying regulation(s) added", npo);
  /* the league cups' pre-rounds: master and ties */
  int npre = 0, nkept = 0;
  for (int i = 0; i < g_nlpre; i++) {
    if (lpre_cal(&g_lpre[i])) continue;
    if (g_lpre[i].alias && !libq) { nkept++; continue; }    /* B275: closed with phase 3 in January */
    for (int g = -1; g < lpre_rows(&g_lpre[i]); g++) {
      uint16_t id = g < 0 ? g_lpre[i].reg : lpre_tie(&g_lpre[i], g);
      int there = 0;
      for (int j = 0; j < k; j++) if (g_td_list[j] == id) there = 1;
      if (!there && get_rec(id) && k < TD_MAX) { g_td_list[k++] = id; npre++; }
    }
  }
  if (npre) logf("fl26swiss: July teardown -- %d league cup pre-round regulation(s) added", npre);
  if (nkept) logf("fl26swiss: July teardown -- %d Libertadores qualifying phase(s) kept open until January, with phase 3", nkept);
  int nd = 0;
  for (int i = 0; i < ndcl && k < TD_MAX; i++) { g_td_list[k++] = dcl[i]; nd++; }
  if (nd) logf("fl26swiss: July teardown -- %d national/super cup(s) of ours added", nd);
  if (uel6) {
    int nu = uel_ko_teardown_add(g_td_list, &k, TD_MAX, in->b, n);
    logf("fl26swiss: July teardown -- Europa League knockout: %d regulation(s) added (the list closes %u but not %u)",
         nu, (unsigned)R_UCLKO, (unsigned)R_UELKO);
  }
  g_td_vec.b = g_td_list; g_td_vec.e = g_td_list + k; g_td_vec.c = g_td_list + TD_MAX;
  logf("fl26swiss: July teardown -- %d ids, Conference League %u/%u/%u added (the list %s 1027, %s 1029)",
       n, UECL_REG, UECL_KO, UECL_ROW, has1027 ? "has" : "does NOT have", has1029 ? "has" : "does NOT have");
  return &g_td_vec;
}
__attribute__((naked)) void teardown_handler(void)
{
  __asm__ volatile(
    "push %rbx\n"
    "push %rbp\n"
    "push %rsi\n"
    "push %rdi\n"
    "sub  $0x28, %rsp\n"
    "mov  %rcx, %rbx\n"
    "call teardown_pre\n"
    "mov  %rbx, %rcx\n"
    "mov  %rax, %rdx\n"
    "call *g_tramp_teardown(%rip)\n"
    "add  $0x28, %rsp\n"
    "pop  %rdi\n"
    "pop  %rsi\n"
    "pop  %rbp\n"
    "pop  %rbx\n"
    "ret\n");
}

/* FL27 (SmokePatch, 31.10.2026) hooks some of our functions itself: `jmp rel32` and nops over the
   whole prologue, its stub ending in the displaced bytes and a jmp back to target + n (set_clubs
   and the standings rows: 5 + 10 bytes).  Our 14-byte jmp then goes over it and the trampoline
   jumps to their stub, which still ends in the original. */
static unsigned char* e9_dest(const unsigned char* target, int n)
{
  if (n < 14 || target[0] != 0xE9) return 0;
  for (int i = 5; i < n; i++) if (target[i] != 0x90) return 0;
  return (unsigned char*)target + 5 + *(const int32_t*)(target + 1);
}
/* Their jmp with fewer nops than our 14 bytes need (the Group A page factory af4e20: e9 + one
   nop, the game's own code right after it): we leave their bytes as they are and only point the
   rel32 at a jmp to our handler, within reach of the exe; our "original" is a jmp to their stub. */
static int e9_retarget(unsigned char* target, void* handler, unsigned char** tramp_out)
{
  if (target[0] != 0xE9) return 2;
  unsigned char* stub = target + 5 + *(const int32_t*)(target + 1);
  unsigned char* t = near_alloc(g_base);
  if (!t) return 3;
  int64_t rel = (int64_t)(uintptr_t)t - (int64_t)(uintptr_t)(target + 5);
  if (rel != (int32_t)rel) return 3;
  t[0] = 0xFF; t[1] = 0x25; *(uint32_t*)(t + 2) = 0; *(uint64_t*)(t + 6) = (uint64_t)(uintptr_t)handler;
  t[16] = 0xFF; t[17] = 0x25; *(uint32_t*)(t + 18) = 0; *(uint64_t*)(t + 22) = (uint64_t)(uintptr_t)stub;
  DWORD old;
  if (!VirtualProtect(target, 5, PAGE_EXECUTE_READWRITE, &old)) return 4;
  *(int32_t*)(target + 1) = (int32_t)rel;
  VirtualProtect(target, 5, old, &old);
  FlushInstructionCache(GetCurrentProcess(), target, 5);
  *tramp_out = t + 16;
  g_chained = 1;
  gate_add(t + 6, handler, stub);
  return 0;
}
static int hook_or_chain(unsigned char* target, const unsigned char* sig, int n, void* handler, unsigned char** tramp_out)
{
  static const unsigned char JMP[6] = { 0xFF, 0x25, 0, 0, 0, 0 };
  if (!memcmp(target, sig, n)) return hook(target, sig, n, handler, tramp_out);
  if (target[0] == 0xE9 && !e9_dest(target, n)) return e9_retarget(target, handler, tramp_out);
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
    g_chained = 1;
    gate_add(target + 6, handler, t);
    return 0;
  }
  if (memcmp(target, JMP, 6)) return 2;
  unsigned char* t = (unsigned char*)VirtualAlloc(0, 0x100, MEM_COMMIT|MEM_RESERVE, PAGE_EXECUTE_READWRITE);
  if (!t) return 3;
  memcpy(t, target, 14);                     /* jmp to the handler that was there */
  DWORD old;
  if (!VirtualProtect(target, 14, PAGE_EXECUTE_READWRITE, &old)) return 4;
  *(uint64_t*)(target + 6) = (uint64_t)(uintptr_t)handler;
  VirtualProtect(target, 14, old, &old);
  FlushInstructionCache(GetCurrentProcess(), target, 14);
  *tramp_out = t;
  g_chained = 1;
  gate_add(target + 6, handler, t);
  return 0;
}

/* The league phase as one scrolling table -- by David (david.bdj), 2026-10-13, taken over as he
 * sent it (notes/prilozi/david-UEFA_tabla_vertical_20261013.zip: src/uefa_vertical.inc, with
 * mocked routing tests in tests/test_uefa.c).  Presentation only: no world or save writes.
 *
 * Competition Info drew the 36-club league phase with the game's group page, four pages of nine
 * (and Return covered row 9).  af4e20 builds that group controller.  For competition 2 / 3 / 174
 * with the league-phase row selected (1027 / 1029 / 1210, or nothing selected yet) and a native
 * table of exactly 36, it builds the game's own league standings controller (aed610) instead,
 * points it at the row (+a8) and gives it a copy of the league vtable 2684408 whose initializer
 * slot d8 (aeda10) is wrapped only to log the row count.  Everything else gets the original
 * factory with its arguments untouched.  The competition selection is read at the disp32 the
 * game's own code uses at af4ea9 and aed39c, decoded live, both must agree.
 *
 * Checked on our exe 2026-10-13 (live, test022 caps): the af4e20 and aed610 prologues, both
 * selection references (offset 0x1787b5c) and vtable slot d8 == aeda10 all as he found them;
 * none of our hooks touches af4e20 (the knockout list is the call at af98c9).
 * Ranks of clubs level on points (his report: 1 pt 1-1 shared 13th, 1 pt 2-2 shared 19th) are
 * the stored table's, the old page shows the same -- not changed here. */
typedef uint64_t (*u10_factory_fn)(uint64_t,uint64_t,uint64_t);
typedef uint64_t (*u10_init_fn)(uint64_t,uint64_t,uint64_t,uint64_t);
static unsigned char* u10_group_tramp;
static uintptr_t u10_vtable[1+0x250/8];
static int32_t u10_selection_offset;
static owner_fn u10_owner;
static table_fn u10_table;
static u10_factory_fn u10_league;
static u10_init_fn u10_native_init;
static unsigned u10_logs;

static uint16_t u10_reg(unsigned comp,unsigned selected) {
 unsigned phase=comp==2?3:comp==3?5:comp==174?186:0;
 /* FL27 (g_native_uefa): the Champions and Europa League phase is the game's, but Competition Info
    draws it with this scrolling table too (mato 19.11.2026, after the pages of 8 of B503: "uzmi onaj
    modul od davida, ono je bilo perfektno"), as the Conference League's always was: row 1027 / 1029
    with 36 clubs goes to the league controller, any other count to the game's pages as before */
 unsigned row=phase==3?1027:phase==5?1029:phase==186?1210:0;
 if(!phase || (selected!=0xffff && selected!=phase && selected!=row))return 0;
 return (uint16_t)row;
}
static unsigned u10_count(uint64_t self) {
 uintptr_t b=*(uintptr_t*)(self+0x90),e=*(uintptr_t*)(self+0x98),c=*(uintptr_t*)(self+0xa0);
 return b && e>=b && c>=e && e-b<=48*4 && (e-b)%4==0?(unsigned)((e-b)/4):0;
}
static uint64_t u10_initialize(uint64_t a,uint64_t b,uint64_t c,uint64_t d) {
 uint64_t ok=u10_native_init(a,b,c,d);
 unsigned reg=*(uint16_t*)(a+0xa8),count=u10_count(a);
 logf("UEFA10 initialized reg=%u result=%u rows=%u expected=36",reg,(unsigned)(ok&255),count);
 return ok;
}
static uint64_t u10_factory(uint64_t a,uint64_t b,uint64_t c) {
 unsigned char* owner=u10_owner();
 unsigned char* block=owner?*(unsigned char**)(owner+0x48):0;
 unsigned comp=0,selected=0;uint16_t row=0;
 if(block) {
   comp=*(uint32_t*)(block+u10_selection_offset);
   selected=*(uint16_t*)(block+u10_selection_offset+4);
   row=u10_reg(comp,selected);
 }
 unsigned char* table=row?lp_table(row):0;     /* B206: the season with clubs, not next season's empty one */
 unsigned count=table?*(uint32_t*)(table+0x3c0):0;
 if(!row || count!=36) {
   if(u10_logs++<80)logf("UEFA10 original comp=%u selected=%u row=%u count=%u",comp,selected,row,count);
   return ((u10_factory_fn)(uintptr_t)u10_group_tramp)(a,b,c);
 }
 uint64_t self=u10_league(a,b,c);
 if(self) {
   /* aed610 returns the newly constructed object before asynchronous init.
      The league initializer consumes +a8 and reads its native table itself. */
   *(uint16_t*)(self+0xa8)=row;
   *(uintptr_t*)self=(uintptr_t)(u10_vtable+1);
 }
 logf("UEFA10 routed comp=%u selected=%u row=%u count=%u object=%llx",comp,selected,row,count,(unsigned long long)self);
 return self;
}
static int u10_decode_offset(unsigned char* compare,unsigned char* load,int32_t* out) {
 /* Decode both LIVE references, since the capacity module relocates ML data.
    af4ea9: cmp dword [r8+disp32],8; aed39c: movsd xmm0,[rcx+disp32]. */
 static const unsigned char cmp[]={0x41,0x83,0xb8};
 static const unsigned char mov[]={0xf2,0x0f,0x10,0x81};
 int32_t x,y;
 /* FL27: SmokePatch's jmp sits on af4ea9 (their own league-phase routing); aed39c is as in FL26 */
 if(g_native_uefa && compare[0]==0xe9 && !memcmp(load,mov,4)) {
   memcpy(&y,load+4,4);
   if(y<0x1000 || y>0x10000000)return 0;
   *out=y;return 1;
 }
 if(memcmp(compare,cmp,3) || compare[7]!=8 || memcmp(load,mov,4))return 0;
 memcpy(&x,compare+3,4);memcpy(&y,load+4,4);
 if(x!=y || x<0x1000 || x>0x10000000)return 0;
 *out=x;return 1;
}
static void u10_install(void) {
 static const unsigned char sig[]={0x40,0x57,0x48,0x83,0xec,0x30,0x48,0xc7,0x44,0x24,0x20,0xfe,0xff,0xff,0xff};
 uintptr_t* vt=(uintptr_t*)(uintptr_t)(g_base+0x2684408);
 if(!u10_decode_offset((unsigned char*)(uintptr_t)(g_base+0xaf4ea9),(unsigned char*)(uintptr_t)(g_base+0xaed39c),&u10_selection_offset)
    || vt[0xd8/8]!=g_base+0xaeda10) {
   logf("UEFA10 disabled: selection signatures or league initializer differ");return;
 }
 memcpy(u10_vtable,vt-1,sizeof u10_vtable);
 u10_vtable[1+0xd8/8]=(uintptr_t)u10_initialize;
 u10_owner=(owner_fn)(uintptr_t)(g_base+OWNER_RVA);
 u10_table=(table_fn)(uintptr_t)(g_base+TABLE_RVA);
 u10_league=(u10_factory_fn)(uintptr_t)(g_base+0xaed610);
 u10_native_init=(u10_init_fn)(uintptr_t)(g_base+0xaeda10);
 int status=hook_or_chain((unsigned char*)(uintptr_t)(g_base+0xaf4e20),sig,sizeof sig,(void*)u10_factory,&u10_group_tramp);
 logf("UEFA10 install=%d selection-offset=%x; exact UEFA 36-team tables only",status,(unsigned)u10_selection_offset);
}

/* ---- B206: Competition Info's League Phase showed "Group A" with no clubs ----
 *
 * Micarodvzla 23.10. (second season, Europa League only) and r13 on 12/6/2030: the Europa League
 * and the Conference League hold an empty table of next season (2030, 0 rows) beside the played
 * one (2029, 36 rows), opened early like the one lp_table works around for the play-off; the
 * Champions League had no 2030 table yet and showed its league phase.  The standings pages read
 * the table of the latest season through 0x141579b90 (a `jmp 0x14158b6f0` thunk).  Only the five
 * calls of those pages -- league page aedd37 / aee0f5 / aee4fa, group page af591e / af63db, all
 * in UI controllers (vtable slots at 0x1426844e0, 0x142685f58, 0x142686210 and the row fill of
 * 0x140aeda10) -- are turned to a jump of ours next to the exe; the game's other calls of the
 * thunk are not touched.  For 1027 / 1029 / 1210 with fewer than 24 rows it answers with
 * season_table's -- the latest season of that id with 24..48 rows; once next season's draw
 * fills its table, that one has 36 rows and is shown as before. */
#define LPPAGE_THUNK 0x1579b90
static unsigned char* lppage_table(uint64_t id)
{
  unsigned char* t = ((table_fn)(uintptr_t)(g_base + LPPAGE_THUNK))(id);
  uint16_t r = (uint16_t)id;
  if (r != 1027 && r != 1029 && r != UECL_ROW) return t;
  if (t && *(uint32_t*)(t + 0x3c0) >= 24) return t;
  unsigned yr = 0;
  unsigned char* t2 = season_table(r, &yr);
  if (!t2) return t;
  static uint16_t said[3];
  int k = r == 1027 ? 0 : r == 1029 ? 1 : 2;
  if (said[k] != (uint16_t)yr) {
    said[k] = (uint16_t)yr;
    logf("fl26swiss: League Phase page, reg %u -- the latest season's table has %u rows; season %u's (%u rows) is shown",
         (unsigned)r, t ? *(uint32_t*)(t + 0x3c0) : 0, yr, *(uint32_t*)(t2 + 0x3c0));
  }
  return t2;
}
static void lppage_install(uint64_t exe_base)
{
  static const uint32_t CALLS[5] = { 0xaedd37, 0xaee0f5, 0xaee4fa, 0xaf591e, 0xaf63db };
  for (int i = 0; i < 5; i++) {
    unsigned char* c = (unsigned char*)(uintptr_t)(exe_base + CALLS[i]);
    if (c[0] != 0xe8 || (uint64_t)(uintptr_t)(c + 5) + *(int32_t*)(c + 1) != exe_base + LPPAGE_THUNK) {
      logf("fl26swiss: League Phase page fallback NOT installed (call %d is not the one expected)", i);
      return;
    }
  }
  unsigned char* t = near_alloc(exe_base);
  if (!t) { logf("fl26swiss: League Phase page fallback NOT installed (no page in reach)"); return; }
  t[0] = 0xFF; t[1] = 0x25; *(uint32_t*)(t + 2) = 0; *(uint64_t*)(t + 6) = (uint64_t)(uintptr_t)lppage_table;
  FlushInstructionCache(GetCurrentProcess(), t, 14);
  for (int i = 0; i < 5; i++) {
    unsigned char* c = (unsigned char*)(uintptr_t)(exe_base + CALLS[i]);
    DWORD old;
    if (!VirtualProtect(c, 5, PAGE_EXECUTE_READWRITE, &old)) return;
    *(int32_t*)(c + 1) = (int32_t)((int64_t)(uintptr_t)t - (int64_t)(uintptr_t)(c + 5));
    VirtualProtect(c, 5, old, &old);
    FlushInstructionCache(GetCurrentProcess(), c, 5);
  }
  logf("fl26swiss: League Phase page fallback live (5 page calls)");
}

/* ---- MP: a matches-played column in the standings (mato 2026-10-21: its own column, A stays) ----
 *
 * The standings page (cpk_dat/common/menu/general/rankingTeam.bin) has seven number cells a row
 * -- Pts W D L F A GD -- filled by 0x140aee0c0 (screen, row widget, idx) from the competition's
 * table (0x141579b90, 0x14 bytes a row). The row's byte +0x0f is the matches played; nothing in
 * the game shows it. Mod Studio's copy of the layout (tools/mkmp.py) adds a cell num_MatchesPlayed
 * after Pts and a header title_MatchesPlayed and moves the seven along; this fills them, after
 * the game's own fill. Without that layout the lookups find nothing and nothing is written. */
#define MPFILL_RVA  0xaee0c0u
#define MPNUM_RVA   0xe493a0u   /* setNumber(widget, int64) */
#define MPTXT_RVA   0xe48bf0u   /* setText(widget, std::string*, u8, u8) */
#define MPROOT_RVA  0xe3d4f0u   /* root(screen, 0) */
typedef uint64_t (*mpfill_fn)(void*, void*, uint64_t, uint64_t);
typedef void (*mpnum_fn)(void*, int64_t);
typedef void (*mptxt_fn)(void*, void*, uint64_t, uint64_t);
typedef void* (*mproot_fn)(void*, uint64_t);
typedef void* (*mpchild_fn)(void*, const char*);
static unsigned char* g_tramp_mpfill;
static int g_mp_cells, g_mp_said, g_mp_way;
static void* mp_child(void* widget, const char* name)
{
  if (!widget) return 0;
  unsigned char* finder = (unsigned char*)widget + 0x98;
  void** vt = *(void***)finder;
  return vt ? ((mpchild_fn)vt[1])(finder, name) : 0;
}
/* ---- the zone strip (0.3.0, mato 2026-11-01; vmican's idea): the colour of a row's place ----
 *
 * Mod Studio's layout (tools/mkmpcol.py ZONE_CELL) gives each row a text cell flZone on its left
 * edge; this writes a left half block into it, as tall as the row (FontScale 1.85: text is not
 * scaled by the cell's matrix; FontScale is a float at +4 of the props at widget+0x98, read with
 * atof by 0x140e4b6a0), in the colour of the row's
 * place, or nothing (setText 0x140e48bf0, then setColor 0x140e48a80: a palette index under 0x50,
 * kept at +0xb8 for when the cursor leaves the row). The place:
 *   - the continental places of the league, by position (zone_access): the access list in use
 *     (g_access: the world's own uefa lines, or the shipped one), the entries of the world's
 *     continental cups of ours (ccup lines, their comp= through fl26_swiss_ccup_zone) and of its
 *     pre-rounds (lpre lines: the modern Libertadores phases 1 and 2, the Sudamericana's first
 *     stage). A confederation's top cup is blue -- the Champions League and its play-off, the
 *     Libertadores (groups, qualifying, phases 1 and 2), the AFC Champions League (Elite), the CAF
 *     Champions League, the CONCACAF Champions Cup, the OFC Champions League; the one below orange
 *     -- the Europa League and its play-off, the Copa Sudamericana and its first stage, the CAF
 *     Confederation Cup, the AFC Champions League Two; the third teal -- the Conference League and
 *     its play-off, the AFC Challenge League (mato 2026-11-08: Brazil's 5-6 and 7-12 had none);
 *   - up and down by the game's own counts (as 0x140aee370 reads them for icon_divisionUp/Down):
 *     the competition (0x1414bb000 on 0x1414b6a60()->+0x48), its clubs (+0x30a & 0x7f), down
 *     when it has a league below (+0x7e) and the row is in the last 0x140ea0bb0(reg), up when it
 *     has one above (+0x7c) and the row is in the first 0x140ea1c00(reg, 0). That function also
 *     wants +0x304's top bits 10, which the Druga NL's (0x6002dd00, its two up arrows drawn) has
 *     not, so it is not asked here (2026-11-01);
 *   - a league phase (36 clubs): 1-8 up (the Round of 16), 9-24 the play-off;
 *   - a league the game splits (Scotland, Denmark, Belgium: ZSPLITS, the game's ids in every world;
 *     mato 2026-11-01: the play-offs decide Europe, not the regular season): its regular season
 *     shows the split -- the first group's places up, the second group's the play-off when the
 *     access list has a place past the first group, the last by the game's count down -- and the
 *     two groups the European places, the first group's place k being the league's place k, the
 *     second group's place k the league's place (first group's clubs + k). A group's clubs are
 *     the game's count (+0x30a) once the split is drawn; before it the count is 0 (FL27,
 *     Belgium, August 2026: both read 0) and the regulation's own number is used (Scotland and
 *     Denmark 6 + 6, Belgium 4 + 4: "Contested by 4 teams"; checked at the split, 2027-06-01). The
 *     game's own down places stay red in the second group (Denmark 11-12: Lyngby and Viborg).
 * The palette, read in FL26 2.2 on 2026-11-01 (the ranking numbers drawn in each index): 70 blue
 * (0,125,255), 3 orange (244,78,0), 34 teal (2,163,174), 62 green (0,255,0), 67 amber
 * (255,189,0), 72 red (208,8,8). Without that layout the cell is not found and nothing is done. */
enum { ZONE_CL, ZONE_EL, ZONE_ECL, ZONE_UP, ZONE_PO, ZONE_DOWN, ZONE_N };
static const int ZONE_COLOUR[ZONE_N] = { 70, 3, 34, 62, 67, 72 };
static const char* const ZONE_NAME[ZONE_N] = { "top continental cup (blue)", "second continental cup (orange)", "third continental cup (teal)", "up", "play-off", "down" };
#define ZONE_SCALE 1.85f        /* 1.0: a 7 x 14 px block at 1152 wide; at 1920 the rows are 45 px apart and 1.9 drew 43-45 px, the last row 2 px past the table edge (FL27, 2026-11-01); 1.85: 43 px */
#define ZCOL_RVA   0xe48a80u    /* setColor(widget, index, keep) */
#define ZDB_RVA    0x14b6a60u   /* the competitions' owner */
#define ZCOMP_RVA  0x14bb000u   /* competition(owner+0x48, reg) */
#define ZDOWN_RVA  0xea0bb0u    /* clubs down(reg) */
#define ZUP_RVA    0xea1c00u    /* clubs up(reg, 0) */
typedef int (*zcol_fn)(void*, int, uint64_t);
typedef void* (*zdb_fn)(void);
typedef unsigned char* (*zcomp_fn)(void*, uint64_t);
typedef uint64_t (*zdown_fn)(uint64_t);
typedef uint64_t (*zup_fn)(uint64_t, uint64_t);
static int g_zone_said;
/* the regular season of a split league and its two groups (top six / bottom six, the title and
   the second play-off), the game's own regulation ids */
static const struct { uint16_t reg, first, second; uint8_t n1, n2; } ZSPLITS[] = {
  { 134, 135, 136, 6, 6 },    /* Scotland */
  { 147, 148, 175, 6, 6 },    /* Denmark */
  { 155, 156, 172, 4, 4 },    /* Belgium */
};
static unsigned char* zcomp(uint16_t reg)
{
#ifdef FL26_ZONE_TEST
  extern unsigned char* zone_test_comp(uint16_t reg);
  return zone_test_comp(reg);
#else
  void* db = ((zdb_fn)(uintptr_t)(g_base + ZDB_RVA))();
  return db ? ((zcomp_fn)(uintptr_t)(g_base + ZCOMP_RVA))(*(void**)((unsigned char*)db + 0x48), reg) : 0;
#endif
}
static unsigned zclubs(uint16_t reg, unsigned dflt)
{
  unsigned char* c = zcomp(reg);
  unsigned n = c ? *(uint16_t*)(c + 0x30a) & 0x7f : 0;
  return n ? n : dflt;
}
/* the League Builder's competition numbers (tools/fl26world.py COMPETITIONS) past the uefa
   lines': its own continental cups (CCUPS, the ccup lines' comp=) and the modern CONMEBOL
   phases (CONMEBOL_STAGE_TARGETS, the lpre lines) */
enum { ZC_CAFCL = 6, ZC_CAFCC = 7, ZC_ACL2 = 8, ZC_SUDAM = 9, ZC_CONCACAF = 13, ZC_OFC = 14, ZC_AFCCHL = 15,
       ZC_LIBF1 = 16, ZC_LIBF2 = 17, ZC_SUDF1 = 19 };
/* a competition's colour: a confederation's top cup blue, the one below orange, the third teal */
static int zone_code(unsigned comp)
{
  switch (comp) {
    case UCL: case UCLQ: case LIB: case LIBQ: case AFCL:
    case ZC_CAFCL: case ZC_CONCACAF: case ZC_OFC: case ZC_LIBF1: case ZC_LIBF2: return ZONE_CL;
    case UEL: case UELQ: case ZC_CAFCC: case ZC_ACL2: case ZC_SUDAM: case ZC_SUDF1: return ZONE_EL;
    case UECL: case UECLQ: case ZC_AFCCHL: return ZONE_ECL;
  }
  return -1;
}
/* the competition of each continental cup of ours, by its knockout id (fl26_swiss_ccup_zone):
   the ccup line's comp=, which the DLL's cup list itself does not carry -- a league cup, a super
   cup or a promotion play-off has none and gets no colour */
static struct { uint16_t ko; uint8_t comp; } g_czone[MAX_CCUP]; static int g_nczone;
static int ccup_zcomp(uint16_t ko)
{
  for (int i = 0; i < g_nczone; i++) if (g_czone[i].ko == ko) return g_czone[i].comp;
  return -1;
}
/* n pairs of u16 from the loader: a cup's knockout id (as fl26_swiss_ccup's list has it), its
   competition (6, 7, 8, 9, 13, 14, 15); others are left out. Answers how many were taken. */
__declspec(dllexport) int fl26_swiss_ccup_zone(const uint16_t* v, int n)
{
  g_nczone = 0;
  for (int i = 0; v && i < n && g_nczone < MAX_CCUP; i++) {
    uint16_t ko = v[2 * i], comp = v[2 * i + 1];
    if (!ko || comp < ZC_CAFCL || comp > ZC_AFCCHL || (comp > ZC_SUDAM && comp < ZC_CONCACAF)) continue;
    g_czone[g_nczone].ko = ko; g_czone[g_nczone].comp = (uint8_t)comp; g_nczone++;
  }
  return g_nczone;
}
/* the continental place of league reg's place rank, or -1: the access list in use (the uefa
   lines, or the shipped list), then the continental cups of ours by their entries (the ccup
   lines' entry=, with the cup's comp=), then the pre-rounds by theirs (the lpre lines: cup=0 a
   Libertadores phase, else the pre-round of the cup it names -- the Sudamericana's first stage).
   A cup winner's place (position 0) and an entry made of another round's winners or losers
   (id + 1024 k, position 255) are no row of a table */
static int zone_access(uint16_t reg, unsigned rank)
{
  if (!rank || assoc_source(reg)) return -1; /* cup winners / synthetic ranks aren't table rows */
  for (size_t k = 0; k < g_naccess; k++) {
    const access_t* a = &g_access[k];
    if (a->reg != reg || a->rank != rank) continue;
    int z = zone_code(a->comp);
    if (z >= 0) return z;
  }
  if (!rank) return -1;
  for (int k = 0; k < g_nccup; k++) {
    const ccup_t* c = &g_ccup[k];
    int z = zone_code((unsigned)ccup_zcomp(c->ko));
    if (z < 0) continue;
    for (int e = 0; e < c->n && e < CCUP_MAX_ENTRY; e++)
      if (c->ereg[e] == reg && c->erank[e] == rank) return z;
  }
  for (int k = 0; k < g_nlpre; k++) {
    const lpre_t* l = &g_lpre[k];
    int z = l->ko ? zone_code((unsigned)ccup_zcomp(l->ko)) : ZONE_CL;
    if (z < 0) continue;
    for (int e = 0; e < 2 * l->ties && e < 2 * LPRE_MAX; e++)
      if (l->ereg[e] == reg && l->erank[e] == rank) return z;
  }
  /* Modern F1/F2 entries live in the world's lpre records, not g_access.
     Alias phases belong to Libertadores; the single-match pre-round feeding
     the identified Sudamericana cup belongs to Sudamericana. Winner/loser
     feeds (rank 0/255) must never be painted as domestic league positions. */
  int stage;
  if (gc_of(reg) >= 0 || ccup_of(reg, &stage) >= 0 || lpre_of(reg, &stage) >= 0)
    return -1; /* these are competition stages, never domestic qualification sources */
  for (int k = 0; k < g_nlpre; k++) {
    const lpre_t* l = &g_lpre[k];
    int colour = l->alias ? ZONE_CL : lpre_is_suda(l) ? ZONE_EL : -1;
    if (colour < 0) continue;
    for (unsigned j = 0; j < 2u * l->ties; j++)
      if (l->ereg[j] == reg && l->erank[j] > 0 && l->erank[j] < 255
          && l->erank[j] == rank) return colour;
  }
  int sud = modern_suda_ccup();
  if (sud >= 0) {
    const ccup_t* c = &g_ccup[sud];
    for (unsigned j = 0; j < c->n; j++)
      if (c->ereg[j] == reg && c->erank[j] > 0 && c->erank[j] < 255
          && c->erank[j] == rank) return ZONE_EL;
  }
  return -1;
}
static int zone_down(uint16_t reg, unsigned i)
{
  unsigned char* c = zcomp(reg);
  if (!c || *(uint16_t*)(c + 0x7e) == 0xffff) return 0;
  unsigned n = *(uint16_t*)(c + 0x30a) & 0x7f;
  unsigned d = (unsigned)((zdown_fn)(uintptr_t)(g_base + ZDOWN_RVA))(reg);
  return d && i < n && i + d >= n;
}
/* B458 (13.11.2026, a tester's Serie C in an FL27 world: Girone A had its promotion colour, Girone
   B and C none). The game links one league to one league (c+0x7c up, c+0x7e down), so of a set of
   groups only the first has a link; the others are moved by fl26chain from the world file's gset
   lines. The loader hands the same lines here (fl26_swiss_gzone): n triples of u16 -- a league,
   how many of its clubs go up, how many go down. A league named twice (a group below one set
   and above another) has both. Used only where the game has no link of its own. */
static struct { uint16_t reg; uint8_t up, down; } g_gzone[512]; static int g_ngzone;
__declspec(dllexport) int fl26_swiss_gzone(const uint16_t* v, int n)
{
  g_ngzone = 0;
  for (int i = 0; v && i < n; i++) {
    uint16_t reg = v[3 * i], up = v[3 * i + 1], down = v[3 * i + 2];
    if (!reg || (!up && !down) || up > 127 || down > 127) continue;
    int k = 0;
    while (k < g_ngzone && g_gzone[k].reg != reg) k++;
    if (k == g_ngzone) {
      if (g_ngzone >= (int)(sizeof g_gzone / sizeof *g_gzone)) continue;
      g_gzone[g_ngzone].reg = reg; g_gzone[g_ngzone].up = 0; g_gzone[g_ngzone].down = 0; g_ngzone++;
    }
    if (up) g_gzone[k].up = (uint8_t)up;
    if (down) g_gzone[k].down = (uint8_t)down;
  }
  return g_ngzone;
}
/* row i (from 0) of league reg with n clubs: ZONE_UP, ZONE_DOWN or -1 by the group sets; a side
   the game links itself (linked_up / linked_down) is the game's to colour */
static int zone_group(uint16_t reg, unsigned i, unsigned n, int linked_up, int linked_down)
{
  for (int k = 0; k < g_ngzone; k++) {
    if (g_gzone[k].reg != reg) continue;
    if (!linked_up && i < g_gzone[k].up) return ZONE_UP;
    if (!linked_down && n && i < n && i + g_gzone[k].down >= n) return ZONE_DOWN;
    return -1;
  }
  return -1;
}
static int zone_of(uint16_t reg, unsigned i)
{
  if (reg == 1027 || reg == 1029 || reg == UECL_ROW)
    return i < 8 ? ZONE_UP : i < 24 ? ZONE_PO : -1;
  int split = 0;
  for (size_t k = 0; k < sizeof ZSPLITS / sizeof *ZSPLITS; k++) {
    if (reg == ZSPLITS[k].first) return zone_access(ZSPLITS[k].reg, i + 1);
    if (reg == ZSPLITS[k].second) return zone_access(ZSPLITS[k].reg, zclubs(ZSPLITS[k].first, ZSPLITS[k].n1) + i + 1);
    if (reg != ZSPLITS[k].reg) continue;
    unsigned a = zclubs(ZSPLITS[k].first, ZSPLITS[k].n1), b = zclubs(ZSPLITS[k].second, ZSPLITS[k].n2);
    static unsigned said_split;
    if (!(said_split & 1u << k)) {
      said_split |= 1u << k;
      logf("fl26swiss: zone -- split league %u: groups %u (%u clubs) and %u (%u clubs)",
           (unsigned)reg, (unsigned)ZSPLITS[k].first, a, (unsigned)ZSPLITS[k].second, b);
    }
    if (i < a) return ZONE_UP;
    if (zone_down(reg, i)) return ZONE_DOWN;   /* Denmark 6 + 6: 11-12 go down, not the play-off */
    if (i < a + b) {
      for (unsigned r = a + 1; r <= a + b; r++)
        if (zone_access(reg, r) >= 0) return ZONE_PO;
    }
    split = 1;
  }
  if (!split) {
    int z = zone_access(reg, i + 1);
    if (z >= 0) return z;
  }
  unsigned char* c = zcomp(reg);
  if (!c) return -1;
  if (*(uint16_t*)(c + 0x7c) != 0xffff && i < (unsigned)((zup_fn)(uintptr_t)(g_base + ZUP_RVA))(reg, 0))
    return ZONE_UP;
  if (zone_down(reg, i)) return ZONE_DOWN;
  return zone_group(reg, i, *(uint16_t*)(c + 0x30a) & 0x7f,
                    *(uint16_t*)(c + 0x7c) != 0xffff, *(uint16_t*)(c + 0x7e) != 0xffff);
}
static void zone_fill(void* roww, uint16_t reg, unsigned i)
{
  void* w = mp_child(roww, "flZone");
  if (!w) return;
  int z = zone_of(reg, i);
  struct { char buf[16]; uint64_t size, cap; } str;              /* MSVC std::string, short form */
  memset(&str, 0, sizeof str); str.cap = 15;
  if (z >= 0) { memcpy(str.buf, "\xe2\x96\x8c", 4); str.size = 3; }   /* U+258C left half block */
  float* props = *(float**)((unsigned char*)w + 0x98);   /* the text's props: +4 FontScale (a float) */
  if (props) props[1] = ZONE_SCALE;                      /* the cell's matrix does not scale text */
  ((mptxt_fn)(uintptr_t)(g_base + MPTXT_RVA))(w, &str, 0, 0);
  if (z >= 0) ((zcol_fn)(uintptr_t)(g_base + ZCOL_RVA))(w, ZONE_COLOUR[z], 1);
  if (g_zone_said < 12 && z >= 0) { g_zone_said++; logf("fl26swiss: zone -- reg %u place %u: %s", (unsigned)reg, i + 1, ZONE_NAME[z]); }
}
static uint64_t mp_fill(void* screen, void* roww, uint64_t idx, uint64_t r9)
{
  uint64_t ret = ((mpfill_fn)(uintptr_t)g_tramp_mpfill)(screen, roww, idx, r9);
  if (!screen || !roww) return ret;
  unsigned i = (unsigned)idx;
  uint16_t reg = *(uint16_t*)((unsigned char*)screen + 0xa8);
  /* the league phases: the table the page shows (B206), not next season's empty one */
  unsigned char* tab = reg == 1027 || reg == 1029 || reg == UECL_ROW ? lp_table(reg)
                     : ((table_fn)(uintptr_t)(g_base + TABLE_RVA))(reg);
  if (!tab) return ret;
  unsigned char* row = i < 0x30 ? tab + i * 0x14 : tab;
  zone_fill(roww, reg, i);
  void* w = mp_child(roww, "num_MatchesPlayed");
  if (!w) {
    if (!g_mp_said++) logf("fl26swiss: MP -- this standings layout has no num_MatchesPlayed cell (game's own layout); nothing added");
    return ret;
  }
  ((mpnum_fn)(uintptr_t)(g_base + MPNUM_RVA))(w, (int64_t)row[0x0f]);
  if (g_mp_cells++ < 3) logf("fl26swiss: MP -- reg %u row %u: %u played", (unsigned)*(uint16_t*)((unsigned char*)screen + 0xa8), i, (unsigned)row[0x0f]);
  /* the header: listHeader's titles are found only when the layout's AS3 registers them, which
     a new one is not (in listHeader or on the page: the page's finder never had it, 2026-10-21),
     so the layout gives every row a title_MatchesPlayed cell over its MP number, a row
     higher; "MP" goes into the top row's (choice_0, whatever line of the table it shows) and
     nothing into the others' */
  void* lab = mp_child(roww, "title_MatchesPlayed");
  if (lab) {
    void* root = ((mproot_fn)(uintptr_t)(g_base + MPROOT_RVA))(screen, 0);
    int top = root && mp_child(root, "choice_0") == roww;
    struct { char buf[16]; uint64_t size, cap; } str;              /* MSVC std::string, short form */
    memset(&str, 0, sizeof str); str.cap = 15;
    if (top) { memcpy(str.buf, "MP", 3); str.size = 2; }
    {   /* the header's colour: a text cell's FontColor (its properties at +0x98, +0x0c; read by
           the text's init 0x140e494f0 from the layout's __setProp) is set only for the cells the
           AS3 knows, so the new one would draw in the rows' dark grey; take title_Points'
           (white, 4 on 2026-10-21) */
      void* tp = root ? mp_child(root, "title_Points") : 0;
      uint32_t* hp = tp ? *(uint32_t**)((unsigned char*)tp + 0x98) : 0;
      uint32_t* lp = *(uint32_t**)((unsigned char*)lab + 0x98);
      if (hp && lp) lp[3] = hp[3];
    }
    ((mptxt_fn)(uintptr_t)(g_base + MPTXT_RVA))(lab, &str, 0, 0);
    if (top && !g_mp_way) { g_mp_way = 1; logf("fl26swiss: MP -- header in the top row's cell"); }
  }
  return ret;
}
static void mp_install(void)
{
  static const unsigned char sig[17] = { 0x40,0x55, 0x56, 0x57, 0x48,0x83,0xec,0x60, 0x48,0xc7,0x44,0x24,0x28,0xfe,0xff,0xff,0xff };
  int st = hook((unsigned char*)(uintptr_t)(g_base + MPFILL_RVA), sig, sizeof sig, (void*)mp_fill, &g_tramp_mpfill);
  logf("fl26swiss: MP column hook %s (%d)", st ? "NOT installed" : "live", st);
  if (!st) logf("fl26swiss: standings zones v2 -- modern CONMEBOL domestic access from lpre/ccup");
}

/* 0 ok; 2 signature mismatch; 3 VirtualAlloc failed; 4 VirtualProtect failed; 9 bad config;
   +10 for the date hook, +20 for the group hook */
__declspec(dllexport) int fl26_swiss_install(uint64_t exe_base, const uint16_t* regs, int nregs)
{
  if (!regs || nregs < 1 || nregs > MAX_REGS) return 9;
  g_base = exe_base;
  /* FL27: set_clubs starts with SmokePatch's jmp -- their league phase for the Champions and
     Europa League, so 1027 / 1029 are not ours to schedule (see g_native_uefa). fl26chain loads
     first and puts its own jmp in front of theirs (in game, 31.10.), so their other hook of the
     same kind, on the standings filler, says it too */
  g_native_uefa = e9_dest((const unsigned char*)(uintptr_t)(exe_base + SETCL_RVA), 15) != 0
               || e9_dest((const unsigned char*)(uintptr_t)(exe_base + STAND_RVA), 15) != 0;
  g_nreg = 0;
  for (int i = 0; i < nregs; i++)
    if (!g_native_uefa || (regs[i] != 1027 && regs[i] != 1029)) g_reg[g_nreg++] = regs[i];
  if (g_native_uefa)
    logf("fl26swiss: FL27 -- UCL/UEL league phase and knockout are the game's; ours: access list, "
         "qualifying rounds, Conference League (%d of %d regulation(s) kept)", g_nreg, nregs);
  /* Both signatures are checked before either is patched: a mismatch on the second one used
     to leave the game half hooked while the loader reported it unmodified. */
  if (memcmp((void*)(uintptr_t)(exe_base + GEN_RVA),  SIG_GEN,  16)) return 2;
  if (memcmp((void*)(uintptr_t)(exe_base + DATE_RVA), SIG_DATE, 17)) return 12;
  if (memcmp((void*)(uintptr_t)(exe_base + GROUP_RVA), SIG_GROUP, 14)) return 22;
  /* optional: without it a league of more rounds than the longest calendar is left short */
  g_pushdate_ok = !memcmp((void*)(uintptr_t)(exe_base + PUSHDATE_RVA), SIG_PUSHDATE, 16);
  if (!g_pushdate_ok) logf("fl26swiss: the calendar push_back (0x%llx) is not the expected code; leagues of more "
                           "than 46 rounds keep 46 dates", (unsigned long long)(exe_base + PUSHDATE_RVA));
  int r = hook((unsigned char*)(uintptr_t)(exe_base + GEN_RVA), SIG_GEN, 16, (void*)gen_handler, &g_tramp_gen);
  if (r) return r;
  r = hook((unsigned char*)(uintptr_t)(exe_base + DATE_RVA), SIG_DATE, 17, (void*)date_handler, &g_tramp_date);
  if (r) return r + 10;
  r = hook((unsigned char*)(uintptr_t)(exe_base + GROUP_RVA), SIG_GROUP, 14, (void*)group_handler, &g_tramp_group);
  if (r) return r + 20;
  /* The watch hooks are optional: a mismatch costs the diagnostics, never the install. */
  if (!memcmp((void*)(uintptr_t)(exe_base + ADDCLUB_RVA), SIG_ADDCLUB, 17) &&
      !memcmp((void*)(uintptr_t)(exe_base + CLRCLUB_RVA), SIG_CLRCLUB, 16) &&
      !memcmp((void*)(uintptr_t)(exe_base + SETCOUNT_RVA), SIG_SETCOUNT, 16) &&
      !hook((unsigned char*)(uintptr_t)(exe_base + ADDCLUB_RVA), SIG_ADDCLUB, 17, (void*)addclub_handler, &g_tramp_add) &&
      !hook((unsigned char*)(uintptr_t)(exe_base + CLRCLUB_RVA), SIG_CLRCLUB, 16, (void*)clrclub_handler, &g_tramp_clr) &&
      !hook((unsigned char*)(uintptr_t)(exe_base + SETCOUNT_RVA), SIG_SETCOUNT, 16, (void*)setcount_handler, &g_tramp_set))
    logf("fl26swiss: watching European club lists (add@%llx clear@%llx set@%llx)",
         (unsigned long long)(exe_base + ADDCLUB_RVA), (unsigned long long)(exe_base + CLRCLUB_RVA),
         (unsigned long long)(exe_base + SETCOUNT_RVA));
  else
    logf("fl26swiss: club-list watch NOT installed (signature)");
  if (!memcmp((void*)(uintptr_t)(exe_base + SEED_RVA), SIG_SEED, 15) &&
      !memcmp((void*)(uintptr_t)(exe_base + GDRAW_RVA), SIG_GDRAW, 16) &&
      !hook((unsigned char*)(uintptr_t)(exe_base + SEED_RVA), SIG_SEED, 15, (void*)seed_handler, &g_tramp_seed) &&
      !hook((unsigned char*)(uintptr_t)(exe_base + GDRAW_RVA), SIG_GDRAW, 16, (void*)gdraw_handler, &g_tramp_gdraw))
    logf("fl26swiss: league-phase entry hooks live (seeding@%llx draw@%llx)",
         (unsigned long long)(exe_base + SEED_RVA), (unsigned long long)(exe_base + GDRAW_RVA));
  else
    logf("fl26swiss: league-phase entry hooks NOT installed (signature)");
  if (!hook_or_chain((unsigned char*)(uintptr_t)(exe_base + SETCL_RVA), SIG_SETCL, 15, (void*)setcl_handler, &g_tramp_setcl))
    logf("fl26swiss: knockout entry live (set_clubs@%llx%s: top %d of the league phase)",
         (unsigned long long)(exe_base + SETCL_RVA), g_chained ? ", in front of another module's hook" : "", KO_N);
  else
    logf("fl26swiss: knockout entry NOT installed (signature)");
  if (!hook((unsigned char*)(uintptr_t)(exe_base + PROG_RVA), SIG_PROG, 15, (void*)prog_handler, &g_tramp_prog))
    logf("fl26swiss: Conference League hand-overs live (progression@%llx)", (unsigned long long)(exe_base + PROG_RVA));
  else
    logf("fl26swiss: Conference League hand-overs NOT installed (signature)");
  {
    unsigned char* td = (unsigned char*)(uintptr_t)(exe_base + TEARDOWN_RVA);
    int chained = td[0] == 0xFF && td[1] == 0x25;
    if (!hook_or_chain(td, SIG_TEARDOWN, 14, (void*)teardown_handler, &g_tramp_teardown))
      logf("fl26swiss: Conference League July teardown live (@%llx%s)", (unsigned long long)(uintptr_t)td,
           chained ? ", in front of another module's hook" : "");
    else
      logf("fl26swiss: Conference League July teardown NOT installed (signature)");
  }
  if (!hook((unsigned char*)(uintptr_t)(exe_base + DAYCHK_RVA), SIG_DAYCHK, 17, (void*)daychk_handler, &g_tramp_daychk))
    logf("fl26swiss: cup fill days live (day loop@%llx)", (unsigned long long)(exe_base + DAYCHK_RVA));
  else
    logf("fl26swiss: cup fill days NOT on the day loop (signature); the loader's tick only");
  {
    int cr = carry_install(exe_base);
    if (!cr) logf("fl26swiss: split points carry live (key switch@%llx)", (unsigned long long)(exe_base + CARRY_SITE_RVA));
    else logf("fl26swiss: split points carry NOT installed (%d)", cr);
  }
  {
    int cr = rk_install(exe_base);
    if (!cr) logf("fl26swiss: splits by competition live (9 phase lookups + the group finder): two splits in one country");
    else logf("fl26swiss: splits by competition NOT fully installed (%d)", cr);
  }
  {
    int meet = -1;
    int cr = cont_install(exe_base, &meet);
    if (!cr) logf("fl26swiss: board objective by continent live (18 calls of the owner's judges)");
    else logf("fl26swiss: board objective by continent NOT installed (%d)", cr);
    if (!cr && !meet) logf("fl26swiss: board objective -- the meeting names the same cup (2 calls)");
    else if (!cr) logf("fl26swiss: board objective -- the meeting's text NOT patched (%d): it may name the Champions League", meet);
  }
  if (!hook((unsigned char*)(uintptr_t)(exe_base + CURPH_RVA), SIG_CURPH, 15, (void*)curph_handler, &g_tramp_curph))
    logf("fl26swiss: phase order live (current phase@%llx: league, play-off, knockout)",
         (unsigned long long)(exe_base + CURPH_RVA));
  else
    logf("fl26swiss: phase order NOT installed (signature)");
  if (!hook((unsigned char*)(uintptr_t)(exe_base + PHKIND_RVA), SIG_PHKIND, 15, (void*)phkind_handler, &g_tramp_phkind))
    logf("fl26swiss: knockout item guard live (phase by kind@%llx)", (unsigned long long)(exe_base + PHKIND_RVA));
  else
    logf("fl26swiss: knockout item guard NOT installed (signature)");
  if (!hook((unsigned char*)(uintptr_t)(exe_base + TXTGET_RVA), SIG_TXTGET, 14, (void*)txtget_handler, &g_tramp_txtget))
    logf("fl26swiss: League Phase text live (@%llx)", (unsigned long long)(exe_base + TXTGET_RVA));
  else
    logf("fl26swiss: League Phase text NOT installed (signature)");
  if (!hook((unsigned char*)(uintptr_t)(exe_base + PHNAME_RVA), SIG_PHNAME, 17, (void*)phname_handler, &g_tramp_phname))
    logf("fl26swiss: play-off names live (@%llx)", (unsigned long long)(exe_base + PHNAME_RVA));
  else
    logf("fl26swiss: play-off names NOT installed (signature)");
  if (!hook((unsigned char*)(uintptr_t)(exe_base + GSTAGE_RVA), SIG_GSTAGE, 19, (void*)gstage_handler, &g_tramp_gstage))
    logf("fl26swiss: group stage item live (@%llx)", (unsigned long long)(exe_base + GSTAGE_RVA));
  else
    logf("fl26swiss: group stage item NOT installed (signature)");
  if (!hook((unsigned char*)(uintptr_t)(exe_base + CATREGS_RVA), SIG_CATREGS, 15, (void*)catregs_handler, &g_tramp_catregs))
    logf("fl26swiss: pre-round ties out of Competition Info (@%llx)", (unsigned long long)(exe_base + CATREGS_RVA));
  else
    logf("fl26swiss: pre-round ties in Competition Info NOT installed (signature)");

  if (!hook((unsigned char*)(uintptr_t)(exe_base + LIBQ_TLIST_RVA),
            SIG_LIBQ_TLIST, 16,
            (void*)libq_tlist_handler,
            &g_tramp_libq_tlist))
    logf("fl26swiss: Libertadores qualifying tie-list routing live (@%llx)",
         (unsigned long long)(exe_base + LIBQ_TLIST_RVA));
  else
    logf("fl26swiss: Libertadores qualifying tie-list routing NOT installed (signature)");

  if (!hook((unsigned char*)(uintptr_t)(exe_base + LIBQ_KOBUILD_RVA),
            SIG_LIBQ_KOBUILD, 16,
            (void*)libq_kobuild_handler,
            &g_tramp_libq_kobuild))
    logf("fl26swiss: Libertadores qualifying pages F1/F2/F3 live (@%llx)",
         (unsigned long long)(exe_base + LIBQ_KOBUILD_RVA));
  else
    logf("fl26swiss: Libertadores qualifying pages F1/F2/F3 NOT installed (signature)");

  {
    int pf = libq_pgfirst_install(exe_base);
    if (!pf)
      logf("fl26swiss: Libertadores qualifying page after a match live (@%llx)",
           (unsigned long long)(exe_base + LIBQ_PGFIRST_RVA));
    else
      logf("fl26swiss: Libertadores qualifying page after a match NOT installed (%d)",
           pf);
  }

  {
    int lp = libq_pgloop_install(exe_base);

    if (!lp)
      logf("fl26swiss: Libertadores qualifying page breaks live (@%llx)",
           (unsigned long long)(exe_base + LIBQ_PGLOOP_RVA));
    else
      logf("fl26swiss: Libertadores qualifying page breaks NOT installed (%d)",
           lp);
  }
  {
    int sp = single_popage_patch(exe_base);
    if (!sp) logf("fl26swiss: one-match pre-round post-match page routing live (@%llx)",
                  (unsigned long long)(exe_base + SINGLE_POPAGE_RVA));
    else logf("fl26swiss: one-match pre-round post-match page routing NOT installed (%d)", sp);
  }

  {
    int lr = libq_skipph_install(exe_base);

    if (!lr)
      logf("fl26swiss: technical Libertadores qualifying competition hidden (@%llx)",
           (unsigned long long)(exe_base + LIBQ_SKIPPH_RVA));
    else
      logf("fl26swiss: technical Libertadores qualifying competition hide NOT installed (%d)",
           lr);
  }
  if (!hook((unsigned char*)(uintptr_t)(exe_base + LBBUILD_RVA), SIG_LBBUILD, 14, (void*)lbbuild_handler, &g_tramp_lbbuild))
    logf("fl26swiss: cup scorers kept through the game's list builds (@%llx)", (unsigned long long)(exe_base + LBBUILD_RVA));
  else
    logf("fl26swiss: cup scorers hook NOT installed (signature)");
  if (!hook_or_chain((unsigned char*)(uintptr_t)(exe_base + STAND_RVA), SIG_STAND, 15, (void*)stand_handler, &g_tramp_stand))
    logf("fl26swiss: standings row guard live (@%llx)", (unsigned long long)(exe_base + STAND_RVA));
  else
    logf("fl26swiss: standings row guard NOT installed (signature)");
  if (!memcmp((void*)(uintptr_t)(exe_base + GNAME_RVA), SIG_GNAME, 15) &&
      !hook((unsigned char*)(uintptr_t)(exe_base + GNAME_RVA), SIG_GNAME, 15, (void*)gname_handler, &g_tramp_gname))
    logf("fl26swiss: league-phase header live (@%llx)", (unsigned long long)(exe_base + GNAME_RVA));
  else
    logf("fl26swiss: league-phase header NOT installed (signature)");
  if (!hook((unsigned char*)(uintptr_t)(exe_base + MDLABEL_RVA), SIG_MDLABEL, 17, (void*)mdlabel_handler, &g_tramp_mdlabel))
    logf("fl26swiss: league-phase matchday labels live (@%llx: 1..8, not 1..16)", (unsigned long long)(exe_base + MDLABEL_RVA));
  else
    logf("fl26swiss: league-phase matchday labels NOT installed (signature)");
  {
    int pr = po_install(exe_base);
    if (!pr) logf("fl26swiss: our play-offs on Match Results live (subclass@%llx, title@%llx)",
                  (unsigned long long)(exe_base + POSEL_CALL), (unsigned long long)(exe_base + POTTL_SITE));
    else logf("fl26swiss: our play-offs on Match Results NOT installed (%d)", pr);
    int tr = ttl_install(exe_base);
    if (!tr) logf("fl26swiss: qualifying round names in match titles live (@%llx, @%llx)",
                  (unsigned long long)(exe_base + TTL_CALL1), (unsigned long long)(exe_base + TTL_CALL2));
    else logf("fl26swiss: qualifying round names in match titles NOT installed (%d)", tr);
    int ar = awgate_install(exe_base);
    if (!ar) logf("fl26swiss: Individual Titles / Team of the Competition for our cup phases live (@%llx)",
                  (unsigned long long)(exe_base + AWGATE_CALL));
    else logf("fl26swiss: Individual Titles / Team of the Competition gate NOT installed (%d)", ar);
  }
  {
    int gr = grp_install(exe_base);
    if (!gr) logf("fl26swiss: League Phase instead of Group A / Group stage live (%d sites)", GRP_N);
    else logf("fl26swiss: League Phase instead of Group A NOT installed (%d)", gr);
  }
  {
    int rx = rix_install(exe_base);
    if (rx) logf("fl26swiss: team-to-league lookup index NOT installed (%d)", rx);
  }
  {
    int kl = kolist_install(exe_base);
    if (!kl) logf("fl26swiss: Competition Info knockouts as a list live (Conference League, world-built continental cups; call@%llx)",
                  (unsigned long long)(exe_base + KOLIST_CALL));
    else logf("fl26swiss: Competition Info knockouts as a list NOT installed (%d); they stay brackets", kl);
    int why = 0, kt = kotext_install(exe_base, &why);
    logf("fl26swiss: Round of 16 names %s (schedule line %s, match title / Competition Info list %s%s)",
         kt == 3 ? "live" : kt ? "partly live" : "NOT installed", kt & 1 ? "yes" : "no", kt & 2 ? "yes" : "no",
         why == 2 ? "; a site was not the one expected" : why == 3 ? "; no page in reach" : why == 4 ? "; VirtualProtect" : "");
    if (!hook((unsigned char*)(uintptr_t)(exe_base + CIMENU_RVA), SIG_CIMENU, 17, (void*)ci_menu_handler, &g_tramp_cimenu)
        && !hook((unsigned char*)(uintptr_t)(exe_base + CISEL_RVA), SIG_CISEL, 20, (void*)ci_sel_handler, &g_tramp_cisel))
      logf("fl26swiss: Competition Info item per qualifying round live (menu@%llx, choice@%llx)",
           (unsigned long long)(exe_base + CIMENU_RVA), (unsigned long long)(exe_base + CISEL_RVA));
    else
      logf("fl26swiss: Competition Info item per qualifying round NOT installed (signature)%s",
           g_tramp_cimenu ? " -- menu hooked, choice not: extra items open the native item's page" : "");
  }
  u10_install();
  lppage_install(exe_base);
  mp_install();
  if (!cupsel_install(exe_base))
    logf("fl26swiss: Cup mode list live (no league phase of 36 in Kick Off > Cup)");
  else
    logf("fl26swiss: Cup mode list NOT installed (vtable slot)");
  logf("fl26swiss: hooks live (schedule@%llx dates@%llx) for %d regulation(s)",
       (unsigned long long)(exe_base + GEN_RVA), (unsigned long long)(exe_base + DATE_RVA), nregs);
  return 0;
}

/* copy and clear the pending log text; returns bytes copied */
__declspec(dllexport) int fl26_swiss_log(char* out, int cap)
{
  if (g_log_lost && g_log_len + 128 < (int)sizeof g_log) {
    uint32_t lost = g_log_lost; g_log_lost = 0;
    logf("fl26swiss: %u log line(s) before this point went to fl26swiss-overflow.log -- the log was full and not drained", (unsigned)lost);
  }
  int n = g_log_len; if (n > cap - 1) n = cap - 1; if (n < 0) n = 0;
  if (n < g_log_len) { int k = n; while (k > 0 && g_log[k - 1] != '\n') k--; if (k > 0) n = k; }  /* whole lines only */
  memcpy(out, g_log, n); out[n] = 0;
  if (n < g_log_len) { memmove(g_log, g_log + n, g_log_len - n); g_log_len -= n; } else g_log_len = 0;
  return n;
}

/* calls seen, schedules written, refused, cells out of range, calendars written */
__declspec(dllexport) void fl26_swiss_stats(uint32_t* out5)
{
  for (int i = 0; i < 5; i++) out5[i] = g_stat[i];
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID r) { (void)h;(void)reason;(void)r; return TRUE; }
