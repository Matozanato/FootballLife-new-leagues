#include <assert.h>
#include <stdio.h>
#include "fl26concacaf.h"
#include "fl26caribbean.h"

#define CLUB(i) ((uint32_t)(i)<<14)

int main(void)
{
  car_config config;
  uint16_t contract[]={1,400,401,3,20,20,2,0,21,21,1,0,22,23,1,0};
  assert(car_parse(&config,contract,sizeof contract/sizeof *contract));
  assert(!car_parse(&config,contract,8));
  assert(car_parse(&config,contract,sizeof contract/sizeof *contract));
  cq_source pools[5]={{0}};
  for (int i=0;i<3;i++) {
    pools[i].n=5;
    for (int j=0;j<5;j++) pools[i].club[j]=CLUB(1+5*i+j);
  }
  pools[1].club[0]=CLUB(1);
  uint32_t field[10];
  assert(car_select(&config,pools,field));
  assert(field[0]==CLUB(1) && field[1]==CLUB(2) && field[2]==CLUB(7));
  pools[0].n=pools[1].n=pools[2].n=3;
  assert(!car_select(&config,pools,field));
  uint16_t exact[]={2,400,401,2,20,20,6,0,21,21,4,0};
  assert(car_parse(&config,exact,sizeof exact/sizeof *exact));
  for (int i=0;i<2;i++) {
    pools[i].n=8;
    for (int j=0;j<8;j++) pools[i].club[j]=CLUB(1+10*i+j);
  }
  assert(car_select(&config,pools,field) && field[5]==CLUB(6) && field[6]==CLUB(11));
  pools[0].n=5;
  assert(!car_select(&config,pools,field)); /* Jamaica cannot absorb Haiti's missing allocation. */
  exact[6]=5;
  assert(!car_parse(&config,exact,sizeof exact/sizeof *exact));
  uint16_t individual[]={3,400,401,2,20,20,0,22,21,21,0,0,
                         0,2,4,6,64+1,64+2,64+3,64+4,64+5,64+6};
  assert(car_parse(&config,individual,sizeof individual/sizeof *individual));
  const uint32_t* tables[]={pools[0].club,pools[1].club};
  unsigned sizes[]={8,8};
  uint32_t titles[]={0,0};
  assert(regional_select(config.places,10,tables,sizes,titles,field));
  assert(field[0]==CLUB(1) && field[1]==CLUB(2) && field[2]==CLUB(4) && field[3]==CLUB(6));
  titles[0]=CLUB(4);
  assert(regional_select(config.places,10,tables,sizes,titles,field) && field[0]==CLUB(1));
  titles[0]=CLUB(8);
  assert(regional_select(config.places,10,tables,sizes,titles,field) && field[0]==CLUB(8));
  individual[13]=41;
  assert(!car_parse(&config,individual,sizeof individual/sizeof *individual));
  individual[13]=0;
  assert(!car_parse(&config,individual,sizeof individual/sizeof *individual));
  unsigned links[5][5]={{0}}, home[5]={0}, away[5]={0};
  for (unsigned day=0;day<5;day++) {
    unsigned seen=0;
    for (unsigned pair=1;pair<=2;pair++) {
      unsigned h,a;
      car_pair(day,pair,&h,&a);
      assert(h<5 && a<5 && h!=a);
      assert(!(seen & ((1u<<h)|(1u<<a))));
      seen|=(1u<<h)|(1u<<a);
      assert(!links[h][a]++ && !links[a][h]++);
      home[h]++; away[a]++;
    }
    assert(seen==(31u^(1u<<day)));
  }
  for (int i=0;i<5;i++) assert(home[i]==2 && away[i]==2);
  assert(car_previous_year(2026*365+338,2027*365+1));
  assert(!car_previous_year(2026*365+334,2027*365+1));
  assert(!car_previous_year(2025*365+338,2027*365+1));
  int draw=2028*365+CAR_FILL, next=draw+365;
  assert(car_draw_current(draw,draw+150));
  assert(!car_draw_current(draw,next));
  assert(car_can_replace(next,draw,28,1,1));
  assert(!car_can_replace(next,draw,28,0,1));
  assert(!car_can_replace(next,draw,28,1,0));
  assert(!car_can_replace(next,next,28,1,1));
  assert(!car_can_replace(next-1,draw,28,1,1));
  assert(!car_can_replace(next+8,draw,28,1,1));
  assert(car_can_replace(next,-1,0,0,0));
  puts("Caribbean contract, redistribution, balanced groups and January freshness passed");
}
