/* FL27 27.1.1 standings display. The native arrow pass still owns its sporting data. */
#include <windows.h>
#include <bcrypt.h>
#include <tlhelp32.h>
#include <stdbool.h>
#include <string.h>

#include "fl27playoffrules.h"

typedef unsigned char byte;
typedef void (*ArrowPass)(byte *, byte *, unsigned);
typedef byte *(*FindWidget)(byte *, unsigned, unsigned);
typedef int (*FindPicture)(void *, const char *, unsigned);
typedef void (*BindPicture)(byte *, const void *);
typedef void (*SelectLabel)(byte *, const char *, bool);
typedef void (*ShowWidget)(byte *, bool, unsigned);
typedef byte *(*DatabaseOwner)(void);
typedef const byte *(*DatabaseLookup)(const byte *, unsigned);
typedef const byte *(*StandingsTable)(unsigned);
typedef unsigned (*PromotionCount)(unsigned, unsigned);
typedef unsigned (*RelegationCount)(unsigned);

static const uintptr_t arrow_address = 0x140aee370ull;
static const uintptr_t bind_address = 0x140048fd0ull;
static const uintptr_t arrow_gate = 0x140aee044ull;
static const FindWidget find_widget = (FindWidget)0x140e4d1c0ull;
static const FindPicture find_picture = (FindPicture)0x140041ce0ull;
static const ShowWidget show_widget = (ShowWidget)0x140e4c240ull;
static const char green_picture[] = "cmnIconRankPromotion-updown-0";
static const char orange_picture[] = "cmnIconRankPromotion-updown-playoff";
static ArrowPass original;
static BindPicture native_bind;
static PlayoffPlaces custom[UINT16_MAX + 1];
static volatile LONG orange_binds, green_restores, forced_rows, lookup_failures;

/* Each live movie has a distinct pool slot. The full handle includes its generation. */
static RowState rows[2][UINT16_MAX + 1];

static byte *pointer_at(const byte *object, unsigned offset)
{
    return *(byte *const *)(object + offset);
}

static unsigned pool_of(uint32_t handle)
{
    return ((handle >> 27) & 15) - 1;
}

static RowState *row_state(uint32_t handle)
{
    unsigned pool = pool_of(handle);
    return pool < 2 ? &rows[pool][handle & 0xffff] : NULL;
}

static uint32_t widget_handle(const byte *widget)
{
    const byte *instance = pointer_at(widget, 0x98);
    const byte *movie = instance ? pointer_at(instance, 0x38) : NULL;
    return movie ? *(const uint32_t *)(movie + 0x2c) : 0;
}

static bool is_green(const byte *leaf)
{
    if (!leaf || *(const uint16_t *)(leaf + 8) != 0x82)
        return false;
    const byte *character = pointer_at(leaf, 0x30);
    const byte *image_tag = character ? pointer_at(character, 8) : NULL;
    return image_tag && *(const uint16_t *)(image_tag + 4) == 2;
}

static byte *green_bitmap(uint32_t handle)
{
    unsigned pool = pool_of(handle), index = handle & 0xffff;
    if (pool >= 2 || index >= ((const uint16_t *)0x14372cf30ull)[pool])
        return NULL;
    byte *const *entries = ((byte *const *const *)0x14372cf10ull)[pool];
    const byte *owner = entries ? entries[index] : NULL;
    if (!owner || *(const uint32_t *)(owner + 0x1c) != handle)
        return NULL;
    byte *outer = pointer_at(owner, 0x1b8);
    byte *icon = outer ? pointer_at(outer, 0x48) : NULL;
    byte *leaf = icon ? pointer_at(icon, 0x48) : NULL;
    return is_green(leaf) && *(const uint32_t *)leaf == handle ? leaf : NULL;
}

static bool descriptor(uint32_t out[4], bool orange)
{
    if (find_picture(out, orange ? orange_picture : green_picture, 0) == 0)
        return true;
    InterlockedIncrement(&lookup_failures);
    return false;
}

/* Also intercept native binds when the movie creates its bitmap after the row pass. */
static void bind_for_row(byte *bitmap, const void *stock)
{
    if (bitmap) {
        uint32_t handle = *(const uint32_t *)bitmap;
        RowState *state = row_state(handle);
        if (state && state->handle == handle && is_green(bitmap)) {
            uint32_t orange[4] = {0};
            if (stock && state->orange && descriptor(orange, true)) {
                native_bind(bitmap, orange);
                state->painted = bitmap;
                InterlockedIncrement(&orange_binds);
                return;
            }
            if (state->painted == bitmap)
                state->painted = NULL;
        }
    }
    native_bind(bitmap, stock);
}

static const byte *regulation(const byte *db, unsigned reg)
{
    return ((DatabaseLookup)0x1414bb000ull)(db, reg);
}

static PlayoffPlaces places_for(const byte *db, unsigned reg, unsigned upper, unsigned up)
{
    if (custom[reg].custom)
        return custom[reg];
    const StockPlayoff *profile = stock_profile(reg);
    if (!profile || upper != profile->upper || up != 3)
        return (PlayoffPlaces){0};
    const byte *record = regulation(db, profile->cup);
    if (!record || *(const uint16_t *)record != profile->cup)
        return (PlayoffPlaces){0};
    const byte *table = ((StandingsTable)0x141579b90ull)(reg);
    if (!table)
        return (PlayoffPlaces){0};
    unsigned count = *(const uint32_t *)(table + 0x3c0);
    if (count > 48)
        return (PlayoffPlaces){0};
    uint32_t no_parent = *(const uint32_t *)0x14351ae44ull;
    uint64_t eligible = 0;
    uint8_t points[48];
    for (unsigned i = 0; i < count; ++i) {
        const byte *standing = table + 0x14 * i;
        points[i] = standing[8];
        uint32_t id = *(const uint32_t *)standing;
        if (id == no_parent)
            continue;
        const byte *club = ((DatabaseLookup)0x1414bb580ull)(db, id);
        if (club && *(const uint32_t *)(club + 0x628) == no_parent)
            eligible |= rank_bit(i + 1);
    }
    return stock_playoff(profile, upper, up, *(const uint32_t *)(record + 0x30c) & 0x7f,
                         (*(const uint32_t *)(record + 0x308) >> 23) & 0x3f,
                         count, eligible, points);
}

static void draw(byte *screen, byte *row, unsigned index)
{
    bool stock_enabled = screen[0xaa] != 0;
    byte *widget = find_widget(row + 0x98, 0x1a, 0);
    uint32_t handle = widget ? widget_handle(widget) : 0;
    RowState *state = row_state(handle);
    if (!state) {
        if (stock_enabled)
            original(screen, row, index);
        return;
    }
    reuse_row(state, handle);

    unsigned reg = *(const uint16_t *)(screen + 0xa8);
    if (!state->orange && !state->painted && !state->forced && !custom[reg].custom
        && !stock_profile(reg)) {
        if (stock_enabled)
            original(screen, row, index);
        return;
    }
    const byte *owner = ((DatabaseOwner)0x1414b6a60ull)();
    const byte *db = owner ? pointer_at(owner, 0x48) : NULL;
    const byte *record = db ? regulation(db, reg) : NULL;
    bool want_orange = false, native_visible = false;
    if (record && *(const uint16_t *)record == reg) {
        unsigned upper = *(const uint16_t *)(record + 0x7c);
        unsigned lower = *(const uint16_t *)(record + 0x7e);
        unsigned clubs = *(const uint16_t *)(record + 0x30a) & 0x7f;
        unsigned up = ((PromotionCount)0x140ea1c00ull)(reg, 0);
        unsigned down = lower == UINT16_MAX ? 0 : ((RelegationCount)0x140ea0bb0ull)(reg);
        bool red = down && down <= clubs && index >= clubs - down && index < clubs;
        const byte *tier_check = (const byte *)0x140aee42bull;
        bool promotion = upper != UINT16_MAX && index < up
            && (*tier_check == 0x90 || (*(const uint32_t *)(record + 0x304) >> 30) == 2);
        native_visible = stock_enabled && (promotion || red);
        want_orange = index < clubs && playoff_arrow(places_for(db, reg, upper, up), index + 1, up, red);
    }

    uint32_t picture[4] = {0};
    state->orange = want_orange && descriptor(picture, true);
    if (stock_enabled)
        original(screen, row, index);

    const bool forced = state->forced;
    state->forced = false;
    if (state->orange) {
        if (!green_bitmap(handle) || !(*(const uint32_t *)(widget + 0xc) & 2)) {
            ((SelectLabel)pointer_at(pointer_at(widget, 0), 0x80))(widget, "icon_divisionUp", true);
        }
        if (!native_visible) {
            show_widget(widget, true, 2);
            state->forced = true;
            InterlockedIncrement(&forced_rows);
        }
    } else if (forced && !native_visible) {
        show_widget(widget, false, 2);
    }

    byte *bitmap = green_bitmap(handle);
    BitmapChange change = bitmap_change(state, bitmap);
    if (change == PAINT_ORANGE) {
        native_bind(bitmap, picture);
        state->painted = bitmap;
        InterlockedIncrement(&orange_binds);
    } else if (change == RESTORE_GREEN && descriptor(picture, false)) {
        native_bind(bitmap, picture);
        state->painted = NULL;
        InterlockedIncrement(&green_restores);
    }
}

static void absolute_jump(byte *code, uintptr_t destination)
{
    const byte opcode[] = {0xff, 0x25, 0, 0, 0, 0};
    memcpy(code, opcode, sizeof opcode);
    memcpy(code + sizeof opcode, &destination, sizeof destination);
}

static void redirect(byte *target, size_t length, uintptr_t destination)
{
    byte patch[32];
    memset(patch, 0x90, length);
    absolute_jump(patch, destination);
    memcpy(target, patch, length);
    FlushInstructionCache(GetCurrentProcess(), target, length);
}

typedef struct {
    HANDLE thread;
    DWORD id;
} ParkedThread;

static void resume_threads(ParkedThread *parked, size_t count)
{
    while (count) {
        HANDLE thread = parked[--count].thread;
        ResumeThread(thread);
        CloseHandle(thread);
    }
}

static bool in_patch(uintptr_t ip, uintptr_t start, size_t length)
{
    return ip >= start && ip - start < length;
}

/* After a pass finds no new threads, every other process thread is stopped.
   Refuse to patch if one is poised inside an instruction sequence we replace. */
static bool park_threads(ParkedThread *parked, size_t capacity, size_t *count,
                         size_t arrow_length, size_t bind_length)
{
    const DWORD pid = GetCurrentProcessId(), self = GetCurrentThreadId();
    for (unsigned pass = 0; pass < 4; ++pass) {
        size_t before = *count;
        HANDLE snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0);
        if (snapshot == INVALID_HANDLE_VALUE)
            return false;
        THREADENTRY32 entry = {.dwSize = sizeof entry};
        BOOL more = Thread32First(snapshot, &entry);
        while (more) {
            if (entry.th32OwnerProcessID == pid && entry.th32ThreadID != self) {
                size_t i = 0;
                while (i < *count && parked[i].id != entry.th32ThreadID)
                    ++i;
                if (i == *count) {
                    HANDLE thread = *count < capacity
                        ? OpenThread(THREAD_SUSPEND_RESUME | THREAD_GET_CONTEXT, FALSE, entry.th32ThreadID)
                        : NULL;
                    if (!thread || SuspendThread(thread) == (DWORD)-1) {
                        if (thread) CloseHandle(thread);
                        CloseHandle(snapshot);
                        return false;
                    }
                    parked[(*count)++] = (ParkedThread){thread, entry.th32ThreadID};
                    CONTEXT ctx = {.ContextFlags = CONTEXT_CONTROL};
                    if (!GetThreadContext(thread, &ctx)
                        || in_patch(ctx.Rip, arrow_address, arrow_length)
                        || in_patch(ctx.Rip, bind_address, bind_length)
                        || in_patch(ctx.Rip, arrow_gate, 2)) {
                        CloseHandle(snapshot);
                        return false;
                    }
                }
            }
            entry.dwSize = sizeof entry;
            more = Thread32Next(snapshot, &entry);
        }
        DWORD error = GetLastError();
        CloseHandle(snapshot);
        if (error != ERROR_NO_MORE_FILES)
            return false;
        if (*count == before)
            return true;
    }
    return false;
}

__declspec(dllexport) void fl27_playoff_place(unsigned reg, unsigned rank, unsigned contested)
{
    if (reg >= UINT16_MAX || rank > 64)
        return;
    custom[reg].custom = 1;
    custom[reg].entrants |= rank_bit(rank);
    if (contested)
        custom[reg].contested |= rank_bit(rank);
}

__declspec(dllexport) void fl27_playoff_group_quota(unsigned reg, unsigned slots)
{
    if (reg < UINT16_MAX && slots <= 64)
        custom[reg].group_quota_plus_one = slots + 1;
}

__declspec(dllexport) unsigned fl27_playoff_status(unsigned which)
{
    static volatile LONG *const counters[] = {&orange_binds, &green_restores, &forced_rows, &lookup_failures};
    return which < 4 ? (unsigned)InterlockedCompareExchange(counters[which], 0, 0) : 0;
}

static bool matches_file(const wchar_t *path, LONGLONG expected_size, const byte expected[32])
{
    HANDLE file = CreateFileW(path, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING,
                              FILE_FLAG_SEQUENTIAL_SCAN, NULL);
    if (file == INVALID_HANDLE_VALUE)
        return false;
    BCRYPT_ALG_HANDLE algorithm = NULL;
    BCRYPT_HASH_HANDLE hash = NULL;
    const DWORD capacity = expected_size < (1024 * 1024) ? (DWORD)expected_size : 1024 * 1024;
    byte *block = NULL;
    byte digest[32];
    DWORD n;
    bool match = false;
    LARGE_INTEGER size;
    if (!GetFileSizeEx(file, &size) || size.QuadPart != expected_size
        || BCryptOpenAlgorithmProvider(&algorithm, BCRYPT_SHA256_ALGORITHM, NULL, 0) < 0
        || BCryptCreateHash(algorithm, &hash, NULL, 0, NULL, 0, 0) < 0)
        goto done;
    block = HeapAlloc(GetProcessHeap(), 0, capacity);
    if (!block)
        goto done;
    while (ReadFile(file, block, capacity, &n, NULL)) {
        if (!n) {
            match = BCryptFinishHash(hash, digest, sizeof digest, 0) >= 0
                && memcmp(digest, expected, sizeof digest) == 0;
            break;
        }
        if (BCryptHashData(hash, block, n, 0) < 0)
            break;
    }
done:
    if (block) HeapFree(GetProcessHeap(), 0, block);
    if (hash) BCryptDestroyHash(hash);
    if (algorithm) BCryptCloseAlgorithmProvider(algorithm, 0);
    CloseHandle(file);
    return match;
}

static int install(const wchar_t *asset)
{
    static const byte exe_hash[] = {
        0x64, 0x38, 0x23, 0x30, 0xcc, 0x98, 0xf0, 0x23, 0x1d, 0xac, 0x69, 0xd4, 0xe9, 0x77, 0xb1, 0x11,
        0x3a, 0x3b, 0x0a, 0xa2, 0x44, 0x61, 0x4a, 0x65, 0xb9, 0x94, 0x15, 0xa3, 0x65, 0x42, 0xa2, 0xc0
    };
    static const byte asset_hash[] = {
        0x21, 0x61, 0x9d, 0x49, 0x02, 0x90, 0x69, 0x39, 0x5f, 0x87, 0x8c, 0x6f, 0xa3, 0x4f, 0x51, 0xbc,
        0xd3, 0x1a, 0x5d, 0x75, 0x41, 0x6d, 0xd8, 0x93, 0x24, 0xa1, 0x42, 0xf9, 0xf1, 0x31, 0x68, 0x8e
    };
    static const byte arrow[] = {
        0x48, 0x89, 0x5c, 0x24, 0x10, 0x48, 0x89, 0x6c, 0x24, 0x18,
        0x56, 0x57, 0x41, 0x56, 0x48, 0x83, 0xec, 0x20
    };
    static const byte finder[] = {0x48, 0x8b, 0x49, 0x78, 0x44, 0x8b, 0xd2};
    static const byte lookup[] = {0x55, 0x48, 0x81, 0xec, 0xb0, 0, 0, 0};
    static const byte bind[] = {
        0x53, 0x56, 0x41, 0x55, 0x41, 0x57, 0x55, 0x48, 0x83,
        0xec, 0x30, 0x48, 0x89, 0xd5, 0x48, 0x89, 0xcb
    };
    static const byte gate[] = {0x74, 0x0e};
    static const byte stock_tier[] = {0x75, 0x44};
    static const byte mod_studio_tier[] = {0x90, 0x90};
    const void *tier = (const void *)0x140aee42bull;
    wchar_t image[MAX_PATH];
    DWORD length = GetModuleFileNameW(NULL, image, MAX_PATH);
    const wchar_t *name = length && length < MAX_PATH ? wcsrchr(image, L'\\') : NULL;
    if (!name || _wcsicmp(name + 1, L"FL_2027.exe")
        || !matches_file(image, 458910720, exe_hash)
        || (uintptr_t)GetModuleHandleW(NULL) != 0x140000000ull
        || memcmp((void *)arrow_address, arrow, sizeof arrow)
        || memcmp((void *)find_widget, finder, sizeof finder)
        || memcmp((void *)find_picture, lookup, sizeof lookup)
        || memcmp((void *)bind_address, bind, sizeof bind)
        || memcmp((void *)arrow_gate, gate, sizeof gate)
        || (memcmp(tier, stock_tier, sizeof stock_tier)
            && memcmp(tier, mod_studio_tier, sizeof mod_studio_tier)))
        return 1;
    if (!asset || !matches_file(asset, 45160, asset_hash))
        return 3;

    byte *trampoline = VirtualAlloc(NULL, 128, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE);
    if (!trampoline)
        return 2;
    memcpy(trampoline, arrow, sizeof arrow);
    absolute_jump(trampoline + sizeof arrow, arrow_address + sizeof arrow);
    memcpy(trampoline + 64, bind, sizeof bind);
    absolute_jump(trampoline + 64 + sizeof bind, bind_address + sizeof bind);
    DWORD old, arrow_old, bind_old, gate_old;
    if (!VirtualProtect(trampoline, 128, PAGE_EXECUTE_READ, &old))
        goto failed;
    FlushInstructionCache(GetCurrentProcess(), trampoline, 128);
    if (!VirtualProtect((void *)arrow_address, sizeof arrow, PAGE_EXECUTE_READWRITE, &arrow_old))
        goto failed;
    if (!VirtualProtect((void *)bind_address, sizeof bind, PAGE_EXECUTE_READWRITE, &bind_old)) {
        VirtualProtect((void *)arrow_address, sizeof arrow, arrow_old, &old);
        goto failed;
    }
    if (!VirtualProtect((void *)arrow_gate, sizeof gate, PAGE_EXECUTE_READWRITE, &gate_old)) {
        VirtualProtect((void *)bind_address, sizeof bind, bind_old, &old);
        VirtualProtect((void *)arrow_address, sizeof arrow, arrow_old, &old);
        goto failed;
    }
    ParkedThread parked[512];
    size_t count = 0;
    if (!park_threads(parked, sizeof parked / sizeof *parked, &count, sizeof arrow, sizeof bind)
        || memcmp((void *)arrow_address, arrow, sizeof arrow)
        || memcmp((void *)bind_address, bind, sizeof bind)
        || memcmp((void *)arrow_gate, gate, sizeof gate)) {
        resume_threads(parked, count);
        VirtualProtect((void *)arrow_gate, sizeof gate, gate_old, &old);
        VirtualProtect((void *)bind_address, sizeof bind, bind_old, &old);
        VirtualProtect((void *)arrow_address, sizeof arrow, arrow_old, &old);
        goto failed;
    }
    original = (ArrowPass)trampoline;
    native_bind = (BindPicture)(trampoline + 64);
    redirect((byte *)bind_address, sizeof bind, (uintptr_t)bind_for_row);
    redirect((byte *)arrow_address, sizeof arrow, (uintptr_t)draw);
    /* Also visit rows native UI suppresses. draw still gates the original pass. */
    memset((void *)arrow_gate, 0x90, sizeof gate);
    FlushInstructionCache(GetCurrentProcess(), (void *)arrow_gate, sizeof gate);
    VirtualProtect((void *)arrow_gate, sizeof gate, gate_old, &old);
    VirtualProtect((void *)bind_address, sizeof bind, bind_old, &old);
    VirtualProtect((void *)arrow_address, sizeof arrow, arrow_old, &old);
    resume_threads(parked, count);
    return 0;

failed:
    VirtualFree(trampoline, 0, MEM_RELEASE);
    return 2;
}

__declspec(dllexport) int fl27_playoff_install(const wchar_t *asset)
{
    static volatile LONG installed;
    if (InterlockedCompareExchange(&installed, 1, 0))
        return 2;
    int result = install(asset);
    if (result)
        InterlockedExchange(&installed, 0);
    return result;
}
