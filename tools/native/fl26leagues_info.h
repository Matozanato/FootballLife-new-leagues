#ifndef FL26LEAGUES_INFO_H
#define FL26LEAGUES_INFO_H

#include <stddef.h>
#include "fl26leagues_phase.h"

/* Layout consumed by FL27's native standings controllers. */
enum { LC_UI_ROW_SIZE=20, LC_UI_ROW_COUNT=0x3c0, LC_UI_TABLE_SIZE=0x790 };
typedef struct {
  unsigned char rows[LC_UI_ROW_COUNT];
  uint32_t count;
  /* The scrolling controller also reads the previous rows at +0x3c4 and
     the native display mode at +0x78c. Zero denotes ordinary standings. */
  unsigned char scroll_state[LC_UI_TABLE_SIZE-LC_UI_ROW_COUNT-sizeof(uint32_t)];
} lc_ui_table;
_Static_assert(offsetof(lc_ui_table,count)==LC_UI_ROW_COUNT,"FL27 standings row count offset");
_Static_assert(sizeof(lc_ui_table)==LC_UI_TABLE_SIZE,"FL27 scrolling standings storage");

static void lc_ui_tables(lc_ui_table tables[2], const lc_phase* phase,
                         const lc_results* results, const uint32_t handles[LC_CLUBS])
{
  memset(tables,0,2*sizeof *tables);
  for (unsigned side=0;side<2;side++) {
    unsigned order[LC_SIDE];
    for (unsigned i=0;i<LC_SIDE;i++) {
      unsigned club=side*LC_SIDE+i, at=i;
      for (;at && lc_rank_before(phase,results,club,order[at-1]);at--)
        order[at]=order[at-1];
      order[at]=club;
    }
    for (unsigned i=0;i<LC_SIDE;i++) {
      unsigned club=order[i];
      const lc_stats* s=&results->table[club];
      unsigned char* row=tables[side].rows+i*LC_UI_ROW_SIZE;
      memcpy(row,&handles[club],sizeof handles[club]);
      uint32_t rank=i+1;
      memcpy(row+4,&rank,sizeof rank);
      /* W/D/L describe regulation time. Shootout points come from lc_score. */
      uint32_t record=s->points | (s->regulation_wins<<8) | (s->regulation_losses<<14) |
                      ((s->penalty_wins+s->penalty_losses)<<20);
      uint32_t goals=s->gf | (s->ga<<12) | (s->played<<24);
      memcpy(row+8,&record,sizeof record);
      memcpy(row+12,&goals,sizeof goals);
    }
    tables[side].count=LC_SIDE;
    /* There is no historical rank snapshot in the sporting provider. Equal
       reference ranks keep the game's movement arrows neutral. */
    memcpy(tables[side].scroll_state,tables[side].rows,sizeof tables[side].rows);
  }
}

#endif
