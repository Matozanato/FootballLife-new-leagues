#include <assert.h>
#include <stdio.h>
#include "fl26concacaf.h"
#define CLUB(n) ((uint32_t)(n)<<14)
int main(int argc, char** argv)
{
  /* Bytes are home regulation/ET/penalties, then away regulation/ET/penalties. */
  const unsigned char first[]={2,0,0,1,0,0};
  const unsigned char races[][6]={
    {0,0,0,0,0,0}, /* aggregate win */
    {3,0,0,2,0,0}, /* equal aggregate, first-leg home advances on away goals */
    {2,0,0,1,0,0}, /* extra time required */
    {2,0,0,1,1,0}, /* first-leg home wins in extra time */
    {2,1,0,1,1,0}, /* equal extra-time goals require penalties */
    {2,1,5,1,1,4}, /* second-leg home wins shootout despite extra-time away goal */
  };
  const int outcomes[]={1,1,0,1,0,-1};
  for (unsigned i=0;i<sizeof outcomes/sizeof *outcomes;i++)
    assert(cq_score_winner(first,races[i])==outcomes[i]);
  assert(cq_score_winner(first,(const unsigned char[]){3,2,5,2,0,4})==1);
  assert(cq_score_winner(first,(const unsigned char[]){2,1,0,1,0,0})==-1);
  assert(cq_score_winner((const unsigned char[]){1,0,0,1,0,0},NULL)==0);
  assert(cq_score_winner((const unsigned char[]){1,0,0,1,1,0},NULL)==-1);
  assert(cq_score_winner((const unsigned char[]){1,1,5,1,1,4},NULL)==1);
  uint32_t direct[5], clubs[22], win[11], out[27]; int matches[11], left[11];
  for (int i=0;i<5;i++) direct[i]=CLUB(i+1);
  for (int i=0;i<22;i++) clubs[i]=CLUB(i+6);
  for (int i=0;i<11;i++) { win[i]=clubs[2*i+1]; matches[i]=2; left[i]=0; }
  assert(cq_handover(direct,clubs,matches,left,win,out));
  int counted[11]={0}, pending[11]={0};
  unsigned legs[11]={0}, dates[11]={0};
  for (int i=0;i<11;i++) {
    assert(cq_count_match(clubs,clubs[2*i],clubs[2*i+1],1,1,counted,pending,legs,dates));
    assert(!cq_count_match(clubs,clubs[2*i],clubs[2*i+1],1,1,counted,pending,legs,dates));
    assert(!cq_count_match(clubs,clubs[2*i+1],clubs[2*i],0,1,counted,pending,legs,dates));
    assert(cq_count_match(clubs,clubs[2*i+1],clubs[2*i],0,2,counted,pending,legs,dates));
    assert(counted[i]==2 && pending[i]==1);
  }
  assert(!cq_handover(direct,clubs,counted,pending,win,out));
  assert(!cq_count_match(clubs,CLUB(100),CLUB(101),1,1,counted,pending,legs,dates));
  for (int i=0;i<11;i++) {
    left[i]=1; assert(!cq_handover(direct,clubs,matches,left,win,out)); left[i]=0;
    matches[i]=1; assert(!cq_handover(direct,clubs,matches,left,win,out)); matches[i]=2;
    uint32_t w=win[i]; win[i]=0; assert(!cq_handover(direct,clubs,matches,left,win,out));
    win[i]=CLUB(100); assert(!cq_handover(direct,clubs,matches,left,win,out)); win[i]=w;
  }
  direct[0]=clubs[0]; assert(!cq_handover(direct,clubs,matches,left,win,out)); direct[0]=CLUB(1);
  for (int i=0;i<27;i++) out[i]=CLUB(i+1);
  assert(cq_edition_fill(0,243)==-122); /* January 2026 has no eligible fill. */
  assert(!cq_first_edition(0,-122));
  int edition=cq_edition_fill(245,243);
  assert(edition==243 && cq_first_edition(0,edition));
  assert(cq_first_edition(216,edition));
  assert(!cq_first_edition(244,edition));
  assert(cq_edition_fill(364,243)==edition);
  assert(cq_edition_fill(365,243)==edition);
  assert(cq_edition_day(edition,33)==398 && cq_edition_day(edition,40)==405);
  assert(cq_snapshot_valid(out,27,243,405,edition,33));
  assert(!cq_snapshot_valid(out,27,1,245,edition,33)); /* obsolete January snapshot */
  assert(!cq_snapshot_valid(out,27,243,240,edition,33)); /* before qualification */
  assert(!cq_snapshot_valid(out,26,243,405,edition,33));
  assert(cq_snapshot_valid(out,27,243,546,edition,33));
  assert(!cq_snapshot_valid(out,27,243,547,edition,33)); /* July reset */
  int next=cq_edition_fill(610,243);
  assert(next==608 && !cq_first_edition(0,next));
  assert(!cq_snapshot_valid(out,27,243,610,next,33));
  assert(!cq_result_fresh(243,next,610)); /* cannot reuse prior-edition evidence */
  assert(cq_result_fresh(350,next,610)); /* completed in December of the previous year */
  assert(cq_result_fresh(580,next,610));
  assert(!cq_result_fresh(611,next,610));
  assert(!cq_match_in_edition(33,edition,33,40,405));
  assert(!cq_match_in_edition(40,edition,33,40,405));
  assert(!cq_match_in_edition(405,edition,33,40,404)); /* future second leg */
  assert(cq_match_in_edition(398,edition,33,40,405)==1);
  assert(cq_match_in_edition(405,edition,33,40,405)==2);
  assert(!cq_match_in_edition(405,next,33,40,770));
  const int jan26=2026*365, jan27=jan26+365, jan28=jan27+365, jan29=jan28+365;
  const int first26=jan26+CQ_JANUARY_FILL, first27=jan27+CQ_JANUARY_FILL;
  assert(cq_edition_fill(jan26,CQ_JANUARY_FILL)==first26-365);
  assert(cq_edition_fill(first26,CQ_JANUARY_FILL)==first26);
  assert(cq_first_edition(jan26,first26));
  assert(!cq_first_edition(jan26,first27));
  assert(cq_first_edition(jan26+181,first27)); /* a July start waits for the next January */
  assert(!cq_first_edition(jan26+181,jan28+CQ_JANUARY_FILL));
  assert(cq_source_bootstrap(jan26,first26,1));
  assert(!cq_source_bootstrap(jan26,first27,1)); /* 2026 calendar results expected */
  assert(cq_source_bootstrap(jan26,first27,0)); /* first August league ends in May 2027 */
  assert(cq_source_bootstrap(jan26+181,first27,0));
  assert(cq_source_bootstrap(jan26+181,first27,1)); /* missed February registration */
  assert(!cq_source_bootstrap(jan26,jan28+CQ_JANUARY_FILL,0));
  assert(!cq_source_bootstrap(jan26+181,jan28+CQ_JANUARY_FILL,1));
  assert(cq_career_start(0x010107eau,2029*365+196)==jan26);
  assert(cq_career_start(0x010807eau,jan26+181)==jan26+181);
  assert(cq_career_start(0x010807eau,jan26+180)==-1);
  assert(cq_career_start(0x100707edu,2029*365+196)==-1);
  assert(cq_summer_bootstrap(jan26,jan26+208,1));
  assert(!cq_summer_bootstrap(jan26,first27+207,1));
  assert(!cq_summer_bootstrap(jan26,first27+207,0));
  assert(cq_summer_bootstrap(jan26+181,first27+207,1));
  assert(!cq_summer_bootstrap(jan26+181,jan28+208,1));
  assert(cq_final_in_edition(1,jan27+145,jan27+145,jan27+176));
  assert(!cq_final_in_edition(1,jan26+145,jan27+145,jan27+176));
  assert(!cq_final_in_edition(0,jan27+145,jan27+145,jan27+176));
  assert(!cq_final_in_edition(1,jan27+145,jan27+145,jan27+144));
  assert(cq_completed_view_window(first27,jan27+182));
  assert(cq_completed_view_window(first27,jan28));
  assert(!cq_completed_view_window(first27,jan28+CQ_JANUARY_FILL));
  assert(!cq_can_register(jan28+CQ_JANUARY_FILL,jan28+CQ_JANUARY_FILL,33,22,29));
  assert(cq_can_register(jan28+CQ_JANUARY_FILL,jan28+CQ_JANUARY_FILL,33,0,0));
  assert(!cq_qualification_open(jan26,first26,33));
  assert(cq_qualification_open(first26,first26,33));
  assert(cq_can_register(jan26+32,first26,33,0,0));
  assert(!cq_can_register(jan26+32,first26,33,22,0));
  assert(!cq_can_register(jan26+32,first26,33,0,29));
  assert(!cq_can_register(jan26+32,first26,33,-1,0));
  assert(!cq_can_register(jan26+33,first26,33,0,0));
  assert(!cq_qualification_open(jan26+181,first26,33));
  assert(!cq_qualification_open(jan27,first26,33));
  assert(cq_result_fresh(jan27-1,first27,first27));
  assert(cq_result_fresh(jan26,first27,first27));
  assert(!cq_result_fresh(jan26-1,first27,first27));
  assert(!cq_result_fresh(jan27,first27,first27));
  assert(!cq_result_fresh(jan27-1,jan28+CQ_JANUARY_FILL,jan28+CQ_JANUARY_FILL));
  assert(cq_result_fresh(jan29-1,jan29+CQ_JANUARY_FILL,jan29+CQ_JANUARY_FILL));
  assert(cq_edition_day(jan28+CQ_JANUARY_FILL,33)==jan28+33);
  assert(cq_edition_day(jan28+CQ_JANUARY_FILL,61)==jan28+61);
  assert(cq_edition_day(jan28+CQ_JANUARY_FILL,145)==jan28+145);
  uint32_t old[40]={CLUB(3),CLUB(1),CLUB(2),CLUB(4)};
  uint32_t current[4]={CLUB(1),CLUB(3),CLUB(5),CLUB(6)};
  assert(cq_current_ranking(old,4,current,4)==4);
  assert(old[0]==CLUB(3) && old[1]==CLUB(1) && old[2]==CLUB(5) && old[3]==CLUB(6));
  const int completed=jan26+CQ_CENTRAL_FINAL_DAY;
  const uint32_t finishers[]={CLUB(3),CLUB(1),CLUB(4),CLUB(2),CLUB(5),CLUB(6)};
  assert(cq_central_year(first27)==2026);
  assert(cq_central_year(first27+365)==2027 && cq_central_year(first27+1)==-1);
  assert(cq_central_bootstrap(jan26,first26));
  assert(!cq_central_bootstrap(jan26+181,first27));
  assert(!cq_central_bootstrap(jan26+CQ_CENTRAL_DRAW,first27));
  assert(cq_central_bootstrap(jan26+CQ_CENTRAL_DRAW+1,first27));
  assert(cq_central_result(2026,completed,first27,finishers,6));
  assert(!cq_central_result(2027,completed,first27,finishers,6));
  assert(!cq_central_result(2026,completed,completed-1,finishers,6));
  assert(!cq_central_result(2026,completed,first27,finishers,5));
  static cq_config feeder;
  feeder.ns=3;
  cq_source* domestic=&feeder.source[0], *central=&feeder.source[1], *car=&feeder.source[2];
  domestic->status=central->status=car->status=1;
  domestic->n=32;
  for (int i=0;i<32;i++) domestic->club[i]=CLUB(i+1);
  central->kind=CQ_CENTRAL; central->n=6;
  memcpy(central->club,finishers,sizeof finishers);
  car->kind=CQ_CARIBBEAN; car->n=4;
  for (int i=0;i<4;i++) car->club[i]=CLUB(7+i);
  for (int i=0;i<27;i++) {
    cq_place* p=&feeder.place[i];
    p->direct=i<5; p->nf=p->local=1;
    if (i==4 || (i>=5 && i<=9)) {
      p->np=1; p->source[0]=1; p->rank[0]=(uint16_t)(i-3);
    }
    if (i==3 || i==10 || i==11) {
      p->np=1; p->source[0]=2; p->rank[0]=(uint16_t)(i==3 ? 1 : i-8);
    }
  }
  uint16_t wire[256]={1,710,711,1,33,40,3, 217,0,1,32, 701,3,1,6, 705,2,2,4};
  int cursor=19, central_bye=-1;
  for (int i=0;i<27;i++) {
    const cq_place* p=&feeder.place[i];
    if (i==4) central_bye=cursor;
    wire[cursor++]=p->direct; wire[cursor++]=p->np;
    wire[cursor++]=p->nf; wire[cursor++]=p->local;
    if (p->np) {
      wire[cursor++]=p->source[0]; wire[cursor++]=p->rank[0];
    }
    wire[cursor++]=p->fallback[0];
  }
  static cq_config parsed_feeder;
  assert(cq_parse(&parsed_feeder,wire,cursor));
  const int central_capacity=7+4+3;
  wire[central_capacity]=5;
  assert(!cq_parse(&parsed_feeder,wire,cursor));
  wire[central_capacity]=6;
  wire[central_bye]=0;
  assert(!cq_parse(&parsed_feeder,wire,cursor));
  wire[central_bye]=1;
  assert(cq_parse(&parsed_feeder,wire,cursor));
  assert(cq_resolve(&feeder,out)==1 && cq_unique(out,27));
  assert(out[4]==finishers[0] && !memcmp(out+5,finishers+1,5*sizeof *out));
  assert(out[3]==car->club[0] && out[10]==car->club[1] && out[11]==car->club[2]);
  assert(cq_central_snapshot(&feeder,1,central,out));
  out[4]=finishers[1];
  assert(!cq_central_snapshot(&feeder,1,central,out));
  car->club[0]=finishers[0];
  assert(!cq_resolve(&feeder,out));
  car->n=0;
  assert(cq_resolve(&feeder,out)==1 && cq_central_snapshot(&feeder,1,central,out));
  central->club[5]=central->club[4]|1;
  assert(!cq_resolve(&feeder,out));
  central->n=0; central->status=2;
  assert(cq_resolve(&feeder,out)==-1);
  central->status=1;
  assert(cq_resolve(&feeder,out)==1 && out[0]==CLUB(1) && out[26]==CLUB(27));
  {
    uint16_t explicit_wire[7+8+27*6]={2,720,721,1,33,40,2,51,0,0,30,734,CQ_LEAGUES,0,3};
    int at=15;
    for (int i=0;i<27;i++) {
      int regional=i>=24;
      explicit_wire[at++]=i<4 || i==24;
      explicit_wire[at++]=1;
      explicit_wire[at++]=0;
      explicit_wire[at++]=0;
      explicit_wire[at++]=(uint16_t)regional;
      explicit_wire[at++]=(uint16_t)(regional ? i-23 : i+1);
    }
    cq_config explicit;
    assert(cq_parse(&explicit,explicit_wire,at));
    explicit.source[0].status=explicit.source[1].status=1;
    explicit.source[0].n=30;
    for (int i=0;i<30;i++) explicit.source[0].club[i]=CLUB(i+1);
    assert(cq_resolve(&explicit,out)==-1); /* January before the first Leagues Cup result. */
    explicit.source[1].n=3;
    for (int i=0;i<3;i++) explicit.source[1].club[i]=CLUB(i+1);
    assert(cq_resolve(&explicit,out)==1 && cq_unique(out,27)); /* Same-source replacements. */
    explicit.source[0].n=23;
    assert(cq_resolve(&explicit,out)==0); /* Never add an unconfigured source. */
  }
  {
    uint16_t wire[7+10+27*6]={3,720,721,1,33,40,2,51,0,0,30,0,55,1,0,0,1};
    int at=17;
    for (int i=0;i<27;i++) {
      wire[at++]=i<5;
      wire[at++]=1; wire[at++]=0; wire[at++]=0;
      wire[at++]=i==0;
      wire[at++]=i ? i+1 : 1;
    }
    cq_config individual;
    assert(cq_parse(&individual,wire,at));
    individual.source[0].status=1; individual.source[0].n=30;
    for (int i=0;i<30;i++) individual.source[0].club[i]=CLUB(i+1);
    individual.source[1].status=1;
    assert(cq_resolve(&individual,out)==1 && out[0]==CLUB(1)); /* bootstrap */
    individual.source[1].n=1; individual.source[1].club[0]=CLUB(4);
    assert(cq_resolve(&individual,out)==1 && out[0]==CLUB(1) && out[3]==CLUB(4));
    individual.source[1].club[0]=CLUB(30);
    assert(cq_resolve(&individual,out)==1 && out[0]==CLUB(30));
    individual.source[1].status=2;
    assert(cq_resolve(&individual,out)==-1); /* never guess an unfinished annual cup */
    wire[16]=2;
    assert(!cq_parse(&individual,wire,at));
  }
  if (argc>1) {
    uint16_t words[8192]; FILE* f=fopen(argv[1],"rb"); assert(f);
    int n=(int)fread(words,sizeof(uint16_t),8192,f); fclose(f);
    static cq_config c, scratch;
    assert(cq_parse(&c,words,n));
    for (int i=0;i<n;i++) assert(!cq_parse(&scratch,words,i));
    const uint16_t version=words[0];
    words[0]=0; assert(!cq_parse(&scratch,words,n)); words[0]=version;
    unsigned club=1;
    for (int i=0;i<c.ns;i++) {
      cq_source* s=&c.source[i]; s->status=1;
      if (s->kind>=CQ_CARIBBEAN) {
        s->n=s->capacity;
        for (int j=0;j<s->n;j++) s->club[j]=CLUB(1000+10*i+j);
      } else if (s->kind) { s->n=1; s->club[0]=CLUB(1); }
      else { s->n=s->capacity; for (int j=0;j<s->n;j++) s->club[j]=CLUB(club++); }
    }
    assert(cq_resolve(&c,out)==1); assert(cq_unique(out,27));
    for (int i=0;i<c.ns;i++) if (c.source[i].kind==CQ_LEAGUES)
      assert(cq_central_snapshot(&c,i,&c.source[i],out));
    for (int i=0;i<c.ns;i++) {
      int old=c.source[i].status; c.source[i].status=2;
      /* A missing used source can only wait/fail, never create a guessed field. */
      int r=cq_resolve(&c,out); assert(r==1 || r==-1); c.source[i].status=old;
    }
    for (int i=0;i<c.ns;i++) { c.source[i].n=1; c.source[i].club[0]=CLUB(1); }
    assert(cq_resolve(&c,out)==0);
  }
  puts("CONCACAF: strict 11-tie handover, uniqueness, season reset, contract bounds and qualification passed");
  return 0;
}
