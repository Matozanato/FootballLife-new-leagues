/* fl26compcache's league_of against the game's walk, written out literally, on made-up regulation
 * arrays: ids rising, ids repeated, ids out of order, more records than CAP, an empty array.
 *
 *     zig cc -target x86_64-windows-gnu -O1 -o test_compcache_league.exe test_compcache_league.c
 *     test_compcache_league.exe          -> "league_of: N questions, 0 differences", exit 0
 *
 * A fake "exe" of 0x1600000 bytes carries what league_of reads from the game: the three
 * instructions of 0x1414ccd10 with COUNT, CAP and REGS, and jumps at 0x1414b6a60 (the owner),
 * 0x1414ccd10 (the list) and 0x1403fb5b0 (free) to the C stand-ins below.  tools/test_compcache_league.py
 * builds and runs it.
 */
#include "fl26compcache.c"
#include <stdlib.h>

#define T_COUNT 0x9000
#define T_REGS  0x10000
#define T_BLANK 0x8000
#define MAXREC  700
#define T_MODE  0x9010

static uint8_t* t_base;
static struct { void* pad[9]; uint8_t* base; } t_owner;       /* +0x48 */
static uint32_t t_cap;
static int t_lists, t_frees;

static void* t_mgr(void) { t_owner.base = t_base; return &t_owner; }

static uint8_t* t_rec(uint32_t i)
{
  return i < t_cap ? t_base + T_REGS + (uint64_t)i * REC : t_base + T_BLANK;
}

static void t_list(lot_vec_t* v)                              /* 0x1414ccd10 */
{
  uint32_t count = *(uint32_t*)(t_base + T_COUNT), n = 0;
  uint16_t* b = malloc(sizeof(uint16_t) * (count + 1));
  for (uint32_t i = 0; i < count; i++) {
    uint8_t* r = t_rec(i);
    uint32_t kind = (*(uint32_t*)(r + 0x308) >> 0x17) & 0x3f;
    if (kind <= 0xf && ((0xf9c2u >> kind) & 1)) b[n++] = *(uint16_t*)r;
  }
  v->b = b; v->e = b + n; v->cap = b + count + 1;
  t_lists++;
}

static void t_free(int* two, void* p) { if (*two != 2) abort(); free(p); t_frees++; }

/* 0x1414bb000 as the game has it: in mode 2 the first of CAP records, else a binary search */
static uint8_t* t_getrec(uint8_t* base, uint64_t idq)
{
  uint16_t id = (uint16_t)idq;
  uint8_t* regs = base + T_REGS; uint8_t* blank = base + T_BLANK;
  if (id == 0xffff) return blank;
  if (*(uint32_t*)(base + T_MODE) == 2) {
    for (uint32_t i = 0; i < t_cap; i++) if (*(uint16_t*)(regs + (uint64_t)i * REC) == id) return regs + (uint64_t)i * REC;
    return blank;
  }
  int64_t n = *(uint32_t*)(base + T_COUNT); uint8_t* lo = regs; uint8_t* end = regs + n * REC;
  while (n > 0) {
    int64_t h = n / 2;
    if (*(uint16_t*)(lo + h * REC) < id) { lo += (h + 1) * REC; n -= h + 1; } else n = h;
  }
  return lo != end && *(uint16_t*)lo == id ? lo : blank;
}
/* 0x141543910 as the game has it */
static uint32_t t_kind(uint32_t idq)
{
  uint16_t id = (uint16_t)idq;
  uint32_t count = *(uint32_t*)(t_base + T_COUNT), i = 0;
  for (; i < count; i++) if (*(uint16_t*)(t_base + T_REGS + (uint64_t)i * REC) == id) break;
  if (i == count) return 0;
  return (*(uint32_t*)(t_getrec(t_base, id) + 0x308) >> 0x17) & 0x3f;
}

/* 0x141543510 as the game has it */
static uint32_t t_game(uint32_t team)
{
  uint32_t count = *(uint32_t*)(t_base + T_COUNT), out = 0xffff;
  lot_vec_t v = { 0, 0, 0 };
  t_list(&v); t_lists--;
  for (uint16_t* p = v.b; p != v.e; p++) {
    uint16_t id = *p;
    if (id == 0xffff || !count) continue;
    uint32_t i = 0;
    for (; i < count; i++) if (*(uint16_t*)(t_base + T_REGS + (uint64_t)i * REC) == id) break;
    if (i == count) continue;
    uint8_t* r = t_base + T_REGS + (uint64_t)i * REC;
    uint32_t kind = (*(uint32_t*)(r + 0x308) >> 0x17) & 0x3f;
    if (kind > 0xb || !((0x842u >> kind) & 1)) continue;
    uint32_t n = *(uint16_t*)(r + 0x30a) & 0x7f, k = 0;
    for (; k < n; k++) {
      uint32_t t = *(uint32_t*)(r + 0x170 + 4 * k);
      if ((t & 0x3fff) == (team & 0x3fff) && !((t ^ team) & 0xffffc000)) break;
    }
    if (k < n) { out = *(uint16_t*)r; break; }
  }
  free(v.b);
  return out;
}

static uint32_t rnd_s = 12345;
static uint32_t rnd(void) { rnd_s = rnd_s * 1664525u + 1013904223u; return rnd_s >> 8; }

static void put_jmp(uint8_t* exe, uint32_t rva, void* to)
{
  uint8_t* p = exe + rva;
  p[0] = 0x48; p[1] = 0xb8; memcpy(p + 2, &to, 8); p[10] = 0xff; p[11] = 0xe0;   /* mov rax, to; jmp rax */
}

int main(void)
{
  uint8_t* exe = VirtualAlloc(0, 0x1600000, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
  t_base = calloc(1, T_REGS + 2001 * REC);            /* CAP records, as the game has them */
  if (!exe || !t_base) return 2;
  g_base = (uint64_t)(uintptr_t)exe;
  put_jmp(exe, LOT_MGR, t_mgr);
  put_jmp(exe, LOT_LIST + 0x200, t_list);          /* the list's entry bytes are checked below, so */
  put_jmp(exe, LOT_FREE, t_free);                 /* league_of is given the stand-in by a second jump */
  static const uint8_t cnt[7] = { 0x44, 0x8b, 0xb5 }, cap[6] = { 0x81, 0xff }, regs[7] = { 0x48, 0x81, 0xc1 };
  memcpy(exe + LOT_COUNT, cnt, 3); *(int32_t*)(exe + LOT_COUNT + 3) = T_COUNT;
  memcpy(exe + LOT_CAP, cap, 2);
  memcpy(exe + LOT_REGS, regs, 3); *(int32_t*)(exe + LOT_REGS + 3) = T_REGS;
  {                                                /* 0x1414ccd10: jmp +0x200 */
    uint8_t* p = exe + LOT_LIST; p[0] = 0xe9; *(int32_t*)(p + 1) = 0x200 - 5;
  }
  {
    static const uint8_t m[2] = { 0x83, 0xb9 }, rg[3] = { 0x48, 0x81, 0xc1 }, cn[2] = { 0x8b, 0x81 };
    memcpy(exe + REG_MODE, m, 2); *(int32_t*)(exe + REG_MODE + 2) = T_MODE; exe[REG_MODE + 6] = 2;
    memcpy(exe + REG_REGS, rg, 3); *(int32_t*)(exe + REG_REGS + 3) = T_REGS;
    exe[REG_CAP] = 0x3d;
    memcpy(exe + REG_COUNT, cn, 2); *(int32_t*)(exe + REG_COUNT + 2) = T_COUNT;
    g_reg_game = t_getrec;
    static const uint8_t wc[3] = { 0x41, 0x8b, 0x89 }, wr[3] = { 0x49, 0x8d, 0x81 };
    memcpy(exe + W80_COUNT, wc, 3); *(int32_t*)(exe + W80_COUNT + 3) = T_COUNT;
    memcpy(exe + W80_REGS, wr, 3); *(int32_t*)(exe + W80_REGS + 3) = T_REGS;
    exe[W80_DEF] = 0x8b; exe[W80_DEF + 1] = 0x05; *(int32_t*)(exe + W80_DEF + 2) = 0x1000;
    *(uint32_t*)(exe + W80_DEF + 6 + 0x1000) = 0x5eedf00d;
  }
  long long asked = 0, bad = 0, plain_cases = 0, rasked = 0, rbad = 0;
  for (int c = 0; c < 400; c++) {
    int shape = c % 8;                             /* 0-3 rising ids; 4 repeats; 5 disorder; 6 past CAP; 7 empty */
    uint32_t count = shape == 7 ? 0 : 1 + rnd() % MAXREC;
    t_cap = shape == 6 ? count / 2 : 2000;
    *(uint32_t*)(exe + LOT_CAP + 2) = t_cap;
    *(uint32_t*)(exe + REG_CAP + 1) = t_cap;
    *(uint32_t*)(t_base + T_MODE) = (c / 8) % 3 == 0 ? 2 : (c / 8) % 3;
    *(uint32_t*)(t_base + T_COUNT) = count;
    memset(t_base + T_REGS, 0, (MAXREC + 1) * REC);
    memset(t_base + T_BLANK, 0, REC);
    *(uint16_t*)(t_base + T_BLANK) = 0xffff;
    uint32_t id = rnd() % 5;
    for (uint32_t i = 0; i < count; i++) {
      uint8_t* r = t_base + T_REGS + (uint64_t)i * REC;
      id += 1 + rnd() % 3;
      uint32_t use = id;
      if (shape == 4 && rnd() % 9 == 0 && i) use = *(uint16_t*)(r - REC * (1 + rnd() % (i < 5 ? i : 5)));
      if (shape == 5 && rnd() % 9 == 0) use = rnd() % (id + 50);
      if (shape == 3 && rnd() % 200 == 0) use = 0xffff;
      *(uint16_t*)r = (uint16_t)use;
      *(uint32_t*)(r + 0x80) = rnd() * 77u + i;
      static const uint8_t kinds[] = { 1, 1, 1, 6, 11, 0, 2, 7, 8, 12, 15, 16, 20 };
      *(uint32_t*)(r + 0x308) = ((uint32_t)kinds[rnd() % sizeof kinds] << 0x17) | (rnd() & 0x7fffff) | ((rnd() & 3) << 30);
      uint32_t n = rnd() % 5 == 0 ? rnd() % 128 : 8 + rnd() % 16;
      *(uint16_t*)(r + 0x30a) = (uint16_t)(n | ((rnd() & 0x1ff) << 7));
      for (uint32_t k = 0; k < 127; k++)           /* past n too: those must not count */
        *(uint32_t*)(r + 0x170 + 4 * k) = (rnd() % 600) | ((rnd() % 4 == 0 ? rnd() % 3 : 0) << 14);
    }
    LONG64 slow0 = g_lot_slow;
    for (int q = 0; q < 700; q++) {
      uint32_t team = (rnd() % 620) | ((rnd() % 4 == 0 ? rnd() % 3 : 0) << 14);
      uint32_t a = league_of(team), b = t_game(team);
      asked++;
      if (a != b) { if (bad++ < 10) printf("case %d shape %d count %u team 0x%x: league_of %u, the game %u\n", c, shape, count, team, a, b); }
    }
    if (g_lot_slow == slow0) plain_cases++;
    for (int q = 0; q < 3000; q++) {               /* a regulation by its id, and its kind */
      uint32_t idq = count && rnd() % 4 ? *(uint16_t*)(t_base + T_REGS + (uint64_t)(rnd() % count) * REC) : rnd() % (id + 40);
      if (rnd() % 300 == 0) idq = 0xffff;
      if (shape < 3 && count > 2 && q == 1500) {   /* the last record goes: the count changes */
        count--; *(uint32_t*)(t_base + T_COUNT) = count;
      }
      uint8_t* a = reg_of(t_base, idq | 0xabcd0000u); uint8_t* b = t_getrec(t_base, idq);
      uint32_t ka = kind_of(idq | 0x10000u), kb = t_kind(idq);
      rasked += 3;
      {
        uint32_t wa = 1, wb = 0x5eedf00d, k = 0, cnt = *(uint32_t*)(t_base + T_COUNT);
        uint32_t* ret = word80_of(&wa, idq | 0x770000u);
        for (; k < cnt; k++) if (*(uint16_t*)(t_base + T_REGS + (uint64_t)k * REC) == (uint16_t)idq) break;
        if (k < cnt) wb = *(uint32_t*)(t_getrec(t_base, idq) + 0x80);
        if (ret != &wa || wa != wb) { if (rbad++ < 10) printf("case %d id %u: word80 %08x / %08x\n", c, idq, wa, wb); }
      }
      if (a != b || ka != kb) { if (rbad++ < 10) printf("case %d shape %d mode %u count %u cap %u id %u: reg %p / %p, kind %u / %u\n", c, shape, *(uint32_t*)(t_base + T_MODE), count, t_cap, idq, (void*)a, (void*)b, ka, kb); }
    }
  }
  printf("regulation by id and its kind: %lld questions, %lld differences; from the index %lld + %lld, the array looked over %lld times\n",
         rasked, rbad, (long long)g_reg_hits, (long long)g_kind_hits, (long long)g_rix_resets);
  if (rbad) return 1;
  if (g_reg_hits + g_kind_hits + g_w80_hits < rasked / 8 || !g_w80_hits) { printf("the index was not exercised as meant\n"); return 1; }
  printf("league_of: %lld questions, %lld differences; %lld of 400 arrays answered in one pass; lists %d, frees %d\n",
         asked, bad, plain_cases, t_lists, t_frees);
  if (t_lists != t_frees) { printf("a list was not freed\n"); return 1; }
  if (plain_cases < 150 || plain_cases > 330) { printf("the one-pass path was not exercised as meant\n"); return 1; }
  return bad ? 1 : 0;
}
