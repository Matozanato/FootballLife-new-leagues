#include <assert.h>

#include "fl27playoffrules.h"

static void expect(PlayoffPlaces places, unsigned promotions, uint64_t expected)
{
    for (unsigned rank = 1; rank <= 64; ++rank)
        assert((playoff_arrow(places, rank, promotions, 0) != 0) == ((expected & rank_bit(rank)) != 0));
}

int main(void)
{
    uint64_t third_to_sixth = rank_bit(3) | rank_bit(4) | rank_bit(5) | rank_bit(6);
    const StockPlayoff *english = stock_profile(79);
    const StockPlayoff *spanish = stock_profile(80);
    const StockPlayoff *italian = stock_profile(82);
    uint8_t points[10] = {0};
    expect(stock_playoff(english, 17, 3, 4, 4, 10, UINT64_MAX, points), 3, third_to_sixth);
    expect(stock_playoff(spanish, 19, 3, 4, 4, 10, UINT64_MAX, points), 3, third_to_sixth);
    expect(stock_playoff(spanish, 19, 3, 4, 4, 10, UINT64_MAX ^ rank_bit(4), points),
           3, (third_to_sixth ^ rank_bit(4)) | rank_bit(7));
    expect(stock_playoff(italian, 18, 3, 4, 4, 10, UINT64_MAX, points),
           3, third_to_sixth | rank_bit(7) | rank_bit(8));
    points[2] = 60; points[3] = 51; points[4] = 46; points[5] = 45;
    expect(stock_playoff(italian, 18, 3, 4, 4, 10, UINT64_MAX, points),
           3, rank_bit(3) | rank_bit(4) | rank_bit(5));
    points[3] = 50;
    expect(stock_playoff(italian, 18, 3, 4, 4, 10, UINT64_MAX, points), 3, 0);
    assert(!stock_profile(366));
    expect(stock_playoff(english, 17, 2, 4, 4, 10, UINT64_MAX, points), 2, 0);
    expect(stock_playoff(english, 17, 3, 0, 4, 10, UINT64_MAX, points), 3, 0);
    expect(stock_playoff(english, 17, 3, 4, 2, 10, UINT64_MAX, points), 3, 0);
    expect(stock_playoff(english, 18, 3, 4, 4, 10, UINT64_MAX, points), 3, 0);

    PlayoffPlaces custom = {.entrants = third_to_sixth | rank_bit(2),
                           .contested = rank_bit(3), .custom = 1};
    expect(custom, 3, third_to_sixth);
    assert(!playoff_arrow(custom, 3, 3, 1)); /* Native relegation wins. */
    assert(!playoff_arrow(custom, 0, 3, 0));
    assert(!playoff_arrow(custom, 65, 3, 0));

    PlayoffPlaces group = {.entrants = rank_bit(2) | rank_bit(4), .custom = 1,
                          .group_quota_plus_one = 2};
    expect(group, 3, rank_bit(2) | rank_bit(4));
    group.group_quota_plus_one = 3;
    expect(group, 0, rank_bit(4));
    group.contested = rank_bit(2);
    expect(group, 0, rank_bit(2) | rank_bit(4));

    PlayoffPlaces challenger = {.entrants = rank_bit(3), .contested = rank_bit(3), .custom = 1};
    expect(challenger, 3, rank_bit(3));
    expect((PlayoffPlaces){0}, 3, 0);

    int first, second;
    RowState row = {0}, other = {0};
    reuse_row(&row, 1);
    reuse_row(&other, 2);
    row.orange = row.forced = true;
    assert(bitmap_change(&row, &first) == PAINT_ORANGE);
    assert(bitmap_change(&other, &second) == KEEP_BITMAP);
    row.painted = &first;
    reuse_row(&row, 1);
    assert(bitmap_change(&row, &first) == KEEP_BITMAP);
    assert(bitmap_change(&row, &second) == PAINT_ORANGE);
    row.orange = false;
    assert(bitmap_change(&row, &first) == RESTORE_GREEN);
    assert(bitmap_change(&row, 0) == KEEP_BITMAP);
    reuse_row(&row, 3);
    assert(!row.forced && !row.painted && bitmap_change(&row, &first) == KEEP_BITMAP);
    return 0;
}
