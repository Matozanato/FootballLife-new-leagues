#define FL26_RCAL_TEST
#include "fl26swiss.c"
#include <assert.h>

int rcal_test_today(void) { return 0; }
int rcal_test_invites(int k, uint16_t id) { (void)k; (void)id; return 0; }
int rcal_test_recday(uint16_t id) { (void)id; return -1; }
int rcal_test_dayload(int d) { (void)d; return 0; }
int rcal_test_round(uint16_t id) { (void)id; return 0; }

static unsigned char *records, owner[0x50];
static int emitted[LC_BATCHES], starts, fail_batch=-1, rollbacks;

static void clear_records(void)
{
  memset(records,0xff,(LC_MATCHES+8)*MATCH_STRIDE);
  memset(records+lay_calendar(),0xff,365*lay_day_size());
}

static uint64_t fake_owner(void) { return (uintptr_t)owner; }
static uint64_t fake_phase(uint32_t* comp, uint64_t kind)
{
  (void)comp;
  return kind;
}
static unsigned char* fake_getrec(void* block, uint16_t id)
{
  static unsigned char rec[0x310];
  assert(block==records && lc_batch(&g_lc,id)>=0);
  *(uint16_t*)rec=id;
  *(uint32_t*)(rec+0x80)=768;
  *(uint32_t*)(rec+0x304)=8;
  return rec;
}
static char fake_free(void* ctx, uint64_t id) { (void)ctx; (void)id; return 1; }
static char fake_start(uint64_t id) { assert(lc_batch(&g_lc,(uint16_t)id)>=0); starts++; return 1; }
static char fake_clubs(uint64_t id, u32vec* list, uint64_t flag)
{
  assert(lc_batch(&g_lc,(uint16_t)id)>=0 && flag==1);
  assert(list->e-list->b==(id>>10 ? 2 : 18));
  return 1;
}

static void fake_register(void* ctx, void* vec)
{
  (void)ctx;
  struct { const uint16_t *b, *e, *c; }* ids=vec;
  int batch=lc_batch(&g_lc,ids->b[0]), replica=(ids->b[0]>>10)!=0;
  assert(batch>=0 && ids->e-ids->b==(replica ? 9 : 1));
  if (!replica && (batch%2)) return; /* exercise exact replica fallback */
  assert(!emitted[batch]++);
  for (int t=0;t<LC_TIES-(batch==fail_batch);t++) {
    unsigned h,a;
    lc_pair(batch,t,&h,&a);
    unsigned char* m=records+(batch*LC_TIES+t)*MATCH_STRIDE;
    memset(m,0,MATCH_STRIDE);
    *(uint32_t*)m=(uint32_t)(batch*LC_TIES+t);
    *(uint16_t*)(m+4)=ids->b[replica ? t : 0];
    unsigned day=lc_group_days[batch][t] ? lc_group_days[batch][t] : g_lpre[batch].days[0];
    *(uint16_t*)(m+8)=LC_YEAR; m[10]=day<=LC_AUG_LAST ? 8 : 9;
    m[11]=(unsigned char)(day-(m[10]==8 ? 211 : LC_AUG_LAST));
    *(uint32_t*)(m+0x14)=g_lc.clubs[h]<<14;
    *(uint32_t*)(m+0x18)=g_lc.clubs[a]<<14;
    unsigned char* list=records+lay_calendar()+day*lay_day_size();
    for (int i=0;i<lay_day_ids();i++) if (lay_day_id(list,i)==0xffff) {
      lay_day_set(list,i,*(uint32_t*)m);
      break;
    }
  }
}

static int fake_rollback(void* ctx, const uint16_t* masters)
{
  assert(ctx==owner && masters==g_lc.master);
  assert(emitted[0] && emitted[1] && !emitted[2]);
  clear_records();
  rollbacks++;
  return 1;
}

static void stub(unsigned offset, uintptr_t target)
{
  unsigned char* p=(unsigned char*)(g_base+offset);
  p[0]=0x48; p[1]=0xb8; memcpy(p+2,&target,8); p[10]=0xff; p[11]=0xe0;
}

static void fake_group_push(lc_page_vector* page, const uint16_t* reg)
{
  assert(page->end<page->capacity);
  *page->end++=*reg;
}

static void fake_group_builder(lc_page_vector* page, uint32_t* comp, unsigned kind)
{
  assert(kind==2);
  uint16_t native=(uint16_t)*comp;
  fake_group_push(page,&native);
}

static void fake_info_push(ci_vec_t* menu, const ci_item_t* item)
{
  assert(menu->e<menu->c);
  *menu->e++=*item;
}

static unsigned char* fake_info_transition(unsigned char* flow)
{
  (void)flow;
  return (unsigned char*)"standings";
}

static const lc_player_ranking* fake_native_stats(uint16_t reg, uint16_t stage, uint8_t assists)
{
  static lc_player_ranking table;
  assert(reg && stage==46);
  table.count=assists ? 7 : 13;
  return &table;
}

static void test_info_menu(void)
{
  stub(CIPUSH_RVA,(uintptr_t)fake_info_push);
  ci_item_t items[6]={{.type=9,.en=1,.text=0x2bc01f5,.buf="regulations",.size=11,.cap=15},
                      {.type=7,.en=1,.buf="goalranking",.size=11,.cap=15}};
  ci_vec_t menu={items,items+2,items+6};
  g_lc.mexico=11;
  uint32_t comp=ci_live_comp(g_lc.master[0]);
  lc_ci_append(&menu,comp);
  assert(menu.e-menu.b==4);
  assert(!strcmp(items[0].buf,"standings") && items[0].text==LC_TABLE_TEXT);
  assert(!strcmp(items[1].buf,"standings") && items[1].text==LC_MX_TABLE_TEXT);
  assert(!strcmp(items[2].buf,"tournamentdraw"));
  assert(!strcmp(items[3].buf,"regulations") && items[3].en && items[3].text==0x2bc01f5);
  assert(g_ci_vec==&menu && g_ci_n==4 && g_ci_comp==comp);
  unsigned char context[0x100]={0}, flow[0x90]={0};
  *(unsigned char**)(flow+0x88)=context;
  g_tramp_cisel=(unsigned char*)(uintptr_t)fake_info_transition;
  for (int side=0;side<2;side++) {
    *(int32_t*)(context+0xd8)=side;
    ci_sel_handler(flow);
    assert(g_ci_pick==g_lc.master[0]+1024*(side+1));
  }
  g_lc_player_stats_hooks=1;
  lc_ci_append(&menu,comp);
  assert(menu.e-menu.b==6 && g_ci_n==6);
  assert(items[3].type==7 && !items[3].en && items[3].text==0x1a00d6 && !strcmp(items[3].buf,"goalranking"));
  assert(items[4].type==8 && !items[4].en && items[4].text==0x1a00d7 && !strcmp(items[4].buf,"assistranking"));
  assert(items[5].type==9 && items[5].en && items[5].text==0x2bc01f5 && !strcmp(items[5].buf,"regulations"));
  stub(0x157c5d0,(uintptr_t)fake_native_stats);
  g_lc_player_stats_open=1;
  g_lc_player_stats_year=g_lc.year;
  g_lc_player_stats_timeline=g_timeline;
  g_lc_player_ranks[0].count=g_lc_player_ranks[1].count=40;
  assert(lc_player_stats_page(g_lc.master[0],46,0)==&g_lc_player_ranks[0]);
  assert(lc_player_stats_page((uint16_t)(g_lc.master[0]+1024),46,1)==&g_lc_player_ranks[1]);
  assert(lc_player_stats_page(1,46,1)->count==7);
  g_lc_player_stats_timeline--;
  assert(lc_player_stats_page(g_lc.master[0],46,0)->count==0);
  g_lc_player_stats_open=0;
  assert(lc_player_stats_page(g_lc.master[0],46,0)->count==13);
  g_lc_player_stats_hooks=0;
  g_ci_vec=0;
  g_ci_pick=0xffff;
  g_lc.mexico=0;
}

static unsigned char test_row[0xa0], test_icon[0xa0], test_division_icon[0xa0];

static void* fake_find_rank_icon(void* finder, unsigned id, unsigned flags)
{
  assert(finder==test_row+0x98 && flags==0);
  if (id==0x1a) return test_division_icon;
  assert(id==0x25);
  return test_icon;
}

static int fake_rank_icon_state(void* icon, unsigned state)
{
  assert(icon==test_icon && state==0);
  *(uint32_t*)(test_icon+0x98)=state;
  return 0;
}

static int fake_rank_icon_hide(void* icon, uint8_t visible, uint8_t recurse, unsigned flags)
{
  assert(icon==test_icon && !visible && recurse && flags==2);
  assert(*(uint32_t*)(test_icon+0x98)==0);
  *(uint32_t*)(test_icon+0xc)&=~flags;
  return 0;
}

static int fake_division_icon_hide(void* icon, uint8_t visible, uint8_t enabled, unsigned flags)
{
  assert(icon==test_division_icon && !visible && !enabled && flags==2);
  *(uint32_t*)(test_division_icon+0x10)&=~flags;
  return 0;
}

static void test_arrow_widget(void)
{
  stub(0xe4d1c0,(uintptr_t)fake_find_rank_icon);
  stub(0xe7ddc0,(uintptr_t)fake_rank_icon_state);
  stub(0xe4c260,(uintptr_t)fake_rank_icon_hide);
  stub(0xe4bba0,(uintptr_t)fake_division_icon_hide);
  /* The same widget may be reused after displaying a down arrow. */
  for (int i=0;i<2;i++) {
    *(uint32_t*)(test_icon+0x98)=2;
    *(uint32_t*)(test_icon+0xc)=3;
    lc_scroll_hide_rank_icon(test_row);
    assert(*(uint32_t*)(test_icon+0xc)==1);
    *(uint32_t*)(test_division_icon+0x10)=7;
    lc_scroll_hide_division_icon(test_row);
    assert(*(uint32_t*)(test_division_icon+0x10)==5);
  }
}

static void test_group_page(void)
{
  stub(0xcc7f20,(uintptr_t)fake_group_push);
  stub(0x1542300,(uintptr_t)fake_group_builder);
  uint16_t rows[2];
  lc_page_vector page={rows,rows,rows+2};
  g_lc_info_groups=g_lc_info_provider=1;
  g_lc.mexico=11;
  uint32_t comp=ci_live_comp(g_lc.master[0]);
  lc_info_group_page(&page,&comp,2);
  assert(page.end-rows==2 && rows[0]==g_lc.master[0]+1024 && rows[1]==g_lc.master[0]+2048);
  assert(((lc_ui_table*)lc_info_group_table(rows[0]))->count==0);
  assert(((lc_ui_table*)lc_info_group_table(rows[1]))->count==0);

  static unsigned char teams[LC_CLUBS*TEAM_STRIDE];
  for (unsigned i=0;i<LC_CLUBS;i++) *(uint32_t*)(teams+i*TEAM_STRIDE)=(g_lc.clubs[i]<<14)|i;
  g_test_teams=teams;
  g_test_nteams=LC_CLUBS;
  *(uint16_t*)(records+lay_today())=0;
  *(uint16_t*)(records+lay_today()+8)=LC_YEAR;
  assert(g_lc_confirm_year!=LC_YEAR);
  page.end=rows;
  lc_info_group_page(&page,&comp,2);
  assert(page.end-rows==2);
  for (unsigned side=0;side<2;side++) {
    const lc_ui_table* table=(const lc_ui_table*)lc_info_group_table(rows[side]);
    assert(table->count==LC_SIDE);
    for (unsigned i=0;i<LC_SIDE;i++) {
      const unsigned char* row=table->rows+i*LC_UI_ROW_SIZE;
      assert((*(const uint32_t*)row>>14)==g_lc.clubs[side*LC_SIDE+i]);
      assert(!row[8] && !row[15]);
    }
    assert(zone_of(rows[side],3)==ZONE_UP && zone_of(rows[side],4)==-1);
  }
  test_arrow_widget();
  g_test_teams=0;
  page.end=rows;
  comp++;
  lc_info_group_page(&page,&comp,2);
  assert(page.end-rows==1 && rows[0]==comp);
  g_lc_info_groups=g_lc_info_provider=0;
  g_lc.mexico=0;
}

static void test_native_knockout(void)
{
  const int semi_last=LC_KO_RECOVERY_LAST-LC_REST-LC_PROCESS_BUFFER;
  int attempt=-1;
  assert(lc_ko_try_day(&attempt,1,253));
  assert(!lc_ko_try_day(&attempt,1,253));
  assert(lc_ko_try_day(&attempt,1,254));
  assert(lc_ko_try_day(&attempt,1,273)); /* recovery remains open in October */
  assert(lc_ko_try_day(&attempt,1,semi_last-LC_REST));
  assert(!lc_ko_try_day(&attempt,1,semi_last-LC_REST+1));
  attempt=INT_MAX;
  assert(!lc_ko_try_day(&attempt,1,254)); /* previous rollback could not be verified */
  attempt=-1;
  assert(lc_ko_try_day(&attempt,2,267));
  assert(!lc_ko_try_day(&attempt,2,267));
  assert(lc_ko_try_day(&attempt,2,268));
  assert(lc_ko_try_day(&attempt,2,LC_KO_RECOVERY_LAST-LC_REST));
  assert(!lc_ko_try_day(&attempt,2,LC_KO_RECOVERY_LAST-LC_REST+1));
  {
    lc_calendar open={0};
    open.capacity=20;
    uint64_t clubs[4]={1,2,4,8};
    uint16_t dates[LC_KO_STAGES];
    unsigned alternatives;
    assert(lc_plan_remaining(&open,1,273,269,clubs,dates,&alternatives));
    assert(dates[1]==276 && dates[2]==281 && alternatives>1);
    lc_block_knockout(&open,1,276);
    assert(lc_plan_remaining(&open,1,273,269,clubs,dates,&alternatives));
    assert(dates[1]==279 && dates[2]==284);
    assert(!lc_plan_remaining(&open,1,LC_KO_RECOVERY_LAST-2,269,clubs,dates,&alternatives));
  }
  {
    lc_calendar calendar={0};
    calendar.capacity=20;
    lc_results played={0};
    memcpy(played.days,lc_preferred,sizeof played.days);
    int original_count=g_nfinal;
    final_t* kept=final_new(LC_PLAN_KEY(g_lc.year));
    assert(kept);
    kept->reg=LC_PLAN_KEY(g_lc.year);
    kept->n=1+LC_BATCHES+LC_KO_STAGES;
    kept->club[0]=g_lc.year;
    for (int b=0;b<LC_BATCHES;b++) kept->club[1+b]=played.days[b];
    for (int s=0;s<LC_KO_STAGES;s++) kept->club[1+LC_BATCHES+s]=250+5*s;
    state_rec_t stored={0};
    stored.gdate=g_lc.year*365+235;
    stored.reg=kept->reg;
    stored.n=(uint8_t)kept->n;
    memcpy(stored.club,kept->club,kept->n*sizeof *kept->club);
    assert(state_clubs_known(&stored));
    uint16_t dates[LC_KO_STAGES];
    assert(lc_plan_restore(&played,&calendar,0,239,LC_ALL_CLUBS,dates));
    assert(dates[0]==250 && dates[1]==255 && dates[2]==260);
    assert(!lc_plan_restore(&played,&calendar,0,251,LC_ALL_CLUBS,dates));
    lc_block_knockout(&calendar,1,255);
    assert(!lc_plan_restore(&played,&calendar,0,239,1,dates));
    assert(lc_plan_restore(&played,&calendar,0,239,2,dates));
    played.days[0]++;
    assert(!lc_plan_restore(&played,&calendar,0,239,2,dates));
    stored.gdate+=365;
    assert(!state_clubs_known(&stored));
    final_t* stop=final_new(LC_STOP_KEY(g_lc.year));
    assert(stop);
    stop->reg=LC_STOP_KEY(g_lc.year);
    stop->n=2;
    stop->club[0]=g_lc.year;
    stop->club[1]=1u<<2;
    stored.reg=stop->reg;
    stored.gdate=g_lc.year*365+235;
    stored.n=2;
    memcpy(stored.club,stop->club,2*sizeof *stop->club);
    assert(state_clubs_known(&stored) && lc_rollback_quarantined(2));
    assert(!lc_rollback_quarantined(0) && !lc_rollback_quarantined(3));
    stored.club[1]=1u<<4;
    assert(!state_clubs_known(&stored));
    g_nfinal=original_count;
  }

  uint32_t pairs[8]={100,118,101,119,102,120,103,121};
  lc_results phase={0};
  phase.played=54;
  for (unsigned i=0;i<LC_CLUBS;i++) phase.table[i].played=3;
  for (unsigned i=0;i<4;i++) phase.table[18+i].points=i+1;
  lc_bracket_view view, again;
  assert(lc_view_read(&view,&phase,g_lc.ko[0]));
  assert(view.rounds[0].slots[0].legs[0]==UINT16_MAX);
  unsigned slot=LC_MATCHES;
  for (int s=0;s<3;s++) {
    int first=232+5*s;
    for (int t=0;t<lc_ko_ties[s];t++,slot++) {
      int day=first+t%2;
      unsigned char* list=records+lay_calendar()+(size_t)day*lay_day_size();
      unsigned char* m=records+(size_t)slot*MATCH_STRIDE;
      memset(m,0,MATCH_STRIDE);
      *(uint32_t*)m=slot;
      *(uint16_t*)(m+4)=g_lc.ko[s]+1024*(t+1);
      *(uint16_t*)(m+8)=LC_YEAR; m[10]=day<243 ? 8 : 9; m[11]=day-(day<243 ? 211 : 242);
      *(uint32_t*)(m+0x14)=pairs[2*t]<<14;
      *(uint32_t*)(m+0x18)=pairs[2*t+1]<<14;
      m[7]=0x40; m[0x1e]=4; m[0x21]=2;
      lay_day_set(list,t/2,slot);
    }
    lc_knockout result;
    assert(lc_knockout_read(s,pairs,&result) && result.records.count==lc_ko_ties[s]);
    assert(result.first==first && result.day==first+1);
    for (int t=0;t<lc_ko_ties[s];t++) assert(result.tie_day[t]==first+t%2);
    *(uint16_t*)(records+TODAY_OFF)=(uint16_t)first;
    *(uint16_t*)(records+TODAY_OFF+8)=LC_YEAR;
    memset(lc_replica_days[s],0,sizeof lc_replica_days[s]);
    lc_ko_recover_date(s);
    assert(!memcmp(lc_replica_days[s],result.tie_day,sizeof result.tie_day));
    assert(lc_filed(&result.records,1) && result.won[0]==pairs[0]);
    assert(lc_view_read(&view,&phase,g_lc.ko[0]));
    assert(lc_view_read(&again,&phase,g_lc.ko[0]));
    assert(!memcmp(&view,&again,sizeof view));
    assert(view.rounds[0].slots[1].legs[0]==LC_MATCHES+3);
    assert(view.matches[0][1].score[2]==4 && view.matches[0][1].score[5]==2);
    assert(view.rounds[1].slots[0].sources[1]==view.rounds[0].slots[1].key);
    if (s==0) {
      const lc_view_round* quarters=lc_list_projected_round(&view,0x2e);
      assert(quarters && quarters->kind_count>>26==0x33 && (quarters->kind_count&0xff)==4);
      assert(!lc_list_projected_round(&view,0x33));
      assert(view.rounds[1].slots[0].legs[0]==UINT16_MAX);
      assert((view.rounds[1].slots[0].clubs[0]>>14)==100);
      assert((view.rounds[1].slots[0].clubs[1]>>14)==103);
      assert(view.rounds[2].slots[0].clubs[0]==UINT32_MAX);
    }
    if (s==1) {
      const lc_view_round* semis=lc_list_projected_round(&view,0x33);
      assert(semis && semis->kind_count>>26==0x34 && (semis->kind_count&0xff)==2);
      assert(!lc_list_projected_round(&view,0x34) && !lc_list_projected_round(&view,0x35));
      assert(view.rounds[2].slots[0].legs[0]==UINT16_MAX);
      assert((view.rounds[2].slots[0].clubs[0]>>14)==100);
      assert((view.rounds[2].slots[0].clubs[1]>>14)==101);
      assert((view.rounds[3].slots[0].clubs[0]>>14)==103);
      assert((view.rounds[3].slots[0].clubs[1]>>14)==102);
    }
    if (s==2) {
      assert(view.matches[3][0].day==first);
      assert(view.matches[2][0].day==first+1);
    }
    if (s<2) lc_advance_bracket(s,result.won,result.lost,pairs);
    else assert(result.won[1]==100 && result.lost[1]==101 && result.won[0]==103);
  }
  assert(slot==62);
  assert(lc_list_projected_round(&view,0x34)==&view.rounds[3]); /* bronze before final */
  assert(lc_list_projected_round(&view,0x35)==&view.rounds[2]);
  static const uint32_t live_ids[]={75734,75737,75735,75736,75738,75739,131071,75741};
  static const uint32_t labels[]={0x3a2001b,0x3a2001c,0x3a2001d,0x190021};
  unsigned match_index=0;
  for (unsigned round=0;round<LC_VIEW_ROUNDS;round++)
    for (unsigned tie=0;tie<(view.rounds[round].kind_count&0xff);tie++) {
      lc_view_match* match=&view.matches[round][tie];
      uint32_t id=live_ids[match_index++];
      uint16_t replica=match->regulation;
      match->id=id;
      assert(lc_view_match_for_key(&view,view.rounds[round].slots[tie].key)==match);
      assert(lc_view_match_is_exact(match,id,replica));
      assert(!lc_view_match_is_exact(match,(uint16_t)id,replica));
      assert(!lc_view_match_is_exact(match,(uint16_t)id,7)); /* domestic fixture */
      assert(!lc_view_match_is_exact(match,id,7));
      assert(!lc_view_match_is_exact(match,id,(uint16_t)(replica^1024)));
      assert(lc_view_round_text(&view,match)==labels[round]);
      uint32_t kind=view.rounds[round].kind_count>>26;
      assert(lc_list_row_round_for(&view,replica,kind)==&view.rounds[round]);
      assert(lc_view_match_for_key(&view,lc_list_row_round_for(&view,replica,kind)->slots[tie].key)==match);
      assert(!lc_list_row_round_for(&view,replica,kind==0x35 ? 0x33 : 0x35));
      assert(!lc_list_row_round_for(&view,7,kind));
    }
  assert(view.matches[2][0].winner==100 && view.matches[3][0].winner==103);
  char score[32];
  lc_view_score_text(lc_view_match_for_key(&view,view.rounds[2].slots[0].key),score);
  assert(!strcmp(score,"0-0 (4-2 pen.)"));
  lc_view_score_text(0,score);
  assert(!score[0]);
  char intermediate[96];
  lc_view_intermediate_text(&view,100,intermediate);
  assert(!strcmp(intermediate,"QF 0-0 (4-2 pen.) W / SF 0-0 (4-2 pen.) W"));
  lc_view_intermediate_text(&view,118,intermediate);
  assert(!strcmp(intermediate,"QF 0-0 (4-2 pen.)"));
  assert(view.rounds[1].slots[1].destinations[1]==view.rounds[3].slots[0].key);
  assert(view.rounds[3].slots[0].sources[1]==view.rounds[1].slots[1].key);
  assert(!lc_view_match_for_key(&view,LC_VIEW_NO_LINK));
  if (lay_day_elem()==4) {
    uint32_t* native_id=(uint32_t*)(records+(slot-1)*MATCH_STRIDE);
    *native_id+=65536;
    assert(lc_view_read(&view,&phase,g_lc.ko[0]));
    const lc_view_match* final=lc_view_match_for_key(&view,view.rounds[2].slots[0].key);
    assert(final && final->id==*native_id && final->regulation==g_lc.ko[2]+2048);
    assert(final->score[2]==4 && final->score[5]==2);
    *native_id-=65536;
  }
  unsigned char* match=records+LC_MATCHES*MATCH_STRIDE;
  match[7]=0;
  assert(lc_view_read(&view,&phase,g_lc.ko[0]));
  lc_view_intermediate_text(&view,100,intermediate);
  assert(!strcmp(intermediate,"QF -"));
  assert(!view.matches[0][0].winner && view.rounds[1].slots[0].legs[0]==UINT16_MAX);
  assert(view.rounds[1].slots[0].clubs[0]==UINT32_MAX);
  assert((view.rounds[1].slots[0].clubs[1]>>14)==103);
  match[7]=0x40;
  g_lc.year++;
  assert(!lc_view_read(&view,&phase,g_lc.ko[0]));
  for (unsigned i=LC_MATCHES;i<slot;i++)
    *(uint16_t*)(records+(size_t)i*MATCH_STRIDE+8)=g_lc.year;
  assert(lc_view_read(&view,&phase,g_lc.ko[0]) && view.year==g_lc.year);
  assert(view.matches[3][0].winner==103);
  g_lc.year--;
  for (unsigned i=LC_MATCHES;i<slot;i++)
    *(uint16_t*)(records+(size_t)i*MATCH_STRIDE+8)=g_lc.year;
}

static void test_native_standings(const lc_results* results)
{
  uint32_t handles[LC_CLUBS];
  lc_ui_table tables[2];
  for (unsigned i=0;i<LC_CLUBS;i++) handles[i]=(g_lc.clubs[i]<<14)|i;
  lc_ui_tables(tables,&g_lc,results,handles);
  for (unsigned side=0;side<2;side++) {
    assert(tables[side].count==18);
    unsigned previous=LC_CLUBS, seen=0;
    for (unsigned rank=0;rank<LC_SIDE;rank++) {
      const unsigned char* row=tables[side].rows+rank*LC_UI_ROW_SIZE;
      uint32_t handle, position, record, goals;
      memcpy(&handle,row,4); memcpy(&record,row+8,4); memcpy(&goals,row+12,4);
      memcpy(&position,row+4,4);
      assert(position==rank+1);
      unsigned i=handle&0x3fff;
      assert(i<LC_CLUBS && i/LC_SIDE==side && handle==handles[i]);
      assert(!(seen&(1u<<(i%LC_SIDE))));
      seen|=1u<<(i%LC_SIDE);
      assert(!rank || lc_rank_before(&g_lc,results,previous,i));
      previous=i;
      const lc_stats* stats=&results->table[i];
      assert((record&255)==stats->points && ((record>>8)&63)==stats->regulation_wins);
      assert(((record>>14)&63)==stats->regulation_losses);
      assert(((record>>20)&63)==stats->penalty_wins+stats->penalty_losses);
      assert((goals&4095)==stats->gf && ((goals>>12)&4095)==stats->ga && (goals>>24)==stats->played);
    }
  }
}

static void test_registration(void)
{
  g_base=(uintptr_t)VirtualAlloc(0,0x27b4000,MEM_RESERVE|MEM_COMMIT,PAGE_EXECUTE_READWRITE);
  assert(g_base);
  records=(unsigned char*)VirtualAlloc(0,lay_today()+16,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);
  assert(records);
  clear_records();
  *(void**)(owner+0x48)=records;
  stub(OWNER_RVA,(uintptr_t)fake_owner);
  stub(GETREC_RVA,(uintptr_t)fake_getrec);
  stub(FINDREC_RVA,(uintptr_t)fake_getrec);
  stub(FREETAB_RVA,(uintptr_t)fake_free);
  stub(START_RVA,(uintptr_t)fake_start);
  stub(REGALL_RVA,(uintptr_t)fake_register);
  g_tramp_setcl=(unsigned char*)(uintptr_t)fake_clubs;
  memcpy((void*)(g_base+MATCH_BASE_SITE),"\x48\x8d\x88",3);
  memcpy((void*)(g_base+MATCH_CAP_SITE),"\x81\xff",2);
  *(uint32_t*)(g_base+MATCH_CAP_SITE+2)=LC_MATCHES+8;
  test_info_menu();
  test_group_page();
  uint32_t handles[LC_CLUBS];
  for (int i=0;i<LC_CLUBS;i++) handles[i]=g_lc.clubs[i]<<14;
  lc_records native;
  lc_apply_days((const uint16_t[]){215,217,222,224,229,231},0);
  assert(lc_start(handles,&native));
  assert(starts==6);
  for (int b=0;b<LC_BATCHES;b++) assert(emitted[b]==1);
  lc_results audit;
  assert(lc_scan(&audit,&native,0) && native.count==54 && !audit.played);
  assert(lc_occupied_year()==2026);
  g_lc.year=2027;
  assert(!lc_scan(&audit,&native,0));
  g_lc.year=2026;
  assert(lc_scan(&audit,&native,0) && native.count==54);
  assert(audit.days[0]==215 && audit.days[1]==217 && lc_ordered(audit.days));
  assert(lc_scan(&audit,&native,0) && native.count==54 && starts==6 && lc_filed(&native,1));
  *(uint16_t*)(records+lay_today())=LC_FILL;
  *(uint16_t*)(records+lay_today()+8)=LC_YEAR;
  g_timeline++;
  lc_apply_days(lc_preferred,0);
  lc_tick(0);
  assert(lc_dates_match(audit.days) && starts==6);
  lc_tick(owner);
  assert(lc_dates_match(audit.days) && starts==6);
  unsigned char* late=records+LC_MATCHES*MATCH_STRIDE;
  memset(late,0,MATCH_STRIDE);
  *(uint32_t*)late=LC_MATCHES;
  *(uint16_t*)(late+4)=54;
  *(uint16_t*)(late+8)=LC_YEAR; late[10]=8; late[11]=6;
  *(uint32_t*)(late+0x14)=g_lc.clubs[0]<<14;
  *(uint32_t*)(late+0x18)=999<<14;
  lc_tick(owner);
  assert(lc_dates_match(audit.days) && starts==6);
  *(uint16_t*)(records+lay_today()+8)=LC_YEAR+1;
  lc_tick(owner);
  assert(starts==6);
  unsigned char* list=records+lay_calendar()+215*lay_day_size();
  lay_day_set(list,9,0);
  assert(!lc_filed(&native,1));
  clear_records();
  memset(emitted,0,sizeof emitted);
  fail_batch=1;
  assert(!lc_register_edition(owner,handles,fake_rollback));
  assert(rollbacks==1 && lc_scan(&audit,&native,0) && native.count==0);
  fail_batch=-1;
  memset(emitted,0,sizeof emitted);
  const uint16_t latest[]={216,217,222,224,229,231};
  uint16_t individual[LC_BATCHES][LC_TIES];
  for (int b=0;b<LC_BATCHES;b++) for (int t=0;t<LC_TIES;t++) individual[b][t]=latest[b];
  individual[0][1]=215;
  individual[1][1]=218;
  uint16_t maxima[LC_BATCHES];
  memcpy(maxima,latest,sizeof maxima);
  maxima[1]=218;
  fail_batch=1;
  lc_apply_group(maxima,individual,0);
  assert(lc_register_edition(owner,handles,fake_rollback)==0 && rollbacks==2);
  assert(lc_scan(&audit,&native,0) && !native.count);
  memset(emitted,0,sizeof emitted);
  fail_batch=-1;
  lc_apply_group(maxima,individual,0);
  assert(lc_register_edition(owner,handles,fake_rollback)==1);
  assert(lc_scan(&audit,&native,0) && native.count==54 && lc_group_rest(&audit));
  assert(!memcmp(individual,audit.fixture,sizeof individual) && lc_filed(&native,1));
  lc_apply_group(lc_preferred,0,0);
  g_timeline++;
  *(uint16_t*)(records+lay_today()+8)=LC_YEAR;
  lc_tick(0);
  assert(!memcmp(individual,lc_group_days,sizeof individual));
  clear_records();
  lc_apply_group(lc_preferred,0,0);
  unsigned char* m=records;
  *(uint32_t*)m=0;
  *(uint16_t*)(m+4)=167;
  *(uint16_t*)(m+8)=LC_YEAR; m[10]=8; m[11]=9;
  *(uint32_t*)(m+0x14)=g_lc.clubs[9]<<14;
  *(uint32_t*)(m+0x18)=999<<14;
  lc_calendar cal;
  assert(lc_scan(&audit,&native,&cal) && !native.count && cal.blocked[3][220] && !cal.blocked[2][220]);
  *(uint16_t*)(m+4)=54; m[11]=15;
  *(uint32_t*)(m+0x14)=g_lc.clubs[0]<<14;
  assert(lc_scan(&audit,&native,&cal) && cal.blocked[2][224]);
  assert(!cal.blocked[2][223]);
  *(uint32_t*)(m+0x18)=0;
  assert(lc_scan(&audit,&native,&cal) && cal.blocked[3][224]);
  date_t pending={.day=237};
  vec_t v={(unsigned char*)&pending,(unsigned char*)(&pending+1),(unsigned char*)(&pending+1)};
  lc_note_cup(&v);
  assert(lc_scan(&audit,&native,&cal) && cal.blocked[0][237] && cal.blocked[1][237]);
  g_timeline++;
  assert(lc_scan(&audit,&native,&cal) && !cal.blocked[0][237]);
  clear_records();
  test_native_knockout();
  VirtualFree(records,0,MEM_RELEASE);
  VirtualFree((void*)g_base,0,MEM_RELEASE);
  g_base=0;
}

static void test_allocator(void)
{
  lc_calendar cal={.capacity=80};
  uint16_t days[LC_BATCHES], replay[LC_BATCHES];
  unsigned domains[LC_BATCHES];
  assert(lc_allocate(&g_lc,&cal,days,domains) && !memcmp(days,lc_preferred,sizeof days));
  lc_block(&cal,1,226); /* Austin, August 15 US Open Cup */
  assert(lc_allocate(&g_lc,&cal,days,domains) && days[2]!=224 && days[3]==224);
  assert(lc_allocate(&g_lc,&cal,replay,domains) && !memcmp(days,replay,sizeof days));
  cal.capacity=17;
  assert(lc_allocate(&g_lc,&cal,days,domains) && lc_ordered(days));
  for (int a=0;a<LC_BATCHES;a++) for (int b=0;b<a;b++) assert(days[a]!=days[b]);
  cal.capacity=8;
  assert(!lc_allocate(&g_lc,&cal,days,domains));
  cal.capacity=80;
  memset(cal.blocked,1,sizeof cal.blocked);
  assert(!lc_allocate(&g_lc,&cal,days,domains));
  assert(!lc_ordered((const uint16_t[]){217,217,219,224,231,231}));

  /* The live failure logged cardinalities 2/3 for every wave. The exact dates
     were unavailable. Exercise that shape with and without boundary dates. */
  const uint16_t wave0[]={212,219,226,242}, wave1[]={212,218,225,232};
  for (int b=0;b<LC_BATCHES;b++) for (unsigned i=0;i<4;i++)
    cal.blocked[b][(b%2 ? wave1 : wave0)[i]]=0;
  lc_phase window=g_lc;
  window.first=215; window.last=239;
  assert(!lc_allocate(&window,&cal,days,domains));
  for (int b=0;b<LC_BATCHES;b++) assert(domains[b]==2+(unsigned)(b%2));
  window.first=LC_AUG_FIRST; window.last=LC_AUG_LAST;
  assert(lc_allocate(&window,&cal,days,domains) && lc_ordered(days));
  assert(days[0]==212 || days[4]==242);
  cal.blocked[0][212]=1; cal.blocked[4][242]=1;
  assert(!lc_allocate(&window,&cal,days,domains));
}

/* Apply the relevant changes from sider.ini's fl26caps, fl26match, fl26swiss
 * order to a private PE mapping. Run the real swiss installer without FL27. */
static void test_knockout_install(const char* path, int match_first)
{
  HANDLE file=CreateFileA(path,GENERIC_READ,FILE_SHARE_READ,0,OPEN_EXISTING,0,0);
  assert(file!=INVALID_HANDLE_VALUE);
  HANDLE image=CreateFileMappingA(file,0,PAGE_READONLY|SEC_IMAGE,0,0,0);
  assert(image);
  unsigned char* base=MapViewOfFile(image,FILE_MAP_READ,0,0,0);
  assert(base);
  static const struct { unsigned rva, size; const char* caps_or_match; } patches[]={
    {0xcab4bb,3,"\x89\xc0\x90"}, {0xcab4d3,3,"\x89\xc0\x90"},
    {0x152b07d,3,"\x8b\x17\x90"},
    {0xcaa84e,3,"\x8b\xd0\x90"}, {0xcaaad9,3,"\x8b\xd0\x90"},
    {0xca2219,3,"\x8b\xd3\x90"}, {0xca1fa4,5,"\x8b\x54\xd8\x04\x90"},
    {0xca29c8,5,"\x8b\x54\x24\x24\x90"}, {0xca2b44,5,"\x8b\x54\x24\x24\x90"}
  };
  for (unsigned i=0;i<(match_first ? ARRAYSIZE(patches) : 3);i++) {
    unsigned char* p=base+patches[i].rva;
    DWORD protection;
    assert(VirtualProtect(p,patches[i].size,PAGE_EXECUTE_READWRITE,&protection));
    memcpy(p,patches[i].caps_or_match,patches[i].size);
    assert(VirtualProtect(p,patches[i].size,protection,&protection));
  }
  g_base=(uintptr_t)base;
  g_lc_bracket_hooks=0;
  g_lc_player_stats_hooks=0;
  assert(lc_list_match_width(0));
  lc_info_install();
  assert(g_lc_bracket_hooks); /* installer sets this only when every call site is redirected */
  assert(g_lc_player_stats_hooks);
  assert(base[0xb1768b]==0xe8 && !rk_call_to(g_base,0xb1768b,0x157c5d0));
  assert(rk_call_to(g_base,0xfc4182,0x157c5f0) && rk_call_to(g_base,0x1fc65e2,0x157c5e0));
  const char* header=match_first ? "\x8b\xd0\x90" : "\x89\xc2\x90";
  assert(!memcmp(base+0xcaa84e,header,3) && !memcmp(base+0xcaaad9,header,3));
  assert(lc_list_match_width(0));
  UnmapViewOfFile(base);
  CloseHandle(image);
  CloseHandle(file);
}

static uint32_t lc_stress_random(uint32_t* seed)
{
  *seed=*seed*UINT32_C(1664525)+UINT32_C(1013904223);
  return *seed>>8;
}

static int lc_test_open(const lc_calendar* cal, uint64_t clubs, unsigned day, unsigned matches)
{
  return !(cal->knockout_blocked[day]&clubs) && !cal->calendar_unknown[day] &&
         cal->load[day]+matches<=cal->capacity;
}

static unsigned lc_test_continuations(const lc_calendar* cal, uint64_t clubs, int first, int last)
{
  unsigned n=0;
  const int gap=LC_REST+LC_PROCESS_BUFFER;
  for (int s=first;s<=last-gap;s++) {
    if (!lc_test_open(cal,clubs,s,2)) continue;
    for (int f=s+gap;f<=last;f++)
      if (lc_test_open(cal,clubs,f,2)) { n++; break; }
  }
  return n;
}

static void lc_test_edition_stress(void)
{
  enum { PROFILES=6, CASES=250 };
  unsigned scheduled[PROFILES]={0}, recovery[PROFILES]={0}, branch[PROFILES]={0}, completed[PROFILES]={0},
           independent[PROFILES]={0}, missed[PROFILES]={0}, split_rounds[PROFILES]={0},
           split_groups[PROFILES]={0}, after_august[PROFILES]={0};
  const int gap=LC_REST+LC_PROCESS_BUFFER;
  uint64_t masks[9];
  for (unsigned i=0;i<9;i++) masks[i]=UINT64_C(1)<<i;
  unsigned budget=LC_COVER_BUDGET;
  assert(lc_uncovered_field(masks,9,0,&budget)==0);
  budget=LC_COVER_BUDGET;
  assert(lc_uncovered_field(masks,4,0,&budget)==1);
  budget=0;
  assert(lc_uncovered_field(masks,9,0,&budget)==-1);
  {
    /* One free calendar slot per day forces the same bracket to use
       separate dates in all three stages, including bronze and final. */
    lc_calendar sparse={0};
    sparse.capacity=20;
    const uint64_t clubs[]={1,2,4,8,16,32,64,128};
    for (int d=245;d<=267;d++) sparse.load[d]=19;
    uint16_t ties[4]={0};
    assert(lc_flexible_branch(&sparse,0,245,267,clubs,ties));
    for (int i=0;i<4;i++) {
      assert(ties[i]>=245 && ties[i]<=248);
      for (int j=0;j<i;j++) assert(ties[i]!=ties[j]);
    }
    assert(lc_flexible_branch(&sparse,1,253,267,clubs,ties));
    assert(ties[0]!=ties[1] && ties[0]>=253 && ties[1]>=253);
    assert(lc_flexible_branch(&sparse,2,260,267,clubs,ties));
    assert(ties[0]!=ties[1] && ties[0]>=260 && ties[1]>=260);
    assert(!lc_flexible_branch(&sparse,0,245,259,clubs,ties));
  }
  {
    /* Reproduce the 20271145 trace's aggregate blackout, which cannot tell
       whether the two disjoint semifinals were blocked on the same days. */
    lc_calendar trace={0};
    trace.capacity=96;
    uint64_t semifinalists[]={1,2,4,8};
    lc_block_knockout(&trace,1,262);
    lc_block_knockout(&trace,4,267);
    for (int attempt=257;attempt<=265;attempt++) {
      unsigned blocked=0;
      for (int d=attempt+LC_REST;d<=269;d++)
        if (trace.knockout_blocked[d]&15) blocked++;
      assert(blocked==(unsigned)(270-attempt-LC_REST));
    }
    uint16_t split[4];
    assert(lc_flexible_branch(&trace,1,260,272,semifinalists,split));
    assert(split[0]==265 && split[1]==260);
    printf("20271145 aggregate blackout witness: semifinals %u/%u, historical fixtures outside capture unknown\n",
           split[0],split[1]);
    memset(trace.knockout_blocked,0,sizeof trace.knockout_blocked);
    lc_block_knockout(&trace,1,262);
    lc_block_knockout(&trace,1,267);
    assert(!lc_flexible_branch(&trace,1,260,272,semifinalists,split));
    assert(lc_plan_split(&trace,1,257,252,semifinalists,split));
    printf("20271145 same-count alternative: no September plan, October allowed %u/%u\n",split[0],split[1]);
  }
  const char* labels[]={"normal","domestic-cup","staggered","capacity","late-calendar-change","extreme"};
  for (unsigned profile=0;profile<PROFILES;profile++) for (unsigned trial=0;trial<CASES;trial++) {
    lc_phase phase={0};
    lc_calendar cal={0};
    uint32_t seed=1+trial+CASES*profile;
    phase.first=LC_AUG_FIRST;
    phase.last=LC_AUG_LAST;
    phase.year=LC_YEAR+trial%4;
    cal.capacity=profile==3 ? 18 : 96;
    cal.group_detail=1;
    for (int i=0;i<LC_CLUBS;i++) phase.clubs[i]=1000+trial*40+i;
    for (int day=LC_AUG_FIRST-2;day<=LC_KO_RECOVERY_LAST+2;day++) {
      cal.load[day]=lc_stress_random(&seed)%(cal.capacity+1);
      for (unsigned cohort=0;cohort<2;cohort++) {
        unsigned phase_shift=profile==2 ? 2*cohort : cohort;
        if ((day+phase_shift+trial)%7==0) {
          uint64_t clubs=0;
          for (unsigned i=0;i<LC_CLUBS;i++)
            if (i/LC_TIES%2==cohort) clubs|=UINT64_C(1)<<i;
          lc_block(&cal,1u<<cohort,day);
          lc_block_knockout(&cal,clubs,day);
        }
      }
      unsigned cup_frequency=profile==1 ? 11 : profile==5 ? 5 : 29;
      if (lc_stress_random(&seed)%cup_frequency==0) {
        uint64_t club=UINT64_C(1)<<(lc_stress_random(&seed)%LC_CLUBS);
        unsigned i=0;
        while (!(club&(UINT64_C(1)<<i))) i++;
        lc_block(&cal,1u<<(i/LC_TIES%2),day);
        lc_block_knockout(&cal,club,day);
      }
      if (profile==3 && lc_stress_random(&seed)%5==0) cal.calendar_unknown[day]=1;
    }
    const int today=profile==5 ? LC_FILL+trial%17 : LC_FILL+trial%4;
    memcpy(cal.group_blocked,cal.knockout_blocked,sizeof cal.group_blocked);
    lc_edition_plan plan, again;
    unsigned domains[LC_BATCHES];
    lc_phase window=phase;
    window.first=(uint16_t)(today>=phase.first ? today+1 : phase.first);
    uint16_t group_only[LC_BATCHES];
    independent[profile]+=lc_allocate(&window,&cal,group_only,domains);
    if (!lc_plan_edition(&phase,&cal,today,&plan,domains)) continue;
    scheduled[profile]++;
    recovery[profile]+=plan.recovery;
    branch[profile]+=plan.contingency;
    /* A fresh planning invocation stands in for a lost soft plan. */
    assert(lc_plan_edition(&phase,&cal,today,&again,domains));
    assert(!memcmp(&plan,&again,sizeof plan));
    unsigned load[365]={0};
    int last_group=0;
    lc_results group={0};
    memcpy(group.fixture,plan.fixture,sizeof group.fixture);
    assert(lc_group_rest(&group));
    int split_group=0;
    for (int b=0;b<LC_BATCHES;b++) for (int t=0;t<LC_TIES;t++) {
      unsigned d=plan.fixture[b][t];
      assert(d>today && d>=phase.first && d<=LC_GROUP_LAST);
      assert(!lc_group_date_reason(&cal,b,d,lc_group_pair(b,t),load[d]++));
      split_group|=d!=plan.groups[b];
      if ((int)d>last_group) last_group=(int)d;
    }
    split_groups[profile]+=split_group;
    after_august[profile]+=last_group>LC_AUG_LAST;
    int previous=last_group;
    for (int s=0;!plan.contingency && s<LC_KO_STAGES;s++) {
      unsigned d=plan.knockout[s];
      assert((int)d>=previous+gap && d<=LC_KO_RECOVERY_LAST);
      assert(lc_test_open(&cal,LC_ALL_CLUBS,d,lc_ko_ties[s]));
      previous=(int)d;
    }
    unsigned choices[2][LC_SIDE];
    for (unsigned side=0;side<2;side++) {
      for (unsigned i=0;i<LC_SIDE;i++) choices[side][i]=side*LC_SIDE+i;
      for (unsigned i=0;i<4;i++) {
        unsigned j=i+lc_stress_random(&seed)%(LC_SIDE-i);
        unsigned swap=choices[side][j]; choices[side][j]=choices[side][i]; choices[side][i]=swap;
      }
    }
    uint64_t clubs[8];
    for (unsigned i=0;i<4;i++) {
      clubs[2*i]=UINT64_C(1)<<choices[0][i];
      clubs[2*i+1]=UINT64_C(1)<<choices[1][3-i];
    }
    if (profile==4) { /* a fixture arrives after the reservation; force recalculation */
      int q=plan.knockout[0] ? plan.knockout[0] : last_group+gap;
      int s=plan.knockout[1] ? plan.knockout[1] : q+gap;
      lc_block_knockout(&cal,clubs[trial%8],q);
      lc_block_knockout(&cal,clubs[(trial+3)%8],s);
      if (trial%11==0)
        for (int d=q;d<=LC_KO_RECOVERY_LAST;d+=5) lc_block_knockout(&cal,clubs[0],d);
    }
    int complete=1, previous_day=last_group;
    for (int s=0;s<LC_KO_STAGES;s++) {
      int delay=trial%7==0 ? 4 : (int)(lc_stress_random(&seed)%3);
      if (s==0 && profile==4) delay+=trial%9;
      const int process_day=previous_day+delay;
      uint16_t dates[LC_KO_STAGES];
      uint16_t replicas[4]={0};
      unsigned alternatives=0;
      int common=lc_plan_remaining(&cal,s,process_day,previous_day,clubs,dates,&alternatives);
      if (common) {
        for (unsigned t=0;t<lc_ko_ties[s];t++) replicas[t]=dates[s];
      } else if (!lc_plan_split(&cal,s,process_day,previous_day,clubs,replicas)) {
        complete=0;
        missed[profile]++;
        break;
      }
      int end=0, split=0;
      unsigned used[365]={0};
      for (unsigned t=0;t<lc_ko_ties[s];t++) {
        unsigned d=replicas[t];
        assert((int)d>=process_day+LC_REST && (int)d>=previous_day+LC_REST);
        assert(lc_test_open(&cal,clubs[2*t]|clubs[2*t+1],d,++used[d]));
        if ((int)d>end) end=(int)d;
        split|=d!=replicas[0];
      }
      split_rounds[profile]+=split;
      if (!s) {
        /* Independent search checks all 16 outcomes for the selected quarter date. */
        for (unsigned outcome=0;outcome<16;outcome++) {
          uint64_t winners=0;
          for (unsigned i=0;i<4;i++) winners|=clubs[2*i+((outcome>>i)&1)];
          if (common) assert(lc_test_continuations(&cal,winners,end+gap,LC_KO_RECOVERY_LAST));
        }
        unsigned winner_set=lc_stress_random(&seed)%16;
        for (unsigned i=0;i<4;i++) clubs[i]=clubs[2*i+((winner_set>>i)&1)];
      }
      previous_day=end;
    }
    completed[profile]+=complete;
  }
  unsigned total_planned=0,total_completed=0;
  for (unsigned p=0;p<PROFILES;p++) {
    printf("%s: group-only=%u planned=%u recovery=%u contingent=%u completed=%u blocked_after_commit=%u split_groups=%u after_august=%u split_rounds=%u / %u\n",
           labels[p],independent[p],scheduled[p],recovery[p],branch[p],completed[p],missed[p],split_groups[p],after_august[p],split_rounds[p],CASES);
    total_planned+=scheduled[p];
    total_completed+=completed[p];
  }
  printf("total: planned=%u completed=%u / %u\n",total_planned,total_completed,PROFILES*CASES);
  assert(total_planned>0 && total_completed>0 && total_planned<PROFILES*CASES);
}

/* Replay calendar demand and exclusions derived from a captured native season.
 * Rows are index, occupancy, cohort mask, and the 36-bit blackout mask. */
static void lc_test_archived_calendar(const char* path)
{
  FILE* in=fopen(path,"r");
  assert(in);
  lc_phase phase={0};
  lc_calendar calendar={0};
  int today;
  unsigned first,last;
  assert(fscanf(in,"%d %u %u %u",&today,&first,&last,&calendar.capacity)==4);
  phase.first=(uint16_t)first;
  phase.last=(uint16_t)last;
  for (unsigned d=0;d<365;d++) {
    unsigned index, cohorts;
    unsigned long long clubs;
    assert(fscanf(in,"%u %u %u %llx",&index,&calendar.load[d],&cohorts,&clubs)==4 && index==d);
    for (int b=0;b<LC_BATCHES;b++) calendar.blocked[b][d]=(cohorts>>(b%2))&1;
    calendar.knockout_blocked[d]=clubs;
  }
  fclose(in);
  lc_edition_plan plan;
  unsigned domains[LC_BATCHES];
  int feasible=lc_plan_edition(&phase,&calendar,today,&plan,domains);
  printf("archive: feasible=%d groups=%u/%u/%u/%u/%u/%u knockout=%u/%u/%u alternatives=%u contingency=%d recovery=%d\n",
         feasible,plan.groups[0],plan.groups[1],plan.groups[2],plan.groups[3],plan.groups[4],plan.groups[5],
         plan.knockout[0],plan.knockout[1],plan.knockout[2],plan.alternatives,plan.contingency,plan.recovery);
}

static void test_group_calendar_recovery(void)
{
  lc_phase phase={.year=2027,.first=LC_AUG_FIRST,.last=LC_AUG_LAST};
  lc_calendar calendar={.capacity=96,.group_detail=1};
  const int extra=226;
  for (int d=LC_AUG_FIRST;d<=LC_KO_RECOVERY_LAST;d++) calendar.calendar_unknown[d]=1;
  const int available[]={217,223,extra,231,245,251,257,264,274,284,294};
  for (unsigned i=0;i<ARRAYSIZE(available);i++) calendar.calendar_unknown[available[i]]=0;
  uint64_t fixed=lc_group_pair(1,0);
  calendar.group_blocked[223]=fixed;
  calendar.group_blocked[extra]=LC_ALL_CLUBS^fixed;
  for (int b=0;b<LC_BATCHES;b++) {
    calendar.blocked[b][extra]=1;
    calendar.blocked[b][223]=b%2;
  }
  unsigned domains[LC_BATCHES];
  lc_edition_plan plan;
  assert(!lc_plan_common_edition(&phase,&calendar,LC_FILL,&plan,domains));
  assert(!memcmp(domains,(const unsigned[]){3,2,3,2,3,2},sizeof domains));
  assert(lc_plan_edition(&phase,&calendar,LC_FILL,&plan,domains));
  int split=0;
  for (int b=0;b<LC_BATCHES;b++) for (int t=0;t<LC_TIES;t++)
    split|=plan.fixture[b][t]!=plan.groups[b];
  assert(split && !plan.recovery);
  assert(lc_plan_edition(&phase,&calendar,232,&plan,domains) && plan.recovery);
  lc_results results={0};
  memcpy(results.fixture,plan.fixture,sizeof results.fixture);
  assert(lc_group_rest(&results) && plan.knockout[0]>=257+LC_REST+LC_PROCESS_BUFFER);
  assert(!lc_plan_edition(&phase,&calendar,252,&plan,domains));
}

static void test_player_statistics(void)
{
  unsigned char matches[LC_STATS_FIXTURES][MATCH_STRIDE]={0};
  lc_player_edition edition={0}, phase[2]={{0}};
  lc_player_ranking goals, assists;
  for (unsigned i=0;i<LC_STATS_FIXTURES;i++) {
    unsigned char* m=matches[i];
    uint32_t id=i==1 ? 131072u : 65536u+i;
    memcpy(m,&id,4);
    memcpy(m+8,&(uint32_t){2026},4);
    memcpy(m+0x14,&(uint32_t){(100+i)<<14},4);
    memcpy(m+0x18,&(uint32_t){(300+i)<<14},4);
    memcpy(m+LC_STATS_PLAYER_BASE+LC_STATS_SIDE*LC_STATS_ROW+4,&(uint32_t){500+i},4);
    m[0x1c]=i<18 ? 5 : 0;
    for (unsigned j=0;j<(i<18 ? 5u : 1u);j++) {
      unsigned char* row=m+LC_STATS_PLAYER_BASE+j*LC_STATS_ROW;
      uint32_t player=(i==0 || i==9) && j==0 ? 90000 : 1000+5*i+j;
      memcpy(row,&i,4);
      memcpy(row+4,&player,4);
      row[8]=row[9]=i<18;
    }
    if (i>=54) { m[0x1e]=7; m[0x21]=6; }
    if (i==61) {
      unsigned char* row=m+LC_STATS_PLAYER_BASE;
      memcpy(row+4,&(uint32_t){90000},4);
      row[8]=1;
      row[LC_STATS_ROW+9]=1;
      memcpy(row+LC_STATS_ROW+4,&(uint32_t){80000},4);
      row[LC_STATS_SIDE*LC_STATS_ROW+8]=1;
      m[0x1c]=m[0x1f]=1;
    }
    unsigned master=i<54 ? 700+i/9 : i<58 ? 706 : i<60 ? 707 : 708;
    assert(lc_stats_collect(&edition,m,master,i,2026));
    if (i<18) assert(lc_stats_collect(&phase[i/9],m,master,i,2026));
  }
  for (unsigned p=0;p<2;p++) {
    lc_stats_rank(&phase[p],0,&goals);
    assert(goals.count==40 && goals.rows[39].player!=90000 && goals.rows[39].rank==0);
  }
  assert(edition.played==62 && edition.count==91);
  assert(lc_stats_scoreboard_goals(&edition)==92);
  lc_stats_rank(&edition,0,&goals);
  lc_stats_rank(&edition,1,&assists);
  assert(goals.count==40 && assists.count==40);
  assert(goals.rows[0].player==90000 && goals.rows[0].a==61 && goals.rows[0].n==3);
  assert(assists.rows[0].player==90000 && assists.rows[0].n==2);
  assert(goals.rows[1].rank==1 && goals.rows[2].rank==1 && goals.rows[1].player<goals.rows[2].player);
  unsigned char replica[MATCH_STRIDE];
  memcpy(replica,matches[0],sizeof replica);
  memcpy(replica,&(uint32_t){222222},4);
  assert(lc_stats_collect(&edition,replica,700,0,2026) && edition.played==62);
  replica[LC_STATS_PLAYER_BASE+8]=2;
  assert(!lc_stats_collect(&edition,replica,700,0,2026) && edition.played==62);
  edition=(lc_player_edition){0};
  assert(lc_stats_collect(&edition,matches[0],700,0,2027) && !edition.played);
  memcpy(replica+8,&(uint32_t){2027},4);
  assert(!lc_stats_collect(&edition,replica,700,0,2027) && !edition.count);
  replica[LC_STATS_PLAYER_BASE+8]=1;
  assert(lc_stats_collect(&edition,replica,700,0,2027) && edition.played==1);
  lc_stats_rank(&edition,0,&goals);
  assert(goals.count==5 && goals.rows[4].player==90000 && goals.rows[4].n==1);
}

int main(int argc, char** argv)
{
  uint32_t allocated[3+LC_BATCHES+LC_CLUBS+LC_KO_STAGES+1]={2,709,710,711,712,713,714};
  for (int i=0;i<LC_CLUBS;i++) allocated[1+LC_BATCHES+i]=100+i;
  memcpy(allocated+1+LC_BATCHES+LC_CLUBS,(const uint32_t[]){212,242,715,716,734,221},6*sizeof(uint32_t));
  lc_phase arbitrary;
  assert(lc_parse(&arbitrary,allocated,ARRAYSIZE(allocated)) && arbitrary.allocated_ids && arbitrary.ko[2]==734);
  allocated[ARRAYSIZE(allocated)-2]=715;
  assert(!lc_parse(&arbitrary,allocated,ARRAYSIZE(allocated)));
  if (argc==3 && !strcmp(argv[1],"--calendar")) {
    lc_test_archived_calendar(argv[2]);
    return 0;
  }
  if (argc==2 && !strcmp(argv[1],"--stress")) {
    lc_test_edition_stress();
    return 0;
  }
  if (argc==2) {
    test_knockout_install(argv[1],1);
    test_knockout_install(argv[1],0);
    puts("Knockout list and player ranking hooks installed with both header encodings");
    return 0;
  }
  test_player_statistics();
  test_group_calendar_recovery();
  uint32_t contract[3+LC_BATCHES+LC_CLUBS+LC_KO_STAGES]={1,710,711,712,713,714,715};
  for (int i=0;i<LC_CLUBS;i++) contract[1+LC_BATCHES+i]=100+i;
  contract[ARRAYSIZE(contract)-5]=215;
  contract[ARRAYSIZE(contract)-4]=239;
  for (int i=0;i<LC_KO_STAGES;i++) contract[ARRAYSIZE(contract)-3+i]=706+i;
  assert(!fl26_swiss_leagues_probe(contract,ARRAYSIZE(contract)));
  g_cq_hooks=1;
  contract[8]=100;
  assert(!fl26_swiss_leagues_probe(contract,ARRAYSIZE(contract)));
  contract[8]=101;
  uint32_t annual[ARRAYSIZE(contract)+1];
  memcpy(annual,contract,sizeof contract);
  annual[ARRAYSIZE(annual)-1]=11;
  lc_phase second;
  assert(lc_parse(&second,annual,ARRAYSIZE(annual)) && second.mexico==11 && second.year==2026);
  assert(!lc_hide_category_reg(&second,710));
  assert(!lc_hide_category_reg(&second,166));
  assert(lc_hide_category_reg(&second,711));
  assert(lc_hide_category_reg(&second,708));
  assert(lc_hide_category_reg(&second,710+1024));

  uint32_t rank[30], mexico[18], field[36];
  for (int i=0;i<30;i++) rank[i]=(300-i)<<14;
  for (int i=0;i<18;i++) mexico[i]=(500+i)<<14;
  assert(lc_select_field(field,rank,30,mexico,18));
  assert(field[0]==300 && field[17]==283 && field[18]==500 && field[35]==517);
  assert(!lc_select_field(field,rank,17,mexico,18));
  assert(!lc_select_field(field,rank,30,mexico,17));
  mexico[0]=rank[0]|1;
  assert(!lc_select_field(field,rank,30,mexico,18));
  annual[ARRAYSIZE(annual)-1]=166;
  assert(!lc_parse(&second,annual,ARRAYSIZE(annual)));
  assert(fl26_swiss_leagues_probe(contract,ARRAYSIZE(contract)) && g_nlpre==9);
  assert(!fl26_swiss_leagues_probe(contract,ARRAYSIZE(contract)) && g_nlpre==9);
  assert(lc_batch(&g_lc,701)<0 && lc_batch(&g_lc,710+1024*10)<0);
  uint32_t comp=768;
  g_tramp_phkind=(unsigned char*)(uintptr_t)fake_phase;
  assert(phkind_core(&comp,710,MENU_GRP_RA)==0xffff);
  assert(phkind_core(&comp,710,MENU_GRP2_RA)==0xffff);
  assert(phkind_core(&comp,710,0)==710);
  assert(phkind_core(&comp,701,0)==701);
  unsigned degree[LC_CLUBS]={0}, edges[LC_CLUBS][LC_CLUBS]={{0}};
  lc_results first={0}, reload={0};
  for (int b=0;b<LC_BATCHES;b++) {
    const lpre_t* l=&g_lpre[b];
    assert(l->single && l->ties==9 && lpre_rows(l)==9 && l->days[0]==lc_preferred[b]);
    assert(l->ties<=16);
    assert(lc_preferred[b]==217+7*(unsigned)(b/2));
    for (int t=0;t<LC_TIES;t++) {
      unsigned h,a;
      lc_pair(b,t,&h,&a);
      assert((h<LC_SIDE)!=(a<LC_SIDE) && !edges[h][a] && !edges[a][h]);
      edges[h][a]=1; degree[h]++; degree[a]++;
      uint16_t reg=lpre_tie(l,t);
      int date=LC_YEAR*365+lc_preferred[b];
      const unsigned char score[]={1,0,3,1,0,4};
      assert(!lc_ingest(&g_lc,&first,reg,date+365,0x40,g_lc.clubs[h],g_lc.clubs[a],score));
      assert(lc_ingest(&g_lc,&first,reg,date,0x40,g_lc.clubs[h],g_lc.clubs[a],score));
      assert(!lc_ingest(&g_lc,&first,reg,date,0x40,g_lc.clubs[h],g_lc.clubs[a],score));
      assert(lc_ingest(&g_lc,&reload,l->reg,date,0x40,g_lc.clubs[h],g_lc.clubs[a],score));
    }
  }
  assert(first.played==54 && !memcmp(&first,&reload,sizeof first));
  test_native_standings(&first);
  lc_results partial={0};
  assert(lc_score(&partial.table[2],&partial.table[LC_SIDE+3],(const unsigned char[]){2,0,0,1,0,0}));
  test_native_standings(&partial);
  unsigned points=0;
  for (int i=0;i<LC_CLUBS;i++) {
    const lc_stats* s=&first.table[i];
    assert(degree[i]==3 && s->played==3 && s->gf==3 && s->ga==3 && !s->gd);
    assert(s->penalty_wins+s->penalty_losses==3);
    points+=s->points;
  }
  assert(points==54*3);
  uint32_t pairs[8], next[4];
  assert(lc_quarterfinals(&g_lc,&first,pairs));
  assert(pairs[0]>=100 && pairs[0]<118 && pairs[1]>=118);
  lc_advance_bracket(0,(const uint32_t[]){100,101,118,119},0,next);
  assert(next[0]==100 && next[1]==119 && next[2]==101 && next[3]==118);
  lc_advance_bracket(1,(const uint32_t[]){100,118},(const uint32_t[]){119,101},next);
  assert(next[0]==119 && next[1]==101 && next[2]==100 && next[3]==118);
  assert(lc_knockout_winner(100,118,(const unsigned char[]){1,0,3,1,0,4})==118);
  lc_stats h={0}, a={0};
  assert(lc_score(&h,&a,(const unsigned char[]){2,0,0,0,0,0}));
  assert(h.regulation_wins==1 && a.regulation_losses==1 && h.points==3 && a.points==0);
  assert(lc_score(&h,&a,(const unsigned char[]){0,0,3,0,0,5}));
  assert(h.penalty_losses==1 && a.penalty_wins==1 && h.points==4 && a.points==2);
  assert(h.gd==2 && a.gd==-2);
  assert(!lc_score(&h,&a,(const unsigned char[]){0,0,0,0,0,0}));
  assert(!lc_score(&h,&a,(const unsigned char[]){0,0,255,0,0,4}));
  assert(!lc_score(&h,&a,(const unsigned char[]){0,1,3,0,0,4}));
  assert(!lc_score(&h,&a,(const unsigned char[]){2,0,3,0,0,4}));
  assert(h.played==2 && a.played==2);
  test_registration();
  test_allocator();
  puts("Leagues Cup native registry, exact fixtures, score isolation and replay passed");
}
