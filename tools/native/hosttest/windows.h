/* hosttest/windows.h -- just enough of Win32 for fl26swiss.c's pure parts to compile and run on
   Linux (fase 6: the DLL's logic tested without the game and without Windows). Nothing here
   reaches a game: the hooks, patches and memory reads are never called by the host tests; the
   file calls (state file, palmares file) work on POSIX files. */
#ifndef FL26_HOST_WINDOWS_H
#define FL26_HOST_WINDOWS_H
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <time.h>
typedef int BOOL; typedef unsigned char BYTE; typedef uint16_t WORD; typedef uint32_t DWORD; typedef uint64_t DWORD64;
typedef int32_t LONG; typedef int64_t LONGLONG; typedef uint64_t ULONG_PTR, SIZE_T, DWORD_PTR; typedef int64_t LONG_PTR;
typedef void* HANDLE; typedef void* HMODULE; typedef void* HINSTANCE; typedef void* HWND; typedef void* LPVOID;
typedef const void* LPCVOID; typedef char* LPSTR; typedef const char* LPCSTR; typedef DWORD* LPDWORD; typedef long HRESULT;
typedef void* PVOID; typedef unsigned long ULONG; typedef unsigned short USHORT; typedef char CHAR; typedef unsigned int UINT;
typedef uint64_t ULONGLONG; typedef int64_t LONG64;
typedef struct { WORD e_magic; WORD e_pad[29]; LONG e_lfanew; } IMAGE_DOS_HEADER;
typedef struct { DWORD VirtualAddress, Size; } IMAGE_DATA_DIRECTORY;
typedef struct { WORD Machine, NumberOfSections; DWORD TimeDateStamp, PointerToSymbolTable, NumberOfSymbols; WORD SizeOfOptionalHeader, Characteristics; } IMAGE_FILE_HEADER;
typedef struct { WORD Magic; BYTE MajorLinkerVersion, MinorLinkerVersion; DWORD SizeOfCode, SizeOfInitializedData, SizeOfUninitializedData, AddressOfEntryPoint, BaseOfCode;
  ULONGLONG ImageBase; DWORD SectionAlignment, FileAlignment; WORD v[6]; DWORD Win32VersionValue, SizeOfImage, SizeOfHeaders, CheckSum; WORD Subsystem, DllCharacteristics;
  ULONGLONG SizeOfStackReserve, SizeOfStackCommit, SizeOfHeapReserve, SizeOfHeapCommit; DWORD LoaderFlags, NumberOfRvaAndSizes; IMAGE_DATA_DIRECTORY DataDirectory[16]; } IMAGE_OPTIONAL_HEADER64;
typedef struct { DWORD Signature; IMAGE_FILE_HEADER FileHeader; IMAGE_OPTIONAL_HEADER64 OptionalHeader; } IMAGE_NT_HEADERS64;
typedef struct { BYTE Name[8]; union { DWORD PhysicalAddress, VirtualSize; } Misc; DWORD VirtualAddress, SizeOfRawData, PointerToRawData, PointerToRelocations, PointerToLinenumbers; WORD NumberOfRelocations, NumberOfLinenumbers; DWORD Characteristics; } IMAGE_SECTION_HEADER;
#define IMAGE_FIRST_SECTION(n) ((IMAGE_SECTION_HEADER*)((BYTE*)&(n)->OptionalHeader + (n)->FileHeader.SizeOfOptionalHeader))
#define IMAGE_SCN_MEM_EXECUTE 0x20000000
#define IMAGE_SCN_CNT_CODE 0x20
#define MEM_PRIVATE 0x20000
#define MEM_IMAGE 0x1000000
#define MEM_FREE 0x10000
#define THREAD_SUSPEND_RESUME 2
#define THREAD_QUERY_INFORMATION 0x40
#define THREAD_GET_CONTEXT 8
#define THREAD_SET_CONTEXT 0x10
#define CONTEXT_INTEGER 0x100002
#define CONTEXT_CONTROL 0x100001
static inline HANDLE OpenThread(DWORD a, BOOL i, DWORD t) { (void)a; (void)i; (void)t; return 0; }
static inline DWORD SuspendThread(HANDLE h) { (void)h; return 0; }
static inline DWORD ResumeThread(HANDLE h) { (void)h; return 0; }
typedef union { struct { DWORD LowPart; LONG HighPart; }; LONGLONG QuadPart; } LARGE_INTEGER, *PLARGE_INTEGER;
typedef struct { PVOID BaseAddress, AllocationBase; DWORD AllocationProtect; SIZE_T RegionSize; DWORD State, Protect, Type; } MEMORY_BASIC_INFORMATION;
typedef struct { DWORD ExceptionCode, ExceptionFlags; void* ExceptionRecord; PVOID ExceptionAddress; DWORD NumberParameters; ULONG_PTR ExceptionInformation[15]; } EXCEPTION_RECORD;
typedef struct { DWORD64 Rax, Rcx, Rdx, Rbx, Rsp, Rbp, Rsi, Rdi, R8, R9, R10, R11, R12, R13, R14, R15, Rip; DWORD EFlags, ContextFlags; DWORD64 Dr0, Dr1, Dr2, Dr3, Dr6, Dr7; } CONTEXT;
typedef struct { EXCEPTION_RECORD* ExceptionRecord; CONTEXT* ContextRecord; } EXCEPTION_POINTERS, *PEXCEPTION_POINTERS;
typedef LONG (*PVECTORED_EXCEPTION_HANDLER)(EXCEPTION_POINTERS*);
#define WINAPI
#define APIENTRY
#define CALLBACK
#define __declspec(x)
#define TRUE 1
#define FALSE 0
#define MAX_PATH 260
#define INVALID_HANDLE_VALUE ((HANDLE)(intptr_t)-1)
#define PAGE_EXECUTE_READWRITE 0x40
#define PAGE_READWRITE 0x04
#define PAGE_EXECUTE_READ 0x20
#define PAGE_READONLY 0x02
#define PAGE_NOACCESS 0x01
#define PAGE_GUARD 0x100
#define PAGE_EXECUTE 0x10
#define PAGE_EXECUTE_WRITECOPY 0x80
#define PAGE_WRITECOPY 0x08
#define MEM_COMMIT 0x1000
#define MEM_RESERVE 0x2000
#define MEM_RELEASE 0x8000
#define GENERIC_READ 0x80000000u
#define GENERIC_WRITE 0x40000000u
#define FILE_SHARE_READ 1
#define FILE_SHARE_WRITE 2
#define OPEN_EXISTING 3
#define OPEN_ALWAYS 4
#define CREATE_ALWAYS 2
#define FILE_ATTRIBUTE_NORMAL 0x80
#define FILE_BEGIN 0
#define FILE_END 2
#define FILE_CURRENT 1
#define MOVEFILE_REPLACE_EXISTING 1
#define EXCEPTION_CONTINUE_EXECUTION (-1)
#define EXCEPTION_CONTINUE_SEARCH 0
#define CONTEXT_ALL 0x10001f
#define CONTEXT_DEBUG_REGISTERS 0x100010
#define DLL_PROCESS_ATTACH 1
#define DLL_PROCESS_DETACH 0
#define TLS_OUT_OF_INDEXES 0xffffffffu
#define GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS 4
#define GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT 2
static inline HANDLE GetCurrentProcess(void) { return (HANDLE)(intptr_t)-1; }
static inline DWORD GetCurrentThreadId(void) { return 1; }
static inline BOOL VirtualProtect(LPVOID a, SIZE_T n, DWORD p, DWORD* o) { (void)a; (void)n; (void)p; if (o) *o = PAGE_READWRITE; return TRUE; }
static inline BOOL FlushInstructionCache(HANDLE h, LPCVOID a, SIZE_T n) { (void)h; (void)a; (void)n; return TRUE; }
static inline LPVOID VirtualAlloc(LPVOID a, SIZE_T n, DWORD t, DWORD p) { (void)a; (void)t; (void)p; return calloc(1, n); }
static inline BOOL VirtualFree(LPVOID a, SIZE_T n, DWORD t) { (void)n; (void)t; free(a); return TRUE; }
static inline SIZE_T VirtualQuery(LPCVOID a, MEMORY_BASIC_INFORMATION* m, SIZE_T n) { (void)a; (void)n; memset(m, 0, sizeof *m); return 0; }
static inline LONG InterlockedIncrement(volatile LONG* p) { return ++*p; }
static inline BOOL ReadProcessMemory(HANDLE h, LPCVOID a, LPVOID b, SIZE_T n, SIZE_T* got) { (void)h; (void)a; (void)b; (void)n; if (got) *got = 0; return FALSE; }
static inline DWORD TlsAlloc(void) { return 0; }
static inline LPVOID TlsGetValue(DWORD i) { (void)i; return 0; }
static inline BOOL TlsSetValue(DWORD i, LPVOID v) { (void)i; (void)v; return TRUE; }
static inline LONG GetLastError(void) { return 0; }
static inline DWORD GetTickCount(void) { return (DWORD)(clock() * 1000 / CLOCKS_PER_SEC); }
static inline BOOL GetThreadContext(HANDLE h, CONTEXT* c) { (void)h; (void)c; return FALSE; }
static inline BOOL SetThreadContext(HANDLE h, const CONTEXT* c) { (void)h; (void)c; return FALSE; }
static inline HANDLE GetCurrentThread(void) { return (HANDLE)(intptr_t)-2; }
static inline HMODULE GetModuleHandleA(LPCSTR n) { (void)n; return 0; }
static inline BOOL GetModuleHandleExA(DWORD f, LPCSTR n, HMODULE* m) { (void)f; (void)n; if (m) *m = 0; return FALSE; }
static inline DWORD GetModuleFileNameA(HMODULE m, LPSTR s, DWORD n) { (void)m; if (n) s[0] = 0; return 0; }
static inline HMODULE LoadLibraryA(LPCSTR n) { (void)n; return 0; }
static inline void* GetProcAddress(HMODULE m, LPCSTR n) { (void)m; (void)n; return 0; }
static inline PVOID AddVectoredExceptionHandler(ULONG f, PVECTORED_EXCEPTION_HANDLER h) { (void)f; (void)h; return 0; }
static inline WORD RtlCaptureStackBackTrace(DWORD s, DWORD n, PVOID* b, DWORD* h) { (void)s; (void)n; (void)b; if (h) *h = 0; return 0; }
/* files: POSIX file descriptors carried in the HANDLE */
static inline HANDLE CreateFileA(LPCSTR p, DWORD acc, DWORD sh, void* sa, DWORD disp, DWORD fl, HANDLE t)
{
  (void)sh; (void)sa; (void)fl; (void)t;
  int f = (acc & GENERIC_WRITE) ? O_RDWR : O_RDONLY;
  if (disp == OPEN_ALWAYS) f |= O_CREAT; else if (disp == CREATE_ALWAYS) f |= O_CREAT | O_TRUNC;
  int fd = open(p, f, 0644);
  return fd < 0 ? INVALID_HANDLE_VALUE : (HANDLE)(intptr_t)(fd + 1);
}
#define FD_OF(h) ((int)(intptr_t)(h) - 1)
static inline BOOL CloseHandle(HANDLE h) { return close(FD_OF(h)) == 0; }
static inline BOOL ReadFile(HANDLE h, LPVOID b, DWORD n, DWORD* got, void* o) { (void)o; ssize_t r = read(FD_OF(h), b, n); if (got) *got = r < 0 ? 0 : (DWORD)r; return r >= 0; }
static inline BOOL WriteFile(HANDLE h, LPCVOID b, DWORD n, DWORD* put, void* o) { (void)o; ssize_t r = write(FD_OF(h), b, n); if (put) *put = r < 0 ? 0 : (DWORD)r; return r >= 0; }
static inline BOOL SetFilePointerEx(HANDLE h, LARGE_INTEGER d, LARGE_INTEGER* np, DWORD how) { off_t r = lseek(FD_OF(h), d.QuadPart, how == FILE_END ? SEEK_END : how == FILE_CURRENT ? SEEK_CUR : SEEK_SET); if (np) np->QuadPart = r; return r >= 0; }
static inline BOOL SetEndOfFile(HANDLE h) { off_t r = lseek(FD_OF(h), 0, SEEK_CUR); return ftruncate(FD_OF(h), r) == 0; }
static inline BOOL GetFileSizeEx(HANDLE h, LARGE_INTEGER* s) { struct stat st; if (fstat(FD_OF(h), &st)) return FALSE; s->QuadPart = st.st_size; return TRUE; }
static inline BOOL MoveFileExA(LPCSTR a, LPCSTR b, DWORD f) { (void)f; return rename(a, b) == 0; }
static inline BOOL DeleteFileA(LPCSTR a) { return unlink(a) == 0; }
/* the wide calls of fl26savedir.h (the save folder, B296): UTF-8 on this side, a path's
   backslashes as slashes; no shell32, no sys.ini, no folder search (FindFirstFileW finds nothing) */
#include <wchar.h>
#include <wctype.h>
typedef wchar_t WCHAR; typedef wchar_t* LPWSTR; typedef const wchar_t* LPCWSTR;
typedef struct { DWORD dwLowDateTime, dwHighDateTime; } FILETIME;
typedef struct { DWORD dwFileAttributes; FILETIME ftCreationTime, ftLastAccessTime, ftLastWriteTime; DWORD nFileSizeHigh, nFileSizeLow; } WIN32_FILE_ATTRIBUTE_DATA;
typedef struct { DWORD dwFileAttributes; FILETIME ftCreationTime, ftLastAccessTime, ftLastWriteTime; DWORD nFileSizeHigh, nFileSizeLow, dwReserved0, dwReserved1; WCHAR cFileName[MAX_PATH]; WCHAR cAlternateFileName[14]; } WIN32_FIND_DATAW;
#define CP_UTF8 65001
#define GetFileExInfoStandard 0
#define FILE_ATTRIBUTE_DIRECTORY 0x10
static inline int WideCharToMultiByte(UINT cp, DWORD f, LPCWSTR w, int wn, LPSTR out, int cap, LPCSTR d, BOOL* u)
{
  (void)cp; (void)f; (void)wn; (void)d; if (u) *u = 0;
  int n = 0;
  for (; ; w++) {
    unsigned c = (unsigned)*w; char b[4]; int k;
    if (c < 0x80) { b[0] = (char)c; k = 1; }
    else if (c < 0x800) { b[0] = (char)(0xc0 | c >> 6); b[1] = (char)(0x80 | (c & 63)); k = 2; }
    else if (c < 0x10000) { b[0] = (char)(0xe0 | c >> 12); b[1] = (char)(0x80 | (c >> 6 & 63)); b[2] = (char)(0x80 | (c & 63)); k = 3; }
    else { b[0] = (char)(0xf0 | c >> 18); b[1] = (char)(0x80 | (c >> 12 & 63)); b[2] = (char)(0x80 | (c >> 6 & 63)); b[3] = (char)(0x80 | (c & 63)); k = 4; }
    if (out && cap) { if (n + k > cap) return 0; memcpy(out + n, b, k); }
    n += k;
    if (!c) return n;
  }
}
static inline int MultiByteToWideChar(UINT cp, DWORD f, LPCSTR u, int un, LPWSTR out, int cap)
{
  (void)cp; (void)f; (void)un;
  const unsigned char* s = (const unsigned char*)u; int n = 0;
  for (; ; ) {
    unsigned c = *s++;
    if (c >= 0xf0) { c = (c & 7) << 18 | (s[0] & 63) << 12 | (s[1] & 63) << 6 | (s[2] & 63); s += 3; }
    else if (c >= 0xe0) { c = (c & 15) << 12 | (s[0] & 63) << 6 | (s[1] & 63); s += 2; }
    else if (c >= 0xc0) { c = (c & 31) << 6 | (s[0] & 63); s += 1; }
    if (out && cap) { if (n >= cap) return 0; out[n] = (wchar_t)c; }
    n++;
    if (!c) return n;
  }
}
static inline void host_u8path(LPCWSTR w, char* out, int cap)
{
  if (!WideCharToMultiByte(CP_UTF8, 0, w, -1, out, cap, 0, 0)) out[0] = 0;
  for (char* c = out; *c; c++) if (*c == '\\') *c = '/';
}
static inline BOOL GetFileAttributesExW(LPCWSTR p, int lvl, void* info)
{
  (void)lvl; char u[MAX_PATH * 4]; struct stat st; WIN32_FILE_ATTRIBUTE_DATA* a = (WIN32_FILE_ATTRIBUTE_DATA*)info;
  host_u8path(p, u, sizeof u);
  if (stat(u, &st)) return FALSE;
  memset(a, 0, sizeof *a);
  a->dwFileAttributes = S_ISDIR(st.st_mode) ? FILE_ATTRIBUTE_DIRECTORY : FILE_ATTRIBUTE_NORMAL;
  ULONGLONG t = (ULONGLONG)st.st_mtime * 10000000ull + 116444736000000000ull;
  a->ftLastWriteTime.dwLowDateTime = (DWORD)t; a->ftLastWriteTime.dwHighDateTime = (DWORD)(t >> 32);
  a->nFileSizeLow = (DWORD)st.st_size; a->nFileSizeHigh = (DWORD)((ULONGLONG)st.st_size >> 32);
  return TRUE;
}
static inline HANDLE FindFirstFileW(LPCWSTR p, WIN32_FIND_DATAW* f) { (void)p; (void)f; return INVALID_HANDLE_VALUE; }
static inline BOOL FindNextFileW(HANDLE h, WIN32_FIND_DATAW* f) { (void)h; (void)f; return FALSE; }
static inline BOOL FindClose(HANDLE h) { (void)h; return TRUE; }
static inline HMODULE LoadLibraryW(LPCWSTR n) { (void)n; return 0; }
static inline DWORD GetModuleFileNameW(HMODULE m, LPWSTR s, DWORD n) { (void)m; if (n) s[0] = 0; return 0; }
static inline UINT GetPrivateProfileIntW(LPCWSTR a, LPCWSTR k, int d, LPCWSTR f) { (void)a; (void)k; (void)f; return (UINT)d; }
static inline DWORD GetEnvironmentVariableW(LPCWSTR n, LPWSTR b, DWORD cap)
{
  char u[256]; host_u8path(n, u, sizeof u); const char* v = getenv(u);
  if (!v || !cap) return 0;
  return MultiByteToWideChar(CP_UTF8, 0, v, -1, b, (int)cap) ? (DWORD)wcslen(b) : 0;
}
#define _snwprintf swprintf
#define _wcsicmp wcscasecmp
static inline FILE* _wfopen(LPCWSTR p, LPCWSTR m) { char u[MAX_PATH * 4], mo[16]; host_u8path(p, u, sizeof u); WideCharToMultiByte(CP_UTF8, 0, m, -1, mo, sizeof mo, 0, 0); return fopen(u, mo); }
static inline BOOL MoveFileExW(LPCWSTR a, LPCWSTR b, DWORD f) { (void)f; char x[MAX_PATH * 4], y[MAX_PATH * 4]; host_u8path(a, x, sizeof x); host_u8path(b, y, sizeof y); return rename(x, y) == 0; }
static inline HANDLE CreateFileW(LPCWSTR p, DWORD acc, DWORD sh, void* sa, DWORD disp, DWORD fl, HANDLE t)
{ char u[MAX_PATH * 4]; host_u8path(p, u, sizeof u); return CreateFileA(u, acc, sh, sa, disp, fl, t); }
#include <x86intrin.h>
static inline ULONGLONG GetTickCount64(void) { return (ULONGLONG)clock() * 1000 / CLOCKS_PER_SEC; }
static inline LONG64 InterlockedCompareExchange64(volatile LONG64* d, LONG64 x, LONG64 c) { LONG64 o = *d; if (o == c) *d = x; return o; }
static inline BOOL IsBadReadPtr(const void* p, ULONG_PTR n) { (void)n; return p == 0; }
static inline DWORD GetTempPathA(DWORD n, LPSTR b) { const char* t = getenv("TMPDIR"); if (!t) t = "/tmp"; snprintf(b, n, "%s/", t); return (DWORD)strlen(b); }
static inline DWORD GetCurrentProcessId(void) { return (DWORD)getpid(); }
#endif
