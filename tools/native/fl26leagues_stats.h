#ifndef FL26LEAGUES_STATS_H
#define FL26LEAGUES_STATS_H

/* FL27 rec596. The native ranking builder at 0x140fbd620 reads two
 * 17-player blocks from the match copy before it builds the top 40. */
enum { LC_STATS_FIXTURES=62, LC_STATS_SIDE=17, LC_STATS_ROW=16,
       LC_STATS_PLAYER_BASE=0x24, LC_STATS_PLAYERS=LC_STATS_FIXTURES*2*LC_STATS_SIDE };
typedef struct {
  const unsigned char* raw;
  uint32_t id, home, away;
  unsigned day;
  uint16_t master;
} lc_stats_match;

typedef struct {
  uint32_t id, key, club;
  unsigned day, goals, assists;
} lc_player_total;

typedef struct {
  lc_stats_match matches[LC_STATS_FIXTURES];
  lc_player_total players[LC_STATS_PLAYERS];
  unsigned played, count;
} lc_player_edition;

typedef struct {
  lb_row_t rows[LB_ROWS];
  uint32_t count, capacity;
} lc_player_ranking;

_Static_assert(offsetof(lc_player_ranking,count)==0x320,"FL27 player ranking count");
_Static_assert(LC_STATS_PLAYER_BASE+2*LC_STATS_SIDE*LC_STATS_ROW<=0x254,"FL27 match player block");

static uint32_t lc_stats_u32(const unsigned char* field)
{
  uint32_t value;
  memcpy(&value,field,sizeof value);
  return value;
}

static unsigned lc_stats_scoreboard_goals(const lc_player_edition* total)
{
  unsigned goals=0;
  for (unsigned i=0;i<total->played;i++) {
    const unsigned char* score=total->matches[i].raw+0x1c;
    goals+=score[0]+score[1]+score[3]+score[4];
  }
  return goals;
}

/* Match IDs and sporting ties both guard against counting an alias twice.
 * A second record with conflicting data invalidates the presentation. */
static int lc_stats_collect(lc_player_edition* total, const unsigned char* raw,
                            uint16_t master, unsigned day, unsigned year)
{
  if ((lc_stats_u32(raw+8)&UINT16_MAX)!=year) return 1;
  lc_stats_match match={raw,lc_stats_u32(raw),lc_stats_u32(raw+0x14),
                        lc_stats_u32(raw+0x18),day,master};
  if (match.id==UINT16_MAX || !(match.home>>14) || !(match.away>>14) ||
      (match.home>>14)==(match.away>>14)) return 0;
  for (unsigned i=0;i<total->played;i++) {
    const lc_stats_match* previous=&total->matches[i];
    if (previous->id!=match.id && (previous->master!=master ||
        !((previous->home>>14==match.home>>14 && previous->away>>14==match.away>>14) ||
          (previous->home>>14==match.away>>14 && previous->away>>14==match.home>>14)))) continue;
    return previous->master==master && previous->day==day &&
           previous->home==match.home && previous->away==match.away &&
           !memcmp(previous->raw+0x1c,raw+0x1c,6) &&
           !memcmp(previous->raw+LC_STATS_PLAYER_BASE,raw+LC_STATS_PLAYER_BASE,
                   2*LC_STATS_SIDE*LC_STATS_ROW);
  }
  if (total->played==LC_STATS_FIXTURES) return 0;
  uint32_t seen[2*LC_STATS_SIDE];
  unsigned used=0;
  for (unsigned side=0;side<2;side++) {
    unsigned goals=0, assists=0, identified=0;
    const unsigned char* players=raw+LC_STATS_PLAYER_BASE+side*LC_STATS_SIDE*LC_STATS_ROW;
    unsigned score=raw[0x1c+3*side]+raw[0x1d+3*side]; /* +2 is the shootout */
    for (unsigned i=0;i<LC_STATS_SIDE;i++) {
      const unsigned char* row=players+i*LC_STATS_ROW;
      unsigned g=row[8], a=row[9];
      uint32_t stable=lc_stats_u32(row+4);
      if (!stable || stable==UINT32_MAX) {
        if (g || a) return 0;
        continue;
      }
      identified++;
      if (!g && !a) continue;
      for (unsigned j=0;j<used;j++) if (seen[j]==stable) return 0;
      seen[used++]=stable;
      goals+=g;
      assists+=a;
    }
    /* Own goals may leave a gap between the credited goals and the score. */
    if (goals>score || assists>score || !identified) return 0;
  }
  for (unsigned side=0;side<2;side++) {
    const unsigned char* players=raw+LC_STATS_PLAYER_BASE+side*LC_STATS_SIDE*LC_STATS_ROW;
    uint32_t club=side ? match.away : match.home;
    for (unsigned i=0;i<LC_STATS_SIDE;i++) {
      const unsigned char* row=players+i*LC_STATS_ROW;
      unsigned g=row[8], a=row[9];
      if (!g && !a) continue;
      uint32_t stable=lc_stats_u32(row+4);
      unsigned at=0;
      for (;at<total->count;at++) if (total->players[at].id==stable) break;
      if (at==total->count) {
        total->players[total->count++]=(lc_player_total){.id=stable};
      }
      lc_player_total* player=&total->players[at];
      player->goals+=g;
      player->assists+=a;
      if (!player->club || day>player->day || (day==player->day && club<player->club)) {
        player->key=lc_stats_u32(row);
        player->club=club;
        player->day=day;
      }
    }
  }
  total->matches[total->played++]=match;
  return 1;
}

static void lc_stats_rank(const lc_player_edition* total, int assists, lc_player_ranking* out)
{
  memset(out,0,sizeof *out);
  out->capacity=LB_ROWS;
  for (unsigned i=0;i<total->count;i++) {
    const lc_player_total* p=&total->players[i];
    unsigned n=assists ? p->assists : p->goals;
    if (!n) continue;
    unsigned at=0;
    while (at<out->count && (out->rows[at].n>n ||
           (out->rows[at].n==n && out->rows[at].player<p->id))) at++;
    if (at==LB_ROWS) continue;
    if (out->count<LB_ROWS) out->count++;
    memmove(out->rows+at+1,out->rows+at,(out->count-at-1)*sizeof *out->rows);
    out->rows[at]=(lb_row_t){p->key,p->id,p->club,0,n};
  }
  for (unsigned i=0;i<out->count;i++)
    out->rows[i].rank=i && out->rows[i-1].n==out->rows[i].n ? out->rows[i-1].rank : i;
}

#endif
