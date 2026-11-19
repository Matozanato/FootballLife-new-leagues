/* Opening round recorded in the FL26 four-team domestic bracket. */
enum { STATE_OPENING_ROUND = 46 };
static const struct state_ids* state_for(unsigned id)
{
  static const uint8_t ranks[]={1,4,2,3};
  for (size_t j=0;j<sizeof states/sizeof states[0];j++) {
    const struct state_ids* s=&states[j];
    if (id!=s->a1 && id!=s->a2 && id!=s->final) continue;
    for (int i=0;i<g_nccup;i++) {
      ccup_t* c=&g_ccup[i];
      if (c->reg==s->final && c->ko==s->final && c->n==4 && !c->groups &&
          c->ereg[0]==s->a1 && c->ereg[1]==s->a1 && c->ereg[2]==s->a1 && c->ereg[3]==s->a1 &&
          !memcmp(c->erank,ranks,sizeof ranks)) return s;
    }
  }
  return NULL;
}
static const unsigned short* state_days(void)
{
  int year=season_year()+(today()<175);
  for (size_t i=0; i<sizeof state_calendar/sizeof state_calendar[0]; ++i)
    if (state_calendar[i].year==year) return state_calendar[i].days;
  /* Beyond the declared years, use the last grade and preserve its weekdays. */
  size_t last=sizeof state_calendar/sizeof state_calendar[0]-1;
  int base_year=state_calendar[last].year;
  if (year>base_year) {
    static int cached_year;
    static unsigned short days[14];
    if (cached_year!=year) {
      for (int i=0;i<14;i++) {
        int d=state_calendar[last].days[i], month=1;
        while (month<12 && d>=MONTH0[month]) ++month;
        int md=d-MONTH0[month-1]+1;
        int shift=(dow(base_year,month,md)-dow(year,month,md)+7)%7;
        if (shift>3) shift-=7;
        int projected=d+shift;
        if (projected<0 || projected>=365 || (i && projected<=days[i-1])) return NULL;
        days[i]=(unsigned short)projected;
      }
      cached_year=year;
    }
    return days;
  }
  return NULL;
}

static void state_fill_days(void)
{
  const unsigned short* d=state_days();
  if (!d) return;
  for (int i=0;i<g_nccup;i++) {
    ccup_t* c=&g_ccup[i];
    const struct state_ids* s=state_for(c->ko);
    if (!s || c->ko!=s->final) continue;
    c->fill=d[10]+1;
    for (int j=0;j<3;j++) c->days[j]=d[11+j];
  }
}
static int state_field(const struct state_ids* state,const uint32_t* clubs,size_t count)
{
  if (!clubs || count!=4) return 0;
  const int ranks[]={1,4,2,3};
  for (int i=0;i<4;i++) {
    const char* how="";
    uint32_t club=cwc_club(state->a1,ranks[i],&how);
    if (!club || !same_club(clubs[i],club) ||
        (strcmp(how,"played matches") && strcmp(how,"live table"))) return 0;
    for (int j=0;j<i;j++) if (same_club(clubs[i],clubs[j])) return 0;
  }
  return 1;
}

static unsigned char* state_single_original;
typedef char (*state_single_fn)(uint64_t,int);
static char state_single_round(uint64_t id,int round)
{
  if (round==STATE_OPENING_ROUND) {
    const struct state_ids* state=state_for((uint16_t)id);
    if (state && state->final==(uint16_t)id) return 1;
  }
  return ((state_single_fn)(uintptr_t)state_single_original)(id,round);
}

static int state_final_ok(uint16_t id,const uint32_t* clubs,size_t count,int check_field)
{
  const struct state_ids* s=state_for(id);
  if (!s || s->final!=id) return 1;
  if (check_field) return state_field(s,clubs,count);
  const unsigned short* d=state_days();
  return d && today()>d[10] && today()<d[11];
}

static int state_dates(uint16_t id,uint64_t reg,vec_t* v,uint64_t* result)
{
  const struct state_ids* s=state_for(id);
  if (!s || id==s->semi) return 0;
  const unsigned short* d=state_days();
  if (!d) return 0;
  state_fill_days();
  int final=id==s->final;
  unsigned donor=final?31:17;
  *result=((date_fn)(uintptr_t)g_tramp_date)((reg & ~(uint64_t)0xffff)|donor,v);
  size_t count=v->b && v->e>=v->b ? (size_t)(v->e-v->b)/sizeof(date_t) : 0;
  date_t* dates=(date_t*)v->b;
  size_t out=0;
  if (!final && count==38) {
    out=id==s->a1?11:14;
    for (size_t i=0;i<out;++i) dates[i].day=d[i];
  } else if (final && count==14) {
    unsigned char* rec=get_rec(id);
    if (rec && rec_count(rec)==4)
      for (size_t i=0;i<count;++i) {
        date_t r=dates[i];
        if (r.round==STATE_OPENING_ROUND && r.kind==0) { r.kind=2; r.day=d[11]; }
        else if (r.round==53 && r.kind<=1) r.day=d[12+r.kind];
        else continue;
        dates[out++]=r;
      }
  } else logf("estadual: regulation %u, unexpected date model (%u records)",id,(unsigned)count);
  if (v->b) v->e=v->b+out*sizeof(date_t);
  return 1;
}
