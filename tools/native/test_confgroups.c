/* fl26confgroups.c without the game: the accordion of Select Team and Competition Info.

     zig cc -O2 -fno-sanitize=undefined test_confgroups.c -o test_confgroups.exe && test_confgroups.exe

   (tools/test_confgroups_dll.py builds and runs it.) Exit code 1 on any failure.

   The game's functions the DLL calls are stand-ins here, put where the DLL calls them: a fake
   image of the exe's size, a `mov rax, imm64; jmp rax` at each function's address. The rows are
   the game's layout (0x70 bytes: slot, clubs vector, name string, emblem string, ...), with the
   game's deep copy and free done by the stand-ins on malloc. The cases:
     - Kick Off: init on an empty list, the rows inserted after it: taken then; an empty list is not.
     - init: one row per confederation, the rows of no group before and after them where they
       were, the cursor on the first confederation; the game's init after it;
     - Confirm on a confederation: "- UEFA" and its countries (a country row on its first
       league's slot), a grouped league of no country as a row of its own; Confirm on a country:
       "- England" and its leagues; Confirm on a league is the game's; Back / Confirm on a "- ..."
       row goes up one level, the cursor on the row it came from; on the top level the game's;
     - the game's "cursor on this team" / "on this slot" show the level of that league first;
     - a row added after init goes in the master rows; the dtor frees them;
     - too few groups: the list is the game's, untouched; a list rebuilt behind our back loses
       our rows; the club column at init shows the level of the cursor's row;
     - Competition Info: pseudo regions, the labels, in / back (Confirm and Back), the right
       side of the row under the cursor, a confederation's right side its `cups` of region 1,
       the region entered shown again when the screen is built anew;
     - a row's emblem: a confederation's row with a logo the emblem of its competition id
       (`emblems`), every other row the game's;
     - League Info (B402): a confederation's row ("+ UEFA", "- UEFA" while open) its `cups` without
       the Club World Cup, at most six, no league above or below; a country, a league, the club
       column and a list of no state the game's; the panel redrawn when the row's confederation
       changes under the same slot 123;
     - the numbers of a club's three lines (fl26_confgroups_numbers): FL_2027.exe by the file's
       name and no other exe; in FL26 nothing is written though the bytes are the same; in
       FL 2027 one byte (0x29 -> 0x21 at 0x141508b07) and no other in the whole image, and only
       when all 25 bytes around it are the game's; asked twice, written once. */
#include "fl26confgroups.c"
#include <stdlib.h>

static int fails, checks;
#define CHECK(c, ...) do { checks++; if (!(c)) { fails++; printf("FAIL %s:%d: ", __FILE__, __LINE__); printf(__VA_ARGS__); printf("\n"); } } while (0)

/* ---- the rows, as the game keeps them ---- */
static void str_copy(char* d, const char* s)
{
  uint64_t n = *(const uint64_t*)(s + 0x10);
  memset(d, 0, 0x20);
  if (n <= 15) { memcpy(d, str_of(s), n); *(uint64_t*)(d + 0x18) = 15; }
  else { char* p = malloc(n + 1); memcpy(p, str_of(s), n); p[n] = 0; *(char**)d = p; *(uint64_t*)(d + 0x18) = n; }
  *(uint64_t*)(d + 0x10) = n;
}
static void str_free(char* s) { if (*(uint64_t*)(s + 0x18) >= 16) free(*(char**)s); }
static void row_copy(char* d, const char* s)
{
  memcpy(d, s, ROW);
  char *cb = *(char* const*)(s + 8), *ce = *(char* const*)(s + 0x10);
  if (cb && ce > cb) {
    char* p = malloc(ce - cb); memcpy(p, cb, ce - cb);
    *(char**)(d + 8) = p; *(char**)(d + 0x10) = p + (ce - cb); *(char**)(d + 0x18) = p + (ce - cb);
  } else {
    *(char**)(d + 8) = *(char**)(d + 0x10) = *(char**)(d + 0x18) = 0;
  }
  str_copy(d + 0x20, s + 0x20);
  str_copy(d + 0x40, s + 0x40);
}
static void row_free(char* r) { free(*(char**)(r + 8)); str_free(r + 0x20); str_free(r + 0x40); }
static void s_clear(void* v) { rvec* x = v; for (char* r = x->b; r && r < x->e; r += ROW) row_free(r); x->e = x->b; }
static int frees;
static void s_free(void* v) { rvec* x = v; s_clear(v); free(x->b); x->b = x->e = x->c = 0; frees++; }
static void s_push(void* v, const void* row)
{
  rvec* x = v;
  if (x->e == x->c) {
    uint64_t n = nrows(x), cap = n ? n * 2 : 4;
    char* nb = malloc(cap * ROW);
    if (n) memcpy(nb, x->b, n * ROW);
    free(x->b);
    x->b = nb; x->e = nb + n * ROW; x->c = nb + cap * ROW;
  }
  row_copy(x->e, row);
  x->e += ROW;
}
static char g_name_buf[64][24];
static void make_row(char* r, uint32_t slot, int clubs, const char* name)
{
  memset(r, 0, ROW);
  *(uint32_t*)r = slot;
  if (clubs) {
    char* c = calloc(clubs, 0x50);
    for (int i = 0; i < clubs; i++) *(uint32_t*)(c + i * 0x50) = slot * 100 + i;
    *(char**)(r + 8) = c; *(char**)(r + 0x10) = c + clubs * 0x50; *(char**)(r + 0x18) = c + clubs * 0x50;
  }
  set_str(r + 0x20, name, (int)strlen(name));
  set_str(r + 0x40, "", 0);
  r[0x60] = 1;
}
static void put_rows(char* t, const uint32_t* slots, int n)
{
  rvec* v = (rvec*)(t + 0x100);
  for (int i = 0; i < n; i++) {
    char r[ROW];
    snprintf(g_name_buf[i], sizeof g_name_buf[i], "L%u", slots[i]);
    make_row(r, slots[i], 3, g_name_buf[i]);
    s_push(v, r);
    row_free(r);
  }
}
static uint32_t slot_at(char* t, uint64_t i) { return *(uint32_t*)(((rvec*)(t + 0x100))->b + i * ROW); }
static const char* name_at(char* t, uint64_t i) { return str_of(((rvec*)(t + 0x100))->b + i * ROW + 0x20); }
static uint64_t shown(char* t) { return nrows((rvec*)(t + 0x100)); }

/* ---- the game's functions ---- */
static int game_init, game_decide, game_cancel, game_dtor, list_sets;
static uint32_t last_list_idx;
static uint64_t g_init(void* t, uint64_t a) { (void)t; (void)a; game_init++; return 1; }
static uint64_t g_decide(void* t, uint64_t a) { (void)t; (void)a; game_decide++; return 7; }
static uint64_t g_cancel(void* t, uint64_t a) { (void)t; (void)a; game_cancel++; return 8; }
static uint64_t g_dtor(void* t, uint64_t a) { (void)t; (void)a; game_dtor++; return 0; }
static void g_list_set(void* t, uint32_t list, uint32_t idx, uint32_t f, float a, float b)
{ (void)t; (void)list; (void)f; (void)a; (void)b; list_sets++; last_list_idx = idx; }
/* the trampolines: what the game's own functions do after the hook */
static uint64_t g_insert(void* t, uint64_t row) { s_push((char*)t + 0x100, (void*)(uintptr_t)row); return 0; }
static uint64_t g_pick(void* t, uint64_t team)
{
  rvec* v = (rvec*)((char*)t + 0x100);
  for (uint64_t i = 0; i < nrows(v); i++) {
    char* r = v->b + i * ROW;
    for (char* c = *(char**)(r + 8); c && c < *(char**)(r + 0x10); c += 0x50)
      if (*(uint32_t*)c == (uint32_t)team) { *(uint32_t*)((char*)t + 0x118) = (uint32_t)i; return 1; }
  }
  return 0;
}
static uint64_t g_jump(void* t, uint64_t slot)
{
  rvec* v = (rvec*)((char*)t + 0x100);
  for (uint64_t i = 0; i < nrows(v); i++)
    if (*(uint32_t*)(v->b + i * ROW) == (uint32_t)slot) { *(uint32_t*)((char*)t + 0x118) = (uint32_t)i; return 1; }
  return 0;
}
/* Competition Info */
static const uint32_t* ci_regions; static int ci_nregions;
static int ci_cells, ci_counts, ci_previews, ci_decides;
static uint32_t ci_count_last;
static void c_reserve(void* v, uint64_t cap)
{
  uvec* x = v;
  uint64_t n = x->b ? (uint64_t)(x->e - x->b) : 0;
  uint32_t* nb = malloc(cap * 4);
  if (n) memcpy(nb, x->b, n * 4);
  free(x->b);
  x->b = nb; x->e = nb + n; x->c = nb + cap;
}
static uint64_t c_init(void* t, uint64_t a)
{
  (void)a;
  uvec* v = (uvec*)((char*)t + 0x90);
  c_reserve(v, ci_nregions);
  for (int i = 0; i < ci_nregions; i++) *v->e++ = ci_regions[i];
  return 1;
}
static uint64_t c_decide(void* t, uint64_t a) { (void)t; (void)a; ci_decides++; return 5; }
static uint64_t c_dtor(void* t, uint64_t a) { (void)a; uvec* v = (uvec*)((char*)t + 0x90); free(v->b); memset(v, 0, sizeof *v); return 0; }
static uint64_t c_cells(void* t) { (void)t; ci_cells++; return 0; }
static void c_count(void* t, uint32_t l, uint32_t n, uint32_t one, uint32_t vis) { (void)t; (void)l; (void)one; (void)vis; ci_counts++; ci_count_last = n; }
static uint32_t ci_preview_region;
static uint64_t c_preview(void* t, uint64_t a) { (void)t; ci_previews++; ci_preview_region = (uint32_t)a; return 0; }
static int ci_cancels;
static uint64_t c_cancel(void* t, uint64_t a) { (void)t; (void)a; ci_cancels++; return 9; }
/* a region's competitions, as the game gives them: REGULATION ids (0x1414ce270 pushes the live
   record's +0x00). Region 1 the club competitions' -- regulation -> competition as in FL 2027 and
   the GigaPack: 1 -> 1 (CWC), 2 -> 2 (UCL), 5, 6, 1029 -> 3 (UEL), 4 -> 4, 8, 9 -> 5 (Libertadores),
   100 -> 100 (ICC), 250 -> 250, 621, 622 -> 516 (Sudamericana), 516 a regulation of the UEL (3),
   777 one with no record; any other region one of its own */
static const struct { uint16_t rid; uint32_t cid; } CLUB_REGS[] = {
  { 1, 1 }, { 2, 2 }, { 5, 3 }, { 6, 3 }, { 4, 4 }, { 8, 5 }, { 9, 5 }, { 100, 100 }, { 1029, 3 },
  { 250, 250 }, { 621, 516 }, { 622, 516 }, { 516, 3 }, { 777, 0 } };
#define NCLUB ((int)(sizeof CLUB_REGS / sizeof CLUB_REGS[0]))
static void* c_comps(void* region, void* out)
{
  hvec* v = out;
  uint32_t r = *(uint32_t*)region;
  int n = r == 1 ? NCLUB : 1;
  v->b = malloc(n * 2); v->e = v->b + n; v->c = v->e;
  for (int i = 0; i < n; i++) v->b[i] = r == 1 ? CLUB_REGS[i].rid : (uint16_t)(r + 1000);
  return out;
}
/* the game (+0x48 its data) and a regulation's live record by id: +0x00 the id, +0x80 the
   competition; an id of none gives the dummy, whose id is not it (and whose +0x80 says 1, so a
   check of the id is what keeps it out) */
static char r_data[8];
static char* r_game(void) { static char game[0x50]; *(void**)(game + GAME_DATA) = r_data; return game; }
static int r_finds, r_bad_data;
static char* r_find(void* data, uint32_t rid)
{
  static char recs[NCLUB][0x314], dummy[0x314];
  r_finds++;
  if (data != r_data) r_bad_data++;
  for (int i = 0; i < NCLUB; i++)
    if (CLUB_REGS[i].rid == (uint16_t)rid && CLUB_REGS[i].cid) {
      *(uint16_t*)recs[i] = CLUB_REGS[i].rid;
      *(uint32_t*)(recs[i] + REG_CID) = CLUB_REGS[i].cid;
      return recs[i];
    }
  *(uint16_t*)dummy = 0xffff;
  *(uint32_t*)(dummy + REG_CID) = 1;
  return dummy;
}
static uint32_t c_cur_list(void* t) { (void)t; return 0; }
static uint32_t ci_cursor;
static uint32_t c_cur_index(void* t, uint32_t l) { (void)t; (void)l; return ci_cursor; }
static void* c_label(void* out, uint32_t r) { char b[16]; int n = snprintf(b, sizeof b, "R%u", r); set_str(out, b, n); return out; }
static void* c_assign(void* d, const void* s, uint64_t p, uint64_t n) { (void)p; (void)n; str_copy(d, s); return d; }

/* a row's emblem: the game's (any row) and the image calls of a competition's */
static int e_games, e_shows;
static uint32_t e_game_slot, e_comp_id, e_comp_size;
static void e_game(void* i, void* f, uint32_t slot, void* p) { (void)i; (void)f; (void)p; e_games++; e_game_slot = slot; }
static void e_show(void* w, uint32_t on, uint32_t k) { (void)w; (void)on; (void)k; e_shows++; }
static uint32_t e_size(void* i, uint32_t* cid) { (void)i; (void)cid; return 7; }
static uint32_t e_comp(void* i, uint32_t cid, uint32_t size, uint32_t z) { (void)i; (void)z; e_comp_id = cid; e_comp_size = size; return 1; }

/* League Info's builder: what the game gave slot 123 -- the Club World Cup, three Intercontinental
   cups, two empty emblems, a league above and below */
static int i_games;
static uint32_t* i_game(uint32_t* r, uint32_t league)
{
  static const uint32_t JUNK[9] = { 0, 1, 100, 101, 102, 0, 0, 40, 41 };
  i_games++;
  memcpy(r, JUNK, sizeof JUNK);
  r[0] = league;
  return r;
}

/* the slot under the cursor */
static uint32_t s_slot;
static int s_games;
static uint32_t s_game(void* t) { (void)t; s_games++; return s_slot; }

static void thunk(uint64_t va, void* fn)
{
  unsigned char* p = (unsigned char*)(uintptr_t)VA(va);
  jmp_rax(p, 0, (uint64_t)(uintptr_t)fn);
}

static const char* label(uint32_t r)
{
  static char s[4][0x20]; static int k;
  char* o = s[k++ & 3];
  cg_label(o, r);
  return str_of(o);
}

/* how many bytes of two images differ, and where the first one is */
static size_t diff_count(const unsigned char* a, const unsigned char* b, size_t n, size_t* first)
{
  size_t k = 0;
  for (size_t i = 0; i < n; i++) if (a[i] != b[i] && !k++) *first = i;
  return k;
}
#define BS "\\"
#define NL "\n"

int main(void)
{
  unsigned char* img = VirtualAlloc(0, 0x2800000, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
  if (!img) { printf("no memory\n"); return 1; }
  B = (uint64_t)(uintptr_t)img;
  {                                                  /* the byte checks with another module's jump on an entry */
    static const unsigned char REG_E[] = { 0x40, 0x53, 0x48, 0x83, 0xec, 0x20, 0xb8, 0xff, 0xff, 0x00, 0x00,
      0x44, 0x0f, 0xb7, 0xc2, 0x48, 0x8b, 0xd9, 0x66, 0x3b };
    const char* reg_hex = "40534883ec20b8ffff0000440fb7c2488bd9663b";
    unsigned char* p = (unsigned char*)(uintptr_t)VA(REG_FIND);
    memcpy(p, REG_E, sizeof REG_E);
    CHECK(sig_state(REG_FIND, reg_hex) == 1, "0x1414bb000 as the game has it");
    p[0] = 0xe9; p[1] = 0x53; p[2] = 0x50; p[3] = 0xb2; p[4] = 0xfe; p[5] = 0x90;   /* fl26compcache's */
    CHECK(sig_state(REG_FIND, reg_hex) == 2, "0x1414bb000 behind fl26compcache's jmp; nop: called through it");
    p[6] = 0xb9;
    CHECK(sig_state(REG_FIND, reg_hex) == 0, "behind a jump, but the rest is not the game's: off");
    memcpy(p, REG_E, sizeof REG_E);
    p[0] = 0xe9; p[1] = 0; p[2] = 0; p[3] = 0; p[4] = 0;
    CHECK(sig_state(REG_FIND, reg_hex) == 2, "a bare 5-byte jump, the rest the game's: called through it");
    p[0] = 0xe8;
    CHECK(sig_state(REG_FIND, reg_hex) == 0, "a call, not a jump, on the entry: off");
    unsigned char* q = (unsigned char*)(uintptr_t)VA(TSC_PICK);
    const char* pick_hex = "4889742418574883ec308b05";
    for (int i = 0; i < 12; i++) { unsigned v; sscanf(pick_hex + 2 * i, "%2x", &v); q[i] = (unsigned char)v; }
    CHECK(sig_state(TSC_PICK, pick_hex) == 1, "a site this DLL hooks, the game's bytes");
    q[0] = 0xe9; q[1] = q[2] = q[3] = q[4] = 0;
    CHECK(sig_state(TSC_PICK, pick_hex) == 0, "a site this DLL hooks behind another's jump: off");
    memset(p, 0, 32); memset(q, 0, 32);
  }
  thunk(ROWS_CLEAR, s_clear); thunk(ROWS_PUSH, s_push); thunk(ROWS_FREE, s_free);
  thunk(TSC_INIT, g_init); thunk(TSC_DECIDE, g_decide); thunk(TSC_CANCEL, g_cancel); thunk(TSC_DTOR, g_dtor);
  thunk(LIST_SET, g_list_set);
  thunk(CI_INIT, c_init); thunk(CI_DECIDE, c_decide); thunk(CI_DTOR, c_dtor); thunk(CI_CELLS, c_cells);
  thunk(CI_COUNT, c_count); thunk(CI_PREVIEW, c_preview); thunk(CI_RESERVE, c_reserve); thunk(CI_CANCEL, c_cancel);
  thunk(CUR_LIST, c_cur_list); thunk(CUR_INDEX, c_cur_index); thunk(LABEL_FN, c_label); thunk(STR_ASSIGN, c_assign);
  thunk(REGION_COMPS, c_comps); thunk(GAME_FN, r_game); thunk(REG_FIND, r_find);
  t_insert = g_insert; t_pick = g_pick; t_jump = g_jump;

  tables_init();
  /* UEFA 7 50 (England) 8 (France) 51 (Spain), CONMEBOL 13 (Brazil), CONCACAF 17 (USA), AFC 102
     (China), CAF 300 (no country: the "other clubs") */
  fl26_confgroups_slot(7, 0); fl26_confgroups_slot(50, 0); fl26_confgroups_slot(8, 0); fl26_confgroups_slot(51, 0);
  fl26_confgroups_slot(13, 1); fl26_confgroups_slot(17, 2); fl26_confgroups_slot(102, 3); fl26_confgroups_slot(300, 4);
  fl26_confgroups_country(7, 10); fl26_confgroups_country(50, 10); fl26_confgroups_country(8, 11);
  fl26_confgroups_country(51, 12); fl26_confgroups_country(13, 20); fl26_confgroups_country(17, 30);
  fl26_confgroups_country(102, 40);
  fl26_confgroups_cname(10, "England"); fl26_confgroups_cname(11, "France"); fl26_confgroups_cname(12, "Spain");
  fl26_confgroups_cname(20, "Brazil"); fl26_confgroups_cname(30, "USA"); fl26_confgroups_cname(40, "China");

  /* ---------------- Select Team ---------------- */
  static char obj[0x170];
  char* t = obj;
  const uint32_t S1[] = { 7, 50, 8, 13, 17, 102, 300, 0, 1, 257 };
  put_rows(t, S1, 10);
  ts_init(t, 0);
  CHECK(game_init == 1, "the game's init ran (%d)", game_init);
  CHECK(shown(t) == 8, "5 confederations + 3 rows of no group shown (%llu)", (unsigned long long)shown(t));
  CHECK(!strcmp(name_at(t, 0), "+ UEFA (3)"), "row 0 '%s'", name_at(t, 0));
  CHECK(!strcmp(name_at(t, 1), "+ CONMEBOL (1)"), "row 1 '%s'", name_at(t, 1));
  CHECK(!strcmp(name_at(t, 4), "+ CAF (1)"), "row 4 '%s'", name_at(t, 4));
  CHECK(slot_at(t, 0) == HEAD_SLOT && slot_at(t, 5) == 0 && slot_at(t, 6) == 1 && slot_at(t, 7) == 257,
        "confederations on slot 123, then 0 1 257");
  CHECK(ts_cur(t) == 0, "cursor on the first confederation (%llu)", (unsigned long long)ts_cur(t));

  ts_decide(t, 0);                                   /* into UEFA */
  CHECK(game_decide == 0, "a confederation is not the game's decide");
  CHECK(shown(t) == 3 && !strcmp(name_at(t, 0), "- UEFA") && !strcmp(name_at(t, 1), "+ England (2)")
        && !strcmp(name_at(t, 2), "+ France (1)"), "UEFA: '%s' '%s' '%s'", name_at(t, 0), name_at(t, 1), name_at(t, 2));
  CHECK(slot_at(t, 0) == HEAD_SLOT && slot_at(t, 1) == 7 && slot_at(t, 2) == 8, "a country on its first league's slot");
  CHECK(is_header(((rvec*)(t + 0x100))->b + ROW), "a country row is ours");
  CHECK(ts_cur(t) == 1 && last_list_idx == 0 && list_sets == 1, "cursor on the first country (%llu)", (unsigned long long)ts_cur(t));

  ts_decide(t, 0);                                   /* into England */
  CHECK(shown(t) == 3 && !strcmp(name_at(t, 0), "- England") && slot_at(t, 1) == 7 && slot_at(t, 2) == 50
        && ts_cur(t) == 1, "England: its two leagues, cursor on the first");
  *(uint32_t*)(t + 0x118) = 2;                       /* a league: the game's */
  ts_decide(t, 0);
  CHECK(game_decide == 1, "a league is the game's decide");

  ts_cancel(t, 0);                                   /* Back: the countries, cursor on England */
  CHECK(game_cancel == 0 && shown(t) == 3 && ts_cur(t) == 1 && !strcmp(name_at(t, 1), "+ England (2)"),
        "Back from England (cursor %llu)", (unsigned long long)ts_cur(t));
  *(uint32_t*)(t + 0x118) = 2;
  ts_decide(t, 0);                                   /* France: one league, a level of its own too */
  CHECK(shown(t) == 2 && !strcmp(name_at(t, 0), "- France") && slot_at(t, 1) == 8, "France: '- France', 8");
  *(uint32_t*)(t + 0x118) = 0;
  ts_decide(t, 0);                                   /* Confirm on "- France": Back */
  CHECK(shown(t) == 3 && ts_cur(t) == 2, "'- France' goes back, cursor on France (%llu)", (unsigned long long)ts_cur(t));
  *(uint32_t*)(t + 0x118) = 0;
  ts_decide(t, 0);                                   /* "- UEFA": the confederations */
  CHECK(shown(t) == 8 && ts_cur(t) == 0, "'- UEFA' goes back, cursor on UEFA");
  ts_cancel(t, 0);
  CHECK(game_cancel == 1, "Back on the confederations is the game's");

  *(uint32_t*)(t + 0x118) = 4;                       /* CAF: its league of no country, a row of its own */
  ts_decide(t, 0);
  CHECK(shown(t) == 2 && !strcmp(name_at(t, 0), "- CAF") && slot_at(t, 1) == 300 && ts_cur(t) == 1, "CAF: 300 itself");
  ts_cancel(t, 0);
  CHECK(shown(t) == 8 && ts_cur(t) == 4, "Back from CAF, cursor on CAF");

  *(uint8_t*)(t + 0x9b) = 1;                         /* the club column: decide / cancel are the game's */
  ts_decide(t, 0); ts_cancel(t, 0);
  CHECK(game_decide == 2 && game_cancel == 2, "club column: the game's");
  *(uint8_t*)(t + 0x9b) = 0;

  ts_pick(t, 102 * 100 + 1);                         /* a team of China: AFC / China shown, the game finds it */
  CHECK(shown(t) == 2 && slot_at(t, ts_cur(t)) == 102 && ts_find(t)->ctry == 40,
        "team pick: China (cursor %llu slot %u)", (unsigned long long)ts_cur(t), slot_at(t, ts_cur(t)));
  ts_jump(t, 300);
  CHECK(shown(t) == 2 && slot_at(t, ts_cur(t)) == 300 && ts_find(t)->ctry == -1, "slot jump: CAF");
  ts_jump(t, 257);
  CHECK(shown(t) == 8 && slot_at(t, ts_cur(t)) == 257, "slot jump to a row of no group: the confederations");

  {                                                  /* a row added after init */
    char r[ROW];
    make_row(r, 51, 2, "L51");
    ts_insert(t, (uint64_t)(uintptr_t)r);
    row_free(r);
    tstate* s = ts_find(t);
    CHECK(s && nrows(&s->master) == 11 && s->nmem[0] == 4 && s->ccnt[12] == 1, "the new row is in the master rows");
    CHECK(!strcmp(name_at(t, 0), "+ UEFA (4)") && slot_at(t, ts_cur(t)) == 257, "UEFA counts it '%s'", name_at(t, 0));
  }
  ts_init(t, 0);                                     /* init again, nothing changed */
  CHECK(game_init == 2 && shown(t) == 8, "a second init leaves the layout");

  {                                                  /* the game rebuilds the vector behind our back */
    rvec* v = (rvec*)(t + 0x100);
    rvec old = *v; memset(v, 0, sizeof *v);
    for (char* r = old.b; r < old.e; r += ROW) s_push(v, r);
    s_free(&old);
    *(uint32_t*)(t + 0x118) = 0;
    int d = game_decide;
    ts_decide(t, 0);                                 /* what is left: 0 1 257 -- no group */
    int heads = 0;
    for (uint64_t i = 0; i < shown(t); i++) heads += is_header(((rvec*)(t + 0x100))->b + i * ROW);
    CHECK(!ts_find(t) && shown(t) == 3 && !heads && slot_at(t, 0) == 0 && game_decide == d + 1,
          "taken again: our rows stripped, the game's list and decide (%llu rows)", (unsigned long long)shown(t));
  }
  ts_dtor(t, 0);
  CHECK(game_dtor == 1 && !ts_find(t), "dtor: no state, the game's dtor");
  s_free((rvec*)(t + 0x100));

  /* too few groups: untouched */
  memset(obj, 0, sizeof obj);
  const uint32_t S2[] = { 7, 50, 8, 51, 0, 1 };
  put_rows(t, S2, 6);
  ts_init(t, 0);
  CHECK(!ts_find(t) && shown(t) == 6 && slot_at(t, 0) == 7, "one group only: the game's list");
  ts_dtor(t, 0);
  s_free((rvec*)(t + 0x100));

  /* the club column at init with the cursor on a Brazilian row */
  memset(obj, 0, sizeof obj);
  put_rows(t, S1, 10);
  *(uint32_t*)(t + 0x118) = 3;
  *(uint8_t*)(t + 0x9b) = 1;
  ts_init(t, 0);
  CHECK(ts_find(t) && ts_find(t)->open == 1 && ts_find(t)->ctry == 20 && slot_at(t, ts_cur(t)) == 13,
        "club column: CONMEBOL / Brazil, cursor on 13");
  ts_dtor(t, 0);
  s_free((rvec*)(t + 0x100));

  /* a preselected row of no group keeps the cursor */
  memset(obj, 0, sizeof obj);
  put_rows(t, S1, 10);
  *(uint32_t*)(t + 0x118) = 9;
  ts_init(t, 0);
  CHECK(ts_find(t) && ts_find(t)->open == -1 && slot_at(t, ts_cur(t)) == 257, "cursor stays on Other");
  ts_dtor(t, 0);
  s_free((rvec*)(t + 0x100));

  {                                                  /* Kick Off: init on an empty list, the rows after it */
    static char ko[0x170];
    char* k = ko;
    int gi = game_init;
    ts_init(k, 0);
    CHECK(game_init == gi + 1 && !ts_find(k) && shown(k) == 0, "empty at init: the game's init, nothing taken");
    for (int i = 0; i < 10; i++) {
      char r[ROW];
      char nm[8];
      snprintf(nm, sizeof nm, "K%u", S1[i]);
      make_row(r, S1[i], 2, nm);
      ts_insert(k, (uint64_t)(uintptr_t)r);
      row_free(r);
    }
    tstate* s = ts_find(k);
    CHECK(s && nrows(&s->master) == 10, "taken once the rows came in (%llu)", s ? (unsigned long long)nrows(&s->master) : 0ULL);
    CHECK(shown(k) == 8 && !strcmp(name_at(k, 0), "+ UEFA (3)") && ts_cur(k) == 0,
          "Kick Off: the confederations, cursor on UEFA ('%s', %llu rows)", name_at(k, 0), (unsigned long long)shown(k));
    ts_pick(k, 0);                                   /* the game's own cursor afterwards still works */
    ts_jump(k, 13);
    CHECK(ts_find(k)->open == 1 && slot_at(k, ts_cur(k)) == 13, "slot jump after a late take: Brazil's league");
    ts_dtor(k, 0);
    CHECK(!ts_find(k) && !ts_pending(k), "dtor: no state, not pending");
    s_free((rvec*)(k + 0x100));
    char* e = ko;                                    /* an empty list that never fills is never taken */
    ts_init(e, 0);
    ts_jump(e, 7);
    CHECK(!ts_find(e), "an empty list stays the game's");
    ts_dtor(e, 0);
  }

  /* ---------------- Competition Info ---------------- */
  fl26_confgroups_region(2, 0); fl26_confgroups_region(3, 0); fl26_confgroups_region(4, 0); fl26_confgroups_region(5, 0);
  fl26_confgroups_region(16, 1); fl26_confgroups_region(23, 2); fl26_confgroups_region(21, 3); fl26_confgroups_region(40, 4);
  const uint32_t R1[] = { 1, 26, 2, 3, 4, 5, 16, 23, 21, 40, 25 };
  ci_regions = R1; ci_nregions = 11;
  static char cobj[0xa8];
  char* c = cobj;
  ci_init(c, 0);
  uvec* cv = (uvec*)(c + 0x90);
  CHECK(cv->e - cv->b == 8 && cv->b[0] == 1 && cv->b[1] == 26 && cv->b[2] == PSEUDO && cv->b[6] == PSEUDO + 4 && cv->b[7] == 25,
        "1 26, five confederations, 25 (%d)", (int)(cv->e - cv->b));
  CHECK(ci_cells == 1 && ci_counts == 1 && ci_count_last == 8 && ci_previews == 1 && last_list_idx == 2
        && ci_preview_region == PSEUDO, "redrawn, 8 items, cursor and right side on UEFA (%u)", last_list_idx);
  CHECK(!strcmp(label(PSEUDO), "+ UEFA") && !strcmp(label(PSEUDO + 2), "+ CONCACAF") && !strcmp(label(2), "R2"),
        "labels '%s' '%s' '%s'", label(PSEUDO), label(PSEUDO + 2), label(2));
  ci_cursor = 2;
  ci_decide(c, 0);
  CHECK(ci_decides == 0 && cv->e - cv->b == 5 && cv->b[0] == PSEUDO && cv->b[1] == 2 && cv->b[4] == 5
        && last_list_idx == 1 && ci_preview_region == 2, "UEFA: '- UEFA' and its four countries, cursor and right side on the first");
  CHECK(!strcmp(label(PSEUDO), "- UEFA"), "label in it '%s'", label(PSEUDO));
  ci_cursor = 0;
  ci_decide(c, 0);
  CHECK(cv->e - cv->b == 8 && last_list_idx == 2 && !strcmp(label(PSEUDO), "+ UEFA"), "'- UEFA' goes back");
  ci_cursor = 3;
  ci_decide(c, 0);
  CHECK(cv->e - cv->b == 2 && cv->b[1] == 16 && last_list_idx == 1, "CONMEBOL");
  ci_cancel(c, 0);
  CHECK(ci_cancels == 0 && cv->e - cv->b == 8 && last_list_idx == 3, "Back: the confederations, cursor on CONMEBOL");
  ci_cancel(c, 0);
  CHECK(ci_cancels == 1, "Back on the confederations is the game's");
  ci_cursor = 3;
  ci_decide(c, 0);
  ci_cursor = 1;
  ci_decide(c, 0);
  CHECK(ci_decides == 1 && g_ci_last == 16, "a country is the game's decide, remembered");
  ci_dtor(c, 0);
  CHECK(!cs_find(c), "dtor: state gone");
  ci_init(c, 0);                                     /* back on the screen: CONMEBOL, cursor on 16 */
  CHECK(cv->e - cv->b == 2 && cv->b[last_list_idx] == 16, "the region entered is shown again (%u)", last_list_idx);
  ci_dtor(c, 0);

  {                                                  /* the right side of a confederation: its cups */
    fl26_confgroups_cup(0, 1); fl26_confgroups_cup(0, 2); fl26_confgroups_cup(0, 3); fl26_confgroups_cup(0, 250);
    hvec v = { 0, 0, 0 };
    uint32_t r = PSEUDO;
    cg_comps(&r, &v);
    /* the regulations of competitions 1, 2, 3 and 250, in the game's order (the right side shows
       one row per competition, emb_<+0x80>) */
    CHECK(v.e - v.b == 7 && v.b[0] == 1 && v.b[1] == 2 && v.b[2] == 5 && v.b[3] == 6 && v.b[4] == 1029
          && v.b[5] == 250 && v.b[6] == 516,
          "UEFA: the regulations of CWC, UCL, UEL, UECL of the club competitions (%d)", (int)(v.e - v.b));
    CHECK(r_finds == NCLUB && !r_bad_data, "every regulation looked up in the game's data (%d)", r_finds);
    free(v.b);
    /* + CONMEBOL (mato 17.11.): cups 1, 5, 516 are competition ids. Kept by regulation id this was
       regulations 1 and 5 -- the Club World Cup and the Europa League's league phase -- and no
       Libertadores or Sudamericana; by the record's competition: CWC, Libertadores, Sudamericana */
    fl26_confgroups_cup(1, 1); fl26_confgroups_cup(1, 5); fl26_confgroups_cup(1, 516);
    r = PSEUDO + 1;
    cg_comps(&r, &v);
    CHECK(v.e - v.b == 5 && v.b[0] == 1 && v.b[1] == 8 && v.b[2] == 9 && v.b[3] == 621 && v.b[4] == 622,
          "CONMEBOL: CWC, Libertadores, Sudamericana and no Europa League (%d)", (int)(v.e - v.b));
    int uel = 0;
    for (uint16_t* p = v.b; p < v.e; p++) if (*p == 5 || *p == 6 || *p == 1029 || *p == 516) uel++;
    CHECK(!uel, "CONMEBOL: no regulation of the Europa League (%d)", uel);
    free(v.b);
    r = PSEUDO + 5;
    cg_comps(&r, &v);
    CHECK(v.e == v.b, "OFC with no cups: nothing");
    free(v.b);
    r = 2;
    cg_comps(&r, &v);
    CHECK(v.e - v.b == 1 && v.b[0] == 1002, "a country: the game's");
    free(v.b);
  }

  {                                                  /* a row's emblem: a confederation's logo */
    thunk(ROW_EMBLEM, e_game); thunk(IMG_SHOW, e_show); thunk(IMG_SIZE, e_size); thunk(IMG_COMP, e_comp);
    fl26_confgroups_emblem(0, 9900); fl26_confgroups_emblem(4, 9904);
    static char row[ROW], img[0x200], frame[0x10];
    memcpy(row, our_row(HEAD_SLOT, "+ UEFA (%d)", 3), ROW);
    cg_emblem(img, frame, HEAD_SLOT, row + 0x40);
    CHECK(e_comp_id == 9900 && e_comp_size == 7 && !e_games && img[0x1c4] == 1 && e_shows == 2,
          "+ UEFA: emblem 9900 (%u, size %u, game %d)", e_comp_id, e_comp_size, e_games);
    memcpy(row, our_row(HEAD_SLOT, "- CAF"), ROW);
    cg_emblem(img, frame, HEAD_SLOT, row + 0x40);
    CHECK(e_comp_id == 9904 && !e_games, "- CAF: emblem 9904 (%u)", e_comp_id);
    memcpy(row, our_row(HEAD_SLOT, "+ AFC (1)"), ROW);
    cg_emblem(img, frame, HEAD_SLOT, row + 0x40);
    CHECK(e_games == 1 && e_game_slot == HEAD_SLOT, "AFC with no logo: the game's");
    memcpy(row, our_row(HEAD_SLOT, "+ UEFAX (1)"), ROW);
    cg_emblem(img, frame, HEAD_SLOT, row + 0x40);
    CHECK(e_games == 2, "a name that only starts with UEFA: the game's");
    memcpy(row, our_row(7, "+ England (2)"), ROW);
    cg_emblem(img, frame, 7, row + 0x40);
    CHECK(e_games == 3 && e_game_slot == 7, "a country row: the game's (its league's emblem)");
    fl26_confgroups_head(0, 7);                      /* `heads`: UEFA on slot 7 -- the logo still */
    memcpy(row, our_row(7, "+ UEFA (3)"), ROW);
    e_comp_id = 0;
    cg_emblem(img, frame, 7, row + 0x40);
    CHECK(e_comp_id == 9900 && e_games == 3, "+ UEFA on its heads slot: emblem 9900");
    fl26_confgroups_head(0, HEAD_SLOT);
  }

  {                                                  /* League Info (B402): a confederation's continental cups */
    thunk(INFO_FN, i_game);
    /* CONMEBOL's 1, 5, 516 are there since the right side's checks above */
    for (int i = 0; i < 9; i++) fl26_confgroups_cup(3, i ? 600 + i : 1);   /* AFC: CWC + 8 cups */
    memset(obj, 0, sizeof obj);
    put_rows(t, S1, 10);
    ts_init(t, 0);
    uint32_t info[9];
    *(uint32_t*)(t + 0x118) = 0;                     /* + UEFA (3): UCL, UEL, UECL -- no CWC */
    uint32_t* r = cg_info(info, 77, t);
    CHECK(r == info && i_games == 1 && info[0] == 77, "the game's builder first, its league kept");
    CHECK(info[1] == 2 && info[2] == 3 && info[3] == 250 && info[4] == ~0u && info[5] == ~0u && info[6] == ~0u,
          "+ UEFA: %u %u %u %d %d %d", info[1], info[2], info[3], (int)info[4], (int)info[5], (int)info[6]);
    CHECK(info[7] == ~0u && info[8] == ~0u, "+ UEFA: no league above or below");
    *(uint32_t*)(t + 0x118) = 1;                     /* + CONMEBOL: the Libertadores and our 516 */
    cg_info(info, 77, t);
    CHECK(info[1] == 5 && info[2] == 516 && info[3] == ~0u, "+ CONMEBOL: %u %u %d", info[1], info[2], (int)info[3]);
    *(uint32_t*)(t + 0x118) = 3;                     /* + AFC: six of its eight */
    cg_info(info, 77, t);
    CHECK(info[1] == 601 && info[6] == 606 && info[7] == ~0u, "+ AFC: the first six (%u .. %u)", info[1], info[6]);
    *(uint32_t*)(t + 0x118) = 4;                     /* + CAF, no cups; the builder gave no league */
    cg_info(info, ~0u, t);
    CHECK(info[0] == 0 && info[1] == ~0u && info[6] == ~0u && info[8] == ~0u, "+ CAF: empty, the panel still filled");
    *(uint32_t*)(t + 0x118) = 5;                     /* a row of the game's (slot 0): the game's */
    cg_info(info, 77, t);
    CHECK(info[1] == 1 && info[2] == 100 && info[5] == 0 && info[7] == 40, "a row of the game's: its League Info");
    *(uint32_t*)(t + 0x118) = 0;
    ts_decide(t, 0);                                 /* into UEFA: "- UEFA" is UEFA's, a country the game's */
    *(uint32_t*)(t + 0x118) = 0;
    cg_info(info, 77, t);
    CHECK(info[1] == 2 && info[3] == 250, "- UEFA: UEFA's cups");
    *(uint32_t*)(t + 0x118) = 1;
    cg_info(info, 77, t);
    CHECK(info[1] == 1 && info[7] == 40, "+ England: its league's League Info");
    ts_decide(t, 0);                                 /* into England: "- England" and its leagues the game's */
    *(uint32_t*)(t + 0x118) = 0;
    cg_info(info, 77, t);
    CHECK(info[1] == 1, "- England: its first league's League Info");
    *(uint32_t*)(t + 0x118) = 1;
    cg_info(info, 77, t);
    CHECK(info[1] == 1, "a league: the game's");
    ts_cancel(t, 0); ts_cancel(t, 0);
    *(uint32_t*)(t + 0x118) = 0;
    *(uint8_t*)(t + 0x9b) = 1;                       /* the club column: the game's */
    cg_info(info, 77, t);
    CHECK(info[1] == 1, "club column: the game's");
    *(uint8_t*)(t + 0x9b) = 0;
    static char other[0x170];                        /* a list this DLL did not take */
    cg_info(info, 77, other);
    CHECK(info[1] == 1 && i_games == 11, "a list of no state: the game's (%d)", i_games);

    /* the redraw: every confederation's row has slot 123, and the game redraws League Info only
       when the slot under the cursor changes -- in the game "+ CONMEBOL" kept UEFA's cups */
    thunk(SLOT_FN, s_game);
    static char panel[0x100], panel2[0x100];
    s_slot = HEAD_SLOT;
    *(uint32_t*)(t + 0x118) = 0;                     /* + UEFA, a new panel: redrawn */
    *(uint32_t*)(panel + INFO_LAST) = HEAD_SLOT;
    uint32_t sl = cg_slot(t, 0, panel);
    CHECK(sl == HEAD_SLOT && *(uint32_t*)(panel + INFO_LAST) != HEAD_SLOT, "+ UEFA: the slot, the panel redrawn");
    *(uint32_t*)(panel + INFO_LAST) = HEAD_SLOT;      /* the game keeps it */
    cg_slot(t, 0, panel);
    CHECK(*(uint32_t*)(panel + INFO_LAST) == HEAD_SLOT, "+ UEFA again: not redrawn");
    *(uint32_t*)(t + 0x118) = 1;                     /* + CONMEBOL, the same slot 123 */
    sl = cg_slot(t, 0, panel);
    CHECK(sl == HEAD_SLOT && *(uint32_t*)(panel + INFO_LAST) != HEAD_SLOT, "+ CONMEBOL: redrawn");
    *(uint32_t*)(panel + INFO_LAST) = HEAD_SLOT;
    *(uint32_t*)(t + 0x118) = 2;
    cg_slot(t, 0, panel);
    CHECK(*(uint32_t*)(panel + INFO_LAST) != HEAD_SLOT, "+ CONCACAF: redrawn");
    s_slot = 0; *(uint32_t*)(panel + INFO_LAST) = 0;
    *(uint32_t*)(t + 0x118) = 5;                     /* a row of the game's after a confederation: redrawn */
    cg_slot(t, 0, panel);
    CHECK(*(uint32_t*)(panel + INFO_LAST) != 0, "a row of the game's after + CONCACAF: redrawn");
    *(uint32_t*)(panel + INFO_LAST) = 0;
    cg_slot(t, 0, panel);
    CHECK(*(uint32_t*)(panel + INFO_LAST) == 0, "the game's row again: the game's alone");
    *(uint32_t*)(panel2 + INFO_LAST) = 0;            /* another screen's panel, a list of no state */
    sl = cg_slot(other, 0, panel2);
    CHECK(sl == 0 && *(uint32_t*)(panel2 + INFO_LAST) == 0, "a list of no state: untouched");
    CHECK(s_games == 7, "the game's getter every time (%d)", s_games);
    ts_dtor(t, 0);
    s_free((rvec*)(t + 0x100));
  }

  /* ---------------- the numbers of a club's three lines ---------------- */
  {
    static const unsigned char SIG[25] = {
      0xf3, 0x0f, 0x10, 0x05, 0x32, 0x63, 0x03, 0x01,     /* movss xmm0, [100.0] */
      0x0f, 0x2f, 0xc8, 0x77, 0x0c,                       /* comiss xmm1, xmm0; ja +12 */
      0xf3, 0x0f, 0x10, 0x05, 0x29, 0x33, 0x09, 0x01,     /* movss xmm0, [50.0] */
      0xf3, 0x0f, 0x5f, 0xc1 };                           /* maxss xmm0, xmm1 */
    const size_t IMG = 0x2800000;
    unsigned char* im = (unsigned char*)(uintptr_t)B;
    unsigned char* at = (unsigned char*)(uintptr_t)VA(NUM_SIG);
    unsigned char* was = malloc(IMG);
    char lg[2048];
    size_t where = 0;
    int rc;
    CHECK(NUM_BYTE - NUM_SIG == 17 && sizeof NUM_SIG_HEX - 1 == 50 && sizeof NUM_DONE_HEX - 1 == 50,
          "the byte is the 18th of the 25 checked");
    memset(at - 0x100, 0x90, 0x200);
    memcpy(at, SIG, 25);
    memcpy(was, im, IMG);
    fl26_confgroups_log(lg, sizeof lg);

    /* whose exe: the file's name, any folder, any case */
    CHECK(path_is_fl27("E:" BS "FL" BS "FL27" BS "game" BS "FL_2027.exe") && path_is_fl27("fl_2027.EXE")
          && path_is_fl27("D:/My Games/FL 27/FL_2027.exe"), "FL_2027.exe is FL 2027");
    CHECK(!path_is_fl27("E:" BS "FL" BS "FL26" BS "game" BS "FL_2026.exe") && !path_is_fl27("FL_2026.exe")
          && !path_is_fl27("PES2021.exe") && !path_is_fl27("E:" BS "FL_2027.exe" BS "FL_2026.exe")
          && !path_is_fl27("xFL_2027.exe") && !path_is_fl27("FL_2027.exe.bak") && !path_is_fl27(""),
          "FL_2026.exe (and any other name) is not");
    CHECK(!exe_is_fl27(), "this test's exe is not FL 2027");

    /* FL26, the very bytes FL 2027 has: nothing read, nothing written */
    rc = num_floor(path_is_fl27("E:" BS "FL" BS "FL26" BS "game" BS "FL_2026.exe"));
    fl26_confgroups_log(lg, sizeof lg);
    CHECK(rc == 1 && diff_count(im, was, IMG, &where) == 0, "FL26: 1, the image as it was (%d)", rc);
    CHECK(!strcmp(lg, "confgroups: team numbers: off not FL 2027" NL), "FL26: the line '%s'", lg);
    /* the export itself, in a process that is not FL_2027.exe (this one) */
    rc = fl26_confgroups_numbers(B);
    fl26_confgroups_log(lg, sizeof lg);
    CHECK(rc == 1 && diff_count(im, was, IMG, &where) == 0 && strstr(lg, "off not FL 2027"),
          "the export outside FL_2027.exe: 1, nothing written (%d)", rc);

    /* FL 2027, not its bytes: each of the 25 in turn, and the byte itself other than 0x29 */
    {
      int bad = 0;
      for (int i = 0; i < 25; i++) {
        at[i] ^= 0x40;
        memcpy(was + (at - im), at, 25);
        rc = num_floor(1);
        fl26_confgroups_log(lg, sizeof lg);
        if (rc != 2 || diff_count(im, was, IMG, &where) != 0 || !strstr(lg, "nothing written")) bad++;
        at[i] ^= 0x40;
        memcpy(was + (at - im), at, 25);
      }
      CHECK(bad == 0, "another byte anywhere in the 25: 2, nothing written (%d of 25 got through)", bad);
      CHECK(strstr(lg, "confgroups: team numbers: off bytes at 0x141508af6 are not FL 2027 1.00's") == lg
            && strstr(lg, "the game keeps its floor of 39"), "its line '%s'", lg);
    }
    CHECK(!memcmp(at, SIG, 25), "the 25 bytes are the game's again");

    /* FL 2027, its bytes: one byte, 0x29 -> 0x21 at 0x141508b07, and nothing else in the image */
    rc = num_floor(1);
    fl26_confgroups_log(lg, sizeof lg);
    CHECK(rc == 0 && diff_count(im, was, IMG, &where) == 1, "FL 2027: 0, one byte written (%d, %llu)", rc,
          (unsigned long long)diff_count(im, was, IMG, &where));
    CHECK(im + where == (unsigned char*)(uintptr_t)VA(NUM_BYTE) && where == 0x1508b07 && was[where] == 0x29
          && im[where] == 0x21, "0x29 -> 0x21 at 0x141508b07 (image +0x%llx: %02x)", (unsigned long long)where, im[where]);
    CHECK(strstr(lg, "confgroups: team numbers: ok -- ") == lg && !strchr(lg, 10)[1], "one line '%s'", lg);
    /* the movss now reads the float 8 bytes lower: rip-relative from the end of the instruction */
    CHECK(*(int32_t*)(at + 17) - *(int32_t*)(was + (at - im) + 17) == -8, "the reference moved 8 bytes down, to the 40.0");

    /* asked again: it is there, nothing more is written */
    memcpy(was, im, IMG);
    rc = num_floor(1);
    fl26_confgroups_log(lg, sizeof lg);
    CHECK(rc == 0 && diff_count(im, was, IMG, &where) == 0 && strstr(lg, "ok (already written)"), "a second ask writes nothing (%d)", rc);
    CHECK(!g_installed, "the lists were never asked for: the two do not hang together");
    free(was);
  }

  printf("test_confgroups: %d checks, %d failed\n", checks, fails);
  return fails ? 1 : 0;
}
