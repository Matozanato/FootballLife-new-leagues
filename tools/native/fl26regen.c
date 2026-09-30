/* fl26regen.dll -- regens that are new players: a new name from their own country, a new
 * potential, and the game's own growth on top.
 *
 * What the game does (measured 2026-09-30, docs/findings.md "regens"): nobody leaves the
 * database. At the New Year (day 364 -> 0) every player first ages by one, then a retiring
 * player is handed to 0x141534cc0(rec), which turns him back into a 16-year-old IN PLACE: same
 * id, same array slot, same name, same face. It pulls each of the 25 abilities back by the
 * growth from 16 to his age, then nudges them twice toward a target taken from the player's
 * side-table dword (block + 0x1676324 + index*4, bits 17..23 -- call it p; the target is
 * 0.5*p + 30), and keeps p. So a regenerated Messi is a 16-year-old Messi with Messi's
 * potential: the same star again, under the same name.
 *
 * The save does not keep names. On a load, 0x1412e5eb0 merges each saved player (0x9c-byte
 * record, id at +0x24) with the database record of the same id and copies the database name
 * back in; the saved age stays. So a name we give a regen is gone after every load unless we
 * give it again.
 *
 * What this does, with two wrapped functions:
 *
 *   0x141534cc0 regen(rec)  before: write a new p into the side table (a bell curve around
 *                           the database's middle, a rare high one), so the game's own two
 *                           passes pull the new 16-year-old toward HIS level, not the old
 *                           player's. after: a new name.
 *   0x1412e5eb0 unpack()    before: while the edit block still holds the database, remember
 *                           every id's database age. after: the saved ages are in; a real
 *                           player is exactly k years older than in the database (k = years
 *                           played, the same for all -- taken as the most common difference),
 *                           a regen is younger than that. Each regen gets its name again.
 *
 * The name is a pure function of the id and the database: the family name of one player of
 * the same nationality and the given name of another, in that nationality's own order
 * ("Sui Weijie" stays family-first), with the family name's own shirt spelling. The pools are
 * built once from the database (or, in a career that was never loaded, from the block before
 * the first regen -- the same names), sorted, so their order never depends on array order.
 * The same id always gets the same name, so a regen keeps it across saves and loads. A world
 * built again with other players can change a regen's name; nothing else can.
 *
 * The face: the game loads a real face (Asset\model\character\face\real\<id>\...) and a
 * portrait (common\render\symbol\player\<id>.dds) by the id alone -- no flag in
 * PlayerAppearance.bin tells it to (checked 2026-09-30 against the 14,487 players that have one).
 * So a regen shows the old player's face. fl26_regen_is(id) lets the Lua loader send those file
 * requests to a name that does not exist, and the game draws the generic face from the
 * player's appearance data instead.
 *
 * Nothing else is touched: no ability is written by us, the growth type is still the game's
 * own random pick, and a player the game does not regenerate is never looked at twice.
 *
 * Built with `zig cc` (tools/native/build-regen.sh). Our own code, no third-party binaries.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <stdarg.h>

#define REGEN_RVA   0x1534cc0
#define UNPACK_RVA  0x12e5eb0
#define OWNER_RVA   0x3705e10          /* block = [[exe + OWNER_RVA] + 0x48]                  */
#define COUNT_INSN  0x14bc9c8          /* mov eax, [rcx + disp32] -- the player count         */
#define SIDE_INSN   0x1534d19          /* lea r13, [rax + disp32] -- the side table (in regen)*/
#define SLIM_INSN   0x1534d28          /* mov ecx, imm32          -- side table size          */
#define BH1_INSN    0x12e5f0c          /* mov r13, [rip + disp32] -- saved players (unpack)   */
#define PH1_INSN    0x12e5f13          /* mov r12d, [rip + disp32] -- saved player count      */
#define APP_CNT_INSN 0x14bd16f         /* movzx eax, word [rcx + disp32] -- appearance count  */
#define APP_CAP_INSN 0x14bd17f         /* mov ecx, imm32                 -- appearance capacity */
#define APP_TAB_INSN 0x14bd1bd         /* lea rcx, [rdx + disp32]        -- appearance records */
#define APP_OWNER   0x60               /* appearance object = [[exe + OWNER_RVA] + 0x60]      */
#define APP_STRIDE  0x48               /* u32 id, 8 zero bytes, 56 appearance bytes, u32 zero */
#define APP_DATA    0x0c
#define APP_LEN     56

#define STRIDE    0x17c
#define R_AGE     0x1c                 /* & 0x3f, years                                       */
#define R_INDEX   0x2c                 /* u16, index into the side table                      */
#define R_ID      0x30
#define R_NAME    0x38
#define R_SHIRT   0x75
#define R_SHIRT2  0xb2
#define NAME_LEN  0x3d
#define R_NAT     0x144                /* & 0x1ff                                             */
#define SAVE_REC  0x9c
#define SAVE_ID   0x24

#define MAX_PLAYERS 200000
#define MAP_BITS  18
#define MIN_POOL  8

/* the first bytes of each function, as this build has them; both are position-free */
static const unsigned char SIG_REGEN[15]  = { 0x48,0x8b,0xc4, 0x55, 0x53, 0x56, 0x57, 0x41,0x54, 0x41,0x55, 0x41,0x56, 0x41,0x57 };
static const unsigned char SIG_UNPACK[19] = { 0x48,0x8b,0xc4, 0x55, 0x41,0x54, 0x41,0x55, 0x41,0x56, 0x41,0x57,
                                              0x48,0x8d,0xa8,0xa8,0xfb,0xff,0xff };

static uint64_t g_base;
static int      g_flags;               /* 1 = names, 2 = potential                            */
static uint32_t g_count_disp, g_side_disp, g_side_lim;
static uint64_t g_bh1, g_ph1;          /* addresses of the two unpack globals                 */
typedef void     (*regen_fn)(unsigned char*);
typedef uint64_t (*unpack_fn)(void*);
static regen_fn  g_regen;
static unpack_fn g_unpack;
static uint32_t  g_stat[8];            /* regens, named at regen, loads, named at load, k, pool size, potentials, skipped */
static uint64_t  g_rng;

/* ---- log the loader drains into sider.log ---- */
static char g_log[4096];
static volatile long g_log_len;
static void logf(const char* fmt, ...)
{
  char line[256];
  va_list ap; va_start(ap, fmt);
  int n = vsnprintf(line, sizeof line - 1, fmt, ap);
  va_end(ap);
  if (n < 0) return;
  if (n > (int)sizeof line - 2) n = (int)sizeof line - 2;
  line[n++] = '\n';
  long len = g_log_len;
  if (len + n >= (long)sizeof g_log) return;
  memcpy(g_log + len, line, n);
  g_log_len = len + n;
}

static unsigned char* block(void)
{
  unsigned char* owner = *(unsigned char**)(uintptr_t)(g_base + OWNER_RVA);
  return owner ? *(unsigned char**)(owner + 0x48) : 0;
}
static uint32_t player_count(unsigned char* blk)
{
  uint32_t n = *(uint32_t*)(blk + g_count_disp);
  return n > MAX_PLAYERS ? 0 : n;
}
static uint64_t mix(uint64_t x)
{
  x += 0x9e3779b97f4a7c15ull;
  x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ull;
  x = (x ^ (x >> 27)) * 0x94d049bb133111ebull;
  return x ^ (x >> 31);
}

/* ---- folding: "Nenê" -> "NENE", so a name can be matched against its shirt spelling ---- */
static const char* const FOLD[192] = {
"A","A","A","A","A","A","AE","C","E","E","E","E","I","I","I","I","D","N","O","O","O","O","O","","O","U","U","U","U","Y","TH","SS","A","A","A","A","A","A","AE","C","E","E","E","E","I","I","I","I","D","N","O","O","O","O","O","","O","U","U","U","U","Y","TH","Y","A","A","A","A","A","A","C","C","C","C","C","C","C","C","D","D","D","D","E","E","E","E","E","E","E","E","E","E","G","G","G","G","G","G","G","G","H","H","H","H","I","I","I","I","I","I","I","I","I","I","IJ","IJ","J","J","K","K","K","L","L","L","L","L","L","L","L","L","L","N","N","N","N","N","N","N","N","N","O","O","O","O","O","O","OE","OE","R","R","R","R","R","R","S","S","S","S","S","S","S","S","T","T","T","T","T","T","U","U","U","U","U","U","U","U","U","U","U","U","W","W","Y","Y","Y","Z","Z","Z","Z","Z","Z","S",};

/* A-Z and single spaces only; anything else is dropped */
static void fold(const char* s, char* out, int cap)
{
  int n = 0;
  const unsigned char* p = (const unsigned char*)s;
  while (*p && n < cap - 3) {
    unsigned c = *p;
    if (c < 0x80) {
      p++;
      if (c >= 'a' && c <= 'z') c -= 32;
      if ((c >= 'A' && c <= 'Z')) out[n++] = (char)c;
      else if (c == ' ' && n && out[n - 1] != ' ') out[n++] = ' ';
    } else if ((c & 0xe0) == 0xc0 && p[1]) {
      unsigned cp = ((c & 0x1f) << 6) | (p[1] & 0x3f);
      p += 2;
      if (cp >= 0xc0 && cp < 0x180) for (const char* f = FOLD[cp - 0xc0]; *f && n < cap - 1; f++) out[n++] = *f;
    } else {
      p++;
      while ((*p & 0xc0) == 0x80) p++;
    }
  }
  while (n && out[n - 1] == ' ') n--;
  out[n] = 0;
}

/* ---- name pools ---- */
typedef struct { uint16_t nat; uint8_t order; char given[NAME_LEN]; char family[NAME_LEN]; char shirt[NAME_LEN]; } entry_t;
static entry_t* g_pool;
static int      g_npool;
static int      g_nat_start[513], g_nat_end[513];

static int entry_cmp(const void* a, const void* b)
{
  const entry_t *x = a, *y = b;
  if (x->nat != y->nat) return x->nat < y->nat ? -1 : 1;
  if (x->order != y->order) return x->order < y->order ? -1 : 1;
  int c = strcmp(x->family, y->family);
  return c ? c : strcmp(x->given, y->given);
}

static void copy_field(char* dst, const char* src, int n)
{
  int len = 0;
  while (len < n - 1 && src[len]) len++;
  memcpy(dst, src, len); dst[len] = 0;
}

/* A player's name split into given and family parts, using the shirt name to tell which is
   which. 0 = given first ("Roque Santa Cruz", shirt SANTA CRUZ), 1 = family first ("Sui Weijie",
   shirt SUI), -1 = no clean split (one word, an initial, a shirt nickname). */
static int split(const char* name, const char* shirt, char* given, char* family, int* whole)
{
  *whole = 0;
  const char* sp = strchr(name, ' ');
  if (!sp || !shirt[0]) return -1;
  char fs[80], ft[80], fh[80], head[NAME_LEN];
  fold(shirt, fs, sizeof fs);
  if (!fs[0]) return -1;
  int hl = (int)(sp - name); if (hl >= NAME_LEN) return -1;
  memcpy(head, name, hl); head[hl] = 0;
  fold(sp + 1, ft, sizeof ft);
  fold(head, fh, sizeof fh);
  if (strchr(head, '.') || strchr(sp + 1, '.')) return -1;
  if (!strcmp(ft, fs)) { copy_field(given, head, NAME_LEN); copy_field(family, sp + 1, NAME_LEN); return 0; }
  if (!strcmp(fh, fs)) { copy_field(family, head, NAME_LEN); copy_field(given, sp + 1, NAME_LEN); return 1; }
  /* "Wu Lei", shirt WU LEI: the whole name on the shirt. In China and Korea that is the rule,
     and the name is family first; build_pools decides per country whether to believe it. */
  char fn[80]; fold(name, fn, sizeof fn);
  if (!strcmp(fn, fs) && !strchr(sp + 1, ' ')) {
    copy_field(family, head, NAME_LEN); copy_field(given, sp + 1, NAME_LEN); *whole = 1;
  }
  return -1;
}

static void build_pools(unsigned char* blk, uint32_t n)
{
  if (g_pool || !blk || !n) return;
  entry_t* e = (entry_t*)malloc((size_t)n * sizeof(entry_t));
  if (!e) return;
  /* two passes. The first counts per country the given-first names, the family-first names and
     the whole-name shirts (those vote family-first). The second keeps only the country's own
     order: a family-first name in Spain or Brazil is almost always a first-name shirt ("Rodrigo
     Bondoso", shirt RODRIGO), and a given-first name in China the odd western spelling. */
  static int first[513], last[513];
  memset(first, 0, sizeof first); memset(last, 0, sizeof last);
  int k = 0;
  for (int pass = 0; pass < 2; pass++)
  for (uint32_t i = 0; i < n; i++) {
    unsigned char* r = blk + (size_t)i * STRIDE;
    if (!*(uint32_t*)(r + R_ID)) continue;
    char name[NAME_LEN + 1], shirt[NAME_LEN + 1];
    memcpy(name, r + R_NAME, NAME_LEN); name[NAME_LEN] = 0;
    memcpy(shirt, r + R_SHIRT, NAME_LEN); shirt[NAME_LEN] = 0;
    unsigned nat = *(uint16_t*)(r + R_NAT) & 0x1ff;
    int w1;
    int o = split(name, shirt, e[k].given, e[k].family, &w1);
    if (pass == 0) { if (o == 0) first[nat]++; else if (o == 1 || w1) last[nat]++; continue; }
    int own = last[nat] > first[nat];
    if (o < 0) {
      if (!w1 || !own) continue;
      o = 1;
      fold(e[k].family, shirt, NAME_LEN);      /* the family name alone on the shirt */
    }
    if (o != own) continue;
    copy_field(e[k].shirt, shirt, NAME_LEN);
    e[k].order = (uint8_t)o;
    e[k].nat = (uint16_t)nat;
    k++;
  }
  qsort(e, k, sizeof *e, entry_cmp);
  int w = 0;                                   /* the same name twice counts once */
  for (int i = 0; i < k; i++) if (!w || entry_cmp(&e[w - 1], &e[i])) e[w++] = e[i];
  for (int i = 0; i < 513; i++) g_nat_start[i] = g_nat_end[i] = 0;
  for (int i = 0; i < w; i++) {
    if (i == 0 || e[i].nat != e[i - 1].nat) g_nat_start[e[i].nat] = i;
    g_nat_end[e[i].nat] = i + 1;
  }
  g_pool = e; g_npool = w; g_stat[5] = (uint32_t)w;
  logf("name pools: %d names from %u players", w, n);
}

static void put_name(unsigned char* dst, const char* s)
{
  int len = (int)strlen(s);
  if (len > NAME_LEN - 1) {                    /* never cut a UTF-8 letter in half */
    len = NAME_LEN - 1;
    while (len && ((unsigned char)s[len] & 0xc0) == 0x80) len--;
  }
  memset(dst, 0, NAME_LEN);
  memcpy(dst, s, len);
}

/* the new name of player `id`: 1 if written */
static int rename_player(unsigned char* r)
{
  if (!g_pool || !g_npool) return 0;
  uint32_t id = *(uint32_t*)(r + R_ID);
  unsigned nat = *(uint16_t*)(r + R_NAT) & 0x1ff;
  int s = g_nat_start[nat], e = g_nat_end[nat];
  if (e - s < MIN_POOL) { s = 0; e = g_npool; }  /* too few names of that country: any */
  int n = e - s;
  char old[NAME_LEN + 1]; memcpy(old, r + R_NAME, NAME_LEN); old[NAME_LEN] = 0;
  uint64_t h = mix((uint64_t)id * 0x2545f4914f6cdd1dull + 0xf126e6);
  for (int t = 0; t < 16; t++, h = mix(h)) {
    const entry_t* fam = &g_pool[s + (int)(h % (uint64_t)n)];
    const entry_t* giv = 0;
    uint64_t g = mix(h ^ 0x51ed);
    for (int u = 0; u < n && !giv; u++) {
      const entry_t* c = &g_pool[s + (int)((g + (uint64_t)u) % (uint64_t)n)];
      if (c->order == fam->order && strcmp(c->given, fam->given)) giv = c;
    }
    if (!giv) continue;
    char name[2 * NAME_LEN + 2];
    if (fam->order == 0) snprintf(name, sizeof name, "%s %s", giv->given, fam->family);
    else                 snprintf(name, sizeof name, "%s %s", fam->family, giv->given);
    if (!strcmp(name, old)) continue;
    put_name(r + R_NAME, name);
    put_name(r + R_SHIRT, fam->shirt);
    put_name(r + R_SHIRT2, fam->shirt);
    return 1;
  }
  return 0;
}

/* ---- potential: a bell curve 58..88 around 73, and one in thirty a gem up to 97 ---- */
static unsigned draw_potential(uint32_t id)
{
  g_rng = mix(g_rng ^ id ^ GetTickCount64());
  uint64_t r = g_rng;
  unsigned p = 58 + (unsigned)(r % 11) + (unsigned)((r >> 8) % 11) + (unsigned)((r >> 16) % 11);
  if (((r >> 24) % 30) == 0) p += 5 + (unsigned)((r >> 32) % 5);
  return p > 99 ? 99 : p;
}

/* ---- which ids are regens: the loader asks, so it can hide their real face ---- */
#define SET_BITS 20                            /* ids below 1,048,576 (NewLife goes to 999,999) */
static uint8_t g_regen_set[(1u << SET_BITS) / 8];
static void set_regen(uint32_t id) { if (id < (1u << SET_BITS)) g_regen_set[id >> 3] |= (uint8_t)(1u << (id & 7)); }

/* ---- faces: a regen gets one of a few pack faces of his part of the world ----
 *
 * The game draws a player from a sorted table of 72-byte records at [[exe + 0x3705e10] + 0x60]
 * + 0x50910 (count u16 at + 0x260552), filled from PlayerAppearance.bin: u32 id, 8 zero bytes,
 * the 56 bytes of that file's record after the id. Writing other bytes into a record (keeping
 * the id) changes the 3D face the game renders for that id. The pack file (fl26regen_faces.bin,
 * shipped with the portraits, not with this code) holds a nationality -> group map and a list of
 * faces, each a group, a portrait number and the 56 bytes. A regen gets face mix(id) of his
 * group, so the same regen always gets the same face and the same portrait
 * (common\render\symbol\player\regen\<number>.dds, the loader rewrites the request). The
 * records are written again every so often (the loader calls fl26_regen_faces), so a table the
 * game builds again gets them back. */
typedef struct { uint8_t group, pad; uint16_t key; uint8_t data[APP_LEN]; } face_t;
static uint8_t  g_nat_group[512];
static face_t*  g_faces;
static int      g_nfaces;
static uint32_t g_app_cnt_disp, g_app_cap, g_app_tab_disp;
#define MAX_RLIST 65536
static uint32_t g_rlist_id[MAX_RLIST];
static int16_t  g_rlist_face[MAX_RLIST];
static int      g_nrlist;

static int face_of(uint32_t id, unsigned nat)
{
  if (!g_nfaces) return -1;
  /* a nationality the pack does not place, or a group without faces: any face of the pack */
  int g = nat < 512 ? g_nat_group[nat] : 0xff, n = 0;
  for (int i = 0; i < g_nfaces; i++) n += g_faces[i].group == g;
  if (!n) { g = -1; n = g_nfaces; }
  int k = (int)(mix(id ^ 0x5eedfaceull) % (uint64_t)n);
  for (int i = 0; i < g_nfaces; i++) if ((g < 0 || g_faces[i].group == g) && k-- == 0) return i;
  return -1;
}
static unsigned char* app_record(uint32_t id)
{
  unsigned char* owner = *(unsigned char**)(uintptr_t)(g_base + OWNER_RVA);
  unsigned char* obj = owner ? *(unsigned char**)(owner + APP_OWNER) : 0;
  if (!obj || !g_app_tab_disp) return 0;
  unsigned n = *(uint16_t*)(obj + g_app_cnt_disp);
  if (n > g_app_cap) return 0;
  unsigned char* t = obj + g_app_tab_disp;
  unsigned lo = 0, hi = n;                     /* the game's own order: unsigned ids, 0 last */
  while (lo < hi) {
    unsigned mid = (lo + hi) / 2;
    uint32_t v = *(uint32_t*)(t + (size_t)mid * APP_STRIDE);
    if (v - 1 < id - 1) lo = mid + 1; else hi = mid;
  }
  return lo < n && *(uint32_t*)(t + (size_t)lo * APP_STRIDE) == id ? t + (size_t)lo * APP_STRIDE : 0;
}
static int apply_face(uint32_t id, int f)
{
  unsigned char* r = f >= 0 ? app_record(id) : 0;
  if (!r) return 0;
  if (memcmp(r + APP_DATA, g_faces[f].data, APP_LEN)) memcpy(r + APP_DATA, g_faces[f].data, APP_LEN);
  return 1;
}
static void note_regen(unsigned char* rec)
{
  uint32_t id = *(uint32_t*)(rec + R_ID);
  if (id >= (1u << SET_BITS) || (g_regen_set[id >> 3] >> (id & 7) & 1)) return;
  set_regen(id);
  if (g_nrlist >= MAX_RLIST) return;
  int f = face_of(id, *(uint16_t*)(rec + R_NAT) & 0x1ff);
  g_rlist_id[g_nrlist] = id; g_rlist_face[g_nrlist] = (int16_t)f; g_nrlist++;
  apply_face(id, f);
}

/* ---- the two wrappers ---- */
static void regen_hook(unsigned char* rec)
{
  unsigned char* blk = block();
  if (rec && blk) {
    g_stat[0]++;
    if (g_flags & 1) build_pools(blk, player_count(blk));    /* before any regen is renamed */
    if (g_flags & 2) {
      unsigned idx = *(uint16_t*)(rec + R_INDEX);
      if (idx < g_side_lim) {                  /* the game itself writes entry 0 otherwise */
        uint32_t* side = (uint32_t*)(blk + g_side_disp) + idx;
        *side = (*side & ~(0x7fu << 17)) | (draw_potential(*(uint32_t*)(rec + R_ID)) << 17);
        g_stat[6]++;
      } else g_stat[7]++;
    }
  }
  g_regen(rec);
  if (rec) note_regen(rec);
  if (rec && (g_flags & 1) && rename_player(rec)) g_stat[1]++;
}

/* id -> database age, for one load */
static uint32_t* g_map_id;
static uint8_t*  g_map_age;
static void map_put(uint32_t id, uint8_t age)
{
  uint32_t m = (1u << MAP_BITS) - 1, i = (uint32_t)mix(id) & m;
  while (g_map_id[i] && g_map_id[i] != id) i = (i + 1) & m;
  g_map_id[i] = id; g_map_age[i] = age;
}
static int map_get(uint32_t id)
{
  uint32_t m = (1u << MAP_BITS) - 1, i = (uint32_t)mix(id) & m;
  while (g_map_id[i]) { if (g_map_id[i] == id) return g_map_age[i]; i = (i + 1) & m; }
  return -1;
}

static uint64_t unpack_hook(void* a)
{
  unsigned char* blk = (g_flags & 1) ? block() : 0;
  int have = 0;
  if (blk && *(uint64_t*)(uintptr_t)g_bh1 && g_map_id) {   /* a save is being read, block = database */
    uint32_t n = player_count(blk);
    build_pools(blk, n);
    memset(g_map_id, 0, sizeof(uint32_t) << MAP_BITS);
    for (uint32_t i = 0; i < n; i++) {
      unsigned char* r = blk + (size_t)i * STRIDE;
      uint32_t id = *(uint32_t*)(r + R_ID);
      if (id) map_put(id, r[R_AGE] & 0x3f);
    }
    have = n > 0;
  }
  uint64_t ret = g_unpack(a);
  if (have && (blk = block())) {
    g_stat[2]++;
    uint32_t n = player_count(blk), hist[128] = {0};
    for (uint32_t i = 0; i < n; i++) {
      unsigned char* r = blk + (size_t)i * STRIDE;
      int db = map_get(*(uint32_t*)(r + R_ID));
      if (db >= 0) hist[((r[R_AGE] & 0x3f) - db + 64) & 127]++;
    }
    int k = 0;
    for (int d = 1; d < 128; d++) if (hist[d] > hist[k]) k = d;
    k -= 64;
    g_stat[4] = (uint32_t)(k < 0 ? 0 : k);
    uint32_t named = 0;
    memset(g_regen_set, 0, sizeof g_regen_set);  /* another save: other regens */
    g_nrlist = 0;
    for (uint32_t i = 0; i < n; i++) {
      unsigned char* r = blk + (size_t)i * STRIDE;
      int db = map_get(*(uint32_t*)(r + R_ID));
      if (db < 0) continue;
      int age = r[R_AGE] & 0x3f;
      if (age - db != k && age < db + k) {
        note_regen(r);
        if (rename_player(r)) named++;
      }
    }
    g_stat[3] += named;
    logf("load: %u players, %d year(s) played, %u regens named again", n, k, named);
  }
  return ret;
}

/* ---- install ---- */
static void* wrap(unsigned char* target, int stolen, void* handler)
{
  unsigned char* t = (unsigned char*)VirtualAlloc(0, 64, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
  if (!t) return 0;
  memcpy(t, target, stolen);
  t[stolen] = 0xFF; t[stolen + 1] = 0x25; *(uint32_t*)(t + stolen + 2) = 0;
  *(uint64_t*)(t + stolen + 6) = (uint64_t)(uintptr_t)(target + stolen);
  DWORD old;
  if (!VirtualProtect(target, stolen, PAGE_EXECUTE_READWRITE, &old)) return 0;
  target[0] = 0xFF; target[1] = 0x25; *(uint32_t*)(target + 2) = 0;
  *(uint64_t*)(target + 6) = (uint64_t)(uintptr_t)handler;
  for (int i = 14; i < stolen; i++) target[i] = 0xCC;
  VirtualProtect(target, stolen, old, &old);
  FlushInstructionCache(GetCurrentProcess(), target, stolen);
  return t;
}

static uint64_t rip_target(uint64_t insn, int len)
{
  return insn + len + (uint64_t)(int64_t)*(int32_t*)(uintptr_t)(insn + len - 4);
}

/* 0 ok; 2 regen signature; 3 unpack signature; 4 an operand is not what it should be;
   5 memory; 6 wrap failed */
__declspec(dllexport) int fl26_regen_install(uint64_t exe_base, int flags)
{
  g_base = exe_base; g_flags = flags;
  unsigned char* regen  = (unsigned char*)(uintptr_t)(exe_base + REGEN_RVA);
  unsigned char* unpack = (unsigned char*)(uintptr_t)(exe_base + UNPACK_RVA);
  if (memcmp(regen, SIG_REGEN, sizeof SIG_REGEN)) return 2;
  if (memcmp(unpack, SIG_UNPACK, sizeof SIG_UNPACK)) return 3;
  const unsigned char* ci = (const unsigned char*)(uintptr_t)(exe_base + COUNT_INSN);
  const unsigned char* si = (const unsigned char*)(uintptr_t)(exe_base + SIDE_INSN);
  const unsigned char* li = (const unsigned char*)(uintptr_t)(exe_base + SLIM_INSN);
  const unsigned char* bi = (const unsigned char*)(uintptr_t)(exe_base + BH1_INSN);
  const unsigned char* pi = (const unsigned char*)(uintptr_t)(exe_base + PH1_INSN);
  if (ci[0] != 0x8b || ci[1] != 0x81) return 4;
  if (si[0] != 0x4c || si[1] != 0x8d || si[2] != 0xa8) return 4;
  if (li[0] != 0xb9) return 4;
  if (bi[0] != 0x4c || bi[1] != 0x8b || bi[2] != 0x2d) return 4;
  if (pi[0] != 0x44 || pi[1] != 0x8b || pi[2] != 0x25) return 4;
  g_count_disp = *(uint32_t*)(ci + 2);         /* a patch set may have moved the count */
  g_side_disp  = *(uint32_t*)(si + 3);
  g_side_lim   = *(uint32_t*)(li + 1);
  g_bh1 = rip_target(exe_base + BH1_INSN, 7);
  g_ph1 = rip_target(exe_base + PH1_INSN, 7);
  g_map_id  = (uint32_t*)calloc((size_t)1 << MAP_BITS, sizeof(uint32_t));
  g_map_age = (uint8_t*)calloc((size_t)1 << MAP_BITS, 1);
  if (!g_map_id || !g_map_age) return 5;
  const unsigned char* ai = (const unsigned char*)(uintptr_t)(exe_base + APP_CNT_INSN);
  const unsigned char* ak = (const unsigned char*)(uintptr_t)(exe_base + APP_CAP_INSN);
  const unsigned char* at = (const unsigned char*)(uintptr_t)(exe_base + APP_TAB_INSN);
  if (ai[0] == 0x0f && ai[1] == 0xb7 && ai[2] == 0x81 && ak[0] == 0xb9 &&
      at[0] == 0x48 && at[1] == 0x8d && at[2] == 0x8a) {  /* faces are optional: no table, no faces */
    g_app_cnt_disp = *(uint32_t*)(ai + 3);
    g_app_cap      = *(uint32_t*)(ak + 1);
    g_app_tab_disp = *(uint32_t*)(at + 3);
  }
  memset(g_nat_group, 0xff, sizeof g_nat_group);
  g_rng = mix(GetTickCount64());
  if (!(g_regen = (regen_fn)wrap(regen, sizeof SIG_REGEN, (void*)regen_hook))) return 6;
  if (!(g_unpack = (unpack_fn)wrap(unpack, sizeof SIG_UNPACK, (void*)unpack_hook))) return 6;
  logf("regen@%llx and load@%llx wrapped; names %s, potential %s; count at block+%#x, side table +%#x (%u)",
       (unsigned long long)(exe_base + REGEN_RVA), (unsigned long long)(exe_base + UNPACK_RVA),
       (flags & 1) ? "on" : "off", (flags & 2) ? "on" : "off", g_count_disp, g_side_disp, g_side_lim);
  return 0;
}

__declspec(dllexport) int fl26_regen_log(char* out, int cap)
{
  int n = (int)g_log_len; if (n > cap - 1) n = cap - 1; if (n < 0) n = 0;
  memcpy(out, g_log, n); out[n] = 0;
  if (n < g_log_len) { memmove(g_log, g_log + n, g_log_len - n); g_log_len -= n; } else g_log_len = 0;
  return n;
}

/* 1 if the player is a regen of this career (seen at a regen or at the last load) */
__declspec(dllexport) int fl26_regen_is(uint32_t id)
{
  return id < (1u << SET_BITS) && (g_regen_set[id >> 3] >> (id & 7) & 1);
}

/* the face pack: "FL26RF01", 512 bytes nationality -> group (0xff none), u32 n, n faces of
   60 bytes (u8 group, u8 0, u16 portrait number, 56 appearance bytes). Returns the face count. */
__declspec(dllexport) int fl26_regen_faces_load(const char* path)
{
  FILE* f = fopen(path, "rb");
  if (!f) return 0;
  char magic[8]; uint32_t n = 0; int ok = 0;
  if (fread(magic, 1, 8, f) == 8 && !memcmp(magic, "FL26RF01", 8) &&
      fread(g_nat_group, 1, 512, f) == 512 && fread(&n, 4, 1, f) == 1 && n > 0 && n < 4096 &&
      (g_faces = (face_t*)calloc(n, sizeof(face_t))) && fread(g_faces, sizeof(face_t), n, f) == n) ok = 1;
  fclose(f);
  if (!ok) { memset(g_nat_group, 0xff, sizeof g_nat_group); free(g_faces); g_faces = 0; return 0; }
  g_nfaces = (int)n;
  logf("face pack: %d faces%s", g_nfaces, g_app_tab_disp ? "" : " -- but the appearance table was not found, faces off");
  return g_app_tab_disp ? g_nfaces : 0;
}

/* the portrait number of a regen's face, or -1 (not a regen, or no face for him) */
__declspec(dllexport) int fl26_regen_face(uint32_t id)
{
  if (!fl26_regen_is(id)) return -1;
  for (int i = 0; i < g_nrlist; i++)
    if (g_rlist_id[i] == id) return g_rlist_face[i] < 0 ? -1 : g_faces[g_rlist_face[i]].key;
  return -1;
}

/* write every regen's face into the appearance table again; returns how many records it found */
__declspec(dllexport) int fl26_regen_faces(void)
{
  int n = 0;
  for (int i = 0; i < g_nrlist; i++) n += apply_face(g_rlist_id[i], g_rlist_face[i]);
  return n;
}

/* regens, named at regen, loads, named at load, years played at the last load, pool size,
   new potentials, regens past the side table */
__declspec(dllexport) void fl26_regen_stats(uint32_t* out8)
{
  for (int i = 0; i < 8; i++) out8[i] = g_stat[i];
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID r) { (void)h;(void)reason;(void)r; return TRUE; }
