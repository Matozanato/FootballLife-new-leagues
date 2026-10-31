/* fl26savedir.h -- the game's save folder, found the way the game finds it (B296).
 *
 * The game keeps its saves in <Documents>\KONAMI\eFootball PES 2021 SEASON UPDATE\<id>\save, <id>
 * the SteamID of sys.ini beside FL_2026.exe (2026 in FL26). Two things broke a fixed
 * "...\2026\save" built with the ANSI calls (GiorgiM 30.10.):
 *   - a Documents folder in letters outside the ANSI code page (C:\დოკუმენტები) came back as
 *     C:\???, a folder that does not exist, so nothing could be written there;
 *   - when the Steam emulator does not read sys.ini the game saves under 0, not 2026 (our own
 *     E:\fútbol test made an empty ...\0\save too).
 * So: Documents by the wide call, and the <id> folder whose save holds SYSTEM00000000 -- sys.ini's
 * first, else the one written last. Paths go out in UTF-8 (the logs take them as they are);
 * fl26_u8open / fl26_u8move turn them back into wide ones for the file calls.
 *
 * kernel32 only: shell32 is asked at run time, as fl26swiss.dll imports nothing else. */
#ifndef FL26SAVEDIR_H
#define FL26SAVEDIR_H
#include <windows.h>
#include <stdio.h>
#include <wchar.h>

#define FL26_SAVE_ID_DEFAULT 2026
#define FL27_SAVE_ID_DEFAULT 2027

static int fl26_w2u(const wchar_t* w, char* out, int cap)
{
  int n = WideCharToMultiByte(CP_UTF8, 0, w, -1, out, cap, 0, 0);
  if (n <= 0) { if (cap) out[0] = 0; return 0; }
  return 1;
}

static int fl26_u2w(const char* u, wchar_t* out, int cap)
{
  int n = MultiByteToWideChar(CP_UTF8, 0, u, -1, out, cap);
  if (n <= 0) { if (cap) out[0] = 0; return 0; }
  return 1;
}

/* the time SYSTEM00000000 was last written in base\<name>\save, 0 when it is not there */
static ULONGLONG fl26_system_time(const wchar_t* base, const wchar_t* name)
{
  wchar_t p[MAX_PATH * 2];
  WIN32_FILE_ATTRIBUTE_DATA a;
  _snwprintf(p, MAX_PATH * 2, L"%ls\\%ls\\save\\SYSTEM00000000", base, name);
  p[MAX_PATH * 2 - 1] = 0;
  if (!GetFileAttributesExW(p, GetFileExInfoStandard, &a) || (a.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY))
    return 0;
  return ((ULONGLONG)a.ftLastWriteTime.dwHighDateTime << 32) | a.ftLastWriteTime.dwLowDateTime;
}

/* <Documents>\KONAMI\eFootball PES 2021 SEASON UPDATE\<id>\save in UTF-8 into out; 0 when there is
   no Documents folder */
static int fl26_save_dir(char* out, int cap)
{
  typedef HRESULT (WINAPI *folder_fn)(HWND, int, HANDLE, DWORD, LPWSTR);
  static folder_fn get = 0;
  if (!get) {
    HMODULE sh = LoadLibraryW(L"shell32.dll");
    get = sh ? (folder_fn)(uintptr_t)GetProcAddress(sh, "SHGetFolderPathW") : 0;
  }
  wchar_t docs[MAX_PATH], base[MAX_PATH * 2], ini[MAX_PATH * 2], id[16], best[MAX_PATH], full[MAX_PATH * 2];
#ifdef FL26_SAVEDIR_TEST
  /* tools/test_savedir.py: a Documents folder of its own */
  if (!GetEnvironmentVariableW(L"FL26_TEST_DOCS", docs, MAX_PATH)) return 0;
#else
  if (!get || get(0, 5 /* CSIDL_PERSONAL */, 0, 0, docs) != 0) return 0;
#endif
  /* sys.ini's SteamID (the game's folder: the exe's). FL27 (31.10.2026) is the same exe named
     FL_2027.exe, and it saves under <Documents>\SPGAME\Football Life\<id>, 2027 by default. */
  int fl27 = 0, def = FL26_SAVE_ID_DEFAULT, sid;
  wchar_t* slash = 0;
  DWORD n = GetModuleFileNameW(0, ini, MAX_PATH * 2);
  if (n && n < MAX_PATH * 2) {
    slash = wcsrchr(ini, L'\\');
    if (slash && !_wcsicmp(slash + 1, L"FL_2027.exe")) fl27 = 1;
  }
#ifdef FL26_SAVEDIR_TEST
  if (GetEnvironmentVariableW(L"FL26_TEST_FL27", id, 16)) fl27 = 1;
#endif
  if (fl27) def = FL27_SAVE_ID_DEFAULT;
  sid = def;
  if (slash && (size_t)(slash - ini) + 9 < MAX_PATH * 2) {
    wcscpy(slash + 1, L"sys.ini");
    sid = (int)GetPrivateProfileIntW(L"Settings", L"SteamID", def, ini);
  }
  _snwprintf(base, MAX_PATH * 2, fl27 ? L"%ls\\SPGAME\\Football Life" : L"%ls\\KONAMI\\eFootball PES 2021 SEASON UPDATE",
             docs);
  base[MAX_PATH * 2 - 1] = 0;
  _snwprintf(id, 16, L"%d", sid);
  id[15] = 0;
  wcscpy(best, id);

  /* sys.ini's folder when the game saves there, else the folder whose SYSTEM was written last */
  if (!fl26_system_time(base, id)) {
    ULONGLONG newest = 0;
    WIN32_FIND_DATAW f;
    wchar_t pat[MAX_PATH * 2];
    _snwprintf(pat, MAX_PATH * 2, L"%ls\\*", base);
    pat[MAX_PATH * 2 - 1] = 0;
    HANDLE h = FindFirstFileW(pat, &f);
    if (h != INVALID_HANDLE_VALUE) {
      do {
        if (!(f.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) || !f.cFileName[0] || wcslen(f.cFileName) >= MAX_PATH)
          continue;
        int digits = 1;
        for (const wchar_t* c = f.cFileName; *c; c++) if (*c < L'0' || *c > L'9') { digits = 0; break; }
        if (!digits) continue;
        ULONGLONG t = fl26_system_time(base, f.cFileName);
        if (t > newest) { newest = t; wcscpy(best, f.cFileName); }
      } while (FindNextFileW(h, &f));
      FindClose(h);
    }
  }
  _snwprintf(full, MAX_PATH * 2, L"%ls\\%ls\\save", base, best);
  full[MAX_PATH * 2 - 1] = 0;
  return fl26_w2u(full, out, cap);
}

static FILE* fl26_u8open(const char* path, const wchar_t* mode)
{
  wchar_t w[MAX_PATH * 2];
  if (!fl26_u2w(path, w, MAX_PATH * 2)) return 0;
  return _wfopen(w, mode);
}

static BOOL fl26_u8move(const char* from, const char* to)
{
  wchar_t a[MAX_PATH * 2], b[MAX_PATH * 2];
  if (!fl26_u2w(from, a, MAX_PATH * 2) || !fl26_u2w(to, b, MAX_PATH * 2)) return FALSE;
  return MoveFileExW(a, b, MOVEFILE_REPLACE_EXISTING);
}
#endif
