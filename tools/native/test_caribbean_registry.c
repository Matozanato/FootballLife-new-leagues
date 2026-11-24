/* Native calls in the same order as fl26swiss.lua, without loading FL27. */
#define FL26_RCAL_TEST
#include "fl26swiss.c"
#include <assert.h>

int rcal_test_today(void) { return 0; }
int rcal_test_invites(int k, uint16_t id) { (void)k; (void)id; return 0; }
int rcal_test_recday(uint16_t id) { (void)id; return -1; }
int rcal_test_dayload(int d) { (void)d; return 0; }
int rcal_test_round(uint16_t id) { (void)id; return 0; }

static int cup(uint16_t* out, uint16_t reg, uint16_t ko, uint16_t groups, int entries)
{
  out[0]=reg; out[1]=ko; out[2]=groups; out[3]=(uint16_t)entries;
  for (int i=0;i<entries;i++) {
    out[4+2*i]=51; out[5+2*i]=(uint16_t)(i+1);
  }
  return 4+2*entries;
}

static int champions(uint16_t* out, int regional)
{
  const uint16_t prefix[]={1,623,707,1,33,40,1,51,0,0,30};
  memcpy(out,prefix,sizeof prefix);
  int n=11;
  if (regional) {
    out[6]=2;
    out[n++]=(uint16_t)regional; out[n++]=2; out[n++]=2; out[n++]=4;
  }
  for (int i=0;i<27;i++) {
    int fed=regional && (i==4 || i==5 || i==6);
    out[n++]=i<5; out[n++]=fed; out[n++]=1; out[n++]=0;
    if (fed) { out[n++]=1; out[n++]=(uint16_t)(i-3); }
    out[n++]=0;
  }
  return n;
}

static void register_round_one(void)
{
  uint16_t pre[50]={707,623,1,33,40,22};
  for (int i=0;i<22;i++) {
    pre[6+2*i]=51; pre[7+2*i]=(uint16_t)(i+1);
  }
  assert(fl26_swiss_lpre(pre,1)==1);
}

static uint64_t native_kolist(uint64_t reg)
{
  assert(reg != 0);
  return 0;
}

static void check_pair(uint16_t group, uint16_t ko)
{
  uint16_t v[128], combined[200], config[]={1,group,ko,1,220,220,2,0};
  int p=cup(v,623,623,0,16);
  int other=p;
  p+=cup(v+p,550,551,2,8);
  int car=p;
  p+=cup(v+p,group,ko,2,10);
  int nw=champions(combined,ko);
  assert(fl26_swiss_ccup(v,3)==2 && !g_car_enabled);
  assert(!fl26_swiss_caribbean(config,8));
  register_round_one();
  assert(fl26_swiss_concacaf(combined,nw)<0);

  assert(fl26_swiss_ccup_caribbean(v,p,3,config,8)==3);
  assert(g_car_enabled && g_car.group==group && g_car.ko==ko);
  register_round_one();
  assert(fl26_swiss_concacaf(combined,nw)==1 && g_cq_enabled);
  uint16_t retained[CQ_NATIVE_REGS];
  assert(cq_native_regs(retained)==13);
  assert(retained[0]==g_cq.ko && retained[1]==g_cq.pre);
  for (int i=0;i<11;i++) assert(retained[i+2]==g_cq.pre+1024*(i+1));
  assert(!cq_native_has(retained,13,group) && !cq_native_has(retained,13,ko));
  uint16_t july[]={2,group,retained[0],ko,retained[12]}, out[16];
  assert(cq_teardown_filter(out,july,5,retained,13)==3);
  assert(out[0]==2 && out[1]==group && out[2]==ko);
  assert(cq_teardown_filter(out,july,5,retained,0)==5);
  out[0]=8; out[1]=retained[12];
  assert(cq_teardown_append(out,2,retained,13)==14);
  for (int i=0;i<13;i++) assert(cq_native_has(out,14,retained[i]));
  uint64_t saved_base=g_base;
  g_base=(uintptr_t)native_kolist-KOLIST_RVA;
  assert(kolist_test(ko)==0);
  assert(kolist_test(551)==1);
  assert(kolist_test(g_cq.ko)==1);
  g_car_enabled=0;
  assert(kolist_test(ko)==1);
  g_car_enabled=1;
  g_base=saved_base;

  assert(fl26_swiss_ccup_caribbean(v,p-1,3,config,8)<0);
  assert(fl26_swiss_ccup_caribbean(v,p,3,config,7)<0);
  config[0]=2;
  assert(fl26_swiss_ccup_caribbean(v,p,3,config,8)<0);
  config[0]=1;
  v[car+2]=1;
  assert(fl26_swiss_ccup_caribbean(v,p,3,config,8)<0);
  v[car+2]=2;
  v[car+1]++;
  assert(fl26_swiss_ccup_caribbean(v,p,3,config,8)<0);
  v[car+1]--;
  assert(g_cq_enabled && g_car_enabled);
  int end=p+cup(v+p,group,ko,2,10);
  assert(fl26_swiss_ccup_caribbean(v,end,4,config,8)<0);

  /* A five-club shape on a different cup still fails the four-club check. */
  p=other+cup(v+other,550,551,2,10);
  p+=cup(v+p,group,ko,2,10);
  assert(fl26_swiss_ccup_caribbean(v,p,3,config,8)==2);
  assert(g_ccup[1].reg==group);

  assert(fl26_swiss_ccup(v,1)==1 && !g_car_enabled);
  register_round_one();
  nw=champions(combined,0);
  assert(fl26_swiss_concacaf(combined,nw)==1 && g_cq_enabled);
}

static void check_world(const char* path)
{
  FILE* f=fopen(path,"rb");
  assert(f);
  uint16_t header[6], data[8192];
  assert(fread(header,sizeof(uint16_t),6,f)==6);
  size_t words=fread(data,sizeof(uint16_t),8192,f);
  fclose(f);
  unsigned count=header[0], cups=header[1], pre=header[2], cc=header[3], car=header[4];
  unsigned like=header[5];
  assert(words==cups+pre+cc+car+2*like);
  assert(fl26_swiss_ccup_like(data+cups+pre+cc+car,like)==(int)like);
  assert(fl26_swiss_ccup_caribbean(data,cups,count,data+cups+pre+cc,car)==(int)count);
  assert(fl26_swiss_lpre(data+cups,1)==1);
  assert(fl26_swiss_concacaf(data+cups+pre,cc)==1 && g_car_enabled && g_cq_enabled);
  puts("Actual combined development world accepted both contracts.");
}

int main(int argc, char** argv)
{
  uintptr_t mock=(uintptr_t)VirtualAlloc(0,MATCH_CAP_SITE+16,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);
  assert(mock);
  memcpy((void*)(mock+MATCH_BASE_SITE),"\x48\x8d\x88",3);
  memcpy((void*)(mock+MATCH_CAP_SITE),"\x81\xff",2);
  g_base=mock; g_cq_hooks=1;
  check_pair(709,710);
  check_pair(818,819);
  if (argc>1) check_world(argv[1]);
  VirtualFree((void*)mock,0,MEM_RELEASE);
  puts("Combined and standalone registry order, dynamic IDs and malformed inputs passed.");
}
