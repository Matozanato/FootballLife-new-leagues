/* B470 (FL Testovi 20.06.2028, save b470-s2-2006): Competition Info -> "Individual Titles" and
   "Team of the Competition" grey for the Champions League (final played), the CAF Champions
   League, the AFC Champions League Two and the OFC Champions League, on for the CONCACAF
   Champions Cup -- before the season roll.
   B470 again (beta4r, 18.11.2026, the same save): with the first gate the Champions League and
   the Europa League were on, but the Conference League, the CAF Champions League, the CAF
   Confederation Cup, the AFC Champions League Two, the AFC Challenge League and the OFC Champions
   League stayed grey. Their groups (replicas of a group stage) carry +0x84 = 1, the value a
   league carries, so they were still asked for an awards list.

     zig cc -O2 -fno-sanitize=undefined -w test_b470_awgate.c -o test_b470_awgate.exe && test_b470_awgate.exe

   (tools/test_b470_awgate.py builds and runs it.) Exit code 1 on any failure.

   The game's own code runs here: the bytes of 0x141590780 (the walk the menu asks, items 10 and
   11) and of 0x1414cfb90 ("no awards") are FL_2027.exe's (md5 69919abe..., the rig's and the
   clean game's), copied to their own RVAs in a fake image, so their rel32 calls land on stubs at
   the RVAs they call: 0x1414b6a60 (the owner), 0x1414fdbc0 (the exe's regulation row table, here
   the rows a full dump of the game holds: 2, 3, 4, 5, 6 and the replicas 1026.. / 1027 / 1029
   with +0x29 = 0, a league row with 1), 0x141590820 (the awards list, empty or not per
   regulation) and 0x1414bc860 (find a record). The records are GigaPack's
   (CompetitionRegulation.bin of _FL26Megapack), with +0x84 as the loader 0x1414f7e80 sets it
   from CompetitionKind (0x1414efb90): a master's kind from bits 11..13, a replica's from bits
   8..10, mapped 1->2 2->3 3->1 4->4 5->5 6->6, so

     file type 1 play-off   master 2, a tie 3
     file type 2 group      master 2, a group 1   (as a league)
     file type 3 knockout   master 3
     file type 4 league     master 1

   and +0x76 the master's id on a replica, 0xffff on a master.

   Without the patch the walk must answer as the game did on 20.06.2028 (UCL and CAF no, CONCACAF
   yes); with awgate_install every cup must answer yes, and a league must answer as before. */
#define FL26_RCAL_TEST
#define FL26_STATE_TEST
#include "fl26swiss.c"
#include <stdio.h>
#include <stdlib.h>

int rcal_test_today(void) { return 171; }
int rcal_test_invites(int k, uint16_t id) { (void)k; (void)id; return 0; }
int rcal_test_recday(uint16_t id) { (void)id; return -1; }
int rcal_test_dayload(int d) { (void)d; return 0; }
int rcal_test_round(uint16_t id) { (void)id; return -1; }
int state_test_date(void) { return 2028 * 365 + 171; }
uint32_t state_test_user(void) { return 0; }
const char* state_test_path(void) { return ""; }

static int fails = 0;
static void expect(int ok, const char* what)
{
  printf("  %s  %s\n", ok ? "ok  " : "FAIL", what);
  if (!ok) fails++;
}

/* FL_2027.exe 0x141590780..0x14159081c and 0x1414cfb90..0x1414cfbbf */
static const char WALK_HEX[] =
  "48895c2408488974241048897c241841564883ec204c8bf1e8c362f2ff33db488b7048399ef4bcd00076560f1f4400"
  "0081fb2c0100007209488dbe7cb7d000eb138bc3488dbe9c2ec1004869c8140300004803f9418b0639878000000075"
  "180fb70fe8a9f3f3ff84c0750c0fb70fe82d00000084c07422ffc33b9ef4bcd00072afb001488b5c2430488b742438"
  "488b7c24404883c420415ec332c0ebe6";
static const char NOAWARD_HEX[] =
  "4881ec38010000488d542420e81fe0020084c0741133c0384424490f94c04881c438010000c332c04881c438010000c3";
#define WALK_RVA   0x1590780
#define STATS_RVA  0x1590820
#define IMG_SIZE   0x1600000
#define BLK_REGS   0xc12e9c
#define BLK_COUNT  0xd0bcf4

static unsigned char* g_img;
static unsigned char* g_blk;
static unsigned char g_owner[0x60];

/* the file's regulation type, as the loader turns it into +0x84 */
enum { T_PLAYOFF = 1, T_GROUP = 2, T_KO = 3, T_LEAGUE = 4 };
static uint32_t kind_of(int type, int replica)
{
  static const uint32_t master[5] = { 0, 2, 2, 3, 1 }, rep[5] = { 0, 3, 1, 0, 0 };
  return replica ? rep[type] : master[type];
}

typedef struct { uint16_t id; uint32_t comp; uint32_t kind; int stats; } trec;
static trec R[512]; static int NR = 0;
static void put(uint16_t id, uint32_t comp, uint32_t kind, uint16_t parent, int stats)
{
  if (NR >= (int)(sizeof R / sizeof R[0])) { printf("  FAIL  too many records\n"); exit(1); }
  R[NR].id = id; R[NR].comp = comp; R[NR].kind = kind; R[NR].stats = stats;
  unsigned char* r = g_blk + BLK_REGS + (size_t)NR * 0x314;
  memset(r, 0, 0x314);
  *(uint16_t*)r = id; *(uint32_t*)(r + 0x80) = comp; *(uint32_t*)(r + 0x84) = kind;
  *(uint16_t*)(r + 0x76) = parent;
  NR++;
  *(uint32_t*)(g_blk + BLK_COUNT) = (uint32_t)NR;
}
/* a master and its n replicas (id + 1024 k), as the file has them */
static void phase(uint16_t id, uint32_t comp, int type, int n, int stats)
{
  put(id, comp, kind_of(type, 0), 0xffff, stats);
  for (int k = 1; k <= n; k++) put((uint16_t)(id + 1024 * k), comp, kind_of(type, 1), id, 0);
}
static void set_stats(uint16_t id, int s) { for (int i = 0; i < NR; i++) if (R[i].id == id) R[i].stats = s; }
static unsigned char* rec_at(uint16_t id)
{
  for (int i = 0; i < NR; i++) if (R[i].id == id) return g_blk + BLK_REGS + (size_t)i * 0x314;
  return 0;
}

static void* t_owner(void) { return g_owner; }
/* 1: find_rec answers NULL for every replica (the rdi path must carry);
   2: for every id -- no master is found, so the gate decides by the record's own kind alone,
      which is the first gate's rule (beta4r) */
static int g_findrec_off = 0;
static void* t_findrec(void* blk, uint64_t id)
{
  if (g_findrec_off == 2) return 0;
  if (g_findrec_off && (uint16_t)id >= 0x400) return 0;
  for (int i = 0; i < NR; i++)
    if (R[i].id == (uint16_t)id) return (unsigned char*)blk + BLK_REGS + (size_t)i * 0x314;
  return 0;
}
/* the exe's rows as the dump holds them: 2..6 with +0x29 = 0 and 2's / 3's / 5's replicas
   through the alias table; 17 (a league) with 1; nothing for 186.., 256.., 615.., 623, 900.. */
static uint8_t t_comprow(uint32_t id, unsigned char* row)
{
  uint16_t r = (uint16_t)id;
  int base = -1;
  if ((r >= 2 && r <= 6) || r == 17) base = r;
  for (int k = 1; k <= 8; k++) if (r == 2 + 1024 * k) base = 2;
  if (r == 1027) base = 3;
  if (r == 1029) base = 5;
  if (base < 0) return 0;
  memset(row, 0, 0x108);
  *(uint32_t*)row = (uint32_t)base;
  row[0x29] = base == 17;
  return 1;
}
static uint8_t t_stats(uint32_t id)
{
  for (int i = 0; i < NR; i++) if (R[i].id == (uint16_t)id) return (uint8_t)(R[i].stats != 0);
  return 0;
}

static void put_jmp(uint32_t rva, void* to)
{
  unsigned char* s = g_img + rva;
  s[0] = 0xFF; s[1] = 0x25; *(uint32_t*)(s + 2) = 0; *(uint64_t*)(s + 6) = (uint64_t)(uintptr_t)to;
}
static void put_hex(uint32_t rva, const char* hex)
{
  for (size_t i = 0; hex[2 * i]; i++) {
    unsigned v; sscanf(hex + 2 * i, "%2x", &v); g_img[rva + i] = (unsigned char)v;
  }
}
typedef uint8_t (*walk_fn)(const uint32_t* comp);
static int walk(uint32_t comp)
{
  return ((walk_fn)(uintptr_t)(g_img + WALK_RVA))(&comp) != 0;
}

/* GigaPack's competitions (ids of _FL26Megapack's Competition.bin) */
enum { C_UCL = 2, C_UEL = 3, C_UECL = 174, C_CAFCL = 513, C_CAFCC = 514, C_AFCCL2 = 515, C_SUDAM = 516,
       C_CONCACAF = 517, C_OFC = 518, C_AFCCHL = 519, C_CAFSC = 520, C_RECOPA = 521 };
static const struct { uint32_t comp; const char* name; } AW_CUPS[] = {
  { C_UCL, "UEFA Champions League" }, { C_UEL, "UEFA Europa League" }, { C_UECL, "UEFA Conference League" },
  { C_CAFCL, "CAF Champions League" }, { C_CAFCC, "CAF Confederation Cup" }, { C_AFCCL2, "AFC Champions League Two" },
  { C_SUDAM, "Copa Sudamericana" }, { C_CONCACAF, "CONCACAF Champions Cup" }, { C_OFC, "OFC Champions League" },
  { C_AFCCHL, "AFC Challenge League" }, { C_CAFSC, "CAF Super Cup" }, { C_RECOPA, "Recopa Sudamericana" } };
#define AW_NCUPS (int)(sizeof AW_CUPS / sizeof AW_CUPS[0])

int main(void)
{
  g_img = (unsigned char*)VirtualAlloc(0, IMG_SIZE, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
  g_blk = (unsigned char*)calloc(1, BLK_COUNT + 0x10);
  if (!g_img || !g_blk) { printf("  FAIL  no memory\n"); return 1; }
  memset(g_img, 0xCC, IMG_SIZE);
  *(void**)(g_owner + 0x48) = g_blk;
  put_hex(WALK_RVA, WALK_HEX);
  put_hex(NOAWARD_RVA, NOAWARD_HEX);
  put_jmp(OWNER_RVA, (void*)t_owner);
  put_jmp(FINDREC_RVA, (void*)t_findrec);
  put_jmp(COMPROW_RVA, (void*)t_comprow);
  put_jmp(STATS_RVA, (void*)t_stats);
  g_base = (uint64_t)(uintptr_t)g_img;

  /* the regulations of GigaPack's CompetitionRegulation.bin, every list empty unless said */
  phase(2, C_UCL, T_PLAYOFF, 8, 0); phase(3, C_UCL, T_GROUP, 1, 0); phase(4, C_UCL, T_KO, 0, 0);
  phase(256, C_UCL, T_PLAYOFF, 16, 0); phase(257, C_UCL, T_PLAYOFF, 16, 0); phase(258, C_UCL, T_PLAYOFF, 8, 0);
  phase(5, C_UEL, T_GROUP, 1, 0); phase(6, C_UEL, T_KO, 0, 0); phase(188, C_UEL, T_PLAYOFF, 8, 0);
  phase(259, C_UEL, T_PLAYOFF, 8, 0); phase(261, C_UEL, T_PLAYOFF, 16, 0);
  phase(186, C_UECL, T_GROUP, 1, 0); phase(187, C_UECL, T_KO, 0, 0); phase(189, C_UECL, T_PLAYOFF, 8, 0);
  phase(263, C_UECL, T_PLAYOFF, 31, 0); phase(264, C_UECL, T_PLAYOFF, 20, 0);
  phase(615, C_CAFCL, T_GROUP, 8, 0); phase(616, C_CAFCL, T_KO, 0, 0);
  phase(617, C_CAFCC, T_GROUP, 8, 0); phase(618, C_CAFCC, T_KO, 0, 0);
  phase(619, C_AFCCL2, T_GROUP, 8, 0); phase(620, C_AFCCL2, T_KO, 0, 0);
  phase(621, C_SUDAM, T_GROUP, 8, 0); phase(622, C_SUDAM, T_KO, 0, 0);
  phase(623, C_CONCACAF, T_KO, 0, 1);                       /* its list filled (on in the game) */
  phase(624, C_OFC, T_GROUP, 2, 0); phase(703, C_OFC, T_KO, 0, 0);
  phase(625, C_AFCCHL, T_GROUP, 8, 0); phase(626, C_AFCCHL, T_KO, 0, 0);
  phase(627, C_CAFSC, T_KO, 0, 0); phase(628, C_RECOPA, T_KO, 0, 0);
  /* a shipped league (row 17, +0x29 = 1), a league of ours with no row plus its split phase,
     and a league of ours played in two halves of the table (a replica with kind 0) */
  phase(17, 31, T_LEAGUE, 0, 0);
  phase(900, 343, T_LEAGUE, 0, 0); phase(901, 343, T_GROUP, 0, 0);
  phase(950, 344, T_LEAGUE, 1, 0);
  /* a league of ours whose master names itself (+0x76 0xffff) and a stray kind-1 replica whose
     master is a league: both still asked, as before */
  put(960, 345, 1, 0xffff, 0); put(960 + 1024, 345, 1, 960, 0);

  printf("the game's walk, unpatched (as on 20.06.2028):\n");
  expect(!walk(C_UCL), "Champions League grey (256 257 258 and ties have no row, empty lists)");
  expect(!walk(C_CAFCL), "CAF Champions League grey");
  expect(walk(C_CONCACAF), "CONCACAF Champions Cup on (623's list is filled)");
  expect(!walk(31), "a shipped league with an empty list grey");

  printf("the loader's kinds (CompetitionKind 0x1414efb90):\n");
  expect(kind_of(T_GROUP, 1) == REC_KIND_LEAGUE, "one group of a group stage carries a league's kind 1");
  expect(kind_of(T_PLAYOFF, 1) == 3 && kind_of(T_KO, 0) == 3, "a play-off tie and a knockout carry 3");
  expect(kind_of(T_GROUP, 0) == 2 && kind_of(T_PLAYOFF, 0) == 2, "a group stage and a play-off carry 2");

  printf("awgate_decide:\n");
  expect(awgate_decide(1, 0, 2, -1) == 1, "a row with +0x29 = 0: skipped (the game's)");
  expect(awgate_decide(1, 1, 1, -1) == 0, "a row with +0x29 = 1: checked (the game's)");
  expect(awgate_decide(1, 1, 4, -1) == 0, "a row with awards, a cup's: checked (the game's)");
  expect(awgate_decide(1, 0, 1, 2) == 1, "a group with the exe's alias row (1027): the row decides");
  expect(awgate_decide(0, 0, 2, -1) == 1, "no row, a play-off or group stage of ours: skipped");
  expect(awgate_decide(0, 0, 3, -1) == 1, "no row, a knockout or a play-off tie of ours: skipped");
  expect(awgate_decide(0, 0, 0, -1) == 1, "no row, kind 0 (a league's half): skipped, as before");
  expect(awgate_decide(0, 0, 1, 2) == 1, "no row, one group of our group stage (kind 1, master 2): skipped");
  expect(awgate_decide(0, 0, 1, -1) == 0, "no row, a league: checked (as before)");
  expect(awgate_decide(0, 0, 1, 1) == 0, "no row, kind 1 under a league master: checked (as before)");
  expect(awgate_decide(0, 0, -1, -1) == 0, "no record: checked (as before)");

  printf("awgate_install:\n");
  unsigned char* call = g_img + AWGATE_CALL;
  unsigned char keep[5]; memcpy(keep, call, 5);
  call[-1] ^= 0xff;
  expect(awgate_install(g_base) == 2 && !memcmp(call, keep, 5), "a different site: refused, nothing written");
  call[-1] ^= 0xff;
  call[1] ^= 1;
  expect(awgate_install(g_base) == 2, "a call to somewhere else: refused");
  call[1] ^= 1;
  expect(awgate_install(g_base) == 0, "the FL_2027.exe site: patched");
  expect(call[0] == 0xE8 && memcmp(call, keep, 5) != 0, "the call goes to our page now");
  {
    unsigned char* t = call + 5 + *(int32_t*)(call + 1);
    expect(t[0] == 0x48 && t[1] == 0x89 && t[2] == 0xfa && t[3] == 0xff && t[4] == 0x25,
           "the page hands the walk's record over (mov rdx, rdi; jmp)");
  }
  expect(awgate_install(g_base) == 2, "a second install: refused (already ours)");

  printf("the game's walk, patched -- every continental cup on:\n");
  char what[160];
  for (int i = 0; i < AW_NCUPS; i++) {
    snprintf(what, sizeof what, "%s (%u) on", AW_CUPS[i].name, (unsigned)AW_CUPS[i].comp);
    expect(walk(AW_CUPS[i].comp), what);
  }
  printf("the same with find_rec blind to replicas (the walk's own record carries the kind):\n");
  g_findrec_off = 1;
  for (int i = 0; i < AW_NCUPS; i++) {
    snprintf(what, sizeof what, "%s (%u) on", AW_CUPS[i].name, (unsigned)AW_CUPS[i].comp);
    expect(walk(AW_CUPS[i].comp), what);
  }
  g_findrec_off = 0;

  printf("the first gate's rule (no master known, kind 1 taken for a league) -- beta4r's result:\n");
  g_findrec_off = 2;
  expect(walk(C_UCL), "UEFA Champions League on (its groups 1027 have the exe's alias row)");
  expect(walk(C_UEL), "UEFA Europa League on (1029 likewise)");
  expect(walk(C_CONCACAF), "CONCACAF Champions Cup on (no group stage)");
  expect(walk(C_CAFSC), "CAF Super Cup on (no group stage)");
  expect(!walk(C_UECL), "UEFA Conference League grey (group 1210 asked)");
  expect(!walk(C_CAFCL), "CAF Champions League grey (groups 1639.. asked)");
  expect(!walk(C_CAFCC), "CAF Confederation Cup grey");
  expect(!walk(C_AFCCL2), "AFC Champions League Two grey");
  expect(!walk(C_OFC), "OFC Champions League grey");
  expect(!walk(C_AFCCHL), "AFC Challenge League grey");
  expect(!walk(C_SUDAM), "Copa Sudamericana grey too (not in the beta4r table)");
  g_findrec_off = 0;

  printf("leagues answer as before:\n");
  expect(!walk(31), "a shipped league with an empty list still grey (its row decides)");
  set_stats(17, 1);
  expect(walk(31), "the same league with its list filled on");
  expect(!walk(343), "a league of ours with no row and an empty list still grey");
  set_stats(900, 1);
  expect(walk(343), "the same league with its list filled on (its split phase 901 no longer asked)");
  expect(!walk(345), "a league of ours (+0x76 0xffff) with an empty list still grey");
  set_stats(960, 1);
  expect(!walk(345), "its kind-1 replica under a league master is still asked (empty -> grey)");
  set_stats(960 + 1024, 1);
  expect(walk(345), "... and on once that list is filled");
  (void)rec_at;

  printf("the log:\n");
  expect(strstr(g_log, "competition 2: regulation 256") != 0, "names the Champions League's regulation 256");
  expect(strstr(g_log, "competition 513: regulation 615 ") != 0, "names the CAF Champions League's 615");
  expect(strstr(g_log, "competition 513: regulation 1639 (a group of 615, kind 1 as a league's, its group stage kind 2)") != 0,
         "names the CAF Champions League's first group 1639 under 615");
  expect(strstr(g_log, "competition 174: regulation 1210 (a group of 186") != 0,
         "names the Conference League's group 1210 under 186");
  int once = 0; for (const char* p = g_log; (p = strstr(p, "competition 513: regulation")); p++) once++;
  expect(once == 2, "one line per competition and sort (a phase, a group)");

  printf(fails ? "FAILED: %d\n" : "all B470 awards gate checks passed\n", fails);
  return fails ? 1 : 0;
}
