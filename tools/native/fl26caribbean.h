#ifndef FL26CARIBBEAN_H
#define FL26CARIBBEAN_H

#include "fl26regional_places.h"

#define CAR_FILL 208
#define CAR_GROUP_FIRST 216
#define CAR_SEMI_FIRST 286
#define CAR_GROUP_SNAPSHOT 0xfffcu
#define CAR_PODIUM 0xfffbu
#define CAR_DOMESTIC(reg) ((uint16_t)(0xe000u | (reg)))
#define CAR_SOURCES 16

typedef struct {
  uint16_t reg, membership, quota, title;
} car_source;

typedef struct {
  uint16_t group, ko, n, exact;
  car_source sources[CAR_SOURCES];
  uint16_t places[10];
} car_config;

static int car_parse(car_config* c, const uint16_t* v, int n)
{
  if (!v || n<4 || (v[0]<1 || v[0]>3) || !v[3] || v[3]>CAR_SOURCES || n!=4+4*v[3]+(v[0]==3 ? 10 : 0) ||
      v[1]<176 || v[1]>1023 || v[2]<176 || v[2]>1023 || v[1]==v[2]) return 0;
  memset(c,0,sizeof *c);
  c->group=v[1]; c->ko=v[2]; c->n=v[3];
  c->exact=v[0]-1;
  uint16_t cups[CAR_SOURCES]={0};
  int quota=0;
  for (int i=0;i<c->n;i++) {
    car_source s={v[4+4*i],v[5+4*i],v[6+4*i],v[7+4*i]};
    if (!s.reg || s.reg>1023 || !s.membership || s.membership>1023 ||
        (c->exact==2 ? s.quota!=0 : c->exact ? (!s.quota || s.quota>10 || s.title) : s.quota>2) || s.reg==c->group || s.reg==c->ko ||
        s.title>1023 || s.title==c->group || s.title==c->ko) return 0;
    for (int j=0;j<i;j++) if (c->sources[j].reg==s.reg) return 0;
    c->sources[i]=s;
    quota+=s.quota;
    cups[i]=s.title;
  }
  if (c->exact==2) {
    memcpy(c->places,v+4+4*c->n,sizeof c->places);
    return regional_places_valid(c->places,10,c->n,cups);
  }
  return c->exact ? quota==10 : quota<=8;
}

static void car_pair(unsigned round, unsigned pair, unsigned* home, unsigned* away)
{
  *home=(round+pair)%5;
  *away=(round+5-pair)%5;
}

static int car_take(const cq_source* s, uint32_t field[10], int n)
{
  for (int i=0;i<s->n;i++) if (!cq_has(field,n,s->club[i])) {
    field[n]=s->club[i]; return 1;
  }
  return 0;
}

static int car_select(const car_config* cfg, const cq_source* pools, uint32_t field[10])
{
  int counts[CAR_SOURCES]={0}, n=0;
  for (int i=0;i<cfg->n;i++) while (counts[i]<cfg->sources[i].quota && car_take(&pools[i],field,n)) {
    counts[i]++; n++;
  }
  if (cfg->exact) return n==10 && cq_unique(field,10);
  while (n<10) {
    unsigned tried=0;
    int before=n;
    for (int pass=0;pass<cfg->n && n<10;pass++) {
      int least=-1;
      for (int i=0;i<cfg->n;i++) if (!(tried & (1u<<i)) && (least<0 || counts[i]<counts[least])) least=i;
      tried|=1u<<least;
      if (car_take(&pools[least],field,n)) { counts[least]++; n++; }
    }
    if (n==before) return 0;
  }
  return cq_unique(field,10);
}

static int car_previous_year(int completed, int now)
{
  return completed>=0 && completed/365==now/365-1 && completed%365>=338;
}

static int car_draw_current(int drawn, int today)
{
  return today>=0 && drawn>=0 && drawn<=today && drawn/365==today/365 &&
         drawn%365>=CAR_FILL && drawn%365<CAR_GROUP_FIRST;
}

static int car_can_replace(int today, int drawn, int old_matches,
                           int day_context, int old_complete)
{
  if (today<0 || today%365<CAR_FILL || today%365>=CAR_GROUP_FIRST ||
      car_draw_current(drawn,today)) return 0;
  return !old_matches || (day_context && old_complete && drawn>=0 && drawn/365<today/365);
}

#endif
