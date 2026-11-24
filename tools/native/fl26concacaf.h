/* Versioned CONCACAF contract and pure qualification/handover checks.
 * No game pointers: the DLL adapter supplies completed rankings and actual winners. */
#ifndef FL26CONCACAF_H
#define FL26CONCACAF_H
#include <stdint.h>
#include <string.h>
#define CQ_VERSION 1
#define CQ_SOURCES 64
#define CQ_RANKS 40
#define CQ_PLACES 27
#define CQ_PREF 8
#define CQ_JANUARY_FILL 1
#define CQ_CARIBBEAN 2
#define CQ_CENTRAL 3
#define CQ_LEAGUES 4
#define CQ_CENTRAL_PLACES 6
#define CQ_CENTRAL_DRAW 201
#define CQ_CENTRAL_FINAL_DAY 339
#define CQ_CENTRAL_KEEP(reg) ((uint16_t)(0xa000u | (reg)))
typedef struct { uint16_t reg, kind, region, capacity, n; int status;
                 uint32_t club[CQ_RANKS]; uint16_t parent; } cq_source;
typedef struct { uint16_t direct, np, nf, local, source[CQ_PREF], rank[CQ_PREF], fallback[CQ_SOURCES]; } cq_place;
typedef struct { uint16_t ko, pre, fill, days[2], ns, explicit_access;
                 cq_source source[CQ_SOURCES]; cq_place place[CQ_PLACES]; } cq_config;
static int cq_has(const uint32_t* a, int n, uint32_t c)
{
  for (int i = 0; i < n; i++) if ((a[i] >> 14) == (c >> 14)) return 1;
  return 0;
}
static int cq_unique(const uint32_t* a, int n)
{
  for (int i = 0; i < n; i++) if (!(a[i] >> 14) || cq_has(a, i, a[i])) return 0;
  return 1;
}

static int cq_central_year(int edition)
{
  return edition>=365 && edition%365==CQ_JANUARY_FILL ? edition/365-1 : -1;
}

static int cq_central_bootstrap(int creation, int edition)
{
  int year=cq_central_year(edition);
  return year>=0 && creation>=0 && creation<=edition && creation>year*365+CQ_CENTRAL_DRAW;
}

static int cq_central_result(int year, int completed, int today, const uint32_t* clubs, int n)
{
  return year>=1990 && year<=2200 && completed==year*365+CQ_CENTRAL_FINAL_DAY &&
         completed<=today && n==CQ_CENTRAL_PLACES && cq_unique(clubs,n);
}
/* The game stores a 365-day year. An edition starts at its absolute fill date,
 * and days below the fill's day-of-year belong to the following calendar year. */
static int cq_edition_fill(int today, unsigned fill)
{
  if (today < 0 || fill >= 365) return -1;
  int date = today - today%365 + (int)fill;
  return date > today ? date-365 : date;
}

static int cq_edition_day(int edition, unsigned day)
{
  int fill = edition%365;
  return edition-fill+(int)day+(day<(unsigned)fill ? 365 : 0);
}

static int cq_snapshot_valid(const uint32_t* clubs, int n, int saved, int today,
                             int edition, unsigned first_leg)
{
  return n==27 && saved>=edition && saved<=today &&
         saved<cq_edition_day(edition,first_leg) && today<cq_edition_day(edition,182) &&
         cq_unique(clubs,27);
}

static int cq_final_in_edition(int played, int match_date, int expected, int today)
{
  return played && expected>=0 && match_date==expected && match_date<=today;
}

/* Visibility only. The registration and handover guards still expire in July. */
static int cq_completed_view_window(int edition, int today)
{
  return edition >= 0 && today >= edition && today < edition + 365;
}

static int cq_first_edition(int built, int edition)
{
  return built>=0 && built<=edition && built>edition-365;
}

/* The ML initializer stores 1 August for the July-start route, whose
 * calendar actually starts on 1 July. Both dates use a 365-day year. */
static int cq_career_start(uint32_t packed, int today)
{
  unsigned year=packed&0xffffu, month_day=packed>>16;
  if (year<1990 || year>2200 || (month_day!=0x0101 && month_day!=0x0108)) return -1;
  int start=(int)year*365+(month_day==0x0108 ? 181 : 0);
  return start<=today ? start : -1;
}

static int cq_qualification_open(int today, int edition, unsigned first_leg)
{
  return edition>=0 && today>=edition && today<cq_edition_day(edition,first_leg);
}

static int cq_can_register(int today, int edition, unsigned first_leg, int pre, int knockout)
{
  return pre==0 && knockout==0 && cq_qualification_open(today,edition,first_leg);
}

/* Winner relative to the first match's home side: +1 home, -1 away.
 * Zero means the supplied scores leave the tie unresolved. */
static int cq_score_winner(const unsigned char* first, const unsigned char* second)
{
  int diff = first[0] - first[3];
  if (second) {
    diff += second[3] - second[0];
    if (!diff) diff = second[3] - first[3];
    if (!diff) diff = second[4] - second[1];
    if (!diff) diff = second[5] - second[2];
  } else {
    if (!diff) diff = first[1] - first[4];
    if (!diff) diff = first[2] - first[5];
  }
  return (diff > 0) - (diff < 0);
}

static int cq_result_fresh(int completed, int edition, int today)
{
  if (edition%365==CQ_JANUARY_FILL) {
    int january=edition-CQ_JANUARY_FILL;
    return completed>=january-365 && completed<january && completed<=today;
  }
  return completed>edition-365 && completed<=today;
}

/* A July league's first complete season runs through the following spring.
 * A calendar league which starts after February registration waits a year. */
static int cq_source_bootstrap(int built, int edition, int calendar_year)
{
  if (built < 0 || built > edition) return 0;
  int first_finish_year = built / 365 + (!calendar_year || built % 365 > 41);
  return edition / 365 <= first_finish_year;
}

/* By the July draw a spring season can already have finished. A calendar
 * league started before its February registration should have a result
 * from its first calendar year by the following July. */
static int cq_summer_bootstrap(int built, int edition, int calendar_year)
{
  if (built<0 || built>edition) return 0;
  int first_finish_year=built/365+(!calendar_year || built%365>41);
  return edition/365<first_finish_year+(calendar_year!=0);
}

static int cq_match_in_edition(int match, int edition, unsigned first_leg,
                               unsigned second_leg, int today)
{
  if (match>today) return 0;
  if (match==cq_edition_day(edition,first_leg)) return 1;
  return match==cq_edition_day(edition,second_leg) ? 2 : 0;
}
static int cq_view_page(int page, int* first, int* end)
{
  if (page<0 || page>2) return 0;
  *first=page ? 5+(page-1)*11 : 0;
  *end=page ? *first+11 : 5;
  return 1;
}

/* Match ownership varies between master and replica across engine versions.
 * Count by the actual tie's two clubs, once per live match record. */
static int cq_count_match(const uint32_t* clubs, uint32_t a, uint32_t b, int played, unsigned date_leg,
                           int* scheduled, int* unplayed, unsigned* legs, unsigned* dates)
{
  for (int i=0;i<11;i++) if (cq_has(clubs+2*i,2,a) && cq_has(clubs+2*i,2,b)
                            && (a>>14)!=(b>>14)) {
    unsigned leg = cq_has(clubs+2*i,1,a) ? 1u : 2u;
    if (!date_leg || (legs[i] & leg) || (dates[i] & date_leg)) return 0;
    legs[i] |= leg;
    dates[i] |= date_leg;
    scheduled[i]++;
    unplayed[i] += !played;
    return 1;
  }
  return 0;
}
/* Promotion/relegation: retain the completed eligible order, then append new
 * members in domestic entry order. Never qualify a departed/deleted club. */
static int cq_current_ranking(uint32_t* ranked, int n, const uint32_t* current, int nc)
{
  if (n<1 || n>CQ_RANKS || nc<1 || nc>CQ_RANKS || !cq_unique(ranked,n) || !cq_unique(current,nc)) return 0;
  uint32_t out[CQ_RANKS]; int count=0;
  for (int i=0;i<n;i++) if (cq_has(current,nc,ranked[i])) out[count++]=ranked[i];
  for (int i=0;i<nc;i++) if (!cq_has(out,count,current[i])) out[count++]=current[i];
  memcpy(ranked,out,(size_t)count*sizeof(uint32_t)); return count;
}
/* Packed u16: version, ko, pre, fill, d1, d2, ns; source records
 * (reg, kind 0 league/1 cup/2 Caribbean podium, region, capacity);
 * 27 place records (direct,np,nf,local, [zero-based source,rank]*np, [source]*nf). */
static int cq_parse(cq_config* c, const uint16_t* v, int n)
{
  if (!c || !v || n < 7 || (v[0]<CQ_VERSION || v[0]>3)) return 0;
  memset(c, 0, sizeof *c);
  c->explicit_access=v[0]-1;
  c->ko=v[1]; c->pre=v[2]; c->fill=v[3]; c->days[0]=v[4]; c->days[1]=v[5]; c->ns=v[6];
  if (c->ko < 176 || c->ko > 1023 || c->pre < 176 || c->pre > 1023 || c->ko == c->pre
      || c->fill < 1 || c->fill >= 365 || c->days[0] < 1 || c->days[1] > 181
      || c->days[0] >= c->days[1] || !c->ns || c->ns > CQ_SOURCES) return 0;
  int p=7, direct=0, central=-1, leagues=-1;
  unsigned central_places=0, leagues_places=0;
  for (int i=0; i<c->ns; i++) {
    if (n-p < 4+(v[0]==3)) return 0;
    cq_source* s=&c->source[i]; s->reg=v[p++]; s->kind=v[p++]; s->region=v[p++]; s->capacity=v[p++];
    if (v[0]==3) s->parent=v[p++];
    if (!s->reg || s->reg>1023 || s->reg==c->ko || s->reg==c->pre || s->kind>CQ_LEAGUES || s->region>2
        || (s->kind==CQ_CARIBBEAN && (s->region!=2 || s->capacity!=4))
        || s->capacity>CQ_RANKS || (!s->kind && !s->capacity)) return 0;
    if (s->kind==CQ_CENTRAL) {
      if (central>=0 || s->reg<176 || s->region!=1 || s->capacity!=CQ_CENTRAL_PLACES ||
          c->fill!=CQ_JANUARY_FILL) return 0;
      central=i;
    }
    if (s->kind==CQ_LEAGUES) {
      if (leagues>=0 || (c->explicit_access ? s->reg<176 : s->reg!=708) || s->region!=0 || s->capacity!=3 ||
          c->fill!=CQ_JANUARY_FILL) return 0;
      leagues=i;
    }
    for (int j=0; j<i; j++) if (c->source[j].reg==s->reg) return 0;
  }
  if (v[0]==3) for (int i=0;i<c->ns;i++) {
    const cq_source* s=&c->source[i];
    if (s->kind!=1 ? s->parent!=0 :
        (!s->parent || s->parent>c->ns || c->source[s->parent-1].kind ||
         c->source[s->parent-1].region!=s->region)) return 0;
  }
  for (int i=0; i<CQ_PLACES; i++) {
    if (n-p < 4) return 0;
    cq_place* s=&c->place[i]; s->direct=v[p++]; s->np=v[p++]; s->nf=v[p++]; s->local=v[p++];
    if (s->direct>1 || s->np>CQ_PREF || s->nf>CQ_SOURCES || s->local>s->nf || n-p < 2*s->np+s->nf ||
        (c->explicit_access ? (s->np!=1 || s->nf) : !s->nf)) return 0;
    direct+=s->direct;
    for (int j=0; j<s->np; j++) {
      s->source[j]=v[p++]; s->rank[j]=v[p++];
      if (s->source[j]>=c->ns || !s->rank[j] || s->rank[j]>CQ_RANKS) return 0;
      if (v[0]==3) {
        const cq_source* source=&c->source[s->source[j]];
        if (s->rank[j]>(source->kind==1 ? 1 : source->capacity)) return 0;
        for (int k=0;k<i;k++)
          if (c->place[k].source[0]==s->source[j] && c->place[k].rank[0]==s->rank[j]) return 0;
      }
      if (s->source[j]==central) {
        unsigned rank=s->rank[j];
        if (s->np!=1 || rank>CQ_CENTRAL_PLACES || s->direct!=(rank==1) ||
            (central_places & (1u<<(rank-1)))) return 0;
        central_places|=1u<<(rank-1);
      }
      if (s->source[j]==leagues) {
        unsigned rank=s->rank[j];
        if (s->np!=1 || rank>3 || s->direct!=(rank==1) || (leagues_places&(1u<<(rank-1)))) return 0;
        leagues_places|=1u<<(rank-1);
      }
    }
    for (int j=0; j<s->nf; j++) {
      s->fallback[j]=v[p++];
      if (s->fallback[j]>=c->ns || c->source[s->fallback[j]].kind) return 0;
    }
  }
  return p==n && direct==5 && (central<0 || central_places==(1u<<CQ_CENTRAL_PLACES)-1) &&
         (leagues<0 || leagues_places==7);
}

static int cq_reserved(const cq_source* car, const cq_source* ca, const cq_source* lc,
                       const cq_source* source, uint32_t club)
{
  return (car && source!=car && cq_has(car->club,car->n<3 ? car->n : 3,club)) ||
         (ca && source!=ca && cq_has(ca->club,ca->n,club)) ||
         (lc && source!=lc && cq_has(lc->club,lc->n,club));
}

/* Match the Central slots in an already retained five-plus-22 field. */
static int cq_central_snapshot(const cq_config* c, int source, const cq_source* s,
                               const uint32_t* field)
{
  if (!s->n) return 1;  /* first eligible Champions Cup precedes the feeder */
  int n=0;
  for (int pass=1; pass>=0; pass--) for (int i=0;i<CQ_PLACES;i++) {
    const cq_place* p=&c->place[i];
    if (p->direct!=pass) continue;
    if (p->np==1 && p->source[0]==source &&
        (p->rank[0]>s->n || !cq_has(s->club+p->rank[0]-1,1,field[n]))) return 0;
    n++;
  }
  return 1;
}
/* out: five byes first, then 22 Round One entrants. 0 invalid/missing,
 * -1 pending, 1 exact field. No partial output may be installed by the adapter. */
static int cq_resolve(const cq_config* c, uint32_t* out)
{
  int n=0;
  const cq_source* car=0, *ca=0, *lc=0;
  for (int i=0;i<c->ns;i++) {
    if (c->source[i].kind==CQ_CARIBBEAN) car=&c->source[i];
    if (c->source[i].kind==CQ_CENTRAL) ca=&c->source[i];
    if (c->source[i].kind==CQ_LEAGUES) lc=&c->source[i];
  }
  if (c->explicit_access && ((car && car->n<3) || (ca && ca->n<6) || (lc && lc->n<3))) return -1;
  if (ca && ca->n) {
    if (ca->n!=CQ_CENTRAL_PLACES || !cq_unique(ca->club,ca->n)) return 0;
    for (int i=0;i<ca->n;i++) if (cq_reserved(car,0,lc,ca,ca->club[i])) return 0;
  }
  if (lc && lc->n) {
    if (lc->n!=3 || !cq_unique(lc->club,lc->n)) return 0;
    for (int i=0;i<lc->n;i++) if (cq_reserved(car,ca,0,lc,lc->club[i])) return 0;
  }
  if (c->explicit_access==2) {
    const cq_place* order[CQ_PLACES];
    for (int direct=1;direct>=0;direct--) for (int i=0;i<CQ_PLACES;i++)
      if (c->place[i].direct==direct) order[n++]=&c->place[i];
    memset(out,0,CQ_PLACES*sizeof *out);
    for (int pass=0;pass<3;pass++) for (int i=0;i<CQ_PLACES;i++) {
      const cq_place* p=order[i];
      const cq_source* src=&c->source[p->source[0]];
      unsigned rank=p->rank[0]-1;
      if (src->status!=1) return src->status==2 ? -1 : 0;
      if ((pass==0 && src->kind!=1) || (pass==1 && src->kind==1)) {
        uint32_t club=rank<src->n ? src->club[rank] : 0;
        if (club && !cq_has(out,CQ_PLACES,club) && !cq_reserved(car,ca,lc,src,club)) out[i]=club;
      } else if (pass==2 && !out[i]) {
        if (src->kind>=CQ_CARIBBEAN) return 0;
        if (src->kind==1) {
          src=&c->source[src->parent-1];
          if (src->status!=1) return src->status==2 ? -1 : 0;
          rank=0;
        }
        for (;rank<src->n;rank++) {
          uint32_t club=src->club[rank];
          if (club && !cq_has(out,CQ_PLACES,club) && !cq_reserved(car,ca,lc,src,club)) {
            out[i]=club; break;
          }
        }
        if (!out[i]) return 0;
      }
    }
    return cq_unique(out,CQ_PLACES);
  }
  for (int pass=1; pass>=0; pass--) for (int i=0; i<CQ_PLACES; i++) {
    const cq_place* p=&c->place[i]; if (p->direct!=pass) continue;
    uint32_t chosen=0;
    for (int j=0; j<p->np && !chosen; j++) {
      const cq_source* s=&c->source[p->source[j]];
      if (s->status!=1) return s->status==2 ? -1 : 0;
      for (int r=p->rank[j]-1; r<s->n; r++) {
        if (s->kind>=CQ_CARIBBEAN && r>=p->rank[j]) break;
        if (!cq_has(out,n,s->club[r]) && !cq_reserved(car,ca,lc,s,s->club[r])) {
          chosen=s->club[r]; break;
        }
      }
    }
    if (!chosen) {
      /* The Python list puts same-region sources first. Finish that region's
       * ranks before crossing a boundary, matching the reference resolver. */
      int first=0;
      for (int tier=0;tier<2 && !chosen;tier++) {
        int end=tier ? p->nf : p->local;
        for (int j=first;j<end;j++) {
          int status=c->source[p->fallback[j]].status;
          if (status!=1) return status==2 ? -1 : 0;
        }
        for (int r=0;r<CQ_RANKS && !chosen;r++) for (int j=first;j<end;j++) {
          const cq_source* s=&c->source[p->fallback[j]];
          if (r<s->n && !cq_has(out,n,s->club[r]) &&
              !cq_reserved(car,ca,lc,s,s->club[r])) {
            chosen=s->club[r]; break;
          }
        }
        first=end;
      }
    }
    if (!(chosen>>14)) return 0;
    out[n++]=chosen;
  }
  return n==27 && cq_unique(out,27);
}
/* Strict per-tie proof: exactly two scheduled matches, both played, a real
 * winner belonging to that tie. No aggregate/first-leg/seeded guess. */
static int cq_handover(const uint32_t* direct, const uint32_t* clubs,
                       const int* scheduled, const int* unplayed, const uint32_t* winners,
                       uint32_t* out)
{
  if (!cq_unique(direct,5) || !cq_unique(clubs,22)) return 0;
  for (int i=0;i<5;i++) if (cq_has(clubs,22,direct[i])) return 0;
  for (int i=0;i<11;i++) {
    if (scheduled[i]!=2 || unplayed[i]!=0 || !(winners[i]>>14)
        || !cq_has(clubs+2*i,2,winners[i])) return 0;
  }
  /* Five bye/winner ties, then three winner/winner ties. */
  for (int i=0;i<5;i++) { out[2*i]=winners[i]; out[2*i+1]=direct[i]; }
  for (int i=5;i<11;i++) out[i+5]=winners[i];
  return cq_unique(out,16);
}
#endif
