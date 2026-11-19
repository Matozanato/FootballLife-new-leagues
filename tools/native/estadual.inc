/* Included in the candidate DLL after lpre_decided. Configuration is generated
   from the same recipe as the database. Only active world links opt in. */
static const struct state_ids* state_for(unsigned id)
{
  for (size_t j=0; j<sizeof states/sizeof states[0]; ++j) {
    const struct state_ids* s=&states[j];
    if (id!=s->a1 && id!=s->a2 && id!=s->semi && id!=s->final) continue;
    for (int i=0; i<g_nlpre; ++i)
      if (g_lpre[i].reg==s->semi && g_lpre[i].ko==s->final &&
          g_lpre[i].ereg[0]==s->a1 && g_lpre[i].ties==2) return s;
  }
  return NULL;
}

static const unsigned short* state_days(void)
{
  int year=season_year()+(today()<175);
  for (size_t i=0; i<sizeof state_calendar/sizeof state_calendar[0]; ++i)
    if (state_calendar[i].year==year) return state_calendar[i].days;
  return NULL;
}

static void state_fill_days(void)
{
  const unsigned short* d=state_days();
  if (!d) return;
  for (int i=0; i<g_nlpre; ++i) {
    lpre_t* l=&g_lpre[i];
    const struct state_ids* s=state_for(l->reg);
    if (s && s->semi==l->reg) {
      l->fill=d[10]+1;
      l->days[0]=l->days[1]=d[11];
    }
  }
  for (int i=0; i<g_nccup; ++i) {
    ccup_t* c=&g_ccup[i];
    const struct state_ids* s=state_for(c->ko);
    if (s && s->final==c->ko) {
      c->fill=d[11]+1;
      c->days[0]=d[12];
      c->days[1]=d[13];
    }
  }
}

static int state_final_ok(uint16_t id, const uint32_t* clubs, size_t n, int check_pair)
{
  const struct state_ids* s=state_for(id);
  if (!s || id!=s->final) return 1;
  for (int i=0; i<g_nlpre; ++i) {
    lpre_t* l=&g_lpre[i];
    uint32_t w[2];
    if (l->reg!=s->semi || l->ties!=2) continue;
    if (today()<=l->days[0] || !lpre_decided(l,w)) return 0;
    if (!check_pair) return 1;
    return clubs && n==2 &&
      ((same_club(clubs[0],w[0]) && same_club(clubs[1],w[1])) ||
       (same_club(clubs[1],w[0]) && same_club(clubs[0],w[1])));
  }
  return 0;
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
    if (rec && state_final_ok(id,rec_clubs(rec),rec_count(rec),1))
      for (size_t i=0;i<count;++i) {
        date_t r=dates[i];
        if (r.round!=53 || r.kind>1) continue;
        r.day=d[12+r.kind];
        dates[out++]=r;
      }
  } else logf("estadual: regulation %u, unexpected date model (%u records)",id,(unsigned)count);
  if (v->b) v->e=v->b+out*sizeof(date_t);
  return 1;
}
