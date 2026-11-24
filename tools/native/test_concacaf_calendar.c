/* Actual shared scheduler with a CONCACAF fallback league, without game pointers. */
#define FL26_RCAL_TEST
#include "fl26swiss.c"
#include <assert.h>
int rcal_test_today(void) { return 0; }
int rcal_test_invites(int k, uint16_t id) { (void)k; (void)id; return 0; }
int rcal_test_recday(uint16_t id) { (void)id; return -1; }
int rcal_test_dayload(int d) { (void)d; return 0; }
int rcal_test_round(uint16_t id) { (void)id; return 0; }
static date_t fake_dates[8];
static uint64_t lib_calendar(uint64_t reg, void* out)
{
  static const date_t lib[] = {
    {216,46,0},{223,46,1},{258,51,0},{265,51,1},
    {296,52,0},{303,52,1},{331,53,2},{331,54,2}
  };
  assert((uint16_t)reg==R_LIBKO);
  memcpy(fake_dates,lib,sizeof lib);
  vec_t* v=out;
  v->b=(unsigned char*)fake_dates;
  v->e=v->c=v->b+sizeof fake_dates;
  return 1;
}
int main(void)
{
  g_test_year=2026;
  g_cq_enabled=1; g_cq.ko=500; g_cq.pre=501;
  g_cq.days[0]=33; g_cq.days[1]=40; g_cq.ns=2;
  g_cq.source[0].reg=300; g_cq.source[1].reg=301;
  g_nccup=2; memset(g_ccup,0,sizeof g_ccup);
  g_ccup[0].reg=g_ccup[0].ko=500;
  const uint16_t days[7]={61,68,89,96,117,124,145};
  memcpy(g_ccup[0].days,days,sizeof days); g_ccup[0].nd=7;
  g_ccup[0].n=16; g_ccup[0].ereg[0]=300; g_ccup[0].erank[0]=1;
  g_ccup[1].reg=g_ccup[1].ko=510;
  g_tramp_date=(unsigned char*)(uintptr_t)lib_calendar;
  vec_t vdates={0};
  assert(ccup_dates(0,1,500,500,&vdates)==1);
  assert(vdates.e-vdates.b==7*sizeof(date_t));
  static const unsigned stage[]={46,46,51,51,52,52,53};
  static const unsigned leg[]={0,1,0,1,0,1,2};
  static const unsigned count[]={8,8,4,4,2,2,1};
  unsigned fixtures=0;
  for (int i=0;i<7;i++) {
    assert(fake_dates[i].day==days[i]);
    assert(fake_dates[i].round==stage[i]);
    assert(fake_dates[i].kind==leg[i]);
    fixtures+=count[i];
  }
  assert(fixtures==29);
  assert(!cq_ko_dates(&g_ccup[0],fake_dates,6));
  assert(ko_text(130,500,16,"test")==0x3a20019u);
  assert(kolist_test(500)==1);
  assert(!ccup_cont_ko(501) && !ccup_cont_ko(510));
  assert(ccup_feeds(0,300)); assert(ccup_feeds(0,301)); /* fallback source also protected */
  assert(!ccup_feeds(0,302)); assert(!ccup_feeds(1,301));
  const uint16_t sum[] = {301, 303, 304, 0};
  assert(fl26_swiss_seasonsum(sum, 1) == 1);
  assert(cq_membership_reg(301) == 303);
  assert(ccup_feeds(0,303) && ccup_feeds(0,304) && !ccup_feeds(1,304));
  busy_t busy[BUSY_MAX]; int n=busy_set(304,busy), found=0;
  uint32_t reserved[9]={33,40,61,68,89,96,117,124,145};
  for (int i=0;i<n;i++) if (busy[i].kind==BZ_CONT) {
    for (int j=0;j<9;j++) if (busy[i].day==reserved[j]) found++;
  }
  assert(found==9);
  g_car_enabled=1;
  g_car.group=519; g_car.ko=510; g_car.n=1;
  g_car.sources[0]=(car_source){305,305,1,0};
  assert(ccup_dates(1,1,510,510,&vdates)==1);
  assert(vdates.e-vdates.b==6*sizeof(date_t));
  const unsigned car_stage[]={46,46,53,53,54,54};
  const unsigned car_ko_days[]={286,293,334,338,334,338};
  unsigned car_fixtures=20;
  for (int i=0;i<6;i++) {
    assert(fake_dates[i].round==car_stage[i] && fake_dates[i].kind==(unsigned)(i%2));
    assert(fake_dates[i].day==car_ko_days[i]);
    car_fixtures+=i<2 ? 2 : 1;
  }
  assert(car_fixtures==28);
  n=busy_set(305,busy); found=0;
  const unsigned car_days[]={216,230,244,251,258,286,293,334,338};
  for (int i=0;i<n;i++) if (busy[i].kind==BZ_CONT) {
    for (int j=0;j<9;j++) if (busy[i].day==car_days[j]) found++;
  }
  assert(found==9);
  assert(!ccup_feeds(1,304));
  unsigned char records[10][MATCH_STRIDE]={{0}};
  uint32_t group[]={1u<<14,2u<<14,3u<<14,4u<<14,5u<<14};
  const unsigned char dates[][2]={{8,5},{8,19},{9,2},{9,9},{9,16}};
  for (unsigned d=0;d<5;d++) for (unsigned pair=1;pair<=2;pair++) {
    unsigned char* m=records[d*2+pair-1];
    unsigned h,a;
    car_pair(d,pair,&h,&a);
    *(uint16_t*)(m+4)=1543; m[6]=(unsigned char)d; m[7]=0x60;
    *(uint16_t*)(m+8)=2026; m[10]=dates[d][0]; m[11]=dates[d][1];
    *(uint32_t*)(m+0x14)=group[h]; *(uint32_t*)(m+0x18)=group[a];
    m[0x1c]=(h<a); m[0x1f]=(a<h);
  }
  car_stats table[5]={{0}};
  int order[5];
  assert(car_group_results(records[0],10,1543,2026,group,table,order));
  for (int i=0;i<5;i++) assert(order[i]==i && table[i].pts==12-3*i);
  records[9][7]=0;
  assert(!car_group_results(records[0],10,1543,2026,group,table,order));
  g_car_enabled=0;
  uint16_t recipe[8]={304,51,339,0,0,96,16,0};
  assert(fl26_swiss_rcal(recipe,1)==1);
  date_t rounds[30]; memset(rounds,0,sizeof rounds);
  assert(rcal_dates(304,rcal_of(304),rounds,30,1)>=0);
  for (int i=0;i<30;i++) for (int j=0;j<9;j++) {
    int gap=abs((int)rounds[i].day-(int)reserved[j]); if (gap>182) gap=365-gap;
    assert(gap>=3);
  }
  /* The actual adapter must fail closed if hooks are absent: neither legacy
   * filler may touch game pointers after the rejected modern contract. */
  uint16_t v[200]={1,500,501,243,33,40,1,300,0,0,28}; int words=11;
  for (int i=0;i<27;i++) {
    v[words++]=(uint16_t)(i<5); v[words++]=0; v[words++]=1; v[words++]=1; v[words++]=0;
  }
  assert(fl26_swiss_concacaf(v,words)==-3);
  assert(g_cq_blocked && !g_cq_enabled);
  g_lpre[0].reg=501;
  lpre_fill(0);
  assert(ccup_fill_one(0,0)==0);
  puts("CONCACAF: both qualification leagues reserve all nine dates; 30 domestic rounds stay at least three days clear; unrelated cup unchanged");
  return 0;
}
