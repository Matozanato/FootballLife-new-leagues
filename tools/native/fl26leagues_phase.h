#ifndef FL26LEAGUES_PHASE_H
#define FL26LEAGUES_PHASE_H

#include <stdint.h>
#include <string.h>

enum { LC_CLUBS=36, LC_SIDE=18, LC_BATCHES=6, LC_TIES=9, LC_YEAR=2026,
       LC_FILL=211, LC_FILL_END=215 }; /* July 31 through August 3, inclusive. */
static const uint16_t lc_preferred[LC_BATCHES]={217,217,224,224,231,231};
enum { LC_AUG_FIRST=212, LC_AUG_LAST=242, LC_REST=3 };
enum { LC_KO_STAGES=3, LC_KO_LAST=272 }; /* September 30 */
enum { LC_KO_RECOVERY_LAST=303, LC_PROCESS_BUFFER=2 }; /* October 31 */
enum { LC_GROUP_LAST=LC_KO_LAST, LC_GROUP_FIXTURES=LC_BATCHES*LC_TIES };
static const unsigned char lc_ko_ties[LC_KO_STAGES]={4,2,2};

typedef struct {
  uint16_t master[LC_BATCHES];
  uint32_t clubs[LC_CLUBS]; /* stable team IDs, MLS followed by Liga MX */
  uint16_t first, last;
  uint16_t ko[LC_KO_STAGES];
  uint16_t year, mexico, allocated_ids;
} lc_phase;

typedef struct {
  unsigned played, regulation_wins, penalty_wins, penalty_losses, regulation_losses;
  unsigned gf, ga, points;
  int gd;
} lc_stats;

typedef struct {
  unsigned seen[LC_BATCHES], played;
  uint16_t days[LC_BATCHES];
  uint16_t fixture[LC_BATCHES][LC_TIES];
  lc_stats table[LC_CLUBS];
} lc_results;

static int lc_parse(lc_phase* out, const uint32_t* data, int n)
{
  const int basic=3+LC_BATCHES+LC_CLUBS;
  if (!data || (n!=basic && n!=basic+LC_KO_STAGES && n!=basic+LC_KO_STAGES+1) ||
      (data[0]!=1 && (data[0]!=2 || n!=basic+LC_KO_STAGES+1))) return 0;
  lc_phase phase={0};
  phase.year=LC_YEAR;
  phase.allocated_ids=data[0]==2;
  for (int i=0;i<LC_BATCHES;i++) {
    unsigned reg=data[1+i];
    if (reg<176 || reg>1023) return 0;
    for (int j=0;j<i;j++) if (phase.master[j]==reg) return 0;
    phase.master[i]=(uint16_t)reg;
  }
  for (int i=0;i<LC_CLUBS;i++) {
    unsigned club=data[1+LC_BATCHES+i];
    if (!club || club>=0x3ffff) return 0;
    for (int j=0;j<i;j++) if (phase.clubs[j]==club) return 0;
    phase.clubs[i]=club;
  }
  unsigned first=data[basic-2], last=data[basic-1];
  if (first<LC_AUG_FIRST || last>LC_AUG_LAST || first>last) return 0;
  phase.first=(uint16_t)first; phase.last=(uint16_t)last;
  if (n>basic) for (int i=0;i<LC_KO_STAGES;i++) {
    if (data[basic+i]<176 || data[basic+i]>1023 || (!phase.allocated_ids && data[basic+i]!=(unsigned)(706+i))) return 0;
    for (int j=0;j<i;j++) if (phase.ko[j]==data[basic+i]) return 0;
    for (int j=0;j<LC_BATCHES;j++) if (phase.master[j]==data[basic+i]) return 0;
    phase.ko[i]=(uint16_t)data[basic+i];
  }
  if (n==basic+LC_KO_STAGES+1) {
    unsigned mexico=data[n-1];
    if (!mexico || mexico>1023 || mexico==51 || mexico==166 || mexico==167) return 0;
    for (int i=0;i<LC_BATCHES;i++) if (phase.master[i]==mexico) return 0;
    for (int i=0;i<LC_KO_STAGES;i++) if (phase.ko[i]==mexico) return 0;
    phase.mexico=(uint16_t)mexico;
  }
  *out=phase;
  return 1;
}

static void lc_pair(int batch, int tie, unsigned* home, unsigned* away)
{
  int round=batch/2, wave=batch%2;
  unsigned mls=wave*LC_TIES+tie, mx=LC_SIDE+wave*LC_TIES+(tie+round)%LC_TIES;
  int mexico_hosts=(tie+round)%2;
  *home=mexico_hosts ? mx : mls;
  *away=mexico_hosts ? mls : mx;
}

static int lc_batch(const lc_phase* phase, uint16_t reg)
{
  for (int i=0;i<LC_BATCHES;i++)
    if ((reg&1023)==phase->master[i] && (reg>>10)<=LC_TIES) return i;
  return -1;
}

static int lc_ko_stage(const lc_phase* phase, uint16_t reg)
{
  for (int i=0;i<LC_KO_STAGES;i++)
    if (phase->ko[i] && (reg&1023)==phase->ko[i] && (reg>>10)<=lc_ko_ties[i]) return i;
  return -1;
}

static int lc_owns(const lc_phase* phase, uint16_t reg)
{
  return lc_batch(phase,reg)>=0 || lc_ko_stage(phase,reg)>=0;
}

static int lc_hide_category_reg(const lc_phase* phase, uint16_t reg)
{
  return phase->mexico && lc_owns(phase,reg) && reg!=phase->master[0];
}

static int lc_select_field(uint32_t out[LC_CLUBS], const uint32_t* ranks, unsigned ranked,
                           const uint32_t* members, unsigned membership)
{
  if (ranked<LC_SIDE || membership!=LC_SIDE) return 0;
  uint32_t ids[LC_CLUBS];
  for (unsigned i=0;i<LC_CLUBS;i++) {
    ids[i]=(i<LC_SIDE ? ranks[i] : members[i-LC_SIDE])>>14;
    if (!ids[i] || ids[i]==0x3ffff) return 0;
    for (unsigned j=0;j<i;j++) if (ids[j]==ids[i]) return 0;
  }
  memcpy(out,ids,sizeof ids);
  return 1;
}

typedef struct {
  unsigned load[365], capacity;
  unsigned char blocked[LC_BATCHES][365];
  uint64_t knockout_blocked[365];
  uint64_t group_blocked[365];
  unsigned char calendar_unknown[365];
  int group_detail;
} lc_calendar;

#define LC_ALL_CLUBS ((UINT64_C(1)<<LC_CLUBS)-1)

typedef struct {
  uint16_t groups[LC_BATCHES], knockout[LC_KO_STAGES];
  unsigned alternatives;
  int recovery, contingency;
  uint16_t fixture[LC_BATCHES][LC_TIES];
  unsigned group_rejection;
} lc_edition_plan;

static uint64_t lc_club_mask(const lc_phase* phase, uint32_t club)
{
  for (unsigned i=0;club && i<LC_CLUBS;i++)
    if (phase->clubs[i]==club) return UINT64_C(1)<<i;
  return 0;
}

static void lc_block_clubs(uint64_t blocked[365], uint64_t clubs, int day)
{
  if (!clubs) return;
  for (int d=day-LC_REST+1;d<day+LC_REST;d++)
    if (d>=0 && d<365) blocked[d]|=clubs;
}

static void lc_block_knockout(lc_calendar* calendar, uint64_t clubs, int day)
{
  lc_block_clubs(calendar->knockout_blocked,clubs,day);
}

static void lc_block(lc_calendar* calendar, unsigned cohorts, int day)
{
  if (!cohorts || day<LC_AUG_FIRST-LC_REST+1 || day>LC_AUG_LAST+LC_REST-1) return;
  for (int b=0;b<LC_BATCHES;b++) if (cohorts & (1u<<(b%2)))
    for (int d=day-LC_REST+1;d<day+LC_REST;d++) calendar->blocked[b][d]=1;
}

static unsigned lc_cohort(const lc_phase* phase, uint32_t club)
{
  for (int i=0;i<LC_CLUBS;i++) if (phase->clubs[i]==club) return 1u<<(i/LC_TIES%2);
  return 0;
}

static int lc_ordered(const uint16_t days[LC_BATCHES])
{
  for (int b=2;b<LC_BATCHES;b++) if (days[b]<days[b-2]+LC_REST) return 0;
  return 1;
}

typedef struct { uint16_t day[3]; unsigned cost; } lc_sequence;
/* At most C(31,3) ordered triples per cohort. Costs follow Mato's separation
 * of hard exclusions from preference and projected day load. */
static int lc_allocate(const lc_phase* phase, const lc_calendar* calendar,
                       uint16_t out[LC_BATCHES], unsigned domains[LC_BATCHES])
{
  lc_sequence seq[2][4495];
  unsigned count[2]={0}, cost[LC_BATCHES][365]={{0}};
  memset(domains,0,LC_BATCHES*sizeof *domains);
  if (!calendar->capacity || phase->first<LC_AUG_FIRST || phase->last>LC_AUG_LAST ||
      phase->first>phase->last) return 0;
  for (int b=0;b<LC_BATCHES;b++) for (int d=phase->first;d<=phase->last;d++) {
    unsigned load=calendar->load[d];
    if (calendar->blocked[b][d] || calendar->calendar_unknown[d] || load+LC_TIES>calendar->capacity) continue;
    int delta=d-(int)lc_preferred[b];
    cost[b][d]=1+8*(unsigned)(delta<0 ? -delta : delta)+16*load/calendar->capacity;
    domains[b]++;
  }
  for (int c=0;c<2;c++) for (int x=phase->first;x<=phase->last;x++) if (cost[c][x])
    for (int y=x+LC_REST;y<=phase->last;y++) if (cost[c+2][y])
      for (int z=y+LC_REST;z<=phase->last;z++) if (cost[c+4][z])
        seq[c][count[c]++]=(lc_sequence){{x,y,z},cost[c][x]+cost[c+2][y]+cost[c+4][z]};
  unsigned best=UINT32_MAX;
  for (unsigned i=0;i<count[0];i++) for (unsigned j=0;j<count[1];j++) {
    const lc_sequence *a=&seq[0][i], *b=&seq[1][j];
    unsigned score=a->cost+b->cost;
    if (score>best) continue;
    int legal=1;
    for (int x=0;x<3;x++) for (int y=0;y<3;y++) if (a->day[x]==b->day[y]) {
      if (calendar->load[a->day[x]]+2*LC_TIES>calendar->capacity) legal=0;
      score+=16*LC_TIES/calendar->capacity;
    }
    if (!legal || score>best) continue;
    uint16_t candidate[LC_BATCHES]={a->day[0],b->day[0],a->day[1],b->day[1],a->day[2],b->day[2]};
    if (score==best) {
      int k=0;
      while (k<LC_BATCHES && candidate[k]==out[k]) k++;
      if (k==LC_BATCHES || candidate[k]>out[k]) continue;
    }
    memcpy(out,candidate,sizeof candidate);
    best=score;
  }
  return best!=UINT32_MAX;
}

/* The same dates must work for every club in `possible`. Before qualification
 * that is the entire edition field. After quarters, all remaining clubs may
 * play in the final or third-place match, independently of the semifinal result. */
static int lc_knockout_schedule(const lc_calendar* calendar, uint64_t possible,
                                int stage, int first, int last, int gap,
                                uint16_t out[LC_KO_STAGES], int* latest,
                                unsigned* alternatives)
{
  uint16_t earliest[LC_KO_STAGES][366]={{0}};
  *latest=0;
  *alternatives=0;
  if (!possible || !calendar->capacity || stage<0 || stage>=LC_KO_STAGES ||
      first<1 || last>=365 || first>last || gap<LC_REST) return 0;
  for (int s=LC_KO_STAGES-1;s>=stage;s--)
    for (int d=last;d>=first;d--) {
      earliest[s][d]=earliest[s][d+1];
      if ((calendar->knockout_blocked[d]&possible) || calendar->calendar_unknown[d] ||
          calendar->load[d]+lc_ko_ties[s]>calendar->capacity) continue;
      if (s<LC_KO_STAGES-1 && (d+gap>last || !earliest[s+1][d+gap])) continue;
      earliest[s][d]=(uint16_t)d;
      if (s==stage) {
        if (!*latest) *latest=d;
        ++*alternatives;
      }
    }
  int d=first;
  for (int s=stage;s<LC_KO_STAGES;s++) {
    if (d>last || !earliest[s][d]) return 0;
    out[s]=earliest[s][d];
    d=out[s]+gap;
  }
  return 1;
}

enum { LC_DATE_MASKS=256, LC_COVER_BUDGET=30000 };
/* Search for a possible top four per league that hits the blocked clubs of
 * every candidate plan. Only a completed proof of no counterexample is accepted. */
static int lc_uncovered_field(const uint64_t* blocked, unsigned count,
                              uint64_t selected, unsigned* budget)
{
  if (!*budget) return -1;
  --*budget;
  const uint64_t mls=(UINT64_C(1)<<LC_SIDE)-1, mx=LC_ALL_CLUBS^mls;
  uint64_t admissible=LC_ALL_CLUBS^selected, choices=0;
  unsigned fewest=LC_CLUBS+1;
  if (__builtin_popcountll(selected&mls)==4) admissible&=~mls;
  if (__builtin_popcountll(selected&mx)==4) admissible&=~mx;
  for (unsigned i=0;i<count;i++) {
    if (blocked[i]&selected) continue;
    uint64_t options=blocked[i]&admissible;
    unsigned n=(unsigned)__builtin_popcountll(options);
    if (!n) return 0; /* this plan covers every completion of the selected clubs */
    if (n<fewest) { fewest=n; choices=options; }
  }
  if (!choices) return 1;
  while (choices) {
    uint64_t club=choices&(~choices+1);
    int result=lc_uncovered_field(blocked,count,selected|club,budget);
    if (result) return result;
    choices^=club;
  }
  return 0;
}

static unsigned lc_qualification_plans(const lc_calendar* cal, int first, int end, int gap)
{
  uint64_t masks[LC_DATE_MASKS];
  unsigned count=0;
  for (int q=first;q+2*gap<=end;q++) {
    if (cal->calendar_unknown[q] || cal->load[q]+lc_ko_ties[0]>cal->capacity) continue;
    for (int s=q+gap;s+gap<=end;s++) {
      if (cal->calendar_unknown[s] || cal->load[s]+lc_ko_ties[1]>cal->capacity) continue;
      uint64_t qs=cal->knockout_blocked[q]|cal->knockout_blocked[s];
      for (int f=s+gap;f<=end;f++) {
        if (cal->calendar_unknown[f] || cal->load[f]+lc_ko_ties[2]>cal->capacity) continue;
        uint64_t mask=qs|cal->knockout_blocked[f];
        const uint64_t mls=(UINT64_C(1)<<LC_SIDE)-1;
        if (__builtin_popcountll(mask&mls)>LC_SIDE-4 ||
            __builtin_popcountll(mask&(LC_ALL_CLUBS^mls))>LC_SIDE-4) continue;
        unsigned i=0;
        while (i<count && (masks[i]&mask)!=masks[i]) i++;
        if (i<count) continue; /* another plan already serves a superset */
        for (i=0;i<count;)
          if ((masks[i]&mask)==mask) masks[i]=masks[--count];
          else i++;
        if (count<LC_DATE_MASKS) masks[count++]=mask;
      }
    }
  }
  unsigned budget=LC_COVER_BUDGET;
  return count && lc_uncovered_field(masks,count,0,&budget)==0 ? count : 0;
}

/* An outcome-independent certificate. A pair sees at least N free slots,
   so the other N-1 ties can never consume all of its opportunities. */
static int lc_flexible_qualification(const lc_calendar* cal, int first, int last, int gap)
{
  for (int s=0;s<LC_KO_STAGES;s++) {
    unsigned slots[LC_CLUBS][LC_CLUBS]={{0}};
    unsigned missing=s ? LC_CLUBS*(LC_CLUBS-1)/2 : LC_SIDE*LC_SIDE;
    unsigned need=lc_ko_ties[s];
    int d=first;
    for (;d<=last && missing;d++) {
      if (cal->calendar_unknown[d] || cal->load[d]>=cal->capacity) continue;
      unsigned free=cal->capacity-cal->load[d];
      for (unsigned a=0;a<LC_CLUBS;a++)
        for (unsigned b=s ? a+1 : LC_SIDE; b<LC_CLUBS && (s || a<LC_SIDE);b++) {
          if (slots[a][b]>=need ||
              (cal->knockout_blocked[d]&((UINT64_C(1)<<a)|(UINT64_C(1)<<b)))) continue;
          slots[a][b]+=free;
          if (slots[a][b]>=need) missing--;
        }
    }
    if (missing) return 0;
    first=d-1+gap;
  }
  return 1;
}

static int lc_plan_common_edition(const lc_phase* phase, const lc_calendar* calendar,
                           int today, lc_edition_plan* plan,
                           unsigned domains[LC_BATCHES])
{
  memset(plan,0,sizeof *plan);
  memset(domains,0,LC_BATCHES*sizeof *domains);
  const int gap=LC_REST+LC_PROCESS_BUFFER;
  for (int recovery=0;recovery<=1;recovery++) {
    int end=recovery ? LC_KO_RECOVERY_LAST : LC_KO_LAST, latest;
    lc_phase window=*phase;
    if (window.first<=today) window.first=(uint16_t)(today+1);
    if (!lc_knockout_schedule(calendar,LC_ALL_CLUBS,0,window.first+gap,end,gap,
                              plan->knockout,&latest,&plan->alternatives)) continue;
    if (window.last>latest-gap) window.last=(uint16_t)(latest-gap);
    if (!lc_allocate(&window,calendar,plan->groups,domains)) continue;
    int last_group=0;
    for (int i=0;i<LC_BATCHES;i++) if (plan->groups[i]>last_group) last_group=plan->groups[i];
    if (!lc_knockout_schedule(calendar,LC_ALL_CLUBS,0,last_group+gap,end,gap,
                              plan->knockout,&latest,&plan->alternatives)) continue;
    plan->recovery=recovery;
    return 1;
  }
  /* Earlier group completion can only add valid knockout branches. Find the
     earliest feasible cutoff with the same native two-cohort allocator. */
  lc_phase window=*phase;
  if (window.first<=today) window.first=(uint16_t)(today+1);
  if (!lc_allocate(&window,calendar,plan->groups,domains)) return 0;
  int lo=window.first, hi=window.last;
  while (lo<hi) {
    int mid=lo+(hi-lo)/2;
    window.last=(uint16_t)mid;
    uint16_t trial[LC_BATCHES];
    if (lc_allocate(&window,calendar,trial,domains)) {
      memcpy(plan->groups,trial,sizeof trial);
      hi=mid;
    } else lo=mid+1;
  }
  memset(plan->knockout,0,sizeof plan->knockout);
  for (int recovery=0;recovery<=1;recovery++) {
    int end=recovery ? LC_KO_RECOVERY_LAST : LC_KO_LAST;
    plan->alternatives=lc_qualification_plans(calendar,lo+gap,end,gap);
    if (plan->alternatives) {
      plan->contingency=1;
      plan->recovery=recovery;
      return 1;
    }
    if (lc_flexible_qualification(calendar,lo+gap,end,gap)) {
      plan->alternatives=1;
      plan->contingency=2;
      plan->recovery=recovery;
      return 1;
    }
  }
  return 0;
}

static uint64_t lc_group_pair(int batch, int tie)
{
  unsigned home,away;
  lc_pair((unsigned)batch,(unsigned)tie,&home,&away);
  return (UINT64_C(1)<<home)|(UINT64_C(1)<<away);
}

enum { LC_DATE_UNKNOWN=1, LC_DATE_CAPACITY=2, LC_DATE_EXTERNAL=4, LC_DATE_REST=8 };
enum { LC_GROUP_WINDOW=1, LC_GROUP_NO_ASSIGNMENT=2, LC_GROUP_SEARCH_LIMIT=4, LC_GROUP_NO_KNOCKOUT=8 };
static unsigned lc_group_date_reason(const lc_calendar* cal, int batch, int day,
                                     uint64_t clubs, unsigned used)
{
  return (cal->calendar_unknown[day] ? LC_DATE_UNKNOWN : 0) |
         (cal->load[day]+used>=cal->capacity ? LC_DATE_CAPACITY : 0) |
         ((cal->group_detail ? (cal->group_blocked[day]&clubs)!=0 : cal->blocked[batch][day])
          ? LC_DATE_EXTERNAL : 0);
}

typedef struct {
  const lc_calendar* calendar;
  int first,last;
  unsigned budget;
  unsigned used[365];
  uint64_t clubs[365], pair[LC_GROUP_FIXTURES];
  uint16_t day[LC_GROUP_FIXTURES];
} lc_group_search;

static unsigned lc_group_candidate(const lc_group_search* search, int match, int day)
{
  uint64_t clubs=search->pair[match];
  unsigned reason=lc_group_date_reason(search->calendar,match/LC_TIES,day,clubs,search->used[day]);
  for (int offset=-LC_REST+1;offset<LC_REST;offset++)
    if (search->clubs[day+offset]&clubs) reason|=LC_DATE_REST;
  return reason;
}

static int lc_group_assign(lc_group_search* search, int remaining)
{
  if (!remaining) return 1;
  if (!search->budget) return 0;
  search->budget--;
  int chosen=-1, best=366;
  for (int m=0;m<LC_GROUP_FIXTURES;m++) if (!search->day[m]) {
    int count=0;
    for (int d=search->first;d<=search->last && count<best;d++)
      count+=lc_group_candidate(search,m,d)==0;
    if (!count) return 0;
    if (count<best) { best=count; chosen=m; }
  }
  for (int d=search->first;d<=search->last && search->budget;d++) {
    if (lc_group_candidate(search,chosen,d)) continue;
    search->day[chosen]=(uint16_t)d;
    search->used[d]++;
    search->clubs[d]|=search->pair[chosen];
    if (lc_group_assign(search,remaining-1)) return 1;
    search->clubs[d]^=search->pair[chosen];
    search->used[d]--;
    search->day[chosen]=0;
  }
  return 0;
}

static int lc_plan_edition(const lc_phase* phase, const lc_calendar* calendar,
                           int today, lc_edition_plan* plan, unsigned domains[LC_BATCHES])
{
  if (lc_plan_common_edition(phase,calendar,today,plan,domains)) {
    for (int b=0;b<LC_BATCHES;b++) for (int t=0;t<LC_TIES;t++) plan->fixture[b][t]=plan->groups[b];
    return 1;
  }
  int first=today>=phase->first ? today+1 : phase->first;
  int cap=phase->last+(LC_GROUP_LAST-LC_AUG_LAST);
  const int gap=LC_REST+LC_PROCESS_BUFFER;
  for (int recovery=0;recovery<=1;recovery++) {
    int latest;
    lc_edition_plan trial={0};
    int end=recovery ? LC_KO_RECOVERY_LAST : LC_KO_LAST;
    int last=recovery ? cap : phase->last;
    if (lc_knockout_schedule(calendar,LC_ALL_CLUBS,0,first+2*LC_REST+gap,end,gap,
                             trial.knockout,&latest,&trial.alternatives) && last>latest-gap)
      last=latest-gap;
    if (first+2*LC_REST>last) { plan->group_rejection|=LC_GROUP_WINDOW; continue; }
    lc_group_search search={.calendar=calendar,.first=first,.last=last,.budget=2000};
    for (int b=0;b<LC_BATCHES;b++) for (int t=0;t<LC_TIES;t++) search.pair[b*LC_TIES+t]=lc_group_pair(b,t);
    if (!lc_group_assign(&search,LC_GROUP_FIXTURES)) {
      plan->group_rejection|=search.budget ? LC_GROUP_NO_ASSIGNMENT : LC_GROUP_SEARCH_LIMIT;
      continue;
    }
    int final_day=first;
    for (int b=0;b<LC_BATCHES;b++) for (int t=0;t<LC_TIES;t++) {
      uint16_t day=search.day[b*LC_TIES+t];
      trial.fixture[b][t]=day;
      if (day>trial.groups[b]) trial.groups[b]=day;
      if (day>final_day) final_day=day;
    }
    if (!lc_knockout_schedule(calendar,LC_ALL_CLUBS,0,final_day+gap,end,gap,
                              trial.knockout,&latest,&trial.alternatives)) {
      trial.alternatives=lc_qualification_plans(calendar,final_day+gap,end,gap);
      if (trial.alternatives) trial.contingency=1;
      else if (lc_flexible_qualification(calendar,final_day+gap,end,gap)) {
        trial.alternatives=1;
        trial.contingency=2;
      } else { plan->group_rejection|=LC_GROUP_NO_KNOCKOUT; continue; }
    }
    trial.recovery=recovery;
    *plan=trial;
    return 1;
  }
  return 0;
}

static int lc_group_rest(const lc_results* results)
{
  uint64_t clubs[365]={0};
  for (int b=0;b<LC_BATCHES;b++) for (int t=0;t<LC_TIES;t++) {
    int d=results->fixture[b][t];
    uint64_t pair=lc_group_pair(b,t);
    if (d<LC_AUG_FIRST || d>LC_GROUP_LAST) return 0;
    for (int o=-LC_REST+1;o<LC_REST;o++) if (clubs[d+o]&pair) return 0;
    clubs[d]|=pair;
  }
  return 1;
}

static int lc_plan_remaining(const lc_calendar* calendar, int stage, int today,
                             int previous, const uint64_t* clubs,
                             uint16_t out[LC_KO_STAGES], unsigned* alternatives)
{
  int first=today+LC_REST, latest;
  const int gap=LC_REST+LC_PROCESS_BUFFER;
  uint64_t possible=0;
  for (int i=0;i<2*lc_ko_ties[stage];i++) possible|=clubs[i];
  if (first<previous+LC_REST) first=previous+LC_REST;
  memset(out,0,LC_KO_STAGES*sizeof *out);
  for (int end=LC_KO_LAST;end<=LC_KO_RECOVERY_LAST;end+=LC_KO_RECOVERY_LAST-LC_KO_LAST) {
    if (lc_knockout_schedule(calendar,possible,stage,first,end,gap,out,&latest,alternatives))
      return 1;
    if (stage!=0) continue;
    /* Qualified field is known. A date for quarters is safe if every possible
       set of winners has some continuation, even when those dates differ. */
    for (int q=first;q+2*gap<=end;q++) {
      if ((calendar->knockout_blocked[q]&possible) || calendar->calendar_unknown[q] ||
          calendar->load[q]+lc_ko_ties[0]>calendar->capacity) continue;
      int all=1;
      for (unsigned outcome=0;outcome<16 && all;outcome++) {
        uint64_t winners=0;
        uint16_t branch[LC_KO_STAGES]={0};
        unsigned count;
        for (unsigned tie=0;tie<4;tie++) winners|=clubs[2*tie+((outcome>>tie)&1)];
        all=lc_knockout_schedule(calendar,winners,1,q+gap,end,gap,branch,&latest,&count);
      }
      if (all) {
        if (!*alternatives) out[0]=(uint16_t)q;
        ++*alternatives;
      }
    }
    if (*alternatives) return 1;
  }
  return 0;
}

static int lc_flexible_round(const lc_calendar* cal, const uint64_t* clubs, unsigned n,
                             int first, int last, int common, uint16_t out[4])
{
  uint16_t paths[16][4]={{0}};
  unsigned reached=1, full=(1u<<n)-1;
  for (int d=first;d<=last;d++) {
    if (cal->calendar_unknown[d] || cal->load[d]>=cal->capacity) continue;
    unsigned available=0, space=cal->capacity-cal->load[d];
    for (unsigned t=0;t<n;t++)
      if (!(cal->knockout_blocked[d]&(clubs[2*t]|clubs[2*t+1]))) available|=1u<<t;
    if (available==full && space>=n) {
      for (unsigned t=0;t<n;t++) out[t]=(uint16_t)d;
      return d;
    }
    if (common) continue;
    unsigned snapshot=reached;
    for (unsigned mask=0;mask<full;mask++) if (snapshot&(1u<<mask)) {
      unsigned free=available&~mask;
      for (unsigned add=free;add;add=(add-1)&free) {
        unsigned next=mask|add;
        if ((reached&(1u<<next)) || (unsigned)__builtin_popcount(add)>space) continue;
        memcpy(paths[next],paths[mask],sizeof paths[next]);
        for (unsigned t=0;t<n;t++) if (add&(1u<<t)) paths[next][t]=(uint16_t)d;
        reached|=1u<<next;
      }
    }
    if (reached&(1u<<full)) {
      memcpy(out,paths[full],sizeof paths[full]);
      return d;
    }
  }
  return 0;
}

static int lc_flexible_branch(const lc_calendar* cal, int stage, int first,
                              int last, const uint64_t* clubs, uint16_t out[4])
{
  const int gap=LC_REST+LC_PROCESS_BUFFER;
  int attempted=0;
  for (int common=1;common>=0;common--) {
    uint16_t dates[4]={0};
    unsigned n=lc_ko_ties[stage];
    int end=lc_flexible_round(cal,clubs,n,first,last-(LC_KO_STAGES-1-stage)*gap,common,dates);
    if (!end || end==attempted) continue;
    attempted=end;
    int valid=1;
    for (unsigned outcome=0;stage<2 && outcome<(1u<<n) && valid;outcome++) {
      uint64_t won[4], lost[4], next[4];
      uint16_t branch[4];
      for (unsigned t=0;t<n;t++) {
        unsigned side=(outcome>>t)&1;
        won[t]=clubs[2*t+side];
        lost[t]=clubs[2*t+(side^1)];
      }
      if (stage==0) {
        next[0]=won[0]; next[1]=won[3]; next[2]=won[1]; next[3]=won[2];
      } else {
        next[0]=lost[0]; next[1]=lost[1]; next[2]=won[0]; next[3]=won[1];
      }
      valid=lc_flexible_branch(cal,stage+1,end+gap,last,next,branch);
    }
    if (valid) {
      memcpy(out,dates,sizeof dates);
      return 1;
    }
  }
  return 0;
}

static int lc_plan_split(const lc_calendar* cal, int stage, int today, int previous,
                         const uint64_t* clubs, uint16_t dates[4])
{
  int first=(today>previous ? today : previous)+LC_REST;
  if (first>LC_KO_RECOVERY_LAST) return 0;
  return lc_flexible_branch(cal,stage,first,LC_KO_LAST,clubs,dates) ||
         lc_flexible_branch(cal,stage,first,LC_KO_RECOVERY_LAST,clubs,dates);
}

/* Return 0 for invalid data and leave the table unchanged. The native
 * record stores regulation, extra-time and penalty goals for each side. */
static int lc_score(lc_stats* home, lc_stats* away, const unsigned char score[6])
{
  unsigned h=score[0], a=score[3], hp=score[2], ap=score[5];
  if (h==255 || a==255 || hp==255 || ap==255 || score[1] || score[4] ||
      (h==a ? hp==ap : hp || ap)) return 0;
  home->played++; away->played++;
  home->gf+=h; home->ga+=a; home->gd+=(int)h-(int)a;
  away->gf+=a; away->ga+=h; away->gd+=(int)a-(int)h;
  if (h!=a) {
    lc_stats* win=h>a ? home : away, *lose=h>a ? away : home;
    win->regulation_wins++; win->points+=3; lose->regulation_losses++;
  } else {
    lc_stats* win=hp>ap ? home : away, *lose=hp>ap ? away : home;
    win->penalty_wins++; win->points+=2; lose->penalty_losses++; lose->points++;
  }
  return 1;
}

/* Ownership, opponents, date and uniqueness are required even for
 * unplayed fixtures. Rebuild from native records on each audit. */
static int lc_ingest(const lc_phase* phase, lc_results* results, uint16_t reg, int date,
                     unsigned flags, uint32_t home, uint32_t away,
                     const unsigned char score[6])
{
  int batch=lc_batch(phase,reg);
  int day=date-phase->year*365;
  if (batch<0 || day<phase->first || day>phase->last+(LC_GROUP_LAST-LC_AUG_LAST)) return 0;
  for (int tie=0;tie<LC_TIES;tie++) {
    unsigned h,a;
    lc_pair(batch,tie,&h,&a);
    if (phase->clubs[a]==home && phase->clubs[h]==away) {
      unsigned swap=h; h=a; a=swap;
    }
    if (phase->clubs[h]!=home || phase->clubs[a]!=away) continue;
    if (((reg>>10) && (reg>>10)!=tie+1) || (results->seen[batch]&(1u<<tie))) return 0;
    if ((flags&0x40) && !lc_score(&results->table[h],&results->table[a],score)) return 0;
    results->seen[batch]|=1u<<tie;
    results->fixture[batch][tie]=(uint16_t)day;
    if (day>results->days[batch]) results->days[batch]=(uint16_t)day;
    results->played+=(flags&0x40)!=0;
    return 1;
  }
  return 0;
}

/* Rank each association after a complete table. Head-to-head is unavailable
 * within an association since every Phase One match is interleague. */
static int lc_rank_before(const lc_phase* phase, const lc_results* results, unsigned a, unsigned b)
{
  const lc_stats *x=&results->table[a], *y=&results->table[b];
  if (x->points!=y->points) return x->points>y->points;
  if (x->gd!=y->gd) return x->gd>y->gd;
  if (x->gf!=y->gf) return x->gf>y->gf;
  if (x->regulation_wins!=y->regulation_wins) return x->regulation_wins>y->regulation_wins;
  return phase->clubs[a]<phase->clubs[b];
}

static int lc_quarterfinals(const lc_phase* phase, const lc_results* results, uint32_t pairs[8])
{
  if (results->played!=54) return 0;
  uint32_t rank[2][4];
  for (unsigned league=0;league<2;league++) {
    unsigned table[LC_SIDE];
    for (unsigned i=0;i<LC_SIDE;i++) {
      unsigned club=league*LC_SIDE+i;
      if (results->table[club].played!=3) return 0;
      unsigned j=i;
      for (;j && lc_rank_before(phase,results,club,table[j-1]);j--) table[j]=table[j-1];
      table[j]=club;
    }
    for (int i=0;i<4;i++) rank[league][i]=phase->clubs[table[i]];
  }
  for (int i=0;i<4;i++) {
    pairs[2*i]=rank[0][i]; pairs[2*i+1]=rank[1][3-i];
  }
  return 1;
}

static uint32_t lc_knockout_winner(uint32_t home, uint32_t away, const unsigned char score[6])
{
  lc_stats h={0}, a={0};
  if (!home || !away || home==away || !lc_score(&h,&a,score)) return 0;
  return h.points>a.points ? home : away;
}

static void lc_advance_bracket(int stage, const uint32_t* winners,
                               const uint32_t* losers, uint32_t pairs[4])
{
  if (stage==0) {
    pairs[0]=winners[0]; pairs[1]=winners[3];
    pairs[2]=winners[1]; pairs[3]=winners[2];
  } else {
    pairs[0]=losers[0]; pairs[1]=losers[1];   /* Bronze */
    pairs[2]=winners[0]; pairs[3]=winners[1]; /* Final */
  }
}

#endif
