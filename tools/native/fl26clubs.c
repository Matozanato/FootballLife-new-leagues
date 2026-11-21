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
 * 2026-11-02: a pool slot by choice (Mod Studio's Select Team list, recipe select_team; vmican:
 * "with a South American world the Other Latin American Teams are of no use"). A league put on
 * 69, 73 or 75 on purpose takes that group's place in the Master League too: for the slot
 * function its clubs are answered from the regulation like any served slot, so they get the
 * slot and Team Info lists them under the league (before, the game's pool clubs were listed
 * there and ours had 123). Those clubs are then the pool the Libertadores and the Club World
 * Cup take fill-ins from, and the group's own clubs, no longer on any list, get 123 -- what the
 * choice says. The world file marks such a league (pick=1); fl26_clubs_own_pools() takes the
 * slots. A league on a pool slot only because no other was free is left as above.
 *
 * Built with `zig cc` (tools/native/build-clubs.sh). Our own code, no third-party binaries.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <string.h>
#include <stdio.h>
#include <stdarg.h>
#include <stdlib.h>

#define COUNT_RVA  0x14d62c0   /* u16 count(void* this, unsigned slot)            */
#define GET_RVA    0x14d6290   /* u32 get(void* this, unsigned slot, unsigned i)  */
#define SET_RVA    0x14d6330   /* set(void* this, unsigned slot, unsigned i, u32) */
#define REG_RVA    0x14bb000   /* void* regulation(void* block, unsigned id)      */
#define OWNER_RVA  0x3705e10   /* global: owner; block = [owner+0x48]             */

#define SLOTS       123        /* the engine's slot count; 123 also means "none"  */
#define STRIDE      750        /* dwords per slot in the list array               */
#define COUNT_OFF   0x5a168    /* SLOTS * STRIDE * 4: where the u16 counts begin  */

/* fl26slots (limits branch, 2026-10-11) raises the slot count past 123 and gives every slot a
   capacity of its own, listed in tables on its page; the readers it leaves behind are a jmp to
   that page. When it is there, this layout is read off its code instead of the constants above:
   g_slots slots (123 stays "none"), slot s at dword g_off[s] of the region with room for
   g_cap[s] clubs, the counts at g_cntoff. Without it these hold the shipped layout. */
static unsigned        g_slots  = SLOTS;
static unsigned        g_cntoff = COUNT_OFF;
static const uint32_t* g_off    = 0;
static const uint32_t* g_cap    = 0;
static int      slot_ok(unsigned s) { return s < g_slots && (!g_off || s != 123); }
static unsigned slot_cap(unsigned s) { return g_cap ? g_cap[s] : STRIDE; }
static uint32_t* slot_list(void* self, unsigned s)
{ return (uint32_t*)self + (g_off ? g_off[s] : s * STRIDE); }
static uint16_t* slot_count(void* self, unsigned s)
{ return (uint16_t*)((unsigned char*)self + g_cntoff + s * 2); }
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
static unsigned g_own[4];                 /* pool slots a league of ours took by choice      */
static int      g_nown;
static int owned(unsigned slot)
{
  for (int k = 0; k < g_nown; k++) if (g_own[k] == slot) return 1;
  return 0;
}
static int pool_index(unsigned slot)
{
  return slot == 69 ? 0 : slot == 70 ? 1 : slot == 73 ? 2 : slot == 75 ? 3 : -1;
}

#define MAX_KEEP 512

typedef struct { uint16_t slot; uint16_t reg; } fl26_clubs_cfg_t;

typedef void* (*reg_fn)(void*, unsigned);

static uint64_t g_base;
#include "fl26layout.h"   /* block offsets read from the code fl26caps patched */
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
  unsigned n = *slot_count(self, slot);
  if (n > slot_cap(slot)) n = slot_cap(slot);
  int ours = rebuild(i);
  const uint32_t* stored = slot_list(self, slot);
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
static int is_pad(uint32_t v) { return v == 0 || v == 0x3ffffu || v == 0xffffffffu; }

/* The stored count is not always the length of the list. Entering a mode, 0x141f14960 loads
   the Edit save's own lists (category 27 -> slot 69, Other European) with the setter alone: the
   entries are written, the count is left as the boot fill set it. An Edit list longer than the
   boot one then loses its last clubs to the old count. So the setter is ours too, and records
   how far each pool slot of that list object was really written; the list is served that far.
   Never further on a guess: past the count of another list object (a Master League season being
   built) the words are not a list, and serving them crashed creation at 0x140aeed0b (8 October). */
static void*    g_hi_self[4];
static unsigned g_hi[4];

/* Only the Edit refill's own call (0x141f14af6) counts. The setter's other caller, 0x1414f6e20,
   sets the count first and then writes the list, and does it again with fewer clubs while a
   Master League season is built: a mark kept from its longer fill served stale words past the
   new count and creation crashed at 0x140aeee1e (8 October, second time). A list that caller
   rewrites is served by its count again; the refill starts its mark over at each fill. */
#define EDIT_REFILL_SET_RET 0x1f14afb

__declspec(dllexport) void set_hook(void* self, unsigned slot, unsigned idx, uint32_t v)
{
  if (!slot_ok(slot) || idx >= slot_cap(slot)) return;
  slot_list(self, slot)[idx] = v;
  int p = pool_index(slot);
  if (p < 0) return;
  uintptr_t ra = (uintptr_t)__builtin_return_address(0) - (uintptr_t)g_base;
  if (ra != EDIT_REFILL_SET_RET) {
    if (g_hi_self[p] == self) { g_hi_self[p] = 0; g_hi[p] = 0; }
    return;
  }
  if (g_hi_self[p] != self || idx == 0) { g_hi_self[p] = self; g_hi[p] = 0; }
  if (idx + 1 > g_hi[p]) g_hi[p] = idx + 1;
}

static int g_kp_said[4];

static unsigned keep_build(void* self, unsigned slot, int p)
{
  unsigned n = *slot_count(self, slot);
  if (n > slot_cap(slot)) n = slot_cap(slot);
  const uint32_t* stored = slot_list(self, slot);
  unsigned len = n;
  if (g_hi_self[p] == self && g_hi[p] > n) {
    len = g_hi[p];
    if (!g_kp_said[p]) {
      g_kp_said[p] = 1;
      logf("fl26clubs: slot %u was written %u past its count of %u (an Edit list) -- served to its end",
           slot, len - n, n);
    }
  }
  int m = 0;
  for (unsigned k = 0; k < len; k++) {
    uint32_t v = stored[k];
    if (k >= n && is_pad(v)) continue;
    if (kept_out(v)) continue;
    int dup = 0;
    if (k >= n) for (int j = 0; j < m && !dup; j++) if (g_kp[p][j] == v) dup = 1;
    if (!dup) g_kp[p][m++] = v;
  }
  g_kn[p] = m;
  return (unsigned)m;
}

/* ---- the two replacements ---- */

__declspec(dllexport) unsigned count_hook(void* self, unsigned slot)
{
  int i = cfg_index(slot);
  if (i >= 0 && self && is_pool(slot) && !owned(slot)) {
    uintptr_t ra = (uintptr_t)__builtin_return_address(0) - (uintptr_t)g_base;
    if (ra == SLOTFN_COUNT1_RET) return pool_build(self, slot, i);
    if (ra == SLOTFN_COUNT2_RET && g_pool_slot == slot && g_npool >= 0) return (unsigned)g_npool;
  }
  if (i >= 0) {
    int n = rebuild(i);
    if (n) { g_stat[0]++; return (unsigned)n; }
    g_stat[3]++;
  }
  if (!slot_ok(slot) || !self) return 0;
  if (i < 0) {
    int p = pool_index(slot);
    if (p >= 0) return keep_build(self, slot, p);
  }
  unsigned n = *slot_count(self, slot);
  return n > slot_cap(slot) ? slot_cap(slot) : n;
}

__declspec(dllexport) unsigned get_hook(void* self, unsigned slot, unsigned idx)
{
  int i = cfg_index(slot);
  if (i >= 0 && is_pool(slot) && !owned(slot) && g_pool_slot == slot && g_npool >= 0 &&
      (uintptr_t)__builtin_return_address(0) - (uintptr_t)g_base == SLOTFN_GET_RET)
    return idx < (unsigned)g_npool ? g_pool[idx] : 0xffffffffu;
  if (i >= 0 && g_n[i] > 0) {
    if (idx >= (unsigned)g_n[i]) return 0xffffffffu;
    g_stat[1]++;
    return g_list[i][idx];
  }
  if (!slot_ok(slot) || !self) return 0xffffffffu;
  if (i < 0) {
    int p = pool_index(slot);
    if (p >= 0) {
      if (g_kn[p] < 0) keep_build(self, slot, p);
      return idx < (unsigned)g_kn[p] ? g_kp[p][idx] : 0xffffffffu;
    }
  }
  unsigned n = *slot_count(self, slot);
  if (idx >= n || idx >= slot_cap(slot)) return 0xffffffffu;
  return slot_list(self, slot)[idx];
}

/* ---- followers and the club ranking (2026-10-08) ----
 *
 * A Master League club's followers are set when the career starts (0x140ef9614) and again
 * each season (0x141300d6d) by 0x14150e950(team handle):
 *
 *   base = {10000,15000,20000,25000,35000,50000,65000,80000,110000,140000}[class]
 *          + 32 * mean popularity of the club's best eleven
 *   followers = round(base * {1,1.25,1.5,2,3,4.5,6,7.5,10,40}[class]) + star players
 *     (0x141589f49; block+0x1798b80 holds base, block+0x1798b8c the followers)
 *
 * `class` is byte +0x0e of the club's entry in the club ranking (block+0x16705a8: 750 entries
 * of 16 bytes, the count at +0x2ee0), 9 for ranks 1-10 down to 0 past 400 (0x141323b84). The
 * ranking is filled when a career starts (0x141324d00) with the first 750 clubs that qualify,
 * in team-array order -- so in a world with more clubs than that, the newest clubs are not in
 * it. The lookup 0x140de2310 answers a club it cannot find with entry 0: the top-ranked club.
 * Every club past the 750 therefore had class 9 and x40 followers (NK Inker Zaprešić, a
 * third-division side: 7,157,582), and class 9 everywhere else the 51 callers use it
 * (sponsor money, a player's popularity, the transfer screens).
 *
 * The lookup is replaced with the same search. On a miss, for a club the world file lists
 * (a "fans" line, written by Mod Studio's League Builder from the club's division and
 * squad), it answers with an entry of that club's own: its handle, a rank inside the class,
 * no points, and the class the line gives. A club the file does not list still gets entry
 * 0, as the game does. All 51 callers only read the entry (+0x04, +0x0a, +0x0e), so the entry
 * lives in a small ring of our own.
 *
 * The same line gives a percentage for the followers' base: 0x14150e950 is wrapped and its
 * result scaled for a listed club, so a lower division has fewer followers than a top flight
 * with the same class (the game's lowest class still gives a third-division club ~35,000).
 *
 * The followers themselves (0x141589e90) add 20,000 / 100,000 / 500,000 for each player of
 * star level 6 / 7 / 7 with a rating of 90+ (200k/500k/5M from class 8). That function is
 * wrapped too: for a listed club below the top flight the star part is cut to the same
 * percentage, and to no more than that percentage of the rest (NK Dugo Selo, a third-tier
 * club: ~80,000 before).
 *
 * A second ranking lookup, 0x140b8abd0, answers a club's rank (+0x04) or -1 for a miss.
 * The Master League broadcasting fee (0x141567ca0: 23,000,000 / (rank + 10) - 40,000) took
 * -1 as better than first place: EUR 250M a season for a club past the 750. It is replaced
 * the same way: a listed club out of the ranking answers the rank its own entry has.
 *
 * A finer share and the season's income (2026-11-11, FL 2027 worlds: "fansx" lines). A whole
 * percent with a floor of 1,000 left half of a big world's clubs on one figure (2,404 of
 * 4,689 at 5 percent). A "fansx <share of 10,000> <ids>" line gives a listed club a finer share,
 * and its base may go down to 100.
 *
 * The same clubs were paid like the game's 450th club every season, whatever their size: the
 * broadcasting fee above (EUR 1.0M for rank 450; the unit is EUR 100) and the sponsors,
 * 0x141567d00: 25 * max(followers base, 150,000) - 670 * min(rank, 400) - 3,451,330 -- the
 * floor of 150,000 is above every base below class 9, so every club of rank 400 or worse gets
 * 30,670 (EUR 3.07M). An Armenian second-division side with wages of EUR 1.39M and a transfer
 * budget of EUR 0.3M was EUR 2.8M up after one season. Both are paid when a career starts and
 * each season (0x14133d6fb..0x14133d7ad, each with a random tenth off or on) into the career's
 * money, block+0x41b9374: +0x00 the transfer budget, +0x14 the salary budget, +0x2c the fee,
 * +0x30 the sponsors, +0x34 the fan club income (= the followers base).
 *
 * Both functions are replaced with the same sums. For a club with a fansx share the two
 * payments are scaled together: what the wages need (the salary budget and the tenth the
 * caller may take off) stays whole, and of the rest the club gets its share. A club is never
 * paid less than its wages; with no salary budget to read the payments stay the game's.
 *
 * When a career starts the two are set by the money's init, 0x1415698f0(handle*, flag*): the
 * sponsors through the function above, the fee by the same sum written out in place, and only
 * after both the budgets, from the squad's wages (0x141566150) -- so the replaced functions meet
 * a salary budget of 0 there. The init is wrapped: once it is through, the fee (+0x2c) and the
 * sponsors (+0x30) it stored are scaled where they lie, by the salary budget it has just set.
 * It leaves early for a club it cannot find; a mark put into both fields before it runs tells
 * whether it wrote them.
 */
#define RANKFIND_RVA 0x0de2310  /* entry* find(ranking*, const u32* handle)          */
static int replace(unsigned char* target, void* handler);
#define FANS_RVA     0x150e950  /* int followers_base(u32 handle)                    */
#define FTOTAL_RVA   0x1589e90  /* void followers_set(u32 handle): block+0x1798b8c   */
#define RANKPOS_RVA  0x0b8abd0  /* int rank_of(ranking*, const u32* handle), -1 miss */
#define BLK_RANKING  lay_ranking()   /* 0x16705a8 unless the set moves the lower tail */
#define BLK_FBASE    lay_fbase()     /* 0x1798b80 */
#define BLK_FANS     lay_fans()      /* 0x1798b8c */
#define RANK_COUNT   0x2ee0
#define MAX_FANS     16384   /* 4096 until 07.11.2026: a world of 4277 new clubs lost the last 181 */

typedef struct { uint32_t tid; uint16_t share; uint8_t cls, fine; } fan_t;   /* share of 10,000 */
#define FANS_FLOOR      1000    /* the lowest scaled base of a "fans" club          */
#define FANS_FLOOR_FINE 100     /* ... and of a club with a "fansx" share           */
static fan_t    g_fans[MAX_FANS];
static int      g_nfans;
static unsigned char g_virt[8][16];
static volatile long g_virt_i;
static uint32_t g_fstat[2];                /* own ranking entries handed out, bases scaled */
unsigned char* g_tramp_fans = 0;
unsigned char* g_tramp_ftotal = 0;
static uint32_t g_fstat2[2];               /* broadcasting ranks answered, star parts cut */
static int      g_nfine;                   /* clubs with a fansx share                    */
static uint32_t g_fin;                     /* block offset of the career's money, 0 = the income is the game's */
static uint32_t g_istat[3];                /* payments scaled, left whole (the wages need them), no salary budget */
static int      g_ilog;
static const float CLASS_MULT[10] = { 1.0f, 1.25f, 1.5f, 2.0f, 3.0f, 4.5f, 6.0f, 7.5f, 10.0f, 40.0f };
static const uint32_t CLASS_RANK[10] = { 450, 370, 310, 250, 190, 130, 80, 45, 20, 5 };

static const fan_t* fan_of(uint32_t tid)
{
  int lo = 0, hi = g_nfans - 1;
  while (lo <= hi) {
    int m = (lo + hi) / 2;
    if (g_fans[m].tid == tid) return &g_fans[m];
    if (g_fans[m].tid < tid) lo = m + 1; else hi = m - 1;
  }
  return 0;
}

__declspec(dllexport) void* rank_find_hook(unsigned char* table, const uint32_t* key)
{
  uint32_t n = *(uint32_t*)(table + RANK_COUNT), h = *key;
  for (uint32_t i = 0; i < n; i++)
    if (*(uint32_t*)(table + 16 * i) == h) return table + 16 * i;
  const fan_t* f = g_nfans ? fan_of(h >> HANDLE_SHIFT) : 0;
  if (!f) return table;
  unsigned char* e = g_virt[(unsigned long)InterlockedIncrement(&g_virt_i) & 7];
  memset(e, 0, 16);
  *(uint32_t*)e = h;
  *(uint32_t*)(e + 4) = CLASS_RANK[f->cls];
  e[0x0e] = f->cls;
  g_fstat[0]++;
  return e;
}

__declspec(dllexport) int fans_post(uint32_t h, int base)
{
  const fan_t* f = g_nfans ? fan_of(h >> HANDLE_SHIFT) : 0;
  if (!f || f->share >= 10000 || base <= 0) return base;
  int v = (int)((int64_t)base * f->share / 10000), lo = f->fine ? FANS_FLOOR_FINE : FANS_FLOOR;
  g_fstat[1]++;
  return v < lo ? lo : v;
}

/* the rank of a club in the ranking, -1 for none -- 0x140b8abd0, with a listed club's own */
__declspec(dllexport) int rank_pos_hook(unsigned char* table, const uint32_t* key)
{
  uint32_t n = *(uint32_t*)(table + RANK_COUNT), h = *key;
  for (uint32_t i = 0; i < n; i++)
    if (*(uint32_t*)(table + 16 * i) == h) return *(int*)(table + 16 * i + 4);
  const fan_t* f = g_nfans ? fan_of(h >> HANDLE_SHIFT) : 0;
  if (!f) return -1;
  g_fstat2[0]++;
  return (int)CLASS_RANK[f->cls];
}

/* after 0x141589e90 set the followers of club h: cut the star players' part of a listed
   club below the top flight. blk is the Master League block, or 0 for none. */
__declspec(dllexport) void fans_total_post(uint32_t h, unsigned char* blk)
{
  const fan_t* f = g_nfans ? fan_of(h >> HANDLE_SHIFT) : 0;
  if (!f || f->share >= 10000 || !blk) return;
  uint32_t key = h;
  unsigned char* e = (unsigned char*)rank_find_hook(blk + BLK_RANKING, &key);
  unsigned cls = e[0x0e] > 9 ? 9 : e[0x0e];
  int fb = *(int*)(blk + BLK_FBASE), v = *(int*)(blk + BLK_FANS);
  float x = (float)fb * CLASS_MULT[cls];
  int base = (int)(x < 0 ? x - 0.5f : x + 0.5f);
  int star = v - base;
  if (star <= 0) return;
  int64_t cut = (int64_t)star * f->share / 10000, room = (int64_t)base * f->share / 10000;
  if (cut > room) cut = room;
  *(int*)(blk + BLK_FANS) = base + (int)cut;
  g_fstat2[1]++;
}

static unsigned char* ml_block(void)
{
  unsigned char* owner = *(unsigned char**)(uintptr_t)(g_base + OWNER_RVA);
  return owner ? *(unsigned char**)(owner + 0x48) : 0;
}

__declspec(dllexport) void fans_total_after(uint32_t h) { fans_total_post(h, ml_block()); }

/* CALL-style wrap of 0x141589e90, as fans_handler below */
__attribute__((naked)) void ftotal_handler(void)
{
  __asm__ volatile(
    "push %rbx\n"
    "sub  $0x20, %rsp\n"
    "mov  %ecx, %ebx\n"
    "call *g_tramp_ftotal(%rip)\n"
    "mov  %ebx, %ecx\n"
    "call fans_total_after\n"
    "add  $0x20, %rsp\n"
    "pop  %rbx\n"
    "ret\n");
}

/* CALL-style wrap of 0x14150e950: the original through its trampoline, then fans_post.
   entry rsp = 8 mod 16; push -> 0; sub 0x20 -> 0, the callees' home space inside it. */
__attribute__((naked)) void fans_handler(void)
{
  __asm__ volatile(
    "push %rbx\n"
    "sub  $0x20, %rsp\n"
    "mov  %ecx, %ebx\n"
    "call *g_tramp_fans(%rip)\n"
    "mov  %ebx, %ecx\n"
    "mov  %eax, %edx\n"
    "call fans_post\n"
    "add  $0x20, %rsp\n"
    "pop  %rbx\n"
    "ret\n");
}

static const unsigned char SIG_RANKFIND[14] = {
  0x48,0x89,0x5c,0x24,0x10, 0x48,0x89,0x6c,0x24,0x18, 0x48,0x89,0x74,0x24 };
/* mov [rsp+8],ecx; push rbp/rbx/rsi/rdi/r13/r14/r15 -- fourteen bytes, nothing rip-relative */
static const unsigned char SIG_FANS[14] = {
  0x89,0x4c,0x24,0x08, 0x55,0x53,0x56,0x57, 0x41,0x55,0x41,0x56,0x41,0x57 };

/* mov [rsp+8],ecx; push rbx/rsi/rdi/r12/r13/r14/r15 -- fifteen bytes, nothing rip-relative */
static const unsigned char SIG_FTOTAL[15] = {
  0x89,0x4c,0x24,0x08, 0x53,0x56,0x57, 0x41,0x54,0x41,0x55,0x41,0x56,0x41,0x57 };
static const unsigned char SIG_RANKPOS[14] = {
  0x48,0x89,0x5c,0x24,0x10, 0x48,0x89,0x6c,0x24,0x18, 0x56,0x57,0x41,0x56 };

static int cmp_fan(const void* a, const void* b)
{
  uint32_t x = ((const fan_t*)a)->tid, y = ((const fan_t*)b)->tid;
  return x < y ? -1 : x > y;
}

/* The world file's fans lines, before fl26_clubs_install: rows of {team id, class << 8 | pct}.
   Returns how many were taken. */
__declspec(dllexport) int fl26_clubs_fans(const uint32_t* rows, int n)
{
  g_nfans = 0;
  for (int k = 0; rows && k < n && g_nfans < MAX_FANS; k++) {
    uint32_t cls = (rows[2 * k + 1] >> 8) & 0xff, pct = rows[2 * k + 1] & 0xff;
    if (!rows[2 * k] || cls > 9 || !pct) continue;
    g_fans[g_nfans].tid = rows[2 * k]; g_fans[g_nfans].cls = (uint8_t)cls;
    g_fans[g_nfans].share = (uint16_t)((pct > 100 ? 100 : pct) * 100); g_fans[g_nfans].fine = 0;
    g_nfans++;
  }
  qsort(g_fans, g_nfans, sizeof g_fans[0], cmp_fan);
  g_nfine = 0;
  return g_nfans;
}

/* The world file's fansx lines, after fl26_clubs_fans and before fl26_clubs_install: rows of
   {team id, share of 10,000}. Only a club with a fans line takes one (the class comes from
   there). Returns how many were taken. */
__declspec(dllexport) int fl26_clubs_fans2(const uint32_t* rows, int n)
{
  g_nfine = 0;
  for (int k = 0; rows && k < n; k++) {
    fan_t* f = (fan_t*)fan_of(rows[2 * k]);
    uint32_t sh = rows[2 * k + 1];
    if (!f || !sh || sh > 10000) continue;
    f->share = (uint16_t)sh; f->fine = 1;
    g_nfine++;
  }
  return g_nfine;
}

/* ---- the season's broadcasting fee and sponsors (see the note above) ---- */
#define TV_RVA          0x1567ca0  /* int broadcasting_fee(u32 handle)                 */
#define SPONSOR_RVA     0x1567d00  /* int sponsors(u32 handle)                         */
#define SPONSOR_PRE_RVA 0x1568770  /* what sponsors() calls first: (handle, 0, 0)      */
#define FIN_WAGES       0x14       /* the salary budget, in the career's money         */
static const unsigned char SIG_TV[9]       = { 0x89,0x4c,0x24,0x08, 0x48,0x83,0xec,0x28, 0xe8 };
static const unsigned char SIG_SPONSOR[10] = { 0x89,0x4c,0x24,0x08, 0x57, 0x48,0x83,0xec,0x20, 0xe8 };
typedef int   (*fbase_fn)(uint32_t);
typedef void* (*spre_fn)(uint32_t, uint32_t, void*);
static unsigned char* ml_block(void);

static int tv_plain(unsigned char* blk, uint32_t h)
{
  uint32_t key = h;
  int rank = rank_pos_hook(blk + BLK_RANKING, &key);
  int v = (int)(23000000u / (uint32_t)(rank + 10)) - 40000;
  return v <= 0 ? 1000 : v;
}

static int sponsor_plain(unsigned char* blk, uint32_t h, int pre)
{
  if (pre) ((spre_fn)(uintptr_t)(g_base + SPONSOR_PRE_RVA))(h, 0, 0);
  int base = ((fbase_fn)(uintptr_t)(g_base + FANS_RVA))(h);
  uint32_t key = h;
  unsigned char* e = (unsigned char*)rank_find_hook(blk + BLK_RANKING, &key);
  uint32_t rank = *(uint32_t*)(e + 4);
  if (rank > 400) rank = 400;
  if (base < 150000) base = 150000;
  int v = base * 25 - (int)rank * 670 - 3451330;
  return v <= 0 ? 1000 : v;
}

/* `mine` of a club's two payments (the other one is `other`) for a club with this salary budget and
   share of 10,000: what the wages need (and the tenth a caller may take off) whole, of the rest
   the share. As it was with no salary budget, a payment of nothing, or less than the wages need.
   Exported for the test: no game memory in it. */
__declspec(dllexport) int fl26_clubs_pay(int mine, int other, int wages, uint32_t share)
{
  int64_t orig = (int64_t)mine + other, need = (int64_t)wages * 112 / 100;
  if (wages <= 0 || mine <= 0 || other < 0 || share >= 10000 || orig <= need) return mine;
  int v = (int)((int64_t)mine * (need + (orig - need) * share / 10000) / orig);
  return v < 1 ? 1 : v;
}

/* `mine` of a club's two payments, scaled for a club with a fansx share */
static int income_scaled(unsigned char* blk, uint32_t h, int mine, int other, const char* what)
{
  const fan_t* f = g_nfans ? fan_of(h >> HANDLE_SHIFT) : 0;
  if (!f || !f->fine || f->share >= 10000 || !g_fin) return mine;
  int64_t orig = (int64_t)mine + other;
  int wages = *(int*)(blk + g_fin + FIN_WAGES), v = fl26_clubs_pay(mine, other, wages, f->share);
  g_istat[wages <= 0 ? 2 : v == mine ? 1 : 0]++;
  if (g_ilog < 12 && wages > 0) {
    g_ilog++;
    logf("fl26clubs: season income of club %u, %s: %d -> %d (with the other payment %d, salary budget %d, "
         "share %u of 10000)", h >> HANDLE_SHIFT, what, mine, v, (int)orig, wages, f->share);
  }
  return v;
}

/* ---- the same when a career starts: the money's init, wrapped ---- */
#define INIT_RVA    0x15698f0  /* void money_init(const u32* handle, const u8* flag)   */
#define FIN_TV      0x2c
#define FIN_SPONSOR 0x30
#define FIN_MARK    0x7ffffffe /* the init clamps what it stores to +-99,999,999        */
/* mov rax,rsp; push rdi/r12/r13/r14/r15; sub rsp,0x70 -- sixteen bytes, nothing rip-relative */
static const unsigned char SIG_INIT[16] = {
  0x48,0x8b,0xc4, 0x57, 0x41,0x54, 0x41,0x55, 0x41,0x56, 0x41,0x57, 0x48,0x83,0xec,0x70 };
unsigned char* g_tramp_init = 0;
static int g_was_tv, g_was_sp;

__declspec(dllexport) void init_before(const uint32_t* ph)
{
  unsigned char* blk = ml_block();
  (void)ph;
  if (!blk || !g_fin) return;
  int* m = (int*)(blk + g_fin);
  g_was_tv = m[FIN_TV / 4]; g_was_sp = m[FIN_SPONSOR / 4];
  m[FIN_TV / 4] = FIN_MARK; m[FIN_SPONSOR / 4] = FIN_MARK;
}

__declspec(dllexport) void init_after(const uint32_t* ph)
{
  unsigned char* blk = ml_block();
  if (!blk || !g_fin) return;
  int* m = (int*)(blk + g_fin);
  int tv = m[FIN_TV / 4], sp = m[FIN_SPONSOR / 4];
  if (tv == FIN_MARK || sp == FIN_MARK) {            /* it left early: as it was */
    if (tv == FIN_MARK) m[FIN_TV / 4] = g_was_tv;
    if (sp == FIN_MARK) m[FIN_SPONSOR / 4] = g_was_sp;
    return;
  }
  uint32_t h = ph ? *ph : 0;
  const fan_t* f = g_nfans ? fan_of(h >> HANDLE_SHIFT) : 0;
  if (!f || !f->fine || f->share >= 10000) return;
  int wages = m[FIN_WAGES / 4];
  int tv2 = tv, sp2 = sp;
  if (wages <= 0 || tv <= 0 || sp <= 0) g_istat[2]++;
  else {
    tv2 = fl26_clubs_pay(tv, sp, wages, f->share); sp2 = fl26_clubs_pay(sp, tv, wages, f->share);
    m[FIN_TV / 4] = tv2; m[FIN_SPONSOR / 4] = sp2;
    g_istat[tv2 == tv && sp2 == sp ? 1 : 0]++;
  }
  logf("fl26clubs: a career's first income of club %u: broadcasting %d -> %d, sponsors %d -> %d "
       "(salary budget %d, share %u of 10000)", h >> HANDLE_SHIFT, tv, tv2, sp, sp2, wages, f->share);
}

/* CALL-style wrap of 0x1415698f0. entry rsp = 8 mod 16; push -> 0; sub 0x20 -> 0. rdx waits in
   our own home space (entry rsp + 0x10 = rsp + 0x38 here), which no callee of ours touches. */
__attribute__((naked)) void init_handler(void)
{
  __asm__ volatile(
    "push %rbx\n"
    "sub  $0x20, %rsp\n"
    "mov  %rcx, %rbx\n"
    "mov  %rdx, 0x38(%rsp)\n"
    "call init_before\n"
    "mov  %rbx, %rcx\n"
    "mov  0x38(%rsp), %rdx\n"
    "call *g_tramp_init(%rip)\n"
    "mov  %rbx, %rcx\n"
    "call init_after\n"
    "add  $0x20, %rsp\n"
    "pop  %rbx\n"
    "ret\n");
}

__declspec(dllexport) int tv_hook(uint32_t h)
{
  unsigned char* blk = ml_block();
  if (!blk) return 1000;
  int tv = tv_plain(blk, h);
  const fan_t* f = g_nfans ? fan_of(h >> HANDLE_SHIFT) : 0;
  if (!f || !f->fine) return tv;
  return income_scaled(blk, h, tv, sponsor_plain(blk, h, 0), "broadcasting");
}

__declspec(dllexport) int sponsor_hook(uint32_t h)
{
  unsigned char* blk = ml_block();
  if (!blk) return 1000;
  int sp = sponsor_plain(blk, h, 1);
  const fan_t* f = g_nfans ? fan_of(h >> HANDLE_SHIFT) : 0;
  if (!f || !f->fine) return sp;
  return income_scaled(blk, h, sp, tv_plain(blk, h), "sponsors");
}

/* payments scaled, left whole, met with no salary budget */
__declspec(dllexport) void fl26_clubs_income_stats(uint32_t* out3)
{
  out3[0] = g_istat[0]; out3[1] = g_istat[1]; out3[2] = g_istat[2];
}

static int rel_to(const unsigned char* at, uint32_t rva)      /* at: an e8 call to g_base + rva? */
{
  return at[0] == 0xe8 && (uintptr_t)(at + 5 + *(const int32_t*)(at + 1)) == (uintptr_t)(g_base + rva);
}

static unsigned char* tramp(unsigned char* fn, int n);

/* 0 all in, 1 not this build's functions (nothing touched), 2 alloc or protect failed */
static int install_income(uint64_t exe_base)
{
  unsigned char* in = (unsigned char*)(uintptr_t)(exe_base + INIT_RVA);
  unsigned char* tv = (unsigned char*)(uintptr_t)(exe_base + TV_RVA);
  unsigned char* sp = (unsigned char*)(uintptr_t)(exe_base + SPONSOR_RVA);
  if (memcmp(tv, SIG_TV, 9) || memcmp(sp, SIG_SPONSOR, 10)) return 1;
  if (tv[0x11] != 0x48 || tv[0x12] != 0x8d || tv[0x13] != 0x81) return 1;      /* lea rax, [rcx + money] */
  if (memcmp(in, SIG_INIT, 16)) return 1;
  if (!rel_to(tv + 0x2e, RANKPOS_RVA) || !rel_to(sp + 0x32, SPONSOR_PRE_RVA) || !rel_to(sp + 0x3b, FANS_RVA)
      || !rel_to(sp + 0x4e, RANKFIND_RVA)) return 1;
  uint32_t fin = *(uint32_t*)(tv + 0x14);
  if (!(g_tramp_init = tramp(in, 16))) return 2;
  if (replace(tv, (void*)tv_hook) || replace(sp, (void*)sponsor_hook)) return 2;
  g_fin = fin;
  if (replace(in, (void*)init_handler)) return 2;
  return 0;
}

/* a trampoline: the first n bytes of fn, then a jump back past them */
static unsigned char* tramp(unsigned char* fn, int n)
{
  unsigned char* t = (unsigned char*)VirtualAlloc(0, 0x40, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
  if (!t) return 0;
  memcpy(t, fn, n);
  t[n] = 0xFF; t[n + 1] = 0x25; *(uint32_t*)(t + n + 2) = 0; *(uint64_t*)(t + n + 6) = (uint64_t)(uintptr_t)(fn + n);
  FlushInstructionCache(GetCurrentProcess(), t, 0x40);
  return t;
}

/* 0 all in; 1 the lookup's signature differs; 2 the followers functions'; 3 alloc/protect;
   4 the rank lookup's. All are checked before any is touched. */
static int install_fans(uint64_t exe_base)
{
  unsigned char* rf = (unsigned char*)(uintptr_t)(exe_base + RANKFIND_RVA);
  unsigned char* fb = (unsigned char*)(uintptr_t)(exe_base + FANS_RVA);
  unsigned char* ft = (unsigned char*)(uintptr_t)(exe_base + FTOTAL_RVA);
  unsigned char* rp = (unsigned char*)(uintptr_t)(exe_base + RANKPOS_RVA);
  if (memcmp(rf, SIG_RANKFIND, 14)) return 1;
  if (memcmp(fb, SIG_FANS, 14) || memcmp(ft, SIG_FTOTAL, 15)) return 2;
  if (memcmp(rp, SIG_RANKPOS, 14)) return 4;
  if (!(g_tramp_fans = tramp(fb, 14)) || !(g_tramp_ftotal = tramp(ft, 15))) return 3;
  if (replace(rf, (void*)rank_find_hook)) return 3;
  if (replace(rp, (void*)rank_pos_hook)) return 3;
  if (replace(fb, (void*)fans_handler)) return 3;
  if (replace(ft, (void*)ftotal_handler)) return 3;
  return 0;
}

/* own ranking entries handed out, followers bases scaled */
__declspec(dllexport) void fl26_clubs_fan_stats(uint32_t* out2)
{
  out2[0] = g_fstat[0]; out2[1] = g_fstat[1];
}

/* broadcasting ranks answered for listed clubs, star parts cut */
__declspec(dllexport) void fl26_clubs_fan_stats2(uint32_t* out2)
{
  out2[0] = g_fstat2[0]; out2[1] = g_fstat2[1];
}

/* ---- install ---- */

/* The first fourteen bytes of each reader, as this build has them. Both functions are longer
   than fourteen bytes and end in a ret, so the jump fits inside the function. */
static const unsigned char SIG_COUNT[14] = {
  0x33,0xc0, 0x83,0xfa,0x7b, 0x73,0x0a, 0x8b,0xc2, 0x0f,0xb7,0x84,0x41,0x68 };
static const unsigned char SIG_GET[14] = {
  0x83,0xfa,0x7b, 0x73,0x20, 0x8b,0xd2, 0x0f,0xb7,0x84,0x51,0x68,0xa1,0x05 };

/* Replace, do not wrap: jmp [rip+0] ; qword handler. Fourteen bytes, nothing stolen. */
static const unsigned char SIG_SET[14] = {
  0x83,0xfa,0x7b,0x73,0x1c,0x41,0x81,0xf8,0xee,0x02,0x00,0x00,0x73,0x13 };

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

/* The pool slots (69, 73, 75) a league of ours took by choice (the world file's pick=1), before
   fl26_clubs_install. Returns how many were taken. */
__declspec(dllexport) int fl26_clubs_own_pools(const uint16_t* slots, int n)
{
  g_nown = 0;
  for (int k = 0; slots && k < n && g_nown < 4; k++)
    if (is_pool(slots[k]) && slots[k] != 70 && !owned(slots[k])) g_own[g_nown++] = slots[k];
  if (g_nown)
    logf("fl26clubs: %d pool slot(s) taken by choice -- their league's clubs get the slot in the Master League",
         g_nown);
  return g_nown;
}

/* fl26slots' readers, when it is loaded: 1 and the layout taken, 0 not there (shipped readers),
   -1 there but not as expected. Each of the three entries is a jmp rel32 into its page; the
   count body starts `xor eax,eax; cmp edx, N`, reads the count `movzx eax, word [rcx+rax*2+D]`
   and the capacity table through the first `lea rdx,[rip+x]`; the get body's second lea is the
   table of first entries. */
static uint64_t jmp_target(uint64_t at)
{
  const unsigned char* b = (const unsigned char*)(uintptr_t)at;
  return b[0] == 0xE9 ? at + 5 + (int64_t)*(const int32_t*)(b + 1) : 0;
}
static uint64_t nth_lea_rdx(uint64_t body, int nth)
{
  const unsigned char* b = (const unsigned char*)(uintptr_t)body;
  for (int k = 0; k < 0x40; k++)
    if (b[k] == 0x48 && b[k + 1] == 0x8d && b[k + 2] == 0x15 && --nth == 0)
      return body + k + 7 + (int64_t)*(const int32_t*)(b + k + 3);
  return 0;
}
static int slots_layout(uint64_t exe_base)
{
  uint64_t c = jmp_target(exe_base + COUNT_RVA), g = jmp_target(exe_base + GET_RVA),
           t = jmp_target(exe_base + SET_RVA);
  if (!c && !g && !t) return 0;
  if (!c || !g || !t) return -1;
  const unsigned char* b = (const unsigned char*)(uintptr_t)c;
  if (b[0] != 0x31 || b[1] != 0xc0 || b[2] != 0x81 || b[3] != 0xfa) return -1;
  unsigned n = *(const uint32_t*)(b + 4), d = 0;
  for (int k = 0; k < 0x40 && !d; k++)
    if (b[k] == 0x0f && b[k + 1] == 0xb7 && b[k + 2] == 0x84 && b[k + 3] == 0x41) d = *(const uint32_t*)(b + k + 4);
  uint64_t cap = nth_lea_rdx(c, 1), off = nth_lea_rdx(g, 2);
  if (n <= SLOTS || n > 1024 || !d || !cap || !off) return -1;
  g_slots = n; g_cntoff = d;
  g_cap = (const uint32_t*)(uintptr_t)cap; g_off = (const uint32_t*)(uintptr_t)off;
  logf("fl26clubs: fl26slots is loaded -- %u slots, counts at +0x%x, capacities at %llx, lists from %llx",
       n, d, (unsigned long long)cap, (unsigned long long)off);
  return 1;
}

/* 0 ok; 2 count signature; 3 get signature; 6 set signature; 4/5/7 protect failed; 9 bad config;
   10 fl26slots' readers not as expected. ncfg may be 0:
   the pools (kept-out clubs, the count an Edit refill leaves stale) are then all there is. */
__declspec(dllexport) int fl26_clubs_install(uint64_t exe_base, const fl26_clubs_cfg_t* cfg, int ncfg)
{
  if (ncfg < 0 || ncfg > MAX_CFG || (ncfg && !cfg)) return 9;
  g_base = exe_base;
  g_ncfg = ncfg;
  int widened = slots_layout(exe_base);
  if (widened < 0) return 10;
  for (int i = 0; i < ncfg; i++) {
    if (!slot_ok(cfg[i].slot)) return 9;
    g_cfg[i] = cfg[i];
    g_n[i] = -1;
  }
  /* check both before touching either, so a mismatch leaves the game unmodified */
  if (!widened) {
    if (memcmp((void*)(uintptr_t)(exe_base + COUNT_RVA), SIG_COUNT, 14)) return 2;
    if (memcmp((void*)(uintptr_t)(exe_base + GET_RVA),   SIG_GET,   14)) return 3;
    if (memcmp((void*)(uintptr_t)(exe_base + SET_RVA),   SIG_SET,   14)) return 6;
  }
  if (replace((unsigned char*)(uintptr_t)(exe_base + COUNT_RVA), (void*)count_hook)) return 4;
  if (replace((unsigned char*)(uintptr_t)(exe_base + GET_RVA),   (void*)get_hook))   return 5;
  if (replace((unsigned char*)(uintptr_t)(exe_base + SET_RVA),   (void*)set_hook))   return 7;
  if (g_nfans) {
    /* not fatal: without it the clubs keep the game's followers, as before */
    int r = install_fans(exe_base);
    if (r) logf("fl26clubs: followers NOT fixed (%s) -- %d club(s) keep the game's ranking fallback",
                r == 1 ? "ranking lookup signature differs" : r == 2 ? "followers function signature differs"
                : r == 4 ? "rank lookup signature differs"
                : "alloc/protect failed", g_nfans);
    else logf("fl26clubs: club ranking lookups replaced, followers wrapped -- %d club(s) with a class, a rank "
              "and a followers share of their own", g_nfans);
    if (!r && g_nfine) {
      int q = install_income(exe_base);
      if (q) logf("fl26clubs: season income NOT scaled (%s) -- %d club(s) keep the game's broadcasting fee and sponsors",
                  q == 1 ? "the income functions differ in this game" : "protect failed", g_nfine);
      else logf("fl26clubs: a finer followers share for %d club(s), their broadcasting fee and sponsors by it "
                "(money at block+0x%x)", g_nfine, g_fin);
    }
  }
  logf("fl26clubs: readers and the setter replaced (count@%llx get@%llx), %d slot(s) served from our regulations, "
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
