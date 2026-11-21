#ifndef FL27_PLAYOFF_RULES_H
#define FL27_PLAYOFF_RULES_H

#include <stdint.h>
#include <stdbool.h>

typedef struct {
    uint64_t entrants;
    uint64_t contested;
    unsigned custom;
    unsigned group_quota_plus_one;
} PlayoffPlaces;

typedef struct {
    uint32_t handle;
    const void *painted;
    bool orange;
    bool forced;
} RowState;

typedef enum { KEEP_BITMAP, PAINT_ORANGE, RESTORE_GREEN } BitmapChange;

static inline void reuse_row(RowState *row, uint32_t handle)
{
    if (row->handle != handle)
        *row = (RowState){.handle = handle};
}

static inline BitmapChange bitmap_change(const RowState *row, const void *bitmap)
{
    if (!bitmap)
        return KEEP_BITMAP;
    if (row->orange && row->painted != bitmap)
        return PAINT_ORANGE;
    if (!row->orange && row->painted == bitmap)
        return RESTORE_GREEN;
    return KEEP_BITMAP;
}

static inline uint64_t rank_bit(unsigned rank)
{
    return rank >= 1 && rank <= 64 ? UINT64_C(1) << (rank - 1) : 0;
}

static inline int playoff_arrow(PlayoffPlaces places, unsigned rank,
                                unsigned promotions, int relegation)
{
    uint64_t bit = rank_bit(rank);
    unsigned slots = places.group_quota_plus_one ? places.group_quota_plus_one - 1 : promotions;
    return !relegation && (places.entrants & bit)
        && (rank > slots || (places.contested & bit));
}

typedef struct {
    unsigned league, upper, cup;
    unsigned uses_points_gap;
} StockPlayoff;

static const StockPlayoff stock_playoffs[] = {
    {79, 17, 83, 0}, /* EFL Championship */
    {80, 19, 84, 0}, /* LaLiga 2 */
    {82, 18, 85, 1}, /* Serie BKT */
};

static inline const StockPlayoff *stock_profile(unsigned league)
{
    for (unsigned i = 0; i < sizeof stock_playoffs / sizeof *stock_playoffs; ++i)
        if (stock_playoffs[i].league == league)
            return &stock_playoffs[i];
    return 0;
}

static inline PlayoffPlaces stock_playoff(const StockPlayoff *profile, unsigned upper,
                                         unsigned promotions, unsigned cup_size,
                                         unsigned cup_format, unsigned count,
                                         uint64_t eligible, const uint8_t *points)
{
    PlayoffPlaces places = {0};
    if (!profile || profile->upper != upper || promotions != 3
        || cup_size != 4 || cup_format != 4 || count > 64)
        return (PlayoffPlaces){0};

    /* FL27 0x141347160 skips two eligible clubs before filling the four places.
       At 0x141347590 Serie B checks a 10-point gap to the next club, a 14-point
       limit for the rest of the field, and allows two to six participants. */
    unsigned start = 0, direct = 0;
    for (unsigned rank = 1; rank <= count; ++rank) {
        if (!(eligible & rank_bit(rank)))
            continue;
        if (direct++ == 2) {
            start = rank;
            break;
        }
    }
    if (!start)
        return places;

    unsigned size = 0;
    for (unsigned rank = start; rank <= count; ++rank) {
        if (profile->uses_points_gap) {
            unsigned lead = points[start - 1], next = points[rank - 1];
            if (rank == start + 1 && lead >= next + 10)
                return (PlayoffPlaces){0};
            if (lead > next + 14)
                break;
        } else if (!(eligible & rank_bit(rank))) {
            continue;
        }
        places.entrants |= rank_bit(rank);
        if (++size == (profile->uses_points_gap ? 6 : 4))
            break;
    }
    if (profile->uses_points_gap ? size < 2 : size != 4)
        return (PlayoffPlaces){0};
    places.contested = rank_bit(start);
    return places;
}

#endif
