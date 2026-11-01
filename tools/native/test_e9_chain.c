/* zig cc -O2 -fno-sanitize=undefined test_e9_chain.c -o t.exe && t.exe      (fl26chain.c)
   zig cc -O2 -fno-sanitize=undefined -DSWISS test_e9_chain.c -o t.exe && t.exe   (fl26swiss.c)
   FL27 (31.10.2026): SmokePatch hooks set_clubs 0x141522b50 itself -- `jmp rel32` + ten nops over
   the 15-byte prologue, its stub ending in the displaced bytes and a jmp back to +15. hook_or_chain
   goes in front of it. A fake function in an RWX page, hooked their way, then ours on top:
   called, it runs our handler, then their stub, then the original's rest. */
#ifdef SWISS
#include "fl26swiss.c"
#else
#include "fl26chain.c"
#endif
#include <stdio.h>

static int fails = 0;
static void check(const char* what, long got, long want)
{
  if (got != want) { printf("FAIL: %s: %ld, not %ld\n", what, got, want); fails++; }
  else printf("ok: %s (%ld)\n", what, got);
}

typedef int (*fn_t)(int);
static unsigned char* g_t;
static int handler(int x) { return ((fn_t)(uintptr_t)g_t)(x * 2); }   /* ours: doubles, then theirs */
static unsigned char* g_t2;
static int handler2(int x) { return ((fn_t)(uintptr_t)g_t2)(x * 2); }

static void jmp32(unsigned char* at, unsigned char* to)
{
  at[0] = 0xE9; *(int32_t*)(at + 1) = (int32_t)(to - (at + 5));
}

int main(void)
{
  unsigned char* p = (unsigned char*)VirtualAlloc(0, 0x1000, MEM_COMMIT|MEM_RESERVE, PAGE_EXECUTE_READWRITE);
  unsigned char* target = p, *stub = p + 0x200;
  /* the original after their prologue: lea eax,[rcx+100]; ret */
  static const unsigned char ORIG_TAIL[] = { 0x8d, 0x81, 0x64, 0x00, 0x00, 0x00, 0xc3 };
  memcpy(target + 15, ORIG_TAIL, sizeof ORIG_TAIL);
  /* theirs: jmp stub + 10 nops; the stub: add ecx,7; the displaced 15 bytes (nops here); jmp +15 */
  jmp32(target, stub);
  memset(target + 5, 0x90, 10);
  stub[0] = 0x83; stub[1] = 0xc1; stub[2] = 0x07;
  memset(stub + 3, 0x90, 15);
  jmp32(stub + 18, target + 15);
  check("their hook alone: 5 + 7 + 100", ((fn_t)(uintptr_t)target)(5), 112);

  static const unsigned char SIG[15] = { 0x48,0x89,0x5c,0x24,0x08, 0x48,0x89,0x6c,0x24,0x10, 0x48,0x89,0x74,0x24,0x18 };
#ifndef SWISS
  check("usable: their e9 prologue", usable(target, SIG, 15), 1);
#endif
  check("e9_dest finds their stub", e9_dest(target, 15) == stub, 1);
  int r = hook_or_chain(target, SIG, 15, (void*)handler, &g_t);
  check("hook_or_chain over their jmp", r, 0);
  check("our jmp abs in place", target[0] == 0xFF && target[1] == 0x25, 1);
  check("byte 14 a nop, their return point +15 untouched", target[14] == 0x90 && !memcmp(target + 15, ORIG_TAIL, sizeof ORIG_TAIL), 1);
  check("ours, then theirs, then the original: 5*2 + 7 + 100", ((fn_t)(uintptr_t)target)(5), 117);

  unsigned char* q = p + 0x400;
  jmp32(q, stub); memset(q + 5, 0xcc, 10);
  unsigned char before[15]; memcpy(before, q, 15);
#ifdef SWISS
  /* fl26swiss (2275a3a): their jmp with fewer nops than our 14 bytes (the Group A page factory
     af4e20, e9 + one nop) is not refused: only its rel32 changes, to a jmp to ours within reach of
     the exe (here: of the page), and our "original" is a jmp to their stub */
  g_base = (uint64_t)(uintptr_t)p;
  check("e9 without the nops: retargeted", hook_or_chain(q, SIG, 15, (void*)handler2, &g_t2), 0);
  check("... still their e9, the bytes after it untouched", q[0] == 0xE9 && !memcmp(before + 5, q + 5, 10), 1);
  check("... ours, then theirs, then the original: 5*2 + 7 + 100", ((fn_t)(uintptr_t)q)(5), 117);
#else
  /* not their shape (e9, then no nops): refused, nothing written */
  unsigned char* t2 = 0;
  check("e9 without the nops: not chained", hook_or_chain(q, SIG, 15, (void*)handler, &t2), 2);
  check("... and left as it was", !memcmp(before, q, 15), 1);
  check("... usable says no", usable(q, SIG, 15), 0);
#endif
  if (fails) { printf("%d check(s) FAILED\n", fails); return 1; }
  printf("all checks passed\n");
  return 0;
}
