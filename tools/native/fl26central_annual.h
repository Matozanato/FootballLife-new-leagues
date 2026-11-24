/* Strict Central American adapter for the existing retained final-table and
 * cup-winner providers. These keys hold domestic results only. */
#define CA_ANNUAL(i,period) ((uint16_t)(0x9000u+2*(i)+((period)&1)))
#define CA_CUP(i,period) ((uint16_t)(0x9020u+2*(i)+((period)&1)))

static ca_source g_ca_sources[CA_ASSOCIATIONS];
static uint16_t g_ca_access[CA_ASSOCIATIONS];
static uint16_t g_ca_places[CA_FIELD];

typedef struct {
  uint32_t club[FINAL_MAX];
  car_stats stats[FINAL_MAX];
  unsigned char pair[FINAL_MAX][FINAL_MAX];
  int n, matches, latest, invalid;
} ca_annual_part;

static int ca_annual_index(ca_annual_part* p, uint32_t club, unsigned capacity)
{
  if (!club || (club>>14)==0x3ffff) return -1;
  int at=car_index(p->club,p->n,club);
  if (at>=0) return at;
  if ((unsigned)p->n>=capacity) return -1;
  p->club[p->n]=club;
  return p->n++;
}

static void ca_annual_match(ca_annual_part* p, const ca_part* spec, int date,
                            int played, uint32_t home, uint32_t away, int gf, int ga)
{
  if (p->invalid) return;
  if (!played || same_club(home,away) || !(home>>14) || !(away>>14)) {
    p->invalid=1;
    return;
  }
  const int h=ca_annual_index(p,home,spec->clubs), a=ca_annual_index(p,away,spec->clubs);
  if (h<0 || a<0 || p->pair[h][a]+p->pair[a][h]>=spec->legs) {
    p->invalid=1;
    return;
  }
  p->pair[h][a]++;
  p->matches++;
  if (date>p->latest) p->latest=date;
  car_stat(p->stats+h,gf,ga,0);
  car_stat(p->stats+a,ga,gf,1);
}

static int ca_annual_complete(const ca_annual_part* p, const ca_part* spec)
{
  return !p->invalid && p->n==spec->clubs && p->matches==p->n*(p->n-1)*spec->legs/2;
}

/* Non-split phases aggregate by points, goal difference and goals scored,
 * as in the existing annual table provider. Split tiers preserve their
 * top/bottom order. A complete native phase table can supply its order. */
static int ca_annual_rank(const ca_source* src, const ca_annual_part parts[CA_PARTS],
                          const uint32_t native[CA_PARTS][FINAL_MAX], final_t* result)
{
  car_stats sum[FINAL_MAX]={{0}};
  int tier[FINAL_MAX]={0}, place[FINAL_MAX]={0}, order[FINAL_MAX];
  int n=parts[0].n, split=src->part[1].tier!=0;
  const uint32_t* club=parts[0].club;
  result->n=0;
  for (int p=0;p<CA_PARTS && src->part[p].reg;p++) {
    const ca_annual_part* part=parts+p;
    if (!ca_annual_complete(part,src->part+p) || (!split && part->n!=n)) return 0;
    for (int j=0;j<part->n;j++) {
      int i=car_index(club,n,part->club[j]);
      if (i<0) return 0;
      if (src->part[p].tier) {
        if (tier[i]) return 0;
        tier[i]=src->part[p].tier;
      }
      sum[i].pts+=part->stats[j].pts;
      sum[i].gf+=part->stats[j].gf;
      sum[i].ga+=part->stats[j].ga;
      if (native && native[p][0] && (src->part[p].tier || !src->part[1].reg)) {
        int r=car_index(native[p],part->n,club[i]);
        if (r<0) return 0;
        place[i]=r+1;
      }
    }
  }
  for (int i=0;i<n;i++) {
    if (split && !tier[i]) return 0;
    order[i]=i;
    for (int j=i;j>0;j--) {
      int a=order[j-1], b=order[j], cmp=car_compare(sum+b,sum+a);
      if (tier[b]>tier[a] || (tier[b]==tier[a] &&
          ((place[a] && place[b]) ? place[b]>place[a] :
           cmp<0 || (!cmp && (club[b]>>14)>(club[a]>>14))))) break;
      order[j-1]=b; order[j]=a;
    }
  }
  for (int i=0;i<n;i++) result->club[i]=club[order[i]];
  result->n=(uint16_t)n;
  return cq_unique(result->club,n);
}

static void ca_annual_native(const ca_part* spec, const ca_annual_part* part,
                             unsigned carried_games, uint32_t* out)
{
  const unsigned char* table=((table_fn)(uintptr_t)(g_base+TABLE_RVA))(spec->reg);
  if (!table || *(const uint32_t*)(table+0x3c0)!=spec->clubs) return;
  uint32_t clubs[FINAL_MAX];
  for (int i=0;i<spec->clubs;i++) {
    const unsigned char* row=table+i*20;
    clubs[i]=*(const uint32_t*)row;
    unsigned games=(spec->clubs-1)*spec->legs;
    if ((row[0x0f]!=games && row[0x0f]!=games+carried_games) ||
        !cq_has(part->club,part->n,clubs[i])) return;
  }
  if (cq_unique(clubs,spec->clubs)) memcpy(out,clubs,spec->clubs*sizeof *out);
}

/* FL27's regulation loader maps file rule bit 28 to +0x304 bit 9
 * (0x1414f8128 -> 0x1414c9b30). With that rule, stage 54 is bronze.
 * Without it either stage can be the terminal tie, depending on the bracket. */
static const uint32_t* ca_cup_final_slot(uint16_t reg, uint32_t rules, unsigned* stage)
{
  const uint32_t* final=0;
  unsigned last_stage=(rules & (1u<<9)) ? 53 : 54;
  for (unsigned kind=53;kind<=last_stage;kind++) {
    unsigned char* round=ko_round(reg,kind);
    if (ko_slots(round)!=1 || *(const uint16_t*)round!=reg ||
        (*(const uint32_t*)(round+0x204)>>26)!=kind) continue;
    const uint32_t* slot=ko_slot(round,0);
    if ((uint16_t)slot[4]==reg) continue; /* winners advance to another tie */
    if (final) return 0;
    final=slot; *stage=kind;
  }
  return final;
}

static int ca_cup_finish(uint16_t reg, uint32_t rules, uint32_t champion, int gd, int creation)
{
  unsigned stage=0;
  const uint32_t* slot=ca_cup_final_slot(reg,rules,&stage);
  if (!slot || !cq_unique(slot,2) || !cq_has(slot,2,champion)) return -1;
  const uint16_t* ids=(const uint16_t*)(slot+2);
  const unsigned char* first=ko_match(ids[0],reg);
  const unsigned char* second=ids[1]==0xffff ? 0 : ko_match(ids[1],reg);
  if (!first || (ids[1]!=0xffff && (!second || second==first)) ||
      first[6]!=stage || !(first[7]&0x40)) return -1;
  uint32_t h=*(const uint32_t*)(first+0x14), a=*(const uint32_t*)(first+0x18);
  if (same_club(h,a) || !cq_has(slot,2,h) || !cq_has(slot,2,a)) return -1;
  const unsigned char* last=second ? second : first;
  const int from=ko_mdate(first), date=ko_mdate(last);
  if (second && (second[6]!=stage || !(second[7]&0x40) || date<=from ||
      !same_club(*(const uint32_t*)(second+0x14),a) ||
      !same_club(*(const uint32_t*)(second+0x18),h))) return -1;
  if (from<0 || from<creation || date>gd || date<=gd-365) return -1;

  /* Score orientation follows the first leg's host. The live away-goals
   * rule (+0x304 bit 5) only applies to two-legged ties. */
  int result=first[0x1c]-first[0x1f];
  if (second) {
    result+=second[0x1f]-second[0x1c];
    if (!result && (rules & (1u<<5))) result=second[0x1f]-first[0x1f];
  }
  if (!result) result=second ? last[0x20]-last[0x1d] : last[0x1d]-last[0x20];
  if (!result) result=second ? last[0x21]-last[0x1e] : last[0x1e]-last[0x21];
  return result && same_club(champion,result>0 ? h : a) ? date : -1;
}

static int ca_capture_cup(const ca_source* src, int index, int gd, int ad, int creation)
{
  const unsigned char* rec=src->cup ? get_rec(src->cup) : 0;
  if (!rec) return 0;
  uint32_t champion=winner_now(src->cup);
  if (!real_club(champion)) return 0;
  int date=ca_cup_finish(src->cup,*(const uint32_t*)(rec+0x304),champion,gd,creation);
  if (date<0) return 0;
  uint16_t key=CA_CUP(index,ca_annual_period(date,src->calendar));
  cupwin_t* w=cupwin_of(key);
  if (w && w->day>=ad-(gd-date)) return 0;
  if (!w) {
    if (g_ncupwin>=CUPWIN_N) return 0;
    w=&g_cupwin[g_ncupwin++];
  }
  w->reg=key; w->day=ad-(gd-date); w->club=champion;
  return 1;
}

/* Capture on season boundaries and before native teardown. A single walk
 * serves every configured association and both eligible annual periods. */
static void ca_capture_domestic(int force)
{
  if (!g_ca_dynamic) return;
  const int gd=game_date(), day=gd%365;
  if (gd<0 || (!force && day>10 && day<151) || (!force && day>=CA_FIRST && day<334)) return;
  const int creation=concacaf_career_start(gd), ad=abs_day();
  if (creation<0) return;
  state_sync();
  static int last=-1, timeline=-1;
  if (!force && last==gd && timeline==g_timeline) return;
  uint32_t cap;
  const unsigned char* matches=car_matches(&cap);
  if (!matches) return;
  last=gd; timeline=g_timeline;
  typedef struct { int current, pending[2]; ca_annual_part parts[2][CA_PARTS]; } annual_source;
  static annual_source scan[CA_ASSOCIATIONS];
  static unsigned char by_reg[65536];
  memset(scan,0,sizeof scan);
  memset(by_reg,0,sizeof by_reg);
  int changed=0, pending=0;
  for (int i=0;i<CA_ASSOCIATIONS;i++) {
    const ca_source* src=g_ca_sources+i;
    if (!src->membership) continue;
    if (!force && (src->calendar ? day>10 && day<334 && day<CA_DRAW
                                : day<151 || day>=CA_FIRST)) continue;
    changed|=ca_capture_cup(src,i,gd,ad,creation);
    annual_source* src_scan=scan+i;
    src_scan->current=ca_annual_period(gd,src->calendar);
    for (int b=0;b<2;b++) {
      int period=src_scan->current-b;
      final_t* f=final_of(CA_ANNUAL(i,period));
      src_scan->pending[b]=(force || b || (src->calendar ? day>=334 : day>=151 && day<181)) &&
                           (!f || ca_annual_period(gd-(ad-f->day),src->calendar)!=period);
      pending|=src_scan->pending[b];
    }
    if (src_scan->pending[0] || src_scan->pending[1])
      for (int p=0;p<CA_PARTS && src->part[p].reg;p++)
        by_reg[src->part[p].reg]=(unsigned char)(1+i*CA_PARTS+p);
  }
  for (uint32_t i=0;pending && i<cap;i++) {
    const unsigned char* m=matches+(size_t)i*MATCH_STRIDE;
    if (*(const uint16_t*)m==0xffff) continue;
    int index=by_reg[*(const uint16_t*)(m+4)]-1;
    if (index<0) continue;
    const int s=index/CA_PARTS, p=index%CA_PARTS, date=ko_mdate(m);
    const ca_source* src=g_ca_sources+s;
    int bucket=scan[s].current-ca_annual_period(date,src->calendar);
    if (date<0) {
      for (int q=0;q<2;q++) scan[s].parts[q][p].invalid=1;
    } else if (bucket>=0 && bucket<2 && scan[s].pending[bucket]) {
      ca_annual_match(&scan[s].parts[bucket][p],src->part+p,date,
                      (m[7]&0x40) && date>=creation && date<=gd,
                      *(const uint32_t*)(m+0x14),*(const uint32_t*)(m+0x18),m[0x1c],m[0x1f]);
    }
  }
  for (int i=0;i<CA_ASSOCIATIONS;i++) for (int b=0;b<2;b++) if (scan[i].pending[b]) {
    const ca_source* src=g_ca_sources+i;
    ca_annual_part* parts=scan[i].parts[b];
    uint32_t native[CA_PARTS][FINAL_MAX]={{0}};
    int latest=-1, complete=1;
    for (int p=0;p<CA_PARTS && src->part[p].reg;p++) {
      if (!ca_annual_complete(parts+p,src->part+p)) { complete=0; break; }
      if (parts[p].latest>latest) latest=parts[p].latest;
      /* Only read a native table when it belongs to the phase's live season. */
      if (!b && (!src->part[1].reg || src->part[p].tier))
        ca_annual_native(src->part+p,parts+p,
                         p ? (src->part[0].clubs-1)*src->part[0].legs : 0,native[p]);
    }
    final_t result;
    if (!complete || !ca_annual_rank(src,parts,native,&result)) continue;
    uint16_t key=CA_ANNUAL(i,scan[i].current-b);
    final_t* f=final_of(key);
    if (!f) f=final_new(key);
    if (!f) continue;
    result.reg=key; result.day=ad-(gd-latest); *f=result; changed=1;
    logf("Central American Cup: retained complete annual standings for association %d, period %d, %u clubs",
         i+1,scan[i].current-b,result.n);
  }
  if (changed) state_store();
}

static final_t* ca_annual_result(int index, int gd, int ad, int creation, int cutoff)
{
  const ca_source* src=g_ca_sources+index;
  int current=ca_annual_period(cutoff,src->calendar);
  for (int p=current;p>=current-1;p--) {
    final_t* f=final_of(CA_ANNUAL(index,p));
    int date=f ? gd-(ad-f->day) : -1;
    if (f && date>=creation && date<=cutoff && ca_annual_period(date,src->calendar)==p) return f;
  }
  return 0;
}

static int ca_filter_ranking(ca_pool* pool, const uint32_t* ranked, unsigned n,
                             const uint32_t* current, unsigned nc)
{
  if (n>FINAL_MAX || nc>FINAL_MAX || !cq_unique(ranked,n) || !cq_unique(current,nc)) return 0;
  for (unsigned i=0;i<n;i++) {
    int j=car_index(current,nc,ranked[i]);
    if (j>=0) pool->league[pool->n++]=current[j];
  }
  return 1;
}

static int ca_domestic_draw(int gd, int year, uint32_t groups[CA_FIELD])
{
  ca_capture_domestic(0);
  int creation=concacaf_career_start(gd), ad=abs_day(), draw=year*365+CA_DRAW;
  if (creation<0 || creation>draw || ad<0) return 0;
  ca_pool pools[CA_ASSOCIATIONS]={{0}};
  const final_t* rankings[CA_ASSOCIATIONS]={0};
  int completion[CA_ASSOCIATIONS]={0};
  for (int i=0;i<CA_ASSOCIATIONS;i++) {
    const ca_source* src=g_ca_sources+i;
    if (!src->membership) continue;
    unsigned char* rec=get_rec(src->membership);
    unsigned n=rec ? rec_count(rec) : 0;
    uint32_t current[FINAL_MAX];
    if (!n || n>FINAL_MAX) return 0;
    for (unsigned j=0;j<n;j++) current[j]=canon_club(rec_clubs(rec)[j]);
    if (!cq_unique(current,n)) return 0;
    final_t* annual=ca_annual_result(i,gd,ad,creation,draw);
    rankings[i]=annual;
    if (annual) {
      if (g_ca_dynamic==4) {
        pools[i].n=annual->n;
        for (unsigned j=0;j<annual->n;j++)
          if (car_index(current,n,annual->club[j])>=0) pools[i].league[j]=annual->club[j];
      } else if (!ca_filter_ranking(pools+i,annual->club,annual->n,current,n)) return 0;
      completion[i]=gd-(ad-annual->day);
    } else if (cq_summer_bootstrap(creation,draw,src->calendar)) {
      memcpy(pools[i].league,current,n*sizeof *current);
      pools[i].n=n;
      logf("Central American Cup: first-career entry order for association %d",i+1);
    } else {
      logf("Central American Cup: expected complete annual result missing or incomplete for association %d",i+1);
      return 0;
    }
    if (src->cup) {
      int found=0, period=ca_annual_period(draw,src->calendar);
      for (int p=period;p>=period-1;p--) {
        cupwin_t* w=cupwin_of(CA_CUP(i,p));
        int date=w ? gd-(ad-w->day) : -1;
        if (!w || date<creation || date>draw || ca_annual_period(date,src->calendar)!=p ||
            (annual && p<ca_annual_period(gd-(ad-annual->day),src->calendar))) continue;
        found=1;
        uint32_t club=canon_club(w->club);
        unsigned char* owner=((owner_fn)(uintptr_t)(g_base+OWNER_RVA))();
        void* block=owner ? *(void**)(owner+0x48) : 0;
        if (!real_club(club) || (g_ca_dynamic!=4 && team_country(block,club)!=(int)ca_country[i])) {
          logf("Central American Cup: national cup winner does not belong to association %d",i+1);
          return 0;
        }
        pools[i].cup=club;
        break;
      }
      if (!found && !cq_summer_bootstrap(creation,draw,src->calendar)) {
        logf("Central American Cup: no eligible verified national cup winner for association %d",i+1);
        return 0;
      }
    }
  }
  ca_entry field[CA_FIELD];
  int allocated;
  if (g_ca_dynamic==4) {
    const uint32_t* tables[CA_ASSOCIATIONS];
    unsigned sizes[CA_ASSOCIATIONS];
    uint32_t cups[CA_ASSOCIATIONS], clubs[CA_FIELD];
    for (unsigned i=0;i<CA_ASSOCIATIONS;i++) {
      tables[i]=pools[i].league; sizes[i]=pools[i].n; cups[i]=pools[i].cup;
    }
    allocated=regional_select(g_ca_places,CA_FIELD,tables,sizes,cups,clubs);
    if (allocated) for (unsigned i=0;i<CA_FIELD;i++) {
      unsigned source=g_ca_places[i]/REGIONAL_RANK_STRIDE;
      int rank=car_index(tables[source],sizes[source],clubs[i]);
      field[i]=(ca_entry){clubs[i],(unsigned char)source,(unsigned char)(rank<0 ? 0 : rank)};
    }
  } else allocated=g_ca_dynamic==3 ? ca_allocate_explicit(pools,g_ca_access,field) : ca_allocate(pools,field);
  if (!allocated) {
    logf("Central American Cup: configured access cannot supply 20 unique eligible clubs");
    return 0;
  }
  if (g_ca_dynamic>=3) {
    for (int i=0;i<CA_FIELD;i++) for (int j=i;j>0;j--) {
      ca_entry a=field[j-1], b=field[j];
      if (a.rank<b.rank || (a.rank==b.rank && a.country<b.country)) break;
      field[j]=a; field[j-1]=b;
    }
    if (!ca_draw_groups(field,year,groups))
      for (int i=0;i<CA_FIELD;i++) groups[5*((i+year)%4)+i/4]=field[i].club;
  } else if (!ca_draw_groups(field,year,groups)) {
    logf("Central American Cup: infeasible five-pot draw with at most two clubs per association per group");
    return 0;
  }
  logf("CA qualification begin edition=%d creation=%d:%03d cutoff=%d:%03d",
       year,creation/365,creation%365,draw/365,draw%365);
  for (int i=0;i<CA_ASSOCIATIONS;i++) if (g_ca_sources[i].membership) {
    const final_t* annual=rankings[i];
    const uint32_t* clubs=annual ? annual->club : pools[i].league;
    unsigned n=annual ? annual->n : pools[i].n;
    for (unsigned r=0;r<n;r++)
      logf("CA ranking association=%u period=%d completed=%d:%03d rank=%u club=%u basis=%s",
           g_ca_dynamic>=3 ? g_ca_sources[i].membership : ca_country[i],annual ? ca_annual_period(completion[i],g_ca_sources[i].calendar) : 0,
           completion[i]/365,completion[i]%365,r+1,clubs[r]>>14,annual ? "annual" : "bootstrap");
  }
  unsigned used[CA_ASSOCIATIONS]={0};
  for (int c=0;c<CA_ASSOCIATIONS;c++) used[c]=pools[c].cup!=0;
  for (int i=0;i<CA_FIELD;i++) {
    const ca_entry* e=field+i;
    int c=e->country, cup=pools[c].cup && same_club(pools[c].cup,e->club);
    const final_t* annual=rankings[c];
    int rank=annual ? car_index(annual->club,annual->n,e->club)+1 :
                      car_index(pools[c].league,pools[c].n,e->club)+1;
    int redistributed=g_ca_dynamic!=4 && !cup && ++used[c]>(g_ca_dynamic==3 ? g_ca_access[c] : ca_quota[c]);
    logf("CA entrant club=%u association=%u rank=%d pot=%d basis=%s place=%s",
         e->club>>14,g_ca_dynamic>=3 ? g_ca_sources[c].membership : ca_country[c],
         rank,i/4+1,cup ? "cup" : annual ? "annual" : "bootstrap",
         redistributed ? "redistributed" : "quota");
  }
  for (int p=0;p<5;p++)
    logf("Central American Cup: pot %d %u %u %u %u",p+1,field[4*p].club>>14,
         field[4*p+1].club>>14,field[4*p+2].club>>14,field[4*p+3].club>>14);
  for (int g=0;g<4;g++)
    logf("Central American Cup: group %c %u %u %u %u %u", 'A'+g, groups[g*5]>>14,
         groups[g*5+1]>>14,groups[g*5+2]>>14,groups[g*5+3]>>14,groups[g*5+4]>>14);
  logf("CA qualification end edition=%d",year);
  return 1;
}
