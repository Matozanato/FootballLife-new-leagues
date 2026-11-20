/* zig cc -O2 -fno-sanitize=undefined test_chain_groups.c -o test_chain_groups.exe && test_chain_groups.exe
   GitHub #98: the group sets and the play-offs of fl26chain.c, run without the game. A fake image
   (VirtualAlloc'd, so the game functions fl26chain calls can be jmp stubs to the fakes below):
   the owner global, a block with the regulation records and a match table, club records with
   their slot byte and +0x628, the standings and INPUT calls, and a setter that writes the
   regulation's +0x170 list as the game's does. A season pass is played by hand (observe + the
   setter, as the hook sees it) between apply_pre and apply_post. Every check also counts every
   club of every league: nobody is lost and nobody is in two leagues. */
#include "fl26chain.c"
#include <stdlib.h>

static unsigned char* img;
static unsigned char* blk;
static unsigned char* clubs;              /* club record of team t at t * CLUB_SIZE */
#define CLUB_SIZE 0x700
#define MAX_TEAM  8192
#define MATCH_CAP  2000
static size_t BLK_SIZE;
static uint32_t mbase;                    /* the match table's offset in the block */

/* ---- the game's functions ---- */
static uint32_t st[4096][MAX_CLUBS]; static int nst[4096]; static int inpass[4096];
static void fake_stand(void* ctx, vec16_t* out, uint64_t id, uint64_t from)
{
  (void)ctx; (void)from;
  int n = nst[(uint16_t)id];
  if (!n || !inpass[(uint16_t)id]) return;
  unsigned char* b = calloc(n, 16);
  for (int i = 0; i < n; i++) *(uint32_t*)(b + 16 * i) = st[(uint16_t)id][i];
  out->b = b; out->e = b + 16 * n; out->c = out->e;
}
static unsigned char* fake_input(void* ctx, uint64_t id) { (void)ctx; return inpass[(uint16_t)id] ? (unsigned char*)img : 0; }
static unsigned char* fake_table(uint64_t id) { (void)id; return 0; }
static unsigned char* fake_club(unsigned char* b, uint64_t h)
{
  (void)b; uint32_t t = (uint32_t)h >> 14;
  return t && t < MAX_TEAM ? clubs + (size_t)t * CLUB_SIZE : 0;
}
static unsigned char* rec_of(uint16_t id)
{
  unsigned char* rec = blk + REG_ARRAY_OFF;
  for (int i = 0; i < REG_CAP; i++, rec += REG_STRIDE) if (*(uint16_t*)rec == id) return rec;
  return 0;
}
static int nwrites;
static char fake_set(uint64_t id, vec32_t* v, uint64_t flag)
{
  (void)flag;
  unsigned char* rec = rec_of((uint16_t)id);
  if (!rec) return 0;
  int n = vcount32(v);
  for (int i = 0; i < n; i++) *(uint32_t*)(rec + 0x170 + 4 * i) = v->b[i];
  *(uint32_t*)(rec + 0x170 + 4 * n) = 0xffffffffu;
  nwrites++;
  return 1;
}
static void stub(uint32_t rva, void* fn)
{
  unsigned char* p = img + rva;
  p[0] = 0xff; p[1] = 0x25; *(uint32_t*)(p + 2) = 0; *(uint64_t*)(p + 6) = (uint64_t)(uintptr_t)fn;
}

/* ---- the world ---- */
static int nreg;
static void league(uint16_t id, int first_team, int n, int slot)
{
  unsigned char* rec = blk + REG_ARRAY_OFF + (size_t)nreg++ * REG_STRIDE;
  *(uint16_t*)rec = id;
  for (int i = 0; i < n; i++) {
    uint32_t h = (uint32_t)(first_team + i) << 14;
    *(uint32_t*)(rec + 0x170 + 4 * i) = h;
    st[id][i] = h;                                    /* the final table: the list's order */
    unsigned char* c = clubs + (size_t)(first_team + i) * CLUB_SIZE;
    *(uint32_t*)(c + OFF_SLOT) = (uint32_t)slot;
    *(uint32_t*)(c + OFF_PARENT) = 0xffffffffu;
  }
  *(uint32_t*)(rec + 0x170 + 4 * n) = 0xffffffffu;
  nst[id] = n; inpass[id] = 1;
}
static int list_of(uint16_t id, uint32_t* out) { return reg_list(id, out); }
static int team_at(uint16_t id, int pos) { return st[id][pos - 1] >> 14; }   /* 1-based table place */
static int holds(uint16_t id, int team)
{
  uint32_t l[MAX_CLUBS]; int n = list_of(id, l);
  for (int i = 0; i < n; i++) if ((l[i] >> 14) == (uint32_t)team) return 1;
  return 0;
}
static int slot_of(int team) { return *(uint32_t*)(clubs + (size_t)team * CLUB_SIZE + OFF_SLOT) & 0x7f; }

static void reset(void)
{
  memset(blk, 0, BLK_SIZE);
  for (int s = 0; s < REG_CAP; s++) *(uint16_t*)(blk + REG_ARRAY_OFF + (size_t)s * REG_STRIDE) = 0xffff;
  for (uint32_t i = 0; i < MATCH_CAP; i++) *(uint16_t*)(blk + mbase + (size_t)i * MATCH_STRIDE) = 0xffff;
  memset(nst, 0, sizeof nst); memset(inpass, 0, sizeof inpass);
  memset(clubs, 0, (size_t)MAX_TEAM * CLUB_SIZE);
  nreg = 0; nwrites = 0; g_nchain = 0; g_ncup = g_nscup = 0;
  fl26_chain_gsets(0, 0); fl26_chain_playoffs(0, 0); fl26_chain_ghomes(0, 0);
  g_log_len = 0;
}

static int nmatch;
static void match(uint16_t ko, int home, int away, int gh, int ga, int ph, int pa)
{
  unsigned char* m = blk + mbase + (size_t)nmatch++ * MATCH_STRIDE;
  memset(m, 0, MATCH_STRIDE);
  *(uint16_t*)m = 1; m[7] = 0x40; *(uint16_t*)(m + 4) = ko;
  *(uint32_t*)(m + 0x14) = (uint32_t)home << 14; *(uint32_t*)(m + 0x18) = (uint32_t)away << 14;
  m[0x1c] = (unsigned char)gh; m[0x1f] = (unsigned char)ga; m[0x1e] = (unsigned char)ph; m[0x21] = (unsigned char)pa;
}

/* the pass as the hook sees it: observe, then the game's setter */
static void pass_write(uint16_t id, uint32_t* l, int n)
{
  vec32_t v = { l, l + n, l + MAX_CLUBS };
  if (!observe(id, &v, 1)) fake_set(id, &v, 1);
}

static int fails;
static void check(const char* what, int ok)
{
  if (!ok) { printf("FAIL: %s\n", what); fails++; }
  else printf("ok: %s\n", what);
}
/* every club of the world in exactly one league, and as many clubs as at the start */
static int census(int want)
{
  static int seen[MAX_TEAM]; memset(seen, 0, sizeof seen);
  int total = 0;
  for (int r = 0; r < nreg; r++) {
    unsigned char* rec = blk + REG_ARRAY_OFF + (size_t)r * REG_STRIDE;
    for (int i = 0; i < MAX_CLUBS && *(uint32_t*)(rec + 0x170 + 4 * i) != 0xffffffffu; i++) {
      uint32_t t = *(uint32_t*)(rec + 0x170 + 4 * i) >> 14;
      if (seen[t]++) { printf("  team %u in two leagues\n", t); return 0; }
      total++;
    }
  }
  if (total != want) printf("  %d clubs, not %d\n", total, want);
  return total == want;
}
static int size_is(uint16_t id, int n) { uint32_t l[MAX_CLUBS]; return list_of(id, l) == n; }
static void dump_log(void) { printf("%.*s", g_log_len, g_log); g_log_len = 0; }

/* the game's one linked pair: the upper's last `down` swap with the lower's first `up` */
static void game_moves(uint16_t upper, uint16_t lower, int down, int up)
{
  uint32_t a[MAX_CLUBS], b[MAX_CLUBS], na[MAX_CLUBS], nb[MAX_CLUBS];
  int n = list_of(upper, a), m = list_of(lower, b), k = 0, j = 0;
  for (int i = 0; i < n - down; i++) na[k++] = st[upper][i];
  for (int i = 0; i < up; i++) na[k++] = st[lower][i];
  for (int i = up; i < m; i++) nb[j++] = st[lower][i];
  for (int i = n - down; i < n; i++) nb[j++] = st[upper][i];
  (void)a; (void)b;
  pass_write(upper, na, k); pass_write(lower, nb, j);
}

/* 16.11.2026: the game's date where fl26chain's pass_date reads it (day of the year from 0, year) */
static void set_date(int day, int year)
{
  *(uint16_t*)(blk + lay_today()) = (uint16_t)day; *(uint16_t*)(blk + lay_today() + 8) = (uint16_t)year;
}
/* a table that is not the list's order: st[id] turned left by k (the list's first k at the bottom) */
static void rotate(uint16_t id, int k)
{
  int n = nst[id]; uint32_t t[MAX_CLUBS];
  for (int i = 0; i < n; i++) t[i] = st[id][(i + k) % n];
  memcpy(st[id], t, sizeof(uint32_t) * n);
}
/* a league's list (team numbers) and its clubs' slots as an old save left them */
static void set_list(uint16_t id, const int* teams, int n, int slot)
{
  unsigned char* rec = rec_of(id);
  for (int i = 0; i < n; i++) {
    *(uint32_t*)(rec + 0x170 + 4 * i) = (uint32_t)teams[i] << 14;
    *(uint32_t*)(clubs + (size_t)teams[i] * CLUB_SIZE + OFF_SLOT) = (uint32_t)slot;
  }
  *(uint32_t*)(rec + 0x170 + 4 * n) = 0xffffffffu;
}
/* every league's list and every club's slot byte, before a pass, to compare after it */
static uint32_t snap_l[64][MAX_CLUBS + 1]; static uint32_t snap_slot[MAX_TEAM];
static void snap_lists(void)
{
  for (int r = 0; r < nreg && r < 64; r++) memcpy(snap_l[r], blk + REG_ARRAY_OFF + (size_t)r * REG_STRIDE + 0x170, sizeof snap_l[r]);
  for (int t = 0; t < MAX_TEAM; t++) snap_slot[t] = *(uint32_t*)(clubs + (size_t)t * CLUB_SIZE + OFF_SLOT);
}
static int lists_same(void)
{
  for (int r = 0; r < nreg && r < 64; r++)
    if (memcmp(snap_l[r], blk + REG_ARRAY_OFF + (size_t)r * REG_STRIDE + 0x170, sizeof snap_l[r])) return 0;
  for (int t = 0; t < MAX_TEAM; t++) if (snap_slot[t] != *(uint32_t*)(clubs + (size_t)t * CLUB_SIZE + OFF_SLOT)) return 0;
  return 1;
}
static int log_has(const char* s)
{
  g_log[g_log_len < (int)sizeof g_log ? g_log_len : (int)sizeof g_log - 1] = 0;
  return strstr(g_log, s) != 0;
}

int main(void)
{
  img = VirtualAlloc(0, OWNER_RVA + 0x1000, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
  unsigned char* owner = calloc(1, 0x100);
  mbase = (uint32_t)((REG_ARRAY_OFF + 1200u * REG_STRIDE + 0xfff) & ~0xfffu);
  BLK_SIZE = mbase + (size_t)MATCH_CAP * MATCH_STRIDE;
  blk = calloc(1, BLK_SIZE);
  clubs = calloc(MAX_TEAM, CLUB_SIZE);
  if (!img || !blk || !clubs) { printf("FAIL: no memory\n"); return 1; }
  *(unsigned char**)(img + OWNER_RVA) = owner; *(unsigned char**)(owner + 0x48) = blk;
  g_base = (uint64_t)(uintptr_t)img;
  *(uint32_t*)(img + NOPARENT_RVA) = 0xffffffffu;
  stub(STAND_RVA, (void*)fake_stand); stub(INPUT_RVA, (void*)fake_input);
  stub(TABLE_RVA, (void*)fake_table); stub(CLUB_RVA, (void*)fake_club);
  g_tramp_set = (unsigned char*)(uintptr_t)fake_set;
  /* the match table where apclau_table and match_table look for it (block + base, cap records) */
  unsigned char* bs = img + MATCH_BASE_SITE, * cs = img + MATCH_CAP_SITE;
  bs[0] = 0x48; bs[1] = 0x8d; bs[2] = 0x88; *(uint32_t*)(bs + 3) = mbase;
  cs[0] = 0x81; cs[1] = 0xff; *(uint32_t*)(cs + 2) = MATCH_CAP;
  printf("regulations at +%x, %d of them; matches at +%x\n", REG_ARRAY_OFF, REG_CAP, mbase);

  /* ---- 1. three Serie C groups under Serie B (82): 3 down, a winner of each group up ---- */
  {
    reset(); nmatch = 0;
    league(81, 1, 20, 1);  league(82, 101, 20, 2);
    league(1001, 201, 20, 3); league(1002, 301, 20, 4); league(1003, 401, 20, 5);
    uint16_t gs[] = { 1, 3,  82, 3,  1001, 1, 0,  1002, 1, 0,  1003, 1, 0 };
    check("1: one set taken", fl26_chain_gsets(gs, sizeof gs / 2) == 1);
    apply_pre(img);
    /* the pass: Serie A (81) and 82 swap three, then the linked pair 82 <-> 1001 as the game moves it */
    game_moves(81, 82, 3, 3);
    uint32_t b[MAX_CLUBS]; int nb = list_of(82, b);
    /* st[82] is 82's final table; the game moves 82's bottom three and 1001's top three */
    { uint32_t l1[MAX_CLUBS], nb2[MAX_CLUBS], nl[MAX_CLUBS]; int n1 = list_of(1001, l1), k = 0, j = 0;
      for (int i = 0; i < nb; i++) { int bottom = 0; for (int q = 17; q < 20; q++) bottom |= b[i] == st[82][q]; if (!bottom) nb2[k++] = b[i]; }
      for (int i = 0; i < 3; i++) nb2[k++] = st[1001][i];
      for (int i = 3; i < n1; i++) nl[j++] = l1[i];
      for (int q = 17; q < 20; q++) nl[j++] = st[82][q];
      pass_write(82, nb2, k); pass_write(1001, nl, j); }
    apply_post(img);
    dump_log();
    check("1: every club once, 100 in all", census(100));
    check("1: all leagues keep 20", size_is(81, 20) && size_is(82, 20) && size_is(1001, 20) && size_is(1002, 20) && size_is(1003, 20));
    check("1: the three group winners in 82", holds(82, team_at(1001, 1)) && holds(82, team_at(1002, 1)) && holds(82, team_at(1003, 1)));
    check("1: 1001's 2nd and 3rd stay in 1001", holds(1001, team_at(1001, 2)) && holds(1001, team_at(1001, 3)));
    check("1: 82's last three one to each group",
          holds(1001, team_at(82, 18)) + holds(1002, team_at(82, 18)) + holds(1003, team_at(82, 18)) == 1 &&
          (holds(1001, team_at(82, 18)) + holds(1001, team_at(82, 19)) + holds(1001, team_at(82, 20))) == 1 &&
          (holds(1002, team_at(82, 18)) + holds(1002, team_at(82, 19)) + holds(1002, team_at(82, 20))) == 1);
    check("1: 81's relegated stay in 82, 82's promoted stay in 81", holds(82, team_at(81, 18)) && holds(81, team_at(82, 1)));
    check("1: slots follow the leagues", slot_of(team_at(1002, 1)) == 2 && slot_of(team_at(82, 20)) >= 3 && slot_of(team_at(1001, 1)) == 2);
    /* the same season's step again (a second pass with the same final tables): nothing changes.
       16.11.2026: once without the game writing 82 (the pass after 1 July in the game: the set is
       not at its season's end there), once with the game writing 82's list as it stands */
    int w0 = nwrites;
    apply_pre(img); apply_post(img);
#ifdef GROUP_DIAG_ONLY
    check("1: a second step with the same tables writes nothing", nwrites == w0 && census(100) && strstr(g_log, "already holds"));
#else
    check("1: a second step the game writes none of the set in: nothing written, 'untouched'",
          nwrites == w0 && census(100) && log_has("not its season's end, untouched") && !log_has("already holds"));
#endif
    dump_log();
    apply_pre(img);
    { uint32_t l[MAX_CLUBS]; int n = list_of(82, l); pass_write(82, l, n); }
    w0 = nwrites;
    apply_post(img);
    check("1: a second step the game writes 82 in: nothing written, 'already holds'", nwrites == w0 && census(100) && log_has("already holds"));
    dump_log();
  }

  /* ---- 2. a refusal: 82 sends 4 but the groups only 3 -> nothing moves, the log says why ---- */
  {
    reset(); nmatch = 0;
    league(82, 101, 20, 2); league(1001, 201, 20, 3); league(1002, 301, 20, 4); league(1003, 401, 20, 5);
    uint16_t gs[] = { 1, 3,  82, 4,  1001, 1, 0,  1002, 1, 0,  1003, 1, 0 };
    fl26_chain_gsets(gs, sizeof gs / 2);
    apply_pre(img);
    { uint32_t l[MAX_CLUBS]; int n = list_of(82, l); pass_write(82, l, n); }   /* its season's end */
    int w0 = nwrites;
    apply_post(img);
    check("2: counts that do not add up move nothing", nwrites == w0 && census(80) && holds(82, team_at(82, 20)));
    check("2: and the log says so", strstr(g_log, "4 go down, 3 go up") != 0);
    dump_log();
  }

  /* ---- 3. a club of a group in no league's list: nothing moves ---- */
  {
    reset(); nmatch = 0;
    league(82, 101, 20, 2); league(1001, 201, 20, 3); league(1002, 301, 20, 4);
    st[1002][0] = 999u << 14;                      /* 1002's winner is in no list (and may go up) */
    *(uint32_t*)(clubs + 999u * CLUB_SIZE + OFF_PARENT) = 0xffffffffu;
    uint16_t gs[] = { 1, 2,  82, 2,  1001, 1, 0,  1002, 1, 0 };
    fl26_chain_gsets(gs, sizeof gs / 2);
    apply_pre(img);
    { uint32_t l[MAX_CLUBS]; int n = list_of(82, l); pass_write(82, l, n); }   /* its season's end */
    int w0 = nwrites;
    apply_post(img);
    check("3: a winner in no league moves nothing", nwrites == w0 && census(60));
    check("3: and the log names it", strstr(g_log, "in none of the set's leagues") != 0);
    dump_log();
  }

  /* ---- 4. many to many: nine Serie D groups under the three of Serie C, two sets ---- */
  {
    reset(); nmatch = 0;
    league(82, 101, 20, 2);
    league(1001, 201, 20, 3); league(1002, 301, 20, 4); league(1003, 401, 20, 5);
    for (int g = 0; g < 9; g++) league((uint16_t)(1101 + g), 1001 + 100 * g, 18, 10 + g);
    /* a relegated club of 1002 was built into 1105: it goes back there */
    /* and 82's 18th has a home in each set (08.11.2026, the TFF 2. Lig and 3. Lig groups): 1003 and 1107 */
    uint32_t homes[] = { (uint32_t)team_at(1002, 18), 1105,  (uint32_t)team_at(82, 18), 1107,  (uint32_t)team_at(82, 18), 1003 };
    fl26_chain_ghomes(homes, 3);
    uint16_t gs[] = { 1, 3,  82, 3,  1001, 1, 0,  1002, 1, 0,  1003, 1, 0,
                      3, 9,  1001, 3,  1002, 3,  1003, 3,
                             1101, 1, 0,  1102, 1, 0,  1103, 1, 0,
                             1104, 1, 1,  1105, 1, 1,  1106, 1, 1,
                             1107, 1, 2,  1108, 1, 2,  1109, 1, 2 };
    check("4: two sets taken", fl26_chain_gsets(gs, sizeof gs / 2) == 2);
    apply_pre(img);
    /* the game moved only the two linked pairs, 82 <-> 1001 and 1001 <-> 1101 (3 each way) */
    game_moves(82, 1001, 3, 3);
    apply_post(img);
    dump_log();
    int total = 20 + 60 + 9 * 18;
    check("4: every club once", census(total));
    int sizes = size_is(82, 20) && size_is(1001, 20) && size_is(1002, 20) && size_is(1003, 20);
    for (int g = 0; g < 9; g++) sizes &= size_is((uint16_t)(1101 + g), 18);
    check("4: every league keeps its size", sizes);
    check("4: each C group gets the winners of its own D groups",
          holds(1001, team_at(1101, 1)) && holds(1001, team_at(1102, 1)) && holds(1001, team_at(1103, 1)) &&
          holds(1002, team_at(1104, 1)) && holds(1002, team_at(1105, 1)) && holds(1002, team_at(1106, 1)) &&
          holds(1003, team_at(1107, 1)) && holds(1003, team_at(1108, 1)) && holds(1003, team_at(1109, 1)));
    check("4: the C winners in 82, 82's last three in C", holds(82, team_at(1001, 1)) && holds(82, team_at(1002, 1)) &&
          holds(82, team_at(1003, 1)) && !holds(82, team_at(82, 18)) && !holds(82, team_at(82, 20)));
    check("4: 1002's 18th goes home to 1105", holds(1105, team_at(1002, 18)));
    check("4: 82's 18th goes to its home of this set, 1003 (its 1107 home is the set below)", holds(1003, team_at(82, 18)));
    int each = 1;
    for (int g = 0; g < 9; g++) {
      int got = 0;
      for (int u = 0; u < 3; u++) for (int p = 18; p <= 20; p++) got += holds((uint16_t)(1101 + g), team_at((uint16_t)(1001 + u), p));
      each &= got == 1;
    }
    check("4: each D group one relegated club", each);
    check("4: 82's relegated stay in Serie C (not sent on to D)", holds(1001, team_at(82, 18)) + holds(1002, team_at(82, 18)) + holds(1003, team_at(82, 18)) == 1);
  }

  /* ---- 5. group winners' play-off for one place: 1002's winner beats 1001's ---- */
  {
    reset(); nmatch = 0;
    league(82, 101, 20, 2); league(1001, 201, 20, 3); league(1002, 301, 20, 4);
    uint16_t gs[] = { 1, 2,  82, 1,  1001, 1, 0,  1002, 0, 0 };
    fl26_chain_gsets(gs, sizeof gs / 2);
    uint16_t po[] = { 900, 82, 1002, 1001, 1, 2,  1001, 1,  1002, 1 };
    check("5: play-off taken", fl26_chain_playoffs(po, sizeof po / 2) == 1);
    match(900, team_at(1001, 1), team_at(1002, 1), 1, 1, 0, 0);
    match(900, team_at(1002, 1), team_at(1001, 1), 2, 0, 0, 0);
    apply_pre(img);
    { uint32_t l[MAX_CLUBS]; int n = list_of(82, l); pass_write(82, l, n); }   /* its season's end */
    apply_post(img);
    dump_log();
    check("5: every club once", census(60));
    check("5: the winner (1002's 1st) in 82, 1001's 1st stays", holds(82, team_at(1002, 1)) && holds(1001, team_at(1001, 1)));
    check("5: sizes kept", size_is(82, 20) && size_is(1001, 20) && size_is(1002, 20));
    check("5: 82's last to 1002 (the group that sent a club)", holds(1002, team_at(82, 20)));
  }

  /* ---- 6. a place play-off on a plain chain: 3rd to 6th for the third place ---- */
  {
    reset(); nmatch = 0;
    league(2001, 101, 24, 2); league(2002, 201, 24, 3);
    g_nchain = 1; memset(&g_chain[0], 0, sizeof g_chain[0]);
    g_chain[0].cfg.mid = 2001; g_chain[0].cfg.low = 2002; g_chain[0].cfg.demote_mid = 3; g_chain[0].cfg.promote_low = 3;
    uint16_t po[] = { 901, 2001, 2002, 2002, 3, 4,  2002, 3,  2002, 4,  2002, 5,  2002, 6 };
    fl26_chain_playoffs(po, sizeof po / 2);
    int t3 = team_at(2002, 3), t4 = team_at(2002, 4), t5 = team_at(2002, 5), t6 = team_at(2002, 6);
    match(901, t6, t3, 1, 0, 0, 0); match(901, t3, t6, 3, 0, 0, 0);     /* 3rd through, 4-1 */
    match(901, t5, t4, 0, 0, 0, 0); match(901, t4, t5, 1, 1, 3, 4);     /* 5th through on penalties */
    match(901, t3, t5, 0, 1, 0, 0);                                     /* the final: the 5th */
    apply_pre(img);
    uint32_t a[MAX_CLUBS], b[MAX_CLUBS]; int na = list_of(2001, a), nb = list_of(2002, b);
    pass_write(2001, a, na); pass_write(2002, b, nb);                    /* the pass writes both as they were */
    apply_post(img);
    dump_log();
    check("6: every club once", census(48));
    check("6: the 5th up, the 3rd stays down", holds(2001, t5) && holds(2002, t3) && holds(2001, team_at(2002, 1)));
    check("6: sizes kept", size_is(2001, 24) && size_is(2002, 24));
    check("6: slots swapped", slot_of(t5) == 2 && slot_of(t3) == 3);
  }

  /* ---- 7. a tie: the upper's 16th beats the lower's 3rd and stays up ---- */
  {
    reset(); nmatch = 0;
    league(2001, 101, 18, 2); league(2002, 201, 18, 3);
    g_nchain = 1; memset(&g_chain[0], 0, sizeof g_chain[0]);
    g_chain[0].cfg.mid = 2001; g_chain[0].cfg.low = 2002; g_chain[0].cfg.demote_mid = 3; g_chain[0].cfg.promote_low = 3;
    uint16_t po[] = { 902, 2001, 2002, 0, 0, 2,  2001, 16,  2002, 3 };
    fl26_chain_playoffs(po, sizeof po / 2);
    int u16 = team_at(2001, 16), l3 = team_at(2002, 3);
    match(902, l3, u16, 0, 0, 0, 0); match(902, u16, l3, 2, 1, 0, 0);
    apply_pre(img);
    uint32_t a[MAX_CLUBS], b[MAX_CLUBS]; int na = list_of(2001, a), nb = list_of(2002, b);
    pass_write(2001, a, na); pass_write(2002, b, nb);
    apply_post(img);
    dump_log();
    check("7: every club once", census(36));
    check("7: the 16th stays up, the 3rd stays down, the 17th goes down", holds(2001, u16) && holds(2002, l3) && holds(2002, team_at(2001, 17)));
  }

  /* ---- 8. a play-off not decided (a level tie, no penalties) leaves the counts ---- */
  {
    reset(); nmatch = 0;
    league(2001, 101, 18, 2); league(2002, 201, 18, 3);
    g_nchain = 1; memset(&g_chain[0], 0, sizeof g_chain[0]);
    g_chain[0].cfg.mid = 2001; g_chain[0].cfg.low = 2002; g_chain[0].cfg.demote_mid = 3; g_chain[0].cfg.promote_low = 3;
    uint16_t po[] = { 902, 2001, 2002, 0, 0, 2,  2001, 16,  2002, 3 };
    fl26_chain_playoffs(po, sizeof po / 2);
    int u16 = team_at(2001, 16), l3 = team_at(2002, 3);
    match(902, l3, u16, 1, 1, 0, 0);
    apply_pre(img);
    uint32_t a[MAX_CLUBS], b[MAX_CLUBS]; int na = list_of(2001, a), nb = list_of(2002, b);
    pass_write(2001, a, na); pass_write(2002, b, nb);
    apply_post(img);
    check("8: a level tie: the counts stand", holds(2002, u16) && holds(2001, l3) && census(36));
    check("8: and the log says why", strstr(g_log, "level") != 0);
    dump_log();
  }

  /* ---- 9. poff_decide: an unfinished bracket, a club in two ties lost, stale matches ---- */
  {
    reset(); nmatch = 0;
    uint32_t e[4] = { 1u << 14, 2u << 14, 3u << 14, 4u << 14 }; char why[160];
    match(903, 1, 2, 2, 0, 0, 0);
    check("9: one tie of three: no winner", poff_decide(blk + mbase, MATCH_CAP, 903, e, 4, why, sizeof why) == 0 && strstr(why, "1 of its 3"));
    match(903, 3, 4, 0, 1, 0, 0); match(903, 1, 4, 1, 0, 0, 0);
    check("9: all three played: 1 wins", poff_decide(blk + mbase, MATCH_CAP, 903, e, 4, why, sizeof why) == e[0]);
    match(903, 9, 1, 1, 0, 0, 0);
    check("9: a match with a club not in it: no winner", poff_decide(blk + mbase, MATCH_CAP, 903, e, 4, why, sizeof why) == 0);
  }

  /* ---- 10. group_plan alone: a club in two leagues' standings is refused ---- */
  {
    static gl_t a, b; memset(&a, 0, sizeof a); memset(&b, 0, sizeof b);
    a.id = 1; b.id = 2;
    for (int i = 0; i < 10; i++) { a.stand[i] = a.list[i] = (uint32_t)(10 + i) << 14; b.stand[i] = b.list[i] = (uint32_t)(30 + i) << 14; }
    a.nstand = a.nlist = b.nstand = b.nlist = 10;
    b.stand[5] = a.stand[2];
    gl_t* m[2] = { &a, &b }; int n[2] = { 1, 1 }, pref[2] = { -1, 0 }, nout[2], flips = 0; char why[200];
    static uint32_t out[2][MAX_CLUBS];
    check("10: a club in two tables is refused", group_plan(m, n, pref, 1, 1, 0, 0, 0, 0, 0, 0, 0, out, nout, &flips, 0, 0, 0, why, sizeof why) == -1 && strstr(why, "standings of"));
    b.stand[5] = b.list[5];
    check("10: else it moves one each way", group_plan(m, n, pref, 1, 1, 0, 0, 0, 0, 0, 0, 0, out, nout, &flips, 0, 0, 0, why, sizeof why) == 0 && nout[0] == 10 && nout[1] == 10);
  }

  /* ---- 11. a group with a plain chain below it: 82 over 1001/1002, 1002 over 3001 (fl26chain's
     chain, as a tier 3 under a tier 2 of ours): the chain's clubs stay where the chain put them ---- */
  {
    reset(); nmatch = 0;
    league(82, 101, 20, 2); league(1001, 201, 20, 3); league(1002, 301, 20, 4); league(3001, 401, 20, 5);
    uint16_t gs[] = { 1, 2,  82, 2,  1001, 1, 0,  1002, 1, 0 };
    fl26_chain_gsets(gs, sizeof gs / 2);
    g_nchain = 1; memset(&g_chain[0], 0, sizeof g_chain[0]);
    g_chain[0].cfg.mid = 1002; g_chain[0].cfg.low = 3001; g_chain[0].cfg.demote_mid = 2; g_chain[0].cfg.promote_low = 2;
    apply_pre(img);
    uint16_t ids[] = { 82, 1001, 1002, 3001 };
    for (int k = 0; k < 4; k++) { uint32_t l[MAX_CLUBS]; int n = list_of(ids[k], l); pass_write(ids[k], l, n); }
    apply_post(img);
    dump_log();
    check("11: every club once", census(80));
    check("11: sizes kept", size_is(82, 20) && size_is(1001, 20) && size_is(1002, 20) && size_is(3001, 20));
    check("11: both group winners in 82, 82's last two in the groups",
          holds(82, team_at(1001, 1)) && holds(82, team_at(1002, 1)) &&
          !holds(82, team_at(82, 19)) && !holds(82, team_at(82, 20)));
    check("11: 1002's last two in 3001, 3001's first two in 1002",
          holds(3001, team_at(1002, 19)) && holds(3001, team_at(1002, 20)) &&
          holds(1002, team_at(3001, 1)) && holds(1002, team_at(3001, 2)));
  }

  /* ---- 12. B418: one club with another league's slot does not make it its league's ----
     Case 1 again, but the first club of 1001 and of 1002 carries Serie B's slot (2), as a club
     the game's own mover took for promoted does after a pass. The league's slot was read from
     its first club: all of 1001 and 1002 then got slot 2. Now it is the slot most of its clubs
     carry, and with the world file's slots (fl26_chain_gslots) the league's own even when most
     of its clubs carry another (11 of 1003's 20). */
  for (int given = 0; given < 2; given++) {
    reset(); nmatch = 0;
    league(81, 1, 20, 1);  league(82, 101, 20, 2);
    league(1001, 201, 20, 3); league(1002, 301, 20, 4); league(1003, 401, 20, 5);
    *(uint32_t*)(clubs + (size_t)201 * CLUB_SIZE + OFF_SLOT) = 2;
    *(uint32_t*)(clubs + (size_t)301 * CLUB_SIZE + OFF_SLOT) = 2;
    if (given) for (int t = 401; t < 412; t++) *(uint32_t*)(clubs + (size_t)t * CLUB_SIZE + OFF_SLOT) = 2;
    uint16_t gs[] = { 1, 3,  82, 3,  1001, 1, 0,  1002, 1, 0,  1003, 1, 0 };
    uint16_t sl[] = { 82, 2,  1001, 3,  1002, 4,  1003, 5,  7777, 9 };
    check("12: one set taken", fl26_chain_gsets(gs, sizeof gs / 2) == 1);
    if (given) check("12: the world's slots taken for the set's four leagues", fl26_chain_gslots(sl, 5) == 4);
    apply_pre(img);
    game_moves(81, 82, 3, 3);
    uint32_t b[MAX_CLUBS]; int nb = list_of(82, b);
    { uint32_t l1[MAX_CLUBS], nb2[MAX_CLUBS], nl2[MAX_CLUBS]; int n1 = list_of(1001, l1), k = 0, j = 0;
      for (int i = 0; i < nb; i++) { int bottom = 0; for (int q = 17; q < 20; q++) bottom |= b[i] == st[82][q]; if (!bottom) nb2[k++] = b[i]; }
      for (int i = 0; i < 3; i++) nb2[k++] = st[1001][i];
      for (int i = 3; i < n1; i++) nl2[j++] = l1[i];
      for (int q = 17; q < 20; q++) nl2[j++] = st[82][q];
      pass_write(82, nb2, k); pass_write(1001, nl2, j); }
    apply_post(img);
    dump_log();
    int bad = 0;
    static const uint16_t L[4][2] = { { 82, 2 }, { 1001, 3 }, { 1002, 4 }, { 1003, 5 } };
    for (int q = 0; q < (given ? 4 : 3); q++) {
      uint32_t l[MAX_CLUBS]; int n = list_of(L[q][0], l);
      for (int i = 0; i < n; i++) if (slot_of((int)(l[i] >> 14)) != L[q][1]) bad++;
    }
    check(given ? "12: with the world's slots every club of the four leagues has its league's slot"
                : "12: without them every club of 82, 1001 and 1002 has its league's slot (most of its clubs')", bad == 0);
    check("12: every club once, 100 in all", census(100));
  }

  /* ---- 13. 16.11.2026: a group below one set and above another (the TFF 2. Lig groups: under the
     1. Lig, over the 3. Lig groups). Beyaz 60 holds 110, a club of Kirmizi 61 (ghome), mid-table:
     the set above sends it home; 117, also of Kirmizi, is 17th of 18 and goes down to the 3. Lig
     in the set below, so it is not moved. Both orders of the sets in the world file, and a second
     pass of the same season end: nothing written again ---- */
  for (int rev = 0; rev < 2; rev++) {
    reset(); nmatch = 0;
    league(50, 1, 20, 1); league(60, 101, 18, 2); league(61, 201, 17, 3); league(70, 301, 18, 4); league(71, 401, 18, 5);
    uint32_t homes[] = { 110, 61,  117, 61 };
    fl26_chain_ghomes(homes, 2);
    uint16_t a[] = { 1, 2,  50, 2,  60, 1, 0,  61, 1, 0 };
    uint16_t b[] = { 2, 2,  60, 2,  61, 2,  70, 2, 1,  71, 2, 0 };
    uint16_t gs[40]; int ng = 0;
    const uint16_t* first = rev ? b : a; int nf = rev ? (int)(sizeof b / 2) : (int)(sizeof a / 2);
    const uint16_t* second = rev ? a : b; int ns = rev ? (int)(sizeof a / 2) : (int)(sizeof b / 2);
    for (int i = 0; i < nf; i++) gs[ng++] = first[i];
    for (int i = 0; i < ns; i++) gs[ng++] = second[i];
    check(rev ? "13r: two sets taken (the lower set first in the file)" : "13: two sets taken", fl26_chain_gsets(gs, ng) == 2);
    apply_pre(img);
    game_moves(50, 60, 2, 2);
    apply_post(img);
    dump_log();
    const char* t = rev ? "13r" : "13";
    char w[200];
    snprintf(w, sizeof w, "%s: every club once, sizes 20/18/17/18/18", t);
    check(w, census(91) && size_is(50, 20) && size_is(60, 18) && size_is(61, 17) && size_is(70, 18) && size_is(71, 18));
    snprintf(w, sizeof w, "%s: the guest 110 came home to Kirmizi; 117 (relegated below) went down, not home", t);
    check(w, holds(61, 110) && !holds(60, 110) && (holds(70, 117) || holds(71, 117)) && !holds(61, 117));
    snprintf(w, sizeof w, "%s: the 1. Lig's last two in Beyaz (the place the guest left), the winners up", t);
    check(w, holds(60, 19) && holds(60, 20) && holds(50, 101) && holds(50, 201) && holds(60, 102));
    snprintf(w, sizeof w, "%s: the 3. Lig's winners in the groups they name (70 -> Kirmizi, 71 -> Beyaz)", t);
    check(w, holds(61, 301) && holds(61, 302) && holds(60, 401) && holds(60, 402));
    int w0 = nwrites;
    apply_pre(img); apply_post(img);
    snprintf(w, sizeof w, "%s: a second pass with the same tables writes nothing", t);
    check(w, nwrites == w0 && census(91) && holds(61, 110));
    dump_log();
  }

  /* ---- 14. 16.11.2026: a guest after a save and a load. Season 1: Serie B's 19th and 20th are both
     of Girone A, A has one place: the 20th goes to B as a guest (log "home 1001 full"). Then the
     module starts afresh, as after a load (only the world file's gset and ghome lines again), with
     season 2's tables: the guest is mid-table in B, A sends one up and nobody of A comes down --
     it goes home, from the standings and ghome alone ---- */
  {
    reset(); nmatch = 0;
    league(82, 101, 20, 2); league(1001, 201, 20, 3); league(1002, 301, 20, 4);
    uint32_t homes[] = { 119, 1001,  120, 1001 };
    fl26_chain_ghomes(homes, 2);
    uint16_t gs[] = { 1, 2,  82, 2,  1001, 1, 0,  1002, 1, 0 };
    fl26_chain_gsets(gs, sizeof gs / 2);
    apply_pre(img); game_moves(82, 1001, 2, 1); apply_post(img);
    check("14: season 1: 119 home in A, 120 a guest in B", holds(1001, 119) && holds(1002, 120) && census(60));
    check("14: the log names each club: 'club 119 82 -> 1001 (home)', 'club 120 82 -> 1002 (guest: home 1001 full)'",
          strstr(g_log, "club 119 82 -> 1001 (home)") && strstr(g_log, "club 120 82 -> 1002 (guest: home 1001 full)"));
    dump_log();
    /* the load: the leagues as season 1 left them, season 2's tables in that order (120 is 10th
       in B), every table of the module cleared and read again from the world file's lines */
    uint32_t l82[MAX_CLUBS], la[MAX_CLUBS], lb[MAX_CLUBS];
    int n82 = list_of(82, l82), na = list_of(1001, la), nb = list_of(1002, lb);
    uint32_t sb[MAX_CLUBS]; int k = 0;
    for (int i = 0; i < nb; i++) if ((lb[i] >> 14) != 120) sb[k++] = lb[i];
    memmove(sb + 10, sb + 9, (k - 9) * 4); sb[9] = 120u << 14; k++;
    /* Serie B's last two this time: the clubs that came up the season before (201, 301: no home) */
    memcpy(st[82], l82, n82 * 4); memcpy(st[1001], la, na * 4); memcpy(st[1002], sb, nb * 4);
    fl26_chain_gsets(0, 0); fl26_chain_ghomes(0, 0); fl26_chain_gborders(0, 0);
    fl26_chain_ghomes(homes, 2);
    fl26_chain_gsets(gs, sizeof gs / 2);
    int last2_home = is_home(st[82][18], 1001) || is_home(st[82][19], 1001);
    apply_pre(img); game_moves(82, 1001, 2, 1); apply_post(img);
    check("14: after the load nobody of A comes down (the test's own tables)", !last2_home);
    check("14: season 2 after the load: the guest 120 is home in A, the log says 'guest came home from 1002'",
          holds(1001, 120) && !holds(1002, 120) && strstr(g_log, "club 120 1002 -> 1001 (guest came home from 1002)") && census(60));
    check("14: sizes kept", size_is(82, 20) && size_is(1001, 20) && size_is(1002, 20));
    dump_log();
  }

  /* ---- 15. 16.11.2026: a set moves only at its season's end, the pass in which the game writes
     its upper league. In the game the season-end step also runs at New Year and in the autumn
     with an INPUT entry for the set's leagues, and the old trigger (any INPUT entry) moved the set
     by the half-season's table there (notes/grupe-promocije-1611.md, sections 10 and 11) ---- */
  {
    reset(); nmatch = 0;
    league(82, 101, 20, 2); league(1001, 201, 20, 3); league(1002, 301, 20, 4); league(1003, 401, 20, 5);
    uint16_t gs[] = { 1, 3,  82, 3,  1001, 1, 0,  1002, 1, 0,  1003, 1, 0 };
    fl26_chain_gsets(gs, sizeof gs / 2);
    /* New Year: half a season played, the table as it stands (82's 1st to 3rd at the bottom, 1001's 20th on top) */
    set_date(0, 2027);
    rotate(82, 3); rotate(1001, 19);
    match(1001, 201, 202, 1, 0, 0, 0); match(1001, 203, 204, 2, 2, 0, 0); match(1001, 205, 206, 0, 0, 0, 0);
    blk[mbase + (size_t)(nmatch - 1) * MATCH_STRIDE + 7] = 0;              /* the third not played yet */
    snap_lists(); int w0 = nwrites;
    apply_pre(img); apply_post(img);
    check("15: the pass line has the date, the INPUT entries, the lists the game wrote, the matches",
          log_has("group set 0 pass 01.01.2027: input 4/4, game wrote upper 0/1 groups 0/3, played 2/3, tables 4/4"));
#ifdef GROUP_DIAG_ONLY
    check("15 (old trigger): the New Year pass moves the set by the half-season's table",
          nwrites > w0 && log_has("acts: yes now, no if upper written") && holds(82, 220) && census(80));
    dump_log();
  }
#else
    check("15: early call (the game wrote no upper league): nothing written, lists as they were",
          nwrites == w0 && lists_same() && census(80));
    check("15: and the log says 'not its season's end, untouched', no club line",
          log_has("group set 0 (82 ...): not its season's end, untouched") && !log_has("group set 0: club ") && !log_has("season end --"));
    dump_log();
    /* 1 July: the final tables, the game moves its linked pair 82 <-> 1001 */
    set_date(181, 2027);
    rotate(82, 17); rotate(1001, 1);                                          /* back to the list order */
    apply_pre(img); game_moves(82, 1001, 3, 3); apply_post(img);
    check("15: the final call acts: 'season end' first, then the moves",
          log_has("group set 0 pass 01.07.2027: input 4/4, game wrote upper 1/1 groups 1/3")
          && log_has("group set 0 (82 ...): season end -- the game wrote 1 of its 1 upper league(s)")
          && log_has("group set 0: 1 upper, 3 lower league(s), 3 down and 3 up"));
    check("15: final call: the group winners in 82, 82's last three in the groups, sizes kept, every club once",
          holds(82, 201) && holds(82, 301) && holds(82, 401) && !holds(82, 118) && !holds(82, 119) && !holds(82, 120)
          && size_is(82, 20) && size_is(1001, 20) && size_is(1002, 20) && size_is(1003, 20) && census(80));
    dump_log();
    /* the same final step again, the game writing 82 and 1001 as they stand now: idempotent */
    snap_lists(); w0 = nwrites;
    apply_pre(img);
    { uint32_t l[MAX_CLUBS]; int n = list_of(82, l); pass_write(82, l, n); n = list_of(1001, l); pass_write(1001, l, n); }
    int wg = nwrites;
    apply_post(img);
    check("15: two final calls in a row do not move twice ('already holds', nothing written by us)",
          nwrites == wg && wg == w0 + 2 && lists_same() && log_has("every league already holds its new clubs")
          && !log_has("group set 0: club ") && census(80));
    dump_log();
    /* season 2, autumn: the INPUT table is still last season's (the game's own in the second
       season of the run), the game writes none of the set */
    set_date(288, 2027);
    snap_lists(); w0 = nwrites;
    apply_pre(img); apply_post(img);
    check("15: an early call in season 2 with last season's table writes nothing",
          nwrites == w0 && lists_same() && log_has("group set 0 pass 16.10.2027") && log_has("not its season's end, untouched") && census(80));
    dump_log();
  }
  /* a set the game never writes the upper league of: every pass says so, nothing ever moves */
  {
    reset(); nmatch = 0;
    league(82, 101, 20, 2); league(1001, 201, 20, 3); league(1002, 301, 20, 4);
    uint16_t gs[] = { 1, 2,  82, 2,  1001, 1, 0,  1002, 1, 0 };
    fl26_chain_gsets(gs, sizeof gs / 2);
    snap_lists();
    int untouched = 0, ends = 0;
    for (int p = 0; p < 3; p++) {
      apply_pre(img);
      { uint32_t l[MAX_CLUBS]; int n = list_of(1002, l); pass_write(1002, l, n); }   /* a group only */
      apply_post(img);
      untouched += log_has("group set 0 (82 ...): not its season's end, untouched");
      ends += log_has("season end --");
      dump_log();
    }
    check("15: a set that never gets the signal logs 'not its season's end' at every pass, never 'season end', moves nobody",
          untouched == 3 && ends == 0 && lists_same() && census(60));
  }
#endif

  /* ---- 16. 16.11.2026: a save made with the code before 64a80c3, loaded with this one. The old
     code placed the relegated one by one in table order: 82's 18th and 19th are of 1002, 20th of
     1001; 18th home in 1002, 19th (1002 full) to 1001 (the most places left, the first), 20th
     (1001 full) to 1003. The next season's early pass still reads season 1's table: the old
     trigger moved 19th and 20th mid-season into the new code's places -- every list whole and every
     club's slot its league's, but in the middle of a season the clubs play in other groups.
     Now nothing is written there ---- */
  {
    reset(); nmatch = 0;
    league(82, 101, 20, 2); league(1001, 201, 20, 3); league(1002, 301, 20, 4); league(1003, 401, 20, 5);
    uint32_t homes[] = { 118, 1002,  119, 1002,  120, 1001 };
    fl26_chain_ghomes(homes, 3);
    uint16_t gs[] = { 1, 3,  82, 3,  1001, 1, 0,  1002, 1, 0,  1003, 1, 0 };
    fl26_chain_gsets(gs, sizeof gs / 2);
    int l82[20], la[20], lb[20], lc[20];
    for (int i = 0; i < 17; i++) l82[i] = 101 + i;
    l82[17] = 201; l82[18] = 301; l82[19] = 401;
    for (int i = 0; i < 19; i++) { la[i] = 202 + i; lb[i] = 302 + i; lc[i] = 402 + i; }
    la[19] = 119; lb[19] = 118; lc[19] = 120;
    set_list(82, l82, 20, 2); set_list(1001, la, 20, 3); set_list(1002, lb, 20, 4); set_list(1003, lc, 20, 5);
    set_date(288, 2027);
    snap_lists(); int w0 = nwrites;
    apply_pre(img); apply_post(img);
    static const uint16_t L[4][2] = { { 82, 2 }, { 1001, 3 }, { 1002, 4 }, { 1003, 5 } };
    int badslot = 0;
    for (int q = 0; q < 4; q++) { uint32_t l[MAX_CLUBS]; int n = list_of(L[q][0], l); for (int i = 0; i < n; i++) badslot += slot_of((int)(l[i] >> 14)) != L[q][1]; }
#ifdef GROUP_DIAG_ONLY
    check("16 (old trigger): the early pass moves the old code's 19th and 20th mid-season (120 to 1001, 119 to 1003)",
          nwrites > w0 && holds(1001, 120) && holds(1003, 119) && !holds(1001, 119));
    check("16 (old trigger): every list whole: every club once, sizes kept, every club's slot its league's",
          census(80) && size_is(82, 20) && size_is(1001, 20) && size_is(1002, 20) && size_is(1003, 20) && badslot == 0);
#else
    check("16: an old save's early pass of season 2: nothing written, the old code's places stay till the season's end",
          nwrites == w0 && lists_same() && census(80) && badslot == 0 && log_has("not its season's end, untouched"));
#endif
    dump_log();
  }

  if (fails) { printf("%d check(s) failed\n", fails); return 1; }
  printf("all checks passed\n");
  return 0;
}
