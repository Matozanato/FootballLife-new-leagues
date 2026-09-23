/* fl26join.dll -- see which of our competitions reach the season door, and what it says.
 *
 * Every competition that enters a Master League season goes through one function,
 * 0x1413ac170(ctx, id) -- the door. Measured 2026-09-22 with the observer below: 65 entries
 * in a season, every one of them from the call inside it. The door has two feeders:
 *
 *   the season builder 0x1413156e0(ctx, events, include): walks every regulation and calls
 *   the door for each id that is in `include` (a u16 vector assembled from a static table in
 *   the exe, keyed by the day's event codes) and has +0x304 bit 8 set;
 *
 *   register_all 0x141343bf0(ctx, vec): calls the door for every id in `vec` plus every
 *   regulation whose parent (+0x76) is in it. Its callers are the promotion/relegation
 *   apply (0x141367010) and a few per-competition dispatch cases.
 *
 * Inside the door the only refusals are "no such record" and "+0x304 bit 8 clear"; the kind
 * switch after them admits kinds 2/5/6 outright and routes kind 1 (a league) through
 * 0x1413f36c0 -> 0x1413f3e00, which returns 1 on every path but a failed lookup. And the
 * flag is not the difference either: sampled live (tools/flagwatch.py, 2026-09-22), it is
 * clear on every regulation at the title screen and switches on for all of them at once,
 * ours included, a minute before the first season is built. So either our ids never reach
 * the door, or the door says yes and something after it throws the result away. This
 * module exists to see which, with nothing inferred:
 *
 *   hook 1 (register_all): appends our ids to the vector it is given, so the second feeder
 *          offers them too, and logs the vector the game assembled;
 *   hook 2 (enter_season 0x14158f420): logs every id that actually enters, with the return
 *          address that asked for it;
 *   hook 3 (builder): logs the include list the builder was handed, per build;
 *   hook 4 (door): logs, for our ids and a few shipped controls, the answer the door gave
 *          and the flag/kind/club fields of the record at that moment.
 *
 * Everything is also appended to a text file (path given by the loader) as it happens,
 * because the run that would have answered this on 2026-09-22 died in the protector's
 * intermittent 0x1484ed4c0 crash before the in-memory log was drained into sider.log.
 *
 * Built with `zig cc` (tools/native/build-join.sh). Our own code, no third-party binaries.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <string.h>
#include <stdio.h>
#include <stdarg.h>

#define JOIN_RVA 0x1343bf0   /* register_all(ctx, vec_u16* comps) -- the real season list */
#define REG_RVA  0x158f420   /* enter_season(u16 compid, u8 create, u8 flag) -> bool       */
#define BLD_RVA  0x13156e0   /* season builder(ctx, events, vec_u16* include)               */
#define DOOR_RVA 0x13ac170   /* door(ctx, u16 id) -> bool: the one way into a season        */
#define SET_RVA  0x14ca020   /* setRunsThisSeason(rec, bool): +0x304 bit 8                  */
#define CLOSE_RVA 0x1363210  /* close_listed(ctx, vec_u16*): New Year close of calendar-year comps */
#define BLD_RET_RVA 0x1315c0b /* return address of the builder's call to the door (0x141315c06)  */
#define OWNER_RVA 0x3705e10  /* *(void**)  -> owner; [owner+0x48] = edit block              */
#define REG_ARRAY_OFF 0x1c84230 /* edit block + this = regulation records, stride 0x314 (caps sets) */
#define REG_STRIDE    0x314
#define REG_CAP       600       /* the caps sets raise the array to 600 rows; unused rows carry id 0 */

#define MAX_IDS   64         /* our competitions */
#define MAX_LIST  512        /* merged include list */

/* 15 whole instructions worth of prologue at each site, checked before anything is written */
static const unsigned char SIG_JOIN[16] = {
  0x41,0x56, 0x48,0x83,0xec,0x40, 0x48,0x89,0x5c,0x24,0x50, 0x48,0x89,0x6c,0x24,0x68 };
static const unsigned char SIG_REG[15] = {    /* mov [rsp+18],r8b; mov [rsp+10],dl; mov [rsp+8],cx; push rbx */
  0x44,0x88,0x44,0x24,0x18, 0x88,0x54,0x24,0x10, 0x66,0x89,0x4c,0x24,0x08, 0x53 };
static const unsigned char SIG_BLD[15] = {    /* mov [rsp+18],r8; mov [rsp+10],rdx; push rbp; push rsi; push rdi; push r12 */
  0x4c,0x89,0x44,0x24,0x18, 0x48,0x89,0x54,0x24,0x10, 0x55, 0x56, 0x57, 0x41,0x54 };
static const unsigned char SIG_DOOR[14] = {   /* mov rax,rsp; push rsi; push rdi; push r14; sub rsp,0xa0 */
  0x48,0x8b,0xc4, 0x56, 0x57, 0x41,0x56, 0x48,0x81,0xec,0xa0,0x00,0x00,0x00 };

/* and dword [rcx+0x304], 0xfffffeff; movzx eax, dl; and eax, 1 -- 16 bytes, no rip-relative */
static const unsigned char SIG_SET[16] = {
  0x81,0xa1,0x04,0x03,0x00,0x00,0xff,0xfe,0xff,0xff, 0x0f,0xb6,0xc2, 0x83,0xe0,0x01 };

/* mov [rsp+8],rbx; mov [rsp+10],rsi; push rdi; sub rsp,0x20 */
static const unsigned char SIG_CLOSE[15] = {
  0x48,0x89,0x5c,0x24,0x08, 0x48,0x89,0x74,0x24,0x10, 0x57, 0x48,0x83,0xec,0x20 };

typedef struct { uint16_t* b; uint16_t* e; uint16_t* c; } vec16_t;

static uint64_t           g_base = 0;
unsigned char*            g_tramp_join = 0;   /* referenced by the naked stubs */
unsigned char*            g_tramp_reg  = 0;
unsigned char*            g_tramp_bld  = 0;
unsigned char*            g_tramp_door = 0;
unsigned char*            g_tramp_set  = 0;
unsigned char*            g_tramp_close = 0;
static char               g_path[520];      /* text file the log is mirrored to, "" = none */
static volatile uint32_t* g_cave = 0;

static uint16_t  g_ids[MAX_IDS];
static int       g_nids = 0;
static uint16_t  g_list[MAX_LIST];
static vec16_t   g_vec;

/* 0 register_all calls, 1 ids appended, 2 register_all calls refused because the list was
   already long, 3 registrations observed, 4 builder calls, 5 door calls, 6 door refusals,
   7 door calls for our ids */
static volatile uint32_t g_stat[8];
/* Set by the season builder's include list, read by the door (see door_pre). */
static volatile int g_euro_build = 0;

/* ---- small text log, drained by the Lua loader into sider.log ---- */
static char g_log[65536]; static volatile int g_log_len = 0;
static void logf(const char* fmt, ...)
{
  char line[512]; va_list ap; va_start(ap, fmt);
  int n = vsnprintf(line, sizeof line, fmt, ap); va_end(ap);
  if (n <= 0) return; if (n >= (int)sizeof line) n = sizeof line - 1;
  if (g_path[0]) {
    /* Written line by line, opened and closed each time: slow, and that is the point --
       a crash one instruction later must not take the line with it. */
    FILE* f = fopen(g_path, "ab");
    if (f) { fwrite(line, 1, (size_t)n, f); fputc('\n', f); fclose(f); }
  }
  if (g_log_len + n + 1 >= (int)sizeof g_log) return;
  memcpy(g_log + g_log_len, line, n); g_log_len += n; g_log[g_log_len++] = '\n';
}

static int ours(uint16_t id) { for (int i = 0; i < g_nids; i++) if (g_ids[i] == id) return 1; return 0; }
/* shipped leagues that do enter, as a yardstick beside ours in the door log */
static int control(uint16_t id) { return id == 17 || id == 21 || id == 50 || id == 81 || id == 82; }

static void list_ids(const uint16_t* b, int n, char* buf, int cap)
{
  int p = 0; buf[0] = 0;
  for (int j = 0; j < n && p < cap - 8; j++) p += snprintf(buf + p, (size_t)(cap - p), "%u ", b[j]);
}

/* ---- the one thing this module changes ----
 *
 * Measured on 2026-09-22 with all four hooks live. Competitions enter a season on two
 * occasions. At creation the season builder 0x1413156e0 admits the calendar-year
 * competitions (a fixed include list of 55 ids; 40 entered, among them our 49, 60 and 162,
 * which reuse shipped calendar-year ids). The rest enter later, in play, when the calendar
 * reaches a registration date: 0x141343bf0 is then called with the ids due that day (on day
 * 41 it was one id, 9) and registers each of them plus every regulation whose parent field
 * (+0x76) names one. The door 0x1413ac170 said YES to every one of ours it was shown, so
 * the only reason 33 of our leagues never had a season was that nothing ever showed them
 * to it -- the id vector comes from a case table over ids 2..175 that cannot be extended.
 *
 * This hook sits on that consumer and hands it a longer vector -- the game's own ids first,
 * unchanged and in order, then ours. Result on 22.09.: all 39 leagues in the world entered
 * on day 41 and 36 of them had a full 38-round schedule; 49, 60 and 162 had a DOUBLE one,
 * because the builder had already let them in at creation and the door does not mind
 * registering a competition twice. So an id whose record already carries a season year
 * (+0x304 bit 8 set) is left out. The caller's vector is not touched, so whoever allocated
 * it still frees exactly what it allocated.
 */
static const unsigned char* find_record(uint16_t cid);
static void log_tables(void);
vec16_t* join_pre(vec16_t* in)
{
  g_stat[0]++;
  log_tables();
  int n = 0;
  if (in && in->b && in->e >= in->b) {
    n = (int)(in->e - in->b);
    if (n > MAX_LIST - MAX_IDS) {
      /* Refuse rather than truncate: a shortened list would silently drop a shipped
         competition out of the season, which is exactly what we must never do. */
      logf("register_all: vector has %d ids, too long to extend -- passed through untouched", n);
      g_stat[2]++;
      return in;
    }
    memcpy(g_list, in->b, (size_t)n * 2);
  }

  int added = 0, already = 0;
  for (int i = 0; i < g_nids; i++) {
    int dup = 0;
    for (int j = 0; j < n; j++) if (g_list[j] == g_ids[i]) { dup = 1; break; }
    if (dup) continue;
    const unsigned char* rec = find_record(g_ids[i]);
    /* In a season now = the runs-this-season flag (+0x304 bit 8). The season year at +0x2fc
       outlives the season: a league closed at New Year keeps it, and was then never let
       back in (2026-09-23: 49 and 60 played no second season, no table at the rollover). */
    if (rec && ((*(const uint32_t*)(rec + 0x304) >> 8) & 1)) { already++; continue; }
    g_list[n++] = g_ids[i]; added++;
  }
  g_vec.b = g_list; g_vec.e = g_list + n; g_vec.c = g_list + MAX_LIST;
  g_stat[1] += (uint32_t)added;

  /* First few builds only: say what the game had, so the log shows whether the shipped
     stand-alone leagues were in the list at all. That is still an open question. */
  if (g_stat[0] <= 4) {
    char buf[240]; int p = 0;
    for (int j = 0; j < n - added && p < (int)sizeof buf - 8; j++)
      p += snprintf(buf + p, sizeof buf - (size_t)p, "%u ", g_list[j]);
    buf[p] = 0;
    logf("register_all %u: game gave %d ids [%s], we appended %d -> %d (%d of ours already in a season)",
         g_stat[0], n - added, buf, added, n, already);
  }
  return &g_vec;
}

/* ---- observation only ---- */
/* Which door a competition comes through matters more than the fact that it arrives.
   enter_season has two callers, and one of them -- the wrapper at 0x141590420 -- has four
   of its own, each reached from a different part of the season build. Measured on
   2026-09-22: of our 41 leagues exactly eight enter a season, and those eight have nothing
   in common in their own record, so the difference must be in who asks for them.

   `ret` is enter_season's own return address. When it is the call inside the wrapper, the
   wrapper's return address is still on the stack -- the wrapper pushes rsi and subtracts
   0x20 before calling, so its own return address sits 0x30 further up -- and that one names
   the real call site. */
void reg_pre(uint64_t compid, uint64_t ret, uint64_t ret2)
{
  g_stat[3]++;
  if (g_cave) {
    uint32_t idx = g_cave[1] & 255;
    uint16_t* ring = (uint16_t*)((void*)(g_cave + 2));
    ring[idx] = (uint16_t)compid;
    g_cave[1] = (g_cave[1] + 1) & 255;
    g_cave[0]++;
  }
  if (g_stat[3] <= 200) {
    uint64_t site = (ret == g_base + 0x159044c) ? ret2 : ret;
    logf("enter_season(%u) from %llx", (unsigned)(compid & 0xffff),
         (unsigned long long)site);
  }
}

/* ---- observation only: the builder's include list ---- */
void bld_pre(uint64_t ctx, uint64_t events, vec16_t* inc)
{
  (void)ctx; (void)events;
  g_stat[4]++;
  int n = (inc && inc->b && inc->e >= inc->b) ? (int)(inc->e - inc->b) : 0;
  /* An August world's builder admits the European leagues, and shipped id 2 (England D1)
     is always among them; a calendar-year world's builder never lists it. */
  g_euro_build = 0;
  for (int j = 0; j < n; j++) if (inc->b[j] == 2) { g_euro_build = 1; break; }
  if (g_stat[4] <= 8) {
    char buf[480]; list_ids(inc ? inc->b : 0, n, buf, sizeof buf);
    logf("builder %u: include list has %d ids [%s]", g_stat[4], n, buf);
  }
}

/* ---- observation only: what the door answered, and the record it looked at ----
 *
 * The record is found by walking the regulation array ourselves. An earlier build asked the
 * game's own lookup 0x1414bc860 for it, and two runs in a row then died at the manager-settings
 * step in the protector's obfuscated code with every register garbage (0x1484ed4c0, then
 * 0x1531cc313). That crash family is known to strike there without any observer installed, so
 * this is not proof the call was to blame -- but an observer that runs no game code at all
 * cannot be, and reading 0x314-byte rows costs nothing. */
static const unsigned char* find_record(uint16_t cid)
{
  void** owner = *(void***)(uintptr_t)(g_base + OWNER_RVA);
  if (!owner) return 0;
  const unsigned char* block = (const unsigned char*)owner[0x48 / 8];
  if (!block) return 0;
  /* All 600 rows are walked rather than the live count: the count's offset differs between
   * caps sets (0x2bc5de8 under ...-mlcopy, 0x3b20888 under ...-fixtures) while the array's
   * does not, and an unused row has id 0, which no competition of ours carries. */
  const unsigned char* rec = block + REG_ARRAY_OFF;
  for (uint32_t i = 0; i < REG_CAP; i++, rec += REG_STRIDE)
    if (*(const uint16_t*)rec == cid) return rec;
  return 0;
}

/* Called before the door. Our leagues are August-May leagues, but three of them reuse
 * shipped calendar-year ids (49, 60, 162) and the builder admits those at creation as if
 * they were mid-season: they got a season year on the spot, a second schedule when
 * register_all admitted them again on day 41, and an end-of-season pass on day 116 over
 * empty standings. So when the builder is the caller, the door says no to ours -- the
 * builder treats a refusal as an ordinary skip -- and they enter on day 41 with the rest.
 * Returns nonzero to refuse without running the door. */
int door_pre(uint64_t id, uint64_t ret)
{
  uint16_t cid = (uint16_t)id;
  if (!ours(cid) || ret != g_base + BLD_RET_RVA) return 0;
  /* All of the above holds for a calendar-year world only. Since fl26augseason a career in
   * one of our leagues builds an August world: the builder admits every European league at
   * creation, ours included, and the first fixtures are the next day -- there is no later
   * registration day to wait for. Refusing there left 38 leagues out (2026-09-22, 22:27). */
  if (g_euro_build) return 0;
  g_stat[6]++;
  logf("door(%u) refused by us: the builder asked at creation; it enters via register_all instead", cid);
  return 1;
}

void door_post(uint64_t id, uint64_t result, uint64_t ret)
{
  uint16_t cid = (uint16_t)id;
  g_stat[5]++;
  if (!(result & 0xff)) g_stat[6]++;
  if (!ours(cid) && !control(cid)) return;
  if (ours(cid)) g_stat[7]++;
  uint32_t flags = 0, kind = 0, clubs = 0; int found = 0;
  const unsigned char* rec = find_record(cid);
  if (rec) {
    found = 1;
    flags = *(const uint32_t*)(rec + 0x304); kind = *(const uint32_t*)(rec + 0x84);
    clubs = (*(const uint32_t*)(rec + 0x308) >> 16) & 0x7f;
  }
  logf("door(%u) -> %s  %s flag %s kind %u clubs %u  from %llx", cid, (result & 0xff) ? "YES" : "no",
       ours(cid) ? "ours" : "ctrl", found ? (((flags >> 8) & 1) ? "on" : "OFF") : "no-record",
       kind, clubs, (unsigned long long)ret);
}

/* ---- observation only: who takes a league of ours out of its season ----
 *
 * Measured 2026-09-23: at New Year five of our leagues (76, 93, 94, 96, 98) lose the season
 * flag and all their clubs, and nothing lets them back in until the next July. Their ids are
 * on the builder's calendar-year include list, but the builder only calls the door for ids
 * whose flag is still set, so something cleared it first. The flag has one setter,
 * 0x1414ca020, with seven callers; this logs which one fires for our ids, plus the exe
 * addresses found higher on the stack as a rough backtrace. */
void set_pre(uint64_t rec, uint64_t flag, const uint64_t* sp)
{
  if (flag & 1) return;
  uint16_t cid = *(const uint16_t*)(uintptr_t)rec;
  if (!ours(cid)) return;
  static int n = 0;
  if (++n > 300) return;
  uint32_t clubs = (*(const uint32_t*)(uintptr_t)(rec + 0x308) >> 16) & 0x7f;
  char buf[200]; int p = 0; int hits = 0;
  for (int i = 1; i < 96 && hits < 8 && p < (int)sizeof buf - 20; i++) {
    uint64_t v = sp[i];
    if (v > g_base + 0x1000 && v < g_base + 0x2600000) {
      p += snprintf(buf + p, sizeof buf - (size_t)p, "%llx ", (unsigned long long)v); hits++;
    }
  }
  buf[p] = 0;
  logf("flag off(%u) clubs %u  from %llx  stack [%s]", cid, clubs, (unsigned long long)sp[0], buf);
}

/* BEFORE-hook on the setter: every volatile register it reads is put back. */
__attribute__((naked)) void set_handler(void)
{
  __asm__ volatile(
    "push %rcx\n"
    "push %rdx\n"
    "push %r8\n"
    "push %r9\n"
    "push %r10\n"
    "push %r11\n"
    "push %rax\n"
    "sub  $0x20, %rsp\n"
    "lea  0x58(%rsp), %r8\n"     /* entry rsp: 0x20 + 7 pushes */
    "call set_pre\n"
    "add  $0x20, %rsp\n"
    "pop  %rax\n"
    "pop  %r11\n"
    "pop  %r10\n"
    "pop  %r9\n"
    "pop  %r8\n"
    "pop  %rdx\n"
    "pop  %rcx\n"
    "jmp  *g_tramp_set(%rip)\n");
}

/* ---- the second thing this module changes: New Year must not close our leagues ----
 *
 * Measured 2026-09-23 with the flag-setter observer: on 1 January 0x141363210 (called once,
 * from the daily scheduler at 0x141314743) walks a list of calendar-year competitions and
 * closes every one that has a season -- 0x141363040, then 0x141363170, which clears the
 * season flag. Five of our leagues (76, 93, 94, 96, 98) and 162 reuse shipped calendar-year
 * ids, so they were closed half-way through their August-May season, and nothing let them
 * back in until July. Worse, at the July rollover they had no season object, and the
 * season-end filter sends a whole group down its no-movement path for one such competition.
 *
 * Our leagues end with the European group on day 181 (fl26augseason puts their regions
 * there), never on 1 January, so the list this function receives is handed on without our
 * ids. The game's own ids are kept, in order; the caller's vector is not touched. */
static uint16_t g_close_list[MAX_LIST];
static vec16_t  g_close_vec;
vec16_t* close_pre(vec16_t* in)
{
  if (!in || !in->b || in->e < in->b) return in;
  int n = (int)(in->e - in->b), k = 0, dropped = 0;
  if (n > MAX_LIST) return in;
  /* The builder also closes the previous season through here at the July rollover, with
     the European list (it starts with 2). Ours must close there like everyone else: a
     league kept open was never re-admitted and played the new season without a table. */
  for (int j = 0; j < n; j++) if (in->b[j] == 2) return in;
  char buf[200]; int p = 0; buf[0] = 0;
  for (int j = 0; j < n; j++) {
    uint16_t id = in->b[j];
    if (ours(id)) {
      dropped++;
      if (p < (int)sizeof buf - 8) p += snprintf(buf + p, sizeof buf - (size_t)p, "%u ", id);
      continue;
    }
    g_close_list[k++] = id;
  }
  if (!dropped) return in;
  g_close_vec.b = g_close_list; g_close_vec.e = g_close_list + k; g_close_vec.c = g_close_list + MAX_LIST;
  logf("new-year close: %d ids, kept ours out of it: [%s]", n, buf);
  return &g_close_vec;
}

__attribute__((naked)) void close_handler(void)
{
  __asm__ volatile(
    "push %rbx\n"
    "push %rbp\n"
    "push %rsi\n"
    "push %rdi\n"
    "sub  $0x28, %rsp\n"
    "mov  %rcx, %rbx\n"
    "mov  %rdx, %rcx\n"
    "call close_pre\n"
    "mov  %rax, %rdx\n"
    "mov  %rbx, %rcx\n"
    "call *g_tramp_close(%rip)\n"
    "add  $0x28, %rsp\n"
    "pop  %rdi\n"
    "pop  %rsi\n"
    "pop  %rbp\n"
    "pop  %rbx\n"
    "ret\n");
}

/* CALL-style hook on the builder: same frame discipline as join_handler. The builder's first
 * two instructions spill r8 and rdx into its caller's home space, which here is our 0x28 area. */
__attribute__((naked)) void bld_handler(void)
{
  __asm__ volatile(
    "push %rbx\n"
    "push %rbp\n"
    "push %rsi\n"
    "push %rdi\n"
    "sub  $0x28, %rsp\n"
    "mov  %rcx, %rbx\n"
    "mov  %rdx, %rsi\n"
    "mov  %r8,  %rdi\n"
    "call bld_pre\n"
    "mov  %rbx, %rcx\n"
    "mov  %rsi, %rdx\n"
    "mov  %rdi, %r8\n"
    "call *g_tramp_bld(%rip)\n"
    "add  $0x28, %rsp\n"
    "pop  %rdi\n"
    "pop  %rsi\n"
    "pop  %rbp\n"
    "pop  %rbx\n"
    "ret\n");
}

/* CALL-style hook on the door: run it, then report what it said. Its own home stores
 * ([rax+8], [rax+0x10] with rax = its entry rsp) land in our 0x28 area. */
__attribute__((naked)) void door_handler(void)
{
  __asm__ volatile(
    "push %rbx\n"
    "push %rbp\n"
    "push %rsi\n"
    "push %rdi\n"
    "sub  $0x28, %rsp\n"
    "mov  %rcx, %rdi\n"   /* ctx */
    "mov  %rdx, %rsi\n"   /* id */
    "movzx %si, %ecx\n"
    "mov  0x48(%rsp), %rdx\n"   /* our return address = the door's caller (4 pushes + 0x28) */
    "call door_pre\n"
    "test %eax, %eax\n"
    "jnz  1f\n"
    "mov  %rdi, %rcx\n"
    "mov  %rsi, %rdx\n"
    "call *g_tramp_door(%rip)\n"
    "mov  %rax, %rbx\n"
    "movzx %si, %ecx\n"
    "mov  %rax, %rdx\n"
    "mov  0x48(%rsp), %r8\n"
    "call door_post\n"
    "mov  %rbx, %rax\n"
    "jmp  2f\n"
    "1:\n"
    "xor  %eax, %eax\n"   /* refused: the door's own 'no' */
    "2:\n"
    "add  $0x28, %rsp\n"
    "pop  %rdi\n"
    "pop  %rsi\n"
    "pop  %rbp\n"
    "pop  %rbx\n"
    "ret\n");
}

/* CALL-style hook on register_all. Entry rsp = 8 mod 16; four pushes leave it at 8, and the
 * sub of 0x28 brings it to 0, so the two calls below are made from an aligned stack and the
 * callee home space lies inside our own 0x28 area rather than the real caller frame. */
__attribute__((naked)) void join_handler(void)
{
  __asm__ volatile(
    "push %rbx\n"
    "push %rbp\n"
    "push %rsi\n"
    "push %rdi\n"
    "sub  $0x28, %rsp\n"
    "mov  %rcx, %rbx\n"
    "mov  %rdx, %rcx\n"
    "call join_pre\n"
    "mov  %rax, %rdx\n"
    "mov  %rbx, %rcx\n"
    "call *g_tramp_join(%rip)\n"
    "add  $0x28, %rsp\n"
    "pop  %rdi\n"
    "pop  %rsi\n"
    "pop  %rbp\n"
    "pop  %rbx\n"
    "ret\n");
}

/* Around-hook on the registration funnel: rcx/rdx/r8 are handed on unchanged; reg_fix_pre may
   reset +0x2fc first and reg_post may repair a refused entry (both for ours at the door only). */
__attribute__((naked)) void reg_handler(void)
{
  __asm__ volatile(
    "push %rbx\n"
    "push %rbp\n"
    "push %rsi\n"
    "push %rdi\n"
    "sub  $0x28, %rsp\n"
    "mov  %rcx, %rbx\n"
    "mov  %rdx, %rsi\n"
    "mov  %r8,  %rdi\n"
    "mov  0x48(%rsp), %rdx\n"      /* enter_season return address */
    "mov  0x78(%rsp), %r8\n"       /* if that was the wrapper: its caller */
    "call reg_pre\n"
    "mov  %rbx, %rcx\n"
    "mov  0x48(%rsp), %rdx\n"
    "call reg_fix_pre\n"
    "mov  %rbx, %rcx\n"
    "mov  %rsi, %rdx\n"
    "mov  %rdi, %r8\n"
    "call *g_tramp_reg(%rip)\n"
    "movzx %al, %r8d\n"            /* bool result -> reg_post, which may turn it into 1 */
    "mov  %rbx, %rcx\n"
    "mov  0x48(%rsp), %rdx\n"
    "call reg_post\n"
    "add  $0x28, %rsp\n"
    "pop  %rdi\n"
    "pop  %rsi\n"
    "pop  %rbp\n"
    "pop  %rbx\n"
    "ret\n");
}

/* ---- the season-end split ----
 *
 * Measured 2026-09-23 at two July rollovers. The season-end filter 0x141365c50 hands the mover
 * 0x141365110 one list per region group, and the mover exchanges clubs between each league A
 * and the league below it, B (+0x7e), using both final tables. Two cases break that:
 *   - A league with no season table at all (49 and 60 lost theirs at New Year). The game's
 *     answer is to send the WHOLE group down the no-movement path 0x141365ed0 -- nobody in
 *     England was promoted either, and every table carried on into the next season.
 *   - A has a table but B has none (Ligue 2 never gets one): the mover writes B's new list
 *     from an empty table, so B ends up holding only the clubs relegated into it. That
 *     emptied Ligue 2 and our 49 down to 3 clubs.
 * Erasing such leagues from the list (the first two attempts, in fl26seasonend) avoids the
 * damage but also keeps them out of the apply, so they are never closed, never re-admitted,
 * and play the new season on the old table.
 *
 * So the list is split here: every league that cannot be moved properly (no table of its
 * own, or a league below it without one) goes through the game's own no-movement path,
 * which re-lists its current members and lets the apply close and re-open it; the rest go
 * to the mover as before. The filter's all-or-nothing check is switched off by
 * fl26seasonend, which reads the byte this module sets at SPLIT_FLAG_RVA. */
#define MOVER_RVA   0x1365110  /* mover(ctx, vec_u16* ids, u8 fixSlots)                     */
#define DEGEN_RVA   0x1365ed0  /* relist(ctx, vec_u16* ids): OUTPUT = current members, no moves */
#define HASTAB_RVA  0x1590750  /* has_season_table(u16 id) -> bool (what the filter asks)   */
#define SPLIT_FLAG_RVA 0x252eef0 /* byte read by fl26seasonend's trampoline: 1 = split is live */
static const unsigned char SIG_MOVER[15] = {               /* mov [rsp+18],r8b; mov [rsp+10],rdx; mov [rsp+8],rcx */
  0x44,0x88,0x44,0x24,0x18, 0x48,0x89,0x54,0x24,0x10, 0x48,0x89,0x4c,0x24,0x08 };
static unsigned char* g_tramp_mover = 0;
static uint16_t g_mv_list[MAX_LIST], g_dg_list[MAX_LIST];
static vec16_t  g_mv_vec, g_dg_vec;
typedef char (*hastab_fn)(uint64_t id);
typedef void (*degen_fn)(void* ctx, vec16_t* ids);

static void ensure_tables(void);
vec16_t* mover_pre(void* ctx, vec16_t* in)
{
  ensure_tables();
  if (!in || !in->b || in->e < in->b) return in;
  int n = (int)(in->e - in->b), k = 0, d = 0;
  if (n > MAX_LIST) return in;
  hastab_fn has = (hastab_fn)(uintptr_t)(g_base + HASTAB_RVA);
  char buf[240]; int p = 0; buf[0] = 0;
  for (int j = 0; j < n; j++) {
    uint16_t id = in->b[j];
    const unsigned char* rec = find_record(id);
    int ok = rec && (has(id) & 1);
    const char* why = "no table";
    if (ok) {
      uint16_t below = *(const uint16_t*)(rec + 0x7e);
      if (below != 0xffff && find_record(below) && !(has(below) & 1)) { ok = 0; why = "below has none"; }
    }
    if (ok) { g_mv_list[k++] = id; continue; }
    g_dg_list[d++] = id;
    if (p < (int)sizeof buf - 24) p += snprintf(buf + p, sizeof buf - (size_t)p, "%u(%s) ", id, why);
  }
  if (!d) return in;
  logf("season end: %d leagues, %d kept still: [%s]", n, d, buf);
  g_dg_vec.b = g_dg_list; g_dg_vec.e = g_dg_list + d; g_dg_vec.c = g_dg_list + MAX_LIST;
  ((degen_fn)(uintptr_t)(g_base + DEGEN_RVA))(ctx, &g_dg_vec);
  g_mv_vec.b = g_mv_list; g_mv_vec.e = g_mv_list + k; g_mv_vec.c = g_mv_list + MAX_LIST;
  return &g_mv_vec;
}

/* Observation: which of ours (and Ligue 2, Serie B) hold a season table right now. Measured
 * 2026-09-23: at the July rollover 49, 60, 81, 98, 100, 109, 110 and 144 had none although the
 * door had admitted them a season earlier. Logged on every registration day so the log shows
 * whether the table never appears or goes away mid-season. */
static void log_tables(void)
{
  if (!g_base) return;
  hastab_fn has = (hastab_fn)(uintptr_t)(g_base + HASTAB_RVA);
  char yes[400], no[400]; int py = 0, pn = 0; yes[0] = no[0] = 0;
  for (int i = 0; i < g_nids + 2; i++) {
    uint16_t id = i < g_nids ? g_ids[i] : (i == g_nids ? 81 : 82);
    if (!find_record(id)) continue;
    int t = has(id) & 1;
    char* b = t ? yes : no; int* pp = t ? &py : &pn;
    if (*pp < 390) *pp += snprintf(b + *pp, 400 - (size_t)*pp, "%u ", id);
  }
  logf("tables: with [%s] without [%s]", yes, no);
}

/* ---- a season that ends without a final table ----
 *
 * A season header entry (0xb4, keyed by 0x1415451a0(id)) holds two sub-records of 0x58:
 * +0 key, +4 u16 season year, +8 up to 20 table indices. The table byte +0x314 is not "exists"
 * but "final": mid-season every shipped league has it clear (surveyed 2026-09-23, day 333),
 * and it is set by 0x141313cd0, which writes the final positions by kind and then flags the
 * sub-record for +0x2fc -- but only if 0x141546c70 agrees, and that gate walks every round and
 * wants every match played. has_season_table() only counts a flagged sub-record, so a league
 * with one unplayed match ends its season with no table, and the season-end filter then sends
 * it down the no-movement path. 49, 60 and 61 carried unplayable doubles from the time the
 * builder and register_all both admitted them.
 *
 * Here, at the season-end split and for ours only: if the sub-record for +0x2fc exists and is
 * not final, it is finalised through the game's own 0x141313cd0 with the gate opened for that
 * one call. Nothing else is touched. */
#define GETCTX_RVA   0x14b6a60   /* returns the object whose +0x78 is the standings object  */
#define KEYOF_RVA    0x15451a0   /* (u32* out, u16 id): the header key of a competition     */
#define ACTIVATE_RVA 0x1313cd0   /* (ctx, u16 id): fill the table for +0x2fc, then switch it on */
#define GATE1_RVA    0x1313d47   /* je (74 4f) after 0x141546c70 in the switch-on            */
#define GATE2_RVA    0x13140d6   /* je rel32 (0f 84) after 0x141546c70 in the kind-1 filler  */
#define TABBASE_IMM  0x158df94   /* u32 immediate: where the tables start (hdr patches move it) */
typedef uint64_t (*getctx_fn)(void);
typedef void (*keyof_fn)(uint32_t* out, uint64_t id);
typedef void (*activate_fn)(uint64_t ctx, uint64_t id);
static void ensure_tables(void)
{
  if (!g_base) return;
  hastab_fn has = (hastab_fn)(uintptr_t)(g_base + HASTAB_RVA);
  uint32_t tabbase = *(const uint32_t*)(uintptr_t)(g_base + TABBASE_IMM);
  if (tabbase < 0x4650 || tabbase > 0x10000) return;
  uint32_t entries = tabbase / 0xb4;
  uint64_t ctx = ((getctx_fn)(uintptr_t)(g_base + GETCTX_RVA))();
  if (!ctx) return;
  const unsigned char* std = *(const unsigned char* const*)(uintptr_t)(ctx + 0x78);
  if (!std) return;
  for (int i = 0; i < g_nids; i++) {
    uint16_t id = g_ids[i];
    unsigned char* rec = (unsigned char*)find_record(id);
    if (!rec) continue;
    uint16_t cur = *(const uint16_t*)(rec + 0x2fc);
    uint32_t key = 0xffffffff;
    ((keyof_fn)(uintptr_t)(g_base + KEYOF_RVA))(&key, id);
    if (key == 0xffffffff) continue;
    uint32_t year = 0xffff, earliest = 0xffff; int cur_final = -1;
    for (uint32_t k = 0; k < entries; k++) {
      const unsigned char* e = std + (size_t)k * 0xb4;
      if (*(const uint32_t*)e != key) continue;
      for (int h = 0; h < 2; h++) {
        const unsigned char* s = e + 4 + h * 0x58;
        uint16_t y = *(const uint16_t*)(s + 4);
        if (*(const uint32_t*)s == 0xffffffff || y == 0xffff) continue;
        int32_t t0 = *(const int32_t*)(s + 8);
        if (t0 < 0) continue;                              /* no table built for it */
        if (y < earliest) earliest = y;
        if (y == cur) cur_final = std[tabbase + (size_t)t0 * 0x187c + 0x314] != 0;
      }
      break;
    }
    /* Only the season that is ending. A league whose +0x2fc is already 0xffff was closed
     * earlier (49/60/61 at New Year, as the calendar-year ids they reuse): finalising some
     * other sub-record for it gave an empty table, the mover then rewrote the league from it
     * and left 49 and 60 with no clubs (2026-09-23). Those stay on the no-movement path. */
    (void)earliest;
    if (cur_final == 0) year = cur;
    if (year == 0xffff) continue;
    /* Switching the flag alone leaves every row at position -1: the switch-on first fills the
     * table by the regulation's kind (0x141313b00 / db0 / 4070, none of which reads the ctx
     * argument), and it picks the sub-record by +0x2fc. So +0x2fc is pointed at the built one
     * for the call and put back afterwards. */
    uint16_t was = cur;
    *(uint16_t*)(rec + 0x2fc) = (uint16_t)year;
    /* The switch-on and the kind-1 filler both ask 0x141546c70 first, and for these ids it
     * says no (2026-09-23: 49/60/61 identical to 11 in every flag that gate reads directly, so
     * the refusal comes from its walk over the season's rounds). Both branches are opened for
     * this one call and closed again straight after. */
    unsigned char* g1 = (unsigned char*)(uintptr_t)(g_base + GATE1_RVA);
    unsigned char* g2 = (unsigned char*)(uintptr_t)(g_base + GATE2_RVA);
    unsigned char s1[2], s2[6]; DWORD o1, o2; int open = 0;
    if (g1[0] == 0x74 && g2[0] == 0x0f && g2[1] == 0x84 &&
        VirtualProtect(g1, 2, PAGE_EXECUTE_READWRITE, &o1)) {
      if (VirtualProtect(g2, 6, PAGE_EXECUTE_READWRITE, &o2)) {
        memcpy(s1, g1, 2); memcpy(s2, g2, 6);
        memset(g1, 0x90, 2); memset(g2, 0x90, 6);
        open = 1;
      } else VirtualProtect(g1, 2, o1, &o1);
    }
    if (open) {
      ((activate_fn)(uintptr_t)(g_base + ACTIVATE_RVA))(0, id);
      memcpy(g1, s1, 2); memcpy(g2, s2, 6);
      VirtualProtect(g2, 6, o2, &o2); VirtualProtect(g1, 2, o1, &o1);
      FlushInstructionCache(GetCurrentProcess(), g1, 2);
      FlushInstructionCache(GetCurrentProcess(), g2, 6);
    }
    *(uint16_t*)(rec + 0x2fc) = was;
    logf("table finalised: %u season %u (+0x2fc %u) -> %s", id, year, was,
         (has(id) & 1) ? "has a table now" : "STILL NONE");
  }
}

/* ---- a new season that enters without its table ----
 *
 * Measured 2026-09-23 (day 242 of the third season): 11, 49, 60 and 61 play the new season and
 * results land in its table, but +0x2fc (the season year everything else reads the table by)
 * is not set. enter_season 0x14158f420 computes the season's year from its first match date
 * and then looks for a sub-record of that year in the competition's header entry:
 *   - none: a new one is built (0x14158f9b0) and 0x14158fd90 writes the year to +0x2fc;
 *   - one already there: it is rebuilt only for ids 0x67 and 0x3a (a local flag set at the
 *     top of the function); for anyone else the call returns false and +0x2fc stays 0xffff.
 * 49/60/61 reuse shipped calendar-year ids and already hold a sub-record for the new year by
 * the time the July builder asks, so they fall in the second case. 11 fails even earlier:
 * 0x141546800 returns its +0x2fc, which the July teardown never reset (still 2025, a final
 * table), and anything other than 0xffff is refused at once.
 *
 * So, for ours and only when the builder's door asks (return address 0x1413ac37e):
 *   before -- a +0x2fc whose sub-record is final (that season is over) is put back to 0xffff,
 *             the teardown value, so the call is not refused outright;
 *   after  -- if the call still said no and +0x2fc is 0xffff, the sub-record of the new year is
 *             rebuilt the way the game does it for 0x67/0x3a (0x14158f870, then 0x14158f9b0 with
 *             flag 0), provided none of its tables is final. The new year is today's year: the
 *             builder runs in July and our leagues start in August. */
#define DOOR_RET_RVA 0x13ac37e   /* enter_season's return address inside the door          */
#define SUBRESET_RVA 0x158f870   /* (u8* subrecord): clear its tables                        */
#define SUBFILL_RVA  0x158f9b0   /* (u8* entry, u16 year, u8 flag): build the year's tables  */
#define TODAY_OFF    0x1642a24   /* u32 date in the edit block: low word = year              */
typedef void (*subreset_fn)(unsigned char* sub);
typedef void (*subfill_fn)(unsigned char* entry, uint64_t year, uint64_t flag);

/* The header entry of `id` and the table base, or NULL. */
static unsigned char* season_entry(uint16_t id, unsigned char** std_out, uint32_t* tabbase_out)
{
  if (!g_base) return 0;
  uint32_t tabbase = *(const uint32_t*)(uintptr_t)(g_base + TABBASE_IMM);
  if (tabbase < 0x4650 || tabbase > 0x10000) return 0;
  uint64_t ctx = ((getctx_fn)(uintptr_t)(g_base + GETCTX_RVA))();
  if (!ctx) return 0;
  unsigned char* std = *(unsigned char* const*)(uintptr_t)(ctx + 0x78);
  if (!std) return 0;
  uint32_t key = 0xffffffff;
  ((keyof_fn)(uintptr_t)(g_base + KEYOF_RVA))(&key, id);
  if (key == 0xffffffff) return 0;
  for (uint32_t k = 0; k < tabbase / 0xb4; k++) {
    unsigned char* e = std + (size_t)k * 0xb4;
    if (*(const uint32_t*)e == key) { *std_out = std; *tabbase_out = tabbase; return e; }
  }
  return 0;
}

/* -1 no sub-record of that year, 0 none of its tables final, 1 at least one final. */
static int sub_final(const unsigned char* e, const unsigned char* std, uint32_t tabbase,
                     uint16_t year, int* h_out)
{
  for (int h = 0; h < 2; h++) {
    const unsigned char* s = e + 4 + h * 0x58;
    if (*(const uint32_t*)s == 0xffffffff || *(const uint16_t*)(s + 4) != year) continue;
    int fin = 0;
    for (int j = 0; j < 20; j++) {
      int32_t t = *(const int32_t*)(s + 8 + j * 4);
      if (t < 0) break;
      if (t < 0x258 && std[tabbase + (size_t)t * 0x187c + 0x314]) fin = 1;
    }
    if (h_out) *h_out = h;
    return fin;
  }
  return -1;
}

void reg_fix_pre(uint64_t compid, uint64_t ret)
{
  uint16_t id = (uint16_t)compid;
  if (ret != g_base + DOOR_RET_RVA || !ours(id)) return;
  unsigned char* rec = (unsigned char*)find_record(id);
  if (!rec) return;
  uint16_t cur = *(const uint16_t*)(rec + 0x2fc);
  if (cur == 0xffff) return;
  unsigned char* std; uint32_t tabbase;
  unsigned char* e = season_entry(id, &std, &tabbase);
  if (!e || sub_final(e, std, tabbase, cur, 0) != 1) return;
  *(uint16_t*)(rec + 0x2fc) = 0xffff;
  logf("enter %u: season %u is over (final table), +0x2fc reset so the new one can enter", id, cur);
}

uint64_t reg_post(uint64_t compid, uint64_t ret, uint64_t result)
{
  uint16_t id = (uint16_t)compid;
  if ((result & 0xff) || ret != g_base + DOOR_RET_RVA || !ours(id)) return result;
  unsigned char* rec = (unsigned char*)find_record(id);
  if (!rec || *(const uint16_t*)(rec + 0x2fc) != 0xffff) return result;
  uint64_t ctx = ((getctx_fn)(uintptr_t)(g_base + GETCTX_RVA))();
  const unsigned char* blk = ctx ? *(const unsigned char* const*)(uintptr_t)(ctx + 0x48) : 0;
  if (!blk) return result;
  uint16_t year = *(const uint16_t*)(blk + TODAY_OFF);
  unsigned char* std; uint32_t tabbase; int h = -1;
  unsigned char* e = season_entry(id, &std, &tabbase);
  int fin = e ? sub_final(e, std, tabbase, year, &h) : -1;
  if (fin != 0) {
    logf("enter %u: refused, season %u sub-record %s -- left alone", id, year,
         fin < 0 ? "missing" : "is final");
    return result;
  }
  ((subreset_fn)(uintptr_t)(g_base + SUBRESET_RVA))(e + 4 + h * 0x58);
  ((subfill_fn)(uintptr_t)(g_base + SUBFILL_RVA))(e, year, 0);
  uint16_t now = *(const uint16_t*)(rec + 0x2fc);
  logf("enter %u: stale season %u sub-record rebuilt -> +0x2fc %u", id, year, now);
  return now == year ? 1 : result;
}

/* CALL-style, same frame discipline as bld_handler: the mover's first three instructions
 * spill r8, rdx and rcx into our 0x28 area. */
__attribute__((naked)) void mover_handler(void)
{
  __asm__ volatile(
    "push %rbx\n"
    "push %rbp\n"
    "push %rsi\n"
    "push %rdi\n"
    "sub  $0x28, %rsp\n"
    "mov  %rcx, %rbx\n"
    "mov  %rdx, %rsi\n"
    "mov  %r8,  %rdi\n"
    "call mover_pre\n"
    "mov  %rbx, %rcx\n"
    "mov  %rax, %rdx\n"
    "mov  %rdi, %r8\n"
    "call *g_tramp_mover(%rip)\n"
    "add  $0x28, %rsp\n"
    "pop  %rdi\n"
    "pop  %rsi\n"
    "pop  %rbp\n"
    "pop  %rbx\n"
    "ret\n");
}

/* ---- the teardown: where a season is really closed ----
 *
 * Measured 2026-09-23. At every rollover the rebuild driver 0x141314fc0 hands 0x141314350 the
 * list of competitions whose season ends that day (built from the exe's static event table),
 * and for each of them it finalises the table (0x141313cd0), clears its calendar days, deletes
 * its match records (0x140af1ed0 over the 0x32c8 records at edit+0xe9ff08), closes it
 * (0x141363210) and puts +0x2fc back to 0xffff. Only then does the builder let it in again.
 *
 * Our ids are not in that table, so from the second season on none of that happened to them:
 * +0x2fc stayed on 2025, enter_season refused them (it refuses anything whose +0x2fc is not
 * 0xffff), every club's league record carried on counting (76 games after two seasons) and
 * the old seasons' matches stayed in the match array. 49/60/61 had the opposite problem: as
 * shipped calendar-year ids they are in the New Year list, so they were torn down in the
 * middle of their August-May season.
 *
 * So: on the July list (the European group, recognised by shipped id 2 as elsewhere in this
 * module) our ids are appended; on every other list they are taken out. The caller's vector is
 * not touched. */
#define TEARDOWN_RVA 0x1314350   /* teardown(ctx, vec_u16* ids)                                */
static const unsigned char SIG_TEARDOWN[14] = {   /* mov [rsp+10],rdx; push rbp/rsi/rdi/r12/r13/r14 */
  0x48,0x89,0x54,0x24,0x10, 0x55, 0x56, 0x57, 0x41,0x54, 0x41,0x55, 0x41,0x56 };
unsigned char* g_tramp_teardown = 0;
static uint16_t g_td_list[MAX_LIST];
static vec16_t  g_td_vec;
vec16_t* teardown_pre(uint64_t ctx, vec16_t* in)
{
  (void)ctx;
  if (!in || !in->b || in->e < in->b) return in;
  int n = (int)(in->e - in->b), k = 0, euro = 0, changed = 0;
  if (n + g_nids > MAX_LIST) return in;
  for (int j = 0; j < n; j++) if (in->b[j] == 2) { euro = 1; break; }
  char buf[320]; int p = 0; buf[0] = 0;
  for (int j = 0; j < n; j++) {
    uint16_t id = in->b[j];
    if (!euro && ours(id)) {
      changed++;
      if (p < (int)sizeof buf - 8) p += snprintf(buf + p, sizeof buf - (size_t)p, "%u ", id);
      continue;
    }
    g_td_list[k++] = id;
  }
  if (euro) {
    for (int i = 0; i < g_nids; i++) {
      uint16_t id = g_ids[i]; int dup = 0;
      for (int j = 0; j < k; j++) if (g_td_list[j] == id) { dup = 1; break; }
      if (dup || !find_record(id)) continue;
      g_td_list[k++] = id; changed++;
      if (p < (int)sizeof buf - 8) p += snprintf(buf + p, sizeof buf - (size_t)p, "%u ", id);
    }
  }
  if (!changed) return in;
  g_td_vec.b = g_td_list; g_td_vec.e = g_td_list + k; g_td_vec.c = g_td_list + MAX_LIST;
  logf("teardown: %d ids, ours %s: [%s]", n, euro ? "added" : "kept out", buf);
  return &g_td_vec;
}

/* CALL-style: the teardown's first instruction spills rdx into our 0x28 area. */
__attribute__((naked)) void teardown_handler(void)
{
  __asm__ volatile(
    "push %rbx\n"
    "push %rbp\n"
    "push %rsi\n"
    "push %rdi\n"
    "sub  $0x28, %rsp\n"
    "mov  %rcx, %rbx\n"
    "call teardown_pre\n"
    "mov  %rbx, %rcx\n"
    "mov  %rax, %rdx\n"
    "call *g_tramp_teardown(%rip)\n"
    "add  $0x28, %rsp\n"
    "pop  %rdi\n"
    "pop  %rsi\n"
    "pop  %rbp\n"
    "pop  %rbx\n"
    "ret\n");
}

/* ---- install ---- */
static int hook(unsigned char* target, const unsigned char* sig, int n, void* handler, unsigned char** tramp_out)
{
  for (int i = 0; i < n; i++) if (target[i] != sig[i]) return 2;
  unsigned char* t = (unsigned char*)VirtualAlloc(0, 0x100, MEM_COMMIT|MEM_RESERVE, PAGE_EXECUTE_READWRITE);
  if (!t) return 3;
  memcpy(t, target, n);
  t[n] = 0xFF; t[n+1] = 0x25; *(uint32_t*)(t + n + 2) = 0; *(uint64_t*)(t + n + 6) = (uint64_t)(uintptr_t)(target + n);
  DWORD old;
  if (!VirtualProtect(target, n, PAGE_EXECUTE_READWRITE, &old)) return 4;
  target[0] = 0xFF; target[1] = 0x25; *(uint32_t*)(target + 2) = 0; *(uint64_t*)(target + 6) = (uint64_t)(uintptr_t)handler;
  for (int i = 14; i < n; i++) target[i] = 0x90;
  VirtualProtect(target, n, old, &old);
  FlushInstructionCache(GetCurrentProcess(), target, n);
  *tramp_out = t;
  return 0;
}

/* 0 ok; 2/3/4 = register_all hook signature/alloc/protect; 12/13/14 the same for enter_season;
   22/23/24 the builder; 32/33/34 the door; 42/43/44 the flag setter; 52/53/54 the New Year close; 62/63/64 the season-end mover; 72/73/74 the teardown; 9 = bad configuration.
   `logpath` may be NULL or empty: then the log lives in memory only, drained by the loader. */
__declspec(dllexport) int fl26_join_install(uint64_t exe_base, uint64_t cave_addr,
                                            const uint16_t* ids, int nids, const char* logpath)
{
  if (!ids || nids < 1 || nids > MAX_IDS) return 9;
  g_base = exe_base; g_cave = (volatile uint32_t*)(uintptr_t)cave_addr;
  g_nids = nids;
  for (int i = 0; i < nids; i++) g_ids[i] = ids[i];
  g_path[0] = 0;
  if (logpath && logpath[0] && strlen(logpath) < sizeof g_path) strcpy(g_path, logpath);

  /* Check every prologue before touching any, so a mismatch leaves the game unmodified
     rather than half hooked. */
  if (memcmp((void*)(uintptr_t)(exe_base + JOIN_RVA), SIG_JOIN, 16)) return 2;
  if (memcmp((void*)(uintptr_t)(exe_base + REG_RVA),  SIG_REG,  15)) return 12;
  if (memcmp((void*)(uintptr_t)(exe_base + BLD_RVA),  SIG_BLD,  15)) return 22;
  if (memcmp((void*)(uintptr_t)(exe_base + DOOR_RVA), SIG_DOOR, 14)) return 32;
  if (memcmp((void*)(uintptr_t)(exe_base + SET_RVA),  SIG_SET,  16)) return 42;
  if (memcmp((void*)(uintptr_t)(exe_base + CLOSE_RVA), SIG_CLOSE, 15)) return 52;
  if (memcmp((void*)(uintptr_t)(exe_base + MOVER_RVA), SIG_MOVER, 15)) return 62;
  if (memcmp((void*)(uintptr_t)(exe_base + TEARDOWN_RVA), SIG_TEARDOWN, 14)) return 72;
  int r = hook((unsigned char*)(uintptr_t)(exe_base + JOIN_RVA), SIG_JOIN, 16, (void*)join_handler, &g_tramp_join);
  if (r) return r;
  r = hook((unsigned char*)(uintptr_t)(exe_base + REG_RVA), SIG_REG, 15, (void*)reg_handler, &g_tramp_reg);
  if (r) return r + 10;
  r = hook((unsigned char*)(uintptr_t)(exe_base + BLD_RVA), SIG_BLD, 15, (void*)bld_handler, &g_tramp_bld);
  if (r) return r + 20;
  r = hook((unsigned char*)(uintptr_t)(exe_base + DOOR_RVA), SIG_DOOR, 14, (void*)door_handler, &g_tramp_door);
  if (r) return r + 30;
  r = hook((unsigned char*)(uintptr_t)(exe_base + SET_RVA), SIG_SET, 16, (void*)set_handler, &g_tramp_set);
  if (r) return r + 40;
  r = hook((unsigned char*)(uintptr_t)(exe_base + CLOSE_RVA), SIG_CLOSE, 15, (void*)close_handler, &g_tramp_close);
  if (r) return r + 50;
  r = hook((unsigned char*)(uintptr_t)(exe_base + MOVER_RVA), SIG_MOVER, 15, (void*)mover_handler, &g_tramp_mover);
  if (r) return r + 60;
  r = hook((unsigned char*)(uintptr_t)(exe_base + TEARDOWN_RVA), SIG_TEARDOWN, 14, (void*)teardown_handler, &g_tramp_teardown);
  if (r) return r + 70;
  {
    volatile unsigned char* flag = (volatile unsigned char*)(uintptr_t)(exe_base + SPLIT_FLAG_RVA);
    DWORD old;
    if (VirtualProtect((void*)flag, 1, PAGE_EXECUTE_READWRITE, &old)) {
      *flag = 1;
      VirtualProtect((void*)flag, 1, old, &old);
    }
  }
  logf("fl26join: hooks live (register_all %llx, enter_season %llx, builder %llx, door %llx), %d competition ids",
       (unsigned long long)(exe_base + JOIN_RVA), (unsigned long long)(exe_base + REG_RVA),
       (unsigned long long)(exe_base + BLD_RVA), (unsigned long long)(exe_base + DOOR_RVA), nids);
  return 0;
}

/* copy and clear the pending log text; returns bytes copied */
__declspec(dllexport) int fl26_join_log(char* out, int cap)
{
  int n = g_log_len; if (n > cap - 1) n = cap - 1; if (n < 0) n = 0;
  memcpy(out, g_log, n); out[n] = 0;
  if (n < g_log_len) { memmove(g_log, g_log + n, g_log_len - n); g_log_len -= n; } else g_log_len = 0;
  return n;
}

/* the eight counters described at g_stat */
__declspec(dllexport) void fl26_join_stats(uint32_t* out8)
{
  for (int i = 0; i < 8; i++) out8[i] = g_stat[i];
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID r) { (void)h;(void)reason;(void)r; return TRUE; }
