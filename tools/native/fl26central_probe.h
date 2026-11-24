/* Opt-in FL27 feasibility world. Included by fl26swiss.c after its native adapters. */
#define CA_DRAW CQ_CENTRAL_DRAW
#define CA_FIRST 209
#define CA_QF 46
#define CA_SF 52
#define CA_FINAL 53

static const unsigned ca_group_days[]={209,216,223,230,237};
static uint32_t g_ca_teams[20];
#include "fl26central_qualification.h"
#include "fl26central_annual.h"

static int ca_domestic_feeds(uint16_t id)
{
  if (!g_ca_dynamic) return cq_native_has(g_ca_leagues,7,id);
  for (int i=0;i<CA_ASSOCIATIONS;i++) if (ca_phase_owner(g_ca_sources+i,id)) return 1;
  return 0;
}

__declspec(dllexport) const uint32_t fl26_swiss_central_access_abi=4;
__declspec(dllexport) int fl26_swiss_central_probe(const uint32_t* data, int n)
{
  if (!g_cq_hooks || !data || n<4 || g_ca_group ||
      g_nccup>=MAX_CCUP || g_nlpre>=MAX_LPRE || g_cq_enabled)
    return 0;
  int dynamic=data[0]>=2 && data[0]<=4;
  if (!dynamic && (g_nccup || g_nlpre)) return 0;
  if (dynamic ? n!=4+CA_ASSOCIATIONS*(CA_SOURCE_WORDS+(data[0]==3))+(data[0]==4 ? CA_FIELD : 0) : (data[0]!=1 || n!=31)) return 0;
  uint16_t ids[9];
  for (int i=1;i<=3;i++)
    if (data[i]<176 || data[i]>1023) return 0;
  for (int i=0;i<5;i++) ids[i]=(uint16_t)(data[1]+1024*i);
  ids[5]=(uint16_t)data[2];
  for (int i=0;i<3;i++) ids[6+i]=(uint16_t)(data[3]+1024*i);
  for (int i=0;i<9;i++)
    for (int j=0;j<i;j++) if (ids[i]==ids[j]) return 0;
  for (int i=0;i<g_nccup;i++) {
    const ccup_t* c=&g_ccup[i];
    if (cq_native_has(ids,9,c->ko)) return 0;
    for (unsigned j=0;j<=c->groups;j++)
      if (cq_native_has(ids,9,(uint16_t)(c->reg+1024*j))) return 0;
  }
  for (int i=0;i<g_nlpre;i++) {
    const lpre_t* l=&g_lpre[i];
    if (cq_native_has(ids,9,l->reg)) return 0;
    for (int j=0;j<lpre_rows(l);j++) if (cq_native_has(ids,9,lpre_tie(l,j))) return 0;
  }
  if (dynamic) {
    if (!ca_sources_parse(g_ca_sources,data+4)) return 0;
    unsigned available=0;
    for (int i=0;i<CA_ASSOCIATIONS;i++) {
      for (int j=0;j<9;j++) if (ca_phase_owner(g_ca_sources+i,ids[j])) return 0;
      available+=g_ca_sources[i].membership!=0;
    }
    if (data[0]==3) {
      unsigned quota=0;
      for (int i=0;i<CA_ASSOCIATIONS;i++) {
        unsigned places=data[4+CA_ASSOCIATIONS*CA_SOURCE_WORDS+i];
        if (places>CA_FIELD || (!!places!=!!g_ca_sources[i].membership)) return 0;
        g_ca_access[i]=(uint16_t)places;
        quota+=places;
      }
      if (quota!=CA_FIELD) return 0;
    } else if (data[0]==4) {
      uint16_t cups[CA_ASSOCIATIONS]={0};
      for (unsigned i=0;i<available;i++) {
        if (!g_ca_sources[i].membership) return 0;
        cups[i]=g_ca_sources[i].cup;
      }
      for (unsigned i=0;i<CA_FIELD;i++) {
        unsigned value=data[4+CA_ASSOCIATIONS*CA_SOURCE_WORDS+i];
        if (value>0xffff) return 0;
        g_ca_places[i]=(uint16_t)value;
      }
      if (!regional_places_valid(g_ca_places,CA_FIELD,available,cups)) return 0;
    } else if (available<3) return 0; /* 20 clubs with at most eight per association. */
  } else {
    for (int i=4;i<24;i++) {
      if (!data[i] || data[i]>=0x3ffff) return 0;
      for (int j=4;j<i;j++) if (data[i]==data[j]) return 0;
    }
    for (int i=24;i<n;i++) {
      if (!data[i] || data[i]>1023 || cq_native_has(ids,9,(uint16_t)data[i])) return 0;
      for (int j=24;j<i;j++) if (data[i]==data[j]) return 0;
    }
    memcpy(g_ca_teams,data+4,sizeof g_ca_teams);
    for (int i=0;i<7;i++) g_ca_leagues[i]=(uint16_t)data[24+i];
  }
  memcpy(g_ca_ids,ids,sizeof ids);
  g_ca_dynamic=data[0]>=3 ? (int)data[0] : dynamic;
  g_ca_group=ids[0]; g_ca_ko=ids[5]; g_ca_pre=ids[6];
  /* The registry needs entries for its shape check. The fixed field below supplies all clubs. */
  uint16_t cup[44]={g_ca_group,g_ca_ko,4,20};
  uint16_t helper[14]={g_ca_pre,g_ca_ko,259,293,300,4};
  int cups=g_nccup, helpers=g_nlpre;
  if (ccup_register_rows(cup,1,0,1)!=cups+1 || lpre_register(helper,1,1)!=helpers+1) return 0;
  logf("Central American Cup prototype: registered nine owned regulation IDs");
  return 1;
}

typedef struct {
  unsigned char group[4][10][MATCH_STRIDE];
  unsigned char* helper[4];
  int counts[9], helper_n, year, played;
} ca_fixtures;

/* One bounded view of native records. Match records are visited once per transition attempt. */
static int ca_collect(ca_fixtures* f)
{
  uint32_t cap;
  const unsigned char* matches=car_matches(&cap);
  if (!matches) return 0;
  memset(f,0,sizeof *f);
  f->year=-1;
  for (uint32_t i=0;i<cap;i++) {
    const unsigned char* m=matches+(size_t)i*MATCH_STRIDE;
    if (*(const uint16_t*)m==0xffff) continue;
    uint16_t reg=*(const uint16_t*)(m+4);
    int row=0;
    while (row<9 && g_ca_ids[row]!=reg) row++;
    if (row==9) continue;
    int pos=f->counts[row]++;
    if (row==0 || (row<5 && pos>=10) || (row==5 && pos>=14) ||
        (row>=6 && f->helper_n>=4)) return 0;
    int date=ko_mdate(m);
    if (date<0) return 0;
    int year=date/365;
    if (f->year!=-1 && f->year!=year) return 0;
    f->year=year;
    f->played+=(m[7]&0x40)!=0;
    if (row<5) memcpy(f->group[row-1][pos],m,MATCH_STRIDE);
    if (row>=6) f->helper[f->helper_n++]=(unsigned char*)m;
  }
  return 1;
}

static int ca_field(uint32_t* clubs)
{
  if (g_ca_dynamic) {
    for (int g=0;g<4;g++) {
      unsigned char* rec=get_rec(g_ca_ids[g+1]);
      if (!rec || rec_count(rec)!=5) return 0;
      memcpy(clubs+5*g,rec_clubs(rec),5*sizeof *clubs);
    }
    return cq_unique(clubs,20);
  }
  uint32_t n;
  unsigned char* teams=team_array(&n);
  if (!teams) return 0;
  memset(clubs,0,20*sizeof *clubs);
  for (uint32_t i=0;i<n;i++) {
    uint32_t h=team_at(teams,i);
    if ((h&0x3fff)!=i) continue;
    for (int j=0;j<20;j++) if (g_ca_teams[j]==h>>14) {
      if (clubs[j]) return 0;
      clubs[j]=h;
    }
  }
  return cq_unique(clubs,20);
}

static void ca_set(uint16_t reg, uint32_t* clubs, int n)
{
  u32vec field={clubs,clubs+n,clubs+n};
  ((setclr_fn)(uintptr_t)g_tramp_setcl)(reg,&field,1);
}

static int ca_rank_seeds(int qualifiers[2][4], const uint32_t* clubs,
                         const car_stats* stats, uint32_t seed[8])
{
  for (int p=0;p<2;p++) for (int i=1;i<4;i++) {
    for (int j=i;j>0;j--) {
      int a=qualifiers[p][j-1], b=qualifiers[p][j];
      int cmp=car_host_compare(stats+b,stats+a);
      if (cmp<0 || (!cmp && clubs[b]>clubs[a])) break;
      qualifiers[p][j-1]=b; qualifiers[p][j]=a;
    }
  }
  /* Insertion can move an earlier qualifier. Copy only the finished ranking. */
  for (int p=0;p<2;p++) for (int i=0;i<4;i++)
    seed[4*p+i]=clubs[qualifiers[p][i]];
  return cq_unique(seed,8);
}

static int ca_group_table(const ca_fixtures* f, int year, const uint32_t* clubs,
                          car_stats stats[20], uint32_t seed[8], int display)
{
  int qualifiers[2][4];
  for (int g=0;g<4;g++) {
    int order[5];
    if (f->counts[g+1]!=10 ||
        !regional_group_results(f->group[g][0],10,g_ca_ids[g+1],year,ca_group_days,
                                clubs+5*g,stats+5*g,order)) return 0;
    for (int p=0;p<2;p++) qualifiers[p][g]=5*g+order[p];
    if (display) car_display_order(g_ca_ids[g+1],clubs+5*g,order);
  }
  return ca_rank_seeds(qualifiers,clubs,stats,seed);
}

static void ca_qf_pairs(const uint32_t seed[8], uint32_t pairs[8])
{
  /* Native slots are first-leg home, away. The winner of each group hosts leg two. */
  static const unsigned order[]={7,0,4,3,6,1,5,2};
  for (int i=0;i<8;i++) pairs[i]=seed[order[i]];
}

/* Match orientation is relative to the host of leg one. On a completed tie,
 * reject mismatched slots, ownership, dates, sides or unresolved results. */
static int ca_legs(unsigned char* first, unsigned char* second, int year, int d1, int d2)
{
  return first && second && first!=second && ko_mdate(first)==year*365+d1 &&
         ko_mdate(second)==year*365+d2;
}

static unsigned char* ca_round(int stage, int count)
{
  unsigned char* round=ko_round(g_ca_ko,stage);
  return ko_slots(round)==count && *(const uint16_t*)round==g_ca_ko ? round : 0;
}

static int ca_round_legs(unsigned char* round, int i, int year, int d1, int d2,
                         unsigned char* legs[2])
{
  const uint16_t* ids=(const uint16_t*)(ko_slot(round,i)+2);
  legs[0]=ko_match(ids[0],g_ca_ko); legs[1]=ko_match(ids[1],g_ca_ko);
  unsigned stage=*(const uint32_t*)(round+0x204)>>26;
  return ca_legs(legs[0],legs[1],year,d1,d2) && legs[0][6]==stage && legs[1][6]==stage &&
         !(legs[0][7]&0x30) && (legs[1][7]&0x30)==0x10;
}

static int ca_round_slots(int stage, int n, int year, int d1, int d2, const uint32_t* pairs)
{
  unsigned char* round=ca_round(stage,n);
  unsigned char* legs[4][2];
  if (!round) return 0;
  /* Validate every slot before editing any. A live slot may already reflect this exact order. */
  for (int i=0;i<n;i++) {
    if (!ca_round_legs(round,i,year,d1,d2,legs[i])) return 0;
    uint32_t h=pairs[2*i], a=pairs[2*i+1];
    uint32_t* slot=ko_slot(round,i);
    if (!cq_has(pairs,2*n,slot[0]) || !cq_has(pairs,2*n,slot[1]) ||
        same_club(slot[0],slot[1])) return 0;
    if ((legs[i][0][7]|legs[i][1][7])&0x40) {
      if (!same_club(slot[0],h) || !same_club(slot[1],a) ||
          !same_club(*(uint32_t*)(legs[i][0]+0x14),h) ||
          !same_club(*(uint32_t*)(legs[i][0]+0x18),a) ||
          !same_club(*(uint32_t*)(legs[i][1]+0x14),a) ||
          !same_club(*(uint32_t*)(legs[i][1]+0x18),h)) return 0;
    }
  }
  int changed=0;
  for (int i=0;i<n;i++) {
    if ((legs[i][0][7]|legs[i][1][7])&0x40) continue;
    uint32_t h=pairs[2*i], a=pairs[2*i+1];
    uint32_t* slot=ko_slot(round,i);
    changed|=slot[0]!=h || slot[1]!=a ||
             *(uint32_t*)(legs[i][0]+0x14)!=h || *(uint32_t*)(legs[i][0]+0x18)!=a ||
             *(uint32_t*)(legs[i][1]+0x14)!=a || *(uint32_t*)(legs[i][1]+0x18)!=h;
    slot[0]=h; slot[1]=a;
    *(uint32_t*)(legs[i][0]+0x14)=h; *(uint32_t*)(legs[i][0]+0x18)=a;
    *(uint32_t*)(legs[i][1]+0x14)=a; *(uint32_t*)(legs[i][1]+0x18)=h;
  }
  if (changed) sched_rebuild("Central American Cup bracket and hosts");
  return 1;
}

static void ca_score(car_stats* stats, const uint32_t* clubs, const unsigned char* m)
{
  int h=car_index(clubs,20,*(const uint32_t*)(m+0x14));
  int a=car_index(clubs,20,*(const uint32_t*)(m+0x18));
  if (h<0 || a<0) return;
  car_stat(stats+h,m[0x1c],m[0x1f],0);
  car_stat(stats+a,m[0x1f],m[0x1c],1);
}

static int ca_outcomes(int stage, int n, int year, int d1, int d2, const uint32_t* pairs,
                       uint32_t* winners, uint32_t* losers, const uint32_t* clubs, car_stats* stats)
{
  unsigned char* round=ca_round(stage,n);
  if (!round) return 0;
  for (int i=0;i<n;i++) {
    unsigned char* legs[2];
    uint32_t h=pairs[2*i], a=pairs[2*i+1];
    if (!ca_round_legs(round,i,year,d1,d2,legs) ||
        !same_club(ko_slot(round,i)[0],h) || !same_club(ko_slot(round,i)[1],a)) return 0;
    for (int leg=0;leg<2;leg++)
      if (!(legs[leg][7]&0x40) ||
          !same_club(*(uint32_t*)(legs[leg]+0x14),leg ? a : h) ||
          !same_club(*(uint32_t*)(legs[leg]+0x18),leg ? h : a)) return 0;
    int result=cq_score_winner(legs[0]+0x1c,legs[1]+0x1c);
    if (!result) return 0;
    winners[i]=result>0 ? h : a;
    losers[i]=result>0 ? a : h;
    for (int leg=0;leg<2;leg++) ca_score(stats,clubs,legs[leg]);
  }
  return 1;
}

static void ca_hosts(uint32_t* pairs, int n, const uint32_t* clubs, const car_stats* stats)
{
  for (int i=0;i<n;i+=2) {
    uint32_t h=pairs[i], a=pairs[i+1];
    int cmp=car_host_compare(stats+car_index(clubs,20,h),stats+car_index(clubs,20,a));
    if (cmp>0 || (!cmp && h<a)) { pairs[i]=a; pairs[i+1]=h; }
  }
}

/* Accept ownership by the master or the correct replica. Pair and date jointly identify
 * each record. A duplicate, partial set, unexpected club or unrelated replica fails closed. */
static int ca_helper_legs(const ca_fixtures* f, int year, const uint32_t pairs[4],
                          unsigned char* legs[2][2])
{
  if (f->helper_n!=4 || !cq_unique(pairs,4)) return 0;
  for (int j=0;j<4;j++) {
    unsigned char* m=f->helper[j];
    uint16_t reg=*(uint16_t*)(m+4);
    int day=ko_mdate(m)-year*365;
    if (day!=293 && day!=300) return 0;
    int leg=day==300, tie=-1;
    if ((m[7]&0x30)!=(leg ? 0x10 : 0)) return 0;
    uint32_t h=*(uint32_t*)(m+0x14), a=*(uint32_t*)(m+0x18);
    for (int t=0;t<2;t++)
      if (!same_club(h,a) && cq_has(pairs+2*t,2,h) && cq_has(pairs+2*t,2,a)) tie=t;
    if (tie<0 || legs[tie][leg] || (reg!=g_ca_pre && reg!=g_ca_ids[7+tie])) return 0;
    legs[tie][leg]=m;
  }
  return 1;
}

static int ca_helper_check(const ca_fixtures* f, int year, const uint32_t pairs[4],
                           int results, uint32_t winners[2])
{
  unsigned char* legs[2][2]={{0}};
  if (!ca_helper_legs(f,year,pairs,legs)) return 0;
  for (int i=0;i<2;i++) for (int leg=0;leg<2;leg++) {
    const unsigned char* m=legs[i][leg];
    if ((results && !(m[7]&0x40)) ||
        !same_club(*(const uint32_t*)(m+0x14),pairs[2*i+leg]) ||
        !same_club(*(const uint32_t*)(m+0x18),pairs[2*i+1-leg])) return 0;
  }
  if (!results) return 1;
  for (int i=0;i<2;i++) {
    int result=cq_score_winner(legs[i][0]+0x1c,legs[i][1]+0x1c);
    if (!result) return 0;
    winners[i]=pairs[2*i+(result<0)];
  }
  return !same_club(winners[0],winners[1]);
}

static int ca_helper_hosts(const ca_fixtures* f, int year, const uint32_t pairs[4])
{
  unsigned char* legs[2][2]={{0}};
  if (!ca_helper_legs(f,year,pairs,legs)) return 0;
  for (int i=0;i<2;i++) for (int leg=0;leg<2;leg++) {
    const unsigned char* m=legs[i][leg];
    if ((m[7]&0x40) && (!same_club(*(const uint32_t*)(m+0x14),pairs[2*i+leg]) ||
                        !same_club(*(const uint32_t*)(m+0x18),pairs[2*i+1-leg]))) return 0;
  }
  int changed=0;
  for (int i=0;i<2;i++) for (int leg=0;leg<2;leg++) {
    unsigned char* m=legs[i][leg];
    uint32_t h=pairs[2*i+leg], a=pairs[2*i+1-leg];
    if (same_club(*(const uint32_t*)(m+0x14),h) && same_club(*(const uint32_t*)(m+0x18),a)) continue;
    *(uint32_t*)(m+0x14)=h; *(uint32_t*)(m+0x18)=a;
    changed=1;
  }
  if (changed) sched_rebuild("Central American Cup play-in hosts");
  return 1;
}

static int ca_closed(const uint16_t* ids, int n)
{
  for (int i=0;i<n;i++) {
    const unsigned char* rec=get_rec(ids[i]);
    if (!rec || *(const uint16_t*)(rec+0x2fc)!=0xffff) return 0;
  }
  return 1;
}

typedef struct {
  unsigned marker, entrants, rows, fixtures;
  int live;
} ca_registration;

static int ca_can_initialize(const ca_registration* states, int n, int year)
{
  for (int i=0;i<n;i++) {
    const ca_registration* s=states+i;
    if (!s->live || (s->marker!=0xffff && s->marker!=(unsigned)year) ||
        s->entrants || s->rows || s->fixtures) return 0;
  }
  return 1;
}

static int ca_claim_initialization(int* attempted, int bit, const ca_registration* states,
                                   int n, int year)
{
  if ((*attempted&bit) || !ca_can_initialize(states,n,year)) return 0;
  *attempted|=bit;
  return 1;
}

/* Read the round table only at registration or when reporting the result. A
 * placeholder row with no slots still blocks a second registration. */
static int ca_registration_state(int first, int n, const ca_fixtures* f,
                                 ca_registration states[3], unsigned stages[64])
{
  unsigned char* owner=((owner_fn)(uintptr_t)(g_base+OWNER_RVA))();
  const unsigned char* block=owner ? *(unsigned char**)(owner+0x48) : 0;
  uint32_t offset=RT_OFF, count=RT_N;
  if (!block || !offset || !count || count>200000) return 0;
  memset(stages,0,64*sizeof *stages);
  for (int i=0;i<n;i++) {
    unsigned char* rec=get_rec(g_ca_ids[first+i]);
    states[i]=(ca_registration){rec ? *(uint16_t*)(rec+0x2fc) : 0xffffu,
                                rec ? rec_count(rec) : 0, 0, f->counts[first+i], rec!=0};
  }
  for (uint32_t row=0;row<count;row++) {
    const unsigned char* r=block+offset+(size_t)row*RT_REC;
    uint16_t reg=*(const uint16_t*)r;
    for (int i=0;i<n;i++) if (reg==g_ca_ids[first+i]) {
      states[i].rows++;
      stages[*(const uint32_t*)(r+0x204)>>26]++;
    }
  }
  return 1;
}

static void ca_log_registration(const char* phase, int first, int n, const ca_fixtures* f,
                                const ca_registration* states, const unsigned stages[64])
{
  for (int i=0;i<n;i++) {
    logf("Central American Cup prototype: %s reg %u season %u entrants %u round rows %u fixtures %d",
         phase,g_ca_ids[first+i],states[i].marker,states[i].entrants,states[i].rows,f->counts[first+i]);
    unsigned char* rec=states[i].entrants && states[i].entrants<=8 ? get_rec(g_ca_ids[first+i]) : 0;
    if (!rec || rec_count(rec)!=states[i].entrants) continue;
    char ids[80]={0};
    size_t used=0;
    for (unsigned j=0;j<states[i].entrants;j++)
      used+=(size_t)snprintf(ids+used,sizeof ids-used," %u",rec_clubs(rec)[j]>>14);
    logf("Central American Cup prototype: reg %u native entrant IDs:%s",g_ca_ids[first+i],ids);
  }
  for (unsigned i=0;i<64;i++) if (stages[i])
    logf("Central American Cup prototype: %s stage ID %u: %u native round rows",phase,i,stages[i]);
}

static int ca_complete(const ca_fixtures* f)
{
  if (f->played!=58 || f->counts[5]!=14 || f->helper_n!=4) return 0;
  for (int i=1;i<5;i++) if (f->counts[i]!=10) return 0;
  return 1;
}

/* Ordered finishers from completed native ties. The caller has verified the
 * QF-to-SF and QF-to-play-in paths; the final must use the two SF winners. */
static int ca_sporting_final(const ca_fixtures* f, int year, const uint32_t finalists[2],
                            const uint32_t eliminated[2], const uint32_t play_winners[2],
                            const uint32_t* clubs, car_stats* stats, uint32_t result[6])
{
  if (!ca_complete(f) || ko_slots(ko_round(g_ca_ko,54)) ||
      !ca_outcomes(CA_FINAL,1,year,335,CQ_CENTRAL_FINAL_DAY,finalists,result,result+1,clubs,stats))
    return 0;
  memcpy(result+2,eliminated,2*sizeof *result);
  memcpy(result+4,play_winners,2*sizeof *result);
  return cq_unique(result,CQ_CENTRAL_PLACES);
}

static int ca_keep_sporting(int year, const uint32_t result[6])
{
  int gd=game_date(), ad=abs_day(), completed=year*365+CQ_CENTRAL_FINAL_DAY;
  int creation=concacaf_career_start(gd);
  if (!g_ca_dynamic || ad<0 || creation<0 || creation>year*365+CA_DRAW ||
      !cq_central_result(year,completed,gd,result,CQ_CENTRAL_PLACES)) return 0;
  uint32_t clubs[CQ_CENTRAL_PLACES];
  for (int i=0;i<CQ_CENTRAL_PLACES;i++) {
    clubs[i]=canon_club(result[i]);
    if (!real_club(clubs[i])) return 0;
  }
  state_sync();
  uint16_t key=CQ_CENTRAL_KEEP(g_ca_ko);
  final_t* keep=final_of(key);
  int day=ad-(gd-completed);
  if (keep && keep->day==day && keep->n==CQ_CENTRAL_PLACES &&
      !memcmp(keep->club,clubs,sizeof clubs)) return 1;
  if (!keep) keep=final_new(key);
  if (!keep) return 0;
  keep->reg=key; keep->day=day; keep->n=CQ_CENTRAL_PLACES;
  memcpy(keep->club,clubs,sizeof clubs);
  state_store();
  logf("Central American Cup: sporting result edition=%d reg=%u champion=%u runner_up=%u semifinalists=%u/%u play_in=%u/%u",
       year,g_ca_ko,clubs[0]>>14,clubs[1]>>14,clubs[2]>>14,clubs[3]>>14,clubs[4]>>14,clubs[5]>>14);
  return 1;
}

static int ca_read_sporting(const ca_fixtures* f, const uint32_t clubs[20], int year,
                            uint32_t result[CQ_CENTRAL_PLACES])
{
  uint32_t seed[8], qf[8], sf[4], play[4], finalists[2], eliminated[2], winners[2];
  car_stats stats[20]={{0}};
  if (f->year!=year || !ca_complete(f) || !ca_group_table(f,year,clubs,stats,seed,0)) return 0;
  ca_qf_pairs(seed,qf);
  if (!ca_outcomes(CA_QF,4,year,251,258,qf,sf,play,clubs,stats)) return 0;
  ca_hosts(sf,4,clubs,stats);
  ca_hosts(play,4,clubs,stats);
  if (!ca_helper_check(f,year,play,1,winners) ||
      !ca_outcomes(CA_SF,2,year,293,300,sf,finalists,eliminated,clubs,stats)) return 0;
  ca_hosts(finalists,2,clubs,stats);
  return ca_sporting_final(f,year,finalists,eliminated,winners,clubs,stats,result);
}

/* Journal keys cannot distinguish two careers with the same club and start
 * date. Check the loaded save's complete bracket even if the row is present. */
static int ca_feeder(cq_source* source, int edition, int gd, int creation, int publish)
{
  source->n=0;
  if (!g_ca_dynamic || source->reg!=g_ca_ko) return 0;
  if (cq_central_bootstrap(creation,edition)) return 1;
  int year=cq_central_year(edition);
  if (!g_base || year<1990 || creation<0 || creation>year*365+CA_DRAW ||
      gd<year*365+CQ_CENTRAL_FINAL_DAY) return 0;
  ca_fixtures f;
  uint32_t clubs[20], result[CQ_CENTRAL_PLACES];
  if (!ca_collect(&f) || !ca_field(clubs) || !ca_read_sporting(&f,clubs,year,result)) return 0;
  const uint32_t* finishers=result;
  if (publish) {
    if (!ca_keep_sporting(year,result)) return 0;
    final_t* keep=final_of(CQ_CENTRAL_KEEP(source->reg));
    if (!keep) return 0;
    finishers=keep->club;
  }
  memcpy(source->club,finishers,CQ_CENTRAL_PLACES*sizeof *source->club);
  source->n=CQ_CENTRAL_PLACES;
  return 1;
}

static int ca_groups_scheduled(const ca_fixtures* f, int year)
{
  if (f->year!=year) return 0;
  for (int i=1;i<5;i++) if (f->counts[i]!=10) return 0;
  return 1;
}

static void ca_drive(void* ctx, int year, int day, int* completed)
{
  static int attempted_year=-1, attempted_timeline=-1, attempted=0;
  enum { CA_GROUP_STARTED=1, CA_MAIN_STARTED=2, CA_HELPER_STARTED=4 };
  if (attempted_year!=year || attempted_timeline!=g_timeline) {
    attempted_year=year; attempted_timeline=g_timeline; attempted=0;
  }
  ca_fixtures f;
  uint32_t clubs[20], incoming[20];
  if (!ca_collect(&f)) return;
  if (f.year>=0 && !ca_field(clubs)) return;
  if (g_ca_dynamic && day<CA_FIRST && f.year!=year &&
      !ca_domestic_draw(year*365+day,year,incoming)) return;
  if (day<CA_FIRST && f.year>=0 && f.year<year) {
    typedef int (*close_fn)(void*,const uint16_t*);
    HMODULE join=GetModuleHandleA("fl26join.dll");
    close_fn close=join ? (close_fn)(uintptr_t)GetProcAddress(join,"fl26_join_close_central_probe") : 0;
    if (!ctx || !close || !ca_complete(&f)) return;
    int prior=0;
    ca_drive(0,f.year,340,&prior);
    attempted_year=year; attempted_timeline=g_timeline; attempted=0;
    if (!(prior&16) || !close(ctx,g_ca_ids) ||
        !ca_closed(g_ca_ids,9) || !ca_collect(&f) || f.year!=-1) return;
    logf("Central American Cup prototype: all nine prior-edition rows reset");
  }
  if (day<CA_FIRST && ca_groups_scheduled(&f,year)) {
    *completed|=1;
    return;
  }
  if (f.year<0 && day<CA_FIRST && ca_closed(g_ca_ids,9) && !(attempted&CA_GROUP_STARTED)) {
    if (g_ca_dynamic) memcpy(clubs,incoming,sizeof clubs);
    else if (!ca_field(clubs)) return;
    attempted|=CA_GROUP_STARTED;
    ca_set(g_ca_group,clubs,20);
    for (int i=0;i<4;i++) ca_set(g_ca_ids[1+i],clubs+5*i,5);
    run_flush();
    car_register(g_ca_ids+1,4);
    ccup_season_fix(g_ca_group,g_ca_ids+1,4);
    if (ca_collect(&f) && f.year==year) {
      int count=f.counts[1]+f.counts[2]+f.counts[3]+f.counts[4];
      logf("Central American Cup prototype: %d group fixtures registered",count);
      if (ca_groups_scheduled(&f,year)) *completed|=1;
    }
    return;
  }
  if (day<237 || f.year!=year) return;
  if (day>=CQ_CENTRAL_FINAL_DAY) {
    uint32_t result[CQ_CENTRAL_PLACES];
    if (!ca_read_sporting(&f,clubs,year,result) ||
        (g_ca_dynamic && !ca_keep_sporting(year,result))) return;
    *completed|=31;
    logf("Central American Cup prototype: 58 completed fixtures, champion %u, runner-up %u",
         result[0]>>14,result[1]>>14);
    return;
  }
  car_stats stats[20]={{0}};
  uint32_t seed[8];
  if (!ca_group_table(&f,year,clubs,stats,seed,!f.counts[5])) return;
  uint32_t qf[8];
  ca_qf_pairs(seed,qf);
  if (!f.counts[5] && day<251 && !(attempted&CA_MAIN_STARTED)) {
    ca_registration state[3]; unsigned stages[64];
    if (!ca_registration_state(5,1,&f,state,stages)) return;
    if (!ca_claim_initialization(&attempted,CA_MAIN_STARTED,state,1,year)) {
      ca_log_registration("knockout initialization blocked",5,1,&f,state,stages);
      return;
    }
    ca_log_registration("knockout initialization",5,1,&f,state,stages);
    ca_set(g_ca_ko,qf,8);
    run_flush();
    unsigned char* rec=get_rec(g_ca_ko);
    unsigned entrants=rec ? rec_count(rec) : 0;
    if (entrants!=8 || !cq_unique(rec_clubs(rec),8)) {
      logf("Central American Cup prototype: knockout setter returned %u entrants; expected eight unique entrants",entrants);
      return;
    }
    for (int i=0;i<8;i++) if (!cq_has(qf,8,rec_clubs(rec)[i])) {
      logf("Central American Cup prototype: knockout setter returned an unexpected entrant");
      return;
    }
    start_stage(0,g_ca_ko);
    car_register(&g_ca_ko,1);
    if (!ca_collect(&f) || !ca_registration_state(5,1,&f,state,stages)) {
      logf("Central American Cup prototype: knockout native start produced unreadable or inconsistent fixture state");
      return;
    }
    ca_log_registration("knockout after native start",5,1,&f,state,stages);
    logf("Central American Cup prototype: requested QF entrants %u/%u %u/%u %u/%u %u/%u",
         qf[0]>>14,qf[1]>>14,qf[2]>>14,qf[3]>>14,qf[4]>>14,qf[5]>>14,qf[6]>>14,qf[7]>>14);
  }
  if (!ca_round_slots(CA_QF,4,year,251,258,qf)) return;
  *completed|=2;
  if (day<258) return;
  uint32_t sf[4], play[4];
  if (!ca_outcomes(CA_QF,4,year,251,258,qf,sf,play,clubs,stats) ||
      !cq_unique(sf,4) || !cq_unique(play,4)) return;
  for (int i=0;i<4;i++) if (cq_has(sf,4,play[i])) return;
  ca_hosts(sf,4,clubs,stats);
  ca_hosts(play,4,clubs,stats);
  if (!f.helper_n && day<293 && !(attempted&CA_HELPER_STARTED)) {
    ca_registration state[3]; unsigned stages[64];
    if (!ca_registration_state(6,3,&f,state,stages)) return;
    if (!ca_claim_initialization(&attempted,CA_HELPER_STARTED,state,3,year)) {
      ca_log_registration("play-in initialization blocked",6,3,&f,state,stages);
      return;
    }
    int tie=-1, helper=lpre_of(g_ca_pre,&tie);
    if (helper<0 || tie>=0) return;
    lpre_t* l=&g_lpre[helper];
    for (int i=7;i<9;i++) ((freetab_fn)(uintptr_t)(g_base+FREETAB_RVA))(0,g_ca_ids[i]);
    ca_set(g_ca_pre,play,4);
    for (int i=0;i<2;i++) ca_set(g_ca_ids[7+i],play+2*i,2);
    memcpy(l->club,play,sizeof play);
    l->nclub=4;
    run_flush();
    start_stage(0,g_ca_pre);
    car_register(&g_ca_pre,1);
    if (!ca_collect(&f) || !ca_registration_state(6,3,&f,state,stages)) return;
    if (!f.helper_n) {
      if (state[0].rows || state[1].rows || state[2].rows) {
        ca_log_registration("play-in replica fallback blocked",6,3,&f,state,stages);
        return;
      }
      car_register(g_ca_ids+7,2);
      if (!ca_collect(&f) || !ca_registration_state(6,3,&f,state,stages)) return;
    }
    ca_log_registration("play-in after native start",6,3,&f,state,stages);
    logf("Central American Cup prototype: play-in registered with %d records, pairs %u/%u and %u/%u",
         f.helper_n,play[0]>>14,play[1]>>14,play[2]>>14,play[3]>>14);
  }
  if (!ca_helper_hosts(&f,year,play) || !ca_helper_check(&f,year,play,0,0) ||
      !ca_round_slots(CA_SF,2,year,293,300,sf)) return;
  *completed|=4;
  if (day<300) return;
  uint32_t finalists[2], eliminated[2], play_winners[2];
  if (!ca_helper_check(&f,year,play,1,play_winners) ||
      !ca_outcomes(CA_SF,2,year,293,300,sf,finalists,eliminated,clubs,stats)) return;
  ca_hosts(finalists,2,clubs,stats);
  if (!ca_round_slots(CA_FINAL,1,year,335,CQ_CENTRAL_FINAL_DAY,finalists)) return;
  if (!(*completed&8)) {
    for (int i=0;i<2;i++) {
      uint32_t native=0;
      ((winner_fn)(uintptr_t)(g_base+WINNER_RVA))(&native,g_ca_ids[7+i]);
      if (!same_club(native,play_winners[i]))
        logf("Central American Cup prototype: play-in %d native winner %u differs from score winner %u",
             i+1,native>>14,play_winners[i]>>14);
    }
    logf("Central American Cup prototype: play-in winners %u / %u",play_winners[0]>>14,play_winners[1]>>14);
  }
  *completed|=8;
}

typedef struct {
  int date, native_checked;
  ULONGLONG due;
  unsigned delay;
} ca_retry;

/* A loader callback can run before the restored fixtures and teams are ready.
 * Back off pending scans, but give the first native day callback its own chance
 * immediately. Successful stages leave the pending mask and stop scanning. */
static int ca_retry_due(ca_retry* retry, int date, int native, ULONGLONG now)
{
  if (retry->date!=date) *retry=(ca_retry){.date=date,.delay=250};
  int first_native=native && !retry->native_checked;
  if (!first_native && now<retry->due) return 0;
  if (native) retry->native_checked=1;
  retry->due=now+retry->delay;
  if (retry->delay<8000) retry->delay*=2;
  return 1;
}

static int ca_pending(int day, int completed, int native)
{
  return (day>=CA_DRAW && day<CA_FIRST && !(completed&1) && native) ||
         (day>=237 && day<=251 && !(completed&2)) ||
         (day>=258 && day<=293 && !(completed&4)) ||
         (day>=300 && day<=335 && !(completed&8)) ||
         (day>=CQ_CENTRAL_FINAL_DAY && day<365 && !(completed&16));
}

static void ca_tick(void* ctx)
{
  if (!g_ca_group || g_ca_busy) return;
  static int timeline=-1, edition=-1, completed;
  static ca_retry retry={.date=-1};
  int gd=game_date(), day=gd%365, year=gd/365;
  if (gd<0 || day<CA_DRAW) return;
  if (timeline!=g_timeline || edition!=year) {
    timeline=g_timeline; edition=year; completed=0; retry.date=-1;
  }
  if (!ca_pending(day,completed,ctx!=0) || !ca_retry_due(&retry,gd,ctx!=0,GetTickCount64())) return;
  g_ca_busy=1;
  ca_drive(ctx,year,day,&completed);
  g_ca_busy=0;
}
