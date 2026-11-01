/* fl26squadlist.dll -- Select Team: on a league row the panel lists the league's clubs.
 *
 * What the player sees.  The Select Team screen (TeamSelectSingle@menu and the other TeamSelect
 * classes: Master League > Database > Team Info, League mode, Edit...) has two columns: the
 * leagues and, after Confirm, the clubs of that league.  The panel on the right shows the
 * players of the club under the cursor while the cursor is in the club column.  In the league
 * column the game leaves it empty (red rows with nothing in them), unless the screen was built
 * with League Info on (only the start of a new Master League), which shows cups and promotion.
 * With this DLL a league row lists the league's clubs, in the order the club column has them,
 * under the title "Team List"; inside the league each club's players under "Squad List", as
 * before.
 *
 * How the list draws.  The panel's rows are fed by a "page" (0x28 bytes, one per list widget):
 * [+0x00] 4-byte entries for type 2/5, [+0x08] 8-byte entries for type 1/4, [+0x18] the type,
 * [+0x19] the stride, [+0x1a] the count, [+0x1c] 1, [+0x20] the widget (the page's key).  The
 * squad list fills it with player handles (type 1) through 0x140e7c300; the same list code fills
 * team ids (type 2) through 0x140e7c4f0 for the screens that list clubs.  Each row element is
 * then drawn from the page by its kind:
 *   texts (element type 0x13)      0x140e7d390: type 1/4 -> 0x140e7d7a0 (kind 1 the player's
 *                                  name), type 2/5 -> 0x140e7db30 (kind 15 the club's name,
 *                                  kind 7 a number; any other kind is left as it was)
 *   position badges (type 0x1d)    0x140e7d260: type 1/4 only; state 0x16 is the empty badge
 *                                  the game gives a missing player
 *
 * What this writes (every site checked byte for byte first; one mismatch and nothing is written):
 *
 * 1. The panel update (0x140c98ee0, vtable +0x250 of every TeamSelect class), league column,
 *    League Info off: it jumped to 0x140c98fde, which stores the invalid team id and empties
 *    the list.  The jne at 0x140c98f57 now goes to the club column's own branch (0x140c990b1)
 *    through a stub that sets the title: "Team List" where the game's "Squad List" (text
 *    0x3c004a) is English, the game's own "Teams" (0x200027, the Edit menu's) in any other
 *    language -- the game has no "Team List" text.  The stub then joins the branch past its
 *    title (0x140c990d7): the league's remembered club in [this+0x90], and the refresh (vtable
 *    +0x268) when that club changed -- which it does from one league to the next, so moving
 *    the cursor over the leagues refreshes the panel.  The club column keeps the branch's own
 *    title, "Squad List".
 * 2. The refresh (0x140c991b0): in the league column it skipped the load.  Now, there, it gives
 *    the panel's page the league's clubs (0x140e7c4f0, type 2) and returns their count, which
 *    the refresh uses as it uses the number of players (rows shown, "numOver").  The league is
 *    the list model's current row ([this+0x98]: rows at +0x100, 0x70 bytes each, the row
 *    +0x118 + +0x11c), its clubs the row's vector at +0x08 (0x50 bytes each, the team id at +0).
 *    League Info on, or no list: nothing loaded, as before.
 * 3. Texts of THAT page while it holds clubs: kind 1 (the name in a squad row) and 15 are drawn
 *    as kind 15, the club's name; every other kind is set to an empty text instead of keeping
 *    the player's.
 * 4. Position badges of that page while it holds clubs: the club's crest instead, where the
 *    world's layout has the crest cell (teamSelectSingle.bin from tools/mkteamcrest.py: a
 *    uirEmblemCompe, element type 0xe, flTeamEmblem, in each row).  The badge pass (0x140e7d2d8,
 *    for each badge of a row) calls sq_row, which finds the row's crest cell (0x140e4d4a0 /
 *    0x140e4d1c0, by type), sets the club on it (0x140e5cda0, the call the game's own crest pass
 *    makes for uirEmblem cells -- that pass never touches 0xe ones), shows it and hides the badge
 *    (0x140e4c240, bit 0 of [node+0xc]).  On every other row of that panel (players, or an empty
 *    row past the clubs) the crest is hidden and a badge this hid is shown again.  No crest cell
 *    (a world's layout from before, or another mod's): the empty badge (0x140e5a9f0(badge, 0x16),
 *    what the game does for a missing player) instead of the last player's position.  The crest
 *    calls are checked first too (the cell's vtable, the invalid team id); otherwise no crests.
 *
 * "That page" is the page pointer 2 last filled with clubs, and its type must still be 2: the
 * club column fills the same page with players (type 1), and every other list and every other
 * page is left to the game's code.
 *
 * FL26 2.2 and FL27 1.00 have the same bytes at the same addresses (FL27's exe is FL26 2.2's
 * code).  The stubs live in a page within 2 GB of the exe (rel32 jumps).
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

static uint64_t B;                                    /* the exe's base */
#define VA(x) (B + ((uint64_t)(x) - 0x140000000ULL))

/* 1. the panel update, league column without League Info */
#define UPD_FN        0x140c98ee0
#define UPD_JNE       0x140c98f57          /* jne 0x140c98fde (the empty list) */
#define UPD_CLUB      0x140c990b1          /* the club column's branch: its title, then ... */
#define UPD_CLUB_LEN  45
#define UPD_PAST      0x140c990d7          /* ... mov byte [rbx+0xa1], 1: the branch past its title */
#define TEXT_TITLE    0x14271cd20          /* "text_title", the title element's name */
#define FIND_CHILD    8                    /* vtable +8 of [widget+0x98]: (name) -> element */
#define TEXT_MGR      0x141497dc0          /* () -> the text manager */
#define TEXT_OF       0x141497dd0          /* (manager, id) -> const char*, "" when missing */
#define SET_TEXT_ID   0x140e48fc0          /* (element, id) */
#define TXT_SQUAD     0x3c004a             /* "Squad List" */
#define TXT_TEAMS     0x200027             /* "Teams" */
/* 2. the refresh */
#define REF_FN        0x140c991b0
#define REF_SITE      0x140c991ea          /* mov rcx,[rbx+0x98]; call 0x140c95790; test al,al; jne */
#define REF_LEN       16
#define REF_LOAD      0x140c991fa          /* the club column: load the players */
#define REF_AFTER     0x140c99214          /* edi = rows */
#define LEAGUE_COL    0x140c95790          /* list model: is the cursor in the league column */
#define PAGES_OF      0x140e3d450          /* screen -> its pages (vector of page pointers) */
#define SET_TEAMS     0x140e7c4f0          /* (pages, &vector<u32>, widget, 0) */
/* 3. texts */
#define TXT_FN        0x140e7d390
#define TXT_SITE      0x140e7d43f          /* movzx edx,byte [r12+0x18]; mov qword [rsp+0x50],0xf */
#define TXT_LEN       15
#define TXT_BACK      0x140e7d44e
#define TXT_NEXT      0x140e7d4a7          /* the next element */
#define SET_TEXT      0x140e48bf0          /* (element, std::string*, 0, 0) */
/* 4. badges */
#define BDG_FN        0x140e7d260
#define BDG_SITE      0x140e7d2d8          /* movzx ecx,byte [r15+0x18]; mov esi,[rax+0xa4] */
#define BDG_LEN       11
#define BDG_BACK      0x140e7d2e3
#define BDG_NEXT      0x140e7d33f
#define BADGE_STATE   0x140e5a9f0          /* (badge, state) */
#define BADGE_EMPTY   0x16
/* 4b. the crest of a club row (a uirEmblemCompe cell the world's teamSelectSingle.bin adds) */
#define NODE_COUNT    0x140e4d4a0          /* (finder, type) -> how many nodes of that type */
#define NODE_GET      0x140e4d1c0          /* (finder, type, i) -> the i-th */
#define NODE_COMPE    0xe                  /* uirEmblemCompe */
#define SHOW          0x140e4c240          /* (node, on, mask): [node+0xc] |= / &= ~mask */
#define SET_EMBLEM    0x140e5cda0          /* (node, &team id, shadow, -, 0, type): the rows' crest call */
#define VT_COMPE      0x1427c2858          /* NodeRectEmblemCompe's vtable */
#define TEAM_NONE     0x14351ae44          /* the invalid team id the game's own crest pass skips */

static const unsigned char SIG_UPD[6]   = { 0x0f,0x85,0x81,0x00,0x00,0x00 };
static const unsigned char SIG_CLUB[UPD_CLUB_LEN] = {
  0x48,0x8d,0x8f,0x98,0x00,0x00,0x00,                   /* lea rcx, [rdi+0x98] */
  0x48,0x8b,0x01,                                       /* mov rax, [rcx] */
  0x48,0x8d,0x15,0x5e,0x3c,0xa8,0x01,                   /* lea rdx, "text_title" */
  0xff,0x50,0x08,                                       /* call [rax+8] */
  0x48,0x85,0xc0, 0x74,0x0d,                            /* test rax, rax; je */
  0xba,0x4a,0x00,0x3c,0x00,                             /* mov edx, 0x3c004a */
  0x48,0x8b,0xc8, 0xe8,0xe9,0xfe,0x1a,0x00,             /* mov rcx, rax; call 0x140e48fc0 */
  0xc6,0x83,0xa1,0x00,0x00,0x00,0x01 };                 /* mov byte [rbx+0xa1], 1 */
static const char SIG_TITLE_NAME[11] = "text_title";
static const unsigned char SIG_REF[REF_LEN] = {
  0x48,0x8b,0x8b,0x98,0x00,0x00,0x00,                   /* mov rcx, [rbx+0x98] */
  0xe8,0x9a,0xc5,0xff,0xff,                             /* call 0x140c95790 */
  0x84,0xc0,                                            /* test al, al */
  0x75,0x1a };                                          /* jne 0x140c99214 */
static const unsigned char SIG_TXT[TXT_LEN] = {
  0x41,0x0f,0xb6,0x54,0x24,0x18,                        /* movzx edx, byte [r12+0x18] */
  0x48,0xc7,0x44,0x24,0x50,0x0f,0x00,0x00,0x00 };       /* mov qword [rsp+0x50], 0xf */
static const unsigned char SIG_BDG[BDG_LEN] = {
  0x41,0x0f,0xb6,0x4f,0x18,                             /* movzx ecx, byte [r15+0x18] */
  0x8b,0xb0,0xa4,0x00,0x00,0x00 };                      /* mov esi, [rax+0xa4] */
/* the callees, by their first bytes */
static const struct { uint64_t va; unsigned char sig[8]; } CALLEES[] = {
  { LEAGUE_COL,  { 0x80,0xb9,0x9b,0x00,0x00,0x00,0x00,0x0f } },
  { PAGES_OF,    { 0x48,0x8b,0x81,0x88,0x00,0x00,0x00,0x48 } },
  { SET_TEAMS,   { 0x48,0x89,0x6c,0x24,0x18,0x56,0x57,0x41 } },
  { SET_TEXT,    { 0x48,0x8b,0xc4,0x55,0x56,0x57,0x41,0x56 } },
  { BADGE_STATE, { 0x48,0x89,0x5c,0x24,0x08,0x57,0x48,0x83 } },
  { TEXT_MGR,    { 0x48,0x8b,0x05,0x21,0xd0,0x26,0x02,0xc3 } },
  { TEXT_OF,     { 0x48,0x89,0x5c,0x24,0x08,0x57,0x48,0x83 } },
  { SET_TEXT_ID, { 0x4c,0x8b,0xdc,0x57,0x48,0x83,0xec,0x60 } },
  { NODE_COUNT,  { 0x48,0x8b,0x49,0x78,0x45,0x33,0xc9,0x44 } },
  { NODE_GET,    { 0x48,0x8b,0x49,0x78,0x44,0x8b,0xd2,0x45 } },
  { SHOW,        { 0x84,0xd2,0x74,0x0b,0x44,0x09,0x41,0x0c } },
  { SET_EMBLEM,  { 0x48,0x8b,0xc4,0x55,0x41,0x56,0x41,0x57 } },
};

typedef void* (*pages_of_t)(void* screen);
typedef void  (*set_teams_t)(void* pages, void* vec, void* widget, uint64_t two);
typedef int64_t (*set_text_t)(void* element, void* str, uint64_t, uint64_t);
typedef void* (*text_mgr_t)(void);
typedef const char* (*text_of_t)(void* mgr, uint32_t id);
typedef int64_t (*set_text_id_t)(void* element, uint32_t id);
typedef int   (*node_count_t)(void* finder, uint32_t type);
typedef char* (*node_get_t)(void* finder, uint32_t type, uint32_t i);
typedef void  (*show_t)(void* node, uint8_t on, uint32_t mask);
typedef void  (*badge_state_t)(void* badge, uint32_t state);
typedef void  (*set_emblem_t)(void* node, uint32_t* team, uint8_t shadow, uint32_t, uint8_t, uint32_t type);

static volatile uint64_t* g_page;        /* in the stub page: the page holding clubs, read by 3/4 */
static uint32_t g_ids[128];
static volatile long g_filled;           /* how many times 2 has filled a league (for the log) */
static char* g_key;                      /* that page's key (the panel list's widget + 0x98) */
static int g_crest_ok;                   /* the crest calls are the ones expected */

#ifdef SQDEBUG
static wchar_t g_dir[MAX_PATH];
static void dbg(const char* fmt, ...)
{
  wchar_t p[MAX_PATH + 32];
  _snwprintf(p, MAX_PATH + 31, L"%lsfl26squadlist-debug.txt", g_dir);
  FILE* f = _wfopen(p, L"ab");
  if (!f) return;
  va_list ap; va_start(ap, fmt); vfprintf(f, fmt, ap); va_end(ap);
  fputc('\n', f);
  fclose(f);
}
static unsigned g_kinds_seen[4];

/* every string of the text tables loaded now, "id<TAB>text", to find a title */
static void dump_texts(void)
{
  static int done;
  if (done) return;
  done = 1;
  char* mgr = *(char**)(uintptr_t)VA(0x143704de8);
  if (!mgr) { dbg("texts: no manager"); return; }
  char* head = *(char**)mgr;
  wchar_t p[MAX_PATH + 32];
  _snwprintf(p, MAX_PATH + 31, L"%lsfl26squadlist-texts.txt", g_dir);
  FILE* f = _wfopen(p, L"wb");
  if (!f) return;
  char* stack[256]; int sp = 0, tables = 0, strings = 0;
  char* root = *(char**)(head + 8);
  if (root && !root[0x19]) stack[sp++] = root;
  while (sp > 0) {
    char* nd = stack[--sp];
    char* l = *(char**)nd; char* r = *(char**)(nd + 0x10);
    if (l && !l[0x19] && sp < 255) stack[sp++] = l;
    if (r && !r[0x19] && sp < 255) stack[sp++] = r;
    uint32_t key = *(uint16_t*)(nd + 0x20);
    char* tbl = *(char**)(nd + 0x28);
    if (!tbl) continue;
    char* base = *(char**)tbl; char* hdr = *(char**)(tbl + 8);
    if (!base || !hdr) continue;
    uint32_t cnt = *(uint32_t*)hdr;
    tables++;
    for (uint32_t i = 0; i < cnt && i < 100000; i++) {
      char* e = hdr + 8 + i * 12;
      fprintf(f, "%08x\t%s\n", (key << 16) | *(uint16_t*)e, base + *(uint32_t*)(e + 8));
      strings++;
    }
  }
  fclose(f);
  dbg("texts: %d tables, %d strings", tables, strings);
}
#endif

/* 2: the league's clubs onto the panel's page; returns their count (the rows to show) */
static int64_t sq_fill(char* screen, char* widget)
{
  if (!screen || !widget) return 0;
  if (*(uint8_t*)(screen + 0xb8) == 1) return 0;                 /* League Info on */
  char* list = *(char**)(screen + 0x98);
  if (!list) return 0;
  uint64_t row = (uint64_t)*(uint32_t*)(list + 0x118) + *(uint32_t*)(list + 0x11c);
  char* lb = *(char**)(list + 0x100);
  char* le = *(char**)(list + 0x108);
  if (!lb || le <= lb || row >= (uint64_t)(le - lb) / 0x70) return 0;
  char* league = lb + row * 0x70;
  char* cb = *(char**)(league + 0x08);
  char* ce = *(char**)(league + 0x10);
  if (!cb || ce <= cb) return 0;
  uint64_t n = (uint64_t)(ce - cb) / 0x50;
  if (n > sizeof g_ids / sizeof g_ids[0]) n = sizeof g_ids / sizeof g_ids[0];
  for (uint64_t i = 0; i < n; i++) g_ids[i] = *(uint32_t*)(cb + i * 0x50);
  struct { uint32_t *b, *e, *c; } v = { g_ids, g_ids + n, g_ids + n };   /* read only: copied */
  char* pages = (char*)((pages_of_t)VA(PAGES_OF))(screen);
  if (!pages) return 0;
  ((set_teams_t)VA(SET_TEAMS))(pages, &v, widget + 0x98, 0);
  char** pb = *(char***)pages;
  char** pe = *(char***)(pages + 8);
  for (char** p = pb; p && p < pe; p++)
    if (*p && *(char**)(*p + 0x20) == widget + 0x98 && *(uint8_t*)(*p + 0x1c) == 1) {
      *g_page = (uint64_t)(uintptr_t)*p;
      g_key = widget + 0x98;
      break;
    }
  InterlockedIncrement(&g_filled);
#ifdef SQDEBUG
  dump_texts();
  dbg("fill: row %llu, %llu clubs, first %08x, page %llx", (unsigned long long)row,
      (unsigned long long)n, n ? g_ids[0] : 0, (unsigned long long)*g_page);
#endif
  return (int64_t)n;
}

/* 1: the panel's title on a league row */
static void sq_title(char* element)
{
  void* mgr = ((text_mgr_t)VA(TEXT_MGR))();
  const char* squad = mgr ? ((text_of_t)VA(TEXT_OF))(mgr, TXT_SQUAD) : 0;
  if (squad && !strcmp(squad, "Squad List")) {
    struct { char buf[16]; uint64_t size, cap; } s;              /* std::string, held in place */
    memset(&s, 0, sizeof s);
    memcpy(s.buf, "Team List", 9);
    s.size = 9;
    s.cap = 15;
    ((set_text_t)VA(SET_TEXT))(element, &s, 0, 0);
  } else {
    ((set_text_id_t)VA(SET_TEXT_ID))(element, TXT_TEAMS);
  }
}

/* 3: a text of the page holding clubs; returns the kind to draw it as, 0 when it was blanked */
static int64_t sq_text(char* element, int64_t kind)
{
  int k = (int)kind;
#ifdef SQDEBUG
  if (k >= 0 && k < 128 && !(g_kinds_seen[k >> 5] & (1u << (k & 31)))) {
    g_kinds_seen[k >> 5] |= 1u << (k & 31);
    dbg("text kind %d seen", k);
  }
#endif
  if (k == 1 || k == 15) return 15;
  struct { char buf[16]; uint64_t size, cap; } s;                /* an empty std::string */
  memset(&s, 0, sizeof s);
  s.cap = 15;
  ((set_text_t)VA(SET_TEXT))(element, &s, 0, 0);
  return 0;
}

/* the badges hidden for a crest, to show them again on the same rows' players */
static char* g_hidden[64];
static void badge_hide(char* badge)
{
  for (int i = 0; i < 64; i++) if (g_hidden[i] == badge) return;
  for (int i = 0; i < 64; i++)
    if (!g_hidden[i]) {
      g_hidden[i] = badge;
      ((show_t)VA(SHOW))(badge, 0, 1);
      return;
    }
}
static void badge_show(char* badge)
{
  for (int i = 0; i < 64; i++)
    if (g_hidden[i] == badge) {
      g_hidden[i] = 0;
      ((show_t)VA(SHOW))(badge, 1, 1);
      return;
    }
}

/* 4: a row of the page holding clubs (team ids) or, the same page later, players.  A club row:
 * its crest in the row's crest cell and the position badge hidden (no crest cell: the empty
 * badge, as before).  A player row: the crest cell hidden, the badge shown, and the game draws
 * the badge as always.  Returns 1 when the row's badge is done, 0 to let the game draw it. */
static int64_t sq_row(char* finder, char* page, uint32_t* entry, char* badge)
{
  char* crest = 0;
  if (g_crest_ok && ((node_count_t)VA(NODE_COUNT))(finder, NODE_COMPE) > 0) {
    crest = ((node_get_t)VA(NODE_GET))(finder, NODE_COMPE, 0);
    if (crest && *(uint64_t*)crest != VA(VT_COMPE)) crest = 0;
  }
  if (*(uint8_t*)(page + 0x18) == 2 && *(char**)(page + 0x20) == g_key) {
    if (crest && *entry != *(uint32_t*)(uintptr_t)VA(TEAM_NONE)) {
      ((show_t)VA(SHOW))(crest, 1, 1);
      *(uint32_t*)(crest + 0x9c) = 0;
      ((set_emblem_t)VA(SET_EMBLEM))(crest, entry, 0, 5, 0, 0);
      badge_hide(badge);
#ifdef SQDEBUG
      dbg("row: crest %p team %08x flags crest %x badge %x", crest, *entry, *(uint32_t*)(crest + 0xc), *(uint32_t*)(badge + 0xc));
#endif
      return 1;
    }
    if (crest) ((show_t)VA(SHOW))(crest, 0, 1);
    badge_show(badge);
    ((badge_state_t)VA(BADGE_STATE))(badge, BADGE_EMPTY);
#ifdef SQDEBUG
    dbg("row: no crest cell (%p), team %08x", crest, *entry);
#endif
    return 1;
  }
  if (crest) ((show_t)VA(SHOW))(crest, 0, 1);
  badge_show(badge);
  return 0;
}

static unsigned char* near_alloc(uint64_t exe_base)
{
  for (uint64_t a = (exe_base & ~0xffffULL) - 0x10000; a > exe_base - 0x70000000ULL; a -= 0x10000) {
    void* p = VirtualAlloc((void*)(uintptr_t)a, 0x1000, MEM_COMMIT|MEM_RESERVE, PAGE_EXECUTE_READWRITE);
    if (p) return (unsigned char*)p;
  }
  return 0;
}

static int rip32(unsigned char* s, int n, const volatile void* target, int tail)
{
  *(int32_t*)(s + n) = (int32_t)((int64_t)(uintptr_t)target - (int64_t)(uintptr_t)(s + n + 4 + tail));
  return n + 4;
}
static int jmp_abs(unsigned char* s, int n, uint64_t to)
{
  s[n++] = 0xff; s[n++] = 0x25; *(uint32_t*)(s + n) = 0; n += 4; *(uint64_t*)(s + n) = to; n += 8;
  return n;
}
static int call_abs_rax(unsigned char* s, int n, uint64_t to)
{
  s[n++] = 0x48; s[n++] = 0xb8; *(uint64_t*)(s + n) = to; n += 8;     /* mov rax, imm64 */
  s[n++] = 0xff; s[n++] = 0xd0;                                       /* call rax */
  return n;
}
static int put_rel_jmp(unsigned char* at, int len, unsigned char* to)
{
  DWORD old;
  if (!VirtualProtect(at, len, PAGE_EXECUTE_READWRITE, &old)) return 0;
  at[0] = 0xe9; *(int32_t*)(at + 1) = (int32_t)((int64_t)(uintptr_t)to - (int64_t)(uintptr_t)(at + 5));
  for (int i = 5; i < len; i++) at[i] = 0xcc;
  VirtualProtect(at, len, old, &old);
  FlushInstructionCache(GetCurrentProcess(), at, len);
  return 1;
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

/* unwind data for a stub that runs inside `host`'s frame (entered by jmp, past the prologue):
 * a copy of the host's unwind codes without its handler, at `ui`; 0 when the host's are chained */
static int host_unwind(uint64_t host, unsigned char* ui, int room)
{
  DWORD64 ib = 0;
  PRUNTIME_FUNCTION rf = RtlLookupFunctionEntry(VA(host), &ib, NULL);
  if (!rf || ib != B || rf->BeginAddress != (DWORD)(host - 0x140000000ULL)) return 0;
  unsigned char* src = (unsigned char*)(uintptr_t)(B + rf->UnwindData);
  int cnt = src[2];
  if (((src[0] >> 3) & UNW_FLAG_CHAININFO) || 4 + 2 * cnt > room) return 0;
  memcpy(ui, src, 4 + 2 * cnt);
  ui[0] = 1;                                              /* version 1, no handler */
  ui[1] = 0;                                              /* no prologue: the stub is past it, all codes apply */
  return 1;
}

/* 0 ok; 2 a site is not the one expected (nothing patched); 3 no page in reach; 4 VirtualProtect */
__declspec(dllexport) int fl26_squadlist_install(uint64_t exe_base)
{
  B = exe_base;
  struct { uint64_t va; const unsigned char* sig; int len; const char* what; } SITES[] = {
    { UPD_JNE,  SIG_UPD,  6,       "Select Team update: league row without League Info -> empty list" },
    { UPD_CLUB, SIG_CLUB, UPD_CLUB_LEN, "Select Team update: the club column's branch (its title)" },
    { TEXT_TITLE, (const unsigned char*)SIG_TITLE_NAME, 11, "the title element's name" },
    { REF_SITE, SIG_REF,  REF_LEN, "Squad List refresh: league column? then no load" },
    { TXT_SITE, SIG_TXT,  TXT_LEN, "list rows: text dispatch by page type" },
    { BDG_SITE, SIG_BDG,  BDG_LEN, "list rows: position badge by page type" },
  };
  int bad = 0;
  for (unsigned i = 0; i < sizeof SITES / sizeof SITES[0]; i++)
    if (memcmp((void*)(uintptr_t)VA(SITES[i].va), SITES[i].sig, SITES[i].len)) {
      logf("fl26squadlist: MISMATCH at 0x%llx [%s]", (unsigned long long)SITES[i].va, SITES[i].what);
      bad++;
    }
  for (unsigned i = 0; i < sizeof CALLEES / sizeof CALLEES[0]; i++)
    if (memcmp((void*)(uintptr_t)VA(CALLEES[i].va), CALLEES[i].sig, 8)) {
      logf("fl26squadlist: MISMATCH at 0x%llx [a function the stubs call]", (unsigned long long)CALLEES[i].va);
      bad++;
    }
  if (bad) {
    logf("fl26squadlist: ABORTED, %d site(s) did not match. Nothing was written; the game is unmodified.", bad);
    return 2;
  }
  {
    uint64_t* vt = (uint64_t*)(uintptr_t)VA(VT_COMPE);
    g_crest_ok = vt[1] == VA(0x140e5bdd0) && vt[4] == VA(0x140e5d400)
                 && *(uint32_t*)(uintptr_t)VA(TEAM_NONE) == 0xffffffffu;
  }
  unsigned char* t = near_alloc(exe_base);
  if (!t) return 3;
  memset(t, 0xcc, 0x1000);
  g_page = (volatile uint64_t*)(t + 0xf00);
  *g_page = 0;
#ifdef SQDEBUG
  {
    HMODULE me = 0;
    GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                       (LPCWSTR)(void*)fl26_squadlist_install, &me);
    DWORD k = GetModuleFileNameW(me, g_dir, MAX_PATH);
    while (k > 0 && g_dir[k - 1] != L'\\' && g_dir[k - 1] != L'/') k--;
    g_dir[k] = 0;
    dbg("install, base %llx", (unsigned long long)exe_base);
  }
#endif

  unsigned char* s = t;
  int n = 0, j;

  /* ---- 1. the update's league row: the title, then the club column's branch past its own ---- */
  unsigned char* ttl = s + n;
  int t_skip;
  s[n++] = 0x48; s[n++] = 0x8d; s[n++] = 0x8f; *(uint32_t*)(s + n) = 0x98; n += 4;   /* lea rcx, [rdi+0x98] */
  s[n++] = 0x48; s[n++] = 0x8b; s[n++] = 0x01;                                      /* mov rax, [rcx] */
  s[n++] = 0x48; s[n++] = 0xba; *(uint64_t*)(s + n) = VA(TEXT_TITLE); n += 8;       /* mov rdx, "text_title" */
  s[n++] = 0xff; s[n++] = 0x50; s[n++] = FIND_CHILD;                                /* call [rax+8] */
  s[n++] = 0x48; s[n++] = 0x85; s[n++] = 0xc0;                                      /* test rax, rax */
  s[n++] = 0x74; t_skip = n++;                                                      /* je past */
  s[n++] = 0x48; s[n++] = 0x8b; s[n++] = 0xc8;                                      /* mov rcx, rax */
  n = call_abs_rax(s, n, (uint64_t)(uintptr_t)sq_title);
  s[t_skip] = (unsigned char)(n - (t_skip + 1));
  n = jmp_abs(s, n, VA(UPD_PAST));
  int ttl_end = n;

  /* ---- 2. the refresh: league column -> the clubs ---- */
  n = (n + 15) & ~15;
  int ref_beg = n;
  unsigned char* ref = s + n;
  s[n++] = 0x48; s[n++] = 0x8b; s[n++] = 0x8b; *(uint32_t*)(s + n) = 0x98; n += 4;   /* mov rcx, [rbx+0x98] */
  n = call_abs_rax(s, n, VA(LEAGUE_COL));
  s[n++] = 0x84; s[n++] = 0xc0;                                                     /* test al, al */
  s[n++] = 0x75; j = n++;                                                           /* jne league */
  n = jmp_abs(s, n, VA(REF_LOAD));                                                  /* the club column, as before */
  s[j] = (unsigned char)(n - (j + 1));
  s[n++] = 0x48; s[n++] = 0x8b; s[n++] = 0xcb;                                      /* mov rcx, rbx (the screen) */
  s[n++] = 0x48; s[n++] = 0x8b; s[n++] = 0xd6;                                      /* mov rdx, rsi (the panel's list) */
  n = call_abs_rax(s, n, (uint64_t)(uintptr_t)sq_fill);
  s[n++] = 0x8b; s[n++] = 0xf8;                                                     /* mov edi, eax */
  n = jmp_abs(s, n, VA(REF_AFTER));
  int ref_end = n;

  /* ---- 3. texts ---- */
  n = (n + 15) & ~15;
  unsigned char* txt = s + n;
  int txt_beg = n, j_back, j_back2, j_skip;
  s[n++] = 0x41; s[n++] = 0x0f; s[n++] = 0xb6; s[n++] = 0x54; s[n++] = 0x24; s[n++] = 0x18; /* movzx edx, byte [r12+0x18] */
  s[n++] = 0x48; s[n++] = 0xc7; s[n++] = 0x44; s[n++] = 0x24; s[n++] = 0x50;           /* mov qword [rsp+0x50], 0xf */
  *(uint32_t*)(s + n) = 0xf; n += 4;
  s[n++] = 0x83; s[n++] = 0xfa; s[n++] = 0x02;                                      /* cmp edx, 2 */
  s[n++] = 0x75; j_back = n++;                                                      /* jne back */
  s[n++] = 0x4c; s[n++] = 0x3b; s[n++] = 0x25; n = rip32(s, n, g_page, 0);          /* cmp r12, [g_page] */
  s[n++] = 0x75; j_back2 = n++;                                                     /* jne back */
  s[n++] = 0x4c; s[n++] = 0x89; s[n++] = 0x4c; s[n++] = 0x24; s[n++] = 0x28;        /* mov [rsp+0x28], r9 */
  s[n++] = 0x48; s[n++] = 0x8b; s[n++] = 0xcb;                                      /* mov rcx, rbx (the text) */
  s[n++] = 0x8b; s[n++] = 0xd6;                                                     /* mov edx, esi (its kind) */
  n = call_abs_rax(s, n, (uint64_t)(uintptr_t)sq_text);
  s[n++] = 0x4c; s[n++] = 0x8b; s[n++] = 0x4c; s[n++] = 0x24; s[n++] = 0x28;        /* mov r9, [rsp+0x28] */
  s[n++] = 0x85; s[n++] = 0xc0;                                                     /* test eax, eax */
  s[n++] = 0x74; j_skip = n++;                                                      /* je skip */
  s[n++] = 0x8b; s[n++] = 0xf0;                                                     /* mov esi, eax */
  s[n++] = 0xba; *(uint32_t*)(s + n) = 2; n += 4;                                   /* mov edx, 2 */
  s[j_back] = (unsigned char)(n - (j_back + 1));
  s[j_back2] = (unsigned char)(n - (j_back2 + 1));
  n = jmp_abs(s, n, VA(TXT_BACK));
  s[j_skip] = (unsigned char)(n - (j_skip + 1));
  n = jmp_abs(s, n, VA(TXT_NEXT));
  int txt_end = n;

  /* ---- 4. badges: on the page 2 filled, sq_row (registers: r12 the row's finder, r15 the
   * page, r14 the row's entry, rbx == rax the badge; rsp is 16-aligned here and [rsp, rsp+0x20)
   * is the host's own outgoing area) ---- */
  n = (n + 15) & ~15;
  unsigned char* bdg = s + n;
  int bdg_beg = n, k_back, k_back2;
  s[n++] = 0x4c; s[n++] = 0x3b; s[n++] = 0x3d; n = rip32(s, n, g_page, 0);          /* cmp r15, [g_page] */
  s[n++] = 0x75; k_back = n++;                                                      /* jne back */
  s[n++] = 0x49; s[n++] = 0x8b; s[n++] = 0xcc;                                      /* mov rcx, r12 */
  s[n++] = 0x49; s[n++] = 0x8b; s[n++] = 0xd7;                                      /* mov rdx, r15 */
  s[n++] = 0x4d; s[n++] = 0x8b; s[n++] = 0xc6;                                      /* mov r8, r14 */
  s[n++] = 0x4c; s[n++] = 0x8b; s[n++] = 0xcb;                                      /* mov r9, rbx */
  n = call_abs_rax(s, n, (uint64_t)(uintptr_t)sq_row);
  s[n++] = 0x85; s[n++] = 0xc0;                                                     /* test eax, eax */
  s[n++] = 0x74; k_back2 = n++;                                                     /* je back */
  n = jmp_abs(s, n, VA(BDG_NEXT));
  s[k_back] = (unsigned char)(n - (k_back + 1));
  s[k_back2] = (unsigned char)(n - (k_back2 + 1));
  s[n++] = 0x41; s[n++] = 0x0f; s[n++] = 0xb6; s[n++] = 0x4f; s[n++] = 0x18;        /* back: movzx ecx, byte [r15+0x18] */
  s[n++] = 0x8b; s[n++] = 0xb3; *(uint32_t*)(s + n) = 0xa4; n += 4;                 /* mov esi, [rbx+0xa4] */
  n = jmp_abs(s, n, VA(BDG_BACK));
  int bdg_end = n;
  if (n > 0xd00) return 3;

  /* unwind data: each stub runs in its host's frame, so it gets a copy of the host's codes */
  {
    unsigned char* ui = t + 0xd00;
    RUNTIME_FUNCTION* tab = (RUNTIME_FUNCTION*)(t + 0xe80);
    const struct { uint64_t host; int beg, end; } ST[4] = {
      { UPD_FN, 0, ttl_end }, { REF_FN, ref_beg, ref_end }, { TXT_FN, txt_beg, txt_end },
      { BDG_FN, bdg_beg, bdg_end } };
    int ok = 0;
    for (int i = 0; i < 4; i++) {
      unsigned char* u = ui + i * 0x50;
      if (!host_unwind(ST[i].host, u, 0x50)) continue;
      tab[ok].BeginAddress = (DWORD)ST[i].beg; tab[ok].EndAddress = (DWORD)ST[i].end;
      tab[ok].UnwindData = (DWORD)(u - t);
      ok++;
    }
    if (ok < 4 || !RtlAddFunctionTable(tab, ok, (DWORD64)(uintptr_t)t))
      logf("fl26squadlist: unwind data for %d of 4 stubs (stack walks stop at the others; the patch works the same)", ok);
  }
  FlushInstructionCache(GetCurrentProcess(), t, 0x1000);

  /* write: the stubs' jumps first, the update's jne (which makes the league rows use them) last */
  if (!put_rel_jmp((unsigned char*)(uintptr_t)VA(TXT_SITE), TXT_LEN, txt)) return 4;
  if (!put_rel_jmp((unsigned char*)(uintptr_t)VA(BDG_SITE), BDG_LEN, bdg)) return 4;
  if (!put_rel_jmp((unsigned char*)(uintptr_t)VA(REF_SITE), REF_LEN, ref)) return 4;
  {
    unsigned char jne[6] = { 0x0f, 0x85 };
    *(int32_t*)(jne + 2) = (int32_t)((int64_t)(uintptr_t)ttl - (int64_t)VA(UPD_JNE + 6));
    if (!put_bytes((unsigned char*)(uintptr_t)VA(UPD_JNE), jne, 6)) return 4;
  }
  logf("fl26squadlist: Select Team lists the league's clubs on the league rows, title Team List (4 sites, stubs %d bytes), crests %s", n,
       g_crest_ok ? "on (where the world's layout has the crest cell)" : "off (not the calls expected)");
  return 0;
}

/* the log lines since the last call */
__declspec(dllexport) int fl26_squadlist_log(char* out, int cap)
{
  int n = g_log_len; if (n > cap - 1) n = cap - 1; if (n < 0) n = 0;
  memcpy(out, g_log, n); out[n] = 0;
  g_log_len = 0;
  return n;
}

/* how many times a league's clubs were put on the panel */
__declspec(dllexport) long fl26_squadlist_count(void)
{
  return g_filled;
}
