/* The trophy ceremony's tournament map (fl26swiss.c, fl26_swiss_tmap): the world file's
   `tmap <reg> <tournament> [noleg0]` records, without the game.

     zig cc -O2 -fno-sanitize=undefined test_ceremony.c -o test_ceremony.exe && test_ceremony.exe

   (tools/test_ceremony.py builds and runs it, on Linux and macOS with tools/native/hosttest.) Exit
   code 1 on any failure. The cases: the records taken, a regulation named twice, a regulation
   outside 1..1023 and a tournament that is none (0, 217 and up) left out, at most TMAP_MAX; the
   handler answers each regulation's tournament whatever the stage bits of the key, and 217 ("no
   tournament") for any other; no hook without the game (g_base 0). */
#define FL26_RCAL_TEST
#define FL26_STATE_TEST
#include "fl26swiss.c"
#include <stdio.h>

int rcal_test_today(void) { return 100; }
int rcal_test_invites(int k, uint16_t id) { (void)k; (void)id; return 0; }
int rcal_test_recday(uint16_t id) { (void)id; return -1; }
int state_test_date(void) { return 2026 * 365 + 100; }
uint32_t state_test_user(void) { return 0x45ed8006u; }
const char* state_test_path(void) { return "fl26swiss-test-ceremony-none.bin"; }

static int fails = 0;
static void expect(int ok, const char* what)
{
  printf("  %s  %s\n", ok ? "ok  " : "FAIL", what);
  if (!ok) fails++;
}

int main(void)
{
  printf("fl26_swiss_tmap\n");
  uint16_t v[] = { 255, 30, 0,   261, 30, 0,   263, 30, TMAP_NOLEG0,   255, 31, 0,   1500, 30, 0,
                   270, 0, 0,   271, 217, 0 };
  int got = fl26_swiss_tmap(v, 7);
  expect(got == 0 && g_ntmap == 3, "three taken; 255 again, 1500, tournaments 0 and 217 left out (no hook without the game)");
  expect(g_tmap_reg[2] == 263 && g_tmap_fl[2] == TMAP_NOLEG0, "263 keeps its noleg0");
  expect(!g_tmap_live, "no hook: g_base is 0");

  printf("tmap_handler\n");
  expect(tmap_handler(255, 0) == 30 && tmap_handler(261 | (3u << 10), 0) == 30, "255 and 261 (stage 3): tournament 30");
  expect(tmap_handler(256, 0) == 0xd9 && tmap_handler(11, 0) == 0xd9, "256 and 11: no tournament (217)");

  printf("at most TMAP_MAX\n");
  uint16_t w[3 * 20];
  for (int i = 0; i < 20; i++) { w[3 * i] = (uint16_t)(300 + i); w[3 * i + 1] = 30; w[3 * i + 2] = 0; }
  fl26_swiss_tmap(w, 20);
  expect(g_ntmap == TMAP_MAX && tmap_handler(300 + TMAP_MAX - 1, 0) == 30 && tmap_handler(300 + TMAP_MAX, 0) == 0xd9,
         "16 taken, the 17th left out");

  printf(fails ? "%d check(s) FAILED\n" : "all checks passed\n", fails);
  return fails ? 1 : 0;
}
