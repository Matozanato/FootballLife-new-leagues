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

typedef struct { uint16_t* b; uint16_t* e; uint16_t* c; } vec16_t;

static uint64_t           g_base = 0;
unsigned char*            g_tramp_join = 0;   /* referenced by the naked stubs */
unsigned char*            g_tramp_reg  = 0;
unsigned char*            g_tramp_bld  = 0;
unsigned char*            g_tramp_door = 0;
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
 * (+0x2fc != 0xffff) is left out. The caller's vector is not touched, so whoever allocated
 * it still frees exactly what it allocated.
 */
static const unsigned char* find_record(uint16_t cid);
vec16_t* join_pre(vec16_t* in)
{
  g_stat[0]++;
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
    if (rec && *(const uint16_t*)(rec + 0x2fc) != 0xffff) { already++; continue; }  /* in a season now */
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

/* BEFORE-hook on the registration funnel: rcx/rdx/r8 are handed on unchanged. */
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
    "mov  %rsi, %rdx\n"
    "mov  %rdi, %r8\n"
    "call *g_tramp_reg(%rip)\n"
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
   22/23/24 the builder; 32/33/34 the door; 9 = bad configuration.
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
  int r = hook((unsigned char*)(uintptr_t)(exe_base + JOIN_RVA), SIG_JOIN, 16, (void*)join_handler, &g_tramp_join);
  if (r) return r;
  r = hook((unsigned char*)(uintptr_t)(exe_base + REG_RVA), SIG_REG, 15, (void*)reg_handler, &g_tramp_reg);
  if (r) return r + 10;
  r = hook((unsigned char*)(uintptr_t)(exe_base + BLD_RVA), SIG_BLD, 15, (void*)bld_handler, &g_tramp_bld);
  if (r) return r + 20;
  r = hook((unsigned char*)(uintptr_t)(exe_base + DOOR_RVA), SIG_DOOR, 14, (void*)door_handler, &g_tramp_door);
  if (r) return r + 30;
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
