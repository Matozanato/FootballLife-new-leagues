/* Exercise the exact-list bridge without executing the game's teardown. */
#include "fl26join.c"
#include <assert.h>

static unsigned calls;
static const uint16_t central[]={700,1724,2748,3772,4796,701,702,1726,2750};
static const uint16_t leagues[]={700,701,702,703,704,705};
static char close_native(void* ctx, vec16_t* ids)
{
  assert(ctx==(void*)(uintptr_t)42);
  assert(ids->c==ids->e);
  if (ids->e-ids->b==4)
    assert(ids->b[0]==818 && ids->b[1]==1842 && ids->b[2]==2866 && ids->b[3]==819);
  else if (ids->e-ids->b==9)
    assert(ids->e-ids->b==9 && !memcmp(ids->b,central,sizeof central));
  else if (ids->e-ids->b==60) {
    assert(ids->e-ids->b==60);
    for (int b=0;b<6;b++) for (int t=0;t<10;t++)
      assert(ids->b[b*10+t]==leagues[b]+1024*t);
  } else if (ids->e-ids->b==5) {
    for (int t=0;t<5;t++) assert(ids->b[t]==715+1024*t);
  } else {
    assert(ids->e-ids->b==71);
    const uint16_t* slot=ids->b;
    const uint16_t moved[]={709,710,711,712,713,714,715,716,734};
    for (int i=0;i<9;i++)
      for (int t=0;t<=(i<6 ? 9 : i==6 ? 4 : 2);t++)
        assert(*slot++==(ids->b[0]==700 ? 700+i : moved[i])+1024*t);
    assert(slot==ids->e);
  }
  calls++;
  return 1;
}

int main(void)
{
  /* The cup-only path installs a real teardown trampoline and leaves league
   * registration untouched. Its normal teardown list is a passthrough. */
  unsigned char* exe=VirtualAlloc(0,TEARDOWN_RVA+0x1000,MEM_COMMIT|MEM_RESERVE,PAGE_EXECUTE_READWRITE);
  assert(exe);
  assert(fl26_join_install_rollback((uintptr_t)exe)!=0 && !g_tramp_teardown);
  memcpy(exe+TEARDOWN_RVA,SIG_TEARDOWN,sizeof SIG_TEARDOWN);
  assert(fl26_join_install_rollback((uintptr_t)exe)==0 && g_tramp_teardown);
  assert(fl26_join_install_rollback((uintptr_t)exe)==0 && !g_tramp_join && !g_tramp_reg);
  vec16_t sample={0};
  assert(teardown_pre(0,&sample)==&sample && g_rollback_only);
  VirtualFree(exe,0,MEM_RELEASE);
  g_tramp_teardown=0;
  g_rollback_only=0;
  uint16_t ids[]={818,1842,2866,819};
  void* ctx=(void*)(uintptr_t)42;
  assert(!fl26_join_close_caribbean(ctx,ids));
  assert(!fl26_join_rollback_leagues(ctx,0));
  g_tramp_teardown=(unsigned char*)(uintptr_t)close_native;
  assert(!fl26_join_close_caribbean(0,ids));
  assert(fl26_join_close_caribbean(ctx,ids));
  ids[2]++;
  assert(!fl26_join_close_caribbean(ctx,ids));
  assert(calls==1);
  puts("Caribbean exact close: original context and four dynamic IDs, invalid requests rejected");
  assert(!fl26_join_close_central_probe(0,central));
  assert(fl26_join_close_central_probe(ctx,central));
  uint16_t bad[9];
  memcpy(bad,central,sizeof bad);
  bad[8]++;
  assert(!fl26_join_close_central_probe(ctx,bad));
  bad[8]--; bad[5]=bad[6];
  assert(!fl26_join_close_central_probe(ctx,bad));
  assert(calls==2);
  puts("Central American Cup exact close: original context and nine IDs, invalid requests rejected");
  assert(!fl26_join_rollback_leagues(0,leagues));
  assert(fl26_join_rollback_leagues(ctx,0) && calls==2);
  assert(fl26_join_rollback_leagues(ctx,leagues));
  uint16_t duplicated[]={700,701,702,703,704,700};
  assert(!fl26_join_rollback_leagues(ctx,duplicated) && calls==3);
  assert(!fl26_join_close_leagues_edition(0));
  assert(fl26_join_close_leagues_edition(ctx) && calls==4);
  uint16_t moved[]={709,710,711,712,713,714,715,716,734};
  assert(fl26_join_close_leagues_edition_ids(ctx,moved) && calls==5);
  moved[8]=715;
  assert(!fl26_join_close_leagues_edition_ids(ctx,moved) && calls==5);
  assert(fl26_join_rollback_leagues_stage_ids(ctx,715,4) && calls==6);
  puts("Leagues Cup rollback: original context and exactly 60 owned IDs");
}
