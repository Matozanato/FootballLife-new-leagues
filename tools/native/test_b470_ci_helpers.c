/* B470 (morpheus 15.11., reproduced on the rig 17.11.): Competition Info listed every continental
   cup's preliminary round (leaguebuilder prepare_cup_prelims, FL_PRE<n>) as a second item with its
   cup's name -- "CAF Champions League", "CAF Confederation Cup", "CONCACAF Champions Cup" and
   "OFC Champions League" twice each, the second one the pre-round: two clubs and a grey bracket
   for the OFC (sider.log 30.06.2027: "comp 768 Group stage, reg 708 group A: 2 clubs").

     zig cc -O2 -fno-sanitize=undefined -w test_b470_ci_helpers.c -o test_b470_ci_helpers.exe && test_b470_ci_helpers.exe

   (tools/test_b470_ci_helpers.py builds and runs it.) Exit code 1 on any failure.

   fl26swiss.c without the game (FL26_RCAL_TEST, FL26_STATE_TEST). The pre-rounds and cups are
   GigaPack beta 3's (fl26world.txt lpre/ccup lines, the competition ids from its
   CompetitionRegulation.bin), plus a league cup pre-round, which is a regulation of its cup's
   own competition (mkeuropo.prerounds). ci_helper_lpre, the rule libq_skipph_handler applies to
   Competition Info's list and grid, must:
     - hide the four continental pre-round competitions (763 764 765 768);
     - still hide the modern CONMEBOL helpers (Sudamericana first stage 512, post-group play-off,
       Libertadores F1/F2);
     - never hide a real cup (513 514 515 516 517 518 519), the Libertadores (5), the Champions
       League (2), or a league cup whose pre-round is its own regulation;
     - leave a pre-round alone whose cup the world does not have (no record). */
#define FL26_RCAL_TEST
#define FL26_STATE_TEST
#include "fl26swiss.c"
#include <stdio.h>
#include <stdlib.h>

int rcal_test_today(void) { return 181; }
int rcal_test_invites(int k, uint16_t id) { (void)k; (void)id; return 0; }
int rcal_test_recday(uint16_t id) { (void)id; return -1; }
int rcal_test_dayload(int d) { (void)d; return 0; }
int rcal_test_round(uint16_t id) { (void)id; return -1; }
int state_test_date(void) { return 2027 * 365 + 181; }
uint32_t state_test_user(void) { return 0; }
const char* state_test_path(void) { return ""; }

static int fails = 0;
static void expect(int ok, const char* what, unsigned v)
{
  if (!ok) { printf("  FAIL  %s (%u)\n", what, v); fails++; }
}

/* GigaPack beta 3 regulation -> competition (CompetitionRegulation.bin +8 / +0x910) */
static const uint16_t RC[][2] = {
  { 614, 512 }, { 621, 516 }, { 622, 516 },          /* Sudamericana first stage, groups, knockout */
  { 615, 513 }, { 616, 513 }, { 705, 763 },          /* CAF Champions League and its pre-round */
  { 617, 514 }, { 618, 514 }, { 706, 764 },          /* CAF Confederation Cup */
  { 623, 517 }, { 707, 765 },                        /* CONCACAF Champions Cup */
  { 624, 518 }, { 703, 518 }, { 708, 768 },          /* OFC Champions League */
  { 619, 515 }, { 620, 515 }, { 625, 519 }, { 626, 519 },
  { 630, 540 }, { 632, 541 }, { 634, 542 },          /* post-group play-off, Libertadores F1/F2 */
  { 7, 5 }, { 8, 5 }, { 9, 5 }, { 2, 2 },
  { 900, 343 }, { 901, 343 },                        /* a league cup and its own pre-round */
  { 950, 777 },                                      /* a pre-round whose cup is not in the world */
};
static uint32_t test_comp(uint16_t reg)
{
  for (unsigned i = 0; i < sizeof RC / sizeof *RC; i++) if (RC[i][0] == reg) return RC[i][1];
  return CI_NO_COMP;
}

static void add_cup(uint16_t reg, uint16_t ko, uint16_t groups, int national, int suda)
{
  ccup_t* c = &g_ccup[g_nccup++];
  memset(c, 0, sizeof *c);
  c->reg = reg; c->ko = ko; c->groups = groups; c->national = (uint8_t)national;
  if (suda) { c->ereg[0] = 8; c->erank[0] = 255; c->n = 1; }   /* modern_suda_ccup: Libertadores losers */
}
static void add_pre(uint16_t reg, uint16_t ko, int single, int alias, int poko)
{
  lpre_t* l = &g_lpre[g_nlpre++];
  memset(l, 0, sizeof *l);
  l->reg = reg; l->ko = ko; l->ties = 1; l->single = (uint8_t)single;
  l->alias = (uint8_t)alias; l->poko = (uint8_t)poko;
}

int main(void)
{
  add_cup(621, 622, 8, 0, 1);         /* Sudamericana */
  add_cup(615, 616, 8, 0, 0);         /* CAF Champions League */
  add_cup(617, 618, 8, 0, 0);
  add_cup(0, 623, 0, 0, 0);           /* CONCACAF: a knockout only */
  add_cup(624, 703, 2, 0, 0);         /* OFC */
  add_cup(619, 620, 8, 0, 0);
  add_cup(625, 626, 8, 0, 0);
  add_cup(0, 900, 0, 1, 0);           /* a league cup */

  add_pre(614, 622, 1, 0, 0);         /* fl26world.txt lpre lines 711..718 */
  add_pre(705, 616, 1, 0, 0);
  add_pre(706, 618, 1, 0, 0);
  add_pre(707, 623, 1, 0, 0);
  add_pre(708, 703, 1, 0, 0);
  add_pre(630, 622, 0, 0, 1);
  add_pre(632, 0, 0, 1, 0);
  add_pre(634, 0, 0, 1, 0);
  add_pre(901, 900, 0, 0, 0);         /* the league cup's pre-round, in the cup's competition */
  add_pre(950, 960, 0, 0, 0);         /* its cup 960 has no record */

  g_cq_enabled = 1;
  g_cq.ko = 623;
  g_cq.pre = 707;
  expect(cq_ci_round_one(517, test_comp, 1, 22), "Round One belongs under the main CONCACAF cup", 517);
  expect(!cq_ci_round_one(765, test_comp, 1, 22), "Round One is not a separate helper cup", 765);
  expect(!cq_ci_round_one(5, test_comp, 1, 22), "Libertadores menu remains separate", 5);
  expect(!cq_ci_round_one(517, test_comp, 0, 22), "no current confirmed field hides the item", 517);
  expect(!cq_ci_round_one(517, test_comp, 1, 21), "no incomplete tie list", 517);
  g_cq_enabled = 0;

  const uint32_t hidden[] = { 763, 764, 765, 768, 512, 540, 541, 542 };
  for (unsigned i = 0; i < sizeof hidden / sizeof *hidden; i++)
    expect(ci_helper_lpre(hidden[i], test_comp) >= 0, "helper competition listed in Competition Info", hidden[i]);
  const uint32_t shown[] = { 513, 514, 515, 516, 517, 518, 519, 5, 2, 343, 777 };
  for (unsigned i = 0; i < sizeof shown / sizeof *shown; i++)
    expect(ci_helper_lpre(shown[i], test_comp) < 0, "real competition hidden from Competition Info", shown[i]);
  expect(ci_helper_lpre(CI_NO_COMP, test_comp) < 0, "a record without a competition hidden", 0);

  /* the pre-round found is the one of that competition: OFC's is 708, of cup 703 */
  int k = ci_helper_lpre(768, test_comp);
  expect(k >= 0 && g_lpre[k].reg == 708 && g_lpre[k].ko == 703, "OFC pre-round of competition 768", k >= 0 ? g_lpre[k].reg : 0);

  /* a world without the continental pre-rounds hides nothing of the cups */
  g_nlpre = 0;
  for (unsigned i = 0; i < sizeof shown / sizeof *shown; i++)
    expect(ci_helper_lpre(shown[i], test_comp) < 0, "no pre-rounds: competition hidden", shown[i]);

  if (fails) { printf("%d check(s) failed\n", fails); return 1; }
  printf("B470 Competition Info helpers: all checks passed\n");
  return 0;
}
