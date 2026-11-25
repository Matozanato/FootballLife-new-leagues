/* fl26match.dll -- the match table's allocator and lookup, ready for match ids past 16 bits.
 *
 * A match id is the index of its 596-byte record in the match table (block + 0xe9ff08 in the
 * exe, moved by fl26caps). The game hands it out in 0x1414bc710 (first record whose u16 at +0
 * is 0xffff, the index written there as a word) and finds it again in 0x1414bc560 (id in dx,
 * truncated at entry). Both are 16-bit, so 65535 records is a wall (notes/match-limit-
 * istrazivanje.md). This replaces both with C that keeps the id as a dword at +0 (+2 is never
 * read by the game, it is zero after the reset 0x140af1ed0) and takes the id in edx whole.
 *
 * A record is free when its u16 at +0 is 0xffff, as before, so the game's own walks over the
 * table still tell free from used. An index whose low 16 bits are 0xffff is therefore never
 * handed out: it would look free, and 0xffff is "no match" all over the game.
 *
 * Steps (notes/plan-zahtjevi-limiti-0411.md, 05.11.):
 *   M1  this, with mask 0xffff and first 0: the game sees no difference (ids < 65535).
 *   M4  first 65536, mask 0xffffffff, once the storages and the code that carries the id
 *       are 32-bit: every id is then past 16 bits, and a site that still truncates looks up
 *       a record nobody has -- a miss, logged here with its callers.
 *
 * Exports: fl26_match_install(first, mask), fl26_match_stats(out[10]), fl26_match_misses(...),
 * fl26_match_statsfile(path), fl26_match_twins(on); players past 65535 (lift16f):
 * fl26_player_install(cap), fl26_player_stats(out[10]).
 * Build: tools/native/build-match.sh (zig cc). */
#include <windows.h>
#include <stdint.h>

#define EXE_VA      0x140000000ull
#define OWNER_VA    0x143705e10ull   /* the edit block's owner (livedump owner_global), block at +0x48 */
#define OWNER_FIELD 0x48
#define ALLOC_VA    0x1414bc710ull
#define LOOKUP_VA   0x1414bc560ull
#define REC         0x254u

static const unsigned char SIG_ALLOC[14] = {0x4c,0x8b,0xc9,0x33,0xc0,0xb9,0xff,0xff,0x00,0x00,0x66,0x0f,0x1f,0x44};
/* lookup: mov [rsp+0x10], rbx; push rsi; mov esi, <cap>; movzx r10d, dx -- the cap is fl26caps' */
static const unsigned char SIG_LOOK_A[7] = {0x48,0x89,0x5c,0x24,0x10,0x56,0xbe};
static const unsigned char SIG_LOOK_B[3] = {0x44,0x0f,0xb7};

static uintptr_t g_exe;
static uint8_t* volatile g_blk;            /* the edit block, as the game hands it to the lookup */
static uint32_t g_off, g_cap, g_first, g_mask = 0xffff;
static volatile LONG g_alloc, g_full, g_hit, g_scan, g_miss, g_none;
static volatile LONG g_wrap, g_wrap_twin;   /* B488: ids handed out below `first`, and those a live match's twin */

#define RING 512
typedef struct { uint32_t id; uint32_t pad; uint64_t ret[3]; } miss_t;
static miss_t g_ring[RING];
static volatile LONG g_ring_n;

static inline uint8_t* rec_at(uint8_t* blk, uint32_t i) { return blk + g_off + (size_t)i * REC; }

/* M4 with first 65536: every id is past 16 bits and records 0..65535 stay free, so a lookup of
 * an id below 65536 (or with junk above bit 15) is an id some code cut to a word. The record it
 * meant is unique, at the id's low word + 65536 (the cap is below 131072): the lookup hands that
 * one back so the game goes on, and the callers are counted here, one entry per call site. */
#define NCUT 256
typedef struct { uint64_t ret[3]; uint32_t n; uint32_t pad; } cut_t;
static cut_t g_cuts[NCUT];
static volatile LONG g_ncut, g_cut;

/* one entry per call site: the first two return addresses, since most lookups come through the
 * game's thin wrappers (0x1414bb280 & co.) and the first frame alone would merge their callers */
static void __attribute__((noinline)) site_note(cut_t* tab, volatile LONG* ntab)
{
  void* fr[5] = {0};
  USHORT k = RtlCaptureStackBackTrace(3, 3, fr, 0);   /* past site_note, its caller and m_lookup */
  uint64_t r0 = k ? (uint64_t)(uintptr_t)fr[0] : 0, r1 = k > 1 ? (uint64_t)(uintptr_t)fr[1] : 0;
  int n = *ntab < NCUT ? (int)*ntab : NCUT;
  for (int i = 0; i < n; i++) if (tab[i].ret[0] == r0 && tab[i].ret[1] == r1) { tab[i].n++; return; }
  LONG j = InterlockedIncrement(ntab) - 1;
  if (j >= NCUT) return;
  for (int q = 0; q < 3; q++) tab[j].ret[q] = q < k ? (uint64_t)(uintptr_t)fr[q] : 0;
  tab[j].n = 1;
}
static void __attribute__((noinline)) cut_note(void) { InterlockedIncrement(&g_cut); site_note(g_cuts, &g_ncut); }
/* twins: a lookup of a low id from a site not known to want the user's twin, while the high twin is
 * a match of the user's club and the low one is not -- the sites that may have meant the high one */
static cut_t g_ambs[NCUT];
static volatile LONG g_namb, g_amb;
static void __attribute__((noinline)) amb_note(void) { InterlockedIncrement(&g_amb); site_note(g_ambs, &g_namb); }
static inline int never(uint32_t i) { return (i & 0xffff) == 0xffff; }

static uint8_t* take(uint8_t* blk, uint32_t lo, uint32_t hi)
{
  for (uint32_t i = lo; i < hi; i++) {
    if (never(i)) continue;
    uint8_t* r = rec_at(blk, i);
    if (*(uint16_t*)r == 0xffff) { *(uint32_t*)r = i; InterlockedIncrement(&g_alloc); return r; }
  }
  return 0;
}

/* Twins (M5, the real thing): past 65535 matches an id L and L + 65536 are both live. The game's
 * sites that still cut an id to a word are then ambiguous; the detector (first 65536) shows which
 * they are, and the ones left are the user's own: his club's schedule (slot 0 of the per-club
 * schedules, 0x14158bd70) keeps u16 ids in a full 16-byte entry. A cut lookup from such a site
 * means the twin that is the user's club's match, so it is told apart by the record's clubs
 * (+0x14/+0x18) against slot 0's club (+4). Any other lookup of a word is the low id itself.
 * fl26_match_twins(1) hands ids out low and high in turn, so twins exist from the first match
 * on: the test of all this without 65536 live matches (harsher than real: a twin pair is two
 * matches made one after the other, same competition and day). fl26_match_twins(n > 1) wraps
 * after n ids instead, so a pair is n allocations apart, as in a full table. */
#define SCHED_LEA_VA 0x14158bde2ull       /* lea rsi, [r15 + schedules] */
/* sites that still read a u16 id out of the managed club's schedule (block+0x3070430, 16 B a day):
 * 0x14158be74 the schedule reader, 0x14157ae1e the hub's day strip (0x14157a790), 0x14157b253 the
 * competition of the user's next match (0x14157b130, from the strip's list of {u16 id, date}) */
/* 0x140cb113f, 0x140cb148d: the rows of Be a Legend's Schedule page, shown from the word the builder kept */
static const uint64_t USER_SITES[] = {0x14158be74ull, 0x14157ae1eull, 0x140cb113full, 0x140cb148dull,
                                      0x140b06890ull, 0x140b068f5ull, 0x140b06abaull, 0x140b071ecull};
/* Be a Legend's Schedule page (B465, 14.11.2026). Its builder (0x140cae9c0 on) walks the calendar,
 * block+0x16038a8: 365 days of 0x2c4 bytes, each up to 280 match ids as WORDS. For every word of a
 * day it asks 0x140cb0660 "is this my club's match" and 0x140caff70, and both look the word up
 * (0x140cb068e, 0x140caff9f). With twins live the word of a day is one of two matches, and the
 * user's club does not tell them apart: the other twin can be his match of ANOTHER day, and the
 * page then showed that one (21 Feb showed the match of 28 Feb). What tells them apart is the day
 * the loop is at: its date is at [rbp-0x31] of the builder ({u16 year, u8 month, u8 day}, the
 * record's own date at +8 has the same form). The 15 bytes at 0x140caea43
 * `movzx edx, ax; mov rcx, r14; call 0x140cb0660; test al, al; je 0x140caea87` go to a stub that
 * notes that date first; a lookup from the two sites then takes the twin dated that day. */
#define DAY_VA 0x140caea43ull
static const unsigned char SIG_DAY[15] = {0x0f,0xb7,0xd0,0x49,0x8b,0xce,0xe8,0x12,0x1c,0x00,0x00,0x84,0xc0,0x74,0x35};
static const uint64_t DAY_SITES[] = {0x140cb068eull, 0x140caff9full};
/* Be a Legend after a match of the user's club (B465): its pages and the day's processing get the
 * match's id from lists and arguments that hold it whole and cut it on the way to the lookup, in
 * functions that never read the context. Seen with the current match's low word (diagnostic build,
 * 14.11.2026): the result page showed the low twin's competition ("Championnat National du Togo,
 * Matchday 1" for a Central League match). At these sites the low word of the current match is the
 * current match; at the pages' own (PAGE) another word is the user's club's twin, as at USER_SITES. */
static const uint64_t CUR_PAGE_SITES[] = {0x140caefc0ull, 0x140b01aedull, 0x140b01773ull, 0x140ca2228ull,
                                          0x140ca29d5ull, 0x140ca1fb1ull, 0x140cd6a71ull,
                                          /* 0x141515300 (the result page's score; its 7 callers are Be a Legend pages) and
                                           * 0x141513990's lookup (the page's rows) cut the id themselves */
                                          0x14151531eull, 0x1415139ceull};
/* 0x14154edc3: 0x14154ed60 takes the id whole in ecx and 0x14154e8d0 cuts it (`movzx edx, di`)
 * 0x1412fde56, 0x1412fde91, 0x1412fdec9 (twins sweep, 17.11.2026): 0x1412fd680 (UpdatePostMatchThread /
 * UpdateDayEndThread) looks the same [rsp+0x28] up four times -- the context's word, stored at 0x1412fd904
 * -- and only the first (0x1412fdb15) was listed; the B488 run's "amb" lines name the other three */
static const uint64_t CUR_SITES[] = {0x141332154ull, 0x1412fdb15ull, 0x1412fe0f7ull, 0x14154edc3ull, 0x141550727ull,
                                     0x1412fde56ull, 0x1412fde91ull, 0x1412fdec9ull};
/* B470/B465 (17.11.2026): Be a Legend's Calendrier and the matchday page opened from it with cross.
 * The Calendrier's day entries (20 bytes: day, id at +4, ...) come from the Schedule builder 0x140cae960,
 * which keeps the day's WORD (0x140caea84 `movzx esi, ax`, from the calendar's word lists): the whole id
 * is never stored there. The rows look that word up at USER_SITES (the user's club's twin: right rows).
 * Cross on a day runs 0x140b05930 (the Calendrier's vtable 0x14268bda8 +0x188): it looks the entry's
 * word up (0x140b059a2 `pextrw edx, xmm0, 2`) and hands it to 0x140e40f90, the "chosen match" (dword at
 * 0x1436f9a60). The matchday page (ctor 0x140cab990, vtable 0x142725490, a result page subclass) takes
 * it from 0x140e3d470 into +0xb8 and looks it up at four more places (0x140cabb9c `movzx edx, bx`,
 * 0x140cacc0c and 0x140cac422/0x140cac5a0 `movzx edx, word [reg+0xb8]`). None was a listed site, so
 * with twins live every one got the low twin: the page showed that match's competition and matchday
 * ("Tercera Division A J22" for EFL Championship J22, diagnostic twinlog of 17.11.: these return
 * addresses, ids 3818 and 3566). Widening would not help: the value is the word itself.
 * PICK_FROM is the Calendrier's lookup: its word is the user's club's match (the builder keeps a day's
 * word only when 0x140cb0660 and 0x140caff70 say so), so the user's twin is taken, as at USER_SITES,
 * and remembered whole (g_pick). PICK_PAGE are the matchday page's lookups: the remembered twin when
 * the word is its word, else as before. Each return address is used only when the bytes before it are
 * the shipped read and `call 0x1414bb280` (pick_check); a site that differs is left off and counted. */
#define WRAP_VA 0x1414bb280ull
typedef struct { uint64_t ret, at; const char* hex; } pick_t;
static const pick_t PICK[] = {
  {0x140b059afull, 0x140b059a2ull, "660fc5d002488bcbe8"},        /* pextrw edx, xmm0, 2; mov rcx, rbx; call */
  {0x140cabba7ull, 0x140cabb9cull, "0fb7d3488bcfe8"},            /* movzx edx, bx; mov rcx, rdi; call */
  {0x140cacc1cull, 0x140cacc0cull, "0fb793b8000000488b4848e8"},  /* movzx edx, word [rbx+0xb8]; mov rcx, [rax+0x48]; call */
  {0x140cac432ull, 0x140cac422ull, "410fb797b8000000498bcce8"},  /* movzx edx, word [r15+0xb8]; mov rcx, r12; call */
  {0x140cac5b0ull, 0x140cac5a0ull, "410fb797b8000000498bcce8"},
};
#define NPICK ((int)(sizeof PICK / sizeof *PICK))
static uint64_t g_pick_ret[NPICK];        /* PICK[i].ret when its bytes are the game's, else 0 */
static volatile uint32_t g_pick = 0xffffffffu;   /* the twin the Calendrier took, whole; none yet */
static volatile LONG g_pick_hi, g_pick_lo, g_pick_amb, g_page_hi, g_page_lo, g_page_none;
static volatile uint32_t g_daydate;       /* the day the Schedule builder is at, 0 = not hooked */
static volatile LONG g_dayhook, g_day_hi, g_day_lo, g_day_same, g_day_none;
static int jmp_to(uintptr_t site, void* to);
static unsigned char g_daysee[15];
static int day_hook(void)
{
  unsigned char* x = (unsigned char*)(g_exe + (DAY_VA - EXE_VA));
  for (int i = 0; i < 15; i++) g_daysee[i] = x[i];
  /* matchid32 has made the first three `mov edx, eax; nop` by now (eax is the word either way) */
  int wide = x[0] == 0x89 && x[1] == 0xc2 && x[2] == 0x90;
  for (int i = wide ? 3 : 0; i < 15; i++) if (x[i] != SIG_DAY[i]) return 0;
  static const unsigned char code[] = {
    0x89,0xc2,0x90,               /* mov edx, eax; nop */
    0x49,0x8b,0xce,               /* mov rcx, r14 */
    0x8b,0x45,0xcf,               /* mov eax, [rbp-0x31] */
    0x49,0xba,0,0,0,0,0,0,0,0,    /* mov r10, &g_daydate */
    0x41,0x89,0x02,               /* mov [r10], eax */
    0x48,0xb8,0,0,0,0,0,0,0,0,    /* mov rax, 0x140cb0660 */
    0xff,0xd0,                    /* call rax */
    0x84,0xc0,                    /* test al, al */
    0x74,0x0e,                    /* jz +14 */
    0xff,0x25,0,0,0,0, 0,0,0,0,0,0,0,0,   /* jmp 0x140caea52 */
    0xff,0x25,0,0,0,0, 0,0,0,0,0,0,0,0    /* jmp 0x140caea87 */
  };
  unsigned char* t = (unsigned char*)VirtualAlloc(0, 128, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
  if (!t) return 0;
  for (unsigned i = 0; i < sizeof code; i++) t[i] = code[i];
  *(uint64_t*)(t + 11) = (uint64_t)(uintptr_t)&g_daydate;
  *(uint64_t*)(t + 24) = (uint64_t)(uintptr_t)(x + 11 + *(int32_t*)(x + 7));
  *(uint64_t*)(t + 44) = (uint64_t)(uintptr_t)(x + 15);
  *(uint64_t*)(t + 58) = (uint64_t)(uintptr_t)(x + 15 + 0x35);
  return jmp_to((uintptr_t)x, t);
}
/* The strip's list ({id, date}, 0x14157a820) kept the schedule's word as the id, so its readers
 * looked the low twin up again (06.11., m9y: "Next" showed Senegal's league for Anderlecht). After
 * the lookup at 0x14157ae1e (a user site, so the user's twin) the list gets the found record's whole
 * id: the 14 bytes `movzx ecx, word [rax]; cmp ecx, ebp; jne 0x14157b0a7; mov esi, [rax+8]` go to a
 * stub that compares the low word as before and then takes the dword into ebp, the value the list
 * stores. matchid32 round 5 widens the list's readers. */
#define STRIP_VA 0x14157ae1eull
static const unsigned char SIG_STRIP[14] = {0x0f,0xb7,0x08,0x3b,0xcd,0x0f,0x85,0x7e,0x02,0x00,0x00,0x8b,0x70,0x08};
static int strip_hook(void)
{
  unsigned char* x = (unsigned char*)(g_exe + (STRIP_VA - EXE_VA));
  for (int i = 0; i < 14; i++) if (x[i] != SIG_STRIP[i]) return 0;
  static const unsigned char code[] = {
    0x8b,0x08,                    /* mov ecx, [rax] */
    0x66,0x39,0xe9,               /* cmp cx, bp */
    0x75,0x13,                    /* jne bad */
    0x89,0xcd,                    /* mov ebp, ecx: the whole id */
    0x8b,0x70,0x08,               /* mov esi, [rax+8] */
    0xff,0x25,0,0,0,0, 0,0,0,0,0,0,0,0,   /* jmp 0x14157ae2c */
    0xff,0x25,0,0,0,0, 0,0,0,0,0,0,0,0 }; /* bad: jmp 0x14157b0a7 */
  unsigned char* t = (unsigned char*)VirtualAlloc(0, 64, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
  if (!t) return 0;
  for (unsigned i = 0; i < sizeof code; i++) t[i] = code[i];
  *(uint64_t*)(t + 18) = (uint64_t)(uintptr_t)(x + 14);
  *(uint64_t*)(t + 32) = (uint64_t)(uintptr_t)(x + 11 + 0x27e);
  return jmp_to((uintptr_t)x, t);
}
static volatile LONG g_strip;

/* B465/B470 (16.11.2026): the result page (class 0x140ca2060, vtable 0x1427215e0) keeps a matchday's
 * matches as 8-byte entries {slot index, id} in groups at page+0x90 (stride 0x20, the entries at the
 * group's +8). Its fillers 0x140caad90, 0x140cabcb0 and 0x140cac030 store the slot reader's whole id
 * (matchid32 widens 0x140cab4bb..0x140cac179), and 0x14152af20, handed the id by pointer, reads it as a
 * dword (0x14152b07d) -- but the page itself reads it back as a word at four places and looks that up,
 * so with twins live the low one, another competition's match, comes back:
 *   0x140ca2219  the header: the competition's name (morpheus' UEL page titled "Liga BetPlay DIMAYOR I")
 *   0x140ca1fa4  vtable +0x270: the row's fixture slot, taken from the competition of that match
 *                (his 8 rows were Colombian clubs too)
 *   0x140ca29c8, 0x140ca2b44  vtable +0x268: the group's first entry
 * The B488 run's "amb" lines name the lookups after three of them (0x140ca2228, 0x140ca1fb1,
 * 0x140ca29d5). Each becomes the dword read; an entry that holds a low id reads as before. The
 * bytes are checked first: a site that is neither the shipped instruction nor the dword read already
 * is left alone and named in the stats. */
typedef struct { uint64_t va; unsigned n; unsigned char old[5], neu[5]; } wide_t;
static const wide_t PAGE_WIDE[] = {
  {0x140ca2219ull, 3, {0x0f,0xb7,0xd3},           {0x8b,0xd3,0x90}},           /* movzx edx, bx -> mov edx, ebx */
  {0x140ca1fa4ull, 5, {0x0f,0xb7,0x54,0xd8,0x04}, {0x8b,0x54,0xd8,0x04,0x90}}, /* word [rax+rbx*8+4] -> dword */
  {0x140ca29c8ull, 5, {0x0f,0xb7,0x54,0x24,0x24}, {0x8b,0x54,0x24,0x24,0x90}}, /* word [rsp+0x24] -> dword */
  {0x140ca2b44ull, 5, {0x0f,0xb7,0x54,0x24,0x24}, {0x8b,0x54,0x24,0x24,0x90}},
};
#define NWIDE ((int)(sizeof PAGE_WIDE / sizeof *PAGE_WIDE))
/* 1 = the shipped instruction (widen it), 2 = the dword read already, 0 = something else (leave it) */
static int wide_state(const unsigned char* at, const wide_t* w)
{
  int o = 1, d = 1;
  for (unsigned i = 0; i < w->n; i++) { o &= at[i] == w->old[i]; d &= at[i] == w->neu[i]; }
  return o ? 1 : d ? 2 : 0;
}
static int g_wide_st[NWIDE];               /* what page_widen found: 1 widened, 2 already, 0 left alone */
static unsigned char g_wide_seen[NWIDE][5];

/* Twins sweep (17.11.2026, notes/twins-pregled-1711.md): every lookup of FL_2027.exe whose id reaches
 * edx through a movzx was traced back; at these 15 the id is already whole one instruction before --
 * in a register or in a dword the game itself wrote -- and the movzx cuts it for the lookup only, the
 * way PAGE_WIDE's four did. With twins live they answer the low one, another competition's match.
 *   result page family (the entries {slot, id} the fillers write as dwords, see PAGE_WIDE):
 *   0x140caa84e, 0x140caaad9  ResultFinalTournament (vtable 0x142724c70) +0x268: the knockout page's
 *                header, from the group's first entry (`mov eax, [rdx+4]` / `[r8+4]`, then movzx edx, ax);
 *                its filler 0x140caad90 writes the entry's +4 as a dword (0x140cab4da)
 *   0x140af88ba, 0x140af88f0  MatchResultPlayoff (0x142686928) +0x280: word [rcx+4] of the entries its
 *                +0x260 0x140af89d0 writes as dwords (0x140af8b27)
 *   0x140cacefa, 0x140cacf30  MatchDayResultsGroupStage (0x1427258d0) +0x280: the same, entries from
 *                0x140cacf90 (dword at 0x140cad0b0, from 0x141510bd0's id list)
 *   0x140ca3fcb, 0x140ca3fe3  MatchDayResults (0x142686690) +0x278: `mov ebx, [rcx]` of 0x141510bd0's
 *                dword id list, then movzx edx, bx
 *   today's match of the user's club, 0x1414c8fd0 (whole in eax: `mov eax, esi`, esi the day list's dword):
 *   0x140c8ca90, 0x140c8cbe9  MainMenuLicenseLeague +0x268 helpers
 *   0x140cd1780               MainMenuML / MainMenuBL +0x290 helper 0x140cd1760 (the hub)
 *   0x140cb077a               0x140cb0660, the Schedule builder's per-day step (after has() on the dword)
 *   0x1412eb4d6               CmnCheckFlowEyeCatch (0x1412eb2f0)
 *   0x14130327c               CmnModeMainMenuGamePlanCreation (0x141303200)
 *   0x141fe2b9c               0x141fe20a0 (screen not identified)
 * Each becomes the 32-bit move of the same source. Where the source holds a low id (an unpatched day
 * list, a movzx upstream), its upper half is zero and the id read is the one read before. Same byte check
 * as PAGE_WIDE: neither the shipped instruction nor the 32-bit one already = left alone, named in the stats. */
static const wide_t TWIN_WIDE[] = {
  {0x140caa84eull, 3, {0x0f,0xb7,0xd0},      {0x8b,0xd0,0x90}},           /* movzx edx, ax -> mov edx, eax */
  {0x140caaad9ull, 3, {0x0f,0xb7,0xd0},      {0x8b,0xd0,0x90}},
  {0x140af88baull, 4, {0x0f,0xb7,0x51,0x04}, {0x8b,0x51,0x04,0x90}},      /* word [rcx+4] -> dword */
  {0x140af88f0ull, 4, {0x0f,0xb7,0x51,0x04}, {0x8b,0x51,0x04,0x90}},
  {0x140cacefaull, 4, {0x0f,0xb7,0x51,0x04}, {0x8b,0x51,0x04,0x90}},
  {0x140cacf30ull, 4, {0x0f,0xb7,0x51,0x04}, {0x8b,0x51,0x04,0x90}},
  {0x140ca3fcbull, 3, {0x0f,0xb7,0xd3},      {0x8b,0xd3,0x90}},           /* movzx edx, bx -> mov edx, ebx */
  {0x140ca3fe3ull, 3, {0x0f,0xb7,0xd3},      {0x8b,0xd3,0x90}},
  {0x140c8ca90ull, 3, {0x0f,0xb7,0xd0},      {0x8b,0xd0,0x90}},
  {0x140c8cbe9ull, 3, {0x0f,0xb7,0xd0},      {0x8b,0xd0,0x90}},
  {0x140cd1780ull, 3, {0x0f,0xb7,0xd0},      {0x8b,0xd0,0x90}},
  {0x140cb077aull, 3, {0x0f,0xb7,0xd3},      {0x8b,0xd3,0x90}},
  {0x1412eb4d6ull, 3, {0x0f,0xb7,0xd0},      {0x8b,0xd0,0x90}},
  {0x14130327cull, 3, {0x0f,0xb7,0xd0},      {0x8b,0xd0,0x90}},
  {0x141fe2b9cull, 3, {0x0f,0xb7,0xd0},      {0x8b,0xd0,0x90}},
};
#define NTWIN ((int)(sizeof TWIN_WIDE / sizeof *TWIN_WIDE))
static int g_twin_st[NTWIN];               /* what twin_widen found: 1 widened, 2 already, 0 left alone */
static unsigned char g_twin_seen[NTWIN][5];

/* The score of a result row (21.11.2026, Master League, Ligue 1 of a big world). 0x141515300 (the row's
 * score: played? goals) takes the id in ecx, and its seven callers -- all on the matchday-results pages,
 * 0x140ca1b60, 0x140ca1d50, 0x140ca2890, 0x140ca7fc0, 0x140ca80d0 -- hand it the record's id as
 * `movzx ecx, word [rec]`, rec the record a lookup just gave them (fl26match keeps the id whole at +0).
 * caps widens the cut inside it (0x14151530f), too late: the word is all it gets. While a low id was a
 * twin of a live match (389 handed out below 65536 in that career), the score looked up the low twin,
 * another competition's match not played yet, and the page listed the round's fixtures with no result
 * but the user's (the current match, which the lookup tells apart) -- the table counted them all. Each
 * read becomes the dword read of the same record; same byte check as PAGE_WIDE. */
static const wide_t SCORE_WIDE[] = {
  {0x140ca1bbaull, 4, {0x0f,0xb7,0x4d,0x00}, {0x8b,0x4d,0x00,0x90}},      /* word [rbp] -> dword */
  {0x140ca1bc6ull, 4, {0x41,0x0f,0xb7,0x0e}, {0x41,0x8b,0x0e,0x90}},      /* word [r14] -> dword */
  {0x140ca1d91ull, 3, {0x0f,0xb7,0x08},      {0x8b,0x08,0x90}},           /* word [rax] -> dword */
  {0x140ca28feull, 3, {0x0f,0xb7,0x08},      {0x8b,0x08,0x90}},
  {0x140ca802dull, 3, {0x0f,0xb7,0x08},      {0x8b,0x08,0x90}},
  {0x140ca8145ull, 3, {0x0f,0xb7,0x0e},      {0x8b,0x0e,0x90}},           /* word [rsi] -> dword */
  {0x140ca814full, 4, {0x41,0x0f,0xb7,0x0e}, {0x41,0x8b,0x0e,0x90}},      /* word [r14] -> dword */
};
/* The rows of the matchday-results page (21.11.2026, the same career, next round: one row only, the
 * user's, and the table counted every match). MatchDayResults' +0x278 (0x140ca3ee0) keeps the day's id
 * list (dwords, 0x141510bd0) through a remove_if (0x140ca3a50) whose test 0x140ca22a0 gets the id whole
 * in ecx, cuts it (`movzx edx, di`) for the lookup and compares the match's round with the current
 * match's (ctx+0x35960). With a twin live it tested the low twin, another competition's match, and the
 * round's fixture left the list. The only lookup of the exe that compares with ctx+0x35960 after a cut. */
static const wide_t LIST_WIDE[] = {
  {0x140ca22bfull, 3, {0x0f,0xb7,0xd7},      {0x8b,0xd7,0x90}},           /* movzx edx, di -> mov edx, edi */
};
#define NLIST ((int)(sizeof LIST_WIDE / sizeof *LIST_WIDE))
static int g_list_st[NLIST];
static unsigned char g_list_seen[NLIST][5];
#define NSCORE ((int)(sizeof SCORE_WIDE / sizeof *SCORE_WIDE))
static int g_score_st[NSCORE];             /* what score_widen found: 1 widened, 2 already, 0 left alone */
static unsigned char g_score_seen[NSCORE][5];

static uint32_t g_sched;                  /* block offset of the per-club schedules, 0 = unknown */
static volatile LONG g_twins, g_turn, g_both, g_user_hi, g_user_amb, g_user_none;

#define USER_LEA_VA 0x140ac8fe3ull        /* lea rcx, [rsi + user club] (fl26layout.h: lay_user) */
static uint32_t g_user_off;               /* block offset of the user's club, 0 = unknown */
/* the user's club; the schedule's own club only when that offset is unknown (it is 0x3fff until
 * the day loop files the schedule: a new career's hub, 06.11.) */
static uint32_t user_club(uint8_t* blk)
{
  uint32_t c = g_user_off ? *(uint32_t*)(blk + g_user_off) : g_sched ? *(uint32_t*)(blk + g_sched + 4) : 0x3fff;
  return c & 0x3fff;
}
static int has_club(const uint8_t* r, uint32_t c)
{
  return (*(const uint32_t*)(r + 0x14) & 0x3fff) == c || (*(const uint32_t*)(r + 0x18) & 0x3fff) == c;
}
/* The current match (the one the user plays or watches) sits in the match context, [ctx+0x50] +
 * 0x35960, as words: its id at +8 (read by 0x141854f00, 127 sites), its competition at +0xa, set
 * together from the record by 0x141550090. +8 has no room for the high half, so the id read there
 * is cut. 0x141550090 is hooked to keep the whole id (g_cur); a lookup of its low word made from a
 * function that reads +8 (CTX_FNS: the functions with a call to 0x141854f00 on the context, and
 * 0x141523ff0 that gets it by pointer from them) is that match. The ranges are whole functions:
 * a function the compiler split (an early `jmp` out, the rest under chained unwind info) has
 * several .pdata entries, and the first list kept only the one with the call -- 27 functions were
 * cut short, 0x1413b7060 after 0x56 bytes. Its lookups after the user's match then got the low
 * twin: Be a Legend showed another league's matchday as the result and the table did not count
 * the match (B465, 14.11.2026). */
#define SETCTX_VA   0x141550090ull
static const unsigned char SIG_SETCTX[15] = {0x48,0x89,0x5c,0x24,0x10,0x48,0x89,0x74,0x24,0x18,0x57,0x48,0x83,0xec,0x20};
static volatile uint32_t g_cur = 0xffff;
static volatile LONG g_cur_hi, g_cur_low, g_cur_site, g_cur_post;
typedef struct { uint32_t b, e; } fnr_t;
static const fnr_t CTX_FNS[] = {   /* exe RVAs, sorted; every fragment of each function (B465) */
  {0x8e9210,0x8e92db}, {0xab8500,0xab8f1f}, {0xac6260,0xac6300}, {0xadcc40,0xadd194},
  {0xaf89d0,0xaf8f87}, {0xb0cae0,0xb0cc0d}, {0xb362a0,0xb3647a}, {0xb365f0,0xb36b8a},
  {0xb6d060,0xb6d118}, {0xc6a540,0xc6b1ac}, {0xc907f0,0xc929d4}, {0xca3e20,0xca3edc},
  {0xcd3490,0xcd3572}, {0xe9c630,0xe9e0d8}, {0xea2db0,0xea2e8d}, {0xebe370,0xebe4d8},
  {0xed67c0,0xed6860}, {0xed6ce0,0xed6d42}, {0xed75a0,0xed75d8}, {0xed77c0,0xed7810},
  {0xed7bb0,0xed7be2}, {0xed7e00,0xed7ee9}, {0xed83b0,0xed8482}, {0xed9aa0,0xed9b77},
  {0xed9d20,0xed9e01}, {0xf0f9c0,0xf10980}, {0xf786e0,0xf78897}, {0xf795e0,0xf7979f},
  {0xf79c30,0xf79e51}, {0xf7a320,0xf7a50c}, {0x12912f0,0x129225e}, {0x1292260,0x1292d01},
  {0x1292d10,0x12967cd}, {0x12967d0,0x1296e69}, {0x1296e70,0x129742b}, {0x1297430,0x129819d},
  {0x12981a0,0x1298768}, {0x1298770,0x1298d98}, {0x129e300,0x129f5bc}, {0x129f5c0,0x12a1624},
  {0x12b4660,0x12b500d}, {0x12b5010,0x12b5561}, {0x12dc210,0x12dc3fa}, {0x12de340,0x12df0f7},
  {0x12df260,0x12e01be}, {0x12e1130,0x12e158e}, {0x12e1590,0x12e1c7a}, {0x12e1c80,0x12e2325},
  {0x12f0e00,0x12f0f22}, {0x12f3230,0x12f35b7}, {0x12f42d0,0x12f514a}, {0x12f8800,0x12f8e5b},
  {0x12f9de0,0x12fa01c}, {0x13007d0,0x1301901}, {0x1308aa0,0x1308d00}, {0x13096b0,0x13099f1},
  {0x131d8c0,0x131f0a3}, {0x1326b70,0x132727a}, {0x132d4f0,0x132da48}, {0x132e2a0,0x132e7cd},
  {0x133ec60,0x133f41b}, {0x134aa50,0x134b626}, {0x13b3b20,0x13b3ce7}, {0x13b7060,0x13b755f},
  {0x151cab0,0x151cb90}, {0x151d110,0x151d18d}, {0x1521cf0,0x1521e4a}, {0x1521e50,0x152200f},
  {0x1523ff0,0x15251db}, {0x15251e0,0x1526f67}, {0x1528490,0x152879c}, {0x1535ae0,0x153696a},
  {0x154f8f0,0x154f991}, {0x15720d0,0x157238e}, {0x1586bc0,0x15870e1}, {0x1fc7e10,0x1fc814c},
  {0x1fc86c0,0x1fc8862}, {0x1fc8870,0x1fc89b2}, {0x1fc8a90,0x1fc8e77}, {0x1fc9260,0x1fc94bc},
  {0x1fca040,0x1fca3bf}, {0x1fca820,0x1fca9d2}, {0x2186fb0,0x2187189}, {0x2187190,0x2187369},
  {0x2187370,0x2187567}, {0x2187570,0x218774c}, {0x21878f0,0x2187d6a}, {0x2187d70,0x21881e9},
  {0x21881f0,0x218866a}, {0x2188670,0x2188a75}, {0x2188a80,0x2188e68}, {0x2188e70,0x21892c9},
  {0x21892d0,0x21894a8}, {0x218ab20,0x218acb6}, {0x2196370,0x2196645}, {0x2196650,0x219686e},
  {0x2197030,0x2197766}, {0x2197770,0x2197a36}, {0x2197a40,0x2197d39}, {0x2197d40,0x2197fe8},
  {0x219be40,0x219c4ed}, {0x219c4f0,0x219cd34}, {0x219cd40,0x219ce6f}, {0x219ce70,0x219d10b},
  {0x219d110,0x219d6b4}, {0x219d6c0,0x219dc41}, {0x219dc50,0x219e1d4}, {0x219e1e0,0x219e41a},
  {0x219e420,0x219e65c}, {0x219e660,0x219e89d}, {0x219e8a0,0x219eadf}, {0x219eae0,0x219ed7f},
  {0x219ed80,0x219f67b}, {0x219f680,0x219fa62}, {0x219fa70,0x219fd5c}, {0x219fd60,0x21a00b6},
  {0x21a2e70,0x21a3287}
};
static void (__attribute__((ms_abi)) *g_setctx)(const uint8_t*);
static void __attribute__((ms_abi)) m_setctx(const uint8_t* rec)
{
  g_cur = *(const uint32_t*)rec;
  g_setctx(rec);
}
/* The post-match thread (21.11.2026, Master League, Ligue 1 of a big world: the hub's headline read
 * "Derrota contra , 1-0" after a win, no opponent). 0x1412fd680 (UpdatePostMatchThread /
 * UpdateDayEndThread, one .pdata entry) reads the context's word (0x1412fd8fc, r15 = ctx + 0x35960)
 * into [rsp+0x28] and hands it on, by value or by pointer, to Master League's after-match handlers:
 * 0x14133dfc0 (the gate and the money, its lookup returns at 0x14133e00b, deeper ones under
 * 0x141567540), 0x14132add0 (0x14132ae80), 0x1413365d0 (reads the context itself, 0x1413366ec) and
 * 0x14134edc0. CUR_SITES named only 0x1412fd680's own four lookups, so with the current match a high
 * twin every one of these got the low twin, another competition's match without the user's club: the
 * news item had no opponent and, his club in neither slot, the result fell through to a defeat (the
 * stats' "amb" lines, 11-13 each, one per match of the career). A lookup of the current match's low
 * word anywhere under this function is the current match -- except when the low twin is played the
 * same day: the day-end pass also simulates the day's other matches, so then it stays the low one. */
static const fnr_t POST_FNS[] = { {0x12fd680,0x12fe5d0} };
/* 1 = under a function of CTX_FNS, 2 = only under one of POST_FNS (check the dates), 0 = neither */
static int __attribute__((noinline)) ctx_site(void)
{
  void* fr[8] = {0};
  USHORT k = RtlCaptureStackBackTrace(2, 8, fr, 0);   /* past ctx_site and m_lookup */
  int post = 0;
  for (int j = 0; j < k; j++) {
    uintptr_t v = (uintptr_t)fr[j];
    if (v < g_exe || v >= g_exe + 0x8000000) continue;
    uint32_t r = (uint32_t)(v - g_exe);
    if (j < 6) {                                       /* CTX_FNS: the depth it always had */
      int lo = 0, hi = (int)(sizeof CTX_FNS / sizeof *CTX_FNS) - 1;
      while (lo <= hi) {
        int m = (lo + hi) / 2;
        if (r < CTX_FNS[m].b) hi = m - 1; else if (r >= CTX_FNS[m].e) lo = m + 1; else return 1;
      }
    }
    for (unsigned s = 0; s < sizeof POST_FNS / sizeof *POST_FNS; s++)
      if (r >= POST_FNS[s].b && r < POST_FNS[s].e) post = 1;
  }
  return post ? 2 : 0;
}

/* Today's calendar list (21.11.2026, the same career: the headline still read "Derrota contra" after
 * the POST_FNS fix, which did fire). Master League's daily pass and its news manager walk TODAY's day
 * of the calendar (block + calendar + today * day size: up to 280 match ids as WORDS, the count at
 * +0x230) and look each word up: 0x14134bc70 (the news manager's "the user's club's match today",
 * called from 0x14134ec10 and 0x14134edc0), 0x141333ad0.. (the day's matches, 0x1412f8e60), and
 * 0x1413007d0 / 0x141304810 (the daily news and finances). With twins live the word of today's match
 * of the user's club, a high id, is also a low match of another day; the lookup gave that one, the
 * user's club was in neither slot, and the news fell to a defeat with no opponent. These are the
 * functions that read the calendar's "today" index (its displacement, 0x1642a1c from the block or
 * 0x3f174 from the calendar, in the shipped exe; every fragment of each, .pdata), 81 of them: when
 * one of them is the lookup's direct caller (the first two return addresses: a wrapper's and its
 * caller's) and only the high twin is dated today (block + 0x1642a24, the dword 0x1415765e0 reads,
 * the form of the record's +8), it is the high twin. A deeper caller is not enough: 0x141546c70 (the
 * slots of a competition), called from them, keeps the slots' own pick. */
static const fnr_t TODAY_FNS[] = {   /* exe RVAs, sorted */
  {0xadcc40,0xadd194}, {0xaed760,0xaed98d}, {0xaf1fb0,0xaf204a}, {0xaf93f0,0xaf94c0},
  {0xaf94e0,0xaf980c}, {0xafff60,0xb000b3}, {0xb00a60,0xb00d86}, {0xb00ed0,0xb00f8d},
  {0xb01360,0xb0190c}, {0xb02120,0xb02550}, {0xb05840,0xb0592f}, {0xb85170,0xb85a48},
  {0xb85a50,0xb86416}, {0xb95310,0xb95e38}, {0xbbdec0,0xbbe421}, {0xc907f0,0xc929d4},
  {0xca3e20,0xca3edc}, {0xca7160,0xca73b7}, {0xcae960,0xcaecf7}, {0xcaee60,0xcaff6b},
  {0xcd3490,0xcd3572}, {0xed9b80,0xed9c00}, {0xf0f9c0,0xf10980}, {0xf6a830,0xf6ab01},
  {0xfad5f0,0xfad62e}, {0xfad62e,0xfad694}, {0xfad694,0xfad736}, {0xfad736,0xfad838},
  {0xfad838,0xfad841}, {0xfc4130,0xfc4584}, {0xfc49c0,0xfc4a4c}, {0xfc4a4c,0xfc4bf4},
  {0xfc4bf4,0xfc4db5}, {0xfc6cb0,0xfc6ce1}, {0xfc6ce1,0xfc6ce9}, {0xfc6ce9,0xfc7039},
  {0xfc7039,0xfc706a}, {0xfc706a,0xfc7073}, {0xfc7ee0,0xfc800c}, {0xfc93e0,0xfc9eac},
  {0x12695b0,0x1269ee4}, {0x1275b00,0x1275c22}, {0x12ddc40,0x12de333}, {0x12e0540,0x12e0573},
  {0x12e0573,0x12e0946}, {0x12e0946,0x12e09d4}, {0x12e09d4,0x12e0a0d}, {0x12e0a0d,0x12e0b25},
  {0x12e0b25,0x12e0b45}, {0x12e0b45,0x12e0b53}, {0x12e8480,0x12e8b62}, {0x12f1cc0,0x12f1ef7},
  {0x12f42d0,0x12f514a}, {0x12f5310,0x12f5a08}, {0x12f8e60,0x12f95e3}, {0x13007d0,0x1301901},
  {0x1304810,0x130692c}, {0x13069c0,0x13069da}, {0x13069da,0x1306a03}, {0x1306a03,0x1306a65},
  {0x1306a65,0x1306a7b}, {0x1306a7b,0x1306ab1}, {0x1306bf0,0x130714a}, {0x1314fc0,0x13156d4},
  {0x1318100,0x1318ad1}, {0x1318c70,0x1318d18}, {0x1320710,0x132071b}, {0x132071b,0x13207c7},
  {0x13207c7,0x13207f8}, {0x13207f8,0x1320974}, {0x1320974,0x1320979}, {0x1320979,0x13209e0},
  {0x13209e0,0x13209f0}, {0x1321110,0x1321e2f}, {0x13247e0,0x132480d}, {0x132480d,0x1324ce6},
  {0x1324ce6,0x1324cf1}, {0x1325a80,0x1325cf5}, {0x132e7d0,0x132ef32}, {0x1333ad0,0x1333b49},
  {0x1333b49,0x1333d7f}, {0x1333d7f,0x1333e03}, {0x133e2c0,0x133e766}, {0x134bc70,0x134be10},
  {0x13504b0,0x1350646}, {0x1351740,0x13517c5}, {0x1357ad0,0x135822a}, {0x135ee70,0x135f0a1},
  {0x135fef0,0x1360493}, {0x1361880,0x1361962}, {0x1367010,0x136728c}, {0x13fbf60,0x13fc0b1},
  {0x14c8fd0,0x14c900e}, {0x14c900e,0x14c90ec}, {0x14c90ec,0x14c90f0}, {0x150c230,0x150c3bd},
  {0x150fe90,0x150fffd}, {0x1510000,0x1510160}, {0x1510bd0,0x1510c34}, {0x1510c34,0x1510cf5},
  {0x1510cf5,0x1510d09}, {0x1510d10,0x1510d69}, {0x1510d69,0x1510e1e}, {0x1510e1e,0x1510e2c},
  {0x15120d0,0x151230b}, {0x1512d70,0x1512f6d}, {0x151c470,0x151c4ce}, {0x151c4ce,0x151c5d4},
  {0x151c5d4,0x151c5d8}, {0x151e090,0x151e337}, {0x15251e0,0x1526f67}, {0x153d440,0x153dd84},
  {0x15416b0,0x1542284}, {0x15481b0,0x15481f6}, {0x15481f6,0x1548314}, {0x1548314,0x1548318},
  {0x157f1a0,0x157f319}, {0x158f420,0x158f86f}, {0x2199c00,0x2199e85}, {0x2199e90,0x219a12c},
  {0x219a130,0x219a3d0}
};
#define TODATE_VA 0x1415765f2ull          /* mov eax, [rdx + today's date] (0x1415765e0) */
static uint32_t g_todate;                 /* block offset of today's date, 0 = unknown (rule off) */
static volatile LONG g_today_hi;
static int __attribute__((noinline)) today_site(void)
{
  void* fr[2] = {0};
  USHORT k = RtlCaptureStackBackTrace(2, 2, fr, 0);   /* past today_site and m_lookup */
  for (int j = 0; j < k; j++) {
    uintptr_t v = (uintptr_t)fr[j];
    if (v < g_exe || v >= g_exe + 0x8000000) continue;
    uint32_t r = (uint32_t)(v - g_exe);
    int lo = 0, hi = (int)(sizeof TODAY_FNS / sizeof *TODAY_FNS) - 1;
    while (lo <= hi) {
      int m = (lo + hi) / 2;
      if (r < TODAY_FNS[m].b) hi = m - 1; else if (r >= TODAY_FNS[m].e) lo = m + 1; else return 1;
    }
  }
  return 0;
}

/* 1 = a user site, 2 = a site of the Schedule builder's day loop (DAY_SITES), 3 CUR_PAGE_SITES,
 * 4 CUR_SITES, 5 the Calendrier's lookup (PICK_FROM), 6 the matchday page's (PICK_PAGE), 0 = none */
static int __attribute__((noinline)) user_site(void)
{
  void* fr[3] = {0};
  USHORT k = RtlCaptureStackBackTrace(2, 3, fr, 0);   /* past user_site and m_lookup */
  for (int j = 0; j < k; j++) {
    uint64_t v = (uint64_t)(uintptr_t)fr[j];
    if (v >= g_exe && v < g_exe + 0x8000000) v = v - g_exe + EXE_VA;
    for (unsigned s = 0; s < sizeof USER_SITES / sizeof *USER_SITES; s++) if (v == USER_SITES[s]) return 1;
    for (unsigned s = 0; s < sizeof DAY_SITES / sizeof *DAY_SITES; s++) if (v == DAY_SITES[s]) return 2;
    for (unsigned s = 0; s < sizeof CUR_PAGE_SITES / sizeof *CUR_PAGE_SITES; s++) if (v == CUR_PAGE_SITES[s]) return 3;
    for (unsigned s = 0; s < sizeof CUR_SITES / sizeof *CUR_SITES; s++) if (v == CUR_SITES[s]) return 4;
    if (v == g_pick_ret[0]) return 5;
    for (int s = 1; s < NPICK; s++) if (v == g_pick_ret[s]) return 6;
  }
  return 0;
}

/* 0x1414bc710: rcx = block -> the record, its id written at +0; NULL when the table is full */
static uint8_t* __attribute__((ms_abi)) m_alloc(uint8_t* blk)
{
  g_blk = blk;
  uint8_t* r = 0;
  if (g_twins > 1) {                       /* wrap after g_twins ids from 65536, as a full table does */
    uint32_t w = 0x10000 + (uint32_t)g_twins < g_cap ? 0x10000 + (uint32_t)g_twins : g_cap;
    r = take(blk, 0x10000, w);
    if (!r) r = take(blk, 0, 0x10000);
    if (!r) r = take(blk, w, g_cap);
  } else if (g_twins) {
    int hi = InterlockedIncrement(&g_turn) & 1;
    r = hi ? take(blk, 0x10000, g_cap) : take(blk, 0, 0x10000);
    if (!r) r = hi ? take(blk, 0, 0x10000) : take(blk, 0x10000, g_cap);
  } else {
    r = take(blk, g_first < g_cap ? g_first : 0, g_cap);
    if (!r && g_first) {
      r = take(blk, 0, g_first < g_cap ? g_first : g_cap);
      /* B488 (16.11.2026): past first..cap the table hands out low ids, and with first 65536 a low
         id L is the twin of L + 65536 while that one lives. Twins are allowed (see M5 above), but in
         a world that should not need them they are the sign of matches made twice (a GigaPack save
         loaded before 1 August: 81 January-December leagues entered a second time). Counted only,
         for fl26match.stats; the allocation itself is what it was. */
      if (r) {
        InterlockedIncrement(&g_wrap);
        uint32_t t = *(uint32_t*)r + 0x10000;
        if (g_first >= 0x10000 && t < g_cap && *(uint32_t*)rec_at(blk, t) == t) InterlockedIncrement(&g_wrap_twin);
      }
    }
  }
  if (!r) InterlockedIncrement(&g_full);
  return r;
}

#ifdef FL26MATCH_DIAG
/* The diagnostic build (-DFL26MATCH_DIAG, B465/B470): every lookup that answers the low twin while
 * the high one is the current match (g_cur) or the user's club's match and the low one is not, with
 * both records and seven return addresses, to modules\fl26match.twinlog. At most TW_MAX lines, TW_PER
 * per caller (the first three frames), and no stack walks after TW_TRY such answers. */
#define TW_MAX 400
#define TW_PER 8
#define TW_KEYS 128
#define TW_TRY 2000000
typedef struct {
  uint32_t id, cur, club; int us;
  uint16_t comp[2]; uint32_t date[2], c0[2], c1[2];
  uint64_t ret[7];
} tw_t;
static tw_t g_tw[TW_MAX];
static volatile LONG g_tw_n, g_tw_seen, g_tw_try, g_tw_nkey;
static uint64_t g_tw_key[TW_KEYS];
static volatile LONG g_tw_cnt[TW_KEYS];
static void __attribute__((noinline)) tw_note(uint8_t* blk, const uint8_t* r, const uint8_t* h, uint32_t id, int us)
{
  uint32_t c = user_club(blk), t = id + 0x10000;
  if (!(g_cur == t || (c != 0x3fff && has_club(h, c) && !has_club(r, c)))) return;
  InterlockedIncrement(&g_tw_seen);
  if (g_tw_n >= TW_MAX || InterlockedIncrement(&g_tw_try) > TW_TRY) return;
  void* fr[7] = {0};
  USHORT k = RtlCaptureStackBackTrace(2, 7, fr, 0);   /* past tw_note and m_lookup: its caller first */
  uint64_t ret[7], key = 0;
  for (int j = 0; j < 7; j++) {
    uint64_t v = j < k ? (uint64_t)(uintptr_t)fr[j] : 0;
    ret[j] = (v >= g_exe && v < g_exe + 0x8000000) ? v - g_exe + EXE_VA : v;
    if (j < 3) key = key * 0x9E3779B97F4A7C15ull + ret[j];
  }
  int s = -1;
  for (int i = 0; i < (int)g_tw_nkey && i < TW_KEYS; i++) if (g_tw_key[i] == key) { s = i; break; }
  if (s < 0) {
    LONG i = InterlockedIncrement(&g_tw_nkey) - 1;
    if (i >= TW_KEYS) return;
    g_tw_key[i] = key; s = (int)i;
  }
  if (InterlockedIncrement(&g_tw_cnt[s]) > TW_PER) return;
  LONG n = InterlockedIncrement(&g_tw_n) - 1;
  if (n >= TW_MAX) return;
  tw_t* e = &g_tw[n];
  e->id = id; e->cur = g_cur; e->club = c; e->us = us;
  const uint8_t* p[2] = {r, h};
  for (int i = 0; i < 2; i++) {
    e->comp[i] = *(const uint16_t*)(p[i] + 4); e->date[i] = *(const uint32_t*)(p[i] + 8);
    e->c0[i] = *(const uint32_t*)(p[i] + 0x14) & 0x3fff; e->c1[i] = *(const uint32_t*)(p[i] + 0x18) & 0x3fff;
  }
  for (int j = 0; j < 7; j++) e->ret[j] = ret[j];
}
#endif

/* 0x1414bc560: rcx = block, edx = id -> its record, NULL when nobody has it */
static uint8_t* __attribute__((ms_abi, noinline)) m_lookup(uint8_t* blk, uint32_t id)
{
  g_blk = blk;
  id &= g_mask;
  if (id < g_cap && !never(id)) {
    uint8_t* r = rec_at(blk, id);
    if (*(uint32_t*)r == id) {
      uint32_t t = id + 0x10000;
      uint8_t* h = id < 0x10000 && t < g_cap && g_mask == 0xffffffffu ? rec_at(blk, t) : 0;
      if (h && *(uint32_t*)h == t) {             /* both twins live: whole low id, or a cut user one */
        InterlockedIncrement(&g_both);
        int us = user_site(), cs = 0;
#ifdef FL26MATCH_DIAG
        int us0 = us;
#endif
        if (us == 5) {                              /* the Calendrier: the user's club's twin, remembered */
          uint32_t c = user_club(blk);
          int a = has_club(r, c), b = has_club(h, c);
          if (b && !a) { g_pick = t; InterlockedIncrement(&g_pick_hi); cut_note(); return h; }
          if (a && !b) { g_pick = id; InterlockedIncrement(&g_pick_lo); InterlockedIncrement(&g_hit); return r; }
          g_pick = 0xffffffffu; InterlockedIncrement(&g_pick_amb);   /* both or neither: as before */
          us = 0;
        } else if (us == 6) {                       /* the matchday page: the twin the Calendrier took */
          if (g_pick == t) { InterlockedIncrement(&g_page_hi); cut_note(); return h; }
          if (g_pick == id) { InterlockedIncrement(&g_page_lo); InterlockedIncrement(&g_hit); return r; }
          InterlockedIncrement(&g_page_none);       /* opened from elsewhere: as before */
          us = 0;
        }
        uint32_t day = us == 2 && g_dayhook ? g_daydate : 0;
        if (day) {                                  /* the twin dated the day the page is at */
          int a = *(uint32_t*)(r + 8) == day, b = *(uint32_t*)(h + 8) == day;
          if (b && !a) { InterlockedIncrement(&g_day_hi); cut_note(); return h; }
          if (a && !b) { InterlockedIncrement(&g_day_lo); InterlockedIncrement(&g_hit); return r; }
          InterlockedIncrement(a ? &g_day_same : &g_day_none);   /* both that day: the user's, as below */
        }
        /* the day's processing may ask for the low twin itself when it is played that day too */
        if (us >= 3 && g_cur == t && (us == 3 || *(uint32_t*)(r + 8) != *(uint32_t*)(h + 8))) {
          InterlockedIncrement(&g_cur_site); cut_note(); return h;
        }
        if (us == 4) us = 0;                        /* not a page of the user's: any other word is the low id */
        if (us) {
          uint32_t c = user_club(blk);
          int a = has_club(r, c), b = has_club(h, c);
          if (a && b) InterlockedIncrement(&g_user_amb);
          if (!a && !b) InterlockedIncrement(&g_user_none);   /* not his club's schedule after all */
          if (b && !a) { InterlockedIncrement(&g_user_hi); cut_note(); return h; }
        } else if (g_cur == t && (cs = ctx_site()) != 0 &&
                   (cs == 1 || *(uint32_t*)(r + 8) != *(uint32_t*)(h + 8))) {
          /* the current match's id, read from the context (2: under the post-match thread, the
           * low twin played another day) */
          InterlockedIncrement(cs == 1 ? &g_cur_hi : &g_cur_post); cut_note(); return h;
        } else if (g_todate && *(uint32_t*)(h + 8) == *(uint32_t*)(blk + g_todate) &&
                   *(uint32_t*)(r + 8) != *(uint32_t*)(blk + g_todate) && today_site()) {
          InterlockedIncrement(&g_today_hi); cut_note(); return h;   /* today's list: today's twin */
        } else if (g_cur == id) InterlockedIncrement(&g_cur_low);
        else if (g_sched) { uint32_t c = user_club(blk); if (c != 0x3fff && has_club(h, c) && !has_club(r, c)) amb_note(); }
#ifdef FL26MATCH_DIAG
        tw_note(blk, r, h, id, us0);
#endif
      }
      InterlockedIncrement(&g_hit); return r;
    }
  }
  if ((id & 0xffff) == 0xffff) { InterlockedIncrement(&g_none); return 0; }
  if (g_first >= 0x10000 || g_twins) {          /* M4: an id cut to 16 bits on its way here */
    uint32_t i = (id & 0xffff) + 0x10000;
    uint8_t* r = i < g_cap ? rec_at(blk, i) : 0;
    if (r && *(uint32_t*)r == i) { cut_note(); return r; }
    r = rec_at(blk, id & 0xffff);               /* junk above bit 15 of a low id */
    if (id > 0xffff && *(uint32_t*)r == (id & 0xffff)) { InterlockedIncrement(&g_hit); return r; }
  }
  for (uint32_t i = 0; i < g_cap; i++) {        /* a record that is not at its own index */
    uint8_t* r = rec_at(blk, i);
    if (*(uint32_t*)r == id) { InterlockedIncrement(&g_scan); return r; }
  }
  InterlockedIncrement(&g_miss);
  LONG n = InterlockedIncrement(&g_ring_n) - 1;
  if (n < RING) {
    void* fr[4] = {0};
    USHORT k = RtlCaptureStackBackTrace(1, 3, fr, 0);
    g_ring[n].id = id;
    for (int j = 0; j < 3; j++) g_ring[n].ret[j] = j < k ? (uint64_t)(uintptr_t)fr[j] : 0;
  }
  return 0;
}

/* 0x1414d6380: rcx = a fixture slot (or a copy of one), edx = the leg wanted (0, 1, 2) -> the id
 * of the slot's match of that leg, 0xffff when none. The slot keeps its two ids as words at +8 and
 * +0xa, and is full (0x20 bytes, notes/plan-zahtjevi-limiti-0411.md), so the id stays cut there;
 * this finds the whole one by what the slot also holds: its two clubs at +0 and +4, copies of the
 * record's +0x14 and +0x18 (0x1413f4710). A word L can be the record L or L + 65536; the one whose
 * leg matches (+4 bits 28-29, as the game checks) and whose clubs are the slot's is the match.
 * Returned in eax whole; the callers that cut it are rewritten by matchid32 (round 2). */
#define SLOTID_VA   0x1414d6380ull
#define CTXGET_VA   0x1414b6a60ull
static const unsigned char SIG_SLOT[20] = {0x48,0x89,0x5c,0x24,0x08,0x48,0x89,0x6c,0x24,0x10,0x56,0x57,0x41,0x56,
                                           0x48,0x83,0xec,0x20,0x8b,0xf2};
static uint8_t** g_ctx;                    /* the game's context pointer; its +0x48 is the edit block */
static volatile LONG g_slot, g_slot_hi, g_slot_amb, g_slot_tie, g_slot_other, g_slot_stale;

static int clubs(const uint8_t* slot, const uint8_t* r)
{
  uint32_t s0 = *(const uint32_t*)slot & 0x3fff, s1 = *(const uint32_t*)(slot + 4) & 0x3fff;
  uint32_t r0 = *(const uint32_t*)(r + 0x14) & 0x3fff, r1 = *(const uint32_t*)(r + 0x18) & 0x3fff;
  int a = (s0 == r0) + (s1 == r1), b = (s0 == r1) + (s1 == r0);
  return a > b ? a : b;
}

/* The slot names its competition too, a word at +0xc. When one twin is of that competition the
 * other is not the slot's match, whatever its leg: Bulgaria's Parva Liga (Megapack mp42, 08.11.)
 * had words 16412.. whose low twins were cup 618's first and second legs, the league's own
 * matches (leg 2) past 65535 with clubs the slot no longer matched. Asked for leg 0, the season
 * check 0x141546c70 got the cup's match, unplayed on the league's last day, so the regular phase
 * never ended and its groups stayed empty. */
static uint32_t __attribute__((ms_abi)) m_slotid(const uint8_t* slot, uint32_t leg)
{
  uint8_t* blk = *(uint8_t**)((uint8_t*)*g_ctx + 0x48);
  uint32_t sreg = *(const uint16_t*)(slot + 0xc);
  InterlockedIncrement(&g_slot);
  for (int i = 0; i < 2; i++) {
    uint32_t lo = *(const uint16_t*)(slot + 8 + 2 * i);
    if (lo == 0xffff) continue;
    int own = 0;                                 /* a twin of the slot's competition */
    for (uint32_t h = 0; h < 2 && sreg != 0xffff; h++) {
      uint32_t id = lo | h << 16;
      if (id >= g_cap) break;
      uint8_t* r = rec_at(blk, id);
      if (*(uint32_t*)r == id && *(const uint16_t*)(r + 4) == sreg) own = 1;
    }
    uint32_t best = 0xffff; int score = -1, n = 0;
    for (uint32_t h = 0; h < 2; h++) {
      uint32_t id = lo | h << 16;
      if (id >= g_cap) break;
      uint8_t* r = rec_at(blk, id);
      if (*(uint32_t*)r != id || (*(uint32_t*)(r + 4) >> 28 & 3) != leg) continue;
      if (own && *(const uint16_t*)(r + 4) != sreg) { InterlockedIncrement(&g_slot_other); continue; }
      int s = clubs(slot, r);
      /* neither twin of the slot's competition: its own match is gone (a calendar-year league's
         last season, freed at New Year, B389). The other competition's twin is the slot's match
         only with both its clubs -- Panama's round 32 got Israel's round 25 by the word alone and
         the New Year build dated it into the next season, so Israel's regular phase never ended */
      if (!own && sreg != 0xffff && *(const uint16_t*)(r + 4) != sreg && s < 2) { InterlockedIncrement(&g_slot_stale); continue; }
      n++;
      if (s > score) { score = s; best = id; }
      else if (s == score) InterlockedIncrement(&g_slot_tie);
    }
    if (n > 1) InterlockedIncrement(&g_slot_amb);
    if (best != 0xffff) {
      if (best > 0xffff) InterlockedIncrement(&g_slot_hi);
      return best;
    }
  }
  return 0xffff;
}

/* 0x1414bb950: rcx = block, rdx = a pointer to an id -> al: is it a match. The game reads a word
 * there; matchid32 (round 3) makes its callers store the whole id as a dword, but one caller sits in
 * the protector's code and still stores a word, so its upper half is whatever was on the stack. A
 * dword that names a live record is taken whole; anything else is read as the word it was. */
#define HAS_VA      0x1414bb950ull
static const unsigned char SIG_HAS[8] = {0x48,0x83,0xec,0x28,0x0f,0xb7,0x12,0xe8};
static volatile LONG g_has_word;

static uint64_t __attribute__((ms_abi)) m_has(uint8_t* blk, const uint8_t* p)
{
  uint32_t id = *(const uint32_t*)p;
  if (id > 0xffff && id < g_cap && *(uint32_t*)rec_at(blk, id) == id) return m_lookup(blk, id) != 0;
  if (id > 0xffff) InterlockedIncrement(&g_has_word);
  return m_lookup(blk, *(const uint16_t*)p) != 0;
}

/* Players past 65535 (lift16f, 06.11.). A career names a player by a key: u16 index into the
 * player array (block + 0, 0x17c a record), u16 padding the game never sets, u32 player id (the
 * record holds its own key at +0x2c, so its id at +0x30). The builders (0x140af2dd1 and ~20
 * alike) cut an index past 0xffff to 0xffff, so a player at index >= 65535 has the word 0xffff
 * in his key, and the game's ways from a key to a record cannot find him:
 *   0x1414bca10  key -> record, trusts the word below a bound and checks the id;
 *   0x1414bb2a0  the lookup 921 calls go through: in a career (mode 2) it takes the word on trust,
 *                otherwise it calls the binary search 0x1414b80f0 (so does 0x1414bc9a0);
 *   0x141502e60  squad slot -> record, NULL for slot 0xff ("no candidate"), dereferenced on the
 *                first match day at 0x1415032f0.
 * What this does, the same bytes lift16f.py wrote into the running game:
 *   - 0x1414bca10 jumps to pl_key: the word, then the word + 0x10000, + 0x20000 ... below the
 *     cap; the word 0xffff goes by id through a map id -> index + 1 (0x40000 dwords, ids below
 *     0x40000, filled by a full scan the first time an id is asked for and checked by id every
 *     time); anything else not found by its word goes by id as well, map first.  15.11.2026: a GigaPack
 *     career made 69228 such scans while it was created, one for each player past 65534 (12 s
 *     of the loading screen), because a scan kept the one id it was asked for.  The 1st, 2nd,
 *     4th, 8th ... scan now also puts every record's id in the map (pl_fill; the lowest index
 *     of an id, as a scan finds), so the players after it are map hits;
 *   - the mode-2 block of 0x1414bb2a0 (0x1414bb2ce) trusts the word as the game does (the loader
 *     asks for a slot before its id is in it); only the word 0xffff goes through the int3 pad
 *     0x1414bb344 to 0x1414bca10, and back to the block's "no player" when that finds nobody;
 *   - the two calls of the binary search (0x1414bc9e1, 0x1414bb30d) go through a wrapper at
 *     0x1414bca20 (free since 0x1414bca10 is a jump), which jumps to pl_bs: with the word 0xffff,
 *     pl_key first and the binary search only when that finds nobody (the search came first,
 *     and while a GigaPack career was created it missed 13.6 million times before the map was
 *     asked -- 15 % of the creating thread); with any other word the record the map has for
 *     the id is the answer when it lies in the range searched and carries the whole key (word
 *     and id) -- in a sorted range that is the record the search would stop at -- and the
 *     game's search otherwise, whose answer is put in the map (16.11.2026: with the first part
 *     in, the search was still a fifth of the creating thread);
 *   - 0x14126cfde, before the loop at 0x14126cff0 that walks every player from a start index
 *     for a key (word and id) and only wants to know that somebody has it (another fifth of
 *     the creating thread): a cave asks the map first; a record at or past the start index,
 *     below the count, carrying the key, goes straight to the loop's "found" (0x14126d02d);
 *     anything else, and the id 0 (the loop then looks for a free record), walks as before;
 *   - the line-up guard (vmican's fl26playercap.lua): 0x141502e66's jge goes to the int3 pad
 *     0x141502eaa and on to a cave near the exe that counts and answers slot 0's record.
 * The cap (records searched) is the set's search bound in 0x1414bc0a0 (mov r10d, cap at
 * 0x1414bc0d5), or the one fl26match.lua passes. The stats, as lift16f's STATS (+0 ... +0x38): */
#define PL_REC        0x17cu
#define PL_KEY_VA     0x1414bca10ull   /* key -> record; its body from +0x10 is free once it jumps */
#define PL_KEY_WORD   0x1414bca51ull   /* movzx eax, dx in it */
#define PL_NONE_CMP   0x1414bca3aull   /* cmp word [rip + none], dx in it */
#define PL_NONE_VA    0x14351ae30ull   /* the game's "no player" key (word, pad, id) */
#define PL_WRAP_VA    0x1414bca20ull
#define PL_LIN_VA     0x14126cfdeull   /* mov r13d, [rsp + 0x4c]; 13 bytes of nop; the loop at 0x14126cff0 */
#define PL_LIN_LOOP   0x14126cff0ull
#define PL_LIN_FOUND  0x14126d02dull
#define PL_WRAP_END   0x1414bca80ull
#define PL_BSEARCH_VA 0x1414b80f0ull
#define PL_MODE2_VA   0x1414bb2ceull   /* mov eax, bound; cmp dx, ax; ja +0x2e7; movzx eax, dx ... */
#define PL_MODE2_END  0x1414bb2e7ull   /* lea rax, [rcx + "no player"]: the block's miss */
#define PL_MODE2_WORD 0x1414bb2d8ull
#define PL_PAD2_VA    0x1414bb344ull   /* 12 int3 after 0x1414bb2a0 */
#define PL_CALL1_VA   0x1414bc9e1ull   /* call 0x1414b80f0 in 0x1414bc9a0 */
#define PL_CALL2_VA   0x1414bb30dull   /* call 0x1414b80f0 in 0x1414bb2a0 */
#define PL_CAP_VA     0x1414bc0d5ull   /* mov r10d, cap (the search bound) */
#define PL_GUARD_VA   0x141502e63ull   /* cmp edx, 0x28; jge 0x141502e8e (in 0x141502e60) */
#define PL_GPAD_VA    0x141502eaaull   /* 6 int3 after 0x141502e60 */
#define PL_MAP_N      0x40000u
enum { PS_STEPS, PS_SCAN, PS_MISS, PS_LASTMISS, PS_SCANKEY, PS_SCANAT, PS_MAP, PS_GUARD };
/* +0 hits past the first word step, +8 full-scan hits, +0x10 misses, +0x18 the last missed key
 * (word | id << 32), +0x20 the last scanned key, +0x28 the index the scan found it at, +0x30 map
 * hits, +0x38 line-up guard hits */
static volatile LONG64 g_pl_st[8];
static volatile LONG64 g_pl_x[3];        /* the search answered by the map, asked of the game; the walk answered by the map */
typedef uint8_t* (__attribute__((ms_abi)) *pl_bs_t)(uint8_t*, uint8_t*, uint64_t);
static pl_bs_t g_pl_bs;                   /* the game's 0x1414b80f0 */
static uint32_t g_pl_ix[PL_MAP_N];        /* id -> index + 1, 0 = not seen yet */
static uint32_t g_pl_cap;
static const uint8_t* g_pl_none;
static uint8_t* g_pl_cave;                /* the near page: pl_key's entry and the guard */

/* lift16f's bytes, assembled at their own addresses (keystone, scratchpad p1ks.py) */
static const unsigned char PL_MODE2[21] = {      /* at 0x1414bb2ce, then nop to 0x1414bb2e7 */
  0x66,0x83,0xfa,0xff,                          /* cmp dx, 0xffff */
  0x74,0x70,                                    /* je 0x1414bb344 */
  0x0f,0xb7,0xc2,                               /* movzx eax, dx */
  0x48,0x69,0xc0,0x7c,0x01,0x00,0x00,           /* imul rax, rax, 0x17c */
  0x48,0x01,0xc8,                               /* add rax, rcx */
  0xeb,0x5b };                                  /* jmp 0x1414bb33e (the epilogue) */
static const unsigned char PL_PAD2[12] = {       /* at 0x1414bb344 */
  0xe8,0xc7,0x16,0x00,0x00,                     /* call 0x1414bca10 (rcx kept, see pl_entry) */
  0x48,0x85,0xc0,                               /* test rax, rax */
  0x75,0xf0,                                    /* jne 0x1414bb33e */
  0xeb,0x97 };                                  /* jmp 0x1414bb2e7 */

static inline uint8_t* pl_rec(uint8_t* arr, uint32_t i) { return arr + (size_t)i * PL_REC; }
static inline uint32_t pl_id(const uint8_t* r) { return *(const uint32_t*)(r + 0x30); }

/* every record's id into the map, the lowest index of an id last so that it is the one kept */
static void pl_fill(uint8_t* arr)
{
  for (uint32_t i = g_pl_cap; i-- > 0; ) {
    uint32_t id = pl_id(pl_rec(arr, i));
    if (id && id < PL_MAP_N) g_pl_ix[id] = i + 1;
  }
}

/* 0x1414bca10: rcx = the player array, rdx = a key -> its record, NULL when nobody has it */
static uint8_t* __attribute__((ms_abi)) pl_key(uint8_t* arr, uint64_t key)
{
  uint32_t id = (uint32_t)(key >> 32), w = (uint16_t)key;
  if (!id) return 0;
  if (*(const uint16_t*)g_pl_none == w && *(const uint32_t*)(g_pl_none + 4) == id) return 0;
  if (w != 0xffff)
    for (uint32_t i = w; i < g_pl_cap; i += 0x10000) {
      uint8_t* r = pl_rec(arr, i);
      if (pl_id(r) == id) { if (i != w) InterlockedIncrement64(&g_pl_st[PS_STEPS]); return r; }
    }
  {                                         /* a player past 65534, or a word that is not his: by id */
    uint32_t v = id < PL_MAP_N ? g_pl_ix[id] : 0;
    if (v && v <= g_pl_cap) {
      uint8_t* r = pl_rec(arr, v - 1);
      if (pl_id(r) == id) { InterlockedIncrement64(&g_pl_st[PS_MAP]); return r; }
    }
  }
  for (uint32_t i = 0; i < g_pl_cap; i++) {
    uint8_t* r = pl_rec(arr, i);
    if (pl_id(r) != id) continue;
    LONG64 n = InterlockedIncrement64(&g_pl_st[PS_SCAN]);
    g_pl_st[PS_SCANAT] = i;
    if (id < PL_MAP_N) g_pl_ix[id] = i + 1;
    if (!(n & (n - 1))) pl_fill(arr);
    g_pl_st[PS_SCANKEY] = (LONG64)(w | (uint64_t)id << 32);
    return r;
  }
  InterlockedIncrement64(&g_pl_st[PS_MISS]);
  g_pl_st[PS_LASTMISS] = (LONG64)(w | (uint64_t)id << 32);
  return 0;
}

/* 0x1414bca20, in place of the two calls of the binary search: first, last, key -> record or NULL */
static uint8_t* __attribute__((ms_abi)) pl_bs(uint8_t* first, uint8_t* last, uint64_t key)
{
  uint32_t id = (uint32_t)(key >> 32);
  if ((uint16_t)key == 0xffff) {
    uint8_t* r = pl_key(first, key);
    return r ? r : g_pl_bs(first, last, key);
  }
  if (id && id < PL_MAP_N) {
    uint32_t v = g_pl_ix[id];
    if (v) {
      uint8_t* r = pl_rec(first, v - 1);
      if (r < last && ((*(const uint64_t*)(r + 0x2c) ^ key) & 0xffffffff0000ffffull) == 0) {
        InterlockedIncrement64(&g_pl_x[0]);
        return r;
      }
    }
  }
  uint8_t* r = g_pl_bs(first, last, key);
  InterlockedIncrement64(&g_pl_x[1]);
  if (r && id && id < PL_MAP_N && r >= first && r < last && (size_t)(r - first) % PL_REC == 0 && pl_id(r) == id)
    g_pl_ix[id] = (uint32_t)((size_t)(r - first) / PL_REC) + 1;
  return r;
}

/* The near page: rel32 from the int3 pad 0x141502eaa has to reach it. lift16f's addresses
 * first (past the image, 0x15b9a6000), then upwards from the image's end in 1 MB steps. */
static uint8_t* near_page(uintptr_t from)
{
  static const uint64_t PREF[] = {0x15f000000ull, 0x161000000ull, 0x171000000ull, 0x15e100000ull};
  const IMAGE_NT_HEADERS64* nt = (const IMAGE_NT_HEADERS64*)(g_exe + ((const IMAGE_DOS_HEADER*)g_exe)->e_lfanew);
  uintptr_t end = (g_exe + nt->OptionalHeader.SizeOfImage + 0xfffff) & ~(uintptr_t)0xfffff;
  for (int k = 0; k < 4 + 1024; k++) {
    uintptr_t at = k < 4 ? g_exe + (uintptr_t)(PREF[k] - EXE_VA) : end + (uintptr_t)(k - 4) * 0x100000;
    uint8_t* p = (uint8_t*)VirtualAlloc((void*)at, 0x1000, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
    if (!p) continue;
    int64_t d = (int64_t)((uintptr_t)p - from);
    if (d < 0x7fff0000ll && d > -0x7fff0000ll) return p;
    VirtualFree(p, 0, MEM_RELEASE);
  }
  return 0;
}

static int put(uintptr_t at, const void* b, size_t n)
{
  DWORD old;
  if (!VirtualProtect((void*)at, n, PAGE_EXECUTE_READWRITE, &old)) return 0;
  for (size_t i = 0; i < n; i++) ((unsigned char*)at)[i] = ((const unsigned char*)b)[i];
  VirtualProtect((void*)at, n, old, &old);
  FlushInstructionCache(GetCurrentProcess(), (void*)at, n);
  return 1;
}

static int is(uintptr_t at, const char* hex)
{
  for (const unsigned char* p = (const unsigned char*)at; hex[0] && hex[1]; hex += 2, p++) {
    int hi = hex[0] <= '9' ? hex[0] - '0' : hex[0] - 'a' + 10, lo = hex[1] <= '9' ? hex[1] - '0' : hex[1] - 'a' + 10;
    if (*p != (hi << 4 | lo)) return 0;
  }
  return 1;
}
static int int3s(uintptr_t at, int n) { for (int i = 0; i < n; i++) if (((unsigned char*)at)[i] != 0xcc) return 0; return 1; }
static int calls(uintptr_t at, uintptr_t to) { return *(unsigned char*)at == 0xe8 && at + 5 + *(int32_t*)(at + 1) == to; }

/* cap: the records searched, 0 = the set's search bound. Returns 0, 2 a signature that is not the
 * game's (or already hooked), 3 cap past the set's bound, 4 no memory near the exe, 5 VirtualProtect.
 * Reads the bound from fl26caps' patched code, so it must run after fl26caps. */
__declspec(dllexport) int fl26_player_install(uint32_t cap)
{
  if (!g_exe) g_exe = (uintptr_t)GetModuleHandleA(0);
#define AT(va) (g_exe + (uintptr_t)((va) - EXE_VA))
  uintptr_t key = AT(PL_KEY_VA), wrap = AT(PL_WRAP_VA), bs = AT(PL_BSEARCH_VA);
  uintptr_t c1 = AT(PL_CALL1_VA), c2 = AT(PL_CALL2_VA), g0 = AT(PL_GUARD_VA), gpad = AT(PL_GPAD_VA);
  /* lift16f's checks, and the ones the bytes below rely on */
  if (*(unsigned char*)key != 0xb8 || !is(AT(PL_KEY_WORD), "0fb7c2")) return 2;
  if (!is(AT(PL_MODE2_VA), "b8") || !is(AT(PL_MODE2_WORD), "0fb7c2") || !int3s(AT(PL_PAD2_VA), 12)) return 2;
  if (!calls(c1, bs) || !calls(c2, bs)) return 2;
  if (!is(g0, "83fa287d26") || !int3s(gpad, 6)) return 2;
  uintptr_t nc = AT(PL_NONE_CMP);
  if (!is(nc, "663915") || nc + 7 + *(int32_t*)(nc + 3) != AT(PL_NONE_VA)) return 2;
  if (!is(AT(PL_CAP_VA), "41ba")) return 2;
  int lin = is(AT(PL_LIN_VA), "448b6c244c0f1f4000660f1f840000000000") && is(AT(PL_LIN_LOOP), "8bc24869c07c010000488b44382c4585ed")
            && is(AT(PL_LIN_FOUND), "488bd3488bcfe8");
  uint32_t bound = *(uint32_t*)(AT(PL_CAP_VA) + 2);
  if (cap > bound) return 3;
  g_pl_cap = cap ? cap : bound;
  g_pl_none = (const uint8_t*)AT(PL_NONE_VA);

  uint8_t* p = near_page(gpad + 5);
  if (!p) return 4;
  /* +0 pl_entry: 0x1414bca10's callers keep rcx (0x1414bb344's miss goes to the block's
   * lea rax, [rcx + ...]) and lift16f's cave left r9-r11 alone, so they are kept around the C */
  static const unsigned char entry[] = {
    0x51, 0x41,0x51, 0x41,0x52, 0x41,0x53,      /* push rcx; push r9; push r10; push r11 */
    0x48,0x83,0xec,0x28,                        /* sub rsp, 0x28 (home space, rsp 16-aligned) */
    0x48,0xb8, 0,0,0,0,0,0,0,0,                 /* mov rax, pl_key */
    0xff,0xd0,                                  /* call rax */
    0x48,0x83,0xc4,0x28,                        /* add rsp, 0x28 */
    0x41,0x5b, 0x41,0x5a, 0x41,0x59, 0x59,      /* pop r11; pop r10; pop r9; pop rcx */
    0xc3 };
  /* +0x40 the guard: count, then slot 0's record (r8 = the slots, as at 0x141502ea2) */
  static const unsigned char guard[] = {
    0x50,                                       /* push rax */
    0x48,0xb8, 0,0,0,0,0,0,0,0,                 /* mov rax, &g_pl_st[PS_GUARD] */
    0xf0,0x48,0xff,0x00,                        /* lock inc qword [rax] */
    0x58,                                       /* pop rax */
    0x49,0x8d,0x40,0x08,                        /* lea rax, [r8 + 8] */
    0xc3 };
  /* +0x80 the walk at 0x14126cff0: edx start index, r8d count, rdi the players, bx / r13d the key */
  static const unsigned char walk[] = {
    0x44,0x8b,0x6c,0x24,0x4c,                   /* mov r13d, [rsp + 0x4c] (the instruction moved here) */
    0x45,0x85,0xed, 0x74,0x5f,                  /* test r13d, r13d; jz out */
    0x41,0x81,0xfd,0x00,0x00,0x04,0x00, 0x73,0x56,   /* cmp r13d, PL_MAP_N; jae out */
    0x51,                                       /* push rcx */
    0x48,0xb8, 0,0,0,0,0,0,0,0,                 /* mov rax, g_pl_ix */
    0x42,0x8b,0x04,0xa8,                        /* mov eax, [rax + r13*4] */
    0x85,0xc0, 0x74,0x42,                       /* test eax, eax; jz outp */
    0xff,0xc8,                                  /* dec eax */
    0x39,0xd0, 0x72,0x3c,                       /* cmp eax, edx; jb outp */
    0x44,0x39,0xc0, 0x73,0x37,                  /* cmp eax, r8d; jae outp */
    0x48,0x69,0xc8,0x7c,0x01,0x00,0x00,         /* imul rcx, rax, 0x17c */
    0x48,0x8b,0x4c,0x39,0x2c,                   /* mov rcx, [rcx + rdi + 0x2c] */
    0x66,0x39,0xd9, 0x75,0x26,                  /* cmp cx, bx; jne outp */
    0x48,0xc1,0xe9,0x20,                        /* shr rcx, 32 */
    0x44,0x39,0xe9, 0x75,0x1d,                  /* cmp ecx, r13d; jne outp */
    0x48,0xb9, 0,0,0,0,0,0,0,0,                 /* mov rcx, &g_pl_x[2] */
    0xf0,0x48,0xff,0x01,                        /* lock inc qword [rcx] */
    0x59,                                       /* pop rcx */
    0xff,0x25,0,0,0,0, 0,0,0,0,0,0,0,0,         /* jmp 0x14126d02d */
    0x59,                                       /* outp: pop rcx */
    0xff,0x25,0,0,0,0, 0,0,0,0,0,0,0,0 };       /* out: jmp 0x14126cff0 */
  for (unsigned i = 0; i < sizeof walk; i++) p[0x80 + i] = walk[i];
  *(uint64_t*)(p + 0x80 + 22) = (uint64_t)(uintptr_t)g_pl_ix;
  *(uint64_t*)(p + 0x80 + 77) = (uint64_t)(uintptr_t)&g_pl_x[2];
  *(uint64_t*)(p + 0x80 + 96) = (uint64_t)AT(PL_LIN_FOUND);
  *(uint64_t*)(p + 0x80 + 111) = (uint64_t)AT(PL_LIN_LOOP);
  g_pl_bs = (pl_bs_t)bs;
  for (unsigned i = 0; i < sizeof entry; i++) p[i] = entry[i];
  *(uint64_t*)(p + 13) = (uint64_t)(uintptr_t)pl_key;
  for (unsigned i = 0; i < sizeof guard; i++) p[0x40 + i] = guard[i];
  *(uint64_t*)(p + 0x40 + 3) = (uint64_t)(uintptr_t)&g_pl_st[PS_GUARD];
  FlushInstructionCache(GetCurrentProcess(), p, 0x1000);
  g_pl_cave = p;

  unsigned char nops[PL_MODE2_END - PL_MODE2_VA];
  for (unsigned i = 0; i < sizeof nops; i++) nops[i] = i < sizeof PL_MODE2 ? PL_MODE2[i] : 0x90;
  unsigned char cw[5] = {0xe8}, gj[5] = {0xe9}, jge[2] = {0x7d, (unsigned char)(gpad - (g0 + 5))};
  *(int32_t*)(gj + 1) = (int32_t)((intptr_t)(p + 0x40) - (intptr_t)(gpad + 5));
  if (!jmp_to(key, p)) return 5;                                   /* 14 bytes, up to +0x0e */
  if (!jmp_to(wrap, (void*)pl_bs)) return 5;                         /* 14 bytes, up to 0x1414bca2e */
  if (lin && !jmp_to(AT(PL_LIN_VA), p + 0x80)) return 5;           /* 14 of the 18 bytes before the loop */
  *(int32_t*)(cw + 1) = (int32_t)(wrap - (c1 + 5)); if (!put(c1, cw, 5)) return 5;
  *(int32_t*)(cw + 1) = (int32_t)(wrap - (c2 + 5)); if (!put(c2, cw, 5)) return 5;
  if (!put(AT(PL_PAD2_VA), PL_PAD2, sizeof PL_PAD2)) return 5;
  if (!put(AT(PL_MODE2_VA), nops, sizeof nops)) return 5;
  if (!put(gpad, gj, 5)) return 5;
  if (!put(g0 + 3, jge, 2)) return 5;
#undef AT
  return 0;
}

/* out: lift16f's STATS (PS_*), then the cap and the near page; returns 0 before the install */
__declspec(dllexport) int fl26_player_stats(uint64_t* out)
{
  for (int i = 0; i < 8; i++) out[i] = (uint64_t)g_pl_st[i];
  out[8] = g_pl_cap; out[9] = (uint64_t)(uintptr_t)g_pl_cave;
  return g_pl_cave != 0;
}

static int jmp_to(uintptr_t site, void* to)
{
  DWORD old;
  unsigned char* s = (unsigned char*)site;
  if (!VirtualProtect(s, 14, PAGE_EXECUTE_READWRITE, &old)) return 0;
  s[0] = 0xFF; s[1] = 0x25; *(uint32_t*)(s + 2) = 0; *(uint64_t*)(s + 6) = (uint64_t)(uintptr_t)to;
  VirtualProtect(s, 14, old, &old);
  FlushInstructionCache(GetCurrentProcess(), s, 14);
  return 1;
}

/* the result page's id reads as dwords (PAGE_WIDE); not fatal: a site left alone shows low twins */
static void page_widen(void)
{
  for (int i = 0; i < NWIDE; i++) {
    unsigned char* at = (unsigned char*)(g_exe + (uintptr_t)(PAGE_WIDE[i].va - EXE_VA));
    for (unsigned k = 0; k < PAGE_WIDE[i].n; k++) g_wide_seen[i][k] = at[k];
    g_wide_st[i] = wide_state(at, &PAGE_WIDE[i]);
    if (g_wide_st[i] == 1 && !put((uintptr_t)at, PAGE_WIDE[i].neu, PAGE_WIDE[i].n)) g_wide_st[i] = 0;
  }
}

/* the twins sweep's id reads as dwords (TWIN_WIDE); the same rules as page_widen */
static void twin_widen(void)
{
  for (int i = 0; i < NTWIN; i++) {
    unsigned char* at = (unsigned char*)(g_exe + (uintptr_t)(TWIN_WIDE[i].va - EXE_VA));
    for (unsigned k = 0; k < TWIN_WIDE[i].n; k++) g_twin_seen[i][k] = at[k];
    g_twin_st[i] = wide_state(at, &TWIN_WIDE[i]);
    if (g_twin_st[i] == 1 && !put((uintptr_t)at, TWIN_WIDE[i].neu, TWIN_WIDE[i].n)) g_twin_st[i] = 0;
  }
}

/* the result rows' score reads as dwords (SCORE_WIDE); the same rules as page_widen */
static void score_widen(void)
{
  for (int i = 0; i < NSCORE; i++) {
    unsigned char* at = (unsigned char*)(g_exe + (uintptr_t)(SCORE_WIDE[i].va - EXE_VA));
    for (unsigned k = 0; k < SCORE_WIDE[i].n; k++) g_score_seen[i][k] = at[k];
    g_score_st[i] = wide_state(at, &SCORE_WIDE[i]);
    if (g_score_st[i] == 1 && !put((uintptr_t)at, SCORE_WIDE[i].neu, SCORE_WIDE[i].n)) g_score_st[i] = 0;
  }
  for (int i = 0; i < NLIST; i++) {          /* the rows' test (LIST_WIDE), the same rules */
    unsigned char* at = (unsigned char*)(g_exe + (uintptr_t)(LIST_WIDE[i].va - EXE_VA));
    for (unsigned k = 0; k < LIST_WIDE[i].n; k++) g_list_seen[i][k] = at[k];
    g_list_st[i] = wide_state(at, &LIST_WIDE[i]);
    if (g_list_st[i] == 1 && !put((uintptr_t)at, LIST_WIDE[i].neu, LIST_WIDE[i].n)) g_list_st[i] = 0;
  }
}

/* the Calendrier's and the matchday page's lookups (PICK): a return address is used only when the read
 * and `call 0x1414bb280` before it are the shipped bytes; returns how many are on. Nothing is written. */
static int pick_check(void)
{
  int on = 0;
  for (int i = 0; i < NPICK; i++) {
    uintptr_t at = g_exe + (uintptr_t)(PICK[i].at - EXE_VA), ret = g_exe + (uintptr_t)(PICK[i].ret - EXE_VA);
    int ok = is(at, PICK[i].hex) && calls(ret - 5, g_exe + (uintptr_t)(WRAP_VA - EXE_VA));
    g_pick_ret[i] = ok ? PICK[i].ret : 0;
    on += ok;
  }
  return on;
}
static int g_pick_on;

/* first: the lowest index handed out first (0, or 65536 for M4); mask: 0xffff until the id
 * travels 32-bit everywhere. Returns 0, or 2/3 a signature that is not the game's, 4 no room,
 * 5 VirtualProtect. Reads the table's place and size from fl26caps' patched code, so it must
 * run after fl26caps. */
__declspec(dllexport) int fl26_match_install(uint32_t first, uint32_t mask)
{
  g_exe = (uintptr_t)GetModuleHandleA(0);
  unsigned char* a = (unsigned char*)(g_exe + (ALLOC_VA - EXE_VA));
  unsigned char* l = (unsigned char*)(g_exe + (LOOKUP_VA - EXE_VA));
  for (int i = 0; i < 14; i++) if (a[i] != SIG_ALLOC[i]) return 2;
  for (int i = 0; i < 7; i++) if (l[i] != SIG_LOOK_A[i]) return 3;
  for (int i = 0; i < 3; i++) if (l[11 + i] != SIG_LOOK_B[i]) return 3;
  /* lea rax, [rcx + table] at +0x21 of the lookup; cmp eax, cap at +0x26 of the allocator */
  if (l[0x21] != 0x48 || l[0x22] != 0x8d || l[0x23] != 0x81 || a[0x26] != 0x3d) return 3;
  g_off = *(uint32_t*)(l + 0x24);
  g_cap = *(uint32_t*)(a + 0x27);
  if (first >= g_cap) return 4;
  /* the slot reader goes with the 32-bit mask only: its callers' widening is in that set */
  unsigned char* s = (unsigned char*)(g_exe + (SLOTID_VA - EXE_VA));
  unsigned char* c = (unsigned char*)(g_exe + (CTXGET_VA - EXE_VA));
  if (mask == 0xffffffffu) {
    for (int i = 0; i < 20; i++) if (s[i] != SIG_SLOT[i]) return 6;
    if (c[0] != 0x48 || c[1] != 0x8b || c[2] != 0x05 || c[7] != 0xc3) return 6;
    g_ctx = (uint8_t**)(c + 7 + *(int32_t*)(c + 3));
    unsigned char* h = (unsigned char*)(g_exe + (HAS_VA - EXE_VA));
    for (int i = 0; i < 8; i++) if (h[i] != SIG_HAS[i]) return 6;
    unsigned char* q = (unsigned char*)(g_exe + (SCHED_LEA_VA - EXE_VA));
    if (q[0] == 0x49 && q[1] == 0x8d && q[2] == 0xb7) g_sched = *(uint32_t*)(q + 3);
    unsigned char* u = (unsigned char*)(g_exe + (USER_LEA_VA - EXE_VA));
    if (u[0] == 0x48 && u[1] == 0x8d && u[2] == 0x8e) g_user_off = *(uint32_t*)(u + 3);
    unsigned char* d = (unsigned char*)(g_exe + (TODATE_VA - EXE_VA));   /* mov eax, [rdx+disp32] */
    if (d[0] == 0x8b && d[1] == 0x82 && d[6] == 0x89 && d[7] == 0x03) g_todate = *(uint32_t*)(d + 2);
  }
  unsigned char* x = (unsigned char*)(g_exe + (SETCTX_VA - EXE_VA));
  int setctx = 0;
  if (mask == 0xffffffffu) {
    setctx = 1;
    for (int i = 0; i < 15; i++) if (x[i] != SIG_SETCTX[i]) setctx = 0;   /* not fatal: no ctx rule */
  }
  if (setctx) {   /* trampoline: the 15 bytes the jmp covers, then back to +15 */
    unsigned char* t = (unsigned char*)VirtualAlloc(0, 64, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
    if (!t) return 5;
    for (int i = 0; i < 15; i++) t[i] = x[i];
    t[15] = 0xFF; t[16] = 0x25; *(uint32_t*)(t + 17) = 0; *(uint64_t*)(t + 21) = (uint64_t)(uintptr_t)(x + 15);
    g_setctx = (void (__attribute__((ms_abi)) *)(const uint8_t*))(void*)t;
  }
  g_first = first; g_mask = mask;
  if (!jmp_to((uintptr_t)a, (void*)m_alloc) || !jmp_to((uintptr_t)l, (void*)m_lookup)) return 5;
  if (mask == 0xffffffffu && (!jmp_to((uintptr_t)s, (void*)m_slotid)
                              || !jmp_to((uintptr_t)(g_exe + (HAS_VA - EXE_VA)), (void*)m_has))) return 5;
  if (setctx && !jmp_to((uintptr_t)x, (void*)m_setctx)) return 5;
  if (mask == 0xffffffffu) g_dayhook = day_hook();    /* not fatal: Be a Legend's Schedule then by club only */
  if (mask == 0xffffffffu) g_strip = strip_hook();   /* not fatal: the strip then shows low twins */
  if (mask == 0xffffffffu) page_widen();
  if (mask == 0xffffffffu) twin_widen();   /* not fatal: a site left alone answers as before */
  if (mask == 0xffffffffu) score_widen();  /* the same: a site left alone shows the low twin's score */
  if (mask == 0xffffffffu) g_pick_on = pick_check();   /* not fatal: a site left off answers as before */
  return 0;
}

/* on: hand ids out low and high in turn (the twins test); before or after install */
/* on > 1: hand ids out from 65536 for `on` matches, then from 0 -- twins as a table past 65535 makes them,
 * a match and the one `on` allocations after it (the realistic test) */
__declspec(dllexport) void fl26_match_twins(int on) { g_twins = on > 1 ? on : on ? 1 : 0; }

/* out: table offset, cap, first, mask, allocs, full, hits, scans, misses, "no match" lookups */
__declspec(dllexport) void fl26_match_stats(uint32_t* out)
{
  out[0] = g_off; out[1] = g_cap; out[2] = g_first; out[3] = g_mask;
  out[4] = (uint32_t)g_alloc; out[5] = (uint32_t)g_full; out[6] = (uint32_t)g_hit;
  out[7] = (uint32_t)g_scan; out[8] = (uint32_t)g_miss; out[9] = (uint32_t)g_none;
}

/* the first misses: id and three return addresses each, as exe offsets when they are the exe's */
__declspec(dllexport) int fl26_match_misses(uint32_t* ids, uint64_t* rets, int max)
{
  int n = g_ring_n < RING ? (int)g_ring_n : RING;
  if (n > max) n = max;
  for (int i = 0; i < n; i++) {
    ids[i] = g_ring[i].id;
    for (int j = 0; j < 3; j++) {
      uint64_t r = g_ring[i].ret[j];
      rets[i * 3 + j] = (r >= g_exe && r < g_exe + 0x8000000) ? r - g_exe + EXE_VA : r;
    }
  }
  return n;
}


/* The tracer (u32 match ids, M2): which instructions touch a storage. The writer thread finds
 * modules\fl26match.trace ("<block offset hex> <length hex> <seconds>"), puts PAGE_GUARD on
 * those pages, and a vectored handler records every instruction that reads or writes inside
 * the range (single-stepping it, then putting the guard back). After the seconds the guard
 * comes off and modules\fl26match.rips gets one line per instruction: its address, how many
 * times, whether it wrote, and the first offset into the range it touched. */
#define NRIP 16384
static char g_path[520];
typedef struct { uint64_t rip; uint32_t n, off; uint32_t wr; } rip_t;
static rip_t g_rips[NRIP];
static volatile LONG g_nrips, g_tracing, g_lost;
static uint8_t *g_lo, *g_hi;
static DWORD g_tls = TLS_OUT_OF_INDEXES;

static void note(uint64_t rip, uint8_t* a, int wr)
{
  uint32_t h = (uint32_t)((rip * 0x9E3779B97F4A7C15ull) >> 50) & (NRIP - 1);
  for (int k = 0; k < NRIP; k++, h = (h + 1) & (NRIP - 1)) {
    uint64_t have = g_rips[h].rip;
    if (have == rip) { g_rips[h].n++; g_rips[h].wr |= wr; return; }
    if (!have) {
      if (InterlockedCompareExchange64((volatile LONG64*)&g_rips[h].rip, (LONG64)rip, 0) == 0) {
        g_rips[h].n = 1; g_rips[h].off = (uint32_t)(a - g_lo); g_rips[h].wr = wr;
        InterlockedIncrement(&g_nrips); return;
      }
      if (g_rips[h].rip == rip) { g_rips[h].n++; return; }
    }
  }
  InterlockedIncrement(&g_lost);
}

static LONG CALLBACK veh(PEXCEPTION_POINTERS e)
{
  DWORD c = e->ExceptionRecord->ExceptionCode;
  if (c == STATUS_GUARD_PAGE_VIOLATION && e->ExceptionRecord->NumberParameters >= 2) {
    uint8_t* a = (uint8_t*)e->ExceptionRecord->ExceptionInformation[1];
    uint8_t* pg = (uint8_t*)((uintptr_t)a & ~(uintptr_t)0xfff);
    if (pg + 0x1000 <= (uint8_t*)((uintptr_t)g_lo & ~(uintptr_t)0xfff) || pg >= g_hi) return EXCEPTION_CONTINUE_SEARCH;
    if (a >= g_lo && a < g_hi) {
      uint64_t rip = e->ContextRecord->Rip;
      if (rip >= g_exe && rip < g_exe + 0x8000000) rip = rip - g_exe + EXE_VA;
      note(rip, a, e->ExceptionRecord->ExceptionInformation[0] == 1);
    }
    if (g_tracing) { TlsSetValue(g_tls, pg); e->ContextRecord->EFlags |= 0x100; }
    return EXCEPTION_CONTINUE_EXECUTION;
  }
  if (c == STATUS_SINGLE_STEP && g_tls != TLS_OUT_OF_INDEXES) {
    uint8_t* pg = (uint8_t*)TlsGetValue(g_tls);
    if (!pg) return EXCEPTION_CONTINUE_SEARCH;
    TlsSetValue(g_tls, 0);
    DWORD old;
    if (g_tracing) VirtualProtect(pg, 0x1000, PAGE_READWRITE | PAGE_GUARD, &old);
    return EXCEPTION_CONTINUE_EXECUTION;
  }
  return EXCEPTION_CONTINUE_SEARCH;
}

static void guard(int on)
{
  DWORD old;
  uint8_t* p = (uint8_t*)((uintptr_t)g_lo & ~(uintptr_t)0xfff);
  for (; p < g_hi; p += 0x1000) VirtualProtect(p, 0x1000, on ? (PAGE_READWRITE | PAGE_GUARD) : PAGE_READWRITE, &old);
}

static void trace_run(const char* dir, uint32_t off, uint32_t len, uint32_t secs)
{
  /* before the first lookup (the main menu, a save being loaded) the block comes from its owner */
  uint8_t* blk = g_blk;
  if (!blk) { uint8_t* o = *(uint8_t**)(g_exe + (OWNER_VA - EXE_VA)); if (o) blk = *(uint8_t**)(o + OWNER_FIELD); }
  if (!blk || !len) return;
  if (g_tls == TLS_OUT_OF_INDEXES) g_tls = TlsAlloc();
  static int added;
  if (!added) { AddVectoredExceptionHandler(1, veh); added = 1; }
  g_lo = blk + off; g_hi = g_lo + len;
  g_tracing = 1; guard(1);
  Sleep(secs * 1000);
  g_tracing = 0; guard(0);
  Sleep(200); guard(0);
  char path[600]; wsprintfA(path, "%sfl26match.rips", dir);
  HANDLE f = CreateFileA(path, GENERIC_WRITE, FILE_SHARE_READ, 0, CREATE_ALWAYS, 0, 0);
  if (f == INVALID_HANDLE_VALUE) return;
  char b[128]; DWORD w; int n;
  n = wsprintfA(b, "range +0x%x len 0x%x secs %u rips %u lost %u\r\n", off, len, secs, (unsigned)g_nrips, (unsigned)g_lost);
  WriteFile(f, b, n, &w, 0);
  for (int i = 0; i < NRIP; i++) if (g_rips[i].rip) {
    n = wsprintfA(b, "%08x%08x %u %s +0x%x\r\n", (unsigned)(g_rips[i].rip >> 32), (unsigned)g_rips[i].rip,
                  g_rips[i].n, g_rips[i].wr ? "W" : "R", g_rips[i].off);
    WriteFile(f, b, n, &w, 0);
  }
  CloseHandle(f);
}

static void trace_poll(void)
{
  char dir[600], path[620];
  lstrcpynA(dir, g_path, sizeof dir);
  char* slash = 0; for (char* q = dir; *q; q++) if (*q == 92 || *q == '/') slash = q;
  if (!slash) return;
  slash[1] = 0;
  wsprintfA(path, "%sfl26match.trace", dir);
  HANDLE f = CreateFileA(path, GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_DELETE, 0, OPEN_EXISTING, 0, 0);
  if (f == INVALID_HANDLE_VALUE) return;
  char b[128] = {0}; DWORD r = 0;
  ReadFile(f, b, sizeof b - 1, &r, 0); CloseHandle(f); DeleteFileA(path);
  uint32_t v[3] = {0, 0, 0}; int k = 0; const char* q = b;
  while (*q && k < 3) {
    while (*q == ' ' || *q == '\t' || *q == '\r' || *q == '\n') q++;
    if (!*q) break;
    uint32_t x = 0; int base = k == 2 ? 10 : 16;
    if (base == 16 && q[0] == '0' && (q[1] == 'x' || q[1] == 'X')) q += 2;
    for (;; q++) {
      int d = (*q >= '0' && *q <= '9') ? *q - '0' : (base == 16 && *q >= 'a' && *q <= 'f') ? *q - 'a' + 10
            : (base == 16 && *q >= 'A' && *q <= 'F') ? *q - 'A' + 10 : -1;
      if (d < 0) break;
      x = x * base + d;
    }
    v[k++] = x;
  }
  if (k == 3) trace_run(dir, v[0], v[1], v[2]);
}

#ifdef FL26MATCH_DIAG
static void tw_write(void)
{
  LONG n = g_tw_n < TW_MAX ? g_tw_n : TW_MAX;
  char path[620], *slash = 0;
  lstrcpynA(path, g_path, 600);
  for (char* q = path; *q; q++) if (*q == 92 || *q == '/') slash = q;
  if (!slash) return;
  lstrcpyA(slash + 1, "fl26match.twinlog");
  HANDLE f = CreateFileA(path, GENERIC_WRITE, FILE_SHARE_READ, 0, CREATE_ALWAYS, 0, 0);
  if (f == INVALID_HANDLE_VALUE) return;
  char b[512]; DWORD w; int k;
  k = wsprintfA(b, "twinlog (B470 diagnostic): low twin answered while the high one was the current match or the user's %u, "
                "logged %d (at most %d, %d per caller), callers %d, stack walks %u\r\n",
                (unsigned)g_tw_seen, (int)n, TW_MAX, TW_PER, (int)(g_tw_nkey < TW_KEYS ? g_tw_nkey : TW_KEYS), (unsigned)g_tw_try);
  WriteFile(f, b, k, &w, 0);
  for (LONG i = 0; i < n; i++) {
    const tw_t* e = &g_tw[i];
    if (!e->ret[0]) continue;                 /* still being filled */
    k = wsprintfA(b, "id %u site %d cur %u club %u | low comp %u date %08x clubs %u-%u | high comp %u date %08x clubs %u-%u | from",
                  e->id, e->us, e->cur, e->club, e->comp[0], e->date[0], e->c0[0], e->c1[0],
                  e->comp[1], e->date[1], e->c0[1], e->c1[1]);
    for (int j = 0; j < 7; j++) k += wsprintfA(b + k, " %08x%08x", (unsigned)(e->ret[j] >> 32), (unsigned)e->ret[j]);
    k += wsprintfA(b + k, "\r\n");
    WriteFile(f, b, k, &w, 0);
  }
  CloseHandle(f);
}
#endif

/* every 5 s the stats and the first misses go to a text file beside the module, because a
 * key press does not always reach sider (session1's F10 did not, 05.11.) */
static DWORD WINAPI writer(LPVOID p)
{
  (void)p;
  for (;;) {
    Sleep(5000);
    trace_poll();
    HANDLE f = CreateFileA(g_path, GENERIC_WRITE, FILE_SHARE_READ, 0, CREATE_ALWAYS, 0, 0);
    if (f == INVALID_HANDLE_VALUE) continue;
    static char b[16384]; DWORD w;
    int n = wsprintfA(b, "table +0x%x cap %u first %u mask 0x%x alloc %u full %u hit %u scan %u miss %u none %u\r\n",
                      g_off, g_cap, g_first, g_mask, (unsigned)g_alloc, (unsigned)g_full, (unsigned)g_hit,
                      (unsigned)g_scan, (unsigned)g_miss, (unsigned)g_none);
    if (g_first) n += wsprintfA(b + n, "handed out below first %u, of them twins of a live match %u\r\n",
                                (unsigned)g_wrap, (unsigned)g_wrap_twin);   /* B488 */
    int m = g_ring_n < 64 ? (int)g_ring_n : 64;
    for (int i = 0; i < m && n < 3900; i++) {
      uint64_t r[3];
      for (int j = 0; j < 3; j++) {
        uint64_t v = g_ring[i].ret[j];
        r[j] = (v >= g_exe && v < g_exe + 0x8000000) ? v - g_exe + EXE_VA : v;
      }
      n += wsprintfA(b + n, "miss id %u from %08x%08x %08x%08x %08x%08x\r\n", g_ring[i].id,
                     (unsigned)(r[0] >> 32), (unsigned)r[0], (unsigned)(r[1] >> 32), (unsigned)r[1],
                     (unsigned)(r[2] >> 32), (unsigned)r[2]);
    }
    int c = g_ncut < NCUT ? (int)g_ncut : NCUT;
    if (g_pl_cave) n += wsprintfA(b + n, "players cap %u: word steps %u, full scans %u (last key %08x%08x at %u), map hits %u, misses %u (last %08x%08x), line-up guard %u; search by map %u, by the game %u, walk by map %u\r\n",
                                  g_pl_cap, (unsigned)g_pl_st[PS_STEPS], (unsigned)g_pl_st[PS_SCAN],
                                  (unsigned)((uint64_t)g_pl_st[PS_SCANKEY] >> 32), (unsigned)g_pl_st[PS_SCANKEY], (unsigned)g_pl_st[PS_SCANAT],
                                  (unsigned)g_pl_st[PS_MAP], (unsigned)g_pl_st[PS_MISS],
                                  (unsigned)((uint64_t)g_pl_st[PS_LASTMISS] >> 32), (unsigned)g_pl_st[PS_LASTMISS], (unsigned)g_pl_st[PS_GUARD],
                                  (unsigned)g_pl_x[0], (unsigned)g_pl_x[1], (unsigned)g_pl_x[2]);
    if (g_ctx) n += wsprintfA(b + n, "slot reads %u, past 16 bits %u, two candidates %u, tie %u, other competition's twin %u, stale slot %u\r\n",
                              (unsigned)g_slot, (unsigned)g_slot_hi, (unsigned)g_slot_amb, (unsigned)g_slot_tie, (unsigned)g_slot_other,
                              (unsigned)g_slot_stale);
    if (g_mask == 0xffffffffu)
      n += wsprintfA(b + n, "twins %s, schedules +0x%x club %u: both live %u, user picked high %u, both user's %u, neither %u\r\n",
                     g_twins ? "on" : "off", g_sched, g_blk ? user_club(g_blk) : 0, (unsigned)g_both,
                     (unsigned)g_user_hi, (unsigned)g_user_amb, (unsigned)g_user_none);
    if (g_mask == 0xffffffffu)
      n += wsprintfA(b + n, "current match %u (%s): its low word looked up from the context %u, after-match sites %u, under the post-match thread %u, today's twin from today's list %u (date +0x%x), the low twin itself %u; strip list %s\r\n",
                     (unsigned)g_cur, g_setctx ? "hooked" : "not hooked", (unsigned)g_cur_hi, (unsigned)g_cur_site, (unsigned)g_cur_post, (unsigned)g_today_hi, g_todate, (unsigned)g_cur_low,
                     g_strip ? "hooked" : "not hooked");
    if (g_mask == 0xffffffffu) {
      int wd = 0, ad = 0, sk = 0;
      for (int i = 0; i < NWIDE; i++) { if (g_wide_st[i] == 1) wd++; else if (g_wide_st[i] == 2) ad++; else sk++; }
      n += wsprintfA(b + n, "result page id reads (B470): widened %d, already 32-bit %d, skipped %d of %d\r\n", wd, ad, sk, NWIDE);
      for (int i = 0; i < NWIDE; i++) if (g_wide_st[i] == 0) {
        n += wsprintfA(b + n, "result page read %08x%08x skipped, saw ", (unsigned)(PAGE_WIDE[i].va >> 32), (unsigned)PAGE_WIDE[i].va);
        for (unsigned k = 0; k < PAGE_WIDE[i].n; k++) n += wsprintfA(b + n, "%02x", g_wide_seen[i][k]);
        n += wsprintfA(b + n, "\r\n");
      }
      wd = ad = sk = 0;
      for (int i = 0; i < NTWIN; i++) { if (g_twin_st[i] == 1) wd++; else if (g_twin_st[i] == 2) ad++; else sk++; }
      n += wsprintfA(b + n, "other cut id reads (twins sweep): widened %d, already 32-bit %d, skipped %d of %d\r\n", wd, ad, sk, NTWIN);
      for (int i = 0; i < NTWIN; i++) if (g_twin_st[i] == 0) {
        n += wsprintfA(b + n, "id read %08x%08x skipped, saw ", (unsigned)(TWIN_WIDE[i].va >> 32), (unsigned)TWIN_WIDE[i].va);
        for (unsigned k = 0; k < TWIN_WIDE[i].n; k++) n += wsprintfA(b + n, "%02x", g_twin_seen[i][k]);
        n += wsprintfA(b + n, "\r\n");
      }
      wd = ad = sk = 0;
      for (int i = 0; i < NSCORE; i++) { if (g_score_st[i] == 1) wd++; else if (g_score_st[i] == 2) ad++; else sk++; }
      n += wsprintfA(b + n, "result row score reads: widened %d, already 32-bit %d, skipped %d of %d\r\n", wd, ad, sk, NSCORE);
      for (int i = 0; i < NSCORE; i++) if (g_score_st[i] == 0) {
        n += wsprintfA(b + n, "score read %08x%08x skipped, saw ", (unsigned)(SCORE_WIDE[i].va >> 32), (unsigned)SCORE_WIDE[i].va);
        for (unsigned k = 0; k < SCORE_WIDE[i].n; k++) n += wsprintfA(b + n, "%02x", g_score_seen[i][k]);
        n += wsprintfA(b + n, "\r\n");
      }
      wd = ad = sk = 0;
      for (int i = 0; i < NLIST; i++) { if (g_list_st[i] == 1) wd++; else if (g_list_st[i] == 2) ad++; else sk++; }
      n += wsprintfA(b + n, "result rows' round test: widened %d, already 32-bit %d, skipped %d of %d\r\n", wd, ad, sk, NLIST);
      for (int i = 0; i < NLIST; i++) if (g_list_st[i] == 0) {
        n += wsprintfA(b + n, "round test %08x%08x skipped, saw ", (unsigned)(LIST_WIDE[i].va >> 32), (unsigned)LIST_WIDE[i].va);
        for (unsigned k = 0; k < LIST_WIDE[i].n; k++) n += wsprintfA(b + n, "%02x", g_list_seen[i][k]);
        n += wsprintfA(b + n, "\r\n");
      }
      n += wsprintfA(b + n, "calendar matchday page (B470): sites on %d of %d; calendar picked high %u, low %u, unclear %u; "
                     "page took the pick high %u, low %u, without a pick %u\r\n", g_pick_on, NPICK,
                     (unsigned)g_pick_hi, (unsigned)g_pick_lo, (unsigned)g_pick_amb,
                     (unsigned)g_page_hi, (unsigned)g_page_lo, (unsigned)g_page_none);
      for (int i = 0; i < NPICK; i++) if (!g_pick_ret[i])
        n += wsprintfA(b + n, "calendar matchday site %08x%08x off: not the shipped bytes\r\n", (unsigned)(PICK[i].ret >> 32), (unsigned)PICK[i].ret);
    }
    if (g_twins) n += wsprintfA(b + n, "schedule page day %s (%08x): high %u, low %u, both that day %u, neither %u\r\n",
                     g_dayhook ? "hooked" : "not hooked", (unsigned)g_daydate, (unsigned)g_day_hi, (unsigned)g_day_lo,
                     (unsigned)g_day_same, (unsigned)g_day_none);
    if (g_twins && !g_dayhook) { for (int i = 0; i < 15; i++) n += wsprintfA(b + n, "%02x", g_daysee[i]); n += wsprintfA(b + n, " seen\r\n"); }
    if (g_first >= 0x10000 || g_twins) n += wsprintfA(b + n, "cut %u at %d sites\r\n", (unsigned)g_cut, c);
    for (int i = 0; i < c && n < 8000; i++) {
      uint64_t r[3];
      for (int j = 0; j < 3; j++) {
        uint64_t v = g_cuts[i].ret[j];
        r[j] = (v >= g_exe && v < g_exe + 0x8000000) ? v - g_exe + EXE_VA : v;
      }
      n += wsprintfA(b + n, "cut %u from %08x%08x %08x%08x %08x%08x\r\n", g_cuts[i].n,
                     (unsigned)(r[0] >> 32), (unsigned)r[0], (unsigned)(r[1] >> 32), (unsigned)r[1],
                     (unsigned)(r[2] >> 32), (unsigned)r[2]);
    }
    int a = g_namb < NCUT ? (int)g_namb : NCUT;
    if (g_twins) n += wsprintfA(b + n, "maybe the user's high twin %u at %d sites\r\n", (unsigned)g_amb, a);
    for (int i = 0; i < a && n < 15800; i++) {
      uint64_t r[3];
      for (int j = 0; j < 3; j++) {
        uint64_t v = g_ambs[i].ret[j];
        r[j] = (v >= g_exe && v < g_exe + 0x8000000) ? v - g_exe + EXE_VA : v;
      }
      n += wsprintfA(b + n, "amb %u from %08x%08x %08x%08x %08x%08x\r\n", g_ambs[i].n,
                     (unsigned)(r[0] >> 32), (unsigned)r[0], (unsigned)(r[1] >> 32), (unsigned)r[1],
                     (unsigned)(r[2] >> 32), (unsigned)r[2]);
    }
    WriteFile(f, b, n, &w, 0);
    CloseHandle(f);
#ifdef FL26MATCH_DIAG
    tw_write();
#endif
  }
  return 0;
}

/* path: where the writer puts the stats (modules\fl26match.stats) */
__declspec(dllexport) int fl26_match_statsfile(const char* path)
{
  if (g_path[0]) return 1;
  lstrcpynA(g_path, path, sizeof g_path);
  return CreateThread(0, 0, writer, 0, 0, 0) != 0;
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD why, LPVOID r) { (void)h; (void)why; (void)r; return TRUE; }
