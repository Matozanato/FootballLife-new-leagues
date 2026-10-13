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
 * Both sites are checked (a rel32 call to the expected function) before anything is written; one
 * mismatch and nothing is patched.  The two stubs are plain jumps to the C functions, in a page
 * within 2 GB of the exe.
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
  logf("fl26compcache: the per-player competition scan reuses each competition's lookup (2 calls redirected)");
  return 0;
}

__declspec(dllexport) int fl26_compcache_log(char* out, int cap)
{
  int n = g_log_len; if (n > cap - 1) n = cap - 1; if (n < 0) n = 0;
  memcpy(out, g_log, n); out[n] = 0;
  g_log_len = 0;
  return n;
}
