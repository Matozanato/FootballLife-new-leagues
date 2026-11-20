/* fl26match's pl_key (key -> player record) against a plain search, on a made-up player array
 * with every id once: players past 65534 (key word 0xffff), records filled in as the game loads
 * them, players moved to another index, players removed.  And the count of full scans: one for
 * each new player past 65534 it was (69228 in a GigaPack career, 12 s), a handful it has to be.
 *
 *     zig cc -target x86_64-windows-gnu -O2 -o test_match_plkey.exe test_match_plkey.c
 *
 * tools/test_match_plkey.py builds and runs it.
 */
#include "fl26match.c"
#include <stdlib.h>
#include <stdio.h>

#define N 90000u
static uint8_t* arr;
static uint8_t none[8];
static uint32_t rs = 777;
static uint32_t rnd(void) { rs = rs * 1664525u + 1013904223u; return rs >> 8; }
static void set(uint32_t i, uint32_t id) { *(uint32_t*)(arr + (size_t)i * PL_REC + 0x30) = id; }
static uint32_t get(uint32_t i) { return *(uint32_t*)(arr + (size_t)i * PL_REC + 0x30); }
static uint8_t* plain(uint32_t id)
{
  if (!id) return 0;
  for (uint32_t i = 0; i < N; i++) if (get(i) == id) return arr + (size_t)i * PL_REC;
  return 0;
}
static long long asked, bad;
static int stale;
static void ask(uint32_t i, uint32_t id)
{
  uint32_t w = i >= 0xffff ? 0xffff : i;
  if (stale && rnd() % 20 == 0) w = rnd() & 0xffff;           /* a word that is not his */
  uint8_t* a = pl_key(arr, (uint64_t)w | (uint64_t)id << 32), *b = plain(id);
  asked++;
  if (a != b && bad++ < 10) printf("id %u word 0x%x: pl_key %p, plain %p\n", id, w, (void*)a, (void*)b);
}

/* the game's 0x1414b80f0: the first record not below the key (word, then id), when it has the key */
static uint64_t keyof(const uint8_t* r) { uint64_t k = *(const uint64_t*)(r + 0x2c); return (k & 0xffff) << 32 | k >> 32; }
static long long bs_calls;
static uint8_t* __attribute__((ms_abi)) game_bs(uint8_t* first, uint8_t* last, uint64_t key)
{
  uint64_t want = (key & 0xffff) << 32 | key >> 32;
  size_t lo = 0, n = (size_t)(last - first) / PL_REC;
  bs_calls++;
  while (n) { size_t h = n / 2; if (keyof(first + (lo + h) * PL_REC) < want) { lo += h + 1; n -= h + 1; } else n = h; }
  uint8_t* r = first + lo * PL_REC;
  return r != last && keyof(r) == want ? r : 0;
}
/* a sorted range (word, then id), every key once: pl_bs against the game's search */
static int test_bs(void)
{
  enum { M = 60000 };
  uint8_t* a = calloc(M + 1, PL_REC);
  long long q = 0, d = 0;
  memset(g_pl_ix, 0, sizeof g_pl_ix);
  g_pl_bs = game_bs;
  for (int round = 0; round < 4; round++) {
    uint32_t w = 0, id = 100 + (uint32_t)round;
    for (uint32_t i = 0; i < M; i++) {           /* words rise slowly, ids rise */
      if (rnd() % 3 == 0 && w < 0xfffe) w++;     /* every id once, as the game has them */
      id += 1 + rnd() % 3 + (uint32_t)round % 2;
      *(uint64_t*)(a + (size_t)i * PL_REC + 0x2c) = (uint64_t)w | (uint64_t)id << 32;
    }
    for (int k = 0; k < 150000; k++) {
      uint32_t i = rnd() % M;
      uint64_t key = *(uint64_t*)(a + (size_t)i * PL_REC + 0x2c);
      if (rnd() % 5 == 0) key += (uint64_t)(rnd() % 3) << 32;          /* maybe nobody's */
      if (rnd() % 9 == 0) key = (key & ~0xffffull) | ((key + 1) & 0xffff);
      key |= (uint64_t)(rnd() & 0xffff) << 16;                         /* bits the search does not read */
      uint8_t* first = a + (size_t)(rnd() % 7 == 0 ? rnd() % 100 : 0) * PL_REC;
      uint8_t* last = a + (size_t)(M - (rnd() % 7 == 0 ? rnd() % 100 : 0)) * PL_REC;
      if ((key & 0xffff) == 0xffff) continue;
      uint8_t* x = pl_bs(first, last, key); uint8_t* y = game_bs(first, last, key);
      q++;
      if (x != y && d++ < 10) printf("pl_bs key %016llx: %p, the game %p\n", (unsigned long long)key, (void*)x, (void*)y);
    }
  }
  printf("pl_bs: %lld questions, %lld differences; %lld answered by the map\n", q, d, (long long)g_pl_x[0]);
  free(a);
  return d || g_pl_x[0] < q / 4;
}

int main(void)
{
  arr = calloc(N + 1, PL_REC);
  if (!arr) return 2;
  none[0] = 0xfe; none[1] = 0xff; *(uint32_t*)(none + 4) = 0x3ffff;
  g_pl_none = none; g_pl_cap = N;
  /* 1. all loaded, then every player asked for (the career's creation) */
  for (uint32_t i = 0; i < N; i++) set(i, 1000 + i * 2);
  for (uint32_t i = 0; i < N; i++) ask(i, get(i));
  long long s1 = g_pl_st[PS_SCAN];
  printf("all loaded first: %lld full scans for %u players past 65534\n", s1, N - 0xffff);
  stale = 1;
  /* 2. ids nobody has, moved players, removed players */
  for (int k = 0; k < 3000; k++) {
    uint32_t i = rnd() % N, j = rnd() % N, id = get(i);
    switch (rnd() % 4) {
    case 0: ask(i, 1001 + (rnd() % N) * 2); break;            /* an odd id: nobody */
    case 1: if (id && !get(j)) { set(j, id); set(i, 0); ask(j, id); } else { set(i, 0); ask(i, id); } break;
    case 2: if (id && get(j)) { uint32_t t = get(j); set(j, id); set(i, t); ask(i, t); ask(j, id); } break;
    default: ask(i, id);
    }
  }
  long long s2 = g_pl_st[PS_SCAN];
  /* 3. records filled in as they are asked for */
  memset(arr, 0, (size_t)N * PL_REC);
  memset(g_pl_ix, 0, sizeof g_pl_ix);
  for (uint32_t i = 0; i < N; i++) { set(i, 200000 + i); ask(i, 200000 + i); }
  for (uint32_t i = 0; i < N; i++) ask(i, 200000 + i);
  printf("pl_key: %lld questions, %lld differences; scans: %lld loaded first, %lld after moves, %lld in all\n",
         asked, bad, s1, s2, (long long)g_pl_st[PS_SCAN]);
  if (s1 > 40) { printf("too many full scans with all players loaded\n"); return 1; }
  if (bad) return 1;
  return test_bs();
}
