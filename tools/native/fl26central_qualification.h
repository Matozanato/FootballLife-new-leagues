#ifndef FL26CENTRAL_QUALIFICATION_H
#define FL26CENTRAL_QUALIFICATION_H

#define CA_ASSOCIATIONS 7
#define CA_PARTS 4
#define CA_FIELD 20
#define CA_SOURCE_WORDS (3+4*CA_PARTS)
static const unsigned ca_quota[]={4,4,3,3,3,2,1};
static const unsigned ca_country[]={112,119,121,116,128,127,108};

typedef struct { uint16_t reg, clubs, legs, tier; } ca_part;
typedef struct { uint16_t membership, calendar, cup; ca_part part[CA_PARTS]; } ca_source;
typedef struct { uint32_t club; unsigned char country, rank; } ca_entry;
typedef struct { uint32_t league[FINAL_MAX], cup; unsigned n; } ca_pool;

/* Cross-year periods are July–June. Calendar-year periods are January–December. */
static int ca_annual_period(int date, int calendar)
{
  if (date<0) return -1;
  return date/365-(!calendar && date%365<181);
}

static int ca_phase_owner(const ca_source* src, uint16_t id)
{
  if (!id) return 0;
  if (id==src->membership || id==src->cup) return 1;
  for (int i=0;i<CA_PARTS;i++) if (src->part[i].reg==id) return 1;
  return 0;
}

static int ca_sources_parse(ca_source out[CA_ASSOCIATIONS], const uint32_t* data)
{
  memset(out,0,sizeof(ca_source)*CA_ASSOCIATIONS);
  for (int i=0;i<CA_ASSOCIATIONS;i++,data+=CA_SOURCE_WORDS) {
    if (data[0]>1023 || data[1]>1 || data[2]>1023) return 0;
    ca_source* src=out+i;
    src->membership=(uint16_t)data[0]; src->calendar=(uint16_t)data[1]; src->cup=(uint16_t)data[2];
    if (!src->membership && src->calendar) return 0;
    if (src->cup && (!src->membership || src->cup==src->membership)) return 0;
    int tiers[4]={0}, tier_clubs=0, last_tier=0;
    for (int p=0;p<CA_PARTS;p++) {
      const uint32_t* v=data+3+4*p;
      if (!v[0]) {
        if (v[1] || v[2] || v[3] || (!p && src->membership)) return 0;
        continue;
      }
      if (!src->membership || (p && !src->part[p-1].reg) || v[0]>0xffff ||
          v[0]==src->cup || v[1]<2 || v[1]>FINAL_MAX || !v[2] || v[2]>7 || v[3]>3) return 0;
      if (v[3]) {
        if (!p || v[3]!=(unsigned)(last_tier+1)) return 0;
        last_tier=(int)v[3];
        tier_clubs+=(int)v[1];
      }
      for (int q=0;q<p;q++) if (src->part[q].reg==v[0]) return 0;
      src->part[p]=(ca_part){(uint16_t)v[0],(uint16_t)v[1],(uint16_t)v[2],(uint16_t)v[3]};
      tiers[v[3]]++;
    }
    if (last_tier && (last_tier<2 || tiers[0]!=1 || src->part[0].clubs!=tier_clubs)) return 0;
    for (int j=0;j<i;j++) {
      if ((src->membership && ca_phase_owner(out+j,src->membership)) ||
          (src->cup && ca_phase_owner(out+j,src->cup))) return 0;
      for (int p=0;p<CA_PARTS && src->part[p].reg;p++)
        if (ca_phase_owner(out+j,src->part[p].reg)) return 0;
    }
  }
  return 1;
}

static int ca_entry_has(const ca_entry* field, int n, uint32_t club)
{
  for (int i=0;i<n;i++) if (same_club(field[i].club,club)) return 1;
  return 0;
}

static int ca_take_rank(const ca_pool* pool, int country, ca_entry* field, int n)
{
  for (unsigned i=0;i<pool->n;i++) if (!ca_entry_has(field,n,pool->league[i])) {
    field[n]=(ca_entry){pool->league[i],(unsigned char)country,(unsigned char)i};
    return 1;
  }
  return 0;
}

/* Cup berths are reserved before league berths. Vacancies go to the least
 * represented eligible association, breaking ties in contract order. */
static int ca_allocate(const ca_pool pools[CA_ASSOCIATIONS], ca_entry field[CA_FIELD])
{
  int count[CA_ASSOCIATIONS]={0}, n=0;
  for (int i=0;i<CA_ASSOCIATIONS;i++) {
    if (pools[i].n>FINAL_MAX || (pools[i].n && !cq_unique(pools[i].league,pools[i].n))) return 0;
    if (pools[i].cup && !ca_entry_has(field,n,pools[i].cup)) {
      unsigned rank=0;
      while (rank<pools[i].n && !same_club(pools[i].league[rank],pools[i].cup)) rank++;
      field[n++]=(ca_entry){pools[i].cup,(unsigned char)i,(unsigned char)rank};
      count[i]++;
    }
  }
  for (int i=0;i<CA_ASSOCIATIONS;i++)
    while (count[i]<(int)ca_quota[i] && ca_take_rank(pools+i,i,field,n)) { count[i]++; n++; }
  while (n<CA_FIELD) {
    int chosen=-1;
    for (int i=0;i<CA_ASSOCIATIONS;i++) {
      if (count[i]>=8 || (chosen>=0 && count[i]>=count[chosen])) continue;
      for (unsigned j=0;j<pools[i].n;j++) if (!ca_entry_has(field,n,pools[i].league[j])) {
        chosen=i; break;
      }
    }
    if (chosen<0 || !ca_take_rank(pools+chosen,chosen,field,n)) return 0;
    count[chosen]++; n++;
  }
  /* Comparable domestic rank first, then fixed association order. */
  for (int i=1;i<CA_FIELD;i++) for (int j=i;j>0;j--) {
    ca_entry a=field[j-1], b=field[j];
    if (a.rank<b.rank || (a.rank==b.rank && (a.country<b.country ||
        (a.country==b.country && (a.club>>14)<(b.club>>14))))) break;
    field[j-1]=b; field[j]=a;
  }
  return 1;
}

static int ca_allocate_explicit(const ca_pool pools[CA_ASSOCIATIONS], const uint16_t* quotas,
                                ca_entry field[CA_FIELD])
{
  int n=0;
  for (int i=0;i<CA_ASSOCIATIONS;i++) {
    if (pools[i].n>FINAL_MAX || (quotas[i] && !cq_unique(pools[i].league,pools[i].n))) return 0;
    for (int k=0;k<quotas[i];k++) {
      if (n==CA_FIELD || !ca_take_rank(pools+i,i,field,n)) return 0;
      n++;
    }
  }
  return n==CA_FIELD;
}

static int ca_place_pots(const ca_entry* field, int i, unsigned used,
                         unsigned char count[4][CA_ASSOCIATIONS], uint32_t* groups)
{
  if (i==CA_FIELD) return 1;
  unsigned country=field[i].country;
  for (int g=0;g<4;g++) {
    unsigned bit=1u<<g;
    if ((used&bit) || count[g][country]>=2) continue;
    count[g][country]++;
    groups[5*g+i/4]=field[i].club;
    if (ca_place_pots(field,i+1,i%4==3 ? 0 : used|bit,count,groups)) return 1;
    count[g][country]--;
  }
  return 0;
}

static int ca_draw_groups(const ca_entry field[CA_FIELD], unsigned edition, uint32_t groups[CA_FIELD])
{
  unsigned char count[4][CA_ASSOCIATIONS]={{0}}, total[CA_ASSOCIATIONS]={0};
  for (int i=0;i<CA_FIELD;i++) {
    if (!(field[i].club>>14) || field[i].country>=CA_ASSOCIATIONS ||
        ca_entry_has(field,i,field[i].club) || ++total[field[i].country]>8) return 0;
  }
  /* Fix the first pot up to a rotation of interchangeable group labels. */
  for (unsigned i=0;i<4;i++) {
    unsigned g=(i+edition)%4;
    groups[5*g]=field[i].club;
    count[g][field[i].country]++;
  }
  return ca_place_pots(field,4,0,count,groups);
}

#endif
