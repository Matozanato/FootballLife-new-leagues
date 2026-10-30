/* test_savedir.c -- fl26savedir.h without the game (tools/test_savedir.py builds and runs it).
 *
 *   test_savedir.exe dir         print the save folder the modules use (UTF-8)
 *   test_savedir.exe put         write probe.fl26x in that folder through fl26_u8open, move it to
 *                                probe.fl26x.moved through fl26_u8move, read it back
 *
 * FL26_TEST_DOCS is the Documents folder; sys.ini is read next to this exe, as next to the game's. */
#define FL26_SAVEDIR_TEST
#include "fl26savedir.h"
#include <string.h>

int main(int argc, char** argv)
{
  if (argc >= 2 && !strcmp(argv[1], "dir")) {
    char d[1024];
    if (!fl26_save_dir(d, sizeof d)) { puts("no folder"); return 1; }
    fwrite(d, 1, strlen(d), stdout);
    putchar('\n');
    return 0;
  }
  if (argc >= 2 && !strcmp(argv[1], "put")) {
    char d[1024], file[1100], moved[1200];
    if (!fl26_save_dir(d, sizeof d)) { puts("no folder"); return 1; }
    snprintf(file, sizeof file, "%s\\probe.fl26x", d);
    FILE* f = fl26_u8open(file, L"wb");
    if (!f) { puts("cannot write"); return 1; }
    fputs("FL26", f);
    fclose(f);
    snprintf(moved, sizeof moved, "%s.moved", file);
    if (!fl26_u8move(file, moved)) { puts("cannot move"); return 1; }
    char b[8] = {0};
    f = fl26_u8open(moved, L"rb");
    if (!f || fread(b, 1, 4, f) != 4 || strcmp(b, "FL26")) { puts("cannot read back"); return 1; }
    fclose(f);
    puts("written");
    return 0;
  }
  return 2;
}
