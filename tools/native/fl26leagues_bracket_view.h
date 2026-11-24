#ifndef FL26LEAGUES_BRACKET_VIEW_H
#define FL26LEAGUES_BRACKET_VIEW_H

/* TournamentProgress round records as captured in Copa Chile. These copies
 * belong to the presentation layer and are never registered with FL27. */
enum { LC_VIEW_ROUNDS=4 };
#define LC_VIEW_NO_LINK UINT32_C(0x07f7ffff)
typedef struct {
  uint32_t clubs[2];
  uint16_t legs[2];
  uint32_t key, destinations[2], sources[2];
} lc_view_slot;

typedef struct {
  uint16_t regulation, reserved;
  lc_view_slot slots[16];
  uint32_t kind_count;
} lc_view_round;

typedef struct {
  uint32_t id, winner, loser;
  uint16_t regulation, day;
  uint8_t flags, score[6];
} lc_view_match;

typedef struct {
  int year;
  lc_view_round rounds[LC_VIEW_ROUNDS];
  lc_view_match matches[LC_VIEW_ROUNDS][4];
} lc_bracket_view;

_Static_assert(sizeof(lc_view_slot)==32 && offsetof(lc_view_slot,sources)==0x18,"native bracket slot");
_Static_assert(sizeof(lc_view_round)==0x208 && offsetof(lc_view_round,kind_count)==0x204,"native bracket round");

static uint32_t lc_view_key(uint16_t regulation, unsigned kind, unsigned slot)
{
  return regulation | ((kind | (slot<<6))<<16);
}

static const lc_view_match* lc_view_match_for_key(const lc_bracket_view* view, uint32_t key)
{
  for (unsigned r=0;r<LC_VIEW_ROUNDS;r++) {
    const lc_view_round* round=&view->rounds[r];
    for (unsigned t=0;t<(round->kind_count&0xff);t++)
      if (round->slots[t].key==key && round->slots[t].legs[0]!=UINT16_MAX)
        return &view->matches[r][t];
  }
  return 0;
}

static int lc_view_match_is_exact(const lc_view_match* match, uint32_t id, uint16_t regulation)
{
  return match && match->regulation && match->id==id && match->regulation==regulation;
}

static uint32_t lc_view_round_text(const lc_bracket_view* view, const lc_view_match* match)
{
  static const uint32_t labels[]={0x3a2001b,0x3a2001c,0x3a2001d,0x190021};
  for (unsigned r=0;r<LC_VIEW_ROUNDS;r++)
    for (unsigned t=0;t<(view->rounds[r].kind_count&0xff);t++)
      if (&view->matches[r][t]==match) return labels[r];
  return 0;
}

static void lc_view_score_text(const lc_view_match* match, char text[32])
{
  text[0]=0;
  if (!match || !(match->flags&0x40)) return;
  unsigned home=match->score[0]+match->score[1], away=match->score[3]+match->score[4];
  if (home==away && match->score[2]!=match->score[5])
    snprintf(text,32,"%u-%u (%u-%u pen.)",home,away,match->score[2],match->score[5]);
  else
    snprintf(text,32,"%u-%u",home,away);
}

static const lc_view_match* lc_view_intermediate_for_club(const lc_bracket_view* view,
                                                         unsigned round, uint32_t club)
{
  if (!club || round>1) return 0;
  const lc_view_round* node=&view->rounds[round];
  for (unsigned i=0;i<(node->kind_count&0xff);i++) {
    const lc_view_slot* slot=&node->slots[i];
    if (slot->legs[0]!=UINT16_MAX &&
        (slot->clubs[0]>>14==club || slot->clubs[1]>>14==club))
      return lc_view_match_for_key(view,slot->key);
  }
  return 0;
}

static void lc_view_intermediate_text(const lc_bracket_view* view, uint32_t club, char text[96])
{
  text[0]=0;
  size_t used=0;
  for (unsigned round=0;round<2;round++) {
    const lc_view_match* match=lc_view_intermediate_for_club(view,round,club);
    if (!match) {
      if (round!=1) continue;
      const lc_view_slot* semi=view->rounds[1].slots;
      if (semi[0].clubs[0]>>14!=club && semi[0].clubs[1]>>14!=club &&
          semi[1].clubs[0]>>14!=club && semi[1].clubs[1]>>14!=club) continue;
    }
    char score[32];
    lc_view_score_text(match,score);
    int added=snprintf(text+used,96-used,"%s%s %s%s",used ? " / " : "",
                       round==0 ? "QF" : "SF",score[0] ? score : "-",
                       match && match->winner==club ? " W" : "");
    if (added<0 || (size_t)added>=96-used) break;
    used+=(size_t)added;
  }
}

static void lc_view_init(lc_bracket_view* view, uint16_t regulation, int year)
{
  static const unsigned kinds[]={0x33,0x34,0x35,0x36}, counts[]={4,2,1,1};
  memset(view,0,sizeof *view);
  view->year=year;
  for (unsigned r=0;r<LC_VIEW_ROUNDS;r++) {
    lc_view_round* round=&view->rounds[r];
    round->regulation=regulation;
    round->kind_count=(kinds[r]<<26)|counts[r];
    for (unsigned t=0;t<counts[r];t++) {
      lc_view_slot* slot=&round->slots[t];
      slot->clubs[0]=slot->clubs[1]=UINT32_MAX;
      slot->legs[0]=slot->legs[1]=UINT16_MAX;
      slot->key=lc_view_key(regulation,kinds[r],t);
      slot->sources[0]=slot->sources[1]=LC_VIEW_NO_LINK;
      slot->destinations[0]=slot->destinations[1]=LC_VIEW_NO_LINK;
    }
  }
  for (unsigned t=0;t<4;t++) {
    lc_view_slot* q=&view->rounds[0].slots[t];
    lc_view_slot* s=&view->rounds[1].slots[t/2];
    q->destinations[0]=s->key;
    s->sources[t%2]=q->key;
  }
  for (unsigned t=0;t<2;t++) {
    lc_view_slot* s=&view->rounds[1].slots[t];
    s->destinations[0]=view->rounds[2].slots[0].key;
    s->destinations[1]=view->rounds[3].slots[0].key;
    view->rounds[2].slots[0].sources[t]=s->key;
    view->rounds[3].slots[0].sources[t]=s->key;
  }
}

static void lc_view_follow_links(lc_bracket_view* view, unsigned source_round, unsigned target_round,
                                 unsigned destination, int losers)
{
  const lc_view_round* source=&view->rounds[source_round];
  lc_view_round* target=&view->rounds[target_round];
  for (unsigned t=0;t<(target->kind_count&0xff);t++) {
    lc_view_slot* to=&target->slots[t];
    for (unsigned k=0;k<2;k++) {
      for (unsigned i=0;i<(source->kind_count&0xff);i++) {
        const lc_view_slot* from=&source->slots[i];
        if (from->key!=to->sources[k] || from->destinations[destination]!=to->key) continue;
        const lc_view_match* match=&view->matches[source_round][i];
        uint32_t club=losers ? match->loser : match->winner;
        for (unsigned side=0;club && side<2;side++)
          if ((from->clubs[side]>>14)==club) to->clubs[k]=from->clubs[side];
        break;
      }
    }
  }
}

static int lc_view_read(lc_bracket_view* view, const lc_results* phase,
                        uint16_t presentation_regulation)
{
  uint32_t pairs[8], capacity;
  const unsigned char* native=car_matches(&capacity);
  if (!native || !lc_quarterfinals(&g_lc,phase,pairs)) return 0;
  lc_view_init(view,presentation_regulation,g_lc.year);
  /* The renderer pairs adjacent quarters. The sporting QF order is 1, 4,
     2, 3 when laid out top to bottom in a connected tree. */
  static const unsigned quarter_slots[]={0,2,3,1};
  for (int stage=0;stage<LC_KO_STAGES;stage++) {
    lc_knockout result;
    unsigned count=lc_ko_ties[stage];
    if (!lc_knockout_read(stage,pairs,&result)) return 0;
    if (!result.records.count) return 1;
    if (result.records.count!=count) return 0;
    int complete=1;
    for (unsigned t=0;t<count;t++) {
      unsigned round=stage<2 ? (unsigned)stage : 3-t;
      unsigned index=stage==0 ? quarter_slots[t] : stage==1 ? t : 0;
      lc_view_slot* slot=&view->rounds[round].slots[index];
      lc_view_match* match=&view->matches[round][index];
      if (result.record_index[t]>=capacity) return 0;
      const unsigned char* record=native+(size_t)result.record_index[t]*MATCH_STRIDE;
      memcpy(slot->clubs,record+0x14,sizeof slot->clubs);
      match->id=lay_day_elem()==4 ? *(const uint32_t*)record : *(const uint16_t*)record;
      slot->legs[0]=(uint16_t)match->id;
      if (slot->legs[0]==UINT16_MAX) slot->legs[0]=0; /* native presence marker, lookup uses match->id */
      match->regulation=*(const uint16_t*)(record+4);
      match->day=result.tie_day[t];
      match->flags=record[7];
      memcpy(match->score,record+0x1c,sizeof match->score);
      match->winner=result.won[t];
      match->loser=result.lost[t];
      if (!match->winner) complete=0;
    }
    if (stage==0) lc_view_follow_links(view,0,1,0,0);
    if (stage==1) {
      lc_view_follow_links(view,1,2,0,0);
      lc_view_follow_links(view,1,3,1,1);
    }
    if (!complete) return 1;
    if (stage<2) lc_advance_bracket(stage,result.won,result.lost,pairs);
  }
  return 1;
}

/* Emit only on a changed projection. This gives a reference at the menu even
 * if the native factory refuses to open the current knockout entry. */
static void lc_bracket_trace(void)
{
  lc_results phase;
  lc_records matches;
  lc_bracket_view view;
  static lc_bracket_view previous;
  static int timeline=-1;
  if (!g_lc.ko[0] || !lc_scan(&phase,&matches,0) ||
      !lc_view_read(&view,&phase,g_lc.ko[0])) return;
  if (timeline==g_timeline && !memcmp(&previous,&view,sizeof view)) return;
  previous=view;
  timeline=g_timeline;
  for (unsigned r=0;r<LC_VIEW_ROUNDS;r++) {
    const lc_view_round* round=&view.rounds[r];
    for (unsigned t=0;t<(round->kind_count&0xff);t++) {
      const lc_view_slot* s=&round->slots[t];
      const lc_view_match empty={0};
      const lc_view_match* m=lc_view_match_for_key(&view,s->key);
      if (!m) m=&empty;
      logf("Leagues Cup bracket view year=%d kind=%u slot=%u key=%x from=%x/%x to=%x/%x reg=%u match=%u flags=%x clubs=%x/%x score=%u/%u pens=%u/%u",
           view.year,round->kind_count>>26,t,s->key,s->sources[0],s->sources[1],
           s->destinations[0],s->destinations[1],m->regulation,m->id,m->flags,
           s->clubs[0],s->clubs[1],m->score[0],m->score[3],m->score[2],m->score[5]);
    }
  }
}

#endif
