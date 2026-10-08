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

/* ---- small text log, drained by the Lua loader into sider.log ---- */
static char g_log[65536]; static volatile int g_log_len = 0;
static void logf(const char* fmt, ...)
{
  char line[256]; va_list ap; va_start(ap, fmt);
  int n = vsnprintf(line, sizeof line, fmt, ap); va_end(ap);
  if (n <= 0) return; if (n >= (int)sizeof line) n = sizeof line - 1;
  if (g_log_len + n + 1 >= (int)sizeof g_log) return;
  memcpy(g_log + g_log_len, line, n); g_log_len += n; g_log[g_log_len++] = '\n';
}

static int ours(uint16_t reg)
{
  for (int i = 0; i < g_nreg; i++) if (g_reg[i] == reg) return 1;
  return 0;
}

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
   competition 2 on any day). Both legs move 11 days later, to 241 and 248, still a week
   before the first league-phase matchday on 257. (Until 0.2.0 14 days, to 244 and 251: 251 is
   the national cups' first round (calendar case 6), and Slavia played Benfica and the Czech
   cup's first leg on the same day -- rwee 07.10.) */
#define PLAYOFF_SHIFT 11
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
static uint16_t phase_row(uint16_t id) { return id == 3 ? 1027 : id == 5 ? 1029 : id == UECL_REG ? UECL_ROW : 0xffff; }
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
static void cont_swap(uint16_t id, u32vec* list, const char* where);
static int cont_comp(uint16_t id);
static int today(void);
void gdraw_handler(uint64_t id, u32vec* list, uint64_t flag)
{
  uint16_t r = (uint16_t)id, row = phase_row(r);
  if (row == 0xffff) {
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
static uint16_t ko_row(uint16_t id) { return id == 4 ? 1027 : id == 6 ? 1029 : id == UECL_KO ? UECL_ROW : 0xffff; }
/* list positions -> table ranks (0-based).  If the knockout pairs neighbours, the ties are
   1-16, 8-9, 4-13, 5-12, 2-15, 7-10, 3-14, 6-11: the seeded half meets the unseeded half. */
static const int KO_ORDER[KO_N] = { 0, 15, 7, 8, 3, 12, 4, 11, 1, 14, 6, 9, 2, 13, 5, 10 };

static int cwc_world(void);
static char cwc_setcl(uint64_t id, u32vec* list, uint64_t flag);
static void cwc_game_champions(u32vec* list);
static uint32_t canon_club(uint32_t h);
static const char* club_note(uint32_t h, char* buf, size_t cap);
typedef struct split_s split_t;
static int split_part(uint16_t id, const split_t** out);
static int q_setcl(uint16_t r, uint64_t id, uint64_t flag, char* ok);
static void split_regular_clubs(uint16_t r, const split_t* s, u32vec* list);
char setcl_handler(uint64_t id, u32vec* list, uint64_t flag)
{
  uint16_t r = (uint16_t)id, row = ko_row(r);
  if (r == 1 && cwc_world()) return cwc_setcl(id, list, flag);
  if (r == 1 && list && list->b && list->e > list->b) cwc_game_champions(list);
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
  }
  size_t n = list && list->b ? (size_t)(list->e - list->b) : 0;
  if (r == 53 || r == 123)            /* GitHub #21: who fills the DFB-Pokal / Russian Cup, and with what */
    logf("fl26swiss: set_clubs cup reg %u -- %u club(s) on day %d, from %llx, first %08x last %08x", (unsigned)r,
         (unsigned)n, today(), (unsigned long long)((uintptr_t)__builtin_return_address(0) - g_base + 0x140000000ull),
         n ? list->b[0] : 0, n ? list->b[n - 1] : 0);
  if (row != 0xffff && n) {
    unsigned char* ph = get_rec(row);
    unsigned char* t = ph && rec_count(ph) >= FL26_SWISS_MIN_CLUBS ? ((table_fn)(uintptr_t)(g_base + TABLE_RVA))(row) : 0;
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

static void start_stage(void* started, uint16_t id)
{
  if (started) ((push16_fn)(uintptr_t)(g_base + PUSH16_RVA))(started, &id);
  char ok = ((start_fn)(uintptr_t)(g_base + START_RVA))(id);
  logf("fl26swiss: reg %u started (0x141590420 -> %d)", (unsigned)id, (int)ok);
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
static int uecl_fill(void* started)
{
  unsigned char* rec = get_rec(UECL_REG);
  if (!rec || !get_rec(UECL_ROW)) { logf("fl26swiss: no Conference League in this world (reg %u)", UECL_REG); return 0; }
  if (rec_count(get_rec(UECL_ROW))) { logf("fl26swiss: row %u already holds %u clubs; Conference League not filled again", UECL_ROW, rec_count(get_rec(UECL_ROW))); return 0; }
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

static int uecl_ko(void* started)
{
  unsigned char* ko = get_rec(UECL_KO);
  if (!ko) return 0;
  if (rec_count(ko)) return 0;
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
#ifndef TODAY_OFF   /* -DTODAY_OFF=... builds for a set that moves the block (the -calendar set) */
#define TODAY_OFF  0x1642a1c
#endif
#define WINNER_RVA 0x151b2e0
#define FREETAB_RVA 0x1363040   /* (this, u16 id): free a regulation's tie tables -- the July teardown's own step */
#define PO_MONTHS_BEFORE 180                 /* any day below this is the second half of a season */
typedef void* (*winner_fn)(uint32_t* out, uint64_t id);
typedef char (*freetab_fn)(void* self, uint64_t id);
static int g_po_enabled = 1;
static int today(void)
{
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
static int g_year_off = 0, g_last_day = -1;
static int abs_day(void)
{
  int d = today();
  if (d < 0) return d;
  if (g_last_day >= 0 && d + 182 < g_last_day) g_year_off += 365;
  else if (g_last_day >= 0 && d > g_last_day + 182 && g_year_off >= 365) g_year_off -= 365;
  g_last_day = d;
  return d + g_year_off;
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
  { 3,        1027,     2,       4,       { 47, 54 }, "Champions League" },    /* 17/24 Feb */
  { 5,        1029,     UEL_PO,  6,       { 49, 56 }, "Europa League" },       /* 19/26 Feb */
  { UECL_REG, UECL_ROW, UECL_PO, UECL_KO, { 49, 56 }, "Conference League" },
};
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
  unsigned char* ph = get_rec(c->row);
  unsigned char* t = ph && rec_count(ph) >= 24 ? ((table_fn)(uintptr_t)(g_base + TABLE_RVA))(c->row) : 0;
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
  start_stage(started, c->po);
  return 1;
}

static int po_finish(int ci, void* started)
{
  const cup_t* c = &CUPS[ci];
  unsigned char* ph = get_rec(c->row);
  unsigned char* t = ph && rec_count(ph) >= 24 ? ((table_fn)(uintptr_t)(g_base + TABLE_RVA))(c->row) : 0;
  uint32_t rows = t ? *(uint32_t*)(t + 0x3c0) : 0;
  if (rows < 24) {
    logf("fl26swiss: %s play-off ended but reg %u has no table (rows %u)", c->name, (unsigned)c->row, rows);
    return 0;
  }
  static uint32_t list[16]; int bad = 0;
  uint32_t w[8];
  for (int k = 0; k < 8; k++) {
    w[k] = 0;
    ((winner_fn)(uintptr_t)(g_base + WINNER_RVA))(&w[k], tie_id(c, k));
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
  u32vec v = { list, list + 16, list + 16 };
  ((setclr_fn)(uintptr_t)g_tramp_setcl)(c->ko, &v, 1);
  run_flush();
  unsigned char* ko = get_rec(c->ko);
  logf("fl26swiss: %s play-off over -- reg %u now %u clubs", c->name, (unsigned)c->ko, ko ? rec_count(ko) : 0);
  if (ko && rec_count(ko)) { start_stage(started, c->ko); return 1; }
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
static final_t g_final[64]; static int g_nfinal = 0;
static const char* COMP_NAME[3] = { "Champions League", "Europa League", "Conference League" };
#define RIGHT_RVA 0x15799e0   /* u32* (u32* out, u16 source, u32 right_type): 0 = winner, 13+n = position n+1 */
#define NOCLUB_RVA 0x351ae44  /* what it answers when nobody holds the right */
typedef uint32_t* (*right_fn)(uint32_t* out, uint64_t source, uint32_t type);
typedef struct { uint16_t reg; int day; uint32_t club; } cupwin_t;
static cupwin_t g_cupwin[32]; static int g_ncupwin = 0;

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
  for (int i = 0; i < g_ncupwin; i++) if (g_cupwin[i].reg == reg) return &g_cupwin[i];
  return 0;
}

static final_t* final_of(uint16_t reg)
{
  for (int i = 0; i < g_nfinal; i++) if (g_final[i].reg == reg) return &g_final[i];
  return 0;
}
#define BUILD_DAY 210   /* the day-216 rollover builds the new season; nothing after this is final */
/* a table in exactly the league's list order is one nobody has played yet */
static int unplayed(unsigned char* rec, unsigned char* t, uint32_t rows)
{
  int listed = rec_count(rec) == rows;
  for (uint32_t k = 0; k < rows && listed; k++) listed = *(uint32_t*)(t + k * 20) == rec_clubs(rec)[k];
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
  if (d >= BUILD_DAY || unplayed(rec, t, rows)) return -1;
  if (!f) { if (g_nfinal >= 64) return 0; f = &g_final[g_nfinal++]; f->reg = reg; }
  f->n = (uint16_t)rows; f->day = ad;
  for (uint32_t k = 0; k < rows; k++) f->club[k] = *(uint32_t*)(t + k * 20);
  return 1;
}
/* at the July teardown: every access league's final table, while it still exists */
static void access_capture(void)
{
  int got = 0, skipped = 0, d = today(), ad = abs_day();
  if (d < 140 || d > 230) return;                 /* the summer rollover only, not New Year's */
  for (size_t i = 0; i < g_naccess; i++) {
    uint16_t reg = g_access[i].reg;
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
}
/* a cup's winner: kept at the July teardown, else asked of the game now */
static uint32_t cup_winner(uint16_t reg)
{
  cupwin_t* w = cupwin_of(reg);
  int d = abs_day();
  if (w && d >= w->day && d - w->day < 120) return w->club;
  return winner_now(reg);
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
/* the league's clubs, strongest first; worked out once per summer */
static final_t* seed_of(uint16_t reg)
{
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
  if (f && rank <= f->n && d >= f->day && d - f->day < keep) { *from_table = 1; return f->club[rank - 1]; }
  *from_table = 0;
  final_t* s = seed_of(reg);
  if (s) return rank <= s->n ? s->club[rank - 1] : 0;
  unsigned char* rec = get_rec(reg);
  if (!rec || (unsigned)rank > rec_count(rec)) return 0;
  return rec_clubs(rec)[rank - 1];
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
static int g_new_career = 0, g_day_ticked = 0;
/* where each placed club came from, for the log: reg 0 = the first-season list */
typedef struct { uint16_t reg; uint8_t rank; } how_t;
static how_t g_how[3][FIELD];
static int any_final_kept(void)
{
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
 *   - the Champions League's play-off is the shipped regulation 2 (days 241 and 248, see
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
 *   - Days (QR_DAYS): the second qualifying round 220 and 225, the third 229 and 236, the
 *     play-offs 242 and 247 (the Champions League's 241 and 248), all on days no shipped
 *     competition plays, and three days clear of the national cups' first round (251; until
 *     0.2.0 243 and 250, 244 and 251, rwee 07.10.). The Europa and Conference League's second
 *     legs stay before the Champions League's, whose end builds the league phases. A round is filled on the days between the round before it and its first
 *     leg (q_fill); the season is built on day 216, so nothing is filled before 217.
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
/* each stage's two legs; the Champions League play-off's are reg 2's own (is_playoff) */
static const uint32_t QR_DAYS[3][2] = { { 242, 247 }, { 229, 236 }, { 220, 225 } };
static uint32_t g_q[NQR][Q_N]; static unsigned g_nq[NQR], g_nnew[NQR]; static int g_q_day = -100000, g_qmask = 0;
static how_t g_qhow[NQR][Q_N];
static unsigned char g_qdrawn[NQR];
static uint32_t g_qwin[NQR][Q_N / 2], g_qlose[NQR][Q_N / 2];
static how_t g_qwhow[NQR][Q_N / 2], g_qlhow[NQR][Q_N / 2];
#define QNAME(i) QCUPS[(i) % NQ].name, QSTAGE[(i) / NQ]
static uint16_t q_reg(int i) { return i < NQ ? QCUPS[i].reg : g_qreg[i]; }
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
static uint32_t q_first_leg(int i) { return i ? QR_DAYS[i / NQ][0] : 230 + PLAYOFF_SHIFT; }
static uint32_t q_fill_from(int mask, int i)
{
  uint32_t d = 0;
  for (int j = 0; j < NQR; j++)
    if (j != i && (mask >> j & 1) && (q_up(mask, j) == i || q_down(mask, j) == i) && QR_DAYS[j / NQ][1] + 1 > d)
      d = QR_DAYS[j / NQ][1] + 1;
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

/* build the lists; a slot whose club is missing or already placed takes the next position of the
   same league. q: 0 no qualifying (36 direct entrants each), 1 also the rounds' new entrants (g_q),
   2 the rounds' clubs are known (g_q) and are not placed again. mask: the rounds on (bit i); a
   competition's places past its direct entrants go to its own rounds when it has them */
static int access_build(int q, int mask)
{
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
  if (g_nfirst[0] + g_nfirst[1] + g_nfirst[2] && !any_final_kept() && !g_new_career) {
    static int said = 0;
    if (!said++) logf("fl26swiss: first-season list -- not a career built in this session; the list is left out");
  }
  /* A career built in this session takes the list in its first European summer. A January
     league's career has a final table of its own by then (2026-10-05: CSL, kept on day 176), so
     the final tables do not tell the first summer from a later one there: the day of the first
     use does -- every build within 120 days of it is the same summer. */
  static int first_day = -1;
  int first_summer = g_new_career && (first_day < 0 || abs_day() - first_day < 120);
  if (g_nfirst[0] + g_nfirst[1] + g_nfirst[2] && first_summer) {
    int missing = 0, twice = 0, over = 0;
    if (first_day < 0) first_day = abs_day();
    for (int k = 0; k < 3; k++)
      for (unsigned i = 0; i < g_nfirst[k]; i++) {
        uint32_t c = club_of_id(g_first[k][i]);
        if (!c) { missing++; logf("fl26swiss: first-season list -- team %u is not in any league of this game", g_first[k][i]); continue; }
        if (has_club(used, nused, c)) { twice++; continue; }
        if (g_nacc[k] >= cap[k]) { over++; continue; }
        g_how[k][g_nacc[k]].reg = 0; g_how[k][g_nacc[k]].rank = 0;
        g_acc[k][g_nacc[k]++] = c; used[nused++] = c; listed++;
      }
    logf("fl26swiss: first-season list -- %u / %u / %u clubs taken (%d not in this game, %d listed twice, %d over %d)",
         g_nacc[0], g_nacc[1], g_nacc[2], missing, twice, over, FIELD);
  }
  /* the round of competition p a new entrant goes to: the one nearest the league phase with room */
  #define QSLOT(p, out) do { out = -1; for (int s_ = 0; s_ < 3 && out < 0; s_++) { int i_ = (p) + NQ * s_; \
      if (on[i_] && g_nq[i_] < room[i_]) out = i_; } } while (0)
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
  int topped = 0;
  /* each competition, then its rounds from the play-off down: -1 - k is league phase k */
  static const int ORDER[NQ + NQR] = { -1, 0, 3, 6, -2, 1, 4, 7, -3, 2, 5, 8 };
  for (int o = 0; o < NQ + NQR; o++) {
    int k = ORDER[o] < 0 ? -1 - ORDER[o] : -1, qi = ORDER[o] >= 0 ? ORDER[o] : -1;
    uint32_t* L = qi < 0 ? g_acc[k] : g_q[qi];
    how_t* H = qi < 0 ? g_how[k] : g_qhow[qi];
    unsigned* N = qi < 0 ? &g_nacc[k] : &g_nq[qi];
    unsigned C = qi < 0 ? cap[k] : q == 1 && on[qi] ? room[qi] : 0;
    int rank[5] = { 1, 1, 1, 1, 1 }, done[5] = { 0 }, cnt[5] = { 0 };
    if (*N < C)
      for (unsigned i = 0; i < *N; i++)
        for (int j = 0; j < 5; j++)
          if (H[i].reg == RESERVE[j] || in_league(RESERVE[j], L[i])) { cnt[j]++; break; }
    while (*N < C && nused < sizeof used / sizeof used[0]) {
      int j = -1;
      for (int r = 0; r < 5; r++) if (!done[r] && (j < 0 || cnt[r] < cnt[j])) j = r;
      if (j < 0) break;
      uint32_t c = 0; int ft = 0;
      while (rank[j] <= FINAL_MAX) {
        c = access_club(RESERVE[j], rank[j]++, &ft);
        if (!c) break;
        if ((c >> 14) && !has_club(used, nused, c)) break;
        c = 0;
      }
      if (!c) { done[j] = 1; continue; }
      H[*N].reg = RESERVE[j]; H[*N].rank = (uint8_t)(rank[j] - 1);
      L[(*N)++] = c; used[nused++] = c; topped++; cnt[j]++;
    }
  }
  if (held) logf("fl26swiss: access -- %d league place(s) left by a title holder, given to the top-up", held);
  if (topped) logf("fl26swiss: access -- %d place(s) topped up from the big five", topped);
  char qs[96] = "";
  if (q == 1) {
    int n = snprintf(qs, sizeof qs, ", qualifying");
    for (int i = 0; i < NQR && n < (int)sizeof qs - 8; i++) if (on[i]) n += snprintf(qs + n, sizeof qs - n, " %u", g_nq[i]);
  } else if (q == 2) snprintf(qs, sizeof qs, " direct, the qualifying rounds' clubs left out");
  logf("fl26swiss: access -- %u / %u / %u clubs%s (%d from the first-season list, %d positions from last season's tables, %d from first-season order, %d missing)",
       g_nacc[0], g_nacc[1], g_nacc[2], qs, listed, tables, orders, gaps);
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
static int q_summer(void) { int d = today(); return d >= 180 && d < 257; }
/* set_clubs on reg 2 or one of its ties in the summer: ours instead of the game's. 1 = handled */
static int q_setcl(uint16_t r, uint64_t id, uint64_t flag, char* ok)
{
  if (!q_summer() || !q_world() || !(q_prepare() & 1)) return 0;
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
/* all three lists at once, so no club is given two places */
static void cont_build(void)
{
  uint32_t used[3 * CONT_MAX]; unsigned nused = 0;
  g_ncont[0] = g_ncont[1] = g_ncont[2] = 0;
  for (size_t i = 0; i < g_naccess; i++) {
    const access_t* a = &g_access[i];
    if (a->comp < LIB || a->comp > AFCL) continue;
    int k = a->comp - LIB, ft = 0; uint32_t c = 0;
    uint16_t reg = a->reg; int first = a->rank;
    if (!first) {                                   /* cup winner, or the alt league's next place */
      c = cup_winner(reg);
      if (c && has_club(used, nused, c)) c = 0;
      if (!c) { reg = a->alt; first = a->alt ? 1 : FINAL_MAX + 1; }
    }
    for (int rank = first; !c && rank <= FINAL_MAX; rank++) {
      c = access_club_kept(reg, rank, &ft, CONT_KEEP);
      if (!c) break;
      if (!(c >> 14) || has_club(used, nused, c)) c = 0;
    }
    if (!c || g_ncont[k] >= CONT_MAX || nused >= sizeof used / sizeof used[0]) continue;
    g_chow[k][g_ncont[k]].reg = a->reg; g_chow[k][g_ncont[k]].rank = a->rank;
    g_cont[k][g_ncont[k]++] = c; used[nused++] = c;
  }
}
/* a club's Master League slot (+0x41c), -1 when its record cannot be read */
static int club_slot(void* blk, uint32_t c)
{
  unsigned char* t = ((teamget_fn)(uintptr_t)(g_base + TEAMGET_RVA))(blk, c);
  if (!t || *(uint32_t*)t >> 14 != c >> 14) return -1;
  return t[0x41c] & 0x7f;
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
static uint16_t g_nat[128];                              /* slot -> country, 0 = not given */

/* pairs (slot, country) from the world file's league lines; returns how many were taken */
__declspec(dllexport) int fl26_swiss_nations(const uint16_t* v, int n)
{
  if (!v || n < 0) return -1;
  int k = 0;
  for (int i = 0; i < n; i++)
    if (v[2 * i] < 123 && v[2 * i + 1]) { g_nat[v[2 * i]] = v[2 * i + 1]; k++; }
  logf("fl26swiss: league-phase draw -- countries of %d league slot(s) from the world file", k);
  return k;
}

static int club_key(void* blk, uint32_t c, int i)
{
  unsigned char* t = ((teamget_fn)(uintptr_t)(g_base + TEAMGET_RVA))(blk, c);
  if (!t || *(uint32_t*)t >> 14 != c >> 14) return 2000 + i;
  int s = t[0x41c] & 0x7f;
  if (s < 123 && g_nat[s]) return g_nat[s];
  if (s < 123 && !memcmp((const void*)(g_base + NATION_RVA), NATION_SIG, sizeof NATION_SIG)) {
    uint32_t k = ((nation_fn)(uintptr_t)(g_base + NATION_RVA))((uint32_t)s) & 0xffff;
    if (k && k < 0xfffc) return (int)k;
  }
  int own = *(uint16_t*)(t + 0x418) & 0x1ff;
  if (own && own != 21) return own;
  return s < 123 ? 1000 + s : 2000 + i;
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
  for (unsigned j = 0; j < g_ncont[k]; j++) {
    uint32_t cand = g_cont[k][j]; int given = 0;
    for (unsigned q = 0; q < g_nmap[k] && !given; q++) given = same_club(g_mto[k][q], cand);
    if (!given && !has_club(list->b, n, cand)) need++;
  }
  if (!need || n < 2 || n > 64) return 0;
  int key[64]; uint8_t out[64];
  for (size_t i = 0; i < n; i++) {
    uint32_t c = list->b[i];
    int s = club_slot(blk, c);
    key[i] = s < 0 ? 1000 + (int)i : s;
    /* not a shipped club of a league: a pool club, one of ours, or one already given way */
    out[i] = !(c >> 14) || s == pool || has_club(g_cont[k], g_ncont[k], c) || cont_mapped(k, c);
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
  if (comp < 0 || !n || !cont_any(comp)) return;
  int k = comp - LIB, pool = comp == AFCL ? POOL_ASIA : POOL_LATAM;
  void* blk = cont_begin(k);
  if (!blk) return;
  /* The AFC field reaches set_clubs already drawn: the list is the groups one after another,
   * four clubs each (measured 2026-09-27, reg 15 = 1039 + 2063 + ... + 8207). Taking the pool
   * clubs in list order put our eight into the first three groups, so the whole field is walked
   * across the groups instead -- first pool club of every group, then the second, ... -- and
   * each group gets one of ours before any gets two. Everything else is walked in order. */
  size_t order[64], no = 0;
  int grouped = comp == AFCL && id == 15 && n % 4 == 0 && n <= 64;
  if (grouped) {
    for (size_t r = 0; r < 4; r++)
      for (size_t g = 0; g < n / 4; g++)
        for (size_t i = g * 4, seen = 0; i < g * 4 + 4; i++)
          if (club_slot(blk, list->b[i]) == pool && seen++ == r) { order[no++] = i; break; }
  } else {
    /* a club that already gave way (a stand-in of the qualifying round, below) gives way again
       in the lists handed over after the whole field */
    for (size_t i = 0; i < n && no < 64; i++)
      if (club_slot(blk, list->b[i]) == pool || cont_mapped(k, list->b[i])) order[no++] = i;
  }
  unsigned npool = 0, put = 0, left = 0, before = g_nmap[k];
  for (size_t q = 0; q < no; q++) {
    size_t i = order[q];
    uint32_t c = list->b[i];
    npool++;
    const how_t* h = 0;
    uint32_t to = cont_map_one(k, c, list->b, n, &h, id);
    if (!to) { left++; continue; }
    list->b[i] = to; put++;
    if (h) logf("fl26swiss:   %s: reg %u %s %u -> %08x, in place of pool club %08x", CONT_NAME[k],
                (unsigned)h->reg, h->rank ? "position" : "winner", (unsigned)h->rank, to, c);
  }
  if (comp == LIBQ && id < 1024) put += cont_standins(k, list, n, blk, pool, put, id);
  logf("fl26swiss: %s (reg %u, %s) -- day %d: %u clubs, %u from pool %d; %u put in (%u newly paired), %u pool clubs left; our places %u, paired %u",
       CONT_NAME[k], (unsigned)id, where, today(), (unsigned)n, npool, pool, put, g_nmap[k] - before, left, g_ncont[k], g_nmap[k]);
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
/* how many match records regulation reg has, played or not; -1 if the match table is not where it was */
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
    if (*(const uint16_t*)m != 0xffff && *(const uint16_t*)(m + 4) == reg) n++;
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
 * CONCACAF champion an American club's, not an African one's; without the line, as before. */
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
static void cwc_game_champions(u32vec* list)
{
  uint32_t cw[MAX_CCUP_FWD]; uint16_t cc[MAX_CCUP_FWD];
  int nw = ccup_champions(cw, MAX_CCUP_FWD, cc);
  size_t n = (size_t)(list->e - list->b);
  unsigned char* o = (unsigned char*)((owner_fn)(uintptr_t)(g_base + OWNER_RVA))();
  void* blk = o ? *(void**)(o + 0x48) : 0;
  static int said_year = -1;
  int y = abs_day() / 365;
  if (said_year != y && blk) {
    said_year = y;
    logf("fl26swiss: Club World Cup (the game's) -- day %d, %u club(s) offered, %d champion(s) of ours", today(),
         (unsigned)n, nw);
    for (size_t i = 0; i < n && i < 40; i++) {
      unsigned char* t = ((teamget_fn)(uintptr_t)(g_base + TEAMGET_RVA))(blk, list->b[i]);
      int ok = t && *(uint32_t*)t >> 14 == list->b[i] >> 14;
      logf("fl26swiss:   entrant %2u: %08x slot %d country %d", (unsigned)i, list->b[i], ok ? t[0x41c] & 0x7f : -1,
           ok ? *(uint16_t*)(t + 0x418) & 0x1ff : -1);
    }
  }
  if (!blk) return;
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
    if (at == n) { at = n - 1; how = "the last entrant, none of its confederation offered"; }
    logf("fl26swiss: Club World Cup (the game's) -- winner of cup %u %08x in place of %08x (%s)", (unsigned)cc[k], cw[k],
         list->b[at], how);
    list->b[at] = cw[k];
  }
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
 * Only those entries are held to ccup_taken; a super cup's winners play their own cups anyway. */
#define MAX_CCUP 16      /* 8 until 0.2.0: CONCACAF and OFC cups next to league and pre-season cups */
_Static_assert(MAX_CCUP == MAX_CCUP_FWD, "the Club World Cup sizes its list of champions by MAX_CCUP_FWD");
#define CCUP_MAX_GROUPS 8
#define CCUP_MAX_ENTRY 32
#define CCUP_MAX_DAYS 8
#define R_LIBGROUP 9
#define R_UCLKO    4
/* the options of fl26_swiss_ccup_opts: fill -- the calendar day the cup is filled on (0: with the
   Champions League play-off, late August); national -- its clubs may also be in another of these
   cups (a league cup's clubs play in the continental one too); days -- the knockout's own days in
   place of CCUP_KO_DAYS; clubs -- team ids invited by name, in place of the league positions */
typedef struct { uint16_t reg, ko, groups, n; uint16_t ereg[CCUP_MAX_ENTRY]; uint8_t erank[CCUP_MAX_ENTRY];
                 uint16_t ealt[CCUP_MAX_ENTRY];
                 uint8_t efrom[CCUP_MAX_ENTRY];   /* alt=: the first position of ealt to try */
                 uint16_t fill, national, nd, nc; uint16_t days[CCUP_MAX_DAYS]; uint32_t clubs[CCUP_MAX_ENTRY];
                 int filled_year; } ccup_t;
static ccup_t g_ccup[MAX_CCUP]; static int g_nccup = 0;
static uint32_t g_ccup_field[MAX_CCUP][CCUP_MAX_ENTRY]; static unsigned g_ccup_nf[MAX_CCUP];
static unsigned g_ccup_done[MAX_CCUP];
/* Midweek, the way UEFA plays (GitHub #70): a cup the league champions go to (the CAF Champions
   League) on the Tuesdays, the one below it -- no entry at position 1: the Confederation Cup,
   the AFC Champions League Two, the Sudamericana -- on the Wednesdays of the same weeks, as the
   Europa League takes the Champions League's: a league that feeds both keeps its Saturday three
   days clear of either (rest_dates), where a Thursday would leave it no day of the week at all.
   Weekdays on the big leagues' grid (case 5: Saturday is 261, so a Tuesday is d % 7 == 5).
   Groups late November to mid February, the knockout mid March to the final in mid May (the
   first pair is spare for a knockout of eight). They were the Mondays and Sundays. */
static const uint32_t CCUP_GROUP_DAYS[2][6] = { { 327, 334, 26, 33, 40, 47 }, { 328, 335, 27, 34, 41, 48 } };
static const uint32_t CCUP_KO_DAYS[2][7] = { { 75, 82, 96, 103, 117, 124, 138 }, { 76, 83, 97, 104, 118, 125, 139 } };

static uint16_t ccup_rep(const ccup_t* c, int g) { return (uint16_t)(c->reg + 1024 * (g + 1)); }
/* 0: a champions' cup (Tuesdays), 1: the cup below (Wednesdays) */
static int ccup_tier(const ccup_t* c)
{
  for (int e = 0; e < c->n && e < CCUP_MAX_ENTRY; e++) if (c->erank[e] == 1) return 0;
  return 1;
}
/* the j-th day of a cup's groups or knockout: the knockout's own days when the world file gives them */
static uint32_t ccup_day(const ccup_t* c, int ko, int j)
{
  if (ko && c->nd) return c->days[j < c->nd ? j : c->nd - 1];
  return ko ? CCUP_KO_DAYS[ccup_tier(c)][j] : CCUP_GROUP_DAYS[ccup_tier(c)][j];
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

__declspec(dllexport) int fl26_swiss_ccup(const uint16_t* v, int n)
{
  /* per cup: reg, ko, groups, entries, then (reg, position) per entry */
  if ((!v && n) || n < 0) return -1;
  g_nccup = 0;
  size_t p = 0;
  for (int i = 0; i < n && g_nccup < MAX_CCUP; i++) {
    ccup_t* c = &g_ccup[g_nccup];
    c->reg = v[p]; c->ko = v[p + 1]; c->groups = v[p + 2]; unsigned ne = v[p + 3]; p += 4;
    c->n = 0; c->fill = c->national = c->nd = c->nc = 0; c->filled_year = -1;
    memset(c->ealt, 0, sizeof c->ealt);
    memset(c->efrom, 0, sizeof c->efrom);
    for (unsigned e = 0; e < ne; e++, p += 2)
      if (c->n < CCUP_MAX_ENTRY) { c->ereg[c->n] = v[p]; c->erank[c->n] = (uint8_t)v[p + 1]; c->n++; }
    if (!c->groups) {
      c->reg = c->ko;
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
    got++;
  }
  if (got) logf("fl26swiss: %d cup winner place(s) with a league to fall back on", got);
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
#define LPRE_TIES 8
typedef struct { uint16_t reg, ko, fill, ties; uint16_t days[2]; uint16_t ereg[2 * LPRE_TIES];
                 uint8_t erank[2 * LPRE_TIES]; int filled_year; uint32_t club[2 * LPRE_TIES]; unsigned nclub; } lpre_t;
static lpre_t g_lpre[MAX_LPRE]; static int g_nlpre = 0;
static int season_ord(int d);
static uint16_t lpre_tie(const lpre_t* l, int k) { return (uint16_t)(l->reg + 1024 * (k + 1)); }
/* which pre-round a regulation belongs to (0-based; *tie -1 for the master), -1 none */
static int lpre_of(uint16_t id, int* tie)
{
  for (int i = 0; i < g_nlpre; i++) {
    if (id == g_lpre[i].reg) { *tie = -1; return i; }
    if (id > 1024 && (id & 0x3ff) == g_lpre[i].reg && (id >> 10) <= LPRE_TIES) { *tie = (id >> 10) - 1; return i; }
  }
  return -1;
}
static int lpre_world(const lpre_t* l) { return get_rec(l->reg) && get_rec(lpre_tie(l, LPRE_TIES - 1)); }
static int lpre_year(void) { return (abs_day() + 183) / 365; }          /* the season, as ccup_fill_days */
/* match records under the master and its ties; -1 when the match table cannot be read */
static int lpre_matches(const lpre_t* l)
{
  int m = ccup_matches(l->reg);
  if (m < 0) return -1;
  for (int k = 0; k < LPRE_TIES; k++) { int x = ccup_matches(lpre_tie(l, k)); if (x > 0) m += x; }
  return m;
}

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
    for (int j = 0; j < g_nccup; j++) if (g_ccup[j].ko == ko && !g_ccup[j].groups) k = j;
    if (g_nlpre >= MAX_LPRE || k < 0 || ne < 2 || ne > 2 * LPRE_TIES || ne % 2 || reg <= 2 || reg > 1023
        || !fill || fill > 365 || !d1 || d1 > 365 || !d2 || d2 > 365) {
      logf("fl26swiss: pre-round %u of cup %u (%u entries) -- not one this module can run; left out",
           (unsigned)reg, (unsigned)ko, ne);
      continue;
    }
    lpre_t* l = &g_lpre[g_nlpre++];
    memset(l, 0, sizeof *l);
    l->reg = reg; l->ko = ko; l->fill = fill; l->days[0] = d1; l->days[1] = d2;
    l->ties = (uint16_t)(ne / 2); l->filled_year = -1;
    for (unsigned j = 0; j < ne; j++) { l->ereg[j] = e[2 * j]; l->erank[j] = (uint8_t)e[2 * j + 1]; }
    int fed = 0;
    for (unsigned j = 0; j < g_ccup[k].n; j++) {
      int t;
      if (!g_ccup[k].erank[j] && lpre_of(g_ccup[k].ereg[j], &t) == g_nlpre - 1 && t >= 0 && t < l->ties) fed++;
    }
    logf("fl26swiss: pre-round %u from the world file: %u tie(s) for cup %u (%d of its places), filled from day %u, "
         "played on days %u and %u", (unsigned)reg, (unsigned)l->ties, (unsigned)ko, fed, (unsigned)fill,
         (unsigned)d1, (unsigned)d2);
  }
  return g_nlpre;
}

/* the clubs pre-round l has this season: the ones it was filled with in this session, else the
   ones its ties hold once this season's matches are there (a save loaded after the fill) */
static unsigned lpre_clubs(const lpre_t* l, uint32_t* out)
{
  if (l->filled_year == lpre_year() && l->nclub == 2u * l->ties) {
    memcpy(out, l->club, l->nclub * sizeof(uint32_t));
    return l->nclub;
  }
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
    uint32_t cl[2 * LPRE_TIES];
    unsigned n = lpre_clubs(&g_lpre[i], cl);
    if (has_club(cl, n, c)) return 1;
  }
  return 0;
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
/* on the days from its fill day to the eve of its first leg, once a season: the clubs, the ties,
   the master started and registered -- q_fill's steps */
static void lpre_fill(int i)
{
  lpre_t* l = &g_lpre[i];
  int d = today();
  if (d < 1) return;
  int s = season_ord(d), f = season_ord(l->fill), last = season_ord(l->days[0]) - 1, year = lpre_year();
  if (last < f) last = f + 7;
  if (s < f || s > last || l->filled_year == year) return;
  l->filled_year = year;
  l->nclub = 0;
  if (!lpre_world(l)) { logf("fl26swiss: pre-round %u -- its rows are not all in this world; left alone", (unsigned)l->reg); return; }
  int m = lpre_matches(l);
  if (m != 0) {
    if (m > 0) logf("fl26swiss: pre-round %u already has %d match record(s) this season; not filled again", (unsigned)l->reg, m);
    return;
  }
  unsigned n = 0;
  for (unsigned j = 0; j < 2u * l->ties; j++) {
    const char* how = ""; uint32_t club = 0;
    for (int rank = l->erank[j]; rank >= 1 && rank <= FINAL_MAX; rank++) {
      club = cwc_club(l->ereg[j], rank, &how);
      if (!club) break;
      if ((club >> 14) && !has_club(l->club, n, canon_club(club))) { club = canon_club(club); break; }
      club = 0;
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
  for (int k = 0; k < LPRE_TIES; k++)
    ((freetab_fn)(uintptr_t)(g_base + FREETAB_RVA))(0, lpre_tie(l, k));
  u32vec va = { l->club, l->club + n, l->club + n };
  ((setclr_fn)(uintptr_t)g_tramp_setcl)(l->reg, &va, 1);
  for (int k = 0; k < l->ties; k++) {
    u32vec v = { l->club + 2 * k, l->club + 2 * k + 2, l->club + 2 * k + 2 };
    ((setclr_fn)(uintptr_t)g_tramp_setcl)(lpre_tie(l, k), &v, 1);
  }
  run_flush();
  l->nclub = n;
  start_stage(0, l->reg);
  uint16_t id = l->reg;
  struct { uint16_t* b; uint16_t* e; uint16_t* c; } rv = { &id, &id + 1, &id + 1 };
  ((regall_fn)(uintptr_t)(g_base + REGALL_RVA))(0, &rv);
  run_flush();
  int mm = ccup_matches(l->reg), mt = 0;
  for (int k = 0; k < l->ties; k++) { int x = ccup_matches(lpre_tie(l, k)); if (x > 0) mt += x; }
  if (mm <= 0 && mt <= 0) {                         /* the ties are their own rows: register them too */
    uint16_t ties[LPRE_TIES];
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
static void lpre_fill_days(void) { for (int i = 0; i < g_nlpre; i++) lpre_fill(i); }

static int ccup_fill_one(int k, void* started)
{
  const ccup_t* c = &g_ccup[k];
  unsigned char* rec = get_rec(c->reg);
  if (!ccup_world(c)) { logf("fl26swiss: cup %u -- its rows are not all in this world; left alone", (unsigned)c->reg); return 0; }
  unsigned held = rec_count(rec);
  if (c->groups && (held || rec_count(get_rec(ccup_rep(c, 0))))) {
    logf("fl26swiss: cup %u already holds %u clubs; not filled again", (unsigned)c->reg, held);
    return 0;
  }
  unsigned n = 0, gaps = 0;
  uint16_t unplayed_phase = 0;
  g_ccup_nf[k] = 0;
  for (unsigned i = 0; i < c->n; i++) {
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
    if (!c->erank[i]) {                            /* a cup's winner: that one club or none */
      int tk;
      if (lpre_of(c->ereg[i], &tk) >= 0) club = lpre_winner(c->ereg[i], &how);
      else { club = cup_winner(c->ereg[i]); how = "cup winner"; }
      if (club && has_club(g_ccup_field[k], n, club)) club = 0;
      if (club && c->ealt[i] && ((!c->national && ccup_taken(club)) || lpre_has(c->ko, club))) club = 0;
      if (!club && c->ealt[i]) {                   /* its league's next club (alt=) */
        for (int rank = c->efrom[i] ? c->efrom[i] : 1; rank <= FINAL_MAX; rank++) {
          uint32_t a = cwc_club(c->ealt[i], rank, &how);
          if (!a) break;
          if ((a >> 14) && !has_club(g_ccup_field[k], n, a) && (c->national || !ccup_taken(a)) && !lpre_has(c->ko, a)) {
            club = a;
            logf("fl26swiss:   cup %u entry: reg %u's winner place goes to reg %u position %d", (unsigned)c->reg,
                 (unsigned)c->ereg[i], (unsigned)c->ealt[i], rank);
            break;
          }
        }
      }
      if (!club) logf("fl26swiss:   cup %u entry: reg %u has no winner to send", (unsigned)c->reg, (unsigned)c->ereg[i]);
    } else
    for (int rank = c->erank[i]; rank <= FINAL_MAX; rank++) {
      club = cwc_club(c->ereg[i], rank, &how);
      if (!club) break;
      if ((club >> 14) && !has_club(g_ccup_field[k], n, club) && (c->national || !ccup_taken(club))
          && !lpre_has(c->ko, club)) break;
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
  if (n != c->n) {
    logf("fl26swiss: cup %u -- only %u of %u clubs found; not started", (unsigned)c->reg, n, (unsigned)c->n);
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
        logf("fl26swiss: cup %u already holds this season's %u clubs; not filled again", (unsigned)c->reg, held);
        return 0;
      }
      logf("fl26swiss: cup %u still holds %u club(s) of an earlier season (%08x ...) -- filled anew",
           (unsigned)c->reg, held, rec_clubs(rec)[0]);
    }
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
    return 1;
  }
  u32vec v = { g_ccup_field[k], g_ccup_field[k] + n, g_ccup_field[k] + n };
  ((setcl_fn)(uintptr_t)(g_base + SETCL_RVA))(c->reg, &v, 1);
  run_flush();
  u32vec w = { g_ccup_field[k], g_ccup_field[k] + n, g_ccup_field[k] + n };
  ((gdraw_fn)(uintptr_t)(g_base + GDRAW_RVA))(c->reg, &w, 1);
  run_flush();
  char line[96]; int p = 0;
  uint16_t reps[CCUP_MAX_GROUPS];
  for (int g = 0; g < c->groups; g++) {
    reps[g] = ccup_rep(c, g);
    unsigned char* rg = get_rec(reps[g]);
    p += snprintf(line + p, sizeof line - p, " %c:%u", 'A' + g, rg ? rec_count(rg) : 0);
  }
  logf("fl26swiss: cup %u -- day %d: %u clubs drawn, groups%s", (unsigned)c->reg, today(), rec_count(rec), line);
  struct { uint16_t* b; uint16_t* e; uint16_t* c; } rv = { reps, reps + c->groups, reps + c->groups };
  ((regall_fn)(uintptr_t)(g_base + REGALL_RVA))(0, &rv);
  run_flush();
  logf("fl26swiss: cup %u -- groups %u..%u handed to register_all", (unsigned)c->reg, (unsigned)reps[0],
       (unsigned)reps[c->groups - 1]);
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
static void ccup_keep_winners(void)
{
  int d = today(), ad = abs_day();
  if (d < 140 || d > 230) return;
  for (int k = 0; k < g_nccup; k++)
    for (unsigned i = 0; i < g_ccup[k].n; i++) {
      uint16_t reg = g_ccup[k].ereg[i];
      int tk;
      if (g_ccup[k].erank[i] || lpre_of(reg, &tk) >= 0) continue;     /* a pre-round's tie: lpre_winner */
      cupwin_t* w = cupwin_of(reg);
      if (w && ad >= w->day && ad - w->day < 60) continue;
      uint32_t c = winner_now(reg);
      if (!c) continue;
      if (!w) { if (g_ncupwin >= 32) continue; w = &g_cupwin[g_ncupwin++]; w->reg = reg; }
      w->day = ad; w->club = c;
      logf("fl26swiss: cup reg %u won by %08x (day %d), kept for cup %u", (unsigned)reg, c, d, (unsigned)g_ccup[k].ko);
    }
  for (int k = 0; k < g_nccup; k++) {                 /* and the champions, for the Club World Cup */
    if (g_ccup[k].national || ccup_tier(&g_ccup[k])) continue;
    uint16_t reg = g_ccup[k].ko;
    cupwin_t* w = cupwin_of(reg);
    if (w && ad >= w->day && ad - w->day < 60) continue;
    uint32_t c = winner_now(reg);
    if (!c) continue;
    if (!w) { if (g_ncupwin >= 32) continue; w = &g_cupwin[g_ncupwin++]; w->reg = reg; }
    w->day = ad; w->club = c;
    logf("fl26swiss: cup %u won by %08x (day %d), kept for the Club World Cup", (unsigned)reg, c, d);
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
  for (int k = 0; k < g_nccup; k++) if (!g_ccup[k].fill) any |= ccup_fill_one(k, started);
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
  if (d < 1) return;
  for (int k = 0; k < g_nccup; k++) {
    ccup_t* c = &g_ccup[k];
    if (!c->fill) continue;
    int f = season_ord(c->fill), s = season_ord(d);
    int last = (c->nd && season_ord(c->days[0]) > f) ? season_ord(c->days[0]) - 1 : f + 7;   /* up to the eve of its first day */
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
    ccup_fill_one(k, started);
  }
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
  unsigned char* ko = get_rec(c->ko);
  if (!ko || rec_count(ko)) return 0;
  static uint32_t buf[2 * CCUP_MAX_GROUPS];
  int nk = 2 * c->groups;
  for (int i = 0; i < nk; i++) {
    /* first half: group 2j's winner v group 2j+1's runner-up; second half the other way round */
    int half = i >= c->groups, j = (i % c->groups) / 2, away = i & 1;
    int g = 2 * j + (half ? !away : away), place = away;
    unsigned char* t = ((table_fn)(uintptr_t)(g_base + TABLE_RVA))(ccup_rep(c, g));
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

static uint64_t ccup_dates(int k, int ko, uint16_t id, uint64_t reg, void* vec)
{
  uint64_t rv = ((date_fn)(uintptr_t)g_tramp_date)((reg & ~(uint64_t)0xffff) | (ko ? R_UCLKO : R_LIBGROUP), vec);
  vec_t* v = (vec_t*)vec;
  size_t have = (v->b && v->e >= v->b) ? (size_t)(v->e - v->b) / sizeof(date_t) : 0;
  date_t* r = (date_t*)v->b;
  const ccup_t* cc = &g_ccup[k];
  size_t want = ko ? (cc->nd ? cc->nd : 7) : 6;
  static unsigned said[MAX_CCUP];
  unsigned bit = ko ? 1 : 2;
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
  for (size_t i = 0; i < have; i++) {
    size_t j = ko ? (i + 1 == have ? want - 1 : i + (want - have)) : i * want / have;
    r[i].day = ccup_day(cc, ko, (int)j);
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
      }
      if (part > 1 && r > 175) ccup_fill_ahead(r, "the end of its phase", started);
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
  /* the two play-off hand-overs replace the game's own case, they do not follow it */
  /* The Conference League's six matchdays end in December, not January: its play-off is drawn
     then (and dated in February like the others) -- otherwise the game sends the top 16 straight
     to the round of 16, as it did on 2026-09-24. */
  int dec = today() >= 300;
  if (g_po_enabled && (po_season_half() || dec)) {
    for (int ci = 0; ci < 3; ci++) {
      const cup_t* c = &CUPS[ci];
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
  return 1;
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

/* the world's cups: n entries of reg, mode (0 off, 1 seeded, 2 random), k, then k league regs, the
   top division first; returns how many were taken */
__declspec(dllexport) int fl26_swiss_cupdraw(const uint16_t* v, int n)
{
  g_ncd = 0;
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
  for (int i = 0; i < nr; i++)
    for (int s = 0; s < ko_slots(rounds[i]); s++) {
      uint32_t* sl = ko_slot(rounds[i], s);
      int k0 = (sl[0] & KO_TBD) != KO_TBD, k1 = (sl[1] & KO_TBD) != KO_TBD;
      if (!k0 && !k1) continue;
      uint16_t* ids = (uint16_t*)(sl + 2);
      for (int l = 0; l < 2; l++) {               /* a tie already played: the cup is under way */
        if (ids[l] == 0xffff) continue;
        unsigned char* m = ko_match(ids[l]);
        if (m && (m[7] & 0x40)) { c->done_key = ckey; return -1; }
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
    key[k] = t * 100000 - (blk ? club_strength(blk, club[k]) : 0);
  }
  /* already drawn by us (a season loaded again): every place let through holds a club of a
     division no lower than any first-round club's, and in every tie the home club's division is
     no higher than the away club's. Only worth asking when the cup mixes divisions. */
  if (c->mode == 1 && ntiers_seen > 1) {
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
    if (ok) { c->done_key = ckey; return -1; }
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
    uint32_t* lst = rec_clubs(rec);
    for (int p = 0; p < CD_CLUBS && lst[p] != 0xffffffffu; p++)
      for (int k = 0; k < np; k++)
        if (club[k] == lst[p]) { if (lst[p] != want[k]) relisted++; lst[p] = want[k]; break; }
  }
  logf("fl26swiss: cup %d drawn %s: %d place(s) in %d round(s), %d club(s) moved, %d division(s), %d entry list place(s) rewritten; day %d",
       c->reg, c->mode == 2 ? "at random" : "with seeds", np, nr, moved, ntiers_seen, relisted, today());
  for (int k = 0; k < np; k++) {
    if (!pl[k].both)
      logf("fl26swiss:   cup %d round %#x slot: %06x through", c->reg, kinds[pl[k].round], want[k] & KO_TBD);
    else if (pl[k].side == 0 && k + 1 < np)
      logf("fl26swiss:   cup %d round %#x tie: %06x v %06x", c->reg, kinds[pl[k].round], want[k] & KO_TBD,
           want[k + 1] & KO_TBD);
  }
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

/* called by the loader every few dozen file opens; cheap outside spring */
__declspec(dllexport) void fl26_swiss_ko_tick(void)
{
  if (!g_base) return;
  int d = today();
  abs_day();                      /* the loader calls this all year: it keeps abs_day() across New Year */
  lpre_fill_days();
  ccup_fill_days();
  cupdraw_tick();
  if (d < 60 || d > 150) return;
  static const uint16_t KO_REGS[3] = { 4, 6, UECL_KO };
  static const char* KO_NAME[3] = { "Champions League", "Europa League", "Conference League" };
  for (int i = 0; i < 3; i++) {
    if (!get_rec(KO_REGS[i])) continue;
    ko_bracket(KO_REGS[i], 0x33, KO_NAME[i]);
    ko_bracket(KO_REGS[i], 0x34, KO_NAME[i]);
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
uint64_t curph_handler(uint64_t comp, uint64_t flag, uint64_t flag2)
{
  split_keys();
  uint64_t r = ((curph_fn)(uintptr_t)g_tramp_curph)(comp, flag, flag2);
  for (int ci = 0; ci < 3; ci++) {
    const cup_t* c = &CUPS[ci];
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
static uint32_t g_kogrey_n = 0;
uint64_t phkind_handler(uint32_t* comp, uint64_t kind)
{
  uint64_t r = ((phkind_fn)(uintptr_t)g_tramp_phkind)(comp, kind);
  uintptr_t ra = (uintptr_t)__builtin_return_address(0);
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
  /* Page type 0 is the grouped phase -- for our Europa and Conference League, the play-off
     for places 9-24.  The menu asks for it twice (0x14151f78c: the item, 0x14151fc11: whether
     it is live); until the play-off is drawn (+0x304 bit 8) the item is left out, as the
     Knockout Phase item is, rather than offered under the game's fallback name "W-L Table"
     with a page behind it that has nothing to show. */
  if (comp && kind == 0 && (ra == g_base + MENU_GRP_RA || ra == g_base + MENU_GRP2_RA)) {
    for (int ci = 1; ci < 3; ci++) {
      const cup_t* c = &CUPS[ci];
      if ((uint16_t)r != c->po) continue;
      unsigned char* po = find_rec(c->po);
      if (!po || !((*(uint32_t*)(po + 0x304) >> 8) & 1)) return r | 0xffff;
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
#define TXTGET_RVA 0x14996f0
static const unsigned char SIG_TXTGET[14] = {
  0x4c, 0x8b, 0x41, 0x08, 0x45, 0x33, 0xc9, 0x45, 0x8b, 0x10, 0x49, 0x8d, 0x40, 0x08 };
typedef const char* (*txtget_fn)(void* table, uint64_t index);
unsigned char* g_tramp_txtget = 0;
const char* txtget_handler(void* table, uint64_t index)
{
  if ((uint16_t)index == (uint16_t)LP_TEXT) return "League Phase";
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
    if ((uint16_t)reg == CUPS[ci].league || (uint16_t)reg == CUPS[ci].row) return LP_TEXT;
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
  for (int ci = 1; ci < 3; ci++) {
    const cup_t* c = &CUPS[ci];
    unsigned char* lg = find_rec(c->league);
    if (!lg || *(uint32_t*)(lg + 0x80) != *comp) continue;
    uint64_t on = (*(uint32_t*)(lg + 0x304) >> 8) & 1;
    if ((r & 0xff) != on && g_gstage_n++ < 8)
      logf("fl26swiss: %s Group stage item %s (league phase %u)", c->name, on ? "enabled" : "disabled",
           (unsigned)c->league);
    return (r & ~0xffull) | on;
  }
  return r;
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
    if (lpre_of(*in, &tie) >= 0 && tie >= 0) { cut++; continue; }
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
/* round of 16, quarter-finals, semi-finals (two legs each) and the final, 2025/26 */
static const uint32_t KO_DAYS[3][7] = {
  { 68, 75,  96, 103, 117, 124, 149 },   /* Champions League: 10/17 Mar, 7/14 Apr, 28 Apr/5 May, 30 May */
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
#define MAX_OUR_LEAGUES 128
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
  for (int i = 0; i < FL26_SWISS36_MATCHDAYS; i++) if (SWISS_DAYS[i] == d) return 1;
  for (int i = 0; i < FL26_SWISS6_MATCHDAYS; i++) if (UECL_DAYS[i] == d) return 1;
  for (int c = 0; c < 3; c++) {
    for (int i = 0; i < 7; i++) if (KO_DAYS[c][i] == d) return 1;
    for (int i = 0; i < 2; i++) if (QR_DAYS[c][i] == d || CUPS[c].days[i] == d) return 1;
  }
  return d == 230 + PLAYOFF_SHIFT || d == 237 + PLAYOFF_SHIFT;   /* reg 2's play-off */
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
static const uint16_t NATCUP_DAYS[12] = { 251, 254, 286, 289, 6, 9, 41, 44, 83, 86, 132, 135 };
static int access_league(uint16_t id)
{
  for (size_t i = 0; i < g_naccess; i++) if (g_access[i].rank && g_access[i].reg == id) return 1;
  return 0;
}
static int ccup_of_league(int k, uint16_t id)
{
  for (int e = 0; e < g_ccup[k].n && e < CCUP_MAX_ENTRY; e++) if (g_ccup[k].ereg[e] == id) return 1;
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
/* the days a league's clubs may play on besides the league: level 0 all of them, 1 without
   the league cup, 2 without the national cups either. A calendar-year league (g_org 0) has
   no European season and its own country's cups, so only its continental cups count. */
static void busy_days(uint16_t id, int level, int buf, uint8_t* bad)
{
  memset(bad, 0, 365);
  for (int k = 0; k < g_nccup; k++)                 /* CAF / AFC / CONMEBOL cups it feeds */
    if (!g_ccup[k].national && ccup_of_league(k, id)) {
      if (g_ccup[k].groups) for (int i = 0; i < 6; i++) block(bad, ccup_day(&g_ccup[k], 0, i), buf);
      for (int i = 0; i < (g_ccup[k].nd ? g_ccup[k].nd : 7) && i < CCUP_MAX_DAYS; i++) block(bad, ccup_day(&g_ccup[k], 1, i), buf);
    }
  if (g_org != 182) return;
  /* only a league that sends clubs to Europe keeps clear of its days: a second division blocked
     by them as well had one day left between a midweek round and a European week, and every
     league of a big world met on it (2026-10-08, the modpack: day 65 asked 403 matches of 280) */
  if (access_league(id)) {
    for (int i = 0; i < FL26_SWISS36_MATCHDAYS; i++) block(bad, SWISS_DAYS[i], buf);
    for (int i = 0; i < FL26_SWISS6_MATCHDAYS; i++) block(bad, UECL_DAYS[i], buf);
    for (int c = 0; c < 3; c++) {
      for (int i = 0; i < 7; i++) block(bad, KO_DAYS[c][i], buf);
      for (int i = 0; i < 2; i++) { block(bad, QR_DAYS[c][i], buf); block(bad, CUPS[c].days[i], buf); }
    }
    block(bad, 230 + PLAYOFF_SHIFT, buf); block(bad, 237 + PLAYOFF_SHIFT, buf);
  }
  /* a national cup round two days from a league round, not three: with three, the one day left
     between New Year's round and the cup's (day 3), and between early February's and the cup's
     (day 38), took every league of a big world -- 330 matches asked of 280 (2026-10-08) */
  if (level < 2) for (int i = 0; i < 12; i++) block(bad, NATCUP_DAYS[i], buf > 2 ? buf - 1 : buf);
  if (level < 1)
    for (int k = 0; k < g_nccup; k++) {
      if (!g_ccup[k].national || !ccup_of_league(k, id)) continue;
      for (int i = 0; i < g_ccup[k].nd && i < CCUP_MAX_DAYS; i++) block(bad, g_ccup[k].days[i], buf);
      for (int li = 0; li < g_nlpre; li++)
        if (g_lpre[li].ko == g_ccup[k].ko) { block(bad, g_lpre[li].days[0], buf); block(bad, g_lpre[li].days[1], buf); }
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
  for (uint32_t i = 0; i < n; i++) o[i] = (int32_t)rpos(r[i].day);
  int lo = o[0], hi = o[n - 1];
  for (int p = 0; p < 365; p++) cost[0][p] = (p >= lo && p <= hi && !bad[p]) ? abs(p - o[0] - jit) : INF;
  for (uint32_t i = 1; i < n; i++) {
    int32_t* c = cost[i & 1]; const int32_t* b = cost[(i - 1) & 1];
    int32_t best = INF; int arg = -1;
    for (int p = 0; p < 365; p++) {
      int q = p - gap;
      if (q >= 0 && b[q] < best) { best = b[q]; arg = q; }
      c[p] = INF; prev[i][p] = -1;
      if (p >= lo && p <= hi && !bad[p] && best < INF) { c[p] = best + abs(p - o[i] - jit); prev[i][p] = (int16_t)arg; }
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
 * played and stay in the table through the day-216 build. The game's own leagues are not dated
 * again at the rollover -- they keep the dates their career was made with, on day 216 -- so a
 * `july` line for one of them changes nothing; it starts as the game dates it. */
#define MAX_JULY 64
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
  static const int LEVEL[4] = { 0, 1, 2, 2 }, GAP[4] = { REST, REST, REST, REST - 1 };
  static uint8_t bad[365];
  static uint16_t said[128]; static int nsaid = 0;
  int seen = 0;
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
  for (int t = 0; t < 4; t++) {
    busy_days(id, LEVEL[t], GAP[t], bad);
    int moved = respace(r, n, bad, GAP[t], id % 3);
    if (moved < 0) continue;
    g_org = 182;
    if (!seen)
      logf("fl26swiss: reg %u -- %d of %u round(s) moved for %d day(s) between matches%s", (unsigned)id, moved,
           (unsigned)n, GAP[t], t == 1 ? " (not around the league cup)" : t >= 2 ? " (not around the cups)" : "");
    return;
  }
  g_org = 182;
  int kept = declash_near(r, n);
  if (!seen) logf("fl26swiss: reg %u -- no calendar with free days between matches; %d round(s) moved a day clear of European days",
                  (unsigned)id, kept);
  declash_log(id, declash(r, n));
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
static void league_rest(uint16_t id, date_t* r, uint32_t n) { rest_dates(id, r, n); }

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
  for (int k = 0; k < nsaid; k++) if (said[k] == id) seen = 1;
  if (!seen && nsaid < 64) said[nsaid++] = id;
  date_t* r = (date_t*)v->b;
  int32_t shift = 0;
  if (eu) {                                         /* the European calendar, from scratch */
    ((date_fn)(uintptr_t)g_tramp_date)((reg & ~(uint64_t)0xffff) | (n <= 38 ? MID_CAL_REG : LONG_CAL_REG), vec);
    have = (v->b && v->e >= v->b) ? (size_t)(v->e - v->b) / sizeof(date_t) : 0;
    r = (date_t*)v->b;
    if (n > have || have < 2) return;
  } else if (n > have) {
    uint32_t first = r[0].day;
    ((date_fn)(uintptr_t)g_tramp_date)((reg & ~(uint64_t)0xffff) | (n <= 38 ? MID_CAL_REG : LONG_CAL_REG), vec);
    have = (v->b && v->e >= v->b) ? (size_t)(v->e - v->b) / sizeof(date_t) : 0;
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

/* Put the key of every live split into the stub, once. Cheap enough to call from the date,
 * progression and current-phase hooks, which between them run on load and on the split day. */
static void split_keys(void)
{
  static uint32_t said_nc = 0;
  if (!g_carry_stub || g_carry_keys >= CARRY_SLOTS) return;
  for (int k = 0; k < g_nsplits; k++) {
    unsigned char* rr = get_rec(SPLITS[k].regular);
    if (!rr || ((*(uint32_t*)(rr + 0x308) >> 23) & 0x3f) != 12) continue;
    unsigned key = (*(uint32_t*)(rr + 0x30c) >> 7) & 0x3f;
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

static uint64_t split_dates(uint16_t id, uint64_t reg, void* vec, int part, const split_t* s)
{
  vec_t* v = (vec_t*)vec;
  static uint16_t said[16]; static int nsaid = 0; int seen = 0;
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

static uint64_t datelike_dates(uint16_t id, uint64_t reg, void* vec)
{
  static uint16_t said[MAX_DATELIKE]; static int nsaid = 0;
  for (int i = 0; i < g_ndlike; i++) {
    if (g_dlike[i][0] != id) continue;
    uint64_t rv = ((date_fn)(uintptr_t)g_tramp_date)((reg & ~(uint64_t)0xffff) | g_dlike[i][1], vec);
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

uint64_t date_handler(uint64_t reg, void* vec)
{
  uint16_t id = (uint16_t)reg;
  if (vec && !g_new_career && !g_day_ticked) {    /* a career built in this session (day 216), */
    int t = today();                               /* before its first day has gone by */
    /* a career in a January league (China, Japan, ...) is built on day 0: measured 2026-10-05 */
    if ((t >= BUILD_DAY && t <= 240) || t == 0) { g_new_career = 1; logf("fl26swiss: a new career, built on day %d", t); }
  }
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
      uint64_t rv = ((date_fn)(uintptr_t)g_tramp_date)((reg & ~(uint64_t)0xffff) | (uint16_t)((id & ~0x3ff) | 2), vec);
      vec_t* v = (vec_t*)vec;
      size_t have = (v->b && v->e >= v->b) ? (size_t)(v->e - v->b) / sizeof(date_t) : 0;
      date_t* r = (date_t*)v->b;
      for (size_t i = 0; i < have; i++) r[i].day = l->days[i < 2 ? i : 1];
      static unsigned char said[MAX_LPRE];
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
    static unsigned char said[2];
    if (have && !said[id == AFC_KO]++)
      logf("fl26swiss: reg %u -- AFC Champions League %s: %d of %u date(s) moved to midweek, days %u..%u",
           (unsigned)id, id == AFC_KO ? "knockout" : "groups", moved, (unsigned)have, r[0].day, r[have - 1].day);
    return rv;
  }
  if (european(id)) seen_once(1, id, 0);
  if (vec && is_playoff(id)) {
    uint64_t prv = ((date_fn)(uintptr_t)g_tramp_date)(reg, vec);
    vec_t* v = (vec_t*)vec;
    size_t have = (v->b && v->e >= v->b) ? (size_t)(v->e - v->b) / sizeof(date_t) : 0;
    date_t* r = (date_t*)v->b;
    if (g_po_enabled && po_season_half()) {          /* the February knockout play-off */
      for (size_t i = 0; i < have; i++) r[i].day = CUPS[0].days[i < 2 ? i : 1];
      static int said = 0;
      if (have && !said++) logf("fl26swiss: reg %u -- knockout play-off dated days %u and %u (%u record(s))",
                                (unsigned)id, CUPS[0].days[0], CUPS[0].days[1], (unsigned)have);
      return prv;
    }
    for (size_t i = 0; i < have; i++)
      if (r[i].day >= 200 && r[i].day + PLAYOFF_SHIFT <= 365) r[i].day += PLAYOFF_SHIFT;
    if (have && !g_playoff_said++)
      logf("fl26swiss: reg %u -- play-off moved %d days later, first leg on day %u",
           (unsigned)id, PLAYOFF_SHIFT, r[0].day);
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
    /* in the summer the play-offs are the August ones (q_fill), a day before the Champions League's */
    int aug = q_summer() || qi >= 0;
    const uint32_t* days = qi >= 0 ? QR_DAYS[qi / NQ] : aug ? QR_DAYS[0] : CUPS[ci].days;
    for (size_t i = 0; i < have; i++) r[i].day = days[i < 2 ? i : 1];
    static int said[2][NQR];
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
    if (have == 9) {
      /* reg 6's shipped calendar still has the old round of 32 in front (rounds 46, 47, 51, 52,
         53). A knockout of sixteen plays its round of 16 on the FIRST pair and skips the second
         (measured on reg 187, 2026-09-24: 18/25 Feb, then April), so both pairs get the round of
         16's dates and the rest follow in order. */
      r[0].day = r[2].day = KO_DAYS[k][0];
      r[1].day = r[3].day = KO_DAYS[k][1];
      for (int i = 4; i < 9; i++) r[i].day = KO_DAYS[k][i - 2];
      if (!said[k]++) logf("fl26swiss: reg %u -- knockout (9 records) on UEFA's dates: %u/%u, %u/%u, %u/%u, final %u",
                           (unsigned)id, r[0].day, r[1].day, r[4].day, r[5].day, r[6].day, r[7].day, r[8].day);
    } else if (have == 7) {
      for (int i = 0; i < 7; i++) r[i].day = KO_DAYS[k][i];
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
    r[i].day   = days[i] + shift;
    r[i].round = (uint32_t)i;
    r[i].kind  = FL26_DATE_KIND_LEAGUE;
  }
  v->e = v->b + (size_t)nmd * sizeof(date_t);
  g_stat[4]++;
  /* asked for once per match placed, so say it once per regulation */
  static uint16_t said[MAX_REGS]; static int nsaid = 0; int seen = 0;
  for (int k = 0; k < nsaid; k++) if (said[k] == id) seen = 1;
  if (!seen && nsaid < MAX_REGS) said[nsaid++] = id;
  if (!seen)
    logf("fl26swiss: reg %u -- calendar written: %d matchdays, days %u..%u",
         (unsigned)id, nmd, days[0] + shift, days[nmd - 1] + shift);
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
    if (!f) { if (g_nfinal >= 64) continue; f = &g_final[g_nfinal++]; }
    *f = t; f->reg = s->total; f->day = d;
    logf("fl26swiss: reg %u -- Apertura + Clausura table from %d matches kept as the final table: "
         "%08x %d pts, %08x %d pts ... last %08x %d pts", (unsigned)s->total, played,
         t.club[0], g_ctab_pts[0], t.club[1], g_ctab_pts[1], t.club[n - 1], g_ctab_pts[2]);
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
  if (d < 205 || d > 243 || !q_world_p(p)) return;
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
char daychk_handler(void* ctx)
{
  char r = ((daychk_fn)(uintptr_t)g_tramp_daychk)(ctx);
  if (g_td_fresh) { g_td_fresh = 0; ccup_fill_ahead(0, "the July teardown", 0); }
  static int last = -1, seen;
  int d = abs_day();
  g_day_ticked = 1;
  if (d != last) {
    if (seen++ < 3) logf("fl26swiss: day loop on day %d", today());
    else if (last >= 0 && d > last + 1) logf("fl26swiss: day loop skipped day(s) %d..%d", last + 1, d - 1);
    last = d;
  }
  apclau_keep();
  lpre_fill_days();
  ccup_fill_days();
  for (int p = NQR - 1; p >= 0; p--) q_fill(p);
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
vec16_t* teardown_pre(uint64_t ctx, vec16_t* in)
{
  (void)ctx;
  if (!in || !in->b || in->e < in->b) return in;
  int n = (int)(in->e - in->b), euro = 0, has186 = 0, has187 = 0, has1210 = 0, has1027 = 0, has1029 = 0;
  if (n + 24 > 512) return in;
  access_capture();
  ccup_keep_tables(in->b, n);
  ccup_keep_winners();
  for (int j = 0; j < n; j++) {
    uint16_t id = in->b[j];
    if (id == 2) euro = 1;
    if (id == UECL_REG) has186 = 1;
    if (id == UECL_KO) has187 = 1;
    if (id == UECL_ROW) has1210 = 1;
    if (id == 1027) has1027 = 1;
    if (id == 1029) has1029 = 1;
  }
  /* A national cup or super cup of ours (a `dates` line, id 176 and up) is closed with the
   * shipped cup it is dated as.  No event table names it, so it kept its old matches and its
   * goals, assists, titles and Team of the Tournament into the next season (GitHub #77). */
  uint16_t dcl[MAX_DATELIKE]; int ndcl = 0;
  for (int i = 0; i < g_ndlike; i++) {
    uint16_t id = g_dlike[i][0]; int like = 0, there = 0;
    if (id < 176 || !get_rec(id)) continue;
    for (int j = 0; j < n; j++) { if (in->b[j] == g_dlike[i][1]) like = 1; if (in->b[j] == id) there = 1; }
    if (like && !there && n + ndcl < 512) dcl[ndcl++] = id;
  }
  if (!euro && !ndcl) return in;
  if (!euro) {
    memcpy(g_td_list, in->b, (size_t)n * sizeof(uint16_t));
    memcpy(g_td_list + n, dcl, (size_t)ndcl * sizeof(uint16_t));
    g_td_vec.b = g_td_list; g_td_vec.e = g_td_list + n + ndcl; g_td_vec.c = g_td_list + 512;
    logf("fl26swiss: teardown on day %d -- %d cup(s) of ours closed with the cup they are dated as", today(), ndcl);
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
  int npre = 0;
  for (int i = 0; i < g_nlpre; i++)
    for (int g = -1; g < LPRE_TIES; g++) {
      uint16_t id = g < 0 ? g_lpre[i].reg : lpre_tie(&g_lpre[i], g);
      int there = 0;
      for (int j = 0; j < k; j++) if (g_td_list[j] == id) there = 1;
      if (!there && get_rec(id) && k < 512) { g_td_list[k++] = id; npre++; }
    }
  if (npre) logf("fl26swiss: July teardown -- %d league cup pre-round regulation(s) added", npre);
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

static int hook_or_chain(unsigned char* target, const unsigned char* sig, int n, void* handler, unsigned char** tramp_out)
{
  static const unsigned char JMP[6] = { 0xFF, 0x25, 0, 0, 0, 0 };
  if (!memcmp(target, sig, n)) return hook(target, sig, n, handler, tramp_out);
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

/* 0 ok; 2 signature mismatch; 3 VirtualAlloc failed; 4 VirtualProtect failed; 9 bad config;
   +10 for the date hook, +20 for the group hook */
__declspec(dllexport) int fl26_swiss_install(uint64_t exe_base, const uint16_t* regs, int nregs)
{
  if (!regs || nregs < 1 || nregs > MAX_REGS) return 9;
  g_base = exe_base;
  g_nreg = nregs;
  for (int i = 0; i < nregs; i++) g_reg[i] = regs[i];
  /* Both signatures are checked before either is patched: a mismatch on the second one used
     to leave the game half hooked while the loader reported it unmodified. */
  if (memcmp((void*)(uintptr_t)(exe_base + GEN_RVA),  SIG_GEN,  16)) return 2;
  if (memcmp((void*)(uintptr_t)(exe_base + DATE_RVA), SIG_DATE, 17)) return 12;
  if (memcmp((void*)(uintptr_t)(exe_base + GROUP_RVA), SIG_GROUP, 14)) return 22;
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
  if (!memcmp((void*)(uintptr_t)(exe_base + STAND_RVA), SIG_STAND, 15) &&
      !hook((unsigned char*)(uintptr_t)(exe_base + STAND_RVA), SIG_STAND, 15, (void*)stand_handler, &g_tramp_stand))
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
