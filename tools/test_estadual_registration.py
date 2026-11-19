"""Executa a decisão de entrada compilada das duas fontes e a lista real de janeiro."""
from pathlib import Path
import subprocess
import sys
import tempfile


def test(source,zig):
    src=source.read_text(encoding="utf8")
    cfg=src[src.index("static int g_build_brazil;"):src.index("vec16_t* bld_pre(uint64_t")]
    door=src[src.index("int door_pre(uint64_t"):src.index("void door_post(")]
    stubs="""
#include <stdint.h>
#include <string.h>
#include <assert.h>
#define BLD_RET_RVA 42
#define logf(...) ((void)0)
static uint64_t g_base;
static int g_euro_build,g_stat[16],g_door_yes[256],live;
static uint32_t data[256];
static int ours(int id){return id==181||id==182||id==11;}
static int calyr(int id){return ours(id);}
static void free_stale_rounds(int id){}
static void timeline_check(const char*a,int b){}
static void canon_listed(int id){}
static void count_listed(int id){}
static unsigned char* find_record(int id){return (unsigned char*)data;}
static int live_rounds(int id,const unsigned char*r){return live;}
"""
    cases="""
int main(void){
  uint16_t br[]={8,29,31,55,97,163},july[]={2,29,163}, other[]={55,97}, states[]={181,182};
  assert(fl26_join_estaduais(states,2)==2);
  g_build_brazil=state_builder(br,6); assert(g_build_brazil);
  data[0x30c/4]=12;
  assert(door_pre(181,42)==1); /* no field */
  for(int i=0;i<12;++i)data[0x170/4+i]=(i+1)<<14;
  assert(door_pre(181,42)==0 && (data[0x304/4]&256));
  g_door_yes[181]=1; assert(door_pre(181,42)==1);
  g_door_yes[181]=0;live=1;assert(door_pre(181,42)==1); /* reload */
  live=0;assert(door_pre(182,42)==0 && door_pre(11,42)==1);
  g_build_brazil=state_builder(july,3);assert(!g_build_brazil && door_pre(181,42)==1);
  g_build_brazil=state_builder(other,2);assert(!g_build_brazil);
  assert(door_pre(181,99)==0); /* ordinary registration uses existing deduplication */
  return 0;
}
"""
    with tempfile.TemporaryDirectory() as folder:
        c=Path(folder)/"registro.c"
        c.write_text(stubs+cfg+door+cases,encoding="utf8")
        exe=c.with_suffix(".exe")
        subprocess.run([str(zig),"cc","-target","x86_64-windows-gnu","-O1",str(c),"-o",str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
    print("OK:",source)


if __name__=="__main__":
    for s in sys.argv[2:]:
        test(Path(s),Path(sys.argv[1]).resolve())
