#include <windows.h>
#include "fl26candidate_sort.h"

enum {
    FIRST_CALL_RVA = 0xfd457a,
    SORT_RVA = 0xfd46d0,
    RNG_RVA = 0x15149e0,
    RNG_BODY_RVA = 0x15872f0,
    MAX_ROWS = 180017
};
typedef struct { Candidate *begin, *end, *capacity; } Vector;
typedef void (*NativeSort)(void*, Vector*);
typedef uint32_t (*NativeRandom)(uint32_t*, unsigned char*);

static NativeSort native_sort;
static NativeRandom native_random;


static int native_tie(void* unused)
{
    (void)unused;
    uint32_t bound = 2;
    unsigned char option = 0;
    return native_random(&bound, &option) != 0;
}

static int writable(uintptr_t address, size_t bytes)
{
    MEMORY_BASIC_INFORMATION region;
    if (!VirtualQuery((const void*)address, &region, sizeof region)) return 0;
    const DWORD access = region.Protect & 0xff;
    if (region.State != MEM_COMMIT || (region.Protect & PAGE_GUARD) ||
        (access != PAGE_READWRITE && access != PAGE_WRITECOPY &&
         access != PAGE_EXECUTE_READWRITE && access != PAGE_EXECUTE_WRITECOPY)) return 0;
    const size_t offset = address - (uintptr_t)region.BaseAddress;
    return offset < region.RegionSize && bytes <= region.RegionSize - offset;
}

static int vector_count(const Vector* vector, size_t* count)
{
    if (!vector || (uintptr_t)vector % _Alignof(Vector) || !writable((uintptr_t)vector, sizeof *vector)) return 0;
    const uintptr_t begin = (uintptr_t)vector->begin;
    const uintptr_t end = (uintptr_t)vector->end;
    const uintptr_t capacity = (uintptr_t)vector->capacity;
    if (end < begin || capacity < end || ((end - begin) % 16) ||
        ((capacity - begin) % 16) || (!begin && capacity)) return 0;
    *count = (end - begin) / 16;
    return 1;
}

static void sort_wrapper(void* self, Vector* vector)
{
    size_t count;
    if (!vector_count(vector, &count) || count < 2 * CANDIDATE_BLOCK ||
        count > MAX_ROWS || ((uintptr_t)vector->begin % _Alignof(Candidate)) ||
        !writable((uintptr_t)vector->begin, count * sizeof(Candidate))) {
        native_sort(self, vector);
        return;
    }

    uint32_t* minima = HeapAlloc(GetProcessHeap(), 0,
        ((count + CANDIDATE_BLOCK - 1) / CANDIDATE_BLOCK) * sizeof *minima);
    if (!minima) {
        native_sort(self, vector);
        return;
    }
    candidate_sort(vector->begin, count, minima, native_tie, NULL);
    HeapFree(GetProcessHeap(), 0, minima);
}
static uint32_t fingerprint(const unsigned char* code, size_t length)
{
    uint32_t hash = UINT32_C(2166136261);
    for (size_t i = 0; i < length; ++i) hash = (hash ^ code[i]) * UINT32_C(16777619);
    return hash;
}

static unsigned char* near_stubs(uintptr_t site)
{
    SYSTEM_INFO system;
    GetSystemInfo(&system);
    const uintptr_t step = system.dwAllocationGranularity;
    const uintptr_t origin = site & ~(step - 1);
    for (uintptr_t delta = step; delta < 0x70000000; delta += step) {
        unsigned char* page = VirtualAlloc((void*)(origin + delta), 4096,
                                           MEM_RESERVE | MEM_COMMIT, PAGE_READWRITE);
        if (page) return page;
    }
    return NULL;
}

static void make_stub(unsigned char* stub, NativeSort handler)
{
    const uintptr_t destination = (uintptr_t)handler;
    /* jmp [rip+0] preserves the argument registers and the caller's stack. */
    const unsigned char jump[] = {0xff, 0x25, 0, 0, 0, 0};
    memcpy(stub, jump, sizeof jump);
    memcpy(stub + sizeof jump, &destination, sizeof destination);
}

static int image_span(uintptr_t base, uintptr_t offset, size_t bytes)
{
    if (offset > UINTPTR_MAX - base) return 0;
    const uintptr_t address = base + offset;
    MEMORY_BASIC_INFORMATION region;
    if (!VirtualQuery((const void*)address, &region, sizeof region) ||
        (uintptr_t)region.AllocationBase != base || region.State != MEM_COMMIT ||
        region.Type != MEM_IMAGE || (region.Protect & PAGE_GUARD)) return 0;
    const DWORD access = region.Protect & 0xff;
    if (access != PAGE_EXECUTE_READ && access != PAGE_EXECUTE_READWRITE &&
        access != PAGE_EXECUTE_WRITECOPY) return 0;
    const size_t start = address - (uintptr_t)region.BaseAddress;
    return start < region.RegionSize && bytes <= region.RegionSize - start;
}

__declspec(dllexport) int fl26_candidate_install(uintptr_t base)
{
    static const unsigned char expected[] = {
        0x48, 0x8d, 0x55, 0xa7, 0x48, 0x8b, 0xcb,
        0xe8, 0x51, 0x01, 0x00, 0x00, 0x41, 0xb0, 0x01
    };
    /* Call during Sider startup, before the native builder can execute. */
    if (!base) return 1;
    if (!image_span(base, FIRST_CALL_RVA - 7, sizeof expected) ||
        !image_span(base, SORT_RVA, 366) || !image_span(base, RNG_RVA, 5) ||
        !image_span(base, RNG_BODY_RVA, 120)) return 2;

    unsigned char* site = (unsigned char*)(base + FIRST_CALL_RVA);
    if (memcmp(site - 7, expected, sizeof expected) ||
        fingerprint((const unsigned char*)(base + SORT_RVA), 366) != UINT32_C(0x365893e8) ||
        fingerprint((const unsigned char*)(base + RNG_RVA), 5) != UINT32_C(0xcab54393) ||
        fingerprint((const unsigned char*)(base + RNG_BODY_RVA), 120) != UINT32_C(0xe0412378))
        return 2;

    native_sort = (NativeSort)(base + SORT_RVA);
    native_random = (NativeRandom)(base + RNG_RVA);
    unsigned char* stub = near_stubs((uintptr_t)site);
    if (!stub) return 4;
    make_stub(stub, sort_wrapper);
    DWORD original_protection, unused;
    if (!VirtualProtect(stub, 4096, PAGE_EXECUTE_READ, &unused) ||
        !FlushInstructionCache(GetCurrentProcess(), stub, 14) ||
        !VirtualProtect(site, 5, PAGE_EXECUTE_READWRITE, &original_protection)) {
        VirtualFree(stub, 0, MEM_RELEASE);
        return 5;
    }

    const int32_t displacement = (int32_t)((intptr_t)stub - (intptr_t)(site + 5));
    memcpy(site + 1, &displacement, sizeof displacement);
    if (FlushInstructionCache(GetCurrentProcess(), site, 5) &&
        VirtualProtect(site, 5, original_protection, &unused))
        return 0;

    /* The call page remains writable on this path. Keep the stub allocated
       if the rollback itself cannot synchronize the instruction cache. */
    memcpy(site + 1, expected + 8, sizeof displacement);
    const BOOL restored = FlushInstructionCache(GetCurrentProcess(), site, 5);
    VirtualProtect(site, 5, original_protection, &unused);
    if (restored) VirtualFree(stub, 0, MEM_RELEASE);
    return 6;
}
