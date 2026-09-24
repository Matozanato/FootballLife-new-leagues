/* fl26chain.dll -- complete a 3-tier promotion/relegation chain at season end.
 *
 * Why (docs/season-rollover-decode.md): the season-end mover 0x141365110 exchanges clubs
 * between a league and the league below it ONCE per pass. For our chain A(11) -> B(49) ->
 * C(60) the visit of A already produces B's new list, and B's own visit is then skipped
 * because B "already has an OUTPUT entry", so B never relegates to C and C never promotes.
 * The mover cannot be fixed with data. This module finishes the job at the apply step,
 * using the game's own standings and the game's own list writer, for OUR leagues only.
 *
 * Two additive inline hooks, both verified against expected bytes before patching:
 *   1. 0x14135bff0  apply(ctx)                          -- CALL-style hook (pre + post)
 *      pre : remember ctx, fetch the final standings of B and C through the game's own
 *            0x141353750(ctx, &vec, id, fromInput=1) while the INPUT list is still intact
 *      post: if the pass wrote both B and C, move the last DemoteNumber(B) clubs of B's
 *            standings down and the first PromoteNumber(C) eligible clubs of C up, fix the
 *            league-slot byte like the mover does, and re-write both lists through the
 *            original 0x141522b50.
 *   2. 0x141522b50  set_regulation_teams(id, &handles, flag) -- BEFORE-hook (observer)
 *      records (id, count) in a small observation ring and, while inside apply, keeps a
 *      copy of the lists the game writes for B and C.
 *
 * Facts used (all measured statically, see the doc):
 *   - 0x141522b50 only READS the vector {begin,end,cap} of u32 handles; it clears +0x170 of
 *     the regulation, pushes each non-null handle (cap 48), stores the flag, finalises.
 *   - 0x141353750 fills a vector of 16-byte entries, handle at +0, standings order top-down;
 *     the out vector must be zero-initialised; the game allocates it (we leak ~1 KB/season).
 *   - club record = 0x1414bca80(block, handle) or NULL; +0x41c low 7 bits = league slot;
 *     +0x628 != 0 => never promoted. block = [[0x143705e10]+0x48].
 *   - A pass that moves clubs in one direction only would change league sizes; the mover
 *     itself does that, we do not: if either side has nothing to move, nothing moves.
 *
 * Built with `zig cc` (tools/native/build-chain.sh). Our own code, no third-party binaries.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <string.h>
#include <stdio.h>
#include <stdarg.h>

#define SET_RVA    0x1522b50   /* set_regulation_teams(u16 id, vec_u32* handles, u8 flag) */
#define APPLY_RVA  0x135bff0   /* apply(ctx): writes every OUTPUT entry of the season-end pass */
#define STAND_RVA  0x1353750   /* copy_standings(ctx, vec16* out, u16 id, u8 fromInput)      */
#define CLUB_RVA   0x14bca80   /* club_record(block, handle) -> record or NULL              */
#define OWNER_RVA  0x3705e10   /* global: owner; block = [owner+0x48]                       */
#define INPUT_RVA  0x13536f0   /* input_entry(ctx, u16 id) -> INPUT entry or NULL           */
#define TABLE_RVA  0x158e000   /* league_table(u16 id) -> season table (0x187c bytes) or NULL */

#define OFF_SLOT   0x41c
#define OFF_PARENT 0x628
#define NOPARENT_RVA 0x351ae44  /* global "no parent club" sentinel the mover compares to */
#define MAX_CLUBS  48
#define MAX_CHAINS 8

/* prologues we steal (whole, position-independent instructions) */
static const unsigned char SIG_SET[15] = {                 /* mov [rsp+8],rbx; mov [rsp+10],rbp; mov [rsp+18],rsi */
  0x48,0x89,0x5c,0x24,0x08, 0x48,0x89,0x6c,0x24,0x10, 0x48,0x89,0x74,0x24,0x18 };
static const unsigned char SIG_APPLY[15] = {               /* push rdi (REX-prefixed); sub rsp,40; mov qword [rsp+20],-2 */
  0x40,0x57, 0x48,0x83,0xec,0x40, 0x48,0xc7,0x44,0x24,0x20,0xfe,0xff,0xff,0xff };

typedef struct { uint32_t* b; uint32_t* e; uint32_t* c; } vec32_t;
typedef struct { unsigned char* b; unsigned char* e; unsigned char* c; } vec16_t;
typedef struct { uint16_t mid, low; uint8_t demote_mid, promote_low; uint8_t pad[2]; } fl26_chain_cfg_t;

typedef char           (*set_fn)(uint64_t id, vec32_t* v, uint64_t flag);
typedef void           (*stand_fn)(void* ctx, vec16_t* out, uint64_t id, uint64_t fromInput);
typedef unsigned char* (*club_fn)(unsigned char* block, uint64_t handle);
typedef unsigned char* (*input_fn)(void* ctx, uint64_t id);
typedef unsigned char* (*table_fn)(uint64_t id);

typedef struct {
  fl26_chain_cfg_t cfg;
  uint32_t stand_mid[MAX_CLUBS], stand_low[MAX_CLUBS]; int n_stand_mid, n_stand_low;
  uint32_t list_mid[MAX_CLUBS],  list_low[MAX_CLUBS];  int n_list_mid,  n_list_low;
  uint64_t flag_mid, flag_low;
  int seen;                       /* bit0 = mid list captured, bit1 = low list captured */
} chain_t;

static uint64_t          g_base = 0;
unsigned char*           g_tramp_set   = 0;    /* referenced by the naked stubs */
unsigned char*           g_tramp_apply = 0;
static volatile uint32_t* g_cave = 0;
static chain_t           g_chain[MAX_CHAINS];
static int               g_nchain = 0;
static volatile int      g_in_apply = 0, g_reentrant = 0;
static void*             g_ctx = 0;

/* counters readable from Lua: applies seen, fixes done, fixes refused, anomalies */
static volatile uint32_t g_stat[4];

/* ---- small text log, drained by the Lua loader into sider.log ---- */
static char g_log[8192]; static volatile int g_log_len = 0;
static void logf(const char* fmt, ...)
{
  char line[256]; va_list ap; va_start(ap, fmt);
  int n = vsnprintf(line, sizeof line, fmt, ap); va_end(ap);
  if (n <= 0) return; if (n >= (int)sizeof line) n = sizeof line - 1;
  if (g_log_len + n + 1 >= (int)sizeof g_log) return;
  memcpy(g_log + g_log_len, line, n); g_log_len += n; g_log[g_log_len++] = '\n';
}

static unsigned char* block(void) {
  unsigned char* owner = *(unsigned char**)(uintptr_t)(g_base + OWNER_RVA);
  return owner ? *(unsigned char**)(owner + 0x48) : 0;
}
static int vcount32(vec32_t* v) { return (v && v->b && v->e >= v->b) ? (int)((v->e - v->b)) : 0; }

/* ---- guard: our regulations are never emptied while they hold clubs ----
 * 2026-09-22, the first August world: at New Year the calendar-year season-end pass rewrote
 * 76, 93, 94, 96, 98 and 162 -- ours, on ids the shipped data treats as calendar-year
 * leagues -- with EMPTY club lists, in the middle of their August-May season. The ids come
 * from the loader (fl26_chain_protect). */
#define MAX_PROTECT 64
#define REG_ARRAY_OFF 0x1c84230   /* edit block + this = regulation records (caps sets), as fl26join.c */
#define REG_STRIDE    0x314
#define REG_CAP       600
static uint16_t g_protect[MAX_PROTECT]; static int g_nprotect = 0;
static int is_protected(uint16_t id) { for (int i = 0; i < g_nprotect; i++) if (g_protect[i] == id) return 1; return 0; }

/* clubs in the regulation's +0x170 list (u32 handles, 0xffffffff ends it), -1 if not found */
static int reg_count(uint16_t id)
{
  unsigned char* blk = block(); if (!blk) return -1;
  unsigned char* rec = blk + REG_ARRAY_OFF;
  for (int i = 0; i < REG_CAP; i++, rec += REG_STRIDE) {
    if (*(uint16_t*)rec != id) continue;
    int n = 0;
    while (n < MAX_CLUBS && *(uint32_t*)(rec + 0x170 + n*4) != 0xffffffffu) n++;
    return n;
  }
  return -1;
}

/* ---- observer + capture (BEFORE-hook on 0x141522b50); nonzero = refuse the write ---- */
int observe(uint64_t id, vec32_t* v, uint64_t flag)
{
  int n = vcount32(v);
  if (n == 0 && !g_reentrant && is_protected((uint16_t)id)) {
    int have = reg_count((uint16_t)id);
    if (have > 0) {
      g_stat[3]++;
      logf("guard: refused an empty club list for %u (it holds %d clubs)", (unsigned)(uint16_t)id, have);
      return 1;
    }
  }
  if (g_cave) {
    g_cave[0]++;
    uint32_t idx = g_cave[1] & 63;
    uint16_t* ring = (uint16_t*)((void*)(g_cave + 2));
    ring[idx*2] = (uint16_t)id; ring[idx*2+1] = (uint16_t)n;
    g_cave[1] = (g_cave[1] + 1) & 63;
  }
  if (!g_in_apply || g_reentrant) return 0;
  for (int i = 0; i < g_nchain; i++) {
    chain_t* ch = &g_chain[i];
    int m = n > MAX_CLUBS ? MAX_CLUBS : n;
    if ((uint16_t)id == ch->cfg.mid) { memcpy(ch->list_mid, v->b, m*4); ch->n_list_mid = m; ch->flag_mid = flag & 0xff; ch->seen |= 1; }
    if ((uint16_t)id == ch->cfg.low) { memcpy(ch->list_low, v->b, m*4); ch->n_list_low = m; ch->flag_low = flag & 0xff; ch->seen |= 2; }
  }
  return 0;
}

__attribute__((naked)) void set_handler(void)
{
  __asm__ volatile(
    "sub  $0x38, %rsp\n"
    "mov  %rcx, 0x20(%rsp)\n"
    "mov  %rdx, 0x28(%rsp)\n"
    "mov  %r8,  0x30(%rsp)\n"
    "call observe\n"
    "test %eax, %eax\n"
    "jz   1f\n"
    "add  $0x38, %rsp\n"
    "mov  $1, %eax\n"            /* refused: report success, write nothing */
    "ret\n"
    "1:\n"
    "mov  0x20(%rsp), %rcx\n"
    "mov  0x28(%rsp), %rdx\n"
    "mov  0x30(%rsp), %r8\n"
    "add  $0x38, %rsp\n"
    "jmp  *g_tramp_set(%rip)\n");
}

/* ---- apply pre/post ---- */
static int fetch_standings(void* ctx, uint16_t id, uint32_t* out)
{
  vec16_t v = {0,0,0};
  ((stand_fn)(uintptr_t)(g_base + STAND_RVA))(ctx, &v, id, 1);
  int n = 0;
  if (v.b && v.e >= v.b) {
    n = (int)((v.e - v.b) / 16); if (n > MAX_CLUBS) n = MAX_CLUBS;
    for (int i = 0; i < n; i++) out[i] = *(uint32_t*)(v.b + i*16);
  }
  return n;   /* the game's buffer is intentionally not freed (allocator unknown; ~1 KB per season) */
}

/* Fallback when the pass carries no INPUT table for a league (2026-09-22: three applies,
   every one "standings 0/0", although both lists were written). Read the league's season
   table the same way the INPUT filler 0x14135e3a0 does: 0x14158e000(id) -> table, 48 slots
   of 16 bytes at +0x10, handle in dword 0, empty slot = the "none" sentinel. Table order is
   the order the filler copies, i.e. the final standings. */
static int fetch_table(uint16_t id, uint32_t* out)
{
  unsigned char* t = ((table_fn)(uintptr_t)(g_base + TABLE_RVA))(id);
  if (!t) return -1;
  uint32_t none = *(uint32_t*)(uintptr_t)(g_base + NOPARENT_RVA);
  int n = 0;
  for (int i = 0; i < MAX_CLUBS; i++) {
    uint32_t h = *(uint32_t*)(t + 0x10 + i*16);
    if (h == none) continue;
    out[n++] = h;
  }
  return n;
}

static int standings(void* ctx, uint16_t id, uint32_t* out)
{
  int n = fetch_standings(ctx, id, out);
  if (n > 0) return n;
  unsigned char* in = ((input_fn)(uintptr_t)(g_base + INPUT_RVA))(ctx, id);
  int t = fetch_table(id, out);
  logf("apply: %u has no INPUT standings (entry %s); season table %s, %d clubs",
       id, in ? "present" : "missing", t < 0 ? "missing" : "found", t < 0 ? 0 : t);
  return t < 0 ? 0 : t;
}

void apply_pre(void* ctx)
{
  g_ctx = ctx; g_in_apply = 1; g_stat[0]++;
  for (int i = 0; i < g_nchain; i++) {
    chain_t* ch = &g_chain[i];
    ch->seen = 0; ch->n_list_mid = ch->n_list_low = 0;
    ch->n_stand_mid = standings(ctx, ch->cfg.mid, ch->stand_mid);
    ch->n_stand_low = standings(ctx, ch->cfg.low, ch->stand_low);
    logf("apply: chain %u->%u standings %d/%d", ch->cfg.mid, ch->cfg.low, ch->n_stand_mid, ch->n_stand_low);
  }
}

static int remove_handle(uint32_t* list, int n, uint32_t h)
{
  for (int i = 0; i < n; i++) if (list[i] == h) { memmove(list + i, list + i + 1, (n - i - 1) * 4); return n - 1; }
  return -1;
}

static void fix_chain(chain_t* ch)
{
  unsigned char* blk = block(); if (!blk) { logf("fix: no block"); g_stat[3]++; return; }
  club_fn club = (club_fn)(uintptr_t)(g_base + CLUB_RVA);
  int k = ch->cfg.demote_mid, p = ch->cfg.promote_low;
  uint32_t down[MAX_CLUBS], up[MAX_CLUBS]; int nd = 0, nu = 0;

  if (ch->n_stand_mid >= k) for (int i = ch->n_stand_mid - k; i < ch->n_stand_mid; i++) down[nd++] = ch->stand_mid[i];
  /* The mover promotes a club only when its +0x628 equals the global sentinel at
     0x14351ae44 -- read at 0x141365827, compared in two halves (low 14 bits at 0x14136582f,
     upper 18 at 0x141365839), which is the same split the club id uses. Measured live on
     2026-09-21: the sentinel is 0xffffffff and all 1486 clubs, ours and shipped, carry it.
     The earlier test here demanded zero, which is why the 2026-09-20 season promoted nobody. */
  uint32_t none = *(uint32_t*)(uintptr_t)(g_base + NOPARENT_RVA);
  for (int i = 0; i < ch->n_stand_low && nu < p; i++) {
    unsigned char* c = club(blk, ch->stand_low[i]);
    if (c && *(uint32_t*)(c + OFF_PARENT) == none) up[nu++] = ch->stand_low[i];
  }

  /* Safety net. With the sentinel read correctly this should never fire; if it does, say
     what each club carried and take the top of the table anyway. The chain is configured for
     our own leagues only, so this can never touch a shipped pyramid. */
  if (nu < p) {
    int blocked = nu; nu = 0;
    for (int i = 0; i < ch->n_stand_low && nu < p; i++) {
      unsigned char* c = club(blk, ch->stand_low[i]);
      uint32_t par = c ? *(uint32_t*)(c + OFF_PARENT) : 0;
      if (par) logf("fix %u->%u: club %08x has +0x628 = %08x", ch->cfg.mid, ch->cfg.low,
                    ch->stand_low[i], par);
      up[nu++] = ch->stand_low[i];
    }
    logf("fix %u->%u: only %d of %d clubs were eligible -- promoting the top %d anyway",
         ch->cfg.mid, ch->cfg.low, blocked, p, nu);
  }
  if (nd == 0 || nu == 0) { logf("fix %u->%u: nothing to move (down %d, up %d)", ch->cfg.mid, ch->cfg.low, nd, nu); g_stat[2]++; return; }

  uint32_t nb[MAX_CLUBS], nc[MAX_CLUBS]; int nnb = ch->n_list_mid, nnc = ch->n_list_low;
  memcpy(nb, ch->list_mid, nnb*4); memcpy(nc, ch->list_low, nnc*4);
  for (int i = 0; i < nd; i++) { int r = remove_handle(nb, nnb, down[i]); if (r < 0) { logf("fix: relegated club %08x not in %u's list -- aborting", down[i], ch->cfg.mid); g_stat[3]++; return; } nnb = r; }
  for (int i = 0; i < nu; i++) { int r = remove_handle(nc, nnc, up[i]);   if (r < 0) { logf("fix: promoted club %08x not in %u's list -- aborting", up[i], ch->cfg.low); g_stat[3]++; return; } nnc = r; }
  if (nnb + nu > MAX_CLUBS || nnc + nd > MAX_CLUBS) { logf("fix: list overflow"); g_stat[3]++; return; }
  for (int i = 0; i < nu; i++) nb[nnb++] = up[i];
  for (int i = 0; i < nd; i++) nc[nnc++] = down[i];

  /* league-slot byte, exactly like the mover: relegated take the slot of the promoted and vice versa */
  unsigned char* c0 = club(blk, down[0]); unsigned char* c1 = club(blk, up[0]);
  uint32_t slot_mid = c0 ? (*(uint32_t*)(c0 + OFF_SLOT) & 0x7f) : 0x7b;
  uint32_t slot_low = c1 ? (*(uint32_t*)(c1 + OFF_SLOT) & 0x7f) : 0x7b;
  for (int i = 0; i < nd; i++) { unsigned char* c = club(blk, down[i]); if (c) *(uint32_t*)(c + OFF_SLOT) = (*(uint32_t*)(c + OFF_SLOT) & 0xffffff80u) | slot_low; }
  for (int i = 0; i < nu; i++) { unsigned char* c = club(blk, up[i]);   if (c) *(uint32_t*)(c + OFF_SLOT) = (*(uint32_t*)(c + OFF_SLOT) & 0xffffff80u) | slot_mid; }

  vec32_t vb = { nb, nb + nnb, nb + MAX_CLUBS }, vc = { nc, nc + nnc, nc + MAX_CLUBS };
  set_fn orig = (set_fn)(uintptr_t)g_tramp_set;
  g_reentrant = 1;
  orig(ch->cfg.mid, &vb, ch->flag_mid);
  orig(ch->cfg.low, &vc, ch->flag_low);
  g_reentrant = 0;
  g_stat[1]++;
  logf("fix %u->%u: %d down (%08x %08x %08x) %d up (%08x %08x %08x); lists now %d/%d; slots %u/%u",
       ch->cfg.mid, ch->cfg.low, nd, down[0], nd>1?down[1]:0, nd>2?down[2]:0, nu, up[0], nu>1?up[1]:0, nu>2?up[2]:0,
       nnb, nnc, slot_mid, slot_low);
}

void apply_post(void* ctx)
{
  (void)ctx;
  for (int i = 0; i < g_nchain; i++) {
    chain_t* ch = &g_chain[i];
    if (ch->seen == 3) fix_chain(ch);
    else if (ch->seen) { logf("apply: chain %u->%u incomplete (seen %d) -- untouched", ch->cfg.mid, ch->cfg.low, ch->seen); g_stat[2]++; }
  }
  g_in_apply = 0; g_ctx = 0;
}

/* CALL-style hook: pre, original, post; rax of the original preserved.
 * entry rsp = 8 mod 16; push,push -> 8; sub 0x28 -> 0 (aligned for the calls).
 * Callee home space [rsp+8, rsp+0x28) lies inside our 0x28 area. */
__attribute__((naked)) void apply_handler(void)
{
  __asm__ volatile(
    "push %rbx\n"
    "push %rbp\n"
    "sub  $0x28, %rsp\n"
    "mov  %rcx, %rbx\n"
    "call apply_pre\n"
    "mov  %rbx, %rcx\n"
    "call *g_tramp_apply(%rip)\n"
    "mov  %rax, %rbp\n"
    "mov  %rbx, %rcx\n"
    "call apply_post\n"
    "mov  %rbp, %rax\n"
    "add  $0x28, %rsp\n"
    "pop  %rbp\n"
    "pop  %rbx\n"
    "ret\n");
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

/* 0 ok; 2/3/4 = set-hook signature/alloc/protect; 12/13/14 = apply-hook signature/alloc/protect; 9 bad config */
__declspec(dllexport) int fl26_chain_install(uint64_t exe_base, uint64_t cave_addr, const fl26_chain_cfg_t* cfg, int ncfg)
{
  if (!cfg || ncfg < 1 || ncfg > MAX_CHAINS) return 9;
  g_base = exe_base; g_cave = (volatile uint32_t*)(uintptr_t)cave_addr;
  g_nchain = ncfg;
  for (int i = 0; i < ncfg; i++) { memset(&g_chain[i], 0, sizeof g_chain[i]); g_chain[i].cfg = cfg[i]; }
  /* Check both prologues before touching either, so a mismatch really does leave the game
     unmodified rather than half hooked. */
  if (memcmp((void*)(uintptr_t)(exe_base + SET_RVA),   SIG_SET,   15)) return 2;
  if (memcmp((void*)(uintptr_t)(exe_base + APPLY_RVA), SIG_APPLY, 15)) return 12;
  int r = hook((unsigned char*)(uintptr_t)(exe_base + SET_RVA), SIG_SET, 15, (void*)set_handler, &g_tramp_set);
  if (r) return r;
  r = hook((unsigned char*)(uintptr_t)(exe_base + APPLY_RVA), SIG_APPLY, 15, (void*)apply_handler, &g_tramp_apply);
  if (r) return r + 10;
  logf("fl26chain: hooks live (set@%llx apply@%llx), %d chain(s)", (unsigned long long)(exe_base + SET_RVA), (unsigned long long)(exe_base + APPLY_RVA), ncfg);
  return 0;
}

/* the regulations the empty-list guard protects; returns how many were taken */
__declspec(dllexport) int fl26_chain_protect(const uint16_t* ids, int n)
{
  if (!ids || n < 0) return 0;
  if (n > MAX_PROTECT) n = MAX_PROTECT;
  for (int i = 0; i < n; i++) g_protect[i] = ids[i];
  g_nprotect = n;
  logf("fl26chain: empty-list guard on %d of our regulations", n);
  return n;
}

/* copy and clear the pending log text; returns bytes copied */
__declspec(dllexport) int fl26_chain_log(char* out, int cap)
{
  int n = g_log_len; if (n > cap - 1) n = cap - 1; if (n < 0) n = 0;
  memcpy(out, g_log, n); out[n] = 0;
  if (n < g_log_len) { memmove(g_log, g_log + n, g_log_len - n); g_log_len -= n; } else g_log_len = 0;
  return n;
}

/* applies seen, fixes done, refused (nothing to move / incomplete), anomalies */
__declspec(dllexport) void fl26_chain_stats(uint32_t* out4)
{
  for (int i = 0; i < 4; i++) out4[i] = g_stat[i];
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID r) { (void)h;(void)reason;(void)r; return TRUE; }
