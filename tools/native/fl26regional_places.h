#ifndef FL26REGIONAL_PLACES_H
#define FL26REGIONAL_PLACES_H

#define REGIONAL_RANKS 40
#define REGIONAL_RANK_STRIDE 64

/* Contract words identify a ranking provider and a position; zero position is its cup. */
static int regional_places_valid(const uint16_t* places, unsigned count,
                                 unsigned sources, const uint16_t* cups)
{
  unsigned used=0;
  for (unsigned i=0;i<count;i++) {
    unsigned source=places[i]/REGIONAL_RANK_STRIDE, rank=places[i]%REGIONAL_RANK_STRIDE;
    if (source>=sources || rank>REGIONAL_RANKS || (!rank && !cups[source])) return 0;
    for (unsigned j=0;j<i;j++) if (places[j]==places[i]) return 0;
    used|=1u<<source;
  }
  return used==(1u<<sources)-1;
}

static int regional_club_used(const uint32_t* field, unsigned count, uint32_t club)
{
  if (!club) return 1;
  for (unsigned i=0;i<count;i++) if (field[i] && cq_has(field+i,1,club)) return 1;
  return 0;
}

/* Reserve named positions first, then distinct cup winners. Replacements stay in
 * the same league and cannot take another explicitly reserved club. */
static int regional_select(const uint16_t* places, unsigned count, const uint32_t* const* tables,
                           const unsigned* sizes, const uint32_t* cups, uint32_t* field)
{
  memset(field,0,count*sizeof *field);
  for (unsigned pass=0;pass<3;pass++) for (unsigned i=0;i<count;i++) {
    unsigned source=places[i]/REGIONAL_RANK_STRIDE, rank=places[i]%REGIONAL_RANK_STRIDE;
    if (pass==0 && rank && rank<=sizes[source]) {
      uint32_t club=tables[source][rank-1];
      if (!regional_club_used(field,count,club)) field[i]=club;
    } else if (pass==1 && !rank && !regional_club_used(field,count,cups[source])) {
      field[i]=cups[source];
    } else if (pass==2 && !field[i]) {
      for (unsigned k=rank ? rank-1 : 0;k<sizes[source];k++) {
        uint32_t club=tables[source][k];
        if (!regional_club_used(field,count,club)) { field[i]=club; break; }
      }
      if (!field[i]) return 0;
    }
  }
  return 1;
}

#endif
