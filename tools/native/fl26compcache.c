/* fl26compcache.dll -- the per-player competition scan without asking the same question
 * sixty thousand times.
 *
 * Speed fix, not a capacity patch.  Found 13.10.2026: a 0.2.2 career (test world, 2400 clubs,
 * 600 regulations, 61905 players) sat 20-30 minutes on the loading screen on day 30 (the end of
 * January, the winter transfer deadline), every core busy.  Thread samples all ended in one loop:
 *
 *     0x140f68760 (a day event of the dispatcher 0x1413007d0)
 *       call 0x140f59360    for every player record (count at the edit block's count block,
 *                           stride 0x17c, up to 61905 with the players cap):
 *         0x141569090 -> 0x141567300 -> 0x141568d00   a score for the player's club
 *             for every regulation (up to 600): a league (kind 1, no parent) or kind 5 ->
 *               call 0x14157c6a0(reg)    -> 0x14158e000: 0x1415451a0 walks the regulation
 *                                           array for the id, 0x14159ecd0 / 0x14158df30 walk
 *                                           the season header's phase tables
 *               call 0x140fc1340         the competition's club list, searched for the club
 *
 * The lookup at 0x14157c6a0 depends on the regulation id alone and was about four fifths of the
 * busy thread.  The game asks it again for every player: 61905 x the leagues of 600 regulations.
 *
 * What the DLL does.  The call at 0x140f687df (the event's call of the player loop) goes through
 * a wrapper: the thread takes the scope and the cache is emptied; afterwards the scope is dropped
 * and fl26compcache.log (beside the dll) gets the loop's time and the cache's hits.  The call at 0x141568f86 (the lookup)
 * goes through the cache: on the thread holding the scope, the first player computes the answer
 * per regulation as the game does and keeps it; every later player reuses it.  Any other thread,
 * or outside the loop: the original call, unchanged.  The loop only reads -- it fills a map of
 * scores and changes no competition, table or club -- so within one loop the answer cannot change.
 *
 * 16.11.2026: the loop has one more caller, 0x140eeacff, run while a career is created; there the
 * lookups were a fifth of the creating thread with a large world.  It goes through the same wrapper.
 *
 * Both sites are checked (a rel32 call to the expected function) before anything is written; one
 * mismatch and nothing is patched.  The two stubs are plain jumps to the C functions, in a page
 * within 2 GB of the exe.
 *
 * The league of a team (15.11.2026).  Sampled in a GigaPack career (about 1270 regulations): a
 * Forward Time > Next took 25-33 s against 9-16 s in a one-league world with the same modules,
 * and the busy thread's first address was 0x141543510, "which league does this team play in":
 *
 *     0x1414ccd10 makes a vector of the ids of the regulations of the kinds 0xf9c2, in the
 *                 order of the regulation array (count at base + COUNT, records of 0x314 bytes
 *                 at base + REGS; an index at or past CAP reads the blank record instead)
 *     for each id:  the first record of the array with that id (a search; fl26regfast.lua and
 *                   fl26swiss made it cheaper), its kind in 0x842, and one of its
 *                   (word +0x30a & 0x7f) teams, dwords at +0x170 (0x140a9d150), is the team:
 *                   the answer is the record's id; none, 0xffff
 *
 * so every question allocates and grows a vector, looks every league up again and reads its
 * teams one call each.  The function's entry now jumps to league_of.  While the ids of the array
 * rise strictly (each id once, so "the first record with that id" is the record itself) and the
 * count is within CAP, the answer is one pass over the array: kind in 0x842, team among its
 * teams.  Otherwise the walk is the game's own, step for step (its vector, the first record with
 * the id).  COUNT, REGS and CAP are read at each question from the instructions of 0x1414ccd10,
 * as fl26caps leaves them.  The entry's bytes and those three instructions are checked first;
 * anything else there and the function is left alone.  Nothing is kept between questions and
 * nothing is written, so two threads may ask at once.  fl26compcache.log gets the count and the
 * time of the questions.
 *
 * A regulation by its id, and its kind (16.11.2026).  With league_of in, every sample of the
 * busy threads was kept with its callers (fl26loaddiag_raw.bin): in a Next 28-45 % of the
 * worker thread was in 0x141543910, "the kind of regulation id" -- a walk of the regulation
 * array from 0 for the id, then 0x1414bb000 (id -> record), which in a career (base + MODE is
 * 2) walks the array again -- and 3-7 % in 0x1414bb000 itself, from its other callers.
 *   - 0x1414bb000's entry jumps to reg_of: the index of an id is kept (id -> index + 1, 64K
 *     words) and used only while that record still carries the id and lies inside the part of
 *     the array the game would search (CAP records in mode 2, COUNT otherwise); anything else,
 *     and the id 0xffff, goes to the game's own code (its first 6 bytes moved to a stub), whose
 *     answer is remembered when it is a record of the array.
 *   - 0x141543910's entry jumps to kind_of: the same index; a miss walks as the game does.
 *   - 0x1415451a0 (out, id) -> the dword at +0x80 of the id's regulation, the game's default
 *     when nobody has it: the same walk and the same lookup, 9 % of the thread that creates a
 *     career; its entry jumps to word80_of.
 * One id in two records would make "the first record with it" something an index cannot know,
 * and the game's binary search needs the ids in order, so whenever COUNT or the base changes the
 * array is read once: ids rising strictly -> the index is used (emptied first); otherwise both
 * answers are the game's own until the count changes again.
 * The same check and bytes-first rule: entries and the four instructions carrying MODE, REGS,
 * CAP and COUNT must be the ones expected, or the two functions are left alone.
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

#define LOOP_SITE    0x0f687df          /* call 0x140f59360 -- the player loop */
#define LOOP_FN      0x0f59360
#define LOOP_SITE2   0x0eeacff          /* the loop's other call: while a career is created (16.11.2026) */
#define LOOKUP_SITE  0x1568f86          /* call 0x14157c6a0 -- competition id -> standings object */
#define LOOKUP_FN    0x157c6a0

typedef uint64_t (*fn1_t)(uint64_t);

static uint64_t g_base;
static char g_file[MAX_PATH];           /* fl26compcache.log beside the dll: the loop runs long after init */

static void filelog(const char* line)
{
  if (!g_file[0]) return;
  HANDLE h = CreateFileA(g_file, FILE_APPEND_DATA, FILE_SHARE_READ, 0, OPEN_ALWAYS, 0, 0);
  if (h == INVALID_HANDLE_VALUE) return;
  SYSTEMTIME st; GetLocalTime(&st);
  char b[512]; int n = snprintf(b, sizeof b, "%04d-%02d-%02d %02d:%02d:%02d %s\r\n",
                               st.wYear, st.wMonth, st.wDay, st.wHour, st.wMinute, st.wSecond, line);
  DWORD w; if (n > 0) WriteFile(h, b, (DWORD)n, &w, 0);
  CloseHandle(h);
}
static volatile DWORD g_scope;          /* thread id holding the loop, 0 none */
static uint64_t g_val[65536];
static uint8_t g_ok[65536];
static uint64_t g_calls, g_hits;
static int g_loops;

static uint64_t cached_lookup(uint64_t reg)
{
  fn1_t f = (fn1_t)(uintptr_t)(g_base + LOOKUP_FN);
  if (g_scope != GetCurrentThreadId()) return f(reg);
  uint16_t id = (uint16_t)reg;
  g_calls++;
  if (g_ok[id]) { g_hits++; return g_val[id]; }
  uint64_t v = f(reg);
  g_val[id] = v; g_ok[id] = 1;
  return v;
}

static uint64_t loop_wrap(uint64_t self)
{
  fn1_t f = (fn1_t)(uintptr_t)(g_base + LOOP_FN);
  DWORD me = GetCurrentThreadId();
  if (InterlockedCompareExchange((volatile LONG*)&g_scope, (LONG)me, 0) != 0) return f(self);
  memset(g_ok, 0, sizeof g_ok);
  g_calls = g_hits = 0;
  DWORD t0 = GetTickCount();
  uint64_t r = f(self);
  DWORD ms = GetTickCount() - t0;
  memset(g_ok, 0, sizeof g_ok);
  InterlockedExchange((volatile LONG*)&g_scope, 0);
  if (g_loops++ < 400) {
    char b[200];
    snprintf(b, sizeof b, "player loop %.1f s, %llu competition lookups, %llu from the cache",
             ms / 1000.0, (unsigned long long)g_calls, (unsigned long long)g_hits);
    filelog(b);
  }
  return r;
}

/* ---- the league of a team ---- */
static int jmp_abs(unsigned char* s, int n, uint64_t to);
#define LOT_FN     0x1543510
#define LOT_MGR    0x14b6a60            /* () -> the object whose +0x48 is the base */
#define LOT_LIST   0x14ccd10            /* (vector*) : the ids of the regulations to ask */
#define LOT_COUNT  0x14ccd2b            /* mov r14d, [rbp + COUNT] : 44 8b b5 disp32 */
#define LOT_CAP    0x14ccd50            /* cmp edi, CAP            : 81 ff imm32 */
#define LOT_REGS   0x14ccd6a            /* add rcx, REGS           : 48 81 c1 imm32 */
#define LOT_FREE   0x03fb5b0            /* (int* 2, p) : the vector's memory back */
#define REC        0x314

typedef struct { uint16_t* b; uint16_t* e; uint16_t* cap; } lot_vec_t;
static volatile LONG64 g_lot_calls, g_lot_ticks, g_lot_slow;

static int lot_has(const uint8_t* r, uint32_t team)
{
  uint32_t kind = (*(const uint32_t*)(r + 0x308) >> 0x17) & 0x3f;
  if (kind > 0xb || !((0x842u >> kind) & 1)) return 0;
  uint32_t n = *(const uint16_t*)(r + 0x30a) & 0x7f;
  const uint32_t* t = (const uint32_t*)(r + 0x170);
  for (uint32_t i = 0; i < n; i++) if (t[i] == team) return 1;
  return 0;
}

/* the game's own walk */
static uint32_t lot_slow(uint8_t* regs, uint32_t count, uint32_t team)
{
  uint32_t out = 0xffff;
  lot_vec_t v = { 0, 0, 0 };
  ((void (*)(lot_vec_t*))(uintptr_t)(g_base + LOT_LIST))(&v);
  for (uint16_t* p = v.b; p != v.e; p++) {
    uint16_t id = *p;
    if (id == 0xffff) continue;
    uint8_t* r = 0;
    for (uint32_t i = 0; i < count; i++)
      if (*(uint16_t*)(regs + (uint64_t)i * REC) == id) { r = regs + (uint64_t)i * REC; break; }
    if (r && lot_has(r, team)) { out = id; break; }
  }
  if (v.b) { int two = 2; ((void (*)(int*, void*))(uintptr_t)(g_base + LOT_FREE))(&two, v.b); }
  return out;
}

static uint32_t league_of(uint32_t team)
{
  LARGE_INTEGER q0, q1;
  QueryPerformanceCounter(&q0);
  uint8_t* base = *(uint8_t**)((uint8_t*)((void* (*)(void))(uintptr_t)(g_base + LOT_MGR))() + 0x48);
  uint32_t count = *(uint32_t*)(base + *(int32_t*)(uintptr_t)(g_base + LOT_COUNT + 3));
  uint32_t cap = *(uint32_t*)(uintptr_t)(g_base + LOT_CAP + 2);
  uint8_t* regs = base + *(int32_t*)(uintptr_t)(g_base + LOT_REGS + 3);
  uint32_t out = 0xffff;
  int plain = count <= cap, found = 0;
  if (plain) {
    int32_t last = -1;
    const uint8_t* r = regs;
    for (uint32_t i = 0; i < count; i++, r += REC) {
      uint16_t id = *(const uint16_t*)r;
      if ((int32_t)id <= last || id == 0xffff) { plain = 0; break; }
      last = id;
      if (!found && lot_has(r, team)) { found = 1; out = id; }
    }
  }
  if (!plain) { out = lot_slow(regs, count, team); InterlockedIncrement64(&g_lot_slow); }
  QueryPerformanceCounter(&q1);
  InterlockedAdd64(&g_lot_ticks, q1.QuadPart - q0.QuadPart);
  LONG64 n = InterlockedIncrement64(&g_lot_calls);
  if ((n == 1000 || n % 100000 == 0) && n <= 20000000) {
    LARGE_INTEGER f; QueryPerformanceFrequency(&f);
    char b[200];
    snprintf(b, sizeof b, "league of a team: %lld questions, %.2f s in all, %lld by the game's own walk, %u regulations",
             (long long)n, (double)g_lot_ticks / (double)f.QuadPart, (long long)g_lot_slow, (unsigned)count);
    filelog(b);
  }
  return out;
}

/* the entry of 0x141543510 -> league_of; 0 done, 2 not the bytes expected, 4 VirtualProtect */
static int lot_install(uint64_t exe_base, unsigned char* stub)
{
  static const unsigned char ENTRY[15] = { 0x89, 0x4c, 0x24, 0x08, 0x55, 0x56, 0x57, 0x41, 0x54, 0x41, 0x55,
                                           0x41, 0x56, 0x41, 0x57 };
  static const unsigned char LIST[9] = { 0x48, 0x89, 0x5c, 0x24, 0x20, 0x55, 0x57, 0x41, 0x56 };
  static const unsigned char CNT[3] = { 0x44, 0x8b, 0xb5 };
  static const unsigned char CAP[2] = { 0x81, 0xff };
  static const unsigned char REGS[3] = { 0x48, 0x81, 0xc1 };
  unsigned char* at = (unsigned char*)(uintptr_t)(exe_base + LOT_FN);
  if (memcmp(at, ENTRY, sizeof ENTRY) || memcmp((void*)(uintptr_t)(exe_base + LOT_LIST), LIST, sizeof LIST) ||
      memcmp((void*)(uintptr_t)(exe_base + LOT_COUNT), CNT, sizeof CNT) ||
      memcmp((void*)(uintptr_t)(exe_base + LOT_CAP), CAP, sizeof CAP) ||
      memcmp((void*)(uintptr_t)(exe_base + LOT_REGS), REGS, sizeof REGS))
    return 2;
  jmp_abs(stub, 0, (uint64_t)(uintptr_t)league_of);
  FlushInstructionCache(GetCurrentProcess(), stub, 16);
  DWORD old;
  if (!VirtualProtect(at, 5, PAGE_EXECUTE_READWRITE, &old)) return 4;
  at[0] = 0xe9;
  *(int32_t*)(at + 1) = (int32_t)((int64_t)(uintptr_t)stub - (int64_t)(exe_base + LOT_FN + 5));
  VirtualProtect(at, 5, old, &old);
  FlushInstructionCache(GetCurrentProcess(), at, 5);
  return 0;
}

/* ---- a regulation by its id, and its kind ---- */
#define REG_FN     0x14bb000            /* (base, id) -> record; the blank record when nobody has it */
#define REG_MODE   0x14bb024            /* cmp dword [rcx + MODE], 2 : 83 b9 disp32 02 */
#define REG_REGS   0x14bb02f            /* add rcx, REGS             : 48 81 c1 imm32 */
#define REG_CAP    0x14bb045            /* cmp eax, CAP              : 3d imm32 */
#define REG_COUNT  0x14bb070            /* mov eax, [rcx + COUNT]    : 8b 81 disp32 */
#define KIND_FN    0x1543910            /* (id) -> the kind of its regulation, 0 when nobody has it */
#define W80_FN     0x15451a0            /* (out, id) -> out; *out = dword [regulation + 0x80], or the default */
#define W80_COUNT  0x15451bc            /* mov ecx, [r9 + COUNT] : 41 8b 89 disp32 */
#define W80_REGS   0x15451c7            /* lea rax, [r9 + REGS]  : 49 8d 81 disp32 */
#define W80_DEF    0x15451e3            /* mov eax, [rip + default] : 8b 05 rel32 */

typedef uint8_t* (*reg_fn_t)(uint8_t*, uint64_t);
static reg_fn_t g_reg_game;             /* the game's 0x1414bb000, past our jump */
static uint16_t g_rix[65536];           /* id -> index + 1; 0 not known */
static uint8_t* volatile g_rix_base;
static volatile LONG g_rix_count = -1, g_rix_ok, g_rix_lock;
static volatile LONG64 g_reg_calls, g_reg_hits, g_kind_calls, g_kind_hits, g_rix_resets;

/* the array changed size or place: do its ids rise strictly (each once, and in the order a
   binary search needs)? */
static void rix_look(uint8_t* base, uint8_t* regs, uint32_t count)
{
  if (InterlockedCompareExchange(&g_rix_lock, 1, 0) != 0) return;     /* another thread is at it */
  InterlockedExchange(&g_rix_ok, 0);
  memset(g_rix, 0, sizeof g_rix);
  int ok = 1;
  int32_t last = -1;
  for (uint32_t i = 0; i < count; i++) {
    uint16_t id = *(uint16_t*)(regs + (uint64_t)i * REC);
    if ((int32_t)id <= last || id == 0xffff) { ok = 0; break; }
    last = id;
  }
  g_rix_base = base;
  InterlockedExchange(&g_rix_count, (LONG)count);
  InterlockedExchange(&g_rix_ok, ok);
  InterlockedIncrement64(&g_rix_resets);
  InterlockedExchange(&g_rix_lock, 0);
}

/* the record of the index kept for id, when it may be used; else 0 */
static inline uint8_t* rix_hit(uint8_t* base, uint8_t* regs, uint32_t count, uint32_t limit, uint16_t id)
{
  if (g_rix_base != base || (uint32_t)g_rix_count != count) { rix_look(base, regs, count); return 0; }
  if (!g_rix_ok || g_rix_lock) return 0;
  uint32_t k = g_rix[id];
  if (!k || k > count || k > limit) return 0;
  uint8_t* r = regs + (uint64_t)(k - 1) * REC;
  if (*(uint16_t*)r != id) return 0;
  if (k > 1 && *(uint16_t*)(r - REC) >= id) return 0;            /* its neighbours still in order */
  if (k < count && *(uint16_t*)(r + REC) <= id) return 0;
  return r;
}

static inline void rix_keep(uint8_t* base, uint8_t* regs, uint32_t count, uint16_t id, uint8_t* r)
{
  if (!g_rix_ok || g_rix_lock || g_rix_base != base || (uint32_t)g_rix_count != count) return;
  if (r < regs || r >= regs + (uint64_t)count * REC || (uint64_t)(r - regs) % REC) return;
  if (*(uint16_t*)r == id) g_rix[id] = (uint16_t)((uint64_t)(r - regs) / REC + 1);
}

static volatile LONG64 g_reg_said;
static void reg_stats(void)
{
  LONG64 n = g_reg_calls + g_kind_calls, said = g_reg_said;
  if (n < said + (said ? 2000000 : 100000) || n > 2000000000) return;
  if (InterlockedCompareExchange64(&g_reg_said, n, said) != said) return;
  char b[240];
  snprintf(b, sizeof b, "regulation by id: %lld questions, %lld from the index; kind of a regulation: %lld, %lld from the index; "
           "the array looked over %lld times, ids %s", (long long)g_reg_calls, (long long)g_reg_hits, (long long)g_kind_calls,
           (long long)g_kind_hits, (long long)g_rix_resets, g_rix_ok ? "rising" : "NOT rising (index off)");
  filelog(b);
}

static uint8_t* reg_of(uint8_t* base, uint64_t idq)
{
  uint16_t id = (uint16_t)idq;
  InterlockedIncrement64(&g_reg_calls);
  if (id != 0xffff) {
    uint8_t* regs = base + *(int32_t*)(uintptr_t)(g_base + REG_REGS + 3);
    uint32_t count = *(uint32_t*)(base + *(int32_t*)(uintptr_t)(g_base + REG_COUNT + 2));
    uint32_t limit = *(int32_t*)(base + *(int32_t*)(uintptr_t)(g_base + REG_MODE + 2)) == 2
                     ? *(uint32_t*)(uintptr_t)(g_base + REG_CAP + 1) : count;
    uint8_t* r = rix_hit(base, regs, count, limit, id);
    if (r) { if (!(InterlockedIncrement64(&g_reg_hits) & 0xfffff)) reg_stats(); return r; }
    r = g_reg_game(base, idq);
    rix_keep(base, regs, count, id, r);
    reg_stats();
    return r;
  }
  return g_reg_game(base, idq);
}

static uint32_t kind_of(uint32_t idq)
{
  uint16_t id = (uint16_t)idq;
  uint8_t* base = *(uint8_t**)((uint8_t*)((void* (*)(void))(uintptr_t)(g_base + LOT_MGR))() + 0x48);
  uint8_t* regs = base + *(int32_t*)(uintptr_t)(g_base + REG_REGS + 3);
  uint32_t count = *(uint32_t*)(base + *(int32_t*)(uintptr_t)(g_base + REG_COUNT + 2));
  InterlockedIncrement64(&g_kind_calls);
  uint8_t* r = 0;
  if (id != 0xffff) {
    uint32_t limit = *(int32_t*)(base + *(int32_t*)(uintptr_t)(g_base + REG_MODE + 2)) == 2
                     ? *(uint32_t*)(uintptr_t)(g_base + REG_CAP + 1) : count;
    r = rix_hit(base, regs, count, limit, id);
    if (r) InterlockedIncrement64(&g_kind_hits);
  }
  if (!r) {                                       /* as the game: is the id in the array, then its record */
    uint32_t i = 0;
    for (; i < count; i++) if (*(uint16_t*)(regs + (uint64_t)i * REC) == id) break;
    if (i == count) return 0;
    r = g_reg_game(base, id);
    if (id != 0xffff) rix_keep(base, regs, count, id, r);
    reg_stats();
  }
  return (*(uint32_t*)(r + 0x308) >> 0x17) & 0x3f;
}

static volatile LONG64 g_w80_calls, g_w80_hits;
static uint32_t* word80_of(uint32_t* out, uint32_t idq)
{
  uint16_t id = (uint16_t)idq;
  uint8_t* base = *(uint8_t**)((uint8_t*)((void* (*)(void))(uintptr_t)(g_base + LOT_MGR))() + 0x48);
  int32_t dregs = *(int32_t*)(uintptr_t)(g_base + W80_REGS + 3), dcount = *(int32_t*)(uintptr_t)(g_base + W80_COUNT + 3);
  uint8_t* regs = base + dregs;
  uint32_t count = *(uint32_t*)(base + dcount);
  InterlockedIncrement64(&g_w80_calls);
  uint8_t* r = 0;
  if (id != 0xffff && dregs == *(int32_t*)(uintptr_t)(g_base + REG_REGS + 3) && dcount == *(int32_t*)(uintptr_t)(g_base + REG_COUNT + 2)) {
    uint32_t limit = *(int32_t*)(base + *(int32_t*)(uintptr_t)(g_base + REG_MODE + 2)) == 2
                     ? *(uint32_t*)(uintptr_t)(g_base + REG_CAP + 1) : count;
    r = rix_hit(base, regs, count, limit, id);
    if (r) InterlockedIncrement64(&g_w80_hits);
  }
  if (!r) {
    uint32_t i = 0;
    for (; i < count; i++) if (*(uint16_t*)(regs + (uint64_t)i * REC) == id) break;
    if (i == count) {
      uint64_t at = g_base + W80_DEF;
      *out = *(uint32_t*)(uintptr_t)(at + 6 + *(int32_t*)(uintptr_t)(at + 2));
      return out;
    }
    r = g_reg_game(base, id);
    if (id != 0xffff) rix_keep(base, regs, count, id, r);
  }
  *out = *(uint32_t*)(r + 0x80);
  return out;
}

static int put_jmp5(uint64_t at_va, unsigned char* to, int pad)
{
  unsigned char* at = (unsigned char*)(uintptr_t)at_va;
  DWORD old;
  if (!VirtualProtect(at, 5 + pad, PAGE_EXECUTE_READWRITE, &old)) return 0;
  at[0] = 0xe9;
  *(int32_t*)(at + 1) = (int32_t)((int64_t)(uintptr_t)to - (int64_t)(at_va + 5));
  for (int i = 0; i < pad; i++) at[5 + i] = 0x90;
  VirtualProtect(at, 5 + pad, old, &old);
  FlushInstructionCache(GetCurrentProcess(), at, 5 + pad);
  return 1;
}

/* 0 done, 2 not the bytes expected, 4 VirtualProtect; stub: 64 bytes of the near page */
static int reg_install(uint64_t exe_base, unsigned char* stub)
{
  static const unsigned char REG_E[11] = { 0x40, 0x53, 0x48, 0x83, 0xec, 0x20, 0xb8, 0xff, 0xff, 0x00, 0x00 };
  static const unsigned char KIND_E[9] = { 0x40, 0x53, 0x48, 0x83, 0xec, 0x20, 0x0f, 0xb7, 0xd9 };
  static const unsigned char MODE[2] = { 0x83, 0xb9 }, REGS[3] = { 0x48, 0x81, 0xc1 }, CNT[2] = { 0x8b, 0x81 };
  unsigned char* e = (unsigned char*)(uintptr_t)exe_base;
  if (memcmp(e + REG_FN, REG_E, sizeof REG_E) || memcmp(e + KIND_FN, KIND_E, sizeof KIND_E) ||
      memcmp(e + REG_MODE, MODE, 2) || e[REG_MODE + 6] != 2 || memcmp(e + REG_REGS, REGS, 3) ||
      e[REG_CAP] != 0x3d || memcmp(e + REG_COUNT, CNT, 2))
    return 2;
  memcpy(stub, REG_E, 6);                         /* push rbx; sub rsp, 0x20; then the game's own code */
  jmp_abs(stub, 6, exe_base + REG_FN + 6);
  jmp_abs(stub + 24, 0, (uint64_t)(uintptr_t)reg_of);
  jmp_abs(stub + 40, 0, (uint64_t)(uintptr_t)kind_of);
  FlushInstructionCache(GetCurrentProcess(), stub, 64);
  g_reg_game = (reg_fn_t)(uintptr_t)stub;
  if (!put_jmp5(exe_base + REG_FN, stub + 24, 1)) return 4;
  if (!put_jmp5(exe_base + KIND_FN, stub + 40, 1)) return 4;
  static const unsigned char W80_E[17] = { 0x48, 0x89, 0x5c, 0x24, 0x08, 0x57, 0x48, 0x83, 0xec, 0x20, 0x0f, 0xb7, 0xda, 0x48, 0x8b, 0xf9, 0xe8 };
  if (!memcmp(e + W80_FN, W80_E, sizeof W80_E) && e[W80_COUNT] == 0x41 && e[W80_COUNT + 1] == 0x8b && e[W80_COUNT + 2] == 0x89 &&
      e[W80_REGS] == 0x49 && e[W80_REGS + 1] == 0x8d && e[W80_REGS + 2] == 0x81 && e[W80_DEF] == 0x8b && e[W80_DEF + 1] == 0x05) {
    jmp_abs(stub + 56, 0, (uint64_t)(uintptr_t)word80_of);
    FlushInstructionCache(GetCurrentProcess(), stub, 80);
    if (!put_jmp5(exe_base + W80_FN, stub + 56, 0)) return 4;
  }
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

static int is_call_to(uint64_t site, uint64_t fn)
{
  unsigned char* p = (unsigned char*)(uintptr_t)site;
  return p[0] == 0xe8 && site + 5 + (int64_t)*(int32_t*)(p + 1) == fn;
}

static int put_call(uint64_t site, unsigned char* to)
{
  unsigned char* at = (unsigned char*)(uintptr_t)site;
  DWORD old;
  if (!VirtualProtect(at, 5, PAGE_EXECUTE_READWRITE, &old)) return 0;
  *(int32_t*)(at + 1) = (int32_t)((int64_t)(uintptr_t)to - (int64_t)(site + 5));
  VirtualProtect(at, 5, old, &old);
  FlushInstructionCache(GetCurrentProcess(), at, 5);
  return 1;
}

static int jmp_abs(unsigned char* s, int n, uint64_t to)
{
  s[n++] = 0xff; s[n++] = 0x25; *(uint32_t*)(s + n) = 0; n += 4; *(uint64_t*)(s + n) = to; n += 8;
  return n;
}

/* 0 ok; 2 a site is not the one expected (nothing patched); 3 no page in reach; 4 VirtualProtect */
__declspec(dllexport) int fl26_compcache_install(uint64_t exe_base);
__declspec(dllexport) int fl26_compcache_install(uint64_t exe_base)
{
  g_base = exe_base;
  {
    HMODULE me = 0;
    GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                       (LPCSTR)(uintptr_t)fl26_compcache_install, &me);
    DWORD k = me ? GetModuleFileNameA(me, g_file, MAX_PATH - 32) : 0;
    char* dot = k ? strrchr(g_file, '.') : 0;
    if (dot) strcpy(dot, ".log"); else g_file[0] = 0;
  }
  if (!is_call_to(exe_base + LOOP_SITE, exe_base + LOOP_FN) ||
      !is_call_to(exe_base + LOOKUP_SITE, exe_base + LOOKUP_FN)) {
    logf("fl26compcache: 0x%llx / 0x%llx are not the calls expected -- nothing patched",
         (unsigned long long)(0x140000000ULL + LOOP_SITE), (unsigned long long)(0x140000000ULL + LOOKUP_SITE));
    return 2;
  }
  unsigned char* t = near_alloc(exe_base);
  if (!t) return 3;
  memset(t, 0xcc, 0x1000);
  int n = jmp_abs(t, 0, (uint64_t)(uintptr_t)loop_wrap);
  unsigned char* s2 = t + 16;
  jmp_abs(s2, 0, (uint64_t)(uintptr_t)cached_lookup);
  (void)n;
  FlushInstructionCache(GetCurrentProcess(), t, 0x1000);
  if (!put_call(exe_base + LOOKUP_SITE, s2)) return 4;
  if (!put_call(exe_base + LOOP_SITE, t)) return 4;
  if (is_call_to(exe_base + LOOP_SITE2, exe_base + LOOP_FN)) {
    if (!put_call(exe_base + LOOP_SITE2, t)) return 4;
    logf("fl26compcache: the same for the loop's call while a career is created");
  }
  logf("fl26compcache: the per-player competition scan reuses each competition's lookup (2 calls redirected)");
  int lr = lot_install(exe_base, t + 32);
  if (lr == 0) logf("fl26compcache: the league of a team is found in one pass over the regulations");
  else logf("fl26compcache: the league of a team left as the game has it (%s)",
            lr == 2 ? "0x141543510 is not the code expected" : "the page could not be written");
  int rr = reg_install(exe_base, t + 64);
  if (rr == 0) logf("fl26compcache: a regulation and its kind are found through an index of the ids");
  else logf("fl26compcache: regulation lookups left as the game has them (%s)",
            rr == 2 ? "0x1414bb000 / 0x141543910 are not the code expected" : "the page could not be written");
  return 0;
}

__declspec(dllexport) int fl26_compcache_log(char* out, int cap)
{
  int n = g_log_len; if (n > cap - 1) n = cap - 1; if (n < 0) n = 0;
  memcpy(out, g_log, n); out[n] = 0;
  g_log_len = 0;
  return n;
}
