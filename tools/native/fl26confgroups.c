/* fl26confgroups.dll -- FL 2027: Select Team and Competition Info by confederation, then country.
 *
 * What the player sees.  With a big world (the Megapack has some 300 leagues) the league column
 * of Select Team (Master League > New, Kick Off, Edit) is one long list, and so is the category
 * grid of Competition Info.  With this DLL both go down one level at a time (mato 08.11.: "da
 * uđemo onda u novi segment, pa da nas krug vraca nazad"):
 *
 *     Select Team                         Competition Info
 *     + UEFA (164)                        + UEFA          (right: UCL, UEL, UECL, Club WC)
 *     + CONMEBOL (31)                     + CONMEBOL
 *     ...                                 ...
 *     the rows of no confederation        the categories of no confederation
 *     (national teams, "Other",           (the club competitions ...) as before
 *     Classic Teams) as before
 *
 * Confirm on a confederation shows only its countries, under a "- UEFA" row:
 *
 *     - UEFA                              - UEFA
 *     + Albania (2)                       Albania         (right: its competitions, the game's)
 *     + Andorra (1)                       Andorra
 *     ...                                 ...
 *     the leagues of no country (the confederation's "other clubs") as rows of their own
 *
 * and in Select Team Confirm on a country shows only its leagues, under a "- Albania" row; a
 * league is entered exactly as before (its clubs).  Every country is a level of its own, one
 * league or more (mato 08.11.: "mislim da ce biti jednostavnije za svaku drzavu tako").  Back
 * goes up one level, the cursor on the row it came from; on the top level, the game's Back.
 * Confirm on a "- ..." row is Back too.  A country's row is its first league's slot: its flag,
 * that league's emblem and League Info on the right (the League Info panel is the game's, one
 * league's, not a list).  In Competition Info the right side lists competitions, and on a
 * confederation its continental cups and the Club World Cup (the world line's `cups`; not the
 * game's International Champions Cups of the club competitions' category).
 *
 * The world file says which league slot (Select Team) and which region (Competition Info) is in
 * which confederation, and which slot is in which country: the `confgroups` and `confnames`
 * lines Mod Studio's League Builder writes for FL 2027 (leaguebuilder.confgroups_lines), handed
 * to this DLL by fl26confgroups.lua.  Groups: 0 UEFA, 1 CONMEBOL, 2 CONCACAF, 3 AFC, 4 CAF, 5 OFC.
 * A slot or region the line does not name stays a row of its own, where the game had it; a
 * grouped slot of no country is a row of its own in its confederation.
 *
 * Select Team (TeamSelectCommon, vtable 0x14271c8c8; the list model TeamSelectSingle holds at
 * +0x98).  Its rows are a std::vector at +0x100 of 0x70-byte rows: +0 the slot, +8 the clubs
 * (vector of 0x50-byte entries: +0 the team id, +8 an emblem path, +0x28 a name), +0x20 the name
 * (std::string, what the league column prints), +0x40 an emblem path (empty: the emblem of the
 * slot), +0x60 a byte (1), +0x64 the club cursor.  The cursor is [+0x118] + [+0x11c]; [+0x9b] 0 =
 * league column; [+0x99] |= 2 redraws the league column (0x140c97230 draws nine cells around the
 * cursor and takes the row count afresh every time; the flag is 0x140c950d0(slot), the emblem
 * 0x140c96090).  The rows are built (0x140c934f0, a sorted insert, the only function that adds
 * one) before the list's init (vtable +0xd8).
 *   init (+0xd8)      before the game's init: the rows move into a private "master" vector and
 *                     the visible vector at +0x100 is rebuilt from it with the game's own
 *                     push_back (0x140c97070, a deep copy): the rows of the level shown.  A row of
 *                     ours is a row with no clubs and the text "+ ..." or "- ..."; a confederation
 *                     or a "- ..." row has slot 123 (no league: no emblem, no flag) or its `heads`
 *                     slot, a country its first league's slot.
 *   0x140c97417       the call of a row's emblem (0x140c96090, its only caller; the row's +0x40
 *                     is its argument): a confederation's row with a logo (`emblems`) gets the
 *                     emblem of that competition id (emb_99xx, written by Mod Studio), the way
 *                     the game draws a league's; any other row the game's.
 *   decide (+0x188)   league column on a row of ours: in or back, rebuild, cursor (the game would
 *                     take a row with no clubs for a team pick with an invalid id -- 0x140c94720 --
 *                     so a row of ours never reaches it); else the game's.
 *   cancel (+0x190)   league column below the top level: back one level; else the game's.
 *   dtor (+0x18)      frees the master rows (0x140c96fa0), then the game's.
 *   0x140c934f0       a row added after init goes into the master rows and the list is rebuilt.
 *                     Kick Off's lists come to init empty and get their leagues after it (seen
 *                     in FL 2027 1.1, 08.11.): such a list is taken by the insert that brings
 *                     enough rows (or by the game's cursor below), on the confederations' level.
 *   0x140c94330       "put the cursor on this team" (26 callers; ML, Edit, Kick Off): the level of
 *                     the team's league is shown first, so the game finds its row.
 *   0x140c942a0       "put the cursor on this slot": the same for a slot.
 *   0x140c98bcf       League Info (the panel of a new Master League, 0x140c98760): the call of the
 *                     builder 0x140c6ccb0(&info, league) goes through a stub that hands cg_info the
 *                     list model ([rdi+0x98], the panel's this is in rdi there).  A confederation's
 *                     row ("+ UEFA (164)", and "- UEFA" while it is open) shows that confederation's
 *                     continental cups -- the world line's `cups` of the group without the Club World
 *                     Cup -- and no league above or below (B402: the game filled the panel from slot
 *                     123 and showed the Club World Cup, three Intercontinental cups and two empty
 *                     emblems).  A country's row and a league's row keep the game's League Info.
 *   0x140c98f8a       League Info's update (0x140c98ee0, vtable +0x250): the call of the slot
 *                     getter 0x140c94fa0 goes through a stub that hands cg_slot the panel (rbx).
 *                     The panel redraws (+0x270) only when that slot differs from the one it keeps
 *                     at +0xbc, and all confederation rows share slot 123, so cg_slot spoils +0xbc
 *                     when the row's confederation changes ("+ UEFA" -> "+ CONMEBOL").
 * Each of the direct hooks is a 5-byte jump at the function's entry; the bytes it covers (whole
 * instructions, none rip-relative) run in a trampoline that jumps back.
 * The subclasses with vtables of their own (0x1426802d0, 0x1426805c0 ...) are not touched: the
 * vtable entries are patched in TeamSelectCommon's vtable only, and the direct hooks do nothing
 * for an object this DLL did not take at init.
 *
 * Competition Info (MenuModeLeagueSelectCategory, vtable 0x142677860).  The categories are a
 * vector of u32 region ids at +0x90, built by init; cell i of the grid "p_select" draws entry i
 * (0x140acd350 -> 0x140acd3f0: the picture by region, default "compeCategory-interClub"; the
 * label from 0x1415787c0(&string, region)).  Decide (+0x188) opens entry [cursor] (0x140e43850).
 * The right side (0x140acd560(this, region)) lists the region's competitions (0x1415789c0).
 *   init (+0xd8)      after the game's init: the regions are copied aside and the vector is
 *                     rebuilt from them, a confederation being a pseudo region 0x0C0F0000+g; then
 *                     the game's own redraw: 0x140acd350, the item count 0x140e41fe0, the cursor
 *                     0x140e411f0, the right side of the region under the cursor.
 *   decide (+0x188)   on a pseudo region: in (or back, on "- UEFA") and the same redraw; else the
 *                     game's (and the region is remembered: coming back to the screen shows its
 *                     confederation again with the cursor on it).
 *   cancel (+0x190)   in a confederation: back to the confederations; else the game's (the
 *                     menus' generic Back 0x140ca7010, patched in this vtable only).
 *   dtor (+0x18)      frees the copy.
 *   0x140acd4ef       the label call (the only caller of 0x1415787c0) goes through cg_label: a
 *                     pseudo region gets "+ UEFA" / "- UEFA" (the game's own string assign,
 *                     0x140402240, so the game frees it as its own), any other region the game's.
 *   0x140acd5e9       the right side's call of 0x1415789c0: a pseudo region gets the club
 *                     competitions' (region 1), only the group's `cups` kept; any other the game's.
 *                     The list is of regulation ids: each is kept by its live record's
 *                     competition id (0x1414bb000, +0x80), not by the regulation id (17.11.).
 * A pseudo region has no regulation and no picture: the region lookups only compare, so they
 * find nothing; the picture is the default.
 *
 * All or nothing: FL_2027.exe only ("off not FL 2027" otherwise); every vtable entry and every
 * function this calls or hooks is checked byte for byte first; one mismatch and nothing is
 * written ("confgroups: off ...").  With fewer than two confederations or six grouped rows a
 * list is left exactly as the game built it.
 *
 * Apart from all of that, one byte for Select Team's attack / midfield / defence numbers, which
 * the game never shows below 39 (fl26_confgroups_numbers, "the numbers of a club's three lines"
 * below): FL_2027.exe only as well, checked and written on its own, with or without the lists.
 */
#include <windows.h>
#include <stdint.h>
#include <string.h>
#include <stdio.h>
#include <stdarg.h>

static char g_log[2048];
static int g_log_len;

static void logf(const char* fmt, ...)
{
  char line[400];
  va_list ap; va_start(ap, fmt);
  int n = vsnprintf(line, sizeof line - 1, fmt, ap);
  va_end(ap);
  if (n < 0) return;
  if (n > (int)sizeof line - 2) n = (int)sizeof line - 2;
  line[n++] = '\n';
  if (g_log_len + n < (int)sizeof g_log) { memcpy(g_log + g_log_len, line, n); g_log_len += n; }
}

/* a trace of what the lists did, for the test in game: modules\fl26confgroups-trace.txt, the
 * first 300 lines of a session (trace=1 in the world line; off by default) */
static wchar_t g_trace_path[MAX_PATH + 40];
static int g_trace_on, g_trace_lines;
static void trace(const char* fmt, ...)
{
  if (!g_trace_on || g_trace_lines >= 300 || !g_trace_path[0]) return;
  FILE* f = _wfopen(g_trace_path, g_trace_lines ? L"ab" : L"wb");
  if (!f) return;
  g_trace_lines++;
  va_list ap; va_start(ap, fmt);
  vfprintf(f, fmt, ap);
  va_end(ap);
  fputc('\n', f);
  fclose(f);
}

static uint64_t B;                                    /* the exe's base */
#define VA(x) (B + ((uint64_t)(x) - 0x140000000ULL))

/* ---- Select Team (TeamSelectCommon) ---- */
#define TSC_VT       0x14271c8c8
#define TSC_DTOR     0x140c93200          /* +0x18 */
#define TSC_INIT     0x140c95420          /* +0xd8 */
#define TSC_DECIDE   0x140c95a10          /* +0x188 */
#define TSC_CANCEL   0x140c95920          /* +0x190 */
#define ROWS_CLEAR   0x140c97010          /* (vector*): destroys the rows, keeps the buffer */
#define ROWS_PUSH    0x140c97070          /* (vector*, const row*): push_back, a deep copy */
#define ROWS_FREE    0x140c96fa0          /* (vector*): destroys the rows and frees the buffer */
#define TSC_INSERT   0x140c934f0          /* (this, const row*): the sorted insert */
#define INSERT_LEN   6                    /* push rbp; push rsi; push rdi; push r12 */
#define TSC_PICK     0x140c94330          /* (this, team id): cursor on that team */
#define PICK_LEN     5                    /* mov [rsp+0x18], rsi */
#define TSC_JUMP     0x140c942a0          /* (this, slot): cursor on that slot's row */
#define JUMP_LEN     11                   /* sub rsp, 0x38; mov rax, [rcx+0x100] */
#define LIST_SET     0x140e411f0          /* (this, list, index, 0, 0f, 0f): the list's cursor */
#define ROW_EMBLEM   0x140c96090          /* (image, frame, slot, std::string* row+0x40): a row's emblem */
#define EMBLEM_CALL  0x140c97417          /* call 0x140c96090, in 0x140c97230 (its only caller) */
#define IMG_SHOW     0x140e4c240          /* (widget, on, 2) */
#define IMG_SIZE     0x140e77290          /* (image, u32* competition) -> the size variant */
#define IMG_COMP     0x140e5cb30          /* (image, competition id, size variant, 0): emb_<id> */
#define INFO_FN      0x140c6ccb0          /* (info*, league id) -> info*: League Info's competitions */
#define INFO_CALL    0x140c98bcf          /* call 0x140c6ccb0, in the League Info panel 0x140c98760 */
#define INFO_THIS    0x140c98799          /* mov rdi, rcx: the panel's this stays in rdi */
#define SLOT_FN      0x140c94fa0          /* (list model) -> the slot of the row under the cursor, -1 none */
#define SLOT_CALL    0x140c98f8a          /* call 0x140c94fa0, in League Info's update 0x140c98ee0 (vtable +0x250) */
#define INFO_LAST    0xbc                 /* League Info: the slot it was last drawn for (+0x270 redraws on a change) */
#define CWC_CID      1                    /* the Club World Cup (leaguebuilder.CLUB_WORLD_CUP_CID) */
#define INFO_ICONS   6                    /* emblemCompe_0..5 */
/* ---- Competition Info (MenuModeLeagueSelectCategory) ---- */
#define CI_VT        0x142677860
#define CI_DTOR      0x140accc00          /* +0x18 */
#define CI_INIT      0x140accce0          /* +0xd8 */
#define CI_DECIDE    0x140acd2c0          /* +0x188 */
#define CI_CANCEL    0x140ca7010          /* +0x190: the menus' generic Back (mov edx, 2; jmp) */
#define CI_CELLS     0x140acd350          /* (this): draws the cells */
#define CI_COUNT     0x140e41fe0          /* (this, list, count, 1, visible 0) */
#define CI_PREVIEW   0x140acd560          /* (this, region): the right side, the region's competitions */
#define CI_RESERVE   0x140acdac0          /* (vector<u32>*, capacity) */
#define CUR_LIST     0x140e3d130          /* (this) -> the current list */
#define CUR_INDEX    0x140e3d8e0          /* (this, list) -> its cursor */
#define LABEL_FN     0x1415787c0          /* (std::string* out, region) -> out: the category's name */
#define LABEL_CALL   0x140acd4ef          /* call 0x1415787c0, in 0x140acd3f0 */
#define STR_ASSIGN   0x140402240          /* (std::string*, const std::string*, 0, npos) */
#define REGION_COMPS 0x1415789c0          /* (u32* region, vector<u16>* out): the region's competitions */
#define COMPS_CALL   0x140acd5e9          /* call 0x1415789c0, in 0x140acd560 (the right side) */
/* the region's list is of REGULATION ids (0x1414ce270 pushes a live record's +0x00), not of
 * competition ids: the right side finds each record (0x1414bb000) and shows emb_<+0x80> */
#define GAME_FN      0x1414b6a60          /* () -> the game; +0x48 the data that owns the regulations */
#define GAME_DATA    0x48
#define REG_FIND     0x1414bb000          /* (data, u16 regulation id) -> its live record, a dummy if none */
#define REG_CID      0x80                 /* live regulation record: the competition id, a dword (tools/cidwide.py) */
#define CLUB_REGION  1                    /* the club competitions' category */

#define NG        6
#define NCTRY     1024                    /* Country.bin ids */
#define HEAD_SLOT 123                     /* fl26world.NO_SLOT: no league, no emblem, no flag */
#define PSEUDO    0x0C0F0000u             /* + group: a confederation in Competition Info */
#define MAXR      1024                    /* rows of one Select Team list */
#define MAXC      512                     /* categories of Competition Info */
#define ROW       0x70

static const char* const GNAME[NG] = { "UEFA", "CONMEBOL", "CONCACAF", "AFC", "CAF", "OFC" };
static int8_t g_slot[1024];               /* slot -> group, -1 none */
static int16_t g_sctry[1024];             /* slot -> country, -1 none */
static int8_t g_reg[256];                 /* region -> group, -1 none */
static char g_cname[NCTRY][40];           /* country -> its name (the confnames line) */
static int g_head[NG] = { HEAD_SLOT, HEAD_SLOT, HEAD_SLOT, HEAD_SLOT, HEAD_SLOT, HEAD_SLOT };
static int g_emb[NG];                     /* group -> the competition id of its row's emblem, 0 none */
/* lab 23/11/2026 (Argentina, the user: "Regionais > each region > its zones"): folders inside a country's level of
   Select Team. `confsub slots=<slot>:<folder>,...` puts a league in a folder; `confsubnames <folder>:<parent>:<cid>:
   <name>|...` names a folder, its parent (0: the country's level) and its row's emblem (a competition id, 0: its first
   league's). A folder's row is "+ Name (n)" -- n its leagues, sub-folders' too -- and opens a level of its own under
   "- Name"; Back goes to the parent's level, the cursor on the folder's row. */
#define NFOLD 256
static uint8_t g_sfold[1024];             /* slot -> folder, 0 none */
static uint8_t g_fpar[NFOLD];             /* folder -> its parent, 0 the country */
static int g_femb[NFOLD];                 /* folder -> emblem competition id, 0 none */
static char g_fname[NFOLD][48];
static int g_tables;

static void tables_init(void)
{
  if (g_tables) return;
  memset(g_slot, 0xff, sizeof g_slot);
  memset(g_sctry, 0xff, sizeof g_sctry);
  memset(g_reg, 0xff, sizeof g_reg);
  g_tables = 1;
}

typedef uint64_t (*fn1_t)(void*);
typedef uint64_t (*fn2_t)(void*, uint64_t);
typedef void (*vecop_t)(void*);
typedef void (*push_t)(void*, const void*);
typedef void (*list_set_t)(void*, uint32_t, uint32_t, uint32_t, float, float);
typedef void (*count_t)(void*, uint32_t, uint32_t, uint32_t, uint32_t);
typedef void (*reserve_t)(void*, uint64_t);
typedef uint32_t (*cur_list_t)(void*);
typedef uint32_t (*cur_index_t)(void*, uint32_t);
typedef void* (*label_t)(void*, uint32_t);
typedef void* (*assign_t)(void*, const void*, uint64_t, uint64_t);
typedef void* (*comps_t)(void*, void*);
typedef char* (*game_t)(void);
typedef char* (*reg_find_t)(void*, uint32_t);
typedef void (*row_emblem_t)(void*, void*, uint32_t, void*);
typedef void (*img_show_t)(void*, uint32_t, uint32_t);
typedef uint32_t (*img_size_t)(void*, uint32_t*);
typedef uint32_t (*img_comp_t)(void*, uint32_t, uint32_t, uint32_t);
typedef uint32_t* (*info_t)(uint32_t*, uint32_t);
typedef uint32_t (*slot_fn_t)(void*);

/* the trampolines: the bytes a hook covers, then a jump back */
static fn2_t t_insert, t_pick, t_jump;

typedef struct { char *b, *e, *c; } rvec;

/* ================================ Select Team ================================ */

/* what a visible row is: a row of the game, a confederation (0..NG-1), a country, the way back */
#define K_GAME  (-1)
#define K_CTRY  100                        /* + country id */
#define K_BACK  (-2)
#define K_FOLD  4096                       /* + folder id */
typedef struct {
  char* obj;
  rvec master;               /* every row the game built, in its order (owned, game memory) */
  char* vis_b;               /* the visible vector after the last rebuild: begin, count */
  uint64_t vis_n;
  int open;                  /* the open group, -1 none (the confederations) */
  int ctry;                  /* the open country of the open group, -1 none (its countries) */
  int fold;                  /* the open folder of the open country, 0 none (the country's own level) */
  uint16_t fcnt[NFOLD];      /* leagues under each folder (its sub-folders' too) in the master rows */
  uint16_t fslot[NFOLD];     /* its first league's slot: the folder row's flag, emblem and League Info */
  int nmem[NG];
  uint16_t ccnt[NCTRY];      /* leagues of each country in the master rows */
  uint16_t cslot[NCTRY];     /* its first league's slot: the country row's flag and League Info */
  int16_t kind[MAXR];        /* visible row -> K_GAME, a group, K_CTRY + country, K_BACK */
} tstate;
static tstate g_ts[8];
/* lists whose init came before their rows (Kick Off: init on an empty vector, the leagues added
 * after it): taken by the insert that brings enough rows, or by the game's cursor */
static char* g_ts_pending[8];

static void ts_pend(char* t, int on)
{
  for (int i = 0; i < 8; i++) if (g_ts_pending[i] == t) { if (!on) g_ts_pending[i] = 0; return; }
  if (on) for (int i = 0; i < 8; i++) if (!g_ts_pending[i]) { g_ts_pending[i] = t; return; }
}

static int ts_pending(char* t)
{
  for (int i = 0; i < 8; i++) if (g_ts_pending[i] == t) return 1;
  return 0;
}
static char g_srow[ROW];
static char g_sname[96];

static uint64_t nrows(const rvec* v) { return v->b ? (uint64_t)(v->e - v->b) / ROW : 0; }
static int grp_slot(uint32_t s) { return s < 1024 ? g_slot[s] : -1; }
static int ctry_slot(uint32_t s) { return s < 1024 ? g_sctry[s] : -1; }
static int fold_slot(uint32_t s) { return s < 1024 ? g_sfold[s] : 0; }
/* the folder to show at level f for a league in folder x: x itself (0 when x == f: the league's own row), the child of
   f on x's way up, -1 when x is not under f */
static int fold_at(int x, int f)
{
  if (x == f) return 0;
  for (int i = 0; i < 16 && x; i++) { if (g_fpar[x] == f) return x; x = g_fpar[x]; }
  return -1;
}
static const char* str_of(const char* s) { return *(const uint64_t*)(s + 0x18) >= 16 ? *(char* const*)s : s; }

static void set_str(char* s, const char* txt, int n)
{
  memset(s, 0, 0x20);
  if (n <= 15) {
    memcpy(s, txt, n);
    *(uint64_t*)(s + 0x18) = 15;
  } else {                                 /* read by the game's copy only: never freed */
    *(const char**)s = txt;
    *(uint64_t*)(s + 0x18) = (uint64_t)n;
  }
  *(uint64_t*)(s + 0x10) = (uint64_t)n;
}

/* a row of ours: no clubs, the text; the game's push_back copies it (the buffers are reused) */
static const char* our_row(uint32_t slot, const char* fmt, ...)
{
  char* r = g_srow;
  memset(r, 0, ROW);
  *(uint32_t*)r = slot;
  va_list ap; va_start(ap, fmt);
  int n = vsnprintf(g_sname, sizeof g_sname, fmt, ap);
  va_end(ap);
  if (n < 0) n = 0;
  if (n > (int)sizeof g_sname - 1) n = (int)sizeof g_sname - 1;
  set_str(r + 0x20, g_sname, n);
  set_str(r + 0x40, "", 0);
  r[0x60] = 1;
  return r;
}

/* a row of ours (in a vector the game rebuilt behind our back) */
static int is_header(const char* row)
{
  if (*(char* const*)(row + 8) != *(char* const*)(row + 0x10)) return 0;    /* has clubs */
  uint32_t s = *(const uint32_t*)row;
  int any = s == HEAD_SLOT || ctry_slot(s) >= 0;
  for (int g = 0; g < NG; g++) if ((uint32_t)g_head[g] == s) any = 1;
  const char* nm = str_of(row + 0x20);
  return any && (nm[0] == '+' || nm[0] == '-') && nm[1] == ' ';
}

static tstate* ts_find(char* t)
{
  if (!t) return 0;
  for (int i = 0; i < 8; i++) if (g_ts[i].obj == t) return &g_ts[i];
  return 0;
}

static int ts_valid(tstate* s)
{
  rvec* vis = (rvec*)(s->obj + 0x100);
  return vis->b == s->vis_b && nrows(vis) == s->vis_n;
}

static void ts_drop(tstate* s)
{
  if (s->master.b) ((vecop_t)VA(ROWS_FREE))(&s->master);
  memset(s, 0, sizeof *s);
}

static uint64_t ts_cur(char* t) { return (uint64_t)*(uint32_t*)(t + 0x118) + *(uint32_t*)(t + 0x11c); }

/* the cursor on visible row idx; live: in the list widget too (what 0x140c942a0 does) */
static void ts_cursor(char* t, uint64_t idx, int live)
{
  int32_t off = *(int32_t*)(t + 0x11c);
  if (off < 0 || (uint64_t)off > idx) { off = 0; *(int32_t*)(t + 0x11c) = 0; }
  *(uint32_t*)(t + 0x118) = (uint32_t)(idx - (uint64_t)off);
  *(uint8_t*)(t + 0x99) |= 6;
  if (live && !*(uint8_t*)(t + 0x9b))
    ((list_set_t)VA(LIST_SET))(t, *(uint32_t*)(t + 0xf4), *(uint32_t*)(t + 0x11c), 0, 0.0f, 0.0f);
}

/* the rows of each group and country, and each country's first slot */
static void ts_count(tstate* s)
{
  memset(s->nmem, 0, sizeof s->nmem);
  memset(s->ccnt, 0, sizeof s->ccnt);
  for (uint64_t i = 0; i < nrows(&s->master); i++) {
    uint32_t slot = *(uint32_t*)(s->master.b + i * ROW);
    int g = grp_slot(slot), c = ctry_slot(slot);
    if (g < 0) continue;
    s->nmem[g]++;
    if (c >= 0 && !s->ccnt[c]++) s->cslot[c] = (uint16_t)slot;
  }
  memset(s->fcnt, 0, sizeof s->fcnt);
  for (uint64_t i = 0; i < nrows(&s->master); i++) {
    uint32_t slot = *(uint32_t*)(s->master.b + i * ROW);
    for (int x = fold_slot(slot), k = 0; x && k < 16; x = g_fpar[x], k++)
      if (!s->fcnt[x]++) s->fslot[x] = (uint16_t)slot;
  }
  if (s->fold && (s->ctry < 0 || !s->fcnt[s->fold])) s->fold = 0;
  if (s->open >= 0 && !s->nmem[s->open]) s->open = -1;
  if (s->open < 0 || s->ctry < 0 || !s->ccnt[s->ctry]) s->ctry = -1;
}

/* the visible rows from the master rows, one level at a time:
 *   no group open   the game's rows before the first grouped one, one row per confederation,
 *                   the game's other rows after them;
 *   a group open    "- UEFA" (the way back), then its countries -- a country of one league is
 *                   that league's row -- and its leagues of no country, in the game's order;
 *   a country open  "- Albania", then its leagues */
static void ts_layout(tstate* s)
{
  rvec* vis = (rvec*)(s->obj + 0x100);
  push_t push = (push_t)VA(ROWS_PUSH);
  uint64_t n = nrows(&s->master), first = n, k = 0;
  for (uint64_t i = 0; i < n; i++)
    if (grp_slot(*(uint32_t*)(s->master.b + i * ROW)) >= 0) { first = i; break; }
  ((vecop_t)VA(ROWS_CLEAR))(vis);
  if (s->open < 0) {
    for (uint64_t i = 0; i < first; i++) { push(vis, s->master.b + i * ROW); s->kind[k++] = K_GAME; }
    for (int g = 0; g < NG; g++) {
      if (!s->nmem[g]) continue;
      push(vis, our_row((uint32_t)g_head[g], "+ %s (%d)", GNAME[g], s->nmem[g]));
      s->kind[k++] = (int16_t)g;
    }
    for (uint64_t i = first; i < n; i++)
      if (grp_slot(*(uint32_t*)(s->master.b + i * ROW)) < 0) { push(vis, s->master.b + i * ROW); s->kind[k++] = K_GAME; }
  } else if (s->ctry < 0) {
    static uint8_t done[NCTRY];
    memset(done, 0, sizeof done);
    push(vis, our_row((uint32_t)g_head[s->open], "- %s", GNAME[s->open]));
    s->kind[k++] = K_BACK;
    for (uint64_t i = first; i < n; i++) {
      char* r = s->master.b + i * ROW;
      uint32_t slot = *(uint32_t*)r;
      if (grp_slot(slot) != s->open) continue;
      int c = ctry_slot(slot);
      if (c < 0) { push(vis, r); s->kind[k++] = K_GAME; continue; }
      if (done[c]) continue;
      done[c] = 1;
      push(vis, our_row(s->cslot[c], "+ %s (%d)", g_cname[c], s->ccnt[c]));
      s->kind[k++] = (int16_t)(K_CTRY + c);
    }
  } else {
    static uint8_t fdone[NFOLD];
    memset(fdone, 0, sizeof fdone);
    if (s->fold) push(vis, our_row(s->fslot[s->fold], "- %s", g_fname[s->fold]));
    else push(vis, our_row(s->cslot[s->ctry], "- %s", g_cname[s->ctry]));
    s->kind[k++] = K_BACK;
    for (uint64_t i = first; i < n; i++) {
      char* r = s->master.b + i * ROW;
      uint32_t slot = *(uint32_t*)r;
      if (grp_slot(slot) != s->open || ctry_slot(slot) != s->ctry) continue;
      int f = fold_at(fold_slot(slot), s->fold);
      if (f < 0) continue;
      if (!f) { push(vis, r); s->kind[k++] = K_GAME; continue; }
      if (fdone[f]) continue;
      fdone[f] = 1;
      push(vis, our_row(s->fslot[f], "+ %s (%d)", g_fname[f], s->fcnt[f]));
      s->kind[k++] = (int16_t)(K_FOLD + f);
    }
  }
  s->vis_b = vis->b;
  s->vis_n = nrows(vis);
  *(uint8_t*)(s->obj + 0x99) |= 6;
  if (ts_cur(s->obj) >= s->vis_n) ts_cursor(s->obj, 0, 0);
}

static int64_t ts_kind_at(tstate* s, int kind)
{
  for (uint64_t i = 0; i < s->vis_n; i++) if (s->kind[i] == kind) return (int64_t)i;
  return -1;
}

/* the visible index of the row of the game with that slot, -1 none */
static int64_t ts_slot_at(tstate* s, uint32_t slot)
{
  rvec* vis = (rvec*)(s->obj + 0x100);
  for (uint64_t i = 0; i < s->vis_n; i++)
    if (s->kind[i] == K_GAME && *(uint32_t*)(vis->b + i * ROW) == slot) return (int64_t)i;
  return -1;
}

static int64_t ts_first_ours(tstate* s)
{
  for (uint64_t i = 0; i < s->vis_n; i++) if (s->kind[i] != K_GAME) return (int64_t)i;
  return 0;
}

/* take the list's rows (at init, or again when the game changed the vector behind our back);
 * 0 when the list stays the game's: not two groups, too few grouped rows, no room.  A row of
 * ours never stays in a list this does not hold. */
static tstate* ts_take(char* t)
{
  tstate* s = ts_find(t);
  if (s && ts_valid(s)) return s;
  rvec* vis = (rvec*)(t + 0x100);
  rvec m = *vis;
  int heads = 0;
  for (uint64_t i = 0; i < nrows(&m); i++) heads += is_header(m.b + i * ROW);
  if (s) {
    trace("select team %p: the rows changed outside (%llu rows, %d of ours), taken again",
          t, (unsigned long long)nrows(&m), heads);
    ts_drop(s);
    s = 0;
  }
  if (heads) {                             /* the game's rows without ours */
    rvec f = { 0, 0, 0 };
    push_t push = (push_t)VA(ROWS_PUSH);
    for (uint64_t i = 0; i < nrows(&m); i++)
      if (!is_header(m.b + i * ROW)) push(&f, m.b + i * ROW);
    ((vecop_t)VA(ROWS_FREE))(&m);
    m = f;
    *vis = m;
    *(uint8_t*)(t + 0x99) |= 6;
    if (ts_cur(t) >= nrows(&m)) ts_cursor(t, 0, 0);
  }
  int nmem[NG] = { 0 }, groups = 0, members = 0;
  for (uint64_t i = 0; i < nrows(&m); i++) {
    int g = grp_slot(*(uint32_t*)(m.b + i * ROW));
    if (g >= 0) { if (!nmem[g]++) groups++; members++; }
  }
  if (groups < 2 || members < 6 || nrows(&m) + NG > MAXR) {
    trace("select team %p: %llu rows, %d groups, %d grouped -- left as it is",
          t, (unsigned long long)nrows(&m), groups, members);
    return 0;
  }
  for (int i = 0; i < 8 && !s; i++) if (!g_ts[i].obj) s = &g_ts[i];
  if (!s) { trace("select team %p: no free state", t); return 0; }
  memset(s, 0, sizeof *s);
  s->obj = t;
  s->open = s->ctry = -1;
  s->master = m;                           /* moved: the visible vector starts empty */
  memset(vis, 0, sizeof *vis);
  ts_count(s);
  return s;
}

static void ts_trace(tstate* s, const char* what)
{
  trace("select team %p: %s -- %s%s%s%s%s, %llu rows shown, cursor %llu", s->obj, what,
        s->open >= 0 ? GNAME[s->open] : "the confederations", s->ctry >= 0 ? " / " : "",
        s->ctry >= 0 ? g_cname[s->ctry] : "", s->fold ? " / " : "", s->fold ? g_fname[s->fold] : "",
        (unsigned long long)s->vis_n, (unsigned long long)ts_cur(s->obj));
}

/* Confirm on a row of ours: a confederation or a country in, the way back out */
static void ts_enter(tstate* s, int kind)
{
  if (kind == K_BACK && s->ctry >= 0 && s->fold) {       /* a folder: up to its parent */
    int f = s->fold;
    s->fold = g_fpar[f];
    ts_layout(s);
    ts_cursor(s->obj, (uint64_t)ts_kind_at(s, K_FOLD + f), 1);
    ts_trace(s, "back");
    return;
  }
  if (kind >= K_FOLD) {
    s->fold = kind - K_FOLD;
    ts_layout(s);
    ts_cursor(s->obj, s->vis_n > 1 ? 1 : 0, 1);
    ts_trace(s, "in");
    return;
  }
  if (kind == K_BACK) {
    int g = s->open, c = s->ctry;
    s->fold = 0;
    if (c >= 0) { s->ctry = -1; ts_layout(s); ts_cursor(s->obj, (uint64_t)ts_kind_at(s, K_CTRY + c), 1); }
    else { s->open = -1; ts_layout(s); ts_cursor(s->obj, (uint64_t)ts_kind_at(s, g), 1); }
    ts_trace(s, "back");
    return;
  }
  if (kind >= K_CTRY) { s->ctry = kind - K_CTRY; s->fold = 0; }
  else { s->open = kind; s->ctry = -1; s->fold = 0; }
  ts_layout(s);
  ts_cursor(s->obj, s->vis_n > 1 ? 1 : 0, 1);
  ts_trace(s, "in");
}

/* the level of a slot: its group open, its country too when that is a row of its own */
static void ts_level_of(tstate* s, uint32_t slot)
{
  s->open = grp_slot(slot);
  s->ctry = -1;
  s->fold = 0;
  if (s->open >= 0 && !s->nmem[s->open]) s->open = -1;
  if (s->open >= 0) s->ctry = ctry_slot(slot);
  if (s->ctry >= 0) s->fold = fold_slot(slot);
}

/* the level a row of ours stood for, by its text (a list built anew keeps the copies) */
static int ts_level_of_text(tstate* s, const char* nm, int* focus)
{
  const char* x = nm + 2;
  for (int g = 0; g < NG; g++) {
    size_t l = strlen(GNAME[g]);
    if (!strncmp(x, GNAME[g], l) && (x[l] == 0 || x[l] == ' ')) {
      if (nm[0] == '+') { s->open = -1; s->ctry = -1; *focus = g; }
      else { s->open = g; s->ctry = -1; *focus = K_BACK; }
      return 1;
    }
  }
  for (uint64_t i = 0; i < nrows(&s->master); i++) {
    uint32_t slot = *(uint32_t*)(s->master.b + i * ROW);
    int c = ctry_slot(slot);
    if (c < 0) continue;
    size_t l = strlen(g_cname[c]);
    if (strncmp(x, g_cname[c], l) || (x[l] != 0 && x[l] != ' ')) continue;
    s->open = grp_slot(slot);
    s->fold = 0;
    if (nm[0] == '+') { s->ctry = -1; *focus = K_CTRY + c; }
    else { s->ctry = c; *focus = K_BACK; }
    return 1;
  }
  for (int f = 1; f < NFOLD; f++) {        /* a folder's row */
    size_t l = strlen(g_fname[f]);
    if (!l || strncmp(x, g_fname[f], l) || (x[l] != 0 && x[l] != ' ')) continue;
    for (uint64_t i = 0; i < nrows(&s->master); i++) {
      uint32_t slot = *(uint32_t*)(s->master.b + i * ROW);
      if (fold_at(fold_slot(slot), g_fpar[f]) != f) continue;
      s->open = grp_slot(slot); s->ctry = ctry_slot(slot);
      if (nm[0] == '+') { s->fold = g_fpar[f]; *focus = K_FOLD + f; }
      else { s->fold = f; *focus = K_BACK; }
      return 1;
    }
  }
  return 0;
}

/* +0xd8: the rows grouped before the game's init enters the league column */
static uint64_t ts_init(char* t, uint64_t a)
{
  uint64_t cur = ts_cur(t);
  rvec* vis = (rvec*)(t + 0x100);
  int at_slot = -1;
  char at_text[96] = "";
  if (cur < nrows(vis)) {
    char* r = vis->b + cur * ROW;
    if (is_header(r)) snprintf(at_text, sizeof at_text, "%s", str_of(r + 0x20));
    else at_slot = (int)*(uint32_t*)r;
  }
  int club_col = *(uint8_t*)(t + 0x9b) != 0;
  tstate* fresh = ts_find(t);
  int was_valid = fresh && ts_valid(fresh);
  tstate* s = ts_take(t);
  ts_pend(t, !s);
  if (s && !was_valid) {
    /* a row the game put the cursor on (a team picked before, the club column) opens its
     * level; row 0 of a list nobody moved stays on the confederations, the cursor on the first */
    int focus = K_GAME;
    int64_t to = -1;
    if (at_slot >= 0 && (cur > 0 || club_col)) ts_level_of(s, (uint32_t)at_slot);
    if (at_text[0] && !ts_level_of_text(s, at_text, &focus)) focus = K_GAME;
    ts_layout(s);
    if (at_slot >= 0) to = ts_slot_at(s, (uint32_t)at_slot);
    if (focus != K_GAME) to = ts_kind_at(s, focus);
    if (to < 0) to = ts_first_ours(s);
    ts_cursor(t, (uint64_t)to, 0);
    trace("select team %p: init, %llu rows -> %llu shown (%d %d %d %d %d %d), cursor %lld",
          t, (unsigned long long)nrows(&s->master), (unsigned long long)s->vis_n, s->nmem[0], s->nmem[1],
          s->nmem[2], s->nmem[3], s->nmem[4], s->nmem[5], (long long)to);
    ts_trace(s, "init");
  }
  return ((fn2_t)VA(TSC_INIT))(t, a);
}

/* +0x188 */
static uint64_t ts_decide(char* t, uint64_t a)
{
  if (!*(uint8_t*)(t + 0x9b)) {
    tstate* s = ts_find(t);
    if (s) s = ts_take(t);
    if (s) {
      uint64_t cur = ts_cur(t);
      if (cur < s->vis_n && s->kind[cur] != K_GAME) {
        *(uint8_t*)(t + 0x9c) = 0;
        ts_enter(s, s->kind[cur]);
        return 0;
      }
    }
  }
  return ((fn2_t)VA(TSC_DECIDE))(t, a);
}

/* +0x190: Back one level; on the confederations, the game's */
static uint64_t ts_cancel(char* t, uint64_t a)
{
  if (!*(uint8_t*)(t + 0x9b)) {
    tstate* s = ts_find(t);
    if (s) s = ts_take(t);
    if (s && s->open >= 0) {
      *(uint8_t*)(t + 0x9c) = 0;
      ts_enter(s, K_BACK);
      return 0;
    }
  }
  return ((fn2_t)VA(TSC_CANCEL))(t, a);
}

/* +0x18 */
static uint64_t ts_dtor(char* t, uint64_t a)
{
  tstate* s = ts_find(t);
  if (s) ts_drop(s);
  ts_pend(t, 0);
  return ((fn2_t)VA(TSC_DTOR))(t, a);
}

/* a list of the pending ones with its rows in now: taken, on the confederations' level */
static tstate* ts_late(char* t)
{
  if (!ts_pending(t)) return 0;
  tstate* s = ts_take(t);
  if (!s) return 0;
  ts_pend(t, 0);
  s->open = s->ctry = -1;
  ts_layout(s);
  ts_cursor(t, (uint64_t)ts_first_ours(s), 0);
  trace("select team %p: taken after init, %llu rows -> %llu shown", t,
        (unsigned long long)nrows(&s->master), (unsigned long long)s->vis_n);
  return s;
}

/* 0x140c934f0: a row added after init goes into the master rows */
static uint64_t ts_insert(char* t, uint64_t row)
{
  tstate* s = ts_find(t);
  if (s) s = ts_take(t);
  if (!s) {
    uint64_t r = t_insert(t, row);
    ts_late(t);
    return r;
  }
  rvec* vis = (rvec*)(t + 0x100);
  uint64_t cur = ts_cur(t);
  int hk = cur < s->vis_n ? s->kind[cur] : K_GAME;
  uint32_t cslot = cur < s->vis_n && hk == K_GAME ? *(uint32_t*)(vis->b + cur * ROW) : 0xffffffffu;
  rvec keep = *vis;
  *vis = s->master;
  uint64_t r = t_insert(t, row);
  s->master = *vis;
  *vis = keep;
  if (nrows(&s->master) + NG > MAXR) {     /* no room: the game's own list again, every row */
    ((vecop_t)VA(ROWS_FREE))(vis);
    *vis = s->master;
    memset(&s->master, 0, sizeof s->master);
    s->obj = 0;
    *(uint8_t*)(t + 0x99) |= 6;
    if (ts_cur(t) >= nrows(vis)) ts_cursor(t, 0, 0);
    trace("select team %p: more than %d rows, the game's list again", t, MAXR - NG);
    return r;
  }
  ts_count(s);
  ts_layout(s);
  int64_t to = hk != K_GAME ? ts_kind_at(s, hk) : ts_slot_at(s, cslot);
  ts_cursor(t, (uint64_t)(to >= 0 ? to : ts_first_ours(s)), 0);
  trace("select team %p: a row added after init (slot %u), %llu rows", t,
        row ? *(uint32_t*)(uintptr_t)row : 0, (unsigned long long)nrows(&s->master));
  return r;
}

/* the game puts the cursor on a team or a slot: that row's level first, so the game finds it */
static void ts_open_for(tstate* s, uint32_t slot)
{
  int g = grp_slot(slot);
  if (g < 0 || !s->nmem[g]) {
    if (s->open < 0) return;
    s->open = s->ctry = -1; s->fold = 0;   /* a row of no group: on the confederations' level */
  } else {
    int c = ctry_slot(slot), f = c >= 0 ? fold_slot(slot) : 0;
    if (s->open == g && s->ctry == c && s->fold == f) return;
    s->open = g;
    s->ctry = c;
    s->fold = f;
  }
  ts_layout(s);
  ts_trace(s, "for the game's own cursor");
}

/* 0x140c94330: the game puts the cursor on a team */
static uint64_t ts_pick(char* t, uint64_t team)
{
  tstate* s = ts_find(t);
  if (s) s = ts_take(t);
  else s = ts_late(t);
  if (s) {
    uint32_t id = (uint32_t)team;
    uint64_t n = nrows(&s->master);
    for (uint64_t i = 0; i < n; i++) {
      char* r = s->master.b + i * ROW;
      char *cb = *(char**)(r + 8), *ce = *(char**)(r + 0x10);
      int hit = 0;
      for (char* c = cb; c && c < ce; c += 0x50) if (*(uint32_t*)c == id) { hit = 1; break; }
      if (hit) { ts_open_for(s, *(uint32_t*)r); break; }
    }
  }
  return t_pick(t, team);
}

/* 0x140c942a0: the game puts the cursor on a slot */
static uint64_t ts_jump(char* t, uint64_t slot)
{
  tstate* s = ts_find(t);
  if (s) s = ts_take(t);
  else s = ts_late(t);
  if (s) ts_open_for(s, (uint32_t)slot);
  return t_jump(t, slot);
}

/* ============================== Competition Info ============================== */

typedef struct {
  char* obj;
  uint32_t* master;          /* the game's regions, in its order (ours, HeapAlloc) */
  uint32_t mn;
  uint32_t* vis_b;           /* the vector after the last rebuild */
  uint32_t vis_n;
  int open;
  int nmem[NG];
} cstate;
static cstate g_cs[4];
static int g_ci_open = -1;                 /* the open group of the last layout (the labels) */
static uint32_t g_ci_last = 0xffffffffu;   /* the last region entered */

static int grp_reg(uint32_t r) { return r < 256 ? g_reg[r] : -1; }
static int is_pseudo(uint32_t r) { return r >= PSEUDO && r < PSEUDO + NG; }
typedef struct { uint32_t *b, *e, *c; } uvec;

static cstate* cs_find(char* t)
{
  for (int i = 0; i < 4; i++) if (g_cs[i].obj == t) return &g_cs[i];
  return 0;
}
static int cs_valid(cstate* s)
{
  uvec* v = (uvec*)(s->obj + 0x90);
  return v->b == s->vis_b && (uint32_t)(v->e - v->b) == s->vis_n;
}
static void cs_drop(cstate* s)
{
  if (s->master) HeapFree(GetProcessHeap(), 0, s->master);
  memset(s, 0, sizeof *s);
}

/* no group open: the game's categories before the first grouped one, one per confederation,
 * the others after them; a group open: "- UEFA" (the way back), then its countries only */
static void cs_layout(cstate* s)
{
  uvec* v = (uvec*)(s->obj + 0x90);
  uint32_t need = s->mn + NG, first = s->mn, k = 0;
  if (!v->b || (uint64_t)(v->c - v->b) < need) ((reserve_t)VA(CI_RESERVE))(v, need);
  for (uint32_t i = 0; i < s->mn; i++) if (grp_reg(s->master[i]) >= 0) { first = i; break; }
  if (s->open < 0) {
    for (uint32_t i = 0; i < first; i++) v->b[k++] = s->master[i];
    for (int g = 0; g < NG; g++) if (s->nmem[g]) v->b[k++] = PSEUDO + (uint32_t)g;
    for (uint32_t i = first; i < s->mn; i++) if (grp_reg(s->master[i]) < 0) v->b[k++] = s->master[i];
  } else {
    v->b[k++] = PSEUDO + (uint32_t)s->open;
    for (uint32_t i = first; i < s->mn; i++) if (grp_reg(s->master[i]) == s->open) v->b[k++] = s->master[i];
  }
  v->e = v->b + k;
  s->vis_b = v->b;
  s->vis_n = k;
  g_ci_open = s->open;
}

static int64_t cs_index_of(cstate* s, uint32_t r)
{
  for (uint32_t i = 0; i < s->vis_n; i++) if (s->vis_b[i] == r) return i;
  return -1;
}

/* the game's own redraw of the grid, the cursor on idx */
static void cs_redraw(cstate* s, int64_t idx)
{
  char* t = s->obj;
  if (idx < 0 || (uint64_t)idx >= s->vis_n) idx = 0;
  ((fn1_t)VA(CI_CELLS))(t);
  ((count_t)VA(CI_COUNT))(t, 0, s->vis_n, 1, 0);
  uint32_t list = ((cur_list_t)VA(CUR_LIST))(t);
  ((list_set_t)VA(LIST_SET))(t, list, (uint32_t)idx, 0, 0.0f, 0.0f);
  if (s->vis_n) ((fn2_t)VA(CI_PREVIEW))(t, s->vis_b[idx]);
}

/* in (g >= 0) or back out (-1) */
static void cs_go(cstate* s, int g)
{
  int was = s->open;
  s->open = g;
  cs_layout(s);
  int64_t to = g >= 0 ? (s->vis_n > 1 ? 1 : 0) : cs_index_of(s, PSEUDO + (uint32_t)was);
  cs_redraw(s, to);
  trace("competition info %p: %s %s, %u shown, cursor %lld", s->obj, g >= 0 ? "in" : "back from",
        GNAME[g >= 0 ? g : was], s->vis_n, (long long)to);
}

/* +0xd8: after the game's init */
static uint64_t ci_init(char* t, uint64_t a)
{
  uint64_t ret = ((fn2_t)VA(CI_INIT))(t, a);
  cstate* s = cs_find(t);
  if (s) cs_drop(s);
  uvec* v = (uvec*)(t + 0x90);
  uint32_t n = v->b ? (uint32_t)(v->e - v->b) : 0;
  int nmem[NG] = { 0 }, groups = 0, members = 0;
  for (uint32_t i = 0; i < n; i++) {
    int g = grp_reg(v->b[i]);
    if (g >= 0) { if (!nmem[g]++) groups++; members++; }
  }
  if (groups < 2 || members < 6 || n + NG > MAXC) {
    trace("competition info %p: %u categories, %d groups, %d grouped -- left as it is", t, n, groups, members);
    return ret;
  }
  for (int i = 0; i < 4 && !s; i++) if (!g_cs[i].obj) s = &g_cs[i];
  if (!s) { trace("competition info %p: no free state", t); return ret; }
  uint32_t* m = (uint32_t*)HeapAlloc(GetProcessHeap(), 0, (n + 1) * sizeof *m);
  if (!m) return ret;
  uint32_t mn = 0;
  for (uint32_t i = 0; i < n; i++) if (!is_pseudo(v->b[i])) m[mn++] = v->b[i];
  memset(s, 0, sizeof *s);
  s->obj = t;
  s->master = m;
  s->mn = mn;
  s->open = -1;
  memcpy(s->nmem, nmem, sizeof nmem);
  int lg = grp_reg(g_ci_last);              /* back from a category: in its group again */
  int64_t to = -1;
  if (lg >= 0 && s->nmem[lg]) s->open = lg;
  cs_layout(s);
  if (s->open >= 0) to = cs_index_of(s, g_ci_last);
  for (uint32_t i = 0; to < 0 && i < s->vis_n; i++) if (is_pseudo(s->vis_b[i])) to = i;
  cs_redraw(s, to);
  trace("competition info %p: init, %u categories -> %u shown (%d %d %d %d %d %d), %s open, cursor %lld",
        t, mn, s->vis_n, nmem[0], nmem[1], nmem[2], nmem[3], nmem[4], nmem[5],
        s->open >= 0 ? GNAME[s->open] : "none", (long long)to);
  return ret;
}

/* +0x188 */
static uint64_t ci_decide(char* t, uint64_t a)
{
  cstate* s = cs_find(t);
  if (s && cs_valid(s)) {
    uint32_t list = ((cur_list_t)VA(CUR_LIST))(t);
    uint32_t idx = ((cur_index_t)VA(CUR_INDEX))(t, list);
    if (idx < s->vis_n) {
      uint32_t r = s->vis_b[idx];
      if (is_pseudo(r)) {
        int g = (int)(r - PSEUDO);
        cs_go(s, s->open == g ? -1 : g);
        return 0;
      }
      g_ci_last = r;
    }
  }
  return ((fn2_t)VA(CI_DECIDE))(t, a);
}

/* +0x190: Back from a confederation to the confederations; there, the game's */
static uint64_t ci_cancel(char* t, uint64_t a)
{
  cstate* s = cs_find(t);
  if (s && cs_valid(s) && s->open >= 0) {
    cs_go(s, -1);
    g_ci_last = 0xffffffffu;
    return 0;
  }
  if (s) g_ci_last = 0xffffffffu;          /* left the screen: it opens on the confederations */
  return ((fn2_t)VA(CI_CANCEL))(t, a);
}

/* +0x18 */
static uint64_t ci_dtor(char* t, uint64_t a)
{
  cstate* s = cs_find(t);
  if (s) cs_drop(s);
  return ((fn2_t)VA(CI_DTOR))(t, a);
}

/* the call at 0x140acd5e9, the right side's competitions of a region (0x1415789c0(&region, &vector
 * of u16)): a confederation gets the club competitions' (region 1) that are its own -- its
 * continental cups and the Club World Cup, the `cups` of the world line (mato 08.11.: "samo
 * kontinentalne kupove ... a ne ove bakrac kupove. E da i klupski spk") -- the vector the game's
 * own, only shortened.  The vector holds regulation ids, so each is kept by its record's
 * competition id (+0x80); comparing the regulation id itself with `cups` showed the regulations
 * 1 and 5 on + CONMEBOL: the Club World Cup and the Europa League's league phase (mato, 17.11.) */
typedef struct { uint16_t *b, *e, *c; } hvec;
static uint16_t g_cups[NG][16];
static int g_ncups[NG];
static uint32_t reg_cid(void* data, uint16_t rid)
{
  const char* rec = data ? ((reg_find_t)VA(REG_FIND))(data, rid) : 0;
  return rec && *(const uint16_t*)rec == rid ? *(const uint32_t*)(rec + REG_CID) : 0;
}
static void* cg_comps(uint32_t* region, hvec* out)
{
  if (!region || !is_pseudo(*region)) return ((comps_t)VA(REGION_COMPS))(region, out);
  int g = (int)(*region - PSEUDO);
  uint32_t club = CLUB_REGION;
  void* r = ((comps_t)VA(REGION_COMPS))(&club, out);
  char* game = ((game_t)VA(GAME_FN))();
  void* data = game ? *(void**)(game + GAME_DATA) : 0;
  uint16_t* k = out->b;
  for (uint16_t* p = out->b; p && p < out->e; p++) {
    uint32_t cid = reg_cid(data, *p);
    int keep = 0;
    for (int i = 0; cid && i < g_ncups[g]; i++) if (g_cups[g][i] == cid) keep = 1;
    if (keep) *k++ = *p;
  }
  if (out->b) out->e = k;
  trace("competition info: the right side of %s, %d competitions", GNAME[g], out->b ? (int)(k - out->b) : 0);
  return r;
}

/* the label of a category cell (the call at 0x140acd4ef) */
static char g_lname[NG][24];
static void* cg_label(void* out, uint32_t region)
{
  if (!is_pseudo(region)) return ((label_t)VA(LABEL_FN))(out, region);
  int g = (int)(region - PSEUDO);
  int n = snprintf(g_lname[g], sizeof g_lname[g], "%s %s", g_ci_open == g ? "-" : "+", GNAME[g]);
  char src[0x20];
  set_str(src, g_lname[g], n);
  char* o = (char*)out;
  memset(o, 0, 0x20);
  *(uint64_t*)(o + 0x18) = 15;
  ((assign_t)VA(STR_ASSIGN))(o, src, 0, ~0ULL);
  return out;
}

/* a row's emblem (the call at 0x140c97417; path is the row's +0x40).  A confederation's row of
 * ours with an emblem from the world line (`emblems`): the competition emblem of that id, as the
 * game draws a league's (the branch of 0x140c96090 for a slot with a competition) -- the files
 * emb_<id>*.png Mod Studio writes into the world.  Any other row: the game's. */
static void cg_emblem(void* img, void* frame, uint32_t slot, void* path)
{
  const char* row = (const char*)path - 0x40;
  if (img && frame && is_header(row)) {
    const char* nm = str_of(row + 0x20) + 2;
    for (int f = 1; f < NFOLD; f++) {      /* lab 23/11/2026: a folder with an emblem of its own */
      size_t k = strlen(g_fname[f]);
      if (!g_femb[f] || !k || strncmp(nm, g_fname[f], k) || (nm[k] && nm[k] != ' ')) continue;
      ((img_show_t)VA(IMG_SHOW))(img, 1, 2);
      ((img_show_t)VA(IMG_SHOW))(frame, 0, 2);
      *((unsigned char*)img + 0x1c4) = 1;
      uint32_t cid = (uint32_t)g_femb[f];
      uint32_t size = ((img_size_t)VA(IMG_SIZE))(img, &cid);
      ((img_comp_t)VA(IMG_COMP))(img, cid, size, 0);
      return;
    }
    for (int g = 0; g < NG; g++) {
      size_t k = strlen(GNAME[g]);
      if (!g_emb[g] || (uint32_t)g_head[g] != slot || strncmp(nm, GNAME[g], k) || (nm[k] && nm[k] != ' ')) continue;
      ((img_show_t)VA(IMG_SHOW))(img, 1, 2);
      ((img_show_t)VA(IMG_SHOW))(frame, 0, 2);
      *((unsigned char*)img + 0x1c4) = 1;
      uint32_t cid = (uint32_t)g_emb[g];
      uint32_t size = ((img_size_t)VA(IMG_SIZE))(img, &cid);
      ((img_comp_t)VA(IMG_COMP))(img, cid, size, 0);
      return;
    }
  }
  ((row_emblem_t)VA(ROW_EMBLEM))(img, frame, slot, path);
}

/* the confederation of the row under the cursor of a list of ours, -1 when it is no confederation's
 * row ("+ UEFA (164)"; "- UEFA" while UEFA's countries are shown; not a country's "- Albania") */
static int ts_row_group(char* t)
{
  tstate* s = ts_find(t);
  if (!s || !ts_valid(s) || *(uint8_t*)(t + 0x9b)) return -1;
  uint64_t cur = ts_cur(t);
  if (cur >= s->vis_n) return -1;
  int k = s->kind[cur];
  if (k >= 0 && k < NG) return k;
  if (k == K_BACK && s->open >= 0 && s->ctry < 0) return s->open;
  return -1;
}

/* League Info (the call at 0x140c98bcf; t is the panel's list model).  info: +0 the league (-1:
 * the panel is not filled), +4 six competition ids (-1: that emblem hidden), +0x1c the league
 * above, +0x20 the league below (-1: none).  A confederation's row: its continental cups, the
 * world line's `cups` of the group without the Club World Cup, in that order; no league above or
 * below.  Any other row: the game's. */
static uint32_t* cg_info(uint32_t* info, uint32_t league, char* t)
{
  uint32_t* r = ((info_t)VA(INFO_FN))(info, league);
  int g = ts_row_group(t);
  if (g < 0 || !r) return r;
  int n = 0;
  for (int i = 0; i < g_ncups[g] && n < INFO_ICONS; i++)
    if (g_cups[g][i] != CWC_CID) r[1 + n++] = g_cups[g][i];
  for (int i = n; i < INFO_ICONS; i++) r[1 + i] = 0xffffffffu;
  r[7] = r[8] = 0xffffffffu;
  if (r[0] == 0xffffffffu) r[0] = 0;       /* a row with no league: the panel is still filled */
  trace("league info: %s, %d continental cups", GNAME[g], n);
  return r;
}

/* League Info's update (the call at 0x140c98f8a; panel is its this): the game redraws the panel
 * only when the slot under the cursor changes, and every confederation's row has the same slot
 * (HEAD_SLOT), so from "+ UEFA" to "+ CONMEBOL" it kept UEFA's cups.  When the row's confederation
 * changes (or the panel), the slot it remembers is spoiled, so it compares unequal and redraws. */
static char* g_li_panel;
static int g_li_group = -1;
static uint32_t cg_slot(char* t, uint64_t unused, char* panel)
{
  (void)unused;
  uint32_t slot = ((slot_fn_t)VA(SLOT_FN))(t);
  int g = ts_row_group(t);
  if (panel && (panel != g_li_panel || g != g_li_group)) {
    if (g >= 0 || g_li_group >= 0) {
      *(uint32_t*)(panel + INFO_LAST) = ~slot;
      trace("league info: redraw, %s -> %s", g_li_group >= 0 ? GNAME[g_li_group] : "-", g >= 0 ? GNAME[g] : "-");
    }
    g_li_panel = panel;
    g_li_group = g;
  }
  return slot;
}

/* ================================== install ================================== */

static unsigned char* near_alloc(uint64_t exe_base)
{
  for (uint64_t a = (exe_base & ~0xffffULL) - 0x10000; a > exe_base - 0x70000000ULL; a -= 0x10000) {
    void* p = VirtualAlloc((void*)(uintptr_t)a, 0x1000, MEM_COMMIT|MEM_RESERVE, PAGE_EXECUTE_READWRITE);
    if (p) return (unsigned char*)p;
  }
  return 0;
}

static int put_bytes(unsigned char* at, const unsigned char* b, int len)
{
  DWORD old;
  if (!VirtualProtect(at, len, PAGE_EXECUTE_READWRITE, &old)) return 0;
  memcpy(at, b, len);
  VirtualProtect(at, len, old, &old);
  FlushInstructionCache(GetCurrentProcess(), at, len);
  return 1;
}

static int put_qword(uint64_t va, uint64_t v) { return put_bytes((unsigned char*)(uintptr_t)va, (unsigned char*)&v, 8); }

/* mov rax, imm64; jmp rax */
static int jmp_rax(unsigned char* s, int n, uint64_t to)
{
  s[n++] = 0x48; s[n++] = 0xb8; *(uint64_t*)(s + n) = to; n += 8;
  s[n++] = 0xff; s[n++] = 0xe0;
  return n;
}
/* jmp [rip+0]; dq to */
static int jmp_abs(unsigned char* s, int n, uint64_t to)
{
  s[n++] = 0xff; s[n++] = 0x25; *(uint32_t*)(s + n) = 0; n += 4; *(uint64_t*)(s + n) = to; n += 8;
  return n;
}

static int path_is_fl27(const char* p)
{
  const char* b = p + strlen(p);
  while (b > p && b[-1] != '\\' && b[-1] != '/') b--;
  return _stricmp(b, "FL_2027.exe") == 0;
}

static int exe_is_fl27(void)
{
  char p[MAX_PATH + 1];
  DWORD k = GetModuleFileNameA(NULL, p, MAX_PATH);
  if (!k || k >= MAX_PATH) return 0;
  p[k] = 0;
  return path_is_fl27(p);
}

/* the first bytes of every function this calls or hooks (FL 2027 1.00) */
static const struct { uint64_t va; const char* hex; const char* what; } SIGS[] = {
  { TSC_INIT,   "48895c240848896c24104889", "Select Team init" },
  { TSC_DECIDE, "40574883ec4048c7442420fe", "Select Team decide" },
  { TSC_CANCEL, "40534883ec4048c7442420fe", "Select Team cancel" },
  { TSC_DTOR,   "48895c2408574883ec208bda", "Select Team dtor" },
  { ROWS_CLEAR, "48895c240848897424105748", "rows clear" },
  { ROWS_PUSH,  "40574883ec3048c7442420fe", "rows push_back" },
  { ROWS_FREE,  "48895c2418574883ec20488b", "rows free" },
  { TSC_INSERT, "405556574154415541564157", "rows sorted insert" },
  { TSC_PICK,   "4889742418574883ec308b05", "cursor on a team" },
  { TSC_JUMP,   "4883ec38488b81000100004533c9", "cursor on a slot" },
  { LIST_SET,   "48895c2408574883ec20410f", "list cursor" },
  { CI_INIT,    "48894c240855535657415441", "Competition Info init" },
  { CI_DECIDE,  "48895c2410574883ec40ba01", "Competition Info decide" },
  { CI_DTOR,    "48895c2408574883ec208bda", "Competition Info dtor" },
  { CI_CANCEL,  "ba02000000e9c6a11900", "the menus' Back" },
  { CI_CELLS,   "4889742410574883ec20488b", "Competition Info cells" },
  { CI_COUNT,   "405556415541564883ec4848", "list item count" },
  { CI_PREVIEW, "405556574154415541564157488d", "Competition Info preview" },
  { CI_RESERVE, "40565741564883ec4048c744", "regions reserve" },
  { CUR_LIST,   "488b81880000008b80a00000", "current list" },
  { CUR_INDEX,  "4883ec28488b898800000048", "list index" },
  { LABEL_FN,   "405556574881eca000000048", "category name" },
  { LABEL_CALL, "e8ccb2aa00904533c94533c0", "the category name's call" },
  { STR_ASSIGN, "48895c240848897424104889", "string assign" },
  { REGION_COMPS, "4889542410555356574154415541", "a region's competitions" },
  { COMPS_CALL, "e8d2b3aa00e86d949e00", "the right side's call of it" },
  { ROW_EMBLEM, "4885c90f84e5010000555356", "a row's emblem" },
  { EMBLEM_CALL, "e874ecffff418b0f", "the row emblem's call" },
  { IMG_SHOW,   "84d2740b4409410c488b0148", "show an image" },
  { IMG_SIZE,   "48895c240848897424184889", "an emblem's size" },
  { IMG_COMP,   "405355565741564881ecc000", "a competition's emblem" },
  { INFO_FN,    "488bc4554154415541564157", "League Info's competitions" },
  { INFO_CALL,  "e8dc40fdff0f1000", "League Info's call of it" },
  { SLOT_FN,    "448b811c010000", "the slot under the cursor" },
  { SLOT_CALL,  "e811c0ffff8be84080fe01", "League Info's update's call of it" },
  { INFO_THIS,  "488bf9e8ef541a00488bd8ba01000000488bcfe83f4d1a00488bf0488b8f98000000", "League Info's this" },
  { GAME_FN,    "488b05a9f32402c3", "the game" },
  { REG_FIND,   "40534883ec20b8ffff0000440fb7c2488bd9663b", "a regulation by id" },
};

static int hexeq(uint64_t va, const char* hex)
{
  const unsigned char* p = (const unsigned char*)(uintptr_t)VA(va);
  for (int i = 0; hex[2 * i]; i++) {
    unsigned v;
    if (sscanf(hex + 2 * i, "%2x", &v) != 1 || p[i] != (unsigned char)v) return 0;
  }
  return 1;
}

/* the sites this DLL writes, or whose bytes it copies or relies on inside the code: the game's
 * bytes exactly.  Every other entry of SIGS is a function it only calls. */
static const uint64_t OWN[] = { TSC_INSERT, TSC_PICK, TSC_JUMP, LABEL_CALL, COMPS_CALL, EMBLEM_CALL,
                                INFO_CALL, SLOT_CALL, INFO_THIS };
static int own_site(uint64_t va)
{
  for (unsigned i = 0; i < sizeof OWN / sizeof OWN[0]; i++) if (OWN[i] == va) return 1;
  return 0;
}
/* a SIGS entry is there: its bytes are the game's, or -- a function this only calls -- another
 * module has put its jump on the entry (`jmp rel32`, then nop / int3 padding over the rest of the
 * instructions it moved) and the bytes after that are the game's.  fl26compcache does that to
 * 0x1414bb000 (`e9 rel32 90`, loaded before this one): the call then goes through its index of the
 * regulation ids, which answers the same record (beta4p 17.11.: "off bytes at 0x1414bb000").
 * 1 the game's, 2 behind another module's jump, 0 neither. */
static int sig_state(uint64_t va, const char* hex)
{
  if (hexeq(va, hex)) return 1;
  if (own_site(va)) return 0;
  const unsigned char* p = (const unsigned char*)(uintptr_t)VA(va);
  int n = (int)strlen(hex) / 2, k = 5;
  if (p[0] != 0xe9) return 0;
  while (k < n && (p[k] == 0x90 || p[k] == 0xcc)) k++;
  return k < n && hexeq(va + k, hex + 2 * k) ? 2 : 0;
}

/* ---- the numbers of a club's three lines (Select Team: attack, midfield, defence) ----
 *
 * 0x1415089e0 makes each of them: x from the best players of the line, then
 * `y = x > 100 ? 100 : max(50.0, x)` and `shown = (y - 20) * 9/7 + 0.5`.  50 gives 39, so a club
 * whose players are rated 41-48 shows 39 / 39 / 39, like every other weak club.
 *
 *   141508af6  f3 0f 10 05 32 63 03 01   movss  xmm0, [0x14253ee30]   100.0
 *   141508afe  0f 2f c8                  comiss xmm1, xmm0            xmm1 = x
 *   141508b01  77 0c                     ja     0x141508b0f
 *   141508b03  f3 0f 10 05 29 33 09 01   movss  xmm0, [0x14259be34]   50.0, the floor
 *   141508b0b  f3 0f 5f c1               maxss  xmm0, xmm1
 *
 * The low byte of that second movss's disp32 (0x141508b07), 0x29 -> 0x21, makes it read the 40.0
 * that sits eight bytes before the 50.0 in .rdata (0x14259be2c).  The floor is then 40, the
 * game's own lowest player rating, which shows as 26; from x = 50 up (39 and more on the screen)
 * nothing changes.  The 50.0 itself is read by over a thousand other instructions and stays.
 * The clamp stays too: without one a line of nobody would go negative and come out as 100.
 * The function is reached from two menu panels only (Select Team, and the next match's panel
 * in a career), so this is what is shown, not what is played.
 *
 * FL_2027.exe only (mato 11.11.: not FL26, though FL_2026.exe has the same bytes there).  The 25
 * bytes above are checked first; anything else there and nothing is written, the game keeps its
 * 39.  It neither needs the lists above nor touches them: the loader asks for it before it reads
 * the world's line, since a world of one confederation has no line and still has weak clubs. */
#define NUM_SIG      0x141508af6
#define NUM_BYTE     0x141508b07
#define NUM_SIG_HEX  "f30f1005326303010f2fc8770cf30f100529330901f30f5fc1"
#define NUM_DONE_HEX "f30f1005326303010f2fc8770cf30f100521330901f30f5fc1"
#define NUM_NEW      0x21

/* 0 written (or it already was); 1 not FL 2027 (nothing read, nothing written); 2 the bytes are
   not FL 2027 1.00's (nothing written); 4 VirtualProtect */
static int num_floor(int fl27)
{
  static const unsigned char b = NUM_NEW;
  if (!fl27) { logf("confgroups: team numbers: off not FL 2027"); return 1; }
  if (hexeq(NUM_SIG, NUM_DONE_HEX)) { logf("confgroups: team numbers: ok (already written)"); return 0; }
  if (!hexeq(NUM_SIG, NUM_SIG_HEX)) {
    logf("confgroups: team numbers: off bytes at 0x%llx are not FL 2027 1.00's -- nothing written, "
         "the game keeps its floor of 39", (unsigned long long)NUM_SIG);
    return 2;
  }
  if (!put_bytes((unsigned char*)(uintptr_t)VA(NUM_BYTE), &b, 1)) {
    logf("confgroups: team numbers: off VirtualProtect failed at 0x%llx -- the game keeps its floor of 39",
         (unsigned long long)NUM_BYTE);
    return 4;
  }
  logf("confgroups: team numbers: ok -- attack / midfield / defence of a weak club show below 39 (1 byte)");
  return 0;
}

__declspec(dllexport) int fl26_confgroups_numbers(uint64_t exe_base)
{
  B = exe_base;
  return num_floor(exe_is_fl27());
}

static int g_installed;

/* 0 ok; 1 not FL 2027 or no groups; 2 a byte check failed (nothing written); 3 no page; 4 VirtualProtect */
__declspec(dllexport) int fl26_confgroups_install(uint64_t exe_base)
{
  B = exe_base;
  tables_init();
  if (g_installed) { logf("confgroups: ok (already installed)"); return 0; }
  if (!exe_is_fl27()) { logf("confgroups: off not FL 2027"); return 1; }
  int ns = 0, nr = 0, gs = 0, gr = 0;
  for (int i = 0; i < 1024; i++) if (g_slot[i] >= 0) { ns++; gs |= 1 << g_slot[i]; }
  for (int i = 0; i < 256; i++) if (g_reg[i] >= 0) { nr++; gr |= 1 << g_reg[i]; }
  if (!ns && !nr) { logf("confgroups: off no slot or region in the confgroups line"); return 1; }

  const struct { uint64_t slot, want; const char* what; } VT[] = {
    { TSC_VT + 0x18,  TSC_DTOR,   "Select Team vtable +0x18" },
    { TSC_VT + 0xd8,  TSC_INIT,   "Select Team vtable +0xd8" },
    { TSC_VT + 0x188, TSC_DECIDE, "Select Team vtable +0x188" },
    { TSC_VT + 0x190, TSC_CANCEL, "Select Team vtable +0x190" },
    { CI_VT + 0x18,   CI_DTOR,    "Competition Info vtable +0x18" },
    { CI_VT + 0xd8,   CI_INIT,    "Competition Info vtable +0xd8" },
    { CI_VT + 0x188,  CI_DECIDE,  "Competition Info vtable +0x188" },
    { CI_VT + 0x190,  CI_CANCEL,  "Competition Info vtable +0x190" },
  };
  for (unsigned i = 0; i < sizeof VT / sizeof VT[0]; i++)
    if (*(uint64_t*)(uintptr_t)VA(VT[i].slot) != VA(VT[i].want)) {
      logf("confgroups: off %s is 0x%llx, not 0x%llx (another mod?) -- nothing written", VT[i].what,
           (unsigned long long)(*(uint64_t*)(uintptr_t)VA(VT[i].slot) - B + 0x140000000ULL),
           (unsigned long long)VT[i].want);
      return 2;
    }
  for (unsigned i = 0; i < sizeof SIGS / sizeof SIGS[0]; i++) {
    int st = sig_state(SIGS[i].va, SIGS[i].hex);
    if (!st) {
      logf("confgroups: off bytes at 0x%llx [%s] are not FL 2027 1.00's -- nothing written",
           (unsigned long long)SIGS[i].va, SIGS[i].what);
      return 2;
    }
    if (st == 2)
      logf("confgroups: 0x%llx [%s] starts with another module's jump; called through it",
           (unsigned long long)SIGS[i].va, SIGS[i].what);
  }

  unsigned char* t = near_alloc(exe_base);
  if (!t) { logf("confgroups: off no page within 2 GB of the exe"); return 3; }
  memset(t, 0xcc, 0x1000);
  int n = 0;
  /* trampolines: the covered bytes, then back */
  const struct { uint64_t va; int len; fn2_t* tr; void* to; } HK[3] = {
    { TSC_INSERT, INSERT_LEN, &t_insert, (void*)ts_insert },
    { TSC_PICK,   PICK_LEN,   &t_pick,   (void*)ts_pick },
    { TSC_JUMP,   JUMP_LEN,   &t_jump,   (void*)ts_jump },
  };
  unsigned char* entry[3];
  for (int i = 0; i < 3; i++) {
    n = (n + 15) & ~15;
    *HK[i].tr = (fn2_t)(void*)(t + n);
    memcpy(t + n, (void*)(uintptr_t)VA(HK[i].va), HK[i].len); n += HK[i].len;
    n = jmp_abs(t, n, VA(HK[i].va) + HK[i].len);
    n = (n + 15) & ~15;
    entry[i] = t + n;
    n = jmp_rax(t, n, (uint64_t)(uintptr_t)HK[i].to);
  }
  n = (n + 15) & ~15;
  unsigned char* lab = t + n;
  n = jmp_rax(t, n, (uint64_t)(uintptr_t)cg_label);
  n = (n + 15) & ~15;
  unsigned char* comps = t + n;
  n = jmp_rax(t, n, (uint64_t)(uintptr_t)cg_comps);
  n = (n + 15) & ~15;
  unsigned char* emb = t + n;
  n = jmp_rax(t, n, (uint64_t)(uintptr_t)cg_emblem);
  n = (n + 15) & ~15;
  unsigned char* info = t + n;               /* mov r8, [rdi+0x98] (the list model); then cg_info */
  t[n++] = 0x4c; t[n++] = 0x8b; t[n++] = 0x87; *(uint32_t*)(t + n) = 0x98; n += 4;
  n = jmp_rax(t, n, (uint64_t)(uintptr_t)cg_info);
  n = (n + 15) & ~15;
  unsigned char* slot = t + n;               /* mov r8, rbx (League Info); then cg_slot */
  t[n++] = 0x49; t[n++] = 0x89; t[n++] = 0xd8;
  n = jmp_rax(t, n, (uint64_t)(uintptr_t)cg_slot);
  FlushInstructionCache(GetCurrentProcess(), t, 0x1000);

  /* write: the vtables (an object built from now on), the direct hooks, the calls */
  const struct { uint64_t slot; void* fn; } NEWVT[] = {
    { TSC_VT + 0x18, (void*)ts_dtor }, { TSC_VT + 0xd8, (void*)ts_init },
    { TSC_VT + 0x188, (void*)ts_decide }, { TSC_VT + 0x190, (void*)ts_cancel },
    { CI_VT + 0x18, (void*)ci_dtor }, { CI_VT + 0xd8, (void*)ci_init }, { CI_VT + 0x188, (void*)ci_decide },
    { CI_VT + 0x190, (void*)ci_cancel },
  };
  for (unsigned i = 0; i < sizeof NEWVT / sizeof NEWVT[0]; i++)
    if (!put_qword(VA(NEWVT[i].slot), (uint64_t)(uintptr_t)NEWVT[i].fn)) {
      logf("confgroups: VirtualProtect failed at the vtable 0x%llx", (unsigned long long)NEWVT[i].slot);
      return 4;
    }
  for (int i = 0; i < 3; i++) {
    unsigned char j[16];
    memset(j, 0xcc, sizeof j);
    j[0] = 0xe9;
    *(int32_t*)(j + 1) = (int32_t)((int64_t)(uintptr_t)entry[i] - (int64_t)(VA(HK[i].va) + 5));
    if (!put_bytes((unsigned char*)(uintptr_t)VA(HK[i].va), j, HK[i].len)) {
      logf("confgroups: VirtualProtect failed at 0x%llx", (unsigned long long)HK[i].va);
      return 4;
    }
  }
  const struct { uint64_t va; unsigned char* to; } CALLS[5] = {
    { LABEL_CALL, lab }, { COMPS_CALL, comps }, { EMBLEM_CALL, emb }, { INFO_CALL, info }, { SLOT_CALL, slot } };
  for (int i = 0; i < 5; i++) {
    unsigned char c[5] = { 0xe8 };
    *(int32_t*)(c + 1) = (int32_t)((int64_t)(uintptr_t)CALLS[i].to - (int64_t)(VA(CALLS[i].va) + 5));
    if (!put_bytes((unsigned char*)(uintptr_t)VA(CALLS[i].va), c, 5)) {
      logf("confgroups: VirtualProtect failed at 0x%llx", (unsigned long long)CALLS[i].va);
      return 4;
    }
  }
  g_installed = 1;
  {
    char gl[64] = "";
    for (int g = 0; g < NG; g++)
      if ((gs | gr) & (1 << g)) { strcat(gl, gl[0] ? " " : ""); strcat(gl, GNAME[g]); }
    int nc = 0;
    for (int i = 0; i < 1024; i++) if (g_sctry[i] >= 0) nc++;
    logf("confgroups: ok -- Select Team and Competition Info by confederation, then country (%d slots, %d of them "
         "by country, %d regions: %s)", ns, nc, nr, gl);
  }
  trace("installed: %d slots, %d regions", ns, nr);
  return 0;
}

/* the world line's entries, before install */
__declspec(dllexport) void fl26_confgroups_slot(int slot, int g)
{
  tables_init();
  if (slot >= 0 && slot < 1024 && g >= -1 && g < NG) g_slot[slot] = (int8_t)g;
}
__declspec(dllexport) void fl26_confgroups_region(int region, int g)
{
  tables_init();
  if (region >= 0 && region < 256 && g >= -1 && g < NG) g_reg[region] = (int8_t)g;
}
/* a slot's country (Country.bin id): its league goes under that country's row */
__declspec(dllexport) void fl26_confgroups_country(int slot, int c)
{
  tables_init();
  if (slot >= 0 && slot < 1024 && c >= -1 && c < NCTRY) g_sctry[slot] = (int16_t)c;
}
/* a country's name (UTF-8, as the game prints it) */
__declspec(dllexport) void fl26_confgroups_cname(int c, const char* name)
{
  if (c < 0 || c >= NCTRY || !name) return;
  snprintf(g_cname[c], sizeof g_cname[c], "%s", name);
}
/* a club competition on a group's right side in Competition Info (its continental cups, the Club
 * World Cup); none: nothing there */
__declspec(dllexport) void fl26_confgroups_cup(int g, int cid)
{
  if (g >= 0 && g < NG && cid > 0 && cid < 0x10000 && g_ncups[g] < 16) g_cups[g][g_ncups[g]++] = (uint16_t)cid;
}
/* the slot a group's header row stands on (its emblem); default 123, none.  League Info on that
 * row is the group's continental cups whatever the slot (cg_info) */
__declspec(dllexport) void fl26_confgroups_head(int g, int slot)
{
  if (g >= 0 && g < NG && slot >= 0 && slot < 1024) g_head[g] = slot;
}
/* the emblem of a group's row: competition `cid`'s (emb_<cid>*.png in the world); default none, the
 * emblem of its `heads` slot */
__declspec(dllexport) void fl26_confgroups_emblem(int g, int cid)
{
  if (g >= 0 && g < NG && cid > 0 && cid < 0x10000) g_emb[g] = cid;
}
/* lab 23/11/2026: a league's folder (confsub) and a folder's parent, emblem and name (confsubnames) */
__declspec(dllexport) void fl26_confgroups_fold(int slot, int f)
{
  if (slot >= 0 && slot < 1024 && f >= 0 && f < NFOLD) g_sfold[slot] = (uint8_t)f;
}
__declspec(dllexport) void fl26_confgroups_fname(int f, int parent, int cid, const char* name)
{
  if (f <= 0 || f >= NFOLD || parent < 0 || parent >= NFOLD || parent == f || !name) return;
  g_fpar[f] = (uint8_t)parent;
  g_femb[f] = cid > 0 && cid < 0x10000 ? cid : 0;
  snprintf(g_fname[f], sizeof g_fname[f], "%s", name);
}
/* trace=1: modules\fl26confgroups-trace.txt (path: the DLL's folder, UTF-16) */
__declspec(dllexport) void fl26_confgroups_trace(int on)
{
  g_trace_on = on;
  HMODULE me = 0;
  if (!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                          (LPCWSTR)(void*)fl26_confgroups_trace, &me)) return;
  DWORD k = GetModuleFileNameW(me, g_trace_path, MAX_PATH);
  while (k > 0 && g_trace_path[k - 1] != L'\\' && g_trace_path[k - 1] != L'/') k--;
  g_trace_path[k] = 0;
  wcscat(g_trace_path, L"fl26confgroups-trace.txt");
}

/* the log lines since the last call */
__declspec(dllexport) int fl26_confgroups_log(char* out, int cap)
{
  int n = g_log_len; if (n > cap - 1) n = cap - 1; if (n < 0) n = 0;
  memcpy(out, g_log, n); out[n] = 0;
  g_log_len = 0;
  return n;
}

