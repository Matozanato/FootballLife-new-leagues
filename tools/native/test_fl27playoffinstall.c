/* Run as FL_2027.exe at the expected base to exercise the unsupported image guard. */
#include <assert.h>

#include "fl27playoff.c"

static volatile LONG ticks;

static DWORD WINAPI worker(LPVOID stop)
{
    while (WaitForSingleObject(stop, 1) == WAIT_TIMEOUT)
        InterlockedIncrement(&ticks);
    return 0;
}

int main(void)
{
    assert((uintptr_t)GetModuleHandleW(NULL) == 0x140000000ull);
    assert(fl27_playoff_install(NULL) == 1);

    HANDLE stop = CreateEventW(NULL, TRUE, FALSE, NULL);
    assert(stop);
    HANDLE workers[] = {CreateThread(NULL, 0, worker, stop, 0, NULL),
                        CreateThread(NULL, 0, worker, stop, 0, NULL)};
    assert(workers[0] && workers[1]);
    while (!InterlockedCompareExchange(&ticks, 0, 0))
        Sleep(1);

    ParkedThread parked[16];
    size_t count = 0;
    assert(!park_threads(parked, 0, &count, 18, 17));
    assert(count == 0);
    assert(!park_threads(parked, 1, &count, 18, 17));
    assert(count == 1);
    resume_threads(parked, count);
    count = 0;
    assert(park_threads(parked, 16, &count, 18, 17));
    assert(count >= 2);
    LONG before = InterlockedCompareExchange(&ticks, 0, 0);
    Sleep(30);
    assert(InterlockedCompareExchange(&ticks, 0, 0) == before);
    resume_threads(parked, count);
    Sleep(30);
    assert(InterlockedCompareExchange(&ticks, 0, 0) > before);
    assert(in_patch(arrow_address + 17, arrow_address, 18));
    assert(!in_patch(arrow_address + 18, arrow_address, 18));
    SetEvent(stop);
    assert(WaitForMultipleObjects(2, workers, TRUE, 2000) == WAIT_OBJECT_0);
    CloseHandle(workers[0]);
    CloseHandle(workers[1]);
    CloseHandle(stop);
    return 0;
}
