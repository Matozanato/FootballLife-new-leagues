/* B246: the Libertadores phase 3 hand-over gives each match record of a tie its new pair whole,
   in its leg's order, even when the new pair shares a club with the old one.

     zig cc -O2 -fno-sanitize=undefined test_legpair.c -o test_legpair.exe && test_legpair.exe

   (tools/test_legpair.py builds and runs it.) Exit code 1 on any failure.

   libq_leg_pair from fl26swiss.c without the game (FL26_RCAL_TEST). antonimus's career, 26.10.,
   beta 12ee8bc: tie 3080 held 01374082 v 027c0130 (day 0), its F2 winners were Deportes La Serena
   027c0130 v Lanus 01e240a5. Side by side, the first leg became La Serena v La Serena and Lanus
   was gone from phase 3. */
#define FL26_RCAL_TEST
#include "fl26swiss.c"
#include <stdio.h>

int rcal_test_today(void) { return 0; }
int rcal_test_invites(int k, uint16_t id) { (void)k; (void)id; return 0; }
int rcal_test_recday(uint16_t id) { (void)id; return -1; }

static int fails = 0;
static void expect(int ok, const char* what)
{
  printf("  %s  %s\n", ok ? "ok  " : "FAIL", what);
  if (!ok) fails++;
}

static int is(const uint32_t* c, uint32_t h, uint32_t w) { return same_club(c[0], h) && same_club(c[1], w); }

int main(void)
{
  const uint32_t A = 0x01374082, SER = 0x027c0130, LAN = 0x01e240a5, X = 0x0505c08b;
  int leg;

  /* antonimus: old 01374082 v 027c0130, new 027c0130 v 01e240a5 */
  uint32_t l1[2] = { A, SER }, l2[2] = { SER, A };
  int r1 = libq_leg_pair(l1, A, SER, 0, 0, SER, LAN, &leg);
  expect(r1 == 1 && is(l1, SER, LAN), "first leg 01374082 v La Serena -> La Serena v Lanus (not La Serena twice)");
  int r2 = libq_leg_pair(l2, A, SER, 0, 0, SER, LAN, &leg);
  expect(r2 == 2 && is(l2, LAN, SER), "return leg La Serena v 01374082 -> Lanus v La Serena");

  /* the new pair the other way round over the old one: old a v b, new b v a -- the record
     already holds the two clubs and is left (as the return leg) */
  uint32_t s1[2] = { A, SER };
  int rs = libq_leg_pair(s1, A, SER, 0, 0, SER, A, &leg);
  expect(rs == 0 && leg == 2 && is(s1, A, SER), "old a v b, new b v a: left, the two clubs are the pair");

  /* a new club that was the old home side, now away */
  uint32_t t1[2] = { A, X }, t2[2] = { X, A };
  libq_leg_pair(t1, A, X, 0, 0, LAN, A, &leg);
  libq_leg_pair(t2, A, X, 0, 0, LAN, A, &leg);
  expect(is(t1, LAN, A) && is(t2, A, LAN), "old home club now the away club: both legs whole");

  /* already given: left, its leg told */
  uint32_t g[2] = { LAN, SER };
  int rg = libq_leg_pair(g, A, SER, 0, 0, SER, LAN, &leg);
  expect(rg == 0 && leg == 2 && is(g, LAN, SER), "a record already holding the new pair is left (return leg)");

  /* a hand-over run again: the records hold what this session gave last */
  uint32_t p1[2] = { 0x0223c136, 0x02aa829f };
  libq_leg_pair(p1, A, SER, 0x0223c136, 0x02aa829f, SER, LAN, &leg);
  expect(is(p1, SER, LAN), "run again: the pair given last -> the new pair");

  /* a save after the B240 swap: one side new, the other neither */
  uint32_t h1[2] = { 0x01111111, LAN };
  libq_leg_pair(h1, A, 0x02222222, 0, 0, SER, LAN, &leg);
  expect(is(h1, SER, LAN), "one side new, the other unknown: put right from the new side");

  /* left by the old hand-over: a club twice -- no pair decides */
  uint32_t d[2] = { SER, SER };
  int rd = libq_leg_pair(d, A, SER, 0, 0, SER, LAN, &leg);
  expect(rd == -1 && is(d, SER, SER), "La Serena twice: no pair decides (libq_match_swap gives it the leg left)");

  /* nothing of either pair */
  uint32_t z[2] = { 0x03333333, 0x03444444 };
  expect(libq_leg_pair(z, A, SER, 0, 0, SER, LAN, &leg) == -1 && is(z, 0x03333333, 0x03444444),
         "a record of neither pair is left alone");

  if (fails) { printf("%d check(s) FAILED\n", fails); return 1; }
  printf("all checks passed\n");
  return 0;
}
