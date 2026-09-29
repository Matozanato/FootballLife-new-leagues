/* fl26clubs.dll -- serve the Select Team club list of OUR leagues from OUR own regulations.
 *
 * Why (measured in a running game, 2026-09-21): the club list the Select Team screen shows is
 * kept per competition *slot*, not per competition -- 123 lists of 750 team ids in the edit
 * block, reached only through five accessors. The game fills them once at boot, and for 32 of
 * our 39 leagues it fills them correctly. Seven come out wrong:
 *
 *   slot  4  Italy D5   overwritten by the national-team group (slot list 0x14297d0c8)
 *   slot  5  Italy D4   overwritten by the classic-team group (slot list 0x14297d0c0)
 *   slot 69  Qatar      overwritten by the "Other" filler at 0x141ef8f00
 *   slot 73  Indonesia  overwritten by the same filler
 *   slot 72  Iran       never filled (3 foreign clubs), cause not established
 *   slot 75  France D3  never filled (1 foreign club), cause not established
 *   slot 80  Czechia    never filled (empty), cause not established
 *   slot 76  France D4  correct, plus 22 foreign clubs on top
 *   slot 77  France D5  correct, plus 10 classic teams and Italy D3's twenty on top
 *
 * Three different causes, and two of them not understood. Rather than chase each one, this
 * answers the question the screen actually asks. The two readers --
 *
 *   0x1414d62c0  count(this, slot) -> u16      (0 when slot >= 123)
 *   0x1414d6290  get(this, slot, i) -> u32     (-1 when out of range)
 *
 * -- are replaced outright, not wrapped: both are short, fully decoded, and position-dependent
 * in their first bytes (each begins with a bounds test and a short jump), so stealing a
 * prologue is not on. The replacements do exactly what the originals do for every slot but
 * ours, and for ours answer from the league's own regulation record instead:
 *
 *   block = [[exe + 0x3705e10] + 0x48]
 *   reg   = 0x1414bb000(block, regulation id)
 *   reg + 0x170: up to 48 club handles, terminated by 0xffffffff; team id = handle >> 14
 *
 * That lookup never returns null: on a miss, and before the edit data is ready at all, it
 * hands back a dummy record instead. So the record is only believed when the id it carries at
 * +0x00 is the one we asked for -- the same test the lookup itself makes.
 *
 * Nothing is written. The game's stored lists are left exactly as it built them, so a slot
 * that is not ours, and every other reader of those lists, sees no change at all. The list is
 * rebuilt on each count() call (one regulation lookup per list draw) and cached for the get()
 * calls that follow, so a new season or a load is picked up without any invalidation logic.
 *
 * If a regulation cannot be read, or holds no clubs, that slot falls through to the game's own
 * answer for that call -- a league we cannot serve looks exactly like it does today, never
 * empty-by-our-doing.
 *
 * 2026-09-26: the Master League club slot. When a Master League is created, 0x141263b40 gives
 * every club a slot (team +0x41c) by looking the club up in these same lists through these same
 * readers, and a club found on 69, 70 or 73 gets that slot even over its own league's. 69, 70,
 * 73 and 75 are the "other clubs" pools the season code fills the Club World Cup from. So a
 * league of ours on one of those slots, served from its regulation here, put all its clubs in
 * a Club World Cup pool. For calls from that one function, a served pool slot now gets the
 * game's own stored list with our league's clubs taken out: our clubs are not found there, they
 * end up with no slot (123, as France D4/D5 and Czechia always had), and the shipped pool clubs
 * keep theirs. Every other caller -- the menus -- is answered exactly as before.
 *
 * 2026-09-29: clubs of the game in our leagues (Mod Studio 0.1.4, GitHub #25/#33). A league of
 * ours may now take a club the game already has, either one in no league (the "other clubs"
 * the game shows under Other European / Latin American / Asian clubs) or one swapped out of a
 * shipped league. The tables make it a member of our league only, but the game's pool lists
 * (69, 70, 73, 75) are filled at boot by their own rule, so such a club could still be found
 * there -- and a club found on a pool slot takes that slot over its league's (above). The world
 * file names those clubs (a "nopool" line); fl26_clubs_keep_out() takes the list, and every
 * pool slot is then answered as the game stored it minus those clubs, for every caller: the
 * club shows under its new league only, and the Master League gives it that league's slot.
 * With no such line nothing of this runs.
 *
 * Built with `zig cc` (tools/native/build-clubs.sh). Our own code, no third-party binaries.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <string.h>
#include <stdio.h>
#include <stdarg.h>

#define COUNT_RVA  0x14d62c0   /* u16 count(void* this, unsigned slot)            */
#define GET_RVA    0x14d6290   /* u32 get(void* this, unsigned slot, unsigned i)  */
#define REG_RVA    0x14bb000   /* void* regulation(void* block, unsigned id)      */
#define OWNER_RVA  0x3705e10   /* global: owner; block = [owner+0x48]             */

#define SLOTS       123        /* the engine's slot count; 123 also means "none"  */
#define STRIDE      750        /* dwords per slot in the list array               */
#define COUNT_OFF   0x5a168    /* SLOTS * STRIDE * 4: where the u16 counts begin  */
#define REG_CLUBS   0x170      /* regulation record: club handle list             */
#define MAX_CLUBS   48         /* the game's own cap on that list                 */
#define HANDLE_SHIFT 14        /* handle = team_id << 14                          */

#define MAX_CFG     16

/* The three reader calls inside 0x141263b40 (the Master League club slot), as return addresses:
   count at 0x141263bd6 and 0x1412640ca, get at 0x141263bf9. */
#define SLOTFN_COUNT1_RET 0x1263bdb
#define SLOTFN_GET_RET    0x1263bfe
#define SLOTFN_COUNT2_RET 0x12640cf
static int is_pool(unsigned slot) { return slot == 69 || slot == 70 || slot == 73 || slot == 75; }
static int pool_index(unsigned slot)
{
  return slot == 69 ? 0 : slot == 70 ? 1 : slot == 73 ? 2 : slot == 75 ? 3 : -1;
}

#define MAX_KEEP 512

typedef struct { uint16_t slot; uint16_t reg; } fl26_clubs_cfg_t;

typedef void* (*reg_fn)(void*, unsigned);

static uint64_t g_base;
static fl26_clubs_cfg_t g_cfg[MAX_CFG];
static int      g_ncfg;
static uint32_t g_list[MAX_CFG][MAX_CLUBS];
static int      g_n[MAX_CFG];              /* -1 = no answer of ours for this slot */
static uint32_t g_stat[4];                 /* counts served, gets served, rebuilds, misses */
static uint32_t g_pool[STRIDE];            /* a pool slot's stored list minus our clubs      */
static int      g_npool = -1;
static unsigned g_pool_slot = SLOTS;
static uint32_t g_pool_calls;
static uint32_t g_keep[MAX_KEEP];          /* clubs of the game now in a league of ours      */
static int      g_nkeep;
static uint32_t g_kp[4][STRIDE];           /* each pool slot's stored list minus those clubs */
static int      g_kn[4] = { -1, -1, -1, -1 };

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

static void* block(void)
{
  unsigned char* owner = *(unsigned char**)(uintptr_t)(g_base + OWNER_RVA);
  return owner ? *(void**)(owner + 0x48) : 0;
}

static int cfg_index(unsigned slot)
{
  for (int i = 0; i < g_ncfg; i++) if (g_cfg[i].slot == slot) return i;
  return -1;
}

/* Read our league's clubs out of its own regulation record. Returns the count, 0 if the
   regulation is not there yet or holds nothing -- in which case the caller leaves the slot
   to the game. */
static int rebuild(int i)
{
  g_n[i] = -1;
  void* blk = block();
  if (!blk) return 0;
  void* reg = ((reg_fn)(uintptr_t)(g_base + REG_RVA))(blk, g_cfg[i].reg);
  /* a miss, or data not loaded yet, gives the dummy record -- it carries a different id */
  if (!reg || *(uint16_t*)reg != g_cfg[i].reg) return 0;
  uint32_t* h = (uint32_t*)((unsigned char*)reg + REG_CLUBS);
  int n = 0;
  for (int k = 0; k < MAX_CLUBS; k++) {
    uint32_t v = h[k];
    if (v == 0xffffffffu || v == 0) break;
    g_list[i][n++] = v >> HANDLE_SHIFT;
  }
  if (!n) return 0;
  g_n[i] = n;
  g_stat[2]++;
  return n;
}

static int kept_out(uint32_t v)
{
  for (int j = 0; j < g_nkeep; j++) if (g_keep[j] == v) return 1;
  return 0;
}

/* The game's stored list of a pool slot with our league's clubs taken out, for 0x141263b40.
   Built at the first count of each slot it asks about and reused for the gets and the
   second count that follow. */
static unsigned pool_build(void* self, unsigned slot, int i)
{
  g_npool = 0; g_pool_slot = slot; g_pool_calls++;
  unsigned n = *(uint16_t*)((unsigned char*)self + COUNT_OFF + slot * 2);
  if (n > STRIDE) n = STRIDE;
  int ours = rebuild(i);
  const uint32_t* stored = (const uint32_t*)((unsigned char*)self + slot * STRIDE * 4);
  for (unsigned k = 0; k < n; k++) {
    uint32_t v = stored[k];
    int mine = kept_out(v);
    for (int j = 0; j < ours && !mine; j++) if (g_list[i][j] == v) mine = 1;
    if (!mine) g_pool[g_npool++] = v;
  }
  return (unsigned)g_npool;
}

/* A pool slot no league of ours sits on, as the game stored it minus the clubs of the game that
   now play in a league of ours. Rebuilt at each count (the stored lists are filled once, at
   boot, and a count before that must not be cached as empty); a get with no count before it
   builds it too. */
static unsigned keep_build(void* self, unsigned slot, int p)
{
  unsigned n = *(uint16_t*)((unsigned char*)self + COUNT_OFF + slot * 2);
  if (n > STRIDE) n = STRIDE;
  const uint32_t* stored = (const uint32_t*)((unsigned char*)self + slot * STRIDE * 4);
  int m = 0;
  for (unsigned k = 0; k < n; k++)
    if (!kept_out(stored[k])) g_kp[p][m++] = stored[k];
  g_kn[p] = m;
  return (unsigned)m;
}

/* ---- the two replacements ---- */

__declspec(dllexport) unsigned count_hook(void* self, unsigned slot)
{
  int i = cfg_index(slot);
  if (i >= 0 && self && is_pool(slot)) {
    uintptr_t ra = (uintptr_t)__builtin_return_address(0) - (uintptr_t)g_base;
    if (ra == SLOTFN_COUNT1_RET) return pool_build(self, slot, i);
    if (ra == SLOTFN_COUNT2_RET && g_pool_slot == slot && g_npool >= 0) return (unsigned)g_npool;
  }
  if (i >= 0) {
    int n = rebuild(i);
    if (n) { g_stat[0]++; return (unsigned)n; }
    g_stat[3]++;
  }
  if (slot >= SLOTS || !self) return 0;
  if (g_nkeep && i < 0) {
    int p = pool_index(slot);
    if (p >= 0) return keep_build(self, slot, p);
  }
  return *(uint16_t*)((unsigned char*)self + COUNT_OFF + slot * 2);
}

__declspec(dllexport) unsigned get_hook(void* self, unsigned slot, unsigned idx)
{
  int i = cfg_index(slot);
  if (i >= 0 && is_pool(slot) && g_pool_slot == slot && g_npool >= 0 &&
      (uintptr_t)__builtin_return_address(0) - (uintptr_t)g_base == SLOTFN_GET_RET)
    return idx < (unsigned)g_npool ? g_pool[idx] : 0xffffffffu;
  if (i >= 0 && g_n[i] > 0) {
    if (idx >= (unsigned)g_n[i]) return 0xffffffffu;
    g_stat[1]++;
    return g_list[i][idx];
  }
  if (slot >= SLOTS || !self) return 0xffffffffu;
  if (g_nkeep && i < 0) {
    int p = pool_index(slot);
    if (p >= 0) {
      if (g_kn[p] < 0) keep_build(self, slot, p);
      return idx < (unsigned)g_kn[p] ? g_kp[p][idx] : 0xffffffffu;
    }
  }
  unsigned n = *(uint16_t*)((unsigned char*)self + COUNT_OFF + slot * 2);
  if (idx >= n) return 0xffffffffu;
  return *(uint32_t*)((unsigned char*)self + (slot * STRIDE + idx) * 4);
}

/* ---- install ---- */

/* The first fourteen bytes of each reader, as this build has them. Both functions are longer
   than fourteen bytes and end in a ret, so the jump fits inside the function. */
static const unsigned char SIG_COUNT[14] = {
  0x33,0xc0, 0x83,0xfa,0x7b, 0x73,0x0a, 0x8b,0xc2, 0x0f,0xb7,0x84,0x41,0x68 };
static const unsigned char SIG_GET[14] = {
  0x83,0xfa,0x7b, 0x73,0x20, 0x8b,0xd2, 0x0f,0xb7,0x84,0x51,0x68,0xa1,0x05 };

/* Replace, do not wrap: jmp [rip+0] ; qword handler. Fourteen bytes, nothing stolen. */
static int replace(unsigned char* target, void* handler)
{
  DWORD old;
  if (!VirtualProtect(target, 14, PAGE_EXECUTE_READWRITE, &old)) return 1;
  target[0] = 0xFF; target[1] = 0x25; *(uint32_t*)(target + 2) = 0;
  *(uint64_t*)(target + 6) = (uint64_t)(uintptr_t)handler;
  VirtualProtect(target, 14, old, &old);
  FlushInstructionCache(GetCurrentProcess(), target, 14);
  return 0;
}

/* The clubs of the game that play in a league of ours (the world file's nopool line), before
   fl26_clubs_install. Returns how many were taken. */
__declspec(dllexport) int fl26_clubs_keep_out(const uint32_t* tids, int n)
{
  g_nkeep = 0;
  for (int k = 0; tids && k < n && g_nkeep < MAX_KEEP; k++)
    if (tids[k] && !kept_out(tids[k])) g_keep[g_nkeep++] = tids[k];
  for (int p = 0; p < 4; p++) g_kn[p] = -1;
  logf("fl26clubs: %d club(s) of the game play in our leagues -- left out of the other-clubs pools", g_nkeep);
  return g_nkeep;
}

/* 0 ok; 2 count signature; 3 get signature; 4/5 protect failed; 9 bad config. ncfg may be 0
   when fl26_clubs_keep_out gave clubs: the pools are then all there is to answer. */
__declspec(dllexport) int fl26_clubs_install(uint64_t exe_base, const fl26_clubs_cfg_t* cfg, int ncfg)
{
  if (ncfg < 0 || ncfg > MAX_CFG || (ncfg && !cfg) || (!ncfg && !g_nkeep)) return 9;
  g_base = exe_base;
  g_ncfg = ncfg;
  for (int i = 0; i < ncfg; i++) {
    if (cfg[i].slot >= SLOTS) return 9;
    g_cfg[i] = cfg[i];
    g_n[i] = -1;
  }
  /* check both before touching either, so a mismatch leaves the game unmodified */
  if (memcmp((void*)(uintptr_t)(exe_base + COUNT_RVA), SIG_COUNT, 14)) return 2;
  if (memcmp((void*)(uintptr_t)(exe_base + GET_RVA),   SIG_GET,   14)) return 3;
  if (replace((unsigned char*)(uintptr_t)(exe_base + COUNT_RVA), (void*)count_hook)) return 4;
  if (replace((unsigned char*)(uintptr_t)(exe_base + GET_RVA),   (void*)get_hook))   return 5;
  logf("fl26clubs: readers replaced (count@%llx get@%llx), %d slot(s) served from our regulations, "
       "%d club(s) kept out of the pools",
       (unsigned long long)(exe_base + COUNT_RVA), (unsigned long long)(exe_base + GET_RVA), ncfg, g_nkeep);
  return 0;
}

__declspec(dllexport) int fl26_clubs_log(char* out, int cap)
{
  int n = (int)g_log_len; if (n > cap - 1) n = cap - 1; if (n < 0) n = 0;
  memcpy(out, g_log, n); out[n] = 0;
  if (n < g_log_len) { memmove(g_log, g_log + n, g_log_len - n); g_log_len -= n; } else g_log_len = 0;
  return n;
}

/* counts served, gets served, rebuilds, times we had no answer and left it to the game */
__declspec(dllexport) void fl26_clubs_stats(uint32_t* out4)
{
  for (int i = 0; i < 4; i++) out4[i] = g_stat[i];
}

/* how many pool lists were handed to the Master League club-slot function */
__declspec(dllexport) uint32_t fl26_clubs_pool_calls(void) { return g_pool_calls; }

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID r) { (void)h;(void)reason;(void)r; return TRUE; }
