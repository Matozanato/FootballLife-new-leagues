/* Use native single-match pre-rounds for fixture emission and penalty rules.
 * Advance the cup from its combined sporting tables and verified tie results. */
static int lc_lpre_first;
static uint32_t lc_inaugural[LC_CLUBS];
static uint16_t lc_replica_days[LC_KO_STAGES][4];
static uint16_t lc_group_days[LC_BATCHES][LC_TIES];

__declspec(dllexport) const uint32_t fl26_swiss_leagues_ids_abi=2;
__declspec(dllexport) int fl26_swiss_leagues_probe(const uint32_t* data, int n)
{
  lc_phase phase;
  if (!g_cq_hooks || g_lc_enabled || !lc_parse(&phase,data,n)) return 0;
  uint16_t rows[(LC_BATCHES+LC_KO_STAGES)*(6+4*LC_TIES)]={0};
  uint16_t singles[LC_BATCHES+LC_KO_STAGES], *row=rows;
  for (int b=0;b<LC_BATCHES;b++) {
    singles[b]=row[0]=phase.master[b]; row[2]=LC_FILL;
    row[3]=row[4]=lc_preferred[b]; row[5]=2*LC_TIES;
    row+=6+4*LC_TIES;
  }
  int rounds=LC_BATCHES;
  for (int i=0;i<LC_KO_STAGES && phase.ko[i];i++) {
    singles[rounds++]=row[0]=phase.ko[i]; row[2]=LC_FILL;
    row[3]=row[4]=LC_KO_LAST; row[5]=2*lc_ko_ties[i];
    row+=6+4*lc_ko_ties[i];
  }
  if (g_nlpre+rounds>MAX_LPRE) return 0;
  for (int i=0;i<rounds;i++) {
    int tie;
    if (lpre_of(singles[i],&tie)>=0 || ca_owned(singles[i])) return 0;
    for (int j=0;j<g_nccup;j++)
      if (g_ccup[j].reg==singles[i] || g_ccup[j].ko==singles[i]) return 0;
  }
  lc_lpre_first=g_nlpre;
  if (lpre_register(rows,rounds,1)!=lc_lpre_first+rounds ||
      fl26_swiss_lpre_single(singles,rounds)!=rounds) return 0;
  g_lc=phase;
  memcpy(lc_inaugural,phase.clubs,sizeof lc_inaugural);
  g_lc_enabled=1;
  logf("Leagues Cup prototype: six native single-match batches registered");
  return 1;
}

static int lc_handles(uint32_t handles[LC_CLUBS])
{
  for (int i=0;i<LC_CLUBS;i++) {
    handles[i]=canon_club(g_lc.clubs[i]<<14);
    if (!real_club(handles[i]) || handles[i]>>14!=g_lc.clubs[i]) return 0;
  }
  return 1;
}

#define LC_ANNUAL_KEY(y) ((uint16_t)(0xb400u|((y)&1)))
#define LC_FIELD_KEY(y) ((uint16_t)(0xb402u|((y)&1)))
#define LC_PLAN_KEY(y) ((uint16_t)(0xb404u|((y)&1)))
#define LC_STOP_KEY(y) ((uint16_t)(0xb406u|((y)&1)))

static int lc_rollback_quarantined(unsigned stage)
{
  const final_t* entry=final_of(LC_STOP_KEY(g_lc.year));
  return entry && entry->n==2 && entry->club[0]==g_lc.year && (entry->club[1]&(1u<<stage));
}

static void lc_quarantine_rollback(unsigned stage)
{
  int now=abs_day();
  if (now<0) return;
  uint16_t key=LC_STOP_KEY(g_lc.year);
  final_t* entry=final_of(key);
  unsigned previous=entry && entry->n==2 && entry->club[0]==g_lc.year ? entry->club[1] : 0;
  if (!entry) entry=final_new(key);
  if (!entry) return;
  entry->reg=key;
  entry->n=2;
  entry->day=now;
  entry->club[0]=g_lc.year;
  entry->club[1]=previous|(1u<<stage);
  state_store();
}

/* Capture only a full MLS annual round robin across both shipped phases. */
static void lc_capture_annual(int boundary)
{
  if (!g_lc_enabled || !g_lc.mexico) return;
  int gd=game_date(), ad=abs_day(), creation=concacaf_career_start(gd);
  if (gd<0 || ad<0 || creation<0 || (!boundary && gd%365<300 && gd%365>7)) return;
  static int last=-1, tl=-1;
  if (!boundary && last==gd && tl==g_timeline) return;
  last=gd; tl=g_timeline;
  state_sync();
  uint32_t cap;
  const unsigned char* matches=car_matches(&cap);
  if (!matches) return;
  const ca_source src={.membership=51,.calendar=1,.part={{166,30,1,0},{167,30,1,0}}};
  for (int year=gd/365-1;year<=gd/365;year++) {
    uint16_t key=LC_ANNUAL_KEY(year);
    final_t* keep=final_of(key);
    if (keep && (gd-ad+keep->day)/365==year) continue;
    ca_annual_part part[CA_PARTS]={0};
    for (uint32_t i=0;i<cap;i++) {
      const unsigned char* m=matches+(size_t)i*MATCH_STRIDE;
      uint16_t id=*(const uint16_t*)(m+4);
      if (*(const uint16_t*)m==0xffff || (id!=166 && id!=167)) continue;
      int date=ko_mdate(m), p=id-166;
      if (date<0) { part[p].invalid=1; continue; }
      if (date/365!=year) continue;
      ca_annual_match(part+p,src.part+p,date,(m[7]&0x40) && date>=creation && date<=gd,
                      *(const uint32_t*)(m+0x14),*(const uint32_t*)(m+0x18),m[0x1c],m[0x1f]);
    }
    final_t result;
    if (!ca_annual_rank(&src,part,0,&result)) continue;
    if (!keep) keep=final_new(key);
    if (!keep) return;
    int date=part[0].latest>part[1].latest ? part[0].latest : part[1].latest;
    result.reg=key; result.day=ad-(gd-date);
    *keep=result;
    state_store();
    logf("Leagues Cup: retained completed MLS annual table year=%d clubs=%u",year,result.n);
  }
}

static int lc_field_for_year(int year, int gd, int committed)
{
  if (year==LC_YEAR) {
    memcpy(g_lc.clubs,lc_inaugural,sizeof lc_inaugural);
    g_lc.year=LC_YEAR;
    return 1;
  }
  if (!g_lc.mexico) return 0;
  state_sync();
  int ad=abs_day(), creation=concacaf_career_start(gd);
  if (ad<0 || creation<0) return 0;
  uint32_t field[LC_CLUBS];
  if (committed) {
    final_t* keep=final_of(LC_FIELD_KEY(year));
    int when=keep ? gd-(ad-keep->day) : 0;
    if (!keep || keep->n!=LC_CLUBS || when/365!=year || when<creation || when>gd ||
        !cq_unique(keep->club,LC_CLUBS)) return 0;
    for (int i=0;i<LC_CLUBS;i++) field[i]=keep->club[i]>>14;
  } else {
    lc_capture_annual(1);
    final_t* ranks=final_of(LC_ANNUAL_KEY(year-1));
    int ended=ranks ? gd-(ad-ranks->day) : 0;
    const unsigned char* reg=get_rec(g_lc.mexico);
    if (!ranks || ranks->n!=30 || ended/365!=year-1 || ended<creation || ended>=gd ||
        !reg || rec_count((void*)reg)!=LC_SIDE) return 0;
    if (!lc_select_field(field,ranks->club,ranks->n,rec_clubs((unsigned char*)reg),LC_SIDE)) return 0;
  }
  memcpy(g_lc.clubs,field,sizeof field);
  g_lc.year=(uint16_t)year;
  return 1;
}

static int lc_occupied_year(void)
{
  uint32_t cap;
  const unsigned char* matches=car_matches(&cap);
  if (!matches) return -1;
  int year=0;
  for (uint32_t i=0;i<cap;i++) {
    const unsigned char* m=matches+(size_t)i*MATCH_STRIDE;
    if (*(const uint16_t*)m==0xffff || !lc_owns(&g_lc,*(const uint16_t*)(m+4))) continue;
    int date=ko_mdate(m);
    if (date<0 || (year && date/365!=year)) return -1;
    year=date/365;
  }
  return year;
}

enum { LC_MATCHES=LC_BATCHES*LC_TIES, LC_US_CUP=54 };
typedef struct {
  uint32_t id[LC_MATCHES];
  uint16_t day[LC_MATCHES];
  unsigned count, free;
} lc_records;

static unsigned char lc_pending_us[365];
static int lc_pending_timeline=-1;

static void lc_note_cup(const vec_t* v)
{
  if (!g_lc_enabled || !v || !v->b || v->e<v->b) return;
  if (lc_pending_timeline!=g_timeline) {
    memset(lc_pending_us,0,sizeof lc_pending_us);
    lc_pending_timeline=g_timeline;
  }
  for (const date_t* d=(const date_t*)v->b; (const unsigned char*)(d+1)<=v->e; d++)
    if (d->day<365) lc_pending_us[d->day]=1;
}

static int lc_scan(lc_results* results, lc_records* records, lc_calendar* calendar)
{
  uint32_t cap;
  const unsigned char* matches=car_matches(&cap);
  if (!matches) return 0;
  memset(results,0,sizeof *results);
  memset(records,0,sizeof *records);
  unsigned char relevant[1024]={0};
  uint64_t participants[1024]={0};
  if (calendar) {
    memset(calendar,0,sizeof *calendar);
    calendar->group_detail=1;
    /* A known participant in a competition makes its unresolved rows relevant. */
    relevant[LC_US_CUP]=3;
    participants[LC_US_CUP]=(UINT64_C(1)<<LC_SIDE)-1;
    for (uint32_t i=0;i<cap;i++) {
      const unsigned char* m=matches+(size_t)i*MATCH_STRIDE;
      if (*(const uint16_t*)m==0xffff || *(const uint16_t*)(m+8)!=g_lc.year) continue;
      uint16_t reg=*(const uint16_t*)(m+4);
      if (lc_batch(&g_lc,reg)>=0) continue;
      relevant[reg&1023]|=lc_cohort(&g_lc,*(const uint32_t*)(m+0x14)>>14) |
                         lc_cohort(&g_lc,*(const uint32_t*)(m+0x18)>>14);
      if (lc_ko_stage(&g_lc,reg)<0)
        participants[reg&1023]|=lc_club_mask(&g_lc,*(const uint32_t*)(m+0x14)>>14) |
                                 lc_club_mask(&g_lc,*(const uint32_t*)(m+0x18)>>14);
    }
  }
  int valid=1;
  for (uint32_t i=0;i<cap;i++) {
    const unsigned char* m=matches+(size_t)i*MATCH_STRIDE;
    if (*(const uint16_t*)m==0xffff) { records->free++; continue; }
    uint16_t reg=*(const uint16_t*)(m+4);
    int date=ko_mdate(m);
    uint32_t h=*(const uint32_t*)(m+0x14)>>14, a=*(const uint32_t*)(m+0x18)>>14;
    if (lc_batch(&g_lc,reg)>=0) {
      unsigned n=records->count++;
      if (n<LC_MATCHES) {
        records->id[n]=lay_day_elem()==4 ? *(const uint32_t*)m : *(const uint16_t*)m;
        records->day[n]=(uint16_t)(date%365);
      }
      if (!lc_ingest(&g_lc,results,reg,date,m[7],h,a,m+0x1c)) valid=0;
      continue;
    }
    if (calendar && date/365==g_lc.year) {
      int day=date%365;
      calendar->load[day]++;
      unsigned cohorts=lc_cohort(&g_lc,h)|lc_cohort(&g_lc,a);
      int unresolved=!h || !a || ((*(const uint32_t*)(m+0x14))&KO_TBD)==KO_TBD ||
                                 ((*(const uint32_t*)(m+0x18))&KO_TBD)==KO_TBD;
      if (unresolved)
        cohorts|=relevant[reg&1023];
      lc_block(calendar,cohorts,day);
      if (lc_ko_stage(&g_lc,reg)<0) {
        uint64_t clubs=lc_club_mask(&g_lc,h)|lc_club_mask(&g_lc,a);
        lc_block_knockout(calendar,clubs|(unresolved ? participants[reg&1023] : 0),day);
        if (unresolved) for (int i=0;i<LC_CLUBS;i++)
          if (cohorts&(1u<<(i/LC_TIES%2))) clubs|=UINT64_C(1)<<i;
        lc_block_clubs(calendar->group_blocked,clubs,day);
      }
    }
  }
  if (calendar) {
    calendar->capacity=day_cap();
    if (!calendar->capacity || calendar->capacity>10000) return 0;
    for (int d=g_lc.first;d<=LC_KO_RECOVERY_LAST;d++) {
      int filed=day_load(d);
      if (filed<0) {
        calendar->calendar_unknown[d]=1;
        continue;
      }
      if ((unsigned)filed>calendar->load[d]) calendar->load[d]=(unsigned)filed;
    }
    if (lc_pending_timeline==g_timeline)
      for (int d=g_lc.first-LC_REST+1;d<=LC_KO_RECOVERY_LAST+LC_REST-1;d++)
        if (lc_pending_us[d]) {
          lc_block(calendar,3,d);
          lc_block_knockout(calendar,participants[LC_US_CUP],d);
          lc_block_clubs(calendar->group_blocked,LC_ALL_CLUBS,d);
        }
  }
  return valid;
}

/* Scan the actual day lists by match ID, including stray IDs outside August. */
static int lc_filed(const lc_records* records, int expected)
{
  unsigned char* owner=(unsigned char*)((owner_fn)(uintptr_t)(g_base+OWNER_RVA))();
  const unsigned char* blk=owner ? *(const unsigned char**)(owner+0x48) : 0;
  int cap=lay_day_ids();
  unsigned count[LC_MATCHES]={0};
  if (!blk || cap<=0 || cap>10000 || records->count>LC_MATCHES) return 0;
  for (int d=0;d<365;d++) {
    const unsigned char* list=blk+lay_calendar()+(size_t)d*lay_day_size();
    for (int i=0;i<cap;i++) {
      uint32_t id=lay_day_id(list,i);
      if (id==0xffff) break;
      for (unsigned j=0;j<records->count;j++) if (records->id[j]==id) {
        if (!expected || records->day[j]!=d || ++count[j]!=1) return 0;
        break;
      }
    }
  }
  for (unsigned j=0;j<records->count;j++) if (count[j]!=(unsigned)expected) return 0;
  return 1;
}

static int lc_ready(void)
{
  for (int b=0;b<LC_BATCHES;b++) for (int t=-1;t<LC_TIES;t++) {
    uint16_t id=t<0 ? g_lc.master[b] : lpre_tie(&g_lpre[lc_lpre_first+b],t);
    unsigned char* rec=get_rec(id);
    /* File bits 25/27 load into live +0x304 bits 4/3. */
    if (!rec || (*(const uint32_t*)(rec+0x304)&0x18)!=8 || rec_count(rec)) return 0;
  }
  return 1;
}

static int lc_dates_match(const uint16_t days[LC_BATCHES])
{
  for (int b=0;b<LC_BATCHES;b++) if (days[b]!=g_lpre[lc_lpre_first+b].days[0]) return 0;
  return 1;
}

static void lc_seed(lpre_t* l, const uint32_t* handles)
{
  l->nclub=2*l->ties;
  memcpy(l->club,handles,l->nclub*sizeof *handles);
  for (int t=0;t<l->ties;t++) {
    uint16_t reg=lpre_tie(l,t);
    ((freetab_fn)(uintptr_t)(g_base+FREETAB_RVA))(0,reg);
    ca_set(reg,l->club+2*t,2);
  }
  ca_set(l->reg,l->club,l->nclub);
  run_flush();
}

static void lc_emit(lpre_t* l, const uint32_t* handles)
{
  lc_seed(l,handles);
  start_stage(0,l->reg);
  car_register(&l->reg,1);
}

static int lc_start(const uint32_t handles[LC_CLUBS], lc_records* records)
{
  lc_results audit;
  for (int b=0;b<LC_BATCHES;b++) {
    lpre_t* l=&g_lpre[lc_lpre_first+b];
    uint16_t ties[LC_TIES];
    uint32_t pairs[2*LC_TIES];
    for (int t=0;t<LC_TIES;t++) {
      unsigned h,a;
      lc_pair(b,t,&h,&a);
      pairs[2*t]=handles[h]; pairs[2*t+1]=handles[a];
      ties[t]=lpre_tie(l,t);
    }
    int split=0;
    for (int t=0;t<LC_TIES;t++) split|=lc_group_days[b][t] && lc_group_days[b][t]!=l->days[0];
    if (split) {
      lc_seed(l,pairs);
      for (int t=0;t<LC_TIES;t++) {
        if (!lc_scan(&audit,records,0)) return 0;
        if (!(audit.seen[b]&(1u<<t))) start_stage(0,ties[t]);
      }
      if (!lc_scan(&audit,records,0)) return 0;
      uint16_t missing[LC_TIES];
      int count=0;
      for (int t=0;t<LC_TIES;t++)
        if (!(audit.seen[b]&(1u<<t))) missing[count++]=ties[t];
      if (count) car_register(missing,count);
    } else lc_emit(l,pairs);
    if (!lc_scan(&audit,records,0)) return 0;
    /* Only fall back when the master and every replica provably emitted zero. */
    if (!split && !audit.seen[b]) {
      car_register(ties,LC_TIES);
      if (!lc_scan(&audit,records,0)) return 0;
    }
    if (audit.seen[b]!=(1u<<LC_TIES)-1 || records->count!=(unsigned)(b+1)*LC_TIES) {
      logf("Leagues Cup prototype: native emission incomplete master=%u batch=%d records=%u",
           l->reg,b+1,records->count);
      return 0;
    }
  }
  for (int b=0;b<LC_BATCHES;b++) for (int t=0;t<LC_TIES;t++) {
    unsigned expected=lc_group_days[b][t] ? lc_group_days[b][t] : g_lpre[lc_lpre_first+b].days[0];
    if (audit.fixture[b][t]!=expected) return 0;
  }
  return lc_group_rest(&audit) && lc_filed(records,1);
}

static int lc_register_edition(void* ctx, const uint32_t handles[LC_CLUBS], car_close_fn rollback)
{
  lc_records emitted={0}, remaining;
  if (lc_start(handles,&emitted)) return 1;
  lc_results results;
  int rolled_back=rollback(ctx,g_lc.master) && lc_scan(&results,&remaining,0) &&
                  !remaining.count && lc_filed(&emitted,0) && lc_ready();
  logf("Leagues Cup prototype: incomplete registration, rollback %s",
       rolled_back ? "verified" : "FAILED; stop isolated validation");
  return rolled_back ? 0 : -1;
}

static int lc_fixture_space(unsigned needed)
{
  unsigned char* owner=(unsigned char*)((owner_fn)(uintptr_t)(g_base+OWNER_RVA))();
  const unsigned char* blk=owner ? *(const unsigned char**)(owner+0x48) : 0;
  unsigned cap=RT_N, free=0;
  if (!blk || !cap || cap>200000) return 0;
  for (unsigned i=0;i<cap;i++) {
    uint16_t reg=*(const uint16_t*)(blk+RT_OFF+(size_t)i*RT_REC);
    if ((!reg || reg==0xffff) && ++free>=needed) return 1;
  }
  return 0;
}

static int lc_plan_timeline=-1;

static void lc_apply_days(const uint16_t days[LC_BATCHES], int committed)
{
  for (int b=0;b<LC_BATCHES;b++) {
    lpre_t* l=&g_lpre[lc_lpre_first+b];
    l->days[0]=l->days[1]=days[b];
  }
  lc_plan_timeline=committed ? g_timeline : -1;
}

static void lc_apply_group(const uint16_t days[LC_BATCHES],
                           const uint16_t fixture[LC_BATCHES][LC_TIES], int committed)
{
  lc_apply_days(days,committed);
  if (fixture) memcpy(lc_group_days,fixture,sizeof lc_group_days);
  else memset(lc_group_days,0,sizeof lc_group_days);
}

static void lc_recover_for_dates(void)
{
  int gd=game_date();
  if (g_lc_busy || lc_plan_timeline==g_timeline || gd<0) return;
  if (g_lc.mexico) {
    int year=lc_occupied_year();
    if (year<=0 || !lc_field_for_year(year,gd,1)) return;
  } else if (gd/365!=g_lc.year) return;
  lc_results results;
  lc_records records;
  if (lc_scan(&results,&records,0) && records.count==LC_MATCHES && lc_group_rest(&results))
    lc_apply_group(results.days,results.fixture,1);
}

typedef struct {
  lc_records records;
  uint32_t won[4], lost[4];
  uint32_t record_index[4];
  uint16_t day, first, tie_day[4];
  unsigned seen;
} lc_knockout;

static void lc_ko_recover_date(int stage)
{
  if (stage<0 || g_lc_busy || game_date()/365!=g_lc.year) return;
  memset(lc_replica_days[stage],0,sizeof lc_replica_days[stage]);
  uint32_t cap;
  const unsigned char* matches=car_matches(&cap);
  if (!matches) return;
  uint16_t dates[4]={0};
  int first=0, common=0, n=0;
  for (uint32_t i=0;i<cap;i++) {
    const unsigned char* m=matches+(size_t)i*MATCH_STRIDE;
    if (*(const uint16_t*)m==0xffff || lc_ko_stage(&g_lc,*(const uint16_t*)(m+4))!=stage) continue;
    unsigned replica=*(const uint16_t*)(m+4)>>10;
    int observed=ko_mdate(m)-g_lc.year*365;
    if (observed<g_lc.first || observed>LC_KO_RECOVERY_LAST || replica>lc_ko_ties[stage]) return;
    if (replica && dates[replica-1]) return;
    if (replica) dates[replica-1]=(uint16_t)observed;
    else if (common && common!=observed) return;
    else common=observed;
    if (!first || observed<first) first=observed;
    n++;
  }
  if (n!=lc_ko_ties[stage]) return;
  for (unsigned t=0;t<lc_ko_ties[stage];t++)
    if (!dates[t]) {
      if (!common) return;
      dates[t]=(uint16_t)common;
    }
  memcpy(lc_replica_days[stage],dates,sizeof dates);
  g_lpre[lc_lpre_first+LC_BATCHES+stage].days[0]=g_lpre[lc_lpre_first+LC_BATCHES+stage].days[1]=(uint16_t)first;
}

static int lc_knockout_read(int stage, const uint32_t* pairs, lc_knockout* result)
{
  memset(result,0,sizeof *result);
  uint32_t cap;
  const unsigned char* matches=car_matches(&cap);
  if (!matches) return 0;
  int valid=1;
  for (uint32_t i=0;i<cap;i++) {
    const unsigned char* m=matches+(size_t)i*MATCH_STRIDE;
    uint16_t reg=*(const uint16_t*)(m+4);
    if (*(const uint16_t*)m==0xffff || lc_ko_stage(&g_lc,reg)!=stage) continue;
    int d=ko_mdate(m)-g_lc.year*365;
    unsigned n=result->records.count++;
    if (n>=LC_MATCHES) return 0;
    result->records.id[n]=lay_day_elem()==4 ? *(const uint32_t*)m : *(const uint16_t*)m;
    result->records.day[n]=(uint16_t)d;
    uint32_t home=*(const uint32_t*)(m+0x14)>>14, away=*(const uint32_t*)(m+0x18)>>14;
    int t=0;
    for (;t<lc_ko_ties[stage];t++)
      if ((pairs[2*t]==home && pairs[2*t+1]==away) || (pairs[2*t]==away && pairs[2*t+1]==home)) break;
    if (t==lc_ko_ties[stage] || ((reg>>10) && (reg>>10)!=t+1) || (result->seen&(1u<<t)) ||
        d<g_lc.first || d>LC_KO_RECOVERY_LAST) { valid=0; continue; }
    result->tie_day[t]=(uint16_t)d;
    if (d>result->day) result->day=(uint16_t)d;
    if (!result->first || d<result->first) result->first=(uint16_t)d;
    result->seen|=1u<<t;
    result->record_index[t]=i;
    if (m[7]&0x40) {
      uint32_t winner=lc_knockout_winner(home,away,m+0x1c);
      if (!winner) { valid=0; continue; }
      result->won[t]=winner; result->lost[t]=winner==home ? away : home;
    }
  }
  return valid;
}

static int lc_ko_last_day(int stage)
{
  return LC_KO_RECOVERY_LAST-(LC_KO_STAGES-1-stage)*(LC_REST+LC_PROCESS_BUFFER);
}

static int lc_ko_try_day(int* attempted, int stage, int today)
{
  if (*attempted==INT_MAX || *attempted==today || today+LC_REST>lc_ko_last_day(stage))
    return 0;
  *attempted=today;
  return 1;
}

static int lc_ko_conflict(int stage, const lc_knockout* round, const uint32_t* pairs)
{
  uint32_t cap;
  const unsigned char* matches=car_matches(&cap);
  if (!matches) return 1;
  for (uint32_t i=0;i<cap;i++) {
    const unsigned char* m=matches+(size_t)i*MATCH_STRIDE;
    if (*(const uint16_t*)m==0xffff) continue;
    uint16_t reg=*(const uint16_t*)(m+4);
    if (lc_ko_stage(&g_lc,reg)==stage) continue;
    int day=ko_mdate(m)-g_lc.year*365;
    uint32_t home=*(const uint32_t*)(m+0x14)>>14, away=*(const uint32_t*)(m+0x18)>>14;
    for (int t=0;t<2*lc_ko_ties[stage];t++)
      if (abs(day-round->tie_day[t/2])<LC_REST && (pairs[t]==home || pairs[t]==away)) return 1;
  }
  return 0;
}

static unsigned lc_ko_space(int stage, unsigned* matches)
{
  *matches=0;
  unsigned rounds=0;
  for (int s=stage;s<LC_KO_STAGES && g_lc.ko[s];s++) {
    *matches+=lc_ko_ties[s];
    rounds++;
  }
  return *matches+rounds;
}

static int lc_ko_rules_empty(int first, int end)
{
  for (int s=first;s<end && g_lc.ko[s];s++) {
    const lpre_t* l=&g_lpre[lc_lpre_first+LC_BATCHES+s];
    for (int t=-1;t<l->ties;t++) {
      uint16_t id=t<0 ? l->reg : lpre_tie(l,t);
      unsigned char* rec=get_rec(id);
      if (!rec || (*(const uint32_t*)(rec+0x304)&0x18)!=8 || rec_count(rec)) {
        logf("Leagues Cup knockout preflight master=%u: invalid regulation=%u present=%d flags=%x clubs=%u",
             l->reg,id,rec!=0,rec ? *(const uint32_t*)(rec+0x304) : 0,rec ? rec_count(rec) : 0);
        return 0;
      }
    }
  }
  return 1;
}

static int lc_ko_register(void* ctx, int stage, const uint16_t dates[4], const uint32_t* pairs, lc_knockout* result)
{
  typedef int (*rollback_stage_fn)(void*, uint16_t);
  typedef int (*rollback_ids_fn)(void*, uint16_t, unsigned);
  HMODULE join=GetModuleHandleW(L"fl26join.dll");
  rollback_stage_fn rollback=join ? (rollback_stage_fn)(uintptr_t)GetProcAddress(join,"fl26_join_rollback_leagues_stage") : 0;
  rollback_ids_fn by_id=join ? (rollback_ids_fn)(uintptr_t)GetProcAddress(join,"fl26_join_rollback_leagues_stage_ids") : 0;
  car_close_fn ready=join ? (car_close_fn)(uintptr_t)GetProcAddress(join,"fl26_join_rollback_leagues") : 0;
  if ((g_lc.allocated_ids ? !by_id : !rollback) || !ready || !ready(ctx,0)) {
    logf("Leagues Cup knockout preflight master=%u: rollback unavailable (module=%d stage export=%d readiness export=%d)",
         g_lc.ko[stage],join!=0,rollback!=0,ready!=0);
    return 0;
  }
  lpre_t* l=&g_lpre[lc_lpre_first+LC_BATCHES+stage];
  uint16_t ids[4];
  if (!lc_ko_rules_empty(stage,LC_KO_STAGES)) return 0;
  for (int t=0;t<l->ties;t++) ids[t]=lpre_tie(l,t);
  uint32_t handles[8];
  for (int t=0;t<2*l->ties;t++) {
    handles[t]=canon_club(pairs[t]<<14);
    if (!real_club(handles[t]) || handles[t]>>14!=pairs[t]) {
      logf("Leagues Cup knockout preflight master=%u: invalid club=%u handle=%x",l->reg,pairs[t],handles[t]);
      return 0;
    }
  }
  uint16_t first=dates[0];
  int split=0;
  for (int t=0;t<l->ties;t++) {
    if (dates[t]<first) first=dates[t];
    split|=dates[t]!=dates[0];
  }
  l->days[0]=l->days[1]=first;
  memcpy(lc_replica_days[stage],dates,sizeof lc_replica_days[stage]);
  g_lc_busy=1;
  if (!split) lc_emit(l,handles);
  else {
    lc_seed(l,handles);
    unsigned expected=(1u<<l->ties)-1;
    int safe=1;
    for (int t=0;t<l->ties && safe;t++) {
      safe=lc_knockout_read(stage,pairs,result);
      for (int i=0;i<l->ties && safe;i++)
        if ((result->seen&(1u<<i)) && result->tie_day[i]!=dates[i]) safe=0;
      if (safe && !(result->seen&(1u<<t))) start_stage(0,ids[t]);
    }
    if (safe && lc_knockout_read(stage,pairs,result) && result->seen!=expected) {
      uint16_t missing[4];
      int count=0;
      for (int t=0;t<l->ties;t++) {
        if (!(result->seen&(1u<<t))) missing[count++]=ids[t];
        else if (result->tie_day[t]!=dates[t]) safe=0;
      }
      if (safe && count) car_register(missing,count);
    }
  }
  int valid=lc_knockout_read(stage,pairs,result);
  if (!split && valid && !result->records.count) {
    car_register(ids,l->ties);
    valid=lc_knockout_read(stage,pairs,result);
  }
  int filed=valid && result->records.count==l->ties && lc_filed(&result->records,1);
  int correct_dates=1;
  for (int t=0;t<l->ties;t++) correct_dates&=result->tie_day[t]==dates[t];
  int complete=valid && correct_dates && result->records.count==l->ties && filed;
  if (!complete) {
    logf("Leagues Cup knockout emission master=%u: valid=%d count=%u/%d dates=%u/%u/%u/%u expected=%u/%u/%u/%u filing=%d",
         l->reg,valid,result->records.count,l->ties,result->tie_day[0],result->tie_day[1],
         result->tie_day[2],result->tie_day[3],dates[0],dates[1],dates[2],dates[3],filed);
    lc_knockout after;
    int cleared=(g_lc.allocated_ids ? by_id(ctx,l->reg,l->ties) : rollback(ctx,l->reg)) && lc_knockout_read(stage,pairs,&after) &&
                !after.records.count && lc_filed(&result->records,0) && lc_ko_rules_empty(stage,stage+1);
    memset(lc_replica_days[stage],0,sizeof lc_replica_days[stage]);
    logf("Leagues Cup: knockout emission failed master=%u rollback=%s",l->reg,cleared ? "verified" : "FAILED");
    if (!cleared) {
      g_lc_busy=0;
      return -1;
    }
  }
  g_lc_busy=0;
  return complete;
}

static int lc_keep_podium(const lc_knockout* final, uint32_t clubs[3])
{
  int gd=game_date(), ad=abs_day(), completed=g_lc.year*365+final->day;
  int creation=concacaf_career_start(gd);
  if (gd<completed || ad<0 || creation<0 || creation>g_lc.year*365+LC_FILL) return 0;
  const uint32_t ids[]={final->won[1],final->lost[1],final->won[0]};
  for (int i=0;i<3;i++) {
    clubs[i]=canon_club(ids[i]<<14);
    if (!real_club(clubs[i])) return 0;
  }
  if (!cq_unique(clubs,3)) return 0;
  state_sync();
  uint16_t key=(uint16_t)(0xb000u|g_lc.ko[2]);
  final_t* keep=final_of(key);
  int day=ad-(gd-completed);
  if (keep && keep->day==day && keep->n==3 && !memcmp(keep->club,clubs,3*sizeof *clubs)) return 1;
  if (!keep) keep=final_new(key);
  if (!keep) return 0;
  keep->reg=key; keep->day=day; keep->n=3;
  memcpy(keep->club,clubs,3*sizeof *clubs);
  state_store();
  logf("Leagues Cup: sporting podium edition=%d champion=%u runner_up=%u third=%u",g_lc.year,ids[0],ids[1],ids[2]);
  return 1;
}

/* Reconstruct the complete bracket in this save before trusting any shared
 * journal row. A career sharing the same club cannot inherit a stale podium. */
static int lc_completed_podium(lc_knockout* final)
{
  uint32_t pairs[8];
  lc_results phase;
  lc_records records;
  if (!lc_scan(&phase,&records,0) || records.count!=LC_MATCHES || !lc_group_rest(&phase) ||
      !lc_quarterfinals(&g_lc,&phase,pairs)) return 0;
  int previous=0;
  for (int b=0;b<LC_BATCHES;b++) if (phase.days[b]>previous) previous=phase.days[b];
  lc_knockout result;
  for (int stage=0;stage<LC_KO_STAGES;stage++) {
    if (!lc_knockout_read(stage,pairs,&result) || result.records.count!=lc_ko_ties[stage] ||
        result.first<previous+LC_REST || lc_ko_conflict(stage,&result,pairs)) return 0;
    for (int i=0;i<lc_ko_ties[stage];i++) if (!result.won[i]) return 0;
    previous=result.day;
    if (stage<2) lc_advance_bracket(stage,result.won,result.lost,pairs);
  }
  *final=result;
  return 1;
}

static int lc_feeder(cq_source* source, int edition, int gd, int creation)
{
  int year=cq_central_year(edition);
  if (!g_lc_enabled || !g_lc.ko[2] || source->reg!=g_lc.ko[2] || year<1990 || creation<0) return 0;
  if (creation>year*365+LC_FILL) return 1;
  if (gd/365!=year+1 || lc_occupied_year()!=year || !lc_field_for_year(year,gd,1)) return 0;
  lc_knockout result;
  if (!lc_completed_podium(&result) || !lc_keep_podium(&result,source->club)) return 0;
  source->n=3;
  return 1;
}

static int lc_close_edition(void* ctx)
{
  typedef int (*close_fn)(void*);
  typedef int (*close_ids_fn)(void*, const uint16_t*);
  HMODULE join=GetModuleHandleW(L"fl26join.dll");
  close_fn close=join ? (close_fn)(uintptr_t)GetProcAddress(join,"fl26_join_close_leagues_edition") : 0;
  close_ids_fn by_id=join ? (close_ids_fn)(uintptr_t)GetProcAddress(join,"fl26_join_close_leagues_edition_ids") : 0;
  if (!ctx || (g_lc.allocated_ids ? !by_id : !close)) return 0;
  if (!g_lc.allocated_ids) for (int i=0;i<LC_BATCHES;i++) if (g_lc.master[i]!=700+i) return 0;
  lc_knockout result;
  uint32_t podium[3];
  if (!lc_completed_podium(&result) || !lc_keep_podium(&result,podium)) return 0;
  lc_results phase;
  lc_records old, finals[LC_KO_STAGES]={0};
  if (!lc_scan(&phase,&old,0) || old.count!=LC_MATCHES) return 0;
  uint32_t cap;
  const unsigned char* matches=car_matches(&cap);
  if (!matches) return 0;
  for (uint32_t i=0;i<cap;i++) {
    const unsigned char* m=matches+(size_t)i*MATCH_STRIDE;
    int k=lc_ko_stage(&g_lc,*(const uint16_t*)(m+4));
    if (*(const uint16_t*)m==0xffff || k<0) continue;
    unsigned at=finals[k].count++;
    if (at>=lc_ko_ties[k]) return 0;
    finals[k].id[at]=lay_day_elem()==4 ? *(const uint32_t*)m : *(const uint16_t*)m;
  }
  uint16_t ids[LC_BATCHES+LC_KO_STAGES];
  memcpy(ids,g_lc.master,sizeof g_lc.master);
  memcpy(ids+LC_BATCHES,g_lc.ko,sizeof g_lc.ko);
  if (!(g_lc.allocated_ids ? by_id(ctx,ids) : close(ctx)) || !lc_filed(&old,0)) return 0;
  for (int i=0;i<LC_KO_STAGES;i++)
    if (!lc_filed(finals+i,0)) return 0;
  return lc_occupied_year()==0 && lc_ready();
}

enum { LC_PLAN_FIELDS=1+LC_BATCHES+LC_KO_STAGES, LC_PLAN_SPLIT_FIELDS=LC_PLAN_FIELDS+4 };

static void lc_plan_store(const uint16_t groups[LC_BATCHES], const uint16_t knockout[LC_KO_STAGES],
                           int stage, const uint16_t* replicas)
{
  unsigned n=replicas ? LC_PLAN_SPLIT_FIELDS : LC_PLAN_FIELDS;
  uint32_t data[LC_PLAN_SPLIT_FIELDS]={g_lc.year};
  for (int i=0;i<LC_BATCHES;i++) data[1+i]=groups[i];
  uint16_t key=LC_PLAN_KEY(g_lc.year);
  final_t* entry=final_of(key);
  if (entry && entry->n>=LC_PLAN_FIELDS && !memcmp(entry->club,data,(1+LC_BATCHES)*sizeof *data))
    for (int i=0;i<stage;i++) data[1+LC_BATCHES+i]=entry->club[1+LC_BATCHES+i];
  for (int i=stage;i<LC_KO_STAGES;i++) data[1+LC_BATCHES+i]=knockout[i];
  if (replicas)
    for (unsigned i=0;i<4;i++) data[LC_PLAN_FIELDS+i]=replicas[i];
  if (entry && entry->n==n && !memcmp(entry->club,data,n*sizeof *data)) return;
  int now=abs_day();
  if (now<0) return;
  if (!entry) entry=final_new(key);
  if (!entry) return;
  entry->reg=key;
  entry->n=(uint16_t)n;
  entry->day=now;
  memcpy(entry->club,data,n*sizeof *data);
  state_store();
}

static void lc_trace_registration(unsigned master, const lc_records* records)
{
  for (unsigned i=0;i<records->count && i<LC_MATCHES;i++)
    if (master) logf("Leagues Cup register: year=%u master=%u match=%u actual_day=%u",
                     g_lc.year,master,records->id[i],records->day[i]);
    else logf("Leagues Cup register: year=%u Phase One match=%u actual_day=%u",
              g_lc.year,records->id[i],records->day[i]);
}

static int lc_plan_restore(const lc_results* phase, const lc_calendar* calendar, int stage,
                           int first, uint64_t possible, uint16_t out[LC_KO_STAGES])
{
  final_t* entry=final_of(LC_PLAN_KEY(g_lc.year));
  if (!entry || (entry->n!=LC_PLAN_FIELDS && entry->n!=LC_PLAN_SPLIT_FIELDS) ||
      entry->club[0]!=g_lc.year) return 0;
  for (int i=0;i<LC_BATCHES;i++) if (entry->club[1+i]!=phase->days[i]) return 0;
  uint16_t dates[LC_KO_STAGES]={0};
  for (int s=stage;s<LC_KO_STAGES;s++) {
    unsigned d=entry->club[1+LC_BATCHES+s];
    if (d<(unsigned)first || d>LC_KO_RECOVERY_LAST) {
      logf("Leagues Cup replan: reserved stage=%d day=%u outside %d..%d",s,d,first,LC_KO_RECOVERY_LAST);
      return 0;
    }
    if (calendar->calendar_unknown[d] || (calendar->knockout_blocked[d]&possible) ||
        calendar->load[d]+lc_ko_ties[s]>calendar->capacity) {
      logf("Leagues Cup replan: reserved stage=%d day=%u conflicting_clubs=%llx load=%u capacity=%u readable=%d",
           s,d,(unsigned long long)(calendar->knockout_blocked[d]&possible),
           calendar->load[d],calendar->capacity,!calendar->calendar_unknown[d]);
      return 0;
    }
    dates[s]=(uint16_t)d;
    first=(int)d+LC_REST+LC_PROCESS_BUFFER;
  }
  memcpy(out,dates,sizeof dates);
  return 1;
}

/* Feed concrete reservations to Mato's domestic date generator. Existing
 * domestic match records and outcome-dependent alternatives are left alone. */
static void lc_protect_domestic_dates(uint16_t regulation, uint8_t bad[365])
{
  if (!g_lc_enabled || lc_plan_timeline!=g_timeline || lc_owns(&g_lc,regulation)) return;
  int gd=game_date();
  if (gd<0 || gd/365!=g_lc.year) return;
  const final_t* plan=final_of(LC_PLAN_KEY(g_lc.year));
  if (!plan || (plan->n!=LC_PLAN_FIELDS && plan->n!=LC_PLAN_SPLIT_FIELDS) ||
      plan->club[0]!=g_lc.year) return;
  uint16_t groups[LC_BATCHES];
  for (int i=0;i<LC_BATCHES;i++) groups[i]=(uint16_t)plan->club[1+i];
  if (!lc_dates_match(groups)) return;
  unsigned char* rec=get_rec(regulation);
  if (!rec) return;
  unsigned n=rec_count(rec);
  if (n>48) return;
  uint64_t members=0;
  for (unsigned i=0;i<n;i++) members|=lc_club_mask(&g_lc,rec_clubs(rec)[i]>>14);
  if (!members) return;
  for (int b=0;b<LC_BATCHES;b++) for (int t=0;t<LC_TIES;t++) {
    unsigned d=lc_group_days[b][t];
    if (d<(unsigned)(gd%365) || d<LC_AUG_FIRST || d>LC_GROUP_LAST || !(members&lc_group_pair(b,t))) continue;
    for (unsigned blocked=d-LC_REST+1;blocked<d+LC_REST;blocked++) bad[blocked]=1;
  }
  for (unsigned k=1+LC_BATCHES;k<plan->n;k++) {
    unsigned d=plan->club[k];
    if (d<(unsigned)(gd%365) || d<LC_AUG_FIRST || d>LC_KO_RECOVERY_LAST) continue;
    for (unsigned t=d-LC_REST+1;t<d+LC_REST;t++) bad[t]=1;
  }
}

static void lc_ko_tick(void* ctx, int day, const lc_results* phase,
                       const lc_calendar* calendar, unsigned free_matches)
{
  if (!g_lc.ko[0]) return;
  uint32_t pairs[8];
  if (!lc_quarterfinals(&g_lc,phase,pairs)) return;
  static int timeline=-1, edition=-1, attempted[LC_KO_STAGES], published;
  static unsigned conflicts;
  if (timeline!=g_timeline || edition!=g_lc.year) {
    timeline=g_timeline; edition=g_lc.year; published=0; conflicts=0;
    for (int i=0;i<LC_KO_STAGES;i++) attempted[i]=-1;
  }
  int previous=0;
  for (int b=0;b<LC_BATCHES;b++) if (phase->days[b]>previous) previous=phase->days[b];
  for (int stage=0;stage<LC_KO_STAGES;stage++) {
    lc_knockout result;
    int n=lc_ko_ties[stage];
    int valid=lc_knockout_read(stage,pairs,&result);
    if (!valid) {
      logf("Leagues Cup: knockout master=%u has invalid native records",g_lc.ko[stage]);
      return;
    }
    if (result.records.count) {
      int filed=lc_filed(&result.records,1);
      if (result.records.count!=n || result.first<previous+LC_REST || !filed) {
        logf("Leagues Cup: knockout master=%u already has records, registration skipped (count=%u/%d date=%u earliest=%d filing=%d)",
             g_lc.ko[stage],result.records.count,n,result.day,previous+LC_REST,filed);
        return;
      }
    }
    if (!result.records.count) {
      if (ctx && attempted[stage]!=INT_MAX && lc_rollback_quarantined((unsigned)stage+1)) {
        logf("Leagues Cup: knockout master=%u quarantined after an unverified rollback",g_lc.ko[stage]);
        attempted[stage]=INT_MAX;
      }
      if (ctx && day+LC_REST>lc_ko_last_day(stage) && attempted[stage]!=INT_MAX) {
        logf("Leagues Cup: bounded recovery exhausted master=%u today=%d last=%d; edition preserved",
             g_lc.ko[stage],day,lc_ko_last_day(stage));
        attempted[stage]=INT_MAX;
      }
      if (ctx && lc_ko_try_day(&attempted[stage],stage,day)) {
        unsigned need_matches, need_slots=lc_ko_space(stage,&need_matches);
        if (free_matches<need_matches || !lc_fixture_space(need_slots)) {
          logf("Leagues Cup: knockout remaining capacity master=%u free matches=%u required=%u fixture slots required=%u",
               g_lc.ko[stage],free_matches,need_matches,need_slots);
          return;
        }
        uint64_t clubs[8]={0}, possible=0;
        for (int i=0;i<2*n;i++) {
          clubs[i]=lc_club_mask(&g_lc,pairs[i]);
          if (!clubs[i] || (possible&clubs[i])) {
            logf("Leagues Cup: invalid contender master=%u club=%u",g_lc.ko[stage],pairs[i]);
            return;
          }
          possible|=clubs[i];
        }
        uint16_t dates[LC_KO_STAGES]={0};
        unsigned alternatives=0;
        int first=(day>previous ? day : previous)+LC_REST;
        int restored=lc_plan_restore(phase,calendar,stage,first,possible,dates);
        uint16_t replicas[4]={0};
        int common=restored || lc_plan_remaining(calendar,stage,day,previous,clubs,dates,&alternatives);
        if (common) {
          for (int t=0;t<n;t++) replicas[t]=dates[stage];
        } else if (!lc_plan_split(calendar,stage,day,previous,clubs,replicas)) {
          logf("Leagues Cup: no full knockout continuation master=%u first=%d last=%d contenders=%llx",
               g_lc.ko[stage],first,LC_KO_RECOVERY_LAST,(unsigned long long)possible);
          return;
        }
        int status=lc_ko_register(ctx,stage,replicas,pairs,&result);
        if (status>0) {
          if (!common) {
            memset(dates,0,sizeof dates);
            dates[stage]=result.day;
          }
          lc_plan_store(phase->days,dates,stage,common ? 0 : replicas);
          logf("Leagues Cup: knockout registered master=%u replicas=%u/%u/%u/%u restored=%d alternatives=%u",
               g_lc.ko[stage],replicas[0],replicas[1],replicas[2],replicas[3],restored,alternatives);
          lc_trace_registration(g_lc.ko[stage],&result.records);
          logf("Leagues Cup rest: master=%u previous_last=%d round_first=%u round_last=%u gap=%d required=%d split=%d",
               g_lc.ko[stage],previous,result.first,result.day,(int)result.first-previous,LC_REST,result.first!=result.day);
        }
        if (status<0) {
          attempted[stage]=INT_MAX;
          lc_quarantine_rollback((unsigned)stage+1);
        }
        if (status<=0)
          logf("Leagues Cup: knockout registration blocked master=%u day=%d",g_lc.ko[stage],day);
      }
      return;
    }
    lpre_t* l=&g_lpre[lc_lpre_first+LC_BATCHES+stage];
    l->days[0]=l->days[1]=result.first;
    memcpy(lc_replica_days[stage],result.tie_day,sizeof lc_replica_days[stage]);
    previous=result.day;
    if (!(conflicts&(1u<<stage)) && lc_ko_conflict(stage,&result,pairs)) {
      conflicts|=1u<<stage;
      logf("Leagues Cup: late knockout calendar conflict master=%u day=%u",
           g_lc.ko[stage],result.day);
    }
    for (int i=0;i<n;i++) if (!result.won[i]) return;
    if (stage<2) lc_advance_bracket(stage,result.won,result.lost,pairs);
    else if (!published) {
      uint32_t clubs[3];
      lc_knockout verified;
      published=lc_completed_podium(&verified) && lc_keep_podium(&verified,clubs);
      if (published)
        logf("Leagues Cup completion: year=%u played=62/62 phase_one=54 knockout=8 last_day=%u knockout_rest_audit=passed",
             g_lc.year,verified.day);
    }
  }
}

static void lc_trace_group_dates(const char* state, const uint16_t dates[LC_BATCHES][LC_TIES])
{
  for (int b=0;b<LC_BATCHES;b++) {
    const uint16_t* d=dates[b];
    int split=0;
    for (int t=1;t<LC_TIES;t++) split|=d[t]!=d[0];
    logf("Leagues Cup %s group year=%u master=%u split=%d dates=%u/%u/%u/%u/%u/%u/%u/%u/%u",
         state,g_lc.year,g_lc.master[b],split,d[0],d[1],d[2],d[3],d[4],d[5],d[6],d[7],d[8]);
  }
}

static void lc_group_domains_trace(const lc_calendar* calendar, int today, const lc_edition_plan* plan)
{
  int first=today>=g_lc.first ? today+1 : g_lc.first;
  int last=g_lc.last+(LC_GROUP_LAST-LC_AUG_LAST);
  lc_group_search committed={.calendar=calendar};
  if (plan) for (int b=0;b<LC_BATCHES;b++) for (int t=0;t<LC_TIES;t++) {
    int d=plan->fixture[b][t];
    committed.clubs[d]|=lc_group_pair(b,t);
    committed.used[d]++;
  }
  for (int b=0;b<LC_BATCHES;b++) for (int t=0;t<LC_TIES;t++)
    for (int base=first;base<=last;base+=32) {
      uint32_t allowed=0, unknown=0, capacity=0, external=0, rest=0;
      int end=base+31<last ? base+31 : last;
      int match=b*LC_TIES+t, assigned=plan ? plan->fixture[b][t] : 0;
      uint64_t pair=committed.pair[match]=lc_group_pair(b,t);
      if (assigned) { committed.clubs[assigned]^=pair; committed.used[assigned]--; }
      for (int d=base;d<=end;d++) {
        uint32_t bit=UINT32_C(1)<<(d-base);
        unsigned reason=lc_group_candidate(&committed,match,d);
        if (!reason) allowed|=bit;
        if (reason&LC_DATE_UNKNOWN) unknown|=bit;
        if (reason&LC_DATE_CAPACITY) capacity|=bit;
        if (reason&LC_DATE_EXTERNAL) external|=bit;
        if (reason&LC_DATE_REST) rest|=bit;
      }
      if (assigned) { committed.clubs[assigned]|=pair; committed.used[assigned]++; }
      logf("Leagues Cup group domains reg=%u tie=%d assigned=%d first=%d last=%d allowed=%08x unknown=%08x capacity=%08x external=%08x rest=%08x",
           g_lc.master[b],t+1,assigned,base,end,allowed,unknown,capacity,external,rest);
    }
}

static void lc_tick(void* ctx)
{
  if (!g_lc_enabled || g_lc_busy) return;
  int gd=game_date(), day=gd%365, year=gd/365;
  if (gd<0 || year<LC_YEAR || (!g_lc.mexico && year!=LC_YEAR)) return;
  if (ctx) lc_capture_annual(0);
  if (day<LC_FILL) return;
  if (ctx) state_sync();
  static int timeline=-1, edition=-1, attempted, last=-1, last_status=-1;
  static unsigned group_conflicts;
  static lc_results retained;
  static ULONGLONG due;
  if (timeline!=g_timeline || edition!=year) {
    timeline=g_timeline; edition=year; attempted=-1; due=0; last=-1; last_status=-1; group_conflicts=0;
    memset(lc_replica_days,0,sizeof lc_replica_days);
    if (lc_plan_timeline!=g_timeline || g_lc.year!=year) lc_apply_group(lc_preferred,0,0);
  }
  ULONGLONG now=GetTickCount64();
  if (!ctx && last==gd && now<due) return;
  last=gd; due=now+1000;
  if (g_lc.mexico) {
    int occupied=lc_occupied_year();
    if (occupied<0 || occupied>year) return;
    if (occupied && occupied<year) {
      if (!ctx || day+2*LC_REST>=g_lc.last+(LC_GROUP_LAST-LC_AUG_LAST)) return;
      /* A missing annual field must not erase the previous edition. */
      if (!lc_field_for_year(year,gd,0)) {
        if (last_status!=8) logf("Leagues Cup: required annual standings or current membership unavailable for %d",year);
        last_status=8;
        return;
      }
      if (!lc_field_for_year(occupied,gd,1) || !lc_close_edition(ctx)) {
        if (ctx && last_status!=7) logf("Leagues Cup: prior edition could not be verified and closed");
        last_status=7;
        return;
      }
      occupied=0;
    }
    if ((!occupied || g_lc.year!=year || last_status==-1) &&
        !lc_field_for_year(year,gd,occupied!=0)) {
      if (ctx && last_status!=8) logf("Leagues Cup: required annual standings or current membership unavailable for %d",year);
      if (ctx) last_status=8;
      return;
    }
  }
  if (g_lc.year==year) {
    g_lc_confirm_timeline=g_timeline;
    g_lc_confirm_year=year;
  }
  lc_results results;
  lc_records records;
  lc_calendar calendar;
  int valid=lc_scan(&results,&records,&calendar);
  if (!valid) {
    if (last_status!=0) logf("Leagues Cup prototype: invalid fixture or result; tables withheld");
    last_status=0;
    return;
  }
  if (!records.count && ctx && day+2*LC_REST<g_lc.last+(LC_GROUP_LAST-LC_AUG_LAST) && attempted!=day && attempted!=INT_MAX) {
    if (lc_rollback_quarantined(0)) {
      logf("Leagues Cup: group registration quarantined after an unverified rollback");
      attempted=INT_MAX;
      return;
    }
    attempted=day;
    uint32_t handles[LC_CLUBS];
    HMODULE join=GetModuleHandleW(L"fl26join.dll");
    car_close_fn rollback=join ? (car_close_fn)(uintptr_t)GetProcAddress(join,"fl26_join_rollback_leagues") : 0;
    FARPROC stage_rollback=join ? GetProcAddress(join,g_lc.allocated_ids ? "fl26_join_rollback_leagues_stage_ids" : "fl26_join_rollback_leagues_stage") : 0;
    unsigned need_matches, need_slots=lc_ko_space(0,&need_matches);
    if (records.free<LC_MATCHES+need_matches || !lc_fixture_space(LC_BATCHES*(LC_TIES+1)+need_slots) ||
        !rollback || !rollback(ctx,0) || (need_matches && !stage_rollback) ||
        !lc_ready() || !lc_ko_rules_empty(0,LC_KO_STAGES) || !lc_handles(handles)) {
      if (last_status!=1) logf("Leagues Cup prototype: registration blocked by capacity, rules, teams or rollback availability");
      last_status=1;
      return;
    }
    lc_edition_plan plan={0};
    unsigned domains[LC_BATCHES];
    lc_phase window=g_lc;
    if (window.first<=day) window.first=(uint16_t)(day+1);
    int planned=g_lc.ko[0] ? lc_plan_edition(&g_lc,&calendar,day,&plan,domains) :
                             lc_allocate(&window,&calendar,plan.groups,domains);
    if (!planned) {
      if (last_status!=4) {
        logf("Leagues Cup: no complete edition plan; August %u-%u, knockout horizon=%d; group domains: %u %u %u %u %u %u (rest=3, capacity=%u)",
               window.first-211,window.last-211,LC_KO_RECOVERY_LAST,domains[0],domains[1],domains[2],domains[3],domains[4],domains[5],calendar.capacity);
      }
      logf("Leagues Cup group planner failure year=%u today=%d window=%d assignment=%d search_limit=%d knockout=%d",
           g_lc.year,day,!!(plan.group_rejection&LC_GROUP_WINDOW),!!(plan.group_rejection&LC_GROUP_NO_ASSIGNMENT),
           !!(plan.group_rejection&LC_GROUP_SEARCH_LIMIT),!!(plan.group_rejection&LC_GROUP_NO_KNOCKOUT));
      lc_group_domains_trace(&calendar,day,0);
      last_status=4;
      return;
    }
    logf("Leagues Cup plan: year=%u group days in master order=%u/%u/%u/%u/%u/%u knockout=%u/%u/%u alternatives=%u recovery=%d contingency=%d rest=%d processing_buffer=%d",
         g_lc.year,plan.groups[0],plan.groups[1],plan.groups[2],plan.groups[3],plan.groups[4],plan.groups[5],
         plan.knockout[0],plan.knockout[1],plan.knockout[2],plan.alternatives,plan.recovery,plan.contingency,LC_REST,LC_PROCESS_BUFFER);
    if (g_lc.ko[0]) {
      lc_trace_group_dates("plan",plan.fixture);
      lc_group_domains_trace(&calendar,day,&plan);
    }
    g_lc_busy=1;
    lc_apply_group(plan.groups,g_lc.ko[0] ? plan.fixture : 0,0);
    int registered=lc_register_edition(ctx,handles,rollback);
    if (registered<=0) {
      lc_apply_group(lc_preferred,0,0);
      if (registered<0) {
        attempted=INT_MAX;
        lc_quarantine_rollback(0);
      }
    }
    else if (g_lc.mexico && year!=LC_YEAR) {
      final_t* keep=final_of(LC_FIELD_KEY(year));
      if (!keep) keep=final_new(LC_FIELD_KEY(year));
      if (keep) {
        keep->reg=LC_FIELD_KEY(year); keep->day=abs_day(); keep->n=LC_CLUBS;
        memcpy(keep->club,handles,sizeof handles);
        state_store();
      } else logf("Leagues Cup: unable to retain edition roster for reload");
    }
    if (registered>0 && g_lc.ko[0]) {
      lc_plan_store(plan.groups,plan.knockout,0,0);
      logf("Leagues Cup: full edition reserved %u/%u/%u alternatives=%u recovery=%d contingency=%d",
           plan.knockout[0],plan.knockout[1],plan.knockout[2],plan.alternatives,plan.recovery,plan.contingency);
    }
    g_lc_busy=0;
    valid=lc_scan(&results,&records,&calendar);
    if (registered>0 && valid && records.count==LC_MATCHES) {
      lc_trace_registration(0,&records);
      lc_trace_group_dates("registered",results.fixture);
      int external_clear=1;
      for (int b=0;b<LC_BATCHES;b++) for (int t=0;t<LC_TIES;t++)
        external_clear&=!(calendar.group_blocked[results.fixture[b][t]]&lc_group_pair(b,t));
      logf("Leagues Cup rest: Phase One registered=%u cohort_spacing_valid=%d external_calendar_clear=%d required=%d",
           records.count,lc_group_rest(&results),external_clear,LC_REST);
    }
  }
  if (!records.count) return;
  if (!valid || records.count!=LC_MATCHES || !lc_group_rest(&results) || !lc_filed(&records,1)) {
    if (last_status!=2)
      logf("Leagues Cup prototype: incomplete or inconsistent native edition (%u records); stop isolated validation",records.count);
    last_status=2;
    return;
  }
  if (lc_plan_timeline==g_timeline && (!lc_dates_match(results.days) ||
      memcmp(lc_group_days,results.fixture,sizeof lc_group_days))) {
    if (last_status!=6) logf("Leagues Cup prototype: committed dates changed; stop isolated validation");
    last_status=6;
    return;
  }
  lc_apply_group(results.days,results.fixture,1);
  for (int b=0;b<LC_BATCHES;b++) for (int t=0;t<LC_TIES;t++) if (
      calendar.group_blocked[results.fixture[b][t]]&lc_group_pair(b,t)) {
    if (!(group_conflicts&(1u<<b))) {
      group_conflicts|=1u<<b;
      logf("Leagues Cup: late group calendar conflict master=%u tie=%d year=%u day=%u",
           g_lc.master[b],t+1,g_lc.year,results.fixture[b][t]);
    }
    last_status=5;
    if (results.played!=LC_MATCHES) return;
  }
  lc_ko_tick(ctx,day,&results,&calendar,records.free);
  if (last_status==3 && !memcmp(&retained,&results,sizeof results)) return;
  if (last_status!=3) for (int b=0;b<LC_BATCHES;b++) {
    int month=results.days[b]<=LC_AUG_LAST ? 8 : 9;
    logf("Leagues Cup prototype: committed master=%u date=%u-%02d-%02d",
         g_lc.master[b],g_lc.year,month,results.days[b]-MONTH0[month-1]+1);
  }
  retained=results; last_status=3;
  logf("Leagues Cup prototype: 54 validated fixtures, %u played",retained.played);
  for (int i=0;i<LC_CLUBS;i++) {
    const lc_stats* s=&retained.table[i];
    logf("LC table %s club=%u P=%u RW=%u PW=%u PL=%u RL=%u GF=%u GA=%u GD=%d Pts=%u",
         i<LC_SIDE ? "MLS" : "LigaMX",g_lc.clubs[i],s->played,s->regulation_wins,
         s->penalty_wins,s->penalty_losses,s->regulation_losses,s->gf,s->ga,s->gd,s->points);
  }
}
