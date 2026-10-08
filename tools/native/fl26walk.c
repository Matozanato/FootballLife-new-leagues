/* fl26walk.dll -- "days until the next match" without asking the same question 365 times.
 *
 * Speed fix, not a capacity patch.  Found 08.10.2026 sampling Master League creation loads
 * (Druga NL club 113 s, Bosnian club 60 s, League Two instant, after fl26regfast and the
 * fl26swiss regulation index).
 *
 * 0x14150d990 ("day kind": what is this date for the user's club -- 0 nothing, 1/2 a match)
 * is asked once per day by three day-walks that look for the next such day, up to 365 days
 * ahead:
 *     0x141512310  days from day N to the next match   (called by 0x141576de0, which the
 *                  inbox process ProceedCompeConfirmTeam, vtable 0x1428eafd0, calls up to 6
 *                  times per evaluation)
 *     0x1415120d0  the same from today
 *     0x141577530  is a match day the last of its month (walks to the next one)
 * Every call of 0x14150d990 begins with the same two date-independent lookups:
 *     0x1414bb650(block, &team, "", &3)   the user's club, a scan of the 0x690-byte club
 *                                          table (up to 750 records)
 *     0x1415773e0(team)                    is that club's league one of ours: "which league
 *                                          is team X in" 0x141543510 (a 73-id list, the
 *                                          regulation lookup, the league's club list)
 * and only then looks at the date (two scans of the day's match list).  In the samples these
 * two lookups were about three quarters of the loading thread's time; the date part the rest.
 *
 * What the DLL does.  Each walk is wrapped: on entry the thread takes a "walk scope" (if no
 * other walk holds it) and the cache is emptied; on exit the scope is dropped and the cache
 * emptied again.  Inside 0x14150d990 the 41 bytes 0x14150da16..0x14150da3f (the two lookups,
 * result in bl, the club id in [rbp-0x39]) jump to a stub: on the thread that holds the scope,
 * the first day computes them as the game does and keeps (club, answer); every later day of
 * the same walk reuses them.  Any other caller, any other thread, or outside a walk: the
 * original two calls, unchanged.  A walk only reads -- nothing in it changes the user's club
 * or its league -- so within one walk the answer cannot change.
 *
 * Every site is checked byte for byte before anything is written; one mismatch and nothing is
 * patched.  The stubs live in a page within 2 GB of the exe (rel32 jumps).
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

#define DAYKIND      0x150d990
#define DK_SITE      0x150da16          /* mov dword [rbp+0x67], 3 ... movzx ebx, al */
#define DK_LEN       41
#define DK_BACK      0x150da3f          /* call 0x14149a470 */
#define USER_CLUB    0x14bb650
#define IS_OURS      0x15773e0
#define EMPTY_STR    0x297e527

static const unsigned char SIG_DK[DK_LEN] = {
  0xc7,0x45,0x67,0x03,0x00,0x00,0x00,                   /* mov dword [rbp+0x67], 3 */
  0x4c,0x8d,0x4d,0x67,                                  /* lea r9, [rbp+0x67] */
  0x4c,0x8d,0x05,0xff,0x0a,0x47,0x01,                   /* lea r8, [rip+...] -> 0x14297e527 */
  0x48,0x8d,0x55,0xc7,                                  /* lea rdx, [rbp-0x39] */
  0x49,0x8b,0xcf,                                       /* mov rcx, r15 */
  0xe8,0x1c,0xdc,0xfa,0xff,                             /* call 0x1414bb650 */
  0x8b,0x4d,0xc7,                                       /* mov ecx, [rbp-0x39] */
  0xe8,0xa4,0x99,0x06,0x00,                             /* call 0x1415773e0 */
  0x0f,0xb6,0xd8 };                                     /* movzx ebx, al */
static const unsigned char SIG_BACK[5] = { 0xe8,0x2c,0xca,0xf8,0xff };   /* call 0x14149a470 */

struct walk { uint32_t rva; int len; unsigned char sig[6]; const char* what; };
static const struct walk WALKS[3] = {
  { 0x1512310, 5, { 0x40,0x53,0x55,0x56,0x57 },      "days from day N to the next match" },
  { 0x15120d0, 5, { 0x40,0x53,0x55,0x56,0x57 },      "days from today to the next match" },
  { 0x1577530, 6, { 0x40,0x57,0x48,0x83,0xec,0x40 }, "last match day of the month" },
};

static unsigned char* near_alloc(uint64_t exe_base)
{
  for (uint64_t a = (exe_base & ~0xffffULL) - 0x10000; a > exe_base - 0x70000000ULL; a -= 0x10000) {
    void* p = VirtualAlloc((void*)(uintptr_t)a, 0x1000, MEM_COMMIT|MEM_RESERVE, PAGE_EXECUTE_READWRITE);
    if (p) return (unsigned char*)p;
  }
  return 0;
}

/* disp32 of a rip-relative operand at s+n, for an instruction that ends `tail` bytes later */
static int rip32(unsigned char* s, int n, void* target, int tail)
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
static int gs_tid(unsigned char* s, int n, int r11)                  /* mov rax|r11, gs:[0x48] */
{
  s[n++] = 0x65; s[n++] = r11 ? 0x4c : 0x48; s[n++] = 0x8b; s[n++] = r11 ? 0x1c : 0x04; s[n++] = 0x25;
  *(uint32_t*)(s + n) = 0x48; n += 4;
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

/* 0 ok; 2 a site is not the one expected (nothing patched); 3 no page in reach; 4 VirtualProtect */
__declspec(dllexport) int fl26_walk_install(uint64_t exe_base)
{
  unsigned char* dk = (unsigned char*)(uintptr_t)(exe_base + DK_SITE);
  if (memcmp(dk, SIG_DK, DK_LEN) || memcmp((unsigned char*)(uintptr_t)(exe_base + DK_BACK), SIG_BACK, 5)) {
    logf("fl26walk: 0x%llx is not the day-kind lookup expected -- nothing patched",
         (unsigned long long)(0x140000000ULL + DK_SITE));
    return 2;
  }
  for (int w = 0; w < 3; w++)
    if (memcmp((unsigned char*)(uintptr_t)(exe_base + WALKS[w].rva), WALKS[w].sig, WALKS[w].len)) {
      logf("fl26walk: 0x%llx (%s) is not the walk expected -- nothing patched",
           (unsigned long long)(0x140000000ULL + WALKS[w].rva), WALKS[w].what);
      return 2;
    }
  unsigned char* t = near_alloc(exe_base);
  if (!t) return 3;
  memset(t, 0xcc, 0x1000);
  /* data: scope (thread id holding the walk, 0 = none), valid, club, answer */
  uint64_t* scope = (uint64_t*)(t + 0xf00);
  uint32_t* valid = (uint32_t*)(t + 0xf08);
  uint32_t* club  = (uint32_t*)(t + 0xf0c);
  uint8_t*  ans   = (uint8_t*)(t + 0xf10);
  *scope = 0; *valid = 0; *club = 0; *ans = 0;

  /* ---- the day-kind stub ---- */
  unsigned char* s = t;
  int n = 0, j_slow1, j_slow2, j_done;
  n = gs_tid(s, n, 0);                                                    /* mov rax, gs:[0x48] */
  s[n++] = 0x48; s[n++] = 0x3b; s[n++] = 0x05; n = rip32(s, n, scope, 0); /* cmp rax, [scope] */
  s[n++] = 0x75; j_slow1 = n++;                                           /* jne slow */
  s[n++] = 0x83; s[n++] = 0x3d; n = rip32(s, n, valid, 1); s[n++] = 0x00; /* cmp dword [valid], 0 */
  s[n++] = 0x74; j_slow2 = n++;                                           /* je slow */
  s[n++] = 0x8b; s[n++] = 0x05; n = rip32(s, n, club, 0);                 /* mov eax, [club] */
  s[n++] = 0x89; s[n++] = 0x45; s[n++] = 0xc7;                            /* mov [rbp-0x39], eax */
  s[n++] = 0x0f; s[n++] = 0xb6; s[n++] = 0x1d; n = rip32(s, n, ans, 0);   /* movzx ebx, byte [ans] */
  n = jmp_abs(s, n, exe_base + DK_BACK);
  s[j_slow1] = (unsigned char)(n - (j_slow1 + 1));
  s[j_slow2] = (unsigned char)(n - (j_slow2 + 1));
  /* slow: the original 41 bytes, with absolute targets */
  s[n++] = 0xc7; s[n++] = 0x45; s[n++] = 0x67; *(uint32_t*)(s + n) = 3; n += 4;   /* mov dword [rbp+0x67], 3 */
  s[n++] = 0x4c; s[n++] = 0x8d; s[n++] = 0x4d; s[n++] = 0x67;                     /* lea r9, [rbp+0x67] */
  s[n++] = 0x49; s[n++] = 0xb8; *(uint64_t*)(s + n) = exe_base + EMPTY_STR; n += 8; /* mov r8, imm64 */
  s[n++] = 0x48; s[n++] = 0x8d; s[n++] = 0x55; s[n++] = 0xc7;                     /* lea rdx, [rbp-0x39] */
  s[n++] = 0x49; s[n++] = 0x8b; s[n++] = 0xcf;                                    /* mov rcx, r15 */
  n = call_abs_rax(s, n, exe_base + USER_CLUB);
  s[n++] = 0x8b; s[n++] = 0x4d; s[n++] = 0xc7;                                    /* mov ecx, [rbp-0x39] */
  n = call_abs_rax(s, n, exe_base + IS_OURS);
  s[n++] = 0x0f; s[n++] = 0xb6; s[n++] = 0xd8;                                    /* movzx ebx, al */
  n = gs_tid(s, n, 0);                                                            /* mov rax, gs:[0x48] */
  s[n++] = 0x48; s[n++] = 0x3b; s[n++] = 0x05; n = rip32(s, n, scope, 0);         /* cmp rax, [scope] */
  s[n++] = 0x75; j_done = n++;                                                    /* jne done */
  s[n++] = 0x8b; s[n++] = 0x45; s[n++] = 0xc7;                                    /* mov eax, [rbp-0x39] */
  s[n++] = 0x89; s[n++] = 0x05; n = rip32(s, n, club, 0);                         /* mov [club], eax */
  s[n++] = 0x88; s[n++] = 0x1d; n = rip32(s, n, ans, 0);                          /* mov [ans], bl */
  s[n++] = 0xc7; s[n++] = 0x05; n = rip32(s, n, valid, 4); *(uint32_t*)(s + n) = 1; n += 4; /* mov dword [valid], 1 */
  s[j_done] = (unsigned char)(n - (j_done + 1));
  n = jmp_abs(s, n, exe_base + DK_BACK);
  int dk_len = n;

  /* ---- the walk wrappers ---- */
  unsigned char* wrap[3];
  unsigned char* wrap_end[3];
  for (int w = 0; w < 3; w++) {
    n = (n + 15) & ~15;
    unsigned char* tramp = s + n;                                   /* the moved prologue */
    memcpy(tramp, (unsigned char*)(uintptr_t)(exe_base + WALKS[w].rva), WALKS[w].len);
    n += WALKS[w].len;
    n = jmp_abs(s, n, exe_base + WALKS[w].rva + WALKS[w].len);
    n = (n + 15) & ~15;
    wrap[w] = s + n;
    int j_notowner, j_out, c;
    s[n++] = 0x48; s[n++] = 0x83; s[n++] = 0xec; s[n++] = 0x28;                   /* sub rsp, 0x28 */
    s[n++] = 0x48; s[n++] = 0xc7; s[n++] = 0x44; s[n++] = 0x24; s[n++] = 0x20;   /* mov qword [rsp+0x20], 0 */
    *(uint32_t*)(s + n) = 0; n += 4;
    n = gs_tid(s, n, 1);                                                          /* mov r11, gs:[0x48] */
    s[n++] = 0x31; s[n++] = 0xc0;                                                 /* xor eax, eax */
    s[n++] = 0xf0; s[n++] = 0x4c; s[n++] = 0x0f; s[n++] = 0xb1; s[n++] = 0x1d;   /* lock cmpxchg [scope], r11 */
    n = rip32(s, n, scope, 0);
    s[n++] = 0x75; j_notowner = n++;                                              /* jne notowner */
    s[n++] = 0xc7; s[n++] = 0x05; n = rip32(s, n, valid, 4); *(uint32_t*)(s + n) = 0; n += 4; /* mov dword [valid], 0 */
    s[n++] = 0xc6; s[n++] = 0x44; s[n++] = 0x24; s[n++] = 0x20; s[n++] = 0x01;   /* mov byte [rsp+0x20], 1 */
    s[j_notowner] = (unsigned char)(n - (j_notowner + 1));
    s[n++] = 0xe8; c = n; n += 4;                                                 /* call tramp */
    *(int32_t*)(s + c) = (int32_t)((int64_t)(uintptr_t)tramp - (int64_t)(uintptr_t)(s + n));
    s[n++] = 0x80; s[n++] = 0x7c; s[n++] = 0x24; s[n++] = 0x20; s[n++] = 0x00;   /* cmp byte [rsp+0x20], 0 */
    s[n++] = 0x74; j_out = n++;                                                   /* je out */
    s[n++] = 0xc7; s[n++] = 0x05; n = rip32(s, n, valid, 4); *(uint32_t*)(s + n) = 0; n += 4; /* mov dword [valid], 0 */
    s[n++] = 0x48; s[n++] = 0xc7; s[n++] = 0x05; n = rip32(s, n, scope, 4);      /* mov qword [scope], 0 */
    *(uint32_t*)(s + n) = 0; n += 4;
    s[j_out] = (unsigned char)(n - (j_out + 1));
    s[n++] = 0x48; s[n++] = 0x83; s[n++] = 0xc4; s[n++] = 0x28;                   /* add rsp, 0x28 */
    s[n++] = 0xc3;                                                                /* ret */
    wrap_end[w] = s + n;
  }
  if (n > 0xe00) return 3;

  /* Unwind data for the stubs, so a stack walk (crash dump, exception) passes through them:
   * the day-kind stub runs in 0x14150d990's frame, past its prologue, so it gets a copy of that
   * function's unwind codes (without its C++ handler, whose state map would not fit the copy);
   * a wrapper is `sub rsp, 0x28` and a call. */
  {
    DWORD64 ib = 0;
    PRUNTIME_FUNCTION rf = RtlLookupFunctionEntry(exe_base + DAYKIND, &ib, NULL);
    unsigned char* ui = t + 0xe00;
    RUNTIME_FUNCTION* tab = (RUNTIME_FUNCTION*)(t + 0xe80);
    int ok = 0;
    if (rf && ib == exe_base && rf->BeginAddress == DAYKIND) {
      unsigned char* src = (unsigned char*)(uintptr_t)(exe_base + rf->UnwindData);
      int cnt = src[2];
      if (!((src[0] >> 3) & UNW_FLAG_CHAININFO) && 4 + 2 * cnt <= 0x60) {
        memcpy(ui, src, 4 + 2 * cnt);
        ui[0] = 1;                                        /* version 1, no handler */
        unsigned char* wu = ui + ((4 + 2 * cnt + 3) & ~3);
        wu[0] = 1; wu[1] = 4; wu[2] = 1; wu[3] = 0;       /* prologue 4 bytes, 1 code */
        wu[4] = 4; wu[5] = 0x42; wu[6] = 0; wu[7] = 0;    /* at 4: UWOP_ALLOC_SMALL 0x28 */
        tab[0].BeginAddress = 0; tab[0].EndAddress = (DWORD)dk_len; tab[0].UnwindData = 0xe00;
        for (int w = 0; w < 3; w++) {
          tab[1 + w].BeginAddress = (DWORD)(wrap[w] - t);
          tab[1 + w].EndAddress = (DWORD)(wrap_end[w] - t);
          tab[1 + w].UnwindData = (DWORD)(wu - t);
        }
        ok = RtlAddFunctionTable(tab, 4, (DWORD64)(uintptr_t)t) ? 1 : 0;
      }
    }
    if (!ok) logf("fl26walk: no unwind data for the stubs (stack walks stop there; the patch works the same)");
  }
  FlushInstructionCache(GetCurrentProcess(), t, 0x1000);

  if (!put_rel_jmp(dk, DK_LEN, t)) return 4;
  for (int w = 0; w < 3; w++)
    if (!put_rel_jmp((unsigned char*)(uintptr_t)(exe_base + WALKS[w].rva), WALKS[w].len, wrap[w])) return 4;
  logf("fl26walk: day walks reuse the user's club and its league (stub %d bytes, 3 walks wrapped)", dk_len);
  return 0;
}

__declspec(dllexport) int fl26_walk_log(char* out, int cap)
{
  int n = g_log_len; if (n > cap - 1) n = cap - 1; if (n < 0) n = 0;
  memcpy(out, g_log, n); out[n] = 0;
  g_log_len = 0;
  return n;
}
