/* fl26edit.dll -- Edit mode keeps the changes made to our clubs (GitHub #55).
 *
 * What the game does (static reading, 2026-10-05, notes in docs/findings.md "#55"): the Edit
 * data is one fixed-size heap object (0xa7c860 bytes, vtable 0x142b9a918, at EditManager +0x70)
 * whose inner part (object + 8) is written to the EDIT file as it is, encrypted, and checked for
 * its exact size on load. Three of its tables hold one record per club -- team data (0x24c
 * bytes), squad (0x11c) and tactics (0x274) -- room for 750 each (0x141ef21d0 returns the cap),
 * and a record goes in only while count < cap - 1. Every save first copies every club of the
 * database in (0x141eec0d0), the game's 749 first, so the tables are full before any club of
 * ours gets a turn: a change to one of our clubs is never stored, and on the next load it is
 * gone. Changing a club the game ships works because its record is already there.
 *
 * What this does, without changing the EDIT file:
 *
 *   - the object grows by a block of our own (EXT below): three tables of TEAMS records, and the
 *     cap is TEAMS. The three accessors the game reaches the tables through answer with our
 *     tables, so the game itself fills, sorts and reads them as before -- only with room.
 *   - the save hands the game a copy of the inner part instead of the live one: the first 749
 *     records of each table in the old places, counts cut to 749 -- the file the game has always
 *     written, which an unmodded game loads as before. The records past 749 (our clubs: their
 *     ids sort last) go to EDIT00000000.fl26x next to it, tagged with the 32 random bytes the
 *     game stamps into each save's header.
 *   - after a load the header carries a tag our block has not seen; the first touch of a table
 *     (an accessor or a count read) then rebuilds our tables from the old places, plus the
 *     .fl26x records when their tag is that header's. A file without one (the game's own
 *     dataSP EDIT, an older save) simply has no records past 749.
 *
 * Every byte patched is checked first; if one is not what it should be, nothing is patched.
 * If the Edit data already exists when the module installs (it would be the old size), nothing
 * is patched either.
 *
 * Built with `zig cc` (tools/native/build-edit.sh). Our own code, no third-party binaries.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <shlobj.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <stdarg.h>

#define EDIT_VT      0x2b9a918          /* vtable of the Edit data object                     */
#define MGR_GLOBAL   0x37f5c28          /* EditManager*; the object is at +0x70               */
#define CTOR_RVA     0x1eeace0          /* inner ctor (rcx = object + 8)                       */
#define SAVE_RVA     0x1f080a7          /* save flow, after the header stamp: lea r8,[rsi+8]   */
#define CAP_RVA      0x1ef21d0          /* mov eax, 0x2ee ; ret                                */

#define OLD_SIZE     0xa7c860u
#define INNER_SIZE   0xa7c858u          /* what goes to disk (0x50 header + 0xa7c808)         */
#define OLD_CAP      750
#define FILE_MAX     749                /* the game never stores more than cap - 1            */
#define TEAMS        2048

#define EXT          OLD_SIZE           /* our block, from the old end of the object          */
#define EXT_MAGIC    0x0
#define EXT_TAG      0x10
#define EXT_HDR      0x40
#define TAG_AT       0x30               /* in the inner header: 32 random bytes per save      */
#define TAG_LEN      32

typedef struct {
  uint32_t acc_rva;     /* the accessor: lea rax, [rcx + disp32] ; ret                      */
  uint32_t old_off;     /* table in the object (what the accessor returned)                 */
  uint32_t rec;         /* record size                                                      */
  uint32_t cnt_off;     /* u16 count in the object                                          */
  uint32_t get_rva;     /* the count getter: movzx eax, word [rcx + disp8] ; ...            */
  uint32_t new_off;     /* our table                                                        */
} table_t;

static table_t T[3] = {
  { 0x1ef2940, 0x8ed304, 0x24c, 0x6c, 0x14083e0, 0 },   /* team data                 */
  { 0x1ef2040, 0x9d4650, 0x11c, 0x78, 0x1408320, 0 },   /* squad                     */
  { 0x1ef21c0, 0xa09888, 0x274, 0x7c, 0x1408330, 0 },   /* tactics                   */
};
static uint32_t g_new_size;

/* the places that know the object's size: {rva of the imm32, old value} */
static const uint32_t SIZE_SITES[][2] = {
  { 0x1ef3446, OLD_SIZE }, { 0x1ef3595, OLD_SIZE }, { 0x1ef36c5, OLD_SIZE },   /* temp copies  */
  { 0x1ef4829, OLD_SIZE }, { 0x1eeb4b1, OLD_SIZE },                            /* live, free   */
  { 0x1ef3491, INNER_SIZE }, { 0x1ef34c2, INNER_SIZE }, { 0x1ef35dc, INNER_SIZE },
  { 0x1ef3601, INNER_SIZE }, { 0x1ef3713, INNER_SIZE },                        /* memcpy_s     */
};
#define CTOR_MEMSET  0x1eeadd4          /* r8d of the ctor's last memset (from inner+0xa09880) */
#define CTOR_MEMSET_OLD 0x72fd8u

static uint64_t g_base;
static unsigned char* g_copy;          /* the inner part the save writes                     */
static char g_side[MAX_PATH];
static uint32_t g_stat[6];             /* rebuilds, side records read, saves, side records written, cap hits, refused */

/* ---- log, drained by the Lua loader ---- */
static char g_log[4096];
static volatile long g_log_len;
static void logf(const char* fmt, ...)
{
  char b[512]; va_list a; va_start(a, fmt); int n = vsnprintf(b, sizeof b - 2, fmt, a); va_end(a);
  if (n < 0) return; if (n > (int)sizeof b - 2) n = sizeof b - 2;
  b[n++] = '\n';
  if (g_log_len + n < (long)sizeof g_log) { memcpy(g_log + g_log_len, b, n); g_log_len += n; }
}

/* ---- the objects: the ctor registers each (the live one and the temporary copies) ---- */
#define MAX_OBJ 32
static unsigned char* g_obj[MAX_OBJ];
static volatile long g_nobj;
static SRWLOCK g_lock = SRWLOCK_INIT;

static int known(unsigned char* o)
{
  for (int i = 0; i < MAX_OBJ; i++) if (g_obj[i] == o) return 1;
  return 0;
}

typedef void* (*ctor_fn)(void*);
static ctor_fn g_ctor;
static void* ctor_hook(unsigned char* inner)
{
  unsigned char* o = inner - 8;
  AcquireSRWLockExclusive(&g_lock);
  if (!known(o)) g_obj[(g_nobj++) % MAX_OBJ] = o;
  ReleaseSRWLockExclusive(&g_lock);
  void* r = g_ctor(inner);
  memset(o + EXT, 0, EXT_HDR);         /* not yet built: the first touch builds it */
  return r;
}

/* ---- the side file ---- */
#define SIDE_MAGIC "FL26EDX1"
static int side_read(const char* path, const unsigned char* tag, unsigned char* o, uint32_t* cnt)
{
  FILE* f = fopen(path, "rb");
  if (!f) return 0;
  char m[8]; unsigned char t[TAG_LEN]; uint32_t n[3]; int got = 0;
  if (fread(m, 1, 8, f) == 8 && !memcmp(m, SIDE_MAGIC, 8) && fread(t, 1, TAG_LEN, f) == TAG_LEN &&
      !memcmp(t, tag, TAG_LEN) && fread(n, 4, 3, f) == 3) {
    for (int k = 0; k < 3; k++) {
      uint32_t room = TEAMS - 1 - cnt[k];
      uint32_t take = n[k] < room ? n[k] : room;
      unsigned char* dst = o + T[k].new_off + (size_t)cnt[k] * T[k].rec;
      if (fread(dst, T[k].rec, take, f) != take) break;
      if (take < n[k]) fseek(f, (long)((n[k] - take) * T[k].rec), SEEK_CUR);
      cnt[k] += take; got += (int)take;
    }
  }
  fclose(f);
  return got;
}

static void side_write(const unsigned char* tag, unsigned char* o, const uint32_t* from, const uint32_t* to)
{
  uint32_t n[3], all = 0;
  for (int k = 0; k < 3; k++) { n[k] = to[k] - from[k]; all += n[k]; }
  /* The file is written when the game builds its save, before "Overwrite data. Proceed?" -- a No
   * there keeps the old EDIT file, whose tag is the previous .fl26x's. So that one stays, as .prev. */
  char tmp[MAX_PATH + 8], prev[MAX_PATH + 8];
  snprintf(prev, sizeof prev, "%s.prev", g_side);
  MoveFileExA(g_side, prev, MOVEFILE_REPLACE_EXISTING);
  if (!all) return;
  snprintf(tmp, sizeof tmp, "%s.tmp", g_side);
  FILE* f = fopen(tmp, "wb");
  if (!f) { logf("save: cannot write %s", tmp); return; }
  int ok = fwrite(SIDE_MAGIC, 1, 8, f) == 8 && fwrite(tag, 1, TAG_LEN, f) == TAG_LEN && fwrite(n, 4, 3, f) == 3;
  for (int k = 0; k < 3 && ok; k++)
    ok = fwrite(o + T[k].new_off + (size_t)from[k] * T[k].rec, T[k].rec, n[k], f) == n[k];
  ok = fclose(f) == 0 && ok;
  if (ok && MoveFileExA(tmp, g_side, MOVEFILE_REPLACE_EXISTING)) g_stat[3] += all;
  else logf("save: writing %s failed", g_side);
}

/* ---- our tables, built from the old places when the header's tag is new to us ---- */
static void ensure(unsigned char* o)
{
  unsigned char* ext = o + EXT;
  const unsigned char* tag = o + 8 + TAG_AT;
  if (*(uint32_t*)(ext + EXT_MAGIC) == 0x45363246u && !memcmp(ext + EXT_TAG, tag, TAG_LEN)) return;
  AcquireSRWLockExclusive(&g_lock);
  if (!(*(uint32_t*)(ext + EXT_MAGIC) == 0x45363246u && !memcmp(ext + EXT_TAG, tag, TAG_LEN))) {
    uint32_t cnt[3];
    for (int k = 0; k < 3; k++) {
      uint32_t c = *(uint16_t*)(o + T[k].cnt_off);
      if (c > FILE_MAX) c = FILE_MAX;                    /* the old places hold 750 at most */
      unsigned char* src = o + T[k].old_off;
      unsigned char* dst = o + T[k].new_off;
      memcpy(dst, src, (size_t)c * T[k].rec);
      const unsigned char* empty = src + (size_t)c * T[k].rec;   /* an unused record of the game's */
      for (uint32_t i = c; i < TEAMS; i++) memcpy(dst + (size_t)i * T[k].rec, empty, T[k].rec);
      cnt[k] = c;
    }
    int side = 0;
    int blank = 1;
    for (int i = 0; i < TAG_LEN; i++) if (tag[i]) { blank = 0; break; }
    if (!blank) {
      char prev[MAX_PATH + 8];
      snprintf(prev, sizeof prev, "%s.prev", g_side);
      side = side_read(g_side, tag, o, cnt);
      if (!side) side = side_read(prev, tag, o, cnt);
    }
    for (int k = 0; k < 3; k++) *(uint16_t*)(o + T[k].cnt_off) = (uint16_t)cnt[k];
    memcpy(ext + EXT_TAG, tag, TAG_LEN);
    *(uint32_t*)(ext + EXT_MAGIC) = 0x45363246u;      /* "F26E" */
    g_stat[0]++; g_stat[1] += side;
    if (g_stat[0] <= 20 || side)
      logf("tables built for %p: %u / %u / %u clubs (team data / squad / tactics), %d from %s",
           (void*)o, cnt[0], cnt[1], cnt[2], side, side ? "the .fl26x file" : "no .fl26x file");
  }
  ReleaseSRWLockExclusive(&g_lock);
}

/* the three accessors (only the Edit data's vtable reaches them) */
static void* acc0(unsigned char* o) { ensure(o); return o + T[0].new_off; }
static void* acc1(unsigned char* o) { ensure(o); return o + T[1].new_off; }
static void* acc2(unsigned char* o) { ensure(o); return o + T[2].new_off; }

/* the three count getters: rcx = the header at object + 0x58 */
static char getc_(int k, unsigned char* hdr, uint32_t* out)
{
  unsigned char* o = hdr - 0x58;
  if (known(o) && *(uint64_t*)o == g_base + EDIT_VT) ensure(o);
  uint32_t c = *(uint16_t*)(hdr + (T[k].cnt_off - 0x58));
  if (c >= TEAMS - 1 && k == 0 && !g_stat[4]++) logf("the Edit tables are full (%d clubs)", TEAMS - 1);
  *out = c;
  return 1;
}
static char get0(unsigned char* h, uint32_t* out) { return getc_(0, h, out); }
static char get1(unsigned char* h, uint32_t* out) { return getc_(1, h, out); }
static char get2(unsigned char* h, uint32_t* out) { return getc_(2, h, out); }

/* the save: which buffer the game writes (rsi + 8 for anything that is not the Edit data) */
static unsigned char* save_buf(unsigned char* o)
{
  if (!o || *(uint64_t*)o != g_base + EDIT_VT || !g_copy) return o + 8;
  AcquireSRWLockExclusive(&g_lock);
  unsigned char* inner = o + 8;
  memcpy(g_copy, inner, INNER_SIZE);
  uint32_t from[3], to[3];
  for (int k = 0; k < 3; k++) {
    uint32_t c = *(uint16_t*)(o + T[k].cnt_off);
    uint32_t n = c < FILE_MAX ? c : FILE_MAX;
    unsigned char* src = o + T[k].new_off;
    unsigned char* dst = g_copy + (T[k].old_off - 8);
    memcpy(dst, src, (size_t)n * T[k].rec);
    const unsigned char* empty = src + (size_t)c * T[k].rec;     /* c < TEAMS - 1 always */
    for (uint32_t i = n; i < OLD_CAP; i++) memcpy(dst + (size_t)i * T[k].rec, empty, T[k].rec);
    *(uint16_t*)(g_copy + (T[k].cnt_off - 8)) = (uint16_t)n;
    from[k] = n; to[k] = c;
  }
  side_write(inner + TAG_AT, o, from, to);
  /* the live header has the new tag: our tables are what it describes */
  memcpy(o + EXT + EXT_TAG, inner + TAG_AT, TAG_LEN);
  g_stat[2]++;
  logf("save: %u / %u / %u clubs, %u / %u / %u past %d to %s", to[0], to[1], to[2],
       to[0] - from[0], to[1] - from[1], to[2] - from[2], FILE_MAX, g_side);
  ReleaseSRWLockExclusive(&g_lock);
  return g_copy;
}

/* ---- install ---- */
static int put(uint64_t at, const void* bytes, int n)
{
  DWORD old;
  if (!VirtualProtect((void*)(uintptr_t)at, n, PAGE_EXECUTE_READWRITE, &old)) return 0;
  memcpy((void*)(uintptr_t)at, bytes, n);
  VirtualProtect((void*)(uintptr_t)at, n, old, &old);
  FlushInstructionCache(GetCurrentProcess(), (void*)(uintptr_t)at, n);
  return 1;
}

static int jmp_to(uint64_t at, void* to, int room)   /* 14-byte absolute jmp, rest int3 */
{
  unsigned char b[32];
  if (room < 14 || room > 32) return 0;
  memset(b, 0xcc, room);
  b[0] = 0xff; b[1] = 0x25; memset(b + 2, 0, 4);
  *(uint64_t*)(b + 6) = (uint64_t)(uintptr_t)to;
  return put(at, b, room);
}

static void* wrap(unsigned char* target, int stolen, void* handler)
{
  unsigned char* t = (unsigned char*)VirtualAlloc(0, 64, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
  if (!t) return 0;
  memcpy(t, target, stolen);
  t[stolen] = 0xff; t[stolen + 1] = 0x25; *(uint32_t*)(t + stolen + 2) = 0;
  *(uint64_t*)(t + stolen + 6) = (uint64_t)(uintptr_t)(target + stolen);
  if (!jmp_to((uint64_t)(uintptr_t)target, handler, stolen)) return 0;
  return t;
}

static const unsigned char SIG_CTOR[15] = { 0x48,0x89,0x5c,0x24,0x08, 0x48,0x89,0x74,0x24,0x10, 0x57, 0x48,0x83,0xec,0x20 };
/* mov [rsp+28],r14 ; xor r9d,r9d ; lea r8,[rsi+8] ; xor edx,edx */
static const unsigned char SIG_SAVE[14] = { 0x4c,0x89,0x74,0x24,0x28, 0x45,0x33,0xc9, 0x4c,0x8d,0x46,0x08, 0x33,0xd2 };
static const unsigned char SIG_CAP[6]   = { 0xb8,0xee,0x02,0x00,0x00,0xc3 };

/* 0 ok; 2 a signature differs; 3 the Edit data exists already; 4 memory; 5 patch failed */
__declspec(dllexport) int fl26_edit_install(uint64_t exe_base)
{
  g_base = exe_base;
  unsigned char* B = (unsigned char*)(uintptr_t)exe_base;
  /* check everything before touching anything */
  if (memcmp(B + CTOR_RVA, SIG_CTOR, sizeof SIG_CTOR)) { logf("ctor bytes differ"); return 2; }
  if (memcmp(B + SAVE_RVA, SIG_SAVE, sizeof SIG_SAVE)) { logf("save bytes differ"); return 2; }
  if (memcmp(B + CAP_RVA, SIG_CAP, sizeof SIG_CAP))    { logf("cap bytes differ"); return 2; }
  for (int k = 0; k < 3; k++) {
    const unsigned char* a = B + T[k].acc_rva;
    if (a[0] != 0x48 || a[1] != 0x8d || a[2] != 0x81 || *(uint32_t*)(a + 3) != T[k].old_off || a[7] != 0xc3) {
      logf("accessor %d bytes differ", k); return 2;
    }
    for (int i = 8; i < 16; i++) if (a[i] != 0xcc) { logf("accessor %d has no room", k); return 2; }
    const unsigned char* g = B + T[k].get_rva;     /* movzx eax, word [rcx+d8] ; mov [rdx],eax ; mov al,1 ; ret */
    if (g[0] != 0x0f || g[1] != 0xb7 || g[2] != 0x41 || g[3] != T[k].cnt_off - 0x58 ||
        g[4] != 0x89 || g[5] != 0x02 || g[6] != 0xb0 || g[7] != 0x01 || g[8] != 0xc3) {
      logf("count getter %d bytes differ", k); return 2;
    }
    for (int i = 9; i < 16; i++) if (g[i] != 0xcc) { logf("count getter %d has no room", k); return 2; }
  }
  for (size_t i = 0; i < sizeof SIZE_SITES / sizeof SIZE_SITES[0]; i++)
    if (*(uint32_t*)(B + SIZE_SITES[i][0]) != SIZE_SITES[i][1]) { logf("size site %#x differs", SIZE_SITES[i][0]); return 2; }
  if (*(uint32_t*)(B + CTOR_MEMSET) != CTOR_MEMSET_OLD) { logf("ctor memset differs"); return 2; }
  uint64_t mgr = *(uint64_t*)(B + MGR_GLOBAL);
  if (mgr && *(uint64_t*)(uintptr_t)(mgr + 0x70)) { logf("the Edit data exists already -- too late to grow it"); return 3; }

  /* the new layout */
  uint32_t at = EXT + EXT_HDR;
  for (int k = 0; k < 3; k++) { T[k].new_off = at; at += TEAMS * T[k].rec; }
  g_new_size = (at + 15) & ~15u;
  g_copy = (unsigned char*)VirtualAlloc(0, INNER_SIZE, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE);
  if (!g_copy) return 4;

  /* the side file sits next to the EDIT file */
  char docs[MAX_PATH];
  if (SHGetFolderPathA(0, CSIDL_PERSONAL, 0, 0, docs) != S_OK) return 4;
  snprintf(g_side, sizeof g_side, "%s\\KONAMI\\eFootball PES 2021 SEASON UPDATE\\2026\\save\\EDIT00000000.fl26x", docs);

  /* the save trampoline: our buffer in r8 */
  unsigned char* t = (unsigned char*)VirtualAlloc(0, 64, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
  if (!t) return 4;
  int p = 0;
  static const unsigned char pre[] = { 0x4c,0x89,0x74,0x24,0x28,  0x48,0x83,0xec,0x30,  0x48,0x89,0xf1,  0x48,0xb8 };
  memcpy(t + p, pre, sizeof pre); p += sizeof pre;
  *(uint64_t*)(t + p) = (uint64_t)(uintptr_t)save_buf; p += 8;
  static const unsigned char mid[] = { 0xff,0xd0,  0x48,0x83,0xc4,0x30,  0x49,0x89,0xc0,  0x45,0x31,0xc9,  0x31,0xd2,  0x48,0xb8 };
  memcpy(t + p, mid, sizeof mid); p += sizeof mid;
  *(uint64_t*)(t + p) = exe_base + SAVE_RVA + 14; p += 8;
  t[p++] = 0xff; t[p++] = 0xe0;

  /* patch: sizes, cap, accessors, getters, ctor, save */
  for (size_t i = 0; i < sizeof SIZE_SITES / sizeof SIZE_SITES[0]; i++) {
    uint32_t v = SIZE_SITES[i][1] == OLD_SIZE ? g_new_size : g_new_size - 8;
    if (!put(exe_base + SIZE_SITES[i][0], &v, 4)) return 5;
  }
  uint32_t ms = g_new_size - (8 + 0xa09880);          /* the ctor zeroes up to the new end */
  if (!put(exe_base + CTOR_MEMSET, &ms, 4)) return 5;
  uint32_t cap = TEAMS;
  if (!put(exe_base + CAP_RVA + 1, &cap, 4)) return 5;
  void* acc[3] = { (void*)acc0, (void*)acc1, (void*)acc2 };
  void* get[3] = { (void*)get0, (void*)get1, (void*)get2 };
  for (int k = 0; k < 3; k++) {
    if (!jmp_to(exe_base + T[k].acc_rva, acc[k], 16)) return 5;
    if (!jmp_to(exe_base + T[k].get_rva, get[k], 16)) return 5;
  }
  if (!(g_ctor = (ctor_fn)wrap(B + CTOR_RVA, sizeof SIG_CTOR, (void*)ctor_hook))) return 5;
  if (!jmp_to(exe_base + SAVE_RVA, t, 14)) return 5;
  logf("live: Edit data %#x -> %#x bytes, %d clubs per table (team data / squad / tactics); "
       "clubs past %d saved to %s", OLD_SIZE, g_new_size, TEAMS, FILE_MAX, g_side);
  return 0;
}

__declspec(dllexport) int fl26_edit_log(char* out, int cap)
{
  int n = (int)g_log_len; if (n > cap - 1) n = cap - 1; if (n < 0) n = 0;
  memcpy(out, g_log, n); out[n] = 0;
  if (n < g_log_len) { memmove(g_log, g_log + n, g_log_len - n); g_log_len -= n; } else g_log_len = 0;
  return n;
}

/* rebuilds, records read from .fl26x, saves, records written to .fl26x, full-table hits */
__declspec(dllexport) void fl26_edit_stats(uint32_t* out5)
{
  for (int i = 0; i < 5; i++) out5[i] = g_stat[i];
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID r) { (void)h;(void)reason;(void)r; return TRUE; }
