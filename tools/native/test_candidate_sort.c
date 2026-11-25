#include <assert.h>
#include <stdio.h>
#include "fl26candidate.c"

typedef struct { uint32_t words[4]; uint64_t count; } Rng;

static uint32_t random_bit(void* opaque)
{
    Rng* r = opaque;
    uint32_t t = r->words[0] ^ (r->words[0] << 11);
    uint32_t w = r->words[3];
    r->words[0] = r->words[1];
    r->words[1] = r->words[2];
    r->words[2] = w;
    r->words[3] = w ^ (w >> 19) ^ t ^ (t >> 8);
    ++r->count;
    return r->words[3] & 1;
}

static int model_tie(void* state) { return (int)random_bit(state); }

static void reference(Candidate* rows, size_t count, Rng* rng)
{
    for (size_t i = 0; i < count; ++i) {
        size_t best = i;
        for (size_t j = i + 1; j < count; ++j) {
            if (rows[j].score < rows[best].score ||
                (rows[j].score == rows[best].score && random_bit(rng))) best = j;
        }
        if (best != i) {
            unsigned char saved[14];
            memcpy(saved, rows + i, sizeof saved);
            memcpy(rows + i, rows + best, sizeof saved);
            memcpy(rows + best, saved, sizeof saved);
        }
    }
}

static uint32_t next(uint32_t* state)
{
    return *state = *state * UINT32_C(1664525) + UINT32_C(1013904223);
}

static void fill(Candidate* rows, size_t count, uint32_t* seed, unsigned distribution)
{
    for (size_t i = 0; i < count; ++i) {
        uint32_t score = next(seed);
        if (distribution == 0) score %= 7;
        if (distribution == 1) score = UINT32_MAX;
        if (distribution == 2) score %= 257;
        rows[i] = (Candidate){next(seed), score, (uint16_t)i, (uint16_t)next(seed)};
    }
}

static void model_tests(void)
{
    Candidate a[257], b[257];
    uint32_t scratch[9], seed = 13;
    for (unsigned trial = 0; trial < 4000; ++trial) {
        size_t count = trial % 258;
        fill(a, count, &seed, trial % 4);
        memcpy(b, a, count * sizeof *a);
        Rng r = {{seed, 2, 3, 4}, 0}, s = r;
        reference(a, count, &r);
        candidate_sort(b, count, scratch, model_tie, &s);
        assert(!memcmp(a, b, count * sizeof *a));
        assert(r.count == s.count && !memcmp(r.words, s.words, sizeof r.words));
    }
}

static NativeSort call_target(const unsigned char* site)
{
    int32_t relative;
    assert(site[0] == 0xe8);
    memcpy(&relative, site + 1, sizeof relative);
    return (NativeSort)(site + 5 + relative);
}

static void compare_native(NativeSort control, NativeSort installed,
                           uint32_t* state, size_t count, unsigned distribution)
{
    Candidate* a = malloc((count + 2) * sizeof *a);
    Candidate* b = malloc((count + 2) * sizeof *b);
    assert(a && b);
    uint32_t seed = 23;
    fill(a, count + 2, &seed, distribution);
    memcpy(b, a, (count + 2) * sizeof *a);
    Vector first = {a + 1, a + 1 + count, a + 1 + count};
    Vector second = {b + 1, b + 1 + count, b + 1 + count};
    uint32_t initial[] = {0x892ab3, 2, 3, 4}, expected[4];
    memcpy(state, initial, sizeof initial);
    control(NULL, &first);
    memcpy(expected, state, sizeof expected);
    memcpy(state, initial, sizeof initial);
    installed(NULL, &second);
    assert(!memcmp(a, b, (count + 2) * sizeof *a));
    assert(!memcmp(state, expected, sizeof expected));
    assert(first.begin == a+1 && second.begin == b+1);
    assert(first.end == a+1+count && second.end == b+1+count);
    assert(first.capacity == first.end && second.capacity == second.end);
    if (count < 4096) {
        /* Reconstruct input and independently check the exact RNG advance. */
        Rng oracle = {{initial[0], initial[1], initial[2], initial[3]}, 0};
        seed = 23;
        fill(b, count + 2, &seed, distribution);
        reference(b+1, count, &oracle);
        assert(!memcmp(a, b, (count + 2) * sizeof *a));
        assert(!memcmp(expected, oracle.words, sizeof expected));
    }
    printf("Mapped native parity: %zu candidates, distribution %u\n", count, distribution);
    free(a);
    free(b);
}

static unsigned fallbacks;
static void fallback_probe(void* self, Vector* vector)
{
    assert(self == &fallbacks && vector);
    ++fallbacks;
}

static void preflight_tests(void)
{
    Candidate row[64];
    Vector small = {row, row + 63, row + 64};
    Vector bad = {row, row + 64, row};
    Vector huge = {row, (Candidate*)((uintptr_t)row + (MAX_ROWS + 1u) * sizeof(Candidate)),
                        (Candidate*)((uintptr_t)row + (MAX_ROWS + 1u) * sizeof(Candidate))};
    native_sort = fallback_probe;
    sort_wrapper(&fallbacks, &small);
    sort_wrapper(&fallbacks, &bad);
    sort_wrapper(&fallbacks, &huge);
    assert(fallbacks == 3);
    assert(fl26_candidate_install((uintptr_t)row) == 2);
}

static uint32_t platform_state;
static uint32_t platform_calls;
static uint32_t platform_draw(void)
{
    ++platform_calls;
    return next(&platform_state);
}

static void check_null_rng(unsigned char* base, NativeSort control, NativeSort installed)
{
    void* empty = NULL;
    memcpy(base + 0x37066a8, &empty, sizeof empty);
    unsigned char* import = base + 0x25306f0;
    uint32_t (*draw)(void) = platform_draw;
    DWORD old;
    assert(VirtualProtect(import, sizeof draw, PAGE_READWRITE, &old));
    memcpy(import, &draw, sizeof draw);
    uint32_t seed = 11;
    Candidate a[128], b[128];
    fill(a, 128, &seed, 1);
    memcpy(b, a, sizeof a);
    Vector first = {a, a + 128, a + 128};
    Vector second = {b, b + 128, b + 128};
    platform_state = 23;
    platform_calls = 0;
    control(NULL, &first);
    const uint32_t state = platform_state, calls = platform_calls;
    assert(calls == 128 * 127 / 2);
    platform_state = 23;
    platform_calls = 0;
    installed(NULL, &second);
    assert(platform_state == state && platform_calls == calls);
    assert(!memcmp(a, b, sizeof a));
    puts("Mapped null-state RNG parity: 8,128 imported draws and identical final records.");
}

static void check_install(const wchar_t* path)
{
    HANDLE file = CreateFileW(path, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING, 0, NULL);
    assert(file != INVALID_HANDLE_VALUE);
    HANDLE mapping = CreateFileMappingW(file, NULL, PAGE_READONLY | SEC_IMAGE, 0, 0, NULL);
    assert(mapping);
    unsigned char* base = MapViewOfFile(mapping, FILE_MAP_READ, 0, 0, 0);
    assert(base);
    unsigned char* a = base + FIRST_CALL_RVA;
    const unsigned char* b = base + 0xfd4626;
    unsigned char untouched[15];
    memcpy(untouched, b - 8, sizeof untouched);
    NativeSort control = call_target(a);
    assert(control == call_target(b) && control == (NativeSort)(base + SORT_RVA));
    assert(fl26_candidate_install(0) == 1);

    DWORD old, ignored;
    assert(VirtualProtect(a, 5, PAGE_EXECUTE_READWRITE, &old));
    a[1] ^= 1;
    assert(fl26_candidate_install((uintptr_t)base) == 2);
    assert(!memcmp(untouched, b - 8, sizeof untouched));
    a[1] ^= 1;
    assert(VirtualProtect(a, 5, old, &ignored));

    assert(fl26_candidate_install((uintptr_t)base) == 0);
    NativeSort first = call_target(a);
    assert(first != control && call_target(b) == control);
    assert(!memcmp(untouched, b - 8, sizeof untouched));
    const unsigned char jump[] = {0xff, 0x25, 0, 0, 0, 0};
    uintptr_t destination;
    assert(!memcmp((const void*)first, jump, sizeof jump));
    memcpy(&destination,(const unsigned char*)first+sizeof jump,sizeof destination);
    assert(destination == (uintptr_t)sort_wrapper);
    assert(fl26_candidate_install((uintptr_t)base) == 2);

    /* The mapped RNG's ordinary non-null state path has no external imports.
       Install a private state vector without loading or starting the game. */
    uint32_t state[4];
    unsigned char* rng_pointer = base + 0x37066a8;
    uint32_t* state_pointer = state;
    assert(VirtualProtect(rng_pointer, sizeof state_pointer, PAGE_READWRITE, &old));
    memcpy(rng_pointer, &state_pointer, sizeof state_pointer);
    puts("Site 1, mapped original routines:");
    compare_native(control, first, state, 0, 0);
    compare_native(control, first, state, 63, 1);
    compare_native(control, first, state, 64, 1);
    compare_native(control, first, state, 102245, 3);
    compare_native(control, first, state, 257, 0);
    compare_native(control, first, state, 2048, 2);
    check_null_rng(base, control, first);
    assert(call_target(b) == control && !memcmp(untouched, b - 8, sizeof untouched));
    puts("Site 2 remains byte-for-byte native and still calls the original sorter.");
    VirtualFree((void*)first, 0, MEM_RELEASE);
    UnmapViewOfFile(base);
    CloseHandle(mapping);
    CloseHandle(file);
}

int wmain(int argc, wchar_t** argv)
{
    model_tests();
    preflight_tests();
    puts("4,000 deterministic model cases passed.");
    if (argc != 2) {
        fputs("Usage: test-candidate-sort.exe <FL_2027.exe>\n", stderr);
        return 2;
    }
    check_install(argv[1]);
    return 0;
}
