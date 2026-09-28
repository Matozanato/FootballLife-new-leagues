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
   the shipped 38-round array wraps from 363 to 2. */
#define FL26_DATE_KIND_LEAGUE 2
static const uint32_t SWISS_DAYS[FL26_SWISS36_MATCHDAYS] = {
  259, 260, 273, 274, 294, 295, 308, 309, 329, 330, 343, 344, 20, 21, 28, 29 };

/* The Conference League plays six matchdays, one opponent from each of six pots (the second
   table in fl26swiss_table.h), on the real Thursdays: 2 and 23 October, 6 and 27 November,
   11 and 18 December.  Each round is two dates because a fixture record holds 16 matches and
   a round of 36 clubs is 18: the Wednesday before carries the first nine. */
static const uint32_t UECL_DAYS[FL26_SWISS6_MATCHDAYS] = {
  273, 274, 294, 295, 308, 309, 329, 330, 343, 344, 350, 351 };

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

/* Days after SWISS_DAYS that a listed competition plays: the first one on the days themselves,
   each next one two days later -- the Champions League on its Tuesday and Wednesday, the Europa
   League on the Thursday and Friday after. None of the shifted days crosses the year end. */
static uint32_t day_shift(uint16_t reg)
{
  for (int i = 0; i < g_nreg; i++) if (g_reg[i] == reg) return 2u * (uint32_t)i;
  return 0;
}

/* The Champions League play-off, regulation 2 and its replicas 0x402, 0x802, ... (the shipped
   case at 0x14158155b: days 230 and 237). A career that starts on day 212 enters the European
   competitions on day 238, after both legs, so the play-off got no matches at all, the group
   stage never filled and the Europa League never started (2026-09-23, calread: no match of
   competition 2 on any day). Both legs move two weeks later, to 244 and 251, still a week
   before the first league-phase matchday on 259. */
#define PLAYOFF_SHIFT 14
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
static int european(uint16_t id)
{
  return ((id & 0x3ff) >= 2 && (id & 0x3ff) <= 7 && id < 0x3400) || id == UECL_REG || id == UECL_KO || id == UECL_ROW
      || new_po(id);
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
  for (int k = 0; k < npairs; k++) {
    const fl26_pair_t* p = &table[k];
    if (p->home >= nclubs || p->away >= nclubs) { skipped++; continue; }
    cell_t* h = cell_at(ctx, 0, p->home, p->away);
    cell_t* a = cell_at(ctx, 0, p->away, p->home);
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
static int has_club(const uint32_t* a, size_t n, uint32_t c)
{
  for (size_t i = 0; i < n; i++) if ((a[i] & 0x3fff) == (c & 0x3fff)) return 1;
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
char setcl_handler(uint64_t id, u32vec* list, uint64_t flag)
{
  uint16_t r = (uint16_t)id, row = ko_row(r);
  if (r == 1 && cwc_world()) return cwc_setcl(id, list, flag);
  if (r == 10 || r == 16 || cont_comp(r) >= 0) {
    logf("fl26swiss: set_clubs reg %u -- %u club(s) on day %d, from %llx", (unsigned)r,
         (unsigned)(list && list->b ? list->e - list->b : 0), today(),
         (unsigned long long)((uintptr_t)__builtin_return_address(0) - g_base + 0x140000000ull));
    cont_swap(r, list, "set_clubs");
  }
  size_t n = list && list->b ? (size_t)(list->e - list->b) : 0;
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
static uint32_t full_club(uint32_t c)
{
  return c >> 14 ? c : club_of_id(c);
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
 * qualifying rounds collapsed into direct places:
 *
 *   Champions League 36 -- champions of 1-10, runners-up of 1-6, thirds of 1-5, fourths of 1-4,
 *     the two extra places of 2025/26 (England and Spain, fifth), Portugal's runner-up; then what
 *     the qualifiers would give: champions of 11-15 (SCO SUI AUT NOR GRE) and France 4th,
 *     Netherlands 3rd, Belgium 2nd.
 *   Europa League 36 -- the next places of 1-15, cup places given to the next league position,
 *     and the champions of 16-27 who would have dropped from Champions League qualifying
 *     (Hungary has no league in these worlds; Slovakia's champion takes its place).
 *   Conference League 36 -- the next place of every association from 1 to 27, the champions of
 *     the smaller ones (SVN FIN IRL BIH ALB MKD MNE) and six runners-up.
 *   A place whose league is missing, or whose club already went elsewhere, takes the next position
 *   of the same league; a list still short at the end is topped up from the next places of the
 *   big five, so each competition always gets its 36.
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
enum { UCL = 0, UEL = 1, UECL = 2, LIB = 3, LIBQ = 4, AFCL = 5 };
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
static const access_t ACCESS[] = {
  /* Champions League */
  {R_ENG,1,UCL},{R_ITA,1,UCL},{R_ESP,1,UCL},{R_GER,1,UCL},{R_FRA,1,UCL},{R_NED,1,UCL},{R_POR,1,UCL},
  {R_BEL,1,UCL},{R_TUR,1,UCL},
  {R_ENG,2,UCL},{R_ITA,2,UCL},{R_ESP,2,UCL},{R_GER,2,UCL},{R_FRA,2,UCL},{R_NED,2,UCL},
  {R_ENG,3,UCL},{R_ITA,3,UCL},{R_ESP,3,UCL},{R_GER,3,UCL},{R_FRA,3,UCL},
  {R_ENG,4,UCL},{R_ITA,4,UCL},{R_ESP,4,UCL},{R_GER,4,UCL},
  {R_ENG,5,UCL},{R_ESP,5,UCL},{R_POR,2,UCL},
  {R_SCO,1,UCL},{R_GRE,1,UCL},
  {R_FRA,4,UCL},{R_NED,3,UCL},{R_BEL,2,UCL},
  /* Europa League */
  {R_ENG,6,UEL},{R_ITA,5,UEL},{R_ESP,6,UEL},{R_GER,5,UEL},{R_FRA,5,UEL},
  {R_ENG,7,UEL},{R_ITA,6,UEL},{R_ESP,7,UEL},{R_GER,6,UEL},{R_FRA,6,UEL},
  {R_NED,4,UEL},{R_NED,5,UEL},{R_POR,3,UEL},{R_POR,4,UEL},{R_BEL,3,UEL},{R_BEL,4,UEL},
  {R_TUR,2,UEL},{R_TUR,3,UEL},
  {R_SCO,2,UEL},{R_SCO,3,UEL},
  {R_GRE,2,UEL},{R_DEN,1,UEL},{R_DEN,2,UEL},
  /* Conference League */
  {R_ENG,8,UECL},{R_ITA,7,UECL},{R_ESP,8,UECL},{R_GER,7,UECL},{R_FRA,7,UECL},
  {R_NED,6,UECL},{R_POR,5,UECL},{R_BEL,5,UECL},{R_TUR,4,UECL},
  {R_SCO,4,UECL},{R_GRE,3,UECL},
  {R_DEN,3,UECL},
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
    final_t* f = final_of(reg);
    /* the first rollover of the summer has the final tables; a later one (day 216, when the new
       season is built) already has next season's clubs in list order and must not replace it */
    if (f && ad >= f->day && ad - f->day < 60) continue;
    unsigned char* rec = get_rec(reg);
    if (!rec) continue;
    unsigned char* t = ((table_fn)(uintptr_t)(g_base + TABLE_RVA))(reg);
    uint32_t rows = t ? *(uint32_t*)(t + 0x3c0) : 0;
    if (rows < 4 || rows > FINAL_MAX) continue;
    /* A new career is built on day 216 and its tables exist then, with nobody having played:
       the clubs in list order. Kept, they stood in for last season's finish and the
       first-season order below never ran (2026-09-27: "final tables of 31 league(s) kept on
       day 216" in a career created that minute). A season's own build is the same rollover
       and, as said above, never holds a final table; and a table in exactly the league's list
       order is one nobody has played. */
    if (d >= BUILD_DAY || unplayed(rec, t, rows)) { skipped++; continue; }
    if (!f) { if (g_nfinal >= 64) continue; f = &g_final[g_nfinal++]; f->reg = reg; }
    f->n = (uint16_t)rows; f->day = ad;
    for (uint32_t k = 0; k < rows; k++) f->club[k] = *(uint32_t*)(t + k * 20);
    got++;
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
/* where each placed club came from, for the log: reg 0 = the first-season list */
typedef struct { uint16_t reg; uint8_t rank; } how_t;
static how_t g_how[3][FIELD];
static int any_final_kept(void)
{
  int d = abs_day();
  for (int i = 0; i < g_nfinal; i++) if (d >= g_final[i].day && d - g_final[i].day < 120) return 1;
  return 0;
}
/* build the three lists; a slot whose club is missing or already placed takes the next position
   of the same league */
static int access_build(void)
{
  uint32_t used[3 * FIELD + 8]; unsigned nused = 0; int tables = 0, orders = 0, gaps = 0, listed = 0;
  g_nacc[0] = g_nacc[1] = g_nacc[2] = 0;
  if (g_nfirst[0] + g_nfirst[1] + g_nfirst[2] && !any_final_kept()) {
    int missing = 0, twice = 0, over = 0;
    for (int k = 0; k < 3; k++)
      for (unsigned i = 0; i < g_nfirst[k]; i++) {
        uint32_t c = club_of_id(g_first[k][i]);
        if (!c) { missing++; logf("fl26swiss: first-season list -- team %u is not in any league of this game", g_first[k][i]); continue; }
        if (has_club(used, nused, c)) { twice++; continue; }
        if (g_nacc[k] >= FIELD) { over++; continue; }
        g_how[k][g_nacc[k]].reg = 0; g_how[k][g_nacc[k]].rank = 0;
        g_acc[k][g_nacc[k]++] = c; used[nused++] = c; listed++;
      }
    logf("fl26swiss: first-season list -- %u / %u / %u clubs taken (%d not in this game, %d listed twice, %d over %d)",
         g_nacc[0], g_nacc[1], g_nacc[2], missing, twice, over, FIELD);
  }
  for (size_t i = 0; i < g_naccess; i++) {
    const access_t* a = &g_access[i];
    if (a->comp > UECL) continue;                   /* the other continents: cont_build below */
    uint32_t c = 0; int ft = 0;
    uint16_t reg = a->reg; int first = a->rank;
    if (!first) {                                   /* cup winner, or the alt league's next place */
      c = cup_winner(reg);
      if (c && !has_club(used, nused, c)) ft = 1;
      else { c = 0; reg = a->alt; first = a->alt ? 1 : FINAL_MAX + 1; }
    }
    for (int rank = first; !c && rank <= FINAL_MAX; rank++) {
      c = access_club(reg, rank, &ft);
      if (!c) break;
      if (!(c >> 14) || has_club(used, nused, c)) { c = 0; continue; }
      break;
    }
    if (!c) { gaps++; logf("fl26swiss: access -- reg %u %s %u: no club", (unsigned)a->reg, a->rank ? "position" : "winner", (unsigned)a->rank); continue; }
    if (g_nacc[a->comp] >= FIELD || nused >= sizeof used / sizeof used[0]) continue;
    g_how[a->comp][g_nacc[a->comp]].reg = a->reg; g_how[a->comp][g_nacc[a->comp]].rank = (uint8_t)(a->rank ? a->rank : 0);
    g_acc[a->comp][g_nacc[a->comp]++] = c;
    used[nused++] = c;
    if (ft) tables++; else orders++;
  }
  /* top-up: the next free positions of the big five, round robin */
  static const uint16_t RESERVE[5] = { R_ENG, R_ESP, R_ITA, R_GER, R_FRA };
  int topped = 0;
  for (int k = 0; k < 3; k++) {
    int rank[5] = { 1, 1, 1, 1, 1 }, stuck = 0;
    while (g_nacc[k] < FIELD && nused < sizeof used / sizeof used[0] && stuck < 5) {
      stuck = 0;
      for (int j = 0; j < 5 && g_nacc[k] < FIELD; j++) {
        uint32_t c = 0; int ft = 0;
        while (rank[j] <= FINAL_MAX) {
          c = access_club(RESERVE[j], rank[j]++, &ft);
          if (!c) break;
          if ((c >> 14) && !has_club(used, nused, c)) break;
          c = 0;
        }
        if (!c) { stuck++; continue; }
        g_how[k][g_nacc[k]].reg = RESERVE[j]; g_how[k][g_nacc[k]].rank = (uint8_t)(rank[j] - 1);
        g_acc[k][g_nacc[k]++] = c; used[nused++] = c; topped++;
      }
    }
  }
  if (topped) logf("fl26swiss: access -- %d place(s) topped up from the big five", topped);
  logf("fl26swiss: access -- %u / %u / %u clubs (%d from the first-season list, %d positions from last season's tables, %d from first-season order, %d missing)",
       g_nacc[0], g_nacc[1], g_nacc[2], listed, tables, orders, gaps);
  return g_nacc[0] == FIELD;
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
    g_access_ready = access_build();
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
/* Which pool club gave way to which of ours, per competition, for this season's lists. The AFC
 * builder hands over the groups itself, each group as its own list (ids 1039 ... 8207) next to
 * the whole field (15), so the same pool club turns up twice and must give way to the same club
 * of ours both times -- whichever list comes first decides. (Measured 2026-09-27: with only the
 * whole field swapped, reg 15 held our eight and its groups the eight pool clubs.) */
static uint32_t g_mfrom[3][CONT_MAX], g_mto[3][CONT_MAX]; static unsigned g_nmap[3]; static int g_mday[3] = { -100000, -100000, -100000 };
/* The club of ours that pool club c gives way to in competition k, or 0 to leave it. A club
 * already mapped keeps its partner; otherwise the next place of ours that is neither given
 * nor already in the list `have` takes it. */
static uint32_t cont_map_one(int k, uint32_t c, const uint32_t* have, size_t nh, const how_t** how)
{
  unsigned j;
  for (j = 0; j < g_nmap[k]; j++)
    if ((g_mfrom[k][j] & 0x3fff) == (c & 0x3fff)) return has_club(have, nh, g_mto[k][j]) ? 0 : g_mto[k][j];
  for (j = 0; j < g_ncont[k] && g_nmap[k] < CONT_MAX; j++) {
    uint32_t cand = g_cont[k][j]; int given = 0;
    for (unsigned q = 0; q < g_nmap[k] && !given; q++) given = (g_mto[k][q] & 0x3fff) == (cand & 0x3fff);
    if (given || has_club(have, nh, cand)) continue;
    g_mfrom[k][g_nmap[k]] = c; g_mto[k][g_nmap[k]++] = cand;
    if (how) *how = &g_chow[k][j];
    return cand;
  }
  return 0;
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
    for (size_t i = 0; i < n && no < 64; i++) if (club_slot(blk, list->b[i]) == pool) order[no++] = i;
  }
  unsigned npool = 0, put = 0, left = 0, before = g_nmap[k];
  for (size_t q = 0; q < no; q++) {
    size_t i = order[q];
    uint32_t c = list->b[i];
    npool++;
    const how_t* h = 0;
    uint32_t to = cont_map_one(k, c, list->b, n, &h);
    if (!to) { left++; continue; }
    list->b[i] = to; put++;
    if (h) logf("fl26swiss:   %s: reg %u %s %u -> %08x, in place of pool club %08x", CONT_NAME[k],
                (unsigned)h->reg, h->rank ? "position" : "winner", (unsigned)h->rank, to, c);
  }
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
  uint32_t to = cont_map_one(k, club, have, nh, 0);
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

/* a league position for the Club World Cup: the final table kept at the July teardown if it is
   this summer's, else the live table (in June it is the season just finished) once a match has
   been played, else the league ordered by squad strength, else list order */
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
  final_t* s = seed_of(reg);
  if (s) { *how = "squad strength"; return (uint32_t)rank <= s->n ? s->club[rank - 1] : 0; }
  *how = "list order";
  return (uint32_t)rank <= rec_count(rec) ? rec_clubs(rec)[rank - 1] : 0;
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
    if (i == POT3)                                   /* the game's own entrants open pot 4 */
      for (size_t k = 0; k < offered; k++) if (cwc_add(&n, list->b[k])) game++;
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
 * given -- first v second, third v fourth ... -- and started at once. */
#define MAX_CCUP 4
#define CCUP_MAX_GROUPS 8
#define CCUP_MAX_ENTRY 32
#define R_LIBGROUP 9
#define R_UCLKO    4
typedef struct { uint16_t reg, ko, groups, n; uint16_t ereg[CCUP_MAX_ENTRY]; uint8_t erank[CCUP_MAX_ENTRY]; } ccup_t;
static ccup_t g_ccup[MAX_CCUP]; static int g_nccup = 0;
static uint32_t g_ccup_field[MAX_CCUP][CCUP_MAX_ENTRY]; static unsigned g_ccup_nf[MAX_CCUP];
static unsigned g_ccup_done[MAX_CCUP];
/* African weekends away from UEFA's evenings: 22/29 November, 26 January, 2/9/16 February;
   the knockout 15/22 March, 5/12 April (the first pair is spare), 26 April/3 May, final 17 May */
static const uint32_t CCUP_GROUP_DAYS[6] = { 326, 333, 25, 32, 39, 46 };
static const uint32_t CCUP_KO_DAYS[7] = { 73, 80, 94, 101, 115, 122, 136 };

static uint16_t ccup_rep(const ccup_t* c, int g) { return (uint16_t)(c->reg + 1024 * (g + 1)); }
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
static int ccup_taken(uint32_t c)
{
  for (int k = 0; k < g_nccup; k++) if (has_club(g_ccup_field[k], g_ccup_nf[k], c)) return 1;
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
    c->n = 0;
    for (unsigned e = 0; e < ne; e++, p += 2)
      if (c->n < CCUP_MAX_ENTRY) { c->ereg[c->n] = v[p]; c->erank[c->n] = (uint8_t)v[p + 1]; c->n++; }
    if (!c->groups) {
      c->reg = c->ko;
      if (c->n != 4 && c->n != 8 && c->n != 16 && c->n != 32) {
        logf("fl26swiss: cup %u -- a knockout of %u clubs is not 4, 8, 16 or 32; left out", (unsigned)c->ko,
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

static int ccup_fill_one(int k, void* started)
{
  const ccup_t* c = &g_ccup[k];
  unsigned char* rec = get_rec(c->reg);
  if (!ccup_world(c)) { logf("fl26swiss: cup %u -- its rows are not all in this world; left alone", (unsigned)c->reg); return 0; }
  if (rec_count(rec) || (c->groups && rec_count(get_rec(ccup_rep(c, 0))))) {
    logf("fl26swiss: cup %u already holds %u clubs; not filled again", (unsigned)c->reg, rec_count(rec));
    return 0;
  }
  unsigned n = 0, gaps = 0;
  g_ccup_nf[k] = 0;
  for (unsigned i = 0; i < c->n; i++) {
    const char* how = ""; uint32_t club = 0;
    for (int rank = c->erank[i]; rank <= FINAL_MAX; rank++) {
      club = cwc_club(c->ereg[i], rank, &how);
      if (!club) break;
      if ((club >> 14) && !has_club(g_ccup_field[k], n, club) && !ccup_taken(club)) break;
      club = 0;
    }
    if (club) {
      g_ccup_field[k][n++] = club; g_ccup_nf[k] = n;
      logf("fl26swiss:   cup %u entry %2u: reg %u position %u -> %08x (%s)", (unsigned)c->reg, n,
           (unsigned)c->ereg[i], (unsigned)c->erank[i], club, how);
    } else gaps++;
  }
  if (n != c->n) {
    logf("fl26swiss: cup %u -- only %u of %u clubs found; not started", (unsigned)c->reg, n, (unsigned)c->n);
    g_ccup_nf[k] = 0;
    return 0;
  }
  if (!c->groups) {
    u32vec v = { g_ccup_field[k], g_ccup_field[k] + n, g_ccup_field[k] + n };
    ((setcl_fn)(uintptr_t)(g_base + SETCL_RVA))(c->ko, &v, 1);
    run_flush();
    logf("fl26swiss: cup %u -- day %d: knockout of %u clubs (%08x v %08x ...)", (unsigned)c->ko, today(),
         rec_count(rec), g_ccup_field[k][0], g_ccup_field[k][1]);
    if (rec_count(rec) != n) return 0;
    start_stage(started, c->ko);
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
static int ccup_fill(void* started)
{
  int any = 0;
  for (int k = 0; k < g_nccup; k++) any |= ccup_fill_one(k, started);
  return any;
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
  size_t want = ko ? 7 : 6;
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
    r[i].day = ko ? CCUP_KO_DAYS[j] : CCUP_GROUP_DAYS[j];
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

char prog_handler(void* ctx, uint64_t id, void* started)
{
  uint16_t r = (uint16_t)id;
  split_keys();
  {
    const split_t* s; int part = split_part(r, &s);
    if (part) {
      char ok = ((prog_fn)(uintptr_t)g_tramp_prog)(ctx, id, started);
      if (part == 2 && r > 175) {
        char sp = ((splitfn_t)(uintptr_t)(g_base + SPLIT_FN_RVA))(ctx, id, started);
        logf("fl26swiss: reg %u -- split regular phase over on day %d, groups filled by 0x141343d70 -> %d",
             (unsigned)r, today(), (int)sp);
        ok |= sp;
      } else {
        logf("fl26swiss: reg %u -- split progression on day %d -> %d", (unsigned)r, today(), (int)ok);
      }
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

/* called by the loader every few dozen file opens; cheap outside spring */
__declspec(dllexport) void fl26_swiss_ko_tick(void)
{
  if (!g_base) return;
  int d = today();
  abs_day();                      /* the loader calls this all year: it keeps abs_day() across New Year */
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
   4 Libertadores qualifying, 5 AFC Champions League), and for a
   cup the league whose next free position takes the place when the winner is already in.
   Replaces the compiled list; answers how many entries were taken, or -1 when none were. */
__declspec(dllexport) int fl26_swiss_access(const uint16_t* v, int n)
{
  int k = 0;
  for (int i = 0; v && i < n && k < ACCESS_MAX; i++) {
    const uint16_t* e = v + 4 * i;
    if (!e[0] || e[2] > AFCL || e[1] > FINAL_MAX) continue;
    g_access_buf[k].reg = e[0]; g_access_buf[k].rank = (uint8_t)e[1];
    g_access_buf[k].comp = (uint8_t)e[2]; g_access_buf[k].alt = e[3];
    k++;
  }
  if (!k) return -1;
  g_access = g_access_buf; g_naccess = (size_t)k; g_access_cfg = 1;
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
  if (get(reg & 0xffff, rec)) return *(uint32_t*)(rec + 0x40);
  if ((uintptr_t)__builtin_return_address(0) == g_base + MENU_NAME_RA &&
      ((uint16_t)reg == CUPS[1].po || (uint16_t)reg == CUPS[2].po) && get(CUPS[0].po, rec))
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
static void league_dates(uint16_t id, uint64_t reg, void* vec)
{
  unsigned char* rec = get_rec(id);
  vec_t* v = (vec_t*)vec;
  size_t have = (v->b && v->e >= v->b) ? (size_t)(v->e - v->b) / sizeof(date_t) : 0;
  if (!rec || have < 2) return;
  uint32_t clubs = *(uint32_t*)(rec + 0x30c) & 0x7f, legs = *(uint32_t*)(rec + 0x308) >> 29;
  uint32_t n = (clubs & 1 ? clubs : clubs - 1) * legs;
  if (clubs < 4 || !legs || n == have) return;
  static uint16_t said[64]; static int nsaid = 0; int seen = 0;
  for (int k = 0; k < nsaid; k++) if (said[k] == id) seen = 1;
  if (!seen && nsaid < 64) said[nsaid++] = id;
  date_t* r = (date_t*)v->b;
  int32_t shift = 0;
  if (n > have) {
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
  }
  memcpy(r, tmp, n * sizeof(date_t));
  v->e = v->b + (size_t)n * sizeof(date_t);
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
static const uint16_t SCOT_DAYS[38] = {
  226, 233, 240, 254, 261, 268, 275, 296, 300, 303, 310, 321, 324, 331, 338, 345, 356, 359, 363,
  2, 13, 16, 20, 23, 31, 34, 37, 51, 58, 65, 72, 79, 100,
  107, 114, 121, 128, 142 };

/* 0 not a split row, 1 total, 2 regular phase, 3 a group */
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

/* Put the key of every live split into the stub, once. Cheap enough to call from the date,
 * progression and current-phase hooks, which between them run on load and on the split day. */
static void split_keys(void)
{
  if (!g_carry_stub || g_carry_keys >= CARRY_SLOTS) return;
  for (int k = 0; k < g_nsplits; k++) {
    unsigned char* rr = get_rec(SPLITS[k].regular);
    if (!rr || ((*(uint32_t*)(rr + 0x308) >> 23) & 0x3f) != 12) continue;
    unsigned key = (*(uint32_t*)(rr + 0x30c) >> 7) & 0x3f;
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
  if (T <= 38) { L = 38; for (size_t i = 0; i < L; i++) line[i] = SCOT_DAYS[i]; }
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
  if (!seen)
    logf("fl26swiss: reg %u -- split %s of %u: %u rounds on days %u..%u (season %u+%u on a %u-date line)",
         (unsigned)id, part == 2 ? "regular phase" : "group", (unsigned)s->total, n,
         r[0].day, r[n - 1].day, n1, n2, (unsigned)L);
  return rv;
}

uint64_t date_handler(uint64_t reg, void* vec)
{
  uint16_t id = (uint16_t)reg;
  {
    const split_t* s; int part;
    if (vec && (part = split_part(id, &s)) != 0) { uint64_t rv = split_dates(id, reg, vec, part, s); split_keys(); return rv; }
  }
  if (vec && (cwc_id(id) || id == CWC_KO) && cwc_world()) return cwc_dates(id, reg, vec);
  if (vec) {
    int ko, k = ccup_of(id, &ko);
    if (k >= 0 && ccup_world(&g_ccup[k])) return ccup_dates(k, ko, id, reg, vec);
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
  if (vec && new_po(id)) {
    /* the added play-offs: past the calendar switch, so they borrow reg 2's records (the same
       tie of it) and get the Europa League's Thursdays */
    int ci = (id & 0x3ff) == UEL_PO ? 1 : 2;
    uint64_t rv = ((date_fn)(uintptr_t)g_tramp_date)((reg & ~(uint64_t)0xffff) | (uint16_t)((id & ~0x3ff) | 2), vec);
    vec_t* v = (vec_t*)vec;
    size_t have = (v->b && v->e >= v->b) ? (size_t)(v->e - v->b) / sizeof(date_t) : 0;
    date_t* r = (date_t*)v->b;
    for (size_t i = 0; i < have; i++) r[i].day = CUPS[ci].days[i < 2 ? i : 1];
    static int said[3];
    if (!said[ci]++)
      logf("fl26swiss: reg %u -- %s play-off dated days %u and %u (%u record(s))", (unsigned)id, CUPS[ci].name,
           CUPS[ci].days[0], CUPS[ci].days[1], (unsigned)have);
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
  if (vec && our_league(id)) {
    uint64_t rv = ((date_fn)(uintptr_t)g_tramp_date)(reg, vec);
    league_dates(id, reg, vec);
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
  for (int j = 0; j < n; j++) {
    uint16_t id = in->b[j];
    if (id == 2) euro = 1;
    if (id == UECL_REG) has186 = 1;
    if (id == UECL_KO) has187 = 1;
    if (id == UECL_ROW) has1210 = 1;
    if (id == 1027) has1027 = 1;
    if (id == 1029) has1029 = 1;
  }
  if (!euro) return in;
  logf("fl26swiss: July teardown on day %d (%d ids)", today(), n);
  int uecl = get_rec(UECL_REG) && !(has186 && has187 && has1210);
  int cwc = cwc_world(), nccw = 0;
  for (int c = 0; c < g_nccup; c++) if (ccup_world(&g_ccup[c])) nccw++;
  if (!uecl && !cwc && !nccw) return in;
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
  if (npo) logf("fl26swiss: July teardown -- %d play-off regulation(s) of the Europa/Conference League added", npo);
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
  {
    int cr = carry_install(exe_base);
    if (!cr) logf("fl26swiss: split points carry live (key switch@%llx)", (unsigned long long)(exe_base + CARRY_SITE_RVA));
    else logf("fl26swiss: split points carry NOT installed (%d)", cr);
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
  if (!hook((unsigned char*)(uintptr_t)(exe_base + PHNAME_RVA), SIG_PHNAME, 17, (void*)phname_handler, &g_tramp_phname))
    logf("fl26swiss: play-off names live (@%llx)", (unsigned long long)(exe_base + PHNAME_RVA));
  else
    logf("fl26swiss: play-off names NOT installed (signature)");
  if (!hook((unsigned char*)(uintptr_t)(exe_base + GSTAGE_RVA), SIG_GSTAGE, 19, (void*)gstage_handler, &g_tramp_gstage))
    logf("fl26swiss: group stage item live (@%llx)", (unsigned long long)(exe_base + GSTAGE_RVA));
  else
    logf("fl26swiss: group stage item NOT installed (signature)");
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
