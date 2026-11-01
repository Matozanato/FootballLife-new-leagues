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
  if (g_log_len + n + 1 >= (int)sizeof g_log) { g_log_lost++; return; }
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
   competition i % 3 at stage i / 3, 3..5 the third qualifying rounds, 6..8 the second; 0..2,
   the play-offs, are 2, 188 and 189 and stay 0 here. */
static uint16_t g_qreg[9];
static int q_added(uint16_t id)          /* the round a regulation or a tie of it is, -1 none */
{
  for (int i = 3; i < 9; i++) if (g_qreg[i] && (id & 0x3ff) == g_qreg[i] && (id >> 10) <= 8) return i;
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
static void gt_report(const char* when);
static void cer_guard_end(int d);
static void borrow_day_check(void);
/* 30.10.: each dated-like regulation's last day (its final), for the trophy ceremony */
typedef struct { uint16_t reg; int day; } dl_last_t;
static dl_last_t g_dl_last[32];
static int g_ndl_last = 0;
static void dl_last_note(uint16_t reg, int day)
{
  for (int i = 0; i < g_ndl_last; i++) if (g_dl_last[i].reg == reg) { g_dl_last[i].day = day; return; }
  if (g_ndl_last < 32) { g_dl_last[g_ndl_last].reg = reg; g_dl_last[g_ndl_last].day = day; g_ndl_last++; }
}
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
 * of the table array and so the number of headers come from the live lea at 0x14158df91
 * (fl26hdr255 moves the array behind 255 headers). */
static int table_of_clubs(const unsigned char* t, unsigned rows, const uint32_t* want, unsigned nwant);
/* the pool's tables: 600 from the table base on, but fl26hdr255 moves the base behind 255
   headers and the member after the pool stays at 0x39a8f0, so it holds 595 there */
static unsigned pool_tables(uint32_t arr)
{
  unsigned n = arr < 0x39a8f0 ? (0x39a8f0 - arr) / 0x187c : 0;
  return n > 600 ? 600 : n;
}
/* the same walk for any table: rows in lo..hi and, given want, only clubs of want (a group's
   table of an earlier season holds other clubs: B169, 20.10.) */
static unsigned char* season_table_x(uint16_t reg, unsigned lo, unsigned hi, const uint32_t* want, unsigned nwant,
                                     unsigned* year_out)
{
  unsigned char* lea = (unsigned char*)(uintptr_t)(g_base + 0x158df91);
  if (lea[0] != 0x49 || lea[1] != 0x8d || lea[2] != 0x82) return 0;
  uint32_t arr; memcpy(&arr, lea + 3, 4);
  unsigned nh = arr / 0xb4, nt = pool_tables(arr);
  if (arr % 0xb4 || nh < 100 || nh > 255) return 0;
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
  unsigned char* lea = (unsigned char*)(uintptr_t)(g_base + 0x158df91);
  if (lea[0] != 0x49 || lea[1] != 0x8d || lea[2] != 0x82) return 0;
  uint32_t arr; memcpy(&arr, lea + 3, 4);
  unsigned nh = arr / 0xb4, nt = pool_tables(arr);
  if (arr % 0xb4 || nh < 100 || nh > 255) return 0;
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

#define MAX_CAL_SCUPS 32
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
  if (r == 1 && cwc_world()) return cwc_setcl(id, list, flag);
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
  for (unsigned id = 1; id < 600; id++) {
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
static unsigned char* team_array(uint32_t* n)
{
#ifdef FL26_RCAL_TEST
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
#ifndef TODAY_OFF   /* the -calendar set (0.2.0): the unit tail moved by 0x2cebc8; -DTODAY_OFF=... for an older set */
#define TODAY_OFF  0x19115e4
#endif
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
  return blk ? *(uint16_t*)(blk + TODAY_OFF) : -1;
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
static int abs_day(void)
{
  int d = today();
  if (d < 0) return d;
  if (g_last_day >= 0 && d < g_last_day) {
    if (d + 182 < g_last_day && g_last_day >= 300) g_year_off += 365;     /* New Year */
    else {
      g_year_off += 730; g_timeline++;
      g_new_career = 0; g_day_ticked = 0; g_first_day = -1;
      g_built_gdate = -1; g_built_stored = 0;
    }
  }
  else if (g_last_day >= 0 && d > g_last_day + 182 && g_year_off >= 365) g_year_off -= 365;
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
#define ACCESS_MAX 256
static access_t g_access_buf[ACCESS_MAX];
static const access_t* g_access = ACCESS;
static size_t g_naccess = NACCESS;
static int g_access_cfg = 0;
#define FINAL_MAX 40
typedef struct { uint16_t reg; uint16_t n; int day; uint32_t club[FINAL_MAX]; } final_t;
/* 64 until B160: a world of 86 leagues filled it by day 176, and the leagues kept after that
   (Vietnam, Jordan, Kuwait, Bahrain, Oman) sent their clubs by the live table */
#define FINAL_N 256
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
static cupwin_t g_cupwin[32]; static int g_ncupwin = 0;
/* Synthetic retained-result key: no real regulation uses this value. */
#define CUPWIN_LIB_RUNNER 0xfffeu
#define FUTVE_RUNNER 0xf000u        /* fase 5: | a Liga FUTVE final's knockout: its loser */

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
static uint32_t futve_cont_club(uint16_t reg, int rank, const char** how);
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
#define BUILD_DAY 210   /* the day-216 rollover builds the new season; nothing after this is final */
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
        if (!lw && g_ncupwin < 32) { lw = &g_cupwin[g_ncupwin++]; lw->reg = libko; }
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
        if (!rw && g_ncupwin < 32) {
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
      if (!w) { if (g_ncupwin >= 32) continue; w = &g_cupwin[g_ncupwin++]; w->reg = reg; }
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
static final_t g_seed[64]; static int g_nseed = 0;

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
  if (!f) { if (g_nseed >= 64) return 0; f = &g_seed[g_nseed++]; f->reg = source; }
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
    if ((t[0x41c] & 0x7f) != ASSOC_POOL_LATAM) continue;
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
  if (!f) { if (g_nseed >= 64) return 0; f = &g_seed[g_nseed++]; f->reg = reg; }
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
  { const char* h; uint32_t fc = futve_cont_club(reg, rank, &h); if (fc) { *from_table = 1; return fc; } }
  final_t* f = final_of(reg);
  int d = abs_day();
  /* B312: a kept table, the first season's order and the list can hold a club at a row the team
     array has since given to another (canon_list) */
  if (f && rank <= f->n && d >= f->day && d - f->day < keep) { *from_table = 1; return canon_club(f->club[rank - 1]); }
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
static uint32_t g_first[3][48]; static unsigned g_nfirst[3];
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
 *     one batch).  A round is filled on the days between the round before it and its first leg
 *     (q_fill); the season is built on day 216, so nothing is filled before 217.
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
 * The eight strongest squads are seeded and listed second, at home in the second leg; the other
 * eight are drawn against them, two clubs of one league kept apart where the draw allows. */
#define Q_N 16
#define NQ 3
#define NQR 9
typedef struct { uint16_t reg; uint8_t comp, to_win, to_lose; const char* name; } qcup_t;
static const qcup_t QCUPS[NQ] = {
  { 2,       UCLQ,  UCL,  UEL,  "Champions League" },
  { UEL_PO,  UELQ,  UEL,  UECL, "Europa League" },
  { UECL_PO, UECLQ, UECL, 0xff, "Conference League" },
};
static const char* const QSTAGE[3] = { "play-off", "third qualifying round", "second qualifying round" };
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
static uint32_t g_qr_leg[3][2]; static int g_qr_sy = -1;
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
    /* FL27: their league phase plays its first matchday on 250 (7 September 2026) and our six
       weeks put the play-off on 251 and 258, the same days as their first two matchdays, for
       clubs that are in both (31.10.). Three weeks instead, Tuesday and Thursday, from the first
       Tuesday after the build (217 is the first day filled): the play-off done by 241 */
    mon = 218;
    while (wday_in(mon, sy) != 2) mon++;   /* 0 = Sunday */
    mon--;
    for (int st = 2; st >= 0; st--) { g_qr_leg[st][0] = mon + 1; g_qr_leg[st][1] = mon + 3; mon += 7; }
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
static uint32_t g_q[NQR][Q_N]; static unsigned g_nq[NQR], g_nnew[NQR]; static int g_q_day = -100000, g_qmask = 0;
static how_t g_qhow[NQR][Q_N];
static unsigned char g_qdrawn[NQR];
static uint32_t g_qwin[NQR][Q_N / 2], g_qlose[NQR][Q_N / 2];
static how_t g_qwhow[NQR][Q_N / 2], g_qlhow[NQR][Q_N / 2];
#define QNAME(i) QCUPS[(i) % NQ].name, QSTAGE[(i) / NQ]
static uint16_t q_reg(int i) { return i < NQ ? QCUPS[i].reg : g_qreg[i]; }

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
  return 0;
}
/* round i is played in this world: its places are listed and its regulations exist -- a
   qualifying round only in front of its competition's play-off */
static int q_world_p(int i)
{
  if (!g_access_on || !q_reg(i) || !q_listed(i)) return 0;
  if (i >= NQ && !q_world_p(i % NQ)) return 0;
  return get_rec(q_reg(i)) && get_rec(q_tie_of(i, Q_N / 2 - 1));
}
/* why round i is not played, once a season (GitHub #128: a modpack career had no qualifying at
   all, and nothing in the log said which test failed) */
static void q_why(int i)
{
  static int said[NQR] = { -1, -1, -1, -1, -1, -1, -1, -1, -1 };
  int y = season_year();
  if (said[i] == y) return;
  said[i] = y;
  const char* why = !g_access_on ? "the access list is off" : !q_reg(i) ? "no regulation named for it"
                  : !q_listed(i) ? "no place of the access list is in it"
                  : i >= NQ && !q_world_p(i % NQ) ? "its play-off is not played"
                  : !get_rec(q_reg(i)) ? "its regulation is not found" : "its last tie is not found";
  logf("fl26swiss: %s %s not played this season: %s (reg %u, tie %u, day %d)", QNAME(i), why,
       (unsigned)q_reg(i), (unsigned)q_tie_of(i, Q_N / 2 - 1), today());
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
  return mask >> j & 1 ? j : -2;
}
static unsigned q_room(int mask, int i)
{
  unsigned n = Q_N;
  for (int j = 0; j < NQR; j++)
    if (j != i && (mask >> j & 1) && (q_up(mask, j) == i || q_down(mask, j) == i)) n -= Q_N / 2;
  return n;
}
/* the first leg of round i, and the first day it is filled on: after the last second leg of the
   rounds that feed it, never before the season's build on day 216 (reg 2 alone, in a new career
   that starts before it: from 205) */
static uint32_t q_first_leg(int i) { return qr_day(i / NQ, 0); }
static uint32_t q_fill_from(int mask, int i)
{
  uint32_t d = 0;
  for (int j = 0; j < NQR; j++)
    if (j != i && (mask >> j & 1) && (q_up(mask, j) == i || q_down(mask, j) == i)) {
      /* and after the second leg the round before had until 0.2.0 (225, 236): a save of then,
         its rounds dated the old way, is not filled before they are over */
      uint32_t e = qr_day(j / NQ, 1) + 1, old = j / NQ == 2 ? 226 : 237;
      if (e < old && !g_native_uefa) e = old;      /* FL27: no save of then; its weeks are shorter */
      if (e > d) d = e;
    }
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
  uint32_t used[3 * FIELD + NQR * Q_N + 8]; unsigned nused = 0; int tables = 0, orders = 0, gaps = 0, listed = 0, held = 0;
  int on[NQR]; unsigned room[NQR];
  for (int i = 0; i < NQR; i++) { on[i] = q && (mask >> i & 1); room[i] = on[i] ? q_room(mask, i) : 0; }
  unsigned cap[3] = { FIELD, FIELD, FIELD };
  for (int p = 0; p < NQ; p++) {
    if (!on[p]) continue;
    cap[QCUPS[p].to_win] -= Q_N / 2;
    if (QCUPS[p].to_lose != 0xff) cap[QCUPS[p].to_lose] -= Q_N / 2;
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
    uint32_t qt[NQR][Q_N]; int filled[NQR], kept = 0;
    for (int i = 0; i < NQR; i++) {
      filled[i] = on[i] && q_matches(i) > 0;
      for (int k = 0; k < Q_N / 2 && filled[i]; k++) {
        unsigned char* t = get_rec(q_tie_of(i, k));
        if (!t || rec_count(t) != 2) filled[i] = 0;
        else { qt[i][2 * k] = rec_clubs(t)[0]; qt[i][2 * k + 1] = rec_clubs(t)[1]; }
      }
    }
    for (int i = 0; i < NQR; i++) {
      if (!filled[i]) continue;
      for (int n = 0; n < Q_N; n++) {
        uint32_t c = qt[i][n];
        if (!(c >> 14) || has_club(used, nused, c)) continue;
        used[nused++] = c;
        int fed = 0;
        for (int j = 0; j < NQR && !fed; j++)
          if (j != i && filled[j] && (q_up(mask, j) == i || q_down(mask, j) == i)) fed = has_club(qt[j], Q_N, c);
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
  #define QSLOT(p, out) do { out = -1; for (int s_ = 0; s_ < 3 && out < 0; s_++) { int i_ = (p) + NQ * s_; \
      if (on[i_] && g_nq[i_] < room[i_]) out = i_; } } while (0)
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
    if (qp >= 0) { QSLOT(qp, qi); if (qi < 0) continue; }
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
  /* top-up: the next free positions of the big five, the league with the fewest clubs on the
     list first (ties in this order), so a place a holder left does not go back to its own country
     and no association crowds a league phase past what the draw can keep apart */
  static const uint16_t RESERVE[5] = { R_ENG, R_ESP, R_ITA, R_GER, R_FRA };
  int topped = 0, lifted = 0;
  /* each competition, then its rounds from the play-off down: -1 - k is league phase k */
  static const int ORDER[NQ + NQR] = { -1, 0, 3, 6, -2, 1, 4, 7, -3, 2, 5, 8 };
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
  int str[Q_N]; unsigned idx[Q_N];
  for (unsigned i = 0; i < Q_N; i++) { idx[i] = i; str[i] = blk ? club_strength(blk, Q[i]) : 0; }
  for (unsigned i = 1; i < Q_N; i++)               /* strongest first, stable */
    for (unsigned j = i; j > 0 && str[idx[j - 1]] < str[idx[j]]; j--) { unsigned t = idx[j]; idx[j] = idx[j - 1]; idx[j - 1] = t; }
  unsigned* seed = idx; unsigned* un = idx + Q_N / 2;
  for (unsigned i = Q_N / 2 - 1; i > 0; i--) { unsigned j = q_rand(i + 1), t = un[i]; un[i] = un[j]; un[j] = t; }
  #define QLG(x) (QH[x].reg)
  for (unsigned k = 0; k < Q_N / 2; k++) {        /* two clubs of one league apart */
    if (!QLG(un[k]) || QLG(un[k]) != QLG(seed[k])) continue;
    for (unsigned j = 0; j < Q_N / 2; j++) {
      if (j == k || QLG(un[j]) == QLG(seed[k]) || (QLG(un[k]) && QLG(un[k]) == QLG(seed[j]))) continue;
      unsigned t = un[k]; un[k] = un[j]; un[j] = t;
      break;
    }
  }
  #undef QLG
  uint32_t c[Q_N]; how_t h[Q_N];
  for (unsigned k = 0; k < Q_N / 2; k++) {
    c[2 * k] = Q[un[k]]; h[2 * k] = QH[un[k]];
    c[2 * k + 1] = Q[seed[k]]; h[2 * k + 1] = QH[seed[k]];
  }
  memcpy(Q, c, sizeof c); memcpy(QH, h, sizeof h);
}
static void q_draw_log(int i)
{
  q_draw(i);
  g_qdrawn[i] = 1;
  for (unsigned k = 0; k < Q_N / 2; k++)
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
  if (g_qmask && ad >= g_q_day && ad - g_q_day < 60) return g_qmask;
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
    if (room == Q_N) q_draw_log(i);
    else logf("fl26swiss: %s %s -- %u new club(s), the other %u from the rounds before it", QNAME(i), room, Q_N - room);
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
  for (int k = 0; k < Q_N / 2; k++) { int x = ccup_matches(q_tie_of(p, k)); if (x > 0) m += x; }
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
  uint32_t pr[Q_N]; how_t ph[Q_N]; int ties = 1, nodec = 0;
  /* the added rounds keep last summer's (or February's) two clubs in each tie until refilled:
     their ties count only with this summer's matches (the July teardown deletes the old ones) */
  if (p && q_matches(p) <= 0) ties = 0;
  for (int k = 0; k < Q_N / 2 && ties; k++) {
    unsigned char* t = get_rec(q_tie_of(p, k));
    if (!t || rec_count(t) != 2) ties = 0;
    else { pr[2 * k] = rec_clubs(t)[0]; pr[2 * k + 1] = rec_clubs(t)[1]; }
  }
  if (ties) {
    int same = g_nq[p] == Q_N;
    for (int i = 0; i < Q_N && same; i++) same = has_club(g_q[p], Q_N, pr[i]);
    if (!same) {                                    /* after a restart, or the game's own clubs */
      logf("fl26swiss: %s %s -- the ties hold clubs this session did not draw; taken as they are", QNAME(p));
      memcpy(g_q[p], pr, sizeof pr); g_nq[p] = Q_N; g_qdrawn[p] = 1;
      for (int i = 0; i < Q_N; i++) { g_qhow[p][i].reg = q_reg(p); g_qhow[p][i].rank = (uint8_t)(i + 1); }
    }
    for (int i = 0; i < Q_N; i++) {                 /* where each came from, in the ties' order */
      ph[i].reg = q_reg(p); ph[i].rank = 0;
      for (int j = 0; j < Q_N; j++) if (same_club(g_q[p][j], pr[i])) { ph[i] = g_qhow[p][j]; break; }
    }
  } else {
    if (!q_complete(p)) return 0;
    memcpy(pr, g_q[p], sizeof pr); memcpy(ph, g_qhow[p], sizeof ph);
    logf("fl26swiss: %s %s -- the ties were never filled (not played); the seeded clubs go through", QNAME(p));
  }
  char wto[96], lto[96];
  q_dest(p, 0, wto, sizeof wto); q_dest(p, 1, lto, sizeof lto);
  for (int k = 0; k < Q_N / 2; k++) {
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
  return 1;
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
    for (int k = 0; k < Q_N / 2 && g_nq[i] < Q_N; k++) {
      g_qhow[i][g_nq[i]] = win ? g_qwhow[j][k] : g_qlhow[j][k];
      g_q[i][g_nq[i]++] = win ? g_qwin[j][k] : g_qlose[j][k];
    }
  }
  if (g_nq[i] < Q_N) {
    logf("fl26swiss: %s %s -- only %u club(s); not played", QNAME(i), g_nq[i]);
    g_nq[i] = g_nnew[i];
    return 0;
  }
  q_draw_log(i);
  return 1;
}
/* the winners into their competition, the losers into the one below: the Champions League's
   play-off first, so each list reads direct entrants, then the play-off above's losers, then its
   own play-off's winners */
static void q_place(int mask)
{
  for (int p = 0; p < NQ; p++) {
    if (!(mask >> p & 1)) continue;
    for (int k = 0; k < Q_N / 2; k++) {
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
  return 0;
}
static int futve_cal(void);
static uint16_t g_tl_total;
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
    /* fase 4 (31.10., Felix): a January-December Liga FUTVE's first season (no final table kept
       yet) sends nobody to the Libertadores -- the pool clubs keep those places; from the second
       season the accumulated table of the year before does */
    if (futve_cal() && g_tl_total && a->reg == g_tl_total && !final_of(g_tl_total)) {
      static int said = 0;
      if (!said++) logf("fl26swiss: %s access -- reg %u: the Liga FUTVE's first season, no final table yet; its places stay with the pool",
                        CONT_NAME[a->comp - LIB], (unsigned)a->reg);
      continue;
    }
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
}
/* The league slot in +0x41c: the low 7 bits, or the whole byte when fl26slot7 is in (it moves
 * the flag in bit 7 to +0x41a and turns every `and 0x7f` reader into `and 0xff`; the first of
 * those readers, 0x140b08f74, says which). */
#define SLOT7_PROBE_RVA 0xb08f74
static int slot_of(const unsigned char* t)
{
  return t[0x41c] & (*(const unsigned char*)(uintptr_t)(g_base + SLOT7_PROBE_RVA) == 0xff ? 0xff : 0x7f);
}
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
  while (need && cap) {
    int best = -1, most = 0;
    for (int i = (int)n - 1; i >= 0; i--) {         /* backwards: a league's last listed first */
      if (out[i]) continue;
      int cnt = 0;
      for (size_t j = 0; j < n; j++) cnt += !out[j] && key[j] == key[i];
      if (cnt > most) { most = cnt; best = i; }
    }
    if (best < 0) break;
    out[best] = 1;
    uint32_t c = list->b[best];
    const how_t* h = 0;
    uint32_t to = cont_map_one(k, c, list->b, n, &h, id);
    if (!to) break;
    list->b[best] = to; need--; cap--; done++;
    logf("fl26swiss:   %s: reg %u %s %u -> %08x, in place of %08x (slot %d, %d of its league in the round)",
         CONT_NAME[k], h ? (unsigned)h->reg : 0u, h && !h->rank ? "winner" : "position", h ? (unsigned)h->rank : 0u,
         to, c, key[best], most);
  }
  if (need) logf("fl26swiss: %s (reg %u) -- %u place(s) of ours left out: all but two places of the round are given away already",
                 CONT_NAME[k], (unsigned)id, need);
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
    for (size_t i = 0; i < n && no < 64; i++) {
      uint32_t c = list->b[i];
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
    uint32_t to = cont_map_one(k, c, list->b, n, &h, id);
    if (!to) { left++; continue; }
    list->b[i] = to; put++;
    if (h) logf("fl26swiss:   %s: reg %u %s %u -> %08x, in place of pool club %08x", CONT_NAME[k],
                (unsigned)h->reg, h->rank ? "position" : "winner", (unsigned)h->rank, to, c);
  }
  if ((comp == LIB || comp == LIBQ) && id < 1024)
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
  if (!blk || club_slot(blk, club) != pool) return 0;
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
#define CWC_KO  200
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
static final_t* phase_table(uint16_t reg)
{
  const split_t* s;
  int d = abs_day(), played;
  if (reg <= 175 || split_part(reg, &s) < 2) return 0;
  if (g_ptab_day == d && g_ptab.reg == reg) return g_ptab.n ? &g_ptab : 0;
  g_ptab_day = d; g_ptab.reg = reg; g_ptab.day = d;
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
  { uint32_t fc = futve_cont_club(reg, rank, how); if (fc) return fc; }
  if (assoc_source(reg)) {
    final_t* a = assoc_seed(reg);
    *how = "association squad strength";
    return a && rank >= 1 && rank <= a->n ? a->club[rank - 1] : 0;
  }
  final_t* f = final_of(reg);
  int d = abs_day();
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
#define MAX_CCUP_FWD 16  /* MAX_CCUP, defined with the continental cups below */
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

static char cwc_setcl(uint64_t id, u32vec* list, uint64_t flag)
{
  unsigned char* rec = get_rec(CWC_REG);
  unsigned char* g0 = get_rec(cwc_rep(0));
  size_t offered = list && list->b ? (size_t)(list->e - list->b) : 0;
  if (rec && g0 && rec_count(rec) == CWC_N && rec_count(g0)) {
    logf("fl26swiss: Club World Cup -- the game offered %u club(s) on day %d, but the 32 are already drawn; ignored",
         (unsigned)offered, today());
    return 1;
  }
  unsigned n = 0, gaps = 0, game = 0;
  const size_t POT3 = 24;
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
  if (n != CWC_N) {
    logf("fl26swiss: Club World Cup -- short field; the game's own entrants stand");
    return ((setclr_fn)(uintptr_t)g_tramp_setcl)(id, list, flag);
  }
  u32vec v = { g_cwc, g_cwc + CWC_N, g_cwc + CWC_N };
  char ok = ((setclr_fn)(uintptr_t)g_tramp_setcl)(id, &v, flag);
  run_flush();
  u32vec w = { g_cwc, g_cwc + CWC_N, g_cwc + CWC_N };
  ((gdraw_fn)(uintptr_t)(g_base + GDRAW_RVA))(CWC_REG, &w, 1);
  run_flush();
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

/* the group stage is over: winners and runners-up into the knockout, in the 2025 bracket */
static unsigned g_cwc_groups_done = 0;
static int cwc_progress(uint16_t r, void* started)
{
  if (r == CWC_REG) g_cwc_groups_done = (1u << CWC_GROUPS) - 1;
  else g_cwc_groups_done |= 1u << (((r >> 10) - 1) & 31);
  logf("fl26swiss: Club World Cup -- progression for reg %u on day %d (groups reported %02x)",
       (unsigned)r, today(), g_cwc_groups_done);
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

/* dates: borrow the World Cup's records, keep their rounds and kinds, move the days */
static uint64_t cwc_dates(uint16_t id, uint64_t reg, void* vec)
{
  int ko = id == CWC_KO;
  uint64_t rv = ((date_fn)(uintptr_t)g_tramp_date)((reg & ~(uint64_t)0xffff) | (ko ? R_WCKO : R_WCGROUP), vec);
  vec_t* v = (vec_t*)vec;
  size_t have = (v->b && v->e >= v->b) ? (size_t)(v->e - v->b) / sizeof(date_t) : 0;
  date_t* r = (date_t*)v->b;
  size_t want = ko ? 10 : 6;
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
 * first entries that fit its bracket.
 *
 * A league play-off (0.2.5, the Liga FUTVE) is the same machinery for a group stage filled in the
 * middle of a season: `gdays=` deals the entries into the groups in their order and dates them,
 * `adv=1` sends only the group winners to the final and `kolike=` gives its calendar. See the
 * comment at ccup_t and fl26_swiss_ccup_gdays / _adv / _kolike. */
#define MAX_CCUP 16      /* 8 until 0.2.0: CONCACAF and OFC cups next to league and pre-season cups */
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
/* A league play-off (0.2.5, the Liga FUTVE): gdays -- the group matchdays of its own (0: none, the
   cup keeps the borrowed Libertadores days); the groups are then dealt in the order of the entries
   instead of drawn (the world file writes A's clubs first: 1, 4, 5, 8 / 2, 3, 6, 7). adv -- only
   that many clubs of each group go through (only 1): the knockout is then the final, the better
   placed club of the regular phase first (at home in the match record). kolike -- the shipped cup
   whose calendar dates the knockout (0: the usual one), the Belgium Super Cup for a one-match
   final. The three come from fl26_swiss_ccup_gdays / _adv / _kolike, each called after
   fl26_swiss_ccup like the options above. */
typedef struct { uint16_t reg, ko, groups, n; uint16_t ereg[CCUP_MAX_ENTRY]; uint8_t erank[CCUP_MAX_ENTRY];
                 uint16_t ealt[CCUP_MAX_ENTRY];
                 uint8_t efrom[CCUP_MAX_ENTRY];   /* alt=: the first position of ealt to try */
                 uint16_t fill, national, nd, nc; uint16_t days[CCUP_MAX_DAYS]; uint32_t clubs[CCUP_MAX_ENTRY];
                 int filled_year;
                 uint16_t like;      /* 0.2.0: the shipped domestic cup whose shape and dates it takes, 0 = none */
                 uint8_t region;     /* 0.2.4 (B35): 1 + its CR_ day table, 0 = not worked out (ccup_region) */
                 unsigned rgen;      /* g_ccup_gen it was worked out under */
                 uint8_t cal;        /* South American February-December calendar (fl26_swiss_ccup_cal) */
                 uint16_t first[CCUP_MAX_ENTRY]; /* optional first-season winner fallbacks (Recopa) */
                 uint8_t adv, gnd;   /* the league play-off: advancers a group, own group days given */
                 uint16_t gdays[CCUP_MAX_DAYS]; /* gnd: the group matchdays */
                 uint16_t kolike;    /* the shipped cup whose calendar dates the knockout, 0 = none */
                 uint16_t src[2];    /* 0.2.5: a final of two cups -- their knockout regs, 0 = none */
               } ccup_t;
static ccup_t g_ccup[MAX_CCUP]; static int g_nccup = 0;
static uint32_t g_ccup_win[MAX_CCUP];  /* the champion ccup_final_note read, for a final of two cups */
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
/* 0: a champions' cup (Tuesdays), 1: the cup below (Wednesdays) */
static int ccup_tier(const ccup_t* c)
{
  for (int e = 0; e < c->n && e < CCUP_MAX_ENTRY; e++) if (c->erank[e] == 1) return 0;
  return 1;
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
  memset(g_ccup_win, 0, sizeof g_ccup_win);
  g_ccup_gen++;
  size_t p = 0;
  for (int i = 0; i < n && g_nccup < MAX_CCUP; i++) {
    ccup_t* c = &g_ccup[g_nccup];
    c->reg = v[p]; c->ko = v[p + 1]; c->groups = v[p + 2]; unsigned ne = v[p + 3]; p += 4;
    c->n = 0; c->fill = c->national = c->nd = c->nc = 0; c->filled_year = -1; c->like = 0; c->cal = 0;
    c->adv = 0; c->gnd = 0; c->kolike = 0;
    c->src[0] = c->src[1] = 0;
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

/* ---- a league play-off's own group days, advancers and knockout calendar (0.2.5) ----
 *
 * The three setters of the cup fields the comment at ccup_t describes. They are separate exports
 * like the options above, called after fl26_swiss_ccup, and each names its cup by the knockout id.
 * `gdays` (records {ko, count, day...}) turns the mode on: the groups are dealt in the order of the
 * entries and dated on those days. `adv` (records {ko, adv}) sends only the group winners to the
 * knockout; only 1 is supported. `kolike` (records {ko, shipped}) is the shipped cup whose calendar
 * dates the knockout, for a one-match final row copied from it. All three answer the number of cups
 * matched and name in the log any record they left out. */
__declspec(dllexport) int fl26_swiss_ccup_gdays(const uint16_t* v, int n)
{
  int got = 0;
  size_t p = 0;
  for (int i = 0; v && i < n; i++) {
    uint16_t ko = v[p], cnt = v[p + 1];
    const uint16_t* days = v + p + 2;
    p += 2 + (size_t)cnt;
    ccup_t* c = 0;
    for (int k = 0; k < g_nccup; k++) if (g_ccup[k].ko == ko) c = &g_ccup[k];
    if (!c || !c->groups) {
      logf("fl26swiss: cup %u -- group days for a cup that is not a group cup; left out", (unsigned)ko);
      continue;
    }
    c->gnd = 0;
    for (uint16_t j = 0; j < cnt && j < CCUP_MAX_DAYS; j++)
      if (days[j] >= 1 && days[j] <= 365) c->gdays[c->gnd++] = days[j];
    if (!c->gnd) {
      logf("fl26swiss: cup %u -- no usable group day; the mode stays off", (unsigned)ko);
      continue;
    }
    logf("fl26swiss: cup %u -- a league play-off: %u group day(s) of its own (%u..%u), groups in entry order",
         (unsigned)ko, (unsigned)c->gnd, (unsigned)c->gdays[0], (unsigned)c->gdays[c->gnd - 1]);
    got++;
  }
  return got;
}

__declspec(dllexport) int fl26_swiss_ccup_adv(const uint16_t* v, int n)
{
  int got = 0;
  for (int i = 0; v && i < n; i++) {
    uint16_t ko = v[2 * i], adv = v[2 * i + 1];
    ccup_t* c = 0;
    for (int k = 0; k < g_nccup; k++) if (g_ccup[k].ko == ko) c = &g_ccup[k];
    if (!c || !c->groups) {
      logf("fl26swiss: cup %u -- advancers for a cup that is not a group cup; left out", (unsigned)ko);
      continue;
    }
    if (adv != 1) {
      logf("fl26swiss: cup %u -- %u advancers a group: only one is supported; left out", (unsigned)ko, (unsigned)adv);
      continue;
    }
    c->adv = 1;
    logf("fl26swiss: cup %u -- only the winner of each group advances (the knockout is the final)", (unsigned)ko);
    got++;
  }
  return got;
}

__declspec(dllexport) int fl26_swiss_ccup_kolike(const uint16_t* v, int n)
{
  int got = 0;
  for (int i = 0; v && i < n; i++) {
    uint16_t ko = v[2 * i], shipped = v[2 * i + 1];
    ccup_t* c = 0;
    for (int k = 0; k < g_nccup; k++) if (g_ccup[k].ko == ko) c = &g_ccup[k];
    /* A straight knockout takes it too: the Final del FUTVE (263) was left on the Champions League
       knockout's calendar (7 records for days=167: "left as it is"), not on day 167. */
    if (!c || shipped < 1 || shipped > 175) {
      logf("fl26swiss: cup %u -- knockout calendar of reg %u for a cup not in the world file; left out",
           (unsigned)ko, (unsigned)shipped);
      continue;
    }
    c->kolike = shipped;
    logf("fl26swiss: cup %u -- its knockout dated as the shipped cup %u", (unsigned)ko, (unsigned)shipped);
    got++;
  }
  return got;
}

/* The final of two cups (0.2.5, the Liga FUTVE's Final del FUTVE): its field is the two champions of
   the cups whose knockouts are named, or none when they are the same club (the title is theirs and
   the match is not played). `src` records {ko, first cup, second cup}; only a knockout cup. */
__declspec(dllexport) int fl26_swiss_ccup_src(const uint16_t* v, int n)
{
  int got = 0;
  for (int i = 0; v && i < n; i++) {
    uint16_t ko = v[3 * i], a = v[3 * i + 1], b = v[3 * i + 2];
    ccup_t* c = 0;
    for (int k = 0; k < g_nccup; k++) if (g_ccup[k].ko == ko) c = &g_ccup[k];
    if (!c || c->groups || !a || !b) {
      logf("fl26swiss: cup %u -- the source cups %u and %u for a cup that is not a knockout; left out",
           (unsigned)ko, (unsigned)a, (unsigned)b);
      continue;
    }
    c->src[0] = a; c->src[1] = b;
    logf("fl26swiss: cup %u -- its field is the winners of cups %u and %u", (unsigned)ko, (unsigned)a, (unsigned)b);
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

  for (int pass = 0; pass < 2; pass++) {
    for (uint32_t i = 0; i < na; i++) {
      uint32_t c = team_at(a, i);
      if (c == 0xffffffffu || !(c >> 14) || (c >> 14) == 0x3ffff || (c & 0x3fff) != i) continue;
      c = canon_club(c);
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
    } else if (futve_cal() && g_tl_total && l->ereg[j] == g_tl_total && !final_of(g_tl_total)) {
      /* fase 5 (01.11.): the Liga FUTVE's first season sends nobody abroad, as its other places
         (cont_build, ccup entries): the slot goes to a club of a league with no place left there */
      static const uint16_t SUB[][2] = { {168, 16}, {168, 17}, {168, 18}, {168, 19}, {168, 20}, {67, 16},
                                         {30, 19}, {30, 20}, {30, 21}, {30, 22}, {30, 23}, {30, 24}, {29, 20} };
      for (size_t q = 0; q < sizeof SUB / sizeof SUB[0] && !club; q++) {
        uint32_t c = cwc_club(SUB[q][0], SUB[q][1], &how);
        if (c >> 14) c = canon_club(c);
        if (!(c >> 14) || has_club(l->club, n, c)) continue;
        if ((lib_stage || suda_first) && (lib_reserved_except(c, i) || (!l->poko && lib9_has(c)))) continue;
        int other = 0;
        for (int x = 0; x < g_nlpre && !other; x++) if (x != i && g_lpre[x].nclub) other = has_club(g_lpre[x].club, g_lpre[x].nclub, c);
        if (other) continue;
        club = c;
        logf("fl26swiss: pre-round %u -- the Liga FUTVE's first season: reg %u position %u goes to reg %u position %u (%08x)",
             (unsigned)l->reg, (unsigned)l->ereg[j], (unsigned)l->erank[j], (unsigned)SUB[q][0], (unsigned)SUB[q][1], c);
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
#define CS_TABBASE_IMM  0x158df94   /* u32 immediate: where the tables start (hdr patches move it) */
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
#define CS_TABN 600
typedef void (*cs_tabclr_fn)(unsigned char* t);
static const uint32_t CS_TABCLR_RVA[5] = { 0x14ff000, 0x14ff070, 0x14ff010, 0x14fefa0, 0x14ff090 };
static int table_pool_reap(const char* when)
{
  static uint8_t held[CS_TABN];
  int year = season_year();
  uint32_t tabbase = *(const uint32_t*)(uintptr_t)(g_base + CS_TABBASE_IMM);
  unsigned char* o = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
  unsigned char* std = o ? *(unsigned char**)(o + 0x78) : 0;
  if (!std || year < 1990 || tabbase < 0x4650 || tabbase > 0x10000 || tabbase % 0xb4) return -1;
  /* 595 behind fl26hdr255's headers: 600 from there read past the pool into the members after it */
  int ntab = (int)pool_tables(tabbase);
  memset(held, 0, sizeof held);
  for (uint32_t h = 0; h < tabbase / 0xb4; h++)
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
  uint32_t tabbase = *(const uint32_t*)(uintptr_t)(g_base + CS_TABBASE_IMM);
  /* the function frees through its own lea r14+imm: it must name the same table base */
  if (memcmp(f, SIG, sizeof SIG) || *(const uint32_t*)(f + 0x73) != tabbase) return;
  if (tabbase < 0x4650 || tabbase > 0x10000 || tabbase % 0xb4) return;
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
  int ntab = (int)pool_tables(tabbase), nfree = 0;
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
    for (uint32_t h = 0; h < tabbase / 0xb4; h++)
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
  uint32_t tabbase = *(const uint32_t*)(uintptr_t)(g_base + CS_TABBASE_IMM);
  unsigned char* o = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
  unsigned char* std = o ? *(unsigned char**)(o + 0x78) : 0;
  uint32_t key = 0xffffffff;
  if (year) ((cs_keyof_fn)(uintptr_t)(g_base + CS_KEYOF_RVA))(&key, master);
  unsigned char* e = 0;
  if (std && key != 0xffffffff && tabbase >= 0x4650 && tabbase <= 0x10000 && tabbase % 0xb4 == 0)
    for (uint32_t k = 0; k < tabbase / 0xb4 && !e; k++)
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

/* ---- a league play-off's groups and final (0.2.5) ----
 *
 * The world file writes the entries grouped: the first half are the clubs of group A (the regular
 * phase's 1st, 4th, 5th and 8th in a two-group play-off), the second half those of group B (2nd,
 * 3rd, 6th and 7th), and so on. No draw is made: the field is dealt in that order. The winner of
 * each group (the first row of its table) is the only club through; the better placed club of the
 * regular phase -- the entry's erank -- is put first, at home in the match record. Both functions
 * are pure so test_ccup_league.c can check them without the game. */
static int ccup_league_groups(const uint32_t* field, unsigned n, unsigned groups,
                              uint32_t out[CCUP_MAX_GROUPS][8], unsigned* per_out)
{
  unsigned per;
  if (!groups || groups > CCUP_MAX_GROUPS || n < groups || (n % groups)) return 0;
  per = n / groups;
  if (per < 1 || per > 8) return 0;
  for (unsigned g = 0; g < groups; g++)
    for (unsigned j = 0; j < per; j++) out[g][j] = field[g * per + j];
  *per_out = per;
  return (int)groups;
}
/* the regular-phase position a club came from (its entry's erank); 256 when it is not an entry */
static int ccup_entry_rank(const ccup_t* c, const uint32_t* field, unsigned nf, uint32_t club)
{
  for (unsigned i = 0; i < nf; i++) if (field[i] == club) return c->erank[i];
  return 256;
}
/* the knockout of a league play-off: the group winners, the better placed of the regular phase
   first. Answers how many were put in out (fewer than n only when the same club won two groups). */
static int ccup_league_final(const ccup_t* c, const uint32_t* field, unsigned nf,
                             const uint32_t* winners, int n, uint32_t* out)
{
  int k = 0;
  for (int i = 0; i < n && i < CCUP_MAX_GROUPS; i++) {
    int dup = 0;
    if (!winners[i]) continue;
    for (int j = 0; j < k; j++) dup |= out[j] == winners[i];
    if (!dup && k < CCUP_MAX_ENTRY) out[k++] = winners[i];
  }
  for (int a = 1; a < k; a++)                     /* insertion sort, stable: lower erank first */
    for (int b = a; b > 0; b--) {
      int x = ccup_entry_rank(c, field, nf, out[b - 1]), y = ccup_entry_rank(c, field, nf, out[b]);
      if (y >= x) break;
      uint32_t t = out[b - 1]; out[b - 1] = out[b]; out[b] = t;
    }
  return k;
}

static int ko_sync(uint16_t reg, const char* why);
static int ccup_of(uint16_t r, int* ko);
static int season_ord(int d);
static void ccup_final_note(int k, void* started, int fresh);
/* Fase 4 (31.10.): the Liga FUTVE from January to December -- its league (split total) is in a
   January-December region (world file `season 29 1`). Its season is the calendar year, not the
   August-May one the cups of ours count by: the Apertura's final (June) and the Clausura's
   (November) are of one season, and the Final del FUTVE (December) takes both. */
static int calyear(uint16_t id);
static uint16_t g_tl_total;
static int futve_cal(void) { return g_tl_total && calyear(g_tl_total); }
/* The champion a final of ours read this season (ccup_final_note), kept as a cup winner in
   g_cupwin -- and so in fl26swiss-state.bin, read back after a reload between the final and the
   Final del FUTVE. 0 while this season's final is not over. Kept from the final's day up to the
   July rollover (season_ord), so last season's champion is never this season's. */
static uint32_t ccup_season_win(int k)
{
  cupwin_t* w = cupwin_of(g_ccup[k].ko);
  int ad = abs_day(), t = today();
  if (!w || ad < 0 || t < 0 || !(w->club >> 14)) return 0;
  int age = ad - w->day;
  /* fase 4: a final of the Liga FUTVE (a play-off's, adv=, or the Final del FUTVE, src=) counts
     from 1 January -- the Apertura's final of June is this season's in December */
  int lim = futve_cal() && (g_ccup[k].adv || g_ccup[k].src[0]) ? t : season_ord(t);
  return age >= 0 && age <= lim ? w->club : 0;
}
/* the champion of a cup a final of two cups feeds on. A cup of ours: this season's, as its final
   note read it -- never the rights code's answer before the final is played, which named last
   season's holder (2026-10-29 10:21: "45ed8006 won both feeding cups" in August, the Clausura
   final then won by 45ee4002). If the final's day is past, the cup was filled this season and no
   note was taken (a progression not seen), it is read now. Not a cup of ours: the game's. */
static uint32_t ccup_src_winner(uint16_t reg)
{
  int ko = 0;
  int k = ccup_of(reg, &ko);
  if (k < 0) return cup_winner(reg);
  uint32_t w = ccup_season_win(k);
  const ccup_t* c = &g_ccup[k];
  int t = today(), year = (abs_day() + 183) / 365;
  /* fase 4: a Liga FUTVE final's day counts from 1 January; by the July anchor the Clausura's (day
     335) was "past" on day 121 of the next year, and last season's winner was read as this one's
     (31.10.: the automatic Liga FUTVE given in June of the second season) */
  int calf = futve_cal() && (c->adv || c->src[0]);
  int past = calf ? t > c->days[c->nd - 1] : season_ord(t) > season_ord(c->days[c->nd - 1]);
  if (!w && c->nd && t >= 0 && (calf || c->filled_year == year) && past) {
    ccup_final_note(k, 0, 0);
    w = ccup_season_win(k);
  }
  return w;
}
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
  if (c->adv && c->groups) {                 /* the knockout must be the field the advancers make */
    unsigned char* kor = get_rec(c->ko);
    unsigned kc = kor ? (*(uint32_t*)(kor + 0x30c) & 0x7f) : 0;
    if (kc && kc != (unsigned)(c->adv * c->groups)) {
      logf("fl26swiss: cup %u -- its knockout row holds %u club(s), not the %u of its %u group winner(s); not filled",
           (unsigned)c->reg, kc, (unsigned)(c->adv * c->groups), (unsigned)c->adv);
      return 0;
    }
    if (!kc)
      logf("fl26swiss: cup %u -- its knockout row does not show its field (%u expected); filled anyway",
           (unsigned)c->reg, (unsigned)(c->adv * c->groups));
  }
  if (!c->national) cont_build();                 /* this season's Libertadores / AFC places, for ccup_club */
  int suda = modern_suda_ccup() == k;
  int single = ccup_like_ok(c);
  if (single)
    logf("fl26swiss: cup %u -- a single-match knockout of %u (reg %u's shape), day %d", (unsigned)c->ko, cn,
         (unsigned)c->like, today());
  if (c->src[0] && c->src[1]) {           /* the final of two cups: their champions, or none */
    uint32_t w1 = ccup_src_winner(c->src[0]), w2 = ccup_src_winner(c->src[1]);
    if (w1 && w2 && w1 == w2) {
      static int said_same = 0;
      if (said_same++ < 4)
        logf("fl26swiss: cup %u -- %08x won both feeding cups (%u, %u); the final is not played, the title is theirs",
             (unsigned)c->reg, w1, (unsigned)c->src[0], (unsigned)c->src[1]);
      g_ccup_nf[k] = 0;
      return 0;
    }
    if (!w1 || !w2) {
      static int said_wait = 0;
      if (said_wait++ < 6)
        logf("fl26swiss: cup %u -- its two champions are not known yet (%08x, %08x); not filled",
             (unsigned)c->reg, w1, w2);
      return 0;
    }
    g_ccup_field[k][0] = w1; g_ccup_field[k][1] = w2; g_ccup_nf[k] = 2;
    n = 2;
    suda = 0; single = 0;
    logf("fl26swiss: cup %u -- the final of its two feeding cups: %08x v %08x", (unsigned)c->reg, w1, w2);
    goto field_ready;
  }
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
    } else if (futve_cal() && g_tl_total && c->ereg[i] == g_tl_total && !c->adv && !c->src[0] && !final_of(g_tl_total)) {
      /* fase 4 (31.10., Felix): the Liga FUTVE's first season sends nobody abroad (no final table yet) */
      logf("fl26swiss:   cup %u entry: reg %u -- the Liga FUTVE's first season, no final table yet; no club sent",
           (unsigned)c->reg, (unsigned)c->ereg[i]);
      club = 0;
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
field_ready:
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
  if (c->gnd) {
    /* a league play-off: the entries are dealt into the groups in their order, not drawn -- the
       world file writes A's clubs first (1, 4, 5, 8 of the regular phase), then B's (2, 3, 6, 7) */
    uint32_t grp[CCUP_MAX_GROUPS][8]; unsigned per = 0;
    if (ccup_league_groups(g_ccup_field[k], n, c->groups, grp, &per) == (int)c->groups) {
      for (int g = 0; g < c->groups; g++) {
        u32vec gv = { grp[g], grp[g] + per, grp[g] + per };
        ((setcl_fn)(uintptr_t)(g_base + SETCL_RVA))(ccup_rep(c, g), &gv, 1);
        run_flush();
        logf("fl26swiss: cup %u -- group %c in entry order: %08x %08x %08x %08x", (unsigned)c->reg, 'A' + g,
             grp[g][0], per > 1 ? grp[g][1] : 0, per > 2 ? grp[g][2] : 0, per > 3 ? grp[g][3] : 0);
      }
    } else
      logf("fl26swiss: cup %u -- %u entries do not deal into %u group(s); left as drawn", (unsigned)c->reg,
           n, (unsigned)c->groups);
  }
  char line[96]; int p = 0;
  uint16_t reps[CCUP_MAX_GROUPS];
  for (int g = 0; g < c->groups; g++) {
    reps[g] = ccup_rep(c, g);
    unsigned char* rg = get_rec(reps[g]);
    p += snprintf(line + p, sizeof line - p, " %c:%u", 'A' + g, rg ? rec_count(rg) : 0);
  }
  logf("fl26swiss: cup %u -- day %d: %u clubs %s, groups%s", (unsigned)c->reg, today(), rec_count(rec),
       c->gnd ? "dealt in entry order" : "drawn", line);
  struct { uint16_t* b; uint16_t* e; uint16_t* c; } rv = { reps, reps + c->groups, reps + c->groups };
  table_pool_reap("cup draw");
  /* A group phase filled in the middle of a season is not in the calendar the season was built
     with. The lpre and q_fill pattern does it here: the phase is started (pushed onto the caller's
     list of started stages, 0x141590420) and registered by its master, whose parent field names the
     groups. The register_all of the group rows alone made no match at all on 28 October. The old
     call stays as the fallback, and the counts say in the log whether the engine made any. */
  start_stage(started, c->reg);
  uint16_t mid = c->reg;
  struct { uint16_t* b; uint16_t* e; uint16_t* c; } mv = { &mid, &mid + 1, &mid + 1 };
  ((regall_fn)(uintptr_t)(g_base + REGALL_RVA))(0, &mv);
  run_flush();
  ccup_season_fix(c->reg, reps, c->groups);
  int mg = ccup_matches(c->reg), mt = 0;
  for (int g = 0; g < c->groups; g++) { int x = ccup_matches(reps[g]); if (x > 0) mt += x; }
  if (mg <= 0 && mt <= 0) {
    ((regall_fn)(uintptr_t)(g_base + REGALL_RVA))(0, &rv);
    run_flush();
    mg = ccup_matches(c->reg); mt = 0;
    for (int g = 0; g < c->groups; g++) { int x = ccup_matches(reps[g]); if (x > 0) mt += x; }
    logf("fl26swiss: cup %u -- its master made no match; the group rows handed to register_all", (unsigned)c->reg);
  }
  logf("fl26swiss: cup %u -- groups filled, started and registered on day %d; %d match record(s) under the phase, "
       "%d under its groups", (unsigned)c->reg, today(), mg, mt);
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
      if (!w) { if (g_ncupwin >= 32) continue; w = &g_cupwin[g_ncupwin++]; w->reg = reg; }
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
          if (!w && g_ncupwin < 32) { w = &g_cupwin[g_ncupwin++]; w->reg = reg; }
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
  int year = (abs_day() + 183) / 365;
  for (int k = 0; k < g_nccup; k++) {
    if (g_ccup[k].src[0] && g_ccup[k].filled_year == year) continue;   /* filled at its last source's final */
    if (!g_ccup[k].fill && !g_ccup[k].cal) any |= ccup_fill_one(k, started);
  }
  return any;
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
  if (d < 0) return;                                            /* day 0 (1 January) is a day: -1 is none */
  for (int k = 0; k < g_nccup; k++) {
    ccup_t* c = &g_ccup[k];
    if (!c->fill) continue;
    int f = season_ord(c->fill), s = season_ord(d);
    int first = (c->cal && c->groups) ? g_ccup_gday0[k] : (c->gnd ? c->gdays[0] : (c->nd ? c->days[0] : 0));
    int last = (first && season_ord(first) > f) ? season_ord(first) - 1 : f + 7;   /* up to the eve of its first day */
    if (s < f || s > last || c->filled_year == year || !ccup_world(c)) continue;
    c->filled_year = year;
    logf("fl26swiss: cup %u -- its fill day %u (day %d)", (unsigned)c->ko, (unsigned)c->fill, d);
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
  /* Day 0 is 1 January, a real day: the Apertura's regular phase ends on it (191: rounds on days
     257..0). `d < 1` returned here, so its play-off was filled only on its fill day 3 -- the day of
     its first group matchday, already gone: the first match was never played (29.10., every test). */
  if (d < 0) return;
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
    /* started = 0: the cup registers its own matches (the group path always does, the knockout
       path when started is 0). Handing the split progression's `started` as well had the cup
       pushed there and registered a second time by the caller whenever that progression reported
       a change -- the Apertura (191 over on day 0 -> 1): every play-off match twice, double points
       and double matches played (30.10.). The Clausura's (192 -> 0) never was. */
    (void)started;
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
  if (c->gnd && g_ccup_done[k] != all) {
    /* A save loaded between two group days: the progression of the groups already over is not
       asked again. The matches say whether they are -- a group of four home and away, 12. */
    unsigned seen = g_ccup_done[k];
    int played = ccup_matches(c->reg), unplayed = ccup_unplayed(c->reg);
    for (int g = 0; g < c->groups && played >= 0 && unplayed >= 0; g++) {
      int m = ccup_matches(ccup_rep(c, g)), u = ccup_unplayed(ccup_rep(c, g));
      if (m > 0) played += m;
      if (u > 0) unplayed += u;
    }
    if (played >= 12 * (int)c->groups && unplayed == 0) {
      g_ccup_done[k] = all;
      logf("fl26swiss: cup %u -- all %d group match(es) are played on day %d although the progression named %02x; "
           "the groups are taken as over", (unsigned)c->reg, played, today(), seen);
    }
  }
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
  if (c->adv) {
    /* a league play-off: only the winner of each group goes through, the better placed club of
       the regular phase first -- at home in the match record */
    uint32_t win[CCUP_MAX_GROUPS];
    int nw = 0;
    for (int g = 0; g < c->groups; g++) {
      unsigned char* t = ccup_group_table(c, g);
      uint32_t rows = t ? *(uint32_t*)(t + 0x3c0) : 0;
      if (rows < 2 || rows > 8) {
        logf("fl26swiss: cup %u -- group %c has a table of %u rows; the final is not filled", (unsigned)c->reg,
             'A' + g, (unsigned)rows);
        return 0;
      }
      win[nw++] = *(uint32_t*)t;
    }
    int nk = ccup_league_final(c, g_ccup_field[k], g_ccup_nf[k], win, nw, buf);
    if (nk != c->adv * c->groups) {
      logf("fl26swiss: cup %u -- %d group winner(s) for a final of %u (the same club in two groups?); not filled",
           (unsigned)c->reg, nk, (unsigned)(c->adv * c->groups));
      return 0;
    }
    logf("fl26swiss: cup %u -- final: %08x (regular position %d) v %08x (position %d)", (unsigned)c->reg,
         buf[0], ccup_entry_rank(c, g_ccup_field[k], g_ccup_nf[k], buf[0]),
         buf[1], ccup_entry_rank(c, g_ccup_field[k], g_ccup_nf[k], buf[1]));
    u32vec v = { buf, buf + nk, buf + nk };
    ((setcl_fn)(uintptr_t)(g_base + SETCL_RVA))(c->ko, &v, 1);
    run_flush();
    logf("fl26swiss: cup %u -- final reg %u now %u club(s)", (unsigned)c->reg, (unsigned)c->ko, rec_count(ko));
    g_ccup_done[k] = 0;
    if ((int)rec_count(ko) != nk) return 0;
    start_stage(started, c->ko);
    return 1;
  }
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
/* The dates of a cup borrowed from a shipped one -- a single-match league cup's (`like`, whole
   cup) or a league play-off's knockout (`kolike`): the shipped regulation's own calendar, its
   records mapped by round to the days given in the world file (the last day for a final). */
static uint64_t ccup_borrowed_dates(int k, uint16_t id, uint64_t reg, void* vec, uint16_t shipped, const char* what)
{
  const ccup_t* cc = &g_ccup[k];
  uint64_t rv = ((date_fn)(uintptr_t)g_tramp_date)((reg & ~(uint64_t)0xffff) | shipped, vec);
  vec_t* v = (vec_t*)vec;
  size_t have = (v->b && v->e >= v->b) ? (size_t)(v->e - v->b) / sizeof(date_t) : 0;
  date_t* r = (date_t*)v->b;
  static unsigned char said[MAX_CCUP];
  if (!have || !cc->nd) {
    if (!said[k]) logf("fl26swiss: cup reg %u: reg %u's calendar gave %u record(s), %u day(s) of its own (%s); left as it is",
                       (unsigned)id, (unsigned)shipped, (unsigned)have, (unsigned)cc->nd, what);
    said[k] = 1;
    return rv;
  }
  /* A two-legged final (days=167,171: the Final del FUTVE ida y vuelta). The exe's super-cup handler
     pushes both legs of its table (kind 0 = first leg, 1 = second) and then, for a regulation whose
     legs mode (CompetitionRegulation +0x10 bits 9-11 -> runtime +0x300 >> 29; 0 single, 1 two legs and
     a single final, 2 all two legs) is 0, erases the first leg and makes the second a single match
     (kind 2) -- 0x14157f720. So the one record comes back in a vector that held two: the first leg is
     put back in front, room permitting. */
  if (cc->nd == 2 && have == 1 && r && (size_t)(v->c - v->b) >= 2 * sizeof(date_t)) {
    r[1] = r[0];
    r[0].kind = 0; r[1].kind = 1;
    v->e = v->b + 2 * sizeof(date_t);
    have = 2;
    if (!said[k]) logf("fl26swiss: cup reg %u: reg %u's one-match final made two legs (ida y vuelta)", (unsigned)id, (unsigned)shipped);
  }
  for (size_t i = 0; i < have; i++) {
    /* as many records as days (a two-legged final, days=167,171 from the Spanish Super Cup's two
       legs): one day each, in order -- by round both legs are the final and took the last day */
    int j = (have > 1 && have == cc->nd) ? (int)i : like_slot(r[i].kind);
    if (j < 0) j = like_slot(r[i].round);
    if (j < 0) j = (int)(have > 1 ? i * 5 / (have - 1) : 5);    /* by order, the last the final */
    if (!said[k])
      logf("fl26swiss: cup reg %u borrowed record %u: day %u round %#x kind %#x -> day %u", (unsigned)id, (unsigned)i,
           r[i].day, r[i].round, r[i].kind, (unsigned)cc->days[j < cc->nd ? j : cc->nd - 1]);
    r[i].day = cc->days[j < cc->nd ? j : cc->nd - 1];
  }
  if (!said[k])
    logf("fl26swiss: cup reg %u dated as reg %u (%s): %u record(s), days %u..%u", (unsigned)id, (unsigned)shipped,
         what, (unsigned)have, r[0].day, r[have - 1].day);
  said[k] = 1;
  return rv;
}
static uint64_t ccup_like_dates(int k, uint16_t id, uint64_t reg, void* vec)
{
  return ccup_borrowed_dates(k, id, reg, vec, g_ccup[k].like, "single-match cup");
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
  if (ko && cc->kolike) return ccup_borrowed_dates(k, id, reg, vec, cc->kolike, "its knockout");
  /* cal=1 cups keep the native Libertadores dates: groups from reg 9 and
     knockout from reg 10. A custom one-off knockout with explicit days keeps
     the normal borrowed calendar instead. */
  int keep = cc->cal && (!ko || !cc->nd);
  uint16_t src = ko ? (keep ? R_LIBKO : R_UCLKO) : R_LIBGROUP;
  uint64_t rv = ((date_fn)(uintptr_t)g_tramp_date)((reg & ~(uint64_t)0xffff) | src, vec);
  vec_t* v = (vec_t*)vec;
  size_t have = (v->b && v->e >= v->b) ? (size_t)(v->e - v->b) / sizeof(date_t) : 0;
  date_t* r = (date_t*)v->b;
  /* a league play-off's groups have their own days (gdays); the others keep six */
  size_t want = ko ? ((cc->nd && !cc->like) ? cc->nd : 7) : (cc->gnd ? cc->gnd : 6);
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
  if (have == 0 || (have > want && !(!ko && cc->gnd))) {
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
    if (!ko && cc->gnd) {                          /* its own group days, in order */
      size_t j = have <= cc->gnd ? i : (i * cc->gnd) / have;
      r[i].day = cc->gdays[j];
      continue;
    }
    size_t j = ko ? (i + 1 == have ? want - 1 : i + (want - have)) : i * want / have;
    r[i].day = kcr >= 0 ? CCUP_KO_DAYS[kcr][ccup_tier(cc)][j] : ccup_day(cc, ko, (int)j);
  }
  if (!(said[k] & bit))
    logf("fl26swiss: cup reg %u dated: %s days %u..%u (%u records)%s", (unsigned)id, ko ? "knockout" : "groups",
         r[0].day, r[have - 1].day, (unsigned)have, !ko && cc->gnd ? " on its own group days" : "");
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

/* A final of two cups (src=) whose feeding final just ended: filled now, as soon as both champions
   are known -- not at reg 2's progression (ccup_fill), which the game asks for in August, not
   between the Clausura final (164) and the Final del FUTVE (167). */
static uint32_t g_ff_dec[MAX_CCUP][2];             /* the two champions a final of two cups was decided on */
static void ccup_fill_finals(uint16_t ko, void* started)
{
  int year = (abs_day() + 183) / 365;
  for (int j = 0; j < g_nccup; j++) {
    ccup_t* f = &g_ccup[j];
    if (!f->src[0] || (f->src[0] != ko && f->src[1] != ko) || !ccup_world(f)) continue;
    uint32_t w1 = ccup_src_winner(f->src[0]), w2 = ccup_src_winner(f->src[1]);
    /* Decided this season on these two champions: nothing to do. On other ones -- a save loaded
       before a feeding final and that final won by another club (29.10., prueba B: the Clausura
       lost after a reload, the stale "won both" kept and no Final del FUTVE) -- decided again. */
    if (f->filled_year == year && g_ff_dec[j][0] == w1 && g_ff_dec[j][1] == w2) continue;
    if (f->filled_year == year)
      logf("fl26swiss: cup %u -- its feeding champions changed (%08x, %08x -> %08x, %08x): decided again",
           (unsigned)f->ko, g_ff_dec[j][0], g_ff_dec[j][1], w1, w2);
    if (!w1 || !w2) {
      logf("fl26swiss: cup %u -- the final of %u is over on day %d; the other feeding final is not (%08x, %08x)",
           (unsigned)f->ko, (unsigned)ko, today(), w1, w2);
      continue;
    }
    f->filled_year = year; g_ff_dec[j][0] = w1; g_ff_dec[j][1] = w2;
    logf("fl26swiss: cup %u -- both feeding finals over on day %d: filled now (its day %u)",
         (unsigned)f->ko, today(), f->nd ? (unsigned)f->days[f->nd - 1] : 0u);
    /* Not the feeding final's `started`: the caller registers the ids pushed there only when the
       progression reports a change, and the 262's did not -- the 263 was filled, dated (171) and
       started with no match record, and never played (29.10., 15:37). With 0 the knockout
       registers its own matches (register_all), as a cup filled on its fill day does. */
    (void)started;
    ccup_fill_one(j, 0);
  }
}
/* The final of a league play-off is over: its champion, once a season, kept as a cup winner (and in
   the state file, so a reload before the Final del FUTVE has it), then the final of two cups it
   feeds. Only from the final's own progression (or ccup_src_winner after the final's day): noting
   it at the group phase's progression (62dee65, "ko || cup.ko") read the 262 on day 160, four days
   before its final, found nothing and locked the season (10:41 to 12:42, every test). A miss is not
   locked: the next progression asks again. */
static void ccup_final_note(int k, void* started, int fresh)
{
  const ccup_t* c = &g_ccup[k];
  /* fresh: the final's own progression -- its match was just played, so it is read whatever was
     kept: a keep of the same day can be another timeline's (a save loaded before the final and the
     final played again, 29.10. prueba B: the kept "45ed8006" stood and the new result was never
     read). Otherwise (ccup_src_winner after the final's day) a keep is enough. */
  uint32_t had = ccup_season_win(k);
  if (had && !fresh) return;
  uint32_t w = ccup_ko_winner(c->ko);
  if (w && had && same_club(w, had)) { ccup_fill_finals(c->ko, started); return; }
  if (had && w) logf("fl26swiss: cup %u -- champion %08x replaces the kept %08x (a save loaded before its final)",
                     (unsigned)c->ko, w, had);
  if (!w) {
    static int said[MAX_CCUP];
    if (said[k]++ < 6)
      logf("fl26swiss: cup %u -- progression on day %d, no winner read yet (asked again at the next one)",
           (unsigned)c->ko, today());
    return;
  }
  int ad = abs_day();
  cupwin_t* cw = cupwin_of(c->ko);
  if (!cw && g_ncupwin < 32) { cw = &g_cupwin[g_ncupwin++]; cw->reg = c->ko; }
  if (cw) { cw->day = ad; cw->club = w; }
  g_ccup_win[k] = w;
  /* fase 5 (01.11.): a Liga FUTVE final's loser too -- the Apertura's and the Clausura's go to the
     Sudamericana, the Final del FUTVE's to the Libertadores' phase 2 (futve_cont_club) */
  if (futve_cal() && (c->adv || c->src[0])) {
    uint32_t r = knockout_runner_now(c->ko);
    if (r && !same_club(r, w)) {
      cupwin_t* rw = cupwin_of((uint16_t)(FUTVE_RUNNER | c->ko));
      if (!rw && g_ncupwin < 32) { rw = &g_cupwin[g_ncupwin++]; rw->reg = (uint16_t)(FUTVE_RUNNER | c->ko); }
      if (rw) { rw->day = ad; rw->club = r; }
      logf("fl26swiss: cup %u -- its final's loser %08x%s", (unsigned)c->ko, r, rw ? " kept" : " (no room to keep it)");
    }
  }
  logf("fl26swiss: cup %u -- its final is over on day %d: champion %08x%s", (unsigned)c->ko, today(), w,
       cw ? " (kept in the state file)" : " (no room to keep it)");
  if (cw) state_store();
  ccup_fill_finals(c->ko, started);
}

/* the title probes of 29-30.10. (daily snapshot, progression diff): 0 = off, they cost seconds */
#ifndef FL26_TITLE_PROBES
#define FL26_TITLE_PROBES 0
#endif
static void honours_fix(void);
static uint16_t g_tl_total, g_tl_cid, g_ff_cid;
static char prog_handler_inner(void* ctx, uint64_t id, void* started);
/* ---- progression diff (30.10., the Palmarés count of the Liga FUTVE) ----
 * With the season rows, the runner-up row and the winners history all corrected, "Liga FUTVE 1"
 * stands: a count the game raised when the split league ended (day 0: 191, day 142: 192 and 11).
 * Around exactly those progressions -- nothing else runs in between -- the career block and the
 * owner's +0x50 block are copied before and compared after, and every changed run is logged
 * (offset, length, old and new). Read-only. */
typedef struct { unsigned char* p; size_t n; unsigned char* snap; size_t cap; } pdiff_t;
static pdiff_t g_pd[2];
static size_t pd_len(unsigned char* p)
{
  MEMORY_BASIC_INFORMATION mi;
  if (!p || !VirtualQuery(p, &mi, sizeof mi) || mi.State != MEM_COMMIT) return 0;
  size_t n = (size_t)((unsigned char*)mi.BaseAddress + mi.RegionSize - p);
  return n > ((size_t)128 << 20) ? ((size_t)128 << 20) : n;
}
static void pd_take(void)
{
  unsigned char* o = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
  for (int b = 0; b < 2; b++) {
    pdiff_t* d = &g_pd[b];
    d->p = o ? *(unsigned char**)(o + (b ? 0x50 : 0x48)) : 0;
    d->n = pd_len(d->p);
    if (d->n > d->cap) {
      if (d->snap) VirtualFree(d->snap, 0, MEM_RELEASE);
      d->snap = (unsigned char*)VirtualAlloc(0, d->n, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE);
      d->cap = d->snap ? d->n : 0;
    }
    if (!d->snap || d->n > d->cap) { d->n = 0; continue; }
    memcpy(d->snap, d->p, d->n);
  }
}
/* The first run (30.10.) was flooded: on day 0 and day 142 hundreds of 4-byte changes of one kind
   (0301c002 -> 0401c002, a record every 0x17c bytes) took all 150 lines. Now the changed runs are
   grouped by their first dword (old -> new): a kind seen more than 4 times is one line (count, first
   offset, stride), and only the rare ones are shown one by one. */
typedef struct { uint32_t o, n; size_t first, last; int count; int b; } pd_kind_t;
static void pd_show(uint16_t r)
{
  static pd_kind_t K[512]; int nk = 0, total = 0;
  static struct { int b; size_t i, len; } R[4096]; int nr = 0;
  for (int b = 0; b < 2; b++) {
    pdiff_t* d = &g_pd[b];
    if (!d->n) continue;
    for (size_t i = 0; i + 4 <= d->n; i += 4) {
      if (*(uint32_t*)(d->snap + i) == *(uint32_t*)(d->p + i)) continue;
      size_t e = i;
      while (e + 4 <= d->n && *(uint32_t*)(d->snap + e) != *(uint32_t*)(d->p + e)) e += 4;
      uint32_t ov = *(uint32_t*)(d->snap + i), nv = *(uint32_t*)(d->p + i);
      int k = 0;
      while (k < nk && !(K[k].o == ov && K[k].n == nv && K[k].b == b)) k++;
      if (k == nk && nk < 512) { K[nk].o = ov; K[nk].n = nv; K[nk].b = b; K[nk].first = i; K[nk].count = 0; nk++; }
      if (k < nk) { K[k].count++; K[k].last = i; }
      if (nr < 4096) { R[nr].b = b; R[nr].i = i; R[nr].len = e - i; nr++; }
      total++;
      i = e;
    }
  }
  int shown = 0;
  for (int k = 0; k < nk; k++)
    if (K[k].count > 4)
      logf("fl26swiss: progression diff reg %u day %d: %d x %08x -> %08x in %s from +%#llx to +%#llx (a bulk kind)",
           (unsigned)r, today(), K[k].count, K[k].o, K[k].n, K[k].b ? "owner+0x50" : "blk",
           (unsigned long long)K[k].first, (unsigned long long)K[k].last);
  for (int q = 0; q < nr && shown < 200; q++) {
    pdiff_t* d = &g_pd[R[q].b];
    uint32_t ov = *(uint32_t*)(d->snap + R[q].i), nv = *(uint32_t*)(d->p + R[q].i);
    int bulk = 0;
    for (int k = 0; k < nk && !bulk; k++) bulk = K[k].o == ov && K[k].n == nv && K[k].b == R[q].b && K[k].count > 4;
    if (bulk) continue;
    size_t show = R[q].len > 32 ? 32 : R[q].len, i = R[q].i;
    char h0[65], h1[65], c0[65];
    static const char H[] = "0123456789abcdef";
    for (size_t x = 0; x < show; x++) {
      h0[2*x] = H[d->snap[i+x] >> 4]; h0[2*x+1] = H[d->snap[i+x] & 15];
      h1[2*x] = H[d->p[i+x] >> 4];    h1[2*x+1] = H[d->p[i+x] & 15];
    }
    h0[2*show] = h1[2*show] = 0;
    size_t cb = i >= 32 ? i - 32 : 0;
    for (size_t x = 0; x < 32; x++) { c0[2*x] = H[d->p[cb+x] >> 4]; c0[2*x+1] = H[d->p[cb+x] & 15]; }
    c0[64] = 0;
    logf("fl26swiss: progression diff reg %u day %d: %s+%#llx (%llu bytes) %s -> %s | before it: %s", (unsigned)r, today(),
         R[q].b ? "owner+0x50" : "blk", (unsigned long long)i, (unsigned long long)R[q].len, h0, h1, c0);
    shown++;
  }
  logf("fl26swiss: progression diff reg %u day %d: %d changed run(s), %d kind(s), %d shown one by one", (unsigned)r,
       today(), total, nk, shown);
}
char prog_handler(void* ctx, uint64_t id, void* started)
{
  uint16_t r = (uint16_t)id;
  const split_t* sp = 0;
  int watch = FL26_TITLE_PROBES && g_tl_total && (r == g_tl_total || split_part(r, &sp));
  if (watch) pd_take();
  char ok = prog_handler_inner(ctx, id, started);
  if (watch) pd_show(r);
  return ok;
}
static uint16_t split_total_of(const split_t* s);
static uint16_t split_group0_of(const split_t* s);
static char prog_handler_inner(void* ctx, uint64_t id, void* started)
{
  uint16_t r = (uint16_t)id;
  split_keys();
  {
    const split_t* s; int part = split_part(r, &s);
    if (part) {
      char ok = ((prog_fn)(uintptr_t)g_tramp_prog)(ctx, id, started);
      if (part == 2 && r > 175 && futve_cal() && calyear(split_total_of(s)) && split_group0_of(s) && ccup_matches(split_group0_of(s)) > 0) {
        /* fase 4: the Clausura was made in February with the Apertura (futve_clausura_early): its
           fixtures stand, the game must not deal the clubs to it a second time */
        check_reg(r, "its phase over");
        logf("fl26swiss: reg %u -- split regular phase over on day %d; its group %u was made with it in February (%d match record(s)): not filled again",
             (unsigned)r, today(), (unsigned)split_group0_of(s), ccup_matches(split_group0_of(s)));
      } else if (part == 2 && r > 175) {
        check_reg(r, "its phase over");
        char sp = ((splitfn_t)(uintptr_t)(g_base + SPLIT_FN_RVA))(ctx, id, started);
        logf("fl26swiss: reg %u -- split regular phase over on day %d, groups filled by 0x141343d70 -> %d",
             (unsigned)r, today(), (int)sp);
        canon_groups(s);
        ok |= sp;
      } else {
        logf("fl26swiss: reg %u -- split progression on day %d -> %d", (unsigned)r, today(), (int)ok);
      }
      if (part > 1 && r > 175) ccup_fill_ahead(r, "the end of its phase", started);
      /* the game writes the league title of a phase it ends in this progression: take it out at
         once, not at the next day loop -- the Palmarés looked at the same day still had it (30.10.) */
      honours_fix();
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
      /* The KO final of a cup is a final whether or not its group phase was marked `gnd`. Only the
         knockout's own progression (ko): the group phase's (the 260 on day 160) comes before the
         final is played. The 261 never noted its champion in the tests after 09:41 because the
         Apertura was never filled in them (no "cup 261 -- its fill day"), not because of ccup_of. */
      /* Only a league play-off's final (adv) or a final of two cups (src): the note keeps its
         champion in g_cupwin, which a continental cup's access (ccup_keep_winners) also reads. */
      if (ko && (g_ccup[k].adv || g_ccup[k].src[0])) { ccup_final_note(k, started, 1); honours_fix(); }
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
  if (european(r) && r < 1024 && !g_prog_seen[r]) {
    g_prog_seen[r] = 1;
    logf("fl26swiss: progression asked for reg %u -> %d", (unsigned)r, (int)ok);
  }
  if (r == 2) { if (uecl_fill(started)) ok = 1; if (ccup_fill(started)) ok = 1; }
  else if (r == UECL_REG || r == UECL_ROW) { if (uecl_ko(started)) ok = 1; }
  if (r == g_tl_total) honours_fix();              /* the split league's own end (reg 11, day 142) */
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
static unsigned char* ko_match(uint16_t id)
{
  unsigned char* o = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
  void* blk = o ? *(void**)(o + 0x48) : 0;
  if (!blk || id == 0xffff) return 0;
  unsigned char* m = ((match_fn)(uintptr_t)(g_base + MATCH_RVA))(blk, id);
  return m && *(uint16_t*)m == id ? m : 0;
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
#define USER_CLUB_OFF   0x1798ab0
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
      unsigned char* m = ko_match(ids[l]);
      if (!m || (m[7] & 0x40)) return -1;
    }
  }
  for (int s = 0; s < n; s++) {
    uint32_t* sl = ko_slot(rnd, s);
    uint16_t* ids = (uint16_t*)(sl + 2);
    uint32_t h = want[2 * s], a = want[2 * s + 1];
    sl[0] = h; sl[1] = a;
    unsigned char* m1 = ko_match(ids[0]);
    unsigned char* m2 = ko_match(ids[1]);
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
      unsigned char* m = ko_match(*(uint16_t*)(sl + 2));
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
#define RT_OFF  0x447ed20
#define RT_REC  0x208
#define RT_N    0x1f40
static int real_club(uint32_t v) { return !(v >> 28) && (v & KO_TBD) != KO_TBD && (v >> 14); }
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
      unsigned char* m = ko_match(*(uint16_t*)(sl + 2));
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
static int ko_winner(const uint32_t* sl, uint32_t* w)
{
  const uint16_t* ids = (const uint16_t*)(sl + 2);
  unsigned char* m1 = ko_match(ids[0]);
  if (!m1 || !(m1[7] & 0x40)) return 0;
  uint32_t h = *(uint32_t*)(m1 + 0x14), a = *(uint32_t*)(m1 + 0x18);
  int gh = ko_goals(m1, 0), ga = ko_goals(m1, 1), ph = m1[0x1e], pa = m1[0x21], awh = 0, awa = ga;
  if (ids[1] != 0xffff) {
    unsigned char* m2 = ko_match(ids[1]);
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
  /* The final's round is the bracket's single-slot one. Its kind is not always 0x36/0x35 (the 262
     final was read as 0 with only those two), so try every knockout kind, and log what was found:
     a 0 here must leave in the log the rounds, their kinds, their slots and their teams. */
  int found = 0, single = 0;
  for (uint32_t kind = 0; kind <= 0x3f; kind++) {
    unsigned char* rnd = ko_round(reg, kind);
    uint32_t w = 0;
    if (!rnd) continue;
    found++;
    logf("fl26swiss: cup reg %u -- round kind %02x: reg %u, %d slot(s)",
         (unsigned)reg, (unsigned)kind, (unsigned)*(uint16_t*)rnd, ko_slots(rnd));
    if (*(uint16_t*)rnd != reg || ko_slots(rnd) != 1) continue;
    single++;
    uint32_t* sl = ko_slot(rnd, 0);
    logf("fl26swiss: cup reg %u -- final kind %02x: %08x vs %08x",
         (unsigned)reg, (unsigned)kind, sl[0], sl[1]);
    if (ko_winner(sl, &w)) logf("fl26swiss: cup reg %u -- final kind %02x: winner raw %08x",
                                (unsigned)reg, (unsigned)kind, w);
    if (w >> 14) return canon_club(w);
  }
  logf("fl26swiss: cup reg %u -- %d round(s), %d single-slot final(s), no winner read",
       (unsigned)reg, found, single);
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
      unsigned char* m = ko_match(*(uint16_t*)(sl + 2));
      if (!m || !(m[7] & 0x40)) continue;           /* not played: ko_sync_all's */
      if (*(uint16_t*)(m + 4) != reg || m[6] != kind) continue;
      uint32_t h = *(uint32_t*)(m + 0x14), a = *(uint32_t*)(m + 0x18);
      if (!real_club(h) || !real_club(a)) continue;
      if ((same_club(sl[0], h) && same_club(sl[1], a)) || (same_club(sl[0], a) && same_club(sl[1], h))) continue;
      if (!here && ko_round(reg, kind) != rnd) break;
      here = 1;
      uint32_t w;
      if (!ko_winner(sl, &w)) continue;
      uint32_t next = sl[4];
      if ((next & 0xffff) != reg) continue;          /* a final: nothing comes after it */
      unsigned char* rnd2 = ko_round(reg, (next >> 16) & 0x3f);
      int t = (int)(next >> 22);
      if (t >= ko_slots(rnd2)) continue;
      uint32_t* ns = ko_slot(rnd2, t);
      int side = ns[6] == sl[3] ? 0 : ns[7] == sl[3] ? 1 : -1;
      if (side < 0) continue;
      uint16_t* nid = (uint16_t*)(ns + 2);
      unsigned char* n1 = ko_match(nid[0]);
      unsigned char* n2 = ko_match(nid[1]);
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
#define CD_MAX     32                 /* cups */
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
        unsigned char* m = ko_match(ids[l]);
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
    unsigned char* m1 = ko_match(pl[k].legs[0]);
    unsigned char* m2 = ko_match(pl[k].legs[1]);
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
#define USER_NT_OFF 0x1798ab4
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
  int k = 0;
  for (int i = 0; v && i < n; i++) {
    const uint16_t* e = v + 3 * i;
    if (e[0] < UCLQ || e[0] > UECLQ || (e[1] != 2 && e[1] != 3) || e[2] < 2 || e[2] > 0x3ff) continue;
    g_qreg[(e[0] - UCLQ) + NQ * (e[1] == 3 ? 1 : 2)] = e[2];
    k++;
  }
  po_fill();
  return k;
}

/* The first-season list from the loader: n pairs of u32 -- competition (0 Champions League,
   1 Europa League, 2 Conference League) and team id, in the order they are to be placed.
   Answers how many were taken. */
__declspec(dllexport) int fl26_swiss_first(const uint32_t* v, int n)
{
  g_nfirst[0] = g_nfirst[1] = g_nfirst[2] = 0;
  int k = 0;
  for (int i = 0; v && i < n; i++) {
    uint32_t comp = v[2 * i], id = v[2 * i + 1];
    if (comp > 2 || !id || id >> 18 || g_nfirst[comp] >= 48) continue;
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
  if (ngroups == 1 && rows > nw) {
    unsigned pages = (unsigned)((rows + nw - 1) / nw);
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
      logf("fl26swiss: standings screen has %u rows for a table of %u -- %u pages of %u (L1/R1)",
           nw, (unsigned)rows, pages, (unsigned)per); }
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
  for (int st = 0; st < 3; st++) {
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
        unsigned char* tie = find_rec(tie_id(c, 0)), *po = find_rec(c->po), *r2 = find_rec(CUPS[0].po);
        if (!tie || !rec_count(tie)) {
          static int said_grey = 0;
          if (said_grey++ < 6) logf("fl26swiss: Competition Info -- %s Play-offs greyed: not drawn yet", c->name);
          return r | 0xffff;
        }
        /* the enable check reads the drawn bit only; the summer play-offs are filled without the
           game's draw, reg 2 is marked drawn all year */
        if (!(po && ((*(uint32_t*)(po + 0x304) >> 8) & 1)) && r2 && ((*(uint32_t*)(r2 + 0x304) >> 8) & 1))
          return (r & ~0xffffull) | CUPS[0].po;
        return r;
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
#define FINAL_TEXT 0x3a2fff6u   /* "Final", a league play-off's one-match final (0.2.5) */
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
  if ((uint16_t)index == (uint16_t)FINAL_TEXT) return "Final";
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
  if (qa >= 0 && g_tramp_txtget) {
    static int said = 0;
    if (said < 4) { said++; logf("fl26swiss: phase name -- regulation %u named %s qualifying round (asked from %llx)",
                                 (unsigned)(uint16_t)reg, qa / NQ == 1 ? "3rd" : "2nd",
                                 (unsigned long long)((uintptr_t)__builtin_return_address(0) - g_base + 0x140000000ull)); }
    return qa / NQ == 1 ? QR3_TEXT : QR2_TEXT;
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
  /* the final of a league play-off (0.2.5, the Liga FUTVE): the knockout is a normal cup's row cut
     to two clubs, and the game has no phase name for it -- the super cup row it was copied from
     before the 28 October test carried none, so the calendar fell back to the competition's name.
     The match screens, and the Competition Info item, now say "Final". */
  for (int k = 0; k < g_nccup; k++) {
    const ccup_t* c = &g_ccup[k];
    if (c->gnd && c->adv && (uint16_t)reg == c->ko) {
      static int said_fin = 0;
      if (said_fin < 4) {
        said_fin++;
        logf("fl26swiss: phase name -- regulation %u named Final", (unsigned)(uint16_t)reg);
      }
      return FINAL_TEXT;
    }
  }
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
    if (!cup_on(ci)) continue;
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
#define LIBQ_SELCOMP_OFF 0x1787b5c

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

static int libq_item_key(void* blk, const unsigned char* item)
{
  unsigned char* m =
      ((libq_matchrec_fn)(uintptr_t)(g_base + LIBQ_MATCHREC_RVA))
      (blk, *(const uint16_t*)(item + 4));

  return m ? libq_page_key(*(uint16_t*)(m + 4)) : -1;
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

  for (int i = 0; i < g_nlpre; i++) {
    /* Technical continental containers:
       - alias: modern Libertadores F1/F2
       - lpre_is_suda: modern Sudamericana first stage
       - poko: modern Sudamericana post-group playoff
       They must stay live in region 1 for the engine, but must not appear as
       standalone tournaments in Competition Info. */
    int technical = g_lpre[i].alias || lpre_is_suda(&g_lpre[i]) || g_lpre[i].poko;
    if (!technical) continue;

    unsigned char* master = find_rec(g_lpre[i].reg);
    if (master && *(uint32_t*)(master + 0x80) == comp) {
      static int said = 0;
      if (said++ < 3)
        logf("fl26swiss: Info Database -- technical CONMEBOL helper competition %u hidden",
             comp);
      return 1;
    }
  }

  return 0;
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
#define MAX_OUR_LEAGUES 256
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
#define CUPD_MAX 256
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
static int ccup_feeds(int k, uint16_t id)
{
  const ccup_t* c = &g_ccup[k];
  for (int e = 0; e < c->n && e < CCUP_MAX_ENTRY; e++) {
    if (c->ereg[e] == id) return 1;
    if (!c->erank[e] && (c->ealt[e] == id || cupdraw_has(c->ereg[e], id))) return 1;
  }
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
#define MAX_JULY 256
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
#define MAX_RCAL 256
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
    } else if (x->national && x->nc && (ccup_of_league(k, id) || ccup_invites(k, id))) {
      /* a pre-season cup (invited clubs): its few July days, for the host's league and each
         invited club's -- any world's cup, not one */
      for (int i = 0; i < x->nd && i < CCUP_MAX_DAYS; i++) BZ(x->days[i], BZ_CONT);
    } else if (x->national && !x->nc && ccup_of_league(k, id)) {   /* its league cup */
      for (int i = 0; i < x->nd && i < CCUP_MAX_DAYS; i++) BZ(x->days[i], BZ_LCUP);
      for (int i = 0; i < x->gnd && i < CCUP_MAX_DAYS; i++) BZ(x->gdays[i], BZ_LCUP);
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
static int rcal_dates(uint16_t id, const rcal_t* c, date_t* r, uint32_t n, int seen)
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
static uint16_t split_total_of(const split_t* s) { return s ? s->total : 0; }
static uint16_t split_group0_of(const split_t* s) { return s ? s->group[0] : 0; }
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
 * (split_keys). Everything else leaves the stub where the original would have gone. */
#define CARRY_SITE_RVA 0x134a680
#define CARRY_FULL_RVA 0x134a68e
#define CARRY_NONE_RVA 0x134a8aa
static const unsigned char SIG_CARRY[14] = {
  0x83,0xef,0x01, 0x74,0x09, 0x83,0xff,0x03, 0x0f,0x85,0x1c,0x02,0x00,0x00 };
#define CARRY_SLOTS 8
static unsigned char* g_carry_stub = 0;      /* slot i's immediate is at +10 + 5*i */
static unsigned g_carry_keys = 0;

static int carry_install(uint64_t exe_base)
{
  unsigned char* site = (unsigned char*)(uintptr_t)(exe_base + CARRY_SITE_RVA);
  for (int i = 0; i < 14; i++) if (site[i] != SIG_CARRY[i]) return 2;
  unsigned char* t = (unsigned char*)VirtualAlloc(0, 0x100, MEM_COMMIT|MEM_RESERVE, PAGE_EXECUTE_READWRITE);
  if (!t) return 3;
  int n = 0, full = 10 + 5 * CARRY_SLOTS + 14;          /* offset of the "full" jump */
  t[n++] = 0x83; t[n++] = 0xef; t[n++] = 0x01;             /* sub edi, 1      (key 12 -> 0) */
  t[n++] = 0x74; t[n] = (unsigned char)(full - (n + 1)); n++;
  t[n++] = 0x83; t[n++] = 0xff; t[n++] = 0x03;             /* cmp edi, 3      (key 15) */
  t[n++] = 0x74; t[n] = (unsigned char)(full - (n + 1)); n++;
  for (int i = 0; i < CARRY_SLOTS; i++) {                  /* cmp edi, key-12 ; je full */
    t[n++] = 0x83; t[n++] = 0xff; t[n++] = 0x7f;           /* 0x7f: an empty slot never matches */
    t[n++] = 0x74; t[n] = (unsigned char)(full - (n + 1)); n++;
  }
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
 * has no objective for the African, North American or Oceanian cups, so those stay as they were. */
#define CONT_RVA 0x15111c0
static const uint32_t CONT_CALLS[] = {
  0xedc75a, 0xedc77b, 0xedc87c, 0xedc893, 0xedca17, 0xedca2e, 0xedcc22, 0xedcc30, 0xedcc80,
  0xedcca6, 0xedd507, 0xedd51b, 0xedd75a, 0xedd77b, 0xeddaa5, 0xeddacb, 0xede311, 0xede324 };
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

/* 0 ok; 2 a call is not the one expected (nothing patched); 3 no page in reach; 4 VirtualProtect */
static int cont_install(uint64_t exe_base)
{
  int n = (int)(sizeof CONT_CALLS / sizeof CONT_CALLS[0]);
  for (int i = 0; i < n; i++) {
    unsigned char* s = (unsigned char*)(uintptr_t)(exe_base + CONT_CALLS[i]);
    if (s[0] != 0xE8 || (uint64_t)(uintptr_t)(s + 5) + *(int32_t*)(s + 1) != exe_base + CONT_RVA) return 2;
  }
  unsigned char* t = near_alloc(exe_base);
  if (!t) return 3;
  t[0] = 0xFF; t[1] = 0x25; *(uint32_t*)(t + 2) = 0; *(uint64_t*)(t + 6) = (uint64_t)(uintptr_t)cont_handler;
  FlushInstructionCache(GetCurrentProcess(), t, 14);
  for (int i = 0; i < n; i++) {
    unsigned char* s = (unsigned char*)(uintptr_t)(exe_base + CONT_CALLS[i]);
    DWORD old;
    if (!VirtualProtect(s, 5, PAGE_EXECUTE_READWRITE, &old)) return 4;
    *(int32_t*)(s + 1) = (int32_t)((int64_t)(uintptr_t)t - (int64_t)(uintptr_t)(s + 5));
    VirtualProtect(s, 5, old, &old);
    FlushInstructionCache(GetCurrentProcess(), s, 5);
  }
  return 0;
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

#define PO_SLOTS (8 + MAX_LPRE)             /* 188, 189, six qualifying rounds, the pre-rounds */
static uint32_t* g_po_tab = 0;               /* low ids the title takes as play-offs; 0xffff empty */
static void po_fill(void)
{
  if (!g_po_tab) return;
  uint32_t v[PO_SLOTS];
  v[0] = UEL_PO; v[1] = UECL_PO;
  for (int i = 3; i < 9; i++) v[i - 1] = g_qreg[i] ? g_qreg[i] : 0xffff;
  for (int i = 0; i < MAX_LPRE; i++) v[8 + i] = i < g_nlpre ? g_lpre[i].reg : 0xffff;
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
    if (qa >= 0 && g_tramp_txtget) {
      static int said = 0;
      if (said < 4) { said++; logf("fl26swiss: match title -- regulation %u named %s qualifying round", (unsigned)(uint16_t)phase, qa / NQ == 1 ? "3rd" : "2nd"); }
      t = qa / NQ == 1 ? QR3_TEXT : QR2_TEXT;
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
  s[n++] = 0x3d; *(uint32_t*)(s + n) = 0x23ff; n += 4;      /* cmp eax, 8*1024+0x3ff */
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
      reg = (uint16_t)((actcomp_fn)(uintptr_t)(g_base + ACTCOMP_RVA))(*(uint32_t*)(blk + 0x1787b5c),
                                                                       *(uint16_t*)(blk + 0x1642a1c), 0, 0);
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
  uint16_t xr[3]; uint32_t xt[3]; int nx = 0;
  for (int st = 2; st >= 0; st--) {                       /* 2nd qualifying, 3rd qualifying, play-off */
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
    xt[nx] = st == 2 ? QR2_TEXT : st == 1 ? QR3_TEXT : kopo_window(ci) ? KOPO_TEXT : 0x3a20010u;
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
 * full region (0..127) from the byte at +0x2fe, which the module marks with 0x5a at +0x2ff,
 * and the 6-bit field at +0x30c bits 7..12 holds min(region, 63); without it the 6-bit field
 * is the region. An unmarked record (an old career fl26join has not repaired yet) falls back
 * to the field. */
static unsigned rec_region(const unsigned char* rr)
{
  static const unsigned char NEW[7] = { 0x0f,0xb6,0x80,0xfe,0x02,0x00,0x00 };   /* fl26reg128 at 0x141541639 */
  unsigned six = (*(const uint32_t*)(rr + 0x30c) >> 7) & 0x3f;
  if (g_base && !memcmp((const void*)(uintptr_t)(g_base + 0x1541639), NEW, sizeof NEW)
      && rr[0x2ff] == 0x5a && rr[0x2fe] <= 127)
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
    unsigned key = rec_region(rr);   /* key - 12 fits the stub's signed imm8 for every key 0..127 */
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
    for (unsigned i = 0; i < g_carry_keys; i++) if (g_carry_stub[12 + 5 * i] == imm) have = 1;
    if (have || g_carry_keys >= CARRY_SLOTS) continue;
    g_carry_stub[12 + 5 * g_carry_keys++] = imm;
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

/* Fase 4 (31.10., the Liga FUTVE from January to December): a split phase's own round days, from
   the world file's `splitdays <reg> d,d,...` lines (fl26_swiss_splitdays: reg, n, n days, ...). A
   phase named there takes them as they are, in place of its share of the Scottish line. */
#define MAX_SPLITDAYS 8
typedef struct { uint16_t reg, n; uint16_t day[64]; } splitdays_t;
static splitdays_t g_sdays[MAX_SPLITDAYS]; static int g_nsdays = 0;
__declspec(dllexport) int fl26_swiss_splitdays(const uint16_t* v, int n)
{
  g_nsdays = 0;
  for (int i = 0; v && i + 2 <= n && g_nsdays < MAX_SPLITDAYS; ) {
    uint16_t reg = v[i], c = v[i + 1];
    if (i + 2 + c > n) break;
    splitdays_t* d = &g_sdays[g_nsdays];
    d->reg = reg; d->n = c > 64 ? 64 : c;
    for (int j = 0; j < d->n; j++) d->day[j] = v[i + 2 + j];
    int ok = d->n > 0;
    for (int j = 0; j < d->n; j++) ok &= d->day[j] < 365 && (j == 0 || d->day[j] > d->day[j - 1]);
    if (ok) g_nsdays++;
    else logf("fl26swiss: splitdays %u -- days not rising within the year; left out", (unsigned)reg);
    i += 2 + c;
  }
  logf("fl26swiss: %d split phase(s) dated on their own days", g_nsdays);
  return g_nsdays;
}
static const splitdays_t* splitdays_of(uint16_t id)
{
  for (int i = 0; i < g_nsdays; i++) if (g_sdays[i].reg == id) return &g_sdays[i];
  return 0;
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
  const splitdays_t* own = splitdays_of(id);
  if (own && own->n >= n) {
    for (uint32_t i = 0; i < n; i++) { r[i].day = own->day[i]; r[i].round = i; r[i].kind = FL26_DATE_KIND_LEAGUE; }
    v->e = v->b + (size_t)n * sizeof(date_t);
    if (!seen)
      logf("fl26swiss: reg %u -- split %s of %u: %u rounds on its own days %u..%u (splitdays)",
           (unsigned)id, part == 2 ? "regular phase" : "group", (unsigned)s->total, n, r[0].day, r[n - 1].day);
    if (!seen && part == 2 && id > 175) check_reg(id, "dated");
    return rv;
  }
  if (own && !seen)
    logf("fl26swiss: reg %u -- splitdays gives %u day(s) for %u rounds; the August-May line instead", (unsigned)id, own->n, n);
  uint16_t line[64]; size_t L;
  if (T <= 38) {
    size_t skip = 38 - T < SPLIT_SKIP ? 38 - T : SPLIT_SKIP;
    L = 38 - skip; for (size_t i = 0; i < L; i++) line[i] = SCOT_DAYS[skip + i];
  }
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
#define MAX_DATELIKE 32
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
  if (n > MAX_DATELIKE) n = MAX_DATELIKE;
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
    if (have) dl_last_note(id, (int)((date_t*)v->b)[have - 1].day);   /* the ceremony's final day */
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
    uint64_t rv = ((date_fn)(uintptr_t)g_tramp_date)((reg & ~(uint64_t)0xffff) | (uint16_t)((id & ~0x3ff) | 2), vec);
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
           aug ? "August" : "knockout", qi >= 0 ? QSTAGE[qi / NQ] : "play-off", days[0], days[1], (unsigned)have);
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
 * holds more than 32 clubs. */
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
    if (rec && (rec[0x30c] & 0x7f) > 32) {
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

/* ---- the automatic Liga FUTVE (30.10.) ----
 * Felix: a club that wins the Apertura and the Clausura is the Liga FUTVE champion at once, with the
 * Final del FUTVE's title and logo, no match played. The season row alone did not show in the
 * Palmarés: for the running season it asks the game who won each competition -- the rights code
 * (0x1415799e0, type 0 = winner), which for an unplayed final answers nobody. So for the final of two
 * cups the answer is ours whenever both feeding finals went to one club this season. */
static const unsigned char SIG_RIGHT[15] = { 0x48,0x89,0x5c,0x24,0x18, 0x48,0x89,0x74,0x24,0x20, 0x66,0x89,0x54,0x24,0x10 };
unsigned char* g_tramp_right = 0;
static uint32_t ff_auto_champion(uint16_t reg)
{
  for (int k = 0; k < g_nccup; k++) {
    const ccup_t* c = &g_ccup[k];
    if (!c->src[0] || c->ko != reg) continue;
    uint32_t w1 = ccup_src_winner(c->src[0]), w2 = ccup_src_winner(c->src[1]);
    return w1 && w2 && same_club(w1, w2) ? w1 : 0;
  }
  return 0;
}
static unsigned char* g_cer_pres;
static int g_final_day;
uint32_t* right_handler(uint32_t* out, uint64_t source, uint32_t type)
{
  static int busy = 0;
  if ((g_cer_pres || g_final_day >= 0) && !busy) {  /* 31.10. (read-only): who asks the rights code on a final's day */
    static int said = 0; static uint64_t ls = 0; static uint32_t lt = 0xffffffffu;
    if (said < 150 && ((uint16_t)source != (uint16_t)ls || type != lt)) {
      said++; ls = source; lt = type;
      uint32_t* r = ((right_fn)(uintptr_t)g_tramp_right)(out, source, type);
      logf("fl26swiss: ceremony -- rights asked: source %llu type %u -> %08x (from %p)", (unsigned long long)source, type,
           r ? *r : 0, __builtin_return_address(0));
      return r;
    }
  }
  if (type == 0 && !busy && out) {
    busy = 1;
    uint32_t w = ff_auto_champion((uint16_t)source);
    busy = 0;
    if (w) { *out = w; return out; }
  }
  return ((right_fn)(uintptr_t)g_tramp_right)(out, source, type);
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
#define STATE_MAXREC (FINAL_N + 32 + 1 + 64)
#define STATE_BUILT 2
/* B240 (antonimus 25.10.): a first season's places go by squad strength, worked out once and kept
   for the summer -- in memory. A save loaded weeks later worked it out again from squads that had
   changed since (two Ecuadorian clubs at 77.5 and 77.8 swapped), and the Libertadores groups'
   fill on day 41 put in the club now second, LDU Quito, which had played and lost the
   Pre-Libertadores, in place of the one the season had started with. The order is kept in the
   file too, and read back with the rest. Older DLLs pass these records over (kind > 2). */
#define STATE_SEED 3
/* fase 4 (31.10., Felix: the second Liga FUTVE won, the Palmares still at 1): a title the DLL put in
   the user's trophy cabinet, by regulation and calendar year (game_date / 365), kept in the file so
   a reload never adds it twice and a later season's is added again. Older DLLs pass these over. */
#define STATE_TITLE 4
typedef struct { uint16_t reg; int year; } titlemark_t;
static titlemark_t g_tmark[64]; static int g_ntmark = 0;
static int tmark_has(uint16_t reg, int year)
{
  for (int i = 0; i < g_ntmark; i++) if (g_tmark[i].reg == reg && g_tmark[i].year == year) return 1;
  return 0;
}
static void tmark_add(uint16_t reg, int year)
{
  if (tmark_has(reg, year)) return;
  if (g_ntmark >= 64) { memmove(g_tmark, g_tmark + 1, 63 * sizeof g_tmark[0]); g_ntmark = 63; }
  g_tmark[g_ntmark].reg = reg; g_tmark[g_ntmark].year = year; g_ntmark++;
}
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
  for (int i = 0; i < g_ntmark && u && nw < STATE_MAXREC; i++) {
    state_rec_t* r = &want[nw++];
    memset(r, 0, sizeof *r);
    r->user = u; r->gdate = g_tmark[i].year * 365; r->kind = STATE_TITLE; r->n = 1; r->reg = g_tmark[i].reg;
    r->club[0] = (uint32_t)g_tmark[i].year;
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
    if (later) logf("fl26swiss: state -- %d keep(s) of a later date left out: a save of an earlier day loaded", later);
  }
  g_st_off = off; g_st_day = an; g_st_user = u; g_st_read_back = 0;
  const char* p = state_path();
  HANDLE h = p ? state_open(p, 0) : 0;
  if (!h) return;
  static state_rec_t best[STATE_MAXREC];
  int nb = 0;
  state_rec_t r; DWORD got = 0;
  while (ReadFile(h, &r, sizeof r, &got, 0) && got == sizeof r) {
    if (r.check != state_check(&r) || r.user != u || r.gdate > gn || gn - r.gdate > STATE_AGE ||
        r.kind > STATE_TITLE || !r.n || r.n > FINAL_MAX ||
        ((r.kind == 1 || r.kind == STATE_BUILT) && r.n != 1)) continue;
    if (r.kind == STATE_TITLE) { tmark_add(r.reg, (int)r.club[0]); continue; }   /* every one, not the newest */
    int k = 0;
    while (k < nb && (best[k].kind != r.kind || best[k].reg != r.reg)) k++;
    if (k == nb) { if (nb >= STATE_MAXREC) continue; nb++; }
    else if (r.gdate < best[k].gdate) continue;
    best[k] = r;                                   /* the newest; of one day, the last written */
  }
  CloseHandle(h);
  int nf = 0, nc = 0, ns = 0, built = -1;
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
    if (best[k].kind == STATE_SEED) {
      final_t* f = 0;
      for (int i = 0; i < g_nseed; i++) if (g_seed[i].reg == best[k].reg) f = &g_seed[i];
      if (f && f->day >= day) continue;
      if (!f) { if (g_nseed >= 64) continue; f = &g_seed[g_nseed++]; }
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
      if (!w) { if (g_ncupwin >= 32) continue; w = &g_cupwin[g_ncupwin++]; }
      w->reg = best[k].reg; w->day = day; w->club = best[k].club[0];
      nc++;
    }
  }
  g_st_busy = 0;
  if (nf || nc || ns)
    logf("fl26swiss: state -- %d final table(s), %d cup winner(s) and %d squad-strength order(s) of club %08x's career read back on day %d (%s)",
         nf, nc, ns, u, today(), STATE_FILE);
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
  if (d == last || (futve_cal() ? td < 290 : (td < 60 || td > 180)) || !g_nnocarry) return;   /* fase 4: after the Clausura's regular phase */
  last = d;
  for (int k = 0; k < g_nsplits; k++) {
    const split_t* s = &SPLITS[k];
    if (!nocarry(s->total) || !s->group[0]) continue;
    final_t* f = final_of(s->total);
    if (f && d >= f->day && d - f->day < 60) continue;
    uint16_t regs[2] = { s->regular, s->group[0] };
    final_t t;
    int played, n = count_table(regs, 2, &t, &played);
    if (n < 4 || played < n * (n - 1)) {
      static int said_y = -1;   /* fase 4: why the January-December Liga FUTVE has no year-end table yet */
      if (futve_cal() && said_y != d / 30) { said_y = d / 30;
        logf("fl26swiss: reg %u -- Apertura + Clausura table not kept yet on day %d: %d club(s), %d of %d matches played",
             (unsigned)s->total, td, n, played, n * (n - 1)); }
      continue;
    }
    if (!f && !(f = final_new(s->total))) continue;
    *f = t; f->reg = s->total; f->day = d;
    logf("fl26swiss: reg %u -- Apertura + Clausura table from %d matches kept as the final table: "
         "%08x %d pts, %08x %d pts ... last %08x %d pts", (unsigned)s->total, played,
         t.club[0], g_ctab_pts[0], t.club[1], g_ctab_pts[1], t.club[n - 1], g_ctab_pts[2]);
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
static int g_q_fill_year[NQR] = { -1, -1, -1, -1, -1, -1, -1, -1, -1 };
static void q_fill(int p)
{
  int d = today();
  if (d < 205 || d > (int)qr_day(0, 1)) return;
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
  canon_list(g_q[p], Q_N, "qualifying reg", reg);   /* B312 */
  for (int k = 0; k < Q_N / 2; k++)
    ((freetab_fn)(uintptr_t)(g_base + FREETAB_RVA))(0, q_tie_of(p, k));
  u32vec va = { g_q[p], g_q[p] + Q_N, g_q[p] + Q_N };
  ((setclr_fn)(uintptr_t)g_tramp_setcl)(reg, &va, 1);
  for (int k = 0; k < Q_N / 2; k++) {
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
  for (int k = 0; k < Q_N / 2; k++) { int x = ccup_matches(q_tie_of(p, k)); if (x > 0) mt += x; }
  if (m <= 0 && mt <= 0) {                          /* the ties are their own rows: register them too */
    uint16_t ties[Q_N / 2];
    for (int k = 0; k < Q_N / 2; k++) ties[k] = q_tie_of(p, k);
    struct { uint16_t* b; uint16_t* e; uint16_t* c; } tv = { ties, ties + Q_N / 2, ties + Q_N / 2 };
    ((regall_fn)(uintptr_t)(g_base + REGALL_RVA))(0, &tv);
    run_flush();
    m = ccup_matches(reg); mt = 0;
    for (int k = 0; k < Q_N / 2; k++) { int x = ccup_matches(q_tie_of(p, k)); if (x > 0) mt += x; }
  }
  logf("fl26swiss: %s %s -- day %d: reg %u filled, started and registered; %d match record(s) under it, %d under its ties",
       QNAME(p), d, (unsigned)reg, m, mt);
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
#if TODAY_OFF == 0x19115e4
#define CAL_STRIDE 0x6c4
#define CAL_IDCAP  792
#define CAL_COUNT  0x630
#else
#define CAL_STRIDE 0x2c4
#define CAL_IDCAP  280
#define CAL_COUNT  0x230
#endif
#define CAL_BASE   (TODAY_OFF - 365 * CAL_STRIDE)
#define MREC_RVA   0x14bb280      /* (blk, u16 id) -> the match record, the scheduler's own lookup */
typedef unsigned char* (*mrec_fn)(void* blk, uint64_t id);
static uint16_t g_cal_first[65536];
#ifdef FL26_RCAL_TEST
int rcal_test_recday(uint16_t id);
#endif
static int rec_day(unsigned char* blk, uint16_t id)
{
#ifdef FL26_RCAL_TEST
  return rcal_test_recday(id);
#endif
  unsigned char* m = ((mrec_fn)(uintptr_t)(g_base + MREC_RVA))(blk, id);
  if (!m || *(uint16_t*)m != id) return -1;
  int mo = m[8 + 2], dd = m[8 + 3];
  if (mo < 1 || mo > 12 || dd < 1 || dd > 31) return -1;
  return MONTH0[mo - 1] + dd - 1;
}
static void cal_dedupe(void)
{
  unsigned char* o = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
  unsigned char* blk = o ? *(unsigned char**)(o + 0x48) : 0;
  if (!blk) return;
  static uint8_t seen[65536 / 8];
  int same = 0, cross = 0, fixed = 0, total = 0, ex = 0;
  char exs[200]; size_t el = 0; exs[0] = 0;
  memset(g_cal_first, 0xff, sizeof g_cal_first);
  for (int d = 0; d < 365; d++) {
    unsigned char* day = blk + CAL_BASE + (size_t)d * CAL_STRIDE;
    uint16_t* ids = (uint16_t*)day;
    int n = 0, w = 0, removed = 0;
    while (n < CAL_IDCAP && ids[n] != 0xffff) n++;
    for (int i = 0; i < n; i++) {
      uint16_t v = ids[i];
      if (seen[v >> 3] & (1 << (v & 7))) {
        removed++;
        if (ex < 6 && el < sizeof exs - 24) { el += snprintf(exs + el, sizeof exs - el, " %u@%d", v, d); ex++; }
        continue;
      }
      seen[v >> 3] |= (uint8_t)(1 << (v & 7));
      ids[w++] = v;
    }
    for (int i = 0; i < w; i++) seen[ids[i] >> 3] = 0;
    if (removed) {
      for (int i = w; i < n; i++) ids[i] = 0xffff;
      uint16_t* cnt = (uint16_t*)(day + CAL_COUNT);
      *cnt = (uint16_t)(*cnt >= removed ? *cnt - removed : w);
      same += removed;
    }
    total += w;
    /* the same match on two days */
    for (int i = 0; i < w; i++) {
      uint16_t v = ids[i];
      if (g_cal_first[v] == 0xffff) { g_cal_first[v] = (uint16_t)d; continue; }
      cross++;
      int e = g_cal_first[v], rd = rec_day(blk, v), drop = rd == d ? e : rd == e ? d : -1;
      if (ex < 6 && el < sizeof exs - 32) { el += snprintf(exs + el, sizeof exs - el, " %u@%d+%d(rec %d)", v, e, d, rd); ex++; }
      if (drop < 0) continue;
      unsigned char* dr = blk + CAL_BASE + (size_t)drop * CAL_STRIDE;
      uint16_t* dl = (uint16_t*)dr;
      int m = 0; while (m < CAL_IDCAP && dl[m] != 0xffff) m++;
      for (int k = 0; k < m; k++)
        if (dl[k] == v) {
          memmove(dl + k, dl + k + 1, (size_t)(m - k - 1) * 2); dl[m - 1] = 0xffff;
          uint16_t* cnt = (uint16_t*)(dr + CAL_COUNT); if (*cnt) (*cnt)--;
          fixed++;
          if (drop == d) { w--; i--; }               /* this day's list moved down by one */
          break;
        }
      g_cal_first[v] = (uint16_t)(rd == d ? d : e);
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
    int c = g_cal_first[*(uint16_t*)e];
    if (c == 0xffff || c == d || c >= 365) continue;
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
/* Fase 4 (31.10., Felix: "first year of ML, no Copa Venezuela"): the January-December Copa (255)
   was put on the New Year builder's list (fl26joindll, cup= of the league line), but the builder
   shows the door only the ids whose runs-this-season flag (+0x304 bit 8) is set, and the New Year
   teardown (which closes it with the cup it is dated as) leaves it clear: never entered, never a
   match. So, as the calendar Super Cup: before its first day, with no match of its own, its field
   is set to the league's clubs, the flag set, the stage started and register_all asked for it --
   the door then enters it and the game draws its bracket (cupdraw seeded). */
/* Fase 4 (31.10., second try at the second season): adding the phases to the New Year teardown
   list did nothing -- fl26join takes ours back out of it ("ours kept out: [191 192]"). What keeps
   the Apertura out is fl26join's register_all test on day 41: a phase in a season (+0x304 bit 8)
   with a table is "already in a season". So before day 41 the regular phase of a January-December
   split of ours has that flag cleared (once a year): register_all then appends it with its league,
   and the door, which resets a league of ours' season year, enters it for the new season. */
static void futve_phase_reopen(void)
{
  int d = today();
  if (!futve_cal() || d < 1 || d > 40) return;
  static int done_year = -1;
  int y = abs_day() / 365;
  if (done_year == y) return;
  done_year = y;
  for (int i = 0; i < g_nsplits; i++) {
    if (!calyear(SPLITS[i].total)) continue;
    unsigned char* r = get_rec(SPLITS[i].regular);
    if (!r) continue;
    if (ccup_matches(SPLITS[i].regular) > 0) continue;   /* in this season already (a career's first, from 1 January) */
    uint32_t* fl = (uint32_t*)(r + 0x304);
    int was = (*fl >> 8) & 1;
    *fl &= ~(1u << 8);
    logf("fl26swiss: reg %u -- a January-December split's regular phase reopened on day %d for its new season "
         "(runs-this-season flag %d -> 0, season year %04x): register_all takes it with its league on day 41",
         (unsigned)SPLITS[i].regular, d, was, *(uint16_t*)(r + 0x2fc));
  }
}
/* Fase 4 (31.10., Felix): the Apertura's and the Clausura's league phases are the same fourteen clubs,
   every one plays them whatever happens -- so the Clausura is on the calendar from February with the
   Apertura, not dealt by the game in May. Once the regular phase has its matches this season and the
   group none: the group's field is set to the regular phase's clubs, the flag set, the stage started
   and register_all asked for it; split_dates gives it its splitdays. The split progression in May
   then leaves it alone (prog_handler_inner). */
static void futve_clausura_early(void)
{
  int d = today();
  /* from day 0: in a career's first season the Apertura has its matches from the creation on 1 January */
  if (!futve_cal() || d < 0 || d > 120) return;
  static int done_year = -1;
  int y = abs_day() / 365;
  if (done_year == y) return;
  for (int i = 0; i < g_nsplits; i++) {
    const split_t* sp = &SPLITS[i];
    if (!calyear(sp->total) || !sp->group[0] || sp->group[1] || !nocarry(sp->total)) continue;
    unsigned char* rr = get_rec(sp->regular);
    unsigned char* gr = get_rec(sp->group[0]);
    if (!rr || !gr || ccup_matches(sp->regular) <= 0) continue;    /* the Apertura not in yet */
    done_year = y;
    if (ccup_matches(sp->group[0]) > 0) continue;                   /* already made this year */
    uint32_t n = rec_count(rr);
    if (n < 4 || n > 32) continue;
    uint32_t clubs[32];
    for (uint32_t c = 0; c < n; c++) clubs[c] = rec_clubs(rr)[c];
    u32vec v = { clubs, clubs + n, clubs + n };
    ((setclr_fn)(uintptr_t)g_tramp_setcl)(sp->group[0], &v, 1);
    run_flush();
    *(uint32_t*)(gr + 0x304) |= 1u << 8;
    start_stage(0, sp->group[0]);
    uint16_t id = sp->group[0];
    struct { uint16_t* b; uint16_t* e; uint16_t* c; } rv = { &id, &id + 1, &id + 1 };
    ((regall_fn)(uintptr_t)(g_base + REGALL_RVA))(0, &rv);
    run_flush();
    canon_groups(sp);
    logf("fl26swiss: reg %u -- the Clausura made on day %d with the Apertura: %u club(s) of reg %u, %d match record(s)",
         (unsigned)sp->group[0], d, n, (unsigned)sp->regular, ccup_matches(sp->group[0]));
  }
}
#define FUTVE_COPA 255
static void futve_copa_fill(void)
{
  int d = today();
  if (!futve_cal() || !g_tl_total || d < 0 || d > 66) return;
  unsigned char* rec = get_rec(FUTVE_COPA);
  if (!rec || ccup_matches(FUTVE_COPA) > 0) return;
  static int tried_year = -1;
  int y = abs_day() / 365;
  if (tried_year == y) return;
  unsigned char* lg = get_rec(g_tl_total);
  const split_t* sp = 0;
  for (int i = 0; i < g_nsplits; i++) if (SPLITS[i].total == g_tl_total) sp = &SPLITS[i];
  unsigned char* src = sp ? get_rec(sp->regular) : 0;
  if (!src || rec_count(src) < 4) src = lg;
  uint32_t n = src ? rec_count(src) : 0;
  if (n < 4 || n > 32) return;                      /* the league's clubs not there yet: next day */
  tried_year = y;
  uint32_t clubs[32];
  for (uint32_t i = 0; i < n; i++) clubs[i] = rec_clubs(src)[i];
  u32vec v = { clubs, clubs + n, clubs + n };
  ((setclr_fn)(uintptr_t)g_tramp_setcl)(FUTVE_COPA, &v, 1);
  run_flush();
  *(uint32_t*)(rec + 0x304) |= 1u << 8;            /* in this season: the door asks for it */
  start_stage(0, FUTVE_COPA);
  uint16_t id = FUTVE_COPA;
  struct { uint16_t* b; uint16_t* e; uint16_t* c; } rv = { &id, &id + 1, &id + 1 };
  ((regall_fn)(uintptr_t)(g_base + REGALL_RVA))(0, &rv);
  run_flush();
  logf("fl26swiss: Copa Venezuela %u -- day %d: %u club(s) of reg %u set, registered: %u club(s), %d match record(s)",
       (unsigned)FUTVE_COPA, d, n, (unsigned)rec_id(src), (unsigned)rec_count(rec), ccup_matches(FUTVE_COPA));
}
static uint32_t futve_champion_kept(int ad);
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

    /* fase 4 (the Liga FUTVE January-December): its champion is the finals', the Final del FUTVE's
       winner in December or the club that won both -- not the accumulated table's leader; the cup's
       runner-up plays it when that club won the Copa Venezuela too (as aug_scup_fill_days) */
    if (g_tl_total && cs->league == g_tl_total) {
      uint32_t lf = futve_champion_kept(abs_day());
      if (lf) champion = lf;
      if (same_club(champion, cupwin)) {
        uint32_t cr = knockout_runner_now(cs->cup);
        if (cr && !same_club(cr, champion)) runner = cr;
      }
      logf("fl26swiss: calendar Super Cup %u -- day %d: Liga FUTVE champion %08x (%s), cup %u winner %08x",
           (unsigned)cs->reg, d, champion, lf ? "the finals'" : "none kept: the table's", (unsigned)cs->cup, cupwin);
    }
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


/* 30.10. (Felix): the Supercopa de Venezuela is the Liga FUTVE champion's -- the Final del FUTVE's
   winner, or the club that won both the Apertura and the Clausura finals -- never the accumulated
   table's leader. Read from the finals kept this season (the last within 120 days). 0: none known. */
static uint32_t futve_champion_kept(int ad)
{
  int fk = -1;
  for (int k = 0; k < g_nccup; k++) if (g_ccup[k].src[0]) fk = k;
  if (fk < 0 || ad < 0) return 0;
  const ccup_t* c = &g_ccup[fk];
  cupwin_t* f = cupwin_of(c->ko);
  if (f && (f->club >> 14) && ad >= f->day && ad - f->day < 120) return f->club;
  cupwin_t* a = cupwin_of(c->src[0]);
  cupwin_t* b = cupwin_of(c->src[1]);
  /* fase 5 (01.11.): the Apertura's final (June) is 200+ days old at the next Supercopa and the
     CONMEBOL fills of January -- 150 lost it ("none kept: the table's") */
  if (a && b && (a->club >> 14) && (b->club >> 14) && ad >= a->day && ad - a->day < 300 &&
      ad >= b->day && ad - b->day < 300 && same_club(a->club, b->club)) return a->club;
  return 0;
}

/* fase 5 (01.11., Felix: "que venezuela sea lo más real posible"): the Liga FUTVE's eight
   continental places as the real league gives them, read through (reg 11, position) by every
   access path (access_club_kept, cwc_club) once a final table of the accumulated league is kept:
     1 the champion (the Final del FUTVE's winner, or the club that won both finals) -- Libertadores
     2 the best of the accumulated table besides the champion and the runner-up -- Libertadores
     3 the runner-up (the Final del FUTVE's loser) -- Libertadores phase 2
     4 the next of the table -- Libertadores phase 1
     5, 6 the Apertura's and the Clausura's final losers -- Sudamericana first stage
     7, 8 the next two of the table -- Sudamericana first stage
   A club already placed hands its place to the next of the table. Only with the modern CONMEBOL
   competitions; 0 (the table as before) otherwise or past position 8. */
static uint32_t futve_runner_kept(uint16_t ko, int ad)
{
  cupwin_t* r = cupwin_of((uint16_t)(FUTVE_RUNNER | ko));
  /* fase 5 (01.11.): the Apertura's final is in June, its loser goes abroad next January -- 150
     days was too short (the second year read none) */
  return r && (r->club >> 14) && ad >= r->day && ad - r->day < 300 ? r->club : 0;
}
static uint32_t futve_cont_club(uint16_t reg, int rank, const char** how)
{
  if (!g_tl_total || reg != g_tl_total || rank < 1 || rank > 8 || !futve_cal() || !modern_conmebol()) return 0;
  final_t* f = final_of(reg);
  int ad = abs_day();
  if (!f || f->n < 10 || ad < f->day || ad - f->day > 300) return 0;
  int fk = -1;
  for (int k = 0; k < g_nccup; k++) if (g_ccup[k].src[0]) fk = k;
  uint32_t C = futve_champion_kept(ad), U = 0, AL = 0, CL = 0;
  if (!C) C = f->club[0];
  if (fk >= 0) {
    U = futve_runner_kept(g_ccup[fk].ko, ad);
    AL = futve_runner_kept(g_ccup[fk].src[0], ad);
    CL = futve_runner_kept(g_ccup[fk].src[1], ad);
  }
  if (U && same_club(U, C)) U = 0;
  uint32_t used[16]; size_t nu = 0, o[8];
  #define FC_NEXT() ({ uint32_t x_ = 0; for (unsigned i_ = 0; i_ < f->n; i_++) \
      if (!has_club(used, nu, f->club[i_])) { x_ = f->club[i_]; break; } x_; })
  used[nu++] = C; if (U) used[nu++] = U;
  o[0] = C;
  o[1] = FC_NEXT(); used[nu++] = o[1];
  o[2] = U ? U : FC_NEXT(); if (!U) used[nu++] = o[2];
  o[3] = FC_NEXT(); used[nu++] = o[3];
  o[4] = AL && !has_club(used, nu, AL) ? AL : FC_NEXT(); used[nu++] = o[4];
  o[5] = CL && !has_club(used, nu, CL) ? CL : FC_NEXT(); used[nu++] = o[5];
  o[6] = FC_NEXT(); used[nu++] = o[6];
  o[7] = FC_NEXT();
  #undef FC_NEXT
  static int said = -1;
  if (said != f->day) {
    said = f->day;
    logf("fl26swiss: Liga FUTVE continental places (fase 5) -- champion %08x, runner-up %08x, finals' losers %08x / %08x: "
         "Lib %08x %08x, F2 %08x, F1 %08x, Suda %08x %08x %08x %08x", C, U, AL, CL,
         (unsigned)o[0], (unsigned)o[1], (unsigned)o[2], (unsigned)o[3], (unsigned)o[4], (unsigned)o[5], (unsigned)o[6], (unsigned)o[7]);
  }
  *how = "Liga FUTVE continental order";
  return (uint32_t)o[rank - 1];
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
    int futve = g_tl_total && cs->league == g_tl_total;
    if (futve) {
      /* the Liga FUTVE: its champion (the finals'), against the Copa Venezuela's winner -- or the
         cup's runner-up when one club won both */
      uint32_t lf = futve_champion_kept(ad);
      static int said_lf = -1;
      if (lf) champion = lf;
      else if (said_lf != log_season()) {
        said_lf = log_season();
        logf("fl26swiss: August-May Super Cup %u -- day %d: no Liga FUTVE champion kept; the table's leader goes",
             (unsigned)cs->reg, d);
      }
      if (cs->cup && cupwin && same_club(champion, cupwin)) {
        uint32_t cr = knockout_runner_now(cs->cup);
        if (cr && !same_club(cr, champion)) runner = cr;
        else {
          static int said_cr = -1;
          if (said_cr != log_season()) {
            said_cr = log_season();
            logf("fl26swiss: August-May Super Cup %u -- day %d: the cup %u's runner-up not read; the league's runner-up goes",
                 (unsigned)cs->reg, d, (unsigned)cs->cup);
          }
        }
      }
    }
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
         by_runner ? (futve && cs->cup ? "cup runner-up" : "league runner-up") : "cup winner", opponent >> 14,
         ccup_matches(cs->reg), ccup_unplayed(cs->reg));
  }
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

/* B-FUTVE: a jump of the calendar over a day a cup of ours needs. The day loop is where the DLL
   fills a cup (fill=), and the game only stops on a match day when the cup has matches; a jump
   over its fill day with the cup still empty, or over a match day of a cup filled that season,
   means the DLL never had that day -- a Fast Forward (c0ad4dc: 37 days let through) -- and the
   cup is missing or half played. Said loudly, so a test of that season is known to be void. */
static void ccup_jump_check(int from, int to)
{
  int said = 0;
  if (from < 0 || to < from) return;
  if (to - from > 400) from = to - 400;
  for (int a = from; a <= to; a++) {
    int doy = a % 365, ya = (a + 183) / 365;
    for (int k = 0; k < g_nccup; k++) {
      const ccup_t* c = &g_ccup[k];
      const char* what = 0;
      int filled = c->filled_year == ya && !(c->src[0] && g_ccup_nf[k] < 2);   /* same champion: no final played */
      if (c->fill && c->fill == doy && !filled) what = "fill day, the cup still empty";
      for (int i = 0; filled && i < c->gnd && !what; i++) if (c->gdays[i] == doy) what = "group matchday";
      /* fase 5: a two-club knockout (the Recopa) plays its last day only -- the six before are not its */
      for (int i = (c->n == 2 && c->nd >= 7) ? c->nd - 1 : 0; filled && i < c->nd && !what; i++) if (c->days[i] == doy) what = "knockout/final day";
      if (!what || !ccup_world(c)) continue;
      if (said++ < 12)
        logf("fl26swiss: AVISO -- the calendar jumped over day %d (%s of cup %u) without the DLL seeing it "
             "(days %d..%d, Fast Forward?): this season's cup %u is not reliable",
             doy, what, (unsigned)c->ko, from % 365, to % 365, (unsigned)c->ko);
    }
  }
  if (said > 12) logf("fl26swiss: AVISO -- and %d more day(s) of our cups jumped over", said - 12);
}

/* ---- title probe (29.10., FUTVE): where does the game write a title into the career? ----
 * The palmarés is the game's own bookkeeping: "Liga FUTVE" (league 11, cid 130) goes to the leader
 * of the accumulated table on day 142, a final's title on its day, and nothing is written for a final
 * that is not played. To move or write a title the record must be found first. So around those days
 * the career block (the owner's +0x48, where today() and the rights code read) is copied once a day
 * and compared with the day before: a dword that changed to the user's club (its handle or team id,
 * handle >> 14), or a changed competition id of ours with the user's club within 64 bytes, is logged
 * with its neighbourhood. Read-only; nothing is written. */
static unsigned char* g_tp_snap = 0; static size_t g_tp_len = 0; static int g_tp_day = -1;
static unsigned char* g_tp_base = 0;
static int tp_day_on(int d)
{
  return (d >= 12 && d <= 18) || (d >= 139 && d <= 145) || (d >= 161 && d <= 175);
}
static void tp_hex(const unsigned char* p, char* out)
{
  static const char H[] = "0123456789abcdef";
  for (int i = 0; i < 32; i++) { out[2 * i] = H[p[i] >> 4]; out[2 * i + 1] = H[p[i] & 15]; }
  out[64] = 0;
}
static void title_probe(void)
{
  if (!FL26_TITLE_PROBES) return;
  int d = today();
  if (d < 0 || !tp_day_on(d)) { g_tp_day = -1; return; }
  unsigned char* o = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
  unsigned char* blk = o ? *(unsigned char**)(o + 0x48) : 0;
  if (!blk) return;
  MEMORY_BASIC_INFORMATION mi;
  if (!VirtualQuery(blk, &mi, sizeof mi) || mi.State != MEM_COMMIT) return;
  size_t len = (size_t)((unsigned char*)mi.BaseAddress + mi.RegionSize - blk);
  static int said_len = 0;
  if (!said_len++) logf("fl26swiss: title probe -- career block %p, region of %llu bytes after it", (void*)blk,
                        (unsigned long long)len);
  if (len > ((size_t)128 << 20)) len = (size_t)128 << 20;
  if (!g_tp_snap || g_tp_len < len) {
    if (g_tp_snap) VirtualFree(g_tp_snap, 0, MEM_RELEASE);
    g_tp_snap = (unsigned char*)VirtualAlloc(0, len, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE);
    g_tp_len = g_tp_snap ? len : 0; g_tp_day = -1;
    if (!g_tp_snap) return;
  }
  uint32_t u = state_user(), team = u >> 14;
  if (g_tp_day >= 0 && g_tp_base == blk && u) {
    static const uint16_t CIDS[] = { 130, 142, 129, 175, 134, 135, 11, 191, 192, 261, 262, 263 };
    int said = 0;
    size_t n = (len < g_tp_len ? len : g_tp_len) & ~(size_t)3;
    for (size_t i = 64; i + 68 <= n && said < 60; i += 4) {
      uint32_t a = *(uint32_t*)(g_tp_snap + i), b = *(uint32_t*)(blk + i);
      if (a == b) continue;
      int why = 0;
      if (b == u || b == team) why = 1;
      else {
        for (size_t c = 0; c < sizeof CIDS / sizeof *CIDS && !why; c++)
          if ((b & 0xffff) == CIDS[c] || (b >> 16) == CIDS[c]) why = 2;
        if (why == 2) {
          int close_by = 0;
          for (size_t j = i - 64; j < i + 64 && !close_by; j += 4)
            close_by = *(uint32_t*)(blk + j) == u || *(uint32_t*)(blk + j) == team;
          if (!close_by) why = 0;
        }
        /* 30.10.: the manager's Palmarés still had "Liga FUTVE" and "Final del FUTVE" with both lists
           corrected -- a third record, without the club beside it. Any slot of the Liga FUTVE (130) or
           the Final del FUTVE (175) that was empty and is not now. */
        if (!why) {
          uint16_t al = (uint16_t)a, ah = (uint16_t)(a >> 16), bl = (uint16_t)b, bh = (uint16_t)(b >> 16);
          if (((bl == 130 || bl == 175) && al != bl && (al == 0xffff || al == 0)) ||
              ((bh == 130 || bh == 175) && ah != bh && (ah == 0xffff || ah == 0))) why = 3;
        }
      }
      if (!why) continue;
      char h0[65], h1[65];
      tp_hex(blk + i - 16, h0); tp_hex(blk + i + 16, h1);
      logf("fl26swiss: title probe day %d (since day %d): blk+%#llx %08x -> %08x (%s) | %s | %s",
           d, g_tp_day, (unsigned long long)i, a, b,
           why == 1 ? "our club" : why == 2 ? "a cid near our club" : "cid 130/175 anywhere", h0, h1);
      said++;
    }
    if (said >= 60) logf("fl26swiss: title probe day %d: more changes, the first 60 shown", d);
    else if (!said) logf("fl26swiss: title probe day %d (since day %d): nothing of our club changed (%llu bytes)",
                         d, g_tp_day, (unsigned long long)n);
  }
  /* 29.10. run: the user's honours look like 12-byte rows {u32 cid, u16 reg, u8, u8, u32} at
     blk+0x17b59f0.. ((130,191,1,0x0d) written on day 0, (142,261,1,0) on day 15, (130,192,1,0x0d) and
     (130,11,1,0x0d) on day 142), and a {u16 reg, u32 club} winners list at blk+0x1798ca8 / 0x1799938.
     Their whole neighbourhood, whenever it changed, so the layout (start, header, count) can be read. */
  {
    static const size_t W[6][2] = { { 0x17b5900, 0x17b5b00 }, { 0x1798c40, 0x1798d00 }, { 0x17998c0, 0x1799980 },
                                    { 0x1f0b500, 0x1f0b600 }, { 0x1f22040, 0x1f22100 }, { 0x1f26a20, 0x1f26ae0 } };
    static unsigned char last[6][0x200]; static int have[6];
    for (int w = 0; w < 6; w++) {
      size_t a = W[w][0], b = W[w][1];
      if (b > len) continue;
      if (have[w] && !memcmp(last[w], blk + a, b - a)) continue;
      memcpy(last[w], blk + a, b - a); have[w] = 1;
      for (size_t q = a; q < b; q += 32) {
        char h[65]; tp_hex(blk + q, h);
        logf("fl26swiss: title dump day %d blk+%#llx %s", d, (unsigned long long)q, h);
      }
    }
  }
  memcpy(g_tp_snap, blk, len);
  g_tp_base = blk; g_tp_day = d;
}

/* ---- the Liga FUTVE title (0.2.5): the user's honours of the season ----
 * Found with the title probe (29.10.): the career block holds the user's honours of the running
 * season at blk+0x17b59e4 -- a header {u16 year, u8 month, u8 day} start, the same for the end,
 * u32 the club -- then 15 rows of 12 bytes {u32 competition id, u16 regulation, u8 won, u8 kind,
 * u32 0}, an empty row {0xffffffff, 0xffff, 0, 0, 0}. The game writes a league title for each phase
 * of a split league it ends: (130, 191, 1, 0x0d) on day 0, (130, 192, 1, 0x0d) and (130, 11, 1,
 * 0x0d) on day 142 -- one is enough for "Liga FUTVE 1" -- and a final of ours as (175, 263, 1, 0)
 * or (129, 262, 0, 1) for the runner-up. The Liga FUTVE is won only in the Final del FUTVE, or by
 * the club that won both feeding finals. So from January to June the rows of the split league are
 * taken out, and the user's win of the final of two cups becomes one league row (cid, total, 1,
 * 0x0d); a lost Final del FUTVE keeps its runner-up row. July and later: left alone (the block is
 * the finished season's until the next one is opened). */
#define HON_OFF   0x17b59e4
#define HON_ROWS  15
/* Fase 4 (31.10.): in the second year the block at HON_OFF still read 2025 -- it is the career's
   first season's, not the running one. The season blocks of the user's club around it: every
   {u16 year 2000..2200, u8 month 1..12, ...} with the user's club at +8, the latest year taken.
   Said once a session (every candidate), and again when the latest moves. */
static unsigned char* hon_block_now(unsigned char* blk, uint32_t u);
/* fase 4 (31.10., Felix: one Liga FUTVE row, still "1"): a cabinet record (0x648 bytes) is
   {u16 reg, u16 0} then two parallel lists of 200: the winners (u32 club) from +4 and the dates
   (u16 year, u8 month, u8 day; empty ffff0000) from +0x324 -- 261 won twice: e9070611 ea070611.
   The Palmares counts the dates. One win more: the club and a date on the ends of both lists, the
   date the given one if sane and of a year not there yet, else the running season's year with the
   last entry's month and day. Returns the wins after. */
static unsigned rec_append(unsigned char* blk, uint32_t u, unsigned char* f, uint32_t club, uint32_t date)
{
  const size_t DAT = 0x324, N = 200;
  size_t k = 0; while (k < N && *(uint32_t*)(f + 4 + 4 * k) != 0xffffffffu) k++;
  if (k >= N) return (unsigned)k;
  uint16_t dy = (uint16_t)date, last = 0; uint32_t lastd = 0;
  int ok = dy >= 2000 && dy < 2200;
  for (size_t j = 0; j < k; j++) { uint32_t dj = *(uint32_t*)(f + DAT + 4 * j); if ((uint16_t)dj == dy) ok = 0;
    if ((uint16_t)dj != 0xffff) { lastd = dj; last = (uint16_t)dj; } }
  if (!ok) {
    unsigned char* hn = u ? hon_block_now(blk, u) : 0;
    uint16_t y = hn ? *(uint16_t*)hn : (uint16_t)(last ? last + 1 : 0);
    if (y <= last) y = (uint16_t)(last + 1);
    date = (lastd & 0xffff0000u) | y;
    if (!lastd) date = 0x0c0b0000u | y;                    /* 11 December */
  }
  *(uint32_t*)(f + 4 + 4 * k) = club;
  *(uint32_t*)(f + DAT + 4 * k) = date;
  return (unsigned)(k + 1);
}
/* the winners a record has no date for (a merge before 31.10. moved only the clubs) get one */
static int rec_dates_fill(unsigned char* blk, uint32_t u, unsigned char* f)
{
  const size_t DAT = 0x324, N = 200;
  size_t k = 0; while (k < N && *(uint32_t*)(f + 4 + 4 * k) != 0xffffffffu) k++;
  size_t dk = 0; while (dk < N && *(uint16_t*)(f + DAT + 4 * dk) != 0xffff) dk++;
  int n = 0;
  uint32_t tail[200]; size_t nt = 0;
  for (size_t j = dk; j < k; j++) { tail[nt++] = *(uint32_t*)(f + 4 + 4 * j); *(uint32_t*)(f + 4 + 4 * j) = 0xffffffffu; }
  for (size_t j = 0; j < nt; j++) { rec_append(blk, u, f, tail[j], 0); n++; }
  return n;
}
/* fase 5 (01.11., Felix: the Liga FUTVE gone from the Palmarés): a title of year y is in the cabinet
   -- a record of reg with a date of that year. The title marks of fl26swiss-state.bin are not
   enough: they outlive the career (a new one with the same club, or a save loaded from before the
   title, kept the mark of a title its cabinet never had). The cabinet itself is the truth. */
static int cab_has_year(unsigned char* blk, uint16_t reg, int y)
{
  const size_t REC0 = 0x1798ca8, RECSZ = 0x648, DAT = 0x324;
  for (unsigned s_ = 0; s_ < 64 && REC0 + (s_ + 1) * RECSZ <= 0x17b0000u; s_++) {   /* WIN_HI */
    unsigned char* f = blk + REC0 + s_ * RECSZ;
    if (*(uint16_t*)f == 0xffff) break;
    if (*(uint16_t*)f != reg) continue;
    for (int q = 0; q < 200 && *(uint32_t*)(f + 4 + 4 * q) != 0xffffffffu; q++)
      if (*(uint16_t*)(f + DAT + 4 * q) == (uint16_t)y) return 1;
  }
  return 0;
}
static unsigned char* hon_block_now(unsigned char* blk, uint32_t u)
{
  static uintptr_t said_at = 0;
  unsigned char* best = 0; int besty = -1, nc = 0;
  char buf[400]; int bl = 0; buf[0] = 0;
  for (size_t off = HON_OFF - 0x20000; off < HON_OFF + 0x40000; off += 4) {
    unsigned char* h = blk + off;
    uint16_t y = *(uint16_t*)h;
    if (y < 2000 || y > 2200 || h[2] < 1 || h[2] > 12 || *(uint32_t*)(h + 8) != u) continue;
    uint16_t y2 = *(uint16_t*)(h + 4);
    if (y2 && (y2 < y || y2 > y + 2)) continue;
    int ok = 1;
    for (int i = 0; i < HON_ROWS && ok; i++) { uint32_t cid = *(uint32_t*)(h + 12 + i * 12); ok = cid == 0xffffffffu || cid < 1024; }
    if (!ok) continue;
    nc++;
    if (bl < 360) bl += snprintf(buf + bl, sizeof buf - bl, " +%#llx:%u/%u", (unsigned long long)off, y, h[2]);
    if (y > besty || (y == besty && off > (size_t)(best - blk))) { besty = y; best = h; }
  }
  if (best && (uintptr_t)best != said_at) {
    said_at = (uintptr_t)best;
    logf("fl26swiss: honours -- %d season block(s) of club %08x:%s; the running one at +%#llx (%d)", nc, u, buf,
         (unsigned long long)(best - blk), besty);
  }
  return best;
}
/* g_tl_total, g_tl_cid: declared before prog_handler (0 until the world names the league) */
__declspec(dllexport) int fl26_swiss_title_league(const uint16_t* v, int n)
{
  int got = 0;
  for (int i = 0; v && i < n; i++) {
    if (!v[2 * i] || !v[2 * i + 1]) continue;
    int isff = 0;
    for (int k = 0; k < g_nccup; k++) isff |= g_ccup[k].src[0] && g_ccup[k].ko == v[2 * i];
    if (isff) {                                    /* the final of two cups and its competition */
      g_ff_cid = v[2 * i + 1]; got++;
      logf("fl26swiss: final of two cups %u (competition %u) -- its title is the league's (the Liga FUTVE)",
           (unsigned)v[2 * i], (unsigned)g_ff_cid);
      continue;
    }
    g_tl_total = v[2 * i]; g_tl_cid = v[2 * i + 1]; got++;
    logf("fl26swiss: league %u (competition %u) -- its phases give no title; its total (the accumulated table) does",
         (unsigned)g_tl_total, (unsigned)g_tl_cid);
  }
  return got;
}
typedef struct { uint32_t cid; uint16_t reg; uint8_t won, kind; uint32_t zero; } hon_row_t;
/* The Palmarés screen does not read that block alone (30.10., screenshot: "Liga FUTVE 1" and "Final
   del FUTVE 1" with the block holding one league row). It counts the career's winners history:
   8-byte entries {u16 regulation, u16 0, u32 club} in blk+0x1790000..0x17b0000, one run per
   competition, one entry a season (reg 261 at +0x1798ca8, reg 11 at +0x1799938 written on day 142,
   reg 263 at +0x1799f80 written after the second leg; an empty one is {0xffff, 0, 0xffffffff}).
   So: the Final del FUTVE's entries get no club (that title does not exist), and this season's
   entry of the split league -- the last of its run, once the Clausura play-off is filled -- gets the
   Liga FUTVE champion, or no club while the title is still open. */
#define WIN_LO 0x1790000
#define WIN_HI 0x17b0000
static void winners_fix(unsigned char* blk, const split_t* sp, int fk, uint32_t champ, int d)
{
  /* 30.10.: the slot "league + 0x648" held the Final del Clausura (262) in this career, the Final del
     FUTVE (263) in two others: the history is not one run per competition at a fixed place. Once a
     session, every non-empty entry of the region, to read its layout. */
  {
    static int dumped = 0;
    if (!dumped++) {
      int n = 0;
      for (size_t off = 0x1798000; off + 8 <= 0x179c000 && n < 400; off += 8) {   /* the runs seen so far */
        uint16_t rg = *(uint16_t*)(blk + off);
        uint32_t cl = *(uint32_t*)(blk + off + 4);
        if (rg == 0xffff && (cl == 0xffffffffu || cl == 0xffff0000u || cl == 0x0000ffffu)) continue;
        if (!rg && !cl) continue;
        if (rg == 0xffff) continue;                    /* an empty slot, whatever its club field */
        logf("fl26swiss: winners list blk+%#llx: %04x %04x %08x", (unsigned long long)off, rg,
             *(uint16_t*)(blk + off + 2), cl);
        n++;
      }
      logf("fl26swiss: winners list: %d entr(ies) shown", n);
    }
  }
  /* The user's trophy cabinet (read 30.10. from the dump): a header with the club at +0x1798ab0, a
     count (u16) at +0x1798b82, then one record of 0x648 bytes per title won, in the order won, each
     starting {u16 regulation, u16 0, u32 club}: 261 at +0x1798ca8, 255 at +0x17992f0, 11 at
     +0x1799938, the next at +0x1799f80. The Palmarés counts these records by competition. The
     automatic Liga FUTVE is one more record: the last one copied (its other fields sane), its
     regulation the Final del FUTVE's, the count raised -- only when the count matches the records. */
  {
    uint16_t ffk = g_ccup[fk].ko;
    uint32_t aw = ff_auto_champion(ffk), u = state_user();
    if (aw && futve_cal()) {       /* fase 5: both finals' winners as the game's brackets read now -- a kept one
                                      can be another career's */
      for (int k2 = 0; k2 < g_nccup; k2++) {
        if (g_ccup[k2].ko != ffk || !g_ccup[k2].src[0]) continue;
        uint32_t l1 = ccup_ko_winner(g_ccup[k2].src[0]), l2 = ccup_ko_winner(g_ccup[k2].src[1]);
        /* a bracket no longer readable says nothing; one that names another club wins */
        if (((l1 >> 14) && !same_club(l1, aw)) || ((l2 >> 14) && !same_club(l2, aw))) aw = 0;
      }
    }
    const size_t HDR = 0x1798ab0, CNT = 0x1798b82, REC0 = 0x1798ca8, RECSZ = 0x648;
    if (aw && u && same_club(aw, u) && *(uint32_t*)(blk + HDR) == u) {
      unsigned cnt = *(uint16_t*)(blk + CNT), seen = 0, has = 0;
      while (seen < 64 && REC0 + (seen + 1) * RECSZ <= WIN_HI && *(uint16_t*)(blk + REC0 + seen * RECSZ) != 0xffff &&
             *(uint16_t*)(blk + REC0 + seen * RECSZ + 2) == 0) {
        has |= *(uint16_t*)(blk + REC0 + seen * RECSZ) == ffk;
        seen++;
      }
      /* 30.10.: +0x1798b82 stayed 3 with the game's own fourth record (the Final del Clausura) in
         place for days -- not a count. The record is appended where the next one is empty, and the
         cabinet's header (+0x1798ab0..+0x1798ca8) is logged before and after, to find the count. */
      /* fase 4: "already in the cabinet" is this season's, not any season's -- the first Liga FUTVE's
         record kept the second one out (31.10.). By the title marks (regulation, calendar year). */
      int ty = game_date() / 365;
      if (futve_cal()) has = cab_has_year(blk, ffk, ty);
      if (has) { /* already in the cabinet */ }
      else if (!seen || REC0 + (seen + 1) * RECSZ > WIN_HI ||
               *(uint16_t*)(blk + REC0 + seen * RECSZ) != 0xffff) {
        static int said = 0;
        if (!said++) logf("fl26swiss: trophy cabinet -- day %d: %u record(s), no empty slot after them; the automatic Liga FUTVE not added", d, seen);
      } else {
        for (size_t q = HDR; q < REC0; q += 32) { char hx[65]; tp_hex(blk + q, hx); logf("fl26swiss: trophy cabinet header before +%#llx %s", (unsigned long long)q, hx); }
        unsigned char* dst = blk + REC0 + seen * RECSZ;
        /* fase 4 (31.10.): a competition won before has its record -- the winner goes on its list */
        int same = -1;
        if (futve_cal()) for (unsigned j = 0; j < seen; j++) if (*(uint16_t*)(blk + REC0 + j * RECSZ) == ffk) { same = (int)j; break; }
        if (same >= 0) {
          unsigned char* f = blk + REC0 + same * RECSZ;
          size_t fe = 4 * (size_t)rec_append(blk, u, f, aw, 0);
          logf("fl26swiss: trophy cabinet -- day %d: the automatic Liga FUTVE added to record %d (reg %u), %u winner(s) now",
               d, same, (unsigned)ffk, (unsigned)(fe / 4));
          tmark_add(ffk, ty); state_store();
        } else {
        /* fase 4 (31.10.): the second Liga FUTVE showed as a second "Liga FUTVE 1" -- it was a copy of
           the record before it (the Supercopa's), the first one a copy of the Final del Clausura's:
           the Palmares groups by more than the regulation. A record of the same title is the model. */
        unsigned tpl = seen - 1;
        for (unsigned j = 0; j < seen; j++) if (*(uint16_t*)(blk + REC0 + j * RECSZ) == ffk) { tpl = j; break; }
        memcpy(dst, blk + REC0 + tpl * RECSZ, RECSZ);
        *(uint16_t*)dst = ffk; *(uint16_t*)(dst + 2) = 0; *(uint32_t*)(dst + 4) = aw;
        if (futve_cal()) {          /* fase 5: a record of its own -- not the template's other wins and dates */
          memset(dst + 4, 0xff, 0x324 - 4);
          for (int q = 0; q < 200; q++) *(uint32_t*)(dst + 0x324 + 4 * q) = 0x0000ffffu;
          rec_append(blk, u, dst, aw, 0);
        }
        logf("fl26swiss: trophy cabinet -- day %d: the automatic Liga FUTVE added as title %u (reg %u, blk+%#llx; +0x1798b82 = %u)", d,
             seen + 1, (unsigned)ffk, (unsigned long long)(REC0 + seen * RECSZ), cnt);
        if (futve_cal()) { tmark_add(ffk, ty); state_store(); }
        }
      }
    }
  }
  /* fase 4 (31.10., Felix): regulation 11 is "Liga FUTVE" again (Select Team), so the title the game
     gives the accumulated table's leader would read "Liga FUTVE". Out of the user's cabinet: the
     records after it move up one, the empty slot after the last takes the last's place. The real
     Liga FUTVE title is the Final del FUTVE's (175 "Liga FUTVE") as before. */
  if (futve_cal()) {
    const size_t HDR = 0x1798ab0, REC0 = 0x1798ca8, RECSZ = 0x648;
    uint32_t u = state_user();
    if (u && *(uint32_t*)(blk + HDR) == u) {
      unsigned seen = 0;
      while (seen < 64 && REC0 + (seen + 1) * RECSZ <= WIN_HI && *(uint16_t*)(blk + REC0 + seen * RECSZ) != 0xffff &&
             *(uint16_t*)(blk + REC0 + seen * RECSZ + 2) == 0) seen++;
      for (unsigned j = 0; j < seen; ) {
        unsigned char* rj = blk + REC0 + j * RECSZ;
        if (*(uint16_t*)rj != g_tl_total) { j++; continue; }
        if (REC0 + (seen + 1) * RECSZ > WIN_HI) break;
        memmove(rj, rj + RECSZ, (size_t)(seen - j) * RECSZ);     /* the empty slot after the last comes along */
        seen--;
        logf("fl26swiss: trophy cabinet -- day %d: the accumulated table's title (reg %u) taken out; %u record(s) left",
             d, (unsigned)g_tl_total, seen);
      }
    }
  }
  /* 30.10.: the slot "league + 0x648" held the Final del Clausura (262) in this career, the Final del
     FUTVE (263) in two others: the history is not one run per competition at a fixed place. Once a
     session, every non-empty entry of the region, to read its layout. */
  {
    static int dumped = 0;
    if (!dumped++) {
      int n = 0;
      for (size_t off = 0x1798000; off + 8 <= 0x179c000 && n < 400; off += 8) {   /* the runs seen so far */
        uint16_t rg = *(uint16_t*)(blk + off);
        uint32_t cl = *(uint32_t*)(blk + off + 4);
        if (rg == 0xffff && (cl == 0xffffffffu || cl == 0xffff0000u || cl == 0x0000ffffu)) continue;
        if (!rg && !cl) continue;
        if (rg == 0xffff) continue;                    /* an empty slot, whatever its club field */
        logf("fl26swiss: winners list blk+%#llx: %04x %04x %08x", (unsigned long long)off, rg,
             *(uint16_t*)(blk + off + 2), cl);
        n++;
      }
      logf("fl26swiss: winners list: %d entr(ies) shown", n);
    }
  }
  /* the automatic Liga FUTVE in the winners history too (it outlives the season, the rights answer
     does not): the final's entry of this season, in the slot where the game writes it after a
     played final -- the same season's slot as the league's own entry (reg 11, written on day 142),
     one run of 0x648 bytes later (seen in two careers: 11 at +0x1799938, 263 at +0x1799f80) */
  {
    uint16_t ffk = g_ccup[fk].ko;
    uint32_t aw = ff_auto_champion(ffk);
    int has = 0;
    for (size_t off = WIN_LO; off + 8 <= WIN_HI && !has; off += 8)
      has = *(uint16_t*)(blk + off) == ffk && *(uint32_t*)(blk + off + 4) == aw;
    if (aw && !has) {
      size_t lg = 0;
      for (size_t off = WIN_LO + 8; off + 16 <= WIN_HI; off += 8)
        if (*(uint16_t*)(blk + off) == sp->total && *(uint16_t*)(blk + off + 2) == 0 &&
            *(uint16_t*)(blk + off + 8) != sp->total) { lg = off; break; }
      size_t slot = lg ? lg + 0x648 : 0;
      /* 30.10.: "no free slot" -- an earlier DLL had left {263, 0, ffffffff} there (the Final del FUTVE
         without its club); the slot of the final is taken whether empty or the final's own */
      uint16_t sr = slot ? *(uint16_t*)(blk + slot) : 0;
      if (0 && slot && slot + 8 <= WIN_HI && (sr == 0xffff || sr == ffk)) {   /* off until the layout is read */
        *(uint16_t*)(blk + slot) = ffk; *(uint16_t*)(blk + slot + 2) = 0; *(uint32_t*)(blk + slot + 4) = aw;
        logf("fl26swiss: winners history -- day %d: blk+%#llx reg %u club %08x (the automatic Liga FUTVE)", d,
             (unsigned long long)slot, (unsigned)ffk, aw);
      } else {
        static int said = 0;
        if (!said++) logf("fl26swiss: winners history -- day %d: no slot for the automatic Liga FUTVE (league entry at %#llx, "
                          "slot %#llx holds %04x %04x %08x)", d, (unsigned long long)lg, (unsigned long long)slot,
                          slot ? *(uint16_t*)(blk + slot) : 0, slot ? *(uint16_t*)(blk + slot + 2) : 0,
                          slot ? *(uint32_t*)(blk + slot + 4) : 0);
      }
    }
  }
  int year = (abs_day() + 183) / 365, clausura_on = 0;
  for (int k = 0; k < g_nccup; k++)
    if (g_ccup[k].n && g_ccup[k].ereg[0] == sp->group[0] &&
        (g_ccup[k].filled_year == year || (g_ccup[k].fill && season_ord(d) >= season_ord(g_ccup[k].fill))))
      clausura_on = 1;                               /* filled this season, or its fill day is past (a save loaded) */
  uint16_t ff = g_ccup[fk].ko;
  for (size_t off = WIN_LO + 8; off + 16 <= WIN_HI; off += 8) {
    uint16_t reg = *(uint16_t*)(blk + off);
    /* 30.10., screenshot: "Liga FUTVE 1" with an empty list of seasons -- the count is these
       entries; the regular phases (191 on day 0, 192) have entries of their own, under the same
       competition, never seen by the probe (day 0 is not one of its days). They give no title. */
    int phase = reg == sp->regular || (reg && (reg == sp->group[0] || reg == sp->group[1] || reg == sp->group[2]));
    int total = futve_cal() && reg == g_tl_total;   /* fase 4: "Liga FUTVE" (11) lists the finals' champion */
    if (!(phase || total) || *(uint16_t*)(blk + off + 2) != 0) continue;   /* 30.10.: 11 and 263 are the game's again */
    uint32_t club = *(uint32_t*)(blk + off + 4);
    if (club != 0xffffffffu && !(club >> 14)) continue;
    uint16_t prev = *(uint16_t*)(blk + off - 8), next = *(uint16_t*)(blk + off + 8);
    if (prev != reg && prev != 0xffff) continue;      /* not inside a run of this competition */
    uint32_t want;
    if (reg == ff || phase) want = 0xffffffffu;      /* no "Final del FUTVE" or phase title, any season */
    else {
      if (next == reg || !clausura_on) continue;     /* an older season's, or this one's not written yet */
      want = champ ? champ : 0xffffffffu;
    }
    if (club == want) continue;
    *(uint32_t*)(blk + off + 4) = want;
    logf("fl26swiss: winners history -- day %d: blk+%#llx reg %u club %08x -> %08x (%s)", d,
         (unsigned long long)off, (unsigned)reg, club, want,
         reg == ff ? "no Final del FUTVE title" : phase ? "a regular phase gives no title" :
         champ ? "the Liga FUTVE champion" : "the Liga FUTVE still open");
  }
}
_Static_assert(sizeof(hon_row_t) == 12, "an honours row is 12 bytes");

/* 30.10. (Supercopa missing from the Palmarés): read-only. Each day, the trophy cabinet's records
   and the season block's rows, logged when they change -- to see where the game puts a new title. */
static void cabinet_watch(void)
{
  unsigned char* o = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
  unsigned char* blk = o ? *(unsigned char**)(o + 0x48) : 0;
  uint32_t u = state_user();
  if (!blk || !u) return;
  const size_t HDR = 0x1798ab0, REC0 = 0x1798ca8, RECSZ = 0x648;
  if (*(uint32_t*)(blk + HDR) != u) return;
  static char last[1024], last_h[1024];
  char buf[1024]; int n = 0, m = 0;
  for (int i = 0; i < 40 && REC0 + (i + 1) * RECSZ <= WIN_HI; i++) {
    unsigned char* r = blk + REC0 + i * RECSZ;
    uint16_t rg = *(uint16_t*)r;
    if (rg == 0xffff) continue;
    if (n < 900) n += snprintf(buf + n, sizeof buf - n, " [%d]%u/%08x", i, (unsigned)rg, *(uint32_t*)(r + 4));
    m++;
  }
  buf[n] = 0;
  int d = today();
  /* fase 4 (31.10., Felix: "Liga FUTVE 1" twice): a record is one competition, its winners a list of
     u32 club ids from +4 (261 won twice: +4 and +8 the club, +0xc ffffffff) -- the Palmares count is
     that list's length. A second record of the same regulation shows as a second row. It is merged:
     its list goes on the end of the first's, the records after it move up one. */
  if (futve_cal()) {
    static const uint16_t MINE[2] = { 263, 256 };
    for (int t = 0; t < 2; t++) {
      int first = -1, cnt = 0;
      while (cnt < 64 && REC0 + (cnt + 1) * RECSZ <= WIN_HI && *(uint16_t*)(blk + REC0 + cnt * RECSZ) != 0xffff) cnt++;
      for (int i = 0; i < cnt; ) {
        unsigned char* r = blk + REC0 + i * RECSZ;
        if (*(uint16_t*)r != MINE[t]) { i++; continue; }
        if (first < 0) { first = i; i++; continue; }
        if (REC0 + (cnt + 1) * RECSZ > WIN_HI) break;
        unsigned char* f = blk + REC0 + first * RECSZ;
        int moved = 0; unsigned now = 0;
        for (size_t q = 0; q < 200 && *(uint32_t*)(r + 4 + 4 * q) != 0xffffffffu; q++, moved++)
          now = rec_append(blk, u, f, *(uint32_t*)(r + 4 + 4 * q), *(uint32_t*)(r + 0x324 + 4 * q));
        size_t fe = 4 + 4 * (size_t)now;
        memmove(r, r + RECSZ, (size_t)(cnt - i) * RECSZ);          /* the empty slot after the last comes along */
        cnt--;
        logf("fl26swiss: trophy cabinet -- day %d: record %d (reg %u) merged into record %d (%d winner(s) moved, %u now)",
             d, i, (unsigned)MINE[t], first, moved, (unsigned)((fe - 4) / 4));
      }
      if (first >= 0) {
        int nf = rec_dates_fill(blk, u, blk + REC0 + first * RECSZ);
        if (nf) logf("fl26swiss: trophy cabinet -- day %d: record %d (reg %u): %d win(s) without a date dated", d, first, (unsigned)MINE[t], nf);
      }
    }
  }
  /* fase 4 (31.10., Felix: three Supercopas won, the Palmares says 1 -- supercup_title_fix took the
     record among the last three for "already this season's"): titles of past seasons the DLL missed,
     from fl26swiss-palmares.txt beside fl26swiss-state.bin, one line per competition:
     "<reg> <year> <year> ...". Each listed year the user's club won is made sure of in its record
     (club and date, 31 January); a date of a year not listed and before the last listed one goes
     (a copy's wrong date). Later titles are not touched, so the file can stay. */
  if (futve_cal()) {
    static int done = 0;
    const char* sp = state_path();
    if (!done && sp) {
      done = 1;
      char fp[MAX_PATH + 96]; snprintf(fp, sizeof fp, "%s", sp);
      char* sl = strrchr(fp, '\\'); if (sl) snprintf(sl + 1, sizeof fp - (size_t)(sl + 1 - fp), "fl26swiss-palmares.txt");
      HANDLE fh = sl ? CreateFileA(fp, GENERIC_READ, FILE_SHARE_READ, 0, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, 0) : INVALID_HANDLE_VALUE;
      if (fh != INVALID_HANDLE_VALUE) {
        char tx[2048]; DWORD got = 0;
        ReadFile(fh, tx, sizeof tx - 1, &got, 0); CloseHandle(fh); tx[got] = 0;
        for (char* line = strtok(tx, "\r\n"); line; line = strtok(0, "\r\n")) {
          int v[24], nv = 0; char* q = line;
          while (nv < 24) { char* e; long x = strtol(q, &e, 10); if (e == q) break; v[nv++] = (int)x; q = e; }
          if (nv < 2 || v[0] <= 0 || v[0] > 1023) continue;
          uint16_t reg = (uint16_t)v[0]; int maxy = 0;
          for (int k = 1; k < nv; k++) if (v[k] > maxy) maxy = v[k];
          unsigned char* f = 0; int cnt = 0;
          while (cnt < 64 && REC0 + (cnt + 1) * RECSZ <= WIN_HI && *(uint16_t*)(blk + REC0 + cnt * RECSZ) != 0xffff) {
            if (*(uint16_t*)(blk + REC0 + cnt * RECSZ) == reg && !f) f = blk + REC0 + cnt * RECSZ;
            cnt++;
          }
          if (!f) { logf("fl26swiss: palmares file -- reg %u: no record in the cabinet, line left", (unsigned)reg); continue; }
          /* the dated entries kept: listed years, or later than the last listed */
          uint32_t kc[200], kd[200]; int nk = 0, dropped = 0, added = 0;
          for (int k = 0; k < 200 && *(uint32_t*)(f + 4 + 4 * k) != 0xffffffffu; k++) {
            uint32_t dt = *(uint32_t*)(f + 0x324 + 4 * k); int yy = (uint16_t)dt, listed = 0;
            for (int j = 1; j < nv; j++) listed |= v[j] == yy;
            if ((uint16_t)dt == 0xffff || (!listed && yy < maxy)) { dropped++; continue; }
            kc[nk] = *(uint32_t*)(f + 4 + 4 * k); kd[nk++] = dt;
          }
          for (int j = 1; j < nv && nk < 200; j++) {
            int there = 0; for (int k = 0; k < nk; k++) there |= (int)(uint16_t)kd[k] == v[j];
            if (!there) { kc[nk] = u; kd[nk++] = (uint32_t)(uint16_t)v[j] | (1u << 16) | (31u << 24); added++; }
          }
          if (!dropped && !added) continue;
          for (int a = 1; a < nk; a++) for (int b = a; b > 0 && (uint16_t)kd[b] < (uint16_t)kd[b - 1]; b--) {
            uint32_t t1 = kc[b]; kc[b] = kc[b - 1]; kc[b - 1] = t1; t1 = kd[b]; kd[b] = kd[b - 1]; kd[b - 1] = t1; }
          for (int k = 0; k < 200; k++) {
            *(uint32_t*)(f + 4 + 4 * k) = k < nk ? kc[k] : 0xffffffffu;
            *(uint32_t*)(f + 0x324 + 4 * k) = k < nk ? kd[k] : 0x0000ffffu;
          }
          logf("fl26swiss: palmares file -- reg %u: %d win(s) added, %d wrong date(s) dropped; %d title(s) now", (unsigned)reg, added, dropped, nk);
        }
        /* fase 5 (01.11., Felix: no titles of another career): the file is for the career it was
           written for -- used once, then renamed, so a new career never gets its years */
        char done[MAX_PATH + 96]; snprintf(done, sizeof done, "%s.applied", fp);
        if (MoveFileExA(fp, done, MOVEFILE_REPLACE_EXISTING)) logf("fl26swiss: palmares file -- applied, renamed to %s", done);
      }
    }
  }
  if (strcmp(buf, last)) {
    logf("fl26swiss: cabinet -- day %d: %d record(s):%s", d, m, buf);
    /* fase 4 (31.10., Felix: a second Liga FUTVE won, the Palmares still says 1): each record's first
       0x80 bytes, once a session, to find where a record keeps its season */
    static int dumped = 0;
    if (!dumped++)
      for (int i = 0; i < 40 && REC0 + (i + 1) * RECSZ <= WIN_HI; i++) {
        unsigned char* r = blk + REC0 + i * RECSZ;
        if (*(uint16_t*)r == 0xffff) continue;
        for (int q = 0; q + 32 <= (int)RECSZ; q += 32) {               /* the whole record, its all-ff lines left out */
          int allff = 1; for (int b = 0; b < 32; b++) if (r[q + b] != 0xff) { allff = 0; break; }
          if (allff && q) continue;
          char hx[65]; tp_hex(r + q, hx); logf("fl26swiss: cabinet record %d +%#x %s", i, q, hx); }
      }
    char hx[65]; tp_hex(blk + 0x1798b70, hx); logf("fl26swiss: cabinet header +0x1798b70 %s", hx);
    tp_hex(blk + 0x1798b90, hx); logf("fl26swiss: cabinet header +0x1798b90 %s", hx);
    memcpy(last, buf, sizeof last);
  }
  unsigned char* h = blk + HON_OFF;
  if (futve_cal()) { unsigned char* hn = hon_block_now(blk, u); if (hn) h = hn; }   /* fase 4: the running season's block */
  n = 0;
  n += snprintf(buf + n, sizeof buf - n, " %u/%u club %08x:", *(uint16_t*)h, h[2], *(uint32_t*)(h + 8));
  for (int i = 0; i < HON_ROWS; i++) {
    unsigned char* r = h + 12 + i * 12;
    if (*(uint32_t*)r == 0xffffffffu) continue;
    n += snprintf(buf + n, sizeof buf - n, " %u/%u/%u%s", *(uint32_t*)r, (unsigned)*(uint16_t*)(r + 4), r[6], r[7] ? "k" : "");
  }
  if (strcmp(buf, last_h)) { logf("fl26swiss: season block -- day %d:%s", d, buf); memcpy(last_h, buf, sizeof last_h); }
}


/* 30.10. (Felix: the Supercopa de Venezuela won on day 227, no title in the Palmarés; the cabinet
   watch: no record added, the ICC (107) on day 220 was). A Super Cup of ours is registered by
   aug_scup_fill_days outside the game's own stage run, and the game never writes its title. Once its
   match is played and the user's club won it, the record goes in by us: the cabinet's last record
   copied into the first empty slot, its regulation and club set. Not twice: a record of that
   regulation among the last three is this season's. */
/* Fase 4 (31.10., Felix: no Venezuelan date may clash with any competition, national teams'
   included): once a season, every day of the Liga FUTVE's own (split phases, play-offs, finals, the
   Copa Venezuela and the Supercopa) against the national teams' windows and tournaments of this
   year (g_nqday, g_ntday), the Libertadores' and its qualifying's, the Club World Cup's and every
   other cup of ours (the Sudamericana ...). A day within one of another's is logged as a clash; the
   national teams' days are listed in full, to set the world's days by. Read-only. */
/* the days on the calendar that hold a match of the custom Copa Sudamericana (257/258 and their
   group and tie rows) or a national teams' friendly (56): read from the calendar's own day lists
   and match records, so these are the days the game really plays them. Fase 4 (31.10., Felix). */
static int futve_cal_scan(uint16_t* od, const char** on, int no, int cap)
{
  unsigned char* o = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
  unsigned char* blk = o ? *(unsigned char**)(o + 0x48) : 0;
  if (!blk) return no;
  for (int d = 0; d < 365 && no < cap; d++) {
    uint16_t* ids = (uint16_t*)(blk + CAL_BASE + (size_t)d * CAL_STRIDE);
    int sud = 0, fr = 0;
    for (int i = 0; i < CAL_IDCAP && ids[i] != 0xffff && !(sud && fr); i++) {
      unsigned char* m = ((mrec_fn)(uintptr_t)(g_base + MREC_RVA))(blk, ids[i]);
      if (!m || *(uint16_t*)m != ids[i]) continue;
      uint16_t b = *(uint16_t*)(m + 4) & 0x3ff;
      int tk_;
      if (b == 257 || b == 258 || lpre_of(b, &tk_) >= 0) sud = 1;   /* fase 5: the modern CONMEBOL pre-rounds too */
      if (b == 56) fr = 1;
    }
    if (sud && no < cap) { od[no] = (uint16_t)d; on[no++] = "Copa Sudamericana"; }
    if (fr && no < cap) { od[no] = (uint16_t)d; on[no++] = "national-team friendly"; }
  }
  return no;
}
static void futve_clash_report(void)
{
  static int said_year = -1, said_day = -100;
  int d = today();
  if (!futve_cal() || d < 0 || !g_nnqday) return;
  int y = abs_day() / 365;
  /* once a year in full, and every week again: the Sudamericana's and the friendlies' matches are
     made through the year (its groups in August); a clash already said is not said again */
  int full = y != said_year;
  if (!full && d - said_day < 7 && d >= said_day) return;
  said_year = y; said_day = d;
  char buf[900]; size_t bl = 0; buf[0] = 0;
  for (int i = 0; i < g_nnqday && bl + 6 < sizeof buf; i++) bl += snprintf(buf + bl, sizeof buf - bl, " %u", g_nqday[i]);
  if (full) logf("fl26swiss: FUTVE dates -- national-team windows:%s", buf);
  bl = 0; buf[0] = 0;
  for (int i = 0; i < g_nntday && bl + 6 < sizeof buf; i++) bl += snprintf(buf + bl, sizeof buf - bl, " %u", g_ntday[i]);
  if (full) logf("fl26swiss: FUTVE dates -- national-team tournaments this year:%s", g_nntday ? buf : " none");
  uint16_t od[400]; const char* on[400]; int no = 0;
  for (int i = 0; i < g_nnqday && no < 400; i++) { od[no] = g_nqday[i]; on[no++] = "national-team window"; }
  for (int i = 0; i < g_nntday && no < 400; i++) { od[no] = g_ntday[i]; on[no++] = "national-team tournament"; }
  static const char* GCN[GC_N] = { "Club World Cup", "Libertadores qualifying", "Libertadores", "AFC" };
  for (int g = 0; g < GC_N; g++) {
    if (g == GC_AFC) continue;                     /* Asian clubs only: never a Venezuelan club's day */
    for (int i = 0; i < g_ngcday[g] && no < 400; i++) { od[no] = g_gcday[g][i]; on[no++] = GCN[g]; }
  }
  no = futve_cal_scan(od, on, no, 400);
  uint16_t fd[200]; char fn[200][24]; int nf = 0;
  for (int i = 0; i < g_nsdays; i++)
    for (int j = 0; j < g_sdays[i].n && nf < 200; j++) { fd[nf] = g_sdays[i].day[j]; snprintf(fn[nf++], 24, "league %u", g_sdays[i].reg); }
  for (int k = 0; k < g_nccup; k++) {
    const ccup_t* c = &g_ccup[k];
    int ours = c->adv || c->src[0];
    /* fase 5: a two-club knockout (the Recopa) plays only its last day of the seven it is handed */
    for (int j = (c->n == 2 && c->nd > 1 && !ours) ? c->nd - 1 : 0; j < c->nd; j++) {
      if (ours && nf < 200) { fd[nf] = c->days[j]; snprintf(fn[nf++], 24, "cup %u final", c->ko); }
      else if (!ours && no < 400) { od[no] = c->days[j]; on[no++] = "a cup of ours"; }
    }
    for (int j = 0; j < c->gnd; j++) {
      if (ours && nf < 200) { fd[nf] = c->gdays[j]; snprintf(fn[nf++], 24, "cup %u group", c->ko); }
      else if (!ours && no < 400) { od[no] = c->gdays[j]; on[no++] = "a cup of ours"; }
    }
  }
  static const uint16_t VCUPS[2] = { 255, 256 };
  for (int v = 0; v < 2; v++) {
    const datedays_t* dd = date_days_for(VCUPS[v]);
    for (int j = 0; dd && j < dd->n && nf < 200; j++) { fd[nf] = dd->day[j]; snprintf(fn[nf++], 24, "cup %u", VCUPS[v]); }
  }
  int clashes = 0, fresh = 0, nsud = 0, nfr = 0;
  static uint32_t said[256]; static int nsaid = 0, said_y = -1;
  if (said_y != y) { said_y = y; nsaid = 0; }
  for (int j = 0; j < no; j++) { nsud += !strcmp(on[j], "Copa Sudamericana"); nfr += !strcmp(on[j], "national-team friendly"); }
  for (int i = 0; i < nf; i++)
    for (int j = 0; j < no; j++)
      if (abs((int)fd[i] - (int)od[j]) < 2) {
        clashes++;
        uint32_t key = ((uint32_t)fd[i] << 16) | od[j];
        int k = 0;
        while (k < nsaid && said[k] != key) k++;
        if (k < nsaid) continue;
        if (nsaid < 256) said[nsaid++] = key;
        fresh++;
        logf("fl26swiss: FUTVE dates -- CLASH: %s on day %u, %s on day %u", fn[i], fd[i], on[j], od[j]);
      }
  if (full || fresh)
    logf("fl26swiss: FUTVE dates -- day %d: %d Venezuelan day(s) checked against %d other(s) (%d Sudamericana day(s), %d friendly day(s) on the calendar): %d clash(es)",
         d, nf, no, nsud, nfr, clashes);
}

/* fase 5 (01.11., Felix: "gané la final del apertura pero no me dio el palmarés"): with the modern
   CONMEBOL competitions the game wrote no title for the Final del Apertura (261, day 167) -- the
   Final del Clausura's (262, day 335) it still wrote. Read from the cabinet three days after a Liga
   FUTVE play-off final the user's club won: a record of that final dated this year, else the DLL
   writes it (the club and the final's date on its lists, or a new record). Once a year, by the title
   marks; a title the game wrote is only marked. */
static void futve_final_title_fix(void)
{
  if (!futve_cal()) return;
  uint32_t u = state_user();
  unsigned char* o = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
  unsigned char* blk = o ? *(unsigned char**)(o + 0x48) : 0;
  const size_t HDR = 0x1798ab0, REC0 = 0x1798ca8, RECSZ = 0x648, DAT = 0x324;
  if (!u || !blk || *(uint32_t*)(blk + HDR) != u) return;
  int gd = game_date(), ad = abs_day(), d = today();
  if (gd < 0 || ad < 0 || d < 0) return;
  int gy = gd / 365;
  for (int k = 0; k < g_nccup; k++) {
    if (!g_ccup[k].adv) continue;                            /* the Apertura's and the Clausura's finals */
    uint16_t reg = g_ccup[k].ko;
    cupwin_t* w = cupwin_of(reg);
    if (!w || !(w->club >> 14) || !same_club(w->club, u)) continue;
    int age = ad - w->day;
    if (age < 3 || age > d) continue;                        /* this year's final, three days on */
    if (cab_has_year(blk, reg, gy)) continue;
    /* the game's own result too: a kept winner can be another career's (the state file is the
       save folder's, every career of the club shares it) -- never a title not won in this one */
    uint32_t live = ccup_ko_winner(reg);
    if (!(live >> 14) || !same_club(live, u)) continue;
    unsigned seen = 0; int same = -1;
    while (seen < 64 && REC0 + (seen + 1) * RECSZ <= WIN_HI && *(uint16_t*)(blk + REC0 + seen * RECSZ) != 0xffff) {
      if (*(uint16_t*)(blk + REC0 + seen * RECSZ) == reg && same < 0) same = (int)seen;
      seen++;
    }
    int fd = d - age;                                        /* the final's day of the year */
    static const int MD[12] = { 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31 };
    int mo = 0, dd = fd;
    while (mo < 11 && dd >= MD[mo]) { dd -= MD[mo]; mo++; }
    uint32_t date = (uint32_t)(uint16_t)gy | ((uint32_t)(mo + 1) << 16) | ((uint32_t)(dd + 1) << 24);
    if (same >= 0) {
      unsigned char* f = blk + REC0 + same * RECSZ;
      int dated = 0;
      for (int q = 0; q < 200 && *(uint32_t*)(f + 4 + 4 * q) != 0xffffffffu; q++) dated |= *(uint16_t*)(f + DAT + 4 * q) == (uint16_t)gy;
      if (dated) { tmark_add(reg, gy); state_store(); logf("fl26swiss: trophy cabinet -- day %d: final %u -- the game wrote this year's title", d, (unsigned)reg); continue; }
      unsigned now = rec_append(blk, u, f, u, date);
      tmark_add(reg, gy); state_store();
      logf("fl26swiss: trophy cabinet -- day %d: final %u won by the user's club on day %d -- no title from the game; added to record %d, %u title(s) now",
           d, (unsigned)reg, fd, same, now);
      continue;
    }
    if (!seen || REC0 + (seen + 1) * RECSZ > WIN_HI) continue;
    unsigned char* dst = blk + REC0 + seen * RECSZ;
    memcpy(dst, blk + REC0 + (seen - 1) * RECSZ, RECSZ);
    memset(dst + 4, 0xff, DAT - 4);
    for (int q = 0; q < 200; q++) *(uint32_t*)(dst + DAT + 4 * q) = 0x0000ffffu;
    *(uint16_t*)dst = reg; *(uint16_t*)(dst + 2) = 0;
    rec_append(blk, u, dst, u, date);
    tmark_add(reg, gy); state_store();
    logf("fl26swiss: trophy cabinet -- day %d: final %u won by the user's club on day %d -- no title from the game; written as title %u (%04u-%02d-%02d)",
         d, (unsigned)reg, fd, seen + 1, (unsigned)gy, mo + 1, dd + 1);
  }
}

static void supercup_title_fix(void)
{
  int d = today();
  /* fase 4: a January-December Super Cup of ours (the Supercopa at the end of January) as well */
  int aug = d >= 182 && d <= 330 && g_naug_scup, cal = d >= 20 && d <= 120 && g_ncal_scup;
  if (!aug && !cal) return;
  uint32_t u = state_user();
  if (!u) return;
  unsigned char* o = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
  unsigned char* blk = o ? *(unsigned char**)(o + 0x48) : 0;
  const size_t HDR = 0x1798ab0, REC0 = 0x1798ca8, RECSZ = 0x648;
  if (!blk || *(uint32_t*)(blk + HDR) != u) return;
  int na = aug ? g_naug_scup : 0, ntot = na + (cal ? g_ncal_scup : 0);
  for (int i = 0; i < ntot; i++) {
    uint16_t reg = i < na ? g_aug_scup[i].reg : g_cal_scup[i - na].reg;
    if (!get_rec(reg) || ccup_matches(reg) <= 0 || ccup_unplayed(reg) != 0) continue;
    uint32_t w = winner_now(reg);
    if (!w) {
      static int said_w = 0;
      if (!said_w++) logf("fl26swiss: trophy cabinet -- day %d: Super Cup %u played, the rights code names no winner", d, (unsigned)reg);
      continue;
    }
    if (!same_club(w, u)) continue;
    unsigned seen = 0;
    while (seen < 64 && REC0 + (seen + 1) * RECSZ <= WIN_HI && *(uint16_t*)(blk + REC0 + seen * RECSZ) != 0xffff &&
           *(uint16_t*)(blk + REC0 + seen * RECSZ + 2) == 0) seen++;
    int has = 0;
    if (futve_cal()) {
      /* fase 4 (31.10.): "this season's" by the title marks; a Supercopa won before has its record,
         the win goes on its lists (club and date, 31 January of this year) */
      int gy = game_date() / 365;
      if (gy <= 0 || cab_has_year(blk, reg, gy)) continue;
      int same = -1;
      for (unsigned j = 0; j < seen; j++) if (*(uint16_t*)(blk + REC0 + j * RECSZ) == reg) { same = (int)j; break; }
      if (same >= 0) {
        unsigned char* sf = blk + REC0 + same * RECSZ; int dated = 0;
        for (int k = 0; k < 200 && *(uint32_t*)(sf + 4 + 4 * k) != 0xffffffffu; k++) dated |= *(uint16_t*)(sf + 0x324 + 4 * k) == (uint16_t)gy;
        if (dated) { tmark_add(reg, gy); state_store(); continue; }   /* this year's already there (the palmares file) */
        unsigned now = rec_append(blk, u, blk + REC0 + same * RECSZ, u, (uint32_t)(uint16_t)gy | (1u << 16) | (31u << 24));
        tmark_add(reg, gy); state_store();
        logf("fl26swiss: trophy cabinet -- day %d: Super Cup %u won by the user's club, added to record %d, %u title(s) now", d, (unsigned)reg, same, now);
        continue;
      }
      tmark_add(reg, gy); state_store();
    } else
    for (unsigned j = seen > 3 ? seen - 3 : 0; j < seen; j++) has |= *(uint16_t*)(blk + REC0 + j * RECSZ) == reg;
    if (has) continue;
    if (!seen || REC0 + (seen + 1) * RECSZ > WIN_HI || *(uint16_t*)(blk + REC0 + seen * RECSZ) != 0xffff) {
      static int said = 0;
      if (!said++) logf("fl26swiss: trophy cabinet -- day %d: Super Cup %u won, %u record(s), no empty slot; not added", d, (unsigned)reg, seen);
      continue;
    }
    unsigned char* dst = blk + REC0 + seen * RECSZ;
    unsigned tpl = seen - 1;   /* a record of the same title as the model (the Palmares groups by more than the regulation) */
    for (unsigned j = 0; j < seen; j++) if (*(uint16_t*)(blk + REC0 + j * RECSZ) == reg) { tpl = j; break; }
    memcpy(dst, blk + REC0 + tpl * RECSZ, RECSZ);
    *(uint16_t*)dst = reg; *(uint16_t*)(dst + 2) = 0; *(uint32_t*)(dst + 4) = u;
    if (futve_cal()) {
      /* fase 5 (01.11., Felix: "2 Supercopas" after one): the copy kept the template's dates (the
         Liga FUTVE's 2025), so this year's title was not seen and went in again two days later. A
         record of its own: this win alone, dated 31 January of this year */
      int gy2 = game_date() / 365;
      memset(dst + 4, 0xff, 0x324 - 4);
      for (int q = 0; q < 200; q++) *(uint32_t*)(dst + 0x324 + 4 * q) = 0x0000ffffu;
      rec_append(blk, u, dst, u, (uint32_t)(uint16_t)gy2 | (1u << 16) | (31u << 24));
    }
    logf("fl26swiss: trophy cabinet -- day %d: Super Cup %u won by the user's club, added as title %u (blk+%#llx)",
         d, (unsigned)reg, seen + 1, (unsigned long long)(REC0 + seen * RECSZ));
  }
}

static void honours_fix(void)
{
  if (!g_tl_total || !g_tl_cid) return;
  int d = today();
  /* January..June: the season of the finals; fase 4 (January-December Liga FUTVE): from May on,
     the Apertura's final in June to the Final del FUTVE in December */
  if (d < 0 || (futve_cal() ? d < 120 : d > 180)) return;
  const split_t* sp = 0;
  for (int i = 0; i < g_nsplits; i++) if (SPLITS[i].total == g_tl_total) sp = &SPLITS[i];
  int fk = -1;
  for (int k = 0; k < g_nccup; k++) if (g_ccup[k].src[0]) fk = k;
  if (!sp || fk < 0) return;
  unsigned char* o = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
  unsigned char* blk = o ? *(unsigned char**)(o + 0x48) : 0;
  uint32_t u = state_user();
  if (!blk || !u) return;
  unsigned char* h = blk + HON_OFF;
  if (futve_cal()) { unsigned char* hn = hon_block_now(blk, u); if (hn) h = hn; }   /* fase 4: the running season's block */
  uint16_t y = *(uint16_t*)h; uint8_t mo = h[2];
  static int said_bad = 0;
  if (y < 2000 || y > 2200 || mo < 1 || mo > 12 || *(uint32_t*)(h + 8) != u) {
    if (!said_bad++) logf("fl26swiss: honours -- no season block of club %08x at blk+%#x (year %u, month %u, club %08x); "
                          "the Liga FUTVE title is left to the game", u, HON_OFF, y, mo, *(uint32_t*)(h + 8));
    return;
  }
  hon_row_t* row = (hon_row_t*)(h + 12);
  /* this season's Liga FUTVE champion: the Final del FUTVE's, or the club that won both finals */
  uint32_t champ = ccup_season_win(fk);
  if (!champ) {
    uint32_t w1 = ccup_src_winner(g_ccup[fk].src[0]), w2 = ccup_src_winner(g_ccup[fk].src[1]);
    if (w1 && w2 && same_club(w1, w2)) champ = w1;
  }
  /* 30.10. (provisional, names): the split league's total (11) is "Tabla acumulada FUTVE" and its
     row stays; the Final del FUTVE's competition (175) is named "Liga FUTVE" and its row stays. Out:
     the rows of the two regular phases (191, 192: no title of their own) and of a lost final. In:
     the club that won both feeding finals, whose Final del FUTVE is not played, gets that row. */
  uint32_t w1 = ccup_src_winner(g_ccup[fk].src[0]), w2 = ccup_src_winner(g_ccup[fk].src[1]);
  int want = g_ff_cid && w1 && w2 && same_club(w1, w2) && same_club(w1, u);
  /* fase 4 (31.10.): the running season's block (hon_block_now) counts titles (+6: the club's
     number of that title so far -- 2026's "142/261/2"); the Liga FUTVE row there takes the count
     of the blocks before it plus one. The champion of the finals decides it, as above. */
  uint8_t ffcount = 1;
  if (futve_cal()) {
    if (!want && g_ff_cid && champ && same_club(champ, u)) want = 1;   /* a played final the game writes itself: have_ff below */
    for (size_t off = HON_OFF - 0x20000; off < HON_OFF + 0x40000; off += 4) {
      unsigned char* hb = blk + off;
      if (hb == h || *(uint16_t*)hb < 2000 || *(uint16_t*)hb >= y || hb[2] < 1 || hb[2] > 12 || *(uint32_t*)(hb + 8) != u) continue;
      for (int i = 0; i < HON_ROWS; i++) {
        unsigned char* rr = hb + 12 + i * 12;
        if (*(uint16_t*)(rr + 4) == g_ccup[fk].ko && rr[6] >= ffcount) ffcount = (uint8_t)(rr[6] + 1);
      }
    }
    static int said_w = -1;
    if (said_w != d) { said_w = d;
      logf("fl26swiss: honours -- day %d, block %u: finals' winners %08x / %08x, champion %08x, Liga FUTVE row %s (count %u)",
           d, (unsigned)y, w1, w2, champ, want ? "wanted" : "not wanted", ffcount); }
  }
  hon_row_t keep[HON_ROWS]; int n = 0, dropped = 0, have_ff = 0;
  for (int i = 0; i < HON_ROWS; i++) {
    const hon_row_t* r = &row[i];
    if (r->cid == 0xffffffffu) continue;
    int league = r->reg == sp->regular ||
                 (r->reg && (r->reg == sp->group[0] || r->reg == sp->group[1] || r->reg == sp->group[2])) ||
                 (futve_cal() && r->reg == g_tl_total);   /* fase 4: the table leader's title is no title */
    int ffwin = 0;
    have_ff |= r->reg == g_ccup[fk].ko && r->won;
    /* 30.10. (screenshot: Liga FUTVE, Final del Apertura, Copa Venezuela with rows 142 won, 131 won
       and 129 runner-up): three rows, three titles -- the runner-up row of a final of ours is counted
       as a title, under the Liga FUTVE's name. A lost final is no title: its row goes too. */
    int lost = 0;
    for (int k = 0; k < g_nccup && !lost; k++)
      lost = (g_ccup[k].adv || g_ccup[k].src[0]) && r->reg == g_ccup[k].ko && !r->won;
    if (league || ffwin || lost) { dropped++; continue; }
    keep[n++] = *r;
  }
  if (want && !have_ff && n < HON_ROWS) {
    hon_row_t t = { g_ff_cid, g_ccup[fk].ko, ffcount, 0, 0 };
    keep[n++] = t;
  }
  hon_row_t out[HON_ROWS];
  for (int i = 0; i < HON_ROWS; i++) {
    if (i < n) out[i] = keep[i];
    else { hon_row_t e = { 0xffffffffu, 0xffff, 0, 0, 0 }; out[i] = e; }
  }
  if (memcmp(out, row, sizeof out)) {
    memcpy(row, out, sizeof out);
    logf("fl26swiss: honours -- day %d: %d row(s) of a regular phase / a lost final taken out%s "
         "(champion %08x, the user's club %08x)", d, dropped,
         want && !have_ff ? ", the Liga FUTVE given: both finals won" : "", champ, u);
  }
  winners_fix(blk, sp, fk, champ, d);
}

/* 30.10. (second run): with the block and the winners history corrected on day 142 itself, the
   manager's Palmarés still read "Liga FUTVE". So it reads a copy elsewhere. On the title days the
   whole process is searched (read-write committed memory) for the honours rows the game writes:
   (130, 191|192|11, 1, 0x0d) -- 82 00 00 00 bf|c0|0b 00 01 0d -- and (175, 263, 1, 0) -- af 00 00 00
   07 01 01 00; each hit with the 32 bytes before it, the career block's own marked. Read-only. */
static void honours_search(int d)
{
  /* 30.10.: the search of the whole process hung the game (2-byte steps, 14 compares, 4.3 GB); the
     blk-only one missed the lead it had found: "130 beside 2025/2026" in a separate allocation of
     3.8 MB below the career block (0x7FF4E0B30000 in that session) -- the manager's record, by the
     look of it. Now: private read-write regions of at most 64 MB, a first-byte filter, the season
     patterns of the Liga FUTVE (130) and the Final del FUTVE (175), and each hit dumped 64 bytes
     before and 96 after. The first day of a session and the title days only. */
  static int done_day = -1;
  if (d == done_day || (done_day >= 0 && !((d >= 0 && d <= 1) || (d >= 142 && d <= 143) || (d >= 164 && d <= 165) || (d >= 171 && d <= 173)))) return;
  done_day = d;
  static const unsigned char P[][4] = {
    { 0x82,0x00,0xe9,0x07 }, { 0x82,0x00,0xea,0x07 }, { 0xe9,0x07,0x82,0x00 }, { 0xea,0x07,0x82,0x00 },
    { 0xaf,0x00,0xe9,0x07 }, { 0xaf,0x00,0xea,0x07 }, { 0xe9,0x07,0xaf,0x00 }, { 0xea,0x07,0xaf,0x00 } };
  const int NP = (int)(sizeof P / sizeof *P);
  unsigned char* o = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
  unsigned char* blk = o ? *(unsigned char**)(o + 0x48) : 0;
  if (o) logf("fl26swiss: honours search day %d: owner %p, +0x48 %p, +0x50 %p, +0x58 %p", d, (void*)o,
              *(void**)(o + 0x48), *(void**)(o + 0x50), *(void**)(o + 0x58));
  static unsigned char* buf = 0;
  if (!buf) buf = (unsigned char*)VirtualAlloc(0, (128u << 20) + 256, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE);
  if (!buf) return;
  unsigned char* a = (unsigned char*)0x10000;
  MEMORY_BASIC_INFORMATION mi;
  int hits = 0; size_t scanned = 0;
  while ((uintptr_t)a < 0x7ffffffe0000ull && hits < 24 && VirtualQuery(a, &mi, sizeof mi)) {
    unsigned char* rb = (unsigned char*)mi.BaseAddress; size_t rs = mi.RegionSize;
    a = rb + rs;
    if (mi.State != MEM_COMMIT || mi.Type != MEM_PRIVATE || mi.Protect != PAGE_READWRITE || rs > (128u << 20)) continue;   /* the career block's region (~77 MB) too */
    if (rb == g_tp_snap || rb == buf) continue;
    SIZE_T got = 0;
    if (!ReadProcessMemory(GetCurrentProcess(), rb, buf, rs, &got) || got != rs) continue;
    scanned += rs;
    for (size_t j = 128; j + 128 <= rs && hits < 40; j += 2) {
      unsigned char c = buf[j];
      if (c != 0x82 && c != 0xaf && c != 0xe9 && c != 0xea) continue;
      int w = -1;
      for (int q = 0; q < NP && w < 0; q++) if (P[q][0] == c && !memcmp(buf + j, P[q], 4)) w = q;
      /* Screenshot 30.10.: "Liga FUTVE 1" with an EMPTY list of seasons -- the count is kept apart
         from the season rows (which are corrected). The user's three titles are 130 (Liga FUTVE),
         142 (Final del Apertura), 131 (Copa Venezuela): a u16 130 with a u16 142 and a u16 131 within
         96 bytes is that count table, whatever its packing. */
      if (w < 0 && c == 0x82 && buf[j + 1] == 0) {
        int has142 = 0, has131 = 0;
        for (int q = -96; q <= 96; q += 2) {
          uint16_t v = *(uint16_t*)(buf + j + q);
          has142 |= v == 142; has131 |= v == 131;
        }
        if (has142 && has131) w = NP;               /* the count table, maybe */
      }
      if (w < 0) continue;
      logf("fl26swiss: honours search day %d: %s at %p (career block %+lld, region %p+%llx)", d,
           w < 4 ? "130 (Liga FUTVE) beside the season" : w < NP ? "175 (Final del FUTVE) beside the season" : "130 with 142 and 131 near (a title count?)",
           (void*)(rb + j),
           blk ? (long long)((rb + j) - blk) : 0LL, (void*)rb, (unsigned long long)rs);
      for (int q = -96; q < 128; q += 32) {
        char h[65]; tp_hex(buf + j + q, h);
        logf("fl26swiss:   %+4d %s", q, h);
      }
      hits++;
    }
  }
  logf("fl26swiss: honours search day %d: %d hit(s) in %llu MB of private read-write memory", d, hits,
       (unsigned long long)(scanned >> 20));
}

char daychk_handler(void* ctx)
{
  table_pool_old_slots("day");        /* B211: before the game's day, which may draw a cup's groups */
  /* the whole game day around the split league's ends too (30.10.): a title count raised outside
     the progressions would show here (reg 0xffff = the day) */
  int pd_day = today(), pd_on = FL26_TITLE_PROBES && g_tl_total && (pd_day == 0 || pd_day == 1 || pd_day == 142 || pd_day == 143);
  if (pd_on) pd_take();
  char r = ((daychk_fn)(uintptr_t)g_tramp_daychk)(ctx);
  if (pd_on) pd_show(0xffff);
  if (g_td_fresh) { g_td_fresh = 0; ccup_fill_ahead(0, "the July teardown", 0); }
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
  int jfrom = -1, jto = -1;
  if (d != last) {
    if (seen++ < 3) logf("fl26swiss: day loop on day %d", today());
    else if (last >= 0 && d > last + 1) logf("fl26swiss: day loop skipped day(s) %d..%d", last + 1, d - 1);
    if (last >= 0 && d > last + 1) { jfrom = last + 1; jto = d - 1; }
    last = d;
  }
  apclau_keep();
  lpre_fill_days();
  ccup_fill_days();
  if (jfrom >= 0) ccup_jump_check(jfrom, jto);     /* after today's fills: a fill day caught today is no loss */
  calendar_scup_fill_days();
  futve_copa_fill();                               /* fase 4: the January-December Copa Venezuela */
  futve_phase_reopen();                            /* fase 4: the Apertura enters its new season on day 41 */
  futve_clausura_early();                          /* fase 4: the Clausura on the calendar from February */
  aug_scup_fill_days();
  for (int p = NQR - 1; p >= 0; p--) q_fill(p);
  cal_dedupe();
  sched_days();
  title_probe();                                   /* read-only, around the title days */
  honours_fix();                                   /* the Liga FUTVE title: only the final's champion */
  supercup_title_fix();                            /* a Super Cup of ours: the game writes no title */
  futve_final_title_fix();                         /* fase 5: a Liga FUTVE play-off final the game left out */
  futve_clash_report();                            /* fase 4, read-only: the Venezuelan days against every other */
  cabinet_watch();                                 /* read-only: where new titles land */
  gt_report("day");                                /* read-only: who read the end-scene table */
  borrow_day_check();                              /* a borrow left over: the day after */
  /* honours_search (the whole-memory search of 30.10.) is off: it found its answer and it costs seconds */
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
static uint16_t g_td_list[512];
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
    if (!w) { if (g_ncupwin >= 32) continue; w = &g_cupwin[g_ncupwin++]; w->reg = cs->cup; }
    w->day = ad; w->club = c;
    logf("fl26swiss: cup reg %u won by %08x (day %d), kept for Super Cup %u", (unsigned)cs->cup, c, d,
         (unsigned)cs->reg);
  }
}

vec16_t* teardown_pre(uint64_t ctx, vec16_t* in)
{
  (void)ctx;
  if (!in || !in->b || in->e < in->b) return in;
  int n = (int)(in->e - in->b), euro = 0, has186 = 0, has187 = 0, has1210 = 0, has1027 = 0, has1029 = 0;
  if (n + 24 > 512) return in;
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
    if (like && !there && n + ndcl < 512) dcl[ndcl++] = id;
  }
  /* B275 (antonimus 29.10.): the Libertadores' qualifying phases 1 and 2 (pre-rounds aliased
     to it) close with its phase 3, the game's reg 8 -- in January, not with the July teardown,
     which took their matches and left the Competition Info page phase 3 alone from July */
  int nal = 0;
  for (int i = 0; i < g_nlpre; i++) if (g_lpre[i].alias && !lpre_cal(&g_lpre[i])) nal++;
  if (!euro) {
    int cal = bra && ncal, qal = nal && (libq || cal);
    /* fase 4 (31.10., second season with no Liga FUTVE): fl26join closes a January-December league
       of ours (11) at New Year, but not its split phases: the Apertura (191) kept last season's
       season flag and table, register_all took it for "already in a season" and the second
       season had no Apertura at all. The New Year list (it has 8) now takes the phases of a
       January-December split of ours too, so they enter again with their league on day 41. */
    int newyear = 0, nfut = 0;
    for (int j = 0; j < n; j++) if (in->b[j] == 8) newyear = 1;
    uint16_t fut[16];
    if (newyear && futve_cal())
      for (int i = 0; i < g_nsplits; i++) {
        if (!calyear(SPLITS[i].total)) continue;
        uint16_t ph[4] = { SPLITS[i].regular, SPLITS[i].group[0], SPLITS[i].group[1], SPLITS[i].group[2] };
        for (int q = 0; q < 4; q++) {
          int there = 0;
          if (!ph[q] || !get_rec(ph[q])) continue;
          for (int j = 0; j < n; j++) if (in->b[j] == ph[q]) there = 1;
          if (!there && nfut < 16) fut[nfut++] = ph[q];
        }
      }
    /* ... and its play-offs and final (kept out of the July teardown) */
    if (newyear && futve_cal())
      for (int c = 0; c < g_nccup; c++) {
        const ccup_t* cc = &g_ccup[c];
        if (!(cc->adv || cc->src[0]) || !ccup_world(cc)) continue;
        for (int g = -2; g < cc->groups && nfut < 16; g++) {
          uint16_t id = g == -2 ? cc->ko : g == -1 ? cc->reg : ccup_rep(cc, g);
          int there = 0;
          for (int j = 0; j < n; j++) if (in->b[j] == id) there = 1;
          for (int j = 0; j < nfut; j++) if (fut[j] == id) there = 1;
          if (!there && get_rec(id)) fut[nfut++] = id;
        }
      }
    if (!cal && !ndcl && !qal && !nfut) return in;
    memcpy(g_td_list, in->b, (size_t)n * sizeof(uint16_t));
    int k = n, added = 0;
    for (int i = 0; i < nfut && k < 512; i++) g_td_list[k++] = fut[i];
    if (nfut) logf("fl26swiss: New Year teardown on day %d -- %d phase(s) and play-off regulation(s) of a January-December league of ours closed with it",
                   today(), nfut);
    for (int c = 0; cal && c < g_nccup; c++) {
      const ccup_t* cc = &g_ccup[c];
      if (!cc->cal || !ccup_world(cc)) continue;
      for (int g = -2; g < cc->groups; g++) {
        uint16_t id = g == -2 ? cc->ko : g == -1 ? cc->reg : ccup_rep(cc, g);
        int there = 0;
        for (int j = 0; j < k; j++) if (g_td_list[j] == id) there = 1;
        if (!there && get_rec(id) && k < 512) { g_td_list[k++] = id; added++; }
      }
    }
    for (int i = 0; cal && i < g_nlpre; i++) {
      if (!lpre_cal(&g_lpre[i])) continue;
      for (int g = -1; g < lpre_rows(&g_lpre[i]); g++) {
        uint16_t id = g < 0 ? g_lpre[i].reg : lpre_tie(&g_lpre[i], g);
        int there = 0;
        for (int j = 0; j < k; j++) if (g_td_list[j] == id) there = 1;
        if (!there && get_rec(id) && k < 512) { g_td_list[k++] = id; added++; }
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
        if (!there && get_rec(id) && k < 512) { g_td_list[k++] = id; qadded++; }
      }
    }
    if (qal) logf("fl26swiss: teardown on day %d -- Libertadores qualifying phases 1/2: %d regulation(s) added (phase 3 %s on the list)",
                  today(), qadded, libq ? "is" : "is NOT");
    for (int i = 0; i < ndcl && k < 512; i++) g_td_list[k++] = dcl[i];
    if (ndcl) logf("fl26swiss: teardown on day %d -- %d cup(s) of ours closed with the cup they are dated as", today(), ndcl);
    g_td_vec.b = g_td_list; g_td_vec.e = g_td_list + k; g_td_vec.c = g_td_list + 512;
    return &g_td_vec;
  }
  g_td_fresh = 1;
  logf("fl26swiss: July teardown on day %d (%d ids)", today(), n);
  int uecl = get_rec(UECL_REG) && !(has186 && has187 && has1210);
  int cwc = cwc_world(), nccw = 0;
  for (int c = 0; c < g_nccup; c++) if (ccup_world(&g_ccup[c])) nccw++;
  /* A world built without the Conference League still has the Europa League play-off (188,
     tools/leaguebuilder.py since issue #33); with nothing else to add this returned here and
     left 188 and its ties out of the teardown, to outlive the season. */
  int pos = get_rec(CUPS[1].po) || get_rec(CUPS[2].po);
  for (int i = 3; i < 9; i++) if (g_qreg[i] && get_rec(g_qreg[i])) pos = 1;
  if (!uecl && !cwc && !nccw && !pos && !ndcl) return in;
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
      if (!there && get_rec(id) && k < 512) { g_td_list[k++] = id; ncwc++; }
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
    if (futve_cal() && (cc->adv || cc->src[0])) {
      /* fase 4 (31.10., Felix: the Apertura's play-off results gone from the calendar by December):
         the Liga FUTVE's play-offs and its final are of the calendar year -- closed at New Year */
      logf("fl26swiss: July teardown -- cup %u is the January-December Liga FUTVE's; kept open to New Year", (unsigned)cc->reg);
      continue;
    }
    int nc = 0;
    for (int g = -2; g < cc->groups; g++) {
      uint16_t id = g == -2 ? cc->ko : g == -1 ? cc->reg : ccup_rep(cc, g);
      int there = 0;
      for (int j = 0; j < k; j++) if (g_td_list[j] == id) there = 1;
      if (!there && get_rec(id) && k < 512) { g_td_list[k++] = id; nc++; }
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
      if (!there && get_rec(id) && k < 512) { g_td_list[k++] = id; npo++; }
    }
  for (int i = 3; i < 9; i++)
    for (int g = -1; g < 8 && g_qreg[i]; g++) {
      uint16_t id = (uint16_t)(g_qreg[i] + (g < 0 ? 0 : 1024 * (g + 1)));
      int there = 0;
      for (int j = 0; j < n; j++) if (in->b[j] == id) there = 1;
      if (!there && get_rec(id) && k < 512) { g_td_list[k++] = id; npo++; }
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
      if (!there && get_rec(id) && k < 512) { g_td_list[k++] = id; npre++; }
    }
  }
  if (npre) logf("fl26swiss: July teardown -- %d league cup pre-round regulation(s) added", npre);
  if (nkept) logf("fl26swiss: July teardown -- %d Libertadores qualifying phase(s) kept open until January, with phase 3", nkept);
  int nd = 0;
  for (int i = 0; i < ndcl && k < 512; i++) { g_td_list[k++] = dcl[i]; nd++; }
  if (nd) logf("fl26swiss: July teardown -- %d national/super cup(s) of ours added", nd);
  g_td_vec.b = g_td_list; g_td_vec.e = g_td_list + k; g_td_vec.c = g_td_list + 512;
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
 if(g_native_uefa && (phase==3 || phase==5))return 0;   /* FL27 draws its own league phase pages */
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
 *   - the European places of the league from the access list in use (g_access: the world's own,
 *     or the shipped one), by position: the Champions League (its play-off, the Libertadores, the
 *     AFC Champions League too), the Europa League, the Conference League;
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
static const char* const ZONE_NAME[ZONE_N] = { "Champions League", "Europa League", "Conference League", "up", "play-off", "down" };
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
  void* db = ((zdb_fn)(uintptr_t)(g_base + ZDB_RVA))();
  return db ? ((zcomp_fn)(uintptr_t)(g_base + ZCOMP_RVA))(*(void**)((unsigned char*)db + 0x48), reg) : 0;
}
static unsigned zclubs(uint16_t reg, unsigned dflt)
{
  unsigned char* c = zcomp(reg);
  unsigned n = c ? *(uint16_t*)(c + 0x30a) & 0x7f : 0;
  return n ? n : dflt;
}
/* the European place of the access list for league reg's place rank, or -1 */
static int zone_access(uint16_t reg, unsigned rank)
{
  for (size_t k = 0; k < g_naccess; k++) {
    const access_t* a = &g_access[k];
    if (a->reg != reg || a->rank != rank) continue;
    switch (a->comp) {
      case UCL: case UCLQ: case LIB: case LIBQ: case AFCL: return ZONE_CL;
      case UEL: case UELQ: return ZONE_EL;
      case UECL: case UECLQ: return ZONE_ECL;
    }
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
  return zone_down(reg, i) ? ZONE_DOWN : -1;
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
}

/* 0 ok; 2 signature mismatch; 3 VirtualAlloc failed; 4 VirtualProtect failed; 9 bad config;
   +10 for the date hook, +20 for the group hook */


/* ---- the trophy ceremony of our finals (30.10.) ----
 * Felix: no trophy ceremony after a final of ours (Apertura, Clausura, Final del FUTVE, Copa
 * Venezuela, Supercopa). The match setup at 0x141f51780.. fills the presentation block (rdi): +0x5170
 * the tournament (after Sider's trophy_rewrite: 16 for ours), +0x5174 its trophy, +0x5179 the kind
 * of match it decides. The kind comes from 0x140a7f370/3b0/3e0 (league / cup / other), which read
 * the match's tournament [rbx+0x498] -- and take any id from 0xda (218) up as 0: ours never are a cup
 * there, +0x5179 stays 0, and the post-match flow (0x1423f0ae0: kind 5 -> case 3 -> state 0x10017
 * for the trophy entry 16) goes to the plain end (0x10008). At 0x141f519b9, after the kind is set:
 * a final of ours with no kind gets 5 (a cup's final), as a UEFA final has. */
#define CER_SITE_RVA 0x1f519b9
#define CER_BACK_RVA 0x1f519c1
#define CER_CALL_RVA 0xa7f3a0

/* 30.10. (read-only): a snapshot of a final's match block (rbx at the setup) and presentation block
   (rdi), to compare the ICC's (with its ceremony) with ours byte by byte. ReadProcessMemory: a page
   that is not there ends the copy, never the game. Files in SiderAddons, one per tournament a day. */
static void cer_dump(const char* what, int d, uint32_t tid, const unsigned char* p, size_t n)
{
  static unsigned char* buf = 0;
  if (!buf) buf = (unsigned char*)VirtualAlloc(0, 0x20000, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE);
  if (!buf || n > 0x20000) return;
  size_t got = 0;
  while (got < n) {
    SIZE_T r = 0;
    size_t chunk = 0x1000 - (((uintptr_t)(p + got)) & 0xfff);
    if (chunk > n - got) chunk = n - got;
    if (!ReadProcessMemory(GetCurrentProcess(), p + got, buf + got, chunk, &r) || r != chunk) break;
    got += chunk;
  }
  char path[160];
  snprintf(path, sizeof path, ".\\SiderAddons\\fl26cer_d%d_t%u_%s.bin", d, tid, what);
  HANDLE h = CreateFileA(path, GENERIC_WRITE, 0, 0, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, 0);
  if (h == INVALID_HANDLE_VALUE) { logf("fl26swiss: ceremony -- dump %s not written", path); return; }
  DWORD w = 0; WriteFile(h, buf, (DWORD)got, &w, 0); CloseHandle(h);
  logf("fl26swiss: ceremony -- dump %s: %u byte(s)", path, (unsigned)w);
}

#define FL26_CER_ICC 0
#define CER_AS_TID    26   /* the Copa Libertadores in the presentation block (reg 10 in the career) */
#define CER_AS_TROPHY 23   /* its trophy */
static volatile LONG g_gt_phase;           /* the guard tracing (below): the trophy check count */
static volatile LONG g_gt_pm_done;         /* the post-match ran: no more watching that day */
static void gt_pm_off(void);
static void gt_report(const char* when);
static unsigned char* g_cer_pres;          /* the presentation block of a final of ours (ceremony_fix) */
static int g_final_day = -9;               /* the day a final (ours or the game's) was set up */
static uint16_t g_cer_reg = 0;
static int g_cer_hit_day = -9;              /* the day a final of ours was set up (hit) */
static volatile DWORD g_match_tid = 0;       /* the thread that runs the match setup (the game's) */
/* 31.10. (session 010, the last try): the final's own match record borrows a real cup's regulation
   during the match (CER_BORROW_REG), put back at full time's result scene (fl26swiss.lua calls
   fl26_swiss_borrow_end on result_env_full) or the day after at the latest. */
#define CER_BORROW 0
#define CER_STACKS 0
#define CER_BORROW_REG 10
static unsigned char* g_borrow_mr = 0;
static uint16_t g_borrow_orig = 0;
static int g_borrow_day = -9;
__declspec(dllexport) int fl26_swiss_borrow_end(void)
{
  if (!g_borrow_mr) return 0;
  logf("fl26swiss: borrow -- the final's match record back to regulation %u (it was %u)", (unsigned)g_borrow_orig,
       (unsigned)*(uint16_t*)(g_borrow_mr + 4));
  *(uint16_t*)(g_borrow_mr + 4) = g_borrow_orig;
  g_borrow_mr = 0;
  return 1;
}
static void borrow_day_check(void) { if (g_borrow_mr && today() != g_borrow_day) fl26_swiss_borrow_end(); }

/* 31.10.: the match block the game's match code reads ([[0x141467e83's rip-relative global]]+0x2ad0),
   for a snapshot at full time (cinematics.lua's trophy_rewrite calls fl26_swiss_cer_note) */
static unsigned char* match_block_now(void)
{
  const unsigned char* c = (const unsigned char*)(uintptr_t)(g_base + 0x1467e83);
  if (c[0] != 0x48 || c[1] != 0x8b || c[2] != 0x05) return 0;
  unsigned char** gp = (unsigned char**)(c + 7 + *(const int32_t*)(c + 3));
  unsigned char* o = *gp;
  return o ? *(unsigned char**)(o + 0x2ad0) : 0;
}
static void cer_fields(const char* when, unsigned char* m, unsigned char* pres)
{
  if (m) logf("fl26swiss: ceremony -- %s: match %p: +2 %u +4 %u +8 %u +496 %#x, context %u/%u/%#x/%u, reg %u, team0 %u/%#x/%u, team1 %u/%#x/%u",
              when, (void*)m, m[2], m[4], *(uint32_t*)(m + 8), m[0x496], *(uint32_t*)(m + 0x498), *(uint32_t*)(m + 0x49c),
              *(uint32_t*)(m + 0x4a0), *(uint32_t*)(m + 0x4a4), *(uint32_t*)(m + 0x5390),
              m[0xe900], *(uint32_t*)(m + 0xe904), m[0xeb04], m[0x11104], *(uint32_t*)(m + 0x11108), m[0x11308]);
  if (pres) logf("fl26swiss: ceremony -- %s: presentation: tournament %u trophy %u kind %u flag %u +5214 %u +5218 %u",
                 when, *(uint32_t*)(pres + 0x5170), *(uint32_t*)(pres + 0x5174), pres[0x5179], pres[0x5178],
                 *(uint32_t*)(pres + 0x5214), pres[0x5218]);
}
__declspec(dllexport) int fl26_swiss_cer_note(int tid, int match_info)
{
  static int n = 0, day = -9;
  int d = today();
  if (d != day) { day = d; n = 0; }
  if (!g_cer_pres || n >= 40) return 0;
  n++;
  /* every call overwrites the same two files: what is left is the last call's (full time) */
  unsigned char* m = match_block_now();
  if (m) cer_dump("last_match", d, (uint32_t)tid, m, 0x12000);
  cer_dump("last_pres", d, (uint32_t)tid, g_cer_pres, 0x5400);
  char w2[48]; snprintf(w2, sizeof w2, "trophy_rewrite %d (match_info %d), call %d", tid, match_info, n);
  cer_fields(w2, m, g_cer_pres);
  return n;
}
#define CER_DECIDE 0
#define CER_PRES 0   /* 31.10. (session 011): the presentation/context disguise off; the tournament map answers instead */
#define CER_END 1
static void ceremony_fix(unsigned char* pres, unsigned char* m)
{
  g_match_tid = GetCurrentThreadId();
  if (!pres || !m) return;
  uint32_t tid = *(uint32_t*)(m + 0x498), as = *(uint32_t*)(pres + 0x5170);
  int d = today();
  /* 30.10. third run: still no line -- today() may be -1 in a match; nothing waits on it now.
     A final of ours: its own regulation (a knockout of ours of one day is all final; the Final del
     FUTVE on its second day; a dated-like cup on its last day or its final round, kind 4), or the
     trophy entry 16 on the day of one. */
  uint16_t hit = 0;
  /* 30.10. sixth run (the Supercopa, day 227: "tournament 217 ... c31a 4 ... not a final of ours"):
     this session's load came after the season's dating, so no day was noted for 256. The surest
     source is the user's own match today: the day schedule's entry (blk+SCHED_ENT_OFF, 16 bytes a
     day, +0 the match id, +12 the club) and its record (+4 the regulation, +7 bits 4-5 the leg). */
  uint16_t sreg = 0xffff; int sleg = -1; unsigned char* umr = 0;
  {
    unsigned char* o = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
    unsigned char* blk = o ? *(unsigned char**)(o + 0x48) : 0;
    if (blk && d >= 0 && d < 365) {
      unsigned char* e = blk + SCHED_ENT_OFF + (size_t)d * 16;
      uint32_t user = *(uint32_t*)(blk + USER_CLUB_OFF);
      unsigned char* mr = *(uint16_t*)e != 0xffff && *(uint32_t*)(e + 12) == user ? ko_match(*(uint16_t*)e) : 0;
      if (mr) { sreg = *(uint16_t*)(mr + 4); sleg = (mr[7] >> 4) & 3; umr = mr; }
      if (mr && mr == g_borrow_mr) sreg = g_borrow_orig;     /* borrowed for the match: its own id */
    }
  }
  if (sreg != 0xffff && (tid == 217 || tid >= 0xda || tid == CER_AS_TID || tid == 30)) {
    for (int k = 0; k < g_nccup && !hit; k++) {
      const ccup_t* c = &g_ccup[k];
      if (!(c->adv || c->src[0]) || c->ko != sreg) continue;
      if (c->nd <= 1 || sleg != 0) hit = sreg;      /* two legs: not the first */
    }
    for (int i = 0; i < g_naug_scup && !hit; i++) if (g_aug_scup[i].reg == sreg) hit = sreg;
    for (int i = 0; i < g_ndl_last && !hit; i++) if (g_dl_last[i].reg == sreg && m[0xc31a] == 4) hit = sreg;
    if (!hit && sreg == 255 && m[0xc31a] == 4) hit = sreg;   /* the Copa Venezuela, its final round */
  }
  /* 30.10. fourth run (day 164, the Clausura final): "tournament 217 (as 34, trophy 32): c31a 4,
     e904 13, kind 0". The match carries 217 for a tournament of ours, not 262, and its round is a
     final's (c31a 4). So: 217 (or an id of ours, or the entry 16), a final's round, the day of a
     final of ours. */
  int anon = tid == 217;                           /* not 16: a real tournament of the game */
  for (int k = 0; k < g_nccup && !hit; k++) {
    const ccup_t* c = &g_ccup[k];
    if (!(c->adv || c->src[0]) || !c->nd) continue;
    if (anon && m[0xc31a] == 4 && d >= 0 && d == (int)c->days[c->nd - 1]) hit = c->ko;
  }
  for (int i = 0; i < g_ndl_last && !hit; i++) {
    /* a Super Cup of ours is one match: its day is enough (its round kind may not be a final's) */
    int scup = 0;
    for (int j = 0; j < g_naug_scup; j++) scup |= g_aug_scup[j].reg == g_dl_last[i].reg;
    if (anon && (m[0xc31a] == 4 || scup) && d >= 0 && d == g_dl_last[i].day) hit = g_dl_last[i].reg;
  }
  for (int k = 0; k < g_nccup && !hit; k++) {
    const ccup_t* c = &g_ccup[k];
    if (!(c->adv || c->src[0]) || !c->nd) continue;
    int fday = d >= 0 && d == (int)c->days[c->nd - 1];
    if (tid == c->ko && (c->nd == 1 || fday)) hit = c->ko;
  }
  for (int i = 0; i < g_ndl_last && !hit; i++) {
    int fday = d >= 0 && d == g_dl_last[i].day;
    if (tid == g_dl_last[i].reg && (fday || m[0xc31a] == 4)) hit = g_dl_last[i].reg;
  }
  for (int i = 0; i < g_naug_scup && !hit; i++) if (tid == g_aug_scup[i].reg) hit = g_aug_scup[i].reg;
  static int said = 0; static uint32_t s_tid = 0xffffffffu, s_as = 0; static int s_day = -9; static unsigned s_k = 0x100;
  {
    static int dumps = 0; static uint32_t dt = 0xffffffffu; static int dd = -9;
    if (dumps < 8 && (dt != tid || dd != d) && (hit || m[0xc31a] == 4 || pres[0x5179])) {
      dumps++; dt = tid; dd = d;
      cer_dump("match", d, tid, m, 0x12000);
      cer_dump("pres", d, tid, pres, 0x5400);
    }
  }
  if (said < 80 && (s_tid != tid || s_as != as || s_day != d || s_k != pres[0x5179])) {
    said++; s_tid = tid; s_as = as; s_day = d; s_k = pres[0x5179];
    logf("fl26swiss: ceremony -- day %d, tournament %u (as %u, trophy %u): c319 %u c31a %u c31b %u c31c %u c324 %u e904 %08x, "
         "kind %u, flag %u; %s %u", d, tid, as, *(uint32_t*)(pres + 0x5174), m[0xc319], m[0xc31a], m[0xc31b],
         *(uint32_t*)(m + 0xc31c), m[0xc324], *(uint32_t*)(m + 0xe904), pres[0x5179], pres[0x5178],
         hit ? "a final of ours: kind 5 (a cup's final), reg" : "not a final of ours", (unsigned)hit);
    logf("fl26swiss: ceremony -- the user's match today: reg %u, leg %d", (unsigned)sreg, sleg);
    logf("fl26swiss: ceremony -- more: pres+98 %u +516c %u +51fc %02x%02x%02x%02x +522f %u +5174 %u; m+18 %llx +30 %llx "
         "+38 %u +3c %u +40 %u +8 %u +c318 %02x%02x%02x%02x +c320 %08x +6284 %08x", *(uint32_t*)(pres + 0x98), pres[0x516c],
         pres[0x51fc], pres[0x51fd], pres[0x51fe], pres[0x51ff], pres[0x522f], *(uint32_t*)(pres + 0x5174),
         (unsigned long long)*(uint64_t*)(m + 0x18), (unsigned long long)*(uint64_t*)(m + 0x30),
         *(uint32_t*)(m + 0x38), *(uint32_t*)(m + 0x3c), *(uint32_t*)(m + 0x40), *(uint32_t*)(m + 8),
         m[0xc318], m[0xc319], m[0xc31a], m[0xc31b], *(uint32_t*)(m + 0xc320), *(uint32_t*)(m + 0x6284));
  }
  /* 30.10. eighth run (ICC v Supercopa, both ending in state 0x1002f, tournament 118-120, kind 9):
     the ICC (trophy 117) shows its ceremony, ours (trophy 32) not. The trophy picks the ceremony's
     assets at load (0x141f4d534: 117 -> asset 0x21c, 32 -> 0x210). So a final of ours takes the
     ICC's trophy as well; the model it shows is a matter of files after that. */
  /* 30.10./31.10. (Felix: the Copa Libertadores final, Kick Off > Cup, won -- its ceremony shows):
     "tournament 26 (as 26, trophy 23): c31a 4 ... kind 5", and the post-match flow ends in 0x10028,
     the state that works out who lifts the cup (+0x5214 the side, +0x5218 the player). Ours came as
     217 (an id from 0xda up is "unknown" to the game) / 34 (the entry 16) and ended in 0x1002f or
     0x10032, no lifter. So a final of ours is presented as the Libertadores' final: tournament 26,
     its trophy 23, kind 5 (the post-match group of 3, 4, 23..30: kind 5 -> 0x10028). Only the
     presentation block; the match and its competition stay ours. */
  /* 31.10.: the setup runs again at every trophy check of the match (kick-off, goals, half time,
     full time: Sider's trophy_rewrite lines), so the last call's blocks are full time's. Overwritten
     each call; the fields logged (40 a day). Sider's Lua has no pcall: nothing here relies on Lua. */
  /* any final (a final's round, c31a 4) or one of ours: the reference (the Libertadores final,
     replayed) gets its full-time blocks too */
  if (hit || m[0xc31a] == 4) {
    cer_guard_end(d);
    InterlockedIncrement(&g_gt_phase);
    { char w[32]; snprintf(w, sizeof w, "check %ld", (long)g_gt_phase); gt_report(w); }
    uint32_t nm = hit ? hit : tid;
    g_final_day = d;
    static int nchk = 0, cday = -9;
    if (cday != d) { cday = d; nchk = 0; }
    if (nchk < 24) {                                 /* each trophy check of the match, numbered */
      char w[24];
      snprintf(w, sizeof w, "chk%02d_match", nchk); cer_dump(w, d, nm, m, 0x12000);
      snprintf(w, sizeof w, "chk%02d_pres", nchk);  cer_dump(w, d, nm, pres, 0x5400);
      nchk++;
    }
    cer_dump("last_match", d, nm, m, 0x12000);
    cer_dump("last_pres", d, nm, pres, 0x5400);
    static int nf = 0, fd = -9;
    if (fd != d) { fd = d; nf = 0; }
    if (nf++ < 40) cer_fields("a trophy check of the final (before ours)", m, pres);
  }
  if (hit && CER_PRES) {
    /* 31.10. (session 002): the match block's header, byte by byte, in the finals that had the
       ceremony -- the Libertadores (01 00 01 00 0b 07 01 32 | 01 00 00 00) and the ICC (01 00 01 00
       08 07 01 2b | 01 00 00 00) -- and in ours without it -- the Clausura (01 00 00 00 06 07 01 33 |
       00 ..), the Supercopa (01 00 01 00 08 07 01 2c | 00 ..). The dword at +8 is 1 only where the
       ceremony played; at full time the Libertadores asked for the end scenes (fixdemo\end:
       end_timeup_*, end_joy_*, end_trophy_*), ours for the plain full time (fixdemo\timeup\tu_full_*).
       The exe's match-environment vocabulary starts with DECIDEMATCH (0x14344d610: DECIDEMATCH,
       HOMEAWAY, 1STLEG, 2NDLEG, EXTIME, PKMATCH, ...): +8 is taken as "this match decides a title",
       +2 with it (1 in the three finals of a cup). Set on the deciding match of ours only (hit). */
    /* 31.10. (session 005): +2/+8 alone (session 003) kept timeup. The header's last difference is
       +4: 0x0b the Libertadores (two legs), 8 the ICC (one match), 6 ours. Now the whole header as
       the ICC final's: +2 1, +4 8, +8 1. */
    if (CER_DECIDE && (*(uint32_t*)(m + 8) != 1 || m[2] != 1 || m[4] != 8)) {
      logf("fl26swiss: ceremony -- the match header +2 %u, +4 %u, +8 %u set to the ICC final's (1, 8, 1)", m[2], m[4], *(uint32_t*)(m + 8));
      m[2] = 1; m[4] = 8; *(uint32_t*)(m + 8) = 1;
    }
    pres[0x5179] = 5; g_cer_pres = pres; g_cer_reg = hit; g_cer_hit_day = d;
    if (CER_BORROW && umr && !g_borrow_mr && *(uint16_t*)(umr + 4) == hit) {
      g_borrow_mr = umr; g_borrow_orig = hit; g_borrow_day = d;
      *(uint16_t*)(umr + 4) = CER_BORROW_REG;
      logf("fl26swiss: borrow -- the final's match record (reg %u) takes regulation %u for the match", (unsigned)hit, (unsigned)CER_BORROW_REG);
    }
    *(uint32_t*)(pres + 0x5170) = CER_AS_TID;
    *(uint32_t*)(pres + 0x5174) = CER_AS_TROPHY;
    /* 31.10. (the Clausura final presented as the Libertadores' reached 0x10028 -- and no ceremony):
       the match block's competition context is read after the setup too. The Libertadores final's
       (Kick Off > Cup): +0x498 26, +0x49c 23, +0x4a0 0x410, +0x4a4 9; ours 217, 217, 0x102, 0. */
    /* 31.10. (the Clausura final as the Libertadores', context and all, state 0x10028 -- no
       ceremony; the Libertadores final was in the Master League too): what is left is the two
       teams' match flags, +0xe900 (byte), +0xe904, +0xeb04 a team (0x2804 apart): 5/0x13/1 here,
       0/0x02/0 in the Libertadores final and the ICC. Set as theirs, logged. */
    for (int t = 0; t < 2; t++) {
      unsigned char* tb = m + (size_t)t * 0x2804;
      if (tb[0xe900] || *(uint32_t*)(tb + 0xe904) != 2 || tb[0xeb04]) {
        logf("fl26swiss: ceremony -- team %d's flags %u/%#x/%u set to the Libertadores final's (0/0x2/0)",
             t, tb[0xe900], *(uint32_t*)(tb + 0xe904), tb[0xeb04]);
        tb[0xe900] = 0; *(uint32_t*)(tb + 0xe904) = 2; tb[0xeb04] = 0;
      }
    }
    /* 31.10. second variant, a Super Cup of ours only: the career's regulation in the match block
       (+0x5390: the Libertadores final's 10, the ICC's 107 -- ours 256, from 0xda up). */
    /* 31.10. (Felix: the Apertura final too): every final of ours, not only a Super Cup */
    if (*(uint32_t*)(m + 0x5390) == hit) {
      logf("fl26swiss: ceremony -- the match's regulation %u set to the Libertadores' (10)", (unsigned)hit);
      *(uint32_t*)(m + 0x5390) = 10;
    }
    {
      unsigned char* gm = match_block_now();
      logf("fl26swiss: ceremony -- the match block %p, the game's global one %p%s", (void*)m, (void*)gm, gm == m ? " (the same)" : "");
    }
    if (*(uint32_t*)(m + 0x498) != CER_AS_TID) {
      logf("fl26swiss: ceremony -- the match's context %u/%u/%#x/%u set to the Libertadores final's",
           *(uint32_t*)(m + 0x498), *(uint32_t*)(m + 0x49c), *(uint32_t*)(m + 0x4a0), *(uint32_t*)(m + 0x4a4));
      *(uint32_t*)(m + 0x498) = CER_AS_TID; *(uint32_t*)(m + 0x49c) = CER_AS_TROPHY;
      *(uint32_t*)(m + 0x4a0) = 0x410; *(uint32_t*)(m + 0x4a4) = 9;
    }
  }
}
static int ceremony_install(uint64_t exe_base)
{
  unsigned char* s = (unsigned char*)(uintptr_t)(exe_base + CER_SITE_RVA);
  if (s[0] != 0x48 || s[1] != 0x8b || s[2] != 0xcb || s[3] != 0xe8 ||
      (uint64_t)(uintptr_t)(s + 8) + *(int32_t*)(s + 4) != exe_base + CER_CALL_RVA || s[8] != 0x84 || s[9] != 0xc0)
    return 2;
  unsigned char* t = near_alloc(exe_base);
  if (!t) return 3;
  unsigned char* p = t;
  /* sub rsp,0x20; mov rcx,rdi; mov rdx,rbx; mov rax,imm64; call rax; add rsp,0x20 -- the site is a
     call's (rsp 16-aligned there): 0x20 of shadow space keeps the handler's entry at 8 mod 16. 0x28
     misaligned it, and the handler's first logf (aligned SSE stores) crashed the game (30.10.). */
  *p++ = 0x48; *p++ = 0x83; *p++ = 0xec; *p++ = 0x20;
  *p++ = 0x48; *p++ = 0x89; *p++ = 0xf9;
  *p++ = 0x48; *p++ = 0x89; *p++ = 0xda;
  *p++ = 0x48; *p++ = 0xb8; *(uint64_t*)p = (uint64_t)(uintptr_t)ceremony_fix; p += 8;
  *p++ = 0xff; *p++ = 0xd0;
  *p++ = 0x48; *p++ = 0x83; *p++ = 0xc4; *p++ = 0x20;
  /* the displaced code: mov rcx,rbx; mov rax,0x140a7f3a0; call rax */
  *p++ = 0x48; *p++ = 0x8b; *p++ = 0xcb;
  *p++ = 0x48; *p++ = 0xb8; *(uint64_t*)p = exe_base + CER_CALL_RVA; p += 8;
  *p++ = 0xff; *p++ = 0xd0;
  /* jmp [rip+0] -> 0x141f519c1 */
  *p++ = 0xff; *p++ = 0x25; *(uint32_t*)p = 0; p += 4; *(uint64_t*)p = exe_base + CER_BACK_RVA; p += 8;
  FlushInstructionCache(GetCurrentProcess(), t, (SIZE_T)(p - t));
  DWORD old;
  if (!VirtualProtect(s, 8, PAGE_EXECUTE_READWRITE, &old)) return 4;
  s[0] = 0xe9; *(int32_t*)(s + 1) = (int32_t)((int64_t)(uintptr_t)t - (int64_t)(uintptr_t)(s + 5));
  s[5] = 0x90; s[6] = 0x90; s[7] = 0x90;
  VirtualProtect(s, 8, old, &old);
  FlushInstructionCache(GetCurrentProcess(), s, 8);
  return 0;
}


/* 30.10. (read-only): the post-match flow at 0x1423f0ae0 -- a state machine whose state is
   *[this+8] (0x10000 start, 0x10008 the plain end, 0x10017/0x10032 the finals' ...). Each change
   is logged with the presentation block's fields it reads, to compare a final with a ceremony (the
   ICC) with ours. Site 0x1423f0af0: mov r15,rax; cmp byte [rax+0x522f],0 (then je). */
#define PM_SITE_RVA 0x23f0af0
#define PM_BACK_RVA 0x23f0afa
#define PM_END_RVA  0x23f1194
static void pm_log(const char* where, unsigned char* self, unsigned char* pres)
{
  static int said = 0;
  uint32_t* sp = *(uint32_t**)(self + 8);
  if (!sp || said >= 300) return;
  said++;
  logf("fl26swiss: post-match %s -- state %#x: tournament %u kind %u flag %u trophy %u +98 %u +516c %u +51fc %02x%02x%02x%02x "
       "+5214 %u +5218 %u +522f %u; team0 +2914 %u +291e %u +291f %u, team1 +5144 %u +514e %u +514f %u%s",
       where, *sp, *(uint32_t*)(pres + 0x5170), pres[0x5179], pres[0x5178], *(uint32_t*)(pres + 0x5174),
       *(uint32_t*)(pres + 0x98), pres[0x516c], pres[0x51fc], pres[0x51fd], pres[0x51fe], pres[0x51ff],
       *(uint32_t*)(pres + 0x5214), pres[0x5218], pres[0x522f], *(uint32_t*)(pres + 0x2914), pres[0x291e], pres[0x291f],
       *(uint32_t*)(pres + 0x5144), pres[0x514e], pres[0x514f], pres == g_cer_pres ? " (a final of ours)" : "");
}
/* 30.10. (the ICC, day 219: "tournament 118, kind 9" -- its ceremony shows): the post-match switch
   gives the ICC's group (118..120) the trophy state 0x1002f when the kind is 9 and both teams' +7
   flags (+0x291f, +0x514f) are set; the default group (an id past 0xaf, ours 217) gives 0x1002f for a
   cup's final (kind 5) when neither team's +0x2914 is 1. Ours came as 34 (the AFC group: 0x10032),
   and showed nothing. So at the start state a final of ours takes the ICC's way, else the default
   one, else stays as it is. */
static void postmatch_watch(unsigned char* self, unsigned char* pres)
{
  if (!self || !pres) return;
  uint32_t* sp = *(uint32_t**)(self + 8);
  if (!sp) return;
  static uint32_t last = 0xffffffffu;
  uint32_t st = *sp;
  if (st != last || pres == g_cer_pres) { last = st; pm_log("entry", self, pres); }
  if (st != 0x10000 || pres != g_cer_pres || !g_cer_reg) return;
  /* 30.10. seventh run (the Supercopa): the default way reached 0x1002f -- the state the ICC's
     group gives -- and still no ceremony. So now the ICC's own way, all of it: its tournament
     (118), its kind (9) and the two teams' +7 flags it asks for; the trophy (32) stays ours. */
  /* 30.10. ninth run: with the ICC's tournament, kind, flags and trophy, state 0x1002f as the ICC's --
     and still no ceremony. What is left differs outside the presentation block (the match and the
     competition). Off (FL26_CER_ICC 0) until that is found: the final keeps kind 5 (its atmosphere). */
  if (!FL26_CER_ICC) {
    logf("fl26swiss: post-match -- a final of ours (reg %u): presented as tournament %u, trophy %u, kind %u",
         (unsigned)g_cer_reg, *(uint32_t*)(pres + 0x5170), *(uint32_t*)(pres + 0x5174), pres[0x5179]);
    g_cer_reg = 0; return;
  }
  const char* how = "the ICC's way (118, kind 9, both teams' +7 flags)";
  *(uint32_t*)(pres + 0x5170) = 118; pres[0x5179] = 9;
  if (!pres[0x291f]) pres[0x291f] = 1;
  if (!pres[0x514f]) pres[0x514f] = 1;
  logf("fl26swiss: post-match -- a final of ours (reg %u): %s", (unsigned)g_cer_reg, how);
  g_cer_reg = 0;
}
static void postmatch_end(unsigned char* self, unsigned char* pres)
{
  if (!self || !pres) return;
  static uint32_t last = 0xffffffffu;
  uint32_t* sp = *(uint32_t**)(self + 8);
  if (!sp || (*sp == last && pres != g_cer_pres)) return;
  last = *sp;
  pm_log("end", self, pres);
  gt_pm_off();
  if (g_final_day >= 0 && g_final_day == today()) {
    static int n = 0;
    if (n < 6) { char w[24]; snprintf(w, sizeof w, "pmend%d_pres", n++); cer_dump(w, today(), *sp, pres, 0x5400); }
  }
}
static int postmatch_install(uint64_t exe_base)
{
  static const unsigned char sig[12] = { 0x4c,0x8b,0xf8, 0x80,0xb8,0x2f,0x52,0x00,0x00,0x00, 0x74,0x12 };
  unsigned char* s = (unsigned char*)(uintptr_t)(exe_base + PM_SITE_RVA);
  if (memcmp(s, sig, sizeof sig)) return 2;
  unsigned char* t = near_alloc(exe_base);
  if (!t) return 3;
  unsigned char* p = t;
  *p++ = 0x4c; *p++ = 0x8b; *p++ = 0xf8;                       /* mov r15, rax */
  *p++ = 0x48; *p++ = 0x83; *p++ = 0xec; *p++ = 0x20;          /* sub rsp, 0x20 (aligned at the site) */
  *p++ = 0x48; *p++ = 0x89; *p++ = 0xf9;                       /* mov rcx, rdi */
  *p++ = 0x4c; *p++ = 0x89; *p++ = 0xfa;                       /* mov rdx, r15 */
  *p++ = 0x48; *p++ = 0xb8; *(uint64_t*)p = (uint64_t)(uintptr_t)postmatch_watch; p += 8;
  *p++ = 0xff; *p++ = 0xd0;                                    /* call rax */
  *p++ = 0x48; *p++ = 0x83; *p++ = 0xc4; *p++ = 0x20;          /* add rsp, 0x20 */
  *p++ = 0x41; *p++ = 0x80; *p++ = 0xbf; *(uint32_t*)p = 0x522f; p += 4; *p++ = 0x00;   /* cmp byte [r15+0x522f], 0 */
  *p++ = 0xff; *p++ = 0x25; *(uint32_t*)p = 0; p += 4; *(uint64_t*)p = exe_base + PM_BACK_RVA; p += 8;
  FlushInstructionCache(GetCurrentProcess(), t, (SIZE_T)(p - t));
  DWORD old;
  if (!VirtualProtect(s, 10, PAGE_EXECUTE_READWRITE, &old)) return 4;
  s[0] = 0xe9; *(int32_t*)(s + 1) = (int32_t)((int64_t)(uintptr_t)t - (int64_t)(uintptr_t)(s + 5));
  for (int i = 5; i < 10; i++) s[i] = 0x90;
  VirtualProtect(s, 10, old, &old);
  FlushInstructionCache(GetCurrentProcess(), s, 10);
  /* the end (0x1423f1194: mov rbx,[rsp+0x60]; mov rsi,[rsp+0x38]): the state the switch left */
  static const unsigned char sig2[10] = { 0x48,0x8b,0x5c,0x24,0x60, 0x48,0x8b,0x74,0x24,0x38 };
  unsigned char* e = (unsigned char*)(uintptr_t)(exe_base + PM_END_RVA);
  if (memcmp(e, sig2, sizeof sig2)) return 5;
  unsigned char* q = p + 16;                                   /* the same page, after the first stub */
  unsigned char* t2 = q;
  *q++ = 0x48; *q++ = 0x83; *q++ = 0xec; *q++ = 0x20;          /* sub rsp, 0x20 */
  *q++ = 0x48; *q++ = 0x89; *q++ = 0xf9;                       /* mov rcx, rdi */
  *q++ = 0x4c; *q++ = 0x89; *q++ = 0xfa;                       /* mov rdx, r15 */
  *q++ = 0x48; *q++ = 0xb8; *(uint64_t*)q = (uint64_t)(uintptr_t)postmatch_end; q += 8;
  *q++ = 0xff; *q++ = 0xd0;
  *q++ = 0x48; *q++ = 0x83; *q++ = 0xc4; *q++ = 0x20;
  memcpy(q, sig2, sizeof sig2); q += sizeof sig2;              /* the displaced loads, rsp as it was */
  *q++ = 0xff; *q++ = 0x25; *(uint32_t*)q = 0; q += 4; *(uint64_t*)q = exe_base + PM_END_RVA + 10; q += 8;
  FlushInstructionCache(GetCurrentProcess(), t2, (SIZE_T)(q - t2));
  if (!VirtualProtect(e, 10, PAGE_EXECUTE_READWRITE, &old)) return 6;
  e[0] = 0xe9; *(int32_t*)(e + 1) = (int32_t)((int64_t)(uintptr_t)t2 - (int64_t)(uintptr_t)(e + 5));
  for (int i = 5; i < 10; i++) e[i] = 0x90;
  VirtualProtect(e, 10, old, &old);
  FlushInstructionCache(GetCurrentProcess(), e, 10);
  return 0;
}


/* ---- 31.10. who reads the end-scene table (read-only tracing) ----
 * Felix: "can we see in the exe where it loads that it is a final?". Sider's livecpk_data_ready hands
 * fl26swiss.lua each file's data as it is read; for common\demo\fixdemo\end\table_end.bin the
 * buffer is handed here and its pages get PAGE_GUARD. A vectored handler takes each first touch:
 * a read inside the buffer is counted under the instruction that made it (RIP, the offset read,
 * the trophy check of the match it came in); then one single step and the guard goes back on. A
 * touch of the same pages outside the buffer only re-arms. Reported at each trophy check and each
 * day. Read-only: nothing the game does is changed. Off after 4 million touches. */
#define GT_MAX 160
#define GT_RANGES 8
typedef struct { volatile LONG64 rip; volatile LONG n; volatile LONG off_lo, off_hi; volatile LONG ph_first, ph_last; volatile LONG range; } gt_rec_t;
static gt_rec_t g_gt[GT_MAX];
static volatile LONG g_gt_n = 0, g_gt_touch = 0, g_gt_phase = 0, g_gt_off = 0;
static uintptr_t g_gt_lo[GT_RANGES], g_gt_hi[GT_RANGES], g_gt_plo[GT_RANGES], g_gt_phi[GT_RANGES];
static char g_gt_tag[GT_RANGES][24];
static volatile LONG g_gt_nr = 0;
static PVOID g_gt_veh = 0;
static DWORD g_gt_tls = TLS_OUT_OF_INDEXES;   /* per thread: a re-arm is due after the single step */
static void gt_arm(void)
{
  DWORD old;
  if (g_gt_off) return;
  MEMORY_BASIC_INFORMATION mi;
  for (int r = 0; r < g_gt_nr; r++)
    for (uintptr_t a = g_gt_plo[r]; a < g_gt_phi[r]; a += 0x1000) {
      if (!VirtualQuery((void*)a, &mi, sizeof mi) || mi.State != MEM_COMMIT) continue;
      if (mi.Protect & PAGE_GUARD) continue;
      VirtualProtect((void*)a, 0x1000, (mi.Protect & 0xff) | PAGE_GUARD, &old);
    }
}
static LONG CALLBACK gt_handler(EXCEPTION_POINTERS* e)
{
  DWORD code = e->ExceptionRecord->ExceptionCode;
  if (code == 0x80000001u /* STATUS_GUARD_PAGE_VIOLATION */ && e->ExceptionRecord->NumberParameters >= 2) {
    uintptr_t a = (uintptr_t)e->ExceptionRecord->ExceptionInformation[1];
    int ours = 0, rr = -1;
    for (int r = 0; r < g_gt_nr; r++) {
      if (a >= g_gt_plo[r] && a < g_gt_phi[r]) ours = 1;
      if (a >= g_gt_lo[r] && a < g_gt_hi[r]) { rr = r; break; }
    }
    if (!ours) return EXCEPTION_CONTINUE_SEARCH;
    if (InterlockedIncrement(&g_gt_touch) > 300000) g_gt_off = 1;
    if (rr >= 0) {
      LONG64 rip = (LONG64)e->ContextRecord->Rip;
      LONG off = (LONG)(a - g_gt_lo[rr]), ph = g_gt_phase;
      int i, n = g_gt_n;
      for (i = 0; i < n && !(g_gt[i].rip == rip && g_gt[i].range == rr); i++) ;
      if (i == n && n < GT_MAX) {
        if (InterlockedCompareExchange64(&g_gt[n].rip, rip, 0) == 0) {
          g_gt[n].off_lo = off; g_gt[n].off_hi = off; g_gt[n].ph_first = ph; g_gt[n].range = rr; InterlockedIncrement(&g_gt_n);
        }
        i = n;
      }
      if (i < GT_MAX && g_gt[i].rip == rip) {
        InterlockedIncrement(&g_gt[i].n);
        if (off < g_gt[i].off_lo) g_gt[i].off_lo = off;
        if (off > g_gt[i].off_hi) g_gt[i].off_hi = off;
        g_gt[i].ph_last = ph;
      }
    }
    if (!g_gt_off) { e->ContextRecord->EFlags |= 0x100; TlsSetValue(g_gt_tls, (LPVOID)1); }
    return EXCEPTION_CONTINUE_EXECUTION;
  }
  if (code == 0x80000004u /* STATUS_SINGLE_STEP */ && g_gt_tls != TLS_OUT_OF_INDEXES && TlsGetValue(g_gt_tls)) {
    TlsSetValue(g_gt_tls, 0);
    gt_arm();
    return EXCEPTION_CONTINUE_EXECUTION;
  }
  return EXCEPTION_CONTINUE_SEARCH;
}
static int g_gt_reported = 0;
static void gt_disarm(const char* why);
static int g_gt_day;
static void gt_report(const char* when)
{
  int n = g_gt_n;
  if (g_gt_nr && when && !strcmp(when, "day") && g_gt_day >= 0 && today() != g_gt_day) gt_disarm("the day after");
  if (n == g_gt_reported) return;
  for (int i = g_gt_reported; i < n; i++) {
    gt_rec_t* r = &g_gt[i];
    logf("fl26swiss: guard -- %s: %s: rip %llx (rva %#llx) x%ld, offsets %#lx..%#lx, checks %ld..%ld",
         when, g_gt_tag[r->range], (unsigned long long)r->rip, (unsigned long long)(r->rip - (LONG64)g_base), (long)r->n,
         (long)r->off_lo, (long)r->off_hi, (long)r->ph_first, (long)r->ph_last);
  }
  logf("fl26swiss: guard -- %s: %d reader(s) so far, %ld touch(es)%s", when, n, (long)g_gt_touch, g_gt_off ? ", off" : "");
  g_gt_reported = n;
}
static int g_gt_day = -9;
static void gt_disarm(const char* why)
{
  if (!g_gt_nr) return;
  g_gt_off = 1;
  DWORD old; MEMORY_BASIC_INFORMATION mi;
  for (int r = 0; r < g_gt_nr; r++)
    for (uintptr_t a = g_gt_plo[r]; a < g_gt_phi[r]; a += 0x1000)
      if (VirtualQuery((void*)a, &mi, sizeof mi) && mi.State == MEM_COMMIT && (mi.Protect & PAGE_GUARD))
        VirtualProtect((void*)a, 0x1000, mi.Protect & ~PAGE_GUARD, &old);
  logf("fl26swiss: guard -- off (%s)", why);
  g_gt_nr = 0;
}
static void gt_pm_off(void)
{
  if (g_gt_nr) { gt_report("post-match"); gt_disarm("post-match"); g_gt_pm_done = 1; }
}
/* add a watched range (up to GT_RANGES); 1 ok */
static int gt_add(uint64_t addr, uint32_t len, const char* tag)
{
  if (!addr || !len || len > 0x400000) return 0;
  if (g_gt_tls == TLS_OUT_OF_INDEXES) g_gt_tls = TlsAlloc();
  if (g_gt_tls == TLS_OUT_OF_INDEXES) return -2;
  if (!g_gt_veh) g_gt_veh = AddVectoredExceptionHandler(1, gt_handler);
  if (!g_gt_veh) return -1;
  if (g_gt_nr >= GT_RANGES) return -3;
  int r = g_gt_nr;
  g_gt_lo[r] = (uintptr_t)addr; g_gt_hi[r] = (uintptr_t)addr + len;
  g_gt_plo[r] = g_gt_lo[r] & ~(uintptr_t)0xfff; g_gt_phi[r] = (g_gt_hi[r] + 0xfff) & ~(uintptr_t)0xfff;
  snprintf(g_gt_tag[r], sizeof g_gt_tag[r], "%s", tag ? tag : "?");
  g_gt_nr = r + 1;
  g_gt_off = 0; g_gt_day = today();
  logf("fl26swiss: guard -- %s at %llx, %u byte(s): watched", g_gt_tag[r], (unsigned long long)addr, len);
  gt_arm();
  return 1;
}
__declspec(dllexport) int fl26_swiss_guard(uint64_t addr, uint32_t len, const char* tag)
{
  return 0;   /* 31.10.: the raw table is only read at load; the decoded one is watched instead (cer_guard_end) */
}
/* 31.10. (second rastreo): the end-scene table decoded (0x141f40c00, table type 7) is kept by the demo
   manager (0x140a7cc00()): +0x168+7*0x20 {category pairs, names, count, entries of 0x78},
   +0x8+7*0x20 {cut pairs, cut names, count, cuts of 0x38}. At a final's setup they are watched:
   whoever reads them at full time is the code that picks the end scene. */
#define CER_GUARD 0
typedef unsigned char* (*demomgr_fn)(void);
static void cer_guard_end(int d)
{
  if (!CER_GUARD) return;   /* 31.10.: session 002 found no reader of the decoded table; off */
  /* 31.10. (second try): at the first trophy check (the setup, before the match loads) the manager
     still holds the previous decoded table; the load frees it and reuses the memory, and guarded
     pages there hung the load (a file read into a guarded page fails). Now: the first check of the
     day only resets; from the second (the match loaded) the current pointers are watched, re-read
     at every check; off after the post-match (postmatch_end) and the day after. */
  static int day = -9;
  static uint64_t armed[5], stale_ce;
  if (day != d) {
    day = d;
    if (g_gt_nr) gt_disarm("a new final");
    g_gt_n = 0; g_gt_reported = 0; g_gt_touch = 0; g_gt_phase = 0;
    memset((void*)g_gt, 0, sizeof g_gt);
    memset(armed, 0, sizeof armed);
    g_gt_pm_done = 0;
    unsigned char* m0 = ((demomgr_fn)(uintptr_t)(g_base + 0xa7cc00))();
    stale_ce = m0 ? *(uint64_t*)(m0 + 0x168 + 7 * 0x20 + 0x18) : 0;
    logf("fl26swiss: guard -- setup: the end table before the load at %llx (not watched)", (unsigned long long)stale_ce);
    return;
  }
  if (g_gt_phase < 1 || g_gt_pm_done) return;
  unsigned char* mgr = ((demomgr_fn)(uintptr_t)(g_base + 0xa7cc00))();
  if (!mgr) { logf("fl26swiss: guard -- no demo manager"); return; }
  if (*(uint64_t*)(mgr + 0x168 + 7 * 0x20 + 0x18) == stale_ce) {   /* not reloaded yet: never guard memory the load frees */
    logf("fl26swiss: guard -- check %ld: the end table not reloaded yet, not watched", (long)g_gt_phase);
    return;
  }
  unsigned char* c = mgr + 0x168 + 7 * 0x20;
  unsigned char* k = mgr + 0x8 + 7 * 0x20;
  uint64_t cp = *(uint64_t*)c, cn = *(uint64_t*)(c + 8), ce = *(uint64_t*)(c + 0x18);
  uint32_t cc = *(uint32_t*)(c + 0x10);
  uint64_t kp = *(uint64_t*)k, kn = *(uint64_t*)(k + 8), ko = *(uint64_t*)(k + 0x18);
  uint32_t kc = *(uint32_t*)(k + 0x10);
  if (armed[0] == cp && armed[1] == cn && armed[2] == ce && armed[3] == kp && armed[4] == ko && g_gt_nr) return;
  if (g_gt_nr) gt_disarm("the table moved");
  armed[0] = cp; armed[1] = cn; armed[2] = ce; armed[3] = kp; armed[4] = ko;
  logf("fl26swiss: guard -- end table: categories %u (pairs %llx, names %llx, entries %llx), cuts %u (pairs %llx, names %llx, cuts %llx)",
       cc, (unsigned long long)cp, (unsigned long long)cn, (unsigned long long)ce, kc, (unsigned long long)kp,
       (unsigned long long)kn, (unsigned long long)ko);
  if (cc && cc < 4096) {
    gt_add(cp, cc * 4, "end category pairs");
    gt_add(cn, cc * 8, "end category names");
    gt_add(ce, cc * 0x78, "end entries");
  }
  if (kc && kc < 65536) {
    gt_add(kp, kc * 4, "end cut pairs");
    gt_add(ko, kc * 0x38, "end cuts");
  }
}

/* 31.10. (the end scenes, read-only): fl26swiss.lua calls this when the game asks for a full-time
   scene file (fixdemo\end\cut_data or fixdemo\timeup\cut_data): the calling thread's stack, each
   frame as module+offset (the exe's as its RVA). If the request is made by the code that chose the
   scene, the Libertadores final's (end) and ours (timeup) part at the choice. */
__declspec(dllexport) int fl26_swiss_stack(const char* tag)
{
  static int n = 0;
  if (!CER_STACKS) return 0;   /* 31.10.: sessions 004-009 found no requester (loader and job threads); off */
  if (n >= 60) return 0;
  n++;
  void* fr[62];
  USHORT k = RtlCaptureStackBackTrace(0, 62, fr, NULL);
  char line[2000]; int o = 0;
  o += snprintf(line + o, sizeof line - o, "fl26swiss: stack -- %s (tid %lu):", tag ? tag : "?", (unsigned long)GetCurrentThreadId());
  for (USHORT i = 0; i < k && o < (int)sizeof line - 40; i++) {
    uint64_t a = (uint64_t)(uintptr_t)fr[i];
    HMODULE mod = NULL;
    if (a >= g_base && a < g_base + 0x20000000ull) { o += snprintf(line + o, sizeof line - o, " %llx", (unsigned long long)(a - g_base + 0x140000000ull)); continue; }
    if (GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT, (LPCSTR)fr[i], &mod) && mod) {
      char nm[MAX_PATH]; DWORD L = GetModuleFileNameA(mod, nm, sizeof nm);
      const char* b = nm; for (DWORD j = 0; j < L; j++) if (nm[j] == '\\' || nm[j] == '/') b = nm + j + 1;
      o += snprintf(line + o, sizeof line - o, " %.12s+%llx", b, (unsigned long long)(a - (uint64_t)(uintptr_t)mod));
    } else o += snprintf(line + o, sizeof line - o, " ?%llx", (unsigned long long)a);
  }
  for (int p = 0; p < o; p += 200) logf("%.200s%s", line + p, p + 200 < o ? " ..." : "");
  /* 31.10. (session 004): the unwinder stops in Sider's trampoline (no unwind data), so no game
     frame came out. The raw stack instead: every qword between here and the end of the stack's
     committed region (VirtualQuery) that falls in one of the exe's executable sections, with its
     offset from here. Nothing of the exe is read at run time (sessions 005 and 006 crashed reading
     the call bytes); which of them are return addresses is checked offline against the exe file. */
  {
    static uint64_t xlo[16], xhi[16]; static int nx = -1;
    if (nx < 0) {
      nx = 0;
      IMAGE_DOS_HEADER* dh = (IMAGE_DOS_HEADER*)(uintptr_t)g_base;
      IMAGE_NT_HEADERS64* nh = (IMAGE_NT_HEADERS64*)((unsigned char*)dh + dh->e_lfanew);
      IMAGE_SECTION_HEADER* sec = IMAGE_FIRST_SECTION(nh);
      for (int i2 = 0; i2 < nh->FileHeader.NumberOfSections && nx < 16; i2++)
        if (sec[i2].Characteristics & IMAGE_SCN_MEM_EXECUTE) {
          xlo[nx] = g_base + sec[i2].VirtualAddress; xhi[nx] = g_base + sec[i2].VirtualAddress + sec[i2].Misc.VirtualSize; nx++;
        }
    }
    volatile uint64_t here = 0;
    uint64_t* sp = (uint64_t*)&here;
    MEMORY_BASIC_INFORMATION mi;
    uint64_t* top = sp;
    if (VirtualQuery((void*)sp, &mi, sizeof mi) && mi.State == MEM_COMMIT)
      top = (uint64_t*)((char*)mi.BaseAddress + mi.RegionSize);
    if ((char*)top - (char*)sp > 0x10000) top = (uint64_t*)((char*)sp + 0x10000);
    int nr = 0; o = 0;
    o += snprintf(line + o, sizeof line - o, "fl26swiss: stack -- raw:");
    for (uint64_t* q = sp; q < top && nr < 64 && o < (int)sizeof line - 40; q++) {
      uint64_t a = *q; int in = 0;
      for (int i2 = 0; i2 < nx && !in; i2++) in = a >= xlo[i2] && a < xhi[i2];
      if (!in) continue;
      o += snprintf(line + o, sizeof line - o, " %llx@%x", (unsigned long long)(a - g_base + 0x140000000ull),
                    (unsigned)((char*)q - (char*)sp));
      nr++;
    }
    for (int p = 0; p < o; p += 200) logf("%.200s%s", line + p, p + 200 < o ? " ..." : "");
    /* 31.10. (session 009): the file request comes from the loader thread; the scene was asked for
       by the match thread. That thread (the one that ran the match setup) is suspended for a
       moment, its registers and up to 64 KiB of its stack copied, and resumed; nothing is logged
       while it is stopped. Its stack's exe values are logged like ours. */
    DWORD mt = g_match_tid;
    if (mt && mt != GetCurrentThreadId()) {
      static unsigned char copy[0x10000];
      HANDLE th = OpenThread(THREAD_SUSPEND_RESUME | THREAD_GET_CONTEXT | THREAD_QUERY_INFORMATION, FALSE, mt);
      if (th) {
        CONTEXT cx; memset(&cx, 0, sizeof cx); cx.ContextFlags = CONTEXT_CONTROL | CONTEXT_INTEGER;
        size_t got = 0; uint64_t rip = 0, rsp = 0;
        if (SuspendThread(th) != (DWORD)-1) {
          if (GetThreadContext(th, &cx)) {
            rip = cx.Rip; rsp = cx.Rsp;
            MEMORY_BASIC_INFORMATION mi2;
            if (VirtualQuery((void*)(uintptr_t)rsp, &mi2, sizeof mi2) && mi2.State == MEM_COMMIT) {
              uint64_t end = (uint64_t)(uintptr_t)mi2.BaseAddress + mi2.RegionSize;
              got = (size_t)(end - rsp); if (got > sizeof copy) got = sizeof copy;
              memcpy(copy, (void*)(uintptr_t)rsp, got);
            }
          }
          ResumeThread(th);
        }
        CloseHandle(th);
        o = 0;
        o += snprintf(line + o, sizeof line - o, "fl26swiss: stack -- match thread %lu: rip %llx, stack:", (unsigned long)mt,
                      (unsigned long long)(rip >= g_base && rip < g_base + 0x20000000ull ? rip - g_base + 0x140000000ull : rip));
        int nr2 = 0;
        for (size_t q = 0; q + 8 <= got && nr2 < 72 && o < (int)sizeof line - 40; q += 8) {
          uint64_t a = *(uint64_t*)(copy + q); int in = 0;
          for (int i2 = 0; i2 < nx && !in; i2++) in = a >= xlo[i2] && a < xhi[i2];
          if (!in) continue;
          o += snprintf(line + o, sizeof line - o, " %llx@%x", (unsigned long long)(a - g_base + 0x140000000ull), (unsigned)q);
          nr2++;
        }
        for (int p = 0; p < o; p += 200) logf("%.200s%s", line + p, p + 200 < o ? " ..." : "");
      }
    }
  }
  return n;
}

/* 31.10. (session 007): the demo dispatcher. 0x141f577b0(this, request) starts each scene of a
   match; the request's byte +4 is the scene table (1 ent, 2 foul, 3 goal, 4 pk, 5 change, 6 timeup,
   7 end, 8 result, 9 mode -- the registration at 0x141f33680). The Libertadores final asks for 7 at
   full time (end_timeup_*, end_joy_*, end_trophy_*), ours for 6 (tu_full_*). Every request is
   logged (bytes 0..15); on a final of ours, the full-time request (a 6 more than a minute after the
   first 6 of the match, the half time's) becomes a 7: the game's own end scenes, whose winner the
   game itself picks. */
#define DEMO_HOOK 0
#define DEMO_RVA  0x1f577b0
#define DEMO_BACK 0x1f577b7
static void demo_req(unsigned char* self, unsigned char* req)
{
  static int day = -9, nlog = 0; static ULONGLONG t6 = 0; static int conv = 0;
  int d = today();
  if (d != day) { day = d; nlog = 0; t6 = 0; conv = 0; }
  if (!req) return;
  unsigned char* m = match_block_now();
  int ours = g_cer_hit_day >= 0 && g_cer_hit_day == d;
  ULONGLONG now = GetTickCount64();
  if (nlog < 200) {
    nlog++;
    logf("fl26swiss: demo -- request type %u (+0 %02x +5 %02x +6 %02x +7 %02x; %02x%02x%02x%02x %02x%02x%02x%02x) day %d, ours %d, m+496 %#x",
         req[4], req[0], req[5], req[6], req[7], req[8], req[9], req[10], req[11], req[12], req[13], req[14], req[15], d, ours,
         m ? m[0x496] : 0xff);
  }
  if (req[4] == 6) {
    if (!t6) t6 = now;
    else if (ours && CER_END && now - t6 > 60000 && m && (m[0x496] & 0x40)) {   /* +0x496 bit 0x40: on after the half time in ours (sessions 002-004) */
      logf("fl26swiss: demo -- a final of ours (reg %u), full time: the plain full-time scene (6) becomes the end scenes (7)", (unsigned)g_cer_reg);
      req[4] = 7; conv++;
    }
  }
}
static int demo_install(uint64_t exe_base)
{
  unsigned char* s = (unsigned char*)(uintptr_t)(exe_base + DEMO_RVA);
  static const unsigned char sig[11] = { 0x48, 0x83, 0xec, 0x38, 0x4c, 0x8b, 0xca, 0x0f, 0xb6, 0x52, 0x04 };
  if (memcmp(s, sig, sizeof sig)) return 2;
  unsigned char* t = near_alloc(exe_base);
  if (!t) return 3;
  unsigned char* p = t;
  /* push rcx; push rdx; push r8; push r9 (rsp 8 mod 16 at the entry, still 8); sub rsp,0x28 (0 mod 16) */
  *p++ = 0x51; *p++ = 0x52; *p++ = 0x41; *p++ = 0x50; *p++ = 0x41; *p++ = 0x51;
  *p++ = 0x48; *p++ = 0x83; *p++ = 0xec; *p++ = 0x28;
  *p++ = 0x48; *p++ = 0xb8; *(uint64_t*)p = (uint64_t)(uintptr_t)demo_req; p += 8;   /* rcx, rdx: this, request */
  *p++ = 0xff; *p++ = 0xd0;
  *p++ = 0x48; *p++ = 0x83; *p++ = 0xc4; *p++ = 0x28;
  *p++ = 0x41; *p++ = 0x59; *p++ = 0x41; *p++ = 0x58; *p++ = 0x5a; *p++ = 0x59;
  memcpy(p, sig, 7); p += 7;                                   /* sub rsp,0x38; mov r9,rdx */
  *p++ = 0xff; *p++ = 0x25; *(uint32_t*)p = 0; p += 4; *(uint64_t*)p = exe_base + DEMO_BACK; p += 8;
  FlushInstructionCache(GetCurrentProcess(), t, (SIZE_T)(p - t));
  DWORD old;
  if (!VirtualProtect(s, 7, PAGE_EXECUTE_READWRITE, &old)) return 4;
  s[0] = 0xe9; *(int32_t*)(s + 1) = (int32_t)((int64_t)(uintptr_t)t - (int64_t)(uintptr_t)(s + 5));
  s[5] = 0x90; s[6] = 0x90;
  VirtualProtect(s, 7, old, &old);
  FlushInstructionCache(GetCurrentProcess(), s, 7);
  return 0;
}

/* 31.10. (session 011, Felix's borrowed ids): the exe's regulation -> tournament map. 0x141e53910
   (cx = regulation | stage << 10) looks the key up in a list of 330 built-in pairs (reg 10 -> 26 the
   Libertadores final, 6 -> 21 the Europa League final, 13 -> 30, ...) and answers 0xd9 (217, "no
   tournament") for anything else -- every regulation of ours. Here a final of ours answers a final
   tournament of the base game that this world does not use: 30 (regulation 13, the shipped Copa
   Sudamericana's final; FL26's Sudamericana is a cup of its own, 257/258), kind 10 like the
   Libertadores' 26, trophy 27. Nothing of the world is renumbered; only the game's question
   "which tournament is this regulation" gets another answer. Callers logged (first 120). */
#define TMAP_HOOK 1
#define TMAP_RVA  0x1e53910
#define TMAP_TID  30
static volatile LONG g_tmap_n = 0;
static uint32_t tmap_handler(uint32_t key, uint64_t ret)
{
  /* 31.10. (Felix: the Final del FUTVE is two legs): its first leg decides nothing -- the user's
     match today, 263 on leg 0, keeps "no tournament" (217), so only the second leg ends in the
     ceremony. The leg is the match record's (+7 bits 4-5), as ceremony_fix reads it. */
  if ((key & 0x3ff) == 263) {
    int d = today();
    unsigned char* o = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
    unsigned char* blk = o ? *(unsigned char**)(o + 0x48) : 0;
    if (blk && d >= 0 && d < 365) {
      unsigned char* e = blk + SCHED_ENT_OFF + (size_t)d * 16;
      unsigned char* mr = *(uint16_t*)e != 0xffff ? ko_match(*(uint16_t*)e) : 0;
      if (mr && *(uint16_t*)(mr + 4) == 263 && ((mr[7] >> 4) & 3) == 0) {
        if (InterlockedIncrement(&g_tmap_n) <= 120)
          logf("fl26swiss: tmap -- regulation 263, first leg (day %d): no tournament (217), no ceremony", d);
        return 0xd9;
      }
    }
  }
  if (InterlockedIncrement(&g_tmap_n) <= 120)
    logf("fl26swiss: tmap -- regulation %u (stage %u) asked by %llx: tournament %u", key & 0x3ff, (key >> 10) & 0x3f,
         (unsigned long long)(ret - g_base + 0x140000000ull), (unsigned)TMAP_TID);
  return TMAP_TID;
}
static int tmap_install(uint64_t exe_base)
{
  unsigned char* s = (unsigned char*)(uintptr_t)(exe_base + TMAP_RVA);
  static const unsigned char sig[5] = { 0x48, 0x89, 0x5c, 0x24, 0x08 };
  if (memcmp(s, sig, 5) || s[5] != 0x48 || s[6] != 0x89 || s[7] != 0x74) return 2;
  unsigned char* t = near_alloc(exe_base);
  if (!t) return 3;
  unsigned char* p = t;
  /* movzx eax, cx; and eax, 0x3ff; cmp eax, 255/256/261/262/263 -> ours */
  *p++ = 0x0f; *p++ = 0xb7; *p++ = 0xc1;
  *p++ = 0x25; *(uint32_t*)p = 0x3ff; p += 4;
  static const uint32_t ours[] = { 255, 256, 261, 262, 263 };
  unsigned char* jmps[5];
  for (int i = 0; i < 5; i++) {
    *p++ = 0x3d; *(uint32_t*)p = ours[i]; p += 4;          /* cmp eax, imm32 */
    *p++ = 0x74; jmps[i] = p; *p++ = 0;                    /* je ours */
  }
  /* not ours: the displaced mov [rsp+8],rbx, back to +5 */
  memcpy(p, sig, 5); p += 5;
  *p++ = 0xff; *p++ = 0x25; *(uint32_t*)p = 0; p += 4; *(uint64_t*)p = exe_base + TMAP_RVA + 5; p += 8;
  unsigned char* o = p;
  for (int i = 0; i < 5; i++) *jmps[i] = (unsigned char)(o - (jmps[i] + 1));
  /* ours: sub rsp,0x28; mov rdx,[rsp+0x28]; (ecx = key) call handler; add rsp,0x28; ret */
  *p++ = 0x48; *p++ = 0x83; *p++ = 0xec; *p++ = 0x28;
  *p++ = 0x48; *p++ = 0x8b; *p++ = 0x54; *p++ = 0x24; *p++ = 0x28;
  *p++ = 0x0f; *p++ = 0xb7; *p++ = 0xc9;                    /* movzx ecx, cx */
  *p++ = 0x48; *p++ = 0xb8; *(uint64_t*)p = (uint64_t)(uintptr_t)tmap_handler; p += 8;
  *p++ = 0xff; *p++ = 0xd0;
  *p++ = 0x48; *p++ = 0x83; *p++ = 0xc4; *p++ = 0x28;
  *p++ = 0xc3;
  FlushInstructionCache(GetCurrentProcess(), t, (SIZE_T)(p - t));
  DWORD old;
  if (!VirtualProtect(s, 5, PAGE_EXECUTE_READWRITE, &old)) return 4;
  s[0] = 0xe9; *(int32_t*)(s + 1) = (int32_t)((int64_t)(uintptr_t)t - (int64_t)(uintptr_t)(s + 5));
  VirtualProtect(s, 5, old, &old);
  FlushInstructionCache(GetCurrentProcess(), s, 5);
  return 0;
}

/* 30.10. (the trophy ceremony): read-only, once. Sider's hooks (trophy-check, trophy-table, ...)
   are code in the game that reaches sider.dll by an absolute address. Every such address in the
   game's executable sections is logged with its RVA, to read the game's code around the trophy
   check in the exe on disk. */
static void sider_site_scan(uint64_t exe_base)
{
  HMODULE sm = GetModuleHandleA("sider.dll");
  if (!sm) { logf("fl26swiss: sider sites -- sider.dll not loaded"); return; }
  IMAGE_DOS_HEADER* sd = (IMAGE_DOS_HEADER*)sm;
  IMAGE_NT_HEADERS64* sn = (IMAGE_NT_HEADERS64*)((unsigned char*)sm + sd->e_lfanew);
  uint64_t lo = (uint64_t)(uintptr_t)sm, hi = lo + sn->OptionalHeader.SizeOfImage;
  IMAGE_DOS_HEADER* dh = (IMAGE_DOS_HEADER*)(uintptr_t)exe_base;
  IMAGE_NT_HEADERS64* nh = (IMAGE_NT_HEADERS64*)((unsigned char*)dh + dh->e_lfanew);
  IMAGE_SECTION_HEADER* sec = IMAGE_FIRST_SECTION(nh);
  int hits = 0;
  logf("fl26swiss: sider sites -- sider.dll %llx..%llx", (unsigned long long)lo, (unsigned long long)hi);
  for (int i = 0; i < nh->FileHeader.NumberOfSections && hits < 80; i++) {
    if (!(sec[i].Characteristics & IMAGE_SCN_MEM_EXECUTE)) continue;
    unsigned char* b = (unsigned char*)(uintptr_t)(exe_base + sec[i].VirtualAddress);
    size_t n = sec[i].Misc.VirtualSize;
    MEMORY_BASIC_INFORMATION mi;
    for (size_t off = 0; off + 8 <= n && hits < 80; ) {
      if (!VirtualQuery(b + off, &mi, sizeof mi)) break;
      size_t end = (size_t)((unsigned char*)mi.BaseAddress + mi.RegionSize - b);
      if (end > n) end = n;
      int ok = mi.State == MEM_COMMIT && !(mi.Protect & (PAGE_NOACCESS | PAGE_GUARD));
      if (ok) for (size_t q = off; q + 8 <= end && hits < 80; q++) {
        uint64_t v = *(uint64_t*)(b + q);
        if (v < lo || v >= hi) continue;
        unsigned char* x = b + q;
        size_t from = q >= 24 ? q - 24 : 0;
        char hx[65]; tp_hex(b + from, hx);
        logf("fl26swiss: sider site rva %#llx -> sider+%#llx (bytes before %02x %02x; from rva %#llx: %s)",
             (unsigned long long)(exe_base + sec[i].VirtualAddress + q - exe_base), (unsigned long long)(v - lo),
             x[-2], x[-1], (unsigned long long)(sec[i].VirtualAddress + from), hx);
        hits++; q += 7;
      }
      off = end > off ? end : off + 0x1000;
    }
  }
  logf("fl26swiss: sider sites -- %d found", hits);
}

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
  if (!memcmp((void*)(uintptr_t)(exe_base + RIGHT_RVA), SIG_RIGHT, 15) &&
      !hook((unsigned char*)(uintptr_t)(exe_base + RIGHT_RVA), SIG_RIGHT, 15, (void*)right_handler, &g_tramp_right))
    logf("fl26swiss: automatic final of two cups live (rights@%llx): its winner is the club that won both feeding cups",
         (unsigned long long)(exe_base + RIGHT_RVA));
  else
    logf("fl26swiss: automatic final of two cups NOT installed (signature at rights@%llx)", (unsigned long long)(exe_base + RIGHT_RVA));
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
    int cr = cont_install(exe_base);
    if (!cr) logf("fl26swiss: board objective by continent live (18 calls of the owner's judges)");
    else logf("fl26swiss: board objective by continent NOT installed (%d)", cr);
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
  {
    int cr = ceremony_install(exe_base);
    if (cr) logf("fl26swiss: ceremony hook NOT installed (%d): the finals of ours keep no trophy ceremony", cr);
    else logf("fl26swiss: ceremony hook live at %llx: a final of ours is a cup's final for the trophy ceremony",
              (unsigned long long)(exe_base + CER_SITE_RVA));
  }
  {
    int tr = TMAP_HOOK ? tmap_install(exe_base) : -1;
    if (tr) logf("fl26swiss: tournament map hook NOT installed (%d)", tr);
    else logf("fl26swiss: tournament map hook live at %llx: our finals (255, 256, 261-263) answer tournament %d",
              (unsigned long long)(exe_base + TMAP_RVA), TMAP_TID);
  }
  {
    int dr = DEMO_HOOK ? demo_install(exe_base) : -1;   /* 31.10. (session 008): not the scene dispatcher; off */
    if (dr) logf("fl26swiss: demo dispatcher hook NOT installed (%d)", dr);
    else logf("fl26swiss: demo dispatcher hook live at %llx (full time of a final of ours -> end scenes)", (unsigned long long)(exe_base + DEMO_RVA));
  }
  {
    int pr = postmatch_install(exe_base);
    if (pr) logf("fl26swiss: post-match watch NOT installed (%d)", pr);
    else logf("fl26swiss: post-match watch live at %llx (read-only)", (unsigned long long)(exe_base + PM_SITE_RVA));
  }
  return 0;
}

/* copy and clear the pending log text; returns bytes copied */
__declspec(dllexport) int fl26_swiss_log(char* out, int cap)
{
  if (g_log_lost && g_log_len + 128 < (int)sizeof g_log) {
    uint32_t lost = g_log_lost; g_log_lost = 0;
    logf("fl26swiss: %u log line(s) lost before this point -- the log was full and not drained", (unsigned)lost);
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
