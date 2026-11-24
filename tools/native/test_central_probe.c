/* Exercise the prototype's actual runtime adapters with synthetic native records. */
#define FL26_RCAL_TEST
#include "fl26swiss.c"
#include <assert.h>

int rcal_test_today(void) { return 0; }
int rcal_test_invites(int k, uint16_t id) { (void)k; (void)id; return 0; }
int rcal_test_recday(uint16_t id) { (void)id; return -1; }
int rcal_test_dayload(int d) { (void)d; return 0; }
int rcal_test_round(uint16_t id) { (void)id; return 0; }

static void test_initialization(void)
{
  /* August 27 live state: reg 701 already had season 2026, but no entrants,
     round rows or fixtures. Do not require closing it before native start. */
  ca_registration main={2026,0,0,0,1};
  assert(ca_can_initialize(&main,1,2026));
  main.marker=0xffff;
  assert(ca_can_initialize(&main,1,2026));
  main.marker=2025;
  assert(!ca_can_initialize(&main,1,2026));
  main.marker=2027;
  assert(!ca_can_initialize(&main,1,2026));
  main.marker=2026;
  main.live=0;
  assert(!ca_can_initialize(&main,1,2026));
  main.live=1;
  main.entrants=8;
  assert(!ca_can_initialize(&main,1,2026));
  main.entrants=0; main.rows=1;
  assert(!ca_can_initialize(&main,1,2026));
  main.rows=0; main.fixtures=1;
  assert(!ca_can_initialize(&main,1,2026));
  main.fixtures=0;
  ca_registration helper[]={main,{0xffff,0,0,0,1},{2026,0,0,0,1}};
  assert(ca_can_initialize(helper,3,2026));
  helper[2].rows=1;
  assert(!ca_can_initialize(helper,3,2026));
  helper[2].rows=0; helper[1].entrants=2;
  assert(!ca_can_initialize(helper,3,2026));
  helper[1].entrants=0; helper[0].fixtures=2;
  assert(!ca_can_initialize(helper,3,2026));
}

static void test_same_day_retry(void)
{
  const int aug27=2026*365+238;
  ca_retry retry={.date=-1};
  int attempted=0, completed=0;
  ca_registration empty={2026,0,0,0,1};
  ca_registration unavailable={0};

  /* A direct load can give Lua a date before the native records are ready. */
  assert(ca_pending(238,completed,0));
  assert(ca_retry_due(&retry,aug27,0,1000));
  assert(!ca_claim_initialization(&attempted,2,&unavailable,1,2026));
  assert(attempted==0 && ca_pending(238,completed,0));
  assert(!ca_retry_due(&retry,aug27,0,1001));
  assert(ca_retry_due(&retry,aug27,0,1250));
  assert(ca_claim_initialization(&attempted,2,&empty,1,2026));
  assert(!ca_claim_initialization(&attempted,2,&empty,1,2026));
  completed|=2;
  assert(!ca_pending(238,completed,0) && !ca_pending(238,completed,1));

  /* The first native day tick can arrive before the loader's retry is due. */
  retry.date=-1;
  attempted=0;
  assert(ca_retry_due(&retry,aug27,0,2000));
  assert(!ca_claim_initialization(&attempted,2,&unavailable,1,2026));
  assert(ca_retry_due(&retry,aug27,1,2001));
  assert(ca_claim_initialization(&attempted,2,&empty,1,2026));
  assert(!ca_retry_due(&retry,aug27,1,2002));
  assert(!ca_retry_due(&retry,aug27,0,2003));
  assert(ca_retry_due(&retry,aug27,1,2501));
  assert(!ca_claim_initialization(&attempted,2,&empty,1,2026));
  attempted=0; /* A reloaded bracket owns fixtures even with no in-memory attempt. */
  empty.fixtures=8;
  assert(!ca_claim_initialization(&attempted,2,&empty,1,2026));

  const int days[]={201,237,258,300,339};
  assert(!ca_pending(201,0,0)); /* Group registration and teardown need native context. */
  ca_fixtures groups={.year=2026,.counts={0,10,10,10,10}};
  assert(ca_groups_scheduled(&groups,2026));
  assert(!ca_groups_scheduled(&groups,2027));
  groups.counts[4]=9;
  assert(!ca_groups_scheduled(&groups,2026));
  for (int i=0;i<5;i++) {
    assert(ca_pending(days[i],0,1));
    assert(ca_retry_due(&retry,2026*365+days[i],1,3000));
    assert(!ca_retry_due(&retry,2026*365+days[i],1,3001));
    assert(!ca_pending(days[i],1<<i,1));
  }
  /* Direct loads deeper in a transition window get a retry on that date too. */
  assert(ca_pending(245,0,0) && ca_retry_due(&retry,2026*365+245,0,4000));
  assert(ca_retry_due(&retry,2026*365+245,0,4250));
}

static date_t date_rows[8];
static unsigned char mock_round[0x208], mock_semi[0x208], mock_final[0x208], mock_stage54[0x208];
static unsigned char mock_qf[14][MATCH_STRIDE], mock_owner[0x50];
static unsigned char* mock_find(const uint16_t* reg, const uint32_t* stage)
{
  if (*reg!=g_ca_ko) return 0;
  if (*stage==(*(uint32_t*)(mock_round+0x204)>>26)) return mock_round;
  if (*stage==CA_SF) return mock_semi;
  if (*stage==CA_FINAL) return mock_final;
  if (*stage==54) return mock_stage54;
  return 0;
}

static uint64_t mock_get_owner(void) { return (uint64_t)(uintptr_t)mock_owner; }

static unsigned char* mock_match(void* block, uint64_t id)
{
  assert(block==mock_qf);
  return id<14 ? mock_qf[id] : 0;
}

static void install_mock(unsigned rva, uintptr_t target)
{
  unsigned char* p=(unsigned char*)(g_base+rva);
  /* mov rax, target ; jmp rax */
  p[0]=0x48; p[1]=0xb8; memcpy(p+2,&target,8); p[10]=0xff; p[11]=0xe0;
}
static uint64_t native_dates(uint64_t reg, void* ptr)
{
  assert((uint16_t)reg==R_LIBKO || (uint16_t)reg==R_LIBGROUP);
  vec_t* v=ptr;
  v->b=(unsigned char*)date_rows;
  v->e=v->c=v->b+sizeof date_rows;
  return 1;
}

static void match(unsigned char* m, int index, uint16_t reg, unsigned stage, unsigned flag,
                  unsigned day, uint32_t h, uint32_t a)
{
  memset(m,0,MATCH_STRIDE);
  *(uint32_t*)m=(uint32_t)index;
  *(uint16_t*)(m+4)=reg;
  m[6]=(unsigned char)stage;
  m[7]=(unsigned char)flag;
  *(uint16_t*)(m+8)=2026;
  int month=1;
  while (day>=MONTH0[month]) month++;
  m[10]=(unsigned char)month;
  m[11]=(unsigned char)(day-MONTH0[month-1]+1);
  *(uint32_t*)(m+0x14)=h;
  *(uint32_t*)(m+0x18)=a;
}

static void test_august_27(void)
{
  const uint32_t teams[20]={
    73154,73188,73204,73284,73286, 73155,73192,73175,73185,73271,
    73156,73193,73199,73176,73274, 73157,73187,73200,73281,76252
  };
  /* The two fixtures per matchday, in the order read from FL27. */
  static const struct { uint32_t home,away; unsigned char gf,ga; } results[4][10]={
    {{73188,73286,0,3},{73204,73284,1,1},{73204,73154,1,3},{73284,73286,1,0},
     {73284,73188,1,0},{73286,73154,0,1},{73154,73188,1,0},{73286,73204,0,1},
     {73154,73284,0,0},{73188,73204,1,1}},
    {{73175,73185,0,1},{73192,73271,4,1},{73175,73155,2,0},{73185,73271,1,1},
     {73185,73192,4,0},{73271,73155,0,1},{73155,73192,0,4},{73271,73175,0,1},
     {73155,73185,0,3},{73192,73175,0,0}},
    {{73193,73274,3,0},{73199,73176,0,1},{73176,73274,0,1},{73199,73156,0,2},
     {73176,73193,0,0},{73274,73156,0,2},{73156,73193,1,0},{73274,73199,0,1},
     {73156,73176,0,2},{73193,73199,2,2}},
    {{73187,76252,5,2},{73200,73281,1,1},{73200,73157,0,1},{73281,76252,1,0},
     {73281,73187,0,1},{76252,73157,0,0},{73157,73187,0,0},{76252,73200,0,1},
     {73157,73281,0,0},{73187,73200,2,4}}
  };
  uint32_t clubs[20], seeds[8], pairs[8];
  for (int i=0;i<20;i++) clubs[i]=teams[i]<<14;
  ca_fixtures f={0};
  car_stats stats[20]={{0}};
  for (int g=0;g<4;g++) {
    f.counts[g+1]=10;
    for (int i=0;i<10;i++) {
      unsigned char* m=f.group[g][i];
      match(m,i,g_ca_ids[g+1],i/2,0x60,ca_group_days[i/2],
            results[g][i].home<<14,results[g][i].away<<14);
      m[0x1c]=results[g][i].gf; m[0x1f]=results[g][i].ga;
    }
  }
  assert(ca_group_table(&f,2026,clubs,stats,seeds,0));
  const uint32_t expected[]={73185,73154,73156,73187,73284,73192,73200,73176};
  for (int i=0;i<8;i++) assert(seeds[i]>>14==expected[i]);
  const uint32_t host_first[]={73185,73176,73187,73284,73154,73200,73156,73192};
  ca_qf_pairs(seeds,pairs);
  for (int i=0;i<8;i++) assert(pairs[i^1]>>14==host_first[i]);
}

static void test_august_27_replay_seeds(void)
{
  /* Exact qualifier totals read in the later live replay, by group then place.
     Goals against are goals for minus the captured goal difference. */
  const uint32_t teams[]={73204,73185,73193,73187,73154,73192,73199,73281};
  const car_stats stats[]={
    {.pts=12,.gf=4,.ga=0,.away=2,.wins=4,.away_wins=2},
    {.pts=9,.gf=8,.ga=1,.away=3,.wins=3,.away_wins=1},
    {.pts=10,.gf=4,.ga=0,.away=3,.wins=3,.away_wins=2},
    {.pts=10,.gf=8,.ga=0,.away=4,.wins=3,.away_wins=1},
    {.pts=7,.gf=6,.ga=4,.away=1,.wins=2,.away_wins=1},
    {.pts=6,.gf=4,.ga=3,.away=0,.wins=2,.away_wins=0},
    {.pts=7,.gf=8,.ga=6,.away=4,.wins=2,.away_wins=1},
    {.pts=7,.gf=4,.ga=4,.away=1,.wins=2,.away_wins=1}
  };
  uint32_t clubs[8], seeds[8], pairs[8];
  int qualifiers[2][4]={{0,1,2,3},{4,5,6,7}};
  for (int i=0;i<8;i++) clubs[i]=teams[i]<<14;
  assert(ca_rank_seeds(qualifiers,clubs,stats,seeds));
  const uint32_t expected[]={73204,73187,73193,73185,73199,73154,73281,73192};
  for (int i=0;i<8;i++) assert(seeds[i]>>14==expected[i]);
  const uint32_t host_first[]={73204,73192,73185,73199,73187,73281,73193,73154};
  ca_qf_pairs(seeds,pairs);
  for (int i=0;i<8;i++) assert(pairs[i^1]>>14==host_first[i]);
}

static void test_seed_permutations(void)
{
  int permutations[24][4], n=0;
  for (int a=0;a<4;a++) for (int b=0;b<4;b++) for (int c=0;c<4;c++) for (int d=0;d<4;d++) {
    if (((1<<a)|(1<<b)|(1<<c)|(1<<d))!=15) continue;
    int order[]={a,b,c,d};
    memcpy(permutations[n++],order,sizeof order);
  }
  assert(n==24);
  uint32_t clubs[8], seeds[8];
  car_stats stats[8]={{0}};
  for (int i=0;i<8;i++) {
    clubs[i]=(uint32_t)(1000+i)<<14;
    stats[i].pts=12-i%4;
  }
  for (int w=0;w<n;w++) for (int r=0;r<n;r++) {
    int qualifiers[2][4];
    for (int i=0;i<4;i++) {
      qualifiers[0][i]=permutations[w][i];
      qualifiers[1][i]=4+permutations[r][i];
    }
    assert(ca_rank_seeds(qualifiers,clubs,stats,seeds));
    assert(!memcmp(seeds,clubs,sizeof seeds));
  }
  int duplicate[][4]={{0,1,2,3},{4,5,6,2}};
  assert(!ca_rank_seeds(duplicate,clubs,stats,seeds));
  clubs[7]=clubs[6]|42; /* Same team ID, different native handle. */
  int duplicate_id[][4]={{0,1,2,3},{4,5,6,7}};
  assert(!ca_rank_seeds(duplicate_id,clubs,stats,seeds));
  clubs[7]=(uint32_t)1007<<14;

  const car_stats tied={.pts=10,.gf=8,.ga=4,.away=3,.wins=3,.away_wins=1};
  const car_stats better[]={
    {.pts=11},
    {.pts=10,.gf=7,.ga=2},
    {.pts=10,.gf=9,.ga=5},
    {.pts=10,.gf=8,.ga=4,.away=4},
    {.pts=10,.gf=8,.ga=4,.away=3,.wins=4},
    {.pts=10,.gf=8,.ga=4,.away=3,.wins=3,.away_wins=2},
    {.pts=10,.gf=8,.ga=4,.away=3,.wins=3,.away_wins=1}
  };
  memset(stats,0,sizeof stats);
  for (unsigned i=0;i<ARRAYSIZE(better);i++) {
    int qualifiers[2][4]={{0,2,1,3},{5,6,4,7}};
    stats[0]=stats[4]=tied;
    stats[1]=stats[5]=better[i];
    assert(ca_rank_seeds(qualifiers,clubs,stats,seeds));
    int different=i+1<ARRAYSIZE(better);
    assert(seeds[0]==clubs[different] && seeds[4]==clubs[4+different]);
  }
}

static void annual_pairs(ca_annual_part* part, const ca_part* spec,
                         unsigned first, int date, int reverse)
{
  for (unsigned i=0;i<spec->clubs;i++) for (unsigned j=i+1;j<spec->clubs;j++)
    for (unsigned leg=0;leg<spec->legs;leg++) {
      uint32_t a=(first+i)<<14, b=(first+j)<<14;
      if (leg&1) ca_annual_match(part,spec,date,1,b,a,reverse,1-reverse);
      else ca_annual_match(part,spec,date,1,a,b,1-reverse,reverse);
    }
}

static void test_domestic_qualification(void)
{
  ca_source src={1,0,0,{{1,4,2,0}}};
  ca_annual_part parts[CA_PARTS]={{0}};
  final_t ranking;
  annual_pairs(parts,src.part,1,2027*365+165,0);
  assert(ca_annual_rank(&src,parts,0,&ranking));
  assert(ranking.n==4 && ranking.club[0]==1u<<14 && ranking.club[3]==4u<<14);
  src.part[1]=(ca_part){2,4,1,0};
  assert(!ca_annual_rank(&src,parts,0,&ranking));
  annual_pairs(parts+1,src.part+1,1,2027*365+175,1);
  assert(ca_annual_rank(&src,parts,0,&ranking));
  assert(ranking.club[0]==1u<<14 && ranking.club[3]==4u<<14);
  ca_annual_match(parts+1,src.part+1,2027*365+175,1,1u<<14,2u<<14,2,0);
  assert(!ca_annual_rank(&src,parts,0,&ranking));
  memset(parts+1,0,sizeof *parts);
  ca_annual_match(parts+1,src.part+1,2027*365+175,0,1u<<14,2u<<14,0,0);
  assert(!ca_annual_rank(&src,parts,0,&ranking));

  memset(parts+1,0,3*sizeof *parts);
  src.part[1]=(ca_part){2,2,1,1}; src.part[2]=(ca_part){3,2,1,2};
  annual_pairs(parts+1,src.part+1,3,2027*365+170,1);
  assert(!ca_annual_rank(&src,parts,0,&ranking));
  annual_pairs(parts+2,src.part+2,1,2027*365+175,0);
  uint32_t native[CA_PARTS][FINAL_MAX]={{0},{4u<<14,3u<<14},{2u<<14,1u<<14}};
  assert(ca_annual_rank(&src,parts,native,&ranking));
  assert(ranking.club[0]==4u<<14 && ranking.club[2]==2u<<14);
  ca_pool eligible={0};
  const uint32_t current[]={1u<<14,2u<<14,3u<<14,5u<<14};
  assert(ca_filter_ranking(&eligible,ranking.club,ranking.n,current,4));
  assert(eligible.n==3 && eligible.league[0]==3u<<14 && eligible.league[2]==1u<<14);
  assert(!cq_has(eligible.league,eligible.n,5u<<14));

  const int draw=2027*365+CA_DRAW;
  assert(ca_annual_period(2027*365+180,0)==2026);
  assert(ca_annual_period(2027*365+181,0)==2027);
  assert(ca_annual_period(2027*365-1,1)==2026);
  assert(ca_annual_period(2027*365,1)==2027);
  assert(cq_summer_bootstrap(2027*365+190,draw,0));
  assert(!cq_summer_bootstrap(2026*365+190,draw,0));
  assert(cq_summer_bootstrap(2026*365+42,draw,1));
  assert(!cq_summer_bootstrap(2026*365+41,draw,1));
  assert(!cq_summer_bootstrap(draw+1,draw,0));

  ca_pool pools[CA_ASSOCIATIONS]={{0}};
  for (int i=0;i<CA_ASSOCIATIONS;i++) {
    pools[i].n=8;
    for (unsigned j=0;j<pools[i].n;j++) pools[i].league[j]=(10+8*i+j)<<14;
  }
  ca_entry field[CA_FIELD];
  pools[0].cup=pools[0].league[0];
  pools[1].cup=99u<<14;
  assert(ca_allocate(pools,field));
  unsigned duplicate=0;
  for (int j=0;j<CA_FIELD;j++) duplicate+=same_club(field[j].club,pools[0].cup);
  assert(duplicate==1); /* Cup champion already leads the league ranking. */
  assert(ca_entry_has(field,CA_FIELD,pools[0].league[3]));
  assert(!ca_entry_has(field,CA_FIELD,pools[0].league[4]));
  assert(ca_entry_has(field,CA_FIELD,pools[1].league[2]));
  assert(!ca_entry_has(field,CA_FIELD,pools[1].league[3]));
  assert(ca_entry_has(field,CA_FIELD,pools[1].cup));
  for (int i=0;i<CA_ASSOCIATIONS;i++) {
    unsigned n=0;
    for (int j=0;j<CA_FIELD;j++) n+=field[j].country==i;
    assert(n==ca_quota[i]);
  }
  pools[6].n=0;
  assert(ca_allocate(pools,field));
  assert(ca_entry_has(field,CA_FIELD,pools[5].league[2]));
  for (int i=2;i<CA_ASSOCIATIONS;i++) pools[i].n=0;
  assert(!ca_allocate(pools,field));

  /* Exhaust every five-pot count pattern for one association. Rotation
     of the other six associations keeps their capacities independently valid. */
  for (unsigned code=0;code<3125;code++) {
    unsigned v=code, total=0, rest=0;
    for (int pot=0;pot<5;pot++,v/=5) for (unsigned k=0;k<4;k++) {
      unsigned i=4*pot+k, country=k<v%5 ? 0 : 1+rest++%6;
      field[i]=(ca_entry){(i+1)<<14,country,0};
      total+=country==0;
    }
    uint32_t groups[CA_FIELD], reload[CA_FIELD];
    assert(ca_draw_groups(field,2027,groups)==(total<=8));
    if (total>8) continue;
    assert(ca_draw_groups(field,2027,reload) && !memcmp(groups,reload,sizeof groups));
    assert(cq_unique(groups,CA_FIELD));
    for (int g=0;g<4;g++) {
      unsigned country_count[CA_ASSOCIATIONS]={0};
      for (unsigned pot=0;pot<5;pot++) {
        unsigned slot=(groups[5*g+pot]>>14)-1;
        assert(slot/4==pot && ++country_count[field[slot].country]<=2);
      }
    }
  }
  field[1].club=field[0].club;
  uint32_t invalid[CA_FIELD];
  assert(!ca_draw_groups(field,2027,invalid));
  puts("Central American Cup annual proof, cutoffs, split/halves, membership, cup berths, redistribution and 3125 draw patterns passed");
}

int main(void)
{
  test_domestic_qualification();
  test_initialization();
  test_same_day_retry();
  uint32_t v[31]={1,700,701,702};
  uint32_t clubs[20];
  for (int i=0;i<20;i++) {
    v[4+i]=(uint32_t)(1000+i);
    clubs[i]=v[4+i]<<14;
  }
  for (int i=24;i<31;i++) v[i]=(uint32_t)(200+i);
  assert(!fl26_swiss_central_probe(v,31)); /* hooks required */
  g_cq_hooks=1;
  assert(!fl26_swiss_central_probe(v,30));
  v[5]=v[4];
  assert(!fl26_swiss_central_probe(v,31));
  v[5]=1001;
  v[3]=v[1];
  assert(!fl26_swiss_central_probe(v,31));
  v[3]=702;
  assert(fl26_swiss_central_probe(v,31)==1);
  assert(!fl26_swiss_central_probe(v,31));
  assert(g_ccup[0].groups==4 && g_ccup[0].n==20);
  test_august_27();
  test_august_27_replay_seeds();
  test_seed_permutations();
  assert(g_lpre[0].ties==2 && lpre_rows(&g_lpre[0])==2 && ca_owned(2750));
  assert(!ca_owned(3774));
  lpre_fill(0); /* the generic helper path may never qualify these clubs */
  assert(!g_lpre[0].nclub);

  g_tramp_date=(unsigned char*)(uintptr_t)native_dates;
  vec_t dates={0};
  assert(ccup_dates(0,1,701,701,&dates)==1 && dates.e-dates.b==6*sizeof(date_t));
  const unsigned stages[]={46,46,52,52,53,53}, days[]={251,258,293,300,335,339};
  for (int i=0;i<6;i++)
    assert(date_rows[i].round==stages[i] && date_rows[i].kind==(unsigned)(i%2) &&
           date_rows[i].day==days[i]);
  assert(ccup_dates(0,0,700,700,&dates)==1 && dates.e-dates.b==5*sizeof(date_t));
  for (int i=0;i<5;i++) assert(date_rows[i].day==ca_group_days[i]);

  ca_fixtures f={0};
  for (int g=0;g<4;g++) {
    f.counts[g+1]=10;
    int home[5]={0}, away[5]={0};
    for (unsigned d=0;d<5;d++) for (unsigned p=1;p<=2;p++) {
      unsigned h,a;
      car_pair(d,p,&h,&a);
      home[h]++; away[a]++;
      unsigned i=2*d+p-1;
      match(f.group[g][i],(int)i,g_ca_ids[g+1],d,0x40,ca_group_days[d],
            clubs[5*g+h],clubs[5*g+a]);
      f.group[g][i][0x1c]=1;
    }
    for (int i=0;i<5;i++) assert(home[i]==2 && away[i]==2);
  }
  uint32_t seeds[8];
  car_stats stats[20]={{0}};
  assert(ca_group_table(&f,2026,clubs,stats,seeds,0));
  for (int i=0;i<4;i++) {
    assert(seeds[i]==clubs[5*i]);
    assert(seeds[i+4]==clubs[5*i+1]);
  }
  uint32_t qf[8];
  ca_qf_pairs(seeds,qf);
  g_base=(uintptr_t)VirtualAlloc(0,FIXFIND_RVA+0x1000,MEM_COMMIT|MEM_RESERVE,PAGE_EXECUTE_READWRITE);
  assert(g_base);
  *(void**)(mock_owner+0x48)=mock_qf;
  install_mock(FIXFIND_RVA,(uintptr_t)mock_find);
  install_mock(OWNER_RVA,(uintptr_t)mock_get_owner);
  install_mock(MATCH_RVA,(uintptr_t)mock_match);
  *(uint16_t*)mock_round=g_ca_ko;
  *(uint32_t*)(mock_round+0x204)=((uint32_t)CA_QF<<26)|4;
  for (int t=0;t<4;t++) {
    uint32_t* slot=ko_slot(mock_round,t);
    uint16_t* ids=(uint16_t*)(slot+2);
    /* Simulate native initial slot order being different from the desired tree. */
    slot[0]=seeds[t]; slot[1]=seeds[t+4];
    ids[0]=(uint16_t)(2*t); ids[1]=(uint16_t)(2*t+1);
    match(mock_qf[2*t],2*t,g_ca_ko,CA_QF,0,251,slot[0],slot[1]);
    match(mock_qf[2*t+1],2*t+1,g_ca_ko,CA_QF,0x10,258,slot[1],slot[0]);
  }
  assert(ca_round_slots(CA_QF,4,2026,251,258,qf));
  assert(ca_round_slots(CA_QF,4,2026,251,258,qf));
  for (int t=0;t<4;t++) {
    uint32_t* slot=ko_slot(mock_round,t);
    assert(slot[0]==qf[2*t] && slot[1]==qf[2*t+1]);
    assert(*(uint32_t*)(mock_qf[2*t+1]+0x14)==qf[2*t+1]);
    mock_qf[2*t][7]|=0x40;
    mock_qf[2*t+1][7]|=0x40;
    mock_qf[2*t+1][0x1c]=1;
  }
  uint32_t qf_winners[4], qf_losers[4];
  mock_qf[7][7]&=~0x40;
  assert(!ca_outcomes(CA_QF,4,2026,251,258,qf,qf_winners,qf_losers,clubs,stats));
  mock_qf[7][7]|=0x40;
  assert(ca_outcomes(CA_QF,4,2026,251,258,qf,qf_winners,qf_losers,clubs,stats));
  for (int t=0;t<4;t++) {
    assert(qf_winners[t]==qf[2*t+1] && qf_losers[t]==qf[2*t]);
    assert(!cq_has(qf_winners,4,qf_losers[t]));
  }
  f.group[3][9][7]=0;
  memset(stats,0,sizeof stats);
  assert(!ca_group_table(&f,2026,clubs,stats,seeds,0));

  uint32_t play[]={clubs[0],clubs[5],clubs[10],clubs[15]}, winners[2];
  unsigned char helper[4][MATCH_STRIDE];
  for (int i=0;i<4;i++) {
    int tie=i/2, leg=i%2;
    match(helper[i],i,leg ? g_ca_ids[7+tie] : g_ca_pre,1,0x40|0x10*leg,
          leg ? 300 : 293,play[2*tie+leg],play[2*tie+1-leg]);
    f.helper[i]=helper[i];
  }
  /* First tie goes to its first-leg visitor on regulation away goals.
     The second uses penalties after tied regulation and extra time. */
  helper[0][0x1c]=2; helper[0][0x1f]=1; helper[1][0x1c]=1;
  helper[3][0x1e]=3; helper[3][0x21]=4;
  f.helper_n=3;
  assert(!ca_helper_check(&f,2026,play,1,winners));
  f.helper_n=4;
  assert(ca_helper_check(&f,2026,play,1,winners));
  assert(winners[0]==play[1] && winners[1]==play[2]);
  helper[3][0x1d]=1; /* extra time overrides penalties */
  assert(ca_helper_check(&f,2026,play,1,winners) && winners[1]==play[3]);
  memset(stats,0,sizeof stats);
  ca_score(stats,clubs,helper[3]);
  assert(stats[10].pts==1 && stats[15].pts==1 && !stats[15].gf);
  helper[3][7]&=~0x40;
  assert(!ca_helper_check(&f,2026,play,1,winners));
  helper[3][7]|=0x40;
  *(uint16_t*)(helper[3]+4)=g_ca_ids[7];
  assert(!ca_helper_check(&f,2026,play,0,0));
  *(uint16_t*)(helper[3]+4)=g_ca_ids[8];
  uint32_t unexpected[]={clubs[0],clubs[5],clubs[10],clubs[16]};
  assert(!ca_helper_check(&f,2026,unexpected,0,0));
  f.helper[3]=f.helper[2];
  assert(!ca_helper_check(&f,2026,play,0,0));
  f.counts[5]=14; f.played=58;
  assert(ca_complete(&f));
  *(uint32_t*)(mock_round+0x204)=((uint32_t)CA_FINAL<<26)|1;
  uint32_t* final=ko_slot(mock_round,0);
  const uint32_t finalists[]={clubs[2],clubs[3]}, eliminated[]={clubs[7],clubs[8]};
  final[0]=finalists[0]; final[1]=finalists[1];
  uint16_t* ids=(uint16_t*)(final+2);
  ids[0]=0; ids[1]=1;
  match(mock_qf[0],0,g_ca_ko,CA_FINAL,0x40,335,final[0],final[1]);
  match(mock_qf[1],1,g_ca_ko,CA_FINAL,0x50,339,final[1],final[0]);
  uint32_t finishers[6];
  assert(!ca_sporting_final(&f,2026,finalists,eliminated,winners,clubs,stats,finishers));
  mock_qf[1][0x1e]=5; mock_qf[1][0x21]=4;
  assert(ca_sporting_final(&f,2026,finalists,eliminated,winners,clubs,stats,finishers));
  assert(finishers[0]==finalists[1] && finishers[1]==finalists[0]);
  assert(!memcmp(finishers+2,eliminated,sizeof eliminated));
  assert(finishers[4]==play[1] && finishers[5]==play[3]);
  mock_qf[1][0x20]=1; /* visitor wins after extra time instead */
  assert(ca_sporting_final(&f,2026,finalists,eliminated,winners,clubs,stats,finishers));
  assert(finishers[0]==finalists[0] && finishers[1]==finalists[1]);
  mock_qf[1][7]&=~0x40;
  assert(!ca_sporting_final(&f,2026,finalists,eliminated,winners,clubs,stats,finishers));
  mock_qf[1][7]|=0x40;
  assert(!ca_sporting_final(&f,2026,finalists,finalists,winners,clubs,stats,finishers));
  f.year=2026;
  f.group[3][9][7]=0x40;
  memset(stats,0,sizeof stats);
  assert(ca_group_table(&f,2026,clubs,stats,seeds,0));
  ca_qf_pairs(seeds,qf);
  unsigned char* rounds[]={mock_round,mock_semi,mock_final};
  uint32_t semi_pairs[4], play_pairs[4], final_pair[2], expected[6];
  const uint32_t* pairs[]={qf,semi_pairs,final_pair};
  const int counts[]={4,2,1}, bracket_stages[]={CA_QF,CA_SF,CA_FINAL};
  const int dates1[]={251,293,335}, dates2[]={258,300,339};
  int offset=0;
  for (int r=0;r<3;r++) {
    *(uint16_t*)rounds[r]=g_ca_ko;
    *(uint32_t*)(rounds[r]+0x204)=((uint32_t)bracket_stages[r]<<26)|counts[r];
    for (int tie=0;tie<counts[r];tie++) {
      uint32_t* slot=ko_slot(rounds[r],tie);
      uint16_t* fixtures=(uint16_t*)(slot+2);
      slot[0]=pairs[r][2*tie]; slot[1]=pairs[r][2*tie+1];
      fixtures[0]=(uint16_t)offset; fixtures[1]=(uint16_t)(offset+1);
      match(mock_qf[offset],offset,g_ca_ko,bracket_stages[r],0x40,dates1[r],slot[0],slot[1]);
      match(mock_qf[offset+1],offset+1,g_ca_ko,bracket_stages[r],0x50,dates2[r],slot[1],slot[0]);
      mock_qf[offset+1][r==2 ? 0x1e : 0x1c]=1;
      ca_score(stats,clubs,mock_qf[offset]);
      ca_score(stats,clubs,mock_qf[offset+1]);
      if (!r) { semi_pairs[tie]=slot[1]; play_pairs[tie]=slot[0]; }
      if (r==1) { final_pair[tie]=slot[1]; expected[2+tie]=slot[0]; }
      if (r==2) { expected[0]=slot[1]; expected[1]=slot[0]; }
      offset+=2;
    }
    if (!r) {
      ca_hosts(semi_pairs,4,clubs,stats);
      ca_hosts(play_pairs,4,clubs,stats);
    }
    if (r==1) ca_hosts(final_pair,2,clubs,stats);
  }
  for (int i=0;i<4;i++) {
    int tie=i/2, leg=i%2;
    match(helper[i],i,leg ? g_ca_ids[7+tie] : g_ca_pre,1,0x40|0x10*leg,
          leg ? 300 : 293,play_pairs[2*tie+leg],play_pairs[2*tie+1-leg]);
    f.helper[i]=helper[i];
  }
  helper[1][0x20]=1; /* extra time for the visitor */
  helper[3][0x1e]=1; /* penalties for the home side in the other tie */
  expected[4]=play_pairs[0]; expected[5]=play_pairs[3];
  assert(ca_read_sporting(&f,clubs,2026,finishers) && !memcmp(finishers,expected,sizeof expected));
  assert(!ca_read_sporting(&f,clubs,2027,finishers));
  mock_qf[11][7]&=~0x40;
  assert(!ca_read_sporting(&f,clubs,2026,finishers));
  mock_qf[11][7]|=0x40;
  *(uint32_t*)(helper[3]+0x18)=play_pairs[0];
  assert(!ca_read_sporting(&f,clubs,2026,finishers));

  /* Native title fixtures can use 53 or 54. Stage 54 is never a title
     fixture when the competition's native bronze rule is set. */
  const int cup_day=2026*365+339, creation=2026*365;
  uint32_t* title=ko_slot(mock_final,0), *second_stage=ko_slot(mock_stage54,0);
  memset(title,0,32);
  title[0]=clubs[0]; title[1]=clubs[1]; title[2]=0xffff0000u;
  match(mock_qf[0],0,g_ca_ko,53,0x40,339,clubs[0],clubs[1]);
  mock_qf[0][0x1c]=1;
  assert(ca_cup_finish(g_ca_ko,0,clubs[0],cup_day,creation)==cup_day);
  assert(ca_cup_finish(g_ca_ko,0,clubs[1],cup_day,creation)<0); /* finalist did not win */
  assert(ca_cup_finish(g_ca_ko,0,clubs[2],cup_day,creation)<0);
  mock_qf[0][0x1c]=0; /* even a native rights claim cannot settle a tied score */
  assert(ca_cup_finish(g_ca_ko,0,clubs[0],cup_day,creation)<0);
  mock_qf[0][0x1c]=1;
  *(uint16_t*)mock_stage54=g_ca_ko;
  *(uint32_t*)(mock_stage54+0x204)=(54u<<26)|1;
  second_stage[0]=clubs[2]; second_stage[1]=clubs[3]; second_stage[2]=0xffff0001u;
  match(mock_qf[1],1,g_ca_ko,54,0x40,339,clubs[2],clubs[3]);
  mock_qf[1][0x1c]=1;
  assert(ca_cup_finish(g_ca_ko,1u<<9,clubs[0],cup_day,creation)==cup_day);
  assert(ca_cup_finish(g_ca_ko,1u<<9,clubs[2],cup_day,creation)<0);
  assert(ca_cup_finish(g_ca_ko,0,clubs[0],cup_day,creation)<0); /* two terminal ties */
  mock_qf[0][7]&=~0x40;
  assert(ca_cup_finish(g_ca_ko,1u<<9,clubs[0],cup_day,creation)<0);
  assert(ca_cup_finish(g_ca_ko,1u<<9,clubs[2],cup_day,creation)<0);
  title[4]=g_ca_ko | 54u<<16;
  assert(ca_cup_finish(g_ca_ko,0,clubs[2],cup_day,creation)==cup_day);
  *(uint32_t*)(mock_final+0x204)=53u<<26;
  assert(ca_cup_finish(g_ca_ko,0,clubs[2],cup_day,creation)==cup_day);
  assert(ca_cup_finish(g_ca_ko,1u<<9,clubs[2],cup_day,creation)<0);
  second_stage[2]=0x00020001u; /* stage 54 needs a second leg */
  match(mock_qf[1],1,g_ca_ko,54,0x40,335,clubs[2],clubs[3]);
  match(mock_qf[2],2,g_ca_ko,54,0x10,339,clubs[3],clubs[2]);
  assert(ca_cup_finish(g_ca_ko,0,clubs[2],cup_day,creation)<0);
  mock_qf[2][7]|=0x40;
  mock_qf[2][0x21]=1;
  assert(ca_cup_finish(g_ca_ko,0,clubs[2],cup_day,creation)==cup_day);
  f.counts[5]=15;
  assert(!ca_complete(&f));
  g_nccup=g_nlpre=g_ca_group=0;
  uint32_t dynamic[4+CA_ASSOCIATIONS*CA_SOURCE_WORDS]={2,700,701,702};
  for (unsigned i=0;i<CA_ASSOCIATIONS;i++) {
    uint32_t* source=dynamic+4+i*CA_SOURCE_WORDS;
    source[0]=source[3]=200+i;
    source[4]=10; source[5]=2;
  }
  dynamic[3]=200; /* must not overlap a feeder regulation */
  assert(!fl26_swiss_central_probe(dynamic,ARRAYSIZE(dynamic)));
  dynamic[3]=702;
  assert(!fl26_swiss_central_probe(dynamic,ARRAYSIZE(dynamic)-1));
  uint16_t other_cup[36]={710,710,0,16};
  uint16_t other_helper[50]={711,710,1,33,40,22};
  assert(ccup_register(other_cup,1,0)==1);
  assert(fl26_swiss_lpre(other_helper,1)==1);
  g_car_enabled=1; /* appending a Central Cup must preserve feeder registry state */
  assert(fl26_swiss_central_probe(dynamic,ARRAYSIZE(dynamic))==1);
  assert(g_ca_dynamic && g_car_enabled && g_nccup==2 && g_nlpre==2);
  assert(g_ccup[0].ko==710 && g_lpre[0].reg==711 && g_lpre[0].ties==11);
  assert(g_lpre[1].reg==702 && g_lpre[1].ties==2);
  assert(ccup_feeds(1,200) && ccup_feeds(1,206) && !ccup_feeds(1,207));
  assert(!fl26_swiss_central_probe(dynamic,ARRAYSIZE(dynamic)));
  g_nccup=g_nlpre=g_ca_group=0;
  uint32_t individual[4+CA_ASSOCIATIONS*CA_SOURCE_WORDS+CA_FIELD]={4,700,701,702};
  individual[4]=individual[7]=200; individual[6]=209; /* separate domestic cup */
  individual[8]=24; individual[9]=2;
  uint32_t* places=individual+4+CA_ASSOCIATIONS*CA_SOURCE_WORDS;
  for (unsigned i=1;i<CA_FIELD;i++) places[i]=i+1; /* cup winner, positions 2 through 20 */
  assert(!fl26_swiss_central_probe(individual,ARRAYSIZE(individual)-1));
  places[1]=41;
  assert(!fl26_swiss_central_probe(individual,ARRAYSIZE(individual)));
  places[1]=2;
  assert(fl26_swiss_central_probe(individual,ARRAYSIZE(individual))==1);
  assert(g_ca_dynamic==4 && g_ca_sources[0].cup==209 && g_ca_places[0]==0 && g_ca_places[1]==2);
  puts("Central American Cup same-day loader/native retry, duplicate prevention, initialization, 4x5 completion, QF slots, helper ownership and scoring passed");
  puts("August 27 live scores, expected QF hosts, 576 seed permutations, duplicate entrant rejection and cross-group tiebreakers passed");
  puts("National cup terminal stages, bronze rule, complete legs, native winner agreement and duplicate berth passed");
}
